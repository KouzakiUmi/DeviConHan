"""
工具函数模块 - 通用清理功能

提供临时目录强制清理等通用工具函数。
"""

__all__ = [
    "retry_operation",
    "force_cleanup_dir",
    "schedule_delayed_cleanup",
]

import logging
import os
import shutil
import stat
import subprocess
import sys
import threading
import time
from typing import Any, Callable

from utils.constants import (
    DEFAULT_CLEANUP_RETRY_DELAY as CLEANUP_RETRY_DELAY,
)
from utils.constants import (
    DELAYED_CLEANUP_DELAY,
)

logger = logging.getLogger(__name__)

# ================= 清理模块常量 =================
# MAX_CLEANUP_RETRIES, CLEANUP_RETRY_DELAY, DELAYED_CLEANUP_DELAY
# 现已从 utils.constants 统一导入，避免重复定义。
FORCE_CLOSE_HANDLE_TIMEOUT: float = 2.0  # 秒


def retry_operation(
    operation: Callable[[], Any],
    max_retries: int = 3,
    delay: float = 0.5,
    operation_name: str = "operation",
) -> bool:
    """
    重试一个可能失败的操作

    Args:
        operation: 要执行的函数
        max_retries: 最大重试次数（必须 >= 1，否则直接返回 False）
        delay: 重试之间的延迟（秒）
        operation_name: 操作名称（用于日志记录）

    Returns:
        bool: 操作是否最终成功
    """
    if max_retries < 1:
        logger.warning(f"{operation_name}: max_retries={max_retries} < 1, skipping")
        return False

    for attempt in range(1, max_retries + 1):
        try:
            result = operation()
            # 如果操作返回 False，认为是失败
            if result is False:
                logger.warning(
                    f"{operation_name} returned False, attempt {attempt}/{max_retries}"
                )
                if attempt < max_retries:
                    time.sleep(delay)
                continue
            return True
        except Exception as e:
            logger.warning(
                f"{operation_name} failed on attempt {attempt}/{max_retries}: {e}"
            )
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
                subprocess.run(
                    ["cmd", "/c", "rmdir", "/s", "/q", temp_dir],
                    capture_output=True,
                    timeout=5,
                    creationflags=creationflags,
                )
            except Exception as e:
                logger.warning(f"System force cleanup failed: {e}")

        return not os.path.exists(temp_dir)

    return retry_operation(
        full_cleanup,
        max_retries=max_retries,
        delay=CLEANUP_RETRY_DELAY,
        operation_name=f"Cleanup {temp_dir}",
    )


def schedule_delayed_cleanup(
    dir_path: str, delay_seconds: int = DELAYED_CLEANUP_DELAY
) -> None:
    """
    安排延迟清理

    在后台线程中等待一段时间后尝试清理目录。
    用于处理文件句柄可能仍被占用的情况。

    Args:
        dir_path: 要清理的目录路径
        delay_seconds: 延迟时间（秒）
    """

    def delayed_cleanup():
        time.sleep(delay_seconds)
        try:
            if os.path.exists(dir_path):
                success = force_cleanup_dir(dir_path)
                if success:
                    logger.info(f"Delayed cleanup completed: {dir_path}")
                else:
                    logger.warning(f"Delayed cleanup failed: {dir_path}")
        except Exception as e:
            logger.error(f"Delayed cleanup error: {e}")

    thread = threading.Thread(target=delayed_cleanup, daemon=True)
    thread.start()
    logger.debug(f"Scheduled delayed cleanup for: {dir_path} (in {delay_seconds}s)")
