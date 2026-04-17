"""
Steam 更新检测和处理模块

提供 Steam 更新检测、文件状态检查和补丁状态验证功能。
"""

import json
import logging
import os
from typing import Callable, Optional, Tuple

from core.config import get_config
from utils.asar_utils import get_file_hashes_in_asar, validate_asar_with_reason
from utils.constants import MIN_ASAR_SIZE
from utils.language import T
from utils.performance import get_performance_monitor

logger = logging.getLogger(__name__)


def _remove_backup_safely(bak_path: str, log_error: bool = True) -> bool:
    """安全删除备份文件，返回是否成功"""
    try:
        if os.path.exists(bak_path):
            os.remove(bak_path)
        return True
    except OSError as e:
        if log_error:
            logger.error(f"Failed to remove backup file {bak_path}: {e}")
        return False


# 注意：原 UpdateStatus 枚举已移除。当前 handle_steam_update() 返回
# (should_continue: bool, cancel_or_error: bool) 元组。若未来需要更丰富的
# 状态表达，可重新引入枚举并改造返回值。


def _show_error(gui_app, title, msg):
    if not gui_app:
        return
    if hasattr(gui_app, "thread_safe_showerror"):
        gui_app.thread_safe_showerror(title, msg)


def _ask_yes_no(gui_app, title, msg):
    if not gui_app:
        return False
    if hasattr(gui_app, "thread_safe_askyesno"):
        return gui_app.thread_safe_askyesno(title, msg)
    return False


def _show_info(gui_app, title, msg):
    if not gui_app:
        return
    if hasattr(gui_app, "thread_safe_showinfo"):
        gui_app.thread_safe_showinfo(title, msg)


# ================= 状态机处理函数 =================


def _handle_both_missing(on_error):
    """处理 ASAR 和备份都不存在的情况"""
    logger.error("Neither ASAR nor backup file exists - game files may be corrupted or incomplete")
    if on_error:
        on_error(T("title_game_files_missing"), T("msg_game_files_missing"))
    return (False, True)


def _handle_asar_missing(core, bak_path, asar_path, on_error, on_ask_yes_no):
    """处理 ASAR 不存在，备份存在的情况"""
    if not asar_path:
        logger.error("Cannot restore ASAR: target asar_path is None or empty")
        if on_error:
            on_error(
                T("title_asar_path_error", "ASAR Path Error"),
                "Cannot restore ASAR: target path is not specified.",
            )
        return (False, True)

    logger.warning("ASAR file missing but backup exists - possible Steam update detected")

    backup_valid, backup_reason = validate_asar_with_reason(bak_path)
    if not backup_valid:
        logger.error(f"Backup file is corrupted: {backup_reason}")
        if on_error:
            on_error(
                T("title_backup_corrupted"),
                T("msg_backup_corrupted")
                + f"\n\n{T('lbl_reason', 'Reason')}: {backup_reason}",
            )
        return (False, True)

    if on_ask_yes_no:
        # 弹窗提醒去Steam验证完整性，询问是否确认备份是最新并从BAK恢复打补丁
        result = on_ask_yes_no(
            T("title_steam_update_detected", "Steam Update Detected"),
            T(
                "msg_steam_update_restore_confirm",
                "ASAR file is missing but backup exists.\n"
                "This may be caused by a Steam update.\n\n"
                "Recommended: Verify game integrity in Steam first.\n\n"
                "Are you sure the backup is up-to-date and want to restore from backup and apply patch?",
            ),
        )
        if not result:
            return (False, True)

    logger.info("Restoring ASAR from backup...")
    try:
        if os.path.exists(asar_path):
            os.remove(asar_path)
        os.replace(bak_path, asar_path)
        logger.info(f"Successfully restored ASAR from backup: {bak_path}")
        return (True, False)
    except OSError as e:
        logger.error(f"Failed to restore ASAR from backup: {e}")
        return (False, True)


