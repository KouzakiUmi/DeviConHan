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

import json
import logging
import os
import shutil
from typing import Callable, Optional, Tuple

from core.bootstrap import get_runtime_game_path
from core.config import get_config
from core.patch_info import save_patch_info, save_patch_meta
from core.state_validator import StateValidator, SystemState
from core.steam import handle_steam_update
from utils.asar_utils import validate_asar_with_reason
from utils.cleanup import force_cleanup_dir
from utils.constants import BATCH_CANCEL_OR_ERROR_MSG
from utils.disk_utils import (
    check_operation_space,
)
from utils.file_ops import detect_patch_zip_root, safe_extract_zip
from utils.language import T
from utils.operation_lock import FileOperationLock, OperationType
from utils.paths import get_resource_path, safe_path_within
from utils.platform import get_platform_info, get_resources_path

logger = logging.getLogger(__name__)

_TRANSACTION_FILE = ".patch_transaction.json"


def _transaction_path(base_dir: str) -> str:
    return os.path.join(base_dir, _TRANSACTION_FILE)


def _write_transaction(base_dir: str, phase: str) -> None:
    """Persist a tiny recovery marker before a game-file state transition."""
    path = _transaction_path(base_dir)
    temp_path = path + ".tmp"
    with open(temp_path, "w", encoding="utf-8") as f:
        json.dump({"phase": phase}, f)
        f.flush()
        os.fsync(f.fileno())
    os.replace(temp_path, path)


def _clear_transaction(base_dir: str) -> None:
    try:
        os.remove(_transaction_path(base_dir))
    except FileNotFoundError:
        pass


def _remove_patch_metadata(base_dir: str) -> None:
    """Remove state files that only describe an installed patch."""
    cfg = get_config()
    for filename in (cfg.patch_info_file, cfg.patch_meta_file):
        path = os.path.join(base_dir, filename)
        for candidate in (path, path + ".tmp", path + ".old"):
            try:
                os.remove(candidate)
            except FileNotFoundError:
                pass


