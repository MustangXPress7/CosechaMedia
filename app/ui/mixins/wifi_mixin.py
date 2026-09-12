import os
import json
from PySide6.QtWidgets import QMessageBox, QDialog, QSystemTrayIcon
from app.core.db import db, WIFI_DEVICE_ID
from app.core.ingestor import Ingestor, DumpTarget
from app.core.metadata_engine import _is_system_entry
from app.core import translator
from app.ui import theme
from app.ui import icons
from app.ui.wifi_panel import SenderEditDialog, ShootInboxPanel
import app.core.shoot_inbox as inboxmod

class WifiMixin:
    """Métodos del flujo WiFi/PairDrop extraídos de MainWindow (quick 260906-ci2)."""

    def _toggle_wifi_folder_mode(self, session, btn):
        sid = session["id"]
        current = bool(session.get("folder_mode"))
        new_val = 0 if current else 1
        db.update_session_config(sid, folder_mode=new_val)
        session["folder_mode"] = new_val
        icons.apply(btn, "folder" if new_val else "copy", size=14)
        btn.setToolTip(
            self.tr("Modo: enviar archivos sueltos") if not new_val
            else self.tr("Modo: enviar carpeta entera"))
        if self._wifi_server is not None and self._wifi_server.running:
            self._wifi_server.folder_mode = bool(new_val)
        if self._wifi_panel is not None:
            self._wifi_panel.refresh()

    def _show_wifi_qr_for_sender(self, sender_name):
        """Abre la ventana QR mostrando el dispositivo de un origen WiFi.

        Fix D-07: no llamar a _sync_wifi_sessions() aquí porque refresca la
        tabla de orígenes y hace que el origen WiFi desaparezca momentáneamente.
        La sincronización de sesiones WiFi se hace en otros momentos (cambio de
        proyecto, auto-sync, etc.).
        """
        if self.current_project_id is None:
            return
        if not self._ensure_wifi_server():
            return
        # No llamar a _sync_wifi_sessions() para evitar refresh destructivo (D-07)
        self._show_wifi_panel()
        if self._wifi_panel is not None:
            self._wifi_panel.select_sender(sender_name)
        self._ensure_wifi_ingestion()

    def _bind_wifi_sender(self, sender_id, session_id=None):
        """Convierte una sesión en la sesión gestionada de un remitente WiFi.

        El binding es aditivo: el mismo remitente puede volcar en varias
        sesiones del proyecto (cada una con su propio destino/configuración).
        Con ``session_id`` (selector de sesión) convierte esa sesión concreta;
        sin él (origen nuevo) reutiliza una sesión sin origen o crea la WiFi.
        """
        if self.current_project_id is None:
            return
        # Look up sender by ID (preferred) or name (fallback for backward compat)
        sender = None
        for s in db.list_inbox_senders():
            if str(s["id"]) == str(sender_id) or s["name"] == sender_id:
                sender = s
                break
        if sender is None:
            return
        sender_name = sender["name"]
        alias = inboxmod.sanitize_alias(sender_name)
        cache = inboxmod.wifi_cache_dir(sender_name)
        sessions = db.get_sessions(self.current_project_id)

        def _wifi_sessions():
            return [s for s in db.get_sessions(self.current_project_id)
                    if (s.get("device_id") or "").startswith("wifi:")
                    and s.get("device_folder") == alias]

        existing = _wifi_sessions()
        if session_id is None:
            if existing:
                session_id = existing[0]["id"]
            else:
                no_source = next((s for s in sessions if not s.get("source_path")), None)
                if no_source is not None:
                    session_id = no_source["id"]
                else:
                    session_id = db.get_or_create_wifi_session(
                        self.current_project_id, sender_name, cache, "")
                    self._after_bind(session_id)
                    return
        target = next((s for s in sessions if s["id"] == session_id), None)
        if target is None:
            return
        # Cambio de origen: si la sesión estaba ligada a OTRO remitente, se
        # desliga de él (sus demás sesiones no se tocan) antes de ligar el nuevo.
        cur_did = target.get("device_id") or ""
        cur_folder = target.get("device_folder") or ""
        if cur_did.startswith("wifi:") and cur_folder and cur_folder != alias:
            db.update_session_config(session_id, device_id="", device_folder="",
                                     nombre_dispositivo=None)
        other = next((s for s in _wifi_sessions() if s["id"] != session_id), None)
        if other is not None:
            QMessageBox.information(
                self, self.tr("Origen compartido"),
                self.tr("El remitente '%1' ya está asignado a la sesión #%2.\n"
                        "Se añadirá también a la sesión #%3.")
                .arg(sender_name).arg(other["id"]).arg(session_id))
        db.update_session_config(
            session_id, device_id=WIFI_DEVICE_ID, device_folder=alias,
            nombre_dispositivo=sender_name, source_path=cache, enabled=1)
        self._after_bind(session_id)

    def _after_bind(self, session_id):
        self._populate_source_paths_from_sessions()
        self._refresh_source_list()
        self._refresh_sessions_combo()
        idx = self.sessions_combo.findData(session_id)
        if idx >= 0:
            self.sessions_combo.setCurrentIndex(idx)
        self.update_start_button_state()
        self.ingest_status_label.setText(
            self.tr("Origen WiFi asignado a la sesión #%1").arg(session_id))

    def _pick_wifi_source(self):
        # Sin ventana intermedia: el QR se genera directamente.
        self._open_wifi_panel(force_new_sender=True)

    # -- WiFi / PairDrop: origen en la tabla + ventana flotante QR --------

    def _open_wifi_panel(self, force_new_sender: bool = False):
        """Configura un QR (nuevo remitente) y abre la ventana flotante.

        Con ``force_new_sender`` (botón WiFi…) siempre pide crear un nuevo
        remitente (un QR nuevo), en vez de reabrir el existente.
        """
        if self.current_project_id is None:
            return
        if not self._ensure_wifi_server():
            return
        if force_new_sender:
            sender = self._prompt_wifi_sender()
            if sender is None:
                return
        elif not db.list_inbox_senders():
            # Si no hay remitentes, pide crear el primero (un origen WiFi más).
            if self._prompt_wifi_sender() is None:
                return
            sender = db.list_inbox_senders()[-1]["name"]
        else:
            sender = None
        self._sync_wifi_sessions()
        self._show_wifi_panel()
        if self._wifi_panel is not None and sender:
            self._wifi_panel.select_sender(sender)
        self._ensure_wifi_ingestion()

    def _prompt_wifi_sender(self):
        """Abre el diálogo de nuevo remitente; devuelve su nombre o None."""
        if self.current_project_id is None:
            QMessageBox.information(
                self, self.tr("Sin proyecto"),
                self.tr("Selecciona un proyecto primero."))
            return None
        dlg = SenderEditDialog(
            self,
            title=self.tr("Añadir dispositivo WiFi"),
            name_label=self.tr(
                "Nombre del dispositivo (aparecerá en el código QR):"),
            name_hint=self.tr("Ej.: Móvil de Joan"),
        )
        if dlg.exec() != QDialog.Accepted:
            return None
        name = dlg.name_edit.text().strip()
        if not name:
            return None
        db.add_inbox_sender(name)
        self._sync_wifi_sessions()
        return name

    def _ensure_wifi_server(self) -> bool:
        if self._wifi_server is not None and self._wifi_server.running:
            return True
        folder_mode = self._get_wifi_folder_mode()
        self._wifi_server = inboxmod.ShootInboxServer(
            page_dark=(theme.get_theme() != "light"),
            folder_mode=folder_mode)
        try:
            self._wifi_server.start()
            # Wait briefly for server to be ready to accept connections
            import time
            for _ in range(50):  # Up to 500ms
                if self._wifi_server.running:
                    try:
                        # Test if we can connect to the server
                        import socket
                        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                        sock.settimeout(0.1)
                        result = sock.connect_ex(('127.0.0.1', self._wifi_server.port))
                        sock.close()
                        if result == 0:
                            break
                    except Exception:
                        pass
                time.sleep(0.01)
        except OSError as e:
            QMessageBox.warning(
                self, self.tr("WiFi"),
                self.tr("No se pudo iniciar el servidor: %1").arg(str(e)))
            self._wifi_server = None
            return False
        return True

    def _get_wifi_folder_mode(self) -> bool:
        if self.current_project_id is None:
            return False
        sessions = [s for s in db.get_sessions(self.current_project_id)
                    if s.get("device_id") == "wifi:pairdrop"]
        for s in sessions:
            if s.get("folder_mode"):
                return True
        return False

    def _show_wifi_panel(self):
        if self._wifi_panel is None:
            self._wifi_panel = ShootInboxPanel(self)
            self._wifi_panel.received.connect(self._on_wifi_file_received)
            self._wifi_panel.stop_requested.connect(self._stop_wifi_reception)
            self._wifi_panel.resume_requested.connect(self._resume_wifi_reception)
        if self._wifi_server is not None and self._wifi_server.running:
            self._wifi_panel.attach_server(self._wifi_server)
        self._wifi_panel.refresh()
        self._wifi_panel.show()
        self._wifi_panel.raise_()
        self._wifi_panel.activateWindow()

    def _sync_wifi_sessions(self):
        """Crea/elimina las sesiones fuente WiFi del proyecto (una por remitente)
        y refresca la tabla de orígenes."""
        if self.current_project_id is None:
            return
        # Filtrar remitentes creados después de la creación del proyecto para
        # evitar heredar QRs de proyectos anteriores.
        conn = db.get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT created_at FROM projects WHERE id = ?', (self.current_project_id,))
        proj_row = cursor.fetchone()
        conn.close()
        project_created_at = proj_row[0] if proj_row else None
        all_senders = db.list_inbox_senders()
        senders = []
        for s in all_senders:
            s_created = s.get("created_at")
            if project_created_at is None or (s_created and s_created >= project_created_at):
                senders.append(s)
        existing = [(s["device_folder"], s["id"])
                    for s in db.list_wifi_sessions(self.current_project_id)]
        keep = set()
        for s in senders:
            folder = inboxmod.sanitize_alias(s["name"])
            cache = inboxmod.wifi_cache_dir(s["name"])
            # La ubicación/destino del dispositivo NO se propaga entre
            # proyectos: cada proyecto vuelca a su propia ruta maestra.
            sid = db.get_or_create_wifi_session(
                self.current_project_id, s["name"], cache, "")
            keep.add(folder)
            if cache not in self._source_paths:
                self._source_paths.append(cache)
        # Elimina TODAS las sesiones de remitentes que ya no existen (un
        # remitente puede estar compartido por varias sesiones del proyecto).
        for folder, sid in existing:
            if folder not in keep:
                db.delete_session(sid)
                ing = self._wifi_ingestors.pop(sid, None)
                if ing is not None:
                    ing.stop()
        self._populate_source_paths_from_sessions()
        self._refresh_source_list()
        self._refresh_sessions_combo()
        self.update_start_button_state()

    def _ingestor_for_wifi_session(self, session) -> "Ingestor":
        """Construye un Ingestor configurado para una sesión WiFi concreta."""
        from app.ui.main_window import ORG_TYPE_MAP
        sid = session["id"]
        s_folder = session.get("folder_name") or self.project_folder_name or "Footage"
        s_org_raw = session.get("organization_type")
        s_org = self.project_organization_type if s_org_raw is None else s_org_raw
        s_dur = session.get("duration_type")
        s_dur = self.project_duration_type if s_dur is None else s_dur
        s_cam = session.get("default_dispositivo")
        s_cam = self.project_default_dispositivo if s_cam is None else s_cam
        s_use_meta = session.get("use_metadata_date")
        s_use_meta = self.project_use_metadata_date if s_use_meta is None else s_use_meta
        device_key = session.get("device_id") or session.get("source_path") or ""
        dev_delicate = db.get_device_delicate(device_key)
        if dev_delicate is not None:
            s_delicate = bool(dev_delicate)
        else:
            s_delicate = False
        s_content_filter = None
        try:
            raw_filter = session.get("content_filter")
            if raw_filter:
                s_content_filter = json.loads(raw_filter)
        except (TypeError, ValueError):
            s_content_filter = None
        dest_root = session.get("destination_override") or self.dest_root
        sess_targets = None
        if not session.get("destination_override"):
            sess_targets = [DumpTarget(l["id"], l["path"], l["include_date"], l["include_camera"])
                            for l in db.dump_locations(self.current_project_id)
                            if l["path"] and os.path.isdir(l["path"])] or None
        camera_map = getattr(self, "_current_camera_map", None) or {}
        camera_map = dict(camera_map)
        # El origen WiFi se etiqueta con la cámara del remitente (su nombre),
        # aunque nunca se haya pulsado «Iniciar Ingesta» (que es donde se
        # construye el mapa global). Así los subdirectorios de la caché del
        # remitente no caen en "Unknown".
        sp = session.get("source_path")
        cn = session.get("nombre_dispositivo")
        if sp and cn:
            camera_map[os.path.normpath(sp)] = cn
        ing = Ingestor(
            self.current_project_id, dest_root,
            folder_name=s_folder, use_metadata_date=bool(s_use_meta),
            order_type=ORG_TYPE_MAP.get(s_org, "camera_first"),
            duration_type=s_dur, default_dispositivo=s_cam,
            delicate_mode=bool(s_delicate), session_id=sid,
            camera_map=camera_map,
            manual_date=self.project_date.toString("yyyy-MM-dd"),
            dump_targets=sess_targets, project_master_root=self.dest_root,
            content_filter=s_content_filter,
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
            lambda stats, i=ing: self._on_wifi_ingestor_complete(stats, i)
        )
        ing.camera_rename_needed.connect(self._on_camera_rename_needed)
        return ing

    def _on_wifi_ingestor_complete(self, stats, ingestor):
        """Al terminar la ingesta WiFi de un remitente sin errores, vacía la
        caché que quede (archivos ya ingeridos en pasadas anteriores).

        Solo se vacía cuando es el último ingestor activo del remitente: con
        el mismo origen compartido por varias sesiones, la primera en terminar
        no puede borrar la caché antes de que las demás la hayan ingerido.
        """
        if ingestor.session_id is not None and (stats.get("errors") or 0) == 0:
            if self._wifi_cache_safe_to_clear(ingestor):
                self._clear_wifi_cache(ingestor.session_id)

    def _wifi_cache_safe_to_clear(self, ingestor):
        """True si ningún otro ingestor del mismo remitente sigue activo."""
        sid = ingestor.session_id
        if sid is None or self.current_project_id is None:
            return True
        session = next((s for s in db.list_wifi_sessions(self.current_project_id)
                        if s["id"] == sid), None)
        if not session:
            return True
        folder = session["device_folder"]
        for s in db.list_wifi_sessions(self.current_project_id):
            if s["device_folder"] != folder or s["id"] == sid:
                continue
            other = self._wifi_ingestors.get(s["id"])
            if other is not None and not other.is_idle():
                return False
        return True

    def _start_wifi_ingestor(self, sid):
        if sid in self._wifi_ingestors:
            return self._wifi_ingestors[sid]
        session = db.get_session(sid)
        if not session or not session.get("source_path"):
            return None
        if not session.get("enabled", True):
            return None
        ing = self._ingestor_for_wifi_session(session)
        self._wifi_ingestors[sid] = ing
        self._scan_wifi_cache(sid, session["source_path"])
        return ing

    def _scan_wifi_cache(self, sid, cache_dir):
        """Ingiere los archivos ya presentes en la caché del remitente."""
        if not cache_dir or not os.path.isdir(cache_dir):
            return
        ing = self._wifi_ingestors.get(sid)
        if ing is None:
            return
        for root, dirs, files in os.walk(cache_dir):
            dirs[:] = [d for d in dirs if not _is_system_entry(d)]
            for f in files:
                if _is_system_entry(f) or f.startswith("."):
                    continue
                ing.handle_new_file(os.path.join(root, f))

    def _ensure_wifi_ingestion(self):
        """Arranca un Ingestor por cada sesión WiFi y escanea la caché."""
        if self.current_project_id is None:
            return
        for s in db.list_wifi_sessions(self.current_project_id):
            self._start_wifi_ingestor(s["id"])

    def _is_inbox_cache_path(self, path):
        """True si ``path`` está dentro de la caché WiFi (``data/inbox``)."""
        root = os.path.abspath(inboxmod.inbox_root(db))
        npath = os.path.abspath(path)
        return npath != root and npath.startswith(root + os.sep)

    def _remove_ingested_wifi_source(self, source_path):
        """Borra de la caché un archivo recibido por WiFi ya ingerido y poda
        las carpetas vacías hasta la caché de su remitente."""
        if not self._is_inbox_cache_path(source_path):
            return
        try:
            if os.path.isfile(source_path):
                os.remove(source_path)
        except OSError:
            return
        root = os.path.abspath(inboxmod.inbox_root(db))
        parent = os.path.dirname(os.path.abspath(source_path))
        while parent and parent != root and os.path.isdir(parent):
            try:
                os.rmdir(parent)
            except OSError:
                break
            parent = os.path.dirname(parent)

    def _clear_wifi_cache(self, session_id):
        """Borra los archivos restantes de la caché de un remitente (ya
        ingeridos en una pasada anterior) y poda sus directorios vacíos."""
        sessions = db.list_wifi_sessions(self.current_project_id) \
            if self.current_project_id is not None else []
        session = next((s for s in sessions if s["id"] == session_id), None)
        cache = (session or {}).get("source_path")
        if not cache or not os.path.isdir(cache):
            return
        root = os.path.abspath(cache)
        for base, dirs, files in os.walk(root, topdown=False):
            for f in files:
                try:
                    os.remove(os.path.join(base, f))
                except OSError:
                    pass
            try:
                os.rmdir(base)
            except OSError:
                pass

    def _on_wifi_file_received(self, alias, path, size):
        # Aviso inmediato (sonido + bandeja) aunque el proyecto no esté
        # seleccionado: el archivo ya está en la caché del remitente.
        self._notify_wifi_file_received(alias, path, size)
        if self.current_project_id is None:
            return
        for s in db.list_wifi_sessions(self.current_project_id):
            if s["device_folder"] != alias:
                continue
            if s["id"] not in self._wifi_ingestors:
                self._start_wifi_ingestor(s["id"])
            ing = self._wifi_ingestors.get(s["id"])
            if ing is not None:
                ing.handle_new_file(path)

    def _notify_wifi_file_received(self, alias, path, size):
        """Alerta al llegar un archivo por WiFi: sonido (si está habilitado) y
        globo en la bandeja del sistema para que el operador lo note aunque la
        ventana principal esté detrás de otras apps."""
        try:
            filename = os.path.basename(path)
            size_txt = self._format_size(size)
            self.notification_manager.notify_wifi_file_received()
            tray = getattr(self, "_tray", None)
            if tray is not None:
                tray.showMessage(
                    self.tr("Archivo recibido por WiFi"),
                    self.tr("Recibido de %1: %2 (%3).")
                    .arg(alias).arg(filename).arg(size_txt),
                    QSystemTrayIcon.Information, 4000)
        except Exception as e:
            print(f"Error notificando archivo WiFi recibido: {e}")

    @staticmethod
    def _format_size(size):
        size = float(size)
        for unit in ("B", "KB", "MB", "GB", "TB"):
            if size < 1024 or unit == "TB":
                return f"{size:.0f} {unit}" if unit == "B" else f"{size:.1f} {unit}"
            size /= 1024
        return f"{size:.0f} B"

    def _stop_wifi_reception(self):
        for ing in self._wifi_ingestors.values():
            try:
                ing.stop()
            except Exception:
                pass
        self._wifi_ingestors = {}
        if self._wifi_server is not None:
            try:
                self._wifi_server.stop()
            except Exception:
                pass
            self._wifi_server = None
        if self._wifi_panel is not None:
            self._wifi_panel.refresh()
            self._wifi_panel.set_server_status(
                self.tr("Recepción detenida. Pulsa «Reanudar» para continuar."))
        self.ingest_status_label.setText(self.tr("Recepción WiFi detenida."))

    def _resume_wifi_reception(self):
        if self.current_project_id is None:
            return
        if not self._ensure_wifi_server():
            return
        self._show_wifi_panel()
        self._ensure_wifi_ingestion()
        if self._wifi_panel is not None:
            self._wifi_panel.refresh()
            self._wifi_panel.set_server_status(
                self.tr("Recepción WiFi reanudada."))
        self.ingest_status_label.setText(self.tr("Recepción WiFi reanudada."))

    def _reset_wifi_ingestors(self):
        for ing in self._wifi_ingestors.values():
            try:
                ing.stop()
            except Exception:
                pass
        self._wifi_ingestors = {}
