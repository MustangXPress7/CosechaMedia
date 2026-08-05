"""Pruebas del volcado selectivo por fecha (offscreen).

Se instancia SelectiveDumpAssistant y se ejercita la lógica de construcción de
jobs y el volcado verificado sin necesidad de ejecutar el escaneo async."""
import os
import shutil
import tempfile
import unittest
from datetime import datetime

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import Qt, QDate
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QDialog

import app.ui.selective_dump as sd_module
from app.core.db import DatabaseManager
from app.ui.selective_dump import SelectiveDumpAssistant


class FakeMeta:
    def get_video_metadata(self, path):
        return {"camera_model": "iPhone 15", "camera_make": "Apple",
                "creation_dt": None, "date_source": None}

    def get_file_type_info(self, path):
        return {"type": "video", "category": "footage"}


class FakeWorker:
    class Sig:
        def emit(self, *args):
            pass

    progress = Sig()
    message = Sig()


class TestSelectiveDump(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="sdimport_sd_")
        self.src = os.path.join(self.tmp, "src")
        self.dest = os.path.join(self.tmp, "dest")
        os.makedirs(self.src)
        os.makedirs(os.path.join(self.src, "DCIM"))
        os.makedirs(self.dest)

        self.day1 = datetime(2024, 1, 2)
        self.day2 = datetime(2024, 1, 5)
        self.files = {
            "clip1.mp4": self.day1,
            "clip2.mp4": self.day1,
            "clip3.mov": self.day2,
        }
        for name, _dt in self.files.items():
            with open(os.path.join(self.src, "DCIM", name), "wb") as f:
                f.write(os.urandom(2048))

        self._orig_db = sd_module.db
        self._orig_meta = sd_module.metadata_engine
        self.db = DatabaseManager(db_path=os.path.join(self.tmp, "sel.db"))
        sd_module.db = self.db
        sd_module.metadata_engine = FakeMeta()

        conn = self.db.get_connection()
        cursor = conn.cursor()
        cursor.execute("INSERT INTO projects (name, root_path) VALUES ('P', ?)", (self.dest,))
        self.pid = cursor.lastrowid
        conn.commit()
        conn.close()

        self.dlg = SelectiveDumpAssistant(
            source_path=self.src,
            project_config={
                "dest_root": self.dest,
                "folder_name": "Footage",
                "organization_type": 0,  # camera_first
                "default_camera": "",
                "project_id": self.pid,
                "use_metadata_date": True,
            },
        )

    def tearDown(self):
        self.dlg.close()
        sd_module.db = self._orig_db
        sd_module.metadata_engine = self._orig_meta
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _set_scan(self, only=None):
        by_date = {}
        for name, dt in self.files.items():
            path = os.path.join(self.src, "DCIM", name)
            if only is not None and path not in only:
                continue
            key = dt.strftime("%Y-%m-%d")
            by_date.setdefault(key, []).append(path)
        self.dlg._scan_result = {"by_date": by_date, "no_date": [], "total": sum(len(v) for v in by_date.values())}
        self.dlg._populate_calendar(self.dlg._scan_result)

    def test_setup_page_has_no_path_inputs(self):
        self.assertFalse(hasattr(self.dlg, "src_input"),
                         "El setup no debe pedir ruta de origen (redundante con el proyecto)")
        self.assertFalse(hasattr(self.dlg, "dst_input"),
                         "El setup no debe pedir ruta maestra (redundante con el proyecto)")

    def test_calendar_population_and_select_all(self):
        self._set_scan()
        self.assertEqual(len(self.dlg.calendar.day_counts), 2)
        self.assertEqual(len(self.dlg.calendar.selected), 2)
        jobs = self.dlg._build_jobs()
        self.assertEqual(len(jobs), 3)

    def test_build_jobs_respects_selected_days(self):
        self._set_scan()
        self.dlg.calendar.clear_selection()
        self.dlg.calendar.selected.add(QDate(2024, 1, 2))
        jobs = self.dlg._build_jobs()
        self.assertEqual(len(jobs), 2)
        for job in jobs:
            self.assertEqual(job["date"], "2024-01-02")
            self.assertEqual(job["camera"], "iPhone 15")

    def test_unique_dest_suffixes(self):
        dest_dir = os.path.join(self.dest, "x")
        os.makedirs(dest_dir)
        p1 = os.path.join(dest_dir, "clip.mp4")
        with open(p1, "wb") as f:
            f.write(b"a")
        unique = self.dlg._unique_dest(dest_dir, os.path.join(self.src, "clip.mp4"))
        self.assertEqual(os.path.basename(unique), "clip (1).mp4")

    def test_dump_work_verified_copy_and_db(self):
        self._set_scan()
        jobs = self.dlg._build_jobs()
        self.dlg._jobs = jobs
        result = self.dlg._dump_work(FakeWorker())

        self.assertEqual(result["processed"], 3)
        self.assertEqual(result["errors"], 0)

        base = os.path.join(self.dest, "Footage", "iPhone 15")
        for name, dt in self.files.items():
            dest_path = os.path.join(base, dt.strftime("%Y-%m-%d"), name)
            self.assertTrue(os.path.exists(dest_path), f"Falta {dest_path}")
            self.assertEqual(
                _md5(dest_path),
                _md5(os.path.join(self.src, "DCIM", name)),
            )

        conn = self.db.get_connection()
        count = conn.execute("SELECT count(*) FROM files WHERE session_id = ?", (str(result["session_id"]),)).fetchone()[0]
        sess = self.db.get_session(result["session_id"])
        conn.close()
        self.assertEqual(count, 3)
        self.assertEqual(sess["status"], "completed")
        self.assertEqual(sess["source_path"], self.src)

    def test_filter_mode_apply_subset(self):
        dlg = SelectiveDumpAssistant(source_path=self.src, mode="filter", auto_scan=False)
        try:
            dlg._scan_result = {
                "by_date": {
                    "2024-01-02": [os.path.join(self.src, "DCIM", "clip1.mp4"),
                                   os.path.join(self.src, "DCIM", "clip2.mp4")],
                    "2024-01-05": [os.path.join(self.src, "DCIM", "clip3.mov")],
                },
                "no_date": [],
                "total": 3,
            }
            dlg._populate_calendar(dlg._scan_result)
            dlg.calendar.clear_selection()
            dlg.calendar.selected.add(QDate(2024, 1, 5))
            dlg.chk_include_nodate.setChecked(False)
            dlg._apply_selection()
            self.assertEqual(dlg.content_filter,
                             {"dates": ["2024-01-05"], "include_nodate": False})
            self.assertEqual(dlg.content_text, "el 5-1-24")
        finally:
            dlg.close()

    def test_filter_mode_full_selection_normalizes_to_none(self):
        dlg = SelectiveDumpAssistant(source_path=self.src, mode="filter", auto_scan=False)
        try:
            dlg._scan_result = {
                "by_date": {"2024-01-02": ["a.mp4"], "2024-01-05": ["b.mp4"]},
                "no_date": [],
                "total": 2,
            }
            dlg._populate_calendar(dlg._scan_result)
            dlg.chk_include_nodate.setChecked(False)
            dlg._apply_selection()
            self.assertIsNone(dlg.content_filter)
            self.assertEqual(dlg.content_text, "Todo")
        finally:
            dlg.close()

    def test_filter_mode_keeps_nodate_when_not_full(self):
        dlg = SelectiveDumpAssistant(source_path=self.src, mode="filter", auto_scan=False)
        try:
            dlg._scan_result = {
                "by_date": {"2024-01-02": ["a.mp4"]},
                "no_date": ["sindate.mp4"],
                "total": 2,
            }
            dlg._populate_calendar(dlg._scan_result)
            dlg.calendar.clear_selection()
            dlg.calendar.selected.add(QDate(2024, 1, 2))
            dlg.chk_include_nodate.setChecked(False)
            dlg._apply_selection()
            self.assertEqual(dlg.content_filter,
                             {"dates": ["2024-01-02"], "include_nodate": False})
        finally:
            dlg.close()


