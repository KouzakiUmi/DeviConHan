"""
存档服务模块，负责执行存档的备份、还原、迁移、删除等业务逻辑
"""

import datetime
import logging
import os
import shutil
import tempfile
import zipfile
from typing import Any, Callable, Optional, Tuple

from utils.constants import (
    TEMP_BACKUP_PREFIX,
    TEMP_FILE_SUFFIX,
)
from utils.error_handler import ErrorCategory, ErrorSeverity, PatcherError
from utils.file_ops import migrate_backup, safe_extract_zip
from utils.paths import normalize_path
from utils.validators import validate_not_empty, validate_path

# 注意: core.config 在方法内延迟导入以避免循环导入

logger = logging.getLogger(__name__)


class SaveService:
    def __init__(self, core_logic: Any) -> None:
        self.core = core_logic

    def _cleanup_temp(self, temp_path: str, is_dir: bool = False) -> None:
        """安全清理临时资源（文件或目录）
        """
        if not os.path.exists(temp_path):
            return
        try:
            if is_dir:
                shutil.rmtree(temp_path, onerror=self.core.remove_readonly_handler)
            else:
                os.remove(temp_path)
        except Exception as e:
            logger.warning(f"Failed to cleanup temp path '{temp_path}': {e}")

    @validate_not_empty("old_dir", "new_dir")
    def migrate_backups(
        self,
        old_dir: str,
        new_dir: str,
        progress_callback: Optional[Callable] = None,
        log_callback: Optional[Callable] = None,
        **kwargs: Any,
    ) -> Tuple[int, int]:
        """迁移备份文件夹"""
        migrated_count = 0
        failed_count = 0
        _check_cancelled = kwargs.get("_check_cancelled")

        old_dir = normalize_path(old_dir)
        new_dir = normalize_path(new_dir)

        from core.config import get_config

        if os.path.exists(old_dir):
            for d in os.listdir(old_dir):
                if _check_cancelled:
                    _check_cancelled()
                fp = os.path.join(old_dir, d)
                if d.startswith(get_config().backup_prefix) and (
                    os.path.isdir(fp) or fp.endswith(".zip")
                ):
                    if log_callback:
                        log_callback(f"Migrating: {d}...")
                    success = migrate_backup(fp, new_dir)
                    if success:
                        migrated_count += 1
                    else:
                        failed_count += 1

        return migrated_count, failed_count

    @validate_not_empty("save_dir", "backup_dir")
    @validate_path("save_dir", should_exist=True)
    def backup_save(
        self,
        save_dir: str,
        backup_dir: str,
        use_zip: bool = True,
        log_callback: Optional[Callable] = None,
        **kwargs: Any,
    ) -> str:
        """执行存档备份（原子操作）"""
        _check_cancelled = kwargs.get("_check_cancelled")
        save_dir = normalize_path(save_dir)
        backup_dir = normalize_path(backup_dir)

        # 确保备份目录存在，不存在则自动创建
        if backup_dir.startswith(save_dir + os.sep) or backup_dir == save_dir:
            raise PatcherError("Backup directory cannot be inside the save directory.")

        try:
            os.makedirs(backup_dir, exist_ok=True)
        except OSError as e:
            raise PatcherError(
                f"Cannot create backup directory '{backup_dir}': {e}"
            ) from e

        from core.config import get_config

        _now = datetime.datetime.now()
        ts = _now.strftime("%Y%m%d%H%M%S") + _now.strftime("%f")[:3]
        prefix = get_config().backup_prefix

        if use_zip:
            zip_name = f"{prefix}{ts}.zip"
            dest_zip = os.path.join(backup_dir, zip_name)
            # 原子写入：先写临时文件，完成后rename
            temp_zip = dest_zip + TEMP_FILE_SUFFIX
            base_path = os.path.normpath(os.path.abspath(save_dir))
            base_len = len(base_path)
            try:
                with zipfile.ZipFile(temp_zip, "w", zipfile.ZIP_DEFLATED) as zf:
                    for root, _dirs, files in os.walk(base_path):
                        if _check_cancelled:
                            _check_cancelled()
                        for file in files:
                            abs_path = os.path.normpath(os.path.join(root, file))
                            abs_root = os.path.normpath(os.path.abspath(root))
                            if not (
                                abs_root.startswith(base_path + os.sep)
                                or abs_root == base_path
                            ):
                                logger.warning(
                                    f"Skipped path outside base directory: {abs_root}"
                                )
                                continue
                            # 正确的相对路径：从规范化基础路径之后截取
                            rel_path = abs_path[base_len:].lstrip(os.sep)
                            zf.write(abs_path, rel_path)
                # 原子替换： rename 操作在 POSIX 下是原子的，Windows 下也足够安全
                os.replace(temp_zip, dest_zip)
            except Exception:
                # 清理临时文件
                self._cleanup_temp(temp_zip, is_dir=False)
                raise
            if log_callback:
                log_callback(f"Backup(ZIP): {zip_name}")
            logger.info(f"Backup created (ZIP): {dest_zip}")
            return dest_zip
        else:
            folder_name = f"{prefix}{ts}"
            dest_folder = os.path.join(backup_dir, folder_name)
            temp_folder = dest_folder + TEMP_FILE_SUFFIX

            def copy_with_cancel(src, dst):
                if _check_cancelled:
                    _check_cancelled()
                shutil.copy2(src, dst)

            self._cleanup_temp(temp_folder, is_dir=True)

            try:
                shutil.copytree(
                    save_dir,
                    temp_folder,
                    symlinks=False,
                    ignore=None,
                    copy_function=copy_with_cancel,
                )
                # 原子替换
                self._cleanup_temp(dest_folder, is_dir=True)
                os.rename(temp_folder, dest_folder)
            except Exception:
                # 清理临时目录
                self._cleanup_temp(temp_folder, is_dir=True)
                raise
            if log_callback:
                log_callback(f"Backup(DIR): {folder_name}")
            logger.info(f"Backup created (DIR): {dest_folder}")
            return dest_folder

    @validate_not_empty("save_dir")
    def clear_save_directory(self, save_dir: str) -> bool:
        """清空存档目录"""
        save_dir = normalize_path(save_dir)
        if not save_dir or not os.path.exists(save_dir):
            return False
        try:
            shutil.rmtree(save_dir, onerror=self.core.remove_readonly_handler)
            return True
        except Exception as clear_err:
            logger.warning(f"Failed to clear save directory: {clear_err}")
            return False

    def _backup_current_save(
        self, save_dir: str, copy_func: Callable[[str, str], None]
    ) -> Tuple[str, str]:
        """步骤1: 备份当前存档到临时目录"""
        temp_dir = tempfile.mkdtemp(prefix=TEMP_BACKUP_PREFIX)
        current_save_backup_path = os.path.join(temp_dir, "current")
        shutil.copytree(
            save_dir,
            current_save_backup_path,
            copy_function=copy_func,
        )
        logger.info(f"Current save backed up to: {temp_dir}")
        return temp_dir, current_save_backup_path

    def _prepare_restore_data(
        self,
        backup_src: str,
        temp_dir: str,
        is_zip: bool,
        copy_func: Callable[[str, str], None],
        check_cancelled: Optional[Callable] = None,
    ) -> str:
        """步骤3: 在临时目录准备要还原的内容"""
        prepared_restore_path = os.path.join(temp_dir, "to_restore")
        if is_zip:
            os.makedirs(prepared_restore_path, exist_ok=True)
            safe_extract_zip(
                backup_src, prepared_restore_path, check_cancelled=check_cancelled
            )
            logger.info(
                f"Extracted backup to temp for restore: {prepared_restore_path}"
            )
        else:
            shutil.copytree(
                backup_src,
                prepared_restore_path,
                copy_function=copy_func,
            )
            logger.info(f"Copied backup to temp for restore: {prepared_restore_path}")
        return prepared_restore_path

    def _apply_restore_data(
        self,
        save_dir: str,
        prepared_restore_path: Optional[str],
        backup_src: str,
        is_zip: bool,
        copy_func: Callable[[str, str], None],
        check_cancelled: Optional[Callable] = None,
    ) -> None:
        """步骤4: 原子替换目标目录"""
        if os.path.exists(save_dir):
            if not self.clear_save_directory(save_dir):
                raise RuntimeError(
                    "Failed to clear current save directory. Aborting restore."
                )

        if prepared_restore_path and os.path.exists(prepared_restore_path):
            os.makedirs(save_dir, exist_ok=True)
            for item in os.listdir(prepared_restore_path):
                src_item = os.path.join(prepared_restore_path, item)
                dst_item = os.path.join(save_dir, item)
                if os.path.isdir(src_item):
                    shutil.copytree(src_item, dst_item, copy_function=copy_func)
                else:
                    copy_func(src_item, dst_item)
        else:
            if is_zip:
                os.makedirs(save_dir, exist_ok=True)
                safe_extract_zip(backup_src, save_dir, check_cancelled=check_cancelled)
            else:
                shutil.copytree(
                    backup_src, save_dir, dirs_exist_ok=True, copy_function=copy_func
                )

    def _rollback_restore(
        self,
        save_dir: str,
        current_save_backup_path: str,
        copy_func: Callable[[str, str], None],
        original_error: Exception,
    ) -> None:
        """
        回滚逻辑：尝试恢复之前备份的当前存档
        """
        try:
            logger.info("Attempting rollback: restoring current save from backup...")
            if os.path.exists(save_dir):
                shutil.rmtree(save_dir, onerror=self.core.remove_readonly_handler)
            os.makedirs(save_dir, exist_ok=True)
            for item in os.listdir(current_save_backup_path):
                src_item = os.path.join(current_save_backup_path, item)
                dst_item = os.path.join(save_dir, item)
                if os.path.isdir(src_item):
                    shutil.copytree(src_item, dst_item, copy_function=copy_func)
                else:
                    copy_func(src_item, dst_item)
            logger.info("Rollback completed successfully")
        except Exception as restore_err:
            logger.error(f"Rollback failed: {restore_err}")
            raise PatcherError(
                f"{original_error}\n\nRollback failed. Current save may be lost. Error: {restore_err}",
                category=ErrorCategory.CORRUPTED_DATA,
                severity=ErrorSeverity.CRITICAL,
            ) from restore_err

        # 回滚成功：仍抛出异常以通知调用方"还原操作失败"，但附带回滚成功信息
        raise PatcherError(
            f"{original_error}\n\nCurrent save has been restored from backup.",
            category=ErrorCategory.UNKNOWN_ERROR,
            severity=ErrorSeverity.WARNING,
        )

    @validate_not_empty("save_dir", "backup_src")
    @validate_path("backup_src", should_exist=True)
    def restore_save(
        self,
        save_dir: str,
        backup_src: str,
        log_callback: Optional[Callable] = None,
        **kwargs: Any,
    ) -> None:
        """
        还原存档（原子事务操作）
        """
        _check_cancelled = kwargs.get("_check_cancelled")
        save_dir = normalize_path(save_dir)
        backup_src = normalize_path(backup_src)

        temp_dir = None
        current_save_backup_path = None

        def copy_with_cancel(src, dst):
            if _check_cancelled:
                _check_cancelled()
            shutil.copy2(src, dst)

        try:
            # 步骤1: 备份当前存档（如果存在）
            if os.path.exists(save_dir):
                temp_dir, current_save_backup_path = self._backup_current_save(
                    save_dir, copy_with_cancel
                )
            else:
                temp_dir = tempfile.mkdtemp(prefix=TEMP_BACKUP_PREFIX)

            # 步骤2: 验证备份源
            if not os.path.exists(backup_src):
                raise FileNotFoundError(f"Backup source not found: {backup_src}")

            is_zip = os.path.isfile(backup_src) and backup_src.endswith(".zip")

            # 步骤3: 在临时目录准备要还原的内容
            if not temp_dir:
                raise RuntimeError("Failed to create temp directory for restore")

            prepared_restore_path = self._prepare_restore_data(
                backup_src, temp_dir, is_zip, copy_with_cancel, _check_cancelled
            )

            # 步骤4: 原子替换目标目录
            self._apply_restore_data(
                save_dir,
                prepared_restore_path,
                backup_src,
                is_zip,
                copy_with_cancel,
                _check_cancelled,
            )

            logger.info(f"Restored save from: {backup_src}")

        except Exception as e:
            logger.error(f"Restore error: {e}")
            if (
                temp_dir
                and current_save_backup_path
                and os.path.exists(current_save_backup_path)
            ):
                self._rollback_restore(
                    save_dir, current_save_backup_path, shutil.copy2, e
                )
            else:
                raise PatcherError(str(e)) from e
        finally:
            if temp_dir and os.path.exists(temp_dir):
                try:
                    shutil.rmtree(temp_dir)
                except Exception as cleanup_err:
                    logger.warning(f"Failed to cleanup temp directory: {cleanup_err}")

    def delete_backup(self, backup_src: str, **kwargs: Any) -> None:
        """
        删除备份
        """
        backup_src = normalize_path(backup_src)
        if not os.path.exists(backup_src):
            logger.warning(
                f"Backup not found (already deleted?): {backup_src}"
            )
            return
        try:
            if os.path.isfile(backup_src):
                os.remove(backup_src)
            else:
                shutil.rmtree(backup_src, onerror=self.core.remove_readonly_handler)
        except OSError as e:
            raise PatcherError(
                f"Failed to delete backup '{backup_src}': {e}",
                category=ErrorCategory.PERMISSION_DENIED,
                severity=ErrorSeverity.ERROR,
            ) from e
