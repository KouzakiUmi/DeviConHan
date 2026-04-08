# -*- coding: utf-8 -*-
"""
补丁安装控制器模块

封装补丁安装相关的业务逻辑，解耦GUI代码。
"""

import os
import shutil
import zipfile
import logging
from typing import Optional, Callable, Tuple

from core.config import get_config
from core.patcher import handle_steam_update, save_patch_info, save_patch_meta
from utils.cleanup import force_cleanup_dir
from utils.language import T
from utils.paths import get_resource_path

logger = logging.getLogger(__name__)


class PatchController:
    """
    补丁安装控制器
    
    负责处理补丁安装的完整流程，包括Steam更新检测、ASAR操作等。
    将GUI代码与业务逻辑分离，提高代码可维护性。
    """
    
    def __init__(self, core_logic, log_callback: Optional[Callable] = None):
        """
        初始化补丁控制器
        
        Args:
            core_logic: CoreLogic 实例
            log_callback: 日志回调函数
        """
        self.core = core_logic
        self.log_callback = log_callback
        self._current_temp_dir = None
    
    def set_log_callback(self, callback: Callable) -> None:
        """设置日志回调"""
        self.log_callback = callback
    
    def _log(self, message: str) -> None:
        """记录日志"""
        if self.log_callback:
            self.log_callback(message)
        logger.info(message)
    
    def check_prerequisites(self) -> Tuple[bool, str]:
        """
        检查补丁安装的前置条件
        
        Returns:
            (是否满足, 错误消息)
        """
        base = os.path.abspath(".")
        res = os.path.join(base, get_config().resource_dir)
        asar = os.path.join(res, "app.asar")
        
        if not os.path.exists(res):
            return False, T("err_res_missing", "❌ 错误: 缺少 resources 文件夹。")
        
        if not os.path.exists(asar):
            bak = asar + ".bak"
            if os.path.exists(bak):
                self._log("app.asar missing, restoring from backup...")
                shutil.copy2(bak, asar)
                self._log("Restored app.asar from backup.")
        
        if not os.path.exists(asar):
            return False, T("err_asar_missing", "❌ 错误: 未找到 app.asar 文件。")
        
        return True, ""
    
    def run_auto_patch(self, gui_app=None, **kwargs) -> Tuple[bool, Optional[str], str]:
        """
        执行自动补丁安装
        
        Args:
            gui_app: GUI 应用实例（用于显示对话框）
            **kwargs: 其他参数，如 _check_cancelled
            
        Returns:
            (是否成功, 临时目录, 错误消息)
        """
        _check_cancelled = kwargs.get('_check_cancelled')
        base = os.path.abspath(".")
        res = os.path.join(base, get_config().resource_dir)
        asar = os.path.join(res, "app.asar")
        bak = asar + ".bak"
        temp = None
        
        # Steam 更新检测
        should_continue, cancel_or_error = handle_steam_update(
            self.core, base, bak, asar,
            log_callback=self._log,
            gui_app=gui_app
        )
        
        if cancel_or_error or not should_continue:
            return False, temp, "Cancelled or error"
        
        # 创建备份
        if not os.path.exists(bak):
            self._log("Creating backup...")
            try:
                shutil.copy2(asar, bak)
                self._log("Backup created successfully.")
            except Exception as e:
                return False, None, f"Failed to create backup: {e}"
        
        # 创建临时目录
        temp = os.path.join(base, "temp_patch")
        if os.path.exists(temp):
            force_cleanup_dir(temp)
        
        # 解包 ASAR
        self._log("Extracting ASAR...")
        self.core.run_asar("extract", asar, temp, callback=self._log)
        
        # 应用补丁
        self._log("Applying patch...")
        patch_zip = get_resource_path("Patch.zip")
        patch_dir = get_resource_path("Patch")
        
        if os.path.exists(patch_zip):
            self._log(f"Extracting Patch.zip...")
            with zipfile.ZipFile(patch_zip, 'r') as zf:
                for member in zf.infolist():
                    if _check_cancelled:
                        _check_cancelled()
                    zf.extract(member, temp)
            self._log("Patch.zip extracted successfully.")
        elif os.path.exists(patch_dir):
            self._log(f"Copying Patch directory...")
            
            def copy_with_cancel(src, dst):
                if _check_cancelled:
                    _check_cancelled()
                shutil.copy2(src, dst)
                
            shutil.copytree(patch_dir, temp, dirs_exist_ok=True, copy_function=copy_with_cancel)
            self._log("Patch files copied.")
        else:
            return False, temp, "Patch data not found"
        
        # 打包 ASAR
        self._log("Packing ASAR...")
        self.core.run_asar("pack", temp, asar, callback=self._log, unpack_pattern="*.{node,dll,exe}")
        
        # 保存补丁信息
        self._log("Saving patch information...")
        save_patch_info(base, asar, bak)
        save_patch_meta(base, temp)
        
        # 清理临时备份文件
        self._cleanup_temp_files(base, bak)
        
        self._log("Patch applied successfully.")
        self._log(T("patch_done", "✅ 安装完成！"))
        
        return True, temp, ""
    
    def _cleanup_temp_files(self, base_dir: str, bak_path: str) -> None:
        """清理临时备份文件"""
        temp_bak = bak_path + ".old"
        patch_info_file = get_config().patch_info_file
        temp_info = os.path.join(base_dir, patch_info_file + ".old")
        
        for tmp_file in [temp_bak, temp_info]:
            if os.path.exists(tmp_file):
                try:
                    os.remove(tmp_file)
                    logger.debug(f"Removed old temp file: {tmp_file}")
                except Exception as e:
                    logger.warning(f"Failed to remove temp backup file {tmp_file}: {e}")
    
    def handle_error(self, base_dir: str, asar_path: str, bak_path: str, error: Exception) -> None:
        """处理补丁失败的还原逻辑"""
        self._log(f"Error: {error}")
        logger.error(f"Patch error: {error}")
        
        if not bak_path or not os.path.exists(bak_path):
            return
        
        try:
            temp_bak = bak_path + ".old"
            patch_info_file = get_config().patch_info_file
            temp_info = os.path.join(base_dir, patch_info_file + ".old") if base_dir else None
            
            if os.path.exists(temp_bak):
                self._log("Restoring backup due to error...")
                if os.path.exists(bak_path):
                    try:
                        os.remove(bak_path)
                    except Exception as e_rm:
                        logger.error(f"Failed to remove corrupted backup: {e_rm}")
                shutil.move(temp_bak, bak_path)
            
            if os.path.exists(asar_path):
                try:
                    os.remove(asar_path)
                except Exception as e_rm:
                    logger.error(f"Failed to remove corrupted ASAR: {e_rm}")
            shutil.copy2(bak_path, asar_path)
            self._log("Restored app.asar from backup.")
        except Exception as be:
            logger.error(f"Backup restore error: {be}")
            self._log(f"Failed to restore backup: {be}")