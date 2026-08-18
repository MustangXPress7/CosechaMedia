"""Pruebas de la tabla de orígenes: columna 'Contenido' y cambio de ruta por doble clic."""
import os
import json
import tempfile
import shutil
import unittest
from unittest import mock

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import (QApplication, QFileDialog, QHBoxLayout, QHeaderView,
                              QPushButton, QWidget)

import app.ui.main_window as mw
import app.core.ingestor as ingestor_module
from app.core.db import DatabaseManager


class TestSourceContent(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    @staticmethod
    def _content_button(row, table):
        wrapper = table.cellWidget(row, 2)
        if isinstance(wrapper, QWidget):
            for child in wrapper.findChildren(QPushButton):
                return child
        return wrapper

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="sdimport_src_")
        self.src = os.path.join(self.tmp, "src")
        self.dest = os.path.join(self.tmp, "dest")
        os.makedirs(self.src)
        os.makedirs(self.dest)

        self._orig_db = mw.db
        self._orig_ing_db = ingestor_module.db
        self._orig_notif = mw.NotificationManager
        self.db = DatabaseManager(db_path=os.path.join(self.tmp, "src.db"))
        mw.db = self.db
        ingestor_module.db = self.db

        class StubNotif:
            def notify_ingest_complete(self, stats):
                pass

            def notify_ingest_stopped(self):
                pass

            def notify_ingest_failed(self, stats=None):
                pass

        mw.NotificationManager = StubNotif

        conn = self.db.get_connection()
        cursor = conn.cursor()
        cursor.execute("INSERT INTO projects (name, root_path) VALUES ('P', ?)", (self.dest,))
        self.pid = cursor.lastrowid
        conn.commit()
        conn.close()

        self.sid = self.db.create_session(self.pid, "Sesión", "2024-01-02", "active", self.src)

        self.window = mw.MainWindow()
        self.window.current_project_id = self.pid
        self.window.dest_root = self.dest
        self.window._source_paths = [self.src]

    def tearDown(self):
        self.window.close()
        mw.db = self._orig_db
        ingestor_module.db = self._orig_ing_db
        mw.NotificationManager = self._orig_notif
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_source_list_has_content_column_with_button(self):
        self.window._refresh_source_list()
        self.assertEqual(self.window.source_list.columnCount(), 4)
        btn = self._content_button(0, self.window.source_list)
        self.assertIsNotNone(btn)
        self.assertEqual(btn.text(), "Todo")
        self.assertTrue(btn.isEnabled())

    def test_content_button_disabled_without_session(self):
        other = os.path.join(self.tmp, "other")
        os.makedirs(other)
        self.window._source_paths = [self.src, other]
        self.window._refresh_source_list()
        btn = self._content_button(1, self.window.source_list)
        self.assertFalse(btn.isEnabled())

    def test_content_button_shows_summary(self):
        filt = json.dumps({"dates": ["2025-05-25", "2025-05-26"], "include_nodate": False})
        self.db.update_session_config(self.sid, content_filter=filt)
        self.window._refresh_source_list()
        btn = self._content_button(0, self.window.source_list)
        self.assertEqual(btn.text(), "del 25-5-25 al 26-5-25")

    def test_change_source_path_updates_session(self):
        new_src = os.path.join(self.tmp, "new_src")
        os.makedirs(new_src)
        self.window._refresh_source_list()
        with mock.patch.object(QFileDialog, "getExistingDirectory", return_value=new_src):
            self.window._prompt_change_source_path(0)
        sessions = self.db.get_sessions(self.pid)
        self.assertEqual(sessions[0]["source_path"], new_src)
        self.assertIn(new_src, self.window._source_paths)
        self.assertNotIn(self.src, self.window._source_paths)

    def test_change_source_path_rejects_duplicate(self):
        other = os.path.join(self.tmp, "other")
        os.makedirs(other)
        self.window._source_paths = [self.src, other]
        self.window._refresh_source_list()
        with mock.patch.object(QFileDialog, "getExistingDirectory", return_value=other), \
             mock.patch.object(mw.QMessageBox, "information") as info:
            self.window._prompt_change_source_path(0)
        info.assert_called_once()
        sessions = self.db.get_sessions(self.pid)
        self.assertEqual(sessions[0]["source_path"], self.src)

    def test_ingest_table_has_progress_column(self):
        self.assertEqual(self.window.table.columnCount(), 6)
        headers = [self.window.table.horizontalHeaderItem(i).text() for i in range(6)]
        self.assertIn("Progreso", headers)

    def test_selective_dump_button_present(self):
        # B-01: «Volcado selectivo…» vive ahora en el área pre-ingesta de orígenes.
        self.assertTrue(hasattr(self.window, "btn_selective_dump"))
        with mock.patch.object(self.window, "_open_selective_dump") as op:
            self.window.btn_selective_dump.click()
            op.assert_called_once()

    def test_selective_dump_button_in_scan_row_not_operations(self):
        scan_row = None
        op_row = None
        for layout in self.window.findChildren(QHBoxLayout):
            widgets = [layout.itemAt(i).widget() for i in range(layout.count())]
            widgets = [w for w in widgets if w is not None]
            if self.window.btn_scan_cameras in widgets:
                scan_row = layout
            if self.window.btn_clear_completed in widgets:
                op_row = layout
        self.assertIsNotNone(scan_row)
        self.assertIsNotNone(op_row)
        scan_widgets = [scan_row.itemAt(i).widget() for i in range(scan_row.count())]
        op_widgets = [op_row.itemAt(i).widget() for i in range(op_row.count())]
        self.assertIn(self.window.btn_selective_dump, scan_widgets)
        self.assertNotIn(self.window.btn_selective_dump, op_widgets)

    def test_source_path_column_interactive_with_default_width(self):
        self.window._refresh_source_list()
        header = self.window.source_list.horizontalHeader()
        self.assertEqual(header.sectionResizeMode(0), QHeaderView.Interactive)
        self.assertFalse(header.stretchLastSection())
        self.assertEqual(header.sectionSize(0), 100)
        header.resizeSection(0, 200)
        self.assertEqual(header.sectionSize(0), 200)

    def test_source_list_has_per_row_delete_column(self):
        self.window._refresh_source_list()
        self.assertEqual(self.window.source_list.columnCount(), 4)
        btn = self.window.source_list.cellWidget(0, 3)
        self.assertIsNotNone(btn)
        self.assertIsInstance(btn, QPushButton)
        self.assertFalse(btn.icon().isNull())
        self.assertFalse(hasattr(self.window, "btn_remove_source"))

    def test_source_delete_button_removes_source_with_confirmation(self):
        self.window._refresh_source_list()
        btn = self.window.source_list.cellWidget(0, 3)
        with mock.patch.object(mw.QMessageBox, "question", return_value=mw.QMessageBox.Yes):
            btn.click()
        self.assertEqual(self.db.get_sessions(self.pid), [])
        self.assertNotIn(self.src, self.window._source_paths)

    def test_source_delete_button_no_keeps_session(self):
        self.window._refresh_source_list()
        btn = self.window.source_list.cellWidget(0, 3)
        with mock.patch.object(mw.QMessageBox, "question", return_value=mw.QMessageBox.No):
            btn.click()
        self.assertEqual(len(self.db.get_sessions(self.pid)), 1)

    def test_files_table_delete_button_removes_row_only(self):
        self.window.on_file_started(os.path.join(self.src, "clip.mp4"))
        self.assertEqual(self.window.table.rowCount(), 1)
        btn = self.window.table.cellWidget(0, 5)
        self.assertIsNotNone(btn)
        before = len(self.db.get_sessions(self.pid))
        btn.click()
        self.assertEqual(self.window.table.rowCount(), 0)
        self.assertEqual(len(self.db.get_sessions(self.pid)), before)

    def test_files_table_delete_follows_sorting(self):
        self.window.on_file_started(os.path.join(self.src, "BBB.mp4"))
        self.window.on_file_started(os.path.join(self.src, "AAA.mp4"))
        key = self.window._file_row_key(os.path.join(self.src, "BBB.mp4"), None)
        item = self.window._file_row_map[key]
        self.window.table.sortItems(0)
        row = self.window.table.indexFromItem(item).row()
        self.assertEqual(row, 1)
        self.window.table.cellWidget(row, 5).click()
        self.assertEqual(self.window.table.rowCount(), 1)
        self.assertEqual(self.window.table.item(0, 0).text(), "AAA.mp4")

    def test_on_copy_progress_updates_cell(self):
        self.window.on_file_started("clip.mp4")
        item = self.window._file_row_map["clip.mp4"]
        row = self.window.table.indexFromItem(item).row()
        self.window.on_copy_progress("clip.mp4", 50, 100)
        self.assertEqual(self.window.table.item(row, 3).text(), "50%")
        self.window.on_file_finished("clip.mp4", "/out/clip.mp4", True, {})
        self.assertEqual(self.window.table.item(row, 3).text(), "100%")

    def test_on_copy_progress_clamped(self):
        self.window.on_file_started("big.mp4")
        item = self.window._file_row_map["big.mp4"]
        row = self.window.table.indexFromItem(item).row()
        self.window.on_copy_progress("big.mp4", 999999, 100)
        self.assertEqual(self.window.table.item(row, 3).text(), "100%")

    def test_session_custom_destination_override(self):
        self.window.current_project_id = self.pid
        self.window._refresh_sessions_combo()
        idx = self.window.sessions_combo.findData(self.sid)
        self.assertNotEqual(idx, -1, "La sesión debe aparecer en el combo")
        self.window.sessions_combo.setCurrentIndex(idx)
        self.window._on_session_selected(idx)
        self.assertEqual(self.window.current_session_id, self.sid)
        self.assertFalse(self.window._btn_browse_sess_src.isHidden())

        custom = os.path.join(self.tmp, "custom_dest")
        self.window.session_dest_label.setText(custom)
        self.window._save_session_override()
        self.assertEqual(self.db.get_session(self.sid)["destination_override"], custom)

        self.window.session_dest_label.setText(self.window.tr("Por defecto"))
        self.window._save_session_override()
        self.assertIsNone(self.db.get_session(self.sid)["destination_override"])

    @mock.patch.object(mw, "FileSystemWatcher")
    @mock.patch.object(mw, "Ingestor")
    def test_start_ingest_passes_content_filter(self, MockIngestor, MockWatcher):
        self.db.update_session_config(
            self.sid, content_filter=json.dumps({"dates": ["2024-01-02"], "include_nodate": True}))
        self.window.start_ingest()
        kwargs = MockIngestor.call_args.kwargs
        self.assertEqual(kwargs["content_filter"], {"dates": ["2024-01-02"], "include_nodate": True})


if __name__ == "__main__":
    unittest.main()
