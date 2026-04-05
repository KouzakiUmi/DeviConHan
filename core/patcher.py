# -*- coding: utf-8 -*-
"""
恶魔链接补丁工具 - 核心逻辑模块

提供ASAR文件操作、补丁应用、Steam更新处理等核心功能。
包含性能监控集成，用于跟踪和优化操作性能。
"""

import os
import sys
import shutil
import mmap
import subprocess
import stat
import datetime
import logging
import hashlib
import enum
import tempfile
import json

from utils.paths import get_resource_path, normalize_path
from utils.language import T
from utils.performance import timing_context, get_performance_monitor
from utils.cleanup import force_cleanup_dir
from core.config import get_config

logger = logging.getLogger(__name__)

# ================== 配置延迟加载 ==================
# 注意: 配置和语言初始化现在由 main.py 统一处理
# 避免在模块导入时执行可能依赖日志系统的初始化

# ================== 异常类定义 ==================
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
    """Steam 的更新检测状态，替代字符串匹配控制流"""
    FIRST_TIME = "first_time"                    # 首次打补丁，无 .bak 文件
    OLD_VERSION = "old_version"                  # 旧版本升级，缺少 .patch_info
    STEAM_UPDATED = "steam_updated"              # 确认被 Steam 更新
    TOOL_ISSUE = "tool_issue"                    # 工具问题导致误判（需用户确认）
    ALL_PASSED = "all_passed"                    # 检查通过，可安全恢复备份
    NO_BACKUP = "no_backup"                      # 无 .bak 文件


# ================= 核心逻辑类 (Worker) =================
class CoreLogic:
    # 统一的 remove_readonly 方法
    @staticmethod
    def remove_readonly_handler(func, path, excinfo):
        """删除只读属性的回调函数（静态方法，可在类外复用）"""
        try:
            os.chmod(path, stat.S_IWRITE)
            func(path)
        except Exception as e:
            logger.debug(f"Failed to remove readonly: {e}")

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
        # TODO: 从配置文件读取或自动检测模式
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
        """
        删除只读属性的回调函数
        
        此方法委托给静态方法，用于 shutil.rmtree 的 onerror 回调。
        当删除只读文件时，Python 会调用此函数先移除只读属性再重试删除。
        
        Args:
            func: 导致异常的操作函数（通常是 os.remove 或 os.rmdir）
            path: 文件/目录路径
            excinfo: 异常信息元组
            
        Returns:
            处理结果（委托给静态方法）
        """
        return self.remove_readonly_handler(func, path, excinfo)

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
        
        # 使用性能监控器记录ASAR操作
        monitor = get_performance_monitor()
        monitor.start(f"asar_{action}")
        
        try:
            # 固定使用内置工具
            cmd = [self.node_path, self.script_path, action, src, dest]
            if action == "pack":
                cmd.extend(["--unpack", unpack_pattern])
            
            logger.debug(f"Using bundled Node.js: {self.node_path}")
            logger.debug(f"Command: {' '.join(cmd)}")
            
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
                errors="backslashreplace",
                creationflags=creationflags,
                timeout=get_config().get_int("main", "ASAR_OPERATION_TIMEOUT", fallback=300)  # 超时时间从配置读取
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
            error_msg = "Operation timed out after 300 seconds"
            logger.error(error_msg)
            raise PatcherError(error_msg)
            
        except Exception as e:
            logger.exception(f"ASAR operation failed: {e}")
            if isinstance(e, (NodeNotFoundError, PatcherFileNotFoundError)):
                raise
            raise PatcherError(str(e))
        finally:
            # 记录ASAR操作耗时
            elapsed = monitor.stop(f"asar_{action}")
            logger.debug(f"ASAR {action} operation took {elapsed:.3f}s")

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
            
            # 获取Fuse配置
            fuse_sentinel = get_config().fuse_sentinel
            header_len = get_config().fuse_wire_header_length
            integrity_offset = get_config().fuse_asar_integrity_offset
            
            with open(exe_path, "r+b") as f:
                with mmap.mmap(f.fileno(), 0) as mm:
                    offset = mm.find(fuse_sentinel)
                    
                    if offset == -1:
                        logger.info("Fuse sentinel not found - already removed or never present")
                        return False
                    
                    # 计算目标偏移量
                    target = offset + header_len + integrity_offset
                    
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
                        if callback:
                            callback("Fuse already disabled.")
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


