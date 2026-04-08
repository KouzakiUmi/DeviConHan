# -*- coding: utf-8 -*-
"""
Steam 更新检测和处理模块

提供 Steam 更新检测、文件状态检查和补丁状态验证功能。
"""

import os
import sys
import shutil
import subprocess
import json
import logging

from utils.language import T
from utils.performance import get_performance_monitor
from core.config import get_config

logger = logging.getLogger(__name__)

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


def _handle_both_missing(gui_app):
    """处理 ASAR 和备份都不存在的情况"""
    logger.error(
        "Neither ASAR nor backup file exists - game files may be corrupted or incomplete"
    )
    _show_error(gui_app, T("title_game_files_missing"), T("msg_game_files_missing"))
    return (False, True)


def _handle_asar_missing(core, bak_path, asar_path, gui_app):
    """处理 ASAR 不存在，备份存在的情况"""
    logger.warning(
        "ASAR file missing but backup exists - possible Steam update detected"
    )

    if not _validate_backup_integrity(bak_path, core):
        logger.error("Backup file is corrupted")
        _show_error(gui_app, T("title_backup_corrupted"), T("msg_backup_corrupted"))
        return (False, True)

    if gui_app:
        result = _ask_yes_no(
            gui_app, T("title_asar_missing"), T("msg_asar_missing_valid_backup")
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


def _handle_backup_missing(core, asar_path, gui_app):
    """处理 ASAR 存在，备份不存在的情况"""
    logger.info(T("msg_asar_exists_no_backup"))
    if not _validate_asar_integrity(asar_path, core):
        logger.error("ASAR file is corrupted")
        _show_error(gui_app, T("title_asar_corrupted"), T("msg_asar_corrupted"))
        return (False, True)

    if gui_app:
        result = _ask_yes_no(
            gui_app,
            T("title_first_time_patch", "First Time Patch"),
            T(
                "msg_first_time_patch_warn",
                "No original backup detected. Please verify game files in Steam first if you have used other patches before. Continue?",
            ),
        )
        if not result:
            return (False, True)

    return (True, False)


def _verify_update_hash(core, asar_path, bak_path, patch_files, gui_app):
    """验证补丁哈希以检测 Steam 更新"""
    check_files = get_config().check_files_for_update
    all_match_patch = True
    mismatched_files = []

    from utils.asar_utils import get_file_hash_in_asar  # 避免循环导入

    for file_path in check_files:
        expected_hash = patch_files.get(file_path)
        if not expected_hash:
            continue

        current_hash = get_file_hash_in_asar(core, asar_path, file_path)
        if current_hash != expected_hash:
            all_match_patch = False
            mismatched_files.append(file_path)
            logger.info(
                f"File {file_path} in ASAR hash mismatch. Expected: {expected_hash}, Got: {current_hash}"
            )
            break

    if all_match_patch:
        logger.info("All crucial files in ASAR match the patch meta. Patch is active.")
        _show_info(
            gui_app,
            T("title_success", "Already Patched"),
            T(
                "msg_already_patched",
                "The game is already patched. No need to apply again.",
            ),
        )
        return (False, False)
    else:
        logger.info(
            "ASAR crucial files do not match patch meta. Checking if it's a Steam update..."
        )

        all_match_bak = True
        for file_path in mismatched_files:
            bak_hash = get_file_hash_in_asar(core, bak_path, file_path)
            asar_hash = get_file_hash_in_asar(core, asar_path, file_path)

            if bak_hash != asar_hash:
                all_match_bak = False
                logger.info(
                    f"File {file_path} differs between ASAR and backup. Bak: {bak_hash}, ASAR: {asar_hash}"
                )
                break

        if all_match_bak:
            logger.info("ASAR crucial files match backup files. Steam update detected.")
            try:
                if os.path.exists(bak_path):
                    os.remove(bak_path)
            except OSError as e:
                logger.error(f"Failed to remove old backup for rebuilding: {e}")
            return (True, False)
        else:
            logger.warning(
                "ASAR files do not match patch OR backup. Possible third-party patch or major Steam update detected."
            )

            if gui_app:
                result = _ask_yes_no(
                    gui_app,
                    T("title_third_party_patch_detected", "Modified ASAR Detected"),
                    T(
                        "msg_third_party_patch_detected",
                        "ASAR file has been modified by an unknown source or major Steam update.\nDo you want to rebuild backup and apply this patch?",
                    ),
                )
                if result:
                    try:
                        if os.path.exists(bak_path):
                            os.remove(bak_path)
                    except OSError as e:
                        logger.error(f"Failed to remove old backup: {e}")
                return (result, not result)
            else:
                try:
                    if os.path.exists(bak_path):
                        os.remove(bak_path)
                except OSError:
                    pass
                return (True, False)


def _handle_both_exist(core, base_dir, asar_path, bak_path, gui_app):
    """处理 ASAR 存在，备份也存在的情况"""
    logger.info("Both ASAR and backup exist - checking patch status via file hashes")

    if not _validate_backup_integrity(bak_path, core):
        logger.warning("Backup file is corrupted, but ASAR is valid")
        if gui_app:
            result = _ask_yes_no(
                gui_app,
                T("title_backup_corrupted_asar_valid"),
                T("msg_backup_corrupted_asar_valid"),
            )
            if not result:
                return (False, True)
        return (True, False)

    patch_meta_file = get_config().patch_meta_file
    meta_file = os.path.join(base_dir, patch_meta_file)

    if not os.path.exists(meta_file):
        patch_info_file = get_config().patch_info_file
        info_file = os.path.join(base_dir, patch_info_file)
        if not os.path.exists(info_file):
            logger.warning(
                "Patch info and meta files missing - may be old version patch or used other tools"
            )
            if gui_app:
                result = _ask_yes_no(
                    gui_app, T("title_no_patch_info"), T("msg_no_patch_info")
                )
                return (result, not result)
            return (True, False)
        else:
            logger.warning(
                "Found old patch info without meta file - recommend repatching"
            )
            return (True, False)

    try:
        with open(meta_file, "r", encoding="utf-8") as f:
            meta_info = json.load(f)

        patch_files = meta_info.get("patch_files", {})
        if not patch_files:
            logger.warning("No patch files listed in meta, cannot verify ASAR.")
            return (True, False)

        return _verify_update_hash(core, asar_path, bak_path, patch_files, gui_app)

    except (json.JSONDecodeError, IOError, OSError) as e:
        logger.warning(f"Failed to check patch meta: {e}")
        return (True, False)


def handle_steam_update(
    core, base_dir, bak_path, asar_path=None, log_callback=None, gui_app=None
):
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
        gui_app: GUI应用实例（用于显示对话框）

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
        return _handle_both_missing(gui_app)

    # 情况 3：ASAR 不存在，备份存在
    if not asar_exists and bak_exists:
        return _handle_asar_missing(core, bak_path, asar_path, gui_app)

    # 情况 1：ASAR 存在，备份不存在
    if asar_exists and not bak_exists:
        return _handle_backup_missing(core, asar_path, gui_app)

    # 情况 2：ASAR 存在，备份存在
    if asar_exists and bak_exists:
        return _handle_both_exist(core, base_dir, asar_path, bak_path, gui_app)

    # 默认情况
    logger.warning("Unexpected file state, proceeding with caution")
    return (True, False)


def _validate_archive_integrity(archive_path, core, archive_type="archive"):
    """
    验证归档文件（ASAR 或备份）的完整性

    Args:
        archive_path: 归档文件路径
        core: CoreLogic 实例
        archive_type: 归档类型（"asar" 或 "backup"），用于日志记录

    Returns:
        bool: 文件是否有效
    """
    # 使用性能监控器记录验证操作
    monitor = get_performance_monitor()
    monitor.start(f"validate_{archive_type}")

    try:
        from utils.constants import MIN_ASAR_SIZE

        # 检查文件大小
        file_size = os.path.getsize(archive_path)
        if file_size < MIN_ASAR_SIZE:  # 小于 MIN_ASAR_SIZE 可能是损坏的
            logger.warning(
                f"{archive_type.capitalize()} file too small: {file_size} bytes"
            )
            return False

        # 尝试读取归档文件的基本信息
        try:
            cmd = [
                core.node_path,
                core.script_path,
                "stat",
                archive_path,
                "package.json",
            ]
            creationflags = 0
            if sys.platform.startswith("win"):
                creationflags = subprocess.CREATE_NO_WINDOW
            proc_result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=10,
                check=True,
                encoding="utf-8",
                creationflags=creationflags,
            )
            data = json.loads(proc_result.stdout.strip())
            if not data.get("success"):
                error_type = data.get("error_type", "unknown")
                if error_type == "file_not_found":
                    logger.warning(f"File not found in {archive_type}: package.json")
                    return False
                elif error_type == "file_corrupted":
                    logger.warning(
                        f"{archive_type.capitalize()} file is corrupted: {data.get('error')}"
                    )
                    return False
                else:
                    logger.warning(
                        f"{archive_type.capitalize()} stat failed: {data.get('error')}"
                    )
                    return False
        except subprocess.CalledProcessError as e:
            # 解析 stderr 中的 JSON 错误信息
            try:
                error_data = json.loads(e.stderr.strip())
                error_type = error_data.get("error_type", "unknown")
                if error_type == "file_not_found":
                    logger.warning(f"File not found in {archive_type}: package.json")
                    return False
                elif error_type == "file_corrupted":
                    logger.warning(
                        f"{archive_type.capitalize()} file is corrupted: {error_data.get('error')}"
                    )
                    return False
                else:
                    logger.warning(
                        f"{archive_type.capitalize()} stat failed: {error_data.get('error')}"
                    )
                    return False
            except json.JSONDecodeError:
                logger.warning(f"Failed to parse error response: {e.stderr}")
                return False
        except Exception as e:
            logger.warning(f"Failed to validate {archive_type} integrity: {e}")
            return False

        return True
    except Exception as e:
        logger.error(f"Error validating {archive_type} integrity: {e}")
        return False
    finally:
        # 记录验证操作耗时
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


def _read_and_validate_patch_info(info_file):
    """
    读取并验证补丁信息文件

    Args:
        info_file: 补丁信息文件路径

    Returns:
        dict: 补丁信息，如果验证失败返回 None
    """
    try:
        # 检查文件大小
        file_size = os.path.getsize(info_file)
        if file_size == 0:
            logger.warning("Patch info file is empty")
            return None

        # 读取 JSON 内容
        with open(info_file, "r", encoding="utf-8") as f:
            content = f.read().strip()
            if not content:
                logger.warning("Patch info file contains only whitespace")
                return None

            patch_info = json.loads(content)
            return patch_info

    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse patch info JSON: {e}")
        return None
    except Exception as e:
        logger.error(f"Failed to read patch info: {e}")
        return None
