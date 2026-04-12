# Tyrano Patch Toolbox

**The でびるコネクション (Devil Connection) localization patch is the built-in example.**

**Developer Note**: This is a general-purpose toolbox for TyranoV8/Electron-based games. It can be adapted to other games by modifying `config.ini` (e.g. `AUTO_TARGET_EXE`, `FUSE_SENTINEL`, `CHECK_FILES_FOR_UPDATE`, `TARGET_ASAR_NAME`) and providing a corresponding `patch.zip` containing the game's localization files with matching directory structure. See [PLUGIN_GUIDE.md](PLUGIN_GUIDE.md) for full plugin development guide.

<div align="center">

**🌐 Language Switch**

**[中文 🇨🇳](README.md)** • **[English 🇬🇧 (Current)](README_en.md)** • **[日本語 🇯🇵](README_ja.md)**

</div>

![Status](https://img.shields.io/badge/Status-RC-orange?style=flat-square)
![Platform](https://img.shields.io/badge/Platform-Win%20|%20Mac%20|%20Linux-blue?style=flat-square)
![License](https://img.shields.io/badge/License-CC%20BY--NC--SA%204.0-lightgrey?style=flat-square)
![Build](https://img.shields.io/badge/Build-Automated-success?style=flat-square)

> **By KouzakiUmi (呜咪 / 神前海)**

> [!NOTE]
> Rebuilt with AI, cost me HKD$1500 💸

---

## Overview

This project is a non-profit personal localization toolbox for TyranoV8-based games, with the Devil Connection localization as the built-in example. It features a full GUI, cross-platform support (Windows/macOS/Linux), advanced save management, and developer tools.

**✨ Core Features:**

- **🚀 One-Click Patching**: Graphical interface for automatic patch installation, backup, and Fuse integrity check removal.
- **💾 Professional Save Manager**: Independent backup location (`~/.tyranopatcher/backups`), ZIP/Dir support, smooth migration with hash verification.
- **🛠️ Developer Toolbox**: ASAR unpack/pack (using Python `asar` library), dynamic Fuse offset configuration, config validation.
- **⚙️ Isolated Config System**: User config in home dir with hot-reload, validation, and template fallback.
- **🔒 Safety Protections**: Concurrency locks, confirmation dialogs, hash checks, atomic writes.
- **🌐 Multilingual**: Chinese/English/Japanese, runtime switching via menu.
- **📚 Comprehensive Docs**: See [PROJECT_SPECS.md](PROJECT_SPECS.md), [API_DOCS.md](API_DOCS.md), [PLUGIN_GUIDE.md](PLUGIN_GUIDE.md).

---

## Installation

### Automatic Build (Recommended)

Releases are built automatically on main branch pushes. Download latest from [Releases](../../releases):
- `Tyrano_Toolbox.exe` - Pure toolbox
- `DevilConnection_Patch.exe` - With built-in example patch (when available)

### From Source (Windows)

```cmd
git clone <repo-url>
cd DeviConHan
.\Pack.cmd
```

Outputs in `dist/`:
- `Tyrano_Toolbox.exe`
- `DevilConnection_Patch.exe` (if Patch.zip or Patch/ present)

### macOS / Linux

Requires Python 3.8+, PyInstaller.

```bash
pip install pyinstaller
python -m PyInstaller -F -w --clean -i "icon.ico" \
  --add-data "icon.ico:." \
  --add-data "config.ini:." \
  --name "Tyrano_Toolbox" main.py
```

For patch version, prepare `Patch.zip` first using `python -c "import shutil; shutil.make_archive('Patch', 'zip', 'Patch')"` then add `--add-data "Patch.zip:." --name "DevilConnection_Patch"`.

**Note**: Pack.cmd and Pack.sh automatically handle Patch/ -> Patch.zip compression for better startup performance and build the appropriate executables.

---

## Save Manager

The built-in Save Manager tab provides professional backup/restore:

- Automatic detection of save directories (`_storage`, `save`, etc.).
- Timestamped backups (ZIP or directory) stored independently in `~/.tyranopatcher/backups`.
- Smooth migration when changing backup paths (with hash verification).
- One-click restore with confirmation.
- Async operations to not block UI.
- Concurrent safety locks.

See [UTILS_GUIDE.md](UTILS_GUIDE.md) for implementation details.

---

## For Developers

See [PROJECT_SPECS.md](PROJECT_SPECS.md) for full architecture, design principles, and technical specs.

**Key Adaptation for Other Games** (as noted above): Modify config and patch.zip. The code uses modern pure-Python ASAR handling via the `asar` package with fallback validation in `utils/asar_utils.py` and `core/state_validator.py`. Packaging scripts updated to reflect current logic (no node.exe dependency in core operations).

**Current Architecture Highlights** (updated from code analysis):
- `main.py`: Argparse, bootstrap, GUI or batch mode.
- `core/`: bootstrap.py, patcher.py (CoreLogic with delayed asar import), config.py (singleton with snapshot/TTL/hot-reload/user-dir priority), steam.py (state machine), save_service.py, fuse.py, state_validator.py, patch_info.py, batch.py.
- `gui/`: main_window.py, about_dialog.py, tabs/ (patch_tab.py, save_tab.py, tools_tab.py).
- `controllers/`: patch_controller.py, save_manager_controller.py.
- `utils/`: language.py (system lang detection + ini prefs), paths.py (MEIPASS support), async_ops.py, file_ops.py, etc.
- Bootstrap performs comprehensive system checks before launching.

**Packaging Scripts**:
- `Pack.cmd` / `Pack.sh`: Check deps, build toolbox, detect/compress Patch to Patch.zip, build patcher if present, cleanup. Updated to current PyInstaller specs and pure Python ASAR.

**Config**:
User config copied from template to `~/.tyranopatcher/config.ini` (or equivalent). Supports all keys with fallbacks. Use Tools tab to validate/reset.

**Running Logic** (from code):
1. Bootstrap: config load, paths, state validation (ASAR/bak/meta integrity via hashes).
2. Patch flow: Steam update detection (using patch_meta hashes), backup, extract (asar.extract_archive), apply patch files, repack (asar.create_archive), save meta/info atomically, cleanup.
3. Save ops: independent of game dir, ZIP support, migration with hash check.
4. Fuse removal: configurable offset, binary patch on EXE.

For full details, analyze `core/bootstrap.py`, `controllers/patch_controller.py`, `core/steam.py handle_steam_update()` state machine (4 cases), and `gui/tabs/tools_tab.py`.

---

## License

This project strictly follows the original author **ばやちゃお (Bayachao)**'s derivative works guidelines.

- **Non-commercial only**. Commercial use prohibited.
- Patch contains only translation/injection files. **Does not include the game itself**.
- All rights to game, characters, designs belong to the original author.

Reference: [Author's Guideline](https://bayachao.com/devil-connection/guideline)

License: [CC BY-NC-SA 4.0](https://creativecommons.org/licenses/by-nc-sa/4.0/)

*Updated based on comprehensive code analysis including packaging scripts, current running logic (pure Python ASAR, bootstrap, state validation, config isolation, atomic writes), and plugin system. All other MD documents (PROJECT_SPECS.md, PACK.md, PLUGIN_GUIDE.md, UTILS_GUIDE.md, API_DOCS.md, BUILD_SCRIPT_UPDATES.md, STANDARDIZATION_CHANGES.md, DOCS_INDEX.md) have been reviewed and aligned with current implementation.*

*Last updated: 2026-04-12*
