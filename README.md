# Podcast Summaries

A shared workspace for managing multiple podcast workflows. Each podcast lives in its own independent git repository under `podcasts/`. Shared tools live here at the root.

## Structure

```
Podcast Summaries/
  transcribe_episode.py       ← shared transcription script
  podcasts/
    CoffeeBreak/              ← Coffee Break Podcast repo
    DeepDive/                 ← Deep Dive Podcast repo
    YourPodcast/              ← add more as needed
```

The `podcasts/` folder is ignored by this repo. Each podcast folder is its own git repo with its own GitHub remote, its own episode summaries, transcripts, and workflow.

---

## Transcription Script

`transcribe_episode.py` splits a podcast audio file into 12-minute chunks with 30-second overlaps, transcribes each chunk using the Google Gemini API, stitches the results into a single transcript, and removes the temporary audio fragments when done.

### Requirements

**Python package:**
```
pip install google-genai
```

**ffmpeg** — must be installed and available in your PATH:
- Windows: `winget install ffmpeg`
- Mac: `brew install ffmpeg`
- Linux: `sudo apt install ffmpeg`

**Google API key** — set as an environment variable:
```
# Windows (PowerShell — permanent, user-level)
[System.Environment]::SetEnvironmentVariable("GOOGLE_API_KEY", "your-key-here", "User")

# Mac/Linux
export GOOGLE_API_KEY="your-key-here"
```
Get a key at [Google AI Studio](https://aistudio.google.com/app/apikey).

### Usage

Run from this root folder, pointing the output into the appropriate podcast subfolder:

```
python transcribe_episode.py "path\to\audio.mp3" "podcasts\CoffeeBreak\Transcripts\Episode 12 - Title.txt"
python transcribe_episode.py "path\to\audio.mp3" "podcasts\DeepDive\Transcripts\DD_042_Title.txt"
```

The output folder is created automatically if it doesn't exist. The audio file itself is not moved or deleted.

### Options

| Argument | Description |
|---|---|
| `audio_file` | Path to the audio file (mp3, m4a, wav, etc.) |
| `output_file` | Output .txt path. Defaults to same name/location as audio if omitted. |
| `--model` | Gemini model to use. Default: `gemini-2.5-flash-lite` |
| `--api-key` | Pass API key directly instead of using the environment variable |

---

## Adding a New Podcast

Run the setup script to scaffold the folder, placeholder files, and initial git commit:

```
python create_podcast.py "My Podcast Name"
```

Then follow `New_Podcast_Setup.txt` for the interactive steps: gathering show info, generating the description format from the RSS feed, and connecting to GitHub.

To (re)generate `Description_Format.txt` from a podcast's published episodes:

```
python generate_description_format.py "podcasts/My Podcast"
```

Requires `GOOGLE_API_KEY` and an RSS URL set in the podcast's `Workflow.txt`.

### Manual folder structure

If setting up by hand instead of using the script:
   ```
   podcasts/YourPodcast/
     Workflow.txt
     Prompts/
       Description_Format.txt        ← layout and style rules, no sample text
       Episode_Summary_Template.txt  ← fill-in-the-blank structure
       New_Episode_Summary_Prompt.txt
       Transcription_Prompt.txt
     Episode Summaries/
     Transcripts/
   ```
4. In `Prompts/Description_Format.txt`, document the description structure for this podcast: field order, opening line convention, episode type variations, show notes format, and any style rules. Do not include sample output text.
5. In `Workflow.txt`, include a note that this workflow is run from the parent `Podcast Summaries` folder and that the transcription script is at the root level. Include a step to read `Prompts/Description_Format.txt` before writing any summary.
6. Reference the script using the path relative to the parent:
   ```
   python transcribe_episode.py "audio.mp3" "podcasts\YourPodcast\Transcripts\output.txt"
   ```

---

## Notes

- Audio files are excluded from all repos via `.gitignore`. Only transcripts and summaries are committed.
- Transcription quality depends on audio clarity. The 30-second overlap between chunks helps the model handle sentence boundaries smoothly.
- The script uses `gemini-2.5-flash-lite` by default. For higher accuracy on difficult audio, pass `--model gemini-2.5-pro`.
