"""Business regressions exercised with real temporary ASAR and ZIP files."""

import hashlib
import json
import shutil
import tempfile
import zipfile
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

import pytest

from controllers.patch_controller import PatchController, recover_incomplete_patch
from controllers.save_manager_controller import SaveManagerController
from core.bootstrap import bootstrap_system
from core.patch_info import get_patch_hash
from core.patcher import CoreLogic
from core.save_service import SaveService
from gui.tabs.save_tab import SaveTab
from utils.asar_utils import get_file_hash_in_asar, validate_asar_with_sidecar
from utils.asar_writer import asar_pack


@pytest.fixture
def work_dir():
    with tempfile.TemporaryDirectory(prefix="devicon-regression-") as directory:
        yield Path(directory)


@pytest.fixture
def game(work_dir, monkeypatch):
    src = work_dir / "src"
    (src / "tyrano").mkdir(parents=True)
    (src / "tyrano/lang.js").write_bytes(b"original" * 300)
    (src / "padding.dat").write_bytes(b"game data" * 300)
    (src / "addon.node").write_bytes(b"original native module")
    resources = work_dir / "resources"
    resources.mkdir()
    asar = resources / "app.asar"
    asar_pack(src, asar, unpacked_files={"addon.node"})
    cfg = SimpleNamespace(
        target_asar_name="app.asar",
        patch_zip_name="Patch.zip",
        patch_dir_name="Patch",
        temp_patch_dir="temp_patch",
        patch_info_file=".patch_info",
        patch_meta_file=".patch_meta",
        check_files_for_update=["tyrano/lang.js"],
        stable_files_for_validation=[],
        backup_prefix="Backup_",
        auto_detect_game=False,
        game_path="",
        validate_config=lambda: (True, [], []),
    )
    for module in (
        "controllers.patch_controller",
        "controllers.save_manager_controller",
        "core.state_validator",
        "core.steam",
        "core.patch_info",
        "core.bootstrap",
    ):
        if module != "controllers.save_manager_controller":
            monkeypatch.setattr(module + ".get_config", lambda: cfg)
    monkeypatch.setattr("controllers.patch_controller.get_runtime_game_path", lambda: str(work_dir))
    monkeypatch.setattr("core.bootstrap.get_runtime_game_path", lambda: str(work_dir))
    monkeypatch.setattr(
        "controllers.patch_controller.get_resource_path", lambda name: str(work_dir / name)
    )
    controller = PatchController(CoreLogic())
    return SimpleNamespace(base=work_dir, asar=asar, controller=controller)


def package(game, name="Patch.zip", text=b"patch A", extra=True):
    dest = game.base / name
    with zipfile.ZipFile(dest, "w") as zf:
        zf.writestr("tyrano/lang.js", text)
        if extra:
            zf.writestr("data/old-patch-only.txt", b"old patch file")
    return dest


def install(game):
    package(game)
    result = game.controller.run_auto_patch()
    assert result[0], result
    return json.loads((game.base / ".patch_meta").read_text())


def test_install_records_hash_and_identical_package_skips(game):
    meta = install(game)
    assert meta["patch_hash"] == get_patch_hash(game.base / "Patch.zip")
    before = game.asar.read_bytes()
    with patch.object(game.controller.core, "run_asar", wraps=game.controller.core.run_asar) as run:
        assert game.controller.run_auto_patch() == (True, None, "")
        run.assert_not_called()
    assert game.asar.read_bytes() == before


@pytest.mark.parametrize("legacy", [False, True])
def test_changed_or_legacy_patch_rebuilds_from_original_without_old_files(game, legacy):
    meta = install(game)
    if legacy:
        meta.pop("patch_hash")
        (game.base / ".patch_meta").write_text(json.dumps(meta))
    backup = game.asar.with_name("app.asar.bak")
    original = backup.read_bytes()
    custom = package(game, "EnglishPatch.zip", b"patch B", extra=False)
    ask = Mock(return_value=True)
    gui = SimpleNamespace(thread_safe_askyesno=ask)
    result = game.controller.run_auto_patch(gui_app=gui, patch_zip_path=str(custom))
    assert result[0], result
    ask.assert_called_once()
    assert "Steam" in ask.call_args.args[1]
    assert (
        get_file_hash_in_asar(str(game.asar), "tyrano/lang.js")
        == hashlib.sha256(b"patch B").hexdigest()
    )
    assert get_file_hash_in_asar(str(game.asar), "data/old-patch-only.txt") is None
    assert backup.read_bytes() == original
    assert validate_asar_with_sidecar(game.asar)[0]
    assert json.loads((game.base / ".patch_meta").read_text())["patch_hash"] == get_patch_hash(
        custom
    )


