import ftplib
import os
import shutil
import socket
import tempfile
import threading
import unittest
from unittest import mock

from app.core import ftp as ftpmod
from app.core.db import db


def _tree():
    return {
        "/": {"type": "dir", "children": ["Internal"]},
        "/Internal": {"type": "dir", "children": ["DCIM", "Pictures"]},
        "/Internal/DCIM": {"type": "dir", "children": ["IMG_1.jpg", "VID_1.mp4", "Camera"]},
        "/Internal/DCIM/IMG_1.jpg": {"type": "file", "size": 100, "mtime": "20260101120000"},
        "/Internal/DCIM/VID_1.mp4": {"type": "file", "size": 500, "mtime": "20260101130000"},
        "/Internal/DCIM/Camera": {"type": "dir", "children": ["IMG_2.jpg"]},
        "/Internal/DCIM/Camera/IMG_2.jpg": {"type": "file", "size": 50, "mtime": "20260101140000"},
        "/Internal/Pictures": {"type": "dir", "children": ["pic.png"]},
        "/Internal/Pictures/pic.png": {"type": "file", "size": 10, "mtime": "20260101150000"},
    }


class FakeFtpConnection:
    """Fake de ftplib.FTP: árbol en memoria por ruta absoluta."""

    def __init__(self, tree, state=None, mlsd_ok=True):
        self._tree = tree
        self._state = state or {}
        self.mlsd_ok = mlsd_ok
        self.retr_count = 0
        self.quit_called = False
        self.close_called = False

    def connect(self, host, port=21, timeout=None):
        return "220 fake"

    def set_pasv(self, val):
        self.pasv = bool(val)

    def _check_passive(self):
        if getattr(self, "pasv", False) and self._state.get("fail_passive"):
            raise ftplib.error_temp("425 Can't open passive connection")
        if not getattr(self, "pasv", True) and self._state.get("fail_active"):
            raise ftplib.error_temp("425 Can't open active connection")

    def login(self, user="", passwd=""):
        return "230 ok"

    def _entry(self, path):
        return self._tree[path]

    def mlsd(self, path, facts=()):
        if not self.mlsd_ok:
            raise ftplib.error_perm("500 MLSD not implemented")
        self._check_passive()
        entry = self._entry(path)
        for name in entry.get("children", []):
            child = self._tree[path.rstrip("/") + "/" + name]
            out = {"type": child["type"]}
            if child["type"] == "file":
                out["size"] = str(child.get("size", 0))
                if child.get("mtime"):
                    out["modify"] = child["mtime"]
            yield (name, out)

    def nlst(self, path):
        self._check_passive()
        entry = self._entry(path)
        prefix = path.rstrip("/") + "/" if path != "/" else "/"
        return [prefix + name for name in entry.get("children", [])]

    def size(self, path):
        entry = self._entry(path)
        if entry["type"] != "file":
            raise ftplib.error_perm("550 not a regular file")
        return entry.get("size", 0)

    def sendcmd(self, cmd):
        parts = cmd.split(" ", 1)
        if parts[0].upper() == "MDTM":
            entry = self._entry(parts[1])
            return "213 " + entry.get("mtime", "19700101000000")
        raise ftplib.error_perm("500 unknown command")

    def retrbinary(self, cmd, callback, blocksize=8192):
        self.retr_count += 1
        path = cmd.split(" ", 1)[1]
        if self._state.get("fail_first"):
            self._state["fail_first"] = False
            raise ftplib.error_temp("421 connection lost")
        if self._state.get("fail_perm") == path:
            raise ftplib.error_perm("550 no such file")
        entry = self._entry(path)
        data = b"x" * int(entry.get("size", 0))
        for i in range(0, len(data), blocksize):
            callback(data[i:i + blocksize])

    def quit(self):
        self.quit_called = True
        raise ftplib.error_temp("421 bye")

    def close(self):
        self.close_called = True


class TestFtpHelpers(unittest.TestCase):
    def test_device_key_roundtrip(self):
        self.assertEqual(ftpmod.profile_id_from_device_key(ftpmod.device_key(7)), 7)
        self.assertIsNone(ftpmod.profile_id_from_device_key("USB#vid"))
        self.assertIsNone(ftpmod.profile_id_from_device_key("ftp:abc"))

    def test_to_remote(self):
        sess = object.__new__(ftpmod.FtpSession)
        sess._base = ""
        self.assertEqual(sess._to_remote(""), "/")
        self.assertEqual(sess._to_remote("Internal/DCIM"), "/Internal/DCIM")
        sess._base = "Internal"
        self.assertEqual(sess._to_remote(""), "/Internal")
        self.assertEqual(sess._to_remote("DCIM/Camera"), "/Internal/DCIM/Camera")


