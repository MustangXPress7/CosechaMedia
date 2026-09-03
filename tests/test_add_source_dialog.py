"""Pruebas del nuevo diálogo «Añadir origen» (AddSourceDialog).

Verifica la tabla plana con 3 secciones y 5 columnas (D-01, D-02), la
integración de dispositivos guardados y detectados (D-03), la distinción
MTP vs USB masivo (D-13/D-14), el aviso WPD no-bloqueante (D-15) y la
detección de cámara off-thread (D-08/D-09).

CRÍTICO: nunca se usa ``.exec()`` modal real en offscreen (cuelga). Los
diálogos/backends se reemplazan con fakes o se ejercitan métodos internos.
"""

import os
import time
import unittest
from unittest import mock

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QApplication, QCheckBox, QLabel, QLineEdit, QPushButton, QTabWidget,
)

import app.core.utils as utils_module
from app.core.mtp import DeviceInfo
from app.ui.add_source_dialog import AddSourceDialog


class _MtpBackend:
    """Backend fake MTP con ``list_devices`` controlable."""

    def __init__(self, devices=None):
        self.devices = devices or []
        self._fail = False

    def fail(self):
        self._fail = True

    def list_devices(self):
        if self._fail:
            raise RuntimeError("WPD boom")
        return self.devices


