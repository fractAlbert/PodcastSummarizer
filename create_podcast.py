#!/usr/bin/env python3
"""
Scaffold a new podcast repo under podcasts/.

Creates the standard folder structure and placeholder files, initialises a local
git repo, and makes an initial commit.  Run the interactive setup workflow
afterwards to fill in the [TODO] markers and connect to GitHub.

Usage:
    python create_podcast.py "My Podcast Name"
"""

import argparse
import subprocess
import sys
from pathlib import Path

PODCASTS_DIR = Path(__file__).parent / "podcasts"


# ── File content builders ──────────────────────────────────────────────────────

def _gitignore():
    return """\
.claude/

# Audio files (large; transcripts are tracked instead)
*.mp3
*.m4a
*.wav
*.aiff
*.aac
*.ogg
*.flac
*.wma
"""


def _podcast_config(name, folder):
    return f"""\
PODCAST NAME:    {name}
RSS FEED:        [TODO: add RSS feed URL]
GITHUB REPO:     [TODO: add GitHub repo URL]
HOSTS:           [TODO: Host Name (host), Co-host Name (co-host)]
TRANSCRIPT DIR:  podcasts\\{folder}\\Transcripts
EPISODE FORMAT:  [TODO: e.g. Episode N - Title  or  ShowCode_NNN_Title]
FILE FORMAT:     [TODO: e.g. Episode N - Title.txt  or  ShowCode_NNN_Title.txt]
"""


def _workflow(name):
    title = f"{name.upper()} - PODCAST-SPECIFIC WORKFLOW NOTES"
    sep = "=" * len(title)
    return f"""\
{title}
{sep}

Follow the generic Episode_Workflow.txt from the parent Podcast Summaries folder.
Connection details (RSS URL, GitHub repo, file naming) are in Podcast.config.

[TODO: Add any podcast-specific steps here, or replace this block with
"NO ADDITIONAL STEPS. The generic workflow applies fully to this podcast."

Examples of what belongs here:
  - Episode type identification (e.g. interview vs. solo vs. review)
  - Voice or presenter identification
  - Show notes search conventions (e.g. always search BGG for game links)
  - Filename quirks or naming conventions]

NOTES
-----
[TODO: add any recurring notes about this podcast's conventions]
"""


def _description_format(name):
    title = f"{name.upper()} - DESCRIPTION FORMAT"
    sep = "=" * len(title)
    return f"""\
{title}
{sep}

[TODO: Document the description format for this podcast.
       Include: field order, opening line convention, episode type variations,
       show notes format, length guidelines, and style rules.
       Do NOT include sample output text.

       Run generate_description_format.py to draft this automatically from the RSS feed
       if the show has 5 or more published episodes.]

FILE STRUCTURE
--------------
[TODO: describe the order and names of fields in a summary file]

KEYWORDS
--------
[TODO: what terms to draw from for the keywords line?]

OPENING
-------
[TODO: how does each description begin?]

BODY
----
[TODO: what goes in the body? How long?]

STYLE RULES
-----------
[TODO: tone, voice, punctuation rules, things to avoid]

SHOW NOTES FORMAT
-----------------
[TODO: how are links and resources formatted?]
"""


def _summary_template(name):
    title = f"{name.upper()} - EPISODE SUMMARY TEMPLATE"
    sep = "=" * len(title)
    return f"""\
{title}
{sep}

[TODO: Add a fill-in-the-blank structure for episode summaries,
       modelled on the format defined in Description_Format.txt.
       Use [BRACKETS] for fields to fill in. No sample text.]
"""


def _summary_prompt(name):
    title = f"{name.upper()} - NEW EPISODE SUMMARY PROMPT"
    sep = "=" * len(title)
    return f"""\
{title}
{sep}

Use the following prompt when generating a description for a new episode.

---PROMPT START---

You are writing a podcast episode description for {name}.

[TODO: Add 1-2 sentences about the show, its audience, and tone.]

Before writing, read Prompts/Description_Format.txt for this podcast's layout
and style rules. Do not invent a format.

OUTPUT FORMAT:
First line:  KEYWORDS: [comma-separated list of 8-12 relevant keywords]
Blank line
Then:        Episode description following Description_Format.txt

[TRANSCRIPT BELOW]

---PROMPT END---
"""


def _transcription_prompt(name):
    title = f"{name.upper()} - TRANSCRIPTION PROMPT"
    sep = "=" * len(title)
    return f"""\
{title}
{sep}

* Role: Act as a transcription assistant for {name}.
* Input: Review the attached audio file.
* Task: Create a complete word-for-word transcript of the audio.
* Formatting: Prefix each speaker change with a timestamp and speaker name:
    [HH:MM:SS] Speaker Name: [what they said]
* Rules:
    - Transcribe every word; include filler words (um, uh) if clearly audible
    - Do not paraphrase or summarize
    - Write [inaudible] for anything that cannot be made out
    - This clip may begin or end mid-sentence; transcribe whatever is present
"""


# ── Setup ──────────────────────────────────────────────────────────────────────

def slugify(name: str) -> str:
    return "".join(c for c in name if c.isalnum() or c in " -_.'").strip()


def create_podcast(name: str) -> Path:
    folder_name = slugify(name)
    podcast_dir = PODCASTS_DIR / folder_name

    if podcast_dir.exists():
        sys.exit(f"Error: '{podcast_dir}' already exists.")

    for subdir in ("Prompts", "Episode Summaries", "Transcripts"):
        (podcast_dir / subdir).mkdir(parents=True)

    files = {
        podcast_dir / ".gitignore":                                _gitignore(),
        podcast_dir / "Podcast.config":                            _podcast_config(name, folder_name),
        podcast_dir / "Workflow.txt":                              _workflow(name),
        podcast_dir / "Prompts" / "Description_Format.txt":       _description_format(name),
        podcast_dir / "Prompts" / "Episode_Summary_Template.txt": _summary_template(name),
        podcast_dir / "Prompts" / "New_Episode_Summary_Prompt.txt": _summary_prompt(name),
        podcast_dir / "Prompts" / "Transcription_Prompt.txt":     _transcription_prompt(name),
    }

    for path, content in files.items():
        path.write_text(content, encoding="utf-8")

    subprocess.run(["git", "init"], cwd=podcast_dir, check=True, capture_output=True)
    subprocess.run(["git", "add", "."], cwd=podcast_dir, check=True, capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", f"Initial commit: {name} podcast structure"],
        cwd=podcast_dir, check=True, capture_output=True,
    )

    return podcast_dir


def main():
    parser = argparse.ArgumentParser(
        description="Scaffold a new podcast repo under podcasts/",
        epilog="After running this, follow New_Podcast_Setup.txt to complete the setup.",
    )
    parser.add_argument("name", help='Podcast name, e.g. "Joe\'s Podcast Shack"')
    args = parser.parse_args()

    podcast_dir = create_podcast(args.name)

    print(f"\nCreated: {podcast_dir}")
    print("\nNext steps — see New_Podcast_Setup.txt for the full workflow:")
    print("  1. Provide the RSS feed URL and show details")
    print("  2. Run generate_description_format.py to draft the format file")
    print("  3. Fill in remaining [TODO] markers")
    print("  4. Add a GitHub remote and push")


if __name__ == "__main__":
    main()
