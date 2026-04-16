#!/usr/bin/env python
"""恶魔链接补丁工具 - 主程序入口"""

import argparse
import logging
import sys

from core.config import get_config
from gui.main_window import App
from utils.language import init_lang
from utils.logging import retarget_console_streams, setup_logging


def parse_arguments() -> argparse.Namespace:
    """解析命令行参数"""
    parser = argparse.ArgumentParser(
        prog="TyranoPatcher",
        description="Tyrano Game Patcher - A tool for applying patches and managing game files",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument("--batch", action="store_true", help="Run in batch mode (no GUI)")
    parser.add_argument("--auto", action="store_true", help="Automatically detect and patch game")
    parser.add_argument(
        "--fuse",
        metavar="FILE",
        help="Remove Fuse integrity check from specified executable",
    )
    parser.add_argument("--log-file", metavar="PATH", help="Custom log file path")
    parser.add_argument("-v", "--verbose", action="store_true", help="Enable verbose output")
    parser.add_argument("-q", "--quiet", action="store_true", help="Suppress non-error output")

    return parser.parse_args()


def main() -> int:
    """
    主函数，处理命令行参数和启动GUI/批处理模式

    Returns:
        int: 退出码 (0=成功, 非0=错误)
    """
    args = parse_arguments()

    # --verbose 和 --quiet 不能同时使用
    if args.verbose and args.quiet:
        print("Error: --verbose and --quiet are mutually exclusive.", file=sys.stderr)
        return 1

    # 1. 初始化日志系统（最先初始化，确保后续操作都能记录日志）
    log_kwargs = {"verbose": args.verbose, "quiet": args.quiet}
    if args.log_file:
        log_kwargs["log_file"] = args.log_file
    logger = setup_logging(**log_kwargs)

    # 2. 初始化语言设置（依赖日志系统）
    init_lang()

    # 3. 系统引导检查（包含配置验证、状态检查、磁盘检查）
    try:
        from core.bootstrap import bootstrap_system

        bootstrap_ok, bootstrap_messages = bootstrap_system(
            skip_state_check=args.batch  # 批处理模式下跳过状态检查
        )

        for msg in bootstrap_messages:
            if "Warning:" in msg:
                logger.warning(msg)
            else:
                logger.info(msg)

    except Exception as e:
        logger.critical(f"System bootstrap failed: {e}")
        return 1

    if args.batch:
        from core.batch import batch_mode

        return batch_mode(args)

    if (args.auto or args.fuse) and not args.batch:
        logger.error(
            "Non-GUI arguments detected but --batch not specified. "
            "Use --batch flag to run in batch mode or remove the non-GUI flags."
        )
        return 1

    # Windows 下动态分配控制台用于 Debug
    class ConsoleManager:
        def __init__(self):
            self.console_allocated = False
            self.console_connected = False
            self.original_stdout = sys.stdout
            self.original_stderr = sys.stderr
            self.ctypes = None
            self.stdout = None
            self.stderr = None

        def acquire(self):
            if sys.platform.startswith("win") and not args.batch:
                config = get_config()
                if config.get_gui_config("show_console", False):
                    try:
                        import ctypes

                        self.ctypes = ctypes
                        # 尝试附加到现有控制台或创建新控制台
                        # 先尝试 AttachConsole(-1) 附加到父进程的控制台
                        if ctypes.windll.kernel32.AttachConsole(-1):
                            self.console_connected = True
                        elif ctypes.windll.kernel32.AllocConsole():
                            # 如果附加失败，尝试创建新控制台
                            self.console_allocated = True
                            self.console_connected = True

                        if self.console_connected:
                            self.stdout = open("CONOUT$", "w", encoding="utf-8", buffering=1)
                            self.stderr = open("CONOUT$", "w", encoding="utf-8", buffering=1)
                            sys.stdout = self.stdout
                            sys.stderr = self.stderr
                            retarget_console_streams(
                                self.stdout,
                                self.stderr,
                                old_stdout=self.original_stdout,
                                old_stderr=self.original_stderr,
                            )
                            logger.debug("Console attached/allocated for debugging")
                    except Exception as e:
                        logger.warning(f"Failed to attach/allocate console: {e}")

        def release(self):
            if self.console_connected:
                try:
                    retarget_console_streams(
                        self.original_stdout,
                        self.original_stderr,
                        old_stdout=self.stdout,
                        old_stderr=self.stderr,
                    )
                    sys.stdout = self.original_stdout
                    sys.stderr = self.original_stderr

                    if self.stdout is not None:
                        self.stdout.close()
                    if self.stderr is not None and self.stderr is not self.stdout:
                        self.stderr.close()

                    if self.ctypes is not None:
                        self.ctypes.windll.kernel32.FreeConsole()
                    self.console_allocated = False
                    self.console_connected = False
                    logging.getLogger(__name__).debug("Console freed")
                except Exception as cleanup_err:
                    logger.warning(f"Console cleanup error: {cleanup_err}")

    console_manager = ConsoleManager()
    console_manager.acquire()

    # 启动GUI模式
    try:
        app = App()
        app.mainloop()
        return 0
    except Exception:
        logger.exception("Fatal error in main")
        return 1
    finally:
        # 清理控制台句柄
        console_manager.release()


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
