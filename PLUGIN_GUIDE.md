# 插件开发指南

## 概述

《恶魔链接》汉化工具采用**文件替换**机制实现插件系统。通过替换 `patch.zip` 文件，可以轻松适配不同游戏，无需修改代码。

---

## 插件机制原理

### 核心设计
- **无复杂API**：不使用传统的插件架构，而是通过文件替换实现
- **即插即用**：替换 `patch.zip` 文件后即可使用
- **开发者友好**：提供asar解包/打包工具进行手动修改

### 工作流程
```
游戏汉化文件 ──压缩──> patch.zip ──替换──> 工具识别 ──安装──> 完成汉化
     ↑                                                ↑
   保持目录结构                                     自动检测
```

---

## 开发步骤

### 1. 准备汉化文件
```
准备目标游戏的汉化文件，保持与原游戏完全相同的目录结构：

game_root/
├── index.html          # 入口文件
├── main.js            # 主程序
├── package.json       # 包配置
├── tyrano/            # Tyrano引擎目录
│   ├── lang.js        # 语言文件（重点汉化）
│   ├── plugins/       # 插件目录
│   └── ...
├── data/              # 游戏数据
│   ├── others/        # 字体、图片等资源
│   └── scenario/      # 剧情脚本
└── ...
```

### 2. 压缩为patch.zip
```bash
# 方法1：使用Python
python -c "import shutil; shutil.make_archive('patch', 'zip', 'game_root')"

# 方法2：使用工具内置功能
# 工具会自动将Patch目录压缩为patch.zip
```

### 3. 替换文件
```
将新生成的 patch.zip 替换到工具目录下，覆盖原有文件：
Tyrano_Toolbox/
├── patch.zip          # ← 替换这个文件
├── main.py
├── config.ini
└── ...
```

### 4. 测试安装
- 运行工具
- 点击"一键安装补丁"
- 验证汉化效果

---

## 高级开发

### 使用开发者工具
如果需要精确控制或自定义修改：

1. **解包asar文件**：
   - 使用"开发者工具" → "Asar解包"
   - 选择游戏的 `app.asar` 文件

2. **应用汉化补丁**：
   - 将汉化文件复制到解包目录
   - 使用"Asar打包"重新打包

3. **移除Fuse保护**：
   - 如遇完整性校验问题，使用"Fuse移除"功能

### 自定义Fuse偏移
不同版本的Electron可能需要调整Fuse偏移值：
- 默认值：4
- 位置："开发者工具" → "配置管理" → "修改Fuse偏移"

### 🔧 配置自定义（多游戏适配）

适配不同游戏时，需要修改 `config.ini` 中的关键配置项：

```ini
[main]
# 游戏可执行文件名（针对Fuse移除功能）
AUTO_TARGET_EXE = YourGame.exe

# Fuse哨兵字符串（游戏Electron版本特定的完整性校验标识）
FUSE_SENTINEL = YourGameFuseSentinel

# Fuse头部长度
FUSE_WIRE_HEADER_LENGTH = 34

# ASAR完整性偏移索引（Electron版本相关）
FUSE_ASAR_INTEGRITY_OFFSET = 4

[files]
# 用于检测Steam更新的文件列表（游戏特定文件路径）
CHECK_FILES_FOR_UPDATE = 
    data/others/your_font.ttf
    tyrano/lang.js

# 用于验证asar完整性的稳定文件列表
STABLE_FILES_FOR_VALIDATION = 
    index.html
    main.js
    package.json
```

**修改步骤**：
1. 复制 `config.ini` 到用户目录 `~/.tyranopatcher/config.ini`
2. 根据目标游戏调整上述配置项
3. 使用工具的"配置管理" → "验证配置"功能检查配置有效性
4. 替换 `patch.zip` 并运行工具

---

## 最佳实践

### 文件结构
- ✅ **保持一致**：汉化文件结构必须与原游戏完全一致
- ✅ **完整覆盖**：确保所有需要汉化的文件都被包含
- ✅ **测试验证**：安装后测试游戏是否正常运行

### 性能优化
- ✅ **压缩效率**：使用ZIP压缩减少文件大小
- ✅ **增量更新**：只包含修改的文件，避免全量替换

### 兼容性
- ✅ **跨平台**：确保路径分隔符正确（使用正斜杠 `/`）
- ✅ **编码统一**：使用UTF-8编码保存文本文件

---

## 故障排除

### 常见问题

**Q: 安装后游戏无法启动？**
A: 检查Fuse是否正确移除，或调整Fuse偏移值。

**Q: 汉化文件不生效？**
A: 确认文件路径和结构与原游戏完全一致。

**Q: patch.zip文件过大？**
A: 压缩前清理临时文件，只保留必要的汉化内容。

### 调试技巧
- 查看工具日志：`~/.tyranopatcher/tyrano_patcher.log`
- 使用开发者工具手动验证asar文件完整性
- 在Steam中验证游戏文件完整性后再尝试

---

## 发布插件

### 打包分发
```bash
# 1. 准备插件包
mkdir plugin_release
cp patch.zip plugin_release/
cp README_plugin.md plugin_release/

# 2. 压缩发布
zip -r GameName_Localization_Plugin.zip plugin_release/
```

### 文档要求
插件发布时应包含：
- patch.zip 文件
- 使用说明
- 适配的游戏版本
- 联系方式

---

## 技术规范

### 支持的文件格式
- ✅ HTML, JS, JSON, CSS
- ✅ 图片文件 (PNG, JPG, etc.)
- ✅ 字体文件 (TTF, OTF)
- ✅ 音频文件 (MP3, OGG)

### 限制条件
- ❌ 不支持二进制文件修改
- ❌ 不支持新增文件（只能替换现有文件）
- ❌ 不支持目录结构变更

---

*插件版本：1.0*  
*最后更新：2026-04-12*