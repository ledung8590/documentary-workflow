# Canonical /gendoc procedure

Fiction over the user's own images is a different path: `/gentruyen`, `docs/STORY_MODE.md`.

Run from the workspace root with `.venv/Scripts/python.exe` (PY). Built stages are marked **[built]**; the others are **[planned]**: say so plainly and stop there, do not improvise a substitute. Stage 10 is a hard stop: the user reviews in the studio before any final output. Every paying command dry-runs first; ask the user before `--run`.

## 1. Ingest [built]
`PY scripts/doc.py doctor` (setup: `powershell -ExecutionPolicy Bypass -File scripts/setup.ps1`). Then `PY scripts/doc.py ingest`.
**Default input:** a narration script `input/<name>.txt` (or `input/<name>/script.txt`), with mode `tts`.
- Ingest detects the language (vi/es/en; `job.json` "language" overrides) and picks the narrator voice for it (`VOICES` in doc.py: en Brian, es Alberto, vi Tung Dang; `voice.voice_id` overrides).
- The voice is generated per sentence through AI84 eleven_v4 with emotion tags, and the SRT is generated from those clips.
- **Everything visible follows the script language:** overlays, captions, "illustrative" notes, map labels, card words, credits wording.
- **Supplied narration** (`<name>.wav` + `<name>.srt`, mode `narration`) is still supported; its voice is only re-paced, never regenerated, unless the user asks for `voice`.
- Empty input: ask for a script.
- Ingest resumes unchanged jobs. Read `brief.json` and `state.json`.

## 2. Research and outline [manual, agent]
Read the whole narration (SRT text, a chunk at a time for long films). Write `projects/<id>/FACTS.md` (claims, dates, places, sources, uncertainties) and `STORY.md` (acts, chapters, emotional curve, where the big beats and title cards go). If the script has a consequential factual error, record it and tell the user; never rewrite their narration silently.

## 3a. Script jobs (default): sentences, emotion, voice [built]
1. Run `split JOB`. The agent reviews every sentence's `emotion`, and may set `tag` (v4 audio tag), `say` (spoken form of numbers or names) or a locked `pause_after`.
2. Run `tts JOB` (dry run: characters ≈ AI84 credits), then `tts JOB --run`. Each sentence is its own AI84 job (own emotion tag, speed and settings: quality first); after the last clip, Whisper (OmniVoice logic, loaded then and released after) gives each clip real word timings for the SRT (`docs/VOICE.md#ai84-voice-one-job-per-sentence--whisper-timing-default-tts-job`). `voice.chunked: true` is a faster, lower-quality opt-in. Results are cached; `--only S004` redoes one sentence. Read the list of poorly heard sentences it prints.
3. Run `assemble JOB`. It trims each clip, applies the emotion pauses, lands each sentence start on a music beat once a music clip is in the timeline (rerun assemble after placing music), writes `voice.wav`, writes a generated subtitle SRT (≤ 42 characters per cue), and retimes the timeline.
4. Check with `qa --stt --run`.

## 3. Supplied-narration jobs: re-pace by emotion [built]
`PY scripts/doc.py pace JOB` finds cut points in silence (never inside a word), groups units into sentences, and designs a pause per sentence from its emotion; mid-sentence breaths stay natural. Then **review** `pacing.md` against STORY.md and edit `pacing.json` on each sentence's last unit: `emotion` + `"source": "agent"`, `paragraph_end` (scene change), `chapter_after` + `chapter_title`, or `pause_after` + `"locked": true` for deliberate holds (before a punch line, after a strong line, before a letter or title card). Rerun `pace`; edits survive. Rules and numbers: `docs/VOICE.md`. Do not regenerate the voice.

## 4. Fix misread sentences [built, user-supplied audio]
If the user (or STT QA) finds a misread unit, ask them to regenerate exactly that unit's text on AI84 with the same voice and drop it at `projects/<id>/voice/replace/U###.wav`. Never create replacement speech yourself. (TTS-fallback jobs instead run `split` + `tts`, dry run first, ask before `--run`.)

