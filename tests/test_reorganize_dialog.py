"""Pruebas del reorganizador de footage (ReorganizeDialog).

Verifica: selector de carpeta, escaneo de SinClasificar/, agrupación por cámara/fecha,
movimiento con shutil.move + MD5 recalculado + re-registro en DB,
archivos sin clasificar permanecen en SinClasificar/, colisiones con sufijo (n),
independencia de ingestores activos (D-16..D-22).

CRÍTICO: nunca se usa ``.exec()`` modal real en offscreen. El diálogo se prueba
ejercitando sus métodos internos y workers con mocks.
"""

import os
import shutil
import tempfile
import unittest
from unittest import mock

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QDialog, QLabel, QPushButton, QTableWidget

import app.core.utils as utils_module
import app.core.db as db_module
import app.core.metadata_engine as meta_module
import app.core.ingestor as ingestor_module
import app.ui.reorganize_dialog as reorg_module
from app.ui.reorganize_dialog import ReorganizeDialog


class _FakeMetadataEngine:
    """Motor de metadatos fake con respuestas controlables."""

    def __init__(self, responses=None):
        # responses: dict path -> {"camera_model": "...", "creation_time": "..."}
        self.responses = responses or {}
        self.call_count = 0

    def get_video_metadata(self, path):
        self.call_count += 1
        return self.responses.get(path, {"camera_model": "", "creation_time": None})

    def get_file_type_info(self, path):
        return {"type": "video", "category": "footage"}


class _FakeDB:
    """Base de datos fake que registra llamadas a UPDATE."""

    def __init__(self):
        self.updates = []  # lista de (sql, params)
        self._conn = None

    def get_connection(self):
        # Retornar un objeto conexión mock
        class _FakeConn:
            def __init__(self, outer):
                self.outer = outer
                self.closed = False

            def cursor(self):
                class _FakeCursor:
                    def __init__(self, outer):
                        self.outer = outer

                    def execute(self, sql, params):
                        self.outer.outer.updates.append((sql, params))

                    def fetchall(self):
                        return []

                    def fetchone(self):
                        return None

                    def close(self):
                        pass

                return _FakeCursor(self)

            def commit(self):
                pass

            def close(self):
                self.closed = True

        return _FakeConn(self)


