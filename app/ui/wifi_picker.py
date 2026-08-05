"""Selector de método de importación por WiFi.

Al aceptar expone ``method``: ``"pairdrop"`` (recepción por QR/navegador) o
``"ftp"`` (servidor FTP clásico en el dispositivo).
"""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QDialog, QHBoxLayout, QLabel, QPushButton, QVBoxLayout

from app.core.translator import QtString


class WifiMethodDialog(QDialog):
    """Diálogo para elegir entre recepción por QR o FTP clásico."""

    def tr(self, text, *args, **kwargs):
        return QtString(super().tr(text, *args, **kwargs))

    def __init__(self, parent=None):
        super().__init__(parent)
        self.method = None
        self.setWindowTitle(self.tr("Recibir por WiFi"))
        self.setMinimumWidth(480)
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(10)

        hint = QLabel(self.tr("¿Cómo quieres recibir los archivos de los móviles?"))
        hint.setWordWrap(True)
        layout.addWidget(hint)

        self.btn_pairdrop = self._make_card(
            self.tr("PairDrop"),
            self.tr("Compatible con Android/iOS. Sin instalar nada en el móvil: "
                    "escanea el código QR y envía los archivos."),
        )
        self.btn_pairdrop.setObjectName("PrimaryAction")
        self.btn_pairdrop.clicked.connect(lambda: self._choose("pairdrop"))
        layout.addWidget(self.btn_pairdrop)

        self.btn_ftp = self._make_card(
            self.tr("FTP Clásico"),
            self.tr("Avanzado. El dispositivo ejecuta un servidor FTP "
                    "(requiere una app y configuración en el móvil)."),
        )
        self.btn_ftp.clicked.connect(lambda: self._choose("ftp"))
        layout.addWidget(self.btn_ftp)

        buttons = QHBoxLayout()
        buttons.addStretch()
        cancel_btn = QPushButton(self.tr("Cancelar"))
        cancel_btn.clicked.connect(self.reject)
        buttons.addWidget(cancel_btn)
        layout.addLayout(buttons)

    def _make_card(self, title, desc):
        btn = QPushButton()
        btn.setCursor(Qt.PointingHandCursor)
        btn.setText(f"{title}\n{desc}")
        btn.setStyleSheet(
            "QPushButton { text-align: left; padding: 12px 14px; }")
        btn.setMinimumHeight(68)
        return btn

    def _choose(self, method):
        self.method = method
        self.accept()
