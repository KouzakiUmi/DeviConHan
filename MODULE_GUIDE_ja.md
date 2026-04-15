# モジュール補足ガイド

> これまでコードや断片的な API 一覧にしか現れていなかったモジュールの要点を整理した簡易リファレンスです。

<div align="center">

**🌐 言語切替**

**[中文 🇨🇳](MODULE_GUIDE.md)** • **[English 🇬🇧](MODULE_GUIDE_en.md)** • **[日本語 🇯🇵 (現在)](MODULE_GUIDE_ja.md)**

</div>

---

## 対象範囲

この文書は次の不足を補います。

- `API_DOCS.md` で体系的に説明されていないモジュール
- README では短く触れられるだけだった実行時/ビルド/UI モジュール
- 他の Tyrano/Electron ゲームへ適応する際に見落としやすい責務境界

関数シグネチャの詳細は `API_DOCS.md` とソースコードを参照してください。

---

## 入口とビルド

| モジュール | 役割 | 主な入口 |
|------|------|----------|
| `main.py` | 全体の起動入口。CLI 解析、言語初期化、bootstrap、GUI/バッチ分岐 | `parse_arguments()` / `main()` |
| `build_modern.py` | wheel/sdist 向けの現代的な Python ビルド補助 | `install_build()` / `build_wheel()` / `build_sdist()` / `main()` |
| `scripts/check_code.py` | ローカルコード品質チェック補助スクリプト | `run_command()` / `main()` |

---

## Core モジュール

| モジュール | 役割 | 説明 |
|------|------|------|
| `core.batch` | GUI なしのバッチ適用フロー | `batch_mode()` が自動化向け入口で、`_validate_fuse_path()` が危険な対象パスを検証します。 |
| `core.fuse` | Electron Fuse のバックアップ、検証、復元、無効化 | `remove_fuse()`、`restore_fuse()`、`verify_fuse_backup()` を提供し、バックアップ可用性は主にセンチネル/対象バイトで確認し、作成と復元時に完全ハッシュで検証します。 |
| `core.patch_info` | パッチメタデータ保存 | `has_embedded_patch()` は同梱パッチ有無を判定し、保存処理は原子的に行われます。 |
| `core.state_validator` | システム状態の整合性検証 | `StateValidator` と `validate_system_state()` が ASAR、バックアップ、パッチメタデータ、パッチ情報を集約します。 |
| `core.steam` | Steam 更新検出とパッチ状態機械 | `handle_steam_update()` がバックアップ欠落、ASAR 上書き、改ざん疑いを処理します。 |

---

## GUI タブ

| モジュール | 役割 | 説明 |
|------|------|------|
| `gui.tabs.patch_tab` | パッチ適用タブ | パッチ入力、主要ボタン、進行状況表示を担当します。 |
| `gui.tabs.save_tab` | セーブ管理タブ | `SaveManagerController` と連携して走査、バックアップ、復元、削除、移行を行います。 |
| `gui.tabs.tools_tab` | 開発者ツールタブ | ASAR 展開/再梱包、Fuse 編集、設定検証、関連ユーティリティをまとめます。 |

---

## Utils 補足モジュール

| モジュール | 役割 | 説明 |
|------|------|------|
| `utils.asar_writer` | 純粋 Python による ASAR 読み書き | `asar_pack()` と `asar_extract()` で旧 Node.js 依存を置き換えます。 |
| `utils.config_bridge` | config と language/error の橋渡し層 | コールバック登録による疎結合化のための層で、現在の言語保存はなお `core.config` への直接書き込みが主体です。 |
| `utils.disk_utils` | ディスク容量と書き込み権限の確認 | bootstrap とパッチ前チェックで使われますが、すべてのファイル操作に自動適用されるわけではありません。 |
| `utils.operation_lock` | 操作単位の排他制御 | パッチ/セーブ/ツール系の競合書き込みを防ぎます。 |
| `utils.platform` | クロスプラットフォームのゲーム/Steam 探索 | Steam ライブラリ走査、リソース位置推定、OS 差異吸収を行います。 |
| `utils.transaction` | トランザクション型ファイル操作 | `FileTransaction`、`atomic_rename()`、`safe_backup()` でロールバック安全性を確保します。 |

---

## 多言語ドキュメントとコード規約

### ドキュメント

- 利用者向け概要は言語別に分離: `README.md` / `README_en.md` / `README_ja.md`
- ドキュメント索引も言語別: `DOCS_INDEX.md` / `DOCS_INDEX_en.md` / `DOCS_INDEX_ja.md`
- このモジュールガイドも同じ構成です

### 実行時 i18n

- UI 文言は必ず `utils.language.T(key)` を経由する
- 新規キーは `cn` / `en` / `jp` を同時に追加する
- 現在のコードでは言語設定の永続化は `utils.language` から `core.config` へ直接行われ、`utils.config_bridge` は利用可能な疎結合フックとして残っています

---

## 推奨読書順

1. `README*`
2. `DOCS_INDEX*`
3. `PROJECT_SPECS.md`
4. `MODULE_GUIDE*`
5. `UTILS_GUIDE.md`
6. `API_DOCS.md`

---

*文書版: 1.0*  
*最終更新: 2026-04-16*
