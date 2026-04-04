# -*- coding: utf-8 -*-

import os
import sys
import logging
import tempfile

def setup_logging(log_dir=None, log_file="tyrano_patcher.log"):
    """
    设置日志系统，支持控制台和文件输出
    
    Args:
        log_dir: 日志目录路径，None表示使用默认目录
        log_file: 日志文件名
        
    Returns:
        logging.Logger: 配置好的根logger
    """
    if log_dir is None:
        # 使用用户主目录下的 .tyranopatcher 子目录
        log_dir = os.path.join(os.path.expanduser("~"), ".tyranopatcher")
    
    log_path = os.path.join(log_dir, log_file)
    
    # 配置日志格式
    formatter = logging.Formatter(
        '%(asctime)s - %(levelname)-8s - %(name)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # 创建根logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)
    
    # 清除已有的handler，避免重复
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # 控制台处理器（始终可用）
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)
    
    # 尝试创建日志目录和文件处理器
    file_handler = None
    log_dirs_to_try = [
        log_dir,  # 用户指定的目录
        os.path.join(os.path.expanduser("~"), ".tyranopatcher"),  # 用户主目录
        "./logs",  # 当前目录下的logs文件夹
        "."  # 当前目录
    ]
    
    for try_dir in log_dirs_to_try:
        try:
            os.makedirs(try_dir, exist_ok=True)
            test_file = os.path.join(try_dir, ".write_test")
            with open(test_file, 'w') as f:
                f.write("test")
            os.remove(test_file)
            
            # 目录可写，尝试创建日志文件
            try_log_path = os.path.join(try_dir, log_file)
            file_handler = logging.FileHandler(try_log_path, encoding='utf-8', mode='a')
            file_handler.setLevel(logging.DEBUG)
            file_handler.setFormatter(formatter)
            root_logger.addHandler(file_handler)
            
            print(f"Logging to file: {try_log_path}")
            break  # 成功创建，退出循环
            
        except PermissionError as e:
            print(f"Warning: No permission to write to {try_dir}: {e}")
        except OSError as e:
            print(f"Warning: Cannot create log directory {try_dir}: {e}")
        except Exception as e:
            print(f"Warning: Unexpected error with log directory {try_dir}: {e}")
    
    if file_handler is None:
        print("Warning: Could not create log file in any location. Logging to console only.")
        print("Log directories tried:")
        for try_dir in log_dirs_to_try:
            print(f"  - {try_dir}")
    
    return root_logger
