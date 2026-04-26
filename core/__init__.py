"""
核心模块

包含补丁操作、配置管理、Steam 更新检测等核心逻辑。
"""

from core.bootstrap import bootstrap_system, get_runtime_game_path
from core.config import get_config
from core.fuse import remove_fuse, restore_fuse, verify_fuse_backup
from core.patch_info import has_embedded_patch, save_patch_info, save_patch_meta
from core.patcher import CoreLogic
from core.save_service import SaveService
from core.state_validator import StateValidator, SystemState, validate_system_state
from core.steam import handle_steam_update

__all__ = [
    "bootstrap_system",
    "get_runtime_game_path",
    "get_config",
    "remove_fuse",
    "restore_fuse",
    "verify_fuse_backup",
    "has_embedded_patch",
    "save_patch_info",
    "save_patch_meta",
    "CoreLogic",
    "SaveService",
    "StateValidator",
    "SystemState",
    "validate_system_state",
    "handle_steam_update",
]
