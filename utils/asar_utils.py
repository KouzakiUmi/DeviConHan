# -*- coding: utf-8 -*-
"""
ASAR 工具模块

提供与 ASAR 文件操作相关的辅助函数，例如从包内计算哈希。
"""

import os
import json
import struct
import hashlib
import logging
from utils.constants import ASAR_MAGIC_NUMBER, HASH_CHUNK_SIZE

logger = logging.getLogger(__name__)


def get_file_hash_in_asar(_core, asar_path, file_path):
    """
    计算 ASAR 包内特定文件的 SHA256 哈希值
    纯 Python 内存实现，不依赖外部命令行调用，速度快且不产生临时文件。

    Args:
        _core: CoreLogic 实例 (保留以保持接口兼容，实际未被使用)
        asar_path: ASAR 文件路径
        file_path: ASAR 内的相对路径

    Returns:
        str: 文件的 SHA256 哈希值，失败返回 None
    """
    if not os.path.exists(asar_path):
        return None

    try:
        with open(asar_path, "rb") as f:
            # 4 bytes for magic number
            magic = f.read(4)
            if magic != ASAR_MAGIC_NUMBER:
                return None

            header_size_bytes = f.read(4)
            if len(header_size_bytes) != 4:
                return None
            header_size = struct.unpack("<I", header_size_bytes)[0]

            # Read the rest of the header
            header_data = f.read(header_size)
            if len(header_data) != header_size:
                return None

            # Bug F 修复：原代码直接对 header_data[4:8] 执行 struct.unpack，
            # 若 header_data 不足 8 字节（截断/损坏的 ASAR），
            # struct.unpack 会静默收到空字节串并抛出 struct.error，
            # 被最外层 except 静默吞掉，难以调试。
            # 修复：显式检查 header_data 最小长度并记录具体原因。
            if len(header_data) < 8:
                logger.debug(
                    f"ASAR header_data too short ({len(header_data)} bytes) "
                    f"in {asar_path}"
                )
                return None

            # The next two uint32s are sizes
            json_size = struct.unpack("<I", header_data[4:8])[0]

            # 验证 json_size 合理性，防止因损坏数据导致超大内存分配
            if json_size == 0 or (8 + json_size) > len(header_data):
                logger.debug(
                    f"ASAR json_size {json_size} out of bounds "
                    f"(header_data={len(header_data)}) in {asar_path}"
                )
                return None

            # The JSON string
            json_str = header_data[8 : 8 + json_size].decode("utf-8")
            header_dict = json.loads(json_str)

            # base offset is where the file data begins
            base_offset = 8 + header_size

            # Normalize path
            path_parts = [p for p in file_path.replace("\\", "/").split("/") if p]

            # Find node
            node = header_dict
            for part in path_parts:
                if "files" in node and part in node["files"]:
                    node = node["files"][part]
                else:
                    return None  # File not found

            # Check if it's a file
            if "offset" not in node or "size" not in node:
                return None

            # We can use the pre-calculated hash if it exists
            if "integrity" in node and node["integrity"].get("algorithm") == "SHA256":
                return node["integrity"].get("hash")

            # Otherwise, read the file and compute hash
            offset = int(node["offset"])
            size = node["size"]

            f.seek(base_offset + offset)

            # 动态调整分块以提高大文件处理效率
            dynamic_chunk = min(max(65536, size // 1000), 4 * 1024 * 1024)

            # Read in chunks to avoid memory issues with large files
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
