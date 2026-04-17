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


class ConsoleManager:
    """Windows 下动态分配控制台用于 Debug"""

    def __init__(self, show_console: bool = False):
        self.console_allocated = False
        self.console_connected = False
        self.original_stdout = sys.stdout
        self.original_stderr = sys.stderr
        self.ctypes = None
        self.stdout = None
        self.stderr = None
        self.show_console = show_console

    def acquire(self):
        if sys.platform.startswith("win") and self.show_console:
            try:
                import ctypes

                self.ctypes = ctypes
                if ctypes.windll.kernel32.AttachConsole(-1):
                    self.console_connected = True
                elif ctypes.windll.kernel32.AllocConsole():
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
                    logging.getLogger(__name__).debug("Console attached/allocated for debugging")
            except Exception as e:
                logging.getLogger(__name__).warning(f"Failed to attach/allocate console: {e}")

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
                logging.getLogger(__name__).warning(f"Console cleanup error: {cleanup_err}")


def main() -> int:
    """
    主函数，处理命令行参数和启动GUI/批处理模式

    Returns:
        int: 退出码 (0=成功, 非0=错误)
    """
    args = parse_arguments()

    if args.verbose and args.quiet:
        print("Error: --verbose and --quiet are mutually exclusive.", file=sys.stderr)
        return 1

    log_kwargs = {"verbose": args.verbose, "quiet": args.quiet}
    if args.log_file:
        log_kwargs["log_file"] = args.log_file
    logger = setup_logging(**log_kwargs)

    init_lang()

    try:
        from core.bootstrap import bootstrap_system

        bootstrap_ok, bootstrap_messages = bootstrap_system(
            skip_state_check=args.batch
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

    show_console = get_config().get_gui_config("show_console", False)
    console_manager = ConsoleManager(show_console=show_console)
    console_manager.acquire()

    try:
        app = App()
        app.mainloop()
        return 0
    except Exception:
        logger.exception("Fatal error in main")
        return 1
    finally:
        console_manager.release()


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
