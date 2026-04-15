"""
Fuse 完整性校验移除模块

提供游戏可执行文件 Fuse 校验移除功能。

改进点：
1. mmap修改后强制flush
2. 修改后验证
3. 恢复原始功能
4. 完整文件哈希校验
"""

__all__ = ["remove_fuse", "restore_fuse", "verify_fuse_backup", "FuseError"]

import hashlib
import logging
import mmap
import os
import shutil
import stat
from typing import Callable, Optional, Tuple

from core.config import get_config
from utils.constants import (
    FUSE_DISABLED_BYTE,
    FUSE_ENABLED_BYTE,
    FUSE_PARTIAL_HASH_HEAD_SIZE,
    FUSE_PARTIAL_HASH_TAIL_SIZE,
    FUSE_VALIDATION_MIN_SIZE,
)
from utils.paths import normalize_path

logger = logging.getLogger(__name__)


class FuseError(Exception):
    """Fuse操作错误"""

    pass


def _compute_full_hash(file_path: str, chunk_size: int = 1024 * 1024) -> str:
    """
    计算文件的完整 SHA256 哈希

    Args:
        file_path: 文件路径
        chunk_size: 分块大小（默认1MB）

    Returns:
        str: 哈希值，失败返回空字符串
    """
    try:
        sha256 = hashlib.sha256()
        with open(file_path, "rb") as f:
            while True:
                chunk = f.read(chunk_size)
                if not chunk:
                    break
                sha256.update(chunk)
        return sha256.hexdigest()
    except Exception as e:
        logger.error(f"Full hash failed for {file_path}: {e}")
        return ""


