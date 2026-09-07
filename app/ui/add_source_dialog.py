"""Diálogo «Añadir origen» — tabla plana de 3 secciones (D-01..D-15).

Sustituye a ``SourcePickerDialog`` (D-04). Muestra una única tabla con 5
columnas y 3 secciones visuales (física MTP/USB, WiFi/PairDrop, FTP), sin
pestañas. Integra los dispositivos guardados y detectados, distingue MTP vs
USB masivo, ofrece detección de cámara off-thread y notifica fallos WPD de
forma no-bloqueante.

Al aceptar expone ``result_sources()``: lista de dicts
``{"kind", "value", "camera", "enabled"}`` con los orígenes marcados.
"""

from concurrent.futures import ThreadPoolExecutor

from PySide6.QtCore import Qt, QObject, Signal
from PySide6.QtWidgets import (
    QCheckBox, QComboBox, QDialog, QFileDialog, QHBoxLayout, QHeaderView, QLabel,
    QLineEdit, QMessageBox, QPushButton, QTableWidget, QTableWidgetItem,
    QVBoxLayout, QWidget,
)

from app.core import utils
from app.core import mtp
from app.core import ftp as ftpmod
from app.core.db import db
from app.core.translator import QtString
from app.ui import theme
from app.ui import icons


# Ítem disparador de detección en el combo de cámara (CHG-5)
TRIGGER_DETECT = object()


def _camera_text(widget):
    """Extrae el texto del widget de cámara (QLineEdit o QComboBox editable)."""
    if isinstance(widget, QComboBox):
        le = widget.lineEdit() if hasattr(widget, "lineEdit") else None
        return le.text() if le is not None else widget.currentText()
    if isinstance(widget, QLineEdit):
        return widget.text()
    return ""


class _CameraDetectWorker(QObject):
    """Detección de cámara en hilo separado (D-08/D-09): no bloquea la UI."""

    done = Signal(int, bool, object)

    def __init__(self, fn, source, executor):
        super().__init__()
        self._fn = fn
        self._source = source
        self._executor = executor
        self._future = None

    def start(self):
        self._future = self._executor.submit(self._run)

    def _run(self):
        try:
            name = self._fn(self._source.get("kind"), self._source.get("value"))
            self.done.emit(self._source.get("_row", -1), True, name)
        except Exception as e:
            self.done.emit(self._source.get("_row", -1), False, str(e))


