# Tyranoパッチツールボックス

**でびるコネクショん漢化パッチは組み込みサンプル作品です。**

**開発者向け説明**: このツールボックスはTyranoV8/Electronベースのゲーム向けの汎用ツールです。`config.ini`を修正（WINDOWS_EXE、MACOS_APP、LINUX_BINARY、FUSE_SENTINEL、CHECK_FILES_FOR_UPDATEなど）し、対象ゲームのローカライズファイルを含む`Patch.zip`を提供することで、他のゲームに適応できます。GUI でカスタム ZIP を選択することもできます。対象ゲームのバージョンで互換性を検証してください。詳細は[PLUGIN_GUIDE.md](PLUGIN_GUIDE.md)を参照してください。

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

このプロジェクトはTyranoV8ベースゲーム向けの非営利個人ローカライズツールボックスで、でびるコネクショんの漢化パッチを組み込み例としています。フルGUI、クロスプラットフォーム（Windows/macOS/Linux）、高度なセーブ管理、開発者ツールを搭載。

**✨ 主な機能：**

- **🚀 ワンクリックパッチ適用**: 内蔵 `Patch.zip` またはGUIで選択したカスタムZIPを使用し、パッチのルートディレクトリの自動検出、バックアップ、オリジナルファイルの手動復元に対応。
- **💾 プロフェッショナルセーブマネージャー**: 独立したバックアップ場所(`~/.tyranopatcher/backups`)、ZIP/Dir対応、ハッシュ検証付きスムーズ移行。
- **🛠️ 開発者ツールボックス**: 純粋Python ASAR展開/パック、動的Fuseオフセット設定、設定検証。
- **⚙️ 隔離設定システム**: ホームディレクトリのユーザー設定、ホットリロード、検証、テンプレートフォールバック。
- **🔒 安全保護**: 同時実行ロック、確認ダイアログ、ハッシュ検証、復旧処理。ゲームファイルの異常時は Steam の整合性確認を優先。
- **🌐 多言語対応**: 中/英/日、メニューによるランタイム切替。
- **📚 包括的なドキュメント**: まず [DOCS_INDEX_ja.md](DOCS_INDEX_ja.md) を参照し、その後 [MODULE_GUIDE_ja.md](MODULE_GUIDE_ja.md)、[PROJECT_SPECS.md](PROJECT_SPECS.md)、[TECHNICAL_REFERENCE.md](TECHNICAL_REFERENCE.md)、[PLUGIN_GUIDE.md](PLUGIN_GUIDE.md) を利用してください。

---

## インストール

### 自動ビルド版（推奨）

mainブランチへのプッシュで自動ビルド。最新版を[Releases](../../releases)からダウンロード：
- `Tyrano_Toolbox.exe` - 純粋ツールボックス
- `DevilConnection_Patch.exe` - 組み込み例パッチ付き（利用可能時）

### ソースからのビルド（Windows）

Python 3.8+ と Tkinter を用意してください。ビルド依存は `pyinstaller` と `pillow` です。

```cmd
git clone https://github.com/KouzakiUmi/DeviConHan.git
cd DeviConHan
.\Pack.cmd
```

`dist/`に出力：
- `Tyrano_Toolbox.exe`
- `Patch.zip` または空でない `Patch/` がある場合 `DevilConnection_Patch.exe`

### macOS / Linux

Python 3.8+ と動作する Tkinter が必要です。ビルドには PyInstaller とアイコン変換用の Pillow を使用します。実行時の ASAR 操作に外部 ASAR ライブラリや Node.js は不要です。

```bash
# ソースから実行
python3 main.py

# 現在の OS 向けにビルド
python3 -m pip install pyinstaller pillow
bash Pack.sh
```

パッチ版には既存の `Patch.zip` または空でない `Patch/` を用意してください。Pack スクリプトはディレクトリを優先して一時 ZIP を生成し、追跡中のパッチ資産は変更しません。

**注意**: 対象 OS 上でビルドしてください。`Pack.cmd` / `Pack.sh` は以前の `dist/` 出力と一時ビルドファイルを削除します。詳細は [PACK.md](PACK.md) を参照してください。

---

## 🎮 パッチ適用と復元

1. ゲームを終了し、パッチ適用タブで同梱パッチまたはカスタム ZIP を選択して適用します。両エディションに適用・復元機能があります。
2. 別のパッチに変更する場合は、先に Steam で整合性を確認するか元のファイルに戻し、対応するバージョンのパッチを適用してください。
3. ゲームファイルに異常がある場合は、まず Steam のプロパティ → インストール済みファイル → ゲームファイルの整合性を確認してください。

> 💡 **パッチの互換性**: 元の ASAR を展開し、新しい Patch で対応ファイルを上書きして再パックします。バージョンの不一致や既存の変更により、ファイルの混在、内容の不整合、起動不能が起こる可能性があります。

