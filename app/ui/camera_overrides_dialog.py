"""Dialogo de fechas por camara (overrides)."""

import json

from PySide6.QtCore import QDate, Qt
from PySide6.QtWidgets import (QComboBox, QDateEdit, QDialog, QHBoxLayout,
                               QHeaderView, QLabel, QPushButton, QTableWidget,
                               QTableWidgetItem, QVBoxLayout)

from app.core.db import db
from app.core.translator import QtString


class CameraOverridesDialog(QDialog):

    def tr(self, text, *args, **kwargs):
        return QtString(super().tr(text, *args, **kwargs))

    def __init__(self, window):
        super().__init__(window)
        self.window = window
        self.setWindowTitle(self.tr("Fechas por cámara"))
        self.setMinimumWidth(640)
        layout = QVBoxLayout(self)
        self.table = QTableWidget(0, 3)
        self.table.setHorizontalHeaderLabels([self.tr("Cámara"), self.tr("Modo"), self.tr("Fecha")])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Interactive)
        self.table.setColumnWidth(2, 180)
        # Cámaras de sesiones activas
        active_cams = set()
        if self.window.current_project_id is not None:
            conn = db.get_connection()
            cur = conn.cursor()
            cur.execute("SELECT DISTINCT nombre_dispositivo FROM sessions WHERE project_id=? AND status IN ('active','pending') AND nombre_dispositivo IS NOT NULL", (self.window.current_project_id,))
            active_cams = {r[0] for r in cur.fetchall()}
            conn.close()
        overrides = json.loads(self.window.project_camera_date_overrides or "{}")
        # Mostrar cámaras activas con modo manual por defecto
        for cam in sorted(active_cams):
            r = self.table.rowCount()
            self.table.insertRow(r)
            item_cam = QTableWidgetItem(cam)
            item_cam.setFlags(item_cam.flags() & ~Qt.ItemIsEditable)
            self.table.setItem(r, 0, item_cam)

            mode_combo = QComboBox()
            mode_combo.addItems([self.tr("Manual"), self.tr("Automático")])
            # Cargar modo/fecha existente
            existing = overrides.get(cam, "")
            if isinstance(existing, dict):
                mode_val = existing.get("mode", "manual")
                date_str = existing.get("date", "")
                mode_idx = 0 if str(mode_val).lower() == "manual" else 1
            elif isinstance(existing, str) and existing:
                mode_idx = 0
                date_str = existing
            else:
                mode_idx = 0
                date_str = QDate.currentDate().toString("yyyy-MM-dd")
            mode_combo.setCurrentIndex(mode_idx)

            date_edit = QDateEdit()
            date_edit.setCalendarPopup(True)
            date_edit.setDisplayFormat("yyyy-MM-dd")
            qdate = QDate.fromString(date_str, "yyyy-MM-dd")
            if not qdate.isValid():
                qdate = QDate.currentDate()
            date_edit.setDate(qdate)
            date_edit.setEnabled(mode_idx == 0)

            def on_mode_changed(idx, de=date_edit):
                de.setEnabled(idx == 0)

            mode_combo.currentIndexChanged.connect(on_mode_changed)
            self.table.setCellWidget(r, 1, mode_combo)
            self.table.setCellWidget(r, 2, date_edit)

        layout.addWidget(self.table)
        btn_row = QHBoxLayout()
        btn_save = QPushButton(self.tr("Guardar"))
        btn_cancel = QPushButton(self.tr("Cancelar"))
        btn_save.setObjectName("PrimaryAction")
        btn_row.addStretch()
        btn_row.addWidget(btn_cancel)
        btn_row.addWidget(btn_save)
        layout.addLayout(btn_row)

        btn_save.clicked.connect(self._save)
        btn_cancel.clicked.connect(self.reject)

    def _save(self):
        # Mantener overrides de cámaras no visibles y actualizar las activas
        try:
            existing_overrides = json.loads(self.window.project_camera_date_overrides or "{}")
            if not isinstance(existing_overrides, dict):
                existing_overrides = {}
        except Exception:
            existing_overrides = {}
        merged = dict(existing_overrides)
        for r in range(self.table.rowCount()):
            item_cam = self.table.item(r, 0)
            if not item_cam:
                continue
            cam = item_cam.text().strip()
            mode_combo = self.table.cellWidget(r, 1)
            date_edit = self.table.cellWidget(r, 2)
            mode = "manual" if mode_combo.currentIndex() == 0 else "auto"
            date_str = date_edit.date().toString("yyyy-MM-dd")
            if cam:
                merged[cam] = {"mode": mode, "date": date_str}
        self.window.project_camera_date_overrides = json.dumps(merged)
        self.accept()