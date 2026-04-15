"""
配置桥接模块 - 解决循环导入问题

提供语言模块与配置模块之间的间接交互，
避免 language.py 和 config.py 之间的直接循环导入。

使用观察者模式实现松耦合。
"""

from __future__ import annotations

import logging
import threading
from typing import Callable

logger = logging.getLogger(__name__)

# 线程锁保护回调注册表
_lock = threading.Lock()

# 语言设置回调注册表
_language_save_callbacks: list[Callable[[str], None]] = []
_language_load_callbacks: list[Callable[[], str | None]] = []

# 错误语言同步回调
_error_language_callbacks: list[Callable[[str], None]] = []


def register_language_save_callback(callback: Callable[[str], None]) -> None:
    """
    注册语言保存回调

    Args:
        callback: 接收语言代码的回调函数
    """
    with _lock:
        if callback not in _language_save_callbacks:
            _language_save_callbacks.append(callback)
            logger.debug(f"Registered language save callback: {callback.__name__}")


def register_language_load_callback(callback: Callable[[], str | None]) -> None:
    """
    注册语言加载回调

    Args:
        callback: 返回语言代码的可选回调函数
    """
    with _lock:
        if callback not in _language_load_callbacks:
            _language_load_callbacks.append(callback)
            logger.debug(f"Registered language load callback: {callback.__name__}")


def register_error_language_callback(callback: Callable[[str], None]) -> None:
    """
    注册错误语言同步回调

    Args:
        callback: 接收语言代码的回调函数
    """
    with _lock:
        if callback not in _error_language_callbacks:
            _error_language_callbacks.append(callback)
            logger.debug(f"Registered error language callback: {callback.__name__}")


def save_language_to_config(code: str) -> bool:
    """
    通过回调将语言保存到配置

    Args:
        code: 语言代码

    Returns:
        bool: 是否成功保存
    """
    success = False
    for callback in _language_save_callbacks:
        try:
            callback(code)
            success = True
        except Exception as e:
            logger.warning(f"Language save callback failed: {e}")
    return success


def load_language_from_config() -> str | None:
    """
    通过回调从配置加载语言

    Returns:
        Optional[str]: 语言代码，如果没有则返回 None
    """
    for callback in _language_load_callbacks:
        try:
            lang = callback()
            if lang:
                return lang
        except Exception as e:
            logger.debug(f"Language load callback failed: {e}")
    return None


def sync_error_language(code: str) -> None:
    """
    同步错误处理器的语言设置

    Args:
        code: 语言代码
    """
    for callback in _error_language_callbacks:
        try:
            callback(code)
        except Exception as e:
            logger.debug(f"Error language callback failed: {e}")


def unregister_all_callbacks() -> None:
    """清除所有回调（主要用于测试）"""
    global _language_save_callbacks, _language_load_callbacks, _error_language_callbacks
    with _lock:
        _language_save_callbacks.clear()
        _language_load_callbacks.clear()
        _error_language_callbacks.clear()
    logger.debug("All config bridge callbacks cleared")
