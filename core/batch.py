"""
批处理模式模块

提供命令行批处理模式的功能。
"""

import logging
import os

from controllers.patch_controller import PatchController
from core.fuse import remove_fuse
from core.patcher import CoreLogic
from utils.cleanup import force_cleanup_dir
from utils.constants import BATCH_CANCEL_OR_ERROR_MSG
from utils.paths import normalize_path
from utils.performance import get_performance_monitor

logger = logging.getLogger(__name__)


def _validate_fuse_path(fuse_arg: str) -> str:
    """
    验证 --fuse 参数路径的安全性

    Args:
        fuse_arg: 用户输入的 fuse 文件路径

    Returns:
        str: 规范化后的安全路径

    Raises:
        ValueError: 路径不合法
    """
    if not fuse_arg or not fuse_arg.strip():
        raise ValueError("Fuse path cannot be empty")

    norm_path = normalize_path(fuse_arg)
    if not norm_path:
        raise ValueError(f"Invalid fuse path: {fuse_arg}")

    if not os.path.isfile(norm_path):
        raise ValueError(f"Fuse path is not a file: {norm_path}")

    return norm_path


def batch_mode(args):
    """
    批处理模式

    Args:
        args: 命令行参数

    Returns:
        int: 退出码 (0=成功, 非0=错误)
    """
    logger.info("Running in batch mode")

    # 处理 --fuse 参数：移除指定文件的 Fuse 完整性校验
    if hasattr(args, "fuse") and args.fuse:
        try:
            fuse_path = _validate_fuse_path(args.fuse)
        except ValueError as e:
            logger.error(f"Invalid fuse argument: {e}")
            return 1

        logger.info(f"Removing Fuse from: {fuse_path}")
        result = remove_fuse(fuse_path, callback=lambda msg: logger.info(msg))
        if result:
            logger.info("Fuse removed successfully")
            return 0
        else:
            logger.error("Failed to remove Fuse or Fuse not found")
            return 1

    if not args.auto:
        logger.error("Batch mode requires --auto or --fuse flag")
        return 1

    try:
        core = CoreLogic()
    except Exception as e:
        logger.error(f"Failed to initialize CoreLogic: {e}")
        return 1

    # 自动检测并打补丁
    logger.info("Auto-detect and patch mode")

    # Use PatchController directly instead of duplicating logic
    controller = PatchController(core, log_callback=lambda msg: logger.info(msg))

    monitor = get_performance_monitor()
    monitor.start("batch_auto_patch")

    temp_dir = None
    try:
        success, temp_dir, error_msg = controller.run_auto_patch()
        if success:
            logger.info("Batch patching completed successfully")
            return 0
        else:
            if error_msg == BATCH_CANCEL_OR_ERROR_MSG:
                # Cancelled or Steam update error (already logged)
                return 1
            else:
                logger.error(f"Batch patching failed: {error_msg}")
                return 1
    except Exception as e:
        logger.exception(f"Batch patching crashed: {e}")
        return 1
    finally:
        # 无论成功与否，都清理临时目录
        if temp_dir and os.path.exists(temp_dir):
            force_cleanup_dir(temp_dir)
        elapsed = monitor.stop("batch_auto_patch")
        logger.info(f"Batch auto patch operation took {elapsed:.3f}s")
