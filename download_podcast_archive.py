#!/usr/bin/env python3
"""
Download all episodes, artwork, and RSS feed for a podcast archive.

Usage:
    python download_podcast_archive.py <rss_url> <output_dir>

Example:
    python download_podcast_archive.py https://feed.podbean.com/pensonthego/feed.xml "podcasts/Pens on the Go"
"""

import sys
import re
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path


def download(url: str, dest: Path, label: str) -> None:
    if dest.exists():
        print(f"  [skip] {label} (already exists)")
        return
    print(f"  Downloading {label}...", flush=True)
    urllib.request.urlretrieve(url, dest)
    print(f"  Saved: {dest.name}")


def main():
    if len(sys.argv) < 3:
        sys.exit(f"Usage: python {sys.argv[0]} <rss_url> <output_dir>")

    rss_url = sys.argv[1]
    out_dir = Path(sys.argv[2])

    episodes_dir = out_dir / "Episodes"
    artwork_dir = out_dir / "Artwork"
    episodes_dir.mkdir(parents=True, exist_ok=True)
    artwork_dir.mkdir(parents=True, exist_ok=True)

    # Save RSS feed
    rss_path = out_dir / "feed.xml"
    print("Fetching RSS feed...")
    with urllib.request.urlopen(rss_url) as resp:
        rss_data = resp.read()
    rss_path.write_bytes(rss_data)
    print(f"  Saved: feed.xml")

    # Parse feed
    root = ET.fromstring(rss_data)
    ns = {"itunes": "http://www.itunes.com/dtds/podcast-1.0.dtd"}
    channel = root.find("channel")

    # Artwork
    image = channel.find("image")
    if image is not None:
        art_url = image.findtext("url")
    else:
        itunes_image = channel.find("itunes:image", ns)
        art_url = itunes_image.get("href") if itunes_image is not None else None

    if art_url:
        ext = Path(art_url.split("?")[0]).suffix or ".jpg"
        art_path = artwork_dir / f"artwork{ext}"
        print("\nDownloading artwork...")
        download(art_url, art_path, "artwork")

    # Episodes
    items = channel.findall("item")
    print(f"\nDownloading {len(items)} episodes...")
    for i, item in enumerate(reversed(items), 1):
        title = item.findtext("title", "").strip()
        enclosure = item.find("enclosure")
        if enclosure is None:
            print(f"  [skip] {title} (no enclosure)")
            continue
        url = enclosure.get("url", "").split("?")[0]
        filename = Path(url).name
        dest = episodes_dir / filename
        download(url, dest, f"[{i:02d}/{len(items)}] {title}")

    print("\nDone.")


if __name__ == "__main__":
    main()
