# ui_builders.py - Widget construction and layout

import tkinter as tk
from tkinter import ttk
import tkinter.font as tkfont
import os
import webbrowser

from config import DARK_THEME, BIAS_COLORS, FACTUAL_COLORS
import window_mgmt
import animations


def setup_styles(app):
    """Configure ttk styles with dark cyberpunk theme."""
    app.root.configure(bg=DARK_THEME["bg"])

    style = ttk.Style()
    style.theme_use("clam")
    t = DARK_THEME

    # Root default
    style.configure(".", background=t["bg"], foreground=t["fg"])

    # Frames
    style.configure("TFrame", background=t["bg"])
    style.configure("TLabel", background=t["bg"], foreground=t["fg"])
    style.configure("TButton", background=t["bg_tertiary"], foreground=t["cyan"], padding=5,
                     bordercolor=t["cyan_dim"], lightcolor=t["bg_tertiary"],
                     darkcolor=t["bg_tertiary"])
    style.map("TButton",
              background=[("active", t["magenta"]), ("pressed", t["magenta_dim"])],
              foreground=[("active", t["fg_highlight"]), ("pressed", t["fg_highlight"])],
              bordercolor=[("active", t["magenta"])])
    style.configure("TCheckbutton", background=t["bg"], foreground=t["fg"],
                     indicatorcolor=t["bg_tertiary"], indicatorrelief=tk.FLAT)
    style.map("TCheckbutton",
              background=[("active", t["bg"])],
              foreground=[("active", t["cyan"])],
              indicatorcolor=[("selected", t["cyan"]), ("active", t["bg_tertiary"])])
    style.configure("TCombobox", fieldbackground=t["bg_tertiary"], foreground=t["fg"],
                     background=t["bg_tertiary"], arrowcolor=t["cyan"])
    style.map("TCombobox",
              fieldbackground=[("readonly", t["bg_tertiary"])],
              foreground=[("readonly", t["fg"])],
              selectbackground=[("readonly", t["magenta"])],
              selectforeground=[("readonly", t["fg_highlight"])],
              arrowcolor=[("active", t["magenta"])])

    # Treeview
    style.configure("Treeview", background=t["bg_tertiary"], foreground=t["fg"],
                     fieldbackground=t["bg_tertiary"], rowheight=28,
                     bordercolor=t["cyan_dim"], lightcolor=t["bg"], darkcolor=t["bg"])
    style.map("Treeview",
              background=[("selected", t["selected"])],
              foreground=[("selected", t["selected_fg"])])
    style.configure("Treeview.Heading", background=t["bg_secondary"], foreground=t["cyan"],
                     bordercolor=t["cyan_dim"], lightcolor=t["bg_secondary"],
                     darkcolor=t["bg_secondary"])
    style.map("Treeview.Heading",
              background=[("active", t["bg_toolbar"])],
              foreground=[("active", t["magenta"])])

    # LabelFrame
    style.configure("TLabelframe", background=t["bg"],
                     bordercolor=t["cyan_dim"], lightcolor=t["bg"], darkcolor=t["bg"])
    style.configure("TLabelframe.Label", background=t["bg"], foreground=t["cyan"])

    # PanedWindow
    style.configure("TPanedwindow", background=t["bg"])

    # Separator
    style.configure("TSeparator", background=t["cyan_dim"])

    # Scrollbar - NEON CYBERPUNK
    style.configure("TScrollbar",
                    background=t["cyan"],           # Thumb is bright cyan
                    troughcolor=t["bg"],            # Deep void trough
                    arrowcolor=t["cyan_bright"],    # Bright arrows
                    bordercolor=t["cyan_dim"],      # Subtle border
                    lightcolor=t["cyan"],           # 3D highlight
                    darkcolor=t["cyan_dim"])        # 3D shadow
    style.map("TScrollbar",
              background=[("active", t["magenta"]), ("pressed", t["magenta_bright"]),
                          ("disabled", t["bg_secondary"])],
              arrowcolor=[("active", t["magenta_bright"]), ("pressed", t["magenta"]),
                          ("disabled", t["fg_secondary"])])

    # Menubutton
    style.configure("TMenubutton", background=t["bg_tertiary"], foreground=t["cyan"])
    style.map("TMenubutton",
              background=[("active", t["magenta"]), ("disabled", t["bg_secondary"])],
              foreground=[("active", t["fg_highlight"]), ("disabled", t["fg_secondary"])])

    # Entry
    style.configure("TEntry", fieldbackground=t["bg_tertiary"], foreground=t["fg"],
                     bordercolor=t["cyan_dim"], lightcolor=t["bg_tertiary"],
                     darkcolor=t["bg_tertiary"], insertcolor=t["cyan"])

    # Spinbox
    style.configure("TSpinbox", fieldbackground=t["bg_tertiary"], foreground=t["fg"],
                     background=t["bg_tertiary"])

    style.configure("Toolbutton", padding=5)

    # Style combobox dropdown popdown (tk.Listbox inside)
    app.root.option_add("*TCombobox*Listbox.background", t["bg_tertiary"])
    app.root.option_add("*TCombobox*Listbox.foreground", t["fg"])
    app.root.option_add("*TCombobox*Listbox.selectBackground", t["magenta"])
    app.root.option_add("*TCombobox*Listbox.selectForeground", t["fg_highlight"])


