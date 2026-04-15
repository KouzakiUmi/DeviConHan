import logging
import os
import sys
import threading
from typing import Dict, Optional, Tuple, Union

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
        "msg_config_valid": "配置完全合法，没有发现警告。",
        "msg_config_warnings": "配置有效，但存在以下警告：\n\n{warnings}",
        "msg_config_invalid": "配置存在以下错误/警告：\n\n{errors}",
        "msg_reset_confirm": "确定要将 config.ini 重置为默认配置吗？\n\n注意：这将覆盖所有自定义的 Fuse 偏移等设置，且操作不可逆。",
        "msg_reset_success": "已成功重置为默认配置。",
        "msg_reset_not_found": "找不到默认的 config.ini 模板文件。",
        "msg_reset_error": "重置配置失败: {error}",
        "title_fuse_setting": "修改 Fuse 偏移值",
        "msg_fuse_setting": "请输入针对此游戏 Electron 版本的 ASAR 完整性验证 Fuse 偏移值 (默认: 4)\n\n提示：\n- 若为标准 TyranoV8 版本，使用默认值 4 即可\n- 若遇到 Fuse 移除无效的情况，请根据实际需求和引擎版本修改此值\n- 修改将保存至 config.ini 中",
        "msg_fuse_saved": "Fuse 偏移值已成功保存为: {offset}",
        "err_fuse_save": "保存 Fuse 偏移设置失败:",
        "msg_fuse_warn": "⚠ 开发者工具警告\n\n此功能用于移除游戏可执行文件的Fuse完整性校验。\n\n⚠ 重要提示：\n1. 操作不可逆，请务必提前备份游戏执行文件！\n2. 当前使用的 Fuse 偏移值为: {offset}\n3. 此偏移值需根据实际需求修改（如遇版本更新或更换引擎）。\n4. 可在左侧“修改Fuse偏移”中调整设置。\n\n确认偏移无误并继续移除 Fuse 吗？",
        "msg_fuse_disabled_or_not_found": "未找到 Fuse 标记或已被禁用。",
        # Auto Patcher
        "lbl_patch_info": "检测到内置汉化补丁。点击下方按钮开始安装。",
        "btn_start_patch": "🚀 开始安装 (Start Patch)",
        "btn_to_tools": "🛠 高级工具箱",
        "patch_done": "✅ 安装完成！",
        "patch_done_done": "✅ 补丁安装成功！\n\n所有临时文件已清理完毕。",
        "msg_exit_after_patch": "补丁已成功安装！\n\n是否现在退出工具？\n（需要时您可以再次运行）",
        "err_res_missing": "❌ 错误: 缺少 resources 文件夹。",
        "err_asar_missing": "❌ 错误: 未找到 app.asar 文件。",
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
        "warn_missing_files": "警告：源目录中缺少必要的 asar 文件（如 package.json, index.html）。\n\n这可能不是一个有效的 asar 源码目录。\n\n是否继续打包？",
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
        "msg_steam_update_restore_confirm": "app.asar 文件缺失，但存在有效的备份。\n"
            "这可能是 Steam 更新导致的。\n\n"
            "建议：先在 Steam 中验证游戏文件完整性。\n\n"
            "您确定备份是最新的，并要从备份恢复后打补丁吗？",
        "title_asar_invalid": "ASAR 文件不合法",
        "msg_asar_invalid": "ASAR 文件验证失败。\n请在 Steam 中验证游戏文件完整性。",
        "title_game_files_missing": "游戏文件缺失",
        "msg_game_files_missing": "app.asar 和备份文件都不存在。\n这可能表明：\n1. 游戏安装损坏\n2. 游戏下载不完整\n3. 文件被手动删除\n\n请通过 Steam 验证游戏完整性或重新安装游戏。",
        "title_asar_missing": "ASAR 文件缺失",
        "msg_asar_missing_valid_backup": "app.asar 文件缺失，但存在有效的备份。\n这可能由于：\n1. 文件被手动删除\n2. 杀毒软件误删\n3. 其他工具误操作\n4. 游戏文件损坏\n\n是否继续打补丁？备份将自动恢复。",
        "title_backup_is_patched": "备份包含已打补丁的文件",
        "msg_backup_is_patched": "检测到备份文件包含已打补丁的内容，这意味着 Steam 已删除了您已打补丁的 ASAR 文件。\n\n请通过 Steam 验证游戏文件完整性来恢复原始游戏文件，然后再重新打补丁。",
        "title_backup_corrupted": "备份文件损坏",
        "msg_backup_corrupted": "备份文件存在但似乎已损坏。\n这可能由于：\n1. 不完整的备份过程\n2. 文件系统损坏\n3. 磁盘错误\n\n请通过 Steam 验证游戏完整性或重新安装游戏。",
        "title_backup_corrupted_asar_valid": "备份损坏但 ASAR 有效",
        "msg_backup_corrupted_asar_valid": "备份文件似乎已损坏，但 ASAR 文件有效。\n这可能由于：\n1. 不完整的备份过程\n2. 文件系统损坏\n\n是否继续打补丁？将创建新备份。",
        "title_no_patch_info": "无补丁信息",
        "msg_no_patch_info": "未找到补丁信息文件。这可能由于：\n1. 使用了旧版本的补丁工具\n2. 使用了其他补丁工具\n3. 补丁信息被删除\n\n是否继续打补丁？将创建新备份。",
        "title_patch_info_corrupted": "补丁信息损坏",
        "msg_patch_info_corrupted": "补丁信息文件为空（可能损坏）。\n是否继续打补丁？这可能会覆盖现有数据。",
        "title_patch_info_corrupted_json": "补丁信息损坏（JSON 错误）",
        "msg_patch_info_corrupted_json": "补丁信息文件损坏（JSON 解析错误）。\n错误：{error}\n\n是否继续打补丁？这可能会覆盖现有数据。",
        "title_old_patch_detected": "检测到旧补丁",
        "msg_old_patch_detected": "补丁是在 {days} 天前应用的。\nSteam 可能已更新游戏。是否继续打补丁？",
        "msg_asar_exists_no_backup": "ASAR 文件存在但无备份 - 首次打补丁或使用了其他补丁工具",
        "title_asar_corrupted": "ASAR 文件损坏",
        "msg_asar_corrupted": "app.asar 文件存在但似乎已损坏。\n请通过 Steam 验证游戏完整性或重新安装游戏。",
        "msg_backup_corrupted_asar_valid_rebuild": "备份文件似乎已损坏，但 ASAR 文件有效。\n这可能由于：\n1. 不完整的备份过程\n2. 文件系统损坏\n\n是否继续打补丁？将创建新备份。",
        "msg_already_patched": "游戏已经安装过本补丁，文件状态正常，无需再次安装。",
        "title_inconsistent_state": "文件状态不一致",
        "msg_inconsistent_state": "检测到游戏文件 (app.asar) 与已有的备份文件不一致，且均未正确安装本补丁。\n\n👉 如果您刚刚在 Steam 中【验证了游戏文件的完整性】：\n说明当前的游戏文件是官方纯净版。请点击“是 (Yes)”，程序将废弃旧备份并为您重新打补丁。\n\n👉 如果您没有验证过完整性：\n当前文件可能已被其他工具修改。强烈建议您点击“否 (No)”，先去 Steam 验证完整性后再来打补丁，以免将已被篡改的文件作为基准备份！",
        "title_first_time_patch": "首次安装补丁提醒",
        "msg_first_time_patch_warn": "未检测到原始备份文件，这似乎是您首次安装本补丁。\n\n⚠ 警告：如果您之前安装过其他汉化工具，您当前的 app.asar 可能已被篡改。继续操作将把已被篡改的文件作为您的“原版”基准备份。\n\n💡 强烈建议：如果您不确定，请在继续之前先在 Steam 中验证游戏文件的完整性。\n\n是否确认原版文件纯净，并继续备份打补丁？",
        # About Dialog
        "about_desc": "《でびるコネクション》非营利性个人本地化工具。\nTyranoV8通用工具箱\n\n==== 技术致谢 ====\n• 核心语言: Python 3 (Pure)\n• 图形界面: Tkinter (Tcl/Tk)\n• 封包引擎: ASAR (Pure Python)\n• 构建工具: PyInstaller\n\n==== 开发人员 ====\n作者：KouzakiUmi (呜咪 / 神前海)\nGitHub: https://github.com/KouzakiUmi/DeviConHan\n\n==== 许可证 ====\n本项目仅限非营利目的使用。\n游戏内容的所有权利均归原作者 ばやちゃお 所有。\n",
        "about_version": "版本: 1.0 Release",
        "about_github_link": "访问 GitHub 主页",
        "btn_ok": "确定",
    },
    "en": {
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
        "msg_config_valid": "Configuration is fully valid. No warnings found.",
        "msg_config_warnings": "Configuration is valid, but has warnings:\n\n{warnings}",
        "msg_config_invalid": "Configuration contains errors/warnings:\n\n{errors}",
        "msg_reset_confirm": "Are you sure you want to reset config.ini to defaults?\n\nWarning: This will overwrite custom Fuse offsets and other settings, and cannot be undone.",
        "msg_reset_success": "Successfully reset to default configuration.",
        "msg_reset_not_found": "Cannot find the default config.ini template file.",
        "msg_reset_error": "Failed to reset config: {error}",
        "title_fuse_setting": "Modify Fuse Offset",
        "msg_fuse_setting": "Please enter the ASAR Integrity Validation Fuse offset for this game's Electron version (Default: 4)\n\nHint:\n- For standard TyranoV8, default value 4 is sufficient.\n- If removing Fuse doesn't work, you may need to adjust this depending on the engine version.\n- Changes will be saved to config.ini.",
        "msg_fuse_saved": "Fuse offset successfully saved as: {offset}",
        "err_fuse_save": "Failed to save Fuse offset setting:",
        "msg_fuse_warn": "⚠ Developer Tool Warning\n\nThis function removes the Fuse integrity validation from the game executable.\n\n⚠ IMPORTANT:\n1. This operation is irreversible, PLEASE backup the executable first!\n2. The currently used Fuse offset is: {offset}\n3. This offset should be modified according to your needs (e.g. engine updates).\n4. You can adjust the setting via the 'Fuse Offset' button on the left.\n\nConfirm offset is correct and continue removing Fuse?",
        "msg_fuse_disabled_or_not_found": "Fuse sentinel not found or already disabled.",
        # Auto Patcher
        "lbl_patch_info": "Patch detected. Click button to install.",
        "btn_start_patch": "🚀 Start Patch",
        "btn_to_tools": "🛠 Advanced Tools",
        "patch_done": "✅ Install Complete!",
        "patch_done_done": "✅ Patch installation completed successfully!\n\nAll temporary files have been cleaned up.",
        "msg_exit_after_patch": "The patch has been installed successfully.\n\nDo you want to exit the tool now?\n(You can always run it again when needed)",
        "err_res_missing": "❌ Error: 'resources' folder missing.",
        "err_asar_missing": "❌ Error: app.asar not found.",
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
        "warn_missing_files": "Warning: Missing expected files (e.g. package.json, index.html).\n\nThis may not be a valid asar source directory.\n\nContinue anyway?",
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
        "msg_steam_update_restore_confirm": "The app.asar file is missing, but a valid backup exists.\n"
            "This may be caused by a Steam update.\n\n"
            "Recommended: Verify game integrity in Steam first.\n\n"
            "Are you sure the backup is up-to-date and want to restore from backup and apply patch?",
        "title_asar_invalid": "ASAR Invalid",
        "msg_asar_invalid": "ASAR file validation failed.\nPlease verify game integrity through Steam.",
        "title_game_files_missing": "Game Files Missing",
        "msg_game_files_missing": "Neither app.asar nor backup file exists.\nThis could indicate:\n1. Corrupted game installation\n2. Incomplete game download\n3. Files were manually deleted\n\nPlease verify game integrity through Steam or reinstall the game.",
        "title_asar_missing": "ASAR File Missing",
        "msg_asar_missing_valid_backup": "The app.asar file is missing, but a valid backup exists.\nThis could be due to:\n1. File manually deleted\n2. Antivirus software removed it\n3. Other tools misoperated\n4. Game files corrupted\n\nDo you want to continue patching? The backup will be restored automatically.",
        "title_backup_is_patched": "Backup Contains Patched Files",
        "msg_backup_is_patched": "The backup contains patched files, meaning Steam has removed your patched ASAR file.\n\nPlease verify game files integrity through Steam to restore the original game files, then apply the patch again.",
        "title_backup_corrupted": "Backup Corrupted",
        "msg_backup_corrupted": "The backup file exists but appears to be corrupted.\nThis could be due to:\n1. Incomplete backup process\n2. File system corruption\n3. Disk errors\n\nPlease verify game integrity through Steam or reinstall the game.",
        "title_backup_corrupted_asar_valid": "Backup Corrupted but ASAR Valid",
        "msg_backup_corrupted_asar_valid": "The backup file appears to be corrupted, but the ASAR file is valid.\nThis could be due to:\n1. Incomplete backup process\n2. File system corruption\n\nDo you want to continue patching? A new backup will be created.",
        "title_no_patch_info": "No Patch Info",
        "msg_no_patch_info": "No patch info file found. This could be:\n1. Old version of this patch tool\n2. Used other patch tools\n3. Patch info was deleted\n\nDo you want to continue patching? A new backup will be created.",
        "title_patch_info_corrupted": "Corrupted Patch Info",
        "msg_patch_info_corrupted": "The patch info file is empty (possibly corrupted).\nDo you want to continue patching? This may overwrite existing data.",
        "title_patch_info_corrupted_json": "Corrupted Patch Info (JSON Error)",
        "msg_patch_info_corrupted_json": "The patch info file is corrupted (JSON parsing error).\nError: {error}\n\nDo you want to continue patching? This may overwrite existing data.",
        "title_old_patch_detected": "Old Patch Detected",
        "msg_old_patch_detected": "The patch was applied {days} days ago.\nSteam may have updated the game. Do you want to continue patching?",
        "msg_asar_exists_no_backup": "ASAR file exists but no backup - first time patching or used other patch tools",
        "title_asar_corrupted": "ASAR Corrupted",
        "msg_asar_corrupted": "The app.asar file exists but appears to be corrupted.\nPlease verify game integrity through Steam or reinstall the game.",
        "msg_backup_corrupted_asar_valid_rebuild": "The backup file appears to be corrupted, but the ASAR file is valid.\nThis could be due to:\n1. Incomplete backup process\n2. File system corruption\n\nDo you want to continue patching? A new backup will be created.",
        "msg_already_patched": "The game is already successfully patched. No further action is required.",
        "title_inconsistent_state": "Inconsistent File State",
        "msg_inconsistent_state": "Detected an inconsistency between the game file (app.asar) and the backup, and neither matches this patch.\n\n👉 If you JUST verified game integrity in Steam:\nYour current game file is clean. Click 'Yes' to discard the old backup and apply the patch.\n\n👉 If you HAVE NOT verified integrity:\nYour file might be modified by other tools. It is STRONGLY RECOMMENDED to click 'No', go to Steam to verify integrity first, then try again. Otherwise, a modified file will be used as your base backup!",
        "title_first_time_patch": "First Time Patching Notice",
        "msg_first_time_patch_warn": "No original backup detected. This appears to be your first time installing this patch.\n\n⚠ WARNING: If you have previously installed other translation tools, your current app.asar may already be modified. Continuing will backup this modified file as your 'original' baseline.\n\n💡 STRONGLY RECOMMENDED: If you are unsure, please verify integrity of game files in Steam first before proceeding.\n\nDo you want to continue backing up the current state and apply the patch?",
        # About Dialog
        "about_desc": "A non-profit personal localization tool for 《でびるコネクション》.\nUniversal Toolbox for TyranoV8\n\n==== Technical Credits ====\n• Core Language: Python 3 (Pure)\n• GUI Framework: Tkinter (Tcl/Tk)\n• Packaging Engine: ASAR (Pure Python)\n• Build Tool: PyInstaller\n\n==== Developers ====\nAuthor: KouzakiUmi\nGitHub: https://github.com/KouzakiUmi/DeviConHan\n\n==== License ====\nFor non-profit purposes only.\nAll rights to the game content belong to the original author, Bayachao.\n",
        "about_version": "Version: 1.0 Release",
        "about_github_link": "Visit GitHub Page",
        "btn_ok": "OK",
    },
    "jp": {
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
        "msg_config_valid": "設定は完全に有効です。警告はありません。",
        "msg_config_warnings": "設定は有効ですが、以下の警告があります：\n\n{warnings}",
        "msg_config_invalid": "設定に以下のエラー/警告が含まれています：\n\n{errors}",
        "msg_reset_confirm": "config.ini をデフォルト設定にリセットしてもよろしいですか？\n\n警告：カスタムのFuseオフセットなどは失われ、この操作は元に戻せません。",
        "msg_reset_success": "デフォルト設定にリセットしました。",
        "msg_reset_not_found": "デフォルトの config.ini テンプレートが見つかりません。",
        "msg_reset_error": "リセットに失敗しました: {error}",
        "title_fuse_setting": "Fuse オフセット値の設定",
        "msg_fuse_setting": "このゲームのElectronバージョンに合わせた、ASAR整合性検証のFuseオフセット値を入力してください（デフォルト：4）\n\nヒント：\n- 標準のTyranoV8の場合、デフォルトの「4」で十分です。\n- Fuseの解除が無効な場合は、エンジンのバージョンに応じてこの値を変更してください。\n- 変更はconfig.iniに保存されます。",
        "msg_fuse_saved": "Fuse オフセットが {offset} として保存されました。",
        "err_fuse_save": "Fuseオフセット設定の保存に失敗しました：",
        "msg_fuse_warn": "⚠ 開発者ツール警告\n\nこの機能は、ゲームの実行可能ファイルからFuse整合性検証を削除します。\n\n⚠ 重要：\n1. この操作は元に戻せません。必ず実行ファイルをバックアップしてください！\n2. 現在使用中のFuseオフセット値は: {offset}\n3. このオフセット値は、エンジンのバージョン更新などに合わせて変更する必要があります。\n4. 左側の「Fuseオフセット」ボタンで設定を変更できます。\n\nオフセット値が正しいことを確認し、Fuseの解除を続行しますか？",
        "msg_fuse_disabled_or_not_found": "Fuseマークが見つからないか、すでに無効になっています。",
        # Auto Patcher
        "lbl_patch_info": "パッチが見つかりました。",
        "btn_start_patch": "インストール開始",
        "btn_to_tools": "ツールボックスへ",
        "patch_done": "✅ 完了しました！",
        "patch_done_done": "✅ パッチのインストールが完了しました！\n\n一時ファイルはすべてクリーンアップされました。",
        "msg_exit_after_patch": "パッチが正常にインストールされました！\n\n今ツールを終了しますか？\n（必要に応じていつでも再実行できます）",
        "err_res_missing": "❌ エラー: resources フォルダ無し。",
        "err_asar_missing": "❌ エラー: app.asar が見つかりません。",
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
        "warn_missing_files": "警告: 必要な asar ファイル（package.json、index.html など）が見つかりません。\n\n有効な asar ソースディレクトリではない可能性があります。\n\n続行しますか？",
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
        "msg_steam_update_restore_confirm": "app.asar ファイルは存在しませんが、有効なバックアップが存在します。\n"
            "これは Steam 更新による可能性があります。\n\n"
            "推奨：先に Steam でゲームファイルの整合性を確認してください。\n\n"
            "バックアップが最新であることを確認し、バックアップから復元してパッチを適用しますか？",
        "title_asar_invalid": "ASAR ファイルが無効",
        "msg_asar_invalid": "ASAR ファイルの検証に失敗しました。\nSteam でゲームファイルの整合性を確認してください。",
        "title_game_files_missing": "ゲームファイルが見つかりません",
        "msg_game_files_missing": "app.asar もバックアップファイルも存在しません。\nこれは以下の可能性があります：\n1. ゲームのインストールが破損している\n2. ゲームのダウンロードが不完全\n3. ファイルが手動で削除された\n\nSteam でゲームの整合性を確認するか、ゲームを再インストールしてください。",
        "title_asar_missing": "ASAR ファイルが見つかりません",
        "msg_asar_missing_valid_backup": "app.asar ファイルは存在しませんが、有効なバックアップが存在します。\nこれは以下の可能性があります：\n1. ファイルが手動で削除された\n2. アンチウイルスソフトが誤って削除した\n3. 他のツールが誤操作した\n4. ゲームファイルが破損した\n\nパッチを適用し続けますか？バックアップが自動的に復元されます。",
        "title_backup_is_patched": "バックアップにはパッチ適用済みファイルが含まれています",
        "msg_backup_is_patched": "バックアップファイルにはパッチ適用済みの内容が含まれているため、Steam がパッチ適用済みの ASAR ファイルを削除した可能性があります。\n\nSteam でゲームの整合性を検証して元のゲームファイルを復元してから、パッチを再度適用してください。",
        "title_backup_corrupted": "バックアップが破損しています",
        "msg_backup_corrupted": "バックアップファイルは存在しますが、破損しているようです。\nこれは以下の可能性があります：\n1. 不完全なバックアッププロセス\n2. ファイルシステムの破損\n3. ディスクエラー\n\nSteam でゲームの整合性を確認するか、ゲームを再インストールしてください。",
        "title_backup_corrupted_asar_valid": "バックアップが破損していますが ASAR は有効",
        "msg_backup_corrupted_asar_valid": "バックアップファイルは破損しているようですが、ASAR ファイルは有効です。\nこれは以下の可能性があります：\n1. 不完全なバックアッププロセス\n2. ファイルシステムの破損\n\nパッチを適用し続けますか？新しいバックアップが作成されます。",
        "title_no_patch_info": "パッチ情報が見つかりません",
        "msg_no_patch_info": "パッチ情報ファイルが見つかりません。これは以下の可能性があります：\n1. このパッチツールの古いバージョン\n2. 他のパッチツールを使用した\n3. パッチ情報が削除された\n\nパッチを適用し続けますか？新しいバックアップが作成されます。",
        "title_patch_info_corrupted": "パッチ情報が破損しています",
        "msg_patch_info_corrupted": "パッチ情報ファイルが空です（破損している可能性があります）。\nパッチを適用し続けますか？これにより既存のデータが上書きされる可能性があります。",
        "title_patch_info_corrupted_json": "パッチ情報が破損しています（JSON エラー）",
        "msg_patch_info_corrupted_json": "パッチ情報ファイルが破損しています（JSON 解析エラー）。\nエラー：{error}\n\nパッチを適用し続けますか？これにより既存のデータが上書きされる可能性があります。",
        "title_old_patch_detected": "古いパッチが検出されました",
        "msg_old_patch_detected": "パッチは {days} 日前に適用されました。\nSteam がゲームを更新した可能性があります。パッチを適用し続けますか？",
        "msg_asar_exists_no_backup": "ASAR ファイルは存在しますがバックアップがありません - 初回のパッチ適用または他のパッチツールを使用",
        "title_asar_corrupted": "ASAR ファイルが破損しています",
        "msg_asar_corrupted": "app.asar ファイルは存在しますが、破損しているようです。\nSteam でゲームの整合性を確認するか、ゲームを再インストールしてください。",
        "msg_backup_corrupted_asar_valid_rebuild": "バックアップファイルは破損しているようですが、ASAR ファイルは有効です。\nこれは以下の可能性があります：\n1. 不完全なバックアッププロセス\n2. ファイルシステムの破損\n\nパッチを適用し続けますか？新しいバックアップが作成されます。",
        "msg_already_patched": "ゲームにはすでにパッチが適用されています。追加の操作は必要ありません。",
        "title_inconsistent_state": "ファイル状態の不一致",
        "msg_inconsistent_state": "ゲームファイル (app.asar) とバックアップが一致せず、どちらもこのパッチと一致しません。\n\n👉 Steamでゲームファイルの整合性を【確認した直後】の場合：\n現在のゲームファイルはクリーンです。「はい (Yes)」をクリックすると、古いバックアップを破棄してパッチを適用します。\n\n👉 整合性を確認していない場合：\nファイルが他のツールによって変更されている可能性があります。「いいえ (No)」をクリックしてパッチ適用を中止し、Steamで整合性を確認してから再試行することを強くお勧めします！",
        "title_first_time_patch": "初回パッチ適用の注意",
        "msg_first_time_patch_warn": "元のバックアップが検出されませんでした。今回が初めてのパッチ適用のようです。\n\n⚠ 警告: 過去に他の翻訳ツールをインストールしたことがある場合、現在の app.asar はすでに変更されている可能性があります。続行すると、この変更されたファイルが基準となる「オリジナル」としてバックアップされます。\n\n💡 強く推奨: 不確かな場合は、続行する前にSteamでゲームファイルの整合性を確認してください。\n\n現在のファイルをバックアップしてパッチの適用を続行しますか？",
        # About Dialog
        "about_desc": "《でびるコネクション》非営利の個人用ローカライズツール。\nTyranoV8 用 汎用ツールボックス\n\n==== 技術提供 ====\n• コア言語: Python 3 (Pure)\n• GUI: Tkinter (Tcl/Tk)\n• パッケージエンジン: ASAR (Pure Python)\n• ビルドツール: PyInstaller\n\n==== 開発者 ====\n作者: KouzakiUmi (呜咪 / 神前海)\nGitHub: https://github.com/KouzakiUmi/DeviConHan\n\n==== ライセンス ====\n本プロジェクトは非営利目的の使用に限られます。\nゲームのすべての権利は原作者である「ばやちゃお」様に帰属します。\n",
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


def get_mono_font(size: int = 9) -> Tuple[str, int]:
    """
    返回合适的等宽字体（用于日志等）
    """
    if IS_WIN:
        family = "Consolas"
    elif sys.platform == "darwin":
        family = "Menlo"
    else:
        family = "monospace"
    return (family, size)


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