def _handle_backup_missing(core, asar_path, on_error, on_ask_yes_no):
    """处理 ASAR 存在，备份不存在的情况"""
    logger.info(T("msg_asar_exists_no_backup"))
    asar_valid, asar_reason = validate_asar_with_reason(asar_path)
    if not asar_valid:
        logger.error(f"ASAR file is corrupted: {asar_reason}")
        if on_error:
            on_error(
                T("title_asar_corrupted"),
                T("msg_asar_corrupted")
                + f"\n\n{T('lbl_reason', 'Reason')}: {asar_reason}",
            )
        return (False, True)

    if on_ask_yes_no:
        result = on_ask_yes_no(
            T("title_first_time_patch", "First Time Patch"),
            T(
                "msg_first_time_patch_warn",
                "No original backup detected. Please verify game files in Steam first if you have used other patches before. Continue?",
            ),
        )
        if not result:
            return (False, True)

    return (True, False)


def _get_fallback_patch_hashes():
    """从本地 Patch.zip 或 Patch/ 目录中动态提取验证文件的哈希值作为 fallback"""
    import hashlib
    import zipfile

    from utils.constants import HASH_CHUNK_SIZE
    from utils.paths import get_resource_path

    check_files = get_config().check_files_for_update
    hashes = {}
    if not check_files:
        return hashes

    patch_zip = get_resource_path("Patch.zip")
    patch_dir = get_resource_path("Patch")

    if os.path.exists(patch_zip):
        try:
            with zipfile.ZipFile(patch_zip, "r") as zf:
                for file_path in check_files:
                    zip_path = file_path.replace("\\", "/")
                    try:
                        with zf.open(zip_path, "r") as f:
                            sha256_hash = hashlib.sha256()
                            for chunk in iter(lambda: f.read(HASH_CHUNK_SIZE), b""):
                                sha256_hash.update(chunk)
                            hashes[file_path] = sha256_hash.hexdigest()
                    except KeyError:
                        continue
        except Exception as e:
            logger.debug(f"Fallback hash extraction from Patch.zip failed: {e}")

    elif os.path.exists(patch_dir):
        from utils.file_ops import compute_file_hash

        for file_path in check_files:
            full_path = os.path.join(patch_dir, file_path)
            if os.path.exists(full_path):
                h = compute_file_hash(full_path)
                if h:
                    hashes[file_path] = h

    return hashes


def _handle_both_exist(core, base_dir, asar_path, bak_path, on_info, on_ask_yes_no, on_error):
    """处理 ASAR 存在，备份也存在的情况"""
    logger.info("Both ASAR and backup exist - checking patch status via file hashes")

    bak_valid = _validate_backup_integrity(bak_path, core)
    asar_valid = _validate_asar_integrity(asar_path, core)

    if not bak_valid and not asar_valid:
        return _handle_both_corrupted(on_error)

    if not bak_valid and asar_valid:
        return _handle_backup_corrupted_asar_valid(asar_path, bak_path, on_ask_yes_no, on_error)

    if bak_valid and not asar_valid:
        return _handle_asar_corrupted_backup_valid(asar_path, bak_path, on_ask_yes_no, on_error)

    return _handle_both_valid(base_dir, asar_path, bak_path, on_info, on_ask_yes_no, on_error)


def _handle_both_corrupted(on_error):
    """处理 ASAR 和备份都损坏的情况"""
    logger.error("Both ASAR and Backup are corrupted!")
    if on_error:
        on_error(
            T("title_error", "Data Corrupted"),
            T(
                "msg_both_corrupted",
                "Both game files and backup are corrupted. Please verify game files in Steam.",
            ),
        )
    return (False, True)


