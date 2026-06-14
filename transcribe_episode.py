#!/usr/bin/env python3
"""
Podcast Transcription Script

Splits an audio file into overlapping chunks, transcribes each chunk using the
Google Gemini API, stitches the results into a single transcript, and saves
the chunk files for review.

Chunks are kept in a {output_stem}_chunks/ folder next to the transcript so
individual chunks can be re-transcribed if needed. To redo a single chunk:
  1. Delete its .txt file from the _chunks/ folder.
  2. Re-run the script with the same arguments.
  3. Only missing .txt files will be re-transcribed; all are then re-stitched.

Only replace a chunk when it is genuinely unusable — e.g. the same sentence
repeating hundreds of times (a Gemini hallucination loop). Small duplicate
passages near chunk boundaries are normal stitching artifacts and can stay.
If a chunk cannot be recovered, replace its .txt with a placeholder note:
  [SEGMENT UNAVAILABLE — transcription failed (approx. minutes X–Y)]

Requirements:
    pip install google-genai
    ffmpeg installed and available in PATH  (https://ffmpeg.org)

Usage:
    python transcribe_episode.py "path\to\audio.mp3" "path\to\output.txt"

    Examples:
    python transcribe_episode.py audio.mp3 "podcasts\ESA\Transcripts\Episode 118 - Title.txt"
    python transcribe_episode.py audio.mp3 "podcasts\1 Player Podcast\Transcripts\1P_401_Title.txt"

API Key:
    Set the GOOGLE_API_KEY environment variable before running, or pass --api-key.
"""

import json
import os
import re
import sys
import time
import argparse
import subprocess
from pathlib import Path

from google import genai

# ── Configuration ──────────────────────────────────────────────────────────────
CHUNK_MINUTES = 12
OVERLAP_SECONDS = 30
MODEL = "gemini-2.5-flash-lite"

TRANSCRIPTION_PROMPT = """\
You are a transcription assistant for a podcast.

Transcribe this audio clip word-for-word. Format each speaker change like this:
[HH:MM:SS] Speaker Name: [what they said]

Example:
[00:00:15] Host: Welcome to the podcast.
[00:01:02] Guest: Thanks for having me.

Rules:
- Transcribe every word spoken; include filler words (um, uh) if clearly audible
- Do not paraphrase or summarize — capture everything said
- If a word is inaudible, write [inaudible]
- This clip may begin or end mid-sentence; transcribe whatever audio is present
"""
# ──────────────────────────────────────────────────────────────────────────────


def get_duration(path: Path) -> float:
    result = subprocess.run(
        ["ffprobe", "-v", "quiet", "-print_format", "json", "-show_streams", str(path)],
        capture_output=True, text=True, check=True,
    )
    data = json.loads(result.stdout)
    for stream in data["streams"]:
        if "duration" in stream:
            return float(stream["duration"])
    raise ValueError(f"Could not read duration from {path}")


def split_audio(audio_path: Path, chunk_dir: Path) -> list[tuple[Path, float, float]]:
    """Split audio into overlapping chunks. Returns list of (chunk_path, start_sec, end_sec)."""
    duration = get_duration(audio_path)
    chunk_sec = CHUNK_MINUTES * 60
    chunks = []
    start = 0.0
    n = 1

    while start < duration:
        content_end = min(start + chunk_sec, duration)
        clip_end = min(content_end + OVERLAP_SECONDS, duration)

        chunk_path = chunk_dir / f"chunk_{n:03d}.mp3"
        subprocess.run(
            [
                "ffmpeg", "-y",
                "-i", str(audio_path),
                "-ss", str(start),
                "-t", str(clip_end - start),
                "-acodec", "libmp3lame", "-q:a", "4",
                str(chunk_path),
            ],
            capture_output=True, check=True,
        )

        chunks.append((chunk_path, start, clip_end))
        start = content_end
        n += 1

    return chunks, duration


def transcribe_chunk(client, model_name: str, chunk_path: Path, num: int, total: int) -> str:
    print(f"  Uploading chunk {num}/{total}...", flush=True)
    uploaded = client.files.upload(file=str(chunk_path))

    while uploaded.state.name == "PROCESSING":
        time.sleep(3)
        uploaded = client.files.get(name=uploaded.name)

    if uploaded.state.name != "ACTIVE":
        raise RuntimeError(f"Upload failed for chunk {num} (state: {uploaded.state.name})")

    print(f"  Transcribing chunk {num}/{total}...", flush=True)
    response = client.models.generate_content(
        model=model_name,
        contents=[uploaded, TRANSCRIPTION_PROMPT],
    )

    client.files.delete(name=uploaded.name)
    return response.text


