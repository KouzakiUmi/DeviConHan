<a id="core.config"></a>

# core.config

恶魔链接补丁工具 - 配置管理模块

提供配置文件读取、验证和管理功能。
包含配置验证功能，确保配置项的有效性和一致性。

<a id="main"></a>

# main

恶魔链接补丁工具 - 程序入口模块

负责解析命令行参数（CLI），决定启动 GUI 模式还是纯后台运行的批处理模式。

<a id="main.parse_arguments"></a>

## parse_arguments Objects

```python
def parse_arguments() -> argparse.Namespace
```

解析命令行参数

**Returns**:

- `argparse.Namespace` - 解析后的命令行参数对象

<a id="main.main"></a>

## main Objects

```python
def main() -> int
```

程序主入口函数

**Returns**:

- `int` - 退出码 (0=成功, 非0=错误)

<a id="core.config.AppConfig"></a>

## AppConfig Objects

```python
class AppConfig()
```

配置管理类，封装 ConfigParser，从 config.ini 读取配置

<a id="core.config.AppConfig.__init__"></a>

#### \_\_init\_\_

```python
def __init__(config_file: Optional[str] = None)
```

初始化配置管理器

**Arguments**:

- `config_file` - 配置文件路径，None 则使用默认路径

<a id="core.config.AppConfig.reload"></a>

#### reload

```python
def reload() -> None
```

重新加载配置文件（热重载）

<a id="core.config.AppConfig.get"></a>

#### get

```python
def get(section: str,
        key: str,
        fallback: Optional[str] = None,
        **kwargs) -> str
```

获取配置值（字符串）

**Arguments**:

- `section` - 配置节名
- `key` - 配置键名
- `fallback` - 默认值
- `**kwargs` - 传递给 ConfigParser.get 的额外参数
  

**Returns**:

- `str` - 配置值

<a id="core.config.AppConfig.get_int"></a>

#### get\_int

```python
def get_int(section: str, key: str, fallback: int = 0) -> int
```

获取配置值（整数）

**Arguments**:

- `section` - 配置节名
- `key` - 配置键名
- `fallback` - 默认值
  

**Returns**:

- `int` - 配置值

<a id="core.config.AppConfig.get_bool"></a>

#### get\_bool

```python
def get_bool(section: str, key: str, fallback: bool = False) -> bool
```

获取配置值（布尔值）

**Arguments**:

- `section` - 配置节名
- `key` - 配置键名
- `fallback` - 默认值
  

**Returns**:

- `bool` - 配置值

<a id="core.config.AppConfig.get_list"></a>

#### get\_list

```python
def get_list(section: str,
             key: str,
             fallback: Optional[List[str]] = None) -> List[str]
```

获取配置值（列表），支持多行值

**Arguments**:

- `section` - 配置节名
- `key` - 配置键名
- `fallback` - 默认值
  

**Returns**:

- `list` - 配置值列表

<a id="core.config.AppConfig.get_gui_config"></a>

#### get\_gui\_config

```python
def get_gui_config(key: str, default: Optional[Any] = None) -> Any
```

获取 GUI 配置值

**Arguments**:

- `key` - 配置键名
- `default` - 默认值
  

**Returns**:

  配置值或默认值

<a id="core.config.AppConfig.set_gui_config"></a>

#### set\_gui\_config

```python
def set_gui_config(key: str, value: Any) -> bool
```

设置 GUI 配置值

**Arguments**:

- `key` - 配置键名
- `value` - 配置值
  

**Returns**:

- `bool` - 是否成功设置

<a id="core.config.AppConfig.auto_target_exe"></a>

#### auto\_target\_exe

```python
@property
def auto_target_exe()
```

游戏可执行文件名

<a id="core.config.AppConfig.fuse_sentinel"></a>

#### fuse\_sentinel

```python
@property
def fuse_sentinel()
```

Fuse 校验特征码

<a id="core.config.AppConfig.fuse_wire_header_length"></a>

#### fuse\_wire\_header\_length

```python
@property
def fuse_wire_header_length()
```

Fuse 线缆头部长度 (默认 34 = sentinel 32 + length 1 + version 1)

<a id="core.config.AppConfig.fuse_asar_integrity_offset"></a>

#### fuse\_asar\_integrity\_offset

```python
@property
def fuse_asar_integrity_offset()
```

Asar Integrity 验证所在的 Fuse 索引偏移量

<a id="core.config.AppConfig.backup_prefix"></a>

#### backup\_prefix

```python
@property
def backup_prefix()
```

备份文件名前缀

<a id="core.config.AppConfig.patch_info_file"></a>

#### patch\_info\_file

```python
@property
def patch_info_file()
```

补丁信息文件名

<a id="core.config.AppConfig.patch_meta_file"></a>

#### patch\_meta\_file

```python
@property
def patch_meta_file()
```

补丁元数据文件名

<a id="core.config.AppConfig.time_diff_threshold_days"></a>

#### time\_diff\_threshold\_days

```python
@property
def time_diff_threshold_days()
```

旧补丁时间阈值（天）

<a id="core.config.AppConfig.check_files_for_update"></a>

#### check\_files\_for\_update

```python
@property
def check_files_for_update()
```

Steam 更新检测文件列表

<a id="core.config.AppConfig.stable_files_for_validation"></a>

#### stable\_files\_for\_validation

