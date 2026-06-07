---
name: feedback_summary_format
description: Each podcast has its own description format; always read the podcast-specific Prompts/ folder before writing a summary
metadata:
  type: feedback
---

Each podcast under `podcasts/` has its own `Prompts/` folder containing `Episode_Summary_Template.txt` and `New_Episode_Summary_Prompt.txt`. These define the tone, structure, and style for that show's episode descriptions.

**Why:** Each podcast has a distinct format. Writing in a generic style or from memory risks getting the tone, opening line, show notes format, or voice attribution wrong.

**How to apply:** Before writing any episode summary, read the target podcast's `Prompts/Description_Format.txt` (layout and rules, no examples) and `Prompts/Episode_Summary_Template.txt`. Do this even if you think you remember the format from earlier in the session. The `Description_Format.txt` files are the authoritative structure reference; they intentionally contain no sample text to avoid bleed-through into outputs.

The RSS download at the start of each session (workflow steps 1-4) is intentionally designed to pull the latest published descriptions into `Episode Summaries/`. Albert edits summaries before publishing, so the published versions in the feed are the authoritative style reference. After downloading, compare the saved summaries against the feed to pick up any format corrections before writing the new one.
