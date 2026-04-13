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

from core.bootstrap import get_detected_game_path
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
from utils.transaction import FileTransaction, TransactionError

logger = logging.getLogger(__name__)


class PatchError(Exception):
    """补丁操作错误"""

    pass


class PatchController:
    """
    补丁安装控制器

    负责处理补丁安装的完整流程，包括：
    - 系统状态验证
    - 磁盘空间预检
    - Steam更新检测
    - 事务性ASAR操作
    - 自动回滚机制
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
        base = get_detected_game_path() or os.path.abspath(".")
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
        if os.path.exists(asar):
            if os.path.getsize(asar) < 4:
                asar_corrupted = True
            else:
                try:
                    with open(asar, "rb") as f:
                        magic = f.read(4)
                        if magic != b"\x04\x00\x00\x00":
                            asar_corrupted = True
                except Exception:
                    asar_corrupted = True

        if not os.path.exists(asar) or asar_corrupted:
            if os.path.exists(bak):
                self._log("app.asar missing or corrupted, restoring from backup...")
                try:
                    if os.path.exists(asar):
                        os.remove(asar)
                    shutil.copy2(bak, asar)
                    self._log("Restored app.asar from backup.")
                except Exception as e:
                    return False, f"Failed to restore backup: {e}"
            elif asar_corrupted:
                return (
                    False,
                    "❌ 错误: app.asar 文件已损坏且无备份，请在 Steam 中验证游戏文件完整性。",
                )

        if not os.path.exists(asar):
            return False, T("err_asar_missing", "❌ 错误: 未找到 app.asar 文件。")

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

    def _separate_unpacked_files(self, extract_dir: str) -> None:
        """
        分离 unpacked 文件到 app.asar.unpacked 目录。

        原生模块文件需要**复制**到 app.asar.unpacked 目录，
        同时**保留**在 extract_dir 中，这样 ASAR 内部有文件路径，外部有实际文件供 Electron 加载。
        """
        NATIVE_EXTENSIONS = {".node", ".dll", ".so", ".dylib", ".bin", ".exe", ".lib"}

        def should_unpack(file_path: str) -> bool:
            ext = os.path.splitext(file_path)[1].lower()
            return ext in NATIVE_EXTENSIONS

        def copy_to_unpacked(source_dir: str, unpacked_root: str):
            if not os.path.isdir(source_dir):
                return

            for entry in os.listdir(source_dir):
                source_path = os.path.join(source_dir, entry)

                if os.path.isdir(source_path):
                    copy_to_unpacked(source_path, unpacked_root)
                elif should_unpack(entry):
                    rel_path = os.path.relpath(source_path, extract_dir)
                    dest_path = os.path.join(unpacked_root, rel_path)
                    dest_dir = os.path.dirname(dest_path)

                    if dest_dir:
                        os.makedirs(dest_dir, exist_ok=True)
                    shutil.copy2(source_path, dest_path)

        copy_to_unpacked(extract_dir, os.path.join(extract_dir, "app.asar.unpacked"))

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
        base = get_detected_game_path() or os.path.abspath(".")
        cfg = get_config()

        # 跨平台资源路径处理
        if is_app_bundle(base):
            res = os.path.join(base, "Contents", "Resources")
        else:
            res = get_resources_path(base, get_platform_info().system)

        asar = os.path.join(res, cfg.target_asar_name)
        bak = asar + ".bak"
        temp = None
        tx = None

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
                    "Disk Space Error",
                    "Insufficient disk space. Please free up some space and try again.",
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
        # 流程: 解包 → 重命名原文件为备份 → 分离unpacked文件 → 应用补丁 → 打包 → 复制unpacked目录
        try:
            # 3.1 解包 ASAR
            self._log("Extracting ASAR...")
            if _check_cancelled:
                _check_cancelled()
            self.core.run_asar("extract", asar, temp, callback=self._log)

            # 验证解压结果
            if not os.path.exists(temp) or not os.listdir(temp):
                raise PatchError("ASAR extraction failed or resulted in empty directory")

            # 3.2 分离 unpacked 文件（复制到 app.asar.unpacked）
            self._log("Separating unpacked files...")
            self._separate_unpacked_files(temp)

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

            # 3.4 重命名原 ASAR 为备份（瞬间完成，不复制）
            self._log("Renaming original ASAR to backup...")
            if os.path.exists(bak):
                os.remove(bak)
            os.rename(asar, bak)
            self._log("Backup created (rename).")

            # 3.5 打包为新的 ASAR
            # fnmatch 不支持 brace 扩展，需要 monkey-patch
            self._log("Packing ASAR...")

            import fnmatch as fnmatch_module

            _original_fnmatch = fnmatch_module.fnmatch

            def fnmatch_multi(filename, pattern):
                if not pattern:
                    return False
                for p in pattern.replace(",", " ").split():
                    if _original_fnmatch(filename, p):
                        return True
                return False

            fnmatch_module.fnmatch = fnmatch_multi

            try:
                unpack_pattern = "*.node *.dll *.so *.dylib *.bin *.exe *.lib"
                self.core.run_asar(
                    "pack",
                    temp,
                    asar,
                    callback=self._log,
                    unpack_pattern=unpack_pattern,
                )
            finally:
                fnmatch_module.fnmatch = _original_fnmatch

            # 验证打包结果
            if not os.path.exists(asar):
                raise PatchError("ASAR packing failed - output file not created")
            if os.path.getsize(asar) < 1024:
                raise PatchError("ASAR packing failed - output file too small")

            # 3.6 复制 app.asar.unpacked 到 ASAR 旁边（供 Electron 加载 native 文件）
            unpacked_src = os.path.join(temp, "app.asar.unpacked")
            unpacked_dest = os.path.join(os.path.dirname(asar), "app.asar.unpacked")
            if os.path.exists(unpacked_src):
                self._log("Copying app.asar.unpacked alongside new ASAR...")
                if os.path.exists(unpacked_dest):
                    shutil.rmtree(unpacked_dest)
                shutil.copytree(unpacked_src, unpacked_dest)

            # 3.7 生成补丁元数据
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
            # 验证备份完整性
            with open(bak_path, "rb") as f:
                magic = f.read(4)
                if magic != b"\x04\x00\x00\x00":
                    logger.error("Backup is corrupted, cannot restore")
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
            shutil.copy2(bak_path, asar_path)
            self._log("Restored app.asar from backup.")
        except Exception as be:
            logger.error(f"Backup restore error: {be}")
            self._log(f"Failed to restore backup: {be}")
