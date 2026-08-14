"""
操作互斥锁模块

防止用户同时进行多个可能冲突的操作。
"""

__all__ = [
    "OperationLock",
    "FileOperationLock",
    "OperationType",
    "get_operation_lock",
    "with_operation_lock",
]

import logging
import os
import threading
from contextlib import contextmanager
from enum import Enum
from functools import wraps
from typing import Callable, Optional, Set, TextIO

logger = logging.getLogger(__name__)


class OperationType(Enum):
    """操作类型"""

    PATCH = "patch"  # 打补丁
    RESTORE = "restore"  # 恢复备份
    FUSE_REMOVE = "fuse_remove"  # 移除Fuse
    FUSE_RESTORE = "fuse_restore"  # 恢复Fuse
    EXTRACT = "extract"  # 解压ASAR
    PACK = "pack"  # 打包ASAR
    SAVE_IMPORT = "save_import"  # 导入存档
    SAVE_EXPORT = "save_export"  # 导出存档
    SAVE_BACKUP = "save_backup"  # 备份存档
    SAVE_RESTORE = "save_restore"  # 还原存档
    SAVE_DELETE = "save_delete"  # 删除备份
    SAVE_MIGRATE = "save_migrate"  # 迁移备份


# 互斥的操作组
MUTEX_GROUPS = {
    # ASAR操作组：不能同时进行
    frozenset(
        {
            OperationType.PATCH,
            OperationType.RESTORE,
            OperationType.EXTRACT,
            OperationType.PACK,
        }
    ),
    # Fuse操作组：不能同时进行
    frozenset(
        {
            OperationType.FUSE_REMOVE,
            OperationType.FUSE_RESTORE,
        }
    ),
    # 存档操作组：不能同时进行
    frozenset(
        {
            OperationType.SAVE_BACKUP,
            OperationType.SAVE_RESTORE,
            OperationType.SAVE_DELETE,
            OperationType.SAVE_MIGRATE,
        }
    ),
}


class OperationLock:
    """
    操作互斥锁

    管理多个操作的互斥关系，防止冲突操作同时进行。
    """

    def __init__(self):
        self._lock = threading.RLock()
        self._current_operations: Set[OperationType] = set()

    def is_operation_running(self, op_type: OperationType) -> bool:
        """检查特定操作是否正在进行"""
        with self._lock:
            return op_type in self._current_operations

    def is_any_operation_running(self) -> bool:
        """检查是否有任何操作正在进行"""
        with self._lock:
            return bool(self._current_operations)

    def get_running_operations(self) -> Set[OperationType]:
        """获取正在进行的操作集合"""
        with self._lock:
            return self._current_operations.copy()

    def acquire(self, op_type: OperationType) -> bool:
        """
        尝试获取操作锁

        Args:
            op_type: 操作类型

        Returns:
            bool: 是否成功获取
        """
        with self._lock:
            # 检查是否与当前操作冲突
            for mutex_group in MUTEX_GROUPS:
                if op_type in mutex_group:
                    # 检查是否有同组的其他操作在进行
                    conflicts = self._current_operations & mutex_group
                    if conflicts:
                        logger.warning(
                            f"Cannot start {op_type.value}: "
                            f"conflicting operations running: {[op.value for op in conflicts]}"
                        )
                        return False

            self._current_operations.add(op_type)
            logger.debug(f"Acquired lock for {op_type.value}")
            return True

    def release(self, op_type: OperationType) -> None:
        """
        释放操作锁

        Args:
            op_type: 操作类型
        """
        with self._lock:
            self._current_operations.discard(op_type)
            logger.debug(f"Released lock for {op_type.value}")

    @contextmanager
    def acquire_context(self, op_type: OperationType):
        """
        上下文管理器形式的锁获取

        使用示例:
            with op_lock.acquire_context(OperationType.PATCH):
                do_patch()
        """
        if not self.acquire(op_type):
            raise OperationConflictError(f"Cannot acquire lock for {op_type.value}")
        try:
            yield self
        finally:
            self.release(op_type)


class OperationConflictError(Exception):
    """操作冲突错误"""

    pass


# 全局操作锁实例
_operation_lock: Optional[OperationLock] = None
_operation_lock_lock = threading.Lock()


def get_operation_lock() -> OperationLock:
    """获取全局操作锁（线程安全懒加载）"""
    global _operation_lock
    if _operation_lock is None:
        with _operation_lock_lock:
            if _operation_lock is None:
                _operation_lock = OperationLock()
    return _operation_lock


def with_operation_lock(op_type: OperationType):
    """
    装饰器：在函数执行期间持有操作锁

    使用示例:
        @with_operation_lock(OperationType.PATCH)
        def apply_patch():
            pass
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            lock = get_operation_lock()
            if not lock.acquire(op_type):
                raise OperationConflictError(
                    f"Cannot execute {func.__name__}: conflicting operation in progress"
                )
            try:
                return func(*args, **kwargs)
            finally:
                lock.release(op_type)

        return wrapper

    return decorator


class FileOperationLock:
    """A non-blocking, cross-process lock for one game resource path.

    The lock is deliberately a sibling of the ASAR so two portable builds of
    the tool coordinate even when they use different user configuration dirs.
    OS-managed advisory locks are released when a crashed process exits.
    """

    def __init__(self, target_path: str) -> None:
        self.path = os.path.abspath(target_path) + ".tyranopatcher.lock"
        self._file: Optional[TextIO] = None
        self._locked = False

    def acquire(self) -> bool:
        try:
            file_obj = open(self.path, "a+", encoding="utf-8")
            self._file = file_obj
            file_obj.seek(0)
            if not file_obj.read(1):
                file_obj.write("0")
                file_obj.flush()
            file_obj.seek(0)
            if os.name == "nt":
                import msvcrt

                msvcrt.locking(file_obj.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl

                fcntl.flock(file_obj.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            self._locked = True
            return True
        except OSError:
            self.release()
            return False

    def release(self) -> None:
        file_obj = self._file
        if file_obj is None:
            return
        try:
            if self._locked:
                file_obj.seek(0)
                if os.name == "nt":
                    import msvcrt

                    msvcrt.locking(file_obj.fileno(), msvcrt.LK_UNLCK, 1)
                else:
                    import fcntl

                    fcntl.flock(file_obj.fileno(), fcntl.LOCK_UN)
        except OSError:
            pass
        finally:
            file_obj.close()
            self._file = None
            self._locked = False
