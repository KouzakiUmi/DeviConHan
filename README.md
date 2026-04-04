# Devil Connection Localization Tool / 恶魔链接本地化工具

![Status](https://img.shields.io/badge/Status-Stable-green?style=flat-square)
![Platform](https://img.shields.io/badge/Platform-Win%20|%20Mac%20|%20Linux-blue?style=flat-square)
![License](https://img.shields.io/badge/License-CC%20BY--NC--SA%204.0-lightgrey?style=flat-square)
![Build](https://img.shields.io/badge/Build-Automated-success?style=flat-square)

> **By KouzakiUmi (呜咪 / 神前海)**

---

### 🇨🇳 中文
本项目是《恶魔链接（でびるコネクション）》的非营利性个人本地化工具。
采用全图形化界面 (GUI)，支持跨平台运行，集成了强大的存档管理与开发者工具。

**✨ 核心功能：**

| 功能 | 描述 |
|------|------|
| 🌍 **跨平台支持** | 完美支持 Windows、macOS 和 Linux 系统 |
| 🚀 **全自动补丁安装** | 图形化界面一键安装，自动备份，自动移除游戏完整性校验 (Fuse) |
| 💾 **专业存档管理** | 自动扫描存档位置，支持一键备份/还原，带时间戳，可压缩为 ZIP |
| 🛠️ **开发者工具箱** | 内置 Asar 解包/打包工具，支持跨平台格式选择 |
| 🔒 **操作保护** | 智能并发锁、备份前确认提示，多重保障确保数据安全 |
| 🌐 **多语言支持** | 内置中文/英文/日文，运行时自由切换，无需重启 |

### 🇺🇸 English
**Devil Connection Localization Tool** is a non-profit, fan-made localization patcher.
Features a full Graphical User Interface (GUI), cross-platform support, and advanced save management tools.

**✨ Key Features:**

| Feature | Description |
|---------|-------------|
| 🌍 **Cross-Platform** | Seamlessly runs on Windows, macOS, and Linux |
| 🚀 **One-Click Patching** | GUI-based automatic installation with auto-backup and Fuse removal |
| 💾 **Professional Save Manager** | Auto-detects saves, timestamped backups, ZIP compression, instant restore |
| 🛠️ **Developer Toolbox** | Built-in Asar extract/pack with multi-platform target selection |
| 🔒 **Operation Safety** | Concurrency protection, confirmation prompts, and multi-layer safeguards |
| 🌐 **Multi-Language** | Chinese/English/Japanese with runtime switching—no restart needed |

### 🇯🇵 日本語
本プロジェクトは、ゲーム『でびるコネクション』の非营利・個人制作によるローカライズツールです。
完全なGUI、クロスプラットフォーム対応、そして強力なセーブデータ管理機能を搭载しました。

**✨ 主な特徴:**

| 機能 | 説明 |
|------|------|
| 🌍 **マルチプラットフォーム対応** | Windows、macOS、Linux で完全サポート |
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
   - **Windows**: 直接运行 `.exe`。
   - **Mac/Linux**: 需要安装 Python 环境或使用构建好的二进制文件（如提供），并确保系统已安装 Node.js（Windows版本内置了精简版 Node，无需安装）。
4. **操作**：在弹出的窗口中点击 **"🚀 开始安装"** 即可。

### 🇺🇸 English
1. **Download**: Get the latest release from [Releases](../../releases).
2. **Place**: Put the tool into the game's root folder.
3. **Run**:
   - **Windows**: Run the `.exe` directly.
   - **Mac/Linux**: Requires Python or provided binary. Ensure Node.js is installed (Windows version includes a bundled Node runtime).
4. **Action**: Click **"🚀 Start Patch"** in the GUI window.

### 🇯🇵 日本語
1. **ダウンロード**: [Releases](../../releases) から最新版をダウンロードします。
2. **配置**: ツールをゲームのルートフォルダに置きます。
3. **実行**:
   - **Windows**: `.exe` を直接実行します。
   - **Mac/Linux**: Python環境、または提供されたバイナリが必要です。Node.jsがインストールされていることを確認してください（Windows版は内装されています）。
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

### 🇨🇳 构建指南

本项目包含一个智能构建脚本 `Pack.cmd`，可生成两种版本的程序：

#### 📦 生成模式

| 模式 | 触发条件 | 特点 | 用途 |
|------|----------|------|------|
| **自动安装器** (Patcher) | `Patch` 文件夹不为空 | 包含汉化资源，一键安装 | 汉化发布版 |
| **通用工具箱** (Toolbox) | `Patch` 文件夹为空/不存在 | 仅含工具功能，跨项目可用 | 开发调试、通用工具 |

#### 🔨 快速开始

1. **克隆并准备**
   ```bash
   git clone <repo-url>
   cd <repo-path>
   ```

2. **配置汉化资源**（可选）
   ```
   将汉化文件放入 Patch/ 文件夹：
   Patch/
   ├── data/
   │   ├── others/    # 游戏脚本
   │   └── scenario/   # 剧情文件
   └── tyrano/
       └── lang.js    # 语言配置
   ```

3. **构建**
   ```bash
   Pack.cmd
   # 生成的可执行文件在 dist/ 目录
   ```

#### 🏗️ 技术架构

**前端界面**
- Tkinter GUI（跨平台原生界面）
- 高分屏自适应支持
- 运行时多语言切换（CN/EN/JP）

**核心引擎**
- **Windows**：内置独立 Node.js 运行时（零依赖）
- **Mac/Linux**：自动调用系统全局 Node.js

**Asar 打包智能系统**
- 使用内置 `asar_cli.mjs` 工具进行 ASAR 操作
- 自动检测目标平台（Windows/Mac/Linux）
- 智能选择 unpack 规则：
  - Windows：`.node`, `.dll`, `.exe`
  - Mac/Linux：`.node`, `.so`, `.dylib`, `.bin`

### 🇺🇸 Build Guide

Intelligent `Pack.cmd` script with **dual-mode generation**:

#### 📦 Generation Modes

| Mode | Condition | Features | Use Case |
|------|-----------|----------|----------|
| **Auto-Installer** | `Patch/` not empty | Bundled patch, one-click install | Release version |
| **Generic Toolbox** | `Patch/` empty | Tools only, project-agnostic | Development, utilities |

#### 🔨 Quick Start

1. **Clone & Setup**
   ```bash
   git clone <repo-url>
   cd <repo-path>
   ```

2. **Add Translation Assets** (Optional)
   ```
   Place files in Patch/:
   Patch/
   ├── data/
   │   ├── others/    # Game scripts
   │   └── scenario/   # Story files
   └── tyrano/
       └── lang.js    # Language config
   ```

3. **Build**
   ```bash
   Pack.cmd
   # Output in dist/
   ```

#### 🏗️ Technical Stack

**Frontend**
- Tkinter (Cross-platform native UI)
- HiDPI support
- Runtime language switching

**Core Engine**
- **Windows**: Bundled standalone Node.js (zero dependencies)
- **Mac/Linux**: System global Node.js auto-detection

**Asar Operations**
- Built-in `asar_cli.mjs` tool for ASAR operations
- Auto-detect target platform
- Intelligent unpack patterns:
  - Windows: `.node`, `.dll`, `.exe`
  - Mac/Linux: `.node`, `.so`, `.dylib`, `.bin`

### 🇯🇵 ビルドガイド

スマートな `Pack.cmd` スクリプトで**デュアルモード生成**：

#### 📦 生成モード

| モード | 条件 | 特徴 | 用途 |
|--------|------|------|------|
| **自動インストーラー** | `Patch/` が存在 | パッチ付属、ワンクリック導入 | リリース版 |
| **汎用ツールボックス** | `Patch/` が空/不存在 | ツールのみ、再利用可能 | 開発・調試 |

#### 🔨 クイックスタート

1. **複製と準備**
   ```bash
   git clone <repo-url>
   cd <repo-path>
   ```

2. **翻訳リソース追加**（任意）
   ```
   Patch/ に配置：
   Patch/
   ├── data/
   │   ├── others/    # ゲームスクリプト
   │   └── scenario/   # ストーリー
   └── tyrano/
       └── lang.js    # 言語設定
   ```

3. **ビルド**
   ```bash
   Pack.cmd
   # 出力は dist/
   ```

#### 🏗️ 技術構成

**フロントエンド**
- Tkinter（クロスプラットフォーム UI）
- 高解像度対応
- 実行時言語切替

**コアエンジン**
- **Windows**: 内蔵スタンドアロン Node.js（依存なし）
- **Mac/Linux**: システムグローバル Node.js 自動検出

**Asar オペレーション**
- 内蔵 `asar_cli.mjs` ツールで ASAR 操作
- ターゲットプラットフォーム自動検出
- インテリジェント unpack パターン：
  - Windows: `.node`, `.dll`, `.exe`
  - Mac/Linux: `.node`, `.so`, `.dylib`, `.bin`

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
