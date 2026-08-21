"""Pruebas del modo de contenido por sesión en el núcleo Ingestor (I-15/I-18).

Cobertura:
- Ventana N días: cutoff calculado desde el último volcado de la sesión.
- Fallback hoy−N cuando la sesión no tiene volcados previos.
- Preservación de window_days/include_nodate del filtro recibido (sin cutoff_date).
- «Intervalo - todo»: filtro None ⇒ volcar todo.
- Intervalo con fechas: solo matchean los date_key incluidos.
"""
import json
import os
import shutil
import tempfile
import unittest
from datetime import date, timedelta
from unittest import mock

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

import app.ui.main_window as mw
import app.core.ingestor as ingestor_module
from app.core.db import DatabaseManager, WIFI_DEVICE_ID
from app.core.ingestor import Ingestor


class _FixedDateMeta:
    """Sustituto de metadata_engine con date_key controlable por test."""

    def __init__(self, date_key):
        self._date_key = date_key

    def get_file_type_info(self, path):
        return {"type": "video", "category": "footage"}

    def get_video_metadata(self, path):
        return {}

    def date_key_for_file(self, path):
        return self._date_key


class TestWindowCutoffCore(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="sdimport_sessmode_")
        self.dst = os.path.join(self.tmp, "dst")
        os.makedirs(self.dst)

        self.db = DatabaseManager(db_path=os.path.join(self.tmp, "sessmode.db"))
        self._orig_db = ingestor_module.db
        self._orig_meta = ingestor_module.metadata_engine
        ingestor_module.db = self.db
        ingestor_module.metadata_engine = _FixedDateMeta("2024-01-02")

        conn = self.db.get_connection()
        cursor = conn.cursor()
        cursor.execute("INSERT INTO projects (name, root_path) VALUES ('P', ?)", (self.dst,))
        self.pid = cursor.lastrowid
        conn.commit()
        conn.close()
        src = os.path.join(self.tmp, "src")
        os.makedirs(src, exist_ok=True)
        self.sid = self.db.create_session(self.pid, "Ses", "2026-08-10", "active", src)

        self._ingestors = []

    def tearDown(self):
        for ing in self._ingestors:
            ing.stop()
            ing.executor.shutdown(wait=True)
        ingestor_module.db = self._orig_db
        ingestor_module.metadata_engine = self._orig_meta
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _make_ingestor(self, **kwargs):
        ing = Ingestor(self.pid, self.dst, session_id=self.sid, **kwargs)
        self._ingestors.append(ing)
        return ing

    def _insert_dump(self, verified_at="2026-08-10 12:00:00"):
        conn = self.db.get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO files (session_id, source_path, dest_path, file_size,"
            " md5_hash, status, verified_at) VALUES (?, 'a.mp4', 'b.mp4', 1,"
            " 'x', 'completed', ?)",
            (str(self.sid), verified_at),
        )
        conn.commit()
        conn.close()

    def test_window_cutoff_from_last_dump(self):
        """El cutoff se calcula desde el último volcado de la sesión menos N días."""
        self._insert_dump("2026-08-10 12:00:00")
        ing = self._make_ingestor(content_mode="window",
                                  content_filter={"window_days": 3})
        self.assertEqual(ing._content_filter["cutoff_date"], "2026-08-07")
        self.assertEqual(ing._content_filter["window_days"], 3)

    def test_window_cutoff_fallback_today_minus_n(self):
        """Sin volcados previos, el cutoff es hoy − N días."""
        ing = self._make_ingestor(content_mode="window",
                                  content_filter={"window_days": 3})
        expected = (date.today() - timedelta(days=3)).strftime("%Y-%m-%d")
        self.assertEqual(ing._content_filter["cutoff_date"], expected)

    def test_window_days_preserved_without_cutoff(self):
        """window_days del filtro recibido NO se resetea al default 7."""
        ing = self._make_ingestor(content_mode="window",
                                  content_filter={"window_days": 5})
        self.assertEqual(ing._content_filter["window_days"], 5)

    def test_interval_none_filter_matches_all(self):
        """«Intervalo - todo» (filtro normalizado a None) vuelca todo."""
        ing = self._make_ingestor(content_mode="interval", content_filter=None)
        self.assertTrue(ing._matches_filter("ruta/cualquiera.mp4"))

    def test_interval_dates_match_only_selected(self):
        """Intervalo con fechas: solo matchean los date_key incluidos."""
        ing = self._make_ingestor(
            content_mode="interval",
            content_filter={"dates": ["2024-01-02"], "include_nodate": False})
        self.assertTrue(ing._matches_filter("clip_dentro.mp4"))

        ingestor_module.metadata_engine = _FixedDateMeta("2024-06-01")
        self.assertFalse(ing._matches_filter("clip_fuera.mp4"))

        ingestor_module.metadata_engine = _FixedDateMeta(None)
        self.assertFalse(ing._matches_filter("clip_sin_fecha.mp4"))


