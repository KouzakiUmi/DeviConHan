# -*- coding: utf-8 -*-

import os
import sys
import logging

logger = logging.getLogger(__name__)

# ================= 跨平台适配 / Cross-Platform =================
IS_WIN = sys.platform.startswith("win")

# ================= 多语言字典 =================
LANG_DICT = {
    'cn': {
        'menu_lang': "语言 (Language)",
        'app_title': "Tyrano 游戏工具箱 (跨平台版)",
        'tab_main': "安装补丁",
        'tab_tools': "开发者工具",
        'tab_save': "存档管理",
        # Save Manager
        'lbl_cur_save': "当前存档位置:",
        'btn_scan': "🔍 重新扫描",
        'btn_backup_now': "➕ 新建备份",
        'btn_restore': "↩️ 还原选中",
        'btn_delete': "🗑️ 删除选中",
        'chk_zip': "📦 直接保存为 ZIP (推荐)",
        'col_name': "备份名称 (时间戳)",
        'col_type': "备份类型",
        'msg_restore_confirm': "确定要还原吗？\n当前进度的存档将被覆盖！",
        'msg_delete_confirm': "确定要永久删除该备份吗？",
        'msg_restored': "✅ 存档已还原！请重启游戏。",
        'msg_backup_ok': "✅ 备份已创建。",
        'err_no_save': "未检测到存档 (请先运行一次游戏)",
        # Tools
        'grp_asar': "Asar 解包/打包",
        'lbl_src_asar': "源文件 (app.asar):",
        'lbl_src_folder': "源文件夹:",
        'btn_auto_scan': "自动扫描",
        'btn_browse_file': "选择文件...",
        'btn_browse_dir': "选择文件夹...",
        'btn_extract': "📦 执行解包 (Extract)",
        'btn_sync_path': "⬇️ 填入解包路径",
        'btn_pack': "📁 执行打包 (Pack)",
        'grp_fix': "游戏修复 (Fuse)",
        'lbl_game_exe': "游戏主程序 (.exe):",
        'btn_fuse': "🔒 移除完整性校验",
        'btn_locate': "🔍 自动定位",
        'lbl_platform': "目标平台:",
        'rad_win': "Windows",
        'rad_mac_linux': "Mac/Linux",
        # Auto Patcher
        'lbl_patch_info': "检测到内置汉化补丁。点击下方按钮开始安装。",
        'btn_start_patch': "🚀 开始安装 (Start Patch)",
        'btn_to_tools': "🛠️ 高级工具箱",
        'patch_done': "✅ 安装完成！",
        'patch_done_done': "✅ 补丁安装成功！\n\n所有临时文件已清理完毕。",
        'msg_exit_after_patch': "补丁已成功安装！\n\n是否现在退出工具？\n（需要时您可以再次运行）",
        'err_res_missing': "❌ 错误: 缺少 resources 文件夹。",
        'err_asar_missing': "❌ 错误: 未找到 app.asar 文件。",
        'err_node_missing': "Error: Node.js 未找到，请安装 Node.js。",
        # Common
        'log_frame': "运行日志 (Log)",
        'title_warning': "警告",
        'title_error': "错误",
        'title_success': "完成",
        'title_confirm': "确认",
        'warn_no_file': "请先选择文件/文件夹。",
        'warn_not_dir': "请选择文件夹。",
        'warn_not_file': "请选择文件。",
        'warn_empty_dir': "❌ 错误: 目标文件夹是空的！无法打包。",
        'warn_no_extracted': "暂无解包记录。请先执行一次解包。",
        'warn_asar_unpacked': "请不要直接打包 'app.asar.unpacked'，请选择源码目录。",
        'op_success': "操作成功！",
        'confirm_overwrite': "目标已存在，是否覆盖？",
        'no_backup_selected': "未选择备份。",
        'err_asar_cmd_missing': "Error: 'asar' 命令不可用。",
        # Steam Update Detection
        'title_game_files_missing': "游戏文件缺失",
        'msg_game_files_missing': "app.asar 和备份文件都不存在。\n这可能表明：\n1. 游戏安装损坏\n2. 游戏下载不完整\n3. 文件被手动删除\n\n请通过 Steam 验证游戏完整性或重新安装游戏。",
        'title_asar_missing': "ASAR 文件缺失",
        'msg_asar_missing_valid_backup': "app.asar 文件缺失，但存在有效的备份。\n这可能由于：\n1. Steam 更新了游戏\n2. 文件被手动删除\n\n是否继续打补丁？备份将自动恢复。",
        'title_backup_corrupted': "备份文件损坏",
        'msg_backup_corrupted': "备份文件存在但似乎已损坏。\n这可能由于：\n1. 不完整的备份过程\n2. 文件系统损坏\n3. 磁盘错误\n\n请通过 Steam 验证游戏完整性或重新安装游戏。",
        'title_backup_corrupted_asar_valid': "备份损坏但 ASAR 有效",
        'msg_backup_corrupted_asar_valid': "备份文件似乎已损坏，但 ASAR 文件有效。\n这可能由于：\n1. 不完整的备份过程\n2. 文件系统损坏\n\n是否继续打补丁？将创建新备份。",
        'title_no_patch_info': "无补丁信息",
        'msg_no_patch_info': "未找到补丁信息文件。这可能由于：\n1. 使用了旧版本的补丁工具\n2. 使用了其他补丁工具\n3. 补丁信息被删除\n\n是否继续打补丁？将创建新备份。",
        'title_patch_info_corrupted': "补丁信息损坏",
        'msg_patch_info_corrupted': "补丁信息文件为空（可能损坏）。\n是否继续打补丁？这可能会覆盖现有数据。",
        'title_patch_info_corrupted_json': "补丁信息损坏（JSON 错误）",
        'msg_patch_info_corrupted_json': "补丁信息文件损坏（JSON 解析错误）。\n错误：{error}\n\n是否继续打补丁？这可能会覆盖现有数据。",
        'title_old_patch_detected': "检测到旧补丁",
        'msg_old_patch_detected': "补丁是在 {days} 天前应用的。\nSteam 可能已更新游戏。是否继续打补丁？",
        'msg_asar_exists_no_backup': "ASAR 文件存在但无备份 - 首次打补丁或使用了其他补丁工具",
        'title_asar_corrupted': "ASAR 文件损坏",
        'msg_asar_corrupted': "app.asar 文件存在但似乎已损坏。\n请通过 Steam 验证游戏完整性或重新安装游戏。",
        'msg_backup_corrupted_asar_valid_rebuild': "备份文件似乎已损坏，但 ASAR 文件有效。\n这可能由于：\n1. 不完整的备份过程\n2. 文件系统损坏\n\n是否继续打补丁？将创建新备份。",
    },
    'en': {
        'menu_lang': "Language",
        'app_title': "Tyrano Toolbox (Cross-Platform)",
        'tab_main': "Install Patch",
        'tab_tools': "Dev Tools",
        'tab_save': "Save Manager",
        # Save Manager
        'lbl_cur_save': "Save Path:",
        'btn_scan': "Rescan",
        'btn_backup_now': "Backup Now",
        'btn_restore': "Restore Selected",
        'btn_delete': "Delete Selected",
        'chk_zip': "Save as ZIP (Direct)",
        'col_name': "Backup Name (Timestamp)",
        'col_type': "Backup Type",
        'msg_restore_confirm': "Restore this backup?\nCurrent save will be overwritten!",
        'msg_delete_confirm': "Delete this backup permanently?",
        'msg_restored': "✅ Restored! Please restart game.",
        'msg_backup_ok': "✅ Backup created.",
        'err_no_save': "Save folder not found.",
        # Tools
        'grp_asar': "Asar Operations",
        'lbl_src_asar': "Source (app.asar):",
        'lbl_src_folder': "Source Folder:",
        'btn_auto_scan': "Auto Scan",
        'btn_browse_file': "Browse File...",
        'btn_browse_dir': "Browse Dir...",
        'btn_extract': "📦 Extract",
        'btn_sync_path': "⬇️ Use Extracted",
        'btn_pack': "📁 Pack",
        'grp_fix': "Game Fix (Fuse)",
        'lbl_game_exe': "Game EXE:",
        'btn_fuse': "🔒 Remove Fuse",
        'btn_locate': "Auto Locate",
        'lbl_platform': "Target:",
        'rad_win': "Windows",
        'rad_mac_linux': "Mac/Linux",
        # Auto Patcher
        'lbl_patch_info': "Patch detected. Click button to install.",
        'btn_start_patch': "🚀 Start Patch",
        'btn_to_tools': "🛠️ Advanced Tools",
        'patch_done': "✅ Install Complete!",
        'patch_done_done': "✅ Patch installation completed successfully!\n\nAll temporary files have been cleaned up.",
        'msg_exit_after_patch': "The patch has been installed successfully.\n\nDo you want to exit the tool now?\n(You can always run it again when needed)",
        'err_res_missing': "❌ Error: 'resources' folder missing.",
        'err_asar_missing': "❌ Error: app.asar not found.",
        'err_node_missing': "Error: Node.js not found! Please install Node.js.",
        'log_frame': "Log",
        'title_warning': "Warning",
        'title_error': "Error",
        'title_success': "Success",
        'title_confirm': "Confirm",
        'warn_no_file': "Please select a file/folder.",
        'warn_not_dir': "Please select a directory.",
        'warn_not_file': "Please select a file.",
        'warn_empty_dir': "❌ Error: Source directory is empty!",
        'warn_no_extracted': "No extraction history found.",
        'warn_asar_unpacked': "Cannot pack 'app.asar.unpacked'. Select source dir.",
        'op_success': "Operation Success!",
        'confirm_overwrite': "Target exists, overwrite?",
        'no_backup_selected': "No backup selected.",
        'err_asar_cmd_missing': "Error: 'asar' command not available.",
        # Steam Update Detection
        'title_game_files_missing': "Game Files Missing",
        'msg_game_files_missing': "Neither app.asar nor backup file exists.\nThis could indicate:\n1. Corrupted game installation\n2. Incomplete game download\n3. Files were manually deleted\n\nPlease verify game integrity through Steam or reinstall the game.",
        'title_asar_missing': "ASAR File Missing",
        'msg_asar_missing_valid_backup': "The app.asar file is missing, but a valid backup exists.\nThis could be due to:\n1. Steam updated the game\n2. The file was manually deleted\n\nDo you want to continue patching? The backup will be restored automatically.",
        'title_backup_corrupted': "Backup Corrupted",
        'msg_backup_corrupted': "The backup file exists but appears to be corrupted.\nThis could be due to:\n1. Incomplete backup process\n2. File system corruption\n3. Disk errors\n\nPlease verify game integrity through Steam or reinstall the game.",
        'title_backup_corrupted_asar_valid': "Backup Corrupted but ASAR Valid",
        'msg_backup_corrupted_asar_valid': "The backup file appears to be corrupted, but the ASAR file is valid.\nThis could be due to:\n1. Incomplete backup process\n2. File system corruption\n\nDo you want to continue patching? A new backup will be created.",
        'title_no_patch_info': "No Patch Info",
        'msg_no_patch_info': "No patch info file found. This could be:\n1. Old version of this patch tool\n2. Used other patch tools\n3. Patch info was deleted\n\nDo you want to continue patching? A new backup will be created.",
        'title_patch_info_corrupted': "Corrupted Patch Info",
        'msg_patch_info_corrupted': "The patch info file is empty (possibly corrupted).\nDo you want to continue patching? This may overwrite existing data.",
        'title_patch_info_corrupted_json': "Corrupted Patch Info (JSON Error)",
        'msg_patch_info_corrupted_json': "The patch info file is corrupted (JSON parsing error).\nError: {error}\n\nDo you want to continue patching? This may overwrite existing data.",
        'title_old_patch_detected': "Old Patch Detected",
        'msg_old_patch_detected': "The patch was applied {days} days ago.\nSteam may have updated the game. Do you want to continue patching?",
        'msg_asar_exists_no_backup': "ASAR file exists but no backup - first time patching or used other patch tools",
        'title_asar_corrupted': "ASAR Corrupted",
        'msg_asar_corrupted': "The app.asar file exists but appears to be corrupted.\nPlease verify game integrity through Steam or reinstall the game.",
        'msg_backup_corrupted_asar_valid_rebuild': "The backup file appears to be corrupted, but the ASAR file is valid.\nThis could be due to:\n1. Incomplete backup process\n2. File system corruption\n\nDo you want to continue patching? A new backup will be created.",
    },
    'jp': {
        'menu_lang': "言語 (Language)",
        'app_title': "Tyrano ツールボックス (Cross-Platform)",
        'tab_main': "パッチ適用",
        'tab_tools': "開発ツール",
        'tab_save': "セーブ管理",
        # Save Manager
        'lbl_cur_save': "セーブ場所:",
        'btn_scan': "再スキャン",
        'btn_backup_now': "バックアップ作成",
        'btn_restore': "復元",
        'btn_delete': "削除",
        'chk_zip': "🗑️ 直接 ZIP 保存（推奨）",
        'col_name': "バックアップ名 (日時)",
        'col_type': "バックアップ型",
        'msg_restore_confirm': "復元しますか？\n現在のセーブデータは上書きされます！",
        'msg_delete_confirm': "このバックアップを完全に削除しますか？",
        'msg_restored': "✅ 復元しました。再起動してください。",
        'msg_backup_ok': "✅ バックアップ完了。",
        'err_no_save': "セーブフォルダ未検出。",
        # Tools
        'grp_asar': "Asar 解凍/圧縮",
        'lbl_src_asar': "元ファイル (app.asar):",
        'lbl_src_folder': "元フォルダ:",
        'btn_auto_scan': "自動検出",
        'btn_browse_file': "ファイル選択...",
        'btn_browse_dir': "フォルダ選択...",
        'btn_extract': "📦 解凍 (Extract)",
        'btn_sync_path': "⬇️ 解凍パスを使用",
        'btn_pack': "📁 圧縮 (Pack)",
        'grp_fix': "修正 (Fuse)",
        'lbl_game_exe': "実行ファイル:",
        'btn_fuse': "🔒 Fuse解除",
        'btn_locate': "自動検出",
        'lbl_platform': "対象OS:",
        'rad_win': "Windows",
        'rad_mac_linux': "Mac/Linux",
        # Auto Patcher
        'lbl_patch_info': "パッチが見つかりました。",
        'btn_start_patch': "🚀 インストール開始",
        'btn_to_tools': "🛠️ ツールボックスへ",
        'patch_done': "✅ 完了しました！",
        'patch_done_done': "✅ パッチのインストールが完了しました！\n\n一時ファイルはすべてクリーンアップされました。",
        'msg_exit_after_patch': "パッチが正常にインストールされました！\n\n今ツールを終了しますか？\n（必要に応じていつでも再実行できます）",
        'err_res_missing': "❌ エラー: resources フォルダ無し。",
        'err_asar_missing': "❌ エラー: app.asar が見つかりません。",
        'err_node_missing': "エラー: Node.js が見つかりません。インストールしてください。",
        'log_frame': "ログ (Log)",
        'title_warning': "警告",
        'title_error': "错误",
        'title_success': "完了",
        'title_confirm': "确认",
        'warn_no_file': "ファイル/フォルダを選択してください。",
        'warn_not_dir': "フォルダを選択してください。",
        'warn_not_file': "ファイルを選択してください。",
        'warn_empty_dir': "❌ エラー: フォルダが空です！",
        'warn_no_extracted': "解凍履歴がありません。",
        'warn_asar_unpacked': "'app.asar.unpacked' は圧縮できません。",
        'op_success': "成功しました！",
        'confirm_overwrite': "既に存在します。上書きしますか？",
        'no_backup_selected': "バックアップが選択されていません。",
        'err_asar_cmd_missing': "エラー: 'asar' コマンドが見つかりません。",
        # Steam Update Detection
        'title_game_files_missing': "ゲームファイルが見つかりません",
        'msg_game_files_missing': "app.asar もバックアップファイルも存在しません。\nこれは以下の可能性があります：\n1. ゲームのインストールが破損している\n2. ゲームのダウンロードが不完全\n3. ファイルが手動で削除された\n\nSteam でゲームの整合性を確認するか、ゲームを再インストールしてください。",
        'title_asar_missing': "ASAR ファイルが見つかりません",
        'msg_asar_missing_valid_backup': "app.asar ファイルは存在しませんが、有効なバックアップが存在します。\nこれは以下の可能性があります：\n1. Steam がゲームを更新した\n2. ファイルが手動で削除された\n\nパッチを適用し続けますか？バックアップが自動的に復元されます。",
        'title_backup_corrupted': "バックアップが破損しています",
        'msg_backup_corrupted': "バックアップファイルは存在しますが、破損しているようです。\nこれは以下の可能性があります：\n1. 不完全なバックアッププロセス\n2. ファイルシステムの破損\n3. ディスクエラー\n\nSteam でゲームの整合性を確認するか、ゲームを再インストールしてください。",
        'title_backup_corrupted_asar_valid': "バックアップが破損していますが ASAR は有効",
        'msg_backup_corrupted_asar_valid': "バックアップファイルは破損しているようですが、ASAR ファイルは有効です。\nこれは以下の可能性があります：\n1. 不完全なバックアッププロセス\n2. ファイルシステムの破損\n\nパッチを適用し続けますか？新しいバックアップが作成されます。",
        'title_no_patch_info': "パッチ情報が見つかりません",
        'msg_no_patch_info': "パッチ情報ファイルが見つかりません。これは以下の可能性があります：\n1. このパッチツールの古いバージョン\n2. 他のパッチツールを使用した\n3. パッチ情報が削除された\n\nパッチを適用し続けますか？新しいバックアップが作成されます。",
        'title_patch_info_corrupted': "パッチ情報が破損しています",
        'msg_patch_info_corrupted': "パッチ情報ファイルが空です（破損している可能性があります）。\nパッチを適用し続けますか？これにより既存のデータが上書きされる可能性があります。",
        'title_patch_info_corrupted_json': "パッチ情報が破損しています（JSON エラー）",
        'msg_patch_info_corrupted_json': "パッチ情報ファイルが破損しています（JSON 解析エラー）。\nエラー：{error}\n\nパッチを適用し続けますか？これにより既存のデータが上書きされる可能性があります。",
        'title_old_patch_detected': "古いパッチが検出されました",
        'msg_old_patch_detected': "パッチは {days} 日前に適用されました。\nSteam がゲームを更新した可能性があります。パッチを適用し続けますか？",
        'msg_asar_exists_no_backup': "ASAR ファイルは存在しますがバックアップがありません - 初回のパッチ適用または他のパッチツールを使用",
        'title_asar_corrupted': "ASAR ファイルが破損しています",
        'msg_asar_corrupted': "app.asar ファイルは存在しますが、破損しているようです。\nSteam でゲームの整合性を確認するか、ゲームを再インストールしてください。",
        'msg_backup_corrupted_asar_valid_rebuild': "バックアップファイルは破損しているようですが、ASAR ファイルは有効です。\nこれは以下の可能性があります：\n1. 不完全なバックアッププロセス\n2. ファイルシステムの破損\n\nパッチを適用し続けますか？新しいバックアップが作成されます。",
    }
}

