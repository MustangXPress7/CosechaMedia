"""Panel de recepción por WiFi (buzón QR embebido en CosechaMedia).

Arranca el servidor HTTP (``app.core.shoot_inbox``), muestra el QR por
remitente y registra los archivos que llegan. La carpeta ``inbox/`` es la que
el usuario después ingiere con el flujo normal de CosechaMedia.
"""

import os

from PySide6.QtCore import QObject, Qt, Signal
from PySide6.QtGui import QColor, QDesktopServices, QPainter, QPixmap
from PySide6.QtCore import QUrl
from PySide6.QtWidgets import (
    QCheckBox, QDialog, QDialogButtonBox, QFormLayout, QHBoxLayout, QLabel,
    QLineEdit, QListWidget, QPushButton, QTreeWidget, QTreeWidgetItem,
    QVBoxLayout, QMessageBox,
)

from app.core import shoot_inbox as inboxmod
from app.core.db import db
from app.core.translator import QtString
from app.ui import theme


class _Bridge(QObject):
    """Puente hilo-del-servidor -> hilo de UI (señales en cola)."""

    received = Signal(str, str, int)  # alias, ruta, tamaño


class _SenderEditDialog(QDialog):
    """Formulario para añadir/editar remitente (nombre + ubicación)."""

    def __init__(self, parent=None, title="", name="", location="",
                 name_label="", location_label="", location_hint=""):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setMinimumWidth(400)
        self.name_edit = QLineEdit(name)
        self.location_edit = QLineEdit(location)
        self.location_edit.setPlaceholderText(location_hint)
        form = QFormLayout()
        form.addRow(name_label, self.name_edit)
        form.addRow(location_label, self.location_edit)
        buttons = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        lay = QVBoxLayout(self)
        lay.addLayout(form)
        lay.addWidget(buttons)


