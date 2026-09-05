"""
恶魔链接补丁工具 - GUI主窗口模块

提供图形用户界面，用于执行ASAR文件操作、备份还原、补丁应用等功能。
包含性能监控集成，用于跟踪和优化GUI操作性能。
"""

import datetime
import logging
import os
import queue
import shutil
import sys
import tkinter as tk
from tkinter import messagebox, scrolledtext, ttk
from typing import Optional

from controllers.patch_controller import PatchController
from controllers.save_manager_controller import SaveManagerController
from core.config import get_config
from core.patcher import CoreLogic
from core.save_service import SaveService
from gui.about_dialog import show_about_dialog
from utils.async_ops import ProgressInfo, get_async_manager
from utils.constants import (
    CORRUPTED_SUFFIX,
    DEFAULT_DIALOG_TIMEOUT,
    LOG_AREA_HEIGHT,
    WINDOW_MIN_HEIGHT,
    WINDOW_MIN_WIDTH,
)
from utils.language import T, get_font, get_mono_font
from utils.operation_lock import OperationType, get_operation_lock
from utils.paths import get_resource_path, get_user_config_path
from utils.performance import get_performance_monitor
from utils.validators import ValidationError, sanitize_user_path

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
        self._terminal_state_seen: bool = False
        self.var_plat: Optional[tk.StringVar] = None
        self.var_zip: Optional[tk.BooleanVar] = None
        self.var_console: Optional[tk.BooleanVar] = None
        self.var_backup_dir: Optional[tk.StringVar] = None

        try:
            # 初始化核心逻辑（可能抛出异常）
            self.core = CoreLogic()
            self.save_service = SaveService(self.core)
            self.save_controller = SaveManagerController(
                self.save_service, log_callback=self.ui_log
            )
            self.patch_controller = PatchController(self.core, log_callback=self.ui_log)
        except Exception as e:
            logger.error(T("err_failed_init_corelogic").format(error=str(e)))
            messagebox.showerror(T("title_error"), str(e))
            self.destroy()
            raise RuntimeError(T("err_init_failed").format(error=str(e))) from e

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

        # 初始化操作锁
        self._op_lock = get_operation_lock()

        self._ui_queue = queue.Queue(maxsize=500)
        self._process_ui_queue()

        self.init_ui()

    def _process_ui_queue(self):
        """处理来自后台线程的UI更新任务"""
        try:
            while True:
                task = self._ui_queue.get_nowait()
                try:
                    task()
                except Exception:
                    logger.debug("UI queue task failed", exc_info=True)
        except queue.Empty:
            pass
        self.after(50, self._process_ui_queue)

    def _on_window_close(self):
        """窗口关闭时的清理逻辑"""
        logger.info("Window closing, cleaning up resources...")
        try:
            # 停止所有运行中的异步操作并等待线程池关闭
            self.async_manager.shutdown(wait=True)
        except Exception as e:
            logger.warning(f"Error during async manager shutdown: {e}")
        finally:
            self.destroy()

    def init_ui(self):
        for widget in self.winfo_children():
            widget.destroy()

        # 设置窗口关闭协议，确保异步操作正确清理
        self.protocol("WM_DELETE_WINDOW", self._on_window_close)

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
        lang_menu.add_command(label="English", command=lambda lang="en": self.change_lang(lang))
        lang_menu.add_command(label="简体中文", command=lambda lang="cn": self.change_lang(lang))
        lang_menu.add_command(label="日本語", command=lambda lang="jp": self.change_lang(lang))

        about_menu = tk.Menu(menubar, tearoff=0)
        about_label = T("menu_about")
        about_app_label = T("menu_about_app")
        menubar.add_cascade(label=about_label, menu=about_menu)
        about_menu.add_command(label=about_app_label, command=lambda: show_about_dialog(self))

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

        # Custom ZIP installation and local restore also work in the toolbox build.
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
                    logger.warning(f"Config file too large ({file_size} bytes), ignoring")
                    return True

                # 仅读取内容用于完整性检查，不重新解析
                with open(self.config_file, encoding="utf-8") as f:
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
                        logger.warning(f"Failed to backup corrupted config: {backup_err}")
                    # 配置文件损坏：用默认配置覆盖后重新加载
                    try:
                        default_config_path = get_resource_path("config.ini")
                        shutil.copy2(default_config_path, self.config_file)
                        logger.info("Replaced corrupted config with default config")
                    except Exception as replace_err:
                        logger.warning(f"Failed to replace corrupted config: {replace_err}")
                    self.app_config.reload()
                    return True

                # 配置文件格式正常，AppConfig 单例已持有最新数据，无需重复解析
                logger.debug(f"Config integrity verified: {self.config_file}")
            else:
                logger.info(f"No existing config found at: {self.config_file}")

            return True

        except Exception as e:
            logger.error(T("err_config_load_failed").format(error=str(e)))
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
                backup_dir = sanitize_user_path(str(self.var_backup_dir.get()), allow_empty=True)
                config_dict["backup_dir"] = backup_dir

            # 使用批量设置方法，在持锁状态下一次性设置所有配置项
            if config_dict:
                return self.app_config.set_gui_config_batch(config_dict)
            return True

        except ValidationError as e:
            logger.error(f"Invalid GUI config input: {e}")
            return False
        except Exception as e:
            logger.error(T("err_config_save_failed").format(error=str(e)))
            return False

    def change_lang(self, code):
        """切换界面语言"""
        if self.is_operating:
            from tkinter import messagebox

            messagebox.showwarning(T("title_warning"), T("warn_operation_in_progress"))
            return

        from utils.language import set_language

        # set_language() 内部已调用 _save_language_to_config()，无需再次写入配置
        set_language(code)
        self.init_ui()

    def _queue_log_update(self, msg: str, level: str = "info") -> None:
        """将日志消息排入 GUI 日志区域更新队列。"""

        def _update():
            if not hasattr(self, "log_area") or not self.log_area.winfo_exists():
                return
            try:
                ts = datetime.datetime.now().strftime("%H:%M:%S")
                self.log_area.config(state="normal")

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

    def ui_log(self, msg: str, level: str = "info") -> None:
        """
        仅在 GUI 中显示日志消息，不重复写入标准日志系统。

        Args:
            msg: 要显示的消息
            level: 日志级别 ("info", "warning", "error", "debug")
        """
        self._queue_log_update(msg, level)

    def log(self, msg: str, level: str = "info") -> None:
        """
        记录到标准日志系统，并在 GUI 中显示日志消息。

        Args:
            msg: 要显示的消息
            level: 日志级别 ("info", "warning", "error", "debug")
        """
        if level == "warning":
            logger.warning(msg)
        elif level == "error":
            logger.error(msg)
        elif level == "debug":
            logger.debug(msg)
        else:
            logger.info(msg)

        self._queue_log_update(msg, level)

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

    def _finish_operation(
        self, monitor_name: str = "", op_type: Optional[OperationType] = None
    ) -> None:
        """
        统一的异步操作完成处理

        在异步操作的 finally 块中调用，停止进度条、重置操作状态、
        记录性能计时。如果提供了操作类型，会释放对应的操作锁。

        Args:
            monitor_name: 性能监控计时器名称，为空则不记录耗时
            op_type: 操作类型，提供时会释放操作锁（必须已通过 _acquire_operation_lock 获取）
        """
        if monitor_name:
            elapsed = self.performance_monitor.stop(monitor_name)
            logger.info(f"{monitor_name} took {elapsed:.3f}s")
        if op_type:
            self.after(0, lambda: self._release_operation_lock(op_type))
        else:
            self.after(0, lambda: setattr(self, "is_operating", False))
            self.after(0, lambda: self.toggle_progress(False))

    def _window_alive(self) -> bool:
        """检查 Tkinter 窗口是否仍然存在且可用"""
        try:
            return bool(self.winfo_exists())
        except Exception:
            return False

    def _thread_safe_dialog(self, dialog_func, title, message, timeout, default_value, log_prefix):
        """
        通用线程安全对话框方法。

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
                options = {"default": messagebox.NO} if dialog_func == messagebox.askyesno else {}
                res = dialog_func(title, message, parent=self, **options)
                q.put(res)
            except Exception as e:
                logger.error(f"Error in {log_prefix} dialog: {e}")
                q.put(default_value)

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

    def _acquire_operation_lock(self, op_type: OperationType) -> bool:
        """
        获取操作锁

        Args:
            op_type: 操作类型

        Returns:
            bool: 是否成功获取
        """
        if not self._op_lock.acquire(op_type):
            logger.warning(f"Failed to acquire lock for {op_type.value}")
            return False
        self._terminal_state_seen = False
        self.is_operating = True
        self.toggle_progress(True)
        return True

    def _release_operation_lock(self, op_type: OperationType) -> None:
        """
        释放操作锁

        Args:
            op_type: 操作类型
        """
        self._op_lock.release(op_type)
        self.is_operating = False
        self.toggle_progress(False)

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
            if self._terminal_state_seen:
                return
            self._terminal_state_seen = True

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