```python
@property
def stable_files_for_validation()
```

稳定文件列表（用于验证备份完整性）

<a id="core.config.AppConfig.resource_dir"></a>

#### resource\_dir

```python
@property
def resource_dir()
```

资源目录名

<a id="core.config.AppConfig.app_name"></a>

#### app\_name

```python
@property
def app_name()
```

程序名称

<a id="core.config.AppConfig.validate_config"></a>

#### validate\_config

```python
def validate_config() -> tuple[bool, list[str]]
```

验证配置文件的有效性

**Returns**:

  tuple[bool, list[str]]: (是否有效, 错误信息列表)

<a id="core.config.AppConfig.validate_required_directory"></a>

#### validate\_required\_directory

```python
def validate_required_directory(dir_path: str,
                                dir_type: str = "directory") -> bool
```

验证必需目录是否存在

**Arguments**:

- `dir_path` - 目录路径
- `dir_type` - 目录类型描述
  

**Returns**:

- `bool` - 目录是否存在

<a id="core.config.get_config"></a>

#### get\_config

```python
def get_config() -> AppConfig
```

获取全局配置实例（单例模式，线程安全）

**Returns**:

- `AppConfig` - 配置实例

<a id="core.patcher"></a>

# core.patcher

恶魔链接补丁工具 - 核心逻辑模块

提供ASAR文件操作、补丁应用、Steam更新处理等核心功能。
包含性能监控集成，用于跟踪和优化操作性能。

<a id="core.patcher.FUSE_ENABLED_BYTE"></a>

#### FUSE\_ENABLED\_BYTE

Fuse 启用状态字节

<a id="core.patcher.FUSE_DISABLED_BYTE"></a>

#### FUSE\_DISABLED\_BYTE

Fuse 禁用状态字节

<a id="core.patcher.FUSE_VALIDATION_MIN_SIZE"></a>

#### FUSE\_VALIDATION\_MIN\_SIZE

Fuse 校验最小文件大小

<a id="core.patcher.CoreLogic"></a>

## CoreLogic Objects

```python
class CoreLogic()
```

<a id="core.patcher.CoreLogic.remove_readonly_handler"></a>

#### remove\_readonly\_handler

```python
@staticmethod
def remove_readonly_handler(func, path, excinfo)
```

删除只读属性的回调函数（静态方法，可在类外复用）

<a id="core.patcher.CoreLogic.__init__"></a>

#### \_\_init\_\_

```python
def __init__()
```

初始化核心逻辑

**Arguments**:

- `log_callback` - 日志回调函数，用于GUI模式
  

**Raises**:

- `PatcherFileNotFoundError` - 如果必要的资源文件不存在

<a id="core.patcher.CoreLogic.remove_readonly"></a>

#### remove\_readonly

```python
def remove_readonly(func, path, excinfo)
```

删除只读属性的回调函数

此方法委托给静态方法，用于 shutil.rmtree 的 onerror 回调。
当删除只读文件时，Python 会调用此函数先移除只读属性再重试删除。

**Arguments**:

- `func` - 导致异常的操作函数（通常是 os.remove 或 os.rmdir）
- `path` - 文件/目录路径
- `excinfo` - 异常信息元组
  

**Returns**:

  处理结果（委托给静态方法）

<a id="core.patcher.CoreLogic.run_asar"></a>

#### run\_asar

```python
def run_asar(action, src, dest, callback=None, unpack_pattern=None)
```

执行ASAR操作（解包或打包）- 固定使用内置依赖库

**Arguments**:

- `action` - 操作类型 ("extract" 或 "pack")
- `src` - 源文件/目录路径
- `dest` - 目标路径
- `callback` - 回调函数，用于更新进度
- `unpack_pattern` - 排除模式（仅打包时使用）
  

**Raises**:


- `PatcherError` - 如果操作失败
  

**Returns**:

- `bool` - 操作是否成功

<a id="core.patcher.CoreLogic.remove_fuse"></a>

#### remove\_fuse

```python
def remove_fuse(exe_path, callback=None)
```

移除游戏可执行文件的Fuse完整性校验

**Arguments**:

- `exe_path` - 游戏可执行文件路径
- `callback` - 回调函数
  

**Returns**:

- `bool` - 是否成功移除Fuse

<a id="core.patcher.has_embedded_patch"></a>

#### has\_embedded\_patch

```python
def has_embedded_patch()
```

检测是否包含内置汉化补丁

**Returns**:

- `bool` - 如果 Patch.zip 或 Patch 目录存在返回 True

<a id="core.patcher.compute_file_hash"></a>

#### compute\_file\_hash

```python
def compute_file_hash(file_path)
```

计算文件的SHA256哈希值

**Arguments**:

- `file_path` - 文件路径
  

**Returns**:

- `str` - 文件的SHA256哈希值（十六进制字符串），失败返回None

<a id="core.patcher.get_file_hash_in_asar"></a>

#### get\_file\_hash\_in\_asar

```python
def get_file_hash_in_asar(_core, asar_path, file_path)
```

计算 ASAR 包内特定文件的 SHA256 哈希值
纯 Python 内存实现，不依赖外部命令行调用，速度快且不产生临时文件。

**Arguments**:

- `_core` - CoreLogic 实例 (保留以保持接口兼容，实际未被使用)
- `asar_path` - ASAR 文件路径
- `file_path` - ASAR 内的相对路径
  