@pytest.mark.parametrize("batch", [False, True])
def test_changed_patch_decline_or_batch_preserves_installed_game(game, batch):
    install(game)
    custom = package(game, "other.zip", b"patch B")
    before = game.asar.read_bytes()
    meta = (game.base / ".patch_meta").read_bytes()
    gui = None if batch else SimpleNamespace(thread_safe_askyesno=Mock(return_value=False))
    result = game.controller.run_auto_patch(gui_app=gui, patch_zip_path=str(custom))
    assert not result[0]
    assert game.asar.read_bytes() == before
    assert (game.base / ".patch_meta").read_bytes() == meta
    if batch:
        assert "Steam" in result[2]


def test_changed_patch_rejects_backup_with_missing_external_file(game):
    install(game)
    custom = package(game, "other.zip", b"patch B")
    (game.base / "resources/app.asar.bak.unpacked/addon.node").unlink()
    before = game.asar.read_bytes()
    ask = Mock(return_value=True)
    result = game.controller.run_auto_patch(
        gui_app=SimpleNamespace(thread_safe_askyesno=ask), patch_zip_path=str(custom)
    )
    assert not result[0] and "Steam" in result[2]
    ask.assert_not_called()
    assert game.asar.read_bytes() == before


def test_patch_source_change_during_extraction_does_not_commit(game):
    source = package(game)
    before = game.asar.read_bytes()
    run = game.controller.core.run_asar

    def change_source(action, *args, **kwargs):
        result = run(action, *args, **kwargs)
        if action == "extract":
            package(game, text=b"replaced while extracting")
        return result

    with patch.object(game.controller.core, "run_asar", side_effect=change_source):
        result = game.controller.run_auto_patch(patch_zip_path=str(source))
    assert not result[0]
    assert game.asar.read_bytes() == before
    assert not (game.base / ".patch_meta").exists()


def test_metadata_write_failure_does_not_claim_installed_hash(game):
    package(game)
    before = game.asar.read_bytes()
    with patch("controllers.patch_controller.save_patch_meta", side_effect=OSError("disk full")):
        result = game.controller.run_auto_patch()
    assert not result[0]
    assert game.asar.read_bytes() == before
    assert not (game.base / ".patch_meta").exists()
    assert validate_asar_with_sidecar(game.asar)[0]


def test_manual_restore_retry_preserves_already_restored_sidecar(game):
    install(game)
    with patch(
        "controllers.patch_controller._remove_patch_metadata", side_effect=PermissionError("busy")
    ):
        assert not game.controller.restore_patch()[0]
    native = game.base / "resources/app.asar.unpacked/addon.node"
    before = native.read_bytes()
    assert (game.base / ".patch_transaction.json").exists()
    assert "Completed cleanup" in recover_incomplete_patch(str(game.base))
    assert native.read_bytes() == before
    assert validate_asar_with_sidecar(game.asar)[0]
    assert recover_incomplete_patch(str(game.base)) is None


def test_incomplete_restore_missing_sidecar_retains_marker_and_guides_steam(game):
    native = game.base / "resources/app.asar.unpacked/addon.node"
    native.unlink()
    marker = game.base / ".patch_transaction.json"
    marker.write_text('{"phase":"restoring"}')
    before = game.asar.read_bytes()
    assert "Steam" in recover_incomplete_patch(str(game.base))
    assert marker.exists()
    assert game.asar.read_bytes() == before


def test_corrupt_game_can_open_recovery_ui_but_cannot_install(game):
    install(game)
    game.asar.write_bytes(b"broken")
    ok, messages = bootstrap_system(str(game.base), skip_disk_check=True, allow_recovery=True)
    assert ok and any("Steam" in m for m in messages)
    result = game.controller.run_auto_patch()
    assert not result[0] and "Steam" in result[2]
    assert game.asar.read_bytes() == b"broken"
    assert game.controller.restore_patch()[0]
    assert validate_asar_with_sidecar(game.asar)[0]


def test_steam_verified_original_can_install_new_patch(game):
    install(game)
    shutil.copy2(game.asar.with_name("app.asar.bak"), game.asar)
    custom = package(game, "new.zip", b"new patch")
    result = game.controller.run_auto_patch(patch_zip_path=str(custom))
    assert result[0], result
    assert (
        get_file_hash_in_asar(str(game.asar), "tyrano/lang.js")
        == hashlib.sha256(b"new patch").hexdigest()
    )


