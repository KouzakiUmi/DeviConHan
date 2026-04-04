# -*- coding: utf-8 -*-

import os
import sys
import shutil
import mmap
import subprocess
import stat
import datetime
import threading
import zipfile
import logging
import argparse
import hashlib
import enum
import tempfile
from configparser import ConfigParser

from utils.paths import get_resource_path, normalize_path
from utils.language import T, init_lang

# 初始化多语言支持
init_lang()

logger = logging.getLogger(__name__)

# ================== 加载配置 ==================
from core.config import get_config

_config = get_config()

# ================== 常量（从配置读取） ==================
AUTO_TARGET_EXE = _config.auto_target_exe
FUSE_SENTINEL = _config.fuse_sentinel
BACKUP_PREFIX = _config.backup_prefix
PATCH_INFO_FILE = _config.patch_info_file
PATCH_META_FILE = _config.patch_meta_file
TIME_DIFF_THRESHOLD_DAYS = _config.time_diff_threshold_days

# 关键文件列表，用于检测Steam是否更新
# 这些文件在补丁中会被修改，如果Steam更新了游戏，这些文件的哈希会变化
CHECK_FILES_FOR_UPDATE = _config.check_files_for_update

# ================= 稳定文件列表（用于验证备份完整性） =================
# 这些文件是Electron应用的核心文件，不在补丁中，但游戏运行必须
# Steam更新后这些文件通常不会改变，用于验证.bak文件的完整性
STABLE_FILES_FOR_VALIDATION = _config.stable_files_for_validation

# ================= 异常类定义 =================
class PatcherError(Exception):
    """自定义异常类，用于区分不同类型的错误"""
    pass

class PatcherFileNotFoundError(PatcherError):
    """文件未找到异常"""
    pass

class PatcherPermissionError(PatcherError):
    """权限异常"""
    pass

class NodeNotFoundError(PatcherError):
    """Node.js未找到异常"""
    pass

class AsarCorruptedError(PatcherError):
    """asar文件损坏异常"""
    pass

# ================= Steam 更新状态枚举 =================
class UpdateStatus(enum.Enum):
    """Steam 更新检测状态，替代字符串匹配控制流"""
    FIRST_TIME = "first_time"                    # 首次打补丁，无 .bak 文件
    OLD_VERSION = "old_version"                  # 旧版本升级，缺少 .patch_info
    STEAM_UPDATED = "steam_updated"              # 确认被 Steam 更新
    TOOL_ISSUE = "tool_issue"                    # 工具问题导致误判（需用户确认）
    ALL_PASSED = "all_passed"                    # 检查通过，可安全恢复备份
    NO_BACKUP = "no_backup"                      # 无 .bak 文件