class TestReorganizeDialog(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="sdimport_reorg_")
        self.project_root = os.path.join(self.tmp, "project")
        os.makedirs(self.project_root)

        # Crear estructura SinClasificar/ con archivos de prueba
        self.sinclasificar = os.path.join(self.project_root, "SinClasificar")
        os.makedirs(self.sinclasificar)

        # Guardar funciones originales para restaurar
        self._orig_meta = reorg_module.metadata_engine
        self._orig_db = reorg_module.db
        self._orig_create_folder = reorg_module.create_folder_structure
        self._orig_calculate_md5 = reorg_module.calculate_md5

    def tearDown(self):
        reorg_module.metadata_engine = self._orig_meta
        reorg_module.db = self._orig_db
        reorg_module.create_folder_structure = self._orig_create_folder
        reorg_module.calculate_md5 = self._orig_calculate_md5
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _create_dialog(self, **kwargs):
        return ReorganizeDialog(None, project_root=self.project_root, **kwargs)

    # -------------------------------------------------------------------------
    # Estructura básica
    # -------------------------------------------------------------------------

    def test_dialog_title(self):
        dlg = self._create_dialog()
        self.assertEqual(dlg.windowTitle(), dlg.tr("Reorganizar footage…"))

    def test_folder_picker_exists(self):
        dlg = self._create_dialog()
        # Verificar que existe el botón "Examinar…" en la página 1
        self.assertTrue(hasattr(dlg, "btn_browse"))
        self.assertIsInstance(dlg.btn_browse, QPushButton)
        self.assertEqual(dlg.btn_browse.text(), dlg.tr("Examinar…"))

    def test_empty_sinclasificar_shows_info(self):
        # Eliminar SinClasificar para probar el caso vacío
        shutil.rmtree(self.sinclasificar, ignore_errors=True)
        dlg = self._create_dialog()
        # El diálogo debe mostrar un mensaje informativo (no crashear)
        # Verificamos que la página 1 tiene el label explicativo
        self.assertTrue(hasattr(dlg, "lbl_info"))

    # -------------------------------------------------------------------------
    # Escaneo y agrupación
    # -------------------------------------------------------------------------

    def test_scan_groups_by_camera_date(self):
        """Archivos en SinClasificar se agrupan por cámara y fecha."""
        # Crear archivos de prueba
        cam1_dir = os.path.join(self.sinclasificar, "cam1")
        os.makedirs(cam1_dir)
        f1 = os.path.join(cam1_dir, "clip1.mp4")
        f2 = os.path.join(cam1_dir, "clip2.mp4")
        with open(f1, "wb") as f:
            f.write(b"x" * 1024)
        with open(f2, "wb") as f:
            f.write(b"y" * 2048)

        # Mock metadata_engine: ambos archivos -> misma cámara, fechas distintas
        fake_meta = _FakeMetadataEngine({
            f1: {"camera_model": "Canon C300", "creation_time": "2024-01-15T10:00:00"},
            f2: {"camera_model": "Canon C300", "creation_time": "2024-01-16T14:30:00"},
        })
        reorg_module.metadata_engine = fake_meta

        dlg = self._create_dialog()
        # Ejecutar escaneo directamente (método interno)
        summary = dlg._scan_folder(self.project_root)

        # Verificar agrupación: 2 archivos, misma cámara, 2 fechas
        self.assertIn("Canon C300", summary)
        self.assertEqual(len(summary["Canon C300"]), 2)
        self.assertIn("2024-01-15", summary["Canon C300"])
        self.assertIn("2024-01-16", summary["Canon C300"])
        self.assertEqual(len(summary["Canon C300"]["2024-01-15"]), 1)
        self.assertEqual(len(summary["Canon C300"]["2024-01-16"]), 1)

    def test_unclassified_stays_in_folder(self):
        """Archivos sin metadata (camera_model vacío) quedan en SinClasificar/."""
        f1 = os.path.join(self.sinclasificar, "unknown1.mp4")
        f2 = os.path.join(self.sinclasificar, "unknown2.mp4")
        with open(f1, "wb") as f:
            f.write(b"a" * 512)
        with open(f2, "wb") as f:
            f.write(b"b" * 512)

        # Mock metadata_engine: devuelve camera_model vacío
        fake_meta = _FakeMetadataEngine({
            f1: {"camera_model": "", "creation_time": None},
            f2: {"camera_model": "", "creation_time": None},
        })
        reorg_module.metadata_engine = fake_meta

        dlg = self._create_dialog()
        # Usar el worker directamente para obtener tanto summary como unclassified
        from app.ui.reorganize_dialog import _ScanWorker
        worker = _ScanWorker(self.project_root)
        success, result = True, None
        def capture(s, r):
            nonlocal success, result
            success, result = s, r
        worker.finished.connect(capture)
        worker.run()
        from PySide6.QtWidgets import QApplication
        QApplication.processEvents()

        self.assertTrue(success)
        self.assertIn("unclassified", result)
        self.assertEqual(len(result["unclassified"]), 2)
        # Los archivos no clasificados se reportan en la lista unclassified
        self.assertIn(f1, result["unclassified"])
        self.assertIn(f2, result["unclassified"])

    # -------------------------------------------------------------------------
    # Movimiento + MD5 + DB
    # -------------------------------------------------------------------------

    def test_move_and_md5_recalc(self):
        """Movimiento ejecuta shutil.move, calculate_md5 y UPDATE en DB."""
        f1 = os.path.join(self.sinclasificar, "clip.mp4")
        with open(f1, "wb") as f:
            f.write(b"test content for md5")

        fake_meta = _FakeMetadataEngine({
            f1: {"camera_model": "Sony A7", "creation_time": "2024-03-10T12:00:00"},
        })
        fake_db = _FakeDB()
        fake_create_folder = mock.MagicMock(return_value=os.path.join(self.project_root, "Footage", "Sony A7", "2024-03-10"))
        fake_calculate_md5 = mock.MagicMock(return_value="d41d8cd98f00b204e9800998ecf8427e")

        reorg_module.metadata_engine = fake_meta
        reorg_module.db = fake_db
        reorg_module.create_folder_structure = fake_create_folder
        reorg_module.calculate_md5 = fake_calculate_md5

        with mock.patch("shutil.move") as mock_move:
            dlg = self._create_dialog()
            summary = {"Sony A7": {"2024-03-10": [f1]}}
            dlg._execute_move(self.project_root, summary)

            # Verificar shutil.move llamado
            mock_move.assert_called_once()
            args, _ = mock_move.call_args
            self.assertEqual(args[0], f1)
            self.assertTrue(args[1].endswith("clip.mp4"))

            # Verificar calculate_md5 llamado
            fake_calculate_md5.assert_called_once()

            # Verificar UPDATE en DB
            self.assertEqual(len(fake_db.updates), 1)
            sql, params = fake_db.updates[0]
            self.assertIn("UPDATE files SET dest_path = ?, md5_hash = ?", sql)
            self.assertEqual(params[1], "d41d8cd98f00b204e9800998ecf8427e")

    def test_collision_suffix(self):
        """Si el destino existe, se aplica sufijo (n)."""
        f1 = os.path.join(self.sinclasificar, "clip.mp4")
        with open(f1, "wb") as f:
            f.write(b"content")

        # Crear archivo destino existente
        dest_dir = os.path.join(self.project_root, "Footage", "Sony A7", "2024-03-10")
        os.makedirs(dest_dir)
        existing = os.path.join(dest_dir, "clip.mp4")
        with open(existing, "wb") as f:
            f.write(b"existing")

        fake_meta = _FakeMetadataEngine({
            f1: {"camera_model": "Sony A7", "creation_time": "2024-03-10T12:00:00"},
        })
        fake_db = _FakeDB()
        fake_create_folder = mock.MagicMock(return_value=dest_dir)
        fake_calculate_md5 = mock.MagicMock(return_value="abcd1234")

        reorg_module.metadata_engine = fake_meta
        reorg_module.db = fake_db
        reorg_module.create_folder_structure = fake_create_folder
        reorg_module.calculate_md5 = fake_calculate_md5

        with mock.patch("shutil.move") as mock_move:
            dlg = self._create_dialog()
            summary = {"Sony A7": {"2024-03-10": [f1]}}
            dlg._execute_move(self.project_root, summary)

            # Verificar que shutil.move recibió un path con sufijo (1)
            args, _ = mock_move.call_args
            dest_path = args[1]
            self.assertTrue(dest_path.endswith("clip (1).mp4"))

    # -------------------------------------------------------------------------
    # Independencia de ingestores
    # -------------------------------------------------------------------------

    def test_independent_of_ingestors(self):
        """El diálogo funciona sin self._ingestors activo."""
        dlg = self._create_dialog()
        # No debe haber referencias a _ingestors ni Ingestor en el diálogo
        self.assertFalse(hasattr(dlg, "_ingestors"))
        # El diálogo no importa Ingestor
        import app.ui.reorganize_dialog as reorg_module
        self.assertNotIn("Ingestor", dir(reorg_module))

    # -------------------------------------------------------------------------
    # Worker threads
    # -------------------------------------------------------------------------

    def test_scan_worker_emits_signals(self):
        """_ScanWorker emite progress y finished correctamente."""
        dlg = self._create_dialog()
        from app.ui.reorganize_dialog import _ScanWorker

        # Crear archivo real en disco
        test_file = os.path.join(self.sinclasificar, "a.mp4")
        with open(test_file, "wb") as f:
            f.write(b"test")

        fake_meta = _FakeMetadataEngine({
            test_file: {"camera_model": "Cam", "creation_time": "2024-01-01T00:00:00"},
        })
        reorg_module.metadata_engine = fake_meta

        worker = _ScanWorker(self.project_root)
        result_container = []

        def on_finished(success, result):
            result_container.append((success, result))

        worker.finished.connect(on_finished)
        worker.run()

        self.assertEqual(len(result_container), 1)
        success, result = result_container[0]
        self.assertTrue(success)
        self.assertIn("Cam", result.get("summary", {}))

    def test_move_worker_emits_signals(self):
        """_MoveWorker emite progress y finished correctamente."""
        f1 = os.path.join(self.sinclasificar, "clip.mp4")
        with open(f1, "wb") as f:
            f.write(b"move test")

        fake_db = _FakeDB()
        fake_create_folder = mock.MagicMock(return_value=os.path.join(self.project_root, "Footage", "Cam", "2024-01-01"))
        fake_calculate_md5 = mock.MagicMock(return_value="md5hash")

        reorg_module.db = fake_db
        reorg_module.create_folder_structure = fake_create_folder
        reorg_module.calculate_md5 = fake_calculate_md5

        from app.ui.reorganize_dialog import _MoveWorker
        summary = {"Cam": {"2024-01-01": [f1]}}
        worker = _MoveWorker(self.project_root, summary, [])

        result_container = []
        def on_finished(success, result):
            result_container.append((success, result))
        worker.finished.connect(on_finished)
        worker.run()

        self.assertEqual(len(result_container), 1)
        success, result = result_container[0]
        self.assertTrue(success)
        # Verificar que el resultado contiene estadísticas
        self.assertIn("moved", result)
        self.assertIn("unclassified", result)


if __name__ == "__main__":
    unittest.main()