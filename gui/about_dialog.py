"""
关于对话框模块
"""

import logging
import os
import tkinter as tk
from tkinter import ttk

from utils.constants import GITHUB_REPO_URL
from utils.language import T, get_font
from utils.paths import get_resource_path

logger = logging.getLogger(__name__)


def show_about_dialog(parent):
    """显示关于对话框"""
    about_app_label = T("menu_about_app")

    dlg = tk.Toplevel(parent)
    dlg.title(about_app_label)
    dlg.resizable(False, False)
    dlg.transient(parent)
    dlg.grab_set()

    _center_dialog(parent, dlg, 550, 350)
    _set_dialog_icon(dlg)

    main_frame = ttk.Frame(dlg, padding=20)
    main_frame.pack(fill="both", expand=True)

    _create_about_avatar(main_frame, dlg)
    _create_about_info(main_frame, dlg)


def _center_dialog(parent, dlg, width, height):
    """将对话框居中显示"""
    parent.update_idletasks()
    x = parent.winfo_rootx() + (parent.winfo_width() // 2) - (width // 2)
    y = parent.winfo_rooty() + (parent.winfo_height() // 2) - (height // 2)
    dlg.geometry(f"{width}x{height}+{x}+{y}")


def _set_dialog_icon(dlg):
    """为对话框设置图标"""
    try:
        icon_path = get_resource_path("icon.ico")
        if os.path.exists(icon_path):
            dlg.iconbitmap(icon_path)
    except Exception:
        pass


def _create_about_avatar(parent_frame, dlg):
    """创建关于对话框的头像区域"""
    avatar_img = None
    try:
        import base64
        import struct

        icon_path = get_resource_path("icon.ico")
        if os.path.exists(icon_path):
            with open(icon_path, "rb") as f:
                f.read(4)
                n = struct.unpack("<H", f.read(2))[0]
                for _ in range(n):
                    img_w, img_h, _, _, _, _, size, offset = struct.unpack("<BBBBHHII", f.read(16))
                    if img_w == 0 and img_h == 0:
                        f.seek(offset)
                        png_data = f.read(size)
                        if png_data.startswith(b"\x89PNG"):
                            b64_data = base64.b64encode(png_data)
                            tk_img = tk.PhotoImage(data=b64_data)
                            avatar_img = tk_img.subsample(2, 2)
                            dlg._avatar_img_ref = avatar_img
                        break
    except Exception as e:
        logger.warning(f"Failed to load avatar from ICO: {e}")

    if avatar_img:
        lbl_avatar = ttk.Label(parent_frame, image=avatar_img)
        lbl_avatar.pack(side="left", padx=(0, 20), anchor="n")
    else:
        lbl_avatar = ttk.Label(parent_frame, text="[ICON]", font=get_font(24))
        lbl_avatar.pack(side="left", padx=(0, 20), anchor="n")


def _create_about_info(parent_frame, dlg):
    """创建关于对话框的文本信息区域"""
    info_frame = ttk.Frame(parent_frame)
    info_frame.pack(side="left", fill="both", expand=True)

    app_name = T("app_title")
    ttk.Label(info_frame, text=app_name, font=get_font(14, "bold")).pack(anchor="w", pady=(0, 5))

    about_version = T("about_version")
    ttk.Label(info_frame, text=about_version, font=get_font(10)).pack(anchor="w", pady=(0, 10))

    desc = T("about_desc")

    # 使用带滚动条的文本框展示 Credits
    from tkinter import scrolledtext

    text_area = scrolledtext.ScrolledText(info_frame, wrap=tk.WORD, height=8, font=get_font(9))
    text_area.insert(tk.END, desc)
    text_area.config(state="disabled")
    text_area.pack(fill="both", expand=True, pady=(0, 10))

    # 链接标签
    def open_url(event):
        import webbrowser

        webbrowser.open(GITHUB_REPO_URL)

    about_github_link = T("about_github_link")
    lbl_link = ttk.Label(info_frame, text=about_github_link, foreground="blue", cursor="hand2")
    lbl_link.pack(anchor="w", pady=(0, 10))
    lbl_link.bind("<Button-1>", open_url)

    btn_frame = ttk.Frame(info_frame)
    btn_frame.pack(fill="x", side="bottom")

    btn_ok = T("btn_ok")
    ttk.Button(btn_frame, text=btn_ok, command=dlg.destroy, width=10).pack(side="right")
