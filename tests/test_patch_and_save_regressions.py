import os
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

from controllers.patch_controller import PatchController, recover_incomplete_patch
from controllers.save_manager_controller import SaveManagerController
from core.save_service import SaveService
from gui.tabs.patch_tab import PatchTab
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
    def test_custom_patch_zip_takes_priority_over_bundled_patch(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            base = Path(temp_dir)
            resources = base / "resources"
            resources.mkdir()
            custom_patch = base / "my-custom-patch.zip"
            custom_patch.write_bytes(b"zip-placeholder")
            config_stub = SimpleNamespace(
                target_asar_name="app.asar",
                patch_zip_name="Patch.zip",
                patch_dir_name="Patch",
                check_files_for_update=["data/expected.txt"],
            )
            controller = PatchController(Mock())

            with patch(
                "controllers.patch_controller.get_runtime_game_path", return_value=str(base)
            ), patch("controllers.patch_controller.get_config", return_value=config_stub), patch(
                "controllers.patch_controller.get_platform_info",
                return_value=SimpleNamespace(system="Windows"),
            ), patch(
                "controllers.patch_controller.get_resources_path", return_value=str(resources)
            ), patch(
                "controllers.patch_controller.get_resource_path",
                side_effect=lambda name: str(base / name),
            ), patch(
                "controllers.patch_controller.detect_patch_zip_root",
                side_effect=ValueError("custom layout checked"),
            ) as detect_root:
                success, temp, error = controller._do_run_auto_patch(None, None, str(custom_patch))

            self.assertFalse(success)
            self.assertIsNone(temp)
            self.assertIn("custom layout checked", error)
            detect_root.assert_called_once_with(
                str(custom_patch.resolve()), config_stub.check_files_for_update
            )

    def test_missing_custom_patch_does_not_fall_back_to_bundled_patch(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            base = Path(temp_dir)
            resources = base / "resources"
            resources.mkdir()
            bundled_patch = base / "Patch.zip"
            bundled_patch.write_bytes(b"bundled")
            missing_patch = base / "missing.zip"
            config_stub = SimpleNamespace(
                target_asar_name="app.asar",
                patch_zip_name="Patch.zip",
                patch_dir_name="Patch",
            )
            controller = PatchController(Mock())

            with patch(
                "controllers.patch_controller.get_runtime_game_path", return_value=str(base)
            ), patch("controllers.patch_controller.get_config", return_value=config_stub), patch(
                "controllers.patch_controller.get_platform_info",
                return_value=SimpleNamespace(system="Windows"),
            ), patch(
                "controllers.patch_controller.get_resources_path", return_value=str(resources)
            ), patch(
                "controllers.patch_controller.get_resource_path",
                side_effect=lambda name: str(base / name),
            ), patch("controllers.patch_controller.detect_patch_zip_root") as detect_root:
                success, temp, error = controller._do_run_auto_patch(None, None, str(missing_patch))

            self.assertFalse(success)
            self.assertIsNone(temp)
            self.assertIn("missing.zip", error)
            detect_root.assert_not_called()

    def test_patch_tab_selects_resets_and_submits_custom_patch(self):
        tab = PatchTab.__new__(PatchTab)
        tab.default_patch_zip = os.path.abspath("Patch.zip")
        tab.var_patch_zip = _VarStub(tab.default_patch_zip)
        custom_patch = os.path.abspath("custom.zip")

        with patch("gui.tabs.patch_tab.filedialog.askopenfilename", return_value=custom_patch):
            tab.select_patch_zip()
        self.assertEqual(tab.var_patch_zip.get(), custom_patch)

        tab.use_default_patch()
        self.assertEqual(tab.var_patch_zip.get(), tab.default_patch_zip)

        tab._pending_patch_zip = custom_patch
        tab.after = lambda _delay, callback: callback()
        tab.app = SimpleNamespace(
            performance_monitor=Mock(),
            patch_controller=Mock(),
            _finish_operation=Mock(),
        )
        tab.app.patch_controller.run_auto_patch.return_value = (True, None, "")
        cancellation_check = Mock()

        tab._run_auto_patch_worker(_check_cancelled=cancellation_check)

        tab.app.patch_controller.run_auto_patch.assert_called_once_with(
            gui_app=tab.app,
            patch_zip_path=custom_patch,
            _check_cancelled=cancellation_check,
        )

    def test_patch_zip_layout_is_rejected_before_asar_extraction(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            base = Path(temp_dir)
            resources = base / "resources"
            resources.mkdir()
            patch_zip = base / "Patch.zip"
            patch_zip.write_bytes(b"zip-placeholder")
            config_stub = SimpleNamespace(
                target_asar_name="app.asar",
                temp_patch_dir="temp_patch",
                check_files_for_update=["data/expected.txt"],
            )
            core = Mock()
            controller = PatchController(core)

            with patch.object(controller, "check_prerequisites", return_value=(True, "")), patch(
                "controllers.patch_controller.get_runtime_game_path", return_value=str(base)
            ), patch("controllers.patch_controller.get_config", return_value=config_stub), patch(
                "controllers.patch_controller.get_platform_info",
                return_value=SimpleNamespace(system="Windows"),
            ), patch(
                "controllers.patch_controller.get_resources_path", return_value=str(resources)
            ), patch(
                "controllers.patch_controller.get_resource_path",
                side_effect=lambda name: str(base / name),
            ), patch(
                "controllers.patch_controller.detect_patch_zip_root",
                side_effect=ValueError("ambiguous payload"),
            ):
                success, temp, error = controller._do_run_auto_patch(None, None)

            self.assertFalse(success)
            self.assertIsNone(temp)
            self.assertIn("ambiguous payload", error)
            core.run_asar.assert_not_called()

    def test_manual_patch_restore_replaces_asar_sidecar_and_metadata(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            base = Path(temp_dir)
            resources = base / "resources"
            resources.mkdir()
            asar = resources / "app.asar"
            backup = resources / "app.asar.bak"
            asar.write_bytes(b"patched-asar")
            backup.write_bytes(b"original-asar")

            live_sidecar = resources / "app.asar.unpacked"
            backup_sidecar = resources / "app.asar.bak.unpacked"
            live_sidecar.mkdir()
            backup_sidecar.mkdir()
            (live_sidecar / "patched.node").write_bytes(b"patched")
            (backup_sidecar / "original.node").write_bytes(b"original")

            patch_info = base / ".patch_info"
            patch_meta = base / ".patch_meta"
            patch_info.write_text("{}", encoding="utf-8")
            patch_meta.write_text("{}", encoding="utf-8")
            config_stub = SimpleNamespace(
                patch_info_file=".patch_info",
                patch_meta_file=".patch_meta",
            )

            controller = PatchController(_CoreStub())
            with patch(
                "controllers.patch_controller.validate_asar_with_reason",
                return_value=(True, ""),
            ), patch("controllers.patch_controller.get_config", return_value=config_stub):
                success, _message = controller._do_restore_patch(str(base), str(asar))

            self.assertTrue(success)
            self.assertEqual(asar.read_bytes(), b"original-asar")
            self.assertFalse(backup.exists())
            self.assertFalse((live_sidecar / "patched.node").exists())
            self.assertEqual((live_sidecar / "original.node").read_bytes(), b"original")
            self.assertFalse(backup_sidecar.exists())
            self.assertFalse(patch_info.exists())
            self.assertFalse(patch_meta.exists())
            self.assertFalse((base / ".patch_transaction.json").exists())

    def test_manual_patch_restore_rejects_invalid_backup_without_changes(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            base = Path(temp_dir)
            resources = base / "resources"
            resources.mkdir()
            asar = resources / "app.asar"
            backup = resources / "app.asar.bak"
            asar.write_bytes(b"patched-asar")
            backup.write_bytes(b"broken-backup")

            controller = PatchController(_CoreStub())
            with patch(
                "controllers.patch_controller.validate_asar_with_reason",
                return_value=(False, "bad header"),
            ):
                success, message = controller._do_restore_patch(str(base), str(asar))

            self.assertFalse(success)
            self.assertIn("bad header", message)
            self.assertEqual(asar.read_bytes(), b"patched-asar")
            self.assertEqual(backup.read_bytes(), b"broken-backup")
            self.assertFalse((base / ".patch_transaction.json").exists())

    def test_recovery_finishes_manual_restore_after_atomic_asar_commit(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            base = Path(temp_dir)
            resources = base / "resources"
            resources.mkdir()
            marker = base / ".patch_transaction.json"
            marker.write_text('{"phase":"restoring"}', encoding="utf-8")
            asar = resources / "app.asar"
            asar.write_bytes(b"original-asar")

            live_sidecar = resources / "app.asar.unpacked"
            backup_sidecar = resources / "app.asar.bak.unpacked"
            live_sidecar.mkdir()
            backup_sidecar.mkdir()
            (live_sidecar / "patched.node").write_bytes(b"patched")
            (backup_sidecar / "original.node").write_bytes(b"original")
            (base / ".patch_info").write_text("{}", encoding="utf-8")
            (base / ".patch_meta").write_text("{}", encoding="utf-8")

            config_stub = SimpleNamespace(
                target_asar_name="app.asar",
                patch_info_file=".patch_info",
                patch_meta_file=".patch_meta",
            )
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

            self.assertIn("Completed cleanup", message)
            self.assertEqual((live_sidecar / "original.node").read_bytes(), b"original")
            self.assertFalse((live_sidecar / "patched.node").exists())
            self.assertFalse((base / ".patch_info").exists())
            self.assertFalse((base / ".patch_meta").exists())
            self.assertFalse(marker.exists())

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
                "controllers.patch_controller.detect_patch_zip_root", return_value=""
            ), patch("controllers.patch_controller.safe_extract_zip", return_value=False):
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
