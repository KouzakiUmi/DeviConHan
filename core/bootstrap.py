# -*- coding: utf-8 -*-
"""
系统启动引导模块

整合所有改进的初始化流程：
1. 系统状态一致性检查
2. 磁盘空间检查
3. 操作锁初始化
4. 配置验证
"""

__all__ = ["bootstrap_system", "find_game_directory", "get_detected_game_path", "SystemBootstrapError"]

import os
import sys
import logging
from typing import Tuple, List, Optional

from core.config import get_config
from core.state_validator import validate_system_state, SystemState
from utils.disk_utils import get_disk_free_space, format_bytes
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


def find_game_directory(base_dir: Optional[str] = None) -> Optional[str]:
    """
    尝试自动检测游戏目录

    Args:
        base_dir: 基础目录（如果指定则直接使用）

    Returns:
        str: 游戏目录路径，未找到返回 None
    """
    from utils.platform import find_game_in_steam, get_platform_info, get_steam_library_paths

    config = get_config()

    # 如果手动指定了游戏目录
    if base_dir:
        return base_dir

    if not config.auto_detect_game:
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
    game_path = find_game_in_steam(config.game_id, search_paths)

    # 缓存结果
    global _detected_game_path
    _detected_game_path = game_path

    return game_path


def bootstrap_system(
    base_dir: Optional[str] = None,
    skip_state_check: bool = False,
    skip_disk_check: bool = False,
) -> Tuple[bool, List[str]]:
    """
    执行系统启动引导和验证

    Args:
        base_dir: 基础目录，默认为当前目录
        skip_state_check: 是否跳过状态检查
        skip_disk_check: 是否跳过磁盘检查

    Returns:
        Tuple[bool, List[str]]: (是否成功, 警告/信息列表)

    Raises:
        SystemBootstrapError: 如果关键检查失败
    """
    messages = []

    logger.info("Starting system bootstrap...")

    # 优先使用当前目录，自动检测仅作为备用
    default_base = base_dir or os.path.abspath(".")
    base_dir = default_base
    logger.info(f"Using directory: {base_dir}")

    # 自动检测（仅当配置启用且未明确指定目录时）
    if not base_dir and config.auto_detect_game:
        game_path = find_game_directory(base_dir)
        if game_path:
            base_dir = game_path
            messages.append(f"Auto-detected game directory: {base_dir}")
            logger.info(f"Using auto-detected game directory: {base_dir}")
    
    # 更新缓存
    global _detected_game_path
    _detected_game_path = base_dir

    # 1. 初始化配置
    try:
        config = get_config()
        config_valid, errors, warnings = config.validate_config()

        if not config_valid:
            raise SystemBootstrapError(f"Configuration validation failed: {errors}")

        if warnings:
            messages.extend(warnings)

    except Exception as e:
        raise SystemBootstrapError(f"Failed to initialize configuration: {e}") from e

    # 2. 系统状态一致性检查
    if not skip_state_check:
        logger.info("Checking system state consistency...")
        state, issues = validate_system_state(base_dir)
        
        critical_errors = [i for i in issues if i.severity == "critical"]
        warnings_list = [i for i in issues if i.severity == "warning"]
        
        if critical_errors:
            error_msg = f"System state critical errors: {[e.message for e in critical_errors]}"
            logger.error(error_msg)
            raise SystemBootstrapError(error_msg)
            
        for warning in warnings_list:
            messages.append(f"Warning: {warning.message}")
            if warning.suggestion:
                messages.append(f"  Suggestion: {warning.suggestion}")
                
        logger.info(f"System state: {state.value}")
        
    # 3. 磁盘空间检查
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
            
    # 4. 初始化操作锁
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
