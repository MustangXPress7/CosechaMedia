import os
import json
import shutil
import tempfile
import unittest
from datetime import datetime, timezone, timedelta
from unittest.mock import patch

from app.core.metadata_engine import MetadataEngine, _is_system_entry


class TestSystemEntryFilter(unittest.TestCase):
    def test_system_dir_names(self):
        for name in ("System Volume Information", "$RECYCLE.BIN", "Windows",
                     ".Trash-1000", "found.000", "Recovery"):
            self.assertTrue(_is_system_entry(name), name)

    def test_normal_dir_not_filtered(self):
        for name in ("DCIM", "PRIVATE", "MISC", "Camera", "Musica", "Fotos"):
            self.assertFalse(_is_system_entry(name), name)

    def test_system_files(self):
        for name in ("desktop.ini", "thumbs.db", ".DS_Store", "~$doc.docx",
                     "autorun.inf", ".Spotlight-V100"):
            self.assertTrue(_is_system_entry(name), name)

    def test_normal_files_not_filtered(self):
        for name in ("clip1.mp4", "foto.jpg", "audio.wav", "backup.dat"):
            self.assertFalse(_is_system_entry(name), name)


class TestScanSkipsSystemDirs(unittest.TestCase):
    def setUp(self):
        self.engine = MetadataEngine()
        self.tmp = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_scan_ignores_system_volume_information(self):
        system_dir = os.path.join(self.tmp, "System Volume Information")
        os.makedirs(system_dir, exist_ok=True)
        with open(os.path.join(system_dir, "WPSettings.dat"), "wb") as f:
            f.write(b"junk")
        with open(os.path.join(self.tmp, "clip1.mp4"), "wb") as f:
            f.write(b"fakemp4")

        seen = []

        def fake_meta(path):
            seen.append(path)
            return {"creation_dt": datetime(2024, 1, 2), "date_source": "metadata"}

        with patch.object(self.engine, "get_video_metadata", side_effect=fake_meta):
            result = self.engine.scan_source_for_dates(self.tmp, max_workers=1)

        self.assertFalse(any("System Volume Information" in p for p in seen),
                         "No debe escanear carpetas del sistema")
        self.assertEqual(result["total"], 1)
        self.assertEqual(result["by_date"].get("2024-01-02", []), [os.path.join(self.tmp, "clip1.mp4")])


class TestDateParsing(unittest.TestCase):
    def setUp(self):
        self.engine = MetadataEngine()

    def test_iso_utc_z(self):
        dt = self.engine._parse_datetime("2024-01-02T10:00:00.000000Z")
        expected = datetime(2024, 1, 2, 10, 0, 0, tzinfo=timezone.utc).astimezone().replace(tzinfo=None)
        self.assertEqual(dt, expected)

    def test_iso_with_offset(self):
        dt = self.engine._parse_datetime("2024-05-01T12:30:00+02:00")
        expected = datetime(2024, 5, 1, 12, 30, tzinfo=timezone(timedelta(hours=2))).astimezone().replace(tzinfo=None)
        self.assertEqual(dt, expected)

    def test_naive_iso(self):
        self.assertEqual(self.engine._parse_datetime("2024-03-10T08:15:00"), datetime(2024, 3, 10, 8, 15, 0))

    def test_date_only(self):
        self.assertEqual(self.engine._parse_datetime("2024-03-10"), datetime(2024, 3, 10))

    def test_space_separated(self):
        self.assertEqual(self.engine._parse_datetime("2024-03-10 08:15:00"), datetime(2024, 3, 10, 8, 15, 0))

    def test_invalid(self):
        self.assertIsNone(self.engine._parse_datetime("not-a-date"))
        self.assertIsNone(self.engine._parse_datetime(""))
        self.assertIsNone(self.engine._parse_datetime(None))


class TestFinalizeDates(unittest.TestCase):
    def setUp(self):
        self.engine = MetadataEngine()
        self.tmp = tempfile.mkdtemp()
        self.file = os.path.join(self.tmp, "clip.mp4")
        with open(self.file, "wb") as f:
            f.write(b"data")

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_metadata_priority(self):
        meta = {"creation_date": "2024-01-02T10:00:00.000000Z", "creation_dt": None, "date_source": None}
        self.engine._finalize_dates(meta, self.file)
        self.assertEqual(meta["date_source"], "metadata")
        self.assertIsNotNone(meta["creation_dt"])
        self.assertTrue(meta["creation_date"].startswith("2024-01-02"))

    def test_mtime_fallback(self):
        meta = {"creation_date": None, "creation_dt": None, "date_source": None}
        self.engine._finalize_dates(meta, self.file)
        self.assertEqual(meta["date_source"], "mtime")
        self.assertEqual(meta["creation_dt"], datetime.fromtimestamp(os.path.getmtime(self.file)))
        self.assertEqual(meta["creation_date"],
                         datetime.fromtimestamp(os.path.getmtime(self.file)).strftime("%Y-%m-%dT%H:%M:%S"))


