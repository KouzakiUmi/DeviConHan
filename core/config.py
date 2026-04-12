# -*- coding: utf-8 -*-
"""
恶魔链接补丁工具 - 配置管理模块

提供配置文件读取、验证和管理功能。
包含配置验证功能，确保配置项的有效性和一致性。
"""

import os
import logging
import shutil
import threading
import time
from configparser import ConfigParser
from contextlib import contextmanager
from typing import Optional, List, Any, Dict, Tuple

from utils.paths import get_resource_path, get_user_config_path
from utils.constants import TIME_DIFF_THRESHOLD_MAX_DAYS, MAX_BACKUP_PREFIX_LENGTH

logger = logging.getLogger(__name__)

# 线程锁，用于保护配置单例的初始化
_config_lock = threading.Lock()

# 读写锁，用于保护配置的并发访问
_config_rw_lock = threading.RLock()


class AppConfig:
    """
    配置管理类，封装 ConfigParser，从 config.ini 读取配置

    线程安全特性：
    - 使用RLock支持读写锁
    - validate_config使用配置快照避免长时间持有锁
    - 所有公共方法自动加锁
    """

    def __init__(self, config_file: Optional[str] = None):
        """
        初始化配置管理器

        Args:
            config_file: 配置文件路径，None 则使用默认路径
        """
        self._lock = _config_rw_lock
        self._config_snapshot: Optional[Dict[str, Any]] = None
        self._snapshot_version = 0
        self._snapshot_time = 0.0

        with self._acquire_lock():
            user_config_path_obj = get_user_config_path()
            default_config_path = get_resource_path("config.ini")
            user_config_dir = os.path.dirname(user_config_path_obj)

            if config_file is None:
                # 确保用户目录存在
                os.makedirs(user_config_dir, exist_ok=True)

                if not os.path.exists(user_config_path_obj) and os.path.exists(
                    default_config_path
                ):
                    try:
                        shutil.copy2(default_config_path, user_config_path_obj)
                        logger.info(f"Copied default config to {user_config_path_obj}")
                    except Exception as e:
                        logger.error(f"Failed to copy config to user dir: {e}")

                if os.path.exists(user_config_path_obj):
                    self.config_file = user_config_path_obj
                else:
                    self.config_file = default_config_path
            else:
                self.config_file = config_file

            self.config: ConfigParser = ConfigParser()
            self.config.read(self.config_file, encoding="utf-8")

            logger.debug(f"Config loaded from: {self.config_file}")

    @contextmanager
    def _acquire_lock(self):
        """线程安全锁上下文管理器（RLock 可重入，读写均通过同一锁保护）"""
        with self._lock:
            yield

    def _invalidate_snapshot(self) -> None:
        """使配置快照失效"""
        self._config_snapshot = None
        self._snapshot_version += 1

    def invalidate_cache(self) -> None:
        """
        使配置缓存失效（公共接口）

        当外部代码通过 config.set() 修改配置后，应调用此方法
        使内部快照缓存失效，确保后续读取获取最新值。
        """
        self._invalidate_snapshot()

    def _get_config_snapshot(self) -> Dict[str, Any]:
        """获取配置快照（线程安全，带TTL刷新）
        """
        with self._acquire_lock():
            current_time = time.time()
            # 在锁内做 TTL 检查，确保检查和更新的原子性
            if self._config_snapshot is not None and (
                current_time - self._snapshot_time <= 2.0
            ):
                return self._config_snapshot

            self._config_snapshot = {
                "resource_dir": self.get("main", "RESOURCE_DIR", fallback="resources"),
                "app_name": self.get("main", "APP_NAME", fallback="TyranoV8_Patcher"),
                "time_threshold": self.get_int(
                    "main", "TIME_DIFF_THRESHOLD_DAYS", fallback=3
                ),
                "backup_prefix": self.get("main", "BACKUP_PREFIX", fallback="Backup_"),
                "patch_info_file": self.get(
                    "main", "PATCH_INFO_FILE", fallback=".patch_info"
                ),
                "patch_meta_file": self.get(
                    "main", "PATCH_META_FILE", fallback=".patch_meta"
                ),
                "target_asar_name": self.get(
                    "main", "TARGET_ASAR_NAME", fallback="app.asar"
                ),
                "temp_patch_dir": self.get(
                    "main", "TEMP_PATCH_DIR", fallback="temp_patch"
                ),
                "patch_zip_name": self.get(
                    "main", "PATCH_ZIP_NAME", fallback="Patch.zip"
                ),
                "patch_dir_name": self.get("main", "PATCH_DIR_NAME", fallback="Patch"),
                "fuse_sentinel": self.get(
                    "main",
                    "FUSE_SENTINEL",
                    fallback="dL7pKGdnNz796PbbjQWNKmHXBZaB9tsX",
                ),
                "fuse_header_length": self.get_int(
                    "main", "FUSE_WIRE_HEADER_LENGTH", fallback=34
                ),
                "fuse_asar_offset": self.get_int(
                    "main", "FUSE_ASAR_INTEGRITY_OFFSET", fallback=4
                ),
                "check_files": self.get_list("files", "CHECK_FILES_FOR_UPDATE"),
                "stable_files": self.get_list("files", "STABLE_FILES_FOR_VALIDATION"),
            }
            self._snapshot_time = current_time
            return self._config_snapshot

    def reload(self) -> None:
        """
        重新加载配置文件（热重载）
        线程安全：自动使旧快照失效
        """
        with self._acquire_lock():
            try:
                self.config = ConfigParser()
                self.config.read(self.config_file, encoding="utf-8")
                self._invalidate_snapshot()
                logger.info(f"Config reloaded from: {self.config_file}")
            except Exception as e:
                logger.error(f"Failed to reload config: {e}")

    def get(self, section: str, key: str, fallback: str = "", **kwargs) -> str:
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
        with self._acquire_lock():
            result = self.config.get(section, key, fallback=fallback, **kwargs)
            return result if result is not None else fallback

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
        with self._acquire_lock():
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
        with self._acquire_lock():
            try:
                return self.config.getboolean(section, key)
            except Exception:
                return fallback

    def get_list(
        self, section: str, key: str, fallback: Optional[List[str]] = None
    ) -> List[str]:
        """
        获取配置值（列表），支持多行值

        Args:
            section: 配置节名
            key: 配置键名
            fallback: 默认值

        Returns:
            list: 配置值列表
        """
        with self._acquire_lock():
            raw_value = self.config.get(section, key, fallback="")
        if raw_value:
            return [line.strip() for line in raw_value.split("\n") if line.strip()]
        return fallback if fallback is not None else []

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
            # 定义特殊处理的配置项
            bool_keys = {"use_zip", "show_console"}
            if key in bool_keys:
                fallback = (
                    bool(default)
                    if default is not None
                    else (True if key == "use_zip" else False)
                )
                return self.get_bool("preferences", key, fallback=fallback)

            # 其他配置项都作为字符串处理
            fallback_map = {
                "platform": str(default) if default else "win",
                "language": str(default) if default else "en",
            }
            fallback = fallback_map.get(key, str(default) if default else "")
            return self.get("preferences", key, fallback=fallback)

        except Exception:
            return default

    def set_main_config(self, key: str, value: Any) -> bool:
        """
        设置 [main] 配置节的键值（线程安全）

        Args:
            key: 配置键名（自动转为大写保持与原配置文件一致）
            value: 配置值

        Returns:
            bool: 是否成功设置并保存
        """
        try:
            with self._acquire_lock():
                if not self.config.has_section("main"):
                    self.config.add_section("main")
                self.config.set("main", str(key).upper(), str(value))
                self._invalidate_snapshot()
            return self.save()
        except Exception as e:
            logger.warning(f'Failed to set main config value for "{key}": {e}')
            return False

    def set_gui_config(self, key: str, value: Any) -> bool:
        """
        设置 GUI 配置值（线程安全）

        Args:
            key: 配置键名
            value: 配置值

        Returns:
            bool: 是否成功设置
        """
        try:
            with self._acquire_lock():
                if not self.config.has_section("preferences"):
                    self.config.add_section("preferences")
                self.config.set("preferences", key, str(value))
                self._invalidate_snapshot()
            return self.save()
        except Exception as e:
            logger.warning(f'Failed to set config value for "{key}": {e}')
            return False

    def set_gui_config_batch(self, config_dict: Dict[str, Any]) -> bool:
        """
        批量设置 GUI 配置值（原子操作）

        Args:
            config_dict: 配置键值对字典

        Returns:
            bool: 是否成功设置
        """
        with self._acquire_lock():
            try:
                if not self.config.has_section("preferences"):
                    self.config.add_section("preferences")
                for key, value in config_dict.items():
                    self.config.set("preferences", key, str(value))
                # 统一写入（save() 内部也会获取写锁，但 RLock 支持重入）
                return self.save()
            except Exception as e:
                logger.warning(f"Failed to batch set config values: {e}")
                return False

    def save(self) -> bool:
        """
        保存配置到文件（原子写入）
        线程安全：自动使快照失效

        Returns:
            bool: 是否成功保存
        """
        with self._acquire_lock():
            temp_file = None
            try:
                config_dir = os.path.dirname(self.config_file)
                if config_dir and not os.path.exists(config_dir):
                    os.makedirs(config_dir, exist_ok=True)

                temp_file = self.config_file + ".tmp"
                # 使用 0o600 权限创建临时文件，只有所有者可读写
                flags = os.O_WRONLY | os.O_CREAT | os.O_TRUNC
                fd = os.open(temp_file, flags, 0o600)
                with os.fdopen(fd, "w", encoding="utf-8") as f:
                    self.config.write(f)
                    # 强制刷新到磁盘
                    f.flush()
                    os.fsync(f.fileno())

                os.replace(temp_file, self.config_file)
                self._invalidate_snapshot()

                logger.debug(f"Config saved to: {self.config_file}")
                return True
            except Exception as e:
                logger.error(f"Failed to save config: {e}")
                if temp_file and os.path.exists(temp_file):
                    try:
                        os.remove(temp_file)
                    except Exception:
                        pass
                return False

    # ========== 便捷访问属性 ==========

    @property
    def auto_target_exe(self):
        """游戏可执行文件名"""
        return self.get("main", "AUTO_TARGET_EXE", fallback="DevilConnection.exe")

    @property
    def fuse_sentinel(self):
        """Fuse 校验特征码"""
        sentinel = self.get(
            "main", "FUSE_SENTINEL", fallback="dL7pKGdnNz796PbbjQWNKmHXBZaB9tsX"
        )
        if isinstance(sentinel, bytes):
            return sentinel
        return (
            sentinel.encode("utf-8")
            if isinstance(sentinel, str)
            else str(sentinel).encode("utf-8")
        )

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
    def target_asar_name(self):
        """目标 asar 文件名"""
        return self.get("main", "TARGET_ASAR_NAME", fallback="app.asar")

    @property
    def temp_patch_dir(self):
        """临时补丁解压目录名"""
        return self.get("main", "TEMP_PATCH_DIR", fallback="temp_patch")

    @property
    def patch_zip_name(self):
        """补丁压缩包文件名"""
        return self.get("main", "PATCH_ZIP_NAME", fallback="Patch.zip")

    @property
    def patch_dir_name(self):
        """补丁目录名"""
        return self.get("main", "PATCH_DIR_NAME", fallback="Patch")

    @property
    def app_name(self):
        """程序名称"""
        return self.get("main", "APP_NAME", fallback="TyranoV8_Patcher")

    # ================== 配置验证方法 ==================

    def validate_config(self) -> Tuple[bool, List[str], List[str]]:
        """
        验证配置文件的有效性（线程安全版本）

        使用配置快照避免长时间持有锁，提高并发性能。

        Returns:
            Tuple[bool, List[str], List[str]]: (是否有效, 错误列表, 警告列表)
            - 第一个元素为 False 表示存在必须修复的错误
            - 错误列表与警告列表分开返回，调用方可按严重程度分别处理
        """
        errors = []
        warnings = []

        # 第一步：快速获取配置快照（持有锁时间最短）
        with self._acquire_lock():
            # 验证必需的配置节
            required_sections = ["main", "files"]
            for section in required_sections:
                if not self.config.has_section(section):
                    errors.append(f"Missing required section: [{section}]")

            # 验证必需的配置项
            required_items = {
                "main": ["RESOURCE_DIR", "APP_NAME"],
                "files": ["CHECK_FILES_FOR_UPDATE"],
            }

            for section, items in required_items.items():
                for item in items:
                    if not self.config.has_option(section, item):
                        errors.append(f"Missing required option [{section}] {item}")

            # 获取配置快照版本
            snapshot = self._get_config_snapshot()
            config_file_path = self.config_file

        # 第二步：使用快照进行验证（无锁）
        # 验证资源配置目录路径
        try:
            resource_dir = snapshot.get("resource_dir", "")
            if not resource_dir:
                errors.append("RESOURCE_DIR cannot be empty")
            elif not os.path.exists(resource_dir):
                warnings.append(f"Resource directory does not exist: {resource_dir}")
        except Exception as e:
            errors.append(f"Error validating RESOURCE_DIR: {e}")

        # 验证时间阈值
        try:
            time_threshold = snapshot.get("time_threshold", 3)
            if time_threshold < 0:
                errors.append(
                    f"TIME_DIFF_THRESHOLD_DAYS cannot be negative: {time_threshold}"
                )
            elif time_threshold > TIME_DIFF_THRESHOLD_MAX_DAYS:
                warnings.append(
                    f"TIME_DIFF_THRESHOLD_DAYS is unusually large: {time_threshold}"
                )
        except Exception as e:
            errors.append(f"Error validating TIME_DIFF_THRESHOLD_DAYS: {e}")

        # 验证配置文件路径
        try:
            if not os.path.exists(config_file_path):
                errors.append(f"Config file does not exist: {config_file_path}")
        except Exception as e:
            errors.append(f"Error validating config file path: {e}")

        # 验证备份前缀
        try:
            backup_prefix = snapshot.get("backup_prefix", "")
            if not backup_prefix:
                warnings.append("BACKUP_PREFIX is empty, could cause issues")
            elif len(backup_prefix) > MAX_BACKUP_PREFIX_LENGTH:
                warnings.append("BACKUP_PREFIX is too long, may cause issues")
        except Exception as e:
            warnings.append(f"Error validating BACKUP_PREFIX: {e}")

        # 验证Fuse校验码
        try:
            fuse_sentinel = snapshot.get("fuse_sentinel", "")
            if not fuse_sentinel:
                warnings.append("FUSE_SENTINEL is empty")
        except Exception as e:
            warnings.append(f"Error validating FUSE_SENTINEL: {e}")

        # 验证文件列表
        try:
            check_files = snapshot.get("check_files", [])
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

        return (len(errors) == 0, errors, warnings)

    def validate_required_directory(
        self, dir_path: str, dir_type: str = "directory"
    ) -> bool:
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
