import os
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import app.core.updater as updater


class TestVersionParsing(unittest.TestCase):
    def test_parse_version(self):
        self.assertEqual(updater._parse_version("v2.0.0"), (2, 0, 0))
        self.assertEqual(updater._parse_version("2.0"), (2, 0, 0))
        self.assertEqual(updater._parse_version("2"), (2, 0, 0))
        self.assertEqual(updater._parse_version("V2.10.0-rc1"), (2, 10, 0))
        self.assertEqual(updater._parse_version(""), (0, 0, 0))

    def test_compare_versions(self):
        self.assertEqual(updater.compare_versions("2.0.1", "2.0.0"), 1)
        self.assertEqual(updater.compare_versions("2.0.0", "2.0.0"), 0)
        self.assertEqual(updater.compare_versions("1.9.9", "2.0.0"), -1)
        self.assertEqual(updater.compare_versions("v2.1", "2.0.9"), 1)


class TestAssetSelection(unittest.TestCase):
    def _assets(self):
        return [
            {"name": "CosechaMedia-windows-x86_64.exe", "size": 1, "browser_download_url": "u1"},
            {"name": "CosechaMedia-macos.app.zip", "size": 2, "browser_download_url": "u2"},
            {"name": "CosechaMedia-linux-x86_64", "size": 3, "browser_download_url": "u3"},
        ]

    def test_windows(self):
        with mock.patch.object(updater.sys, "platform", "win32"):
            asset = updater.select_platform_asset({"assets": self._assets()})
            self.assertEqual(asset["name"], "CosechaMedia-windows-x86_64.exe")

    def test_macos(self):
        with mock.patch.object(updater.sys, "platform", "darwin"):
            asset = updater.select_platform_asset({"assets": self._assets()})
            self.assertEqual(asset["name"], "CosechaMedia-macos.app.zip")

    def test_linux(self):
        with mock.patch.object(updater.sys, "platform", "linux"):
            asset = updater.select_platform_asset({"assets": self._assets()})
            self.assertEqual(asset["name"], "CosechaMedia-linux-x86_64")

    def test_no_assets(self):
        with mock.patch.object(updater.sys, "platform", "win32"):
            self.assertIsNone(updater.select_platform_asset({"assets": []}))

    def test_no_matching_platform(self):
        with mock.patch.object(updater, "_platform_keywords", return_value=("solaris",)):
            self.assertIsNone(updater.select_platform_asset({"assets": self._assets()}))


class TestSha256(unittest.TestCase):
    def test_sha256sum_and_verify(self):
        with tempfile.NamedTemporaryFile(delete=False) as f:
            f.write(b"hello world")
            path = f.name
        try:
            digest = updater.sha256sum(path)
            self.assertEqual(len(digest), 64)
            self.assertTrue(updater.verify_sha256(path, digest))
            self.assertFalse(updater.verify_sha256(path, "0" * 64))
            self.assertTrue(updater.verify_sha256(path, digest.upper()))
        finally:
            os.unlink(path)


class TestDownloadFile(unittest.TestCase):
    def test_download_file(self):
        with tempfile.NamedTemporaryFile(delete=False) as f:
            f.write(b"hello download")
            src = f.name
        tmp = tempfile.mkdtemp(prefix="upd_")
        try:
            dst = os.path.join(tmp, "out.bin")
            updater.download_file(Path(src).as_uri(), dst)
            with open(dst, "rb") as f2:
                self.assertEqual(f2.read(), b"hello download")
        finally:
            os.unlink(src)
            shutil.rmtree(tmp, ignore_errors=True)

    def test_download_file_progress(self):
        with tempfile.NamedTemporaryFile(delete=False) as f:
            f.write(b"data" * 100)
            src = f.name
        tmp = tempfile.mkdtemp(prefix="upd_")
        try:
            dst = os.path.join(tmp, "out.bin")
            calls = []
            updater.download_file(Path(src).as_uri(), dst, lambda d, t: calls.append((d, t)))
            self.assertGreater(len(calls), 0)
            self.assertEqual(calls[-1][0], os.path.getsize(src))
        finally:
            os.unlink(src)
            shutil.rmtree(tmp, ignore_errors=True)


class TestInstallGuard(unittest.TestCase):
    def test_install_update_raises_in_dev(self):
        with mock.patch.object(updater.sys, "frozen", False, create=True):
            with self.assertRaises(updater.UpdateError):
                updater.install_update({}, "path")

    def test_mac_app_bundle(self):
        cases = [
            ("/Applications/CosechaMedia.app/Contents/MacOS/CosechaMedia", "CosechaMedia.app"),
            ("/usr/local/bin/CosechaMedia", None),
        ]
        for exe, expected_tail in cases:
            with mock.patch.object(updater.sys, "executable", exe):
                bundle = updater._mac_app_bundle()
                if expected_tail is None:
                    self.assertIsNone(bundle)
                else:
                    self.assertIsNotNone(bundle)
                    self.assertTrue(bundle.endswith(expected_tail))


if __name__ == "__main__":
    unittest.main()
