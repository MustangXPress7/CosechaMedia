import json
import os
from datetime import datetime
from PySide6.QtCore import QSettings
from PySide6.QtWidgets import QMessageBox, QInputDialog, QFileDialog, QDialog, QSpinBox, QComboBox, QDialogButtonBox, QFormLayout
from app.core.db import db
from app.core.metadata_engine import metadata_engine
from app.core import translator
from app.ui import icons
from app.ui.selective_dump import SelectiveDumpAssistant, content_summary


class SessionsMixin:
    """Métodos de gestión de sesiones extraídos de MainWindow (quick 260906-i6a)."""

    def _refresh_sessions_combo(self):
        # Prioridad: _restore_session_id (desde load_existing_projects) > prev_id (actual)
        restore_id = getattr(self, "_restore_session_id", None)
        if restore_id is not None:
            target_id = restore_id
            self._restore_session_id = None
        else:
            target_id = self.sessions_combo.currentData()
        
        self.sessions_combo.blockSignals(True)
        self.sessions_combo.clear()
        if self.current_project_id is None:
            self.sessions_combo.blockSignals(False)
            self._reset_session_selection_ui()
            return
        sessions = db.get_sessions(self.current_project_id)
        if not sessions:
            self.sessions_combo.addItem(self.tr("(Sin sesiones)"), None)
            self.sessions_combo.blockSignals(False)
            self._reset_session_selection_ui()
            return
        for idx, s in enumerate(sessions, start=1):
            status_fmt = "●" if s["status"] == "active" else "○"
            src = s.get("source_path") or ""
            label = f"{status_fmt} #{idx} - {s['name']}"
            if src and f"({self._drive_label(src)})" not in s.get("name", ""):
                label += f" ({self._drive_label(src)})"
            self.sessions_combo.addItem(label, s["id"])
        if target_id is not None:
            idx = self.sessions_combo.findData(target_id)
            if idx >= 0:
                self.sessions_combo.setCurrentIndex(idx)
            else:
                # La sesión a restaurar no existe: quedarse con la primera
                self.sessions_combo.setCurrentIndex(0)
                self._on_session_selected(0)
        else:
            self.sessions_combo.setCurrentIndex(0)
            self._on_session_selected(0)
        self.sessions_combo.blockSignals(False)
        self.btn_delete_session.setEnabled(self.current_session_id is not None)
        self._update_session_dump_switch()

    def _reset_session_selection_ui(self):
        """Deja el panel de sesión sin selección y con etiquetas neutras."""
        self.current_session_id = None
        self.btn_delete_session.setEnabled(False)
        self.session_src_label.setText("")
        self.session_src_label.setToolTip("")
        self._btn_browse_sess_src.setVisible(False)
        self.session_dest_label.setText(self.tr("Por defecto"))
        self.session_dest_label.setToolTip("")
        self._btn_browse_sess_dest.setVisible(False)
        self._update_session_dump_switch()

    def _on_session_selected(self, index):
        session_id = self.sessions_combo.itemData(index)
        if session_id is None:
            self.current_session_id = None
            self.btn_delete_session.setEnabled(False)
            self.session_src_label.setText("")
            self._btn_browse_sess_src.setVisible(False)
            self.session_dest_label.setText(self.tr("Por defecto"))
            self._btn_browse_sess_dest.setVisible(False)
            self._update_session_dump_switch()
            return
        self.current_session_id = session_id
        self.btn_delete_session.setEnabled(True)
        session = db.get_session(session_id)
        if not session:
            return
        managed = self._is_managed_session(session)
        # El origen de cualquier sesión se puede cambiar desde el selector
        # (otro remitente WiFi, una carpeta…), también en las gestionadas.
        self._btn_browse_sess_src.setVisible(True)
        self._btn_browse_sess_dest.setVisible(True)
        src = session.get("source_path") or ""
        if managed and src:
            # Muestra el nombre del dispositivo (cámara/móvil) en lugar de la
            # ruta técnica de la caché local (B-02).
            name = session.get("nombre_dispositivo") or session.get("device_folder") or ""
            if name:
                text = self.tr("Origen automático: %1").arg(name)
            else:
                text = self.tr("Origen automático: %1").arg(src)
        else:
            text = (self.tr("Origen: %1").arg(src) if src
                    else self.tr("Origen: sin origen (no se ejecutará)"))
        self.session_src_label.setText(text)
        self.session_src_label.setToolTip(text)
        dest = session.get("destination_override")
        self.session_dest_label.setText(dest if dest else self.tr("Por defecto"))
        self.session_dest_label.setToolTip(dest or "")
        self._update_session_dump_switch()

    def _session_content_state(self, sid):
        """Devuelve (mode, filt, restricted) de la sesión dada.

        restricted = sesión WiFi/FTP (siempre vuelcan todo). El filtro JSON
        corrupto degrada a None («todo»), nunca crash."""
        sess = db.get_session(sid) if sid is not None else None
        if not sess:
            return "all", None, False
        device_id = str(sess.get("device_id") or "")
        restricted = device_id.startswith("wifi:") or device_id.startswith("ftp:")
        filt = None
        try:
            raw = sess.get("content_filter")
            if raw:
                filt = json.loads(raw)
        except (TypeError, ValueError):
            filt = None
        mode = sess.get("content_mode") or "all"
        return mode, filt, restricted

    @staticmethod
    def _window_value_unit_from_filter(filt):
        """(valor, unidad) del filtro ventana; filtro legacy → (días, "days")."""
        if not isinstance(filt, dict):
            return 1, "days"
        # Formato nuevo: window_value + window_unit
        unit = filt.get("window_unit")
        if unit in ("days", "weeks", "months"):
            try:
                value = int(filt.get("window_value", 1))
            except (TypeError, ValueError):
                value = 1
            return value, unit
        # Formato legacy: solo window_days
        try:
            return int(filt.get("window_days", 1)), "days"
        except (TypeError, ValueError):
            return 1, "days"

    @staticmethod
    def _window_days_from_filter(filt):
        """Días efectivos para el ingestor según la unidad (1/7/30)."""
        value, unit = MainWindow._window_value_unit_from_filter(filt)
        if unit == "weeks":
            return value * 7
        if unit == "months":
            return value * 30
        return value

    def _window_filter_text(self, filt):
        """Etiqueta unit-aware del botón de configuración: N días/semanas/meses."""
        value, unit = self._window_value_unit_from_filter(filt)
        if unit == "weeks":
            return self.tr("Últimas %1 semanas").arg(value)
        if unit == "months":
            return self.tr("Últimos %1 meses").arg(value)
        return self.tr("Últimos %1 días").arg(value)

    def _update_session_dump_switch(self):
        """Refresca el rotativo (icono del modo) y el botón de configuración.

        El rotativo muestra solo el icono del modo vigente (cuadrado=todo,
        calendario=intervalo, cronómetro=N días); el botón de configuración
        muestra en texto la configuración actual y abre su menú al pulsar."""
        btn = getattr(self, "btn_session_dump_mode", None)
        cfg = getattr(self, "btn_session_dump_config", None)
        if btn is None or cfg is None:
            return
        sid = self.current_session_id
        if sid is None:
            btn.setEnabled(False)
            cfg.setEnabled(False)
            icons.apply(btn, "square", size=16)
            cfg.setText(self.tr("Todo el contenido"))
            return
        mode, filt, restricted = self._session_content_state(sid)
        if restricted:
            # WiFi y FTP siempre vuelcan todo el contenido (coherente con start_ingest)
            btn.setEnabled(False)
            cfg.setEnabled(False)
            icons.apply(btn, "square", size=16)
            cfg.setText(self.tr("Todo el contenido"))
            tip = self.tr("WiFi y FTP siempre vuelcan todo el contenido")
            btn.setToolTip(tip)
            cfg.setToolTip(tip)
            return
        btn.setEnabled(True)
        btn.setToolTip(self.tr(
            "Cambiar el volcado de esta sesión: todo / intervalo de fechas / últimos N días"))
        cfg.setToolTip(self.tr("Abrir las opciones del modo de volcado actual"))
        if mode == "interval":
            icons.apply(btn, "calendar", size=16)
            if filt:
                cfg.setText(self.tr("Intervalo: %1").arg(content_summary(filt)))
            else:
                cfg.setText(self.tr("Intervalo de fechas"))
            cfg.setEnabled(True)
        elif mode == "window":
            icons.apply(btn, "timer", size=16)
            cfg.setText(self._window_filter_text(filt))
            cfg.setEnabled(True)
        else:
            icons.apply(btn, "square", size=16)
            cfg.setText(self.tr("Todo el contenido"))
            # El modo «todo» no tiene opciones que configurar
            cfg.setEnabled(False)

    def _cycle_session_content_mode(self):
        """Cicla el modo de volcado de la sesión sin abrir diálogos."""
        sid = self.current_session_id
        if sid is not None:
            mode, filt, restricted = self._session_content_state(sid)
            if not restricted:
                nxt = {"all": "interval", "interval": "window",
                       "window": "all"}.get(mode, "interval")
                if nxt == "all":
                    db.update_session_config(sid, content_mode=nxt, content_filter=None)
                else:
                    db.update_session_config(sid, content_mode=nxt)
        self._update_session_dump_switch()

    def _open_session_dump_menu(self):
        """Abre el diálogo de configuración del modo de volcado activo."""
        sid = self.current_session_id
        if sid is not None:
            mode, filt, restricted = self._session_content_state(sid)
            if not restricted:
                if mode == "interval":
                    # El asistente persiste al aceptar; cancelar conserva el filtro.
                    self._open_content_filter(sid)
                elif mode == "window":
                    value, unit = self._window_value_unit_from_filter(filt)
                    value, unit, ok = self._open_window_filter_dialog(value, unit)
                    if ok:
                        # Guardar valor + unidad; el ingestor usa días normalizados.
                        days = value * (7 if unit == "weeks" else 30 if unit == "months" else 1)
                        db.update_session_config(
                            sid, content_mode="window",
                            content_filter=json.dumps({
                                "window_days": days,
                                "window_value": int(value),
                                "window_unit": unit,
                            }))
        self._update_session_dump_switch()

    def _open_window_filter_dialog(self, initial_value: int, initial_unit: str):
        """Diálogo para configurar filtro ventana con selector de unidad (días/semanas/meses)."""
        dialog = QDialog(self)
        dialog.setWindowTitle(self.tr("Configurar últimos N días/semanas/meses"))
        dialog.setModal(True)
        layout = QFormLayout(dialog)

        spin = QSpinBox()
        spin.setRange(1, 3650)
        spin.setValue(initial_value)
        spin.setToolTip(self.tr("Cantidad de unidades hacia atrás"))
        layout.addRow(self.tr("Valor:"), spin)

        combo = QComboBox()
        combo.addItems([self.tr("Días"), self.tr("Semanas"), self.tr("Meses")])
        unit_map = {"days": 0, "weeks": 1, "months": 2}
        combo.setCurrentIndex(unit_map.get(initial_unit, 0))
        combo.setToolTip(self.tr("Unidad de tiempo para el filtro"))
        layout.addRow(self.tr("Unidad:"), combo)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        layout.addRow(buttons)

        if dialog.exec() == QDialog.Accepted:
            idx = combo.currentIndex()
            unit = ["days", "weeks", "months"][idx]
            return spin.value(), unit, True
        return initial_value, initial_unit, False

    def _add_manual_session(self):
        if self.current_project_id is None:
            QMessageBox.information(self, self.tr("Sin proyecto"), self.tr("Selecciona un proyecto primero."))
            return
        name, ok = QInputDialog.getText(
            self, self.tr("Nueva Sesión manual"),
            self.tr("Nombre de la sesión:"),
            text="Sesión " + datetime.now().strftime("%Y-%m-%d")
        )
        if not ok or not name.strip():
            return
        session_id = db.create_session(
            self.current_project_id, name.strip(),
            QDate.currentDate().toString("yyyy-MM-dd"), "active"
        )
        self._refresh_sessions_combo()
        idx = self.sessions_combo.findData(session_id)
        if idx >= 0:
            self.sessions_combo.setCurrentIndex(idx)
        self.ingest_status_label.setText(self.tr("Sesión manual '%1' creada (ID: %2)").arg(name.strip()).arg(session_id))

    def _delete_current_session(self):
        if self.current_session_id is None:
            return
        sid = self.current_session_id
        reply = QMessageBox.question(
            self, self.tr("Eliminar sesión"),
            self.tr("¿Eliminar la sesión #%1 y sus registros de ingesta?\n"
                    "Los archivos en disco se conservan.\n"
                    "Esta acción no se puede deshacer.").arg(sid),
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if reply == QMessageBox.No:
            return
        db.delete_session(sid)
        self.current_session_id = None
        self._refresh_sessions_combo()
        self._refresh_source_list()
        self.ingest_status_label.setText(self.tr("Sesión #%1 eliminada.").arg(sid))

    def _on_session_dest_type_changed(self, index):
        pass

    def _save_session_override(self):
        if self.current_session_id is None:
            return
        dest_text = self.session_dest_label.text().strip()
        is_custom = dest_text and dest_text != self.tr("Por defecto")
        kw = {
            "destination_override": dest_text if is_custom else None,
        }
        db.update_session_config(self.current_session_id, **kw)

    def _browse_session_dest(self):
        current = self.session_dest_label.text().strip()
        if current == self.tr("Por defecto"):
            current = ""
        path = QFileDialog.getExistingDirectory(
            self, self.tr("Seleccionar destino de sesión"),
            current or self.dest_root or os.path.expanduser("~")
        )
        if path:
            self.session_dest_label.setText(path)
            self.session_dest_label.setToolTip(path)
            self._save_session_override()

    def _browse_session_src(self):
        if self.current_session_id is None:
            return
        sources = self._pick_source_entry()
        if not sources:
            return
        for src in sources:
            kind = src.get("kind")
            value = src.get("value")
            camera = src.get("camera")
            if kind == "browse":
                path = QFileDialog.getExistingDirectory(
                    self, self.tr("Seleccionar origen de sesión"),
                    os.path.expanduser("~")
                )
                if path:
                    self._assign_session_folder(self.current_session_id, path)
            elif kind == "folder":
                self._assign_session_folder(self.current_session_id, value)
            elif kind == "sender":
                self._bind_wifi_sender(value, session_id=self.current_session_id)
            elif kind == "ftp_profile":
                self._pick_ftp_source(preset_profile_id=value)
            elif kind == "device":
                device_id = value
                device_folder = ""
                device_name = camera or "Dispositivo"
                self._register_device_source_from_picker(
                    device_id, device_folder, device_name, backend=mtp.WpdBackend())
            elif kind == "usb":
                self._assign_session_folder(self.current_session_id, value)
            elif kind == "ftp_new":
                profile_id, device_id, device_folder, device_name = value
                self._register_device_source_from_picker(
                    device_id, device_folder, device_name, backend=ftp.FtpBackend())
            elif kind == "wifi":
                self._pick_wifi_source()

    def _populate_source_paths_from_sessions(self):
        self._source_paths.clear()
        if self.current_project_id is None:
            return
        for s in db.get_sessions(self.current_project_id):
            sp = s.get("source_path")
            if sp and sp not in self._source_paths:
                self._source_paths.append(sp)

    def _open_content_filter(self, session_id):
        """Abre el asistente en modo filtro para una sesión; True solo si acepta.

        Al aceptar persiste content_mode + content_filter de la sesión."""
        if self.current_project_id is None:
            return False
        session = db.get_session(session_id) if session_id is not None else None
        if not session:
            return False
        path = session.get("source_path") or ""
        dialog = SelectiveDumpAssistant(self, source_path=path, mode="filter",
                                        session_id=session_id, initial_mode="interval")
        if dialog.exec() == QDialog.Accepted:
            filt = dialog.content_filter
            mode = dialog.content_mode
            db.update_session_config(
                session_id, 
                content_filter=json.dumps(filt) if filt else None,
                content_mode=mode)
            self._update_session_dump_switch()
            self.ingest_status_label.setText(
                self.tr("Contenido del origen %1: %2").arg(path).arg(dialog.content_text))
            return True
        return False