# 工具模块说明文档

本文档详细介绍 `utils/` 目录下的实用工具类及其使用方法。

---

## 目录

1. [路径处理 (utils/paths)](#路径处理-utilspaths)
2. [异步操作 (utils/async_ops)](#异步操作-utilasync_ops)
3. [错误处理 (utils/error_handler)](#错误处理-utilserror_handler)
4. [性能监控 (utils/performance)](#性能监控-utilsperformance)
5. [文件操作 (utils/file_ops)](#文件操作-utilsfile_ops)
6. [清理工具 (utils/cleanup)](#清理工具-utilscleanup)
7. [多语言支持 (utils/language)](#多语言支持-utilslanguage)
8. [日志系统 (utils/logging)](#日志系统-utilslogging)
9. [常量定义 (utils/constants)](#常量定义-utilsconstants)
10. [输入验证 (utils/validators)](#输入验证-utilsvalidators)
11. [ASAR 工具 (utils/asar_utils)](#asar-工具-utilasar_utils)
12. [磁盘工具 (utils/disk_utils)](#磁盘工具-utilsdisk_utils)
13. [操作锁 (utils/operation_lock)](#操作锁-utilsoperation_lock)
14. [平台工具 (utils/platform)](#平台工具-utilsplatform)
15. [事务管理 (utils/transaction)](#事务管理-utilstransaction)

---

## 路径处理 (utils/paths)

### 主要功能

| 函数 | 描述 |
|------|------|
| `get_resource_path(relative_path)` | 获取资源路径，支持 PyInstaller 打包 |
| `normalize_path(path)` | 规范化路径，处理各种边界情况 |
| `safe_path_within(path, base_dir)` | 规范化路径并验证其位于指定基础目录内（防路径遍历） |
| `validate_path_exists(path, path_type)` | 验证路径是否存在 |
| `ensure_directory(dir_path)` | 确保目录存在，不存在则创建 |
| `get_user_config_path(filename)` | 获取用户配置文件路径（跨平台） |

### 使用示例

```python
from utils.paths import get_resource_path, normalize_path, ensure_directory

# 获取资源路径（兼容 PyInstaller 打包）
icon_path = get_resource_path("icon.ico")

# 规范化路径
normalized = normalize_path("C:\Users\测试\game")

# 确保目录存在
ensure_directory("C:\game_data\saves")
```

---

## 异步操作 (utils/async_ops)

### 主要功能

提供后台任务执行、进度更新和取消功能，避免 GUI 卡顿。

| 类/函数 | 描述 |
|--------|------|
| `AsyncOperationManager` | 异步操作管理器 |
| `ProgressInfo` | 进度信息对象 |
| `OperationState` | 操作状态枚举 |
| `get_async_manager()` | 获取全局异步操作管理器 |

### 使用示例

```python
from utils.async_ops import get_async_manager

# 获取全局管理器
async_mgr = get_async_manager()

# 设置进度回调
async_mgr.set_progress_callback(lambda info: print(f"{info.progress}% - {info.message}"))

# 提交后台任务 (支持通过接收 _check_cancelled kwargs 实现真实线程中断)
future = async_mgr.submit("my_task", my_worker_function, arg1, arg2)

# 更新进度
async_mgr.update_progress("my_task", 50, "处理中...")

# 取消任务
async_mgr.cancel("my_task")
```

---

## 错误处理 (utils/error_handler)

### 主要功能

提供标准化的错误处理、用户友好的错误消息和日志记录。

| 异常类 | 描述 |
|--------|------|
| `PatcherError` | 基础补丁工具异常类 |
| `PatcherFileNotFoundError` | 文件未找到异常 |
| `PatcherPermissionError` | 权限异常 |
| `AsarCorruptedError` | ASAR 文件损坏异常 |
| `ConfigError` | 配置错误异常 |

### 使用示例

```python
from utils.error_handler import PatcherError, get_error_handler, handle_patcher_error

# 抛出自定义异常
raise PatcherFileNotFoundError("app.asar not found")

# 使用错误处理器
error_handler = get_error_handler()
user_message = error_handler.get_user_message(exception)

# 便捷函数
user_message = handle_patcher_error(exception, context="打补丁操作")
```

---

## 性能监控 (utils/performance)

### 主要功能

提供性能分析和计时功能，用于优化和监控程序运行。

| 函数/类 | 描述 |
|---------|------|
| `PerformanceMonitor` | 性能监控器 |
| `get_performance_monitor()` | 获取全局性能监控器实例 |
| `timing_context(name)` | 计时上下文管理器 |
| `timed(name)` | 计时装饰器 |
| `profile_block(description)` | 性能分析代码块 |

### 使用示例

```python
from utils.performance import get_performance_monitor, timing_context, timed

# 获取监控器
monitor = get_performance_monitor()

# 简单计时
monitor.start("operation")
# ... 执行操作 ...
elapsed = monitor.stop("operation")

# 使用上下文管理器
with timing_context("file_copy"):
    copy_files()

# 使用装饰器
@timed("my_function")
def my_function():
    pass
```

---

## 文件操作 (utils/file_ops)

### 主要功能

高级文件操作，提供如 Hash 校验迁移等高阶数据安全方法。

| 函数 | 描述 |
|------|------|
| `compute_file_hash(file_path)` | 计算文件的 SHA256 哈希值 |
| `migrate_backup(src, dest_dir)` | 将备份文件迁移到目标目录，复制后校验哈希值 |
| `safe_extract_zip(zip_path, dest_dir)` | 安全解压 ZIP 文件（防止路径遍历） |

### 使用示例

```python
from utils.file_ops import compute_file_hash, migrate_backup, safe_extract_zip

# 计算文件哈希
hash_value = compute_file_hash("game_save.dat")

# 安全迁移备份（校验后删除源文件）
success = migrate_backup("old_backup.zip", "C:/backups")

# 安全解压 ZIP
safe_extract_zip("patch.zip", "C:/game/resources")
```

---

## 清理工具 (utils/cleanup)

### 主要功能

处理顽固的只读文件清理及 Windows 特有的权限占用问题。

| 函数/类 | 描述 |
|--------|------|
| `retry_operation(operation, max_retries, delay, operation_name)` | 重试可能失败的操作 |
| `force_cleanup_dir(temp_dir, max_retries)` | 强制清理临时目录（处理只读文件） |
| `schedule_delayed_cleanup()` | 延迟清理调度 |

### 使用示例

```python
from utils.cleanup import (
    retry_operation, 
    force_cleanup_dir,
    schedule_delayed_cleanup,
)

# 重试操作
success = retry_operation(lambda: risky_operation(), max_retries=3)

# 强制清理目录
force_cleanup_dir("C:\\temp\\game_patch")

# 延迟清理（后台线程等待60秒后清理）
schedule_delayed_cleanup("C:\\temp\\old_dir", delay_seconds=60)
```

---

## 多语言支持 (utils/language)

### 主要功能

多语言字典（CN/EN/JP），支持系统语言探测及无缝热切换。**线程安全**：使用版本号缓存机制，语言切换时自动刷新所有线程的缓存。

| 函数 | 描述 |
|------|------|
| `T(key)` | 多语言翻译函数（线程安全，带缓存） |
| `set_language(code)` | 设置界面语言（线程安全） |
| `init_lang()` | 初始化语言设置 |
| `detect_lang()` | 自动检测系统语言 |
| `get_font(size, weight)` | 根据平台和语言返回合适的 UI 字体 |
| `get_mono_font(size)` | 返回合适的等宽字体 |

### 使用示例

```python
from utils.language import T, set_language, init_lang

# 初始化语言
init_lang()

# 设置语言（自动通知所有线程刷新）
set_language("cn")  # 中文
set_language("en")  # 英文
set_language("jp")  # 日文

# 翻译（自动使用线程本地缓存）
message = T("save_success")  # "存档成功"

# 带默认值的翻译
message = T("unknown_key", "Default Text")
```

---

## 日志系统 (utils/logging)

### 主要功能

初始化滚动日志（Rotating File Handler），支持控制台和文件输出。

| 函数 | 描述 |
|------|------|
| `setup_logging(log_dir, log_file, max_bytes, backup_count, verbose, quiet)` | 设置日志系统 |

### 使用示例

```python
from utils.logging import setup_logging
import logging

# 设置日志
logger = setup_logging(
    log_dir=None,  # 使用默认目录
    log_file="tyrano_patcher.log",
    max_bytes=10*1024*1024,  # 10MB
    backup_count=5,
    verbose=False,
    quiet=False
)

# 使用日志
logger.info("程序启动")
logger.error("发生错误")
```

---

## 常量定义 (utils/constants)

### 主要功能

集中管理所有魔法数字和配置常量，提高代码可维护性。

| 常量类别 | 示例 |
|---------|------|
| `MAX_CONFIG_FILE_SIZE` | 配置文件大小限制 (1MB) |
| `DEFAULT_ASAR_TIMEOUT` | ASAR操作超时 (300秒) |
| `HASH_CHUNK_SIZE` | 哈希计算块大小 (64KB) |
| `ASAR_MAGIC_NUMBER` | Pickle 头部固定前缀字段（非完整文件签名） |
| `MAX_CLEANUP_RETRIES` | 清理重试次数 (3次) |

### 使用示例

```python
from utils.constants import MAX_CONFIG_FILE_SIZE, HASH_CHUNK_SIZE

# 检查配置文件大小
if file_size > MAX_CONFIG_FILE_SIZE:
    logger.warning("Config file too large")

# 计算文件哈希
sha256_hash = hashlib.sha256()
with open(file_path, "rb") as f:
    for chunk in iter(lambda: f.read(HASH_CHUNK_SIZE), b""):
        sha256_hash.update(chunk)
```

---

## 输入验证 (utils/validators)

### 主要功能

提供输入验证装饰器，简化参数校验逻辑。

| 装饰器 | 描述 |
|--------|------|
| `@validate_path(should_exist, path_type)` | 路径存在性和类型验证 |
| `@validate_not_empty` | 非空字符串验证 |

### 使用示例

```python
from utils.validators import validate_path, validate_not_empty, ValidationError

@validate_path(should_exist=True, path_type='file')
@validate_not_empty
def process_asar_file(asar_path: str) -> None:
    """处理ASAR文件（带验证）"""
    # 路径已通过装饰器验证
    pass

@validate_path(should_exist=True, path_type='dir')
def backup_directory(dir_path: str) -> bool:
    """备份目录（带验证）"""
    # 目录已验证存在
    return True

# 处理验证错误
try:
    process_asar_file("")
except ValidationError as e:
    logger.error(f"Validation failed: {e}")
```

---

## ASAR 工具 (utils/asar_utils)

### 主要功能

提供纯 Python 的 ASAR 格式解析能力，支持在不解包的情况下读取 ASAR 内部文件的 Hash 值。
当前解析器兼容 `modern_pickle`、`legacy_8` 和 `legacy_16` 三种头部布局。

| 函数 | 描述 |
|------|------|
| `parse_asar_header(asar_path)` | 解析 ASAR 头部并返回格式、JSON 大小和数据区偏移 |
| `is_valid_asar(asar_path)` | 验证 ASAR 是否可被支持的解析器成功读取 |
| `validate_asar_with_reason(asar_path)` | 验证 ASAR 并返回失败原因 |
| `open_asar_reader(asar_path)` | 以只读方式打开 ASAR 读取器 |
| `get_file_hashes_in_asar(asar_path, file_paths)` | 批量获取 ASAR 内文件的 SHA256 Hash |

### 核心特性

- **纯 Python 实现**：无需 Node.js，直接读取 ASAR 二进制格式
- **多格式解析**：优先识别现代 Pickle 格式，再回退旧布局
- **直接定位**：使用 `seek` 进行高效文件读取
- **Hash 验证**：支持 Steam 更新检测，快速比对文件完整性

### 使用示例

```python
from utils.asar_utils import get_file_hashes_in_asar, parse_asar_header

# 解析头部
header = parse_asar_header("app.asar")
print(header.format_name, header.base_offset)

# 批量获取 ASAR 内文件的 Hash（无需解包）
hashes = get_file_hashes_in_asar("app.asar", ["tyrano/lang.js", "index.html"])
for path, file_hash in hashes.items():
    print(path, file_hash)
```



### 实现原理

1. 按支持的格式依次尝试解析 ASAR 头部
2. 提取 JSON 元数据，获取文件偏移量和大小
3. 使用 `seek` 定位到指定偏移量
4. 直接在流上计算 SHA256

---

## 配置管理 (core/config)

虽然不在 utils 目录，但这是一个重要的配置管理工具：

### 主要功能

| 函数/属性 | 描述 |
|-----------|------|
| `AppConfig` | 配置管理类（线程安全） |
| `get_config()` | 获取全局配置实例 |
| `auto_target_exe` | 游戏可执行文件名 |
| `fuse_sentinel` | Fuse 校验特征码 |
| `backup_prefix` | 备份文件名前缀 |
| `validate_config()` | 验证配置有效性（使用快照） |
| `reload()` | 重新加载配置（原子操作） |

### 线程安全特性

配置模块已实现线程安全：
- **RLock 读写锁**：支持并发读取，独占写入
- **配置快照**：验证时使用快照，避免长时间持有锁
- **原子操作**：配置保存和重载均为原子操作

### 使用示例

```python
from core.config import get_config

config = get_config()

# 读取配置（线程安全）
exe_name = config.auto_target_exe
sentinel = config.fuse_sentinel

# 获取值
value = config.get("preferences", "language", fallback="en")
value_int = config.get_int("advanced", "timeout", fallback=30)
value_bool = config.get_bool("settings", "auto_backup", fallback=True)

# 验证配置（返回 valid, errors, warnings）
valid, errors, warnings = config.validate_config()
if not valid:
    logger.error(f"Config validation failed: {errors}")

# 设置配置值（自动加锁）
config.set_gui_config("language", "cn")
```

---

## 磁盘工具 (utils/disk_utils)

### 主要功能

| 函数 | 描述 |
|------|------|
| `get_disk_free_space(path)` | 获取磁盘剩余空间 |
| `check_disk_space(path, required_bytes)` | 检查是否有足够磁盘空间 |
| `estimate_asar_size(source_path)` | 估算ASAR打包后的大小 |
| `validate_write_permission(path)` | 验证写入权限 |
| `format_bytes(bytes_value)` | 格式化字节数为人类可读格式 |
| `check_operation_space(operations, base_path)` | 检查一系列操作所需的磁盘空间 |

### 使用示例

```python
from utils.disk_utils import check_disk_space, estimate_asar_size, format_bytes, get_disk_free_space

# 检查磁盘空间
free_space = get_disk_free_space("/game")
ok, available = check_disk_space("/game", 100 * 1024 * 1024)  # 100MB
if not ok:
    print(f"空间不足，仅剩 {available} 字节")

# 估算ASAR大小
size = estimate_asar_size("source_dir")
print(f"预计大小: {format_bytes(size)}")
```

---

## 操作锁 (utils/operation_lock)

### 主要功能

| 类/函数 | 描述 |
|------|------|
| `OperationLock` | 操作互斥锁类 |
| `OperationType` | 操作类型枚举 |
| `get_operation_lock()` | 获取全局操作锁实例 |
| `with_operation_lock(op_type)` | 装饰器形式的操作锁 |

### 使用示例

```python
from utils.operation_lock import OperationType, get_operation_lock, with_operation_lock

op_lock = get_operation_lock()

# 检查操作是否可以开始
if op_lock.is_operation_running(OperationType.PATCH):
    print("补丁操作正在进行中")
else:
    if op_lock.acquire(OperationType.PATCH):
        try:
            apply_patch()
        finally:
            op_lock.release(OperationType.PATCH)

with op_lock.acquire_context(OperationType.PATCH):
    apply_patch()

@with_operation_lock(OperationType.PATCH)
def apply_patch():
    pass
```

---

## 平台工具 (utils/platform)

### 主要功能

| 函数/类 | 描述 |
|------|------|
| `PlatformInfo` | 当前平台及主 Steam 路径信息 |
| `SteamAppInfo` | 从 ACF 清单解析出的 Steam 应用信息 |
| `get_platform_info()` | 获取平台信息 |
| `get_steam_library_paths()` | 获取所有 Steam 库路径 |
| `find_game_by_appid(appid)` | 通过 AppID 精确查找游戏 |
| `find_game_in_steam(game_id)` | 通过 AppID 或名称变体查找游戏 |
| `get_resources_path(game_path)` | 获取游戏 resources 路径 |
| `get_asar_path(game_path, asar_name)` | 获取 ASAR 文件路径 |
| `is_app_bundle(path)` | 判断是否为 macOS `.app` bundle |

### 使用示例

```python
from utils.platform import find_game_in_steam, get_asar_path, get_platform_info

info = get_platform_info()
print(info.system, info.steam_common_path)

game_dir = find_game_in_steam("3054820")
if game_dir:
    print(get_asar_path(game_dir))
```

---

## 事务管理 (utils/transaction)

### 主要功能

| 类/函数 | 描述 |
|------|------|
| `FileTransaction` | 文件操作事务管理器 |
| `atomic_rename(src, dst)` | 原子重命名 |
| `safe_backup(file_path)` | 创建安全备份 |

### 使用示例

```python
from utils.transaction import FileTransaction

with FileTransaction() as tx:
    tx.backup_original("app.asar")
    tx.stage_new_file("app.asar", "app.asar.new")
    tx.commit()
```

---
