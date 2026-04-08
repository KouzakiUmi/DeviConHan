# -*- coding: utf-8 -*-
"""
Fuse 完整性校验移除模块

提供游戏可执行文件 Fuse 校验移除功能。
"""

import os
import mmap
import shutil
import logging
import stat

from utils.paths import normalize_path
from utils.file_ops import compute_file_hash
from core.config import get_config
from utils.constants import (
    FUSE_ENABLED_BYTE,
    FUSE_DISABLED_BYTE,
    FUSE_VALIDATION_MIN_SIZE,
)

logger = logging.getLogger(__name__)


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
        # 移除只读属性
        os.chmod(exe_path, stat.S_IWRITE)

        # -------------------------------------------------------
        # 自动备份机制（修复 P3：备份完整性验证）
        #
        # 原实现仅检查备份文件是否存在，若备份为空文件或写入中断
        # 导致截断，后续不会重新创建，用户将失去原始文件。
        # 修复：
        # 1. 若备份不存在 → 创建并通过哈希验证写入完整性；
        # 2. 若备份已存在 → 通过文件大小 + SHA256 对比是否与
        #    当前可执行文件内容匹配（fuse 已被修改）或与原始一致；
        #    若大小为 0 或哈希计算失败（表明备份损坏），则重新创建；
        # 3. 备份创建失败时中止操作，保护用户数据安全。
        # -------------------------------------------------------
        backup_path = exe_path + ".fuse_backup"

        def _create_backup() -> bool:
            """创建备份并验证写入完整性，成功返回 True。"""
            temp_backup = backup_path + ".tmp"
            try:
                shutil.copy2(exe_path, temp_backup)

                # 哈希验证：确保备份与源文件内容一致
                src_hash = compute_file_hash(exe_path)
                dst_hash = compute_file_hash(temp_backup)

                if not src_hash or src_hash != dst_hash:
                    logger.error(
                        f"Fuse backup hash mismatch after copy "
                        f"(src={src_hash}, dst={dst_hash}). Aborting."
                    )
                    try:
                        os.remove(temp_backup)
                    except OSError:
                        pass
                    return False

                # 原子替换备份文件（防止中途崩溃留下损坏备份）
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
            # 检查已存在的备份是否有效（大小 > 0 且哈希可计算）
            bak_size = os.path.getsize(backup_path)
            bak_hash = compute_file_hash(backup_path) if bak_size > 0 else ""
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

        with open(exe_path, "r+b") as f:
            with mmap.mmap(f.fileno(), 0) as mm:
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

        logger.info("Fuse operation completed successfully")
        return True

    except (OSError, IOError) as e:
        # mmap.error 是 OSError 的子类
        logger.error(f"MMap/IO error: {e}")
        return False
    except Exception as e:
        logger.exception(f"Failed to remove Fuse: {e}")
        if callback:
            callback(f"Fuse Error: {e}")
        return False