class TestFtpStaging(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="ftp_test_")
        self._old_db_path = db.db_path
        db.db_path = os.path.join(self.tmp, "db.sqlite")
        db.create_tables()
        self.tree = _tree()
        self.profile_id = db.add_ftp_profile("Fake Phone", "127.0.0.1", 2221,
                                             username="user", password="pass")
        self.device_id = ftpmod.device_key(self.profile_id)

    def tearDown(self):
        db.db_path = self._old_db_path
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _factory(self, **kwargs):
        state = kwargs.pop("state", {})
        return lambda: FakeFtpConnection(self.tree, state=state, **kwargs)

    def test_first_run_stages_all(self):
        with mock.patch.object(ftpmod.ftplib, "FTP", self._factory()):
            backend = ftpmod.FtpBackend()
            res = ftpmod.stage_device_folder(backend, self.device_id, "Internal/DCIM")
        self.assertEqual(res["staged"], 3)
        self.assertEqual(res["errors"], 0)
        cache = ftpmod.device_cache_dir(self.device_id, "Internal/DCIM")
        for rel in ("IMG_1.jpg", "VID_1.mp4", "Camera/IMG_2.jpg"):
            self.assertTrue(os.path.exists(os.path.join(cache, *rel.split("/"))),
                            f"missing {rel}")

    def test_second_run_skips_unchanged(self):
        with mock.patch.object(ftpmod.ftplib, "FTP", self._factory()):
            backend = ftpmod.FtpBackend()
            ftpmod.stage_device_folder(backend, self.device_id, "Internal/DCIM")
            res = ftpmod.stage_device_folder(backend, self.device_id, "Internal/DCIM")
        self.assertEqual(res["skipped"], 3)
        self.assertEqual(res["staged"], 0)

    def test_fallback_listing_without_mlsd(self):
        with mock.patch.object(ftpmod.ftplib, "FTP", self._factory(mlsd_ok=False)):
            backend = ftpmod.FtpBackend()
            res = ftpmod.stage_device_folder(backend, self.device_id, "Internal/DCIM")
        self.assertEqual(res["staged"], 3)
        self.assertEqual(res["errors"], 0)

    def test_retries_once_on_connection_loss(self):
        with mock.patch.object(ftpmod.ftplib, "FTP", self._factory(state={"fail_first": True})):
            backend = ftpmod.FtpBackend()
            res = ftpmod.stage_device_folder(backend, self.device_id, "Internal/DCIM")
        self.assertEqual(res["staged"], 3)
        self.assertEqual(res["errors"], 0)

    def test_permanent_download_error_reported(self):
        errors = []
        state = {"fail_perm": "/Internal/DCIM/VID_1.mp4"}
        with mock.patch.object(ftpmod.ftplib, "FTP", self._factory(state=state)):
            backend = ftpmod.FtpBackend()
            res = ftpmod.stage_device_folder(backend, self.device_id, "Internal/DCIM",
                                             on_error=errors.append)
        self.assertEqual(res["staged"], 2)
        self.assertEqual(res["errors"], 1)
        self.assertTrue(any("VID_1.mp4" in e for e in errors))

    def test_whole_device_staging(self):
        with mock.patch.object(ftpmod.ftplib, "FTP", self._factory()):
            backend = ftpmod.FtpBackend()
            res = ftpmod.stage_device_folder(backend, self.device_id, "")
        self.assertEqual(res["staged"], 4)
        cache = ftpmod.device_cache_dir(self.device_id, "")
        self.assertTrue(os.path.exists(os.path.join(cache, "Internal", "DCIM", "IMG_1.jpg")))

    def test_base_folder_is_respected(self):
        self.tree["/Internal"] = {"type": "dir", "children": ["DCIM", "Pictures"]}
        self.tree["/Internal/Pictures"] = self.tree["/Internal/Pictures"]
        db.update_ftp_profile(self.profile_id, base_folder="Internal")
        with mock.patch.object(ftpmod.ftplib, "FTP", self._factory()):
            backend = ftpmod.FtpBackend()
            res = ftpmod.stage_device_folder(backend, self.device_id, "DCIM")
        self.assertEqual(res["staged"], 3)
        cache = ftpmod.device_cache_dir(self.device_id, "DCIM")
        self.assertTrue(os.path.exists(os.path.join(cache, "IMG_1.jpg")))

    def test_passive_failure_flips_profile_to_active(self):
        state = {"fail_passive": True}
        with mock.patch.object(ftpmod.ftplib, "FTP", self._factory(state=state)):
            backend = ftpmod.FtpBackend()
            children = backend.list_children(self.device_id, "")
        self.assertTrue(any(c.name == "Internal" for c in children))
        row = db.get_ftp_profile(self.profile_id)
        self.assertFalse(row["passive"])

    def test_active_failure_flips_profile_to_passive(self):
        db.update_ftp_profile(self.profile_id, passive=False)
        state = {"fail_active": True}
        with mock.patch.object(ftpmod.ftplib, "FTP", self._factory(state=state)):
            backend = ftpmod.FtpBackend()
            children = backend.list_children(self.device_id, "")
        self.assertTrue(any(c.name == "Internal" for c in children))
        row = db.get_ftp_profile(self.profile_id)
        self.assertTrue(row["passive"])

    def test_errors_are_reported_not_flipped(self):
        state = {"fail_passive": True, "fail_active": True}
        with mock.patch.object(ftpmod.ftplib, "FTP", self._factory(state=state)):
            backend = ftpmod.FtpBackend()
            with self.assertRaises(ftplib.error_temp):
                backend.list_children(self.device_id, "")

    def test_stage_flips_mode_when_passive_never_works(self):
        state = {"fail_passive": True}
        with mock.patch.object(ftpmod.ftplib, "FTP", self._factory(state=state)):
            backend = ftpmod.FtpBackend()
            res = ftpmod.stage_device_folder(backend, self.device_id, "Internal/DCIM")
        self.assertEqual(res["staged"], 3)
        row = db.get_ftp_profile(self.profile_id)
        self.assertFalse(row["passive"])


