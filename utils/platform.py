"""
跨平台检测模块

提供跨平台的 Steam 游戏路径检测和平台信息获取。
通过扫描 Steam 的 appmanifest_*.acf 文件定位游戏，
支持按 App ID 精确匹配和按名称模糊匹配。
"""

import logging
import os
import platform
import re
import string
import sys
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import TimeoutError as FuturesTimeoutError
from dataclasses import dataclass
from functools import lru_cache
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class PlatformInfo:
    """平台信息"""

    system: str  # 'windows', 'darwin', 'linux'
    arch: str  # 'x86_64', 'arm64', etc.
    steam_common_path: str  # Primary Steam installation path


@dataclass
class SteamAppInfo:
    """Steam 应用信息（从 ACF 清单文件解析）"""

    appid: str
    name: str
    install_dir: str
    steamapps_path: str

    @property
    def full_path(self) -> str:
        return os.path.join(self.steamapps_path, "common", self.install_dir)


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
            os.path.expanduser("~/Library/Application Support"), "Steam", "steamapps", "common"
        )
    elif system.startswith("linux"):
        system_name = "linux"
        steam_path = os.path.join(os.path.expanduser("~/.steam/steam"), "steamapps", "common")
    else:
        system_name = "unknown"
        steam_path = ""

    return PlatformInfo(
        system=system_name, arch=platform.machine().lower(), steam_common_path=steam_path
    )


@lru_cache(maxsize=1)
def _find_steam_path_windows() -> str:
    """
    在 Windows 上查找 Steam 安装路径

    Returns:
        str: Steam common 路径，找不到返回默认路径
    """
    default_path = os.path.join(
        os.environ.get("ProgramFiles", "C:\\Program Files"), "Steam", "steamapps", "common"
    )

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


def _get_steam_install_path() -> Optional[str]:
    """
    获取 Steam 安装根目录（包含 steamapps 的上级目录）

    在 Windows 上通过注册表查找，在 Linux/WSL 上扫描挂载的 Windows 驱动器。

    Returns:
        str: Steam 安装目录路径，找不到返回 None
    """
    info = get_platform_info()

    if info.system == "windows":
        common = info.steam_common_path
        if os.path.isdir(common):
            return os.path.dirname(os.path.dirname(common))

        for candidate in [
            os.path.join(os.environ.get("ProgramFiles", "C:\\Program Files"), "Steam"),
            os.path.join(os.environ.get("ProgramFiles(x86)", "C:\\Program Files (x86)"), "Steam"),
        ]:
            if os.path.isdir(candidate):
                return candidate

        for drive in ["C:\\", "D:\\", "E:\\", "F:\\"]:
            steam_dir = os.path.join(drive, "Steam")
            if os.path.isdir(steam_dir):
                return steam_dir
            try:
                for entry in os.listdir(drive):
                    entry_lower = entry.lower()
                    if "steam" in entry_lower and os.path.isdir(os.path.join(drive, entry)):
                        return os.path.join(drive, entry)
            except (PermissionError, OSError):
                pass

    elif info.system == "darwin":
        candidate = os.path.expanduser("~/Library/Application Support/Steam")
        if os.path.isdir(candidate):
            return candidate

    elif info.system == "linux":
        home = os.path.expanduser("~")
        for candidate in [
            os.path.join(home, ".steam", "steam"),
            os.path.join(home, ".local", "share", "Steam"),
        ]:
            if os.path.isdir(candidate):
                return candidate

    return None


def get_steam_library_paths() -> List[str]:
    """
    获取所有 Steam 库目录（支持多库配置）

    Returns:
        List[str]: Steam steamapps 目录路径列表
    """
    info = get_platform_info()
    paths = []

    steam_install = _get_steam_install_path()
    if not steam_install:
        logger.info("Steam installation not found")
        return paths

    main_steamapps = os.path.join(steam_install, "steamapps")
    if os.path.isdir(main_steamapps):
        paths.append(main_steamapps)
        logger.info(f"Primary Steam library: {main_steamapps}")

    library_folders_vdf = os.path.join(main_steamapps, "libraryfolders.vdf")
    if os.path.isfile(library_folders_vdf):
        try:
            with open(library_folders_vdf, encoding="utf-8", errors="ignore") as f:
                content = f.read()
            for line in content.split("\n"):
                line = line.strip()
                if '"path"' in line.lower():
                    match = re.search(r'"path"\s*"([^"]+)"', line, re.IGNORECASE)
                    if match:
                        lib_path = os.path.normpath(match.group(1))
                        lib_steamapps = os.path.join(lib_path, "steamapps")
                        if os.path.isdir(lib_steamapps) and lib_steamapps not in paths:
                            paths.append(lib_steamapps)
                            logger.info(f"Found Steam library from config: {lib_steamapps}")
        except Exception as e:
            logger.debug(f"Failed to parse libraryfolders.vdf: {e}")

    if info.system == "windows":
        for drive_letter in string.ascii_uppercase:
            base = f"{drive_letter}:\\"
            if not os.path.isdir(base):
                continue
            try:
                for entry in os.listdir(base):
                    if "steamlibrary" in entry.lower():
                        lib_steamapps = os.path.join(base, entry, "steamapps")
                        if os.path.isdir(lib_steamapps) and lib_steamapps not in paths:
                            paths.append(lib_steamapps)
                            logger.info(f"Found Steam library: {lib_steamapps}")
            except (PermissionError, OSError):
                pass

    seen = set()
    unique_paths = []
    for p in paths:
        normalized = os.path.normpath(p)
        if normalized not in seen and os.path.isdir(p):
            seen.add(normalized)
            unique_paths.append(p)

    logger.info(f"Total Steam library paths found: {len(unique_paths)}")
    return unique_paths