class TestCalendarInteraction(unittest.TestCase):
    """Clic/ctrl+clic sobre el calendario y comportamiento de cerrar/cancelar."""

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="sdimport_cal_")
        self.src = os.path.join(self.tmp, "src")
        self.dest = os.path.join(self.tmp, "dest")
        os.makedirs(os.path.join(self.src, "DCIM"))
        os.makedirs(self.dest)
        self.day1 = datetime(2024, 1, 2)
        self.day2 = datetime(2024, 1, 5)
        self.files = {"clip1.mp4": self.day1, "clip3.mov": self.day2}
        for name, dt in self.files.items():
            with open(os.path.join(self.src, "DCIM", name), "wb") as f:
                f.write(os.urandom(1024))

        self._orig_db = sd_module.db
        self._orig_meta = sd_module.metadata_engine
        self.db = DatabaseManager(db_path=os.path.join(self.tmp, "cal.db"))
        sd_module.db = self.db
        sd_module.metadata_engine = FakeMeta()
        conn = self.db.get_connection()
        cursor = conn.cursor()
        cursor.execute("INSERT INTO projects (name, root_path) VALUES ('P', ?)", (self.dest,))
        self.pid = cursor.lastrowid
        conn.commit()
        conn.close()

        self.dlg = SelectiveDumpAssistant(
            source_path=self.src,
            project_config={
                "dest_root": self.dest, "folder_name": "Footage",
                "organization_type": 0, "default_camera": "",
                "project_id": self.pid, "use_metadata_date": True,
            },
        )

    def tearDown(self):
        self.dlg.close()
        sd_module.db = self._orig_db
        sd_module.metadata_engine = self._orig_meta
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _show_select_page(self):
        by_date = {}
        for name, dt in self.files.items():
            path = os.path.join(self.src, "DCIM", name)
            key = dt.strftime("%Y-%m-%d")
            by_date.setdefault(key, []).append(path)
        self.dlg._scan_result = {"by_date": by_date, "no_date": [], "total": 2}
        self.dlg._populate_calendar(self.dlg._scan_result)
        self.dlg._stack.setCurrentWidget(self.dlg._select_page)
        self.dlg.show()
        self.app.processEvents()

    def _cell_center(self, row, col):
        view = self.dlg.calendar._grid
        rect = view.visualRect(view.model().index(row, col))
        return rect.center()

    def test_simple_click_selects_day(self):
        self._show_select_page()
        self.dlg.calendar.clear_selection()
        QTest.mouseClick(self.dlg.calendar._grid_viewport, Qt.LeftButton, pos=self._cell_center(1, 2))
        self.app.processEvents()
        self.assertEqual(self.dlg.calendar.selected,
                         {QDate(2024, 1, 2)})

    def test_ctrl_click_toggles_day(self):
        self._show_select_page()
        self.dlg.calendar.clear_selection()
        cal = self.dlg.calendar
        QTest.mouseClick(cal._grid_viewport, Qt.LeftButton, pos=self._cell_center(1, 2))
        self.app.processEvents()
        QTest.mouseClick(cal._grid_viewport, Qt.LeftButton, Qt.ControlModifier, pos=self._cell_center(1, 5))
        self.app.processEvents()
        self.assertEqual(cal.selected, {QDate(2024, 1, 2), QDate(2024, 1, 5)})
        QTest.mouseClick(cal._grid_viewport, Qt.LeftButton, Qt.ControlModifier, pos=self._cell_center(1, 2))
        self.app.processEvents()
        self.assertEqual(cal.selected, {QDate(2024, 1, 5)})

    def test_click_on_weekday_header_ignored(self):
        self._show_select_page()
        self.dlg.calendar.clear_selection()
        QTest.mouseClick(self.dlg.calendar._grid_viewport, Qt.LeftButton, pos=self._cell_center(0, 1))
        self.app.processEvents()
        self.assertEqual(self.dlg.calendar.selected, set())

    def test_click_via_calendar_widget_also_works(self):
        self._show_select_page()
        self.dlg.calendar.clear_selection()
        view = self.dlg.calendar._grid
        pos = self._cell_center(1, 2) + view.pos()
        QTest.mouseClick(self.dlg.calendar, Qt.LeftButton, pos=pos)
        self.app.processEvents()
        self.assertEqual(self.dlg.calendar.selected, {QDate(2024, 1, 2)})

    def test_reject_closes_when_idle(self):
        self._show_select_page()
        self.dlg.reject()
        self.app.processEvents()
        self.assertEqual(self.dlg.result(), QDialog.Rejected)

    def test_reject_during_work_cancels_but_does_not_close(self):
        class FakeThread:
            def isRunning(self):
                return True

        self.dlg._thread = FakeThread()
        self.dlg._stack.setCurrentWidget(self.dlg._scan_page)
        self.dlg.show()
        self.app.processEvents()
        self.dlg.reject()
        self.app.processEvents()
        self.assertTrue(self.dlg._cancel_flag)
        self.assertTrue(self.dlg._close_when_done)
        self.assertTrue(self.dlg.isVisible())

    def test_scan_done_closes_when_requested(self):
        self.dlg._close_when_done = True
        self.dlg._on_scan_done(True, {"source": self.src, "result": {}})
        self.app.processEvents()
        self.assertEqual(self.dlg.result(), QDialog.Rejected)
        self.assertFalse(self.dlg._close_when_done)

    def test_scan_done_cancelled_returns_to_setup(self):
        self.dlg._cancel_flag = True
        self.dlg._on_scan_done(True, {"source": self.src, "result": {}})
        self.app.processEvents()
        self.assertEqual(self.dlg._stack.currentWidget(), self.dlg._setup_page)
        self.assertFalse(self.dlg._cancel_flag)

    def test_cancel_button_gives_feedback(self):
        self.dlg._stack.setCurrentWidget(self.dlg._scan_page)
        self.dlg._cancel_current_work()
        self.assertTrue(self.dlg._cancel_flag)
        self.assertFalse(self.dlg.btn_scan_cancel.isEnabled())
        self.assertIn("Cancelando", self.dlg.scan_status.text())

    def test_reject_with_deleted_thread_does_not_crash(self):
        class GoneThread:
            def isRunning(self):
                raise RuntimeError(
                    "libshiboken: Internal C++ object (PySide6.QtCore.QThread) already deleted.")

        self.dlg._thread = GoneThread()
        self.dlg.reject()
        self.app.processEvents()
        self.assertEqual(self.dlg.result(), QDialog.Rejected)
        self.assertIsNone(self.dlg._thread)

    def test_thread_reference_cleared_on_finish(self):
        self.dlg._on_thread_finished()
        self.assertIsNone(self.dlg._thread)
        self.assertIsNone(self.dlg._worker)