class AddSourceDialog(QDialog):
    """Tabla plana de orígenes con 3 secciones y 5 columnas."""

    def tr(self, text, *args, **kwargs):
        return QtString(super().tr(text, *args, **kwargs))

    def __init__(self, parent=None, folders=(), senders=(),
                 devices_missing=(), devices_connected=(),
                 mtp_backend=None, ftp_backend=None,
                 on_delete=None, on_detect=None, on_qr=None,
                 on_camera_name_changed=None, on_wifi_status=None,
                 camera_detection_mode="auto"):
        super().__init__(parent)
        self.on_delete = on_delete      # on_delete(kind, value) -> bool
        self.on_detect = on_detect      # on_detect(kind, value) -> str (cámara)
        self.on_qr = on_qr              # on_qr(sender_name) -> None
        self.on_camera_name_changed = on_camera_name_changed
        self.on_wifi_status = on_wifi_status  # on_wifi_status(sender_id) -> bool
        # on_camera_name_changed(device_id, nombre) -> None: se invoca al
        # editar el nombre de un dispositivo conocido (persistencia B-20).
        self._camera_detection_mode = camera_detection_mode
        self._mtp_backend = mtp_backend if mtp_backend is not None else mtp.WpdBackend()
        self._explicit_mtp = mtp_backend is not None
        self._ftp_backend = ftp_backend or ftpmod.FtpBackend()
        self._row_sources = []          # dict por fila de datos (None = cabecera)
        self._cam_executor = ThreadPoolExecutor(max_workers=1)
        self._cam_worker = None
        self._accepted = None   # None=sin decidir, True=aceptado, False=cancelado
        # Limpieza one-shot de carpetas locales persistidas como dispositivos
        # (bug 5): las carpetas ya viven en recent_paths y no son dispositivos.
        try:
            db.delete_known_devices_by_type("folder")
        except Exception:
            pass

        self.setWindowTitle(self.tr("Añadir origen"))
        self.setMinimumSize(800, 500)
        self._build_ui(folders, senders, devices_missing, devices_connected)

    # -- construcción de la UI --------------------------------------------

    def _build_ui(self, folders, senders, devices_missing, devices_connected):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(10)

        hint = QLabel(self.tr("Marca los orígenes a añadir y ajusta el nombre "
                              "de cámara de cada uno."))
        hint.setWordWrap(True)
        layout.addWidget(hint)

        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels([
            self.tr("Seleccionar"), self.tr("Ruta de origen"), self.tr("Dispositivo"),
            self.tr("Estado"), self.tr("Borrar")])
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(1, QHeaderView.Stretch)
        header.setStretchLastSection(False)
        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionMode(QTableWidget.NoSelection)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        layout.addWidget(self.table, 1)

        self.error_label = QLabel("")
        self.error_label.setVisible(False)
        self.error_label.setStyleSheet(
            "color: {}; font-size: 11px; padding: 2px 0;"
            .format(theme.color("danger")))
        layout.addWidget(self.error_label)

        # fila de acciones
        actions = QHBoxLayout()
        self.btn_browse = QPushButton(self.tr("Examinar…"))
        self.btn_browse.clicked.connect(self._browse_folder)
        actions.addWidget(self.btn_browse)
        self.btn_detect = QPushButton(self.tr("Detectar"))
        self.btn_detect.setToolTip(self.tr("Detectar dispositivos y unidades extraíbles"))
        icons.apply(self.btn_detect, "refresh", size=14)
        self.btn_detect.clicked.connect(self._detect_devices)
        actions.addWidget(self.btn_detect)
        self.btn_new_wifi = QPushButton(self.tr("Nuevo WiFi"))
        self.btn_new_wifi.clicked.connect(self._add_wifi_row)
        actions.addWidget(self.btn_new_wifi)
        self.btn_new_ftp = QPushButton(self.tr("Nuevo FTP"))
        self.btn_new_ftp.clicked.connect(self._add_ftp_row)
        actions.addWidget(self.btn_new_ftp)
        actions.addStretch()

        self.btn_import = QPushButton(self.tr("Importar JSON"))
        self.btn_import.setToolTip(self.tr("Importar dispositivos conocidos desde un archivo JSON"))
        self.btn_import.clicked.connect(self._import_json)
        actions.addWidget(self.btn_import)

        self.btn_export = QPushButton(self.tr("Exportar JSON"))
        self.btn_export.setToolTip(self.tr("Exportar dispositivos conocidos a un archivo JSON"))
        self.btn_export.clicked.connect(self._export_json)
        actions.addWidget(self.btn_export)

        layout.addLayout(actions)

        # fila de botones Aceptar/Cancelar
        buttons = QHBoxLayout()
        cancel_btn = QPushButton(self.tr("Cancelar"))
        cancel_btn.clicked.connect(self.reject)
        self.btn_aceptar = QPushButton(self.tr("Aceptar"))
        self.btn_aceptar.setObjectName("PrimaryAction")
        self.btn_aceptar.setDefault(True)
        self.btn_aceptar.clicked.connect(self.accept)
        buttons.addStretch()
        buttons.addWidget(cancel_btn)
        buttons.addWidget(self.btn_aceptar)
        layout.addLayout(buttons)

        # ---- poblado de secciones ----
        self._populate(folders, senders, devices_missing, devices_connected)
        self._update_ok_state()

    # -- poblado ----------------------------------------------------------

    def _populate(self, folders, senders, devices_missing, devices_connected):
        row = 0
        # Sección física
        row = self._add_section(row, self.tr("Conexión física (MTP/USB/SD)"))
        # Carpetas locales (parte del origen físico; sin cabecera propia).
        for folder in folders:
            row = self._add_source_row(
                row, {"kind": "folder", "value": folder, "camera": "",
                      "enabled": True, "connected": True,
                      "label": folder, "type": "FOLDER"})
        # Dispositivos conectados / detectados por el llamador (D-03).
        devices = list(devices_connected)
        if self._explicit_mtp:
            # Backend proporcionado (p. ej. tests): enumerar en construcción.
            try:
                devices = devices or self._mtp_backend.list_devices()
            except Exception as e:
                self._show_wpd_error(e)
                devices = []
        # Cuando NO se pasó backend, confiamos en devices_connected (el
        # llamador pre-detecta); la detección a demanda la hace "Detectar".
        for dev in devices:
            device_id = dev.device_id
            # Usar nombre de cámara guardado si existe (feature: recordar última cámara)
            saved_camera = db.get_dispositivo_for_device(device_id)
            name = saved_camera or dev.name or device_id
            row = self._add_source_row(
                row, {"kind": "device", "value": device_id,
                      "camera": name, "enabled": True, "connected": True,
                      "label": self.tr("[MTP] %1").arg(name), "type": "MTP"})
        # Unidades USB masivas removibles (D-13/D-14). Solo se escanean en
        # construcción cuando hay un backend explícito (o el llamador ya
        # pre-detectó): evita dependencia del estado real del equipo en tests.
        if self._explicit_mtp:
            for drive in utils.get_mounted_drives():
                # get_mounted_drives() devuelve dicts {"path","type","label"};
                # aceptamos también strings por robustez.
                drive_path = drive if isinstance(drive, str) else drive.get("path", "")
                if not drive_path:
                    continue
                if utils.is_removable_drive(drive_path):
                    row = self._add_source_row(
                        row, {"kind": "usb", "value": drive_path,
                              "camera": self.tr("Sin nombre"), "enabled": True,
                              "connected": True,
                              "label": self.tr("[USB] %1").arg(drive_path),
                              "type": "USB"})
        # Desconectados (D-03/D-12): filas atenuadas, no seleccionables
        for dev in devices_missing:
            device_id = dev["id"]
            # Los dispositivos FTP se gestionan en su propia sección; no mostrarlos aquí
            if device_id.startswith("ftp:"):
                continue
            saved_camera = db.get_dispositivo_for_device(device_id)
            name = saved_camera or dev.get("name") or device_id
            if device_id.startswith("usb:"):
                # Unidad USB masiva guardada: etiqueta/estilo propios, no [MTP]
                row = self._add_source_row(
                    row, {"kind": "usb", "value": device_id[len("usb:"):],
                          "camera": name, "enabled": False, "connected": False,
                          "label": self.tr("[USB] %1").arg(device_id[len("usb:"):]),
                          "type": "USB"})
            else:
                row = self._add_source_row(
                    row, {"kind": "device", "value": device_id, "camera": name,
                          "enabled": False, "connected": False,
                          "label": self.tr("[MTP] %1").arg(name), "type": "MTP"})

        # Sección WiFi
        row = self._add_section(row, self.tr("WiFi / PairDrop"))
        for sender in senders:
            name = sender["name"]
            sender_id = sender.get("id", name)  # Use unique ID if available
            used = sender.get("used")
            label = name + ("  " + self.tr("(ya asignado)") if used else "")
            # Check WiFi server status if callback provided
            wifi_connected = True
            if self.on_wifi_status is not None:
                try:
                    wifi_connected = self.on_wifi_status(sender_id)
                except Exception:
                    wifi_connected = False
            row = self._add_source_row(
                row, {"kind": "sender", "value": sender_id, "camera": name,
                      "enabled": True, "connected": wifi_connected,
                      "label": label, "type": "WiFi", "sender_name": name})

        # Sección FTP
        row = self._add_section(row, self.tr("FTP"))
        ftp_profiles = self._ftp_backend.list_profiles() if hasattr(
            self._ftp_backend, "list_profiles") else []
        for p in ftp_profiles:
            profile_id = p.get("id")
            device_id = f"ftp:{profile_id}"
            # Usar nombre de cámara guardado para perfiles FTP
            saved_camera = db.get_dispositivo_for_device(device_id)
            label = p.get("name") or ""
            camera = saved_camera or label or self.tr("Sin nombre")
            row = self._add_source_row(
                row, {"kind": "ftp_profile", "value": profile_id,
                      "camera": camera, "enabled": True, "connected": True,
                      "label": label or self.tr("(sin nombre)"), "type": "FTP"})

        self.table.setRowCount(row)

    def _add_section(self, row, title):
        self.table.insertRow(row)
        self._row_sources.append(None)
        section = QLabel(title)
        section.setStyleSheet(
            "font-weight: 600; font-size: 11px; color: {};"
            "background-color: {}; padding: 2px 6px;"
            .format(theme.color("text_secondary"), theme.color("bg_elevated")))
        # Celda combinada en todas las columnas (CHG-4)
        self.table.setSpan(row, 0, 1, self.table.columnCount())
        self.table.setCellWidget(row, 0, section)
        return row + 1

    def _add_source_row(self, row, src):
        self.table.insertRow(row)
        self._row_sources.append(src)

        # Col 0: checkbox de selección (sin marcar por defecto; el usuario
        # decide qué añadir). Las filas desconectadas quedan atenuadas (D-12).
        cb = QCheckBox()
        cb.setChecked(False)
        if not src.get("enabled") or not src.get("connected"):
            cb.setEnabled(False)
        cb.stateChanged.connect(self._update_ok_state)
        # Contenedor centrado (CHG-3)
        cb_wrap = QWidget()
        cb_lay = QHBoxLayout(cb_wrap)
        cb_lay.setContentsMargins(0, 0, 0, 0)
        cb_lay.setAlignment(Qt.AlignCenter)
        cb_lay.addWidget(cb)
        self.table.setCellWidget(row, 0, cb_wrap)

        # Col 1: ruta/origen + botón QR solo para WiFi (D-05/D-06)
        path_widget = QWidget()
        pl = QHBoxLayout(path_widget)
        pl.setContentsMargins(4, 0, 4, 0)
        pl.setSpacing(4)
        lbl = QLabel(src["label"])
        lbl.setToolTip(src.get("label", ""))
        if not src.get("connected"):
            lbl.setStyleSheet(
                "color: {}; font-size: 11px;".format(theme.color("text_secondary")))
        pl.addWidget(lbl, 1)
        if src["type"] == "WiFi":
            qr_btn = QPushButton(self.tr("QR"))
            qr_btn.setToolTip(self.tr("Mostrar el código QR de este dispositivo"))
            qr_btn.setCursor(Qt.PointingHandCursor)
            qr_btn.setStyleSheet(
                "QPushButton { border: none; text-align: left; padding: 2px 6px;"
                " color: %s; font-size: 11px; }"
                "QPushButton:hover { color: %s; }"
                % (theme.color("text_secondary"), theme.color("accent")))
            # Connect QR button to callback - use sender_name for display, value is sender_id
            sender_name = src.get("sender_name", src["value"])
            if self.on_qr is not None:
                qr_btn.clicked.connect(
                    lambda _=False, name=sender_name: self.on_qr(name))
            pl.addWidget(qr_btn)
        self.table.setCellWidget(row, 1, path_widget)

        # Col 2: nombre de cámara (editable o combo con conocidas, CHG-5/CHG-6);
        # para remitentes WiFi/FTP el nombre es fijo (bug 7).
        if src["type"] in ("WiFi", "FTP"):
            cam = self._build_fixed_name_widget(src)
        else:
            cam = self._build_camera_combo(row, src)
        if not src.get("connected"):
            cam.setEnabled(False)
        self.table.setCellWidget(row, 2, cam)

        # Col 3: estado activo/online
        if src.get("connected"):
            status = QLabel(self.tr("Conectado"))
            color = theme.color("success")
        else:
            status = QLabel(self.tr("Desconectado"))
            color = theme.color("danger")
        status.setStyleSheet("color: {}; font-size: 11px;".format(color))
        self.table.setCellWidget(row, 3, status)

        # Col 4: papelera borrar (D-11)
        trash = QPushButton()
        trash.setObjectName("IconButton")
        trivia_icon = theme.color("text_secondary")
        trash.setStyleSheet(
            "QPushButton { border: none; padding: 2px; }"
            "QPushButton:hover { color: %s; }" % theme.color("danger"))
        try:
            icons.apply(trash, "trash", size=16)
        except Exception:
            trash.setText(self.tr("Borrar"))
        trash.clicked.connect(
            lambda _=False, k=src["kind"], v=src["value"]:
            self._on_delete_clicked(k, v))
        self.table.setCellWidget(row, 4, trash)
        return row + 1

    def _known_camera_names(self):
        """Nombres de cámara conocidos en el sistema (CHG-5)."""
        try:
            from app.core.db import db
            return db.list_known_camera_names()
        except Exception:
            return []

    def _build_camera_combo(self, row, src):
        """Combo editable con nombres conocidos + disparador de detección (CHG-5/CHG-6)."""
        combo = QComboBox()
        combo.setEditable(True)
        combo.setInsertPolicy(QComboBox.NoInsert)
        known = self._known_camera_names()
        combo.addItems(known)
        # Bug 6: en ambos modos existe «— Vacío —» y es el estado por defecto
        # cuando la fila no tiene cámara; en auto va seguido del disparador de
        # detección.
        self._vacio_trigger_index = len(known)
        combo.addItem(self.tr("— Vacío —"))
        self._detect_trigger_index = self._vacio_trigger_index + 1
        if self._camera_detection_mode == "auto":
            combo.addItem(self.tr("🔍 Detectar cámara automáticamente…"))
        # Datos: -1 = normal (editable), índice de disparo especial
        for i in range(len(known)):
            combo.setItemData(i, i)
        combo.setItemData(self._vacio_trigger_index, "VACIO")
        if self._camera_detection_mode == "auto":
            combo.setItemData(self._detect_trigger_index, TRIGGER_DETECT)
        # Seleccionar el nombre actual si está en la lista; si no, escribirlo
        current = (src.get("camera") or "").strip()
        idx = combo.findText(current) if current else -1
        if idx >= 0:
            combo.setCurrentIndex(idx)
        elif current:
            combo.setEditText(current)
        else:
            combo.setCurrentIndex(self._vacio_trigger_index)
            # El campo queda vacío (la cámara no tiene nombre); el ítem
            # «— Vacío —» queda seleccionado de cara al desplegable.
            combo.setEditText("")
        combo.currentIndexChanged.connect(
            lambda i, r=row: self._on_camera_combo_changed(r, i))
        combo.lineEdit().textChanged.connect(self._update_ok_state)
        combo.lineEdit().textChanged.connect(
            lambda text, r=row: self._update_camera_in_row(r, text))
        if self.on_camera_name_changed is not None:
            combo.lineEdit().textChanged.connect(
                lambda text, r=row: self._on_camera_text_changed(r, text))
        return combo

    def _on_camera_text_changed(self, row, text):
        """Propaga el nombre editado al callback on_camera_name_changed.

        B-20: al editar el combo de un dispositivo conocido (o al detectarlo
        automáticamente), se notifica al llamador para persistir el nombre en
        device_settings. Solo aplica a filas con device_id (MTP/FTP); los
        textos de marcador de posición (Detectando/Sin nombre/Vacío) se
        ignoran para no guardar estados transitorios.
        """
        if self.on_camera_name_changed is None:
            return
        src = self._row_sources[row] if 0 <= row < len(self._row_sources) else None
        if not src:
            return
        kind = src.get("kind")
        value = src.get("value")
        if kind == "device":
            device_id = value
        elif kind == "ftp_profile":
            device_id = f"ftp:{value}"
        else:
            return
        if not device_id:
            return
        name = (text or "").strip()
        if not name:
            return
        placeholders = (self.tr("Detectando…"), self.tr("Sin nombre"),
                        self.tr("— Vacío —"))
        if name in placeholders:
            return
        self.on_camera_name_changed(device_id, name)

    def _on_camera_combo_changed(self, row, index):
        if index < 0:
            return
        combo = self.table.cellWidget(row, 2)
        if combo is None or not isinstance(combo, QComboBox):
            return
        item_data = combo.itemData(index)
        if item_data is TRIGGER_DETECT:
            src = self._row_sources[row] if 0 <= row < len(self._row_sources) else None
            if src is None or self.on_detect is None:
                return
            # Reset al valor anterior mientras se detecta (evita quedarse pegado)
            combo.blockSignals(True)
            combo.setEditText(self.tr("Detectando…"))
            combo.blockSignals(False)
            self._start_camera_detection(row, src)
        elif item_data == "VACIO":
            # En modo manual, "Vacío" deja el campo editable vacío
            combo.blockSignals(True)
            combo.setEditText("")
            combo.blockSignals(False)
            self._update_camera_in_row(row, "")
        else:
            # Seleccionó un nombre conocido → persistirlo
            text = combo.currentText().strip()
            if text:
                combo.setEditText(text)
                self._update_camera_in_row(row, text)

    # -- acciones ---------------------------------------------------------


    def _on_delete_clicked(self, kind, value):
        if self.on_delete is not None:
            accepted = self.on_delete(kind, value)
            if accepted is False:
                return
        # Quitar la fila de la tabla inmediatamente
        for i, src in enumerate(self._row_sources):
            if src is None:
                continue
            if src["kind"] == kind and src["value"] == value:
                self._remove_row(i)
                break

    def _remove_row(self, row):
        """Elimina la fila visual y del dict interno."""
        if 0 <= row < len(self._row_sources):
            self._row_sources.pop(row)
            self.table.removeRow(row)
            self._update_ok_state()

    def _browse_folder(self):
        start = ""
        path = QFileDialog.getExistingDirectory(
            self, self.tr("Seleccionar carpeta de origen"), start)
        if not path:
            return
        # Añadir como fila de carpeta local
        row = self._append_raw_source({
            "kind": "folder", "value": path, "camera": self.tr("Sin nombre"),
            "enabled": True, "connected": True,
            "label": path, "type": "FOLDER"},
            insert_before_row=self._section_start_row(1))
        self._update_ok_state()

    def _section_start_row(self, section_index):
        """Row index del encabezado de la sección section_index (0=física, 1=WiFi, 2=FTP)."""
        count = 0
        for i, src in enumerate(self._row_sources):
            if src is None:
                if count == section_index:
                    return i
                count += 1
        return len(self._row_sources)

    def _append_raw_source(self, src, insert_before_row=None):
        row = self.table.rowCount() if insert_before_row is None else insert_before_row
        self.table.insertRow(row)
        if insert_before_row is not None:
            self._row_sources.insert(row, src)
        else:
            self._row_sources.append(src)
        # reutilizamos _add_source_row sobre la fila recién creada no es trivial;
        # hacemos el render directo (equivalente a _add_source_row)
        cb = QCheckBox()
        cb.setChecked(False)
        if not src.get("enabled") or not src.get("connected"):
            cb.setEnabled(False)
        cb.stateChanged.connect(self._update_ok_state)
        cb_wrap = QWidget()
        cb_lay = QHBoxLayout(cb_wrap)
        cb_lay.setContentsMargins(0, 0, 0, 0)
        cb_lay.setAlignment(Qt.AlignCenter)
        cb_lay.addWidget(cb)
        self.table.setCellWidget(row, 0, cb_wrap)
        pw = QWidget()
        pl = QHBoxLayout(pw)
        pl.setContentsMargins(4, 0, 4, 0)
        lbl = QLabel(src["label"])
        if not src.get("connected"):
            lbl.setStyleSheet(
                "color: {}; font-size: 11px;".format(theme.color("text_secondary")))
        pl.addWidget(lbl, 1)
        self.table.setCellWidget(row, 1, pw)
        if src.get("kind") in ("sender", "ftp_profile"):
            # Bug 7: el nombre de WiFi/FTP es fijo (viene de la BD); un combo
            # con las cámaras USB/MTP confundiría al operador.
            cam = self._build_fixed_name_widget(src)
        else:
            cam = self._build_camera_combo(row, src)
        if not src.get("connected"):
            cam.setEnabled(False)
        self.table.setCellWidget(row, 2, cam)
        if src.get("connected"):
            status = QLabel(self.tr("Conectado"))
            color = theme.color("success")
        else:
            status = QLabel(self.tr("Desconectado"))
            color = theme.color("danger")
        status.setStyleSheet(
            "color: {}; font-size: 11px;".format(color))
        self.table.setCellWidget(row, 3, status)
        trash = QPushButton()
        trash.setObjectName("IconButton")
        trash.setStyleSheet(
            "QPushButton { border: none; padding: 2px; }"
            "QPushButton:hover { color: %s; }" % theme.color("danger"))
        try:
            icons.apply(trash, "trash", size=16)
        except Exception:
            trash.setText(self.tr("Borrar"))
        trash.setToolTip(self.tr("Borrar"))
        trash.clicked.connect(
            lambda _=False, k=src["kind"], v=src["value"]:
            self._on_delete_clicked(k, v))
        self.table.setCellWidget(row, 4, trash)
        return row

    def _build_fixed_name_widget(self, src):
        """Widget de solo lectura para nombres fijos (remitentes WiFi / FTP).

        Estos orígenes no permiten rebautizar: el nombre viene de la BD
        (inbox_senders/ftp_profiles) y no debe confundirse con un combo.
        """
        edit = QLineEdit(src.get("camera") or src.get("label") or "")
        edit.setReadOnly(True)
        edit.setToolTip(self.tr("Nombre fijo"))
        return edit

    def _detect_devices(self):
        """Re-enumera dispositivos MTP y unidades USB (D-08)."""
        self._refresh_physical_section()

    def _refresh_physical_section(self):
        devices = []
        try:
            devices = self._mtp_backend.list_devices()
        except Exception as e:
            self._show_wpd_error(e)
            devices = []
        connected_device_ids = {dev.device_id for dev in devices}
        connected_usb_paths = set()
        for drive in utils.get_mounted_drives():
            drive_path = drive if isinstance(drive, str) else drive.get("path", "")
            if drive_path and utils.is_removable_drive(drive_path):
                connected_usb_paths.add(drive_path)

        # Actualizar estado de dispositivos existentes en la sección física
        wifi_row = self._section_start_row(1)
        for row in range(wifi_row):
            src = self._row_sources[row] if row < len(self._row_sources) else None
            if src is None or src.get("kind") not in ("device", "usb"):
                continue
            device_id = src.get("value")
            if src["kind"] == "device":
                is_connected = device_id in connected_device_ids
            else:  # usb
                is_connected = device_id in connected_usb_paths
            
            if is_connected != src.get("connected", True):
                src["connected"] = is_connected
                src["enabled"] = is_connected
                # Actualizar checkbox
                cb_wrap = self.table.cellWidget(row, 0)
                if cb_wrap:
                    for cb in cb_wrap.findChildren(QCheckBox):
                        cb.setEnabled(is_connected)
                        if not is_connected:
                            cb.setChecked(False)
                # Actualizar label de ruta (color)
                path_widget = self.table.cellWidget(row, 1)
                if path_widget:
                    for lbl in path_widget.findChildren(QLabel):
                        if not is_connected:
                            lbl.setStyleSheet(
                                "color: {}; font-size: 11px;".format(theme.color("text_secondary")))
                        else:
                            lbl.setStyleSheet("")
                # Actualizar combo de cámara
                cam_widget = self.table.cellWidget(row, 2)
                if cam_widget:
                    cam_widget.setEnabled(is_connected)
                # Actualizar estado
                status_widget = self.table.cellWidget(row, 3)
                if status_widget and isinstance(status_widget, QLabel):
                    if is_connected:
                        status_widget.setText(self.tr("Conectado"))
                        status_widget.setStyleSheet("color: {}; font-size: 11px;".format(theme.color("success")))
                    else:
                        status_widget.setText(self.tr("Desconectado"))
                        status_widget.setStyleSheet("color: {}; font-size: 11px;".format(theme.color("danger")))

        # Añadir nuevos dispositivos no presentes ya
        for dev in devices:
            if self._row_for_source("device", dev.device_id) is not None:
                continue
            device_id = dev.device_id
            saved_camera = db.get_dispositivo_for_device(device_id)
            name = saved_camera or dev.name or device_id
            self._append_raw_source({
                "kind": "device", "value": device_id, "camera": name,
                "enabled": True, "connected": True,
                "label": self.tr("[MTP] %1").arg(name), "type": "MTP"},
                insert_before_row=wifi_row)
            # Persist MTP device to known_devices for cross-project persistence
            try:
                db.upsert_known_device(device_id, "mtp", name=name, last_camera=name)
            except Exception:
                pass
            wifi_row += 1
        for drive in utils.get_mounted_drives():
            drive_path = drive if isinstance(drive, str) else drive.get("path", "")
            if not drive_path:
                continue
            if utils.is_removable_drive(drive_path) and \
                    self._row_for_source("usb", drive_path) is None:
                self._append_raw_source({
                    "kind": "usb", "value": drive_path, "camera": self.tr("Sin nombre"),
                    "enabled": True, "connected": True,
                    "label": self.tr("[USB] %1").arg(drive_path), "type": "USB"},
                    insert_before_row=wifi_row)
                # Persist USB drive to known_devices for cross-project persistence
                try:
                    db.upsert_known_device(f"usb:{drive_path}", "usb",
                                           name=drive_path,
                                           last_camera=self.tr("Sin nombre"))
                except Exception:
                    pass
                wifi_row += 1
        self._update_ok_state()

    def _import_json(self):
        """Importa dispositivos conocidos desde un archivo JSON (backup/restore)."""
        import json
        path, _ = QFileDialog.getOpenFileName(
            self, self.tr("Importar dispositivos conocidos"),
            "", self.tr("JSON (*.json)"))
        if not path:
            return
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            if not isinstance(data, list):
                raise ValueError(self.tr("El JSON debe ser una lista de dispositivos"))
            count = 0
            for d in data:
                if not all(k in d for k in ("device_id", "device_type")):
                    continue
                db.upsert_known_device(
                    d["device_id"], d["device_type"],
                    d.get("name"), d.get("serial"),
                    d.get("last_camera"), d.get("metadata"))
                count += 1
            # Mostrar los importados como filas desconectadas si no están ya.
            self._sync_imported_devices(data)
            QMessageBox.information(
                self, self.tr("Importación completada"),
                self.tr("Se importaron %1 dispositivos.").arg(count))
        except Exception as e:
            QMessageBox.critical(
                self, self.tr("Error"),
                self.tr("No se pudo importar: %1").arg(str(e)))

    def _sync_imported_devices(self, data):
        """Añade como filas «Desconectado» los dispositivos importados que
        no aparecen ya en la tabla (MTP/USB; WiFi va por senders, FTP por
        perfiles). Evita repoblar toda la tabla para no perder selecciones."""
        wifi_row = self._section_start_row(1)
        for d in data:
            did = d.get("device_id") or ""
            dtype = d.get("device_type") or ""
            if not did:
                continue
            if dtype in ("wifi", "folder") or did.startswith("wifi:"):
                continue
            if self._row_for_source("device", did) is not None:
                continue
            name = d.get("name") or did
            if did.startswith("usb:"):
                self._append_raw_source(
                    {"kind": "usb", "value": did[len("usb:"):], "camera": name,
                     "enabled": False, "connected": False,
                     "label": self.tr("[USB] %1").arg(did[len("usb:"):]),
                     "type": "USB"},
                    insert_before_row=wifi_row)
            else:
                self._append_raw_source(
                    {"kind": "device", "value": did, "camera": name,
                     "enabled": False, "connected": False,
                     "label": self.tr("[MTP] %1").arg(name), "type": "MTP"},
                    insert_before_row=wifi_row)
            wifi_row += 1

    def _export_json(self):
        """Exporta dispositivos conocidos a un archivo JSON (backup)."""
        import json
        path, _ = QFileDialog.getSaveFileName(
            self, self.tr("Exportar dispositivos conocidos"),
            "known_devices.json", self.tr("JSON (*.json)"))
        if not path:
            return
        try:
            devices = db.list_known_devices()
            export_data = []
            for d in devices:
                export_data.append({
                    "device_id": d["device_id"],
                    "device_type": d["device_type"],
                    "name": d["name"],
                    "serial": d["serial"],
                    "last_camera": d["last_camera"],
                    "last_seen": d["last_seen"],
                    "metadata": d["metadata"],
                })
            with open(path, "w", encoding="utf-8") as f:
                json.dump(export_data, f, ensure_ascii=False, indent=2)
            QMessageBox.information(
                self, self.tr("Exportación completada"),
                self.tr("Se exportaron %1 dispositivos.").arg(len(export_data)))
        except Exception as e:
            QMessageBox.critical(
                self, self.tr("Error"),
                self.tr("No se pudo exportar: %1").arg(str(e)))

    def _add_wifi_row(self):
        """Crea un nuevo remitente WiFi real (no placeholder)."""
        from PySide6.QtWidgets import QInputDialog, QMessageBox
        from app.core.db import db
        name, ok = QInputDialog.getText(
            self, self.tr("Nuevo dispositivo WiFi"),
            self.tr("Nombre del dispositivo (aparecerá en el código QR):"),
            text=self.tr("Móvil"))
        if not ok or not name.strip():
            return
        name = name.strip()
        try:
            sender_id = db.add_inbox_sender(name)
        except Exception as e:
            QMessageBox.warning(self, self.tr("Error"),
                                self.tr("No se pudo crear el remitente: %1").arg(str(e)))
            return
        # Check WiFi server status if callback provided
        wifi_connected = True
        if self.on_wifi_status is not None:
            try:
                wifi_connected = self.on_wifi_status(sender_id)
            except Exception:
                wifi_connected = False
        row = self._append_raw_source({
            "kind": "sender", "value": sender_id, "camera": name,
            "enabled": True, "connected": wifi_connected,
            "label": name, "type": "WiFi", "sender_name": name},
            insert_before_row=self._section_start_row(2))
        self._update_ok_state()

    def _add_ftp_row(self):
        """Abre el selector de FTP para crear/seleccionar un perfil."""
        from app.ui.ftp_picker import FtpPickerDialog
        dialog = FtpPickerDialog(self)
        if dialog.exec() != QDialog.Accepted:
            return
        if not dialog.device_id or not dialog.device_folder:
            return
        # Add as a real row with the selected FTP profile
        name = dialog.device_name or dialog.device_folder
        row = self._append_raw_source({
            "kind": "ftp_profile", "value": dialog.device_id,
            "camera": name, "enabled": True, "connected": True,
            "label": name, "type": "FTP"})
        self._update_ok_state()

    # -- detección de cámara (D-08/D-09) ----------------------------------

    def _detect_camera_for_row(self, row):
        cam = self.table.cellWidget(row, 2)
        if cam is None:
            return
        text = _camera_text(cam)
        if text.strip():
            return
        src = self._row_sources[row]
        if src is None:
            return
        if self.on_detect is None:
            return
        self._start_camera_detection(row, src)

    def _start_camera_detection(self, row, src):
        cam = self.table.cellWidget(row, 2)
        if isinstance(cam, QComboBox):
            cam.setEnabled(False)
            combo = cam
            if hasattr(combo, "lineEdit") and combo.lineEdit() is not None:
                combo.setEditText(self.tr("Detectando…"))
        else:
            cam.setText(self.tr("Detectando…"))
            cam.setEnabled(False)
        src = dict(src)
        src["_row"] = row
        worker = _CameraDetectWorker(self.on_detect, src, self._cam_executor)
        worker.done.connect(self._on_camera_detected)
        self._cam_worker = worker
        worker.start()

    def _on_camera_detected(self, row, ok, name):
        if row is None or row < 0 or row >= self.table.rowCount():
            row = self.table.rowCount() - 1
        cam = self.table.cellWidget(row, 2)
        if cam is None:
            return
        result = name if ok and name else self.tr("Sin nombre")
        if isinstance(cam, QComboBox):
            cam.setEnabled(True)
            self._set_combo_text(cam, result)
        else:
            cam.setEnabled(True)
            cam.setText(result)
        self._update_ok_state()
        # Persistir nombre detectado automáticamente a known_devices (REQ-09)
        if ok and name and self.on_camera_name_changed:
            src = self._row_sources[row] if 0 <= row < len(self._row_sources) else None
            if src:
                device_id = src.get("value")
                if device_id:
                    self.on_camera_name_changed(device_id, name)

    @staticmethod
    def _set_combo_text(combo, text):
        """Escribe text en un combo editable sin disparar índices de disparo ni señales."""
        combo.blockSignals(True)
        le = combo.lineEdit()
        if le:
            le.blockSignals(True)
        idx = combo.findText(text)
        if idx >= 0:
            combo.setCurrentIndex(idx)
        else:
            combo.setEditText(text)
        if le:
            le.setText(text)
            le.blockSignals(False)
        combo.blockSignals(False)

    # -- estado de aceptar -------------------------------------------------

    def _update_ok_state(self, *_):
        self.btn_aceptar.setEnabled(self._has_valid_selection())

    def _has_valid_selection(self):
        for i, src in enumerate(self._row_sources):
            if src is None:
                continue
            if not self._checkbox_checked(i):
                continue
            cam = self.table.cellWidget(i, 2)
            if _camera_text(cam).strip():
                return True
        return False

    # -- resultado --------------------------------------------------------

    def accept(self):
        # En modo manual, si hay orígenes seleccionados con cámara "Vacío" (vacía),
        # mostrar diálogo de renombrado para cada uno antes de aceptar
        if self._camera_detection_mode == "manual":
            from PySide6.QtWidgets import QInputDialog, QMessageBox
            for i, src in enumerate(self._row_sources):
                if src is None:
                    continue
                if not self._checkbox_checked(i):
                    continue
                cam = self.table.cellWidget(i, 2)
                camera = _camera_text(cam).strip()
                if not camera:
                    # Preguntar nombre de dispositivo
                    name, ok = QInputDialog.getText(
                        self, self.tr("Renombrar dispositivo"),
                        self.tr("Nombre del dispositivo para %1:").arg(src.get("label", src["value"])),
                        text=""
                    )
                    if not ok:
                        return  # Usuario canceló, no cerrar diálogo
                    if not name.strip():
                        QMessageBox.warning(
                            self, self.tr("Nombre requerido"),
                            self.tr("Debe introducir un nombre de dispositivo."))
                        return
                    # Actualizar el combo con el nombre ingresado
                    self._set_combo_text(cam, name.strip())
                    self._update_camera_in_row(i, name.strip())
        self._accepted = True
        super().accept()

    def reject(self):
        self._accepted = False
        super().reject()

    def result_sources(self):
        """Lista de dicts con los orígenes marcados (vacía si se canceló)."""
        if self._accepted is False:
            return []
        out = []
        for i, src in enumerate(self._row_sources):
            if src is None:
                continue
            if not self._checkbox_checked(i):
                continue
            cam = self.table.cellWidget(i, 2)
            camera = _camera_text(cam).strip()
            out.append({"kind": src["kind"], "value": src["value"],
                        "camera": camera, "enabled": True})
        return out

    # -- utilidades -------------------------------------------------------

    def _show_wpd_error(self, e):
        """Aviso non-bloqueante cuando falla el acceso WPD (D-15)."""
        self.error_label.setText(
            self.tr("No se pudo acceder a los dispositivos MTP: %1").arg(str(e)))
        self.error_label.setVisible(True)

    def _row_for_source(self, kind, value):
        for i, src in enumerate(self._row_sources):
            if src is None:
                continue
            if src["kind"] != kind:
                continue
            if isinstance(value, tuple) and isinstance(src["value"], tuple):
                if src["value"][0] == value[0]:
                    return i
            elif src["value"] == value:
                return i
        return None

    def _update_camera_in_row(self, row, text):
        """Persiste el nombre de cámara editado en el dict interno."""
        if 0 <= row < len(self._row_sources) and self._row_sources[row] is not None:
            self._row_sources[row]["camera"] = text.strip()

    def _checkbox_checked(self, row):
        """True si el QCheckBox de la fila está marcado (dentro del contenedor centrado)."""
        wrap = self.table.cellWidget(row, 0)
        if wrap is None:
            return False
        for ch in wrap.findChildren(QCheckBox):
            return ch.isChecked()
        return False
