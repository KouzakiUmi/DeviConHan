#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import os
import argparse
import logging

from gui.main_window import App
from core.patcher import batch_mode
from utils.logging import setup_logging
from utils.language import init_lang, T

def parse_arguments():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(
        prog="TyranoV8_Patcher",
        description="Tyrano Game Patcher - A tool for applying patches and managing game files",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    parser.add_argument("--batch", action="store_true",
                        help="Run in batch mode (no GUI)")
    parser.add_argument("--auto", action="store_true",
                        help="Automatically detect and patch game")
    parser.add_argument("--fuse", metavar="FILE",
                        help="Remove fuse checksum from specified file")
    parser.add_argument("--log-file", metavar="PATH",
                        help="Custom log file path")
    parser.add_argument("-v", "--verbose", action="store_true",
                        help="Enable verbose output")
    parser.add_argument("-q", "--quiet", action="store_true",
                        help="Suppress non-error output")

    return parser.parse_args()

def main():
    """
    主函数，处理命令行参数和启动GUI/批处理模式

    Returns:
        int: 退出码 (0=成功, 非0=错误)
    """
    args = parse_arguments()
    init_lang()
    if args.log_file:
        logger = setup_logging(log_file=args.log_file)
    else:
        logger = setup_logging()

    if args.batch:
        return batch_mode(args)

    # 如果使用了非GUI参数但没有--batch，则应该报错或退出
    if any([args.auto, args.fuse]) and not args.batch:
        print("Error: Non-GUI arguments detected but --batch not specified.")
        print("Use --batch flag to run in batch mode or remove the non-GUI flags.")
        return 1

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
