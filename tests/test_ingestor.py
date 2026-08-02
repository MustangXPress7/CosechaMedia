import os
import shutil
import tempfile
import unittest

import app.core.ingestor as ingestor_module
from app.core.db import DatabaseManager
from app.core.ingestor import Ingestor, DumpTarget


class FakeMeta:
    def get_file_type_info(self, path):
        return {"type": "video", "category": "footage"}

    def get_video_metadata(self, path):
        return {
            "camera_model": "TestCam",
            "camera_make": "Test",
            "creation_date": "2024-01-02T10:00:00.000000Z",
            "duration": 1.0,
            "is_video": True,
        }


class TestIngestor(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="sdimport_ing_")
        self.src_dir = os.path.join(self.tmp, "src")
        self.dst_dir = os.path.join(self.tmp, "dst")
        os.makedirs(self.src_dir)
        os.makedirs(self.dst_dir)

        self.db = DatabaseManager(db_path=os.path.join(self.tmp, "ingest.db"))
        self._orig_db = ingestor_module.db
        self._orig_meta = ingestor_module.metadata_engine
        self._orig_calc = ingestor_module.calculate_md5
        ingestor_module.db = self.db
        ingestor_module.metadata_engine = FakeMeta()

        self.ing = Ingestor(1, self.dst_dir, session_id=1)

    def tearDown(self):
        self.ing.stop()
        self.ing.executor.shutdown(wait=True)
        ingestor_module.db = self._orig_db
        ingestor_module.metadata_engine = self._orig_meta
        ingestor_module.calculate_md5 = self._orig_calc
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _make_source(self, name="clip.mp4", size=2048, content=None):
        path = os.path.join(self.src_dir, name)
        if content is None:
            with open(path, "wb") as f:
                f.write(os.urandom(size))
        else:
            with open(path, "wb") as f:
                f.write(content)
        return path

    def test_verified_copy_success(self):
        src = self._make_source()
        self.ing._process_single_file(src, {"type": "video", "category": "footage"})

        stats = self.ing.get_stats()
        self.assertEqual(stats["processed"], 1)
        self.assertEqual(stats["errors"], 0)

        dest = os.path.join(self.dst_dir, "Footage", "TestCam", "2024-01-02", "clip.mp4")
        self.assertTrue(os.path.exists(dest), "El destino debe existir tras una copia verificada")

        conn = self.db.get_connection()
        row = conn.execute("SELECT dest_path, md5_hash, status FROM files WHERE session_id = '1'").fetchone()
        conn.close()
        self.assertIsNotNone(row)
        self.assertEqual(row["dest_path"], dest)
        self.assertEqual(row["md5_hash"], self._orig_calc(dest))
        self.assertEqual(row["status"], "completed")

    def test_mismatch_detected_and_dest_removed(self):
        src = self._make_source()
        ingestor_module.calculate_md5 = lambda p: "0" * 32  # dest nunca coincidirá
        self.ing._process_single_file(src, {"type": "video", "category": "footage"})

        stats = self.ing.get_stats()
        self.assertEqual(stats["processed"], 0)
        self.assertEqual(stats["errors"], 1)
        dest = os.path.join(self.dst_dir, "Footage", "TestCam", "2024-01-02", "clip.mp4")
        self.assertFalse(os.path.exists(dest), "El destino corrupto debe eliminarse")

    def test_copy_error_removes_partial(self):
        src = self._make_source()
        dest = os.path.join(self.dst_dir, "partial.bin")
        self.ing._copy_verified(src, dest)
        self.assertTrue(os.path.exists(dest))

        ingestor_module.calculate_md5 = lambda p: "1" * 32
        self.ing._copy_verified(src, dest)
        self.assertFalse(os.path.exists(dest), "El destino con hash erróneo debe eliminarse")

    def test_reference_unique_names(self):
        os.makedirs(os.path.join(self.src_dir, "a"))
        os.makedirs(os.path.join(self.src_dir, "b"))
        f1 = os.path.join(self.src_dir, "a", "notes.txt")
        f2 = os.path.join(self.src_dir, "b", "notes.txt")
        with open(f1, "w") as f:
            f.write("one")
        with open(f2, "w") as f:
            f.write("two")

        self.ing._handle_reference_file(f1)
        self.ing._handle_reference_file(f2)

        ref_dir = os.path.join(self.dst_dir, "_reference")
        names = set(os.listdir(ref_dir))
        self.assertEqual(names, {"notes.txt", "notes (1).txt"})

    def test_dump_target_full(self):
        target = DumpTarget(1, self.dst_dir, True, True)
        dir_full = target.next_available_dir("Cam", "2024-01-02", "Footage", 10)
        self.assertTrue(os.path.isdir(dir_full))

        orig_free = ingestor_module._free_space
        ingestor_module._free_space = lambda p: 5  # menos que el archivo + margen
        try:
            self.assertIsNone(
                target.next_available_dir("Cam", "2024-01-02", "Footage", 1024 * 1024)
            )
        finally:
            ingestor_module._free_space = orig_free


class TestUtils(unittest.TestCase):
    def test_resource_path_dev(self):
        from app.core.utils import resource_path
        p = resource_path(os.path.join("app", "ui", "logo.png"))
        self.assertTrue(p.endswith(os.path.join("app", "ui", "logo.png")))


if __name__ == "__main__":
    unittest.main()
