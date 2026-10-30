---
name: gentruyen
description: Make a narrated fiction story video from a script plus the user's own images (e.g. AI images per ~8 s) in input/; language auto-detected (voice, cards, subtitles in the script's language), no archival search or fact-check, studio review stop before the final video; invoke with /gentruyen.
---

Read `AGENTS.md`, then `docs/STORY_MODE.md` at the workspace root (three directories above this file), and run its steps for the story the user put in `input/` (use `ingest --story --only NAME` when several are there). Story mode is separate from the archival workflow: no archival media search, no fact-check, no "(illustrative)" labels. The studio review (step 7) is a hard stop: open the studio and wait for the user's approval before exporting. Ask before any command that spends API credits (AI84 voice, ElevenLabs). Report in the user's language.
