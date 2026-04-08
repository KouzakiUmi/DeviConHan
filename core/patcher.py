# -*- coding: utf-8 -*-
"""
恶魔链接补丁工具 - 核心逻辑模块

提供ASAR文件操作和补丁应用的核心功能。
包含性能监控集成，用于跟踪和优化操作性能。
"""

import os
import sys
import subprocess
import stat
import logging

from utils.paths import get_resource_path, normalize_path
from utils.performance import get_performance_monitor
from utils.error_handler import (
    PatcherError,
    PatcherFileNotFoundError,
    NodeNotFoundError,
)
from utils.validators import validate_path, validate_not_empty
from core.config import get_config

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
            os.chmod(path, stat.S_IWRITE)
            func(path)
        except Exception as e:
            logger.debug(f"Failed to remove readonly: {e}")

    def __init__(self):
        """
        初始化核心逻辑

        Args:
            log_callback: 日志回调函数，用于GUI模式

        Raises:
            PatcherFileNotFoundError: 如果必要的资源文件不存在
        """
        self.node_path = get_resource_path(os.path.join("tools", "node.exe"))
        self.script_path = self._find_script()

        # 验证必要文件存在
        if not os.path.exists(self.node_path):
            raise PatcherFileNotFoundError(
                f"Node.js executable not found: {self.node_path}"
            )

        if not self.script_path or not os.path.exists(self.script_path):
            raise PatcherFileNotFoundError("Patcher script not found")

        # 从配置文件读取模式设置，默认使用内置工具
        self.mode = get_config().get("main", "ASAR_MODE", fallback="bundled")

        logger.info(f"CoreLogic initialized. Mode: {self.mode}")
        logger.debug(f"Node path: {self.node_path}")
        logger.debug(f"Script path: {self.script_path}")

    def _find_script(self):
        """
        查找 ASAR 命令行脚本

        Returns:
            脚本文件路径，未找到返回None
        """
        tools = get_resource_path("tools")
        candidates = [
            os.path.join(tools, "asar_cli.mjs"),  # 优先使用新的 CLI 工具
            os.path.join(tools, "bundled_asar", "index.mjs"),
            os.path.join(tools, "bundled_asar", "index.js"),
        ]

        for p in candidates:
            if os.path.exists(p):
                logger.debug(f"Found script: {p}")
                return p

        logger.warning("No ASAR script found")
        return None

    @validate_not_empty("action", "src", "dest")
    @validate_path("src", should_exist=True)
    def run_asar(self, action, src, dest, callback=None, unpack_pattern=None):
        """
        执行ASAR操作（解包或打包）- 固定使用内置依赖库

        Args:
            action: 操作类型 ("extract" 或 "pack")
            src: 源文件/目录路径
            dest: 目标路径
            callback: 回调函数，用于更新进度
            unpack_pattern: 排除模式（仅打包时使用）

        Raises:
            NodeNotFoundError: 如果Node.js未找到
            PatcherFileNotFoundError: 如果源路径不存在
            PatcherError: 如果操作失败或超时

        Returns:
            bool: 操作成功返回 True，失败则抛出异常
        """
        logger.info(f"Running ASAR {action} operation")

        # 验证输入参数
        src = normalize_path(src)
        dest = normalize_path(dest)

        if not src or not os.path.exists(src):
            raise PatcherFileNotFoundError(f"Source path does not exist: {src}")

        if action == "extract" and not os.path.isfile(src):
            raise PatcherError(f"Source must be a file for extraction: {src}")

        # 设置默认排除模式
        if not unpack_pattern:
            unpack_pattern = "*.{node,dll,so,dylib,exe,bin}"

        # 使用性能监控器记录ASAR操作
        monitor = get_performance_monitor()
        monitor.start(f"asar_{action}")

        from utils.constants import DEFAULT_ASAR_TIMEOUT_SECONDS

        # 初始化超时值，防止在异常处理中未定义
        timeout_seconds = get_config().get_int(
            "main", "ASAR_OPERATION_TIMEOUT", fallback=DEFAULT_ASAR_TIMEOUT_SECONDS
        )

        try:
            # 固定使用内置工具
            cmd = [self.node_path, self.script_path, action, src, dest]
            if action == "pack":
                cmd.extend(["--unpack", unpack_pattern])

            logger.debug(f"Using bundled Node.js: {self.node_path}")
            logger.debug(f"Command: {' '.join(cmd)}")

            # 确保所有命令参数都是字符串，防止类型问题
            cmd = [str(arg) if not isinstance(arg, str) else arg for arg in cmd]

            # 执行命令
            if callback:
                callback(f"Executing: {action}...")

            creationflags = 0
            if sys.platform.startswith("win"):
                creationflags = subprocess.CREATE_NO_WINDOW

            # 使用 Popen 实时读取输出，避免缓冲区溢出
            proc = subprocess.Popen(
                cmd,
                shell=False,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding="utf-8",
                errors="backslashreplace",
                creationflags=creationflags,
            )

            stdout_lines = []

            def read_output():
                if proc.stdout:
                    for line in iter(proc.stdout.readline, ""):
                        stripped_line = line.rstrip()
                        stdout_lines.append(stripped_line)
                        logger.debug(f"ASAR: {stripped_line}")

            import threading

            reader_thread = threading.Thread(target=read_output, daemon=True)
            reader_thread.start()

            # 等待进程完成并检查超时
            try:
                returncode = proc.wait(timeout=timeout_seconds)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait()
                raise
            finally:
                reader_thread.join(timeout=1.0)

            stdout_output = "\n".join(stdout_lines)

            if returncode != 0:
                error_msg = f"ASAR {action} failed with code {returncode}"
                if stdout_output:
                    logger.error(f"Output: {stdout_output}")
                raise PatcherError(error_msg)

            logger.info(f"ASAR {action} completed successfully")
            if callback:
                callback("Asar operation success.")
            return True

        except subprocess.TimeoutExpired:
            error_msg = f"ASAR {action} timed out after {timeout_seconds} seconds"
            logger.error(error_msg)
            raise PatcherError(error_msg)

        except Exception as e:
            logger.exception(f"ASAR operation failed: {e}")
            if isinstance(e, (NodeNotFoundError, PatcherFileNotFoundError)):
                raise
            raise PatcherError(str(e))
        finally:
            # 记录ASAR操作耗时
            elapsed = monitor.stop(f"asar_{action}")
            logger.debug(f"ASAR {action} operation took {elapsed:.3f}s")
