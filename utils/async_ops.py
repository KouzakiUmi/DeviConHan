# -*- coding: utf-8 -*-
"""
异步操作管理器模块

提供异步操作执行、进度跟踪和取消功能，用于避免GUI卡顿。
"""

import logging
import threading
from concurrent.futures import ThreadPoolExecutor, Future, CancelledError
from typing import Callable, Optional, Any, Dict
from enum import Enum

logger = logging.getLogger(__name__)


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
        self.operation_id = operation_id
        self.state = OperationState.PENDING
        self.progress = 0  # 0-100
        self.message = ""
        self.result = None
        self.error = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'operation_id': self.operation_id,
            'state': self.state.value,
            'progress': self.progress,
            'message': self.message,
            'error': str(self.error) if self.error else None
        }


class AsyncOperationManager:
    """
    异步操作管理器
    
    提供后台任务执行、进度更新和取消功能。
    """
    
    def __init__(self, max_workers: int = 2):
        """
        初始化异步操作管理器
        
        Args:
            max_workers: 最大工作线程数
        """
        self._executor = ThreadPoolExecutor(max_workers=max_workers)
        self._operations: Dict[str, ProgressInfo] = {}
        self._lock = threading.Lock()
        self._progress_callback: Optional[Callable[[ProgressInfo], None]] = None
    
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
        
        Args:
            operation_id: 操作ID
            func: 要执行的函数
            *args: 函数位置参数
            **kwargs: 函数关键字参数
            
        Returns:
            Future: 异步任务Future对象
        """
        with self._lock:
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
                
                # 执行实际函数
                result = func(*args, **kwargs)
                
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
                    progress_info.error = e
                self._notify_progress(progress_info)
                raise
        
        future = self._executor.submit(wrapped_func)
        
        # 存储future引用
        with self._lock:
            self._operations[operation_id].future = future
        
        return future
    
    def update_progress(self, operation_id: str, progress: int, message: str = "") -> None:
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
        """
        with self._lock:
            if operation_id not in self._operations:
                return False
            
            progress_info = self._operations[operation_id]
            if hasattr(progress_info, 'future'):
                cancelled = progress_info.future.cancel()
                if cancelled:
                    progress_info.state = OperationState.CANCELLED
                    progress_info.message = "Cancelled"
                    self._notify_progress(progress_info)
                return cancelled
            return False
    
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
            completed_states = {OperationState.COMPLETED, OperationState.CANCELLED, OperationState.FAILED}
            to_remove = [
                op_id for op_id, info in self._operations.items() 
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


# 全局异步操作管理器实例
_async_manager = AsyncOperationManager()


def get_async_manager() -> AsyncOperationManager:
    """获取全局异步操作管理器"""
    return _async_manager