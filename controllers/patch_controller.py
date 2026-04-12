# -*- coding: utf-8 -*-
"""
补丁安装控制器模块

封装补丁安装相关的业务逻辑，解耦GUI代码。
"""

import os
import shutil
import logging
from typing import Optional, Callable, Tuple

from core.config import get_config
from core.steam import handle_steam_update
from core.patch_info import save_patch_info, save_patch_meta
from utils.cleanup import force_cleanup_dir
from utils.file_ops import safe_extract_zip
from utils.language import T
from utils.paths import get_resource_path, safe_path_within
from utils.constants import BATCH_CANCEL_OR_ERROR_MSG

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
        cfg = get_config()
        res = os.path.join(base, cfg.resource_dir)
        asar = os.path.join(res, cfg.target_asar_name)

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
        _check_cancelled = kwargs.get("_check_cancelled")
        base = os.path.abspath(".")
        cfg = get_config()
        res = os.path.join(base, cfg.resource_dir)
        asar = os.path.join(res, cfg.target_asar_name)
        bak = asar + ".bak"
        temp = None

        ok, prereq_err = self.check_prerequisites()
        if not ok:
            return False, None, prereq_err

        # 构建回调函数以解耦GUI
        on_error = getattr(gui_app, "thread_safe_showerror", None) if gui_app else None
        on_ask_yes_no = (
            getattr(gui_app, "thread_safe_askyesno", None) if gui_app else None
        )
        on_info = getattr(gui_app, "thread_safe_showinfo", None) if gui_app else None

        # Steam 更新检测
        should_continue, cancel_or_error = handle_steam_update(
            self.core,
            base,
            bak,
            asar,
            log_callback=self._log,
            on_error=on_error,
            on_ask_yes_no=on_ask_yes_no,
            on_info=on_info,
        )

        if cancel_or_error or not should_continue:
            return False, temp, BATCH_CANCEL_OR_ERROR_MSG

        # 创建备份
        if not os.path.exists(bak):
            self._log("Creating backup...")
            try:
                shutil.copy2(asar, bak)
                self._log("Backup created successfully.")
            except Exception as e:
                return False, None, f"Failed to create backup: {e}"

        temp_raw = os.path.join(base, cfg.temp_patch_dir)
        temp = safe_path_within(temp_raw, base)
        if not temp:
            return False, None, f"Security error: Invalid temporary patch directory path '{temp_raw}'"
        if os.path.exists(temp):
            if not force_cleanup_dir(temp):
                return (
                    False,
                    None,
                    f"Failed to clean up existing temporary directory: {temp}",
                )

        # 解包 ASAR
        self._log("Extracting ASAR...")
        self.core.run_asar("extract", asar, temp, callback=self._log)

        # 应用补丁
        self._log("Applying patch...")
        patch_zip = get_resource_path("Patch.zip")
        patch_dir = get_resource_path("Patch")

        if os.path.exists(patch_zip):
            self._log("Extracting Patch.zip...")
            try:
                safe_extract_zip(patch_zip, temp, check_cancelled=_check_cancelled)
                self._log("Patch.zip extracted successfully.")
            except ValueError as e:
                return False, temp, f"Security violation in patch ZIP: {e}"
            except Exception as e:
                return False, temp, f"Failed to extract Patch.zip: {e}"
        elif os.path.exists(patch_dir):
            self._log("Copying Patch directory...")

            def copy_with_cancel(src, dst):
                if _check_cancelled:
                    _check_cancelled()
                shutil.copy2(src, dst)

            shutil.copytree(
                patch_dir, temp, dirs_exist_ok=True, copy_function=copy_with_cancel
            )
            self._log("Patch files copied.")
        else:
            return False, temp, "Patch data not found"

        # 打包 ASAR
        self._log("Packing ASAR...")
        self.core.run_asar(
            "pack", temp, asar, callback=self._log, unpack_pattern="*.{node,dll,exe,so,dylib,bin}"
        )

        self._log("Saving patch information...")
        try:
            save_patch_info(base, asar, bak)
            save_patch_meta(base, temp)
        except Exception as e:
            logger.warning(
                f"Failed to save patch info/meta (non-fatal, patch still applied): {e}"
            )
            self._log(f"Warning: could not save patch info: {e}")

        # 清理临时备份文件
        self._cleanup_temp_files(base)

        self._log("Patch applied successfully.")
        self._log(T("patch_done", "✅ 安装完成！"))

        return True, temp, ""

    def _cleanup_temp_files(self, base_dir: str) -> None:
        """清理临时备份文件 (例如残留的 .patch_info.old 等)"""
        patch_info_file = get_config().patch_info_file
        temp_info = os.path.join(base_dir, patch_info_file + ".old")

        if os.path.exists(temp_info):
            try:
                os.remove(temp_info)
                logger.debug(f"Removed old temp file: {temp_info}")
            except Exception as e:
                logger.warning(f"Failed to remove temp file {temp_info}: {e}")

    def handle_error(
        self, base_dir: str, asar_path: str, bak_path: str, error: Exception
    ) -> None:
        """处理补丁失败的还原逻辑"""
        self._log(f"Error: {error}")
        logger.error(f"Patch error: {error}")

        if not bak_path or not os.path.exists(bak_path):
            return

        try:
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
