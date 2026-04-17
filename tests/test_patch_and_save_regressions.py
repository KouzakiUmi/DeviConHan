import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

from controllers.patch_controller import PatchController
from core.save_service import SaveService
from gui.tabs.save_tab import SaveTab
from utils.error_handler import PatcherError


class _CoreStub:
    @staticmethod
    def remove_readonly_handler(func, path, excinfo):
        func(path)


class _VarStub:
    def __init__(self, value):
        self.value = value

    def get(self):
        return self.value

    def set(self, value):
        self.value = value


class TestPatchAndSaveRegressions(unittest.TestCase):
    def test_run_auto_patch_fails_when_patch_zip_extraction_returns_false(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            base = Path(temp_dir)
            resources = base / "resources"
            resources.mkdir()
            asar_path = resources / "app.asar"
            asar_path.write_bytes(b"asar-data")
            patch_zip = base / "Patch.zip"
            patch_zip.write_bytes(b"zip-data")
            temp_patch_dir = base / "temp_patch"

            controller = PatchController(_CoreStub())
            mock_core = Mock()

            def run_asar_side_effect(action, src, dest, callback=None, unpacked_files=None):
                if action == "extract":
                    Path(dest).mkdir(parents=True, exist_ok=True)
                    (Path(dest) / "package.json").write_text("{}", encoding="utf-8")
                    return True, set()
                raise AssertionError("pack should not be called when patch extraction fails")

            mock_core.run_asar.side_effect = run_asar_side_effect
            controller.core = mock_core

            config_stub = SimpleNamespace(target_asar_name="app.asar", temp_patch_dir="temp_patch")
            platform_info = SimpleNamespace(system="Windows")

            with (
                patch.object(controller, "check_prerequisites", return_value=(True, "")),
                patch("controllers.patch_controller.get_runtime_game_path", return_value=str(base)),
                patch("controllers.patch_controller.get_config", return_value=config_stub),
                patch("controllers.patch_controller.get_platform_info", return_value=platform_info),
                patch("controllers.patch_controller.get_resources_path", return_value=str(resources)),
                patch("controllers.patch_controller.StateValidator") as mock_validator_cls,
                patch("controllers.patch_controller.handle_steam_update", return_value=(True, False)),
                patch.object(controller, "_check_disk_space", return_value=(True, "disk ok")),
                patch("controllers.patch_controller.safe_path_within", return_value=str(temp_patch_dir)),
                patch("controllers.patch_controller.get_resource_path") as mock_resource_path,
                patch("controllers.patch_controller.safe_extract_zip", return_value=False),
            ):
                mock_validator = mock_validator_cls.return_value
                mock_validator.validate_all.return_value = (SimpleNamespace(value="clean"), [])
                mock_resource_path.side_effect = (
                    lambda relative: str(patch_zip)
                    if relative == "Patch.zip"
                    else str(base / relative)
                )

                success, _temp, error_msg = controller._do_run_auto_patch(None, None)

            self.assertFalse(success)
            self.assertIn("Failed to extract patch data", error_msg)

    def test_restore_save_preserves_existing_data_when_zip_extraction_fails(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            save_dir = root / "save"
            save_dir.mkdir()
            original_file = save_dir / "slot1.sav"
            original_file.write_text("original-save", encoding="utf-8")

            backup_zip = root / "backup.zip"
            backup_zip.write_bytes(b"bad-zip")

            service = SaveService(_CoreStub())

            with patch("core.save_service.safe_extract_zip", return_value=False):
                with self.assertRaises(PatcherError):
                    service.restore_save(str(save_dir), str(backup_zip))

            self.assertTrue(original_file.exists())
            self.assertEqual(original_file.read_text(encoding="utf-8"), "original-save")

    def test_change_backup_dir_switches_location_without_migrating_when_declined(self):
        old_dir = r"D:\old-backups"
        new_dir = r"D:\new-backups"

        tab = SaveTab.__new__(SaveTab)
        tab.app = SimpleNamespace(
            var_backup_dir=_VarStub(old_dir),
            save_config=Mock(return_value=True),
            log=Mock(),
        )
        tab._additional_backup_dirs = set()
        tab.get_backup_dir = lambda: old_dir
        tab.scan_saves = Mock()

        with (
            patch("gui.tabs.save_tab.filedialog.askdirectory", return_value=new_dir),
            patch("gui.tabs.save_tab.messagebox.askyesno", return_value=False),
        ):
            tab.change_backup_dir()

        self.assertEqual(tab.app.var_backup_dir.get(), new_dir)
        self.assertEqual(tab._additional_backup_dirs, {old_dir})
        tab.app.save_config.assert_called_once()
        tab.scan_saves.assert_called_once()


if __name__ == "__main__":
    unittest.main()
