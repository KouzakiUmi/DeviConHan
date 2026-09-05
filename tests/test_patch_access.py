"""Exercise edition defaults and installation gating using actual Tk controls."""

import tempfile
import tkinter as tk
from pathlib import Path
from tkinter import ttk
from unittest.mock import Mock

import pytest

from core.config import AppConfig
from gui.main_window import App
from gui.tabs.patch_tab import PatchTab
from gui.tabs.tools_tab import ToolsTab
from utils.language import T


class PatchWindow(ttk.Frame):
    _init_patch_settings = App._init_patch_settings
    get_config_value = App.get_config_value
    save_config = App.save_config
    on_patch_enabled_changed = App.on_patch_enabled_changed
    refresh_patch_access = App.refresh_patch_access

    def __init__(self, parent, config):
        super().__init__(parent)
        self.app_config = config
        self.is_operating = False
        self.async_manager = Mock()
        self.toggle_progress = Mock()
        self.log = Mock()
        self._init_patch_settings()
        self.notebook = ttk.Notebook(self)
        self.tab_patch = PatchTab(self.notebook, self)
        self.notebook.add(self.tab_patch, text="Patch")
        self.tab_tools = ToolsTab(self.notebook, self)
        self.notebook.add(self.tab_tools, text="Tools")
        self.refresh_patch_access()

    def patch_checkbox(self):
        def children(widget):
            for child in widget.winfo_children():
                yield child
                yield from children(child)
        return next(
            widget for widget in children(self.tab_tools)
            if isinstance(widget, ttk.Checkbutton)
            and str(widget.cget("variable")) == str(self.var_patch_enabled)
        )


@pytest.fixture(scope="module")
def tk_root():
    try:
        root = tk.Tk()
    except tk.TclError as error:
        if "no display name" in str(error) or "couldn't connect to display" in str(error):
            pytest.skip(f"Tk display unavailable: {error}")
        raise
    root.withdraw()
    yield root
    root.destroy()


@pytest.fixture
def work_dir():
    with tempfile.TemporaryDirectory(prefix="devicon-patch-ui-") as path:
        yield Path(path)


@pytest.fixture
def windows(work_dir, monkeypatch, tk_root):
    config_path = work_dir / "config.ini"
    config_path.write_text("[main]\n[preferences]\n", encoding="utf-8")
    created = []
    monkeypatch.setattr("gui.tabs.patch_tab.messagebox.showwarning", Mock())

    def create(bundled):
        config = AppConfig(str(config_path))
        monkeypatch.setattr("gui.main_window.has_embedded_patch", lambda: bundled)
        monkeypatch.setattr("gui.tabs.patch_tab.get_config", lambda: config)
        window = PatchWindow(tk_root, config)
        created.append(window)
        return window

    yield create
    for window in created:
        try:
            window.destroy()
        except tk.TclError:
            pass


@pytest.mark.parametrize("bundled", [False, True])
def test_defaults_and_checkbox_unlock_first_tab(windows, bundled):
    app = windows(bundled)
    assert app.var_patch_enabled.get() is bundled
    assert app.notebook.tab(app.tab_patch, "state") == ("normal" if bundled else "disabled")
    app.notebook.select(app.tab_patch)
    assert app.notebook.select() == str(app.tab_patch if bundled else app.tab_tools)
    assert app.tab_patch.btn_p.instate(["!disabled"]) is bundled
    app.patch_checkbox().invoke()
    assert app.notebook.tab(app.tab_patch, "state") == ("disabled" if bundled else "normal")
    app.notebook.select(app.tab_patch)
    assert app.notebook.select() == str(app.tab_tools if bundled else app.tab_patch)
    assert app.tab_patch.btn_p.instate(["!disabled"]) is (not bundled)
    assert app.tab_patch.btn_restore_patch.instate(["!disabled"]) is (not bundled)
    assert app.tab_patch.btn_default_patch.instate(["disabled"])


