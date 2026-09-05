import logging
import os
import sys
import threading
from typing import Dict, Iterable, Optional, Tuple, Union

from utils.paths import get_user_config_path

logger = logging.getLogger(__name__)

_lang_lock = threading.Lock()
# 保留 _version_lock 别名以向下兼容（指向同一对象）
_version_lock = _lang_lock

# 使用线程本地存储优化频繁读取的语言代码
_thread_local = threading.local()

# 语言版本号，用于检测语言变化并刷新缓存
_lang_version: int = 0

# ================= 跨平台适配 / Cross-Platform =================
IS_WIN: bool = sys.platform.startswith("win")

# ================= 多语言字典 =================
LANG_DICT: Dict[str, Dict[str, str]] = {
    "cn": {
        "chk_enable_patch": "启用补丁安装（工具箱需自选 ZIP）",
        "lbl_bundled_patch": "内置补丁",
        "lbl_patch_disabled": "请在“开发者工具”的配置管理中勾选“启用补丁安装”，再返回此页操作。",
        "lbl_custom_patch_info": "请选择补丁 ZIP，然后点击安装。\n如需更换补丁，请先通过 Steam 验证游戏文件完整性，或还原原版游戏文件。",
        "warn_select_patch_zip": "请先选择要安装的补丁 ZIP。",
        "msg_both_corrupted": "游戏文件与本地备份均未通过校验。请先通过 Steam 验证游戏文件完整性，再安装补丁。",
        "msg_asar_corrupted_valid_backup": "是否从本地备份恢复游戏文件并继续安装补丁？\n\n当前 ASAR 未通过校验，备份通过了文件检查，但可能早于当前游戏版本。覆盖不兼容的文件可能导致内容混杂。\n\n建议选择“否”，优先通过 Steam 验证游戏文件完整性。",
        "progress_starting": "正在开始…",
        "progress_running": "正在处理…",
        "progress_completed": "操作完成。",
        "progress_cancelled": "操作已取消。",
        "progress_failed": "操作失败：{error}",
        "err_disk_space_required": "磁盘空间不足：预计需要 {required}，含预留空间 {reserved}，可用 {available}。",
        "err_disk_space_check": "无法检查磁盘空间：{error}",
        "log_disk_space_header": "磁盘空间检查：",
        "log_disk_required": "预计需要：{size}",
        "log_disk_reserved": "含预留空间：{size}",
        "log_disk_available": "当前可用：{size}",
        "log_disk_breakdown": "估算明细：",
        "log_disk_sufficient": "空间充足。",
        "log_disk_shortfall": "空间不足，还需释放 {size}。",
        "disk_operation_backup": "ASAR 备份",
        "disk_operation_extract": "ASAR 解包",
        "disk_operation_pack": "ASAR 重新打包",
        "disk_operation_temp": "临时文件",
        "warn_disk_check_unavailable": "未能检查磁盘空间，将继续操作。",
        "log_checking_game_state": "正在检查游戏文件状态…",
        "log_checking_disk_space": "正在检查磁盘空间…",
        "err_patch_data_missing": "未找到补丁数据。请选择补丁 ZIP，或使用包含内置补丁的版本。",
        "msg_game_recovery_needed": "游戏文件缺失、不完整或状态异常。建议先在 Steam 库中右键游戏 → 属性 → 已安装文件 → 验证游戏文件的完整性，完成后再安装补丁。\n\n也可以在本工具中选择从校验通过的本地原版备份还原；该备份可能早于当前游戏版本。Steam 验证游戏文件不能代替存档备份。",
        "msg_patch_change_requires_restore": "所选补丁与已安装补丁不同，或无法识别已安装的补丁版本。\n\n补丁的工作方式是用新 Patch 覆盖原始 ASAR 中的对应文件，再重新打包。若补丁与游戏版本不匹配，或原始文件中已有其他修改，可能导致新旧文件混杂、内容错乱或游戏无法正常运行。\n\n请优先在 Steam 中验证游戏文件完整性，再安装所选补丁；也可在图形界面中确认使用本地原版备份重新安装。",
        "msg_patch_replace_confirm": "是否使用本地原版备份安装所选补丁？\n\n所选补丁与已安装补丁不同，或无法识别已安装的补丁版本。程序会解包原版备份，用新 Patch 覆盖其中的对应文件，再重新打包。\n\n若补丁与游戏版本不匹配，或备份中已有其他修改，可能导致新旧文件混杂、内容错乱或游戏无法正常运行。备份通过文件检查不代表与补丁兼容；存档不受影响。\n\n建议选择“否”，先通过 Steam 验证游戏文件完整性，再安装适用于当前游戏版本的补丁。",
        "err_patch_source_changed": "安装期间补丁源发生变化，已停止安装。请重新选择补丁后重试。",
        "msg_restore_patch_confirm": "是否使用安装补丁时创建的本地原版备份还原游戏文件？\n\n还原前会校验备份，但该备份可能早于当前游戏版本。请先关闭游戏；存档不会受到影响。\n\n建议选择“否”，优先通过 Steam 验证游戏文件完整性，恢复官方游戏数据。",
        "title_select_save_target": "选择要恢复的存档文件夹（例如 _storage，可新建）",
        "err_save_target_game_root": "请选择实际的存档文件夹（例如游戏目录下的 _storage），不能选择游戏安装目录或它的上级目录。",
        "menu_lang": "语言 (Language)",
        "menu_about": "关于 (About)",
        "menu_about_app": "关于本程序",
        "app_title": "Tyrano 游戏工具箱 (跨平台版)",
        "tab_main": "安装补丁",
        "tab_tools": "开发者工具",
        "tab_save": "存档管理",
        # Save Manager
        "lbl_cur_save": "当前存档位置:",
        "btn_scan": "🔍 重新扫描",
        "lbl_backup_dir": "备份存储位置:",
        "btn_change_dir": "更改目录",
        "title_select_dir": "选择备份存放目录",
        "btn_backup_now": "➕ 新建备份",
        "btn_restore": "↩ 还原选中",
        "btn_delete": "🗑 删除选中",
        "chk_zip": "📦 直接保存为 ZIP (推荐)",
        "col_name": "备份名称 (时间戳)",
        "col_type": "备份类型",
        "title_select_directory": "选择文件夹",
        "title_select_file": "选择文件",
        "file_type_all": "所有文件",
        "file_type_exe": "执行文件",
        "file_type_asar": "Asar文件",
        "msg_restore_confirm": "确定要还原吗？\n当前进度的存档将被覆盖！",
        "msg_delete_confirm": "确定要永久删除该备份吗？",
        "msg_migrate_confirm": "是否将旧目录中的备份文件迁移到新位置？\n\n程序会安全地进行复制、校验哈希后删除原文件。",
        "msg_migrate_success": "迁移完成。\n成功迁移: {migrated} 个备份",
        "msg_migrate_failed": "\n失败: {failed} 个 (原文件已保留)",
        "msg_migrate_error": "迁移过程中发生错误：{error}",
        "msg_restored": "✅ 存档已还原！请重启游戏。",
        "msg_backup_ok": "✅ 备份已创建。",
        "err_no_save": "未检测到存档 (请先运行一次游戏)",
        # Tools
        "grp_asar": "Asar 解包/打包",
        "lbl_src_asar": "源文件 (app.asar):",
        "lbl_src_folder": "源文件夹:",
        "btn_auto_scan": "自动扫描",
        "btn_browse_file": "选择文件...",
        "btn_browse_dir": "选择文件夹...",
        "btn_extract": "📦 执行解包 (Extract)",
        "btn_sync_path": "⬇ 填入解包路径",
        "btn_pack": "📁 执行打包 (Pack)",
        "grp_fix": "开发者工具 (Fuse)",
        "lbl_game_exe": "游戏主程序 (.exe):",
        "btn_fuse": "🔒 移除Fuse (开发者)",
        "btn_fuse_setting": "修改Fuse偏移",
        "btn_locate": "🔍 自动定位",
        "lbl_platform": "目标平台:",
        "rad_win": "Windows",
        "rad_mac_linux": "Mac/Linux",
        "grp_config": "配置管理",
        "chk_show_console": "显示调试控制台 (需重启生效)",
        "btn_validate_config": "✔ 验证配置",
        "btn_reset_config": "🔄 还原配置",
        "msg_config_valid": "配置检查通过，未发现警告。",
        "msg_config_warnings": "配置有效，但存在以下警告：\n\n{warnings}",
        "msg_config_invalid": "配置存在以下错误/警告：\n\n{errors}",
        "msg_reset_confirm": "确定要将 config.ini 重置为默认配置吗？\n\n注意：这将覆盖所有自定义的 Fuse 偏移等设置，且操作不可逆。",
        "msg_reset_success": "已成功重置为默认配置。",
        "msg_reset_not_found": "找不到默认的 config.ini 模板文件。",
        "msg_reset_error": "重置配置失败: {error}",
        "title_fuse_setting": "修改 Fuse 偏移值",
        "msg_fuse_setting": "请输入目标游戏的 ASAR 完整性验证 Fuse 偏移值。\n\n初始值为当前设置。请根据目标游戏的 Electron 布局确认偏移，并先在副本上测试；不能仅凭引擎名称判断。保存后写入用户 config.ini。",
        "msg_fuse_saved": "Fuse 偏移值已成功保存为: {offset}",
        "err_fuse_save": "保存 Fuse 偏移设置失败:",
        "msg_fuse_warn": "是否使用当前偏移 {offset} 禁用 ASAR 完整性验证 Fuse？\n\n此操作会直接修改游戏主程序，并创建或检查 .fuse_backup。偏移必须与目标游戏的 Electron 布局匹配，错误配置可能导致游戏无法运行。\n\n请先关闭游戏，并在副本上验证设置。游戏数据出现异常时，优先通过 Steam 验证游戏文件完整性。",
        "msg_fuse_disabled_or_not_found": "未找到 Fuse 标记或已被禁用。",
        "err_fuse_backup_not_found": "Fuse 备份未找到，无法恢复",
        "err_fuse_backup_verify": "备份验证失败: {reason}",
        "err_fuse_restore_verify": "恢复验证失败！",
        "msg_fuse_restored": "Fuse 恢复成功。",
        "err_fuse_error": "Fuse 错误: {error}",
        "err_fuse_rollback_failed": "回滚失败！可执行文件可能已损坏。",
        "err_fuse_io_error": "IO 错误: {error}",
        "msg_fuse_backup_created": "备份已创建: {name}",
        "msg_fuse_removed": "Fuse 已移除并验证。",
        "msg_fuse_already_disabled": "Fuse 已经处于禁用状态。",
        # Auto Patcher
        "lbl_patch_info": "选择内置或自定义补丁，然后点击安装。\n如需更换补丁，请先通过 Steam 验证游戏文件完整性，或还原原版游戏文件。",
        "grp_patch_package": "本次使用的补丁包",
        "btn_select_patch": "选择 ZIP...",
        "btn_use_default_patch": "使用内置补丁",
        "title_select_patch": "选择自定义补丁包",
        "file_type_zip": "ZIP 补丁包",
        "btn_start_patch": "🚀 开始安装 (Start Patch)",
        "btn_restore_patch": "↩ 还原原版游戏文件",
        "btn_to_tools": "🛠 高级工具箱",
        "msg_patch_restore_success": "原版游戏文件已从本地备份还原。\n\n存档未被修改。",
        "err_patch_backup_not_found": "未找到安装补丁时创建的原始 app.asar 备份。\n\n无法安全自动还原，请在 Steam 中验证游戏文件完整性。",
        "err_patch_backup_invalid": "原始 app.asar 备份校验失败，已停止还原：{reason}\n\n当前游戏文件未被修改；请在 Steam 中验证游戏文件完整性。",
        "err_patch_restore_failed": "还原原版游戏文件失败：{error}\n\n请关闭游戏后重试；若仍然失败，请在 Steam 中验证游戏文件完整性。",
        "err_patch_directory_busy": "该游戏目录正在被另一个补丁进程操作。",
        "log_patch_restoring_original": "正在还原原版游戏文件...",
        "log_patch_restore_complete": "原版游戏文件还原完成。",
        "log_custom_patch_selected": "本次安装使用自定义补丁包：{path}",
        "err_custom_patch_missing": "选择的自定义补丁包不存在：{path}",
        "patch_done": "✅ 安装完成！",
        "patch_done_done": "补丁安装完成。",
        "msg_exit_after_patch": "是否现在退出工具？\n\n补丁已安装完成。",
        "err_res_missing": "❌ 错误: 缺少 resources 文件夹。",
        "err_asar_missing": "❌ 错误: 未找到 app.asar 文件。",
        "err_asar_corrupted_no_backup": "❌ 错误: app.asar 文件已损坏且无备份，请在 Steam 中验证游戏文件完整性。",
        "err_node_missing": "Error: Node.js 未找到，请安装 Node.js。",
        # Common
        "log_frame": "运行日志 (Log)",
        "title_warning": "警告",
        "title_error": "错误",
        "title_success": "完成",
        "title_confirm": "确认",
        "title_asar_path_error": "ASAR 路径错误",
        "title_disk_space_error": "磁盘空间错误",
        "msg_insufficient_disk_space": "磁盘空间不足，请释放一些空间后重试。",
        "lbl_reason": "原因",
        "warn_no_file": "请先选择文件/文件夹。",
        "warn_not_dir": "请选择文件夹。",
        "warn_not_file": "请选择文件。",
        "warn_empty_dir": "❌ 错误: 目标文件夹是空的！无法打包。",
        "warn_no_extracted": "暂无解包记录。请先执行一次解包。",
        "warn_asar_unpacked": "请不要直接打包 'app.asar.unpacked'，请选择源码目录。",
        "warn_exe_not_found": "未找到目标程序：{exe_name}\n请尝试手动选择。",
        "op_success": "操作成功！",
        "confirm_overwrite": "目标已存在，是否覆盖？",
        "no_backup_selected": "未选择备份。",
        "err_asar_cmd_missing": "Error: 'asar' 命令不可用。",
        "err_cannot_access": "❌ 无法访问该目录。",
        "warn_missing_files": "是否继续打包此文件夹？\n\n源目录缺少 package.json、index.html 等预期文件，可能不是完整的 ASAR 源目录。\n\n请确认选择的是解包后的根目录。",
        "warn_operation_in_progress": "有操作正在进行中，请稍候...",
        "err_save_dir_not_exist": "存档目录不存在。",
        "err_backup_not_exist": "备份文件/目录不存在。",
        "err_path_not_exist": "路径不存在。",
        "err_delete_failed": "❌ 删除失败，请查看日志。",
        "err_permission_denied": "❌ 权限被拒绝，无法访问。",
        # System Errors
        "err_verbose_quiet_exclusive": "错误: --verbose 和 --quiet 不能同时使用。",
        "err_failed_init_corelogic": "初始化 CoreLogic 失败: {error}",
        "err_fatal_error": "致命错误",
        "err_unexpected_error": "发生意外错误:\n{error}",
        "err_init_failed": "初始化失败: {error}",
        "err_config_load_failed": "配置加载失败: {error}",
        "err_config_save_failed": "配置保存失败: {error}",
        "err_config_validation_failed": "配置验证失败: {errors}",
        "err_operation_conflict": "无法启动操作: 存在冲突的操作正在进行 ({operations})。",
        "err_lock_acquire_failed": "获取锁失败: {error}",
        # Steam Update Detection
        "title_steam_update_detected": "Steam 更新检测",
        "msg_steam_update_restore_confirm": "是否从本地备份恢复游戏文件并继续安装补丁？\n\n当前 app.asar 缺失，但存在校验通过的备份。备份可能早于当前游戏版本，继续覆盖可能导致版本或内容不匹配。\n\n建议选择“否”，先通过 Steam 验证游戏文件完整性，再安装对应版本的补丁。",
        "title_asar_invalid": "ASAR 文件不合法",
        "msg_asar_invalid": "ASAR 文件验证失败。\n请在 Steam 中验证游戏文件完整性。",
        "title_game_files_missing": "游戏文件缺失",
        "msg_game_files_missing": "app.asar 和备份文件都不存在。\n这可能表明：\n1. 游戏安装损坏\n2. 游戏下载不完整\n3. 文件被手动删除\n\n请通过 Steam 验证游戏完整性或重新安装游戏。",
        "title_asar_missing": "ASAR 文件缺失",
        "msg_asar_missing_valid_backup": "是否从本地备份恢复游戏文件并继续安装补丁？\n\n当前 app.asar 缺失，但存在校验通过的备份。备份可能早于当前游戏版本，继续覆盖可能导致版本或内容不匹配。\n\n建议选择“否”，先通过 Steam 验证游戏文件完整性，再安装对应版本的补丁。",
        "title_backup_is_patched": "备份包含已打补丁的文件",
        "msg_backup_is_patched": "检测到备份文件包含已打补丁的内容，这意味着 Steam 已删除了您已打补丁的 ASAR 文件。\n\n请通过 Steam 验证游戏文件完整性来恢复原始游戏文件，然后再重新打补丁。",
        "title_backup_corrupted": "备份文件损坏",
        "msg_backup_corrupted": "备份文件存在但似乎已损坏。\n这可能由于：\n1. 不完整的备份过程\n2. 文件系统损坏\n3. 磁盘错误\n\n请通过 Steam 验证游戏完整性或重新安装游戏。",
        "title_backup_corrupted_asar_valid": "备份损坏但 ASAR 有效",
        "msg_backup_corrupted_asar_valid": "是否删除损坏的本地备份，并以当前游戏文件为基础安装补丁？\n\n当前 ASAR 通过了文件检查，但这不能确认它是未修改的原版。继续操作会创建新备份，已有修改可能与补丁混杂。\n\n建议选择“否”，先通过 Steam 验证游戏文件完整性，再安装补丁。",
        "title_no_patch_info": "无补丁信息",
        "msg_no_patch_info": "是否继续安装补丁？\n\n未找到有效的安装记录，无法确认当前文件是否已被修改。继续覆盖可能导致文件混杂。\n\n建议选择“否”，先通过 Steam 验证游戏文件完整性，再安装对应版本的补丁。",
        "title_patch_info_corrupted": "补丁信息损坏",
        "msg_patch_info_corrupted": "是否继续安装补丁？\n\n安装记录为空，无法确认当前补丁状态。继续覆盖可能导致文件混杂。\n\n建议选择“否”，先通过 Steam 验证游戏文件完整性。",
        "title_patch_info_corrupted_json": "补丁信息损坏（JSON 错误）",
        "msg_patch_info_corrupted_json": "是否继续安装补丁？\n\n无法读取安装记录：{error}\n继续覆盖可能导致文件混杂。\n\n建议选择“否”，先通过 Steam 验证游戏文件完整性。",
        "title_old_patch_detected": "检测到旧补丁",
        "msg_old_patch_detected": "是否继续安装补丁？\n\n上次安装是在 {days} 天前，仅凭安装时间无法判断游戏是否更新。请确认补丁适用于当前游戏版本。\n\n不确定时请选择“否”，先通过 Steam 验证游戏文件完整性。",
        "msg_asar_exists_no_backup": "ASAR 文件存在但无备份 - 首次打补丁或使用了其他补丁工具",
        "title_asar_corrupted": "ASAR 文件损坏",
        "msg_asar_corrupted": "app.asar 文件存在但似乎已损坏。\n请通过 Steam 验证游戏完整性或重新安装游戏。",
        "msg_backup_corrupted_asar_valid_rebuild": "是否删除损坏的本地备份，并以当前游戏文件为基础安装补丁？\n\n当前 ASAR 通过了文件检查，但这不能确认它是未修改的原版。继续操作会创建新备份，已有修改可能与补丁混杂。\n\n建议选择“否”，先通过 Steam 验证游戏文件完整性，再安装补丁。",
        "msg_already_patched": "游戏已经安装过本补丁，文件状态正常，无需再次安装。",
        "log_patch_extracting_asar": "解压 ASAR...",
        "log_patch_cleaning_temp": "清理临时文件...",
        "log_patch_applying": "应用补丁...",
        "log_patch_extracting_zip": "正在解压所选补丁 ZIP…",
        "log_patch_zip_root_detected": "检测到补丁 ZIP 包装目录，将自动移除层级：{root}",
        "log_patch_zip_root_direct": "补丁 ZIP 已位于正确的 ASAR 根目录层级。",
        "log_patch_zip_extracted": "补丁 ZIP 解压完成。",
        "err_patch_zip_layout": "无法确定补丁 ZIP 的实际根目录：{error}",
        "log_patch_copying_dir": "正在复制补丁目录中的文件…",
        "log_patch_files_copied": "补丁文件复制完成。",
        "log_patch_creating_backup": "创建备份...",
        "log_patch_backup_created": "备份创建完成。",
        "log_patch_packing_asar": "打包 ASAR...",
        "log_patch_asar_replaced": "ASAR 替换成功。",
        "log_patch_generating_meta": "生成补丁元数据...",
        "log_patch_complete": "补丁安装成功。",
        "log_patch_restored_backup": "从备份还原 app.asar。",
        "log_patch_restore_failed": "备份还原失败: {error}",
        "log_patch_corrupted_restoring": "app.asar 已损坏，删除并从备份中恢复...",
        "log_patch_validating_asar": "验证 ASAR 文件...",
        "title_inconsistent_state": "文件状态不一致",
        "msg_inconsistent_state": "是否已通过 Steam 验证游戏文件完整性，并继续安装补丁？\n\n当前 ASAR 与本地备份及补丁记录均不一致。选择“是”将删除旧 ASAR 备份，并以当前游戏文件为基础安装补丁。\n\n如果尚未验证，请选择“否”，先通过 Steam 恢复游戏文件，避免混用不同版本或已修改的文件。",
        "title_first_time_patch": "首次安装补丁提醒",
        "msg_first_time_patch_warn": "是否确认当前文件是原版，并继续安装补丁？\n\n未找到原版备份。程序会将当前 ASAR 作为备份，再用补丁覆盖对应文件；如果当前文件已有其他修改，可能导致文件混杂。\n\n不确定时请选择“否”，先通过 Steam 验证游戏文件完整性，再安装对应版本的补丁。",
        # About Dialog
        "about_desc": "《でびるコネクショん》非营利性个人本地化工具。\nTyranoV8通用工具箱\n\n==== 技术致谢 ====\n• 核心语言: Python 3 (Pure)\n• 图形界面: Tkinter (Tcl/Tk)\n• 封包引擎: ASAR (Pure Python)\n• 构建工具: PyInstaller\n\n==== 开发人员 ====\n作者：KouzakiUmi (呜咪 / 神前海)\nGitHub: https://github.com/KouzakiUmi/DeviConHan\n\n==== 许可证 ====\n本项目仅限非营利目的使用。\n游戏内容的所有权利均归原作者 ばやちゃお 所有。\n",
        "about_version": "版本: 1.0 Release",
        "about_github_link": "访问 GitHub 主页",
        "btn_ok": "确定",
    },
    "en": {
        "chk_enable_patch": "Enable patch installation (toolbox requires a custom ZIP)",
        "lbl_bundled_patch": "Bundled patch",
        "lbl_patch_disabled": "Enable patch installation under Developer Tools → Configuration, then return to this page.",
        "lbl_custom_patch_info": "Select a patch ZIP, then install.\nBefore switching patches, verify game files in Steam or restore the original game files.",
        "warn_select_patch_zip": "Select a patch ZIP before installing.",
        "msg_both_corrupted": "Both game files and the local backup failed validation. Verify game files in Steam before installing the patch.",
        "msg_asar_corrupted_valid_backup": "Restore game files from the local backup and install the patch?\n\nThe current ASAR failed validation. The backup passed file checks but may be older than the current game. Overwriting incompatible files may leave mixed content.\n\nRecommended: choose No and verify game files in Steam first.",
        "progress_starting": "Starting...",
        "progress_running": "In progress...",
        "progress_completed": "Completed.",
        "progress_cancelled": "Cancelled.",
        "progress_failed": "Failed: {error}",
        "err_disk_space_required": "Insufficient disk space: estimated {required}, including reserve {reserved}, available {available}.",
        "err_disk_space_check": "Could not check disk space: {error}",
        "log_disk_space_header": "Disk space check:",
        "log_disk_required": "Estimated requirement: {size}",
        "log_disk_reserved": "Required including reserve: {size}",
        "log_disk_available": "Available: {size}",
        "log_disk_breakdown": "Estimate breakdown:",
        "log_disk_sufficient": "Sufficient disk space.",
        "log_disk_shortfall": "Insufficient space; free another {size}.",
        "disk_operation_backup": "ASAR backup",
        "disk_operation_extract": "ASAR extraction",
        "disk_operation_pack": "ASAR repacking",
        "disk_operation_temp": "Temporary files",
        "warn_disk_check_unavailable": "Disk space could not be checked; continuing.",
        "log_checking_game_state": "Checking game file state...",
        "log_checking_disk_space": "Checking disk space...",
        "err_patch_data_missing": "No patch data found. Select a patch ZIP or use a build with a bundled patch.",
        "msg_game_recovery_needed": "Game files are missing, incomplete, or inconsistent. First use Steam Library > game Properties > Installed Files > Verify integrity of game files, then install the patch again.\n\nAlternatively, use this tool to restore a validated local original backup; it may predate the current game version. Steam file verification does not replace save backups.",
        "msg_patch_change_requires_restore": "The selected patch differs from the installed patch, or the installed patch version cannot be identified.\n\nThe tool overwrites corresponding files in the original ASAR with the new Patch, then repacks the archive. If the patch does not match the game version, or the source already contains other modifications, this may mix old and new files, cause inconsistent content, or prevent the game from working.\n\nVerify game files in Steam first, then install the selected patch. Alternatively, confirm using a local original backup in the GUI.",
        "msg_patch_replace_confirm": "Install the selected patch using the local original backup?\n\nThe selected patch differs from the installed patch, or the installed patch version cannot be identified. The tool extracts the original backup, overwrites corresponding files with the new Patch, then repacks it.\n\nIf the patch does not match the game version, or the backup already contains other modifications, this may mix old and new files, cause inconsistent content, or prevent the game from working. Passing file checks does not establish patch compatibility. Saves are unaffected.\n\nRecommended: choose No, verify game files in Steam, then install a patch intended for the current game version.",
        "err_patch_source_changed": "The patch source changed during installation. Installation stopped; select the patch again and retry.",
        "msg_restore_patch_confirm": "Restore game files using the local original backup created during patch installation?\n\nThe backup will be validated before restoration, but it may predate the current game version. Close the game first. Saves are unaffected.\n\nRecommended: choose No and verify game files in Steam to restore official game data.",
        "title_select_save_target": "Select the save folder to restore (e.g. _storage; may be new)",
        "err_save_target_game_root": "Select the actual save folder, such as _storage inside the game folder, not the game installation folder or its parent.",
        "menu_lang": "Language",
        "menu_about": "About",
        "menu_about_app": "About This App",
        "app_title": "Tyrano Toolbox (Cross-Platform)",
        "tab_main": "Install Patch",
        "tab_tools": "Dev Tools",
        "tab_save": "Save Manager",
        # Save Manager
        "lbl_cur_save": "Save Path:",
        "btn_scan": "Rescan",
        "lbl_backup_dir": "Backup Dir:",
        "btn_change_dir": "Change Dir",
        "title_select_dir": "Select Backup Directory",
        "btn_backup_now": "Backup Now",
        "btn_restore": "Restore Selected",
        "btn_delete": "Delete Selected",
        "chk_zip": "Save as ZIP (Direct)",
        "col_name": "Backup Name (Timestamp)",
        "col_type": "Backup Type",
        "title_select_directory": "Select Directory",
        "title_select_file": "Select File",
        "file_type_all": "All Files",
        "file_type_exe": "Executable",
        "file_type_asar": "Asar File",
        "msg_restore_confirm": "Restore this backup?\nCurrent save will be overwritten!",
        "msg_delete_confirm": "Delete this backup permanently?",
        "msg_migrate_confirm": "Migrate existing backups from the old directory to the new one?\n\nThe program will safely copy, verify hashes, and then delete original files.",
        "msg_migrate_success": "Migration complete.\nSuccessfully migrated: {migrated} backups",
        "msg_migrate_failed": "\nFailed: {failed} (originals kept)",
        "msg_migrate_error": "Error during migration: {error}",
        "msg_restored": "✅ Restored! Please restart game.",
        "msg_backup_ok": "✅ Backup created.",
        "err_no_save": "Save folder not found.",
        # Tools
        "grp_asar": "Asar Operations",
        "lbl_src_asar": "Source (app.asar):",
        "lbl_src_folder": "Source Folder:",
        "btn_auto_scan": "Auto Scan",
        "btn_browse_file": "Browse File...",
        "btn_browse_dir": "Browse Dir...",
        "btn_extract": "📦 Extract",
        "btn_sync_path": "⬇ Use Extracted",
        "btn_pack": "📁 Pack",
        "grp_fix": "Dev Tools (Fuse)",
        "lbl_game_exe": "Game EXE:",
        "btn_fuse": "🔒 Remove Fuse (Dev)",
        "btn_fuse_setting": "Fuse Offset",
        "btn_locate": "Auto Locate",
        "lbl_platform": "Target:",
        "rad_win": "Windows",
        "rad_mac_linux": "Mac/Linux",
        "grp_config": "Configuration",
        "chk_show_console": "Show Debug Console (requires restart)",
        "btn_validate_config": "✔ Validate Config",
        "btn_reset_config": "🔄 Reset Config",
        "msg_config_valid": "Configuration checks passed without warnings.",
        "msg_config_warnings": "Configuration is valid, but has warnings:\n\n{warnings}",
        "msg_config_invalid": "Configuration contains errors/warnings:\n\n{errors}",
        "msg_reset_confirm": "Are you sure you want to reset config.ini to defaults?\n\nWarning: This will overwrite custom Fuse offsets and other settings, and cannot be undone.",
        "msg_reset_success": "Successfully reset to default configuration.",
        "msg_reset_not_found": "Cannot find the default config.ini template file.",
        "msg_reset_error": "Failed to reset config: {error}",
        "title_fuse_setting": "Modify Fuse Offset",
        "msg_fuse_setting": "Enter the ASAR integrity Fuse offset for the target game.\n\nThe initial value is the current setting. Confirm the offset against the game's Electron layout and test on a copy first; the engine name alone is insufficient. The value is saved to the user config.ini.",
        "msg_fuse_saved": "Fuse offset successfully saved as: {offset}",
        "err_fuse_save": "Failed to save Fuse offset setting:",
        "msg_fuse_warn": "Disable the ASAR integrity Fuse using offset {offset}?\n\nThis edits the game executable and creates or checks .fuse_backup. The offset must match the target game's Electron layout; an incorrect setting may prevent the game from running.\n\nClose the game and validate the setting on a copy first. For damaged game files, use Steam verification as the first recovery step.",
        "msg_fuse_disabled_or_not_found": "Fuse sentinel not found or already disabled.",
        "err_fuse_backup_not_found": "Fuse backup not found, cannot restore",
        "err_fuse_backup_verify": "Backup verification failed: {reason}",
        "err_fuse_restore_verify": "Restore verification failed!",
        "msg_fuse_restored": "Fuse restored successfully.",
        "err_fuse_error": "Fuse Error: {error}",
        "err_fuse_rollback_failed": "Rollback failed! The executable may be corrupted.",
        "err_fuse_io_error": "IO Error: {error}",
        "msg_fuse_backup_created": "Backup created: {name}",
        "msg_fuse_removed": "Fuse removed and verified.",
        "msg_fuse_already_disabled": "Fuse already disabled.",
        # Auto Patcher
        "lbl_patch_info": "Choose the bundled or a custom patch, then click Install.\nTo switch patches, first verify game files in Steam or restore the original game files.",
        "grp_patch_package": "Patch package for this installation",
        "btn_select_patch": "Choose ZIP...",
        "btn_use_default_patch": "Use Bundled Patch",
        "title_select_patch": "Choose a Custom Patch Package",
        "file_type_zip": "ZIP Patch Package",
        "btn_start_patch": "🚀 Start Patch",
        "btn_restore_patch": "↩ Restore Original Game Files",
        "btn_to_tools": "🛠 Advanced Tools",
        "msg_patch_restore_success": "Original game files were restored from the local backup.\n\nSaves were not modified.",
        "err_patch_backup_not_found": "The original app.asar backup created during patch installation was not found.\n\nA safe automatic restore is not possible. Verify the game files in Steam instead.",
        "err_patch_backup_invalid": "The original app.asar backup failed validation, so restoration was stopped: {reason}\n\nThe current game files were not modified. Verify the game files in Steam.",
        "err_patch_restore_failed": "Failed to restore the original game files: {error}\n\nClose the game and try again. If it still fails, verify the game files in Steam.",
        "err_patch_directory_busy": "The game directory is being modified by another patch process.",
        "log_patch_restoring_original": "Restoring the original game files...",
        "log_patch_restore_complete": "Original game files restored.",
        "log_custom_patch_selected": "Using custom patch package for this installation: {path}",
        "err_custom_patch_missing": "The selected custom patch package does not exist: {path}",
        "patch_done": "✅ Install Complete!",
        "patch_done_done": "Patch installation is complete.",
        "msg_exit_after_patch": "Exit the toolbox now?\n\nPatch installation is complete.",
        "err_res_missing": "❌ Error: 'resources' folder missing.",
        "err_asar_missing": "❌ Error: app.asar not found.",
        "err_asar_corrupted_no_backup": "❌ Error: app.asar is corrupted and no backup exists. Please verify game files in Steam.",
        "err_asar_cmd_missing": "Error: 'asar' command not available.",
        "err_node_missing": "Error: Node.js not found! Please install Node.js.",
        "log_frame": "Log",
        "title_warning": "Warning",
        "title_error": "Error",
        "title_success": "Success",
        "title_confirm": "Confirm",
        "title_asar_path_error": "ASAR Path Error",
        "title_disk_space_error": "Disk Space Error",
        "msg_insufficient_disk_space": "Insufficient disk space. Please free up some space and try again.",
        "lbl_reason": "Reason",
        "warn_no_file": "Please select a file/folder.",
        "warn_not_dir": "Please select a directory.",
        "warn_not_file": "Please select a file.",
        "warn_empty_dir": "❌ Error: Source directory is empty!",
        "warn_no_extracted": "No extraction history found.",
        "warn_asar_unpacked": "Cannot pack 'app.asar.unpacked'. Select source dir.",
        "warn_exe_not_found": "Target executable not found: {exe_name}\nPlease select it manually.",
        "op_success": "Operation Success!",
        "confirm_overwrite": "Target exists, overwrite?",
        "no_backup_selected": "No backup selected.",
        "err_cannot_access": "❌ Cannot access directory.",
        "warn_missing_files": "Pack this folder anyway?\n\nExpected files such as package.json or index.html are missing. This may not be a complete ASAR source directory.\n\nCheck that you selected the extracted root folder.",
        "warn_operation_in_progress": "Operation in progress, please wait...",
        "err_save_dir_not_exist": "Save directory does not exist.",
        "err_backup_not_exist": "Backup file/folder does not exist.",
        "err_path_not_exist": "Path does not exist.",
        "err_delete_failed": "❌ Failed to delete. Check logs.",
        "err_permission_denied": "❌ Permission denied.",
        # System Errors
        "err_verbose_quiet_exclusive": "Error: --verbose and --quiet are mutually exclusive.",
        "err_failed_init_corelogic": "Failed to initialize CoreLogic: {error}",
        "err_fatal_error": "Fatal Error",
        "err_unexpected_error": "An unexpected error occurred:\n{error}",
        "err_init_failed": "Initialization failed: {error}",
        "err_config_load_failed": "Failed to load config: {error}",
        "err_config_save_failed": "Failed to save config: {error}",
        "err_config_validation_failed": "Configuration validation failed: {errors}",
        "err_operation_conflict": "Cannot start operation: conflicting operations in progress ({operations}).",
        "err_lock_acquire_failed": "Failed to acquire lock: {error}",
        # Steam Update Detection
        "title_steam_update_detected": "Steam Update Detected",
        "msg_steam_update_restore_confirm": "Restore game files from the local backup and install the patch?\n\nThe current app.asar is missing, but a backup passed validation. It may be older than the current game; patching it may cause version or content mismatches.\n\nRecommended: choose No, verify game files in Steam, then install a matching patch.",
        "title_asar_invalid": "ASAR Invalid",
        "msg_asar_invalid": "ASAR file validation failed.\nPlease verify game integrity through Steam.",
        "title_game_files_missing": "Game Files Missing",
        "msg_game_files_missing": "Neither app.asar nor backup file exists.\nThis could indicate:\n1. Corrupted game installation\n2. Incomplete game download\n3. Files were manually deleted\n\nPlease verify game integrity through Steam or reinstall the game.",
        "title_asar_missing": "ASAR File Missing",
        "msg_asar_missing_valid_backup": "Restore game files from the local backup and install the patch?\n\nThe current app.asar is missing, but a backup passed validation. It may be older than the current game; patching it may cause version or content mismatches.\n\nRecommended: choose No, verify game files in Steam, then install a matching patch.",
        "title_backup_is_patched": "Backup Contains Patched Files",
        "msg_backup_is_patched": "The backup contains patched files, meaning Steam has removed your patched ASAR file.\n\nPlease verify game files integrity through Steam to restore the original game files, then apply the patch again.",
        "title_backup_corrupted": "Backup Corrupted",
        "msg_backup_corrupted": "The backup file exists but appears to be corrupted.\nThis could be due to:\n1. Incomplete backup process\n2. File system corruption\n3. Disk errors\n\nPlease verify game integrity through Steam or reinstall the game.",
        "title_backup_corrupted_asar_valid": "Backup Corrupted but ASAR Valid",
        "msg_backup_corrupted_asar_valid": "Discard the damaged local backup and install using the current game files?\n\nThe current ASAR passed file checks, but this does not establish that it is unmodified. Continuing creates a new backup; existing modifications may mix with the patch.\n\nRecommended: choose No and verify game files in Steam before installing.",
        "title_no_patch_info": "No Patch Info",
        "msg_no_patch_info": "Continue installing the patch?\n\nNo valid installation record was found, so existing modifications cannot be ruled out. Overwriting these files may leave mixed content.\n\nRecommended: choose No, verify game files in Steam, then install a patch for that game version.",
        "title_patch_info_corrupted": "Corrupted Patch Info",
        "msg_patch_info_corrupted": "Continue installing the patch?\n\nThe installation record is empty, so the current patch state cannot be confirmed. Overwriting may leave mixed content.\n\nRecommended: choose No and verify game files in Steam first.",
        "title_patch_info_corrupted_json": "Corrupted Patch Info (JSON Error)",
        "msg_patch_info_corrupted_json": "Continue installing the patch?\n\nCould not read the installation record: {error}\nOverwriting may leave mixed content.\n\nRecommended: choose No and verify game files in Steam first.",
        "title_old_patch_detected": "Old Patch Detected",
        "msg_old_patch_detected": "Continue installing the patch?\n\nThe last installation was {days} days ago. Its age alone cannot determine whether the game has updated. Confirm that the patch matches your game version.\n\nIf unsure, choose No and verify game files in Steam first.",
        "msg_asar_exists_no_backup": "ASAR file exists but no backup - first time patching or used other patch tools",
        "title_asar_corrupted": "ASAR Corrupted",
        "msg_asar_corrupted": "The app.asar file exists but appears to be corrupted.\nPlease verify game integrity through Steam or reinstall the game.",
        "msg_backup_corrupted_asar_valid_rebuild": "Discard the damaged local backup and install using the current game files?\n\nThe current ASAR passed file checks, but this does not establish that it is unmodified. Continuing creates a new backup; existing modifications may mix with the patch.\n\nRecommended: choose No and verify game files in Steam before installing.",
        "msg_already_patched": "The game is already successfully patched. No further action is required.",
        "log_patch_extracting_asar": "Extracting ASAR...",
        "log_patch_cleaning_temp": "Cleaning up temp files...",
        "log_patch_applying": "Applying patch...",
        "log_patch_extracting_zip": "Extracting the selected patch ZIP...",
        "log_patch_zip_root_detected": "Detected a patch ZIP wrapper directory; stripping: {root}",
        "log_patch_zip_root_direct": "The patch ZIP is already rooted at the correct ASAR level.",
        "log_patch_zip_extracted": "Patch ZIP extracted.",
        "err_patch_zip_layout": "Could not determine the patch ZIP root: {error}",
        "log_patch_copying_dir": "Copying files from the patch directory...",
        "log_patch_files_copied": "Patch files copied.",
        "log_patch_creating_backup": "Creating backup...",
        "log_patch_backup_created": "Backup created.",
        "log_patch_packing_asar": "Packing ASAR...",
        "log_patch_asar_replaced": "ASAR replaced successfully.",
        "log_patch_generating_meta": "Generating patch metadata...",
        "log_patch_complete": "Patch applied successfully.",
        "log_patch_restored_backup": "Restored app.asar from backup.",
        "log_patch_restore_failed": "Failed to restore from backup: {error}",
        "log_patch_corrupted_restoring": "app.asar corrupted, removing and restoring from backup...",
        "log_patch_validating_asar": "Validating ASAR file...",
        "title_inconsistent_state": "Inconsistent File State",
        "msg_inconsistent_state": "Have you verified game files in Steam and want to continue installing?\n\nThe current ASAR differs from both the local backup and the patch record. Yes discards the old ASAR backup and installs using the current game files.\n\nIf you have not verified them, choose No and restore game files through Steam first to avoid mixing versions or modified files.",
        "title_first_time_patch": "First Time Patching Notice",
        "msg_first_time_patch_warn": "Are the current files original, and do you want to install the patch?\n\nNo original backup was found. The tool will back up the current ASAR, then overwrite matching files with the patch. Existing modifications may leave mixed content.\n\nIf unsure, choose No, verify game files in Steam, then install a patch for that game version.",
        # About Dialog
        "about_desc": "A non-profit personal localization tool for 《でびるコネクショん》.\nUniversal Toolbox for TyranoV8\n\n==== Technical Credits ====\n• Core Language: Python 3 (Pure)\n• GUI Framework: Tkinter (Tcl/Tk)\n• Packaging Engine: ASAR (Pure Python)\n• Build Tool: PyInstaller\n\n==== Developers ====\nAuthor: KouzakiUmi\nGitHub: https://github.com/KouzakiUmi/DeviConHan\n\n==== License ====\nFor non-profit purposes only.\nAll rights to the game content belong to the original author, Bayachao.\n",
        "about_version": "Version: 1.0 Release",
        "about_github_link": "Visit GitHub Page",
        "btn_ok": "OK",
    },
    "jp": {
        "chk_enable_patch": "パッチ適用を有効化（ツールボックスでは ZIP の選択が必要）",
        "lbl_bundled_patch": "同梱パッチ",
        "lbl_patch_disabled": "開発者ツールの設定管理でパッチ適用を有効にしてから、このページに戻ってください。",
        "lbl_custom_patch_info": "パッチ ZIP を選択して適用してください。\n別のパッチに変更する前に、Steam で整合性を確認するか元のゲームファイルに戻してください。",
        "warn_select_patch_zip": "適用するパッチ ZIP を先に選択してください。",
        "msg_both_corrupted": "ゲームファイルとローカルバックアップの両方が検証に失敗しました。Steam で整合性を確認してからパッチを適用してください。",
        "msg_asar_corrupted_valid_backup": "ローカルバックアップから復元し、パッチを適用しますか？\n\n現在の ASAR は検証に失敗しました。バックアップは検証に合格しましたが、古いバージョンの可能性があります。互換性のないファイルの上書きで内容が混在する場合があります。\n\n「いいえ」を選び、先に Steam で整合性を確認することをお勧めします。",
        "progress_starting": "開始しています…",
        "progress_running": "処理しています…",
        "progress_completed": "完了しました。",
        "progress_cancelled": "キャンセルしました。",
        "progress_failed": "失敗しました：{error}",
        "err_disk_space_required": "ディスク容量が不足しています。推定必要量 {required}、予備を含む必要量 {reserved}、空き容量 {available}。",
        "err_disk_space_check": "ディスク容量を確認できません：{error}",
        "log_disk_space_header": "ディスク容量の確認：",
        "log_disk_required": "推定必要量：{size}",
        "log_disk_reserved": "予備を含む必要量：{size}",
        "log_disk_available": "空き容量：{size}",
        "log_disk_breakdown": "推定内訳：",
        "log_disk_sufficient": "必要な空き容量があります。",
        "log_disk_shortfall": "容量が不足しています。あと {size} の空き容量が必要です。",
        "disk_operation_backup": "ASAR バックアップ",
        "disk_operation_extract": "ASAR 展開",
        "disk_operation_pack": "ASAR 再パック",
        "disk_operation_temp": "一時ファイル",
        "warn_disk_check_unavailable": "ディスク容量を確認できませんでした。処理を続行します。",
        "log_checking_game_state": "ゲームファイルの状態を確認しています…",
        "log_checking_disk_space": "ディスク容量を確認しています…",
        "err_patch_data_missing": "パッチデータが見つかりません。パッチ ZIP を選択するか、パッチ同梱版を使用してください。",
        "msg_game_recovery_needed": "ゲームファイルが存在しない、不完全、または不整合です。まず Steam ライブラリでゲームのプロパティ → インストール済みファイル → ゲームファイルの整合性を確認し、その後パッチを適用してください。\n\n検証済みのローカルバックアップから復元することもできますが、古いバージョンの場合があります。Steam のファイル検証はセーブデータのバックアップの代わりにはなりません。",
        "msg_patch_change_requires_restore": "選択したパッチがインストール済みのものと異なるか、インストール済みのバージョンを識別できません。\n\n新しい Patch で元の ASAR 内の対応するファイルを上書きしてから、再パックします。ゲームのバージョンに対応しないパッチや、すでに変更された元のファイルを使用すると、新旧ファイルの混在、内容の不整合、動作不良が起こる可能性があります。\n\nまず Steam でゲームファイルの整合性を確認してから適用してください。GUI で確認のうえ、ローカルバックアップを使用することもできます。",
        "msg_patch_replace_confirm": "ローカルの元のバックアップを使用して、選択したパッチを適用しますか？\n\n選択したパッチがインストール済みのものと異なるか、インストール済みのバージョンを識別できません。元のバックアップを展開し、新しい Patch で対応するファイルを上書きしてから再パックします。\n\nゲームのバージョンに対応しないパッチや、すでに変更されたバックアップを使用すると、新旧ファイルの混在、内容の不整合、動作不良が起こる可能性があります。ファイル検証の合格はパッチとの互換性を保証しません。セーブデータには影響しません。\n\n「いいえ」を選択し、Steam でゲームファイルの整合性を確認してから、現在のバージョンに対応するパッチを適用することをお勧めします。",
        "err_patch_source_changed": "インストール中にパッチの内容が変更されたため中止しました。パッチを選択し直して再試行してください。",
        "msg_restore_patch_confirm": "パッチ適用時に作成したローカルの元のバックアップから、ゲームファイルを復元しますか？\n\n復元前にバックアップを検証しますが、古いバージョンの場合があります。先にゲームを終了してください。セーブデータには影響しません。\n\n「いいえ」を選択し、Steam でゲームファイルの整合性を確認して公式データに戻すことをお勧めします。",
        "title_select_save_target": "復元先のセーブフォルダーを選択（例：_storage、新規作成可）",
        "err_save_target_game_root": "ゲームのインストールフォルダーやその親ではなく、_storage など実際のセーブフォルダーを選択してください。",
        "menu_lang": "言語 (Language)",
        "menu_about": "ヘルプ (Help)",
        "menu_about_app": "このアプリについて",
        "app_title": "Tyrano ツールボックス (Cross-Platform)",
        "tab_main": "パッチ適用",
        "tab_tools": "開発ツール",
        "tab_save": "セーブ管理",
        # Save Manager
        "lbl_cur_save": "セーブ場所:",
        "btn_scan": "再スキャン",
        "lbl_backup_dir": "保存先:",
        "btn_change_dir": "場所変更",
        "title_select_dir": "バックアップフォルダを選択",
        "btn_backup_now": "バックアップ作成",
        "btn_restore": "復元",
        "btn_delete": "削除",
        "chk_zip": "🗑 直接 ZIP 保存（推奨）",
        "col_name": "バックアップ名 (日時)",
        "col_type": "バックアップ型",
        "title_select_directory": "フォルダを選択",
        "title_select_file": "ファイルを選択",
        "file_type_all": "すべてのファイル",
        "file_type_exe": "実行ファイル",
        "file_type_asar": "Asarファイル",
        "msg_restore_confirm": "復元しますか？\n現在のセーブデータは上書きされます！",
        "msg_delete_confirm": "このバックアップを完全に削除しますか？",
        "msg_migrate_confirm": "旧フォルダから新フォルダへバックアップを移行しますか？\n\nコピーとハッシュ検証を行った後、安全に元のファイルを削除します。",
        "msg_migrate_success": "移行完了。\n成功した数: {migrated} 個",
        "msg_migrate_failed": "\n失敗: {failed} 個 (元のファイルは保持されています)",
        "msg_migrate_error": "移行中にエラーが発生しました: {error}",
        "msg_restored": "✅ 復元しました。再起動してください。",
        "msg_backup_ok": "✅ バックアップ完了。",
        "err_no_save": "セーブフォルダ未検出。",
        # Tools
        "grp_asar": "Asar 解凍/圧縮",
        "lbl_src_asar": "元ファイル (app.asar):",
        "lbl_src_folder": "元フォルダ:",
        "btn_auto_scan": "自動検出",
        "btn_browse_file": "ファイル選択...",
        "btn_browse_dir": "フォルダ選択...",
        "btn_extract": "📦 解凍 (Extract)",
        "btn_sync_path": "⬇ 解凍パスを使用",
        "btn_pack": "📁 圧縮 (Pack)",
        "grp_fix": "開発ツール (Fuse)",
        "lbl_game_exe": "実行ファイル:",
        "btn_fuse": "🔒 Fuse解除 (開発者)",
        "btn_fuse_setting": "Fuseオフセット",
        "btn_locate": "自動検出",
        "lbl_platform": "対象OS:",
        "rad_win": "Windows",
        "rad_mac_linux": "Mac/Linux",
        "grp_config": "設定管理",
        "chk_show_console": "デバッグコンソールを表示 (再起動が必要)",
        "btn_validate_config": "✔ 設定の検証",
        "btn_reset_config": "🔄 初期設定に戻す",
        "msg_config_valid": "設定の検証に合格しました。警告はありません。",
        "msg_config_warnings": "設定は有効ですが、以下の警告があります：\n\n{warnings}",
        "msg_config_invalid": "設定に以下のエラー/警告が含まれています：\n\n{errors}",
        "msg_reset_confirm": "config.ini をデフォルト設定にリセットしてもよろしいですか？\n\n警告：カスタムのFuseオフセットなどは失われ、この操作は元に戻せません。",
        "msg_reset_success": "デフォルト設定にリセットしました。",
        "msg_reset_not_found": "デフォルトの config.ini テンプレートが見つかりません。",
        "msg_reset_error": "リセットに失敗しました: {error}",
        "title_fuse_setting": "Fuse オフセット値の設定",
        "msg_fuse_setting": "対象ゲームの ASAR 整合性検証 Fuse オフセットを入力してください。\n\n初期値は現在の設定です。Electron の構造を確認し、先にコピーでテストしてください。エンジン名だけでは判断できません。ユーザーの config.ini に保存します。",
        "msg_fuse_saved": "Fuse オフセットが {offset} として保存されました。",
        "err_fuse_save": "Fuseオフセット設定の保存に失敗しました：",
        "msg_fuse_warn": "現在のオフセット {offset} で ASAR 整合性検証 Fuse を無効にしますか？\n\nゲーム実行ファイルを直接変更し、.fuse_backup を作成または確認します。対象ゲームの Electron 構造に合わない設定では、起動できなくなる可能性があります。\n\nゲームを終了し、先にコピーで設定を検証してください。ゲームファイルに異常がある場合は、まず Steam で整合性を確認してください。",
        "msg_fuse_disabled_or_not_found": "Fuseマークが見つからないか、すでに無効になっています。",
        "err_fuse_backup_not_found": "Fuse バックアップが見つかりません。復元できません",
        "err_fuse_backup_verify": "バックアップ検証に失敗しました: {reason}",
        "err_fuse_restore_verify": "復元検証に失敗しました！",
        "msg_fuse_restored": "Fuse が正常に復元されました。",
        "err_fuse_error": "Fuse エラー: {error}",
        "err_fuse_rollback_failed": "ロールバックに失敗しました！実行可能ファイルが破損している可能性があります。",
        "err_fuse_io_error": "IO エラー: {error}",
        "msg_fuse_backup_created": "バックアップを作成しました: {name}",
        "msg_fuse_removed": "Fuse を削除し、検証しました。",
        "msg_fuse_already_disabled": "Fuse は既に無効です。",
        # Auto Patcher
        "lbl_patch_info": "内蔵またはカスタムパッチを選択して、インストールしてください。\n別のパッチに変更する場合は、先に Steam でゲームファイルの整合性を確認するか、元のゲームファイルに戻してください。",
        "grp_patch_package": "今回使用するパッチパッケージ",
        "btn_select_patch": "ZIP を選択...",
        "btn_use_default_patch": "内蔵パッチを使用",
        "title_select_patch": "カスタムパッチパッケージを選択",
        "file_type_zip": "ZIP パッチパッケージ",
        "btn_start_patch": "インストール開始",
        "btn_restore_patch": "↩ オリジナル版に戻す",
        "btn_to_tools": "ツールボックスへ",
        "msg_patch_restore_success": "ローカルバックアップから元のゲームファイルを復元しました。\n\nセーブデータは変更していません。",
        "err_patch_backup_not_found": "パッチのインストール時に作成された app.asar のバックアップが見つかりません。\n\n安全に自動復元できないため、Steam でゲームファイルの整合性を確認してください。",
        "err_patch_backup_invalid": "app.asar のバックアップ検証に失敗したため、復元を中止しました：{reason}\n\n現在のゲームファイルは変更されていません。Steam でゲームファイルの整合性を確認してください。",
        "err_patch_restore_failed": "オリジナルのゲームファイルへの復元に失敗しました：{error}\n\nゲームを終了して再試行してください。解決しない場合は Steam でゲームファイルの整合性を確認してください。",
        "err_patch_directory_busy": "ゲームディレクトリは別のパッチ処理によって使用されています。",
        "log_patch_restoring_original": "オリジナルのゲームファイルを復元中...",
        "log_patch_restore_complete": "オリジナルのゲームファイルを復元しました。",
        "log_custom_patch_selected": "今回のインストールではカスタムパッチを使用します：{path}",
        "err_custom_patch_missing": "選択したカスタムパッチが見つかりません：{path}",
        "patch_done": "✅ 完了しました！",
        "patch_done_done": "パッチの適用が完了しました。",
        "msg_exit_after_patch": "ツールを終了しますか？\n\nパッチの適用が完了しました。",
        "err_res_missing": "❌ エラー: resources フォルダ無し。",
        "err_asar_missing": "❌ エラー: app.asar が見つかりません。",
        "err_asar_corrupted_no_backup": "❌ エラー: app.asar が破損しており、バックアップもありません。Steam でゲームファイルの整合性を確認してください。",
        "err_node_missing": "エラー: Node.js が見つかりません。インストールしてください。",
        "log_frame": "ログ (Log)",
        "title_warning": "警告",
        "title_error": "エラー",
        "title_success": "完了",
        "title_confirm": "確認",
        "title_asar_path_error": "ASAR パスエラー",
        "title_disk_space_error": "ディスク容量エラー",
        "msg_insufficient_disk_space": "ディスク容量が不足しています。空き容量を増やしてから再試行してください。",
        "lbl_reason": "理由",
        "warn_no_file": "ファイル/フォルダを選択してください。",
        "warn_not_dir": "フォルダを選択してください。",
        "warn_not_file": "ファイルを選択してください。",
        "warn_empty_dir": "❌ エラー: フォルダが空です！",
        "warn_no_extracted": "解凍履歴がありません。",
        "warn_asar_unpacked": "'app.asar.unpacked' は圧縮できません。",
        "warn_exe_not_found": "実行ファイルが見つかりません: {exe_name}\n手動で選択してください。",
        "op_success": "成功しました！",
        "confirm_overwrite": "既に存在します。上書きしますか？",
        "no_backup_selected": "バックアップが選択されていません。",
        "err_cannot_access": "❌ ディレクトリにアクセスできません。",
        "warn_missing_files": "このフォルダーのパックを続行しますか？\n\npackage.json や index.html などの想定ファイルがなく、ASAR のソースが不完全な可能性があります。\n\n展開したルートフォルダーを選択したか確認してください。",
        "warn_operation_in_progress": "操作が進行中です。お待ちください...",
        "err_asar_cmd_missing": "エラー: 'asar' コマンドが見つかりません。",
        # System Errors
        "err_verbose_quiet_exclusive": "エラー: --verbose と --quiet は同時に使用できません。",
        "err_failed_init_corelogic": "CoreLogic の初期化に失敗しました: {error}",
        "err_fatal_error": "致命的なエラー",
        "err_unexpected_error": "予期しないエラーが発生しました:\n{error}",
        "err_init_failed": "初期化に失敗しました: {error}",
        "err_config_load_failed": "設定の読み込みに失敗しました: {error}",
        "err_config_save_failed": "設定の保存に失敗しました: {error}",
        "err_config_validation_failed": "設定の検証に失敗しました: {errors}",
        "err_operation_conflict": "操作を開始できません: 競合する操作が進行中です ({operations})。",
        "err_lock_acquire_failed": "ロックの取得に失敗しました: {error}",
        "err_save_dir_not_exist": "セーブフォルダが存在しません。",
        "err_backup_not_exist": "バックアップファイル/フォルダが存在しません。",
        "err_path_not_exist": "パスが存在しません。",
        "err_delete_failed": "❌ 削除に失敗しました。ログを確認してください。",
        "err_permission_denied": "❌ アクセスが拒否されました。",
        # Steam Update Detection
        "title_steam_update_detected": "Steam 更新を検出",
        "msg_steam_update_restore_confirm": "ローカルバックアップからゲームファイルを復元し、パッチを適用しますか？\n\n現在の app.asar がありませんが、検証に合格したバックアップがあります。古いバージョンの場合、パッチ適用でバージョンや内容の不一致が起こる可能性があります。\n\n「いいえ」を選び、先に Steam で整合性を確認してから対応するパッチを適用することをお勧めします。",
        "title_asar_invalid": "ASAR ファイルが無効",
        "msg_asar_invalid": "ASAR ファイルの検証に失敗しました。\nSteam でゲームファイルの整合性を確認してください。",
        "title_game_files_missing": "ゲームファイルが見つかりません",
        "msg_game_files_missing": "app.asar もバックアップファイルも存在しません。\nこれは以下の可能性があります：\n1. ゲームのインストールが破損している\n2. ゲームのダウンロードが不完全\n3. ファイルが手動で削除された\n\nSteam でゲームの整合性を確認するか、ゲームを再インストールしてください。",
        "title_asar_missing": "ASAR ファイルが見つかりません",
        "msg_asar_missing_valid_backup": "ローカルバックアップからゲームファイルを復元し、パッチを適用しますか？\n\n現在の app.asar がありませんが、検証に合格したバックアップがあります。古いバージョンの場合、パッチ適用でバージョンや内容の不一致が起こる可能性があります。\n\n「いいえ」を選び、先に Steam で整合性を確認してから対応するパッチを適用することをお勧めします。",
        "title_backup_is_patched": "バックアップにはパッチ適用済みファイルが含まれています",
        "msg_backup_is_patched": "バックアップファイルにはパッチ適用済みの内容が含まれているため、Steam がパッチ適用済みの ASAR ファイルを削除した可能性があります。\n\nSteam でゲームの整合性を検証して元のゲームファイルを復元してから、パッチを再度適用してください。",
        "title_backup_corrupted": "バックアップが破損しています",
        "msg_backup_corrupted": "バックアップファイルは存在しますが、破損しているようです。\nこれは以下の可能性があります：\n1. 不完全なバックアッププロセス\n2. ファイルシステムの破損\n3. ディスクエラー\n\nSteam でゲームの整合性を確認するか、ゲームを再インストールしてください。",
        "title_backup_corrupted_asar_valid": "バックアップが破損していますが ASAR は有効",
        "msg_backup_corrupted_asar_valid": "破損したローカルバックアップを削除し、現在のゲームファイルを基にパッチを適用しますか？\n\n現在の ASAR はファイル検証に合格しましたが、未変更の原版であるとは限りません。続行すると新しいバックアップを作成します。既存の変更がパッチと混在する可能性があります。\n\n「いいえ」を選び、先に Steam で整合性を確認することをお勧めします。",
        "title_no_patch_info": "パッチ情報が見つかりません",
        "msg_no_patch_info": "パッチのインストールを続行しますか？\n\n有効なインストール記録がなく、現在のファイルが変更済みか確認できません。上書きするとファイルが混在する可能性があります。\n\n「いいえ」を選択し、Steam で整合性を確認してから対応するバージョンのパッチを適用することをお勧めします。",
        "title_patch_info_corrupted": "パッチ情報が破損しています",
        "msg_patch_info_corrupted": "パッチの適用を続行しますか？\n\nインストール記録が空のため、現在の状態を確認できません。上書きにより内容が混在する可能性があります。\n\n「いいえ」を選び、先に Steam で整合性を確認することをお勧めします。",
        "title_patch_info_corrupted_json": "パッチ情報が破損しています（JSON エラー）",
        "msg_patch_info_corrupted_json": "パッチの適用を続行しますか？\n\nインストール記録を読み取れません：{error}\n上書きにより内容が混在する可能性があります。\n\n「いいえ」を選び、先に Steam で整合性を確認することをお勧めします。",
        "title_old_patch_detected": "古いパッチが検出されました",
        "msg_old_patch_detected": "パッチの適用を続行しますか？\n\n前回の適用は {days} 日前です。経過日数だけではゲーム更新の有無を判断できません。現在のバージョンに対応するパッチか確認してください。\n\n不明な場合は「いいえ」を選び、先に Steam で整合性を確認してください。",
        "msg_asar_exists_no_backup": "ASAR ファイルは存在しますがバックアップがありません - 初回のパッチ適用または他のパッチツールを使用",
        "title_asar_corrupted": "ASAR ファイルが破損しています",
        "msg_asar_corrupted": "app.asar ファイルは存在しますが、破損しているようです。\nSteam でゲームの整合性を確認するか、ゲームを再インストールしてください。",
        "msg_backup_corrupted_asar_valid_rebuild": "破損したローカルバックアップを削除し、現在のゲームファイルを基にパッチを適用しますか？\n\n現在の ASAR はファイル検証に合格しましたが、未変更の原版であるとは限りません。続行すると新しいバックアップを作成します。既存の変更がパッチと混在する可能性があります。\n\n「いいえ」を選び、先に Steam で整合性を確認することをお勧めします。",
        "msg_already_patched": "ゲームにはすでにパッチが適用されています。追加の操作は必要ありません。",
        "log_patch_extracting_asar": "ASAR を展開中...",
        "log_patch_cleaning_temp": "一時ファイルを消去中...",
        "log_patch_applying": "パッチを適用中...",
        "log_patch_extracting_zip": "選択したパッチ ZIP を展開しています…",
        "log_patch_zip_root_detected": "パッチ ZIP のラッパーディレクトリを検出しました。次の階層を自動的に削除します：{root}",
        "log_patch_zip_root_direct": "パッチ ZIP は正しい ASAR ルート階層にあります。",
        "log_patch_zip_extracted": "パッチ ZIP の展開が完了しました。",
        "err_patch_zip_layout": "パッチ ZIP のルートを判定できません：{error}",
        "log_patch_copying_dir": "パッチフォルダーのファイルをコピーしています…",
        "log_patch_files_copied": "パッチファイルのコピーが完了しました。",
        "log_patch_creating_backup": "バックアップを作成中...",
        "log_patch_backup_created": "バックアップが作成されました。",
        "log_patch_packing_asar": "ASAR をパック中...",
        "log_patch_asar_replaced": "ASAR の置き換えに成功しました。",
        "log_patch_generating_meta": "パッチメタデータを生成中...",
        "log_patch_complete": "パッチの適用に成功しました。",
        "log_patch_restored_backup": "バックアップから app.asar を復元しました。",
        "log_patch_restore_failed": "バックアップの復元に失敗しました: {error}",
        "log_patch_corrupted_restoring": "app.asar が破損しています。バックアップから復元します...",
        "log_patch_validating_asar": "ASAR ファイルを検証中...",
        "title_inconsistent_state": "ファイル状態の不一致",
        "msg_inconsistent_state": "Steam でゲームファイルの整合性を確認済みで、インストールを続行しますか？\n\n現在の ASAR はローカルバックアップ、パッチ記録のどちらとも一致しません。「はい」を選ぶと古い ASAR バックアップを削除し、現在のゲームファイルを基に適用します。\n\n未確認の場合は「いいえ」を選択し、まず Steam で復元してください。異なるバージョンや変更済みのファイルの混在を防ぐためです。",
        "title_first_time_patch": "初回パッチ適用の注意",
        "msg_first_time_patch_warn": "現在のファイルが元の状態であることを確認し、パッチを適用しますか？\n\n元のバックアップがありません。現在の ASAR をバックアップし、対応するファイルをパッチで上書きします。既存の変更があると、内容が混在する可能性があります。\n\n不明な場合は「いいえ」を選び、先に Steam で整合性を確認してから対応するパッチを適用してください。",
        # About Dialog
        "about_desc": "《でびるコネクショん》非営利の個人用ローカライズツール。\nTyranoV8 用 汎用ツールボックス\n\n==== 技術提供 ====\n• コア言語: Python 3 (Pure)\n• GUI: Tkinter (Tcl/Tk)\n• パッケージエンジン: ASAR (Pure Python)\n• ビルドツール: PyInstaller\n\n==== 開発者 ====\n作者: KouzakiUmi (呜咪 / 神前海)\nGitHub: https://github.com/KouzakiUmi/DeviConHan\n\n==== ライセンス ====\n本プロジェクトは非営利目的の使用に限られます。\nゲームのすべての権利は原作者である「ばやちゃお」様に帰属します。\n",
        "about_version": "バージョン: 1.0 Release",
        "about_github_link": "GitHub ページを開く",
        "btn_ok": "OK",
    },
}

