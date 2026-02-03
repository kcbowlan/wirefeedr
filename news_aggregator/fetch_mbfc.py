"""Fetch MBFC data from drmikecrowe/mbfcext and build local lookup JSON."""

import json
import os
import sys
import urllib.request
from datetime import datetime, timezone

MBFC_URL = "https://raw.githubusercontent.com/drmikecrowe/mbfcext/main/docs/v5/data/combined.json"
OUTPUT_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "mbfc_sources.json")


def fetch_and_build():
    print(f"Fetching MBFC data from {MBFC_URL} ...")
    req = urllib.request.Request(MBFC_URL, headers={"User-Agent": "wirefeedr/1.0"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        raw = json.loads(resp.read().decode("utf-8"))

    version = raw.get("version", 5)
    aliases = raw.get("aliases", {})
    sources_list = raw.get("sources", [])

    # Re-index sources by domain
    sources = {}
    for src in sources_list:
        domain = src.get("domain", "").strip().lower()
        if not domain:
            continue
        sources[domain] = src

    output = {
        "_meta": {
            "source": "drmikecrowe/mbfcext",
            "version": version,
            "fetched": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
            "total_sources": len(sources),
        },
        "aliases": aliases,
        "sources": sources,
    }

    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, separators=(",", ":"))

    print(f"Wrote {len(sources)} sources to {OUTPUT_PATH}")
    print(f"  Aliases: {len(aliases)}")

    # Coverage check against default feeds
    from config import DEFAULT_FEEDS
    import mbfc
    mbfc.load_mbfc_data()
    from mbfc import lookup_source

    # Feed URLs point to RSS endpoints (feeds.bbci.co.uk, feeds.content.dowjones.io),
    # not the publisher domain. For Google News feeds, normalize_domain extracts the
    # allinurl: domain. For direct RSS feeds, we check known publisher article URLs.
    _FEED_SAMPLE_URLS = {
        "BBC World": "https://www.bbc.com/news/article",
        "Wall Street Journal": "https://www.wsj.com/articles/article",
    }

    print("\nFeed coverage check:")
    matched = 0
    for feed in DEFAULT_FEEDS:
        sample_url = _FEED_SAMPLE_URLS.get(feed["name"], feed["url"])
        entry = lookup_source(sample_url)
        status = "OK" if entry else "MISSING"
        if entry:
            matched += 1
        domain = entry["domain"] if entry else "?"
        bias = entry["bias"] if entry else "N/A"
        print(f"  {status:7s}  {feed['name']:25s}  domain={domain}  mbfc_bias={bias}")

    print(f"\n{matched}/{len(DEFAULT_FEEDS)} feeds matched in MBFC data")


if __name__ == "__main__":
    fetch_and_build()
