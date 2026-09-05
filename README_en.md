# Tyrano Patch Toolbox

[中文](README.md) · [English](README_en.md) · [日本語](README_ja.md)

Patch installation, save management, and ASAR tools for Tyrano / Electron games. The localization patch for `でびるコネクショん` is the bundled example.

By KouzakiUmi（呜咪 / 神前海）

## Getting started

Download the build for your operating system from [Releases](../../releases):

- `Tyrano_Toolbox`: no bundled patch; select a custom ZIP in the GUI.
- `DevilConnection_Patch`: includes the example patch; built when patch assets are available.

Both builds provide patch installation, original-file restoration, save management, and developer tools.

1. Close the game and start the toolbox.
2. On the patch tab, choose the bundled patch or a custom ZIP, then install.
3. Before switching patches, verify game files in Steam or restore the original game files, then install a patch for that game version.

## Switching patches and recovering game files

The tool extracts the original ASAR, overwrites corresponding files with the new Patch, and repacks it. A version mismatch or pre-existing modifications can mix incompatible files, cause inconsistent content, or prevent the game from running.

For game-file problems, first open the game's Steam Properties → Installed Files → Verify integrity of game files. You can also confirm restoration from a local original backup in the toolbox. That backup may be older than the current game; passing file checks does not establish patch compatibility.

The installation record stores a patch hash. An identical package is skipped only when the installed state is healthy. A different package or an older record without a hash prompts for a recovery approach. If you choose the local backup, the tool rebuilds from that original archive instead of layering patches.

## Save management

- Detects `_storage`, `save`, `SaveData`, and `UserData`; supports ZIP and directory backups.
- Defaults to `~/.tyranopatcher/backups`. You can change the location and choose whether to migrate existing backups.
- Confirms the restore destination. Existing backups remain selectable when the current save directory is missing.
- Attempts rollback after restore failures and distinguishes success, unchanged or rolled-back data, and rollback failure.

**Steam game-file verification does not replace save-backup restoration.** Installing or removing a patch does not directly modify saves.

## Running or building from source

Requires Python 3.8+ and working Tkinter. Runtime ASAR operations need neither a third-party ASAR library nor Node.js.

```bash
python main.py
python main.py --help
```

For packaging, install `pyinstaller` and `pillow` (`Pack.sh` uses Pillow for icon conversion), then run on the target operating system:

```powershell
python -m pip install pyinstaller pillow
.\Pack.cmd
```

```bash
python3 -m pip install pyinstaller pillow
bash Pack.sh
```

Outputs are placed in `dist/`. Scripts clean previous build outputs. An existing `Patch.zip` or nonempty `Patch/` also produces the patch edition. See the [packaging guide](PACK.md) (Chinese).

## Configuration and logs

| Content | Default location |
|---|---|
| User configuration | `~/.tyranopatcher/config.ini` |
| Log | `~/.tyranopatcher/tyrano_patcher.log` |
| Save backups | `~/.tyranopatcher/backups` |

On Windows, `~` means `%USERPROFILE%`. The first launch copies the bundled configuration template; later launches use the user copy. The language menu selects Chinese, English, or Japanese. User-facing messages and progress follow this setting; technical diagnostic logs remain English.

## Development and adaptation

- [Documentation index](DOCS_INDEX_en.md): choose a guide by task.
- [Technical reference](TECHNICAL_REFERENCE.md) (Chinese): CLI, patch hashes, transactions, and recovery contracts.
- [Project specifications](PROJECT_SPECS.md) (Chinese) and [module guide](MODULE_GUIDE_en.md): design boundaries and module responsibilities.
- [Patch adaptation guide](PLUGIN_GUIDE.md) (Chinese): game configuration and patch layout.

Configuration changes and a patch package are the starting point for adaptation; test the result against the target game version. Fuse editing is a separate developer action, not part of automatic patch installation.

## Copyright and license

The project follows original author **ばやちゃお (Bayachao)**'s [derivative-work guidelines](https://bayachao.com/devil-connection/guideline). Non-commercial use only. Patches do not include the game itself. Rights to the game, characters, and assets belong to the original author.

Project license: [CC BY-NC-SA 4.0](https://creativecommons.org/licenses/by-nc-sa/4.0/); see [LICENSE](LICENSE).
