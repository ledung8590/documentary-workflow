# Canonical /gendoc procedure

Run from the workspace root with `.venv/Scripts/python.exe` (PY). Built stages are marked **[built]**; the others are **[planned]**: say so plainly and stop there, do not improvise a substitute. Every paying command dry-runs first; ask the user before `--run`.

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
2. Run `tts JOB` (dry run: characters ≈ AI84 credits), then `tts JOB --run`. One AI84 job per sentence; the result is cached, so `--only S004` redoes a single sentence.
3. Run `assemble JOB`. It trims each clip, applies the emotion pauses, lands each sentence start on a music beat once a music clip is in the timeline (rerun assemble after placing music), writes `voice.wav`, writes a generated subtitle SRT (≤ 42 characters per cue), and retimes the timeline.
4. Check with `qa --stt --run`.

## 3. Supplied-narration jobs: re-pace by emotion [built]
`PY scripts/doc.py pace JOB` finds cut points in silence (never inside a word), groups units into sentences, and designs a pause per sentence from its emotion; mid-sentence breaths stay natural. Then **review** `pacing.md` against STORY.md and edit `pacing.json` on each sentence's last unit: `emotion` + `"source": "agent"`, `paragraph_end` (scene change), `chapter_after` + `chapter_title`, or `pause_after` + `"locked": true` for deliberate holds (before a punch line, after a strong line, before a letter or title card). Rerun `pace`; edits survive. Rules and numbers: `docs/VOICE.md`. Do not regenerate the voice.

## 4. Fix misread sentences [built, user-supplied audio]
If the user (or STT QA) finds a misread unit, ask them to regenerate exactly that unit's text on AI84 with the same voice and drop it at `projects/<id>/voice/replace/U###.wav`. Never create replacement speech yourself. (TTS-fallback jobs instead run `split` + `tts`, dry run first, ask before `--run`.)

## 5. Assemble [built]
`PY scripts/doc.py assemble JOB` rebuilds `voice/voice.wav` with the designed gaps and any replacements, fails if a spliced edge is not silent, retimes every SRT cue (`voice/voice.srt`), writes approximate word onsets (`voice/words.json`), and creates/updates `timeline.json`. Clips anchored to units (`U###`) or cues (`{"cue": N}`) are retimed, so pictures, music and SFX stay synced after any later pacing change. Report the new duration. Listen to `voice.wav` where a playback tool exists; otherwise say you did not listen.

## 6. Scenes and media [planned: `doc.py media`]
Turn the per-unit video slots into scenes (a new shot every ~3–6 s; merge/split slots, keep anchors). For each scene write a media need, search licensed sources (`docs/MEDIA.md`), download into `media/`, log licence rows, set `src`, motion (Ken Burns / pan / hold), grade (archival B&W, sepia), caption + credit line. Maps from terrain + satellite tiles (`docs/MEDIA.md#maps`) with annotations on the overlay track.

## 7. Music [planned: `doc.py music`]
Per chapter mood, beds from the shared ElevenLabs Music library (`assets/music/<mood>/`; generate missing moods only after a dry run with tracks, durations and credits, and the user's yes) or user-supplied Suno Pro files; never sunoapi.org or other unofficial Suno APIs (see `docs/MUSIC.md`), beat grid, cuts and swells aligned to beats nearest the anchored story beats; ducked under voice.

## 8. SFX [planned: `doc.py sfx`]
Word-anchored one-shots from the shared ElevenLabs SFX library (`docs/SOUND.md`); sparse, under the voice.

## 9. Studio review [planned: `doc.py studio`]
Open `timeline.json` in the local studio (`docs/STUDIO.md`). The user may drag clips and leave review notes; the agent reads `review_notes`, fixes, marks them done.

## 10. Render and mix [planned: `doc.py render`, `doc.py mix`]
ffmpeg compositor: 1920×1080, fps from brief (24 default), H.264 High, AAC 48 kHz. Mix voice-led, music ducked, −14 LUFS, ≤ −1 dBTP.

## 11. QA [built: `doc.py qa`]
`PY scripts/doc.py qa JOB --video FILE` — black, freeze (flags anything not on an intentional card), loudness, true peak. `--stt` dry-runs; with the user's OK `--stt --run` transcribes with ElevenLabs Scribe and compares words with the SRT/script (target ≥ 97 %; judge names/spellings rather than hiding them). Then inspect real frames at every flagged time, transitions, maps and text cards. Record what was and was not checked.

## 12. Deliver
`output/<id>/video.mp4`, `LICENSES.md`, `credits.txt` (description-ready attribution), `qa.json`. Never upload.
