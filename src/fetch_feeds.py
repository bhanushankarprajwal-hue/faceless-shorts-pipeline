"""
fetch_feeds.py
Reads config/feeds.yaml, pulls recent items from each RSS feed,
and saves them as a single JSON file of raw story candidates.
"""

import json
import os
from datetime import datetime, timedelta, timezone

import feedparser
import yaml

FEEDS_CONFIG_PATH = "config/feeds.yaml"
OUTPUT_PATH = "data/raw_candidates.json"
LOOKBACK_HOURS = 48  # only keep items published within the last 48 hours


def load_feed_list():
    with open(FEEDS_CONFIG_PATH, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)
    return config.get("feeds", [])


def parse_published_date(entry):
    """Try a few possible date fields; return a timezone-aware datetime or None."""
    for key in ("published_parsed", "updated_parsed"):
        value = entry.get(key)
        if value:
            return datetime(*value[:6], tzinfo=timezone.utc)
    return None


def fetch_one_feed(feed_name, feed_url):
    candidates = []
    try:
        parsed = feedparser.parse(feed_url)
    except Exception as e:
        print(f"[SKIP] Could not fetch '{feed_name}': {e}")
        return candidates

    if parsed.bozo and not parsed.entries:
        print(f"[SKIP] Feed '{feed_name}' returned no readable entries.")
        return candidates

    cutoff = datetime.now(timezone.utc) - timedelta(hours=LOOKBACK_HOURS)

    for entry in parsed.entries:
        published = parse_published_date(entry)
        if published and published < cutoff:
            continue  # too old, skip

        candidates.append({
            "source_feed": feed_name,
            "title": entry.get("title", "").strip(),
            "link": entry.get("link", "").strip(),
            "summary": entry.get("summary", "").strip(),
            "published": published.isoformat() if published else None,
        })

    print(f"[OK] {feed_name}: {len(candidates)} recent item(s)")
    return candidates


def main():
    os.makedirs("data", exist_ok=True)
    feeds = load_feed_list()

    all_candidates = []
    for feed in feeds:
        name = feed.get("name", "Unnamed feed")
        url = feed.get("url")
        if not url:
            continue
        all_candidates.extend(fetch_one_feed(name, url))

    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(all_candidates, f, indent=2, ensure_ascii=False)

    print(f"\nSaved {len(all_candidates)} total raw candidate(s) to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
