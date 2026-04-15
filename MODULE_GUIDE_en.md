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

Use `API_DOCS.md` and the source code for signature-level detail.

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
| `core.batch` | Non-GUI batch patch flow | `batch_mode()` is the automation-friendly entry; `_validate_fuse_path()` guards risky file targets. |
| `core.fuse` | Electron Fuse backup, verification, restore, and patching | Exposes `remove_fuse()`, `restore_fuse()`, `verify_fuse_backup()`; backup availability is checked mainly via sentinel/byte validation, with full-hash verification during backup creation and restore. |
| `core.patch_info` | Patch metadata persistence | `has_embedded_patch()` detects bundled patch data; save helpers use atomic writes. |
| `core.state_validator` | System state consistency checks | `StateValidator` and `validate_system_state()` aggregate ASAR, backup, patch-meta, and patch-info health. |
| `core.steam` | Steam update detection and patch state machine | `handle_steam_update()` covers missing backup, overwritten ASAR, and tampering branches. |

---

## GUI Tabs

| Module | Responsibility | Notes |
|------|------|------|
| `gui.tabs.patch_tab` | Patch-install tab | Handles patch-path input, main patch actions, and UI state feedback. |
| `gui.tabs.save_tab` | Save-management tab | Connects to `SaveManagerController` for scan, backup, restore, delete, and migration flows. |
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
| `utils.transaction` | Transactional file operations | `FileTransaction`, `atomic_rename()`, and `safe_backup()` support rollback-safe workflows. |

---

## Multilingual Docs And Code Rules

### Documentation

- User-facing overview docs are split by language: `README.md` / `README_en.md` / `README_ja.md`
- Documentation navigation is also split by language: `DOCS_INDEX.md` / `DOCS_INDEX_en.md` / `DOCS_INDEX_ja.md`
- This module guide follows the same pattern

### Runtime i18n

- All UI text should go through `utils.language.T(key)`
- Every new key must be added for `cn`, `en`, and `jp`
- In the current code, persisted language preference is written by `utils.language` through `core.config`; `utils.config_bridge` is an available decoupling hook, not the only active path

---

## Suggested Reading Order

1. `README*`
2. `DOCS_INDEX*`
3. `PROJECT_SPECS.md`
4. `MODULE_GUIDE*`
5. `UTILS_GUIDE.md`
6. `API_DOCS.md`

---

*Document version: 1.0*  
*Last updated: 2026-04-16*
