import os
import shutil
import sys
import tempfile
import threading
import unittest
from unittest import mock

from app.core import mtp


class FakeSession:
    """Árbol de archivos en memoria que imita la interfaz de una sesión WPD."""

    def __init__(self, root):
        self._root = root
        self._nodes = {}
        self._oid_seq = 0
        self.downloaded = []
        self.fail_downloads = set()
        self.closed = False
        self._build(self._root, "")

    def _register(self, name, rel, size, mtime, is_dir, children):
        self._oid_seq += 1
        oid = f"o{self._oid_seq}"
        self._nodes[oid] = {
            "name": name, "rel": rel, "size": size, "mtime": mtime,
            "is_dir": is_dir, "children": children,
        }
        return oid

    def _build(self, node, prefix):
        rel = f"{prefix}/{node['name']}" if prefix else node["name"]
        children = {}
        oid = self._register(node["name"], rel, node.get("size", 0),
                             node.get("mtime", 0), node.get("is_dir", False), children)
        for child in node.get("children", []):
            child_oid = self._build(child, rel)
            children[child["name"]] = child_oid
        return oid

    # -- interfaz ---------------------------------------------------------

    def storages(self):
        return [self._make_file(oid) for oid, n in self._nodes.items()
                if "/" not in n["rel"] and n["is_dir"]]

    def _resolve(self, folder_path):
        parts = [p for p in folder_path.split("/") if p]
        if not parts:
            return None
        matches = [self._make_file(oid) for oid, n in self._nodes.items()
                   if n["rel"] == parts[0] and n["is_dir"]]
        if not matches:
            return None
        cur = matches[0]
        for part in parts[1:]:
            node = self._nodes[cur.object_id]
            child_oid = node["children"].get(part)
            if child_oid is None:
                return None
            cur = self._make_file(child_oid)
        return cur

    def _enum_children(self, object_id):
        node = self._nodes[object_id]
        out = []
        for oid in node["children"].values():
            rf = self._make_file(oid)
            rf.rel_path = self._nodes[oid]["name"]
            out.append(rf)
        return out

    def children(self, folder_path):
        content = self._resolve(folder_path) if folder_path else None
        if folder_path and content is None:
            return []
        if content is None:
            return self.storages()
        return self._enum_children(content.object_id)

    def download(self, rf, dest_path):
        if rf.object_id in self.fail_downloads:
            raise OSError("simulated download failure")
        os.makedirs(os.path.dirname(dest_path), exist_ok=True)
        with open(dest_path, "wb") as fh:
            fh.write(b"x" * max(int(rf.size), 0))
        self.downloaded.append(rf.rel_path)

    def close(self):
        self.closed = True

    def __enter__(self):
        return self

    def __exit__(self, *a):
        self.close()

    def _make_file(self, oid):
        n = self._nodes[oid]
        from datetime import datetime
        mtime = datetime.fromtimestamp(n["mtime"]) if n["mtime"] else None
        return mtp.RemoteFile(
            rel_path=n["rel"], name=n["name"], size=n["size"],
            date_modified=mtime, is_dir=n["is_dir"], object_id=oid,
        )


class FakeBackend(mtp.MtpBackend):
    def __init__(self, root, name="Fake Phone"):
        self._root = root
        self._name = name
        self.fail_downloads = set()

    def list_devices(self):
        return [mtp.DeviceInfo("D1", self._name)]

    def _open_session(self, device_id):
        sess = FakeSession(self._root)
        sess.fail_downloads = self.fail_downloads
        return sess


def _tree():
    return {
        "name": "Internal", "is_dir": True, "children": [
            {"name": "DCIM", "is_dir": True, "children": [
                {"name": "IMG_1.jpg", "size": 100, "mtime": 100},
                {"name": "VID_1.mp4", "size": 500, "mtime": 200},
                {"name": "Camera", "is_dir": True, "children": [
                    {"name": "IMG_2.jpg", "size": 50, "mtime": 300},
                ]},
            ]},
            {"name": "Pictures", "is_dir": True, "children": [
                {"name": "pic.png", "size": 10, "mtime": 10},
            ]},
        ],
    }


class TestDeviceCacheDir(unittest.TestCase):
    def test_deterministic_and_sanitized(self):
        a = mtp.device_cache_dir("dev-1", "Internal/DCIM")
        b = mtp.device_cache_dir("dev-1", "Internal/DCIM")
        c = mtp.device_cache_dir("dev-1", "DCIM")
        self.assertEqual(a, b)
        self.assertNotEqual(a, c)
        self.assertIn("Internal", a)


