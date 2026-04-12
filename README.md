# Tyrano补丁工具箱

**でびるコネクション汉化补丁是自带示例作品。**

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

**开发者说明**：本工具箱为通用 **Tyrano补丁工具**，`でびるコネクション` 汉化补丁为自带示例。通过**修改 `config.ini`**（AUTO_TARGET_EXE、FUSE_SENTINEL、CHECK_FILES_FOR_UPDATE 等）并替换 `patch.zip`（包含对应游戏的汉化文件ZIP），即可适配其他 Tyrano/Electron 游戏。详见 [PLUGIN_GUIDE.md](PLUGIN_GUIDE.md)。

---

## 🇨🇳 中文

本项目起源是《恶魔连接（でびるコネクション）》的非营利性个人本地化工具。
采用全图形化界面 (GUI)，支持 Windows/macOS/Linux，集成了强大的存档管理与开发者工具。现已更新为通用工具箱。

**✨ 核心功能：**

| 功能 | 描述 |
|------|------|
| 🚀 **全自动补丁安装** | 图形化界面一键安装，自动备份，自动/手动移除游戏完整性校验 (Fuse) |
| 💾 **专业存档管理** | 独立于游戏目录的安全备份位置，支持自定义目录与平滑迁移，一键备份/还原/ZIP |
| 🛠️ **开发者工具箱** | 内置 Asar 解包/打包工具，支持跨平台格式选择与自定义 Fuse 偏移量修改 |
| ⚙️ **独立配置系统** | 支持热重载与合法性验证，自动隔离用户配置与内置模板，保障长期运行稳定 |
| 🔒 **操作保护** | 智能并发锁、备份迁移确认、Hash 安全校验，多重保障确保数据万无一失 |
| 🌐 **多语言支持** | 内置中文/英文/日文，运行时自由切换，无需重启 |
| 📚 **API 文档** | 提供了自动生成的项目 API 手册 [API_DOCS.md](API_DOCS.md) 供开发者参考 |

---

## 📥 Installation / 安装 / インストール

### 🚀 自动构建版（推荐）

每次推送到 main 分支会自动构建，下载最新版本：
- 前往 [Releases](../../releases) 下载 `DevilConnection_Patch.exe` 或 `Tyrano_Toolbox.exe`

### 🏁 Windows（从源码构建）

```cmd
git clone <repo-url>
cd repo-path
.\Pack.cmd
```

构建产物位于 `dist/` 目录：
- `Tyrano_Toolbox.exe` - 纯净工具箱
- `DevilConnection_Patch.exe` - 游戏汉化补丁版（仅当 Patch/ 目录存在时生成）

---

### 🍎 macOS / 🐧 Linux

**前置要求**
- Python 3.8+
- Node.js 18+

**安装步骤**
```bash
# 1. 克隆项目
git clone <repo-url>
cd <repo-path>

# 2. 安装依赖
pip install pyinstaller

# 3. 运行程序
python main.py
```

**跨平台构建**
```bash
# macOS / Linux 上构建 Windows 可执行文件（需要 wine）
pip install pyinstaller
python -m PyInstaller -F -w --clean \
    -i "icon.ico" \
    --add-data "icon.ico:." \
    --add-data "tools/node.exe:tools" \
    --add-data "tools/bundled_asar:tools\bundled_asar" \
    --add-data "tools/asar_cli.mjs:tools" \
    --add-data "config.ini:." \
    --name "DevilConnection_Patch" \
    main.py
```

---

## 💾 Save Manager / 存档管理 / セーブ管理

### 🇨🇳 功能介绍
工具内置了**专业级存档管理系统**（`Save Manager` 标签页），让您再也不怕存档丢失：

#### 🔄 工作流程
```
🎮 游戏运行 → 🔍 自动扫描 → 📋 列表显示 → 💾 一键备份 → ✅ 安全还原
```

#### 核心功能
- **🔍 自动扫描**：智能识别 `_storage` 或 `save` 文件夹
- **💾 快速备份**：点击 **"➕ 新建备份"**，自动生成带**年月日时分秒**时间戳的快照
  - 默认独立存储于 `~/.tyranopatcher/backups`，即使重新安装游戏甚至覆盖目录，存档均不会丢失
  - 支持**平滑迁移**：更改备份存放目录时可自动同步以前的数据（全程经过 Hash 校验，安全可靠）
  - 支持**文件夹备份**和 **ZIP 压缩备份**（推荐开启，节省空间）
  - 备份类型在列表中清晰显示 `[ZIP]` 或 `[DIR]`
- **↩️ 瞬间还原**：选中历史备份，点击 **"还原选中"** 一秒回档
  - 还原前自动弹出确认框，防止误操作覆盖当前进度
  - 异步操作，不卡顿游戏窗口
- **🗑️ 灵活删除**：可随时清理不需要的旧备份，释放存储空间
- **🔒 多重保护**：并发锁机制防止同时运行多个操作，确保数据完整性

---

## 🛠️ 开发者工具箱与高级功能

> 💡 **重要提醒**：所有架构细节、工作流与技术规范，请参见最新的 [项目规范与技术参考 (PROJECT_SPECS.md)](./PROJECT_SPECS.md)。

### ⚙️ 配置文件体系与隔离
配置现采用**用户偏好与出厂预设双隔离模式**：
- **`~/.tyranopatcher/config.ini`**（优先加载）：系统在首次启动时，会自动将内置的默认配置拷贝至该位置持久保存。
- **配置管理**：开发者工具界面中自带“验证配置”与“重置默认”功能。随时可验证你的配置文件是否存在缺失键值或者非法语法的异常。