def test_toolbox_cannot_submit_until_user_selects_package(windows, work_dir, monkeypatch):
    app = windows(False)
    tab = app.tab_patch
    tab.run_auto_patch()
    tab.restore_patch()
    app.async_manager.submit.assert_not_called()
    app.patch_checkbox().invoke()
    tab.run_auto_patch()
    app.async_manager.submit.assert_not_called()
    assert not app.is_operating
    assert tab.var_patch_zip.get() == ""
    package = work_dir / "custom.zip"
    package.write_bytes(b"selection only; controller validates ZIP contents")
    monkeypatch.setattr("gui.tabs.patch_tab.filedialog.askopenfilename", lambda **_: str(package))
    tab.select_patch_zip()
    tab.use_default_patch()  # A toolbox cannot switch to an implicit bundled source.
    assert app.selected_patch_zip == str(package)
    tab.run_auto_patch()
    assert tab._pending_patch_zip == str(package)
    assert app.is_operating
    app.async_manager.submit.assert_called_once_with("auto_patch_op", tab._run_auto_patch_worker)
    assert tab.btn_p.instate(["disabled"])


def test_bundled_install_uses_default_resolver_for_zip_or_directory(windows):
    app = windows(True)
    assert app.tab_patch.var_patch_zip.get() == T("lbl_bundled_patch")
    app.tab_patch.run_auto_patch()
    assert app.tab_patch._pending_patch_zip is None
    app.async_manager.submit.assert_called_once()


def test_deleted_selected_zip_does_not_fall_back_to_bundle(windows, work_dir):
    app = windows(True)
    app.selected_patch_zip = str(work_dir / "missing.zip")
    app.tab_patch.run_auto_patch()
    app.async_manager.submit.assert_not_called()
    assert not app.is_operating


def test_edition_preferences_are_independent_and_boolean(windows):
    toolbox = windows(False)
    toolbox.patch_checkbox().invoke()
    toolbox.destroy()
    bundled = windows(True)
    assert bundled.var_patch_enabled.get()
    bundled.patch_checkbox().invoke()
    bundled.destroy()
    toolbox_again = windows(False)
    assert toolbox_again.var_patch_enabled.get()
    toolbox_again.destroy()
    bundled_again = windows(True)
    assert not bundled_again.var_patch_enabled.get()


def test_busy_toggle_rejected_and_page_rebuild_preserves_selection(windows, work_dir):
    app = windows(False)
    app.patch_checkbox().invoke()
    app.selected_patch_zip = str(work_dir / "selected.zip")
    app.is_operating = True
    app.patch_checkbox().invoke()
    assert app.var_patch_enabled.get()
    app.is_operating = False
    app.tab_patch.destroy()
    app.tab_patch = PatchTab(app.notebook, app)
    app.notebook.insert(0, app.tab_patch, text="Patch")
    app.refresh_patch_access()
    assert app.tab_patch.var_patch_zip.get() == app.selected_patch_zip
    assert app.tab_patch.btn_p.instate(["!disabled"])
    assert app.tab_patch.btn_default_patch.instate(["disabled"])
    app.patch_checkbox().invoke()
    app.tab_patch._set_action_buttons_enabled(True)
    assert app.tab_patch.btn_p.instate(["disabled"])


@pytest.mark.parametrize("bundled", [False, True])
def test_reset_restores_mode_default_and_refuses_during_operation(
    windows, work_dir, monkeypatch, bundled
):
    app = windows(bundled)
    app.patch_checkbox().invoke()
    template = work_dir / "default.ini"
    template.write_text("[main]\n", encoding="utf-8")
    monkeypatch.setattr("utils.paths.get_resource_path", lambda _: str(template))
    monkeypatch.setattr("gui.tabs.tools_tab.get_config", lambda: app.app_config)
    ask = Mock(return_value=True)
    monkeypatch.setattr("gui.tabs.tools_tab.messagebox.askyesno", ask)
    monkeypatch.setattr("gui.tabs.tools_tab.messagebox.showinfo", Mock())
    app.is_operating = True
    app.tab_tools._reset_config()
    ask.assert_not_called()
    assert app.var_patch_enabled.get() is (not bundled)
    app.is_operating = False
    app.tab_tools._reset_config()
    assert app.var_patch_enabled.get() is bundled
    assert app.notebook.tab(app.tab_patch, "state") == ("normal" if bundled else "disabled")
    assert app.tab_patch.btn_p.instate(["!disabled"]) is bundled


def test_disabling_selected_patch_tab_returns_to_tools(windows):
    app = windows(True)
    app.notebook.select(app.tab_patch)
    app.patch_checkbox().invoke()
    assert app.notebook.select() == str(app.tab_tools)
    assert app.notebook.tab(app.tab_patch, "state") == "disabled"
    app.notebook.select(app.tab_patch)
    assert app.notebook.select() == str(app.tab_tools)
    app.patch_checkbox().invoke()
    app.notebook.select(app.tab_patch)
    assert app.notebook.select() == str(app.tab_patch)