class TestStaging(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="mtp_test_")
        self._old_db_path = mtp.db.db_path
        mtp.db.db_path = os.path.join(self.tmp, "db.sqlite")

    def tearDown(self):
        mtp.db.db_path = self._old_db_path
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_first_run_stages_all(self):
        backend = FakeBackend(_tree())
        res = mtp.stage_device_folder(backend, "D1", "Internal/DCIM")
        self.assertEqual(res["staged"], 3)
        self.assertEqual(res["errors"], 0)
        cache = mtp.device_cache_dir("D1", "Internal/DCIM")
        for rel in ("IMG_1.jpg", "VID_1.mp4", "Camera/IMG_2.jpg"):
            self.assertTrue(os.path.exists(os.path.join(cache, *rel.split("/"))),
                            f"missing {rel}")

    def test_second_run_skips_unchanged(self):
        backend = FakeBackend(_tree())
        mtp.stage_device_folder(backend, "D1", "Internal/DCIM")
        res = mtp.stage_device_folder(backend, "D1", "Internal/DCIM")
        self.assertEqual(res["skipped"], 3)
        self.assertEqual(res["staged"], 0)

    def test_changed_and_new_files(self):
        tree = _tree()
        backend = FakeBackend(tree)
        mtp.stage_device_folder(backend, "D1", "Internal/DCIM")
        dcim = tree["children"][0]
        dcim["children"][0] = {"name": "IMG_1.jpg", "size": 200, "mtime": 999}
        dcim["children"].append({"name": "NEW.jpg", "size": 7, "mtime": 1})
        res = mtp.stage_device_folder(backend, "D1", "Internal/DCIM")
        self.assertEqual(res["staged"], 2)
        self.assertEqual(res["skipped"], 2)

    def test_removed_file_cleaned(self):
        backend = FakeBackend(_tree())
        mtp.stage_device_folder(backend, "D1", "Internal/DCIM")
        cache = mtp.device_cache_dir("D1", "Internal/DCIM")
        gone = os.path.join(cache, "IMG_1.jpg")
        self.assertTrue(os.path.exists(gone))
        tree = _tree()
        tree["children"][0]["children"] = [c for c in tree["children"][0]["children"]
                                           if c["name"] != "IMG_1.jpg"]
        res = mtp.stage_device_folder(FakeBackend(tree), "D1", "Internal/DCIM")
        self.assertFalse(os.path.exists(gone))
        manifest = mtp._load_manifest(cache)
        self.assertNotIn("IMG_1.jpg", manifest)

    def test_download_error_reported_and_continues(self):
        backend = FakeBackend(_tree())
        fail_oid = None
        with backend._open_session("D1") as sess:
            fail_oid = next(oid for oid, n in sess._nodes.items() if n["name"] == "VID_1.mp4")
        backend.fail_downloads.add(fail_oid)
        errors = []
        res = mtp.stage_device_folder(backend, "D1", "Internal/DCIM", on_error=errors.append)
        self.assertEqual(res["staged"], 2)
        self.assertEqual(res["errors"], 1)
        self.assertTrue(any("VID_1.mp4" in e for e in errors))

    def test_cancel_stops(self):
        calls = {"n": 0}

        def cancel():
            calls["n"] += 1
            return calls["n"] > 1

        backend = FakeBackend(_tree())
        res = mtp.stage_device_folder(backend, "D1", "Internal/DCIM", cancel=cancel)
        self.assertLessEqual(res["staged"], 2)

    def test_walk_relative_paths(self):
        backend = FakeBackend(_tree())
        files = backend.walk("D1", "Internal/DCIM")
        rels = sorted(f.rel_path for f in files)
        self.assertEqual(rels, ["IMG_1.jpg", "IMG_2.jpg", "VID_1.mp4"])
        for f in files:
            self.assertFalse(f.is_dir)
            self.assertGreaterEqual(f.size, 0)

    def test_whole_device_storage_staging(self):
        backend = FakeBackend(_tree())
        res = mtp.stage_device_folder(backend, "D1", "")
        self.assertEqual(res["staged"], 4)
        cache = mtp.device_cache_dir("D1", "")
        self.assertTrue(os.path.exists(os.path.join(cache, "Internal", "DCIM", "IMG_1.jpg")))


