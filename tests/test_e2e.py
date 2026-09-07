"""Prueba end-to-end offscreen: crea proyecto, sesión y orígenes, ejecuta
start_ingest y verifica que los archivos llegan a los destinos de volcado."""

import os
import sys
import time
import tempfile
import shutil
import unittest
from datetime import datetime, timedelta

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

import app.ui.main_window as mw
import app.ui.mixins.camera_mixin as camera_mixin_module
import app.ui.mixins.sessions_mixin as sessions_mixin_module
import app.ui.mixins.sources_mixin as sources_mixin_module
import app.ui.mixins.project_mixin as project_mixin_module
import app.ui.mixins.ingest_mixin as ingest_mixin_module
import app.core.ingestor as ingestor_module
import app.core.metadata_engine as me_module
import app.ui.mixins.devices_mixin as devices_mixin_module
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
        self._orig_cam_db = camera_mixin_module.db
        self._orig_sess_db = sessions_mixin_module.db
        self._orig_sources_db = sources_mixin_module.db
        self._orig_proj_db = project_mixin_module.db
        self._orig_ing_db = ingestor_module.db
        self._orig_me_db = me_module.db
        self._orig_devices_db = devices_mixin_module.db
        self._orig_ingest_mixin_db = ingest_mixin_module.db
        self._orig_notif = mw.NotificationManager
        self._orig_data_dir = ingestor_module.data_dir
        self.db = DatabaseManager(db_path=os.path.join(self.tmp, "e2e.db"))
        mw.db = self.db
        camera_mixin_module.db = self.db
        sessions_mixin_module.db = self.db
        sources_mixin_module.db = self.db
        project_mixin_module.db = self.db
        ingestor_module.db = self.db
        me_module.db = self.db
        devices_mixin_module.db = self.db
        ingest_mixin_module.db = self.db
        ingestor_module.data_dir = lambda: os.path.join(self.tmp, "resume")

        os.makedirs(os.path.join(self.tmp, "resume"), exist_ok=True)

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
        camera_mixin_module.db = self._orig_cam_db
        sessions_mixin_module.db = self._orig_sess_db
        sources_mixin_module.db = self._orig_sources_db
        project_mixin_module.db = self._orig_proj_db
        ingestor_module.db = self._orig_ing_db
        me_module.db = self._orig_me_db
        devices_mixin_module.db = self._orig_devices_db
        ingest_mixin_module.db = self._orig_ingest_mixin_db
        mw.NotificationManager = self._orig_notif
        ingestor_module.data_dir = self._orig_data_dir
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
            base = os.path.join(disk, "Footage", "SinClasificar", date_dir)
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

    def test_redump_after_master_delete(self):
        """Si el usuario borra clips de la carpeta maestra, una nueva ingesta
        los vuelve a volcar (no debe darlos por completados). Además no debe
        quedar ningún .json de reanudación junto al destino."""
        self.window.start_ingest()
        done = self._wait_done()
        self.assertTrue(done, "La primera ingesta no terminó a tiempo")
        date_dir = self.window.project_date.toString("yyyy-MM-dd")

        def clips():
            found = []
            for disk in (self.disk_a, self.disk_b):
                base = os.path.join(disk, "Footage", "SinClasificar", date_dir)
                if os.path.isdir(base):
                    found.extend(os.listdir(base))
            return sorted(found)

        self.assertEqual(clips(), ["clip1.mp4", "clip2.MOV"])
        for c in clips():
            os.remove(os.path.join(
                self.disk_a, "Footage", "SinClasificar", date_dir, c))

        # Re-ingesta tras borrar de la carpeta maestra
        self.window.start_ingest()
        done = self._wait_done()
        self.assertTrue(done, "La segunda ingesta no terminó a tiempo")
        self.assertEqual(clips(), ["clip1.mp4", "clip2.MOV"],
                         "Los clips borrados de la carpeta maestra deben re-volcarse")

        # Sin residuo .json molesto en la raíz del destino
        residue = [f for f in os.listdir(self.dest)
                   if f.startswith(".sdimport_session")]
        self.assertEqual(residue, [])

    def test_redump_in_window_mode_when_older_than_window(self):
        """«Últimos x días»: un clip con volcado previo cuya copia se borra
        del archivo debe re-volearse aunque su fecha haya quedado fuera de la
        ventana recalculada (la ventana se ancla al último volcado y deriva
        hacia delante). El filtro solo decide sobre contenido NUEVO."""
        today = datetime.now().date()
        housed = today - timedelta(days=14)
        for name in ("clip1.mp4", "clip2.MOV"):
            t = time.mktime(housed.timetuple())
            os.utime(os.path.join(self.src, name), (t, t))

        mw.db.update_session_config(
            self.sid, content_mode="window",
            content_filter='{"window_days": 1}')

        # Volcado previo de la sesión hace 16 días: ancla la 1.ª ventana para
        # que los clips de hace 14 días sí se vuelquen en la primera pasada.
        conn = mw.db.get_connection()
        conn.execute(
            "INSERT INTO files (session_id, source_path, dest_path, file_size,"
            " md5_hash, status, verified_at) VALUES (?, 'prev.mp4', 'prev.mp4',"
            " 1, 'x', 'completed', ?)",
            (str(self.sid), (today - timedelta(days=16)).strftime("%Y-%m-%d 12:00:00")))
        conn.commit()
        conn.close()

        def clips():
            found = []
            for disk in (self.disk_a, self.disk_b):
                base = os.path.join(disk, "Footage", "SinClasificar")
                if os.path.isdir(base):
                    for root, _dirs, files in os.walk(base):
                        found.extend(files)
            return sorted(found)

        self.window.start_ingest()
        self.assertTrue(self._wait_done(), "La primera ingesta no terminó a tiempo")
        self.assertEqual(clips(), ["clip1.mp4", "clip2.MOV"],
                         "Los clips dentro de la ventana anclada deben volcarse")

        for disk in (self.disk_a, self.disk_b):
            base = os.path.join(disk, "Footage", "SinClasificar")
            if os.path.isdir(base):
                for root, _dirs, files in os.walk(base):
                    for f in files:
                        os.remove(os.path.join(root, f))

        self.window.start_ingest()
        self.assertTrue(self._wait_done(), "La segunda ingesta no terminó a tiempo")
        self.assertEqual(clips(), ["clip1.mp4", "clip2.MOV"],
                         "Los clips con volcado previo deben re-volearse aunque "
                         "queden fuera de la ventana recalculada")


if __name__ == "__main__":
    unittest.main()
