"""Ventana flotante (no modal) de recepción por WiFi (PairDrop).

Muestra el código QR del dispositivo seleccionado mientras el servidor HTTP de
``app.core.shoot_inbox`` está activo. Es una ventana independiente no modal,
así que puedes dejarla abierta mientras operas el resto de la aplicación.

Los dispositivos (móviles que escanean el QR) se gestionan desde la ventana
principal, donde cada dispositivo se registra como un origen de ingesta normal.
Este panel solo se encarga de:

- Mostrar el QR/URL del dispositivo indicado por la ventana principal
  (``select_sender``); sin desplegable: cada origen WiFi abre su propio QR.
- Activar/desactivar el modo carpeta.
- Reenviar cada archivo recibido a la ventana principal (``received``) para la
  auto-ingesta.
- Detener/reanudar la recepción (``stop_requested`` / ``resume_requested``).

Ciclo de vida:
- Cerrar la ventana solo la oculta; el servidor sigue recibiendo archivos.
- ``received(alias, path, size)`` reenvía cada archivo desde el hilo del
  servidor al hilo de UI (cola segura).
"""

import os

from PySide6.QtCore import QObject, Qt, Signal
from PySide6.QtGui import QColor, QPainter, QPixmap
from PySide6.QtWidgets import (
    QCheckBox, QDialog, QDialogButtonBox, QFormLayout,
    QHBoxLayout, QLabel, QLineEdit, QPushButton, QVBoxLayout, QWidget,
)

from app.core import shoot_inbox as inboxmod
from app.core.db import db
from app.core.translator import QtString
from app.ui import theme


class _Bridge(QObject):
    """Puente hilo-del-servidor -> hilo de UI (señales en cola)."""

    received = Signal(str, str, int)  # alias, ruta, tamaño


class SenderEditDialog(QDialog):
    """Formulario para añadir un dispositivo WiFi (solo nombre)."""

    def __init__(self, parent=None, title="", name="",
                 name_label="Nombre del dispositivo:", name_hint=""):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setMinimumWidth(440)
        self.name_edit = QLineEdit(name)
        self.name_edit.setPlaceholderText(name_hint)
        form = QFormLayout()
        form.addRow(name_label, self.name_edit)
        buttons = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        lay = QVBoxLayout(self)
        lay.addLayout(form)
        lay.addWidget(buttons)


