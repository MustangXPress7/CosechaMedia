"""Self-check/mínimo para la normalización USB + repair (bug copia fantasma)."""
import os
import tempfile
import unittest

from app.core.db import DatabaseManager, usb_device_id


class TestUsbIdentity(unittest.TestCase):

    def setUp(self):
        tmp = tempfile.mkdtemp()
        self.db = DatabaseManager(os.path.join(tmp, "test.db"))

    def test_normalize_formats(self):
        self.assertEqual(usb_device_id("F:"), "usb:F:\\")
        self.assertEqual(usb_device_id("F:\\"), "usb:F:\\")
        self.assertEqual(usb_device_id("F:/"), "usb:F:\\")
        self.assertEqual(usb_device_id("F:\\DCIM"), "usb:F:\\")
        self.assertEqual(usb_device_id("usb:F:/"), "usb:F:\\")
        self.assertEqual(usb_device_id("g:\\"), "usb:G:\\")
        self.assertEqual(usb_device_id(""), "")

    def test_repair_consolidates_duplicates(self):
        # Datos pre-fix: claves USB guardadas con formatos distintos (sin la
        # normalización del upsert, que ya colapsa en escrituras nuevas).
        conn = self.db.get_connection()
        cur = conn.cursor()
        for did in ("usb:F:/", "usb:F:\\", "F:\\DCIM", "G:\\"):
            cur.execute(
                "INSERT OR IGNORE INTO known_devices "
                "(device_id, device_type, name) VALUES (?, 'usb', ?)",
                (did, did))
        conn.commit()
        conn.close()
        project = self.db.create_project("P", os.path.join(self.db.db_path, "..", "proj"))
        conn = self.db.get_connection()
        conn.execute(
            "INSERT INTO sessions (project_id, name, status, device_id, source_path) "
            "VALUES (?, 's1', 'pending', 'usb:F:/', 'F:/')",
            (project,))
        conn.commit()
        conn.close()

        migrated = self.db.repair_duplicate_usb_keys()
        self.assertGreaterEqual(migrated, 4)

        usb_f = [d["device_id"] for d in self.db.list_known_devices()
                 if d["device_id"] == "usb:F:\\"]
        self.assertEqual(len(usb_f), 1)

        conn = self.db.get_connection()
        row = conn.execute(
            "SELECT device_id FROM sessions WHERE name='s1'").fetchone()
        conn.close()
        self.assertEqual(row[0], "usb:F:\\")

    def test_sync_keeps_usb_type(self):
        self.db.save_dispositivo_config("F:\\", "CAM-X")
        self.db.sync_device_settings_to_known()
        kd = self.db.get_known_device("usb:F:\\")
        self.assertIsNotNone(kd)
        self.assertEqual(kd["device_type"], "usb")

    def test_repair_purges_corrupt_usb_wrapped_keys(self):
        conn = self.db.get_connection()
        cur = conn.cursor()
        for did in ("usb:mtp:auto1", "usb:ftp:13", "usb:wifi:x"):
            cur.execute(
                "INSERT OR IGNORE INTO known_devices "
                "(device_id, device_type, name) VALUES (?, 'usb', ?)",
                (did, did))
        conn.commit()
        conn.close()

        self.db.repair_duplicate_usb_keys()

        for did in ("usb:mtp:auto1", "usb:ftp:13", "usb:wifi:x"):
            self.assertIsNone(self.db.get_known_device(did))


if __name__ == "__main__":
    unittest.main()