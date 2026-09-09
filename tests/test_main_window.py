"""Tests de regresión para MainWindow y funciones core relacionadas.

Cubre: detección de cámara (token-based), rename_dispositivo (separadores),
_free_space, generate_integrity_report, y flujo básico de sesión.
"""

import os
import sys
import time
import tempfile
import shutil
import unittest
from types import SimpleNamespace
from unittest import mock

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication, QLabel, QMessageBox
from PySide6.QtCore import Qt, QTimer

import app.ui.main_window as mw
import app.ui.mixins.camera_mixin as camera_mixin_module
import app.ui.mixins.sessions_mixin as sessions_mixin_module
import app.ui.mixins.sources_mixin as sources_mixin_module
import app.ui.mixins.project_mixin as project_mixin_module
import app.ui.mixins.devices_mixin as devices_mixin_module
import app.ui.mixins.ingest_mixin as ingest_mixin_module
import app.core.ingestor as ingestor_module
import app.core.metadata_engine as me_module
from app.core.db import DatabaseManager
from app.core.ingestor import _free_space, generate_integrity_report, generate_card_content_report
from app.core.sd_reader import sd_reader
from app.ui import theme


class TestMetadataUnverifiedMarker(unittest.TestCase):
    """D-02: el marker 'Metadatos no verificados' se muestra en la celda de
    cámara (columna 1) + tooltip, NUNCA en la columna de estado (2); así
    _clear_completed_rows sigue limpiando las filas 'Completado'."""

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="sdimport_marker_")
        self._orig_db = mw.db
        self._orig_cam_db = camera_mixin_module.db
        self._orig_sess_db = sessions_mixin_module.db
        self._orig_sources_db = sources_mixin_module.db
        self._orig_proj_db = project_mixin_module.db
        self._orig_ing_db = ingestor_module.db
        self._orig_me_db = me_module.db
        self._orig_devices_db = devices_mixin_module.db
        self._orig_ingest_mixin_db = ingest_mixin_module.db
        self.db = DatabaseManager(db_path=os.path.join(self.tmp, "marker.db"))
        mw.db = self.db
        camera_mixin_module.db = self.db
        sessions_mixin_module.db = self.db
        sources_mixin_module.db = self.db
        project_mixin_module.db = self.db
        ingestor_module.db = self.db
        me_module.db = self.db
        devices_mixin_module.db = self.db
        ingest_mixin_module.db = self.db

        conn = self.db.get_connection()
        conn.execute(
            "INSERT INTO projects (name, root_path) VALUES ('Test', ?)", (self.tmp,)
        )
        self.pid = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
        conn.commit()
        conn.close()

        self.window = mw.MainWindow()
        self.window.current_project_id = self.pid

    def tearDown(self):
        if hasattr(self.window, '_sync_timer') and self.window._sync_timer:
            self.window._sync_timer.stop()
        if hasattr(self.window, '_cam_timer') and self.window._cam_timer:
            self.window._cam_timer.stop()
        self.window.close()
        mw.db = self._orig_db
        camera_mixin_module.db = self._orig_cam_db
        sessions_mixin_module.db = self._orig_sess_db
        sources_mixin_module.db = self._orig_sources_db
        project_mixin_module.db = self._orig_proj_db
        ingestor_module.db = self._orig_ing_db
        me_module.db = self._orig_me_db
        devices_mixin_module.db = self._orig_devices_db
        ingest_mixin_module.db = self._orig_ingest_mixin_db
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_marker_in_camera_cell_keeps_status_completado(self):
        """El marker de metadata no verificada va a la celda de cámara (1) y
        la columna de estado (2) mantiene 'Completado', de modo que
        _clear_completed_rows sigue eliminando la fila (Pitfall 3)."""
        src = os.path.join(self.tmp, "src")
        os.makedirs(src)
        source_file = os.path.join(src, "clip.mp4")
        with open(source_file, "wb") as f:
            f.write(b"data")
        self.window.on_file_started(source_file)
        row = self.window.table.rowCount() - 1

        self.window.on_file_finished(
            source_file, os.path.join(self.tmp, "dest", "clip.mp4"), True,
            {"camera_model": "SinClasificar", "metadata_verified": False})

        camera_text = self.window.table.item(row, 1).text()
        self.assertEqual(camera_text, "SinClasificar")
        self.assertEqual(self.window.table.item(row, 2).text(),
                         self.window.tr("Completado"))

        self.window._clear_completed_rows()
        self.assertEqual(self.window.table.rowCount(), 0)

    def test_verified_camera_still_shows_model(self):
        """Cuando los metadatos están verificados, la celda de cámara muestra
        el modelo y el estado permanece 'Completado'."""
        src = os.path.join(self.tmp, "src2")
        os.makedirs(src)
        source_file = os.path.join(src, "clip.mp4")
        with open(source_file, "wb") as f:
            f.write(b"data")
        self.window.on_file_started(source_file)
        row = self.window.table.rowCount() - 1

        self.window.on_file_finished(
            source_file, os.path.join(self.tmp, "dest2", "clip.mp4"), True,
            {"camera_model": "iPhone 15 Pro", "metadata_verified": True})

        self.assertEqual(self.window.table.item(row, 1).text(), "iPhone 15 Pro")
        self.assertEqual(self.window.table.item(row, 2).text(),
                         self.window.tr("Completado"))

    def test_unknown_camera_keeps_existing_value_no_crash(self):
        """BUG: camera_model == 'Unknown' con metadata_verified True lanzaba
        UnboundLocalError (camera_item sin asignar). La celda de cámara
        conserva el valor previo ('Sin nombre') y no crashea."""
        src = os.path.join(self.tmp, "src3")
        os.makedirs(src)
        source_file = os.path.join(src, "clip.mp4")
        with open(source_file, "wb") as f:
            f.write(b"data")
        self.window.on_file_started(source_file)
        row = self.window.table.rowCount() - 1

        self.window.on_file_finished(
            source_file, os.path.join(self.tmp, "dest3", "clip.mp4"), True,
            {"camera_model": "Unknown", "metadata_verified": True})

        self.assertEqual(self.window.table.item(row, 1).text(),
                         self.window.tr("Sin nombre"))
        self.assertEqual(self.window.table.item(row, 2).text(),
                         self.window.tr("Completado"))


class TestIngestTableTerminology(unittest.TestCase):
    """B-13: la tabla de ingesta usa el término 'Dispositivo' (no 'Cámara')
    en la cabecera; las celdas siguen mostrando el modelo detectado."""

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="sdimport_term_")
        self._orig_db = mw.db
        self._orig_cam_db = camera_mixin_module.db
        self._orig_sess_db = sessions_mixin_module.db
        self._orig_sources_db = sources_mixin_module.db
        self._orig_proj_db = project_mixin_module.db
        self._orig_ing_db = ingestor_module.db
        self._orig_me_db = me_module.db
        self._orig_devices_db = devices_mixin_module.db
        self._orig_ingest_mixin_db = ingest_mixin_module.db
        self.db = DatabaseManager(db_path=os.path.join(self.tmp, "cam.db"))
        mw.db = self.db
        camera_mixin_module.db = self.db
        sessions_mixin_module.db = self.db
        sources_mixin_module.db = self.db
        project_mixin_module.db = self.db
        ingestor_module.db = self.db
        me_module.db = self.db
        devices_mixin_module.db = self.db
        ingest_mixin_module.db = self.db

        conn = self.db.get_connection()
        conn.execute(
            "INSERT INTO projects (name, root_path) VALUES ('Test', ?)", (self.tmp,)
        )
        self.pid = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
        conn.commit()
        conn.close()

        self.window = mw.MainWindow()
        self.window.current_project_id = self.pid

    def tearDown(self):
        if hasattr(self.window, '_sync_timer') and self.window._sync_timer:
            self.window._sync_timer.stop()
        if hasattr(self.window, '_cam_timer') and self.window._cam_timer:
            self.window._cam_timer.stop()
        self.window.close()
        mw.db = self._orig_db
        camera_mixin_module.db = self._orig_cam_db
        sessions_mixin_module.db = self._orig_sess_db
        sources_mixin_module.db = self._orig_sources_db
        project_mixin_module.db = self._orig_proj_db
        ingestor_module.db = self._orig_ing_db
        me_module.db = self._orig_me_db
        devices_mixin_module.db = self._orig_devices_db
        ingest_mixin_module.db = self._orig_ingest_mixin_db
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_ingest_table_header_says_dispositivo(self):
        """La cabecera de la columna 1 es 'Dispositivo', nunca 'Cámara'."""
        header = self.window.table.horizontalHeaderItem(1).text()
        self.assertEqual(header, self.window.tr("Dispositivo"))
        self.assertNotEqual(header, "Cámara")

    def test_ingest_table_cell_shows_camera_model(self):
        """Las celdas de la columna 1 siguen mostrando el modelo del
        dispositivo detectado (no cambia el contenido, solo el rótulo)."""
        src = os.path.join(self.tmp, "src")
        os.makedirs(src)
        source_file = os.path.join(src, "clip.mp4")
        with open(source_file, "wb") as f:
            f.write(b"data")
        self.window._current_camera_map = {src: "Canon C300"}
        self.window.on_file_started(source_file)
        row = self.window.table.rowCount() - 1
        self.assertEqual(self.window.table.item(row, 1).text(), "Canon C300")


