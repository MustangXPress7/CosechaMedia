import os
import shutil
import threading
import time
import json
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor
from typing import Dict, List, Optional, Set
from app.core.db import db
from app.core.utils import create_folder_structure, calculate_md5
from app.core.metadata_engine import metadata_engine

from PySide6.QtCore import QObject, Signal


def _human_bytes(num: int) -> str:
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if abs(num) < 1024.0:
            return f"{num:3.1f} {unit}"
        num /= 1024.0
    return f"{num:.1f} PB"


def _free_space(path: str) -> int:
    try:
        return shutil.disk_usage(path).free
    except Exception:
        return 0


def copy_verified(source_path: str, dest_path: str, progress_cb=None) -> bool:
    """Copia un archivo calculando el hash del origen durante la copia y
    comparándolo con el del destino. Devuelve True solo si coinciden.
    Elimina el destino parcial ante cualquier error o discrepancia.
    ``progress_cb(copied, total)`` se invoca por bloque copiado."""
    import hashlib
    src_md5 = hashlib.md5()
    total = 0
    try:
        total = os.path.getsize(source_path)
    except OSError:
        pass
    try:
        with open(source_path, 'rb') as src_f, open(dest_path, 'wb') as dst_f:
            copied = 0
            while True:
                chunk = src_f.read(8192)
                if not chunk:
                    break
                src_md5.update(chunk)
                dst_f.write(chunk)
                copied += len(chunk)
                if progress_cb:
                    progress_cb(copied, total)
        try:
            shutil.copystat(source_path, dest_path)
        except OSError:
            pass
        src_hash = src_md5.hexdigest()
        dest_hash = calculate_md5(dest_path)
        if src_hash and dest_hash and src_hash != dest_hash:
            try:
                os.remove(dest_path)
            except OSError:
                pass
            return False
        return True
    except Exception as e:
        print(f"Error copying {source_path}: {e}")
        try:
            os.remove(dest_path)
        except OSError:
            pass
        return False


def _ensure_subfolder(parent: str, camera: str, shoot_date: str,
                      include_date: bool, include_camera: bool,
                      folder_name: str) -> str:
    """Builds subpath inside parent: {folder_name}/{camera?}/{date?}."""
    parts = [parent, folder_name]
    if include_camera and camera:
        parts.append(camera)
    if include_date and shoot_date:
        parts.append(shoot_date)
    full = os.path.join(*parts)
    os.makedirs(full, exist_ok=True)
    return full


class DumpTarget:
    """Representa una ubicación de volcado y permite elegir la próxima."""
    def __init__(self, loc_id: int, path: str, include_date: bool, include_camera: bool):
        self.loc_id = loc_id
        self.path = path
        self.include_date = include_date
        self.include_camera = include_camera
        self._lock = threading.Lock()

    def next_available_dir(self, camera: str, shoot_date: str,
                           folder_name: str, file_size: int) -> Optional[str]:
        """Reservar la carpeta de volcado si cabe el archivo; None si está llena."""
        with self._lock:
            target = _ensure_subfolder(
                self.path, camera, shoot_date,
                self.include_date, self.include_camera, folder_name
            )
            free = _free_space(self.path)
            if free < file_size + (50 * 1024 * 1024):
                return None
            return target