**Returns**:

- `str` - 文件的 SHA256 哈希值，失败返回 None

<a id="core.patcher.save_patch_info"></a>

#### save\_patch\_info

```python
def save_patch_info(base_dir, asar_path, bak_path)
```

保存补丁信息到 .patch_info 文件

**Arguments**:

- `base_dir` - 基础目录
- `asar_path` - asar文件路径
- `bak_path` - 备份文件路径

<a id="core.patcher.save_patch_meta"></a>

#### save\_patch\_meta

```python
def save_patch_meta(base_dir, temp_dir)
```

保存补丁元数据到 .patch_meta 文件

**Arguments**:

- `base_dir` - 基础目录
- `temp_dir` - 临时目录

<a id="core.patcher.handle_steam_update"></a>

#### handle\_steam\_update

```python
def handle_steam_update(core,
                        base_dir,
                        bak_path,
                        asar_path=None,
                        log_callback=None,
                        gui_app=None)
```

处理Steam更新检测和文件状态检查

检测逻辑：
1. ASAR 存在，备份不存在 → 首次打补丁或已使用其他补丁工具
2. ASAR 存在，备份存在 → 检查补丁信息，判断是否需要重新打补丁
3. ASAR 不存在，备份存在 → Steam 更新后自动恢复备份
4. ASAR 不存在，备份不存在 → 游戏文件损坏或安装不完整

**Arguments**:

- `core` - CoreLogic 实例
- `base_dir` - 基础目录
- `bak_path` - 备份文件路径
- `asar_path` - asar文件路径（可选，用于验证文件存在性）
- `log_callback` - 日志回调函数
- `on_error` - 错误提示回调，接收 (title, msg) 参数
- `on_ask_yes_no` - 询问回调，接收 (title, msg) 参数并返回 bool
- `on_info` - 信息提示回调，接收 (title, msg) 参数
  

**Returns**:

- `tuple` - (should_continue, cancel_or_error)
- `should_continue` - 是否应该继续打补丁
- `cancel_or_error` - 是否因为错误或用户取消而停止

<a id="core.patcher.batch_mode"></a>

#### batch\_mode

```python
def batch_mode(args)
```

批处理模式

**Arguments**:

- `args` - 命令行参数
  

**Returns**:

- `int` - 退出码 (0=成功, 非0=错误)

<a id="core.save_service"></a>

# core.save\_service

恶魔链接补丁工具 - 存档服务模块

提供存档的备份、还原、删除和平滑迁移等底层操作。

<a id="core.save_service.SaveService"></a>

## SaveService Objects

```python
class SaveService()
```

存档服务类

提供存档的备份、还原、删除和平滑迁移功能。

<a id="core.save_service.SaveService.__init__"></a>

#### \_\_init\_\_

```python
def __init__(core_logic)
```

初始化存档服务

**Arguments**:

- `core_logic` - CoreLogic 实例

<a id="core.save_service.SaveService.backup_save"></a>

#### backup\_save

```python
def backup_save(save_dir, backup_dir, use_zip=True, log_callback=None)
```

创建存档备份

**Arguments**:

- `save_dir` - 源存档目录
- `backup_dir` - 备份目标目录
- `use_zip` - 是否使用 ZIP 格式压缩
- `log_callback` - 日志回调函数

**Returns**:

- `bool` - 是否备份成功

<a id="core.save_service.SaveService.clear_save_directory"></a>

#### clear\_save\_directory

```python
def clear_save_directory(save_dir)
```

清空存档目录

**Arguments**:

- `save_dir` - 要清空的目录

**Returns**:

- `bool` - 是否成功

<a id="core.save_service.SaveService.restore_save"></a>

#### restore\_save

```python
def restore_save(save_dir, backup_src, log_callback=None)
```

还原存档

**Arguments**:

- `save_dir` - 目标存档目录
- `backup_src` - 备份源路径
- `log_callback` - 日志回调函数

**Returns**:

- `bool` - 是否还原成功

**Raises**:

- `Exception` - 如果清空目录失败

<a id="core.save_service.SaveService.delete_backup"></a>

#### delete\_backup

```python
def delete_backup(backup_src)
```

删除备份

**Arguments**:

- `backup_src` - 备份文件路径

<a id="core.save_service.SaveService.migrate_backups"></a>

#### migrate\_backups

```python
def migrate_backups(old_dir, new_dir, progress_callback=None, log_callback=None)
```

平滑迁移备份

**Arguments**:

- `old_dir` - 旧备份目录
- `new_dir` - 新备份目录
- `progress_callback` - 进度回调函数
- `log_callback` - 日志回调函数
<a id="gui.about_dialog"></a>

# gui.about\_dialog

关于对话框模块

<a id="gui.about_dialog.show_about_dialog"></a>

#### show\_about\_dialog

```python
def show_about_dialog(parent)
```

显示关于对话框

**Arguments**:

- `parent` - 父级窗口实例

<a id="gui.main_window"></a>

# gui.main\_window

恶魔链接补丁工具 - GUI主窗口模块

提供图形用户界面，用于执行ASAR文件操作、备份还原、补丁应用等功能。
包含性能监控集成，用于跟踪和优化GUI操作性能。

<a id="gui.main_window.App"></a>

## App Objects

```python
class App(tk.Tk)
```

