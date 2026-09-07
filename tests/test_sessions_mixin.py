import unittest
from unittest import mock

from app.ui.mixins import sessions_mixin


class _Harness(sessions_mixin.SessionsMixin):
    current_project_id = 1
    current_session_id = None
    btn_delete_session = mock.MagicMock()
    session_src_label = mock.MagicMock()
    session_dest_label = mock.MagicMock()
    _btn_browse_sess_src = mock.MagicMock()
    _btn_browse_sess_dest = mock.MagicMock()

    def __init__(self):
        self.ingest_status_label = mock.MagicMock()
        self.sessions_combo = mock.MagicMock()
        self.sessions_combo.currentData.return_value = 99
        self.sessions_combo.findData.return_value = 0
        self._restore_session_id = None

    def _update_session_dump_switch(self):
        pass

    @staticmethod
    def tr(text, *args):
        class _QtStr(str):
            def arg(self, value):
                return self

        return _QtStr(text)


class TestAddManualSession(unittest.TestCase):
    """_add_manual_session must call db.create_session with a date string
    and refresh the combo. Regression of i6a: QDate was never imported
    (NameError on QDate.currentDate())."""

    @mock.patch.object(sessions_mixin, "QInputDialog")
    @mock.patch.object(sessions_mixin, "db")
    def test_creates_session(self, mock_db, mock_qid):
        mock_db.create_session.return_value = 42
        mock_db.get_sessions.return_value = []
        mock_qid.getText.return_value = ("Sesión test", True)
        h = _Harness()
        h._add_manual_session()
        mock_db.create_session.assert_called_once()
        args = mock_db.create_session.call_args[0]
        self.assertEqual(args[0], 1)
        self.assertEqual(args[1], "Sesión test")
        # Third arg must be a date string like "2026-09-07"
        import re
        self.assertRegex(args[2], r"^\d{4}-\d{2}-\d{2}$")
        self.assertEqual(args[3], "active")

    @mock.patch.object(sessions_mixin, "QInputDialog")
    @mock.patch.object(sessions_mixin, "db")
    def test_refreshes_combo(self, mock_db, mock_qid):
        mock_db.create_session.return_value = 10
        mock_db.get_sessions.return_value = []
        mock_qid.getText.return_value = ("S", True)
        h = _Harness()
        h._add_manual_session()
        h.sessions_combo.blockSignals.assert_called()
        h.sessions_combo.clear.assert_called()
        h.sessions_combo.findData.assert_called_with(10)
        h.ingest_status_label.setText.assert_called_once()

    @mock.patch.object(sessions_mixin, "QInputDialog")
    @mock.patch.object(sessions_mixin, "db")
    def test_cancel_does_not_create(self, mock_db, mock_qid):
        mock_qid.getText.return_value = ("", False)
        h = _Harness()
        h._add_manual_session()
        mock_db.create_session.assert_not_called()


if __name__ == "__main__":
    unittest.main()