def adjust_timestamps(text: str, offset_sec: float) -> str:
    """Shift [HH:MM:SS] timestamps by offset_sec to reflect position in full episode."""
    def shift(m):
        total = int(m.group(1)) * 3600 + int(m.group(2)) * 60 + int(m.group(3)) + round(offset_sec)
        h, remainder = divmod(total, 3600)
        mn, s = divmod(remainder, 60)
        return f"[{h:02d}:{mn:02d}:{s:02d}]"
    return re.sub(r'\[(\d{2}):(\d{2}):(\d{2})\]', shift, text)


def deduplicate_chunk(text: str, window: int = 6) -> str:
    """Truncate a chunk at the point where a repeating line sequence begins."""
    lines = text.splitlines()
    for i in range(len(lines) - window):
        seq = lines[i:i + window]
        for j in range(i + window, len(lines) - window + 1):
            if lines[j:j + window] == seq:
                return "\n".join(lines[:j]).rstrip()
    return text


def stitch(transcripts: list[str]) -> str:
    """Join consecutive transcripts, removing duplicated text from overlapping audio."""
    if not transcripts:
        return ""

    result = transcripts[0]

    for curr in transcripts[1:]:
        window = 800
        tail = result[-window:]
        head = curr[:window]

        tail_words = tail.split()
        head_words = head.split()

        join_point = None
        for seq_len in range(min(25, len(tail_words), len(head_words)), 4, -1):
            for ti in range(len(tail_words) - seq_len + 1):
                seq = tail_words[ti : ti + seq_len]
                for hi in range(len(head_words) - seq_len + 1):
                    if head_words[hi : hi + seq_len] == seq:
                        join_point = (" ".join(seq), ti, hi)
                        break
                if join_point:
                    break
            if join_point:
                break

        if join_point:
            phrase, _, hi = join_point
            head_char = head.find(phrase)
            overlap_start_in_result = len(result) - window + tail.find(phrase)
            result = result[:overlap_start_in_result].rstrip() + "\n" + curr[head_char:].lstrip()
        else:
            result = result.rstrip() + "\n\n" + curr.lstrip()

    return result


def main():
    parser = argparse.ArgumentParser(description="Transcribe a podcast episode via Google Gemini API")
    parser.add_argument("audio_file", help="Path to the audio file (mp3, m4a, wav, etc.)")
    parser.add_argument("output_file", nargs="?", help="Output .txt path (default: same name as audio)")
    parser.add_argument("--api-key", help="Google API key (overrides GOOGLE_API_KEY env var)")
    parser.add_argument("--model", default=MODEL, help=f"Gemini model (default: {MODEL})")
    args = parser.parse_args()

    audio_path = Path(args.audio_file).resolve()
    if not audio_path.exists():
        sys.exit(f"Error: File not found: {audio_path}")

    api_key = args.api_key or os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        sys.exit("Error: Set the GOOGLE_API_KEY environment variable or pass --api-key.")

    output_path = (
        Path(args.output_file).resolve() if args.output_file else audio_path.with_suffix(".txt")
    )

    client = genai.Client(api_key=api_key)

    chunk_dir = output_path.parent / (output_path.stem + "_chunks")
    chunk_dir.mkdir(parents=True, exist_ok=True)

    print(f"Audio:  {audio_path.name}")
    print(f"Output: {output_path}")
    print(f"Chunks: {chunk_dir}")

    print("Splitting audio into chunks...")
    chunks, duration = split_audio(audio_path, chunk_dir)
    print(
        f"Duration: {duration / 60:.1f} min  ->  {len(chunks)} chunk(s) "
        f"of ~{CHUNK_MINUTES} min each (with {OVERLAP_SECONDS}s overlap)"
    )

    transcripts = []
    for i, (chunk_path, start_sec, _) in enumerate(chunks, 1):
        chunk_txt = chunk_path.with_suffix(".txt")
        if chunk_txt.exists():
            print(f"  [skip] Chunk {i}/{len(chunks)} (transcript already exists)", flush=True)
            t = chunk_txt.read_text(encoding="utf-8")
        else:
            t = transcribe_chunk(client, args.model, chunk_path, i, len(chunks))
            t = deduplicate_chunk(t)
            chunk_txt.write_text(t, encoding="utf-8")
            print(f"  Chunk {i} complete.", flush=True)
        transcripts.append(adjust_timestamps(t, start_sec))

    print("Stitching transcript...", flush=True)
    full_transcript = stitch(transcripts)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(full_transcript, encoding="utf-8")
    print(f"\nDone. Transcript saved to:\n  {output_path}")
    print(f"Chunks kept in:        {chunk_dir}")
    print("To redo a chunk: delete its .txt from the chunks folder and re-run.")


if __name__ == "__main__":
    main()
