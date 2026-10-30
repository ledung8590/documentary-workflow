# Story mode (`/gentruyen`)

A **fiction story** narrated over the user's own images (for example AI images made one per ~8 s of an earlier narration). Separate from the archival workflow (`/gendoc`, `/genvideo`): no archival search, no fact-check, no "(illustrative)" labels, no licence rows for the user's images.

## Input (`input/`)
Either layout:
- **A (side by side):** `input/<name>.txt` (script) + `input/<name>/` (images `001.png`, `002.png`…) + optional `input/<name>.srt` + optional `input/<name>_… scene.txt` (prompts).
- **B (one folder):** `input/<name>/` with `script.txt` (or the only script `.txt`), the images, optional one `.srt`, optional `*scene*.txt` / `*prompt*.txt`.

The `.srt` here is the **timing the images were made for** (one image per `seconds_per_image` of it, default: its length ÷ image count, rounded to 0.5 s, i.e. 8 s for Whisk scenes); it is not used as narration. Without it the images are spread evenly over the new voice. The prompts file (JSON lines `{"scenes 12": "…"}` or one prompt per line) only fills each clip's `need` text. Folders starting with `_` are ignored (old jobs).

Optional `input/<name>.json` (or `job.json` in the folder): `title`, `language`, `voice`, and `"story": {"grade": "archival|film|modern|none", "seconds_per_image": 8, "music": true, "card_sfx": true, "title_card": true}`.

## Language and market
Like `/genvideo`: `ingest` detects the script language (vi / es / en; `language` overrides) and picks the narrator (`VOICES` in `doc.py`: en Brian, es Alberto, vi Tung Dang). Every on-screen word follows it: title, `CHAPTER`/`CHƯƠNG`/`CAPÍTULO`, cards, subtitles.

## Steps
1. `PY scripts/doc.py ingest --story [--only NAME]` → `projects/<id>/` with `genre: story`.
2. Read the story; write a short `STORY.md` (chapters, emotional curve, title). Fiction: no `FACTS.md`. Chapters come from `# Heading` lines in the script; if it has none, propose chapter points to the user (or add them to `sentences.json` chapters) before voicing.
3. `split JOB` → review emotions → `tts JOB` (dry run, credits) → **ask** → `tts JOB --run` → `assemble JOB`.
4. `PY scripts/doc.py story JOB`: one clip per image anchored to the word where its part of the story starts (word alignment with the image SRT), title card after the opening paragraph, a chapter card in each chapter pause, music beds per chapter (mood from the sentences' emotions, tiled with crossfades, ~13 dB under the voice), card SFX at measured levels, grain + burned-in subtitles. Rerun after every `assemble`.
5. Refine with `doc.py ops` / the studio MCP tools: date tags, lower thirds, quote cards, story SFX on words, ambience.
6. `PY scripts/doc.py build JOB --only picture` (GPU draft render).
7. **Studio review: stop and wait** (`doc.py studio JOB`). Fix notes over MCP until the user approves.
8. Export from the studio (first export → `output/<id>/video.mp4`), `doc.py qa JOB --video …`, deliver. Never upload.

Checked on the story the user made with this workflow before (388 images, 65 min): the generic alignment places the images within 0.42 s (median) of the hand-tuned edit, 90 % within 1.3 s.
