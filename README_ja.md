# Tyranoパッチツールボックス

**でびるコネクション漢化パッチは組み込みサンプル作品です。**

**開発者向け説明**: このツールボックスはTyranoV8/Electronベースのゲーム向けの汎用ツールです。`config.ini`を修正（AUTO_TARGET_EXE、FUSE_SENTINEL、CHECK_FILES_FOR_UPDATEなど）し、対象ゲームのローカライズファイルを含む`patch.zip`を提供することで、他のゲームに適応できます。詳細は[PLUGIN_GUIDE.md](PLUGIN_GUIDE.md)を参照してください。

<div align="center">

**🌐 言語切替**

**[中文 🇨🇳](README.md)** • **[English 🇬🇧](README_en.md)** • **[日本語 🇯🇵 (現在)](README_ja.md)**

</div>

![Status](https://img.shields.io/badge/Status-RC-orange?style=flat-square)
![Platform](https://img.shields.io/badge/Platform-Win%20|%20Mac%20|%20Linux-blue?style=flat-square)
![License](https://img.shields.io/badge/License-CC%20BY--NC--SA%204.0-lightgrey?style=flat-square)
![Build](https://img.shields.io/badge/Build-Automated-success?style=flat-square)

> **By KouzakiUmi (呜咪 / 神前海)**


---

## 概要

このプロジェクトはTyranoV8ベースゲーム向けの非営利個人ローカライズツールボックスで、でびるコネクションの漢化パッチを組み込み例としています。フルGUI、クロスプラットフォーム（Windows/macOS/Linux）、高度なセーブ管理、開発者ツールを搭載。

**✨ 主な機能：**

- **🚀 ワンクリックパッチ適用**: グラフィカルUIで自動インストール、バックアップ、Fuse完全性チェック除去。
- **💾 プロフェッショナルセーブマネージャー**: 独立したバックアップ場所(`~/.tyranopatcher/backups`)、ZIP/Dir対応、ハッシュ検証付きスムーズ移行。
- **🛠️ 開発者ツールボックス**: Python `asar`ライブラリによるASAR展開/パック、動的Fuseオフセット設定、設定検証。
- **⚙️ 隔離設定システム**: ホームディレクトリのユーザー設定、ホットリロード、検証、テンプレートフォールバック。
- **🔒 安全保護**: 同時実行ロック、確認ダイアログ、ハッシュチェック、原子性書き込み。
- **🌐 多言語対応**: 中/英/日、メニューによるランタイム切替。
- **📚 包括的なドキュメント**: [PROJECT_SPECS.md](PROJECT_SPECS.md)、[API_DOCS.md](API_DOCS.md)、[PLUGIN_GUIDE.md](PLUGIN_GUIDE.md)を参照。

---

## インストール

### 自動ビルド版（推奨）

mainブランチへのプッシュで自動ビルド。最新版を[Releases](../../releases)からダウンロード：
- `Tyrano_Toolbox.exe` - 純粋ツールボックス
- `DevilConnection_Patch.exe` - 組み込み例パッチ付き（利用可能時）

### ソースからのビルド（Windows）

```cmd
git clone <repo-url>
cd DeviConHan
.\Pack.cmd
```

`dist/`に出力：
- `Tyrano_Toolbox.exe`
- Patchデータがある場合`DevilConnection_Patch.exe`

### macOS / Linux

Python 3.8+、PyInstallerが必要。

```bash
pip install pyinstaller
python -m PyInstaller -F -w --clean -i "icon.ico" \
  --add-data "icon.ico:." \
  --add-data "config.ini:." \
  --name "Tyrano_Toolbox" main.py
```

パッチ版はまず`Patch.zip`を準備（`python -c "import shutil; shutil.make_archive('Patch', 'zip', 'Patch')"`）してから追加データとして指定。

**注意**: Pack.cmd/Pack.shはPatch/をPatch.zipに自動圧縮して起動性能を向上させ、適切な実行ファイルを作成します。

---

## セーブマネージャー

組み込みのSave Managerタブでプロ級のバックアップ/復元を提供：

- セーブディレクトリの自動検出（パッチ実行場所に関係なく確実に位置を特定）。
- タイムスタンプ付き独立バックアップ（ZIPまたはディレクトリ）。
- バックアップパス変更時のスムーズ移行（ハッシュ検証付き）。
- 確認付きワンクリック復元。
- UIをブロックしない非同期操作。
- 同時実行安全ロック。

実装詳細は[UTILS_GUIDE.md](UTILS_GUIDE.md)を参照。

---

## 開発者向け

完全なアーキテクチャと設計原則は[PROJECT_SPECS.md](PROJECT_SPECS.md)を参照。

**他のゲームへの適応**（上記参照）：configとpatch.zipを修正。現在のコードは`asar` Pythonパッケージを使用した純粋Python ASAR処理、`utils/asar_utils.py`と`core/state_validator.py`での検証、bootstrap、state machineを採用。パッケージングスクリプトも現在のロジックに更新（node.exe依存をコア操作から除去）。

**現在のアーキテクチャ**（コード分析に基づく更新）:
- `main.py`: 引数解析、bootstrap、GUI/バッチモード。
- `core/`: bootstrap.py, patcher.py (遅延asarインポート付きCoreLogic), config.py (スナップショット/TTL/ホットリロード/ユーザーディレクトリ優先のシングルトン), steam.py (ステートマシン), save_service.py, fuse.py, state_validator.py, patch_info.py, batch.py。
- `gui/`: main_window.py, tabs/(patch_tab.py, save_tab.py, tools_tab.py)。
- `controllers/`: patch_controller, save_manager_controller。
- `utils/`: language.py (システム言語検出+ini設定), paths.py, async_ops.py など。
- Bootstrapは起動前に包括的なシステムチェックを実行。

**パッケージングスクリプト分析**:
- `Pack.cmd`/`Pack.sh`: 依存チェック、ツールボックスビルド、Patch圧縮、必要時パッチャービルド、クリーンアップ。現在のPyInstaller仕様と純Python ASARに更新。

**設定**:
テンプレートから`~/.tyranopatcher/config.ini`へコピー。すべてのキーに対応。Toolsタブで検証/リセット可能。

**実行ロジック**（コードから）:
1. Bootstrap: 設定ロード、パス、状態検証 (ASAR/bak/metaのハッシュ整合性)。
2. パッチフロー: Steam更新検出 (patch_metaハッシュ使用)、バックアップ、抽出 (asar.extract_archive)、パッチ適用、再パック (asar.create_archive)、メタ/情報原子性保存、クリーンアップ。
3. セーブ操作: ゲームディレクトリ独立、ZIP対応、ハッシュチェック付き移行。
4. Fuse除去: 設定可能オフセット、EXEへのバイナリパッチ。

詳細は`core/bootstrap.py`、`controllers/patch_controller.py`、`core/steam.py`のhandle_steam_update() (4ケースのステートマシン)、`gui/tabs/tools_tab.py`を分析してください。

---

## ライセンス

本プロジェクトは原作者**ばやちゃお (Bayachao)**氏の二次創作ガイドラインを厳守します。

- **非営利のみ**。商用利用禁止。
- パッチは翻訳/注入ファイルのみを含み、**ゲーム本体は含まれません**。
- ゲーム、キャラクター、デザインの全権利は原作者に帰属。

参照: [作者ガイドライン](https://bayachao.com/devil-connection/guideline)
ライセンス: [CC BY-NC-SA 4.0](https://creativecommons.org/licenses/by-nc-sa/4.0/)