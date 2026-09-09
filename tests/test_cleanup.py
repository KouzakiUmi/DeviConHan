import os
import tempfile
import unittest

from core.patcher import CoreLogic
from utils.cleanup import force_cleanup_dir


@unittest.skipUnless(os.name == "posix", "POSIX directory permissions are required")
class TestCleanup(unittest.TestCase):
    def test_force_cleanup_removes_nested_directory_on_posix(self):
        with tempfile.TemporaryDirectory() as parent:
            temp_dir = os.path.join(parent, "temp_patch")
            nested = os.path.join(temp_dir, "nested")
            os.makedirs(nested)
            with open(os.path.join(nested, "payload"), "w", encoding="utf-8") as stream:
                stream.write("payload")

            self.assertTrue(force_cleanup_dir(temp_dir, max_retries=1))
            self.assertFalse(os.path.exists(temp_dir))

    def test_force_cleanup_recovers_directory_without_execute_permission(self):
        with tempfile.TemporaryDirectory() as parent:
            temp_dir = os.path.join(parent, "temp_patch")
            nested = os.path.join(temp_dir, "nested")
            os.makedirs(nested)
            with open(os.path.join(nested, "payload"), "w", encoding="utf-8") as stream:
                stream.write("payload")

            # This is the residue produced by the previous implementation.
            os.chmod(nested, 0o600)

            self.assertTrue(force_cleanup_dir(temp_dir, max_retries=1))
            self.assertFalse(os.path.exists(temp_dir))

    def test_force_cleanup_removes_symlink_without_following_target(self):
        with tempfile.TemporaryDirectory() as parent, tempfile.TemporaryDirectory() as outside:
            temp_dir = os.path.join(parent, "temp_patch")
            os.symlink(outside, temp_dir)

            self.assertTrue(force_cleanup_dir(temp_dir, max_retries=1))
            self.assertFalse(os.path.lexists(temp_dir))
            self.assertTrue(os.path.isdir(outside))

    def test_readonly_handler_keeps_directory_traversable(self):
        with tempfile.TemporaryDirectory() as parent:
            target = os.path.join(parent, "readonly")
            os.mkdir(target)
            os.chmod(target, 0o500)

            CoreLogic.remove_readonly_handler(os.rmdir, target, None)

            self.assertFalse(os.path.exists(target))


if __name__ == "__main__":
    unittest.main()
