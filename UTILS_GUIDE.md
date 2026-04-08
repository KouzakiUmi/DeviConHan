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

---

## 路径处理 (utils/paths)

### 主要功能

| 函数 | 描述 |
|------|------|
| `get_resource_path(relative_path)` | 获取资源路径，支持 PyInstaller 打包 |
| `normalize_path(path)` | 规范化路径，处理各种边界情况 |
| `validate_path_exists(path, path_type)` | 验证路径是否存在 |
| `ensure_directory(dir_path)` | 确保目录存在，不存在则创建 |
| `get_user_config_path(filename)` | 获取用户配置文件路径（跨平台） |

### 使用示例

```python
from utils.paths import get_resource_path, normalize_path, ensure_directory

# 获取资源路径（兼容 PyInstaller 打包）
icon_path = get_resource_path("icon.ico")

# 规范化路径
normalized = normalize_path("C:\\Users\\测试\\game")

# 确保目录存在
ensure_directory("C:\\game_data\\saves")
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
| `NodeNotFoundError` | Node.js 未找到异常 |
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

### 使用示例

```python
from utils.file_ops import compute_file_hash, migrate_backup

# 计算文件哈希
hash_value = compute_file_hash("game_save.dat")

# 安全迁移备份（校验后删除源文件）
success = migrate_backup("old_backup.zip", "C:/backups")
```

---

## 清理工具 (utils/cleanup)

### 主要功能

处理顽固的只读文件清理及 Windows 特有的权限占用问题。

| 函数 | 描述 |
|------|------|
| `retry_operation(operation, max_retries, delay, operation_name)` | 重试可能失败的操作 |
| `force_cleanup_dir(temp_dir, max_retries)` | 强制清理临时目录（处理只读文件） |

### 使用示例

```python
from utils.cleanup import retry_operation, force_cleanup_dir

# 重试操作
success = retry_operation(lambda: risky_operation(), max_retries=3)

# 强制清理目录
force_cleanup_dir("C:\\temp\\game_patch")
```

---

## 多语言支持 (utils/language)

### 主要功能

多语言字典（CN/EN/JP），支持系统语言探测及无缝热切换。

| 函数 | 描述 |
|------|------|
| `T(key)` | 多语言翻译函数 |
| `set_language(code)` | 设置界面语言 |
| `init_lang()` | 初始化语言设置 |
| `detect_lang_fallback()` | 使用环境变量检测语言 |
| `get_font(size, weight)` | 根据平台和语言返回合适的 UI 字体 |
| `get_mono_font(size)` | 返回合适的等宽字体 |

### 使用示例

```python
from utils.language import T, set_language, init_lang

# 初始化语言
init_lang()

# 设置语言
set_language("cn")  # 中文
set_language("en")  # 英文
set_language("jp")  # 日文

# 翻译
message = T("save_success")  # "存档成功"
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

## 配置管理 (core/config)

虽然不在 utils 目录，但这是一个重要的配置管理工具：

### 主要功能

| 函数/属性 | 描述 |
|-----------|------|
| `AppConfig` | 配置管理类 |
| `get_config()` | 获取全局配置实例 |
| `auto_target_exe` | 游戏可执行文件名 |
| `fuse_sentinel` | Fuse 校验特征码 |
| `backup_prefix` | 备份文件名前缀 |

### 使用示例

```python
from core.config import get_config

config = get_config()

# 读取配置
exe_name = config.auto_target_exe
sentinel = config.fuse_sentinel

# 获取值
value = config.get("preferences", "language", fallback="en")
value_int = config.get_int("advanced", "timeout", fallback=30)
value_bool = config.get_bool("settings", "auto_backup", fallback=True)