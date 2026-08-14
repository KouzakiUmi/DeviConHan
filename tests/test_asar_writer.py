import io
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from utils.asar_writer import _extract_node, _path_within, asar_pack


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

            self.assertEqual(created_targets, [os.path.join("..", "target.txt")])

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

    def test_path_containment_fails_closed_when_resolution_fails(self):
        with patch.object(Path, "resolve", side_effect=OSError("unavailable")):
            self.assertFalse(_path_within(Path("target"), Path("root")))

    def test_repack_removes_stale_unpacked_sidecar(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            source = root / "source"
            source.mkdir()
            native = source / "native.node"
            native.write_bytes(b"native")
            archive = root / "app.asar"

            asar_pack(source, archive)
            self.assertTrue((root / "app.asar.unpacked" / "native.node").is_file())

            native.unlink()
            (source / "main.js").write_bytes(b"main")
            asar_pack(source, archive)

            self.assertFalse((root / "app.asar.unpacked").exists())


if __name__ == "__main__":
    unittest.main()
