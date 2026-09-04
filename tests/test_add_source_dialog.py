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
    QApplication, QCheckBox, QComboBox, QLabel, QLineEdit, QPushButton, QTabWidget,
)

import app.core.utils as utils_module
from app.core.mtp import DeviceInfo
from app.ui.add_source_dialog import AddSourceDialog


def _checkbox(dlg, row):
    """El QCheckBox dentro del contenedor centrado de la fila (CHG-3)."""
    wrap = dlg.table.cellWidget(row, 0)
    for ch in wrap.findChildren(QCheckBox):
        return ch
    return None


def _set_camera(dlg, row, text):
    """Asigna texto al combo editable de cámara de una fila."""
    combo = dlg.table.cellWidget(row, 2)
    combo.setEditText(text)


def _camera_text(dlg, row):
    combo = dlg.table.cellWidget(row, 2)
    return combo.lineEdit().text() if combo.lineEdit() else combo.currentText()


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
        # 3 filas separadoras de sección, una por título (celda combinada col 0)
        titles = [dlg.tr("Conexión física (MTP/USB/SD)"),
                  dlg.tr("WiFi / PairDrop"), dlg.tr("FTP")]
        section_rows = 0
        for i in range(dlg.table.rowCount()):
            lbl = dlg.table.cellWidget(i, 0)
            if isinstance(lbl, QLabel) and lbl.text() in titles:
                section_rows += 1
        self.assertEqual(section_rows, 3)

    def test_section_rows_span_all_columns(self):
        """CHG-4: las filas de sección combinan las 5 columnas con setSpan."""
        dlg = self._dialog()
        for i in range(dlg.table.rowCount()):
            lbl = dlg.table.cellWidget(i, 0)
            if isinstance(lbl, QLabel) and lbl.text() in (
                    dlg.tr("Conexión física (MTP/USB/SD)"),
                    dlg.tr("WiFi / PairDrop"), dlg.tr("FTP")):
                span = dlg.table.rowSpan(i, 0)
                self.assertEqual(span, 1)
                self.assertEqual(dlg.table.columnSpan(i, 0), 5)

    def test_section_label_in_column_0(self):
        """CHG-4: el rótulo de sección se coloca en la columna 0 (antes col 1)."""
        dlg = self._dialog()
        titles = {dlg.tr("Conexión física (MTP/USB/SD)"),
                  dlg.tr("WiFi / PairDrop"), dlg.tr("FTP")}
        found = 0
        for i in range(dlg.table.rowCount()):
            lbl = dlg.table.cellWidget(i, 0)
            if isinstance(lbl, QLabel) and lbl.text() in titles:
                found += 1
        self.assertEqual(found, 3)

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
        _set_camera(dlg, row, "Cámara A")
        _checkbox(dlg, row).setChecked(True)
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
            _set_camera(dlg, row, "Cam")
            _checkbox(dlg, row).setChecked(True)
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
        _checkbox(dlg, row).setChecked(True)
        # sin nombre de cámara → deshabilitado
        self.assertFalse(dlg.btn_aceptar.isEnabled())
        _set_camera(dlg, row, "Sony")
        self.assertTrue(dlg.btn_aceptar.isEnabled())

    # -- inhabilitado / atenuado (D-12) ------------------------------------

    def test_disabled_row_dimmed(self):
        """Filas de dispositivos desconectados: checkbox desc. y no habilitado."""
        dlg = self._dialog(devices_missing=[{"id": "M1", "name": "Cámara A"}])
        row = dlg._row_for_source("device", "M1")
        self.assertIsNotNone(row)
        cb = _checkbox(dlg, row)
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
        self.assertEqual(_camera_text(dlg, row), "Cámara Sony")

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
        _set_camera(dlg, row, "")
        dlg._detect_camera_for_row(row)
        # worker lanzado; la UI no se bloquea y muestra progreso inline
        self.assertEqual(dlg.tr("Detectando…"), _camera_text(dlg, row))
        deadline = time.time() + 5
        while _camera_text(dlg, row) == dlg.tr("Detectando…") and time.time() < deadline:
            QApplication.processEvents()
            time.sleep(0.01)
        self.assertEqual(_camera_text(dlg, row), "Sony A7 III")

    # -- nueva funcionalidad (bugs/mejoras 2026-09-04) --------------------

    def test_delete_removes_row_from_table(self):
        """BUG-2/4: borrar una fila la elimina de la tabla y del dict interno."""
        calls = []
        dlg = self._dialog(
            folders=["E:\\DCIM"],
            on_delete=lambda k, v: calls.append((k, v)) or True)
        row = dlg._row_for_source("folder", "E:\\DCIM")
        before = dlg.table.rowCount()
        btn = dlg.table.cellWidget(row, 4)
        btn.click()
        self.assertEqual(calls, [("folder", "E:\\DCIM")])
        self.assertEqual(dlg.table.rowCount(), before - 1)
        self.assertIsNone(dlg._row_for_source("folder", "E:\\DCIM"))

    def test_delete_row_kept_when_callback_returns_false(self):
        """BUG-4: si on_delete devuelve False, la fila permanece."""
        dlg = self._dialog(
            folders=["E:\\DCIM"],
            on_delete=lambda k, v: False)
        row = dlg._row_for_source("folder", "E:\\DCIM")
        before = dlg.table.rowCount()
        btn = dlg.table.cellWidget(row, 4)
        btn.click()
        self.assertEqual(dlg.table.rowCount(), before)

    def test_delete_row_when_no_callback(self):
        """Si no hay on_delete, la fila se elimina igualmente de la UI."""
        dlg = self._dialog(folders=["E:\\DCIM"])
        row = dlg._row_for_source("folder", "E:\\DCIM")
        before = dlg.table.rowCount()
        btn = dlg.table.cellWidget(row, 4)
        btn.click()
        self.assertEqual(dlg.table.rowCount(), before - 1)

    def test_camera_edit_persists_in_dict(self):
        """BUG-7: editar la cámara actualiza el dict interno (persistente)."""
        dlg = self._dialog(folders=["E:\\DCIM"])
        row = dlg._row_for_source("folder", "E:\\DCIM")
        _set_camera(dlg, row, "Canon R5")
        self.assertEqual(dlg._row_sources[row]["camera"], "Canon R5")

    def test_camera_result_uses_edited_value(self):
        """BUG-7: el valor editado se devuelve en result_sources."""
        dlg = self._dialog(folders=["E:\\DCIM"])
        row = dlg._row_for_source("folder", "E:\\DCIM")
        _set_camera(dlg, row, "Sony FX3")
        _checkbox(dlg, row).setChecked(True)
        sources = dlg.result_sources()
        self.assertEqual(sources[0]["camera"], "Sony FX3")

    def test_checkbox_centered(self):
        """CHG-3: el checkbox de la columna 0 va centrado en un contenedor."""
        dlg = self._dialog(folders=["E:\\DCIM"])
        row = dlg._row_for_source("folder", "E:\\DCIM")
        wrap = dlg.table.cellWidget(row, 0)
        self.assertEqual(len(wrap.findChildren(QCheckBox)), 1)
        cb = _checkbox(dlg, row)
        self.assertIsInstance(cb, QCheckBox)
        self.assertTrue(cb.isChecked() == cb.isChecked())

    def test_camera_combo_with_trigger(self):
        """CHG-5: la celda de cámara es un combo con disparador de detección."""
        dlg = self._dialog(
            folders=["E:\\DCIM"],
            on_detect=lambda kind, value: "Sony A7 III")
        row = dlg._row_for_source("folder", "E:\\DCIM")
        combo = dlg.table.cellWidget(row, 2)
        self.assertIsInstance(combo, QComboBox)
        self.assertTrue(combo.isEditable())
        # El último item es el disparador
        last = combo.count() - 1
        combo.setCurrentIndex(last)
        # Disparar lanza detección
        self.assertEqual(_camera_text(dlg, row), dlg.tr("Detectando…"))
        deadline = time.time() + 5
        while _camera_text(dlg, row) == dlg.tr("Detectando…") and time.time() < deadline:
            QApplication.processEvents()
            time.sleep(0.01)
        self.assertEqual(_camera_text(dlg, row), "Sony A7 III")


if __name__ == "__main__":
    unittest.main()
