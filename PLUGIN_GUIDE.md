# 补丁适配指南

这里的“插件”指游戏配置和补丁文件包，不是可动态加载的代码插件系统。Tyrano 补丁工具箱以 `でびるコネクショん` 为示例，可为其他 Tyrano / Electron 游戏配置补丁流程。

## 准备补丁

补丁路径应与解包后的原始 ASAR 相对路径一致，只放入需要替换或增加的文件。例如：

```text
Patch/
├── tyrano/
│   └── lang.js
└── data/
    ├── others/
    │   └── font.ttf
    └── scenario/
        └── scene.ks
```

可将该目录压缩成 ZIP，然后在安装页选择，无需覆盖工具内置的 `Patch.zip`：

```bash
python -c "import shutil; shutil.make_archive('MyPatch', 'zip', 'Patch')"
```

支持根目录直接包含 `data/`、`tyrano/` 等内容，也支持 `Patch/data/` 或更深的单一包装层。根目录存在歧义时会停止，不能靠随意添加目录层级解决。

源码运行默认优先使用 `Patch.zip`，找不到时使用 `Patch/`；这两个名称可配置。区分大小写的文件系统中，请保持名称大小写一致。打包脚本有非空 `Patch/` 时优先将其压缩到临时构建目录，否则使用现有 `Patch.zip`。

## 配置目标游戏

首次启动后修改 `~/.tyranopatcher/config.ini`。发布新的独立构建时，还应调整仓库内的默认模板。

```ini
[main]
GAME_ID = YOUR_STEAM_APP_ID
AUTO_DETECT_GAME = true
WINDOWS_EXE = YourGame.exe
MACOS_APP = YourGame.app
LINUX_BINARY = yourgame

[files]
CHECK_FILES_FOR_UPDATE =
    tyrano/lang.js
    data/others/font.ttf
STABLE_FILES_FOR_VALIDATION =
    index.html
    main.js
    package.json
```

`GAME_ID` 可填 Steam App ID 或游戏目录名称。自动检测不适用时，设置 `AUTO_DETECT_GAME = false` 和 `GAME_PATH`。通过开发者工具中的“验证配置”检查配置格式。

`CHECK_FILES_FOR_UPDATE` 应选择能代表补丁状态的文件；仅检查这些文件不足以证明整个游戏未被修改。`STABLE_FILES_FOR_VALIDATION` 用于部分状态分支中的文件可读性判断，不是官方文件哈希清单。

## 安装与更换补丁

1. 关闭游戏，并通过 Steam 验证游戏文件完整性。
2. 选择适配当前游戏版本的 ZIP，运行安装。
3. 检查启动、字体、脚本跳转和使用到的资源；不要仅以“安装成功”判断兼容。
4. 如需更换补丁，先通过 Steam 验证完整性或还原原版文件。

工具解包原始 ASAR，用新 Patch 覆盖对应路径并增加新文件，然后重新打包。它不合并脚本，也没有“删除原始文件”的补丁清单。如果基础文件或游戏版本不匹配，可能导致文件混杂、内容错乱或无法运行。

安装记录中的 `patch_hash` 用于识别所选补丁包。不同包或没有指纹的旧安装需要恢复提示；GUI 中选择使用本地原版备份后，会从该备份重建。备份通过结构和文件检查不代表其版本与补丁兼容。详见 [技术参考](TECHNICAL_REFERENCE.md)。

## ASAR 与 Fuse 工具

开发者工具可单独解包和打包 ASAR。需要保留 `.unpacked` 配套资源，尤其是原生模块；不能只拷贝归档本体。包内文件可以是文本或二进制资源，替换是否有效取决于游戏如何使用它们。

Fuse 修改不属于自动安装流程。只有确认目标游戏的完整性机制后，才在副本上配置 `FUSE_SENTINEL`、`FUSE_WIRE_HEADER_LENGTH` 和 `FUSE_ASAR_INTEGRITY_OFFSET` 并测试。不要把“游戏无法启动”直接等同于“需要修改 Fuse”。

## 故障处理

| 现象 | 建议 |
|---|---|
| 安装后无法启动或内容异常 | 先通过 Steam 恢复游戏文件，再确认补丁对应的游戏版本 |
| 找不到补丁或文本未改变 | 检查所选 ZIP、名称大小写、根目录层级和内部相对路径 |
| 无法验证本地备份 | 停止使用该备份，通过 Steam 恢复 |
| 相同包被跳过 | 当前指纹与安装记录相同且状态正常；确认是否选中了新包 |
| 新压缩的相同内容被视为不同包 | ZIP 指纹包含压缩与元数据字节，重新压缩可能改变指纹 |

查看 `~/.tyranopatcher/tyrano_patcher.log`。Steam 文件验证不能替代存档恢复，需要单独使用存档备份。

## 分发

提供补丁 ZIP、适配的游戏版本、安装/还原说明、所需配置和联系方式。仅更改外置 ZIP 无法替换已打包进单文件程序的内置资源，用户应通过界面选择 ZIP，或重新构建内置补丁版。

不要包含游戏本体或无权分发的资源。构建方法见 [PACK.md](PACK.md)，项目许可见 [LICENSE](LICENSE)。
