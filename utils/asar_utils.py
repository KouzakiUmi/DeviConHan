"""
ASAR 工具模块

提供与 ASAR 文件操作相关的辅助函数，例如从包内计算哈希。
支持现代 Pickle ASAR 头部以及历史遗留布局。
"""

import hashlib
import json
import logging
import os
import struct
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

from utils.constants import MAX_ASAR_SIZE, MIN_ASAR_SIZE

logger = logging.getLogger(__name__)

__all__ = [
    "parse_asar_header",
    "validate_asar_with_reason",
    "validate_asar_comprehensive",
    "open_asar_reader",
    "is_valid_asar",
    "check_asar_path_traversal",
    "get_file_hashes_in_asar",
    "get_file_hash_in_asar",
]

HEADER_SIZE_BYTES = 8
MAX_HEADER_SIZE = 50 * 1024 * 1024


@dataclass(frozen=True)
class AsarHeaderInfo:
    """解析后的 ASAR 头部信息"""

    header_dict: dict
    json_size: int
    base_offset: int
    format_name: str


@dataclass(frozen=True)
class AsarReader:
    """复用同一份 header 信息与文件元数据的 ASAR 读取器"""

    asar_path: str
    header_info: AsarHeaderInfo
    file_size: int


def _parse_pickle_header(f: Any) -> Optional[AsarHeaderInfo]:
    """解析 @electron/asar 当前 Pickle 头部格式"""
    f.seek(0)
    size_buf = f.read(8)
    if len(size_buf) < 8:
        return None

    size_payload_size, header_buf_len = struct.unpack("<II", size_buf)
    if size_payload_size != 4 or header_buf_len < 8 or header_buf_len > MAX_HEADER_SIZE:
        return None

    header_buf = f.read(header_buf_len)
    if len(header_buf) != header_buf_len:
        return None

    payload_size, json_size = struct.unpack("<II", header_buf[:8])
    if (
        payload_size < 4
        or payload_size > header_buf_len
        or json_size <= 0
        or json_size > MAX_HEADER_SIZE
    ):
        return None

    json_end = 8 + json_size
    if json_end > header_buf_len:
        return None

    header_dict = json.loads(header_buf[8:json_end].decode("utf-8"))
    if "files" not in header_dict:
        return None

    return AsarHeaderInfo(
        header_dict=header_dict,
        json_size=json_size,
        base_offset=8 + header_buf_len,
        format_name="modern_pickle",
    )


def _parse_legacy_8_header(f: Any) -> Optional[AsarHeaderInfo]:
    """解析旧 8 字节头部格式 [json_size][padding]"""
    f.seek(0)
    header_buf = f.read(8)
    if len(header_buf) < 8:
        return None

    json_size, padding = struct.unpack("<II", header_buf)
    if json_size <= 0 or json_size > MAX_HEADER_SIZE or padding != 0:
        return None

    header_bytes = f.read(json_size)
    if len(header_bytes) != json_size:
        return None

    header_dict = json.loads(header_bytes.decode("utf-8"))
    if "files" not in header_dict:
        return None

    return AsarHeaderInfo(
        header_dict=header_dict,
        json_size=json_size,
        base_offset=8 + json_size,
        format_name="legacy_8",
    )


def _parse_legacy_16_header(f: Any) -> Optional[AsarHeaderInfo]:
    """解析旧 16 字节头部格式"""
    f.seek(0)
    header_buf = f.read(16)
    if len(header_buf) < 16:
        return None

    _data_size, header_size, header_object_size, json_size = struct.unpack("<IIII", header_buf)
    if (
        header_size <= 0
        or header_object_size <= 0
        or json_size <= 0
        or header_size > MAX_HEADER_SIZE
        or header_object_size > MAX_HEADER_SIZE
        or json_size > MAX_HEADER_SIZE
        or header_object_size < json_size
    ):
        return None

    header_bytes = f.read(json_size)
    if len(header_bytes) != json_size:
        return None

    header_dict = json.loads(header_bytes.decode("utf-8"))
    if "files" not in header_dict:
        return None

    return AsarHeaderInfo(
        header_dict=header_dict,
        json_size=json_size,
        base_offset=16 + header_object_size,
        format_name="legacy_16",
    )


