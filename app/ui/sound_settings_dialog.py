"""Diálogo de configuración de sonido para CosechaMedia."""
from PySide6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QCheckBox, QSlider, QPushButton, QGroupBox
from PySide6.QtCore import Qt, QSettings

_ORG = "Audiovisual Production"
_APP = "CosechaMedia"

class SoundSettingsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(self.tr("Opciones de sonido"))
        self.setMinimumWidth(380)
        
        settings = QSettings(_ORG, _APP)
        self._sounds_enabled = settings.value("soundsEnabled", True, type=bool)
        self._sound_volume = settings.value("soundVolume", 70, type=int)
        
        main_layout = QVBoxLayout(self)
        
        group = QGroupBox(self.tr("Alertas de ingesta"))
        g_layout = QVBoxLayout(group)
        
        self.chk_enabled = QCheckBox(self.tr("Reproducir sonidos de alerta"))
        self.chk_enabled.setChecked(self._sounds_enabled)
        g_layout.addWidget(self.chk_enabled)
        
        vol_layout = QHBoxLayout()
        vol_layout.addWidget(QLabel(self.tr("Volumen")))
        self.slider = QSlider(Qt.Horizontal)
        self.slider.setRange(0, 100)
        self.slider.setValue(self._sound_volume)
        vol_layout.addWidget(self.slider)
        self.lbl_value = QLabel(f"{self._sound_volume}%")
        vol_layout.addWidget(self.lbl_value)
        g_layout.addLayout(vol_layout)
        
        self.slider.valueChanged.connect(self._on_volume_changed)
        
        main_layout.addWidget(group)
        
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        btn_ok = QPushButton(self.tr("Aceptar"))
        btn_cancel = QPushButton(self.tr("Cancelar"))
        btn_ok.clicked.connect(self.accept)
        btn_cancel.clicked.connect(self.reject)
        btn_layout.addWidget(btn_cancel)
        btn_layout.addWidget(btn_ok)
        main_layout.addLayout(btn_layout)
    
    def _on_volume_changed(self, value):
        self.lbl_value.setText(f"{value}%")
    
    def accept(self):
        settings = QSettings(_ORG, _APP)
        settings.setValue("soundsEnabled", self.chk_enabled.isChecked())
        settings.setValue("soundVolume", self.slider.value())
        super().accept()
