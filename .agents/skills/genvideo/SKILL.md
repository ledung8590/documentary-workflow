---
name: genvideo
description: Produces a historical-analysis documentary from real archival media (photos, film, maps) from a narration script in input/, with a studio review stop before the final video. Use when the user types /genvideo or /gendoc, or asks to make an archival documentary film from a script.
---

Read `GEMINI.md` (how this workspace maps onto Antigravity) and `AGENTS.md`, then follow `docs/WORKFLOW.md` from section 0 as far as its built stages go. Do the work; do not only explain it.

1. Start gate (WORKFLOW 0): read the lessons index named in `GEMINI.md`, and run every command that may ask for permission while the user is still there.
2. Script review: `/kiem-duyet-kich-ban <script> --auto`. Fix the script yourself and report the before/after table. Never ask before fixing the script (user rule 2026-11-12, confirmed 2026-11-21). Finish the fact check before `tts --run`.
3. Voice, edit plan, media, scenes, maps, music and SFX as WORKFLOW 3a–8, built through `doc.py plan JOB` and `templates/archival/` (never `doc.py story`).
4. `PY scripts\gate.py JOB plan` until PASS, then the draft render: `PY scripts\doc.py build JOB --only picture`.
5. `PY scripts\gate.py JOB studio` until PASS, then `PY scripts\doc.py studio JOB`. Tell the user in Vietnamese what to check and END THE TURN. This is the only stop.
6. After the user approves in chat: `PY scripts\export.py JOB`, the thumbnail and description (WORKFLOW 13), `PY scripts\gate.py JOB deliver --video FILE` until PASS. Then deliver and ask whether the film is uploaded.

Always reply in Vietnamese; the film's own text follows the script language.