def parse_asar_header(asar_path: str) -> Optional[AsarHeaderInfo]:
    """
    解析 ASAR 头部，按已知格式依次尝试。

    优先现代 Pickle 格式，再回退旧格式，避免把 Pickle 文件误判为旧 16 字节格式。
    """
    if not os.path.exists(asar_path):
        return None

    parsers = (
        _parse_pickle_header,
        _parse_legacy_8_header,
        _parse_legacy_16_header,
    )

    try:
        with open(asar_path, "rb") as f:
            for parser in parsers:
                try:
                    result = parser(f)
                except (json.JSONDecodeError, UnicodeDecodeError, struct.error, ValueError):
                    result = None

                if result is not None:
                    logger.debug(f"Detected ASAR format {result.format_name} for {asar_path}")
                    return result
    except OSError as e:
        logger.error(f"Failed to read ASAR header from {asar_path}: {e}")
        return None
    except Exception as e:
        logger.error(f"Failed to parse ASAR header from {asar_path}: {e}")
        return None

    logger.error(f"Failed to detect a supported ASAR header format for {asar_path}")
    return None


def _is_suspicious_asar_name(name: str) -> bool:
    """检查 ASAR header 键名是否可疑"""
    if not name or name in {".", ".."}:
        return True
    return (
        "/" in name
        or "\\" in name
        or name.startswith("/")
        or name.startswith("\\")
        or ":" in name
        or "\x00" in name
    )


def _resolve_link_target(link: str) -> list:
    """将链接目标路径解析为组件列表，从归档根开始解析。

    链接目标在 ASAR 中是相对于归档根目录的，这与 @electron/asar 的行为一致。
    返回解析后的路径组件列表；如果链接会逃逸到根目录外则返回 None。
    """
    if not link or link.startswith("/") or link.startswith("\\") or ":" in link or "\x00" in link:
        return None

    resolved: list = []
    for part in link.replace("\\", "/").split("/"):
        if not part or part == ".":
            continue
        if part == "..":
            if not resolved:
                return None
            resolved.pop()
        else:
            resolved.append(part)
    return resolved


def _is_safe_link_target(link: str, _current_prefix: str = "") -> bool:
    """检查 link 目标是否仍位于归档逻辑根内。

    链接目标相对于归档根目录解析（与 @electron/asar 的行为一致）。
    _current_prefix 参数保留用于向后兼容，不再使用。
    """
    return _resolve_link_target(link) is not None


def _validate_file_ranges(
    node: dict, base_offset: int, file_size: int, prefix: str = ""
) -> Tuple[bool, str]:
    """验证 header 中所有条目的路径、link 和 offset/size 是否安全"""
    if "files" not in node:
        return True, ""

    for name, child in node["files"].items():
        rel_path = f"{prefix}/{name}" if prefix else name

        if _is_suspicious_asar_name(name):
            return False, f"ASAR entry has suspicious name: {rel_path!r}"

        if "files" in child:
            ok, reason = _validate_file_ranges(child, base_offset, file_size, rel_path)
            if not ok:
                return False, reason
            continue

        if "link" in child:
            link_target = child.get("link")
            if not isinstance(link_target, str) or not _is_safe_link_target(link_target, rel_path):
                return False, f"ASAR symlink escapes archive root: {rel_path!r} -> {link_target!r}"
            continue

        if child.get("unpacked"):
            continue

        if "offset" not in child or "size" not in child:
            return False, f"ASAR entry missing offset/size: {rel_path}"

        try:
            offset = int(child["offset"])
            size = int(child["size"])
        except (TypeError, ValueError):
            return False, f"ASAR entry has invalid offset/size: {rel_path}"

        if offset < 0 or size < 0:
            return False, f"ASAR entry has negative offset/size: {rel_path}"

        data_start = base_offset + offset
        data_end = data_start + size
        if data_start < base_offset or data_end > file_size:
            return (
                False,
                f"ASAR entry points outside archive: {rel_path} "
                f"(start={data_start}, end={data_end}, file_size={file_size})",
            )

    return True, ""


def validate_asar_with_reason(asar_path: str) -> Tuple[bool, str]:
    """验证 ASAR 并返回可用于日志或 UI 的失败原因（向后兼容）"""
    if not os.path.exists(asar_path):
        return False, f"ASAR file not found: {asar_path}"

    header_info = parse_asar_header(asar_path)
    if header_info is None:
        return False, "Unsupported or unreadable ASAR header"

    try:
        file_size = os.path.getsize(asar_path)
    except OSError as e:
        return False, f"Failed to stat ASAR file: {e}"

    if header_info.base_offset > file_size:
        return (
            False,
            f"ASAR base offset exceeds file size: "
            f"base_offset={header_info.base_offset}, file_size={file_size}",
        )

    ok, reason = _validate_file_ranges(header_info.header_dict, header_info.base_offset, file_size)
    if not ok:
        return False, reason

    return True, ""


