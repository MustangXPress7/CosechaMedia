import os
import json
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel,
                              QPushButton, QLineEdit, QMessageBox, QTableWidget,
                              QTableWidgetItem, QHeaderView, QFileDialog,
                              QMenu, QAbstractItemView, QWidget)
from PySide6.QtCore import Qt, QSettings
from PySide6.QtGui import QAction
from app.core.db import db
from app.ui import theme


class DeviceRegistryDialog(QDialog):
    """Diálogo para gestionar dispositivos conocidos (Herramientas → Dispositivos conocidos)."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(self.tr("Dispositivos conocidos"))
        self.setMinimumSize(900, 500)
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(16, 16, 16, 16)
        self.layout.setSpacing(8)

        self._build_ui()
        self._populate_table()

    def _build_ui(self):
        title = QLabel(self.tr("Dispositivos conocidos"))
        title.setStyleSheet(f"font-size: 18px; font-weight: bold; color: {theme.color('accent')}; margin-bottom: 8px;")
        self.layout.addWidget(title)

        # Toolbar
        toolbar = QHBoxLayout()
        toolbar.setSpacing(8)

        btn_import = QPushButton(self.tr("Importar JSON"))
        btn_import.setMinimumHeight(36)
        btn_import.clicked.connect(self._import_json)
        toolbar.addWidget(btn_import)

        btn_export = QPushButton(self.tr("Exportar JSON"))
        btn_export.setMinimumHeight(36)
        btn_export.clicked.connect(self._export_json)
        toolbar.addWidget(btn_export)

        toolbar.addStretch()

        btn_clear = QPushButton(self.tr("Limpiar todo"))
        btn_clear.setObjectName("DestructiveButton")
        btn_clear.setMinimumHeight(36)
        btn_clear.setToolTip(self.tr("Elimina TODOS los dispositivos conocidos (equivalente al kill-switch D-11)"))
        btn_clear.clicked.connect(self._clear_all)
        toolbar.addWidget(btn_clear)

        btn_close = QPushButton(self.tr("Cerrar"))
        btn_close.setMinimumHeight(36)
        btn_close.clicked.connect(self.accept)
        toolbar.addWidget(btn_close)

        self.layout.addLayout(toolbar)

        # Tabla
        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels([
            self.tr("Tipo"), self.tr("ID Dispositivo"), self.tr("Nombre"),
            self.tr("Serial"), self.tr("Última Cámara"), self.tr("Última vez visto")
        ])
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self._show_context_menu)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        self.table.verticalHeader().setVisible(False)
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(5, QHeaderView.ResizeToContents)
        self.layout.addWidget(self.table)

    def _populate_table(self):
        devices = db.list_known_devices()
        self.table.setRowCount(len(devices))
        for row, d in enumerate(devices):
            # Tipo
            type_item = QTableWidgetItem(d["device_type"].upper())
            type_item.setData(Qt.UserRole, d["device_id"])
            self.table.setItem(row, 0, type_item)

            # ID Dispositivo
            self.table.setItem(row, 1, QTableWidgetItem(d["device_id"]))

            # Nombre (editable)
            name = d["name"] or ""
            name_item = QTableWidgetItem(name)
            name_item.setFlags(name_item.flags() | Qt.ItemIsEditable)
            self.table.setItem(row, 2, name_item)

            # Serial
            self.table.setItem(row, 3, QTableWidgetItem(d["serial"] or ""))

            # Última Cámara
            self.table.setItem(row, 4, QTableWidgetItem(d["last_camera"] or ""))

            # Última vez visto
            self.table.setItem(row, 5, QTableWidgetItem(d["last_seen"] or ""))

        # Conectar señal de edición
        self.table.itemChanged.connect(self._on_item_changed)

    def _on_item_changed(self, item):
        """Se llama al editar una celda (solo columna Nombre)."""
        if item.column() != 2:
            return
        device_id = self.table.item(item.row(), 1).text()
        new_name = item.text().strip() or None
        db.upsert_known_device(device_id, device_type="", name=new_name)

    def _show_context_menu(self, pos):
        item = self.table.itemAt(pos)
        if not item:
            return
        row = item.row()
        device_id = self.table.item(row, 1).text()
        device_type = self.table.item(row, 0).text().lower()

        menu = QMenu(self)

        act_edit_name = QAction(self.tr("Editar nombre"), self)
        act_edit_name.triggered.connect(lambda: self._edit_name(row, device_id))
        menu.addAction(act_edit_name)

        act_copy_id = QAction(self.tr("Copiar ID"), self)
        act_copy_id.triggered.connect(lambda: self._copy_to_clipboard(device_id))
        menu.addAction(act_copy_id)

        menu.addSeparator()

        act_delete = QAction(self.tr("Eliminar"), self)
        act_delete.triggered.connect(lambda: self._delete_device(row, device_id))
        menu.addAction(act_delete)

        menu.exec(self.table.viewport().mapToGlobal(pos))

    def _edit_name(self, row, device_id):
        current = self.table.item(row, 2).text()
        new_name, ok = QLineEdit.getText(
            self, self.tr("Editar nombre"),
            self.tr("Nuevo nombre para %1:").arg(device_id),
            text=current
        )
        if ok:
            new_name = new_name.strip() or None
            db.upsert_known_device(device_id, device_type="", name=new_name)
            self.table.item(row, 2).setText(new_name or "")

    def _copy_to_clipboard(self, text):
        from PySide6.QtWidgets import QApplication
        QApplication.clipboard().setText(text)

    def _delete_device(self, row, device_id):
        reply = QMessageBox.question(
            self, self.tr("Eliminar dispositivo"),
            self.tr("¿Eliminar el dispositivo %1 de la lista de conocidos?").arg(device_id),
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            db.delete_known_device(device_id)
            self.table.removeRow(row)

    def _clear_all(self):
        reply = QMessageBox.question(
            self, self.tr("Limpiar todo"),
            self.tr("¿Eliminar TODOS los dispositivos conocidos?\nEsta acción no se puede deshacer."),
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            # Usar método de limpieza masiva
            conn = db.get_connection()
            try:
                cursor = conn.cursor()
                cursor.execute('DELETE FROM known_devices')
                conn.commit()
            finally:
                conn.close()
            self.table.setRowCount(0)

    def _import_json(self):
        path, _ = QFileDialog.getOpenFileName(
            self, self.tr("Importar dispositivos conocidos"),
            "", "JSON (*.json)"
        )
        if not path:
            return
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            if not isinstance(data, list):
                raise ValueError("El JSON debe ser una lista de dispositivos")
            
            count = 0
            for d in data:
                if not all(k in d for k in ("device_id", "device_type")):
                    continue
                db.upsert_known_device(
                    d["device_id"], d["device_type"],
                    d.get("name"), d.get("serial"),
                    d.get("last_camera"), d.get("metadata")
                )
                count += 1
            self._populate_table()
            QMessageBox.information(self, self.tr("Importación completada"),
                                    self.tr("Se importaron %1 dispositivos.").arg(count))
        except Exception as e:
            QMessageBox.critical(self, self.tr("Error"), self.tr("No se pudo importar: %1").arg(str(e)))

    def _export_json(self):
        path, _ = QFileDialog.getSaveFileName(
            self, self.tr("Exportar dispositivos conocidos"),
            "known_devices.json", "JSON (*.json)"
        )
        if not path:
            return
        try:
            devices = db.list_known_devices()
            # Serializar solo campos necesarios
            export_data = []
            for d in devices:
                export_data.append({
                    "device_id": d["device_id"],
                    "device_type": d["device_type"],
                    "name": d["name"],
                    "serial": d["serial"],
                    "last_camera": d["last_camera"],
                    "last_seen": d["last_seen"],
                    "metadata": d["metadata"],
                })
            with open(path, "w", encoding="utf-8") as f:
                json.dump(export_data, f, ensure_ascii=False, indent=2)
            QMessageBox.information(self, self.tr("Exportación completada"),
                                    self.tr("Se exportaron %1 dispositivos.").arg(len(export_data)))
        except Exception as e:
            QMessageBox.critical(self, self.tr("Error"), self.tr("No se pudo exportar: %1").arg(str(e)))

    def tr(self, text, *args, **kwargs):
        from app.core.translator import QtString
        return QtString(super().tr(text, *args, **kwargs))