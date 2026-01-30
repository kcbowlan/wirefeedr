# app.py - Tkinter GUI

import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
import webbrowser
import threading
from datetime import datetime
from typing import Optional
from urllib.parse import urlparse
import io
import math
import random
import sys
import os
import socket

# Sound support (Windows)
try:
    import winsound
    HAS_WINSOUND = True
except ImportError:
    HAS_WINSOUND = False

from PIL import Image, ImageDraw, ImageTk

from storage import Storage
from feeds import FeedManager
from filters import FilterEngine
from config import BIAS_COLORS, FACTUAL_COLORS, DARK_THEME


class NewsAggregatorApp:
    def __init__(self, root: tk.Tk):
        # Windows: set AppUserModelID so taskbar uses our icon instead of python.exe's
        if sys.platform == "win32":
            try:
                import ctypes
                ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("wirefeedr.app.1")
            except Exception:
                pass

        # Hidden owner provides taskbar presence + icon
        self._owner = root
        self._owner.title("WIREFEEDR")
        self._setup_owner_icon()
        self._owner.attributes("-alpha", 0)
        self._owner.geometry("1x1+-10000+-10000")

        # Real visible window as Toplevel (borderless via Win32 style stripping)
        self.root = tk.Toplevel(self._owner)
        self.root.title("WIREFEEDR")
        self.root.geometry("1200x700")
        self.root.minsize(900, 500)

        # Strip native title bar via Win32 API (keeps proper z-order unlike overrideredirect)
        self._strip_title_bar()

        # Restore from taskbar click on hidden owner
        self._owner.bind("<Map>", self._on_taskbar_restore)

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
        self._ticker_running = False

        # Animation state
        self._anim_frame = 0
        self._anim_id = None
        self._neon_panels = []
        self._is_maximized = False
        self._normal_geometry = ""
        self._drag_start_x = 0
        self._drag_start_y = 0
        self._drag_win_x = 0
        self._drag_win_y = 0

        # Gradient image cache (prevent GC of PhotoImages)
        self._gradient_cache = {}

        # Glitch effect (on refresh)
        self._glitch_active = False
        self._glitch_end_frame = 0

        # Feed glow (new articles)
        self._glowing_feeds = {}
        self._pre_refresh_counts = {}

        # Hover glow (article list)
        self._hover_item = None

        # Sash flash (panel divider)
        self._sash_flash_active = False
        self._sash_flash_end_frame = 0
        self._sash_dragging = False

        # Typewriter effect (preview)
        self._typewriter_active = False
        self._typewriter_words = []
        self._typewriter_pos = 0
        self._typewriter_chunk_size = 3
        self._typewriter_article_id = None
        self._typewriter_pending_highlight = False
        self._typewriter_full_text = ""

        # Idle status cycling (cyberpunk terminal messages)
        self._idle_messages = [
            # System operations
            "RETICULATING SPLINES",
            "DEFRAGMENTING NEURAL CACHE",
            "CALIBRATING BIAS MATRIX",
            "POLLING DEAD DROPS",
            "DECRYPTING FEED VECTORS",
            "SYNCHRONIZING REALITY ANCHORS",
            "COMPILING TRUTH ALGORITHMS",
            "SCANNING MEMETIC SIGNATURES",
            "BOOTSTRAPPING INFERENCE ENGINE",
            "VALIDATING SOURCE INTEGRITY",
            "CROSS-REFERENCING NARRATIVE THREADS",
            "PARSING PROPAGANDA RESIDUE",
            "INITIALIZING FACT-CHECK DAEMON",
            "PURGING CLICKBAIT BUFFERS",
            "ESTABLISHING SECURE CHANNEL",
            "RUNNING SENTIMENT ANALYSIS",
            "QUERYING ORACLE DATABASE",
            "HARMONIZING DATA STREAMS",
            "ENGAGING FILTER PROTOCOLS",
            "MONITORING INFO-SPHERE",
            "TRIANGULATING SIGNAL ORIGIN",
            "DECOMPILING SPIN MATRICES",
            "ALLOCATING SKEPTICISM UNITS",
            "CHARGING CRITICAL THINKING CAPACITORS",
            "LOADING CYNICISM MODULES",
            "VERIFYING CHAIN OF CUSTODY",
            "AUDITING TRUST LEDGER",
            "REFRESHING WORLDVIEW CACHE",
            "INDEXING CURRENT EVENTS",
            "PROCESSING ZEITGEIST TELEMETRY",
            "AWAITING SIGNAL",
            "STANDING BY",
            # Network operations
            "PINGING SHADOW SERVERS",
            "ROUTING THROUGH PROXY MESH",
            "HANDSHAKING WITH NODE CLUSTER",
            "TUNNELING ENCRYPTED PACKETS",
            "MAPPING NETWORK TOPOLOGY",
            "NEGOTIATING BANDWIDTH ALLOCATION",
            "RESOLVING DNS ANOMALIES",
            "AUTHENTICATING PEER CONNECTIONS",
            "LOAD BALANCING DATA STREAMS",
            "CACHING FREQUENTLY ACCESSED NODES",
            "ESTABLISHING TOR CIRCUIT",
            "BOUNCING THROUGH RELAYS",
            "SPOOFING MAC ADDRESS",
            "INJECTING PACKET HEADERS",
            "FRAGMENTING DATAGRAMS",
            "REASSEMBLING TCP STREAM",
            "PROBING OPEN PORTS",
            "SNIFFING TRAFFIC PATTERNS",
            "INTERCEPTING CLEARTEXT",
            "DECAPSULATING VPN TUNNEL",
            # Data processing
            "NORMALIZING INPUT VECTORS",
            "TOKENIZING HEADLINE CORPUS",
            "STEMMING LEXICAL ROOTS",
            "APPLYING BLOOM FILTERS",
            "HASHING CONTENT SIGNATURES",
            "DEDUPLICATING ARTICLE QUEUE",
            "COMPRESSING ARCHIVE SEGMENTS",
            "SERIALIZING STATE OBJECTS",
            "GARBAGE COLLECTING OLD REFS",
            "OPTIMIZING QUERY PLANS",
            "SHARDING DISTRIBUTED CACHE",
            "INDEXING INVERTED TREES",
            "BALANCING B-TREE NODES",
            "PRUNING DEAD BRANCHES",
            "VACUUMING DATABASE PAGES",
            "CHECKPOINTING WAL SEGMENTS",
            "COMPACTING STORAGE BLOCKS",
            "DEFRAGMENTING HEAP SPACE",
            "RECLAIMING ORPHAN INODES",
            "FSYNCING DIRTY BUFFERS",
            # Analysis operations
            "TRAINING CLASSIFIER WEIGHTS",
            "EVALUATING MODEL ACCURACY",
            "COMPUTING FEATURE VECTORS",
            "CLUSTERING TOPIC GROUPS",
            "RANKING BY RELEVANCE SCORE",
            "DETECTING ANOMALY PATTERNS",
            "PROFILING SOURCE BEHAVIOR",
            "MEASURING ENTROPY LEVELS",
            "CALCULATING TRUST SCORES",
            "BENCHMARKING THROUGHPUT",
            "EXTRACTING NAMED ENTITIES",
            "PARSING DEPENDENCY TREES",
            "RESOLVING COREFERENCES",
            "DETECTING STANCE POLARITY",
            "SCORING READABILITY INDEX",
            "ANALYZING LEXICAL DENSITY",
            "COMPUTING TF-IDF WEIGHTS",
            "BUILDING WORD EMBEDDINGS",
            "FINE-TUNING ATTENTION HEADS",
            "BACKPROPAGATING GRADIENTS",
            # Security operations
            "ROTATING ENCRYPTION KEYS",
            "SCANNING FOR INTRUSIONS",
            "VALIDATING CERTIFICATE CHAIN",
            "HARDENING FIREWALL RULES",
            "SANITIZING USER INPUT",
            "OBFUSCATING TRAFFIC PATTERNS",
            "AUDITING ACCESS LOGS",
            "PATCHING KNOWN VULNERABILITIES",
            "ENFORCING RATE LIMITS",
            "QUARANTINING SUSPECT PAYLOADS",
            "VERIFYING DIGITAL SIGNATURES",
            "SALTING PASSWORD HASHES",
            "GENERATING ENTROPY POOL",
            "SEEDING RANDOM ORACLE",
            "ESTABLISHING ZERO KNOWLEDGE",
            "COMPUTING MERKLE ROOTS",
            "SIGNING BLOCKCHAIN TRANSACTION",
            "VALIDATING SMART CONTRACT",
            "REVOKING COMPROMISED CERTS",
            "ROTATING SECRET KEYS",
            # Cyberpunk flavor - Neuromancer
            "JACKING INTO THE MATRIX",
            "GHOSTING THROUGH ICE",
            "FLATLINE RECOVERY PROTOCOL",
            "DUMPING CYBERSPACE COORDS",
            "TRACING BLACK ICE SIGNATURE",
            "UPLOADING CONSCIOUSNESS BACKUP",
            "DECKING THE MAINFRAME",
            "PARSING WETWARE SIGNALS",
            "OVERCLOCKING NEURAL LINK",
            "STABILIZING MEAT-MACHINE INTERFACE",
            "FRAGMENTING DIGITAL PERSONA",
            "REROUTING THROUGH CHIBA CITY",
            "SCANNING FOR RAZORGIRLS",
            "CONSULTING STREET SAMURAI DB",
            "BOOTING ICEBREAKER SUITE",
            "MONITORING MEGACORP CHATTER",
            "INTERCEPTING ZAIBATSU COMMS",
            "DECRYPTING YAKUZA PROTOCOLS",
            "RUNNING INTRUSION COUNTERMEASURES",
            "DODGING ATTACK BARRIERS",
            # Cyberpunk flavor - Blade Runner
            "ANALYZING VOIGHT-KAMPFF RESULTS",
            "SCANNING FOR REPLICANTS",
            "ENHANCING ESPER PHOTOGRAPH",
            "TRACKING NEXUS-6 SIGNATURES",
            "ACCESSING TYRELL ARCHIVES",
            "DECODING ORIGAMI MESSAGE",
            "SEARCHING OFF-WORLD COLONIES",
            "RETIRING ROGUE UNITS",
            "PARSING MEMORY IMPLANTS",
            "VERIFYING BASELINE TEST",
            # Cyberpunk flavor - Ghost in the Shell
            "DIVING INTO THE NET",
            "SCANNING GHOST SIGNATURES",
            "TRACING PUPPET MASTER",
            "HACKING CYBERBRAIN",
            "UPLOADING TO SHELL",
            "SYNCHRONIZING TACHIKOMAS",
            "DEPLOYING THERMOPTIC CAMO",
            "ANALYZING STAND ALONE COMPLEX",
            "INTERCEPTING SECTION 9 COMMS",
            "GHOSTHACKING BARRIER MAZE",
            # Cyberpunk flavor - Misc
            "SLOTTING SKILLSOFT CHIP",
            "JACKING CYBERDECK INTERFACE",
            "BURNING CHROME BARRIERS",
            "RUNNING DAEMON PROCESSES",
            "SPAWNING ICE BREAKERS",
            "EXECUTING ZERO-DAY EXPLOIT",
            "SPOOFING BIOMETRIC SCAN",
            "FORGING DIGITAL IDENTITY",
            "LAUNDERING CRYPTO FUNDS",
            "ERASING DIGITAL FOOTPRINT",
            "PLANTING LOGIC BOMB",
            "ACTIVATING KILLSWITCH",
            "RELEASING POLYMORPHIC VIRUS",
            "DEPLOYING RANSOMWARE PAYLOAD",
            "HIJACKING BOTNET SWARM",
            "POISONING DNS CACHE",
            "INJECTING SQL PAYLOAD",
            "ESCALATING PRIVILEGES",
            "PIVOTING THROUGH NETWORK",
            "EXFILTRATING SENSITIVE DATA",
            # Hacker culture
            "READING THE JARGON FILE",
            "INVOKING HACKTIVIST PROTOCOL",
            "CONSULTING THE MENTOR",
            "ENTERING GIBSON CYBERSPACE",
            "LOADING ANARCHIST COOKBOOK",
            "RUNNING WARDIALERS",
            "PHREAKING PHONE SYSTEMS",
            "CRACKING WEP ENCRYPTION",
            "RAINBOW TABLE LOOKUP",
            "BRUTE FORCING CREDENTIALS",
            # Retro computing
            "LOADING PUNCH CARDS",
            "REWINDING MAGNETIC TAPE",
            "ALIGNING DISK HEADS",
            "BOOTING FROM FLOPPY",
            "DEFRAGMENTING FAT TABLE",
            "CLEARING CMOS BATTERY",
            "UPDATING BIOS FIRMWARE",
            "EXPANDING CONVENTIONAL MEMORY",
            "LOADING HIMEM.SYS",
            "RUNNING MEMTEST86",
            # Misc technical
            "SPINNING UP WORKER THREADS",
            "FLUSHING MEMORY BUFFERS",
            "REBUILDING SEARCH INDEX",
            "MIGRATING SCHEMA VERSION",
            "REBALANCING SHARD DISTRIBUTION",
            "WARMING PREDICTION CACHE",
            "SNAPSHOTTING SYSTEM STATE",
            "REPLAYING EVENT LOG",
            "MERGING CONFLICT BRANCHES",
            "ROLLING BACK FAILED TRANSACTION",
            "FORKING CHILD PROCESS",
            "JOINING WORKER POOL",
            "ACQUIRING MUTEX LOCK",
            "RELEASING SEMAPHORE",
            "SIGNALING CONDITION VARIABLE",
            "POLLING EPOLL DESCRIPTOR",
            "AWAITING FUTEX WAKE",
            "YIELDING TIME SLICE",
            "PREEMPTING LOW PRIORITY",
            "SCHEDULING REAL-TIME TASK",
            # AI/ML operations
            "TRAINING NEURAL NETWORK",
            "ADJUSTING HYPERPARAMETERS",
            "MINIMIZING LOSS FUNCTION",
            "APPLYING DROPOUT MASK",
            "NORMALIZING BATCH INPUTS",
            "COMPUTING ATTENTION SCORES",
            "GENERATING EMBEDDINGS",
            "SAMPLING LATENT SPACE",
            "DECODING TRANSFORMER OUTPUT",
            "CALIBRATING CONFIDENCE SCORES",
            "RUNNING INFERENCE PASS",
            "QUANTIZING MODEL WEIGHTS",
            "PRUNING SPARSE CONNECTIONS",
            "DISTILLING KNOWLEDGE",
            "FINE-TUNING FOUNDATION MODEL",
            "PROMPTING LANGUAGE MODEL",
            "ALIGNING WITH HUMAN FEEDBACK",
            "REDUCING HALLUCINATIONS",
            "GROUNDING IN REALITY",
            "VERIFYING FACTUAL CLAIMS",
            # News/media specific
            "FILTERING EDITORIAL BIAS",
            "DETECTING SPIN PATTERNS",
            "MEASURING HEADLINE VALENCE",
            "ANALYZING FRAMING EFFECTS",
            "TRACKING NARRATIVE SHIFT",
            "IDENTIFYING ASTROTURF",
            "FLAGGING COORDINATED INAUTHENTIC",
            "SCORING SOURCE CREDIBILITY",
            "CROSS-CHECKING WIRE SERVICES",
            "VERIFYING PRIMARY SOURCES",
            "DEBUNKING VIRAL CLAIMS",
            "TRACING INFORMATION CASCADE",
            "MAPPING ECHO CHAMBERS",
            "DETECTING FILTER BUBBLES",
            "ANALYZING ENGAGEMENT BAIT",
            "SCORING HEADLINE ACCURACY",
            "MEASURING CONTEXT COLLAPSE",
            "TRACKING AMPLIFICATION NETWORK",
            "IDENTIFYING BOT ACTIVITY",
            "FLAGGING SYNTHETIC MEDIA",
            # Status messages
            "ALL SYSTEMS NOMINAL",
            "OPERATING WITHIN PARAMETERS",
            "MAINTAINING VIGILANCE",
            "SIGNAL STRENGTH OPTIMAL",
            "FEED INTEGRITY VERIFIED",
            "NO ANOMALIES DETECTED",
            "READY FOR INPUT",
            "CHANNELS CLEAR",
            "HOLDING PATTERN",
            "MONITORING ACTIVE",
            "STANDING BY FOR ORDERS",
            "PERIMETER SECURE",
            "THREAT LEVEL MINIMAL",
            "COGNITIVE LOAD NOMINAL",
            "BANDWIDTH SUFFICIENT",
            "LATENCY ACCEPTABLE",
            "UPTIME 99.97 PERCENT",
            "ZERO ERRORS LOGGED",
            "QUEUE DEPTH STABLE",
            "ENTROPY POOL FULL",
        ]
        self._idle_active = True
        self._idle_message_index = 0
        self._idle_char_pos = 0
        self._idle_display_frames = 0  # How long to show completed message
        self._idle_last_real_status = ""
        self._idle_pause_until = 0  # Frame to resume idle cycling

        # Build UI
        self._setup_styles()
        self._build_title_bar()
        self._build_menus()
        self._bind_shortcuts()
        self._build_toolbar()
        self._build_ticker()
        self._build_status_bar()  # Pack BOTTOM elements first so they survive resize
        self._build_main_layout()
        self._build_resize_grip()
        # Corner decorations removed — overlapped with content

        # Register neon panels for pulsing
        # (widget, color_key, cycle_period_in_frames) — different speeds per panel
        self._neon_panels = [
            (self.feeds_frame, "cyan", 90),       # ~3s cycle
            (self.articles_frame, "cyan", 120),    # ~4s cycle
            (self.preview_frame, "magenta", 150),  # ~5s cycle
        ]

        # Load initial data
        self.refresh_feeds_list()
        self.refresh_articles()

        # Cleanup old articles if 48+ hours since last cleanup
        self._auto_cleanup_old_articles()

        # Start auto-refresh if enabled
        self._schedule_auto_refresh()

        # Bind window close
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

        # Ensure the window is visible and focused
        self.root.deiconify()
        self.root.lift()
        self.root.focus_force()

        # Boot sequence (starts animation loop when complete)
        self._play_boot_sequence()

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

    def _build_title_bar(self):
        """Build neon border frame around entire window."""
        self.max_btn = None
        self.title_bar = None
        t = DARK_THEME

        # Create border canvases (top, bottom, left, right)
        border_thickness = 2

        self._border_top = tk.Canvas(self.root, height=border_thickness, bg=t["bg"], highlightthickness=0)
        self._border_top.pack(side=tk.TOP, fill=tk.X)

        self._border_bottom = tk.Canvas(self.root, height=border_thickness, bg=t["bg"], highlightthickness=0)
        self._border_bottom.pack(side=tk.BOTTOM, fill=tk.X)

        self._border_left = tk.Canvas(self.root, width=border_thickness, bg=t["bg"], highlightthickness=0)
        self._border_left.pack(side=tk.LEFT, fill=tk.Y)

        self._border_right = tk.Canvas(self.root, width=border_thickness, bg=t["bg"], highlightthickness=0)
        self._border_right.pack(side=tk.RIGHT, fill=tk.Y)

        # For compatibility with existing code
        self.title_neon_line = self._border_top

    def _build_menus(self):
        """Pre-build popup menus for the custom title bar."""
        _m = dict(bg=DARK_THEME["bg_secondary"], fg=DARK_THEME["fg"],
                  activebackground=DARK_THEME["magenta"],
                  activeforeground=DARK_THEME["fg_highlight"], tearoff=0)

        # Settings menu (consolidated)
        self._settings_menu = tk.Menu(self.root, **_m)

        # Feeds submenu
        self._feeds_submenu = tk.Menu(self._settings_menu, **_m)
        self._feeds_submenu.add_command(label="Add Feed...", command=self.show_add_feed_dialog)
        self._feeds_submenu.add_command(label="Manage Feeds...", command=self.show_manage_feeds_dialog)
        self._settings_menu.add_cascade(label="Feeds", menu=self._feeds_submenu)

        # Articles submenu
        self._articles_submenu = tk.Menu(self._settings_menu, **_m)
        self._articles_submenu.add_command(label="Mark All as Read", command=self.mark_all_read)
        self._articles_submenu.add_command(label="Delete Old Articles...", command=self.show_delete_old_dialog)
        self._settings_menu.add_cascade(label="Articles", menu=self._articles_submenu)

        self._settings_menu.add_separator()

        # Recency submenu
        self._recency_submenu = tk.Menu(self._settings_menu, **_m)
        self._recency_var = tk.StringVar(value=self.storage.get_setting("recency_hours", "24"))
        for label, value in [("6 hours", "6"), ("12 hours", "12"), ("24 hours", "24"),
                             ("48 hours", "48"), ("1 week", "168"), ("All time", "0")]:
            self._recency_submenu.add_radiobutton(
                label=label, variable=self._recency_var, value=value,
                command=lambda v=value: self._set_recency(v))
        self._settings_menu.add_cascade(label="Recency", menu=self._recency_submenu)

        # Per Source submenu
        self._per_source_submenu = tk.Menu(self._settings_menu, **_m)
        self._per_source_var = tk.StringVar(value=self.storage.get_setting("max_per_source", "10"))
        for label, value in [("5 per source", "5"), ("10 per source", "10"), ("15 per source", "15"),
                             ("20 per source", "20"), ("No limit", "0")]:
            self._per_source_submenu.add_radiobutton(
                label=label, variable=self._per_source_var, value=value,
                command=lambda v=value: self._set_per_source(v))
        self._settings_menu.add_cascade(label="Per Source", menu=self._per_source_submenu)

        # Cluster toggle
        self._cluster_var = tk.BooleanVar(value=self.storage.get_setting("cluster_topics", "True") == "True")
        self._settings_menu.add_checkbutton(label="Cluster Topics", variable=self._cluster_var,
                                            command=self._on_cluster_toggle)

        self._settings_menu.add_separator()
        self._settings_menu.add_command(label="Filter Keywords...", command=self.show_filter_keywords_dialog)
        self._settings_menu.add_separator()
        self._settings_menu.add_command(label="Exit", command=self._on_close)

    def _show_settings_menu(self, event):
        self._settings_menu.tk_popup(event.widget.winfo_rootx(),
                                      event.widget.winfo_rooty() + event.widget.winfo_height())

    def _bind_shortcuts(self):
        """Bind keyboard shortcuts."""
        self.root.bind("<F5>", lambda e: self.fetch_all_feeds())
        # Note: Up/Down arrow bindings moved to articles_tree in _build_main_layout
        self.root.bind("<Return>", lambda e: self.open_in_browser())
        self.root.bind("m", self._on_key_toggle_read)
        self.root.bind("M", self._on_key_toggle_read)
        self.root.bind("h", self._on_key_hide)
        self.root.bind("H", self._on_key_hide)

    def _build_toolbar(self):
        """Build the toolbar with gradient background (also serves as drag handle)."""
        t = DARK_THEME

        # Container frame for toolbar
        toolbar_container = tk.Frame(self.root, bg=t["bg_secondary"])
        toolbar_container.pack(side=tk.TOP, fill=tk.X, padx=0, pady=0)

        # Gradient canvas placed behind widgets via place()
        self._toolbar_canvas = tk.Canvas(
            toolbar_container, highlightthickness=0, bg=t["bg_secondary"]
        )
        self._toolbar_canvas.place(x=0, y=0, relwidth=1.0, relheight=1.0)

        # The actual toolbar frame sits on top of the canvas
        self.toolbar = tk.Frame(toolbar_container, bg=t["bg_secondary"])
        self.toolbar.pack(fill=tk.X)
        toolbar = self.toolbar

        # Drag bindings for borderless window
        toolbar.bind("<Button-1>", self._start_drag)
        toolbar.bind("<B1-Motion>", self._do_drag)
        toolbar.bind("<ButtonRelease-1>", self._end_drag)
        toolbar.bind("<Double-1>", lambda e: self._toggle_maximize())
        # Also bind drag on the canvas for the gap areas
        self._toolbar_canvas.bind("<Button-1>", self._start_drag)
        self._toolbar_canvas.bind("<B1-Motion>", self._do_drag)
        self._toolbar_canvas.bind("<ButtonRelease-1>", self._end_drag)
        self._toolbar_canvas.bind("<Double-1>", lambda e: self._toggle_maximize())

        # Refresh button
        self.refresh_btn = self._create_gradient_button(
            toolbar, "\u21bb Refresh", self.fetch_all_feeds
        )
        self.refresh_btn.pack(side=tk.LEFT, padx=2)

        # Mark all read button
        self._mark_all_btn = self._create_gradient_button(
            toolbar, "\u2713 Mark All Read", self.mark_all_read
        )
        self._mark_all_btn.pack(side=tk.LEFT, padx=2)

        # Separator
        ttk.Separator(toolbar, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=10)

        # Show read articles checkbox
        self.show_read_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(toolbar, text="Show Read", variable=self.show_read_var,
                        command=self.refresh_articles).pack(side=tk.LEFT, padx=5)

        # Window controls (far right)
        btn_style = dict(
            bg=t["bg_secondary"], fg=t["fg"],
            font=("Segoe UI Symbol", 10), bd=0, padx=6, pady=1,
            activebackground=t["bg_tertiary"], activeforeground=t["fg_highlight"],
            width=2
        )

        close_btn = tk.Button(toolbar, text="\u2715", command=self._on_close, **btn_style)
        close_btn.pack(side=tk.RIGHT, padx=(2, 0))
        close_btn.bind("<Enter>", lambda e: e.widget.configure(bg="#cc0000", fg="#ffffff"))
        close_btn.bind("<Leave>", lambda e: e.widget.configure(bg=t["bg_secondary"], fg=t["fg"]))

        self.max_btn = tk.Button(toolbar, text="\u25fb", command=self._toggle_maximize, **btn_style)
        self.max_btn.pack(side=tk.RIGHT, padx=1)
        self.max_btn.bind("<Enter>", lambda e: e.widget.configure(bg=t["cyan_dim"], fg=t["cyan"]))
        self.max_btn.bind("<Leave>", lambda e: e.widget.configure(bg=t["bg_secondary"], fg=t["fg"]))

        min_btn = tk.Button(toolbar, text="\u2012", command=self._minimize_window, **btn_style)
        min_btn.pack(side=tk.RIGHT, padx=1)
        min_btn.bind("<Enter>", lambda e: e.widget.configure(bg=t["cyan_dim"], fg=t["cyan"]))
        min_btn.bind("<Leave>", lambda e: e.widget.configure(bg=t["bg_secondary"], fg=t["fg"]))

        # Separator before window controls
        ttk.Separator(toolbar, orient=tk.VERTICAL).pack(side=tk.RIGHT, fill=tk.Y, padx=8)

        # Clear button (rightmost before window controls)
        self._clear_btn = self._create_gradient_button(
            toolbar, "Clear", self.clear_search
        )
        self._clear_btn.pack(side=tk.RIGHT, padx=2)

        # Filter entry
        self.search_var = tk.StringVar()
        self.search_var.trace_add("write", self._on_search_changed)
        self.search_entry = ttk.Entry(toolbar, textvariable=self.search_var, width=25)
        self.search_entry.pack(side=tk.RIGHT, padx=2)
        ttk.Label(toolbar, text="Filter:").pack(side=tk.RIGHT, padx=(5, 5))

        # Settings button (left of Filter)
        self._settings_btn = tk.Label(
            toolbar, text="\u2699 SETTINGS",
            bg=t["bg_tertiary"], fg=t["cyan"],
            font=("Consolas", 9), padx=8, pady=2, cursor="hand2"
        )
        self._settings_btn.pack(side=tk.RIGHT, padx=(5, 10))
        self._settings_btn.bind("<Button-1>", self._show_settings_menu)
        self._settings_btn.bind("<Enter>", lambda e: e.widget.configure(fg=t["magenta"]))
        self._settings_btn.bind("<Leave>", lambda e: e.widget.configure(fg=t["cyan"]))

        # Separator after left buttons
        ttk.Separator(toolbar, orient=tk.VERTICAL).pack(side=tk.RIGHT, fill=tk.Y, padx=8)

        # Bind resize to redraw gradient
        toolbar_container.bind("<Configure>", self._on_toolbar_configure)

    def _on_toolbar_configure(self, event):
        """Redraw toolbar gradient on resize."""
        w = event.width
        h = event.height
        if w < 10 or h < 2:
            return
        photo = self._create_gradient_image(w, h, "#0a1028", "#280a18", cache_key="toolbar_grad")
        if photo:
            self._toolbar_canvas.delete("all")
            self._toolbar_canvas.create_image(0, 0, anchor=tk.NW, image=photo)

    def _draw_panel_header(self, canvas, text, color1, color2, cache_key):
        """Draw a gradient background and centered text on a panel header canvas."""
        w = canvas.winfo_width()
        h = canvas.winfo_height()
        if w < 10 or h < 2:
            return
        photo = self._create_gradient_image(w, h, color1, color2, cache_key=cache_key)
        if photo:
            canvas.delete("all")
            canvas.create_image(0, 0, anchor=tk.NW, image=photo, tags="bg")
            canvas.create_text(
                w // 2, h // 2, text=text, fill=DARK_THEME["cyan"],
                font=("Consolas", 9, "bold"), anchor=tk.CENTER, tags="header_text"
            )

    def _create_gradient_button(self, parent, text, command, disabled=False):
        """Create a canvas-based button with diagonal gradient fill.

        Returns the canvas widget. Stores an '_enabled' attribute for state management.
        """
        t = DARK_THEME
        font = ("Consolas", 9)
        # Measure text to size the canvas
        tmp = tk.Label(parent, text=text, font=font)
        tmp.update_idletasks()
        text_w = tmp.winfo_reqwidth()
        text_h = tmp.winfo_reqheight()
        tmp.destroy()
        pad_x, pad_y = 12, 4
        btn_w = text_w + pad_x * 2
        btn_h = text_h + pad_y * 2

        canvas = tk.Canvas(parent, width=btn_w, height=btn_h,
                           highlightthickness=0, bg=t["bg_tertiary"], cursor="hand2")
        canvas._btn_text = text
        canvas._btn_command = command
        canvas._btn_w = btn_w
        canvas._btn_h = btn_h
        canvas._btn_enabled = not disabled

        # Draw initial state
        self._draw_gradient_btn(canvas, hover=False)

        # Bindings
        canvas.bind("<Enter>", lambda e, c=canvas: self._on_grad_btn_enter(c))
        canvas.bind("<Leave>", lambda e, c=canvas: self._on_grad_btn_leave(c))
        canvas.bind("<Button-1>", lambda e, c=canvas: self._on_grad_btn_click(c))

        return canvas

    def _draw_gradient_btn(self, canvas, hover=False):
        """Redraw a gradient button's background and text."""
        w = canvas._btn_w
        h = canvas._btn_h
        enabled = canvas._btn_enabled
        t = DARK_THEME

        if not enabled:
            c1, c2 = "#0c0c18", "#180c14"
            text_color = t["fg_secondary"]
        elif hover:
            c1, c2 = "#2a1250", "#50122a"
            text_color = t["fg_highlight"]
        else:
            c1, c2 = "#0a1028", "#280a18"
            text_color = t["cyan"]

        key = f"gbtn_{id(canvas)}_{hover}_{enabled}"
        photo = self._create_gradient_image(w, h, c1, c2, cache_key=key)
        canvas.delete("all")
        if photo:
            canvas.create_image(0, 0, anchor=tk.NW, image=photo)
        canvas.create_text(
            w // 2, h // 2, text=canvas._btn_text, fill=text_color,
            font=("Consolas", 9), anchor=tk.CENTER
        )

    def _on_grad_btn_enter(self, canvas):
        if canvas._btn_enabled:
            self._draw_gradient_btn(canvas, hover=True)

    def _on_grad_btn_leave(self, canvas):
        self._draw_gradient_btn(canvas, hover=False)

    def _on_grad_btn_click(self, canvas):
        if canvas._btn_enabled and canvas._btn_command:
            canvas._btn_command()

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

    def _ticker_step(self):
        """Move ticker items left by speed pixels. Called by master animation loop."""
        if not self.ticker_paused and self.ticker_total_width > 0:
            self.ticker_canvas.move("ticker_text", -self.ticker_speed, 0)
            self.ticker_offset += self.ticker_speed

            if self.ticker_offset >= self.ticker_total_width:
                self.ticker_canvas.move("ticker_text", self.ticker_total_width, 0)
                self.ticker_offset -= self.ticker_total_width

    def _start_ticker_animation(self):
        """Flag ticker as running (driven by master animation loop)."""
        self._ticker_running = True

    def _stop_ticker_animation(self):
        """Flag ticker as stopped."""
        self._ticker_running = False

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
        self.feeds_frame = tk.LabelFrame(
            self.main_paned, text="",
            bg=DARK_THEME["bg"], fg=DARK_THEME["cyan"],
            font=("Consolas", 10, "bold"),
            highlightbackground=DARK_THEME["cyan_dim"],
            highlightcolor=DARK_THEME["cyan"],
            highlightthickness=2, bd=0, relief=tk.FLAT,
            padx=5, pady=5
        )
        feeds_frame = self.feeds_frame
        self.main_paned.add(feeds_frame, weight=1)

        # Gradient header bar
        self._feeds_header = tk.Canvas(feeds_frame, height=20, highlightthickness=0,
                                        bg=DARK_THEME["bg_secondary"])
        self._feeds_header.pack(fill=tk.X, pady=(0, 3))
        self._feeds_header.bind("<Configure>", lambda e: self._draw_panel_header(
            self._feeds_header, "FEEDS", "#0a1028", "#1a0a20", "feeds_hdr"))

        # Branding at bottom (pack first so it stays at bottom)
        branding_frame = tk.Frame(feeds_frame, bg=DARK_THEME["bg"])
        branding_frame.pack(side=tk.BOTTOM, fill=tk.X, pady=(5, 0))

        # Load logo (use taskbar icon) - clickable link to Patreon
        try:
            logo_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "icon_preview.png")
            self._logo_image = tk.PhotoImage(file=logo_path)
            w, h = self._logo_image.width(), self._logo_image.height()
            if h > 28:
                factor = max(1, h // 28)
                self._logo_image = self._logo_image.subsample(factor, factor)
            logo_label = tk.Label(branding_frame, image=self._logo_image, bg=DARK_THEME["bg"], cursor="hand2")
            logo_label.pack(side=tk.LEFT, padx=(0, 6))
            logo_label.bind("<Button-1>", lambda e: webbrowser.open("https://www.patreon.com/kcbowlan"))
            logo_label.bind("<Enter>", lambda e: self._show_logo_tooltip(e))
            logo_label.bind("<Leave>", lambda e: self._hide_logo_tooltip(e))
        except Exception:
            pass

        # Large WIREFEEDR text to span panel
        self.title_label = tk.Label(
            branding_frame, text="WIREFEEDR",
            bg=DARK_THEME["bg"], fg=DARK_THEME["cyan"],
            font=("Consolas", 16, "bold")
        )
        self.title_label.pack(side=tk.LEFT)

        tk.Label(
            branding_frame, text="v2.1",
            bg=DARK_THEME["bg"], fg=DARK_THEME["fg_secondary"],
            font=("Consolas", 9)
        ).pack(side=tk.LEFT, padx=(4, 0), pady=(8, 0))

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
        self.right_paned = ttk.PanedWindow(self.main_paned, orient=tk.VERTICAL)
        right_paned = self.right_paned
        self.main_paned.add(right_paned, weight=4)

        # Articles list
        self.articles_frame = tk.LabelFrame(
            right_paned, text="",
            bg=DARK_THEME["bg"], fg=DARK_THEME["cyan"],
            font=("Consolas", 10, "bold"),
            highlightbackground=DARK_THEME["cyan_dim"],
            highlightcolor=DARK_THEME["cyan"],
            highlightthickness=2, bd=0, relief=tk.FLAT,
            padx=5, pady=5
        )
        articles_frame = self.articles_frame
        right_paned.add(articles_frame, weight=2)

        # Gradient header bar
        self._articles_header = tk.Canvas(articles_frame, height=20, highlightthickness=0,
                                           bg=DARK_THEME["bg_secondary"])
        self._articles_header.pack(fill=tk.X, pady=(0, 3))
        self._articles_header.bind("<Configure>", lambda e: self._draw_panel_header(
            self._articles_header, "ARTICLES", "#0a1028", "#1a0a20", "articles_hdr"))

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
        # Arrow key navigation - bound to tree to prevent default double-movement
        self.articles_tree.bind("<Up>", self._on_key_up)
        self.articles_tree.bind("<Down>", self._on_key_down)

        # Configure tags for read/unread styling
        self.articles_tree.tag_configure("unread", font=("TkDefaultFont", 9, "bold"),
                                          foreground=DARK_THEME["fg"])
        self.articles_tree.tag_configure("read", foreground=DARK_THEME["fg_secondary"])
        self.articles_tree.tag_configure("hover", background="#1a1a2e")

        # Hover glow on article rows
        self.articles_tree.bind("<Motion>", self._on_article_hover)
        self.articles_tree.bind("<Leave>", self._on_article_leave)

        # Preview panel
        self.preview_frame = tk.LabelFrame(
            right_paned, text="",
            bg=DARK_THEME["bg"], fg=DARK_THEME["magenta"],
            font=("Consolas", 10, "bold"),
            highlightbackground=DARK_THEME["magenta_dim"],
            highlightcolor=DARK_THEME["magenta"],
            highlightthickness=2, bd=0, relief=tk.FLAT,
            padx=5, pady=5
        )
        preview_frame = self.preview_frame
        right_paned.add(preview_frame, weight=1)

        # Gradient header bar (magenta-tinted for preview)
        self._preview_header = tk.Canvas(preview_frame, height=20, highlightthickness=0,
                                          bg=DARK_THEME["bg_secondary"])
        self._preview_header.pack(fill=tk.X, pady=(0, 3))
        self._preview_header.bind("<Configure>", lambda e: self._draw_panel_header(
            self._preview_header, "PREVIEW", "#1a0a28", "#280a18", "preview_hdr"))

        # Sash flash bindings
        for paned in [self.main_paned, self.right_paned]:
            paned.bind("<ButtonPress-1>", self._on_sash_press)
            paned.bind("<ButtonRelease-1>", self._on_sash_release)

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

        self.open_btn = self._create_gradient_button(
            btn_frame, "Open in Browser", self.open_in_browser, disabled=True
        )
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

        # Preview text with scrollbar (scrollbar must be packed first to appear on right)
        preview_text_scroll = ttk.Scrollbar(preview_frame, orient=tk.VERTICAL)
        preview_text_scroll.pack(side=tk.RIGHT, fill=tk.Y, pady=5)

        self.preview_text = tk.Text(preview_frame, wrap=tk.WORD, height=8, state=tk.DISABLED,
                                     bg=DARK_THEME["bg_tertiary"], fg=DARK_THEME["fg"],
                                     insertbackground=DARK_THEME["cyan"],
                                     relief=tk.FLAT, padx=10, pady=10,
                                     yscrollcommand=preview_text_scroll.set)
        self.preview_text.pack(fill=tk.BOTH, expand=True, pady=5)

        preview_text_scroll.configure(command=self.preview_text.yview)

        # Configure semantic highlighting tags
        self._setup_highlight_tags()

    def _build_status_bar(self):
        """Build the cyberpunk status bar."""
        t = DARK_THEME
        status_frame = tk.Frame(self.root, bg=t["status_bg"], height=24)
        status_frame.pack(side=tk.BOTTOM, fill=tk.X)
        status_frame.pack_propagate(False)

        # Left: Cyberpunk progress bar (segmented blocks with gradient)
        self._progress_frame = tk.Frame(status_frame, bg=t["status_bg"])
        self._progress_frame.pack(side=tk.LEFT, padx=(8, 0))

        # Progress bar canvas (20 segments, wider)
        self._progress_segments = 20
        self._progress_seg_width = 12
        self._progress_seg_height = 12
        self._progress_gap = 2
        canvas_width = self._progress_segments * (self._progress_seg_width + self._progress_gap)
        self._progress_canvas = tk.Canvas(
            self._progress_frame, width=canvas_width, height=self._progress_seg_height,
            bg=t["status_bg"], highlightthickness=0
        )
        self._progress_canvas.pack(side=tk.LEFT, pady=6)

        # Create segment rectangles
        self._progress_rects = []
        for i in range(self._progress_segments):
            x = i * (self._progress_seg_width + self._progress_gap)
            rect = self._progress_canvas.create_rectangle(
                x, 0, x + self._progress_seg_width, self._progress_seg_height,
                fill=t["bg_tertiary"], outline=""
            )
            self._progress_rects.append(rect)

        # Progress percentage label
        self._progress_label = tk.Label(
            self._progress_frame, text="",
            bg=t["status_bg"], fg=t["cyan"],
            font=("Consolas", 9)
        )
        self._progress_label.pack(side=tk.LEFT, padx=(4, 0))

        # Hide progress bar initially
        self._progress_frame.pack_forget()
        self._progress_value = 0

        # Blinking block cursor (pack first so it's on far right)
        self._cursor_label = tk.Label(
            status_frame, text="\u2588",
            bg=t["status_bg"], fg=t["cyan"],
            font=("Consolas", 12)  # Larger for chunky look
        )
        self._cursor_label.pack(side=tk.RIGHT, padx=(0, 20))

        # Right-aligned status text (to left of cursor)
        self.status_bar = tk.Label(
            status_frame, text="", anchor=tk.E,
            bg=t["status_bg"], fg=t["cyan"],
            font=("Consolas", 9)
        )
        self.status_bar.pack(side=tk.RIGHT, padx=(8, 0))

    def _show_progress(self):
        """Show the progress bar."""
        self._progress_frame.pack(side=tk.LEFT, padx=(8, 0))
        self._progress_value = 0
        self._update_progress(0)

    def _hide_progress(self):
        """Hide the progress bar."""
        self._progress_frame.pack_forget()

    def _update_progress(self, percent: float):
        """Update progress bar with gradient fill (magenta -> cyan)."""
        t = DARK_THEME
        self._progress_value = percent
        filled = int((percent / 100) * self._progress_segments)

        for i, rect in enumerate(self._progress_rects):
            if i < filled:
                # Gradient from magenta to cyan based on position
                ratio = i / max(self._progress_segments - 1, 1)
                color = self._lerp_color(t["magenta"], t["cyan"], ratio)
                self._progress_canvas.itemconfigure(rect, fill=color)
            else:
                # Empty segment
                self._progress_canvas.itemconfigure(rect, fill=t["bg_tertiary"])

        # Update percentage text
        self._progress_label.configure(text=f"{int(percent)}%")

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

        # Get filter values from settings menu variables
        recency_hours = int(self._recency_var.get())
        max_per_source = int(self._per_source_var.get())
        use_clustering = self._cluster_var.get()

        articles = self.storage.get_articles(
            feed_id=self.current_feed_id,
            include_read=include_read,
            min_score=0,  # Show all scores, let user judge
            recency_hours=recency_hours,
            max_per_source=max_per_source
        )

        # Apply real-time search filter
        search_term = self.search_var.get().strip().lower()
        if search_term:
            articles = [a for a in articles if search_term in a.get("title", "").lower()
                        or search_term in a.get("summary", "").lower()]

        # Apply clustering if enabled
        if use_clustering and self.current_feed_id is None:
            clusters = self.filter_engine.cluster_articles(articles)
            self._display_clustered_articles(clusters)
            total_articles = sum(c["count"] for c in clusters)
            self._update_status(f"Showing {len(clusters)} topics ({total_articles} articles)")
        else:
            self._display_flat_articles(articles)
            self._update_status(f"Showing {len(articles)} articles")

        # Update read counter in articles frame title
        self._update_read_counter(articles)

        self._update_ticker()

    def _update_read_counter(self, articles: list):
        """Update the articles header canvas with read count."""
        total = len(articles)
        read = sum(1 for a in articles if a.get("is_read", False))
        text = f"ARTICLES ({read}/{total} READ)" if total > 0 else "ARTICLES"
        # Update the text on the gradient header canvas
        text_items = self._articles_header.find_withtag("header_text")
        if text_items:
            self._articles_header.itemconfigure(text_items[0], text=text)
        else:
            # Header not drawn yet — force a redraw with updated text
            self._draw_panel_header(
                self._articles_header, text, "#0a1028", "#1a0a20", "articles_hdr"
            )

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
        self.refresh_btn._btn_enabled = False
        self._draw_gradient_btn(self.refresh_btn, hover=False)
        self._update_status("Fetching feeds...")
        self._show_progress()
        self._start_glitch()
        self._snapshot_feed_counts()

        def fetch_thread():
            feeds = self.storage.get_feeds()
            total = len(feeds)
            success_count = 0
            article_count = 0

            for i, feed in enumerate(feeds):
                progress = ((i + 1) / total) * 100
                self.root.after(0, lambda f=feed, idx=i, p=progress: (
                    self._update_status(f"Fetching {f['name']}... ({idx + 1}/{total})"),
                    self._update_progress(p)
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
                self.refresh_btn._btn_enabled = True
                self._draw_gradient_btn(self.refresh_btn, hover=False)
                self._hide_progress()
                self.refresh_feeds_list()
                self.refresh_articles()
                self._detect_new_article_feeds()
                self._update_status(
                    f"Fetched {success_count}/{total} feeds, {article_count} new articles"
                )

            self.root.after(0, finish)

        thread = threading.Thread(target=fetch_thread, daemon=True)
        thread.start()

    def _play_cyber_modem_sound(self):
        """Play a pleasant cyber-modem chirp sound on refresh."""
        if not HAS_WINSOUND:
            return

        def play_sound():
            try:
                # Pleasant ascending digital chirp sequence
                # Frequencies chosen for a "data transfer" feel without being harsh
                tones = [
                    (800, 30),   # Start tone
                    (1200, 25),  # Rising
                    (1600, 20),  # Peak
                    (1400, 25),  # Slight dip
                    (1800, 20),  # Higher peak
                    (2200, 15),  # Quick chirp
                    (1600, 30),  # Settle
                    (2000, 20),  # Another chirp
                    (1200, 40),  # Descend
                ]
                for freq, duration in tones:
                    winsound.Beep(freq, duration)
            except Exception:
                pass  # Silently fail if sound doesn't work

        # Play in background thread so it doesn't block UI
        threading.Thread(target=play_sound, daemon=True).start()

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
            initialvalue=2,
            minvalue=1,
            maxvalue=365
        )
        if days:
            count = self.storage.delete_old_articles(days)
            self.refresh_feeds_list()
            self.refresh_articles()
            messagebox.showinfo("Done", f"Deleted {count} old articles.")

    def _auto_cleanup_old_articles(self):
        """Automatically delete old articles every 48 hours."""
        import time
        last_cleanup = self.storage.get_setting("last_auto_cleanup", "0")
        last_cleanup_time = float(last_cleanup)
        now = time.time()
        hours_since = (now - last_cleanup_time) / 3600

        if hours_since >= 48:
            retention_days = int(self.storage.get_setting("article_retention_days", "2"))
            count = self.storage.delete_old_articles(retention_days)
            self.storage.set_setting("last_auto_cleanup", str(now))
            if count > 0:
                self.update_status(f"Auto-purged {count} old articles")

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

            self.preview_meta.configure(text=meta)

            self.preview_text.configure(state=tk.NORMAL)
            self.preview_text.delete("1.0", tk.END)
            self.preview_text.configure(state=tk.DISABLED)

            summary = article.get("summary", "No summary available.")
            self._start_typewriter(summary, article_id)

            self.open_btn._btn_enabled = True
            self._draw_gradient_btn(self.open_btn, hover=False)

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

    def _set_recency(self, hours: str):
        """Handle recency setting change."""
        self.storage.set_setting("recency_hours", hours)
        self.refresh_articles()

    def _set_per_source(self, value: str):
        """Handle per-source cap setting change."""
        self.storage.set_setting("max_per_source", value)
        self.refresh_articles()

    def _on_cluster_toggle(self):
        """Handle cluster checkbox toggle."""
        self.storage.set_setting("cluster_topics", str(self._cluster_var.get()))
        self.refresh_articles()

    def _on_search_changed(self, *args):
        """Handle real-time search filtering."""
        self.refresh_articles()

    def _schedule_auto_refresh(self):
        """Schedule automatic feed refresh."""
        if self.auto_refresh_job:
            self.root.after_cancel(self.auto_refresh_job)

        minutes = int(self.storage.get_setting("auto_refresh_minutes", "60"))
        if minutes > 0:
            ms = minutes * 60 * 1000
            self.auto_refresh_job = self.root.after(ms, self._auto_refresh)

    def _auto_refresh(self):
        """Perform automatic refresh."""
        self._auto_cleanup_old_articles()
        if not self.is_fetching:
            self.fetch_all_feeds()
        self._schedule_auto_refresh()

    def _setup_highlight_tags(self):
        """Configure text tags for semantic highlighting."""
        # Bold for first sentence (lede)
        # lede tag removed — no special formatting for first sentence

        # Entity categories (clickable Wikipedia links) — bright for dark bg
        self.highlight_categories = {
            "people": "#00e5e5",      # Bright Cyan
            "titles": "#da70d6",      # Orchid
            "government": "#9d8bff",  # Bright Lavender
            "military": "#6cb4e6",    # Light Steel Blue
            "organizations": "#50e650", # Bright Green
            "countries": "#ff9d3a",   # Bright Orange
            "places": "#e08850",      # Light Sienna
            "events": "#f0c050",      # Bright Goldenrod
            "proper_nouns": "#00ffa0", # Electric Mint — unknown proper nouns
        }

        # Number categories (not clickable) — bright for dark bg
        self.number_categories = {
            "money": "#ff50a0",       # Bright Pink
            "statistics": "#ff88cc",  # Bright Hot Pink
            "dates": "#ff7098",       # Bright Rose
            "numbers": "#ffe040",     # Bright Yellow
        }

        # Verb categories (not clickable) — colors chosen for thematic meaning
        self.verb_categories = {
            "verb_communication": "#87ceeb",  # Sky Blue — clear as open air, neutral transmission
            "verb_accusation": "#dc143c",     # Crimson — blood, anger, pointed finger
            "verb_support": "#90ee90",        # Light Green — growth, thumbs up, go signal
            "verb_agreement": "#40e0d0",      # Turquoise — harmony, meeting of waters
            "verb_decision": "#9370db",       # Medium Purple — royal decree, judge's robe
            "verb_political": "#8b008b",      # Dark Magenta — imperial purple, power
            "verb_military": "#8b0000",       # Dark Red — blood of battle, Mars
            "verb_legal": "#ffd700",          # Gold — scales of justice, law's weight
            "verb_economic": "#228b22",       # Forest Green — money, wealth, growth
            "verb_discovery": "#00bfff",      # Deep Sky Blue — eureka, illumination, insight
            "verb_change": "#ff8c00",         # Dark Orange — autumn leaves, transformation
            "verb_creation": "#00fa9a",       # Medium Spring Green — new life, genesis
            "verb_movement": "#b0c4de",       # Light Steel Blue — wind, motion, travel
            "verb_emotion": "#ff69b4",        # Hot Pink — the heart, passion, feeling
            "verb_prevention": "#4682b4",     # Steel Blue — shield, barrier, protection
            "verb_competition": "#ffa500",    # Orange — trophy, medal, fire of competition
            "verb_medical": "#20b2aa",        # Light Sea Green — clinical, healing, triage
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

        # Configure tags for verbs (not clickable)
        for tag, color in self.verb_categories.items():
            self.preview_text.tag_configure(tag, foreground=color)

        # Related articles section (yellow)
        self.preview_text.tag_configure("related_header", foreground=DARK_THEME["neon_yellow"], font=("Consolas", 9, "bold"))

        # Store related article targets (populated in _finish_typewriter)
        self._related_article_targets = {}

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

        # Heads of State & Notable Leaders (current + recent, with name variants)
        self.leaders = {
            # === UNITED STATES - PRESIDENTS (All 46) ===
            "biden", "joe biden", "joseph biden", "president biden", "joseph r biden",
            "trump", "donald trump", "president trump", "donald j trump",
            "obama", "barack obama", "president obama", "barack hussein obama",
            "bush", "george bush", "george w bush", "president bush", "george h w bush", "bush sr", "bush jr",
            "clinton", "bill clinton", "president clinton", "william clinton",
            "reagan", "ronald reagan", "president reagan", "the gipper",
            "carter", "jimmy carter", "president carter", "james earl carter",
            "nixon", "richard nixon", "president nixon", "tricky dick",
            "ford", "gerald ford", "president ford",
            "kennedy", "john f kennedy", "jfk", "president kennedy", "john kennedy", "jack kennedy",
            "johnson", "lyndon johnson", "lbj", "lyndon b johnson",
            "eisenhower", "dwight eisenhower", "ike", "dwight d eisenhower",
            "truman", "harry truman", "president truman", "harry s truman",
            "roosevelt", "franklin roosevelt", "fdr", "franklin d roosevelt",
            "theodore roosevelt", "teddy roosevelt", "tr",
            "hoover", "herbert hoover", "president hoover",
            "coolidge", "calvin coolidge", "silent cal",
            "harding", "warren harding", "warren g harding",
            "wilson", "woodrow wilson", "president wilson",
            "taft", "william taft", "william howard taft",
            "mckinley", "william mckinley", "president mckinley",
            "cleveland", "grover cleveland",
            "harrison", "benjamin harrison", "william henry harrison",
            "arthur", "chester arthur", "chester a arthur",
            "garfield", "james garfield", "james a garfield",
            "hayes", "rutherford hayes", "rutherford b hayes",
            "grant", "ulysses grant", "ulysses s grant", "general grant",
            "andrew johnson", "president johnson",
            "lincoln", "abraham lincoln", "abe lincoln", "president lincoln", "honest abe",
            "buchanan", "james buchanan",
            "pierce", "franklin pierce",
            "fillmore", "millard fillmore",
            "taylor", "zachary taylor",
            "polk", "james polk", "james k polk",
            "tyler", "john tyler",
            "van buren", "martin van buren",
            "jackson", "andrew jackson", "old hickory",
            "adams", "john adams", "john quincy adams", "samuel adams",
            "jefferson", "thomas jefferson", "president jefferson",
            "washington", "george washington", "president washington", "general washington",

            # === UNITED STATES - FOUNDING FATHERS & EARLY LEADERS ===
            "benjamin franklin", "ben franklin", "franklin",
            "alexander hamilton", "hamilton",
            "james madison", "madison",
            "james monroe", "monroe",
            "john jay",
            "patrick henry",
            "paul revere",
            "john hancock",
            "thomas paine",
            "aaron burr", "burr",
            "betsy ross",

            # === UNITED STATES - CIVIL WAR ERA ===
            "robert e lee", "general lee", "lee",
            "stonewall jackson", "thomas jackson",
            "ulysses s grant", "general grant",
            "william sherman", "general sherman", "sherman",
            "jefferson davis",
            "john brown",
            "harriet tubman", "tubman",
            "frederick douglass", "douglass",
            "clara barton",
            "sojourner truth",

            # === UNITED STATES - CIVIL RIGHTS LEADERS ===
            "martin luther king", "mlk", "dr king", "martin luther king jr", "reverend king",
            "rosa parks",
            "malcolm x", "malcolm little", "el-hajj malik el-shabazz",
            "john lewis", "congressman lewis",
            "medgar evers",
            "thurgood marshall", "justice marshall",
            "booker t washington",
            "w e b du bois", "du bois",
            "ida b wells",
            "jesse jackson", "reverend jackson",
            "al sharpton", "reverend sharpton",
            "coretta scott king",
            "ralph abernathy",
            "stokely carmichael",
            "huey newton",
            "angela davis",
            "cesar chavez",
            "dolores huerta",

            # === UNITED STATES - SUPREME COURT JUSTICES ===
            "john roberts", "chief justice roberts", "roberts",
            "clarence thomas", "justice thomas",
            "samuel alito", "justice alito", "alito",
            "sonia sotomayor", "justice sotomayor", "sotomayor",
            "elena kagan", "justice kagan", "kagan",
            "neil gorsuch", "justice gorsuch", "gorsuch",
            "brett kavanaugh", "justice kavanaugh", "kavanaugh",
            "amy coney barrett", "justice barrett", "barrett",
            "ketanji brown jackson", "justice jackson",
            "ruth bader ginsburg", "rbg", "justice ginsburg", "ginsburg",
            "antonin scalia", "justice scalia", "scalia",
            "anthony kennedy", "justice kennedy",
            "sandra day oconnor", "oconnor",
            "john paul stevens",
            "david souter",
            "earl warren", "chief justice warren",

            # === UNITED STATES - VICE PRESIDENTS & FIRST LADIES ===
            "kamala harris", "harris", "vice president harris",
            "mike pence", "pence", "vice president pence",
            "dick cheney", "cheney", "vice president cheney",
            "al gore", "gore", "vice president gore",
            "dan quayle", "quayle",
            "walter mondale", "mondale",
            "nelson rockefeller",
            "spiro agnew", "agnew",
            "hubert humphrey", "humphrey",
            "hillary clinton", "hillary rodham clinton", "secretary clinton",
            "michelle obama", "first lady obama",
            "melania trump", "first lady trump",
            "jill biden", "dr jill biden",
            "laura bush", "first lady bush",
            "barbara bush",
            "nancy reagan", "first lady reagan",
            "jacqueline kennedy", "jackie kennedy", "jackie o",
            "eleanor roosevelt", "first lady roosevelt",

            # === UNITED STATES - CABINET & KEY OFFICIALS ===
            "blinken", "antony blinken", "secretary blinken",
            "pompeo", "mike pompeo", "secretary pompeo",
            "tillerson", "rex tillerson",
            "kerry", "john kerry", "secretary kerry",
            "hillary clinton", "secretary clinton",
            "condoleezza rice", "condi rice", "secretary rice",
            "colin powell", "general powell", "secretary powell",
            "madeleine albright", "secretary albright",
            "austin", "lloyd austin", "secretary austin",
            "mattis", "james mattis", "general mattis", "mad dog mattis",
            "esper", "mark esper",
            "rumsfeld", "donald rumsfeld", "secretary rumsfeld",
            "yellen", "janet yellen", "secretary yellen",
            "mnuchin", "steven mnuchin",
            "geithner", "timothy geithner",
            "paulson", "hank paulson", "henry paulson",
            "garland", "merrick garland", "attorney general garland",
            "barr", "william barr", "bill barr", "attorney general barr",
            "sessions", "jeff sessions", "attorney general sessions",
            "holder", "eric holder", "attorney general holder",
            "comey", "james comey", "director comey",
            "mueller", "robert mueller", "special counsel mueller",

            # === UNITED STATES - MILITARY LEADERS ===
            "general milley", "mark milley", "milley",
            "general petraeus", "david petraeus", "petraeus",
            "general mcchrystal", "stanley mcchrystal",
            "norman schwarzkopf", "stormin norman",
            "wesley clark",
            "douglas macarthur", "general macarthur", "macarthur",
            "george patton", "general patton", "patton",
            "omar bradley", "general bradley",
            "chester nimitz", "admiral nimitz",
            "john pershing", "general pershing", "black jack pershing",

            # === UNITED STATES - CONGRESSIONAL LEADERS ===
            "pelosi", "nancy pelosi", "speaker pelosi",
            "mccarthy", "kevin mccarthy", "speaker mccarthy",
            "johnson", "mike johnson", "speaker johnson",
            "schumer", "chuck schumer", "senator schumer", "majority leader schumer",
            "mcconnell", "mitch mcconnell", "senator mcconnell", "minority leader mcconnell",
            "aoc", "alexandria ocasio-cortez", "ocasio-cortez",
            "bernie sanders", "sanders", "senator sanders",
            "elizabeth warren", "warren", "senator warren",
            "ted cruz", "cruz", "senator cruz",
            "marco rubio", "rubio", "senator rubio",
            "mitt romney", "romney", "senator romney",
            "rand paul", "senator paul",
            "lindsey graham", "graham", "senator graham",
            "joe manchin", "manchin", "senator manchin",
            "kyrsten sinema", "sinema",
            "adam schiff", "schiff", "representative schiff",
            "jim jordan", "jordan", "representative jordan",
            "marjorie taylor greene", "mtg",
            "matt gaetz", "gaetz",
            "newt gingrich", "gingrich", "speaker gingrich",
            "tip oneill", "oneill",
            "bob dole", "dole", "senator dole",
            "john mccain", "mccain", "senator mccain",
            "ted kennedy", "senator kennedy",
            "robert kennedy", "rfk", "bobby kennedy",

            # === UNITED STATES - GOVERNORS & STATE LEADERS ===
            "desantis", "ron desantis", "governor desantis",
            "newsom", "gavin newsom", "governor newsom",
            "abbott", "greg abbott", "governor abbott",
            "cuomo", "andrew cuomo", "governor cuomo",
            "hochul", "kathy hochul", "governor hochul",
            "pritzker", "jb pritzker",
            "whitmer", "gretchen whitmer", "governor whitmer",
            "kemp", "brian kemp",
            "noem", "kristi noem",
            "haley", "nikki haley", "ambassador haley",
            "polis", "jared polis",
            "schwarzenegger", "arnold schwarzenegger", "governor schwarzenegger",
            "jerry brown", "governor brown",
            "rudy giuliani", "giuliani", "mayor giuliani",
            "bloomberg", "michael bloomberg", "mayor bloomberg",
            "de blasio", "bill de blasio",
            "eric adams", "mayor adams",

            # === UNITED STATES - OTHER NOTABLE FIGURES ===
            "elon musk", "musk",
            "jeff bezos", "bezos",
            "mark zuckerberg", "zuckerberg", "zuck",
            "bill gates", "gates",
            "warren buffett", "buffett",
            "steve jobs", "jobs",
            "tim cook",
            "sam altman",
            "henry kissinger", "kissinger", "secretary kissinger",
            "zbigniew brzezinski", "brzezinski",
            "george soros", "soros",
            "koch", "charles koch", "david koch", "koch brothers",
            "rupert murdoch", "murdoch",
            "oprah", "oprah winfrey",
            "tucker carlson", "carlson",
            "sean hannity", "hannity",
            "rachel maddow", "maddow",
            "alex jones",
            "rush limbaugh", "limbaugh",
            "bob woodward", "woodward",
            "carl bernstein", "bernstein",
            "edward snowden", "snowden",
            "julian assange", "assange",
            "chelsea manning", "manning",

            # === UNITED KINGDOM (Monarchs, PMs) ===
            "king charles", "charles iii", "king charles iii",
            "queen elizabeth", "elizabeth ii", "queen elizabeth ii",
            "prince william", "william", "prince of wales",
            "prince harry", "harry", "duke of sussex",
            "kate middleton", "catherine", "princess of wales",
            "meghan markle", "meghan", "duchess of sussex",
            "starmer", "keir starmer", "prime minister starmer", "sir keir starmer",
            "sunak", "rishi sunak", "prime minister sunak",
            "truss", "liz truss", "prime minister truss",
            "boris johnson", "johnson", "prime minister johnson",
            "theresa may", "may", "prime minister may",
            "david cameron", "cameron", "prime minister cameron",
            "gordon brown", "brown", "prime minister brown",
            "tony blair", "blair", "prime minister blair",
            "john major", "major",
            "thatcher", "margaret thatcher", "prime minister thatcher", "baroness thatcher",

            # === CANADA ===
            "trudeau", "justin trudeau", "prime minister trudeau", "pierre trudeau",
            "harper", "stephen harper",
            "chretien", "jean chretien",
            "mulroney", "brian mulroney",
            "poilievre", "pierre poilievre",

            # === FRANCE ===
            "macron", "emmanuel macron", "president macron",
            "hollande", "francois hollande", "president hollande",
            "sarkozy", "nicolas sarkozy", "president sarkozy",
            "chirac", "jacques chirac",
            "mitterrand", "francois mitterrand",
            "de gaulle", "charles de gaulle", "general de gaulle",
            "le pen", "marine le pen", "jean-marie le pen",
            "melenchon", "jean-luc melenchon",
            "attal", "gabriel attal", "prime minister attal",
            "borne", "elisabeth borne",

            # === GERMANY ===
            "scholz", "olaf scholz", "chancellor scholz",
            "merkel", "angela merkel", "chancellor merkel",
            "schroeder", "gerhard schroeder", "chancellor schroeder",
            "kohl", "helmut kohl", "chancellor kohl",
            "steinmeier", "frank-walter steinmeier", "president steinmeier",
            "habeck", "robert habeck",
            "lindner", "christian lindner",
            "baerbock", "annalena baerbock",

            # === ITALY ===
            "meloni", "giorgia meloni", "prime minister meloni",
            "draghi", "mario draghi", "prime minister draghi",
            "conte", "giuseppe conte",
            "berlusconi", "silvio berlusconi",
            "renzi", "matteo renzi",
            "salvini", "matteo salvini",
            "mattarella", "sergio mattarella", "president mattarella",

            # === SPAIN ===
            "sanchez", "pedro sanchez", "prime minister sanchez",
            "rajoy", "mariano rajoy",
            "zapatero", "jose luis zapatero",
            "felipe vi", "king felipe",

            # === OTHER WESTERN EUROPE ===
            "rutte", "mark rutte", "prime minister rutte",
            "wilders", "geert wilders",
            "de croo", "alexander de croo",
            "bettel", "xavier bettel",
            "ammann", "alain berset", "viola amherd",
            "nehammer", "karl nehammer",
            "kurz", "sebastian kurz",
            "costa", "antonio costa",
            "rebelo de sousa", "marcelo rebelo de sousa",

            # === NORDIC COUNTRIES ===
            "frederiksen", "mette frederiksen",
            "kristersson", "ulf kristersson",
            "andersson", "magdalena andersson",
            "store", "jonas gahr store",
            "solberg", "erna solberg",
            "marin", "sanna marin",
            "stubb", "alexander stubb",
            "orpo", "petteri orpo",
            "niinisto", "sauli niinisto",

            # === EASTERN EUROPE ===
            "zelensky", "zelenskyy", "volodymyr zelensky", "president zelensky", "volodymyr zelenskyy",
            "poroshenko", "petro poroshenko",
            "yanukovych", "viktor yanukovych",
            "tymoshenko", "yulia tymoshenko",
            "duda", "andrzej duda", "president duda",
            "morawiecki", "mateusz morawiecki",
            "tusk", "donald tusk", "prime minister tusk",
            "kaczynski", "jaroslaw kaczynski", "lech kaczynski",
            "orban", "viktor orban", "prime minister orban",
            "fiala", "petr fiala",
            "babis", "andrej babis",
            "zeman", "milos zeman",
            "havel", "vaclav havel",
            "fico", "robert fico",
            "iohannis", "klaus iohannis",
            "radev", "rumen radev",
            "vucic", "aleksandar vucic",
            "plenkovic", "andrej plenkovic",
            "pahor", "borut pahor",
            "rama", "edi rama",
            "milo", "milo djukanovic",

            # === RUSSIA & FORMER USSR ===
            "putin", "vladimir putin", "president putin", "vladimir vladimirovich putin",
            "medvedev", "dmitry medvedev", "prime minister medvedev",
            "lavrov", "sergey lavrov", "foreign minister lavrov", "sergei lavrov",
            "shoigu", "sergei shoigu", "defense minister shoigu",
            "gerasimov", "valery gerasimov",
            "prigozhin", "yevgeny prigozhin",
            "navalny", "alexei navalny", "aleksei navalny",
            "gorbachev", "mikhail gorbachev", "president gorbachev",
            "yeltsin", "boris yeltsin", "president yeltsin",
            "khrushchev", "nikita khrushchev",
            "stalin", "joseph stalin",
            "lenin", "vladimir lenin",
            "lukashenko", "alexander lukashenko", "president lukashenko", "alyaksandr lukashenko",
            "tokayev", "kassym-jomart tokayev",
            "nazarbayev", "nursultan nazarbayev",
            "mirziyoyev", "shavkat mirziyoyev",
            "aliyev", "ilham aliyev",
            "pashinyan", "nikol pashinyan",
            "garibashvili", "irakli garibashvili",
            "saakashvili", "mikheil saakashvili",

            # === CHINA ===
            "xi", "xi jinping", "president xi", "chairman xi", "xi jin ping",
            "li qiang", "premier li qiang", "prime minister li",
            "li keqiang", "premier li keqiang",
            "wang yi", "foreign minister wang",
            "hu jintao", "president hu",
            "jiang zemin", "president jiang",
            "deng xiaoping", "deng",
            "mao", "mao zedong", "chairman mao", "mao tse-tung",
            "zhou enlai", "premier zhou",
            "wen jiabao", "premier wen",

            # === JAPAN ===
            "kishida", "fumio kishida", "prime minister kishida",
            "suga", "yoshihide suga", "prime minister suga",
            "abe", "shinzo abe", "prime minister abe",
            "koizumi", "junichiro koizumi",
            "emperor naruhito", "naruhito",
            "emperor akihito", "akihito",

            # === KOREA ===
            "yoon", "yoon suk yeol", "president yoon", "yoon suk-yeol",
            "moon", "moon jae-in", "president moon",
            "park geun-hye", "park",
            "lee myung-bak",
            "kim jong un", "kim jong-un", "jong un", "chairman kim",
            "kim jong il", "kim il sung",

            # === INDIA ===
            "modi", "narendra modi", "prime minister modi", "pm modi",
            "gandhi", "rahul gandhi", "sonia gandhi", "indira gandhi", "rajiv gandhi", "mahatma gandhi",
            "singh", "manmohan singh", "prime minister singh",
            "vajpayee", "atal bihari vajpayee",
            "murmu", "droupadi murmu", "president murmu",
            "kovind", "ram nath kovind",
            "shah", "amit shah", "home minister shah",
            "jaishankar", "s jaishankar",

            # === PAKISTAN ===
            "sharif", "nawaz sharif", "shehbaz sharif", "prime minister sharif",
            "khan", "imran khan", "prime minister khan",
            "bhutto", "benazir bhutto", "zulfikar ali bhutto", "bilawal bhutto",
            "zardari", "asif ali zardari",
            "musharraf", "pervez musharraf",

            # === SOUTHEAST ASIA ===
            "marcos", "bongbong marcos", "ferdinand marcos jr", "ferdinand marcos",
            "duterte", "rodrigo duterte", "president duterte",
            "aquino", "benigno aquino", "corazon aquino",
            "jokowi", "joko widodo", "president jokowi",
            "prabowo", "prabowo subianto",
            "yudhoyono", "susilo bambang yudhoyono",
            "anwar", "anwar ibrahim", "prime minister anwar",
            "mahathir", "mahathir mohamad",
            "lee hsien loong", "prime minister lee",
            "lee kuan yew",
            "prayuth", "prayuth chan-ocha",
            "thaksin", "thaksin shinawatra",
            "hun sen", "prime minister hun sen",
            "hun manet",
            "aung san suu kyi", "suu kyi",
            "min aung hlaing",

            # === MIDDLE EAST - ISRAEL ===
            "netanyahu", "benjamin netanyahu", "bibi", "prime minister netanyahu", "bibi netanyahu",
            "gantz", "benny gantz",
            "lapid", "yair lapid",
            "bennett", "naftali bennett",
            "herzog", "isaac herzog", "president herzog",
            "ben-gvir", "itamar ben-gvir",
            "smotrich", "bezalel smotrich",
            "sharon", "ariel sharon",
            "olmert", "ehud olmert",
            "barak", "ehud barak",
            "peres", "shimon peres",
            "rabin", "yitzhak rabin",
            "begin", "menachem begin",
            "ben-gurion", "david ben-gurion",

            # === MIDDLE EAST - PALESTINE ===
            "abbas", "mahmoud abbas", "president abbas", "abu mazen",
            "arafat", "yasser arafat",
            "haniyeh", "ismail haniyeh",
            "sinwar", "yahya sinwar",
            "meshaal", "khaled meshaal",

            # === MIDDLE EAST - IRAN ===
            "khamenei", "ali khamenei", "ayatollah khamenei", "supreme leader khamenei",
            "raisi", "ebrahim raisi", "president raisi",
            "rouhani", "hassan rouhani",
            "ahmadinejad", "mahmoud ahmadinejad",
            "khatami", "mohammad khatami",
            "khomeini", "ayatollah khomeini", "ruhollah khomeini",
            "zarif", "javad zarif", "mohammad javad zarif",
            "soleimani", "qasem soleimani", "general soleimani",

            # === MIDDLE EAST - TURKEY ===
            "erdogan", "recep tayyip erdogan", "president erdogan", "tayyip erdogan",
            "davutoglu", "ahmet davutoglu",
            "yildirim", "binali yildirim",
            "ataturk", "mustafa kemal ataturk", "kemal ataturk",

            # === MIDDLE EAST - ARAB STATES ===
            "mbs", "mohammed bin salman", "crown prince mohammed", "prince mohammed",
            "king salman", "salman bin abdulaziz", "king salman bin abdulaziz",
            "king abdullah", "abdullah ii",
            "sisi", "abdel fattah el-sisi", "al-sisi", "president sisi",
            "mubarak", "hosni mubarak",
            "morsi", "mohamed morsi",
            "assad", "bashar al-assad", "bashar assad", "president assad",
            "hafez assad", "hafez al-assad",
            "saddam", "saddam hussein",
            "maliki", "nouri al-maliki",
            "abadi", "haider al-abadi",
            "kadhimi", "mustafa al-kadhimi",
            "gaddafi", "muammar gaddafi", "qaddafi", "colonel gaddafi",
            "haftar", "khalifa haftar",
            "houthi", "abdul-malik al-houthi",
            "sheikh mohammed", "mohammed bin rashid", "mbr",
            "tamim", "sheikh tamim", "emir tamim",

            # === AFRICA - NORTH ===
            "tebboune", "abdelmadjid tebboune",
            "bouteflika", "abdelaziz bouteflika",
            "saied", "kais saied",
            "essebsi", "beji caid essebsi",
            "king mohammed vi", "mohammed vi",

            # === AFRICA - SUB-SAHARAN ===
            "ramaphosa", "cyril ramaphosa", "president ramaphosa",
            "zuma", "jacob zuma",
            "mbeki", "thabo mbeki",
            "mandela", "nelson mandela", "madiba",
            "de klerk", "fw de klerk",
            "kagame", "paul kagame", "president kagame",
            "museveni", "yoweri museveni",
            "ruto", "william ruto", "president ruto",
            "kenyatta", "uhuru kenyatta", "jomo kenyatta",
            "tinubu", "bola tinubu", "president tinubu",
            "buhari", "muhammadu buhari",
            "obasanjo", "olusegun obasanjo",
            "jonathan", "goodluck jonathan",
            "abiy", "abiy ahmed", "prime minister abiy",
            "afwerki", "isaias afwerki",
            "bashir", "omar al-bashir",
            "burhan", "abdel fattah al-burhan",
            "hemeti", "mohamed hamdan dagalo",
            "kabila", "joseph kabila", "laurent kabila",
            "tshisekedi", "felix tshisekedi",
            "mnangagwa", "emmerson mnangagwa",
            "mugabe", "robert mugabe",
            "dos santos", "jose eduardo dos santos",
            "lourenco", "joao lourenco",
            "deby", "idriss deby", "mahamat deby",
            "keita", "ibrahim boubacar keita",
            "goita", "assimi goita",
            "ouattara", "alassane ouattara",
            "akufo-addo", "nana akufo-addo",
            "mahama", "john mahama",
            "macky sall", "sall",
            "conde", "alpha conde",

            # === LATIN AMERICA ===
            "lula", "lula da silva", "luiz inacio lula da silva", "president lula",
            "bolsonaro", "jair bolsonaro", "president bolsonaro",
            "rousseff", "dilma rousseff",
            "temer", "michel temer",
            "cardoso", "fernando henrique cardoso",
            "amlo", "lopez obrador", "andres manuel lopez obrador",
            "calderon", "felipe calderon",
            "pena nieto", "enrique pena nieto",
            "sheinbaum", "claudia sheinbaum",
            "milei", "javier milei", "president milei",
            "fernandez", "alberto fernandez", "cristina fernandez", "cristina kirchner",
            "macri", "mauricio macri",
            "kirchner", "nestor kirchner",
            "maduro", "nicolas maduro", "president maduro",
            "chavez", "hugo chavez", "president chavez",
            "guaido", "juan guaido",
            "petro", "gustavo petro", "president petro",
            "duque", "ivan duque",
            "santos", "juan manuel santos",
            "uribe", "alvaro uribe",
            "boric", "gabriel boric", "president boric",
            "pinera", "sebastian pinera",
            "bachelet", "michelle bachelet",
            "castillo", "pedro castillo",
            "boluarte", "dina boluarte",
            "morales", "evo morales",
            "arce", "luis arce",
            "correa", "rafael correa",
            "noboa", "daniel noboa",
            "bukele", "nayib bukele", "president bukele",
            "ortega", "daniel ortega",
            "castro", "fidel castro", "raul castro", "miguel diaz-canel", "diaz-canel",
            "aristide", "jean-bertrand aristide",

            # === OCEANIA ===
            "albanese", "anthony albanese", "prime minister albanese",
            "morrison", "scott morrison",
            "turnbull", "malcolm turnbull",
            "abbott", "tony abbott",
            "gillard", "julia gillard",
            "rudd", "kevin rudd",
            "howard", "john howard",
            "luxon", "christopher luxon",
            "ardern", "jacinda ardern", "prime minister ardern",
            "hipkins", "chris hipkins",

            # === INTERNATIONAL ORGANIZATIONS ===
            "guterres", "antonio guterres", "secretary general guterres", "un secretary general",
            "ban ki-moon", "ban", "secretary general ban",
            "kofi annan", "annan",
            "stoltenberg", "jens stoltenberg", "secretary general stoltenberg",
            "von der leyen", "ursula von der leyen", "president von der leyen",
            "michel", "charles michel",
            "lagarde", "christine lagarde", "ecb president lagarde",
            "draghi", "mario draghi",
            "georgieva", "kristalina georgieva",
            "okonjo-iweala", "ngozi okonjo-iweala",
            "tedros", "tedros adhanom", "dr tedros",

            # === RELIGIOUS LEADERS ===
            "pope francis", "francis", "pope",
            "pope benedict", "benedict xvi", "joseph ratzinger",
            "pope john paul", "john paul ii", "karol wojtyla",
            "dalai lama", "tenzin gyatso",
            "patriarch kirill", "kirill",
            "archbishop welby", "justin welby",

            # === MAJOR HISTORICAL FIGURES (20th century, still referenced) ===
            "churchill", "winston churchill",
            "hitler", "adolf hitler",
            "mussolini", "benito mussolini",
            "franco", "francisco franco",
            "tito", "josip broz tito",
            "ceausescu", "nicolae ceausescu",
            "pinochet", "augusto pinochet",
            "pol pot",
            "ho chi minh",
            "sukarno", "suharto",
            "nasser", "gamal abdel nasser",
            "sadat", "anwar sadat",
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
            # === TECH ACRONYMS & TERMS ===
            # AI & Machine Learning
            "ai", "artificial intelligence", "ml", "machine learning", "llm", "llms",
            "large language model", "gpt", "chatgpt", "gpt-4", "gpt-5", "claude",
            "generative ai", "gen ai", "neural network", "neural networks",
            "deep learning", "nlp", "natural language processing", "computer vision",
            "reinforcement learning", "supervised learning", "transformer",
            "diffusion model", "stable diffusion", "midjourney", "dall-e",
            "copilot", "gemini", "bard", "llama", "mistral", "perplexity",
            # VR/AR/XR
            "vr", "virtual reality", "ar", "augmented reality", "xr", "mixed reality",
            "metaverse", "oculus", "quest", "hololens", "vision pro", "spatial computing",
            # Connectivity & Infrastructure
            "iot", "internet of things", "5g", "6g", "wifi", "wi-fi", "broadband",
            "fiber optic", "starlink", "satellite internet", "edge computing",
            "cloud computing", "aws", "azure", "gcp", "data center", "data centers",
            "api", "apis", "saas", "paas", "iaas", "microservices", "kubernetes",
            "docker", "devops", "agile", "scrum",
            # Electric & Autonomous Vehicles
            "ev", "evs", "electric vehicle", "electric vehicles", "hybrid",
            "autonomous vehicle", "autonomous vehicles", "self-driving", "autopilot",
            "full self-driving", "fsd", "lidar", "adas", "vehicle-to-everything", "v2x",
            # Crypto & Blockchain
            "blockchain", "cryptocurrency", "cryptocurrencies", "crypto",
            "bitcoin", "btc", "ethereum", "eth", "solana", "cardano", "dogecoin",
            "stablecoin", "stablecoins", "usdt", "usdc", "defi", "decentralized finance",
            "nft", "nfts", "non-fungible token", "web3", "dao", "smart contract",
            "smart contracts", "mining", "proof of work", "proof of stake",
            # Cybersecurity
            "deepfake", "deepfakes", "cybersecurity", "cyber security", "infosec",
            "ransomware", "malware", "phishing", "spyware", "trojan", "botnet",
            "ddos", "zero-day", "exploit", "vulnerability", "data breach",
            "encryption", "end-to-end encryption", "vpn", "firewall", "antivirus",
            "two-factor", "2fa", "mfa", "biometric", "biometrics",
            # Hardware & Chips
            "semiconductor", "semiconductors", "chip", "chips", "microchip", "microchips",
            "cpu", "gpu", "gpus", "tpu", "processor", "processors", "silicon",
            "nanometer", "fab", "foundry", "tsmc", "asml", "arm", "risc-v", "quantum",
            "quantum computing", "quantum computer", "qubit", "qubits",
            # Software & Platforms
            "software", "hardware", "firmware", "app", "apps", "application",
            "platform", "platforms", "algorithm", "algorithms", "open source",
            "proprietary", "linux", "windows", "macos", "android", "ios",
            # Data & Analytics
            "big data", "data analytics", "data science", "database", "sql", "nosql",
            "data privacy", "gdpr", "ccpa", "cookies", "tracking", "surveillance",
            # Social Media & Content
            "social media", "streaming", "content moderation", "misinformation",
            "disinformation", "fake news", "bot", "bots", "troll", "viral",
            "influencer", "influencers", "creator economy", "monetization",
            # Emerging Tech
            "biotech", "biotechnology", "crispr", "gene editing", "mrna",
            "nanotechnology", "nanotech", "3d printing", "additive manufacturing",
            "robotics", "robot", "robots", "drone", "drones", "uav",
            "brain-computer interface", "bci", "neuralink", "wearable", "wearables",
            # === TECH COMPANIES ===
            # Big Tech / FAANG+
            "apple", "google", "alphabet", "microsoft", "amazon", "meta", "facebook",
            "twitter", "x corp", "tesla", "nvidia", "netflix",
            # AI Companies
            "openai", "anthropic", "deepmind", "google ai", "meta ai", "microsoft ai",
            "cohere", "stability ai", "inflection", "character ai", "hugging face",
            "scale ai", "databricks", "c3 ai", "soundhound", "jasper",
            "runway", "eleven labs", "synthesia", "replika", "adept",
            # Semiconductors & Hardware
            "intel", "amd", "nvidia", "qualcomm", "broadcom", "texas instruments",
            "micron", "western digital", "seagate", "sk hynix", "mediatek",
            "marvell", "on semiconductor", "analog devices", "nxp", "infineon",
            "arm holdings", "synopsys", "cadence", "lam research", "applied materials",
            # Enterprise Software
            "ibm", "oracle", "salesforce", "sap", "workday", "servicenow",
            "adobe", "intuit", "autodesk", "vmware", "splunk", "datadog",
            "mongodb", "elastic", "confluent", "hashicorp", "gitlab", "github",
            "atlassian", "asana", "monday", "notion", "airtable", "figma",
            # Cloud & Infrastructure
            "cisco", "juniper", "arista", "f5", "cloudflare", "fastly", "akamai",
            "digitalocean", "linode", "vultr", "rackspace", "equinix",
            # Hardware & Devices
            "dell", "hp", "hewlett packard", "hpe", "lenovo", "asus", "acer",
            "samsung", "sony", "lg", "panasonic", "toshiba", "sharp", "tcl",
            "huawei", "xiaomi", "oppo", "vivo", "oneplus", "realme", "honor",
            "logitech", "razer", "corsair", "steelseries",
            # Social Media & Content
            "tiktok", "bytedance", "snap", "snapchat", "pinterest", "reddit",
            "discord", "twitch", "youtube", "instagram", "whatsapp", "telegram",
            "signal", "wechat", "weibo", "line", "kakao",
            # Chinese Tech Giants
            "alibaba", "tencent", "baidu", "jd.com", "meituan", "pinduoduo",
            "didi", "nio", "xpeng", "li auto", "netease", "bilibili",
            "kuaishou", "ant group", "sea limited", "grab", "gojek",
            # E-commerce & Marketplaces
            "ebay", "etsy", "wayfair", "chewy", "wish", "mercadolibre",
            "coupang", "flipkart", "lazada", "shopee", "zalando",
            # Streaming & Entertainment
            "netflix", "spotify", "roku", "sonos", "pandora", "deezer",
            "hulu", "peacock", "paramount+", "discovery+", "crunchyroll",
            # Rideshare & Delivery
            "uber", "lyft", "airbnb", "doordash", "instacart", "grubhub",
            "deliveroo", "just eat", "bolt", "ola", "careem", "gett",
            # Fintech & Payments
            "paypal", "square", "block", "stripe", "coinbase", "robinhood",
            "klarna", "affirm", "afterpay", "marqeta", "plaid", "chime",
            "sofi", "revolut", "n26", "monzo", "wise", "adyen",
            "binance", "kraken", "gemini", "ftx", "celsius", "blockfi",
            # Collaboration & Productivity
            "zoom", "slack", "dropbox", "box", "docusign", "ringcentral",
            "twilio", "okta", "zscaler", "crowdstrike", "sentinelone",
            "shopify", "wix", "squarespace", "godaddy", "hubspot", "mailchimp",
            # Cybersecurity
            "palo alto networks", "fortinet", "check point", "fireeye", "mandiant",
            "mcafee", "norton", "symantec", "kaspersky", "bitdefender", "avast",
            "proofpoint", "mimecast", "tenable", "rapid7", "qualys",
            # Gaming Tech
            "unity", "roblox", "zynga", "king", "supercell", "niantic",
            "epic games", "valve", "steam", "ea", "ubisoft", "capcom",
            # Data & Analytics
            "snowflake", "palantir", "tableau", "alteryx", "domo", "qlik",
            "teradata", "informatica", "talend", "fivetran",
            # Health Tech
            "teladoc", "doximity", "veeva", "cerner", "epic systems",
            "fitbit", "peloton", "whoop", "oura", "garmin",
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
        # lede highlighting removed

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
        number_patterns = [
            # Ordinals
            r'\b\d+(?:st|nd|rd|th)\b',              # 1st, 2nd, 3rd, 250th
            # Times
            r'\b\d{1,2}:\d{2}(?::\d{2})?\s*(?:AM|PM|am|pm|a\.m\.|p\.m\.)?\b',  # 3:00, 10:30 PM
            # Ranges and scores
            r'\b\d+(?:\.\d+)?[-–—]\d+(?:\.\d+)?\b', # 10-15, 2.5-3.0, 2020–2024
            r'\b\d+/\d+\b',                         # Fractions/scores: 1/2, 3/4
            # Decades
            r"\b\d{2,4}'?s\b",                      # 1990s, 80s, '90s
            # With units
            r'\b\d+(?:\.\d+)?\s*(?:km|mi|m|ft|in|cm|mm|kg|lb|lbs|oz|g|mg|mph|kph|fps|hz|khz|mhz|ghz|kb|mb|gb|tb|kw|mw|gw)\b',
            # With K/M/B abbreviations
            r'\b\d+(?:\.\d+)?\s*[KkMmBb]\b',        # 5K, 10M, 2.5B
            # Version numbers
            r'\bv?\d+(?:\.\d+)+\b',                 # v1.0, 2.5.1, v10.3.2
            # Scientific notation
            r'\b\d+(?:\.\d+)?[eE][+-]?\d+\b',       # 1e10, 2.5e-3
            # Temperatures
            r'[-−]?\d+(?:\.\d+)?°[FCfc]?\b',        # 72°F, -10°C, 22°
            # Coordinates
            r'\b\d+(?:\.\d+)?°[NSEW]?\b',           # 40.7128°N
            # Stock/number changes
            r'[+−-]\d+(?:\.\d+)?%?\b',              # +5.2, -3.8, +12%
            # Numbered items
            r'(?:No\.|#|№)\s*\d+\b',                # No. 1, #1, №1
            # Hyphenated number phrases
            r'\b\d+[-–](?:year|day|hour|minute|month|week|meter|mile|foot|pound|dollar|point|game|run|set)\b',
            # Approximate/comparative
            r'[~≈<>≤≥]\s*\d+(?:\.\d+)?',            # ~100, >50, <100
            # Roman numerals (common ones in news)
            r'\b(?:III|II|IV|VI|VII|VIII|IX|XI|XII|XIII|XIV|XV|XVI|XVII|XVIII|XIX|XX|XXI)\b',
            # Feet and inches
            r"\b\d+[''′]\s*\d*[\"″]?\b",            # 6'2", 5'
            # Plain numbers (catch-all, must be last)
            r'\b\d+(?:\.\d+)?\b',                   # 42, 3.14
        ]
        for pattern in number_patterns:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                add_highlight(match.start(), match.end(), "numbers")

        # 5. Verbs (news action words) - categorized with distinct colors
        verb_categories = {
            "verb_communication": [
                "said", "says", "saying", "stated", "states", "stating", "declared", "declares",
                "announced", "announces", "announcing", "told", "tells", "telling", "claimed", "claims", "claiming",
                "asserted", "asserts", "asserting", "remarked", "remarking", "commented", "comments", "commenting",
                "mentioned", "mentioning", "expressed", "expressing", "articulated", "articulating",
                "conveyed", "conveying", "communicated", "communicating", "spoke", "speaks", "speaking",
                "responded", "responds", "responding", "replied", "replies", "replying",
                "answered", "answers", "answering", "questioned", "questions", "questioning",
                "asked", "asks", "asking", "inquired", "inquiring", "queried", "querying",
                "interviewed", "interviewing", "briefed", "briefing", "addressed", "addressing",
                "emphasized", "emphasised", "emphasizing", "emphasising", "stressed", "stressing",
                "highlighted", "highlighting", "underscored", "underscoring", "reiterated", "reiterating",
                "repeated", "repeating", "clarified", "clarifying", "explained", "explains", "explaining",
                "elaborated", "elaborating", "detailed", "detailing", "outlined", "outlining",
                "summarized", "summarised", "summarizing", "summarising", "recapped", "recapping",
                "described", "describes", "describing", "depicted", "depicting",
                "characterized", "characterised", "characterizing", "characterising",
                "portrayed", "portraying", "presented", "presents", "presenting",
                "relayed", "relaying", "transmitted", "transmitting", "broadcast", "broadcasts", "broadcasting",
                "published", "publishes", "publishing", "posted", "posts", "posting",
                "tweeted", "tweets", "tweeting", "shared", "shares", "sharing",
                "reported", "reports", "reporting", "disclosed", "discloses", "disclosing",
                "revealed", "reveals", "revealing", "exposed", "exposes", "exposing",
                "leaked", "leaks", "leaking", "divulged", "divulging", "confirmed", "confirms", "confirming",
                "acknowledged", "acknowledges", "acknowledging", "admitted", "admits", "admitting",
                "conceded", "concedes", "conceding", "noted", "notes", "noting",
                "added", "adds", "adding", "cited", "cites", "citing", "quoted", "quotes", "quoting",
                "referenced", "referencing", "indicated", "indicates", "indicating",
                "signaled", "signalled", "signals", "signaling", "signalling",
                "suggested", "suggests", "suggesting", "implied", "implies", "implying",
                "hinted", "hints", "hinting", "alluded", "alluding", "insinuated", "insinuating",
                "speculated", "speculates", "speculating", "predicted", "predicts", "predicting",
                "forecast", "forecasts", "forecasting", "projected", "projects", "projecting",
                "estimated", "estimates", "estimating", "calculated", "calculating", "assessed", "assessing",
                "wrote", "writes", "writing", "penned", "penning", "authored", "authoring",
            ],
            "verb_accusation": [
                "accused", "accuses", "accusing", "blamed", "blames", "blaming",
                "alleged", "alleges", "alleging", "implicated", "implicating",
                "incriminated", "incriminating", "condemned", "condemns", "condemning",
                "denounced", "denounces", "denouncing",
                "criticized", "criticised", "criticizes", "criticises", "criticizing", "criticising",
                "slammed", "slams", "slamming", "blasted", "blasts", "blasting",
                "lambasted", "lambasting", "castigated", "castigating",
                "rebuked", "rebukes", "rebuking", "reprimanded", "reprimanding",
                "chastised", "chastising", "scolded", "scolding", "admonished", "admonishing",
                "faulted", "faults", "faulting", "singled", "singling",
                "attacked", "attacking", "assailed", "assailing", "vilified", "vilifying",
            ],
            "verb_support": [
                "praised", "praises", "praising", "commended", "commends", "commending",
                "applauded", "applauds", "applauding", "hailed", "hails", "hailing",
                "celebrated", "celebrates", "celebrating", "honored", "honoured", "honors", "honours", "honoring", "honouring",
                "recognized", "recognised", "recognizes", "recognises", "recognizing", "recognising",
                "endorsed", "endorses", "endorsing", "supported", "supports", "supporting",
                "backed", "backs", "backing", "championed", "champions", "championing",
                "advocated", "advocates", "advocating", "promoted", "promotes", "promoting",
                "defended", "defends", "defending", "justified", "justifies", "justifying",
                "validated", "validates", "validating", "upheld", "upholds", "upholding",
                "embraced", "embraces", "embracing", "touted", "touts", "touting",
            ],
            "verb_agreement": [
                "agreed", "agrees", "agreeing", "disagreed", "disagrees", "disagreeing",
                "concurred", "concurs", "concurring", "disputed", "disputes", "disputing",
                "contested", "contests", "contesting", "challenged", "challenges", "challenging",
                "opposed", "opposes", "opposing", "objected", "objects", "objecting",
                "protested", "protests", "protesting", "resisted", "resists", "resisting",
                "rejected", "rejects", "rejecting", "refused", "refuses", "refusing",
                "declined", "declines", "declining", "denied", "denies", "denying",
                "contradicted", "contradicts", "contradicting", "countered", "counters", "countering",
                "rebutted", "rebuts", "rebutting", "refuted", "refutes", "refuting",
                "dismissed", "dismisses", "dismissing", "doubted", "doubts", "doubting",
            ],
            "verb_decision": [
                "decided", "decides", "deciding", "determined", "determines", "determining",
                "concluded", "concludes", "concluding", "resolved", "resolves", "resolving",
                "ruled", "rules", "ruling", "judged", "judges", "judging", "decreed", "decreeing",
                "ordered", "orders", "ordering", "commanded", "commands", "commanding",
                "directed", "directs", "directing", "instructed", "instructs", "instructing",
                "mandated", "mandates", "mandating", "required", "requires", "requiring",
                "demanded", "demands", "demanding", "requested", "requests", "requesting",
                "urged", "urges", "urging", "encouraged", "encourages", "encouraging",
                "pressured", "pressures", "pressuring", "pushed", "pushes", "pushing",
                "lobbied", "lobbies", "lobbying", "petitioned", "petitions", "petitioning",
                "appealed", "appeals", "appealing", "sought", "seeks", "seeking",
                "pursued", "pursues", "pursuing", "aimed", "aims", "aiming",
                "intended", "intends", "intending", "planned", "plans", "planning",
                "proposed", "proposes", "proposing", "recommended", "recommends", "recommending",
                "forced", "forces", "forcing", "compelled", "compels", "compelling",
                "labeled", "labelled", "labels", "labeling", "labelling",
                "designated", "designates", "designating", "classified", "classifies", "classifying",
            ],
            "verb_political": [
                "enacted", "enacts", "enacting", "legislated", "legislates", "legislating",
                "passed", "passes", "passing", "vetoed", "vetoes", "vetoing",
                "signed", "signs", "signing", "ratified", "ratifies", "ratifying",
                "amended", "amends", "amending", "repealed", "repeals", "repealing",
                "overturned", "overturns", "overturning", "enforced", "enforces", "enforcing",
                "implemented", "implements", "implementing", "administered", "administers", "administering",
                "governed", "governs", "governing", "regulated", "regulates", "regulating",
                "deregulated", "deregulates", "deregulating", "sanctioned", "sanctions", "sanctioning",
                "embargoed", "embargoes", "embargoing",
                "authorized", "authorised", "authorizes", "authorises", "authorizing", "authorising",
                "approved", "approves", "approving", "certified", "certifies", "certifying",
                "licensed", "licenced", "licenses", "licences", "licensing", "licencing",
                "permitted", "permits", "permitting", "banned", "bans", "banning",
                "prohibited", "prohibits", "prohibiting", "blocked", "blocks", "blocking",
                "suspended", "suspends", "suspending", "revoked", "revokes", "revoking",
                "rescinded", "rescinds", "rescinding", "appointed", "appoints", "appointing",
                "nominated", "nominates", "nominating", "elected", "elects", "electing",
                "inaugurated", "inaugurates", "inaugurating", "sworn", "swore", "swearing",
                "impeached", "impeaches", "impeaching", "ousted", "ousts", "ousting",
                "toppled", "topples", "toppling", "overthrew", "overthrows", "overthrowing",
                "resigned", "resigns", "resigning", "retired", "retires", "retiring", "quit", "quits", "quitting",
            ],
            "verb_military": [
                "attacked", "attacks", "attacking", "struck", "strikes", "striking",
                "bombed", "bombs", "bombing", "shelled", "shells", "shelling",
                "fired", "fires", "firing", "shot", "shoots", "shooting",
                "targeted", "targets", "targeting", "assaulted", "assaults", "assaulting",
                "invaded", "invades", "invading", "occupied", "occupies", "occupying",
                "seized", "seizes", "seizing", "captured", "captures", "capturing",
                "conquered", "conquers", "conquering", "liberated", "liberates", "liberating",
                "retreated", "retreats", "retreating", "withdrew", "withdraws", "withdrawing",
                "deployed", "deploys", "deploying", "mobilized", "mobilised", "mobilizes", "mobilises", "mobilizing", "mobilising",
                "escalated", "escalates", "escalating", "retaliated", "retaliates", "retaliating",
                "fortified", "fortifies", "fortifying", "besieged", "besieges", "besieging",
                "blockaded", "blockades", "blockading", "ambushed", "ambushes", "ambushing",
                "raided", "raids", "raiding", "stormed", "storms", "storming",
                "clashed", "clashes", "clashing", "fought", "fights", "fighting",
                "battled", "battles", "battling", "killed", "kills", "killing",
                "slew", "slays", "slaying", "murdered", "murders", "murdering",
                "assassinated", "assassinates", "assassinating", "executed", "executes", "executing",
                "massacred", "massacres", "massacring", "slaughtered", "slaughters", "slaughtering",
                "wounded", "wounds", "wounding", "injured", "injures", "injuring",
                "maimed", "maims", "maiming", "hurt", "hurts", "hurting",
                "died", "dies", "dying", "perished", "perishes", "perishing",
                "surrendered", "surrenders", "surrendering", "capitulated", "capitulates", "capitulating",
                "ceased", "ceases", "ceasing",
            ],
            "verb_legal": [
                "arrested", "arrests", "arresting", "detained", "detains", "detaining",
                "jailed", "jails", "jailing", "imprisoned", "imprisons", "imprisoning",
                "incarcerated", "incarcerates", "incarcerating", "released", "releases", "releasing",
                "freed", "frees", "freeing", "charged", "charges", "charging",
                "indicted", "indicts", "indicting", "prosecuted", "prosecutes", "prosecuting",
                "tried", "tries", "trying", "convicted", "convicts", "convicting",
                "acquitted", "acquits", "acquitting", "sentenced", "sentences", "sentencing",
                "fined", "fines", "fining", "pardoned", "pardons", "pardoning",
                "exonerated", "exonerates", "exonerating", "testified", "testifies", "testifying",
                "sued", "sues", "suing", "settled", "settles", "settling",
                "litigated", "litigates", "litigating", "extradited", "extradites", "extraditing",
                "deported", "deports", "deporting", "subpoenaed", "subpoenas", "subpoenaing",
            ],
            "verb_economic": [
                "invested", "invests", "investing", "divested", "divests", "divesting",
                "acquired", "acquires", "acquiring", "merged", "merges", "merging",
                "bought", "buys", "buying", "sold", "sells", "selling",
                "traded", "trades", "trading", "profited", "profits", "profiting",
                "earned", "earns", "earning", "spent", "spends", "spending",
                "paid", "pays", "paying", "funded", "funds", "funding",
                "financed", "finances", "financing", "borrowed", "borrows", "borrowing",
                "lent", "lends", "lending", "defaulted", "defaults", "defaulting",
                "restructured", "restructures", "restructuring", "downsized", "downsizes", "downsizing",
                "expanded", "expands", "expanding", "grew", "grows", "growing",
                "shrank", "shrinks", "shrinking", "surged", "surges", "surging",
                "plunged", "plunges", "plunging", "soared", "soars", "soaring",
                "plummeted", "plummets", "plummeting", "rallied", "rallies", "rallying",
                "rose", "rises", "rising", "fell", "falls", "falling",
                "increased", "increases", "increasing", "decreased", "decreases", "decreasing",
                "doubled", "doubles", "doubling", "tripled", "triples", "tripling",
                "halved", "halves", "halving", "slashed", "slashes", "slashing",
                "cut", "cuts", "cutting", "raised", "raises", "raising",
                "boosted", "boosts", "boosting", "lifted", "lifts", "lifting",
                "lowered", "lowers", "lowering", "hired", "hires", "hiring",
                "billed", "bills", "billing", "cost", "costs", "costing",
            ],
            "verb_discovery": [
                "discovered", "discovers", "discovering", "found", "finds", "finding",
                "uncovered", "uncovers", "uncovering", "unearthed", "unearths", "unearthing",
                "detected", "detects", "detecting", "identified", "identifies", "identifying",
                "located", "locates", "locating", "traced", "traces", "tracing",
                "tracked", "tracks", "tracking", "monitored", "monitors", "monitoring",
                "surveyed", "surveys", "surveying", "examined", "examines", "examining",
                "analyzed", "analysed", "analyzes", "analyses", "analyzing", "analysing",
                "investigated", "investigates", "investigating", "probed", "probes", "probing",
                "scrutinized", "scrutinised", "scrutinizes", "scrutinises", "scrutinizing", "scrutinising",
                "reviewed", "reviews", "reviewing", "audited", "audits", "auditing",
                "inspected", "inspects", "inspecting", "verified", "verifies", "verifying",
                "tested", "tests", "testing", "searched", "searches", "searching",
                "recovered", "recovers", "recovering", "encountered", "encounters", "encountering",
                "proved", "proves", "proving", "proven", "conducted", "conducts", "conducting",
            ],
            "verb_change": [
                "changed", "changes", "changing", "altered", "alters", "altering",
                "modified", "modifies", "modifying", "revised", "revises", "revising",
                "updated", "updates", "updating", "upgraded", "upgrades", "upgrading",
                "improved", "improves", "improving", "enhanced", "enhances", "enhancing",
                "transformed", "transforms", "transforming", "converted", "converts", "converting",
                "shifted", "shifts", "shifting", "transitioned", "transitions", "transitioning",
                "evolved", "evolves", "evolving", "adapted", "adapts", "adapting",
                "adjusted", "adjusts", "adjusting", "reformed", "reforms", "reforming",
                "restructured", "restructures", "restructuring",
                "reorganized", "reorganised", "reorganizes", "reorganises", "reorganizing", "reorganising",
                "overhauled", "overhauls", "overhauling", "replaced", "replaces", "replacing",
                "substituted", "substitutes", "substituting", "swapped", "swaps", "swapping",
                "switched", "switches", "switching", "reversed", "reverses", "reversing",
            ],
            "verb_creation": [
                "created", "creates", "creating", "built", "builds", "building",
                "constructed", "constructs", "constructing", "developed", "develops", "developing",
                "designed", "designs", "designing", "invented", "invents", "inventing",
                "launched", "launches", "launching", "introduced", "introduces", "introducing",
                "unveiled", "unveils", "unveiling", "opened", "opens", "opening",
                "established", "establishes", "establishing", "founded", "founds", "founding",
                "started", "starts", "starting", "began", "begins", "beginning",
                "initiated", "initiates", "initiating", "closed", "closes", "closing",
                "shut", "shuts", "shutting", "ended", "ends", "ending",
                "terminated", "terminates", "terminating", "demolished", "demolishes", "demolishing",
                "destroyed", "destroys", "destroying", "ruined", "ruins", "ruining",
                "damaged", "damages", "damaging", "wrecked", "wrecks", "wrecking",
                "devastated", "devastates", "devastating", "razed", "razes", "razing",
                "leveled", "levelled", "levels", "leveling", "levelling",
                "collapsed", "collapses", "collapsing", "imploded", "implodes", "imploding",
                "exploded", "explodes", "exploding", "detonated", "detonates", "detonating",
                "burned", "burnt", "burns", "burning", "flooded", "floods", "flooding",
                "sank", "sinks", "sinking",
            ],
            "verb_movement": [
                "moved", "moves", "moving", "traveled", "travelled", "travels", "traveling", "travelling",
                "went", "goes", "going", "came", "comes", "coming",
                "arrived", "arrives", "arriving", "departed", "departs", "departing",
                "left", "leaves", "leaving", "returned", "returns", "returning",
                "visited", "visits", "visiting", "toured", "tours", "touring",
                "fled", "flees", "fleeing", "escaped", "escapes", "escaping",
                "evacuated", "evacuates", "evacuating", "migrated", "migrates", "migrating",
                "immigrated", "immigrates", "immigrating", "emigrated", "emigrates", "emigrating",
                "expelled", "expels", "expelling", "exiled", "exiles", "exiling",
                "banished", "banishes", "banishing", "crossed", "crosses", "crossing",
                "entered", "enters", "entering", "exited", "exits", "exiting",
                "landed", "lands", "landing", "crashed", "crashes", "crashing",
                "collided", "collides", "colliding", "derailed", "derails", "derailing",
                "capsized", "capsizes", "capsizing", "embarked", "embarks", "embarking",
            ],
            "verb_emotion": [
                "feared", "fears", "fearing", "worried", "worries", "worrying",
                "concerned", "concerns", "concerning", "alarmed", "alarms", "alarming",
                "shocked", "shocks", "shocking", "surprised", "surprises", "surprising",
                "stunned", "stuns", "stunning", "outraged", "outrages", "outraging",
                "angered", "angers", "angering", "infuriated", "infuriates", "infuriating",
                "pleased", "pleases", "pleasing", "delighted", "delights", "delighting",
                "thrilled", "thrills", "thrilling", "excited", "excites", "exciting",
                "relieved", "relieves", "relieving", "disappointed", "disappoints", "disappointing",
                "frustrated", "frustrates", "frustrating", "dismayed", "dismays", "dismaying",
                "mourned", "mourns", "mourning", "grieved", "grieves", "grieving",
                "lamented", "laments", "lamenting", "cheered", "cheers", "cheering",
                "welcomed", "welcomes", "welcoming",
            ],
            "verb_prevention": [
                "prevented", "prevents", "preventing", "stopped", "stops", "stopping",
                "halted", "halts", "halting", "barred", "bars", "barring",
                "thwarted", "thwarts", "thwarting", "foiled", "foils", "foiling",
                "averted", "averts", "averting", "avoided", "avoids", "avoiding",
                "protected", "protects", "protecting", "shielded", "shields", "shielding",
                "guarded", "guards", "guarding", "secured", "secures", "securing",
                "safeguarded", "safeguards", "safeguarding", "preserved", "preserves", "preserving",
                "saved", "saves", "saving", "rescued", "rescues", "rescuing",
            ],
            "verb_competition": [
                "won", "wins", "winning", "lost", "loses", "losing",
                "defeated", "defeats", "defeating", "beat", "beats", "beating",
                "prevailed", "prevails", "prevailing", "triumphed", "triumphs", "triumphing",
                "succeeded", "succeeds", "succeeding", "failed", "fails", "failing",
                "achieved", "achieves", "achieving", "accomplished", "accomplishes", "accomplishing",
                "completed", "completes", "completing", "finished", "finishes", "finishing",
                "led", "leads", "leading", "trailed", "trails", "trailing",
                "tied", "ties", "tying", "drew", "draws", "drawing",
                "qualified", "qualifies", "qualifying", "eliminated", "eliminates", "eliminating",
                "advanced", "advances", "advancing", "competed", "competes", "competing",
            ],
            "verb_medical": [
                "diagnosed", "diagnoses", "diagnosing", "treated", "treats", "treating",
                "cured", "cures", "curing", "healed", "heals", "healing",
                "hospitalized", "hospitalised", "hospitalizes", "hospitalises", "hospitalizing", "hospitalising",
                "operated", "operates", "operating", "vaccinated", "vaccinates", "vaccinating",
                "infected", "infects", "infecting", "contracted", "contracts", "contracting",
                "spread", "spreads", "spreading", "transmitted", "transmits", "transmitting",
                "quarantined", "quarantines", "quarantining", "isolated", "isolates", "isolating",
                "sickened", "sickens", "sickening", "suffered", "suffers", "suffering",
            ],
        }
        for category, verbs in verb_categories.items():
            pattern = r'\b(?:' + '|'.join(verbs) + r')\b'
            for match in re.finditer(pattern, text, re.IGNORECASE):
                add_highlight(match.start(), match.end(), category)

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
            if phrase_lower in self.leaders:
                category = "people"
            elif phrase_lower in self.events:
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
                if word_lower in self.countries:
                    category = "countries"
                elif word_lower in self.places:
                    category = "places"
                elif word_lower in self.organizations:
                    category = "organizations"
                elif not at_sentence_start:
                    # Mid-sentence capitalization = proper noun
                    category = "proper_nouns"

            # Fallback: mid-sentence capitalized phrase not matching any category
            if not category and not at_sentence_start and len(words) >= 1:
                category = "proper_nouns"

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
        """Update the status bar with a real message, pausing idle cycling."""
        self.status_bar.configure(text=f"... {message.upper()}")
        self._idle_active = False
        self._idle_last_real_status = message.upper()
        # Resume idle cycling after ~5 seconds (150 frames at 30fps)
        self._idle_pause_until = self._anim_frame + 150

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

    # ── Borderless window methods ──────────────────────────────────

    def _strip_title_bar(self):
        """Remove native title bar using Win32 API while keeping proper window management."""
        if sys.platform != "win32":
            self.root.overrideredirect(True)
            return
        try:
            import ctypes
            self.root.update_idletasks()
            hwnd = int(self.root.wm_frame(), 16)
            self._hwnd = hwnd

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
            self.root.overrideredirect(True)

    def _setup_owner_icon(self):
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
            self._owner.iconbitmap(ico_path)
        except Exception:
            pass

    def _on_taskbar_restore(self, event=None):
        """Restore window when taskbar icon is clicked."""
        self._owner.attributes("-alpha", 0)  # Keep owner invisible
        self._owner.geometry("1x1+-10000+-10000")
        self.root.deiconify()
        self.root.lift()
        self.root.focus_force()

    def _start_drag(self, event):
        """Record drag start position."""
        self._drag_start_x = event.x_root
        self._drag_start_y = event.y_root
        geo = self.root.geometry()
        import re
        m = re.match(r'(\d+)x(\d+)\+(-?\d+)\+(-?\d+)', geo)
        if m:
            self._drag_win_x = int(m.group(3))
            self._drag_win_y = int(m.group(4))
        else:
            self._drag_win_x = self.root.winfo_x()
            self._drag_win_y = self.root.winfo_y()
        self.root.lift()

    def _do_drag(self, event):
        """Move window during drag."""
        if self._is_maximized:
            self._toggle_maximize()
        dx = event.x_root - self._drag_start_x
        dy = event.y_root - self._drag_start_y
        x = self._drag_win_x + dx
        y = self._drag_win_y + dy
        # Use Win32 MoveWindow with repaint flag to avoid ghosting
        if sys.platform == "win32" and hasattr(self, "_hwnd"):
            try:
                import ctypes
                w = self.root.winfo_width()
                h = self.root.winfo_height()
                ctypes.windll.user32.MoveWindow(self._hwnd, x, y, w, h, True)
                return
            except Exception:
                pass
        self.root.geometry(f"+{x}+{y}")

    def _end_drag(self, event):
        """Ensure window stays visible after drag."""
        self.root.lift()
        self.root.focus_force()

    def _minimize_window(self):
        """Minimize to taskbar."""
        if sys.platform == "win32" and hasattr(self, "_hwnd"):
            try:
                import ctypes
                ctypes.windll.user32.ShowWindow(self._hwnd, 6)  # SW_MINIMIZE
                return
            except Exception:
                pass
        self.root.withdraw()
        self._owner.iconify()

    def _toggle_maximize(self):
        """Toggle between maximized and normal size."""
        if self._is_maximized:
            self.root.geometry(self._normal_geometry)
            self.max_btn.configure(text="\u25fb")
            self._is_maximized = False
        else:
            self._normal_geometry = self.root.geometry()
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
                w = self.root.winfo_screenwidth()
                h = self.root.winfo_screenheight() - 48
            self.root.geometry(f"{w}x{h}+{x}+{y}")
            self.max_btn.configure(text="\u25a3")
            self._is_maximized = True

    def _build_resize_grip(self):
        """Add resize grip to bottom-right corner."""
        self._grip = tk.Label(
            self.root, text="\u2921",
            bg=DARK_THEME["bg"], fg=DARK_THEME["cyan_dim"],
            font=("Consolas", 10), cursor="size_nw_se"
        )
        self._grip.place(relx=1.0, rely=1.0, anchor=tk.SE)
        self._grip.bind("<Button-1>", self._start_resize)
        self._grip.bind("<B1-Motion>", self._do_resize)

    def _start_resize(self, event):
        self._resize_x = event.x_root
        self._resize_y = event.y_root
        self._resize_w = self.root.winfo_width()
        self._resize_h = self.root.winfo_height()

    def _do_resize(self, event):
        dx = event.x_root - self._resize_x
        dy = event.y_root - self._resize_y
        new_w = max(900, self._resize_w + dx)
        new_h = max(500, self._resize_h + dy)
        self.root.geometry(f"{new_w}x{new_h}")

    # ── Corner decorations ──────────────────────────────────────

    # Corner decorations removed — overlapped with content

    # ── Animation system ────────────────────────────────────────

    def _start_animation_loop(self):
        """Start the unified animation loop."""
        self._stop_animation_loop()
        self._anim_frame = 0
        # Reset idle status cycling to start fresh
        self._idle_active = True
        self._idle_pause_until = 0
        self._idle_char_pos = 0
        self._idle_display_frames = 0
        self._anim_tick()

    def _stop_animation_loop(self):
        """Stop all animations."""
        if self._anim_id:
            self.root.after_cancel(self._anim_id)
            self._anim_id = None

    def _anim_tick(self):
        """Master animation tick at ~30fps."""
        self._anim_frame = (self._anim_frame + 1) % 3600

        # Ticker
        if self._ticker_running:
            self._ticker_step()

        # Glitch effect (overrides pulse)
        self._animate_glitch()

        # Pulsing borders (skipped during glitch/flash)
        self._pulse_borders()

        # Sash flash
        self._animate_sash_flash()

        # Feed glows
        self._animate_feed_glows()

        # Title glow
        self._animate_title_glow()

        # Neon sweep line
        self._draw_title_neon_line()

        # Status bar cursor blink + clock
        self._animate_status_bar()

        # Typewriter effect
        self._animate_typewriter()

        self._anim_id = self.root.after(33, self._anim_tick)

    def _lerp_color(self, hex1, hex2, t):
        """Linearly interpolate between two hex colors."""
        r1, g1, b1 = int(hex1[1:3], 16), int(hex1[3:5], 16), int(hex1[5:7], 16)
        r2, g2, b2 = int(hex2[1:3], 16), int(hex2[3:5], 16), int(hex2[5:7], 16)
        r = int(r1 + (r2 - r1) * t)
        g = int(g1 + (g2 - g1) * t)
        b = int(b1 + (b2 - b1) * t)
        return f"#{r:02x}{g:02x}{b:02x}"

    def _create_gradient_image(self, width, height, color1, color2, cache_key=None):
        """Create a diagonal gradient image (top-left=color1, bottom-right=color2).

        Returns a PIL.ImageTk.PhotoImage. Stored in _gradient_cache to prevent GC.
        """
        if width < 1 or height < 1:
            return None
        r1, g1, b1 = int(color1[1:3], 16), int(color1[3:5], 16), int(color1[5:7], 16)
        r2, g2, b2 = int(color2[1:3], 16), int(color2[3:5], 16), int(color2[5:7], 16)
        img = Image.new("RGB", (width, height))
        draw = ImageDraw.Draw(img)
        # Draw diagonal lines from top-right to bottom-left; each line shares the same
        # diagonal distance factor (0..1) which maps to the color blend.
        max_d = width + height - 2 if (width + height - 2) > 0 else 1
        for d in range(width + height - 1):
            t = d / max_d
            r = int(r1 + (r2 - r1) * t)
            g = int(g1 + (g2 - g1) * t)
            b = int(b1 + (b2 - b1) * t)
            color = f"#{r:02x}{g:02x}{b:02x}"
            # Each anti-diagonal line: from (d,0) toward (0,d)
            x0 = min(d, width - 1)
            y0 = d - x0
            x1 = max(d - (height - 1), 0)
            y1 = d - x1
            draw.line([(x0, y0), (x1, y1)], fill=color)
        photo = ImageTk.PhotoImage(img)
        key = cache_key or id(photo)
        self._gradient_cache[key] = photo
        return photo

    def _pulse_borders(self):
        """Animate panel borders with sine-wave pulsing at different intervals."""
        if self._glitch_active or self._sash_flash_active:
            return
        for widget, color_key, period in self._neon_panels:
            t_val = (math.sin(self._anim_frame * (2 * math.pi / period)) + 1) / 2
            bright = DARK_THEME[color_key]
            dim = DARK_THEME[color_key + "_dim"]
            color = self._lerp_color(dim, bright, t_val)
            widget.configure(highlightbackground=color)

    def _animate_title_glow(self):
        """Subtle color cycle on the WIREFEEDR title."""
        t_val = (math.sin(self._anim_frame * (2 * math.pi / 180)) + 1) / 2
        color = self._lerp_color(DARK_THEME["cyan"], DARK_THEME["magenta"], t_val)
        self.title_label.configure(fg=color)

    def _draw_title_neon_line(self):
        """Draw two animated neon sweeps chasing around window frame with diagonal gradient colors."""
        top = self._border_top
        bottom = self._border_bottom
        left = self._border_left
        right = self._border_right

        w = top.winfo_width()
        h = left.winfo_height()
        if w < 10 or h < 10:
            return

        t = DARK_THEME
        thickness = 2

        # Full cycle = 300 frames (~10s)
        cycle = self._anim_frame % 300
        pos1 = cycle / 300.0  # Wave 1 position (0 to 1)
        pos2 = (pos1 + 0.5) % 1.0  # Wave 2, opposite side

        perimeter = 2 * w + 2 * h
        max_diag = w + h if (w + h) > 0 else 1  # for diagonal factor normalization

        # Initialize segments on resize — store (rid, seg_pos, diag_factor)
        if not hasattr(self, '_border_seg_count') or self._border_seg_count != (w, h):
            self._border_seg_count = (w, h)
            for canvas in [top, bottom, left, right]:
                canvas.delete("all")
            self._border_ids = {'top': [], 'bottom': [], 'left': [], 'right': []}

            # Top: left to right — y=0, x varies
            for x in range(0, w, 4):
                rid = top.create_rectangle(x, 0, x + 4, thickness, fill=t["bg"], outline="")
                diag = x / max_diag  # top-left=0, top-right=~0.5
                self._border_ids['top'].append((rid, x / perimeter, diag))

            # Right: top to bottom — x=w, y varies
            for y in range(0, h, 4):
                rid = right.create_rectangle(0, y, thickness, y + 4, fill=t["bg"], outline="")
                diag = (w + y) / max_diag  # top-right=~0.5, bottom-right=1.0
                self._border_ids['right'].append((rid, (w + y) / perimeter, min(diag, 1.0)))

            # Bottom: right to left — y=h, x varies (reversed)
            for x in range(w, 0, -4):
                rid = bottom.create_rectangle(x - 4, 0, x, thickness, fill=t["bg"], outline="")
                diag = (x + h) / max_diag  # bottom-right=1.0, bottom-left=~0.5
                self._border_ids['bottom'].append((rid, (w + h + (w - x)) / perimeter, min(diag, 1.0)))

            # Left: bottom to top — x=0, y varies (reversed)
            for y in range(h, 0, -4):
                rid = left.create_rectangle(0, y - 4, thickness, y, fill=t["bg"], outline="")
                diag = y / max_diag  # bottom-left=~0.5, top-left=0
                self._border_ids['left'].append((rid, (2 * w + h + (h - y)) / perimeter, diag))

        # Update all segments with dual wave colors + diagonal gradient
        base_color = t["bg"]
        cyan = t["cyan"]
        magenta = t["magenta"]
        for side in ['top', 'right', 'bottom', 'left']:
            canvas = {'top': top, 'right': right, 'bottom': bottom, 'left': left}[side]
            for rid, seg_pos, diag in self._border_ids[side]:
                # Each wave's peak color varies by diagonal position
                wave_color = self._lerp_color(cyan, magenta, diag)

                # Distance to wave 1
                dist1 = min(abs(seg_pos - pos1), 1.0 - abs(seg_pos - pos1))
                bright1 = max(0, 1.0 - dist1 * 8)

                # Distance to wave 2
                dist2 = min(abs(seg_pos - pos2), 1.0 - abs(seg_pos - pos2))
                bright2 = max(0, 1.0 - dist2 * 8)

                # Blend: both waves use the same position-based color
                total_bright = max(bright1, bright2)
                if total_bright > 0:
                    color = self._lerp_color(base_color, wave_color, total_bright)
                else:
                    color = base_color

                canvas.itemconfigure(rid, fill=color)

    def _animate_status_bar(self):
        """Blink the cursor, update clock, and cycle idle messages."""
        # Cursor blink
        visible = (self._anim_frame // 16) % 2 == 0
        self._cursor_label.configure(
            fg=DARK_THEME["cyan"] if visible else DARK_THEME["status_bg"]
        )

        # Check if we should resume idle cycling
        if not self._idle_active and self._anim_frame >= self._idle_pause_until:
            self._idle_active = True
            self._idle_char_pos = 0
            self._idle_display_frames = 0

        # Idle message typewriter cycling
        if self._idle_active:
            current_message = self._idle_messages[self._idle_message_index]
            full_text = f"... {current_message}"  # Leading dots only

            if self._idle_char_pos < len(full_text):
                # Typewriter effect: add 4 characters every frame (fast typing)
                self._idle_char_pos = min(self._idle_char_pos + 4, len(full_text))
                partial = full_text[:self._idle_char_pos]
                self.status_bar.configure(text=partial)
            else:
                # Message complete, display for random interval then move to next
                self._idle_display_frames += 1
                # Random intervals: 3s, 5s, 7s, 9s, 12s (at 30fps)
                if not hasattr(self, '_idle_current_duration'):
                    self._idle_current_duration = random.choice([90, 150, 210, 270, 360])
                if self._idle_display_frames > self._idle_current_duration:
                    # Move to next message with new random duration
                    self._idle_message_index = (self._idle_message_index + 1) % len(self._idle_messages)
                    self._idle_char_pos = 0
                    self._idle_display_frames = 0
                    self._idle_current_duration = random.choice([90, 150, 210, 270, 360])

    # ── Hover glow (Feature 3) ────────────────────────────────

    def _on_article_hover(self, event):
        """Apply hover highlight to article row under cursor."""
        item = self.articles_tree.identify_row(event.y)
        if item == self._hover_item:
            return
        if self._hover_item:
            try:
                tags = list(self.articles_tree.item(self._hover_item, "tags") or ())
                if "hover" in tags:
                    tags.remove("hover")
                    self.articles_tree.item(self._hover_item, tags=tags)
            except tk.TclError:
                pass
        self._hover_item = item
        if item:
            try:
                tags = list(self.articles_tree.item(item, "tags") or ())
                if "hover" not in tags:
                    tags.append("hover")
                    self.articles_tree.item(item, tags=tags)
            except tk.TclError:
                pass

    def _on_article_leave(self, event):
        """Clear hover when mouse leaves articles tree."""
        if self._hover_item:
            try:
                tags = list(self.articles_tree.item(self._hover_item, "tags") or ())
                if "hover" in tags:
                    tags.remove("hover")
                    self.articles_tree.item(self._hover_item, tags=tags)
            except tk.TclError:
                pass
            self._hover_item = None

    # ── Glitch effect (Feature 1) ─────────────────────────────

    def _start_glitch(self):
        """Activate glitch effect on refresh start."""
        self._glitch_active = True
        self._glitch_end_frame = (self._anim_frame + 8) % 3600
        self._glitch_sequence = ["#00ffff", "#ff00ff", "#ffffff", "#00ffff", "#ff00ff", "#ffffff", "#00ffff", "#ff00ff"]
        self._glitch_step = 0

    def _animate_glitch(self):
        """Flash panel borders through a fixed neon sequence."""
        if not self._glitch_active:
            return
        if self._anim_frame == self._glitch_end_frame:
            self._glitch_active = False
            return
        color = self._glitch_sequence[self._glitch_step % len(self._glitch_sequence)]
        self._glitch_step += 1
        for widget, _, _ in self._neon_panels:
            widget.configure(highlightbackground=color)

    # ── Sash flash (Feature 4) ────────────────────────────────

    def _on_sash_press(self, event):
        """Detect if press is on a PanedWindow sash."""
        try:
            result = str(event.widget.identify(event.x, event.y))
            self._sash_dragging = "sash" in result or "separator" in result
        except Exception:
            # Fallback: check if click is near a sash coordinate
            try:
                paned = event.widget
                for i in range(len(paned.panes()) - 1):
                    sx, sy = paned.sash_coord(i)
                    orient = str(paned.cget("orient"))
                    if orient == "horizontal":
                        if abs(event.y - sy) < 8:
                            self._sash_dragging = True
                            return
                    else:
                        if abs(event.x - sx) < 8:
                            self._sash_dragging = True
                            return
            except Exception:
                pass
            self._sash_dragging = False

    def _on_sash_release(self, event):
        """Trigger border flash on sash release."""
        if self._sash_dragging:
            self._sash_flash_active = True
            self._sash_flash_end_frame = (self._anim_frame + 10) % 3600
            self._sash_dragging = False

    def _animate_sash_flash(self):
        """Fade panel borders from white back to normal after sash release."""
        if not self._sash_flash_active:
            return
        remaining = (self._sash_flash_end_frame - self._anim_frame) % 3600
        if remaining > 10 or remaining == 0:
            self._sash_flash_active = False
            return
        t = remaining / 10.0
        flash_color = self._lerp_color(DARK_THEME["cyan"], "#ffffff", t)
        for widget, _, _ in self._neon_panels:
            widget.configure(highlightbackground=flash_color)

    # ── Feed glow (Feature 2) ─────────────────────────────────

    def _snapshot_feed_counts(self):
        """Capture unread counts before refresh to detect new articles."""
        feeds = self.storage.get_feeds()
        self._pre_refresh_counts = {
            feed["id"]: self.storage.get_article_count(feed["id"], unread_only=True)
            for feed in feeds
        }

    def _detect_new_article_feeds(self):
        """Start glow on feeds that received new articles."""
        feeds = self.storage.get_feeds()
        for feed in feeds:
            old_count = self._pre_refresh_counts.get(feed["id"], 0)
            new_count = self.storage.get_article_count(feed["id"], unread_only=True)
            if new_count > old_count:
                iid = f"feed_{feed['id']}"
                self._glowing_feeds[iid] = (self._anim_frame + 90) % 3600

    def _animate_feed_glows(self):
        """Pulse foreground color of feeds with new articles."""
        if not self._glowing_feeds:
            return
        expired = []
        t_val = (math.sin(self._anim_frame * (2 * math.pi / 60)) + 1) / 2
        color = self._lerp_color(DARK_THEME["cyan_dim"], DARK_THEME["cyan"], t_val)
        for iid, end_frame in self._glowing_feeds.items():
            if self._anim_frame == end_frame:
                expired.append(iid)
                continue
            try:
                tag_name = f"glow_{iid}"
                self.feeds_tree.tag_configure(tag_name, foreground=color)
                current_tags = list(self.feeds_tree.item(iid, "tags") or ())
                if tag_name not in current_tags:
                    current_tags.append(tag_name)
                    self.feeds_tree.item(iid, tags=current_tags)
            except tk.TclError:
                expired.append(iid)
        for iid in expired:
            del self._glowing_feeds[iid]
            try:
                tag_name = f"glow_{iid}"
                current_tags = list(self.feeds_tree.item(iid, "tags") or ())
                if tag_name in current_tags:
                    current_tags.remove(tag_name)
                    self.feeds_tree.item(iid, tags=current_tags)
            except tk.TclError:
                pass

    # ── Typewriter effect (Feature 5) ─────────────────────────

    def _start_typewriter(self, text, article_id):
        """Begin typewriter animation for article preview."""
        self._cancel_typewriter()
        self._typewriter_active = True
        self._typewriter_full_text = text
        self._typewriter_words = text.split(" ")
        self._typewriter_pos = 0
        self._typewriter_article_id = article_id

    def _cancel_typewriter(self):
        """Cancel in-progress typewriter animation."""
        self._typewriter_active = False
        self._typewriter_words = []
        self._typewriter_pos = 0
        self._typewriter_article_id = None
        self._typewriter_pending_highlight = False
        self._typewriter_full_text = ""

    def _animate_typewriter(self):
        """Insert next chunk of words into preview with live highlighting."""
        if not self._typewriter_active:
            return
        if self.selected_article_id != self._typewriter_article_id:
            self._cancel_typewriter()
            return
        if self._typewriter_pos >= len(self._typewriter_words):
            self._finish_typewriter()
            return
        end_pos = min(self._typewriter_pos + self._typewriter_chunk_size,
                      len(self._typewriter_words))
        self._typewriter_pos = end_pos
        # Rebuild text from words typed so far, apply full highlighting
        partial_text = " ".join(self._typewriter_words[:self._typewriter_pos])
        self.preview_text.configure(state=tk.NORMAL)
        self.preview_text.delete("1.0", tk.END)
        self._apply_highlighting(self.preview_text, partial_text)
        self.preview_text.configure(state=tk.DISABLED)
        self.preview_text.see(tk.END)

    def _finish_typewriter(self):
        """Finalize typewriter — add related articles."""
        self._typewriter_active = False
        # Clear previous related article targets
        self._related_article_targets = {}

        # Related articles
        article_id = self._typewriter_article_id
        if hasattr(self, "cluster_map") and article_id in self.cluster_map:
            cluster = self.cluster_map[article_id]
            if cluster["count"] > 1:
                self.preview_text.configure(state=tk.NORMAL)
                # Header in yellow with instruction
                start = self.preview_text.index(tk.END)
                self.preview_text.insert(tk.END, "\n\n─── RELATED ARTICLES ───\n───── Click to Read ─────\n\n")
                self.preview_text.tag_add("related_header", start, tk.END)
                self.preview_text.tag_add("related_header", start, tk.END)

                # Related items in yellow (clickable)
                for i, related in enumerate(cluster["articles"][1:]):
                    source = related.get("feed_name", "Unknown")
                    score = related.get("noise_score", 0)
                    related_id = related.get("id")

                    # Create unique tag for this related article
                    tag_name = f"related_link_{related_id}"

                    # Store the article ID for this tag
                    self._related_article_targets[tag_name] = related_id

                    # Configure tag appearance (no underline)
                    self.preview_text.tag_configure(
                        tag_name,
                        foreground=DARK_THEME["neon_yellow"]
                    )

                    # Get position before insert
                    line_start = self.preview_text.index("end-1c")

                    # Insert the text
                    text = f"  [{source}] {related['title']} ({score})\n"
                    self.preview_text.insert(tk.END, text)

                    # Apply tag to the inserted text
                    line_end = self.preview_text.index("end-1c")
                    self.preview_text.tag_add(tag_name, line_start, line_end)

                self.preview_text.configure(state=tk.DISABLED)

                # Bind handlers for related links
                self.preview_text.bind("<Button-1>", self._on_preview_click, add=True)
                self.preview_text.bind("<Motion>", self._on_preview_motion, add=True)

        self._typewriter_article_id = None

    def _on_preview_click(self, event):
        """Handle clicks on the preview text, checking for related article links."""
        # Get the index at click position
        index = self.preview_text.index(f"@{event.x},{event.y}")
        # Check all tags at this position
        tags = self.preview_text.tag_names(index)
        for tag in tags:
            if tag.startswith("related_link_") and tag in self._related_article_targets:
                article_id = self._related_article_targets[tag]
                self._navigate_to_article(article_id)
                return

    def _on_preview_motion(self, event):
        """Change cursor when hovering over related article links."""
        index = self.preview_text.index(f"@{event.x},{event.y}")
        tags = self.preview_text.tag_names(index)
        is_link = any(tag.startswith("related_link_") for tag in tags)
        self.preview_text.configure(cursor="hand2" if is_link else "")

    def _navigate_to_article(self, article_id):
        """Navigate to and display a specific article."""
        if not article_id:
            return
        # Find and select the article in the tree
        for item in self.articles_tree.get_children():
            if int(item) == article_id:
                self.articles_tree.selection_set(item)
                self.articles_tree.see(item)
                self._on_article_select(None)
                return
        # Article not in current view - fetch and display directly
        article = self.storage.get_article(article_id)
        if article:
            self._display_article(article)

    # ── Boot sequence ───────────────────────────────────────────

    def _play_boot_sequence(self):
        """Play cyberpunk boot-up animation."""
        self._boot_overlay = tk.Canvas(
            self.root, bg=DARK_THEME["bg"], highlightthickness=0
        )
        self._boot_overlay.place(relx=0, rely=0, relwidth=1, relheight=1)
        self.root.update_idletasks()
        tk.Misc.lift(self._boot_overlay)

        self._boot_lines = [
            "WIREFEEDR v2.0",
            "INITIALIZING NEURAL FEED PARSER",
            "CONNECTING TO NEWS GRID",
            "BIAS DETECTION MATRIX: ONLINE",
            "SIGNAL LOCKED. WELCOME, OPERATOR.",
        ]
        self._boot_step = 0
        self.root.after(200, self._boot_next_line)

    def _boot_next_line(self):
        """Display next boot line with typewriter effect."""
        if self._boot_step >= len(self._boot_lines):
            self.root.after(400, self._boot_fade_out)
            return

        y = 200 + self._boot_step * 28
        text = self._boot_lines[self._boot_step]
        color = DARK_THEME["cyan"] if self._boot_step < len(self._boot_lines) - 1 else DARK_THEME["magenta"]

        self._boot_overlay.create_text(
            60, y, text=text, fill=color, anchor=tk.W,
            font=("Consolas", 11, "bold")
        )
        self._boot_step += 1
        self.root.after(300, self._boot_next_line)

    def _boot_fade_out(self):
        """Remove boot overlay and start animations."""
        self._boot_overlay.destroy()
        self._start_animation_loop()

    # ── Tooltip for logo ────────────────────────────────────────

    def _show_logo_tooltip(self, event):
        """Show Patreon tooltip on logo hover."""
        self._logo_tooltip = tk.Toplevel(self.root)
        self._logo_tooltip.wm_overrideredirect(True)
        self._logo_tooltip.wm_geometry(f"+{event.x_root + 10}+{event.y_root + 10}")
        label = tk.Label(
            self._logo_tooltip, text="Patreon",
            bg=DARK_THEME["bg_secondary"], fg=DARK_THEME["cyan"],
            font=("Consolas", 9), padx=6, pady=2,
            relief=tk.SOLID, borderwidth=1
        )
        label.pack()
        event.widget.configure(bg=DARK_THEME["bg_secondary"])

    def _hide_logo_tooltip(self, event):
        """Hide Patreon tooltip."""
        if hasattr(self, '_logo_tooltip') and self._logo_tooltip:
            self._logo_tooltip.destroy()
            self._logo_tooltip = None
        event.widget.configure(bg=DARK_THEME["bg"])

    # ── Window close ────────────────────────────────────────────

    def _on_close(self):
        """Handle window close."""
        self._stop_animation_loop()
        self.storage.close()
        self.root.destroy()
        self._owner.destroy()


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


SINGLE_INSTANCE_PORT = 47391  # Arbitrary port for instance communication


def signal_existing_instance_to_close():
    """Try to signal any existing instance to close."""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(1)
        sock.connect(('127.0.0.1', SINGLE_INSTANCE_PORT))
        sock.send(b'CLOSE')
        sock.close()
        import time
        time.sleep(0.5)  # Give existing instance time to close
    except (ConnectionRefusedError, socket.timeout, OSError):
        pass  # No existing instance


def start_instance_listener(root):
    """Start a listener thread that closes the app when signaled."""
    def listener():
        try:
            server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            server.bind(('127.0.0.1', SINGLE_INSTANCE_PORT))
            server.listen(1)
            server.settimeout(1)
            while True:
                try:
                    conn, addr = server.accept()
                    data = conn.recv(1024)
                    conn.close()
                    if data == b'CLOSE':
                        root.after(0, root.destroy)
                        break
                except socket.timeout:
                    if not root.winfo_exists():
                        break
        except OSError:
            pass  # Port in use or other error

    thread = threading.Thread(target=listener, daemon=True)
    thread.start()


if __name__ == "__main__":
    signal_existing_instance_to_close()
    root = tk.Tk()
    start_instance_listener(root)
    app = NewsAggregatorApp(root)
    root.mainloop()
