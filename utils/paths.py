__all__ = [
    "get_resource_path",
    "normalize_path",
    "safe_path_within",
    "validate_path_exists",
    "ensure_directory",
    "get_user_config_path",
]

import logging
import os
import sys
from typing import Optional, Tuple

from utils.constants import MAX_PATH_LENGTH

logger = logging.getLogger(__name__)


def get_resource_path(relative_path: str) -> str:
    """
    获取资源路径（支持PyInstaller打包）
    Args:
        relative_path: 相对路径
    Returns:
        绝对路径
    """
    base_path = getattr(sys, "_MEIPASS", None)
    if base_path is None:
        base_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    path = os.path.join(base_path, relative_path)

    if not os.path.exists(path):
        logger.debug(f"Resource path not found or not yet created: {path}")

    return path


def normalize_path(path: str) -> str:
    """
    规范化路径，处理各种边界情况。

    注意：本函数不对路径做边界限制（沙箱），仅做格式规范化。
    """
    if not path:
        return ""

    try:
        path = path.strip()

        if "%" in path and sys.platform.startswith("win"):
            original = path
            path = os.path.expandvars(path)
            if path != original:
                logger.debug(f"Expanded environment variables in path: {original} -> {path}")

        path = os.path.normpath(os.path.abspath(path))

        if len(path) > MAX_PATH_LENGTH:
            logger.warning(f"Path too long: {len(path)} chars")

        if sys.platform == "win32" and len(path) >= MAX_PATH_LENGTH:
            if not path.startswith("\\\\?\\"):
                path = path.replace("/", "\\")
                if path.startswith("\\\\"):
                    path = "\\\\?\\UNC\\" + path[2:]
                else:
                    path = "\\\\?\\" + path

        return path
    except (TypeError, ValueError, AttributeError) as e:
        logger.error(f"Path normalization failed due to invalid input: {e}")
        return ""
    except Exception as e:
        logger.error(f"Unexpected error during path normalization: {e}")
        return ""


def safe_path_within(path: str, base_dir: str) -> Optional[str]:
    """
    规范化路径并验证其位于指定基础目录内（防路径遍历沙箱）。

    Args:
        path:     待验证的路径（可以是相对路径或绝对路径）
        base_dir: 允许的根目录（绝对路径）

    Returns:
        规范化后的绝对路径字符串（若在 base_dir 内），否则返回 None。
    """
    if not path or not base_dir:
        return None

    try:
        abs_base = os.path.normpath(os.path.abspath(base_dir))
        abs_path = os.path.normpath(os.path.abspath(os.path.join(abs_base, path)))

        base_lower = abs_base.lower().replace("\\", "/").rstrip("/") + "/"
        path_lower = abs_path.lower().replace("\\", "/")

        path_normalized = path_lower.rstrip("/") + "/"
        base_normalized = base_lower.rstrip("/") + "/"

        if path_normalized != base_normalized and not path_normalized.startswith(base_normalized):
            logger.warning(
                f"Path traversal detected: '{path}' resolves to '{abs_path}' "
                f"which is outside base '{abs_base}'"
            )
            return None

        return abs_path
    except (TypeError, ValueError) as e:
        logger.error(f"safe_path_within failed due to invalid input: {e}")
        return None
    except Exception as e:
        logger.error(f"safe_path_within failed: {e}")
        return None


def validate_path_exists(path: str, path_type: str = "Resource") -> Tuple[bool, str]:
    """
    验证路径是否存在

    Args:
        path: 路径字符串
        path_type: 路径类型描述（用于日志）

    Returns:
        Tuple[bool, str]: (是否存在, 错误消息)
    """
    if not path:
        return False, f"{path_type} path is empty"

    if not os.path.exists(path):
        return False, f"{path_type} not found: {path}"

    return True, ""


def ensure_directory(dir_path: str) -> bool:
    """
    确保目录存在，不存在则创建

    Args:
        dir_path: 目录路径

    Returns:
        bool: 是否成功
    """
    try:
        if not os.path.exists(dir_path):
            os.makedirs(dir_path, exist_ok=True)
            logger.debug(f"Created directory: {dir_path}")
        return True
    except Exception as e:
        logger.error(f"Failed to create directory {dir_path}: {e}")
        return False


def get_user_config_path(filename: str = "config.ini") -> str:
    """
    获取用户配置文件路径（跨平台）

    Args:
        filename: 配置文件名

    Returns:
        str: 完整的配置文件路径
    """
    config_dir = os.path.join(os.path.expanduser("~"), ".tyranopatcher")
    return os.path.join(config_dir, filename)