# ================= 核心逻辑类 (Worker) =================
class CoreLogic:
    def __init__(self):
        """
        初始化核心逻辑
        
        Args:
            log_callback: 日志回调函数，用于GUI模式
            
        Raises:
            PatcherFileNotFoundError: 如果必要的资源文件不存在
        """
        self.node_path = get_resource_path(os.path.join("tools", "node.exe"))
        self.script_path = self._find_script()
        
        # 验证必要文件存在
        if not os.path.exists(self.node_path):
            raise PatcherFileNotFoundError(f"Node.js executable not found: {self.node_path}")
            
        if not self.script_path or not os.path.exists(self.script_path):
            raise PatcherFileNotFoundError(f"Patcher script not found")
        
        # 直接使用内置工具，不再检测系统环境
        self.mode = 'bundled'
        
        logger.info(f"CoreLogic initialized. Mode: {self.mode}")
        logger.debug(f"Node path: {self.node_path}")
        logger.debug(f"Script path: {self.script_path}")

    def _find_script(self):
        """
        查找 ASAR 命令行脚本
        
        Returns:
            脚本文件路径，未找到返回None
        """
        tools = get_resource_path("tools")
        candidates = [
            os.path.join(tools, "asar_cli.mjs"),          # 优先使用新的 CLI 工具
            os.path.join(tools, "bundled_asar", "index.mjs"),
            os.path.join(tools, "bundled_asar", "index.js")
        ]
        
        for p in candidates:
            if os.path.exists(p):
                logger.debug(f"Found script: {p}")
                return p
        
        logger.warning("No ASAR script found")
        return None

    def remove_readonly(self, func, path, excinfo):
        """删除只读属性的回调函数"""
        try:
            os.chmod(path, stat.S_IWRITE)
            func(path)
        except Exception as e:
            logger.debug(f"Failed to remove readonly: {e}")

    def run_asar(self, action, src, dest, callback=None, unpack_pattern=None):
        """
        执行ASAR操作（解包或打包）- 固定使用内置依赖库
        
        Args:
            action: 操作类型 ("extract" 或 "pack")
            src: 源文件/目录路径
            dest: 目标路径
            callback: 回调函数，用于更新进度
            unpack_pattern: 排除模式（仅打包时使用）
            
        Raises:
            NodeNotFoundError: 如果Node.js未找到
            PatcherError: 如果操作失败
            
        Returns:
            bool: 操作是否成功
        """
        logger.info(f"Running ASAR {action} operation")
        
        # 验证输入参数
        src = normalize_path(src)
        dest = normalize_path(dest)
        
        if not src or not os.path.exists(src):
            raise PatcherFileNotFoundError(f"Source path does not exist: {src}")
            
        if action == "extract" and not os.path.isfile(src):
            raise PatcherError(f"Source must be a file for extraction: {src}")
        
        # 设置默认排除模式
        if not unpack_pattern:
            unpack_pattern = "*.{node,dll,so,dylib,exe,bin}"
        
        try:
            # 固定使用内置工具
            cmd = [self.node_path, self.script_path, action, src, dest]
            if action == "pack": 
                cmd.extend(["--unpack", unpack_pattern])
            
            logger.debug(f"Using bundled Node.js: {self.node_path}")
            logger.debug(f"Command: {" ".join(cmd)}")
            
            # 执行命令
            if callback:
                callback(f"Executing: {action}...")
            
            creationflags = 0
            if sys.platform.startswith("win"):
                creationflags = subprocess.CREATE_NO_WINDOW
            
            proc = subprocess.run(
                cmd,
                shell=False,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding="utf-8",
                errors="replace",
                creationflags=creationflags,
                timeout=300  # 5分钟超时
            )
            
            if proc.returncode != 0:
                error_msg = f"ASAR {action} failed with code {proc.returncode}"
                if proc.stdout:
                    logger.error(f"Output: {proc.stdout}")
                raise PatcherError(error_msg)
            
            logger.info(f"ASAR {action} completed successfully")
            if callback:
                callback("Asar operation success.")
            return True
            
        except subprocess.TimeoutExpired:
            error_msg = f"Operation timed out after 300 seconds"
            logger.error(error_msg)
            raise PatcherError(error_msg)
            
        except Exception as e:
            logger.exception(f"ASAR operation failed: {e}")
            if isinstance(e, (NodeNotFoundError, PatcherFileNotFoundError)):
                raise
            raise PatcherError(str(e))

    def remove_fuse(self, exe_path, callback=None):
        """
        移除游戏可执行文件的Fuse完整性校验
        
        Args:
            exe_path: 游戏可执行文件路径
            callback: 回调函数
            
        Returns:
            bool: 是否成功移除Fuse
        """
        logger.info(f"Attempting to remove Fuse from: {exe_path}")
        
        # 验证输入参数
        try:
            if not exe_path or not isinstance(exe_path, str):
                logger.warning("Invalid executable path")
                return False
            
            exe_path = normalize_path(exe_path)
            
            if not os.path.exists(exe_path):
                logger.error(f"Executable file does not exist: {exe_path}")
                return False
                
            if not os.path.isfile(exe_path):
                logger.error(f"Not a file: {exe_path}")
                return False
            
            # 检查文件大小
            file_size = os.path.getsize(exe_path)
            if file_size < 1024:
                logger.warning(f"File too small to contain Fuse data: {file_size} bytes")
                return False
                
        except Exception as e:
            logger.error(f"Failed to validate executable path: {e}")
            return False
        
        try:
            # 移除只读属性
            os.chmod(exe_path, stat.S_IWRITE)
            
            with open(exe_path, "r+b") as f:
                with mmap.mmap(f.fileno(), 0) as mm:
                    offset = mm.find(FUSE_SENTINEL)
                    
                    if offset == -1:
                        logger.info("Fuse sentinel not found - already removed or never present")
                        return False
                    
                    target = offset + 34 + 4
                    
                    # 边界检查
                    if target >= mm.size():
                        logger.error(f"Target position {target} exceeds file size {mm.size()}")
                        return False
                    
                    current_byte = mm[target:target+1]
                    
                    if current_byte == b"\x31":
                        mm[target:target+1] = b"\x30"
                        logger.info("Fuse checksum byte modified (0x31 -> 0x30)")
                        if callback:
                            callback("Fuse removed.")
                        return True
                    elif current_byte == b"\x30":
                        logger.info("Fuse already disabled")
                        return True
                    else:
                        logger.warning(f"Unexpected byte at target position: {current_byte}")
                        return False
                        
            logger.info("Fuse operation completed successfully")
            return True
            
        except mmap.error as e:
            logger.error(f"MMap error: {e}")
            return False
        except Exception as e:
            logger.exception(f"Failed to remove Fuse: {e}")
            if callback:
                callback(f"Fuse Error: {e}")
            return False