def _handle_backup_corrupted_asar_valid(asar_path, bak_path, on_ask_yes_no, on_error):
    """处理备份损坏但 ASAR 有效的情况"""
    logger.warning("Backup file is corrupted, but ASAR appears valid")

    stable_files = get_config().stable_files_for_validation
    asar_legitimate = True
    if stable_files:
        stable_hashes = get_file_hashes_in_asar(asar_path, stable_files)
        for file_path in stable_files:
            asar_hash = stable_hashes.get(file_path)
            if not asar_hash:
                logger.warning(f"ASAR missing stable file: {file_path}")
                asar_legitimate = False
                break
        if asar_legitimate:
            logger.info("ASAR passed stable_files validation, appears legitimate")
    else:
        logger.warning("No stable_files configured, skipping deep validation")

    if not asar_legitimate:
        logger.error("ASAR failed stable_files validation, may be corrupted or modified")
        if on_error:
            on_error(
                T("title_asar_invalid", "ASAR Invalid"),
                T(
                    "msg_asar_invalid",
                    "ASAR failed validation. Please verify game files in Steam.",
                )
                + f"\n\n{T('lbl_reason', 'Reason')}: missing or unreadable stable files",
            )
        return (False, True)

    if on_ask_yes_no:
        result = on_ask_yes_no(
            T("title_backup_corrupted_asar_valid"),
            T("msg_backup_corrupted_asar_valid"),
        )
        if not result:
            return (False, True)

    _remove_backup_safely(bak_path)
    return (True, False)


def _handle_asar_corrupted_backup_valid(asar_path, bak_path, on_ask_yes_no, on_error):
    """处理 ASAR 损坏但备份有效的情况"""
    asar_valid_detail, asar_reason = validate_asar_with_reason(asar_path)
    logger.warning(
        "ASAR is corrupted, but Backup is valid. "
        f"Reverting ASAR to Backup. Reason: {asar_reason if not asar_valid_detail else 'unknown'}"
    )
    if on_ask_yes_no:
        result = on_ask_yes_no(
            T("title_asar_corrupted"),
            T(
                "msg_asar_corrupted_valid_backup",
                "ASAR is corrupted but a valid backup was found. Restore from backup and repatch?",
            )
            + (
                f"\n\n{T('lbl_reason', 'Reason')}: {asar_reason}"
                if not asar_valid_detail and asar_reason
                else ""
            ),
        )
        if not result:
            return (False, True)

    try:
        if os.path.exists(asar_path):
            os.remove(asar_path)
        os.replace(bak_path, asar_path)
        logger.info(f"Successfully restored ASAR from backup: {bak_path}")
    except OSError as e:
        logger.error(f"Failed to restore ASAR from backup: {e}")
        if on_error:
            on_error(T("title_error"), f"Failed to restore ASAR from backup: {e}")
        return (False, True)

    return (True, False)


def _load_patch_hashes(base_dir):
    """加载补丁哈希，依次从 patch_meta、Patch payload、patch_info 中获取"""
    patch_meta_file = get_config().patch_meta_file
    meta_file = os.path.join(base_dir, patch_meta_file)
    patch_files = {}

    if os.path.exists(meta_file):
        try:
            with open(meta_file, encoding="utf-8") as f:
                meta_info = json.load(f)
            patch_files = meta_info.get("patch_files", {})
        except Exception as e:
            logger.warning(f"Failed to read patch meta: {e}")

    if not patch_files:
        logger.info(
            "Patch meta missing or empty, attempting to read hashes directly from Patch payload..."
        )
        patch_files = _get_fallback_patch_hashes()

    if not patch_files:
        patch_info_file = get_config().patch_info_file
        info_file = os.path.join(base_dir, patch_info_file)
        if not os.path.exists(info_file):
            logger.warning(
                "Patch info and meta files missing - may be old version patch or used other tools"
            )
            return None
        else:
            logger.warning("Found old patch info without meta file - recommend repatching")
            return {}

    return patch_files


