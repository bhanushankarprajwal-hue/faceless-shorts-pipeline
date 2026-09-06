"""
sheets_writer.py
Writes the day's final package and rejected candidates into the
Google Sheet dashboard: Today, Archive, Used_Stories_Log, Rejected_Candidates.
"""

import json
from datetime import date

from sheets_helper import get_worksheet, append_row, overwrite_row_2

FINAL_PACKAGE_PATH = "data/final_package.json"
SCORED_PATH = "data/scored_candidates.json"
VERIFIED_PATH = "data/verified_candidates.json"

TODAY_HEADERS = [
    "Date", "Story Title", "One-Line Hook", "Full Script", "VO Script",
    "Shot List", "Visual Queries", "Music/SFX Notes", "Source Links",
    "Score Breakdown", "Est. Runtime",
]

ARCHIVE_HEADERS = TODAY_HEADERS + ["Date Archived"]


def load_json(path, default):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return default


def format_full_script(full_script):
    if not full_script:
        return ""
    order = ["hook", "curiosity_gap", "setup", "escalation", "reveal", "payoff"]
    return "\n\n".join(f"{k.upper()}: {full_script.get(k, '')}" for k in order)


def format_shot_list(shot_list):
    lines = []
    for shot in shot_list or []:
        lines.append(
            f"Shot {shot.get('shot_number')}: {shot.get('visual_description')} "
            f"[{shot.get('suggested_source_type')} - \"{shot.get('search_query')}\"] "
            f"(VO: {shot.get('vo_line')})"
        )
    return "\n".join(lines)


def format_visual_queries(shot_list):
    return "\n".join(
        f"Shot {s.get('shot_number')}: {s.get('search_query')}" for s in (shot_list or [])
    )


def format_music_notes(music_notes):
    if not music_notes:
        return ""
    mood = music_notes.get("overall_mood", "")
    markers = music_notes.get("moment_markers", [])
    marker_lines = "\n".join(f"- {m.get('timing')}: {m.get('suggestion')}" for m in markers)
    return f"Mood: {mood}\n{marker_lines}"


def format_score_breakdown(scores, total_score):
    if not scores:
        return ""
    lines = [f"{k}: {v}" for k, v in scores.items()]
    lines.append(f"TOTAL: {total_score}")
    return "\n".join(lines)


def archive_previous_today():
    """Moves whatever is currently in the Today tab into Archive before overwriting it."""
    today_ws = get_worksheet("Today")
    rows = today_ws.get_all_values()

    if len(rows) < 2:
        print("No previous Today entry to archive (first run or empty).")
        return

    previous_row = rows[1]  # row 1 = header, row 2 = the one story
    archived_row = previous_row + [date.today().isoformat()]
    append_row("Archive", archived_row)
    print("Previous Today entry moved to Archive.")


def write_today(package):
    story_title = package.get("story_title", "")
    hook = package.get("full_script", {}).get("hook", "")
    full_script_text = format_full_script(package.get("full_script"))
    vo_script = package.get("vo_script", "")
    shot_list_text = format_shot_list(package.get("shot_list"))
    visual_queries_text = format_visual_queries(package.get("shot_list"))
    music_notes_text = format_music_notes(package.get("music_notes"))
    source_link = package.get("source_link", "")
    score_breakdown_text = format_score_breakdown(
        package.get("scores"), package.get("total_score")
    )
    runtime = package.get("estimated_runtime_seconds", "")

    row = [
        date.today().isoformat(), story_title, hook, full_script_text, vo_script,
        shot_list_text, visual_queries_text, music_notes_text, source_link,
        score_breakdown_text, runtime,
    ]
    overwrite_row_2("Today", TODAY_HEADERS, row)
    print(f"Today tab updated with: {story_title}")


def log_used_story(package):
    verification = package.get("verification", {})
    core_facts = verification.get("verified_core_facts", "")
    slug = package.get("story_title", "")[:80]

    row = [date.today().isoformat(), slug, core_facts, "", package.get("source_link", "")]
    append_row("Used_Stories_Log", row)
    print(f"Logged '{slug}' to Used_Stories_Log.")


def log_rejected_candidates():
    scored_data = load_json(SCORED_PATH, {})
    verified_data = load_json(VERIFIED_PATH, {})

    semantic_dupes = scored_data.get("rejected_as_duplicate", [])
    all_checked = verified_data.get("all_checked", [])
    verified_passed_titles = {
