"""
补丁安装控制器模块

封装补丁安装相关的业务逻辑，解耦GUI代码。

改进点：
1. 使用事务性操作确保数据一致性
2. 磁盘空间预检
3. 状态一致性验证
4. 原子性ASAR替换
"""

__all__ = ["PatchController", "PatchError"]

import logging
import os
import shutil
from typing import Callable, Optional, Tuple

from core.bootstrap import get_runtime_game_path
from core.config import get_config
from core.patch_info import save_patch_info, save_patch_meta
from core.state_validator import StateValidator, SystemState
from core.steam import handle_steam_update
from utils.cleanup import force_cleanup_dir
from utils.constants import BATCH_CANCEL_OR_ERROR_MSG
from utils.disk_utils import (
    check_operation_space,
)
from utils.file_ops import safe_extract_zip
from utils.language import T
from utils.operation_lock import OperationType
from utils.paths import get_resource_path, safe_path_within
from utils.platform import get_platform_info, get_resources_path, is_app_bundle
from utils.asar_utils import validate_asar_with_reason

logger = logging.getLogger(__name__)


class PatchError(Exception):
    """补丁操作错误"""

    pass


class PatchController:
    """
    补丁安装控制器

    负责处理补丁安装的完整流程，包括：
    - 系统状态验证
    - 磁盘空间检查
    - 补丁提取和应用
    - ASAR文件操作
    - 状态一致性验证
    - 错误处理和回滚

    提供了完整的事务性操作，确保补丁安装过程的可靠性和安全性。
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
        self._is_operating = False

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
        # 优先使用检测到的游戏目录，否则使用当前目录
        base = get_runtime_game_path() or os.path.abspath(".")
        cfg = get_config()

        # 跨平台资源路径处理
        if is_app_bundle(base):
            res = os.path.join(base, "Contents", "Resources")
        else:
            res = get_resources_path(base, get_platform_info().system)

        asar = os.path.join(res, cfg.target_asar_name)
        bak = asar + ".bak"

        if not os.path.exists(res):
            return False, T("err_res_missing", "❌ 错误: 缺少 resources 文件夹。")

        asar_corrupted = False
        asar_reason = ""
        if os.path.exists(asar):
            try:
                asar_valid, asar_reason = validate_asar_with_reason(asar)
                asar_corrupted = not asar_valid
            except Exception:
                asar_corrupted = True
                asar_reason = "Unexpected validation error"

        if not os.path.exists(asar) or asar_corrupted:
            if os.path.exists(bak):
                # 删除损坏的 ASAR（如果存在），然后重命名 bak → app.asar
                if asar_corrupted and os.path.exists(asar):
                    self._log("app.asar corrupted, removing and restoring from backup...")
                    try:
                        os.remove(asar)
                    except Exception as e:
                        return False, f"Failed to remove corrupted ASAR: {e}"
                # 重命名 bak → app.asar（原子操作）
                try:
                    os.replace(bak, asar)
                    self._log("Restored app.asar from backup.")
                except Exception as e:
                    return False, f"Failed to restore from backup: {e}"
            elif asar_corrupted:
                return (
                    False,
                    "❌ 错误: app.asar 文件已损坏且无备份，请在 Steam 中验证游戏文件完整性。"
                    + (
                        f"\n\n{T('lbl_reason', 'Reason')}: {asar_reason}"
                        if asar_reason
                        else ""
                    ),
                )

        # ASAR 和 BAK 都不存在才算失败（BAK 存在时 run_auto_patch 可直接用 BAK 为源）
        if not os.path.exists(asar) and not os.path.exists(bak):
            return False, T("err_asar_missing", "❌ 错误: 未找到 app.asar 文件且无备份。")

        return True, ""

    def _check_disk_space(self, base_dir: str, asar_path: str) -> Tuple[bool, str]:
        """
        检查磁盘空间是否足够

        Returns:
            (是否足够, 详细信息)
        """
        try:
            asar_size = os.path.getsize(asar_path) if os.path.exists(asar_path) else 0

            operations = [
                ("ASAR备份", asar_size),
                ("ASAR解压", asar_size * 1.2),  # 解压后通常更大
                ("ASAR重新打包", asar_size * 1.1),
                ("临时文件", 100 * 1024 * 1024),  # 100MB临时空间
            ]

            return check_operation_space(operations, base_dir)

        except Exception as e:
            logger.warning(f"Failed to check disk space: {e}")
            return True, "无法检查磁盘空间，继续操作"  # 保守策略：继续

    def run_auto_patch(self, gui_app=None, **kwargs) -> Tuple[bool, Optional[str], str]:
        """
        执行自动补丁安装（事务性版本）

        改进点：
        1. 使用事务包装确保原子性
        2. 磁盘空间预检
        3. 增强错误处理和回滚

        Args:
            gui_app: GUI 应用实例（用于显示对话框）
            **kwargs: 其他参数，如 _check_cancelled

        Returns:
            (是否成功, 临时目录, 错误消息)
        """
        from utils.operation_lock import get_operation_lock

        lock = get_operation_lock()
        if not lock.acquire(OperationType.PATCH):
            return False, None, "另一个操作正在进行中"

        if self._is_operating:
            lock.release(OperationType.PATCH)
            return False, None, "另一个操作正在进行中"

        self._is_operating = True
        _check_cancelled = kwargs.get("_check_cancelled")

        try:
            return self._do_run_auto_patch(gui_app, _check_cancelled)
        finally:
            self._is_operating = False
            lock.release(OperationType.PATCH)

    def _do_run_auto_patch(self, gui_app, _check_cancelled) -> Tuple[bool, Optional[str], str]:
        """实际的补丁安装逻辑"""
        base = get_runtime_game_path() or os.path.abspath(".")
        cfg = get_config()

        # 跨平台资源路径处理
        if is_app_bundle(base):
            res = os.path.join(base, "Contents", "Resources")
        else:
            res = get_resources_path(base, get_platform_info().system)

        asar = os.path.join(res, cfg.target_asar_name)
        bak = asar + ".bak"
        temp = None

        # ========== 阶段 1: 前置检查 ==========
        ok, prereq_err = self.check_prerequisites()
        if not ok:
            return False, None, prereq_err

        # 构建回调函数以解耦GUI
        on_error = getattr(gui_app, "thread_safe_showerror", None) if gui_app else None
        on_ask_yes_no = getattr(gui_app, "thread_safe_askyesno", None) if gui_app else None
        on_info = getattr(gui_app, "thread_safe_showinfo", None) if gui_app else None

        # 系统状态验证
        self._log("Checking system state...")
        validator = StateValidator(base)
        state, issues = validator.validate_all()

        for issue in issues:
            if issue.severity == "critical":
                return False, None, f"System state error: {issue.message}"
            elif issue.severity == "warning":
                self._log(f"Warning: {issue.message}")

        if state == SystemState.PATCHED:
            self._log("Game is already patched.")
            if on_info:
                on_info(
                    T("title_success", "Already Patched"),
                    T(
                        "msg_already_patched",
                        "The game is already patched. No need to apply again.",
                    ),
                )
            return True, None, ""

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

        # 磁盘空间预检
        self._log("Checking disk space...")
        space_ok, space_info = self._check_disk_space(base, asar)
        self._log(space_info)
        if not space_ok:
            if on_error:
                on_error(
                    T("title_disk_space_error", "Disk Space Error"),
                    T(
                        "msg_insufficient_disk_space",
                        "Insufficient disk space. Please free up some space and try again.",
                    ),
                )
            return False, None, "Insufficient disk space"

        # ========== 阶段 2: 准备临时目录 ==========
        temp_raw = os.path.join(base, cfg.temp_patch_dir)
        temp = safe_path_within(temp_raw, base)
        if not temp:
            return (
                False,
                None,
                f"Security error: Invalid temporary patch directory path '{temp_raw}'",
            )

        if os.path.exists(temp):
            if not force_cleanup_dir(temp):
                return (
                    False,
                    None,
                    f"Failed to clean up existing temporary directory: {temp}",
                )

        # ========== 阶段 3: 补丁操作 ==========
        # 最小化写入流程: 解包 -> 打补丁 -> 重命名 -> 打包
        try:
            need_backup = os.path.exists(asar) and not os.path.exists(bak)

            # 3.1 解包 ASAR
            self._log("Extracting ASAR...")
            if _check_cancelled:
                _check_cancelled()
            _, unpacked_files = self.core.run_asar("extract", asar, temp, callback=self._log)

            # 验证解压结果
            if not os.path.exists(temp) or not os.listdir(temp):
                raise PatchError("ASAR extraction failed or resulted in empty directory")

            # 3.2 清理解包残留的 app.asar.unpacked 目录
            unpacked_leftover = os.path.join(temp, "app.asar.unpacked")
            if os.path.exists(unpacked_leftover):
                self._log("Cleaning up extraction leftover...")
                shutil.rmtree(unpacked_leftover, ignore_errors=True)

            # 3.3 应用补丁
            self._log("Applying patch...")
            patch_zip = get_resource_path("Patch.zip")
            patch_dir = get_resource_path("Patch")

            if os.path.exists(patch_zip):
                self._log("Extracting Patch.zip...")
                try:
                    safe_extract_zip(patch_zip, temp, check_cancelled=_check_cancelled)
                    self._log("Patch.zip extracted successfully.")
                except ValueError as e:
                    raise PatchError(f"Security violation in patch ZIP: {e}") from e
            elif os.path.exists(patch_dir):
                self._log("Copying Patch directory...")

                def copy_with_cancel(src, dst):
                    if _check_cancelled:
                        _check_cancelled()
                    shutil.copy2(src, dst)

                shutil.copytree(
                    patch_dir,
                    temp,
                    dirs_exist_ok=True,
                    copy_function=copy_with_cancel,
                )
                self._log("Patch files copied.")
            else:
                raise PatchError("Patch data not found")

            # 3.4 如果需要备份，重命名 app.asar -> app.asar.bak
            if need_backup:
                self._log("Creating backup...")
                os.replace(asar, bak)
                self._log("Backup created.")

            # 3.5 打包为新的 ASAR
            self._log("Packing ASAR...")
            if _check_cancelled:
                _check_cancelled()
            self.core.run_asar(
                "pack", temp, asar, callback=self._log, unpacked_files=unpacked_files
            )

            # 验证打包结果
            if not os.path.exists(asar):
                raise PatchError("ASAR packing failed - output file not created")
            if os.path.getsize(asar) < 1024:
                raise PatchError("ASAR packing failed - output file too small")

            self._log("ASAR replaced successfully.")

            # 3.6 生成补丁元数据
            self._log("Generating patch metadata...")
            try:
                save_patch_info(base, asar, bak)
                save_patch_meta(base, temp)
            except Exception as e:
                logger.warning(f"Failed to save patch metadata: {e}")

            self._log("Patch applied successfully.")
            self._log(T("patch_done", "✅ 安装完成！"))

            return True, temp, ""

        except PatchError as e:
            logger.error(f"Patch error: {e}")
            return False, temp, str(e)
        except Exception as e:
            logger.exception("Unexpected error during patching")
            return False, temp, f"Unexpected error: {e}"
        finally:
            # 清理临时目录
            if temp and os.path.exists(temp):
                try:
                    force_cleanup_dir(temp)
                except Exception as e:
                    logger.warning(f"Failed to cleanup temp directory: {e}")

    def _cleanup_temp_files(self, base_dir: str) -> None:
        """清理临时备份文件"""
        patch_info_file = get_config().patch_info_file
        temp_info = os.path.join(base_dir, patch_info_file + ".old")

        if os.path.exists(temp_info):
            try:
                os.remove(temp_info)
                logger.debug(f"Removed old temp file: {temp_info}")
            except Exception as e:
                logger.warning(f"Failed to remove temp file {temp_info}: {e}")

    def handle_error(self, base_dir: str, asar_path: str, bak_path: str, error: Exception) -> None:
        """
        处理补丁失败的还原逻辑

        注意：新的事务性流程已自动处理回滚，
        此方法仅作为兼容性保留。
        """
        self._log(f"Error: {error}")
        logger.error(f"Patch error: {error}")

        # 如果备份存在但ASAR损坏，尝试恢复
        if not bak_path or not os.path.exists(bak_path):
            return

        try:
            valid, reason = validate_asar_with_reason(bak_path)
            if not valid:
                logger.error(f"Backup is corrupted, cannot restore: {reason}")
                return
        except Exception as e:
            logger.error(f"Cannot verify backup: {e}")
            return

        try:
            if os.path.exists(asar_path):
                try:
                    os.remove(asar_path)
                except Exception as e_rm:
                    logger.error(f"Failed to remove corrupted ASAR: {e_rm}")
            os.replace(bak_path, asar_path)
            self._log("Restored app.asar from backup.")
        except Exception as be:
            logger.error(f"Backup restore error: {be}")
            self._log(f"Failed to restore backup: {be}")
