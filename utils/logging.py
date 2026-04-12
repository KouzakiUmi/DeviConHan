# -*- coding: utf-8 -*-

import os
import sys
import logging
from logging.handlers import RotatingFileHandler
from typing import Optional


class NewlineSanitizingFormatter(logging.Formatter):
    """格式化器，将日志消息中的换行符转义以防止日志注入

    M5 修复：不再直接修改 LogRecord 的原始字段。
    LogRecord 对象可能被多个 handler 共享，原地修改 .msg 是副作用。
    修复：若消息包含换行符，就先遺制一份副本再修改，不影响原始对象。
    """

    def format(self, record):
        # 只在消息确实包含换行 / 回车符时才进行副本。
        # 避免对每条日志都拷贝对象，减少不必要内存分配。
        if isinstance(record.msg, str) and ("\n" in record.msg or "\r" in record.msg):
            record = logging.makeLogRecord(record.__dict__)
            record.msg = record.msg.replace("\n", "\\n").replace("\r", "\\r")
        return super().format(record)


def setup_logging(
    log_dir: Optional[str] = None,
    log_file: str = "tyrano_patcher.log",
    max_bytes: int = 10 * 1024 * 1024,
    backup_count: int = 5,
    verbose: bool = False,
    quiet: bool = False,
) -> logging.Logger:
    """
    设置日志系统，支持控制台和文件输出，带日志轮转功能

    Args:
        log_dir: 日志目录路径，None表示使用默认目录
        log_file: 日志文件名
        max_bytes: 单个日志文件最大字节数（默认10MB）
        backup_count: 保留的备份文件数量
        verbose: 是否启用详细输出
        quiet: 是否静默模式（仅输出错误）

    Returns:
        logging.Logger: 配置好的根logger
    """
    if log_dir is None:
        # 使用用户主目录下的 .tyranopatcher 子目录
        log_dir = os.path.join(os.path.expanduser("~"), ".tyranopatcher")

    # 尝试创建日志目录
    log_dirs_to_try = [
        log_dir,
        os.path.join(os.path.expanduser("~"), ".tyranopatcher"),
        "./logs",
        ".",
    ]

    actual_log_dir = None
    for try_dir in log_dirs_to_try:
        try:
            import tempfile

            os.makedirs(try_dir, exist_ok=True)
            # 使用 tempfile 创建写测试文件，避免残留固定名称文件
            with tempfile.NamedTemporaryFile(
                mode="w",
                encoding="utf-8",
                dir=try_dir,
                prefix=".write_test_",
                delete=True,
            ) as _tf:
                _tf.write("test")
            actual_log_dir = try_dir
            break
        except (PermissionError, OSError):
            continue

    if actual_log_dir is None:
        print(
            "Warning: Could not create log directory in any location. Logging to console only."
        )
        actual_log_dir = "."

    log_path = os.path.join(actual_log_dir, log_file)

    # 配置日志格式
    detailed_formatter = NewlineSanitizingFormatter(
        "%(asctime)s - %(levelname)-8s - %(name)s - %(funcName)s:%(lineno)d - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    simple_formatter = NewlineSanitizingFormatter(
        "%(asctime)s - %(levelname)-8s - %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
    )

    # 创建根logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)

    # 清除已有的handler，避免重复
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    # 根据参数设置日志级别
    if quiet:
        console_level = logging.ERROR
    elif verbose:
        console_level = logging.DEBUG
    else:
        console_level = logging.INFO

    # 控制台处理器
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(console_level)
    console_handler.setFormatter(simple_formatter)
    root_logger.addHandler(console_handler)

    # 文件处理器（带轮转）
    try:
        file_handler = RotatingFileHandler(
            log_path, maxBytes=max_bytes, backupCount=backup_count, encoding="utf-8"
        )
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(detailed_formatter)
        root_logger.addHandler(file_handler)

        # 输出日志文件位置信息（quiet 模式下不输出）
        if not quiet and console_level <= logging.INFO:
            print(f"Logging to file: {log_path}")

    except (PermissionError, OSError) as e:
        print(f"Warning: Could not create log file: {e}")
        print("Logging to console only.")

    return root_logger
