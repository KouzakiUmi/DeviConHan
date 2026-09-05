# Tyrano 补丁工具箱

[中文](README.md) · [English](README_en.md) · [日本語](README_ja.md)

面向 Tyrano / Electron 游戏的补丁安装、存档管理和 ASAR 工具。`でびるコネクショん` 汉化补丁为内置示例。

By KouzakiUmi（呜咪 / 神前海）

## 开始使用

从 [Releases](../../releases) 下载对应系统的构建：

- `Tyrano_Toolbox`：不含内置补丁，可在界面选择自定义 ZIP。
- `DevilConnection_Patch`：包含示例补丁；有补丁资源时生成。

两种构建均提供安装、原版文件还原、存档管理和开发者工具页面。

1. 关闭游戏，启动工具。
2. 在“安装补丁”页选择内置补丁或自定义 ZIP，然后点击安装。
3. 如需更换补丁，先通过 Steam 验证游戏文件完整性，或还原原版游戏文件，再安装对应版本的补丁。

## 更换补丁与恢复游戏

工具会解包原始 ASAR，用新 Patch 覆盖对应文件，再重新打包。补丁与游戏版本不匹配，或原始文件已有其他修改时，可能导致文件混杂、内容错乱或游戏无法运行。

遇到异常时，优先在 Steam 库中打开游戏的“属性 → 已安装文件 → 验证游戏文件的完整性”。也可在工具中确认使用本地原版备份还原；备份可能早于当前游戏版本，文件校验通过不代表与新补丁兼容。

安装记录包含补丁哈希。相同补丁且安装状态正常时会跳过；不同补丁或旧记录缺少哈希时，会提示恢复方式。选择本地备份继续时，程序从原版备份重新构建，不在上一份补丁上叠加。

## 存档管理

- 自动查找 `_storage`、`save`、`SaveData`、`UserData`，支持 ZIP 或目录备份。
- 默认备份位置为 `~/.tyranopatcher/backups`，可在界面更改并选择是否迁移已有备份。
- 还原前确认目标路径；当前存档目录丢失时，仍可选择现有备份和恢复位置。
- 存档还原失败时会尝试回滚，并区分成功、未修改或已回滚、回滚失败。

**Steam 验证游戏文件不能代替存档备份恢复。** 安装/卸载补丁不会主动修改存档。

## 从源码运行或打包

需要 Python 3.8+ 和可用的 Tkinter；运行时不依赖第三方 ASAR 库或 Node.js。

```bash
python main.py
python main.py --help
```

打包时安装 `pyinstaller` 和 `pillow`（`Pack.sh` 使用 Pillow 转换图标），然后在目标操作系统执行：

```powershell
python -m pip install pyinstaller pillow
.\Pack.cmd
```

```bash
python3 -m pip install pyinstaller pillow
bash Pack.sh
```

构建输出位于 `dist/`。脚本会清理旧构建产物；已有 `Patch.zip` 或非空 `Patch/` 时还会构建补丁版。详见 [打包指南](PACK.md)。

## 配置与日志

| 内容 | 默认位置 |
|---|---|
| 用户配置 | `~/.tyranopatcher/config.ini` |
| 日志 | `~/.tyranopatcher/tyrano_patcher.log` |
| 存档备份 | `~/.tyranopatcher/backups` |

Windows 中 `~` 对应 `%USERPROFILE%`。首次启动从内置模板创建用户配置，之后以用户配置为准。通过语言菜单切换中文、英文或日文；面向用户的提示和进度随语言切换，技术诊断日志保留英文。

## 开发与适配

- [文档索引](DOCS_INDEX.md)：按任务查找文档。
- [技术参考](TECHNICAL_REFERENCE.md)：CLI、补丁哈希、事务与恢复契约。
- [项目规范](PROJECT_SPECS.md)与[模块指南](MODULE_GUIDE.md)：设计边界和模块职责。
- [补丁适配指南](PLUGIN_GUIDE.md)：配置其他游戏、组织补丁文件。

修改 `config.ini` 与提供补丁包是适配的起点，还需要在目标游戏版本上验证效果。Fuse 编辑是独立的开发者操作，不由自动安装流程执行。

## 版权与许可

本项目遵循原作者 **ばやちゃお（Bayachao）** 的[二次创作指南](https://bayachao.com/devil-connection/guideline)。仅供非商业用途；补丁不包含游戏本体。游戏、角色和素材的权利归原作者所有。

项目许可证：[CC BY-NC-SA 4.0](https://creativecommons.org/licenses/by-nc-sa/4.0/)，详见 [LICENSE](LICENSE)。