def _extract_and_get_file_info(asar_path, file_paths=None, core=None):
    """
    通过解包asar文件获取文件信息（大小、哈希等）
    
    这是修复后的核心函数，替代原来有问题的get_asar_file_size()。
    
    Args:
        asar_path: asar 文件路径
        file_paths: 要获取信息的文件路径列表（None表示获取所有CHECK_FILES_FOR_UPDATE）
        core: CoreLogic 实例（必须提供）
        
    Returns:
        dict: {file_path: {"size": int, "hash": str}} 或空字典（如果失败）
    """
    import tempfile
    import atexit
    
    if core is None:
        raise ValueError("core parameter is required for _extract_and_get_file_info")
    
    temp_dir = None
    result = {}
    
    try:
        # 创建临时目录
        temp_dir = tempfile.mkdtemp(prefix="asar_extract_")
        
        # 注册清理函数，确保即使程序崩溃也能清理
        def cleanup_temp_dir():
            if temp_dir and os.path.exists(temp_dir):
                try:
                    shutil.rmtree(temp_dir, onerror=core.remove_readonly)
                    logger.debug(f"Cleaned up temp directory: {temp_dir}")
                except Exception as cleanup_err:
                    logger.warning(f"Failed to cleanup temp directory: {cleanup_err}")
        
        atexit.register(cleanup_temp_dir)
        
        # 解包asar文件
        core.run_asar("extract", asar_path, temp_dir)
        
        # 确定要检查的文件列表
        if file_paths is None:
            file_paths = CHECK_FILES_FOR_UPDATE
        
        # 获取每个文件的信息
        for rel_path in file_paths:
            full_path = os.path.join(temp_dir, rel_path)
            if os.path.exists(full_path):
                file_size = os.path.getsize(full_path)
                file_hash = compute_file_hash(full_path)
                result[rel_path] = {
                    "size": file_size,
                    "hash": file_hash
                }
            else:
                logger.debug(f"File not found in extracted asar: {rel_path}")
                
    except Exception as e:
        logger.error(f"Failed to extract and get file info from {asar_path}: {e}")
        return {}
    finally:
        # 立即清理临时目录
        if temp_dir and os.path.exists(temp_dir):
            try:
                shutil.rmtree(temp_dir, onerror=core.remove_readonly)
                logger.debug(f"Cleaned up temp directory: {temp_dir}")
            except Exception as cleanup_err:
                logger.warning(f"Failed to cleanup temp directory: {cleanup_err}")
    
    return result

def _remove_readonly_handler(func, path, excinfo):
    """删除只读属性的回调函数"""
    import stat
    try:
        os.chmod(path, stat.S_IWRITE)
        func(path)
    except Exception as e:
        logger.debug(f"Failed to remove readonly: {e}")

def get_asar_file_info(asar_path, file_path, core=None):
    """
    获取 asar 包中指定文件的完整信息（不解包）
    
    使用 asar 的 statFile API 获取文件信息，包括大小、偏移量、可执行标志等
    
    Args:
        asar_path: asar 文件路径
        file_path: asar 中要查询的文件路径（如 data/others/craftmincho.ttf）
        core: CoreLogic 实例（必须提供）

    Returns:
        dict: 文件信息字典，包含 size, offset, executable 等字段
        None: 如果文件不存在或无法访问
        
    Raises:
        AsarCorruptedError: 如果asar文件损坏或无法访问
        ValueError: 如果 core 参数为 None
    """
    import json
    
    if core is None:
        raise ValueError("core parameter is required for get_asar_file_info")
    
    try:
        # 使用 asar 的 statFile API（不解包）
        cmd = [core.node_path, core.script_path, 'stat', asar_path, file_path]
        proc_result = subprocess.run(cmd, capture_output=True, text=True, timeout=30, encoding='utf-8')
        
        # 检查命令执行状态
        if proc_result.returncode != 0:
            # 解析错误信息
            try:
                error_data = json.loads(proc_result.stderr.strip())
                error_type = error_data.get("error_type", "unknown")
                if error_type == "file_not_found":
                    logger.debug(f"File not found in ASAR: {file_path}")
                    return None
                elif error_type == "file_corrupted":
                    raise AsarCorruptedError(f"ASAR file is corrupted: {error_data.get('error')}")
                else:
                    raise AsarCorruptedError(f"ASAR stat failed: {error_data.get('error')}")
            except json.JSONDecodeError:
                raise AsarCorruptedError(f"Failed to parse ASAR stat error response: {proc_result.stderr}")
        
        # 解析成功响应
        data = json.loads(proc_result.stdout.strip())
        if data.get("success"):
            return {
                "size": data.get("size"),
                "offset": data.get("offset"),
                "executable": data.get("executable"),
                "mtime": data.get("mtime"),
                "atime": data.get("atime")
            }
        else:
            error_type = data.get("error_type", "unknown")
            if error_type == "file_not_found":
                logger.debug(f"File not found in ASAR: {file_path}")
                return None
            raise AsarCorruptedError(f"ASAR stat failed: {data.get('error')}")
            
    except subprocess.TimeoutExpired:
        raise AsarCorruptedError(f"ASAR stat operation timed out for {file_path}")
    except json.JSONDecodeError as e:
        raise AsarCorruptedError(f"Failed to parse ASAR stat response: {e}")
    except Exception as e:
        raise AsarCorruptedError(f"Failed to get file info from ASAR: {e}")