def build_title_bar(app):
    """Build neon border frame around entire window."""
    app.max_btn = None
    app.title_bar = None
    t = DARK_THEME

    # Create border canvases (top, bottom, left, right)
    border_thickness = 2

    app._border_top = tk.Canvas(app.root, height=border_thickness, bg=t["bg"], highlightthickness=0)
    app._border_top.pack(side=tk.TOP, fill=tk.X)

    app._border_bottom = tk.Canvas(app.root, height=border_thickness, bg=t["bg"], highlightthickness=0)
    app._border_bottom.pack(side=tk.BOTTOM, fill=tk.X)

    app._border_left = tk.Canvas(app.root, width=border_thickness, bg=t["bg"], highlightthickness=0)
    app._border_left.pack(side=tk.LEFT, fill=tk.Y)

    app._border_right = tk.Canvas(app.root, width=border_thickness, bg=t["bg"], highlightthickness=0)
    app._border_right.pack(side=tk.RIGHT, fill=tk.Y)

    # For compatibility with existing code
    app.title_neon_line = app._border_top


def build_menus(app):
    """Pre-build popup menus for the custom title bar."""
    _m = dict(bg=DARK_THEME["bg_secondary"], fg=DARK_THEME["fg"],
              activebackground=DARK_THEME["magenta"],
              activeforeground=DARK_THEME["fg_highlight"], tearoff=0)

    # Settings menu (consolidated)
    app._settings_menu = tk.Menu(app.root, **_m)

    # Feeds submenu
    app._feeds_submenu = tk.Menu(app._settings_menu, **_m)
    app._feeds_submenu.add_command(label="Add Feed...", command=app.show_add_feed_dialog)
    app._feeds_submenu.add_command(label="Manage Feeds...", command=app.show_manage_feeds_dialog)
    app._settings_menu.add_cascade(label="Feeds", menu=app._feeds_submenu)

    # Articles submenu
    app._articles_submenu = tk.Menu(app._settings_menu, **_m)
    app._articles_submenu.add_command(label="Mark All as Read", command=app.mark_all_read)
    app._articles_submenu.add_command(label="Delete Old Articles...", command=app.show_delete_old_dialog)
    app._settings_menu.add_cascade(label="Articles", menu=app._articles_submenu)

    app._settings_menu.add_separator()

    # Recency submenu
    app._recency_submenu = tk.Menu(app._settings_menu, **_m)
    app._recency_var = tk.StringVar(value=app.storage.get_setting("recency_hours", "24"))
    for label, value in [("6 hours", "6"), ("12 hours", "12"), ("24 hours", "24"),
                         ("48 hours", "48"), ("1 week", "168"), ("All time", "0")]:
        app._recency_submenu.add_radiobutton(
            label=label, variable=app._recency_var, value=value,
            command=lambda v=value: app._set_recency(v))
    app._settings_menu.add_cascade(label="Recency", menu=app._recency_submenu)

    # Per Source submenu
    app._per_source_submenu = tk.Menu(app._settings_menu, **_m)
    app._per_source_var = tk.StringVar(value=app.storage.get_setting("max_per_source", "10"))
    for label, value in [("5 per source", "5"), ("10 per source", "10"), ("15 per source", "15"),
                         ("20 per source", "20"), ("No limit", "0")]:
        app._per_source_submenu.add_radiobutton(
            label=label, variable=app._per_source_var, value=value,
            command=lambda v=value: app._set_per_source(v))
    app._settings_menu.add_cascade(label="Per Source", menu=app._per_source_submenu)

    # Cluster toggle
    app._cluster_var = tk.BooleanVar(value=app.storage.get_setting("cluster_topics", "True") == "True")
    app._settings_menu.add_checkbutton(label="Cluster Topics", variable=app._cluster_var,
                                        command=app._on_cluster_toggle)

    app._settings_menu.add_separator()
    app._settings_menu.add_command(label="Filter Keywords...", command=app.show_filter_keywords_dialog)
    app._settings_menu.add_separator()
    app._settings_menu.add_command(label="About WIREFEEDR...", command=app.show_about_dialog)
    app._settings_menu.add_separator()
    app._settings_menu.add_command(label="Exit", command=app._on_close)


def show_settings_menu(app, event):
    app._settings_menu.tk_popup(event.widget.winfo_rootx(),
                                  event.widget.winfo_rooty() + event.widget.winfo_height())


def bind_shortcuts(app):
    """Bind keyboard shortcuts."""
    app.root.bind("<F5>", lambda e: app.fetch_all_feeds())
    # Note: Up/Down arrow bindings moved to articles_tree in _build_main_layout
    app.root.bind("<Return>", lambda e: app.open_in_browser())
    app.root.bind("m", app._on_key_toggle_read)
    app.root.bind("M", app._on_key_toggle_read)
    app.root.bind("h", app._on_key_hide)
    app.root.bind("H", app._on_key_hide)
    app.root.bind("f", app._on_key_toggle_favorite)
    app.root.bind("F", app._on_key_toggle_favorite)
    app.root.bind("<KeyPress>", lambda e: animations.konami_check(app, e))