class TestCameraPersistence(unittest.TestCase):
    """Verifica persistencia de cámara en DB (I-03): sd_cards y device_settings."""

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="sdimport_persist_")
        self.db = DatabaseManager(db_path=os.path.join(self.tmp, "persist.db"))
        self._orig_db = mw.db
        self._orig_cam_db = camera_mixin_module.db
        self._orig_sess_db = sessions_mixin_module.db
        self._orig_sources_db = sources_mixin_module.db
        self._orig_proj_db = project_mixin_module.db
        self._orig_ing_db = ingestor_module.db
        self._orig_me_db = me_module.db
        self._orig_devices_db = devices_mixin_module.db
        self._orig_ingest_mixin_db = ingest_mixin_module.db
        mw.db = self.db
        camera_mixin_module.db = self.db
        sessions_mixin_module.db = self.db
        sources_mixin_module.db = self.db
        project_mixin_module.db = self.db
        ingestor_module.db = self.db
        me_module.db = self.db
        devices_mixin_module.db = self.db
        ingest_mixin_module.db = self.db

        conn = self.db.get_connection()
        conn.execute(
            "INSERT INTO projects (name, root_path) VALUES ('Test', ?)", (self.tmp,)
        )
        self.pid = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
        conn.commit()
        conn.close()

        self.window = mw.MainWindow()
        self.window.current_project_id = self.pid

    def tearDown(self):
        if hasattr(self.window, '_sync_timer') and self.window._sync_timer:
            self.window._sync_timer.stop()
        self.window.close()
        mw.db = self._orig_db
        camera_mixin_module.db = self._orig_cam_db
        sessions_mixin_module.db = self._orig_sess_db
        sources_mixin_module.db = self._orig_sources_db
        project_mixin_module.db = self._orig_proj_db
        ingestor_module.db = self._orig_ing_db
        me_module.db = self._orig_me_db
        devices_mixin_module.db = self._orig_devices_db
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_known_sd_card_auto_fills(self):
        from unittest.mock import patch
        src = os.path.join(self.tmp, "card")
        os.makedirs(src)
        self.db.save_dispositivo("AAAA1111", "Canon C300")
        sid = self.db.create_session(self.pid, "S1", "2024-01-01", "active", src)
        with patch.object(sd_reader, 'get_volume_serial', return_value="AAAA1111"):
            self.window._detect_camera_for_session(sid, src)
        sess = self.db.get_session(sid)
        self.assertEqual(sess.get("nombre_dispositivo"), "Canon C300")

    def test_known_device_auto_fills(self):
        src = os.path.join(self.tmp, "mtp")
        os.makedirs(src)
        self.db.save_dispositivo_config("mtp:ABC", "Sony FX6")
        sid = self.db.create_session(self.pid, "S1", "2024-01-01", "active", src)
        conn = self.db.get_connection()
        conn.execute("UPDATE sessions SET device_id = ? WHERE id = ?",
                     ("mtp:ABC", sid))
        conn.commit()
        conn.close()
        self.window._detect_camera_for_session(sid, src)
        sess = self.db.get_session(sid)
        self.assertEqual(sess.get("nombre_dispositivo"), "Sony FX6")

    def test_persist_after_rename(self):
        src = os.path.join(self.tmp, "card2")
        os.makedirs(src)
        sid = self.db.create_session(self.pid, "S1", "2024-01-01", "active", src)
        self.window._persist_camera_mapping(sid, src, "RED V-Raptor")
        serial = self.db.get_connection().execute(
            "SELECT serial FROM sd_cards LIMIT 1"
        ).fetchone()
        if serial:
            cam = self.db.get_dispositivo_for_card(serial[0])
            self.assertEqual(cam, "RED V-Raptor")

    def test_persist_after_prompt(self):
        src = os.path.join(self.tmp, "card3")
        os.makedirs(src)
        sid = self.db.create_session(self.pid, "S1", "2024-01-01", "active", src)
        self.window._persist_camera_mapping(sid, src, "ARRI Alexa")
        serial = self.db.get_connection().execute(
            "SELECT serial FROM sd_cards LIMIT 1"
        ).fetchone()
        if serial:
            cam = self.db.get_dispositivo_for_card(serial[0])
            self.assertEqual(cam, "ARRI Alexa")


class TestDevicePersistenceAcrossProjects(unittest.TestCase):
    """B-17/D-12: los dispositivos guardados (device_settings) persisten al
    deshabilitar un origen y al borrar el proyecto. Solo la papelera del
    diálogo «Añadir origen» borra el guardado."""

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="sdimport_devpersist_")
        self.db = DatabaseManager(db_path=os.path.join(self.tmp, "devpersist.db"))
        self._orig_db = mw.db
        self._orig_cam_db = camera_mixin_module.db
        self._orig_sess_db = sessions_mixin_module.db
        self._orig_sources_db = sources_mixin_module.db
        self._orig_proj_db = project_mixin_module.db
        self._orig_ing_db = ingestor_module.db
        self._orig_me_db = me_module.db
        self._orig_devices_db = devices_mixin_module.db
        self._orig_ingest_mixin_db = ingest_mixin_module.db
        mw.db = self.db
        camera_mixin_module.db = self.db
        sessions_mixin_module.db = self.db
        sources_mixin_module.db = self.db
        project_mixin_module.db = self.db
        ingestor_module.db = self.db
        me_module.db = self.db
        devices_mixin_module.db = self.db
        ingest_mixin_module.db = self.db

        conn = self.db.get_connection()
        conn.execute(
            "INSERT INTO projects (name, root_path) VALUES ('Test', ?)", (self.tmp,)
        )
        self.pid = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
        conn.commit()
        conn.close()

        self.window = mw.MainWindow()
        self.window.current_project_id = self.pid
        self.window.project_camera_detection_mode = "manual"

        self.src = os.path.join(self.tmp, "card")
        os.makedirs(self.src)
        self.sid = self.db.create_session(self.pid, "S1", "2024-01-01", "active",
                                          self.src)
        self.db.save_dispositivo_config("mtp:PERSIST1", "Sony FX6")
        self.db.update_session_config(self.sid, device_id="mtp:PERSIST1",
                                      nombre_dispositivo="Sony FX6")

    def tearDown(self):
        if hasattr(self.window, '_sync_timer') and self.window._sync_timer:
            self.window._sync_timer.stop()
        if hasattr(self.window, '_cam_timer') and self.window._cam_timer:
            self.window._cam_timer.stop()
        self.window.close()
        mw.db = self._orig_db
        camera_mixin_module.db = self._orig_cam_db
        sessions_mixin_module.db = self._orig_sess_db
        sources_mixin_module.db = self._orig_sources_db
        project_mixin_module.db = self._orig_proj_db
        ingestor_module.db = self._orig_ing_db
        me_module.db = self._orig_me_db
        devices_mixin_module.db = self._orig_devices_db
        ingest_mixin_module.db = self._orig_ingest_mixin_db
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _count_device_settings(self, key):
        conn = self.db.get_connection()
        try:
            row = conn.execute(
                "SELECT COUNT(*) FROM device_settings WHERE device_key = ?", (key,)
            ).fetchone()
            return row[0]
        finally:
            conn.close()

    def test_disable_source_keeps_device_settings(self):
        """Desmarcar el checkbox → enabled=0 en la sesión y device_settings
        intactos (B-17): inhabilitar NO es borrar."""
        self.window._on_source_widget_check_changed(0, self.src, Qt.Unchecked)
        sess = self.db.get_session(self.sid)
        self.assertEqual(sess.get("enabled"), 0)
        self.assertEqual(self._count_device_settings("mtp:PERSIST1"), 1)

    def test_disabled_source_row_is_dimmed(self):
        """Con enabled=0 la etiqueta del origen aparece atenuada (D-12)."""
        self.window._populate_source_paths_from_sessions()
        self.window._refresh_source_list()
        self.window._on_source_widget_check_changed(0, self.src, Qt.Unchecked)
        # La sesión queda en la tabla (habilitada=0) al refrescar la lista
        self.window._populate_source_paths_from_sessions()
        self.window._refresh_source_list()
        cell = self.window.source_list.cellWidget(0, 0)
        label = next(w for w in cell.findChildren(QLabel) if w.text() == self.src)
        self.assertIn(theme.color("text_disabled"), label.styleSheet())

    def test_delete_project_keeps_device_settings(self):
        """Borrar el proyecto NO borra device_settings: el dispositivo sigue
        disponible para otros proyectos y en «Añadir origen» (B-17)."""
        with mock.patch.object(mw.QMessageBox, "question",
                               return_value=mw.QMessageBox.Yes):
            with mock.patch.object(mw.QMessageBox, "information"):
                self.window.delete_current_project()
        self.assertEqual(self._count_device_settings("mtp:PERSIST1"), 1)
        # La sesión del proyecto sí se borra
        self.assertIsNone(self.db.get_session(self.sid))

    def test_add_source_trash_deletes_device_settings(self):
        """La papelera del diálogo «Añadir origen» SÍ borra device_settings:
        es el kill switch intencional (B-04)."""
        with mock.patch.object(mw.QMessageBox, "question",
                               return_value=mw.QMessageBox.Yes):
            result = self.window._delete_saved_source("device", "mtp:PERSIST1")
        self.assertTrue(result)
        self.assertEqual(self._count_device_settings("mtp:PERSIST1"), 0)


