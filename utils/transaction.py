"""
事务性文件操作模块

提供原子性文件操作，确保数据一致性。
支持操作回滚和自动清理。
"""

__all__ = [
    "TransactionError",
    "FileTransaction",
    "atomic_rename",
    "safe_backup",
]

import logging
import os
import shutil
import tempfile
from typing import List, Optional

logger = logging.getLogger(__name__)


class TransactionError(Exception):
    """事务操作错误"""

    pass


class FileTransaction:
    """
    文件事务管理器

    确保一组文件操作要么全部成功，要么全部回滚。
    支持自动清理和手动回滚。

    使用示例:
        with FileTransaction() as tx:
            tx.backup_original("app.asar")
            tx.stage_new_file("app.asar", new_content)
            tx.commit()  # 提交所有更改
    """

    def __init__(self, temp_dir: Optional[str] = None):
        """
        初始化事务管理器

        Args:
            temp_dir: 临时目录路径，None则使用系统默认
        """
        self.temp_dir = temp_dir or tempfile.gettempdir()
        self.tx_dir: str = ""
        self.backups: dict = {}  # 原始文件 -> 备份路径
        self.staged: dict = {}  # 目标路径 -> 临时路径
        self.committed = False
        self._cleanup_on_exit = True

    def __enter__(self):
        """进入上下文，创建事务目录"""
        self.tx_dir = tempfile.mkdtemp(prefix="patcher_tx_", dir=self.temp_dir)
        logger.debug(f"Transaction directory created: {self.tx_dir}")
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """退出上下文，自动回滚或清理"""
        try:
            if exc_type is not None and not self.committed:
                logger.warning(f"Exception in transaction, rolling back: {exc_val}")
                self.rollback()
            elif not self.committed:
                self.rollback()
        finally:
            self.cleanup()

    def backup_original(self, file_path: str) -> str:
        """
        备份原始文件到事务目录

        Args:
            file_path: 原始文件路径

        Returns:
            str: 备份路径

        Raises:
            TransactionError: 如果文件不存在或备份失败
        """
        if not os.path.exists(file_path):
            raise TransactionError(f"Cannot backup non-existent file: {file_path}")

        backup_path = os.path.join(self.tx_dir, f"backup_{len(self.backups)}")

        try:
            if os.path.isfile(file_path):
                shutil.copy2(file_path, backup_path)
            elif os.path.isdir(file_path):
                shutil.copytree(file_path, backup_path)
            else:
                raise TransactionError(f"Unknown file type: {file_path}")

            self.backups[file_path] = backup_path
            logger.debug(f"Backed up {file_path} -> {backup_path}")
            return backup_path

        except Exception as e:
            raise TransactionError(f"Failed to backup {file_path}: {e}") from e

    def stage_new_file(self, target_path: str, source_path: str) -> None:
        """
        暂存新文件，等待提交

        Args:
            target_path: 最终目标路径
            source_path: 临时源文件路径（会被移动到事务目录）

        Raises:
            TransactionError: 如果暂存失败
        """
        if not os.path.exists(source_path):
            raise TransactionError(f"Source file does not exist: {source_path}")

        staged_path = os.path.join(self.tx_dir, f"staged_{len(self.staged)}")

        try:
            if os.path.isfile(source_path):
                shutil.move(source_path, staged_path)
            elif os.path.isdir(source_path):
                shutil.move(source_path, staged_path)
            else:
                raise TransactionError(f"Unknown file type: {source_path}")

            self.staged[target_path] = staged_path
            logger.debug(f"Staged {source_path} -> {target_path} (temp: {staged_path})")

        except Exception as e:
            raise TransactionError(f"Failed to stage {source_path}: {e}") from e

    def commit(self) -> None:
        """
        提交所有暂存的更改

        执行顺序：
        1. 将原始文件移动到 .old 备份
        2. 将暂存文件移动到目标位置
        3. 删除 .old 备份

        Raises:
            TransactionError: 如果提交失败
        """
        if self.committed:
            raise TransactionError("Transaction already committed")

        old_backups = []
        new_files_placed = []

        try:
            # 第一步：移动原始文件到.old
            for target_path in self.staged.keys():
                if os.path.exists(target_path):
                    old_path = target_path + ".tx_old"
                    os.replace(target_path, old_path)
                    old_backups.append((target_path, old_path))
                    logger.debug(f"Moved original to {old_path}")

            # 第二步：移动暂存文件到目标位置
            for _target_path, staged_path in self.staged.items():
                shutil.move(staged_path, target_path)
                new_files_placed.append(target_path)
                logger.info(f"Committed: {staged_path} -> {target_path}")

            # 第三步：删除.old备份
            for _target_path, old_path in old_backups:
                if os.path.isfile(old_path):
                    os.remove(old_path)
                elif os.path.isdir(old_path):
                    shutil.rmtree(old_path)
                logger.debug(f"Removed old backup: {old_path}")

            self.committed = True
            logger.info("Transaction committed successfully")

        except Exception as e:
            # 提交失败，尝试恢复
            logger.error(f"Commit failed: {e}")
            self._recover_from_failed_commit(old_backups, new_files_placed)
            raise TransactionError(f"Commit failed: {e}") from e

    def _recover_from_failed_commit(
        self, old_backups: List[tuple], new_files_placed: List[str]
    ) -> None:
        """从失败的提交中恢复"""
        logger.warning("Attempting to recover from failed commit...")

        # 清理已经放置的新文件
        for target_path in new_files_placed:
            try:
                if os.path.exists(target_path):
                    if os.path.isfile(target_path):
                        os.remove(target_path)
                    else:
                        shutil.rmtree(target_path)
                    logger.debug(f"Removed newly placed file during recovery: {target_path}")
            except Exception as e:
                logger.error(f"Failed to remove new file {target_path}: {e}")

        for target_path, old_path in old_backups:
            try:
                # 恢复.old备份
                if os.path.exists(old_path):
                    # 如果刚才清理遗漏了或者因为某些原因目标还存在，强制删除以保证恢复
                    if os.path.exists(target_path) and os.path.isdir(target_path):
                        shutil.rmtree(target_path)
                    os.replace(old_path, target_path)
                    logger.info(f"Recovered: {old_path} -> {target_path}")
            except Exception as e:
                logger.error(f"Recovery failed for {target_path}: {e}")

    def rollback(self) -> None:
        """回滚所有更改，恢复原始文件"""
        if self.committed:
            logger.warning("Cannot rollback committed transaction")
            return

        logger.info("Rolling back transaction...")

        # 1. 恢复通过 backup_original 备份的文件
        for original_path, backup_path in self.backups.items():
            try:
                if os.path.exists(backup_path):
                    temp_restore = original_path + ".restore_tmp"
                    if os.path.isfile(backup_path):
                        shutil.copy2(backup_path, temp_restore)
                    else:
                        shutil.copytree(backup_path, temp_restore)

                    if os.path.exists(original_path) and os.path.isdir(original_path):
                        shutil.rmtree(original_path)
                    os.replace(temp_restore, original_path)
                    logger.debug(f"Restored original file from backup: {original_path}")
            except Exception as e:
                logger.warning(f"Failed to restore original file {original_path}: {e}")

        # 2. 删除所有暂存文件
        for _target_path, staged_path in self.staged.items():
            try:
                if os.path.exists(staged_path):
                    if os.path.isfile(staged_path):
                        os.remove(staged_path)
                    else:
                        shutil.rmtree(staged_path)
                    logger.debug(f"Removed staged file: {staged_path}")
            except Exception as e:
                logger.warning(f"Failed to remove staged file {staged_path}: {e}")

        self.cleanup()

    def cleanup(self) -> None:
        """清理事务目录"""
        if self.tx_dir and os.path.exists(self.tx_dir):
            try:
                shutil.rmtree(self.tx_dir)
                logger.debug(f"Cleaned up transaction directory: {self.tx_dir}")
            except Exception as e:
                logger.warning(f"Failed to cleanup transaction directory: {e}")
            finally:
                self.tx_dir = ""