def build_toolbar(app):
    """Build the toolbar with gradient background (also serves as drag handle)."""
    t = DARK_THEME

    # Container frame for toolbar
    toolbar_container = tk.Frame(app.root, bg=t["bg_secondary"])
    toolbar_container.pack(side=tk.TOP, fill=tk.X, padx=0, pady=0)

    # Gradient canvas placed behind widgets via place()
    app._toolbar_canvas = tk.Canvas(
        toolbar_container, highlightthickness=0, bg=t["bg_secondary"]
    )
    app._toolbar_canvas.place(x=0, y=0, relwidth=1.0, relheight=1.0)

    # The actual toolbar frame sits on top of the canvas
    app.toolbar = tk.Frame(toolbar_container, bg=t["bg_secondary"])
    app.toolbar.pack(fill=tk.X)
    toolbar = app.toolbar

    # Drag bindings for borderless window
    toolbar.bind("<Button-1>", lambda e: window_mgmt.start_drag(app, e))
    toolbar.bind("<B1-Motion>", lambda e: window_mgmt.do_drag(app, e))
    toolbar.bind("<ButtonRelease-1>", lambda e: window_mgmt.end_drag(app, e))
    toolbar.bind("<Double-1>", lambda e: app._toggle_maximize())
    # Also bind drag on the canvas for the gap areas
    app._toolbar_canvas.bind("<Button-1>", lambda e: window_mgmt.start_drag(app, e))
    app._toolbar_canvas.bind("<B1-Motion>", lambda e: window_mgmt.do_drag(app, e))
    app._toolbar_canvas.bind("<ButtonRelease-1>", lambda e: window_mgmt.end_drag(app, e))
    app._toolbar_canvas.bind("<Double-1>", lambda e: app._toggle_maximize())

    # Refresh button
    app.refresh_btn = animations.create_gradient_button(
        app, toolbar, "\u21bb Refresh", app.fetch_all_feeds
    )
    app.refresh_btn.pack(side=tk.LEFT, padx=2)

    # Mark all read button
    app._mark_all_btn = animations.create_gradient_button(
        app, toolbar, "\u2713 Mark All Read", app.mark_all_read
    )
    app._mark_all_btn.pack(side=tk.LEFT, padx=2)

    # Separator
    ttk.Separator(toolbar, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=10)

    # Show read articles checkbox
    app.show_read_var = tk.BooleanVar(value=True)
    ttk.Checkbutton(toolbar, text="Show Read", variable=app.show_read_var,
                    command=app.refresh_articles).pack(side=tk.LEFT, padx=5)

    # Window controls (far right)
    btn_style = dict(
        bg=t["bg_secondary"], fg=t["fg"],
        font=("Segoe UI Symbol", 10), bd=0, padx=6, pady=1,
        activebackground=t["bg_tertiary"], activeforeground=t["fg_highlight"],
        width=2
    )

    close_btn = tk.Button(toolbar, text="\u2715", command=app._on_close, **btn_style)
    close_btn.pack(side=tk.RIGHT, padx=(2, 0))
    close_btn.bind("<Enter>", lambda e: e.widget.configure(bg="#cc0000", fg="#ffffff"))
    close_btn.bind("<Leave>", lambda e: e.widget.configure(bg=t["bg_secondary"], fg=t["fg"]))

    app.max_btn = tk.Button(toolbar, text="\u25fb", command=app._toggle_maximize, **btn_style)
    app.max_btn.pack(side=tk.RIGHT, padx=1)
    app.max_btn.bind("<Enter>", lambda e: e.widget.configure(bg=t["cyan_dim"], fg=t["cyan"]))
    app.max_btn.bind("<Leave>", lambda e: e.widget.configure(bg=t["bg_secondary"], fg=t["fg"]))

    min_btn = tk.Button(toolbar, text="\u2012", command=app._minimize_window, **btn_style)
    min_btn.pack(side=tk.RIGHT, padx=1)
    min_btn.bind("<Enter>", lambda e: e.widget.configure(bg=t["cyan_dim"], fg=t["cyan"]))
    min_btn.bind("<Leave>", lambda e: e.widget.configure(bg=t["bg_secondary"], fg=t["fg"]))

    # Separator before window controls
    ttk.Separator(toolbar, orient=tk.VERTICAL).pack(side=tk.RIGHT, fill=tk.Y, padx=8)

    # Clear button (rightmost before window controls)
    app._clear_btn = animations.create_gradient_button(
        app, toolbar, "Clear", app.clear_search
    )
    app._clear_btn.pack(side=tk.RIGHT, padx=2)

    # Filter entry
    app.search_var = tk.StringVar()
    app.search_var.trace_add("write", app._on_search_changed)
    app.search_entry = ttk.Entry(toolbar, textvariable=app.search_var, width=25)
    app.search_entry.pack(side=tk.RIGHT, padx=2)
    ttk.Label(toolbar, text="Filter:").pack(side=tk.RIGHT, padx=(5, 5))

    # Settings button (left of Filter)
    app._settings_btn = tk.Label(
        toolbar, text="\u2699 SETTINGS",
        bg=t["bg_tertiary"], fg=t["cyan"],
        font=("Consolas", 9), padx=8, pady=2, cursor="hand2"
    )
    app._settings_btn.pack(side=tk.RIGHT, padx=(5, 10))
    app._settings_btn.bind("<Button-1>", lambda e: show_settings_menu(app, e))
    app._settings_btn.bind("<Enter>", lambda e: e.widget.configure(fg=t["magenta"]))
    app._settings_btn.bind("<Leave>", lambda e: e.widget.configure(fg=t["cyan"]))

    # Separator after left buttons
    ttk.Separator(toolbar, orient=tk.VERTICAL).pack(side=tk.RIGHT, fill=tk.Y, padx=8)

    # Bind resize to redraw gradient
    toolbar_container.bind("<Configure>", lambda e: on_toolbar_configure(app, e))


def on_toolbar_configure(app, event):
    """Redraw toolbar gradient on resize."""
    w = event.width
    h = event.height
    if w < 10 or h < 2:
        return
    photo = animations.create_gradient_image(app, w, h, "#0a1028", "#280a18", cache_key="toolbar_grad")
    if photo:
        app._toolbar_canvas.delete("all")
        app._toolbar_canvas.create_image(0, 0, anchor=tk.NW, image=photo)


