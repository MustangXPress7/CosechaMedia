import json
import os
import shutil
import tempfile
import unittest
from urllib.request import Request, urlopen, HTTPError

from app.core import shoot_inbox as inboxmod
from app.core.db import DatabaseManager


class TestSanitizers(unittest.TestCase):
    def test_sanitize_alias_keeps_accents_and_spaces(self):
        self.assertEqual(inboxmod.sanitize_alias("Alice Gómez"), "Alice Gómez")

    def test_sanitize_alias_removes_dangerous_chars(self):
        cleaned = inboxmod.sanitize_alias("a/b\\c:d")
        self.assertNotIn("/", cleaned)
        self.assertNotIn("\\", cleaned)
        self.assertNotIn(":", cleaned)

    def test_sanitize_alias_empty_fallback(self):
        self.assertEqual(inboxmod.sanitize_alias(""), "desconocido")
        self.assertEqual(inboxmod.sanitize_alias("../.."), "desconocido")

    def test_sanitize_relative_path_blocks_traversal(self):
        self.assertEqual(inboxmod.sanitize_relative_path("../../etc/passwd"), "etc/passwd")
        self.assertEqual(inboxmod.sanitize_relative_path("..\\..\\Windows\\x"), "Windows/x")
        self.assertEqual(inboxmod.sanitize_relative_path("DCIM/VID_1.mp4"), "DCIM/VID_1.mp4")


class TestShootInboxServer(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="inbox_")
        self.db = DatabaseManager(db_path=os.path.join(self.tmp, "test.db"))
        self.root = os.path.join(self.tmp, "inbox")
        self.alice_id = self.db.add_inbox_sender("Alice")
        self.alice = next(s for s in self.db.list_inbox_senders() if s["id"] == self.alice_id)
        self.received = []
        self.server = inboxmod.ShootInboxServer(
            root=self.root, db=self.db,
            on_file_received=lambda a, p, s: self.received.append((a, p, s)),
            host="127.0.0.1", port=0,
        )
        self.server.start()
        self.base = f"http://127.0.0.1:{self.server.port}"
        self.addCleanup(self._stop)

    def _stop(self):
        self.server.stop()
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _upload(self, src, token, name, data=b"hola"):
        url = (f"{self.base}/upload?src={src}&token={token}"
               f"&name={name.replace('/', '%2F')}")
        req = Request(url, data=data, method="POST")
        req.add_header("Content-Type", "application/octet-stream")
        return urlopen(req, timeout=10)

    def test_serves_page_with_alias(self):
        body = urlopen(f"{self.base}/?src={self.alice['name']}", timeout=10).read()
        self.assertIn("Alice".encode(), body)
        self.assertIn("webkitdirectory".encode(), body)

    def test_health(self):
        body = urlopen(f"{self.base}/health", timeout=10).read()
        self.assertEqual(json.loads(body)["ok"], True)

    def test_upload_stores_file_with_date_folder(self):
        resp = self._upload(self.alice["name"], self.alice["token"], "VID_1.mp4", b"content")
        self.assertEqual(resp.status, 200)
        data = json.loads(resp.read())
        self.assertTrue(data["ok"])
        import glob
        hits = glob.glob(os.path.join(self.root, "Alice", "????-??-??", "VID_1.mp4"))
        self.assertEqual(len(hits), 1)
        with open(hits[0], "rb") as f:
            self.assertEqual(f.read(), b"content")
        self.assertFalse(os.path.exists(hits[0] + ".part"))
        self.assertEqual(self.received, [("Alice", hits[0], len(b"content"))])

    def test_upload_rejects_bad_token(self):
        with self.assertRaises(HTTPError) as ctx:
            self._upload(self.alice["name"], "wrong-token", "x.mp4", b"x")
        self.assertEqual(ctx.exception.code, 403)

    def test_upload_rejects_unknown_sender(self):
        with self.assertRaises(HTTPError) as ctx:
            self._upload("Ghost", "tok", "x.mp4", b"x")
        self.assertEqual(ctx.exception.code, 403)

    def test_upload_sanitizes_filename(self):
        self._upload(self.alice["name"], self.alice["token"], "../escape.mp4", b"y")
        import glob
        hits = glob.glob(os.path.join(self.root, "Alice", "????-??-??", "escape.mp4"))
        self.assertEqual(len(hits), 1)

    def test_duplicate_names_get_unique_suffix(self):
        for _ in range(2):
            self._upload(self.alice["name"], self.alice["token"], "same.mp4", b"a")
        import glob
        hits = glob.glob(os.path.join(self.root, "Alice", "????-??-??", "same.mp4"))
        plus = glob.glob(os.path.join(self.root, "Alice", "????-??-??", "same (1).mp4"))
        self.assertEqual(len(hits), 1)
        self.assertEqual(len(plus), 1)

    def test_url_for_sender_contains_token(self):
        url = self.server.url_for_sender("Alice")
        self.assertIn("src=Alice", url)
        self.assertIn(f"token={self.alice['token']}", url)


class TestInboxRoot(unittest.TestCase):
    def test_inbox_root_next_to_db(self):
        tmp = tempfile.mkdtemp(prefix="inbox_")
        try:
            dbm = DatabaseManager(db_path=os.path.join(tmp, "test.db"))
            self.assertEqual(
                inboxmod.inbox_root(dbm), os.path.join(tmp, "inbox"))
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


class TestInboxSenders(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="senders_")
        self.db = DatabaseManager(db_path=os.path.join(self.tmp, "test.db"))

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_sender_crud_with_tokens(self):
        sid = self.db.add_inbox_sender("Alice")
        rows = self.db.list_inbox_senders()
        self.assertEqual(len(rows), 1)
        self.assertTrue(rows[0]["token"])
        self.assertGreater(len(rows[0]["token"]), 8)

        self.db.rename_inbox_sender(sid, "Alice 2")
        self.assertEqual(self.db.list_inbox_senders()[0]["name"], "Alice 2")

        self.db.delete_inbox_sender(sid)
        self.assertEqual(self.db.list_inbox_senders(), [])

    def test_senders_have_unique_tokens(self):
        a = self.db.add_inbox_sender("A")
        b = self.db.add_inbox_sender("B")
        rows = {r["id"]: r for r in self.db.list_inbox_senders()}
        self.assertNotEqual(rows[a]["token"], rows[b]["token"])


if __name__ == "__main__":
    unittest.main()
