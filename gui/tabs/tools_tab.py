# -*- coding: utf-8 -*-

import os
import sys
import shutil
import subprocess
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import logging
from core.config import get_config
from core.fuse import remove_fuse
from utils.language import T
from utils.constants import (
    UNPACKED_DIR_NAME,
    PACKED_DIR_NAME,
    EXTRACTED_SUFFIX,
    ASAR_EXTENSION,
)

logger = logging.getLogger(__name__)


class ToolsTab(ttk.Frame):
    _PLATFORM_PATTERNS: dict = {
        "win": "*.{node,dll,exe}",
        "nix": "*.{node,dll,so,dylib,bin}",
    }

    def __init__(self, parent, app):
        super().__init__(parent, padding=10)
        self.app = app
        self._init_ui()

    def _file_entry(self, parent, label, is_dir=False, ext=None):
        f = ttk.Frame(parent)
        f.pack(fill="x", pady=5)

        label_widget = ttk.Label(f, text=label, width=18)
        label_widget.pack(side="left")

        var = tk.StringVar()
        entry = ttk.Entry(f, textvariable=var, width=50)
        entry.pack(side="left", fill="x", expand=True, padx=5)

        def _browse():
            try:
                if is_dir:
                    p = filedialog.askdirectory(
                        title=T("title_select_directory"), initialdir=os.getcwd()
                    )
                else:
                    types = [(T("file_type_all"), "*.*")]
                    if ext:
                        if not isinstance(ext, (list, tuple)):
                            ext_tuple = (ext,)
                        else:
                            ext_tuple = ext

                        display_name = ext_tuple[0]
                        if "asar" in str(ext_tuple).lower():
                            display_name = T("file_type_asar")
                        elif "exe" in str(ext_tuple).lower():
                            display_name = T("file_type_exe")

                        types.insert(
                            0,
                            (
                                display_name,
                                ext_tuple[1]
                                if len(ext_tuple) > 1
                                else (ext_tuple[0] if len(ext_tuple) > 0 else "*.*"),
                            ),
                        )

                    p = filedialog.askopenfilename(
                        title=T("title_select_file"),
                        filetypes=types,
                        initialdir=os.getcwd(),
                    )

                if p:
                    var.set(os.path.abspath(p))
            except Exception as e:
                logger.error(f"File browser error: {e}")
                messagebox.showerror(T("title_error", "Error"), str(e))

        browse_btn = ttk.Button(f, text="...", width=4, command=_browse)
        browse_btn.pack(side="right")

        return var

    def _init_ui(self):
        lf = ttk.LabelFrame(self, text=T("grp_asar"), padding=10)
        lf.pack(fill="x", pady=5)

        self.app.var_ext_src = self._file_entry(
            lf, T("lbl_src_asar"), False, ("Asar", "*.asar")
        )
        box_ext = ttk.Frame(lf)
        box_ext.pack(fill="x", pady=2)
        ttk.Button(box_ext, text=T("btn_auto_scan"), command=self._auto_scan_asar).pack(
            side="left"
        )
        ttk.Button(box_ext, text=T("btn_extract"), command=self._tool_extract).pack(
            side="right"
        )

        ttk.Separator(lf, orient="horizontal").pack(fill="x", pady=10)

        self.app.var_pack_src = self._file_entry(lf, T("lbl_src_folder"), True)
        box_pack = ttk.Frame(lf)
        box_pack.pack(fill="x", pady=2)

        f_plat = ttk.Frame(box_pack)
        f_plat.pack(side="left")
        ttk.Label(f_plat, text=T("lbl_platform")).pack(side="left", padx=(0, 5))
        saved_plat = self.app.get_config_value("platform", "win")
        self.app.var_plat = tk.StringVar(value=saved_plat)
        ttk.Radiobutton(
            f_plat,
            text=T("rad_win"),
            variable=self.app.var_plat,
            value="win",
            command=self.app.save_config,
        ).pack(side="left")
        ttk.Radiobutton(
            f_plat,
            text=T("rad_mac_linux"),
            variable=self.app.var_plat,
            value="nix",
            command=self.app.save_config,
        ).pack(side="left", padx=5)

        ttk.Button(box_pack, text=T("btn_pack"), command=self._tool_pack).pack(
            side="right"
        )
        ttk.Button(
            box_pack, text=T("btn_sync_path"), command=self._sync_extracted_path
        ).pack(side="right", padx=5)

        lf2 = ttk.LabelFrame(self, text=T("grp_fix"), padding=10)
        lf2.pack(fill="x", pady=10)
        self.app.var_exe = self._file_entry(
            lf2, T("lbl_game_exe"), False, ("EXE", "*.exe")
        )

        box_fuse = ttk.Frame(lf2)
        box_fuse.pack(fill="x")
        ttk.Button(box_fuse, text=T("btn_locate"), command=self._auto_scan_exe).pack(
            side="left"
        )
        ttk.Button(
            box_fuse,
            text=T("btn_fuse_setting", "修改Fuse偏移"),
            command=self._edit_fuse_offset,
        ).pack(side="left", padx=10)
        ttk.Button(box_fuse, text=T("btn_fuse"), command=self._tool_fuse).pack(
            side="right"
        )

        lf3 = ttk.LabelFrame(self, text=T("grp_config"), padding=10)
        lf3.pack(fill="x", pady=10)

        if sys.platform.startswith("win"):
            box_debug = ttk.Frame(lf3)
            box_debug.pack(fill="x", pady=(0, 10))
            show_console = self.app.get_config_value("show_console", False)
            self.app.var_console = tk.BooleanVar(value=show_console)
            ttk.Checkbutton(
                box_debug,
                text=T("chk_show_console"),
                variable=self.app.var_console,
                command=self.app.save_config,
            ).pack(side="left")

        box_config = ttk.Frame(lf3)
        box_config.pack(fill="x")
        ttk.Button(
            box_config, text=T("btn_validate_config"), command=self._validate_config
        ).pack(side="left")
        ttk.Button(
            box_config, text=T("btn_reset_config"), command=self._reset_config
        ).pack(side="right")

    def _validate_config(self):
        config = get_config()
        valid, errors, warnings = config.validate_config()
        if valid:
            if not warnings:
                messagebox.showinfo(T("title_success"), T("msg_config_valid"))
                self.app.log("Configuration validation passed with no warnings.")
            else:
                msg = T("msg_config_warnings").format(warnings="\n".join(warnings))
                messagebox.showinfo(T("title_warning"), msg)
                self.app.log("Configuration is valid but has warnings.")
        else:
            all_messages = errors + (warnings if warnings else [])
            msg = T("msg_config_invalid").format(errors="\n".join(all_messages))
            messagebox.showerror(T("title_error"), msg)
            self.app.log("Configuration validation failed!")

    def _reset_config(self):
        from utils.paths import get_resource_path

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
                self.app.log("Configuration reset to default successfully.")
            else:
                messagebox.showerror(T("title_error"), T("msg_reset_not_found"))
        except Exception as e:
            logger.error(f"Reset config error: {e}")
            messagebox.showerror(T("title_error"), T("msg_reset_error").format(error=e))

    def _auto_scan_asar(self):
        cands = [os.path.join(get_config().resource_dir, "app.asar"), "app.asar"]
        for c in cands:
            p = os.path.abspath(c)
            if os.path.exists(p):
                self.app.var_ext_src.set(p)
                self.app.log(f"Found: {p}")
                return
        self.app.log("app.asar not found in default locations.")
        messagebox.showinfo(T("title_warning"), T("warn_no_file", "未找到文件"))

    def _auto_scan_exe(self):
        exe_name = get_config().auto_target_exe
        p = os.path.abspath(exe_name)
        if os.path.exists(p):
            self.app.var_exe.set(p)
            self.app.log(f"Found: {p}")
        else:
            self.app.log(f"{exe_name} not found.")
            messagebox.showinfo(
                T("title_warning"), T("warn_exe_not_found").format(exe_name=exe_name)
            )

    def _tool_extract(self):
        if self.app.is_operating:
            return messagebox.showwarning(
                T("title_warning"),
                T("warn_operation_in_progress", "Operation in progress..."),
            )
        src = self.app.var_ext_src.get()
        if not src or not os.path.exists(src):
            return messagebox.showwarning(T("title_warning"), T("warn_no_file"))

        fname = os.path.basename(src)
        out_dir = os.path.join(
            os.getcwd(), UNPACKED_DIR_NAME, f"{fname}{EXTRACTED_SUFFIX}"
        )
        self.app.last_extracted_path = out_dir

        if not self.app.core:
            return

        if os.path.exists(out_dir):
            try:
                shutil.rmtree(out_dir, onerror=self.app.core.remove_readonly_handler)
            except Exception as e:
                logger.debug(
                    f"Failed to remove existing output directory {out_dir}: {e}"
                )

        self.app.performance_monitor.start("gui_extract_asar")
        self.app.is_operating = True
        self.app.toggle_progress(True)

        core = self.app.core

        def _t():
            try:
                core.run_asar("extract", src, out_dir, callback=self.app.log)
                self.after(
                    0,
                    lambda extracted_path=out_dir: messagebox.showinfo(
                        T("title_success"), f"{T('op_success')}\nPath: {extracted_path}"
                    ),
                )
                self.after(0, self._sync_extracted_path)
                if os.path.exists(out_dir):
                    try:
                        if sys.platform.startswith("win"):
                            os.startfile(out_dir)
                        elif sys.platform == "darwin":
                            subprocess.run(["open", out_dir], encoding="utf-8")
                        else:
                            subprocess.run(["xdg-open", out_dir], encoding="utf-8")
                    except Exception as open_err:
                        logger.warning(f"Failed to open output directory: {open_err}")
            except Exception as e:
                from utils.error_handler import ErrorHandler

                traceback_str = ErrorHandler.format_traceback(e)
                self.app.log(f"Extract ASAR error: {e}\n{traceback_str}", "error")
                self.after(
                    0,
                    lambda e_str=f"{str(e)}\n\n{traceback_str}": messagebox.showerror(
                        T("title_error"), e_str
                    ),
                )
            finally:
                self.app._finish_operation("gui_extract_asar")

        self.app.async_manager.submit("gui_extract_asar_op", _t)

    def _sync_extracted_path(self):
        if self.app.last_extracted_path and os.path.exists(
            self.app.last_extracted_path
        ):
            self.app.var_pack_src.set(self.app.last_extracted_path)
            self.app.log(f"Synced path: {self.app.last_extracted_path}")
        else:
            root = os.path.join(os.getcwd(), UNPACKED_DIR_NAME)
            if os.path.exists(root):
                dirs = [
                    os.path.join(root, d)
                    for d in os.listdir(root)
                    if os.path.isdir(os.path.join(root, d))
                ]
                if dirs:
                    latest = max(dirs, key=os.path.getmtime)
                    self.app.var_pack_src.set(latest)
                    self.app.log(f"Synced latest path: {latest}")
                    return
            messagebox.showwarning(T("title_warning"), T("warn_no_extracted"))

    def _validate_asar_source_for_packing(self, src: str) -> bool:
        if not src:
            messagebox.showwarning(T("title_warning"), T("warn_no_file"))
            return False

        if not os.path.exists(src):
            messagebox.showerror(
                T("title_error"), T("err_path_not_exist", f"Path does not exist: {src}")
            )
            return False

        if not os.path.isdir(src):
            messagebox.showwarning(T("title_warning"), T("warn_not_dir"))
            return False

        src_basename = os.path.basename(os.path.normpath(src))
        if (
            src_basename.endswith(".unpacked")
            or src_basename == f"app{ASAR_EXTENSION}.unpacked"
        ):
            messagebox.showwarning(T("title_warning"), T("warn_asar_unpacked"))
            return False

        try:
            if not os.listdir(src):
                messagebox.showerror(T("title_error"), T("warn_empty_dir"))
                return False
        except PermissionError as e:
            logger.error(f"Permission denied when accessing directory {src}: {e}")
            messagebox.showerror(
                T("title_error"),
                T("err_permission_denied", f"Permission denied: {src}"),
            )
            return False
        except Exception as e:
            logger.error(f"Error accessing directory {src}: {e}")
            messagebox.showerror(
                T("title_error"),
                T("err_cannot_access", f"Cannot access directory: {src}"),
            )
            return False

        from utils.constants import REQUIRED_ASAR_FILES

        missing_files = [
            f for f in REQUIRED_ASAR_FILES if not os.path.exists(os.path.join(src, f))
        ]
        if missing_files:
            logger.warning(
                f"Missing required files in source directory: {missing_files}"
            )
            msg = T(
                "warn_missing_files",
                f"Warning: Missing expected files: {', '.join(missing_files)}\n\nThis may not be a valid asar source directory.\n\nContinue anyway?",
            )
            if not messagebox.askyesno(T("title_warning"), msg):
                return False

        return True

    def _get_out_path_for_packing(self, src: str) -> str:
        base_name = os.path.basename(src).replace(EXTRACTED_SUFFIX, "")
        if base_name.endswith(ASAR_EXTENSION):
            base_name = base_name[: -len(ASAR_EXTENSION)]
        if base_name.endswith(".new"):
            base_name = base_name[:-4]
        out_name = f"{base_name}{ASAR_EXTENSION}"
        out_path = os.path.join(os.getcwd(), PACKED_DIR_NAME, out_name)
        os.makedirs(os.path.dirname(out_path), exist_ok=True)
        return out_path

    def _tool_pack(self):
        if self.app.is_operating:
            return messagebox.showwarning(
                T("title_warning"),
                T("warn_operation_in_progress", "Operation in progress..."),
            )

        src = self.app.var_pack_src.get()
        if not self._validate_asar_source_for_packing(src):
            return

        out_path = self._get_out_path_for_packing(src)

        pat = self._PLATFORM_PATTERNS.get(
            self.app.var_plat.get() if self.app.var_plat else "win", "*.{node,dll,exe}"
        )

        if os.path.exists(out_path):
            if not messagebox.askyesno(T("title_confirm"), T("confirm_overwrite")):
                return
            try:
                os.remove(out_path)
            except Exception as e:
                logger.debug(f"Failed to remove existing output file {out_path}: {e}")

        self.app.performance_monitor.start("gui_pack_asar")
        self.app.is_operating = True
        self.app.toggle_progress(True)

        if not self.app.core:
            return

        core = self.app.core

        def _t():
            try:
                core.run_asar(
                    "pack", src, out_path, callback=self.app.log, unpack_pattern=pat
                )
                self.after(
                    0,
                    lambda packed_path=out_path: messagebox.showinfo(
                        T("title_success"), f"{T('op_success')}\nPath: {packed_path}"
                    ),
                )
            except Exception as e:
                from utils.error_handler import ErrorHandler

                traceback_str = ErrorHandler.format_traceback(e)
                self.app.log(f"Pack ASAR error: {e}\n{traceback_str}", "error")
                self.after(
                    0,
                    lambda e_str=f"{str(e)}\n\n{traceback_str}": messagebox.showerror(
                        T("title_error"), e_str
                    ),
                )
            finally:
                self.app._finish_operation("gui_pack_asar")

        self.app.async_manager.submit("gui_pack_asar_op", _t)

    def _edit_fuse_offset(self):
        from tkinter import simpledialog

        current_offset = get_config().fuse_asar_integrity_offset
        title = T("title_fuse_setting")
        prompt = T("msg_fuse_setting")

        new_offset = simpledialog.askinteger(
            title, prompt, initialvalue=current_offset, parent=self
        )

        if new_offset is not None:
            try:
                cfg = get_config()
                if not cfg.set_main_config("FUSE_ASAR_INTEGRITY_OFFSET", new_offset):
                    raise OSError("set_main_config() returned False")

                success_msg = T("msg_fuse_saved").format(offset=new_offset)
                messagebox.showinfo(T("title_success"), success_msg)
                self.app.log(f"Fuse offset updated to {new_offset}")
            except Exception as e:
                err_msg = f"{T('err_fuse_save')} {e}"
                messagebox.showerror(T("title_error"), err_msg)
                logger.error(f"Failed to update fuse offset: {e}")

    def _tool_fuse(self):
        if self.app.is_operating:
            return messagebox.showwarning(
                T("title_warning"),
                T("warn_operation_in_progress", "Operation in progress..."),
            )

        t = self.app.var_exe.get()
        if not t:
            return messagebox.showwarning(
                T("title_warning"), T("warn_no_file", "请选择文件")
            )

        if not os.path.exists(t):
            return messagebox.showerror(
                T("title_error"), T("err_path_not_exist", "路径不存在")
            )

        current_offset = get_config().fuse_asar_integrity_offset
        warn_msg = T("msg_fuse_warn").format(offset=current_offset)

        if not messagebox.askyesno(T("title_warning"), warn_msg):
            return

        result = remove_fuse(t, callback=self.app.log)
        if result:
            messagebox.showinfo(T("title_success"), T("op_success"))
        else:
            messagebox.showinfo(T("title_warning"), T("msg_fuse_disabled_or_not_found"))