def _parse_acf_manifest(filepath: str) -> Optional[Dict[str, str]]:
    """
    解析 Steam ACF 清单文件

    Args:
        filepath: ACF 文件路径

    Returns:
        包含 appid, name, installdir 的字典，解析失败返回 None
    """
    try:
        with open(filepath, encoding="utf-8", errors="ignore") as f:
            content = f.read()

        result = {}

        appid_m = re.search(r'"appid"\s+"(\d+)"', content)
        if appid_m:
            result["appid"] = appid_m.group(1)

        name_m = re.search(r'"name"\s+"([^"]*)"', content)
        if name_m:
            result["name"] = name_m.group(1)

        installdir_m = re.search(r'"installdir"\s+"([^"]*)"', content)
        if installdir_m:
            result["installdir"] = installdir_m.group(1)

        if "appid" in result and "installdir" in result:
            return result

    except Exception as e:
        logger.debug(f"Failed to parse ACF manifest {filepath}: {e}")

    return None


def scan_steam_apps(steamapps_dirs: Optional[List[str]] = None) -> List[SteamAppInfo]:
    """
    扫描所有 Steam 库中的已安装应用

    Returns:
        List[SteamAppInfo]: 所有已安装应用的列表
    """
    apps = []
    if steamapps_dirs is None:
        steamapps_dirs = get_steam_library_paths()

    for steamapps_dir in steamapps_dirs:
        try:
            for entry in os.listdir(steamapps_dir):
                if not entry.startswith("appmanifest_") or not entry.endswith(".acf"):
                    continue

                filepath = os.path.join(steamapps_dir, entry)
                manifest = _parse_acf_manifest(filepath)
                if manifest:
                    apps.append(
                        SteamAppInfo(
                            appid=manifest["appid"],
                            name=manifest.get("name", manifest["installdir"]),
                            install_dir=manifest["installdir"],
                            steamapps_path=steamapps_dir,
                        )
                    )
        except (PermissionError, OSError) as e:
            logger.debug(f"Cannot scan {steamapps_dir}: {e}")

    return apps


def find_game_by_appid(appid: str, steamapps_dirs: Optional[List[str]] = None) -> Optional[str]:
    """
    通过 Steam App ID 精确查找游戏安装路径

    Args:
        appid: Steam 应用 ID（如 "3054820"）

    Returns:
        str: 游戏安装路径，未找到返回 None
    """
    if steamapps_dirs is None:
        steamapps_dirs = get_steam_library_paths()

    for steamapps_dir in steamapps_dirs:
        manifest_path = os.path.join(steamapps_dir, f"appmanifest_{appid}.acf")
        if os.path.isfile(manifest_path):
            manifest = _parse_acf_manifest(manifest_path)
            if manifest and "installdir" in manifest:
                game_path = os.path.join(steamapps_dir, "common", manifest["installdir"])
                if os.path.isdir(game_path):
                    logger.info(f"Found game by AppID {appid}: {game_path}")
                    return game_path

    logger.info(f"Game with AppID {appid} not found in Steam libraries")
    return None


