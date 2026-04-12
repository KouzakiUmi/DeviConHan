# -*- coding: utf-8 -*-
"""
补丁信息管理模块

提供补丁信息保存、读取和管理功能。
"""

import os
import json
import logging
import datetime

from utils.file_ops import compute_file_hash
from utils.paths import get_resource_path
from core.config import get_config

logger = logging.getLogger(__name__)

# Bug G 修复：移除此文件中从未被使用的 ASAR 格式常量重复定义。
# ASAR_MAGIC_NUMBER 等常量的权威定义在 utils/constants.py，
# 此处保留会误导维护者以为本文件内有 ASAR 解析逻辑。


def has_embedded_patch():
    """
    检测是否包含内置汉化补丁

    Returns:
        bool: 如果 Patch.zip 或 Patch 目录存在返回 True
    """
    config = get_config()
    patch_zip = os.path.join(get_resource_path("."), config.patch_zip_name)
    patch_dir = os.path.join(get_resource_path("."), config.patch_dir_name)
    return os.path.exists(patch_zip) or os.path.exists(patch_dir)


def _atomic_write_json(file_path, data):
    """
    原子写入 JSON 文件：先写 .tmp 临时文件，再 os.replace 原子替换。
    防止写入中途崩溃导致文件截断损坏（steam.py 依赖这些文件判断补丁状态）。
    """
    temp_file = file_path + ".tmp"
    try:
        with open(temp_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
            f.flush()
            os.fsync(f.fileno())
        os.replace(temp_file, file_path)
    except Exception:
        if os.path.exists(temp_file):
            try:
                os.remove(temp_file)
            except OSError:
                pass
        raise


def save_patch_info(base_dir, asar_path, bak_path):
    """
    保存补丁信息到 .patch_info 文件

    Args:
        base_dir: 基础目录
        asar_path: asar文件路径
        bak_path: 备份文件路径
    """
    patch_info_file = get_config().patch_info_file
    info_file = os.path.join(base_dir, patch_info_file)
    info = {
        "asar_path": asar_path,
        "bak_path": bak_path,
        "timestamp": datetime.datetime.now().isoformat(),
    }

    _atomic_write_json(info_file, info)

    logger.info(f"Saved patch info to: {info_file}")


def save_patch_meta(base_dir, temp_dir):
    """
    保存补丁元数据到 .patch_meta 文件

    Args:
        base_dir: 基础目录
        temp_dir: 临时目录
    """
    patch_meta_file = get_config().patch_meta_file
    meta_file = os.path.join(base_dir, patch_meta_file)

    meta_info = {"timestamp": datetime.datetime.now().isoformat(), "patch_files": {}}

    check_files = get_config().check_files_for_update
    for file_path in check_files:
        full_path = os.path.join(temp_dir, file_path)
        if os.path.exists(full_path):
            meta_info["patch_files"][file_path] = compute_file_hash(full_path)

    _atomic_write_json(meta_file, meta_info)

    logger.info(f"Saved patch meta to: {meta_file}")


# get_resource_path 已统一从 utils.paths 导入，此处删除局部副本。
# 修复说明：原实现在本文件底部重复定义了与 utils/paths.py 完全相同的
# get_resource_path 函数。局部副本不会受益于 utils/paths.py 的后续修改
# （如安全性增强），且 has_embedded_patch() 调用的是未经 normalize_path
# 处理的本地版本。修复方法：顶部 import，删除局部定义。
