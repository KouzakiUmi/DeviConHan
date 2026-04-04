# -*- coding: utf-8 -*-

import os
import sys
import shutil
import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext, ttk
import threading
from configparser import ConfigParser
import datetime
import zipfile
import logging

from core.config import get_config
from core.patcher import (
    CoreLogic, PatcherError, PatcherFileNotFoundError, 
    NodeNotFoundError, AsarCorruptedError, has_embedded_patch, 
    PATCH_INFO_FILE, handle_steam_update, save_patch_info, save_patch_meta
)
from utils.language import init_lang, T
from utils.paths import get_resource_path

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
        except Exception as e:
            logger.error(f"Failed to initialize CoreLogic: {e}")
            messagebox.showerror("Initialization Error", str(e))
            # 安全退出GUI，而不是直接raise导致崩溃
            self.destroy()
            return

        self.log_callback = log_callback  # 允许外部设置日志回调
        self.app_config = None
        # 使用 APPDATA 目录存储配置文件 (Windows) 或 ~/.config (Mac/Linux)
        if sys.platform.startswith("win"):
            config_dir = os.environ.get("APPDATA", os.path.expanduser("~"))
        else:
            config_dir = os.environ.get("XDG_CONFIG_HOME", os.path.expanduser("~/.config"))
        self.config_file = os.path.join(config_dir, "tyrano_patcher.ini")
        
        self.load_config()        
        self.init_ui()

    def init_ui(self):
        for widget in self.winfo_children(): widget.destroy()

        self.title(T("app_title"))
        self.geometry("800x620")
        
        menubar = tk.Menu(self)
        self.config(menu=menubar) 
        lang_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label=T("menu_lang"), menu=lang_menu)
        lang_menu.add_command(label="English", command=lambda: self.change_lang("en"))
        lang_menu.add_command(label="简体中文", command=lambda: self.change_lang("cn"))
        lang_menu.add_command(label="日本語", command=lambda: self.change_lang("jp"))

        style = ttk.Style()
        if sys.platform.startswith("win"): style.theme_use("vista")
        elif sys.platform == "darwin": style.theme_use("clam")
        else: style.theme_use("clam")
        style.configure("Big.TButton", font=("Segoe UI", 11, "bold"), padding=8)
        
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
        self.log_area = scrolledtext.ScrolledText(self.log_frame, height=8, state="disabled", font=("Consolas", 9))
        self.log_area.pack(fill="both", padx=5, pady=5)
        
        self.progress = ttk.Progressbar(self.log_frame, mode="indeterminate")
        self.progress.pack(fill="x", padx=5, pady=(0, 5))

    def load_config(self):
        """
        从配置文件加载用户偏好设置

        Returns:
            bool: 是否成功加载配置
        """
        try:
            self.app_config = ConfigParser()

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

                self.app_config.read_string(content)
                logger.debug(f"Loaded config from: {self.config_file}")
            else:
                logger.info(f"No existing config found at: {self.config_file}")

            return True

        except Exception as e:
            logger.error(f"Failed to load config: {e}")
            self.app_config = ConfigParser()  # 初始化空配置
            return False
    
    def get_config_value(self, key, default=None):
        """
        获取配置值，支持类型转换和默认值
        
        Args:
            key: 配置键名
            default: 默认值
            
        Returns:
            配置值或默认值
        """
        try:
            if not hasattr(self, "app_config") or self.app_config is None:
                return default
                
            if key in ["use_zip"]:
                return self.app_config.getboolean("preferences", key, fallback=bool(default))
            elif key == "platform":
                return self.app_config.get("preferences", key, fallback=str(default) if default else "win")
            elif key == "language":
                return self.app_config.get("preferences", key, fallback=str(default) if default else "en")
            else:
                return self.app_config.get("preferences", key, fallback=str(default) if default else "")
                
        except Exception as e:
            logger.warning(f"Failed to get config value for \"{key}\": {e}")
            return default
    
    def save_config(self):
        """
        保存用户偏好设置到配置文件
        
        Returns:
            bool: 是否成功保存
        """
        try:
            if not hasattr(self, "app_config") or self.app_config is None:
                logger.warning("Config object not initialized")
                return False
            
            if not self.app_config.has_section("preferences"):
                self.app_config.add_section("preferences")
            
            if hasattr(self, "var_plat") and self.var_plat is not None:
                value = self.var_plat.get()
                self.app_config.set("preferences", "platform", str(value))

            if hasattr(self, "var_zip") and self.var_zip is not None:
                value = self.var_zip.get()
                self.app_config.set("preferences", "use_zip", str(value).lower())

            config_dir = os.path.dirname(self.config_file)
            if config_dir and not os.path.exists(config_dir):
                os.makedirs(config_dir, exist_ok=True)
            
            with open(self.config_file, "w", encoding="utf-8") as f:
                self.app_config.write(f)
                
            logger.debug(f"Config saved to: {self.config_file}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to save config: {e}")
            return False

    def change_lang(self, code):
        from utils import language
        language.CURRENT_LANG_CODE = code
        if hasattr(self, "app_config") and self.app_config is not None:
            if not self.app_config.has_section("preferences"):
                self.app_config.add_section("preferences")
            self.app_config.set("preferences", "language", code)
            self.save_config()
        self.init_ui()

    def log(self, msg):
        """
        在GUI中显示日志消息
        
        Args:
            msg: 要显示的消息
        """
        logger.info(msg)
        
        def _update():
            try:
                ts = datetime.datetime.now().strftime("%H:%M:%S")
                self.log_area.config(state="normal")
                self.log_area.insert(tk.END, f"[{ts}] {msg}\n")
                self.log_area.see(tk.END)
                self.log_area.config(state="disabled")
            except tk.TclError:
                pass
        
        try:
            self.after(0, _update)
        except tk.TclError:
            print(f"[{datetime.datetime.now().strftime("%H:%M:%S")}] {msg}")

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
                        title="Select Directory",
                        initialdir=os.getcwd()
                    )
                else:
                    types = [("All Files", "*.*")]
                    if ext:
                        if not isinstance(ext, (list, tuple)):
                            ext_tuple = (ext,)
                        else:
                            ext_tuple = ext
                        types.insert(0, ext_tuple)
                    
                    p = filedialog.askopenfilename(
                        title="Select File",
                        filetypes=types,
                        initialdir=os.getcwd()
                    )
                
                if p:
                    var.set(os.path.abspath(p))
            except Exception as e:
                logger.error(f"File browser error: {e}")
                messagebox.showerror("Error", str(e))
        
        browse_btn = ttk.Button(f, text="...", width=4, command=_browse)
        browse_btn.pack(side="right")
        
        return var

    def _init_save_manager_ui(self):
        f = ttk.Frame(self.tab_save, padding=10)
        f.pack(fill="both", expand=True)
        
        top = ttk.Frame(f)
        top.pack(fill="x")
        ttk.Label(top, text=T("lbl_cur_save")).pack(side="left")
        self.var_save_path = tk.StringVar()
        ttk.Entry(top, textvariable=self.var_save_path, state="readonly").pack(side="left", fill="x", expand=True, padx=5)
        ttk.Button(top, text=T("btn_scan"), command=self.scan_saves).pack(side="right")

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
            backups = []
            try:
                for d in os.listdir(root):
                    fp = os.path.join(root, d)
                    if os.path.isdir(fp) and d.startswith("Backup_"):
                        self._add_to_list(backups, d, fp, is_zip=False)
                    elif os.path.isfile(fp) and d.startswith("Backup_") and d.endswith(".zip"):
                        self._add_to_list(backups, d, fp, is_zip=True)
            except Exception as scan_err:
                logger.debug(f"Error scanning save directory: {scan_err}")
            
            for dn, fp, is_zip in sorted(backups, reverse=True):
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
            return messagebox.showwarning(T("title_warning"), "Operation in progress...")
        if not self.current_save_dir:
            return messagebox.showerror(T("title_error"), T("err_no_save"))

        if not os.path.exists(self.current_save_dir):
            return messagebox.showerror(T("title_error"), "Save directory does not exist")

        ts = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
        parent = os.path.dirname(self.current_save_dir)

        self.is_operating = True
        def _worker():
            try:
                if self.var_zip.get():
                    zip_name = f"{"Backup_"}{ts}.zip"
                    dest_zip = os.path.join(parent, zip_name)
                    with zipfile.ZipFile(dest_zip, "w", zipfile.ZIP_DEFLATED) as zf:
                        base_len = len(self.current_save_dir)
                        for root, dirs, files in os.walk(self.current_save_dir):
                            for file in files:
                                abs_path = os.path.join(root, file)
                                if not os.path.commonpath([self.current_save_dir, abs_path]) == self.current_save_dir:
                                    continue
                                rel_path = abs_path[base_len:].lstrip(os.sep)
                                zf.write(abs_path, rel_path)
                    self.log(f"Backup(ZIP): {zip_name}")
                    logger.info(f"Backup created (ZIP): {dest_zip}")
                else:
                    folder_name = f"{"Backup_"}{ts}"
                    dest_folder = os.path.join(parent, folder_name)
                    shutil.copytree(self.current_save_dir, dest_folder, symlinks=False, ignore=None)
                    self.log(f"Backup(DIR): {folder_name}")
                    logger.info(f"Backup created (DIR): {dest_folder}")

                self.after(0, lambda: [self.scan_saves(), messagebox.showinfo(T("title_success"), T("msg_backup_ok"))])
            except Exception as e:
                self.log(f"Backup error: {e}")
                self.after(0, lambda: messagebox.showerror(T("title_error"), str(e)))
            finally:
                self.is_operating = False
        threading.Thread(target=_worker, daemon=True).start()

    def do_restore_save(self):
        if self.is_operating:
            return messagebox.showwarning(T("title_warning"), "Operation in progress...")
        sel = self.tree.selection()
        if not sel:
            return messagebox.showwarning(T("title_warning"), T("no_backup_selected"))
        src = self.backup_paths[sel[0]]

        if not os.path.exists(src):
            return messagebox.showerror(T("title_error"), "Backup file/folder does not exist")

        if messagebox.askyesno(T("title_confirm"), T("msg_restore_confirm")):
            self.is_operating = True
            def _w():
                temp_dir = None
                backup_success = False
                try:
                    if os.path.exists(self.current_save_dir):
                        import tempfile
                        temp_dir = tempfile.mkdtemp(prefix="save_backup_")
                        shutil.copytree(self.current_save_dir, os.path.join(temp_dir, "current"))
                        backup_success = True
                        logger.info(f"Successfully backed up current save to: {temp_dir}")

                    if os.path.isfile(src) and src.endswith(".zip"):
                        # 清空当前存档目录（如果存在）
                        if os.path.exists(self.current_save_dir):
                            try:
                                shutil.rmtree(self.current_save_dir, onerror=self.core.remove_readonly)
                            except Exception as clear_err:
                                logger.warning(f"Failed to clear save directory: {clear_err}")
                        os.makedirs(self.current_save_dir, exist_ok=True)
                        with zipfile.ZipFile(src, "r") as zf:
                            for member in zf.infolist():
                                # 安全检查：防止 ZIP 遍历攻击
                                file_path = os.path.join(self.current_save_dir, member.filename)
                                abs_save_dir = os.path.abspath(self.current_save_dir)
                                abs_file_path = os.path.abspath(file_path)
                                if not abs_file_path.startswith(abs_save_dir + os.sep):
                                    raise ValueError("Invalid path in ZIP: potential directory traversal")
                            zf.extractall(self.current_save_dir)
                        logger.info(f"Restored save from ZIP: {src}")
                    else:
                        # 清空当前存档目录（如果存在）
                        if os.path.exists(self.current_save_dir):
                            try:
                                shutil.rmtree(self.current_save_dir, onerror=self.core.remove_readonly)
                            except Exception as clear_err:
                                logger.warning(f"Failed to clear save directory: {clear_err}")
                        shutil.copytree(src, self.current_save_dir, dirs_exist_ok=True)
                        logger.info(f"Restored save from folder: {src}")

                    self.after(0, lambda: messagebox.showinfo(T("title_success"), T("msg_restored")))
                    self.after(0, self.scan_saves)
                except Exception as e:
                    logger.error(f"Restore error: {e}")
                    if temp_dir and backup_success and os.path.exists(temp_dir):
                        try:
                            logger.info("Attempting to restore from backup...")
                            shutil.rmtree(self.current_save_dir, onerror=self.core.remove_readonly)
                            shutil.copytree(os.path.join(temp_dir, "current"), self.current_save_dir)
                            logger.info("Successfully restored from backup")
                        except Exception as restore_err:
                            logger.error(f"Failed to restore from backup: {restore_err}")
                            self.after(0, lambda: messagebox.showerror(
                                T("title_error"), 
                                f"{str(e)}\n\nFailed to restore from backup: {str(restore_err)}"
                            ))
                        else:
                            self.after(0, lambda: messagebox.showerror(
                                T("title_error"), 
                                f"{str(e)}\n\nCurrent save has been restored from backup."
                            ))
                    else:
                        self.after(0, lambda: messagebox.showerror(T("title_error"), str(e)))
                finally:
                    if temp_dir and os.path.exists(temp_dir):
                        try:
                            shutil.rmtree(temp_dir)
                        except Exception as cleanup_err:
                            logger.warning(f"Failed to cleanup temp directory: {cleanup_err}")
                    self.is_operating = False
            threading.Thread(target=_w, daemon=True).start()

    def do_delete_backup(self):
        if self.is_operating:
            return messagebox.showwarning(T("title_warning"), "Operation in progress...")
        sel = self.tree.selection()
        if not sel:
            return messagebox.showwarning(T("title_warning"), T("no_backup_selected"))
        src = self.backup_paths[sel[0]]

        if not messagebox.askyesno(T("title_confirm"), T("msg_delete_confirm")):
            return
        self.is_operating = True
        def _w():
            try:
                if os.path.isfile(src):
                    os.remove(src)
                else:
                    shutil.rmtree(src, onerror=self.core.remove_readonly)
                self.after(0, self.scan_saves)
            except Exception as e:
                self.after(0, lambda: messagebox.showerror(T("title_error"), str(e)))
            finally:
                self.is_operating = False
        threading.Thread(target=_w, daemon=True).start()

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
        ttk.Button(box_fuse, text=T("btn_fuse"), command=self._tool_fuse).pack(side="right")

    def _auto_scan_asar(self):
        cands = [get_config().resource_dir + "/app.asar", "app.asar"]
        for c in cands:
            p = os.path.abspath(c)
            if os.path.exists(p):
                self.var_ext_src.set(p)
                self.log(f"Found: {p}")
                return
        self.log("Not found.")

    def _auto_scan_exe(self):
        p = os.path.abspath(get_config().auto_target_exe)
        if os.path.exists(p):
            self.var_exe.set(p)

    def _tool_extract(self):
        if self.is_operating:
            return messagebox.showwarning(T("title_warning"), "Operation in progress...")
        src = self.var_ext_src.get()
        if not src or not os.path.exists(src):
            return messagebox.showwarning(T("title_warning"), T("warn_no_file"))

        fname = os.path.basename(src)
        out_dir = os.path.join(os.getcwd(), "_Unpacked", f"{fname}_extracted")
        self.last_extracted_path = out_dir

        if os.path.exists(out_dir):
            try:
                shutil.rmtree(out_dir, onerror=self.core.remove_readonly)
            except:
                pass

        self.is_operating = True
        self.toggle_progress(True)
        def _t():
            try:
                self.core.run_asar("extract", src, out_dir, callback=self.log)
                messagebox.showinfo(T("title_success"), f"{T("op_success")}\nPath: {out_dir}")
                self._sync_extracted_path()
                if sys.platform.startswith("win"):
                    os.startfile(out_dir)
                elif sys.platform == "darwin":
                    subprocess.run(["open", out_dir])
                else:
                    subprocess.run(["xdg-open", out_dir])
            except Exception as e:
                messagebox.showerror(T("title_error"), str(e))
            finally:
                self.is_operating = False
                self.toggle_progress(False)
        threading.Thread(target=_t, daemon=True).start()

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
            return messagebox.showwarning(T("title_warning"), "Operation in progress...")
        src = self.var_pack_src.get()
        
        # 路径验证
        if not src:
            return messagebox.showwarning(T("title_warning"), T("warn_no_file"))
        
        if not os.path.exists(src):
            return messagebox.showerror(T("title_error"), f"Path does not exist: {src}")
        
        if not os.path.isdir(src):
            return messagebox.showwarning(T("title_warning"), T("warn_not_dir"))
        
        # 检查是否是asar解包目录
        if src.endswith(".unpacked") or "app.asar.unpacked" in src:
            return messagebox.showwarning(T("title_warning"), T("warn_asar_unpacked"))
        
        # 检查目录是否为空
        try:
            if not os.listdir(src):
                return messagebox.showerror(T("title_error"), T("warn_empty_dir"))
        except PermissionError as e:
            logger.error(f"Permission denied when accessing directory {src}: {e}")
            return messagebox.showerror(T("title_error"), f"Permission denied: {src}")
        except Exception as e:
            logger.error(f"Error accessing directory {src}: {e}")
            return messagebox.showerror(T("title_error"), f"Cannot access directory: {src}")
        
        # 验证目录结构（检查是否包含必要的asar文件）
        required_files = ['package.json', 'index.html']
        missing_files = [f for f in required_files if not os.path.exists(os.path.join(src, f))]
        if missing_files:
            logger.warning(f"Missing required files in source directory: {missing_files}")
            if not messagebox.askyesno(
                T("title_warning"),
                f"Warning: Missing expected files: {', '.join(missing_files)}\n\nThis may not be a valid asar source directory.\n\nContinue anyway?"
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

        pat = "*.{node,dll,exe}" if self.var_plat.get() == "win" else "*.{node,dll,so,dylib,bin}"

        if os.path.exists(out_path):
            if not messagebox.askyesno(T("title_confirm"), T("confirm_overwrite")):
                return
            try:
                os.remove(out_path)
            except:
                pass

        self.is_operating = True
        self.toggle_progress(True)
        def _t():
            try:
                self.core.run_asar("pack", src, out_path, callback=self.log, unpack_pattern=pat)
                messagebox.showinfo(T("title_success"), f"{T("op_success")}\nPath: {out_path}")
            except Exception as e:
                messagebox.showerror(T("title_error"), str(e))
            finally:
                self.is_operating = False
                self.toggle_progress(False)
        threading.Thread(target=_t, daemon=True).start()

    def _tool_fuse(self):
        t = self.var_exe.get()
        if t and os.path.exists(t):
            result = self.core.remove_fuse(t, callback=self.log)
            if result:
                messagebox.showinfo(T("title_success"), T("op_success"))
            else:
                messagebox.showinfo(T("title_warning"), "Fuse sentinel not found or already disabled.")

    def _init_patch_ui(self):
        f = ttk.Frame(self.tab_patch, padding=20)
        f.pack(fill="both", expand=True)
        ttk.Label(f, text=T("lbl_patch_info"), font=("Segoe UI", 11)).pack(pady=20)

        self.btn_p = ttk.Button(f, text=T("btn_start_patch"), style="Big.TButton", command=self.run_auto_patch)
        self.btn_p.pack(pady=10, ipady=10, fill="x", padx=50)
        ttk.Button(f, text=T("btn_to_tools"), command=lambda: self.notebook.select(self.tab_tools)).pack(pady=10)

    def _run_auto_patch_worker(self):
        base = res = asar = bak = temp = None
        try:
            base = os.path.abspath(".")
            res = os.path.join(base, get_config().resource_dir)
            asar = os.path.join(res, "app.asar")
            bak = asar + ".bak"
            
            if not os.path.exists(res):
                raise Exception(T("err_res_missing"))

            # 检查 ASAR 文件是否存在，如果不存在但有备份，先恢复备份
            if not os.path.exists(asar) and os.path.exists(bak):
                self.log("app.asar missing, restoring from backup...")
                shutil.copy2(bak, asar)
                self.log("Restored app.asar from backup.")
            
            should_continue, cancel_or_error = handle_steam_update(
                self.core, base, bak, asar,
                log_callback=self.log,
                gui_app=self
            )
            
            if cancel_or_error or not should_continue:
                return

            if not os.path.exists(asar):
                raise Exception(T("err_asar_missing"))

            temp = os.path.join(base, "temp_patch")
            if os.path.exists(temp):
                try:
                    shutil.rmtree(temp, onerror=self.core.remove_readonly)
                except Exception as cleanup_err:
                    logger.warning(f"Failed to cleanup temp directory: {cleanup_err}")

            self.log("Extracting ASAR...")
            self.core.run_asar("extract", asar, temp, callback=self.log)
            
            self.log("Applying patch...")
            patch_dir = get_resource_path("Patch")
            if not os.path.exists(patch_dir):
                raise Exception("Patch directory not found")
            shutil.copytree(patch_dir, temp, dirs_exist_ok=True)
            self.log("Patch files copied.")

            self.log("Packing ASAR...")
            self.core.run_asar("pack", temp, asar, callback=self.log, unpack_pattern="*.{node,dll,exe}")

            self.log("Saving patch information...")
            save_patch_info(base, asar, bak)
            save_patch_meta(base, temp)

            # 清理旧的临时备份文件
            temp_bak = bak + ".old"
            temp_info = os.path.join(base, PATCH_INFO_FILE + ".old")
            for tmp_file in [temp_bak, temp_info]:
                if os.path.exists(tmp_file):
                    try:
                        os.remove(tmp_file)
                        logger.debug(f"Removed old temp file: {tmp_file}")
                    except Exception as e:
                        logger.warning(f"Failed to remove temp backup file {tmp_file}: {e}")

            self.log("Patch applied successfully. (Fuse removal is now manual)")
            self.log(T("patch_done"))
            messagebox.showinfo(T("title_success"), T("patch_done_done"))
            if messagebox.askyesno(T("title_confirm"), T("msg_exit_after_patch")):
                self.destroy()
        except Exception as e:
            self.log(f"Error: {e}")
            logger.error(f"Patch error: {e}")
            
            # 尝试恢复备份
            if bak and os.path.exists(bak):
                try:
                    temp_bak = bak + ".old"
                    temp_info = os.path.join(base, PATCH_INFO_FILE + ".old") if base else None
                    
                    if os.path.exists(temp_bak):
                        self.log("Restoring backup due to error...")
                        if os.path.exists(bak):
                            os.remove(bak)
                        shutil.move(temp_bak, bak)
                    
                    if os.path.exists(asar):
                        os.remove(asar)
                    shutil.copy2(bak, asar)
                    self.log("Restored app.asar from backup.")
                except Exception as be:
                    logger.error(f"Backup restore error: {be}")
                    self.log(f"Failed to restore backup: {be}")

            messagebox.showerror(T("title_error"), str(e))
        finally:
            # 清理临时目录
            if temp and os.path.exists(temp):
                try:
                    shutil.rmtree(temp, onerror=self.core.remove_readonly)
                    logger.info(f"Cleaned up temporary directory: {temp}")
                except Exception as cleanup_err:
                    logger.warning(f"Failed to cleanup temp directory: {cleanup_err}")
            
            self.is_operating = False
            if hasattr(self, 'btn_p') and self.btn_p:
                self.btn_p.state(["!disabled"])
            self.toggle_progress(False)

    def run_auto_patch(self):
        if self.is_operating:
            return messagebox.showwarning(T("title_warning"), "Operation in progress...")
        self.is_operating = True
        self.btn_p.state(["disabled"])
        self.toggle_progress(True)
        threading.Thread(target=self._run_auto_patch_worker, daemon=True).start()
