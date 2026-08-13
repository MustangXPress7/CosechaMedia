import os
import shutil
import tempfile
import unittest

try:
    from app.core import mtp
except ImportError:
    mtp = None


@unittest.skipUnless(mtp is not None, "mtp no disponible")
class TestMtpLive(unittest.TestCase):
    """Validación end-to-end contra un dispositivo MTP real conectado.
    Se omite automáticamente si no hay ninguno visible."""

    @classmethod
    def setUpClass(cls):
        cls.backend = mtp.WpdBackend()
        cls.device = None
        cls.storages = []
        try:
            devices = cls.backend.list_devices()
        except Exception:
            devices = []
        for d in devices:
            if d.device_id:
                cls.device = d
                break
        if cls.device is not None:
            try:
                with cls.backend._open_session(cls.device.device_id) as sess:
                    cls.storages = sess.storages()
            except Exception:
                cls.storages = []

    @classmethod
    def tearDownClass(cls):
        cls.backend = None
        cls.device = None
        cls.storages = []

    def test_device_connected(self):
        if self.device is None:
            self.skipTest("sin dispositivo MTP conectado")

    def test_storages_listed(self):
        if self.device is None or not self.storages:
            self.skipTest("sin dispositivo con storages legibles")
        for s in self.storages:
            self.assertTrue(s.is_dir)

    def test_stage_small_folder(self):
        if self.device is None or not self.storages:
            self.skipTest("sin dispositivo con storages legibles")
        folder = self.storages[0].name
        tmp = tempfile.mkdtemp(prefix="mtp_live_")
        old = mtp.db.db_path
        mtp.db.db_path = os.path.join(tmp, "db.sqlite")
        try:
            res = mtp.stage_device_folder(
                self.backend, self.device.device_id, folder, on_error=lambda e: None)
            self.assertGreaterEqual(res["errors"] + res["staged"] + res["skipped"], 0)
        finally:
            mtp.db.db_path = old
            shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