class TestDisconnectedDeviceStatus(unittest.TestCase):
    """Tarea 3: la columna Estado muestra «Conectado»/«Desconectado» según la
    conectividad real (cache alimentado por la sonda off-thread)."""

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="sdimport_status_")
        self.db = DatabaseManager(db_path=os.path.join(self.tmp, "status.db"))
        self._orig_db = mw.db
        self._orig_cam_db = camera_mixin_module.db
        self._orig_sess_db = sessions_mixin_module.db
        self._orig_sources_db = sources_mixin_module.db
        self._orig_proj_db = project_mixin_module.db
        self._orig_ing_db = ingestor_module.db
        self._orig_me_db = me_module.db
        self._orig_devices_db = devices_mixin_module.db
        self._orig_ingest_mixin_db = ingest_mixin_module.db
        mw.db = self.db
        camera_mixin_module.db = self.db
        sessions_mixin_module.db = self.db
        sources_mixin_module.db = self.db
        project_mixin_module.db = self.db
        ingestor_module.db = self.db
        me_module.db = self.db
        devices_mixin_module.db = self.db
        ingest_mixin_module.db = self.db

        conn = self.db.get_connection()
        conn.execute(
            "INSERT INTO projects (name, root_path) VALUES ('Test', ?)", (self.tmp,)
        )
        self.pid = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
        conn.commit()
        conn.close()

        self.window = mw.MainWindow()
        self.window.current_project_id = self.pid
        self.window.project_camera_detection_mode = "manual"

        self.src = os.path.join(self.tmp, "device")
        os.makedirs(self.src)
        self.sid = self.db.create_session(self.pid, "S1", "2024-01-01", "active",
                                          self.src)
        self.db.update_session_config(self.sid, device_id="mtp:OFF1",
                                      nombre_dispositivo="Sony FX6")
        self.window._populate_source_paths_from_sessions()

    def tearDown(self):
        if hasattr(self.window, '_sync_timer') and self.window._sync_timer:
            self.window._sync_timer.stop()
        if hasattr(self.window, '_cam_timer') and self.window._cam_timer:
            self.window._cam_timer.stop()
        self.window.close()
        mw.db = self._orig_db
        camera_mixin_module.db = self._orig_cam_db
        sessions_mixin_module.db = self._orig_sess_db
        sources_mixin_module.db = self._orig_sources_db
        project_mixin_module.db = self._orig_proj_db
        ingestor_module.db = self._orig_ing_db
        me_module.db = self._orig_me_db
        devices_mixin_module.db = self._orig_devices_db
        ingest_mixin_module.db = self._orig_ingest_mixin_db
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _status_label(self, row=0):
        cell = self.window.source_list.cellWidget(row, 2)
        self.assertIsInstance(cell, QLabel)
        return cell

    def test_mtp_device_shows_disconnected_when_unknown(self):
        """Sin datos de sonda aún, un dispositivo MTP guardado se muestra
        «Desconectado» (no «Conectado») — Tarea 3."""
        self.window._refresh_source_list()
        self.assertIn(self.window.tr("Desconectado"), self._status_label().text())

    def test_mtp_device_shows_connected_when_reachable(self):
        """Con la sonda que reporta el dispositivo como alcanzable → verde."""
        self.window._connectivity["mtp:OFF1"] = True
        self.window._refresh_source_list()
        self.assertIn(self.window.tr("Conectado"), self._status_label().text())

    def test_ftp_profile_disconnected_when_probe_fails(self):
        """Perfil FTP cuya sonda falla → «Desconectado» (test plan
        test_ftp_profile_connectivity_check)."""
        self.db.update_session_config(self.sid, device_id="ftp:42",
                                      device_folder="DCIM")
        self.window._connectivity["ftp:42"] = False
        self.window._populate_source_paths_from_sessions()
        self.window._refresh_source_list()
        self.assertIn(self.window.tr("Desconectado"), self._status_label().text())

    def test_folder_source_shows_dash(self):
        """Un origen de carpeta (sin device_id) no muestra estado de conexión."""
        self.db.update_session_config(self.sid, device_id="", source_path=self.src)
        self.window._source_paths = [self.src]
        self.window._refresh_source_list()
        self.assertIn("—", self._status_label().text())

    def test_wifi_source_status_follows_server_running(self):
        """WiFi: «Conectado» cuando el servidor está en marcha; si no, no."""
        self.db.update_session_config(self.sid, device_id="wifi:pairdrop",
                                      nombre_dispositivo="Alice")
        self.window._populate_source_paths_from_sessions()
        # servidor parado
        self.window._wifi_server = SimpleNamespace(running=False)
        self.window._refresh_source_list()
        self.assertIn(self.window.tr("Desconectado"), self._status_label().text())
        # servidor en marcha
        self.window._wifi_server = SimpleNamespace(running=True)
        self.window._update_source_status_cells()
        self.assertIn(self.window.tr("Conectado"), self._status_label().text())

    def test_update_source_status_cells_from_probe(self):
        """El resultado de la sonda refresca solo la columna Estado in-place."""
        self.window._refresh_source_list()
        self.assertIn(self.window.tr("Desconectado"), self._status_label().text())
        self.window._connectivity["mtp:OFF1"] = True
        self.window._connectivity_ts = time.time()
        self.window._update_source_status_cells()
        self.assertIn(self.window.tr("Conectado"), self._status_label().text())

    def test_probe_device_connectivity_uses_mtp_and_ftp(self):
        """La sonda module-level enumera MTP y comprueba FTP; los WiFi no
        entran en el mapa de conectividad."""
        fake_dev = SimpleNamespace(device_id="mtp:ON1")
        with mock.patch.object(mw.mtp.WpdBackend, "list_devices",
                               return_value=[fake_dev]):
            with mock.patch.object(mw.FtpBackend, "is_reachable",
                                   return_value=True) as fr:
                result = mw._probe_device_connectivity([
                    {"device_id": "mtp:ON1"},
                    {"device_id": "mtp:OFF1"},
                    {"device_id": "ftp:7"},
                    {"device_id": "wifi:pairdrop"},
                ])
        self.assertEqual(result["mtp_connected"], {"mtp:ON1"})
        self.assertEqual(result["ftp_reachable"], {"ftp:7"})
        fr.assert_called_once_with("ftp:7")
        self.assertIn("ftp_backend", result)
        self.assertNotIn("wifi:pairdrop", result["mtp_connected"])
        self.assertNotIn("wifi:pairdrop", result["ftp_reachable"])


