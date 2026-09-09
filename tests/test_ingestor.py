import builtins
import json
import os
import shutil
import tempfile
import unittest
from unittest import mock

import app.core.ingestor as ingestor_module
from app.core.db import DatabaseManager
from app.core.ingestor import Ingestor, DumpTarget


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


class RefMeta(FakeMeta):
    def get_file_type_info(self, path):
        return {"type": "other", "category": "reference"}


class TestIngestor(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="sdimport_ing_")
        self.src_dir = os.path.join(self.tmp, "src")
        self.dst_dir = os.path.join(self.tmp, "dst")
        self.resume_dir = os.path.join(self.tmp, "resume")
        os.makedirs(self.src_dir)
        os.makedirs(self.dst_dir)
        os.makedirs(self.resume_dir)

        self.db = DatabaseManager(db_path=os.path.join(self.tmp, "ingest.db"))
        self._orig_db = ingestor_module.db
        self._orig_meta = ingestor_module.metadata_engine
        self._orig_calc = ingestor_module.calculate_md5
        self._orig_data_dir = ingestor_module.data_dir
        ingestor_module.db = self.db
        ingestor_module.metadata_engine = FakeMeta()
        ingestor_module.data_dir = lambda: self.resume_dir

        self.ing = Ingestor(1, self.dst_dir, session_id=1)

    def tearDown(self):
        self.ing.stop()
        self.ing.executor.shutdown(wait=True)
        ingestor_module.db = self._orig_db
        ingestor_module.metadata_engine = self._orig_meta
        ingestor_module.calculate_md5 = self._orig_calc
        ingestor_module.data_dir = self._orig_data_dir
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _make_source(self, name="clip.mp4", size=2048, content=None):
        path = os.path.join(self.src_dir, name)
        if content is None:
            with open(path, "wb") as f:
                f.write(os.urandom(size))
        else:
            with open(path, "wb") as f:
                f.write(content)
        return path

    def test_verified_copy_success(self):
        src = self._make_source()
        self.ing._process_single_file(src, {"type": "video", "category": "footage"})

        stats = self.ing.get_stats()
        self.assertEqual(stats["processed"], 1)
        self.assertEqual(stats["errors"], 0)

        dest = os.path.join(self.dst_dir, "Footage", "TestCam", "2024-01-02", "clip.mp4")
        self.assertTrue(os.path.exists(dest), "El destino debe existir tras una copia verificada")

        conn = self.db.get_connection()
        row = conn.execute("SELECT dest_path, md5_hash, status FROM files WHERE session_id = '1'").fetchone()
        conn.close()
        self.assertIsNotNone(row)
        self.assertEqual(row["dest_path"], dest)
        self.assertEqual(row["md5_hash"], self._orig_calc(dest))
        self.assertEqual(row["status"], "completed")

    def test_camera_map_prefix_matches_subfolders_not_siblings(self):
        root = os.path.join(self.tmp, "inbox", "Alice")
        ing = Ingestor(1, self.dst_dir, session_id=2,
                       camera_map={root: "Alice"})
        self.assertEqual(
            ing._get_dispositivo_for_file(os.path.join(root, "DCIM", "x.mp4")),
            "Alice")
        self.assertEqual(ing._get_dispositivo_for_file(root), "Alice")
        # Un directorio hermano con nombre similar no debe emparejarse.
        self.assertEqual(
            ing._get_dispositivo_for_file(os.path.join(self.tmp, "inbox", "Alice2", "x.mp4")),
            "SinClasificar")

    def test_copy_progress_emitted_by_percent(self):
        src = self._make_source(size=8192 * 300)  # 300 bloques → enough para throttle
        progress = []
        self.ing.copy_progress.connect(lambda sp, c, t: progress.append((c, t)))
        dest = os.path.join(self.dst_dir, "progress.bin")
        self.assertTrue(self.ing._copy_verified(src, dest))
        self.assertTrue(os.path.exists(dest))

        self.assertGreaterEqual(len(progress), 2)
        self.assertLessEqual(len(progress), 101, "El throttle por % debe limitar las emisiones")
        pcts = [int(c * 100.0 / t) for c, t in progress if t]
        self.assertEqual(pcts, sorted(pcts))
        self.assertEqual(pcts[-1], 100)
        last_c, last_t = progress[-1]
        self.assertEqual(last_c, last_t)

    def test_copy_verified_small_file_single_emission(self):
        src = self._make_source(size=1024)
        progress = []
        self.ing.copy_progress.connect(lambda sp, c, t: progress.append((c, t)))
        dest = os.path.join(self.dst_dir, "small.bin")
        self.assertTrue(self.ing._copy_verified(src, dest))
        self.assertGreaterEqual(len(progress), 1)
        self.assertEqual(progress[-1][0], progress[-1][1])

    def test_copy_verified_single_pass_no_dest_reread(self):
        src = self._make_source()
        dest = os.path.join(self.dst_dir, "single_pass.bin")
        ingestor_module.calculate_md5 = mock.Mock(return_value="")
        try:
            result = self.ing._copy_verified(src, dest)
            # (a) el destino NO se vuelve a leer con calculate_md5 en el pase único
            ingestor_module.calculate_md5.assert_not_called()
            # (b) el destino existe y está íntegro en disco
            self.assertTrue(os.path.exists(dest), "El destino debe existir tras el pase único")
            self.assertEqual(
                os.path.getsize(dest), os.path.getsize(src),
                "El destino debe contener exactamente los bytes copiados del origen")
            # (c) el hash devuelto == hash real del contenido del destino (leído en el test)
            self.assertEqual(result, self._orig_calc(dest))
        finally:
            ingestor_module.calculate_md5 = self._orig_calc

    def test_copy_error_removes_partial_dest(self):
        src = self._make_source()
        dest = os.path.join(self.dst_dir, "partial.bin")
        real_open = builtins.open

        def _raise_write(path, mode, *args, **kwargs):
            if any(ch in mode for ch in ("w", "a", "x", "+")):
                raise OSError("disk full")
            return real_open(path, mode, *args, **kwargs)

        with mock.patch("builtins.open", side_effect=_raise_write):
            result = self.ing._copy_verified(src, dest)

        self.assertIsNone(result, "Ante error de escritura el retorno debe ser None")
        self.assertFalse(os.path.exists(dest), "El destino parcial debe eliminarse")

    def test_reference_unique_names(self):
        os.makedirs(os.path.join(self.src_dir, "a"))
        os.makedirs(os.path.join(self.src_dir, "b"))
        f1 = os.path.join(self.src_dir, "a", "notes.txt")
        f2 = os.path.join(self.src_dir, "b", "notes.txt")
        with open(f1, "w") as f:
            f.write("one")
        with open(f2, "w") as f:
            f.write("two")

        self.ing._handle_reference_file(f1)
        self.ing._handle_reference_file(f2)

        ref_dir = os.path.join(self.dst_dir, "_reference")
        names = set(os.listdir(ref_dir))
        self.assertEqual(names, {"notes.txt", "notes (1).txt"})

    def test_dump_target_full(self):
        target = DumpTarget(1, self.dst_dir, True, True)
        dir_full = target.next_available_dir("Cam", "2024-01-02", "Footage", 10)
        self.assertTrue(os.path.isdir(dir_full))

        orig_free = ingestor_module._free_space
        ingestor_module._free_space = lambda p: 5  # menos que el archivo + margen
        try:
            self.assertIsNone(
                target.next_available_dir("Cam", "2024-01-02", "Footage", 1024 * 1024)
            )
        finally:
            ingestor_module._free_space = orig_free

    def test_content_filter_includes_matching(self):
        ing = Ingestor(1, self.dst_dir, session_id=7,
                       content_filter={"dates": ["2024-01-02"], "include_nodate": False})
        ing.handle_new_file(self._make_source())
        ing.executor.shutdown(wait=True)
        stats = ing.get_stats()
        self.assertEqual(stats["processed"], 1)
        self.assertEqual(stats["skipped"], 0)

    def test_content_filter_skips_out_of_range(self):
        ing = Ingestor(1, self.dst_dir, session_id=8,
                       content_filter={"dates": ["2024-06-01"], "include_nodate": False})
        ing.handle_new_file(self._make_source())
        ing.executor.shutdown(wait=True)
        stats = ing.get_stats()
        self.assertEqual(stats["processed"], 0)
        self.assertEqual(stats["skipped"], 1)

    def test_content_filter_nodate_included(self):
        class NoDateMeta(FakeMeta):
            def date_key_for_file(self, path):
                return None
        ingestor_module.metadata_engine = NoDateMeta()
        ing = Ingestor(1, self.dst_dir, session_id=9,
                       content_filter={"dates": ["2024-01-02"], "include_nodate": True})
        ing.handle_new_file(self._make_source())
        ing.executor.shutdown(wait=True)
        self.assertEqual(ing.get_stats()["processed"], 1)

    def test_content_filter_nodate_excluded(self):
        class NoDateMeta(FakeMeta):
            def date_key_for_file(self, path):
                return None
        ingestor_module.metadata_engine = NoDateMeta()
        ing = Ingestor(1, self.dst_dir, session_id=10,
                       content_filter={"dates": ["2024-01-02"], "include_nodate": False})
        ing.handle_new_file(self._make_source())
        ing.executor.shutdown(wait=True)
        stats = ing.get_stats()
        self.assertEqual(stats["processed"], 0)
        self.assertEqual(stats["skipped"], 1)

    def test_completed_file_with_present_dest_is_skipped(self):
        src = self._make_source()
        self.ing.handle_new_file(src)
        self.ing.executor.shutdown(wait=True)
        self.assertEqual(self.ing.get_stats()["processed"], 1)
        dest = os.path.join(self.dst_dir, "Footage", "TestCam", "2024-01-02", "clip.mp4")
        self.assertTrue(os.path.exists(dest))

        ing2 = Ingestor(1, self.dst_dir, session_id=1)
        try:
            ing2.handle_new_file(src)
            ing2.executor.shutdown(wait=True)
            stats = ing2.get_stats()
            self.assertEqual(stats["processed"], 0)
            self.assertEqual(stats["skipped"], 1)
        finally:
            ing2.stop()

    def test_completed_file_with_missing_dest_is_recopied(self):
        src = self._make_source()
        self.ing.handle_new_file(src)
        self.ing.executor.shutdown(wait=True)
        self.assertEqual(self.ing.get_stats()["processed"], 1)
        dest = os.path.join(self.dst_dir, "Footage", "TestCam", "2024-01-02", "clip.mp4")
        self.assertTrue(os.path.exists(dest))
        os.remove(dest)

        ing2 = Ingestor(1, self.dst_dir, session_id=1)
        try:
            ing2.handle_new_file(src)
            ing2.executor.shutdown(wait=True)
            stats = ing2.get_stats()
            self.assertEqual(stats["processed"], 1)
            self.assertEqual(stats["skipped"], 0)
            self.assertTrue(os.path.exists(dest),
                            "El archivo debe re-volcarse al faltar el destino")
        finally:
            ing2.stop()

    def test_should_skip_resolves_verdict(self):
        """Verificación in-task del predicado compartido `should_skip` (W#3):
        un veredicto 'copied' con destino presente en disco ⇒ skip True; con el
        mismo veredicto pero destino borrado ⇒ skip False (F-02: re-volcar)."""
        src = self._make_source()
        dest = os.path.join(self.dst_dir, "Footage", "TestCam", "2024-01-02", "clip.mp4")

        # Veredicto persistido 'copied' en el inventario (pasada previa).
        ingestor_module.db.save_seen(self.src_dir, {src: "copied"})
        ing = self.ing
        ing.source_dir = self.src_dir

        # Fila completed + destino presente en disco ⇒ skip.
        conn = self.db.get_connection()
        conn.execute(
            "INSERT INTO files (session_id, source_path, dest_path, file_size,"
            " md5_hash, status) VALUES (?, ?, ?, 1, 'x', 'completed')",
            (str(ing.session_id), src, dest))
        conn.commit()
        conn.close()
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        with open(dest, "wb") as f:
            f.write(b"x")
        self.assertTrue(ing.should_skip(src),
                        "Con destino presente el volcado previo exime de re-copiar")

        # Borrar el destino ⇒ skip False (re-volcar, F-02).
        os.remove(dest)
        self.assertFalse(ing.should_skip(src),
                         "Destino borrado ⇒ el inventario 'copied' no debe saltar (F-02)")

    def test_reference_file_missing_dest_recopied(self):
        src = os.path.join(self.src_dir, "notes.txt")
        with open(src, "w") as f:
            f.write("hoja de rodaje")
        ingestor_module.metadata_engine = RefMeta()
        self.ing.handle_new_file(src)
        self.ing.executor.shutdown(wait=True)
        dest = os.path.join(self.dst_dir, "_reference", "notes.txt")
        self.assertTrue(os.path.exists(dest))

        # El usuario borra la copia: la ingesta debe volver a copiarla aunque
        # la fila de la DB esté en estado 'reference' (no 'completed').
        os.remove(dest)
        ing2 = Ingestor(1, self.dst_dir, session_id=1)
        try:
            ing2.handle_new_file(src)
            ing2.executor.shutdown(wait=True)
            self.assertTrue(os.path.exists(dest),
                            "El archivo de referencia borrado debe re-copiarse")
        finally:
            ing2.stop()

    def test_json_resume_alone_does_not_skip_missing_dest(self):
        src = self._make_source()
        # Estado legacy: el resume JSON dice copiado pero no hay fila en la DB.
        legacy = os.path.join(self.dst_dir, ".sdimport_session_9.json")
        with open(legacy, "w") as f:
            json.dump({"copied_files": [src]}, f)

        ing = Ingestor(1, self.dst_dir, session_id=9)
        try:
            # El .json legacy de la raíz de destino se elimina al construirse
            # el Ingestor (ya no tiene cabida junto a Footage).
            self.assertFalse(os.path.exists(legacy),
                             "El resume JSON legacy no debe quedar en la raíz de destino")
            ing.handle_new_file(src)
            ing.executor.shutdown(wait=True)
            stats = ing.get_stats()
            self.assertEqual(stats["processed"], 1,
                             "Sin fila volcada en la DB no se debe saltar por el JSON")
            dest = os.path.join(self.dst_dir, "Footage", "TestCam", "2024-01-02", "clip.mp4")
            self.assertTrue(os.path.exists(dest))
        finally:
            ing.stop()

    def test_window_known_dump_outside_window_is_skipped(self):
        """«Últimos x días»: un archivo con volcado previo cuya fecha
        quedó fuera de la ventana recalculada se omite aunque la copia
        haya sido borrada. La ventana de contenido es la fuente de verdad."""
        src = self._make_source()
        conn = self.db.get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO files (session_id, source_path, dest_path, file_size,"
            " md5_hash, status, verified_at) VALUES (?, ?, ?, 1, 'x',"
            " 'completed', '2026-08-10 12:00:00')",
            (str(21), src, os.path.join(self.dst_dir, "perdido.mp4")))
        conn.commit()
        conn.close()

        # Simular inventario de pasada previa (veredicto copied).
        ingestor_module.db.save_seen(self.src_dir, {src: "copied"})

        ing = Ingestor(1, self.dst_dir, session_id=21,
                       content_mode="window",
                       content_filter={"window_days": 1})
        ing.source_dir = self.src_dir
        try:
            # cutoff = 2026-08-09: el date_key 2024-01-02 quedaría fuera
            self.assertLess("2024-01-02", ing._content_filter["cutoff_date"])
            ing.handle_new_file(src)
            ing.executor.shutdown(wait=True)
            stats = ing.get_stats()
            self.assertEqual(stats["processed"], 0,
                             "Archivo fuera de ventana debe omitirse aunque hubiera volcado previo")
            self.assertEqual(stats["skipped"], 1)
        finally:
            ing.stop()

    def test_window_known_dump_inside_window_is_recopied(self):
        """«Últimos x días»: un archivo con volcado previo cuya fecha
        SÍ está dentro de la ventana se re-vuelca si la copia fue borrada."""
        src = self._make_source()
        conn = self.db.get_connection()
        cursor = conn.cursor()
        # date_key del archivo de prueba es 2024-01-02; window_days=1
        # con last_dump_date = 2024-01-02 → cutoff = 2024-01-01 → dentro
        cursor.execute(
            "INSERT INTO files (session_id, source_path, dest_path, file_size,"
            " md5_hash, status, verified_at) VALUES (?, ?, ?, 1, 'x',"
            " 'completed', '2024-01-02 12:00:00')",
            (str(21), src, os.path.join(self.dst_dir, "perdido.mp4")))
        conn.commit()
        conn.close()

        ing = Ingestor(1, self.dst_dir, session_id=21,
                       content_mode="window",
                       content_filter={"window_days": 1})
        try:
            self.assertEqual(ing._content_filter["cutoff_date"], "2024-01-01")
            ing.handle_new_file(src)
            ing.executor.shutdown(wait=True)
            stats = ing.get_stats()
            self.assertEqual(stats["processed"], 1,
                             "Archivo dentro de ventana sin copia debe re-volcarse")
            self.assertEqual(stats["skipped"], 0)
            dest = os.path.join(self.dst_dir, "Footage", "TestCam", "2024-01-02", "clip.mp4")
            self.assertTrue(os.path.exists(dest))
        finally:
            ing.stop()

    def test_window_new_content_below_cutoff_is_skipped(self):
        """Contenido NUEVO sin volcado previo fuera de la ventana sí se
        descarta (el filtro de contenido sigue decidiendo sobre lo nuevo)."""
        ing = Ingestor(1, self.dst_dir, session_id=22,
                       content_mode="window",
                       content_filter={"window_days": 1})
        try:
            ing.handle_new_file(self._make_source())
            ing.executor.shutdown(wait=True)
            stats = ing.get_stats()
            self.assertEqual(stats["processed"], 0)
            self.assertEqual(stats["skipped"], 1)
        finally:
            ing.stop()


