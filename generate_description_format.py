#!/usr/bin/env python3
"""
Draft a Description_Format.txt for a podcast by analysing its published episode descriptions.

Fetches the RSS feed, extracts recent episode descriptions, and uses the Gemini API
to identify formatting patterns and write the format document.

Requirements:
    pip install google-genai
    GOOGLE_API_KEY environment variable set

Usage:
    python generate_description_format.py "podcasts/My Podcast" --rss https://feeds.example.com/feed.xml
    python generate_description_format.py "podcasts/My Podcast"
      (reads RSS URL from Workflow.txt if already set)
"""

import argparse
import os
import re
import sys
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

from google import genai

EPISODES_TO_ANALYZE = 10
MODEL = "gemini-2.5-flash-lite"

ANALYSIS_PROMPT = """\
You are documenting the formatting conventions used in a podcast's episode descriptions.

Below are {count} recent episode descriptions from "{name}". Study them carefully, \
then write a Description_Format.txt file that documents the observed patterns.

The file must cover these sections:
  FILE STRUCTURE   — what fields appear and in what order
  KEYWORDS         — format of the keywords line, if present
  OPENING          — how descriptions begin (exact phrasing patterns, not examples)
  BODY             — content, structure, typical length
  STYLE RULES      — tone, voice, punctuation, things consistently avoided
  SHOW NOTES FORMAT — how links and resources are listed

Rules for your output:
  - Describe patterns and rules only. Do not include any example sentences or \
sample text drawn from the episodes.
  - Be specific ("Begins with 'This week'" not "Uses a casual opener").
  - Note where patterns vary rather than inventing a rule that doesn't hold.
  - Keep it concise — this document will be read by an AI before every summary write.
  - Start your output with the title line in the format:
      [PODCAST NAME IN CAPS] - DESCRIPTION FORMAT

EPISODE DESCRIPTIONS:
---
{descriptions}
---
"""


def fetch_rss_descriptions(rss_url: str, count: int) -> list[tuple[str, str]]:
    with urllib.request.urlopen(rss_url, timeout=30) as response:
        content = response.read()

    root = ET.fromstring(content)
    ns = {"itunes": "http://www.itunes.com/dtds/podcast-1.0.dtd"}

    episodes = []
    for item in root.findall(".//item")[:count]:
        title = (item.findtext("title") or "").strip()
        description = (
            item.findtext("itunes:summary", namespaces=ns)
            or item.findtext("description")
            or ""
        ).strip()
        description = re.sub(r"<[^>]+>", "", description).strip()
        if title and description:
            episodes.append((title, description))

    return episodes


def read_rss_from_workflow(podcast_dir: Path) -> str | None:
    workflow = podcast_dir / "Workflow.txt"
    if not workflow.exists():
        return None
    match = re.search(r"RSS Feed:\s*(https?://\S+)", workflow.read_text(encoding="utf-8"))
    return match.group(1) if match else None


def main():
    parser = argparse.ArgumentParser(
        description="Draft Description_Format.txt from a podcast RSS feed"
    )
    parser.add_argument(
        "podcast_dir",
        help='Path to the podcast folder, e.g. "podcasts/My Podcast"',
    )
    parser.add_argument("--rss", help="RSS feed URL (overrides value in Workflow.txt)")
    parser.add_argument("--api-key", help="Google API key (overrides GOOGLE_API_KEY env var)")
    parser.add_argument(
        "--episodes",
        type=int,
        default=EPISODES_TO_ANALYZE,
        help=f"Number of recent episodes to analyse (default: {EPISODES_TO_ANALYZE})",
    )
    parser.add_argument(
        "--model",
        default=MODEL,
        help=f"Gemini model to use (default: {MODEL})",
    )
    args = parser.parse_args()

    podcast_dir = Path(args.podcast_dir).resolve()
    if not podcast_dir.exists():
        sys.exit(f"Error: '{podcast_dir}' does not exist.")

    api_key = args.api_key or os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        sys.exit("Error: Set the GOOGLE_API_KEY environment variable or pass --api-key.")

    rss_url = args.rss or read_rss_from_workflow(podcast_dir)
    if not rss_url:
        sys.exit(
            "Error: No RSS URL found. Pass --rss or add it to Workflow.txt as:\n"
            "  RSS Feed: https://..."
        )

    print(f"Fetching RSS: {rss_url}", flush=True)
    episodes = fetch_rss_descriptions(rss_url, args.episodes)
    if not episodes:
        sys.exit("Error: No episode descriptions found in the RSS feed.")
    print(f"Found {len(episodes)} episode(s). Analysing with Gemini...", flush=True)

    descriptions_text = "\n\n---\n\n".join(
        f"EPISODE: {title}\n{desc}" for title, desc in episodes
    )

    client = genai.Client(api_key=api_key)
    response = client.models.generate_content(
        model=args.model,
        contents=ANALYSIS_PROMPT.format(
            count=len(episodes),
            name=podcast_dir.name,
            descriptions=descriptions_text,
        ),
    )

    output_path = podcast_dir / "Prompts" / "Description_Format.txt"
    output_path.write_text(response.text, encoding="utf-8")
    print(f"Saved: {output_path}")
    print("Review the file and adjust anything that looks off before using.")


if __name__ == "__main__":
    main()
