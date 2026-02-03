# config.py - Default settings and sources

# Dark mode color palette (cyberpunk aesthetic) - NEON OVERDRIVE
DARK_THEME = {
    # Backgrounds - deep void black for maximum neon contrast
    "bg": "#020206",               # Void black (deeper)
    "bg_secondary": "#06060c",     # Panel backgrounds (darker)
    "bg_tertiary": "#0a0a14",      # Lists, inputs
    "bg_toolbar": "#08080f",       # Toolbar background

    # Text
    "fg": "#f0f0f0",               # Primary text (brighter white)
    "fg_secondary": "#7080a0",     # Muted text (slightly bluer)
    "fg_highlight": "#ffffff",     # Highlighted text

    # Neon accents - MAXIMUM SATURATION
    "cyan": "#00ffff",             # Pure neon cyan
    "cyan_bright": "#40ffff",      # Brighter cyan (for highlights)
    "cyan_dim": "#006666",         # Dim cyan (for animation low point)
    "magenta": "#ff00ff",          # Pure neon magenta
    "magenta_bright": "#ff40ff",   # Brighter magenta
    "magenta_dim": "#660066",      # Dim magenta (for animation low point)
    "pink": "#ff1493",             # Hot pink
    "neon_green": "#39ff14",       # Electric green
    "neon_orange": "#ff6600",      # Neon orange
    "neon_yellow": "#ffff00",      # Electric yellow
    "neon_purple": "#bf00ff",      # Neon purple
    "neon_red": "#ff073a",         # Neon red

    # Functional colors
    "accent": "#00ffff",           # Primary accent (cyan)
    "accent_secondary": "#ff00ff", # Secondary accent (magenta)
    "border": "#00ffff",           # Default border (cyan)
    "hover": "#ff00ff",            # Hover state (magenta!)
    "selected": "#ff00ff",         # Selected row (magenta)
    "selected_fg": "#ffffff",      # Selected text (white on magenta)

    # Component specific
    "heading_cyan": "#00ffff",     # Cyan headings
    "heading_magenta": "#ff00ff",  # Magenta headings
    "button_hover": "#ff00ff",     # Button hover (magenta)
    "status_bg": "#04040a",        # Status bar background (darker)

    # Row striping
    "row_even": "#0c0c16",         # Even rows
    "row_odd": "#06060c",          # Odd rows (base)
}

# Bias ratings: Center, Lean Left, Lean Right, Left, Right, Left-Center, Right-Center
# Factual ratings: Very High, High, Mostly Factual, Mixed
# Source: Media Bias/Fact Check (mediabiasfactcheck.com)

# Default RSS feeds from factual news organizations
DEFAULT_FEEDS = [
    {
        "name": "Associated Press",
        "url": "https://news.google.com/rss/search?q=when:24h+allinurl:apnews.com&ceid=US:en&hl=en-US&gl=US",
        "category": "Wire Services",
        "bias": "Center",
        "factual": "Very High",
        "author_url_pattern": "https://apnews.com/author/{author_slug}"
    },
    {
        "name": "Reuters World",
        "url": "https://news.google.com/rss/search?q=when:24h+allinurl:reuters.com&ceid=US:en&hl=en-US&gl=US",
        "category": "Wire Services",
        "bias": "Center",
        "factual": "Very High",
        "author_url_pattern": "https://www.reuters.com/authors/{author_slug}/"
    },
    {
        "name": "NPR News",
        "url": "https://feeds.npr.org/1001/rss.xml",
        "category": "Public Broadcasting",
        "bias": "Left-Center",
        "factual": "Very High",
        "author_url_pattern": "https://www.npr.org/people/{author_slug}"
    },
    {
        "name": "BBC World",
        "url": "https://feeds.bbci.co.uk/news/world/rss.xml",
        "category": "International",
        "bias": "Left-Center",
        "factual": "High",
        "author_url_pattern": None  # BBC doesn't have consistent author pages
    },
    {
        "name": "The Guardian World",
        "url": "https://www.theguardian.com/world/rss",
        "category": "International",
        "bias": "Left-Center",
        "factual": "Mixed",
        "author_url_pattern": "https://www.theguardian.com/profile/{author_slug}"
    },
    {
        "name": "PBS NewsHour",
        "url": "https://www.pbs.org/newshour/feeds/rss/headlines",
        "category": "Public Broadcasting",
        "bias": "Center",
        "factual": "High",
        "author_url_pattern": "https://www.pbs.org/newshour/author/{author_slug}"
    },
    {
        "name": "Wall Street Journal",
        "url": "https://feeds.content.dowjones.io/public/rss/mw_topstories",
        "category": "Business",
        "bias": "Right-Center",
        "factual": "High",
        "author_url_pattern": "https://www.wsj.com/news/author/{author_slug}"
    },
    {
        "name": "The Economist",
        "url": "https://www.economist.com/international/rss.xml",
        "category": "International",
        "bias": "Center",
        "factual": "High",
        "author_url_pattern": None  # Economist articles are often unbylined
    }
]

