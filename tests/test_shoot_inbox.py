import contextlib
import io
import json
import os
import shutil
import socket
import tempfile
import time
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


class TestWifiCacheDir(unittest.TestCase):
    def test_cache_dir_under_inbox(self):
        tmp = tempfile.mkdtemp(prefix="cache_")
        try:
            dbm = DatabaseManager(db_path=os.path.join(tmp, "test.db"))
            out = inboxmod.wifi_cache_dir("Alice Gómez", db=dbm)
            self.assertEqual(out, os.path.join(tmp, "inbox", "Alice Gómez"))
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_cache_dir_sanitizes_dangerous_name(self):
        tmp = tempfile.mkdtemp(prefix="cache_")
        try:
            dbm = DatabaseManager(db_path=os.path.join(tmp, "test.db"))
            out = inboxmod.wifi_cache_dir("../evil", db=dbm)
            self.assertNotIn("..", os.path.basename(out))
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


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
        self.assertIn(b"type=\"file\" multiple", body)
        self.assertNotIn(b"webkitdirectory", body)
        self.assertIn("misma red WiFi".encode(), body)

    def test_folder_mode_page_offers_whole_folder(self):
        self.server.folder_mode = True
        body = urlopen(f"{self.base}/?src={self.alice['name']}", timeout=10).read()
        self.assertIn(b"webkitdirectory", body)
        self.assertIn(b"carpeta", body)

    def test_health(self):
        body = urlopen(f"{self.base}/health", timeout=10).read()
        self.assertEqual(json.loads(body)["ok"], True)

    def test_client_reset_connection_is_silent(self):
        """Un cliente que aborta la conexión a mitad de un request no debe
        imprimir tracebacks en stderr (ni tumbar el servidor)."""
        for _ in range(3):
            s = socket.create_connection(("127.0.0.1", self.server.port), timeout=5)
            s.sendall(b"G")  # línea de request incompleta
            # Abort close (RST): el servidor verá ConnectionResetError al leer.
            s.setsockopt(socket.SOL_SOCKET, socket.SO_LINGER,
                         b"\x01\x00\x00\x00\x00\x00\x00\x00")
            s.close()
            time.sleep(0.2)
        captured = io.StringIO()
        with contextlib.redirect_stderr(captured):
            self.assertEqual(
                json.loads(urlopen(f"{self.base}/health", timeout=10).read())["ok"],
                True)
        self.assertNotIn("Traceback", captured.getvalue())
        self.assertNotIn("Exception occurred", captured.getvalue())

    def test_upload_stores_file_in_sender_cache(self):
        resp = self._upload(self.alice["name"], self.alice["token"], "VID_1.mp4", b"content")
        self.assertEqual(resp.status, 200)
        data = json.loads(resp.read())
        self.assertTrue(data["ok"])
        expected_dir = inboxmod.wifi_cache_dir("Alice", db=self.db)
        expected = os.path.join(expected_dir, "VID_1.mp4")
        self.assertTrue(os.path.exists(expected), expected)
        with open(expected, "rb") as f:
            self.assertEqual(f.read(), b"content")
        self.assertFalse(os.path.exists(expected + ".part"))
        self.assertEqual(self.received, [("Alice", expected, len(b"content"))])

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
        expected_dir = inboxmod.wifi_cache_dir("Alice", db=self.db)
        self.assertTrue(os.path.exists(os.path.join(expected_dir, "escape.mp4")))

    def test_upload_preserves_relative_path_in_folder_mode(self):
        self.server.folder_mode = True
        url = (f"{self.base}/upload?src={self.alice['name']}"
               f"&token={self.alice['token']}"
               f"&name={('DCIM/100MEDIA/VID_5.mp4').replace('/', '%2F')}")
        req = Request(url, data=b"f", method="POST")
        req.add_header("Content-Type", "application/octet-stream")
        self.assertEqual(urlopen(req, timeout=10).status, 200)
        expected = os.path.join(
            inboxmod.wifi_cache_dir("Alice", db=self.db),
            "DCIM", "100MEDIA", "VID_5.mp4")
        self.assertTrue(os.path.exists(expected), expected)

    def test_duplicate_names_get_unique_suffix(self):
        for _ in range(2):
            self._upload(self.alice["name"], self.alice["token"], "same.mp4", b"a")
        expected_dir = inboxmod.wifi_cache_dir("Alice", db=self.db)
        self.assertTrue(os.path.exists(os.path.join(expected_dir, "same.mp4")))
        self.assertTrue(os.path.exists(os.path.join(expected_dir, "same (1).mp4")))

    def test_url_for_sender_contains_token(self):
        url = self.server.url_for_sender("Alice")
        self.assertIn("src=Alice", url)
        self.assertIn(f"token={self.alice['token']}", url)


class TestUploadHandlerConnectionErrors(unittest.TestCase):
    """``_UploadHandler.handle`` debe tragar los errores de conexión que el
    navegador provoca al abortar la descarga (ConnectionResetError /
    BrokenPipeError / timeout), que si no se convierten en tracebacks de
    "Exception occurred during processing of request"."""

    def _handler_with_failing_read(self, exc):
        handler = inboxmod._UploadHandler.__new__(inboxmod._UploadHandler)

        class FakeServer:
            pass

        handler.server = FakeServer()
        handler.connection = object()
        handler.close_connection = True
        handler.log_message = lambda *a, **k: None

        def boom():
            raise exc

        handler.handle_one_request = boom
        return handler

    def test_connection_reset_is_swallowed(self):
        h = self._handler_with_failing_read(
            ConnectionResetError(10054, "Se ha forzado la interrupción"))
        h.handle()  # no debe propagar

    def test_broken_pipe_is_swallowed(self):
        h = self._handler_with_failing_read(
            BrokenPipeError(32, "Broken pipe"))
        h.handle()

    def test_socket_timeout_is_swallowed(self):
        h = self._handler_with_failing_read(socket.timeout("timed out"))
        h.handle()

    def test_other_errors_still_propagate(self):
        h = self._handler_with_failing_read(RuntimeError("real error"))
        with self.assertRaises(RuntimeError):
            h.handle()