def open_asar_reader(asar_path: str) -> Optional[AsarReader]:
    """打开一个可复用的 ASAR 读取器"""
    ok, reason = validate_asar_with_reason(asar_path)
    if not ok:
        logger.error(f"ASAR validation failed for {asar_path}: {reason}")
        return None

    header_info = parse_asar_header(asar_path)
    if header_info is None:
        return None

    try:
        file_size = os.path.getsize(asar_path)
    except OSError:
        return None

    return AsarReader(asar_path=asar_path, header_info=header_info, file_size=file_size)


def validate_asar_comprehensive(
    asar_path: str,
    check_min_size: bool = True,
    check_max_size: bool = True,
    min_size: int = MIN_ASAR_SIZE,
    max_size: int = MAX_ASAR_SIZE,
    enable_performance_monitor: bool = False,
) -> tuple[bool, str, dict]:
    """
    统一的 ASAR 文件验证函数

    整合文件存在性检查、大小范围检查和 ASAR 结构验证，
    提供可选的性能监控能力。

    Args:
        asar_path: ASAR 文件路径
        check_min_size: 是否检查最小文件大小
        check_max_size: 是否检查最大文件大小
        min_size: 最小文件大小阈值
        max_size: 最大文件大小阈值
        enable_performance_monitor: 是否启用性能监控

    Returns:
        tuple[bool, str, dict]:
            - 是否验证通过
            - 失败原因（成功时为空字符串）
            - 额外信息字典（包含 file_size、validation_time 等）
    """
    extra_info = {}

    if enable_performance_monitor:
        from utils.performance import get_performance_monitor
        monitor = get_performance_monitor()
        monitor.start("validate_asar_comprehensive")

    try:
        if not os.path.exists(asar_path):
            return False, f"ASAR file not found: {asar_path}", extra_info

        file_size = os.path.getsize(asar_path)
        extra_info["file_size"] = file_size

        if check_min_size and file_size < min_size:
            return False, f"ASAR file too small: {file_size} bytes (min: {min_size})", extra_info

        if check_max_size and file_size > max_size:
            return False, f"ASAR file too large: {file_size} bytes (max: {max_size})", extra_info

        valid, reason = validate_asar_with_reason(asar_path)
        if not valid:
            return False, reason, extra_info

        return True, "", extra_info

    except OSError as e:
        return False, f"Failed to read ASAR file: {e}", extra_info
    except Exception as e:
        return False, f"ASAR validation failed: {e}", extra_info
    finally:
        if enable_performance_monitor:
            elapsed = monitor.stop("validate_asar_comprehensive")
            extra_info["validation_time"] = elapsed
            logger.debug(f"ASAR validation took {elapsed:.3f}s")


def is_valid_asar(asar_path: str) -> bool:
    """检查 ASAR 结构是否可解析，且所有已打包文件范围都在归档内"""
    valid, _, _ = validate_asar_comprehensive(
        asar_path,
        check_min_size=False,
        check_max_size=False,
        enable_performance_monitor=False,
    )
    return valid


def _read_header_from_asar(asar_path: str) -> tuple:
    """
    从 ASAR 文件读取头部信息。

    兼容格式：
    - modern_pickle: [sizePickle 8B][headerPickle NB][file data...]
    - legacy_8:      [json_size][padding][json][file data...]
    - legacy_16:     [data_size][header_size][header_object_size][json_size][json][file data...]

    Args:
        asar_path: ASAR 文件路径

    Returns:
        tuple: (header_dict, json_size, base_offset)
            - header_dict: 解析后的 JSON 头字典
            - json_size: JSON 数据大小
            - base_offset: 文件数据起始偏移量
            失败返回 (None, None, None)
    """
    reader = open_asar_reader(asar_path)
    if reader is None:
        return None, None, None
    return (
        reader.header_info.header_dict,
        reader.header_info.json_size,
        reader.header_info.base_offset,
    )


