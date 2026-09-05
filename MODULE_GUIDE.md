# 模块补充文档

> 为此前仅在代码或 API 索引中出现、但缺少独立说明的模块提供快速参考。

<div align="center">

**🌐 语言 / Language / 言語**

**[中文 🇨🇳 (当前)](MODULE_GUIDE.md)** • **[English 🇬🇧](MODULE_GUIDE_en.md)** • **[日本語 🇯🇵](MODULE_GUIDE_ja.md)**

</div>

---

## 适用范围

本文件补充以下三类内容：

- `API_DOCS.md` 中尚未成体系说明的模块职责
- `README*` 中只被简短提及的运行/构建/界面模块
- 文档读者在适配其他 Tyrano/Electron 游戏时最容易遗漏的接口边界

当前接口和恢复边界见 [技术参考](TECHNICAL_REFERENCE.md) 与源码；`API_DOCS.md` 仅保留历史索引。

---

## 入口与构建

| 模块 | 职责 | 关键入口 |
|------|------|----------|
| `main.py` | 程序总入口，解析 CLI 参数，初始化语言与 bootstrap，选择 GUI 或批处理模式 | `parse_arguments()`、`main()` |
| `build_modern.py` | 现代 Python 构建脚本，面向 wheel/sdist 发布流程 | `install_build()`、`build_wheel()`、`build_sdist()`、`main()` |
| `scripts/check_code.py` | 本地代码质量检查脚本，封装常用检查命令 | `run_command()`、`main()` |

---

## Core 模块

| 模块 | 作用 | 说明 |
|------|------|------|
| `core.bootstrap` | 启动检查与中断恢复 | GUI 使用 `allow_recovery=True`，文件异常时仍可打开窗口并查看恢复指引。 |
| `core.batch` | 无 GUI 批处理安装流程 | `batch_mode()` 面向自动化/命令行执行，`_validate_fuse_path()` 用于危险路径前置校验。 |
| `core.fuse` | Electron Fuse 备份、验证、恢复与移除 | 提供 `remove_fuse()`、`restore_fuse()`、`verify_fuse_backup()`；备份可用性主要靠哨兵/字节检查，创建与恢复时再做完整哈希验证。 |
| `core.patch_info` | 补丁元数据写入与查询 | `get_patch_hash()` 计算补丁源指纹，`load_patch_hash()` 读取 `.patch_meta.patch_hash`；保存函数使用原子写入。 |
| `core.state_validator` | 系统状态一致性检查 | `StateValidator` 和 `validate_system_state()` 负责汇总 ASAR、备份、补丁元数据与补丁信息状态。 |
| `core.steam` | Steam 更新检测与补丁状态机 | `handle_steam_update()` 处理备份缺失、ASAR 覆盖、异常篡改等分支；内部含归档完整性校验。 |

---

## GUI 子模块

| 模块 | 作用 | 说明 |
|------|------|------|
| `gui.tabs.patch_tab` | 补丁安装标签页 | 两种版本均显示此页；内置版默认启用，工具箱需在开发者工具中开启后才能进入此页，安装时需自选 ZIP；主界面只提供操作指引，风险说明放在确认框中。 |
| `gui.tabs.save_tab` | 存档管理标签页 | 对接 `SaveManagerController`，执行扫描、备份、还原、删除与迁移；存档目录缺失时仍可扫描独立备份并选择恢复目标。 |
| `gui.tabs.tools_tab` | 开发者工具标签页 | 聚合 ASAR 打包/解包、Fuse 修改、配置验证与日志入口。 |

---

## Utils 补充模块

| 模块 | 作用 | 说明 |
|------|------|------|
| `utils.asar_writer` | 纯 Python ASAR 归档读写 | `asar_pack()` / `asar_extract()` 用于替代外部 Node.js 依赖。 |
| `utils.config_bridge` | 配置与语言模块之间的桥接层 | 提供回调注册接口以支持解耦；当前主流程里语言持久化仍直接通过 `core.config` 完成。 |
| `utils.disk_utils` | 磁盘空间与写权限检查 | 供 bootstrap 和补丁流程做容量评估；并非所有文件操作都会自动调用。 |
| `utils.operation_lock` | 操作级互斥锁 | 为补丁、存档、工具箱操作提供冲突检测，避免并发写入。 |
| `utils.platform` | 跨平台游戏与 Steam 定位 | 提供平台信息、Steam 库扫描、AppID 查找、资源路径推导。 |
| `utils.transaction` | 事务性文件操作 | 提供 `FileTransaction` 等通用辅助接口；补丁控制器使用自己的事务标记与恢复流程。 |

---

## 多语言文档与代码约定

### 文档语言

- 用户入口文档使用三语独立文件：`README.md` / `README_en.md` / `README_ja.md`
- 文档导航使用三语独立文件：`DOCS_INDEX.md` / `DOCS_INDEX_en.md` / `DOCS_INDEX_ja.md`
- 本模块补充文档同样提供三语版本

### 代码中的多语言支持

- 界面文案和用户可见的操作进度、磁盘检查报告统一走 `utils.language.T(key)`；内部诊断日志使用英文
- 新增文案时同步补齐 `cn` / `en` / `jp`，保持格式参数一致；确认框按“问题、影响、建议”排列
- 当前语言偏好由 `utils.language` 直接写入 `core.config`；`utils.config_bridge` 更适合作为后续解耦接口，而不是现有唯一写入路径

---

## 推荐阅读顺序

1. `README*`
2. `DOCS_INDEX*`
3. `PROJECT_SPECS.md`
4. `MODULE_GUIDE*`
5. `UTILS_GUIDE.md`
6. `TECHNICAL_REFERENCE.md`
