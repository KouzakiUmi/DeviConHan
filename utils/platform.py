# -*- coding: utf-8 -*-
"""
跨平台检测模块

提供跨平台的 Steam 游戏路径检测和平台信息获取。
"""

import os
import sys
import platform
import logging
import re
from typing import Optional, Tuple, List
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class PlatformInfo:
    """平台信息"""
    system: str  # 'windows', 'darwin', 'linux'
    arch: str  # 'x86_64', 'arm64', etc.
    steam_common_path: str  # Primary Steam installation path


def get_platform_info() -> PlatformInfo:
    """
    获取当前平台信息

    Returns:
        PlatformInfo: 包含平台信息的对象
    """
    system = sys.platform.lower()

    if system.startswith("win"):
        system_name = "windows"
        # 尝试多个可能的 Steam 安装位置
        steam_path = _find_steam_path_windows()
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
        steam_path = os.path.join(
            os.path.expanduser("~/.steam/steam"),
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


def _find_steam_path_windows() -> str:
    """
    在 Windows 上查找 Steam 安装路径

    Returns:
        str: Steam 路径，找不到返回默认路径
    """
    # 默认路径
    default_path = os.path.join(
        os.environ.get("ProgramFiles", "C:\\Program Files"),
        "Steam",
        "steamapps",
        "common"
    )

    # 首先检查常见位置
    common_paths = [
        os.path.join(os.environ.get("ProgramFiles", "C:\\Program Files"), "Steam"),
        os.path.join(os.environ.get("ProgramFiles(x86)", "C:\\Program Files (x86)"), "Steam"),
        os.path.join(os.environ.get("ProgramW6432", "C:\\Program Files"), "Steam"),
    ]

    for path in common_paths:
        if os.path.isdir(path):
            steamapps = os.path.join(path, "steamapps")
            if os.path.isdir(steamapps):
                logger.info(f"Found Steam at: {path}")
                return os.path.join(steamapps, "common")

    # 尝试从注册表读取 (需要 winreg)
    try:
        import winreg
        key = winreg.OpenKey(
            winreg.HKEY_LOCAL_MACHINE,
            r"SOFTWARE\WOW6432Node\Valve\Steam"
        )
        value, _ = winreg.QueryValueEx(key, "InstallPath")
        winreg.CloseKey(key)
        if value and os.path.isdir(value):
            steamapps = os.path.join(value, "steamapps")
            if os.path.isdir(steamapps):
                logger.info(f"Found Steam from registry: {value}")
                return os.path.join(steamapps, "common")
    except Exception:
        pass

    # 尝试从用户注册表
    try:
        import winreg
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"SOFTWARE\Valve\Steam"
        )
        value, _ = winreg.QueryValueEx(key, "SteamPath")
        winreg.CloseKey(key)
        if value and os.path.isdir(value):
            steamapps = os.path.join(value, "steamapps")
            if os.path.isdir(steamapps):
                logger.info(f"Found Steam from user registry: {value}")
                return os.path.join(steamapps, "common")
    except Exception:
        pass

    return default_path


def get_steam_library_paths() -> List[str]:
    """
    获取所有 Steam 库目录（支持多库配置）

    通过搜索 common 目录下存在 SteamLibrary 标识的路径，
    或者从 Steam 配置文件中读取自定义库路径。

    Returns:
        List[str]: Steam 库目录列表
    """
    info = get_platform_info()
    paths = []

    # 添加主库路径
    if info.system == "windows":
        # 主 Steam 路径
        main_steam = os.path.dirname(info.steam_common_path)  # steamapps
        if os.path.isdir(main_steam):
            paths.append(main_steam)

        # 搜索所有盘符中的 SteamLibrary
        for drive in range(ord('D'), ord('Z') + 1):
            drive_letter = f"{chr(drive)}:\\"
            if os.path.isdir(drive_letter):
                # 搜索 SteamLibrary 目录
                _search_steam_libraries(drive_letter, paths)
    elif info.system == "darwin":
        base = os.path.dirname(os.path.dirname(info.steam_common_path))  # Steam
        paths.append(os.path.join(base, "steamapps"))
        # 搜索其他位置
        for prefix in ["/Volumes", "/Users"]:
            if os.path.exists(prefix):
                _search_steam_libraries(prefix, paths)
    elif info.system == "linux":
        # Linux Steam 路径
        paths.append(os.path.dirname(info.steam_common_path))  # steamapps

        # 搜索常见位置
        for home in ["/home", "/media", "/mnt"]:
            if os.path.exists(home):
                _search_steam_libraries(home, paths)

    # 去重
    seen = set()
    unique_paths = []
    for p in paths:
        normalized = os.path.normpath(p)
        if normalized not in seen and os.path.isdir(p):
            seen.add(normalized)
            unique_paths.append(p)

    logger.info(f"Found Steam library paths: {unique_paths}")
    return unique_paths


