# -*- coding: utf-8 -*-
"""
批处理模式模块

提供命令行批处理模式的功能。
"""

import os
import logging

from utils.performance import get_performance_monitor
from core.patcher import CoreLogic
from controllers.patch_controller import PatchController
from utils.cleanup import force_cleanup_dir

logger = logging.getLogger(__name__)


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
        from core.fuse import remove_fuse

        logger.info(f"Removing Fuse from: {args.fuse}")
        if not os.path.exists(args.fuse):
            logger.error(f"File not found: {args.fuse}")
            return 1
        result = remove_fuse(args.fuse, callback=lambda msg: logger.info(msg))
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

    try:
        success, temp_dir, error_msg = controller.run_auto_patch()
        if success:
            logger.info("Batch patching completed successfully")
            if temp_dir and os.path.exists(temp_dir):
                force_cleanup_dir(temp_dir)
            return 0
        else:
            if error_msg == "Cancelled or error":
                # Cancelled or Steam update error (already logged)
                return 1
            else:
                logger.error(f"Batch patching failed: {error_msg}")
                return 1
    except Exception as e:
        logger.exception(f"Batch patching crashed: {e}")
        return 1
    finally:
        elapsed = monitor.stop("batch_auto_patch")
        logger.info(f"Batch auto patch operation took {elapsed:.3f}s")
