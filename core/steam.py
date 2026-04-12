# -*- coding: utf-8 -*-
"""
Steam 更新检测和处理模块

提供 Steam 更新检测、文件状态检查和补丁状态验证功能。
"""

import os
import shutil
import json
import logging

from typing import Callable, Optional, Tuple

from utils.language import T
from utils.performance import get_performance_monitor
from utils.asar_utils import get_file_hash_in_asar
from utils.constants import MIN_ASAR_SIZE
from core.config import get_config

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
    logger.error(
        "Neither ASAR nor backup file exists - game files may be corrupted or incomplete"
    )
    if on_error:
        on_error(T("title_game_files_missing"), T("msg_game_files_missing"))
    return (False, True)


def _handle_asar_missing(core, bak_path, asar_path, on_error, on_ask_yes_no):
    """处理 ASAR 不存在，备份存在的情况"""
    if not asar_path:
        logger.error("Cannot restore ASAR: target asar_path is None or empty")
        if on_error:
            on_error(
                "ASAR Path Error",
                "Cannot restore ASAR: target path is not specified.",
            )
        return (False, True)

    logger.warning(
        "ASAR file missing but backup exists - possible Steam update detected"
    )

    if not _validate_backup_integrity(bak_path, core):
        logger.error("Backup file is corrupted")
        if on_error:
            on_error(T("title_backup_corrupted"), T("msg_backup_corrupted"))
        return (False, True)

    if on_ask_yes_no:
        result = on_ask_yes_no(
            T("title_asar_missing"), T("msg_asar_missing_valid_backup")
        )
        if not result:
            return (False, True)

    logger.info("Restoring ASAR from backup...")
    try:
        shutil.copy2(bak_path, asar_path)
        logger.info(f"Successfully restored ASAR from backup: {bak_path}")
        return (True, False)
    except (OSError, IOError) as e:
        logger.error(f"Failed to restore ASAR from backup: {e}")
        return (False, True)


def _handle_backup_missing(core, asar_path, on_error, on_ask_yes_no):
    """处理 ASAR 存在，备份不存在的情况"""
    logger.info(T("msg_asar_exists_no_backup"))
    if not _validate_asar_integrity(asar_path, core):
        logger.error("ASAR file is corrupted")
        if on_error:
            on_error(T("title_asar_corrupted"), T("msg_asar_corrupted"))
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