<a id="gui.main_window.App.__init__"></a>

#### \_\_init\_\_

```python
def __init__(log_callback=None)
```

初始化GUI应用程序

**Arguments**:

- `log_callback` - 日志回调函数（用于批处理模式）

<a id="gui.main_window.App.load_config"></a>

#### load\_config

```python
def load_config()
```

从配置文件加载用户偏好设置（使用统一的 AppConfig）

**Returns**:

- `bool` - 是否成功加载配置

<a id="gui.main_window.App.get_config_value"></a>

#### get\_config\_value

```python
def get_config_value(key, default=None)
```

获取配置值（使用统一的 AppConfig）

**Arguments**:

- `key` - 配置键名
- `default` - 默认值
  

**Returns**:

  配置值或默认值

<a id="gui.main_window.App.save_config"></a>

#### save\_config

```python
def save_config()
```

保存用户偏好设置到配置文件（使用统一的 AppConfig）

**Returns**:

- `bool` - 是否成功保存

<a id="gui.main_window.App.change_lang"></a>

#### change\_lang

```python
def change_lang(code)
```

切换界面语言

<a id="gui.main_window.App.log"></a>

#### log

```python
def log(msg: str, level: str = "info") -> None
```

在GUI中显示日志消息

**Arguments**:

- `msg` - 要显示的消息
- `level` - 日志级别 ("info", "warning", "error", "debug")

<a id="gui.main_window.App.toggle_progress"></a>

#### toggle\_progress

```python
def toggle_progress(running)
```

切换进度条状态

**Arguments**:

- `running` - True表示开始，False表示停止

<a id="gui.main_window.App.get_backup_dir"></a>

#### get\_backup\_dir

```python
def get_backup_dir()
```

获取当前配置的存档备份存放目录

<a id="utils.async_ops"></a>

# utils.async\_ops

异步操作管理器模块

提供异步操作执行、进度跟踪和取消功能，用于避免GUI卡顿。

<a id="utils.async_ops.OperationState"></a>

## OperationState Objects

```python
class OperationState(Enum)
```

操作状态

<a id="utils.async_ops.ProgressInfo"></a>

## ProgressInfo Objects

```python
class ProgressInfo()
```

进度信息

<a id="utils.async_ops.AsyncOperationManager"></a>

## AsyncOperationManager Objects

```python
class AsyncOperationManager()
```

异步操作管理器

提供后台任务执行、进度更新和取消功能。

<a id="utils.async_ops.AsyncOperationManager.__init__"></a>

#### \_\_init\_\_

```python
def __init__(max_workers: int = 2)
```

初始化异步操作管理器

**Arguments**:

- `max_workers` - 最大工作线程数

<a id="utils.async_ops.AsyncOperationManager.set_progress_callback"></a>

#### set\_progress\_callback

```python
def set_progress_callback(callback: Callable[[ProgressInfo], None]) -> None
```

设置进度回调函数

**Arguments**:

- `callback` - 回调函数，接收 ProgressInfo 参数

<a id="utils.async_ops.AsyncOperationManager.submit"></a>

#### submit

```python
def submit(operation_id: str, func: Callable, *args, **kwargs) -> Future
```

提交异步任务

**Arguments**:

- `operation_id` - 操作ID
- `func` - 要执行的函数
- `*args` - 函数位置参数
- `**kwargs` - 函数关键字参数
  

**Returns**:

- `Future` - 异步任务Future对象

<a id="utils.async_ops.AsyncOperationManager.update_progress"></a>

#### update\_progress

```python
def update_progress(operation_id: str,
                    progress: int,
                    message: str = "") -> None
```

更新操作进度

**Arguments**:

- `operation_id` - 操作ID
- `progress` - 进度值 (0-100)
- `message` - 进度消息

<a id="utils.async_ops.AsyncOperationManager.cancel"></a>

#### cancel

```python
def cancel(operation_id: str) -> bool
```

取消操作

**Arguments**:

- `operation_id` - 操作ID
  

**Returns**:

- `bool` - 是否成功取消

<a id="utils.async_ops.AsyncOperationManager.get_progress"></a>

#### get\_progress

```python
def get_progress(operation_id: str) -> Optional[ProgressInfo]
```

获取操作进度信息

**Arguments**:

- `operation_id` - 操作ID
  

**Returns**:

  ProgressInfo 或 None

<a id="utils.async_ops.AsyncOperationManager.get_all_operations"></a>

#### get\_all\_operations

```python
def get_all_operations() -> Dict[str, ProgressInfo]
```

获取所有操作信息

<a id="utils.async_ops.AsyncOperationManager.cleanup_completed"></a>

#### cleanup\_completed

```python
def cleanup_completed() -> None
```

清理已完成的任务记录

<a id="utils.async_ops.AsyncOperationManager.shutdown"></a>

#### shutdown

```python
def shutdown(wait: bool = True) -> None
```

关闭异步操作管理器

**Arguments**:

- `wait` - 是否等待任务完成

<a id="utils.async_ops.get_async_manager"></a>

#### get\_async\_manager

```python
def get_async_manager() -> AsyncOperationManager
```

获取全局异步操作管理器

<a id="utils.cleanup"></a>

# utils.cleanup

工具函数模块 - 通用清理功能

提供临时目录强制清理等通用工具函数。

<a id="utils.cleanup.retry_operation"></a>

