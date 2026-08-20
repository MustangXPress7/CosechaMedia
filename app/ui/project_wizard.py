import os
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                              QPushButton, QLineEdit, QMessageBox,
                              QGroupBox, QRadioButton, QButtonGroup, QComboBox, QCheckBox,
                              QFileDialog, QSpinBox)
from PySide6.QtCore import Qt, QSettings
from app.core.db import db
from app.ui import theme
from app.core.translator import QtString
 
class ProjectWizard(QDialog):
    def tr(self, text, *args, **kwargs):
        return QtString(super().tr(text, *args, **kwargs))

    def __init__(self, on_finished_callback, on_cancel_callback=None):
        super().__init__()
        self.on_finished_callback = on_finished_callback
        self.on_cancel_callback = on_cancel_callback
        self.setWindowTitle(self.tr("Nuevo Proyecto"))
        self.setMinimumWidth(660)
        self.setMinimumHeight(620)
        
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(32, 24, 32, 24)
        self.layout.setSpacing(12)
        
        self._build_ui()
        
    def _build_ui(self):
        title = QLabel(self.tr("Nuevo Proyecto"))
        title.setStyleSheet(f"font-size: 22px; font-weight: bold; color: {theme.color('accent')}; margin-bottom: 4px;")
        self.layout.addWidget(title)

        name_group = QGroupBox(self.tr("Nombre del Proyecto"))
        name_layout = QVBoxLayout(name_group)
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText(self.tr("Ej: Rodaje_Cine_01"))
        self.name_input.setMinimumHeight(36)
        name_layout.addWidget(self.name_input)
        self.layout.addWidget(name_group)
        
        desc_group = QGroupBox(self.tr("Descripción (Opcional)"))
        desc_layout = QVBoxLayout(desc_group)
        self.desc_input = QLineEdit()
        self.desc_input.setPlaceholderText(self.tr("Breve descripción del proyecto..."))
        self.desc_input.setMinimumHeight(36)
        desc_layout.addWidget(self.desc_input)
        self.layout.addWidget(desc_group)

        dest_group = QGroupBox(self.tr("Ruta Maestra"))
        dest_layout = QHBoxLayout(dest_group)
        dest_layout.setSpacing(6)
        self.dest_input = QLineEdit()
        self.dest_input.setPlaceholderText(self.tr("Ej: H:/Produccion/Proyectos"))
        self.dest_input.setMinimumHeight(36)
        dest_layout.addWidget(self.dest_input)
        btn_browse = QPushButton(self.tr("Examinar..."))
        btn_browse.setMinimumHeight(36)
        btn_browse.setMinimumWidth(90)
        btn_browse.clicked.connect(self._browse_dest)
        dest_layout.addWidget(btn_browse)
        self.layout.addWidget(dest_group)
        
        config_row = QHBoxLayout()

        duration_group = QGroupBox(self.tr("Duración"))
        duration_layout = QVBoxLayout(duration_group)
        
        self.duration_group = QButtonGroup()
        
        self.radio_one_day = QRadioButton(self.tr("Un solo día"))
        self.radio_one_day.setChecked(True)
        self.radio_one_day.setToolTip(self.tr("Todos los archivos pertenecen al mismo día"))
        
        self.radio_multiple_days = QRadioButton(self.tr("Múltiples días"))
        self.radio_multiple_days.setToolTip(self.tr("Los archivos se organizarán por fecha de rodaje"))
        
        self.radio_no_date = QRadioButton(self.tr("Sin fecha"))
        self.radio_no_date.setToolTip(self.tr("No se usará fecha para organizar los archivos"))
        
        self.duration_group.addButton(self.radio_one_day, 1)
        self.duration_group.addButton(self.radio_multiple_days, 2)
        self.duration_group.addButton(self.radio_no_date, 3)
        
        duration_layout.addWidget(self.radio_one_day)
        duration_layout.addWidget(self.radio_multiple_days)
        duration_layout.addWidget(self.radio_no_date)
        config_row.addWidget(duration_group, 1)
        
        org_group = QGroupBox(self.tr("Organización"))
        org_layout = QVBoxLayout(org_group)
        
        self.org_combo = QComboBox()
        self.org_combo.addItems([
            self.tr("Cámara primero (Cámara/Fecha)"),
            self.tr("Fecha primero (Fecha/Cámara)"),
            self.tr("Solo por cámara"),
            self.tr("Sin subcarpetas")
        ])
        self.org_combo.setMinimumHeight(36)
        org_layout.addWidget(self.org_combo)
        
        self.chk_use_metadata_date = QCheckBox(self.tr("Usar fecha de metadatos"))
        self.chk_use_metadata_date.setChecked(True)
        self.chk_use_metadata_date.setToolTip(self.tr("Usar las fechas de los archivos en lugar de la fecha manual"))
        org_layout.addWidget(self.chk_use_metadata_date)
        
        config_row.addWidget(org_group, 1)
        
        self.layout.addLayout(config_row)

        config_row2 = QHBoxLayout()

        detect_group = QGroupBox(self.tr("Detección de cámara"))
        detect_layout = QVBoxLayout(detect_group)
        self.detect_combo = QComboBox()
        self.detect_combo.addItems([
            self.tr("Automática (ffprobe)"),
            self.tr("Manual (preguntar)")
        ])
        self.detect_combo.setMinimumHeight(36)
        detect_layout.addWidget(self.detect_combo)
        self.spin_detect_timeout = QSpinBox()
        self.spin_detect_timeout.setRange(1, 30)
        self.spin_detect_timeout.setValue(5)
        self.spin_detect_timeout.setSuffix(" s")
        self.spin_detect_timeout.setToolTip(self.tr("Tiempo máximo de espera para auto-detección"))
        timeout_row = QHBoxLayout()
        timeout_row.addWidget(QLabel(self.tr("Timeout:")))
        timeout_row.addWidget(self.spin_detect_timeout)
        timeout_row.addStretch()
        detect_layout.addLayout(timeout_row)
        config_row2.addWidget(detect_group, 1)

        proxy_group = QGroupBox(self.tr("Proxies y rendimiento"))
        proxy_layout = QVBoxLayout(proxy_group)
        self.chk_generate_proxies = QCheckBox(self.tr("Generar proxies"))
        self.chk_generate_proxies.setToolTip(self.tr("Crear copias de baja resolución para edición ligera"))
        proxy_layout.addWidget(self.chk_generate_proxies)
        self.proxy_combo = QComboBox()
        self.proxy_combo.addItems(["720p", "1080p"])
        self.proxy_combo.setMinimumHeight(36)
        self.proxy_combo.setEnabled(False)
        self.chk_generate_proxies.toggled.connect(self.proxy_combo.setEnabled)
        proxy_layout.addWidget(self.proxy_combo)
        self.chk_delicate_mode = QCheckBox(self.tr("Modo delicado (1 hilo)"))
        self.chk_delicate_mode.setToolTip(self.tr("Reduce carga del sistema — recomendado en máquinas lentas"))
        proxy_layout.addWidget(self.chk_delicate_mode)
        config_row2.addWidget(proxy_group, 1)

        self.layout.addLayout(config_row2)
        
        btn_row = QHBoxLayout()
        btn_row.addStretch()

        btn_cancel = QPushButton(self.tr("Cancelar"))
        btn_cancel.setMinimumHeight(44)
        btn_cancel.clicked.connect(self._cancel)
        btn_row.addWidget(btn_cancel)
        
        btn_finish = QPushButton(self.tr("Crear Proyecto"))
        btn_finish.setObjectName("PrimaryAction")
        btn_finish.setMinimumHeight(44)
        btn_finish.clicked.connect(self.finish_wizard)
        btn_row.addWidget(btn_finish)
        
        self.layout.addLayout(btn_row)

        settings = QSettings("Audiovisual Production", "CosechaMedia")
        saved_dur = settings.value("default_duration_type", 1, type=int)
        dur_map = {1: self.radio_one_day, 2: self.radio_multiple_days, 3: self.radio_no_date}
        btn = dur_map.get(saved_dur)
        if btn:
            btn.setChecked(True)
        saved_org = settings.value("default_organization_type", 0, type=int)
        if 0 <= saved_org < self.org_combo.count():
            self.org_combo.setCurrentIndex(saved_org)
        self.chk_use_metadata_date.setChecked(
            settings.value("default_use_metadata_date", True, type=bool)
        )
        saved_detect = settings.value("camera_detection_mode", "auto")
        self.detect_combo.setCurrentIndex(0 if saved_detect == "auto" else 1)
        self.spin_detect_timeout.setValue(
            settings.value("camera_detection_timeout", 5, type=int))
        self.chk_generate_proxies.setChecked(
            settings.value("default_generate_proxies", False, type=bool))
        saved_proxy_res = settings.value("default_proxy_resolution", "720p")
        idx = self.proxy_combo.findText(saved_proxy_res)
        if idx >= 0:
            self.proxy_combo.setCurrentIndex(idx)
        self.chk_delicate_mode.setChecked(
            settings.value("default_delicate_mode", False, type=bool))
        
    def _browse_dest(self):
        folder = QFileDialog.getExistingDirectory(
            self, self.tr("Seleccionar ruta maestra"),
            self.dest_input.text() or ""
        )
        if folder:
            self.dest_input.setText(folder)
        
    def _cancel(self):
        if self.on_cancel_callback:
            self.on_cancel_callback()
        
    def finish_wizard(self):
        name = self.name_input.text().strip()
        dest = self.dest_input.text().strip()
        
        if not name or not dest:
            QMessageBox.warning(self, self.tr("Error"), self.tr("Debes poner un nombre y una ruta de destino."))
            return
        
        conn = db.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO projects (name, root_path) 
                VALUES (?, ?)
            ''', (name, os.path.abspath(dest)))
            project_id = cursor.lastrowid
            
            duration_type = self.duration_group.checkedId()
            org_type = self.org_combo.currentIndex()
            
            cursor.execute('''
                UPDATE projects SET 
                    description = ?,
                    duration_type = ?,
                    organization_type = ?,
                    use_metadata_date = ?,
                    camera_detection_mode = ?,
                    camera_detection_timeout = ?,
                    generate_proxies = ?,
                    proxy_resolution = ?,
                    delicate_mode = ?
                WHERE id = ?
            ''', (
                self.desc_input.text().strip(),
                duration_type,
                org_type,
                self.chk_use_metadata_date.isChecked(),
                "auto" if self.detect_combo.currentIndex() == 0 else "manual",
                self.spin_detect_timeout.value(),
                self.chk_generate_proxies.isChecked(),
                self.proxy_combo.currentText(),
                self.chk_delicate_mode.isChecked(),
                project_id
            ))
            
            conn.commit()
            
            self.name_input.clear()
            self.desc_input.clear()
            self.dest_input.clear()
            
            self.on_finished_callback(project_id)
            
        except Exception as e:
            conn.rollback()
            QMessageBox.critical(self, self.tr("Error"), self.tr("No se pudo guardar el proyecto: %1").arg(str(e)))
        finally:
            conn.close()
