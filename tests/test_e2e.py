"""Prueba end-to-end offscreen: crea proyecto, sesión y orígenes, ejecuta
start_ingest y verifica que los archivos llegan a los destinos de volcado."""

import os
import sys
import time
import tempfile
import shutil
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

import app.ui.main_window as mw
import app.core.ingestor as ingestor_module
import app.core.metadata_engine as me_module
from app.core.db import DatabaseManager


class TestEndToEndIngest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="sdimport_e2e_")
        self.src = os.path.join(self.tmp, "src")
        self.dest = os.path.join(self.tmp, "dest")
        self.disk_a = os.path.join(self.tmp, "disk_a")
        self.disk_b = os.path.join(self.tmp, "disk_b")
        for d in (self.src, self.dest, self.disk_a, self.disk_b):
            os.makedirs(d)

        with open(os.path.join(self.src, "clip1.mp4"), "wb") as f:
            f.write(os.urandom(2048))
        with open(os.path.join(self.src, "clip2.MOV"), "wb") as f:
            f.write(os.urandom(4096))
        with open(os.path.join(self.src, "notes.txt"), "w") as f:
            f.write("hoja de rodaje")

        self._orig_db = mw.db
        self._orig_ing_db = ingestor_module.db
        self._orig_me_db = me_module.db
        self._orig_notif = mw.NotificationManager
        self.db = DatabaseManager(db_path=os.path.join(self.tmp, "e2e.db"))
        mw.db = self.db
        ingestor_module.db = self.db
        me_module.db = self.db

        class StubNotif:
            def notify_ingest_complete(self, stats):
                pass

            def notify_ingest_stopped(self):
                pass

            def notify_ingest_failed(self, stats=None):
                pass

        mw.NotificationManager = StubNotif

        conn = mw.db.get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO projects (name, root_path) VALUES ('E2E', ?)", (self.dest,)
        )
        self.pid = cursor.lastrowid
        conn.commit()
        conn.close()
        self.sid = mw.db.create_session(
            self.pid, "Sesión E2E", "2024-01-02", "active", self.src
        )
        mw.db.add_dump_location(self.pid, self.disk_a)
        mw.db.add_dump_location(self.pid, self.disk_b)

        self.window = mw.MainWindow()
        self.window.current_project_id = self.pid
        self.window.dest_root = self.dest
        self.window._source_paths = [self.src]
        self.window.project_date = self.window.project_date  # hoy

    def tearDown(self):
        if hasattr(self.window, '_sync_timer') and self.window._sync_timer:
            self.window._sync_timer.stop()
        if hasattr(self.window, '_cam_timer') and self.window._cam_timer:
            self.window._cam_timer.stop()
        self.window.close()
        mw.db = self._orig_db
        ingestor_module.db = self._orig_ing_db
        me_module.db = self._orig_me_db
        mw.NotificationManager = self._orig_notif
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _wait_done(self, timeout=30):
        deadline = time.time() + timeout
        while time.time() < deadline:
            self.app.processEvents()
            if self.window.btn_start.text() == "Iniciar Ingesta":
                return True
            time.sleep(0.05)
        return False

    def test_ingest_to_dump_targets(self):
        self.window.start_ingest()
        done = self._wait_done()
        self.assertTrue(done, "La ingesta no terminó a tiempo")

        # Los clips deben estar bajo disk_a/disk_b en Footage/<camara>/<fecha>
        date_dir = self.window.project_date.toString("yyyy-MM-dd")
        found = []
        for disk in (self.disk_a, self.disk_b):
            base = os.path.join(disk, "Footage", "Unknown_Camera", date_dir)
            if os.path.isdir(base):
                found.extend(os.listdir(base))
        self.assertEqual(sorted(found), ["clip1.mp4", "clip2.MOV"])

        # El archivo de referencia debe estar en _reference del destino maestro
        ref = os.path.join(self.dest, "_reference", "notes.txt")
        self.assertTrue(os.path.exists(ref), "El archivo de referencia debe copiarse")

        # Filas en la BD
        conn = mw.db.get_connection()
        rows = conn.execute("SELECT count(*) FROM files WHERE session_id = ?", (str(self.sid),)).fetchone()[0]
        conn.close()
        self.assertEqual(rows, 3)

        # La sesión debe marcarse como completada
        sess = mw.db.get_session(self.sid)
        self.assertEqual(sess["status"], "completed")


if __name__ == "__main__":
    unittest.main()
