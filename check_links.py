#!/usr/bin/env python3
"""
Check that URLs in Episode Summary files are still live.

Usage:
    python check_links.py "podcasts/My Podcast"   (one podcast)
    python check_links.py                          (all podcasts)
"""

import re
import sys
import time
import urllib.request
import urllib.error
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).parent
PODCASTS_DIR = ROOT / "podcasts"
TIMEOUT = 12
DELAY = 0.5
RETRY_DELAY = 3

# Realistic browser UA to avoid bot-blocking
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36"
)

# These status codes mean the server responded but won't serve bots --
# the page likely exists. Flag as a warning, not a dead link.
UNCERTAIN_CODES = {403, 406, 429}

URL_RE = re.compile(r'https?://[^\s|>)"\]]+')


def extract_urls(text: str) -> list[str]:
    urls = []
    for match in URL_RE.finditer(text):
        url = match.group().rstrip(".,)")
        urls.append(url)
    return urls


def check_url(url: str) -> tuple[str, int | None, str]:
    """Returns (verdict, status_code, message).
    verdict is 'ok', 'dead', or 'uncertain'.
    """
    headers = {"User-Agent": USER_AGENT}

    for attempt in range(2):
        for method in ("HEAD", "GET"):
            try:
                req = urllib.request.Request(url, headers=headers, method=method)
                with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
                    return "ok", resp.status, "OK"
            except urllib.error.HTTPError as e:
                if method == "HEAD" and e.code == 405:
                    continue
                if e.code in UNCERTAIN_CODES:
                    return "uncertain", e.code, e.reason
                if e.code in (404, 410):
                    return "dead", e.code, e.reason
                # Other 4xx/5xx -- retry once
                if attempt == 0:
                    break
                return "uncertain", e.code, e.reason
            except urllib.error.URLError as e:
                if attempt == 0:
                    time.sleep(RETRY_DELAY)
                    break
                return "uncertain", None, str(e.reason)
            except Exception as e:
                if attempt == 0:
                    time.sleep(RETRY_DELAY)
                    break
                return "uncertain", None, str(e)
        if attempt == 0:
            time.sleep(RETRY_DELAY)

    return "uncertain", None, "Failed after retry"


def check_podcast(podcast_dir: Path) -> tuple[list, list]:
    """Returns (dead, uncertain) link lists."""
    summaries_dir = podcast_dir / "Episode Summaries"
    if not summaries_dir.exists():
        return [], []

    url_to_files: dict[str, list[str]] = defaultdict(list)
    for f in sorted(summaries_dir.glob("*.txt")):
        for url in extract_urls(f.read_text(encoding="utf-8", errors="ignore")):
            url_to_files[url].append(f.name)

    dead, uncertain = [], []
    total = len(url_to_files)

    for i, (url, files) in enumerate(url_to_files.items(), 1):
        print(f"  [{i}/{total}] {url}", flush=True)
        verdict, status, msg = check_url(url)
        label = str(status) if status else "ERR"
        if verdict == "dead":
            for fname in files:
                dead.append((fname, url, label, msg))
        elif verdict == "uncertain":
            for fname in files:
                uncertain.append((fname, url, label, msg))
        time.sleep(DELAY)

    return dead, uncertain


def main():
    if len(sys.argv) > 1:
        podcast_dirs = [Path(sys.argv[1]).resolve()]
    else:
        if not PODCASTS_DIR.exists():
            sys.exit("No podcasts/ folder found.")
        podcast_dirs = sorted(
            d for d in PODCASTS_DIR.iterdir()
            if d.is_dir() and not d.name.startswith(".")
        )

    all_dead, all_uncertain = [], []
    for podcast_dir in podcast_dirs:
        print(f"\nChecking: {podcast_dir.name}", flush=True)
        dead, uncertain = check_podcast(podcast_dir)
        all_dead.extend(dead)
        all_uncertain.extend(uncertain)

    print("\n" + "=" * 60, flush=True)

    if all_dead:
        print(f"{len(all_dead)} dead link(s):\n")
        for fname, url, status, msg in all_dead:
            print(f"  [{status}] {url}")
            print(f"        in: {fname}")
    else:
        print("No dead links found.")

    if all_uncertain:
        print(f"\n{len(all_uncertain)} uncertain (bot-blocked or server error -- check manually):\n")
        for fname, url, status, msg in all_uncertain:
            print(f"  [{status}] {url}")
            print(f"        in: {fname}")

    return 1 if all_dead else 0


if __name__ == "__main__":
    sys.exit(main())
