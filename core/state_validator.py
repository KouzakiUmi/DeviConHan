"""
系统状态一致性验证器

检查补丁工具相关文件的状态是否一致，
在启动时自动检测并修复不一致状态。
"""

__all__ = [
    "StateValidationError",
    "SystemState",
    "StateValidator",
    "validate_system_state",
]

import json
import logging
import os
from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Optional, Tuple

from core.config import get_config
from utils.asar_utils import get_file_hash_in_asar
from utils.platform import get_platform_info, get_resources_path, is_app_bundle

logger = logging.getLogger(__name__)


class SystemState(Enum):
    """系统状态枚举"""
    UNKNOWN = "unknown"
    CLEAN = "clean"  # 原始状态，未打补丁
    PATCHED = "patched"  # 已打补丁，状态正常
    INCONSISTENT = "inconsistent"  # 状态不一致
    CORRUPTED = "corrupted"  # 文件损坏
    PARTIAL_PATCH = "partial_patch"  # 部分补丁（可能中断）
    STEAM_UPDATED = "steam_updated"  # Steam已更新


@dataclass
class StateValidationError:
    """状态验证错误"""
    severity: str  # "critical", "warning", "info"
    message: str
    file_path: Optional[str] = None
    suggestion: str = ""


@dataclass
class FileState:
    """单个文件的状态"""
    path: str
    exists: bool
    size: int = 0
    hash: Optional[str] = None
    is_valid: bool = False


