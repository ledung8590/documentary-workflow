# timeline.json (version 1)

The one editable project file. Times are seconds (float); `frame` = round(start × fps). The studio, the agent and the renderer all read/write this file; nothing else holds edit state.

```json
{
 "version": 1, "id": "dien-bien-phu", "fps": 24, "width": 1920, "height": 1080, "duration": 154.5,
 "loudness": {"target_lufs": -14.0, "true_peak": -1.0},
 "mock_voice": false,
 "tracks": [
  {"id": "video", "kind": "video", "clips": [
    {"id": "V003", "start": 17.58, "end": 22.58, "src": "media/artillery-1954.jpg", "need": "porters hauling guns",
     "anchor": {"sentence": "S004", "edge": "start", "offset": 0.0}, "end_anchor": {"sentence": "S005", "edge": "start"},
     "in": 0.0, "fit": "cover", "motion": {"type": "kenburns", "from": [1.0, 0.5, 0.5], "to": [1.12, 0.45, 0.55]},
     "grade": "archival_bw", "transition_in": {"type": "fade", "dur": 0.4},
     "caption": "Porters pulling a 105 mm howitzer, 1954 (illustrative)", "credit": "Photo: NARA 111-SC-xxxx (public domain)"}]},
  {"id": "overlay", "kind": "overlay", "clips": [
    {"id": "O1", "start": 0.0, "end": 6.0, "type": "date_tag", "props": {"text": "1953 – 1954"}},
    {"id": "O2", "start": 60.4, "end": 64.0, "type": "title_card", "props": {"text": "The Last Days"}},
    {"id": "O3", "type": "lower_third", "props": {"kicker": "Battery commander", "name": "…", "sub": "…"}},
    {"id": "O4", "type": "stat", "props": {"items": [{"value": "261,453", "label": "porters"}]}},
    {"id": "O5", "type": "quote", "props": {"text": "…", "source": "…", "typewriter": true}},
    {"id": "O6", "type": "map_annot", "props": {"map": "maps/dbp-valley.json", "layers": ["zones", "arrows"]}}]},
  {"id": "voice", "kind": "voiceover", "clips": [
    {"id": "S001", "start": 2.0, "end": 7.9, "src": "voice/trimmed/S001.wav", "text": "…", "emotion": "hook", "gain_db": 0, "pause_after": 0.7}]},
  {"id": "music", "kind": "music", "clips": [
    {"id": "M1", "start": 0.0, "end": 58.0, "src": "music/hook.mp3", "in": 12.4, "mood": "ominous", "gain_db": -16,
     "fade_in": 1.0, "fade_out": 2.0, "duck": true, "cut_on_beat": true, "anchor": {"sentence": "S001", "edge": "start", "offset": -2.0}}]},
  {"id": "original", "kind": "original", "clips": [
    {"id": "A1", "start": 9.1, "end": 12.0, "src": "media/karmen-1955.mp4", "in": 31.0, "gain_db": -20}]},
  {"id": "sfx", "kind": "sfx", "clips": [
    {"id": "X1", "start": 39.2, "end": 41.0, "frame": 941, "src": "../../assets/sfx/boom/boom-1.mp3", "gain_db": -9,
     "anchor": {"sentence": "S007", "word": 3, "offset": -0.05}}]}
 ],
 "markers": [{"t": 22.58, "kind": "chapter", "label": "The Guns in the Hills", "anchor": {"sentence": "S004", "edge": "start"}}],
 "review_notes": [{"id": "N1", "t": 17.0, "rect": [0.6, 0.1, 0.3, 0.2], "text": "Ảnh này mờ, đổi ảnh khác", "status": "open"}],
 "credits": [{"file": "media/artillery-1954.jpg", "line": "NARA, public domain"}]
}
```

Rules
- Voice track is rebuilt by `assemble`; edit pacing via `pacing.json` (narration mode, units `U###`, clips point into `voice/voice.wav` with `in`) or `sentences.json` (TTS fallback, `S###`), not here. Clips may also anchor to an original SRT cue: `{"cue": 345, "edge": "start"}` / `{"cue": 345, "word": 2}`.
- Anything that should follow narration carries `anchor` (+ optional `end_anchor`). Word anchors use the 0-based word index in that sentence (`voice/words.json`, field `i`).
- Unanchored clips stay where they are when the voice changes (`assemble` reports how many).
- `review_notes.status`: `open` → `doing` → `done`. Only the user closes a note as `done` after looking, unless they say otherwise.
- Overlay `type` set: `date_tag lower_third title_card stat quote calendar map_annot black` (renderer templates, planned). `title_card`, `quote`, `black` mark intentional dark/still stretches for QA.

## Studio fields (optional; scripts/render_fx.py)
- Video clip `color`: `{exposure, brightness, contrast, saturation, temperature, tint, gamma, shadows, highlights, fade, sepia}` (neutral 0, or 1 for contrast/saturation/gamma).
- Video clip `motion`: `{"type": "push"|"pull", "dx"}` (classic) or `{"type": "custom", "from": {"zoom", "x", "y"}, "to": {...}, "ease": "smooth|linear|in|out", "shake": 0..1}` or `{"type": "none"}`.
- Video clip `transition_in.type`: `fade dip dip_white wipe_left wipe_right wipe_up wipe_down slide_left slide_right slide_up slide_down zoom blur circle_open circle_close radial pixelize`.
- Tracks with `"kind": "fx"` (ids `fx`, `fx2`…; `"hidden": true` = off) hold effect clips `{"type", "start", "end", "params", "opacity", "fade_in", "fade_out", "label"}`; types and default params in `render_fx.EFFECTS`; `media_overlay.params` = `{src, blend, scale, x, y, size, speed, loop}`.
- Overlay `type: "text"`: props `text x y size font color align stroke stroke_color shadow box box_color anim upper line_gap`.
- Top-level `subtitle_style`: `{size, y, color, upper, stroke, stroke_color, shadow, box, box_color, box_pad, box_radius, font}` (box = background opacity 0..1).
- Top-level `subtitle_overrides`: `{"<cue start in ms>": {"text", "start", "end"}}`: studio edits of single burned-in cues; `voice/voice.srt` stays as assembled, `"text": ""` hides a cue.
- Audio clip `mute: true` leaves it out of the mix.
