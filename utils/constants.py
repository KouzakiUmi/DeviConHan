# -*- coding: utf-8 -*-
"""
全局常量定义模块

集中管理所有魔法数字和配置常量，提高代码可维护性。
"""

import os

# ================= 文件限制常量 =================
MAX_CONFIG_FILE_SIZE: int = 1024 * 1024  # 1MB
MAX_PATH_LENGTH: int = 260  # Windows 标准路径长度
MAX_BACKUP_PREFIX_LENGTH: int = 50

# ================= 时间常量 =================
DEFAULT_ASAR_TIMEOUT: int = 300  # 秒
DEFAULT_CLEANUP_RETRY_DELAY: float = 0.5  # 秒
MAX_CLEANUP_RETRIES: int = 3
DELAYED_CLEANUP_DELAY: int = 60  # 秒

# ================= 文件大小限制 =================
MIN_ASAR_SIZE: int = 1024  # 1KB，小于此值视为损坏
MAX_ASAR_SIZE: int = 2 * 1024 * 1024 * 1024  # 2GB，用于安全检查

# ================= UI 常量 =================
DEFAULT_FONT_SIZE: int = 9
LARGE_FONT_SIZE: int = 11
LOG_AREA_HEIGHT: int = 8  # 行数
WINDOW_MIN_WIDTH: int = 800
WINDOW_MIN_HEIGHT: int = 620

# ================= 哈希计算常量 =================
HASH_CHUNK_SIZE: int = 65536  # 64KB，用于大文件哈希计算

# ================= 异步操作常量 =================
MAX_ASYNC_WORKERS: int = 2
MAX_OPERATION_HISTORY: int = 50

# ================= 存档相关常量 =================
BACKUP_TIMESTAMP_FORMAT: str = "%Y%m%d%H%M%S"
DEFAULT_BACKUP_DIR: str = os.path.join(
    os.path.expanduser("~"), ".tyranopatcher", "backups"
)

# ================= ASAR 常量 =================
ASAR_MAGIC_NUMBER: bytes = b"\x04\x00\x00\x00"
ASAR_HEADER_FIXED_SIZE: int = 8
REQUIRED_ASAR_FILES: list[str] = ["package.json", "index.html"]

# ================= Fuse 常量 =================
FUSE_ENABLED_BYTE: bytes = b"\x31"
FUSE_DISABLED_BYTE: bytes = b"\x30"
FUSE_VALIDATION_MIN_SIZE: int = 1024  # 1KB

# ================= 配置验证常量 =================
TIME_DIFF_THRESHOLD_MAX_DAYS: int = 365  # 旧补丁时间阈值上限（天）

# ================= 默认配置值 =================
DEFAULT_RESOURCE_DIR: str = "resources"
DEFAULT_APP_NAME: str = "TyranoV8_Patcher"
DEFAULT_TARGET_ASAR_NAME: str = "app.asar"
DEFAULT_TEMP_PATCH_DIR: str = "temp_patch"
DEFAULT_PATCH_ZIP_NAME: str = "Patch.zip"
DEFAULT_PATCH_DIR_NAME: str = "Patch"
DEFAULT_BACKUP_PREFIX: str = "Backup_"
DEFAULT_PATCH_INFO_FILE: str = ".patch_info"
DEFAULT_PATCH_META_FILE: str = ".patch_meta"
DEFAULT_FUSE_WIRE_HEADER_LENGTH: int = 34
DEFAULT_FUSE_ASAR_INTEGRITY_OFFSET: int = 4
DEFAULT_TIME_DIFF_THRESHOLD_DAYS: int = 3
DEFAULT_ASAR_TIMEOUT_SECONDS: int = 300

# ================= 项目链接常量 =================
GITHUB_REPO_URL: str = "https://github.com/KouzakiUmi/DeviConHan"
