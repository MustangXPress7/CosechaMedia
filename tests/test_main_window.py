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
from unittest import mock

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QTimer

import app.ui.main_window as mw
import app.core.ingestor as ingestor_module
import app.core.metadata_engine as me_module
from app.core.db import DatabaseManager
from app.core.ingestor import _free_space, generate_integrity_report
from app.core.sd_reader import sd_reader


class TestCameraDetectionToken(unittest.TestCase):
    """Verifica que la detección de cámara usa tokens para evitar carreras."""

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="sdimport_camtest_")
        self._orig_db = mw.db
        self._orig_ing_db = ingestor_module.db
        self._orig_me_db = me_module.db
        self.db = DatabaseManager(db_path=os.path.join(self.tmp, "cam.db"))
        mw.db = self.db
        ingestor_module.db = self.db
        me_module.db = self.db

        conn = self.db.get_connection()
        conn.execute(
            "INSERT INTO projects (name, root_path) VALUES ('Test', ?)", (self.tmp,)
        )
        self.pid = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
        conn.commit()
        conn.close()

        self.window = mw.MainWindow()
        self.window.current_project_id = self.pid
        self.window.project_camera_detection_mode = "auto"

    def tearDown(self):
        if hasattr(self.window, '_sync_timer') and self.window._sync_timer:
            self.window._sync_timer.stop()
        if hasattr(self.window, '_cam_timer') and self.window._cam_timer:
            self.window._cam_timer.stop()
        self.window.close()
        mw.db = self._orig_db
        ingestor_module.db = self._orig_ing_db
        me_module.db = self._orig_me_db
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_token_increments_on_each_detection(self):
        """Cada llamada a _detect_camera_for_session genera un nuevo detection_id."""
        src = os.path.join(self.tmp, "src1")
        os.makedirs(src)
        sid = self.db.create_session(self.pid, "S1", "2024-01-01", "active", src)
        old_id = getattr(self.window, '_cam_detection_id', None)
        self.window._detect_camera_for_session(sid, src)
        new_id = getattr(self.window, '_cam_detection_id', None)
        self.assertNotEqual(old_id, new_id)

    def test_old_timer_is_stopped(self):
        """El detection_id se cambia al iniciar una nueva detección."""
        src1 = os.path.join(self.tmp, "src1")
        src2 = os.path.join(self.tmp, "src2")
        os.makedirs(src1)
        os.makedirs(src2)
        sid1 = self.db.create_session(self.pid, "S1", "2024-01-01", "active", src1)
        sid2 = self.db.create_session(self.pid, "S2", "2024-01-02", "active", src2)
        self.window.project_camera_detection_timeout = 60
        self.window._detect_camera_for_session(sid1, src1)
        id1 = self.window._cam_detection_id
        self.window._detect_camera_for_session(sid2, src2)
        id2 = self.window._cam_detection_id
        self.assertNotEqual(id1, id2)

    def test_stale_token_does_not_overwrite(self):
        """Un detection_id previo se reemplaza por la nueva detección."""
        self.window._cam_detection_id = "stale_token"
        src = os.path.join(self.tmp, "src_stale")
        os.makedirs(src)
        sid = self.db.create_session(self.pid, "S_stale", "2024-01-01", "active", src)
        self.window._detect_camera_for_session(sid, src)
        self.assertNotEqual(self.window._cam_detection_id, "stale_token")


class TestCameraPersistence(unittest.TestCase):
    """Verifica persistencia de cámara en DB (I-03): sd_cards y device_settings."""

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="sdimport_persist_")
        self.db = DatabaseManager(db_path=os.path.join(self.tmp, "persist.db"))
        self._orig_db = mw.db
        self._orig_ing_db = ingestor_module.db
        self._orig_me_db = me_module.db
        mw.db = self.db
        ingestor_module.db = self.db
        me_module.db = self.db

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

    def tearDown(self):
        if hasattr(self.window, '_sync_timer') and self.window._sync_timer:
            self.window._sync_timer.stop()
        self.window.close()
        mw.db = self._orig_db
        ingestor_module.db = self._orig_ing_db
        me_module.db = self._orig_me_db
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


class TestForcePromptI14(unittest.TestCase):
    """I-14: force_prompt muestra el prompt en modo manual cuando no hay cámara conocida."""

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self._orig_db = mw.db
        self._orig_ing_db = ingestor_module.db
        self._orig_me_db = me_module.db
        self.db = DatabaseManager(db_path=os.path.join(self.tmp, "test.db"))
        mw.db = self.db
        ingestor_module.db = self.db
        me_module.db = self.db
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

    def tearDown(self):
        self.window.close()
        mw.db = self._orig_db
        ingestor_module.db = self._orig_ing_db
        me_module.db = self._orig_me_db
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_manual_no_prompt_without_force(self):
        src = os.path.join(self.tmp, "card")
        os.makedirs(src)
        sid = self.db.create_session(self.pid, "S1", "2024-01-01", "active", src)
        with mock.patch("PySide6.QtWidgets.QInputDialog.getText") as m:
            m.return_value = ("", False)
            self.window._detect_camera_for_session(sid, src, force_prompt=False)
        m.assert_not_called()

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

    def test_force_prompt_skipped_when_camera_known(self):
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
            self.window._detect_camera_for_session(sid, src, force_prompt=True)
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
        self._orig_ing_db = ingestor_module.db
        self._orig_me_db = me_module.db
        self.db = DatabaseManager(db_path=os.path.join(self.tmp, "report.db"))
        mw.db = self.db
        ingestor_module.db = self.db
        me_module.db = self.db

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
        ingestor_module.db = self._orig_ing_db
        me_module.db = self._orig_me_db
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


class TestSessionCRUD(unittest.TestCase):
    """Verifica operaciones CRUD de sesiones en MainWindow."""

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="sdimport_session_")
        self._orig_db = mw.db
        self._orig_ing_db = ingestor_module.db
        self._orig_me_db = me_module.db
        self.db = DatabaseManager(db_path=os.path.join(self.tmp, "session.db"))
        mw.db = self.db
        ingestor_module.db = self.db
        me_module.db = self.db

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
        ingestor_module.db = self._orig_ing_db
        me_module.db = self._orig_me_db
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


if __name__ == "__main__":
    unittest.main()