## 5. Assemble [built]
`PY scripts/doc.py assemble JOB` rebuilds `voice/voice.wav` with the designed gaps and any replacements, fails if a spliced edge is not silent, retimes every SRT cue (`voice/voice.srt`), writes approximate word onsets (`voice/words.json`), and creates/updates `timeline.json`. Clips anchored to units (`U###`) or cues (`{"cue": N}`) are retimed, so pictures, music and SFX stay synced after any later pacing change. Report the new duration. Listen to `voice.wav` where a playback tool exists; otherwise say you did not listen.

## 6. Scenes and archival media [built: `doc.py media`, `doc.py ops`, 3D maps, JS scenes]
Real, licensed archival material only (`docs/MEDIA.md`); this workflow is for historical-analysis films. (`projects/nguoi-gac-dem` was a one-off fiction run with the user's own AI images: never use it as the model.)

**Liveliness and uniqueness (user review 2026-10-31, the Akula draft was rejected as "a crude slideshow"):**
- The film must feel like the reference (`docs/STYLE.md`): animated 3D maps for every place, route or battle (`docs/MAPS.md`); animated JS graphics for physics, technology, data, networks and comparisons (`docs/SCENES.md`); a designed full card about every 15–20 s; real film clips cut short; full-frame photos.
- **Opening hook (user review 2026-10-31).** Every input script opens with its own vivid moment in paragraph 1 ("Imagine…", "Picture the scene…").
  - Before and under the first lines, stage **that** moment powerfully: its footage, map or JS scene, with the title slammed in using FX that fit it (a sonar ping, a radar sweep, a flash) and a hit SFX.
  - Never use a stock explosion: a Mark 14 dud "thud" or a radar contact must not become a blast.
  - **Real combat film in the first ~10 s, even when the cold open is calm** (user review 2026-10-31: a ship photo at 0:06 was "nhạt"). Put 1–2 short cuts of weapons firing (a launch, a torpedo or missile hit, gunfire; DVIDS SINKEX/launch film) on the line that names the threat or the weapon ("a heavily armed adversary"), with launch/blast SFX 2–3 dB under the voice. Where the script's moment is a dud or a near miss, show the firing, not a blast.
  - Plan the hook in STORY.md at Stage 2.
- **Weapons footage.** Wherever the narration names a weapon or a strike, show real weapons film (DVIDS SINKEX and launch footage, `docs/MEDIA.md`) with blast or launch SFX on the hit frame. Under the voice, keep SFX peaks 2–3 dB below the voice peaks.
- **Subscribe call-to-action.** The narration's "subscribe" line always gets the animated subscribe overlay: the button, a cursor click, the switch to "Subscribed" with FX, and the bell, with click SFX (`docs/SCENES.md`, Subscribe overlay). This rule comes from the user review on 2026-10-31.
- Never more than ~25 s without a map, scene, card or callout. Still photos fill at most about half the screen time.
- **Never merge shots to hide a missing picture, and never use the same picture twice in a film** (YouTube demonetises reused content). A shot with no unique archival picture gets a map, a JS scene or a card.
- Before the studio stop, count media keys used more than once (must be zero) and compare a contact sheet of the draft with the reference.
1. Turn the per-sentence video slots into scenes, a new shot every ~3–6 s. Merge, split and trim slots with timeline ops (`doc.py ops JOB ops.json`, or the studio MCP tool `update_clips`): moved clips are re-anchored to the nearest word, so later voice changes still retime them.
2. For each scene write the media need, then `doc.py media JOB search "query" --tag T [--kind photo|video]` and look at the contact sheet `qa/media-T.jpg`.
3. `doc.py media JOB pick SLOT T K --caption "what it really shows"` downloads the file, sets `src`/`kind`/`credit` and appends the `LICENSES.md` row. A photo of another place or date gets "(illustrative)" / "(minh hoạ)" in its caption.
4. Per scene, as needed: motion (Ken Burns presets or custom `motion`), grade, `transition_in`, colour (`docs/SCHEMA.md#studio-fields`).
5. Overlays on the `overlay` track: date tags, lower thirds, callouts, title/question/chapter/stat/quote cards, free text.
6. Maps: `node scripts/mapscene.mjs projects/JOB/maps/X.json projects/JOB/media/map-X.mp4` (`docs/MAPS.md`). JS graphics: `node scripts/jsscene.mjs projects/JOB/scenes/X.js projects/JOB/media/scene-X.mp4` (`docs/SCENES.md`). Both go on the video track as `kind: video`, `grade: none`, credited.

## 7. Music [built: shared library + placement; beat grid planned]
Per chapter, pick a mood bed from `assets/music/<mood>/` and place it on the `music` track with `doc.py ops` / `update_clips` (`add` with `src`, `start`, `end`, `gain_db`, `fade_in`, `fade_out`, `in`; anchored automatically to the nearest word). Missing moods: `PY scripts/music_elevenlabs.py MOOD --seconds 90 --prompt "..."` dry-runs with the live balance; `--run` only after the user's yes (`docs/MUSIC.md`). Suno only as the user's manual Pro downloads. Beat-grid snapping (librosa) is **planned**: cut on phrase ends by ear instead. Rerun `assemble` after placing music if sentence starts should land on beats.

## 8. SFX [built: shared library + placement]
Word-anchored one-shots from `assets/sfx/<type>/` on the `sfx` track (`add` with the event's time: the anchor goes to the word naming it), plus field sound of archival film on `original` (`docs/SOUND.md`). Sparse, under the voice; cards get an audible hit.
**Card and typing checklist (before the studio stop; missed twice, user review 2026-10-31):**
- Every `quote` overlay: `typewriter/el_03` from card start + 0.7 s for chars/cps (`render.card_quote`), stopping on the last character, then `typebell`. Gain about -6 (≈10 dB under the voice above 400 Hz).
- Every JS scene that uses `L.typed`: `jsscene.mjs --typing` spans → typewriter on each span.
- Every chapter card: whoosh + chapterhit + subdrop + `cardslam` (mid/high layer); every question card: `cardslam` + impact; title cards: revswell + titlehit.
- Grep the sfx track for each quote overlay's start before opening the studio. New SFX types only via `scripts/sfx_elevenlabs.py` dry run and the user's yes.

## 9. Draft render [built: `doc.py build JOB --only picture`]
Renders `render/picture.mp4` from the timeline on the GPU (`scripts/render_gl.py`) in 3 parallel parts with NVENC encoding, the same path as the studio's whole-picture render (`core.render_range`, ~157 fps: ~10–12 min for a 65-min film; x264/CPU fallback), and saves the render state so studio exports only re-render edited ranges. (Before 2026-10-31 `build` rendered in one process with x264 at ~31 fps: 3–4× slower.) Not a deliverable: it is what the studio plays and splices into. Self-check a few frames (cards, maps, transitions) before the review.

## 10. Studio review: STOP and wait for the user [built: `doc.py studio JOB` or `Studio.bat`]
**Mandatory gate: never produce the final output before the user approves in the studio.**
1. Start the studio for the job (`PY scripts/doc.py studio JOB`, http://localhost:5280/). Tell the user it is open, what to check (pictures and captions, cards, music/SFX levels, subtitles) and how: play, press C to leave notes, drag clips, edit subtitles by clicking them.
2. **End the turn and wait.** Do not export, do not continue to QA.
3. On each round: `list_review_notes` → fix with `update_clips` (or `doc.py ops`) → check with `render_frame` / `render_preview` → `set_note_status` doing + reply. Only the user marks notes done.
4. Continue only when the user says the film is approved in chat. **The studio is for review only** (user decision 2026-10-31): do not use its **Xuất bản** button or the MCP `export` tool.

## 11. Export [built: `PY scripts/export.py JOB`]
**Never through the studio** (its export job hung at start twice on 2026-10-31, workers idle). `scripts/export.py` runs in the foreground process:
- re-renders only the picture ranges changed in review (spliced into `render/picture.mp4`; no usable picture → whole picture on the GPU);
- runs the voice-led mix (−14 LUFS, ≤ −1 dBTP; `--no-mix` reuses `render/mix.wav` after picture-only edits) and muxes;
- the first export writes `output/<id>/video.mp4` with `LICENSES.md` and `credits.txt`; later ones write `video-<time>.mp4` and never overwrite `video.mp4`.
- Run it in the background **with a watchdog**: check CPU/GPU or output growth within 1–2 min, stop on no progress for ~2–3 min, hard timeout about 1.5× the expected time. Never wait without a limit.
(`doc.py build JOB` still does picture + mix + mux in one go without review: only when the user asks to skip the studio.)

## 12. QA [built: `doc.py qa`]
`PY scripts/doc.py qa JOB --video FILE` on the exported file: black, freeze (flags anything not on an intentional card), loudness, true peak. `--stt` dry-runs; with the user's OK `--stt --run` transcribes with ElevenLabs Scribe and compares words with the SRT/script (target ≥ 97 %; judge names/spellings rather than hiding them). Then inspect real frames at every flagged time, transitions, maps and text cards. Record what was and was not checked.

## 13. Deliver
`output/<id>/video.mp4` (or the approved `video-studio-<time>.mp4`), `LICENSES.md`, `credits.txt` (description-ready attribution), `qa.json`. Never upload.
- **Thumbnail.** Make a 1280×720 JPG in the film's look (user request, 2026-10-31):
  - The hero is a public-domain archival photo that is already in the film, graded steel-teal shadows and warm highlights, with a dark band on the left.
  - The hook goes on that band, 2–3 short lines **in the script's language** in Black Ops One: off-white plus red, with a thick dark stroke. The font has full Vietnamese diacritics, as do Saira and Oswald.
  - Add a small Saira kicker and one red graphic cue on the subject (sonar rings and a target, a stamp tag).
  - Keep the bottom-right corner clear for YouTube's timestamp. It must read at 320×180.
  - Template: `projects/85-…/thumbnail.py`.
- **Names.** Rename the video and the thumbnail to the input script's file name, e.g. `85. Soviets Make … Fa.mp4` and `.jpg`. Copy `description_youtube.txt` next to them.
- **Then ask the user whether the video is uploaded.** Do not build the evidence pack before they say so.

## 14. Evidence pack (after the user confirms the upload)
`PY scripts/evidence.py JOB` is a dry run. Add `--run` to build `evidence/<script name>/`, one folder per film under `evidence/` at the workspace root. It is not in git.
- **Moved, not copied (saves disk):**
  - the deliverables from `output/<id>/`;
  - every media file on screen;
  - the project record: the timeline, the script, the notes, the scene/map sources and the voice;
  - the original input script from `input/` (and its job .json).
- **Fetched:** each source's licence record, i.e. the NARA catalog record, the Commons metadata plus page, and the DVIDS asset plus page.
- **Copied, never moved:** the music and SFX used from `assets/`, so later films keep using them without searching or downloading again.
- **Written:**
  - `INDEX.csv`: film time, file, source, licence and record;
  - `README.md`: how to answer a claim, including 17 U.S.C. § 105 for US government works.
- **Leftovers:** what remains in `projects/<id>/` is regenerable cache (render, unused candidates, voice clips). Ask before deleting it.
- **Reruns:** the script can be rerun after a partial run. A folder the studio holds open is copied and its empty shell is left behind.
