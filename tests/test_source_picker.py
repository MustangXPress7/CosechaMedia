"""Pruebas del lanzador compacto de orígenes (SourcePickerDialog)."""
import inspect
import os
import unittest
from unittest import mock

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QDialog, QPushButton

from app.ui.source_picker import SourcePickerDialog


class FakeDeviceDialog(QDialog):
    """Fake de DevicePickerDialog: fija ``exec`` y los datos expuestos."""

    instances = []
    fake_accepted = True

    def __init__(self, parent=None, backend=None):
        super().__init__(parent)
        FakeDeviceDialog.instances.append(self)
        self.accepted = type(self).fake_accepted
        self.device_id = "dev-123"
        self.device_folder = "Almacenamiento/DCIM"
        self.device_name = "Cámara A"

    def exec(self):
        return QDialog.Accepted if self.accepted else QDialog.Rejected


class FakeFtpDialog(QDialog):
    """Fake de FtpPickerDialog: fija ``exec`` y los datos expuestos."""

    instances = []

    def __init__(self, parent=None, backend=None):
        super().__init__(parent)
        FakeFtpDialog.instances.append(self)
        self.profile_id = 7
        self.device_id = "ftp:7"
        self.device_folder = "DCIM"
        self.device_name = "Servidor FTP"

    def exec(self):
        return QDialog.Accepted


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
        )

    def _find_item(self, dlg, role_value):
        for i in range(dlg.list_widget.count()):
            item = dlg.list_widget.item(i)
            if item.data(Qt.UserRole) == role_value:
                return item
        return None

    def _missing_item(self, dlg):
        for i in range(dlg.list_widget.count()):
            item = dlg.list_widget.item(i)
            if item.data(Qt.UserRole) is None and item.text().startswith("📱"):
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

    def test_ftp_profiles_not_duplicated_in_guardados(self):
        # B-04: los perfiles FTP viven en «Configuración → Dispositivos
        # guardados» y en el diálogo FTP; no se duplican en Guardados.
        dlg = SourcePickerDialog(
            None, folders=[], senders=[],
            devices_missing=[{"id": "M1", "name": "Cámara A"}])
        self.assertIsNone(self._find_item(dlg, ("ftp_profile", 7)))

    def test_no_tabs_and_three_sections(self):
        # El diálogo es un lanzador: sin pestañas, una única lista con las
        # tres secciones; los encabezados no llevan UserRole.
        dlg = self._dialog()
        self.assertFalse(hasattr(dlg, "tabs"))
        headers = []
        for i in range(dlg.list_widget.count()):
            item = dlg.list_widget.item(i)
            if item.text() in (dlg.tr("Carpetas guardadas"),
                               dlg.tr("Remitentes WiFi"),
                               dlg.tr("Desconectados")):
                headers.append(item)
        self.assertEqual(len(headers), 3)
        for header in headers:
            self.assertIsNone(header.data(Qt.UserRole))

    def test_ok_btn_disabled_until_valid_selection(self):
        dlg = self._dialog()
        self.assertFalse(dlg.ok_btn.isEnabled())
        item = self._find_item(dlg, ("folder", "E:\\DCIM"))
        dlg.list_widget.setCurrentItem(item)
        self.assertTrue(dlg.ok_btn.isEnabled())
        dlg.list_widget.setCurrentItem(None)
        self.assertFalse(dlg.ok_btn.isEnabled())

    def test_missing_item_does_not_enable_ok(self):
        dlg = SourcePickerDialog(
            None, folders=[], senders=[],
            devices_missing=[{"id": "M1", "name": "Cámara A"}])
        missing = self._missing_item(dlg)
        self.assertIsNotNone(missing)
        dlg.list_widget.setCurrentItem(missing)
        self.assertFalse(dlg.ok_btn.isEnabled())
        dlg._accept_current()
        self.assertIsNone(dlg.kind)
        self.assertIsNone(dlg.value)
        self.assertEqual(dlg.result(), QDialog.Rejected)

    def test_accept_current_noop_without_valid_selection(self):
        dlg = self._dialog()
        dlg.list_widget.setCurrentItem(None)
        dlg._accept_current()
        self.assertIsNone(dlg.kind)
        self.assertIsNone(dlg.value)
        self.assertEqual(dlg.result(), QDialog.Rejected)

    def test_search_buttons_present(self):
        dlg = self._dialog()
        for name, label in (("btn_browse", "Examinar…"),
                            ("btn_mtp", "USB/MTP"),
                            ("btn_ftp", "FTP"),
                            ("btn_wifi_qr", "WiFi QR")):
            btn = getattr(dlg, name)
            self.assertIsInstance(btn, QPushButton)
            self.assertEqual(btn.text(), dlg.tr(label))

    def test_browse_button_sets_browse(self):
        dlg = self._dialog()
        dlg._browse()
        self.assertEqual((dlg.kind, dlg.value), ("browse", None))
        self.assertEqual(dlg.result(), QDialog.Accepted)

    def test_mtp_button_opens_device_picker_and_accepts(self):
        with mock.patch("app.ui.source_picker.DevicePickerDialog",
                        FakeDeviceDialog):
            FakeDeviceDialog.instances.clear()
            FakeDeviceDialog.fake_accepted = True
            dlg = self._dialog()
            dlg._pick_device()
        self.assertEqual(len(FakeDeviceDialog.instances), 1)
        self.assertEqual(dlg.kind, "device")
        self.assertEqual(dlg.value,
                         ("dev-123", "Almacenamiento/DCIM", "Cámara A"))
        self.assertEqual(dlg.result(), QDialog.Accepted)

    def test_mtp_button_cancel_keeps_launcher_open(self):
        with mock.patch("app.ui.source_picker.DevicePickerDialog",
                        FakeDeviceDialog):
            FakeDeviceDialog.instances.clear()
            FakeDeviceDialog.fake_accepted = False
            dlg = self._dialog()
            dlg._pick_device()
        self.assertEqual(len(FakeDeviceDialog.instances), 1)
        self.assertIsNone(dlg.kind)
        self.assertIsNone(dlg.value)
        self.assertEqual(dlg.result(), QDialog.Rejected)

    def test_mtp_requires_valid_device_folder(self):
        # T-260816-01: el lanzador no confía solo en el Accepted del hijo;
        # exige device_id/device_folder no vacíos antes de aceptar.
        class EmptyFolderDialog(FakeDeviceDialog):
            def __init__(self, parent=None, backend=None):
                super().__init__(parent)
                self.device_folder = ""
        with mock.patch("app.ui.source_picker.DevicePickerDialog",
                        EmptyFolderDialog):
            FakeDeviceDialog.fake_accepted = True
            dlg = self._dialog()
            dlg._pick_device()
        self.assertIsNone(dlg.kind)
        self.assertEqual(dlg.result(), QDialog.Rejected)

    def test_ftp_button_opens_ftp_picker_and_accepts(self):
        with mock.patch("app.ui.source_picker.FtpPickerDialog", FakeFtpDialog):
            FakeFtpDialog.instances.clear()
            dlg = self._dialog()
            dlg._pick_ftp()
        self.assertEqual(len(FakeFtpDialog.instances), 1)
        self.assertEqual(dlg.kind, "ftp_new")
        self.assertEqual(dlg.value, (7, "ftp:7", "DCIM", "Servidor FTP"))
        self.assertEqual(dlg.result(), QDialog.Accepted)

    def test_wifi_qr_button_sets_wifi(self):
        dlg = self._dialog()
        dlg.btn_wifi_qr.click()
        self.assertEqual((dlg.kind, dlg.value), ("wifi", None))
        self.assertEqual(dlg.result(), QDialog.Accepted)

    def test_double_click_item_accepts(self):
        dlg = self._dialog()
        item = self._find_item(dlg, ("folder", "F:\\ROOT"))
        self.assertIsNotNone(item)
        dlg.show()
        QApplication.processEvents()
        rect = dlg.list_widget.visualItemRect(item)
        QTest.mouseDClick(dlg.list_widget.viewport(), Qt.LeftButton,
                          Qt.KeyboardModifiers(), rect.center())
        QApplication.processEvents()
        self.assertEqual((dlg.kind, dlg.value), ("folder", "F:\\ROOT"))
        self.assertEqual(dlg.result(), QDialog.Accepted)
        dlg.close()

    def test_used_sender_shows_suffix(self):
        dlg = self._dialog()
        item = self._find_item(dlg, ("sender", "Alice"))
        self.assertIn(dlg.tr("(ya asignado)"), item.text())

    def test_empty_section_shows_placeholder(self):
        dlg = SourcePickerDialog(None, folders=[], senders=[])
        texts = [dlg.list_widget.item(i).text()
                 for i in range(dlg.list_widget.count())]
        self.assertIn(dlg.tr("(vacío)"), texts)

    def test_missing_section_lists_devices(self):
        # B-04: «Desconectados» solo lista dispositivos MTP conocidos; los
        # perfiles FTP no se repiten aquí (viven en «Configuración →
        # Dispositivos guardados» y en el diálogo FTP).
        dlg = SourcePickerDialog(
            None, folders=[], senders=[],
            devices_missing=[{"id": "M1", "name": "Cámara A"}])
        texts = [dlg.list_widget.item(i).text()
                 for i in range(dlg.list_widget.count())]
        self.assertIn(dlg.tr("Desconectados"), texts)
        self.assertTrue(any(t.startswith("📱") for t in texts))
        self.assertTrue(any(dlg.tr("desconectado") in t for t in texts))
        missing = self._missing_item(dlg)
        self.assertIsNotNone(missing)
        self.assertTrue(missing.toolTip())

    def test_delete_saved_removes_item(self):
        calls = []
        dlg = SourcePickerDialog(
            None, folders=["E:\\DCIM"], senders=[],
            on_delete=lambda k, v: calls.append((k, v)) or True)
        item = self._find_item(dlg, ("folder", "E:\\DCIM"))
        self.assertIsNotNone(item)
        dlg._delete_selected(item, ("folder", "E:\\DCIM"))
        self.assertEqual(calls, [("folder", "E:\\DCIM")])
        self.assertIsNone(self._find_item(dlg, ("folder", "E:\\DCIM")))

    def test_delete_saved_keeps_item_when_rejected(self):
        dlg = SourcePickerDialog(
            None, folders=["E:\\DCIM"], senders=[],
            on_delete=lambda k, v: False)
        item = self._find_item(dlg, ("folder", "E:\\DCIM"))
        dlg._delete_selected(item, ("folder", "E:\\DCIM"))
        self.assertIsNotNone(self._find_item(dlg, ("folder", "E:\\DCIM")))

    def test_constructor_signature_compat(self):
        # Compatibilidad con _pick_source_entry (main_window.py).
        params = list(inspect.signature(SourcePickerDialog.__init__).parameters)
        for name in ("folders", "senders", "devices_missing", "mtp_backend",
                     "ftp_backend", "on_delete"):
            self.assertIn(name, params)


if __name__ == "__main__":
    unittest.main()
