"""
输入验证装饰器和验证函数

提供路径验证、非空验证等常用验证功能。
"""

__all__ = [
    "ValidationError",
    "sanitize_text_input",
    "sanitize_user_path",
    "validate_path",
    "validate_not_empty",
]

import functools
import inspect
import os
from typing import Callable, List, Optional, Union

from utils.constants import MAX_PATH_LENGTH


class ValidationError(Exception):
    """验证错误异常"""

    pass


def sanitize_text_input(
    value: str,
    *,
    max_length: int = MAX_PATH_LENGTH,
    allow_empty: bool = True,
) -> str:
    """
    清理并验证用户输入文本，拒绝控制字符和超长输入。
    """
    if value is None:
        if allow_empty:
            return ""
        raise ValidationError("Null input is not allowed")

    text = str(value).strip()
    if not text:
        if allow_empty:
            return ""
        raise ValidationError("Empty input is not allowed")

    if len(text) > max_length:
        raise ValidationError(f"Input exceeds maximum length ({max_length})")

    if any(ord(ch) < 32 for ch in text):
        raise ValidationError("Input contains control characters")

    return text


def sanitize_user_path(path: str, *, allow_empty: bool = True, max_length: int = 4096) -> str:
    """
    清理并规范化用户输入路径。
    """
    text = sanitize_text_input(path, max_length=max_length, allow_empty=allow_empty)
    if not text:
        return ""

    normalized = os.path.normpath(os.path.abspath(text))
    if len(normalized) > max_length:
        raise ValidationError(f"Path exceeds maximum length ({max_length})")
    return normalized


def validate_path(
    arg_name: Union[str, List[str]],
    should_exist: bool = True,
    path_type: Optional[str] = None,
) -> Callable:
    """
    路径验证装饰器

    Args:
        arg_name: 需要验证的参数名，可以是单个字符串或字符串列表
        should_exist: 路径是否应该存在
        path_type: 路径类型 ('file', 'dir', None表示两者皆可)

    Returns:
        装饰器函数
    """
    if isinstance(arg_name, str):
        arg_names = [arg_name]
    else:
        arg_names = arg_name

    def decorator(func: Callable) -> Callable:
        sig = inspect.signature(func)

        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            bound_args = sig.bind(*args, **kwargs)
            bound_args.apply_defaults()

            for name in arg_names:
                if name in bound_args.arguments:
                    path = bound_args.arguments[name]
                    if path:
                        if should_exist and not os.path.exists(path):
                            raise ValidationError(f"Path does not exist: {path}")

                        if path_type == "file" and not os.path.isfile(path):
                            raise ValidationError(f"Not a file: {path}")

                        if path_type == "dir" and not os.path.isdir(path):
                            raise ValidationError(f"Not a directory: {path}")

            return func(*args, **kwargs)

        return wrapper

    return decorator


def validate_not_empty(*arg_names: str) -> Callable:
    """
    验证参数非空的装饰器

    Args:
        *arg_names: 需要验证非空的参数名列表
    """

    def decorator(func: Callable) -> Callable:
        sig = inspect.signature(func)

        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            bound_args = sig.bind(*args, **kwargs)
            bound_args.apply_defaults()

            names_to_check = arg_names if arg_names else bound_args.arguments.keys()

            for name in names_to_check:
                if name in bound_args.arguments:
                    val = bound_args.arguments[name]
                    str_val = str(val) if val is not None else ""
                    if not str_val.strip():
                        raise ValidationError(f"Empty or None argument not allowed: {name}")

            return func(*args, **kwargs)

        return wrapper

    return decorator
