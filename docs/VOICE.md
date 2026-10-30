# Voice: supplied narration, re-paced by emotion

**Default (narration mode):** the user supplies `input/<name>.wav` + `<name>.srt` (same base name), made on ai84.pro with MiniMax Speech 2.8 HD (WAV 44.1/48 kHz, voice only, no music), SRT from Whisper. Often 40+ minutes. The voice is **never regenerated** here; we only move silence. ElevenLabs TTS remains an optional fallback (see the end).

## `doc.py pace JOB` → `pacing.json`, `pacing.md`
1. **Cut points, only in silence.** 10 ms RMS; adaptive threshold = noise floor (5th percentile) + 15 dB, clamped to −50…−35 dB. At every SRT cue boundary the longest silent run (≥ 60 ms) within ±0.35 s of the Whisper boundary is searched; at every sentence end *inside* a cue the time is estimated from the character position and searched ±0.6 s for ≥ 120 ms of silence. No silence → the boundary stays glued (never cut inside a word).
2. **Units** = audio between cuts (40 ms head / 90 ms tail of the silence kept with the speech). Each unit records its source range, its original gap, its text and SRT cue numbers.
3. **Design.** Units are grouped into sentences; emotion is judged on the whole sentence (`scripts/sentences.py` heuristic, EN+VI). The sentence's last unit gets the emotion pause below, which lengthens or shortens MiniMax's gap; mid-sentence cuts keep MiniMax's own breath (only a gap over 0.45 s is capped).
4. **Agent review (required).** Read `pacing.md` alongside `STORY.md` and edit `pacing.json` on the sentence's last unit: `emotion` + `"source": "agent"`, `paragraph_end: true` (scene change), `chapter_after: true` + `chapter_title`, or `pause_after` + `"locked": true` for a deliberate hold (before a letter, after a reveal: 2–7 s). Rerun `pace`; edits survive for unchanged text.

| emotion | pause s | use |
|---|---|---|
| urgent | 0.22 | action runs on |
| tense | 0.32 | build-up |
| neutral | 0.45 | exposition |
| calm | 0.55 | |
| hook | 0.70 | cold open |
| triumphant | 0.75 | let it ring |
| reflective | 0.85 | |
| dramatic | 0.95 | punch lines, reveals |
| question | 1.00 | rhetorical question |
| somber | 1.15 | death, loss |

Modifiers: paragraph end +0.5; before a chapter +2.2; trailing `…` +0.3; > 28 words +0.1; sharp temperature change to the next sentence +0.3; clamp 0.15–4.0 s.

Measured on a real 38-minute MiniMax narration (1,072 cues): 712 units, 711 cuts in silence, 360 cue boundaries glued; pauses 103 s → 181 s before agent review, film 37:58 → 39:20. Pace + assemble ran in about 10 s.

## `doc.py assemble JOB`
Rebuilds `voice/voice.wav` (48 kHz) with the new gaps, checks every spliced edge is below −40 dB (or the noise threshold) before the 5 ms splice fades, and writes:
- `voice/voice.srt`: every original cue moved to the new pacing (`remap`: linear inside a unit, proportional inside a gap);
- `voice/words.json`: word onsets estimated from character position inside each cue (approximate; good to about ±0.15 s; SFX anchors may need a frame nudge);
- `timeline.json`: voice clips per unit; every clip anchored to a unit (`{"sentence": "U012"}`) or an SRT cue (`{"cue": 345}`) is retimed.

## Replacing one misread sentence
Find the unit in `pacing.md`, regenerate **exactly that unit's text** on AI84 with the same voice/model/speed, save it as `projects/<id>/voice/replace/U012.wav` (wav/flac/mp3/m4a). `assemble` trims its silence and splices it between the same cut points; the cues inside are scaled to its new length and everything after moves. Delete the file to go back. If the unit is only part of a sentence and the re-read sounds out of context, regenerate the neighbouring units of that sentence too.