def has_embedded_patch():
    """
    检测是否包含内置汉化补丁
    
    Returns:
        bool: 如果 Patch.zip 或 Patch 目录存在返回 True
    """
    patch_zip = os.path.join(get_resource_path("."), "Patch.zip")
    patch_dir = os.path.join(get_resource_path("."), "Patch")
    return os.path.exists(patch_zip) or os.path.exists(patch_dir)

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

def get_file_hash_in_asar(core, asar_path, file_path):
    """
    计算 ASAR 包内特定文件的 SHA256 哈希值
    纯 Python 内存实现，不依赖外部命令行调用，速度快且不产生临时文件。
    
    Args:
        core: CoreLogic 实例 (保留以保持接口兼容，实际未被使用)
        asar_path: ASAR 文件路径
        file_path: ASAR 内的相对路径
        
    Returns:
        str: 文件的 SHA256 哈希值，失败返回 None
    """
    import struct
    import json
    
    if not os.path.exists(asar_path):
        return None
        
    try:
        with open(asar_path, 'rb') as f:
            # 4 bytes for magic number
            magic = f.read(4)
            if magic != b'\x04\x00\x00\x00':
                return None
                
            header_size_bytes = f.read(4)
            if len(header_size_bytes) != 4:
                return None
            header_size = struct.unpack('<I', header_size_bytes)[0]
            
            # Read the rest of the header
            header_data = f.read(header_size)
            if len(header_data) != header_size:
                return None
                
            # The next two uint32s are sizes
            json_size = struct.unpack('<I', header_data[4:8])[0]
            
            # The JSON string
            json_str = header_data[8:8+json_size].decode('utf-8')
            header_dict = json.loads(json_str)
            
            # base offset is where the file data begins
            base_offset = 8 + header_size
            
            # Normalize path
            path_parts = [p for p in file_path.replace('\\', '/').split('/') if p]
            
            # Find node
            node = header_dict
            for part in path_parts:
                if 'files' in node and part in node['files']:
                    node = node['files'][part]
                else:
                    return None # File not found
                    
            # Check if it's a file
            if 'offset' not in node or 'size' not in node:
                return None
                
            # We can use the pre-calculated hash if it exists
            if 'integrity' in node and node['integrity'].get('algorithm') == 'SHA256':
                return node['integrity'].get('hash')
                
            # Otherwise, read the file and compute hash
            offset = int(node['offset'])
            size = node['size']
            
            f.seek(base_offset + offset)
            # Read in chunks to avoid memory issues with large files
            sha256_hash = hashlib.sha256()
            bytes_read = 0
            while bytes_read < size:
                chunk_size = min(4096, size - bytes_read)
                chunk = f.read(chunk_size)
                if not chunk:
                    break
                sha256_hash.update(chunk)
                bytes_read += len(chunk)
                
            return sha256_hash.hexdigest()
            
    except Exception as e:
        logger.debug(f"Error parsing ASAR file {asar_path} for {file_path}: {e}")
        return None

def save_patch_info(base_dir, asar_path, bak_path):
    """
    保存补丁信息到 .patch_info 文件
    
    Args:
        base_dir: 基础目录
        asar_path: asar文件路径
        bak_path: 备份文件路径
    """
    import json
    patch_info_file = get_config().patch_info_file
    info_file = os.path.join(base_dir, patch_info_file)
    info = {
        "asar_path": asar_path,
        "bak_path": bak_path,
        "timestamp": datetime.datetime.now().isoformat()
    }
    
    with open(info_file, "w", encoding="utf-8") as f:
        json.dump(info, f, indent=2, ensure_ascii=False)
    
    logger.info(f"Saved patch info to: {info_file}")

