# app.py - Tkinter GUI

import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
import webbrowser
import threading
from datetime import datetime
from typing import Optional
from urllib.parse import urlparse
import io

from storage import Storage
from feeds import FeedManager
from filters import FilterEngine
from config import BIAS_COLORS, FACTUAL_COLORS, DARK_THEME


class NewsAggregatorApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("Personal News Aggregator")
        self.root.geometry("1200x700")
        self.root.minsize(900, 500)

        # Initialize components
        self.storage = Storage()
        self.feed_manager = FeedManager()
        self.filter_engine = FilterEngine(self.storage.get_filter_keywords())

        # State
        self.current_feed_id = None  # None = All feeds
        self.selected_article_id = None
        self.current_author_url = None
        self.is_fetching = False
        self.auto_refresh_job = None
        self.cluster_map = {}  # Maps article_id -> cluster info for expanding
        self.feed_icons = {}  # Cache for PhotoImage objects

        # Ticker state
        self.ticker_canvas = None
        self.ticker_frame = None
        self.ticker_canvas_to_article = {}  # canvas item ID -> article ID
        self.ticker_offset = 0
        self.ticker_total_width = 0
        self.ticker_paused = False
        self.ticker_animation_id = None
        self.ticker_speed = 2
        self._ticker_resize_job = None

        # Build UI
        self._setup_styles()
        self._build_menu()
        self._build_toolbar()
        self._build_ticker()
        self._build_main_layout()
        self._build_status_bar()

        # Load initial data
        self.refresh_feeds_list()
        self.refresh_articles()

        # Start auto-refresh if enabled
        self._schedule_auto_refresh()

        # Bind window close
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

    def _setup_styles(self):
        """Configure ttk styles with dark cyberpunk theme."""
        self.root.configure(bg=DARK_THEME["bg"])

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

        # Scrollbar
        style.configure("TScrollbar", background=t["bg_secondary"], troughcolor=t["bg"],
                         arrowcolor=t["cyan"])
        style.map("TScrollbar",
                  background=[("active", t["magenta"]), ("pressed", t["magenta_dim"])],
                  arrowcolor=[("active", t["magenta"])])

        # Menubutton
        style.configure("TMenubutton", background=t["bg_tertiary"], foreground=t["cyan"])
        style.map("TMenubutton",
                  background=[("active", t["magenta"])],
                  foreground=[("active", t["fg_highlight"])])

        # Entry
        style.configure("TEntry", fieldbackground=t["bg_tertiary"], foreground=t["fg"],
                         bordercolor=t["cyan_dim"], lightcolor=t["bg_tertiary"],
                         darkcolor=t["bg_tertiary"], insertcolor=t["cyan"])

        # Spinbox
        style.configure("TSpinbox", fieldbackground=t["bg_tertiary"], foreground=t["fg"],
                         background=t["bg_tertiary"])

        style.configure("Toolbutton", padding=5)

        # Style combobox dropdown popdown (tk.Listbox inside)
        self.root.option_add("*TCombobox*Listbox.background", t["bg_tertiary"])
        self.root.option_add("*TCombobox*Listbox.foreground", t["fg"])
        self.root.option_add("*TCombobox*Listbox.selectBackground", t["magenta"])
        self.root.option_add("*TCombobox*Listbox.selectForeground", t["fg_highlight"])

    def _build_menu(self):
        """Build the menu bar."""
        _m = dict(bg=DARK_THEME["bg_secondary"], fg=DARK_THEME["fg"],
                  activebackground=DARK_THEME["magenta"], activeforeground=DARK_THEME["fg_highlight"])
        menubar = tk.Menu(self.root, **_m)
        self.root.config(menu=menubar)

        # File menu
        file_menu = tk.Menu(menubar, tearoff=0, **_m)
        menubar.add_cascade(label="File", menu=file_menu)
        file_menu.add_command(label="Refresh All Feeds", command=self.fetch_all_feeds,
                              accelerator="F5")
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self._on_close)

        # Feeds menu
        feeds_menu = tk.Menu(menubar, tearoff=0, **_m)
        menubar.add_cascade(label="Feeds", menu=feeds_menu)
        feeds_menu.add_command(label="Add Feed...", command=self.show_add_feed_dialog)
        feeds_menu.add_command(label="Manage Feeds...", command=self.show_manage_feeds_dialog)

        # Articles menu
        articles_menu = tk.Menu(menubar, tearoff=0, **_m)
        menubar.add_cascade(label="Articles", menu=articles_menu)
        articles_menu.add_command(label="Mark All as Read", command=self.mark_all_read)
        articles_menu.add_separator()
        articles_menu.add_command(label="Delete Old Articles...", command=self.show_delete_old_dialog)

        # Settings menu
        settings_menu = tk.Menu(menubar, tearoff=0, **_m)
        menubar.add_cascade(label="Settings", menu=settings_menu)
        settings_menu.add_command(label="Filter Keywords...", command=self.show_filter_keywords_dialog)

        # Bind keyboard shortcuts
        self.root.bind("<F5>", lambda e: self.fetch_all_feeds())

        # Article navigation shortcuts
        self.root.bind("<Up>", self._on_key_up)
        self.root.bind("<Down>", self._on_key_down)
        self.root.bind("<Return>", lambda e: self.open_in_browser())
        self.root.bind("m", self._on_key_toggle_read)
        self.root.bind("M", self._on_key_toggle_read)
        self.root.bind("h", self._on_key_hide)
        self.root.bind("H", self._on_key_hide)

    def _build_toolbar(self):
        """Build the toolbar."""
        toolbar = ttk.Frame(self.root)
        toolbar.pack(side=tk.TOP, fill=tk.X, padx=5, pady=5)

        # Refresh button
        self.refresh_btn = ttk.Button(toolbar, text="↻ Refresh", command=self.fetch_all_feeds)
        self.refresh_btn.pack(side=tk.LEFT, padx=2)

        # Mark all read button
        ttk.Button(toolbar, text="✓ Mark All Read", command=self.mark_all_read).pack(side=tk.LEFT, padx=2)

        # Separator
        ttk.Separator(toolbar, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=10)

        # Show read articles checkbox
        self.show_read_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(toolbar, text="Show Read", variable=self.show_read_var,
                        command=self.refresh_articles).pack(side=tk.LEFT, padx=5)

        # Recency filter dropdown
        ttk.Label(toolbar, text="Recency:").pack(side=tk.LEFT, padx=(20, 5))
        self.recency_var = tk.StringVar(value=self.storage.get_setting("recency_hours", "24"))
        recency_options = [("6h", "6"), ("12h", "12"), ("24h", "24"), ("48h", "48"), ("Week", "168"), ("All", "0")]
        self.recency_combo = ttk.Combobox(toolbar, textvariable=self.recency_var, width=6, state="readonly",
                                          values=[opt[0] for opt in recency_options])
        # Set display value from stored hours
        recency_map = {"6": "6h", "12": "12h", "24": "24h", "48": "48h", "168": "Week", "0": "All"}
        self.recency_combo.set(recency_map.get(self.recency_var.get(), "24h"))
        self.recency_combo.pack(side=tk.LEFT, padx=2)
        self.recency_combo.bind("<<ComboboxSelected>>", self._on_recency_change)
        self._recency_options = dict(recency_options)

        # Per Source cap dropdown
        ttk.Label(toolbar, text="Per Source:").pack(side=tk.LEFT, padx=(10, 5))
        self.per_source_var = tk.StringVar(value=self.storage.get_setting("max_per_source", "10"))
        per_source_options = [("5", "5"), ("10", "10"), ("15", "15"), ("20", "20"), ("No Limit", "0")]
        self.per_source_combo = ttk.Combobox(toolbar, textvariable=self.per_source_var, width=8, state="readonly",
                                              values=[opt[0] for opt in per_source_options])
        per_source_map = {"5": "5", "10": "10", "15": "15", "20": "20", "0": "No Limit"}
        self.per_source_combo.set(per_source_map.get(self.per_source_var.get(), "10"))
        self.per_source_combo.pack(side=tk.LEFT, padx=2)
        self.per_source_combo.bind("<<ComboboxSelected>>", self._on_per_source_change)
        self._per_source_options = dict(per_source_options)

        # Cluster toggle
        self.cluster_var = tk.BooleanVar(value=self.storage.get_setting("cluster_topics", "True") == "True")
        ttk.Checkbutton(toolbar, text="Cluster", variable=self.cluster_var,
                        command=self._on_cluster_toggle).pack(side=tk.LEFT, padx=(10, 5))

        # Search
        ttk.Label(toolbar, text="Search:").pack(side=tk.LEFT, padx=(20, 5))
        self.search_var = tk.StringVar()
        self.search_entry = ttk.Entry(toolbar, textvariable=self.search_var, width=20)
        self.search_entry.pack(side=tk.LEFT, padx=2)
        self.search_entry.bind("<Return>", lambda e: self.search_articles())
        ttk.Button(toolbar, text="Go", command=self.search_articles, width=4).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="Clear", command=self.clear_search, width=5).pack(side=tk.LEFT, padx=2)

    def _build_ticker(self):
        """Build the scrolling ticker tape banner."""
        self.ticker_frame = ttk.Frame(self.root, height=28)
        self.ticker_frame.pack(side=tk.TOP, fill=tk.X, padx=5)
        self.ticker_frame.pack_propagate(False)

        self.ticker_canvas = tk.Canvas(
            self.ticker_frame,
            height=28,
            bg=DARK_THEME["bg_secondary"],
            highlightthickness=1,
            highlightbackground=DARK_THEME["cyan_dim"],
        )
        self.ticker_canvas.pack(fill=tk.BOTH, expand=True)

        # Bind events
        self.ticker_canvas.bind("<Enter>", lambda e: self._ticker_set_paused(True))
        self.ticker_canvas.bind("<Leave>", lambda e: self._ticker_set_paused(False))
        self.ticker_canvas.bind("<Button-1>", self._on_ticker_click)
        self.ticker_canvas.bind("<Double-1>", self._on_ticker_double_click)
        self.ticker_canvas.bind("<Motion>", self._on_ticker_motion)
        self.ticker_canvas.bind("<Configure>", self._on_ticker_configure)

    def _ticker_set_paused(self, paused):
        """Pause or resume ticker animation."""
        self.ticker_paused = paused
        if not paused:
            # Reset all text colors back to cyan when leaving
            for item_id in self.ticker_canvas.find_withtag("ticker_text"):
                self.ticker_canvas.itemconfigure(item_id, fill=DARK_THEME["cyan"])

    def _on_ticker_configure(self, event):
        """Handle ticker canvas resize with debounce."""
        if self._ticker_resize_job:
            self.root.after_cancel(self._ticker_resize_job)
        self._ticker_resize_job = self.root.after(200, self._update_ticker)

    def _update_ticker(self):
        """Rebuild ticker content from unread articles in the treeview."""
        self.ticker_canvas.delete("all")
        self.ticker_canvas_to_article = {}
        self.ticker_offset = 0

        # Collect unread articles from treeview
        unread_items = []
        for item_id in self.articles_tree.get_children():
            tags = self.articles_tree.item(item_id, "tags")
            if "unread" in tags:
                values = self.articles_tree.item(item_id, "values")
                # values: (title, source, bias, date, score)
                unread_items.append({
                    "article_id": int(item_id),
                    "title": values[0],
                    "source": values[1],
                })

        if not unread_items:
            # Show placeholder
            self.ticker_canvas.create_text(
                self.ticker_canvas.winfo_width() // 2, 14,
                text="No unread articles",
                fill=DARK_THEME["fg_secondary"],
                font=("TkDefaultFont", 9, "italic"),
                anchor=tk.CENTER,
            )
            self._stop_ticker_animation()
            return

        # Build text items — two copies for seamless looping
        separator = "  \u2022  "  # bullet
        x = 0
        font = ("TkDefaultFont", 9)
        copy_positions = []  # track (x_start, article_id) for both copies

        for copy in range(2):
            for i, item in enumerate(unread_items):
                label = f"[{item['source']}]: {item['title']}"
                text_id = self.ticker_canvas.create_text(
                    x, 14,
                    text=label,
                    fill=DARK_THEME["cyan"],
                    font=font,
                    anchor=tk.W,
                    tags="ticker_text",
                )
                self.ticker_canvas_to_article[text_id] = item["article_id"]
                bbox = self.ticker_canvas.bbox(text_id)
                text_width = bbox[2] - bbox[0] if bbox else 100
                x += text_width

                # Add separator (not after last item in second copy)
                if i < len(unread_items) - 1 or copy == 0:
                    sep_id = self.ticker_canvas.create_text(
                        x, 14,
                        text=separator,
                        fill=DARK_THEME["fg_secondary"],
                        font=font,
                        anchor=tk.W,
                        tags="ticker_text",
                    )
                    sep_bbox = self.ticker_canvas.bbox(sep_id)
                    sep_width = sep_bbox[2] - sep_bbox[0] if sep_bbox else 20
                    x += sep_width

            if copy == 0:
                self.ticker_total_width = x

        self._start_ticker_animation()

    def _ticker_animate(self):
        """Move all ticker items left by speed pixels."""
        if not self.ticker_paused and self.ticker_total_width > 0:
            self.ticker_canvas.move("ticker_text", -self.ticker_speed, 0)
            self.ticker_offset += self.ticker_speed

            if self.ticker_offset >= self.ticker_total_width:
                # Reset: shift everything back by one full copy width
                self.ticker_canvas.move("ticker_text", self.ticker_total_width, 0)
                self.ticker_offset -= self.ticker_total_width

        self.ticker_animation_id = self.root.after(33, self._ticker_animate)  # ~30fps

    def _start_ticker_animation(self):
        """Start the ticker animation loop."""
        self._stop_ticker_animation()
        self.ticker_animation_id = self.root.after(33, self._ticker_animate)

    def _stop_ticker_animation(self):
        """Cancel the ticker animation loop."""
        if self.ticker_animation_id:
            self.root.after_cancel(self.ticker_animation_id)
            self.ticker_animation_id = None

    def _on_ticker_click(self, event):
        """Handle single click on ticker — select article in treeview."""
        item_id = self.ticker_canvas.find_closest(event.x, event.y)
        if not item_id:
            return
        item_id = item_id[0]
        article_id = self.ticker_canvas_to_article.get(item_id)
        if article_id is None:
            return

        article_str = str(article_id)
        if self.articles_tree.exists(article_str):
            self.articles_tree.selection_set(article_str)
            self.articles_tree.see(article_str)
            self.articles_tree.event_generate("<<TreeviewSelect>>")

    def _on_ticker_double_click(self, event):
        """Handle double-click on ticker — open article in browser."""
        item_id = self.ticker_canvas.find_closest(event.x, event.y)
        if not item_id:
            return
        item_id = item_id[0]
        article_id = self.ticker_canvas_to_article.get(item_id)
        if article_id is None:
            return

        article = self.storage.get_article(article_id)
        if article:
            webbrowser.open(article["link"])
            if not article["is_read"]:
                self.storage.mark_article_read(article_id)
                self.refresh_feeds_list()
                self.refresh_articles()

    def _on_ticker_motion(self, event):
        """Highlight headline under cursor (magenta), others stay cyan."""
        closest = self.ticker_canvas.find_closest(event.x, event.y)
        if not closest:
            return
        closest_id = closest[0]

        for item_id in self.ticker_canvas.find_withtag("ticker_text"):
            if item_id == closest_id and item_id in self.ticker_canvas_to_article:
                self.ticker_canvas.itemconfigure(item_id, fill=DARK_THEME["magenta"])
            else:
                self.ticker_canvas.itemconfigure(item_id, fill=DARK_THEME["cyan"])

    def _build_main_layout(self):
        """Build the main paned layout."""
        # Main paned window
        self.main_paned = ttk.PanedWindow(self.root, orient=tk.HORIZONTAL)
        self.main_paned.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Left panel - Feed list
        self._build_feeds_panel()

        # Right panel - Articles and preview
        self._build_articles_panel()

    def _build_feeds_panel(self):
        """Build the feeds list panel."""
        feeds_frame = ttk.LabelFrame(self.main_paned, text="Feeds", padding=5)
        self.main_paned.add(feeds_frame, weight=1)

        # Feeds treeview
        self.feeds_tree = ttk.Treeview(feeds_frame, selectmode="browse", show="tree")
        self.feeds_tree.pack(fill=tk.BOTH, expand=True, side=tk.LEFT)

        feeds_scroll = ttk.Scrollbar(feeds_frame, orient=tk.VERTICAL, command=self.feeds_tree.yview)
        feeds_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.feeds_tree.configure(yscrollcommand=feeds_scroll.set)

        self.feeds_tree.bind("<<TreeviewSelect>>", self._on_feed_select)
        self.feeds_tree.bind("<Button-3>", self._on_feed_right_click)

    def _build_articles_panel(self):
        """Build the articles and preview panel."""
        right_paned = ttk.PanedWindow(self.main_paned, orient=tk.VERTICAL)
        self.main_paned.add(right_paned, weight=4)

        # Articles list
        articles_frame = ttk.LabelFrame(right_paned, text="Articles", padding=5)
        right_paned.add(articles_frame, weight=2)

        # Articles treeview with columns
        columns = ("title", "source", "bias", "date", "noise")
        self.articles_tree = ttk.Treeview(articles_frame, columns=columns, show="headings",
                                          selectmode="browse")

        self.articles_tree.heading("title", text="Title", anchor=tk.W)
        self.articles_tree.heading("source", text="Source", anchor=tk.W)
        self.articles_tree.heading("bias", text="Bias", anchor=tk.CENTER)
        self.articles_tree.heading("date", text="Date", anchor=tk.W)
        self.articles_tree.heading("noise", text="Score", anchor=tk.CENTER)

        self.articles_tree.column("title", width=400, minwidth=200)
        self.articles_tree.column("source", width=120, minwidth=80)
        self.articles_tree.column("bias", width=90, minwidth=60)
        self.articles_tree.column("date", width=120, minwidth=80)
        self.articles_tree.column("noise", width=60, minwidth=40)

        self.articles_tree.pack(fill=tk.BOTH, expand=True, side=tk.LEFT)

        articles_scroll = ttk.Scrollbar(articles_frame, orient=tk.VERTICAL,
                                         command=self.articles_tree.yview)
        articles_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.articles_tree.configure(yscrollcommand=articles_scroll.set)

        self.articles_tree.bind("<<TreeviewSelect>>", self._on_article_select)
        self.articles_tree.bind("<Double-1>", self._on_article_double_click)
        self.articles_tree.bind("<Button-3>", self._on_article_right_click)

        # Configure tags for read/unread styling
        self.articles_tree.tag_configure("unread", font=("TkDefaultFont", 9, "bold"),
                                          foreground=DARK_THEME["fg"])
        self.articles_tree.tag_configure("read", foreground=DARK_THEME["fg_secondary"])

        # Preview panel
        preview_frame = ttk.LabelFrame(right_paned, text="Preview", padding=5)
        right_paned.add(preview_frame, weight=1)

        # Preview header
        header_frame = ttk.Frame(preview_frame)
        header_frame.pack(fill=tk.X, pady=(0, 5))

        self.preview_title = ttk.Label(header_frame, text="", font=("TkDefaultFont", 11, "bold"),
                                        wraplength=500)
        self.preview_title.pack(side=tk.LEFT, fill=tk.X, expand=True)

        # Buttons frame
        btn_frame = ttk.Frame(header_frame)
        btn_frame.pack(side=tk.RIGHT)

        # Search Author dropdown menu
        self.author_menu_btn = ttk.Menubutton(btn_frame, text="Search Author")
        self.author_menu = tk.Menu(self.author_menu_btn, tearoff=0,
                                    bg=DARK_THEME["bg_secondary"], fg=DARK_THEME["fg"],
                                    activebackground=DARK_THEME["magenta"],
                                    activeforeground=DARK_THEME["fg_highlight"])
        self.author_menu_btn["menu"] = self.author_menu
        self.author_menu.add_command(label="Google", command=lambda: self._search_author("google"))
        self.author_menu.add_command(label="LinkedIn", command=lambda: self._search_author("linkedin"))
        self.author_menu.add_command(label="Wikipedia", command=lambda: self._search_author("wikipedia"))
        self.author_menu.add_command(label="Twitter/X", command=lambda: self._search_author("twitter"))
        self.author_menu_btn.pack(side=tk.LEFT, padx=2)
        self.author_menu_btn.configure(state=tk.DISABLED)

        self.open_btn = ttk.Button(btn_frame, text="Open in Browser", command=self.open_in_browser,
                                    state=tk.DISABLED)
        self.open_btn.pack(side=tk.LEFT, padx=2)

        # Bias info frame (colored labels)
        bias_frame = ttk.Frame(preview_frame)
        bias_frame.pack(fill=tk.X, pady=(0, 5))

        ttk.Label(bias_frame, text="Source Bias:", font=("TkDefaultFont", 9)).pack(side=tk.LEFT)
        self.bias_label = tk.Label(bias_frame, text="", font=("TkDefaultFont", 9, "bold"),
                                    bg=DARK_THEME["bg"], padx=8, pady=2)
        self.bias_label.pack(side=tk.LEFT, padx=5)

        ttk.Label(bias_frame, text="Factual Rating:", font=("TkDefaultFont", 9)).pack(side=tk.LEFT, padx=(10, 0))
        self.factual_label = tk.Label(bias_frame, text="", font=("TkDefaultFont", 9, "bold"),
                                       bg=DARK_THEME["bg"], padx=8, pady=2)
        self.factual_label.pack(side=tk.LEFT, padx=5)

        # Preview meta info
        self.preview_meta = ttk.Label(preview_frame, text="", foreground=DARK_THEME["fg_secondary"])
        self.preview_meta.pack(fill=tk.X)

        # Preview text
        self.preview_text = tk.Text(preview_frame, wrap=tk.WORD, height=8, state=tk.DISABLED,
                                     bg=DARK_THEME["bg_tertiary"], fg=DARK_THEME["fg"],
                                     insertbackground=DARK_THEME["cyan"],
                                     relief=tk.FLAT, padx=10, pady=10)
        self.preview_text.pack(fill=tk.BOTH, expand=True, pady=5)

        # Configure semantic highlighting tags
        self._setup_highlight_tags()

        preview_text_scroll = ttk.Scrollbar(preview_frame, orient=tk.VERTICAL,
                                             command=self.preview_text.yview)
        preview_text_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.preview_text.configure(yscrollcommand=preview_text_scroll.set)

    def _build_status_bar(self):
        """Build the status bar."""
        self.status_bar = ttk.Label(self.root, text="Ready", anchor=tk.W, padding=(5, 2))
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X)

    # Feed operations
    def _get_favicon_domain(self, feed_url: str) -> str:
        """Extract the domain for favicon fetching, handling special cases."""
        try:
            parsed = urlparse(feed_url)
            domain = parsed.netloc.lower()

            # Handle Google News RSS proxy - extract real domain from query
            if "news.google.com" in domain:
                # URL like: news.google.com/rss/search?q=when:24h+allinurl:apnews.com
                query = parsed.query
                if "allinurl:" in query:
                    # Extract domain after allinurl:
                    start = query.find("allinurl:") + 9
                    end = query.find("&", start)
                    real_domain = query[start:end] if end > start else query[start:]
                    return real_domain.strip()

            # Handle feed subdomains
            subdomain_mappings = {
                "feeds.npr.org": "npr.org",
                "feeds.bbci.co.uk": "bbc.com",
                "rss.nytimes.com": "nytimes.com",
                "feeds.washingtonpost.com": "washingtonpost.com",
            }
            if domain in subdomain_mappings:
                return subdomain_mappings[domain]

            # Remove 'feeds.' or 'rss.' prefix if present
            if domain.startswith("feeds."):
                domain = domain[6:]
            elif domain.startswith("rss."):
                domain = domain[4:]

            return domain
        except:
            return ""

    def _fetch_favicon(self, feed_id: int, feed_url: str):
        """Fetch favicon for a feed in background thread."""
        domain = self._get_favicon_domain(feed_url)
        if not domain:
            return

        def fetch():
            try:
                import requests
                # Use Google's favicon service
                favicon_url = f"https://www.google.com/s2/favicons?domain={domain}&sz=16"
                response = requests.get(favicon_url, timeout=5)
                if response.status_code == 200:
                    self.storage.set_feed_favicon(feed_id, response.content)
                    # Schedule UI update on main thread
                    self.root.after(0, self.refresh_feeds_list)
            except:
                pass  # Silently fail

        thread = threading.Thread(target=fetch, daemon=True)
        thread.start()

    def _load_favicon_image(self, feed_id: int) -> Optional[tk.PhotoImage]:
        """Load favicon from database as PhotoImage, scaled to 16x16."""
        if feed_id in self.feed_icons:
            return self.feed_icons[feed_id]

        favicon_data = self.storage.get_feed_favicon(feed_id)
        if not favicon_data:
            return None

        try:
            # Use PIL to properly scale the favicon to 16x16
            from PIL import Image, ImageTk
            img = Image.open(io.BytesIO(favicon_data))
            img = img.resize((16, 16), Image.Resampling.LANCZOS)
            photo = ImageTk.PhotoImage(img)
            self.feed_icons[feed_id] = photo
            return photo
        except ImportError:
            # PIL not available - try native PhotoImage with subsample
            try:
                image = tk.PhotoImage(data=favicon_data)
                # Subsample if image is larger than 16x16
                w, h = image.width(), image.height()
                if w > 16 or h > 16:
                    factor = max(w // 16, h // 16, 1)
                    image = image.subsample(factor, factor)
                self.feed_icons[feed_id] = image
                return image
            except:
                return None
        except:
            return None

    def refresh_feeds_list(self):
        """Refresh the feeds treeview."""
        self.feeds_tree.delete(*self.feeds_tree.get_children())

        # Add "All Feeds" item
        all_count = self.storage.get_article_count(unread_only=True)
        self.feeds_tree.insert("", tk.END, iid="all", text=f"All Feeds ({all_count} unread)")

        # Group feeds by category
        feeds = self.storage.get_feeds()
        categories = {}
        for feed in feeds:
            cat = feed["category"]
            if cat not in categories:
                categories[cat] = []
            categories[cat].append(feed)

        for category, cat_feeds in sorted(categories.items()):
            cat_id = self.feeds_tree.insert("", tk.END, text=category, open=True)
            for feed in cat_feeds:
                unread = self.storage.get_article_count(feed["id"], unread_only=True)
                text = f"{feed['name']} ({unread})"

                # Try to load favicon
                icon = self._load_favicon_image(feed["id"])
                if icon:
                    self.feeds_tree.insert(cat_id, tk.END, iid=f"feed_{feed['id']}",
                                          text=text, image=icon)
                else:
                    self.feeds_tree.insert(cat_id, tk.END, iid=f"feed_{feed['id']}", text=text)
                    # Fetch favicon in background if not cached
                    if not self.storage.get_feed_favicon(feed["id"]):
                        self._fetch_favicon(feed["id"], feed["url"])

    def refresh_articles(self):
        """Refresh the articles list."""
        self.articles_tree.delete(*self.articles_tree.get_children())

        include_read = self.show_read_var.get()

        # Get filter values
        recency_display = self.recency_combo.get()
        recency_hours = int(self._recency_options.get(recency_display, "24"))

        per_source_display = self.per_source_combo.get()
        max_per_source = int(self._per_source_options.get(per_source_display, "10"))

        use_clustering = self.cluster_var.get()

        articles = self.storage.get_articles(
            feed_id=self.current_feed_id,
            include_read=include_read,
            min_score=0,  # Show all scores, let user judge
            recency_hours=recency_hours,
            max_per_source=max_per_source
        )

        # Apply clustering if enabled
        if use_clustering and self.current_feed_id is None:
            clusters = self.filter_engine.cluster_articles(articles)
            self._display_clustered_articles(clusters)
            total_articles = sum(c["count"] for c in clusters)
            self._update_status(f"Showing {len(clusters)} topics ({total_articles} articles)")
        else:
            self._display_flat_articles(articles)
            self._update_status(f"Showing {len(articles)} articles")

        self._update_ticker()

    def _display_flat_articles(self, articles: list):
        """Display articles without clustering."""
        for article in articles:
            self._insert_article_row(article)

    def _display_clustered_articles(self, clusters: list):
        """Display clustered articles with [+N] indicators."""
        self.cluster_map = {}  # Map article_id -> cluster info

        for cluster in clusters:
            rep = cluster["representative"]
            count = cluster["count"]

            # Store cluster info for expanding later
            if count > 1:
                self.cluster_map[rep["id"]] = cluster

            # Add cluster indicator to title if multiple articles
            title = rep["title"]
            if count > 1:
                title = f"[+{count - 1}] {title}"

            self._insert_article_row(rep, title_override=title)

    def _insert_article_row(self, article: dict, title_override: str = None):
        """Insert a single article row into the treeview."""
        title = title_override or article["title"]

        # Format date as relative time
        date_str = ""
        if article["published"]:
            try:
                dt = datetime.fromisoformat(article["published"])
                now = datetime.now()
                diff = now - dt
                hours = diff.total_seconds() / 3600
                if hours < 1:
                    date_str = "< 1 Hour"
                elif hours < 24:
                    date_str = f"< {int(hours) + 1} Hours"
                else:
                    days = int(hours / 24)
                    date_str = f"{days} Day{'s' if days > 1 else ''}"
            except ValueError:
                date_str = article["published"][:16]

        score_label = self.filter_engine.get_noise_level(article["noise_score"])
        bias = article.get("bias", "Unknown")

        tags = ("unread",) if not article["is_read"] else ("read",)

        self.articles_tree.insert(
            "", tk.END,
            iid=str(article["id"]),
            values=(title, article["feed_name"], bias, date_str, score_label),
            tags=tags
        )

    def fetch_all_feeds(self):
        """Fetch all enabled feeds in a background thread."""
        if self.is_fetching:
            return

        self.is_fetching = True
        self.refresh_btn.configure(state=tk.DISABLED)
        self._update_status("Fetching feeds...")

        def fetch_thread():
            feeds = self.storage.get_feeds()
            total = len(feeds)
            success_count = 0
            article_count = 0

            for i, feed in enumerate(feeds):
                self.root.after(0, lambda f=feed, idx=i: self._update_status(
                    f"Fetching {f['name']}... ({idx + 1}/{total})"
                ))

                result = self.feed_manager.fetch_feed(feed["url"])
                if result["success"]:
                    success_count += 1

                    # Score all articles first
                    scored_articles = []
                    for article in result["articles"]:
                        score = self.filter_engine.calculate_objectivity_score(
                            article["title"],
                            article["link"],
                            article.get("summary", ""),
                            feed.get("factual", "")
                        )
                        scored_articles.append((score, article))

                    # Sort by score (highest first) and take top 10
                    scored_articles.sort(key=lambda x: x[0], reverse=True)
                    top_articles = scored_articles[:10]

                    for noise_score, article in top_articles:
                        added = self.storage.add_article(
                            feed_id=feed["id"],
                            title=article["title"],
                            link=article["link"],
                            summary=article.get("summary", ""),
                            published=article.get("published"),
                            author=article.get("author", ""),
                            noise_score=noise_score
                        )
                        if added:
                            article_count += 1

                    self.storage.update_feed_fetched(feed["id"])

            # Update UI on main thread
            def finish():
                self.is_fetching = False
                self.refresh_btn.configure(state=tk.NORMAL)
                self.refresh_feeds_list()
                self.refresh_articles()
                self._update_status(
                    f"Fetched {success_count}/{total} feeds, {article_count} new articles"
                )

            self.root.after(0, finish)

        thread = threading.Thread(target=fetch_thread, daemon=True)
        thread.start()

    def show_add_feed_dialog(self):
        """Show dialog to add a new feed."""
        dialog = AddFeedDialog(self.root, self.feed_manager)
        if dialog.result:
            name, url, category = dialog.result
            feed_id = self.storage.add_feed(name, url, category)
            if feed_id:
                self.refresh_feeds_list()
                self._update_status(f"Added feed: {name}")
                # Fetch the new feed
                self._fetch_single_feed(feed_id)
            else:
                messagebox.showwarning("Duplicate", "This feed URL already exists.")

    def show_manage_feeds_dialog(self):
        """Show dialog to manage feeds."""
        dialog = ManageFeedsDialog(self.root, self.storage)
        if dialog.changed:
            self.refresh_feeds_list()
            self.refresh_articles()

    def _fetch_single_feed(self, feed_id: int):
        """Fetch a single feed."""
        feed = self.storage.get_feed(feed_id)
        if not feed:
            return

        self._update_status(f"Fetching {feed['name']}...")

        def fetch_thread():
            result = self.feed_manager.fetch_feed(feed["url"])
            article_count = 0

            if result["success"]:
                # Score all articles first
                scored_articles = []
                for article in result["articles"]:
                    score = self.filter_engine.calculate_objectivity_score(
                        article["title"],
                        article["link"],
                        article.get("summary", ""),
                        feed.get("factual", "")
                    )
                    scored_articles.append((score, article))

                # Sort by score (highest first) and take top 10
                scored_articles.sort(key=lambda x: x[0], reverse=True)
                top_articles = scored_articles[:10]

                for noise_score, article in top_articles:
                    added = self.storage.add_article(
                        feed_id=feed_id,
                        title=article["title"],
                        link=article["link"],
                        summary=article.get("summary", ""),
                        published=article.get("published"),
                        author=article.get("author", ""),
                        noise_score=noise_score
                    )
                    if added:
                        article_count += 1

                self.storage.update_feed_fetched(feed_id)

            def finish():
                self.refresh_feeds_list()
                self.refresh_articles()
                if result["success"]:
                    self._update_status(f"Fetched {feed['name']}: {article_count} new articles")
                else:
                    self._update_status(f"Failed to fetch {feed['name']}: {result['error']}")

            self.root.after(0, finish)

        thread = threading.Thread(target=fetch_thread, daemon=True)
        thread.start()

    # Article operations
    def mark_all_read(self):
        """Mark all visible articles as read."""
        self.storage.mark_all_read(self.current_feed_id)
        self.refresh_feeds_list()
        self.refresh_articles()
        self._update_status("Marked all as read")

    def open_in_browser(self):
        """Open the selected article in the default browser."""
        if self.selected_article_id:
            article = self.storage.get_article(self.selected_article_id)
            if article:
                webbrowser.open(article["link"])
                self.storage.mark_article_read(self.selected_article_id)
                self.refresh_articles()

    def _clean_author_name(self, author: str) -> Optional[str]:
        """Clean and validate author name for searching."""
        if not author:
            return None

        author = author.strip()

        # Skip agency bylines
        agency_bylines = ["AFP", "Reuters", "AP", "Associated Press", "Bloomberg",
                         "Staff", "Wire Services", "News Desk", "Editors"]
        if any(agency.lower() in author.lower() for agency in agency_bylines):
            return None

        # Remove common prefixes
        for prefix in ["By ", "by ", "BY "]:
            if author.startswith(prefix):
                author = author[len(prefix):]

        # Remove suffixes after comma (titles, locations, etc.)
        if "," in author:
            author = author.split(",")[0].strip()

        # Remove parenthetical info
        author = author.split("(")[0].strip()

        # Remove "and others" type suffixes
        for suffix in [" and ", " & ", " et al"]:
            if suffix in author:
                author = author.split(suffix)[0].strip()

        # Must have at least 2 characters
        if len(author) < 2:
            return None

        return author

    def _search_author(self, platform: str):
        """Search for current author on specified platform."""
        if not hasattr(self, 'current_author_clean') or not self.current_author_clean:
            return

        author = self.current_author_clean
        domain = getattr(self, 'current_article_domain', '')

        # Build search URL based on platform
        import urllib.parse
        encoded_author = urllib.parse.quote(author)

        if platform == "google":
            query = f'"{author}" author'
            if domain:
                query += f" site:{domain}"
            url = f"https://www.google.com/search?q={urllib.parse.quote(query)}"
        elif platform == "linkedin":
            url = f"https://www.linkedin.com/search/results/people/?keywords={encoded_author}"
        elif platform == "wikipedia":
            url = f"https://en.wikipedia.org/wiki/Special:Search?search={encoded_author}"
        elif platform == "twitter":
            url = f"https://twitter.com/search?q={encoded_author}&f=user"
        else:
            return

        webbrowser.open(url)

    def search_articles(self):
        """Search articles by title/summary."""
        query = self.search_var.get().strip()
        if not query:
            self.refresh_articles()
            return

        self.articles_tree.delete(*self.articles_tree.get_children())
        threshold = self.noise_threshold_var.get()
        articles = self.storage.search_articles(query, min_score=threshold)

        for article in articles:
            date_str = ""
            if article["published"]:
                try:
                    dt = datetime.fromisoformat(article["published"])
                    date_str = dt.strftime("%Y-%m-%d %H:%M")
                except ValueError:
                    date_str = article["published"][:16]

            noise_level = self.filter_engine.get_noise_level(article["noise_score"])
            bias = article.get("bias", "Unknown")
            tags = ("unread",) if not article["is_read"] else ("read",)

            self.articles_tree.insert(
                "", tk.END,
                iid=str(article["id"]),
                values=(article["title"], article["feed_name"], bias, date_str, noise_level),
                tags=tags
            )

        self._update_status(f"Found {len(articles)} articles matching '{query}'")

    def clear_search(self):
        """Clear search and refresh articles."""
        self.search_var.set("")
        self.refresh_articles()

    def show_delete_old_dialog(self):
        """Show dialog to delete old articles."""
        days = simpledialog.askinteger(
            "Delete Old Articles",
            "Delete articles older than how many days?",
            initialvalue=7,
            minvalue=1,
            maxvalue=365
        )
        if days:
            count = self.storage.delete_old_articles(days)
            self.refresh_feeds_list()
            self.refresh_articles()
            messagebox.showinfo("Done", f"Deleted {count} old articles.")

    def show_filter_keywords_dialog(self):
        """Show dialog to manage filter keywords."""
        dialog = FilterKeywordsDialog(self.root, self.storage)
        if dialog.changed:
            # Update filter engine with new keywords
            self.filter_engine.update_custom_keywords(self.storage.get_filter_keywords())
            self._update_status("Filter keywords updated")

    # Event handlers
    def _on_feed_select(self, event):
        """Handle feed selection."""
        selection = self.feeds_tree.selection()
        if not selection:
            return

        item_id = selection[0]
        if item_id == "all":
            self.current_feed_id = None
        elif item_id.startswith("feed_"):
            self.current_feed_id = int(item_id.replace("feed_", ""))
        else:
            # Category selected, show all feeds in category
            self.current_feed_id = None

        self.refresh_articles()

    def _on_feed_right_click(self, event):
        """Handle right-click on feed."""
        item = self.feeds_tree.identify_row(event.y)
        if item and item.startswith("feed_"):
            self.feeds_tree.selection_set(item)
            feed_id = int(item.replace("feed_", ""))

            menu = tk.Menu(self.root, tearoff=0,
                          bg=DARK_THEME["bg_secondary"], fg=DARK_THEME["fg"],
                          activebackground=DARK_THEME["magenta"],
                          activeforeground=DARK_THEME["fg_highlight"])
            menu.add_command(label="Refresh This Feed",
                             command=lambda: self._fetch_single_feed(feed_id))
            menu.add_command(label="Mark All as Read",
                             command=lambda: self._mark_feed_read(feed_id))
            menu.add_separator()
            menu.add_command(label="Remove Feed",
                             command=lambda: self._remove_feed(feed_id))
            menu.post(event.x_root, event.y_root)

    def _mark_feed_read(self, feed_id: int):
        """Mark all articles in a feed as read."""
        self.storage.mark_all_read(feed_id)
        self.refresh_feeds_list()
        self.refresh_articles()

    def _remove_feed(self, feed_id: int):
        """Remove a feed after confirmation."""
        feed = self.storage.get_feed(feed_id)
        if feed and messagebox.askyesno("Confirm", f"Remove '{feed['name']}' and all its articles?"):
            self.storage.remove_feed(feed_id)
            self.refresh_feeds_list()
            self.refresh_articles()
            self._update_status(f"Removed feed: {feed['name']}")

    def _on_article_select(self, event):
        """Handle article selection."""
        selection = self.articles_tree.selection()
        if not selection:
            return

        article_id = int(selection[0])
        self.selected_article_id = article_id
        article = self.storage.get_article(article_id)

        if article:
            self.preview_title.configure(text=article["title"])

            # Update bias label with color
            bias = article.get("bias", "Unknown")
            bias_color = BIAS_COLORS.get(bias, "#666666")
            self.bias_label.configure(text=bias, bg=bias_color, fg="white")

            # Update factual label with color
            factual = article.get("factual", "Unknown")
            factual_color = FACTUAL_COLORS.get(factual, "#666666")
            self.factual_label.configure(text=factual, bg=factual_color, fg="white")

            date_str = ""
            if article["published"]:
                try:
                    dt = datetime.fromisoformat(article["published"])
                    date_str = dt.strftime("%B %d, %Y at %H:%M")
                except ValueError:
                    date_str = article["published"]

            meta = f"{article['feed_name']}"
            if article.get("author"):
                meta += f" • {article['author']}"
            if date_str:
                meta += f" • {date_str}"
            meta += f" • Noise: {article['noise_score']} ({self.filter_engine.get_noise_level(article['noise_score'])})"

            self.preview_meta.configure(text=meta)

            self.preview_text.configure(state=tk.NORMAL)
            self.preview_text.delete("1.0", tk.END)

            summary = article.get("summary", "No summary available.")
            self._apply_highlighting(self.preview_text, summary)

            # Show related articles if this is a cluster representative
            if hasattr(self, 'cluster_map') and article_id in self.cluster_map:
                cluster = self.cluster_map[article_id]
                if cluster["count"] > 1:
                    self.preview_text.insert(tk.END, "\n\n─── RELATED ARTICLES ───\n\n")
                    for i, related in enumerate(cluster["articles"][1:], 1):  # Skip representative
                        source = related.get("feed_name", "Unknown")
                        score = related.get("noise_score", 0)
                        self.preview_text.insert(tk.END, f"• [{source}] {related['title']} ({score})\n")

            self.preview_text.configure(state=tk.DISABLED)

            self.open_btn.configure(state=tk.NORMAL)

            # Enable author search if we have a valid author name
            self.current_author_clean = self._clean_author_name(article.get("author", ""))
            # Extract domain from article link for Google search
            try:
                from urllib.parse import urlparse
                parsed = urlparse(article.get("link", ""))
                self.current_article_domain = parsed.netloc.replace("www.", "")
            except:
                self.current_article_domain = ""

            if self.current_author_clean:
                self.author_menu_btn.configure(state=tk.NORMAL)
            else:
                self.author_menu_btn.configure(state=tk.DISABLED)

            # Mark as read
            if not article["is_read"]:
                self.storage.mark_article_read(article_id)
                self.refresh_feeds_list()
                # Update just this row's tag
                self.articles_tree.item(str(article_id), tags=("read",))
                self._update_ticker()

    def _on_article_double_click(self, event):
        """Handle double-click on article."""
        self.open_in_browser()

    def _on_article_right_click(self, event):
        """Handle right-click on article."""
        item = self.articles_tree.identify_row(event.y)
        if item:
            self.articles_tree.selection_set(item)
            article_id = int(item)

            menu = tk.Menu(self.root, tearoff=0,
                          bg=DARK_THEME["bg_secondary"], fg=DARK_THEME["fg"],
                          activebackground=DARK_THEME["magenta"],
                          activeforeground=DARK_THEME["fg_highlight"])
            menu.add_command(label="Open in Browser", command=self.open_in_browser)
            menu.add_command(label="Mark as Unread",
                             command=lambda: self._toggle_read(article_id, False))
            menu.add_separator()
            menu.add_command(label="Hide Article",
                             command=lambda: self._hide_article(article_id))
            menu.post(event.x_root, event.y_root)

    def _toggle_read(self, article_id: int, is_read: bool):
        """Toggle article read status."""
        self.storage.mark_article_read(article_id, is_read)
        self.refresh_feeds_list()
        self.refresh_articles()

    def _hide_article(self, article_id: int):
        """Hide an article."""
        self.storage.hide_article(article_id)
        self.refresh_articles()
        self._update_status("Article hidden")

    def _on_recency_change(self, event):
        """Handle recency dropdown change."""
        display = self.recency_combo.get()
        hours = self._recency_options.get(display, "24")
        self.storage.set_setting("recency_hours", hours)
        self.refresh_articles()

    def _on_per_source_change(self, event):
        """Handle per-source cap dropdown change."""
        display = self.per_source_combo.get()
        value = self._per_source_options.get(display, "10")
        self.storage.set_setting("max_per_source", value)
        self.refresh_articles()

    def _on_cluster_toggle(self):
        """Handle cluster checkbox toggle."""
        self.storage.set_setting("cluster_topics", str(self.cluster_var.get()))
        self.refresh_articles()

    def _schedule_auto_refresh(self):
        """Schedule automatic feed refresh."""
        if self.auto_refresh_job:
            self.root.after_cancel(self.auto_refresh_job)

        minutes = int(self.storage.get_setting("auto_refresh_minutes", "30"))
        if minutes > 0:
            ms = minutes * 60 * 1000
            self.auto_refresh_job = self.root.after(ms, self._auto_refresh)

    def _auto_refresh(self):
        """Perform automatic refresh."""
        if not self.is_fetching:
            self.fetch_all_feeds()
        self._schedule_auto_refresh()

    def _setup_highlight_tags(self):
        """Configure text tags for semantic highlighting."""
        # Bold for first sentence (lede)
        self.preview_text.tag_configure("lede", font=("TkDefaultFont", 9, "bold"))

        # Entity categories (clickable Wikipedia links)
        self.highlight_categories = {
            "people": "#008b8b",      # Cyan
            "titles": "#8b008b",      # Purple
            "government": "#6a5acd",  # Slate Blue
            "military": "#4682b4",    # Steel Blue
            "organizations": "#228b22", # Green
            "countries": "#cc7000",   # Orange
            "places": "#a0522d",      # Sienna
            "events": "#b8860b",      # Goldenrod
        }

        # Number categories (not clickable)
        self.number_categories = {
            "money": "#c71585",       # Magenta
            "statistics": "#ff69b4",  # Hot Pink
            "dates": "#e75480",       # Rose
            "verbs": "#d2956b",       # Muted Coral
            "numbers": "#e6c300",     # Yellow
        }

        # Configure tags for entities (clickable)
        for tag, color in self.highlight_categories.items():
            self.preview_text.tag_configure(tag, foreground=color, underline=True)
            self.preview_text.tag_bind(tag, "<Enter>",
                                       lambda e: self.preview_text.configure(cursor="hand2"))
            self.preview_text.tag_bind(tag, "<Leave>",
                                       lambda e: self.preview_text.configure(cursor=""))
            self.preview_text.tag_bind(tag, "<Button-1>", self._on_wiki_link_click)

        # Configure tags for numbers (not clickable)
        for tag, color in self.number_categories.items():
            self.preview_text.tag_configure(tag, foreground=color)

        # Store wiki link targets: {(start, end): (search_term, category)}
        self.wiki_link_targets = {}

        # Initialize entity databases
        self._init_entity_databases()

    def _init_entity_databases(self):
        """Initialize databases of known entities for categorization."""

        # Titles & Roles (comprehensive - will be followed by a name)
        self.titles = {
            # === POLITICAL LEADERS ===
            "president", "vice president", "president-elect",
            "prime minister", "premier", "deputy prime minister",
            "chancellor", "vice chancellor",
            "chief minister", "first minister",
            # === CABINET & MINISTERS ===
            "minister", "secretary", "undersecretary", "deputy minister",
            "foreign minister", "defense minister", "defence minister",
            "finance minister", "interior minister", "home secretary",
            "foreign secretary", "treasury secretary", "attorney general",
            "solicitor general", "secretary of state", "secretary general",
            # === LEGISLATORS ===
            "senator", "congressman", "congresswoman", "representative",
            "assemblyman", "assemblywoman", "delegate", "councillor", "councilor",
            "speaker", "majority leader", "minority leader", "whip",
            "mp", "member of parliament", "mep", "lawmaker", "legislator",
            # === REGIONAL/LOCAL ===
            "governor", "lieutenant governor", "mayor", "deputy mayor",
            "city manager", "county executive", "prefect", "magistrate",
            # === ROYALTY & NOBILITY ===
            "king", "queen", "prince", "princess", "crown prince", "crown princess",
            "emperor", "empress", "sultan", "emir", "sheikh", "sheik",
            "duke", "duchess", "earl", "countess", "baron", "baroness",
            "lord", "lady", "sir", "dame", "count",
            # === RELIGIOUS LEADERS ===
            "pope", "cardinal", "archbishop", "bishop", "priest", "reverend",
            "pastor", "rabbi", "imam", "ayatollah", "grand ayatollah",
            "patriarch", "dalai lama", "grand mufti", "cleric",
            # === MILITARY RANKS ===
            "general", "lieutenant general", "major general", "brigadier general",
            "brigadier", "colonel", "lieutenant colonel", "major",
            "captain", "lieutenant", "first lieutenant", "second lieutenant",
            "sergeant", "corporal", "private",
            "admiral", "vice admiral", "rear admiral", "commodore",
            "fleet admiral", "field marshal", "marshal",
            "commander", "chief of staff", "commandant",
            # === JUDICIAL ===
            "judge", "justice", "chief justice", "associate justice",
            "magistrate", "prosecutor", "district attorney", "da",
            "public defender", "solicitor", "barrister", "advocate",
            # === DIPLOMATIC ===
            "ambassador", "envoy", "consul", "diplomat", "attaché",
            "high commissioner", "chargé d'affaires", "representative",
            "special envoy", "special representative",
            # === CORPORATE ===
            "ceo", "cfo", "coo", "cto", "cio",
            "chief executive", "chief executive officer",
            "chairman", "chairwoman", "chairperson", "chair",
            "president", "vice president", "vp", "evp", "svp",
            "director", "managing director", "executive director",
            "founder", "co-founder", "partner", "managing partner",
            "treasurer", "comptroller",
            # === ACADEMIC ===
            "professor", "prof", "doctor", "dr",
            "dean", "provost", "chancellor", "rector", "principal",
            "researcher", "scientist", "fellow",
            # === MEDIA ===
            "editor", "editor-in-chief", "publisher", "correspondent",
            "anchor", "journalist", "reporter", "columnist",
            # === LAW ENFORCEMENT ===
            "chief", "police chief", "sheriff", "deputy",
            "commissioner", "superintendent", "inspector",
            "detective", "officer", "constable", "marshal",
            "special agent", "agent",
            # === INTELLIGENCE ===
            "spy", "spymaster", "station chief",
            # === GENERAL LEADERSHIP ===
            "leader", "head", "chief", "boss", "czar", "tsar",
            "spokesperson", "spokesman", "spokeswoman", "representative",
            "coordinator", "advisor", "adviser", "counsel", "aide",
            "official", "executive", "administrator", "commissioner",
        }

        # Countries & Nations (all 195 UN members + common aliases + territories)
        self.countries = {
            # North America
            "united states", "america", "usa", "u.s.", "canada", "mexico",
            # Central America
            "guatemala", "belize", "honduras", "el salvador", "nicaragua", "costa rica", "panama",
            # Caribbean
            "cuba", "haiti", "dominican republic", "jamaica", "bahamas", "barbados",
            "trinidad and tobago", "trinidad", "tobago", "grenada", "saint lucia", "st lucia",
            "antigua and barbuda", "antigua", "saint kitts and nevis", "saint vincent",
            "dominica", "puerto rico",
            # South America
            "brazil", "argentina", "colombia", "venezuela", "peru", "chile", "ecuador",
            "bolivia", "paraguay", "uruguay", "guyana", "suriname", "french guiana",
            # Western Europe
            "united kingdom", "britain", "england", "scotland", "wales", "northern ireland",
            "france", "germany", "italy", "spain", "portugal", "netherlands", "belgium",
            "luxembourg", "switzerland", "austria", "ireland", "monaco", "andorra",
            "liechtenstein", "san marino", "vatican",
            # Northern Europe
            "sweden", "norway", "finland", "denmark", "iceland", "greenland",
            # Eastern Europe
            "russia", "ukraine", "poland", "romania", "czech republic", "czechia",
            "hungary", "bulgaria", "slovakia", "belarus", "moldova", "lithuania",
            "latvia", "estonia",
            # Balkans
            "serbia", "croatia", "bosnia", "bosnia and herzegovina", "slovenia",
            "north macedonia", "macedonia", "albania", "montenegro", "kosovo", "greece",
            # Central Asia
            "kazakhstan", "uzbekistan", "turkmenistan", "kyrgyzstan", "tajikistan",
            "afghanistan", "mongolia",
            # East Asia
            "china", "japan", "south korea", "north korea", "korea", "taiwan", "hong kong", "macau",
            # Southeast Asia
            "vietnam", "thailand", "philippines", "indonesia", "malaysia", "singapore",
            "myanmar", "burma", "cambodia", "laos", "brunei", "east timor", "timor-leste",
            # South Asia
            "india", "pakistan", "bangladesh", "sri lanka", "nepal", "bhutan", "maldives",
            # Middle East
            "iran", "iraq", "israel", "palestine", "gaza", "syria", "turkey", "lebanon",
            "jordan", "saudi arabia", "yemen", "oman", "uae", "united arab emirates", "emirates",
            "qatar", "bahrain", "kuwait", "cyprus",
            # Caucasus
            "georgia", "armenia", "azerbaijan",
            # North Africa
            "egypt", "libya", "tunisia", "algeria", "morocco", "western sahara",
            # East Africa
            "ethiopia", "kenya", "tanzania", "uganda", "rwanda", "burundi", "somalia",
            "south sudan", "sudan", "eritrea", "djibouti", "seychelles", "mauritius",
            # West Africa
            "nigeria", "ghana", "senegal", "ivory coast", "cote d'ivoire", "mali",
            "burkina faso", "niger", "guinea", "benin", "togo", "sierra leone", "liberia",
            "mauritania", "gambia", "guinea-bissau", "cape verde",
            # Central Africa
            "congo", "democratic republic of congo", "drc", "cameroon", "gabon",
            "central african republic", "chad", "equatorial guinea", "sao tome",
            # Southern Africa
            "south africa", "zimbabwe", "zambia", "botswana", "namibia", "mozambique",
            "angola", "malawi", "lesotho", "eswatini", "swaziland", "madagascar",
            # Oceania
            "australia", "new zealand", "papua new guinea", "fiji", "solomon islands",
            "vanuatu", "samoa", "tonga", "kiribati", "micronesia", "palau", "marshall islands",
            "nauru", "tuvalu",
            # Historical
            "soviet union", "ussr", "yugoslavia", "czechoslovakia",
        }

        # Government & Politics (comprehensive)
        self.government = {
            # === US GOVERNMENT ===
            # Executive
            "white house", "oval office", "executive branch",
            "state department", "department of state", "treasury department",
            "defense department", "department of defense", "dod", "pentagon",
            "justice department", "department of justice", "doj",
            "homeland security", "department of homeland security", "dhs",
            "interior department", "department of interior",
            "commerce department", "department of commerce",
            "labor department", "department of labor",
            "hhs", "health and human services", "department of education",
            "department of energy", "doe", "department of agriculture", "usda",
            "department of transportation", "dot", "hud",
            "department of veterans affairs", "va",
            # US Agencies
            "fbi", "federal bureau of investigation", "cia", "central intelligence agency",
            "nsa", "national security agency", "dea", "atf", "secret service",
            "us marshals", "ice", "cbp", "customs and border protection",
            "tsa", "fema", "coast guard",
            "sec", "securities and exchange commission",
            "ftc", "federal trade commission", "fcc", "federal communications commission",
            "epa", "environmental protection agency", "fda", "food and drug administration",
            "cdc", "centers for disease control", "nih", "national institutes of health",
            "faa", "federal aviation administration", "nasa",
            "federal reserve", "fed", "treasury", "irs", "internal revenue service",
            "usps", "postal service", "social security administration", "ssa",
            "national weather service", "nws", "noaa",
            # US Legislative
            "congress", "senate", "house of representatives", "house",
            "capitol", "capitol hill", "congressional",
            # US Judicial
            "supreme court", "federal court", "appeals court", "circuit court",
            "district court",
            # US Political
            "democratic party", "democrats", "dnc",
            "republican party", "republicans", "gop", "rnc",
            "libertarian party", "green party",
            # US State/Local
            "governor", "state legislature", "city council", "mayor",
            # === UK GOVERNMENT ===
            "parliament", "house of commons", "house of lords", "westminster",
            "downing street", "10 downing street", "cabinet office", "privy council",
            "home office", "foreign office", "treasury", "ministry of defence", "mod",
            "nhs", "national health service", "mi5", "mi6", "gchq",
            "scotland yard", "met police", "metropolitan police",
            "labour party", "labour", "conservative party", "conservatives", "tories",
            "liberal democrats", "lib dems", "snp", "scottish national party",
            # === EU INSTITUTIONS ===
            "european commission", "european parliament", "european council",
            "council of the european union", "european court of justice", "ecj",
            "european central bank", "ecb", "eurogroup", "frontex",
            # === RUSSIAN GOVERNMENT ===
            "kremlin", "duma", "state duma", "federation council",
            "fsb", "federal security service", "svr", "gru",
            "ministry of defence", "ministry of foreign affairs",
            "united russia", "communist party of russia",
            # === CHINESE GOVERNMENT ===
            "communist party", "ccp", "cpc", "politburo", "standing committee",
            "central committee", "national people's congress", "npc",
            "state council", "central military commission", "cmc",
            "ministry of foreign affairs", "ministry of national defense",
            "ministry of state security", "mss", "ministry of public security",
            "people's bank of china", "pboc",
            # === OTHER GOVERNMENTS ===
            # France
            "elysee", "elysee palace", "national assembly", "french senate",
            # Germany
            "bundestag", "bundesrat", "chancellery",
            "cdu", "csu", "spd", "greens", "afd", "fdp",
            # Japan
            "diet", "national diet", "ldp", "liberal democratic party",
            # India
            "lok sabha", "rajya sabha", "bjp", "congress party", "inc",
            # Brazil
            "planalto", "brazilian congress",
            # General terms
            "parliament", "legislature", "congress", "senate", "assembly",
            "cabinet", "ministry", "department", "agency", "bureau", "office",
            "court", "tribunal", "commission", "council", "committee",
            "defence ministry", "defense ministry", "foreign ministry",
            "interior ministry", "finance ministry", "justice ministry",
            "prime minister's office", "president's office", "chancellery",
            "national security council", "nsc",
            "intelligence agency", "secret service", "security service",
            "central bank", "reserve bank", "monetary authority",
            "electoral commission", "election commission",
            "constitutional court", "high court", "appeals court",
            "prosecutor", "attorney general", "solicitor general",
            "bureau of meteorology", "weather service",
        }

        # Military & Defense (comprehensive)
        self.military = {
            # === ALLIANCES & COALITIONS ===
            "nato", "north atlantic treaty organization",
            "five eyes", "aukus", "quad", "csto", "sco", "shanghai cooperation",
            # === US MILITARY ===
            "us military", "us armed forces", "american military",
            "us army", "army", "us navy", "navy", "us air force", "air force",
            "us marine corps", "marine corps", "marines", "usmc",
            "us coast guard", "coast guard", "space force", "us space force",
            "national guard", "army national guard", "air national guard",
            "special forces", "green berets", "army rangers", "delta force",
            "navy seals", "seal team", "devgru", "jsoc",
            "joint chiefs", "joint chiefs of staff", "central command", "centcom",
            "indo-pacific command", "indopacom", "european command", "eucom",
            "northern command", "northcom", "southern command", "southcom",
            "africa command", "africom", "cyber command", "strategic command",
            # === RUSSIAN MILITARY ===
            "russian military", "russian armed forces", "russian army",
            "russian navy", "russian air force", "vks",
            "spetsnaz", "gru", "wagner group", "wagner", "pmc wagner",
            "black sea fleet", "northern fleet", "pacific fleet",
            # === CHINESE MILITARY ===
            "pla", "people's liberation army", "chinese military",
            "pla army", "pla navy", "plan", "pla air force", "plaaf",
            "pla rocket force", "plarf", "strategic support force",
            "eastern theater command", "southern theater command",
            # === UK MILITARY ===
            "british military", "british armed forces", "british army",
            "royal navy", "royal air force", "raf", "royal marines",
            "sas", "sbs", "special air service", "special boat service",
            # === OTHER NATIONAL MILITARIES ===
            "idf", "israel defense forces", "israeli military", "mossad", "shin bet",
            "bundeswehr", "german military", "german army",
            "french military", "french army", "foreign legion",
            "indian military", "indian army", "indian navy", "indian air force",
            "jsdf", "japan self-defense forces", "japanese military",
            "rok military", "south korean military", "rok army",
            "turkish military", "turkish armed forces",
            "iranian military", "irgc", "revolutionary guard", "quds force",
            "saudi military", "saudi armed forces",
            "pakistani military", "pakistan army", "isi",
            "ukrainian military", "ukrainian armed forces", "azov",
            # === MILITANT & TERRORIST GROUPS ===
            "hamas", "palestinian islamic jihad", "pij", "fatah", "plo",
            "hezbollah", "houthis", "ansar allah",
            "taliban", "haqqani network",
            "isis", "isil", "islamic state", "daesh", "al-qaeda", "al qaeda",
            "al-shabaab", "boko haram", "jemaah islamiyah",
            "pkk", "kurdish militants", "peshmerga", "ypg", "sdf",
            "ira", "eta", "farc", "eln",
            # === MILITARY UNITS & TERMS ===
            "armed forces", "military", "defense forces", "defence forces",
            "troops", "soldiers", "infantry", "cavalry", "artillery",
            "battalion", "brigade", "division", "regiment", "corps",
            "platoon", "company", "squadron", "fleet", "flotilla",
            "airborne", "paratroopers", "mechanized", "armored",
            "special operations", "commandos", "elite forces",
            "reservists", "reserves", "militia", "paramilitary",
            "mercenaries", "contractors", "private military",
            # === EQUIPMENT TERMS ===
            "fighter jets", "bombers", "drones", "uav", "missiles",
            "tanks", "armored vehicles", "warships", "submarines",
            "aircraft carrier", "destroyer", "frigate", "cruiser",
            "nuclear weapons", "icbm", "ballistic missiles",
        }

        # Organizations (Companies, NGOs, Institutions - comprehensive)
        self.organizations = {
            # === INTERNATIONAL ORGANIZATIONS ===
            "united nations", "un", "who", "unesco", "unicef", "imf", "world bank",
            "world health organization", "world trade organization", "wto",
            "international monetary fund", "world food programme", "wfp",
            "international atomic energy agency", "iaea", "interpol",
            "international criminal court", "icc", "icj", "world court",
            "international committee of the red cross", "icrc", "red cross", "red crescent",
            "world economic forum", "wef", "oecd", "g7", "g20", "g77",
            "european union", "eu", "european central bank", "ecb",
            "african union", "au", "asean", "opec", "opec+", "apec", "brics",
            "arab league", "oic", "commonwealth", "nato", "osce",
            "amnesty international", "human rights watch", "hrw",
            "greenpeace", "doctors without borders", "msf", "oxfam", "care",
            "save the children", "world wildlife fund", "wwf", "iucn",
            "transparency international", "reporters without borders",
            # === TECH COMPANIES ===
            "apple", "google", "alphabet", "microsoft", "amazon", "meta", "facebook",
            "twitter", "x corp", "tesla", "nvidia", "intel", "amd", "qualcomm",
            "openai", "anthropic", "deepmind", "ibm", "oracle", "salesforce",
            "adobe", "cisco", "dell", "hp", "hewlett packard", "lenovo",
            "samsung", "sony", "lg", "panasonic", "toshiba", "huawei", "xiaomi",
            "tiktok", "bytedance", "alibaba", "tencent", "baidu", "jd.com",
            "netflix", "spotify", "uber", "lyft", "airbnb", "doordash",
            "paypal", "square", "stripe", "coinbase", "robinhood",
            "zoom", "slack", "dropbox", "atlassian", "shopify", "snowflake",
            "palantir", "crowdstrike", "palo alto networks", "fortinet",
            # === FINANCE & BANKING ===
            "jpmorgan", "jpmorgan chase", "goldman sachs", "morgan stanley",
            "bank of america", "citigroup", "citibank", "wells fargo",
            "hsbc", "barclays", "deutsche bank", "ubs", "credit suisse",
            "bnp paribas", "societe generale", "santander", "ing",
            "blackrock", "vanguard", "fidelity", "state street", "schwab",
            "berkshire hathaway", "visa", "mastercard", "american express",
            # === ENERGY & OIL ===
            "exxonmobil", "exxon", "chevron", "shell", "bp", "totalenergies", "total",
            "conocophillips", "marathon", "valero", "phillips 66",
            "gazprom", "rosneft", "lukoil", "saudi aramco", "aramco",
            "petrochina", "sinopec", "cnooc", "petrobras", "equinor", "eni",
            # === AUTOMOTIVE ===
            "toyota", "volkswagen", "vw", "ford", "general motors", "gm",
            "honda", "nissan", "hyundai", "kia", "bmw", "mercedes", "mercedes-benz",
            "audi", "porsche", "ferrari", "lamborghini", "maserati",
            "stellantis", "chrysler", "jeep", "dodge", "fiat", "peugeot", "renault",
            "rivian", "lucid", "nio", "byd", "geely", "volvo",
            # === AEROSPACE & DEFENSE ===
            "boeing", "airbus", "lockheed martin", "raytheon", "northrop grumman",
            "general dynamics", "bae systems", "l3harris", "leidos",
            "spacex", "blue origin", "virgin galactic", "rocket lab",
            # === PHARMA & HEALTHCARE ===
            "pfizer", "johnson & johnson", "j&j", "moderna", "astrazeneca",
            "novartis", "roche", "merck", "sanofi", "gsk", "glaxosmithkline",
            "abbvie", "eli lilly", "bristol myers squibb", "amgen", "gilead",
            "unitedhealth", "anthem", "cigna", "humana", "cvs", "walgreens",
            # === RETAIL & CONSUMER ===
            "walmart", "costco", "target", "kroger", "home depot", "lowes",
            "nike", "adidas", "puma", "under armour", "lululemon",
            "coca-cola", "pepsi", "pepsico", "nestle", "unilever", "procter & gamble",
            "mcdonalds", "starbucks", "yum brands", "chipotle", "dominos",
            "lvmh", "gucci", "prada", "hermes", "chanel", "rolex",
            # === MEDIA & ENTERTAINMENT ===
            "disney", "warner bros", "universal", "paramount", "sony pictures",
            "netflix", "hbo", "hulu", "peacock", "discovery",
            "live nation", "spotify", "sirius xm", "iheartmedia",
            "electronic arts", "ea", "activision", "blizzard", "take-two",
            "epic games", "riot games", "valve", "nintendo", "playstation", "xbox",
            # === NEWS MEDIA ===
            "reuters", "associated press", "ap", "afp", "agence france-presse",
            "bbc", "cnn", "fox news", "msnbc", "nbc", "abc", "cbs", "pbs", "npr",
            "new york times", "washington post", "wall street journal", "wsj",
            "los angeles times", "chicago tribune", "usa today", "politico",
            "guardian", "times", "telegraph", "daily mail", "financial times", "ft",
            "economist", "bloomberg", "reuters", "al jazeera", "rt", "xinhua",
            "der spiegel", "le monde", "el pais", "corriere della sera",
            "sky news", "euronews", "dw", "france 24", "nhk", "abc australia",
            # === UNIVERSITIES ===
            "harvard", "yale", "princeton", "columbia", "cornell", "brown", "dartmouth", "penn",
            "mit", "stanford", "caltech", "berkeley", "ucla", "usc",
            "university of chicago", "duke", "northwestern", "johns hopkins",
            "oxford", "cambridge", "imperial college", "lse", "ucl",
            "eth zurich", "epfl", "sorbonne", "heidelberg", "tu munich",
            "university of tokyo", "kyoto university", "tsinghua", "peking university",
            "national university of singapore", "nus", "melbourne university",
            # === THINK TANKS & RESEARCH ===
            "brookings", "rand corporation", "cato institute", "heritage foundation",
            "council on foreign relations", "cfr", "chatham house", "carnegie",
            "peterson institute", "hoover institution", "american enterprise institute",
            # === SPORTS LEAGUES ===
            "nfl", "nba", "mlb", "nhl", "mls", "pga", "ufc", "wwe",
            "fifa", "uefa", "premier league", "la liga", "bundesliga", "serie a",
            "ioc", "olympic committee", "world athletics", "itf", "atp", "wta",
        }

        # Places & Landmarks (comprehensive)
        self.places = {
            # === US CITIES (Top 100+) ===
            "new york", "new york city", "nyc", "manhattan", "brooklyn", "queens", "bronx",
            "los angeles", "chicago", "houston", "phoenix", "philadelphia",
            "san antonio", "san diego", "dallas", "san jose", "austin",
            "jacksonville", "fort worth", "columbus", "charlotte", "san francisco",
            "indianapolis", "seattle", "denver", "washington", "washington dc", "dc",
            "boston", "el paso", "detroit", "nashville", "portland", "memphis",
            "oklahoma city", "las vegas", "louisville", "baltimore", "milwaukee",
            "albuquerque", "tucson", "fresno", "mesa", "sacramento", "atlanta",
            "kansas city", "colorado springs", "miami", "raleigh", "omaha",
            "long beach", "virginia beach", "oakland", "minneapolis", "tulsa",
            "tampa", "arlington", "new orleans", "wichita", "cleveland",
            "bakersfield", "aurora", "anaheim", "honolulu", "santa ana",
            "riverside", "corpus christi", "lexington", "st louis", "stockton",
            "pittsburgh", "anchorage", "cincinnati", "st paul", "newark",
            "greensboro", "plano", "henderson", "lincoln", "orlando",
            "jersey city", "chula vista", "buffalo", "fort wayne", "chandler",
            "st petersburg", "laredo", "durham", "irvine", "madison",
            "norfolk", "lubbock", "gilbert", "winston-salem", "glendale",
            "reno", "hialeah", "garland", "chesapeake", "irving", "north las vegas",
            "scottsdale", "baton rouge", "fremont", "richmond", "boise",
            "san bernardino", "birmingham", "spokane", "rochester", "modesto",
            "des moines", "oxnard", "tacoma", "fontana", "fayetteville",
            "moreno valley", "yonkers", "huntington beach", "salt lake city",
            "grand rapids", "amarillo", "montgomery", "little rock", "akron",
            "huntsville", "augusta", "port st lucie", "grand prairie", "tallahassee",
            "overland park", "tempe", "mckinney", "mobile", "cape coral", "shreveport",
            # === EUROPEAN CITIES ===
            "london", "manchester", "birmingham", "liverpool", "leeds", "sheffield",
            "bristol", "glasgow", "edinburgh", "cardiff", "belfast", "dublin",
            "newcastle", "nottingham", "southampton", "leicester", "portsmouth",
            "paris", "marseille", "lyon", "toulouse", "nice", "nantes",
            "strasbourg", "montpellier", "bordeaux", "lille", "rennes",
            "berlin", "hamburg", "munich", "cologne", "frankfurt", "stuttgart",
            "dusseldorf", "dortmund", "essen", "leipzig", "bremen", "dresden", "hanover",
            "rome", "milan", "naples", "turin", "palermo", "genoa", "bologna",
            "florence", "venice", "verona", "bari",
            "madrid", "barcelona", "valencia", "seville", "zaragoza", "malaga",
            "bilbao", "murcia", "palma",
            "amsterdam", "rotterdam", "the hague", "brussels", "antwerp",
            "vienna", "zurich", "geneva", "basel", "bern", "lisbon", "porto",
            "athens", "thessaloniki",
            "moscow", "st petersburg", "kyiv", "kiev", "kharkiv", "odesa", "odessa",
            "warsaw", "krakow", "lodz", "prague", "brno", "budapest",
            "bucharest", "sofia", "belgrade", "zagreb", "sarajevo", "skopje",
            "tirana", "pristina", "chisinau", "minsk", "vilnius", "riga", "tallinn",
            "stockholm", "gothenburg", "malmo", "oslo", "bergen", "copenhagen",
            "helsinki", "reykjavik",
            # === ASIAN CITIES ===
            "beijing", "shanghai", "guangzhou", "shenzhen", "chengdu", "hangzhou",
            "wuhan", "xian", "nanjing", "tianjin", "chongqing", "shenyang",
            "harbin", "dalian", "qingdao", "zhengzhou", "kunming", "changsha",
            "tokyo", "osaka", "kyoto", "yokohama", "nagoya", "sapporo", "kobe",
            "fukuoka", "kawasaki", "hiroshima", "sendai", "kitakyushu",
            "seoul", "busan", "incheon", "daegu", "daejeon", "gwangju", "ulsan",
            "delhi", "new delhi", "mumbai", "bombay", "bangalore", "bengaluru",
            "hyderabad", "chennai", "madras", "kolkata", "calcutta", "ahmedabad",
            "pune", "surat", "jaipur", "lucknow", "kanpur",
            "bangkok", "ho chi minh city", "saigon", "hanoi", "singapore",
            "kuala lumpur", "jakarta", "surabaya", "manila", "quezon city",
            "phnom penh", "yangon", "rangoon", "vientiane",
            "hong kong", "taipei", "kaohsiung", "macau", "ulaanbaatar",
            "karachi", "lahore", "islamabad", "dhaka", "chittagong",
            "colombo", "kathmandu", "kabul", "tashkent", "almaty", "astana",
            # === MIDDLE EAST CITIES ===
            "tehran", "baghdad", "basra", "mosul", "damascus", "aleppo",
            "jerusalem", "tel aviv", "haifa", "gaza city", "ramallah",
            "beirut", "amman", "riyadh", "jeddah", "mecca", "medina",
            "dubai", "abu dhabi", "doha", "kuwait city", "manama", "muscat",
            "sanaa", "aden", "ankara", "istanbul", "izmir", "antalya",
            # === AFRICAN CITIES ===
            "cairo", "alexandria", "giza", "lagos", "kano", "ibadan", "abuja",
            "johannesburg", "cape town", "durban", "pretoria", "nairobi", "mombasa",
            "addis ababa", "dar es salaam", "kampala", "kigali", "kinshasa",
            "luanda", "harare", "lusaka", "maputo", "accra", "dakar", "abidjan",
            "casablanca", "rabat", "algiers", "tunis", "tripoli", "khartoum",
            # === AMERICAS (non-US) ===
            "toronto", "montreal", "vancouver", "calgary", "edmonton", "ottawa",
            "winnipeg", "quebec city", "hamilton", "halifax",
            "mexico city", "guadalajara", "monterrey", "tijuana", "cancun",
            "guatemala city", "san salvador", "tegucigalpa", "managua",
            "panama city", "havana", "santo domingo", "san juan",
            "kingston", "port-au-prince",
            "sao paulo", "rio de janeiro", "brasilia", "salvador", "fortaleza",
            "buenos aires", "cordoba", "rosario", "bogota", "medellin", "cali",
            "lima", "santiago", "caracas", "maracaibo", "quito", "guayaquil",
            "la paz", "montevideo", "asuncion", "georgetown", "paramaribo",
            # === OCEANIA ===
            "sydney", "melbourne", "brisbane", "perth", "adelaide", "canberra",
            "auckland", "wellington", "christchurch", "suva", "port moresby",
            # === LANDMARKS & REGIONS ===
            "capitol hill", "wall street", "silicon valley", "hollywood",
            "times square", "central park", "ground zero", "las vegas strip",
            "golden gate", "liberty island", "pearl harbor", "mount rushmore",
            "grand canyon", "yellowstone", "yosemite", "niagara falls",
            "red square", "tiananmen square", "forbidden city", "great wall",
            "eiffel tower", "big ben", "buckingham palace", "westminster",
            "colosseum", "vatican city", "notre dame", "louvre", "versailles",
            "tower of london", "stonehenge", "acropolis", "parthenon",
            "taj mahal", "angkor wat", "machu picchu", "christ the redeemer",
            "kremlin", "downing street", "champs elysees", "brandenburg gate",
            "white house", "pentagon", "capitol building",
            "10 downing street", "elysee palace", "reichstag", "european parliament",
            "west bank", "gaza strip", "golan heights", "crimea", "donbas", "donetsk",
            "luhansk", "transnistria", "nagorno-karabakh", "south ossetia", "abkhazia",
            "kashmir", "tibet", "xinjiang",
            "middle east", "near east", "far east", "southeast asia", "south asia",
            "central asia", "east asia", "north africa", "sub-saharan africa",
            "western europe", "eastern europe", "northern europe", "southern europe",
            "latin america", "central america", "caribbean", "south america",
            "north america", "oceania", "australasia", "scandinavia", "balkans",
            "baltic states", "caucasus", "persian gulf", "arabian peninsula",
            "levant", "maghreb", "sahel",
            "atlantic", "pacific", "indian ocean", "arctic ocean", "antarctic",
            "mediterranean", "caribbean sea", "south china sea", "east china sea",
            "sea of japan", "black sea", "caspian sea", "red sea", "dead sea",
            "baltic sea", "north sea", "arabian sea", "bay of bengal",
            "gulf of mexico", "gulf of aden", "taiwan strait",
            "strait of hormuz", "strait of malacca", "english channel",
            "suez canal", "panama canal", "bosphorus",
        }

        # Events & Conflicts (comprehensive)
        self.events = {
            # === WORLD WARS ===
            "world war", "world war i", "world war ii", "wwi", "wwii",
            "first world war", "second world war", "great war",
            # === COLD WAR ERA ===
            "cold war", "iron curtain", "berlin wall", "cuban missile crisis",
            "korean war", "vietnam war", "soviet-afghan war",
            "bay of pigs", "space race", "arms race",
            # === MIDDLE EAST CONFLICTS ===
            "gulf war", "iraq war", "iran-iraq war",
            "war on terror", "afghanistan war", "operation enduring freedom",
            "operation iraqi freedom", "desert storm", "desert shield",
            "six day war", "yom kippur war", "arab-israeli war",
            "gaza war", "gaza conflict", "intifada", "first intifada", "second intifada",
            "lebanon war", "syrian civil war", "yemen civil war", "yemeni civil war",
            "libyan civil war", "isis insurgency",
            # === EUROPE/RUSSIA CONFLICTS ===
            "ukraine war", "russian invasion", "invasion of ukraine",
            "crimean annexation", "donbas war", "chechen war",
            "bosnian war", "kosovo war", "yugoslav wars", "balkan wars",
            "nagorno-karabakh war", "georgian war", "russo-georgian war",
            # === AFRICAN CONFLICTS ===
            "rwandan genocide", "darfur", "somali civil war", "ethiopian civil war",
            "tigray war", "congo war", "liberian civil war", "sierra leone civil war",
            "sudanese civil war", "south sudan civil war", "boko haram insurgency",
            # === ASIAN CONFLICTS ===
            "chinese civil war", "indo-pakistani war", "kashmir conflict",
            "sri lankan civil war", "rohingya crisis", "myanmar coup",
            "tiananmen square massacre", "tiananmen",
            # === AMERICAS CONFLICTS ===
            "american civil war", "mexican revolution",
            "cuban revolution", "nicaraguan revolution",
            "colombian conflict", "farc insurgency", "drug war",
            # === HISTORICAL EVENTS ===
            "french revolution", "russian revolution", "october revolution",
            "industrial revolution", "american revolution",
            "napoleonic wars", "hundred years war", "thirty years war",
            "crusades", "spanish civil war",
            # === TERRORISM & ATTACKS ===
            "9/11", "september 11", "september 11 attacks",
            "january 6", "jan 6", "january 6 insurrection", "capitol riot",
            "october 7", "october 7 attack", "hamas attack",
            "boston marathon bombing", "london bombings", "7/7",
            "paris attacks", "bataclan", "charlie hebdo",
            "madrid bombings", "mumbai attacks", "bali bombings",
            "oklahoma city bombing", "manchester arena bombing",
            "christchurch shooting", "las vegas shooting",
            # === DISASTERS & CRISES ===
            "covid", "covid-19", "pandemic", "coronavirus", "corona",
            "sars", "mers", "ebola", "swine flu", "bird flu",
            "financial crisis", "great recession", "subprime crisis",
            "fukushima", "chernobyl", "three mile island",
            "deepwater horizon", "exxon valdez",
            "hurricane katrina", "hurricane sandy", "hurricane maria",
            "indian ocean tsunami", "japan tsunami", "haiti earthquake",
            "california wildfires", "australian bushfires",
            # === POLITICAL EVENTS ===
            "brexit", "arab spring", "color revolution", "velvet revolution",
            "orange revolution", "euromaidan", "maidan",
            "tiananmen square", "hong kong protests", "umbrella movement",
            "watergate", "iran-contra", "monica lewinsky", "impeachment",
            "mueller investigation", "russia investigation",
            # === TREATIES & AGREEMENTS ===
            "paris agreement", "paris climate accord", "kyoto protocol",
            "geneva convention", "geneva conventions",
            "camp david", "camp david accords", "oslo accords",
            "dayton agreement", "good friday agreement", "belfast agreement",
            "iran nuclear deal", "jcpoa", "new start", "inf treaty",
            "versailles treaty", "treaty of versailles",
            "maastricht treaty", "lisbon treaty", "rome treaty",
            "abraham accords", "normalization agreement",
            # === SUMMITS & CONFERENCES ===
            "g7", "g7 summit", "g8", "g20", "g20 summit",
            "cop26", "cop27", "cop28", "cop29", "climate summit",
            "un general assembly", "unga", "security council",
            "davos", "world economic forum", "apec summit", "asean summit",
            "nato summit", "eu summit", "munich security conference",
            # === ELECTIONS ===
            "presidential election", "midterm elections", "general election",
            "brexit referendum", "scottish referendum", "quebec referendum",
            # === SPORTS EVENTS ===
            "olympics", "olympic games", "summer olympics", "winter olympics",
            "paralympics", "world cup", "fifa world cup", "euro",
            "super bowl", "world series", "nba finals", "stanley cup",
            "wimbledon", "us open", "french open", "australian open",
            "tour de france", "formula 1", "f1", "grand prix",
            "commonwealth games", "asian games", "pan american games",
        }

    def _apply_highlighting(self, text_widget: tk.Text, text: str):
        """Apply semantic highlighting to text in the widget."""
        import re

        # Clear previous wiki link targets
        self.wiki_link_targets = {}

        # Insert text first
        text_widget.insert("1.0", text)

        # Bold the first sentence (lede)
        first_sentence_end = None
        for i, char in enumerate(text):
            if char in ".!?" and i > 20:
                first_sentence_end = i + 1
                break
        if first_sentence_end:
            text_widget.tag_add("lede", "1.0", f"1.{first_sentence_end}")

        text_lower = text.lower()

        # Track highlighted ranges to avoid overlaps
        highlighted_ranges = []

        def is_overlapping(start, end):
            for s, e in highlighted_ranges:
                if start < e and end > s:
                    return True
            return False

        def add_highlight(start, end, tag, search_term=None):
            if is_overlapping(start, end):
                return False
            highlighted_ranges.append((start, end))
            start_idx = f"1.0+{start}c"
            end_idx = f"1.0+{end}c"
            text_widget.tag_add(tag, start_idx, end_idx)
            if search_term and tag in self.highlight_categories:
                self.wiki_link_targets[(start, end)] = (search_term, tag)
            return True

        # === NUMBERS (non-clickable) ===

        # 1. Money patterns
        money_patterns = [
            r'\$[\d,]+(?:\.\d+)?(?:\s*(?:million|billion|trillion))?',
            r'€[\d,]+(?:\.\d+)?(?:\s*(?:million|billion|trillion))?',
            r'£[\d,]+(?:\.\d+)?(?:\s*(?:million|billion|trillion))?',
            r'\b\d+(?:\.\d+)?\s*(?:dollars|euros|pounds|yen|yuan)',
        ]
        for pattern in money_patterns:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                add_highlight(match.start(), match.end(), "money")

        # 2. Statistics patterns
        stats_patterns = [
            r'\b\d+(?:\.\d+)?%',
            r'\b\d+(?:\.\d+)?\s*(?:percent|percentage)',
            r'\b\d{1,3}(?:,\d{3})+\b',
            r'\b\d+(?:\.\d+)?\s*(?:million|billion|trillion|thousand)\b',
            r'\b\d+\s*(?:people|troops|soldiers|casualties|deaths|injured|killed|wounded)',
        ]
        for pattern in stats_patterns:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                add_highlight(match.start(), match.end(), "statistics")

        # 3. Date patterns
        date_patterns = [
            r'\b(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2}(?:st|nd|rd|th)?(?:,?\s+\d{4})?',
            r'\b\d{1,2}(?:st|nd|rd|th)?\s+(?:January|February|March|April|May|June|July|August|September|October|November|December)(?:,?\s+\d{4})?',
            r'\b(?:Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday)',
            r'\b(?:last|next|this)\s+(?:week|month|year|Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday)',
        ]
        for pattern in date_patterns:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                add_highlight(match.start(), match.end(), "dates")

        # 4. Catch-all numbers (not already categorized)
        number_pattern = r'\b\d+(?:\.\d+)?\b'
        for match in re.finditer(number_pattern, text):
            add_highlight(match.start(), match.end(), "numbers")

        # 5. Verbs (news action words)
        verb_pattern = r'\b(?:said|says|told|announced|reported|confirmed|denied|claimed|stated|revealed|warned|urged|declared|signed|passed|voted|launched|arrested|killed|injured|died|added|noted|explained|described|called|asked|accused|blamed|praised|criticized|rejected|accepted|approved|condemned|demanded|proposed|suggested|argued|insisted|acknowledged|admitted|agreed|disagreed|promised|threatened|vowed|pledged|ordered|banned|blocked|suspended|fired|resigned|appointed|elected|defeated|won|lost|fled|escaped|attacked|invaded|bombed|shelled|seized|captured|released|freed|charged|sentenced|convicted|acquitted|testified|investigated|raided|searched|discovered|found|recovered|identified|named|cited|quoted)\b'
        for match in re.finditer(verb_pattern, text, re.IGNORECASE):
            add_highlight(match.start(), match.end(), "verbs")

        # === ENTITIES (clickable) ===

        # 4. Titles followed by names - match FIRST as one unit (e.g., "president Xi Jinping")
        for title in self.titles:
            pattern = r'\b(' + re.escape(title) + r'\s+[A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)'
            for match in re.finditer(pattern, text, re.IGNORECASE):
                full_phrase = match.group(1)
                add_highlight(match.start(), match.end(), "people", full_phrase)

        # 5. Find ALL capitalized word sequences, then classify them
        # This matches: "Zhang Youxia", "President Xi Jinping", "Central Military Commission"
        # Also handles possessives: "China's" -> "China"
        cap_sequence_pattern = r"([A-Z][a-z]+(?:[-'][a-z]+)?(?:\s+(?:of|the|and|for|de|von|van)?\s*[A-Z][a-z]+(?:[-'][a-z]+)?)*)"

        # Collect all sequences first
        sequences = []
        for match in re.finditer(cap_sequence_pattern, text):
            phrase = match.group(1)
            start = match.start()
            end = match.end()

            # Handle possessive 's at the end - include it in highlight but not search
            if end < len(text) and text[end:end+2] == "'s":
                display_end = end + 2
            else:
                display_end = end

            sequences.append((start, end, display_end, phrase))

        # Words to skip (sentence starters, common words)
        skip_words = {
            "the", "a", "an", "this", "that", "these", "those", "it", "its",
            "has", "have", "had", "been", "was", "were", "are", "is", "be",
            "said", "says", "told", "added", "noted", "asked", "called",
            "new", "many", "more", "most", "some", "all", "other", "such",
            "also", "just", "even", "still", "well", "back", "now", "then",
            "but", "and", "for", "not", "you", "his", "her", "their", "our",
            "first", "last", "next", "high", "low", "long", "short", "big",
            "according", "including", "during", "after", "before", "since",
            "while", "where", "when", "which", "what", "who", "how", "why",
            "continue", "reading", "here", "there", "very", "much", "far",
            "however", "although", "though", "because", "therefore", "thus",
        }

        # Classify and highlight each sequence
        for start, end, display_end, phrase in sequences:
            phrase_lower = phrase.lower()
            words = phrase.split()

            # Skip single common words
            if len(words) == 1 and words[0].lower() in skip_words:
                continue

            # Check if this is at sentence start (position 0 or after ". ")
            at_sentence_start = False
            if start == 0:
                at_sentence_start = True
            elif start > 1 and text[start-2:start] in (". ", "! ", "? "):
                at_sentence_start = True

            # At sentence start, only skip if it's a single common word
            # Multi-word sequences (names) at sentence start should still be highlighted
            if at_sentence_start and len(words) == 1:
                # Single word at sentence start - only highlight if known entity
                if phrase_lower not in self.countries and phrase_lower not in self.places and phrase_lower not in self.organizations:
                    continue

            # Determine category by checking against known entities and patterns
            category = None
            search_term = phrase

            # Check known entity databases (exact match)
            if phrase_lower in self.events:
                category = "events"
            elif phrase_lower in self.military:
                category = "military"
            elif phrase_lower in self.government:
                category = "government"
            elif phrase_lower in self.organizations:
                category = "organizations"
            elif phrase_lower in self.countries:
                category = "countries"
            elif phrase_lower in self.places:
                category = "places"

            # Check for title + name pattern (e.g., "President Xi Jinping")
            elif words[0].lower() in self.titles:
                category = "titles"
                # If more than just title, it's title + name
                if len(words) > 1:
                    # Highlight whole thing as title+person combined
                    category = "people"
                    search_term = " ".join(words[1:])  # Search just the name

            # Check for organizational patterns (X Y Commission/Ministry/etc.)
            elif any(w.lower() in {"commission", "committee", "council", "ministry",
                                   "department", "bureau", "agency", "authority",
                                   "administration", "board", "corps", "command"}
                    for w in words):
                category = "government"

            # Check for military patterns
            elif any(w.lower() in {"army", "navy", "force", "forces", "guard", "corps",
                                   "fleet", "brigade", "division", "regiment"}
                    for w in words):
                category = "military"

            # Check for organization patterns
            elif any(w.lower() in {"university", "college", "institute", "corporation",
                                   "company", "inc", "corp", "foundation", "association",
                                   "bank", "group", "trust"}
                    for w in words):
                category = "organizations"

            # Default: if 2-3 capitalized words, likely a person's name
            elif len(words) >= 2 and len(words) <= 3:
                # Check if all words look like name parts (not org keywords)
                looks_like_name = all(
                    w[0].isupper() and w.lower() not in skip_words
                    for w in words
                )
                if looks_like_name:
                    category = "people"

            # Single capitalized word in middle of sentence - check databases
            elif len(words) == 1:
                word = words[0]
                word_lower = word.lower()
                # Only highlight if it's a known entity
                if word_lower in self.countries:
                    category = "countries"
                elif word_lower in self.places:
                    category = "places"
                elif word_lower in self.organizations:
                    category = "organizations"
                # Otherwise skip single unknown words

            # Apply highlight if category was determined
            if category:
                add_highlight(start, display_end, category, search_term)


    def _on_wiki_link_click(self, event):
        """Handle click on wiki link - open Wikipedia search."""
        index = self.preview_text.index(f"@{event.x},{event.y}")
        line, char = index.split(".")
        char_offset = int(char)

        for (start, end), (search_term, category) in self.wiki_link_targets.items():
            if start <= char_offset < end:
                import urllib.parse
                query = urllib.parse.quote(search_term)
                url = f"https://en.wikipedia.org/wiki/Special:Search?search={query}&go=Go"
                webbrowser.open(url)
                return

    def _update_status(self, message: str):
        """Update the status bar."""
        self.status_bar.configure(text=message)

    def _on_key_up(self, event):
        """Handle Up arrow key - select previous article."""
        selection = self.articles_tree.selection()
        if not selection:
            # Select last item if nothing selected
            children = self.articles_tree.get_children()
            if children:
                self.articles_tree.selection_set(children[-1])
                self.articles_tree.see(children[-1])
            return "break"

        current = selection[0]
        prev_item = self.articles_tree.prev(current)
        if prev_item:
            self.articles_tree.selection_set(prev_item)
            self.articles_tree.see(prev_item)
        return "break"

    def _on_key_down(self, event):
        """Handle Down arrow key - select next article."""
        selection = self.articles_tree.selection()
        if not selection:
            # Select first item if nothing selected
            children = self.articles_tree.get_children()
            if children:
                self.articles_tree.selection_set(children[0])
                self.articles_tree.see(children[0])
            return "break"

        current = selection[0]
        next_item = self.articles_tree.next(current)
        if next_item:
            self.articles_tree.selection_set(next_item)
            self.articles_tree.see(next_item)
        return "break"

    def _on_key_toggle_read(self, event):
        """Handle M key - toggle read/unread status."""
        if self.selected_article_id:
            article = self.storage.get_article(self.selected_article_id)
            if article:
                new_status = not article["is_read"]
                self.storage.mark_article_read(self.selected_article_id, new_status)
                self.refresh_feeds_list()
                # Update just this row's tag
                tag = "read" if new_status else "unread"
                self.articles_tree.item(str(self.selected_article_id), tags=(tag,))
                self._update_status(f"Marked {'read' if new_status else 'unread'}")
        return "break"

    def _on_key_hide(self, event):
        """Handle H key - hide current article."""
        if self.selected_article_id:
            self._hide_article(self.selected_article_id)
        return "break"

    def _on_close(self):
        """Handle window close."""
        self._stop_ticker_animation()
        self.storage.close()
        self.root.destroy()


class AddFeedDialog:
    """Dialog for adding a new feed."""

    def __init__(self, parent, feed_manager: FeedManager):
        self.result = None
        self.feed_manager = feed_manager

        self.dialog = tk.Toplevel(parent)
        self.dialog.title("Add Feed")
        self.dialog.geometry("500x200")
        self.dialog.transient(parent)
        self.dialog.grab_set()
        self.dialog.configure(bg=DARK_THEME["bg"])

        # Center on parent
        self.dialog.geometry(f"+{parent.winfo_x() + 100}+{parent.winfo_y() + 100}")

        frame = ttk.Frame(self.dialog, padding=20)
        frame.pack(fill=tk.BOTH, expand=True)

        # URL
        ttk.Label(frame, text="Feed URL:").grid(row=0, column=0, sticky=tk.W, pady=5)
        self.url_var = tk.StringVar()
        self.url_entry = ttk.Entry(frame, textvariable=self.url_var, width=50)
        self.url_entry.grid(row=0, column=1, sticky=tk.EW, pady=5)

        # Name
        ttk.Label(frame, text="Name:").grid(row=1, column=0, sticky=tk.W, pady=5)
        self.name_var = tk.StringVar()
        self.name_entry = ttk.Entry(frame, textvariable=self.name_var, width=50)
        self.name_entry.grid(row=1, column=1, sticky=tk.EW, pady=5)

        # Category
        ttk.Label(frame, text="Category:").grid(row=2, column=0, sticky=tk.W, pady=5)
        self.category_var = tk.StringVar(value="Uncategorized")
        self.category_entry = ttk.Entry(frame, textvariable=self.category_var, width=50)
        self.category_entry.grid(row=2, column=1, sticky=tk.EW, pady=5)

        # Buttons
        btn_frame = ttk.Frame(frame)
        btn_frame.grid(row=3, column=0, columnspan=2, pady=20)

        ttk.Button(btn_frame, text="Validate", command=self._validate).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Add", command=self._add).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Cancel", command=self.dialog.destroy).pack(side=tk.LEFT, padx=5)

        # Status
        self.status_label = ttk.Label(frame, text="", foreground=DARK_THEME["fg_secondary"])
        self.status_label.grid(row=4, column=0, columnspan=2)

        frame.columnconfigure(1, weight=1)
        self.url_entry.focus()

        self.dialog.wait_window()

    def _validate(self):
        """Validate the feed URL."""
        url = self.url_var.get().strip()
        if not url:
            self.status_label.configure(text="Please enter a URL", foreground="#ff4444")
            return

        self.status_label.configure(text="Validating...", foreground=DARK_THEME["fg_secondary"])
        self.dialog.update()

        result = self.feed_manager.validate_feed_url(url)
        if result["valid"]:
            self.status_label.configure(
                text=f"Valid feed: {result['feed_title']} ({result['article_count']} articles)",
                foreground="#44ff44"
            )
            if not self.name_var.get():
                self.name_var.set(result["feed_title"])
        else:
            self.status_label.configure(text=f"Invalid: {result['error']}", foreground="#ff4444")

    def _add(self):
        """Add the feed."""
        url = self.url_var.get().strip()
        name = self.name_var.get().strip()
        category = self.category_var.get().strip() or "Uncategorized"

        if not url:
            self.status_label.configure(text="Please enter a URL", foreground="#ff4444")
            return

        if not name:
            self.status_label.configure(text="Please enter a name", foreground="#ff4444")
            return

        self.result = (name, url, category)
        self.dialog.destroy()


