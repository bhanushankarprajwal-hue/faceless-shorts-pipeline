"""
dedup_check.py
Layer 1 duplicate filter: removes candidates that closely match
anything already in the Used_Stories_Log Google Sheet tab, using
simple fuzzy text comparison (no AI call needed for this pass).
"""

import json
from difflib import SequenceMatcher

from sheets_helper import read_all_rows

INPUT_PATH = "data/raw_candidates.json"
OUTPUT_PATH = "data/filtered_candidates.json"
SIMILARITY_THRESHOLD = 0.72  # 0.0 = no match, 1.0 = identical text


def similarity(a, b):
    if not a or not b:
        return 0.0
    return SequenceMatcher(None, a.lower().strip(), b.lower().strip()).ratio()


def is_duplicate(candidate, used_stories):
    title = candidate.get("title", "")
    summary = candidate.get("summary", "")

    for used in used_stories:
        used_summary = used.get("Core Fact Summary", "")
        used_slug = used.get("Story Slug", "")

        if similarity(title, used_slug) >= SIMILARITY_THRESHOLD:
            return True, used_slug
        if similarity(summary, used_summary) >= SIMILARITY_THRESHOLD:
            return True, used_slug

    return False, None


def main():
    with open(INPUT_PATH, "r", encoding="utf-8") as f:
        candidates = json.load(f)

    try:
        used_stories = read_all_rows("Used_Stories_Log")
    except Exception as e:
        print(f"[WARN] Could not read Used_Stories_Log ({e}). Proceeding with no dedup history.")
        used_stories = []

    kept = []
    dropped = []

    for candidate in candidates:
        dup, matched_slug = is_duplicate(candidate, used_stories)
        if dup:
            candidate["duplicate_of"] = matched_slug
            dropped.append(candidate)
        else:
            kept.append(candidate)

    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(kept, f, indent=2, ensure_ascii=False)

    print(f"Checked {len(candidates)} candidate(s).")
    print(f"Kept {len(kept)} as non-duplicate.")
    print(f"Dropped {len(dropped)} as likely duplicate(s):")
    for d in dropped:
        print(f"   - '{d['title']}' matched used story '{d['duplicate_of']}'")


if __name__ == "__main__":
    main()
