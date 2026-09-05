# 打包与分发指南

`Tyrano_Toolbox` 不含内置补丁，可选择自定义 ZIP；`DevilConnection_Patch` 含 `でびるコネクショん` 示例补丁。两者使用相同的安装、还原和存档功能。

## 构建前

在目标操作系统上准备 Python、Tkinter、源码、`config.ini` 和图标。项目声明 Python 3.8+；实际构建环境还需符合安装的 PyInstaller 版本要求。

```bash
python -m pip install pyinstaller pillow
```

运行核心 ASAR 操作无需第三方 `asar` 包或 Node.js。Pillow 用于 `Pack.sh` 的 macOS/Linux 图标转换。构建脚本会清理旧 `dist/`、构建目录及临时资源，不要把需要保留的文件放在这些目录中。

## Windows

在项目目录使用 PowerShell 或命令提示符：

```powershell
.\Pack.cmd
```

输出通常为 `dist/Tyrano_Toolbox.exe`，有补丁数据时另生成 `dist/DevilConnection_Patch.exe`。

## macOS / Linux

```bash
python3 -m pip install pyinstaller pillow
bash Pack.sh
```

脚本选择 `python3`，找不到时回退到 `python`，并转换图标。输出位于 `dist/`，具体形式由操作系统和 PyInstaller 决定。脚本按当前操作系统构建，不提供一个命令直接生成所有平台产物的流程。

## 补丁资源选择

1. 先构建不含补丁的工具箱。
2. 存在 `Patch.zip` 时将其作为候选内置补丁。
3. 存在非空 `Patch/` 时，将其压缩至 `.build_assets/Patch.zip`，优先用于补丁版。
4. 有可用补丁数据时构建补丁版，完成后清理临时构建文件。

脚本不覆盖仓库中的 `Patch.zip`。自定义 ZIP 可以单独分发，通过安装页选择；不必为了更换补丁重新打包工具。

## Python 包构建

`build_modern.py` 用于 wheel/sdist，和 PyInstaller 可执行文件是两条构建路径。

```bash
python -m pip install build
python -m build
```

Python 包入口为 `tyrano-patcher`。发布前应在隔离环境安装产物并检查入口及资源，不能用 CLI 帮助可运行代替 GUI 或实际补丁安装验证。

## 自动构建

当前工作流为 [.github/workflows/main.yml](.github/workflows/main.yml)。它在推送到 `main` 或手动触发时，在 Windows、macOS、Ubuntu 上构建，再更新 `nightly` 预发布。工作流另装了 `asar`，但核心代码不依赖它。

构建是否成功以对应 Actions 记录为准。工作流会替换已有 nightly 发布和标签；这不是版本归档。文档不复制工作流 YAML，以免参数与实现产生偏差。

## 分发与验收

- 附带使用说明和 [LICENSE](LICENSE)，注明补丁对应的游戏版本。
- 确认安装页能选择 ZIP、能展示恢复建议，并可进入存档和工具页面。
- 用游戏副本验证首次安装、相同包跳过、更换包、Steam 恢复后重装及本地还原。
- Windows、macOS、Linux 分别验证对应产物；源码测试通过不等于各平台 GUI 均已验证。
- 推送前检查工作区，显式选择源码、文档和补丁资产，避免将自用 ZIP 或临时目录一并提交。

```bash
python -m pytest -q -p no:cacheprovider
python main.py --help
git diff --check
```

## 用户数据位置与故障处理

所有平台默认使用用户主目录下的 `.tyranopatcher`：

| 内容 | 路径 |
|---|---|
| 配置 | `~/.tyranopatcher/config.ini` |
| 日志 | `~/.tyranopatcher/tyrano_patcher.log` |
| 存档备份 | `~/.tyranopatcher/backups` |

Windows 的 `~` 对应 `%USERPROFILE%`。打包进程序的 `config.ini` 是首次启动模板，不会自动覆盖已有用户配置。

工具自身启动失败时检查日志、资源和 Tkinter；需要查看控制台时可使用源码运行或构建不带 `-w` 的调试版本。游戏文件异常时优先通过 Steam 验证完整性，存档问题则使用独立备份恢复。
