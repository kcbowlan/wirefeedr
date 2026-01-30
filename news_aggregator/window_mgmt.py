# window_mgmt - Win32 borderless window management, drag, resize, tooltips

import sys
import os

from config import DARK_THEME


def strip_title_bar(app):
    """Remove native title bar using Win32 API while keeping proper window management."""
    if sys.platform != "win32":
        app.root.overrideredirect(True)
        return
    try:
        import ctypes
        app.root.update_idletasks()
        hwnd = int(app.root.wm_frame(), 16)
        app._hwnd = hwnd

        GWL_STYLE = -16
        WS_CAPTION = 0x00C00000
        WS_THICKFRAME = 0x00040000
        WS_SYSMENU = 0x00080000
        WS_MINIMIZEBOX = 0x00020000
        WS_VISIBLE = 0x10000000
        SWP_FRAMECHANGED = 0x0020
        SWP_NOMOVE = 0x0002
        SWP_NOSIZE = 0x0001
        SWP_NOZORDER = 0x0004

        style = ctypes.windll.user32.GetWindowLongW(hwnd, GWL_STYLE)
        style = style & ~WS_CAPTION & ~WS_THICKFRAME & ~WS_SYSMENU
        style = style | WS_MINIMIZEBOX | WS_VISIBLE
        ctypes.windll.user32.SetWindowLongW(hwnd, GWL_STYLE, style)

        ctypes.windll.user32.SetWindowPos(
            hwnd, 0, 0, 0, 0, 0,
            SWP_FRAMECHANGED | SWP_NOMOVE | SWP_NOSIZE | SWP_NOZORDER
        )
    except Exception:
        app.root.overrideredirect(True)