class TestSessionDumpSwitch(unittest.TestCase):
    """Switch cíclico de volcado por sesión en el área «Sesiones» (I-15/I-18)."""

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="sdimport_dumpswitch_")
        self.src = os.path.join(self.tmp, "src")
        self.dest = os.path.join(self.tmp, "dest")
        os.makedirs(self.src)
        os.makedirs(self.dest)

        self._orig_db = mw.db
        self._orig_ing_db = ingestor_module.db
        self._orig_notif = mw.NotificationManager
        self.db = DatabaseManager(db_path=os.path.join(self.tmp, "switch.db"))
        mw.db = self.db
        ingestor_module.db = self.db

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

        self.sid = self.db.create_session(self.pid, "Sesión", "2026-08-10", "active", self.src)

        self.window = mw.MainWindow()
        self.window.current_project_id = self.pid
        self.window.dest_root = self.dest
        self.window._source_paths = [self.src]
        self.window._refresh_sessions_combo()

    def tearDown(self):
        self.window.close()
        mw.db = self._orig_db
        ingestor_module.db = self._orig_ing_db
        mw.NotificationManager = self._orig_notif
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _select_session(self, sid):
        idx = self.window.sessions_combo.findData(sid)
        self.assertNotEqual(idx, -1)
        self.window.sessions_combo.setCurrentIndex(idx)

    def test_initial_state_all_enabled(self):
        """Sesión normal seleccionada: switch habilitado en «Todo el contenido»."""
        self._select_session(self.sid)
        btn = self.window.btn_session_dump_mode
        self.assertTrue(btn.isEnabled())
        self.assertEqual(btn.text(), self.window.tr("Todo el contenido"))

    def test_cycle_all_to_interval_accepted_persists(self):
        """all→intervalo aceptado: persiste modo+filtro y el switch muestra «Intervalo:»."""
        fake = mock.Mock()
        fake.exec.return_value = mw.QDialog.Accepted
        fake.content_filter = {"dates": ["2024-01-05"], "include_nodate": False}
        fake.content_mode = "interval"
        fake.content_text = "el 5-1-24"
        with mock.patch.object(mw, "SelectiveDumpAssistant", return_value=fake) as MockDlg:
            self.window.btn_session_dump_mode.click()
        kwargs = MockDlg.call_args.kwargs
        self.assertEqual(kwargs.get("mode"), "filter")
        self.assertEqual(kwargs.get("session_id"), self.sid)
        self.assertEqual(kwargs.get("initial_mode"), "interval")
        sess = self.db.get_session(self.sid)
        self.assertEqual(sess["content_mode"], "interval")
        self.assertEqual(json.loads(sess["content_filter"]), fake.content_filter)
        self.assertIn("Intervalo:", self.window.btn_session_dump_mode.text())

    def test_cycle_interval_cancelled_keeps_all(self):
        """Cancelar el asistente NO persiste nada y el switch vuelve a «Todo»."""
        fake = mock.Mock()
        fake.exec.return_value = mw.QDialog.Rejected
        with mock.patch.object(mw, "SelectiveDumpAssistant", return_value=fake):
            self.window.btn_session_dump_mode.click()
        sess = self.db.get_session(self.sid)
        self.assertEqual(sess["content_mode"], "all")
        self.assertIsNone(sess["content_filter"])
        self.assertEqual(self.window.btn_session_dump_mode.text(),
                         self.window.tr("Todo el contenido"))

    def test_cycle_to_window_accepted_persists_days(self):
        """interval→ventana aceptado: persiste {window_days: N} sin cutoff congelado."""
        self.db.update_session_config(
            self.sid, content_mode="interval",
            content_filter=json.dumps({"dates": ["2024-01-05"], "include_nodate": False}))
        self.window._update_session_dump_switch()
        with mock.patch.object(mw.QInputDialog, "getInt", return_value=(9, True)) as gi:
            self.window.btn_session_dump_mode.click()
        gi.assert_called_once()
        sess = self.db.get_session(self.sid)
        self.assertEqual(sess["content_mode"], "window")
        self.assertEqual(json.loads(sess["content_filter"]), {"window_days": 9})
        self.assertNotIn("cutoff_date", json.loads(sess["content_filter"]))
        self.assertEqual(self.window.btn_session_dump_mode.text(),
                         self.window.tr("Últimos %1 días").arg(9))

    def test_cycle_window_cancelled_keeps_state(self):
        """Cancelar el diálogo de días NO altera la sesión."""
        self.db.update_session_config(
            self.sid, content_mode="interval",
            content_filter=json.dumps({"dates": ["2024-01-05"], "include_nodate": False}))
        self.window._update_session_dump_switch()
        with mock.patch.object(mw.QInputDialog, "getInt", return_value=(9, False)):
            self.window.btn_session_dump_mode.click()
        sess = self.db.get_session(self.sid)
        self.assertEqual(sess["content_mode"], "interval")
        self.assertEqual(json.loads(sess["content_filter"]),
                         {"dates": ["2024-01-05"], "include_nodate": False})

    def test_cycle_window_to_all(self):
        """ventana→todo: persiste modo all y filtro None."""
        self.db.update_session_config(self.sid, content_mode="window",
                                      content_filter=json.dumps({"window_days": 9}))
        self.window._update_session_dump_switch()
        self.window.btn_session_dump_mode.click()
        sess = self.db.get_session(self.sid)
        self.assertEqual(sess["content_mode"], "all")
        self.assertIsNone(sess["content_filter"])
        self.assertEqual(self.window.btn_session_dump_mode.text(),
                         self.window.tr("Todo el contenido"))

    def test_wifi_session_switch_disabled(self):
        """Sesión WiFi: switch deshabilitado fijado en «Todo el contenido»."""
        wifi_sid = self.db.create_session(self.pid, "WiFi", "2026-08-10", "active", "")
        self.db.update_session_config(wifi_sid, device_id=WIFI_DEVICE_ID)
        self.window._refresh_sessions_combo()
        self._select_session(wifi_sid)
        btn = self.window.btn_session_dump_mode
        self.assertFalse(btn.isEnabled())
        self.assertEqual(btn.text(), self.window.tr("Todo el contenido"))

    def test_switch_refreshes_on_selection_change(self):
        """Cambiar de sesión en el combo actualiza el texto del switch."""
        self.db.update_session_config(self.sid, content_mode="window",
                                      content_filter=json.dumps({"window_days": 9}))
        other = os.path.join(self.tmp, "other")
        os.makedirs(other)
        sid2 = self.db.create_session(self.pid, "Otra", "2026-08-11", "active", other)
        self.db.update_session_config(
            sid2, content_mode="interval",
            content_filter=json.dumps({"dates": ["2024-01-05"], "include_nodate": False}))
        self.window._refresh_sessions_combo()

        self._select_session(self.sid)
        self.assertEqual(self.window.btn_session_dump_mode.text(),
                         self.window.tr("Últimos %1 días").arg(9))
        self._select_session(sid2)
        self.assertIn("Intervalo:", self.window.btn_session_dump_mode.text())


if __name__ == "__main__":
    unittest.main()
