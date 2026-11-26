---
name: gentruyen
description: Makes a narrated fiction story video from a script plus generated images, language auto-detected, with a studio review stop before the final video. Use when the user types /gentruyen or asks to make a story video.
---

Read `GEMINI.md` (how this workspace maps onto Antigravity) and `AGENTS.md`, then follow `docs/STORY_MODE.md` step by step (and `docs/STORY_WRITING.md`, `docs/ZIMAGE.md` when a step names them). Do the work; do not only explain it.

- Story path only: no archival search, no `FACTS.md`, no `doc.py plan`, no `templates/archival/`.
- Read the lessons index named in `GEMINI.md` first; entries marked `[archival]` do not apply.
- Script checks before any voice credit: `PY scripts\storycheck.py <script>` and `/kiem-duyet-kich-ban <script> --truyen --auto`. Fix the script yourself and report before/after. The `same skeleton` finding is the exception: follow docs/STORY_WRITING.md "A new frame every story" (a script from before 2026-11-26 goes back to the user's story app; a newer one gets a new opening and outro). A title equal to an earlier story is told to the user first.
- Before the review: `PY scripts\gate.py JOB studio` until PASS, then `PY scripts\doc.py studio JOB`. Tell the user in Vietnamese what to check and END THE TURN.
- After the user approves in chat: `PY scripts\export.py JOB`, then `PY scripts\gate.py JOB deliver --video FILE` until PASS.

Always reply in Vietnamese; the story's own text follows the script language.

Delegate: this skill explicitly asks for sub-agents and parallel agent work for the steps listed in `AGENTS.md` ("Sub-agents are explicitly requested here"); do not do media search, group editing or reviews alone when an agent tool exists.
