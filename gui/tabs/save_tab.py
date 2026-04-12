# -*- coding: utf-8 -*-

import os
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import logging
from utils.language import T

logger = logging.getLogger(__name__)


class SaveTab(ttk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent, padding=10)
        self.app = app
        self._init_ui()

    def _init_ui(self):
        top = ttk.Frame(self)
        top.pack(fill="x")
        ttk.Label(top, text=T("lbl_cur_save")).pack(side="left")
        self.app.var_save_path = tk.StringVar()
        ttk.Entry(top, textvariable=self.app.var_save_path, state="readonly").pack(
            side="left", fill="x", expand=True, padx=5
        )
        ttk.Button(top, text=T("btn_scan"), command=self.scan_saves).pack(side="right")

        top_backup = ttk.Frame(self)
        top_backup.pack(fill="x", pady=(5, 0))
        ttk.Label(top_backup, text=T("lbl_backup_dir")).pack(side="left")
        self.app.var_backup_dir = tk.StringVar(value=self.get_backup_dir())
        ttk.Entry(
            top_backup, textvariable=self.app.var_backup_dir, state="readonly"
        ).pack(side="left", fill="x", expand=True, padx=5)
        ttk.Button(
            top_backup, text=T("btn_change_dir"), command=self.change_backup_dir
        ).pack(side="right")

        paned = ttk.PanedWindow(self, orient="horizontal")
        paned.pack(fill="both", expand=True, pady=10)

        tree_f = ttk.Frame(paned)
        self.tree = ttk.Treeview(
            tree_f, columns=("name", "type"), show="headings", selectmode="browse"
        )
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

        ttk.Button(
            btn_f,
            text=T("btn_backup_now"),
            command=self.do_backup_save,
            style="Big.TButton",
        ).pack(fill="x", pady=5)
        use_zip = self.app.get_config_value("use_zip", True)
        self.app.var_zip = tk.BooleanVar(value=use_zip)
        ttk.Checkbutton(
            btn_f,
            text=T("chk_zip"),
            variable=self.app.var_zip,
            command=self.app.save_config,
        ).pack(fill="x", pady=5)

        ttk.Separator(btn_f, orient="horizontal").pack(fill="x", pady=15)
        ttk.Button(btn_f, text=T("btn_restore"), command=self.do_restore_save).pack(
            fill="x", pady=5
        )
        ttk.Button(btn_f, text=T("btn_delete"), command=self.do_delete_backup).pack(
            fill="x", pady=5
        )

        self.backup_paths = {}
        self.after(500, self.scan_saves)

    def get_backup_dir(self):
        d = self.app.get_config_value("backup_dir", "")
        if not d or not os.path.exists(d):
            default_dir = os.path.join(
                os.path.expanduser("~"), ".tyranopatcher", "backups"
            )
            os.makedirs(default_dir, exist_ok=True)
            return default_dir
        return d

    def change_backup_dir(self):
        new_dir = filedialog.askdirectory(
            title=T("title_select_dir"), initialdir=self.get_backup_dir()
        )
        if new_dir:
            old_dir = self.get_backup_dir()
            if os.path.abspath(new_dir) == os.path.abspath(old_dir):
                return

            self.app.var_backup_dir.set(new_dir)
            self.app.save_config()

            if messagebox.askyesno(T("title_confirm"), T("msg_migrate_confirm")):
                self.app.is_operating = True
                self.app.toggle_progress(True)

                def _migrate_worker():
                    try:
                        self.app.save_controller.set_log_callback(self.app.log)
                        migrated_count, failed_count = (
                            self.app.save_controller.migrate_backups(old_dir, new_dir)
                        )
                        msg = T("msg_migrate_success").format(migrated=migrated_count)
                        if failed_count > 0:
                            msg += T("msg_migrate_failed").format(failed=failed_count)
                        self.after(
                            0,
                            lambda success_msg=msg: messagebox.showinfo(
                                T("title_success"), success_msg
                            ),
                        )
                        self.after(0, self.scan_saves)
                    except Exception as e:
                        logger.error(f"Migration error: {e}")
                        self.after(
                            0,
                            lambda e_str=str(e): messagebox.showerror(
                                T("title_error"),
                                T("msg_migrate_error").format(error=e_str),
                            ),
                        )
                    finally:
                        self.app._finish_operation()

                self.app.async_manager.submit("migrate_backup_op", _migrate_worker)
            else:
                self.scan_saves()

    def scan_saves(self):
        found = self.app.save_controller.scan_save_directory()

        for i in self.tree.get_children():
            self.tree.delete(i)
        self.backup_paths.clear()

        if found:
            self.app.var_save_path.set(found)
            self.app.current_save_dir = found

            root = os.path.dirname(found)
            backup_dir = self.get_backup_dir()

            backups = self.app.save_controller.scan_backups(root, backup_dir)

            for dn, fp, is_zip in backups:
                iid = f"bk_{len(self.backup_paths)}"
                type_tag = "[ZIP]" if is_zip else "[DIR]"
                self.tree.insert("", tk.END, iid=iid, values=(dn, type_tag))
                self.backup_paths[iid] = fp
        else:
            self.app.var_save_path.set(T("err_no_save"))
            self.app.current_save_dir = None

    def do_backup_save(self):
        if self.app.is_operating:
            return messagebox.showwarning(
                T("title_warning"),
                T("warn_operation_in_progress", "Operation in progress..."),
            )
        if not self.app.current_save_dir:
            return messagebox.showerror(T("title_error"), T("err_no_save"))

        if not os.path.exists(self.app.current_save_dir):
            return messagebox.showerror(
                T("title_error"),
                T("err_save_dir_not_exist", "Save directory does not exist"),
            )

        parent = self.get_backup_dir()
        use_zip = self.app.var_zip.get() if self.app.var_zip else True
        save_dir = self.app.current_save_dir

        self.app.performance_monitor.start("backup_save")
        self.app.is_operating = True
        self.app.toggle_progress(True)

        def _worker():
            try:
                self.app.save_controller.set_log_callback(self.app.log)
                success = self.app.save_controller.execute_backup(
                    save_dir, parent, use_zip
                )
                if success:
                    self.after(0, self.scan_saves)
                    self.after(
                        0,
                        lambda msg=T("msg_backup_ok"): messagebox.showinfo(
                            T("title_success"), msg
                        ),
                    )
                else:
                    self.after(
                        0,
                        lambda e_str="Backup failed. Check logs.": messagebox.showerror(
                            T("title_error"), e_str
                        ),
                    )
            except Exception as e:
                from utils.error_handler import ErrorHandler

                traceback_str = ErrorHandler.format_traceback(e)
                self.app.log(f"Backup error: {e}\n{traceback_str}", "error")
                self.after(
                    0,
                    lambda e_str=f"{str(e)}\n\n{traceback_str}": messagebox.showerror(
                        T("title_error"), e_str
                    ),
                )
            finally:
                self.app._finish_operation("backup_save")

        self.app.async_manager.submit("backup_save_op", _worker)

    def do_restore_save(self):
        if self.app.is_operating:
            return messagebox.showwarning(
                T("title_warning"),
                T("warn_operation_in_progress", "Operation in progress..."),
            )

        if not self.app.current_save_dir:
            return messagebox.showerror(T("title_error"), T("err_no_save"))

        save_dir: str = self.app.current_save_dir

        sel = self.tree.selection()
        if not sel:
            return messagebox.showwarning(T("title_warning"), T("no_backup_selected"))
        src = self.backup_paths[sel[0]]

        if not os.path.exists(src):
            return messagebox.showerror(
                T("title_error"),
                T("err_backup_not_exist", "Backup file/folder does not exist"),
            )

        if messagebox.askyesno(T("title_confirm"), T("msg_restore_confirm")):
            self.app.performance_monitor.start("restore_save")
            self.app.is_operating = True
            self.app.toggle_progress(True)

            def _w():
                try:
                    self.app.save_controller.set_log_callback(self.app.log)
                    success, error_msg = self.app.save_controller.execute_restore(
                        save_dir, src
                    )
                    if success:
                        self.after(
                            0,
                            lambda msg=T("msg_restored"): messagebox.showinfo(
                                T("title_success"), msg
                            ),
                        )
                        self.after(0, self.scan_saves)
                    else:
                        self.after(
                            0,
                            lambda e_str=error_msg: messagebox.showerror(
                                T("title_error"), e_str
                            ),
                        )
                except Exception as e:
                    from utils.error_handler import ErrorHandler

                    traceback_str = ErrorHandler.format_traceback(e)
                    logger.error(f"Restore error: {e}\n{traceback_str}")
                    self.after(
                        0,
                        lambda e_str=f"{str(e)}\n\n{traceback_str}": (
                            messagebox.showerror(T("title_error"), e_str)
                        ),
                    )
                finally:
                    self.app._finish_operation("restore_save")

            self.app.async_manager.submit("restore_save_op", _w)

    def do_delete_backup(self):
        if self.app.is_operating:
            return messagebox.showwarning(
                T("title_warning"),
                T("warn_operation_in_progress", "Operation in progress..."),
            )
        sel = self.tree.selection()
        if not sel:
            return messagebox.showwarning(T("title_warning"), T("no_backup_selected"))
        src = self.backup_paths[sel[0]]

        if not messagebox.askyesno(T("title_confirm"), T("msg_delete_confirm")):
            return

        self.app.performance_monitor.start("delete_backup")
        self.app.is_operating = True
        self.app.toggle_progress(True)

        def _w():
            try:
                self.app.save_controller.set_log_callback(self.app.log)
                success = self.app.save_controller.execute_delete(src)
                if success:
                    self.after(0, self.scan_saves)
                else:
                    self.after(
                        0,
                        lambda: messagebox.showerror(
                            T("title_error", "Error"),
                            T("err_delete_failed", "Failed to delete. Check logs."),
                        ),
                    )
            except Exception as e:
                from utils.error_handler import ErrorHandler

                traceback_str = ErrorHandler.format_traceback(e)
                self.app.log(f"Delete backup error: {e}\n{traceback_str}", "error")
                self.after(
                    0,
                    lambda e_str=f"{str(e)}\n\n{traceback_str}": messagebox.showerror(
                        T("title_error"), e_str
                    ),
                )
            finally:
                self.app._finish_operation("delete_backup")

        self.app.async_manager.submit("delete_backup_op", _w)