# 默认语言设置
CURRENT_LANG_CODE = 'en'

def detect_lang():
    global CURRENT_LANG_CODE
    try:
        if IS_WIN:
            import ctypes
            try:
                lang = ctypes.windll.kernel32.GetUserDefaultUILanguage()
                if lang == 2052: 
                    CURRENT_LANG_CODE = 'cn'
                elif lang == 1041: 
                    CURRENT_LANG_CODE = 'jp'
                else: 
                    CURRENT_LANG_CODE = 'en'
            except Exception as e:
                logger.warning(f"Failed to get Windows UI language: {e}")
                # 使用环境变量作为后备
                detect_lang_fallback()
        else:
            detect_lang_fallback()
    except Exception as e:
        logger.error(f"Language detection error: {e}")
        CURRENT_LANG_CODE = 'en'

def detect_lang_fallback():
    """使用环境变量检测语言（跨平台）"""
    try:
        lang = os.environ.get('LANG', '').lower()
        if 'zh' in lang or 'cn' in lang or 'tw' in lang:
            CURRENT_LANG_CODE = 'cn'
        elif 'ja' in lang:
            CURRENT_LANG_CODE = 'jp'
        else:
            CURRENT_LANG_CODE = 'en'
    except Exception as e:
        logger.warning(f"Language detection fallback failed: {e}")
        CURRENT_LANG_CODE = 'en'

def T(key):
    """
    多语言翻译函数
    
    Args:
        key: 翻译键
        
    Returns:
        对应语言的文本
    """
    return LANG_DICT.get(CURRENT_LANG_CODE, LANG_DICT.get("en")).get(key, key)

def init_lang():
    detect_lang()
