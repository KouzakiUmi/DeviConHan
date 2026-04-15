# Tyrano补丁工具箱 - 项目规范与技术参考 (Project Specifications)

**でびるコネクション汉化补丁是自带示例作品。可通过config和patch.zip适配其他游戏。**

这份文档详细描述了本工具的设计哲学、架构细节、核心工作流以及避免常见误解的关键设定。

---

## 1. 核心定位与设计原则 (Core Philosophy)

* **定位**：这是一个专为基于 **Electron / TyranoV8** 引擎开发的游戏《恶魔链接 (Devil Connection)》设计的本地化（汉化）自动化工具箱。
* **安全性至上**：所有破坏性操作（如覆盖存档、删除文件、修改可执行文件）均需经过前置确认、Hash 校验或严格的沙盒化处理。
* **无痛防更新**：Steam 经常强制更新游戏文件。工具必须能够智能感知 Steam 的更新，在可验证时复用或重建备份，并尽量减少用户重复操作。
* **跨平台兼容**：在 Windows、macOS 和 Linux 上均可运行，所有路径操作和系统级 API 调用（如获取默认语言、打开文件夹）都必须考虑跨平台差异。

---

## 2. 目录与架构设计 (Architecture)

工具采用了经典的 MVC / 模块化分层架构：

### 📁 模块说明
* **`main.py`**：程序入口点。负责解析命令行参数（CLI），决定启动 `GUI 模式` 还是纯后台运行的 `批处理模式 (--batch)`。
* **`core/`** (核心业务层)
  * `bootstrap.py`：系统引导模块，负责初始化检查、配置验证和状态检查。
  * `patcher.py`：负责 **ASAR 解包/打包** 的核心调用与校验；Steam 更新状态机由 `steam.py` 和 `patch_controller.py` 协调。
  * `config.py`：`AppConfig` 配置管理单例。支持内存热加载，优先读取用户个人空间配置。
  * `save_service.py`：`SaveService` 存档服务类，提供存档的备份、还原、删除和平滑迁移等底层操作。
  * `steam.py`：Steam 更新状态机及 Hash 校验检测。
  * `state_validator.py`：系统状态验证模块，检查ASAR文件、备份完整性和补丁状态。
  * `patch_info.py`：补丁元数据存储管理。
  * `fuse.py`：移除游戏底层 Electron 的防篡改锁。
  * `batch.py`：非 GUI 的静默批处理安装模式。
* **`gui/`** (表示层)
  * `main_window.py`：基于 `tkinter` 和 `ttk` 的图形界面主入口。复杂视图已被独立拆分为内部辅助方法或外部模块以提高可读性。
  * `about_dialog.py`：独立的“关于”对话框视图模块，解决原先 `App` 类过于臃肿的问题。
* **`controllers/`** (业务控制器层)
  * `save_manager_controller.py`：存档管理控制器，封装存档扫描、备份、还原、删除和平滑迁移等业务逻辑，将 GUI 代码与业务逻辑分离。
  * `patch_controller.py`：补丁安装控制器，封装补丁安装的完整流程，包括 Steam 更新检测、ASAR 操作等。
* **`utils/`** (通用工具层) —— *本层全面应用了 Python Type Hints 以确保调用安全*
  * `language.py`：多语言字典（CN/EN/JP），支持系统语言探测及无缝热切换。注意：tkinter 不支持 CSS 式逗号分隔字体回退，`get_font()` 返回单一字体族名。
  * `paths.py`：安全处理资源路径解析（兼容 PyInstaller 的 `sys._MEIPASS`）。
  * `file_ops.py`：高级文件操作，提供如 **Hash 校验迁移 (`migrate_backup`)** 等高阶数据安全方法。
  * `cleanup.py`：包含 `force_cleanup_dir`，用于处理顽固的只读文件清理及 Windows 特有的权限占用问题。
  * `async_ops.py`：封装了 `ThreadPoolExecutor` 的 `AsyncOperationManager`，统筹 GUI 进度条、任务状态与后台线程，并支持通过下发 `_check_cancelled` 实现文件级的真实线程中断。
  * `performance.py`：用于性能打点和日志耗时统计。
  * `logging.py`：初始化滚动日志（Rotating File Handler），默认输出至 `~/.tyranopatcher/tyrano_patcher.log`。