#### retry\_operation

```python
def retry_operation(operation: Callable[[], Any],
                    max_retries: int = 3,
                    delay: float = 0.5,
                    operation_name: str = "operation") -> bool
```

重试一个可能失败的操作

**Arguments**:

- `operation` - 要执行的函数
- `max_retries` - 最大重试次数
- `delay` - 重试之间的延迟（秒）
- `operation_name` - 操作名称（用于日志记录）
  

**Returns**:

- `bool` - 操作是否最终成功

<a id="utils.cleanup.force_cleanup_dir"></a>

#### force\_cleanup\_dir

```python
def force_cleanup_dir(temp_dir: str, max_retries: int = 3) -> bool
```

强制清理临时目录（处理只读文件和目录）

**Arguments**:

- `temp_dir` - 临时目录路径
- `max_retries` - 最大重试次数
  

**Returns**:

- `bool` - 是否成功清理

<a id="utils.error_handler"></a>

# utils.error\_handler

统一错误处理模块

提供标准化的错误处理、用户友好的错误消息和日志记录功能。

<a id="utils.error_handler.ErrorSeverity"></a>

## ErrorSeverity Objects

```python
class ErrorSeverity(Enum)
```

错误严重级别

<a id="utils.error_handler.ErrorCategory"></a>

## ErrorCategory Objects

```python
class ErrorCategory(Enum)
```

错误分类

<a id="utils.error_handler.PatcherError"></a>

## PatcherError Objects

```python
class PatcherError(Exception)
```

基础补丁工具异常类

<a id="utils.error_handler.PatcherError.to_dict"></a>

#### to\_dict

```python
def to_dict() -> Dict[str, Any]
```

转换为字典格式

<a id="utils.error_handler.PatcherFileNotFoundError"></a>

## PatcherFileNotFoundError Objects

```python
class PatcherFileNotFoundError(PatcherError)
```

文件未找到异常

<a id="utils.error_handler.PatcherPermissionError"></a>

## PatcherPermissionError Objects

```python
class PatcherPermissionError(PatcherError)
```

权限异常

<a id="utils.error_handler.AsarCorruptedError"></a>

## AsarCorruptedError Objects

```python
class AsarCorruptedError(PatcherError)
```

ASAR文件损坏异常

<a id="utils.error_handler.ConfigError"></a>

## ConfigError Objects

```python
class ConfigError(PatcherError)
```

配置错误异常

<a id="utils.error_handler.ErrorHandler"></a>

## ErrorHandler Objects

```python
class ErrorHandler()
```

统一错误处理器

<a id="utils.error_handler.ErrorHandler.set_language"></a>

#### set\_language

```python
def set_language(lang: str)
```

设置当前语言

<a id="utils.error_handler.ErrorHandler.get_user_message"></a>

#### get\_user\_message

```python
def get_user_message(error: Exception) -> str
```

获取用户友好的错误消息

**Arguments**:

- `error` - 异常对象
  

**Returns**:

- `str` - 用户友好的错误消息

<a id="utils.error_handler.ErrorHandler.log_error"></a>

#### log\_error

```python
def log_error(error: Exception, context: str = "") -> None
```

记录错误日志

**Arguments**:

- `error` - 异常对象
- `context` - 错误上下文信息

<a id="utils.error_handler.ErrorHandler.handle_error"></a>

#### handle\_error

```python
def handle_error(error: Exception, context: str = "") -> str
```

处理错误并返回用户友好的消息

**Arguments**:

- `error` - 异常对象
- `context` - 错误上下文
  

**Returns**:

- `str` - 用户友好的错误消息

<a id="utils.error_handler.ErrorHandler.format_traceback"></a>

#### format\_traceback

```python
@staticmethod
def format_traceback(error: Exception) -> str
```

格式化异常堆栈跟踪

<a id="utils.error_handler.get_error_handler"></a>

#### get\_error\_handler

```python
def get_error_handler() -> ErrorHandler
```

获取全局错误处理器

<a id="utils.error_handler.set_error_language"></a>

#### set\_error\_language

```python
def set_error_language(lang: str) -> None
```

设置错误处理器的语言

<a id="utils.error_handler.handle_patcher_error"></a>

#### handle\_patcher\_error

```python
def handle_patcher_error(error: Exception, context: str = "") -> str
```

处理补丁工具错误的便捷函数

**Arguments**:

- `error` - 异常对象
- `context` - 错误上下文
  

**Returns**:

- `str` - 用户友好的错误消息

<a id="utils.file_ops"></a>

# utils.file\_ops

文件和目录操作模块

提供复制目录并校验哈希值等高级文件操作。

<a id="utils.file_ops.compute_file_hash"></a>

#### compute\_file\_hash

```python
def compute_file_hash(file_path: str) -> str
```

计算文件的 SHA256 哈希值

<a id="utils.file_ops.migrate_backup"></a>

#### migrate\_backup

```python
def migrate_backup(src: str, dest_dir: str) -> bool
```

将备份文件或目录迁移到目标目录，
复制后校验哈希值，如果校验通过则删除源文件/目录。

**Arguments**:

- `src` - 源路径 (文件或目录)
- `dest_dir` - 目标目录的父路径 (备份将被放置于此目录中)
  

**Returns**:

- `bool` - 迁移是否完全成功

<a id="utils.language"></a>

# utils.language

