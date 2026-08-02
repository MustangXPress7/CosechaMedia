import os
import tempfile
import unittest
import shutil

from app.core.db import DatabaseManager


class TestDatabaseManager(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="sdimport_db_")
        self.db = DatabaseManager(db_path=os.path.join(self.tmp, "test.db"))

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_default_project_created(self):
        conn = self.db.get_connection()
        count = conn.execute("SELECT COUNT(*) FROM projects").fetchone()[0]
        conn.close()
        self.assertGreaterEqual(count, 1)

    def test_session_crud(self):
        conn = self.db.get_connection()
        pid = conn.execute("INSERT INTO projects (name) VALUES ('P')").lastrowid
        conn.commit()
        conn.close()

        sid = self.db.create_session(pid, "Sesión 1", "2024-01-02", "pending", "/src")
        sess = self.db.get_session(sid)
        self.assertEqual(sess["name"], "Sesión 1")
        self.assertEqual(sess["source_path"], "/src")

        self.db.update_session_config(sid, status="completed", camera_name="Cámara A")
        sess = self.db.get_session(sid)
        self.assertEqual(sess["status"], "completed")
        self.assertEqual(sess["camera_name"], "Cámara A")

        self.db.delete_session(sid)
        self.assertIsNone(self.db.get_session(sid))

    def test_dump_locations_roundtrip(self):
        conn = self.db.get_connection()
        pid = conn.execute("INSERT INTO projects (name) VALUES ('P')").lastrowid
        conn.commit()
        conn.close()

        a = self.db.add_dump_location(pid, "C:/discos/disco1")
        b = self.db.add_dump_location(pid, "C:/discos/disco2", label="Backup")
        locs = self.db.dump_locations(pid)
        self.assertEqual(
            [l["path"] for l in locs],
            [os.path.abspath("C:/discos/disco1"), os.path.abspath("C:/discos/disco2")],
        )
        self.assertTrue(locs[1]["include_date"])
        self.assertEqual(locs[1]["label"], "Backup")

        self.db.reorder_dump_locations(pid, [b, a])
        locs = self.db.dump_locations(pid)
        self.assertEqual(
            [l["path"] for l in locs],
            [os.path.abspath("C:/discos/disco2"), os.path.abspath("C:/discos/disco1")],
        )

        self.db.delete_dump_location(a)
        locs = self.db.dump_locations(pid)
        self.assertEqual([l["path"] for l in locs], [os.path.abspath("C:/discos/disco2")])

    def test_recent_paths_limited(self):
        for i in range(15):
            self.db.save_recent_path(f"C:/src/{i}", "source")
        paths = self.db.get_recent_paths("source", limit=10)
        self.assertEqual(len(paths), 10)
        self.assertEqual(paths[0], "C:/src/14")


if __name__ == "__main__":
    unittest.main()
