# Story mode (`/gentruyen`)

A **fiction story** narrated over the user's own images (for example AI images made one per ~8 s of an earlier narration). Separate from the archival workflow (`/gendoc`, `/genvideo`, `docs/WORKFLOW.md`).

**Do not use from the archival workflow:** archival media search, fact-check (`FACTS.md`), "(illustrative)" labels, licence rows for the user's images, `doc.py plan` / `templates/archival/`, the drawn-character budget, `description.py` CC lists, `evidence.py`. **Shared with it:** voice (`split`, `tts`, `assemble`), card SFX and music levels (music 8–10 dB under the voice, SFX set from their own loudness under the voice), subscribe overlay, the studio review stop, export via `scripts/export.py`, QA.

The layout here, one picture per story beat anchored to its words, is right for a story and wrong for an archival film: never carry it over to `/genvideo`.

## Input (`input/`)
Either layout:
- **A (side by side):** `input/<name>.txt` (script) + `input/<name>/` (images `001.png`, `002.png`…) + optional `input/<name>.srt` + optional `input/<name>_… scene.txt` (prompts).
- **B (one folder):** `input/<name>/` with `script.txt` (or the only script `.txt`), the images, optional one `.srt`, optional `*scene*.txt` / `*prompt*.txt`.

The `.srt` here is the **timing the images were made for** (one image per `seconds_per_image` of it, default: its length ÷ image count, rounded to 0.5 s, i.e. 8 s for Whisk scenes); it is not used as narration. Without it the images are spread evenly over the new voice. The prompts file (JSON lines `{"scenes 12": "…"}` or one prompt per line) only fills each clip's `need` text. Folders starting with `_` are ignored (old jobs).

Optional `input/<name>.json` (or `job.json` in the folder): `title`, `language`, `voice`, and `"story": {"grade": "archival|film|modern|none", "seconds_per_image": 8, "music": true, "card_sfx": true, "title_card": true}`.

## Language and market
`ingest` detects the script language (vi / es / de / en; `language` overrides) and picks the narrator (`VOICES` in `doc.py`: en Brian, es Alberto, de Robert Ranger, vi Tung Dang). Every on-screen word follows it: title, `CHAPTER`/`CHƯƠNG`/`CAPÍTULO`/`KAPITEL`, cards, subtitles.

## Voice
Vietnamese and US English stories use the user's MiniMax cloned voices on AI84 by default: TUNG_DUY_V2 (vi) and LS_US (en). Whole chunks of up to 9,500 characters each are read with the voice's own expression, then Whisper cuts them into sentences for the subtitles (`docs/VOICE.md`, MiniMax section). Other languages keep the per-sentence AI84 eleven_v4 voice. The script must pass `storycheck.py` before any voice, so the voice is always generated here, never outside.

## Images without the user's folder: TST Auto Generate Image over MCP
When a story arrives without images, generate them with the user's app **TST Auto Generate Image**. Its MCP server is `auto-image` (`http://127.0.0.1:47100/mcp`, added to Claude Code on 2026-11-02). The user must switch the app's MCP server on, and the tools load only in a session started after that.
- **Tools.** `get_usage` comes first: the account allows 6,000 images per day, shared with the app. Then `generate_image(prompt, aspect_ratio="16:9", reference_images=[abs paths], output_folder)` once per image, which returns a job_id at once. `wait_for_jobs(job_ids, timeout_seconds≤900)` takes 20–90 s per image, and its result has `output_path`. Use `view_image` to check a result and `retry_job` for errors.
- **Character lock.** Each main character gets one reference image, made first by text→image from a fixed appearance description (face, age, hair, clothes, era) in the film's style. It is saved as `refs/<Name>.png`. The file name is the name alone, with no `@`.
  - Every scene prompt passes the refs of the characters in that scene as `reference_images` (absolute paths).
  - The prompt names them in the order of those images, e.g. "the man from reference image 1 (@Loc) hands a note to the woman from reference image 2 (@Nhan)", and repeats each one's fixed clothing in a few words.
  - The `@Name` tag in the prompt and the reference file name `Name.png` follow the app's own convention. In the app's GUI, the folder mode reads prompt.txt plus same-named reference images, but over MCP the paths are explicit.
  - The style, era and palette sentence is identical in every prompt. Scenes without a main character use text→image with the same style sentence.
  - **House style = Người Gác Đêm (2026-10-30 story the viewers liked): black-and-white war-era documentary photography, no colour.** Each prompt starts with shot size, angle, camera move and light (e.g. "Medium shot, eye level, static, hard lamplight.") and ends with: "Black and white 1960s-70s documentary photograph, 35mm film grain, high contrast, deep shadows, slightly warm silver tone, candid, realistic, no colour, no text." Reference images are made in the same style, and `story.grade` stays `archival` (the renderer's monochrome grade).
- **Pacing.** About one image per 8 s of voice (one per scene beat), anchored like the user's own images. Check a contact sheet of the first 10 images before queueing the rest, then spot-check about every 20th image with `view_image`.
- **Output.** Save to `input/<name>/` as `001.png`, `002.png`…, plus a prompts file, so `ingest --story` and `doc.py story` work unchanged.

## Steps
1. `PY scripts/doc.py ingest --story [--only NAME]` → `projects/<id>/` with `genre: story`.
2. Run `PY scripts/storycheck.py <script>` against earlier stories (`docs/STORY_WRITING.md`). Report every `!!` to the user; fix them, rewriting with the user's OK if they wrote the script, before `split`/`tts`. Then read the story and write a short `STORY.md` (chapters, emotional curve, title). Fiction: no `FACTS.md`. Chapters come from `# Heading` lines in the script; if it has none, propose chapter points to the user (or add them to `sentences.json` chapters) before voicing.
3. `split JOB` → review emotions → `tts JOB` (dry run, credits) → `tts JOB --run` (spend pre-authorized) → `assemble JOB`.
4. `PY scripts/doc.py story JOB`: one clip per image anchored to the word where its part of the story starts (word alignment with the image SRT), title card after the opening paragraph, a chapter card in each chapter pause, music beds per chapter (mood from the sentences' emotions, tiled with crossfades; measure the ducked music 8–10 dB under the voice and adjust gains), card SFX at measured levels, grain + burned-in subtitles. Rerun after every `assemble`.
5. Refine with `doc.py ops` / the studio MCP tools: date tags, lower thirds, quote cards, story SFX on words, ambience.
6. `PY scripts/doc.py build JOB --only picture` (GPU draft render).
7. **Studio review: stop and wait** (`doc.py studio JOB`). Fix notes over MCP until the user approves.
8. After the user's approval, export with `PY scripts/export.py JOB` (never the studio's export button), then `doc.py qa JOB --video …`.
9. Deliver to `output/<id>/`:
   - the video and a 1280×720 thumbnail made from one of the user's own images (sharp, one clear subject, 2–4 big words in the story's language, bottom-right clear), both renamed to the input script's file name;
   - `description_youtube.txt` written by hand in the story's language: a short hook, chapters from 0:00, music/SFX credits if any, then a line of 7 #hashtags and a TAGS line of 7 comma-separated tags. No archival source or CC list.
   Give the tags and hashtags in chat. Never upload. There is no evidence pack for stories: after the user confirms the upload, copy the script to `stories/published/`, add its line to `stories/published/LOG.md`, and ask before deleting `projects/<id>/` caches.

Checked on the story the user made with this workflow before (388 images, 65 min): the generic alignment places the images within 0.42 s (median) of the hand-tuned edit, 90 % within 1.3 s.