def save_patch_meta(base_dir, temp_dir):
    """
    保存补丁元数据到 .patch_meta 文件
    
    Args:
        base_dir: 基础目录
        temp_dir: 临时目录
    """
    import json
    patch_meta_file = get_config().patch_meta_file
    meta_file = os.path.join(base_dir, patch_meta_file)
    
    # 收集补丁文件的信息
    meta_info = {
        "timestamp": datetime.datetime.now().isoformat(),
        "patch_files": {}
    }
    
    # 记录关键文件的哈希值
    check_files = get_config().check_files_for_update
    for file_path in check_files:
        full_path = os.path.join(temp_dir, file_path)
        if os.path.exists(full_path):
            meta_info["patch_files"][file_path] = compute_file_hash(full_path)
    
    with open(meta_file, "w", encoding="utf-8") as f:
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
    
    # 获取配置常量
    patch_info_file = get_config().patch_info_file
    time_diff_threshold_days = get_config().time_diff_threshold_days
    
    # 检查 ASAR 文件状态
    asar_exists = asar_path and os.path.exists(asar_path)
    bak_exists = os.path.exists(bak_path)
    
    # 情况 4：ASAR 和备份都不存在 → 游戏文件损坏或安装不完整
    if not asar_exists and not bak_exists:
        logger.error("Neither ASAR nor backup file exists - game files may be corrupted or incomplete")
        if gui_app:
            if hasattr(gui_app, "thread_safe_showerror"):
                gui_app.thread_safe_showerror(T('title_game_files_missing'), T('msg_game_files_missing'))
            else:
                from tkinter import messagebox
                messagebox.showerror(T('title_game_files_missing'), T('msg_game_files_missing'))
        return (False, True)
    
    # 情况 3：ASAR 不存在，备份存在 → Steam 更新后恢复备份
    if not asar_exists and bak_exists:
        logger.warning("ASAR file missing but backup exists - possible Steam update detected")
        
        # 验证备份文件的完整性
        if not _validate_backup_integrity(bak_path, core):
            logger.error("Backup file is corrupted")
            if gui_app:
                if hasattr(gui_app, "thread_safe_showerror"):
                    gui_app.thread_safe_showerror(T('title_backup_corrupted'), T('msg_backup_corrupted'))
                else:
                    from tkinter import messagebox
                    messagebox.showerror(T('title_backup_corrupted'), T('msg_backup_corrupted'))
            return (False, True)
        
        # 备份有效，询问用户是否恢复
        if gui_app:
            if hasattr(gui_app, "thread_safe_askyesno"):
                result = gui_app.thread_safe_askyesno(T('title_asar_missing'), T('msg_asar_missing_valid_backup'))
            else:
                from tkinter import messagebox
                result = messagebox.askyesno(T('title_asar_missing'), T('msg_asar_missing_valid_backup'))
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
                if hasattr(gui_app, "thread_safe_showerror"):
                    gui_app.thread_safe_showerror(T('title_asar_corrupted'), T('msg_asar_corrupted'))
                else:
                    from tkinter import messagebox
                    messagebox.showerror(T('title_asar_corrupted'), T('msg_asar_corrupted'))
            return (False, True)
        
        # GUI 模式下提示用户首次打补丁的风险
        if gui_app:
            title = T('title_first_time_patch')
            msg = T('msg_first_time_patch_warn')
            if title == 'title_first_time_patch': 
                title = "First Time Patch"
            if msg == 'msg_first_time_patch_warn': 
                msg = "No original backup detected. Please verify game files in Steam first if you have used other patches before. Continue?"
                
            if hasattr(gui_app, "thread_safe_askyesno"):
                result = gui_app.thread_safe_askyesno(title, msg)
            else:
                from tkinter import messagebox
                result = messagebox.askyesno(title, msg)
            if not result:
                return (False, True)
        
        # ASAR 文件有效，可以继续打补丁
        return (True, False)
    
    # 情况 2：ASAR 存在，备份存在 → 检查补丁信息，判断是否需要重新打补丁
    if asar_exists and bak_exists:
        logger.info("Both ASAR and backup exist - checking patch status via file hashes")
        
        # 验证备份文件的完整性
        if not _validate_backup_integrity(bak_path, core):
            logger.warning("Backup file is corrupted, but ASAR is valid")
            if gui_app:
                if hasattr(gui_app, "thread_safe_askyesno"):
                    result = gui_app.thread_safe_askyesno(T('title_backup_corrupted_asar_valid'), T('msg_backup_corrupted_asar_valid'))
                else:
                    from tkinter import messagebox
                    result = messagebox.askyesno(T('title_backup_corrupted_asar_valid'), T('msg_backup_corrupted_asar_valid'))
                if not result:
                    return (False, True)
            return (True, False)
        
        # 检查补丁元数据文件
        patch_meta_file = get_config().patch_meta_file
        meta_file = os.path.join(base_dir, patch_meta_file)
        
        # 兼容旧版本：如果没有 meta，但有 info，视为旧版本
        if not os.path.exists(meta_file):
            info_file = os.path.join(base_dir, patch_info_file)
            if not os.path.exists(info_file):
                logger.warning("Patch info and meta files missing - may be old version patch or used other tools")
                if gui_app:
                    if hasattr(gui_app, "thread_safe_askyesno"):
                        result = gui_app.thread_safe_askyesno(T('title_no_patch_info'), T('msg_no_patch_info'))
                    else:
                        from tkinter import messagebox
                        result = messagebox.askyesno(T('title_no_patch_info'), T('msg_no_patch_info'))
                    return (result, not result)
                return (True, False)
            else:
                logger.warning("Found old patch info without meta file - recommend repatching")
                return (True, False)
                
        # 存在 meta 文件，读取并验证哈希
        try:
            import json
            with open(meta_file, 'r', encoding='utf-8') as f:
                meta_info = json.load(f)
            
            patch_files = meta_info.get("patch_files", {})
            if not patch_files:
                logger.warning("No patch files listed in meta, cannot verify ASAR.")
                return (True, False)
            
            # Step 1: 检查 asar 关键文件 vs 补丁
            check_files = get_config().check_files_for_update
            all_match_patch = True
            mismatched_files = []
            
            for file_path in check_files:
                expected_hash = patch_files.get(file_path)
                if not expected_hash:
                    # 这个文件可能不在补丁中，跳过
                    continue
                
                current_hash = get_file_hash_in_asar(core, asar_path, file_path)
                if current_hash != expected_hash:
                    all_match_patch = False
                    mismatched_files.append(file_path)
                    logger.info(f"File {file_path} in ASAR hash mismatch. Expected: {expected_hash}, Got: {current_hash}")
                    break
                    
            if all_match_patch:
                logger.info("All crucial files in ASAR match the patch meta. Patch is active.")
                # We return False for should_continue, False for cancel_or_error
                # so the patching process skips without error
                if gui_app:
                    if hasattr(gui_app, "thread_safe_showinfo"):
                        gui_app.thread_safe_showinfo(
                            T('title_success') if T('title_success') else "Already Patched",
                            T('msg_already_patched') if T('msg_already_patched') else "The game is already patched. No need to apply again."
                        )
                    else:
                        from tkinter import messagebox
                        messagebox.showinfo(
                            T('title_success') if T('title_success') else "Already Patched",
                            T('msg_already_patched') if T('msg_already_patched') else "The game is already patched. No need to apply again."
                        )
                return (False, False)
            else:
                logger.info("ASAR crucial files do not match patch meta. Checking if it's a Steam update...")
                
                # Step 2: 检查 bak 关键文件 vs asar
                all_match_bak = True
                for file_path in mismatched_files:
                    bak_hash = get_file_hash_in_asar(core, bak_path, file_path)
                    asar_hash = get_file_hash_in_asar(core, asar_path, file_path)
                    
                    if bak_hash != asar_hash:
                        all_match_bak = False
                        logger.info(f"File {file_path} differs between ASAR and backup. Bak: {bak_hash}, ASAR: {asar_hash}")
                        break
                        
                if all_match_bak:
                    # bak 关键文件与 asar 一致
                    # 这意味着当前 asar 是纯净的原始文件，与我们早先备份的原始文件（或下载的原始文件）一致
                    logger.info("ASAR crucial files match backup files. Steam update detected.")
                    # 既然要重建备份，我们删除现有的备份
                    try:
                        if os.path.exists(bak_path):
                            os.remove(bak_path)
                    except Exception as e:
                        logger.error(f"Failed to remove old backup for rebuilding: {e}")
                    return (True, False) # 需要重新打补丁（main_window 中会把当前的 asar 复制为 bak）
                else:
                    # asar 既不匹配补丁，也不匹配原版 bak，说明使用了其他汉化或者文件被篡改，或者 Steam 更新修改了关键文件
                    logger.warning("ASAR files do not match patch OR backup. Possible third-party patch or major Steam update detected.")
                    if gui_app:
                        title = T('title_third_party_patch_detected') if T('title_third_party_patch_detected') else "Modified ASAR Detected"
                        msg = T('msg_third_party_patch_detected') if T('msg_third_party_patch_detected') else "ASAR file has been modified by an unknown source or major Steam update.\nDo you want to rebuild backup and apply this patch?"
                        if hasattr(gui_app, "thread_safe_askyesno"):
                            result = gui_app.thread_safe_askyesno(title, msg)
                        else:
                            from tkinter import messagebox
                            result = messagebox.askyesno(title, msg)
                        if result:
                            try:
                                if os.path.exists(bak_path):
                                    os.remove(bak_path)
                            except Exception as e:
                                logger.error(f"Failed to remove old backup: {e}")
                        return (result, not result)
                    else:
                        try:
                            if os.path.exists(bak_path):
                                os.remove(bak_path)
                        except:
                            pass
                        return (True, False)
                    
        except Exception as e:
            logger.warning(f"Failed to check patch meta: {e}")
            # 回退机制
            return (True, False)
    
    # 默认情况（理论上不会到达这里）
    logger.warning("Unexpected file state, proceeding with caution")
    return (True, False)

