import hashlib
import json
import shutil
import tempfile
import unittest
from pathlib import Path

from core.state_validator import StateValidator, SystemState
from utils.asar_writer import asar_pack


class TestStateValidator(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.base_dir = Path(self.temp_dir.name)
        self.resources_dir = self.base_dir / "resources"
        self.resources_dir.mkdir()
        self.src_dir = self.base_dir / "src"
        self.src_dir.mkdir()

        self.patch_files = {
            "package.json": b'{"name":"validator-test","version":"1.0.0"}\n' * 12,
            "tyrano/lang.js": b'console.log("lang");\n' * 40,
            "tyrano/data.ks": b"*start\nHello\n" * 50,
            "assets/ui.txt": b"ui-data\n" * 80,
        }

        for rel_path, content in self.patch_files.items():
            file_path = self.src_dir / rel_path
            file_path.parent.mkdir(parents=True, exist_ok=True)
            file_path.write_bytes(content)

        self.asar_path = self.resources_dir / "app.asar"
        asar_pack(self.src_dir, self.asar_path)
        shutil.copy2(self.asar_path, self.resources_dir / "app.asar.bak")

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_partial_patch_detected_when_later_patch_file_hash_mismatches(self):
        expected_hashes = {
            path: hashlib.sha256(content).hexdigest()
            for path, content in self.patch_files.items()
        }
        expected_hashes["assets/ui.txt"] = "0" * 64

        patch_meta = {
            "patch_files": expected_hashes,
        }
        (self.base_dir / ".patch_meta").write_text(
            json.dumps(patch_meta, ensure_ascii=False),
            encoding="utf-8",
        )

        validator = StateValidator(str(self.base_dir))
        state, _issues = validator.validate_all()

        self.assertEqual(state, SystemState.PARTIAL_PATCH)


if __name__ == "__main__":
    unittest.main()