class Ingestor(QObject):
    file_started = Signal(str)
    file_finished = Signal(str, str, bool, dict)
    copy_progress = Signal(str, int, int)
    ingest_complete = Signal(dict)
    camera_rename_needed = Signal(str, str)
    disk_full = Signal(int)
    dump_progress = Signal(str)

    def __init__(self, project_id: int, destination_root: str,
                 folder_name: str = "Footage", use_metadata_date: bool = True,
                 order_type: str = "camera_first", duration_type: int = 1,
                 default_camera: str = "", delicate_mode: bool = False,
                 max_workers: int = 4, session_id: Optional[int] = None,
                 dump_targets: Optional[List[DumpTarget]] = None,
                 project_master_root: Optional[str] = None,
                 camera_map: Optional[Dict[str, str]] = None,
                 manual_date: Optional[str] = None,
                 content_filter: Optional[Dict] = None):
        super().__init__()
        self.project_id = project_id
        self.session_id = session_id
        self.destination_root = destination_root
        self.project_master_root = project_master_root or destination_root
        self.folder_name = folder_name
        self.use_metadata_date = use_metadata_date
        self.manual_date = manual_date
        self.order_type = order_type
        self.duration_type = duration_type
        self.default_camera = default_camera
        self.delicate_mode = delicate_mode
        self.max_workers = 1 if delicate_mode else max_workers
        self.executor = ThreadPoolExecutor(max_workers=self.max_workers)
        self.processed_files = set()
        self._stop_event = threading.Event()

        self.dump_targets: List[DumpTarget] = dump_targets or []
        self._current_target_idx = 0
        self._target_lock = threading.Lock()
        self._full_targets: Set[int] = set()

        self._session_file = os.path.join(
            destination_root, f".sdimport_session_{self.session_id if self.session_id is not None else 'reactive'}.json"
        )
        self._legacy_session_file = os.path.join(destination_root, ".sdimport_session.json")
        self._copied_files = self._load_copied_files()

        self._content_filter = None
        if content_filter:
            self._content_filter = {
                "dates": set(content_filter.get("dates") or []),
                "include_nodate": bool(content_filter.get("include_nodate")),
            }
        self._stats = {
            "processed": 0,
            "errors": 0,
            "skipped": 0,
            "start_time": time.time()
        }
        self._camera_mapping = {}
        self._source_camera_map = dict(camera_map) if camera_map else {}
        self._camera_lock = threading.Lock()
        self._db_lock = threading.Lock()

        self._inflight = 0
        self._inflight_lock = threading.Lock()
        self._remaining_watchers = 0
        self._complete_emitted = False

    def _load_copied_files(self) -> Set[str]:
        for path in (self._session_file, self._legacy_session_file):
            if os.path.exists(path):
                try:
                    with open(path, 'r') as f:
                        data = json.load(f)
                        return set(data.get("copied_files", []))
                except Exception:
                    continue
        return set()

    def _save_copied_files(self):
        try:
            with open(self._session_file, 'w') as f:
                json.dump({
                    "copied_files": list(self._copied_files),
                    "last_update": datetime.now().isoformat()
                }, f, indent=2)
        except:
            pass

    def stop(self):
        self._stop_event.set()
        self._save_copied_files()

    def begin_watching(self, watcher_count: int):
        with self._inflight_lock:
            self._remaining_watchers = watcher_count
            self._complete_emitted = False

    def watcher_completed(self):
        emit = False
        with self._inflight_lock:
            if self._remaining_watchers > 0:
                self._remaining_watchers -= 1
            if self._remaining_watchers == 0 and self._inflight == 0:
                emit = True
        if emit:
            self._emit_complete_once()

    def _emit_complete_once(self):
        with self._inflight_lock:
            if self._complete_emitted:
                return
            self._complete_emitted = True
        stats = self.get_stats()
        self.ingest_complete.emit(stats)

    def is_idle(self) -> bool:
        with self._inflight_lock:
            return self._inflight == 0

    def handle_new_file(self, source_path: str):
        if source_path in self.processed_files:
            return
        
        if source_path in self._copied_files:
            self._stats["skipped"] += 1
            return
        
        if self._stop_event.is_set():
            return

        if self._content_filter and not self._matches_filter(source_path):
            self._stats["skipped"] += 1
            return

        self.processed_files.add(source_path)
        
        file_info = metadata_engine.get_file_type_info(source_path)
        
        if file_info["type"] in ["other"]:
            self._handle_reference_file(source_path)
            return
        
        self.file_started.emit(source_path)
        
        with self._inflight_lock:
            self._inflight += 1
        self.executor.submit(self._process_single_file, source_path, file_info)

    def _matches_filter(self, source_path: str) -> bool:
        """True si el archivo cae dentro del filtro de contenido (por fecha)."""
        date_key = metadata_engine.date_key_for_file(source_path)
        if date_key is None:
            return self._content_filter.get("include_nodate", False)
        return date_key in self._content_filter.get("dates", set())

    def _handle_reference_file(self, source_path: str):
        ref_dir = os.path.join(self.destination_root, "_reference")
        os.makedirs(ref_dir, exist_ok=True)

        base, ext = os.path.splitext(os.path.basename(source_path))
        dest_path = os.path.join(ref_dir, os.path.basename(source_path))
        n = 1
        while os.path.exists(dest_path):
            dest_path = os.path.join(ref_dir, f"{base} ({n}){ext}")
            n += 1

        try:
            shutil.copy2(source_path, dest_path)

            sid = self.session_id if self.session_id is not None else "reference_session"
            with self._db_lock:
                conn = db.get_connection()
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO files (session_id, source_path, dest_path, file_size, md5_hash, status, verified_at)
                    VALUES (?, ?, ?, ?, ?, 'reference', CURRENT_TIMESTAMP)
                ''', (str(sid), source_path, dest_path, os.path.getsize(dest_path), calculate_md5(dest_path)))
                conn.commit()
                conn.close()

            self._copied_files.add(source_path)
            self._save_copied_files()
        except Exception as e:
            print(f"Error copying reference file {source_path}: {e}")

    def _process_single_file(self, source_path: str, file_info: Dict):
        try:
            if self._stop_event.is_set():
                return
            self._run_single_file(source_path, file_info)
        finally:
            emit = False
            with self._inflight_lock:
                self._inflight -= 1
                if self._remaining_watchers == 0 and self._inflight == 0:
                    emit = True
            if emit:
                self._emit_complete_once()

    def _run_single_file(self, source_path: str, file_info: Dict):
        try:
            known_cam = self._get_camera_for_file(source_path)
            metadata = metadata_engine.get_video_metadata(source_path)
            if known_cam != "Unknown_Camera":
                camera_name = known_cam
            else:
                camera_name = metadata.get("camera_model", "Unknown_Camera")
                camera_name = self._sanitize_camera_name(camera_name)

                if camera_name == "Unknown_Camera" and self.default_camera:
                    camera_name = self.default_camera

                if camera_name == "Unknown_Camera":
                    self.camera_rename_needed.emit(source_path, camera_name)

                self._update_camera_mapping(source_path, camera_name)

            shoot_date = self._determine_date(metadata)

            actual_camera = self._get_camera_for_file(source_path)

            try:
                file_size = os.path.getsize(source_path)
            except OSError:
                file_size = 0

            target, dest_dir = self._pick_dump_target(
                actual_camera, shoot_date, file_size
            )
            if dest_dir is None:
                self._stats["errors"] += 1
                self.file_finished.emit(source_path, "", False, metadata)
                return

            dest_path = os.path.join(dest_dir, os.path.basename(source_path))
            os.makedirs(os.path.dirname(dest_path), exist_ok=True)

            if not self._copy_verified(source_path, dest_path):
                self._stats["errors"] += 1
                self.file_finished.emit(source_path, "", False, metadata)
                return

            file_hash = calculate_md5(dest_path)
            file_size = os.path.getsize(dest_path)

            sid = self.session_id if self.session_id is not None else "reactive_session"

            with self._db_lock:
                conn = db.get_connection()
                cursor = conn.cursor()
                cursor.execute(
                    '''INSERT INTO files (session_id, source_path, dest_path, dump_location_id,
                                          file_size, md5_hash, status, verified_at)
                       VALUES (?, ?, ?, ?, ?, ?, 'completed', CURRENT_TIMESTAMP)''',
                    (str(sid), source_path, dest_path, target.loc_id if target else None,
                     file_size, file_hash)
                )
                conn.commit()
                conn.close()

            self._copied_files.add(source_path)
            self._save_copied_files()

            self._stats["processed"] += 1

            self.file_finished.emit(source_path, dest_path, True, metadata)

        except Exception as e:
            print(f"Error processing {source_path}: {e}")
            self._stats["errors"] += 1
            self.file_finished.emit(source_path, "", False, {})

    def _copy_verified(self, source_path: str, dest_path: str) -> bool:
        """Copia verificada por MD5 con progreso por archivo (emitido por %)."""
        state = {"last": -1}

        def _progress(copied: int, total: int):
            if not total:
                return
            pct = int(copied * 100.0 / total)
            if pct != state["last"]:
                state["last"] = pct
                self.copy_progress.emit(source_path, copied, total)

        return copy_verified(source_path, dest_path, progress_cb=_progress)

    def _pick_dump_target(self, camera: str, shoot_date: str,
                          file_size: int):
        """Reserva el siguiente target secuencial que tenga espacio."""
        if not self.dump_targets:
            dest_dir = create_folder_structure(
                self.destination_root,
                camera, shoot_date, self.order_type,
                folder_name=self.folder_name
            )
            return None, dest_dir

        n = len(self.dump_targets)
        start_idx = self._current_target_idx
        for offset in range(n):
            idx = (start_idx + offset) % n
            target = self.dump_targets[idx]
            with self._target_lock:
                if target.loc_id in self._full_targets:
                    continue
                dest = target.next_available_dir(
                    camera, shoot_date, self.folder_name, file_size
                )
                if dest is None:
                    self._full_targets.add(target.loc_id)
                    self.disk_full.emit(target.loc_id)
                    self.dump_progress.emit(
                        f"Disco lleno: {target.path} ({_human_bytes(_free_space(target.path))} libres)"
                    )
                    continue
                if offset > 0:
                    self._current_target_idx = idx
                self.dump_progress.emit(
                    f"Volcando a {target.path}"
                )
                return target, dest
        return None, None

    def _sanitize_camera_name(self, name: str) -> str:
        invalid_chars = ['<', '>', ':', '"', '/', '\\', '|', '?', '*']
        for char in invalid_chars:
            name = name.replace(char, '_')
        return name.strip()

    def _determine_date(self, metadata: Dict) -> str:
        if self.duration_type == 3:
            return ""
        
        if self.use_metadata_date and metadata.get("creation_date"):
            date_str = metadata["creation_date"]
            if len(date_str) >= 10:
                return date_str[:10]
        
        if self.manual_date:
            return self.manual_date
        
        return datetime.now().strftime("%Y-%m-%d")

    def _update_camera_mapping(self, file_path: str, camera_name: str):
        with self._camera_lock:
            if file_path not in self._camera_mapping:
                self._camera_mapping[file_path] = camera_name

    def _get_camera_for_file(self, file_path: str) -> str:
        with self._camera_lock:
            cam = self._camera_mapping.get(file_path)
            if cam:
                return cam
            npath = file_path.replace("\\", "/")
            for src_root, cam_name in self._source_camera_map.items():
                nroot = src_root.replace("\\", "/")
                # Empareja solo la raíz y sus subdirectorios (no "Joan2"
                # cuando la raíz es "Joan").
                if npath == nroot or npath.startswith(nroot.rstrip("/") + "/"):
                    return cam_name
            return "Unknown_Camera"

    def reorganize_by_metadata(self):
        unknown_dir = os.path.join(self.destination_root, self.folder_name, "Unknown_Camera")
        if not os.path.exists(unknown_dir):
            return
        
        files_to_reorganize = []
        for root, dirs, files in os.walk(unknown_dir):
            for file in files:
                file_path = os.path.join(root, file)
                files_to_reorganize.append(file_path)
        
        camera_batches = {}
        for file_path in files_to_reorganize:
            metadata = metadata_engine.get_video_metadata(file_path)
            camera = metadata.get("camera_model", "Unknown_Camera")
            camera = self._sanitize_camera_name(camera)
            
            if camera not in camera_batches:
                camera_batches[camera] = []
            camera_batches[camera].append((file_path, metadata))
        
        for camera_name, files in camera_batches.items():
            if camera_name == "Unknown_Camera":
                continue
            
            for file_path, metadata in files:
                shoot_date = self._determine_date(metadata)
                new_dir = create_folder_structure(
                    self.destination_root,
                    camera_name,
                    shoot_date,
                    "camera_first",
                    folder_name=self.folder_name
                )
                new_path = os.path.join(new_dir, os.path.basename(file_path))
                n = 1
                while os.path.exists(new_path):
                    base, ext = os.path.splitext(os.path.basename(file_path))
                    new_path = os.path.join(new_dir, f"{base} ({n}){ext}")
                    n += 1
                try:
                    shutil.move(file_path, new_path)
                except:
                    pass

    def get_stats(self) -> Dict:
        self._stats["duration"] = time.time() - self._stats["start_time"]
        return self._stats.copy()



    def rename_camera(self, old_name: str, new_name: str):
        new_name = self._sanitize_camera_name(new_name)
        if old_name == new_name:
            return
        
        old_dir = os.path.join(self.destination_root, self.folder_name, old_name)
        new_dir = os.path.join(self.destination_root, self.folder_name, new_name)
        
        if os.path.exists(old_dir):
            os.makedirs(new_dir, exist_ok=True)
            for item in os.listdir(old_dir):
                old_item = os.path.join(old_dir, item)
                new_item = os.path.join(new_dir, item)
                if os.path.isdir(old_item):
                    shutil.move(old_item, new_item)
                else:
                    shutil.move(old_item, new_item)
            try:
                os.rmdir(old_dir)
            except OSError:
                pass
        
        with self._camera_lock:
            for fp, cam in self._camera_mapping.items():
                if cam == old_name:
                    self._camera_mapping[fp] = new_name
        
        with self._db_lock:
            conn = db.get_connection()
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE files SET dest_path = REPLACE(dest_path, ?, ?) WHERE dest_path LIKE ?",
                (f"/{old_name}/", f"/{new_name}/", f"%/{old_name}/%")
            )
            conn.commit()
            conn.close()
