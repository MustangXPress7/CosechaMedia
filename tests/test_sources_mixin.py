import unittest
from unittest import mock

from app.ui.mixins import sources_mixin


class _Harness(sources_mixin.SourcesMixin):
    current_project_id = None

    @staticmethod
    def tr(text, *args):
        return text


class TestPickSourceEntryNoProject(unittest.TestCase):
    """Bug 4: pulsar 'Añadir origen' sin proyecto debe avisar, no fallar en
    silencio (antes _pick_source_entry devolvía None sin explicación)."""

    def _call(self):
        return _Harness()._pick_source_entry()

    @mock.patch.object(sources_mixin, "QMessageBox")
    def test_no_project_shows_info_and_returns_none(self, qmb):
        result = self._call()
        self.assertIsNone(result)
        qmb.information.assert_called_once()

    @mock.patch.object(sources_mixin, "QMessageBox")
    def test_no_project_message_is_translated(self, qmb):
        self._call()
        args = qmb.information.call_args[0]
        self.assertEqual(args[1], "Proyecto requerido")
        self.assertIn("proyecto", args[2])

    @mock.patch.object(sources_mixin, "QMessageBox")
    def test_add_source_entry_does_not_crash_without_project(self, qmb):
        # _add_source_entry llama a _pick_source_entry; sin proyecto informa y
        # no avanza (no lanza excepciones).
        _Harness()._add_source_entry()
        qmb.information.assert_called_once()


if __name__ == "__main__":
    unittest.main()