class TestForcePromptI14(unittest.TestCase):
    """I-14: force_prompt muestra el prompt en modo manual cuando no hay cámara conocida."""

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self._orig_db = mw.db
        self._orig_cam_db = camera_mixin_module.db
        self._orig_sess_db = sessions_mixin_module.db
        self._orig_sources_db = sources_mixin_module.db
        self._orig_proj_db = project_mixin_module.db
        self._orig_ing_db = ingestor_module.db
        self._orig_me_db = me_module.db
        self._orig_devices_db = devices_mixin_module.db
        self._orig_ingest_mixin_db = ingest_mixin_module.db
        self.db = DatabaseManager(db_path=os.path.join(self.tmp, "test.db"))
        mw.db = self.db
        camera_mixin_module.db = self.db
        sessions_mixin_module.db = self.db
        sources_mixin_module.db = self.db
        project_mixin_module.db = self.db
        ingestor_module.db = self.db
        me_module.db = self.db
        devices_mixin_module.db = self.db
        conn = self.db.get_connection()
        conn.execute(
            "INSERT INTO projects (name, root_path) VALUES ('Test', ?)", (self.tmp,)
        )
        self.pid = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
        conn.commit()
        conn.close()
        self.window = mw.MainWindow()
        self.window.current_project_id = self.pid

    def tearDown(self):
        self.window.close()
        mw.db = self._orig_db
        camera_mixin_module.db = self._orig_cam_db
        sessions_mixin_module.db = self._orig_sess_db
        sources_mixin_module.db = self._orig_sources_db
        project_mixin_module.db = self._orig_proj_db
        ingestor_module.db = self._orig_ing_db
        me_module.db = self._orig_me_db
        devices_mixin_module.db = self._orig_devices_db
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_manual_no_prompt_without_force(self):
        """Sin cámara conocida y sin force_prompt: se muestra prompt manual."""
        src = os.path.join(self.tmp, "card")
        os.makedirs(src)
        sid = self.db.create_session(self.pid, "S1", "2024-01-01", "active", src)
        with mock.patch("PySide6.QtWidgets.QInputDialog.getText") as m:
            m.return_value = ("", False)
            self.window._detect_camera_for_session(sid, src, force_prompt=False)
        m.assert_called_once()

    def test_manual_prompt_with_force(self):
        src = os.path.join(self.tmp, "card")
        os.makedirs(src)
        sid = self.db.create_session(self.pid, "S1", "2024-01-01", "active", src)
        with mock.patch("PySide6.QtWidgets.QInputDialog.getText") as m:
            m.return_value = ("Panasonic S5", True)
            self.window._detect_camera_for_session(sid, src, force_prompt=True)
        m.assert_called_once()
        sess = self.db.get_session(sid)
        self.assertEqual(sess.get("nombre_dispositivo"), "Panasonic S5")

    def test_force_prompt_shows_prompt_even_when_known(self):
        """Con cámara conocida y force_prompt=True: se muestra prompt para permitir cambio."""
        src = os.path.join(self.tmp, "card")
        os.makedirs(src)
        self.db.save_dispositivo_config("mtp:X", "Known Cam")
        sid = self.db.create_session(self.pid, "S1", "2024-01-01", "active", src)
        conn = self.db.get_connection()
        conn.execute("UPDATE sessions SET device_id = ? WHERE id = ?",
                     ("mtp:X", sid))
        conn.commit()
        conn.close()
        with mock.patch("PySide6.QtWidgets.QInputDialog.getText") as m:
            m.return_value = ("Nuevo Nombre", True)
            self.window._detect_camera_for_session(sid, src, force_prompt=True)
        m.assert_called_once()
        sess = self.db.get_session(sid)
        self.assertEqual(sess.get("nombre_dispositivo"), "Nuevo Nombre")

    def test_known_camera_auto_fills_without_force(self):
        """Con cámara conocida y force_prompt=False: auto-rellena sin prompt."""
        src = os.path.join(self.tmp, "card")
        os.makedirs(src)
        self.db.save_dispositivo_config("mtp:X", "Known Cam")
        sid = self.db.create_session(self.pid, "S1", "2024-01-01", "active", src)
        conn = self.db.get_connection()
        conn.execute("UPDATE sessions SET device_id = ? WHERE id = ?",
                     ("mtp:X", sid))
        conn.commit()
        conn.close()
        with mock.patch("PySide6.QtWidgets.QInputDialog.getText") as m:
            self.window._detect_camera_for_session(sid, src, force_prompt=False)
        m.assert_not_called()
        sess = self.db.get_session(sid)
        self.assertEqual(sess.get("nombre_dispositivo"), "Known Cam")


class TestRenameCamera(unittest.TestCase):
    """Verifica rename_dispositivo con separadores / y \\."""

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="sdimport_rename_")
        self._orig_ing_db = ingestor_module.db
        self._orig_me_db = me_module.db
        self.db = DatabaseManager(db_path=os.path.join(self.tmp, "rename.db"))
        ingestor_module.db = self.db
        me_module.db = self.db

        conn = self.db.get_connection()
        conn.execute(
            "INSERT INTO projects (name, root_path) VALUES ('Test', ?)", (self.tmp,)
        )
        self.pid = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
        conn.commit()
        conn.close()

        self.dest = os.path.join(self.tmp, "Footage")
        os.makedirs(os.path.join(self.dest, "OLD_CAM", "2024-01-01"))
        from app.core.ingestor import Ingestor
        self.ing = Ingestor.__new__(Ingestor)
        self.ing.destination_root = self.tmp
        self.ing.folder_name = "Footage"
        self.ing._dispositivo_mapping = {}
        self.ing._dispositivo_lock = __import__("threading").Lock()
        self.ing._db_lock = __import__("threading").Lock()

    def tearDown(self):
        ingestor_module.db = self._orig_ing_db
        me_module.db = self._orig_me_db
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _insert_file(self, session_id, dest_path):
        conn = self.db.get_connection()
        conn.execute(
            "INSERT INTO files (session_id, dest_path, file_size, md5_hash, status) "
            "VALUES (?, ?, 100, 'abc', 'copied')",
            (session_id, dest_path)
        )
        conn.commit()
        conn.close()

    def _get_dest_paths(self, session_id):
        conn = self.db.get_connection()
        rows = conn.execute(
            "SELECT dest_path FROM files WHERE session_id = ?", (session_id,)
        ).fetchall()
        conn.close()
        return [r[0] for r in rows]

    def test_rename_updates_forward_slash_paths(self):
        sid = "1"
        self._insert_file(sid, "/data/Footage/OLD_CAM/2024-01-01/clip.mp4")
        self.ing.rename_dispositivo("OLD_CAM", "NEW_CAM")
        paths = self._get_dest_paths(sid)
        self.assertEqual(paths[0], "/data/Footage/NEW_CAM/2024-01-01/clip.mp4")

    def test_rename_updates_backslash_paths(self):
        sid = "2"
        self._insert_file(sid, "D:\\Footage\\OLD_CAM\\2024-01-01\\clip.mp4")
        self.ing.rename_dispositivo("OLD_CAM", "NEW_CAM")
        paths = self._get_dest_paths(sid)
        self.assertEqual(paths[0], "D:\\Footage\\NEW_CAM\\2024-01-01\\clip.mp4")

    def test_rename_updates_mixed_separator_paths(self):
        sid = "3"
        self._insert_file(sid, "/data/Footage/OLD_CAM/2024-01-01/clip.mp4")
        self._insert_file(sid, "D:\\Footage\\OLD_CAM\\2024-01-01\\clip2.mp4")
        self.ing.rename_dispositivo("OLD_CAM", "NEW_CAM")
        paths = self._get_dest_paths(sid)
        self.assertIn("/data/Footage/NEW_CAM/2024-01-01/clip.mp4", paths)
        self.assertIn("D:\\Footage\\NEW_CAM\\2024-01-01\\clip2.mp4", paths)


