# -*- coding: utf-8 -*-
"""
跨平台检测模块

提供跨平台的 Steam 游戏路径检测和平台信息获取。
"""

import os
import sys
import platform
import logging
import threading
from typing import Optional, List, Tuple
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
    default_path = os.path.join(
        os.environ.get("ProgramFiles", "C:\\Program Files"),
        "Steam",
        "steamapps",
        "common"
    )

    # 从注册表读取
    try:
        import winreg
        for root_key in [winreg.HKEY_LOCAL_MACHINE, winreg.HKEY_CURRENT_USER]:
            for sub_key in [r"SOFTWARE\WOW6432Node\Valve\Steam", r"SOFTWARE\Valve\Steam"]:
                try:
                    key = winreg.OpenKey(root_key, sub_key)
                    value, _ = winreg.QueryValueEx(key, "InstallPath")
                    winreg.CloseKey(key)
                    if value and os.path.isdir(value):
                        logger.info(f"Found Steam from registry: {value}")
                        return os.path.join(value, "steamapps", "common")
                except (FileNotFoundError, PermissionError, OSError):
                    continue
    except ImportError:
        pass

    return default_path


def get_steam_library_paths() -> List[str]:
    """
    获取所有 Steam 库目录（支持多库配置）

    Returns:
        List[str]: Steam 库目录列表 (steamapps 目录路径)
    """
    info = get_platform_info()
    paths = []

    # 主库路径 (从 steamapps/common 推出 steamapps)
    main_steamapps = os.path.dirname(info.steam_common_path)
    if os.path.isdir(main_steamapps):
        paths.append(main_steamapps)
        logger.info(f"Primary Steam library: {main_steamapps}")

    # 读取 libraryfolders.vdf 获取其他库
    library_folders_vdf = os.path.join(main_steamapps, "libraryfolders.vdf")
    if os.path.isfile(library_folders_vdf):
        try:
            with open(library_folders_vdf, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            # 解析 libraryfolders.vdf 提取路径
            for line in content.split('\n'):
                line = line.strip()
                if '"path"' in line.lower():
                    # 提取路径
                    import re
                    match = re.search(r'"path"\s*"([^"]+)"', line, re.IGNORECASE)
                    if match:
                        lib_path = match.group(1).replace('\\\\', '\\')
                        if os.path.isdir(lib_path):
                            lib_steamapps = os.path.join(lib_path, "steamapps")
                            if os.path.isdir(lib_steamapps) and lib_steamapps not in paths:
                                paths.append(lib_steamapps)
                                logger.info(f"Found Steam library from config: {lib_steamapps}")
        except Exception as e:
            logger.debug(f"Failed to parse libraryfolders.vdf: {e}")

    # Windows 上额外检查 SteamLibrary 目录（可选）
    if info.system == "windows":
        for base in ["E:\\", "D:\\"]:
            if os.path.isdir(base):
                for entry in os.listdir(base):
                    if "steamlibrary" in entry.lower():
                        lib_steamapps = os.path.join(base, entry, "steamapps")
                        if os.path.isdir(lib_steamapps) and lib_steamapps not in paths:
                            paths.append(lib_steamapps)
                            logger.info(f"Found Steam library: {lib_steamapps}")

    # 去重
    seen = set()
    unique_paths = []
    for p in paths:
        normalized = os.path.normpath(p)
        if normalized not in seen and os.path.isdir(p):
            seen.add(normalized)
            unique_paths.append(p)

    logger.info(f"Total Steam library paths found: {len(unique_paths)}")
    return unique_paths


def find_game_in_steam(game_name: str, search_paths: Optional[List[str]] = None, timeout: float = 10.0) -> Optional[str]:
    """
    在 Steam 目录中查找游戏

    Args:
        game_name: 游戏目录名称
        search_paths: 可选的搜索路径列表
        timeout: 搜索超时（秒）

    Returns:
        str: 游戏目录路径，未找到返回 None
    """
    if search_paths is None:
        search_paths = get_steam_library_paths()

    # 规范化游戏名称
    normalized_name = game_name.lower().strip()
    variations = [
        normalized_name,
        normalized_name.replace(" ", "_"),
        normalized_name.replace(" ", "-"),
        normalized_name.replace("_", " "),
        normalized_name.replace("-", " "),
        # 日语变体
        normalized_name.replace("でびるこねくしょん", "でびるコネクション"),
        "debil connection",
        "deviru konenku",
    ]

    logger.info(f"Searching for game: {game_name}")
    logger.info(f"Searching in paths: {search_paths}")

    result = [None]  # Thread-safe container

    def search():
        for base in search_paths:
            common_dir = os.path.join(base, "common")
            logger.info(f"Checking directory: {common_dir}")
            if not os.path.isdir(common_dir):
                logger.info(f"  -> common directory does not exist")
                continue

            try:
                entries = os.listdir(common_dir)
                logger.info(f"  -> Found {len(entries)} entries in common")
                for entry in entries:
                    entry_lower = entry.lower()
                    logger.info(f"  -> Checking: {entry}")
                    for var in variations:
                        if var in entry_lower or entry_lower in var:
                            game_path = os.path.join(common_dir, entry)
                            logger.info(f"Found game match: '{entry}' (looking for '{var}') at {game_path}")
                            result[0] = game_path
                            return
            except (PermissionError, OSError) as e:
                logger.warning(f"Cannot access {common_dir}: {e}")
                continue

    # 使用线程执行搜索（带超时）
    search_thread = threading.Thread(target=search, daemon=True)
    search_thread.start()
    search_thread.join(timeout=timeout)

    if result[0] is None:
        logger.warning(f"Game '{game_name}' not found in Steam libraries (timeout={timeout}s)")

    return result[0]


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
        return f"{game_name}.app"
    else:
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
        return os.path.join(game_path, "Contents", "Resources")
    else:
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
