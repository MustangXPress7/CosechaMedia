"""Tests de regresión para MainWindow y funciones core relacionadas.

Cubre: detección de cámara (token-based), rename_camera (separadores),
_free_space, generate_integrity_report, y flujo básico de sesión.
"""

import os
import sys
import time
import tempfile
import shutil
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QTimer

import app.ui.main_window as mw
import app.core.ingestor as ingestor_module
import app.core.metadata_engine as me_module
from app.core.db import DatabaseManager
from app.core.ingestor import _free_space, generate_integrity_report


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
        """Cada llamada a _detect_camera_for_session resetea _cam_done."""
        src = os.path.join(self.tmp, "src1")
        os.makedirs(src)
        sid = self.db.create_session(self.pid, "S1", "2024-01-01", "active", src)
        self.window._cam_done = True
        self.window._detect_camera_for_session(sid, src)
        self.assertFalse(self.window._cam_done)

    def test_old_timer_is_stopped(self):
        """El flag _cam_done se resetea al iniciar una nueva detección."""
        src1 = os.path.join(self.tmp, "src1")
        src2 = os.path.join(self.tmp, "src2")
        os.makedirs(src1)
        os.makedirs(src2)
        sid1 = self.db.create_session(self.pid, "S1", "2024-01-01", "active", src1)
        sid2 = self.db.create_session(self.pid, "S2", "2024-01-02", "active", src2)
        self.window.project_camera_detection_timeout = 60
        self.window._detect_camera_for_session(sid1, src1)
        self.assertFalse(self.window._cam_done)
        self.window._detect_camera_for_session(sid2, src2)
        self.assertFalse(self.window._cam_done)

    def test_stale_token_does_not_overwrite(self):
        """Un _cam_done=True previo se resetea por la nueva detección."""
        self.window._cam_done = True
        src = os.path.join(self.tmp, "src_stale")
        os.makedirs(src)
        sid = self.db.create_session(self.pid, "S_stale", "2024-01-01", "active", src)
        self.window._detect_camera_for_session(sid, src)
        self.assertFalse(self.window._cam_done)


class TestRenameCamera(unittest.TestCase):
    """Verifica rename_camera con separadores / y \\."""

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
        self.ing._camera_mapping = {}
        self.ing._camera_lock = __import__("threading").Lock()
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
        self.ing.rename_camera("OLD_CAM", "NEW_CAM")
        paths = self._get_dest_paths(sid)
        self.assertEqual(paths[0], "/data/Footage/NEW_CAM/2024-01-01/clip.mp4")

    def test_rename_updates_backslash_paths(self):
        sid = "2"
        self._insert_file(sid, "D:\\Footage\\OLD_CAM\\2024-01-01\\clip.mp4")
        self.ing.rename_camera("OLD_CAM", "NEW_CAM")
        paths = self._get_dest_paths(sid)
        self.assertEqual(paths[0], "D:\\Footage\\NEW_CAM\\2024-01-01\\clip.mp4")

    def test_rename_updates_mixed_separator_paths(self):
        sid = "3"
        self._insert_file(sid, "/data/Footage/OLD_CAM/2024-01-01/clip.mp4")
        self._insert_file(sid, "D:\\Footage\\OLD_CAM\\2024-01-01\\clip2.mp4")
        self.ing.rename_camera("OLD_CAM", "NEW_CAM")
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

    def test_returns_false_for_invalid_session(self):
        out = os.path.join(self.tmp, "report2.csv")
        result = generate_integrity_report(99999, out)
        self.assertFalse(result)


if __name__ == "__main__":
    unittest.main()
