# 打包脚本调整和清理

## 更改摘要

### 0. 修复asar依赖处理
- 🔧 **core/patcher.py**: 添加了对asar库可用性的检查和错误处理
  - 添加延迟导入和可用性检查
  - 在asar不可用时提供清晰的错误信息
- ✅ **验证通过**: 程序正确处理asar库的可用性，asar仍然是必要的运行时依赖

### 1. 移除过时的asar依赖引用
- **Pack.cmd**: 移除了 `pip install pyinstaller asar` 中的 `asar`
- **Pack.sh**: 移除了 `pip install pyinstaller asar` 中的 `asar`
- **GitHub Actions**: 移除了workflow中的asar安装

### 2. 添加pyproject.toml支持提示
- 在两个打包脚本中添加了使用 `pip install -e .` 的替代安装说明
- 展示了如何使用现代Python打包方式

### 3. 改进脚本标识
- 在脚本标题中添加了"Pure Python ASAR Implementation"标识
- 明确说明项目使用纯Python实现，不依赖外部asar工具

### 4. 增强清理逻辑
- Pack.cmd: 添加了对递归__pycache__目录的清理

### 5. 添加现代构建脚本 (build_modern.py)
- 创建了可选的现代Python构建脚本
- 展示了如何使用pyproject.toml进行wheel和sdist构建
- 包含版本检查和依赖安装逻辑

## 技术细节

### asar依赖说明
- 项目使用 `asar` Python库进行asar文件的解包/打包操作
- 这是必要的运行时依赖，用于开发者工具中的asar操作
- 构建脚本不再自动安装asar（需要用户手动安装）

### 构建方式对比

| 方式 | 用途 | 命令 |
|------|------|------|
| PyInstaller | 可执行文件构建 | `Pack.cmd` / `Pack.sh` |
| setuptools | Python包构建 | `pip install -e .` |
| build模块 | 现代打包 | `python build_modern.py` |

### 验证结果
- ✅ 脚本语法检查通过
- ✅ PyInstaller可用性确认
- ✅ 构建流程逻辑保持完整

## 影响
- **构建时间**: 略微减少（不需要自动安装asar）
- **兼容性**: 保持（asar是标准Python包）
- **维护性**: 改善（正确的依赖处理）
- **运行时依赖**: 需要asar包（用于asar操作功能）
- **用户体验**: 功能型工具，GUI主要为操作便利性设计

## 功能定位确认
- **核心功能**: TyranoV8游戏汉化补丁一键安装工具
- **插件机制**: 通过patch.zip文件替换实现多游戏支持
- **GUI设计**: 功能导向，非美化需求
- **语言支持**: 中英文足够（Tyrano游戏主流语言）
- **测试策略**: 功能简单，无需复杂测试系统

---
*更新时间: 2026-04-12*