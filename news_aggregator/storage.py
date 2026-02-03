# storage.py - SQLite database operations

import sqlite3
import os
from datetime import datetime, timedelta
from typing import Optional
from config import DATABASE_NAME, DATA_FOLDER, DEFAULT_FEEDS, DEFAULT_SETTINGS


class Storage:
    def __init__(self, db_path: Optional[str] = None):
        if db_path is None:
            # Create data folder if it doesn't exist
            base_dir = os.path.dirname(os.path.abspath(__file__))
            data_dir = os.path.join(base_dir, DATA_FOLDER)
            os.makedirs(data_dir, exist_ok=True)
            db_path = os.path.join(data_dir, DATABASE_NAME)

        self.db_path = db_path
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self._init_db()

    def _init_db(self):
        """Initialize database tables."""
        cursor = self.conn.cursor()

        # Feeds table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS feeds (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                url TEXT UNIQUE NOT NULL,
                category TEXT DEFAULT 'Uncategorized',
                bias TEXT DEFAULT 'Unknown',
                factual TEXT DEFAULT 'Unknown',
                author_url_pattern TEXT,
                enabled INTEGER DEFAULT 1,
                last_fetched TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Migration: Add new columns to existing databases
        self._migrate_feeds_table(cursor)

        # Articles table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS articles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                feed_id INTEGER NOT NULL,
                title TEXT NOT NULL,
                link TEXT UNIQUE NOT NULL,
                summary TEXT,
                published TIMESTAMP,
                author TEXT,
                noise_score INTEGER DEFAULT 0,
                is_read INTEGER DEFAULT 0,
                is_hidden INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (feed_id) REFERENCES feeds(id) ON DELETE CASCADE
            )
        """)

        # Custom filter keywords table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS filter_keywords (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                keyword TEXT UNIQUE NOT NULL,
                weight INTEGER DEFAULT 10,
                is_active INTEGER DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Settings table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            )
        """)

        # Migration: Add new columns to existing articles table
        self._migrate_articles_table(cursor)

        # Create indexes for performance
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_articles_feed_id ON articles(feed_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_articles_published ON articles(published DESC)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_articles_noise_score ON articles(noise_score)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_articles_is_read ON articles(is_read)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_articles_publisher_domain ON articles(publisher_domain)")

        self.conn.commit()

        # Initialize default settings if empty
        self._init_default_settings()

        # Initialize default feeds if empty
        self._init_default_feeds()

    def _migrate_articles_table(self, cursor):
        """Add new columns to existing articles table if they don't exist."""
        cursor.execute("PRAGMA table_info(articles)")
        existing_columns = {row[1] for row in cursor.fetchall()}

        if "is_favorite" not in existing_columns:
            cursor.execute("ALTER TABLE articles ADD COLUMN is_favorite INTEGER DEFAULT 0")

        # Per-article credibility logging columns
        for col, typedef in [
            ("publisher_domain", "TEXT"),
            ("article_score", "INTEGER"),
            ("publisher_score", "INTEGER"),
            ("mbfc_bias", "TEXT"),
            ("mbfc_reporting", "TEXT"),
            ("mbfc_credibility", "TEXT"),
            ("mbfc_flags", "TEXT"),
        ]:
            if col not in existing_columns:
                cursor.execute(f"ALTER TABLE articles ADD COLUMN {col} {typedef}")

    def _migrate_feeds_table(self, cursor):
        """Add new columns to existing feeds table if they don't exist."""
        # Get existing columns
        cursor.execute("PRAGMA table_info(feeds)")
        existing_columns = {row[1] for row in cursor.fetchall()}

        # Add missing columns
        if "bias" not in existing_columns:
            cursor.execute("ALTER TABLE feeds ADD COLUMN bias TEXT DEFAULT 'Unknown'")
        if "factual" not in existing_columns:
            cursor.execute("ALTER TABLE feeds ADD COLUMN factual TEXT DEFAULT 'Unknown'")
        if "author_url_pattern" not in existing_columns:
            cursor.execute("ALTER TABLE feeds ADD COLUMN author_url_pattern TEXT")
        if "favicon" not in existing_columns:
            cursor.execute("ALTER TABLE feeds ADD COLUMN favicon BLOB")

        # Populate 'Unknown' bias/factual values from DEFAULT_FEEDS
        feed_lookup = {f["name"]: f for f in DEFAULT_FEEDS}
        cursor.execute("SELECT id, name FROM feeds WHERE bias = 'Unknown' OR factual = 'Unknown'")
        for row in cursor.fetchall():
            feed_id, name = row
            if name in feed_lookup:
                data = feed_lookup[name]
                cursor.execute(
                    "UPDATE feeds SET bias = ?, factual = ?, author_url_pattern = ? WHERE id = ?",
                    (data.get("bias", "Unknown"), data.get("factual", "Unknown"),
                     data.get("author_url_pattern"), feed_id)
                )

        # Fix AP/Reuters feed URLs (migrate from broken direct URLs to Google News proxy)
        ap_reuters_fixes = {
            "Associated Press": "https://news.google.com/rss/search?q=when:24h+allinurl:apnews.com&ceid=US:en&hl=en-US&gl=US",
            "Reuters World": "https://news.google.com/rss/search?q=when:24h+allinurl:reuters.com&ceid=US:en&hl=en-US&gl=US",
        }
        for feed_name, correct_url in ap_reuters_fixes.items():
            cursor.execute(
                "UPDATE feeds SET url = ? WHERE name = ? AND url NOT LIKE '%news.google.com%'",
                (correct_url, feed_name)
            )

    def _init_default_settings(self):
        """Initialize default settings if not present."""
        cursor = self.conn.cursor()
        for key, value in DEFAULT_SETTINGS.items():
            cursor.execute(
                "INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)",
                (key, str(value))
            )
        self.conn.commit()

    def _init_default_feeds(self):
        """Add default feeds if the feeds table is empty."""
        cursor = self.conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM feeds")
        count = cursor.fetchone()[0]

        if count == 0:
            for feed in DEFAULT_FEEDS:
                self.add_feed(
                    name=feed["name"],
                    url=feed["url"],
                    category=feed.get("category", "Uncategorized"),
                    bias=feed.get("bias", "Unknown"),
                    factual=feed.get("factual", "Unknown"),
                    author_url_pattern=feed.get("author_url_pattern")
                )

    # Feed operations
    def add_feed(self, name: str, url: str, category: str = "Uncategorized",
                 bias: str = "Unknown", factual: str = "Unknown",
                 author_url_pattern: str = None) -> Optional[int]:
        """Add a new feed. Returns feed ID or None if already exists."""
        try:
            cursor = self.conn.cursor()
            cursor.execute(
                """INSERT INTO feeds (name, url, category, bias, factual, author_url_pattern)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (name, url, category, bias, factual, author_url_pattern)
            )
            self.conn.commit()
            return cursor.lastrowid
        except sqlite3.IntegrityError:
            return None

    def remove_feed(self, feed_id: int):
        """Remove a feed and all its articles."""
        cursor = self.conn.cursor()
        cursor.execute("DELETE FROM articles WHERE feed_id = ?", (feed_id,))
        cursor.execute("DELETE FROM feeds WHERE id = ?", (feed_id,))
        self.conn.commit()

    def get_feeds(self, enabled_only: bool = True) -> list:
        """Get all feeds."""
        cursor = self.conn.cursor()
        if enabled_only:
            cursor.execute("SELECT * FROM feeds WHERE enabled = 1 ORDER BY category, name")
        else:
            cursor.execute("SELECT * FROM feeds ORDER BY category, name")
        return [dict(row) for row in cursor.fetchall()]

    def get_feed(self, feed_id: int) -> Optional[dict]:
        """Get a single feed by ID."""
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM feeds WHERE id = ?", (feed_id,))
        row = cursor.fetchone()
        return dict(row) if row else None

    def toggle_feed(self, feed_id: int, enabled: bool):
        """Enable or disable a feed."""
        cursor = self.conn.cursor()
        cursor.execute(
            "UPDATE feeds SET enabled = ? WHERE id = ?",
            (1 if enabled else 0, feed_id)
        )
        self.conn.commit()

    def update_feed_fetched(self, feed_id: int):
        """Update the last_fetched timestamp for a feed."""
        cursor = self.conn.cursor()
        cursor.execute(
            "UPDATE feeds SET last_fetched = ? WHERE id = ?",
            (datetime.now().isoformat(), feed_id)
        )
        self.conn.commit()

    def set_feed_favicon(self, feed_id: int, favicon_data: bytes):
        """Store favicon data for a feed."""
        cursor = self.conn.cursor()
        cursor.execute(
            "UPDATE feeds SET favicon = ? WHERE id = ?",
            (favicon_data, feed_id)
        )
        self.conn.commit()

    def get_feed_favicon(self, feed_id: int) -> Optional[bytes]:
        """Get favicon data for a feed."""
        cursor = self.conn.cursor()
        cursor.execute("SELECT favicon FROM feeds WHERE id = ?", (feed_id,))
        row = cursor.fetchone()
        return row[0] if row and row[0] else None

    # Article operations
    def add_article(self, feed_id: int, title: str, link: str, summary: str = "",
                    published: str = None, author: str = "", noise_score: int = 0,
                    publisher_domain: str = None, article_score: int = None,
                    publisher_score: int = None, mbfc_bias: str = None,
                    mbfc_reporting: str = None, mbfc_credibility: str = None,
                    mbfc_flags: str = None) -> Optional[int]:
        """Add an article. Returns article ID or None if already exists."""
        try:
            cursor = self.conn.cursor()
            cursor.execute("""
                INSERT INTO articles (feed_id, title, link, summary, published, author, noise_score,
                    publisher_domain, article_score, publisher_score,
                    mbfc_bias, mbfc_reporting, mbfc_credibility, mbfc_flags)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (feed_id, title, link, summary, published, author, noise_score,
                  publisher_domain, article_score, publisher_score,
                  mbfc_bias, mbfc_reporting, mbfc_credibility, mbfc_flags))
            self.conn.commit()
            return cursor.lastrowid
        except sqlite3.IntegrityError:
            # Article already exists, update scores and credibility data
            cursor.execute("""
                UPDATE articles SET noise_score = ?, publisher_domain = ?,
                    article_score = ?, publisher_score = ?,
                    mbfc_bias = ?, mbfc_reporting = ?, mbfc_credibility = ?, mbfc_flags = ?
                WHERE link = ?
            """, (noise_score, publisher_domain, article_score, publisher_score,
                  mbfc_bias, mbfc_reporting, mbfc_credibility, mbfc_flags, link))
            self.conn.commit()
            return None

    def get_articles(self, feed_id: Optional[int] = None, feed_ids: list = None,
                     include_read: bool = True, favorites_only: bool = False,
                     min_score: int = 0, recency_hours: int = 0, max_per_source: int = 0,
                     limit: int = 500) -> list:
        """Get articles with optional filters.

        Args:
            feed_id: Filter to specific feed (None = all feeds)
            feed_ids: Filter to multiple feeds (overrides feed_id if set)
            include_read: Include read articles
            favorites_only: Only return favorited articles
            min_score: Minimum objectivity score
            recency_hours: Only show articles from last N hours (0 = no limit)
            max_per_source: Max articles per feed, ranked by quality (0 = no limit)
            limit: Maximum number of articles to return
        """
        cursor = self.conn.cursor()

        query = """
            SELECT a.*, f.name as feed_name, f.category, f.bias, f.factual, f.author_url_pattern
            FROM articles a
            JOIN feeds f ON a.feed_id = f.id
            WHERE a.noise_score >= ? AND a.is_hidden = 0
        """
        params = [min_score]

        if feed_ids:
            placeholders = ",".join("?" * len(feed_ids))
            query += f" AND a.feed_id IN ({placeholders})"
            params.extend(feed_ids)
        elif feed_id is not None:
            query += " AND a.feed_id = ?"
            params.append(feed_id)

        if not include_read:
            query += " AND a.is_read = 0"

        if favorites_only:
            query += " AND a.is_favorite = 1"

        if recency_hours > 0:
            cutoff = (datetime.now() - timedelta(hours=recency_hours)).isoformat()
            query += " AND a.published >= ?"
            params.append(cutoff)

        query += " ORDER BY a.published DESC LIMIT ?"
        params.append(limit)

        cursor.execute(query, params)
        articles = [dict(row) for row in cursor.fetchall()]

        # Apply per-source cap if specified (when showing multiple feeds)
        if max_per_source > 0 and feed_id is None:
            articles = self._apply_per_source_cap(articles, max_per_source)

        return articles

    def _apply_per_source_cap(self, articles: list, max_per_source: int) -> list:
        """Limit articles per feed, keeping highest quality ones.

        Groups articles by feed, sorts each group by quality (noise_score descending),
        takes top N from each, then re-sorts by published date.
        """
        from collections import defaultdict

        # Group by feed
        by_feed = defaultdict(list)
        for article in articles:
            by_feed[article["feed_id"]].append(article)

        # Take top N per feed (sorted by quality score, highest first)
        result = []
        for feed_id, feed_articles in by_feed.items():
            # Sort by noise_score descending (higher = better quality)
            sorted_articles = sorted(feed_articles, key=lambda a: a["noise_score"], reverse=True)
            result.extend(sorted_articles[:max_per_source])

        # Re-sort by published date descending
        result.sort(key=lambda a: a["published"] or "", reverse=True)

        return result

    def get_article(self, article_id: int) -> Optional[dict]:
        """Get a single article by ID."""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT a.*, f.name as feed_name, f.category, f.bias, f.factual, f.author_url_pattern
            FROM articles a
            JOIN feeds f ON a.feed_id = f.id
            WHERE a.id = ?
        """, (article_id,))
        row = cursor.fetchone()
        return dict(row) if row else None

    def mark_article_read(self, article_id: int, is_read: bool = True):
        """Mark an article as read or unread."""
        cursor = self.conn.cursor()
        cursor.execute(
            "UPDATE articles SET is_read = ? WHERE id = ?",
            (1 if is_read else 0, article_id)
        )
        self.conn.commit()

    def mark_article_favorite(self, article_id: int, is_favorite: bool = True):
        """Mark an article as favorite or unfavorite."""
        cursor = self.conn.cursor()
        cursor.execute(
            "UPDATE articles SET is_favorite = ? WHERE id = ?",
            (1 if is_favorite else 0, article_id)
        )
        self.conn.commit()

    def mark_all_read(self, feed_id: Optional[int] = None):
        """Mark all articles as read, optionally for a specific feed."""
        cursor = self.conn.cursor()
        if feed_id is not None:
            cursor.execute("UPDATE articles SET is_read = 1 WHERE feed_id = ?", (feed_id,))
        else:
            cursor.execute("UPDATE articles SET is_read = 1")
        self.conn.commit()

    def hide_article(self, article_id: int, is_hidden: bool = True):
        """Hide or unhide an article."""
        cursor = self.conn.cursor()
        cursor.execute(
            "UPDATE articles SET is_hidden = ? WHERE id = ?",
            (1 if is_hidden else 0, article_id)
        )
        self.conn.commit()

    def search_articles(self, query: str, min_score: int = 0, limit: int = 100) -> list:
        """Search articles by title or summary."""
        cursor = self.conn.cursor()
        search_term = f"%{query}%"
        cursor.execute("""
            SELECT a.*, f.name as feed_name, f.category, f.bias, f.factual, f.author_url_pattern
            FROM articles a
            JOIN feeds f ON a.feed_id = f.id
            WHERE (a.title LIKE ? OR a.summary LIKE ?)
            AND a.noise_score >= ? AND a.is_hidden = 0
            ORDER BY a.published DESC LIMIT ?
        """, (search_term, search_term, min_score, limit))
        return [dict(row) for row in cursor.fetchall()]

    def delete_old_articles(self, days: int = 7):
        """Delete articles older than specified days (preserves favorites)."""
        cursor = self.conn.cursor()
        cutoff = (datetime.now() - timedelta(days=days)).isoformat()
        cursor.execute("DELETE FROM articles WHERE created_at < ? AND is_favorite = 0", (cutoff,))
        self.conn.commit()
        return cursor.rowcount

    def delete_all_articles(self):
        """Delete all stored articles (preserves favorites)."""
        cursor = self.conn.cursor()
        cursor.execute("DELETE FROM articles WHERE is_favorite = 0")
        self.conn.commit()
        return cursor.rowcount

    def get_article_count(self, feed_id: Optional[int] = None, unread_only: bool = False) -> int:
        """Get article count, optionally for a specific feed."""
        cursor = self.conn.cursor()
        query = "SELECT COUNT(*) FROM articles WHERE is_hidden = 0"
        params = []

        if feed_id is not None:
            query += " AND feed_id = ?"
            params.append(feed_id)

        if unread_only:
            query += " AND is_read = 0"

        cursor.execute(query, params)
        return cursor.fetchone()[0]

    # Filter keyword operations
    def add_filter_keyword(self, keyword: str, weight: int = 10) -> Optional[int]:
        """Add a custom filter keyword."""
        try:
            cursor = self.conn.cursor()
            cursor.execute(
                "INSERT INTO filter_keywords (keyword, weight) VALUES (?, ?)",
                (keyword.lower(), weight)
            )
            self.conn.commit()
            return cursor.lastrowid
        except sqlite3.IntegrityError:
            return None

    def remove_filter_keyword(self, keyword_id: int):
        """Remove a custom filter keyword."""
        cursor = self.conn.cursor()
        cursor.execute("DELETE FROM filter_keywords WHERE id = ?", (keyword_id,))
        self.conn.commit()

    def get_filter_keywords(self, active_only: bool = True) -> list:
        """Get all custom filter keywords."""
        cursor = self.conn.cursor()
        if active_only:
            cursor.execute("SELECT * FROM filter_keywords WHERE is_active = 1")
        else:
            cursor.execute("SELECT * FROM filter_keywords")
        return [dict(row) for row in cursor.fetchall()]

    # Settings operations
    def get_setting(self, key: str, default: str = None) -> str:
        """Get a setting value."""
        cursor = self.conn.cursor()
        cursor.execute("SELECT value FROM settings WHERE key = ?", (key,))
        row = cursor.fetchone()
        return row[0] if row else default

    def set_setting(self, key: str, value: str):
        """Set a setting value."""
        cursor = self.conn.cursor()
        cursor.execute(
            "INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)",
            (key, str(value))
        )
        self.conn.commit()

    def get_all_settings(self) -> dict:
        """Get all settings as a dictionary."""
        cursor = self.conn.cursor()
        cursor.execute("SELECT key, value FROM settings")
        return {row[0]: row[1] for row in cursor.fetchall()}

    def update_feed_category(self, feed_id: int, category: str):
        """Update the category for a feed."""
        cursor = self.conn.cursor()
        cursor.execute(
            "UPDATE feeds SET category = ? WHERE id = ?",
            (category, feed_id)
        )
        self.conn.commit()

    def close(self):
        """Close the database connection."""
        self.conn.close()
