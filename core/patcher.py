"""
恶魔链接补丁工具 - 核心逻辑模块

提供ASAR文件操作和补丁应用的核心功能。
使用纯 Python ASAR 读写模块，不依赖第三方 asar 包。
"""

import logging
import os
import stat
from typing import Any, Callable, Optional, Tuple

from utils.asar_utils import check_asar_path_traversal
from utils.asar_writer import asar_extract, asar_pack, NATIVE_EXTENSIONS
from utils.constants import MAX_ASAR_SIZE, MIN_ASAR_SIZE
from utils.error_handler import PatcherError
from utils.file_ops import verify_directory_safe
from utils.paths import normalize_path
from utils.performance import get_performance_monitor
from utils.validators import validate_not_empty, validate_path

logger = logging.getLogger(__name__)


class CoreLogic:
    @staticmethod
    def remove_readonly_handler(func, path, excinfo):
        """删除只读属性的回调函数"""
        try:
            os.chmod(path, stat.S_IRUSR | stat.S_IWUSR)
            func(path)
        except Exception as e:
            logger.debug(f"Failed to remove readonly: {e}")

    @staticmethod
    def _validate_asar_integrity(asar_path: str) -> bool:
        """
        验证 ASAR 文件完整性，支持两种格式：
        - 官方 8 字节格式: [4字节 header_size][4字节 padding][JSON][文件数据]
        - 旧 16 字节格式: [4字节 data_size][4字节 header_size][4字节 header_object_size][4字节 header_string_size][JSON][文件数据]

        Args:
            asar_path: ASAR 文件路径

        Returns:
            bool: 验证是否通过
        """
        import json
        import struct

        try:
            with open(asar_path, "rb") as f:
                f.seek(0, os.SEEK_END)
                file_size = f.tell()
                if file_size < MIN_ASAR_SIZE:
                    logger.error(f"ASAR file too small: {file_size} bytes")
                    return False
                if file_size > MAX_ASAR_SIZE:
                    logger.error(f"ASAR file too large: {file_size} bytes")
                    return False

                f.seek(0)

                # Pickle format: [4B size_payload=4][4B header_buf_len][headerPickle...]
                size_buf = f.read(8)
                if len(size_buf) < 8:
                    logger.error("Cannot read ASAR size pickle")
                    return False

                size_payload = struct.unpack("<I", size_buf[0:4])[0]
                header_buf_len = struct.unpack("<I", size_buf[4:8])[0]
                if size_payload != 4 or header_buf_len == 0 or header_buf_len > MAX_ASAR_SIZE:
                    logger.error(f"Invalid ASAR size pickle: {size_payload}, {header_buf_len}")
                    return False

                # headerPickle: [4B payload_size][4B json_len][json bytes][padding]
                header_pickle = f.read(min(header_buf_len, 8))
                if len(header_pickle) < 8:
                    logger.error("Cannot read ASAR header pickle")
                    return False

                json_size = struct.unpack("<I", header_pickle[4:8])[0]
                if json_size == 0 or json_size > MAX_ASAR_SIZE:
                    logger.error(f"Invalid ASAR JSON size: {json_size}")
                    return False

                header_bytes = f.read(json_size)
                if len(header_bytes) != json_size:
                    logger.error(
                        f"ASAR header truncated: expected {json_size}, got {len(header_bytes)}"
                    )
                    return False

                try:
                    header_dict = json.loads(header_bytes.decode("utf-8"))
                except (UnicodeDecodeError, json.JSONDecodeError) as e:
                    logger.error(f"ASAR header JSON corrupted: {e}")
                    return False

                if "files" not in header_dict:
                    logger.error("ASAR header missing 'files' key")
                    return False

                return True

        except OSError as e:
            logger.error(f"Failed to read ASAR file: {e}")
            return False
        except Exception as e:
            logger.error(f"ASAR integrity validation failed: {e}")
            return False

    def __init__(self):
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
        unpacked_files: Optional[set] = None,
    ) -> Tuple[bool, Optional[Any]]:
        """
        执行ASAR操作（解包或打包）- 使用纯 Python 实现

        Args:
            action: 操作类型 ("extract" 或 "pack")
            src: 源文件/目录路径
            dest: 目标路径
            callback: 回调函数，用于更新进度
            unpack_pattern: 已弃用，保留参数兼容性（内部使用 NATIVE_EXTENSIONS）
            unpacked_files: 明确的 unpacked 文件集合，用于 pack 时保持原有 unpacked 状态

        Raises:
            PatcherError: 如果操作失败

        Returns:
            bool: 操作成功返回 True，失败则抛出异常
        """
        logger.info(f"Running ASAR {action} operation")

        src = normalize_path(src)
        dest = normalize_path(dest)

        if action == "extract" and not os.path.isfile(src):
            raise PatcherError(f"Source must be a file for extraction: {src}")

        monitor = get_performance_monitor()
        monitor.start(f"asar_{action}")

        try:
            if callback:
                callback(f"Executing: {action}...")

            if action == "extract":
                if callback:
                    callback("Validating ASAR file...")
                if not self._validate_asar_integrity(src):
                    raise PatcherError(
                        f"ASAR file validation failed: '{src}' is corrupted or invalid. "
                        f"Please restore from backup or verify game files in Steam."
                    )

                if not check_asar_path_traversal(src):
                    raise PatcherError(
                        f"Security violation: Path traversal detected in ASAR file '{src}'. "
                        f"Possible malicious ASAR file."
                    )

                unpacked_files, _ = asar_extract(src, dest, callback=callback)

                if not verify_directory_safe(dest):
                    raise PatcherError(
                        f"Security violation: ASAR extraction resulted in files "
                        f"outside target directory '{dest}'. Possible malicious ASAR file."
                    )

            elif action == "pack":
                asar_pack(
                    src,
                    dest,
                    unpack_extensions=NATIVE_EXTENSIONS,
                    callback=callback,
                    unpacked_files=unpacked_files,
                )

            else:
                raise PatcherError(f"Unknown ASAR action: {action}")

            logger.info(f"ASAR {action} completed successfully")
            if callback:
                callback("Asar operation success.")

            if action == "extract":
                return True, unpacked_files
            return True, None

        except Exception as e:
            logger.exception("ASAR operation failed")
            if isinstance(e, PatcherError):
                raise
            raise PatcherError(f"{type(e).__name__}: {e}") from e
        finally:
            elapsed = monitor.stop(f"asar_{action}")
            logger.debug(f"ASAR {action} operation took {elapsed:.3f}s")
