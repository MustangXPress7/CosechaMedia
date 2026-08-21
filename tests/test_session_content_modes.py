"""Pruebas del modo de contenido por sesión en el núcleo Ingestor (I-15/I-18).

Cobertura:
- Ventana N días: cutoff calculado desde el último volcado de la sesión.
- Fallback hoy−N cuando la sesión no tiene volcados previos.
- Preservación de window_days/include_nodate del filtro recibido (sin cutoff_date).
- «Intervalo - todo»: filtro None ⇒ volcar todo.
- Intervalo con fechas: solo matchean los date_key incluidos.
"""
import os
import shutil
import tempfile
import unittest
from datetime import date, timedelta

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import app.core.ingestor as ingestor_module
from app.core.db import DatabaseManager
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


if __name__ == "__main__":
    unittest.main()
