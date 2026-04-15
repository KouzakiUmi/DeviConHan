"""
ASAR 工具模块

提供与 ASAR 文件操作相关的辅助函数，例如从包内计算哈希。
与 electron/asar 官方格式兼容：8字节头部 + JSON header + 文件数据
"""

import hashlib
import json
import logging
import os
import struct

from utils.constants import ASAR_MAGIC_NUMBER

logger = logging.getLogger(__name__)

HEADER_SIZE_BYTES = 8
MAX_HEADER_SIZE = 50 * 1024 * 1024


def _read_header_from_asar(asar_path: str) -> tuple:
    """
    从 ASAR 文件读取头部信息，支持两种格式：
    - 官方 8 字节格式: [4字节 header_size][4字节 padding][JSON][文件数据]
    - 旧 16 字节格式: [4字节 data_size][4字节 header_size][4字节 header_object_size][4字节 header_string_size][JSON][文件数据]

    Args:
        asar_path: ASAR 文件路径

    Returns:
        tuple: (header_dict, json_size, base_offset)
            - header_dict: 解析后的 JSON 头字典
            - json_size: JSON 数据大小
            - base_offset: 文件数据起始偏移量
            失败返回 (None, None, None)
    """
    if not os.path.exists(asar_path):
        return None, None, None

    try:
        with open(asar_path, "rb") as f:
            header_buf = f.read(16)
            if len(header_buf) < 8:
                logger.error(f"Failed to read ASAR header from {asar_path}")
                return None, None, None

            header_size_8byte = struct.unpack("<I", header_buf[0:4])[0]
            padding = struct.unpack("<I", header_buf[4:8])[0]

            if header_size_8byte > 0 and header_size_8byte <= MAX_HEADER_SIZE and padding == 0:
                is_8byte_format = True
            elif header_size_8byte > MAX_HEADER_SIZE:
                is_8byte_format = False
            else:
                is_8byte_format = False

            if is_8byte_format:
                json_size = header_size_8byte
                base_offset = 8 + header_size_8byte
            else:
                if len(header_buf) < 16:
                    logger.error(f"File too small for 16-byte format header: {asar_path}")
                    return None, None, None
                header_object_size = struct.unpack("<I", header_buf[8:12])[0]
                json_size = struct.unpack("<I", header_buf[12:16])[0]
                base_offset = 16 + header_object_size

            if json_size == 0 or json_size > MAX_HEADER_SIZE:
                logger.error(f"Invalid ASAR JSON size: {json_size}")
                return None, None, None

            json_start = 8 if is_8byte_format else 16
            header_bytes = header_buf[json_start : json_start + json_size]
            if len(header_bytes) < json_size:
                with open(asar_path, "rb") as f:
                    f.seek(json_start)
                    header_bytes = f.read(json_size)
                    if len(header_bytes) != json_size:
                        logger.error(f"Failed to read ASAR header data from {asar_path}")
                        return None, None, None

            json_str = header_bytes.decode("utf-8")
            header_dict = json.loads(json_str)

            return header_dict, json_size, base_offset

    except Exception as e:
        logger.error(f"Failed to read ASAR header from {asar_path}: {e}")
        return None, None, None


def check_asar_path_traversal(asar_path: str) -> bool:
    """
    Check if the ASAR file contains any paths that could lead to path traversal
    (e.g., absolute paths, or paths containing '../').

    Args:
        asar_path: Path to the ASAR file

    Returns:
        bool: True if safe (no traversal found), False if potentially malicious
    """
    header_dict, _, _ = _read_header_from_asar(asar_path)
    if header_dict is None:
        return False

    def check_node(node):
        if "files" in node:
            for name, child in node["files"].items():
                if ".." in name or name.startswith("/") or name.startswith("\\") or ":" in name:
                    logger.error(f"Path traversal detected in ASAR: {name}")
                    return False
                if not check_node(child):
                    return False
        return True

    return check_node(header_dict)


def get_file_hash_in_asar(asar_path, file_path):
    """
    计算 ASAR 包内特定文件的 SHA256 哈希值
    纯 Python 内存实现，不依赖外部命令行调用，速度快且不产生临时文件。

    Args:
        asar_path: ASAR 文件路径
        file_path: ASAR 内的相对路径

    Returns:
        str: 文件的 SHA256 哈希值，失败返回 None
    """
    header_dict, json_size, base_offset = _read_header_from_asar(asar_path)
    if header_dict is None:
        return None

    path_parts = [p for p in file_path.replace("\\", "/").split("/") if p]

    node = header_dict
    for part in path_parts:
        if "files" in node and part in node["files"]:
            node = node["files"][part]
        else:
            return None

    if "offset" not in node or "size" not in node:
        return None

    if "integrity" in node and node["integrity"].get("algorithm") == "SHA256":
        return node["integrity"].get("hash")

    offset = int(node["offset"])
    size = node["size"]

    try:
        with open(asar_path, "rb") as f:
            f.seek(base_offset + offset)

            dynamic_chunk = min(max(65536, size // 1000), 4 * 1024 * 1024)

            sha256_hash = hashlib.sha256()
            bytes_read = 0

            while bytes_read < size:
                chunk_size = min(dynamic_chunk, size - bytes_read)
                chunk = f.read(chunk_size)
                if not chunk:
                    break
                sha256_hash.update(chunk)
                bytes_read += len(chunk)

            return sha256_hash.hexdigest()

    except Exception as e:
        logger.debug(f"Error parsing ASAR file {asar_path} for {file_path}: {e}")
        return None
