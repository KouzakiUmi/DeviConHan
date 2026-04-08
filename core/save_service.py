# -*- coding: utf-8 -*-
"""
存档服务模块，负责执行存档的备份、还原、迁移、删除等业务逻辑
"""
import os
import shutil
import logging
import datetime
import zipfile
from utils.language import T
from utils.file_ops import migrate_backup
from utils.paths import normalize_path

logger = logging.getLogger(__name__)

class SaveService:
    def __init__(self, core_logic):
        self.core = core_logic

    def migrate_backups(self, old_dir, new_dir, progress_callback=None, log_callback=None, **kwargs):
        """迁移备份文件夹"""
        migrated_count = 0
        failed_count = 0
        _check_cancelled = kwargs.get('_check_cancelled')
        
        old_dir = normalize_path(old_dir)
        new_dir = normalize_path(new_dir)
        
        if os.path.exists(old_dir):
            for d in os.listdir(old_dir):
                if _check_cancelled:
                    _check_cancelled()
                fp = os.path.join(old_dir, d)
                if d.startswith("Backup_") and (os.path.isdir(fp) or fp.endswith(".zip")):
                    if log_callback:
                        log_callback(f"Migrating: {d}...")
                    success = migrate_backup(fp, new_dir)
                    if success:
                        migrated_count += 1
                    else:
                        failed_count += 1
                        
        return migrated_count, failed_count

    def backup_save(self, save_dir, backup_dir, use_zip=True, log_callback=None, **kwargs):
        """执行存档备份"""
        _check_cancelled = kwargs.get('_check_cancelled')
        save_dir = normalize_path(save_dir)
        backup_dir = normalize_path(backup_dir)
        
        ts = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
        
        if use_zip:
            zip_name = f"Backup_{ts}.zip"
            dest_zip = os.path.join(backup_dir, zip_name)
            base_path = os.path.abspath(save_dir)
            with zipfile.ZipFile(dest_zip, "w", zipfile.ZIP_DEFLATED) as zf:
                base_len = len(save_dir)
                for root, dirs, files in os.walk(save_dir):
                    if _check_cancelled:
                        _check_cancelled()
                    for file in files:
                        abs_path = os.path.join(root, file)
                        abs_root = os.path.abspath(root)
                        if not (abs_root.startswith(base_path + os.sep) or abs_root == base_path):
                            logger.warning(f"Skipped path outside base directory: {abs_root}")
                            continue
                        rel_path = abs_path[base_len:].lstrip(os.sep)
                        zf.write(abs_path, rel_path)
            if log_callback:
                log_callback(f"Backup(ZIP): {zip_name}")
            logger.info(f"Backup created (ZIP): {dest_zip}")
            return dest_zip
        else:
            folder_name = f"Backup_{ts}"
            dest_folder = os.path.join(backup_dir, folder_name)
            
            def copy_with_cancel(src, dst):
                if _check_cancelled:
                    _check_cancelled()
                shutil.copy2(src, dst)
                
            shutil.copytree(save_dir, dest_folder, symlinks=False, ignore=None, copy_function=copy_with_cancel)
            if log_callback:
                log_callback(f"Backup(DIR): {folder_name}")
            logger.info(f"Backup created (DIR): {dest_folder}")
            return dest_folder

    def clear_save_directory(self, save_dir):
        """清空存档目录"""
        save_dir = normalize_path(save_dir)
        if not save_dir or not os.path.exists(save_dir):
            return False
        try:
            shutil.rmtree(save_dir, onerror=self.core.remove_readonly)
            return True
        except Exception as clear_err:
            logger.warning(f"Failed to clear save directory: {clear_err}")
            return False

    def restore_save(self, save_dir, backup_src, log_callback=None, **kwargs):
        """还原存档"""
        _check_cancelled = kwargs.get('_check_cancelled')
        save_dir = normalize_path(save_dir)
        backup_src = normalize_path(backup_src)
        
        temp_dir = None
        backup_success = False
        
        def copy_with_cancel(src, dst):
            if _check_cancelled:
                _check_cancelled()
            shutil.copy2(src, dst)
            
        try:
            if os.path.exists(save_dir):
                import tempfile
                temp_dir = tempfile.mkdtemp(prefix="save_backup_")
                shutil.copytree(save_dir, os.path.join(temp_dir, "current"), copy_function=copy_with_cancel)
                backup_success = True
                logger.info(f"Successfully backed up current save to: {temp_dir}")

            if os.path.isfile(backup_src) and backup_src.endswith(".zip"):
                if os.path.exists(save_dir):
                    if not self.clear_save_directory(save_dir):
                        raise RuntimeError("Failed to clear current save directory. Aborting restore to prevent data pollution.")
                os.makedirs(save_dir, exist_ok=True)
                with zipfile.ZipFile(backup_src, "r") as zf:
                    for member in zf.infolist():
                        if _check_cancelled:
                            _check_cancelled()
                        file_path = os.path.join(save_dir, member.filename)
                        abs_save_dir = os.path.abspath(save_dir)
                        abs_file_path = os.path.abspath(file_path)
                        if not (abs_file_path.startswith(abs_save_dir + os.sep) or abs_file_path == abs_save_dir):
                            raise ValueError("Invalid path in ZIP: potential directory traversal")
                    zf.extractall(save_dir)
                logger.info(f"Restored save from ZIP: {backup_src}")
            else:
                if os.path.exists(save_dir):
                    if not self.clear_save_directory(save_dir):
                        raise RuntimeError("Failed to clear current save directory. Aborting restore to prevent data pollution.")
                shutil.copytree(backup_src, save_dir, dirs_exist_ok=True, copy_function=copy_with_cancel)
                logger.info(f"Restored save from folder: {backup_src}")

        except Exception as e:
            logger.error(f"Restore error: {e}")
            if temp_dir and backup_success and os.path.exists(temp_dir):
                try:
                    logger.info("Attempting to restore from backup...")
                    shutil.rmtree(save_dir, onerror=self.core.remove_readonly)
                    shutil.copytree(os.path.join(temp_dir, "current"), save_dir, copy_function=copy_with_cancel)
                    logger.info("Successfully restored from backup")
                except Exception as restore_err:
                    logger.error(f"Failed to restore from backup: {restore_err}")
                    raise Exception(f"{e}\n\nFailed to restore from backup: {restore_err}")
                else:
                    raise Exception(f"{e}\n\nCurrent save has been restored from backup.")
            else:
                raise e
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
            shutil.rmtree(backup_src, onerror=self.core.remove_readonly)
