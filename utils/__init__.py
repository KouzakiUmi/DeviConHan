"""
工具模块

包含通用工具函数、路径处理、文件操作、异步管理等。
"""

from utils.async_ops import AsyncOperationManager, get_async_manager
from utils.cleanup import force_cleanup_dir
from utils.constants import (
    FUSE_DISABLED_BYTE,
    FUSE_ENABLED_BYTE,
    MAX_ASAR_SIZE,
    MAX_PATH_LENGTH,
    MIN_ASAR_SIZE,
    NATIVE_EXTENSIONS,
)
from utils.disk_utils import format_bytes, get_disk_free_space
from utils.error_handler import (
    ErrorCategory,
    ErrorHandler,
    ErrorSeverity,
    PatcherError,
    get_error_handler,
)
from utils.file_ops import (
    compute_file_hash,
    detect_patch_zip_root,
    safe_extract_zip,
    verify_directory_safe,
)
from utils.language import T, get_font, get_mono_font, init_lang, set_language
from utils.operation_lock import OperationLock, OperationType, get_operation_lock
from utils.paths import get_resource_path, get_user_config_path, normalize_path, safe_path_within
from utils.performance import PerformanceMonitor, get_performance_monitor
from utils.platform import get_platform_info, get_resources_path, get_steam_library_paths
from utils.validators import ValidationError, sanitize_user_path

__all__ = [
    "AsyncOperationManager",
    "get_async_manager",
    "force_cleanup_dir",
    "MAX_PATH_LENGTH",
    "MIN_ASAR_SIZE",
    "MAX_ASAR_SIZE",
    "NATIVE_EXTENSIONS",
    "FUSE_ENABLED_BYTE",
    "FUSE_DISABLED_BYTE",
    "format_bytes",
    "get_disk_free_space",
    "ErrorCategory",
    "ErrorHandler",
    "ErrorSeverity",
    "PatcherError",
    "get_error_handler",
    "compute_file_hash",
    "detect_patch_zip_root",
    "safe_extract_zip",
    "verify_directory_safe",
    "T",
    "get_font",
    "get_mono_font",
    "set_language",
    "init_lang",
    "OperationLock",
    "OperationType",
    "get_operation_lock",
    "get_resource_path",
    "normalize_path",
    "safe_path_within",
    "get_user_config_path",
    "PerformanceMonitor",
    "get_performance_monitor",
    "get_platform_info",
    "get_steam_library_paths",
    "get_resources_path",
    "ValidationError",
    "sanitize_user_path",
]
