---
name: genvideo
description: Same as /gendoc - produce a historical-analysis documentary from real archival media (photos, film, maps) from a script in input/, with a studio review stop before the final video; invoke with /genvideo.
---

Read `AGENTS.md` then `docs/WORKFLOW.md` at the workspace root (three directories above this file). Execute the archival workflow up to the last built stage: real archival media, built through the edit-plan toolkit (`doc.py plan JOB` → `templates/archival/`), never the story layout (`doc.py story`, one picture per sentence). Stage 10 (studio review) is a hard stop: open the studio and wait for the user's approval before exporting with `scripts/export.py`. AI84/ElevenLabs spend is pre-authorized: dry-run, then `--run` without asking. Read stage docs progressively. ALWAYS reply to the user in Vietnamese (every chat message, progress note, recap, question and button label), even when the script, docs or tool output are English: the user does not read English (user rule 2026-11-03).
