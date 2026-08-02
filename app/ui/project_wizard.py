import os
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                              QPushButton, QLineEdit, QMessageBox,
                              QGroupBox, QRadioButton, QButtonGroup, QComboBox, QCheckBox)
from PySide6.QtCore import Qt
from app.core.db import db
from app.ui import theme
 
class ProjectWizard(QWidget):
    def __init__(self, on_finished_callback, on_cancel_callback=None):
        super().__init__()
        self.on_finished_callback = on_finished_callback
        self.on_cancel_callback = on_cancel_callback
        self.setWindowTitle("Nuevo Proyecto")
        self.setMinimumWidth(600)
        self.setMinimumHeight(520)
        
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(32, 24, 32, 24)
        self.layout.setSpacing(12)
        
        self._build_ui()
        
    def _build_ui(self):
        title = QLabel("Nuevo Proyecto")
        title.setStyleSheet(f"font-size: 22px; font-weight: bold; color: {theme.color('accent')}; margin-bottom: 4px;")
        self.layout.addWidget(title)

        name_group = QGroupBox("Nombre del Proyecto")
        name_layout = QVBoxLayout(name_group)
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("Ej: Rodaje_Cine_01")
        self.name_input.setMinimumHeight(36)
        name_layout.addWidget(self.name_input)
        self.layout.addWidget(name_group)
        
        desc_group = QGroupBox("Descripción (Opcional)")
        desc_layout = QVBoxLayout(desc_group)
        self.desc_input = QLineEdit()
        self.desc_input.setPlaceholderText("Breve descripción del proyecto...")
        self.desc_input.setMinimumHeight(36)
        desc_layout.addWidget(self.desc_input)
        self.layout.addWidget(desc_group)

        dest_group = QGroupBox("Ruta de Destino")
        dest_layout = QVBoxLayout(dest_group)
        self.dest_input = QLineEdit()
        self.dest_input.setPlaceholderText("Ej: H:/Produccion/Proyectos")
        self.dest_input.setMinimumHeight(36)
        dest_layout.addWidget(self.dest_input)
        self.layout.addWidget(dest_group)
        
        config_row = QHBoxLayout()

        duration_group = QGroupBox("Duración")
        duration_layout = QVBoxLayout(duration_group)
        
        self.duration_group = QButtonGroup()
        
        self.radio_one_day = QRadioButton("Un solo día")
        self.radio_one_day.setChecked(True)
        self.radio_one_day.setToolTip("Todos los archivos pertenecen al mismo día")
        
        self.radio_multiple_days = QRadioButton("Múltiples días")
        self.radio_multiple_days.setToolTip("Los archivos se organizarán por fecha de rodaje")
        
        self.radio_no_date = QRadioButton("Sin fecha")
        self.radio_no_date.setToolTip("No se usará fecha para organizar los archivos")
        
        self.duration_group.addButton(self.radio_one_day, 1)
        self.duration_group.addButton(self.radio_multiple_days, 2)
        self.duration_group.addButton(self.radio_no_date, 3)
        
        duration_layout.addWidget(self.radio_one_day)
        duration_layout.addWidget(self.radio_multiple_days)
        duration_layout.addWidget(self.radio_no_date)
        config_row.addWidget(duration_group, 1)
        
        org_group = QGroupBox("Organización")
        org_layout = QVBoxLayout(org_group)
        
        self.org_combo = QComboBox()
        self.org_combo.addItems([
            "Cámara primero (Cámara/Fecha)",
            "Fecha primero (Fecha/Cámara)",
            "Solo por cámara",
            "Sin subcarpetas"
        ])
        self.org_combo.setMinimumHeight(36)
        org_layout.addWidget(self.org_combo)
        
        self.chk_use_metadata_date = QCheckBox("Usar fecha de metadatos")
        self.chk_use_metadata_date.setChecked(True)
        self.chk_use_metadata_date.setToolTip("Usar las fechas de los archivos en lugar de la fecha manual")
        org_layout.addWidget(self.chk_use_metadata_date)
        
        config_row.addWidget(org_group, 1)
        
        self.layout.addLayout(config_row)
        
        btn_row = QHBoxLayout()
        btn_row.addStretch()

        btn_cancel = QPushButton("Cancelar")
        btn_cancel.setMinimumHeight(44)
        btn_cancel.clicked.connect(self._cancel)
        btn_row.addWidget(btn_cancel)
        
        btn_finish = QPushButton("Crear Proyecto")
        btn_finish.setObjectName("PrimaryAction")
        btn_finish.setMinimumHeight(44)
        btn_finish.clicked.connect(self.finish_wizard)
        btn_row.addWidget(btn_finish)
        
        self.layout.addLayout(btn_row)
        
    def _cancel(self):
        if self.on_cancel_callback:
            self.on_cancel_callback()
        
    def finish_wizard(self):
        name = self.name_input.text().strip()
        dest = self.dest_input.text().strip()
        
        if not name or not dest:
            QMessageBox.warning(self, "Error", "Debes poner un nombre y una ruta de destino.")
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
                    use_metadata_date = ?
                WHERE id = ?
            ''', (
                self.desc_input.text().strip(),
                duration_type,
                org_type,
                self.chk_use_metadata_date.isChecked(),
                project_id
            ))
            
            conn.commit()
            
            self.name_input.clear()
            self.desc_input.clear()
            self.dest_input.clear()
            
            self.on_finished_callback(project_id)
            
        except Exception as e:
            conn.rollback()
            QMessageBox.critical(self, "Error", f"No se pudo guardar el proyecto: {e}")
        finally:
            conn.close()
