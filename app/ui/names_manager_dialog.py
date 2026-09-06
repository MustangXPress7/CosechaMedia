"""Dialogo de gestion de nombres (carpetas de footage / contenedores)."""

from PySide6.QtWidgets import (QDialog, QHBoxLayout, QInputDialog, QLabel,
                               QLineEdit, QListWidget, QMessageBox, QPushButton,
                               QVBoxLayout)

from app.core.translator import QtString
from app.ui import theme


class NamesManagerDialog(QDialog):

    def tr(self, text, *args, **kwargs):
        return QtString(super().tr(text, *args, **kwargs))

    def __init__(self, parent=None, title="", getter=None, add_cb=None,
                 rename_cb=None, delete_cb=None, duplicate_cb=None):
        super().__init__(parent)
        self._getter = getter
        self._add_cb = add_cb
        self._rename_cb = rename_cb
        self._delete_cb = delete_cb
        self._duplicate_cb = duplicate_cb
        self.setWindowTitle(title)
        self.setMinimumWidth(380)
        self.setMinimumHeight(360)
        layout = QVBoxLayout(self)
        layout.setSpacing(8)
        layout.setContentsMargins(16, 12, 16, 12)

        hint = QLabel(
            self.tr("Puedes añadir, duplicar, renombrar o eliminar nombres.")
            if duplicate_cb is not None
            else self.tr("Puedes añadir, renombrar o eliminar nombres.")
        )
        hint.setStyleSheet(f"color: {theme.color('text_secondary')}; font-size: 10px;")
        layout.addWidget(hint)

        search = QLineEdit()
        search.setPlaceholderText(self.tr("Buscar..."))
        layout.addWidget(search)

        self.listw = QListWidget()
        layout.addWidget(self.listw, 1)

        self._names_manager = {"filter": "", "items": []}

        search.textChanged.connect(self._on_search)
        self._refresh()

        btn_row = QHBoxLayout()
        btn_add = QPushButton(self.tr("Añadir..."))
        btn_ren = QPushButton(self.tr("Renombrar..."))
        btn_del = QPushButton(self.tr("Eliminar"))
        for b in (btn_add, btn_ren, btn_del):
            btn_row.addWidget(b)
        btn_dup = None
        if duplicate_cb is not None:
            btn_dup = QPushButton(self.tr("Duplicar"))
            btn_row.addWidget(btn_dup)
        btn_row.addStretch()
        btn_close = QPushButton(self.tr("Cerrar"))
        btn_row.addWidget(btn_close)
        layout.addLayout(btn_row)

        btn_add.clicked.connect(self._add)
        if btn_dup is not None:
            btn_dup.clicked.connect(self._dup)
        btn_ren.clicked.connect(self._ren)
        btn_del.clicked.connect(self._del)
        btn_close.clicked.connect(self.accept)

    def _refresh(self):
        self.listw.clear()
        items = self._getter()
        self._names_manager["items"] = list(items)
        filter_text = self._names_manager["filter"].lower()
        for name in items:
            if not filter_text or filter_text in name.lower():
                self.listw.addItem(name)
        if self.listw.count():
            self.listw.setCurrentRow(0)

    def _on_search(self, text):
        self._names_manager["filter"] = text
        self._refresh()

    def _selected(self):
        item = self.listw.currentItem()
        return item.text() if item else None

    def _add(self):
        name, ok = QInputDialog.getText(self, self.tr("Añadir"), self.tr("Nuevo nombre:"))
        name = name.strip() if ok else ""
        if name:
            self._add_cb(name)
            self._refresh()

    def _dup(self):
        name = self._selected()
        if not name:
            return
        self._duplicate_cb(name)
        self._refresh()

    def _ren(self):
        name = self._selected()
        if not name:
            return
        new_name, ok = QInputDialog.getText(self, self.tr("Renombrar"), self.tr("Nuevo nombre:"), text=name)
        new_name = new_name.strip() if ok else ""
        if new_name and new_name != name:
            self._rename_cb(name, new_name)
            self._refresh()

    def _del(self):
        name = self._selected()
        if not name:
            return
        reply = QMessageBox.question(
            self, self.tr("Eliminar"),
            self.tr("¿Eliminar '%1'?").arg(name),
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            self._delete_cb(name)
            self._refresh()