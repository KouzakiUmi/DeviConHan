"""
全局常量定义模块

集中管理所有魔法数字和配置常量，提高代码可维护性。
"""

import os

# ================= 文件限制常量 =================
MAX_CONFIG_FILE_SIZE: int = 1024 * 1024  # 1MB
MAX_PATH_LENGTH: int = 260
MAX_BACKUP_PREFIX_LENGTH: int = 50

# ================= 时间常量 =================
DEFAULT_CLEANUP_RETRY_DELAY: float = 0.5
MAX_CLEANUP_RETRIES: int = 3
DELAYED_CLEANUP_DELAY: int = 60

# ================= 文件大小限制 =================
MIN_ASAR_SIZE: int = 1024
MAX_ASAR_SIZE: int = 8 * 1024 * 1024 * 1024

# ================= UI 常量 =================
DEFAULT_FONT_SIZE: int = 9
LARGE_FONT_SIZE: int = 11
LOG_AREA_HEIGHT: int = 12
WINDOW_MIN_WIDTH: int = 800
WINDOW_MIN_HEIGHT: int = 680

# ================= 目录和文件命名常量 =================
UNPACKED_DIR_NAME: str = "_Unpacked"
PACKED_DIR_NAME: str = "_Packed"
EXTRACTED_SUFFIX: str = "_extracted"
ASAR_EXTENSION: str = ".asar"
ZIP_EXTENSION: str = ".zip"
TEMP_FILE_SUFFIX: str = ".tmp"
CORRUPTED_SUFFIX: str = ".corrupted"

# ================= 临时目录前缀 =================
TEMP_BACKUP_PREFIX: str = "save_restore_"

# ================= 对话框超时 =================
DEFAULT_DIALOG_TIMEOUT: int = 3600

# ================= 哈希计算常量 =================
HASH_CHUNK_SIZE: int = 65536

# ================= ZIP 安全限制常量 =================
# 防止 ZIP 炸弹攻击：限制解压后总大小和文件数量
MAX_ZIP_EXTRACT_SIZE: int = 2 * 1024 * 1024 * 1024  # 2 GB
MAX_ZIP_EXTRACT_FILES: int = 100_000

# ================= 异步操作常量 =================
MAX_ASYNC_WORKERS: int = 2
MAX_OPERATION_HISTORY: int = 50

# ================= 存档相关常量 =================
BACKUP_TIMESTAMP_FORMAT: str = "%Y%m%d%H%M%S"
DEFAULT_BACKUP_DIR: str = os.path.join(os.path.expanduser("~"), ".tyranopatcher", "backups")

# ================= ASAR 协议常量 =================
# Pickle 格式 sizePickle 的固定 payload_size 字段，不应当被当作完整文件签名使用。
ASAR_MAGIC_NUMBER: bytes = b"\x04\x00\x00\x00"
ASAR_DATA_SIZE: int = 4
ASAR_BLOCK_SIZE: int = 4 * 1024 * 1024
ASAR_ALGORITHM: str = "SHA256"
ASAR_HEADER_STRUCT_FMT: str = "<4I"
ASAR_HEADER_READ_SIZE: int = 16
ASAR_MAGIC_BYTES_SIZE: int = 4

# ================= Fuse 常量 =================
FUSE_ENABLED_BYTE: bytes = b"\x31"
FUSE_DISABLED_BYTE: bytes = b"\x30"
FUSE_VALIDATION_MIN_SIZE: int = 1024
FUSE_PARTIAL_HASH_HEAD_SIZE: int = 1024 * 1024  # 1 MB
FUSE_PARTIAL_HASH_TAIL_SIZE: int = 1024 * 1024  # 1 MB

# ================= ASAR 原生模块扩展名 =================
NATIVE_EXTENSIONS = frozenset({".node", ".dll", ".so", ".dylib", ".bin", ".exe", ".lib"})

# ================= ASAR 必需文件 =================
# 用于验证 ASAR 解包目录是否是有效的 asar 源码目录
REQUIRED_ASAR_FILES = ["package.json", "index.html"]

# ================= 配置验证常量 =================
# 与 config.ini 中的 TIME_DIFF_THRESHOLD_DAYS 保持一致（默认 730 天，约 2 年）
TIME_DIFF_THRESHOLD_MAX_DAYS: int = 730

# ================= 默认配置值 =================
DEFAULT_ASAR_TIMEOUT_SECONDS: int = 300  # ASAR 操作超时时间（秒）

# ================= 项目链接常量 =================
GITHUB_REPO_URL: str = "https://github.com/KouzakiUmi/DeviConHan"

BATCH_CANCEL_OR_ERROR_MSG: str = "Cancelled or error"
