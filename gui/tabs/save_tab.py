import logging
import os
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from utils.error_handler import ErrorSeverity, PatcherError
from utils.language import T

logger = logging.getLogger(__name__)


class SaveTab(ttk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent, padding=10)
        self.app = app
        self._additional_backup_dirs = set()
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
        ttk.Entry(top_backup, textvariable=self.app.var_backup_dir, state="readonly").pack(
            side="left", fill="x", expand=True, padx=5
        )
        ttk.Button(top_backup, text=T("btn_change_dir"), command=self.change_backup_dir).pack(
            side="right"
        )

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
            default_dir = os.path.join(os.path.expanduser("~"), ".tyranopatcher", "backups")
            os.makedirs(default_dir, exist_ok=True)
            return default_dir
        return d

    def change_backup_dir(self):
        from utils.operation_lock import OperationType

        new_dir = filedialog.askdirectory(
            title=T("title_select_dir"), initialdir=self.get_backup_dir()
        )
        if new_dir:
            old_dir = self.get_backup_dir()
            if os.path.abspath(new_dir) == os.path.abspath(old_dir):
                return

            if not messagebox.askyesno(T("title_confirm"), T("msg_migrate_confirm")):
                previous_dir = self.app.var_backup_dir.get()
                self.app.var_backup_dir.set(new_dir)
                if self.app.save_config():
                    self._additional_backup_dirs.add(old_dir)
                    self.app.log(
                        "Backup directory updated without migration; existing backups remain in the old location.",
                        "warning",
                    )
                else:
                    self.app.var_backup_dir.set(previous_dir)
                    self._additional_backup_dirs.clear()
                    self.app.log("Failed to persist the new backup directory setting.", "error")
                self.scan_saves()
                return

            if not self.app._acquire_operation_lock(OperationType.SAVE_MIGRATE):
                return

            def _migrate_worker(cancel_event=None, _check_cancelled=None):
                try:
                    self.app.save_controller.set_log_callback(self.app.ui_log)
                    migrated_count, failed_count = self.app.save_controller.migrate_backups(
                        old_dir, new_dir, _check_cancelled=_check_cancelled
                    )

                    def _apply_migration_result():
                        msg = T("msg_migrate_success").format(migrated=migrated_count)
                        if failed_count > 0:
                            msg += T("msg_migrate_failed").format(failed=failed_count)
                            self._additional_backup_dirs = {new_dir}
                            self.app.log(
                                "Backup migration incomplete; keeping the current backup directory active.",
                                "warning",
                            )
                        else:
                            previous_dir = self.app.var_backup_dir.get()
                            self.app.var_backup_dir.set(new_dir)
                            if self.app.save_config():
                                self._additional_backup_dirs.clear()
                                self.app.log(f"Backup directory updated: {new_dir}")
                            else:
                                self.app.var_backup_dir.set(previous_dir)
                                self._additional_backup_dirs = {new_dir}
                                msg += (
                                    "\n\nFailed to save the new backup directory setting. "
                                    "Showing both locations for now."
                                )
                                self.app.log(
                                    "Failed to persist the new backup directory setting.",
                                    "error",
                                )

                        if self.app._window_alive():
                            messagebox.showinfo(T("title_success"), msg)
                        self.scan_saves()

                    self.after(0, _apply_migration_result)
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
                    self.app._finish_operation("migrate_backups", OperationType.SAVE_MIGRATE)

            self.app.async_manager.submit("migrate_backup_op", _migrate_worker)

    def scan_saves(self):
        found = self.app.save_controller.scan_save_directory()

        for i in self.tree.get_children():
            self.tree.delete(i)
        self.backup_paths.clear()

        self.app.current_save_dir = found
        self.app.var_save_path.set(found or T("err_no_save"))
        from core.bootstrap import get_runtime_game_path

        root = (
            os.path.dirname(found) if found else (get_runtime_game_path() or os.path.abspath("."))
        )
        backup_dirs = [self.get_backup_dir()]
        backup_dirs.extend(
            path
            for path in sorted(self._additional_backup_dirs)
            if os.path.abspath(path) != os.path.abspath(backup_dirs[0])
        )
        backups = self.app.save_controller.scan_backups(root, backup_dirs)
        for dn, fp, is_zip in backups:
            iid = f"bk_{len(self.backup_paths)}"
            type_tag = "[ZIP]" if is_zip else "[DIR]"
            self.tree.insert("", tk.END, iid=iid, values=(dn, type_tag))
            self.backup_paths[iid] = fp

    def _submit_async_operation(self, op_type, op_name, worker_func):
        from utils.operation_lock import get_operation_lock

        lock = get_operation_lock()
        if not lock.acquire(op_type):
            return messagebox.showwarning(
                T("title_warning"),
                T("warn_operation_in_progress", "Operation in progress..."),
            )

        self.app.performance_monitor.start(op_name)
        self.app.is_operating = True
        self.app.toggle_progress(True)

        def wrapped_worker(cancel_event=None, _check_cancelled=None):
            try:
                return worker_func(cancel_event, _check_cancelled)
            finally:
                self.app._finish_operation(op_name, op_type)

        self.app.async_manager.submit(f"{op_name}_op", wrapped_worker)

    def do_backup_save(self):
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

        from utils.operation_lock import OperationType

        def _worker(cancel_event=None, _check_cancelled=None):
            try:
                self.app.save_controller.set_log_callback(self.app.ui_log)
                success = self.app.save_controller.execute_backup(
                    save_dir, parent, use_zip, _check_cancelled=_check_cancelled
                )
                if success:
                    self.after(0, self.scan_saves)
                    self.after(
                        0,
                        lambda: messagebox.showinfo(T("title_success"), T("msg_backup_ok")),
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
                    lambda e_str=f"{e}\n\n{traceback_str}": messagebox.showerror(
                        T("title_error"), e_str
                    ),
                )

        self._submit_async_operation(OperationType.SAVE_BACKUP, "backup_save", _worker)

    def do_restore_save(self):
        from utils.operation_lock import OperationType

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

        if not save_dir:
            from core.bootstrap import get_runtime_game_path
            from core.save_service import SaveService

            game_dir = get_runtime_game_path() or os.path.abspath(".")
            save_dir = filedialog.askdirectory(
                title=T("title_select_save_target"), initialdir=game_dir, mustexist=False
            )
            if not save_dir:
                return
            save_dir = os.path.abspath(save_dir)
            if SaveService._is_within_or_equal(game_dir, save_dir):
                return messagebox.showerror(T("title_error"), T("err_save_target_game_root"))

        if not messagebox.askyesno(
            T("title_confirm"),
            T("msg_restore_confirm") + "\n\n" + save_dir,
            default=messagebox.NO,
        ):
            return

        def _w(cancel_event=None, _check_cancelled=None):
            try:
                self.app.save_controller.set_log_callback(self.app.ui_log)
                success, msg = self.app.save_controller.execute_restore(
                    save_dir, src, _check_cancelled=_check_cancelled
                )
                if success and not msg:
                    self.after(
                        0,
                        lambda: messagebox.showinfo(T("title_success"), T("msg_restored")),
                    )
                    self.after(0, self.scan_saves)
                elif success and msg:
                    self.after(
                        0,
                        lambda w_msg=msg: messagebox.showwarning(T("title_warning"), w_msg),
                    )
                    self.after(0, self.scan_saves)
                else:
                    self.after(
                        0,
                        lambda e_str=msg: messagebox.showerror(T("title_error"), e_str),
                    )
            except PatcherError as e:
                from utils.error_handler import ErrorHandler

                traceback_str = ErrorHandler.format_traceback(e)
                logger.error(f"Restore error: {e}\n{traceback_str}")
                title = T("title_error")
                msg = f"{e}\n\n{traceback_str}"
                if e.severity == ErrorSeverity.CRITICAL:
                    msg = T("err_fatal_error", "Fatal Error") + f":\n{msg}"
                self.after(
                    0,
                    lambda e_title=title, e_msg=msg: messagebox.showerror(e_title, e_msg),
                )
            except Exception as e:
                from utils.error_handler import ErrorHandler

                traceback_str = ErrorHandler.format_traceback(e)
                logger.error(f"Restore error: {e}\n{traceback_str}")
                self.after(
                    0,
                    lambda e_str=f"{e}\n\n{traceback_str}": messagebox.showerror(
                        T("title_error"), e_str
                    ),
                )

        self._submit_async_operation(OperationType.SAVE_RESTORE, "restore_save", _w)

    def do_delete_backup(self):
        from utils.operation_lock import OperationType

        sel = self.tree.selection()
        if not sel:
            return messagebox.showwarning(T("title_warning"), T("no_backup_selected"))
        src = self.backup_paths[sel[0]]

        if not messagebox.askyesno(T("title_confirm"), T("msg_delete_confirm")):
            return

        def _w(cancel_event=None, _check_cancelled=None):
            try:
                self.app.save_controller.set_log_callback(self.app.ui_log)
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
                    lambda e_str=f"{e}\n\n{traceback_str}": messagebox.showerror(
                        T("title_error"), e_str
                    ),
                )

        self._submit_async_operation(OperationType.SAVE_DELETE, "delete_backup", _w)