class TestInboxRoot(unittest.TestCase):
    def test_inbox_root_next_to_db(self):
        tmp = tempfile.mkdtemp(prefix="inbox_")
        try:
            dbm = DatabaseManager(db_path=os.path.join(tmp, "test.db"))
            self.assertEqual(
                inboxmod.inbox_root(dbm), os.path.join(tmp, "inbox"))
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


class TestShootInboxLateCallback(unittest.TestCase):
    """El callback debe registrarse aunque sea después de ``start()`` (así lo
    hace la ventana principal con ``attach_server``)."""

    def test_callback_attached_after_start_still_receives(self):
        tmp = tempfile.mkdtemp(prefix="inbox_late_")
        try:
            dbm = DatabaseManager(db_path=os.path.join(tmp, "test.db"))
            alice_id = dbm.add_inbox_sender("Alice")
            alice = next(s for s in dbm.list_inbox_senders() if s["id"] == alice_id)
            received = []
            server = inboxmod.ShootInboxServer(
                root=os.path.join(tmp, "inbox"), db=dbm,
                host="127.0.0.1", port=0)
            server.start()
            server.on_file_received = lambda a, p, s: received.append((a, p, s))
            base = f"http://127.0.0.1:{server.port}"
            try:
                url = (f"{base}/upload?src={alice['name']}"
                       f"&token={alice['token']}&name=VID.mp4")
                req = Request(url, data=b"data", method="POST")
                req.add_header("Content-Type", "application/octet-stream")
                self.assertEqual(urlopen(req, timeout=10).status, 200)
            finally:
                server.stop()
            self.assertEqual(len(received), 1)
            self.assertEqual(received[0][0], "Alice")
            self.assertTrue(os.path.exists(received[0][1]))
            self.assertEqual(received[0][2], len(b"data"))
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_callback_replaced_live_takes_effect(self):
        tmp = tempfile.mkdtemp(prefix="inbox_live_")
        try:
            dbm = DatabaseManager(db_path=os.path.join(tmp, "test.db"))
            alice_id = dbm.add_inbox_sender("Alice")
            alice = next(s for s in dbm.list_inbox_senders() if s["id"] == alice_id)
            first = []
            second = []
            server = inboxmod.ShootInboxServer(
                root=os.path.join(tmp, "inbox"), db=dbm,
                on_file_received=lambda a, p, s: first.append(a),
                host="127.0.0.1", port=0)
            server.start()
            server.on_file_received = lambda a, p, s: second.append(a)
            base = f"http://127.0.0.1:{server.port}"
            try:
                url = (f"{base}/upload?src={alice['name']}"
                       f"&token={alice['token']}&name=VID.mp4")
                req = Request(url, data=b"data", method="POST")
                req.add_header("Content-Type", "application/octet-stream")
                self.assertEqual(urlopen(req, timeout=10).status, 200)
            finally:
                server.stop()
            self.assertEqual(first, [])
            self.assertEqual(second, ["Alice"])
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


class TestInboxSenders(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="senders_")
        self.db = DatabaseManager(db_path=os.path.join(self.tmp, "test.db"))

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_sender_crud_with_tokens(self):
        sid = self.db.add_inbox_sender("Alice", "Rodaje 1")
        rows = self.db.list_inbox_senders()
        self.assertEqual(len(rows), 1)
        self.assertTrue(rows[0]["token"])
        self.assertGreater(len(rows[0]["token"]), 8)
        self.assertEqual(rows[0]["location"], "Rodaje 1")

        self.db.update_inbox_sender(sid, "Alice 2", "Rodaje 2")
        rows = self.db.list_inbox_senders()
        self.assertEqual(rows[0]["name"], "Alice 2")
        self.assertEqual(rows[0]["location"], "Rodaje 2")

        self.db.delete_inbox_sender(sid)
        self.assertEqual(self.db.list_inbox_senders(), [])

    def test_sender_default_location_empty(self):
        self.db.add_inbox_sender("Bob")
        self.assertEqual(self.db.list_inbox_senders()[0]["location"], "")

    def test_sender_location_migration_from_old_schema(self):
        import sqlite3
        db_path = os.path.join(self.tmp, "old_schema.db")
        conn = sqlite3.connect(db_path)
        conn.execute("""CREATE TABLE inbox_senders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            token TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )""")
        conn.commit()
        conn.close()
        dbm = DatabaseManager(db_path=db_path)
        dbm.add_inbox_sender("Alice", "Rodaje")
        rows = dbm.list_inbox_senders()
        self.assertEqual(rows[0]["location"], "Rodaje")

    def test_senders_have_unique_tokens(self):
        a = self.db.add_inbox_sender("A")
        b = self.db.add_inbox_sender("B")
        rows = {r["id"]: r for r in self.db.list_inbox_senders()}
        self.assertNotEqual(rows[a]["token"], rows[b]["token"])


if __name__ == "__main__":
    unittest.main()