# MBFC bias → Wirefeedr display values
MBFC_BIAS_MAP = {
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

# MBFC reporting → Wirefeedr factual display values
MBFC_REPORTING_MAP = {
    "very-high": "Very High",
    "high": "High",
    "mostly-factual": "Mostly Factual",
    "mixed": "Mixed",
    "low": "Mixed",
    "very-low": "Mixed",
}

# Bias display colors (for UI)
BIAS_COLORS = {
    "Center": "#27ae60",        # Green
    "Left-Center": "#3498db",   # Blue
    "Right-Center": "#9b59b6",  # Purple
    "Lean Left": "#2980b9",     # Darker blue
    "Lean Right": "#8e44ad",    # Darker purple
    "Left": "#e74c3c",          # Red
    "Right": "#e74c3c",         # Red
}

# Factual rating colors
FACTUAL_COLORS = {
    "Very High": "#27ae60",     # Green
    "High": "#2ecc71",          # Light green
    "Mostly Factual": "#f39c12", # Orange
    "Mixed": "#e74c3c",         # Red
}

# URL path patterns that indicate opinion/editorial content
OPINION_URL_PATTERNS = [
    "/opinion/",
    "/opinions/",
    "/editorial/",
    "/editorials/",
    "/columnist/",
    "/columnists/",
    "/blog/",
    "/blogs/",
    "/commentary/",
    "/op-ed/",
    "/perspective/",
    "/analysis/",
    "/letter-to-editor/",
    "/letters/"
]

# Title patterns indicating opinion content
OPINION_TITLE_PATTERNS = [
    "opinion:",
    "editorial:",
    "commentary:",
    "op-ed:",
    "column:",
    "analysis:",
    "perspective:",
    "letter to the editor",
    "| opinion",
    "- opinion",
]

# Sensationalism keywords and phrases (case-insensitive)
SENSATIONAL_KEYWORDS = [
    # Urgency/shock words
    "breaking:",
    "breaking news:",
    "shocking",
    "bombshell",
    "explosive",
    "stunning",
    "jaw-dropping",
    "mind-blowing",
    "unbelievable",
    "incredible",

    # Conflict exaggeration
    "slams",
    "destroys",
    "eviscerates",
    "obliterates",
    "demolishes",
    "annihilates",
    "blasts",
    "rips",
    "torches",
    "schools",
    "owns",
    "wrecks",
    "crushes",

    # Clickbait phrases
    "you won't believe",
    "what happened next",
    "this one trick",
    "doctors hate",
    "the truth about",
    "what they don't want you to know",
    "goes viral",
    "the internet is",
    "twitter reacts",
    "everyone is talking about",
    "is breaking the internet",

    # Emotional manipulation
    "outrage",
    "fury",
    "meltdown",
    "chaos",
    "firestorm",
    "backlash erupts",
    "nightmare",
    "disaster",
]

# Clickbait number patterns (e.g., "10 reasons why...")
CLICKBAIT_NUMBER_PATTERNS = [
    r"^\d+\s+(reasons?|ways?|things?|facts?|secrets?|tricks?|tips?|signs?|mistakes?)",
    r"^top\s+\d+",
    r"^\d+\s+.+\s+that\s+will",
]

# Article grades (based on objectivity score - higher = better)
# Format: (max_score, grade_letter, label, color)
ARTICLE_GRADES = [
    (24, "F", "Slop", "#e74c3c"),         # Red
    (44, "D", "Noise", "#e67e22"),        # Orange
    (64, "C", "Weak", "#f1c40f"),         # Yellow
    (84, "B", "Passable", "#2ecc71"),     # Green
    (100, "A", "Solid", "#27ae60"),       # Dark green
]

# Application settings
DEFAULT_SETTINGS = {
    "min_score_threshold": 70,  # Hide articles with objectivity score below this
    "auto_refresh_minutes": 60,
    "article_retention_days": 2,  # 48 hours
    "max_articles_per_feed": 50,
    "show_read_articles": True,
    "recency_hours": 24,  # Only show articles from last N hours (0 = no limit)
    "max_per_source": 10,  # Max articles per feed (0 = no limit), ranked by quality
    "cluster_topics": True,  # Group similar articles into topic clusters
}

# Database settings
DATABASE_NAME = "news.db"
DATA_FOLDER = "data"
