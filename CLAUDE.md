# Podcast Summaries — Project Instructions

## Repository Structure

This is the parent repository. Each podcast lives in its own sub-repository under `podcasts/`:

- `podcasts/ESA/` — Event Safety Podcast (own git repo: fractAlbert/ESA-Podcast, branch: master)
- `podcasts/1 Player Podcast/` — 1 Player Podcast (own git repo: fractAlbert/1PlayerPodcastSummaries, branch: main)

Commits and pushes for episode files (transcripts, summaries) go to the **sub-repository**, not the parent.

All changes, in the parent and every sub-repository, go through a pull request. Never push directly to `master` or `main`. Use the `/push` procedure: new branch, commit, push the branch, open a PR, and the user merges it.

## Episode Workflow

Read `Episode_Workflow.txt` for the full step-by-step process. Read the podcast's `Podcast.config` and `Workflow.txt` for podcast-specific settings (RSS URL, GitHub repo, file naming).

Before writing any summary, read the podcast's `Prompts/Description_Format.txt` and `Prompts/Episode_Summary_Template.txt`. Do this even if you think you remember the format from earlier in the session.

## Transcription

Edited audio files are in `C:\Users\fract\Documents\Audacity\Output\`

Run from the parent repo root:
```
python transcribe_episode.py "path\to\audio.mp3" "path\to\output.txt"
```

Chunk files are cached in `chunks/` at the parent repo root. If a chunk `.txt` already exists, the script skips the API call and re-stitches only — much faster.

### Hallucination detection

Gemini sometimes repeats a phrase thousands of times, producing a line of 100KB+.

**Detect:** After transcription, check file size (normal: 10–80KB; suspicious: >200KB) and max line length:
```powershell
$lines = Get-Content $f
($lines | Measure-Object -Property Length -Maximum).Maximum
```

**Find the bad chunk:** List chunk file sizes — the large one is the culprit.

**Fix:** Find a distinctive phrase near the start of the repeated section, locate its second occurrence, and truncate there:
```powershell
$first  = $chunk.IndexOf($phrase)
$second = $chunk.IndexOf($phrase, $first + $phrase.Length)
$clean  = $chunk.Substring(0, $second).TrimEnd()
Set-Content -Path $chunkPath -Value $clean -Encoding UTF8 -NoNewline
```
Then delete the stitched output file and re-run `transcribe_episode.py`. It re-stitches from cached chunks without re-calling the API.

## Guest Database (ESA)

`podcasts/ESA/guests.csv` tracks every ESA guest with canonical name, title, organization, episode numbers, and links. Before writing the Guests section of any ESA summary, read this file. Use the canonical name spelling from the database rather than the transcript. See `podcasts/ESA/Workflow.txt` for the full lookup and update procedure.

`podcasts/ESA/appearances.csv` indexes each guest by the episode they appeared in. During the RSS sync, compare each published guest name against that episode's appearance rows, never by name alone. Similar names can be different people, so a rename that would collide with another row is marked `review` and confirmed with the user, never merged automatically.

## Rules

### Cross-episode references
Before citing another episode to justify a name spelling, guest title, or fact — e.g. "this matches Episode 122's roster" — **read that episode's file first** and confirm it actually supports the claim. If it cannot be verified, say so rather than asserting it.

### Summary content
Describe **what was discussed**, not who said what. Speaker attribution belongs only in the Guests block. The body should read as a description of episode content, not a transcript of the conversation.

### Names
The RSS feed is authoritative for guest and episode names. When a name in a local file differs from the RSS feed, fix the local file to match — don't ask for confirmation.

### File rewrites
Before finishing any file rewrite, do a diff pass to confirm no existing content was silently dropped.
