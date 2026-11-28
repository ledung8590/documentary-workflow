---
name: soat-lo-truyen
description: Checks a whole folder of new story scripts (the "Truyện Lính" batch from the Bienkich app) before any of them is built - reads every script completely, records what each story turns on, compares all of them with each other and with every published story, and runs storycheck. Use when the user types /soat-lo-truyen, or asks to check, review or "soát" a batch or folder of stories.
---

# Soát lô truyện (trước khi dựng bất kỳ truyện nào)

Reply to the user in Vietnamese. Do not edit, rename or delete any script: this skill only reads and records verdicts. Run from the workspace root with `.venv\Scripts\python.exe` (PY).

The argument is the folder with the new scripts (for example `C:\Users\Le Dung\Downloads\Military Chronicle`). Files ending in `_old.txt` are skipped.

1. `PY scripts/storycore.py --batch "<folder>"` and follow what it prints. It is a two-step job:
   - **Step 1, the heavy one:** for every script without a core, one fresh reader (a sub-agent on a cheap model is enough; several can run in parallel) reads the WHOLE script, first line to last, and records in 20-45 words what the story turns on: `--set-core "<file>" @<text file>`. Check that the reader reports the script's real number of lines; if it read less, run it again.
   - **Step 2, the light one:** when every script has a core, run the command again. One reader compares the cores of the batch with each other and with the earlier stories it lists, and records one verdict per script: `--verdict "<file>" different`, or `--verdict "<file>" same --with "<title or file>" --why "<max 30 words>"`. When two scripts of the batch repeat each other, the LATER one is "same".
   - "Same" means the same device or turning point with other names, places and jobs. A shared battle, season or the retreat itself does not count. The printed brief has the full rule: follow it, be strict and fair.
2. `PY scripts/storycore.py --batch "<folder>" --check` until every script has a verdict.
3. For every script: `PY scripts/storycheck.py "<script>" --corpus "<folder>"`. Count its `!!` lines by kind (shared phrases, names, motifs, fragments, same-opener runs). Do not fix them here: `/gentruyen` rewrites them when the story is built.
4. Report one table: script, what it turns on (one line), verdict (different / SAME as ...), storycheck `!!` by kind. Then say plainly which scripts can go to `/gentruyen` and which must be written again in the app (every "same"), and suggest an upload order that keeps the closest stories apart.

The verdicts are stored per script text in `stories/checked-cores.json`. `/gentruyen` takes them over when the script was not edited, so it does not read the story again for this check.
