# Podcast Summaries

A shared workspace for managing multiple podcast workflows. Each podcast lives in its own independent git repository under `podcasts/`. Shared tools live here at the root.

## Structure

```
Podcast Summaries/
  transcribe_episode.py       ← shared transcription script
  podcasts/
    ESA/                      ← Event Safety Podcast repo
    1 Player Podcast/         ← 1 Player Podcast repo
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
python transcribe_episode.py "path\to\audio.mp3" "podcasts\ESA\Transcripts\Episode 118 - Title.txt"
python transcribe_episode.py "path\to\audio.mp3" "podcasts\1 Player Podcast\Transcripts\1P_401_Title.txt"
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

1. Create a folder under `podcasts/` with the podcast name
2. Initialize a git repo inside it and connect it to GitHub
3. Set up the folder structure:
   ```
   podcasts/YourPodcast/
     Workflow.txt
     Prompts/
     Episode Summaries/
     Transcripts/
   ```
4. In `Workflow.txt`, include a note that this workflow is run from the parent `Podcast Summaries` folder and that the transcription script is at the root level
5. Reference the script using the path relative to the parent:
   ```
   python transcribe_episode.py "audio.mp3" "podcasts\YourPodcast\Transcripts\output.txt"
   ```

---

## Notes

- Audio files are excluded from all repos via `.gitignore`. Only transcripts and summaries are committed.
- Transcription quality depends on audio clarity. The 30-second overlap between chunks helps the model handle sentence boundaries smoothly.
- The script uses `gemini-2.5-flash-lite` by default. For higher accuracy on difficult audio, pass `--model gemini-2.5-pro`.
