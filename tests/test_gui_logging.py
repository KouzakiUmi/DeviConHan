import queue
import unittest
from unittest.mock import patch

from gui.main_window import App


class TestGuiLogging(unittest.TestCase):
    def _make_app_stub(self):
        app = App.__new__(App)
        app._ui_queue = queue.Queue()
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


if __name__ == "__main__":
    unittest.main()