def _validate_archive_integrity(archive_path, core, archive_type="archive"):
    """
    验证归档文件（ASAR 或备份）的完整性
    
    Args:
        archive_path: 归档文件路径
        core: CoreLogic 实例
        archive_type: 归档类型（"asar" 或 "backup"），用于日志记录
        
    Returns:
        bool: 文件是否有效
    """
    import json
    
    # 使用性能监控器记录验证操作
    monitor = get_performance_monitor()
    monitor.start(f"validate_{archive_type}")
    
    try:
        # 检查文件大小
        file_size = os.path.getsize(archive_path)
        if file_size < 1024:  # 小于 1KB 可能是损坏的
            logger.warning(f"{archive_type.capitalize()} file too small: {file_size} bytes")
            return False
        
        # 尝试读取归档文件的基本信息
        try:
            cmd = [core.node_path, core.script_path, 'stat', archive_path, 'package.json']
            proc_result = subprocess.run(cmd, capture_output=True, text=True, timeout=10, check=True, encoding='utf-8')
            data = json.loads(proc_result.stdout.strip())
            if not data.get("success"):
                error_type = data.get("error_type", "unknown")
                if error_type == "file_not_found":
                    logger.warning(f"File not found in {archive_type}: package.json")
                    return False
                elif error_type == "file_corrupted":
                    logger.warning(f"{archive_type.capitalize()} file is corrupted: {data.get('error')}")
                    return False
                else:
                    logger.warning(f"{archive_type.capitalize()} stat failed: {data.get('error')}")
                    return False
        except subprocess.CalledProcessError as e:
            # 解析 stderr 中的 JSON 错误信息
            try:
                error_data = json.loads(e.stderr.strip())
                error_type = error_data.get("error_type", "unknown")
                if error_type == "file_not_found":
                    logger.warning(f"File not found in {archive_type}: package.json")
                    return False
                elif error_type == "file_corrupted":
                    logger.warning(f"{archive_type.capitalize()} file is corrupted: {error_data.get('error')}")
                    return False
                else:
                    logger.warning(f"{archive_type.capitalize()} stat failed: {error_data.get('error')}")
                    return False
            except json.JSONDecodeError:
                logger.warning(f"Failed to parse error response: {e.stderr}")
                return False
        except Exception as e:
            logger.warning(f"Failed to validate {archive_type} integrity: {e}")
            return False
        
        return True
    except Exception as e:
        logger.error(f"Error validating {archive_type} integrity: {e}")
        return False
    finally:
        # 记录验证操作耗时
        elapsed = monitor.stop(f"validate_{archive_type}")
        logger.debug(f"Validate {archive_type} integrity took {elapsed:.3f}s")