def draw_panel_header(app, canvas, text, color1, color2, cache_key):
    """Draw a gradient background and centered text on a panel header canvas."""
    w = canvas.winfo_width()
    h = canvas.winfo_height()
    if w < 10 or h < 2:
        return
    photo = animations.create_gradient_image(app, w, h, color1, color2, cache_key=cache_key)
    if photo:
        canvas.delete("all")
        canvas.create_image(0, 0, anchor=tk.NW, image=photo, tags="bg")
        canvas.create_text(
            w // 2, h // 2, text=text, fill=DARK_THEME["cyan"],
            font=("Consolas", 9, "bold"), anchor=tk.CENTER, tags="header_text"
        )


def build_ticker(app):
    """Build the scrolling ticker tape banner."""
    app.ticker_frame = ttk.Frame(app.root, height=28)
    app.ticker_frame.pack(side=tk.TOP, fill=tk.X, padx=5)
    app.ticker_frame.pack_propagate(False)

    app.ticker_canvas = tk.Canvas(
        app.ticker_frame,
        height=28,
        bg=DARK_THEME["bg_secondary"],
        highlightthickness=1,
        highlightbackground=DARK_THEME["cyan_dim"],
    )
    app.ticker_canvas.pack(fill=tk.BOTH, expand=True)

    # Bind events
    app.ticker_canvas.bind("<Enter>", lambda e: app._ticker_set_paused(True))
    app.ticker_canvas.bind("<Leave>", lambda e: app._ticker_set_paused(False))
    app.ticker_canvas.bind("<Button-1>", app._on_ticker_click)
    app.ticker_canvas.bind("<Double-1>", app._on_ticker_double_click)
    app.ticker_canvas.bind("<Motion>", app._on_ticker_motion)
    app.ticker_canvas.bind("<Configure>", app._on_ticker_configure)


def build_main_layout(app):
    """Build the main paned layout."""
    # Main paned window
    app.main_paned = tk.PanedWindow(
        app.root, orient=tk.HORIZONTAL, sashwidth=4,
        bg=DARK_THEME["bg"], bd=0, relief=tk.FLAT,
        showhandle=False, opaqueresize=True
    )
    app.main_paned.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

    # Left panel - Feed list
    build_feeds_panel(app)

    # Right panel - Articles and preview
    build_articles_panel(app)

    # Set preview pane to 45% of vertical space after window is fully laid out
    def _set_initial_sash():
        try:
            app.right_paned.update_idletasks()
            h = app.right_paned.winfo_height()
            if h > 50:
                app.right_paned.sashpos(0, int(h * 0.55))
        except Exception:
            pass

    app.root.after(200, _set_initial_sash)


