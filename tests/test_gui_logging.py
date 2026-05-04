import queue
import unittest
from unittest.mock import Mock, patch

from gui.main_window import App


class TestGuiLogging(unittest.TestCase):
    def _make_app_stub(self):
        app = App.__new__(App)
        app._ui_queue = queue.Queue()
        app.after = lambda *a, **kw: None
        return app

    def test_ui_log_does_not_emit_standard_log_records(self):
        app = self._make_app_stub()

        with patch("gui.main_window.logger") as mock_logger:
            app.ui_log("message")

        self.assertEqual(app._ui_queue.qsize(), 1)
        mock_logger.info.assert_not_called()
        mock_logger.warning.assert_not_called()
        mock_logger.error.assert_not_called()
        mock_logger.debug.assert_not_called()

    def test_log_emits_standard_log_records_and_updates_ui(self):
        app = self._make_app_stub()

        with patch("gui.main_window.logger") as mock_logger:
            app.log("message")

        self.assertEqual(app._ui_queue.qsize(), 1)
        mock_logger.info.assert_called_once_with("message")


    def test_process_ui_queue_catches_task_exceptions(self):
        app = self._make_app_stub()
        bad_task = Mock(side_effect=ValueError("boom"))
        app._ui_queue.put(bad_task)

        with patch("gui.main_window.logger") as mock_logger:
            app._process_ui_queue()

        bad_task.assert_called_once()
        mock_logger.debug.assert_called_once()
        call_args = mock_logger.debug.call_args
        self.assertIn("UI queue task failed", call_args[0][0])

    def test_process_ui_queue_handles_empty_queue_gracefully(self):
        app = self._make_app_stub()

        with patch("gui.main_window.logger") as mock_logger:
            app._process_ui_queue()

        mock_logger.debug.assert_not_called()


if __name__ == "__main__":
    unittest.main()