<a id="utils.language.detect_lang_fallback"></a>

#### detect\_lang\_fallback

```python
def detect_lang_fallback() -> None
```

使用环境变量检测语言（跨平台）

<a id="utils.language.T"></a>

#### T

```python
def T(key: str) -> str
```

多语言翻译函数

**Arguments**:

- `key` - 翻译键
  

**Returns**:

  对应语言的文本

<a id="utils.language.get_font"></a>

#### get\_font

```python
def get_font(
        size: int = 9,
        weight: str = "normal"
) -> Union[Tuple[str, int], Tuple[str, int, str]]
```

根据平台和语言返回合适的 UI 字体

<a id="utils.language.get_mono_font"></a>

#### get\_mono\_font

```python
def get_mono_font(size: int = 9) -> Tuple[str, int]
```

返回合适的等宽字体（用于日志等）

<a id="utils.language.set_language"></a>

#### set\_language

```python
def set_language(code: str) -> None
```

设置界面语言（推荐使用此函数而非直接修改 CURRENT_LANG_CODE）

**Arguments**:

- `code` - 语言代码 ('en', 'cn', 'jp')

<a id="utils.language.init_lang"></a>

#### init\_lang

```python
def init_lang() -> None
```

初始化语言设置，优先从配置文件读取用户偏好

<a id="utils.logging"></a>

# utils.logging

<a id="utils.logging.setup_logging"></a>

#### setup\_logging

```python
def setup_logging(log_dir: Optional[str] = None,
                  log_file: str = "tyrano_patcher.log",
                  max_bytes: int = 10 * 1024 * 1024,
                  backup_count: int = 5,
                  verbose: bool = False,
                  quiet: bool = False) -> logging.Logger
```

设置日志系统，支持控制台和文件输出，带日志轮转功能

**Arguments**:

- `log_dir` - 日志目录路径，None表示使用默认目录
- `log_file` - 日志文件名
- `max_bytes` - 单个日志文件最大字节数（默认10MB）
- `backup_count` - 保留的备份文件数量
- `verbose` - 是否启用详细输出
- `quiet` - 是否静默模式（仅输出错误）
  

**Returns**:

- `logging.Logger` - 配置好的根logger

<a id="utils.paths"></a>

# utils.paths

<a id="utils.paths.get_resource_path"></a>

#### get\_resource\_path

```python
def get_resource_path(relative_path: str) -> str
```

获取资源路径（支持PyInstaller打包）

**Arguments**:

- `relative_path` - 相对路径

**Returns**:

  绝对路径

<a id="utils.paths.normalize_path"></a>

#### normalize\_path

```python
def normalize_path(path: str) -> str
```

规范化路径，处理各种边界情况

<a id="utils.paths.validate_path_exists"></a>

#### validate\_path\_exists

```python
def validate_path_exists(path: str,
                         path_type: str = "Resource") -> Tuple[bool, str]
```

验证路径是否存在

**Arguments**:

- `path` - 路径字符串
- `path_type` - 路径类型描述（用于日志）
  

**Returns**:

  tuple[bool, str]: (是否存在, 错误消息)

<a id="utils.paths.ensure_directory"></a>

#### ensure\_directory

```python
def ensure_directory(dir_path: str) -> bool
```

确保目录存在，不存在则创建

**Arguments**:

- `dir_path` - 目录路径
  

**Returns**:

- `bool` - 是否成功

<a id="utils.paths.get_user_config_path"></a>

#### get\_user\_config\_path

```python
def get_user_config_path(filename: str = "config.ini") -> str
```

获取用户配置文件路径（跨平台）

**Arguments**:

- `filename` - 配置文件名
  

**Returns**:

- `str` - 完整的配置文件路径

<a id="utils.performance"></a>

# utils.performance

性能分析工具模块

提供性能分析和计时功能，用于优化和监控程序运行。

<a id="utils.performance.PerformanceMonitor"></a>

## PerformanceMonitor Objects

```python
class PerformanceMonitor()
```

性能监控器，用于跟踪和分析代码性能

<a id="utils.performance.PerformanceMonitor.__init__"></a>

#### \_\_init\_\_

```python
def __init__()
```

初始化性能监控器

<a id="utils.performance.PerformanceMonitor.enable"></a>

#### enable

```python
def enable() -> None
```

启用性能监控

<a id="utils.performance.PerformanceMonitor.disable"></a>

#### disable

```python
def disable() -> None
```

禁用性能监控

<a id="utils.performance.PerformanceMonitor.start"></a>

#### start

```python
def start(name: str) -> None
```

开始计时

**Arguments**:

- `name` - 计时器名称

<a id="utils.performance.PerformanceMonitor.stop"></a>

#### stop

```python
def stop(name: str) -> float
```

停止计时并返回耗时

**Arguments**:

- `name` - 计时器名称
  

**Returns**:

  耗时（秒）

<a id="utils.performance.PerformanceMonitor.get_stats"></a>

#### get\_stats

```python
def get_stats(name: str) -> Optional[Dict[str, Any]]
```

获取计时器统计信息

**Arguments**:

- `name` - 计时器名称
  

**Returns**:

  统计信息字典，如果计时器不存在则返回 None

<a id="utils.performance.PerformanceMonitor.get_all_stats"></a>

#### get\_all\_stats

```python
def get_all_stats() -> Dict[str, Dict[str, Any]]
```