* `asar_utils.py`：纯 Python ASAR 解析与 Hash 计算，`get_file_hash_in_asar(asar_path, file_path)` 无需 CoreLogic 实例。
* **`Patch/`** (数据层)
    * 包含实际将要注入进游戏 `app.asar` 中的翻译文件与媒体资源。

---

## 3. 核心机制详解 (Core Mechanisms)

为了避免“我以为是这样但是并不是”的情况，以下是各个系统的特定设计：

### 3.1 配置文件隔离机制 (Configuration Isolation)
* **不是读取当前目录！**：为了防止 Steam 验证完整性、覆盖安装或工具移动位置导致配置丢失，程序**优先读取并保存至** `~/.tyranopatcher/config.ini`（或对应的 Windows `%USERPROFILE%` 路径）。
* **回退机制**：如果用户目录下不存在该配置，工具会将自身的 `config.ini` 默认模板**复制一份到用户目录**中。后续修改（如 Fuse 偏移、语言偏好）全部基于用户目录下的副本。

### 3.2 存档管理与平滑迁移 (Save Backup & Migration)
* **备份位置**：过去存档默认备份在游戏的 `_storage` 的上级目录，这会导致卸载游戏时备份一并丢失。现在**默认备份路径改为了 `~/.tyranopatcher/backups`**。
* **扫描与去重**：`SaveManagerController.scan_backups()` 会**同时扫描**游戏目录和当前备份目录。如果有同名备份，会在显示名后附加父目录以区分，并按时间戳字符串倒序显示。
* **平滑迁移 (Migrate Backup)**：当用户在界面点击“更改目录”时，触发 `utils/file_ops.py` 的迁移机制。
  * **机制**：复制源文件 -> 计算双方 SHA256 -> 比对一致 -> 删除源文件。确保中途断电也不会丢失存档。
* **防目录遍历 (Zip Slip)**：在还原 ZIP 备份时，通过比对解压后的绝对路径和目标根路径 (`startswith`)，防止恶意构造的 ZIP 覆盖系统核心文件。

### 3.3 Steam 更新状态机 (Steam Update Detection)
在 `core/steam.py -> handle_steam_update()` 中，并非简单检测“是否存在 ASAR”。
* **检测依据**：除了文件存在性，工具还会检查 `app.asar` 内部几个关键稳定文件（如 `index.html`, `package.json`）的 **Hash 值**。
* **情境矩阵**：
  * 无 ASAR 无备份：提示游戏损坏，需验证完整性。
  * 无 ASAR 有备份：被 Steam 覆盖性更新或手动删除；批处理模式会继续恢复，GUI 模式会先询问用户是否基于备份继续。
  * 有 ASAR 有备份：核对 ASAR 内文件 Hash 是否符合 `.patch_meta` 中记录的补丁后 Hash。如果不符合，再比对原版备份的 Hash：
    * 如果与原版一致，说明 Steam 发生更新覆盖，**删除旧备份并重建**。
    * 如果都不一致，提示可能受到第三方篡改，请求用户决策。

### 3.4 动态 Fuse 移除架构 (Electron Fuses Patching)
游戏可执行文件 (`DevilConnection.exe`) 包含 Electron Fuse，其中第 4 项用于验证 ASAR 完整性（如果不移除，修改后的 `app.asar` 将无法启动游戏）。
* **误区**：不要以为所有 Electron 的 Fuse 固定在硬编码位置。
* **设计**：根据 Electron 的 `kFuseWire` 规范：
  * **特征码 (Sentinel)**：`dL7pKGdnNz796PbbjQWNKmHXBZaB9tsX`（32 字节）。
  * 紧跟其后的是 **1字节长度**和 **1字节版本**（共 34 字节的头部）。
  * 因此目标标志位的偏移量是：`Header Length (34) + 目标Fuse索引 (4)`。
* 程序现在将 `34` 和 `4` 作为**可配置项**暴露在 `config.ini` 中 (`FUSE_WIRE_HEADER_LENGTH`, `FUSE_ASAR_INTEGRITY_OFFSET`)。UI 界面提供直接修改偏移量的入口，保障引擎换代后的向下兼容能力。修改的值将从 `0x31 (1)` 变为 `0x30 (0)`。

### 3.5 纯 Python 的 ASAR Hash 读取 (In-Memory ASAR Parsing)
* 程序使用 Python 直接解析 ASAR 头部，兼容 `modern_pickle`、`legacy_8` 和 `legacy_16` 三种布局。
* 对现代 Pickle 格式，头部结构为 `[sizePickle 8B][headerPickle NB][file data...]`，数据区起点是 `8 + headerPickle.length`。
* 解析出 JSON 字典、目标文件的 Offset 和 Size 后，再通过 `seek` 直接计算 SHA256。此操作使得更新检测极为迅速，不会产生额外的解包开销。