def _validate_asar_integrity(asar_path, core):
    """
    验证 ASAR 文件的完整性
    
    Args:
        asar_path: ASAR 文件路径
        core: CoreLogic 实例
        
    Returns:
        bool: 文件是否有效
    """
    return _validate_archive_integrity(asar_path, core, "asar")


def _validate_backup_integrity(bak_path, core):
    """
    验证备份文件的完整性
    
    Args:
        bak_path: 备份文件路径
        core: CoreLogic 实例
        
    Returns:
        bool: 文件是否有效
    """
    return _validate_archive_integrity(bak_path, core, "backup")

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
    res = os.path.join(base, get_config().resource_dir)
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
    
    if cancel_or_error:
        return 1
    if not should_continue:
        logger.info("Patch operation skipped (already patched or not needed)")
        return 0
    
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
                shutil.rmtree(temp, onerror=core.remove_readonly_handler)
            except Exception as cleanup_err:
                logger.warning(f"Failed to cleanup temp directory: {cleanup_err}")
        
        logger.info(f"Extracting asar to: {temp}")
        try:
            # 使用性能监控器记录ASAR解包操作
            monitor = get_performance_monitor()
            monitor.start("batch_extract_asar")
            try:
                core.run_asar("extract", asar, temp)
                logger.info("ASAR extraction completed")
            finally:
                elapsed = monitor.stop("batch_extract_asar")
                logger.info(f"Batch ASAR extraction took {elapsed:.3f}s")
        except Exception as extract_err:
            logger.error(f"Failed to extract ASAR: {extract_err}")
            return 1
        
        # 应用补丁
        patch_zip = get_resource_path("Patch.zip")
        patch_dir = get_resource_path("Patch")
        
        if os.path.exists(patch_zip):
            logger.info(f"Applying patch from: {patch_zip}")
            try:
                import zipfile
                with zipfile.ZipFile(patch_zip, 'r') as zf:
                    zf.extractall(temp)
                logger.info("Patch applied successfully")
            except Exception as patch_err:
                logger.error(f"Failed to extract Patch.zip: {patch_err}")
                return 1
        elif os.path.exists(patch_dir):
            logger.info(f"Applying patch from: {patch_dir}")
            try:
                shutil.copytree(patch_dir, temp, dirs_exist_ok=True)
                logger.info("Patch applied successfully")
            except Exception as patch_err:
                logger.error(f"Failed to apply patch: {patch_err}")
                return 1
        else:
            logger.error("Patch data not found - cannot continue without patch files")
            return 1
        
        # 打包
        logger.info("Packing asar with patch...")
        try:
            # 使用性能监控器记录ASAR打包操作
            monitor = get_performance_monitor()
            monitor.start("batch_pack_asar")
            try:
                core.run_asar("pack", temp, asar, unpack_pattern="*.{node,dll,exe}")
                logger.info("ASAR packing completed - patch applied successfully")
            finally:
                elapsed = monitor.stop("batch_pack_asar")
                logger.info(f"Batch ASAR packing took {elapsed:.3f}s")
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
        
        # 清理临时目录（使用更强力的清理策略）
        logger.info(f"Cleaning up temp directory: {temp}")
        if os.path.exists(temp):
            force_cleanup_dir(temp)
        
        logger.info("Patch completed successfully")
        return 0
    
    logger.info("Batch mode completed")
    return 0