获取所有计时器的统计信息

**Returns**:

  所有计时器的统计信息字典

<a id="utils.performance.PerformanceMonitor.reset"></a>

#### reset

```python
def reset(name: Optional[str] = None) -> None
```

重置计时器

**Arguments**:

- `name` - 计时器名称，None 表示重置所有计时器

<a id="utils.performance.PerformanceMonitor.log_stats"></a>

#### log\_stats

```python
def log_stats(name: str) -> None
```

记录计时器统计信息到日志

**Arguments**:

- `name` - 计时器名称

<a id="utils.performance.get_performance_monitor"></a>

#### get\_performance\_monitor

```python
def get_performance_monitor() -> PerformanceMonitor
```

获取全局性能监控器实例

**Returns**:

  性能监控器实例

<a id="utils.performance.timing_context"></a>

#### timing\_context

```python
@contextmanager
def timing_context(name: str)
```

计时上下文管理器

**Arguments**:

- `name` - 计时器名称
  
  Usage:
  with timing_context('operation_name'):
  # 代码块

<a id="utils.performance.timed"></a>

#### timed

```python
def timed(name: Optional[str] = None)
```

计时装饰器

**Arguments**:

- `name` - 计时器名称，None 表示使用函数名
  
  Usage:
  @timed()
  def my_function():
  pass
  
  @timed('custom_name')
  def another_function():
  pass

<a id="utils.performance.profile_block"></a>

#### profile\_block

```python
@contextmanager
def profile_block(description: str, enabled: bool = True)
```

性能分析代码块

**Arguments**:

- `description` - 描述信息
- `enabled` - 是否启用
  
  Usage:
  with profile_block("ASAR extraction"):
  # 代码块

<a id="controllers"></a>

# controllers

控制器模块

提供业务逻辑控制器，将 GUI 代码与业务逻辑分离，提高代码可维护性。

<a id="controllers.save_manager_controller"></a>

## controllers.save\_manager\_controller

存档管理控制器模块

封装存档扫描、备份、还原、删除和平滑迁移等业务逻辑。

<a id="controllers.save_manager_controller.SaveManagerController"></a>

### SaveManagerController Objects

```python
class SaveManagerController()
```

存档管理器控制器

提供存档目录扫描、备份、还原、删除和平滑迁移功能。

<a id="controllers.save_manager_controller.SaveManagerController.__init__"></a>

#### \_\_init\_\_

```python
def __init__(save_service: SaveService, log_callback: Optional[Callable] = None)
```

初始化存档管理器控制器

**Arguments**:

- `save_service` - SaveService 实例
- `log_callback` - 日志回调函数

<a id="controllers.save_manager_controller.SaveManagerController.set_log_callback"></a>

#### set\_log\_callback

```python
def set_log_callback(callback: Callable) -> None
```

设置日志回调

**Arguments**:

- `callback` - 日志回调函数

<a id="controllers.save_manager_controller.SaveManagerController.scan_save_directory"></a>

#### scan\_save\_directory

```python
def scan_save_directory() -> Optional[str]
```

扫描并返回存档目录路径

**Returns**:

- `str` - 存档目录路径，未找到则返回 None

<a id="controllers.save_manager_controller.SaveManagerController.scan_backups"></a>

#### scan\_backups

```python
def scan_backups(save_root: str, backup_dir: str) -> list
```

扫描备份目录，返回备份文件列表

**Arguments**:

- `save_root` - 游戏存档根目录
- `backup_dir` - 备份目录

**Returns**:

- `list` - 备份文件列表

<a id="controllers.save_manager_controller.SaveManagerController.execute_backup"></a>

#### execute\_backup

```python
def execute_backup(save_dir: str, backup_dir: str, use_zip: bool) -> bool
```

执行存档备份

**Arguments**:

- `save_dir` - 源存档目录
- `backup_dir` - 备份目标目录
- `use_zip` - 是否使用 ZIP 格式

**Returns**:

- `bool` - 是否备份成功

<a id="controllers.save_manager_controller.SaveManagerController.execute_restore"></a>

#### execute\_restore

```python
def execute_restore(save_dir: str, backup_src: str) -> tuple[bool, str]
```

执行存档还原

**Arguments**:

- `save_dir` - 目标存档目录
- `backup_src` - 备份源路径

**Returns**:

- `tuple[bool, str]` - (是否成功, 错误消息)

<a id="controllers.save_manager_controller.SaveManagerController.execute_delete"></a>

#### execute\_delete

```python
def execute_delete(backup_src: str) -> bool
```

删除备份

**Arguments**:

- `backup_src` - 备份文件路径

**Returns**:

- `bool` - 是否删除成功

<a id="controllers.save_manager_controller.SaveManagerController.migrate_backups"></a>

#### migrate\_backups

```python
def migrate_backups(old_dir: str, new_dir: str) -> tuple[int, int]
```

平滑迁移备份文件

**Arguments**:

- `old_dir` - 旧备份目录
- `new_dir` - 新备份目录

**Returns**:

- `tuple[int, int]` - (成功数量, 失败数量)

<a id="controllers.patch_controller"></a>

## controllers.patch\_controller

补丁安装控制器模块

封装补丁安装相关业务逻辑，解耦 GUI 代码。

<a id="controllers.patch_controller.PatchController"></a>

