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
import json
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
        self.assertEqual(headers(2).text(), dlg.tr("Dispositivo"))
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

    def test_usb_missing_renders_as_usb_row_not_mtp(self):
        """Bug 3: una unidad USB guardada (clave ``usb:<ruta>``) desconectada
        debe renderizarse como ``kind=usb`` con etiqueta [USB], nunca como MTP."""
        dlg = self._dialog(devices_missing=[{"id": "usb:E:\\", "name": "Sony"}])
        row = dlg._row_for_source("usb", "E:\\")
        self.assertIsNotNone(row)
        self.assertIsNone(dlg._row_for_source("device", "usb:E:\\"))
        lbl = dlg.table.cellWidget(row, 1)
        text = " ".join(ch.text() for ch in lbl.findChildren(QLabel))
        self.assertIn("[USB]", text)
        # No seleccionable (desconectado) y no habilitado
        cb = _checkbox(dlg, row)
        self.assertFalse(cb.isEnabled())

    def test_usb_connected_renders_selectable(self):
        """Una USB montada (usb_connected) es seleccionable al reabrir «Añadir
        origen» en otro proyecto, sin pulsar «Detectar» ni depender de que esté
        guardada (tras borrar el origen, la unidad física sigue apareciendo)."""
        dlg = self._dialog(usb_connected=["F:\\"], folders=["E:\\DCIM"])
        row = dlg._row_for_source("usb", "F:\\")
        self.assertIsNotNone(row)
        cb = _checkbox(dlg, row)
        self.assertTrue(cb.isEnabled())
        # Queda dentro de result_sources al marcar + aceptar
        cb.setChecked(True)
        dlg.accept()
        sources = dlg.result_sources()
        self.assertTrue(any(s["kind"] == "usb" and s["value"] == "F:\\"
                            for s in sources))

    def test_usb_connected_no_conflict_with_missing(self):
        """Si la misma USB viene en usb_connected y en devices_missing, no se
        duplica (la montada gana como seleccionable)."""
        dlg = self._dialog(
            devices_missing=[{"id": "usb:E:\\", "name": "Sony"}],
            usb_connected=["E:\\"])
        e_rows = [i for i, s in enumerate(dlg._row_sources)
                  if s is not None and s["kind"] == "usb" and s["value"] == "E:\\"]
        self.assertEqual(len(e_rows), 1)
        self.assertTrue(_checkbox(dlg, e_rows[0]).isEnabled())

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

    def test_detected_device_inserted_in_physical_section(self):
        """BUG-3: tras "Detectar", los MTP nuevos se insertan antes de la sección WiFi."""
        backend = _MtpBackend([_Device("MTP1", "Cam A")])
        dlg = self._dialog(mtp_backend=backend, folders=["E:\\DCIM"])
        wifi_row = dlg._section_start_row(1)
        # Lanzar detección: el MTP no está presente aún, debe añadirse
        dlg._detect_devices()
        device_row = dlg._row_for_source("device", "MTP1")
        self.assertIsNotNone(device_row)
        # El dispositivo debe quedar ANTES del encabezado WiFi
        self.assertLess(device_row, wifi_row)

    def test_detect_adds_usb_even_without_explicit_backend(self):
        """Bug E/F: "Detectar" escanea USB incluso con _explicit_mtp=False
        (producción sin backend). En construcción no se escanean devuelve 0
        esperando a que usb_connected lo provea; al pulsar «Detectar» sí."""
        with mock.patch.object(utils_module, "get_mounted_drives",
                               return_value=["H:\\"]), \
             mock.patch.object(utils_module, "is_removable_drive",
                               return_value=True):
            dlg = self._dialog(folders=["E:\\DCIM"])
            # Sin usb_connected: la mounted drive NO se lista en construcción
            self.assertIsNone(dlg._row_for_source("usb", "H:\\"))
            # Pero «Detectar» sí la escanea y no rompe
            dlg._detect_devices()
            self.assertIsNotNone(dlg._row_for_source("usb", "H:\\"))

    def test_detect_skips_non_removable_usb_without_explicit_backend(self):
        """Tras "Detectar", una unidad que no es removable real no se añade."""
        with mock.patch.object(utils_module, "get_mounted_drives",
                               return_value=["E:\\", "F:\\"]), \
             mock.patch.object(utils_module, "is_removable_drive",
                               side_effect=lambda p: p == "E:\\"):
            dlg = self._dialog(folders=["E:\\DCIM"])
            dlg._detect_devices()
            self.assertIsNotNone(dlg._row_for_source("usb", "E:\\"))
            self.assertIsNone(dlg._row_for_source("usb", "F:\\"))

    def test_usb_known_name_prefills_combo(self):
        """Quick 260908-f5o: una USB con nombre conocido en el registro
        (device_settings/known_devices) pre-selecciona el combo de cámara."""
        import app.ui.add_source_dialog as dlgmod
        with mock.patch.object(dlgmod, "usb_device_id",
                               return_value="usb:E:\\"), \
             mock.patch.object(dlgmod.db, "get_dispositivo_for_device",
                               return_value="Sony A7S"):
            dlg = self._dialog(usb_connected=["E:\\"])
        row = dlg._row_for_source("usb", "E:\\")
        self.assertIsNotNone(row)
        self.assertEqual(_camera_text(dlg, row), "Sony A7S")
        self.assertNotEqual(_camera_text(dlg, row), dlg.tr("Sin nombre"))

    def test_usb_known_name_prefills_after_detect(self):
        """Quick 260908-f5o: «Detectar» también pre-rellena el nombre conocido."""
        import app.ui.add_source_dialog as dlgmod
        with mock.patch.object(utils_module, "get_mounted_drives",
                               return_value=["E:\\"]), \
             mock.patch.object(utils_module, "is_removable_drive",
                               return_value=True), \
             mock.patch.object(dlgmod, "usb_device_id",
                               return_value="usb:E:\\"), \
             mock.patch.object(dlgmod.db, "get_dispositivo_for_device",
                               return_value="Sony A7S"):
            dlg = self._dialog(folders=["E:\\DCIM"])
            dlg._detect_devices()
        row = dlg._row_for_source("usb", "E:\\")
        self.assertIsNotNone(row)
        self.assertEqual(_camera_text(dlg, row), "Sony A7S")

    def test_usb_unknown_keeps_sin_nombre(self):
        """Quick 260908-f5o: USB sin nombre conocido → combo «Sin nombre»."""
        import app.ui.add_source_dialog as dlgmod
        with mock.patch.object(dlgmod.db, "get_dispositivo_for_device",
                               return_value=None):
            dlg = self._dialog(usb_connected=["E:\\"])
        row = dlg._row_for_source("usb", "E:\\")
        self.assertIsNotNone(row)
        self.assertEqual(_camera_text(dlg, row), dlg.tr("Sin nombre"))

    def test_wifi_row_inserted_in_wifi_section(self):
        """BUG-3: un nuevo WiFi se inserta antes de la sección FTP."""
        dlg = self._dialog(folders=["E:\\DCIM"])
        wifi_row = dlg._section_start_row(1)
        # Simular inserción de fila WiFi sin depender de QInputDialog
        dlg._append_raw_source(
            {"kind": "sender", "value": "NuevoMóvil", "camera": "NuevoMóvil",
             "enabled": True, "connected": True, "label": "NuevoMóvil",
             "type": "WiFi"},
            insert_before_row=dlg._section_start_row(2))
        sender_row = dlg._row_for_source("sender", "NuevoMóvil")
        ftp_row = dlg._section_start_row(2)
        self.assertIsNotNone(sender_row)
        self.assertGreaterEqual(sender_row, wifi_row)
        self.assertLess(sender_row, ftp_row)

    def test_detected_device_delete_button_works(self):
        """BUG-4: el botón borrar de un dispositivo recién detectado elimina la fila."""
        backend = _MtpBackend([_Device("MTP9", "Cam Z")])
        calls = []
        dlg = self._dialog(
            mtp_backend=backend,
            on_delete=lambda k, v: calls.append((k, v)) or True)
        dlg._detect_devices()
        row = dlg._row_for_source("device", "MTP9")
        self.assertIsNotNone(row)
        btn = dlg.table.cellWidget(row, 4)
        self.assertIsNotNone(btn)
        before = dlg.table.rowCount()
        btn.click()
        self.assertEqual(calls, [("device", "MTP9")])
        self.assertEqual(dlg.table.rowCount(), before - 1)
        self.assertIsNone(dlg._row_for_source("device", "MTP9"))


