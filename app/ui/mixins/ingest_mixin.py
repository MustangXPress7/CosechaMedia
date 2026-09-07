import os
import sys
import json
import time
from PySide6.QtWidgets import (QMessageBox, QFileDialog,
                               QTableWidgetItem, QHeaderView, QDialog, QDialogButtonBox)
from PySide6.QtCore import Qt, QTimer, QThread
from PySide6.QtGui import QColor
from app.core.db import db, WIFI_DEVICE_ID
from app.core.ingestor import (Ingestor, DumpTarget, generate_integrity_report,
                               generate_card_content_report)
from app.core.watcher import FileSystemWatcher
from app.core.metadata_engine import metadata_engine, _is_system_entry
from app.core.notifications import NotificationManager
from app.core.ffmpeg_utils import ffmpeg
from app.core.sd_reader import sd_reader
import app.core.utils as utils
from app.core import translator
from app.core.translator import QtString
from app.ui import theme, icons
import app.core.shoot_inbox as inboxmod
from app.ui.mixins.workers import _TaskWorker


ORG_TYPE_MAP = {
    0: "camera_first",
    1: "date_first",
    2: "camera_only",
    3: "flat",
}


class IngestMixin:
    """Pipeline de ingesta verificada (MD5) y acciones post-ingesta extraídos de MainWindow (quick 260906-ingest-mixin-extraction)."""

    def start_ingest(self):
        if self.current_project_id is None:
            return
        sessions = db.get_sessions(self.current_project_id)
        active = []
        single = self.source_input.currentText().strip()
        if single and os.path.isdir(single):
            active = [{
                "id": None,
                "source_path": single,
                "destination_override": None,
                "folder_name": None,
                "organization_type": None,
                "duration_type": None,
                "default_dispositivo": None,
                "use_metadata_date": None,
                "delicate_mode": None,
            }]
        else:
            active = [
                s for s in sessions
                if s.get("source_path") and os.path.isdir(s["source_path"])
                and s.get("enabled", True)
            ]

        if not active:
            QMessageBox.warning(self, self.tr("Sin orígenes"), self.tr("No hay sesiones con rutas de origen válidas."))
            return

        sources = [s["source_path"] for s in active]
        for s in sources:
            db.save_recent_path(s, "source")
        self._refresh_recent_paths()

        if any(getattr(w, "running", False) for w in self.watchers):
            QMessageBox.information(self, self.tr("Ya en marcha"), self.tr("El monitoreo de la SD ya está activo."))
            return

        folder_name = self.project_folder_name or "Footage"
        if folder_name:
            db.add_footage_folder(folder_name)

        self.table.setRowCount(0)
        self.table.setSortingEnabled(False)
        self.progress_bar.setValue(0)
        self.progress_bar.setFormat("")
        self._file_row_map = {}
        self._processed_count = 0
        self._total_files = 0
        self._unknown_cameras = set()
        self._ingested_videos = []
        self._ingestors = []
        self._ingest_completed = set()

        camera_map = {}
        for s in sessions:
            sp = s.get("source_path")
            cn = s.get("nombre_dispositivo")
            if sp and cn:
                camera_map[os.path.normpath(sp)] = cn
        self._current_camera_map = camera_map

        project_targets = []
        if self.current_project_id is not None:
            for loc in db.dump_locations(self.current_project_id):
                if loc["path"] and os.path.isdir(loc["path"]):
                    project_targets.append(
                        DumpTarget(loc["id"], loc["path"], loc["include_date"], loc["include_camera"])
                    )

        for sess in active:
            sid = sess.get("id")
            s_folder = sess.get("folder_name") or self.project_folder_name or "Footage"
            s_org_raw = sess.get("organization_type")
            s_org = self.project_organization_type if s_org_raw is None else s_org_raw
            s_dur = sess.get("duration_type")
            s_dur = self.project_duration_type if s_dur is None else s_dur
            s_cam = sess.get("default_dispositivo")
            s_cam = self.project_default_dispositivo if s_cam is None else s_cam
            s_date_mode = sess.get("date_mode") or self.project_date_mode or "auto"
            s_use_meta = s_date_mode == "auto"
            s_manual_date = sess.get("manual_date") or (self.project_manual_date if s_date_mode == "manual" else None)
            device_key = sess.get("device_id") or sess.get("source_path") or ""
            dev_delicate = db.get_device_delicate(device_key)
            if dev_delicate is not None:
                s_delicate = bool(dev_delicate)
            else:
                s_delicate = False

            # I-18: Modo de contenido desde la sesión, con WiFi/FTP default a "all"
            s_content_mode = sess.get("content_mode", "all")
            # WiFi y FTP siempre usan "all" (todo el contenido) por compatibilidad
            is_ftp = str(device_key).startswith("ftp:")
            if is_ftp or device_key.startswith("wifi:"):
                s_content_mode = "all"

            s_content_filter = None
            try:
                raw_filter = sess.get("content_filter")
                if raw_filter:
                    s_content_filter = json.loads(raw_filter)
            except (TypeError, ValueError):
                s_content_filter = None

            dest_root = sess.get("destination_override") or self.dest_root
            sess_targets = None
            if not sess.get("destination_override"):
                sess_targets = project_targets or None
            order_val = ORG_TYPE_MAP.get(s_org, "camera_first")

            if sid is not None:
                db.update_session_config(sid, status="active")

            cam_overrides = {}
            try:
                raw_overrides = json.loads(self.project_camera_date_overrides or "{}")
                # Normalizar a dict cam -> fecha para modos manual
                for cam, val in raw_overrides.items():
                    if isinstance(val, dict):
                        if str(val.get("mode", "manual")).lower() == "manual":
                            date_str = val.get("date")
                            if date_str:
                                cam_overrides[cam] = date_str
                    elif isinstance(val, str) and val:
                        cam_overrides[cam] = val
            except Exception:
                cam_overrides = {}
            ing = Ingestor(
                self.current_project_id,
                dest_root,
                folder_name=s_folder,
                use_metadata_date=bool(s_use_meta),
                order_type=order_val,
                duration_type=s_dur,
                default_dispositivo=s_cam,
                delicate_mode=bool(s_delicate),
                session_id=sid,
                camera_map=camera_map,
                manual_date=s_manual_date,
                dump_targets=sess_targets,
                project_master_root=self.dest_root,
                content_filter=s_content_filter,
                content_mode=s_content_mode,
                camera_date_overrides=cam_overrides,
            )
            ing.file_started.connect(
                lambda sp, i=ing: self.on_file_started(sp, ingestor=i)
            )
            ing.copy_progress.connect(
                lambda sp, cb, tb, i=ing: self.on_copy_progress(sp, cb, tb, ingestor=i)
            )
            ing.file_finished.connect(
                lambda sp, dp, ok, md, i=ing: self.on_file_finished(sp, dp, ok, md, ingestor=i)
            )
            ing.ingest_complete.connect(
                lambda stats, i=ing: self._on_ingestor_complete(stats, i)
            )
            ing.camera_rename_needed.connect(self._on_camera_rename_needed)
            self._ingestors.append(ing)

        self.watchers = []
        for idx, sess in enumerate(active):
            ing = self._ingestors[idx]
            watcher = FileSystemWatcher(
                sess["source_path"],
                ing,
                status_callback=self.update_status_from_watcher
            )
            ing.begin_watching(1)
            watcher.start()
            self.watchers.append(watcher)

        self.btn_start.setEnabled(False)
        self.btn_start.setText(self.tr("Procesando..."))
        self.btn_stop.setEnabled(True)
        self.ingest_status_label.setText(self.tr("Procesando %1 ruta(s): %2").arg(len(sources)).arg(', '.join(sources)))
        self._set_status_color("warning", 6)
        self.status_text.setText(self.tr("En progreso"))

    def stop_ingest(self):
        for watcher in self.watchers:
            if watcher:
                watcher.stop()
        self.watchers = []

        for ing in self._ingestors:
            ing.stop()

        # Esperar y limpiar el thread de staging para no dejar un hilo con
        # referencias COM corruptas tras detener la ingesta (D-25).
        if hasattr(self, '_stage_thread') and self._stage_thread and self._stage_thread.isRunning():
            self._stage_thread.quit()
            self._stage_thread.wait(2000)
            self._stage_thread = None
        if hasattr(self, '_stage_worker'):
            self._stage_worker = None

        self.btn_start.setText(self.tr("Iniciar Ingesta"))
        self.btn_start.setEnabled(True)
        self.btn_stop.setEnabled(False)
        self.table.setSortingEnabled(True)
        self.ingest_status_label.setText(self.tr("Ingesta detenida por el usuario"))
        self._set_status_color("danger", 6)
        self.status_text.setText(self.tr("Detenido"))

        self.notification_manager.notify_ingest_stopped()

    def prepare_for_update(self):
        """Stop all background work (ingest, watchers, wifi, polling) before an update.
        Called from AboutDialog before spawning the update helper."""
        # Stop any active ingestion
        self.stop_ingest()
        # Stop WiFi reception
        self._stop_wifi_reception()
        # Stop device polling timer
        if hasattr(self, '_sync_timer') and self._sync_timer.isActive():
            self._sync_timer.stop()
        # Cancel any background staging threads
        if hasattr(self, '_stage_thread') and self._stage_thread and self._stage_thread.isRunning():
            self._stage_thread.quit()
            self._stage_thread.wait(2000)

    def on_file_started(self, source_path, ingestor=None):
        was_sorted = self.table.isSortingEnabled()
        if was_sorted:
            self.table.setSortingEnabled(False)
        row = self.table.rowCount()
        self.table.insertRow(row)

        filename_item = QTableWidgetItem(os.path.basename(source_path))
        filename_item.setFlags(filename_item.flags() & ~Qt.ItemIsEditable)
        self.table.setItem(row, 0, filename_item)

        cam_name = self._camera_for_path(source_path)
        if cam_name:
            cam_text = cam_name
        elif self.project_camera_detection_mode == "manual":
            cam_text = self.tr("Sin nombre")
        else:
            cam_text = self.tr("Detectando...")
        camera_item = QTableWidgetItem(cam_text)
        camera_item.setFlags(camera_item.flags() & ~Qt.ItemIsEditable)
        self.table.setItem(row, 1, camera_item)

        status_item = QTableWidgetItem(self.tr("Copiando..."))
        status_item.setFlags(status_item.flags() & ~Qt.ItemIsEditable)
        self.table.setItem(row, 2, status_item)

        progress_item = QTableWidgetItem("0%")
        progress_item.setFlags(progress_item.flags() & ~Qt.ItemIsEditable)
        self.table.setItem(row, 3, progress_item)

        dest_item = QTableWidgetItem("")
        dest_item.setFlags(dest_item.flags() & ~Qt.ItemIsEditable)
        self.table.setItem(row, 4, dest_item)

        self.table.setCellWidget(row, 5, self._build_remove_file_button(filename_item))

        if was_sorted:
            self.table.setSortingEnabled(True)

        # Con el mismo origen compartido por varias sesiones (fan-out WiFi),
        # cada ingestor tiene su propia fila; si no hay ingestor (llamadas
        # externas/directas) se indexa solo por ruta como antes.
        key = self._file_row_key(source_path, ingestor)
        self._file_row_map[key] = filename_item
        self._total_files += 1
        self.progress_bar.setMaximum(self._total_files)
        self.ingest_status_label.setText(self.tr("Procesando: %1").arg(os.path.basename(source_path)))

    @staticmethod
    def _file_row_key(source_path, ingestor):
        return (id(ingestor), source_path) if ingestor is not None else source_path

    def on_copy_progress(self, source_path, copied_bytes, total_bytes, ingestor=None):
        item = self._file_row_map.get(self._file_row_key(source_path, ingestor))
        if item is None or not total_bytes:
            return
        row = self.table.indexFromItem(item).row()
        pct = int(copied_bytes * 100.0 / total_bytes)
        pct = max(0, min(100, pct))
        progress_item = QTableWidgetItem(f"{pct}%")
        progress_item.setFlags(progress_item.flags() & ~Qt.ItemIsEditable)
        self.table.setItem(row, 3, progress_item)

    def on_file_finished(self, source_path, dest_path, success, metadata=None, ingestor=None):
        item = self._file_row_map.get(self._file_row_key(source_path, ingestor))
        if item is not None:
            row = self.table.indexFromItem(item).row()

            if self.project_camera_detection_mode != "manual" and metadata:
                if metadata.get("metadata_verified") is False:
                    camera_item = QTableWidgetItem(self.tr("⛔ Metadatos no verificados"))
                    camera_item.setToolTip(self.tr("ffprobe no respondió; metadatos no verificados"))
                elif metadata.get("camera_model") != "Unknown":
                    camera_item = QTableWidgetItem(metadata["camera_model"])
                else:
                    # camera_model "Unknown" con metadatos verificados: no
                    # sobreescribir con "Unknown"; conservar el valor que ya
                    # mostraba la celda (nombre/Detectando...) para que
                    # camera_item SIEMPRE esté enlazado (evita UnboundLocalError).
                    existing = self.table.item(row, 1)
                    camera_item = existing if existing is not None else QTableWidgetItem("")
                self.table.setItem(row, 1, camera_item)

            if success:
                status = self.tr("Completado")
                text_color = QColor(theme.color("success"))
            else:
                status = self.tr("Error")
                text_color = QColor(theme.color("danger"))

            status_item = QTableWidgetItem(status)
            status_item.setForeground(text_color)
            self.table.setItem(row, 2, status_item)

            progress_item = QTableWidgetItem("100%" if success else "0%")
            progress_item.setForeground(text_color if success else QColor(theme.color("danger")))
            progress_item.setFlags(progress_item.flags() & ~Qt.ItemIsEditable)
            self.table.setItem(row, 3, progress_item)

            if dest_path:
                dest_item = QTableWidgetItem(dest_path)
                self.table.setItem(row, 4, dest_item)

        if success and dest_path:
            ftype = metadata_engine.get_file_type_info(dest_path)
            if ftype.get("type") == "video":
                root = ingestor.destination_root if ingestor else self.dest_root
                self._ingested_videos.append((dest_path, root))
            # Un archivo recibido por WiFi ya está en su destino: lo sacamos de
            # la caché para que no se vuelva a ingerir en la próxima pasada.
            if self._is_inbox_cache_path(source_path):
                self._remove_ingested_wifi_source(source_path)

        self._processed_count += 1
        self.progress_bar.setValue(self._processed_count)

        self.lbl_files_processed.setText(self.tr("%1 procesados").arg(self._processed_count))
        self.lbl_files_pending.setText(self.tr("%1 pendientes").arg(max(0, self._total_files - self._processed_count)))

    def _on_ingestor_complete(self, stats, ingestor):
        self._ingest_completed.add(id(ingestor))
        if ingestor.session_id is not None:
            db.update_session_config(ingestor.session_id, status="completed")
        if len(self._ingest_completed) >= len(self._ingestors):
            self._finalize_ingest()

    def _finalize_ingest(self):
        try:
            for watcher in self.watchers:
                if watcher:
                    watcher.stop()
            self.watchers = []

            for ing in self._ingestors:
                ing.stop()

            self.btn_start.setText(self.tr("Iniciar Ingesta"))
            self.btn_start.setEnabled(True)
            self.btn_stop.setEnabled(False)

            total_processed = sum(ing.get_stats().get("processed", 0) for ing in self._ingestors)
            total_errors = sum(ing.get_stats().get("errors", 0) for ing in self._ingestors)
            total_skipped = sum(ing.get_stats().get("skipped", 0) for ing in self._ingestors)
            self.progress_bar.setFormat(self.tr("%v / %m archivos"))
            self.ingest_status_label.setText(
                self.tr("Ingesta completada: %1 procesados, %2 errores, %3 omitidos.")
                .arg(total_processed).arg(total_errors).arg(total_skipped)
            )

            self._set_status_color("success", 6)
            self.status_text.setText(self.tr("Completado"))

            stats = {
                "processed": total_processed,
                "errors": total_errors,
                "skipped": total_skipped,
            }
            if total_errors > 0:
                self.notification_manager.notify_ingest_failed(stats)
            else:
                self.notification_manager.notify_ingest_complete(stats)

            self._refresh_sessions_combo()
            self._post_ingest_rename_dialog()
            self.table.setSortingEnabled(True)

            if total_errors == 0:
                # Limpia la caché WiFi que haya quedado (ya ingerida).
                for ing in self._ingestors:
                    if ing.session_id is not None:
                        self._clear_wifi_cache(ing.session_id)

            can_destroy = total_errors == 0
            blocked = []
            if self.chk_format_sources.isChecked() and not can_destroy:
                blocked.append(self.tr("formateo de orígenes"))
            if self.chk_shutdown.isChecked() and not can_destroy:
                blocked.append(self.tr("apagado del equipo"))
            if blocked:
                QMessageBox.warning(
                    self, self.tr("Acciones posteriores bloqueadas"),
                    self.tr("Hay errores en la ingesta. Por seguridad, se han bloqueado las siguientes acciones:\n• %1")
                    .arg("\n• ".join(blocked))
                )

            self._pending_actions = []
            if self.chk_format_sources.isChecked() and can_destroy:
                self._pending_actions.append("format")
            if self.project_generate_proxies:
                self._pending_actions.append("proxies")
            if self.chk_generate_report.isChecked():
                self._pending_actions.append("report")
            if self.chk_shutdown.isChecked() and can_destroy:
                self._pending_actions.append("shutdown")
            self._run_next_post_ingest_action()
        except Exception as e:
            print(f"Error al finalizar la ingesta: {e}")
            self.notification_manager.notify_ingest_failed({})

    def _run_next_post_ingest_action(self):
        while True:
            if not self._pending_actions:
                self.btn_start.setText(self.tr("Iniciar Ingesta"))
                self.btn_start.setEnabled(True)
                return
            action = self._pending_actions[0]
            if action == "format":
                started = self._format_sources_after_ingest()
            elif action == "proxies":
                started = self._generate_proxies_after_ingest()
            elif action == "report":
                self._pending_actions.pop(0)
                self._generate_report_after_ingest()
                continue
            elif action == "shutdown":
                self._pending_actions.pop(0)
                self._shutdown_computer()
                continue
            else:
                started = False
            self._pending_actions.pop(0)
            if started:
                return

    def _is_managed_source_path(self, path):
        """True si ``path`` es una caché gestionada (WiFi/FTP/MTP), no editable
        por el usuario y nunca formateable."""
        if not path:
            return False
        p = os.path.normpath(os.path.abspath(path))
        data_root = os.path.normpath(os.path.abspath(os.path.dirname(db.db_path)))
        for sub in ("inbox", "device_cache"):
            root = os.path.join(data_root, sub)
            if p.startswith(root + os.sep) or p == root:
                return True
        return False

    def _is_managed_session(self, session):
        """True si la sesión es auto-gestionada (WiFi/FTP/MTP): su origen es la
        caché local del dispositivo, no un destino elegido por el usuario."""
        did = (session or {}).get("device_id") or ""
        if did.startswith("wifi:") or did.startswith("ftp:"):
            return True
        return self._is_managed_source_path((session or {}).get("source_path"))

    def _format_candidate_paths(self):
        """Rutas de unidades extraíbles reales y no gestionadas: las únicas que
        tiene sentido formatear al acabar la ingesta."""
        if self.current_project_id is None:
            return []
        return [p for p in self._source_paths
                if utils.is_removable_drive(p) and not self._is_managed_source_path(p)]

    def _update_format_sources_state(self):
        """Desactiva «Formatear orígenes» cuando no hay ninguna unidad extraíble
        formateable (p. ej. proyectos solo-WiFi)."""
        has_candidates = bool(self._format_candidate_paths())
        self.chk_format_sources.setEnabled(has_candidates)
        if not has_candidates and self.chk_format_sources.isChecked():
            self.chk_format_sources.setChecked(False)
        self.combo_format_mode.setEnabled(
            has_candidates and self.chk_format_sources.isChecked())

    def _format_sources_after_ingest(self) -> bool:
        if sys.platform != "win32":
            QMessageBox.information(
                self, self.tr("Formatear orígenes"),
                self.tr("El formateo de tarjetas solo está disponible en Windows.")
            )
            return False
        if not self._source_paths:
            QMessageBox.information(self, self.tr("Formatear orígenes"), self.tr("No hay orígenes que formatear."))
            return False
        mode_idx = self.combo_format_mode.currentIndex()
        mode = self.tr("completo") if mode_idx == 1 else self.tr("rápido")
        removable = self._format_candidate_paths()
        skipped = [p for p in self._source_paths if p not in removable]
        if not removable:
            QMessageBox.warning(
                self, self.tr("Formatear orígenes"),
                self.tr("Ninguno de los orígenes es una unidad extraíble. No se formateará nada.")
            )
            return False
        lines = [self.tr("Se formatearán las unidades extraíbles (modo %1):").arg(mode)]
        lines += removable
        if skipped:
            lines.append(self.tr("\nSe omitirán (no son unidades extraíbles):"))
            lines += skipped
        reply = QMessageBox.question(
            self, self.tr("Formatear orígenes"),
            "\n".join(lines) + self.tr("\n\n¿Continuar?"),
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        if reply != QMessageBox.Yes:
            return False
        self.btn_start.setEnabled(False)
        self.btn_start.setText(self.tr("Formateando..."))
        self._run_background(
            _format_sources_worker, self._on_format_finished,
            removable, quick=(mode_idx != 1)
        )
        return True

    def _on_format_finished(self, success, payload):
        if not success:
            QMessageBox.critical(self, self.tr("Formatear"), self.tr("No se pudo completar el formateo:\n%1").arg(str(payload)))
        else:
            failed = [f"{p}: {e}" for p, ok, e in payload if not ok]
            ok_count = sum(1 for _, ok, _ in payload if ok)
            if failed:
                self.ingest_status_label.setText(self.tr("Formateados %1/%2 con errores").arg(ok_count).arg(len(payload)))
                QMessageBox.warning(
                    self, self.tr("Formatear"),
                    self.tr("Formateados %1/%2.\nErrores:\n%3").arg(ok_count).arg(len(payload)).arg("\n".join(failed))
                )
            else:
                self.ingest_status_label.setText(self.tr("Orígenes formateados: %1/%2").arg(ok_count).arg(len(payload)))
                QMessageBox.information(
                    self, self.tr("Formatear"),
                    self.tr("Orígenes formateados correctamente: %1/%2.").arg(ok_count).arg(len(payload))
                )
        self._run_next_post_ingest_action()

    def _shutdown_computer(self):
        reply = QMessageBox.question(
            self, self.tr("Apagar ordenador"),
            self.tr("Todas las tareas han finalizado. ¿Apagar el ordenador ahora?"),
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        if reply != QMessageBox.Yes:
            return
        import subprocess
        try:
            if sys.platform.startswith("win"):
                subprocess.run(["shutdown", "/s", "/t", "10"], check=False)
            elif sys.platform == "darwin":
                subprocess.run(["sudo", "shutdown", "-h", "+1"], check=False)
            else:
                subprocess.run(["shutdown", "-h", "+1"], check=False)
            self.ingest_status_label.setText(self.tr("Apagado programado."))
        except Exception as e:
            QMessageBox.warning(self, self.tr("Apagar"), self.tr("No se pudo programar el apagado:\n%1").arg(str(e)))

    def _generate_report_after_ingest(self):
        """Genera CSV de integridad para todas las sesiones de la ingesta."""
        from app.core.ingestor import generate_integrity_report
        if self.current_project_id is None:
            return
        sessions = db.get_sessions(self.current_project_id)
        active = [s for s in sessions if s.get("source_path")]
        if not active:
            return
        import os
        for session in active:
            default_name = f"integridad_{session.get('name', 'sesion')}.csv"
            dest = os.path.join(session.get("source_path", ""), default_name)
            # Si no se puede escribir en el origen, usar el home
            if not os.access(os.path.dirname(dest) or os.path.expanduser("~"), os.W_OK):
                dest = os.path.join(os.path.expanduser("~"), default_name)
            generate_integrity_report(session["id"], dest)
        self.ingest_status_label.setText(self.tr("Reporte CSV generado."))

    def update_status_from_watcher(self, message):
        self.ingest_status_label.setText(message)

    def _run_background(self, fn, on_finished, *args, **kwargs):
        """Lanza `fn` en un QThread. on_finished(success, payload) corre en la UI."""
        thread = QThread(self)
        worker = _TaskWorker(fn, *args, **kwargs)
        worker.moveToThread(thread)
        thread.started.connect(worker.run)
        worker.progress.connect(self.ingest_status_label.setText)
        worker.finished.connect(thread.quit)
        worker.finished.connect(lambda ok, res, t=thread, w=worker: self._cleanup_background(t, w))
        thread.finished.connect(thread.deleteLater)
        worker.finished.connect(on_finished)
        self._background_tasks.append((thread, worker))
        thread.start()

    def _cleanup_background(self, thread, worker):
        self._background_tasks = [(t, w) for (t, w) in self._background_tasks if t is not thread]

    def _show_table_context_menu(self, pos):
        context_menu = QMenu(self)
        clear_action = context_menu.addAction(self.tr("Eliminar completados"))
        clear_action.triggered.connect(self._clear_completed_rows)
        context_menu.addSeparator()
        integrity_action = context_menu.addAction(self.tr("Exportar reporte de integridad (CSV)"))
        integrity_action.triggered.connect(self._export_integrity_report)
        source_path = self._current_source_path()
        if source_path and os.path.isdir(source_path):
            content_action = context_menu.addAction(self.tr("Exportar contenido de tarjeta (CSV)"))
            content_action.triggered.connect(self._export_card_content_report)
        context_menu.exec(self.table.viewport().mapToGlobal(pos))

    def _clear_completed_rows(self):
        """Quita de la tabla de ingesta las filas cuyo estado es «Completado»."""
        done_text = self.tr("Completado")
        was_sorted = self.table.isSortingEnabled()
        self.table.setSortingEnabled(False)
        try:
            for r in range(self.table.rowCount() - 1, -1, -1):
                status_item = self.table.item(r, 2)
                if status_item and status_item.text() == done_text:
                    self.table.removeRow(r)
        finally:
            self.table.setSortingEnabled(was_sorted)

    def _export_integrity_report(self):
        """Exporta CSV de integridad (post-dump) para la sesión activa."""
        if self.current_project_id is None:
            return
        sessions = db.get_sessions(self.current_project_id)
        active = [s for s in sessions if s.get("source_path")]
        if not active:
            QMessageBox.information(self, self.tr("Reporte"),
                                    self.tr("No hay sesiones con origen para exportar."))
            return
        session = active[0]
        default_name = f"integridad_{session.get('name', 'sesion')}.csv"
        path, _ = QFileDialog.getSaveFileName(
            self, self.tr("Guardar reporte de integridad"),
            os.path.join(os.path.expanduser("~"), default_name),
            "CSV (*.csv)")
        if not path:
            return
        from app.core.ingestor import generate_integrity_report
        ok = generate_integrity_report(session["id"], path)
        if ok:
            QMessageBox.information(self, self.tr("Reporte"),
                                    self.tr("Reporte guardado en:\n%1").arg(path))
        else:
            QMessageBox.warning(self, self.tr("Reporte"),
                                self.tr("No se pudo generar el reporte."))

    def _export_card_content_report(self):
        """Exporta CSV de contenido de tarjeta (pre-dump) para el origen activo."""
        source_path = self._current_source_path()
        if not source_path or not os.path.isdir(source_path):
            QMessageBox.information(self, self.tr("Reporte"),
                                    self.tr("No se detectó una ruta de origen válida."))
            return
        base = os.path.basename(os.path.normpath(source_path)) or "tarjeta"
        default_name = f"contenido_{base}.csv"
        path, _ = QFileDialog.getSaveFileName(
            self, self.tr("Guardar contenido de tarjeta"),
            os.path.join(os.path.expanduser("~"), default_name),
            "CSV (*.csv)")
        if not path:
            return
        from app.core.ingestor import generate_card_content_report
        ok = generate_card_content_report(source_path, path)
        if ok:
            QMessageBox.information(self, self.tr("Reporte"),
                                    self.tr("Contenido exportado en:\n%1").arg(path))
        else:
            QMessageBox.warning(self, self.tr("Reporte"),
                                self.tr("No se pudo exportar el contenido."))

    def _proxy_resolution_height(self) -> int:
        return int(self.project_proxy_resolution.replace("p", "")) if self.project_proxy_resolution else 720

    def _generate_proxies_after_ingest(self) -> bool:
        videos = list(dict.fromkeys(self._ingested_videos))
        if not videos:
            QMessageBox.information(self, self.tr("Proxies"), self.tr("No se encontraron clips de video en la ingesta."))
            return False
        height = self._proxy_resolution_height()
        reply = QMessageBox.question(
            self, self.tr("Generar proxies"),
            self.tr("Generar proxies %1p para %2 clips de video?").arg(height).arg(len(videos)),
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        if reply != QMessageBox.Yes:
            return False
        jobs = []
        for item in videos:
            path, root = item if isinstance(item, tuple) else (item, self.dest_root)
            jobs.append((path, root))
        self.btn_start.setEnabled(False)
        self.btn_start.setText(self.tr("Generando proxies..."))
        self._run_background(
            _generate_proxies_worker, self._on_proxies_finished,
            jobs, height
        )
        return True

    def _on_proxies_finished(self, success, payload):
        if not success:
            QMessageBox.critical(self, self.tr("Proxies"), self.tr("No se pudieron generar los proxies:\n%1").arg(payload))
        else:
            QMessageBox.information(self, self.tr("Proxies"), self.tr("Proxies generados: %1").arg(payload))
        self._run_next_post_ingest_action()