# -*- coding: utf-8 -*-
"""
恶魔链接补丁工具 - GUI主窗口模块

提供图形用户界面，用于执行ASAR文件操作、备份还原、补丁应用等功能。
包含性能监控集成，用于跟踪和优化GUI操作性能。
"""

import os
import sys
import shutil
import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext, ttk
import datetime
import logging
import subprocess
import queue

from typing import Optional

from core.config import get_config
from core.patcher import CoreLogic
from core.patch_info import has_embedded_patch
from core.fuse import remove_fuse
from core.save_service import SaveService
from controllers.patch_controller import PatchController
from controllers.save_manager_controller import SaveManagerController
from utils.language import T, get_font, get_mono_font
from utils.paths import get_resource_path, get_user_config_path
from utils.performance import get_performance_monitor
from utils.async_ops import get_async_manager, ProgressInfo
from utils.constants import (
    UNPACKED_DIR_NAME,
    PACKED_DIR_NAME,
    EXTRACTED_SUFFIX,
    ASAR_EXTENSION,
    CORRUPTED_SUFFIX,
    DEFAULT_DIALOG_TIMEOUT,
    LOG_AREA_HEIGHT,
    WINDOW_MIN_WIDTH,
    WINDOW_MIN_HEIGHT,
)
from gui.about_dialog import show_about_dialog

logger = logging.getLogger(__name__)


