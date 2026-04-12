"""
磁盘空间检查和文件系统工具

提供磁盘空间预检、路径可用性验证等功能。
"""

__all__ = [
    "DiskSpaceError",
    "check_disk_space",
    "estimate_asar_size",
    "validate_write_permission",
    "get_disk_free_space",
]

import logging
import os
import shutil
from typing import Tuple

logger = logging.getLogger(__name__)

# 安全余量系数：预留额外空间防止意外增长
SAFETY_MARGIN = 1.5


class DiskSpaceError(Exception):
    """磁盘空间不足错误"""
    pass


def get_disk_free_space(path: str) -> int:
    """
    获取指定路径所在磁盘的剩余空间（字节）

    Args:
        path: 文件或目录路径

    Returns:
        int: 剩余空间字节数

    Raises:
        DiskSpaceError: 如果无法获取磁盘信息
    """
    try:
        abs_path = os.path.abspath(path)

        # Windows和Unix都支持
        if hasattr(shutil, 'disk_usage'):
            usage = shutil.disk_usage(os.path.dirname(abs_path) if os.path.isfile(abs_path) else abs_path)
            return usage.free
        else:
            # 旧版本Python回退方案
            import ctypes
            if os.name == 'nt':  # Windows
                drive = os.path.splitdrive(abs_path)[0]
                free_bytes = ctypes.c_ulonglong(0)
                ctypes.windll.kernel32.GetDiskFreeSpaceExW(
                    ctypes.c_wchar_p(drive),
                    ctypes.pointer(free_bytes),
                    None,
                    None
                )
                return free_bytes.value
            else:  # Unix
                stat = os.statvfs(abs_path)
                return stat.f_frsize * stat.f_bavail

    except Exception as e:
        raise DiskSpaceError(f"Failed to get disk space for {path}: {e}") from e


def check_disk_space(
    path: str,
    required_bytes: int,
    safety_margin: float = SAFETY_MARGIN,
    raise_on_error: bool = True
) -> Tuple[bool, int]:
    """
    检查磁盘是否有足够空间

    Args:
        path: 要检查的磁盘路径
        required_bytes: 需要的空间（字节）
        safety_margin: 安全余量系数（默认1.5倍）
        raise_on_error: 空间不足时是否抛出异常

    Returns:
        Tuple[bool, int]: (是否足够, 可用空间字节数)

    Raises:
        DiskSpaceError: 如果空间不足且raise_on_error为True

    示例:
        >>> ok, free = check_disk_space("/data", 1024*1024*100)  # 检查100MB
        >>> if not ok:
        ...     print(f"空间不足，只剩 {free // 1024 // 1024} MB")
    """
    try:
        free_space = get_disk_free_space(path)
        required_with_margin = int(required_bytes * safety_margin)

        has_space = free_space >= required_with_margin

        if not has_space:
            msg = (
                f"磁盘空间不足: 需要 {format_bytes(required_bytes)} "
                f"(含余量 {format_bytes(required_with_margin)}), "
                f"可用 {format_bytes(free_space)}"
            )
            logger.error(msg)
            if raise_on_error:
                raise DiskSpaceError(msg)

        return has_space, free_space

    except DiskSpaceError:
        raise
    except Exception as e:
        msg = f"检查磁盘空间时出错: {e}"
        logger.error(msg)
        if raise_on_error:
            raise DiskSpaceError(msg) from e
        return False, 0


def estimate_asar_size(source_path: str) -> int:
    """
    估算ASAR打包后的大小

    ASAR文件 = Header + 文件内容
    Header大小取决于文件数量和目录结构，通常很小
    打包后大小约等于源目录大小 + 5-10%开销

    Args:
        source_path: 源目录路径

    Returns:
        int: 估算的字节数
    """
    if not os.path.exists(source_path):
        return 0

    total_size = 0

    try:
        if os.path.isfile(source_path):
            total_size = os.path.getsize(source_path)
        else:
            for dirpath, _dirnames, filenames in os.walk(source_path):
                for filename in filenames:
                    filepath = os.path.join(dirpath, filename)
                    try:
                        total_size += os.path.getsize(filepath)
                    except OSError:
                        pass

        # ASAR有额外开销：header + padding
        overhead = max(1024 * 1024, int(total_size * 0.1))  # 至少1MB，或10%
        return total_size + overhead

    except Exception as e:
        logger.warning(f"Failed to estimate ASAR size: {e}")
        # 如果无法计算，返回一个保守的估计
        return 1024 * 1024 * 500  # 500MB


def validate_write_permission(path: str) -> bool:
    """
    验证是否有写入权限

    Args:
        path: 要验证的路径

    Returns:
        bool: 是否有写入权限
    """
    try:
        # 如果是文件，检查父目录
        check_path = path if os.path.isdir(path) else os.path.dirname(path)

        if not os.path.exists(check_path):
            # 尝试创建目录
            try:
                os.makedirs(check_path, exist_ok=True)
            except PermissionError:
                return False

        # 尝试创建临时文件
        test_file = os.path.join(check_path, ".write_test_tmp")
        try:
            with open(test_file, 'w') as f:
                f.write("test")
            os.remove(test_file)
            return True
        except (OSError, PermissionError):
            return False

    except Exception as e:
        logger.warning(f"Write permission check failed for {path}: {e}")
        return False


def format_bytes(bytes_value: int) -> str:
    """
    格式化字节数为人类可读字符串

    Args:
        bytes_value: 字节数

    Returns:
        str: 格式化后的字符串（如 "1.5 GB"）
    """
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if bytes_value < 1024.0:
            return f"{bytes_value:.1f} {unit}"
        bytes_value /= 1024.0
    return f"{bytes_value:.1f} PB"


def check_operation_space(
    operations: list,
    base_path: str = "."
) -> Tuple[bool, str]:
    """
    检查一系列操作所需的磁盘空间

    Args:
        operations: 操作列表，每项为 (描述, 所需字节数)
        base_path: 基础路径

    Returns:
        Tuple[bool, str]: (是否足够, 详细信息)

    示例:
        >>> ops = [
        ...     ("解压ASAR", 200*1024*1024),
        ...     ("创建备份", 150*1024*1024),
        ... ]
        >>> ok, info = check_operation_space(ops)
    """
    total_required = sum(op[1] for op in operations)

    try:
        free_space = get_disk_free_space(base_path)
        required_with_margin = int(total_required * SAFETY_MARGIN)

        detail_lines = [
            "磁盘空间检查:",
            f"  所需空间: {format_bytes(total_required)}",
            f"  安全余量: {format_bytes(required_with_margin)}",
            f"  可用空间: {format_bytes(free_space)}",
            "  详细需求:",
        ]

        for desc, size in operations:
            detail_lines.append(f"    - {desc}: {format_bytes(size)}")

        if free_space >= required_with_margin:
            detail_lines.append("  ✓ 空间充足")
            return True, "\n".join(detail_lines)
        else:
            detail_lines.append(f"  ✗ 空间不足，缺少 {format_bytes(required_with_margin - free_space)}")
            return False, "\n".join(detail_lines)

    except Exception as e:
        return False, f"无法检查磁盘空间: {e}"
