# Podcast Summaries

A shared workspace for managing multiple podcast workflows with an AI coding assistant.

![Podcast Summaries UI](assets/screenshots.png)

---

## Introduction

This workspace keeps the tools and podcasts organised in one place. Each podcast
lives in its own independent git repository under `podcasts/`. The shared tools
live here at the root.

**An AI coding assistant is the main interface.** You give it a file and a direction —
"transcribe this episode", "run the summary workflow", "set up a new podcast called X" —
and it handles the rest: transcribing audio, syncing descriptions from the RSS feed,
writing the episode summary, looking up URLs, and committing the results.

Any AI with filesystem and terminal access works — Claude Code, GitHub Copilot, and
Gemini Code Assist are all good fits. A browser-only chat AI won't have the access
needed to run scripts or commit files.

Several tasks can also be run directly as Python scripts or through the web UI
(see [Technical](#technical)).

---

## Installing

**Python package** (for transcription and format generation):
```
pip install google-genai flask
```

**ffmpeg** — required for audio transcription; must be on your PATH:
- Windows: `winget install ffmpeg`
- Mac: `brew install ffmpeg`
- Linux: `sudo apt install ffmpeg`

**Google API key** — required for transcription and format generation:
```
# Windows (PowerShell — permanent, user-level)
[System.Environment]::SetEnvironmentVariable("GOOGLE_API_KEY", "your-key-here", "User")

# Mac/Linux
export GOOGLE_API_KEY="your-key-here"
```
Get a key at [Google AI Studio](https://aistudio.google.com/app/apikey).

---

## Using

Open this folder in your AI assistant and tell it what you need:

| What you say | What the AI does |
|---|---|
| "I have a new episode to transcribe: [path]" | Transcribes the audio and saves the transcript |
| "Run the summary workflow" | Syncs RSS descriptions, writes the episode summary, looks up URLs, commits |
| "Create a new podcast repo called [Name]" | Scaffolds the folder, gathers show info, generates the format file, connects GitHub |
| "Regenerate the description format for [podcast]" | Re-analyses the RSS feed and updates `Description_Format.txt` |

The generic episode steps live in `Episode_Workflow.txt` at the root. Each podcast
has a `Podcast.config` (RSS URL, hosts, file naming) and a `Workflow.txt` for any
podcast-specific additions. `Prompts/Description_Format.txt` tells the AI how that
show's descriptions are structured — no sample text, just rules and layout.

---

## Web UI

Double-click **`Launch.bat`** (or run `python app.py`) to open the web interface.
It provides point-and-click access to the most common tasks without needing an AI assistant:

| Card | What it does |
|---|---|
| **Transcribe Episode** | Select an audio file and transcribe it with Gemini |
| **Create New Podcast** | Scaffold a new podcast folder and starter files |
| **Generate Description Format** | Draft format rules by analysing published RSS episodes |
| **Social Media Snippets** | Generate ready-to-post Twitter/X, LinkedIn, and Newsletter copy from an episode summary |
| **Search Transcripts** | Full-text search across all transcripts, optionally filtered to one podcast |
| **Check Links** | Scan episode summaries for dead or unreachable URLs |

Long-running tasks (transcription, link checking) stream output live to a console
panel at the bottom of the page.

---

## Technical

### How transcription works

`transcribe_episode.py` splits the audio into 12-minute chunks with 30-second overlaps,
sends each chunk to the Gemini API, stitches the results back together, and removes the
temporary audio files. The overlap helps handle words that fall on a chunk boundary.
Default model: `gemini-2.5-flash-lite`. Pass `--model gemini-2.5-pro` for higher
accuracy on difficult audio.

### Scripts you can run directly

These tasks can be run without an AI assistant (or invoked from the web UI):

**Transcribe an episode:**
```
python transcribe_episode.py "path\to\audio.mp3" "podcasts\MyPodcast\Transcripts\output.txt"
```

**Scaffold a new podcast repo:**
```
python create_podcast.py "My Podcast Name"
```
Creates the folder structure, placeholder files, and an initial git commit under
`podcasts/`. Follow `New_Podcast_Setup.txt` to complete the setup.

**Generate or refresh a podcast's description format:**
```
python generate_description_format.py "podcasts/My Podcast"
```
Fetches the RSS feed (reads the URL from `Podcast.config`), analyses the last 10
published episode descriptions with Gemini, and writes `Prompts/Description_Format.txt`.
Requires `GOOGLE_API_KEY` and the RSS URL set in `Podcast.config`.

**Generate social media snippets:**
```
python generate_social.py "podcasts/My Podcast/Episode Summaries/Episode 10 - Title.txt"
python generate_social.py "..." --platforms twitter newsletter
```
Reads an episode summary and writes Twitter/X, LinkedIn, and Newsletter posts using
Gemini. Requires `GOOGLE_API_KEY`.

**Search transcripts:**
```
python search_transcripts.py "search term"
python search_transcripts.py "search term" "podcasts/My Podcast"
```
Case-insensitive search across all transcript files. Optionally scope to one podcast.

**Check links:**
```
python check_links.py                        # all podcasts
python check_links.py "podcasts/My Podcast"  # one podcast
```
Scans every episode summary for URLs and makes a live HTTP request to each one.
Reports dead links (404/410) and uncertain ones (bot-blocked or server errors).

### Folder structure

```
Podcast Summaries/
  app.py                              <- web UI (run with Launch.bat)
  transcribe_episode.py               <- shared transcription script
  create_podcast.py                   <- scaffold a new podcast repo
  generate_description_format.py      <- draft Description_Format.txt from RSS
  generate_social.py                  <- generate social media posts from a summary
  search_transcripts.py               <- full-text search across transcripts
  check_links.py                      <- verify URLs in episode summaries
  Episode_Workflow.txt                <- generic episode workflow (all podcasts)
  New_Podcast_Setup.txt               <- interactive setup workflow for your AI assistant
  podcasts/
    MyPodcast/                        <- independent git repo
      Podcast.config                  <- RSS URL, GitHub URL, hosts, file naming
      Workflow.txt                    <- podcast-specific steps and notes
      Prompts/
        Description_Format.txt       <- layout/style rules (no sample text)
        Episode_Summary_Template.txt
        New_Episode_Summary_Prompt.txt
        Transcription_Prompt.txt
      Episode Summaries/
      Transcripts/
```

The `podcasts/` folder is ignored by this repo. Audio files are excluded from
all repos via `.gitignore` — only transcripts and summaries are committed.
