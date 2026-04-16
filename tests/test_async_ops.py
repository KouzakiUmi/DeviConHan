import threading
import time
import unittest
from concurrent.futures import CancelledError

from utils.async_ops import AsyncOperationManager, OperationState


class TestAsyncOperationManager(unittest.TestCase):
    def test_submit_reuses_existing_future_while_operation_is_cancelling(self):
        manager = AsyncOperationManager(max_workers=1)
        started = threading.Event()
        release = threading.Event()

        def worker(cancel_event=None, _check_cancelled=None):
            started.set()
            while cancel_event is not None and not cancel_event.is_set():
                time.sleep(0.01)
            release.wait(timeout=1.0)
            if _check_cancelled is not None:
                _check_cancelled()

        try:
            first_future = manager.submit("op", worker)
            self.assertTrue(started.wait(timeout=1.0))

            self.assertTrue(manager.cancel("op"))
            progress = manager.get_progress("op")
            self.assertIsNotNone(progress)
            self.assertEqual(progress.state, OperationState.CANCELLING)

            second_future = manager.submit("op", lambda: "unexpected")
            self.assertIs(second_future, first_future)

            release.set()
            with self.assertRaises(CancelledError):
                first_future.result(timeout=1.0)
        finally:
            release.set()
            manager.shutdown(wait=True)


if __name__ == "__main__":
    unittest.main()