class TestGetVideoMetadata(unittest.TestCase):
    def setUp(self):
        self.engine = MetadataEngine()
        self.engine._cache.clear()
        self.tmp = tempfile.mkdtemp()
        self.file = os.path.join(self.tmp, "clip.mp4")
        with open(self.file, "wb") as f:
            f.write(b"fakemp4data")

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    @staticmethod
    def _payload():
        return json.dumps({
            "format": {
                "format_name": "mov,mp4,m4a,3gp,3g2,mj2",
                "duration": "5.0",
                "bitrate": "1000",
                "tags": {
                    "make": "Apple",
                    "model": "iPhone 15 Pro",
                    "creation_time": "2024-01-02T10:00:00.000000Z",
                },
            },
            "streams": [
                {"codec_type": "video", "codec_name": "h264",
                 "width": 1920, "height": 1080, "r_frame_rate": "30/1",
                 "tags": {}},
            ],
        })

    def test_fields_and_normalized_date(self):
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = type("R", (), {"stdout": self._payload(), "returncode": 0})()
            meta = self.engine.get_video_metadata(self.file)
        self.assertEqual(meta["camera_make"], "Apple")
        self.assertEqual(meta["camera_model"], "iPhone 15 Pro")
        self.assertTrue(meta["is_video"])
        self.assertEqual(meta["width"], 1920)
        self.assertEqual(meta["height"], 1080)
        self.assertEqual(meta["date_source"], "metadata")
        expected = datetime(2024, 1, 2, 10, 0, 0, tzinfo=timezone.utc).astimezone().replace(tzinfo=None)
        self.assertEqual(meta["creation_dt"], expected)

    def test_android_tags(self):
        payload = json.dumps({
            "format": {
                "format_name": "mov,mp4",
                "tags": {
                    "com.android.manufacturer": "samsung",
                    "com.android.model": "SM-S928U",
                    "com.android.version": "14",
                },
            },
            "streams": [],
        })
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = type("R", (), {"stdout": payload, "returncode": 0})()
            meta = self.engine.get_video_metadata(self.file)
        self.assertEqual(meta["camera_make"], "samsung")
        self.assertEqual(meta["camera_model"], "SM-S928U")


class TestBatchScan(unittest.TestCase):
    def setUp(self):
        self.engine = MetadataEngine()

    def test_scan_groups_by_date(self):
        def fake_meta(path):
            base = os.path.basename(path)
            if base.startswith("a"):
                return {"creation_dt": datetime(2024, 1, 2), "date_source": "metadata"}
            if base.startswith("b"):
                return {"creation_dt": datetime(2024, 1, 3), "date_source": "metadata"}
            return {"creation_dt": None, "date_source": "mtime"}

        paths = ["/tmp/a1.mp4", "/tmp/a2.mp4", "/tmp/b1.mp4", "/tmp/c1.mp4"]
        with patch.object(self.engine, "get_video_metadata", side_effect=fake_meta):
            result = self.engine.scan_for_dates_batch(paths)
        self.assertEqual(set(result["by_date"].keys()), {"2024-01-02", "2024-01-03"})
        self.assertEqual(len(result["by_date"]["2024-01-02"]), 2)
        self.assertEqual(len(result["by_date"]["2024-01-03"]), 1)
        self.assertEqual(result["no_date"], ["/tmp/c1.mp4"])
        self.assertEqual(result["total"], 4)

    def test_scan_progress_calls(self):
        calls = []
        with patch.object(self.engine, "get_video_metadata",
                          return_value={"creation_dt": datetime(2024, 1, 2), "date_source": "metadata"}):
            self.engine.scan_for_dates_batch(["/tmp/x.mp4", "/tmp/y.mp4"],
                                             progress_cb=lambda d, t: calls.append((d, t)))
        self.assertEqual(calls[-1], (2, 2))

    def test_scan_cancel(self):
        with patch.object(self.engine, "get_video_metadata",
                          return_value={"creation_dt": datetime(2024, 1, 2), "date_source": "metadata"}):
            result = self.engine.scan_for_dates_batch(["/tmp/x.mp4", "/tmp/y.mp4"],
                                                      cancel_cb=lambda: True)
        self.assertEqual(result["total"], 2)
        self.assertEqual(result["by_date"], {})


class TestDateKey(unittest.TestCase):
    def setUp(self):
        self.engine = MetadataEngine()
        self.tmp = tempfile.mkdtemp()
        self.file = os.path.join(self.tmp, "clip.mp4")
        with open(self.file, "wb") as f:
            f.write(b"data")

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_metadata_date(self):
        with patch.object(self.engine, "get_video_metadata",
                          return_value={"creation_dt": datetime(2024, 1, 2), "date_source": "metadata"}):
            self.assertEqual(self.engine.date_key_for_file(self.file), "2024-01-02")

    def test_mtime_fallback(self):
        with patch.object(self.engine, "get_video_metadata",
                          return_value={"creation_dt": None, "date_source": None}):
            expected = datetime.fromtimestamp(os.path.getmtime(self.file)).strftime("%Y-%m-%d")
            self.assertEqual(self.engine.date_key_for_file(self.file), expected)

    def test_no_date(self):
        with patch.object(self.engine, "get_video_metadata",
                          return_value={"creation_dt": None, "date_source": None}), \
             patch("os.path.getmtime", side_effect=OSError):
            self.assertIsNone(self.engine.date_key_for_file(self.file))


if __name__ == "__main__":
    unittest.main()