def _handle_both_valid(base_dir, asar_path, bak_path, on_info, on_ask_yes_no, on_error):
    """处理 ASAR 和备份都有效的情况：通过哈希比较判断补丁状态"""
    check_files = get_config().check_files_for_update

    if not check_files:
        logger.warning(
            "check_files_for_update is empty; skipping hash verification and continuing."
        )
        return (True, False)

    patch_files = _load_patch_hashes(base_dir)
    if patch_files is None:
        if on_ask_yes_no:
            result = on_ask_yes_no(T("title_no_patch_info"), T("msg_no_patch_info"))
            return (result, not result)
        return (True, False)

    if not patch_files:
        return (True, False)

    expected_check_files = [
        file_path for file_path in check_files if patch_files.get(file_path)
    ]
    asar_hashes = get_file_hashes_in_asar(asar_path, expected_check_files)

    asar_match_patch, mismatched_against_patch = _compare_asar_with_patch(
        asar_hashes, patch_files, expected_check_files
    )

    if asar_match_patch:
        logger.info("All crucial files in ASAR match the patch meta. Patch is active.")
        if on_info:
            on_info(
                T("title_success", "Already Patched"),
                T(
                    "msg_already_patched",
                    "The game is already patched. No need to apply again.",
                ),
            )
        return (False, False)

    check_files_match_bak = _compare_asar_with_backup(
        asar_hashes, bak_path, expected_check_files
    )

    if not check_files_match_bak:
        return _handle_inconsistent_state(
            mismatched_against_patch, bak_path, on_ask_yes_no
        )

    return _handle_steam_update_detected(asar_path, bak_path)


def _compare_asar_with_patch(asar_hashes, patch_files, expected_check_files):
    """比较 ASAR 哈希与补丁元数据，返回 (是否匹配, 不匹配列表)"""
    asar_match_patch = True
    mismatched_against_patch = []

    for file_path in expected_check_files:
        expected_hash = patch_files[file_path]
        asar_hash = asar_hashes.get(file_path)
        if asar_hash != expected_hash:
            asar_match_patch = False
            mismatched_against_patch.append((file_path, expected_hash, asar_hash))

    return asar_match_patch, mismatched_against_patch


def _compare_asar_with_backup(asar_hashes, bak_path, expected_check_files):
    """比较 ASAR 和 BAK 的 check_files 哈希，判断是否一致"""
    bak_hashes = get_file_hashes_in_asar(bak_path, expected_check_files)

    for file_path in expected_check_files:
        asar_hash = asar_hashes.get(file_path)
        bak_hash = bak_hashes.get(file_path)
        if asar_hash != bak_hash:
            return False
    return True


def _handle_inconsistent_state(mismatched_against_patch, bak_path, on_ask_yes_no):
    """处理 ASAR 与 BAK 不一致且与补丁也不匹配的情况"""
    logger.warning(
        f"ASAR check files differ from backup. "
        f"Mismatched files against patch: {len(mismatched_against_patch)}."
    )
    for file_path, expected, asar_h in mismatched_against_patch:
        logger.debug(f"  - {file_path}: patch={expected[:16]}..., asar={asar_h[:16]}...")

    if on_ask_yes_no:
        result = on_ask_yes_no(
            T("title_inconsistent_state", "Inconsistent File State"),
            T(
                "msg_inconsistent_state",
                "Game file and backup differ, and neither matches this patch.\n"
                "If you just verified game integrity in Steam, click 'Yes' to discard old backup and apply patch.\n"
                "If you have NOT verified integrity, click 'No', go to Steam to verify integrity first, then try again.",
            ),
        )
        if result:
            _remove_backup_safely(bak_path)
        return (result, not result)
    else:
        logger.warning(
            "Batch mode: inconsistent file state detected between ASAR and backup. "
            "Discarding old backup and repatching (consider verifying game integrity via Steam)."
        )
        _remove_backup_safely(bak_path, log_error=True)
        return (True, False)


def _handle_steam_update_detected(asar_path, bak_path):
    """处理检测到 Steam 更新的情况（check_files 匹配 BAK 但整体不同）"""
    from utils.file_ops import quick_file_hash

    asar_quick_hash = quick_file_hash(asar_path)
    bak_quick_hash = quick_file_hash(bak_path)

    if asar_quick_hash == bak_quick_hash:
        logger.info(
            "ASAR quick hash matches backup. The game appears to be in its original state. "
            "Removing old backup and allowing re-patch."
        )
    else:
        logger.info(
            "Crucial files match backup but overall ASAR differs (quick hash). Steam update detected. "
            "Removing old backup and allowing re-patch."
        )

    _remove_backup_safely(bak_path)
    return (True, False)


