"""
verify_facts.py
Takes the top-ranked scored candidates, fetches their source article text,
and asks Gemini to cross-check the claims for exaggeration/inaccuracy.
Outputs a shortlist of verified candidates with a confidence rating.
"""

import json
import os
import re

import requests
import google.generativeai as genai

INPUT_PATH = "data/scored_candidates.json"
OUTPUT_PATH = "data/verified_candidates.json"

MODEL_NAME = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")
TOP_N_TO_VERIFY = 5
REQUEST_TIMEOUT_SECONDS = 15
MAX_ARTICLE_CHARS = 6000

HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; ShortsStoryBot/1.0; personal research project)"
}


def fetch_article_text(url):
    try:
        resp = requests.get(url, headers=HEADERS, timeout=REQUEST_TIMEOUT_SECONDS)
        resp.raise_for_status()
        text = re.sub(r"<[^>]+>", " ", resp.text)
        text = re.sub(r"\s+", " ", text).strip()
        return text[:MAX_ARTICLE_CHARS]
    except Exception as e:
        print(f"[WARN] Could not fetch article at {url}: {e}")
        return None


def build_verification_prompt(candidate, article_text):
    return f"""You are fact-checking a story candidate before it becomes a YouTube Shorts script.

CANDIDATE TITLE: {candidate.get('title')}
CANDIDATE SUMMARY (from RSS feed): {candidate.get('summary')}

SOURCE ARTICLE TEXT (fetched directly from the original link):
{article_text if article_text else "(Could not fetch article text - evaluate based on summary only, and lower confidence accordingly.)"}

Assess:
1. Does the RSS summary accurately reflect the source article, or does it exaggerate/misstate anything?
2. Are the core factual claims specific and verifiable (named people, places, dates, institutions), or vague/unverifiable?
3. Any red flags of misinformation, satire, or clickbait exaggeration?

Respond ONLY with valid JSON, no markdown fences, no extra text:
{{
  "confidence": "high" | "medium" | "low",
  "summary_accurate": true | false,
  "concerns": "one or two sentences describing any concerns, or empty string if none",
  "verified_core_facts": "a clean 1-2 sentence statement of what can be confidently stated as true"
}}
"""


def extract_json(text):
    text = text.strip()
    text = re.sub(r"^```(json)?", "", text).strip()
    text = re.sub(r"```$", "", text).strip()
