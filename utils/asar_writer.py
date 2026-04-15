"""
纯 Python ASAR 归档读写模块

严格对照 @electron/asar 官方实现：
  https://github.com/electron/asar/blob/main/src/disk.ts
  https://github.com/electron/asar/blob/main/src/pickle.ts

Pickle 格式（disk.ts: createFilesystemWriteStream）：
  headerPickle = Pickle.writeString(JSON)
    → [4B: payload_size = align(4+json_bytes, 4)]
      [4B: json_byte_length]
      [json bytes]
      [padding to align(4+json_bytes,4)-4 bytes]
  sizePickle = Pickle.writeUInt32(headerBuf.length)
    → [4B: payload_size = 4]
      [4B: headerBuf.length]

  File layout:
    [sizePickle 8 bytes] [headerPickle N bytes] [packed file data...]

  base_offset (disk.ts: readFileSync):
    8 + filesystem.getHeaderSize()
    = 8 + bytes[4:8]   ← sizePickle payload = headerBuf.length
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import shutil
import struct
from pathlib import Path

logger = logging.getLogger(__name__)

DATA_SIZE = 4
BLOCK_SIZE = 4 * 1024 * 1024
ALGORITHM = "SHA256"

NATIVE_EXTENSIONS: frozenset[str] = frozenset(
    {".node", ".dll", ".so", ".dylib", ".bin", ".exe", ".lib"}
)


def _align(size: int, alignment: int = DATA_SIZE) -> int:
    return (size + alignment - 1) & ~(alignment - 1)


# ---------------------------------------------------------------------------
# Pickle helpers – mirrors pickle.ts
# Pickle layout: [4B payload_size][payload bytes (aligned to 4)]
# writeUInt32(v) → payload = [4B v]           → toBuffer() = 8 bytes
# writeString(s) → payload = [4B len][s bytes] padded to 4 → toBuffer() varies
# ---------------------------------------------------------------------------


def _pickle_write_uint32(value: int) -> bytes:
    """Serialize a single uint32 as a Pickle (matches Pickle.writeUInt32)."""
    payload = struct.pack("<I", value)  # 4 bytes, already aligned
    return struct.pack("<I", len(payload)) + payload  # [payload_size=4][value]


def _pickle_write_string(s: str) -> bytes:
    """Serialize a string as a Pickle (matches Pickle.writeString).
    writeString calls writeInt(len) then writeBytes(str, len).
    writeInt uses writeBytes which aligns to SIZE_UINT32=4.
    """
    encoded = s.encode("utf-8")
    str_len = len(encoded)
    # writeInt(str_len): 4 bytes + align to 4 (already aligned)
    # writeBytes(str, str_len): str_len bytes + padding to align(str_len, 4)
    aligned_str = _align(str_len, DATA_SIZE)
    # payload = [4B str_len] + [str bytes] + [padding]
    payload_size = DATA_SIZE + aligned_str  # INT32 for length + aligned string
    payload = struct.pack("<I", str_len) + encoded + b"\x00" * (aligned_str - str_len)
    return struct.pack("<I", payload_size) + payload  # [payload_size][payload]


def _file_integrity(file_path: str) -> tuple:
    """
    计算文件的完整性哈希值和大小

    Args:
        file_path: 文件路径

    Returns:
        tuple: (完整性信息字典, 文件大小)
        - 完整性信息字典包含:
          - algorithm: 哈希算法
          - hash: 文件的整体哈希值
          - blockSize: 分块大小
          - blocks: 各块的哈希值列表
    """
    sha = hashlib.sha256()
    blocks: list = []
    size = 0
    with open(file_path, "rb") as f:
        while True:
            chunk = f.read(BLOCK_SIZE)
            if not chunk:
                break
            size += len(chunk)
            sha.update(chunk)
            blocks.append(hashlib.sha256(chunk).hexdigest())
    return {
        "algorithm": ALGORITHM,
        "hash": sha.hexdigest(),
        "blockSize": BLOCK_SIZE,
        "blocks": blocks,
    }, size


def _dir_has_native(directory: Path, unpack_extensions: frozenset[str]) -> bool:
    """
    检查目录是否包含需要解压的原生扩展文件

    Args:
        directory: 要检查的目录路径
        unpack_extensions: 需要解压的文件扩展名集合

    Returns:
        bool: 如果目录包含原生扩展文件，返回 True，否则返回 False
    """
    try:
        for entry in directory.rglob("*"):
            if entry.is_file() and entry.suffix.lower() in unpack_extensions:
                return True
    except PermissionError:
        pass
    return False


def asar_pack(
    src,
    dest,
    unpack_extensions=None,
    callback=None,
    check_cancelled=None,
    unpacked_files: set | None = None,
) -> None:
    """
    将目录打包为 ASAR 归档文件。

    文件扩展名在 *unpack_extensions* 中的文件标记为 unpacked：
    它们不存储在 ASAR 数据段内，而是复制到归档旁边的
    ``<dest>.unpacked/`` 目录中，与 Node.js asar CLI 行为一致。

    *src* 中名为 ``app.asar.unpacked`` 的目录始终跳过（它是解压残留）

    Args:
        src: 源目录路径
        dest: 目标 ASAR 文件路径
        unpack_extensions: 需要 unpack 的文件扩展名集合，
            默认为 NATIVE_EXTENSIONS（仅当 unpacked_files 未指定时使用）
        callback: 可选的进度回调 (msg)
        check_cancelled: 可选的取消检查回调
        unpacked_files: 明确的 unpacked 文件路径集合（优先于 unpack_extensions），
            路径格式为 "path/to/file.ext"
    """
    if unpack_extensions is None:
        unpack_extensions = NATIVE_EXTENSIONS

    src = Path(src)
    dest = Path(dest)

    if not src.is_dir():
        raise ValueError(f"Source directory does not exist: {src}")

    if callback:
        callback("Building ASAR header...")

    root_node = {"files": {}}
    file_entries = []

    _walk_for_pack(
        src,
        src,
        root_node["files"],
        unpack_extensions,
        file_entries,
        offset_ref=[0],
        callback=callback,
        check_cancelled=check_cancelled,
        unpacked_files=unpacked_files,
    )

    if callback:
        callback("Writing ASAR archive...")

    header_json = json.dumps(root_node, sort_keys=True, separators=(",", ":"), ensure_ascii=False)

    # 严格对照 disk.ts: createFilesystemWriteStream
    #   headerPickle = Pickle.writeString(JSON)  → _pickle_write_string
    #   sizePickle   = Pickle.writeUInt32(headerBuf.length) → _pickle_write_uint32
    #   file: [sizePickle(8B)][headerPickle(N B)][packed data...]
    #   base_offset = 8 + bytes[4:8]  (= 8 + headerBuf.length = 8 + len(headerPickle))
    header_pickle = _pickle_write_string(header_json)  # headerBuf
    size_pickle = _pickle_write_uint32(len(header_pickle))  # sizeBuf

    dest.parent.mkdir(parents=True, exist_ok=True)

    with open(dest, "wb") as f:
        f.write(size_pickle)  # 8 bytes: [4][headerBuf.length]
        f.write(header_pickle)  # [payload_size][json_len][json bytes][padding]

        for _rel_path, abs_path, is_unpacked, _fsize in file_entries:
            if is_unpacked:
                continue  # unpacked 文件不写入 ASAR 数据段
            if check_cancelled:
                check_cancelled()
            with open(abs_path, "rb") as src_file:
                while True:
                    chunk = src_file.read(BLOCK_SIZE)
                    if not chunk:
                        break
                    f.write(chunk)

    if callback:
        callback("Writing unpacked files...")

    unpacked_dir = Path(f"{dest}.unpacked")
    has_unpacked = False
    for _rel_path, abs_path, is_unpacked, _fsize in file_entries:
        if not is_unpacked:
            continue
        has_unpacked = True
        target = unpacked_dir / _rel_path
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(abs_path, target)

    if not has_unpacked and unpacked_dir.exists():
        shutil.rmtree(str(unpacked_dir), ignore_errors=True)

    if callback:
        callback("ASAR packing complete.")


def _walk_for_pack(
    current: Path,
    src_root: Path,
    header_node: dict,
    unpack_extensions: frozenset[str],
    file_entries: list,
    offset_ref: list,
    callback,
    check_cancelled,
    unpacked_files: set | None = None,
    parent_is_unpacked: bool = False,
) -> None:
    try:
        entries = sorted(current.iterdir(), key=lambda e: e.name.lower())
    except PermissionError as e:
        logger.warning(f"Permission denied: {current}: {e}")
        return

    for entry in entries:
        if check_cancelled:
            check_cancelled()

        name = entry.name

        if name == "app.asar.unpacked" and entry.is_dir():
            continue

        rel = str(entry.relative_to(src_root)).replace("\\", "/")

        if entry.is_symlink():
            try:
                target = entry.resolve().relative_to(src_root)
            except ValueError:
                raise ValueError(f"Symlink '{rel}' points outside the package") from None
            header_node[name] = {"link": str(target).replace("\\", "/")}
            if callback:
                callback(f"Linked: {rel}")

        elif entry.is_dir():
            sub_node: dict = {"files": {}}

            dir_is_unpacked = False
            if unpacked_files is not None:
                dir_is_unpacked = rel in unpacked_files
            elif _dir_has_native(entry, unpack_extensions):
                dir_is_unpacked = True

            _walk_for_pack(
                entry,
                src_root,
                sub_node["files"],
                unpack_extensions,
                file_entries,
                offset_ref,
                callback,
                check_cancelled,
                unpacked_files,
                parent_is_unpacked or dir_is_unpacked,
            )

            if dir_is_unpacked:
                sub_node["unpacked"] = True
            header_node[name] = sub_node

        elif entry.is_file():
            if parent_is_unpacked:
                should_unpack = True
            elif unpacked_files is not None:
                should_unpack = rel in unpacked_files
            else:
                should_unpack = entry.suffix.lower() in unpack_extensions
            integrity, fsize = _file_integrity(str(entry))

            entry_dict: dict = {
                "size": fsize,
                "integrity": integrity,
            }
            if should_unpack:
                entry_dict["unpacked"] = True
            else:
                entry_dict["offset"] = str(offset_ref[0])
                offset_ref[0] += fsize

            is_exec = os.name != "nt" and (entry.stat().st_mode & 0o100)
            if is_exec:
                entry_dict["executable"] = True

            header_node[name] = entry_dict
            file_entries.append((rel, str(entry), should_unpack, fsize))

            logger.debug(f"Packed: {rel}")

        else:
            logger.debug(f"Skipping special file: {rel}")


def asar_extract(
    src,
    dest,
    callback=None,
    check_cancelled=None,
):
    """
    解压 ASAR 归档文件到目录。

    对于头部中标记 ``unpacked: true`` 的文件，从归档旁边的
    ``<src>.unpacked/`` 目录中复制（与 Node.js asar 和 Electron 一致）。

    Args:
        src: ASAR 归档文件路径
        dest: 解压目标目录路径
        callback: 可选的进度回调 (msg)
        check_cancelled: 可选的取消检查回调

    Returns:
        tuple: (unpacked_files: set, base_offset: int) 记录哪些文件是 unpacked 的
    """
    src = Path(src)
    dest = Path(dest)

    if not src.is_file():
        raise FileNotFoundError(f"ASAR file not found: {src}")

    dest.mkdir(parents=True, exist_ok=True)
    unpacked_dir = Path(f"{src}.unpacked")

    with open(src, "rb") as f:
        size_buf = f.read(8)
        if len(size_buf) < 8:
            raise ValueError(f"Failed to read ASAR size pickle from {src}")

        size_payload_size = struct.unpack("<I", size_buf[0:4])[0]
        header_buf_len = struct.unpack("<I", size_buf[4:8])[0]
        if size_payload_size != 4 or header_buf_len == 0 or header_buf_len > 50 * 1024 * 1024:
            raise ValueError(
                f"Invalid ASAR size pickle: payload_size={size_payload_size}, header_buf_len={header_buf_len}"
            )

        base_offset = 8 + header_buf_len

        header_buf = f.read(header_buf_len)
        if len(header_buf) < header_buf_len:
            raise ValueError(f"Failed to read ASAR header pickle from {src}")

        json_len = struct.unpack("<I", header_buf[4:8])[0]
        if json_len == 0 or json_len > 50 * 1024 * 1024:
            raise ValueError(f"Invalid ASAR JSON size: {json_len}")

        header_bytes = header_buf[8 : 8 + json_len]
        header = json.loads(header_bytes.decode("utf-8"))

        if callback:
            callback("Extracting ASAR...")

        unpacked_files = set()
        _extract_node(
            header,
            dest,
            dest,
            f,
            base_offset,
            unpacked_dir,
            callback,
            check_cancelled,
            unpacked_files,
        )

    if callback:
        callback("ASAR extraction complete.")

    return unpacked_files, base_offset


def _collect_unpacked_files(node: dict, prefix: str = "") -> set:
    """收集 header 中所有标记为 unpacked 的文件路径"""
    unpacked = set()
    if "files" not in node:
        return unpacked
    for name, child in node["files"].items():
        rel_path = f"{prefix}/{name}" if prefix else name
        if child.get("unpacked"):
            unpacked.add(rel_path)
        if "files" in child:
            unpacked.update(_collect_unpacked_files(child, rel_path))
    return unpacked


def _extract_node(
    node: dict,
    current_dest: Path,
    root_dest: Path,
    asar_file,
    base_offset: int,
    unpacked_dir: Path,
    callback,
    check_cancelled,
    unpacked_files: set,
    prefix: str = "",
) -> None:
    if "files" not in node:
        return

    for name, child in node["files"].items():
        if check_cancelled:
            check_cancelled()

        rel_path = f"{prefix}/{name}" if prefix else name
        child_dest = current_dest / name

        if "files" in child:
            child_dest.mkdir(parents=True, exist_ok=True)
            _extract_node(
                child,
                child_dest,
                root_dest,
                asar_file,
                base_offset,
                unpacked_dir,
                callback,
                check_cancelled,
                unpacked_files,
                rel_path,
            )

        elif "link" in child:
            child_dest.parent.mkdir(parents=True, exist_ok=True)
            link_target = current_dest / child["link"]
            try:
                child_dest.symlink_to(link_target)
            except FileExistsError:
                child_dest.unlink()
                child_dest.symlink_to(link_target)
            except OSError:
                pass

        else:
            child_dest.parent.mkdir(parents=True, exist_ok=True)
            is_unpacked = child.get("unpacked", False)

            if is_unpacked:
                unpacked_files.add(rel_path)
                unpacked_src = unpacked_dir / rel_path
                if unpacked_src.exists():
                    shutil.copy2(str(unpacked_src), str(child_dest))
                else:
                    logger.warning(
                        f"Unpacked file missing from external dir (no offset in ASAR): {rel_path}"
                    )
            else:
                offset = int(child["offset"])
                size = child["size"]
                asar_file.seek(base_offset + offset)
                remaining = size
                with open(child_dest, "wb") as out:
                    while remaining > 0:
                        chunk = asar_file.read(min(remaining, BLOCK_SIZE))
                        if not chunk:
                            break
                        out.write(chunk)
                        remaining -= len(chunk)

            if child.get("executable") and os.name != "nt":
                try:
                    child_dest.chmod(child_dest.stat().st_mode | 0o100)
                except OSError:
                    pass

            logger.debug(f"Extracted: {rel_path}")
