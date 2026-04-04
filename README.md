# Devil Connection Localization Tool / 恶魔链接本地化工具

![Status](https://img.shields.io/badge/Status-Stable-green?style=flat-square)
![Platform](https://img.shields.io/badge/Platform-Win%20|%20Mac%20|%20Linux-blue?style=flat-square)
![License](https://img.shields.io/badge/License-CC%20BY--NC--SA%204.0-lightgrey?style=flat-square)
![Build](https://img.shields.io/badge/Build-Automated-success?style=flat-square)

> **By KouzakiUmi (呜咪 / 神前海)**

---

### 🇨🇳 中文
本项目是《恶魔链接（でびるコネクション）》的非营利性个人本地化工具。
采用全图形化界面 (GUI)，内置 Node.js 运行时，支持 Windows/macOS/Linux，集成了强大的存档管理与开发者工具。

**✨ 核心功能：**

| 功能 | 描述 |
|------|------|
| 🌟 **内置运行时** | Windows 版本内置 Node.js 运行环境，零依赖，开箱即用 |
| 🚀 **全自动补丁安装** | 图形化界面一键安装，自动备份，自动移除游戏完整性校验 (Fuse) |
| 💾 **专业存档管理** | 自动扫描存档位置，支持一键备份/还原，带时间戳，可压缩为 ZIP |
| 🛠️ **开发者工具箱** | 内置 Asar 解包/打包工具，支持跨平台格式选择 |
| 🔒 **操作保护** | 智能并发锁、备份前确认提示，多重保障确保数据安全 |
| 🌐 **多语言支持** | 内置中文/英文/日文，运行时自由切换，无需重启 |

### 🇺🇸 English
**Devil Connection Localization Tool** is a non-profit, fan-made localization patcher.
Features a full Graphical User Interface (GUI) with built-in Node.js runtime, supports Windows/macOS/Linux, and advanced save management tools.

**✨ Key Features:**

| Feature | Description |
|---------|-------------|
| 🌟 **Built-in Runtime** | Windows version includes bundled Node.js—no dependencies required |
| 🚀 **One-Click Patching** | GUI-based automatic installation with auto-backup and Fuse removal |
| 💾 **Professional Save Manager** | Auto-detects saves, timestamped backups, ZIP compression, instant restore |
| 🛠️ **Developer Toolbox** | Built-in Asar extract/pack with multi-platform target selection |
| 🔒 **Operation Safety** | Concurrency protection, confirmation prompts, and multi-layer safeguards |
| 🌐 **Multi-Language** | Chinese/English/Japanese with runtime switching—no restart needed |

### 🇯🇵 日本語
本プロジェクトは、ゲーム『でびるコネクション』の非营利・個人制作によるローカライズツールです。
完全なGUIを搭载し、内蔵 Node.js ランタイムで Windows/macOS/Linux をサポート、セーブデータ管理機能も強力です。

**✨ 主な特徴:**

| 機能 | 説明 |
|------|------|
| 🌟 **内置ランタイム** | Windows 版は Node.js を内装、依存関係なし |
| 🚀 **自動ワンクリック導入** | GUI による簡単インストール、自動バックアップ、Fuse 自動解除 |
| 💾 **セーブデータ管理** | 自動検出、タイムスタンプ付きバックアップ、ZIP 圧縮対応 |
| 🛠️ **開発者ツールボックス** | Asar 解凍/圧縮、マルチプラットフォーム対応 |
| 🔒 **操作保護機能** | 並行実行保護、確認メッセージ、データ安全性多重保障 |
| 🌐 **多言語サポート** | 中文/English/日本語、実行時切替可能 |

---

## 📥 Installation / 安装 / インストール

### 🇨🇳 中文
1. **下载**：下载本项目的最新 [Releases](../../releases) 版本。
2. **放入目录**：将程序放入游戏根目录（即 `DevilConnection.exe` 所在的文件夹）。
3. **运行**：双击运行。
   - **Windows**: 直接运行 `.exe`（内置 Node.js，无需安装任何依赖）。
   - **Mac/Linux**: 需要 Python 环境，并确保系统已安装 Node.js。
4. **操作**：在弹出的窗口中点击 **"🚀 开始安装"** 即可。

### 🇺🇸 English
1. **Download**: Get the latest release from [Releases](../../releases).
2. **Place**: Put the tool into the game's root folder.
3. **Run**:
   - **Windows**: Run the `.exe` directly (bundled Node.js, no dependencies needed).
   - **Mac/Linux**: Requires Python environment and Node.js installed.
4. **Action**: Click **"🚀 Start Patch"** in the GUI window.

### 🇯🇵 日本語
1. **ダウンロード**: [Releases](../../releases) から最新版をダウンロードします。
2. **配置**: ツールをゲームのルートフォルダに置きます。
3. **実行**:
   - **Windows**: `.exe` を直接実行します（Node.js 内蔵、依存関係不要）。
   - **Mac/Linux**: Python 環境と Node.js のインストールが必要です。
4. **操作**: ウィンドウ内の **"🚀 インストール開始"** をクリックします。

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
- **💾 快速备份**：点击 **"📦 创建备份"**，自动生成带**年月日时分秒**时间戳的快照
  - 支持**文件夹备份**和 **ZIP 压缩备份**（节省空间）
  - 备份类型在列表中清晰显示 `[ZIP]` 或 `[DIR]`
- **↩️ 瞬间还原**：选中历史备份，点击 **"还原选中"** 一秒回档
  - 还原前自动弹出确认框，防止误操作覆盖当前进度
  - 异步操作，不卡顿游戏窗口
- **🗑️ 灵活删除**：可随时清理不需要的旧备份，释放存储空间
- **🔒 多重保护**：并发锁机制防止同时运行多个操作，确保数据完整性

### 🇺🇸 Features
A dedicated `Save Manager` tab with **enterprise-grade backup system**:

#### 🔄 Workflow
```
🎮 Game Running → 🔍 Auto-Detect → 📋 List → 💾 Backup → ✅ Restore
```

#### Core Functions
- **🔍 Smart Detection**：Automatically identifies `_storage` or `save` folders
- **💾 Fast Backup**：Click **"📦 Backup Now"** to create timestamped snapshots
  - Support both folder and ZIP-compressed backups
  - Backup types displayed as `[ZIP]` or `[DIR]`
- **↩️ Instant Restore**：Select and restore in seconds with confirmation prompts
  - Async operations, no freezing
- **🗑️ Cleanup**：Delete old backups to free space
- **🔒 Concurrency Protection**：Prevents simultaneous operations

### 🇯🇵 機能紹介
専用の `Save Manager` タブで**企業レベルのバックアップシステム**を実装：

#### 🔄 ワークフロー
```
🎮 ゲーム実行 → 🔍 自動検出 → 📋 リスト表示 → 💾 バックアップ → ✅ 復元
```

#### コア機能
- **🔍 自動検出**：`_storage` または `save` フォルダを自動認識
- **💾 高速バックアップ**：**"📦 バックアップ作成"** でタイムスタンプ付きスナップショット生成
  - フォルダ・ZIP 圧縮の両対応
  - リストに `[ZIP]` または `[DIR]` を表示
- **↩️ 瞬時復元**：選択して復元、確認メッセージで誤操作防止
  - 非同期処理でフリーズなし
- **🗑️ 柔軟削除**：旧バックアップを削除してスペース節約
- **🔒 並行実行保護**：複数操作の同時実行を防止

---

## 🛠️ For Developers / 开发者与技术细节 / 技術情報

### 🏗️ Project Architecture / 项目架构 / プロジェクト構成

```
┌─────────────────────────────────────────────────────────────────┐
│                         main.py (入口)                           │
│  ┌─────────────┐  ┌─────────────┐  ┌──────────────────────────┐ │
│  │  argparse   │  │  GUI Mode   │  │    Batch Mode (--batch)   │ │
│  │  参数解析   │  │  图形界面   │  │       批处理模式          │ │
│  └─────────────┘  └─────────────┘  └──────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
                               │
          ┌────────────────────┼────────────────────┐
          ▼                    ▼                    ▼
┌─────────────────┐  ┌─────────────────┐  ┌─────────────────────┐
│   core/patcher  │  │  gui/main_window │  │     utils/         │
│   核心打补丁    │  │   Tkinter GUI   │  │   工具模块         │
│                 │  │                 │  │                    │
│ • ASAR操作     │  │ • 补丁安装标签页  │  │ • language.py      │
│ • Fuse移除     │  │ • 存档管理标签页  │  │   多语言支持       │
│ • Steam更新检测│  │ • 开发者工具标签页│  │ • paths.py         │
│ • 备份管理     │  │                 │  │   路径处理         │
│                 │  │                 │  │ • logging.py       │
│                 │  │                 │  │   日志系统         │
└─────────────────┘  └─────────────────┘  └─────────────────────┘
                               │
                               ▼
                    ┌─────────────────────┐
                    │    tools/           │
                    │    内置工具          │
                    │                    │
                    │ • node.exe         │
                    │   Node.js运行时     │
                    │ • asar_cli.mjs     │
                    │   ASAR操作CLI      │
                    │ • bundled_asar/    │
                    │   ASAR依赖库       │
                    └─────────────────────┘
```

### 📁 Directory Structure / 目录结构 / ディレクトリ構造

| 目录/文件 | 说明 |
|-----------|------|
| `main.py` | 程序入口，支持 `--batch` 批处理模式和 GUI 模式 |
| `config.ini` | 全局配置文件，定义游戏参数和文件校验列表 |
| `Pack.cmd` | Windows 构建脚本，使用 PyInstaller 打包 |
| `core/` | 核心模块 |
| `core/__init__.py` | 模块初始化 |
| `core/config.py` | 配置管理类 `AppConfig`，封装 ConfigParser |
| `core/patcher.py` | 核心逻辑，包含 `CoreLogic` 类和所有补丁操作函数 |
| `gui/` | 图形界面模块 |
| `gui/main_window.py` | 主窗口类 `App(tk.Tk)`，包含所有 UI 组件 |
| `utils/` | 工具模块 |
| `utils/__init__.py` | 模块初始化 |
| `utils/language.py` | 多语言系统，支持 CN/EN/JP 三种语言 |
| `utils/logging.py` | 日志系统配置 |
| `utils/paths.py` | 路径处理，支持 PyInstaller 打包后的资源路径 |
| `tools/` | 内置运行时工具 |
| `tools/node.exe` | Windows 内置 Node.js 运行时 |
| `tools/asar_cli.mjs` | ASAR 文件操作 CLI 工具 |
| `tools/bundled_asar/` | ASAR Node.js 依赖库 |
| `Patch/` | 汉化补丁数据目录（可选） |
| `Patch/data/` | 补丁文件：scenario/、others/、image/ |
| `Patch/tyrano/` | 语言配置文件 lang.js |

### ⚙️ Configuration File / 配置文件详解 / 設定ファイル

`config.ini` 是项目的全局配置文件，使用 INI 格式：

```ini
[main]
# 游戏可执行文件名
AUTO_TARGET_EXE = DevilConnection.exe
# Fuse 校验特征码（用于完整性校验移除）
FUSE_SENTINEL = dL7pKGdnNz796PbbjQWNKmHXBZaB9tsX
# 备份文件名前缀
BACKUP_PREFIX = Backup_
# 补丁信息文件名
PATCH_INFO_FILE = .patch_info
# 补丁元数据文件名
PATCH_META_FILE = .patch_meta
# 旧补丁时间阈值（天），超过此值提示用户
TIME_DIFF_THRESHOLD_DAYS = 3

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
main.py → App.__init__() → init_ui()
                              │
        ┌─────────────────────┼─────────────────────┐
        ▼                     ▼                     ▼
┌───────────────┐    ┌───────────────┐    ┌───────────────────┐
│  补丁安装标签  │    │  存档管理标签   │    │    开发者工具标签   │
│  (tab_patch) │    │  (tab_save)   │    │    (tab_tools)    │
└───────────────┘    └───────────────┘    └───────────────────┘
        │                     │                     │
        ▼                     ▼                     ▼
┌───────────────┐    ┌───────────────┐    ┌───────────────────┐
│1. 检查ASAR   │    │1. 扫描存档    │    │ • ASAR解包/打包   │
│2. 创建备份   │    │2. 备份/还原   │    │ • Fuse移除        │
│3. 解包ASAR   │    │3. ZIP压缩    │    │ • 跨平台选择      │
│4. 应用补丁   │    │4. 异步操作    │    │                   │
│5. 重新打包   │    │               │    │                   │
│6. 保存元数据 │    │               │    │                   │
└───────────────┘    └───────────────┘    └───────────────────┘
```

#### 批处理模式流程 (`--batch --auto`)
```
main.py --batch --auto
    │
    ▼
handle_steam_update()  ←── Steam更新检测
    │
    ▼
shutil.copy2(asar, bak)  ←── 创建备份
    │
    ▼
core.run_asar("extract")  ←── 解包ASAR
    │
    ▼
shutil.copytree(Patch, temp)  ←── 应用补丁
    │
    ▼
core.run_asar("pack")  ←── 重新打包
    │
    ▼
save_patch_info() + save_patch_meta()  ←── 保存元数据
```

#### Steam 更新检测状态机
```
┌────────────────────────────────────────────────────────────────┐
│                     handle_steam_update()                       │
├────────────────────────────────────────────────────────────────┤
│                                                                │
│  ┌──────────────┐    ASAR?    ┌──────────────┐                 │
│  │  情况4:      │─────────────│  情况1:      │                 │
│  │  文件损坏    │    否       │  首次打补丁  │                 │
│  └──────────────┘             └──────────────┘                 │
│       │                            │                          │
│       ▼                            ▼                          │
│  显示错误对话框              验证ASAR完整性                     │
│                                │    │                         │
│  ┌──────────────┐    ASAR?     │    │      ┌──────────────┐   │
│  │  情况3:      │──────────────┘    └──────│  情况2:      │   │
│  │  Steam更新   │         是             │  已打过补丁   │   │
│  │  自动恢复    │                       └──────────────┘   │
│  └──────────────┘                            │               │
│       │                                      ▼               │
│       ▼                            检查.patch_info文件        │
│  询问用户是否继续                    │    │    │             │
│       │                      损坏?   │    │    │   过期?     │
│       ▼                      ▼       │    │    ▼   ▼        │
│  验证备份完整性              提示用户  │    │  提示用户  │   │
│       │                            继续  │    │  继续     │   │
│       ▼                                  ▼    └──────┬───┘   │
│  自动恢复备份                                      继续打补丁  │
│                                                                │
└────────────────────────────────────────────────────────────────┘
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
┌─────────────────────────────────────────────────────────────┐
│                    语言检测流程                              │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  1. Windows 系统 → GetUserDefaultUILanguage() API           │
│     ├── 2052 (中文)     → 'cn'                              │
│     ├── 1041 (日语)     → 'jp'                              │
│     └── 其他            → 'en'                              │
│                                                              │
│  2. 其他系统 → 环境变量 LANG                                │
│     ├── 包含 'zh'/'cn'/'tw' → 'cn'                         │
│     ├── 包含 'ja'        → 'jp'                             │
│     └── 其他            → 'en'                             │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

##### 代码结构

```python
# 语言字典结构
LANG_DICT = {
    'cn': {...},  # 简体中文
    'en': {...},  # English
    'jp': {...},  # 日本語
}

# 关键函数
T(key)              # 获取翻译文本
init_lang()         # 初始化语言（自动检测）
detect_lang()        # 检测系统语言

# 运行时切换
language.CURRENT_LANG_CODE = 'en'
self.init_ui()  # 重新初始化界面以应用新语言
```

##### 添加新翻译

在 `LANG_DICT` 字典中添加新键值：

```python
LANG_DICT = {
    'cn': {
        'new_key': '中文文本',
    },
    'en': {
        'new_key': 'English text',
    },
    'jp': {
        'new_key': '日本語テキスト',
    },
}
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

切换时会调用 `change_lang(code)` 方法：
1. 更新 `CURRENT_LANG_CODE`
2. 保存用户偏好到 `tyrano_patcher.ini`
3. 重新初始化 UI (`init_ui()`)

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

`Pack.cmd` 脚本执行以下操作：

```
┌─────────────────────────────────────────────────────────────────┐
│                      Pack.cmd 执行流程                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  1. 前置检查                                                     │
│     ├── tools/node.exe 存在?                                    │
│     ├── tools/bundled_asar/ 存在?                               │
│     ├── tools/asar_cli.mjs 存在?                                │
│     ├── Python 可用?                                            │
│     └── PyInstaller 安装?                                        │
│                                                                  │
│  2. 任务A: 构建纯净工具箱 (Tyrano_Toolbox.exe)                   │
│     └── 不包含 Patch/ 目录                                      │
│                                                                  │
│  3. 任务B: 构建汉化补丁 (DevilConnection_Patch.exe)              │
│     └── 仅当 Patch/ 目录存在且非空时构建                         │
│                                                                  │
│  4. 清理                                                         │
│     ├── 删除 build_toolbox/                                     │
│     ├── 删除 build_patcher/                                     │
│     └── 删除 *.spec 文件                                         │
│                                                                  │
│  输出: dist/Tyrano_Toolbox.exe                                  │
│        dist/DevilConnection_Patch.exe (可选)                     │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### 🐛 Debugging / 调试技巧 / デバッグ

#### 查看日志
```bash
# 默认日志位置
# Windows: %TEMP%/tyrano_patcher.log
# Linux/Mac: /tmp/tyrano_patcher.log

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

#### 常见问题排查
| 问题 | 解决方案 |
|------|----------|
| `Node.js not found` | 检查 tools/node.exe 是否存在 |
| `ASAR operation failed` | 使用 `--verbose` 查看详细错误 |
| `Permission denied` | 以管理员权限运行 |
| `Backup corrupted` | 通过 Steam 验证游戏完整性 |

### 📝 Patching Workflow / 完整打补丁流程 / パッチ適用ワークフロー

```
用户点击"🚀 开始安装"
         │
         ▼
    检查 Steam 更新 ──── 有更新 ────→ 询问用户，必要时恢复备份
         │
         否
         ▼
    创建备份 (app.asar → app.asar.bak)
         │
         ▼
    解包 ASAR → temp_patch/
         │
         ▼
    复制补丁文件 ──── Patch/* → temp_patch/
         │
         ▼
    重新打包 ASAR ──── temp_patch/ → app.asar
         │
         ▼
    移除 Fuse ──── DevilConnection.exe
         │
         ▼
    保存元数据 ──── .patch_info, .patch_meta
         │
         ▼
    清理临时目录
         │
         ▼
    ✅ 安装完成
```

### 🇺🇸 English Version / Technical Documentation

#### 🏗️ Project Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         main.py (Entry)                          │
│  ┌─────────────┐  ┌─────────────┐  ┌──────────────────────────┐ │
│  │  argparse   │  │  GUI Mode   │  │    Batch Mode (--batch)   │ │
│  │  Arg Parser │  │  Tkinter UI │  │      CLI Mode            │ │
│  └─────────────┘  └─────────────┘  └──────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
                               │
          ┌────────────────────┼────────────────────┐
          ▼                    ▼                    ▼
┌─────────────────┐  ┌─────────────────┐  ┌─────────────────────┐
│   core/patcher  │  │  gui/main_window │  │       utils/        │
│   Core Patcher  │  │   Tkinter GUI   │  │      Utilities      │
│                  │  │                  │  │                    │
│ • ASAR ops      │  │ • Patch tab      │  │ • language.py      │
│ • Fuse removal  │  │ • Save Manager   │  │   i18n system      │
│ • Steam update  │  │ • Dev Tools tab  │  │ • paths.py         │
│ • Backup mgmt   │  │                  │  │   path handling    │
│                  │  │                  │  │ • logging.py       │
│                  │  │                  │  │   logging system   │
└─────────────────┘  └─────────────────┘  └─────────────────────┘
                               │
                               ▼
                    ┌─────────────────────┐
                    │       tools/        │
                    │   Built-in Tools   │
                    │                    │
                    │ • node.exe         │
                    │   Node.js runtime  │
                    │ • asar_cli.mjs    │
                    │   ASAR CLI tool   │
                    │ • bundled_asar/   │
                    │   ASAR libraries  │
                    └─────────────────────┘
```

#### 📁 Directory Structure

| Path | Description |
|------|-------------|
| `main.py` | Entry point, supports `--batch` CLI and GUI modes |
| `config.ini` | Global config file with game parameters |
| `Pack.cmd` | Windows build script using PyInstaller |
| `core/` | Core modules |
| `core/patcher.py` | `CoreLogic` class with all patch operations |
| `gui/main_window.py` | `App(tk.Tk)` main window class |
| `utils/` | Utility modules |
| `utils/language.py` | i18n system (CN/EN/JP) |
| `utils/paths.py` | Path utilities for PyInstaller |
| `tools/` | Bundled runtime tools |
| `tools/node.exe` | Bundled Node.js for Windows |
| `tools/asar_cli.mjs` | ASAR operations CLI tool |
| `tools/bundled_asar/` | ASAR Node.js dependencies |
| `Patch/` | Translation data directory (optional) |
| `Patch/data/` | Patch files: scenario/, others/, image/ |
| `Patch/tyrano/` | Language config lang.js |

#### ⚙️ Configuration File (`config.ini`)

```ini
[main]
AUTO_TARGET_EXE = DevilConnection.exe
FUSE_SENTINEL = dL7pKGdnNz796PbbjQWNKmHXBZaB9tsX
BACKUP_PREFIX = Backup_
PATCH_INFO_FILE = .patch_info
PATCH_META_FILE = .patch_meta
TIME_DIFF_THRESHOLD_DAYS = 3

[files]
# Files to check for Steam updates
CHECK_FILES_FOR_UPDATE =
    data/others/craftmincho.ttf
    data/others/DZUYOKU.ttf
    data/others/funwari-round.ttf
    data/others/HeadUpDaisy.ttf
    tyrano/lang.js

# Stable files for backup validation
STABLE_FILES_FOR_VALIDATION =
    index.html      # Entry HTML
    main.js         # Electron main
    package.json    # Package config
    steam.js        # Steam integration
    preload.js      # Preload script
    electron_latest.js
```

#### 🔄 Execution Flow

##### GUI Mode
```
main.py → App.__init__() → init_ui()
                              │
        ┌─────────────────────┼─────────────────────┐
        ▼                     ▼                     ▼
┌───────────────┐    ┌───────────────┐    ┌───────────────────┐
│  Patch Tab    │    │  Save Tab     │    │   Tools Tab       │
│ (tab_patch)  │    │ (tab_save)   │    │  (tab_tools)      │
└───────────────┘    └───────────────┘    └───────────────────┘
        │                     │                     │
        ▼                     ▼                     ▼
┌───────────────┐    ┌───────────────┐    ┌───────────────────┐
│1. Check ASAR │    │1. Scan saves  │    │ • ASAR extract/pack│
│2. Create bkup│    │2. Backup/restore│   │ • Fuse removal    │
│3. Extract    │    │3. ZIP compress│    │ • Platform select │
│4. Apply patch│    │4. Async ops   │    │                   │
│5. Repack     │    │               │    │                   │
│6. Save meta  │    │               │    │                   │
└───────────────┘    └───────────────┘    └───────────────────┘
```

##### Batch Mode (`--batch --auto`)
```
main.py --batch --auto
    │
    ▼
handle_steam_update()  ←── Steam update detection
    │
    ▼
shutil.copy2(asar, bak)  ←── Create backup
    │
    ▼
core.run_asar("extract")  ←── Extract ASAR
    │
    ▼
shutil.copytree(Patch, temp)  ←── Apply patch
    │
    ▼
core.run_asar("pack")  ←── Repack ASAR
    │
    ▼
save_patch_info() + save_patch_meta()  ←── Save metadata
```

##### Steam Update Detection State Machine
```
┌────────────────────────────────────────────────────────────────┐
│                     handle_steam_update()                       │
├────────────────────────────────────────────────────────────────┤
│                                                                │
│  ┌──────────────┐    ASAR?    ┌──────────────┐                 │
│  │  Case 4:     │─────────────│  Case 1:     │                 │
│  │  File corrupt│    No       │  First patch │                 │
│  └──────────────┘             └──────────────┘                 │
│       │                            │                          │
│       ▼                            ▼                          │
│  Show error            Validate ASAR integrity                  │
│                                                                 │
│  ┌──────────────┐    ASAR?    ┌──────────────┐                 │
│  │  Case 3:     │─────────────│  Case 2:     │                 │
│  │  Steam update│    Yes      │  Already pthd │                 │
│  │  Auto restore│            └──────────────┘                 │
│  └──────────────┘                            │               │
│       │                                      ▼               │
│       ▼                            Check .patch_info file     │
│  Validate backup integrity                 │                   │
│       │                            Corrupt?  │  │  Expired?│
│       ▼                              ▼       │    ▼         │
│  Auto restore                           │       │  │          │
│                                         │       │  ▼          │
│                                         └───────┴─────────────►│
└────────────────────────────────────────────────────────────────┘
```

#### 🛠️ Core Components

##### CoreLogic Class (`core/patcher.py`)

| Method | Description |
|--------|-------------|
| `__init__()` | Initialize, validate Node.js and ASAR CLI |
| `run_asar(action, src, dest)` | Execute ASAR extract/pack operations |
| `remove_fuse(exe_path)` | Remove game Fuse integrity check |
| `_find_script()` | Find ASAR CLI script |

##### App Class (`gui/main_window.py`)

| Component | Description |
|-----------|-------------|
| `tab_patch` | Patch installation UI (only if patch exists) |
| `tab_save` | Save manager with backup/restore/delete |
| `tab_tools` | Developer toolbox, ASAR and Fuse ops |
| `log_area` | Log display (ScrolledText) |
| `progress` | Progress bar (indeterminate mode) |

##### Multi-Language System (`utils/language.py`)

Supports **Simplified Chinese (cn)**, **English (en)**, **日本語 (jp)**.

**Detection Priority:**
```
1. Windows → GetUserDefaultUILanguage() API
   ├── 2052 (Chinese) → 'cn'
   ├── 1041 (Japanese) → 'jp'
   └── Other → 'en'

2. Other systems → Environment variable LANG
   ├── Contains 'zh'/'cn'/'tw' → 'cn'
   ├── Contains 'ja' → 'jp'
   └── Other → 'en'
```

**Usage:**
```python
T('btn_start_patch')  # → "🚀 Start Patch"
language.CURRENT_LANG_CODE = 'en'
self.init_ui()  # Reinitialize to apply new language
```

**Adding Translations:**
```python
LANG_DICT = {
    'cn': {'new_key': '中文文本'},
    'en': {'new_key': 'English text'},
    'jp': {'new_key': '日本語テキスト'},
}
```

**User Preferences:**
- Windows: `%APPDATA%/tyrano_patcher.ini`
- Linux/Mac: `~/.config/tyrano_patcher.ini`

#### 🔧 Build Process

```
┌─────────────────────────────────────────────────────────────────┐
│                      Pack.cmd Execution                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  1. Pre-checks                                                  │
│     ├── tools/node.exe exists?                                  │
│     ├── tools/bundled_asar/ exists?                            │
│     ├── tools/asar_cli.mjs exists?                              │
│     ├── Python available?                                       │
│     └── PyInstaller installed?                                 │
│                                                                  │
│  2. Task A: Build Toolbox (Tyrano_Toolbox.exe)                 │
│     └── Does NOT include Patch/                                │
│                                                                  │
│  3. Task B: Build Patcher (DevilConnection_Patch.exe)           │
│     └── Only if Patch/ exists and is non-empty                 │
│                                                                  │
│  4. Cleanup                                                     │
│     ├── Delete build_toolbox/                                  │
│     ├── Delete build_patcher/                                  │
│     └── Delete *.spec files                                    │
│                                                                  │
│  Output: dist/Tyrano_Toolbox.exe                              │
│          dist/DevilConnection_Patch.exe (optional)              │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

#### 🐛 Debugging

**Log Location:**
```bash
# Windows: %TEMP%/tyrano_patcher.log
# Linux/Mac: /tmp/tyrano_patcher.log

# Custom log file
python main.py --log-file /path/to/custom.log
```

**Batch Mode Debug:**
```bash
# Verbose output
python main.py --batch --auto --verbose

# Fuse removal only
python main.py --batch --fuse DevilConnection.exe
```

**Troubleshooting:**
| Issue | Solution |
|-------|----------|
| `Node.js not found` | Check if tools/node.exe exists |
| `ASAR operation failed` | Use `--verbose` for details |
| `Permission denied` | Run as administrator |
| `Backup corrupted` | Verify game integrity via Steam |

#### 📝 Patching Workflow

```
User clicks "🚀 Start Patch"
         │
         ▼
   Check Steam Update ──── Updated ────→ Ask user, restore if needed
         │
         No
         ▼
   Create Backup (app.asar → app.asar.bak)
         │
         ▼
   Extract ASAR → temp_patch/
         │
         ▼
   Copy Patch Files ──── Patch/* → temp_patch/
         │
         ▼
   Repack ASAR ──── temp_patch/ → app.asar
         │
         ▼
   Remove Fuse ──── DevilConnection.exe
         │
         ▼
   Save Metadata ──── .patch_info, .patch_meta
         │
         ▼
   Cleanup temp directory
         │
         ▼
   ✅ Installation Complete
```

#### 🔨 Build Guide

1. **Clone & Setup**
   ```bash
   git clone <repo-url>
   cd <repo-path>
   ```

2. **Add Translation Assets**
   ```
   Place files in Patch/:
   Patch/
   ├── data/
   │   ├── others/    # Game scripts
   │   └── scenario/  # Story files
   └── tyrano/
       └── lang.js    # Language config
   ```

3. **Build**
   ```bash
   Pack.cmd
   # Output in dist/
   ```

### 🇯🇵 日本語版 / 技術ドキュメント

#### 🏗️ プロジェクト構成

```
┌─────────────────────────────────────────────────────────────────┐
│                         main.py (エントリポイント)               │
│  ┌─────────────┐  ┌─────────────┐  ┌──────────────────────────┐ │
│  │  argparse   │  │  GUI モード │  │   Batch Mode (--batch)   │ │
│  │  引数解析   │  │ Tkinter UI │  │      CLI モード          │ │
│  └─────────────┘  └─────────────┘  └──────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
                               │
          ┌────────────────────┼────────────────────┐
          ▼                    ▼                    ▼
┌─────────────────┐  ┌─────────────────┐  ┌─────────────────────┐
│   core/patcher  │  │  gui/main_window │  │       utils/        │
│   コアパッチャー │  │   Tkinter GUI   │  │      ユーティリティ  │
│                  │  │                  │  │                    │
│ • ASAR操作      │  │ • パッチタブ    │  │ • language.py      │
│ • Fuse解除      │  │ • セーブ管理    │  │   多言語システム   │
│ • Steam更新検出 │  │ • 開発者ツール  │  │ • paths.py         │
│ • バックアップ   │  │                  │  │   パス処理        │
│                  │  │                  │  │ • logging.py       │
│                  │  │                  │  │   ログシステム   │
└─────────────────┘  └─────────────────┘  └─────────────────────┘
                               │
                               ▼
                    ┌─────────────────────┐
                    │       tools/        │
                    │    内蔵ツール       │
                    │                    │
                    │ • node.exe         │
                    │   Node.js ランタイム│
                    │ • asar_cli.mjs    │
                    │   ASAR CLI ツール  │
                    │ • bundled_asar/   │
                    │   ASAR 依存ライブラリ│
                    └─────────────────────┘
```

#### 📁 ディレクトリ構造

| パス | 説明 |
|------|------|
| `main.py` | エントリポイント、`--batch` CLI と GUI モード対応 |
| `config.ini` | グローバル設定ファイル |
| `Pack.cmd` | PyInstaller でビルドする Windows 用スクリプト |
| `core/` | コアモジュール |
| `core/patcher.py` | `CoreLogic` クラスと全てのパッチ操作 |
| `gui/main_window.py` | `App(tk.Tk)` メインウィンドウクラス |
| `utils/` | ユーティリティモジュール |
| `utils/language.py` | i18n システム（CN/EN/JP） |
| `utils/paths.py` | PyInstaller 用パスユーティリティ |
| `tools/` | 内蔵ランタイムツール |
| `tools/node.exe` | Windows 用バンドル Node.js |
| `tools/asar_cli.mjs` | ASAR 操作 CLI ツール |
| `tools/bundled_asar/` | ASAR Node.js 依存ライブラリ |
| `Patch/` | 翻訳データディレクトリ（オプション） |
| `Patch/data/` | パッチファイル: scenario/, others/, image/ |
| `Patch/tyrano/` | 言語設定 lang.js |

#### ⚙️ 設定ファイル (`config.ini`)

```ini
[main]
AUTO_TARGET_EXE = DevilConnection.exe
FUSE_SENTINEL = dL7pKGdnNz796PbbjQWNKmHXBZaB9tsX
BACKUP_PREFIX = Backup_
PATCH_INFO_FILE = .patch_info
PATCH_META_FILE = .patch_meta
TIME_DIFF_THRESHOLD_DAYS = 3

[files]
# Steam更新を検出するファイル
CHECK_FILES_FOR_UPDATE =
    data/others/craftmincho.ttf
    data/others/DZUYOKU.ttf
    data/others/funwari-round.ttf
    data/others/HeadUpDaisy.ttf
    tyrano/lang.js

# バックアップ整合性検証用の安定ファイル
STABLE_FILES_FOR_VALIDATION =
    index.html      # エントリ HTML
    main.js         # Electron メイン
    package.json    # パッケージ設定
    steam.js        # Steam 連携
    preload.js      # プレロードスクリプト
    electron_latest.js
```

#### 🔄 実行フロー

##### GUI モード
```
main.py → App.__init__() → init_ui()
                              │
        ┌─────────────────────┼─────────────────────┐
        ▼                     ▼                     ▼
┌───────────────┐    ┌───────────────┐    ┌───────────────────┐
│  パッチタブ   │    │ セーブタブ     │    │   ツールタブ      │
│ (tab_patch) │    │ (tab_save)  │    │  (tab_tools)     │
└───────────────┘    └───────────────┘    └───────────────────┘
        │                     │                     │
        ▼                     ▼                     ▼
┌───────────────┐    ┌───────────────┐    ┌───────────────────┐
│1. ASAR確認   │    │1. セーブスキャン│    │ • ASAR解凍/圧縮  │
│2. バックアップ│    │2. バックアップ │    │ • Fuse解除       │
│3. 解凍       │    │3. ZIP圧縮     │    │ • プラットフォーム│
│4. パッチ適用 │    │4. 非同期処理   │    │                   │
│5. 再圧縮     │    │               │    │                   │
│6. メタデータ  │    │               │    │                   │
└───────────────┘    └───────────────┘    └───────────────────┘
```

##### バッチモード (`--batch --auto`)
```
main.py --batch --auto
    │
    ▼
handle_steam_update()  ←── Steam更新検出
    │
    ▼
shutil.copy2(asar, bak)  ←── バックアップ作成
    │
    ▼
core.run_asar("extract")  ←── ASAR解凍
    │
    ▼
shutil.copytree(Patch, temp)  ←── パッチ適用
    │
    ▼
core.run_asar("pack")  ←── ASAR再圧縮
    │
    ▼
save_patch_info() + save_patch_meta()  ←── メタデータ保存
```

##### Steam更新検出状態機械
```
┌────────────────────────────────────────────────────────────────┐
│                    handle_steam_update()                        │
├────────────────────────────────────────────────────────────────┤
│                                                                │
│  ┌──────────────┐    ASAR?    ┌──────────────┐                 │
│  │  ケース4:   │─────────────│  ケース1:   │                 │
│  │  ファイル破損│    なし    │  初回パッチ │                 │
│  └──────────────┘            └──────────────┘                 │
│       │                            │                          │
│       ▼                            ▼                          │
│  エラー表示            ASAR整合性検証                          │
│                                                                 │
│  ┌──────────────┐    ASAR?    ┌──────────────┐                 │
│  │  ケース3:   │─────────────│  ケース2:   │                 │
│  │  Steam更新  │    あり     │  既存パッチ │                 │
│  │  自動復元   │            └──────────────┘                 │
│  └──────────────┘                            │               │
│       │                                      ▼               │
│       ▼                            .patch_info ファイル確認   │
│  バックアップ整合性                              │               │
│       │                            破損?  │  │  期限切れ？│  │
│       ▼                              ▼      │    ▼         │
│  自動復元                             │       │  │          │
│                                         └───────┴─────────────►│
└────────────────────────────────────────────────────────────────┘
```

#### 🛠️ コアコンポーネント

##### CoreLogic クラス (`core/patcher.py`)

| メソッド | 説明 |
|---------|------|
| `__init__()` | 初期化、Node.js と ASAR CLI 検証 |
| `run_asar(action, src, dest)` | ASAR 解凍/圧縮 操作実行 |
| `remove_fuse(exe_path)` | ゲーム Fuse 整合性解除 |
| `_find_script()` | ASAR CLI スクリプト検索 |

##### App クラス (`gui/main_window.py`)

| コンポーネント | 説明 |
|--------------|------|
| `tab_patch` | パッチインストールUI（パッチ存在時のみ） |
| `tab_save` | バックアップ/復元/削除付きセーブ管理 |
| `tab_tools` | 開発者ツールボックス、ASARとFuse操作 |
| `log_area` | ログ表示（ScrolledText） |
| `progress` | 進捗バー（indeterminate モード） |

##### 多言語システム (`utils/language.py`)

**简体中文 (cn)**、**English (en)**、**日本語 (jp)** をサポート。

**検出優先度:**
```
1. Windows → GetUserDefaultUILanguage() API
   ├── 2052 (中国語) → 'cn'
   ├── 1041 (日本語) → 'jp'
   └── その他 → 'en'

2. その他 → 環境変数 LANG
   ├── 'zh'/'cn'/'tw' 含む → 'cn'
   ├── 'ja' 含む → 'jp'
   └── その他 → 'en'
```

**使用方法:**
```python
T('btn_start_patch')  # → "🚀 インストール開始"
language.CURRENT_LANG_CODE = 'en'
self.init_ui()  # 再初期化して新言語を適用
```

**翻訳追加:**
```python
LANG_DICT = {
    'cn': {'new_key': '中文文本'},
    'en': {'new_key': 'English text'},
    'jp': {'new_key': '日本語テキスト'},
}
```

**ユーザー設定:**
- Windows: `%APPDATA%/tyrano_patcher.ini`
- Linux/Mac: `~/.config/tyrano_patcher.ini`

#### 🔧 ビルドプロセス

```
┌─────────────────────────────────────────────────────────────────┐
│                     Pack.cmd 実行フロー                           │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  1. 事前チェック                                                 │
│     ├── tools/node.exe 存在確認                                  │
│     ├── tools/bundled_asar/ 存在確認                            │
│     ├── tools/asar_cli.mjs 存在確認                              │
│     ├── Python 利用可能確認                                       │
│     └── PyInstaller インストール確認                            │
│                                                                  │
│  2. タスクA: ツールボックスビルド (Tyrano_Toolbox.exe)           │
│     └── Patch/ は含まない                                        │
│                                                                  │
│  3. タスクB: パッチャービルド (DevilConnection_Patch.exe)       │
│     └── Patch/ が存在し空でない場合のみ                         │
│                                                                  │
│  4. クリーンアップ                                               │
│     ├── build_toolbox/ 削除                                      │
│     ├── build_patcher/ 削除                                      │
│     └── *.spec ファイル削除                                      │
│                                                                  │
│  出力: dist/Tyrano_Toolbox.exe                                  │
│        dist/DevilConnection_Patch.exe (オプション)               │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

#### 🐛 デバッグ

**ログの場所:**
```bash
# Windows: %TEMP%/tyrano_patcher.log
# Linux/Mac: /tmp/tyrano_patcher.log

# カスタムログファイル
python main.py --log-file /path/to/custom.log
```

**バッチモード デバッグ:**
```bash
# 詳細出力
python main.py --batch --auto --verbose

# Fuse解除のみ
python main.py --batch --fuse DevilConnection.exe
```

**トラブルシューティング:**
| 問題 | 解決策 |
|------|--------|
| `Node.js not found` | tools/node.exe の存在確認 |
| `ASAR operation failed` | `--verbose` で詳細確認 |
| `Permission denied` | 管理者権限で実行 |
| `Backup corrupted` | Steam でゲーム整合性検証 |

#### 📝 パッチ適用ワークフロー

```
ユーザーが「🚀 インストール開始」をクリック
         │
         ▼
   Steam更新チェック ──── 更新あり ────→ ユーザーに確認、必要なら復元
         │
         なし
         ▼
   バックアップ作成 (app.asar → app.asar.bak)
         │
         ▼
   ASAR解凍 → temp_patch/
         │
         ▼
   パッチファイルコピー ──── Patch/* → temp_patch/
         │
         ▼
   ASAR再圧縮 ──── temp_patch/ → app.asar
         │
         ▼
   Fuse解除 ──── DevilConnection.exe
         │
         ▼
   メタデータ保存 ──── .patch_info, .patch_meta
         │
         ▼
   一時ディレクトリクリーンアップ
         │
         ▼
   ✅ インストール完了
```

#### 🔨 ビルドガイド

1. **複製と準備**
   ```bash
   git clone <repo-url>
   cd <repo-path>
   ```

2. **翻訳リソース追加**
   ```
   Patch/ に配置：
   Patch/
   ├── data/
   │   ├── others/    # ゲームスクリプト
   │   └── scenario/  # ストーリー
   └── tyrano/
       └── lang.js    # 言語設定
   ```

3. **ビルド**
   ```bash
   Pack.cmd
   # 出力は dist/
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
