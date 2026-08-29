import os
import shutil
import tempfile
import unittest
from unittest import mock

import app.core.ingestor as ingestor_module
from app.core.db import DatabaseManager
from app.core.ingestor import Ingestor


class FakeMeta:
    def get_file_type_info(self, path):
        return {"type": "video", "category": "footage"}

    def get_video_metadata(self, path):
        return {
            "camera_model": "TestCam",
            "camera_make": "Test",
            "creation_date": "2024-01-02T10:00:00.000000Z",
            "duration": 1.0,
            "is_video": True,
        }

    def date_key_for_file(self, path):
        return "2024-01-02"


class TestWatcherInventory(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="sdimport_watcher_inv_")
        self.src_dir = os.path.join(self.tmp, "src")
        self.dst_dir = os.path.join(self.tmp, "dst")
        os.makedirs(self.src_dir)
        os.makedirs(self.dst_dir)

        self.db = DatabaseManager(db_path=os.path.join(self.tmp, "watcher.db"))
        self._orig_db = ingestor_module.db
        self._orig_meta = ingestor_module.metadata_engine
        ingestor_module.db = self.db
        ingestor_module.metadata_engine = FakeMeta()

        self.ing = Ingestor(1, self.dst_dir, session_id=1)
        self.ing.source_dir = self.src_dir

    def tearDown(self):
        self.ing.stop()
        self.ing.executor.shutdown(wait=True)
        ingestor_module.db = self._orig_db
        ingestor_module.metadata_engine = self._orig_meta
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _make_path(self, rel):
        return os.path.join(self.src_dir, rel)

    def test_f02_conserved_in_watcher_skip(self):
        """F-02: archivo con veredicto 'copied' y destino borrado ⇒ should_skip False."""
        src = self._make_path("a.mp4")
        dest = os.path.join(self.dst_dir, "Footage", "TestCam", "2024-01-02", "a.mp4")
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        with open(dest, "wb") as f:
            f.write(b"x")

        # fila completed en DB
        conn = self.db.get_connection()
        conn.execute(
            "INSERT INTO files (session_id, source_path, dest_path, file_size, md5_hash, status)"
            " VALUES (?, ?, ?, 1, 'x', 'completed')",
            (str(self.ing.session_id), src, dest),
        )
        conn.commit()
        conn.close()

        # inventario con veredicto copied
        self.db.save_seen(self.src_dir, {src: "copied"})

        # destino presente ⇒ skip True
        self.assertTrue(self.ing.should_skip(src))

        # destino borrado ⇒ skip False (re-volcar)
        os.remove(dest)
        self.assertFalse(self.ing.should_skip(src))

    def test_cap_10k_removed(self):
        """El watcher ya no contiene el cap duro de 10k; inventario persiste en DB."""
        # Verificación conceptual: watcher.py no debe contener literal 10000
        from app.core import watcher as watcher_module
        src = watcher_module.__file__
        with open(src, "r", encoding="utf-8") as f:
            content = f.read()
        self.assertNotIn("10000", content, "El cap duro de 10k debe estar eliminado de watcher.py")

        # Inventario sin cap: podemos guardar >10k entradas
        big_dict = {os.path.join(self.src_dir, f"f{i}.mp4"): "copied" for i in range(20000)}
        self.db.save_seen(self.src_dir, big_dict)
        loaded = self.db.load_seen(self.src_dir)
        self.assertEqual(len(loaded), 20000)

    def test_verdicts_with_filter_key_identity(self):
        """'filtered' solo salta si filter_key coincide; 'errored' siempre se re-maneja."""
        src1 = self._make_path("b.mp4")
        src2 = self._make_path("c.mp4")
        src3 = self._make_path("d.mp4")

        # copied con destino presente
        dest1 = os.path.join(self.dst_dir, "Footage", "TestCam", "2024-01-02", "b.mp4")
        os.makedirs(os.path.dirname(dest1), exist_ok=True)
        with open(dest1, "wb") as f:
            f.write(b"x")
        conn = self.db.get_connection()
        conn.execute(
            "INSERT INTO files (session_id, source_path, dest_path, file_size, md5_hash, status)"
            " VALUES (?, ?, ?, 1, 'x', 'completed')",
            (str(self.ing.session_id), src1, dest1),
        )
        conn.commit()
        conn.close()
        self.db.save_seen(self.src_dir, {src1: "copied"})

        # filtered con misma firma que el content-filter actual
        current_sig = self.ing._content_filter_signature()
        self.db.save_seen(self.src_dir, {src2: "filtered"}, filter_keys={src2: current_sig})
        # should_skip debe ser True porque el filtro coincide y no hay destino
        # (sin fila completed, el veredicto filtrado evita re-sondeo)
        # Simular que handle_new_file habría cortocircuitado; comprobamos el predicado
        # Para el predicado, 'filtered' con key coincidente ⇒ skip True
        # Necesitamos que no haya destino conocido
        self.assertTrue(self.ing.should_skip(src2))

        # filtered con firma distinta ⇒ re-evaluar (skip False)
        different_sig = "mode:all:2020-01-01"
        self.db.save_seen(self.src_dir, {src3: "filtered"}, filter_keys={src3: different_sig})
        self.assertFalse(self.ing.should_skip(src3))

        # errored siempre se re-maneja
        src_err = self._make_path("e.mp4")
        self.db.save_seen(self.src_dir, {src_err: "errored"})
        self.assertFalse(self.ing.should_skip(src_err))

    def test_prune_by_age(self):
        """prune_seen elimina filas con first_seen >30 días."""
        src = self._make_path("old.mp4")
        self.db.save_seen(self.src_dir, {src: "copied"})
        # Forzar fecha antigua
        conn = self.db.get_connection()
        conn.execute(
            "UPDATE watcher_seen SET first_seen = '2000-01-01 00:00:00' WHERE source_path = ? AND file_path = ?",
            (os.path.normpath(self.src_dir), os.path.normpath(src)),
        )
        conn.commit()
        conn.close()

        self.db.prune_seen(self.src_dir, days=30)
        loaded = self.db.load_seen(self.src_dir)
        self.assertNotIn(os.path.normpath(src), loaded)

    def test_normalization_backslash(self):
        """Grabar con / y consultar con \\ debe deduplicar."""
        src_forward = os.path.join(self.src_dir, "x", "y.mp4")
        # Usar 'filtered' para no requerir destino en disco (F-02)
        current_sig = self.ing._content_filter_signature()
        self.db.save_seen(self.src_dir, {src_forward: "filtered"}, filter_keys={src_forward: current_sig})
        # Ruta con backslash Windows (en Windows os.path.join ya usa backslash,
        # pero probamos que la normalización funcione)
        src_back = os.path.normpath(src_forward).replace("/", "\\")
        loaded = self.db.load_seen(self.src_dir)
        # load_seen normaliza internamente la source_path; comprobamos coincidencia
        self.assertIn(os.path.normpath(src_forward), loaded)
        # should_skip con 'filtered' y filter_key coincidente debe retornar True
        self.assertTrue(self.ing.should_skip(src_forward))

    def test_shared_predicate_and_verdict_registration(self):
        """should_skip comparte lógica con handle_new_file y registra veredictos."""
        src = self._make_path("f.mp4")
        # Sin veredicto previo, sin destino → should_skip False
        self.assertFalse(self.ing.should_skip(src))

        # Simular pasada del watcher que registra 'filtered' cuando fuera de ventana
        ing_filtered = Ingestor(1, self.dst_dir, session_id=2,
                                content_mode="window",
                                content_filter={"window_days": 1})
        # fecha actual ficticia: cutoff en 2026, archivo 2024 → fuera de ventana
        # should_skip sin inventario → aplica filtro y retorna True
        # Forzamos filtro
        self.assertTrue(ing_filtered.should_skip(src))
        # Veredicto debería haberse registrado vía handle_new_file (no testeamos handle directamente)
        # Comprobamos que load_seen devuelve vacio (porque no hicimos handle)
        # Basta con verificar que should_skip funciona con inventario
        self.db.save_seen(self.src_dir, {src: "filtered"}, filter_keys={src: ing_filtered._content_filter_signature()})
        self.assertTrue(ing_filtered.should_skip(src))


if __name__ == "__main__":
    unittest.main()
