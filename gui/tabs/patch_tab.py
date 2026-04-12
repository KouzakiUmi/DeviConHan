
import os
import tkinter as tk
from tkinter import messagebox, ttk

from core.bootstrap import get_detected_game_path
from utils.language import T, get_font
from utils.platform import get_platform_info, get_resources_path, is_app_bundle


class PatchTab(ttk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent, padding=20)
        self.app = app
        self._init_ui()

    def _init_ui(self):
        ttk.Label(self, text=T("lbl_patch_info"), font=get_font(11)).pack(pady=20)

        self.btn_p = ttk.Button(
            self,
            text=T("btn_start_patch"),
            style="Big.TButton",
            command=self.run_auto_patch,
        )
        self.btn_p.pack(pady=10, ipady=10, fill="x", padx=50)
        ttk.Button(
            self,
            text=T("btn_to_tools"),
            command=lambda: self.app.notebook.select(self.app.tab_tools),
        ).pack(pady=10)

    def _run_auto_patch_worker(self, cancel_event=None, _check_cancelled=None):
        self.app.performance_monitor.start("auto_patch")
        temp = None
        try:
            success, temp, error_msg = self.app.patch_controller.run_auto_patch(
                gui_app=self.app, _check_cancelled=_check_cancelled
            )
            if success:
                def on_exit_confirm():
                    if messagebox.askyesno(
                        T("title_success"), T("msg_exit_after_patch")
                    ):
                        self.app.destroy()

                self.after(0, on_exit_confirm)
            else:
                if error_msg and error_msg != "Cancelled or error":
                    self.after(
                        0,
                        lambda msg=error_msg: messagebox.showerror(
                            T("title_error"), msg
                        ),
                    )
        except Exception as e:
            base = get_detected_game_path() or os.path.abspath(".")
            if is_app_bundle(base):
                res = os.path.join(base, "Contents", "Resources")
            else:
                res = get_resources_path(base, get_platform_info().system)
            asar = os.path.join(res, "app.asar")
            bak = asar + ".bak"
            self.app.patch_controller.handle_error(base, asar, bak, e)
            self.after(
                0, lambda e_str=str(e): messagebox.showerror(T("title_error"), e_str)
            )
        finally:
            if temp and os.path.exists(temp):
                try:
                    from utils.cleanup import force_cleanup_dir

                    force_cleanup_dir(temp)
                except Exception:
                    pass

            if hasattr(self, "btn_p") and self.btn_p:

                def _enable_btn():
                    if hasattr(self, "btn_p") and self.btn_p:
                        try:
                            self.btn_p.state(["!disabled"])
                        except tk.TclError:
                            pass

                self.after(0, _enable_btn)
            self.app._finish_operation("auto_patch")

    def run_auto_patch(self):
        if self.app.is_operating:
            return messagebox.showwarning(
                T("title_warning"),
                T("warn_operation_in_progress", "Operation in progress..."),
            )
        self.app.is_operating = True
        self.btn_p.state(["disabled"])
        self.app.toggle_progress(True)
        self.app.async_manager.submit("auto_patch_op", self._run_auto_patch_worker)
