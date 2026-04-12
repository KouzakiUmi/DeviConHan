# -*- coding: utf-8 -*-
"""
输入验证装饰器和验证函数

提供路径验证、非空验证等常用验证功能。
"""

__all__ = [
    "ValidationError",
    "validate_path",
    "validate_not_empty",
]

import functools
import inspect
import os
from typing import Callable, Optional, Union, List


class ValidationError(Exception):
    """验证错误异常"""

    pass


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
                    # 修复说明（M4）：原实现僅检查 str 类型，若参数为 None
                    # （Optional[str] 常见）则静默跳过。None 同样是不合法的空输入。
                    # 进一步修复：对于预期接收路径字符串的参数，传入 int(0)/ []/False
                    # 也应视为无效输入。修复：增加 not isinstance(val, str) 检查。
                    if val is None or not isinstance(val, str) or not val.strip():
                        raise ValidationError(
                            f"Empty or None argument not allowed: {name}"
                        )

            return func(*args, **kwargs)

        return wrapper

    return decorator
