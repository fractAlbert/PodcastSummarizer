#!/usr/bin/env python3
"""
Search across podcast transcripts.

Usage:
    python search_transcripts.py "query"
    python search_transcripts.py "query" "podcasts/My Podcast"
"""

import re
import sys
from pathlib import Path

ROOT = Path(__file__).parent
PODCASTS_DIR = ROOT / "podcasts"


def search_podcast(pattern: re.Pattern, podcast_dir: Path) -> int:
    transcripts_dir = podcast_dir / "Transcripts"
    if not transcripts_dir.exists():
        return 0

    total = 0
    for transcript_file in sorted(transcripts_dir.glob("*.txt")):
        lines = transcript_file.read_text(encoding="utf-8", errors="ignore").splitlines()
        matches = [line.strip() for line in lines if pattern.search(line)]
        if matches:
            print(f"\n── {podcast_dir.name} / {transcript_file.name} ({len(matches)} match(es))")
            for line in matches:
                print(f"  {line}")
            total += len(matches)

    return total


def main():
    if len(sys.argv) < 2:
        sys.exit("Usage: python search_transcripts.py \"query\" [\"podcasts/My Podcast\"]")

    query = sys.argv[1]
    pattern = re.compile(re.escape(query), re.IGNORECASE)

    if len(sys.argv) > 2:
        podcast_dirs = [Path(sys.argv[2]).resolve()]
    else:
        if not PODCASTS_DIR.exists():
            sys.exit("No podcasts/ folder found.")
        podcast_dirs = sorted(
            d for d in PODCASTS_DIR.iterdir()
            if d.is_dir() and not d.name.startswith(".")
        )

    print(f'Searching for "{query}"...', flush=True)
    total = sum(search_podcast(pattern, d) for d in podcast_dirs)

    print(f'\n{"=" * 60}')
    print(f"{total} match(es) found." if total else f'No matches found for "{query}".')


if __name__ == "__main__":
    main()