def get_asar_file_size(asar_path, file_path, core=None):
    """
    获取 asar 包中指定文件的大小（三层容错版）
    
    优先级：
    1. 使用asar的statFile API（最快，不解压）
    2. 失败则提取单个文件到临时目录（较快）
    3. 仍然失败则抛出AsarCorruptedError（文件损坏）

    Args:
        asar_path: asar 文件路径
        file_path: asar 中要查询的文件路径（如 data/others/craftmincho.ttf）
        core: CoreLogic 实例（必须提供）

    Returns:
        int: 文件大小（字节），如果文件不存在则返回 None
        
    Raises:
        AsarCorruptedError: 如果asar文件损坏或无法访问
        ValueError: 如果 core 参数为 None
    """
    import tempfile
    
    if core is None:
        raise ValueError("core parameter is required for get_asar_file_size")
    
    try:
        # 第一层：使用asar的statFile API（不解压）
        file_info = get_asar_file_info(asar_path, file_path, core)
        if file_info is not None:
            logger.debug(f"Got file size from statFile API for {file_path}: {file_info['size']}")
            return file_info["size"]
        
        # 文件不存在，返回None而不是抛出异常
        return None
        
    except AsarCorruptedError as e:
        logger.debug(f"statFile API failed for {file_path}: {e}, trying fallback method")
        # 继续尝试第二层
    
    # 第二层：提取单个文件到临时目录
    temp_dir = None
    try:
        temp_dir = tempfile.mkdtemp(dir=".")
        extracted_file_path = os.path.join(temp_dir, os.path.basename(file_path))
        cmd_extract = [core.node_path, core.script_path, 'extract-file', asar_path, file_path]
        subprocess.run(cmd_extract, capture_output=True, text=True, timeout=30, check=True, cwd=temp_dir, encoding='utf-8')
        file_size = os.path.getsize(extracted_file_path)
        logger.debug(f"Got file size from extraction for {file_path}: {file_size}")
        return file_size
        
    except subprocess.CalledProcessError as e:
        # 提取失败，检查是否是文件不存在还是asar损坏
        error_output = e.stderr.lower() if e.stderr else ""
        if 'not found' in error_output or 'no such file' in error_output:
            logger.debug(f"File not found in ASAR: {file_path}")
            return None
        # 其他错误视为asar损坏
        raise AsarCorruptedError(
            f'ASAR file "{asar_path}" is corrupted or invalid. '
            f'Cannot access file "{file_path}".'
        )
    except Exception as e:
        raise AsarCorruptedError(
            f'Failed to get file size for "{file_path}" from ASAR: {e}'
        )
    finally:
        # 确保临时目录被清理
        if temp_dir and os.path.exists(temp_dir):
            try:
                shutil.rmtree(temp_dir)
            except Exception as cleanup_err:
                logger.warning(f"Failed to cleanup temp directory in get_asar_file_size: {cleanup_err}")

def validate_asar_file(asar_path, file_paths=None, core=None):
    """
    验证asar文件的完整性
    
    Args:
        asar_path: asar 文件路径
        file_paths: 要验证的文件路径列表（None表示使用STABLE_FILES_FOR_VALIDATION）
        core: CoreLogic 实例（必须提供）
        
    Returns:
        dict: {file_path: {"size": int, "hash": str}} 或空字典（如果失败）
        
    Raises:
        AsarCorruptedError: 如果asar文件损坏或无法访问
        ValueError: 如果 core 参数为 None
    """
    import json
    
    if core is None:
        raise ValueError("core parameter is required for validate_asar_file")
    
    if file_paths is None:
        file_paths = STABLE_FILES_FOR_VALIDATION

    result = {}
    logger.info(f"Validating ASAR file: {asar_path}")
    
    for rel_path in file_paths:
        temp_dir = None
        try:
            # First, try to get stats without extraction
            cmd = [core.node_path, core.script_path, 'stat', asar_path, rel_path]
            proc_result = subprocess.run(cmd, capture_output=True, text=True, timeout=30, check=True, encoding='utf-8')
            data = json.loads(proc_result.stdout.strip())
            
            # Now, get hash by extracting single file to temp
            temp_dir = tempfile.mkdtemp(dir=".")
            try:
                extracted_file_path = os.path.join(temp_dir, os.path.basename(rel_path))
                cmd_extract = [core.node_path, core.script_path, 'extract-file', asar_path, rel_path]
                subprocess.run(cmd_extract, capture_output=True, text=True, timeout=30, check=True, cwd=temp_dir, encoding='utf-8')
                
                file_hash = compute_file_hash(extracted_file_path)
                result[rel_path] = {
                    "size": data["size"],
                    "hash": file_hash
                }
                logger.debug(f"Validated file: {rel_path} (size: {data['size']})")
            finally:
                # 确保临时目录被清理
                if temp_dir and os.path.exists(temp_dir):
                    try:
                        shutil.rmtree(temp_dir)
                    except Exception as cleanup_err:
                        logger.warning(f"Failed to cleanup temp dir for {rel_path}: {cleanup_err}")
                    temp_dir = None
                        
        except subprocess.CalledProcessError as e:
            # 解析 stderr 中的 JSON 错误信息
            try:
                error_data = json.loads(e.stderr.strip())
                error_type = error_data.get("error_type", "unknown")
                if error_type == "file_not_found":
                    logger.debug(f"File not found in ASAR: {rel_path}, skipping validation")
                    continue  # 跳过不存在的文件
                elif error_type == "file_corrupted":
                    logger.error(f"ASAR file is corrupted (validation failed for {rel_path}): {error_data.get('error')}")
                    raise AsarCorruptedError(f"ASAR file is corrupted: {error_data.get('error')}")
                else:
                    logger.warning(f"ASAR stat failed for {rel_path}: {error_data.get('error')}, skipping")
                    continue  # 跳过有问题的文件
            except json.JSONDecodeError:
                logger.warning(f"Failed to parse error response for {rel_path}: {e.stderr}, skipping")
                continue  # 跳过有问题的文件
        except (FileNotFoundError, json.JSONDecodeError) as e:
            logger.warning(f"Fast path for validation failed for {rel_path}: {e}, trying fallback")
            # Fallback: extract single file to get info
            temp_dir = None
            try:
                temp_dir = tempfile.mkdtemp(dir=".")
                try:
                    extracted_file_path = os.path.join(temp_dir, os.path.basename(rel_path))
                    cmd_extract = [core.node_path, core.script_path, 'extract-file', asar_path, rel_path]
                    subprocess.run(cmd_extract, capture_output=True, text=True, timeout=30, check=True, cwd=temp_dir, encoding='utf-8')
                    
                    file_size = os.path.getsize(extracted_file_path)
                    file_hash = compute_file_hash(extracted_file_path)
                    result[rel_path] = {
                        "size": file_size,
                        "hash": file_hash
                    }
                    logger.debug(f"Validated file (fallback): {rel_path} (size: {file_size})")
                finally:
                    # 确保临时目录被清理
                    if temp_dir and os.path.exists(temp_dir):
                        try:
                            shutil.rmtree(temp_dir)
                        except Exception as cleanup_err:
                            logger.warning(f"Failed to cleanup temp dir for {rel_path}: {cleanup_err}")
                        temp_dir = None
            except Exception as e2:
                logger.error(f"Fallback extraction failed for {rel_path}: {e2}")
                raise AsarCorruptedError(f"Failed to validate file: {rel_path}") from e2

    logger.info(f"ASAR validation complete. Validated {len(result)}/{len(file_paths)} files")
    return result