### 3.6 ASAR 完整性校验 (Archive Integrity Validation)
* 在 `core/steam.py -> _validate_archive_integrity()` 中，**同样使用纯 Python 解析 ASAR header**来验证归档文件完整性，不再启动 `node.exe` 子进程。
* 校验流程：按支持的格式依次尝试解析头部 → 提取 JSON header → 校验 `files` 字段存在。不会再把前 4 字节 `0x04 00 00 00` 当作完整文件签名使用。整个过程零子进程开销，耗时从原先的 0.5-1s 降至约 10ms。

### 3.7 补丁信息原子写入 (Atomic Patch Info Writes)
* `core/patch_info.py` 中的 `save_patch_info()` 和 `save_patch_meta()` 使用原子写入模式（先写 `.tmp` 临时文件，再 `os.replace` 原子替换）。
* 这与 `core/config.py` 的 `save()` 方法保持一致，防止进程崩溃时文件截断损坏。由于 Steam 更新检测依赖 `.patch_meta` 文件判断补丁状态，原子写入确保数据安全性。

### 3.8 Fuse 备份快速验证 (Fast Fuse Backup Verification)
* `core/fuse.py` 中存在 `_partial_hash()` 作为快速校验工具，但当前实际的 Fuse 备份可用性判定主要依赖哨兵定位与目标字节检查。
* 创建与恢复 `.fuse_backup` 时，代码仍会通过完整 SHA256 比对源文件和备份文件，优先保证可恢复性而非只追求极速校验。

---

## 4. UI 响应与异常处理 (Exception Handling & UI Responsiveness)

* **操作闭环 (is_operating)**：在 `main_window.py` 中，任何导致文件写入的操作（打补丁、备份、恢复、打包解包）在进入工作流前，必须先校验 `if self.is_operating:`，并设为 `True`，同时触发 `self.toggle_progress(True)`。结束后在 `finally` 块或 `_on_async_progress` 回调中重置。
* **空指针安全 (Null Checks)**：
  * 在 UI 中点击“解包”、“修改 Fuse”等任何强依赖路径的操作前，必须进行 `if not t:` 和 `os.path.exists(t)` 验证。若触发空指针则弹窗阻止，**避免静默失败使用户困惑**。
* **日志隔离与输出**：UI 提供实时滚动文本框展示日志。而底层的 `logger` 会将其同步写入文件和控制台，确保即使 UI 卡死也能追溯错误源。

---

## 5. 维护与更新指南 (Maintenance Guide)

当需要修改工具或扩展功能时：
1. **修改界面语言**：不要在代码中直接写中文字符串用于提示！去 `utils/language.py` 添加一个 Key，并在三语字典（`cn`/`en`/`jp`）中补齐翻译。在 UI 代码中使用 `T("your_key")` 调用。如果是带变量的字符串，请在 Python 层调用 `.format(var=xxx)`。
2. **新增配置项**：在 `core/config.py -> AppConfig` 添加对应的 `@property` 及 fallback 值。无需手动解析类型，使用 `get_int` / `get_bool`。如果有 GUI 设置需求，利用 `set_gui_config` 写入 `[preferences]`。
3. **增加耗时后台任务**：使用 `self.async_manager.submit("task_id", _worker_func)`，在 `_worker_func` 中切勿直接操作 tkinter 组件。如果任务非常耗时，应通过 `**kwargs` 接收 `_check_cancelled` 回调，在底层循环中检测中断事件。
4. **编译与打包**：确保 `Patch/` 目录存在后，在 Windows 执行 `Pack.cmd`，即可生成 `DevilConnection_Patch.exe`。
5. **类型安全 (Type Hints)**：在扩展 `utils` 或 `core` 等底层库的方法时，建议尽可能包含 Python 的静态类型提示 (`from typing import Optional, Dict` 等)，并在复杂函数上补充完备的文档注释。
6. **自动化脚本与参数补全**：若要对 `--auto` 以及其他 CLI 命令参数进行扩充，在 `main.py` 的 `parse_arguments` 中先完成定义，然后必须在批处理流和 GUI 流同时做好回退处理。

--- 
*End of Specs*
