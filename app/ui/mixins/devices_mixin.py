import os
import json
from PySide6.QtWidgets import QMessageBox, QDialog, QFileDialog, QInputDialog
from PySide6.QtCore import QThread, QTimer, QDate
from app.core.db import db, WIFI_DEVICE_ID, usb_device_id
from app.core import translator, mtp, ftp
from app.core.metadata_engine import metadata_engine
from app.core.sd_reader import sd_reader
import app.core.utils as utils
from app.ui import theme
from app.ui import icons
from app.ui.ftp_picker import FtpPickerDialog
from app.ui.ftp_status import FtpStatusDialog
from app.ui.add_source_dialog import AddSourceDialog
from app.core.mtp import DeviceInfo
from app.ui.mixins.workers import _StageWorker


def _is_usb_mounted(did, mounted):
    """Una clave usb:<ruta> está montada si su unidad sigue como medio real."""
    path = did[len("usb:"):]
    return path in mounted


class DevicesMixin:
    """Métodos de registro de dispositivos y staging MTP/FTP extraídos de MainWindow (quick 260906-bloque6-devicesmixin)."""

    def _delete_all_saved_devices(self):
        """Borra todos los dispositivos guardados (known_devices, inbox_senders, perfiles FTP)."""
        reply = QMessageBox.question(
            self, self.tr("Borrar dispositivos guardados"),
            self.tr("Esto eliminará todos los dispositivos guardados: "
                    "dispositivos conocidos, remitentes WiFi y perfiles FTP.\n"
                    "Esta acción no se puede deshacer.\n\n"
                    "¿Continuar?"),
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply != QMessageBox.Yes:
            return
        db.delete_all_saved_devices()
        self._populate_source_paths_from_sessions()
        self._refresh_source_list()
        self._refresh_sessions_combo()
        self.update_start_button_state()
        self.ingest_status_label.setText(
            self.tr("Todos los dispositivos guardados han sido eliminados."))

    def _delete_all_known_cameras(self):
        """Borra la cache de detección y los nombres de dispositivo en DB.
        No toca los dispositivos en sí (sesiones, perfiles FTP, remitentes)."""
        reply = QMessageBox.question(
            self, self.tr("Borrar nombres de dispositivos"),
            self.tr("Esto limpiará la cache de detección y los nombres de "
                    "cámara guardados para los dispositivos.\n"
                    "Los dispositivos en sí no se eliminan.\n"
                    "La próxima ingesta volverá a detectar los nombres automáticamente.\n\n"
                    "¿Continuar?"),
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply != QMessageBox.Yes:
            return
        metadata_engine.clear_cache()
        db.delete_all_known_cameras()
        self.ingest_status_label.setText(
            self.tr("Nombres de dispositivos eliminados. La detección se reiniciará."))

    def _disconnected_devices(self):
        """Dispositivos MTP/USB/FTP desconectados y perfiles FTP para poder
        borrarlos desde el diálogo unificado (D-12).

        También incluye dispositivos guardados globalmente (known_devices y el
        legacy device_settings) que no tienen sesiones en el proyecto actual,
        para que permanezcan visibles en 'Añadir origen' aunque se borren todas
        las sesiones del proyecto. Sin esto, borrar el origen de un USB de la
        tabla de orígenes lo hacía desaparecer también del diálogo (a diferencia
        de WiFi, que persiste vía inbox_senders)."""
        if self.current_project_id is None:
            return []
        try:
            current = {dev.device_id for dev in mtp.WpdBackend().list_devices()}
        except Exception:
            current = set()
        known = {}
        # 1. Dispositivos con sesiones en el proyecto actual
        for s in db.get_sessions(self.current_project_id):
            did = s.get("device_id") or ""
            if did.startswith("ftp:"):
                known.setdefault(did, s.get("nombre_dispositivo") or "")
            elif did and not did.startswith("wifi:"):
                known.setdefault(did, s.get("nombre_dispositivo") or "")
        # 2. Dispositivos guardados globalmente (known_devices; tabla unificada).
        #    Excluimos wifi (va por inbox_senders) y carpetas locales (van por
        #    la lista de carpetas), que no son dispositivos.
        for kd in db.list_known_devices():
            did = kd.get("device_id") or ""
            if not did:
                continue
            dtype = kd.get("device_type") or ""
            if dtype in ("wifi", "folder") or did.startswith("wifi:"):
                continue
            # Normalizar claves legacy de USB: el diálogo guardaba la ruta cruda
            # (E:\) mientras las sesiones/device_settings usan usb:E:\. Al unificar
            # la identidad evitamos duplicados y que delete_device no encuentre
            # las sesiones por usar una clave distinta.
            if dtype == "usb" and not did.startswith("usb:"):
                did = usb_device_id(did)
            if kd.get("name"):
                known.setdefault(did, kd["name"])
        # 3. Legacy device_settings (fuente histórica; redundante con
        #    known_devices, pero se mantiene hasta completar la migración).
        conn = db.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute('SELECT device_key, nombre_dispositivo FROM device_settings')
            for row in cursor.fetchall():
                did = row["device_key"]
                name = row["nombre_dispositivo"] or did
                if did not in known:
                    known[did] = name
        finally:
            conn.close()
        # Devolver dispositivos salvados, salvo unidades USB extraíbles que sigan
        # montadas como medio real: la visibilidad de una USB montada la da el
        # escaneo físico de «Añadir origen» (not connected flag), no el
        # registro guardado. Evita duplicar la fila [USB] seleccionable.
        mounted = set()
        try:
            mounted = {d["path"] for d in utils.get_mounted_drives()}
        except Exception:
            mounted = set()
        out = []
        for did in sorted(known):
            if did.startswith("usb:") and _is_usb_mounted(did, mounted):
                continue
            if did.startswith("ftp:") or did not in current:
                out.append({"id": did, "name": known[did] or did})
        return out

    def _register_device_source_from_picker(self, device_id, device_folder,
                                            device_name, backend):
        """Registra un origen de dispositivo (MTP o FTP) elegido en el diálogo unificado."""
        if self.current_project_id is None:
            QMessageBox.information(
                self, self.tr("Sin proyecto"),
                self.tr("Selecciona o crea un proyecto antes de elegir un dispositivo.")
            )
            return
        cache_dir = mtp.device_cache_dir(device_id, device_folder)
        try:
            os.makedirs(cache_dir, exist_ok=True)
        except OSError:
            cache_dir = mtp.device_cache_dir(device_id, "")
            os.makedirs(cache_dir, exist_ok=True)
        self._register_device_source(
            cache_dir, device_id, device_folder, device_name, backend=backend)

    def _assign_folder_source(self, path, camera=None):
        """Asigna un folder real como nuevo origen (nunca una caché gestionada).

        Si se pasa ``camera`` (p. ej. el nombre elegido en «Añadir origen»), se
        usa ese nombre como dispositivo en lugar de lanzar detección/prompt.
        """
        if self._is_managed_source_path(path):
            self._warn_managed_source(path)
            return
        if path not in self._source_paths:
            self._source_paths.append(path)
            self.source_input.setCurrentText("")
            if self.current_project_id:
                sessions = db.get_sessions(self.current_project_id)
                if not any(s.get("source_path") == path for s in sessions):
                    base = self._drive_label(path)
                    no_source = [s for s in sessions if not s.get("source_path")]
                    if no_source:
                        db.update_session_config(
                            no_source[0]["id"], source_path=path, name=f"Auto ({base})")
                        sid = no_source[0]["id"]
                    else:
                        # Para unidades USB extraíbles, asignar device_id basado en la ruta
                        # (solo si es una extraíble real, con filtro de falso positivo).
                        device_id = ""
                        if utils.is_true_removable_drive(path):
                            device_id = usb_device_id(path)
                        sid = db.create_session(
                            self.current_project_id, f"Auto ({base})",
                            QDate.currentDate().toString("yyyy-MM-dd"), "active",
                            source_path=path, device_id=device_id)
                    cam = (camera or "").strip()
                    if cam and cam not in (self.tr("Sin nombre"),):
                        db.update_session_config(sid, nombre_dispositivo=cam)
                        self._persist_camera_mapping(sid, path, cam)
                        self._set_camera_cell_text(path, cam)
                    else:
                        self._detect_camera_for_session(sid, path, force_prompt=not camera)
        self._repair_folder_device_id(path)
        self._refresh_source_list()
        self._refresh_sessions_combo()
        self.update_start_button_state()

    def _assign_session_folder(self, session_id, path):
        """Asigna un folder real como origen de una sesión concreta.

        Si la sesión estaba ligada a un dispositivo gestionado (WiFi/FTP/MTP),
        se desliga primero: pasa a ser un origen manual.
        """
        if self._is_managed_source_path(path):
            self._warn_managed_source(path)
            return
        session = db.get_session(session_id)
        if session is None:
            return
        if session.get("source_path") != path:
            if path not in self._source_paths:
                self._source_paths.append(path)
            base = self._drive_label(path)
            auto_name = f"Auto ({base})"
            sessions = db.get_sessions(self.current_project_id)
            for s in sessions:
                if s["id"] != session_id and s.get("source_path")==path and str(s.get("name","")).startswith("Auto ("):
                    auto_name = s.get("name")
                    break
            db.update_session_config(session_id, source_path=path, name=auto_name)
        if session.get("device_id"):
            db.update_session_config(session_id, device_id="", device_folder="")
            self._detect_camera_for_session(session_id, path)
        self._repair_folder_device_id(path)
        self._refresh_sessions_combo()
        self.update_start_button_state()

    def _repair_folder_device_id(self, path):
        """Repara el device_id de una sesión ligada a una carpeta/tarjeta.

        Un bug anterior (bug 2) podía dejar sesiones con device_id ``usbstor``
        (unidades USB de almacenamiento masivo que WPD enumera). Esos NO son
        dispositivos MTP reales: un device_id así rompe la asociación por
        serial, de modo que la sesión «no pilla el dispositivo». Lo limpiamos
        para que la tarjeta se identifique por su serial de volumen (sd_cards),
        tanto al asignar de nuevo un origen como al detectar la cámara.
        """
        if not utils.is_removable_drive(path):
            return
        if self.current_project_id is None:
            return
        for s in db.get_sessions(self.current_project_id):
            if s.get("source_path") != path:
                continue
            did = str(s.get("device_id") or "")
            if "usbstor" in did.lower():
                db.update_session_config(s["id"], device_id="", device_folder="")
                # Limpiar también el mapeo cámara huérfano guardado bajo ese id fake
                db.delete_device_settings_by_key(did)

    def _warn_managed_source(self, path):
        sessions = (db.get_sessions(self.current_project_id)
                    if self.current_project_id else [])
        owner = next((s for s in sessions
                      if s.get("source_path")
                      and os.path.normpath(s["source_path"]) == os.path.normpath(path)),
                     None)
        if owner is not None:
            QMessageBox.information(
                self, self.tr("Origen gestionado"),
                self.tr("Ese origen ya está asignado a la sesión #%1.").arg(owner["id"]))
        else:
            QMessageBox.warning(
                self, self.tr("Origen gestionado"),
                self.tr("No puedes usar una caché gestionada como origen manual."))

    def _show_ftp_status(self):
        dlg = FtpStatusDialog(self)
        dlg.exec()

    def _show_ftp_status_for_device(self, device_id):
        dlg = FtpStatusDialog(self, device_id=device_id)
        dlg.exec()

    def _reset_mtp_thread_local(self):
        """Reinicia el thread-local COM del MTP para evitar referencias corruptas."""
        try:
            from app.core import mtp
            import threading
            if hasattr(mtp, '_manager_local'):
                mtp._manager_local = threading.local()
        except Exception:
            pass
        # Detener thread de staging si existe
        if hasattr(self, '_stage_thread') and self._stage_thread and self._stage_thread.isRunning():
            self._stage_thread.quit()
            self._stage_thread.wait(2000)
            self._stage_thread = None
        if hasattr(self, '_stage_worker'):
            self._stage_worker = None

    def _reset_ingestors(self):
        """Limpia los ingestors vivos."""
        # Detener timers y watchers
        if hasattr(self, '_sync_timer') and self._sync_timer.isActive():
            self._sync_timer.stop()
        if hasattr(self, '_cam_timer') and self._cam_timer.isActive():
            self._cam_timer.stop()
        for watcher in self.watchers[:]:
            try:
                watcher.stop()
            except Exception:
                pass
        self.watchers = []
        # Detener ingestors
        for ing in self._ingestors[:]:
            try:
                ing.stop()
            except Exception:
                pass
        self._ingestors = []


    def _pick_ftp_source(self, preset_profile_id=None):
        dialog = FtpPickerDialog(self, preset_profile_id=preset_profile_id)
        if dialog.exec() != QDialog.Accepted:
            return
        if not dialog.device_id or not dialog.device_folder:
            return
        if self.current_project_id is None:
            QMessageBox.information(
                self, self.tr("Sin proyecto"),
                self.tr("Selecciona o crea un proyecto antes de elegir un dispositivo.")
            )
            return
        name = dialog.device_name or ""
        cache_dir = mtp.device_cache_dir(dialog.device_id, dialog.device_folder)
        try:
            os.makedirs(cache_dir, exist_ok=True)
        except OSError:
            cache_dir = mtp.device_cache_dir(dialog.device_id, "")
            os.makedirs(cache_dir, exist_ok=True)
        self._register_device_source(
            cache_dir, dialog.device_id, dialog.device_folder, name,
            backend=ftp.FtpBackend(),
        )

    def _register_device_source(self, cache_dir, device_id, device_folder, device_name, backend=None):
        if cache_dir not in self._source_paths:
            self._source_paths.append(cache_dir)
            self.source_input.setCurrentText("")
        # Guardar nombre del dispositivo para recordarlo en futuros proyectos
        if device_id and device_name:
            try:
                db.save_dispositivo_config(device_id, device_name)
                # Upsert a known_devices para persistencia cross-proyecto (REQ-09)
                device_type = "ftp" if str(device_id).startswith("ftp:") else "mtp"
                db.upsert_known_device(device_id, device_type, name=device_name, last_camera=device_name)
            except Exception:
                pass
        sessions = db.get_sessions(self.current_project_id)
        existing = next((s for s in sessions if s.get("source_path") == cache_dir), None)
        if existing:
            db.update_session_config(
                existing["id"],
                device_id=device_id, device_folder=device_folder,
                source_path=cache_dir,
                nombre_dispositivo=device_name,
            )
            sid = existing["id"]
        else:
            base = device_name or self._drive_label(cache_dir)
            no_source = [s for s in sessions if not s.get("source_path")]
            if no_source:
                sid = no_source[0]["id"]
                db.update_session_config(
                    sid, source_path=cache_dir, name=f"Auto ({base})",
                    device_id=device_id, device_folder=device_folder,
                    nombre_dispositivo=device_name,
                )
            else:
                sid = db.create_session(
                    self.current_project_id, f"Auto ({base})",
                    QDate.currentDate().toString("yyyy-MM-dd"), "active",
                    source_path=cache_dir,
                )
                db.update_session_config(sid, device_id=device_id, device_folder=device_folder,
                                          nombre_dispositivo=device_name)
        self._refresh_source_list()
        self._refresh_sessions_combo()
        self.update_start_button_state()
        self._stage_device_in_background(device_id, device_folder, sid, cache_dir, backend=backend)

    def _stage_device_in_background(self, device_id, device_folder, session_id, cache_dir,
                                    backend=None, silent=False):
        backend = backend or mtp.WpdBackend()
        worker = _StageWorker(backend, device_id, device_folder)
        thread = QThread(self)
        worker.moveToThread(thread)
        thread.started.connect(worker.run)
        worker.progress.connect(self._on_stage_progress)
        worker.done.connect(lambda ok, res, w=worker, t=thread, sid=session_id, cdir=cache_dir, sil=silent:
                            self._on_stage_done(ok, res, w, t, sid, cdir, silent=sil))
        thread.finished.connect(thread.deleteLater)
        self._stage_thread = thread
        self._stage_worker = worker
        self.ingest_status_label.setText(
            self.tr("Sincronizando dispositivo (primera pasada)…")
        )
        thread.start()

    def _on_stage_progress(self, message):
        self.ingest_status_label.setText(message)

    def _on_stage_done(self, ok, res, worker, thread, session_id, cache_dir, silent=False):
        if not ok:
            if silent:
                self.ingest_status_label.setText(self.tr("Dispositivo no disponible"))
            else:
                QMessageBox.warning(
                    self, self.tr("Dispositivo"),
                    self.tr("No se pudo sincronizar el dispositivo: %1").arg(str(res)),
                )
                self.ingest_status_label.setText(self.tr("Listo"))
            thread.quit()
            return
        staged = res.get("staged", 0)
        skipped = res.get("skipped", 0)
        errors = res.get("errors", 0)
        self._refresh_source_list()
        self._refresh_sessions_combo()
        self.update_start_button_state()
        self.ingest_status_label.setText(
            self.tr("Dispositivo sincronizado: %1 nuevos, %2 sin cambios, %3 errores.")
            .arg(staged).arg(skipped).arg(errors)
        )
        self._detect_camera_for_session(session_id, cache_dir)
        thread.quit()