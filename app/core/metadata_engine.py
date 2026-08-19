import subprocess
import json
import os
import threading
from datetime import datetime
from typing import Optional, Dict, List
import sys

from app.core.db import db

VIDEO_EXTENSIONS = ['.mp4', '.mov', '.avi', '.mkv', '.mxf', '.mts', '.m2ts', '.ts', '.mpg', '.mpeg']
AUDIO_EXTENSIONS = ['.wav', '.mp3', '.aac', '.flac', '.ogg', '.m4a']
IMAGE_EXTENSIONS = ['.jpg', '.jpeg', '.png', '.tiff', '.tif', '.bmp', '.gif', '.webp']
RAW_EXTENSIONS = ['.cr2', '.cr3', '.nef', '.arw', '.dng', '.raf', '.orf', '.rw2', '.pef', '.srw']
BUILTIN_EXTENSIONS = set(VIDEO_EXTENSIONS + AUDIO_EXTENSIONS + IMAGE_EXTENSIONS + RAW_EXTENSIONS)

_SYSTEM_DIR_NAMES = {
    "$recycle.bin", "$windows.~bt", "$windows.~ws", "system volume information",
    "recycler", "recovery", "found.000", "lost+found", "msocache", "perflogs",
    "programdata", "windows", "windows.old",
    ".trashes", ".spotlight-v100", ".fseventsd", ".temporaryitems",
}
_SYSTEM_FILE_NAMES = {".ds_store", "desktop.ini", "thumbs.db", "autorun.inf"}


def _is_system_entry(name: str) -> bool:
    """True para carpetas/archivos del sistema que nunca deben escanearse.

    Al escanear la raíz de una tarjeta/disco (p. ej. F:/) aparecen carpetas
    como 'System Volume Information' o '$RECYCLE.BIN'; recorrerlas dispara
    ffprobe/copias sobre basura del sistema."""
    lower = name.lower()
    if lower in _SYSTEM_DIR_NAMES:
        return True
    if lower.startswith(".trash-") or lower.startswith("~$"):
        return True
    return lower in _SYSTEM_FILE_NAMES

_MAKE_KEYS = ("make", "com.apple.quicktime.make", "com.android.manufacturer")
_MODEL_KEYS = ("model", "com.apple.quicktime.model", "com.android.model")
_DATE_KEYS = ("creation_time", "date", "com.apple.quicktime.creationdate", "com.apple.quicktime.creationDate")
_SERIAL_KEYS = ("serial", "UniqueID", "com.apple.quicktime.serial")


