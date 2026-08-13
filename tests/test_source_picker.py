"""Pruebas del selector unificado de orígenes (SourcePickerDialog)."""
import os
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication

from app.ui.source_picker import SourcePickerDialog


class TestSourcePicker(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def _dialog(self):
        return SourcePickerDialog(
            None,
            folders=["E:\\DCIM", "F:\\ROOT"],
            senders=[{"name": "Alice", "used": True},
                     {"name": "Bob", "used": False}],
            ftp_profiles=[{"id": 7, "name": "Serv", "host": "192.168.1.5"}],
        )

    def _find_item(self, dlg, role_value):
        for i in range(dlg.list_widget.count()):
            item = dlg.list_widget.item(i)
            if item.data(Qt.UserRole) == role_value:
                return item
        return None

    def test_sender_selection(self):
        dlg = self._dialog()
        item = self._find_item(dlg, ("sender", "Bob"))
        self.assertIsNotNone(item)
        dlg._accept_item(item)
        self.assertEqual((dlg.kind, dlg.value), ("sender", "Bob"))

    def test_folder_selection(self):
        dlg = self._dialog()
        item = self._find_item(dlg, ("folder", "F:\\ROOT"))
        self.assertIsNotNone(item)
        dlg._accept_item(item)
        self.assertEqual((dlg.kind, dlg.value), ("folder", "F:\\ROOT"))

    def test_ftp_selection(self):
        dlg = self._dialog()
        item = self._find_item(dlg, ("ftp_profile", 7))
        self.assertIsNotNone(item)
        dlg._accept_item(item)
        self.assertEqual((dlg.kind, dlg.value), ("ftp_profile", 7))

    def test_used_sender_shows_suffix(self):
        dlg = self._dialog()
        item = self._find_item(dlg, ("sender", "Alice"))
        self.assertIn(dlg.tr("(ya asignado)"), item.text())

    def test_browse_button_sets_browse(self):
        dlg = self._dialog()
        dlg._browse()
        self.assertEqual((dlg.kind, dlg.value), ("browse", None))

    def test_empty_section_shows_placeholder(self):
        dlg = SourcePickerDialog(None, folders=[], senders=[], ftp_profiles=[])
        texts = [dlg.list_widget.item(i).text()
                 for i in range(dlg.list_widget.count())]
        self.assertIn(dlg.tr("(vacío)"), texts)


if __name__ == "__main__":
    unittest.main()
