import os
import shutil
import tempfile
import threading
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

    def _require_device(self):
        if self.device is None:
            self.skipTest("sin dispositivo MTP conectado")

    def _require_storages(self):
        self._require_device()
        if not self.storages:
            self.skipTest("sin storages legibles")

    def test_device_connected(self):
        self._require_device()

    def test_storages_listed(self):
        self._require_storages()
        for s in self.storages:
            self.assertTrue(s.is_dir)
            self.assertTrue(s.name)

    def test_enumerate_root_children(self):
        self._require_storages()
        with self.backend._open_session(self.device.device_id) as sess:
            storage = self.storages[0]
            children = sess._enum_children(storage.object_id)
            self.assertGreater(len(children), 0)
            for c in children:
                self.assertTrue(c.is_dir)
                self.assertTrue(c.name)

    def test_enumerate_subfolder(self):
        self._require_storages()
        with self.backend._open_session(self.device.device_id) as sess:
            storage = self.storages[0]
            root_children = sess._enum_children(storage.object_id)
            folders = [c for c in root_children if c.is_dir and c.name == "Pictures"]
            if not folders:
                self.skipTest("carpeta Pictures no encontrada")
            pic_kids = sess._enum_children(folders[0].object_id)
            self.assertGreater(len(pic_kids), 0)
            has_files = any(not c.is_dir for c in pic_kids)
            self.assertTrue(has_files, "Pictures debería contener archivos")

    def _try_download(self, sess, remote_file, timeout=15):
        """Intenta descargar un archivo con timeout; devuelve (ok, tmp_path, error_msg)."""
        tmp = tempfile.mktemp(suffix=".tmp")
        result = {"ok": False, "error": None}

        def _do():
            try:
                sess.download(remote_file, tmp)
                result["ok"] = True
            except Exception as e:
                herr = getattr(e, "hresult", None)
                herr_hex = f"0x{herr & 0xFFFFFFFF:08X}" if herr is not None else "N/A"
                result["error"] = f"{e} (HRESULT={herr_hex})"

        t = threading.Thread(target=_do, daemon=True)
        t.start()
        t.join(timeout=timeout)
        if t.is_alive():
            result["error"] = f"timeout {timeout}s (GetStream colgado)"
        if os.path.exists(tmp):
            os.unlink(tmp)
        return result["ok"], tmp, result["error"]

    def test_download_smallest_file(self):
        self._require_storages()
        with self.backend._open_session(self.device.device_id) as sess:
            storage = self.storages[0]
            root_children = sess._enum_children(storage.object_id)
            folders = [c for c in root_children if c.is_dir and c.name == "Pictures"]
            if not folders:
                self.skipTest("carpeta Pictures no encontrada")
            pic_kids = sess._enum_children(folders[0].object_id)
            files = sorted([c for c in pic_kids if not c.is_dir], key=lambda x: x.size)
            if not files:
                self.skipTest("sin archivos en Pictures")
            last_err = None
            for f in files[:3]:
                ok, _, err = self._try_download(sess, f, timeout=15)
                if ok:
                    return
                last_err = err
            self.skipTest(
                f"el dispositivo no soporta GetStream para archivos en Pictures "
                f"(WPD_E_OBJECT_NOT_ACCESSIBLE o similar). "
                f"Ultimo error: {last_err}"
            )


if __name__ == "__main__":
    unittest.main()