# 默认语言设置
CURRENT_LANG_CODE: str = "en"


def detect_lang() -> None:
    global CURRENT_LANG_CODE
    try:
        detected_lang = "en"
        if IS_WIN:
            import ctypes

            try:
                lang = ctypes.windll.kernel32.GetUserDefaultUILanguage()
                if lang == 2052:
                    detected_lang = "cn"
                elif lang == 1041:
                    detected_lang = "jp"
                else:
                    detected_lang = "en"
            except Exception as e:
                logger.warning(f"Failed to get Windows UI language: {e}")
                detected_lang = _detect_lang_from_env()
        else:
            detected_lang = _detect_lang_from_env()

        with _lang_lock:
            CURRENT_LANG_CODE = detected_lang
    except Exception as e:
        logger.error(f"Language detection error: {e}")
        with _lang_lock:
            CURRENT_LANG_CODE = "en"


def _detect_lang_from_env() -> str:
    """使用环境变量检测语言（跨平台）"""
    try:
        lang = os.environ.get("LANG", "").lower()
        if "zh" in lang or "cn" in lang or "tw" in lang:
            return "cn"
        elif "ja" in lang:
            return "jp"
        else:
            return "en"
    except Exception as e:
        logger.warning(f"Language detection fallback failed: {e}")
        return "en"


