#!/usr/bin/env python
"""恶魔链接补丁工具 - 主程序入口"""

import argparse
import sys

from core.config import get_config
from gui.main_window import App
from utils.language import init_lang
from utils.logging import setup_logging


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
    _console_opened = False
    _original_stdout = sys.stdout
    _original_stderr = sys.stderr
    _ctypes = None
    if sys.platform.startswith("win") and not args.batch:
        config = get_config()
        if config.get_gui_config("show_console", False):
            try:
                import ctypes

                _ctypes = ctypes
                # 如果 AllocConsole 返回非0，说明成功分配了新的控制台
                if ctypes.windll.kernel32.AllocConsole():
                    # 在重定向之前先备份原有的 stdout/stderr，并重置到已关闭状态
                    new_stdout = open("CONOUT$", "w", encoding="utf-8")
                    new_stderr = open("CONOUT$", "w", encoding="utf-8")
                    sys.stdout = new_stdout
                    sys.stderr = new_stderr
                    _console_opened = True
            except Exception as e:
                logger.warning(f"Failed to allocate console: {e}")

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
        if _console_opened and _ctypes is not None:
            try:
                # 必须先恢复原始句柄，确保后续代码不会尝试写入已关闭的流
                if sys.stdout and sys.stdout != _original_stdout:
                    sys.stdout.close()
                if sys.stderr and sys.stderr != _original_stderr:
                    sys.stderr.close()
                
                sys.stdout = _original_stdout
                sys.stderr = _original_stderr
                _ctypes.windll.kernel32.FreeConsole()
            except Exception as cleanup_err:
                logger.warning(f"Console cleanup error: {cleanup_err}")


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
