"""Pruebas de la ingesta WiFi (PairDrop) como origen integrado en la tabla.

Cobertura:
- Abrir el panel WiFi registra una sesión/fila por remitente (caché local).
- El panel es una ventana no modal (Qt.Window) y no bloquea la app.
- Al recibir un archivo se dispara ``handle_new_file`` del ingestor.
- ``_open_wifi_panel`` arranca el servidor/panel solo con proyecto activo.
- ``_delete_saved_source`` borra dispositivos guardados (MTP y FTP) desde el
  diálogo Añadir origen, con confirmación veraz y default No.
- Eliminar un origen desde la tabla borra sesión y remitente WiFi.
"""
import os
import tempfile
import shutil
import unittest
from unittest import mock

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QTableWidgetItem

import app.ui.main_window as mw
import app.core.ingestor as ingestor_module
from app.core.db import DatabaseManager, WIFI_DEVICE_ID


class TestWifiSource(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="wifi_src_")
        self.dest = os.path.join(self.tmp, "dest")
        os.makedirs(self.dest)

        self._orig_db = mw.db
        self._orig_ing_db = ingestor_module.db
        self._orig_notif = mw.NotificationManager
        self.db = DatabaseManager(db_path=os.path.join(self.tmp, "wifisrc.db"))
        mw.db = self.db
        ingestor_module.db = self.db

        # La caché WiFi resuelve contra la misma DB que el resto del test.
        from app.core import shoot_inbox as inboxmod
        self._orig_inbox_db = inboxmod._default_db
        inboxmod._default_db = self.db

        class StubNotif:
            def notify_ingest_complete(self, stats): pass
            def notify_ingest_stopped(self): pass
            def notify_ingest_failed(self, stats=None): pass

        mw.NotificationManager = StubNotif

        conn = self.db.get_connection()
        cursor = conn.cursor()
        cursor.execute("INSERT INTO projects (name, root_path) VALUES ('P', ?)", (self.dest,))
        self.pid = cursor.lastrowid
        conn.commit()
        conn.close()

        self.db.add_inbox_sender("Alice")
        self.db.add_inbox_sender("Bob")

        self.window = mw.MainWindow()
        self.window.current_project_id = self.pid
        self.window.dest_root = self.dest

        # Evita arrancar servidores/threads reales: sustituye el servidor.
        self._fake_server = _FakeServer()
        self._orig_ensure = mw.MainWindow._ensure_wifi_server
        mw.MainWindow._ensure_wifi_server = lambda self_: self._attach_fake(self_)
        self._orig_show = mw.MainWindow._show_wifi_panel
        mw.MainWindow._show_wifi_panel = lambda self_: None  # no abrir ventana real
        self._orig_prompt = mw.MainWindow._prompt_wifi_sender
        mw.MainWindow._prompt_wifi_sender = lambda self_: "NewSender"  # no abrir diálogo real

    def _attach_fake(self, window):
        window._wifi_server = self._fake_server
        return True

    def tearDown(self):
        from app.core import shoot_inbox as inboxmod
        inboxmod._default_db = self._orig_inbox_db
        mw.MainWindow._ensure_wifi_server = self._orig_ensure
        mw.MainWindow._show_wifi_panel = self._orig_show
        mw.MainWindow._prompt_wifi_sender = self._orig_prompt
        self.window.close()
        mw.db = self._orig_db
        ingestor_module.db = self._orig_ing_db
        mw.NotificationManager = self._orig_notif
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_open_wifi_panel_with_project_starts_server(self):
        # Test 3 (gating): con proyecto activo, _open_wifi_panel arranca el
        # servidor y muestra el panel (mocks del setUp).
        self.window._open_wifi_panel()
        self.assertIs(self.window._wifi_server, self._fake_server)

    def test_open_wifi_panel_without_project_is_noop(self):
        # Test 3 (gating): sin proyecto, _open_wifi_panel no arranca nada.
        self.window.current_project_id = None
        with mock.patch.object(mw.MainWindow, "_ensure_wifi_server") as ensure:
            self.window._open_wifi_panel()
            ensure.assert_not_called()

    def test_delete_saved_device_confirmed_deletes(self):
        # Test 2: borrar un dispositivo guardado con confirmación aprobada
        # borra sus sesiones vía db.delete_device y devuelve True.
        cache = os.path.join(self.tmp, "device_cache", "abc123", "DCIM")
        os.makedirs(cache, exist_ok=True)
        sid = self.db.create_session(self.pid, "MTP", "2026-01-01", "active",
                                     source_path=cache)
        self.db.update_session_config(sid, device_id="mtp:pnp123",
                                      device_folder="DCIM")
        self.assertEqual(len(self.db.get_devices()), 1)
        with mock.patch.object(mw.QMessageBox, "question",
                               return_value=mw.QMessageBox.Yes):
            result = self.window._delete_saved_source("device", "mtp:pnp123")
        self.assertTrue(result)
        self.assertEqual(self.db.get_devices(), [])

    def test_delete_saved_device_rejected_keeps(self):
        # Test 2: con confirmación rechazada no se borra y devuelve False.
        cache = os.path.join(self.tmp, "device_cache", "abc123", "DCIM")
        os.makedirs(cache, exist_ok=True)
        sid = self.db.create_session(self.pid, "MTP", "2026-01-01", "active",
                                     source_path=cache)
        self.db.update_session_config(sid, device_id="mtp:pnp123",
                                      device_folder="DCIM")
        with mock.patch.object(mw.QMessageBox, "question",
                               return_value=mw.QMessageBox.No):
            result = self.window._delete_saved_source("device", "mtp:pnp123")
        self.assertFalse(result)
        self.assertEqual(len(self.db.get_devices()), 1)

    def test_delete_saved_ftp_device_deletes_profile(self):
        # Test 2: para un dispositivo ftp:<id>, además de borrar el dispositivo
        # se borra el perfil FTP asociado (db.delete_ftp_profile).
        from app.core import ftp as ftpmod
        pid = self.db.add_ftp_profile("Serv", "192.168.1.50")
        dev_id = ftpmod.device_key(pid)
        cache = os.path.join(self.tmp, "device_cache", "abc123", "DCIM")
        os.makedirs(cache, exist_ok=True)
        sid = self.db.create_session(self.pid, "FTP", "2026-01-01", "active",
                                     source_path=cache)
        self.db.update_session_config(sid, device_id=dev_id, device_folder="DCIM")
        with mock.patch.object(mw.QMessageBox, "question",
                               return_value=mw.QMessageBox.Yes):
            with mock.patch.object(self.db, "delete_ftp_profile",
                                   wraps=self.db.delete_ftp_profile) as dfp:
                result = self.window._delete_saved_source("device", dev_id)
        self.assertTrue(result)
        dfp.assert_called_once_with(pid)
        self.assertEqual(self.db.get_devices(), [])

    def test_panel_is_non_modal_window(self):
        from app.ui.wifi_panel import ShootInboxPanel
        panel = ShootInboxPanel(self.window)
        self.assertTrue(bool(panel.windowFlags() & Qt.Window))
        self.assertFalse(panel.isModal())

    def test_panel_shows_sender_url_and_copy_button_copies_it(self):
        from PySide6.QtWidgets import QApplication
        from app.ui.wifi_panel import ShootInboxPanel
        panel = ShootInboxPanel(self.window)
        panel.attach_server(self._fake_server)
        panel.select_sender("Alice")
        expected = self._fake_server.url_for_sender("Alice")
        self.assertEqual(panel.url_label.text(), expected)
        self.assertTrue(panel.copy_btn.isEnabled())
        panel.copy_btn.click()
        self.assertEqual(QApplication.clipboard().text(), expected)

    def test_copy_button_disabled_without_url(self):
        from app.ui.wifi_panel import ShootInboxPanel
        panel = ShootInboxPanel(self.window)
        panel._clear_qr()
        self.assertFalse(panel.copy_btn.isEnabled())

    def test_sync_wifi_sessions_creates_one_per_sender(self):
        from app.core import shoot_inbox as inboxmod
        self.window._open_wifi_panel()
        sessions = self.db.list_wifi_sessions(self.pid)
        self.assertEqual(
            sorted(s["device_folder"] for s in sessions),
            ["Alice", "Bob"])
        for s in sessions:
            self.assertEqual(s["source_path"], inboxmod.wifi_cache_dir(s["nombre_dispositivo"]))
            self.assertIn(s["source_path"], self.window._source_paths)
        self.assertEqual(self.window.source_list.rowCount(), len(sessions))

    def test_sync_wifi_sessions_removes_deleted_sender(self):
        from app.core import shoot_inbox as inboxmod
        self.window._open_wifi_panel()
        self.assertEqual(len(self.db.list_wifi_sessions(self.pid)), 2)
        bob = next(s for s in self.db.list_inbox_senders() if s["name"] == "Bob")
        self.db.delete_inbox_sender(bob["id"])
        self.window._sync_wifi_sessions()
        sessions = self.db.list_wifi_sessions(self.pid)
        self.assertEqual([s["device_folder"] for s in sessions], ["Alice"])

    def test_file_received_triggers_handle_new_file(self):
        from app.core import shoot_inbox as inboxmod
        self.window._open_wifi_panel()
        cache = inboxmod.wifi_cache_dir("Alice")
        os.makedirs(cache, exist_ok=True)
        fpath = os.path.join(cache, "clip.mp4")
        with open(fpath, "wb") as f:
            f.write(b"x")
        with mock.patch.object(mw.Ingestor, "handle_new_file") as hnf:
            self.window._on_wifi_file_received("Alice", fpath, 1)
            hnf.assert_called_once_with(fpath)

    def test_file_received_creates_ingestor_lazily(self):
        from app.core import shoot_inbox as inboxmod
        self.window._open_wifi_panel()
        # _open_wifi_panel arranca un ingestor por sesión y escanea la caché.
        sessions = self.db.list_wifi_sessions(self.pid)
        self.assertEqual(
            set(self.window._wifi_ingestors.keys()),
            {s["id"] for s in sessions})
        alice_sid = next(s["id"] for s in sessions if s["device_folder"] == "Alice")
        cache = inboxmod.wifi_cache_dir("Alice")
        os.makedirs(cache, exist_ok=True)
        fpath = os.path.join(cache, "clip.mp4")
        with open(fpath, "wb") as f:
            f.write(b"x")
        with mock.patch.object(mw.Ingestor, "handle_new_file") as hnf:
            self.window._on_wifi_file_received("Alice", fpath, 1)
            hnf.assert_called_once_with(fpath)
        self.assertIn(alice_sid, self.window._wifi_ingestors)

    def _emit_all(self):
        from PySide6.QtWidgets import QApplication
        QApplication.processEvents()
        QApplication.processEvents()

    def test_qr_ingest_registers_status_in_table(self):
        """Bug 1: un archivo recibido por QR registra su estado en la tabla,
        aunque la tabla tenga ordenación activa."""
        import time
        from app.core import shoot_inbox as inboxmod
        orig_meta = mw.metadata_engine
        orig_ing_meta = ingestor_module.metadata_engine
        mw.metadata_engine = _FakeMeta()
        ingestor_module.metadata_engine = _FakeMeta()
        try:
            self.window._open_wifi_panel()
            cache = inboxmod.wifi_cache_dir("Alice", db=self.db)
            os.makedirs(cache, exist_ok=True)
            for name in ("b.mp4", "a.mp4"):
                fpath = os.path.join(cache, name)
                with open(fpath, "wb") as f:
                    f.write(b"fake-clip")
                self.window._on_wifi_file_received(
                    "Alice", fpath, os.path.getsize(fpath))
            done = 0
            deadline = time.time() + 15
            while time.time() < deadline:
                self._emit_all()
                for r in range(self.window.table.rowCount()):
                    name_item = self.window.table.item(r, 0)
                    if name_item is None:
                        continue
                    status = self.window.table.item(r, 2).text()
                    if status not in ("", self.window.tr("Copiando...")):
                        done += 1
                if done >= 2:
                    break
                time.sleep(0.05)
            # Ambas filas deben tener estado "Completado" (no mezclarse).
            for r in range(self.window.table.rowCount()):
                name_item = self.window.table.item(r, 0)
                if name_item is None:
                    continue
                status = self.window.table.item(r, 2).text()
                self.assertEqual(status, self.window.tr("Completado"),
                                 f"{name_item.text()} sin estado correcto")
        finally:
            mw.metadata_engine = orig_meta
            ingestor_module.metadata_engine = orig_ing_meta

    def test_wifi_panel_stop_toggles_to_resume(self):
        """Bug 6: el botón Detener/Reanudar del panel funciona como toggle."""
        from app.ui.wifi_panel import ShootInboxPanel
        panel = ShootInboxPanel(self.window)
        self._fake_server.running = True
        panel.attach_server(self._fake_server)
        self.assertEqual(panel.stop_btn.text(), panel.tr("Detener"))
        calls = []
        panel.stop_requested.connect(lambda: calls.append("stop"))
        panel.resume_requested.connect(lambda: calls.append("resume"))
        panel._on_stop_clicked()
        self.assertEqual(calls, ["stop"])
        self._fake_server.running = False
        panel._refresh_server_status()
        self.assertEqual(panel.stop_btn.text(), panel.tr("Reanudar"))
        panel._on_stop_clicked()
        self.assertEqual(calls, ["stop", "resume"])
        self._fake_server.running = True
        panel._refresh_server_status()
        self.assertEqual(panel.stop_btn.text(), panel.tr("Detener"))

    def test_resume_wifi_reception_restarts_ingestion(self):
        """Bug 6: reanudar tras Detener vuelve a arrancar los ingestores."""
        self.window._open_wifi_panel()
        sessions = self.db.list_wifi_sessions(self.pid)
        self.assertEqual(
            set(self.window._wifi_ingestors.keys()),
            {s["id"] for s in sessions})
        self.window._stop_wifi_reception()
        self.assertEqual(self.window._wifi_ingestors, {})
        self.assertIsNone(self.window._wifi_server)
        self._fake_server.running = True  # servidor nuevo
        self.window._resume_wifi_reception()
        self.assertEqual(
            set(self.window._wifi_ingestors.keys()),
            {s["id"] for s in sessions})

    def test_wifi_session_ignores_sender_location(self):
        """Bug 4: la ubicación guardada del dispositivo no se propaga entre
        proyectos (cada proyecto vuelca a su propia ruta maestra)."""
        conn = self.db.get_connection()
        conn.execute("UPDATE inbox_senders SET location = ? WHERE name = 'Alice'",
                     (os.path.join(self.tmp, "otro-proyecto"),))
        conn.commit()
        conn.close()
        self.window._open_wifi_panel()
        session = next(s for s in self.db.list_wifi_sessions(self.pid)
                       if s["device_folder"] == "Alice")
        self.assertIsNone(session["destination_override"])

    def test_sync_wifi_sessions_preserves_destination_override(self):
        """Sincronizar las sesiones WiFi no borra el destino personalizado
        configurado por el usuario en una sesión."""
        from app.core import shoot_inbox as inboxmod
        self.window._open_wifi_panel()
        alice = next(s for s in self.db.list_wifi_sessions(self.pid)
                     if s["device_folder"] == "Alice")
        custom = os.path.join(self.tmp, "destino-propio")
        self.db.update_session_config(alice["id"], destination_override=custom)
        self.window._sync_wifi_sessions()
        alice2 = next(s for s in self.db.list_wifi_sessions(self.pid)
                      if s["device_folder"] == "Alice")
        self.assertEqual(alice2["destination_override"], custom)

    def test_managed_session_detection(self):
        """Las sesiones WiFi/FTP son gestionadas; las manuales no."""
        from app.core import ftp as ftpmod
        self.window._open_wifi_panel()
        alice = next(s for s in self.db.get_sessions(self.pid)
                     if s["device_folder"] == "Alice")
        self.assertTrue(self.window._is_managed_session(alice))

        pid = self.db.add_ftp_profile("Serv", "192.168.1.50")
        dev_id = ftpmod.device_key(pid)
        cache = os.path.join(self.tmp, "cache-ftp")
        os.makedirs(cache, exist_ok=True)
        sid = self.db.create_session(self.pid, "FTP", "2026-01-01", "active",
                                     source_path=cache)
        self.db.update_session_config(sid, device_id=dev_id)
        ftp_sess = next(s for s in self.db.get_sessions(self.pid)
                        if s.get("device_id") == dev_id)
        self.assertTrue(self.window._is_managed_session(ftp_sess))

        manual = os.path.join(self.tmp, "manual")
        os.makedirs(manual, exist_ok=True)
        self.db.create_session(self.pid, "Manual", "2026-01-01", "active",
                               source_path=manual)
        man = next(s for s in self.db.get_sessions(self.pid)
                   if s.get("source_path") == manual)
        self.assertFalse(self.window._is_managed_session(man))

    def test_is_managed_source_path(self):
        from app.core import shoot_inbox as inboxmod
        cache = inboxmod.wifi_cache_dir("Alice", db=self.db)
        self.assertTrue(self.window._is_managed_source_path(cache))
        self.assertTrue(self.window._is_managed_source_path(
            os.path.join(cache, "x.mp4")))
        self.assertFalse(self.window._is_managed_source_path(self.dest))
        self.assertFalse(self.window._is_managed_source_path(""))

    def test_format_candidates_exclude_managed_cache(self):
        """El formateo posterior excluye cachés gestionadas (WiFi) y solo
        considera unidades extraíbles reales."""
        from app.core import shoot_inbox as inboxmod
        self.window._open_wifi_panel()
        manual = os.path.join(self.tmp, "manual")
        os.makedirs(manual, exist_ok=True)
        self.db.create_session(self.pid, "Manual", "2026-01-01", "active",
                               source_path=manual)
        self.window._populate_source_paths_from_sessions()
        cache = inboxmod.wifi_cache_dir("Alice", db=self.db)
        with mock.patch.object(mw, "is_removable_drive",
                               side_effect=lambda p: p == manual):
            candidates = self.window._format_candidate_paths()
            self.assertEqual(candidates, [manual])
            self.assertNotIn(cache, candidates)
        # Solo-WiFi (nada extraíble): el checkbox queda deshabilitado.
        with mock.patch.object(mw, "is_removable_drive", return_value=False):
            self.window._update_format_sources_state()
            self.assertFalse(self.window.chk_format_sources.isEnabled())
            self.assertFalse(self.window.combo_format_mode.isEnabled())

    def test_format_candidates_enabled_with_removable_drive(self):
        manual = os.path.join(self.tmp, "manual")
        os.makedirs(manual, exist_ok=True)
        self.db.create_session(self.pid, "Manual", "2026-01-01", "active",
                               source_path=manual)
        self.window._populate_source_paths_from_sessions()
        with mock.patch.object(mw, "is_removable_drive", return_value=True):
            self.window._update_format_sources_state()
            self.assertTrue(self.window.chk_format_sources.isEnabled())

    def test_session_source_shows_wifi_origin(self):
        """El origen de una sesión WiFi muestra el remitente (sin prefijo
        emoji) y permite cambiar el origen desde el selector."""
        from app.core import shoot_inbox as inboxmod
        self.window._open_wifi_panel()
        alice = next(s for s in self.db.list_wifi_sessions(self.pid)
                     if s["device_folder"] == "Alice")
        idx = self.window.sessions_combo.findData(alice["id"])
        self.assertGreaterEqual(idx, 0)
        self.window._on_session_selected(idx)
        self.assertFalse(self.window._btn_browse_sess_src.isHidden())
        self.assertIn(self.window.tr("Origen automático:"),
                      self.window.session_src_label.toolTip())
        # El origen WiFi muestra el remitente sin prefijo emoji (icono aparte).
        self.assertIn("Alice", self.window.session_src_label.toolTip())
        self.assertNotIn("📶", self.window.session_src_label.toolTip())

    def test_session_source_shows_mtp_device_name(self):
        """Una sesión MTP muestra el nombre del dispositivo, no la ruta de
        la caché técnica (B-02)."""
        cache = os.path.join(self.tmp, "device_cache", "abc123", "DCIM")
        os.makedirs(cache, exist_ok=True)
        sid = self.db.create_session(self.pid, "Auto (Canon R5)",
                                     "2026-01-01", "active", source_path=cache)
        self.db.update_session_config(sid, device_id="mtp:pnp123",
                                      device_folder="DCIM",
                                       nombre_dispositivo="Canon R5")
        self.window._refresh_sessions_combo()
        idx = self.window.sessions_combo.findData(sid)
        self.assertGreaterEqual(idx, 0)
        self.window._on_session_selected(idx)
        tip = self.window.session_src_label.toolTip()
        self.assertIn(self.window.tr("Origen automático:"), tip)
        self.assertNotIn("📱", tip)
        self.assertIn("Canon R5", tip)
        self.assertNotIn(cache, tip)

    def test_session_source_editable_for_manual(self):
        manual = os.path.join(self.tmp, "manual")
        os.makedirs(manual, exist_ok=True)
        sid = self.db.create_session(self.pid, "Manual", "2026-01-01", "active",
                                     source_path=manual)
        self.window._refresh_sessions_combo()
        idx = self.window.sessions_combo.findData(sid)
        self.assertGreaterEqual(idx, 0)
        self.window._on_session_selected(idx)
        self.assertFalse(self.window._btn_browse_sess_src.isHidden())
        self.assertIn(self.window.tr("Origen:"),
                      self.window.session_src_label.toolTip())

    def test_bind_wifi_sender_converts_manual_session(self):
        from app.core import shoot_inbox as inboxmod
        manual = os.path.join(self.tmp, "manual")
        os.makedirs(manual, exist_ok=True)
        sid = self.db.create_session(self.pid, "Rodaje A", "2026-01-01", "active",
                                     source_path=manual)
        custom = os.path.join(self.tmp, "destino-propio")
        self.db.update_session_config(sid, destination_override=custom)
        self.window._bind_wifi_sender("Alice", session_id=sid)
        session = self.db.get_session(sid)
        self.assertEqual(session["device_id"], WIFI_DEVICE_ID)
        self.assertEqual(session["device_folder"], "Alice")
        self.assertEqual(session["nombre_dispositivo"], "Alice")
        self.assertEqual(session["source_path"], inboxmod.wifi_cache_dir("Alice"))
        self.assertEqual(session["name"], "Rodaje A")
        self.assertEqual(session["destination_override"], custom)
        self.assertEqual(session["enabled"], 1)
        wifi = [s for s in self.db.list_wifi_sessions(self.pid)
                if s["device_folder"] == "Alice"]
        self.assertEqual([s["id"] for s in wifi], [sid])

    def test_bind_wifi_sender_shared_keeps_other_binding(self):
        from app.core import shoot_inbox as inboxmod
        self.window._open_wifi_panel()
        alice = next(s for s in self.db.list_wifi_sessions(self.pid)
                     if s["device_folder"] == "Alice")
        manual = os.path.join(self.tmp, "manual")
        os.makedirs(manual, exist_ok=True)
        new_sid = self.db.create_session(self.pid, "Segunda", "2026-01-01",
                                         "active", source_path=manual)
        with mock.patch.object(mw.QMessageBox, "information"):
            self.window._bind_wifi_sender("Alice", session_id=new_sid)
        # El binding es aditivo: la sesión original conserva el origen y la
        # nueva también lo recibe (mismo remitente, otro destino).
        self.assertEqual(self.db.get_session(alice["id"])["device_id"],
                         WIFI_DEVICE_ID)
        new = self.db.get_session(new_sid)
        self.assertEqual(new["device_id"], WIFI_DEVICE_ID)
        self.assertEqual(new["source_path"], inboxmod.wifi_cache_dir("Alice"))
        wifi = [s for s in self.db.list_wifi_sessions(self.pid)
                if s["device_folder"] == "Alice"]
        self.assertEqual(len(wifi), 2)

    def test_bind_wifi_sender_switches_sender_in_session(self):
        """Cambiar el remitente de una sesión ligada la desliga del anterior."""
        from app.core import shoot_inbox as inboxmod
        self.window._open_wifi_panel()
        alice = next(s for s in self.db.list_wifi_sessions(self.pid)
                     if s["device_folder"] == "Alice")
        manual = os.path.join(self.tmp, "manual")
        os.makedirs(manual, exist_ok=True)
        new_sid = self.db.create_session(self.pid, "Segunda", "2026-01-01",
                                         "active", source_path=manual)
        with mock.patch.object(mw.QMessageBox, "information"):
            self.window._bind_wifi_sender("Alice", session_id=new_sid)
            # Ahora se cambia el origen de esa misma sesión a Bob.
            self.window._bind_wifi_sender("Bob", session_id=new_sid)
        self.assertEqual(self.db.get_session(alice["id"])["device_id"],
                         WIFI_DEVICE_ID)
        new = self.db.get_session(new_sid)
        self.assertEqual(new["device_id"], WIFI_DEVICE_ID)
        self.assertEqual(new["device_folder"], "Bob")
        self.assertEqual(new["source_path"], inboxmod.wifi_cache_dir("Bob"))
        # La sesión nueva dejó de estar ligada a Alice.
        alice_wifi = [s for s in self.db.list_wifi_sessions(self.pid)
                      if s["device_folder"] == "Alice"]
        self.assertEqual([s["id"] for s in alice_wifi], [alice["id"]])

    def test_assign_folder_detaches_managed_session(self):
        """Asignar una carpeta a una sesión WiFi la desliga del dispositivo."""
        from app.core import shoot_inbox as inboxmod
        self.window._open_wifi_panel()
        alice = next(s for s in self.db.list_wifi_sessions(self.pid)
                     if s["device_folder"] == "Alice")
        folder = os.path.join(self.tmp, "carpeta-propia")
        os.makedirs(folder, exist_ok=True)
        self.window.project_camera_detection_mode = "manual"
        with mock.patch.object(mw, "is_removable_drive", return_value=False), \
             mock.patch.object(mw.QInputDialog, "getText", return_value=("TestCam", True)):
            self.window._assign_session_folder(alice["id"], folder)
        session = self.db.get_session(alice["id"])
        self.assertFalse(session["device_id"])
        self.assertFalse(session["device_folder"])
        self.assertEqual(session["source_path"], folder)
        # Ya no cuenta como sesión WiFi del remitente.
        alice_wifi = [s for s in self.db.list_wifi_sessions(self.pid)
                      if s["device_folder"] == "Alice"]
        self.assertEqual(alice_wifi, [])

    def test_file_received_fans_out_to_all_sessions(self):
        from app.core import shoot_inbox as inboxmod
        self.window._open_wifi_panel()
        manual = os.path.join(self.tmp, "manual")
        os.makedirs(manual, exist_ok=True)
        new_sid = self.db.create_session(self.pid, "Segunda", "2026-01-01",
                                         "active", source_path=manual)
        with mock.patch.object(mw.QMessageBox, "information"):
            self.window._bind_wifi_sender("Alice", session_id=new_sid)
        cache = inboxmod.wifi_cache_dir("Alice")
        os.makedirs(cache, exist_ok=True)
        fpath = os.path.join(cache, "clip.mp4")
        with open(fpath, "wb") as f:
            f.write(b"x")
        with mock.patch.object(mw.MainWindow, "_scan_wifi_cache"):
            with mock.patch.object(mw.Ingestor, "handle_new_file") as hnf:
                self.window._on_wifi_file_received("Alice", fpath, 1)
                self.assertEqual(hnf.call_count, 2)

    def test_fanout_rows_reflect_each_session(self):
        """Con un origen compartido, cada sesión tiene su fila con su propio
        progreso, estado y destino (no se pisan entre sí)."""
        from app.core import shoot_inbox as inboxmod
        self.window._open_wifi_panel()
        manual = os.path.join(self.tmp, "manual")
        os.makedirs(manual, exist_ok=True)
        new_sid = self.db.create_session(self.pid, "Segunda", "2026-01-01",
                                         "active", source_path=manual)
        with mock.patch.object(mw.QMessageBox, "information"):
            self.window._bind_wifi_sender("Alice", session_id=new_sid)
        alice = [s for s in self.db.list_wifi_sessions(self.pid)
                 if s["device_folder"] == "Alice"]
        self.assertEqual(len(alice), 2)
        # Arranca ambos ingestores antes de crear la caché: el scan no ve nada.
        ing_a = self.window._start_wifi_ingestor(alice[0]["id"])
        ing_b = self.window._start_wifi_ingestor(alice[1]["id"])
        self.assertIsNotNone(ing_a)
        self.assertIsNotNone(ing_b)
        cache = inboxmod.wifi_cache_dir("Alice")
        os.makedirs(cache, exist_ok=True)
        fpath = os.path.join(cache, "clip.mp4")
        with open(fpath, "wb") as f:
            f.write(b"x")
        self.window.on_file_started(fpath, ingestor=ing_a)
        self.window.on_file_started(fpath, ingestor=ing_b)
        self.window.on_copy_progress(fpath, 50, 100, ingestor=ing_a)
        self.window.on_copy_progress(fpath, 100, 100, ingestor=ing_b)
        self.window.on_file_finished(fpath, "/outA/clip.mp4", True, {},
                                     ingestor=ing_a)
        self.window.on_file_finished(fpath, "/outB/clip.mp4", True, {},
                                     ingestor=ing_b)
        self.assertEqual(self.window.table.rowCount(), 2)
        statuses = [self.window.table.item(r, 2).text()
                    for r in range(self.window.table.rowCount())]
        self.assertEqual(statuses, [self.window.tr("Completado"),
                                    self.window.tr("Completado")])
        dests = sorted(self.window.table.item(r, 4).text()
                       for r in range(self.window.table.rowCount()))
        self.assertEqual(dests, ["/outA/clip.mp4", "/outB/clip.mp4"])

    def test_wifi_cache_cleared_only_when_last_ingestor_completes(self):
        self.window._open_wifi_panel()
        manual = os.path.join(self.tmp, "manual")
        os.makedirs(manual, exist_ok=True)
        new_sid = self.db.create_session(self.pid, "Segunda", "2026-01-01",
                                         "active", source_path=manual)
        with mock.patch.object(mw.QMessageBox, "information"):
            self.window._bind_wifi_sender("Alice", session_id=new_sid)
        alice_sessions = [s for s in self.db.list_wifi_sessions(self.pid)
                          if s["device_folder"] == "Alice"]
        self.assertEqual(len(alice_sessions), 2)
        ing_a = self.window._start_wifi_ingestor(alice_sessions[0]["id"])
        ing_b = self.window._start_wifi_ingestor(alice_sessions[1]["id"])
        self.assertIsNotNone(ing_a)
        self.assertIsNotNone(ing_b)
        # La primera en terminar no borra la caché si la otra sigue activa.
        with mock.patch.object(ing_a, "is_idle", return_value=True), \
                mock.patch.object(ing_b, "is_idle", return_value=False):
            with mock.patch.object(self.window, "_clear_wifi_cache") as clear:
                self.window._on_wifi_ingestor_complete({"errors": 0}, ing_a)
                clear.assert_not_called()
        # La última en terminar sí la borra.
        with mock.patch.object(self.window, "_clear_wifi_cache") as clear:
            self.window._on_wifi_ingestor_complete({"errors": 0}, ing_b)
            clear.assert_called_once_with(alice_sessions[1]["id"])

    def test_sync_wifi_sessions_removes_all_sessions_of_deleted_sender(self):
        self.window._open_wifi_panel()
        manual = os.path.join(self.tmp, "manual")
        os.makedirs(manual, exist_ok=True)
        new_sid = self.db.create_session(self.pid, "Segunda", "2026-01-01",
                                         "active", source_path=manual)
        with mock.patch.object(mw.QMessageBox, "information"):
            self.window._bind_wifi_sender("Bob", session_id=new_sid)
        self.assertEqual(len(self.db.list_wifi_sessions(self.pid)), 3)
        bob = next(s for s in self.db.list_inbox_senders() if s["name"] == "Bob")
        self.db.delete_inbox_sender(bob["id"])
        self.window._sync_wifi_sessions()
        sessions = self.db.list_wifi_sessions(self.pid)
        self.assertEqual([s["device_folder"] for s in sessions], ["Alice"])

    def test_bind_wifi_sender_uses_no_source_session(self):
        from app.core import shoot_inbox as inboxmod
        sid = self.db.create_session(self.pid, "Vacía", "2026-01-01", "active")
        self.window._bind_wifi_sender("Alice")
        session = self.db.get_session(sid)
        self.assertEqual(session["device_id"], WIFI_DEVICE_ID)
        self.assertEqual(session["source_path"], inboxmod.wifi_cache_dir("Alice"))
        wifi = self.db.list_wifi_sessions(self.pid)
        self.assertEqual([s["id"] for s in wifi], [sid])

    def test_bind_wifi_sender_creates_when_no_session(self):
        self.window._bind_wifi_sender("Alice")
        wifi = self.db.list_wifi_sessions(self.pid)
        self.assertEqual(len(wifi), 1)
        self.assertEqual(wifi[0]["device_folder"], "Alice")
        self.assertEqual(wifi[0]["name"], "WiFi (Alice)")

    def test_bind_wifi_sender_ignores_unknown_sender(self):
        sid = self.db.create_session(self.pid, "Manual", "2026-01-01", "active")
        self.window._bind_wifi_sender("Ghost", session_id=sid)
        self.assertFalse(self.db.get_session(sid)["device_id"])

    def test_assign_folder_source_rejects_managed_cache(self):
        from app.core import shoot_inbox as inboxmod
        self.window._open_wifi_panel()
        cache = inboxmod.wifi_cache_dir("Alice")
        before = len(self.db.get_sessions(self.pid))
        with mock.patch.object(mw.QMessageBox, "information") as info:
            self.window._assign_folder_source(cache)
            self.assertEqual(info.call_count, 1)
        self.assertEqual(len(self.db.get_sessions(self.pid)), before)

    def test_assign_folder_source_orphan_managed_warns(self):
        from app.core import shoot_inbox as inboxmod
        cache = inboxmod.wifi_cache_dir("Ghost")
        with mock.patch.object(mw.QMessageBox, "warning") as warn:
            self.window._assign_folder_source(cache)
            self.assertEqual(warn.call_count, 1)

    def test_assign_folder_source_creates_session(self):
        folder = os.path.join(self.tmp, "sd")
        os.makedirs(folder, exist_ok=True)
        with mock.patch.object(mw.QInputDialog, "getText", return_value=("TestCam", True)):
            self.window._assign_folder_source(folder)
        sessions = self.db.get_sessions(self.pid)
        self.assertEqual(len(sessions), 1)
        self.assertEqual(sessions[0]["source_path"], folder)
        self.assertIn(folder, self.window._source_paths)

    def test_assign_session_folder_sets_source(self):
        folder = os.path.join(self.tmp, "sd")
        os.makedirs(folder, exist_ok=True)
        sid = self.db.create_session(self.pid, "Manual", "2026-01-01", "active")
        self.window._assign_session_folder(sid, folder)
        session = self.db.get_session(sid)
        self.assertEqual(session["source_path"], folder)
        self.assertIn("Auto", session["name"])

    def test_sender_dialog_has_no_location_field(self):
        """Bug 2: el diálogo de nuevo dispositivo WiFi solo pide el nombre."""
        from app.ui.wifi_panel import SenderEditDialog
        dlg = SenderEditDialog(
            self.window, title="T", name_label="Nombre del dispositivo:",
            name_hint="")
        self.assertFalse(hasattr(dlg, "location_edit"))

    def test_remove_wifi_source_deletes_sender_and_session(self):
        from app.core import shoot_inbox as inboxmod
        self.window._open_wifi_panel()
        self.assertEqual(len(self.db.list_wifi_sessions(self.pid)), 2)
        alice_cache = inboxmod.wifi_cache_dir("Alice")
        self.assertIn(alice_cache, self.window._source_paths)
        self.window._remove_source_path(alice_cache)
        sessions = self.db.list_wifi_sessions(self.pid)
        self.assertEqual([s["device_folder"] for s in sessions], ["Bob"])
        names = [s["name"] for s in self.db.list_inbox_senders()]
        self.assertNotIn("Alice", names)
        self.assertNotIn(alice_cache, self.window._source_paths)

    def test_remove_source_keeps_manual_source(self):
        # Un origen manual (sin device_id WiFi) se borra sin tocar remitentes.
        manual = os.path.join(self.tmp, "manual")
        os.makedirs(manual, exist_ok=True)
        self.db.create_session(self.pid, "Manual", "2026-01-01", "active",
                               source_path=manual)
        self.window._populate_source_paths_from_sessions()
        self.assertIn(manual, self.window._source_paths)
        self.window._remove_source_path(manual)
        self.assertNotIn(manual, self.window._source_paths)
        self.assertEqual(len(self.db.list_inbox_senders()), 2)

    def test_content_button_wifi_opens_qr_for_sender(self):
        """La columna «Contenido» de un origen WiFi muestra resumen de contenido."""
        self.window._open_wifi_panel()
        sessions = self.db.get_sessions(self.pid)
        alice = next(s for s in sessions if s["device_folder"] == "Alice")
        wrapper = self.window._build_content_button(0, alice)
        btn = wrapper.layout().itemAt(0).widget()
        self.assertEqual(btn.text(), self.window.tr("Todo"))

    def test_content_button_ftp_opens_reconfigure(self):
        """La columna «Contenido» de un origen FTP abre el filtro de contenido."""
        from app.core import ftp as ftpmod
        pid = self.db.add_ftp_profile("Serv", "192.168.1.50")
        dev_id = ftpmod.device_key(pid)
        cache = os.path.join(self.tmp, "cache-ftp")
        os.makedirs(cache, exist_ok=True)
        sid = self.db.create_session(self.pid, "FTP", "2026-01-01", "active",
                                     source_path=cache)
        self.db.update_session_config(sid, device_id=dev_id, device_folder="DCIM")
        session = next(s for s in self.db.get_sessions(self.pid)
                       if s.get("device_id") == dev_id)
        wrapper = self.window._build_content_button(0, session)
        btn = wrapper.layout().itemAt(0).widget()
        self.assertEqual(btn.text(), self.window.tr("Todo"))

    def test_content_button_normal_opens_filter(self):
        """Un origen normal conserva el filtro de contenido en «Contenido»."""
        manual = os.path.join(self.tmp, "manual")
        os.makedirs(manual, exist_ok=True)
        self.db.create_session(self.pid, "Manual", "2026-01-01", "active",
                               source_path=manual)
        session = next(s for s in self.db.get_sessions(self.pid)
                       if s.get("source_path") == manual)
        wrapper = self.window._build_content_button(0, session)
        btn = wrapper.layout().itemAt(0).widget()
        self.assertNotEqual(btn.text(), self.window.tr("QR"))
        self.assertNotEqual(btn.text(), self.window.tr("FTP"))

    def test_pick_wifi_source_pairdrop_configures_new_qr(self):
        """El botón WiFi… siempre configura un QR nuevo (no reabre el existente)."""
        fake = mock.Mock()
        fake.method = "pairdrop"
        fake.exec.return_value = 1
        with mock.patch("app.ui.wifi_picker.WifiMethodDialog", return_value=fake):
            with mock.patch.object(mw.MainWindow, "_open_wifi_panel") as open_panel:
                self.window._pick_wifi_source()
                open_panel.assert_called_once_with(force_new_sender=True)

    def test_pick_wifi_source_ftp_opens_ftp_picker(self):
        """El botón WiFi… con FTP clásico abre el selector FTP."""
        fake = mock.Mock()
        fake.method = "ftp"
        fake.exec.return_value = 1
        with mock.patch("app.ui.wifi_picker.WifiMethodDialog", return_value=fake):
            with mock.patch.object(mw.MainWindow, "_pick_ftp_source") as pick:
                self.window._pick_wifi_source()
                pick.assert_called_once_with()

    def test_wifi_ingestor_maps_source_to_sender_camera(self):
        """El ingestor WiFi etiqueta los subdirectorios de su caché con el
        nombre del remitente (no "Unknown"), aunque no se haya pulsado
        «Iniciar Ingesta»."""
        from app.core import shoot_inbox as inboxmod
        self.window._open_wifi_panel()
        sessions = self.db.get_sessions(self.pid)
        alice = next(s for s in sessions if s["device_folder"] == "Alice")
        ing = self.window._ingestor_for_wifi_session(alice)
        cache = inboxmod.wifi_cache_dir("Alice", db=self.db)
        cam = ing._get_dispositivo_for_file(
            os.path.join(cache, "DCIM", "100MEDIA", "clip.mp4"))
        self.assertEqual(cam, "Alice")
        # Un remitente distinto no cae en la raíz de Alice.
        bob_cache = inboxmod.wifi_cache_dir("Bob", db=self.db)
        cam2 = ing._get_dispositivo_for_file(
            os.path.join(bob_cache, "clip.mp4"))
        self.assertEqual(cam2, "Unknown_Camera")

    def test_is_inbox_cache_path(self):
        from app.core import shoot_inbox as inboxmod
        cache = inboxmod.wifi_cache_dir("Alice", db=self.db)
        self.assertTrue(
            self.window._is_inbox_cache_path(os.path.join(cache, "x.mp4")))
        self.assertFalse(self.window._is_inbox_cache_path(self.dest))
        self.assertFalse(
            self.window._is_inbox_cache_path(inboxmod.inbox_root(db=self.db)))

    def test_remove_ingested_wifi_source_deletes_cache_and_prunes(self):
        from app.core import shoot_inbox as inboxmod
        cache = inboxmod.wifi_cache_dir("Alice", db=self.db)
        sub = os.path.join(cache, "DCIM", "100MEDIA")
        os.makedirs(sub, exist_ok=True)
        fpath = os.path.join(sub, "clip.mp4")
        with open(fpath, "wb") as f:
            f.write(b"x")
        self.window._remove_ingested_wifi_source(fpath)
        self.assertFalse(os.path.exists(fpath))
        self.assertFalse(os.path.exists(sub))
        # La caché del remitente se poda, pero la raíz del buzón se conserva.
        self.assertFalse(os.path.exists(cache))
        self.assertTrue(os.path.isdir(inboxmod.inbox_root(db=self.db)))

    def test_remove_ingested_wifi_source_ignores_non_inbox(self):
        outside = os.path.join(self.tmp, "outside.mp4")
        with open(outside, "wb") as f:
            f.write(b"x")
        self.window._remove_ingested_wifi_source(outside)
        self.assertTrue(os.path.exists(outside))

    def test_clear_completed_rows_removes_only_completed(self):
        def add_row(name, status):
            row = self.window.table.rowCount()
            self.window.table.insertRow(row)
            self.window.table.setItem(row, 0, QTableWidgetItem(name))
            self.window.table.setItem(row, 1, QTableWidgetItem("Cam"))
            self.window.table.setItem(row, 2, QTableWidgetItem(status))
        self.window.table.setSortingEnabled(False)
        add_row("a.mp4", self.window.tr("Completado"))
        add_row("b.mp4", self.window.tr("Error"))
        add_row("c.mp4", self.window.tr("Completado"))
        self.window._clear_completed_rows()
        remaining = [self.window.table.item(r, 0).text()
                     for r in range(self.window.table.rowCount())]
        self.assertEqual(set(remaining), {"b.mp4"})
        self.window.table.setSortingEnabled(True)

    def _add_completed_file(self, session_id, dest):
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        with open(dest, "wb") as f:
            f.write(b"x")
        conn = self.db.get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO files (session_id, source_path, dest_path, status) "
            "VALUES (?, ?, ?, 'completed')",
            (session_id, dest, dest))
        fid = cursor.lastrowid
        conn.commit()
        conn.close()
        return fid

    def test_move_completed_files_to_new_root(self):
        sid = self.db.create_session(self.pid, "S", "2026-01-01", "active",
                                     source_path="")
        old_file = os.path.join(self.dest, "Footage", "Cam", "2026-01-01",
                                "clip.mp4")
        fid = self._add_completed_file(sid, old_file)
        new_root = os.path.join(self.tmp, "dest2")
        rows = self.window._completed_files_under_root(self.dest)
        self.assertEqual(len(rows), 1)
        moved, failed = self.window._move_completed_files(rows, self.dest, new_root)
        self.assertEqual((moved, failed), (1, 0))
        expected = os.path.join(new_root, "Footage", "Cam", "2026-01-01",
                                "clip.mp4")
        self.assertTrue(os.path.exists(expected))
        self.assertFalse(os.path.exists(old_file))
        conn = self.db.get_connection()
        row = conn.execute("SELECT dest_path FROM files WHERE id = ?", (fid,)).fetchone()
        conn.close()
        self.assertEqual(row["dest_path"], expected)

    def test_move_completed_files_collision_gets_suffix(self):
        sid = self.db.create_session(self.pid, "S", "2026-01-01", "active",
                                     source_path="")
        old_file = os.path.join(self.dest, "Footage", "Cam", "clip.mp4")
        fid = self._add_completed_file(sid, old_file)
        new_root = os.path.join(self.tmp, "dest2")
        os.makedirs(os.path.join(new_root, "Footage", "Cam"), exist_ok=True)
        with open(os.path.join(new_root, "Footage", "Cam", "clip.mp4"), "wb") as f:
            f.write(b"occupied")
        rows = self.window._completed_files_under_root(self.dest)
        moved, failed = self.window._move_completed_files(rows, self.dest, new_root)
        self.assertEqual((moved, failed), (1, 0))
        expected = os.path.join(new_root, "Footage", "Cam", "clip (1).mp4")
        self.assertTrue(os.path.exists(expected))
        conn = self.db.get_connection()
        row = conn.execute("SELECT dest_path FROM files WHERE id = ?", (fid,)).fetchone()
        conn.close()
        self.assertEqual(row["dest_path"], expected)

    def test_delete_completed_file_records(self):
        sid = self.db.create_session(self.pid, "S", "2026-01-01", "active",
                                     source_path="")
        old_file = os.path.join(self.dest, "Footage", "Cam", "clip.mp4")
        fid = self._add_completed_file(sid, old_file)
        rows = self.window._completed_files_under_root(self.dest)
        self.window._delete_completed_file_records(rows)
        conn = self.db.get_connection()
        n = conn.execute("SELECT COUNT(*) FROM files WHERE id = ?", (fid,)).fetchone()[0]
        conn.close()
        self.assertEqual(n, 0)


class _FakeServer:
    running = True
    folder_mode = False

    def base_url(self):
        return "http://127.0.0.1:9999"

    def base_dir(self):
        return "."

    def stop(self):
        self.running = False

    def url_for_sender(self, name):
        return f"http://127.0.0.1:9999/?src={name}"


class _FakeMeta:
    def get_file_type_info(self, path):
        return {"type": "video", "category": "footage"}

    def get_video_metadata(self, path):
        return {
            "camera_model": "TestCam",
            "camera_make": "Test",
            "creation_date": "2026-01-01T10:00:00.000000Z",
            "duration": 1.0,
            "is_video": True,
        }

    def date_key_for_file(self, path):
        return "2026-01-01"


if __name__ == "__main__":
    unittest.main()
