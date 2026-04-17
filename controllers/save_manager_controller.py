"""
存档管理器控制器模块

封装存档管理相关的业务逻辑，解耦GUI代码。
"""

import logging
import os
from typing import Callable, Iterable, Optional, Tuple, Union

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
        from core.bootstrap import get_runtime_game_path

        runtime_game_path = get_runtime_game_path()
        base_dir = runtime_game_path or os.path.abspath(".")

        for candidate in self.SAVE_DIR_CANDIDATES:
            path = os.path.join(base_dir, candidate)
            if os.path.exists(path) and os.path.isdir(path):
                self._log(f"Found save directory: {path}")
                return path

        # 仅在没有运行时游戏目录时，回退到当前工作目录查找旧版存档结构
        if runtime_game_path is None and base_dir != os.path.abspath("."):
            for candidate in self.SAVE_DIR_CANDIDATES:
                path = os.path.abspath(candidate)
                if os.path.exists(path) and os.path.isdir(path):
                    self._log(f"Found save directory (in CWD fallback): {path}")
                    return path

        return None

    def scan_backups(self, save_root: str, backup_dirs: Union[str, Iterable[str]]) -> list:
        """
        扫描备份目录

        Args:
            save_root: 游戏存档根目录
            backup_dirs: 一个或多个备份存储目录

        Returns:
            备份列表 [(display_name, fullpath, is_zip), ...]
        """
        backups = []
        if isinstance(backup_dirs, (str, os.PathLike)):
            configured_dirs = {os.fspath(backup_dirs)}
        else:
            configured_dirs = {os.fspath(path) for path in backup_dirs if path}

        dirs_to_scan = {save_root, *configured_dirs}

        from core.config import get_config

        prefix = get_config().backup_prefix

        for d_path in dirs_to_scan:
            if not os.path.exists(d_path):
                continue
            try:
                with os.scandir(d_path) as entries:
                    for entry in entries:
                        d = entry.name
                        if not d.startswith(prefix):
                            continue

                        fp = entry.path
                        if entry.is_dir():
                            self._add_backup_to_list(backups, d, fp, is_zip=False, prefix=prefix)
                        elif entry.is_file() and d.endswith(".zip"):
                            self._add_backup_to_list(backups, d, fp, is_zip=True, prefix=prefix)
            except Exception as e:
                logger.debug(f"Error scanning {d_path}: {e}")

        # 去重并按时间倒序排序
        # 先按路径去重（防止同一个文件被扫描两次），使用路径作为唯一键
        seen_paths: dict = {}
        for name, fp, is_zip in backups:
            if fp not in seen_paths:
                seen_paths[fp] = (name, fp, is_zip)

        deduped = list(seen_paths.values())

        # 若多个不同路径的备份拥有相同的显示名，则在名称后附加父目录名以区分
        name_count: dict = {}
        for name, _fp, _is_zip in deduped:
            name_count[name] = name_count.get(name, 0) + 1

        result = []
        for name, fp, is_zip in deduped:
            if name_count[name] > 1:
                parent = os.path.basename(os.path.dirname(fp))
                display = f"{name} ({parent})"
            else:
                display = name
            result.append((display, fp, is_zip))

        return sorted(result, reverse=True)

    def _add_backup_to_list(
        self,
        list_ref: list,
        filename: str,
        fullpath: str,
        is_zip: bool,
        prefix: str = "Backup_",
    ) -> None:
        """解析备份名称并添加到列表

        时间戳格式支持两种：
        - 14 位旧格式: YYYYMMDDHHMMSS
        - 17 位新格式: YYYYMMDDHHMMSSmmm（含毫秒，由 save_service.backup_save 生成）
        """
        try:
            name_part = filename.replace(".zip", "")
            ts = name_part[len(prefix) :]
            if len(ts) >= 17:
                # 新格式：含毫秒（17位）
                display_name = (
                    f"{ts[:4]}-{ts[4:6]}-{ts[6:8]} {ts[8:10]}:{ts[10:12]}:{ts[12:14]}.{ts[14:17]}"
                )
            elif len(ts) == 14:
                # 旧格式：无毫秒（14位）
                display_name = f"{ts[:4]}-{ts[4:6]}-{ts[6:8]} {ts[8:10]}:{ts[10:12]}:{ts[12:14]}"
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

    def execute_restore(self, save_dir: str, backup_src: str, **kwargs) -> Tuple[bool, str]:
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

    def migrate_backups(self, old_dir: str, new_dir: str, **kwargs) -> Tuple[int, int]:
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
