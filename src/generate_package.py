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

JSON_TEMPLATE = """
Respond ONLY with valid JSON, no markdown fences, no extra text, in this exact structure:
{
  "full_script": {
    "hook": "...", "curiosity_gap": "...", "setup": "...",
    "escalation": "...", "reveal": "...", "payoff": "..."
  },
  "vo_script": "...",
  "shot_list": [
    {"shot_number": 1, "vo_line": "...", "visual_description": "...",
      "suggested_source_type": "...", "search_query": "..."}
  ],
  "music_notes": {
    "overall_mood": "...",
    "moment_markers": [{"timing": "...", "suggestion": "..."}]
  },
  "estimated_runtime_seconds": 0
}
"""


def pick_winner(verified_candidates):
    if not verified_candidates:
        return None
    return verified_candidates[0]


def build_package_prompt(candidate):
    verification = candidate.get("verification", {})
    verified_facts = verification.get("verified_core_facts") or candidate.get("summary", "")

    instructions = (
        "You are writing a complete YouTube Shorts content package for a channel about "
        "curiosity-building real stories. Target runtime: 30-60 seconds spoken aloud.\n\n"
        "STORY TITLE: " + str(candidate.get("title")) + "\n"
        "VERIFIED CORE FACTS: " + str(verified_facts) + "\n"
        "SOURCE: " + str(candidate.get("link")) + "\n\n"
        "Write the following,
