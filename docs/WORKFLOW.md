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
2. Run `tts JOB` (dry run: characters ≈ AI84 credits), then `tts JOB --run`. Each sentence is its own AI84 job (own emotion tag, speed and settings: quality first); Whisper (OmniVoice logic, started before the jobs and released after) gives each clip real word timings for the SRT (`docs/VOICE.md#ai84-voice-one-job-per-sentence--whisper-timing-default-tts-job`). `voice.chunked: true` is a faster, lower-quality opt-in. Results are cached; `--only S004` redoes one sentence. Read the list of poorly heard sentences it prints.
3. Run `assemble JOB`. It trims each clip, applies the emotion pauses, lands each sentence start on a music beat once a music clip is in the timeline (rerun assemble after placing music), writes `voice.wav`, writes a generated subtitle SRT (≤ 42 characters per cue), and retimes the timeline.
4. Check with `qa --stt --run`.

## 3. Supplied-narration jobs: re-pace by emotion [built]
`PY scripts/doc.py pace JOB` finds cut points in silence (never inside a word), groups units into sentences, and designs a pause per sentence from its emotion; mid-sentence breaths stay natural. Then **review** `pacing.md` against STORY.md and edit `pacing.json` on each sentence's last unit: `emotion` + `"source": "agent"`, `paragraph_end` (scene change), `chapter_after` + `chapter_title`, or `pause_after` + `"locked": true` for deliberate holds (before a punch line, after a strong line, before a letter or title card). Rerun `pace`; edits survive. Rules and numbers: `docs/VOICE.md`. Do not regenerate the voice.

## 4. Fix misread sentences [built, user-supplied audio]
If the user (or STT QA) finds a misread unit, ask them to regenerate exactly that unit's text on AI84 with the same voice and drop it at `projects/<id>/voice/replace/U###.wav`. Never create replacement speech yourself. (TTS-fallback jobs instead run `split` + `tts`, dry run first, ask before `--run`.)

## 5. Assemble [built]
`PY scripts/doc.py assemble JOB` rebuilds `voice/voice.wav` with the designed gaps and any replacements, fails if a spliced edge is not silent, retimes every SRT cue (`voice/voice.srt`), writes approximate word onsets (`voice/words.json`), and creates/updates `timeline.json`. Clips anchored to units (`U###`) or cues (`{"cue": N}`) are retimed, so pictures, music and SFX stay synced after any later pacing change. Report the new duration. Listen to `voice.wav` where a playback tool exists; otherwise say you did not listen.

## 6. Scenes and archival media [built: `doc.py media`, `doc.py ops`; maps planned]
Real, licensed archival material only (`docs/MEDIA.md`); this workflow is for historical-analysis films. (`projects/nguoi-gac-dem` was a one-off fiction run with the user's own AI images: never use it as the model.)
1. Turn the per-sentence video slots into scenes, a new shot every ~3–6 s. Merge, split and trim slots with timeline ops (`doc.py ops JOB ops.json`, or the studio MCP tool `update_clips`): moved clips are re-anchored to the nearest word, so later voice changes still retime them.
2. For each scene write the media need, then `doc.py media JOB search "query" --tag T [--kind photo|video]` and look at the contact sheet `qa/media-T.jpg`.
3. `doc.py media JOB pick SLOT T K --caption "what it really shows"` downloads the file, sets `src`/`kind`/`credit` and appends the `LICENSES.md` row. A photo of another place or date gets "(illustrative)" / "(minh hoạ)" in its caption.
4. Per scene, as needed: motion (Ken Burns presets or custom `motion`), grade, `transition_in`, colour (`docs/SCHEMA.md#studio-fields`).
5. Overlays on the `overlay` track: date tags, lower thirds, callouts, title/question/chapter/stat/quote cards, free text.
Maps (terrain + satellite tiles) are **planned**: say so; until then use licensed archival maps found with `media search`.

## 7. Music [built: shared library + placement; beat grid planned]
Per chapter, pick a mood bed from `assets/music/<mood>/` and place it on the `music` track with `doc.py ops` / `update_clips` (`add` with `src`, `start`, `end`, `gain_db`, `fade_in`, `fade_out`, `in`; anchored automatically to the nearest word). Missing moods: `PY scripts/music_elevenlabs.py MOOD --seconds 90 --prompt "..."` dry-runs with the live balance; `--run` only after the user's yes (`docs/MUSIC.md`). Suno only as the user's manual Pro downloads. Beat-grid snapping (librosa) is **planned**: cut on phrase ends by ear instead. Rerun `assemble` after placing music if sentence starts should land on beats.

## 8. SFX [built: shared library + placement]
Word-anchored one-shots from `assets/sfx/<type>/` on the `sfx` track (`add` with the event's time: the anchor goes to the word naming it), plus field sound of archival film on `original` (`docs/SOUND.md`). Sparse, under the voice; cards get an audible hit. New SFX types only via `scripts/sfx_elevenlabs.py` dry run and the user's yes.

## 9. Draft render [built: `doc.py build JOB --only picture`]
Renders `render/picture.mp4` from the timeline on the GPU (`scripts/render_gl.py`; ~10–12 min for a 65-min film, CPU fallback). Not a deliverable: it is what the studio plays and splices into. Self-check a few frames (cards, maps, transitions) before the review.

## 10. Studio review: STOP and wait for the user [built: `doc.py studio JOB` or `Studio.bat`]
**Mandatory gate: never produce the final output before the user approves in the studio.**
1. Start the studio for the job (`PY scripts/doc.py studio JOB`, http://localhost:5280/). Tell the user it is open, what to check (pictures and captions, cards, music/SFX levels, subtitles) and how: play, press C to leave notes, drag clips, edit subtitles by clicking them.
2. **End the turn and wait.** Do not export, do not continue to QA.
3. On each round: `list_review_notes` → fix with `update_clips` (or `doc.py ops`) → check with `render_frame` / `render_preview` → `set_note_status` doing + reply. Only the user marks notes done.
4. Continue only when the user says the film is approved (in chat) or exports it with **Xuất bản**.

## 11. Export [built: studio **Xuất bản**, or the MCP tool `export` when the user asks]
Re-renders only the picture ranges changed in review (spliced into `render/picture.mp4`), runs the voice-led mix (−14 LUFS, ≤ −1 dBTP) and muxes. The first export of a film writes `output/<id>/video.mp4` with `LICENSES.md` and `credits.txt`; later exports write `video-studio-<time>.mp4` and never overwrite `video.mp4`. (`doc.py build JOB` still does picture + mix + mux in one go without review: only when the user asks to skip the studio.)

## 12. QA [built: `doc.py qa`]
`PY scripts/doc.py qa JOB --video FILE` on the exported file: black, freeze (flags anything not on an intentional card), loudness, true peak. `--stt` dry-runs; with the user's OK `--stt --run` transcribes with ElevenLabs Scribe and compares words with the SRT/script (target ≥ 97 %; judge names/spellings rather than hiding them). Then inspect real frames at every flagged time, transitions, maps and text cards. Record what was and was not checked.

## 13. Deliver
`output/<id>/video.mp4` (or the approved `video-studio-<time>.mp4`), `LICENSES.md`, `credits.txt` (description-ready attribution), `qa.json`. Never upload.