@unittest.skipUnless(sys.platform == "win32", "WPD/COM es Windows-only")
class TestThreadLocalManager(unittest.TestCase):
    """El manager COM (`IPortableDeviceManager`) debe ser por hilo, no un
    singleton global: el staging en QThread y el list_devices del hilo
    principal no pueden compartir objetos COM entre apartamentos."""

    def setUp(self):
        self._orig_ensure_types = mtp._ensure_types
        mtp._ensure_types = lambda: None

    def tearDown(self):
        mtp._ensure_types = self._orig_ensure_types

    def test_manager_is_thread_local(self):
        created = []

        def fake_create(*args, **kwargs):
            dm = mock.MagicMock()
            created.append(dm)
            return dm

        with mock.patch("comtypes.client.CreateObject", side_effect=fake_create), \
             mock.patch.dict(sys.modules,
                             {"comtypes.gen.PortableDeviceApiLib": mock.MagicMock()}):
            m1 = mtp._manager()
            m2 = mtp._manager()
            other = {}
            t = threading.Thread(target=lambda: other.setdefault("dm", mtp._manager()))
            t.start()
            t.join()
        self.assertIs(m1, m2)
        self.assertIsNot(m1, other["dm"])
        self.assertEqual(len(created), 2)

    def test_list_devices_uses_current_thread_manager(self):
        fake_dm = mock.MagicMock()

        def fake_get_devices(ids, count):
            if not ids:
                count.contents.value = 2
                return
            for i, dev_id in enumerate(["DEV1", "DEV2"]):
                ids[i] = dev_id

        fake_dm.GetDevices.side_effect = fake_get_devices

        def fake_friendly_name(dev_id, buf, nlen):
            name = {"DEV1": "Camera A", "DEV2": "Camera B"}.get(dev_id, dev_id)
            nlen.contents.value = len(name)
            if buf:
                for i, ch in enumerate(name):
                    buf[i] = ord(ch)
                buf[len(name)] = 0

        fake_dm.GetDeviceFriendlyName.side_effect = fake_friendly_name

        with mock.patch.object(mtp, "_manager", return_value=fake_dm), \
             mock.patch("comtypes.CoInitialize"), \
             mock.patch("comtypes.CoUninitialize"):
            devices = mtp.WpdBackend().list_devices()
        self.assertEqual([d.device_id for d in devices], ["DEV1", "DEV2"])
        self.assertEqual([d.name for d in devices], ["Camera A", "Camera B"])
        self.assertGreaterEqual(fake_dm.GetDevices.call_count, 1)

    def test_wpd_session_devicename_no_duplicate(self):
        fake_port = mock.MagicMock()
        fake_types = mock.MagicMock()
        ci = mock.MagicMock()
        device_mock = mock.MagicMock()
        device_mock.Content.return_value.Properties.return_value.GetValues.return_value.GetStringValue.return_value = "SERIAL9"
        fake_dm = mock.MagicMock()

        def fake_friendly_name(pnp_id, buf, nlen):
            nlen.contents.value = 0

        fake_dm.GetDeviceFriendlyName.side_effect = fake_friendly_name

        def fake_create(clsid, clsctx=None, interface=None):
            if clsid is fake_types.PortableDeviceValues:
                return ci
            if clsid is fake_port.PortableDevice:
                return device_mock
            return mock.MagicMock()

        with mock.patch.object(mtp, "_manager", return_value=fake_dm), \
             mock.patch.object(mtp, "_pkey", lambda fmtid, pid: mock.MagicMock()), \
             mock.patch("comtypes.CoInitialize"), \
             mock.patch("comtypes.CoUninitialize"), \
             mock.patch("comtypes.client.CreateObject", side_effect=fake_create), \
             mock.patch.dict(sys.modules, {
                 "comtypes.gen.PortableDeviceApiLib": fake_port,
                 "comtypes.gen.PortableDeviceTypesLib": fake_types,
             }):
            sess = mtp._WpdSession("PNP1")
            try:
                self.assertEqual(sess.devicename, "PNP1_SERIAL9")
                self.assertNotEqual(sess.devicename, "PNP1_PNP1_SERIAL9")
            finally:
                sess.close()


if __name__ == "__main__":
    unittest.main()
