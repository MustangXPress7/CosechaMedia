import os
import json
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

    def test_content_filter_roundtrip(self):
        conn = self.db.get_connection()
        pid = conn.execute("INSERT INTO projects (name) VALUES ('P')").lastrowid
        conn.commit()
        conn.close()

        sid = self.db.create_session(pid, "S", source_path="/src")
        self.assertIsNone(self.db.get_session(sid)["content_filter"])

        filt = {"dates": ["2025-05-25", "2025-05-26"], "include_nodate": True}
        self.db.update_session_config(sid, content_filter=json.dumps(filt))
        sess = self.db.get_session(sid)
        self.assertEqual(json.loads(sess["content_filter"]), filt)

        sessions = self.db.get_sessions(pid)
        self.assertEqual(json.loads(sessions[0]["content_filter"]), filt)

        self.db.update_session_config(sid, content_filter=None)
        self.assertIsNone(self.db.get_session(sid)["content_filter"])

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

    def test_device_helpers(self):
        conn = self.db.get_connection()
        pid = conn.execute("INSERT INTO projects (name) VALUES ('P')").lastrowid
        conn.commit()
        conn.close()

        sid1 = self.db.create_session(pid, "D1", source_path="/cache/a")
        self.db.update_session_config(sid1, device_id="DEV1", device_folder="DCIM")
        sid2 = self.db.create_session(pid, "D1b", source_path="/cache/b")
        self.db.update_session_config(sid2, device_id="DEV1", device_folder="DCIM")
        sid3 = self.db.create_session(pid, "D2", source_path="/cache/c")
        self.db.update_session_config(sid3, device_id="DEV2", device_folder="")

        devices = self.db.get_devices()
        by_id = {(d["device_id"], d["device_folder"]): d["session_count"] for d in devices}
        self.assertEqual(by_id[("DEV1", "DCIM")], 2)
        self.assertEqual(by_id[("DEV2", "")], 1)

        dev1 = self.db.get_sessions_by_device("DEV1")
        self.assertEqual([s["id"] for s in dev1], [sid1, sid2])
        self.assertEqual(dev1[0]["device_folder"], "DCIM")
        self.assertEqual(dev1[0]["source_path"], "/cache/a")

    def test_delete_device_cascades(self):
        conn = self.db.get_connection()
        pid = conn.execute("INSERT INTO projects (name) VALUES ('P')").lastrowid
        conn.commit()
        conn.close()

        sid1 = self.db.create_session(pid, "D1", source_path="/cache/a")
        self.db.update_session_config(sid1, device_id="DEV1", device_folder="DCIM")
        conn = self.db.get_connection()
        conn.execute("INSERT INTO files (session_id, source_path, dest_path, status) VALUES (?, ?, ?, ?)",
                     (sid1, "/cache/a/x.jpg", "/out/x.jpg", "ok"))
        conn.commit()
        conn.close()

        self.assertEqual(len(self.db.get_sessions_by_device("DEV1")), 1)
        self.db.delete_device("DEV1")
        self.assertEqual(self.db.get_sessions_by_device("DEV1"), [])
        self.assertIsNone(self.db.get_session(sid1))
        conn = self.db.get_connection()
        files = conn.execute("SELECT COUNT(*) FROM files WHERE session_id = ?", (sid1,)).fetchone()[0]
        conn.close()
        self.assertEqual(files, 0)

        other = self.db.get_devices()
        self.assertTrue(all(d["device_id"] != "DEV1" for d in other))


if __name__ == "__main__":
    unittest.main()
