"""Dialogo de destinos de volcado del proyecto."""

import os

from PySide6.QtWidgets import (QDialog, QFileDialog, QHBoxLayout, QInputDialog,
                               QLabel, QListWidget, QPushButton, QVBoxLayout)

from app.core.db import db
from app.core.translator import QtString
from app.ui import theme


class DumpLocationsDialog(QDialog):

    def tr(self, text, *args, **kwargs):
        return QtString(super().tr(text, *args, **kwargs))

    def __init__(self, window):
        super().__init__(window)
        self.window = window
        self.setWindowTitle(self.tr("Destinos de volcado"))
        self.setMinimumSize(480, 340)
        layout = QVBoxLayout(self)
        layout.setSpacing(8)
        layout.setContentsMargins(16, 12, 16, 12)

        hint = QLabel(
            self.tr("Los archivos se repartirán entre estos destinos por orden. Cuando uno esté lleno se pasará al siguiente. Deja vacío para usar la ruta maestra del proyecto.")
        )
        hint.setWordWrap(True)
        hint.setStyleSheet(f"color: {theme.color('text_secondary')}; font-size: 10px;")
        layout.addWidget(hint)

        self.listw = QListWidget()
        layout.addWidget(self.listw, 1)

        btn_row = QHBoxLayout()
        btn_add = QPushButton(self.tr("Añadir..."))
        btn_del = QPushButton(self.tr("Eliminar"))
        btn_up = QPushButton(self.tr("Subir"))
        btn_down = QPushButton(self.tr("Bajar"))
        for b in (btn_add, btn_del, btn_up, btn_down):
            btn_row.addWidget(b)
        btn_row.addStretch()
        layout.addLayout(btn_row)

        btn_add.clicked.connect(self._add)
        btn_del.clicked.connect(self._del)
        btn_up.clicked.connect(lambda: self._move(-1))
        btn_down.clicked.connect(lambda: self._move(1))

        btn_close = QPushButton(self.tr("Cerrar"))
        btn_close.setObjectName("PrimaryAction")
        bottom = QHBoxLayout()
        bottom.addStretch()
        bottom.addWidget(btn_close)
        btn_close.clicked.connect(self.accept)
        layout.addLayout(bottom)

        self._refresh()

    def _refresh(self):
        self.listw.clear()
        for loc in db.dump_locations(self.window.current_project_id):
            include = []
            if loc["include_date"]:
                include.append(self.tr("fecha"))
            if loc["include_camera"]:
                include.append(self.tr("cámara"))
            suffix = f"  [{', '.join(include)}]" if include else ""
            self.listw.addItem(f"{loc['path']}{suffix}")

    def _add(self):
        path = QFileDialog.getExistingDirectory(
            self, self.tr("Seleccionar destino de volcado"), self.window.dest_root or os.path.expanduser("~")
        )
        if not path:
            return
        label, ok = QInputDialog.getText(self, self.tr("Destino de volcado"), self.tr("Etiqueta (opcional):"))
        label = label.strip() if ok else None
        db.add_dump_location(self.window.current_project_id, path, label or None)
        self._refresh()

    def _del(self):
        row = self.listw.currentRow()
        if row < 0:
            return
        locs = db.dump_locations(self.window.current_project_id)
        db.delete_dump_location(locs[row]["id"])
        self._refresh()

    def _move(self, delta):
        row = self.listw.currentRow()
        if row < 0:
            return
        locs = db.dump_locations(self.window.current_project_id)
        new_row = row + delta
        if new_row < 0 or new_row >= len(locs):
            return
        locs[row], locs[new_row] = locs[new_row], locs[row]
        db.reorder_dump_locations(
            self.window.current_project_id, [l["id"] for l in locs]
        )
        self._refresh()
        self.listw.setCurrentRow(new_row)