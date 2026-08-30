import os
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from core.bootstrap import get_runtime_game_path
from core.config import get_config
from utils.language import T, get_font
from utils.paths import get_resource_path
from utils.platform import get_platform_info, get_resources_path


class PatchTab(ttk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent, padding=20)
        self.app = app
        self.default_patch_zip = get_resource_path(get_config().patch_zip_name)
        self.var_patch_zip = tk.StringVar(value=self.default_patch_zip)
        self._pending_patch_zip = self.default_patch_zip
        self._init_ui()

    def _init_ui(self):
        ttk.Label(self, text=T("lbl_patch_info"), font=get_font(11)).pack(pady=20)

        source_frame = ttk.LabelFrame(self, text=T("grp_patch_package"), padding=10)
        source_frame.pack(fill="x", padx=30, pady=(0, 10))
        source_frame.columnconfigure(0, weight=1)
        ttk.Entry(
            source_frame,
            textvariable=self.var_patch_zip,
            state="readonly",
        ).grid(row=0, column=0, sticky="ew", padx=(0, 8))
        self.btn_select_patch = ttk.Button(
            source_frame,
            text=T("btn_select_patch"),
            command=self.select_patch_zip,
        )
        self.btn_select_patch.grid(row=0, column=1, padx=(0, 8))
        self.btn_default_patch = ttk.Button(
            source_frame,
            text=T("btn_use_default_patch"),
            command=self.use_default_patch,
        )
        self.btn_default_patch.grid(row=0, column=2)

        self.btn_p = ttk.Button(
            self,
            text=T("btn_start_patch"),
            style="Big.TButton",
            command=self.run_auto_patch,
        )
        self.btn_p.pack(pady=10, ipady=10, fill="x", padx=50)
        self.btn_restore_patch = ttk.Button(
            self,
            text=T("btn_restore_patch"),
            command=self.restore_patch,
        )
        self.btn_restore_patch.pack(pady=5, ipady=6, fill="x", padx=50)
        ttk.Button(
            self,
            text=T("btn_to_tools"),
            command=self._switch_to_tools,
        ).pack(pady=10)

    def _switch_to_tools(self):
        """切换到开发者工具箱标签页"""
        if hasattr(self.app, "tab_tools") and hasattr(self.app, "notebook"):
            self.app.notebook.select(self.app.tab_tools)

    def _run_auto_patch_worker(self, cancel_event=None, _check_cancelled=None):
        self.app.performance_monitor.start("auto_patch")
        temp = None
        try:
            success, temp, error_msg = self.app.patch_controller.run_auto_patch(
                gui_app=self.app,
                patch_zip_path=self._pending_patch_zip,
                _check_cancelled=_check_cancelled,
            )
            if success:
                # 只有当实际进行了补丁安装时才显示退出确认
                if temp is not None:  # temp不为None表示实际进行了补丁操作

                    def on_exit_confirm():
                        if messagebox.askyesno(T("title_success"), T("msg_exit_after_patch")):
                            self.app.destroy()

                    self.after(0, on_exit_confirm)
            else:
                if error_msg and error_msg != "Cancelled or error":
                    self.after(
                        0,
                        lambda msg=error_msg: messagebox.showerror(T("title_error"), msg),
                    )
        except Exception as e:
            base = get_runtime_game_path() or os.path.abspath(".")
            res = get_resources_path(base, get_platform_info().system)
            asar = os.path.join(res, "app.asar")
            bak = asar + ".bak"
            self.app.patch_controller.handle_error(base, asar, bak, e)
            self.after(0, lambda e_str=str(e): messagebox.showerror(T("title_error"), e_str))
        finally:
            if temp and os.path.exists(temp):
                try:
                    from utils.cleanup import force_cleanup_dir

                    force_cleanup_dir(temp)
                except Exception:
                    pass

            self.after(0, lambda: self._set_action_buttons_enabled(True))
            self.app._finish_operation("auto_patch")

    def run_auto_patch(self):
        if self.app.is_operating:
            return messagebox.showwarning(
                T("title_warning"),
                T("warn_operation_in_progress", "Operation in progress..."),
            )
        self.app.is_operating = True
        self._pending_patch_zip = self.var_patch_zip.get().strip() or self.default_patch_zip
        self._set_action_buttons_enabled(False)
        self.app.toggle_progress(True)
        self.app.async_manager.submit("auto_patch_op", self._run_auto_patch_worker)

    def _set_action_buttons_enabled(self, enabled):
        state = ["!disabled"] if enabled else ["disabled"]
        for name in (
            "btn_p",
            "btn_restore_patch",
            "btn_select_patch",
            "btn_default_patch",
        ):
            button = getattr(self, name, None)
            if button:
                try:
                    button.state(state)
                except tk.TclError:
                    pass

    def select_patch_zip(self):
        current = self.var_patch_zip.get().strip()
        initial_dir = (
            os.path.dirname(current) if current else os.path.dirname(self.default_patch_zip)
        )
        selected = filedialog.askopenfilename(
            title=T("title_select_patch"),
            initialdir=initial_dir if os.path.isdir(initial_dir) else None,
            filetypes=[
                (T("file_type_zip"), "*.zip"),
                (T("file_type_all"), "*.*"),
            ],
        )
        if selected:
            self.var_patch_zip.set(os.path.abspath(selected))

    def use_default_patch(self):
        self.var_patch_zip.set(self.default_patch_zip)

    def _restore_patch_worker(self, cancel_event=None, _check_cancelled=None):
        self.app.performance_monitor.start("restore_patch")
        try:
            success, message = self.app.patch_controller.restore_patch()
            if success:
                self.after(
                    0,
                    lambda msg=message: messagebox.showinfo(T("title_success"), msg),
                )
            else:
                self.after(
                    0,
                    lambda msg=message: messagebox.showerror(T("title_error"), msg),
                )
        except Exception as e:
            self.after(0, lambda msg=str(e): messagebox.showerror(T("title_error"), msg))
        finally:
            self.after(0, lambda: self._set_action_buttons_enabled(True))
            self.app._finish_operation("restore_patch")

    def restore_patch(self):
        if self.app.is_operating:
            return messagebox.showwarning(
                T("title_warning"),
                T("warn_operation_in_progress", "Operation in progress..."),
            )
        if not messagebox.askyesno(T("title_confirm"), T("msg_restore_patch_confirm")):
            return None

        self.app.is_operating = True
        self._set_action_buttons_enabled(False)
        self.app.toggle_progress(True)
        self.app.async_manager.submit("restore_patch_op", self._restore_patch_worker)
