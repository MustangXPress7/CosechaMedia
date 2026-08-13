"""Selector unificado de origen para sesiones.

Agrupa los orígenes guardados (carpetas recientes, remitentes WiFi y perfiles
FTP) en un único diálogo, de modo que una sesión pueda quedarse con un
remitente WiFi sin duplicar cachés. Al aceptar expone ``kind`` (``"folder"``,
``"sender"``, ``"ftp_profile"`` o ``"browse"``) y ``value``.
"""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog, QHBoxLayout, QLabel, QListWidget, QListWidgetItem,
    QPushButton, QVBoxLayout,
)

from app.core.translator import QtString


class SourcePickerDialog(QDialog):
    """Lista agrupada de orígenes guardados para asignar a una sesión.

    ``folders``: rutas de carpetas (recientes / del proyecto).
    ``senders``: dicts con ``name`` y ``used`` (ya tiene sesión en el proyecto).
    ``ftp_profiles``: dicts con ``id``, ``name`` y ``host``.
    """

    def tr(self, text, *args, **kwargs):
        return QtString(super().tr(text, *args, **kwargs))

    def __init__(self, parent=None, folders=(), senders=(), ftp_profiles=()):
        super().__init__(parent)
        self.kind = None
        self.value = None
        self.setWindowTitle(self.tr("Seleccionar origen"))
        self.setMinimumWidth(460)
        self._build_ui(folders, senders, ftp_profiles)

    def _build_ui(self, folders, senders, ftp_profiles):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(10)

        hint = QLabel(
            self.tr("Elige un origen guardado para la sesión o explora una carpeta:"))
        hint.setWordWrap(True)
        layout.addWidget(hint)

        self.list_widget = QListWidget()
        self.list_widget.itemDoubleClicked.connect(self._accept_item)
        layout.addWidget(self.list_widget)

        self._add_section(self.tr("Carpetas guardadas"), folders, self._folder_item)
        self._add_section(self.tr("Remitentes WiFi"), senders, self._sender_item)
        self._add_section(self.tr("Dispositivos FTP guardados"),
                          ftp_profiles, self._ftp_item)

        buttons = QHBoxLayout()
        browse_btn = QPushButton(self.tr("Examinar…"))
        browse_btn.clicked.connect(self._browse)
        buttons.addWidget(browse_btn)
        buttons.addStretch()
        cancel_btn = QPushButton(self.tr("Cancelar"))
        cancel_btn.clicked.connect(self.reject)
        ok_btn = QPushButton(self.tr("Aceptar"))
        ok_btn.setObjectName("PrimaryAction")
        ok_btn.clicked.connect(self._accept_current)
        buttons.addWidget(cancel_btn)
        buttons.addWidget(ok_btn)
        layout.addLayout(buttons)

    def _add_section(self, title, items, make_item):
        header = QListWidgetItem(title)
        header.setFlags(Qt.ItemIsEnabled)
        font = header.font()
        font.setBold(True)
        header.setFont(font)
        self.list_widget.addItem(header)
        if not items:
            empty = QListWidgetItem(self.tr("(vacío)"))
            empty.setFlags(Qt.ItemIsEnabled)
            self.list_widget.addItem(empty)
            return
        for item in items:
            self.list_widget.addItem(make_item(item))

    def _folder_item(self, path):
        item = QListWidgetItem(path)
        item.setData(Qt.UserRole, ("folder", path))
        item.setToolTip(path)
        return item

    def _sender_item(self, sender):
        label = sender["name"]
        if sender.get("used"):
            label += "  " + self.tr("(ya asignado)")
        item = QListWidgetItem(label)
        item.setData(Qt.UserRole, ("sender", sender["name"]))
        item.setToolTip(sender["name"])
        return item

    def _ftp_item(self, profile):
        label = f"{profile['name']} ({profile['host']})"
        item = QListWidgetItem(label)
        item.setData(Qt.UserRole, ("ftp_profile", profile["id"]))
        item.setToolTip(label)
        return item

    def _browse(self):
        self.kind = "browse"
        self.value = None
        self.accept()

    def _accept_item(self, item):
        self._set_from_item(item)
        if self.kind is not None:
            self.accept()

    def _accept_current(self):
        item = self.list_widget.currentItem()
        if item is not None:
            self._set_from_item(item)
        if self.kind is not None:
            self.accept()

    def _set_from_item(self, item):
        role = item.data(Qt.UserRole)
        if role is not None:
            self.kind, self.value = role
