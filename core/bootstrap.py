# -*- coding: utf-8 -*-
"""
系统启动引导模块

整合所有改进的初始化流程：
1. 系统状态一致性检查
2. 磁盘空间检查
3. 操作锁初始化
4. 配置验证
"""

__all__ = ["bootstrap_system", "SystemBootstrapError"]

import os
import sys
import logging
from typing import Tuple, List, Optional

from core.config import get_config
from core.state_validator import validate_system_state, SystemState
from utils.disk_utils import get_disk_free_space, format_bytes
from utils.operation_lock import get_operation_lock

logger = logging.getLogger(__name__)


class SystemBootstrapError(Exception):
    """系统启动错误"""
    pass


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
