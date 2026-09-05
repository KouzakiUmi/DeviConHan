# Tyrano补丁工具箱

**でびるコネクショん汉化补丁是自带示例作品。**

![Status](https://img.shields.io/badge/Status-RC-orange?style=flat-square)
![Platform](https://img.shields.io/badge/Platform-Win%20|%20Mac%20|%20Linux-blue?style=flat-square)
![License](https://img.shields.io/badge/License-CC%20BY--NC--SA%204.0-lightgrey?style=flat-square)
![Build](https://img.shields.io/badge/Build-Automated-success?style=flat-square)

> **By KouzakiUmi (呜咪 / 神前海)**

---

<div align="center">

**🌐 语言 / Language / 言語**

**[中文 🇨🇳 (当前)](README.md)** • **[English 🇬🇧](README_en.md)** • **[日本語 🇯🇵](README_ja.md)**

</div>

**开发者说明**：本工具箱为通用 **Tyrano补丁工具**，`でびるコネクショん` 汉化补丁为自带示例。通过**修改 `config.ini`**（WINDOWS_EXE、FUSE_SENTINEL、CHECK_FILES_FOR_UPDATE 等）并提供对应游戏的 `Patch.zip`（也可在界面选择自定义 ZIP）进行适配，完成后需在目标游戏版本上验证。详见 [PLUGIN_GUIDE.md](PLUGIN_GUIDE.md)。

---

本项目起源是《恶魔连接（でびるコネクショん）》的非营利性个人本地化工具。
采用全图形化界面 (GUI)，支持 Windows/macOS/Linux，集成了强大的存档管理与开发者工具。现已更新为通用工具箱。

**✨ 核心功能：**

| 功能 | 描述 |
|------|------|
| 🚀 **全自动补丁安装** | 默认使用内置 `Patch.zip`，也可在界面选择自定义 ZIP；自动识别负载层级、备份并支持手动还原原版文件 |
| 💾 **专业存档管理** | 独立于游戏目录的安全备份位置，支持自定义目录与平滑迁移，一键备份/还原/ZIP |
| 🛠️ **开发者工具箱** | 内置 Asar 解包/打包工具，支持跨平台格式选择与自定义 Fuse 偏移量修改 |
| ⚙️ **独立配置系统** | 支持热重载与合法性验证，自动隔离用户配置与内置模板，保障长期运行稳定 |
| 🔒 **操作保护** | 智能并发锁、备份迁移确认、Hash 校验与失败恢复；游戏文件异常时优先通过 Steam 验证完整性 |
| 🌐 **多语言支持** | 内置中文/英文/日文，运行时自由切换，无需重启 |
| 📚 **技术文档** | 当前运行接口与安全契约见 [TECHNICAL_REFERENCE.md](TECHNICAL_REFERENCE.md)，旧签名索引见 [API_DOCS.md](API_DOCS.md) |

---

## 📥 安装

### 🚀 自动构建版（推荐）

每次推送到 main 分支会自动构建，下载最新版本：
- 前往 [Releases](../../releases) 下载对应系统的构建；Windows 版为 `DevilConnection_Patch.exe` 或 `Tyrano_Toolbox.exe`

### 🏁 Windows（从源码构建）

准备 Python 3.8+ 和 Tkinter；构建依赖为 `pyinstaller`、`pillow`。

```cmd
git clone https://github.com/KouzakiUmi/DeviConHan.git
cd DeviConHan
.\Pack.cmd
```

构建产物位于 `dist/` 目录：
- `Tyrano_Toolbox.exe` - 纯净工具箱
- `DevilConnection_Patch.exe` - 游戏汉化补丁版（存在 `Patch.zip` 或非空 `Patch/` 时生成）

---

### 🍎 macOS / 🐧 Linux

**前置要求**
- Python 3.8+，并确保 Tkinter 可用
- 运行核心功能无需第三方 ASAR 库或 Node.js；打包需要 `pyinstaller` 和 `pillow`（用于图标转换）

**安装步骤**
```bash
# 1. 克隆项目
git clone https://github.com/KouzakiUmi/DeviConHan.git
cd DeviConHan

# 2. 安装构建依赖（仅构建时需要）
python3 -m pip install pyinstaller pillow

# 3. 运行程序
python3 main.py
```

**跨平台构建**
```bash
# 在 macOS / Linux 上构建当前系统版本
bash Pack.sh
```

请在目标操作系统上运行对应构建脚本。脚本会清理旧 `dist/` 和临时构建文件；非空 `Patch/` 会优先压缩为临时补丁资源，否则使用已有 `Patch.zip`，不覆盖仓库中的补丁包。详见 [PACK.md](PACK.md)。

---

## 🎮 补丁安装与还原

1. 关闭游戏，在“安装补丁”页选择内置补丁或自定义 ZIP，然后点击安装。工具箱版请先到“开发者工具 → 配置管理”勾选“启用补丁安装”，即可点击进入第一页并选择补丁 ZIP；内置补丁版默认开启。
2. 如需更换补丁，请先通过 Steam 验证游戏文件完整性，或还原原版游戏文件，再安装对应版本的补丁。
3. 文件异常时，优先使用 Steam 的“属性 → 已安装文件 → 验证游戏文件的完整性”。

**🌐 英文补丁**：[EnglishPatch.zip](EnglishPatch.zip) 是《でびるコネクショん》的英文补丁，可按上述步骤选择该 ZIP 进行自定义安装。

> 💡 **补丁与版本**：工具解包原始 ASAR，用新 Patch 覆盖对应文件，再重新打包。游戏版本不匹配或原始文件已有其他修改时，可能导致文件混杂、内容错乱或无法运行。

安装记录会保存补丁 Hash；相同补丁且安装状态正常时跳过。更换补丁或旧记录缺少 Hash 时，GUI 会提供恢复提示；确认使用本地原版备份后，会从该备份重新构建。备份可能早于当前游戏版本，校验通过不代表与补丁兼容。

---

## 💾 存档管理

### 🇨🇳 功能介绍
工具内置了**专业级存档管理系统**（“存档管理”标签页），便于备份、还原和管理历史存档：

#### 🔄 工作流程
```
🎮 游戏运行 → 🔍 自动扫描 → 📋 列表显示 → 💾 一键备份 → ✅ 确认还原
```

#### 核心功能
- **🔍 自动扫描**：识别 `_storage`、`save`、`SaveData`、`UserData` 等存档文件夹，并根据检测到的游戏目录定位；当前存档目录缺失时仍可扫描独立备份
- **💾 快速备份**：点击 **"➕ 新建备份"**，自动生成带**年月日时分秒**时间戳的快照
  - 默认独立存储于 `~/.tyranopatcher/backups`，与游戏目录分开保存，减少重装游戏时误删备份的风险
  - 支持**平滑迁移**：更改备份存放目录时可选择迁移以前的数据（复制并校验 Hash 后才删除源备份）
  - 支持**文件夹备份**和 **ZIP 压缩备份**（推荐开启，节省空间）
  - 备份类型在列表中清晰显示 `[ZIP]` 或 `[DIR]`
- **↩️ 一键还原**：选中历史备份，点击 **"还原选中"** 恢复存档
  - 还原前确认目标路径，避免误覆盖当前进度；存档目录丢失时可选择实际恢复位置
  - 后台异步操作，保持工具界面响应；操作前请先关闭游戏
- **🗑️ 灵活删除**：可随时清理不需要的旧备份，释放存储空间
- **🔒 多重保护**：并发锁避免冲突操作；还原失败时尝试回滚，并区分成功、未修改或已回滚、回滚失败

> 💡 **存档独立管理**：安装或还原补丁不会主动修改存档。Steam 验证游戏文件不能代替存档备份恢复。

---

## 🛠️ 开发者工具箱与高级功能

> 💡 **重要提醒**：所有架构细节、工作流与技术规范，请参见最新的 [项目规范与技术参考 (PROJECT_SPECS.md)](./PROJECT_SPECS.md)。

补丁事务、取消边界、崩溃恢复、存档还原三态返回值和 CLI 参数的准确契约见
[TECHNICAL_REFERENCE.md](TECHNICAL_REFERENCE.md)。补丁提交阶段不可安全取消；
若此时进程被终止，工具下次启动会按恢复记录尝试恢复，失败时应通过 Steam 验证
游戏文件完整性。GUI 可在游戏文件异常时打开并显示恢复指引，安装前仍会校验文件。

### ⚙️ 配置文件体系与隔离
配置现采用**用户偏好与出厂预设双隔离模式**：
- **`~/.tyranopatcher/config.ini`**（优先加载）：系统在首次启动时，会自动将内置的默认配置拷贝至该位置持久保存。
- **日志与语言**：日志默认位于 `~/.tyranopatcher/tyrano_patcher.log`；用户提示和操作进度随语言设置切换，内部诊断日志保留英文。Windows 中 `~` 对应 `%USERPROFILE%`。
- **日志显示**：默认窗口为 `800 × 800`，日志区按 6 行设置，使用 10 磅字体并增加行距。中文优先使用已安装的中文等宽字体，其次使用微软雅黑 UI 等本地字体；英文界面保留等宽显示。
- **配置管理**：开发者工具界面中自带“验证配置”与“重置默认”功能。随时可验证你的配置文件是否存在缺失键值或者非法语法的异常。

### 🔧 Fuse移除与配置动态化
TyranoV8/Electron版本迭代可能改变Fuse布局。开发者工具箱 -> 配置管理 -> 修改Fuse偏移（默认4，可配置`FUSE_ASAR_INTEGRITY_OFFSET`）支持动态调整，值实时保存到用户`config.ini`并生效。此功能独立于自动安装流程。偏移应按目标游戏的 Electron 布局确认，并先在副本上测试；文件异常时优先通过 Steam 恢复。

### 📁 项目架构

- **入口**：`main.py` — 参数解析、init_lang、bootstrap_system（配置/路径/状态检查）、GUI (`gui/main_window.py` + `tabs/*`) 或 batch模式。
- **core/**：`bootstrap.py`（系统引导）、`patcher.py`（CoreLogic，直接调用 `utils.asar_writer` 的 `asar_extract` / `asar_pack`）、`config.py`（单例、用户`~/.tyranopatcher/config.ini`优先、snapshot+TTL热重载、fallback如`TARGET_ASAR_NAME=app.asar`、`PATCH_ZIP_NAME=Patch.zip`）、`steam.py`+`state_validator.py`（4种ASAR/备份/patch_meta状态机 + 纯Python哈希验证）、`save_service.py`、`fuse.py`（可配置偏移）、`patch_info.py`（补丁指纹、安装记录与原子写入）、`batch.py`。
- **gui/**：`main_window.py`（tab管理、log/progress）、`tabs/patch_tab.py`、`save_tab.py`、`tools_tab.py`（ASAR/Fuse/配置UI）。
- **controllers/**：业务逻辑分离（`patch_controller.py`封装Steam处理+patch流程、`save_manager_controller.py`）。
- **utils/**：`language.py`（系统语言优先级+菜单切换+INI持久化）、`paths.py`（PyInstaller _MEIPASS兼容）、`async_ops.py`（ThreadPool+取消）、`file_ops.py`（hash/migrate）、`cleanup.py`、`logging.py`（RotatingFile）、`asar_utils.py`（纯Python校验）、`validators.py`、`constants.py`、`performance.py`。
- **打包脚本**：`Pack.cmd`/`Pack.sh` — 检查Python/PyInstaller、构建`Tyrano_Toolbox`、在临时构建目录中为`Patch/`生成 staged `Patch.zip`（不改动工作区原文件）、构建带补丁的`DevilConnection_Patch`、清理build/和.spec。运行时仅依赖Python标准库；打包时额外需要 `PyInstaller` 和用于图标转换的 `Pillow`。
- **文档导航**：总览见 [DOCS_INDEX.md](DOCS_INDEX.md)，补充的模块文档见 [MODULE_GUIDE.md](MODULE_GUIDE.md)。

**config.ini模板关键项**（用户副本优先，可热重载验证）：
```ini
[main]
WINDOWS_EXE = DevilConnection.exe
MACOS_APP = Devil Connection.app
LINUX_BINARY = DevilConnection
FUSE_SENTINEL = dL7pKGdnNz796PbbjQWNKmHXBZaB9tsX
FUSE_ASAR_INTEGRITY_OFFSET = 4
TARGET_ASAR_NAME = app.asar
PATCH_ZIP_NAME = Patch.zip
TIME_DIFF_THRESHOLD_DAYS = 730
[files]
CHECK_FILES_FOR_UPDATE =
    data/others/craftmincho.ttf
    tyrano/lang.js
STABLE_FILES_FOR_VALIDATION =
    index.html
    main.js
    package.json
```

适配其他游戏：修改以上配置 + 提供 `Patch.zip`（保持 ASAR 内部的相对目录结构），并验证目标游戏版本。文件列表逐行填写实际路径；详见 [PLUGIN_GUIDE.md](PLUGIN_GUIDE.md)。

---

## ⚠️ 版权与许可

本项目严格遵守原作者 **ばやちゃお (Bayachao)** 的《二次创作与同人活动指南》。
- **非营利**：仅限非营利目的使用，严禁用于商业用途。
- **素材使用**：本工具/补丁仅包含运行所需的翻译文件、注入代码和工具逻辑，**不包含任何游戏本体**。
- **版权归属**：游戏的所有权利（原作、设计、人物、剧情等）均归 **ばやちゃお** 所有。

**参考**：[原作者二次创作指南](https://bayachao.com/devil-connection/guideline)
**许可证**：[CC BY-NC-SA 4.0](https://creativecommons.org/licenses/by-nc-sa/4.0/)
