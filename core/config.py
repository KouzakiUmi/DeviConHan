# -*- coding: utf-8 -*-
"""
恶魔链接补丁工具 - 配置管理模块

提供配置文件读取、验证和管理功能。
包含配置验证功能，确保配置项的有效性和一致性。
"""

import os
import logging
import threading
from configparser import ConfigParser
from typing import Optional, List, Any, Union

from utils.paths import get_resource_path

logger = logging.getLogger(__name__)

# 线程锁，用于保护配置单例的初始化
_config_lock = threading.Lock()


class AppConfig:
    """
    配置管理类，封装 ConfigParser，从 config.ini 读取配置
    """
    
    def __init__(self, config_file: Optional[str] = None):
        """
        初始化配置管理器
        
        Args:
            config_file: 配置文件路径，None 则使用默认路径
        """
        user_config_dir = os.path.join(os.path.expanduser("~"), ".tyranopatcher")
        user_config_path = os.path.join(user_config_dir, "config.ini")
        default_config_path = get_resource_path("config.ini")
        
        if config_file is None:
            # 确保用户目录存在
            os.makedirs(user_config_dir, exist_ok=True)
            
            if not os.path.exists(user_config_path) and os.path.exists(default_config_path):
                import shutil
                try:
                    shutil.copy2(default_config_path, user_config_path)
                    logger.info(f"Copied default config to {user_config_path}")
                except Exception as e:
                    logger.error(f"Failed to copy config to user dir: {e}")
                    
            if os.path.exists(user_config_path):
                self.config_file = user_config_path
            else:
                self.config_file = default_config_path
        else:
            self.config_file = config_file
        
        self.config: ConfigParser = ConfigParser()
        self.config.read(self.config_file, encoding="utf-8")
        
        logger.debug(f"Config loaded from: {self.config_file}")
    
    def reload(self) -> None:
        """
        重新加载配置文件（热重载）
        """
        try:
            self.config = ConfigParser()
            self.config.read(self.config_file, encoding="utf-8")
            logger.info(f"Config reloaded from: {self.config_file}")
        except Exception as e:
            logger.error(f"Failed to reload config: {e}")
    
    def get(self, section: str, key: str, fallback: Optional[str] = None, **kwargs) -> str:
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
    
    def get_int(self, section: str, key: str, fallback: int = 0) -> int:
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
    
    def get_bool(self, section: str, key: str, fallback: bool = False) -> bool:
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
    
    def get_list(self, section: str, key: str, fallback: Optional[List[str]] = None) -> List[str]:
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
    
    def get_gui_config(self, key: str, default: Optional[Any] = None) -> Any:
        """
        获取 GUI 配置值
        
        Args:
            key: 配置键名
            default: 默认值
            
        Returns:
            配置值或默认值
        """
        try:
            if key == "use_zip":
                return self.get_bool("preferences", key, fallback=bool(default) if default is not None else True)
            elif key == "platform":
                return self.get("preferences", key, fallback=str(default) if default else "win")
            elif key == "language":
                return self.get("preferences", key, fallback=str(default) if default else "en")
            else:
                return self.get("preferences", key, fallback=str(default) if default else "")
        except Exception:
            return default
    
    def set_gui_config(self, key: str, value: Any) -> bool:
        """
        设置 GUI 配置值
        
        Args:
            key: 配置键名
            value: 配置值
            
        Returns:
            bool: 是否成功设置
        """
        try:
            if not self.config.has_section("preferences"):
                if not self.config.add_section("preferences"):
                    logger.warning(f"Failed to add section: preferences")
                    return False
            self.config.set("preferences", key, str(value))
            return True
        except Exception as e:
            logger.warning(f"Failed to set config value for \"{key}\": {e}")
            return False
    
    # ========== 便捷访问属性 ==========
    
    @property
    def auto_target_exe(self):
        """游戏可执行文件名"""
        return self.get("main", "AUTO_TARGET_EXE", fallback="DevilConnection.exe")
    
    @property
    def fuse_sentinel(self):
        """Fuse 校验特征码"""
        sentinel = self.get("main", "FUSE_SENTINEL", fallback="dL7pKGdnNz796PbbjQWNKmHXBZaB9tsX")
        if isinstance(sentinel, bytes):
            return sentinel
        return sentinel.encode('utf-8') if isinstance(sentinel, str) else str(sentinel).encode('utf-8')
    
    @property
    def fuse_wire_header_length(self):
        """Fuse 线缆头部长度 (默认 34 = sentinel 32 + length 1 + version 1)"""
        return self.get_int("main", "FUSE_WIRE_HEADER_LENGTH", fallback=34)
    
    @property
    def fuse_asar_integrity_offset(self):
        """Asar Integrity 验证所在的 Fuse 索引偏移量"""
        return self.get_int("main", "FUSE_ASAR_INTEGRITY_OFFSET", fallback=4)
    
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
    
    # ================== 配置验证方法 ==================
    
    def validate_config(self) -> tuple[bool, list[str]]:
        """
        验证配置文件的有效性
        
        Returns:
            tuple[bool, list[str]]: (是否有效, 错误信息列表)
        """
        errors = []
        warnings = []
        
        # 验证必需的配置节
        required_sections = ["main", "files"]
        for section in required_sections:
            if not self.config.has_section(section):
                errors.append(f"Missing required section: [{section}]")
        
        # 验证必需的配置项
        required_items = {
            "main": ["RESOURCE_DIR", "APP_NAME"],
            "files": ["CHECK_FILES_FOR_UPDATE"]
        }
        
        for section, items in required_items.items():
            for item in items:
                if not self.config.has_option(section, item):
                    errors.append(f"Missing required option [{section}] {item}")
        
        # 验证资源配置目录路径
        try:
            resource_dir = self.resource_dir
            if not resource_dir:
                errors.append("RESOURCE_DIR cannot be empty")
            elif not os.path.exists(resource_dir):
                warnings.append(f"Resource directory does not exist: {resource_dir}")
        except Exception as e:
            errors.append(f"Error validating RESOURCE_DIR: {e}")
        
        # 验证时间阈值
        try:
            time_threshold = self.time_diff_threshold_days
            if time_threshold < 0:
                errors.append(f"TIME_DIFF_THRESHOLD_DAYS cannot be negative: {time_threshold}")
            elif time_threshold > 365:
                warnings.append(f"TIME_DIFF_THRESHOLD_DAYS is unusually large: {time_threshold}")
        except Exception as e:
            errors.append(f"Error validating TIME_DIFF_THRESHOLD_DAYS: {e}")
        
        # 验证配置文件路径
        try:
            if not os.path.exists(self.config_file):
                errors.append(f"Config file does not exist: {self.config_file}")
        except Exception as e:
            errors.append(f"Error validating config file path: {e}")
        
        # 验证备份前缀
        try:
            backup_prefix = self.backup_prefix
            if not backup_prefix:
                warnings.append("BACKUP_PREFIX is empty, could cause issues")
            elif len(backup_prefix) > 50:
                warnings.append("BACKUP_PREFIX is too long, may cause issues")
        except Exception as e:
            warnings.append(f"Error validating BACKUP_PREFIX: {e}")
        
        # 验证Fuse校验码
        try:
            fuse_sentinel = self.fuse_sentinel
            if not fuse_sentinel:
                warnings.append("FUSE_SENTINEL is empty")
        except Exception as e:
            warnings.append(f"Error validating FUSE_SENTINEL: {e}")
        
        # 验证文件列表
        try:
            check_files = self.check_files_for_update
            if not check_files:
                warnings.append("CHECK_FILES_FOR_UPDATE is empty")
        except Exception as e:
            warnings.append(f"Error validating CHECK_FILES_FOR_UPDATE: {e}")
        
        # 记录验证结果
        if errors:
            logger.error(f"Configuration validation failed: {errors}")
        if warnings:
            logger.warning(f"Configuration warnings: {warnings}")
        if not errors and not warnings:
            logger.info("Configuration validation passed")
        
        return (len(errors) == 0, errors + warnings)
    
    def validate_required_directory(self, dir_path: str, dir_type: str = "directory") -> bool:
        """
        验证必需目录是否存在
        
        Args:
            dir_path: 目录路径
            dir_type: 目录类型描述
            
        Returns:
            bool: 目录是否存在
        """
        if not dir_path:
            logger.error(f"{dir_type} path is empty")
            return False
        
        if not os.path.exists(dir_path):
            logger.error(f"{dir_type} does not exist: {dir_path}")
            return False
        
        if not os.path.isdir(dir_path):
            logger.error(f"{dir_type} is not a directory: {dir_path}")
            return False
        
        logger.debug(f"{dir_type} validated: {dir_path}")
        return True


# Global config instance - 延迟初始化
_config_instance: Optional[AppConfig] = None


def get_config() -> AppConfig:
    """
    获取全局配置实例（单例模式，线程安全）
    
    Returns:
        AppConfig: 配置实例
    """
    global _config_instance
    if _config_instance is None:
        with _config_lock:
            # 双重检查锁定模式
            if _config_instance is None:
                _config_instance = AppConfig()
    return _config_instance
