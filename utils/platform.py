# -*- coding: utf-8 -*-
"""
跨平台检测模块

提供跨平台的 Steam 游戏路径检测和平台信息获取。
"""

import os
import sys
import platform
import logging
from typing import Optional, Tuple, List
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class PlatformInfo:
    """平台信息"""
    system: str  # 'windows', 'darwin', 'linux'
    arch: str  # 'x86_64', 'arm64', etc.
    steam_common_path: str  # Steam games common path


def get_platform_info() -> PlatformInfo:
    """
    获取当前平台信息

    Returns:
        PlatformInfo: 包含平台信息的对象
    """
    system = sys.platform.lower()

    if system.startswith("win"):
        system_name = "windows"
        steam_path = os.path.join(
            os.environ.get("ProgramFiles", "C:\\Program Files"),
            "Steam",
            "steamapps",
            "common"
        )
    elif system.startswith("darwin"):
        system_name = "darwin"
        steam_path = os.path.join(
            os.path.expanduser("~/Library/Application Support"),
            "Steam",
            "steamapps",
            "common"
        )
    elif system.startswith("linux"):
        system_name = "linux"
        # 检查多个可能的 Steam 路径
        steam_path = os.path.join(
            os.path.expanduser("~/.local/share"),
            "Steam",
            "steamapps",
            "common"
        )
    else:
        system_name = "unknown"
        steam_path = ""

    return PlatformInfo(
        system=system_name,
        arch=platform.machine().lower(),
        steam_common_path=steam_path
    )


def get_steam_library_paths() -> List[str]:
    """
    获取所有 Steam 库目录（支持多库配置）

    Returns:
        List[str]: Steam 库目录列表
    """
    info = get_platform_info()
    paths = [info.steam_common_path]

    if info.system == "windows":
        # Windows: 检查其他可能的盘符
        for drive in range(ord('D'), ord('Z') + 1):
            path = f"{chr(drive)}:\\Program Files\\Steam\\steamapps\\common"
            if os.path.exists(path):
                paths.append(path)
    elif info.system == "linux":
        # Linux: 检查其他常见位置
        linux_paths = [
            os.path.expanduser("~/.steam/steam"),
            "/home/.steam/steam",
            "/usr/share/steam",
        ]
        for base in linux_paths:
            common = os.path.join(base, "steamapps", "common")
            if os.path.exists(common) and common not in paths:
                paths.append(common)

    return paths


def find_game_in_steam(game_name: str, search_paths: Optional[List[str]] = None) -> Optional[str]:
    """
    在 Steam 目录中查找游戏

    Args:
        game_name: 游戏目录名称
        search_paths: 可选的搜索路径列表

    Returns:
        str: 游戏目录路径，未找到返回 None
    """
    if search_paths is None:
        search_paths = get_steam_library_paths()

    for base in search_paths:
        if not os.path.exists(base):
            continue

        game_path = os.path.join(base, game_name)
        if os.path.isdir(game_path):
            logger.info(f"Found game at: {game_path}")
            return game_path

        # macOS: 游戏可能是 .app bundle
        app_path = os.path.join(base, f"{game_name}.app")
        if os.path.isdir(app_path):
            logger.info(f"Found game app bundle at: {app_path}")
            return app_path

    return None


def get_game_executable_name(game_name: str, system: Optional[str] = None) -> str:
    """
    获取游戏可执行文件名称

    Args:
        game_name: 游戏目录/名称
        system: 可选的平台名称

    Returns:
        str: 可执行文件名称
    """
    if system is None:
        info = get_platform_info()
        system = info.system

    if system == "darwin":
        # macOS: 返回 .app bundle 名称
        return f"{game_name}.app"
    else:
        # Windows/Linux: 返回 .exe 或无扩展名
        return f"{game_name}.exe"


def get_resources_path(game_path: str, system: Optional[str] = None) -> str:
    """
    获取游戏的 resources 目录路径

    Args:
        game_path: 游戏目录路径
        system: 可选的平台名称

    Returns:
        str: resources 目录路径
    """
    if system is None:
        info = get_platform_info()
        system = info.system

    if system == "darwin":
        # macOS: resources 在 .app/Contents/Resources/
        return os.path.join(game_path, "Contents", "Resources")
    else:
        # Windows/Linux: resources 在游戏目录下
        return os.path.join(game_path, "resources")


def get_asar_path(game_path: str, asar_name: str = "app.asar", system: Optional[str] = None) -> str:
    """
    获取 ASAR 文件路径

    Args:
        game_path: 游戏目录路径
        asar_name: ASAR 文件名
        system: 可选的平台名称

    Returns:
        str: ASAR 文件完整路径
    """
    resources = get_resources_path(game_path, system)
    return os.path.join(resources, asar_name)


def is_app_bundle(path: str) -> bool:
    """
    检查路径是否是 macOS app bundle

    Args:
        path: 路径

    Returns:
        bool: 是否为 app bundle
    """
    return path.endswith(".app") and os.path.isdir(path)


def get_bundle_executable_path(app_bundle_path: str) -> str:
    """
    获取 macOS app bundle 中的可执行文件路径

    Args:
        app_bundle_path: .app bundle 路径

    Returns:
        str: MacOS/main 可执行文件路径
    """
    return os.path.join(app_bundle_path, "Contents", "MacOS", "main")
