import io
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from utils.asar_writer import _extract_node


class TestAsarWriter(unittest.TestCase):
    def test_extract_symlink_uses_root_relative_target(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            current_dest = root / "nested"
            current_dest.mkdir()
            node = {"files": {"alias.txt": {"link": "target.txt"}}}
            created_targets = []

            def capture_target(self, target):
                created_targets.append(target)

            with patch.object(Path, "symlink_to", new=capture_target):
                _extract_node(
                    node,
                    current_dest,
                    root,
                    io.BytesIO(),
                    0,
                    root / "app.asar.unpacked",
                    None,
                    None,
                    set(),
                )

            self.assertEqual(created_targets, [root / "target.txt"])

    def test_extract_skips_symlink_failure_on_windows(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            node = {"files": {"alias.txt": {"link": "target.txt"}}}

            with patch("utils.asar_writer.os.name", "nt"):
                with patch.object(Path, "symlink_to", side_effect=OSError("privilege missing")):
                    _extract_node(
                        node,
                        root,
                        root,
                        io.BytesIO(),
                        0,
                        root / "app.asar.unpacked",
                        None,
                        None,
                        set(),
                    )

            self.assertFalse((root / "alias.txt").exists())


if __name__ == "__main__":
    unittest.main()
