"""Dialogo de configuracion general del proyecto."""

from PySide6.QtCore import QSettings
from PySide6.QtWidgets import (QCheckBox, QComboBox, QDateEdit, QDialog,
                               QFormLayout, QGridLayout, QGroupBox, QHBoxLayout,
                               QLabel, QPushButton, QSpinBox, QVBoxLayout)

from app.core.db import db
from app.core.translator import QtString


class ProjectSettingsDialog(QDialog):

    def tr(self, text, *args, **kwargs):
        return QtString(super().tr(text, *args, **kwargs))

    def __init__(self, window, open_overrides_cb=None):
        super().__init__(window)
        self.window = window
        self._open_overrides_cb = open_overrides_cb
        self.setWindowTitle(self.tr("Configuración"))
        self.setMinimumWidth(620)
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(12)
        main_layout.setContentsMargins(16, 12, 16, 12)

        # --- Grupo Configuración general ---
        gen_group = QGroupBox(self.tr("Configuración general"))
        gen_grid = QGridLayout(gen_group)
        gen_grid.setHorizontalSpacing(16)
        gen_grid.setVerticalSpacing(8)

        folder_input = QComboBox()
        folder_input.setEditable(True)
        folder_input.addItems(db.get_footage_folders())
        folder_input.setCurrentText(self.window.project_folder_name or "Footage")
        gen_grid.addWidget(QLabel(self.tr("Carpeta footage:")), 0, 0)
        gen_grid.addWidget(folder_input, 0, 1)

        org_combo = QComboBox()
        org_combo.addItems([self.tr("Cámara / Fecha"), self.tr("Fecha / Cámara"), self.tr("Solo cámara"), self.tr("Sin subcarpetas")])
        org_combo.setCurrentIndex(self.window.project_organization_type)
        gen_grid.addWidget(QLabel(self.tr("Organización:")), 0, 2)
        gen_grid.addWidget(org_combo, 0, 3)

        date_mode_combo = QComboBox()
        date_mode_combo.addItems([self.tr("Automática"), self.tr("Manual")])
        date_mode_combo.setCurrentIndex(0 if self.window.project_date_mode == "auto" else 1)
        gen_grid.addWidget(QLabel(self.tr("Modo de fechas:")), 1, 0)
        gen_grid.addWidget(date_mode_combo, 1, 1)
        btn_manage_overrides = QPushButton(self.tr("Gestionar overrides…"))
        gen_grid.addWidget(btn_manage_overrides, 2, 2, 1, 2)
        btn_manage_overrides.clicked.connect(self._open_overrides)

        date_input = QDateEdit()
        date_input.setCalendarPopup(True)
        date_input.setDate(self.window.project_date)
        date_input.setDisplayFormat("yyyy-MM-dd")
        date_label = QLabel(self.tr("Fecha:"))
        gen_grid.addWidget(date_label, 2, 0)
        gen_grid.addWidget(date_input, 2, 1)

        # Lógica de habilitación
        def _update_ui_state():
            uses_date = org_combo.currentIndex() in [0,1]
            date_mode_combo.setEnabled(uses_date)
            is_manual = date_mode_combo.currentIndex() == 1
            btn_manage_overrides.setEnabled(uses_date)
            date_input.setEnabled(uses_date and is_manual)
            date_label.setEnabled(uses_date and is_manual)

        date_mode_combo.currentIndexChanged.connect(lambda _: _update_ui_state())
        org_combo.currentIndexChanged.connect(lambda _: _update_ui_state())
        _update_ui_state()

        main_layout.addWidget(gen_group)

        # --- Grupo Detección de cámara ---
        cam_group = QGroupBox(self.tr("Detección de cámara"))
        cam_layout = QFormLayout(cam_group)

        cam_mode_combo = QComboBox()
        cam_mode_combo.addItems([self.tr("Manual"), self.tr("Automático")])
        cam_mode_combo.setCurrentIndex(0 if self.window.project_camera_detection_mode != "auto" else 1)
        cam_layout.addRow(self.tr("Modo:"), cam_mode_combo)

        cam_timeout_spin = QSpinBox()
        cam_timeout_spin.setRange(1, 30)
        cam_timeout_spin.setSuffix(" s")
        cam_timeout_spin.setValue(self.window.project_camera_detection_timeout)
        cam_timeout_spin.setEnabled(cam_mode_combo.currentIndex() == 1)
        cam_layout.addRow(self.tr("Timeout:"), cam_timeout_spin)
        cam_mode_combo.currentIndexChanged.connect(lambda i: cam_timeout_spin.setEnabled(i == 1))

        main_layout.addWidget(cam_group)

        # --- Grupo Proxies ---
        prox_group = QGroupBox(self.tr("Proxies y rendimiento"))
        prox_layout = QFormLayout(prox_group)

        chk_gen_proxies = QCheckBox(self.tr("Generar proxies tras la ingesta"))
        chk_gen_proxies.setChecked(self.window.project_generate_proxies)
        prox_layout.addRow(chk_gen_proxies)

        proxy_res_combo = QComboBox()
        proxy_res_combo.addItems(["720p", "1080p"])
        proxy_res_combo.setCurrentText(self.window.project_proxy_resolution)
        proxy_res_combo.setEnabled(self.window.project_generate_proxies)
        prox_layout.addRow(self.tr("Resolución proxy:"), proxy_res_combo)
        chk_gen_proxies.toggled.connect(proxy_res_combo.setEnabled)

        main_layout.addWidget(prox_group)

        # --- Botones ---
        btn_save = QPushButton(self.tr("Guardar"))
        btn_save.setObjectName("PrimaryAction")

        def _save():
            self.window.project_folder_name = folder_input.currentText().strip() or "Footage"
            self.window.project_organization_type = org_combo.currentIndex()
            self.window.project_date_mode = "manual" if date_mode_combo.currentIndex() == 1 else "auto"
            self.window.project_manual_date = date_input.date().toString("yyyy-MM-dd") if date_mode_combo.currentIndex() == 1 else None
            self.window.project_generate_proxies = chk_gen_proxies.isChecked()
            self.window.project_proxy_resolution = proxy_res_combo.currentText()
            self.window.project_camera_detection_mode = "auto" if cam_mode_combo.currentIndex() == 1 else "manual"
            self.window.project_camera_detection_timeout = cam_timeout_spin.value()
            if self.window.current_project_id is not None:
                db.add_footage_folder(self.window.project_folder_name)
                conn = db.get_connection()
                cursor = conn.cursor()
                cursor.execute(
                    'UPDATE projects SET folder_name=?, organization_type=?, date_mode=?, manual_date=?, '
                    'generate_proxies=?, proxy_resolution=?, '
                    'camera_detection_mode=?, camera_detection_timeout=?, camera_date_overrides=? WHERE id=?',
                    (self.window.project_folder_name, self.window.project_organization_type,
                     self.window.project_date_mode, self.window.project_manual_date,
                     int(self.window.project_generate_proxies), self.window.project_proxy_resolution,
                     self.window.project_camera_detection_mode, self.window.project_camera_detection_timeout,
                     self.window.project_camera_date_overrides,
                     self.window.current_project_id)
                )
                conn.commit()
                conn.close()
            self.window._refresh_source_list()
            self.accept()

        btn_save.clicked.connect(_save)

        btn_defaults = QPushButton(self.tr("Establecer como predeterminado"))
        def _set_defaults():
            settings = QSettings("Audiovisual Production", "CosechaMedia")
            settings.setValue("default_folder_name", folder_input.currentText().strip() or "Footage")
            settings.setValue("default_organization_type", org_combo.currentIndex())
            settings.setValue("default_date_mode", "manual" if date_mode_combo.currentIndex() == 1 else "auto")
            settings.setValue("default_manual_date", date_input.date().toString("yyyy-MM-dd") if date_mode_combo.currentIndex() == 1 else "")
            settings.setValue("default_camera_detection_mode", "auto" if cam_mode_combo.currentIndex() == 1 else "manual")
            settings.setValue("camera_detection_timeout", cam_timeout_spin.value())
            self.window.ingest_status_label.setText(self.tr("Valores guardados como predeterminados."))
        btn_defaults.clicked.connect(_set_defaults)

        btn_cancel = QPushButton(self.tr("Cancelar"))
        btn_cancel.clicked.connect(self.reject)

        btn_row = QHBoxLayout()
        btn_row.addWidget(btn_defaults)
        btn_row.addStretch()
        btn_row.addWidget(btn_cancel)
        btn_row.addWidget(btn_save)
        main_layout.addLayout(btn_row)

    def _open_overrides(self):
        if self._open_overrides_cb is not None:
            self._open_overrides_cb()
