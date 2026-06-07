#!/usr/bin/env python3
"""
Generate social media snippets from an episode summary.

Usage:
    python generate_social.py "podcasts/ESA/Episode Summaries/Episode 118 - Title.txt"
    python generate_social.py "path/to/summary.txt" --platforms twitter linkedin
"""

import argparse
import os
import sys
from pathlib import Path

from google import genai

MODEL = "gemini-2.5-flash-lite"

PLATFORMS = {
    "twitter": "TWITTER/X (max 280 characters including hashtags, punchy and engaging, 2-3 hashtags)",
    "linkedin": "LINKEDIN (100-200 words, professional tone, 3-5 hashtags at the end)",
    "newsletter": "NEWSLETTER BLURB (2-3 sentences, neutral tone, no hashtags, suitable for an email)",
}

PROMPT = """\
You are writing social media posts to promote a podcast episode.

Read the episode summary below and write a post for each platform listed.
Write the platform name in all-caps as a header before each post, with a blank line after it.
Do not use em dashes. Do not invent facts or quotes not present in the summary.

PLATFORMS:
{platforms}

EPISODE SUMMARY:
{summary}
"""


def main():
    parser = argparse.ArgumentParser(description="Generate social media snippets from an episode summary")
    parser.add_argument("summary_file", help="Path to the episode summary .txt file")
    parser.add_argument(
        "--platforms", nargs="+",
        choices=list(PLATFORMS.keys()),
        default=list(PLATFORMS.keys()),
        help="Platforms to generate for (default: all)",
    )
    parser.add_argument("--api-key", help="Google API key (overrides GOOGLE_API_KEY env var)")
    parser.add_argument("--model", default=MODEL, help=f"Gemini model (default: {MODEL})")
    args = parser.parse_args()

    summary_path = Path(args.summary_file).resolve()
    if not summary_path.exists():
        sys.exit(f"Error: File not found: {summary_path}")

    api_key = args.api_key or os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        sys.exit("Error: Set the GOOGLE_API_KEY environment variable or pass --api-key.")

    summary = summary_path.read_text(encoding="utf-8", errors="ignore").strip()
    platforms_text = "\n".join(f"- {PLATFORMS[p]}" for p in args.platforms)

    print(f"Generating social snippets for: {summary_path.name}", flush=True)
    print(f"Platforms: {', '.join(args.platforms)}\n", flush=True)

    client = genai.Client(api_key=api_key)
    response = client.models.generate_content(
        model=args.model,
        contents=PROMPT.format(platforms=platforms_text, summary=summary),
    )

    print(response.text)


if __name__ == "__main__":
    main()
