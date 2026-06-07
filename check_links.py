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
TIMEOUT = 10
DELAY = 0.3

URL_RE = re.compile(r'https?://[^\s|>)"\]]+')


def extract_urls(text: str) -> list[str]:
    urls = []
    for match in URL_RE.finditer(text):
        url = match.group().rstrip(".,)")
        urls.append(url)
    return urls


def check_url(url: str) -> tuple[int | None, str]:
    headers = {"User-Agent": "Mozilla/5.0 (compatible; podcast-link-checker/1.0)"}
    for method in ("HEAD", "GET"):
        try:
            req = urllib.request.Request(url, headers=headers, method=method)
            with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
                return resp.status, "OK"
        except urllib.error.HTTPError as e:
            if method == "HEAD" and e.code == 405:
                continue
            return e.code, e.reason
        except urllib.error.URLError as e:
            return None, str(e.reason)
        except Exception as e:
            return None, str(e)
    return None, "Failed"


def check_podcast(podcast_dir: Path) -> list[tuple[str, str, int | None, str]]:
    summaries_dir = podcast_dir / "Episode Summaries"
    if not summaries_dir.exists():
        return []

    url_to_files: dict[str, list[str]] = defaultdict(list)
    for f in sorted(summaries_dir.glob("*.txt")):
        for url in extract_urls(f.read_text(encoding="utf-8", errors="ignore")):
            url_to_files[url].append(f.name)

    broken = []
    total = len(url_to_files)

    for i, (url, files) in enumerate(url_to_files.items(), 1):
        print(f"  [{i}/{total}] {url}", flush=True)
        status, msg = check_url(url)
        if status is None or status >= 400:
            label = str(status) if status else "ERR"
            for fname in files:
                broken.append((fname, url, label, msg))
        time.sleep(DELAY)

    return broken


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

    all_broken = []
    for podcast_dir in podcast_dirs:
        print(f"\nChecking: {podcast_dir.name}", flush=True)
        broken = check_podcast(podcast_dir)
        all_broken.extend(broken)

    print("\n" + "=" * 60, flush=True)
    if not all_broken:
        print("All links OK.")
    else:
        print(f"{len(all_broken)} broken link(s):\n")
        for fname, url, status, msg in all_broken:
            print(f"  [{status}] {url}")
            print(f"        in: {fname}")

    return 1 if all_broken else 0


if __name__ == "__main__":
    sys.exit(main())
