# app.py - Tkinter GUI (orchestration + handlers + business logic)

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
import re
from collections import Counter
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
from config import BIAS_COLORS, FACTUAL_COLORS, DARK_THEME, get_grade
from constants import IDLE_MESSAGES, BIAS_POSITIONS, TRENDING_STOP_WORDS, FLAP_CHARS

# Extracted modules
import ui_builders
import window_mgmt
import animations
import ticker
import highlighting
from dialogs import AddFeedDialog, ManageFeedsDialog, FilterKeywordsDialog, CredibilityDetailDialog
import mbfc


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
        window_mgmt.setup_owner_icon(self)
        self._owner.attributes("-alpha", 0)
        self._owner.geometry("1x1+-10000+-10000")

        # Real visible window as Toplevel (borderless via Win32 style stripping)
        self.root = tk.Toplevel(self._owner)
        self.root.title("WIREFEEDR")
        self.root.geometry("1200x700")
        self.root.minsize(900, 500)

        # Strip native title bar via Win32 API (keeps proper z-order unlike overrideredirect)
        window_mgmt.strip_title_bar(self)

        # Restore from taskbar click on hidden owner
        self._owner.bind("<Map>", lambda e: window_mgmt.on_taskbar_restore(self, e))

        # Initialize components
        self.storage = Storage()
        self.feed_manager = FeedManager()
        self.filter_engine = FilterEngine(self.storage.get_filter_keywords())
        mbfc.load_mbfc_data()

        # State
        self.current_feed_id = None  # None = All feeds
        self.current_category = None  # None = no category filter
        self.selected_article_id = None
        self.current_author_url = None
        self.is_fetching = False
        self.auto_refresh_job = None
        self.cluster_map = {}  # Maps article_id -> cluster info for expanding
        self.feed_icons = {}  # Cache for PhotoImage objects
        self._articles_tab = "all"  # "all" or "favorites"

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
        self._bias_arrow_pos = 0.5
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
        self._feed_hover_item = None

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

        # Matrix rain effect (preview placeholder)
        self._rain_active = False
        self._rain_canvas = None
        self._rain_columns = []
        self._rain_col_width = 14
        self._rain_row_height = 16
        self._rain_font = ("Consolas", 11)

        # Static noise bursts
        self._static_noise_active = False
        self._static_noise_frame = 0
        self._static_noise_duration = 0
        self._static_noise_next = 300
        self._static_noise_canvases = []
        self._static_noise_panels = []

        # CRT shutdown
        self._shutdown_active = False
        self._shutdown_canvas = None
        self._shutdown_phase = 0
        self._shutdown_frame = 0

        # Header glitch effect
        self._header_glitch_active = False
        self._header_glitch_frame = 0
        self._header_glitch_duration = 0
        self._header_glitch_target = None
        self._header_glitch_original = ""
        self._header_glitch_next = 0

        # Konami code easter egg
        self._konami_seq = []
        self._konami_code = ["Up", "Up", "Down", "Down", "Left", "Right", "Left", "Right", "b", "a"]
        self._konami_active = False

        # Phosphor afterglow (ticker edges)
        self._phosphor_items = []

        # Idle status cycling (cyberpunk terminal messages)
        self._idle_messages = random.sample(IDLE_MESSAGES, len(IDLE_MESSAGES))
        self._idle_active = True
        self._idle_message_index = 0
        self._idle_char_pos = 0
        self._idle_display_frames = 0  # How long to show completed message
        self._idle_last_real_status = ""
        self._idle_pause_until = 0  # Frame to resume idle cycling

        # Build UI (delegated to ui_builders)
        ui_builders.setup_styles(self)
        ui_builders.build_title_bar(self)
        ui_builders.build_menus(self)
        ui_builders.bind_shortcuts(self)
        ui_builders.build_toolbar(self)
        ui_builders.build_ticker(self)
        ui_builders.build_status_bar(self)  # Pack BOTTOM elements first so they survive resize
        ui_builders.build_main_layout(self)
        window_mgmt.build_resize_grip(self)
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
        animations.play_boot_sequence(self)

    # ── Delegation stubs for callbacks bound in ui_builders ──────

    def _ticker_set_paused(self, paused):
        ticker.ticker_set_paused(self, paused)

    def _on_ticker_configure(self, event):
        ticker.on_ticker_configure(self, event)

    def _on_ticker_click(self, event):
        ticker.on_ticker_click(self, event)

    def _on_ticker_double_click(self, event):
        ticker.on_ticker_double_click(self, event)

    def _on_ticker_motion(self, event):
        ticker.on_ticker_motion(self, event)

    def _update_bias_balance(self):
        ticker.update_bias_balance(self)

    def _toggle_maximize(self):
        window_mgmt.toggle_maximize(self)

    def _minimize_window(self):
        window_mgmt.minimize_window(self)

    def _start_drag(self, event):
        window_mgmt.start_drag(self, event)

    def _do_drag(self, event):
        window_mgmt.do_drag(self, event)

    def _end_drag(self, event):
        window_mgmt.end_drag(self, event)

    def _on_sash_press(self, event):
        animations.on_sash_press(self, event)

    def _on_sash_release(self, event):
        animations.on_sash_release(self, event)

    def _on_article_hover(self, event):
        animations.on_article_hover(self, event)

    def _on_article_leave(self, event):
        animations.on_article_leave(self, event)

    def _show_settings_menu(self, event):
        ui_builders.show_settings_menu(self, event)

    def _setup_highlight_tags(self):
        highlighting.setup_highlight_tags(self)

    def _apply_highlighting(self, text_widget, text):
        highlighting.apply_highlighting(self, text_widget, text)

    def _on_wiki_link_click(self, event):
        highlighting.on_wiki_link_click(self, event)

    def _create_gradient_image(self, width, height, color1, color2, cache_key=None):
        return animations.create_gradient_image(self, width, height, color1, color2, cache_key)

    def _lerp_color(self, hex1, hex2, t):
        return animations.lerp_color(hex1, hex2, t)

    def _draw_panel_header(self, canvas, text, color1, color2, cache_key):
        animations.draw_panel_header(self, canvas, text, color1, color2, cache_key)

    def _show_progress(self):
        ui_builders.show_progress(self)

    def _hide_progress(self):
        ui_builders.hide_progress(self)

    def _update_progress(self, percent):
        ui_builders.update_progress(self, percent)

    def _update_ticker(self):
        ticker.update_ticker(self)

    def _update_trending(self, articles):
        ticker.update_trending(self, articles)

    def _layout_trending_slots(self):
        ticker.layout_trending_slots(self)

    def _flip_all_trending(self):
        ticker.flip_all_trending(self)

    def _display_article(self, article):
        """Display an article in the preview panel."""
        if self._rain_active:
            self._rain_active = False
            if self._rain_canvas:
                self._rain_canvas.delete("all")
                self._rain_canvas.place_forget()

        self.selected_article_id = article["id"]

        if not article.get("is_read", False):
            self.storage.mark_article_read(article["id"])
            item_id = str(article["id"])
            if self.articles_tree.exists(item_id):
                tags = list(self.articles_tree.item(item_id, "tags") or ())
                if "unread" in tags:
                    tags.remove("unread")
                if "read" not in tags:
                    tags.append("read")
                self.articles_tree.item(item_id, tags=tuple(tags))
            self.refresh_feeds_list()

        self.preview_title.configure(text=article["title"])

        bias = article.get("bias", "")
        if bias and bias in BIAS_COLORS:
            self.bias_label.configure(text=bias, fg=BIAS_COLORS[bias],
                                       bg=DARK_THEME["bg_tertiary"])
        else:
            self.bias_label.configure(text=bias or "Unknown", fg=DARK_THEME["fg"],
                                       bg=DARK_THEME["bg_tertiary"])

        mbfc_source = mbfc.lookup_source(article.get("link", ""))
        factual = mbfc.map_reporting_to_wirefeedr(
            mbfc_source.get("reporting", "")) if mbfc_source else ""
        factual = factual or article.get("factual", "")
        if factual and factual in FACTUAL_COLORS:
            self.factual_label.configure(text=factual, fg=FACTUAL_COLORS[factual],
                                          bg=DARK_THEME["bg_tertiary"])
        else:
            self.factual_label.configure(text=factual or "Unknown", fg=DARK_THEME["fg"],
                                          bg=DARK_THEME["bg_tertiary"])

        meta_parts = []
        if article.get("author"):
            meta_parts.append(f"By {article['author']}")
        if article.get("published"):
            meta_parts.append(article["published"])
        if article.get("feed_name"):
            meta_parts.append(f"Source: {article['feed_name']}")
        self.preview_meta.configure(text=" | ".join(meta_parts))

        author = self._clean_author_name(article.get("author", ""))
        if author:
            self.author_menu_btn.configure(state=tk.NORMAL)
            self.current_author_url = None
        else:
            self.author_menu_btn.configure(state=tk.DISABLED)

        self.open_btn._btn_enabled = True
        animations.draw_gradient_btn(self, self.open_btn, hover=False)

        summary = article.get("summary", "No summary available.")
        self.preview_text.configure(state=tk.NORMAL)
        self.preview_text.delete("1.0", tk.END)
        self.preview_text.configure(state=tk.DISABLED)
        animations.start_typewriter(self, summary, article["id"])

        # Show score breakdown in status bar
        self._show_score_status(article)

    # ── Feed operations ──────────────────────────────────────────

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
        self.feeds_tree.insert("", tk.END, iid="all",
                               text=f"\u25c8 All Feeds ({all_count} unread)",
                               tags=("all_item",))

        # Group feeds by category
        feeds = self.storage.get_feeds()
        categories = {}
        for feed in feeds:
            cat = feed["category"]
            if cat not in categories:
                categories[cat] = []
            categories[cat].append(feed)

        for category, cat_feeds in sorted(categories.items()):
            cat_iid = f"cat_{category}"
            divider_text = f"\u2500\u2500\u2500 {category.upper()} " + "\u2500" * max(1, 20 - len(category))
            self.feeds_tree.insert("", tk.END, iid=cat_iid, text=divider_text,
                                   tags=("cat_divider",))
            for feed in cat_feeds:
                unread = self.storage.get_article_count(feed["id"], unread_only=True)
                text = f"  {feed['name']} ({unread})"
                feed_tag = "feed_unread" if unread > 0 else "feed_item"

                # Try to load favicon
                icon = self._load_favicon_image(feed["id"])
                if icon:
                    self.feeds_tree.insert("", tk.END, iid=f"feed_{feed['id']}",
                                          text=text, image=icon,
                                          tags=(feed_tag,))
                else:
                    self.feeds_tree.insert("", tk.END, iid=f"feed_{feed['id']}",
                                          text=text, tags=(feed_tag,))
                    # Fetch favicon in background if not cached
                    if not self.storage.get_feed_favicon(feed["id"]):
                        self._fetch_favicon(feed["id"], feed["url"])

        self._update_bias_balance()

    def refresh_articles(self):
        """Refresh the articles list."""
        self.articles_tree.delete(*self.articles_tree.get_children())

        include_read = self.show_read_var.get()

        # Get filter values from settings menu variables
        recency_hours = int(self._recency_var.get())
        max_per_source = int(self._per_source_var.get())
        use_clustering = self._cluster_var.get()

        # Build feed filter based on selection
        category_feed_ids = None
        if self.current_category:
            feeds = self.storage.get_feeds()
            category_feed_ids = [f["id"] for f in feeds if f["category"] == self.current_category]

        favorites_only = self._articles_tab == "favorites"

        articles = self.storage.get_articles(
            feed_id=self.current_feed_id,
            feed_ids=category_feed_ids,
            include_read=include_read,
            favorites_only=favorites_only,
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

        # Update favorites tab count
        fav_count = len(self.storage.get_articles(favorites_only=True, limit=9999))
        self._tab_fav.configure(text=f"FAVORITES ({fav_count})")

        # Reset preview if selected article is no longer visible
        if self.selected_article_id and not self.articles_tree.exists(str(self.selected_article_id)):
            self.selected_article_id = None
            ui_builders.show_preview_placeholder(self)

        self._update_ticker()

        self._update_trending(articles)

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
        """Display articles grouped by topic clusters."""
        self.cluster_map = {}
        for cluster in clusters:
            primary = cluster["articles"][0]
            if cluster["count"] > 1:
                title = f"[{cluster['count']}] {primary['title']}"
            else:
                title = primary["title"]
            self._insert_article_row(primary, title_override=title)
            self.cluster_map[primary["id"]] = cluster

    def _insert_article_row(self, article: dict, title_override: str = None):
        """Insert a single article row into the treeview."""
        fav = "\u25c6" if article.get("is_favorite") else "\u25c7"
        title = title_override or article["title"]
        source = article.get("feed_name", "Unknown")
        bias = article.get("bias", "")
        date = article.get("published", "")
        if date:
            try:
                dt = datetime.fromisoformat(date)
                hours = (datetime.now() - dt).total_seconds() / 3600
                if hours < 1:
                    date = "Just Now"
                elif hours < 24:
                    half = round(hours * 2) / 2
                    if half == int(half):
                        date = f"{int(half)}h ago"
                    else:
                        date = f"{int(half)}.5h ago"
                elif hours < 168:
                    date = f"{int(hours // 24)}d ago"
                else:
                    date = f"{int(hours // 168)}w ago"
            except:
                pass
        noise = article.get("noise_score", 0)
        letter, label, color = get_grade(noise)
        noise_display = f"{noise} {label}"

        tags = []
        if article.get("is_favorite"):
            tags.append("favorite")
        tags.append("read" if article.get("is_read", False) else "unread")

        self.articles_tree.insert("", tk.END, iid=str(article["id"]),
                                  values=(fav, title, source, bias, date, noise_display),
                                  tags=tuple(tags))

    # ── Fetch operations ─────────────────────────────────────────

    def fetch_all_feeds(self):
        """Fetch all feeds in background."""
        if self.is_fetching:
            return

        self.is_fetching = True
        self.refresh_btn._btn_enabled = False
        animations.draw_gradient_btn(self, self.refresh_btn, hover=False)
        self._show_progress()
        animations.start_glitch(self)
        animations.snapshot_feed_counts(self)

        self._play_refresh_sound()

        def fetch_thread():
            feeds = self.storage.get_feeds()
            total = len(feeds)
            results = []

            for i, feed in enumerate(feeds):
                try:
                    result = self.feed_manager.fetch_feed(feed["url"])
                    if not result.get("success"):
                        results.append((feed["name"], 0, 0))
                        percent = ((i + 1) / total) * 100
                        self.root.after(0, lambda p=percent: self._update_progress(p))
                        continue
                    fetched = result.get("articles", [])
                    new_count = 0
                    for article in fetched:
                        article["feed_id"] = feed["id"]
                        article["bias"] = feed.get("bias", "")
                        article["factual"] = feed.get("factual", "")
                        # Attach MBFC data for article's actual publisher
                        mbfc_source = mbfc.lookup_source(article.get("link", ""))
                        if mbfc_source:
                            article["mbfc"] = mbfc_source
                        # Apply noise scoring (WRFDR-only, before blend)
                        art_score = self.filter_engine.calculate_objectivity_score(
                            title=article.get("title", ""),
                            link=article.get("link", ""),
                            summary=article.get("summary", ""),
                            factual_rating=article.get("factual", "")
                        )
                        # Compute publisher credibility fields
                        pub_score = mbfc.publisher_score(mbfc_source)
                        domain = mbfc.normalize_domain(article.get("link", ""))
                        # Blend with MBFC publisher reputation (40/60)
                        article["noise_score"] = mbfc.composite_score(art_score, mbfc_source)
                        # Extract raw MBFC strings for logging
                        m_bias = mbfc_source.get("bias") if mbfc_source else None
                        m_reporting = mbfc_source.get("reporting") if mbfc_source else None
                        m_credibility = mbfc_source.get("credibility") if mbfc_source else None
                        m_flags = ",".join(mbfc_source.get("questionable", [])) if mbfc_source and mbfc_source.get("questionable") else None
                        if self.storage.add_article(
                            feed_id=article["feed_id"],
                            title=article["title"],
                            link=article["link"],
                            summary=article.get("summary", ""),
                            published=article.get("published"),
                            author=article.get("author", ""),
                            noise_score=article.get("noise_score", 0),
                            publisher_domain=domain or None,
                            article_score=art_score,
                            publisher_score=pub_score,
                            mbfc_bias=m_bias,
                            mbfc_reporting=m_reporting,
                            mbfc_credibility=m_credibility,
                            mbfc_flags=m_flags,
                        ):
                            new_count += 1
                    results.append((feed["name"], new_count, len(fetched)))
                except Exception as e:
                    results.append((feed["name"], 0, 0))

                # Update progress
                percent = ((i + 1) / total) * 100
                self.root.after(0, lambda p=percent: self._update_progress(p))

            # Update UI on main thread
            def finish():
                self.is_fetching = False
                self.refresh_btn._btn_enabled = True
                animations.draw_gradient_btn(self, self.refresh_btn, hover=False)
                self._hide_progress()

                total_new = sum(r[1] for r in results)
                self._update_status(f"Fetched {total_new} new articles from {len(results)} feeds")

                self.refresh_feeds_list()
                self.refresh_articles()

                # Detect and glow feeds with new articles
                animations.detect_new_article_feeds(self)

            self.root.after(0, finish)

        thread = threading.Thread(target=fetch_thread, daemon=True)
        thread.start()

    def _play_refresh_sound(self):
        """Play refresh sound effect."""
        if not HAS_WINSOUND:
            return

        def play_sound():
            try:
                sound_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                                          "793358__someusername0__menu_select.wav")
                if os.path.exists(sound_path):
                    winsound.PlaySound(sound_path, winsound.SND_FILENAME | winsound.SND_ASYNC)
            except:
                pass

        thread = threading.Thread(target=play_sound, daemon=True)
        thread.start()

    # ── Dialog launchers ─────────────────────────────────────────

    def show_add_feed_dialog(self):
        """Show the Add Feed dialog."""
        dialog = AddFeedDialog(self.root, self.feed_manager)
        if dialog.result:
            name, url, category = dialog.result
            feed_id = self.storage.add_feed(name, url, category)
            if feed_id:
                self._update_status(f"Added feed: {name}")
                self.refresh_feeds_list()
                # Auto-fetch
                self._fetch_single_feed(feed_id)
            else:
                self._update_status("Feed already exists")

    def show_manage_feeds_dialog(self):
        """Show the Manage Feeds dialog."""
        dialog = ManageFeedsDialog(self.root, self.storage)
        if dialog.changed:
            self.refresh_feeds_list()
            self.refresh_articles()

    def _fetch_single_feed(self, feed_id: int):
        """Fetch a single feed in background."""
        feed = self.storage.get_feed(feed_id)
        if not feed:
            return

        self._update_status(f"Fetching {feed['name']}...")

        def fetch_thread():
            try:
                result = self.feed_manager.fetch_feed(feed["url"])
                if not result.get("success"):
                    self.root.after(0, lambda: self._update_status(
                        f"Error fetching {feed['name']}: {result.get('error', 'Unknown error')}"))
                    return
                fetched = result.get("articles", [])
                new_count = 0
                for article in fetched:
                    article["feed_id"] = feed_id
                    article["bias"] = feed.get("bias", "")
                    article["factual"] = feed.get("factual", "")
                    # Attach MBFC data for article's actual publisher
                    mbfc_source = mbfc.lookup_source(article.get("link", ""))
                    if mbfc_source:
                        article["mbfc"] = mbfc_source
                    # Apply noise scoring (WRFDR-only, before blend)
                    art_score = self.filter_engine.calculate_objectivity_score(
                        title=article.get("title", ""),
                        link=article.get("link", ""),
                        summary=article.get("summary", ""),
                        factual_rating=article.get("factual", "")
                    )
                    # Compute publisher credibility fields
                    pub_score = mbfc.publisher_score(mbfc_source)
                    domain = mbfc.normalize_domain(article.get("link", ""))
                    # Blend with MBFC publisher reputation (40/60)
                    article["noise_score"] = mbfc.composite_score(art_score, mbfc_source)
                    # Extract raw MBFC strings for logging
                    m_bias = mbfc_source.get("bias") if mbfc_source else None
                    m_reporting = mbfc_source.get("reporting") if mbfc_source else None
                    m_credibility = mbfc_source.get("credibility") if mbfc_source else None
                    m_flags = ",".join(mbfc_source.get("questionable", [])) if mbfc_source and mbfc_source.get("questionable") else None
                    if self.storage.add_article(
                        feed_id=article["feed_id"],
                        title=article["title"],
                        link=article["link"],
                        summary=article.get("summary", ""),
                        published=article.get("published"),
                        author=article.get("author", ""),
                        noise_score=article.get("noise_score", 0),
                        publisher_domain=domain or None,
                        article_score=art_score,
                        publisher_score=pub_score,
                        mbfc_bias=m_bias,
                        mbfc_reporting=m_reporting,
                        mbfc_credibility=m_credibility,
                        mbfc_flags=m_flags,
                    ):
                        new_count += 1

                def finish():
                    self._update_status(f"Fetched {new_count} new articles from {feed['name']}")
                    self.refresh_feeds_list()
                    self.refresh_articles()

                self.root.after(0, finish)
            except Exception as e:
                self.root.after(0, lambda: self._update_status(f"Error fetching {feed['name']}: {e}"))

        thread = threading.Thread(target=fetch_thread, daemon=True)
        thread.start()

    def mark_all_read(self):
        """Mark all visible articles as read."""
        for item in self.articles_tree.get_children():
            self.storage.mark_article_read(int(item))
        self.refresh_feeds_list()
        self.refresh_articles()
        self._update_status("Marked all articles as read")

    def open_in_browser(self):
        """Open selected article in browser."""
        if self.selected_article_id:
            article = self.storage.get_article(self.selected_article_id)
            if article:
                webbrowser.open(article["link"])
                if not article["is_read"]:
                    self.storage.mark_article_read(self.selected_article_id)
                    self.refresh_feeds_list()
                    self.refresh_articles()

    def _clean_author_name(self, author: str) -> Optional[str]:
        """Extract a clean author name from various feed formats."""
        if not author:
            return None

        # Remove email patterns: "name (email)" or "email (name)" or just "email"
        email_paren = re.match(r'^(.*?)\s*\(.*?@.*?\)\s*$', author)
        if email_paren:
            author = email_paren.group(1).strip()

        paren_email = re.match(r'^.*?@.*?\s*\((.*?)\)\s*$', author)
        if paren_email:
            author = paren_email.group(1).strip()

        if '@' in author:
            return None

        # Remove common prefixes
        for prefix in ["By ", "by ", "BY ", "Written by ", "Author: ", "AUTHOR: "]:
            if author.startswith(prefix):
                author = author[len(prefix):]

        # Remove role suffixes after comma: "John Smith, Senior Reporter"
        if ',' in author:
            author = author.split(',')[0].strip()

        # Remove "and" joined multiple authors - just take first
        if ' and ' in author.lower():
            author = re.split(r'\s+and\s+', author, flags=re.IGNORECASE)[0].strip()

        # Skip if too short or doesn't look like a name
        if len(author) < 3 or not author[0].isupper():
            return None

        # Skip if it looks like an organization
        org_keywords = ["staff", "desk", "team", "editorial", "newsroom", "correspondent",
                       "reporter", "editor", "bureau", "agency", "press", "news",
                       "associated", "reuters", "media"]
        if any(kw in author.lower() for kw in org_keywords):
            return None

        return author.strip()

    def _search_author(self, platform: str):
        """Open search for the current article's author."""
        if not self.selected_article_id:
            return

        article = self.storage.get_article(self.selected_article_id)
        if not article or not article.get("author"):
            self._update_status("No author information available")
            return

        author = self._clean_author_name(article["author"])
        if not author:
            self._update_status("Could not extract author name")
            return

        import urllib.parse
        query = urllib.parse.quote(author)

        urls = {
            "google": f"https://www.google.com/search?q={query}",
            "linkedin": f"https://www.linkedin.com/search/results/people/?keywords={query}",
            "wikipedia": f"https://en.wikipedia.org/wiki/Special:Search?search={query}&go=Go",
            "twitter": f"https://twitter.com/search?q={query}&src=typed_query&f=user",
        }

        url = urls.get(platform)
        if url:
            webbrowser.open(url)
            self._update_status(f"Searching {platform} for {author}")

    def search_articles(self):
        """Show search dialog and filter articles."""
        query = simpledialog.askstring("Search", "Search articles:", parent=self.root)
        if query:
            self.search_var.set(query)

    def clear_search(self):
        """Clear search filter."""
        self.search_var.set("")
        self.refresh_articles()

    def show_delete_old_dialog(self):
        """Show dialog to delete old articles."""
        days = simpledialog.askinteger(
            "Delete Old Articles",
            "Delete articles older than how many days?",
            parent=self.root,
            minvalue=1,
            initialvalue=30
        )
        if days:
            count = self.storage.delete_old_articles(days)
            self._update_status(f"Deleted {count} articles older than {days} days")
            self.refresh_feeds_list()
            self.refresh_articles()

    def _auto_cleanup_old_articles(self):
        """Auto-cleanup articles older than 30 days if 48+ hours since last cleanup."""
        last_cleanup = self.storage.get_setting("last_cleanup", "")
        if last_cleanup:
            try:
                last = datetime.fromisoformat(last_cleanup)
                hours_since = (datetime.now() - last).total_seconds() / 3600
                if hours_since < 48:
                    return
            except:
                pass
        count = self.storage.delete_old_articles(30)
        self.storage.set_setting("last_cleanup", datetime.now().isoformat())
        if count > 0:
            self._update_status(f"Auto-cleaned {count} old articles")

    def show_filter_keywords_dialog(self):
        """Show the Filter Keywords dialog."""
        dialog = FilterKeywordsDialog(self.root, self.storage)
        if dialog.changed:
            self.filter_engine = FilterEngine(self.storage.get_filter_keywords())
            self._update_status("Filter keywords updated")

    # ── Event handlers ───────────────────────────────────────────

    def _on_feed_select(self, event):
        """Handle feed selection."""
        selection = self.feeds_tree.selection()
        if not selection:
            return

        item = selection[0]
        if item == "all":
            self.current_feed_id = None
            self.current_category = None
        elif item.startswith("feed_"):
            self.current_feed_id = int(item.replace("feed_", ""))
            self.current_category = None
        elif item.startswith("cat_"):
            # Category header — filter to all feeds in this category
            self.current_feed_id = None
            self.current_category = item[4:]  # strip "cat_" prefix
        else:
            return

        self.refresh_articles()

    def _on_feed_hover(self, event):
        """Apply hover highlight to feed row under cursor."""
        item = self.feeds_tree.identify_row(event.y)
        if item == self._feed_hover_item:
            return
        # Remove hover from previous item
        if self._feed_hover_item:
            try:
                tags = list(self.feeds_tree.item(self._feed_hover_item, "tags") or ())
                if "hover" in tags:
                    tags.remove("hover")
                    self.feeds_tree.item(self._feed_hover_item, tags=tags)
            except tk.TclError:
                pass
        self._feed_hover_item = item
        # Apply hover to new item, skip category dividers
        if item:
            try:
                tags = list(self.feeds_tree.item(item, "tags") or ())
                if "cat_divider" in tags:
                    return
                if "hover" not in tags:
                    tags.append("hover")
                    self.feeds_tree.item(item, tags=tags)
            except tk.TclError:
                pass

    def _on_feed_leave(self, event):
        """Clear hover when mouse leaves feeds tree."""
        if self._feed_hover_item:
            try:
                tags = list(self.feeds_tree.item(self._feed_hover_item, "tags") or ())
                if "hover" in tags:
                    tags.remove("hover")
                    self.feeds_tree.item(self._feed_hover_item, tags=tags)
            except tk.TclError:
                pass
            self._feed_hover_item = None

    def _on_feed_right_click(self, event):
        """Show context menu for feeds or categories."""
        item = self.feeds_tree.identify_row(event.y)
        if not item:
            return

        self.feeds_tree.selection_set(item)

        menu = tk.Menu(self.root, tearoff=0,
                       bg=DARK_THEME["bg_secondary"], fg=DARK_THEME["fg"],
                       activebackground=DARK_THEME["magenta"],
                       activeforeground=DARK_THEME["fg_highlight"])

        if item.startswith("cat_"):
            # Category right-click menu
            category = item[4:]
            menu.add_command(label="Rename Category...",
                             command=lambda: self._rename_category(category))
            menu.add_command(label="Delete Category",
                             command=lambda: self._delete_category(category))
        elif item.startswith("feed_"):
            # Feed right-click menu
            feed_id = int(item.replace("feed_", ""))
            menu.add_command(label="Refresh Feed", command=lambda: self._fetch_single_feed(feed_id))
            menu.add_command(label="Mark Feed Read", command=lambda: self._mark_feed_read(feed_id))
            menu.add_separator()

            # "Move to" submenu
            move_menu = tk.Menu(menu, tearoff=0,
                                bg=DARK_THEME["bg_secondary"], fg=DARK_THEME["fg"],
                                activebackground=DARK_THEME["magenta"],
                                activeforeground=DARK_THEME["fg_highlight"])
            feeds = self.storage.get_feeds()
            categories = sorted(set(f["category"] for f in feeds))
            for cat in categories:
                move_menu.add_command(label=cat,
                                      command=lambda c=cat: self._move_feed_to_category(feed_id, c))
            move_menu.add_separator()
            move_menu.add_command(label="New Category...",
                                  command=lambda: self._move_feed_to_category(feed_id, None))
            menu.add_cascade(label="Move to", menu=move_menu)

            menu.add_separator()
            menu.add_command(label="Remove Feed", command=lambda: self._remove_feed(feed_id))
        else:
            return

        menu.tk_popup(event.x_root, event.y_root)

    def _mark_feed_read(self, feed_id: int):
        """Mark all articles in a feed as read."""
        self.storage.mark_feed_read(feed_id)
        self.refresh_feeds_list()
        self.refresh_articles()
        self._update_status("Marked feed as read")

    def _remove_feed(self, feed_id: int):
        """Remove a feed after confirmation."""
        feed = self.storage.get_feed(feed_id)
        if feed and messagebox.askyesno("Confirm", f"Remove '{feed['name']}'?"):
            self.storage.remove_feed(feed_id)
            self.refresh_feeds_list()
            self.refresh_articles()
            self._update_status(f"Removed feed: {feed['name']}")

    def _rename_category(self, old_name: str):
        """Rename a category, updating all feeds that belong to it."""
        new_name = simpledialog.askstring("Rename Category", f"New name for '{old_name}':",
                                          parent=self.root, initialvalue=old_name)
        if not new_name or new_name == old_name:
            return
        feeds = self.storage.get_feeds()
        for feed in feeds:
            if feed["category"] == old_name:
                self.storage.update_feed_category(feed["id"], new_name)
        if self.current_category == old_name:
            self.current_category = new_name
        self.refresh_feeds_list()
        self.refresh_articles()
        self._update_status(f"Renamed category '{old_name}' to '{new_name}'")

    def _delete_category(self, category: str):
        """Delete a category, moving all its feeds to Uncategorized."""
        if category == "Uncategorized":
            self._update_status("Cannot delete the Uncategorized category")
            return
        if not messagebox.askyesno("Confirm",
                                    f"Delete category '{category}'?\nFeeds will move to Uncategorized."):
            return
        feeds = self.storage.get_feeds()
        for feed in feeds:
            if feed["category"] == category:
                self.storage.update_feed_category(feed["id"], "Uncategorized")
        if self.current_category == category:
            self.current_category = None
        self.refresh_feeds_list()
        self.refresh_articles()
        self._update_status(f"Deleted category '{category}'")

    def _move_feed_to_category(self, feed_id: int, category: str):
        """Move a feed to a different category."""
        if category is None:
            category = simpledialog.askstring("New Category", "Category name:",
                                              parent=self.root)
            if not category:
                return
        self.storage.update_feed_category(feed_id, category)
        self.refresh_feeds_list()
        self.refresh_articles()
        feed = self.storage.get_feed(feed_id)
        name = feed["name"] if feed else "Feed"
        self._update_status(f"Moved '{name}' to '{category}'")

    def _on_article_select(self, event):
        """Handle article selection — show preview."""
        selection = self.articles_tree.selection()
        if not selection:
            return

        article_id = int(selection[0])
        self.selected_article_id = article_id

        article = self.storage.get_article(article_id)
        if not article:
            return

        # Mark as read
        if not article["is_read"]:
            self.storage.mark_article_read(article_id)
            tags = list(self.articles_tree.item(str(article_id), "tags") or ())
            if "unread" in tags:
                tags.remove("unread")
            if "read" not in tags:
                tags.append("read")
            self.articles_tree.item(str(article_id), tags=tuple(tags))
            self.refresh_feeds_list()

        # Update preview
        self.preview_title.configure(text=article["title"])

        self._display_article(article)

    def _on_article_double_click(self, event):
        """Handle double-click on article — open in browser."""
        self.open_in_browser()

    def _on_article_right_click(self, event):
        """Show context menu for articles."""
        item = self.articles_tree.identify_row(event.y)
        if not item:
            return
        self.articles_tree.selection_set(item)
        article_id = int(item)
        article = self.storage.get_article(article_id)
        if not article:
            return

        menu = tk.Menu(self.root, tearoff=0,
                       bg=DARK_THEME["bg_secondary"], fg=DARK_THEME["fg"],
                       activebackground=DARK_THEME["magenta"],
                       activeforeground=DARK_THEME["fg_highlight"])
        is_read = article.get("is_read", False)
        menu.add_command(label="Mark Unread" if is_read else "Mark Read",
                         command=lambda: self._toggle_read(article_id, is_read))
        menu.add_command(label="Hide Article", command=lambda: self._hide_article(article_id))
        menu.add_separator()
        menu.add_command(label="Open in Browser", command=self.open_in_browser)
        menu.tk_popup(event.x_root, event.y_root)

    def _toggle_read(self, article_id: int, is_read: bool):
        self.storage.mark_article_read(article_id, not is_read)
        self.refresh_feeds_list()
        self.refresh_articles()

    def _hide_article(self, article_id: int):
        self.storage.hide_article(article_id)
        self.refresh_articles()
        self._update_status("Article hidden")

    def _set_recency(self, hours: str):
        self.storage.set_setting("recency_hours", hours)
        self.refresh_articles()

    def _set_per_source(self, value: str):
        self.storage.set_setting("max_per_source", value)
        self.refresh_articles()

    def _on_cluster_toggle(self):
        self.storage.set_setting("cluster_topics", str(self._cluster_var.get()))
        self.refresh_articles()

    def _on_search_changed(self, *args):
        self.refresh_articles()

    def _schedule_auto_refresh(self):
        """Schedule auto-refresh every 5 minutes."""
        interval = int(self.storage.get_setting("auto_refresh_minutes", "5")) * 60 * 1000
        if interval > 0:
            self.auto_refresh_job = self.root.after(interval, self._auto_refresh)

    def _auto_refresh(self):
        """Auto-refresh feeds."""
        if not self.is_fetching:
            self.fetch_all_feeds()
        self._schedule_auto_refresh()

    # ── Keyboard handlers ────────────────────────────────────────

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
                # Update just this row's tag, preserving favorite
                item_id = str(self.selected_article_id)
                tags = list(self.articles_tree.item(item_id, "tags") or ())
                for t in ("read", "unread"):
                    if t in tags:
                        tags.remove(t)
                tags.append("read" if new_status else "unread")
                self.articles_tree.item(item_id, tags=tuple(tags))
                self._update_status(f"Marked {'read' if new_status else 'unread'}")
        return "break"

    def _on_key_hide(self, event):
        """Handle H key - hide current article."""
        if self.selected_article_id:
            self._hide_article(self.selected_article_id)
        return "break"

    def _on_article_click(self, event):
        """Handle click on articles tree — detect fav or score column click."""
        region = self.articles_tree.identify_region(event.x, event.y)
        if region != "cell":
            return
        col = self.articles_tree.identify_column(event.x)
        item = self.articles_tree.identify_row(event.y)
        if not item:
            return
        article_id = int(item)
        if col == "#1":  # fav column
            self._toggle_favorite(article_id)
            return "break"
        if col == "#6":  # score column
            self._on_score_click(article_id)
            return "break"

    def _on_score_click(self, article_id: int):
        """Show score breakdown in status bar and open detail dialog."""
        article = self.storage.get_article(article_id)
        if not article:
            return
        self._score_click_article_id = article_id
        self._show_score_status(article)
        mbfc_source = mbfc.lookup_source(article.get("link", ""))
        cleaned_author = self._clean_author_name(article.get("author", ""))
        CredibilityDetailDialog(self.root, article, mbfc_source,
                                storage=self.storage,
                                cleaned_author=cleaned_author)

    def _show_score_status(self, article: dict):
        """Display score breakdown in status bar for an article."""
        noise = article.get("noise_score", 0)
        letter, label, color = get_grade(noise)
        mbfc_source = mbfc.lookup_source(article.get("link", ""))

        # Check for anomaly
        domain = article.get("publisher_domain", "")
        pub_trend = self.storage.get_publisher_trend_data(domain) if domain else None
        anomaly_suffix = " \u26a0 ANOMALY" if Storage.is_anomaly(noise, pub_trend) else ""

        if mbfc_source:
            pub_score = mbfc.publisher_score(mbfc_source)
            if pub_score is not None:
                wrfdr_contrib = 0.6 * round((noise - 0.4 * pub_score) / 0.6)
                mbfc_contrib = 0.4 * pub_score
                total = wrfdr_contrib + mbfc_contrib
                if total > 0:
                    wrfdr_pct = round(wrfdr_contrib / total * 100)
                    mbfc_pct = 100 - wrfdr_pct
                else:
                    wrfdr_pct, mbfc_pct = 60, 40
                self._update_status(
                    f"SCORE {noise} {label.upper()} \u2014 "
                    f"WRFDR: {wrfdr_pct}%, MBFC: {mbfc_pct}%{anomaly_suffix}"
                )
                return
        self._update_status(
            f"SCORE {noise} {label.upper()} \u2014 WRFDR: 100%{anomaly_suffix}"
        )

    def _on_key_toggle_favorite(self, event):
        """Handle F key - toggle favorite on selected article."""
        if self.selected_article_id:
            self._toggle_favorite(self.selected_article_id)
        return "break"

    def _toggle_favorite(self, article_id: int):
        """Toggle favorite status for an article."""
        article = self.storage.get_article(article_id)
        if not article:
            return
        new_status = not article.get("is_favorite", False)
        self.storage.mark_article_favorite(article_id, new_status)

        # Update row in-place
        item_id = str(article_id)
        if self.articles_tree.exists(item_id):
            values = list(self.articles_tree.item(item_id, "values"))
            values[0] = "\u25c6" if new_status else "\u25c7"
            tags = list(self.articles_tree.item(item_id, "tags") or ())
            if new_status and "favorite" not in tags:
                tags.append("favorite")
            elif not new_status and "favorite" in tags:
                tags.remove("favorite")
            self.articles_tree.item(item_id, values=values, tags=tuple(tags))

        # Update favorites tab count
        fav_count = len(self.storage.get_articles(favorites_only=True, limit=9999))
        self._tab_fav.configure(text=f"FAVORITES ({fav_count})")

        # If on favorites tab and unfavorited, remove the row
        if self._articles_tab == "favorites" and not new_status:
            self.articles_tree.delete(item_id)

        self._update_status(f"{'Favorited' if new_status else 'Unfavorited'}")

    # ── Window close ────────────────────────────────────────────

    def _on_close(self):
        """Handle window close with CRT shutdown animation."""
        if self._shutdown_active:
            return
        self._shutdown_active = True
        animations.stop_animation_loop(self)
        animations.play_crt_shutdown(self)


if __name__ == "__main__":
    from dialogs import signal_existing_instance_to_close, start_instance_listener
    signal_existing_instance_to_close()
    root = tk.Tk()
    start_instance_listener(root)
    app = NewsAggregatorApp(root)
    app._owner.mainloop()
