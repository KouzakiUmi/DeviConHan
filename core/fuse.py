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
                        f"Backup does not contain original fuse byte, found {verify_byte!r}",
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

        # 恢复备份（先写临时文件，再原子替换）
        logger.info(f"Restoring from {backup_path}")
        temp_restore_path = exe_path + ".restore_tmp"
        if os.path.exists(temp_restore_path):
            os.remove(temp_restore_path)
        try:
            shutil.copy2(backup_path, temp_restore_path)
            if not _verify_backup_with_full_hash(temp_restore_path, backup_path):
                logger.error("Restore temp file verification failed")
                if callback:
                    callback("Restore verification failed!")
                return False

            os.replace(temp_restore_path, exe_path)
        finally:
            if os.path.exists(temp_restore_path):
                try:
                    os.remove(temp_restore_path)
                except OSError:
                    pass

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


def remove_fuse(exe_path: str, callback: Optional[Callable] = None) -> bool:
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

    exe_path = _validate_fuse_input(exe_path)
    if exe_path is None:
        return False

    temp_backup = exe_path + ".fuse_temp"

    try:
        os.chmod(exe_path, os.stat(exe_path).st_mode | stat.S_IRUSR | stat.S_IWUSR)
        shutil.copy2(exe_path, temp_backup)

        if not _ensure_fuse_backup(exe_path, callback):
            _cleanup_temp_backup(temp_backup)
            return False

        modify_result = _modify_fuse_byte(exe_path, callback)
        if modify_result is None:
            return False
        if modify_result is True and callback:
            return True

        if not _verify_fuse_final(exe_path):
            raise FuseError("Final verification failed")

        logger.info("Final verification passed")
        return True

    except FuseError as e:
        logger.error(f"Fuse operation failed: {e}")
        if callback:
            callback(f"Fuse Error: {e}")
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
        _cleanup_temp_backup(temp_backup)


def _validate_fuse_input(exe_path: str) -> Optional[str]:
    """验证 Fuse 操作的输入参数，返回规范化路径或 None"""
    try:
        if not exe_path or not isinstance(exe_path, str):
            logger.warning("Invalid executable path")
            return None

        exe_path = normalize_path(exe_path)

        if not os.path.exists(exe_path):
            logger.error(f"Executable file does not exist: {exe_path}")
            return None

        if not os.path.isfile(exe_path):
            logger.error(f"Not a file: {exe_path}")
            return None

        file_size = os.path.getsize(exe_path)
        if file_size < FUSE_VALIDATION_MIN_SIZE:
            logger.warning(f"File too small to contain Fuse data: {file_size} bytes")
            return None

        return exe_path
    except Exception as e:
        logger.error(f"Failed to validate executable path: {e}")
        return None


def _ensure_fuse_backup(exe_path: str, callback: Optional[Callable]) -> bool:
    """确保 Fuse 备份存在且有效，不存在则创建。返回是否成功"""
    backup_path = exe_path + ".fuse_backup"

    need_backup = True
    if os.path.exists(backup_path):
        ok, reason = verify_fuse_backup(exe_path, use_full_hash=False)
        if ok:
            need_backup = False
            logger.debug(f"Existing Fuse backup verified: {backup_path}")
        else:
            logger.warning(f"Existing backup corrupted, recreating: {reason}")

    if not need_backup:
        return True

    temp_bak = backup_path + ".tmp"
    try:
        shutil.copy2(exe_path, temp_bak)

        if not _verify_backup_with_full_hash(exe_path, temp_bak):
            logger.error("Backup verification failed")
            try:
                os.remove(temp_bak)
            except OSError:
                pass
            return False

        os.replace(temp_bak, backup_path)
        logger.info(f"Created verified Fuse backup at: {backup_path}")
    except Exception as backup_e:
        logger.error(f"Failed to create Fuse backup: {backup_e}")
        try:
            if os.path.exists(temp_bak):
                os.remove(temp_bak)
        except OSError:
            pass
        return False

    if callback:
        callback(f"Backup created: {os.path.basename(backup_path)}")
    return True


def _modify_fuse_byte(exe_path: str, callback: Optional[Callable]) -> Optional[bool]:
    """
    使用 mmap 修改 Fuse 校验字节。

    Returns:
        None: 失败（sentinel 未找到或意外字节）
        True: Fuse 已禁用（无需修改）
        False: 已修改成功，需要后续验证
    """
    fuse_sentinel = get_config().fuse_sentinel
    header_len = get_config().fuse_wire_header_length
    integrity_offset = get_config().fuse_asar_integrity_offset

    with open(exe_path, "r+b") as f:
        with mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_WRITE) as mm:
            offset = mm.find(fuse_sentinel)

            if offset == -1:
                logger.info("Fuse sentinel not found - already removed or never present")
                return None

            target = offset + header_len + integrity_offset

            if target + 1 > mm.size():
                logger.error(f"Target position {target} exceeds file size {mm.size()}")
                return None

            current_byte = mm[target : target + 1]

            if current_byte == FUSE_ENABLED_BYTE:
                mm[target : target + 1] = FUSE_DISABLED_BYTE
                mm.flush()

                mm.seek(target)
                verify_byte = mm.read(1)
                if verify_byte != FUSE_DISABLED_BYTE:
                    logger.error(
                        f"Verification failed after modification: expected {FUSE_DISABLED_BYTE!r}, got {verify_byte!r}"
                    )
                    raise FuseError("Modification verification failed")

                logger.info("Fuse checksum byte modified (0x31 -> 0x30) and verified")
                if callback:
                    callback("Fuse removed and verified.")
                return False

            elif current_byte == FUSE_DISABLED_BYTE:
                logger.info("Fuse already disabled")
                if callback:
                    callback("Fuse already disabled.")
                return True
            else:
                logger.warning(f"Unexpected byte at target position: {current_byte!r}")
                return None


def _verify_fuse_final(exe_path: str) -> bool:
    """最终验证：重新打开文件确认修改持久化"""
    fuse_sentinel = get_config().fuse_sentinel
    header_len = get_config().fuse_wire_header_length
    integrity_offset = get_config().fuse_asar_integrity_offset

    with open(exe_path, "rb") as f:
        with mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ) as mm:
            offset = mm.find(fuse_sentinel)
            if offset != -1:
                target = offset + header_len + integrity_offset
                final_byte = mm[target : target + 1]
                if final_byte == FUSE_DISABLED_BYTE:
                    return True
                else:
                    logger.error(f"Final verification failed: {final_byte!r}")
                    return False
            else:
                logger.warning("Sentinel not found in final verification")
                return False


def _cleanup_temp_backup(temp_backup: str) -> None:
    """清理临时备份文件"""
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