class TestUtils(unittest.TestCase):
    def test_resource_path_dev(self):
        from app.core.utils import resource_path
        p = resource_path(os.path.join("app", "ui", "logo.png"))
        self.assertTrue(p.endswith(os.path.join("app", "ui", "logo.png")))

    def test_is_removable_drive_darwin(self):
        from unittest.mock import patch
        from app.core import utils
        with patch.object(utils, "sys", spec=["platform"]) as fake_sys:
            fake_sys.platform = "darwin"
            self.assertTrue(utils.is_removable_drive("/Volumes/LEXAR"))
            self.assertFalse(utils.is_removable_drive("/System/Volumes/Data"))
            self.assertFalse(utils.is_removable_drive(""))

    def test_is_removable_drive_linux(self):
        from unittest.mock import patch
        from app.core import utils
        with patch.object(utils, "sys", spec=["platform"]) as fake_sys:
            fake_sys.platform = "linux"
            self.assertTrue(utils.is_removable_drive("/media/user/LEXAR"))
            self.assertTrue(utils.is_removable_drive("/mnt/card"))
            self.assertFalse(utils.is_removable_drive("/home/user"))

    def test_is_removable_drive_windows(self):
        """Windows: DRIVE_REMOVABLE (GetDriveTypeW==2) es el criterio. El flag
        FILE_REMOVABLE_MEDIA no se exige porque muchos lectores/pendrives no lo
        reportan aunque tengan medio válido: E:/F: (type 2) deben detectarse.
        Los discos fijos (type 3) no son removibles."""
        import sys as _sys
        import types as _types
        from unittest.mock import patch
        from app.core import utils

        def make_fake_ctypes(drive_type):
            class _Kernel32:
                @staticmethod
                def GetDriveTypeW(drive):
                    return drive_type

            class _Ctypes(_types.ModuleType):
                def __init__(self):
                    super().__init__("ctypes")
                    self.windll = type("windll", (),
                                       {"kernel32": _Kernel32()})()

            return _Ctypes()

        cases = [
            # drive_type, path, expected
            (2, "E:\\", True),   # lector/pendrive removible (con o sin medio)
            (2, "F:\\", True),
            (3, "C:\\", False),  # disco fijo
            (3, "H:\\", False),  # disco fijo (p. ej. unidad "Proyectos")
        ]
        for drive_type, path, expected in cases:
            fake = make_fake_ctypes(drive_type)
            with patch.object(utils, "sys",
                              spec=["platform"]) as fake_sys, \
                 patch.dict(_sys.modules, {"ctypes": fake}):
                fake_sys.platform = "win32"
                self.assertEqual(utils.is_removable_drive(path), expected)

    def test_get_drive_label_darwin_linux(self):
        from unittest.mock import patch
        from app.core import utils
        with patch.object(utils, "sys", spec=["platform"]) as fake_sys:
            fake_sys.platform = "darwin"
            self.assertEqual(utils.get_drive_label("/Volumes/LEXAR"), "LEXAR")
        with patch.object(utils, "sys", spec=["platform"]) as fake_sys:
            fake_sys.platform = "linux"
            self.assertEqual(utils.get_drive_label("/media/user/LEXAR"), "LEXAR")


if __name__ == "__main__":
    unittest.main()
