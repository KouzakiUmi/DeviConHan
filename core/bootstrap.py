"""
系统启动引导模块

整合所有改进的初始化流程：
1. 系统状态一致性检查
2. 磁盘空间检查
3. 操作锁初始化
4. 配置验证
"""

__all__ = [
    "bootstrap_system",
    "find_game_directory",
    "get_detected_game_path",
    "get_runtime_game_path",
    "SystemBootstrapError",
]

import logging
import os
from typing import List, Optional, Tuple

from core.config import get_config
from core.state_validator import SystemState, validate_system_state
from utils.disk_utils import format_bytes, get_disk_free_space
from utils.language import T
from utils.operation_lock import get_operation_lock

logger = logging.getLogger(__name__)

# 存储检测到的游戏目录（模块级缓存）
_detected_game_path: Optional[str] = None


class SystemBootstrapError(Exception):
    """系统启动错误"""

    pass


def get_detected_game_path() -> Optional[str]:
    """
    获取检测到的游戏目录

    Returns:
        str: 检测到的游戏目录，未检测返回 None
    """
    return _detected_game_path


def get_runtime_game_path() -> Optional[str]:
    """
    获取当前运行时应使用的游戏目录。

    优先返回已缓存且仍然有效的目录；若缓存为空或无效，则重新尝试自动检测。
    """
    config = get_config()

    if _detected_game_path and is_game_directory(_detected_game_path, config):
        return _detected_game_path

    detected = find_game_directory(auto_detect=True)
    if detected and is_game_directory(detected, config):
        return detected

    if config.game_path and is_game_directory(config.game_path, config):
        return config.game_path

    return None


def is_game_directory(path: str, config=None) -> bool:
    """
    检查指定目录是否是游戏目录

    检查以下任一情况存在即可：
    - resources/app.asar (主游戏资源)
    - resources/app.asar.bak (备份文件)
    - resources/app.asar.unpacked/ (已解压的 ASAR 目录)

    Args:
        path: 目录路径
        config: 配置对象

    Returns:
        bool: 是否是游戏目录
    """
    if not os.path.isdir(path):
        return False

    if config is None:
        config = get_config()

    from utils.platform import get_platform_info, get_resources_path

    info = get_platform_info()

    # 确定 resources 目录
    res_path = get_resources_path(path, info.system)

    # 检查是否存在 resources 目录
    if not os.path.isdir(res_path):
        logger.debug(f"Resources directory not found: {res_path}")
        return False

    # 检查是否有游戏文件（app.asar / app.asar.bak / app.asar.unpacked）
    asar_name = config.target_asar_name
    asar_path = os.path.join(res_path, asar_name)
    bak_path = asar_path + ".bak"
    unpacked_path = os.path.join(res_path, f"{asar_name}.unpacked")

    has_game_files = (
        os.path.isfile(asar_path)  # app.asar
        or os.path.isfile(bak_path)  # app.asar.bak
        or os.path.isdir(unpacked_path)  # app.asar.unpacked/
    )

    if has_game_files:
        logger.debug(f"Confirmed game directory: {path} (found ASAR or backup)")
        return True

    logger.debug(f"No game files found in: {res_path}")
    return False


def find_game_directory(base_dir: Optional[str] = None, auto_detect: bool = True) -> Optional[str]:
    """
    尝试自动检测游戏目录

    Args:
        base_dir: 基础目录（如果指定则直接使用）
        auto_detect: 是否允许自动检测（默认 True）

    Returns:
        str: 游戏目录路径，未找到返回 None
    """
    from utils.platform import find_game_in_steam, get_platform_info, get_steam_library_paths

    config = get_config()

    # 如果手动指定了游戏目录
    if base_dir:
        return base_dir

    if not auto_detect or not config.auto_detect_game:
        # 手动模式
        if config.game_path and os.path.exists(config.game_path):
            return config.game_path
        return None

    # 自动检测模式
    info = get_platform_info()
    logger.info(f"Detected platform: {info.system}")
    logger.info(f"Steam library search path: {info.steam_common_path}")

    # 在 Steam 目录中查找游戏
    search_paths = get_steam_library_paths()
    game_path = find_game_in_steam(
        config.game_id, search_paths, extra_variations=config.game_name_variations
    )

    # 自动检测失败时回退到手动配置路径
    if not game_path and config.game_path and os.path.exists(config.game_path):
        game_path = config.game_path
        logger.info(f"Auto-detection failed, falling back to configured game path: {game_path}")

    # 缓存结果
    global _detected_game_path
    _detected_game_path = game_path

    return game_path


