# Tyrano补丁工具箱：技术参考

本文档描述当前实现的运行接口、持久化文件和安全契约。它面向适配其他
Tyrano/Electron 游戏、嵌入核心模块或排查失败的开发者。项目首先是桌面
应用而非稳定的通用 Python SDK；未在本文列出的内部函数可以调整。

## 命令行接口

    python main.py
    python main.py --batch --auto
    python main.py --batch --fuse PATH_TO_EXECUTABLE

无参数启动 GUI。批处理模式必须至少提供 --auto 或 --fuse；在非批处理模式
传入这两个参数会失败。--auto 自动定位游戏并执行补丁流程。--fuse 修改指定
可执行文件中的 Fuse；若同时提供 --auto 与 --fuse，Fuse 分支优先且流程结束
后不会继续自动补丁。--verbose 和 --quiet 互斥。--log-file PATH 改变日志文件
位置。退出码 0 表示成功；参数、引导、验证或业务操作失败返回 1。

批处理模式会跳过启动时的完整状态检查，但补丁控制器仍会在写入前运行前置检查和
状态验证，因此它不是绕过安全检查的开关。

## 配置和运行时路径

首次运行时，内置 config.ini 会复制到用户目录：

    ~/.tyranopatcher/config.ini

所有后续 GUI 设置与动态配置均写入该副本。关键配置项位于 main 和 files 节：
TARGET_ASAR_NAME、PATCH_ZIP_NAME、TEMP_PATCH_DIR、WINDOWS_EXE、MACOS_APP、
LINUX_BINARY、FUSE_SENTINEL、FUSE_WIRE_HEADER_LENGTH、
FUSE_ASAR_INTEGRITY_OFFSET、CHECK_FILES_FOR_UPDATE 和
STABLE_FILES_FOR_VALIDATION。

AppConfig 是线程安全单例。get、get_int、get_bool 与 get_list 读取配置；
set_main_config、set_gui_config 与 set_gui_config_batch 会保存配置。保存通过同
目录临时文件加替换完成。对 config 属性做直接修改时必须调用 invalidate_cache。

## 补丁事务与恢复

PatchController.run_auto_patch(gui_app=None, patch_zip_path=None, _check_cancelled=None) 返回：

    success, temporary_directory_or_none, message

GUI 可通过 `patch_zip_path` 为本次安装传入自定义 ZIP。该参数只替换本次运行使用的
补丁源，不会覆盖程序目录中的内置 `Patch.zip`；未传入时仍使用内置 ZIP 或 `Patch/`
目录。

它先取得进程内 PATCH 锁和 app.asar 同目录的跨进程锁文件，然后执行：

1. 预检 Patch.zip 的真实负载根目录：优先匹配配置中的关键文件，再识别任意深度下
   直接包含 `data`、`tyrano` 等 ASAR 根目录的层级；歧义布局会在解包 ASAR 前终止。
2. 验证 ASAR、备份、Steam 状态和磁盘空间。
3. 解包到游戏目录内的 TEMP_PATCH_DIR，并在安全提取 Patch.zip 时自动剥离压缩工具
   添加的任意层包装目录，或复制 Patch 目录。
4. 写入 app.asar.new 及其 .unpacked sidecar。
5. 对 staged ASAR 执行结构校验，并确认已声明的 unpacked 文件存在。
6. 写入 .patch_transaction.json，按同目录重命名将原文件变为 .bak，再将 staged
   文件变为正式 ASAR。
7. 再次校验正式 ASAR，写入补丁元数据并删除事务标记。

取消检查只在准备、解包、补丁覆盖、完整性哈希和打包阶段协作式生效。提交阶段的
重命名刻意不可取消：在此阶段终止进程或断电可能留下事务标记。下次
bootstrap_system 启动时会调用 recover_incomplete_patch，并先取得目标 ASAR 的
跨进程锁；其他补丁进程仍在运行时只延后恢复，不触碰其 staged 文件。`packing`
阶段只清理未完成的 `.new`，保留未改动的正式 ASAR；`committing` 阶段则优先从
`.bak` 恢复。若备份不存在或恢复失败，应停止操作并用 Steam 验证文件完整性，
再重新执行补丁。

app.asar.unpacked 与 .bak.unpacked 视为同一事务的一部分，会随 ASAR 一起移动或
恢复。提交新的 ASAR 时，旧旁挂目录会被完整替换或删除，避免残留已移除的原生
文件。不要手工只删除其中一个。

## 存档操作契约

SaveService.backup_save(save_dir, backup_dir, use_zip, ...) 返回创建的备份路径。
ZIP 先写入临时文件再替换；目录备份先复制到临时目录再同卷重命名。备份目录不能
位于存档目录内。

SaveService.restore_save(save_dir, backup_src, ...) 的返回值是三态：

- None：成功，目标存档已替换。
- 字符串：操作失败但已成功回滚，字符串是应展示给用户的警告。
- 抛出 PatcherError：操作失败且回滚失败，当前存档可能需要人工恢复。

还原先在存档父目录创建临时目录，准备 ZIP 或目录备份，再使用同卷目录重命名
切换新旧存档。恢复标记文件为 存档目录名.restore-journal；下次还原前会尝试
恢复尚未完成的切换。提交完成后旧目录才会清理。调用方不得把普通非空字符串
返回值当作成功。

## 状态、锁和并发

StateValidator.validate_all 返回 SystemState 与问题列表。can_apply_patch 和
can_restore_backup 返回布尔值及原因文本，适合 GUI 前置判断。

OperationLock 仅协调单一进程中的冲突操作。PatchController 额外使用
FileOperationLock，在目标 ASAR 旁创建 .tyranopatcher.lock 并使用操作系统咨询
锁，因此不同便携版进程也能互斥。锁在进程异常退出后由操作系统释放，但锁文件
本身可以保留，属于正常现象。

## ASAR 接口与边界

utils.asar_utils 支持现代 Pickle、legacy_8 与 legacy_16 头部，提供
parse_asar_header、validate_asar_with_reason、validate_asar_comprehensive、
get_file_hash_in_asar 和 get_file_hashes_in_asar。结构校验检查头、路径与文件
范围；哈希接口读取实际 payload，而不信任 header 声明的完整性字段。

utils.asar_writer.asar_extract 与 asar_pack 是本项目内部集成接口，支持 callback
和 check_cancelled 回调以及 .unpacked 文件集合。它们的签名和业务约束服务于
补丁流程，不是通用归档库 API。需要在其他项目复用 ASAR 能力时，使用独立的
pyasar 项目，不要依赖此处的 utils 模块。

## Fuse 操作

remove_fuse(exe_path) 与 restore_fuse(exe_path) 会在可执行文件旁维护
.fuse_backup。Fuse 定位由哨兵、线缆头长度与 ASAR 完整性位偏移决定，均可在
配置中调整。该操作直接修改游戏可执行文件；失败时优先使用备份回滚。新游戏或
新 Electron 版本必须先在副本上验证配置值。

## 文档与测试的权威关系

API_DOCS.md 是历史自动生成的签名索引，可能遗漏新接口和事务语义。本文档、
源码中的类型签名和 tests 是当前行为的依据；三者冲突时以测试和源码为准。使用
pytest 运行回归测试；Windows 专属测试会在非 Windows 环境跳过。
