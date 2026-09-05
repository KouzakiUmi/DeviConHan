# Tyrano Patch Toolbox

**The でびるコネクショん (Devil Connection) localization patch is the built-in example.**

**Developer Note**: This is a general-purpose toolbox for TyranoV8/Electron-based games. It can be adapted to other games by modifying `config.ini` (e.g. `WINDOWS_EXE`, `MACOS_APP`, `LINUX_BINARY`, `FUSE_SENTINEL`, `CHECK_FILES_FOR_UPDATE`) and providing a corresponding `Patch.zip` containing the game's localization files with matching directory structure, or selecting a custom ZIP in the GUI. Test compatibility with the target game version. See [PLUGIN_GUIDE.md](PLUGIN_GUIDE.md) for full plugin development guide.

<div align="center">

**🌐 Language Switch**

**[中文 🇨🇳](README.md)** • **[English 🇬🇧 (Current)](README_en.md)** • **[日本語 🇯🇵](README_ja.md)**

</div>

![Status](https://img.shields.io/badge/Status-RC-orange?style=flat-square)
![Platform](https://img.shields.io/badge/Platform-Win%20|%20Mac%20|%20Linux-blue?style=flat-square)
![License](https://img.shields.io/badge/License-CC%20BY--NC--SA%204.0-lightgrey?style=flat-square)
![Build](https://img.shields.io/badge/Build-Automated-success?style=flat-square)

> **By KouzakiUmi (呜咪 / 神前海)**


---

## Overview

This project is a non-profit personal localization toolbox for TyranoV8-based games, with the Devil Connection localization as the built-in example. It features a full GUI, cross-platform support (Windows/macOS/Linux), advanced save management, and developer tools.

**✨ Core Features:**

- **🚀 One-Click Patching**: Uses the bundled `Patch.zip` by default or a custom ZIP selected in the GUI, with automatic payload-root detection, backup, and manual original-file restoration.
- **💾 Professional Save Manager**: Independent backup location (`~/.tyranopatcher/backups`), ZIP/Dir support, smooth migration with hash verification.
- **🛠️ Developer Toolbox**: ASAR unpack/pack (using pure Python ASAR implementation), dynamic Fuse offset configuration, config validation.
- **⚙️ Isolated Config System**: User config in home dir with hot-reload, validation, and template fallback.
- **🔒 Safety Protections**: Concurrency locks, confirmation dialogs, hash checks, and recovery handling; use Steam verification first for game-file problems.
- **🌐 Multilingual**: Chinese/English/Japanese, runtime switching via menu.
- **📚 Comprehensive Docs**: Start with [DOCS_INDEX_en.md](DOCS_INDEX_en.md), then use [MODULE_GUIDE_en.md](MODULE_GUIDE_en.md), [PROJECT_SPECS.md](PROJECT_SPECS.md), [TECHNICAL_REFERENCE.md](TECHNICAL_REFERENCE.md), and [PLUGIN_GUIDE.md](PLUGIN_GUIDE.md).

---

## Installation

### Automatic Build (Recommended)

Releases are built automatically on main branch pushes. Download latest from [Releases](../../releases):
- `Tyrano_Toolbox.exe` - Pure toolbox
- `DevilConnection_Patch.exe` - With built-in example patch (when available)

### From Source (Windows)

Prepare Python 3.8+ with Tkinter; build dependencies are `pyinstaller` and `pillow`.

```cmd
git clone https://github.com/KouzakiUmi/DeviConHan.git
cd DeviConHan
.\Pack.cmd
```

Outputs in `dist/`:
- `Tyrano_Toolbox.exe`
- `DevilConnection_Patch.exe` (if `Patch.zip` or a nonempty `Patch/` is present)

### macOS / Linux

Requires Python 3.8+ with working Tkinter. Packaging additionally requires PyInstaller and Pillow for icon conversion; runtime ASAR operations do not require an external ASAR library or Node.js.

```bash
# Run from source
python3 main.py

# Build for the current operating system
python3 -m pip install pyinstaller pillow
bash Pack.sh
```

For the patch version, provide an existing `Patch.zip` or a nonempty `Patch/` directory. The pack scripts prefer the directory and stage a temporary `Patch.zip` without modifying tracked patch assets.

**Note**: Build on the target operating system. `Pack.cmd` and `Pack.sh` clear previous `dist/` output and temporary build assets. See [PACK.md](PACK.md) for details.

---

## 🎮 Patching and Restoration

1. Close the game, choose the bundled patch or a custom ZIP on the patch tab, then install. In the toolbox edition, first enable patch installation under Developer Tools → Configuration. You can then open the first tab and choose a ZIP. The bundled edition enables this option by default.
2. Before switching patches, verify game files in Steam or restore the original files, then install a patch for that game version.
3. For game-file problems, first use Steam Properties → Installed Files → Verify integrity of game files.

**🌐 English Patch**: [EnglishPatch.zip](EnglishPatch.zip) is the English-language patch for `でびるコネクショん` (Devil Connection). Select it as a custom ZIP using the steps above.

> 💡 **Patch compatibility**: The tool extracts the original ASAR, overwrites corresponding files with the new Patch, and repacks it. A mismatched game version or existing modifications may mix incompatible files, cause inconsistent content, or prevent the game from running.

The installation record stores a patch hash. An identical patch is skipped only when the installed state is healthy. A different patch or an older record without a hash prompts for recovery in the GUI. Confirming the local original backup rebuilds from that archive. The backup may be older than the current game; passing validation does not establish patch compatibility.

---

## Save Manager

The built-in Save Manager tab provides professional backup/restore:

- Automatic detection of save directories (`_storage`, `save`, etc.) using the detected game path. Existing independent backups remain accessible when the current save directory is missing.
- Timestamped backups (ZIP or directory) stored independently in `~/.tyranopatcher/backups`.
- Optional migration when changing backup paths (copy and verify hashes before deleting source backups).
- One-click restore with destination confirmation, including selecting a destination when the save directory is missing.
- Async operations keep the toolbox responsive; close the game before working with saves.
- Concurrency locks prevent conflicting operations; restore failures attempt rollback and distinguish unchanged or rolled-back data from rollback failure.

**Note**: Installing or restoring a patch does not directly modify saves. Steam game-file verification does not replace save-backup restoration.

See [UTILS_GUIDE.md](UTILS_GUIDE.md) for implementation details.

---

## For Developers

See [DOCS_INDEX_en.md](DOCS_INDEX_en.md) for the English documentation entry point and [PROJECT_SPECS.md](PROJECT_SPECS.md) for full architecture, design principles, and technical specs.

**Key Adaptation for Other Games** (as noted above): Modify config and Patch.zip. The code uses modern pure-Python ASAR handling via pure Python implementation in `utils/asar_writer.py` with fallback validation in `utils/asar_utils.py` and `core/state_validator.py`. Packaging scripts updated to reflect current logic (no node.exe dependency in core operations).

**Current Architecture Highlights** (updated from code analysis):
- `main.py`: Argparse, bootstrap, GUI or batch mode.
- `core/`: bootstrap.py, patcher.py (CoreLogic calling `utils.asar_writer.asar_extract` / `asar_pack`), config.py (singleton with snapshot/TTL/hot-reload/user-dir priority), steam.py (state machine), save_service.py, fuse.py, state_validator.py, patch_info.py, batch.py.
- `gui/`: main_window.py, about_dialog.py, tabs/ (patch_tab.py, save_tab.py, tools_tab.py).
- `controllers/`: patch_controller.py, save_manager_controller.py.
- `utils/`: language.py (system lang detection + ini prefs), paths.py (MEIPASS support), async_ops.py, file_ops.py, etc.
- GUI bootstrap allows access to recovery guidance when game files are damaged; installation still validates files before writing.

**Packaging Scripts**:
- `Pack.cmd` / `Pack.sh`: Check deps, build toolbox, stage `Patch/` as a temporary `Patch.zip` if needed, build patcher if present, cleanup. Updated to current PyInstaller specs and pure Python ASAR.

**Config**:
User config copied from template to `~/.tyranopatcher/config.ini` on all platforms; `~` means `%USERPROFILE%` on Windows. Supports all keys with fallbacks. Use Tools tab to validate/reset. Logs default to `~/.tyranopatcher/tyrano_patcher.log`; user-facing progress follows the selected language, while internal diagnostics use English.

**Log Display**: The default window is `800 × 800`, with a six-row log area, 10-point text, and extra line spacing. Chinese logs prefer an installed CJK monospace font, then a local CJK font such as Microsoft YaHei UI; the English interface retains monospace text.

**Running Logic** (from code):
1. Bootstrap: config load, paths, state checks and interrupted-operation recovery. These checks do not certify official game files.
2. Patch flow: compare source and installed patch hashes, check game state, select the original archive with confirmation when needed, backup, extract (`utils.asar_writer.asar_extract`), apply patch files, repack (`utils.asar_writer.asar_pack`), save meta/info atomically, cleanup.
3. Save ops: independent of game dir, ZIP support, migration with hash check.
4. Fuse removal: a separate developer operation, using a configurable offset to edit the executable. Validate the layout on a copy first; automatic patch installation does not perform this step.

For full details, analyze `core/bootstrap.py`, `controllers/patch_controller.py`, `core/steam.py handle_steam_update()` state machine (4 cases), and `gui/tabs/tools_tab.py`.

---

## License

This project strictly follows the original author **ばやちゃお (Bayachao)**'s derivative works guidelines.

- **Non-commercial only**. Commercial use prohibited.
- Patch contains only translation/injection files. **Does not include the game itself**.
- All rights to game, characters, designs belong to the original author.

Reference: [Author's Guideline](https://bayachao.com/devil-connection/guideline)
License: [CC BY-NC-SA 4.0](https://creativecommons.org/licenses/by-nc-sa/4.0/)
