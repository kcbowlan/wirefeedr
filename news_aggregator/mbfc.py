"""MBFC (Media Bias/Fact Check) data loader and query module.

Loads the local mbfc_sources.json built by fetch_mbfc.py and provides
domain normalization and source lookup for article URLs.
"""

import json
import os
import re
from urllib.parse import urlparse, parse_qs

# Module-level cache
_mbfc_data = None
_sources = {}
_aliases = {}

DATA_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "mbfc_sources.json")

# MBFC bias strings → Wirefeedr display values
BIAS_MAP = {
    "left": "Left",
    "left-center": "Left-Center",
    "center": "Center",
    "right-center": "Right-Center",
    "right": "Right",
    "pro-science": "Center",
    "conspiracy-pseudoscience": "Right",
    "satire": "Center",
    "fake-news": "Center",
}

# MBFC reporting strings → Wirefeedr display values
REPORTING_MAP = {
    "very-high": "Very High",
    "high": "High",
    "mostly-factual": "Mostly Factual",
    "mixed": "Mixed",
    "low": "Mixed",
    "very-low": "Mixed",
}

# Common subdomains to strip when normalizing
_STRIP_SUBDOMAINS = {
    "www", "feeds", "rss", "feed", "news", "m", "mobile",
    "amp", "api", "static", "cdn", "media",
}


def load_mbfc_data(path=None):
    """Load mbfc_sources.json into module-level cache. Returns source count or 0 on failure."""
    global _mbfc_data, _sources, _aliases

    path = path or DATA_PATH
    if not os.path.exists(path):
        print(f"[MBFC] Data file not found: {path}")
        print("[MBFC] Run fetch_mbfc.py to download MBFC data.")
        return 0

    with open(path, "r", encoding="utf-8") as f:
        _mbfc_data = json.load(f)

    _sources = _mbfc_data.get("sources", {})
    _aliases = _mbfc_data.get("aliases", {})

    count = len(_sources)
    print(f"[MBFC] Loaded {count} sources, {len(_aliases)} aliases")
    return count


def normalize_domain(url):
    """Extract bare publisher domain from any URL.

    Handles:
    - Standard URLs (https://www.apnews.com/article/...) → apnews.com
    - Feed subdomains (feeds.npr.org) → npr.org
    - Google News proxy URLs (allinurl:apnews.com in query) → apnews.com
    - Regional/alias variants via alias map
    """
    if not url:
        return ""

    # Google News proxy: extract real domain from the allinurl: parameter
    if "news.google.com" in url:
        domain = _extract_google_news_domain(url)
        if domain:
            return _resolve_alias(domain)

    # Standard URL parsing
    try:
        parsed = urlparse(url if "://" in url else f"https://{url}")
        hostname = (parsed.hostname or "").lower().strip(".")
    except Exception:
        return ""

    if not hostname:
        return ""

    # Strip common subdomains
    domain = _strip_subdomains(hostname)
    return _resolve_alias(domain)


def lookup_source(url):
    """Look up MBFC data for a URL. Returns source dict or None."""
    if not _sources:
        return None

    domain = normalize_domain(url)
    if not domain:
        return None

    # Direct match
    if domain in _sources:
        return _sources[domain]

    # Try alias resolution (already done in normalize_domain, but check again)
    aliased = _aliases.get(domain, "")
    if aliased and aliased in _sources:
        return _sources[aliased]

    # Try progressively stripping subdomains
    # e.g. "special.edition.bbc.com" → "edition.bbc.com" → "bbc.com"
    parts = domain.split(".")
    while len(parts) > 2:
        parts.pop(0)
        candidate = ".".join(parts)
        if candidate in _sources:
            return _sources[candidate]
        aliased = _aliases.get(candidate, "")
        if aliased and aliased in _sources:
            return _sources[aliased]

    return None


def map_bias_to_wirefeedr(mbfc_bias):
    """Convert MBFC bias string to Wirefeedr display value."""
    if not mbfc_bias:
        return ""
    return BIAS_MAP.get(mbfc_bias.lower().strip(), "")


def map_reporting_to_wirefeedr(mbfc_reporting):
    """Convert MBFC reporting string to Wirefeedr factual display value."""
    if not mbfc_reporting:
        return ""
    return REPORTING_MAP.get(mbfc_reporting.lower().strip(), "")


def _extract_google_news_domain(url):
    """Extract the real publisher domain from a Google News RSS URL.

    Google News feed URLs look like:
      https://news.google.com/rss/search?q=when:24h+allinurl:apnews.com&...
    Article links from Google News look like:
      https://news.google.com/rss/articles/... (these redirect, use link domain instead)
    """
    try:
        parsed = urlparse(url)
        query = parsed.query or ""

        # Check for allinurl: in the q parameter
        qs = parse_qs(query)
        q_value = " ".join(qs.get("q", []))
        match = re.search(r"allinurl:(\S+)", q_value)
        if match:
            raw = match.group(1).lower().strip(".")
            # The value might be just a domain like "apnews.com"
            return _strip_subdomains(raw)
    except Exception:
        pass

    return ""


def _strip_subdomains(hostname):
    """Strip common subdomains from a hostname.

    feeds.npr.org → npr.org
    www.bbc.com → bbc.com
    """
    parts = hostname.split(".")
    if len(parts) <= 2:
        return hostname

    # Strip known generic subdomains from the front
    while len(parts) > 2 and parts[0] in _STRIP_SUBDOMAINS:
        parts.pop(0)

    return ".".join(parts)


def publisher_score(source):
    """Derive a 0-100 publisher reputation score from MBFC data.

    Scoring:
    - Base from reporting level (very-high=95 down to very-low=10)
    - Credibility modifier: high=+5, medium=0, low=-10
    - Questionable flags: -5 each (capped at -20)
    - Returns None if source is missing or has no reporting data.
    """
    if not source:
        return None

    reporting = (source.get("reporting") or "").lower().strip()
    if not reporting:
        return None

    base_scores = {
        "very-high": 95,
        "high": 80,
        "mostly-factual": 65,
        "mixed": 45,
        "low": 25,
        "very-low": 10,
    }
    base = base_scores.get(reporting)
    if base is None:
        return None

    # Credibility modifier
    credibility = (source.get("credibility") or "").lower().strip()
    cred_mod = {"high-credibility": 5, "medium-credibility": 0, "low-credibility": -10}
    base += cred_mod.get(credibility, 0)

    # Questionable flags penalty
    flags = source.get("questionable") or []
    if flags:
        penalty = min(len(flags) * 5, 20)
        base -= penalty

    return max(0, min(100, base))


def composite_score(article_score, source=None):
    """Blend publisher reputation (40%) with per-article analysis (60%).

    Returns article_score unchanged when no MBFC publisher score is available.
    """
    pub = publisher_score(source)
    if pub is None:
        return article_score
    return round(0.4 * pub + 0.6 * article_score)


def _resolve_alias(domain):
    """Resolve domain through alias map."""
    return _aliases.get(domain, domain)
