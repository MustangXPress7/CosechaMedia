"""Panel de estado/monitor para servidores FTP."""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog, QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget
)

from app.core import ftp as ftpmod
from app.core.db import db
from app.core.translator import QtString
from app.ui import theme
from app.ui.ftp_picker import FtpPickerDialog


class FtpStatusDialog(QDialog):
    def tr(self, text, *args, **kwargs):
        return QtString(super().tr(text, *args, **kwargs))

    def __init__(self, parent=None, backend=None, device_id=None):
        super().__init__(parent)
        self._backend = backend or ftpmod.FtpBackend()
        self._device_id = device_id
        self.setWindowTitle(self.tr("Estado FTP"))
        self.resize(520, 240)
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(10)

        hint = QLabel(self.tr("Selecciona un perfil para comprobar su estado en red."))
        hint.setWordWrap(True)
        hint.setStyleSheet("color: {}; font-size: 12px;".format(theme.color("text_secondary")))
        layout.addWidget(hint)

        row = QHBoxLayout()
        self.profile_label = QLabel(self.tr("Perfil:"))
        row.addWidget(self.profile_label)
        if self._device_id:
            pid = ftpmod.profile_id_from_device_key(self._device_id)
            if pid:
                row_data = db.get_ftp_profile(pid)
                name = (row_data.get("name") or row_data.get("host") or self._device_id)
            else:
                name = self._device_id
        else:
            name = self.tr("Sin perfil seleccionado")
        self.info = QLabel(name)
        row.addWidget(self.info, 1)
        layout.addLayout(row)

        btn_row = QHBoxLayout()
        self.ping_btn = QPushButton(self.tr("Probar conexión / Ping"))
        self.ping_btn.setObjectName("PrimaryAction")
        self.ping_btn.clicked.connect(self._check_reachable)
        btn_row.addWidget(self.ping_btn)
        self.config_btn = QPushButton(self.tr("Configurar perfil"))
        self.config_btn.clicked.connect(self._open_config)
        btn_row.addWidget(self.config_btn)
        btn_row.addStretch()
        layout.addLayout(btn_row)

        self.status = QLabel(self.tr("Estado: —"))
        self.status.setStyleSheet("color: {}; font-size: 12px;".format(theme.color("text_secondary")))
        layout.addWidget(self.status)

        self.last_action = QLabel("")
        self.last_action.setStyleSheet("color: {}; font-size: 11px;".format(theme.color("text_secondary")))
        layout.addWidget(self.last_action)

        close_btn = QPushButton(self.tr("Cerrar"))
        close_btn.clicked.connect(self.accept)
        layout.addWidget(close_btn, alignment=Qt.AlignRight)

    def _check_reachable(self):
        if not self._device_id:
            self.status.setText(self.tr("Estado: sin perfiles"))
            self.last_action.setText(self.tr("Última acción: no hay perfiles"))
            return
        device_id = self._device_id
        try:
            reachable = self._backend.is_reachable(device_id, timeout=4.0)
            if reachable:
                self.status.setText(self.tr("Estado: conectado"))
                from datetime import datetime
                self.last_action.setText(self.tr("Última acción: ping OK %1").arg(datetime.now().strftime("%H:%M:%S")))
            else:
                self.status.setText(self.tr("Estado: no responde"))
                from datetime import datetime
                self.last_action.setText(self.tr("Última acción: ping falló %1").arg(datetime.now().strftime("%H:%M:%S")))
        except Exception as e:
            self.status.setText(self.tr("Estado: error"))
            self.last_action.setText(self.tr("Última acción: %1").arg(str(e)))

    def _open_config(self):
        if not self._device_id:
            return
        pid = ftpmod.profile_id_from_device_key(self._device_id)
        dlg = FtpPickerDialog(self)
        # Pre-seleccionar perfil si es posible
        if pid is not None:
            # Intenta preseleccionar estableciendo la propiedad profile_id
            if hasattr(dlg, "set_profile_id"):
                dlg.set_profile_id(pid)
            elif hasattr(dlg, "profile_id"):
                dlg.profile_id = pid
        dlg.exec()


