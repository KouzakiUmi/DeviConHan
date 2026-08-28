import stat
import tempfile
import unittest
import zipfile
from pathlib import Path

from utils.file_ops import detect_patch_zip_root, safe_extract_zip


class TestFileOpsSecurity(unittest.TestCase):
    def test_detects_and_strips_patch_zip_wrapper_directory(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            zip_path = root / "Patch.zip"
            dest = root / "out"
            with zipfile.ZipFile(zip_path, "w") as zf:
                zf.writestr("Patch/data/scenario/chapter.ks", "translated")
                zf.writestr("Patch/tyrano/lang.js", "translated")

            prefix = detect_patch_zip_root(str(zip_path), ["tyrano/lang.js"])
            self.assertEqual(prefix, "Patch")
            self.assertTrue(safe_extract_zip(str(zip_path), str(dest), strip_prefix=prefix))
            self.assertEqual(
                (dest / "data" / "scenario" / "chapter.ks").read_text(encoding="utf-8"),
                "translated",
            )
            self.assertFalse((dest / "Patch").exists())

    def test_detects_nested_wrapper_from_asar_root_directories(self):
        with tempfile.TemporaryDirectory() as td:
            zip_path = Path(td) / "Patch.zip"
            with zipfile.ZipFile(zip_path, "w") as zf:
                zf.writestr("release/Patch/data/scenario/chapter.ks", "translated")
                zf.writestr("release/Patch/data/image/button.png", "image")

            self.assertEqual(detect_patch_zip_root(str(zip_path)), "release/Patch")

    def test_keeps_already_rooted_patch_zip_unchanged(self):
        with tempfile.TemporaryDirectory() as td:
            zip_path = Path(td) / "Patch.zip"
            with zipfile.ZipFile(zip_path, "w") as zf:
                zf.writestr("data/scenario/chapter.ks", "translated")
                zf.writestr("tyrano/lang.js", "translated")

            self.assertEqual(detect_patch_zip_root(str(zip_path)), "")

    def test_rejects_ambiguous_patch_zip_roots(self):
        with tempfile.TemporaryDirectory() as td:
            zip_path = Path(td) / "Patch.zip"
            with zipfile.ZipFile(zip_path, "w") as zf:
                zf.writestr("first/data/others/font.ttf", "one")
                zf.writestr("second/data/others/font.ttf", "two")

            with self.assertRaisesRegex(ValueError, "multiple patch payload roots"):
                detect_patch_zip_root(str(zip_path), ["data/others/font.ttf"])

    def test_prefix_filter_does_not_hide_unsafe_zip_members(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            zip_path = root / "Patch.zip"
            with zipfile.ZipFile(zip_path, "w") as zf:
                zf.writestr("Patch/data/scenario/chapter.ks", "translated")
                zf.writestr("../outside.txt", "unsafe")

            with self.assertRaisesRegex(ValueError, "Path traversal detected"):
                safe_extract_zip(str(zip_path), str(root / "out"), strip_prefix="Patch")

    def test_rejects_zip_symlink_entries(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            zip_path = root / "symlink.zip"
            dest = root / "out"

            info = zipfile.ZipInfo("bad-link")
            info.create_system = 3
            info.external_attr = (stat.S_IFLNK | 0o777) << 16

            with zipfile.ZipFile(zip_path, "w") as zf:
                zf.writestr(info, "../outside.txt")

            with self.assertRaisesRegex(ValueError, "Symlink not allowed"):
                safe_extract_zip(str(zip_path), str(dest))


if __name__ == "__main__":
    unittest.main()
