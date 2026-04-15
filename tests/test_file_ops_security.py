import stat
import tempfile
import unittest
import zipfile
from pathlib import Path

from utils.file_ops import safe_extract_zip


class TestFileOpsSecurity(unittest.TestCase):
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
