"""Pruebas del mixin CameraMixin (rename persistente por doble clic, quick 260908-f5o)."""

import os
import unittest
from unittest import mock

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from app.ui.mixins import camera_mixin


class _Harness(camera_mixin.CameraMixin):
    current_project_id = 1
    _source_paths = ["E:\\DCIM"]
    source_list = mock.MagicMock()
    ingest_status_label = mock.MagicMock()

    def _refresh_source_list(self):
        pass

    def _refresh_sessions_combo(self):
        pass

    def _persist_camera_mapping(self, session_id, source_path, nombre_dispositivo):
        self._persisted = (session_id, source_path, nombre_dispositivo)

    def update_start_button_state(self):
        pass

    @staticmethod
    def tr(text, *args):
        class _QtStr(str):
            def arg(self, value):
                return self
        return _QtStr(text)


def _setup_popup(mbox, clicked="yes", checkbox=False):
    mbox.Yes = 1
    mbox.No = 2
    mbox.Question = 3
    box = mbox.return_value
    yes_btn = mock.Mock()
    no_btn = mock.Mock()
    box.button.side_effect = lambda b: yes_btn if b == mbox.Yes else no_btn
    box.clickedButton.return_value = yes_btn if clicked == "yes" else no_btn
    box.setCheckBox = mock.Mock()
    dont_ask = mock.Mock()
    dont_ask.isChecked.return_value = checkbox
    camera_mixin.QCheckBox = mock.Mock(return_value=dont_ask)
    return box


class TestPromptRenameCamera(unittest.TestCase):
    def setUp(self):
        self.h = _Harness()
        self.h._persisted = None
        patcher = mock.patch.object(camera_mixin, "db")
        self.mock_db = patcher.start()
        self.addCleanup(patcher.stop)
        self.mock_db.get_sessions.return_value = [
            {"id": 7, "source_path": "E:\\DCIM", "nombre_dispositivo": "OldCam"}]
        camera_mixin.QSettings = mock.MagicMock()
        camera_mixin.QSettings().value.return_value = False

    def _input(self, text="Canon R5", ok=True):
        return mock.patch.object(camera_mixin, "QInputDialog",
                                 **{"getText.return_value": (text, ok)})

    def test_yes_persists_globally(self):
        with self._input(), \
             mock.patch.object(camera_mixin, "QMessageBox") as mbox:
            _setup_popup(mbox)
            self.h._prompt_rename_camera(0)
        self.mock_db.update_session_config.assert_called_once_with(
            7, nombre_dispositivo="Canon R5")
        self.assertEqual(self.h._persisted, (7, "E:\\DCIM", "Canon R5"))

    def test_no_persists_only_session(self):
        with self._input(), \
             mock.patch.object(camera_mixin, "QMessageBox") as mbox:
            _setup_popup(mbox, clicked="no")
            self.h._prompt_rename_camera(0)
        self.mock_db.update_session_config.assert_called_once_with(
            7, nombre_dispositivo="Canon R5")
        self.assertIsNone(self.h._persisted)

    def test_no_ask_checkbox_sets_skip_flag_and_persists(self):
        with self._input(), \
             mock.patch.object(camera_mixin, "QMessageBox") as mbox:
            _setup_popup(mbox, clicked="yes", checkbox=True)
            self.h._prompt_rename_camera(0)
        self.mock_db.update_session_config.assert_called_once_with(
            7, nombre_dispositivo="Canon R5")
        self.assertEqual(self.h._persisted, (7, "E:\\DCIM", "Canon R5"))
        camera_mixin.QSettings().setValue.assert_has_calls([
            mock.call("camera/skip_rename_confirm", True),
            mock.call("camera/rename_global_default", True),
        ])

    def test_skip_flag_bypasses_popup(self):
        camera_mixin.QSettings().value.return_value = True
        with self._input(), \
             mock.patch.object(camera_mixin, "QMessageBox") as mbox:
            self.h._prompt_rename_camera(0)
            mbox.assert_not_called()
        self.assertEqual(self.h._persisted, (7, "E:\\DCIM", "Canon R5"))
        self.mock_db.update_session_config.assert_called_once_with(
            7, nombre_dispositivo="Canon R5")

    def test_empty_name_persists_nothing(self):
        with self._input("   "), \
             mock.patch.object(camera_mixin, "QMessageBox") as mbox:
            _setup_popup(mbox)
            self.h._prompt_rename_camera(0)
            mbox.assert_not_called()
        self.mock_db.update_session_config.assert_not_called()
        self.assertIsNone(self.h._persisted)


if __name__ == "__main__":
    unittest.main()
