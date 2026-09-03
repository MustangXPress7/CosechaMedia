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
    QCheckBox, QDialog, QFileDialog, QHBoxLayout, QHeaderView, QLabel,
    QLineEdit, QPushButton, QTableWidget, QTableWidgetItem, QVBoxLayout,
    QWidget,
)

from app.core import utils
from app.core import mtp
from app.core import ftp as ftpmod
from app.core.translator import QtString
from app.ui import theme
from app.ui import icons


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
                 on_delete=None, on_detect=None):
        super().__init__(parent)
        self.on_delete = on_delete      # on_delete(kind, value) -> bool
        self.on_detect = on_detect      # on_detect(kind, value) -> str (cámara)
        self._mtp_backend = mtp_backend if mtp_backend is not None else mtp.WpdBackend()
        self._explicit_mtp = mtp_backend is not None
        self._ftp_backend = ftp_backend or ftpmod.FtpBackend()
        self._row_sources = []          # dict por fila de datos (None = cabecera)
        self._cam_executor = ThreadPoolExecutor(max_workers=1)
        self._cam_worker = None
        self._accepted = None   # None=sin decidir, True=aceptado, False=cancelado

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
            self.tr("Seleccionar"), self.tr("Ruta de origen"), self.tr("Cámara"),
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
            name = dev.name or dev.device_id
            row = self._add_source_row(
                row, {"kind": "device", "value": dev.device_id,
                      "camera": name, "enabled": True, "connected": True,
                      "label": self.tr("[MTP] %1").arg(name),
                      "type": "MTP"})
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
            name = dev.get("name") or dev.get("id") or ""
            row = self._add_source_row(
                row, {"kind": "device", "value": dev["id"], "camera": name,
                      "enabled": False, "connected": False,
                      "label": self.tr("[MTP] %1").arg(name), "type": "MTP"})

        # Sección WiFi
        row = self._add_section(row, self.tr("WiFi / PairDrop"))
        for sender in senders:
            name = sender["name"]
            used = sender.get("used")
            label = name + ("  " + self.tr("(ya asignado)") if used else "")
            row = self._add_source_row(
                row, {"kind": "sender", "value": name, "camera": name,
                      "enabled": True, "connected": True,
                      "label": label, "type": "WiFi"})

        # Sección FTP
        row = self._add_section(row, self.tr("FTP"))
        ftp_profiles = self._ftp_backend.list_profiles() if hasattr(
            self._ftp_backend, "list_profiles") else []
        for p in ftp_profiles:
            label = p.get("name") or ""
            row = self._add_source_row(
                row, {"kind": "ftp_profile", "value": p.get("id"),
                      "camera": label or self.tr("Sin nombre"),
                      "enabled": True, "connected": True,
                      "label": label or self.tr("(sin nombre)"), "type": "FTP"})

        self.table.setRowCount(row)

    def _add_section(self, row, title):
        self.table.insertRow(row)
        self._row_sources.append(None)
        section = QLabel(title)
        section.setStyleSheet(
            "font-weight: 600; font-size: 11px; color: {};"
            .format(theme.color("text_secondary")))
        self.table.setCellWidget(row, 1, section)
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
        self.table.setCellWidget(row, 0, cb)

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
            pl.addWidget(qr_btn)
        self.table.setCellWidget(row, 1, path_widget)

        # Col 2: nombre de cámara (editable)
        cam = QLineEdit()
        cam.setText(src["camera"])
        if not src.get("connected"):
            cam.setEnabled(False)
        cam.textChanged.connect(self._update_ok_state)
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

    # -- acciones ---------------------------------------------------------

    def _on_delete_clicked(self, kind, value):
        if self.on_delete is not None:
            self.on_delete(kind, value)

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
            "label": path, "type": "FOLDER"})
        self._update_ok_state()

    def _append_raw_source(self, src):
        row = self.table.rowCount()
        self.table.insertRow(row)
        self._row_sources.append(src)
        # reutilizamos _add_source_row sobre la fila recién creada no es trivial;
        # hacemos el render directo
        cb = QCheckBox()
        cb.setChecked(False)
        cb.stateChanged.connect(self._update_ok_state)
        self.table.setCellWidget(row, 0, cb)
        pw = QWidget()
        pl = QHBoxLayout(pw)
        pl.setContentsMargins(4, 0, 4, 0)
        pl.addWidget(QLabel(src["label"]), 1)
        self.table.setCellWidget(row, 1, pw)
        cam = QLineEdit()
        cam.setText(src["camera"])
        cam.textChanged.connect(self._update_ok_state)
        self.table.setCellWidget(row, 2, cam)
        status = QLabel(self.tr("Conectado"))
        status.setStyleSheet(
            "color: {}; font-size: 11px;".format(theme.color("success")))
        self.table.setCellWidget(row, 3, status)
        trash = QPushButton(self.tr("Borrar"))
        trash.clicked.connect(
            lambda _=False, k=src["kind"], v=src["value"]:
            self._on_delete_clicked(k, v))
        self.table.setCellWidget(row, 4, trash)
        return row

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
        # Reconstruir toda la tabla es costoso; aquí re-renderizamos la sección
        # física añadiendo los dispositivos no presentes ya.
        for dev in devices:
            if self._row_for_source("device", dev.device_id) is not None:
                continue
            name = dev.name or dev.device_id
            self._append_raw_source({
                "kind": "device", "value": dev.device_id, "camera": name,
                "enabled": True, "connected": True,
                "label": self.tr("[MTP] %1").arg(name), "type": "MTP"})
        for drive in utils.get_mounted_drives():
            drive_path = drive if isinstance(drive, str) else drive.get("path", "")
            if not drive_path:
                continue
            if utils.is_removable_drive(drive_path) and \
                    self._row_for_source("usb", drive_path) is None:
                self._append_raw_source({
                    "kind": "usb", "value": drive_path, "camera": self.tr("Sin nombre"),
                    "enabled": True, "connected": True,
                    "label": self.tr("[USB] %1").arg(drive_path), "type": "USB"})
        self._update_ok_state()

    def _add_wifi_row(self):
        self._append_raw_source({
            "kind": "sender", "value": self.tr("Nuevo WiFi"),
            "camera": self.tr("Sin nombre"), "enabled": True, "connected": True,
            "label": self.tr("Nuevo WiFi"), "type": "WiFi"})
        self._update_ok_state()

    def _add_ftp_row(self):
        self._append_raw_source({
            "kind": "ftp_profile", "value": None, "camera": self.tr("Sin nombre"),
            "enabled": True, "connected": True,
            "label": self.tr("FTP nuevo"), "type": "FTP"})
        self._update_ok_state()

    # -- detección de cámara (D-08/D-09) ----------------------------------

    def _detect_camera_for_row(self, row):
        cam = self.table.cellWidget(row, 2)
        if cam is None or cam.text().strip():
            return
        src = self._row_sources[row]
        if src is None:
            return
        if self.on_detect is None:
            return
        self._start_camera_detection(row, src)

    def _start_camera_detection(self, row, src):
        cam = self.table.cellWidget(row, 2)
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
        cam.setEnabled(True)
        cam.setText(name if ok and name else self.tr("Sin nombre"))
        self._update_ok_state()

    # -- estado de aceptar -------------------------------------------------

    def _update_ok_state(self, *_):
        self.btn_aceptar.setEnabled(self._has_valid_selection())

    def _has_valid_selection(self):
        for i, src in enumerate(self._row_sources):
            if src is None:
                continue
            cb = self.table.cellWidget(i, 0)
            if not isinstance(cb, QCheckBox) or not cb.isChecked():
                continue
            cam = self.table.cellWidget(i, 2)
            if isinstance(cam, QLineEdit) and cam.text().strip():
                return True
        return False

    # -- resultado --------------------------------------------------------

    def accept(self):
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
            cb = self.table.cellWidget(i, 0)
            if not isinstance(cb, QCheckBox) or not cb.isChecked():
                continue
            cam = self.table.cellWidget(i, 2)
            camera = cam.text().strip() if isinstance(cam, QLineEdit) else ""
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
