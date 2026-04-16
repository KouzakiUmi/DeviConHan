import io
import logging
import tempfile
import unittest

from utils.logging import retarget_console_streams


class TestLoggingStreams(unittest.TestCase):
    def test_retarget_console_streams_updates_stream_handlers_only(self):
        root_logger = logging.getLogger()
        old_handlers = root_logger.handlers[:]
        old_level = root_logger.level

        old_stdout = io.StringIO()
        old_stderr = io.StringIO()
        new_stdout = io.StringIO()
        new_stderr = io.StringIO()

        console_handler = logging.StreamHandler(old_stdout)
        error_handler = logging.StreamHandler(old_stderr)

        with tempfile.TemporaryDirectory() as temp_dir:
            file_handler = logging.FileHandler(f"{temp_dir}/test.log")
            try:
                root_logger.handlers = [console_handler, error_handler, file_handler]
                root_logger.setLevel(logging.DEBUG)

                rebound = retarget_console_streams(
                    new_stdout,
                    new_stderr,
                    old_stdout=old_stdout,
                    old_stderr=old_stderr,
                )

                self.assertEqual(rebound, 2)
                self.assertIs(console_handler.stream, new_stdout)
                self.assertIs(error_handler.stream, new_stderr)
                self.assertIsNot(file_handler.stream, new_stdout)
                self.assertIsNot(file_handler.stream, new_stderr)
            finally:
                file_handler.close()
                root_logger.handlers = old_handlers
                root_logger.setLevel(old_level)


if __name__ == "__main__":
    unittest.main()