def check_asar_path_traversal(asar_path: str) -> bool:
    """
    Check if the ASAR file contains any paths that could lead to path traversal
    (e.g., absolute paths, or paths containing '../').
    Also validates symlink targets to ensure they don't escape the archive root.

    Args:
        asar_path: Path to the ASAR file

    Returns:
        bool: True if safe (no traversal found), False if potentially malicious
    """
    header_dict, _, _ = _read_header_from_asar(asar_path)
    if header_dict is None:
        return False

    def check_node(node: Dict[str, Any]) -> bool:
        if "files" in node:
            for name, child in node["files"].items():
                if ".." in name or name.startswith("/") or name.startswith("\\") or ":" in name:
                    logger.error(f"Path traversal detected in ASAR entry name: {name}")
                    return False
                if "link" in child:
                    link_target = child.get("link")
                    if not isinstance(link_target, str) or _resolve_link_target(link_target) is None:
                        logger.error(
                            f"Path traversal detected in ASAR symlink target: "
                            f"{name!r} -> {link_target!r}"
                        )
                        return False
                if not check_node(child):
                    return False
        return True

    return check_node(header_dict) if header_dict else False


def _resolve_node(header_dict: Dict[str, Any], file_path: str) -> Optional[Dict[str, Any]]:
    """在 header 树中定位目标文件节点"""
    path_parts = [p for p in file_path.replace("\\", "/").split("/") if p]

    node = header_dict
    for part in path_parts:
        if "files" in node and part in node["files"]:
            node = node["files"][part]
        else:
            return None

    return node


def _compute_node_hash(asar_file: Any, base_offset: int, node: Dict[str, Any]) -> Optional[str]:
    """对单个 ASAR 文件节点计算哈希"""
    if "offset" not in node or "size" not in node:
        return None

    if "integrity" in node and node["integrity"].get("algorithm") == "SHA256":
        return node["integrity"].get("hash")

    offset = int(node["offset"])
    size = node["size"]

    asar_file.seek(base_offset + offset)

    dynamic_chunk = min(max(65536, size // 1000), 4 * 1024 * 1024)

    sha256_hash = hashlib.sha256()
    bytes_read = 0
    max_iterations = max(size // 1024, 1_000_000)
    iteration_count = 0

    while bytes_read < size:
        iteration_count += 1
        if iteration_count > max_iterations:
            logger.error(f"Hash computation exceeded max iterations ({max_iterations})")
            return None
        chunk_size = min(dynamic_chunk, size - bytes_read)
        chunk = asar_file.read(chunk_size)
        if not chunk:
            break
        sha256_hash.update(chunk)
        bytes_read += len(chunk)

    return sha256_hash.hexdigest()


def get_file_hashes_in_asar(asar_path: str, file_paths: List[str]) -> Dict[str, Optional[str]]:
    """
    一次性读取多个 ASAR 内文件的 SHA256 哈希值，避免重复解析 header 和重复打开文件。
    """
    reader = open_asar_reader(asar_path)
    if reader is None:
        return dict.fromkeys(file_paths, None)

    results: Dict[str, Optional[str]] = {}
    try:
        with open(asar_path, "rb") as f:
            for file_path in file_paths:
                node = _resolve_node(reader.header_info.header_dict, file_path)
                if node is None:
                    results[file_path] = None
                    continue
                results[file_path] = _compute_node_hash(f, reader.header_info.base_offset, node)
    except OSError as e:
        logger.debug(f"OS error reading ASAR file {asar_path}: {e}")
        return dict.fromkeys(file_paths, None)
    except Exception as e:
        logger.debug(f"Error parsing ASAR file {asar_path}: {e}")
        return dict.fromkeys(file_paths, None)

    return results


def get_file_hash_in_asar(asar_path: str, file_path: str) -> Optional[str]:
    """
    计算 ASAR 包内特定文件的 SHA256 哈希值
    纯 Python 内存实现，不依赖外部命令行调用，速度快且不产生临时文件。

    Args:
        asar_path: ASAR 文件路径
        file_path: ASAR 内的相对路径

    Returns:
        str: 文件的 SHA256 哈希值，失败返回 None
    """
    reader = open_asar_reader(asar_path)
    if reader is None:
        return None

    node = _resolve_node(reader.header_info.header_dict, file_path)
    if node is None:
        return None

    try:
        with open(asar_path, "rb") as f:
            return _compute_node_hash(f, reader.header_info.base_offset, node)
    except OSError as e:
        logger.debug(f"OS error reading ASAR file {asar_path} for {file_path}: {e}")
        return None
    except Exception as e:
        logger.debug(f"Error parsing ASAR file {asar_path} for {file_path}: {e}")
        return None