class App(tk.Tk):
    def __init__(self, log_callback=None):
        """
        初始化GUI应用程序

        Args:
            log_callback: 日志回调函数（用于批处理模式）
        """
        super().__init__()

        # 初始化属性
        self.core: Optional[CoreLogic] = None
        self.current_save_dir: Optional[str] = None
        self.last_extracted_path: Optional[str] = None
        self.is_operating: bool = False
        self.var_plat: Optional[tk.StringVar] = None
        self.var_zip: Optional[tk.BooleanVar] = None
        self.var_console: Optional[tk.BooleanVar] = None
        self.var_backup_dir: Optional[tk.StringVar] = None

        try:
            # 初始化核心逻辑（可能抛出异常）
            self.core = CoreLogic()
            self.save_service = SaveService(self.core)
            self.save_controller = SaveManagerController(
                self.save_service, log_callback=self.log
            )
            self.patch_controller = PatchController(self.core, log_callback=self.log)
        except Exception as e:
            logger.error(f"Failed to initialize CoreLogic: {e}")
            messagebox.showerror(T("title_error", "Initialization Error"), str(e))
            self.destroy()
            raise RuntimeError(f"Initialization failed: {e}") from e

        self.log_callback = log_callback  # 允许外部设置日志回调
        self.app_config = None
        # 使用统一的配置路径函数
        self.config_file = get_user_config_path()

        self.load_config()

        # 初始化性能监控器
        self.performance_monitor = get_performance_monitor()

        # 初始化异步任务管理器
        self.async_manager = get_async_manager()
        self.async_manager.set_progress_callback(self._on_async_progress)

        # 修复说明：原实现无 maxsize，若后台线程高频回调则队列无限增长导致内存溢出。
        # 修复：设置 maxsize=500，导虫入队改用 put_nowait 并在满队时少量丢弃日志更新。
        self._ui_queue = queue.Queue(maxsize=500)
        self._process_ui_queue()

        self.init_ui()

    def _process_ui_queue(self):
        """处理来自后台线程的UI更新任务"""
        try:
            while True:
                task = self._ui_queue.get_nowait()
                task()
        except queue.Empty:
            pass
        self.after(50, self._process_ui_queue)

    def init_ui(self):
        for widget in self.winfo_children():
            widget.destroy()

        self.title(T("app_title"))
        self.geometry(f"{WINDOW_MIN_WIDTH}x{WINDOW_MIN_HEIGHT}")
        self.minsize(WINDOW_MIN_WIDTH, WINDOW_MIN_HEIGHT)

        default_font = get_font(9)
        self.option_add("*Font", default_font)

        try:
            icon_path = get_resource_path("icon.ico")
            if os.path.exists(icon_path):
                self.iconbitmap(icon_path)
        except Exception as e:
            logger.warning(f"Failed to set app icon: {e}")

        menubar = tk.Menu(self)
        self.config(menu=menubar)
        lang_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label=T("menu_lang"), menu=lang_menu)
        lang_menu.add_command(
            label="English", command=lambda l="en": self.change_lang(l)
        )
        lang_menu.add_command(
            label="简体中文", command=lambda l="cn": self.change_lang(l)
        )
        lang_menu.add_command(
            label="日本語", command=lambda l="jp": self.change_lang(l)
        )

        about_menu = tk.Menu(menubar, tearoff=0)
        about_label = T("menu_about")
        about_app_label = T("menu_about_app")
        menubar.add_cascade(label=about_label, menu=about_menu)
        about_menu.add_command(
            label=about_app_label, command=lambda: show_about_dialog(self)
        )

        # 修复说明：原实现 darwin 和 else 分支都使用 "clam"，是重复代码。已合并。
        style = ttk.Style()
        if sys.platform.startswith("win"):
            style.theme_use("vista")
        else:
            style.theme_use("clam")

        style.configure(".", font=default_font)
        style.configure("TButton", padding=(5, 3))
        style.configure("Big.TButton", font=get_font(11, "bold"), padding=8)

        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill="both", expand=True, padx=5, pady=5)

        if has_embedded_patch():
            from gui.tabs.patch_tab import PatchTab

            self.tab_patch = PatchTab(self.notebook, self)
            self.notebook.add(self.tab_patch, text=T("tab_main"))

        from gui.tabs.save_tab import SaveTab

        self.tab_save = SaveTab(self.notebook, self)
        self.notebook.add(self.tab_save, text=T("tab_save"))

        from gui.tabs.tools_tab import ToolsTab

        self.tab_tools = ToolsTab(self.notebook, self)
        self.notebook.add(self.tab_tools, text=T("tab_tools"))

        self.log_frame = ttk.LabelFrame(self, text=T("log_frame"))
        self.log_frame.pack(fill="x", padx=5, pady=5, side="bottom")
        self.log_area = scrolledtext.ScrolledText(
            self.log_frame,
            height=LOG_AREA_HEIGHT,
            state="disabled",
            font=get_mono_font(9),
        )
        self.log_area.pack(fill="both", padx=5, pady=5)

        self.progress = ttk.Progressbar(self.log_frame, mode="indeterminate")
        self.progress.pack(fill="x", padx=5, pady=(0, 5))

    def load_config(self):
        """
        从配置文件加载用户偏好设置（使用统一的 AppConfig）

        修复说明（P1 配置文件重复读取）：
        原实现在 get_config() 已将配置文件读入 AppConfig 单例后，
        又用第二个 ConfigParser 重新解析同一文件并手动逐 section/key
        同步，完全冗余且存在竞态写入风险。
        修复后：
        1. 仅获取已初始化好的全局 AppConfig 实例。
        2. 若文件存在，先做轻量完整性检查（大小、非法字符）；
           若检测到损坏文件，备份后调用 reload() 回退到默认值，
           不再进行第二次完整解析。
        3. save_config 改为使用 AppConfig.save() 原子写入。

        Returns:
            bool: 是否成功加载配置
        """
        try:
            # 获取全局单例（AppConfig.__init__ 在首次调用时已读取配置文件）
            self.app_config = get_config()

            from utils.constants import MAX_CONFIG_FILE_SIZE

            if os.path.exists(self.config_file):
                file_size = os.path.getsize(self.config_file)
                if file_size > MAX_CONFIG_FILE_SIZE:
                    logger.warning(
                        f"Config file too large ({file_size} bytes), ignoring"
                    )
                    return True

                # 仅读取内容用于完整性检查，不重新解析
                with open(self.config_file, "r", encoding="utf-8") as f:
                    content = f.read()

                # 检查无效控制字符（排除合法的换行/回车/制表符）
                if any(ord(c) < 32 and c not in "\n\r\t" for c in content):
                    logger.error("Config file contains invalid characters, rejecting")
                    # 备份损坏的配置文件
                    try:
                        backup_file = self.config_file + CORRUPTED_SUFFIX
                        shutil.copy2(self.config_file, backup_file)
                        logger.info(f"Backed up corrupted config to: {backup_file}")
                    except Exception as backup_err:
                        logger.warning(
                            f"Failed to backup corrupted config: {backup_err}"
                        )
                    # 配置文件损坏：让 AppConfig 重新从默认配置加载
                    self.app_config.reload()
                    return True

                # 配置文件格式正常，AppConfig 单例已持有最新数据，无需重复解析
                logger.debug(f"Config integrity verified: {self.config_file}")
            else:
                logger.info(f"No existing config found at: {self.config_file}")

            return True

        except Exception as e:
            logger.error(f"Failed to load config: {e}")
            self.app_config = get_config()  # 使用默认配置
            return False

    def get_config_value(self, key, default=None):
        """
        获取配置值（使用统一的 AppConfig）

        Args:
            key: 配置键名
            default: 默认值

        Returns:
            配置值或默认值
        """
        try:
            if not hasattr(self, "app_config") or self.app_config is None:
                return default

            return self.app_config.get_gui_config(key, default)

        except Exception as e:
            logger.warning(f'Failed to get config value for "{key}": {e}')
            return default

    def save_config(self):
        """
        保存用户偏好设置到配置文件（使用统一的 AppConfig）

        修复说明（C2 竞态条件）：
        原实现直接操作 self.app_config.config.set() 后调用 save()，
        在批量设置多个配置项的过程中存在竞态条件。修复后使用
        AppConfig.set_gui_config_batch() 在持锁状态下一次性设置所有配置项，
        然后统一写入文件，确保原子性。

        Returns:
            bool: 是否成功保存
        """
        try:
            if not hasattr(self, "app_config") or self.app_config is None:
                logger.warning("Config object not initialized")
                return False

            # 收集所有需要保存的配置项
            config_dict = {}
            if hasattr(self, "var_plat") and self.var_plat is not None:
                config_dict["platform"] = str(self.var_plat.get())

            if hasattr(self, "var_zip") and self.var_zip is not None:
                config_dict["use_zip"] = str(self.var_zip.get()).lower()

            if hasattr(self, "var_console") and self.var_console is not None:
                config_dict["show_console"] = str(self.var_console.get()).lower()

            if hasattr(self, "var_backup_dir") and self.var_backup_dir is not None:
                config_dict["backup_dir"] = str(self.var_backup_dir.get())

            # 使用批量设置方法，在持锁状态下一次性设置所有配置项
            if config_dict:
                return self.app_config.set_gui_config_batch(config_dict)
            return True

        except Exception as e:
            logger.error(f"Failed to save config: {e}")
            return False

    def change_lang(self, code):
        """切换界面语言

        修复说明（H4）：原实现调用 set_language() 后，
        连续调用 set_gui_config() + save_config()，共触发三次文件写入，
        而 set_language() 内部已通过 _save_language_to_config() 保存了一次。
        修复：移除多余的两次写入，仅保留 set_language() 即可。
        """
        if self.is_operating:
            from tkinter import messagebox

            messagebox.showwarning(T("title_warning"), T("warn_operation_in_progress"))
            return

        from utils.language import set_language

        # set_language() 内部已调用 _save_language_to_config()，无需再次写入配置
        set_language(code)
        self.init_ui()

    def log(self, msg: str, level: str = "info") -> None:
        """
        在GUI中显示日志消息

        Args:
            msg: 要显示的消息
            level: 日志级别 ("info", "warning", "error", "debug")
        """
        # 记录到标准日志系统
        if level == "warning":
            logger.warning(msg)
        elif level == "error":
            logger.error(msg)
        elif level == "debug":
            logger.debug(msg)
        else:
            logger.info(msg)

        def _update():
            if not hasattr(self, "log_area") or not self.log_area.winfo_exists():
                return
            try:
                ts = datetime.datetime.now().strftime("%H:%M:%S")
                self.log_area.config(state="normal")

                # 根据日志级别添加颜色标记（如果支持）
                # 修复说明：原实现 level_prefix 为 "" 时保留了占位空格，
                # 导致 info 级别日志出现 "[ts]  msg" 双空格。
                # 修复：将空格纳入 level_prefix 内部。
                level_prefix = f" [{level.upper()}]" if level != "info" else ""
                self.log_area.insert(tk.END, f"[{ts}]{level_prefix} {msg}\n")
                self.log_area.see(tk.END)
                self.log_area.config(state="disabled")
            except tk.TclError:
                pass

        try:
            if hasattr(self, "_ui_queue"):
                try:
                    self._ui_queue.put_nowait(_update)
                except queue.Full:
                    # 队列达到上限时丢弃本次日志更新（GUI 卡顿期间的累积消息）
                    pass
            else:
                self.after(0, _update)
        except tk.TclError:
            pass

    def toggle_progress(self, running):
        """
        切换进度条状态

        Args:
            running: True表示开始，False表示停止
        """
        try:
            if running:
                self.progress.start(10)
            else:
                self.progress.stop()
        except tk.TclError:
            pass

    def _finish_operation(self, monitor_name: str = "") -> None:
        """
        统一的异步操作完成处理

        在异步操作的 finally 块中调用，停止进度条、重置操作状态、
        记录性能计时。

        Args:
            monitor_name: 性能监控计时器名称，为空则不记录耗时
        """
        if monitor_name:
            elapsed = self.performance_monitor.stop(monitor_name)
            logger.info(f"{monitor_name} took {elapsed:.3f}s")
        self.after(0, lambda: setattr(self, "is_operating", False))
        self.after(0, lambda: self.toggle_progress(False))

    def _window_alive(self) -> bool:
        """检查 Tkinter 窗口是否仍然存在且可用"""
        try:
            return bool(self.winfo_exists())
        except Exception:
            return False

    def _thread_safe_dialog(
        self, dialog_func, title, message, timeout, default_value, log_prefix
    ):
        """
        通用线程安全对话框方法。

        修复说明（P2 线程安全对话框空指针）：
        原实现在调用 self.after() 前没有检查窗口是否仍然存在，且
        self.after() 本身若在窗口销毁后调用会抛出未捕获的 tk.TclError。
        修复：
        1. 调用 self.after() 前先检查 _window_alive()；
        2. 将 self.after() 包裹在 try-except 中，若失败直接向队列写入默认值
           确保后台线程不会永久阻塞；
        3. 回调函数内检查 winfo_exists()，避免在销毁的父窗口上弹出对话框。

        Args:
            dialog_func: 对话框函数（如 messagebox.askyesno）
            title: 对话框标题
            message: 对话框消息
            timeout: 超时时间（秒）
            default_value: 超时或出错时的默认值
            log_prefix: 日志前缀

        Returns:
            对话框返回值或默认值
        """
        q = queue.Queue()

        def _show():
            try:
                if not self._window_alive():
                    q.put(default_value)
                    return
                res = dialog_func(title, message, parent=self)
                q.put(res)
            except Exception as e:
                logger.error(f"Error in {log_prefix} dialog: {e}")
                q.put(default_value if not isinstance(default_value, Exception) else e)

        try:
            if not self._window_alive():
                return default_value
            self.after(0, _show)
        except tk.TclError as e:
            logger.error(f"{log_prefix}: window destroyed before scheduling: {e}")
            return default_value

        try:
            return q.get(timeout=timeout)
        except queue.Empty:
            logger.error(f"{log_prefix} timed out after {timeout}s. Returning default.")
            return default_value

    def thread_safe_askyesno(self, title, message, timeout=DEFAULT_DIALOG_TIMEOUT):
        """从后台线程安全地显示 Yes/No 对话框。"""
        return self._thread_safe_dialog(
            messagebox.askyesno, title, message, timeout, False, "thread_safe_askyesno"
        )

    def thread_safe_showerror(self, title, message, timeout=DEFAULT_DIALOG_TIMEOUT):
        """从后台线程安全地显示错误对话框。"""
        return self._thread_safe_dialog(
            messagebox.showerror, title, message, timeout, None, "thread_safe_showerror"
        )

    def thread_safe_showinfo(self, title, message, timeout=DEFAULT_DIALOG_TIMEOUT):
        """从后台线程安全地显示信息对话框。"""
        return self._thread_safe_dialog(
            messagebox.showinfo, title, message, timeout, None, "thread_safe_showinfo"
        )

    def _on_async_progress(self, progress_info: ProgressInfo) -> None:
        """
        处理异步操作进度更新

        Args:
            progress_info: 进度信息对象
        """
        if progress_info.message:
            # 使用 self.log 记录重要步骤，但避免记录太频繁的进度
            if progress_info.message not in [
                "Starting...",
                "In progress...",
                "Completed",
                "Cancelled",
            ]:
                self.log(progress_info.message, "debug")

        if progress_info.state.value in ["completed", "cancelled", "failed"]:

            def update_state():
                self.toggle_progress(False)
                self.is_operating = False

            # 使用队列安全地在主线程更新UI状态，设置超时避免后台线程被无限期挂起
            try:
                self._ui_queue.put(update_state, timeout=1.0)
            except queue.Full:
                # 极端情况下如果队列仍满，尝试直接通过 tkinter 的 after 强制调度
                try:
                    self.after(0, update_state)
                except Exception:
                    pass
