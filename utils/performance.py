# -*- coding: utf-8 -*-
"""
性能分析工具模块

提供性能分析和计时功能，用于优化和监控程序运行。
"""

import logging
import time
from contextlib import contextmanager
from typing import Optional, Dict, Any
from functools import wraps

logger = logging.getLogger(__name__)


class PerformanceMonitor:
    """
    性能监控器，用于跟踪和分析代码性能
    """
    
    def __init__(self):
        """初始化性能监控器"""
        self._timings: Dict[str, Dict[str, Any]] = {}
        self._enabled = True
    
    def enable(self) -> None:
        """启用性能监控"""
        self._enabled = True
    
    def disable(self) -> None:
        """禁用性能监控"""
        self._enabled = False
    
    def start(self, name: str) -> None:
        """
        开始计时
        
        Args:
            name: 计时器名称
        """
        if not self._enabled:
            return
        
        if name not in self._timings:
            self._timings[name] = {
                'total_time': 0.0,
                'count': 0,
                'min_time': float('inf'),
                'max_time': 0.0
            }
        
        self._timings[name]['start_time'] = time.perf_counter()
    
    def stop(self, name: str) -> float:
        """
        停止计时并返回耗时
        
        Args:
            name: 计时器名称
            
        Returns:
            耗时（秒）
        """
        if not self._enabled:
            return 0.0
        
        if name not in self._timings or 'start_time' not in self._timings[name]:
            logger.warning(f"Timer '{name}' was not started")
            return 0.0
        
        elapsed = time.perf_counter() - self._timings[name]['start_time']
        
        # 更新统计信息
        timing = self._timings[name]
        timing['total_time'] += elapsed
        timing['count'] += 1
        timing['min_time'] = min(timing['min_time'], elapsed)
        timing['max_time'] = max(timing['max_time'], elapsed)
        
        return elapsed
    
    def get_stats(self, name: str) -> Optional[Dict[str, Any]]:
        """
        获取计时器统计信息
        
        Args:
            name: 计时器名称
            
        Returns:
            统计信息字典，如果计时器不存在则返回 None
        """
        if name not in self._timings:
            return None
        
        timing = self._timings[name]
        avg_time = timing['total_time'] / timing['count'] if timing['count'] > 0 else 0.0
        
        return {
            'total_time': timing['total_time'],
            'count': timing['count'],
            'avg_time': avg_time,
            'min_time': timing['min_time'] if timing['min_time'] != float('inf') else 0.0,
            'max_time': timing['max_time']
        }
    
    def get_all_stats(self) -> Dict[str, Dict[str, Any]]:
        """
        获取所有计时器的统计信息
        
        Returns:
            所有计时器的统计信息字典
        """
        return {
            name: self.get_stats(name)
            for name in self._timings
        }
    
    def reset(self, name: Optional[str] = None) -> None:
        """
        重置计时器
        
        Args:
            name: 计时器名称，None 表示重置所有计时器
        """
        if name is None:
            self._timings.clear()
        elif name in self._timings:
            del self._timings[name]
    
    def log_stats(self, name: str) -> None:
        """
        记录计时器统计信息到日志
        
        Args:
            name: 计时器名称
        """
        stats = self.get_stats(name)
        if stats is None:
            logger.warning(f"No stats available for '{name}'")
            return
        
        logger.info(
            f"Performance '{name}': "
            f"total={stats['total_time']:.3f}s, "
            f"count={stats['count']}, "
            f"avg={stats['avg_time']:.3f}s, "
            f"min={stats['min_time']:.3f}s, "
            f"max={stats['max_time']:.3f}s"
        )


# 全局性能监控器实例
_monitor = PerformanceMonitor()


def get_performance_monitor() -> PerformanceMonitor:
    """
    获取全局性能监控器实例
    
    Returns:
        性能监控器实例
    """
    return _monitor


@contextmanager
def timing_context(name: str):
    """
    计时上下文管理器
    
    Args:
        name: 计时器名称
        
    Usage:
        with timing_context('operation_name'):
            # 代码块
    """
    _monitor.start(name)
    try:
        yield
    finally:
        elapsed = _monitor.stop(name)
        logger.debug(f"Operation '{name}' took {elapsed:.3f}s")


def timed(name: Optional[str] = None):
    """
    计时装饰器
    
    Args:
        name: 计时器名称，None 表示使用函数名
        
    Usage:
        @timed()
        def my_function():
            pass
            
        @timed('custom_name')
        def another_function():
            pass
    """
    def decorator(func):
        timer_name = name if name else func.__name__
        
        @wraps(func)
        def wrapper(*args, **kwargs):
            _monitor.start(timer_name)
            try:
                result = func(*args, **kwargs)
                return result
            finally:
                elapsed = _monitor.stop(timer_name)
                logger.debug(f"Function '{timer_name}' took {elapsed:.3f}s")
        
        return wrapper
    
    return decorator


@contextmanager
def profile_block(description: str, enabled: bool = True):
    """
    性能分析代码块
    
    Args:
        description: 描述信息
        enabled: 是否启用
        
    Usage:
        with profile_block("ASAR extraction"):
            # 代码块
    """
    if not enabled:
        yield
        return
    
    _monitor.start(description)
    try:
        yield
    finally:
        elapsed = _monitor.stop(description)
        logger.info(f"{description} took {elapsed:.3f}s")
