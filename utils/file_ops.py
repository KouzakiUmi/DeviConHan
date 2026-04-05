# -*- coding: utf-8 -*-
"""
文件和目录操作模块

提供复制目录并校验哈希值等高级文件操作。
"""

import os
import shutil
import hashlib
import logging

logger = logging.getLogger(__name__)

def compute_file_hash(file_path: str) -> str:
    """计算文件的 SHA256 哈希值"""
    try:
        if not os.path.exists(file_path) or not os.path.isfile(file_path):
            return ""
        
        sha256_hash = hashlib.sha256()
        with open(file_path, "rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()
    except Exception as e:
        logger.error(f"Failed to compute hash for {file_path}: {e}")
        return ""

def migrate_backup(src: str, dest_dir: str) -> bool:
    """
    将备份文件或目录迁移到目标目录，
    复制后校验哈希值，如果校验通过则删除源文件/目录。
    
    Args:
        src: 源路径 (文件或目录)
        dest_dir: 目标目录的父路径 (备份将被放置于此目录中)
        
    Returns:
        bool: 迁移是否完全成功
    """
    basename = os.path.basename(src)
    dest_path = os.path.join(dest_dir, basename)
    
    # 防止同名文件或目录已经存在
    if os.path.exists(dest_path):
        logger.warning(f"Destination path already exists: {dest_path}")
        # 如果目标已经存在，并且哈希完全匹配？这里安全起见不覆盖
        # 但如果是续传或者冲突，可以直接在目标加一个后缀
        counter = 1
        while os.path.exists(dest_path):
            dest_path = os.path.join(dest_dir, f"{basename}_{counter}")
            counter += 1

    try:
        if os.path.isfile(src):
            # 复制单个文件
            shutil.copy2(src, dest_path)
            
            # 校验哈希
            src_hash = compute_file_hash(src)
            dest_hash = compute_file_hash(dest_path)
            
            if src_hash and dest_hash and src_hash == dest_hash:
                os.remove(src)
                logger.info(f"Successfully migrated backup file: {src} -> {dest_path}")
                return True
            else:
                logger.error(f"Hash mismatch after migrating file: {src}")
                # 清理损坏的副本
                if os.path.exists(dest_path):
                    os.remove(dest_path)
                return False
                
        elif os.path.isdir(src):
            # 复制目录
            shutil.copytree(src, dest_path)
            
            # 校验目录下所有文件哈希
            all_match = True
            for root, _, files in os.walk(src):
                for name in files:
                    src_file = os.path.join(root, name)
                    rel_path = os.path.relpath(src_file, src)
                    dest_file = os.path.join(dest_path, rel_path)
                    
                    if not os.path.exists(dest_file):
                        all_match = False
                        break
                        
                    src_hash = compute_file_hash(src_file)
                    dest_hash = compute_file_hash(dest_file)
                    
                    if not src_hash or src_hash != dest_hash:
                        all_match = False
                        break
                
                if not all_match:
                    break
                    
            if all_match:
                # 校验通过，删除源目录
                from utils.cleanup import force_cleanup_dir
                force_cleanup_dir(src)
                logger.info(f"Successfully migrated backup directory: {src} -> {dest_path}")
                return True
            else:
                logger.error(f"Hash mismatch after migrating directory: {src}")
                # 清理损坏的副本目录
                from utils.cleanup import force_cleanup_dir
                if os.path.exists(dest_path):
                    force_cleanup_dir(dest_path)
                return False
                
        else:
            logger.error(f"Source path is not a valid file or directory: {src}")
            return False
            
    except Exception as e:
        logger.exception(f"Exception occurred during migration of {src}: {e}")
        # 如果复制过程出错，尝试清理不完整的目标
        if os.path.exists(dest_path):
            try:
                if os.path.isfile(dest_path):
                    os.remove(dest_path)
                else:
                    from utils.cleanup import force_cleanup_dir
                    force_cleanup_dir(dest_path)
            except Exception:
                pass
        return False
