"""Selector de carpetas de dispositivos MTP (móviles/cámaras) vía WPD."""

import sys

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QComboBox, QDialog, QHBoxLayout, QLabel, QMessageBox, QPushButton,
    QTreeWidget, QTreeWidgetItem, QVBoxLayout, QWidget,
)

from app.core import mtp
from app.core.translator import QtString
from app.ui import theme

_DCIM_HINTS = ("dcim", "picture", "foto", "cámara", "camara", "100dci", "100media")


class MtpDevicePane(QWidget):
    """Panel reutilizable de selección de carpeta MTP (móviles/cámaras vía WPD).

    No incluye fila de botones Aceptar/Cancelar: el contenedor (diálogo o
    pestaña) gestiona la confirmación. Emite ``selection_changed`` con un
    bool (¿listo para aceptar?) y ``activate_requested`` en doble clic válido.
    La carga de dispositivos es diferida (``ensure_loaded``) para no tocar WPD
    hasta que el usuario abre el panel.
    """

    selection_changed = Signal(bool)
    activate_requested = Signal()

    def tr(self, text, *args, **kwargs):
        return QtString(super().tr(text, *args, **kwargs))

    def __init__(self, parent=None, backend=None):
        super().__init__(parent)
        self._backend = backend or mtp.WpdBackend()
        self._devices = []
        self._node_path = {}
        self._loaded = False
        self.device_id = ""
        self.device_name = ""
        self.device_folder = ""
        self._build_ui()

    def ensure_loaded(self):
        if not self._loaded:
            self._loaded = True
            self._load_devices()

    def can_accept(self):
        return bool(self._current_device_id() and self._selected_path())

    def commit(self):
        """Rellena ``device_id``/``device_name``/``device_folder`` si hay
        selección válida. Devuelve bool."""
        device_id = self._current_device_id()
        path = self._selected_path()
        if not device_id or not path:
            return False
        idx = self.device_combo.currentIndex()
        self.device_id = device_id
        self.device_name = self._devices[idx].name if 0 <= idx < len(self._devices) else device_id
        self.device_folder = path
        return True

    # -- UI --------------------------------------------------------------

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(8)

        hint = QLabel(
            self.tr("Conecta el móvil o la cámara por USB y elige la carpeta a importar.")
        )
        hint.setWordWrap(True)
        hint.setStyleSheet("color: {}; font-size: 12px;".format(theme.color("text_secondary")))
        layout.addWidget(hint)

        row = QHBoxLayout()
        row.addWidget(QLabel(self.tr("Dispositivo:")))
        self.device_combo = QComboBox()
        self.device_combo.setMinimumWidth(260)
        self.device_combo.currentIndexChanged.connect(self._on_device_changed)
        row.addWidget(self.device_combo, 1)
        self.refresh_btn = QPushButton(self.tr("Actualizar"))
        self.refresh_btn.clicked.connect(self._load_devices)
        row.addWidget(self.refresh_btn)
        layout.addLayout(row)

        self.tree = QTreeWidget()
        self.tree.setHeaderHidden(True)
        self.tree.setAlternatingRowColors(True)
        self.tree.itemExpanded.connect(self._on_item_expanded)
        self.tree.itemSelectionChanged.connect(self._update_ok_state)
        self.tree.itemDoubleClicked.connect(self._on_item_double_clicked)
        layout.addWidget(self.tree, 1)

        self.selection_label = QLabel("")
        self.selection_label.setStyleSheet(
            "color: {}; font-size: 11px;".format(theme.color("text_secondary"))
        )
        layout.addWidget(self.selection_label)

    # -- carga de datos ---------------------------------------------------

    def _load_devices(self):
        try:
            self._devices = self._backend.list_devices()
        except Exception as e:
            # En plataformas sin WPD (Linux/macOS) basta con el estado vacío;
            # en Windows el aviso modal ayuda a diagnosticar el fallo.
            if sys.platform == "win32":
                QMessageBox.warning(self, self.tr("Dispositivo"), str(e))
            self._devices = []
        self.device_combo.blockSignals(True)
        self.device_combo.clear()
        for dev in self._devices:
            self.device_combo.addItem(dev.name, dev.device_id)
        self.device_combo.blockSignals(False)
        self._on_device_changed()

    def _current_device_id(self):
        idx = self.device_combo.currentIndex()
        if 0 <= idx < len(self._devices):
            return self._devices[idx].device_id
        return None

    def _on_device_changed(self, *_):
        self.tree.clear()
        self._node_path = {}
        self._update_ok_state()
        device_id = self._current_device_id()
        if device_id is None:
            self.selection_label.setText(
                self.tr("No se detectaron dispositivos. Revisa el cable y pulsa Actualizar.")
            )
            return
        self.selection_label.setText(self.tr("Cargando…"))
        try:
            storages = self._backend.list_children(device_id, "")
        except Exception as e:
            self.selection_label.setText(
                self.tr("No se pudo leer el dispositivo: %1").arg(str(e))
            )
            return
        for st in storages:
            item = QTreeWidgetItem([st.name])
            item.setIcon(0, self._folder_icon())
            item.setData(0, Qt.UserRole, {"path": st.name, "loaded": False})
            item.setChildIndicatorPolicy(QTreeWidgetItem.ShowIndicator)
            self.tree.addTopLevelItem(item)
        self._suggest_dcim()

    def _folder_icon(self):
        from PySide6.QtWidgets import QStyle
        return self.style().standardIcon(QStyle.SP_DirIcon)

    def _load_children(self, item):
        data = item.data(0, Qt.UserRole) or {}
        if data.get("loaded"):
            return
        device_id = self._current_device_id()
        if device_id is None:
            return
        path = data["path"]
        try:
            children = self._backend.list_children(device_id, path)
        except Exception:
            children = []
        self._load_children_into(item, children)

    def _suggest_dcim(self):
        """Preselecciona DCIM (o una carpeta de imágenes) del primer storage."""
        device_id = self._current_device_id()
        if device_id is None:
            return
        for i in range(self.tree.topLevelItemCount()):
            storage_item = self.tree.topLevelItem(i)
            path = storage_item.data(0, Qt.UserRole)["path"]
            try:
                children = self._backend.list_children(device_id, path)
            except Exception:
                continue
            for child in children:
                if not child.is_dir:
                    continue
                low = child.name.lower()
                if any(h in low for h in _DCIM_HINTS):
                    self._load_children_into(storage_item, children)
                    target = None
                    for j in range(storage_item.childCount()):
                        cand = storage_item.child(j)
                        if cand.text(0) == child.name:
                            target = cand
                            break
                    if target is not None:
                        storage_item.setExpanded(True)
                        self.tree.setCurrentItem(target)
                    return

    def _load_children_into(self, item, children):
        data = item.data(0, Qt.UserRole) or {}
        data["loaded"] = True
        item.setData(0, Qt.UserRole, data)
        path = data["path"]
        for child in children:
            child_item = QTreeWidgetItem([child.name])
            child_item.setData(0, Qt.UserRole, {"path": path + "/" + child.name, "loaded": False})
            if child.is_dir:
                child_item.setIcon(0, self._folder_icon())
                child_item.setChildIndicatorPolicy(QTreeWidgetItem.ShowIndicator)
            item.addChild(child_item)

    def _on_item_expanded(self, item):
        self._load_children(item)

    def _on_item_double_clicked(self, item, _col):
        if item.childCount() > 0:
            return
        if self.can_accept():
            self.activate_requested.emit()

    def _selected_path(self):
        items = self.tree.selectedItems()
        if not items:
            return ""
        data = items[0].data(0, Qt.UserRole) or {}
        return data.get("path", "")

    def _update_ok_state(self, *_):
        path = self._selected_path()
        self.selection_label.setText(path)
        self.selection_changed.emit(bool(path))


