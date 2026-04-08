# -*- coding: utf-8 -*-
"""
工具函数模块 - 通用清理功能

提供临时目录强制清理等通用工具函数。
"""

import os
import shutil
import stat
import logging
import time
import subprocess
import sys
from typing import Callable, Any

logger = logging.getLogger(__name__)


def retry_operation(operation: Callable[[], Any], max_retries: int = 3, delay: float = 0.5, operation_name: str = "operation") -> bool:
    """
    重试一个可能失败的操作

    Args:
        operation: 要执行的函数
        max_retries: 最大重试次数
        delay: 重试之间的延迟（秒）
        operation_name: 操作名称（用于日志记录）

    Returns:
        bool: 操作是否最终成功
    """
    for attempt in range(1, max_retries + 1):
        try:
            result = operation()
            # 如果操作返回 False，认为是失败
            if result is False:
                logger.warning(f"{operation_name} returned False, attempt {attempt}/{max_retries}")
                if attempt < max_retries:
                    time.sleep(delay)
                continue
            return True
        except Exception as e:
            logger.warning(f"{operation_name} failed on attempt {attempt}/{max_retries}: {e}")
            if attempt < max_retries:
                time.sleep(delay)
            else:
                logger.error(f"{operation_name} failed after {max_retries} attempts")
                return False
    return False


def force_cleanup_dir(temp_dir: str, max_retries: int = 3) -> bool:
    """
    强制清理临时目录（处理只读文件和目录）

    Args:
        temp_dir: 临时目录路径
        max_retries: 最大重试次数

    Returns:
        bool: 是否成功清理
    """
    if not os.path.exists(temp_dir):
        logger.debug(f"Temp directory already removed: {temp_dir}")
        return True

    # 1. 修改所有文件和目录的只读属性
    def chmod_recursive():
        for root, dirs, files in os.walk(temp_dir):
            for name in files:
                try:
                    os.chmod(os.path.join(root, name), stat.S_IWRITE | stat.S_IRUSR)
                except Exception:
                    pass
            for name in dirs:
                try:
                    os.chmod(os.path.join(root, name), stat.S_IWRITE | stat.S_IRUSR)
                except Exception:
                    pass

    # 2. 尝试使用 shutil.rmtree
    def rmtree_attempt():
        shutil.rmtree(temp_dir, ignore_errors=True)
        return not os.path.exists(temp_dir)

    # 3. 手动逐个删除（如果 rmtree 失败）
    def manual_delete_attempt():
        if not os.path.exists(temp_dir):
            return True
        for root, dirs, files in os.walk(temp_dir, topdown=False):
            for name in files:
                try:
                    os.remove(os.path.join(root, name))
                except Exception:
                    pass
            for name in dirs:
                try:
                    os.rmdir(os.path.join(root, name))
                except Exception:
                    pass
        try:
            os.rmdir(temp_dir)
        except Exception:
            pass
        return not os.path.exists(temp_dir)

    # 组合操作：chmod -> rmtree -> manual_delete
    def full_cleanup():
        chmod_recursive()
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir, ignore_errors=True)

        if os.path.exists(temp_dir):
            manual_delete_attempt()

        if os.path.exists(temp_dir) and sys.platform.startswith("win"):
            try:
                creationflags = subprocess.CREATE_NO_WINDOW
                subprocess.run(['cmd', '/c', 'rmdir', '/s', '/q', temp_dir], capture_output=True, timeout=5, creationflags=creationflags)
            except Exception as e:
                logger.warning(f"System force cleanup failed: {e}")

        return not os.path.exists(temp_dir)

    return retry_operation(full_cleanup, max_retries=max_retries, delay=0.5, operation_name=f"Cleanup {temp_dir}")
