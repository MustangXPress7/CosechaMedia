"""Lanzador compacto de orígenes para sesiones.

Muestra los orígenes guardados (carpetas recientes y remitentes WiFi) y los
dispositivos conocidos pero no conectados, en una única lista por secciones.
Cada flujo de búsqueda (Examinar, USB/MTP, FTP, WiFi QR) abre su propia
ventana desde los botones. Al aceptar expone ``kind`` y ``value``:

- Guardados: ``"folder"``/``"sender"`` o ``"browse"``.
- Dispositivos: ``"device"`` (MTP) o ``"ftp_new"`` (FTP) con los datos en
  ``value`` (id, carpeta, nombre) / (perfil, id, carpeta, nombre).
- WiFi: ``"wifi"`` con ``value=None``.
"""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog, QHBoxLayout, QLabel, QListWidget, QListWidgetItem,
    QMenu, QPushButton, QVBoxLayout,
)

from app.core.translator import QtString
from app.ui import theme
from app.ui import icons
from app.ui.device_picker import DevicePickerDialog
from app.ui.ftp_picker import FtpPickerDialog
from app.ui.wifi_panel import SenderEditDialog


class SourcePickerDialog(QDialog):
    """Lanzador compacto para añadir un origen a una sesión.

    ``folders``: rutas de carpetas (recientes / del proyecto).
    ``senders``: dicts con ``name`` y ``used`` (ya tiene sesión en el proyecto).
    ``devices_missing``: dicts con ``id`` y ``name`` de dispositivos MTP
    conocidos pero no conectados ahora.
    ``mtp_backend``/``ftp_backend``: se conservan por compatibilidad de API;
    el lanzador no los usa (los diálogos hijos crean los suyos).
    """

    def tr(self, text, *args, **kwargs):
        return QtString(super().tr(text, *args, **kwargs))

    def __init__(self, parent=None, folders=(), senders=(),
                 devices_missing=(), mtp_backend=None, ftp_backend=None,
                 on_delete=None):
        super().__init__(parent)
        self.kind = None
        self.value = None
        # ``on_delete(kind, value)`` devuelve True si el elemento guardado se
        # borró de la BD; si es así se quita de la lista (B-04).
        self.on_delete = on_delete
        self.setWindowTitle(self.tr("Añadir origen"))
        self.setMinimumWidth(560)
        self._build_ui(folders, senders, devices_missing,
                       mtp_backend, ftp_backend)

    def _build_ui(self, folders, senders, devices_missing,
                  mtp_backend, ftp_backend):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(10)

        hint = QLabel(
            self.tr("Añade un origen guardado o busca uno en un dispositivo:"))
        hint.setWordWrap(True)
        layout.addWidget(hint)

        self.saved_empty_label = QLabel(self.tr("Sin dispositivos guardados"))
        self.saved_empty_label.setStyleSheet(
            "color: {}; font-size: 11px;".format(theme.color("text_secondary")))
        self.saved_empty_label.setVisible(not folders and not senders)
        layout.addWidget(self.saved_empty_label)

        self.list_widget = QListWidget()
        self.list_widget.itemDoubleClicked.connect(self._accept_item)
        self.list_widget.setContextMenuPolicy(Qt.CustomContextMenu)
        self.list_widget.customContextMenuRequested.connect(self._show_item_menu)
        self.list_widget.itemSelectionChanged.connect(self._update_ok_state)
        layout.addWidget(self.list_widget, 1)

        self._add_section(self.tr("Carpetas guardadas"), folders, self._folder_item)
        self._add_section(self.tr("Remitentes WiFi"), senders, self._sender_item)
        self._add_section(self.tr("Desconectados"), devices_missing,
                          self._missing_item)

        search_row = QHBoxLayout()
        self.btn_browse = QPushButton(self.tr("Examinar…"))
        self.btn_browse.clicked.connect(self._browse)
        self.btn_mtp = QPushButton(self.tr("USB/MTP"))
        self.btn_mtp.clicked.connect(self._pick_device)
        self.btn_ftp = QPushButton(self.tr("FTP"))
        self.btn_ftp.clicked.connect(self._pick_ftp)
        self.btn_wifi_qr = QPushButton(self.tr("WiFi QR"))
        self.btn_wifi_qr.clicked.connect(self._choose_wifi)
        for btn in (self.btn_browse, self.btn_mtp, self.btn_wifi_qr,
                    self.btn_ftp):
            search_row.addWidget(btn)
        search_row.addStretch()
        layout.addLayout(search_row)

        buttons = QHBoxLayout()
        cancel_btn = QPushButton(self.tr("Cancelar"))
        cancel_btn.clicked.connect(self.reject)
        self.ok_btn = QPushButton(self.tr("Aceptar"))
        self.ok_btn.setObjectName("PrimaryAction")
        self.ok_btn.clicked.connect(self._accept_current)
        buttons.addStretch()
        buttons.addWidget(cancel_btn)
        buttons.addWidget(self.ok_btn)
        layout.addLayout(buttons)

        self._update_ok_state()

    # -- aceptar ----------------------------------------------------------

    def _update_ok_state(self, *_):
        item = self.list_widget.currentItem()
        role = item.data(Qt.UserRole) if item is not None else None
        if role is not None and role[0] == "device":
            # Ítem no-accionable (sección Desconectados): no habilita OK.
            self.ok_btn.setEnabled(False)
            return
        self.ok_btn.setEnabled(role is not None)

    def _accept_current(self):
        item = self.list_widget.currentItem()
        if item is None:
            return
        role = item.data(Qt.UserRole)
        if role is None or role[0] == "device":
            return
        self._set_from_item(item)
        self.accept()

    # -- flujos de búsqueda (ventanas propias) -----------------------------

    def _browse(self):
        self.kind = "browse"
        self.value = None
        self.accept()

    def _pick_device(self):
        dialog = DevicePickerDialog(self)
        if (dialog.exec() == QDialog.Accepted
                and dialog.device_id and dialog.device_folder):
            self.kind = "device"
            self.value = (dialog.device_id, dialog.device_folder,
                          dialog.device_name)
            self.accept()

    def _pick_ftp(self):
        # Pedir nombre antes de configurar el servidor, como en WiFi
        name_dlg = SenderEditDialog(
            self,
            title=self.tr("Añadir servidor FTP"),
            name_label=self.tr("Nombre del servidor (aparecerá en la tabla de orígenes):"),
            name_hint=self.tr("Ej.: Servidor rodaje A"),
        )
        if name_dlg.exec() != QDialog.Accepted:
            return
        name = name_dlg.name_edit.text().strip()
        if not name:
            return
        dialog = FtpPickerDialog(self)
        if (dialog.exec() == QDialog.Accepted
                and dialog.device_id and dialog.device_folder):
            self.kind = "ftp_new"
            self.value = (dialog.profile_id, dialog.device_id,
                          dialog.device_folder, name)
            self.accept()

    def _choose_wifi(self):
        self.kind = "wifi"
        self.value = None
        self.accept()

    # -- lista de guardados ------------------------------------------------

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

    def _missing_item(self, dev):
        name = dev.get("name") or dev.get("id") or ""
        item = QListWidgetItem(name + " — " + self.tr("desconectado"))
        item.setFlags(Qt.ItemIsEnabled)
        item.setIcon(icons.icon("phone", size=16))
        item.setData(Qt.UserRole, ("device", dev["id"]))
        item.setToolTip(
            self.tr("Dispositivo conocido pero no conectado ahora"))
        return item

    # -- gestión de guardados (B-04) --------------------------------------

    def _show_item_menu(self, pos):
        item = self.list_widget.itemAt(pos)
        if item is None or self.on_delete is None:
            return
        role = item.data(Qt.UserRole)
        if role is None:
            return
        menu = QMenu(self)
        action = menu.addAction(self.tr("Eliminar guardado…"))
        if menu.exec(self.list_widget.viewport().mapToGlobal(pos)) is action:
            self._delete_selected(item, role)

    def _delete_selected(self, item, role):
        kind, value = role
        if self.on_delete(kind, value):
            row = self.list_widget.row(item)
            self.list_widget.takeItem(row)
            self._update_ok_state()

    def _accept_item(self, item):
        role = item.data(Qt.UserRole)
        if role is None or role[0] == "device":
            # Ítem no-accionable (sección Desconectados): el doble clic no
            # debe aceptar el diálogo ni mutar kind/value.
            return
        self._set_from_item(item)
        if self.kind is not None:
            self.accept()

    def _set_from_item(self, item):
        role = item.data(Qt.UserRole)
        if role is None or role[0] == "device":
            return
        self.kind, self.value = role