class ShootInboxDialog(QDialog):
    """Diálogo modal que sirve el buzón de recepción por WiFi."""

    def tr(self, text, *args, **kwargs):
        return QtString(super().tr(text, *args, **kwargs))

    def __init__(self, parent=None, backend=None):
        super().__init__(parent)
        self._server = backend or inboxmod.ShootInboxServer()
        self._bridge = _Bridge()
        self._bridge.received.connect(self._on_file_received)

        self.setWindowTitle(self.tr("Recibir por WiFi (PairDrop)"))
        self.resize(560, 640)
        self._build_ui()
        self._load_senders()
        self._start_server()

    # -- UI --------------------------------------------------------------

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(8)

        hint = QLabel(
            self.tr("Cada persona escanea su código QR desde el móvil y envía "
                    "los archivos sin instalar nada. El móvil y el ordenador "
                    "deben estar conectados a la misma red WiFi. Al llegar, "
                    "CosechaMedia los recibe en su carpeta inbox."))
        hint.setWordWrap(True)
        hint.setStyleSheet(
            "color: {}; font-size: 12px;".format(theme.color("text_secondary")))
        layout.addWidget(hint)

        self.status_label = QLabel("")
        self.status_label.setWordWrap(True)
        self.status_label.setStyleSheet("font-weight: 600;")
        layout.addWidget(self.status_label)

        self.folder_mode_cb = QCheckBox(
            self.tr("Enviar una carpeta entera (modo carpeta)"))
        self.folder_mode_cb.toggled.connect(self._on_folder_mode_toggled)
        layout.addWidget(self.folder_mode_cb)

        row = QHBoxLayout()
        row.addWidget(QLabel(self.tr("Remitentes:")))
        self.sender_tree = QTreeWidget()
        self.sender_tree.setHeaderLabels(
            [self.tr("Remitente"), self.tr("Ubicación")])
        self.sender_tree.setRootIsDecorated(False)
        self.sender_tree.setColumnWidth(0, 190)
        self.sender_tree.currentItemChanged.connect(self._on_sender_changed)
        row.addWidget(self.sender_tree, 1)
        layout.addLayout(row)

        btns = QHBoxLayout()
        self.add_btn = QPushButton(self.tr("Añadir"))
        self.add_btn.clicked.connect(self._add_sender)
        self.edit_btn = QPushButton(self.tr("Editar"))
        self.edit_btn.clicked.connect(self._edit_sender)
        self.del_btn = QPushButton(self.tr("Eliminar"))
        self.del_btn.clicked.connect(self._delete_sender)
        btns.addWidget(self.add_btn)
        btns.addWidget(self.edit_btn)
        btns.addWidget(self.del_btn)
        btns.addStretch()
        layout.addLayout(btns)

        qr_row = QHBoxLayout()
        self.qr_label = QLabel()
        self.qr_label.setFixedSize(200, 200)
        self.qr_label.setAlignment(Qt.AlignCenter)
        self.qr_label.setStyleSheet(
            "border: 1px solid #333; border-radius: 6px; background: #ffffff;")
        qr_row.addWidget(self.qr_label)
        right = QVBoxLayout()
        self.url_label = QLabel("")
        self.url_label.setWordWrap(True)
        self.url_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        right.addWidget(self.url_label)
        self.copy_btn = QPushButton(self.tr("Copiar enlace"))
        self.copy_btn.clicked.connect(self._copy_url)
        right.addWidget(self.copy_btn)
        self.open_btn = QPushButton(self.tr("Abrir carpeta inbox"))
        self.open_btn.clicked.connect(self._open_inbox)
        right.addWidget(self.open_btn)
        right.addStretch()
        qr_row.addLayout(right, 1)
        layout.addLayout(qr_row)

        layout.addWidget(QLabel(self.tr("Recibidos:")))
        self.received_list = QListWidget()
        layout.addWidget(self.received_list, 1)

        buttons = QHBoxLayout()
        buttons.addStretch()
        close_btn = QPushButton(self.tr("Cerrar"))
        close_btn.clicked.connect(self.accept)
        buttons.addWidget(close_btn)
        layout.addLayout(buttons)

    # -- servidor --------------------------------------------------------

    def _start_server(self):
        self._server.on_file_received = self._bridge.received.emit
        try:
            self._server.start()
        except OSError as e:
            self.status_label.setText(
                self.tr("No se pudo iniciar el servidor: %1").arg(str(e)))
            return
        self.status_label.setText(
            self.tr("Servidor activo. Comparte esta dirección con los móviles: "
                    "%1").arg(self._server.base_url()))

    def _stop_server(self):
        try:
            self._server.stop()
        except Exception:
            pass

    def closeEvent(self, event):
        self._stop_server()
        super().closeEvent(event)

    # -- remitentes ------------------------------------------------------

    def _on_folder_mode_toggled(self, checked):
        self._server.folder_mode = checked

    def _load_senders(self):
        self._senders = db.list_inbox_senders()
        self.sender_tree.blockSignals(True)
        self.sender_tree.clear()
        for s in self._senders:
            loc = s["location"] or "—"
            item = QTreeWidgetItem([s["name"], loc])
            item.setData(0, Qt.UserRole, s["id"])
            self.sender_tree.addTopLevelItem(item)
        self.sender_tree.blockSignals(False)
        if self._senders:
            self.sender_tree.setCurrentItem(self.sender_tree.topLevelItem(0))
        else:
            self._clear_qr()

    def _on_sender_changed(self, current, _previous):
        if current is None:
            self._clear_qr()
            return
        sid = current.data(0, Qt.UserRole)
        sender = next((s for s in self._senders if s["id"] == sid), None)
        if sender is None:
            self._clear_qr()
            return
        url = self._server.url_for_sender(sender["name"])
        self.url_label.setText(url)
        self._show_qr(url)

    def _clear_qr(self):
        self.qr_label.clear()
        self.url_label.setText("")

    def _show_qr(self, url):
        pix = self._render_qr(url)
        self.qr_label.setPixmap(pix)

    def _render_qr(self, url):
        try:
            import qrcode
            qr = qrcode.QRCode(box_size=4, border=2)
            qr.add_data(url)
            qr.make(fit=True)
            matrix = qr.get_matrix()
        except Exception:
            return QPixmap()
        n = len(matrix)
        scale = max(1, 192 // n)
        pix = QPixmap(n * scale, n * scale)
        pix.fill(QColor("#ffffff"))
        painter = QPainter(pix)
        painter.setBrush(QColor("#ffffff"))
        painter.setPen(Qt.NoPen)
        for r in range(n):
            for c in range(n):
                if matrix[r][c]:
                    painter.fillRect(c * scale, r * scale, scale, scale, QColor("#000000"))
        painter.end()
        return pix

    def _add_sender(self):
        dlg = self._make_edit_dialog(title=self.tr("Añadir remitente"))
        if dlg.exec() != QDialog.Accepted:
            return
        name = dlg.name_edit.text().strip()
        if not name:
            return
        db.add_inbox_sender(name, dlg.location_edit.text().strip())
        self._load_senders()

    def _make_edit_dialog(self, title, name="", location=""):
        return _SenderEditDialog(
            self,
            title=title, name=name, location=location,
            name_label=self.tr(
                "Nombre de la persona (aparecerá en el código QR):"),
            location_label=self.tr(
                "Ubicación (carpeta donde se guardarán sus archivos):"),
            location_hint=self.tr(
                "En blanco: se usará el nombre del remitente"),
        )

    def _edit_sender(self):
        item = self.sender_tree.currentItem()
        if item is None:
            return
        sid = item.data(0, Qt.UserRole)
        sender = next((s for s in self._senders if s["id"] == sid), None)
        if sender is None:
            return
        dlg = self._make_edit_dialog(
            title=self.tr("Editar remitente"),
            name=sender["name"], location=sender["location"])
        if dlg.exec() != QDialog.Accepted:
            return
        name = dlg.name_edit.text().strip()
        if not name:
            return
        db.update_inbox_sender(
            sid, name, dlg.location_edit.text().strip())
        self._load_senders()

    def _delete_sender(self):
        item = self.sender_tree.currentItem()
        if item is None:
            return
        sid = item.data(0, Qt.UserRole)
        sender = next((s for s in self._senders if s["id"] == sid), None)
        if sender is None:
            return
        answer = QMessageBox.question(
            self, self.tr("Eliminar remitente"),
            self.tr("¿Eliminar a %1?").arg(sender["name"]))
        if answer != QMessageBox.Yes:
            return
        db.delete_inbox_sender(sid)
        self._load_senders()

    # -- acciones --------------------------------------------------------

    def _copy_url(self):
        url = self.url_label.text()
        if not url:
            return
        from PySide6.QtWidgets import QApplication
        QApplication.clipboard().setText(url)
        self.status_label.setText(self.tr("Enlace copiado al portapapeles."))

    def _open_inbox(self):
        path = self._server.root
        os.makedirs(path, exist_ok=True)
        QDesktopServices.openUrl(QUrl.fromLocalFile(path))

    def _on_file_received(self, alias, path, size):
        size_txt = self._format_size(size)
        rel = os.path.relpath(path, self._server.root)
        self.received_list.insertItem(0, f"{alias} → {rel} ({size_txt})")
        self.status_label.setText(
            self.tr("Recibido de %1: %2 (%3). Ya puedes ingerir la carpeta inbox.")
            .arg(alias).arg(os.path.basename(path)).arg(size_txt))

    def _format_size(self, size):
        size = float(size)
        for unit in ("B", "KB", "MB", "GB", "TB"):
            if size < 1024 or unit == "TB":
                return f"{size:.0f} {unit}" if unit == "B" else f"{size:.1f} {unit}"
            size /= 1024
        return f"{size:.0f} B"
