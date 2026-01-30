# dialogs.py - Dialog windows and instance management

import tkinter as tk
from tkinter import ttk, messagebox
import socket
import threading

from config import DARK_THEME
from storage import Storage
from feeds import FeedManager
from constants import SINGLE_INSTANCE_PORT


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
