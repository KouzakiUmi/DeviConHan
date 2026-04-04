# -*- coding: utf-8 -*-

import os
import sys
import logging

logger = logging.getLogger(__name__)

def get_resource_path(relative_path):
    """
    获取资源路径（支持PyInstaller打包）
    Args:
        relative_path: 相对路径
    Returns:
        绝对路径
    Raises:
        FileNotFoundError: 如果文件不存在
    """
    base_path = getattr(sys, '_MEIPASS', None)
    if base_path is None:
        base_path = os.path.abspath(".")

    path = os.path.join(base_path, relative_path)

    if not relative_path.startswith('patch_data') and not os.path.exists(path):
        logger.warning(f"Resource path not found: {path}")

    return path

def normalize_path(path):
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
    except Exception as e:
        logger.exception(f"Path normalization failed: {e}")
        return ""