def T(key: str, default: str = "") -> str:
    """
    多语言翻译函数（线程安全版本）

    使用版本号机制确保语言切换时自动刷新缓存。

    Args:
        key: 翻译键
        default: 当找不到翻译时返回的默认文本，如果为空则返回键名

    Returns:
        对应语言的文本
    """
    global _lang_version

    # 获取当前全局版本号
    with _version_lock:
        current_version = _lang_version

    # 检查线程本地缓存
    cache = getattr(_thread_local, "lang_cache", None)

    if cache is not None:
        cached_version, cached_code, cached_dict = cache

        # 如果版本号匹配，使用缓存
        if cached_version == current_version:
            # 在当前语言字典中查找
            if key in cached_dict:
                return cached_dict[key]
            # 回退到英语
            en_dict = LANG_DICT.get("en", {})
            if key in en_dict:
                return en_dict[key]
            logger.debug(
                f"Missing translation key: '{key}' "
                f"(lang={cached_code}, fallback='{default or key}')"
            )
            return default if default else key

    # 缓存未命中或版本过期，重新加载
    with _lang_lock:
        lang_code = CURRENT_LANG_CODE
        current_dict = LANG_DICT.get(lang_code, {})

    # 更新线程本地缓存
    _thread_local.lang_cache = (current_version, lang_code, current_dict)

    # 查找翻译
    if key in current_dict:
        return current_dict[key]

    # 回退到英语
    en_dict = LANG_DICT.get("en", {})
    if key in en_dict:
        return en_dict[key]

    logger.debug(
        f"Missing translation key: '{key}' (lang={lang_code}, fallback='{default or key}')"
    )
    return default if default else key


