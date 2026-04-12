# 文档索引

> **项目状态：RC (Release Candidate)**

> **文档系统**：默认`README.md`为中文，提供醒目的三语切换链接至纯英文(`README_en.md`)和纯日文(`README_ja.md`)独立文档。各语言文件不混用其他语言。标题统一为Tyrano补丁工具箱，でびるコネクション为自带示例。

本文档汇总了项目中的所有说明文档，帮助您快速找到需要的信息。

---

## 快速导航

### 新用户必读

| 文档 | 说明 | 阅读顺序 |
|------|------|----------|
| [README.md](README.md) | 项目介绍、安装指南、使用说明 | ⭐ 第1步 |
| [UTILS_GUIDE.md](UTILS_GUIDE.md) | 工具模块使用指南 | 第2步 |

### 开发者文档

| 文档 | 说明 | 目标读者 |
|------|------|----------|
| [PROJECT_SPECS.md](PROJECT_SPECS.md) | 项目架构和技术规范 | 开发者 |
| [API_DOCS.md](API_DOCS.md) | API 参考文档 | 开发者 |
| [UTILS_GUIDE.md](UTILS_GUIDE.md) | 工具模块详细说明 | 开发者 |

### 打包与分发

| 文档 | 说明 | 目标读者 |
|------|------|----------|
| [PACK.md](PACK.md) | 打包和分发指南 | 发布者 |
| [tools/ASAR_CLI.md](tools/ASAR_CLI.md) | ASAR CLI 工具说明 | 开发者 |

---

## 文档详细说明

### README.md

**内容**：
- 项目简介
- 安装指南（Windows/macOS/Linux）
- 功能特性介绍
- 使用说明
- 项目架构
- 配置文件详解
- 构建流程
- 版权和许可证

**适用场景**：
- 首次使用本项目
- 了解项目功能
- 安装和配置

---

### UTILS_GUIDE.md

**内容**：
- 路径处理 (`utils/paths`)
- 异步操作 (`utils/async_ops`)
- 错误处理 (`utils/error_handler`)
- 性能监控 (`utils/performance`)
- 文件操作 (`utils/file_ops`)
- 清理工具 (`utils/cleanup`)
- 多语言支持 (`utils/language`)
- 日志系统 (`utils/logging`)
- 常量定义 (`utils/constants`)
- 输入验证 (`utils/validators`)
- ASAR 工具 (`utils/asar_utils`)
- 配置管理 (`core/config`)

**适用场景**：
- 了解各个工具模块的功能
- 学习如何使用特定工具
- 开发新功能时查阅 API

---

### PROJECT_SPECS.md

**内容**：
- 架构设计
- 模块职责
- 数据流
- 接口定义
- 技术选型说明

**适用场景**：
- 深入了解项目架构
- 进行架构评审
- 规划新功能

---

### API_DOCS.md

**内容**：
- 完整的 API 参考
- 函数签名
- 参数说明
- 返回值说明
- 使用示例

**适用场景**：
- 查找特定函数的用法
- 了解模块接口
- IDE 集成文档提示

---

### PACK.md

**内容**：
- 打包前准备
- Windows 打包指南
- 跨平台打包指南
- 自动构建配置
- 分发注意事项
- 版本管理
- 常见问题

**适用场景**：
- 构建发布版本
- 配置 CI/CD
- 解决打包问题

---

## 按主题查找

### 线程安全

相关文档：
- [UTILS_GUIDE.md](UTILS_GUIDE.md) - 多语言、配置管理模块的线程安全特性

### 性能优化

相关文档：
- [UTILS_GUIDE.md](UTILS_GUIDE.md) - 性能监控模块

### 文件操作

相关文档：
- [UTILS_GUIDE.md](UTILS_GUIDE.md) - 文件操作、清理工具模块
- [README.md](README.md) - ASAR 操作流程

### 配置管理

相关文档：
- [README.md](README.md) - 配置文件详解
- [UTILS_GUIDE.md](UTILS_GUIDE.md) - 配置管理工具

### 打包发布

相关文档：
- [PACK.md](PACK.md) - 完整打包指南
- [README.md](README.md) - 快速构建说明

---

## 更新记录

| 日期 | 更新内容 |
|------|----------|
| 2026-04-12 | 修复asar依赖处理，添加延迟导入和可用性检查 |
| 2026-04-12 | 添加插件机制说明：通过patch.zip文件替换实现多游戏支持 |
| 2026-04-12 | 创建PLUGIN_GUIDE.md插件开发指南 |
| 2026-04-12 | 更新文档结构，完善README和PROJECT_SPECS.md |
| 2026-04-12 | 技术债清理：移除死代码(TempDirectoryManager/validate_asar_source)、简化锁机制、优化ASAR校验为纯Python实现 |
| 2026-04-09 | 更新文档索引，移除已弃用的改进文档 |
| 2026-04-09 | 添加 RC 阶段状态说明 |
| 2026-04-09 | 补充 `asar_utils` 模块说明 |
| 2026-04-09 | 创建文档索引 |
| 2026-04-09 | 添加 PACK.md 打包指南 |
| 2026-04-09 | 更新 UTILS_GUIDE.md，添加 constants 和 validators 模块 |
| 2026-04-09 | 更新 API_DOCS.md，添加新模块 API 文档 |
| 2026-04-09 | 更新 README.md，添加新模块到目录结构 |

---

## 贡献文档

如果您发现文档有误或需要改进，欢迎提交 PR：

1. Fork 项目
2. 修改文档
3. 提交 PR
4. 等待审核

---

*文档版本：2.1*  
*最后更新：2026-04-12*
