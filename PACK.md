# 打包与分发指南

本文档详细介绍 **Tyrano补丁工具箱** 的打包和分发流程（基于Pack.cmd/Pack.sh脚本的最新运行逻辑）。

**注意**：`でびるコネクション`汉化补丁为自带示例，通过Patch.zip适配其他游戏。

---

## 目录

1. [打包前准备](#打包前准备)
2. [Windows 打包](#windows-打包)
3. [跨平台打包](#跨平台打包)
4. [自动构建](#自动构建)
5. [分发注意事项](#分发注意事项)

---

## 打包前准备

### 必需文件

确保以下文件和目录存在：

```
├── main.py              # 程序入口
├── config.ini           # 配置文件
├── icon.ico             # 程序图标
├── Pack.cmd             # Windows 构建脚本
├── core/                # 核心模块
├── gui/                 # GUI 模块
├── utils/               # 工具模块
├── controllers/         # 控制器模块
└── Patch/               # 汉化补丁源文件（可选）
```

### 依赖检查

**Windows**:
```cmd
# 检查 Python
python --version  # 需要 3.8+

# 检查 PyInstaller
pip install pyinstaller
```

**macOS/Linux**:
```bash
# 检查 Python
python3 --version  # 需要 3.8+

# 检查 PyInstaller
pip3 install pyinstaller
```

---

## Windows 打包

### 方法 1：使用 Pack.cmd（推荐）

```cmd
# 在项目根目录执行
.\Pack.cmd
```

Pack.cmd 会自动执行：
2. 如果存在 `Patch/` 目录，则在临时构建目录中生成一个 staged `Patch.zip`（不会修改工作区中的 `Patch/` 或已跟踪的 `Patch.zip`）
3. 构建纯净工具箱 (Tyrano_Toolbox.exe)
4. 构建汉化补丁版 (DevilConnection_Patch.exe)（如果 Patch/ 存在）
5. 清理临时文件

### 方法 2：手动打包

#### 纯净工具箱

```cmd
python -m PyInstaller -F -w --clean ^
    -i "icon.ico" ^
    --add-data "icon.ico:." ^
    --add-data "config.ini:." ^
    --name "Tyrano_Toolbox" ^
    main.py
```

#### 汉化补丁版

```cmd
# 首先压缩 Patch 目录
python -c "import shutil; shutil.make_archive('Patch', 'zip', 'Patch')"

# 然后打包
python -m PyInstaller -F -w --clean ^
    -i "icon.ico" ^
    --add-data "icon.ico:." ^
    --add-data "config.ini:." ^
    --add-data "Patch.zip:." ^
    --name "DevilConnection_Patch" ^
    main.py
```

### 打包参数说明

| 参数 | 说明 |
|------|------|
| `-F` | 单文件模式 |
| `-w` | 无控制台窗口 |
| `--clean` | 清理临时文件 |
| `-i` | 图标文件 |
| `--add-data` | 添加数据文件 |
| `--name` | 输出文件名 |

---

## 跨平台打包

### macOS

```bash
# 安装依赖
python3 -m pip install pyinstaller pillow

# 构建
python3 -m PyInstaller -F -w --clean \
    -i "icon.ico" \
    --add-data "icon.ico:." \

    --add-data "config.ini:." \
    --name "Tyrano_Toolbox" \
    main.py
```

### Linux

```bash
# 安装依赖
pip3 install pyinstaller

# 构建
python3 -m PyInstaller -F -w --clean \
    -i "icon.ico" \
    --add-data "icon.ico:." \

    --add-data "config.ini:." \
    --name "Tyrano_Toolbox" \
    main.py
```


---

## 自动构建

### GitHub Actions

项目配置了 GitHub Actions 自动构建工作流：

```yaml
# .github/workflows/build.yml
name: Build Executables

on:
  push:
    branches: [ main ]
  pull_request:
    branches: [ main ]

jobs:
  build:
    runs-on: windows-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.10'
      
      - name: Install dependencies
        run: pip install pyinstaller
      
      - name: Build
        run: .\Pack.cmd
      
      - name: Upload artifacts
        uses: actions/upload-artifact@v4
        with:
          name: executables
          path: dist/*.exe
```

### 自动发布

每次推送到 main 分支会自动：
1. 构建可执行文件
2. 生成 nightly 版本标签
3. 发布到 Releases 页面

---

## 分发注意事项

### 文件清单

分发时需要包含：

| 文件 | 说明 |
|------|------|
| `DevilConnection_Patch.exe` 或 `Tyrano_Toolbox.exe` | 主程序 |
| `README.md` | 使用说明 |
| `LICENSE` | 许可证文件 |

### 用户配置

首次运行时，程序会自动创建：
- **Windows**: `%APPDATA%/.tyranopatcher/config.ini`
- **macOS/Linux**: `~/.config/tyrano_patcher.ini`

### 日志位置

- **Windows**: `%USERPROFILE%/.tyranopatcher/tyrano_patcher.log`
- **macOS/Linux**: `~/.tyranopatcher/tyrano_patcher.log`

### 存档备份位置

- **Windows**: `%USERPROFILE%/.tyranopatcher/backups`
- **macOS/Linux**: `~/.tyranopatcher/backups`

---

## 常见问题

### Q: 打包后程序无法启动？

A: 检查以下几点：
1. 确保所有必需文件已正确打包
2. `config.ini` 是否存在
3. 是否以管理员权限运行

### Q: 如何减小打包体积？

A: 使用 UPX 压缩：
```cmd
pip install pyinstaller
python -m PyInstaller -F -w --upx-dir "C:\upx" ...
```

### Q: 如何调试打包问题？

A: 移除 `-w` 参数以保留控制台窗口：
```cmd
python -m PyInstaller -F --clean ...
```

### Q: 打包后图标不显示？

A: 确保图标文件格式正确（.ico for Windows, .icns for macOS）。

---

## 版本管理

### 版本号规范

使用语义化版本号：`主版本.次版本.修订号`

- **主版本**：重大更新，不兼容的 API 更改
- **次版本**：新功能，向后兼容
- **修订号**：Bug 修复，向后兼容

### 版本标记

```bash
# 确保工作区只包含要提交的源码/文档改动
git status

# 提交后再打 tag
git add .
git commit -m "Update ASAR validation, security checks, and packaging docs"

# 创建版本标签
git tag -a v1.0.0 -m "Release version 1.0.0"

# 推送标签
git push origin v1.0.0
```

### 推送前检查

- 运行 `python -m unittest tests.test_asar_utils tests.test_file_ops_security -v`
- 运行 `Pack.cmd` 或 `Pack.sh` 验证构建
- 确认工作区中没有误删的 `Patch/`、误覆盖的 `Patch.zip`、或临时生成的 `.build_assets/`

---

## 许可证声明

分发时必须包含以下声明：

```
本项目严格遵守原作者 ばやちゃお (Bayachao) 的《二次创作与同人活动指南》。
- 非营利：仅限非营利目的使用，严禁用于商业用途。
- 素材使用：本补丁仅包含运行所需的翻译文件与代码，不包含游戏本体。
- 版权归属：游戏的所有权利（原作，设计，人物等）均归 ばやちゃお 所有。

许可证：CC BY-NC-SA 4.0
```

---

*文档版本：1.0*  
*最后更新：2026-04-09*