class ManageFeedsDialog:
    """Dialog for managing feeds."""

    def __init__(self, parent, storage: Storage):
        self.storage = storage
        self.changed = False

        self.dialog = tk.Toplevel(parent)
        self.dialog.title("Manage Feeds")
        self.dialog.geometry("600x400")
        self.dialog.transient(parent)
        self.dialog.grab_set()
        self.dialog.configure(bg=DARK_THEME["bg"])

        frame = ttk.Frame(self.dialog, padding=10)
        frame.pack(fill=tk.BOTH, expand=True)

        # Feeds list
        columns = ("name", "category", "url")
        self.tree = ttk.Treeview(frame, columns=columns, show="headings", selectmode="browse")
        self.tree.heading("name", text="Name")
        self.tree.heading("category", text="Category")
        self.tree.heading("url", text="URL")
        self.tree.column("name", width=150)
        self.tree.column("category", width=100)
        self.tree.column("url", width=300)
        self.tree.pack(fill=tk.BOTH, expand=True, side=tk.LEFT)

        scroll = ttk.Scrollbar(frame, orient=tk.VERTICAL, command=self.tree.yview)
        scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.tree.configure(yscrollcommand=scroll.set)

        # Buttons
        btn_frame = ttk.Frame(self.dialog, padding=10)
        btn_frame.pack(fill=tk.X)

        ttk.Button(btn_frame, text="Remove Selected", command=self._remove).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Close", command=self.dialog.destroy).pack(side=tk.RIGHT, padx=5)

        self._refresh()
        self.dialog.wait_window()

    def _refresh(self):
        """Refresh the feeds list."""
        self.tree.delete(*self.tree.get_children())
        for feed in self.storage.get_feeds(enabled_only=False):
            self.tree.insert("", tk.END, iid=str(feed["id"]),
                             values=(feed["name"], feed["category"], feed["url"]))

    def _remove(self):
        """Remove selected feed."""
        selection = self.tree.selection()
        if selection:
            feed_id = int(selection[0])
            feed = self.storage.get_feed(feed_id)
            if messagebox.askyesno("Confirm", f"Remove '{feed['name']}'?"):
                self.storage.remove_feed(feed_id)
                self.changed = True
                self._refresh()