class ShootInboxPanel(QWidget):
    """Ventana flotante no modal con el QR de recepción por WiFi.

    Muestra el QR de un dispositivo concreto (fijado con ``select_sender``).
    Diseño compacto: el QR arriba del todo y el resto de texto y opciones
    debajo.
    """

    received = Signal(str, str, int)
    stop_requested = Signal()
    resume_requested = Signal()

    def tr(self, text, *args, **kwargs):
        return QtString(super().tr(text, *args, **kwargs))

    def __init__(self, parent=None):
        super().__init__(parent, Qt.Window)
        self.setWindowTitle(self.tr("Recibir por WiFi (PairDrop)"))
        icon = parent.windowIcon() if parent is not None else None
        if icon is not None:
            self.setWindowIcon(icon)
        self.resize(420, 460)
        self._server = None
        self._bridge = _Bridge()
        self._bridge.received.connect(self._on_file_received)
        self._sender_name = None
        self._build_ui()
        self.refresh()

    # -- UI --------------------------------------------------------------

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(8)

        self.qr_label = QLabel()
        self.qr_label.setFixedSize(260, 260)
        self.qr_label.setAlignment(Qt.AlignCenter)
        self.qr_label.setStyleSheet(
            "border: 1px solid #333; border-radius: 6px; background: #ffffff;")
        layout.addWidget(self.qr_label, 0, Qt.AlignHCenter)

        self.url_label = QLabel("")
        self.url_label.setWordWrap(True)
        self.url_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self.url_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.url_label)

        self.status_label = QLabel("")
        self.status_label.setWordWrap(True)
        self.status_label.setStyleSheet("font-weight: 600;")
        layout.addWidget(self.status_label)

        hint = QLabel(
            self.tr("Escanea este código QR desde el móvil para enviar "
                    "archivos sin instalar nada. El móvil y el ordenador "
                    "deben estar en la misma red WiFi."))
        hint.setWordWrap(True)
        hint.setStyleSheet(
            "color: {}; font-size: 12px;".format(theme.color("text_secondary")))
        layout.addWidget(hint)

        self.folder_mode_cb = QCheckBox(
            self.tr("Enviar una carpeta entera (modo carpeta)"))
        self.folder_mode_cb.toggled.connect(self._on_folder_mode_toggled)
        layout.addWidget(self.folder_mode_cb)

        layout.addStretch(1)

        bottom = QHBoxLayout()
        bottom.addStretch()
        self.stop_btn = QPushButton(self.tr("Detener"))
        self.stop_btn.setObjectName("DangerAction")
        self.stop_btn.clicked.connect(self._on_stop_clicked)
        bottom.addWidget(self.stop_btn)
        self.close_btn = QPushButton(self.tr("Cerrar"))
        self.close_btn.clicked.connect(self.hide)
        bottom.addWidget(self.close_btn)
        layout.addLayout(bottom)

    # -- servidor --------------------------------------------------------

    def attach_server(self, server):
        self._server = server
        server.on_file_received = self._bridge.received.emit
        server.folder_mode = self.folder_mode_cb.isChecked()
        self._refresh_server_status()
        self._render_current()

    def set_server_status(self, text):
        self.status_label.setText(text)

    def _refresh_server_status(self):
        if self._server is None or not self._server.running:
            self.status_label.setText(self.tr("El servidor no está activo."))
            self.stop_btn.setText(self.tr("Reanudar"))
            self.stop_btn.setObjectName("PrimaryAction")
        else:
            self.stop_btn.setText(self.tr("Detener"))
            self.stop_btn.setObjectName("DangerAction")
            self.status_label.setText(
                self.tr("Servidor activo. Comparte esta dirección con los móviles: "
                        "%1").arg(self._server.base_url()))
        self.stop_btn.style().unpolish(self.stop_btn)
        self.stop_btn.style().polish(self.stop_btn)

    def _on_folder_mode_toggled(self, checked):
        if self._server is not None:
            self._server.folder_mode = checked

    def closeEvent(self, event):
        # Cerrar solo oculta; el servidor sigue (lo gestiona la ventana principal).
        self.hide()
        event.ignore()

    def _on_stop_clicked(self):
        if self._server is None or not self._server.running:
            self.resume_requested.emit()
        else:
            self.stop_requested.emit()

    # -- dispositivo ------------------------------------------------------

    def select_sender(self, name):
        """Fija el dispositivo a mostrar (su QR) y lo pinta ya mismo."""
        self._sender_name = name
        self._render_current()

    def _current_sender(self):
        if self._sender_name is not None:
            return self._sender_name
        senders = db.list_inbox_senders()
        return senders[0]["name"] if senders else None

    def _render_current(self):
        name = self._current_sender()
        if name is None or self._server is None:
            self._clear_qr()
            return
        url = self._server.url_for_sender(name)
        self.url_label.setText(url)
        self.qr_label.setPixmap(self._render_qr(url))

    def _clear_qr(self):
        self.qr_label.clear()
        self.url_label.setText("")

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
        scale = max(1, 232 // n)
        pix = QPixmap(n * scale, n * scale)
        pix.fill(QColor("#ffffff"))
        painter = QPainter(pix)
        painter.setBrush(QColor("#ffffff"))
        painter.setPen(Qt.NoPen)
        for r in range(n):
            for c in range(n):
                if matrix[r][c]:
                    painter.fillRect(c * scale, r * scale, scale, scale,
                                     QColor("#000000"))
        painter.end()
        return pix

    # -- recepción -------------------------------------------------------

    def _on_file_received(self, alias, path, size):
        size_txt = self._format_size(size)
        self.status_label.setText(
            self.tr("Recibido de %1: %2 (%3).")
            .arg(alias).arg(os.path.basename(path)).arg(size_txt))
        self.received.emit(alias, path, size)

    def _format_size(self, size):
        size = float(size)
        for unit in ("B", "KB", "MB", "GB", "TB"):
            if size < 1024 or unit == "TB":
                return f"{size:.0f} {unit}" if unit == "B" else f"{size:.1f} {unit}"
            size /= 1024
        return f"{size:.0f} B"

    def refresh(self):
        self._refresh_server_status()
        self._render_current()
