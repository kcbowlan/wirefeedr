# dialogs.py - Dialog windows and instance management

import tkinter as tk
from tkinter import ttk, messagebox
import socket
import threading
import webbrowser

from config import DARK_THEME, BIAS_COLORS, FACTUAL_COLORS, get_grade
from storage import Storage
from feeds import FeedManager
from constants import SINGLE_INSTANCE_PORT
import mbfc
import animations


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


class CredibilityDetailDialog:
    """Modal dialog showing full score breakdown for an article."""

    def __init__(self, parent, article: dict, mbfc_source: dict | None):
        self.article = article
        self.mbfc_source = mbfc_source

        composite = article.get("noise_score", 0)
        letter, label, color = get_grade(composite)
        pub_score = mbfc.publisher_score(mbfc_source) if mbfc_source else None

        # Back-derive article-only score
        if pub_score is not None:
            article_score = max(0, min(100, round((composite - 0.4 * pub_score) / 0.6)))
        else:
            article_score = composite

        self.dialog = tk.Toplevel(parent)
        self.dialog.title("Credibility Analysis")
        self.dialog.geometry("480x520")
        self.dialog.resizable(False, False)
        self.dialog.transient(parent)
        self.dialog.grab_set()
        self.dialog.configure(bg=DARK_THEME["bg"])
        self.dialog.geometry(f"+{parent.winfo_x() + 200}+{parent.winfo_y() + 60}")
        self.dialog.bind("<Escape>", lambda e: self.dialog.destroy())

        self._build_header()
        self._build_composite_score(composite, letter, label, color)
        self._build_breakdown_bar(article_score, pub_score)
        self._build_wrfdr_section(article_score)
        self._build_mbfc_section()
        self._build_close_button()

        self.dialog.wait_window()

    def _build_header(self):
        """Gradient header banner."""
        hdr = tk.Canvas(self.dialog, height=36, highlightthickness=0,
                        bg=DARK_THEME["bg"])
        hdr.pack(fill=tk.X)
        hdr.update_idletasks()
        w = max(hdr.winfo_width(), 480)
        # Draw gradient manually
        for i in range(w):
            t = i / max(w - 1, 1)
            r = int(10 + (26 - 10) * t)
            g = int(16 + (10 - 16) * t)
            b = int(40 + (32 - 40) * t)
            hdr.create_line(i, 0, i, 36, fill=f"#{r:02x}{g:02x}{b:02x}")
        hdr.create_text(w // 2, 18, text="CREDIBILITY ANALYSIS",
                        fill=DARK_THEME["cyan"], font=("Consolas", 12, "bold"))

    def _build_composite_score(self, composite, letter, label, color):
        """Big score number + grade + article title."""
        frame = tk.Frame(self.dialog, bg=DARK_THEME["bg"])
        frame.pack(fill=tk.X, padx=20, pady=(12, 4))

        score_text = f"{composite}  {label.upper()} ({letter})"
        tk.Label(frame, text=score_text, font=("Consolas", 22, "bold"),
                 fg=color, bg=DARK_THEME["bg"]).pack()

        title = self.article.get("title", "")
        if len(title) > 70:
            title = title[:67] + "..."
        tk.Label(frame, text=f'"{title}"', font=("Consolas", 9),
                 fg=DARK_THEME["fg_secondary"], bg=DARK_THEME["bg"],
                 wraplength=440).pack(pady=(2, 0))

    def _build_breakdown_bar(self, article_score, pub_score):
        """Proportional WRFDR / MBFC bar."""
        frame = tk.Frame(self.dialog, bg=DARK_THEME["bg"])
        frame.pack(fill=tk.X, padx=20, pady=(10, 2))

        bar = tk.Canvas(frame, height=28, highlightthickness=0,
                        bg=DARK_THEME["bg_secondary"])
        bar.pack(fill=tk.X)
        bar.update_idletasks()
        total_w = max(bar.winfo_width(), 440)

        if pub_score is not None:
            wrfdr_frac = 0.6
            mbfc_frac = 0.4
            wrfdr_w = int(total_w * wrfdr_frac)
            mbfc_w = total_w - wrfdr_w
            bar.create_rectangle(0, 0, wrfdr_w, 28, fill="#1a3a5c", outline="")
            bar.create_text(wrfdr_w // 2, 14, text=f"WRFDR: {article_score}",
                            fill=DARK_THEME["cyan"], font=("Consolas", 10, "bold"))
            bar.create_rectangle(wrfdr_w, 0, total_w, 28, fill="#3a1a4c", outline="")
            bar.create_text(wrfdr_w + mbfc_w // 2, 14, text=f"MBFC: {pub_score}",
                            fill=DARK_THEME["magenta"], font=("Consolas", 10, "bold"))
            formula = f"0.6 \u00d7 {article_score} + 0.4 \u00d7 {pub_score} = {self.article.get('noise_score', 0)}"
        else:
            bar.create_rectangle(0, 0, total_w, 28, fill="#1a3a5c", outline="")
            bar.create_text(total_w // 2, 14, text=f"WRFDR: {article_score}",
                            fill=DARK_THEME["cyan"], font=("Consolas", 10, "bold"))
            formula = f"WRFDR only (no MBFC data) = {article_score}"

        tk.Label(frame, text=formula, font=("Consolas", 9),
                 fg=DARK_THEME["fg_secondary"], bg=DARK_THEME["bg"]).pack(pady=(4, 0))

    def _build_wrfdr_section(self, article_score):
        """WRFDR article analysis section."""
        frame = tk.Frame(self.dialog, bg=DARK_THEME["bg"])
        frame.pack(fill=tk.X, padx=20, pady=(10, 0))

        tk.Label(frame, text="\u2500\u2500 WRFDR ARTICLE ANALYSIS \u2500" * 3,
                 font=("Consolas", 9), fg=DARK_THEME["cyan"],
                 bg=DARK_THEME["bg"]).pack(anchor=tk.W)

        detail = tk.Frame(frame, bg=DARK_THEME["bg"])
        detail.pack(fill=tk.X, padx=10, pady=(4, 0))

        _, lbl, clr = get_grade(article_score)
        tk.Label(detail, text=f"Score: {article_score}  ({lbl})",
                 font=("Consolas", 10), fg=clr,
                 bg=DARK_THEME["bg"]).pack(anchor=tk.W)

        tk.Label(detail,
                 text="Signals: opinion, sensationalism, clickbait,\n"
                      "punctuation, caps, summary analysis",
                 font=("Consolas", 9), fg=DARK_THEME["fg_secondary"],
                 bg=DARK_THEME["bg"], justify=tk.LEFT).pack(anchor=tk.W, pady=(2, 0))

    def _build_mbfc_section(self):
        """MBFC publisher data section."""
        frame = tk.Frame(self.dialog, bg=DARK_THEME["bg"])
        frame.pack(fill=tk.X, padx=20, pady=(10, 0))

        tk.Label(frame, text="\u2500\u2500 MBFC PUBLISHER DATA \u2500" * 3,
                 font=("Consolas", 9), fg=DARK_THEME["magenta"],
                 bg=DARK_THEME["bg"]).pack(anchor=tk.W)

        detail = tk.Frame(frame, bg=DARK_THEME["bg"])
        detail.pack(fill=tk.X, padx=10, pady=(4, 0))

        if not self.mbfc_source:
            tk.Label(detail,
                     text="No MBFC data available for this publisher.",
                     font=("Consolas", 10), fg=DARK_THEME["fg_secondary"],
                     bg=DARK_THEME["bg"]).pack(anchor=tk.W, pady=8)
            return

        src = self.mbfc_source
        rows = []

        # Publisher name
        name = src.get("name", "Unknown")
        rows.append(("Publisher:", name, DARK_THEME["fg"]))

        # Bias
        bias_raw = mbfc.map_bias_to_wirefeedr(src.get("bias", ""))
        bias_color = BIAS_COLORS.get(bias_raw, DARK_THEME["fg"])
        rows.append(("Bias:", bias_raw or "Unknown", bias_color))

        # Factual Reporting
        reporting_raw = mbfc.map_reporting_to_wirefeedr(src.get("reporting", ""))
        reporting_color = FACTUAL_COLORS.get(reporting_raw, DARK_THEME["fg"])
        rows.append(("Factual Rep.:", reporting_raw or "Unknown", reporting_color))

        # Credibility
        cred = (src.get("credibility") or "").replace("-", " ").title()
        cred_color = "#27ae60" if "high" in cred.lower() else (
            DARK_THEME["fg"] if "medium" in cred.lower() else "#e74c3c")
        rows.append(("Credibility:", cred or "Unknown", cred_color))

        # Questionable flags
        flags = src.get("questionable") or []
        flag_text = ", ".join(f.replace("-", " ").title() for f in flags) if flags else "None"
        flag_color = "#e74c3c" if flags else "#27ae60"
        rows.append(("Flags:", flag_text, flag_color))

        # Publisher score
        pub_score = mbfc.publisher_score(src)
        if pub_score is not None:
            _, plbl, pclr = get_grade(pub_score)
            rows.append(("Pub Score:", f"{pub_score}  ({plbl})", pclr))

        for label_text, value, color in rows:
            row = tk.Frame(detail, bg=DARK_THEME["bg"])
            row.pack(fill=tk.X, pady=1)
            tk.Label(row, text=label_text, font=("Consolas", 10),
                     fg=DARK_THEME["fg_secondary"], bg=DARK_THEME["bg"],
                     width=14, anchor=tk.W).pack(side=tk.LEFT)
            tk.Label(row, text=value, font=("Consolas", 10),
                     fg=color, bg=DARK_THEME["bg"],
                     anchor=tk.W).pack(side=tk.LEFT)

        # MBFC link
        url = src.get("url", "")
        if url:
            link = tk.Label(detail, text="View on MBFC", font=("Consolas", 10, "underline"),
                            fg=DARK_THEME["cyan"], bg=DARK_THEME["bg"], cursor="hand2")
            link.pack(anchor=tk.W, pady=(6, 0))
            link.bind("<Button-1>", lambda e: webbrowser.open(url))

    def _build_close_button(self):
        """Close button at the bottom."""
        frame = tk.Frame(self.dialog, bg=DARK_THEME["bg"])
        frame.pack(fill=tk.X, pady=(16, 12))
        btn = tk.Button(frame, text="CLOSE", command=self.dialog.destroy,
                        font=("Consolas", 10, "bold"),
                        bg=DARK_THEME["bg_secondary"], fg=DARK_THEME["cyan"],
                        activebackground=DARK_THEME["magenta"],
                        activeforeground=DARK_THEME["fg_highlight"],
                        bd=1, relief=tk.FLAT, padx=20, pady=4,
                        cursor="hand2")
        btn.pack()


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