def get_font(size: int = 9, weight: str = "normal") -> Union[Tuple[str, int], Tuple[str, int, str]]:
    """
    根据平台和语言返回合适的 UI 字体

    注意：tkinter 不支持 CSS 式逗号分隔字体回退，只会使用首个字体族名。
    因此每个平台/语言组合返回单一字体族。
    线程安全：通过锁读取全局语言代码，避免并发修改导致的数据竞争。
    """
    with _lang_lock:
        lang_code = CURRENT_LANG_CODE

    if IS_WIN:
        if lang_code == "cn":
            family = "Microsoft YaHei"
        elif lang_code == "jp":
            family = "Meiryo"
        else:
            family = "Segoe UI"
    elif sys.platform == "darwin":
        if lang_code == "cn":
            family = "PingFang SC"
        elif lang_code == "jp":
            family = "Hiragino Sans"
        else:
            family = ".AppleSystemUIFont"
    else:
        if lang_code == "cn":
            family = "Noto Sans CJK SC"
        elif lang_code == "jp":
            family = "Noto Sans CJK JP"
        else:
            family = "Noto Sans"

    if weight == "normal":
        return (family, size)
    else:
        return (family, size, weight)


def get_mono_font(
    size: int = 9, available_families: Optional[Iterable[str]] = None
) -> Tuple[str, int]:
    """Choose a log font: prefer CJK monospace, then a readable local CJK font.

    Pass Tk's available families from the UI thread to avoid implicit font
    substitution. Without an inventory, use the platform's usual default.
    """
    with _lang_lock:
        lang_code = CURRENT_LANG_CODE

    if IS_WIN:
        defaults = {"cn": "Microsoft YaHei UI", "jp": "Meiryo", "en": "Consolas"}
        fallbacks = {"cn": ["Microsoft YaHei", "SimHei"], "jp": ["Yu Gothic UI", "MS Gothic"]}
    elif sys.platform == "darwin":
        defaults = {"cn": "PingFang SC", "jp": "Hiragino Sans", "en": "Menlo"}
        fallbacks = {"cn": ["Heiti SC"], "jp": ["Hiragino Kaku Gothic ProN"]}
    else:
        defaults = {"cn": "Noto Sans CJK SC", "jp": "Noto Sans CJK JP", "en": "monospace"}
        fallbacks = {"cn": ["WenQuanYi Micro Hei", "WenQuanYi Zen Hei"], "jp": ["IPAGothic"]}

    default = defaults.get(lang_code, defaults["en"])
    if available_families is None:
        return (default, size)

    available = {family.casefold(): family for family in available_families}
    if lang_code in ("cn", "jp"):
        region = "SC" if lang_code == "cn" else "JP"
        candidates = [
            "Sarasa Mono " + ("SC" if lang_code == "cn" else "J"),
            "Noto Sans Mono CJK " + region,
            default,
            *fallbacks[lang_code],
        ]
    else:
        candidates = [default, "Cascadia Mono", "DejaVu Sans Mono", "Liberation Mono"]
    for family in candidates:
        if family.casefold() in available:
            return (available[family.casefold()], size)
    return (default, size)