def setup_owner_icon(app):
    """Set the taskbar icon on the hidden owner window."""
    try:
        from PIL import Image, ImageDraw, ImageFont
        ico_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "icon.ico")
        # Generate crisp icon: bold cyan W with magenta shadow on dark bg
        ico_sizes = [256, 64, 48, 32, 24, 16]
        frames = []
        for s in ico_sizes:
            img = Image.new("RGBA", (s, s), (5, 5, 10, 255))
            draw = ImageDraw.Draw(img)
            bw = max(1, s // 64)
            draw.rectangle([0, 0, s - 1, s - 1], outline=(0, 255, 255, 255), width=bw)
            font_size = int(s * 0.7)
            try:
                font = ImageFont.truetype("consola.ttf", font_size)
            except Exception:
                font = ImageFont.load_default()
            bbox = draw.textbbox((0, 0), "W", font=font)
            tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
            x = (s - tw) // 2
            y = (s - th) // 2 - bbox[1]
            off = max(1, s // 64)
            draw.text((x + off, y + off), "W", fill=(255, 0, 255, 180), font=font)
            draw.text((x, y), "W", fill=(0, 255, 255, 255), font=font)
            frames.append(img)
        frames[0].save(ico_path, format="ICO", append_images=frames[1:])
        app._owner.iconbitmap(ico_path)
    except Exception:
        pass


def on_taskbar_restore(app, event=None):
    """Restore window when taskbar icon is clicked."""
    app._owner.attributes("-alpha", 0)  # Keep owner invisible
    app._owner.geometry("1x1+-10000+-10000")
    app.root.deiconify()
    app.root.lift()
    app.root.focus_force()


def start_drag(app, event):
    """Record drag start position."""
    app._drag_start_x = event.x_root
    app._drag_start_y = event.y_root
    geo = app.root.geometry()
    import re
    m = re.match(r'(\d+)x(\d+)\+(-?\d+)\+(-?\d+)', geo)
    if m:
        app._drag_win_x = int(m.group(3))
        app._drag_win_y = int(m.group(4))
    else:
        app._drag_win_x = app.root.winfo_x()
        app._drag_win_y = app.root.winfo_y()
    app.root.lift()


def do_drag(app, event):
    """Move window during drag."""
    if app._is_maximized:
        toggle_maximize(app)
    dx = event.x_root - app._drag_start_x
    dy = event.y_root - app._drag_start_y
    x = app._drag_win_x + dx
    y = app._drag_win_y + dy
    # Use Win32 MoveWindow with repaint flag to avoid ghosting
    if sys.platform == "win32" and hasattr(app, "_hwnd"):
        try:
            import ctypes
            w = app.root.winfo_width()
            h = app.root.winfo_height()
            ctypes.windll.user32.MoveWindow(app._hwnd, x, y, w, h, True)
            return
        except Exception:
            pass
    app.root.geometry(f"+{x}+{y}")


def end_drag(app, event):
    """Ensure window stays visible after drag."""
    app.root.lift()
    app.root.focus_force()


def minimize_window(app):
    """Minimize to taskbar."""
    if sys.platform == "win32" and hasattr(app, "_hwnd"):
        try:
            import ctypes
            ctypes.windll.user32.ShowWindow(app._hwnd, 6)  # SW_MINIMIZE
            return
        except Exception:
            pass
    app.root.withdraw()
    app._owner.iconify()


def toggle_maximize(app):
    """Toggle between maximized and normal size."""
    if app._is_maximized:
        app.root.geometry(app._normal_geometry)
        app.max_btn.configure(text="\u25fb")
        app._is_maximized = False
    else:
        app._normal_geometry = app.root.geometry()
        # Get usable work area (excludes taskbar) via Win32 API
        try:
            import ctypes
            from ctypes import wintypes
            rect = wintypes.RECT()
            # SPI_GETWORKAREA = 0x0030
            ctypes.windll.user32.SystemParametersInfoW(0x0030, 0, ctypes.byref(rect), 0)
            x, y, w, h = rect.left, rect.top, rect.right - rect.left, rect.bottom - rect.top
        except Exception:
            x, y = 0, 0
            w = app.root.winfo_screenwidth()
            h = app.root.winfo_screenheight() - 48
        app.root.geometry(f"{w}x{h}+{x}+{y}")
        app.max_btn.configure(text="\u25a3")
        app._is_maximized = True


def build_resize_grip(app):
    """Add resize grip to bottom-right corner."""
    import tkinter as tk
    app._grip = tk.Label(
        app.root, text="\u2921",
        bg=DARK_THEME["bg"], fg=DARK_THEME["cyan_dim"],
        font=("Consolas", 10), cursor="size_nw_se"
    )
    app._grip.place(relx=1.0, rely=1.0, anchor=tk.SE)
    app._grip.bind("<Button-1>", lambda e: start_resize(app, e))
    app._grip.bind("<B1-Motion>", lambda e: do_resize(app, e))


def start_resize(app, event):
    app._resize_x = event.x_root
    app._resize_y = event.y_root
    app._resize_w = app.root.winfo_width()
    app._resize_h = app.root.winfo_height()


def do_resize(app, event):
    dx = event.x_root - app._resize_x
    dy = event.y_root - app._resize_y
    new_w = max(900, app._resize_w + dx)
    new_h = max(500, app._resize_h + dy)
    app.root.geometry(f"{new_w}x{new_h}")


def show_logo_tooltip(app, event):
    """Show Patreon tooltip on logo hover."""
    import tkinter as tk
    app._logo_tooltip = tk.Toplevel(app.root)
    app._logo_tooltip.wm_overrideredirect(True)
    app._logo_tooltip.wm_geometry(f"+{event.x_root + 10}+{event.y_root + 10}")
    label = tk.Label(
        app._logo_tooltip, text="Patreon",
        bg=DARK_THEME["bg_secondary"], fg=DARK_THEME["cyan"],
        font=("Consolas", 9), padx=6, pady=2,
        relief=tk.SOLID, borderwidth=1
    )
    label.pack()
    event.widget.configure(bg=DARK_THEME["bg_secondary"])


def hide_logo_tooltip(app, event):
    """Hide Patreon tooltip."""
    if hasattr(app, '_logo_tooltip') and app._logo_tooltip:
        app._logo_tooltip.destroy()
        app._logo_tooltip = None
    event.widget.configure(bg=DARK_THEME["bg"])