def _partial_hash(
    file_path: str,
    head_size: int = FUSE_PARTIAL_HASH_HEAD_SIZE,
    tail_size: int = FUSE_PARTIAL_HASH_TAIL_SIZE,
) -> str:
    """
    计算文件首尾各 head_size/tail_size 字节的 SHA256 + 文件总大小。

    用于快速验证备份完整性，完整哈希请使用 _compute_full_hash。
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


def _verify_backup_with_full_hash(exe_path: str, backup_path: str) -> bool:
    """
    使用完整哈希验证备份完整性

    Args:
        exe_path: 原始文件路径
        backup_path: 备份文件路径

    Returns:
        bool: 是否验证通过
    """
    logger.info("Verifying backup with full hash (this may take a moment)...")

    src_hash = _compute_full_hash(exe_path)
    dst_hash = _compute_full_hash(backup_path)

    if not src_hash or not dst_hash:
        logger.error("Failed to compute full hash")
        return False

    if src_hash != dst_hash:
        logger.error(f"Full hash mismatch! src={src_hash[:16]}..., dst={dst_hash[:16]}...")
        return False

    logger.info("Full hash verification passed")
    return True


def verify_fuse_backup(exe_path: str, use_full_hash: bool = False) -> Tuple[bool, str]:
    """
    验证Fuse备份是否可用

    注意：此方法不再与当前exe_path进行对比，而是通过检查备份文件本身是否包含
    完整的Fuse哨兵和对应的校验位来判断其是否为合法的原始备份文件。

    Args:
        exe_path: 原始可执行文件路径
        use_full_hash: 保留参数以兼容现有接口，实际上不再用于与被修改的文件比对

    Returns:
        Tuple[bool, str]: (是否可用, 备份路径或错误消息)
    """
    exe_path = normalize_path(exe_path)
    backup_path = exe_path + ".fuse_backup"

    if not os.path.exists(backup_path):
        return False, "Backup not found"

    try:
        file_size = os.path.getsize(backup_path)
        if file_size < FUSE_VALIDATION_MIN_SIZE:
            return False, f"Backup file too small: {file_size} bytes"

        fuse_sentinel = get_config().fuse_sentinel
        header_len = get_config().fuse_wire_header_length
        integrity_offset = get_config().fuse_asar_integrity_offset

        with open(backup_path, "rb") as f:
            with mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ) as mm:
                offset = mm.find(fuse_sentinel)
                if offset == -1:
                    return False, "Fuse sentinel not found in backup file"

                target = offset + header_len + integrity_offset
                if target + 1 > mm.size():
                    return False, "Backup corrupted: sentinel position near EOF"

                verify_byte = mm[target : target + 1]
                if verify_byte != FUSE_ENABLED_BYTE:
                    return (
                        False,
                        f"Backup does not contain original fuse byte, found {verify_byte}",
                    )

        return True, backup_path
    except Exception as e:
        logger.error(f"Failed to verify backup: {e}")
        return False, f"Verification failed: {e}"


def restore_fuse(exe_path: str, callback: Optional[Callable] = None) -> bool:
    """
    恢复原始的Fuse状态（从备份恢复）

    Args:
        exe_path: 可执行文件路径
        callback: 回调函数

    Returns:
        bool: 是否成功恢复
    """
    logger.info(f"Attempting to restore Fuse backup for: {exe_path}")

    try:
        exe_path = normalize_path(exe_path)
        backup_path = exe_path + ".fuse_backup"

        if not os.path.exists(backup_path):
            msg = "Fuse backup not found, cannot restore"
            logger.error(msg)
            if callback:
                callback(msg)
            return False

        # 验证备份完整性
        ok, reason = verify_fuse_backup(exe_path, use_full_hash=True)
        if not ok:
            logger.error(f"Backup verification failed: {reason}")
            if callback:
                callback(f"Backup verification failed: {reason}")
            return False

        # 恢复备份
        logger.info(f"Restoring from {backup_path}")
        shutil.copy2(backup_path, exe_path)

        # 验证恢复结果
        if _verify_backup_with_full_hash(exe_path, backup_path):
            logger.info("Fuse restored successfully")
            if callback:
                callback("Fuse restored successfully.")
            return True
        else:
            logger.error("Restore verification failed")
            if callback:
                callback("Restore verification failed!")
            return False

    except Exception as e:
        logger.exception(f"Failed to restore Fuse: {e}")
        if callback:
            callback(f"Restore error: {e}")
        return False


def remove_fuse(exe_path, callback=None):
    """
    移除游戏可执行文件的Fuse完整性校验（改进版）

    改进点：
    1. mmap修改后强制flush
    2. 修改后重新读取验证
    3. 完整的文件哈希验证
    4. 失败自动回滚

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

    # 修改前创建临时备份（用于回滚）
    temp_backup = exe_path + ".fuse_temp"

    try:
        # 确保文件可写
        os.chmod(exe_path, os.stat(exe_path).st_mode | stat.S_IRUSR | stat.S_IWUSR)

        # 创建临时备份
        shutil.copy2(exe_path, temp_backup)

        backup_path = exe_path + ".fuse_backup"

        def _create_backup() -> bool:
            """创建备份并验证写入完整性，成功返回 True。"""
            temp_bak = backup_path + ".tmp"
            try:
                shutil.copy2(exe_path, temp_bak)

                # 使用完整哈希验证
                if not _verify_backup_with_full_hash(exe_path, temp_bak):
                    logger.error("Backup verification failed")
                    try:
                        os.remove(temp_bak)
                    except OSError:
                        pass
                    return False

                os.replace(temp_bak, backup_path)
                logger.info(f"Created verified Fuse backup at: {backup_path}")
                return True
            except Exception as backup_e:
                logger.error(f"Failed to create Fuse backup: {backup_e}")
                try:
                    if os.path.exists(temp_bak):
                        os.remove(temp_bak)
                except OSError:
                    pass
                return False

        need_backup = True
        if os.path.exists(backup_path):
            ok, reason = verify_fuse_backup(exe_path, use_full_hash=False)
            if ok:
                need_backup = False
                logger.debug(f"Existing Fuse backup verified: {backup_path}")
            else:
                logger.warning(f"Existing backup corrupted, recreating: {reason}")

        if need_backup:
            if not _create_backup():
                if callback:
                    callback("Failed to create Fuse backup. Aborting.")
                # 清理临时备份
                if os.path.exists(temp_backup):
                    os.remove(temp_backup)
                return False
            if callback:
                callback(f"Backup created: {os.path.basename(backup_path)}")

        # 获取Fuse配置
        fuse_sentinel = get_config().fuse_sentinel
        header_len = get_config().fuse_wire_header_length
        integrity_offset = get_config().fuse_asar_integrity_offset

        # 使用mmap修改文件
        with open(exe_path, "r+b") as f:
            # 获取文件大小用于mmap
            file_size = os.path.getsize(exe_path)

            with mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_WRITE) as mm:
                offset = mm.find(fuse_sentinel)

                if offset == -1:
                    logger.info("Fuse sentinel not found - already removed or never present")
                    return False

                # 计算目标偏移量
                target = offset + header_len + integrity_offset

                # 边界检查
                if target + 1 > mm.size():
                    logger.error(f"Target position {target} exceeds file size {mm.size()}")
                    return False

                current_byte = mm[target : target + 1]

                if current_byte == FUSE_ENABLED_BYTE:
                    # 执行修改
                    mm[target : target + 1] = FUSE_DISABLED_BYTE

                    # 关键：强制flush到磁盘
                    mm.flush()

                    # 验证修改
                    mm.seek(target)
                    verify_byte = mm.read(1)
                    if verify_byte != FUSE_DISABLED_BYTE:
                        logger.error(
                            f"Verification failed after modification: expected {FUSE_DISABLED_BYTE}, got {verify_byte}"
                        )
                        raise FuseError("Modification verification failed")

                    logger.info("Fuse checksum byte modified (0x31 -> 0x30) and verified")
                    if callback:
                        callback("Fuse removed and verified.")

                elif current_byte == FUSE_DISABLED_BYTE:
                    logger.info("Fuse already disabled")
                    if callback:
                        callback("Fuse already disabled.")
                    return True
                else:
                    logger.warning(f"Unexpected byte at target position: {current_byte}")
                    return False

        # 最终验证：重新打开文件检查
        with open(exe_path, "rb") as f:
            with mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ) as mm:
                offset = mm.find(fuse_sentinel)
                if offset != -1:
                    target = offset + header_len + integrity_offset
                    final_byte = mm[target : target + 1]
                    if final_byte == FUSE_DISABLED_BYTE:
                        logger.info("Final verification passed")
                        return True
                    else:
                        logger.error(f"Final verification failed: {final_byte}")
                        raise FuseError("Final verification failed")
                else:
                    logger.warning("Sentinel not found in final verification")
                    return False

    except FuseError as e:
        logger.error(f"Fuse operation failed: {e}")
        if callback:
            callback(f"Fuse Error: {e}")
        # 尝试回滚
        _rollback_fuse(exe_path, temp_backup)
        return False
    except OSError as e:
        logger.error(f"MMap/IO error: {e}")
        if callback:
            callback(f"IO Error: {e}")
        _rollback_fuse(exe_path, temp_backup)
        return False
    except Exception as e:
        logger.exception(f"Failed to remove Fuse: {e}")
        if callback:
            callback(f"Fuse Error: {e}")
        _rollback_fuse(exe_path, temp_backup)
        return False
    finally:
        # 清理临时备份
        if os.path.exists(temp_backup):
            try:
                os.remove(temp_backup)
            except OSError:
                pass


def _rollback_fuse(exe_path: str, temp_backup: str) -> None:
    """
    回滚Fuse修改

    Args:
        exe_path: 可执行文件路径
        temp_backup: 临时备份路径
    """
    logger.warning("Attempting to rollback Fuse modification...")

    try:
        if os.path.exists(temp_backup):
            shutil.copy2(temp_backup, exe_path)
            logger.info("Rollback successful")
        else:
            logger.error("Cannot rollback: temp backup not found")
    except Exception as e:
        logger.error(f"Rollback failed: {e}")