class TestRenameDialogPersistence(unittest.TestCase):
    """B-20: renombrar en el diálogo «Añadir origen» persiste el nombre en
    device_settings y sincroniza las sesiones abiertas del dispositivo."""

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="sdimport_dlgrename_")
        self.db = DatabaseManager(db_path=os.path.join(self.tmp, "dlgrename.db"))
        self._orig_db = mw.db
        self._orig_cam_db = camera_mixin_module.db
        self._orig_sess_db = sessions_mixin_module.db
        self._orig_sources_db = sources_mixin_module.db
        self._orig_proj_db = project_mixin_module.db
        self._orig_ing_db = ingestor_module.db
        self._orig_me_db = me_module.db
        self._orig_devices_db = devices_mixin_module.db
        self._orig_ingest_mixin_db = ingest_mixin_module.db
        mw.db = self.db
        camera_mixin_module.db = self.db
        sessions_mixin_module.db = self.db
        sources_mixin_module.db = self.db
        project_mixin_module.db = self.db
        ingestor_module.db = self.db
        me_module.db = self.db
        devices_mixin_module.db = self.db
        ingest_mixin_module.db = self.db

        conn = self.db.get_connection()
        conn.execute(
            "INSERT INTO projects (name, root_path) VALUES ('Test', ?)", (self.tmp,)
        )
        self.pid = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
        conn.commit()
        conn.close()

        self.window = mw.MainWindow()
        self.window.current_project_id = self.pid
        self.window.project_camera_detection_mode = "manual"
        self.src = os.path.join(self.tmp, "dev")
        os.makedirs(self.src)

    def tearDown(self):
        if hasattr(self.window, '_sync_timer') and self.window._sync_timer:
            self.window._sync_timer.stop()
        if hasattr(self.window, '_cam_timer') and self.window._cam_timer:
            self.window._cam_timer.stop()
        self.window.close()
        mw.db = self._orig_db
        camera_mixin_module.db = self._orig_cam_db
        sessions_mixin_module.db = self._orig_sess_db
        sources_mixin_module.db = self._orig_sources_db
        project_mixin_module.db = self._orig_proj_db
        ingestor_module.db = self._orig_ing_db
        me_module.db = self._orig_me_db
        devices_mixin_module.db = self._orig_devices_db
        ingest_mixin_module.db = self._orig_ingest_mixin_db
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _session_with_device(self, sid, device_id, src):
        sid = self.db.create_session(self.pid, sid, "2024-01-01", "active", src)
        conn = self.db.get_connection()
        conn.execute("UPDATE sessions SET device_id = ? WHERE id = ?",
                     (device_id, sid))
        conn.commit()
        conn.close()
        return sid

    def test_rename_in_dialog_persists_device_settings(self):
        """Editar el nombre en el diálogo actualiza device_settings y la
        sesión del dispositivo (B-20, ruta «device»)."""
        from unittest.mock import patch
        from app.core.mtp import DeviceInfo
        sid = self._session_with_device("S1", "mtp:ren1", self.src)
        import app.ui.add_source_dialog as asd
        with patch.object(asd, "db", self.db):
            dlg = asd.AddSourceDialog(
                None, devices_connected=[DeviceInfo("mtp:ren1", "Sony FX6")],
                on_camera_name_changed=self.window._on_dialog_camera_name_changed)
            row = dlg._row_for_source("device", "mtp:ren1")
            self.assertIsNotNone(row)
            combo = dlg.table.cellWidget(row, 2)
            combo.setEditText("Nuevo Nombre")
            dlg.close()
        self.assertEqual(self.db.get_dispositivo_for_device("mtp:ren1"),
                         "Nuevo Nombre")
        sess = self.db.get_session(sid)
        self.assertEqual(sess.get("nombre_dispositivo"), "Nuevo Nombre")

    def test_rename_in_dialog_ftp_prefix(self):
        """La ruta FTP usa el device_id con prefijo ftp: (B-20)."""
        from unittest.mock import patch
        sid = self._session_with_device("S2", "ftp:42", self.src)

        class _FakeFtpBackend:
            def list_profiles(self):
                return [{"id": "42", "name": "Mi FTP", "host": "192.168.1.10"}]
        import app.ui.add_source_dialog as asd
        with patch.object(asd, "db", self.db):
            dlg = asd.AddSourceDialog(
                None, ftp_backend=_FakeFtpBackend(),
                on_camera_name_changed=self.window._on_dialog_camera_name_changed)

    def test_cross_project_rename_persists(self):
        """Renombrar en el diálogo persiste en device_settings (global): el
        nuevo nombre aparece al volver a abrir el diálogo (B-20, cross-project)."""
        from unittest.mock import patch
        from app.core.mtp import DeviceInfo
        self._session_with_device("S3", "mtp:ren3", self.src)
        import app.ui.add_source_dialog as asd
        with patch.object(asd, "db", self.db):
            dlg = asd.AddSourceDialog(
                None, devices_connected=[DeviceInfo("mtp:ren3", "Sony FX3")],
                on_camera_name_changed=self.window._on_dialog_camera_name_changed)
            row = dlg._row_for_source("device", "mtp:ren3")
            combo = dlg.table.cellWidget(row, 2)
            combo.setEditText("RED Komodo 6K")
            dlg.close()
        # Segundo diálogo (aunque el proyecto sea otro, el guardado global aparece)
        self.window.current_project_id = None
        with patch.object(asd, "db", self.db):
            dlg2 = asd.AddSourceDialog(
                None, devices_connected=[DeviceInfo("mtp:ren3", "Sony FX3")])
            row2 = dlg2._row_for_source("device", "mtp:ren3")
            combo2 = dlg2.table.cellWidget(row2, 2)
            self.assertEqual(combo2.lineEdit().text(), "RED Komodo 6K")
            dlg2.close()

    def test_rename_usb_reconciles_serial_identity(self):
        """Renombrar una unidad USB desde el diálogo actualiza también la
        identidad por serial (sd_cards): el nombre viejo no queda huérfano
        (debug: renombrar-sobreescribe-nombre-device)."""
        from unittest.mock import patch
        sid = self._session_with_device("SUSB", "usb:F:\\", "F:\\")
        self.db.save_dispositivo("073e1bba", "Culote")
        with patch.object(sd_reader, "get_volume_serial", return_value="073e1bba"):
            self.window._on_dialog_camera_name_changed("usb:F:\\", "Pitorrote")
        self.assertEqual(self.db.get_dispositivo_for_card("073e1bba"), "Pitorrote")
        self.assertEqual(self.db.get_dispositivo_for_device("usb:F:\\"), "Pitorrote")
        self.assertEqual(self.db.list_known_camera_names(), ["Pitorrote"])

    def test_persist_mapping_usb_reconciles_serial(self):
        """_persist_camera_mapping con device_id usb: sincroniza sd_cards por
        serial (ruta del pop-up «¿Guardar para futuras sesiones?»)."""
        from unittest.mock import patch
        sid = self._session_with_device("SUSB2", "usb:F:\\", "F:\\")
        self.db.save_dispositivo("073e1bba", "Culote")
        with patch.object(sd_reader, "get_volume_serial", return_value="073e1bba"):
            self.window._persist_camera_mapping(sid, "F:\\", "Pitorrote")
        self.assertEqual(self.db.get_dispositivo_for_card("073e1bba"), "Pitorrote")
        self.assertEqual(self.db.list_known_camera_names(), ["Pitorrote"])

    def test_persist_mapping_ftp_does_not_write_serial(self):
        """FTP no reconcilia identidad serial: su source_path es un staging
        local y no debe contaminar sd_cards con el serial del disco del sistema."""
        from unittest.mock import patch
        sid = self._session_with_device("SFTP", "ftp:42", os.path.join(self.tmp, "staging"))
        with patch.object(sd_reader, "get_volume_serial", return_value="c0ffee00"):
            self.window._persist_camera_mapping(sid, os.path.join(self.tmp, "staging"), "Camara FTP")
        self.assertIsNone(self.db.get_dispositivo_for_card("c0ffee00"))


