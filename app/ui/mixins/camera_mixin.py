import os
import threading
import uuid
from PySide6.QtCore import QTimer, QDate, QSettings
from PySide6.QtWidgets import QInputDialog, QMessageBox
from app.core.db import db
from app.core.sd_reader import sd_reader
from app.core.metadata_engine import metadata_engine
from app.core.utils import get_mounted_drives

class CameraMixin:
    """Métodos de detección/nombrado de cámara y lectura de tarjeta SD extraídos de MainWindow (quick 260906-fgl)."""

    def _on_camera_rename_needed(self, source_path, nombre_dispositivo):
        if self.project_camera_detection_mode == "manual":
            return
        self._unknown_cameras.add(nombre_dispositivo)

    def _post_ingest_rename_dialog(self):
        if self.project_camera_detection_mode == "manual":
            self._unknown_cameras.clear()
            return
        if not self._unknown_cameras:
            return
        unknown_list = list(self._unknown_cameras)
        self._unknown_cameras.clear()
        for old_name in unknown_list:
            new_name, ok = QInputDialog.getText(
                self, self.tr("Dispositivo desconocido detectado"),
                self.tr("Se detectó '%1' sin identificar.\nIntroduce un nombre para el dispositivo:").arg(old_name),
                text=""
            )
            if ok and new_name.strip():
                new_cam = new_name.strip()
                for ing in self._ingestors:
                    ing.rename_dispositivo(old_name, new_cam)
                for r in range(self.table.rowCount()):
                    cam_item = self.table.item(r, 1)
                    if cam_item and cam_item.text() == old_name:
                        cam_item.setText(new_cam)
                sessions = db.get_sessions(self.current_project_id) if self.current_project_id else []
                for s in sessions:
                    if s.get("nombre_dispositivo") == old_name:
                        sp = s.get("source_path", "")
                        self._persist_camera_mapping(s["id"], sp, new_cam)
                self.ingest_status_label.setText(self.tr("Dispositivo renombrado: %1 → %2").arg(old_name).arg(new_cam))

    def _prompt_rename_camera(self, row):
        if self.current_project_id is None:
            return
        if row < 0 or row >= len(self._source_paths):
            return
        path = self._source_paths[row]
        sessions = db.get_sessions(self.current_project_id)
        session = next((s for s in sessions if s.get("source_path") == path), None)
        if not session:
            return
        current = session.get("nombre_dispositivo") or ""
        name, ok = QInputDialog.getText(
            self, self.tr("Renombrar dispositivo"),
            self.tr("Nombre del dispositivo para este origen:"),
            text=current
        )
        if ok:
            db.update_session_config(session["id"], nombre_dispositivo=name.strip() or None)
            self._refresh_source_list()
            self._refresh_sessions_combo()

    @staticmethod
    def _drive_label(path):
        if len(path) >= 2 and path[1] == ":":
            return path[:2]
        return os.path.basename(path.rstrip("/\\"))

    def _find_smallest_media(self, source_path):
        exts = {'.mp4','.mov','.mxf','.avi','.m4v','.mkv','.mts','.m2ts',
                '.cr2','.cr3','.nef','.arw','.dng','.jpg','.jpeg','.png','.bmp','.tiff','.tif'}
        candidates = []
        for root, dirs, files in os.walk(source_path):
            for f in files:
                ext = os.path.splitext(f)[1].lower()
                if ext in exts:
                    fp = os.path.join(root, f)
                    try:
                        candidates.append((os.path.getsize(fp), fp))
                    except OSError:
                        pass
        if not candidates:
            return None
        candidates.sort(key=lambda x: x[0])
        return candidates[0][1]

    def _set_camera_cell_text(self, source_path, text):
        for row in range(self.source_list.rowCount()):
            if row < len(self._source_paths) and self._source_paths[row] == source_path:
                cam_item = self.source_list.item(row, 1)
                if cam_item:
                    self.source_list.blockSignals(True)
                    cam_item.setText(text)
                    self.source_list.blockSignals(False)
                break

    def _camera_for_path(self, source_path):
        camera_map = getattr(self, "_current_camera_map", None)
        if not camera_map:
            return None
        npath = source_path.replace("\\", "/")
        for root, cam in camera_map.items():
            if npath.startswith(root.replace("\\", "/")):
                return cam
        return None

    def _detect_camera_for_session(self, session_id, source_path, force_prompt=False):
        """Detecta la cámara para una sesión. Flujo I-03+I-14:
        1. Buscar nombre conocido (sd_cards por serial o device_settings por device_id)
        2. Auto-rellenar si se conoce → guardar en sesión y volver
        3. Si no se conoce → detección automática (ffprobe) o prompt manual
        Si force_prompt=True (registro explícito de origen), se muestra el prompt
        incluso en modo manual si no se detectó cámara.
        """
        # 1. Buscar cámara conocida (I-03)
        sess = db.get_session(session_id)
        device_id = sess.get("device_id") if sess else None
        known_cam = None
        if device_id and str(device_id).startswith("ftp:"):
            known_cam = db.get_dispositivo_for_device(device_id)
        elif device_id and not str(device_id).startswith("wifi:"):
            known_cam = db.get_dispositivo_for_device(device_id)
        else:
            serial = sd_reader.get_volume_serial(source_path)
            if serial:
                known_cam = db.get_dispositivo_for_card(serial)

        # 2. Auto-rellenar si se conoce (I-03)
        if known_cam:
            db.update_session_config(session_id, nombre_dispositivo=known_cam)
            self._set_camera_cell_text(source_path, known_cam)
            self._refresh_source_list()
            self._refresh_sessions_combo()
            self.ingest_status_label.setText(self.tr("Dispositivo conocido: %1").arg(known_cam))
            return

        # 3. Detección automática (I-14)
        if self.project_camera_detection_mode == "manual":
            self._set_camera_cell_text(source_path, self.tr("Sin nombre"))
            if force_prompt:
                self._prompt_nombre_dispositivo(session_id, source_path, "")
            return

        self._set_camera_cell_text(source_path, "🔄 Escaneando…")
        detection_id = uuid.uuid4().hex
        self._cam_detection_id = detection_id
        self._cam_timer = QTimer(self)
        self._cam_timer.setSingleShot(True)
        self._cam_scan_scheduled = False

        def _apply_detection():
            """Aplica el resultado del scan y muestra prompt (main thread)."""
            if self._cam_detection_id != detection_id:
                return
            if self._cam_scan_scheduled:
                return
            self._cam_scan_scheduled = True
            cam = getattr(self, '_cam_detected', None)
            if cam:
                self._set_camera_cell_text(source_path, cam)
                db.update_session_config(session_id, nombre_dispositivo=cam)
                self._persist_camera_mapping(session_id, source_path, cam)
                self._refresh_source_list()
                self._refresh_sessions_combo()
                self.ingest_status_label.setText(
                    self.tr("Dispositivo detectado: %1").arg(cam))
            else:
                self._set_camera_cell_text(source_path, self.tr("Sin nombre"))
            QTimer.singleShot(0, lambda c=cam or "": self._prompt_nombre_dispositivo(session_id, source_path, c))

        def on_timeout():
            _apply_detection()

        self._cam_timer.timeout.connect(on_timeout)
        self._cam_timer.start(self.project_camera_detection_timeout * 1000)

        def scan():
            if self._cam_detection_id != detection_id:
                return
            smallest = self._find_smallest_media(source_path)
            if smallest is None:
                self._cam_detected = None
                QTimer.singleShot(0, _apply_detection)
                return
            try:
                meta = metadata_engine.get_video_metadata(smallest)
                cam = meta.get("camera_model", "") or ""
                if cam and cam.strip() and cam != "Unknown":
                    self._cam_detected = cam.strip()
                    QTimer.singleShot(0, _apply_detection)
                    return
            except Exception:
                pass
            self._cam_detected = None
            QTimer.singleShot(0, _apply_detection)

        t = threading.Thread(target=scan, daemon=True)
        t.start()

    def _prompt_nombre_dispositivo(self, session_id, source_path, suggested_name=""):
        """Prompt manual para nombre de dispositivo (I-14)."""
        self.raise_()
        self.activateWindow()
        base = self._drive_label(source_path)
        name, ok = QInputDialog.getText(
            self, self.tr("Nombre de dispositivo"),
            self.tr("Introduce el nombre del dispositivo para %1:").arg(base),
            text=suggested_name,
        )
        if ok and name.strip():
            cam = name.strip()
            db.update_session_config(session_id, nombre_dispositivo=cam)
            self._set_camera_cell_text(source_path, cam)
            self._persist_camera_mapping(session_id, source_path, cam)
        else:
            db.update_session_config(session_id, nombre_dispositivo=None)
            self._set_camera_cell_text(source_path, self.tr("Sin nombre"))
        self._refresh_source_list()
        self._refresh_sessions_combo()
        self.ingest_status_label.setText(
            self.tr("Dispositivo: %1").arg(cam if ok and name.strip() else self.tr("Sin nombre"))
        )

    def _detect_camera_for_source(self, kind, value):
        """Detecta la cámara para un origen del AddSourceDialog (D-08/D-09).

        Se ejecuta en un worker off-thread. Devuelve el nombre de cámara detectado
        o cadena vacía si no se pudo detectar.
        """
        # Para carpetas locales y USB, usamos el path directamente
        source_path = None
        if kind == "folder":
            source_path = value
        elif kind == "usb":
            source_path = value
        elif kind == "device":
            # Para MTP, el value es el device_id; no tenemos path directo aquí
            # La detección para MTP se hace en el diálogo principal tras registro
            return ""
        elif kind == "sender":
            # WiFi: no hay path local para detectar
            return ""
        elif kind == "ftp_profile":
            return ""

        if not source_path or not os.path.isdir(source_path):
            return ""

        try:
            smallest = self._find_smallest_media(source_path)
            if smallest is None:
                return ""
            meta = metadata_engine.get_video_metadata(smallest)
            cam = meta.get("camera_model", "") or ""
            if cam and cam.strip() and cam != "Unknown":
                return cam.strip()
        except Exception:
            pass
        return ""

    def _persist_camera_mapping(self, session_id, source_path, nombre_dispositivo):
        """Persiste el mapeo cámara→dispositivo en sd_cards o device_settings (I-03)."""
        if not nombre_dispositivo:
            return
        sess = db.get_session(session_id)
        if not sess:
            return
        device_id = sess.get("device_id")
        if device_id and not str(device_id).startswith("wifi:"):
            db.save_dispositivo_config(device_id, nombre_dispositivo)
            # Upsert a known_devices para persistencia cross-proyecto (REQ-09)
            try:
                device_type = "ftp" if str(device_id).startswith("ftp:") else "mtp"
                db.upsert_known_device(device_id, device_type, name=nombre_dispositivo, last_camera=nombre_dispositivo)
            except Exception:
                pass
        else:
            serial = sd_reader.get_volume_serial(source_path)
            if serial:
                db.save_dispositivo(serial, nombre_dispositivo)

    def _on_camera_cell_edited(self, item):
        row = item.row()
        if row < 0 or row >= len(self._source_paths):
            return
        path = self._source_paths[row]
        sessions = db.get_sessions(self.current_project_id)
        session = next((s for s in sessions if s.get("source_path") == path), None)
        if not session:
            return
        new_name = item.text().strip()
        db.update_session_config(session["id"], nombre_dispositivo=new_name or None)
        if new_name:
            self._persist_camera_mapping(session["id"], path, new_name)
        self._refresh_sessions_combo()
        self.ingest_status_label.setText(self.tr("Dispositivo: %1").arg(new_name or self.tr("Sin nombre")))

    def _on_dialog_camera_name_changed(self, device_id, nombre_dispositivo):
        """Guarda el nombre editado en el diálogo «Añadir origen» (B-20).

        Persiste el mapeo device_id→nombre en device_settings y sincroniza
        las sesiones abiertas de ese dispositivo; los cambios se reflejan en
        la lista de orígenes y en el combo de sesiones si la ventana está
        visible (durante el diálogo modal no hace falta refrescar).
        """
        if not device_id or not nombre_dispositivo:
            return
        sane = db._sanitize_dispositivo_nombre(nombre_dispositivo)
        if not sane:
            return
        db.save_dispositivo_config(device_id, sane)
        # Upsert a known_devices para persistencia cross-proyecto (REQ-09)
        try:
            device_type = "ftp" if str(device_id).startswith("ftp:") else "mtp"
            db.upsert_known_device(device_id, device_type, name=sane, last_camera=sane)
        except Exception:
            pass
        if self.current_project_id is None:
            return
        for s in db.get_sessions(self.current_project_id):
            if s.get("device_id") == device_id:
                db.update_session_config(s["id"], nombre_dispositivo=sane)
        if self.isVisible():
            self._refresh_source_list()
            self._refresh_sessions_combo()

    def _detect_sd_card(self):
        if not self._source_paths and not self.source_input.currentText().strip():
            QMessageBox.information(self, self.tr("Sin origen"), self.tr("Selecciona o añade una ruta de tarjeta SD primero."))
            return
        path = self._source_paths[0] if self._source_paths else self.source_input.currentText().strip()
        info = sd_reader.detect_card_info(path)
        lines = []
        if info["brand"]:
            lines.append(self.tr("Marca: %1").arg(info["brand"]))
        if info["model"]:
            lines.append(self.tr("Modelo: %1").arg(info["model"]))
        if info["serial"]:
            lines.append(self.tr("Serie: %1").arg(info["serial"]))
        if info["capacity_gb"]:
            lines.append(self.tr("Capacidad: %1 GB").arg(info["capacity_gb"]))
        if info["file_system"]:
            lines.append(self.tr("Sistema: %1").arg(info["file_system"]))
        if info["total_space"] > 0:
            used_pct = (info["used_space"] / info["total_space"]) * 100
            lines.append(self.tr("Uso: %1%").arg(f"{used_pct:.1f}"))
        if info["errors"]:
            lines.append(self.tr("Errores: %1").arg(", ".join(info["errors"])))
        text = "\n".join(lines) if lines else self.tr("No se pudo detectar información de la tarjeta.")
        QMessageBox.information(self, self.tr("Información de Tarjeta SD"), text)

    def _on_auto_detect_toggled(self, checked):
        settings = QSettings("Audiovisual Production", "CosechaMedia")
        settings.setValue("autoDetectDrives", bool(checked))
        if checked:
            self._auto_detect_removable_drives()

    def _auto_detect_removable_drives(self):
        try:
            drives = get_mounted_drives()
        except Exception as e:
            print(f"Error detecting drives: {e}")
            return
        if not drives:
            self.ingest_status_label.setText(self.tr("No se detectaron unidades extraíbles."))
            return
        added = []
        for d in drives:
            dp = d.get("path")
            if not dp:
                continue
            dcim = os.path.join(dp, "DCIM")
            candidate = dcim if os.path.isdir(dcim) else dp
            if candidate in self._source_paths:
                continue
            self._source_paths.append(candidate)
            added.append(candidate)
        if added:
            for p in added:
                if self.current_project_id:
                    sessions = db.get_sessions(self.current_project_id)
                    if not any(s.get("source_path") == p for s in sessions):
                        base = self._drive_label(p)
                        no_source = [s for s in sessions if not s.get("source_path")]
                        if no_source:
                            db.update_session_config(no_source[0]["id"], source_path=p, name=f"Auto ({base})")
                            sid = no_source[0]["id"]
                        else:
                            sid = db.create_session(
                                self.current_project_id, f"Auto ({base})",
                                QDate.currentDate().toString("yyyy-MM-dd"), "active",
                                source_path=p
                            )
                        self._detect_camera_for_session(sid, p)
            self._refresh_source_list()
            self._refresh_sessions_combo()
            self.update_start_button_state()
            self.ingest_status_label.setText(self.tr("Auto-detect: %1 unidad(es) añadida(s).").arg(len(added)))
        else:
            self._refresh_source_list()
            self.ingest_status_label.setText(self.tr("Auto-detect: ninguna unidad nueva."))

