#!/usr/bin/env python3
"""
Generate social media snippets from an episode summary.

Usage:
    python generate_social.py "podcasts/ESA/Episode Summaries/Episode 118 - Title.txt"
    python generate_social.py "path/to/summary.txt" --platforms twitter linkedin
    python generate_social.py "path/to/summary.txt" --json   (outputs raw JSON for the web UI)
"""

import argparse
import json
import os
import re
import sys
from pathlib import Path

from google import genai

MODEL = "gemini-2.5-flash-lite"

PLATFORM_RULES = {
    "twitter":    "Max 280 characters including hashtags. Punchy and engaging. 2-3 relevant hashtags.",
    "linkedin":   "100-200 words. Professional tone. 3-5 hashtags at the end.",
    "newsletter": "2-3 sentences. Neutral, informative tone. No hashtags. Suitable for an email.",
}

PROMPT = """\
You are writing social media posts to promote a podcast episode.

Read the episode summary below and write a post for each platform listed.
Respond with a JSON object only -- no markdown, no code fences, just raw JSON.
Use the platform names as keys exactly as listed.

Platforms and rules:
{platform_rules}

Additional rules:
- Do not use em dashes
- Do not invent facts or quotes not present in the summary

EPISODE SUMMARY:
{summary}
"""


def generate(summary: str, platforms: list[str], api_key: str, model: str) -> dict[str, str]:
    rules = "\n".join(f"  {p}: {PLATFORM_RULES[p]}" for p in platforms)
    client = genai.Client(api_key=api_key)
    response = client.models.generate_content(
        model=model,
        contents=PROMPT.format(platform_rules=rules, summary=summary),
    )
    text = response.text.strip()
    # Strip markdown code fences if Gemini adds them anyway
    text = re.sub(r"^```[a-z]*\n?", "", text)
    text = re.sub(r"\n?```$", "", text)
    return json.loads(text)


def main():
    parser = argparse.ArgumentParser(description="Generate social media snippets from an episode summary")
    parser.add_argument("summary_file", help="Path to the episode summary .txt file")
    parser.add_argument(
        "--platforms", nargs="+",
        choices=list(PLATFORM_RULES.keys()),
        default=list(PLATFORM_RULES.keys()),
    )
    parser.add_argument("--json", action="store_true", dest="as_json",
                        help="Output raw JSON (used by the web UI)")
    parser.add_argument("--api-key", help="Google API key (overrides GOOGLE_API_KEY env var)")
    parser.add_argument("--model", default=MODEL)
    args = parser.parse_args()

    summary_path = Path(args.summary_file).resolve()
    if not summary_path.exists():
        sys.exit(f"Error: File not found: {summary_path}")

    api_key = args.api_key or os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        sys.exit("Error: Set the GOOGLE_API_KEY environment variable or pass --api-key.")

    summary = summary_path.read_text(encoding="utf-8", errors="ignore").strip()

    if not args.as_json:
        print(f"Generating snippets for: {summary_path.name}\n", flush=True)

    snippets = generate(summary, args.platforms, api_key, args.model)

    if args.as_json:
        print(json.dumps(snippets))
    else:
        labels = {"twitter": "Twitter / X", "linkedin": "LinkedIn", "newsletter": "Newsletter"}
        for platform, text in snippets.items():
            print(f"-- {labels.get(platform, platform.upper())} --")
            print(text)
            print()


if __name__ == "__main__":
    main()
