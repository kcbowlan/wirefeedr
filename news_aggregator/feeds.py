# feeds.py - RSS feed fetching and parsing

import feedparser
import requests
from datetime import datetime
from typing import Optional
from time import mktime
import html
import re


class FeedManager:
    def __init__(self, timeout: int = 30):
        self.timeout = timeout
        self.user_agent = "NewsAggregator/1.0 (Personal News Reader)"

    def fetch_feed(self, url: str) -> dict:
        """
        Fetch and parse an RSS feed.

        Returns a dict with:
            - success: bool
            - feed_title: str (if successful)
            - articles: list of article dicts (if successful)
            - error: str (if failed)
        """
        try:
            # Use requests to fetch with custom headers
            headers = {"User-Agent": self.user_agent}
            response = requests.get(url, headers=headers, timeout=self.timeout)
            response.raise_for_status()

            # Parse the feed content
            feed = feedparser.parse(response.content)

            if feed.bozo and not feed.entries:
                # Feed parsing error with no entries
                return {
                    "success": False,
                    "error": f"Feed parsing error: {feed.bozo_exception}"
                }

            articles = []
            for entry in feed.entries:
                article = self._parse_entry(entry)
                if article:
                    articles.append(article)

            return {
                "success": True,
                "feed_title": feed.feed.get("title", "Unknown Feed"),
                "articles": articles
            }

        except requests.exceptions.Timeout:
            return {"success": False, "error": "Request timed out"}
        except requests.exceptions.ConnectionError:
            return {"success": False, "error": "Connection failed"}
        except requests.exceptions.HTTPError as e:
            return {"success": False, "error": f"HTTP error: {e.response.status_code}"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _parse_entry(self, entry) -> Optional[dict]:
        """Parse a single feed entry into an article dict."""
        # Title is required
        title = entry.get("title", "").strip()
        if not title:
            return None

        # Link is required
        link = entry.get("link", "").strip()
        if not link:
            return None

        # Clean HTML from title
        title = self._clean_html(title)

        # Get summary/description
        summary = ""
        if "summary" in entry:
            summary = entry.summary
        elif "description" in entry:
            summary = entry.description
        elif "content" in entry and entry.content:
            summary = entry.content[0].get("value", "")

        summary = self._clean_html(summary)
        # Truncate long summaries
        if len(summary) > 1000:
            summary = summary[:1000] + "..."

        # Parse published date
        published = None
        if "published_parsed" in entry and entry.published_parsed:
            try:
                published = datetime.fromtimestamp(mktime(entry.published_parsed))
            except (ValueError, OverflowError):
                pass
        elif "updated_parsed" in entry and entry.updated_parsed:
            try:
                published = datetime.fromtimestamp(mktime(entry.updated_parsed))
            except (ValueError, OverflowError):
                pass

        if published is None:
            published = datetime.now()

        # Get author
        author = entry.get("author", "")
        if not author and "authors" in entry and entry.authors:
            author = entry.authors[0].get("name", "")

        return {
            "title": title,
            "link": link,
            "summary": summary,
            "published": published.isoformat(),
            "author": author
        }

    def _clean_html(self, text: str) -> str:
        """Remove HTML tags and decode entities from text."""
        if not text:
            return ""

        # Decode HTML entities
        text = html.unescape(text)

        # Remove HTML tags
        text = re.sub(r"<[^>]+>", " ", text)

        # Normalize whitespace
        text = re.sub(r"\s+", " ", text).strip()

        return text

    def validate_feed_url(self, url: str) -> dict:
        """
        Validate that a URL is a valid RSS/Atom feed.

        Returns:
            - valid: bool
            - feed_title: str (if valid)
            - article_count: int (if valid)
            - error: str (if invalid)
        """
        result = self.fetch_feed(url)

        if result["success"]:
            return {
                "valid": True,
                "feed_title": result["feed_title"],
                "article_count": len(result["articles"])
            }
        else:
            return {
                "valid": False,
                "error": result["error"]
            }
