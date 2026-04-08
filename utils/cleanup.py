# -*- coding: utf-8 -*-
"""
工具函数模块 - 通用清理功能

提供临时目录强制清理等通用工具函数。
"""

__all__ = [
    "retry_operation",
    "force_cleanup_dir",
    "TempDirectoryManager",
    "schedule_delayed_cleanup",
]

import os
import shutil
import stat
import logging
import time
import subprocess
import sys
import threading
import tempfile
from typing import Callable, Any, Optional
from contextlib import contextmanager
from utils.constants import (
    MAX_CLEANUP_RETRIES,
    DEFAULT_CLEANUP_RETRY_DELAY as CLEANUP_RETRY_DELAY,
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


class TempDirectoryManager:
    """
    临时目录上下文管理器

    提供安全的临时目录创建和自动清理。
    支持重试机制和延迟清理，确保目录最终能被删除。

    用法：
        with TempDirectoryManager(prefix="patch_") as temp_dir:
            # 使用 temp_dir
            pass
        # 自动清理

        # 或保留目录：
        with TempDirectoryManager(prefix="debug_") as temp_dir:
            manager.keep()
    """

    def __init__(
        self,
        prefix: str = "temp_",
        suffix: str = "",
        parent_dir: Optional[str] = None,
        cleanup_on_exit: bool = True,
    ):
        """
        初始化临时目录管理器

        Args:
            prefix: 目录名前缀
            suffix: 目录名后缀
            parent_dir: 父目录，None则使用系统临时目录
            cleanup_on_exit: 退出时是否清理
        """
        self.prefix = prefix
        self.suffix = suffix
        self.parent_dir = parent_dir
        self._cleanup_on_exit = cleanup_on_exit
        self._temp_dir: Optional[str] = None
        self._lock = threading.Lock()

    def __enter__(self) -> str:
        """进入上下文，创建临时目录"""
        self._temp_dir = tempfile.mkdtemp(
            prefix=self.prefix, suffix=self.suffix, dir=self.parent_dir
        )
        logger.debug(f"Created temp directory: {self._temp_dir}")
        return self._temp_dir

    def __exit__(self, exc_type, exc_val, exc_tb):
        """退出上下文，清理临时目录"""
        if self._cleanup_on_exit and self._temp_dir:
            with self._lock:
                temp_dir = self._temp_dir
                # delay_seconds=0 时直接同步清理，避免为 0 延迟创建不必要的线程；
                # 若需要非阻塞延迟清理，调用 schedule_delayed_cleanup 并指定正延迟值。
                force_cleanup_dir(temp_dir)

    def keep(self) -> None:
        """保留临时目录，退出时不清理"""
        with self._lock:
            self._cleanup_on_exit = False
            logger.debug(f"Temp directory will be kept: {self._temp_dir}")

    def get_path(self) -> Optional[str]:
        """获取临时目录路径"""
        return self._temp_dir

    def cleanup_now(self) -> bool:
        """立即清理临时目录（用于手动触发）"""
        if not self._temp_dir:
            return True

        with self._lock:
            success = force_cleanup_dir(self._temp_dir)
            if success:
                self._temp_dir = None
            return success


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


@contextmanager
def temp_directory(
    prefix: str = "temp_", suffix: str = "", parent_dir: Optional[str] = None
):
    """
    临时目录上下文管理器（函数式接口）

    用法：
        with temp_directory(prefix="patch_") as temp_dir:
            # 使用 temp_dir
            pass
        # 自动清理
    """
    manager = TempDirectoryManager(prefix, suffix, parent_dir)
    try:
        yield manager.__enter__()
    finally:
        manager.__exit__(None, None, None)
