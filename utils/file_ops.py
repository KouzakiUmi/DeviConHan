"""
文件和目录操作模块

提供复制目录并校验哈希值等高级文件操作。
"""

__all__ = [
    "compute_file_hash",
    "quick_file_hash",
    "migrate_backup",
    "safe_extract_zip",
    "verify_directory_safe",
]

import hashlib
import logging
import os
import shutil
import struct
import zipfile
from typing import Callable, Optional

from utils.cleanup import force_cleanup_dir
from utils.constants import HASH_CHUNK_SIZE, MAX_ZIP_EXTRACT_FILES, MAX_ZIP_EXTRACT_SIZE
from utils.paths import safe_path_within

logger = logging.getLogger(__name__)


def quick_file_hash(file_path: str, head_size: int = 65536, tail_size: int = 65536) -> str:
    """
    快速计算文件的 SHA256 哈希值（仅读取首尾部分）

    适用于大文件的快速比较，不保证完全准确，但性能极优。
    读取文件头部、尾部和文件大小作为指纹。

    Args:
        file_path: 文件路径
        head_size: 头部读取字节数（默认64KB）
        tail_size: 尾部读取字节数（默认64KB）

    Returns:
        str: 哈希值，失败返回空字符串
    """
    try:
        if not os.path.exists(file_path) or not os.path.isfile(file_path):
            return ""

        file_size = os.path.getsize(file_path)
        sha256_hash = hashlib.sha256()

        # 加入文件大小作为指纹一部分
        sha256_hash.update(struct.pack("<Q", file_size))

        with open(file_path, "rb") as f:
            # 读取头部
            sha256_hash.update(f.read(head_size))

            # 如果文件足够大，读取尾部
            if file_size > head_size + tail_size:
                f.seek(-tail_size, 2)
                sha256_hash.update(f.read(tail_size))
            elif file_size > head_size:
                # 文件不大，读取剩余部分
                f.seek(head_size)
                sha256_hash.update(f.read())

        return sha256_hash.hexdigest()
    except Exception as e:
        logger.error(f"Failed to compute quick hash for {file_path}: {e}")
        return ""