def get_asar_font_sizes(asar_path, core=None):
    """
    获取 asar 中所有字体文件的大小（修复版）

    Args:
        asar_path: asar 文件路径
        core: CoreLogic 实例（必须提供）

    Returns:
        dict: {font_file_path: size_in_bytes}
    """
    if core is None:
        raise ValueError("core parameter is required for get_asar_font_sizes")
    
    font_files = [
        "data/others/craftmincho.ttf",
        "data/others/DZUYOKU.ttf",
        "data/others/funwari-round.ttf",
        "data/others/HeadUpDaisy.ttf"
    ]

    try:
        all_file_info = _extract_and_get_file_info(asar_path, font_files, core)
        # 只提取size信息
        sizes = {}
        for font_file in font_files:
            if font_file in all_file_info:
                sizes[font_file] = all_file_info[font_file]["size"]
        return sizes
    except Exception as e:
        logger.error(f"Failed to get font sizes from {asar_path}: {e}")
        return {}

def has_embedded_patch():
    """
    检测是否包含内置汉化补丁
    
    Returns:
        bool: 如果 Patch 目录存在返回 True
    """
    patch_dir = os.path.join(get_resource_path("."), "Patch")
    return os.path.exists(patch_dir)

# ================= 补丁信息管理 =================

def compute_file_hash(file_path):
    """
    计算文件的SHA256哈希值
    
    Args:
        file_path: 文件路径
        
    Returns:
        str: 文件的SHA256哈希值（十六进制字符串），失败返回None
    """
    try:
        if not os.path.exists(file_path):
            logger.warning(f"File not found for hash computation: {file_path}")
            return None
            
        if not os.path.isfile(file_path):
            logger.warning(f"Path is not a file: {file_path}")
            return None
            
        sha256_hash = hashlib.sha256()
        with open(file_path, "rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()
    except PermissionError as e:
        logger.error(f"Permission denied when computing hash for {file_path}: {e}")
        return None
    except IOError as e:
        logger.error(f"IO error when computing hash for {file_path}: {e}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error when computing hash for {file_path}: {e}")
        return None

def save_patch_info(base_dir, asar_path, bak_path):
    """
    保存补丁信息到 .patch_info 文件
    
    Args:
        base_dir: 基础目录
        asar_path: asar文件路径
        bak_path: 备份文件路径
    """
    info_file = os.path.join(base_dir, PATCH_INFO_FILE)
    info = {
        "asar_path": asar_path,
        "bak_path": bak_path,
        "timestamp": datetime.datetime.now().isoformat()
    }
    
    with open(info_file, "w", encoding="utf-8") as f:
        import json
        json.dump(info, f, indent=2, ensure_ascii=False)
    
    logger.info(f"Saved patch info to: {info_file}")

def save_patch_meta(base_dir, temp_dir):
    """
    保存补丁元数据到 .patch_meta 文件
    
    Args:
        base_dir: 基础目录
        temp_dir: 临时目录
    """
    meta_file = os.path.join(base_dir, PATCH_META_FILE)
    
    # 收集补丁文件的信息
    meta_info = {
        "timestamp": datetime.datetime.now().isoformat(),
        "patch_files": {}
    }
    
    # 记录关键文件的哈希值
    for file_path in CHECK_FILES_FOR_UPDATE:
        full_path = os.path.join(temp_dir, file_path)
        if os.path.exists(full_path):
            meta_info["patch_files"][file_path] = compute_file_hash(full_path)
    
    with open(meta_file, "w", encoding="utf-8") as f:
        import json
        json.dump(meta_info, f, indent=2, ensure_ascii=False)
    
    logger.info(f"Saved patch meta to: {meta_file}")

def handle_steam_update(core, base_dir, bak_path, asar_path=None, log_callback=None, gui_app=None):
    """
    处理Steam更新检测和文件状态检查
    
    检测逻辑：
    1. ASAR 存在，备份不存在 → 首次打补丁或已使用其他补丁工具
    2. ASAR 存在，备份存在 → 检查补丁信息，判断是否需要重新打补丁
    3. ASAR 不存在，备份存在 → Steam 更新后自动恢复备份
    4. ASAR 不存在，备份不存在 → 游戏文件损坏或安装不完整
    
    Args:
        core: CoreLogic 实例
        base_dir: 基础目录
        bak_path: 备份文件路径
        asar_path: asar文件路径（可选，用于验证文件存在性）
        log_callback: 日志回调函数
        gui_app: GUI应用实例（用于显示对话框）
        
    Returns:
        tuple: (should_continue, cancel_or_error)
            should_continue: 是否应该继续打补丁
            cancel_or_error: 是否因为错误或用户取消而停止
    """
    if log_callback:
        log_callback("Checking for Steam updates...")
    
    # 检查 ASAR 文件状态
    asar_exists = asar_path and os.path.exists(asar_path)
    bak_exists = os.path.exists(bak_path)
    
    # 情况 4：ASAR 和备份都不存在 → 游戏文件损坏或安装不完整
    if not asar_exists and not bak_exists:
        logger.error("Neither ASAR nor backup file exists - game files may be corrupted or incomplete")
        if gui_app:
            from tkinter import messagebox
            messagebox.showerror(
                T('title_game_files_missing'),
                T('msg_game_files_missing')
            )
        return (False, True)
    
    # 情况 3：ASAR 不存在，备份存在 → Steam 更新后恢复备份
    if not asar_exists and bak_exists:
        logger.warning("ASAR file missing but backup exists - possible Steam update detected")
        
        # 验证备份文件的完整性
        if not _validate_backup_integrity(bak_path, core):
            logger.error("Backup file is corrupted")
            if gui_app:
                from tkinter import messagebox
                messagebox.showerror(
                    T('title_backup_corrupted'),
                    T('msg_backup_corrupted')
                )
            return (False, True)
        
        # 备份有效，询问用户是否恢复
        if gui_app:
            from tkinter import messagebox
            result = messagebox.askyesno(
                T('title_asar_missing'),
                T('msg_asar_missing_valid_backup')
            )
            if not result:
                return (False, True)
            return (True, False)
        else:
            # 批处理模式：自动恢复备份
            logger.info("Restoring ASAR from backup...")
            try:
                shutil.copy2(bak_path, asar_path)
                logger.info(f"Successfully restored ASAR from backup: {bak_path}")
                return (True, False)
            except Exception as e:
                logger.error(f"Failed to restore ASAR from backup: {e}")
                return (False, True)
    
    # 情况 1：ASAR 存在，备份不存在 → 首次打补丁或已使用其他补丁工具
    if asar_exists and not bak_exists:
        logger.info(T('msg_asar_exists_no_backup'))
        # 检查 ASAR 文件是否有效
        if not _validate_asar_integrity(asar_path, core):
            logger.error("ASAR file is corrupted")
            if gui_app:
                from tkinter import messagebox
                messagebox.showerror(
                    T('title_asar_corrupted'),
                    T('msg_asar_corrupted')
                )
            return (False, True)
        
        # ASAR 文件有效，可以继续打补丁
        return (True, False)
    
    # 情况 2：ASAR 存在，备份存在 → 检查补丁信息，判断是否需要重新打补丁
    if asar_exists and bak_exists:
        logger.info("Both ASAR and backup exist - checking patch status")
        
        # 验证备份文件的完整性
        if not _validate_backup_integrity(bak_path, core):
            logger.warning("Backup file is corrupted, but ASAR is valid")
            if gui_app:
                from tkinter import messagebox
                result = messagebox.askyesno(
                    T('title_backup_corrupted_asar_valid'),
                    T('msg_backup_corrupted_asar_valid')
                )
                if not result:
                    return (False, True)
            return (True, False)
        
        # 检查补丁信息文件
        info_file = os.path.join(base_dir, PATCH_INFO_FILE)
        if not os.path.exists(info_file):
            logger.warning("Patch info file missing - may be old version patch or used other tools")
            if gui_app:
                from tkinter import messagebox
                result = messagebox.askyesno(
                    T('title_no_patch_info'),
                    T('msg_no_patch_info')
                )
                return (result, not result)
            return (True, False)
        
        # 读取并验证补丁信息
        try:
            patch_info = _read_and_validate_patch_info(info_file)
            if patch_info is None:
                # 文件损坏或被删除，继续执行
                return (True, False)
            
            # 检查时间差，超过阈值显示警告但仍继续
            patch_time = datetime.datetime.fromisoformat(patch_info.get("timestamp", ""))
            time_diff = datetime.datetime.now() - patch_time
            
            if time_diff.days > TIME_DIFF_THRESHOLD_DAYS:
                logger.warning(f"Patch was applied {time_diff.days} days ago")
                if gui_app:
                    from tkinter import messagebox
                    result = messagebox.askyesno(
                        T('title_old_patch_detected'),
                        T('msg_old_patch_detected').format(days=time_diff.days)
                    )
                    if not result:
                        return (False, True)
        except Exception as e:
            logger.warning(f"Failed to check patch time: {e}")
        
        logger.info("Steam update check passed")
        return (True, False)
    
    # 默认情况（理论上不会到达这里）
    logger.warning("Unexpected file state, proceeding with caution")
    return (True, False)

def _validate_asar_integrity(asar_path, core):
    """
    验证 ASAR 文件的完整性
    
    Args:
        asar_path: ASAR 文件路径
        core: CoreLogic 实例
        
    Returns:
        bool: 文件是否有效
    """
    import json
    
    try:
        # 检查文件大小
        file_size = os.path.getsize(asar_path)
        if file_size < 1024:  # 小于 1KB 可能是损坏的
            logger.warning(f"ASAR file too small: {file_size} bytes")
            return False
        
        # 尝试读取 ASAR 文件的基本信息
        try:
            cmd = [core.node_path, core.script_path, 'stat', asar_path, 'package.json']
            proc_result = subprocess.run(cmd, capture_output=True, text=True, timeout=10, check=True, encoding='utf-8')
            data = json.loads(proc_result.stdout.strip())
            if not data.get("success"):
                error_type = data.get("error_type", "unknown")
                if error_type == "file_not_found":
                    logger.warning(f"File not found in ASAR: package.json")
                    return False
                elif error_type == "file_corrupted":
                    logger.warning(f"ASAR file is corrupted: {data.get('error')}")
                    return False
                else:
                    logger.warning(f"ASAR stat failed: {data.get('error')}")
                    return False
        except subprocess.CalledProcessError as e:
            # 解析 stderr 中的 JSON 错误信息
            try:
                error_data = json.loads(e.stderr.strip())
                error_type = error_data.get("error_type", "unknown")
                if error_type == "file_not_found":
                    logger.warning(f"File not found in ASAR: package.json")
                    return False
                elif error_type == "file_corrupted":
                    logger.warning(f"ASAR file is corrupted: {error_data.get('error')}")
                    return False
                else:
                    logger.warning(f"ASAR stat failed: {error_data.get('error')}")
                    return False
            except json.JSONDecodeError:
                logger.warning(f"Failed to parse error response: {e.stderr}")
                return False
        except Exception as e:
            logger.warning(f"Failed to validate ASAR integrity: {e}")
            return False
        
        return True
    except Exception as e:
        logger.error(f"Error validating ASAR integrity: {e}")
        return False

def _validate_backup_integrity(bak_path, core):
    """
    验证备份文件的完整性
    
    Args:
        bak_path: 备份文件路径
        core: CoreLogic 实例
        
    Returns:
        bool: 文件是否有效
    """
    import json
    
    try:
        # 检查文件大小
        file_size = os.path.getsize(bak_path)
        if file_size < 1024:  # 小于 1KB 可能是损坏的
            logger.warning(f"Backup file too small: {file_size} bytes")
            return False
        
        # 尝试读取备份文件的基本信息
        try:
            cmd = [core.node_path, core.script_path, 'stat', bak_path, 'package.json']
            proc_result = subprocess.run(cmd, capture_output=True, text=True, timeout=10, check=True, encoding='utf-8')
            data = json.loads(proc_result.stdout.strip())
            if not data.get("success"):
                error_type = data.get("error_type", "unknown")
                if error_type == "file_not_found":
                    logger.warning(f"File not found in backup: package.json")
                    return False
                elif error_type == "file_corrupted":
                    logger.warning(f"Backup file is corrupted: {data.get('error')}")
                    return False
                else:
                    logger.warning(f"Backup stat failed: {data.get('error')}")
                    return False
        except subprocess.CalledProcessError as e:
            # 解析 stderr 中的 JSON 错误信息
            try:
                error_data = json.loads(e.stderr.strip())
                error_type = error_data.get("error_type", "unknown")
                if error_type == "file_not_found":
                    logger.warning(f"File not found in backup: package.json")
                    return False
                elif error_type == "file_corrupted":
                    logger.warning(f"Backup file is corrupted: {error_data.get('error')}")
                    return False
                else:
                    logger.warning(f"Backup stat failed: {error_data.get('error')}")
                    return False
            except json.JSONDecodeError:
                logger.warning(f"Failed to parse error response: {e.stderr}")
                return False
        except Exception as e:
            logger.warning(f"Failed to validate backup integrity: {e}")
            return False
        
        return True
    except Exception as e:
        logger.error(f"Error validating backup integrity: {e}")
        return False

def _read_and_validate_patch_info(info_file):
    """
    读取并验证补丁信息文件
    
    Args:
        info_file: 补丁信息文件路径
        
    Returns:
        dict: 补丁信息，如果验证失败返回 None
    """
    try:
        # 检查文件大小
        file_size = os.path.getsize(info_file)
        if file_size == 0:
            logger.warning("Patch info file is empty")
            return None
        
        # 读取 JSON 内容
        with open(info_file, "r", encoding="utf-8") as f:
            import json
            content = f.read().strip()
            if not content:
                logger.warning("Patch info file contains only whitespace")
                return None
            
            patch_info = json.loads(content)
            return patch_info
            
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse patch info JSON: {e}")
        return None
    except Exception as e:
        logger.error(f"Failed to read patch info: {e}")
        return None

def batch_mode(args):
    """
    批处理模式
    
    Args:
        args: 命令行参数
        
    Returns:
        int: 退出码 (0=成功, 非0=错误)
    """
    logger.info("Running in batch mode")
    
    try:
        core = CoreLogic()
    except Exception as e:
        logger.error(f"Failed to initialize CoreLogic: {e}")
        return 1
    
    base = os.path.abspath(".")
    res = os.path.join(base, "resources")
    asar = os.path.join(res, "app.asar")
    bak = asar + ".bak"
    
    # 检查资源目录
    if not os.path.exists(res):
        logger.error("Resources directory not found")
        return 1
    
    # 处理Steam更新
    logger.info("Checking for Steam updates...")
    should_continue, cancel_or_error = handle_steam_update(
        core, base, bak, asar
    )
    
    if cancel_or_error or not should_continue:
        return 1
    
    # 检查asar文件
    if not os.path.exists(asar):
        logger.error("app.asar not found")
        return 1
    
    # 自动检测并打补丁
    if args.auto:
        logger.info("Auto-detect and patch mode")
        
        # 创建备份
        if not os.path.exists(bak):
            logger.info(f"Creating backup: {bak}")
            try:
                shutil.copy2(asar, bak)
                logger.info(f"Backup created successfully: {bak}")
            except Exception as backup_err:
                logger.error(f"Failed to create backup: {backup_err}")
                return 1
        else:
            # 备份已存在，提醒用户这是重新打补丁
            logger.warning(f"Backup already exists: {bak} - this appears to be a re-patch operation")
        
        # 解包
        temp = os.path.join(base, "temp_patch")
        if os.path.exists(temp):
            logger.info(f"Cleaning up existing temp directory: {temp}")
            try:
                shutil.rmtree(temp, onerror=core.remove_readonly)
            except Exception as cleanup_err:
                logger.warning(f"Failed to cleanup temp directory: {cleanup_err}")
        
        logger.info(f"Extracting asar to: {temp}")
        try:
            core.run_asar("extract", asar, temp)
            logger.info("ASAR extraction completed")
        except Exception as extract_err:
            logger.error(f"Failed to extract ASAR: {extract_err}")
            return 1
        
        # 应用补丁
        from utils.paths import get_resource_path
        patch_dir = get_resource_path("Patch")
        if os.path.exists(patch_dir):
            logger.info(f"Applying patch from: {patch_dir}")
            try:
                shutil.copytree(patch_dir, temp, dirs_exist_ok=True)
                logger.info("Patch applied successfully")
            except Exception as patch_err:
                logger.error(f"Failed to apply patch: {patch_err}")
                return 1
        else:
            logger.error("Patch directory not found - cannot continue without patch files")
            return 1
        
        # 打包
        logger.info("Packing asar with patch...")
        try:
            core.run_asar("pack", temp, asar, unpack_pattern="*.{node,dll,exe}")
            logger.info("ASAR packing completed - patch applied successfully")
        except Exception as pack_err:
            logger.error(f"Failed to pack ASAR: {pack_err}")
            return 1
        
        # 保存补丁信息
        logger.info("Saving patch information...")
        try:
            save_patch_info(base, asar, bak)
            save_patch_meta(base, temp)
            logger.info("Patch information saved")
        except Exception as save_err:
            logger.error(f"Failed to save patch information: {save_err}")
        
        # 清理临时目录
        logger.info(f"Cleaning up temp directory: {temp}")
        if os.path.exists(temp):
            try:
                shutil.rmtree(temp, onerror=core.remove_readonly)
                logger.info("Temp directory cleaned up")
            except Exception as cleanup_err:
                logger.warning(f"Failed to cleanup temp directory: {cleanup_err}")
        
        logger.info("Patch completed successfully")
        return 0
    
    # 处理Fuse移除
    if args.fuse:
        exe_path = os.path.abspath(args.fuse)
        if not os.path.exists(exe_path):
            logger.error(f"Executable not found: {exe_path}")
            return 1
        
        logger.info(f"Removing Fuse from: {exe_path}")
        result = core.remove_fuse(exe_path)
        if result:
            logger.info("Fuse removed successfully")
            return 0
        else:
            logger.warning("Fuse sentinel not found or already disabled")
            return 1
    
    logger.info("Batch mode completed")
    return 0