class TestContentSummary(unittest.TestCase):
    def test_none_is_todo(self):
        self.assertEqual(sd_module.content_summary(None), "Todo")

    def test_single_day(self):
        self.assertEqual(sd_module.content_summary({"dates": ["2025-05-25"]}), "el 25-5-25")

    def test_contiguous_range(self):
        filt = {"dates": ["2025-05-25", "2025-05-26", "2025-05-27"]}
        self.assertEqual(sd_module.content_summary(filt), "del 25-5-25 al 27-5-25")

    def test_range_across_years(self):
        filt = {"dates": ["2025-12-31", "2026-01-01"]}
        self.assertEqual(sd_module.content_summary(filt), "del 31-12-25 al 1-1-26")

    def test_multiple_segments(self):
        filt = {"dates": ["2025-05-25", "2025-05-27"]}
        self.assertEqual(sd_module.content_summary(filt), "2 días")

    def test_only_nodate(self):
        filt = {"dates": [], "include_nodate": True}
        self.assertEqual(sd_module.content_summary(filt), "Solo sin fecha")

    def test_with_nodate(self):
        filt = {"dates": ["2025-05-25"], "include_nodate": True}
        self.assertEqual(sd_module.content_summary(filt), "el 25-5-25 · sin fecha")


def _md5(path):
    import hashlib
    h = hashlib.md5()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


if __name__ == "__main__":
    unittest.main()