インストール記録にはパッチハッシュを保存し、同じパッチで適用状態が正常な場合のみ処理を省略します。異なるパッチやハッシュのない旧記録では GUI で復元方法を確認します。ローカルの元のバックアップを選ぶと、そのアーカイブから再構築します。古いバージョンの可能性があり、検証に合格してもパッチとの互換性は保証されません。

---

## セーブマネージャー

組み込みのSave Managerタブでプロ級のバックアップ/復元を提供：

- 検出したゲームパスからセーブディレクトリを自動探索。現在のセーブ先がなくても独立したバックアップを検索可能。
- タイムスタンプ付き独立バックアップ（ZIPまたはディレクトリ）。
- バックアップパス変更時に移行するか選択可能（コピーとハッシュ検証後に元のバックアップを削除）。
- 復元先を確認してワンクリック復元。現在のセーブ先がない場合は復元先を選択可能。
- ツールの応答性を保つ非同期操作。セーブ操作前にゲームを終了してください。
- 競合操作を防ぐロック。復元失敗時はロールバックを試み、変更なし・復旧済みとロールバック失敗を区別。

**注意**: パッチの適用・復元でセーブを直接変更しません。Steam のゲームファイル検証はセーブのバックアップ復元の代わりにはなりません。

実装詳細は[UTILS_GUIDE.md](UTILS_GUIDE.md)を参照。

---

## 開発者向け

日本語ドキュメント入口は [DOCS_INDEX_ja.md](DOCS_INDEX_ja.md)、完全なアーキテクチャと設計原則は [PROJECT_SPECS.md](PROJECT_SPECS.md) を参照。

**他のゲームへの適応**（上記参照）：configとPatch.zipを修正。現在のコードは`utils/asar_writer.py`による純粋Python ASAR処理、`utils/asar_utils.py`と`core/state_validator.py`での検証、bootstrap、state machineを採用。パッケージングスクリプトも現在のロジックに更新（node.exe依存をコア操作から除去）。

**現在のアーキテクチャ**（コード分析に基づく更新）:
- `main.py`: 引数解析、bootstrap、GUI/バッチモード。
- `core/`: bootstrap.py, patcher.py (`utils.asar_writer.asar_extract` / `asar_pack` を呼ぶ CoreLogic), config.py (スナップショット/TTL/ホットリロード/ユーザーディレクトリ優先のシングルトン), steam.py (ステートマシン), save_service.py, fuse.py, state_validator.py, patch_info.py, batch.py。
- `gui/`: main_window.py, tabs/(patch_tab.py, save_tab.py, tools_tab.py)。
- `controllers/`: patch_controller, save_manager_controller。
- `utils/`: language.py (システム言語検出+ini設定), paths.py, async_ops.py など。
- GUI はゲームファイルに異常があっても起動して復元案内を表示。インストール前の検証は引き続き実行。

**パッケージングスクリプト分析**:
- `Pack.cmd`/`Pack.sh`: 依存チェック、ツールボックスビルド、必要に応じた `Patch/` の一時ZIP化、パッチャービルド、クリーンアップ。現在のPyInstaller仕様と純Python ASARに更新。

**設定**:
全 OS でテンプレートから `~/.tyranopatcher/config.ini` へコピー。Windows の `~` は `%USERPROFILE%`。すべてのキーに対応。Toolsタブで検証/リセット可能。ログは既定で `~/.tyranopatcher/tyrano_patcher.log` に保存し、利用者向け進捗は選択言語、内部診断は英語で表示。

**実行ロジック**（コードから）:
1. Bootstrap: 設定ロード、パス、状態検証、中断処理の復旧。これらの検証は公式ファイルの認証ではありません。
2. パッチフロー: 選択したパッチと適用済みハッシュの比較、ゲーム状態検証、必要に応じた確認による元アーカイブ選択、バックアップ、抽出 (`utils.asar_writer.asar_extract`)、パッチ適用、再パック (`utils.asar_writer.asar_pack`)、メタ/情報原子性保存、クリーンアップ。
3. セーブ操作: ゲームディレクトリ独立、ZIP対応、ハッシュチェック付き移行。
4. Fuse除去: 設定可能オフセットによる実行ファイルの編集。独立した開発者操作であり、自動パッチ適用には含まれません。先にコピーで構造を検証してください。

詳細は`core/bootstrap.py`、`controllers/patch_controller.py`、`core/steam.py`のhandle_steam_update() (4ケースのステートマシン)、`gui/tabs/tools_tab.py`を分析してください。

---

## ライセンス

本プロジェクトは原作者**ばやちゃお (Bayachao)**氏の二次創作ガイドラインを厳守します。

- **非営利のみ**。商用利用禁止。
- パッチは翻訳/注入ファイルのみを含み、**ゲーム本体は含まれません**。
- ゲーム、キャラクター、デザインの全権利は原作者に帰属。

参照: [作者ガイドライン](https://bayachao.com/devil-connection/guideline)
ライセンス: [CC BY-NC-SA 4.0](https://creativecommons.org/licenses/by-nc-sa/4.0/)
