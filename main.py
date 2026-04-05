#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""恶魔链接补丁工具 - 主程序入口"""

import sys
import argparse
from typing import Optional, List

from core.config import get_config
from gui.main_window import App
from core.patcher import batch_mode
from utils.logging import setup_logging
from utils.language import init_lang


def parse_arguments() -> argparse.Namespace:
    """解析命令行参数"""
    parser = argparse.ArgumentParser(
        prog=get_config().app_name,
        description="Tyrano Game Patcher - A tool for applying patches and managing game files",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    parser.add_argument("--batch", action="store_true",
                        help="Run in batch mode (no GUI)")
    parser.add_argument("--auto", action="store_true",
                        help="Automatically detect and patch game")
    parser.add_argument("--log-file", metavar="PATH",
                        help="Custom log file path")
    parser.add_argument("-v", "--verbose", action="store_true",
                        help="Enable verbose output")
    parser.add_argument("-q", "--quiet", action="store_true",
                        help="Suppress non-error output")

    return parser.parse_args()


def main() -> int:
    """
    主函数，处理命令行参数和启动GUI/批处理模式

    Returns:
        int: 退出码 (0=成功, 非0=错误)
    """
    args = parse_arguments()
    # 初始化语言必须在获取配置之前，因为配置可能需要本地化的错误消息
    init_lang()
    # 初始化日志系统（在配置之前，以便记录配置加载过程）
    if args.log_file:
        logger = setup_logging(log_file=args.log_file)
    else:
        logger = setup_logging()

    # 获取配置（现在日志和语言都已初始化）
    config = get_config()
    config_valid, issues = config.validate_config()
    if not config_valid:
        logger.error(f"Configuration validation failed: {issues}")
        # 在批处理模式下，配置验证失败应该退出
        if args.batch:
            return 1

    if args.batch:
        return batch_mode(args)

    # 如果使用了非GUI参数但没有--batch，则应该报错或退出
    if args.auto and not args.batch:
        print("Error: Non-GUI arguments detected but --batch not specified.")
        print("Use --batch flag to run in batch mode or remove the non-GUI flags.")
        return 1

    # Windows 下动态分配控制台用于 Debug
    if sys.platform.startswith("win") and not args.batch:
        if config.get_gui_config("show_console", False):
            import ctypes
            # 如果 AllocConsole 返回 1，说明成功分配了新的控制台
            if ctypes.windll.kernel32.AllocConsole():
                sys.stdout = open("CONOUT$", "w", encoding="utf-8")
                sys.stderr = open("CONOUT$", "w", encoding="utf-8")

    # 启动GUI模式
    try:
        app = App()
        app.mainloop()
        return 0
    except Exception as e:
        logger.exception(f"Fatal error in main: {e}")
        # messagebox.showerror("Fatal Error", f"An unexpected error occurred:\n{str(e)}")
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
