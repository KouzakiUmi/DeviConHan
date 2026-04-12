# -*- coding: utf-8 -*-
"""
恶魔链接补丁工具 - 核心逻辑模块

提供ASAR文件操作和补丁应用的核心功能。
包含性能监控集成，用于跟踪和优化操作性能。
"""

import os
import stat
import logging
from typing import Callable, Optional

from utils.paths import normalize_path
from utils.performance import get_performance_monitor
from utils.error_handler import (
    PatcherError,
)
from utils.validators import validate_path, validate_not_empty

logger = logging.getLogger(__name__)

# ================== 配置延迟加载 ==================
# 注意: 配置和语言初始化现在由 main.py 统一处理
# 避免在模块导入时执行可能依赖日志系统的初始化


# ================= 核心逻辑类 (Worker) =================
class CoreLogic:
    # 统一的 remove_readonly 方法
    @staticmethod
    def remove_readonly_handler(func, path, excinfo):
        """删除只读属性的回调函数（静态方法，可在类外复用）"""
        try:
            os.chmod(path, stat.S_IRUSR | stat.S_IWUSR)
            func(path)
        except Exception as e:
            logger.debug(f"Failed to remove readonly: {e}")

    def __init__(self):
        """
        初始化核心逻辑
        """
        try:
            import asar  # noqa: F401  # noqa: F401  # noqa: F401
        except ImportError:
            raise PatcherError(
                "Missing dependency: asar. Please install it using 'pip install asar'."
            )

        logger.info("CoreLogic initialized (Pure Python ASAR mode)")

    @validate_not_empty("action", "src", "dest")
    @validate_path("src", should_exist=True)
    def run_asar(
        self,
        action: str,
        src: str,
        dest: str,
        callback: Optional[Callable] = None,
        unpack_pattern: Optional[str] = None,
    ) -> bool:
        """
        执行ASAR操作（解包或打包）- 固定使用内置依赖库

        Args:
            action: 操作类型 ("extract" 或 "pack")
            src: 源文件/目录路径
            dest: 目标路径
            callback: 回调函数，用于更新进度
            unpack_pattern: 排除模式（仅打包时使用）

        Raises:
            PatcherFileNotFoundError: 如果源路径不存在
            PatcherError: 如果操作失败

        Returns:
            bool: 操作成功返回 True，失败则抛出异常
        """
        logger.info(f"Running ASAR {action} operation")

        src = normalize_path(src)
        dest = normalize_path(dest)

        if action == "extract" and not os.path.isfile(src):
            raise PatcherError(f"Source must be a file for extraction: {src}")

        if action == "pack" and not unpack_pattern:
            unpack_pattern = "*.{node,dll,so,dylib,exe,bin}"

        # 使用性能监控器记录ASAR操作
        monitor = get_performance_monitor()
        monitor.start(f"asar_{action}")

        try:
            import asar  # noqa: F401  # noqa: F401  # noqa: F401
            from pathlib import Path

            if callback:
                callback(f"Executing: {action}...")

            # 移除背景线程和 timeout_seconds
            # ASAR 是阻塞的 IO 操作，且因为没有安全的杀死线程的方式，
            # 强制超时终止不仅可能留下半成品的写文件，还引发过后台死锁。
            # 这里依赖上层的 AsyncOperationManager 提供对用户体验的线程分离即可。
            if action == "extract":
                asar.extract_archive(Path(src), Path(dest))

            elif action == "pack":
                asar.create_archive(Path(src), Path(dest), unpack=unpack_pattern or "")

            else:
                raise PatcherError(f"Unknown ASAR action: {action}")

            logger.info(f"ASAR {action} completed successfully")
            if callback:
                callback("Asar operation success.")
            return True

        except Exception as e:
            logger.exception("ASAR operation failed")
            if isinstance(e, PatcherError):
                raise
            raise PatcherError(str(e)) from e
        finally:
            # 记录ASAR操作耗时
            elapsed = monitor.stop(f"asar_{action}")
            logger.debug(f"ASAR {action} operation took {elapsed:.3f}s")