class DevicePickerDialog(QDialog):
    """Diálogo para elegir una carpeta de un dispositivo MTP.

    Al aceptar expone ``device_id``, ``device_name`` y ``device_folder``
    (ruta relativa con "/", p. ej. ``"Almacenamiento interno compartido/DCIM"``).
    """

    def tr(self, text, *args, **kwargs):
        return QtString(super().tr(text, *args, **kwargs))

    def __init__(self, parent=None, backend=None):
        super().__init__(parent)
        self.device_id = ""
        self.device_name = ""
        self.device_folder = ""

        self.setWindowTitle(self.tr("Seleccionar carpeta del dispositivo"))
        self.resize(680, 500)
        self._build_ui(backend)

    def _build_ui(self, backend):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(8)

        self.pane = MtpDevicePane(self, backend=backend)
        layout.addWidget(self.pane, 1)

        buttons = QHBoxLayout()
        self.ok_btn = QPushButton(self.tr("Aceptar"))
        self.ok_btn.setObjectName("PrimaryAction")
        self.ok_btn.setEnabled(False)
        self.ok_btn.clicked.connect(self.accept)
        cancel_btn = QPushButton(self.tr("Cancelar"))
        cancel_btn.clicked.connect(self.reject)
        buttons.addStretch()
        buttons.addWidget(self.ok_btn)
        buttons.addWidget(cancel_btn)
        layout.addLayout(buttons)

        self.pane.selection_changed.connect(self.ok_btn.setEnabled)
        self.pane.activate_requested.connect(self.accept)
        self.pane.ensure_loaded()

    def accept(self):
        if not self.pane.commit():
            return
        self.device_id = self.pane.device_id
        self.device_name = self.pane.device_name
        self.device_folder = self.pane.device_folder
        super().accept()
