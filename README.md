# Devil Connection Localization Tool / 恶魔链接本地化工具

![Status](https://img.shields.io/badge/Status-Stable-green?style=flat-square)
![Platform](https://img.shields.io/badge/Platform-Win%20|%20Mac%20|%20Linux-blue?style=flat-square)
![License](https://img.shields.io/badge/License-CC%20BY--NC--SA%204.0-lightgrey?style=flat-square)
![Build](https://img.shields.io/badge/Build-Automated-success?style=flat-square)

> **By KouzakiUmi (呜咪 / 神前海)**

---

## 🇨🇳 中文

本项目是《恶魔链接（でびるコネクション）》的非营利性个人本地化工具。
采用全图形化界面 (GUI)，支持 Windows/macOS/Linux，集成了强大的存档管理与开发者工具。

**✨ 核心功能：**

| 功能 | 描述 |
|------|------|
| 🚀 **全自动补丁安装** | 图形化界面一键安装，自动备份，自动/手动移除游戏完整性校验 (Fuse) |
| 💾 **专业存档管理** | 独立于游戏目录的安全备份位置，支持自定义目录与平滑迁移，一键备份/还原/ZIP |
| 🛠️ **开发者工具箱** | 内置 Asar 解包/打包工具，支持跨平台格式选择与自定义 Fuse 偏移量修改 |
| ⚙️ **独立配置系统** | 支持热重载与合法性验证，自动隔离用户配置与内置模板，保障长期运行稳定 |
| 🔒 **操作保护** | 智能并发锁、备份迁移确认、Hash 安全校验，多重保障确保数据万无一失 |
| 🌐 **多语言支持** | 内置中文/英文/日文，运行时自由切换，无需重启 |

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
- `DevilConnection_Patch.exe` - 汉化补丁版（仅当 Patch/ 目录存在时生成）

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
python -m PyInstaller -F --clean \
    --add-data "tools/node.exe:tools" \
    --add-data "tools/bundled_asar:tools/bundled_asar" \
    --add-data "tools/asar_cli.mjs:tools" \
    --add-data "config.ini:." \
    --add-data "utils/language.py:utils" \
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

## 🛠️ For Developers / 开发者与高级功能 / 技術情報

> 💡 **重要提醒**：所有架构细节、工作流与技术规范，请参见最新的 [项目规范与技术参考 (PROJECT_SPECS.md)](./PROJECT_SPECS.md)。

### ⚙️ 配置文件体系与隔离
配置现采用**用户偏好与出厂预设双隔离模式**：
- **`~/.tyranopatcher/config.ini`**（优先加载）：系统在首次启动时，会自动将内置的默认配置拷贝至该位置持久保存。
- **配置管理**：开发者工具界面中自带“验证配置”与“重置默认”功能。随时可验证你的配置文件是否存在缺失键值或者非法语法的异常。

### 🔧 移除 Fuse 完整性限制 (动态架构)
由于 TyranoV8 等版本可能随着底层 Electron 版本的更迭而调整 Fuse 布局：
- 您现可以在 `开发者工具` -> `配置管理` -> `修改 Fuse 偏移` 处**动态改变偏移值（默认：4）**，此值将实时写入您的 `config.ini` 并立刻生效。
- 所有操作都会伴有危险警告以及强制的本地文件存在检查，从根本上防止误操作。

### 🏗️ Project Architecture / 项目架构 / プロジェクト構成

```
main.py (入口)
├── argparse (参数解析)
├── GUI Mode (Tkinter UI)
└── Batch Mode (--batch CLI)

    │
    ├── core/            │  gui/                │  utils/
    │   ├── patcher.py│  │  └── main_window.py  │  ├── language.py
    │   └── config.py │                         │  ├── paths.py
    │                 │                         │  ├── file_ops.py
    │                 │                         │  └── logging.py
    │
    └── tools/
        ├── node.exe
        ├── asar_cli.mjs
        └── bundled_asar/
```

### 📁 Directory Structure / 目录结构 / ディレクトリ構造

```
├── main.py              # 程序入口，支持 --batch 批处理模式和 GUI 模式
├── config.ini           # 全局配置文件，定义游戏参数和文件校验列表
├── Pack.cmd             # Windows 构建脚本，使用 PyInstaller 打包
│
├── core/                # 核心模块
│   ├── patcher.py       # 核心逻辑类 CoreLogic，包含所有补丁操作函数
│   └── config.py        # 配置管理类 AppConfig，封装 ConfigParser
│
├── gui/                 # 图形界面模块
│   └── main_window.py   # 主窗口类 App(tk.Tk)，包含所有 UI 组件
│
├── utils/               # 工具模块
│   ├── language.py      # 多语言系统，支持 CN/EN/JP 三种语言
│   ├── file_ops.py      # 文件操作模块（包含 Hash 校验与安全迁移）
│   ├── logging.py       # 日志系统配置
│   └── paths.py         # 路径处理，支持 PyInstaller 打包后的资源路径
│
├── tools/               # 内置运行时工具
│   ├── node.exe         # Windows 内置 Node.js 运行时
│   ├── asar_cli.mjs     # ASAR 文件操作 CLI 工具
│   └── bundled_asar/    # ASAR Node.js 依赖库
│       └── index.mjs    # ASAR 核心库
│
├── Patch/               # 汉化补丁数据目录（可选）
│   ├── data/
│   │   ├── scenario/    # 剧情脚本文件
│   │   ├── others/      # 游戏资源文件
│   │   └── image/       # 图片资源
│   └── tyrano/
│       └── lang.js      # 语言配置文件
```

### ⚙️ Configuration File / 配置文件详解 / 設定ファイル

`config.ini` 是项目的全局配置文件，使用 INI 格式：

```ini
[main]
# 游戏可执行文件名
AUTO_TARGET_EXE = DevilConnection.exe
# Fuse 校验特征码（用于完整性校验移除）
FUSE_SENTINEL = dL7pKGdnNz796PbbjQWNKmHXBZaB9tsX
# Fuse 协议头部长度与验证偏移索引（供更换 Electron 引擎时动态调整）
FUSE_WIRE_HEADER_LENGTH = 34
FUSE_ASAR_INTEGRITY_OFFSET = 4
# 备份文件名前缀
BACKUP_PREFIX = Backup_
# 补丁信息文件名
PATCH_INFO_FILE = .patch_info
# 补丁元数据文件名
PATCH_META_FILE = .patch_meta
# 旧补丁时间阈值（天），超过此值提示用户
TIME_DIFF_THRESHOLD_DAYS = 3
# 资源目录名称
RESOURCE_DIR = resources
# 程序名称
APP_NAME = TyranoV8_Patcher

[files]
# Steam更新检测文件列表
# 这些文件在补丁中会被修改，如果Steam更新了游戏，哈希会变化
CHECK_FILES_FOR_UPDATE =
    data/others/craftmincho.ttf
    data/others/DZUYOKU.ttf
    data/others/funwari-round.ttf
    data/others/HeadUpDaisy.ttf
    tyrano/lang.js

# 稳定文件列表（用于验证备份完整性）
STABLE_FILES_FOR_VALIDATION =
    index.html      # 入口HTML
    main.js         # Electron主进程
    package.json    # 包配置
    steam.js        # Steam集成
    preload.js      # 预加载脚本
    electron_latest.js
```

### 🔄 Execution Flow / 运行逻辑 / 実行フロー

#### GUI 模式流程
```
main.py -> App.__init__() -> init_ui()

标签页:
  [补丁安装]     [存档管理]      [开发者工具]
  1.检查ASAR     1.扫描存档      ASAR解包/打包
  2.创建备份     2.备份/还原     Fuse移除
  3.解包ASAR     3.ZIP压缩      跨平台选择
  4.应用补丁     4.异步操作
  5.重新打包
  6.保存元数据
```

#### 批处理模式流程 (`--batch --auto`)
```
main.py --batch --auto
  -> handle_steam_update()  (Steam更新检测)
  -> shutil.copy2(asar, bak)  (创建备份)
  -> core.run_asar("extract")  (解包ASAR)
  -> shutil.copytree(Patch, temp)  (应用补丁)
  -> core.run_asar("pack")  (重新打包)
  -> save_patch_info() + save_patch_meta()  (保存元数据)
```

#### Steam 更新检测状态机
```
handle_steam_update() 状态:

情况4: ASAR不存在 + 备份不存在
  -> 文件损坏，报错退出

情况3: ASAR不存在 + 备份存在
  -> Steam更新，自动恢复备份

情况1: ASAR存在 + 备份不存在
  -> 首次打补丁，验证ASAR后继续

情况2: ASAR存在 + 备份存在
  -> 检查.patch_info文件状态
  -> 损坏/过期 -> 提示用户 -> 继续或退出
  -> 正常 -> 继续打补丁
```

### 🛠️ Core Components / 核心组件 / コアコンポーネント

#### CoreLogic 类 (`core/patcher.py`)
核心逻辑类，负责所有底层操作：

| 方法 | 功能 |
|------|------|
| `__init__()` | 初始化，验证 Node.js 和 ASAR CLI 是否存在 |
| `run_asar(action, src, dest)` | 执行 ASAR 解包/打包操作 |
| `remove_fuse(exe_path)` | 移除游戏 Fuse 完整性校验 |
| `_find_script()` | 查找 ASAR CLI 脚本 |

#### App 类 (`gui/main_window.py`)
主窗口类，继承 `tk.Tk`：

| 组件 | 说明 |
|------|------|
| `tab_patch` | 补丁安装界面（仅当存在内置补丁时显示） |
| `tab_save` | 存档管理器，包含备份/还原/删除功能 |
| `tab_tools` | 开发者工具箱，ASAR 操作和 Fuse 移除 |
| `log_area` | 日志显示区域（ScrolledText） |
| `progress` | 进度条（indeterminate 模式） |

#### 多语言系统 (`utils/language.py`)

项目使用完整的多语言支持系统，支持 **简体中文 (cn)**、**English (en)**、**日本語 (jp)** 三种语言。

##### 语言检测优先级

```
语言检测流程:

1. Windows 系统 -> GetUserDefaultUILanguage() API
   - 2052 (中文)    -> 'cn'
   - 1041 (日语)    -> 'jp'
   - 其他           -> 'en'

2. 其他系统 -> 环境变量 LANG
   - 包含 'zh'/'cn'/'tw' -> 'cn'
   - 包含 'ja'           -> 'jp'
   - 其他                -> 'en'
```

##### GUI 语言切换

通过菜单栏实时切换语言，无需重启程序：

```
菜单栏 (Menu)
    └── 语言 (Language)
          ├── English
          ├── 简体中文
          └── 日本語
```

##### 用户偏好持久化

用户语言设置保存在：
- **Windows**: `%APPDATA%/tyrano_patcher.ini`
- **Linux/Mac**: `~/.config/tyrano_patcher.ini`

```ini
[preferences]
language = cn
platform = win
use_zip = true
```

### 🔧 Build Process / 构建流程 / ビルドプロセス

#### 🤖 自动构建

推送到 main 分支会自动触发 GitHub Actions 构建：
- 构建 Windows 可执行文件
- 生成 nightly 版本标签
- 发布到 [Releases](../../releases)

#### 💻 本地构建

```cmd
# 确保前置条件
# 1. 安装 Python
# 2. pip install pyinstaller
# 3. 确保 tools/ 目录包含 node.exe 和 bundled_asar/

.\Pack.cmd
```

构建脚本执行以下操作：

```
Pack.cmd 执行流程:

1. 前置检查
   - tools/node.exe 存在?
   - tools/bundled_asar/ 存在?
   - tools/asar_cli.mjs 存在?
   - Python 可用?
   - PyInstaller 安装?

2. 任务A: 构建纯净工具箱 (Tyrano_Toolbox.exe)
   - 不包含 Patch/ 目录

3. 任务B: 构建汉化补丁 (DevilConnection_Patch.exe)
   - 仅当 Patch/ 目录存在且非空时构建

4. 清理
   - 删除 build_toolbox/
   - 删除 build_patcher/
   - 删除 *.spec 文件

输出:
   - dist/Tyrano_Toolbox.exe
   - dist/DevilConnection_Patch.exe (可选)
```

#### macOS / Linux 构建

```bash
# 安装依赖
pip install pyinstaller

# 构建工具箱
python -m PyInstaller -F --clean \
    --distpath "dist" \
    --add-data "tools/node.exe:tools" \
    --add-data "tools/bundled_asar:tools/bundled_asar" \
    --add-data "tools/asar_cli.mjs:tools" \
    --add-data "config.ini:." \
    --add-data "utils/language.py:utils" \
    --name "Tyrano_Toolbox" \
    main.py

# 构建包含补丁的版本（需要同时存在 Patch/ 目录）
python -m PyInstaller -F --clean \
    --distpath "dist" \
    --add-data "tools/node.exe:tools" \
    --add-data "tools/bundled_asar:tools/bundled_asar" \
    --add-data "tools/asar_cli.mjs:tools" \
    --add-data "config.ini:." \
    --add-data "utils/language.py:utils" \
    --add-data "Patch:Patch" \
    --name "DevilConnection_Patch" \
    main.py
```

### 🐛 Debugging / 调试技巧 / デバッグ

#### 查看日志
```bash
# 默认日志位置
# Windows: %USERPROFILE%\.tyranopatcher\tyrano_patcher.log
# Linux/Mac: ~/.tyranopatcher/tyrano_patcher.log

# 自定义日志文件
python main.py --log-file /path/to/custom.log
```

#### 批处理模式调试
```bash
# 查看详细输出
python main.py --batch --auto --verbose

# 仅移除Fuse
python main.py --batch --fuse DevilConnection.exe
```

#### CLI 参数说明
```
main.py [-h] [--batch] [--auto] [--fuse FILE] [--log-file PATH] [-v] [-q]

选项:
  --batch         批处理模式（无 GUI）
  --auto          自动检测并打补丁
  --fuse FILE     移除指定文件的 Fuse 校验
  --log-file PATH 自定义日志文件路径
  -v, --verbose   启用详细输出
  -q, --quiet     抑制非错误输出
```

#### 常见问题排查
| 问题 | 解决方案 |
|------|----------|
| `Node.js not found` | 检查 tools/node.exe 是否存在 |
| `ASAR operation failed` | 使用 `--verbose` 查看详细错误 |
| `Permission denied` | 以管理员权限运行 |
| `Backup corrupted` | 通过 Steam 验证游戏完整性 |

### 📝 Patching Workflow / 完整打补丁流程 / パッチ適用ワークフロー

```
打补丁流程:

用户点击"开始安装"
  -> 检查 Steam 更新 -> 有更新? -> 询问用户/恢复备份
  -> 创建备份 (app.asar -> app.asar.bak)
  -> 解包 ASAR -> temp_patch/
  -> 复制补丁文件 (Patch/* -> temp_patch/)
  -> 重新打包 ASAR (temp_patch/ -> app.asar)
  -> 保存元数据
  -> 清理临时文件 (.patch_info, .patch_meta)
  -> 清理临时目录
  -> 安装完成
```

---

## ⚠️ Rights & License / 版权与许可 / 権利とライセンス

### 🇨🇳 中文
本项目严格遵守原作者 **ばやちゃお (Bayachao)** 的《二次创作与同人活动指南》。
- **非营利**：仅限非营利目的使用，严禁用于商业用途。
- **素材使用**：本补丁仅包含运行所需的翻译文件与代码，**不包含游戏本体**。
- **版权归属**：游戏的所有权利（原作，设计，人物等）均归 **ばやちゃお** 所有。

- **参考链接：** [原作者 Guideline](https://bayachao.com/devil-connection/guideline)
- **许可证**：[CC BY-NC-SA 4.0](https://creativecommons.org/licenses/by-nc-sa/4.0/deed.zh)

### 🇺🇸 English
This project strictly adheres to the "Derivative Works Guidelines" set by the original author, **Bayachao**.
- **Non-Commercial**: For non-profit, educational purposes only. Commercial use is strictly prohibited.
- **Assets**: Contains only necessary translation files and injection code. **Does not distribute the full game**.
- **Ownership**: All rights to the original game, designs, and characters belong to **Bayachao**.

**Reference:** [Author's Guideline](https://bayachao.com/devil-connection/guideline)
- **License**: [CC BY-NC-SA 4.0](https://creativecommons.org/licenses/by-nc-sa/4.0/)

### 🇯🇵 日本語
本プロジェクトは，原作者 **ばやちゃお** 様の「二次創作・同人活動可能範囲」および「翻訳パッチの作成について」の規定を厳守して作成されています。
- **非营利**: 非营利目的での利用に限ります。营利目的での利用は固く禁じられています。
- **素材の利用**: 本パッチは翻訳および導入に必要なファイルのみを含んでおり、**ゲーム本体は含まれません**。
- **権利の帰属**: 原作、デザイン、キャラクター等のすべての権利は **ばやちゃお** 様に帰属します。

**参照リンク:** [二次創作ガイドライン](https://bayachao.com/devil-connection/guideline)
- **ライセンス**: [CC BY-NC-SA 4.0](https://creativecommons.org/licenses/by-nc-sa/4.0/deed.ja)
