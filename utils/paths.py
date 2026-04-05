# -*- coding: utf-8 -*-

import os
import sys
import logging

logger = logging.getLogger(__name__)

def get_resource_path(relative_path: str) -> str:
    """
    获取资源路径（支持PyInstaller打包）
    Args:
        relative_path: 相对路径
    Returns:
        绝对路径
    """
    base_path = getattr(sys, '_MEIPASS', None)
    if base_path is None:
        base_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    path = os.path.join(base_path, relative_path)

    if not os.path.exists(path):
        logger.debug(f"Resource path not found or not yet created: {path}")

    return path

def normalize_path(path: str) -> str:
    """规范化路径，处理各种边界情况"""
    if not path:
        return ""
    try:
        path = path.strip()
        path = os.path.abspath(path)
        path = os.path.normpath(path)

        if len(path) > 260:
            logger.warning(f"Path too long: {len(path)} chars")

        return path
    except (TypeError, ValueError, AttributeError) as e:
        logger.exception(f"Path normalization failed due to invalid input: {e}")
        return ""
    except Exception as e:
        logger.exception(f"Unexpected error during path normalization: {e}")
        return ""


def validate_path_exists(path: str, path_type: str = "Resource") -> tuple[bool, str]:
    """
    验证路径是否存在
    
    Args:
        path: 路径字符串
        path_type: 路径类型描述（用于日志）
        
    Returns:
        tuple[bool, str]: (是否存在, 错误消息)
    """
    if not path:
        return False, f"{path_type} path is empty"
    
    if not os.path.exists(path):
        return False, f"{path_type} not found: {path}"
    
    return True, ""


def ensure_directory(dir_path: str) -> bool:
    """
    确保目录存在，不存在则创建
    
    Args:
        dir_path: 目录路径
        
    Returns:
        bool: 是否成功
    """
    try:
        if not os.path.exists(dir_path):
            os.makedirs(dir_path, exist_ok=True)
            logger.debug(f"Created directory: {dir_path}")
        return True
    except Exception as e:
        logger.error(f"Failed to create directory {dir_path}: {e}")
        return False


def get_user_config_path(filename: str = "config.ini") -> str:
    """
    获取用户配置文件路径（跨平台）
    
    Args:
        filename: 配置文件名
        
    Returns:
        str: 完整的配置文件路径
    """
    config_dir = os.path.join(os.path.expanduser("~"), ".tyranopatcher")
    return os.path.join(config_dir, filename)
