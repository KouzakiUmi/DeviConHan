# -*- coding: utf-8 -*-
"""
工具函数模块 - 通用清理功能

提供临时目录强制清理等通用工具函数。
"""

import os
import shutil
import stat
import logging
import time
import subprocess
import sys

logger = logging.getLogger(__name__)


def force_cleanup_dir(temp_dir: str, max_retries: int = 3) -> bool:
    """
    强制清理临时目录（处理只读文件和目录）
    
    Args:
        temp_dir: 临时目录路径
        max_retries: 最大重试次数
        
    Returns:
        bool: 是否成功清理
    """
    for retry in range(max_retries):
        try:
            # 检查目录是否存在
            if not os.path.exists(temp_dir):
                logger.debug(f"Temp directory already removed: {temp_dir}")
                return True
            
            # 递归修改所有文件和目录的只读属性
            for root, dirs, files in os.walk(temp_dir):
                for name in files:
                    file_path = os.path.join(root, name)
                    try:
                        os.chmod(file_path, stat.S_IWRITE | stat.S_IRUSR)
                    except Exception:
                        pass
                for name in dirs:
                    dir_path = os.path.join(root, name)
                    try:
                        os.chmod(dir_path, stat.S_IWRITE | stat.S_IRUSR)
                    except Exception:
                        pass
            
            # 尝试删除整个目录
            shutil.rmtree(temp_dir, ignore_errors=True)
            
            # 如果仍然存在，尝试逐个删除
            if os.path.exists(temp_dir):
                for root, dirs, files in os.walk(temp_dir, topdown=False):
                    for name in files:
                        try:
                            os.remove(os.path.join(root, name))
                        except Exception:
                            pass
                    for name in dirs:
                        try:
                            os.rmdir(os.path.join(root, name))
                        except Exception:
                            pass
                # 最后尝试删除根目录
                try:
                    os.rmdir(temp_dir)
                except Exception:
                    pass
            
            # 验证是否成功删除
            if not os.path.exists(temp_dir):
                logger.info(f"Successfully cleaned up temporary directory: {temp_dir}")
                return True
            else:
                logger.warning(f"Retry {retry + 1}/{max_retries}: Temp directory still exists: {temp_dir}")
                if retry < max_retries - 1:
                    time.sleep(0.5)  # 等待后重试
                    
        except Exception as cleanup_err:
            logger.warning(f"Cleanup attempt {retry + 1} failed: {cleanup_err}")
            if retry < max_retries - 1:
                time.sleep(0.5)
    
    # 最后尝试：使用 Windows 命令强制删除
    if os.path.exists(temp_dir) and sys.platform.startswith("win"):
        try:
            result = subprocess.run(
                ['cmd', '/c', 'rmdir', '/s', '/q', temp_dir],
                capture_output=True,
                timeout=5,
                encoding='utf-8'
            )
            if result.returncode != 0:
                logger.warning(f"System command failed with code {result.returncode}: {result.stderr}")
            else:
                logger.info(f"Force cleanup via system command: {temp_dir}")
            return not os.path.exists(temp_dir)
        except subprocess.TimeoutExpired:
            logger.warning(f"System command timed out for: {temp_dir}")
        except Exception as e:
            logger.warning(f"System force cleanup also failed: {e}")
    
    return not os.path.exists(temp_dir)