class FilterKeywordsDialog:
    """Dialog for managing filter keywords."""

    def __init__(self, parent, storage: Storage):
        self.storage = storage
        self.changed = False

        self.dialog = tk.Toplevel(parent)
        self.dialog.title("Filter Keywords")
        self.dialog.geometry("500x400")
        self.dialog.transient(parent)
        self.dialog.grab_set()
        self.dialog.configure(bg=DARK_THEME["bg"])

        frame = ttk.Frame(self.dialog, padding=10)
        frame.pack(fill=tk.BOTH, expand=True)

        ttk.Label(frame, text="Custom keywords to flag as sensationalist:").pack(anchor=tk.W)

        # Keywords list
        list_frame = ttk.Frame(frame)
        list_frame.pack(fill=tk.BOTH, expand=True, pady=10)

        columns = ("keyword", "weight")
        self.tree = ttk.Treeview(list_frame, columns=columns, show="headings", selectmode="browse")
        self.tree.heading("keyword", text="Keyword")
        self.tree.heading("weight", text="Weight")
        self.tree.column("keyword", width=300)
        self.tree.column("weight", width=80)
        self.tree.pack(fill=tk.BOTH, expand=True, side=tk.LEFT)

        scroll = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.tree.yview)
        scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.tree.configure(yscrollcommand=scroll.set)

        # Add keyword frame
        add_frame = ttk.Frame(frame)
        add_frame.pack(fill=tk.X, pady=10)

        ttk.Label(add_frame, text="Keyword:").pack(side=tk.LEFT)
        self.keyword_var = tk.StringVar()
        ttk.Entry(add_frame, textvariable=self.keyword_var, width=30).pack(side=tk.LEFT, padx=5)

        ttk.Label(add_frame, text="Weight:").pack(side=tk.LEFT, padx=(10, 0))
        self.weight_var = tk.StringVar(value="10")
        ttk.Spinbox(add_frame, textvariable=self.weight_var, from_=1, to=50, width=5).pack(side=tk.LEFT, padx=5)

        ttk.Button(add_frame, text="Add", command=self._add).pack(side=tk.LEFT, padx=5)

        # Buttons
        btn_frame = ttk.Frame(frame)
        btn_frame.pack(fill=tk.X)

        ttk.Button(btn_frame, text="Remove Selected", command=self._remove).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Close", command=self.dialog.destroy).pack(side=tk.RIGHT, padx=5)

        self._refresh()
        self.dialog.wait_window()

    def _refresh(self):
        """Refresh the keywords list."""
        self.tree.delete(*self.tree.get_children())
        for kw in self.storage.get_filter_keywords(active_only=False):
            self.tree.insert("", tk.END, iid=str(kw["id"]),
                             values=(kw["keyword"], kw["weight"]))

    def _add(self):
        """Add a new keyword."""
        keyword = self.keyword_var.get().strip()
        if not keyword:
            return

        try:
            weight = int(self.weight_var.get())
        except ValueError:
            weight = 10

        result = self.storage.add_filter_keyword(keyword, weight)
        if result:
            self.changed = True
            self.keyword_var.set("")
            self._refresh()

    def _remove(self):
        """Remove selected keyword."""
        selection = self.tree.selection()
        if selection:
            keyword_id = int(selection[0])
            self.storage.remove_filter_keyword(keyword_id)
            self.changed = True
            self._refresh()