def find_game_in_steam(
    game_id: str,
    search_paths: Optional[List[str]] = None,
    timeout: float = 10.0,
    extra_variations: Optional[List[str]] = None,
) -> Optional[str]:
    """
    在 Steam 目录中查找游戏

    优先使用 AppID 精确匹配，失败后回退到名称模糊匹配。

    Args:
        game_id: 游戏标识 — 如果全是数字则按 AppID 匹配，否则按名称匹配
        search_paths: 可选的 steamapps 路径列表
        timeout: 搜索超时（秒），名称匹配模式下的线程超时
        extra_variations: 额外的名称变体列表（如罗马音、简写等）

    Returns:
        str: 游戏目录路径，未找到返回 None
    """
    if search_paths is None:
        search_paths = get_steam_library_paths()

    if not search_paths:
        logger.warning("No Steam library paths found")
        return None

    # 策略 1: 如果 game_id 是纯数字，优先按 AppID 精确匹配
    stripped_id = game_id.strip()
    if stripped_id.isdigit():
        result = find_game_by_appid(stripped_id, search_paths)
        if result:
            return result
        logger.info(f"AppID {stripped_id} not found, falling back to name search")

    # 策略 2: 扫描所有清单文件，按名称模糊匹配
    logger.info(f"Searching for game by name: {game_id}")
    normalized_name = _normalize_japanese(stripped_id)

    variations = [
        normalized_name,
        normalized_name.replace(" ", "_"),
        normalized_name.replace(" ", "-"),
        normalized_name.replace("_", " "),
        normalized_name.replace("-", " "),
    ]

    if extra_variations:
        variations.extend([_normalize_japanese(v) for v in extra_variations if v.strip()])

    apps = scan_steam_apps(search_paths)
    for app in apps:
        app_name_normalized = _normalize_japanese(app.name)
        app_dir_normalized = _normalize_japanese(app.install_dir)

        for var in variations:
            if app_name_normalized == var or app_dir_normalized == var:
                if os.path.isdir(app.full_path):
                    logger.info(
                        f"Found game by name match: '{app.name}' "
                        f"(dir='{app.install_dir}') at {app.full_path}"
                    )
                    return app.full_path

    # 策略 3: 子字符串匹配（最宽松，仅在前两种策略都失败时使用）
    for app in apps:
        app_name_lower = _normalize_japanese(app.name).lower()
        app_dir_lower = _normalize_japanese(app.install_dir).lower()

        for var in variations:
            var_lower = var.lower()
            if var_lower in app_name_lower or var_lower in app_dir_lower:
                if os.path.isdir(app.full_path):
                    logger.info(
                        f"Found game by substring match: '{app.name}' "
                        f"(dir='{app.install_dir}') at {app.full_path}"
                    )
                    return app.full_path

    # 策略 4: 回退到旧的目录名扫描（适用于非 Steam 安装或清单缺失）
    logger.info("Manifest scan failed, falling back to directory name scan")
    return _find_game_by_directory_scan(variations, search_paths, timeout)


def _find_game_by_directory_scan(
    variations: List[str],
    search_paths: List[str],
    timeout: float,
) -> Optional[str]:
    """
    回退：通过目录名扫描查找游戏（旧方法）

    Args:
        variations: 规范化名称变体列表
        search_paths: steamapps 路径列表
        timeout: 超时时间

    Returns:
        str: 游戏目录路径，未找到返回 None
    """
    def search():
        for base in search_paths:
            common_dir = os.path.join(base, "common")
            if not os.path.isdir(common_dir):
                continue

            try:
                for entry in os.listdir(common_dir):
                    entry_normalized = _normalize_japanese(entry)
                    for var in variations:
                        if entry_normalized == var:
                            game_path = os.path.join(common_dir, entry)
                            logger.info(f"Found game by directory scan: '{entry}' at {game_path}")
                            return game_path
            except (PermissionError, OSError) as e:
                logger.warning(f"Cannot access {common_dir}: {e}")

        return None

    try:
        with ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(search)
            result = future.result(timeout=timeout)
    except FuturesTimeoutError:
        logger.warning("Directory scan timed out")
        result = None
    except Exception as e:
        logger.warning(f"Directory scan failed: {e}")
        result = None

    if result is None:
        logger.warning("Game not found by any method")

    return result




def _normalize_japanese(s: str) -> str:
    """
    归一化日文：平假名转片假名，统一大小写
    """
    result = []
    for c in s:
        if "\u3040" <= c <= "\u309f":
            result.append(chr(ord(c) + 0x60))
        else:
            result.append(c.lower())
    return "".join(result)


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
    elif system == "windows":
        return f"{game_name}.exe"
    else:
        return game_name


def get_resources_path(game_path: str, system: Optional[str] = None) -> str:
    """
    获取游戏的 resources 目录路径

    自动处理 macOS app bundle（路径以 .app 结尾的目录）。
    """
    if is_app_bundle(game_path):
        return os.path.join(game_path, "Contents", "Resources")

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
    """
    resources = get_resources_path(game_path, system)
    return os.path.join(resources, asar_name)


def is_app_bundle(path: str) -> bool:
    """检查路径是否是 macOS app bundle"""
    return path.endswith(".app") and os.path.isdir(path)


def get_bundle_executable_path(app_bundle_path: str) -> str:
    """
    获取 macOS app bundle 中的可执行文件路径
    """
    return os.path.join(app_bundle_path, "Contents", "MacOS", "main")