class TestAddSourceDialog(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def _dialog(self, **kw):
        return AddSourceDialog(None, **kw)

    # -- estructura --------------------------------------------------------

    def test_dialog_title(self):
        dlg = self._dialog()
        self.assertEqual(dlg.windowTitle(), dlg.tr("Añadir origen"))

    def test_flat_structure_no_tabs(self):
        """Tabla plana: sin QTabWidget y con QTableWidget de 3 secciones."""
        dlg = self._dialog()
        self.assertEqual(len(dlg.findChildren(QTabWidget)), 0)
        self.assertTrue(hasattr(dlg, "table"))
        # 3 filas separadoras de sección, una por título
        titles = [dlg.tr("Conexión física (MTP/USB/SD)"),
                  dlg.tr("WiFi / PairDrop"), dlg.tr("FTP")]
        found = [s for i, s in enumerate(dlg._row_sources)
                 if s is None and i < dlg.table.rowCount()]
        # Contar cabeceras por texto de la fila 0 (ruta)
        section_rows = 0
        for i in range(dlg.table.rowCount()):
            lbl = dlg.table.cellWidget(i, 1)
            if isinstance(lbl, QLabel) and lbl.text() in titles:
                section_rows += 1
        self.assertEqual(section_rows, 3)

    def test_five_columns(self):
        dlg = self._dialog()
        self.assertEqual(dlg.table.columnCount(), 5)

    def test_columns_headers(self):
        dlg = self._dialog()
        headers = dlg.table.horizontalHeaderItem
        self.assertEqual(headers(0).text(), dlg.tr("Seleccionar"))
        self.assertEqual(headers(1).text(), dlg.tr("Ruta de origen"))
        self.assertEqual(headers(2).text(), dlg.tr("Cámara"))
        self.assertEqual(headers(3).text(), dlg.tr("Estado"))
        self.assertEqual(headers(4).text(), dlg.tr("Borrar"))

    # -- selección y aceptación -------------------------------------------

    def test_accept_returns_sources(self):
        dlg = self._dialog(folders=["E:\\DCIM", "F:\\ROOT"])
        row = dlg._row_for_source("folder", "E:\\DCIM")
        self.assertIsNotNone(row)
        cam = dlg.table.cellWidget(row, 2)
        cam.setText("Cámara A")
        dlg.table.cellWidget(row, 0).setChecked(True)
        self.assertTrue(dlg.btn_aceptar.isEnabled())
        sources = dlg.result_sources()
        self.assertEqual(len(sources), 1)
        self.assertEqual(sources[0]["kind"], "folder")
        self.assertEqual(sources[0]["value"], "E:\\DCIM")
        self.assertEqual(sources[0]["camera"], "Cámara A")
        self.assertTrue(sources[0]["enabled"])

    def test_accept_returns_multiple_checked(self):
        dlg = self._dialog(folders=["E:\\DCIM", "F:\\ROOT"])
        for path in ("E:\\DCIM", "F:\\ROOT"):
            row = dlg._row_for_source("folder", path)
            dlg.table.cellWidget(row, 2).setText("Cam")
            dlg.table.cellWidget(row, 0).setChecked(True)
        self.assertEqual(len(dlg.result_sources()), 2)

    def test_reject_returns_empty_list(self):
        dlg = self._dialog(folders=["E:\\DCIM"])
        dlg.reject()
        self.assertEqual(dlg.result_sources(), [])

    def test_ok_disabled_without_checked_source(self):
        dlg = self._dialog(folders=["E:\\DCIM"])
        self.assertFalse(dlg.btn_aceptar.isEnabled())

    def test_ok_disabled_until_camera_filled(self):
        dlg = self._dialog(folders=["E:\\DCIM"])
        row = dlg._row_for_source("folder", "E:\\DCIM")
        dlg.table.cellWidget(row, 0).setChecked(True)
        # sin nombre de cámara → deshabilitado
        self.assertFalse(dlg.btn_aceptar.isEnabled())
        dlg.table.cellWidget(row, 2).setText("Sony")
        self.assertTrue(dlg.btn_aceptar.isEnabled())

    # -- inhabilitado / atenuado (D-12) ------------------------------------

    def test_disabled_row_dimmed(self):
        """Filas de dispositivos desconectados: checkbox desc. y no habilitado."""
        dlg = self._dialog(devices_missing=[{"id": "M1", "name": "Cámara A"}])
        row = dlg._row_for_source("device", "M1")
        self.assertIsNotNone(row)
        cb = dlg.table.cellWidget(row, 0)
        self.assertIsInstance(cb, QCheckBox)
        self.assertFalse(cb.isChecked())
        self.assertFalse(cb.isEnabled())
        cam = dlg.table.cellWidget(row, 2)
        self.assertFalse(cam.isEnabled())

    # -- papelera borrar (D-11) -------------------------------------------

    def test_delete_triggers_callback(self):
        calls = []
        dlg = self._dialog(
            folders=["E:\\DCIM"],
            on_delete=lambda k, v: calls.append((k, v)))
        row = dlg._row_for_source("folder", "E:\\DCIM")
        btn = dlg.table.cellWidget(row, 4)
        self.assertIsInstance(btn, QPushButton)
        btn.click()
        self.assertEqual(calls, [("folder", "E:\\DCIM")])

    # -- QR solo para WiFi (D-05/D-06) ------------------------------------

    def test_qr_button_only_for_wifi(self):
        dlg = self._dialog(
            folders=["E:\\DCIM"],
            senders=[{"name": "Alice", "used": False}])
        folder_row = dlg._row_for_source("folder", "E:\\DCIM")
        sender_row = dlg._row_for_source("sender", "Alice")
        folder_widget = dlg.table.cellWidget(folder_row, 1)
        sender_widget = dlg.table.cellWidget(sender_row, 1)
        folder_qr = folder_widget.findChildren(QPushButton)
        sender_qr = sender_widget.findChildren(QPushButton)
        self.assertEqual(len(folder_qr), 0)
        self.assertTrue(any(b.text() == dlg.tr("QR") for b in sender_qr))

    # -- MTP vs USB masivo (D-13/D-14) -------------------------------------

    def test_mtp_vs_usb_mass(self):
        backend = _MtpBackend(devices=[DeviceInfo("dev-1", "Cámara Sony")])
        with mock.patch.object(utils_module, "get_mounted_drives",
                               return_value=["E:\\", "F:\\"]):
            with mock.patch.object(utils_module, "is_removable_drive",
                                   side_effect=lambda p: p == "E:\\"):
                dlg = self._dialog(mtp_backend=backend)
        # La unidad USB masiva E:\ se listó (marcada removable)
        e_row = dlg._row_for_source("usb", "E:\\")
        self.assertIsNotNone(e_row)
        # F:\ no es removable → NO se listó como USB
        self.assertIsNone(dlg._row_for_source("usb", "F:\\"))
        # El dispositivo MTP se listó
        m_row = dlg._row_for_source("device", "dev-1")
        self.assertIsNotNone(m_row)

    def test_mtp_label_in_path(self):
        backend = _MtpBackend(devices=[DeviceInfo("dev-1", "Cámara Sony")])
        with mock.patch.object(utils_module, "get_mounted_drives",
                               return_value=[]):
            dlg = self._dialog(mtp_backend=backend)
        row = dlg._row_for_source("device", "dev-1")
        cam = dlg.table.cellWidget(row, 2)
        self.assertEqual(cam.text(), "Cámara Sony")

    # -- fallo WPD no-bloqueante (D-15) ------------------------------------

    def test_wpd_error_non_blocking(self):
        backend = _MtpBackend()
        backend.fail()
        with mock.patch.object(utils_module, "get_mounted_drives",
                               return_value=[]):
            dlg = self._dialog(mtp_backend=backend)
        # El fallo no derriba: el diálogo conserva su tabla y sigue útil.
        self.assertTrue(hasattr(dlg, "table"))
        self.assertGreaterEqual(dlg.table.columnCount(), 5)
        # Aviso non-bloqueante visible en el diálogo
        self.assertTrue(dlg.error_label.isVisible()
                        or "No se pudo" in dlg.error_label.text())

    # -- detección de cámara off-thread (D-08/D-09) -----------------------

    def test_camera_detection_worker(self):
        dlg = self._dialog(
            folders=["E:\\DCIM"],
            on_detect=lambda kind, value: "Sony A7 III")
        row = dlg._row_for_source("folder", "E:\\DCIM")
        cam = dlg.table.cellWidget(row, 2)
        cam.setText("")
        dlg._detect_camera_for_row(row)
        # worker lanzado; la UI no se bloquea y muestra progreso inline
        self.assertEqual(cam.text(), dlg.tr("Detectando…"))
        deadline = time.time() + 5
        while cam.text() == dlg.tr("Detectando…") and time.time() < deadline:
            QApplication.processEvents()
            time.sleep(0.01)
        self.assertEqual(cam.text(), "Sony A7 III")


if __name__ == "__main__":
    unittest.main()
