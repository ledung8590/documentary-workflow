# Architecture

## What the reference film is (sampled 2026-10-30)
`Chiến Dịch Điện Biên Phủ 1954.mp4`: 154.5 s, 1920×1080, 24 fps (VP9/AAC 48 kHz), −14.1 LUFS, true peak −0.5 dBFS (slightly above our −1 dBTP target), LRA 4.6 LU. About 40 picture changes, so a new shot every ~3.8 s. Visual grammar, from 32 sampled frames:
- B&W/sepia archival photos with slow Ken Burns moves and a short credit line bottom-right ("Ảnh: TTLTQG III / TTXVN", "Tư liệu phim «Việt Nam» (R. Karmen, 1955)").
- Satellite and terrain maps (Sentinel-2 cloudless 2016, AWS Terrain Tiles, OSM) with blue sector zones, a white dashed perimeter, red/orange trench and attack arrows, an animated route line, and a full attribution line.
- Date tag top-left (red bar + condensed bold caps, "TỪ 30/3/1954"); lower thirds (kicker + name + unit); title cards on black ("VÌ SAO?", red); stat cards on parchment (big condensed numbers, red underline, small label); calendar card; typewriter quote on dark brown with a source line; closing card "TRI ÂN …".
- Archival film snippets with original sound under narration.

## Pipeline
```
input/<name>.wav + <name>.srt  (AI84/MiniMax voice, Whisper SRT; default)
 1 ingest      ─► projects/<id>/{brief,state}.json, narration.srt, LICENSES.md         [built]
 2 research    ─► FACTS.md, STORY.md (agent)                                            [manual]
 3 pace        ─► pacing.json/.md: cuts in silence, emotion + new pause per unit        [built]
 4 replace     ─► voice/replace/U###.wav re-reads from the user (optional)              [built]
 5 assemble    ─► voice/voice.wav, voice.srt (cues retimed), words.json (approx),
                  timeline.json (anchored clips retimed)                                [built]
   fallback: input/<job>/script.txt → split → tts (ElevenLabs, dry run) → assemble      [built]
 6 media       ─► archival photos/film (media search/pick), scenes, overlays, LICENSES  [built; maps planned]
 7 music       ─► shared mood beds placed per chapter (doc.py ops / update_clips)     [built; beat grid planned]
 8 sfx         ─► word-anchored sfx clips from the shared library                     [built]
 9 draft       ─► render/picture.mp4 (GPU, doc.py build --only picture)               [built]
10 STUDIO STOP ─► user reviews in the studio, notes, agent fixes over MCP, approval   [built]
11 export      ─► dirty ranges re-rendered, mix −14 LUFS, output/<id>/video.mp4       [built]
12 qa          ─► qa/qa.json: black, freeze, loudness, STT match                       [built]
```
Every stage reads/writes files in the project folder only; `timeline.json` is the shared contract (docs/SCHEMA.md). Paying stages dry-run by default.

## Why units + anchors
The voice is the clock. Cutting the supplied narration into units at silent points lets us (a) choose every pause by emotion without regenerating speech, (b) splice in one re-read sentence without touching the rest, (c) map every SRT cue and word to the new timeline. Everything else hangs off sentence/word anchors, so a regenerated sentence or a changed pause moves the scenes, music cuts and SFX with it; this is exactly the "giãn mốc" step the reference session had to do by hand.

## Layout
```
documentary-workflow/
 AGENTS.md CLAUDE.md GEMINI.md README.md .claude/skills/gendoc/
 docs/       WORKFLOW ARCHITECTURE VOICE MEDIA MUSIC SOUND SCHEMA STUDIO CAN_CHUAN_BI(vi)
 scripts/    doc.py (CLI) common.py pacing.py sentences.py elevenlabs.py timeline.py setup.ps1
 tests/      test_pipeline.py test_pacing.py (offline)
 examples/   example-dien-bien-phu/script.txt
 input/  projects/  output/  licenses/
 studio/     server.py (web UI + API) · mcp_server.py · core.py · jobs.py · ui/
```

## Build order for the remaining stages
1. `render.py` minimal: still images + Ken Burns + crossfades + voice → MP4 (lets QA run on real output early).
2. Overlay templates (date tag, lower third, title card, stat, quote) as Pillow PNG renders.
3. `media` search/download with licence logging (Commons + NARA + LoC first).
4. `maps` (tiles → large still → annotated layers).
5. `music` (ElevenLabs Music mood-bed library with dry run + credit estimate, manual Suno import, librosa beats) and `mix` (ducking, loudnorm two-pass).
6. `sfx` placement from the shared library.
7. Studio server + UI + MCP.
