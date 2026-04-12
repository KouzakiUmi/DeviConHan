# -*- coding: utf-8 -*-
"""
Fuse 完整性校验移除模块

提供游戏可执行文件 Fuse 校验移除功能。
"""

import os
import mmap
import shutil
import hashlib
import logging
import stat

from utils.paths import normalize_path
from core.config import get_config
from utils.constants import (
    FUSE_ENABLED_BYTE,
    FUSE_DISABLED_BYTE,
    FUSE_VALIDATION_MIN_SIZE,
)

logger = logging.getLogger(__name__)


def _partial_hash(
    file_path: str, head_size: int = 1024 * 1024, tail_size: int = 1024 * 1024
) -> str:
    """
    计算文件首尾各 head_size/tail_size 字节的 SHA256 + 文件总大小。

    对于 80-150MB 的 Electron 可执行文件，全量 SHA256 需要 5-15 秒；
    而首尾各 1MB 的组合哈希 + 文件大小校验足以检测 copy2 的写入错误，
    耗时仅需约 0.1 秒。
    """
    try:
        file_size = os.path.getsize(file_path)
        sha256 = hashlib.sha256()
        sha256.update(str(file_size).encode("ascii"))
        with open(file_path, "rb") as f:
            data = f.read(min(head_size, file_size))
            sha256.update(data)
            if file_size > tail_size:
                f.seek(file_size - tail_size)
                data = f.read(tail_size)
                sha256.update(data)
        return sha256.hexdigest()
    except Exception as e:
        logger.debug(f"Partial hash failed for {file_path}: {e}")
        return ""


def remove_fuse(exe_path, callback=None):
    """
    移除游戏可执行文件的Fuse完整性校验

    Args:
        exe_path: 游戏可执行文件路径
        callback: 回调函数

    Returns:
        bool: 是否成功移除Fuse
    """
    logger.info(f"Attempting to remove Fuse from: {exe_path}")

    # 验证输入参数
    try:
        if not exe_path or not isinstance(exe_path, str):
            logger.warning("Invalid executable path")
            return False

        exe_path = normalize_path(exe_path)

        if not os.path.exists(exe_path):
            logger.error(f"Executable file does not exist: {exe_path}")
            return False

        if not os.path.isfile(exe_path):
            logger.error(f"Not a file: {exe_path}")
            return False

        # 检查文件大小
        file_size = os.path.getsize(exe_path)
        if file_size < FUSE_VALIDATION_MIN_SIZE:
            logger.warning(f"File too small to contain Fuse data: {file_size} bytes")
            return False

    except Exception as e:
        logger.error(f"Failed to validate executable path: {e}")
        return False

    try:
        os.chmod(exe_path, os.stat(exe_path).st_mode | stat.S_IRUSR | stat.S_IWUSR)

        backup_path = exe_path + ".fuse_backup"

        def _create_backup() -> bool:
            """创建备份并验证写入完整性，成功返回 True。"""
            temp_backup = backup_path + ".tmp"
            try:
                shutil.copy2(exe_path, temp_backup)

                src_hash = _partial_hash(exe_path)
                dst_hash = _partial_hash(temp_backup)

                if not src_hash or src_hash != dst_hash:
                    logger.error(
                        f"Fuse backup verification mismatch after copy "
                        f"(src={src_hash}, dst={dst_hash}). Aborting."
                    )
                    try:
                        os.remove(temp_backup)
                    except OSError:
                        pass
                    return False

                os.replace(temp_backup, backup_path)
                logger.info(
                    f"Created verified Fuse backup at: {backup_path} (hash={src_hash[:12]}...)"
                )
                return True
            except Exception as backup_e:
                logger.error(f"Failed to create Fuse backup: {backup_e}")
                try:
                    if os.path.exists(temp_backup):
                        os.remove(temp_backup)
                except OSError:
                    pass
                return False

        need_backup = True
        if os.path.exists(backup_path):
            bak_size = os.path.getsize(backup_path)
            bak_hash = _partial_hash(backup_path) if bak_size > 0 else ""
            if bak_size > 0 and bak_hash:
                need_backup = False
                logger.debug(
                    f"Existing Fuse backup verified (size={bak_size}, "
                    f"hash={bak_hash[:12]}...)"
                )
            else:
                logger.warning(
                    f"Existing Fuse backup is corrupted (size={bak_size}), "
                    f"recreating..."
                )

        if need_backup:
            if not _create_backup():
                if callback:
                    callback("Failed to create Fuse backup. Aborting.")
                return False
            if callback:
                callback(f"Backup created: {os.path.basename(backup_path)}")

        # 获取Fuse配置
        fuse_sentinel = get_config().fuse_sentinel
        header_len = get_config().fuse_wire_header_length
        integrity_offset = get_config().fuse_asar_integrity_offset

        with open(exe_path, "r+b") as f, mmap.mmap(f.fileno(), 0) as mm:
            offset = mm.find(fuse_sentinel)

            if offset == -1:
                logger.info(
                    "Fuse sentinel not found - already removed or never present"
                )
                return False

            # 计算目标偏移量
            target = offset + header_len + integrity_offset

            # 边界检查（确保target + 1在文件范围内）
            if target + 1 > mm.size():
                logger.error(
                    f"Target position {target} (+1 byte) exceeds file size {mm.size()}"
                )
                return False

            current_byte = mm[target : target + 1]

            if current_byte == FUSE_ENABLED_BYTE:
                mm[target : target + 1] = FUSE_DISABLED_BYTE
                logger.info("Fuse checksum byte modified (0x31 -> 0x30)")
                if callback:
                    callback("Fuse removed.")
                return True
            elif current_byte == FUSE_DISABLED_BYTE:
                logger.info("Fuse already disabled")
                if callback:
                    callback("Fuse already disabled.")
                return True
            else:
                logger.warning(
                    f"Unexpected byte at target position: {current_byte}"
                )
                return False


    except (OSError, IOError) as e:
        # mmap.error 是 OSError 的子类
        logger.error(f"MMap/IO error: {e}")
        return False
    except Exception as e:
        logger.exception(f"Failed to remove Fuse: {e}")
        if callback:
            callback(f"Fuse Error: {e}")
        return False