## Re-voicing with emotion tags via AI84 (`doc.py voice JOB`)
Used when the supplied voice sounds flat. Setup in `brief.json`:
- `pacing.cut: "sentence"`, so each unit is a whole sentence;
- `pacing.beat_snap: true`;
- `voice.provider: "ai84"`, `voice_id` (e.g. Tung Dang Deep/Warm `3VnrjnYrskPMDsapTr8X`), `model: "eleven_v4"`, `language_code: "vi"`.

Steps:
1. `pace`, then the agent reviews the emotion of every sentence.
2. `voice JOB` (dry run), then `voice JOB --run`. Each sentence is sent with a v4 tag mapped from its emotion (`[dramatic]`, `[thoughtful]`; per-unit `tag` overrides it, `say` replaces the spoken text). Whisper artefacts are cleaned first ("20. 000" → "20.000", "Msta- S" → "Msta-S", "152mm" → "152 li").
3. Files land in `voice/replace/U###.mp3` and are cached by text, voice, model and settings.
4. `assemble` splices them at the original cut points, and each sentence after a pause starts on the nearest music beat (−0.12 to +0.35 s).
5. Run `qa --stt --run`. On the Bakhmut test: 95.7 % word match; every diff was a number written as words; no tag was spoken. Cost: 1,231 AI84 credits for 1,231 characters.

The key comes from env `AI84_API_KEY` or the user's AI84 doc file; it is never printed.

## Optional fallback: ElevenLabs TTS (mode "tts")
`input/<job>/script.txt` without WAV/SRT → `split` (sentences.json) → `tts` (dry run; `--run` costs credits, ask first; `--mock` for offline timing tests, never deliverable) → `assemble`. Script markup: `# chapter`, blank line = paragraph, `{somber}` emotion, `[pause 2.5]`. Delivery per emotion and costs: `scripts/elevenlabs.py`. ElevenLabs is otherwise used only for SFX and temporary music.

## Chunked AI84 + Whisper (default for AI84 voices, `tts JOB`)
Per-sentence jobs were slow (~10 sentences/min: ~2 h for a 65-min film). Now `tts` sends **chunks**:
- **Chunks:** consecutive sentences, one chunk per chapter (AI84 recommends long texts: faster), split further only past `voice.chunk_chars` (default 0 = no limit). Each sentence keeps its own emotion tag inline (`[dramatic] …`), a new paragraph starts a new line. Up to `voice.workers` (default 4) AI84 jobs at once; finished chunks are cached in `voice/chunks/`, so a rerun resumes.
- **Whisper first:** the Whisper worker (`scripts/whisper_worker.py`, faster-whisper, the medium model from TOOL SY, CUDA float16) starts loading **before** the first AI84 job goes out (the model takes ~15 s to load). Each chunk is transcribed as soon as it arrives (~11× real time on the RTX 4070 Ti SUPER). When the last chunk is cut the worker exits, which releases its GPU memory.
- **Same logic as OmniVoice Playground** (`scripts/whisper_align.py`): the script's own text is aligned 100 % to Whisper's words character by character (difflib blocks ≥ 3 chars, interpolation). AI84's transcript is never used.
- **Cut into sentences:** each boundary goes into a real pause of the chunk. Pauses are matched to the predicted boundaries in order by dynamic programming, so one-word sentences heard as one ("Gạo. Muối. Đèn.") still split at their own pauses. Each sentence becomes a clip in `voice/clips/` with real character timings. `assemble` then trims it, adds the emotion pauses, writes `words.json` (real word onsets, no longer approximate) and `voice.srt` with OmniVoice's subtitle splitting and cue timing.
- **Check:** sentences where little of the script was heard (skipped or misread by the voice) are listed after the run. Redo them with `tts JOB --only S123 --run` after fixing the text, or set `voice.chunked: false` to fall back to one job per sentence.
- **Settings in `brief.json` → `voice`:** `chunked` (true), `chunk_chars` (0 = no limit), `workers` (4), `whisper_python` (a Python with faster-whisper; auto-detected: this venv, the user's Python 3.13/3.12, OmniVoice's backend venv), `whisper_model` (default: TOOL SY's medium, else `medium`).
- Tested without credits on 30 real sentences glued into one chunk: 29/29 cuts inside the right pause, every clip edge below −40 dB, subtitle splitting identical to OmniVoice on 461/461 texts.

