"""
generate_package.py
Takes the single best verified candidate and asks Gemini to produce
the full Shorts creative package: structured script, clean VO script,
shot-by-shot visual plan, visual search queries, and music/SFX notes.
"""

import json
import os
import re

import google.generativeai as genai

INPUT_PATH = "data/verified_candidates.json"
OUTPUT_PATH = "data/final_package.json"

MODEL_NAME = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")

JSON_TEMPLATE_LINES = [
    "Respond ONLY with valid JSON, no markdown fences, no extra text, in this exact structure:",
    "{",
    '  "full_script": {',
    '    "hook": "...", "curiosity_gap": "...", "setup": "...",',
    '    "escalation": "...", "reveal": "...", "payoff": "..."',
    "  },",
    '  "vo_script": "...",',
    '  "shot_list": [',
    '    {"shot_number": 1, "vo_line": "...", "visual_description": "...",',
    '      "suggested_source_type": "...", "search_query": "..."}',
    "  ],",
    '  "music_notes": {',
    '    "overall_mood": "...",',
    '    "moment_markers": [{"timing": "...", "suggestion": "..."}]',
    "  },",
    '  "estimated_runtime_seconds": 0',
    "}",
]

INSTRUCTION_LINES = [
    "You are writing a complete YouTube Shorts content package for a channel about",
    "curiosity-building real stories. Target runtime: 30-60 seconds spoken aloud.",
    "",
    "STORY_TITLE_PLACEHOLDER",
    "VERIFIED_FACTS_PLACEHOLDER",
    "SOURCE_PLACEHOLDER",
    "",
    "Write the following, using ONLY the verified facts above. Do not invent details,",
    "names, or numbers that are not grounded in them.",
    "",
    "1. FULL_SCRIPT: the complete script broken into these labeled sections:",
    "   HOOK - first 1-2 sentences, must create instant curiosity",
    "   CURIOSITY_GAP - the specific question or mystery planted",
    "   SETUP - context needed to understand the story",
    "   ESCALATION - tension and stakes rising",
    "   REVEAL - the answer or twist",
    "   PAYOFF - the satisfying closing line, ideally with a lingering thought",
    "",
    "2. VO_SCRIPT: the same content rewritten as ONE clean, continuous voice-over script,",
    "ready for text-to-speech. Natural spoken rhythm, no stage directions, no labels,",
    "no asterisks, just the words to be spoken.",
    "",
    "3. SHOT_LIST: an array of shots, each with:",
    "   - shot_number",
    "   - vo_line (the exact VO_SCRIPT segment this shot covers)",
    "   - visual_description (what should be shown on screen)",
    "   - suggested_source_type (one of: Pexels, Pixabay, Wikimedia Commons,",
    "     NASA archive, Internet Archive, Public domain museum or institution,",
    "     Text or graphic overlay)",
    "   - search_query (a specific search phrase to use on that source)",
    "",
    "4. MUSIC_NOTES: object with overall_mood and moment_markers",
    "(an array of timing and suggestion pairs).",
    "",
    "5. ESTIMATED_RUNTIME_SECONDS: your best estimate of spoken runtime for VO_SCRIPT.",
    "",
]


def pick_winner(verified_candidates):
    if not verified_candidates:
        return None
    return verified_candidates[0]


def build_package_prompt(candidate):
    verification = candidate.get("verification", {})
    verified_facts = verification.get("verified_core_facts") or candidate.get("summary", "")

    lines = []
    for line in INSTRUCTION_LINES:
        if line == "STORY_TITLE_PLACEHOLDER":
            lines.append("STORY TITLE: " + str(candidate.get("title")))
        elif line == "VERIFIED_FACTS_PLACEHOLDER":
            lines.append("VERIFIED CORE FACTS: " + str(verified_facts))
        elif line == "SOURCE_PLACEHOLDER":
            lines.append("SOURCE: " + str(candidate.get("link")))
        else:
            lines.append(line)

    lines.extend(JSON_TEMPLATE_LINES)
    return "\n".join(lines)


def extract_json(text):
    text = text.strip()
    text = re.sub(r"^```(json)?", "", text).strip()
    text = re.sub(r"```$", "", text).strip()
    return json.loads(text)


def main():
    with open(INPUT_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)

    verified = data.get("verified_candidates", [])
    winner = pick_winner(verified)

    if not winner:
        print("No verified candidate available. No package generated today.")
        with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
            json.dump({}, f)
        return

    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY environment variable is missing.")
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel(MODEL_NAME)

    prompt = build_package_prompt(winner)
    response = model.generate_content(
        prompt,
        generation_config={"max_output_tokens": 8192},
    )

    try:
        package = extract_json(response.text)
    except Exception as e:
        print("=== RAW GEMINI RESPONSE (for debugging) ===")
        print(response.text)
        print("=== END RAW RESPONSE ===")
        raise e

    final = {
        "story_title": winner.get("title"),
        "source_link": winner.get("link"),
        "scores": winner.get("scores", {}),
        "total_score": winner.get("total_score"),
        "verification": winner.get("verification", {}),
    }
    final.update(package)

    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(final, f, indent=2, ensure_ascii=False)

    print(f"Package generated for: {final['story_title']}")
    print(f"Estimated runtime: {final.get('estimated_runtime_seconds')}s")


if __name__ == "__main__":
    main()