def bootstrap_system(
    base_dir: Optional[str] = None,
    skip_state_check: bool = False,
    skip_disk_check: bool = False,
    allow_recovery: bool = False,
) -> Tuple[bool, List[str]]:
    """
    执行系统启动引导和验证

    Args:
        base_dir: 基础目录，默认为当前目录
        skip_state_check: 是否跳过状态检查
        skip_disk_check: 是否跳过磁盘检查
        allow_recovery: 游戏文件异常时仍允许进入 GUI，安装前仍会再次校验

    Returns:
        Tuple[bool, List[str]]: (是否成功, 警告/信息列表)

    Raises:
        SystemBootstrapError: 如果关键检查失败
    """
    messages = []

    logger.info("Starting system bootstrap...")

    # 1. 初始化配置（尽早获取 config）
    config = get_config()

    # 2. 确定游戏目录
    # 优先级：明确指定 > 自动检测 > 当前目录（如果是游戏目录）> 当前目录
    current_dir = os.path.abspath(".")

    if base_dir:
        # 明确指定
        logger.info(f"Using specified directory: {base_dir}")
    elif config.auto_detect_game:
        # 自动检测模式
        logger.info("Attempting Steam auto-detection...")
        detected = find_game_directory(auto_detect=True)
        if detected:
            base_dir = detected
            messages.append(f"Auto-detected game directory: {base_dir}")
            logger.info(f"Using auto-detected game directory: {base_dir}")
        elif is_game_directory(current_dir, config):
            base_dir = current_dir
            logger.info(f"Steam auto-detection failed; using current game directory: {base_dir}")
        else:
            base_dir = current_dir
            logger.info(f"Auto-detection failed, using current directory: {base_dir}")
    elif is_game_directory(current_dir, config):
        # 当前目录是有效的游戏目录
        base_dir = current_dir
        logger.info(f"Current directory is valid game directory: {base_dir}")
    else:
        # 使用当前目录
        base_dir = current_dir
        logger.info(f"Using current directory: {base_dir}")

    # 仅缓存真实游戏目录，避免把任意工作目录误当作检测结果
    global _detected_game_path
    _detected_game_path = base_dir if is_game_directory(base_dir, config) else None

    # If a previous process died during the two-rename ASAR commit, restore
    # the known original before any state validation presents misleading data.
    try:
        from controllers.patch_controller import recover_incomplete_patch

        recovery_message = recover_incomplete_patch(base_dir)
        if recovery_message:
            messages.append(f"Warning: {recovery_message}")
    except Exception as e:
        messages.append(f"Warning: Could not check incomplete patch recovery: {e}")

    # 2. 配置验证
    try:
        config_valid, errors, warnings = config.validate_config()

        if not config_valid:
            raise SystemBootstrapError(f"Configuration validation failed: {errors}")

        if warnings:
            messages.extend(warnings)

    except Exception as e:
        raise SystemBootstrapError(f"Failed to initialize configuration: {e}") from e

    # 3. 系统状态一致性检查
    if not skip_state_check:
        logger.info("Checking system state consistency...")
        state, issues = validate_system_state(base_dir)

        critical_errors = [i for i in issues if i.severity == "critical"]
        warnings_list = [i for i in issues if i.severity == "warning"]

        if critical_errors or state == SystemState.CORRUPTED:
            error_msg = f"System state errors: {[e.message for e in issues]}"
            logger.error(error_msg)
            if not allow_recovery:
                raise SystemBootstrapError(error_msg)
            messages.append("Warning: " + T("msg_game_recovery_needed"))

        for warning in warnings_list:
            messages.append(f"Warning: {warning.message}")
            if warning.suggestion:
                messages.append(f"  Suggestion: {warning.suggestion}")

        logger.info(f"System state: {state.value}")

    # 4. 磁盘空间检查
    if not skip_disk_check:
        logger.info("Checking disk space...")
        try:
            base = base_dir or os.path.abspath(".")
            free_space = get_disk_free_space(base)

            # 建议保留至少1GB空间
            MIN_FREE_SPACE = 1024 * 1024 * 1024  # 1GB

            if free_space < MIN_FREE_SPACE:
                messages.append(
                    f"Warning: Low disk space. Available: {format_bytes(free_space)}, "
                    f"Recommended: {format_bytes(MIN_FREE_SPACE)}"
                )
            else:
                logger.info(f"Disk space OK: {format_bytes(free_space)} available")

        except Exception as e:
            messages.append(f"Warning: Could not check disk space: {e}")

    # 5. 初始化操作锁
    try:
        _ = get_operation_lock()
        logger.debug("Operation lock initialized")
    except Exception as e:
        raise SystemBootstrapError(f"Failed to initialize operation lock: {e}") from e

    logger.info("System bootstrap completed successfully")
    return True, messages


def check_can_apply_patch(base_dir: Optional[str] = None) -> Tuple[bool, str]:
    """
    检查是否可以应用补丁

    Args:
        base_dir: 基础目录

    Returns:
        Tuple[bool, str]: (是否可以, 原因)
    """
    try:
        from core.state_validator import StateValidator

        validator = StateValidator(base_dir)
        can_apply, reason = validator.can_apply_patch()
        return can_apply, reason

    except Exception as e:
        return False, f"Cannot verify patch availability: {e}"


def check_can_restore_backup(base_dir: Optional[str] = None) -> Tuple[bool, str]:
    """
    检查是否可以恢复备份

    Args:
        base_dir: 基础目录

    Returns:
        Tuple[bool, str]: (是否可以, 原因)
    """
    try:
        from core.state_validator import StateValidator

        validator = StateValidator(base_dir)
        can_restore, reason = validator.can_restore_backup()
        return can_restore, reason

    except Exception as e:
        return False, f"Cannot verify restore availability: {e}"