def _search_steam_libraries(root: str, results: List[str], depth: int = 0):
    """
    递归搜索包含 SteamLibrary 标识的目录

    Args:
        root: 搜索根目录
        results: 结果列表
        depth: 当前递归深度
    """
    if depth > 4:  # 限制深度避免太深
        return

    try:
        entries = os.listdir(root)
    except (PermissionError, OSError):
        return

    for entry in entries:
        if entry in results:
            continue

        full_path = os.path.join(root, entry)
        if not os.path.isdir(full_path):
            continue

        # 检查是否是 SteamLibrary
        if _is_steam_library(full_path):
            steamapps = os.path.join(full_path, "steamapps")
            if os.path.isdir(steamapps):
                results.append(steamapps)
                logger.info(f"Found Steam library: {steamapps}")

        # 继续递归搜索子目录
        _search_steam_libraries(full_path, results, depth + 1)


def _is_steam_library(path: str) -> bool:
    """
    检查目录是否是 Steam 库目录

    Args:
        path: 目录路径

    Returns:
        bool: 是否是 Steam 库目录
    """
    if not os.path.isdir(path):
        return False

    # 检查关键标识
    steamapps = os.path.join(path, "steamapps")
    if not os.path.isdir(steamapps):
        return False

    # 检查 libraryfolders.vdf 或 steam.cfg
    library_folders = [
        os.path.join(path, "steamapps", "libraryfolders.vdf"),
        os.path.join(path, "steam.cfg"),
        os.path.join(path, "Steam.cfg"),
    ]

    for f in library_folders:
        if os.path.isfile(f):
            return True

    # 或者目录名包含 SteamLibrary
    if "steamlibrary" in path.lower():
        return True

    # 或者检查常见的 steamapps 结构
    common_marker = os.path.join(path, "steamapps", "common")
    if os.path.isdir(common_marker):
        # 检查是否有任何游戏目录
        try:
            entries = os.listdir(common_marker)
            # 如果有 .acf 文件（Steam 应用数据），认为是库目录
            for e in entries:
                if e.endswith('.acf'):
                    return True
        except (PermissionError, OSError):
            pass

    return False


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

    # 规范化游戏名称用于匹配
    normalized_name = game_name.lower().strip()
    variations = [
        normalized_name,
        normalized_name.replace(" ", "_"),
        normalized_name.replace(" ", "-"),
        normalized_name.replace("_", " "),
        normalized_name.replace("-", " "),
    ]

    for base in search_paths:
        common_dir = os.path.join(base, "common")
        if not os.path.isdir(common_dir):
            continue

        # 列出所有游戏目录
        try:
            for entry in os.listdir(common_dir):
                entry_lower = entry.lower()
                # 精确匹配
                if entry_lower == normalized_name:
                    game_path = os.path.join(common_dir, entry)
                    logger.info(f"Found game (exact match) at: {game_path}")
                    return game_path

                # 模糊匹配
                for var in variations:
                    if var in entry_lower or entry_lower in var:
                        game_path = os.path.join(common_dir, entry)
                        logger.info(f"Found game (fuzzy match '{entry}') at: {game_path}")
                        return game_path

        except (PermissionError, OSError) as e:
            logger.debug(f"Cannot access {common_dir}: {e}")
            continue

    # 如果在 common 中没找到，尝试在整个 steamapps 中搜索
    for base in search_paths:
        steamapps_dir = base
        if not os.path.isdir(steamapps_dir):
            continue

        try:
            for entry in os.listdir(steamapps_dir):
                entry_lower = entry.lower()
                for var in variations:
                    if var in entry_lower:
                        full_path = os.path.join(steamapps_dir, entry)
                        if os.path.isdir(full_path):
                            logger.info(f"Found game (deep match '{entry}') at: {full_path}")
                            return full_path
        except (PermissionError, OSError):
            continue

    logger.warning(f"Game '{game_name}' not found in Steam libraries")
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