class MetadataEngine:
    _MAX_CACHE = 2000

    def __init__(self):
        self.ffprobe_path = "ffprobe"
        self._setup_ffmpeg_silence()
        self._cache = {}
        self._cache_lock = threading.Lock()
        self._recognized_extensions = None
    
    def _setup_ffmpeg_silence(self):
        if sys.platform == "win32":
            self.startupinfo = subprocess.STARTUPINFO()
            self.startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            self.startupinfo.wShowWindow = subprocess.SW_HIDE
        else:
            self.startupinfo = None

    @staticmethod
    def _first_tag(tags: dict, keys: tuple) -> Optional[str]:
        """Primer tag no vacío de la lista de claves (evita valores basura)."""
        if not tags:
            return None
        for key in keys:
            value = tags.get(key)
            if value:
                value = str(value).strip()
                if value and value.lower() not in ("unknown", "n/a", "none"):
                    return value
        return None

    def _apply_camera_tags(self, metadata: dict, tags: dict):
        """Aplica make/model desde un diccionario de tags (formato o stream).

        Un modelo a nivel de stream es más específico que uno a nivel de
        contenedor, por eso el último modelo encontrado gana. También entiende
        los tags de móviles (QuickTime de Apple y com.android.*)."""
        model = self._first_tag(tags, _MODEL_KEYS)
        make = self._first_tag(tags, _MAKE_KEYS)
        if model:
            metadata["camera_model"] = model
        if make:
            metadata["camera_make"] = make
        if metadata["camera_model"] in ("Unknown", "", None) and make:
            metadata["camera_model"] = make

    @staticmethod
    def _parse_datetime(raw) -> Optional[datetime]:
        """Convierte una fecha cruda a datetime LOCAL (naive).

        Acepta ISO-8601 con Z/offset, formas 'YYYY-MM-DD HH:MM:SS' y variantes.
        Si la cadena es 'aware', la convierte a la zona horaria local del equipo."""
        if not raw:
            return None
        text = str(raw).strip().replace(" UTC", "")
        if not text:
            return None
        dt = None
        try:
            dt = datetime.fromisoformat(text)
        except ValueError:
            for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%d",
                        "%d/%m/%Y %H:%M:%S", "%d/%m/%Y %H:%M", "%d-%m-%Y %H:%M:%S"):
                try:
                    dt = datetime.strptime(text, fmt)
                    break
                except ValueError:
                    continue
        if dt is None:
            return None
        if dt.tzinfo is not None:
            dt = dt.astimezone().replace(tzinfo=None)
        return dt

    def _finalize_dates(self, metadata: dict, file_path: str):
        """Rellena creation_dt (datetime local) y date_source ('metadata'|'mtime').

        Si ffprobe no aportó fecha, cae al mtime del archivo, marcando la
        fuente para que la UI pueda indicar que la fecha es orientativa."""
        raw = metadata.get("creation_date")
        dt = self._parse_datetime(raw) if raw else None
        source = "metadata"
        if dt is None:
            try:
                dt = datetime.fromtimestamp(os.path.getmtime(file_path))
                source = "mtime"
            except OSError:
                dt = None
                source = None
        metadata["creation_dt"] = dt
        metadata["date_source"] = source
        if dt is not None:
            metadata["creation_date"] = dt.strftime("%Y-%m-%dT%H:%M:%S")

    def get_video_metadata(self, file_path: str) -> Dict:
        try:
            mtime = os.path.getmtime(file_path)
            with self._cache_lock:
                if file_path in self._cache:
                    cached_mtime, cached_meta = self._cache[file_path]
                    if cached_mtime == mtime:
                        return cached_meta.copy()
        except OSError:
            pass

        cmd = [
            self.ffprobe_path,
            "-v", "quiet",
            "-print_format", "json",
            "-show_format",
            "-show_streams",
            "-read_intervals", "%+0.5",
            file_path
        ]

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=True,
                startupinfo=self.startupinfo,
                timeout=10
            )
            data = json.loads(result.stdout)

            metadata = {
                "camera_model": "Unknown",
                "camera_make": "Unknown",
                "serial": None,
                "creation_date": None,
                "creation_dt": None,
                "date_source": None,
                "duration": 0,
                "bitrate": 0,
                "format": "",
                "width": 0,
                "height": 0,
                "fps": 0,
                "codec": "",
                "audio_codec": "",
                "file_size": os.path.getsize(file_path),
                "is_video": False,
                "is_audio": False,
                "is_image": False
            }

            if "format" in data:
                fmt = data["format"]
                metadata["format"] = fmt.get("format_name", "Unknown")
                metadata["duration"] = float(fmt.get("duration", 0))
                metadata["bitrate"] = int(fmt.get("bitrate", 0))

                format_tags = fmt.get("tags", {})
                metadata["creation_date"] = self._first_tag(format_tags, _DATE_KEYS)
                self._apply_camera_tags(metadata, format_tags)
                metadata["serial"] = self._first_tag(format_tags, _SERIAL_KEYS)

            for stream in data.get("streams", []):
                codec_type = stream.get("codec_type", "")

                if codec_type == "video":
                    metadata["is_video"] = True
                    metadata["width"] = int(stream.get("width", 0))
                    metadata["height"] = int(stream.get("height", 0))
                    metadata["codec"] = stream.get("codec_name", "")

                    fps_str = stream.get("r_frame_rate", "0/1")
                    if "/" in fps_str:
                        num, den = fps_str.split("/")
                        if int(den) > 0:
                            metadata["fps"] = round(int(num) / int(den), 2)

                    tags = stream.get("tags", {})
                    self._apply_camera_tags(metadata, tags)
                    if not metadata["creation_date"]:
                        metadata["creation_date"] = self._first_tag(tags, _DATE_KEYS)
                    if not metadata["serial"]:
                        metadata["serial"] = self._first_tag(tags, _SERIAL_KEYS)

                elif codec_type == "audio":
                    metadata["is_audio"] = True
                    metadata["audio_codec"] = stream.get("codec_name", "")

            ext = os.path.splitext(file_path)[1].lower()
            image_extensions = ['.jpg', '.jpeg', '.png', '.tiff', '.tif', '.bmp', '.gif', '.webp']
            raw_extensions = ['.cr2', '.cr3', '.nef', '.arw', '.dng', '.raf', '.orf', '.rw2', '.pef', '.srw']

            if ext in image_extensions or ext in raw_extensions:
                metadata["is_image"] = True
                metadata["is_video"] = False
                camera_from_ext = self._camera_from_extension(ext)
                if metadata["camera_model"] == "Unknown" and camera_from_ext:
                    metadata["camera_model"] = camera_from_ext

            self._finalize_dates(metadata, file_path)

            with self._cache_lock:
                self._cache[file_path] = (mtime, metadata.copy())
                if len(self._cache) > self._MAX_CACHE:
                    for k in list(self._cache)[: self._MAX_CACHE // 2]:
                        self._cache.pop(k, None)

            return metadata

        except subprocess.TimeoutExpired:
            metadata = {"camera_model": "Unknown_Camera", "camera_make": "Unknown", "serial": None,
                    "creation_date": None, "creation_dt": None, "date_source": None,
                    "duration": 0, "bitrate": 0, "format": "", "width": 0, "height": 0,
                    "fps": 0, "codec": "", "audio_codec": "", "file_size": 0,
                    "is_video": False, "is_audio": False, "is_image": False}
            try:
                metadata["file_size"] = os.path.getsize(file_path)
            except OSError:
                pass
            self._finalize_dates(metadata, file_path)
            return metadata
        except Exception as e:
            print(f"Error extracting metadata from {file_path}: {e}")
            metadata = {"camera_model": "Unknown_Camera", "camera_make": "Unknown", "serial": None,
                    "creation_date": None, "creation_dt": None, "date_source": None,
                    "duration": 0, "bitrate": 0, "format": "", "width": 0, "height": 0,
                    "fps": 0, "codec": "", "audio_codec": "", "file_size": 0,
                    "is_video": False, "is_audio": False, "is_image": False}
            try:
                metadata["file_size"] = os.path.getsize(file_path)
            except OSError:
                pass
            self._finalize_dates(metadata, file_path)
            return metadata

    def _camera_from_extension(self, ext: str) -> str:
        raw_ext_to_brand = {
            '.cr2': 'Canon', '.cr3': 'Canon',
            '.nef': 'Nikon',
            '.arw': 'Sony',
            '.dng': 'Generic DNG',
            '.raf': 'Fujifilm',
            '.orf': 'Olympus',
            '.rw2': 'Panasonic',
            '.pef': 'Pentax',
            '.srw': 'Samsung',
        }
        return raw_ext_to_brand.get(ext, "Unknown")
    
    def detect_camera_batch(self, file_paths: List[str]) -> Dict:
        camera_counts = {}
        
        for file_path in file_paths[:10]:
            metadata = self.get_video_metadata(file_path)
            if metadata:
                camera = metadata.get("camera_model", "Unknown")
                if camera != "Unknown":
                    camera_counts[camera] = camera_counts.get(camera, 0) + 1
        
        if camera_counts:
            dominant_camera = max(camera_counts.items(), key=lambda x: x[1])
            return {
                "primary_camera": dominant_camera[0],
                "camera_counts": camera_counts,
                "confidence": dominant_camera[1] / min(len(file_paths), 10)
            }
        
        return {
            "primary_camera": "Unknown",
            "camera_counts": {},
            "confidence": 0
        }

    def scan_for_dates_batch(self, file_paths: List[str], progress_cb=None,
                             max_workers: int = 8, cancel_cb=None) -> Dict:
        """Escanea archivos en paralelo y los agrupa por día de grabación.

        progress_cb(done, total) se invoca por cada archivo completado.
        cancel_cb() (opcional) se evalúa periódicamente; si devuelve True la
        exploración se detiene devolviendo el resultado parcial.

        Devuelve:
            {
                "by_date": { "YYYY-MM-DD": [file_path, ...], ... },
                "no_date": [file_path, ...],
                "total": len(file_paths),
            }
        """
        from concurrent.futures import ThreadPoolExecutor, as_completed
        by_date: Dict[str, List[str]] = {}
        no_date: List[str] = []
        total = len(file_paths)
        done = 0

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {executor.submit(self._probe_for_date, p): p for p in file_paths}
            for future in as_completed(futures):
                if cancel_cb and cancel_cb():
                    executor.shutdown(wait=False, cancel_futures=True)
                    break
                path = futures[future]
                try:
                    date_key, _source = future.result()
                except Exception:
                    date_key = None
                if date_key:
                    by_date.setdefault(date_key, []).append(path)
                else:
                    no_date.append(path)
                done += 1
                if progress_cb:
                    progress_cb(done, total)

        return {
            "by_date": by_date,
            "no_date": no_date,
            "total": total,
        }

    def date_key_for_file(self, file_path: str):
        """Devuelve la clave de fecha 'YYYY-MM-DD' para un archivo usando la
        misma resolución que el escaneo por fechas (metadatos -> mtime), o
        None si no se pudo determinar."""
        meta = self.get_video_metadata(file_path)
        dt = meta.get("creation_dt") if meta else None
        if dt is None:
            try:
                dt = datetime.fromtimestamp(os.path.getmtime(file_path))
            except OSError:
                dt = None
        if dt is None:
            return None
        return dt.strftime("%Y-%m-%d")

    def _probe_for_date(self, file_path: str):
        """Devuelve (fecha_YYYY-MM-DD, fuente) o (None, None)."""
        meta = self.get_video_metadata(file_path)
        source = meta.get("date_source") if meta else None
        return self.date_key_for_file(file_path), source

    def scan_source_for_dates(self, source_path: str, progress_cb=None,
                              max_workers: int = 8, cancel_cb=None) -> Dict:
        """Recorre un origen, recoge los archivos reconocidos y los agrupa por
        día de grabación (ver scan_for_dates_batch)."""
        files = []
        for root, dirs, fnames in os.walk(source_path):
            dirs[:] = [d for d in dirs if not _is_system_entry(d)]
            for name in fnames:
                if name.startswith(".") or _is_system_entry(name):
                    continue
                full = os.path.join(root, name)
                try:
                    info = self.get_file_type_info(full)
                except Exception:
                    continue
                if info.get("type") in ("other", "reference"):
                    continue
                files.append(full)
        return self.scan_for_dates_batch(files, progress_cb=progress_cb,
                                         max_workers=max_workers, cancel_cb=cancel_cb)

    def _builtin_extensions(self) -> set:
        return set(BUILTIN_EXTENSIONS)

    def _load_recognized_extensions(self):
        try:
            raw = db.get_containers()
        except Exception:
            raw = []
        exts = set()
        for e in raw:
            e = e.strip().lower()
            if not e:
                continue
            if not e.startswith("."):
                e = "." + e
            exts.add(e)
        self._recognized_extensions = exts or self._builtin_extensions()

    def refresh_file_types(self):
        self._recognized_extensions = None

    def get_recognized_extensions(self) -> set:
        if self._recognized_extensions is None:
            self._load_recognized_extensions()
        return self._recognized_extensions

    def get_file_type_info(self, file_path: str) -> Dict:
        ext = os.path.splitext(file_path)[1].lower()
        if not ext:
            return {"type": "other", "category": "reference"}
        if ext in VIDEO_EXTENSIONS:
            return {"type": "video", "category": "footage"}
        elif ext in AUDIO_EXTENSIONS:
            return {"type": "audio", "category": "audio"}
        elif ext in RAW_EXTENSIONS:
            return {"type": "raw_image", "category": "photos"}
        elif ext in IMAGE_EXTENSIONS:
            return {"type": "image", "category": "photos"}
        elif ext in self.get_recognized_extensions():
            return {"type": "media", "category": "media"}
        else:
            return {"type": "other", "category": "reference"}

metadata_engine = MetadataEngine()