def _verify_update_hash(core, asar_path, bak_path, patch_files, on_info, on_ask_yes_no):
    """验证补丁哈希以检测 Steam 更新"""
    check_files = get_config().check_files_for_update

    if not check_files:
        logger.warning(
            "check_files_for_update is empty; skipping hash verification and continuing."
        )
        return (True, False)

    all_match_patch = True
    mismatched_files = []

    for file_path in check_files:
        expected_hash = patch_files.get(file_path)
        if not expected_hash:
            continue

        current_hash = get_file_hash_in_asar(asar_path, file_path)
        if current_hash != expected_hash:
            all_match_patch = False
            mismatched_files.append((file_path, expected_hash, current_hash))
            logger.info(
                f"File {file_path} in ASAR hash mismatch. Expected: {expected_hash}, Got: {current_hash}"
            )
            # 不再break，继续检查所有文件
            # 这样可以提供完整的变化报告

    if all_match_patch:
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
    else:
        logger.info(
            f"ASAR crucial files do not match patch meta. "
            f"Mismatched files: {len(mismatched_files)}. "
            f"Checking if it's a Steam update..."
        )
        # 记录所有不匹配的文件
        for file_path, expected, actual in mismatched_files:
            logger.debug(
                f"  - {file_path}: expected={expected[:16]}..., actual={actual[:16]}..."
            )

        all_match_bak = True
        for file_path, expected_hash, current_hash in mismatched_files:
            bak_hash = get_file_hash_in_asar(bak_path, file_path)
            asar_hash = get_file_hash_in_asar(asar_path, file_path)

            if bak_hash != asar_hash:
                all_match_bak = False
                logger.info(
                    f"File {file_path} differs between ASAR and backup. Bak: {bak_hash}, ASAR: {asar_hash}"
                )
                # 只检查第一个不匹配的文件来判断是否是Steam更新
                break

        if all_match_bak:
            logger.info("ASAR crucial files match backup files. Steam update detected.")
            _remove_backup_safely(bak_path)
            return (True, False)
        else:
            logger.warning(
                "ASAR files do not match patch OR backup. Possible third-party patch or major Steam update detected."
            )

            if on_ask_yes_no:
                result = on_ask_yes_no(
                    T("title_inconsistent_state", "Inconsistent File State"),
                    T(
                        "msg_inconsistent_state",
                        "Game file and backup differ, and neither matches this patch.\nIf you just verified game integrity in Steam, click 'Yes' to discard old backup and apply patch.\nIf you have NOT verified integrity, click 'No', go to Steam to verify integrity first, then try again.",
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


def _get_fallback_patch_hashes():
    """从本地 Patch.zip 或 Patch/ 目录中动态提取验证文件的哈希值作为 fallback"""
    import zipfile
    import hashlib
    from utils.paths import get_resource_path
    from utils.constants import HASH_CHUNK_SIZE

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


def _handle_both_exist(
    core, base_dir, asar_path, bak_path, on_info, on_ask_yes_no, on_error
):
    """处理 ASAR 存在，备份也存在的情况"""
    logger.info("Both ASAR and backup exist - checking patch status via file hashes")

    bak_valid = _validate_backup_integrity(bak_path, core)
    asar_valid = _validate_asar_integrity(asar_path, core)

    if not bak_valid and not asar_valid:
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

    if not bak_valid and asar_valid:
        logger.warning("Backup file is corrupted, but ASAR is valid")
        if on_ask_yes_no:
            result = on_ask_yes_no(
                T("title_backup_corrupted_asar_valid"),
                T("msg_backup_corrupted_asar_valid"),
            )
            if not result:
                return (False, True)

        # 用户选择重建备份，必须先删除损坏的备份才能触发 patch_controller 重新复制
        _remove_backup_safely(bak_path)
        return (True, False)

    if bak_valid and not asar_valid:
        logger.warning(
            "ASAR is corrupted, but Backup is valid. Reverting ASAR to Backup."
        )
        if on_ask_yes_no:
            result = on_ask_yes_no(
                T("title_asar_corrupted"),
                T(
                    "msg_asar_corrupted_valid_backup",
                    "ASAR is corrupted but a valid backup was found. Restore from backup and repatch?",
                ),
            )
            if not result:
                return (False, True)

        try:
            shutil.copy2(bak_path, asar_path)
            logger.info(f"Successfully restored ASAR from backup: {bak_path}")
        except (OSError, IOError) as e:
            logger.error(f"Failed to restore ASAR from backup: {e}")
            if on_error:
                on_error(T("title_error"), f"Failed to restore ASAR from backup: {e}")
            return (False, True)

        return (True, False)

    # Both are valid, proceed to verify patch hashes
    patch_meta_file = get_config().patch_meta_file
    meta_file = os.path.join(base_dir, patch_meta_file)

    patch_files = None

    if os.path.exists(meta_file):
        try:
            with open(meta_file, "r", encoding="utf-8") as f:
                meta_info = json.load(f)
            patch_files = meta_info.get("patch_files", {})
        except Exception as e:
            logger.warning(f"Failed to read patch meta: {e}")

    if not patch_files:
        logger.info(
            "Patch meta missing or empty, attempting to read hashes directly from Patch payload..."
        )
        patch_files = _get_fallback_patch_hashes()

    if patch_files:
        return _verify_update_hash(
            core, asar_path, bak_path, patch_files, on_info, on_ask_yes_no
        )

    patch_info_file = get_config().patch_info_file
    info_file = os.path.join(base_dir, patch_info_file)
    if not os.path.exists(info_file):
        logger.warning(
            "Patch info and meta files missing - may be old version patch or used other tools"
        )
        if on_ask_yes_no:
            result = on_ask_yes_no(T("title_no_patch_info"), T("msg_no_patch_info"))
            return (result, not result)
        return (True, False)
    else:
        logger.warning("Found old patch info without meta file - recommend repatching")
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

    使用纯 Python 解析 ASAR header（与 asar_utils.py 同源逻辑），
    替代原先的 node.exe 子进程调用，避免约 0.5-1s 的进程启动开销。

    Args:
        archive_path: 归档文件路径
        core: CoreLogic 实例
        archive_type: 归档类型（"asar" 或 "backup"），用于日志记录

    Returns:
        bool: 文件是否有效
    """
    from utils.constants import ASAR_MAGIC_NUMBER
    import struct

    monitor = get_performance_monitor()
    monitor.start(f"validate_{archive_type}")

    try:
        file_size = os.path.getsize(archive_path)
        if file_size < MIN_ASAR_SIZE:
            logger.warning(
                f"{archive_type.capitalize()} file too small: {file_size} bytes"
            )
            return False

        try:
            with open(archive_path, "rb") as f:
                magic = f.read(4)
                if magic != ASAR_MAGIC_NUMBER:
                    logger.warning(
                        f"{archive_type.capitalize()} invalid ASAR magic number"
                    )
                    return False

                header_size_bytes = f.read(4)
                if len(header_size_bytes) != 4:
                    logger.warning(f"{archive_type.capitalize()} truncated header size")
                    return False

                header_size = struct.unpack("<I", header_size_bytes)[0]

                # 增加最大Header Size限制（例如50MB），防止OOM
                MAX_HEADER_SIZE = 50 * 1024 * 1024
                if header_size > MAX_HEADER_SIZE:
                    logger.warning(
                        f"{archive_type.capitalize()} header too large ({header_size} bytes)"
                    )
                    return False

                header_data = f.read(header_size)
                if len(header_data) != header_size or len(header_data) < 8:
                    logger.warning(f"{archive_type.capitalize()} truncated header data")
                    return False

                json_size = struct.unpack("<I", header_data[4:8])[0]
                if json_size == 0 or (8 + json_size) > len(header_data):
                    logger.warning(
                        f"{archive_type.capitalize()} invalid json_size in header"
                    )
                    return False

                json_str = header_data[8 : 8 + json_size].decode("utf-8")
                header_dict = json.loads(json_str)

                if "files" not in header_dict or "package.json" not in header_dict.get(
                    "files", {}
                ):
                    logger.warning(f"File not found in {archive_type}: package.json")
                    return False

        except (json.JSONDecodeError, struct.error, UnicodeDecodeError) as e:
            logger.warning(f"{archive_type.capitalize()} file is corrupted: {e}")
            return False
        except Exception as e:
            logger.warning(f"Failed to validate {archive_type} integrity: {e}")
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
