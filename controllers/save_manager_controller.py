# -*- coding: utf-8 -*-
"""
存档管理器控制器模块

封装存档管理相关的业务逻辑，解耦GUI代码。
"""

import os
import logging
from typing import Optional, Callable

from core.save_service import SaveService

logger = logging.getLogger(__name__)


class SaveManagerController:
    """
    存档管理器控制器
    
    负责处理存档的扫描、备份、还原、删除等业务逻辑。
    将GUI代码与业务逻辑分离，提高代码可维护性。
    """
    
    # 存档目录候选名称
    SAVE_DIR_CANDIDATES = ["_storage", "save", "SaveData", "UserData"]
    
    def __init__(self, save_service: SaveService, log_callback: Optional[Callable] = None):
        """
        初始化存档管理器控制器
        
        Args:
            save_service: SaveService 实例
            log_callback: 日志回调函数
        """
        self.save_service = save_service
        self.log_callback = log_callback
    
    def set_log_callback(self, callback: Callable) -> None:
        """设置日志回调"""
        self.log_callback = callback
    
    def _log(self, message: str, level: str = "info") -> None:
        """记录日志"""
        if self.log_callback:
            self.log_callback(message)
        if level == "error":
            logger.error(message)
        elif level == "warning":
            logger.warning(message)
        else:
            logger.info(message)
    
    def scan_save_directory(self) -> Optional[str]:
        """
        扫描并返回游戏存档目录
        
        Returns:
            存档目录路径，未找到返回 None
        """
        for candidate in self.SAVE_DIR_CANDIDATES:
            path = os.path.abspath(candidate)
            if os.path.exists(path) and os.path.isdir(path):
                self._log(f"Found save directory: {path}")
                return path
        return None
    
    def scan_backups(self, save_root: str, backup_dir: str) -> list:
        """
        扫描备份目录
        
        Args:
            save_root: 游戏存档根目录
            backup_dir: 备份存储目录
            
        Returns:
            备份列表 [(display_name, fullpath, is_zip), ...]
        """
        backups = []
        dirs_to_scan = {save_root, backup_dir}
        
        for d_path in dirs_to_scan:
            if not os.path.exists(d_path):
                continue
            try:
                for d in os.listdir(d_path):
                    fp = os.path.join(d_path, d)
                    if os.path.isdir(fp) and d.startswith("Backup_"):
                        self._add_backup_to_list(backups, d, fp, is_zip=False)
                    elif os.path.isfile(fp) and d.startswith("Backup_") and d.endswith(".zip"):
                        self._add_backup_to_list(backups, d, fp, is_zip=True)
            except Exception as e:
                logger.debug(f"Error scanning {d_path}: {e}")
        
        # 去重并按时间倒序排序
        unique_backups = {}
        for name, fp, is_zip in backups:
            if name not in unique_backups:
                unique_backups[name] = (name, fp, is_zip)
        
        return sorted(unique_backups.values(), reverse=True)
    
    def _add_backup_to_list(self, list_ref: list, filename: str, fullpath: str, is_zip: bool) -> None:
        """解析备份名称并添加到列表"""
        try:
            name_part = filename.replace(".zip", "")
            ts = name_part[len("Backup_"):]
            if len(ts) >= 14:
                if len(ts) == 14:
                    display_name = f"{ts[:4]}-{ts[4:6]}-{ts[6:8]} {ts[8:10]}:{ts[10:12]}:{ts[12:14]}"
                else:
                    display_name = name_part
            else:
                display_name = name_part
            list_ref.append((display_name, fullpath, is_zip))
        except Exception as e:
            logger.debug(f"Error parsing backup name '{filename}': {e}")
            list_ref.append((filename, fullpath, is_zip))
    
    def get_backup_path(self, backup_dir: str) -> str:
        """
        获取备份存储目录
        
        Args:
            backup_dir: 配置的备份目录
            
        Returns:
            实际使用的备份目录路径
        """
        if not backup_dir or not os.path.exists(backup_dir):
            default_dir = os.path.join(os.path.expanduser("~"), ".tyranopatcher", "backups")
            os.makedirs(default_dir, exist_ok=True)
            return default_dir
        return backup_dir
    
    def execute_backup(self, save_dir: str, backup_dir: str, use_zip: bool, **kwargs) -> bool:
        """
        执行存档备份
        
        Args:
            save_dir: 存档目录
            backup_dir: 备份目录
            use_zip: 是否使用ZIP格式
            **kwargs: 其他参数，如 _check_cancelled
            
        Returns:
            是否成功
        """
        try:
            result = self.save_service.backup_save(save_dir, backup_dir, use_zip, **kwargs)
            self._log(f"Backup created: {result}")
            return True
        except Exception as e:
            self._log(f"Backup error: {e}", "error")
            return False
    
    def execute_restore(self, save_dir: str, backup_src: str, **kwargs) -> tuple[bool, str]:
        """
        执行存档还原
        
        Args:
            save_dir: 目标存档目录
            backup_src: 备份源路径
            **kwargs: 其他参数，如 _check_cancelled
            
        Returns:
            (是否成功, 错误消息)
        """
        try:
            self.save_service.restore_save(save_dir, backup_src, **kwargs)
            self._log("Restore completed")
            return True, ""
        except Exception as e:
            logger.error(f"Restore error: {e}")
            return False, str(e)
    
    def execute_delete(self, backup_src: str, **kwargs) -> bool:
        """
        执行备份删除
        
        Args:
            backup_src: 要删除的备份路径
            **kwargs: 其他参数，如 _check_cancelled
            
        Returns:
            是否成功
        """
        try:
            self.save_service.delete_backup(backup_src, **kwargs)
            self._log(f"Deleted: {backup_src}")
            return True
        except Exception as e:
            self._log(f"Delete error: {e}", "error")
            return False
    
    def migrate_backups(self, old_dir: str, new_dir: str, **kwargs) -> tuple[int, int]:
        """
        迁移备份目录
        
        Args:
            old_dir: 旧备份目录
            new_dir: 新备份目录
            **kwargs: 其他参数，如 _check_cancelled
            
        Returns:
            (成功数量, 失败数量)
        """
        try:
            return self.save_service.migrate_backups(old_dir, new_dir, **kwargs)
        except Exception as e:
            self._log(f"Migration error: {e}", "error")
            return 0, 0