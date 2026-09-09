import os
import json
from PySide6.QtWidgets import (QMessageBox, QFileDialog, QMenu, QCheckBox, QLabel,
                               QWidget, QHBoxLayout, QPushButton, QSizePolicy,
                               QTableWidgetItem, QDialog)
from PySide6.QtCore import Qt, QDate, QTimer
from PySide6.QtGui import QColor
from app.core.db import db, WIFI_DEVICE_ID, usb_device_id
from app.core.metadata_engine import metadata_engine, _is_system_entry
from app.core import ftp, mtp
import app.core.utils as utils
import app.core.shoot_inbox as inboxmod
from app.core import translator
from app.ui import theme
from app.ui import icons
from app.ui.add_source_dialog import AddSourceDialog
from app.ui.ftp_status import FtpStatusDialog


class SourcesMixin:
    """Métodos de la tabla de fuentes, widgets y menús contextuales extraídos de MainWindow (quick 260906-sources-mixin)."""

    def _current_source_path(self):
        """Devuelve la source_path de la sesión activa, o None."""
        if self.current_project_id is None:
            return None
        sessions = db.get_sessions(self.current_project_id)
        for s in sessions:
            if s.get("source_path"):
                return s["source_path"]
        return None

    def _on_source_double_clicked(self, item):
        if item.column() == 0:
            self._prompt_change_source_path(item.row())
        elif item.column() == 1:
            self._prompt_rename_camera(item.row())

    def _prompt_change_source_path(self, row):
        if row < 0 or row >= len(self._source_paths):
            return
        old = self._source_paths[row]
        # Detectar origen FTP por device_id asociado a la sesión
        if self.current_project_id is not None:
            sessions = db.get_sessions(self.current_project_id)
            sess = next((s for s in sessions if s.get("source_path") == old), None)
            if sess:
                device_id = sess.get("device_id") or ""
                if str(device_id).startswith("ftp:"):
                    dlg = FtpStatusDialog(self, device_id=device_id)
                    dlg.exec()
                    return
        start = old if os.path.isdir(old) else os.path.expanduser("~")
        new = QFileDialog.getExistingDirectory(
            self, self.tr("Seleccionar carpeta de la Tarjeta SD"), start)
        if not new or new == old:
            return
        if new in self._source_paths:
            QMessageBox.information(
                self, self.tr("Aviso"),
                self.tr("El origen '%1' ya está en la lista.").arg(new))
            return
        if 0 <= row < len(self._source_paths):
            self._source_paths[row] = new
        if self.current_project_id is not None:
            for s in db.get_sessions(self.current_project_id):
                if s.get("source_path") == old:
                    db.update_session_config(s["id"], source_path=new)
        self._refresh_source_list()
        self._refresh_sessions_combo()
        self.update_start_button_state()
        self.ingest_status_label.setText(self.tr("Origen cambiado: %1").arg(new))

    def _refresh_source_list(self):
        self.source_list.blockSignals(True)
        self.source_list.setRowCount(0)
        if self.current_project_id is None:
            self.source_list.blockSignals(False)
            return
        sessions = db.get_sessions(self.current_project_id)
        by_path = {}
        for s in sessions:
            sp = s.get("source_path")
            if sp:
                by_path.setdefault(sp, []).append(s)
        for row, path in enumerate(self._source_paths):
            self.source_list.insertRow(row)
            # Column 0: source path with checkbox + optional QR/FTP button
            path_sessions = by_path.get(path) or []
            sess = path_sessions[0] if path_sessions else None
            any_enabled = any(s.get("enabled", True) for s in path_sessions)
            checked = (sess is not None and any_enabled)
            self.source_list.setCellWidget(row, 0, self._build_path_widget(row, path, sess, checked))

            # Column 1: camera name
            cam = sess.get("nombre_dispositivo") if sess else None
            cam_text = cam if cam else self.tr("Sin nombre")
            cam_item = QTableWidgetItem(cam_text)
            if not checked:
                cam_item.setForeground(QColor(theme.color("text_disabled")))
            self.source_list.setItem(row, 1, cam_item)
            # Column 2: estado de conectividad (Tarea 3)
            device_id = (sess or {}).get("device_id") or ""
            self.source_list.setCellWidget(row, 2, self._build_status_label(device_id))
            # Column 3: opciones (toggle WiFi, rápido/delicado y papelera)
            self.source_list.setCellWidget(row, 3, self._build_options_widget(row, sess))
        self.source_list.blockSignals(False)
        self._update_format_sources_state()
        self._update_source_list_height()

    def _update_source_list_height(self):
        """Altura mínima de la tabla de orígenes según su contenido (B-06).

        La tabla crece con las filas sin saltos bruscos, pero sin fijar un
        máximo: con espacio disponible la amplía el propio layout."""
        header = self.source_list.horizontalHeader().height() or 26
        row_h = self.source_list.verticalHeader().defaultSectionSize() or 30
        height = header + self.source_list.rowCount() * row_h
        self.source_list.setMinimumHeight(max(56, height))

    def _build_status_label(self, device_id):
        """Estado «Conectado»/«Desconectado» para la columna de estado de la
        tabla de orígenes (Tarea 3).

        El estado real proviene del cache ``self._connectivity``, alimentado
        por la sonda off-thread del auto-sync; los orígenes WiFi se resuelven
        de forma síncrona (servidor en marcha). Sin device_id (carpeta/SD)
        se muestra «—»."""
        if not device_id:
            lbl = QLabel(self.tr("—"))
            lbl.setStyleSheet(
                f"color: {theme.color('text_secondary')}; font-size: 11px;")
            return lbl
        if device_id == WIFI_DEVICE_ID:
            connected = bool(
                self._wifi_server is not None and self._wifi_server.running)
        elif device_id.startswith("usb:"):
            # Unidad USB extraíble: conectada si sigue montada (y es un medio real).
            path = device_id[len("usb:"):]
            connected = bool(utils.is_true_removable_drive(path))
        else:
            connected = bool(self._connectivity.get(device_id))
        lbl = QLabel(self.tr("Conectado") if connected else self.tr("Desconectado"))
        color = theme.color("success") if connected else theme.color("danger")
        lbl.setStyleSheet(f"color: {color}; font-size: 11px;")
        return lbl

    def _update_source_status_cells(self):
        """Refresca solo la columna Estado tras una verificación de
        conectividad off-thread, sin reconstruir toda la tabla (Tarea 3)."""
        if self.current_project_id is None:
            return
        sessions = db.get_sessions(self.current_project_id)
        by_path = {}
        for s in sessions:
            sp = s.get("source_path")
            if sp:
                by_path.setdefault(sp, []).append(s)
        for row, path in enumerate(self._source_paths):
            if row >= self.source_list.rowCount():
                break
            sesss = by_path.get(path) or []
            sess = sesss[0] if sesss else None
            device_id = (sess or {}).get("device_id") or ""
            self.source_list.setCellWidget(
                row, 2, self._build_status_label(device_id))

    def _build_path_widget(self, row, path, session, checked):
        widget = QWidget()
        lay = QHBoxLayout(widget)
        lay.setContentsMargins(4, 0, 4, 0)
        lay.setSpacing(4)
        cb = QCheckBox()
        cb.setChecked(checked)
        cb.stateChanged.connect(lambda state, r=row, p=path: self._on_source_widget_check_changed(r, p, state))
        lay.addWidget(cb)
        device_id = (session or {}).get("device_id") or ""
        # Mostrar etiqueta amigable para orígenes gestionados
        display_text = path
        tooltip_text = path
        if session and self._is_managed_source_path(path):
            name = (session.get("nombre_dispositivo") or "").strip()
            if device_id.startswith("ftp:"):
                try:
                    pid = int(device_id.split(":", 1)[1])
                    prof = db.get_ftp_profile(pid)
                    if prof:
                        host = prof.get("host") or ""
                        port = prof.get("port") or 21
                        display_text = f"FTP {host}:{port}"
                        if name:
                            display_text = f"{name} [{display_text}]"
                except Exception:
                    display_text = name or f"FTP {device_id}"
            elif device_id.startswith("wifi:"):
                display_text = f"WiFi {name}" if name else "WiFi"
            else:
                display_text = name or path
        elif device_id.startswith("ftp:"):
            try:
                pid = int(device_id.split(":", 1)[1])
                prof = db.get_ftp_profile(pid)
                if prof:
                    host = prof.get("host") or ""
                    port = prof.get("port") or 21
                    display_text = f"FTP {host}:{port}"
            except Exception:
                pass
        lbl = QLabel(display_text)
        # Origen deshabilitado (D-12): el label se atenúa
        if not checked:
            lbl.setStyleSheet(
                f"font-size: 11px; color: {theme.color('text_disabled')};")
        else:
            lbl.setStyleSheet(f"font-size: 11px;")
        lbl.setToolTip(tooltip_text)
        lbl.setSizePolicy(QSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred))
        lay.addWidget(lbl, 1)
        is_wifi = bool(session) and device_id == WIFI_DEVICE_ID
        if is_wifi:
            # Solo QR para WiFi (D-06)
            qr_btn = QPushButton(self.tr("QR"))
            qr_btn.setToolTip(self.tr("Mostrar el código QR de este dispositivo"))
            qr_btn.setCursor(Qt.PointingHandCursor)
            qr_btn.setStyleSheet(
                "QPushButton { border: none; text-align: left; padding: 2px 6px;"
                " color: %s; font-size: 11px; }"
                "QPushButton:hover { color: %s; }"
                % (theme.color("text_secondary"), theme.color("accent")))
            sender_name = (session.get("nombre_dispositivo")
                           or session.get("device_folder") or "")
            qr_btn.clicked.connect(
                lambda _=False, n=sender_name: self._show_wifi_qr_for_sender(n))
            lay.addWidget(qr_btn)
        elif device_id.startswith("ftp:"):
            ftp_btn = QPushButton(self.tr("FTP"))
            ftp_btn.setToolTip(self.tr("Estado y configuración FTP"))
            ftp_btn.setCursor(Qt.PointingHandCursor)
            ftp_btn.setStyleSheet(
                "QPushButton { border: none; text-align: left; padding: 2px 6px;"
                " color: %s; font-size: 11px; }"
                "QPushButton:hover { color: %s; }"
                % (theme.color("text_secondary"), theme.color("accent")))
            ftp_btn.clicked.connect(lambda _=False, did=device_id: self._handle_ftp_button(did))
            lay.addWidget(ftp_btn)
        return widget

    def _disable_source_in_project(self, session_id):
        """Inhabilita un origen en el proyecto actual sin borrar el dispositivo
        guardado (B-17/D-12).

        Desmarcar el checkbox pone la sesión con enabled=0: el origen queda
        atenuado en la tabla y NO se toca device_settings ni el diálogo
        «Añadir origen». La papelera de ese diálogo es el único camino que
        borra el dispositivo guardado."""
        db.update_session_config(session_id, enabled=0)

    def _on_source_widget_check_changed(self, row, path, state):
        checked = state == Qt.Checked
        if self.current_project_id is None:
            return
        existing = db.get_sessions(self.current_project_id)
        with_path = [s for s in existing if s.get("source_path") == path]
        if checked:
            if not with_path:
                no_source = [s for s in existing if not s.get("source_path")]
                base = self._drive_label(path)
                name = f"Auto ({base})"
                if no_source:
                    sid = no_source[0]["id"]
                    db.update_session_config(sid, source_path=path, name=name)
                    self.ingest_status_label.setText(self.tr("Origen asignado a sesión #%1").arg(sid))
                else:
                    sid = db.create_session(
                        self.current_project_id, name,
                        QDate.currentDate().toString("yyyy-MM-dd"), "active",
                        source_path=path
                    )
                    self.ingest_status_label.setText(self.tr("Sesión auto creada para %1").arg(path))
                self.current_session_id = sid
                self._repair_folder_device_id(path)
                self._detect_camera_for_session(sid, path)
            else:
                for s in with_path:
                    db.update_session_config(s["id"], enabled=1)
                self.ingest_status_label.setText(self.tr("Origen habilitado: %1").arg(path))
        else:
            if with_path:
                deleted = []
                disabled = []
                for s in with_path:
                    sid = s["id"]
                    name = s.get("name", "")
                    device_id = s.get("device_id") or ""
                    # Eliminar sesiones automáticas creadas al seleccionar origen,
                    # pero conservar las que tienen device_id (USB/FTP/MTP) para
                    # poder deshabilitarlas en lugar de borrarlas.
                    if name.startswith("Auto (") and not device_id:
                        # detener ingestores asociados si existen
                        ing = self._wifi_ingestors.pop(sid, None)
                        if ing is not None:
                            try:
                                ing.stop()
                            except Exception:
                                pass
                        db.delete_session(sid)
                        if self.current_session_id == sid:
                            self.current_session_id = None
                        deleted.append(sid)
                    else:
                        self._disable_source_in_project(sid)
                        disabled.append(sid)
                if deleted:
                    self.ingest_status_label.setText(self.tr("Sesión auto eliminada para %1").arg(path))
                    # repoblar lista de orígenes tras borrado
                    self._populate_source_paths_from_sessions()
                    self._refresh_source_list()
                elif disabled:
                    self.ingest_status_label.setText(self.tr("Origen deshabilitado: %1").arg(path))
                else:
                    self.ingest_status_label.setText(self.tr("Origen deshabilitado: %1").arg(path))
            # actualizar vistas
        self._refresh_sessions_combo()
        self.update_start_button_state()

    def _build_options_widget(self, row, session):
        """Columna «Opciones»: toggle carpeta/archivo WiFi (si aplica),
        rápido/delicado y papelera de eliminar origen."""
        device_id = (session or {}).get("device_id") or ""
        device_key = device_id or ((session or {}).get("source_path") or "")

        wrapper = QWidget()
        wrapper_lay = QHBoxLayout(wrapper)
        wrapper_lay.setContentsMargins(0, 0, 0, 0)
        wrapper_lay.setSpacing(2)

        is_wifi = device_id == "wifi:pairdrop"
        if is_wifi and session:
            mode_btn = QPushButton()
            mode_btn.setObjectName("IconButton")
            mode_btn.setFixedSize(22, 22)
            mode_btn.setCursor(Qt.PointingHandCursor)
            is_folder = bool(session.get("folder_mode"))
            icons.apply(mode_btn, "folder" if is_folder else "copy", size=14)
            mode_btn.setToolTip(
                self.tr("Modo: enviar archivos sueltos") if not is_folder
                else self.tr("Modo: enviar carpeta entera"))
            mode_btn.clicked.connect(
                lambda _=False, s=session, b=mode_btn: self._toggle_wifi_folder_mode(s, b))
            wrapper_lay.addWidget(mode_btn, 0, Qt.AlignRight)

        delicate_btn = QPushButton()
        delicate_btn.setObjectName("IconButton")
        delicate_btn.setFixedSize(22, 22)
        delicate_btn.setCursor(Qt.PointingHandCursor)
        delicate_btn.setToolTip(self.tr("Cambiar modo: rápido / delicado"))
        is_delicate = bool(db.get_device_delicate(device_key)) if device_key else False
        icons.apply(delicate_btn, "snail" if is_delicate else "zap", size=14)
        if session:
            delicate_btn.clicked.connect(
                lambda _=False, dk=device_key, b=delicate_btn: self._toggle_device_delicate(dk, b))
        else:
            delicate_btn.setEnabled(False)
        wrapper_lay.addWidget(delicate_btn, 0, Qt.AlignRight)

        trash_btn = QPushButton()
        trash_btn.setObjectName("IconButton")
        trash_btn.setFixedSize(24, 24)
        trash_btn.setToolTip(self.tr("Eliminar este origen…"))
        trash_btn.setCursor(Qt.PointingHandCursor)
        icons.apply(trash_btn, "trash", size=16)
        trash_btn.clicked.connect(lambda: self._delete_source_at_row(row))
        wrapper_lay.addWidget(trash_btn, 0, Qt.AlignRight)

        return wrapper

    def _toggle_device_delicate(self, device_key, btn):
        current = bool(db.get_device_delicate(device_key))
        db.set_device_delicate(device_key, not current)
        icons.apply(btn, "snail" if not current else "zap", size=14)

    def _build_remove_file_button(self, row_item):
        btn = QPushButton()
        btn.setObjectName("IconButton")
        btn.setFixedSize(24, 24)
        btn.setToolTip(self.tr("Quitar de la vista…"))
        btn.setCursor(Qt.PointingHandCursor)
        icons.apply(btn, "trash", size=16)
        btn.clicked.connect(lambda: self._remove_file_row(row_item))
        return btn

    def _remove_file_row(self, row_item):
        row = self.table.indexFromItem(row_item).row()
        if row < 0:
            return
        self.table.removeRow(row)

    def _reconfigure_ftp_source(self, session):
        """Reabre el selector FTP con el perfil de este origen preseleccionado."""
        profile_id = ftp.profile_id_from_device_key(
            session.get("device_id") or "")
        self._pick_ftp_source(preset_profile_id=profile_id)

    def _reconfigure_mtp_source(self, session):
        """Reabre el selector de dispositivo MTP con los datos del origen."""
        from app.ui.device_picker import DevicePickerDialog
        from app.core import mtp
        dialog = DevicePickerDialog(self)
        if dialog.exec() == QDialog.Accepted and dialog.device_id and dialog.device_folder:
            cache_dir = mtp.device_cache_dir(dialog.device_id, dialog.device_folder)
            try:
                os.makedirs(cache_dir, exist_ok=True)
            except OSError:
                cache_dir = mtp.device_cache_dir(dialog.device_id, "")
                os.makedirs(cache_dir, exist_ok=True)
            old_path = session.get("source_path")
            self._register_device_source(
                cache_dir, dialog.device_id, dialog.device_folder,
                dialog.device_name, backend=mtp.WpdBackend())

    def _show_source_context_menu(self, pos):
        row = self.source_list.rowAt(pos.y())
        if row < 0:
            return
        menu = QMenu(self)
        delete_action = menu.addAction(self.tr("Eliminar origen…"))
        delete_action.triggered.connect(
            lambda: self._delete_source_at_row(row))
        menu.exec(self.source_list.viewport().mapToGlobal(pos))

    def _clear_source_list_selection(self):
        """Deselecciona todas las filas de la lista de orígenes."""
        self.source_list.clearSelection()
        self.source_list.setCurrentCell(-1, -1)

    def _source_list_event_filter(self, obj, ev):
        """Event filter for source_list to handle ESC key and click-away deselect."""
        if obj == self.source_list:
            if ev.type() == ev.Type.KeyPress:
                if ev.key() == Qt.Key_Escape:
                    self._clear_source_list_selection()
                    return True
            elif ev.type() == ev.Type.MouseButtonPress:
                pos = ev.pos()
                if not self.source_list.geometry().contains(pos):
                    self._clear_source_list_selection()
        return True
        return False

    def _handle_ftp_button(self, device_id):
        try:
            pid = int(device_id.split(":", 1)[1])
        except Exception:
            QMessageBox.warning(self, self.tr("FTP"), self.tr("Identificador FTP inválido"))
            return
        from app.ui.ftp_status import FtpStatusDialog
        dlg = FtpStatusDialog(self, device_id=device_id)
        dlg.exec()
        self._refresh_source_list()
        self._refresh_sessions_combo()

    def _delete_source_at_row(self, row):
        if row < 0 or row >= len(self._source_paths):
            return
        path = self._source_paths[row]
        if self.current_project_id is None:
            return
        sessions = [s for s in db.get_sessions(self.current_project_id)
                    if s.get("source_path") == path]
        if not sessions:
            return
        names = ", ".join(s["name"] for s in sessions)
        reply = QMessageBox.question(
            self, self.tr("Eliminar origen"),
            self.tr("¿Eliminar el origen '%1' y sus sesiones?\n"
                    "Esta acción no se puede deshacer.")
            .arg(path).arg(names),
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No,
        )
        if reply != QMessageBox.Yes:
            return
        self._remove_source_path(path)

    def _remove_source_path(self, path):
        """Borra las sesiones de un origen y, si es WiFi, también su remitente."""
        sessions = [s for s in db.get_sessions(self.current_project_id)
                    if s.get("source_path") == path]
        for s in sessions:
            sid = s["id"]
            ing = self._wifi_ingestors.pop(sid, None)
            if ing is not None:
                try:
                    ing.stop()
                except Exception:
                    pass
            device_id = s.get("device_id") or ""
            db.delete_session(sid)
            # Si es un origen WiFi, elimina el remitente asociado para que
            # _sync_wifi_sessions no lo recree.
            if s.get("device_id") == "wifi:pairdrop":
                folder = s.get("device_folder") or ""
                for sender in db.list_inbox_senders():
                    if (inboxmod.sanitize_alias(sender["name"]) == folder):
                        db.delete_inbox_sender(sender["id"])
                        break
            # Limpiar registro de dispositivo USB para evitar fantasmas en Añadir origen
            if device_id.startswith("usb:"):
                try:
                    db.delete_device(device_id)
                except Exception:
                    pass
        if path in self._source_paths:
            self._source_paths.remove(path)
        self._populate_source_paths_from_sessions()
        self._refresh_source_list()
        self._refresh_sessions_combo()
        self.update_start_button_state()

        if self._wifi_panel is not None:
            self._wifi_panel.refresh()
        self.ingest_status_label.setText(
            self.tr("Origen eliminado: %1").arg(path))

    def _hide_source_path(self, path):
        """Quita un origen de la lista visual sin borrar sus sesiones en DB."""
        if path in self._source_paths:
            self._source_paths.remove(path)
        self._refresh_source_list()
        self._refresh_sessions_combo()
        self.update_start_button_state()
        self.ingest_status_label.setText(
            self.tr("Origen ocultado: %1").arg(path))

    def _on_source_check_changed(self, item):
        if self.current_project_id is None:
            return
        if item.column() == 1:
            self._on_camera_cell_edited(item)
            return

    def _add_source_entry(self):
        sources = self._pick_source_entry()
        if sources:
            for src in sources:
                self._apply_source_choice(src)

    def _apply_source_choice(self, src):
        """Procesa un único origen devuelto por AddSourceDialog."""
        kind = src.get("kind")
        value = src.get("value")
        camera = src.get("camera")
        if kind == "browse":
            start_dir = self.source_input.currentText().strip() or os.path.expanduser("~")
            path = QFileDialog.getExistingDirectory(
                self, self.tr("Seleccionar carpeta de la Tarjeta SD"), start_dir
            )
            if path:
                self._assign_folder_source(path)
        elif kind == "folder":
            self._assign_folder_source(value)
        elif kind == "sender":
            self._bind_wifi_sender(value)
        elif kind == "ftp_profile":
            # Registrar directamente el perfil FTP sin reabrir el selector
            raw = value
            if isinstance(raw, str) and raw.startswith("ftp:"):
                profile_id = int(raw.split(":",1)[1])
            else:
                profile_id = int(raw)
            from app.core import ftp
            profile = db.get_ftp_profile(profile_id)
            device_id = f"ftp:{profile_id}"
            device_folder = (profile.get("base_folder") or "") if profile else ""
            device_name = camera or (profile.get("name") if profile else "")
            self._register_device_source_from_picker(
                device_id, device_folder, device_name, backend=ftp.FtpBackend())
        elif kind == "device":
            # value es el device_id; necesitamos obtener folder y nombre
            # Para MTP, el diálogo no selecciona carpeta; usamos la raíz del dispositivo
            device_id = value
            # Buscar en devices_connected o usar valores por defecto
            device_folder = ""
            device_name = camera or "Dispositivo"
            backend = ftp.FtpBackend() if str(device_id).startswith("ftp:") else mtp.WpdBackend()
            self._register_device_source_from_picker(
                device_id, device_folder, device_name, backend=backend)
        elif kind == "usb":
            # USB masivo: se trata como carpeta local, conservando el nombre
            # de cámara elegido en el diálogo (si lo hay)
            self._assign_folder_source(value, camera=camera)
        elif kind == "ftp_new":
            profile_id, device_id, device_folder, device_name = value
            self._register_device_source_from_picker(
                device_id, device_folder, device_name, backend=ftp.FtpBackend())
        elif kind == "wifi":
            self._pick_wifi_source()

    def _pick_source_entry(self):
        """Abre el nuevo diálogo «Añadir origen» (AddSourceDialog).

        Devuelve una lista de orígenes seleccionados (cada uno es un dict
        con kind, value, camera, enabled) o ``None`` si se cancela.
        """
        if self.current_project_id is None:
            QMessageBox.information(
                self, self.tr("Proyecto requerido"),
                self.tr("Debes seleccionar o crear un proyecto antes de añadir un origen."))
            return None
        sessions = db.get_sessions(self.current_project_id)
        folders = []
        for p in db.get_recent_paths("source"):
            if p not in folders:
                folders.append(p)
        for s in sessions:
            sp = s.get("source_path")
            if sp and not self._is_managed_source_path(sp) and sp not in folders:
                folders.append(sp)
        used = {s.get("device_folder") for s in sessions
                if (s.get("device_id") or "").startswith("wifi:")}
        senders = [{"id": s["id"], "name": s["name"],
                    "used": inboxmod.sanitize_alias(s["name"]) in used}
                   for s in db.list_inbox_senders()]
        # Ensure WiFi server is running so status is accurate
        self._ensure_wifi_server()
        # Dispositivos conectados para la sección física (D-03)
        devices_connected = []
        try:
            devices_connected = mtp.WpdBackend().list_devices()
        except Exception:
            devices_connected = []
        # Unidades USB masivas montadas: la visibilidad no depende de que
        # estén guardadas (borrar el origen no debe ocultar un dispositivo
        # físicamente presente).
        usb_connected = []
        try:
            for drive in utils.get_mounted_drives():
                drive_path = drive if isinstance(drive, str) else drive.get("path", "")
                if drive_path and utils.is_removable_drive(drive_path):
                    usb_connected.append(drive_path)
        except Exception:
            usb_connected = []
        dialog = AddSourceDialog(self, folders=folders, senders=senders,
                                  devices_missing=self._disconnected_devices(),
                                  devices_connected=devices_connected,
                                  usb_connected=usb_connected,
                                  on_delete=self._delete_saved_source,
                                  on_qr=self._show_wifi_qr_for_sender,
                                  on_camera_name_changed=self._on_dialog_camera_name_changed,
                                  on_wifi_status=lambda sender_id: self._wifi_server is not None and self._wifi_server.running)
        if dialog.exec() != QDialog.Accepted:
            return None
        sources = dialog.result_sources()
        if not sources:
            return None
        return sources

    def _delete_saved_source(self, kind, value):
        """Borra un guardado desde el diálogo «Añadir origen» (B-04).

        Devuelve True si se eliminó (para quitar el elemento de la lista)."""
        if kind == "folder":
            if self.current_project_id is not None:
                in_use = any(s.get("source_path") == value
                             for s in db.get_sessions(self.current_project_id))
                if in_use:
                    QMessageBox.information(
                        self, self.tr("Eliminar origen"),
                        self.tr("La carpeta '%1' está asignada a una sesión; "
                                "elimínala desde la lista de orígenes.")
                        .arg(value))
                    return False
            db.remove_recent_path(value)
            return True
        if kind == "ftp_profile":
            reply = QMessageBox.question(
                self, self.tr("Eliminar perfil FTP"),
                self.tr("¿Eliminar el perfil FTP guardado?"),
                QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
            if reply != QMessageBox.Yes:
                return False
            raw = value
            if isinstance(raw, str) and raw.startswith("ftp:"):
                raw = int(raw.split(":",1)[1])
            db.delete_ftp_profile(int(raw))
            return True
        if kind == "sender":
            # value is now sender_id (int), but handle name for backward compat
            sender = None
            for s in db.list_inbox_senders():
                if str(s["id"]) == str(value) or s["name"] == value:
                    sender = s
                    break
            if sender is None:
                return False
            reply = QMessageBox.question(
                self, self.tr("Eliminar remitente WiFi"),
                self.tr("¿Eliminar el remitente WiFi '%1'?").arg(sender["name"]),
                QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
            if reply != QMessageBox.Yes:
                return False
            db.delete_inbox_sender(sender["id"])
            self._sync_wifi_sessions()
            return True
        if kind == "device":
            reply = QMessageBox.question(
                self, self.tr("Eliminar dispositivo guardado"),
                self.tr("¿Eliminar este dispositivo guardado y sus sesiones?\n"
                        "Los archivos en disco se conservan.\n"
                        "Esta acción no se puede deshacer."),
                QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
            if reply != QMessageBox.Yes:
                return False
            if str(value).startswith("ftp:"):
                pid = ftp.profile_id_from_device_key(value)
                if pid is not None:
                    db.delete_ftp_profile(pid)
            db.delete_device(value)
            self._populate_source_paths_from_sessions()
            self._refresh_source_list()
            self._refresh_sessions_combo()
            self.update_start_button_state()
            return True
        if kind == "usb":
            # El diálogo guarda unidades USB con clave usb:<ruta> (igual que las
            # sesiones). value es la ruta cruda (E:\).
            device_id = usb_device_id(value)
            reply = QMessageBox.question(
                self, self.tr("Eliminar unidad USB guardada"),
                self.tr("¿Eliminar esta unidad USB guardada y sus sesiones?\n"
                        "Los archivos en disco se conservan.\n"
                        "Esta acción no se puede deshacer."),
                QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
            if reply != QMessageBox.Yes:
                return False
            db.delete_device(device_id)
            self._populate_source_paths_from_sessions()
            self._refresh_source_list()
            self._refresh_sessions_combo()
            self.update_start_button_state()
            return True
        return False