def recover_incomplete_patch(base_dir: str) -> Optional[str]:
    """Restore the original ASAR after an interrupted commit, when possible.

    The marker is intentionally conservative: an unverified transaction is
    always rolled back to the known backup rather than trying to guess whether
    a partially-written ASAR is usable.
    """
    marker = _transaction_path(base_dir)
    if not os.path.exists(marker):
        return None

    cfg = get_config()
    res = get_resources_path(base_dir, get_platform_info().system)
    asar = os.path.join(res, cfg.target_asar_name)
    bak = asar + ".bak"
    staged = asar + ".new"
    asar_unpacked = asar + ".unpacked"
    bak_unpacked = bak + ".unpacked"
    staged_unpacked = staged + ".unpacked"
    file_lock = FileOperationLock(asar)
    if not file_lock.acquire():
        message = "Another patch process is active; deferred transaction recovery."
        logger.warning(message)
        return message
    try:
        if not os.path.exists(marker):
            return None
        phase = "committing"
        try:
            with open(marker, encoding="utf-8") as f:
                marker_data = json.load(f)
            if isinstance(marker_data, dict) and marker_data.get("phase") in {
                "packing",
                "committing",
                "restoring",
            }:
                phase = marker_data["phase"]
        except (OSError, ValueError) as e:
            logger.warning("Could not read patch transaction marker: %s", e)

        if phase == "restoring":
            # Manual restore commits with one atomic bak -> live replacement.
            # A remaining backup therefore means the commit never happened;
            # otherwise finish the sidecar/metadata cleanup after a crash.
            if os.path.exists(bak):
                message = "Cancelled an incomplete manual restore; game files were unchanged."
            elif os.path.exists(asar):
                PatchController._replace_unpacked_sidecar(bak, asar)
                _remove_patch_metadata(base_dir)
                message = "Completed cleanup after an interrupted manual restore."
            else:
                message = "Manual restore was interrupted and no usable ASAR is available."
                logger.error(message)
                return message
        elif phase == "packing":
            message = "Removed an incomplete staged ASAR; the original was unchanged."
        elif os.path.exists(bak):
            if os.path.exists(asar):
                os.remove(asar)
            if os.path.isdir(asar_unpacked):
                shutil.rmtree(asar_unpacked, ignore_errors=True)
            os.replace(bak, asar)
            if os.path.isdir(bak_unpacked):
                os.replace(bak_unpacked, asar_unpacked)
            message = "Recovered original ASAR from an incomplete patch transaction."
        else:
            message = "Found an incomplete patch transaction, but no ASAR backup is available."
        if os.path.exists(staged):
            os.remove(staged)
        if os.path.isdir(staged_unpacked):
            shutil.rmtree(staged_unpacked, ignore_errors=True)
        _clear_transaction(base_dir)
        logger.warning(message)
        return message
    except OSError as e:
        logger.error("Could not recover incomplete patch transaction: %s", e)
        return f"Could not recover incomplete patch transaction: {e}"
    finally:
        file_lock.release()


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
                    self._log(T("log_patch_corrupted_restoring"))
                    try:
                        os.remove(asar)
                    except Exception as e:
                        return False, f"Failed to remove corrupted ASAR: {e}"
                # 重命名 bak → app.asar（原子操作）
                try:
                    os.replace(bak, asar)
                    bak_unpacked = bak + ".unpacked"
                    asar_unpacked = asar + ".unpacked"
                    if os.path.isdir(bak_unpacked):
                        if os.path.isdir(asar_unpacked):
                            shutil.rmtree(asar_unpacked, ignore_errors=True)
                        os.replace(bak_unpacked, asar_unpacked)
                    self._log(T("log_patch_restored_backup"))
                except Exception as e:
                    return False, f"Failed to restore from backup: {e}"
            elif asar_corrupted:
                msg = T("err_asar_corrupted_no_backup")
                if asar_reason:
                    msg += f"\n\n{T('lbl_reason', 'Reason')}: {asar_reason}"
                return False, msg

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

        cfg = get_config()
        base = get_runtime_game_path() or os.path.abspath(".")
        asar = os.path.join(
            get_resources_path(base, get_platform_info().system), cfg.target_asar_name
        )
        file_lock = FileOperationLock(asar)
        if not file_lock.acquire():
            lock.release(OperationType.PATCH)
            return False, None, "该游戏目录正在被另一个补丁工具操作"

        _check_cancelled = kwargs.get("_check_cancelled")

        try:
            return self._do_run_auto_patch(gui_app, _check_cancelled)
        finally:
            file_lock.release()
            lock.release(OperationType.PATCH)

    def restore_patch(self) -> Tuple[bool, str]:
        """Restore the original ASAR backup and remove installed-patch state."""
        from utils.operation_lock import get_operation_lock

        lock = get_operation_lock()
        if not lock.acquire(OperationType.PATCH):
            return False, T("warn_operation_in_progress", "Another operation is in progress.")

        cfg = get_config()
        base = get_runtime_game_path() or os.path.abspath(".")
        asar = os.path.join(
            get_resources_path(base, get_platform_info().system), cfg.target_asar_name
        )
        file_lock = FileOperationLock(asar)
        if not file_lock.acquire():
            lock.release(OperationType.PATCH)
            return False, T(
                "err_patch_directory_busy",
                "The game directory is being modified by another patch process.",
            )

        try:
            return self._do_restore_patch(base, asar)
        finally:
            file_lock.release()
            lock.release(OperationType.PATCH)

    def _do_restore_patch(self, base: str, asar: str) -> Tuple[bool, str]:
        """Perform the locked manual restore operation."""
        bak = asar + ".bak"
        if not os.path.exists(bak):
            return False, T(
                "err_patch_backup_not_found",
                "No original ASAR backup was found. Verify the game files in Steam to restore them.",
            )

        try:
            valid, reason = validate_asar_with_reason(bak)
        except Exception as e:
            valid, reason = False, str(e)
        if not valid:
            return False, T(
                "err_patch_backup_invalid",
                "The original ASAR backup is invalid: {reason}",
            ).format(reason=reason)

        self._log(T("log_patch_restoring_original", "Restoring the original game files..."))
        try:
            # The backup and live archive are siblings, so os.replace performs
            # a single atomic commit without exposing a missing app.asar.
            _write_transaction(base, "restoring")
            os.replace(bak, asar)
            self._replace_unpacked_sidecar(bak, asar)

            valid, reason = validate_asar_with_reason(asar)
            if not valid:
                raise PatchError(f"Restored ASAR failed validation: {reason}")

            _remove_patch_metadata(base)
            _clear_transaction(base)
            self._log(T("log_patch_restore_complete", "Original game files restored."))
            return True, T(
                "msg_patch_restore_success",
                "The patch was removed and the original game files were restored.",
            )
        except Exception as e:
            logger.exception("Manual patch restore failed")
            # If the atomic replacement already consumed the backup, retain
            # the marker so startup recovery can finish sidecar/metadata work.
            if os.path.exists(bak):
                _clear_transaction(base)
            return False, T(
                "err_patch_restore_failed",
                "Failed to restore the original game files: {error}",
            ).format(error=e)

    def _do_run_auto_patch(self, gui_app, _check_cancelled) -> Tuple[bool, Optional[str], str]:
        """实际的补丁安装逻辑"""
        base = get_runtime_game_path() or os.path.abspath(".")
        cfg = get_config()

        # 跨平台资源路径处理
        res = get_resources_path(base, get_platform_info().system)

        asar = os.path.join(res, cfg.target_asar_name)
        bak = asar + ".bak"
        temp = None
        staged_asar = asar + ".new"

        # Validate the embedded payload layout before extracting a potentially
        # very large ASAR or changing any game/backup state.
        patch_zip = get_resource_path("Patch.zip")
        patch_dir = get_resource_path("Patch")
        patch_root = ""
        if os.path.exists(patch_zip):
            try:
                patch_root = detect_patch_zip_root(
                    patch_zip,
                    getattr(cfg, "check_files_for_update", ()),
                )
            except (OSError, ValueError) as e:
                return (
                    False,
                    None,
                    T(
                        "err_patch_zip_layout",
                        "Cannot determine the patch ZIP layout safely: {error}",
                    ).format(error=e),
                )

            if patch_root:
                self._log(T("log_patch_zip_root_detected").format(root=patch_root))
            else:
                self._log(T("log_patch_zip_root_direct"))
        elif not os.path.exists(patch_dir):
            return False, None, "Patch data not found"

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
            self._log(T("msg_already_patched"))
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
        need_backup = False
        try:
            need_backup = os.path.exists(asar) and not os.path.exists(bak)

            # 3.1 解包 ASAR
            self._log(T("log_patch_extracting_asar"))
            if _check_cancelled:
                _check_cancelled()
            extract_kwargs = {"callback": self._log}
            if _check_cancelled:
                extract_kwargs["check_cancelled"] = _check_cancelled
            _, unpacked_files = self.core.run_asar("extract", asar, temp, **extract_kwargs)

            # 验证解压结果
            if not os.path.exists(temp) or not os.listdir(temp):
                raise PatchError("ASAR extraction failed or resulted in empty directory")

            # 3.2 清理解包残留的 app.asar.unpacked 目录
            unpacked_leftover = os.path.join(temp, "app.asar.unpacked")
            if os.path.exists(unpacked_leftover):
                self._log(T("log_patch_cleaning_temp"))
                shutil.rmtree(unpacked_leftover, ignore_errors=True)

            # 3.3 应用补丁
            self._log(T("log_patch_applying"))

            if os.path.exists(patch_zip):
                self._log(T("log_patch_extracting_zip"))
                try:
                    extracted = safe_extract_zip(
                        patch_zip,
                        temp,
                        check_cancelled=_check_cancelled,
                        strip_prefix=patch_root,
                    )
                    if not extracted:
                        raise PatchError(f"Failed to extract patch data from: {patch_zip}")
                    self._log(T("log_patch_zip_extracted"))
                except ValueError as e:
                    raise PatchError(f"Security violation in patch ZIP: {e}") from e
            elif os.path.exists(patch_dir):
                self._log(T("log_patch_copying_dir"))

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
                self._log(T("log_patch_files_copied"))

            # 3.4 Build beside the original ASAR.  This writes the new archive
            # once, but keeps the playable original untouched until validation.
            if os.path.exists(staged_asar):
                os.remove(staged_asar)
            self._log(T("log_patch_packing_asar"))
            if _check_cancelled:
                _check_cancelled()
            _write_transaction(base, "packing")
            pack_kwargs = {"callback": self._log, "unpacked_files": unpacked_files}
            if _check_cancelled:
                pack_kwargs["check_cancelled"] = _check_cancelled
            self.core.run_asar("pack", temp, staged_asar, **pack_kwargs)

            # Lightweight post-build validation: structural ranges plus all
            # externally-unpacked files.  It avoids a second full 8GB read.
            valid, reason = validate_asar_with_reason(staged_asar)
            if not valid:
                raise PatchError(f"ASAR packing failed validation: {reason}")
            if os.path.getsize(staged_asar) < 1024:
                raise PatchError("ASAR packing failed - output file too small")
            staged_unpacked = staged_asar + ".unpacked"
            for relative_path in unpacked_files or set():
                if not os.path.isfile(os.path.join(staged_unpacked, relative_path)):
                    raise PatchError(
                        f"ASAR packing failed - unpacked file missing: {relative_path}"
                    )

            if _check_cancelled:
                _check_cancelled()

            # Commit is intentionally non-cancellable.  Both renames are in
            # the same directory; the journal lets the next launch recover
            # the backup if power is lost between them.
            _write_transaction(base, "committing")
            if need_backup:
                self._log(T("log_patch_creating_backup"))
                os.replace(asar, bak)
                asar_unpacked = asar + ".unpacked"
                bak_unpacked = bak + ".unpacked"
                if os.path.isdir(asar_unpacked):
                    if os.path.isdir(bak_unpacked):
                        shutil.rmtree(bak_unpacked, ignore_errors=True)
                    os.replace(asar_unpacked, bak_unpacked)
                self._log(T("log_patch_backup_created"))
            os.replace(staged_asar, asar)
            self._replace_unpacked_sidecar(staged_asar, asar)

            valid, reason = validate_asar_with_reason(asar)
            if not valid:
                raise PatchError(f"Committed ASAR failed validation: {reason}")

            self._log(T("log_patch_asar_replaced"))

            # 3.6 生成补丁元数据
            self._log(T("log_patch_generating_meta"))
            try:
                save_patch_info(base, asar, bak)
                save_patch_meta(base, temp)
            except Exception as e:
                logger.warning(f"Failed to save patch metadata: {e}")

            _clear_transaction(base)

            self._log(T("log_patch_complete"))
            self._log(T("patch_done", "✅ 安装完成！"))

            return True, temp, ""

        except PatchError as e:
            logger.error(f"Patch error: {e}")
            self._rollback_asar_on_failure(asar, bak, need_backup)
            self._cleanup_staged_asar(staged_asar)
            _clear_transaction(base)
            return False, temp, str(e)
        except Exception as e:
            logger.exception("Unexpected error during patching")
            self._rollback_asar_on_failure(asar, bak, need_backup)
            self._cleanup_staged_asar(staged_asar)
            _clear_transaction(base)
            return False, temp, f"Unexpected error: {e}"
        finally:
            # 清理临时目录
            if temp and os.path.exists(temp):
                try:
                    force_cleanup_dir(temp)
                except Exception as e:
                    logger.warning(f"Failed to cleanup temp directory: {e}")

    @staticmethod
    def _cleanup_staged_asar(staged_asar: str) -> None:
        """Best-effort cleanup of an uncommitted ASAR and unpacked sidecar."""
        for path in (staged_asar, staged_asar + ".unpacked"):
            try:
                if os.path.isdir(path):
                    shutil.rmtree(path, ignore_errors=True)
                elif os.path.exists(path):
                    os.remove(path)
            except OSError as e:
                logger.warning("Failed to remove staged ASAR artifact %s: %s", path, e)

    @staticmethod
    def _replace_unpacked_sidecar(staged_asar: str, asar: str) -> None:
        """Replace or remove the live sidecar to match the committed ASAR."""
        staged_unpacked = staged_asar + ".unpacked"
        asar_unpacked = asar + ".unpacked"
        if os.path.isdir(asar_unpacked):
            shutil.rmtree(asar_unpacked)
        elif os.path.exists(asar_unpacked):
            os.remove(asar_unpacked)
        if os.path.isdir(staged_unpacked):
            os.replace(staged_unpacked, asar_unpacked)

    @staticmethod
    def _rollback_asar_on_failure(asar: str, bak: str, need_backup: bool) -> None:
        if not need_backup or not os.path.exists(bak):
            return
        if os.path.exists(asar):
            try:
                os.remove(asar)
                logger.info("Removed unverified ASAR before rollback")
            except Exception as e:
                logger.warning(f"Failed to remove corrupted ASAR: {e}")
        try:
            asar_unpacked = asar + ".unpacked"
            bak_unpacked = bak + ".unpacked"
            if os.path.isdir(asar_unpacked):
                shutil.rmtree(asar_unpacked, ignore_errors=True)
            os.replace(bak, asar)
            if os.path.isdir(bak_unpacked):
                os.replace(bak_unpacked, asar_unpacked)
            logger.info(f"Rolled back ASAR from backup: {bak} -> {asar}")
        except Exception as e:
            logger.error(f"Failed to rollback ASAR from backup: {e}")

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
            self._log(T("log_patch_restored_backup"))
        except Exception as be:
            logger.error(f"Backup restore error: {be}")
            self._log(T("log_patch_restore_failed").format(error=be))