def set_language(code: str) -> None:
    """
    设置界面语言（推荐使用此函数而非直接修改 CURRENT_LANG_CODE）

    Note: 此函数是线程安全的，会自动递增版本号通知所有线程刷新缓存

    Args:
        code: 语言代码 ('en', 'cn', 'jp')
    """
    global CURRENT_LANG_CODE, _lang_version
    if code in LANG_DICT:
        # 在单一锁内同时更新语言码和版本号，避免不一致窗口
        with _lang_lock:
            CURRENT_LANG_CODE = code
            _lang_version += 1
            _updated_version = _lang_version

        # 清除当前线程的缓存
        _thread_local.lang_cache = None

        logger.debug(f"Language changed to: {code} (version: {_updated_version})")

        # 同步报错模块的语言设置
        try:
            from utils.error_handler import set_error_language

            set_error_language(code)
        except ImportError as e:
            logger.warning(f"Failed to sync error language: {e}")

        # 自动保存到配置文件
        _save_language_to_config(code)
    else:
        logger.warning(f"Unknown language code: {code}")


def init_lang() -> None:
    """初始化语言设置，优先从配置文件读取用户偏好"""
    # 首先尝试从配置文件加载用户保存的语言偏好
    saved_lang = _load_saved_language()
    if saved_lang:
        set_language(saved_lang)
        return

    # 如果没有保存的偏好，则自动检测系统语言
    detect_lang()


def _load_saved_language() -> Optional[str]:
    """从配置文件加载保存的语言偏好"""
    try:
        # 延迟导入避免循环依赖（language -> config -> language）
        from core.config import get_config

        lang = get_config().get_gui_config("language")
        if lang and lang in LANG_DICT:
            logger.debug(f"Loaded saved language from AppConfig: {lang}")
            return lang
    except Exception as e:
        logger.warning(f"Failed to load saved language: {e}")
    return None


def _get_config_path() -> str:
    """获取配置文件路径（使用统一的路径函数）"""
    return get_user_config_path()


def _save_language_to_config(code: str) -> None:
    """
    保存语言偏好到配置文件。
    """
    try:
        # 延迟导入避免在模块顶层产生循环依赖
        from core.config import get_config

        cfg = get_config()
        cfg.set_gui_config("language", code)
        logger.debug(f"Language preference saved to config: {code}")
    except Exception as e:
        logger.warning(f"Failed to save language preference: {e}")