### PatchController Objects

```python
class PatchController()
```

补丁安装控制器

负责处理补丁安装的完整流程，包括 Steam 更新检测、ASAR 操作等。

<a id="controllers.patch_controller.PatchController.__init__"></a>

#### \_\_init\_\_

```python
def __init__(core_logic, log_callback: Optional[Callable] = None)
```

初始化补丁控制器

**Arguments**:

- `core_logic` - CoreLogic 实例
- `log_callback` - 日志回调函数

<a id="controllers.patch_controller.PatchController.set_log_callback"></a>

#### set\_log\_callback

```python
def set_log_callback(callback: Callable) -> None
```

设置日志回调

**Arguments**:

- `callback` - 日志回调函数

<a id="controllers.patch_controller.PatchController.check_prerequisites"></a>

#### check\_prerequisites

```python
def check_prerequisites() -> Tuple[bool, str]
```

检查补丁安装的前置条件

**Returns**:

- `tuple[bool, str]` - (是否满足, 错误消息)

<a id="controllers.patch_controller.PatchController.run_auto_patch"></a>

#### run\_auto\_patch

```python
def run_auto_patch(gui_app=None) -> Tuple[bool, Optional[str], str]
```

执行自动补丁安装

**Arguments**:

- `gui_app` - GUI 应用实例（用于显示对话框）

**Returns**:

- `tuple[bool, Optional[str], str]` - (是否成功, 临时目录, 错误消息)

<a id="controllers.patch_controller.PatchController.handle_error"></a>

#### handle\_error

```python
def handle_error(base_dir: str, asar_path: str, bak_path: str, error: Exception) -> None
```

处理补丁失败的还原逻辑

**Arguments**:

- `base_dir` - 基础目录
- `asar_path` - ASAR 文件路径
- `bak_path` - 备份文件路径
- `error` - 异常对象

---

<a id="utils.constants"></a>

# utils.constants

全局常量定义模块

集中管理所有魔法数字和配置常量。

<a id="utils.constants.MAX_CONFIG_FILE_SIZE"></a>

#### MAX\_CONFIG\_FILE\_SIZE

配置文件大小限制 (1MB)

<a id="utils.constants.DEFAULT_ASAR_TIMEOUT"></a>

#### DEFAULT\_ASAR\_TIMEOUT

ASAR 操作超时时间 (300秒)

<a id="utils.constants.HASH_CHUNK_SIZE"></a>

#### HASH\_CHUNK\_SIZE

哈希计算块大小 (64KB)

<a id="utils.constants.ASAR_MAGIC_NUMBER"></a>

#### ASAR\_MAGIC\_NUMBER

ASAR 文件魔数 (b"\x04\x00\x00\x00")

<a id="utils.constants.MAX_CLEANUP_RETRIES"></a>

#### MAX\_CLEANUP\_RETRIES

清理重试次数 (3)

---

<a id="utils.validators"></a>

# utils.validators

输入验证装饰器模块

提供路径验证、非空验证等常用验证功能。

<a id="utils.validators.ValidationError"></a>

## ValidationError Objects

```python
class ValidationError(Exception)
```

验证错误异常

<a id="utils.validators.validate_path"></a>

#### validate\_path

```python
def validate_path(should_exist: bool = True, path_type: Optional[str] = None) -> Callable
```

路径验证装饰器

**Arguments**:

- `should_exist` - 路径是否应该存在
- `path_type` - 路径类型 ('file', 'dir', None)

**Returns**:

- 装饰器函数

**Usage**:

```python
@validate_path(should_exist=True, path_type='file')
def process_file(file_path: str):
    pass
```

<a id="utils.validators.validate_not_empty"></a>

#### validate\_not\_empty

```python
def validate_not_empty(func: Callable) -> Callable
```

非空字符串验证装饰器

**Usage**:

```python
@validate_not_empty
def process_name(name: str):
    pass
```

<a id="utils.validators.validate_asar_source"></a>

#### validate\_asar\_source

```python
def validate_asar_source(func: Callable) -> Callable
```

ASAR 源目录验证装饰器

检查目录是否包含必需的 ASAR 文件

---

<a id="utils.cleanup.TempDirectoryManager"></a>

## TempDirectoryManager Objects

```python
class TempDirectoryManager()
```

临时目录上下文管理器

提供安全的临时目录创建和自动清理。

<a id="utils.cleanup.TempDirectoryManager.__init__"></a>

#### \_\_init\_\_

```python
def __init__(prefix: str = "temp_", suffix: str = "", parent_dir: Optional[str] = None, cleanup_on_exit: bool = True)
```

初始化临时目录管理器

**Arguments**:

- `prefix` - 目录名前缀
- `suffix` - 目录名后缀
- `parent_dir` - 父目录
- `cleanup_on_exit` - 退出时是否清理

<a id="utils.cleanup.TempDirectoryManager.keep"></a>

#### keep

```python
def keep() -> None
```

保留临时目录，退出时不清理

<a id="utils.cleanup.TempDirectoryManager.get_path"></a>

#### get\_path

```python
def get_path() -> Optional[str]
```

获取临时目录路径

<a id="utils.cleanup.TempDirectoryManager.cleanup_now"></a>

#### cleanup\_now

```python
def cleanup_now() -> bool
```

立即清理临时目录

**Returns**:

- `bool` - 是否成功清理

