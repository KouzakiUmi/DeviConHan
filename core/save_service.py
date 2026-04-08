# -*- coding: utf-8 -*-
"""
存档服务模块，负责执行存档的备份、还原、迁移、删除等业务逻辑
"""

import os
import shutil
import logging
import datetime
import zipfile
from utils.file_ops import migrate_backup, safe_extract_zip
from utils.paths import normalize_path
from utils.validators import validate_path, validate_not_empty

logger = logging.getLogger(__name__)


class SaveService:
    def __init__(self, core_logic):
        self.core = core_logic

    @validate_not_empty("old_dir", "new_dir")
    def migrate_backups(
        self, old_dir, new_dir, progress_callback=None, log_callback=None, **kwargs
    ):
        """迁移备份文件夹"""
        migrated_count = 0
        failed_count = 0
        _check_cancelled = kwargs.get("_check_cancelled")

        old_dir = normalize_path(old_dir)
        new_dir = normalize_path(new_dir)

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
        self, save_dir, backup_dir, use_zip=True, log_callback=None, **kwargs
    ):
        """执行存档备份（原子操作）"""
        _check_cancelled = kwargs.get("_check_cancelled")
        save_dir = normalize_path(save_dir)
        backup_dir = normalize_path(backup_dir)

        from core.config import get_config

        ts = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
        prefix = get_config().backup_prefix

        if use_zip:
            zip_name = f"{prefix}{ts}.zip"
            dest_zip = os.path.join(backup_dir, zip_name)
            # 原子写入：先写临时文件，完成后rename
            temp_zip = dest_zip + ".tmp"
            # Bug E 修复：base_path 和 base_len 必须使用同一个规范化路径。
            # 原实现 base_path = os.path.abspath(save_dir) 但
            # base_len = len(save_dir)（未规范化），abs_path 是基于
            # base_path 构建的绝对路径，用 base_len 切割会切到路径中间，
            # 产生错乱的 ZIP 内部路径，极端情况产生路径遍历风险。
            # 修复：统一使用 base_path（规范化绝对路径）及其长度。
            base_path = os.path.normpath(os.path.abspath(save_dir))
            base_len = len(base_path)
            try:
                with zipfile.ZipFile(temp_zip, "w", zipfile.ZIP_DEFLATED) as zf:
                    for root, dirs, files in os.walk(base_path):
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
                if os.path.exists(temp_zip):
                    try:
                        os.remove(temp_zip)
                    except Exception:
                        pass
                raise
            if log_callback:
                log_callback(f"Backup(ZIP): {zip_name}")
            logger.info(f"Backup created (ZIP): {dest_zip}")
            return dest_zip
        else:
            folder_name = f"{prefix}{ts}"
            dest_folder = os.path.join(backup_dir, folder_name)
            temp_folder = dest_folder + ".tmp"

            def copy_with_cancel(src, dst):
                if _check_cancelled:
                    _check_cancelled()
                shutil.copy2(src, dst)

            if os.path.exists(temp_folder):
                shutil.rmtree(temp_folder, onerror=self.core.remove_readonly_handler)

            try:
                shutil.copytree(
                    save_dir,
                    temp_folder,
                    symlinks=False,
                    ignore=None,
                    copy_function=copy_with_cancel,
                )
                # 原子替换
                if os.path.exists(dest_folder):
                    shutil.rmtree(
                        dest_folder, onerror=self.core.remove_readonly_handler
                    )
                os.rename(temp_folder, dest_folder)
            except Exception:
                # 清理临时目录
                if os.path.exists(temp_folder):
                    try:
                        shutil.rmtree(
                            temp_folder, onerror=self.core.remove_readonly_handler
                        )
                    except Exception:
                        pass
                raise
            if log_callback:
                log_callback(f"Backup(DIR): {folder_name}")
            logger.info(f"Backup created (DIR): {dest_folder}")
            return dest_folder

    @validate_not_empty("save_dir")
    def clear_save_directory(self, save_dir):
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

    def _backup_current_save(self, save_dir, copy_func):
        """步骤1: 备份当前存档到临时目录"""
        import tempfile

        temp_dir = tempfile.mkdtemp(prefix="save_restore_")
        current_save_backup_path = os.path.join(temp_dir, "current")
        shutil.copytree(
            save_dir,
            current_save_backup_path,
            copy_function=copy_func,
        )
        logger.info(f"Current save backed up to: {temp_dir}")
        return temp_dir, current_save_backup_path

    def _prepare_restore_data(
        self, backup_src, temp_dir, is_zip, copy_func, check_cancelled
    ):
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
        save_dir,
        prepared_restore_path,
        backup_src,
        is_zip,
        copy_func,
        check_cancelled,
    ):
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
        self, save_dir, current_save_backup_path, copy_func, original_error
    ):
        """
        回滚逻辑：尝试恢复之前备份的当前存档

        修复说明：原实现在回滚成功后仍抛出 PatcherError，将成功恢复
        视为异常，调用方难以区分"还原失败"与"还原操作本身出错但已回滚"。
        修复后：
        - 回滚成功：抛出包含原始错误信息 + 回滚成功提示的 PatcherError，
          使用 WARNING 级别而不是 ERROR，便于调用方展示给用户。
        - 回滚失败：抛出 CRITICAL 级别的 PatcherError，提示数据可能丢失。
        """
        from utils.error_handler import PatcherError, ErrorSeverity, ErrorCategory

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
            )

        # 回滚成功：仍抛出异常以通知调用方"还原操作失败"，但附带回滚成功信息
        raise PatcherError(
            f"{original_error}\n\nCurrent save has been restored from backup.",
            category=ErrorCategory.UNKNOWN_ERROR,
            severity=ErrorSeverity.WARNING,
        )

    @validate_not_empty("save_dir", "backup_src")
    @validate_path("backup_src", should_exist=True)
    def restore_save(self, save_dir, backup_src, log_callback=None, **kwargs):
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
                import tempfile

                temp_dir = tempfile.mkdtemp(prefix="save_restore_")

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
                    save_dir, current_save_backup_path, copy_with_cancel, e
                )
            else:
                from utils.error_handler import PatcherError

                raise PatcherError(str(e))
        finally:
            if temp_dir and os.path.exists(temp_dir):
                try:
                    shutil.rmtree(temp_dir)
                except Exception as cleanup_err:
                    logger.warning(f"Failed to cleanup temp directory: {cleanup_err}")

    def delete_backup(self, backup_src, **kwargs):
        """删除备份"""
        backup_src = normalize_path(backup_src)
        if os.path.isfile(backup_src):
            os.remove(backup_src)
        else:
            shutil.rmtree(backup_src, onerror=self.core.remove_readonly_handler)