class TestFtpReachability(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="ftp_test_")
        self._old_db_path = db.db_path
        db.db_path = os.path.join(self.tmp, "db.sqlite")
        db.create_tables()
        self.profile_id = db.add_ftp_profile("Fake Phone", "127.0.0.1", 2221)
        self.device_id = ftpmod.device_key(self.profile_id)

    def tearDown(self):
        db.db_path = self._old_db_path
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_reachable(self):
        backend = ftpmod.FtpBackend()
        with mock.patch.object(ftpmod.ftplib, "FTP",
                               lambda: FakeFtpConnection(_tree(), state={})):
            self.assertTrue(backend.is_reachable(self.device_id))

    def test_reachable_in_active_when_passive_broken(self):
        state = {"fail_passive": True}
        backend = ftpmod.FtpBackend()
        with mock.patch.object(ftpmod.ftplib, "FTP",
                               lambda: FakeFtpConnection(_tree(), state=state)):
            self.assertTrue(backend.is_reachable(self.device_id))

    def test_not_reachable(self):
        backend = ftpmod.FtpBackend()
        self.assertFalse(backend.is_reachable("ftp:99999"))
        self.assertFalse(backend.is_reachable("not-a-device"))


class TestNetworkScan(unittest.TestCase):
    def _serve_banner(self, banner=b"220 Primitive FTPd on TEST\r\n"):
        srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        srv.bind(("127.0.0.1", 0))
        srv.listen(1)
        port = srv.getsockname()[1]

        def serve():
            conn, _ = srv.accept()
            conn.sendall(banner)
            conn.close()
            srv.close()

        t = threading.Thread(target=serve, daemon=True)
        t.start()
        return port

    def test_probe_ftp_banner(self):
        port = self._serve_banner()
        self.assertEqual(
            ftpmod.probe_ftp_banner("127.0.0.1", port, timeout=2.0),
            "220 Primitive FTPd on TEST")
        self.assertIsNone(ftpmod.probe_ftp_banner("127.0.0.1", port + 1, timeout=0.5))

    def test_scan_network_ftp_custom_hosts(self):
        port = self._serve_banner()
        results = ftpmod.scan_network_ftp(hosts=["127.0.0.1"], ports=(port,), timeout=2.0)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["host"], "127.0.0.1")
        self.assertEqual(results[0]["port"], port)
        self.assertIn("FTP", results[0]["banner"])

    def test_scan_no_results(self):
        results = ftpmod.scan_network_ftp(hosts=["127.0.0.1"], ports=(65531,), timeout=0.4)
        self.assertEqual(results, [])


if __name__ == "__main__":
    unittest.main()
