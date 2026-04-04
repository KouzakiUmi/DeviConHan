# -*- coding: utf-8 -*-

import os
import logging
from configparser import ConfigParser

from utils.paths import get_resource_path

logger = logging.getLogger(__name__)


class AppConfig:
    """
    配置管理类，封装 ConfigParser，从 config.ini 读取配置
    """
    
    def __init__(self, config_file=None):
        """
        初始化配置管理器
        
        Args:
            config_file: 配置文件路径，None 则使用默认路径
        """
        if config_file is None:
            self.config_file = get_resource_path("config.ini")
        else:
            self.config_file = config_file
        
        self.config = ConfigParser()
        self.config.read(self.config_file, encoding="utf-8")
        
        logger.debug(f"Config loaded from: {self.config_file}")
    
    def get(self, section, key, fallback=None, **kwargs):
        """
        获取配置值（字符串）
        
        Args:
            section: 配置节名
            key: 配置键名
            fallback: 默认值
            **kwargs: 传递给 ConfigParser.get 的额外参数
            
        Returns:
            str: 配置值
        """
        return self.config.get(section, key, fallback=fallback, **kwargs)
    
    def get_int(self, section, key, fallback=0):
        """
        获取配置值（整数）
        
        Args:
            section: 配置节名
            key: 配置键名
            fallback: 默认值
            
        Returns:
            int: 配置值
        """
        try:
            return self.config.getint(section, key)
        except Exception:
            return fallback
    
    def get_bool(self, section, key, fallback=False):
        """
        获取配置值（布尔值）
        
        Args:
            section: 配置节名
            key: 配置键名
            fallback: 默认值
            
        Returns:
            bool: 配置值
        """
        try:
            return self.config.getboolean(section, key)
        except Exception:
            return fallback
    
    def get_list(self, section, key, fallback=None):
        """
        获取配置值（列表），支持多行值
        
        Args:
            section: 配置节名
            key: 配置键名
            fallback: 默认值
            
        Returns:
            list: 配置值列表
        """
        value = self.get(section, key, fallback=fallback)
        if value is not None:
            if isinstance(value, list):
                return value
            return [line.strip() for line in str(value).split("\n") if line.strip()]
        return []
    
    # ========== 便捷访问属性 ==========
    
    @property
    def auto_target_exe(self):
        """游戏可执行文件名"""
        return self.get("main", "AUTO_TARGET_EXE", fallback="DevilConnection.exe")
    
    @property
    def fuse_sentinel(self):
        """Fuse 校验特征码"""
        sentinel = self.get("main", "FUSE_SENTINEL", fallback="dL7pKGdnNz796PbbjQWNKmHXBZaB9tsX")
        return sentinel.encode() if isinstance(sentinel, str) else sentinel
    
    @property
    def backup_prefix(self):
        """备份文件名前缀"""
        return self.get("main", "BACKUP_PREFIX", fallback="Backup_")
    
    @property
    def patch_info_file(self):
        """补丁信息文件名"""
        return self.get("main", "PATCH_INFO_FILE", fallback=".patch_info")
    
    @property
    def patch_meta_file(self):
        """补丁元数据文件名"""
        return self.get("main", "PATCH_META_FILE", fallback=".patch_meta")
    
    @property
    def time_diff_threshold_days(self):
        """旧补丁时间阈值（天）"""
        return self.get_int("main", "TIME_DIFF_THRESHOLD_DAYS", fallback=3)
    
    @property
    def check_files_for_update(self):
        """Steam 更新检测文件列表"""
        return self.get_list("files", "CHECK_FILES_FOR_UPDATE")
    
    @property
    def stable_files_for_validation(self):
        """稳定文件列表（用于验证备份完整性）"""
        return self.get_list("files", "STABLE_FILES_FOR_VALIDATION")
    
    @property
    def resource_dir(self):
        """资源目录名"""
        return self.get("main", "RESOURCE_DIR", fallback="resources")
    
    @property
    def app_name(self):
        """程序名称"""
        return self.get("main", "APP_NAME", fallback="TyranoV8_Patcher")


# Global config instance - 延迟初始化
_config_instance = None


def get_config():
    """
    获取全局配置实例（单例模式）
    
    Returns:
        AppConfig: 配置实例
    """
    global _config_instance
    if _config_instance is None:
        _config_instance = AppConfig()
    return _config_instance
