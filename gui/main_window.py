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
import threading
import datetime
import logging
import subprocess

from core.config import get_config
from core.patcher import CoreLogic, has_embedded_patch
from core.save_service import SaveService
from controllers.patch_controller import PatchController
from controllers.save_manager_controller import SaveManagerController
from utils.cleanup import force_cleanup_dir
from utils.language import init_lang, T, get_font, get_mono_font
from utils.paths import get_resource_path, get_user_config_path
from utils.performance import get_performance_monitor
from utils.async_ops import get_async_manager, ProgressInfo
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
        self.core = None
        self.current_save_dir = None
        self.last_extracted_path = None
        self.is_operating = False
        self.var_plat = None
        self.var_zip = None
        
        try:
            # 初始化核心逻辑（可能抛出异常）
            self.core = CoreLogic()
            self.save_service = SaveService(self.core)
            self.save_controller = SaveManagerController(self.save_service, log_callback=self.log)
            self.patch_controller = PatchController(self.core, log_callback=self.log)
        except Exception as e:
            logger.error(f"Failed to initialize CoreLogic: {e}")
            messagebox.showerror(T("title_error", "Initialization Error"), str(e))
            self.after(0, self.destroy)
            return

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
        
        self.init_ui()

    def init_ui(self):
        for widget in self.winfo_children(): widget.destroy()

        self.title(T("app_title"))
        self.geometry("800x620")
        
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
        lang_menu.add_command(label="English", command=lambda l="en": self.change_lang(l))
        lang_menu.add_command(label="简体中文", command=lambda l="cn": self.change_lang(l))
        lang_menu.add_command(label="日本語", command=lambda l="jp": self.change_lang(l))

        about_menu = tk.Menu(menubar, tearoff=0)
        about_label = T("menu_about")
        about_app_label = T("menu_about_app")
        menubar.add_cascade(label=about_label, menu=about_menu)
        about_menu.add_command(label=about_app_label, command=lambda: show_about_dialog(self))

        style = ttk.Style()
        if sys.platform.startswith("win"): style.theme_use("vista")
        elif sys.platform == "darwin": style.theme_use("clam")
        else: style.theme_use("clam")
        
        style.configure(".", font=default_font)
        style.configure("Big.TButton", font=get_font(11, "bold"), padding=8)
        
        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill="both", expand=True, padx=5, pady=5)
        
        if has_embedded_patch():
            self.tab_patch = ttk.Frame(self.notebook)
            self.notebook.add(self.tab_patch, text=T("tab_main"))
            self._init_patch_ui()
            
        self.tab_save = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_save, text=T("tab_save"))
        self._init_save_manager_ui()
        
        self.tab_tools = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_tools, text=T("tab_tools"))
        self._init_tools_ui()

        self.log_frame = ttk.LabelFrame(self, text=T("log_frame"))
        self.log_frame.pack(fill="x", padx=5, pady=5, side="bottom")
        self.log_area = scrolledtext.ScrolledText(self.log_frame, height=8, state="disabled", font=get_mono_font(9))
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
            self.app_config = get_config()

            if os.path.exists(self.config_file):
                file_size = os.path.getsize(self.config_file)
                if file_size > 1024 * 1024:  # 1MB limit
                    logger.warning(f"Config file too large ({file_size} bytes), ignoring")
                    return True

                with open(self.config_file, "r", encoding="utf-8") as f:
                    content = f.read()

                if any(ord(c) < 32 and c not in "\n\r\t" for c in content):
                    logger.warning("Config file contains invalid characters")
                    return True

                # 读取配置到 AppConfig
                from configparser import ConfigParser
                parser = ConfigParser()
                parser.read_string(content)
                
                # 将配置同步到 AppConfig
                for section in parser.sections():
                    if not self.app_config.config.has_section(section):
                        self.app_config.config.add_section(section)
                    for key, value in parser.items(section):
                        self.app_config.config.set(section, key, value)
                
                logger.debug(f"Loaded config from: {self.config_file}")
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
            logger.warning(f"Failed to get config value for \"{key}\": {e}")
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
            
            # 设置配置值
            if hasattr(self, "var_plat") and self.var_plat is not None:
                value = self.var_plat.get()
                self.app_config.set_gui_config("platform", str(value))

            if hasattr(self, "var_zip") and self.var_zip is not None:
                value = self.var_zip.get()
                self.app_config.set_gui_config("use_zip", str(value).lower())

            if hasattr(self, "var_console") and self.var_console is not None:
                value = self.var_console.get()
                self.app_config.set_gui_config("show_console", str(value).lower())

            if hasattr(self, "var_backup_dir") and self.var_backup_dir is not None:
                value = self.var_backup_dir.get()
                self.app_config.set_gui_config("backup_dir", str(value))

            # 保存到文件
            config_dir = os.path.dirname(self.config_file)
            if config_dir and not os.path.exists(config_dir):
                os.makedirs(config_dir, exist_ok=True)
            
            with open(self.config_file, "w", encoding="utf-8") as f:
                self.app_config.config.write(f)
                
            logger.debug(f"Config saved to: {self.config_file}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to save config: {e}")
            return False

    def change_lang(self, code):
        """切换界面语言"""
        if self.is_operating:
            from tkinter import messagebox
            messagebox.showwarning(T("title_warning"), T("warn_operation_in_progress"))
            return
            
        from utils.language import set_language
        set_language(code)
        if hasattr(self, "app_config") and self.app_config is not None:
            self.app_config.set_gui_config("language", code)
            self.save_config()
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
            if not hasattr(self, 'log_area') or not self.log_area.winfo_exists():
                return
            try:
                ts = datetime.datetime.now().strftime("%H:%M:%S")
                self.log_area.config(state="normal")
                
                # 根据日志级别添加颜色标记（如果支持）
                level_prefix = f"[{level.upper()}]" if level != "info" else ""
                self.log_area.insert(tk.END, f"[{ts}] {level_prefix} {msg}\n")
                self.log_area.see(tk.END)
                self.log_area.config(state="disabled")
            except tk.TclError:
                pass
        
        try:
            self.after(0, _update)
        except tk.TclError:
            # 仅在紧急情况下使用 print（避免与日志系统冲突）
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

    def thread_safe_askyesno(self, title, message, timeout=30):
        import queue
        q = queue.Queue()
        def _ask():
            try:
                res = messagebox.askyesno(title, message, parent=self)
                q.put(res)
            except Exception as e:
                logger.error(f"Error in ask dialog: {e}")
                q.put(False)
        self.after(0, _ask)
        try:
            return q.get(timeout=timeout)
        except queue.Empty:
            logger.error(f"thread_safe_askyesno timed out after {timeout}s. Returning False.")
            return False

    def thread_safe_showerror(self, title, message, timeout=30):
        import queue
        q = queue.Queue()
        def _show():
            try:
                messagebox.showerror(title, message, parent=self)
                q.put(None)
            except Exception as e:
                logger.error(f"Error in showerror dialog: {e}")
                q.put(e)
        self.after(0, _show)
        try:
            return q.get(timeout=timeout)
        except queue.Empty:
            logger.error(f"thread_safe_showerror timed out after {timeout}s.")
            return None

    def thread_safe_showinfo(self, title, message, timeout=30):
        import queue
        q = queue.Queue()
        def _show():
            try:
                messagebox.showinfo(title, message, parent=self)
                q.put(None)
            except Exception as e:
                logger.error(f"Error in showinfo dialog: {e}")
                q.put(e)
        self.after(0, _show)
        try:
            return q.get(timeout=timeout)
        except queue.Empty:
            logger.error(f"thread_safe_showinfo timed out after {timeout}s.")
            return None

    def _on_async_progress(self, progress_info: ProgressInfo) -> None:
        """
        处理异步操作进度更新
        
        Args:
            progress_info: 进度信息对象
        """
        if progress_info.message:
            # 使用 self.log 记录重要步骤，但避免记录太频繁的进度
            if progress_info.message not in ["Starting...", "In progress...", "Completed", "Cancelled"]:
                self.log(progress_info.message, "debug")
            
        if progress_info.state.value in ["completed", "cancelled", "failed"]:
            self.after(0, lambda s=self: s.toggle_progress(False))
            self.after(0, lambda s=self: setattr(s, 'is_operating', False))

    def _file_entry(self, parent, label, is_dir=False, ext=None):
        """
        创建文件选择器组件
        
        Args:
            parent: 父容器
            label: 标签文本
            is_dir: 是否为目录选择
            ext: 允许的文件扩展名
            
        Returns:
            StringVar: 文件路径变量
        """
        f = ttk.Frame(parent)
        f.pack(fill="x", pady=5)
        
        label_widget = ttk.Label(f, text=label, width=15)
        label_widget.pack(side="left")
        
        var = tk.StringVar()
        entry = ttk.Entry(f, textvariable=var, width=50)
        entry.pack(side="left", fill="x", expand=True, padx=5)
        
        def _browse():
            try:
                if is_dir:
                    p = filedialog.askdirectory(
                        title=T("title_select_directory"),
                        initialdir=os.getcwd()
                    )
                else:
                    types = [(T("file_type_all"), "*.*")]
                    if ext:
                        if not isinstance(ext, (list, tuple)):
                            ext_tuple = (ext,)
                        else:
                            ext_tuple = ext
                        
                        # Fix up the types display based on extension
                        display_name = ext_tuple[0]
                        if "asar" in str(ext_tuple).lower():
                            display_name = T("file_type_asar")
                        elif "exe" in str(ext_tuple).lower():
                            display_name = T("file_type_exe")
                        
                        types.insert(0, (display_name, ext_tuple[1] if len(ext_tuple) > 1 else ext_tuple[0]))
                    
                    p = filedialog.askopenfilename(
                        title=T("title_select_file"),
                        filetypes=types,
                        initialdir=os.getcwd()
                    )
                
                if p:
                    var.set(os.path.abspath(p))
            except Exception as e:
                logger.error(f"File browser error: {e}")
                messagebox.showerror(T("title_error", "Error"), str(e))
        
        browse_btn = ttk.Button(f, text="...", width=4, command=_browse)
        browse_btn.pack(side="right")
        
        return var

    def get_backup_dir(self):
        """获取当前配置的存档备份存放目录"""
        d = self.get_config_value("backup_dir", "")
        if not d or not os.path.exists(d):
            default_dir = os.path.join(os.path.expanduser("~"), ".tyranopatcher", "backups")
            os.makedirs(default_dir, exist_ok=True)
            return default_dir
        return d

    def _init_save_manager_ui(self):
        f = ttk.Frame(self.tab_save, padding=10)
        f.pack(fill="both", expand=True)
        
        top = ttk.Frame(f)
        top.pack(fill="x")
        ttk.Label(top, text=T("lbl_cur_save")).pack(side="left")
        self.var_save_path = tk.StringVar()
        ttk.Entry(top, textvariable=self.var_save_path, state="readonly").pack(side="left", fill="x", expand=True, padx=5)
        ttk.Button(top, text=T("btn_scan"), command=self.scan_saves).pack(side="right")
        
        top_backup = ttk.Frame(f)
        top_backup.pack(fill="x", pady=(5, 0))
        ttk.Label(top_backup, text=T("lbl_backup_dir")).pack(side="left")
        self.var_backup_dir = tk.StringVar(value=self.get_backup_dir())
        ttk.Entry(top_backup, textvariable=self.var_backup_dir, state="readonly").pack(side="left", fill="x", expand=True, padx=5)
        ttk.Button(top_backup, text=T("btn_change_dir"), command=self.change_backup_dir).pack(side="right")

        paned = ttk.PanedWindow(f, orient="horizontal")
        paned.pack(fill="both", expand=True, pady=10)
        
        tree_f = ttk.Frame(paned)
        self.tree = ttk.Treeview(tree_f, columns=("name", "type"), show="headings", selectmode="browse")
        self.tree.heading("name", text=T("col_name"))
        self.tree.heading("type", text=T("col_type"))
        self.tree.column("name", width=350)
        self.tree.column("type", width=80)
        sc = ttk.Scrollbar(tree_f, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=sc.set)
        self.tree.pack(side="left", fill="both", expand=True)
        sc.pack(side="right", fill="y")
        paned.add(tree_f, weight=3)
        
        btn_f = ttk.Frame(paned, padding=10)
        paned.add(btn_f, weight=1)
        
        ttk.Button(btn_f, text=T("btn_backup_now"), command=self.do_backup_save, style="Big.TButton").pack(fill="x", pady=5)
        use_zip = self.get_config_value("use_zip", True)
        self.var_zip = tk.BooleanVar(value=use_zip)
        ttk.Checkbutton(btn_f, text=T("chk_zip"), variable=self.var_zip, command=self.save_config).pack(fill="x", pady=5)
        
        ttk.Separator(btn_f, orient="horizontal").pack(fill="x", pady=15)
        ttk.Button(btn_f, text=T("btn_restore"), command=self.do_restore_save).pack(fill="x", pady=5)
        ttk.Button(btn_f, text=T("btn_delete"), command=self.do_delete_backup).pack(fill="x", pady=5)
        
        self.backup_paths = {}
        self.after(500, self.scan_saves)

    def change_backup_dir(self):
        new_dir = filedialog.askdirectory(
            title=T("title_select_dir"),
            initialdir=self.get_backup_dir()
        )
        if new_dir:
            old_dir = self.get_backup_dir()
            if os.path.abspath(new_dir) == os.path.abspath(old_dir):
                return
            
            # 记录新目录
            self.var_backup_dir.set(new_dir)
            self.save_config()
            
            # 是否需要迁移旧备份？
            if messagebox.askyesno(
                T("title_confirm"),
                T("msg_migrate_confirm")
            ):
                self.is_operating = True
                self.toggle_progress(True)
                
                def _migrate_worker():
                    try:
                        self.save_controller.set_log_callback(self.log)
                        migrated_count, failed_count = self.save_controller.migrate_backups(
                            old_dir, new_dir
                        )
                        msg = T("msg_migrate_success").format(migrated=migrated_count)
                        if failed_count > 0:
                            msg += T("msg_migrate_failed").format(failed=failed_count)
                        self.after(0, lambda success_msg=msg: messagebox.showinfo(T("title_success"), success_msg))
                        self.after(0, self.scan_saves)
                    except Exception as e:
                        logger.error(f"Migration error: {e}")
                        self.after(0, lambda e_str=str(e): messagebox.showerror(T("title_error"), T("msg_migrate_error").format(error=e_str)))
                    finally:
                        self.after(0, lambda: setattr(self, 'is_operating', False))
                        self.after(0, lambda: self.toggle_progress(False))
                
                # 启动异步线程
                self.async_manager.submit("migrate_backup_op", _migrate_worker)
            else:
                self.scan_saves()

    def scan_saves(self):
        candidates = ["_storage", "save", "SaveData", "UserData"]
        found = None
        for c in candidates:
            p = os.path.abspath(c)
            if os.path.exists(p) and os.path.isdir(p):
                found = p
                break

        for i in self.tree.get_children():
            self.tree.delete(i)
        self.backup_paths.clear()
        
        if found:
            self.var_save_path.set(found)
            self.current_save_dir = found
            
            root = os.path.dirname(found)
            backup_dir = self.get_backup_dir()
            
            # 同时扫描原游戏目录和自定义备份目录
            dirs_to_scan = {root, backup_dir}
            backups = []
            
            try:
                for d_path in dirs_to_scan:
                    if not os.path.exists(d_path):
                        continue
                    for d in os.listdir(d_path):
                        fp = os.path.join(d_path, d)
                        if os.path.isdir(fp) and d.startswith("Backup_"):
                            self._add_to_list(backups, d, fp, is_zip=False)
                        elif os.path.isfile(fp) and d.startswith("Backup_") and d.endswith(".zip"):
                            self._add_to_list(backups, d, fp, is_zip=True)
            except Exception as scan_err:
                logger.debug(f"Error scanning save directory: {scan_err}")
            
            # 按时间倒序排序 (这里可能会有重名的显示名，但fp不同，因此在字典中是安全的)
            # 不过字典备份是用 iid 存储的，所以没问题
            # 去重：不同目录下可能有两个名称完全相同的 Backup，我们以最新找到的优先
            unique_backups = {}
            for name, fp, is_zip in backups:
                if name not in unique_backups:
                    unique_backups[name] = (name, fp, is_zip)
            
            for dn, fp, is_zip in sorted(unique_backups.values(), reverse=True):
                iid = f"bk_{len(self.backup_paths)}"
                type_tag = "[ZIP]" if is_zip else "[DIR]"
                self.tree.insert("", tk.END, iid=iid, values=(dn, type_tag))
                self.backup_paths[iid] = fp
        else:
            self.var_save_path.set(T("err_no_save"))
            self.current_save_dir = None

    def _add_to_list(self, list_ref, filename, fullpath, is_zip):
        try:
            name_part = filename.replace(".zip", "")
            ts = name_part[len("Backup_"):]
            if len(ts) >= 14:
                if len(ts) == 14:
                    display_name = f"{ts[:4]}-{ts[4:6]}-{ts[6:8]} {ts[8:10]}:{ts[10:12]}:{ts[12:14]}"
                else:
                    display_name = name_part
            else:
                display_name = name_part
            list_ref.append((display_name, fullpath, is_zip))
        except Exception as parse_err:
            logger.debug(f"Error parsing backup name \'{filename}\': {parse_err}")
            list_ref.append((filename, fullpath, is_zip))


    def do_backup_save(self):
        if self.is_operating:
            return messagebox.showwarning(T("title_warning"), T("warn_operation_in_progress", "Operation in progress..."))
        if not self.current_save_dir:
            return messagebox.showerror(T("title_error"), T("err_no_save"))

        if not os.path.exists(self.current_save_dir):
            return messagebox.showerror(T("title_error"), T("err_save_dir_not_exist", "Save directory does not exist"))

        parent = self.get_backup_dir()
        use_zip = self.var_zip.get()
        save_dir = self.current_save_dir

        self.performance_monitor.start("backup_save")
        self.is_operating = True
        self.toggle_progress(True)
        def _worker():
            try:
                self.save_controller.set_log_callback(self.log)
                self.save_controller.execute_backup(save_dir, parent, use_zip)
                self.after(0, self.scan_saves)
                self.after(0, lambda msg=T("msg_backup_ok"): messagebox.showinfo(T("title_success"), msg))
            except Exception as e:
                self.log(f"Backup error: {e}")
                self.after(0, lambda e_str=str(e): messagebox.showerror(T("title_error"), e_str))
            finally:
                elapsed = self.performance_monitor.stop("backup_save")
                logger.info(f"Backup operation took {elapsed:.3f}s")
                self.after(0, lambda: setattr(self, 'is_operating', False))
                self.after(0, lambda: self.toggle_progress(False))
                
        self.async_manager.submit("backup_save_op", _worker)

    def do_restore_save(self):
        if self.is_operating:
            return messagebox.showwarning(T("title_warning"), T("warn_operation_in_progress", "Operation in progress..."))
        sel = self.tree.selection()
        if not sel:
            return messagebox.showwarning(T("title_warning"), T("no_backup_selected"))
        src = self.backup_paths[sel[0]]

        if not os.path.exists(src):
            return messagebox.showerror(T("title_error"), T("err_backup_not_exist", "Backup file/folder does not exist"))

        if messagebox.askyesno(T("title_confirm"), T("msg_restore_confirm")):
            self.performance_monitor.start("restore_save")
            self.is_operating = True
            self.toggle_progress(True)
            save_dir = self.current_save_dir
            def _w():
                try:
                    self.save_controller.set_log_callback(self.log)
                    success, error_msg = self.save_controller.execute_restore(save_dir, src)
                    self.after(0, lambda msg=T("msg_restored"): messagebox.showinfo(T("title_success"), msg))
                    self.after(0, self.scan_saves)
                except Exception as e:
                    logger.error(f"Restore error: {e}")
                    self.after(0, lambda e_str=str(e): messagebox.showerror(T("title_error"), e_str))
                finally:
                    elapsed = self.performance_monitor.stop("restore_save")
                    logger.info(f"Restore operation took {elapsed:.3f}s")
                    self.after(0, lambda: setattr(self, 'is_operating', False))
                    self.after(0, lambda: self.toggle_progress(False))
            
            self.async_manager.submit("restore_save_op", _w)

    def do_delete_backup(self):
        if self.is_operating:
            return messagebox.showwarning(T("title_warning"), T("warn_operation_in_progress", "Operation in progress..."))
        sel = self.tree.selection()
        if not sel:
            return messagebox.showwarning(T("title_warning"), T("no_backup_selected"))
        src = self.backup_paths[sel[0]]

        if not messagebox.askyesno(T("title_confirm"), T("msg_delete_confirm")):
            return
            
        self.performance_monitor.start("delete_backup")
        self.is_operating = True
        def _w():
            try:
                self.save_controller.set_log_callback(self.log)
                success = self.save_controller.execute_delete(src)
                if success:
                    self.after(0, self.scan_saves)
                else:
                    self.after(0, lambda: messagebox.showerror(T("title_error", "Error"), T("err_delete_failed", "Failed to delete. Check logs.")))
            except Exception as e:
                self.after(0, lambda e_str=str(e): messagebox.showerror(T("title_error"), e_str))
            finally:
                elapsed = self.performance_monitor.stop("delete_backup")
                logger.info(f"Delete backup operation took {elapsed:.3f}s")
                self.after(0, lambda: setattr(self, 'is_operating', False))
                self.after(0, lambda: self.toggle_progress(False))
                
        self.async_manager.submit("delete_backup_op", _w)

    def _init_tools_ui(self):
        f = ttk.Frame(self.tab_tools, padding=10)
        f.pack(fill="both", expand=True)
        
        lf = ttk.LabelFrame(f, text=T("grp_asar"), padding=10)
        lf.pack(fill="x", pady=5)
        
        self.var_ext_src = self._file_entry(lf, T("lbl_src_asar"), False, ("Asar", "*.asar"))
        box_ext = ttk.Frame(lf)
        box_ext.pack(fill="x", pady=2)
        ttk.Button(box_ext, text=T("btn_auto_scan"), command=self._auto_scan_asar).pack(side="left")
        ttk.Button(box_ext, text=T("btn_extract"), command=self._tool_extract).pack(side="right")

        ttk.Separator(lf, orient="horizontal").pack(fill="x", pady=10)
        
        self.var_pack_src = self._file_entry(lf, T("lbl_src_folder"), True)
        box_pack = ttk.Frame(lf)
        box_pack.pack(fill="x", pady=2)
        
        f_plat = ttk.Frame(box_pack)
        f_plat.pack(side="left")
        ttk.Label(f_plat, text=T("lbl_platform")).pack(side="left", padx=(0,5))
        saved_plat = self.get_config_value("platform", "win")
        self.var_plat = tk.StringVar(value=saved_plat)
        ttk.Radiobutton(f_plat, text=T("rad_win"), variable=self.var_plat, value="win", command=self.save_config).pack(side="left")
        ttk.Radiobutton(f_plat, text=T("rad_mac_linux"), variable=self.var_plat, value="nix", command=self.save_config).pack(side="left", padx=5)
        
        ttk.Button(box_pack, text=T("btn_pack"), command=self._tool_pack).pack(side="right")
        ttk.Button(box_pack, text=T("btn_sync_path"), command=self._sync_extracted_path).pack(side="right", padx=5)

        lf2 = ttk.LabelFrame(f, text=T("grp_fix"), padding=10)
        lf2.pack(fill="x", pady=10)
        self.var_exe = self._file_entry(lf2, T("lbl_game_exe"), False, ("EXE", "*.exe"))
        
        box_fuse = ttk.Frame(lf2)
        box_fuse.pack(fill="x")
        ttk.Button(box_fuse, text=T("btn_locate"), command=self._auto_scan_exe).pack(side="left")
        ttk.Button(box_fuse, text=T("btn_fuse_setting", "修改Fuse偏移"), command=self._edit_fuse_offset).pack(side="left", padx=10)
        ttk.Button(box_fuse, text=T("btn_fuse"), command=self._tool_fuse).pack(side="right")

        lf3 = ttk.LabelFrame(f, text=T("grp_config"), padding=10)
        lf3.pack(fill="x", pady=10)
        
        if sys.platform.startswith("win"):
            box_debug = ttk.Frame(lf3)
            box_debug.pack(fill="x", pady=(0, 10))
            show_console = self.get_config_value("show_console", False)
            self.var_console = tk.BooleanVar(value=show_console)
            ttk.Checkbutton(box_debug, text=T("chk_show_console"), variable=self.var_console, command=self.save_config).pack(side="left")
        
        box_config = ttk.Frame(lf3)
        box_config.pack(fill="x")
        ttk.Button(box_config, text=T("btn_validate_config"), command=self._validate_config).pack(side="left")
        ttk.Button(box_config, text=T("btn_reset_config"), command=self._reset_config).pack(side="right")

    def _validate_config(self):
        """验证配置合法性"""
        config = get_config()
        valid, messages = config.validate_config()
        if valid:
            if not messages:
                messagebox.showinfo(T("title_success"), T("msg_config_valid"))
                self.log("Configuration validation passed with no warnings.")
            else:
                msg = T("msg_config_warnings").format(warnings="\n".join(messages))
                messagebox.showinfo(T("title_warning"), msg)
                self.log("Configuration is valid but has warnings.")
        else:
            msg = T("msg_config_invalid").format(errors="\n".join(messages))
            messagebox.showerror(T("title_error"), msg)
            self.log("Configuration validation failed!")

    def _reset_config(self):
        """还原默认配置"""
        from utils.paths import get_resource_path
        import shutil
        
        if not messagebox.askyesno(T("title_confirm"), T("msg_reset_confirm")):
            return
            
        default_config_path = get_resource_path("config.ini")
        config = get_config()
        user_config_path = config.config_file
        
        try:
            if os.path.exists(default_config_path):
                shutil.copy2(default_config_path, user_config_path)
                config.reload()
                messagebox.showinfo(T("title_success"), T("msg_reset_success"))
                self.log("Configuration reset to default successfully.")
            else:
                messagebox.showerror(T("title_error"), T("msg_reset_not_found"))
        except Exception as e:
            logger.error(f"Reset config error: {e}")
            messagebox.showerror(T("title_error"), T("msg_reset_error").format(error=e))

    def _auto_scan_asar(self):
        cands = [get_config().resource_dir + "/app.asar", "app.asar"]
        for c in cands:
            p = os.path.abspath(c)
            if os.path.exists(p):
                self.var_ext_src.set(p)
                self.log(f"Found: {p}")
                return
        self.log("app.asar not found in default locations.")
        messagebox.showinfo(T("title_warning"), T("warn_no_file", "未找到文件"))

    def _auto_scan_exe(self):
        exe_name = get_config().auto_target_exe
        p = os.path.abspath(exe_name)
        if os.path.exists(p):
            self.var_exe.set(p)
            self.log(f"Found: {p}")
        else:
            self.log(f"{exe_name} not found.")
            messagebox.showinfo(T("title_warning"), T("warn_exe_not_found").format(exe_name=exe_name))

    def _tool_extract(self):
        if self.is_operating:
            return messagebox.showwarning(T("title_warning"), T("warn_operation_in_progress", "Operation in progress..."))
        src = self.var_ext_src.get()
        if not src or not os.path.exists(src):
            return messagebox.showwarning(T("title_warning"), T("warn_no_file"))

        fname = os.path.basename(src)
        out_dir = os.path.join(os.getcwd(), "_Unpacked", f"{fname}_extracted")
        self.last_extracted_path = out_dir

        if os.path.exists(out_dir):
            try:
                shutil.rmtree(out_dir, onerror=self.core.remove_readonly)
            except Exception as e:
                logger.debug(f"Failed to remove existing output directory {out_dir}: {e}")

        # 使用性能监控器记录ASAR解包操作
        self.performance_monitor.start("gui_extract_asar")
        
        self.is_operating = True
        self.toggle_progress(True)
        def _t():
            try:
                self.core.run_asar("extract", src, out_dir, callback=self.log)
                self.after(0, lambda extracted_path=out_dir: messagebox.showinfo(T("title_success"), f"{T('op_success')}\nPath: {extracted_path}"))
                self.after(0, self._sync_extracted_path)
                if sys.platform.startswith("win"):
                    os.startfile(out_dir)
                elif sys.platform == "darwin":
                    subprocess.run(["open", out_dir], encoding='utf-8')
                else:
                    subprocess.run(["xdg-open", out_dir], encoding='utf-8')
            except Exception as e:
                self.after(0, lambda e_str=str(e): messagebox.showerror(T("title_error"), e_str))
            finally:
                # 记录ASAR解包操作耗时
                elapsed = self.performance_monitor.stop("gui_extract_asar")
                logger.info(f"GUI ASAR extraction took {elapsed:.3f}s")
                self.after(0, lambda: setattr(self, 'is_operating', False))
                self.after(0, lambda: self.toggle_progress(False))
                
        self.async_manager.submit("gui_extract_asar_op", _t)

    def _sync_extracted_path(self):
        if self.last_extracted_path and os.path.exists(self.last_extracted_path):
            self.var_pack_src.set(self.last_extracted_path)
            self.log(f"Synced path: {self.last_extracted_path}")
        else:
            root = os.path.join(os.getcwd(), "_Unpacked")
            if os.path.exists(root):
                dirs = [os.path.join(root, d) for d in os.listdir(root) if os.path.isdir(os.path.join(root, d))]
                if dirs:
                    latest = max(dirs, key=os.path.getmtime)
                    self.var_pack_src.set(latest)
                    self.log(f"Synced latest path: {latest}")
                    return
            messagebox.showwarning(T("title_warning"), T("warn_no_extracted"))

    def _tool_pack(self):
        if self.is_operating:
            return messagebox.showwarning(T("title_warning"), T("warn_operation_in_progress", "Operation in progress..."))
        src = self.var_pack_src.get()
        
        # 路径验证
        if not src:
            return messagebox.showwarning(T("title_warning"), T("warn_no_file"))
        
        if not os.path.exists(src):
            return messagebox.showerror(T("title_error"), T("err_path_not_exist", f"Path does not exist: {src}"))
        
        if not os.path.isdir(src):
            return messagebox.showwarning(T("title_warning"), T("warn_not_dir"))
        
        # 检查是否是asar解包目录
        src_basename = os.path.basename(os.path.normpath(src))
        if src_basename.endswith(".unpacked") or src_basename == "app.asar.unpacked":
            return messagebox.showwarning(T("title_warning"), T("warn_asar_unpacked"))
        
        # 检查目录是否为空
        try:
            if not os.listdir(src):
                return messagebox.showerror(T("title_error"), T("warn_empty_dir"))
        except PermissionError as e:
            logger.error(f"Permission denied when accessing directory {src}: {e}")
            return messagebox.showerror(T("title_error"), T("err_permission_denied", f"Permission denied: {src}"))
        except Exception as e:
            logger.error(f"Error accessing directory {src}: {e}")
            return messagebox.showerror(T("title_error"), T("err_cannot_access", f"Cannot access directory: {src}"))
        
        # 验证目录结构（检查是否包含必要的asar文件）
        REQUIRED_FILES = ['package.json', 'index.html']
        missing_files = [f for f in REQUIRED_FILES if not os.path.exists(os.path.join(src, f))]
        if missing_files:
            logger.warning(f"Missing required files in source directory: {missing_files}")
            msg = T("warn_missing_files", f"Warning: Missing expected files: {', '.join(missing_files)}\n\nThis may not be a valid asar source directory.\n\nContinue anyway?")
            if not messagebox.askyesno(
                T("title_warning"),
                msg
            ):
                return

        base_name = os.path.basename(src).replace("_extracted", "")
        if base_name.endswith(".asar"):
            base_name = base_name[:-5]
        if base_name.endswith(".new"):
            base_name = base_name[:-4]
        out_name = f"{base_name}.asar"

        out_path = os.path.join(os.getcwd(), "_Packed", out_name)
        os.makedirs(os.path.dirname(out_path), exist_ok=True)

        # 平台特定的排除模式
        PLATFORM_PATTERNS = {
            "win": "*.{node,dll,exe}",
            "nix": "*.{node,dll,so,dylib,bin}"
        }
        pat = PLATFORM_PATTERNS.get(self.var_plat.get(), "*.{node,dll,exe}")

        if os.path.exists(out_path):
            if not messagebox.askyesno(T("title_confirm"), T("confirm_overwrite")):
                return
            try:
                os.remove(out_path)
            except Exception as e:
                logger.debug(f"Failed to remove existing output file {out_path}: {e}")

        # 使用性能监控器记录ASAR打包操作
        self.performance_monitor.start("gui_pack_asar")
        
        self.is_operating = True
        self.toggle_progress(True)
        def _t():
            try:
                self.core.run_asar("pack", src, out_path, callback=self.log, unpack_pattern=pat)
                self.after(0, lambda packed_path=out_path: messagebox.showinfo(T("title_success"), f"{T('op_success')}\nPath: {packed_path}"))
            except Exception as e:
                self.after(0, lambda e_str=str(e): messagebox.showerror(T("title_error"), e_str))
            finally:
                # 记录ASAR打包操作耗时
                elapsed = self.performance_monitor.stop("gui_pack_asar")
                logger.info(f"GUI ASAR packing took {elapsed:.3f}s")
                self.after(0, lambda: setattr(self, 'is_operating', False))
                self.after(0, lambda: self.toggle_progress(False))
                
        self.async_manager.submit("gui_pack_asar_op", _t)

    def _edit_fuse_offset(self):
        """打开修改Fuse偏移值配置的对话框"""
        from tkinter import simpledialog
        from configparser import ConfigParser
        
        current_offset = get_config().fuse_asar_integrity_offset
        title = T("title_fuse_setting")
        prompt = T("msg_fuse_setting")
                  
        new_offset = simpledialog.askinteger(title, prompt, initialvalue=current_offset, parent=self)
        
        if new_offset is not None:
            try:
                config_file = get_config().config_file
                parser = ConfigParser()
                parser.read(config_file, encoding="utf-8")
                
                if not parser.has_section("main"):
                    parser.add_section("main")
                parser.set("main", "FUSE_ASAR_INTEGRITY_OFFSET", str(new_offset))
                
                with open(config_file, "w", encoding="utf-8") as f:
                    parser.write(f)
                    
                get_config().reload()
                
                success_msg = T("msg_fuse_saved").format(offset=new_offset)
                messagebox.showinfo(T("title_success"), success_msg)
                self.log(f"Fuse offset updated to {new_offset}")
            except Exception as e:
                err_msg = f"{T('err_fuse_save')} {e}"
                messagebox.showerror(T("title_error"), err_msg)
                logger.error(f"Failed to update fuse offset: {e}")

    def _tool_fuse(self):
        """Fuse移除工具 - 仅供开发者使用，需联网确认偏移值是否正确"""
        if self.is_operating:
            return messagebox.showwarning(T("title_warning"), T("warn_operation_in_progress", "Operation in progress..."))
            
        t = self.var_exe.get()
        if not t:
            return messagebox.showwarning(T("title_warning"), T("warn_no_file", "请选择文件"))
            
        if not os.path.exists(t):
            return messagebox.showerror(T("title_error"), T("err_path_not_exist", "路径不存在"))

        # 添加开发者工具警告确认
        current_offset = get_config().fuse_asar_integrity_offset
        warn_msg = T("msg_fuse_warn").format(offset=current_offset)
        
        if not messagebox.askyesno(
            T("title_warning"),
            warn_msg
        ):
            return
            
        result = self.core.remove_fuse(t, callback=self.log)
        if result:
            messagebox.showinfo(T("title_success"), T("op_success"))
        else:
            messagebox.showinfo(T("title_warning"), T("msg_fuse_disabled_or_not_found"))

    def _init_patch_ui(self):
        f = ttk.Frame(self.tab_patch, padding=20)
        f.pack(fill="both", expand=True)
        ttk.Label(f, text=T("lbl_patch_info"), font=get_font(11)).pack(pady=20)

        self.btn_p = ttk.Button(f, text=T("btn_start_patch"), style="Big.TButton", command=self.run_auto_patch)
        self.btn_p.pack(pady=10, ipady=10, fill="x", padx=50)
        ttk.Button(f, text=T("btn_to_tools"), command=lambda: self.notebook.select(self.tab_tools)).pack(pady=10)


    def _run_auto_patch_worker(self):
        self.performance_monitor.start("auto_patch")
        temp = None
        try:
            success, temp, error_msg = self.patch_controller.run_auto_patch(gui_app=self)
            if success:
                self.after(0, lambda msg=T("patch_done_done"): messagebox.showinfo(T("title_success"), msg))
                
                # 先清理临时目录，再询问退出
                if temp and os.path.exists(temp):
                    from utils.cleanup import force_cleanup_dir
                    force_cleanup_dir(temp)
                
                def on_exit_confirm():
                    if messagebox.askyesno(T("title_confirm"), T("msg_exit_after_patch")):
                        if temp and os.path.exists(temp):
                            from utils.cleanup import force_cleanup_dir
                            force_cleanup_dir(temp)
                        self.destroy()
                self.after(0, on_exit_confirm)
        except Exception as e:
            base = os.path.abspath(".")
            res = os.path.join(base, get_config().resource_dir)
            asar = os.path.join(res, "app.asar")
            bak = asar + ".bak"
            self.patch_controller.handle_error(base, asar, bak, e)
            self.after(0, lambda e_str=str(e): messagebox.showerror(T("title_error"), e_str))
        finally:
            if temp and os.path.exists(temp):
                try:
                    from utils.cleanup import force_cleanup_dir
                    force_cleanup_dir(temp)
                except Exception:
                    pass
            
            if hasattr(self, 'btn_p') and self.btn_p:
                def _enable_btn():
                    if hasattr(self, 'btn_p') and self.btn_p:
                        try:
                            self.btn_p.state(["!disabled"])
                        except tk.TclError:
                            pass
                self.after(0, _enable_btn)
            elapsed = self.performance_monitor.stop("auto_patch")
            logger.info(f"Auto patch operation took {elapsed:.3f}s")
            self.after(0, lambda: setattr(self, 'is_operating', False))
            self.after(0, lambda: self.toggle_progress(False))

    def run_auto_patch(self):
        if self.is_operating:
            return messagebox.showwarning(T("title_warning"), T("warn_operation_in_progress", "Operation in progress..."))
        self.is_operating = True
        self.btn_p.state(["disabled"])
        self.toggle_progress(True)
        self.async_manager.submit("auto_patch_op", self._run_auto_patch_worker)