def compute_file_hash(file_path: str, chunk_size: int = HASH_CHUNK_SIZE) -> str:
    """
    计算文件的 SHA256 哈希值

    当 chunk_size 为默认值时，根据文件大小动态调整块大小以优化性能；
    当调用方显式指定 chunk_size 时，尊重调用方的设置。

    Args:
        file_path: 文件路径
        chunk_size: 读取块大小（默认64KB，优化大文件性能）

    Returns:
        str: 哈希值，失败返回空字符串
    """
    try:
        if not os.path.exists(file_path) or not os.path.isfile(file_path):
            return ""

        # 仅在使用默认值时做动态调整，显式传入的 chunk_size 保持不变
        if chunk_size == HASH_CHUNK_SIZE:
            file_size = os.path.getsize(file_path)
            actual_chunk = min(4 * 1024 * 1024, max(65536, file_size // 100))
        else:
            actual_chunk = chunk_size

        sha256_hash = hashlib.sha256()
        with open(file_path, "rb") as f:
            for byte_block in iter(lambda: f.read(actual_chunk), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()
    except Exception as e:
        logger.error(f"Failed to compute hash for {file_path}: {e}")
        return ""


def safe_extract_zip(
    zip_path: str, dest_dir: str, check_cancelled: Optional[Callable] = None
) -> bool:
    """
    安全地解压ZIP文件，防止路径遍历攻击并防止 ZIP 炸弹攻击

    Args:
        zip_path: ZIP文件路径
        dest_dir: 目标目录
        check_cancelled: 取消检查回调函数

    Returns:
        bool: 是否成功解压

    Raises:
        ValueError: 如果检测到恶意路径或超过安全限制
    """
    if not os.path.exists(zip_path):
        logger.error(f"ZIP file not found: {zip_path}")
        return False

    try:
        abs_dest_dir = os.path.normpath(os.path.abspath(dest_dir))

        with zipfile.ZipFile(zip_path, "r") as zf:
            total_uncompressed = 0
            file_count = 0
            for info in zf.infolist():
                file_count += 1
                total_uncompressed += info.file_size
                if file_count > MAX_ZIP_EXTRACT_FILES:
                    raise ValueError(
                        f"ZIP contains too many files (>{MAX_ZIP_EXTRACT_FILES}). "
                        "Possible ZIP bomb."
                    )
                if total_uncompressed > MAX_ZIP_EXTRACT_SIZE:
                    raise ValueError(
                        f"ZIP uncompressed size exceeds {MAX_ZIP_EXTRACT_SIZE // (1024**3)} GB limit. "
                        "Possible ZIP bomb."
                    )

            for member in zf.infolist():
                # 检查取消标志
                if check_cancelled:
                    check_cancelled()

                # 额外检查：拒绝绝对路径（ZIP 规范本不允许，但需明确防御）
                if os.path.isabs(member.filename):
                    raise ValueError(f"Absolute path not allowed in ZIP file: {member.filename}")

                # 使用 safe_path_within 做路径遍历检测
                # 该函数先 join 再 normpath/abspath，能防御 ....// 等所有变体
                abs_member_path = safe_path_within(member.filename, abs_dest_dir)
                if abs_member_path is None:
                    raise ValueError(f"Path traversal detected in ZIP file: {member.filename}")

                # 检查是否为目录
                if member.filename.endswith("/"):
                    os.makedirs(abs_member_path, exist_ok=True)
                else:
                    # 确保父目录存在
                    parent_dir = os.path.dirname(abs_member_path)
                    os.makedirs(parent_dir, exist_ok=True)

                    # 解压文件（使用分块读取避免大文件内存溢出）
                    with zf.open(member) as source, open(abs_member_path, "wb") as target:
                        # 分块读取，每块 64KB，避免大文件一次性读入内存
                        while True:
                            chunk = source.read(65536)
                            if not chunk:
                                break
                            target.write(chunk)

        logger.info(f"Successfully extracted ZIP file: {zip_path}")
        return True

    except ValueError as e:
        logger.error(f"Security violation in ZIP file: {e}")
        raise
    except Exception as e:
        logger.error(f"Failed to extract ZIP file {zip_path}: {e}")
        return False


def migrate_backup(src: str, dest_dir: str) -> bool:
    """
    将备份文件或目录迁移到目标目录，
    复制后校验哈希值，如果校验通过则删除源文件/目录。

    Args:
        src: 源路径 (文件或目录)
        dest_dir: 目标目录的父路径 (备份将被放置于此目录中)

    Returns:
        bool: 迁移是否完全成功
    """
    basename = os.path.basename(src)
    dest_path = os.path.join(dest_dir, basename)

    # 防止同名文件或目录已经存在
    if os.path.exists(dest_path):
        logger.warning(f"Destination path already exists: {dest_path}")
        # 如果目标已经存在，并且哈希完全匹配？这里安全起见不覆盖
        # 但如果是续传或者冲突，可以直接在目标加一个后缀
        counter = 1
        while os.path.exists(dest_path):
            dest_path = os.path.join(dest_dir, f"{basename}_{counter}")
            counter += 1

    try:
        if os.path.isfile(src):
            # 复制单个文件
            shutil.copy2(src, dest_path)

            # 校验哈希
            src_hash = compute_file_hash(src)
            dest_hash = compute_file_hash(dest_path)

            if src_hash and dest_hash and src_hash == dest_hash:
                os.remove(src)
                logger.info(f"Successfully migrated backup file: {src} -> {dest_path}")
                return True
            else:
                logger.error(f"Hash mismatch after migrating file: {src}")
                # 清理损坏的副本
                if os.path.exists(dest_path):
                    os.remove(dest_path)
                return False

        elif os.path.isdir(src):
            # 复制目录
            shutil.copytree(src, dest_path)

            # 校验目录下所有文件哈希
            all_match = True
            for root, _, files in os.walk(src):
                for name in files:
                    src_file = os.path.join(root, name)
                    rel_path = os.path.relpath(src_file, src)
                    dest_file = os.path.join(dest_path, rel_path)

                    if not os.path.exists(dest_file):
                        all_match = False
                        break

                    src_hash = compute_file_hash(src_file)
                    dest_hash = compute_file_hash(dest_file)

                    if not src_hash or src_hash != dest_hash:
                        all_match = False
                        break

                if not all_match:
                    break

            if all_match:
                # 校验通过，删除源目录
                force_cleanup_dir(src)
                logger.info(f"Successfully migrated backup directory: {src} -> {dest_path}")
                return True
            else:
                logger.error(f"Hash mismatch after migrating directory: {src}")
                # 清理损坏的副本目录
                if os.path.exists(dest_path):
                    force_cleanup_dir(dest_path)
                return False

        else:
            logger.error(f"Source path is not a valid file or directory: {src}")
            return False

    except Exception as e:
        logger.exception(f"Exception occurred during migration of {src}: {e}")
        # 如果复制过程出错，尝试清理不完整的目标
        if os.path.exists(dest_path):
            try:
                if os.path.isfile(dest_path):
                    os.remove(dest_path)
                else:
                    force_cleanup_dir(dest_path)
            except Exception:
                pass
        return False


def verify_directory_safe(directory: str) -> bool:
    """
    验证目录中所有文件和子目录的路径都在该目录内（防止路径遍历）

    Args:
        directory: 要验证的目录路径

    Returns:
        bool: 目录是否安全（所有路径都在目录内）

    Note:
        此函数用于验证 ASAR 解压后的结果，确保没有路径遍历攻击
    """
    if not directory or not os.path.exists(directory):
        return True

    try:
        abs_dir = os.path.normpath(os.path.abspath(directory))
        dir_with_sep = abs_dir if abs_dir.endswith(os.sep) else abs_dir + os.sep

        for root, dirs, files in os.walk(directory):
            for name in dirs + files:
                item_path = os.path.join(root, name)
                abs_item = os.path.normpath(os.path.abspath(item_path))

                if abs_item != abs_dir and not abs_item.startswith(dir_with_sep):
                    logger.error(
                        f"Path traversal detected in directory: {item_path} "
                        f"resolves to {abs_item} which is outside {abs_dir}"
                    )
                    return False

        return True
    except Exception as e:
        logger.error(f"Failed to verify directory safety: {e}")
        return False
