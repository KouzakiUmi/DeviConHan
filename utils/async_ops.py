# -*- coding: utf-8 -*-
"""
异步操作管理器模块

提供异步操作执行、进度跟踪和取消功能，用于避免GUI卡顿。
"""

__all__ = [
    "OperationState",
    "ProgressInfo",
    "AsyncOperationManager",
    "get_async_manager",
]

import atexit
import inspect
import logging
import threading
from concurrent.futures import ThreadPoolExecutor, Future, CancelledError
from typing import Callable, Optional, Any, Dict
from enum import Enum

logger = logging.getLogger(__name__)

# ================= 异步操作常量 =================
# 异步操作历史记录上限（超过此值自动清理已完成记录）
MAX_HISTORY_OPERATIONS: int = 50
# 线程池最大工作线程数
DEFAULT_MAX_WORKERS: int = 2


class OperationState(Enum):
    """操作状态"""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    FAILED = "failed"


class ProgressInfo:
    """进度信息"""

    def __init__(self, operation_id: str):
        self.operation_id: str = operation_id
        self.state: OperationState = OperationState.PENDING
        self.progress: int = 0  # 0-100
        self.message: str = ""
        self.result: Any = None
        self.error: Optional[BaseException] = None
        self.cancel_event: threading.Event = threading.Event()
        self.future: Optional[Future] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "operation_id": self.operation_id,
            "state": self.state.value,
            "progress": self.progress,
            "message": self.message,
            "error": str(self.error) if self.error else None,
        }