def handle_steam_update(
    core,
    base_dir: str,
    bak_path: str,
    asar_path: Optional[str] = None,
    log_callback: Optional[Callable] = None,
    on_error: Optional[Callable] = None,
    on_ask_yes_no: Optional[Callable] = None,
    on_info: Optional[Callable] = None,
) -> Tuple[bool, bool]:
    """
    处理Steam更新检测和文件状态检查

    检测逻辑：
    1. ASAR 存在，备份不存在 → 首次打补丁或已使用其他补丁工具
    2. ASAR 存在，备份存在 → 检查补丁信息，判断是否需要重新打补丁
    3. ASAR 不存在，备份存在 → Steam 更新后自动恢复备份
    4. ASAR 不存在，备份不存在 → 游戏文件损坏或安装不完整

    Args:
        core: CoreLogic 实例
        base_dir: 基础目录
        bak_path: 备份文件路径
        asar_path: asar文件路径（可选，用于验证文件存在性）
        log_callback: 日志回调函数
        on_error: 错误提示回调，接收 (title, msg) 参数
        on_ask_yes_no: 询问回调，接收 (title, msg) 参数并返回 bool
        on_info: 信息提示回调，接收 (title, msg) 参数

    Returns:
        tuple: (should_continue, cancel_or_error)
            should_continue: 是否应该继续打补丁
            cancel_or_error: 是否因为错误或用户取消而停止
    """
    if log_callback:
        log_callback("Checking for Steam updates...")

    asar_exists = asar_path and os.path.exists(asar_path)
    bak_exists = os.path.exists(bak_path)

    # 情况 4：ASAR 和备份都不存在
    if not asar_exists and not bak_exists:
        return _handle_both_missing(on_error)

    # 情况 3：ASAR 不存在，备份存在
    if not asar_exists and bak_exists:
        return _handle_asar_missing(core, bak_path, asar_path, on_error, on_ask_yes_no)

    # 情况 1：ASAR 存在，备份不存在
    if asar_exists and not bak_exists:
        return _handle_backup_missing(core, asar_path, on_error, on_ask_yes_no)

    # 情况 2：ASAR 存在，备份存在
    if asar_exists and bak_exists:
        return _handle_both_exist(
            core, base_dir, asar_path, bak_path, on_info, on_ask_yes_no, on_error
        )

    # 默认情况
    logger.warning("Unexpected file state, proceeding with caution")
    return (True, False)


def _validate_archive_integrity(archive_path, core, archive_type="archive"):
    """
    验证归档文件（ASAR 或备份）的完整性

    支持 8 字节和 16 字节两种 ASAR 格式。

    Args:
        archive_path: 归档文件路径
        core: CoreLogic 实例
        archive_type: 归档类型（"asar" 或 "backup"），用于日志记录

    Returns:
        bool: 文件是否有效
    """
    monitor = get_performance_monitor()
    monitor.start(f"validate_{archive_type}")

    try:
        file_size = os.path.getsize(archive_path)
        if file_size < MIN_ASAR_SIZE:
            logger.warning(f"{archive_type.capitalize()} file too small: {file_size} bytes")
            return False

        valid, reason = validate_asar_with_reason(archive_path)
        if not valid:
            logger.warning(f"{archive_type.capitalize()} file is corrupted or unsupported: {reason}")
            return False

        return True
    except Exception as e:
        logger.error(f"Error validating {archive_type} integrity: {e}")
        return False
    finally:
        elapsed = monitor.stop(f"validate_{archive_type}")
        logger.debug(f"Validate {archive_type} integrity took {elapsed:.3f}s")


def _validate_asar_integrity(asar_path, core):
    """
    验证 ASAR 文件的完整性

    Args:
        asar_path: ASAR 文件路径
        core: CoreLogic 实例

    Returns:
        bool: 文件是否有效
    """
    return _validate_archive_integrity(asar_path, core, "asar")


def _validate_backup_integrity(bak_path, core):
    """
    验证备份文件的完整性

    Args:
        bak_path: 备份文件路径
        core: CoreLogic 实例

    Returns:
        bool: 文件是否有效
    """
    return _validate_archive_integrity(bak_path, core, "backup")