def test_directory_patch_hash_detects_file_content_and_path_changes(work_dir):
    (work_dir / "a.txt").write_bytes(b"A")
    first = get_patch_hash(work_dir)
    (work_dir / "a.txt").write_bytes(b"B")
    assert get_patch_hash(work_dir) != first
    second = get_patch_hash(work_dir)
    (work_dir / "a.txt").rename(work_dir / "b.txt")
    assert get_patch_hash(work_dir) != second


def save_tab(game):
    backups = game.base / "backups"
    backups.mkdir()
    backup = backups / "Backup_20260905000000000"
    backup.mkdir()
    (backup / "slot.sav").write_bytes(b"saved progress")
    tab = SaveTab.__new__(SaveTab)
    controller = SaveManagerController(SaveService(CoreLogic()))
    tab.app = SimpleNamespace(
        save_controller=controller, var_save_path=Mock(), current_save_dir=None
    )
    tab.tree = Mock()
    tab.tree.get_children.return_value = []
    tab.backup_paths = {}
    tab._additional_backup_dirs = set()
    tab.get_backup_dir = lambda: str(backups)
    tab.after = Mock()
    return tab, backup


def test_missing_save_directory_still_lists_independent_backups(game):
    tab, backup = save_tab(game)
    tab.scan_saves()
    assert tab.app.current_save_dir is None
    assert str(backup) in tab.backup_paths.values()


def test_missing_save_directory_asks_for_target_before_restoring(game):
    tab, backup = save_tab(game)
    tab.tree.selection.return_value = ["selected"]
    tab.backup_paths = {"selected": str(backup)}
    target = game.base / "_storage"
    tab._submit_async_operation = Mock()
    with patch("gui.tabs.save_tab.filedialog.askdirectory", return_value=str(target)), patch(
        "gui.tabs.save_tab.messagebox.askyesno", return_value=True
    ) as confirm:
        tab.do_restore_save()
    assert str(target) in confirm.call_args.args[1]
    worker = tab._submit_async_operation.call_args.args[2]
    tab.app.ui_log = Mock()
    worker()
    assert (target / "slot.sav").read_bytes() == b"saved progress"


def test_missing_save_rejects_game_root_as_restore_target(game):
    tab, backup = save_tab(game)
    tab.tree.selection.return_value = ["selected"]
    tab.backup_paths = {"selected": str(backup)}
    tab._submit_async_operation = Mock()
    with patch("gui.tabs.save_tab.filedialog.askdirectory", return_value=str(game.base)), patch(
        "gui.tabs.save_tab.messagebox.showerror"
    ) as error:
        tab.do_restore_save()
    error.assert_called_once()
    tab._submit_async_operation.assert_not_called()


def test_failed_replacement_before_commit_preserves_previous_patch(game):
    install(game)
    custom = package(game, "new.zip", b"patch B", extra=False)
    before = game.asar.read_bytes()
    metadata = (game.base / ".patch_meta").read_bytes()
    run = game.controller.core.run_asar

    def fail_pack(action, *args, **kwargs):
        if action == "pack":
            raise OSError("packing failed")
        return run(action, *args, **kwargs)

    with patch.object(game.controller.core, "run_asar", side_effect=fail_pack):
        result = game.controller.run_auto_patch(
            gui_app=SimpleNamespace(thread_safe_askyesno=Mock(return_value=True)),
            patch_zip_path=str(custom),
        )
    assert not result[0]
    assert game.asar.read_bytes() == before
    assert (game.base / ".patch_meta").read_bytes() == metadata
    assert validate_asar_with_sidecar(game.asar)[0]


def test_manual_restore_rejects_truncated_backup_sidecar_without_changes(game):
    install(game)
    native = game.base / "resources/app.asar.bak.unpacked/addon.node"
    native.write_bytes(b"short")
    before = game.asar.read_bytes()
    result = game.controller.restore_patch()
    assert not result[0] and "Steam" in result[1]
    assert game.asar.read_bytes() == before
    assert game.asar.with_name("app.asar.bak").exists()


def test_early_gui_error_does_not_restore_over_healthy_game(game):
    install(game)
    before = game.asar.read_bytes()
    backup = game.asar.with_name("app.asar.bak")
    game.controller.handle_error(
        str(game.base), str(game.asar), str(backup), OSError("ZIP unreadable")
    )
    assert game.asar.read_bytes() == before
    assert backup.exists()