def atomic_rename(src: str, dst: str) -> None:
    """
    原子性重命名文件

    Args:
        src: 源文件路径
        dst: 目标文件路径

    Raises:
        TransactionError: 如果操作失败
    """
    try:
        # Windows上os.rename是原子的
        os.replace(src, dst)
    except OSError as e:
        raise TransactionError(f"Failed to rename {src} to {dst}: {e}") from e


def safe_backup(file_path: str, backup_suffix: str = ".bak") -> str:
    """
    安全地创建文件备份

    Args:
        file_path: 要备份的文件
        backup_suffix: 备份文件后缀

    Returns:
        str: 备份文件路径

    Raises:
        TransactionError: 如果备份失败
    """
    if not os.path.exists(file_path):
        raise TransactionError(f"Cannot backup non-existent file: {file_path}")

    backup_path = file_path + backup_suffix

    # 如果备份已存在，创建带序号的备份
    counter = 1
    original_backup = backup_path
    while os.path.exists(backup_path):
        backup_path = f"{original_backup}.{counter}"
        counter += 1

    try:
        if os.path.isfile(file_path):
            shutil.copy2(file_path, backup_path)
        elif os.path.isdir(file_path):
            shutil.copytree(file_path, backup_path)
        else:
            raise TransactionError(f"Unknown file type: {file_path}")

        logger.info(f"Created backup: {file_path} -> {backup_path}")
        return backup_path

    except Exception as e:
        raise TransactionError(f"Failed to create backup: {e}") from e
