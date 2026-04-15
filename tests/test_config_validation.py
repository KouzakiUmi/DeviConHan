import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from core.config import AppConfig


class TestConfigValidation(unittest.TestCase):
    def test_validate_config_resolves_relative_resource_dir_from_app_root(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "resources").mkdir()
            config_path = root / "config.ini"
            config_path.write_text(
                "[main]\nRESOURCE_DIR = resources\nAPP_NAME = TestApp\n\n[files]\nCHECK_FILES_FOR_UPDATE = package.json\n",
                encoding="utf-8",
            )

            config = AppConfig(str(config_path))
            with patch("core.config.get_resource_path", return_value=str(root / "resources")):
                valid, errors, warnings = config.validate_config()

            self.assertTrue(valid)
            self.assertEqual(errors, [])
            self.assertEqual(warnings, [])


if __name__ == "__main__":
    unittest.main()