def build_feeds_panel(app):
    """Build the feeds list panel."""
    app.feeds_frame = tk.LabelFrame(
        app.main_paned, text="",
        bg=DARK_THEME["bg"], fg=DARK_THEME["cyan"],
        font=("Consolas", 10, "bold"),
        highlightbackground=DARK_THEME["cyan_dim"],
        highlightcolor=DARK_THEME["cyan"],
        highlightthickness=2, bd=0, relief=tk.FLAT,
        padx=5, pady=5
    )
    feeds_frame = app.feeds_frame
    app.main_paned.add(feeds_frame, minsize=280, sticky="nsew")

    # Gradient header bar
    app._feeds_header = tk.Canvas(feeds_frame, height=20, highlightthickness=0,
                                    bg=DARK_THEME["bg_secondary"])
    app._feeds_header.pack(fill=tk.X, pady=(0, 3))
    app._feeds_header.bind("<Configure>", lambda e: draw_panel_header(
        app, app._feeds_header, "FEEDS", "#0a1028", "#1a0a20", "feeds_hdr"))

    # Branding at bottom (pack first so it stays at bottom)
    branding_frame = tk.Frame(feeds_frame, bg=DARK_THEME["bg"])
    branding_frame.pack(side=tk.BOTTOM, fill=tk.X, pady=(5, 0))

    # Load logo (use taskbar icon) - clickable link to Patreon
    try:
        logo_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "icon_preview.png")
        app._logo_image = tk.PhotoImage(file=logo_path)
        w, h = app._logo_image.width(), app._logo_image.height()
        if h > 28:
            factor = max(1, h // 28)
            app._logo_image = app._logo_image.subsample(factor, factor)
        logo_label = tk.Label(branding_frame, image=app._logo_image, bg=DARK_THEME["bg"], cursor="hand2")
        logo_label.pack(side=tk.LEFT, padx=(0, 6))
        logo_label.bind("<Button-1>", lambda e: webbrowser.open("https://www.patreon.com/kcbowlan"))
        logo_label.bind("<Enter>", lambda e: window_mgmt.show_logo_tooltip(app, e))
        logo_label.bind("<Leave>", lambda e: window_mgmt.hide_logo_tooltip(app, e))
    except Exception:
        pass

    # Large WIREFEEDR text with chromatic aberration (canvas-based 3-layer text)
    title_font = ("Consolas", 16, "bold")
    fobj = tkfont.Font(family="Consolas", size=16, weight="bold")
    tw = fobj.measure("WIREFEEDR")
    th = fobj.metrics("linespace")
    cw = tw + 8
    ch = th + 4
    app._title_canvas = tk.Canvas(
        branding_frame, width=cw, height=ch,
        bg=DARK_THEME["bg"], highlightthickness=0
    )
    app._title_canvas.pack(side=tk.LEFT)
    cx = cw // 2
    cy = ch // 2
    # Red/magenta shadow — offset left 2px (drawn first = lowest layer)
    app._title_ab_red = app._title_canvas.create_text(
        cx - 2, cy, text="WIREFEEDR",
        fill=DARK_THEME["magenta_dim"], font=title_font, anchor=tk.CENTER
    )
    # Cyan shadow — offset right 2px
    app._title_ab_cyan = app._title_canvas.create_text(
        cx + 2, cy, text="WIREFEEDR",
        fill=DARK_THEME["cyan_dim"], font=title_font, anchor=tk.CENTER
    )
    # Main text on top (drawn last = topmost layer)
    app._title_main = app._title_canvas.create_text(
        cx, cy, text="WIREFEEDR",
        fill=DARK_THEME["cyan"], font=title_font, anchor=tk.CENTER
    )

    tk.Label(
        branding_frame, text="v2.1",
        bg=DARK_THEME["bg"], fg=DARK_THEME["fg_secondary"],
        font=("Consolas", 9)
    ).pack(side=tk.LEFT, padx=(4, 0), pady=(8, 0))

    # Feeds treeview in capped-height container
    feeds_tree_container = tk.Frame(feeds_frame, bg=DARK_THEME["bg"], height=200)
    feeds_tree_container.pack(fill=tk.X)
    feeds_tree_container.pack_propagate(False)

    app.feeds_tree = ttk.Treeview(feeds_tree_container, selectmode="browse", show="tree")
    app.feeds_tree.pack(fill=tk.BOTH, expand=True, side=tk.LEFT)

    feeds_scroll = ttk.Scrollbar(feeds_tree_container, orient=tk.VERTICAL, command=app.feeds_tree.yview)
    feeds_scroll.pack(side=tk.RIGHT, fill=tk.Y)
    app.feeds_tree.configure(yscrollcommand=feeds_scroll.set)

    app.feeds_tree.bind("<<TreeviewSelect>>", app._on_feed_select)
    app.feeds_tree.bind("<Button-3>", app._on_feed_right_click)
    app.feeds_tree.bind("<Motion>", app._on_feed_hover)
    app.feeds_tree.bind("<Leave>", app._on_feed_leave)

    # Tag styles for flat grouped feeds list
    app.feeds_tree.tag_configure("all_item", foreground=DARK_THEME["cyan"],
                                 font=("Consolas", 10, "bold"))
    app.feeds_tree.tag_configure("cat_divider", foreground=DARK_THEME["cyan_dim"],
                                 font=("Consolas", 8),
                                 background=DARK_THEME["bg_secondary"])
    app.feeds_tree.tag_configure("feed_item", foreground=DARK_THEME["fg_secondary"],
                                 font=("Consolas", 9))
    app.feeds_tree.tag_configure("feed_unread", foreground=DARK_THEME["magenta_dim"],
                                 font=("Consolas", 9, "bold"))
    app.feeds_tree.tag_configure("hover", background="#1a1a2e")

    # --- Bias Balance Bar ---
    tk.Label(feeds_frame, text="PERSONAL FEED BIAS", bg=DARK_THEME["bg"],
             fg=DARK_THEME["cyan"], font=("Consolas", 8, "bold")
    ).pack(fill=tk.X, pady=(6, 1))

    app._bias_canvas = tk.Canvas(feeds_frame, height=30, highlightthickness=0,
                                   bg=DARK_THEME["bg_secondary"])
    app._bias_canvas.pack(fill=tk.X, pady=(0, 4))
    app._bias_canvas.bind("<Configure>", lambda e: app._update_bias_balance())

    # --- Trending Topics ---
    trending_hdr_row = tk.Frame(feeds_frame, bg=DARK_THEME["bg"])
    trending_hdr_row.pack(fill=tk.X, pady=(2, 0))

    app._trending_header = tk.Canvas(trending_hdr_row, height=16, highlightthickness=0,
                                       bg=DARK_THEME["bg_secondary"])
    app._trending_header.pack(side=tk.LEFT, fill=tk.X, expand=True)
    app._trending_header.bind("<Configure>", lambda e: draw_panel_header(
        app, app._trending_header, "TRENDING", "#0a1028", "#1a0a20", "trend_hdr"))

    refresh_btn = tk.Label(
        trending_hdr_row, text="\u21bb", bg=DARK_THEME["bg_secondary"],
        fg=DARK_THEME["cyan_dim"], font=("Consolas", 11), cursor="hand2", padx=4
    )
    refresh_btn.pack(side=tk.RIGHT, fill=tk.Y)
    refresh_btn.bind("<Button-1>", lambda e: app._flip_all_trending())
    refresh_btn.bind("<Enter>", lambda e: refresh_btn.configure(fg=DARK_THEME["cyan"]))
    refresh_btn.bind("<Leave>", lambda e: refresh_btn.configure(fg=DARK_THEME["cyan_dim"]))

    app._trending_frame = tk.Frame(feeds_frame, bg=DARK_THEME["bg"])
    app._trending_frame.pack(fill=tk.BOTH, expand=True, pady=(2, 0))

    app._trending_canvas = tk.Canvas(
        app._trending_frame, bg=DARK_THEME["bg"],
        borderwidth=0, highlightthickness=0
    )
    app._trending_canvas.pack(fill=tk.BOTH, expand=True)
    app._trending_canvas.bind("<Configure>", lambda e: app._layout_trending_slots())
    app._trending_pool = []       # full ordered word list
    app._trending_slots = []      # visible slot dicts
    app._trending_pool_idx = 0    # next word to pull from pool
    app._trending_intervals = [900, 1800, 9000]  # 30s, 1m, 5m in frames
    app._trending_interval_idx = 0
    app._trending_next_flip = 0   # anim_frame when next board-wide flip fires


def build_articles_panel(app):
    """Build the articles and preview panel."""
    app.right_paned = ttk.PanedWindow(app.main_paned, orient=tk.VERTICAL)
    right_paned = app.right_paned
    app.main_paned.add(right_paned, sticky="nsew")

    # Articles list
    app.articles_frame = tk.LabelFrame(
        right_paned, text="",
        bg=DARK_THEME["bg"], fg=DARK_THEME["cyan"],
        font=("Consolas", 10, "bold"),
        highlightbackground=DARK_THEME["cyan_dim"],
        highlightcolor=DARK_THEME["cyan"],
        highlightthickness=2, bd=0, relief=tk.FLAT,
        padx=5, pady=5
    )
    articles_frame = app.articles_frame
    right_paned.add(articles_frame, weight=55)

    # Gradient header bar
    app._articles_header = tk.Canvas(articles_frame, height=20, highlightthickness=0,
                                       bg=DARK_THEME["bg_secondary"])
    app._articles_header.pack(fill=tk.X, pady=(0, 3))
    app._articles_header.bind("<Configure>", lambda e: draw_panel_header(
        app, app._articles_header, "ARTICLES", "#0a1028", "#1a0a20", "articles_hdr"))

    # Tab bar (ALL / FAVORITES)
    t = DARK_THEME
    app._articles_tab = "all"
    tab_frame = tk.Frame(articles_frame, bg=t["bg"])
    tab_frame.pack(fill=tk.X, pady=(0, 3))

    app._tab_all = tk.Label(
        tab_frame, text="ALL", bg=t["bg"], fg=t["cyan"],
        font=("Consolas", 9, "bold"), padx=12, pady=2, cursor="hand2"
    )
    app._tab_all.pack(side=tk.LEFT)

    app._tab_fav = tk.Label(
        tab_frame, text="FAVORITES (0)", bg=t["bg"], fg=t["fg_secondary"],
        font=("Consolas", 9), padx=12, pady=2, cursor="hand2"
    )
    app._tab_fav.pack(side=tk.LEFT)

    # Underline canvases for active tab indicator
    app._tab_all_line = tk.Canvas(tab_frame, height=2, bg=t["cyan"],
                                   highlightthickness=0, width=40)
    app._tab_all_line.place(in_=app._tab_all, relx=0, rely=1.0,
                             relwidth=1.0, height=2)
    app._tab_fav_line = tk.Canvas(tab_frame, height=2, bg=t["bg"],
                                   highlightthickness=0, width=40)
    app._tab_fav_line.place(in_=app._tab_fav, relx=0, rely=1.0,
                             relwidth=1.0, height=2)

    def switch_tab(tab_name):
        app._articles_tab = tab_name
        if tab_name == "all":
            app._tab_all.configure(fg=t["cyan"], font=("Consolas", 9, "bold"))
            app._tab_fav.configure(fg=t["fg_secondary"], font=("Consolas", 9))
            app._tab_all_line.configure(bg=t["cyan"])
            app._tab_fav_line.configure(bg=t["bg"])
        else:
            app._tab_all.configure(fg=t["fg_secondary"], font=("Consolas", 9))
            app._tab_fav.configure(fg=t["cyan"], font=("Consolas", 9, "bold"))
            app._tab_all_line.configure(bg=t["bg"])
            app._tab_fav_line.configure(bg=t["cyan"])
        app.refresh_articles()

    app._tab_all.bind("<Button-1>", lambda e: switch_tab("all"))
    app._tab_fav.bind("<Button-1>", lambda e: switch_tab("favorites"))

    # Hover effects on tabs
    app._tab_all.bind("<Enter>", lambda e: e.widget.configure(
        fg=t["magenta"] if app._articles_tab != "all" else t["cyan"]))
    app._tab_all.bind("<Leave>", lambda e: e.widget.configure(
        fg=t["cyan"] if app._articles_tab == "all" else t["fg_secondary"]))
    app._tab_fav.bind("<Enter>", lambda e: e.widget.configure(
        fg=t["magenta"] if app._articles_tab != "favorites" else t["cyan"]))
    app._tab_fav.bind("<Leave>", lambda e: e.widget.configure(
        fg=t["cyan"] if app._articles_tab == "favorites" else t["fg_secondary"]))

    # Articles treeview with columns
    columns = ("fav", "title", "source", "bias", "date", "noise")
    app.articles_tree = ttk.Treeview(articles_frame, columns=columns, show="headings",
                                      selectmode="browse", height=10)

    app.articles_tree.heading("fav", text="\u25c6", anchor=tk.CENTER)
    app.articles_tree.heading("title", text="Title", anchor=tk.W)
    app.articles_tree.heading("source", text="Source", anchor=tk.W)
    app.articles_tree.heading("bias", text="Bias", anchor=tk.CENTER)
    app.articles_tree.heading("date", text="Date", anchor=tk.W)
    app.articles_tree.heading("noise", text="Score", anchor=tk.CENTER)

    app.articles_tree.column("fav", width=30, minwidth=30, stretch=False)
    app.articles_tree.column("title", width=400, minwidth=200)
    app.articles_tree.column("source", width=120, minwidth=80)
    app.articles_tree.column("bias", width=90, minwidth=60)
    app.articles_tree.column("date", width=120, minwidth=80)
    app.articles_tree.column("noise", width=100, minwidth=80)

    app.articles_tree.pack(fill=tk.BOTH, expand=True, side=tk.LEFT)

    articles_scroll = ttk.Scrollbar(articles_frame, orient=tk.VERTICAL,
                                     command=app.articles_tree.yview)
    articles_scroll.pack(side=tk.RIGHT, fill=tk.Y)
    app.articles_tree.configure(yscrollcommand=articles_scroll.set)

    app.articles_tree.bind("<<TreeviewSelect>>", app._on_article_select)
    app.articles_tree.bind("<Button-1>", app._on_article_click)
    app.articles_tree.bind("<Double-1>", app._on_article_double_click)
    app.articles_tree.bind("<Button-3>", app._on_article_right_click)
    # Arrow key navigation - bound to tree to prevent default double-movement
    app.articles_tree.bind("<Up>", app._on_key_up)
    app.articles_tree.bind("<Down>", app._on_key_down)

    # Configure tags for read/unread styling
    app.articles_tree.tag_configure("unread", font=("TkDefaultFont", 9, "bold"),
                                      foreground=DARK_THEME["fg"])
    app.articles_tree.tag_configure("read", foreground=DARK_THEME["fg_secondary"])
    app.articles_tree.tag_configure("favorite", foreground=DARK_THEME["cyan"])
    app.articles_tree.tag_configure("hover", background="#1a1a2e")

    # Hover glow on article rows
    app.articles_tree.bind("<Motion>", app._on_article_hover)
    app.articles_tree.bind("<Leave>", app._on_article_leave)

    # Preview panel
    app.preview_frame = tk.LabelFrame(
        right_paned, text="",
        bg=DARK_THEME["bg"], fg=DARK_THEME["magenta"],
        font=("Consolas", 10, "bold"),
        highlightbackground=DARK_THEME["magenta_dim"],
        highlightcolor=DARK_THEME["magenta"],
        highlightthickness=2, bd=0, relief=tk.FLAT,
        padx=5, pady=5
    )
    preview_frame = app.preview_frame
    right_paned.add(preview_frame, weight=45)

    # Gradient header bar (magenta-tinted for preview)
    app._preview_header = tk.Canvas(preview_frame, height=20, highlightthickness=0,
                                      bg=DARK_THEME["bg_secondary"])
    app._preview_header.pack(fill=tk.X, pady=(0, 3))
    app._preview_header.bind("<Configure>", lambda e: draw_panel_header(
        app, app._preview_header, "PREVIEW", "#1a0a28", "#280a18", "preview_hdr"))

    # Sash flash bindings
    for paned in [app.main_paned, app.right_paned]:
        paned.bind("<ButtonPress-1>", app._on_sash_press)
        paned.bind("<ButtonRelease-1>", app._on_sash_release)

    # Preview header
    header_frame = ttk.Frame(preview_frame)
    header_frame.pack(fill=tk.X, pady=(0, 5))

    app.preview_title = ttk.Label(header_frame, text="", font=("TkDefaultFont", 11, "bold"),
                                    wraplength=500)
    app.preview_title.pack(side=tk.LEFT, fill=tk.X, expand=True)

    # Buttons frame
    btn_frame = ttk.Frame(header_frame)
    btn_frame.pack(side=tk.RIGHT)

    # Search Author dropdown menu
    app.author_menu_btn = ttk.Menubutton(btn_frame, text="Search Author",
                                            direction="below")
    app.author_menu = tk.Menu(app.author_menu_btn, tearoff=0,
                                bg=DARK_THEME["bg_secondary"], fg=DARK_THEME["fg"],
                                activebackground=DARK_THEME["magenta"],
                                activeforeground=DARK_THEME["fg_highlight"])
    app.author_menu_btn.configure(menu=app.author_menu)
    app.author_menu.add_command(label="Google", command=lambda: app._search_author("google"))
    app.author_menu.add_command(label="LinkedIn", command=lambda: app._search_author("linkedin"))
    app.author_menu.add_command(label="Wikipedia", command=lambda: app._search_author("wikipedia"))
    app.author_menu.add_command(label="Twitter/X", command=lambda: app._search_author("twitter"))
    app.author_menu_btn.pack(side=tk.LEFT, padx=2)
    app.author_menu_btn.configure(state=tk.DISABLED)

    app.open_btn = animations.create_gradient_button(
        app, btn_frame, "Open in Browser", app.open_in_browser, disabled=True
    )
    app.open_btn.pack(side=tk.LEFT, padx=2)

    # Bias info frame (colored labels)
    bias_frame = ttk.Frame(preview_frame)
    bias_frame.pack(fill=tk.X, pady=(0, 5))

    ttk.Label(bias_frame, text="Source Bias:", font=("TkDefaultFont", 9)).pack(side=tk.LEFT)
    app.bias_label = tk.Label(bias_frame, text="", font=("TkDefaultFont", 9, "bold"),
                                bg=DARK_THEME["bg"], padx=8, pady=2)
    app.bias_label.pack(side=tk.LEFT, padx=5)

    ttk.Label(bias_frame, text="Factual Rating:", font=("TkDefaultFont", 9)).pack(side=tk.LEFT, padx=(10, 0))
    app.factual_label = tk.Label(bias_frame, text="", font=("TkDefaultFont", 9, "bold"),
                                   bg=DARK_THEME["bg"], padx=8, pady=2)
    app.factual_label.pack(side=tk.LEFT, padx=5)

    # Preview meta info
    app.preview_meta = ttk.Label(preview_frame, text="", foreground=DARK_THEME["fg_secondary"])
    app.preview_meta.pack(fill=tk.X)

    # Preview text with scrollbar (scrollbar must be packed first to appear on right)
    preview_text_scroll = ttk.Scrollbar(preview_frame, orient=tk.VERTICAL)
    preview_text_scroll.pack(side=tk.RIGHT, fill=tk.Y, pady=5)

    app.preview_text = tk.Text(preview_frame, wrap=tk.WORD, height=8, state=tk.DISABLED,
                                 bg=DARK_THEME["bg_tertiary"], fg=DARK_THEME["fg"],
                                 insertbackground=DARK_THEME["cyan"],
                                 relief=tk.FLAT, padx=10, pady=10,
                                 yscrollcommand=preview_text_scroll.set)
    app.preview_text.pack(fill=tk.BOTH, expand=True, pady=5)

    preview_text_scroll.configure(command=app.preview_text.yview)

    # Rain canvas (overlays preview_text for matrix rain placeholder)
    app._rain_canvas = tk.Canvas(app.preview_frame, bg=DARK_THEME["bg_tertiary"], highlightthickness=0)
    app._rain_canvas.bind("<Configure>", lambda e: animations.on_rain_configure(app, e))

    # Configure semantic highlighting tags
    import highlighting
    highlighting.setup_highlight_tags(app)

    # Show empty-state placeholder
    show_preview_placeholder(app)


def show_preview_placeholder(app):
    """Display matrix rain placeholder when no article is selected."""
    app.preview_title.configure(text="")
    app.bias_label.configure(text="", bg=DARK_THEME["bg_tertiary"])
    app.factual_label.configure(text="", bg=DARK_THEME["bg_tertiary"])
    app.preview_meta.configure(text="")

    # Clear the text widget
    pw = app.preview_text
    pw.configure(state=tk.NORMAL)
    pw.delete("1.0", tk.END)
    pw.configure(state=tk.DISABLED)

    # Place rain canvas over preview_text
    if app._rain_canvas:
        app._rain_canvas.delete("all")
        app._rain_canvas.place(in_=app.preview_text, relx=0, rely=0, relwidth=1, relheight=1)
        app._rain_active = True
        app._rain_columns = []
        # Draw placeholder text on canvas
        animations._draw_rain_placeholder_text(app)


def build_status_bar(app):
    """Build the cyberpunk status bar."""
    t = DARK_THEME
    status_frame = tk.Frame(app.root, bg=t["status_bg"], height=24)
    status_frame.pack(side=tk.BOTTOM, fill=tk.X)
    status_frame.pack_propagate(False)

    # Left: Cyberpunk progress bar (segmented blocks with gradient)
    app._progress_frame = tk.Frame(status_frame, bg=t["status_bg"])
    app._progress_frame.pack(side=tk.LEFT, padx=(8, 0))

    # Progress bar canvas (20 segments, wider)
    app._progress_segments = 20
    app._progress_seg_width = 12
    app._progress_seg_height = 12
    app._progress_gap = 2
    canvas_width = app._progress_segments * (app._progress_seg_width + app._progress_gap)
    app._progress_canvas = tk.Canvas(
        app._progress_frame, width=canvas_width, height=app._progress_seg_height,
        bg=t["status_bg"], highlightthickness=0
    )
    app._progress_canvas.pack(side=tk.LEFT, pady=6)

    # Create segment rectangles
    app._progress_rects = []
    for i in range(app._progress_segments):
        x = i * (app._progress_seg_width + app._progress_gap)
        rect = app._progress_canvas.create_rectangle(
            x, 0, x + app._progress_seg_width, app._progress_seg_height,
            fill=t["bg_tertiary"], outline=""
        )
        app._progress_rects.append(rect)

    # Progress percentage label
    app._progress_label = tk.Label(
        app._progress_frame, text="",
        bg=t["status_bg"], fg=t["cyan"],
        font=("Consolas", 9)
    )
    app._progress_label.pack(side=tk.LEFT, padx=(4, 0))

    # Hide progress bar initially
    app._progress_frame.pack_forget()
    app._progress_value = 0

    # Blinking block cursor (pack first so it's on far right)
    app._cursor_label = tk.Label(
        status_frame, text="\u2588",
        bg=t["status_bg"], fg=t["cyan"],
        font=("Consolas", 12)  # Larger for chunky look
    )
    app._cursor_label.pack(side=tk.RIGHT, padx=(0, 20))

    # Right-aligned status text (to left of cursor)
    app.status_bar = tk.Label(
        status_frame, text="", anchor=tk.E,
        bg=t["status_bg"], fg=t["cyan"],
        font=("Consolas", 9)
    )
    app.status_bar.pack(side=tk.RIGHT, padx=(8, 0))


def show_progress(app):
    """Show the progress bar."""
    app._progress_frame.pack(side=tk.LEFT, padx=(8, 0))
    app._progress_value = 0
    update_progress(app, 0)


def hide_progress(app):
    """Hide the progress bar."""
    app._progress_frame.pack_forget()


def update_progress(app, percent):
    """Update progress bar with gradient fill (magenta -> cyan)."""
    t = DARK_THEME
    app._progress_value = percent
    filled = int((percent / 100) * app._progress_segments)

    for i, rect in enumerate(app._progress_rects):
        if i < filled:
            # Gradient from magenta to cyan based on position
            ratio = i / max(app._progress_segments - 1, 1)
            color = animations.lerp_color(t["magenta"], t["cyan"], ratio)
            app._progress_canvas.itemconfigure(rect, fill=color)
        else:
            # Empty segment
            app._progress_canvas.itemconfigure(rect, fill=t["bg_tertiary"])

    # Update percentage text
    app._progress_label.configure(text=f"{int(percent)}%")
