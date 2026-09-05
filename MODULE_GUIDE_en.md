# Module Guide

> Quick reference for modules that were previously only visible in code or sparse API listings.

<div align="center">

**🌐 Language Switch**

**[中文 🇨🇳](MODULE_GUIDE.md)** • **[English 🇬🇧 (Current)](MODULE_GUIDE_en.md)** • **[日本語 🇯🇵](MODULE_GUIDE_ja.md)**

</div>

---

## Scope

This guide fills the gap for:

- modules not clearly described in `API_DOCS.md`
- runtime/build/UI modules only mentioned briefly in the READMEs
- adaptation-related boundaries that are easy to miss when reusing the toolbox for another Tyrano/Electron game

Use the [technical reference](TECHNICAL_REFERENCE.md) and source for current contracts and recovery boundaries. `API_DOCS.md` is a historical index.

---

## Entry And Build

| Module | Responsibility | Key entry points |
|------|------|----------|
| `main.py` | Top-level entry point, CLI parsing, language init, bootstrap, GUI/batch selection | `parse_arguments()` / `main()` |
| `build_modern.py` | Modern Python packaging helper for wheel/sdist workflows | `install_build()` / `build_wheel()` / `build_sdist()` / `main()` |
| `scripts/check_code.py` | Local code-quality helper script | `run_command()` / `main()` |

---

## Core Modules

| Module | Responsibility | Notes |
|------|------|------|
| `core.bootstrap` | Startup checks and interrupted-operation recovery | The GUI uses `allow_recovery=True` so damaged files do not prevent access to recovery guidance. |
| `core.batch` | Non-GUI batch patch flow | `batch_mode()` is the automation-friendly entry; `_validate_fuse_path()` guards risky file targets. |
| `core.fuse` | Electron Fuse backup, verification, restore, and patching | Exposes `remove_fuse()`, `restore_fuse()`, `verify_fuse_backup()`; backup availability is checked mainly via sentinel/byte validation, with full-hash verification during backup creation and restore. |
| `core.patch_info` | Patch metadata persistence | `get_patch_hash()` fingerprints the patch source; `load_patch_hash()` reads `.patch_meta.patch_hash`. Save helpers use atomic writes. |
| `core.state_validator` | System state consistency checks | `StateValidator` and `validate_system_state()` aggregate ASAR, backup, patch-meta, and patch-info health. |
| `core.steam` | Steam update detection and patch state machine | `handle_steam_update()` covers missing backup, overwritten ASAR, and tampering branches. |

---

## GUI Tabs

| Module | Responsibility | Notes |
|------|------|------|
| `gui.tabs.patch_tab` | Patch-install tab | Available in both editions. Enabled by default when bundled; the toolbox tab stays disabled until enabled in Developer Tools, and installation requires a selected ZIP. The main page gives operation guidance; confirmation dialogs explain risks. |
| `gui.tabs.save_tab` | Save-management tab | Connects to `SaveManagerController` for scan, backup, restore, delete, and migration. Separate backups remain accessible when the save directory is missing; users can select a restore destination. |
| `gui.tabs.tools_tab` | Developer tools tab | Hosts ASAR pack/extract, Fuse editing, config validation, and related utilities. |

---

## Additional Utils Modules

| Module | Responsibility | Notes |
|------|------|------|
| `utils.asar_writer` | Pure-Python ASAR read/write implementation | `asar_pack()` and `asar_extract()` replace the old external Node.js dependency. |
| `utils.config_bridge` | Bridge layer between config and language/error modules | Exposes callback registration for decoupling; the current language-persistence path still writes through `core.config` directly. |
| `utils.disk_utils` | Disk-space and write-permission checks | Used by bootstrap and patching prechecks; not every file operation invokes it automatically. |
| `utils.operation_lock` | Operation-scoped mutual exclusion | Prevents conflicting patch/save/toolbox write operations. |
| `utils.platform` | Cross-platform game and Steam discovery | Scans Steam libraries, locates app resources, and resolves platform-specific paths. |
| `utils.transaction` | Transactional file operations | Provides general helpers such as `FileTransaction`; the patch controller uses its own transaction markers and recovery flow. |

---

## Multilingual Docs And Code Rules

### Documentation

- User-facing overview docs are split by language: `README.md` / `README_en.md` / `README_ja.md`
- Documentation navigation is also split by language: `DOCS_INDEX.md` / `DOCS_INDEX_en.md` / `DOCS_INDEX_ja.md`
- This module guide follows the same pattern

### Runtime i18n

- UI text, user-facing progress and disk-space reports should use `utils.language.T(key)`; internal diagnostic logs use English
- Add each new key for `cn`, `en`, and `jp` with matching format arguments; order confirmations as question, effect, recommendation
- In the current code, persisted language preference is written by `utils.language` through `core.config`; `utils.config_bridge` is an available decoupling hook, not the only active path

---

## Suggested Reading Order

1. `README*`
2. `DOCS_INDEX*`
3. `PROJECT_SPECS.md`
4. `MODULE_GUIDE*`
5. `UTILS_GUIDE.md`
6. `TECHNICAL_REFERENCE.md`