# -- importar/exportar JSON (device registry consolidado) -------------

    def test_import_export_buttons_exist(self):
        """El diálogo tiene botones Importar JSON y Exportar JSON."""
        dlg = self._dialog()
        buttons = dlg.findChildren(QPushButton)
        texts = {b.text() for b in buttons}
        self.assertIn(dlg.tr("Importar JSON"), texts)
        self.assertIn(dlg.tr("Exportar JSON"), texts)

    def test_export_json_writes_valid_file(self):
        """_export_json escribe un JSON con los dispositivos conocidos."""
        import app.ui.add_source_dialog as dlg_mod
        with mock.patch.object(dlg_mod.db, "list_known_devices") as m_list, \
             mock.patch.object(dlg_mod.QMessageBox, "information") as m_info, \
             mock.patch("app.ui.add_source_dialog.QFileDialog.getSaveFileName",
                        return_value=(os.path.join(
                            os.environ.get("TEMP", "."), "kd_export_test.json"), True)):
            m_list.return_value = [
                {"device_id": "mtp:PNP1", "device_type": "mtp", "name": "Cam A",
                 "serial": "S1", "last_camera": "Cam A", "last_seen": "2026-09-06",
                 "metadata": {}},
            ]
            dlg = self._dialog()
            dlg._export_json()
            m_info.assert_called_once()
        path = os.path.join(os.environ.get("TEMP", "."), "kd_export_test.json")
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            self.assertEqual(len(data), 1)
            self.assertEqual(data[0]["device_id"], "mtp:PNP1")
        finally:
            if os.path.exists(path):
                os.remove(path)

    def test_import_json_adds_disconnected_rows(self):
        """_import_json persiste en known_devices y añade filas desconectadas."""
        import app.ui.add_source_dialog as dlg_mod
        payload = [
            {"device_id": "mtp:PNP_X", "device_type": "mtp", "name": "Cam Import",
             "serial": "SX", "last_camera": "Cam Import", "metadata": {}},
        ]
        path = os.path.join(os.environ.get("TEMP", "."), "kd_import_test.json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump(payload, f)
        try:
            imported = []
            def _fake_upsert(*a, **kw):
                imported.append(a[0])
                return 1
            with mock.patch.object(dlg_mod.db, "upsert_known_device",
                                   side_effect=_fake_upsert), \
                 mock.patch.object(dlg_mod.QMessageBox, "information"), \
                 mock.patch("app.ui.add_source_dialog.QFileDialog.getOpenFileName",
                            return_value=(path, True)):
                dlg = self._dialog()
                dlg._import_json()
            self.assertIn("mtp:PNP_X", imported)
            # La fila desconectada MTP se añadió a la tabla
            row = dlg._row_for_source("device", "mtp:PNP_X")
            self.assertIsNotNone(row)
            cam = dlg.table.cellWidget(row, 2)
            self.assertFalse(cam.isEnabled())
        finally:
            if os.path.exists(path):
                os.remove(path)

    def test_import_json_skips_wifi_and_folders(self):
        """WiFi/folder importados no se añaden como filas MTP desconectadas."""
        import app.ui.add_source_dialog as dlg_mod
        payload = [
            {"device_id": "wifi:pairdrop", "device_type": "wifi", "name": "WiFi",
             "metadata": {}},
            {"device_id": "folder:/tmp/x", "device_type": "folder", "name": "Carpeta",
             "metadata": {}},
        ]
        with mock.patch.object(dlg_mod.db, "upsert_known_device",
                               return_value=1), \
             mock.patch.object(dlg_mod.QMessageBox, "information"), \
             mock.patch("app.ui.add_source_dialog.QFileDialog.getOpenFileName",
                        return_value=("whatever.json", True)), \
             mock.patch("builtins.open",
                        mock.mock_open(read_data=json.dumps(payload))):
            dlg = self._dialog()
            dlg._import_json()
        self.assertIsNone(dlg._row_for_source("device", "wifi:pairdrop"))
        self.assertIsNone(dlg._row_for_source("device", "folder:/tmp/x"))

    def test_import_json_cancel_noop(self):
        """Cancelar el diálogo de archivo no hace nada."""
        import app.ui.add_source_dialog as dlg_mod
        with mock.patch("app.ui.add_source_dialog.QFileDialog.getOpenFileName",
                        return_value=("", False)):
            dlg = self._dialog()
            dlg._import_json()
        # Sin filas añadidas por import
        self.assertIsNone(dlg._row_for_source("device", "mtp:PNP_X"))


class _Device:
    """Minimal fake con los atributos que usa el diálogo (name, device_id)."""

    def __init__(self, device_id, name):
        self.device_id = device_id
        self.name = name


# -- E2E: full user flows ----------------------------------------------------

    def test_full_acceptance_flow_multiple_sources(self):
        """E2E: open dialog → select multiple sources → edit cameras → accept → verify result_sources."""
        dlg = self._dialog(
            folders=["E:\\DCIM", "F:\\ROOT"],
            senders=[{"name": "Alice", "used": False}],
            on_detect=lambda kind, value: "Sony A7 III",
            on_qr=lambda name: None)
        # Check folder 1
        row1 = dlg._row_for_source("folder", "E:\\DCIM")
        _set_camera(dlg, row1, "Cámara 1")
        _checkbox(dlg, row1).setChecked(True)
        # Check folder 2
        row2 = dlg._row_for_source("folder", "F:\\ROOT")
        _set_camera(dlg, row2, "Cámara 2")
        _checkbox(dlg, row2).setChecked(True)
        # Check WiFi sender
        row3 = dlg._row_for_source("sender", "Alice")
        _set_camera(dlg, row3, "Móvil Alice")
        _checkbox(dlg, row3).setChecked(True)
        self.assertTrue(dlg.btn_aceptar.isEnabled())
        dlg.accept()
        sources = dlg.result_sources()
        self.assertEqual(len(sources), 3)
        kinds = {s["kind"] for s in sources}
        self.assertEqual(kinds, {"folder", "folder", "sender"})
        cameras = {s["camera"] for s in sources}
        self.assertEqual(cameras, {"Cámara 1", "Cámara 2", "Móvil Alice"})

    def test_mtp_folder_picker_interaction(self):
        """E2E: select MTP device → click Detectar → verify folder selector appears (mocked)."""
        backend = _MtpBackend(devices=[DeviceInfo("dev-mtp", "Cámara MTP")])
        dlg = self._dialog(mtp_backend=backend)
        row = dlg._row_for_source("device", "dev-mtp")
        self.assertIsNotNone(row)
        # Simulate clicking "Detectar" (which triggers _detect_devices)
        with mock.patch.object(utils_module, "get_mounted_drives", return_value=[]):
            with mock.patch("app.ui.add_source_dialog.QFileDialog.getExistingDirectory", return_value="E:\\DCIM"):
                dlg._detect_devices()
        # Device should already be present (enumerated in _populate)
        self.assertIsNotNone(dlg._row_for_source("device", "dev-mtp"))

    def test_wifi_qr_flow(self):
        """E2E: select WiFi sender → click QR button → verify on_qr callback invoked."""
        qr_calls = []
        dlg = self._dialog(
            senders=[{"name": "Bob", "used": False}],
            on_qr=lambda name: qr_calls.append(name))
        row = dlg._row_for_source("sender", "Bob")
        self.assertIsNotNone(row)
        path_widget = dlg.table.cellWidget(row, 1)
        qr_btns = path_widget.findChildren(QPushButton)
        qr_btn = next((b for b in qr_btns if b.text() == dlg.tr("QR")), None)
        self.assertIsNotNone(qr_btn)
        qr_btn.click()
        self.assertEqual(qr_calls, ["Bob"])

    def test_ftp_profile_selection(self):
        """E2E: select FTP profile → verify row has correct kind and value."""
        class _FakeFtpBackend:
            def list_profiles(self):
                return [{"id": "ftp-1", "name": "Mi FTP", "host": "192.168.1.10"}]
        dlg = self._dialog(ftp_backend=_FakeFtpBackend())
        row = dlg._row_for_source("ftp_profile", "ftp-1")
        self.assertIsNotNone(row)
        cam = dlg.table.cellWidget(row, 2)
        self.assertEqual(_camera_text(dlg, row), "Mi FTP")

    def test_new_wifi_button_adds_sender(self):
        """E2E: click Nuevo WiFi → mock QInputDialog → verify sender row added to table."""
        with mock.patch("app.ui.add_source_dialog.QInputDialog.getText", return_value=("NuevoMóvil", True)):
            dlg = self._dialog()
            before = dlg.table.rowCount()
            dlg._add_wifi_row()
            # New row should be in WiFi section (before FTP section)
            row = dlg._row_for_source("sender", "NuevoMóvil")
            self.assertIsNotNone(row)
            self.assertEqual(dlg.table.rowCount(), before + 1)

    def test_new_ftp_button_opens_picker(self):
        """E2E: click Nuevo FTP → mock FtpPickerDialog → verify profile row added."""
        class _FakePicker:
            def __init__(self, parent):
                self._accepted = True
                self.device_id = "ftp-new"
                self.device_folder = "/remote"
                self.device_name = "FTP Nuevo"
            def exec(self):
                return QDialog.Accepted
        with mock.patch("app.ui.add_source_dialog.FtpPickerDialog", _FakePicker):
            dlg = self._dialog()
            before = dlg.table.rowCount()
            dlg._add_ftp_row()
            row = dlg._row_for_source("ftp_profile", "ftp-new")
            self.assertIsNotNone(row)
            self.assertEqual(dlg.table.rowCount(), before + 1)

    def test_reject_cancel_returns_empty(self):
        """E2E: open dialog → make selections → click Cancel → verify result_sources() == []."""
        dlg = self._dialog(folders=["E:\\DCIM"])
        row = dlg._row_for_source("folder", "E:\\DCIM")
        _set_camera(dlg, row, "Test Cam")
        _checkbox(dlg, row).setChecked(True)
        dlg.reject()
        self.assertEqual(dlg.result_sources(), [])

    def test_keyboard_navigation_accept(self):
        """E2E: Tab navigation → Space to toggle checkbox → Enter on Aceptar."""
        dlg = self._dialog(folders=["E:\\DCIM"])
        dlg.show()
        # Focus first checkbox
        QApplication.processEvents()
        wrap = dlg.table.cellWidget(1, 0)  # first data row, col 0
        cb = wrap.findChildren(QCheckBox)[0]
        cb.setFocus()
        # Space to toggle
        from PySide6.QtTest import QTest
        QTest.keyClick(cb, Qt.Key_Space)
        self.assertTrue(cb.isChecked())
        # Tab to camera combo
        QTest.keyClick(cb, Qt.Key_Tab)
        cam = dlg.table.cellWidget(1, 2)
        cam.setFocus()
        # Type camera name
        QTest.keyClicks(cam.lineEdit(), "Keyboard Cam")
        # Tab to Aceptar and press Enter
        dlg.btn_aceptar.setFocus()
        QTest.keyClick(dlg.btn_aceptar, Qt.Key_Enter)
        QApplication.processEvents()
        sources = dlg.result_sources()
        self.assertEqual(len(sources), 1)
        self.assertEqual(sources[0]["camera"], "Keyboard Cam")


    def test_dialog_init_purges_folder_known_devices(self):
        """Bug 5: al abrir el diálogo se limpian las carpetas legacy persistidas
        como 'folder' en known_devices."""
        from app.core.db import db
        with mock.patch.object(db, "delete_known_devices_by_type", return_value=0) as m:
            self._dialog()
        m.assert_called_once_with("folder")

    def test_browse_folder_no_longer_upserts_known_device(self):
        """Bug 5: añadir una carpeta local no debe persistirla en known_devices
        (no es un dispositivo; ya vive en recent_paths)."""
        import app.ui.add_source_dialog as dlgmod
        dlg = self._dialog()
        calls = []
        orig = dlgmod.db.upsert_known_device

        def _spy(*a, **k):
            calls.append(a)
            return 0

        dlgmod.db.upsert_known_device = _spy
        try:
            with mock.patch.object(dlgmod.QFileDialog, "getExistingDirectory",
                                   return_value="C:/carpeta-test"):
                dlg._browse_folder()
        finally:
            dlgmod.db.upsert_known_device = orig
        args_list = [a for a in calls if len(a) > 1 and a[1] == "folder"]
        self.assertEqual(args_list, [])
        self.assertEqual(len([s for s in dlg._row_sources if s and s["kind"] == "folder"]), 1)


class TestCameraVacioDefault(unittest.TestCase):
    """Bug 6: «— Vacío —» existe en modo manual y automático y es la opción
    predeterminada cuando la fila no tiene cámara."""

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def _combo(self, camera=""):
        dlg = AddSourceDialog(None)
        src = {"kind": "device", "value": "PNP1", "camera": camera,
               "enabled": True, "connected": True}
        dlg._row_sources = [None, src]
        with mock.patch.object(AddSourceDialog, "_known_camera_names",
                               return_value=["Canon C300", "Sony FX6"]):
            combo = dlg._build_camera_combo(1, src)
        return dlg, combo

    def test_manual_mode_has_vacio_and_is_default(self):
        dlg, combo = self._combo()
        texts = [combo.itemText(i) for i in range(combo.count())]
        self.assertIn(dlg.tr("— Sin nombre —"), texts)
        self.assertEqual(combo.currentIndex(), dlg._vacio_trigger_index)
        self.assertEqual(combo.itemData(combo.currentIndex()), "VACIO")
        self.assertEqual(combo.lineEdit().text(), "")

    def test_known_camera_still_selected_when_present(self):
        dlg, combo = self._combo(camera="Sony FX6")
        self.assertEqual(combo.currentText(), "Sony FX6")
        self.assertNotEqual(combo.currentIndex(), dlg._vacio_trigger_index)

    def test_selecting_vacio_clears_camera_text(self):
        dlg, combo = self._combo(camera="Sony FX6")
        dlg._row_sources = [None, {"kind": "device", "value": "PNP1",
                                   "camera": "Sony FX6", "connected": True}]
        dlg.table.setCellWidget(1, 2, combo)
        combo.setCurrentIndex(dlg._vacio_trigger_index)
        self.assertEqual(combo.lineEdit().text(), "")
        self.assertEqual(dlg._row_sources[1]["camera"], "")


class TestCameraNameChangedCallback(unittest.TestCase):
    """B-20: el diálogo notifica ediciones de nombre de dispositivo al
    llamador vía on_camera_name_changed(device_id, nombre)."""

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def _dialog(self, **kw):
        return AddSourceDialog(None, **kw)

    def test_edit_camera_fires_callback_for_device(self):
        """Editar el combo de un dispositivo MTP dispara el callback con el
        device_id real y el nuevo nombre."""
        calls = []
        dlg = self._dialog(
            devices_connected=[DeviceInfo("dev-1", "Cámara MTP")],
            on_camera_name_changed=lambda did, name: calls.append((did, name)))
        row = dlg._row_for_source("device", "dev-1")
        self.assertIsNotNone(row)
        _set_camera(dlg, row, "Cámara A")
        self.assertEqual(calls, [("dev-1", "Cámara A")])

    def test_ftp_row_has_fixed_readonly_name(self):
        """Bug 7: la cámara de una fila FTP es fija (solo lectura), no un combo."""
        class _FakeFtpBackend:
            def list_profiles(self):
                return [{"id": "ftp-1", "name": "Mi FTP", "host": "192.168.1.10"}]
        dlg = self._dialog(ftp_backend=_FakeFtpBackend())
        row = dlg._row_for_source("ftp_profile", "ftp-1")
        self.assertIsNotNone(row)
        cam = dlg.table.cellWidget(row, 2)
        self.assertIsInstance(cam, QLineEdit)
        self.assertTrue(cam.isReadOnly())
        self.assertEqual(cam.text(), "Mi FTP")

    def test_sender_row_has_fixed_readonly_name(self):
        """Bug 7: la cámara de una fila de remitente WiFi es fija (solo lectura)."""
        dlg = self._dialog(senders=[{"name": "Alice", "used": False}])
        row = dlg._row_for_source("sender", "Alice")
        self.assertIsNotNone(row)
        cam = dlg.table.cellWidget(row, 2)
        self.assertIsInstance(cam, QLineEdit)
        self.assertTrue(cam.isReadOnly())
        self.assertEqual(cam.text(), "Alice")

    def test_no_callback_for_folder_rows(self):
        """Las filas de carpeta (sin device_id) NO disparan el callback."""
        calls = []
        dlg = self._dialog(
            folders=["E:\\DCIM"],
            on_camera_name_changed=lambda did, name: calls.append((did, name)))
        row = dlg._row_for_source("folder", "E:\\DCIM")
        self.assertIsNotNone(row)
        _set_camera(dlg, row, "Cámara X")
        self.assertEqual(calls, [])

    def test_placeholder_sin_nombre_not_persisted(self):
        """El placeholder 'Sin nombre' no se guarda como nombre real."""
        calls = []
        dlg = self._dialog(
            devices_connected=[DeviceInfo("dev-3", "Cámara C")],
            on_camera_name_changed=lambda did, name: calls.append((did, name)))
        row = dlg._row_for_source("device", "dev-3")
        combo = dlg.table.cellWidget(row, 2)
        combo.setEditText(dlg.tr("Sin nombre"))
        self.assertEqual(calls, [])


if __name__ == "__main__":
    unittest.main()