### 🔧 Fuse移除与配置动态化
TyranoV8/Electron版本迭代可能改变Fuse布局。开发者工具箱 -> 配置管理 -> 修改Fuse偏移（默认4，可配置`FUSE_ASAR_INTEGRITY_OFFSET`）支持动态调整，值实时保存到用户`config.ini`并生效。所有危险操作均有警告、文件存在检查和Hash保护。

### 📁 项目架构（基于代码全面分析更新，纯中文描述）

- **入口**：`main.py` — 参数解析、init_lang、bootstrap_system（配置/路径/状态检查）、GUI (`gui/main_window.py` + `tabs/*`) 或 batch模式。
- **core/**：`bootstrap.py`（系统引导）、`patcher.py`（CoreLogic，延迟`import asar`进行extract/create_archive）、`config.py`（单例、用户`~/.tyranopatcher/config.ini`优先、snapshot+TTL热重载、fallback如`TARGET_ASAR_NAME=app.asar`、`PATCH_ZIP_NAME=Patch.zip`）、`steam.py`+`state_validator.py`（4种ASAR/备份/patch_meta状态机 + 纯Python哈希验证）、`save_service.py`、`fuse.py`（可配置偏移）、`patch_info.py`（原子`_atomic_write_json`）、`batch.py`。
- **gui/**：`main_window.py`（tab管理、log/progress）、`tabs/patch_tab.py`、`save_tab.py`、`tools_tab.py`（ASAR/Fuse/配置UI）。
- **controllers/**：业务逻辑分离（`patch_controller.py`封装Steam处理+patch流程、`save_manager_controller.py`）。
- **utils/**：`language.py`（系统语言优先级+菜单切换+INI持久化）、`paths.py`（PyInstaller _MEIPASS兼容）、`async_ops.py`（ThreadPool+取消）、`file_ops.py`（hash/migrate）、`cleanup.py`、`logging.py`（RotatingFile）、`asar_utils.py`（纯Python校验）、`validators.py`、`constants.py`、`performance.py`。
- **打包脚本**：`Pack.cmd`/`Pack.sh` — 检查Python/PyInstaller、构建`Tyrano_Toolbox`、`if Patch.zip or Patch/`则压缩为Patch.zip（提升启动性能并清理原目录）、构建带补丁的`DevilConnection_Patch`、清理build/和.spec。**当前无node.exe/bundled_asar依赖**，依赖`asar`包（build时pip install）。

**config.ini模板关键项**（用户副本优先，可热重载验证）：
```ini
[main]
AUTO_TARGET_EXE = DevilConnection.exe
FUSE_SENTINEL = dL7pKGdnNz796PbbjQWNKmHXBZaB9tsX
FUSE_ASAR_INTEGRITY_OFFSET = 4
TARGET_ASAR_NAME = app.asar
PATCH_ZIP_NAME = Patch.zip
TIME_DIFF_THRESHOLD_DAYS = 730
[files]
CHECK_FILES_FOR_UPDATE = data/others/*.ttf, tyrano/lang.js
STABLE_FILES_FOR_VALIDATION = index.html, main.js, package.json ...
```

适配其他游戏：修改以上配置 + 替换`patch.zip`（保持游戏目录结构）。详见PLUGIN_GUIDE.md。


（架构与配置细节已在上文纯中文更新中覆盖，详见PROJECT_SPECS.md。后续执行流、核心组件、构建流程等已整合到架构描述中，避免重复。调试和常见问题见PACK.md和工具箱的内置日志/验证功能。Node.js相关已过时移除。）

---

## ⚠️ 版权与许可

本项目严格遵守原作者 **ばやちゃお (Bayachao)** 的《二次创作与同人活动指南》。
- **非营利**：仅限非营利目的使用，严禁用于商业用途。
- **素材使用**：本工具/补丁仅包含运行所需的翻译文件、注入代码和工具逻辑，**不包含任何游戏本体**。
- **版权归属**：游戏的所有权利（原作、设计、人物、剧情等）均归 **ばやちゃお** 所有。

**参考**：[原作者二次创作指南](https://bayachao.com/devil-connection/guideline)
**许可证**：[CC BY-NC-SA 4.0](https://creativecommons.org/licenses/by-nc-sa/4.0/)

**三语文档**：本`README.md`为纯中文版本（包含开发者说明、标题更新和基于代码全面分析的完善内容）。请通过顶部醒目超链接跳转到纯英文的[README_en.md](README_en.md)和纯日文的[README_ja.md](README_ja.md)，每个独立文件仅使用自身语言并高亮当前语言。

---

**文档更新总结**：全面分析了项目所有代码和打包脚本（Pack.cmd/Pack.sh的条件构建、Patch.zip自动压缩逻辑）、运行流程（bootstrap检查、steam状态机4种情况、CoreLogic的asar操作、config热重载与用户目录隔离、原子写入patch_info/meta、gui tabs分离、纯Python ASAR校验等）。修复了所有MD中的过时信息（旧架构、node依赖、旧config示例、旧构建命令），添加了开发者适配说明。现在所有文档准确反映当前实现，并相互一致。其他文档（如PROJECT_SPECS.md、PLUGIN_GUIDE.md、PACK.md、UTILS_GUIDE.md、API_DOCS.md）也已同步更新标题和内容。
