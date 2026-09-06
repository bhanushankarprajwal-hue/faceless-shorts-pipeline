"""
score_candidates.py
Sends filtered candidates to Gemini for scoring against the 10 criteria,
plus a Layer 2 semantic duplicate check against recent used-story summaries.
Outputs a ranked list of scored, non-duplicate candidates.
"""

import json
import os
import re

import google.generativeai as genai

from sheets_helper import read_all_rows

INPUT_PATH = "data/filtered_candidates.json"
OUTPUT_PATH = "data/scored_candidates.json"

# If this default model name ever errors out, check aistudio.google.com
# for the current available free-tier model names and update this.
MODEL_NAME = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")

CRITERIA = [
    "hook_strength", "curiosity_gap", "emotional_stakes", "escalation_potential",
    "satisfying_payoff", "visual_availability", "factual_reliability",
    "competition_level", "shorts_format_fit", "overall_originality",
]

MAX_CANDIDATES_TO_SCORE = 15  # keep batch size sane for one API call


def build_prompt(candidates, recent_used_summaries):
    used_context = "\n".join(f"- {s}" for s in recent_used_summaries) or "(none yet)"

    candidates_block = ""
    for i, c in enumerate(candidates):
        candidates_block += (
            f"\n[{i}] TITLE: {c.get('title')}\n"
            f"SUMMARY: {c.get('summary')[:500]}\n"
            f"SOURCE: {c.get('source_feed')}\n"
        )

    return f"""You are evaluating story candidates for a YouTube Shorts channel about
curiosity-building real stories (mysteries, surprising events, science, history, animals, human stories).

Here are core-fact summaries of stories ALREADY USED recently (do not recommend anything
substantially the same event or topic as these, even if worded differently):
{used_context}

Score EACH candidate below on a 1-10 scale for each criterion:
{", ".join(CRITERIA)}

Also flag "is_likely_duplicate": true/false if it overlaps with the used stories above,
and give a one-line "duplicate_reason" if true (else empty string).

Give a one-line "justification" per candidate explaining the scores.

Candidates:
{candidates_block}

Respond ONLY with valid JSON, no markdown fences, no extra text, in this exact structure:
{{
  "results": [
    {{
      "index": 0,
      "scores": {{"hook_strength": 8, "curiosity_gap": 7, ... (all criteria)}},
      "total_score": 0,
      "is_likely_duplicate": false,
      "duplicate_reason": "",
      "justification": "..."
    }}
  ]
}}
"""


def extract_json(text):
    """Gemini sometimes wraps JSON in markdown fences despite instructions; strip them."""
    text = text.strip()
    text = re.sub(r"^```(json)?", "", text).strip()
    text = re.sub(r"```$", "", text).strip()
    return json.loads(text)


def main():
    with open(INPUT_PATH, "r", encoding="utf-8") as f:
        candidates = json.load(f)

    if not candidates:
        print("No candidates to score. Exiting.")
        with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
            json.dump([], f)
        return

    candidates = candidates[:MAX_CANDIDATES_TO_SCORE]

    try:
        used_rows = read_all_rows("Used_Stories_Log")
        recent_summaries = [r.get("Core Fact Summary", "") for r in used_rows[-40:]]
    except Exception as e:
        print(f"[WARN] Could not read Used_Stories_Log ({e}). Proceeding without it.")
        recent_summaries = []

    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY environment variable is missing.")
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel(MODEL_NAME)

    prompt = build_prompt(candidates, recent_summaries)
    response = model.generate_content(
        prompt,
        generation_config={"max_output_tokens": 8192},
    )
    try:
        parsed = extract_json(response.text)
    except Exception as e:
        print("=== RAW GEMINI RESPONSE (for debugging) ===")
        print(response.text)
        print("=== END RAW RESPONSE ===")
        raise e

    scored = []
    for result in parsed.get("results", []):
        idx = result.get("index")
        if idx is None or idx >= len(candidates):
            continue

        scores = result.get("scores", {})
        total = sum(scores.get(c, 0) for c in CRITERIA)

        scored.append({
            **candidates[idx],
            "scores": scores,
            "total_score": total,
            "is_likely_duplicate": result.get("is_likely_duplicate", False),
            "duplicate_reason": result.get("duplicate_reason", ""),
            "justification": result.get("justification", ""),
        })

    non_duplicates = [c for c in scored if not c["is_likely_duplicate"]]
    duplicates = [c for c in scored if c["is_likely_duplicate"]]

    non_duplicates.sort(key=lambda c: c["total_score"], reverse=True)

    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump({
            "ranked_candidates": non_duplicates,
            "rejected_as_duplicate": duplicates,
        }, f, indent=2, ensure_ascii=False)

    print(f"Scored {len(scored)} candidate(s).")
    print(f"{len(duplicates)} rejected as semantic duplicates.")
    print(f"Top candidate: {non_duplicates[0]['title'] if non_duplicates else 'NONE'}")


if __name__ == "__main__":
    main()