class AsyncOperationManager:
    """
    异步操作管理器

    提供后台任务执行、进度更新和取消功能。
    """

    def __init__(self, max_workers: int = DEFAULT_MAX_WORKERS):
        """
        初始化异步操作管理器

        Args:
            max_workers: 最大工作线程数
        """
        self._executor = ThreadPoolExecutor(max_workers=max_workers)
        self._operations: Dict[str, ProgressInfo] = {}
        self._lock = threading.Lock()
        self._progress_callback: Optional[Callable[[ProgressInfo], None]] = None
        # 修复说明：原实现依赖 __del__ 清理线程池，但 Python 的 __del__
        # 调用时机不可靠（循环引用阻止、解释器退出时全局变量已为 None）。
        # 修复：使用 atexit 注册确定性的退出时清理。
        atexit.register(self._atexit_shutdown)

    def set_progress_callback(self, callback: Callable[[ProgressInfo], None]) -> None:
        """
        设置进度回调函数

        Args:
            callback: 回调函数，接收 ProgressInfo 参数
        """
        self._progress_callback = callback

    def _notify_progress(self, progress_info: ProgressInfo) -> None:
        """通知进度更新"""
        if self._progress_callback:
            try:
                self._progress_callback(progress_info)
            except Exception as e:
                logger.warning(f"Progress callback error: {e}")

    def submit(self, operation_id: str, func: Callable, *args, **kwargs) -> Future:
        """
        提交异步任务

        Bug D 修复：原实现在 wrapped_func 内部直接修改通过 **kwargs 捕获的
        同一字典对象（kwargs["cancel_event"] = ... 等），若调用方复用该字典
        或同一操作被重新提交，注入的键会污染后续调用。
        修复：在 wrapped_func 执行时复制一份 kwargs 副本再注入，不修改原始字典。

        同时修复：原 len(self._operations) >= MAX_HISTORY_OPERATIONS 检查在锁外
        执行，cleanup_completed() 内再重新加锁，存在 TOCTOU 竞态；改为在持锁
        状态下做清理。

        Args:
            operation_id: 操作ID
            func: 要执行的函数
            *args: 函数位置参数
            **kwargs: 函数关键字参数

        Returns:
            Future: 异步任务Future对象
        """
        sig = inspect.signature(func)
        accepts_cancel = "cancel_event" in sig.parameters

        with self._lock:
            # M4 修复：拒绝对正在运行中的同名 operation_id 重复提交。
            # 原实现直接覆盖旧的 ProgressInfo，导致旧的 wrapped_func
            # 仍持有旧对象引用并在完成时调用 _notify_progress，
            # 而此时 _operations 字典里就已是新对象，导致状态孤儿。
            existing = self._operations.get(operation_id)
            if existing is not None and existing.state == OperationState.RUNNING:
                logger.warning(
                    f"Operation '{operation_id}' is already running. "
                    "Ignoring duplicate submit."
                )
                return existing.future  # type: ignore[return-value]

            # 防积压：在持锁状态内检查并清理，避免 TOCTOU 竞态
            if len(self._operations) >= MAX_HISTORY_OPERATIONS:
                completed_states = {
                    OperationState.COMPLETED,
                    OperationState.CANCELLED,
                    OperationState.FAILED,
                }
                to_remove = [
                    op_id
                    for op_id, info in self._operations.items()
                    if info.state in completed_states
                ]
                for op_id in to_remove:
                    del self._operations[op_id]

            progress_info = ProgressInfo(operation_id)
            progress_info.state = OperationState.RUNNING
            progress_info.message = "Starting..."
            self._operations[operation_id] = progress_info

        self._notify_progress(progress_info)

        def wrapped_func():
            try:
                # 更新进度
                progress_info.message = "In progress..."
                self._notify_progress(progress_info)

                # 复制一份 kwargs，避免修改调用方传入的原始字典（Bug D 修复）
                call_kwargs = dict(kwargs)

                def check_cancelled():
                    if progress_info.cancel_event.is_set():
                        raise CancelledError("Operation cancelled by user")

                # 仅当函数签名接受取消参数时才注入（注入到副本，不影响原始 kwargs）
                if accepts_cancel:
                    call_kwargs["cancel_event"] = progress_info.cancel_event
                    call_kwargs["_check_cancelled"] = check_cancelled

                # 执行实际函数
                result = func(*args, **call_kwargs)

                # 更新完成状态
                with self._lock:
                    progress_info.state = OperationState.COMPLETED
                    progress_info.progress = 100
                    progress_info.message = "Completed"
                    progress_info.result = result

                self._notify_progress(progress_info)
                return result

            except CancelledError:
                with self._lock:
                    progress_info.state = OperationState.CANCELLED
                    progress_info.message = "Cancelled"
                self._notify_progress(progress_info)
                raise

            except Exception as e:
                logger.exception(f"Operation {operation_id} failed: {e}")
                with self._lock:
                    progress_info.state = OperationState.FAILED
                    progress_info.message = f"Failed: {str(e)}"
                    progress_info.error = e  # type: ignore
                self._notify_progress(progress_info)
                raise

        future = self._executor.submit(wrapped_func)

        # 存储future引用
        with self._lock:
            self._operations[operation_id].future = future

        return future

    def update_progress(
        self, operation_id: str, progress: int, message: str = ""
    ) -> None:
        """
        更新操作进度

        Args:
            operation_id: 操作ID
            progress: 进度值 (0-100)
            message: 进度消息
        """
        with self._lock:
            if operation_id in self._operations:
                progress_info = self._operations[operation_id]
                progress_info.progress = max(0, min(100, progress))
                if message:
                    progress_info.message = message
                self._notify_progress(progress_info)

    def cancel(self, operation_id: str) -> bool:
        """
        取消操作

        Args:
            operation_id: 操作ID

        Returns:
            bool: 是否成功取消

        修复说明（C2 死锁）：
        原实现在持有 self._lock 的状态下调用 _notify_progress()，
        而 _notify_progress 会执行外部回调，外部回调若调用
        get_progress() / get_all_operations() 等任何需要获取
        self._lock 的方法，就会因为 threading.Lock() 不可重入而
        发生死锁。
        修复：在锁内仅修改状态，将 _notify_progress 移到锁外调用。
        """
        progress_to_notify: Optional[ProgressInfo] = None
        result = False

        with self._lock:
            if operation_id not in self._operations:
                return False

            progress_info = self._operations[operation_id]

            # 设置 cancel_event，通知运行中的任务尽早退出
            if hasattr(progress_info, "cancel_event"):
                progress_info.cancel_event.set()

            future = progress_info.future
            if future is not None:
                cancelled = future.cancel()
                if cancelled:
                    progress_info.state = OperationState.CANCELLED
                    progress_info.message = "Cancelled"
                    progress_to_notify = progress_info
                result = cancelled

        # 在锁外执行回调，避免死锁
        if progress_to_notify is not None:
            self._notify_progress(progress_to_notify)

        return result

    def get_progress(self, operation_id: str) -> Optional[ProgressInfo]:
        """
        获取操作进度信息

        Args:
            operation_id: 操作ID

        Returns:
            ProgressInfo 或 None
        """
        with self._lock:
            return self._operations.get(operation_id)

    def get_all_operations(self) -> Dict[str, ProgressInfo]:
        """获取所有操作信息"""
        with self._lock:
            return dict(self._operations)

    def cleanup_completed(self) -> None:
        """清理已完成的任务记录"""
        with self._lock:
            completed_states = {
                OperationState.COMPLETED,
                OperationState.CANCELLED,
                OperationState.FAILED,
            }
            to_remove = [
                op_id
                for op_id, info in self._operations.items()
                if info.state in completed_states
            ]
            for op_id in to_remove:
                del self._operations[op_id]

    def shutdown(self, wait: bool = True) -> None:
        """
        关闭异步操作管理器

        Args:
            wait: 是否等待任务完成
        """
        self._executor.shutdown(wait=wait)

    def __enter__(self) -> "AsyncOperationManager":
        """支持上下文管理器协议"""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """退出上下文时关闭线程池"""
        self.shutdown(wait=False)

    def _atexit_shutdown(self) -> None:
        """解释器退出时的清理钩子（通过 atexit 注册，比 __del__ 更可靠）"""
        try:
            self._executor.shutdown(wait=False)
        except Exception:
            pass

    def __del__(self) -> None:
        """析构函数（保留作为次要保险，主要清理由 atexit 完成）

        修复说明：__del__ 的调用时机在 Python 中不可靠（循环引用会阻止
        调用，解释器退出阶段全局变量已为 None 会导致 AttributeError）。
        主要清理责任已转移到 atexit 注册的 _atexit_shutdown()。
        """
        try:
            self._executor.shutdown(wait=False)
        except Exception:
            pass


# 全局异步操作管理器实例（懒初始化，避免在纯批处理模式下创建不必要的线程池）
_async_manager: Optional[AsyncOperationManager] = None
_async_manager_lock = threading.Lock()


def get_async_manager() -> AsyncOperationManager:
    """获取全局异步操作管理器（线程安全懒初始化单例）"""
    global _async_manager
    if _async_manager is None:
        with _async_manager_lock:
            if _async_manager is None:
                _async_manager = AsyncOperationManager()
    return _async_manager