class StateValidator:
    """
    系统状态验证器

    检查以下文件的状态一致性：
    - app.asar (当前游戏资源)
    - app.asar.bak (原始备份)
    - .patch_info (补丁信息)
    - .patch_meta (补丁元数据)
    - Patch.zip/Patch/ (补丁数据源)
    """

    def __init__(self, base_dir: Optional[str] = None):
        """
        初始化验证器

        Args:
            base_dir: 基础目录，默认当前目录
        """
        self.base_dir = base_dir or os.path.abspath(".")
        self.config = get_config()

        # 获取平台信息
        self.platform_info = get_platform_info()

        # 跨平台资源路径处理
        if is_app_bundle(self.base_dir):
            # macOS .app bundle 情况
            self.res_dir = os.path.join(self.base_dir, "Contents", "Resources")
        else:
            # Windows/Linux: 使用平台检测
            self.res_dir = get_resources_path(self.base_dir, self.platform_info.system)

        self.asar_path = os.path.join(self.res_dir, self.config.target_asar_name)
        self.bak_path = self.asar_path + ".bak"
        self.patch_info_path = os.path.join(self.base_dir, self.config.patch_info_file)
        self.patch_meta_path = os.path.join(self.base_dir, self.config.patch_meta_file)

        self.errors: List[StateValidationError] = []
        self.warnings: List[StateValidationError] = []
        self.infos: List[StateValidationError] = []

    def validate_all(self) -> Tuple[SystemState, List[StateValidationError]]:
        """
        执行完整的系统状态验证

        Returns:
            Tuple[SystemState, List[StateValidationError]]: (系统状态, 错误列表)
        """
        self.errors = []
        self.warnings = []
        self.infos = []

        logger.info("Starting system state validation...")

        # 1. 检查基础路径
        self._validate_base_paths()

        # 2. 检查ASAR文件
        asar_state = self._validate_asar()

        # 3. 检查备份文件
        bak_state = self._validate_backup()

        # 4. 检查补丁元数据
        meta_state = self._validate_patch_meta()

        # 5. 检查补丁信息
        info_state = self._validate_patch_info()

        # 6. 综合分析状态
        system_state = self._analyze_state(asar_state, bak_state, meta_state, info_state)

        all_issues = self.errors + self.warnings + self.infos

        if not all_issues:
            logger.info(f"System state validation passed: {system_state.value}")
        else:
            logger.warning(f"System state: {system_state.value}, issues found: {len(all_issues)}")

        return system_state, all_issues

    def _validate_base_paths(self) -> None:
        """验证基础路径"""
        if not os.path.exists(self.res_dir):
            self.errors.append(StateValidationError(
                severity="critical",
                message=f"Resources directory not found: {self.res_dir}",
                file_path=self.res_dir,
                suggestion="Please ensure the patcher is in the game directory"
            ))

    def _validate_asar(self) -> FileState:
        """验证ASAR文件"""
        state = FileState(path=self.asar_path, exists=os.path.exists(self.asar_path))

        if not state.exists:
            self.warnings.append(StateValidationError(
                severity="warning",
                message="ASAR file not found",
                file_path=self.asar_path,
                suggestion="If Steam just updated, restore from backup first"
            ))
            return state

        try:
            state.size = os.path.getsize(self.asar_path)

            # 检查ASAR完整性（magic number）
            with open(self.asar_path, 'rb') as f:
                magic = f.read(4)
                if magic != b'\x04\x00\x00\x00':  # ASAR magic number
                    self.errors.append(StateValidationError(
                        severity="critical",
                        message=f"ASAR file is corrupted (invalid magic number: {magic.hex()})",
                        file_path=self.asar_path,
                        suggestion="Restore from backup or verify game files in Steam"
                    ))
                    state.is_valid = False
                else:
                    state.is_valid = True

        except Exception as e:
            self.errors.append(StateValidationError(
                severity="critical",
                message=f"Failed to validate ASAR: {e}",
                file_path=self.asar_path
            ))

        return state

    def _validate_backup(self) -> FileState:
        """验证备份文件"""
        state = FileState(path=self.bak_path, exists=os.path.exists(self.bak_path))

        if not state.exists:
            self.infos.append(StateValidationError(
                severity="info",
                message="Backup file not found - this is normal for first-time patching",
                file_path=self.bak_path
            ))
            return state

        try:
            state.size = os.path.getsize(self.bak_path)

            # 验证备份完整性
            with open(self.bak_path, 'rb') as f:
                magic = f.read(4)
                if magic != b'\x04\x00\x00\x00':
                    self.warnings.append(StateValidationError(
                        severity="warning",
                        message="Backup file is corrupted",
                        file_path=self.bak_path,
                        suggestion="Backup will be recreated when you apply patch"
                    ))
                else:
                    state.is_valid = True

        except Exception as e:
            self.warnings.append(StateValidationError(
                severity="warning",
                message=f"Failed to validate backup: {e}",
                file_path=self.bak_path
            ))

        return state

    def _validate_patch_meta(self) -> Optional[Dict]:
        """验证补丁元数据"""
        if not os.path.exists(self.patch_meta_path):
            return None

        try:
            with open(self.patch_meta_path, encoding='utf-8') as f:
                meta = json.load(f)

            # 验证必要字段
            if 'patch_files' not in meta:
                self.warnings.append(StateValidationError(
                    severity="warning",
                    message="Patch meta is missing 'patch_files' field",
                    file_path=self.patch_meta_path
                ))

            return meta

        except json.JSONDecodeError as e:
            self.warnings.append(StateValidationError(
                severity="warning",
                message=f"Patch meta is corrupted (JSON error): {e}",
                file_path=self.patch_meta_path,
                suggestion="Meta file will be regenerated when you apply patch"
            ))
        except Exception as e:
            self.warnings.append(StateValidationError(
                severity="warning",
                message=f"Failed to read patch meta: {e}",
                file_path=self.patch_meta_path
            ))

        return None

    def _validate_patch_info(self) -> Optional[Dict]:
        """验证补丁信息"""
        if not os.path.exists(self.patch_info_path):
            return None

        try:
            with open(self.patch_info_path, encoding='utf-8') as f:
                info = json.load(f)
            return info
        except Exception as e:
            self.warnings.append(StateValidationError(
                severity="warning",
                message=f"Failed to read patch info: {e}",
                file_path=self.patch_info_path
            ))
            return None

    def _analyze_state(
        self,
        asar_state: FileState,
        bak_state: FileState,
        meta_state: Optional[Dict],
        info_state: Optional[Dict]
    ) -> SystemState:
        """
        综合分析系统状态

        状态矩阵：
        - ASAR存在 + 备份不存在 + 无元数据 = CLEAN (原始状态)
        - ASAR存在 + 备份存在 + 有元数据 = PATCHED (已打补丁)
        - ASAR不存在 + 备份存在 = STEAM_UPDATED (Steam更新)
        - ASAR存在 + 备份存在 + 无元数据 = INCONSISTENT (不一致)
        - ASAR损坏 = CORRUPTED (损坏)
        """

        # 检查是否损坏
        if asar_state.exists and not asar_state.is_valid:
            return SystemState.CORRUPTED

        # ASAR和备份都不存在
        if not asar_state.exists and not bak_state.exists:
            return SystemState.CORRUPTED

        # ASAR不存在但备份存在 - Steam更新
        if not asar_state.exists and bak_state.exists:
            return SystemState.STEAM_UPDATED

        # ASAR存在但备份不存在
        if asar_state.exists and not bak_state.exists:
            if meta_state or info_state:
                # 有元数据但没有备份 - 不一致
                self.warnings.append(StateValidationError(
                    severity="warning",
                    message="Patch metadata exists but no backup found",
                    suggestion="The patch may have been applied by another tool"
                ))
                return SystemState.INCONSISTENT
            return SystemState.CLEAN

        # ASAR和备份都存在
        if asar_state.exists and bak_state.exists:
            if meta_state:
                # 验证补丁是否完整应用
                if self._verify_patch_integrity(meta_state):
                    return SystemState.PATCHED
                else:
                    return SystemState.PARTIAL_PATCH
            else:
                # 有备份但没有元数据
                self.warnings.append(StateValidationError(
                    severity="warning",
                    message="Backup exists but no patch metadata",
                    suggestion="You may need to reapply the patch"
                ))
                return SystemState.INCONSISTENT

        return SystemState.UNKNOWN

    def _verify_patch_integrity(self, meta: Dict) -> bool:
        """
        验证补丁完整性

        检查ASAR中的关键文件是否与元数据中的哈希匹配
        """
        patch_files = meta.get('patch_files', {})
        if not patch_files:
            return True

        # 只检查前3个文件，避免太慢
        check_count = 0
        for file_path, expected_hash in patch_files.items():
            if check_count >= 3:
                break
            try:
                actual_hash = get_file_hash_in_asar(self.asar_path, file_path)
                if actual_hash != expected_hash:
                    return False
                check_count += 1
            except Exception:
                # 如果无法读取，可能是部分补丁
                return False

        return True

    def can_apply_patch(self) -> Tuple[bool, str]:
        """
        检查是否可以安全地应用补丁

        Returns:
            Tuple[bool, str]: (是否可以, 原因)
        """
        state, issues = self.validate_all()

        critical_errors = [e for e in issues if e.severity == "critical"]
        if critical_errors:
            return False, f"Critical errors found: {critical_errors[0].message}"

        if state == SystemState.CORRUPTED:
            return False, "Game files are corrupted. Please verify integrity in Steam first."

        if state == SystemState.PATCHED:
            return False, "Game is already patched. No need to apply again."

        return True, "Ready to apply patch"

    def can_restore_backup(self) -> Tuple[bool, str]:
        """
        检查是否可以恢复备份

        Returns:
            Tuple[bool, str]: (是否可以, 原因)
        """
        if not os.path.exists(self.bak_path):
            return False, "Backup file not found"

        try:
            with open(self.bak_path, 'rb') as f:
                magic = f.read(4)
                if magic != b'\x04\x00\x00\x00':
                    return False, "Backup file is corrupted"
        except Exception as e:
            return False, f"Cannot read backup: {e}"

        return True, "Ready to restore"


def validate_system_state(base_dir: Optional[str] = None) -> Tuple[SystemState, List[StateValidationError]]:
    """
    便捷函数：验证系统状态

    Args:
        base_dir: 基础目录

    Returns:
        Tuple[SystemState, List[StateValidationError]]: (状态, 问题列表)
    """
    validator = StateValidator(base_dir)
    return validator.validate_all()
