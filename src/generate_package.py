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


def pick_winner(verified_candidates):
    """Verified candidates are already in score order from earlier steps;
    the first one is the winner."""
    if not verified_candidates:
        return None
    return verified_candidates[0]


def build_package_prompt(candidate):
    verification = candidate.get("verification", {})
    verified_facts = verification.get("verified_core_facts") or candidate.get("summary", "")

    return f"""You are writing a complete YouTube Shorts content package for a channel about
curiosity-building real stories. Target runtime: 30-60 seconds spoken aloud.

STORY TITLE: {candidate.get('title')}
VERIFIED CORE FACTS: {verified_facts}
SOURCE: {candidate.get('link')}

Write the following, using ONLY the verified facts above (do not invent details,
names, or numbers that aren't grounded in them):

1. FULL_SCRIPT: the complete script broken into these labeled sections:
   HOOK (first 1-2 sentences, must create instant curiosity)
   CURIOSITY_GAP (the specific question/mystery planted)
   SETUP (context needed to understand the story)
   ESCALATION (tension/stakes rising)
   REVEAL (the answer/twist)
   PAYOFF (the satisfying closing line, ideally with a lingering thought)

2. VO_SCRIPT: the same content rewritten as ONE clean, continuous voice-over script,
   ready for text-to-speech - natural spoken rhythm, no stage directions, no labels,
   no asterisks, just the words to be spoken.

3. SHOT_LIST: an array of shots, each with:
   - "shot_number"
   - "vo_line" (the exact VO_SCRIPT segment this shot covers)
   - "visual_description" (what should be shown on screen)
   - "suggested_source_type" (one of: "Pexels", "Pixabay", "Wikimedia Commons", "NASA archive", "Internet Archive", "Public domain museum/institution", "Text/graphic overlay")
   - "search_query" (a specific search phrase to use on that source)

4. MUSIC_NOTES: object with "overall_mood" and "moment_markers" (array of
   {{"timing": "e.g. at the reveal", "suggestion": "e.g. brief silence then a stinger"}})

5. ESTIMATED_RUNTIME_SECONDS: your best estimate of spoken runtime for VO_SCRIPT.

Respond ONLY with valid JSON, no markdown fences, no extra text, in this exact structure:
{{
  "full_script": {{
    "hook": "...", "curiosity_gap": "...", "setup": "...",
    "escalation": "...", "reveal": "...", "payoff": "..."
  }},
