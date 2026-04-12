"""
操作互斥锁模块

防止用户同时进行多个可能冲突的操作。
"""

__all__ = [
    "OperationLock",
    "OperationType",
    "get_operation_lock",
    "with_operation_lock",
]

import logging
import threading
from contextlib import contextmanager
from enum import Enum
from functools import wraps
from typing import Callable, Optional, Set

logger = logging.getLogger(__name__)


class OperationType(Enum):
    """操作类型"""
    PATCH = "patch"              # 打补丁
    RESTORE = "restore"          # 恢复备份
    FUSE_REMOVE = "fuse_remove"  # 移除Fuse
    FUSE_RESTORE = "fuse_restore" # 恢复Fuse
    EXTRACT = "extract"          # 解压ASAR
    PACK = "pack"                # 打包ASAR
    SAVE_IMPORT = "save_import"  # 导入存档
    SAVE_EXPORT = "save_export"  # 导出存档


# 互斥的操作组
MUTEX_GROUPS = {
    # ASAR操作组：不能同时进行
    frozenset({
        OperationType.PATCH,
        OperationType.RESTORE,
        OperationType.EXTRACT,
        OperationType.PACK,
    }),
    # Fuse操作组：不能同时进行
    frozenset({
        OperationType.FUSE_REMOVE,
        OperationType.FUSE_RESTORE,
    }),
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
            return len(self._current_operations) > 0

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
                    f"Cannot execute {func.__name__}: "
                    f"conflicting operation in progress"
                )
            try:
                return func(*args, **kwargs)
            finally:
                lock.release(op_type)
        return wrapper
    return decorator
