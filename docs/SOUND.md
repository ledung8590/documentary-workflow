# SFX (stage 8: shared library + placement built)

Library: reuse `../history-video-workflow/assets/sfx/` (ElevenLabs Sound Effects, Starter commercial licence confirmed 2026-10-30, per-file `LICENSES.md`). Copy, do not regenerate; new types are generated only after a dry run and the user's OK.

Placement: an SFX clip is anchored to the word that names or shows the event (`{"sentence": "S007", "word": 3, "offset": -0.05}`), so it lands on the exact frame and follows voice changes. The visual cut it belongs to should share the anchor.

**Clip sound.** Video clip audio is muted by default, because uploads often carry music; in the Bakhmut test, V04 and V14 had music. For every action clip (firing, explosions, vehicles):
1. Check its audio with Scribe audio-event tagging (`tag_audio_events`). If it reports music/jingle, keep it muted.
2. If it is field sound only, set `original_audio: true`, `gain_db` about −6, and an `audio_note` saying what was verified.
3. Find the shots: audio transients plus a filmstrip (`media strip`). Layer a library boom/gun SFX on each visible shot, anchored to the clip.

An action shot never plays silent.

Rules carried over from the chibi pipeline: sparse (about 3 per minute, ≥ ~12 s apart in long films), gain ≤ −9 dB relative to voice and ducked by the voice; no SFX on every sentence; ambience beds only where the picture shows a place. Archival film with real sound goes on the `original` track at low level instead of an SFX.
