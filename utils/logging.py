# -*- coding: utf-8 -*-

import os
import sys
import logging
from logging.handlers import RotatingFileHandler
from typing import Optional


def setup_logging(log_dir: Optional[str] = None, log_file: str = "tyrano_patcher.log", 
                  max_bytes: int = 10*1024*1024, backup_count: int = 5, verbose: bool = False, quiet: bool = False) -> logging.Logger:
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
        "."
    ]
    
    actual_log_dir = None
    for try_dir in log_dirs_to_try:
        try:
            os.makedirs(try_dir, exist_ok=True)
            test_file = os.path.join(try_dir, ".write_test")
            with open(test_file, 'w', encoding='utf-8') as f:
                f.write("test")
            os.remove(test_file)
            actual_log_dir = try_dir
            break
        except (PermissionError, OSError):
            continue
    
    if actual_log_dir is None:
        print("Warning: Could not create log directory in any location. Logging to console only.")
        actual_log_dir = "."
    
    log_path = os.path.join(actual_log_dir, log_file)
    
    # 配置日志格式
    detailed_formatter = logging.Formatter(
        '%(asctime)s - %(levelname)-8s - %(name)s - %(funcName)s:%(lineno)d - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    simple_formatter = logging.Formatter(
        '%(asctime)s - %(levelname)-8s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
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
            log_path,
            maxBytes=max_bytes,
            backupCount=backup_count,
            encoding='utf-8'
        )
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(detailed_formatter)
        root_logger.addHandler(file_handler)
        
        # 输出日志文件位置信息
        if console_level <= logging.INFO:
            print(f"Logging to file: {log_path}")
            
    except (PermissionError, OSError) as e:
        print(f"Warning: Could not create log file: {e}")
        print("Logging to console only.")
    
    return root_logger