class TestFreeSpace(unittest.TestCase):
    """Verifica _free_space maneja errores correctamente."""

    def test_returns_positive_for_valid_path(self):
        result = _free_space(os.path.expanduser("~"))
        self.assertGreater(result, 0)

    def test_returns_negative_for_invalid_path(self):
        result = _free_space("/nonexistent_path_xyz_12345")
        self.assertEqual(result, -1)


class TestIntegrityReport(unittest.TestCase):
    """Verifica generate_integrity_report produce un CSV válido."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="sdimport_report_")
        self._orig_db = mw.db
        self._orig_cam_db = camera_mixin_module.db
        self._orig_sess_db = sessions_mixin_module.db
        self._orig_sources_db = sources_mixin_module.db
        self._orig_proj_db = project_mixin_module.db
        self._orig_ing_db = ingestor_module.db
        self._orig_me_db = me_module.db
        self._orig_devices_db = devices_mixin_module.db
        self._orig_ingest_mixin_db = ingest_mixin_module.db
        self.db = DatabaseManager(db_path=os.path.join(self.tmp, "report.db"))
        mw.db = self.db
        camera_mixin_module.db = self.db
        sessions_mixin_module.db = self.db
        sources_mixin_module.db = self.db
        project_mixin_module.db = self.db
        ingestor_module.db = self.db
        me_module.db = self.db
        devices_mixin_module.db = self.db
        ingest_mixin_module.db = self.db

        conn = self.db.get_connection()
        conn.execute(
            "INSERT INTO projects (name, root_path) VALUES ('Test', ?)", (self.tmp,)
        )
        self.pid = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
        conn.commit()
        conn.close()

        self.sid = self.db.create_session(
            self.pid, "Report Session", "2024-06-15", "active", "/src"
        )

        conn = self.db.get_connection()
        conn.execute(
            "INSERT INTO files (session_id, source_path, dest_path, file_size, "
            "md5_hash, status, verified_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (str(self.sid), "/src/clip.mp4", "/dest/clip.mp4", 1024,
             "abc123", "copied", "2024-06-15T10:30:00")
        )
        conn.commit()
        conn.close()

    def tearDown(self):
        mw.db = self._orig_db
        camera_mixin_module.db = self._orig_cam_db
        sessions_mixin_module.db = self._orig_sess_db
        sources_mixin_module.db = self._orig_sources_db
        project_mixin_module.db = self._orig_proj_db
        ingestor_module.db = self._orig_ing_db
        me_module.db = self._orig_me_db
        devices_mixin_module.db = self._orig_devices_db
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_generates_valid_csv(self):
        out = os.path.join(self.tmp, "report.csv")
        result = generate_integrity_report(self.sid, out)
        self.assertTrue(result)
        self.assertTrue(os.path.exists(out))
        with open(out, 'r', encoding='utf-8') as f:
            content = f.read()
        self.assertIn("clip.mp4", content)
        self.assertIn("abc123", content)
        self.assertIn("Report Session", content)
        self.assertIn("Resumen", content)
        self.assertIn("Total archivos", content)
        self.assertIn("Verificados", content)

    def test_returns_false_for_invalid_session(self):
        out = os.path.join(self.tmp, "report2.csv")
        result = generate_integrity_report(99999, out)
        self.assertFalse(result)


class TestCardContentReport(unittest.TestCase):
    """Verifica generate_card_content_report (pre-dump)."""

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="sdimport_card_")
        self.source = os.path.join(self.tmp, "source")
        os.makedirs(self.source)

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_generates_csv_with_files(self):
        # Create test files
        for name in ("clip.mp4", "photo.jpg", "audio.wav"):
            with open(os.path.join(self.source, name), "wb") as f:
                f.write(b"\x00" * 1024)
        out = os.path.join(self.tmp, "card.csv")
        result = generate_card_content_report(self.source, out)
        self.assertTrue(result)
        self.assertTrue(os.path.exists(out))
        with open(out, 'r', encoding='utf-8') as f:
            content = f.read()
        self.assertIn("clip.mp4", content)
        self.assertIn("photo.jpg", content)
        self.assertIn("audio.wav", content)
        self.assertIn("Total archivos", content)
        self.assertIn("1024", content)  # file size

    def test_returns_false_for_invalid_path(self):
        result = generate_card_content_report("/nonexistent/path", "/tmp/out.csv")
        self.assertFalse(result)

    def test_skips_hidden_files(self):
        with open(os.path.join(self.source, ".hidden"), "wb") as f:
            f.write(b"data")
        with open(os.path.join(self.source, "visible.mp4"), "wb") as f:
            f.write(b"data")
        out = os.path.join(self.tmp, "card.csv")
        result = generate_card_content_report(self.source, out)
        self.assertTrue(result)
        with open(out, 'r', encoding='utf-8') as f:
            content = f.read()
        self.assertNotIn(".hidden", content)
        self.assertIn("visible.mp4", content)

    def test_includes_subdirectories(self):
        subdir = os.path.join(self.source, "sub")
        os.makedirs(subdir)
        with open(os.path.join(subdir, "nested.mov"), "wb") as f:
            f.write(b"data")
        out = os.path.join(self.tmp, "card.csv")
        result = generate_card_content_report(self.source, out)
        self.assertTrue(result)
        with open(out, 'r', encoding='utf-8') as f:
            content = f.read()
        self.assertIn("nested.mov", content)


class TestSessionCRUD(unittest.TestCase):
    """Verifica operaciones CRUD de sesiones en MainWindow."""

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="sdimport_session_")
        self._orig_db = mw.db
        self._orig_cam_db = camera_mixin_module.db
        self._orig_sess_db = sessions_mixin_module.db
        self._orig_sources_db = sources_mixin_module.db
        self._orig_proj_db = project_mixin_module.db
        self._orig_ing_db = ingestor_module.db
        self._orig_me_db = me_module.db
        self._orig_devices_db = devices_mixin_module.db
        self._orig_ingest_mixin_db = ingest_mixin_module.db
        self.db = DatabaseManager(db_path=os.path.join(self.tmp, "session.db"))
        mw.db = self.db
        camera_mixin_module.db = self.db
        sessions_mixin_module.db = self.db
        sources_mixin_module.db = self.db
        project_mixin_module.db = self.db
        ingestor_module.db = self.db
        me_module.db = self.db
        devices_mixin_module.db = self.db
        ingest_mixin_module.db = self.db

        conn = self.db.get_connection()
        conn.execute(
            "INSERT INTO projects (name, root_path) VALUES ('Test', ?)", (self.tmp,)
        )
        self.pid = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
        conn.commit()
        conn.close()

        self.window = mw.MainWindow()
        self.window.current_project_id = self.pid

    def tearDown(self):
        if hasattr(self.window, '_sync_timer') and self.window._sync_timer:
            self.window._sync_timer.stop()
        self.window.close()
        mw.db = self._orig_db
        camera_mixin_module.db = self._orig_cam_db
        sessions_mixin_module.db = self._orig_sess_db
        sources_mixin_module.db = self._orig_sources_db
        project_mixin_module.db = self._orig_proj_db
        ingestor_module.db = self._orig_ing_db
        me_module.db = self._orig_me_db
        devices_mixin_module.db = self._orig_devices_db
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_session_create_and_list(self):
        sid = self.db.create_session(self.pid, "S1", "2024-01-01", "active", "/src1")
        sessions = self.db.get_sessions(self.pid)
        self.assertEqual(len(sessions), 1)
        self.assertEqual(sessions[0]["name"], "S1")

    def test_session_update_config(self):
        sid = self.db.create_session(self.pid, "S1", "2024-01-01", "active", "/src1")
        self.db.update_session_config(sid, nombre_dispositivo="Canon R5")
        session = self.db.get_session(sid)
        self.assertEqual(session["nombre_dispositivo"], "Canon R5")

    def test_session_delete(self):
        sid = self.db.create_session(self.pid, "S1", "2024-01-01", "active", "/src1")
        self.db.delete_session(sid)
        sessions = self.db.get_sessions(self.pid)
        self.assertEqual(len(sessions), 0)

    def test_delete_session_reselects_remaining_with_own_data(self):
        """Al borrar una de dos sesiones, la que queda muestra sus propios
        datos (no los de la borrada) sin necesidad de reiniciar la app."""
        sid1 = self.db.create_session(self.pid, "S1", "2024-01-01", "active", "/src1")
        sid2 = self.db.create_session(self.pid, "S2", "2024-01-02", "active", "/src2")
        self.db.update_session_config(sid2, destination_override="X:\\customdest")

        self.window._refresh_sessions_combo()
        self.window.sessions_combo.setCurrentIndex(
            self.window.sessions_combo.findData(sid2))
        self.assertEqual(self.window.current_session_id, sid2)
        self.assertIn("/src2", self.window.session_src_label.text())

        with mock.patch("PySide6.QtWidgets.QMessageBox.question",
                        return_value=QMessageBox.Yes):
            self.window._delete_current_session()

        self.assertEqual(self.window.sessions_combo.currentData(), sid1)
        self.assertEqual(self.window.current_session_id, sid1)
        self.assertIn("/src1", self.window.session_src_label.text())
        self.assertNotIn("customdest", self.window.session_dest_label.text())

    def test_ingestor_creation_with_params(self):
        from app.core.ingestor import Ingestor
        ing = Ingestor(
            self.pid, self.tmp,
            folder_name="Footage",
            use_metadata_date=True,
            order_type="camera_first",
            duration_type=1,
            default_dispositivo="TestCam",
            delicate_mode=False,
            session_id=1,
            camera_map={"/src": "TestCam"},
        )
        self.assertEqual(ing.default_dispositivo, "TestCam")
        self.assertEqual(ing._source_dispositivo_map, {"/src": "TestCam"})
        self.assertFalse(ing.delicate_mode)
        self.assertEqual(ing.max_workers, 4)
        ing.stop()
        ing.executor.shutdown(wait=True)

    def test_ingestor_delicate_mode_limits_workers(self):
        from app.core.ingestor import Ingestor
        ing = Ingestor(self.pid, self.tmp, delicate_mode=True)
        self.assertEqual(ing.max_workers, 1)
        ing.stop()
        ing.executor.shutdown(wait=True)


class TestProjectWizard(unittest.TestCase):
    """Verifica que el wizard de proyecto (I-11) guarda todos los campos."""

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="sdimport_wizard_")
        self._orig_db = mw.db
        self._orig_cam_db = camera_mixin_module.db
        self._orig_sess_db = sessions_mixin_module.db
        self._orig_proj_db = project_mixin_module.db
        self._orig_ing_db = ingestor_module.db
        self._orig_devices_db = devices_mixin_module.db
        self._orig_ingest_mixin_db = ingest_mixin_module.db
        self.db = DatabaseManager(db_path=os.path.join(self.tmp, "wiz.db"))
        mw.db = self.db
        camera_mixin_module.db = self.db
        sessions_mixin_module.db = self.db
        project_mixin_module.db = self.db
        ingestor_module.db = self.db
        devices_mixin_module.db = self.db
        ingest_mixin_module.db = self.db

    def tearDown(self):
        mw.db = self._orig_db
        camera_mixin_module.db = self._orig_cam_db
        sessions_mixin_module.db = self._orig_sess_db
        project_mixin_module.db = self._orig_proj_db
        ingestor_module.db = self._orig_ing_db
        devices_mixin_module.db = self._orig_devices_db
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_wizard_saves_new_fields(self):
        from app.ui.project_wizard import ProjectWizard
        import app.ui.project_wizard as pw_mod
        orig_pw_db = pw_mod.db
        pw_mod.db = self.db
        result = {}
        def on_finished(pid):
            result['pid'] = pid
        try:
            wizard = ProjectWizard(on_finished)
            wizard.name_input.setText("Test Project")
            wizard.desc_input.setText("A test")
            wizard.dest_input.setText(self.tmp)
            wizard.chk_generate_proxies.setChecked(True)
            wizard.proxy_combo.setCurrentText("1080p")
            wizard.finish_wizard()
            self.assertIn('pid', result)
            conn = self.db.get_connection()
            row = conn.execute(
                "SELECT generate_proxies, proxy_resolution "
                "FROM projects WHERE id = ?", (result['pid'],)
            ).fetchone()
            conn.close()
            self.assertIsNotNone(row)
            self.assertEqual(row[0], 1)
            self.assertEqual(row[1], "1080p")
        finally:
            pw_mod.db = orig_pw_db


class TestAccentSwitch(unittest.TestCase):
    """Regresión: cambiar acento/tema no debe lanzar AttributeError en las etiquetas."""

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="sdimport_accent_")
        self._orig_db = mw.db
        self._orig_cam_db = camera_mixin_module.db
        self._orig_sess_db = sessions_mixin_module.db
        self._orig_sources_db = sources_mixin_module.db
        self._orig_proj_db = project_mixin_module.db
        self._orig_ing_db = ingestor_module.db
        self._orig_me_db = me_module.db
        self._orig_devices_db = devices_mixin_module.db
        self._orig_ingest_mixin_db = ingest_mixin_module.db
        self.db = DatabaseManager(db_path=os.path.join(self.tmp, "accent.db"))
        mw.db = self.db
        camera_mixin_module.db = self.db
        sessions_mixin_module.db = self.db
        sources_mixin_module.db = self.db
        project_mixin_module.db = self.db
        ingestor_module.db = self.db
        me_module.db = self.db
        devices_mixin_module.db = self.db
        self.window = mw.MainWindow()

    def tearDown(self):
        if hasattr(self.window, '_sync_timer') and self.window._sync_timer:
            self.window._sync_timer.stop()
        if hasattr(self.window, '_cam_timer') and self.window._cam_timer:
            self.window._cam_timer.stop()
        self.window.close()
        mw.db = self._orig_db
        camera_mixin_module.db = self._orig_cam_db
        sessions_mixin_module.db = self._orig_sess_db
        sources_mixin_module.db = self._orig_sources_db
        project_mixin_module.db = self._orig_proj_db
        ingestor_module.db = self._orig_ing_db
        me_module.db = self._orig_me_db
        devices_mixin_module.db = self._orig_devices_db
        ingest_mixin_module.db = self._orig_ingest_mixin_db
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_switch_accent_retints_app_label(self):
        from app.ui import theme

        for accent in ("green", "blue", "default"):
            self.window._switch_accent(accent)
            style = self.window.app_label.styleSheet()
            expected = theme.color("accent")
            if expected:
                self.assertIn(expected, style)

    def test_switch_theme_retints_labels(self):
        for t in ("light", "dark"):
            self.window._switch_theme(t)
            self.assertTrue(self.window.app_label.styleSheet())


class TestAutoSyncOffThread(unittest.TestCase):
    """R5: _auto_sync_check despacha off-thread vía _run_background con guards."""

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="sdimport_autosync_")
        self._orig_db = mw.db
        self._orig_cam_db = camera_mixin_module.db
        self._orig_sess_db = sessions_mixin_module.db
        self._orig_sources_db = sources_mixin_module.db
        self._orig_proj_db = project_mixin_module.db
        self._orig_ing_db = ingestor_module.db
        self._orig_me_db = me_module.db
        self._orig_devices_db = devices_mixin_module.db
        self._orig_ingest_mixin_db = ingest_mixin_module.db
        self.db = DatabaseManager(db_path=os.path.join(self.tmp, "autosync.db"))
        mw.db = self.db
        camera_mixin_module.db = self.db
        sessions_mixin_module.db = self.db
        sources_mixin_module.db = self.db
        project_mixin_module.db = self.db
        ingestor_module.db = self.db
        me_module.db = self.db
        devices_mixin_module.db = self.db
        ingest_mixin_module.db = self.db

        conn = self.db.get_connection()
        conn.execute("INSERT INTO projects (name, root_path) VALUES ('Test', ?)", (self.tmp,))
        self.pid = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
        conn.commit()
        conn.close()

        src = os.path.join(self.tmp, "src")
        os.makedirs(src, exist_ok=True)
        sid = self.db.create_session(self.pid, "S1", "2024-01-01", "active", src)
        self.db.update_session_config(sid, device_id="mtp:testdev", device_folder="DCIM")
        self.sid = sid

        self.window = mw.MainWindow()
        self.window.current_project_id = self.pid
        self.window._poll_in_progress = False
        self.window._stage_thread = None

    def tearDown(self):
        if hasattr(self.window, '_sync_timer') and self.window._sync_timer:
            self.window._sync_timer.stop()
        if hasattr(self.window, '_cam_timer') and self.window._cam_timer:
            self.window._cam_timer.stop()
        self.window.close()
        mw.db = self._orig_db
        camera_mixin_module.db = self._orig_cam_db
        sessions_mixin_module.db = self._orig_sess_db
        sources_mixin_module.db = self._orig_sources_db
        project_mixin_module.db = self._orig_proj_db
        ingestor_module.db = self._orig_ing_db
        me_module.db = self._orig_me_db
        devices_mixin_module.db = self._orig_devices_db
        ingest_mixin_module.db = self._orig_ingest_mixin_db
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_auto_sync_dispatches_via_run_background(self):
        with mock.patch.object(self.window, "_run_background") as mock_run_bg, \
             mock.patch.object(self.window, "_process_device_poll") as mock_process:
            self.window._poll_in_progress = False
            self.window._stage_thread = None
            self.window._auto_sync_check()
            self.assertTrue(mock_run_bg.called, "_run_background should be called")
            mock_process.assert_not_called()
            args, _ = mock_run_bg.call_args
            fn = args[0]
            callback = args[1]
            self.assertTrue(callable(fn))
            self.assertTrue(callable(callback))

    def test_auto_sync_guarded_by_poll_in_progress(self):
        with mock.patch.object(self.window, "_run_background") as mock_run_bg:
            self.window._poll_in_progress = True
            self.window._auto_sync_check()
            mock_run_bg.assert_not_called()

    def test_auto_sync_runs_probe_off_thread(self):
        import threading
        from app.core.mtp import WpdBackend
        from app.core.ftp import FtpBackend
        with mock.patch.object(WpdBackend, "list_devices", return_value=[]):
            with mock.patch.object(FtpBackend, "is_reachable", return_value=False):
                captured_ident = {}
                def fake_run_background(fn, on_finished, *a, **k):
                    # Execute fn in a separate thread to simulate _run_background
                    def runner():
                        captured_ident['worker'] = threading.get_ident()
                        class DummySignal:
                            def emit(self, *args): pass
                        result = None
                        try:
                            result = fn(DummySignal())
                        except Exception:
                            pass
                        on_finished(True, result)
                    t = threading.Thread(target=runner)
                    t.start()
                    t.join()
                with mock.patch.object(self.window, "_run_background", side_effect=fake_run_background):
                    self.window._poll_in_progress = False
                    self.window._stage_thread = None
                    self.window._auto_sync_check()
                    main_ident = threading.get_ident()
                    self.assertIn('worker', captured_ident)
                    self.assertNotEqual(captured_ident['worker'], main_ident)


class TestCleanupMenu(unittest.TestCase):
    """Verifica CHG-1/CHG-2: borrar dispositivos guardados y cámaras conocidas."""

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="sdimport_cleanup_")
        self._orig_db = mw.db
        self._orig_cam_db = camera_mixin_module.db
        self._orig_sess_db = sessions_mixin_module.db
        self._orig_sources_db = sources_mixin_module.db
        self._orig_proj_db = project_mixin_module.db
        self._orig_ing_db = ingestor_module.db
        self._orig_me_db = me_module.db
        self._orig_devices_db = devices_mixin_module.db
        self._orig_ingest_mixin_db = ingest_mixin_module.db
        self.db = DatabaseManager(db_path=os.path.join(self.tmp, "session.db"))
        mw.db = self.db
        camera_mixin_module.db = self.db
        sessions_mixin_module.db = self.db
        sources_mixin_module.db = self.db
        project_mixin_module.db = self.db
        ingestor_module.db = self.db
        me_module.db = self.db
        devices_mixin_module.db = self.db
        ingest_mixin_module.db = self.db

        conn = self.db.get_connection()
        conn.execute(
            "INSERT INTO projects (name, root_path) VALUES ('Test', ?)", (self.tmp,)
        )
        self.pid = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
        conn.commit()
        conn.close()

        self.window = mw.MainWindow()
        self.window.current_project_id = self.pid

    def tearDown(self):
        if hasattr(self.window, '_sync_timer') and self.window._sync_timer:
            self.window._sync_timer.stop()
        self.window.close()
        mw.db = self._orig_db
        camera_mixin_module.db = self._orig_cam_db
        sessions_mixin_module.db = self._orig_sess_db
        sources_mixin_module.db = self._orig_sources_db
        project_mixin_module.db = self._orig_proj_db
        ingestor_module.db = self._orig_ing_db
        me_module.db = self._orig_me_db
        devices_mixin_module.db = self._orig_devices_db
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_delete_all_saved_devices(self):
        """CHG-1: borra dispositivos, sd_cards, remitentes y perfiles FTP."""
        self.db.add_inbox_sender("Alice")
        self.db.save_dispositivo("ABC123", "Sony A7")
        self.db.save_dispositivo_config("d1", "Canon")
        self.db.add_ftp_profile("FTP1", "192.168.1.1")
        with mock.patch.object(QMessageBox, "question", return_value=QMessageBox.Yes):
            self.window._delete_all_saved_devices()
        conn = self.db.get_connection()
        n_senders = conn.execute("SELECT COUNT(*) FROM inbox_senders").fetchone()[0]
        n_cards = conn.execute("SELECT COUNT(*) FROM sd_cards").fetchone()[0]
        n_dev = conn.execute("SELECT COUNT(*) FROM device_settings").fetchone()[0]
        n_ftp = conn.execute("SELECT COUNT(*) FROM ftp_profiles").fetchone()[0]
        conn.close()
        self.assertEqual(n_senders, 0)
        self.assertEqual(n_cards, 0)
        self.assertEqual(n_dev, 0)
        self.assertEqual(n_ftp, 0)

    def test_delete_all_saved_devices_cancelled(self):
        """CHG-1: si el usuario cancela, no se borra nada."""
        self.db.add_inbox_sender("Alice")
        with mock.patch.object(QMessageBox, "question", return_value=QMessageBox.No):
            self.window._delete_all_saved_devices()
        self.assertEqual(len(self.db.list_inbox_senders()), 1)

    def test_delete_all_known_cameras(self):
        """CHG-2: limpia la cache de metadatos y los nombres conocidos."""
        self.db.save_dispositivo("ABC123", "Sony A7")
        with mock.patch.object(QMessageBox, "question", return_value=QMessageBox.Yes):
            with mock.patch.object(me_module.metadata_engine, "clear_cache") as mock_clear:
                self.window._delete_all_known_cameras()
        mock_clear.assert_called_once()
        self.assertIsNone(self.db.get_dispositivo_for_card("ABC123"))

    def test_cleanup_menu_actions_exist(self):
        """CHG-1/CHG-2: las acciones del menú Herramientas existen."""
        text_dev = self.window.tr("Borrar &dispositivos guardados…")
        text_cam = self.window.tr("Borrar &nombres de dispositivos…")
        from PySide6.QtGui import QAction
        actions = self.window.findChildren(QAction)
        labels = {a.text() for a in actions}
        self.assertIn(text_dev, labels)
        self.assertIn(text_cam, labels)


if __name__ == "__main__":
    unittest.main()
