import os
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

from controllers.patch_controller import PatchController, recover_incomplete_patch
from controllers.save_manager_controller import SaveManagerController
from core.save_service import SaveService
from gui.tabs.save_tab import SaveTab
from utils.operation_lock import FileOperationLock


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
    def test_file_operation_lock_excludes_a_second_process_handle(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            target = str(Path(temp_dir) / "app.asar")
            first = FileOperationLock(target)
            second = FileOperationLock(target)
            third = FileOperationLock(target)
            try:
                self.assertTrue(first.acquire())
                self.assertFalse(second.acquire())
                self.assertFalse(third.acquire())
                first.release()
                self.assertTrue(second.acquire())
            finally:
                first.release()
                second.release()
                third.release()

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

            with patch.object(controller, "check_prerequisites", return_value=(True, "")), patch(
                "controllers.patch_controller.get_runtime_game_path", return_value=str(base)
            ), patch("controllers.patch_controller.get_config", return_value=config_stub), patch(
                "controllers.patch_controller.get_platform_info", return_value=platform_info
            ), patch(
                "controllers.patch_controller.get_resources_path", return_value=str(resources)
            ), patch("controllers.patch_controller.StateValidator") as mock_validator_cls, patch(
                "controllers.patch_controller.handle_steam_update", return_value=(True, False)
            ), patch.object(controller, "_check_disk_space", return_value=(True, "disk ok")), patch(
                "controllers.patch_controller.safe_path_within",
                return_value=str(temp_patch_dir),
            ), patch("controllers.patch_controller.get_resource_path") as mock_resource_path, patch(
                "controllers.patch_controller.safe_extract_zip", return_value=False
            ):
                mock_validator = mock_validator_cls.return_value
                mock_validator.validate_all.return_value = (SimpleNamespace(value="clean"), [])
                mock_resource_path.side_effect = lambda relative: (
                    str(patch_zip) if relative == "Patch.zip" else str(base / relative)
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
                result = service.restore_save(str(save_dir), str(backup_zip))

            # Should return warning message instead of raising
            self.assertIsInstance(result, str)
            self.assertIn("Current save was not modified", result)
            self.assertTrue(original_file.exists())
            self.assertEqual(original_file.read_text(encoding="utf-8"), "original-save")

    def test_restore_save_switches_prepared_directory_without_copying_over_live_save(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            save_dir = root / "save"
            save_dir.mkdir()
            (save_dir / "old.sav").write_text("old", encoding="utf-8")

            backup_dir = root / "backup"
            backup_dir.mkdir()
            (backup_dir / "new.sav").write_text("new", encoding="utf-8")

            result = SaveService(_CoreStub()).restore_save(str(save_dir), str(backup_dir))

            self.assertIsNone(result)
            self.assertFalse((save_dir / "old.sav").exists())
            self.assertEqual((save_dir / "new.sav").read_text(encoding="utf-8"), "new")
            self.assertFalse((root / "save.restore-journal").exists())

    def test_restore_save_retries_rollback_when_immediate_switch_rollback_fails(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            save_dir = root / "save"
            save_dir.mkdir()
            (save_dir / "old.sav").write_text("old", encoding="utf-8")
            backup_dir = root / "backup"
            backup_dir.mkdir()
            (backup_dir / "new.sav").write_text("new", encoding="utf-8")
            real_replace = os.replace
            old_restore_attempts = 0

            def flaky_replace(src, dst):
                nonlocal old_restore_attempts
                source = Path(src)
                destination = Path(dst)
                if source.name == "to_restore" and destination == save_dir:
                    raise OSError("new save switch failed")
                if source.name == "to_restore.old" and destination == save_dir:
                    old_restore_attempts += 1
                    if old_restore_attempts == 1:
                        raise OSError("immediate rollback failed")
                return real_replace(src, dst)

            with patch("core.save_service.os.replace", side_effect=flaky_replace):
                result = SaveService(_CoreStub()).restore_save(str(save_dir), str(backup_dir))

            self.assertIsInstance(result, str)
            self.assertIn("Current save has been restored from backup", result)
            self.assertEqual((save_dir / "old.sav").read_text(encoding="utf-8"), "old")
            self.assertFalse((root / "save.restore-journal").exists())

    def test_patch_recovery_defers_while_another_process_holds_lock(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            base = Path(temp_dir)
            resources = base / "resources"
            resources.mkdir()
            marker = base / ".patch_transaction.json"
            marker.write_text('{"phase":"packing"}', encoding="utf-8")
            staged = resources / "app.asar.new"
            staged.write_bytes(b"in-progress")
            config_stub = SimpleNamespace(target_asar_name="app.asar")
            platform_info = SimpleNamespace(system="Windows")

            with patch("controllers.patch_controller.get_config", return_value=config_stub), patch(
                "controllers.patch_controller.get_platform_info",
                return_value=platform_info,
            ), patch(
                "controllers.patch_controller.get_resources_path",
                return_value=str(resources),
            ), patch("controllers.patch_controller.FileOperationLock") as lock_cls:
                lock_cls.return_value.acquire.return_value = False
                message = recover_incomplete_patch(str(base))

            self.assertIn("deferred transaction recovery", message)
            self.assertTrue(marker.exists())
            self.assertTrue(staged.exists())
            lock_cls.return_value.release.assert_not_called()

    def test_patch_recovery_keeps_original_during_packing_phase(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            base = Path(temp_dir)
            resources = base / "resources"
            resources.mkdir()
            marker = base / ".patch_transaction.json"
            marker.write_text('{"phase":"packing"}', encoding="utf-8")
            asar = resources / "app.asar"
            backup = resources / "app.asar.bak"
            staged = resources / "app.asar.new"
            asar.write_bytes(b"current")
            backup.write_bytes(b"older-backup")
            staged.write_bytes(b"partial")
            config_stub = SimpleNamespace(target_asar_name="app.asar")
            platform_info = SimpleNamespace(system="Windows")

            with patch("controllers.patch_controller.get_config", return_value=config_stub), patch(
                "controllers.patch_controller.get_platform_info",
                return_value=platform_info,
            ), patch(
                "controllers.patch_controller.get_resources_path",
                return_value=str(resources),
            ), patch("controllers.patch_controller.FileOperationLock") as lock_cls:
                lock_cls.return_value.acquire.return_value = True
                message = recover_incomplete_patch(str(base))

            self.assertIn("original was unchanged", message)
            self.assertEqual(asar.read_bytes(), b"current")
            self.assertEqual(backup.read_bytes(), b"older-backup")
            self.assertFalse(staged.exists())
            self.assertFalse(marker.exists())
            lock_cls.return_value.release.assert_called_once()

    def test_commit_replaces_existing_unpacked_sidecar(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            asar = root / "app.asar"
            live_sidecar = root / "app.asar.unpacked"
            staged_sidecar = root / "app.asar.new.unpacked"
            live_sidecar.mkdir()
            staged_sidecar.mkdir()
            (live_sidecar / "old.node").write_bytes(b"old")
            (staged_sidecar / "new.node").write_bytes(b"new")

            PatchController._replace_unpacked_sidecar(str(root / "app.asar.new"), str(asar))

            self.assertFalse((live_sidecar / "old.node").exists())
            self.assertEqual((live_sidecar / "new.node").read_bytes(), b"new")
            self.assertFalse(staged_sidecar.exists())

    @unittest.skipUnless(os.name == "nt", "Windows path semantics")
    def test_is_within_or_equal_handles_case_insensitive_paths(self):
        """Test that path comparison is case-insensitive on Windows"""
        service = SaveService(_CoreStub())

        # Test equal paths with different cases
        self.assertTrue(service._is_within_or_equal(r"C:\Game\Save", r"c:\game\save"))
        self.assertTrue(service._is_within_or_equal(r"c:\game\save", r"C:\GAME\SAVE"))

        # Test child within parent with different cases
        self.assertTrue(service._is_within_or_equal(r"C:\Game\Save\Backup", r"c:\game\save"))
        self.assertTrue(service._is_within_or_equal(r"c:\game\save\backup", r"C:\GAME\SAVE"))

        # Test non-child paths
        self.assertFalse(service._is_within_or_equal(r"C:\Game\Other", r"c:\game\save"))
        self.assertFalse(service._is_within_or_equal(r"D:\Game\Save", r"c:\game\save"))

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

        with patch("gui.tabs.save_tab.filedialog.askdirectory", return_value=new_dir), patch(
            "gui.tabs.save_tab.messagebox.askyesno", return_value=False
        ):
            tab.change_backup_dir()

        self.assertEqual(tab.app.var_backup_dir.get(), new_dir)
        self.assertEqual(tab._additional_backup_dirs, {old_dir})
        tab.app.save_config.assert_called_once()
        tab.scan_saves.assert_called_once()

    def test_migrate_backups_returns_error_tuple_distinct_from_empty(self):
        svc = SaveService(Mock())
        ctrl = SaveManagerController(svc)
        ctrl.set_log_callback(lambda msg: None)

        with patch.object(svc, "migrate_backups", side_effect=RuntimeError("disk full")):
            migrated, failed = ctrl.migrate_backups("old", "new")

        self.assertEqual(migrated, -1)
        self.assertEqual(failed, -1)
        self.assertNotEqual((migrated, failed), (0, 0))

    def test_migrate_backups_returns_normal_result(self):
        svc = SaveService(Mock())
        ctrl = SaveManagerController(svc)
        ctrl.set_log_callback(lambda msg: None)

        with patch.object(svc, "migrate_backups", return_value=(3, 1)):
            migrated, failed = ctrl.migrate_backups("old", "new")

        self.assertEqual(migrated, 3)
        self.assertEqual(failed, 1)


if __name__ == "__main__":
    unittest.main()
