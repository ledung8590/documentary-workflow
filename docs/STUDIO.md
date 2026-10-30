# Studio (stage 9, built)

Small fixes to a finished film: Claude edits `timeline.json` over MCP, the user checks in a web UI and exports.

## Run it
```
PY scripts/doc.py studio <job>          # = PY studio/server.py <job>; opens http://localhost:5280/
```
- **MCP:** `.mcp.json` registers `documentary-studio` (`.venv\Scripts\python.exe studio\mcp_server.py`). Claude Code asks once to approve the project server. Tools default to the project the studio last opened.
- **Background jobs:** previews and exports run as `studio/jobs.py` processes. Status lives in `projects/<id>/render/studio/jobs/`; the UI (tab *Bản dựng*) and `get_job` both read it.

## What it does
| Part | Files | Notes |
|---|---|---|
| Store | `studio/core.py` | Every write is ETag-checked (sha1 of the file) under a lock file. A stale write gets HTTP 412 or an MCP `CONFLICT`. The previous file is kept in `render/studio/history/` with a log of who changed what and why. The server writes only `timeline.json`, plus its own work files in `render/studio/`. |
| Clip ops | `core.apply_ops` | `move / trim (roll) / split / set / add / delete / fx`. A moved clip is re-anchored to the nearest word or sentence edge, so `assemble` still retimes it. The voice track is read-only (rebuild it with `doc.py`). |
| Preview frame | `core.Framer` → `render.composite` | Draws a frame the same way as `render.picture`: Photo + Ken Burns, overlays, credit line, subtitle, grain and vignette. Checked against the delivered `picture.mp4`: median PSNR 36.6 dB over 83 frames, with differences coming from grain phase and H.264. |
| Monitor audio | `render.mix_graph(t0, t1, only)` | The UI plays 10 s windows of the real premix: same ducking, levels and limiter, at the export's loudnorm gain. M/S toggles only affect listening. The meter is K-weighted momentary loudness. |
| Preview render | `core.preview` | A range of up to 180 s. With *Tự động*, frames are rendered only if the range has picture edits; otherwise the range is cut from `picture.mp4` and the audio re-mixed (≈2 s for 8 s). Frame rendering runs at about 5 fps. |
| Export | `core.export` | **Audio-only edits:** full mix + mux onto the existing `render/picture.mp4` (≈7 min for 65 min). **Picture edits:** only the dirty ranges are re-rendered, widened to `picture.mp4` keyframes, then stream-copied back in (frame count verified) before the mix. The first export of a film writes `output/<id>/video.mp4` (+ `LICENSES.md`, `credits.txt`); after that every export is a new file, `video-studio-<time>.mp4`, and `video.mp4` is never overwritten. |

`render/studio/picture_state.json` records which video and overlay clips `picture.mp4` contains, so the studio knows which ranges are *dirty*. These are shown red on the ruler and overview, and in *Bản dựng*. On the first open of a rendered film, the studio assumes the current tracks match `picture.mp4`. It also writes each photo's Ken Burns direction into `motion`, which `render.Photo` otherwise derives from the clip's index inside its render chunk. The picture does not change, and later splits or inserts no longer shift every move after them.

## UI (Vietnamese)
Layout: tool panels on the left, preview in the middle, *Thuộc tính* (inspector of the selected clip) on the right, timeline below. `Studio.bat` in the repo root starts it with a double-click.
- **Preview:** paused frames come from the current timeline. During playback, unchanged stretches play from `picture.mp4` (*Hình mượt*), and edited stretches are drawn live. Sliders show a *xem nháp* (draft) frame while dragging (`POST /api/frame` with ops, nothing saved) and save on release.
- **Timeline tracks:** Cảnh, Chữ / thẻ, Hiệu ứng (any number, `＋ Track hiệu ứng`; eye = off), Lời đọc (locked), Nhạc, Nền, Tiếng động. Per track: lock, M/S (listening only).
- **Editing:** drag the body to move, an edge to trim; the cut between two scenes rolls both (Alt: one only). Snaps to sentences, words, playhead, clip edges. Shift/Ctrl+click selects several clips. Items from the panels drag onto the tracks.
- **Panels:**
  - *Media*: thumbnails of the film's media and of `assets/overlays` + `media/import`; drop files to import; drag a tile onto Cảnh to insert a shot (Alt on a shot = replace), onto Hiệu ứng = overlay layer.
  - *Âm thanh*: shared music/sfx library grouped by folder, ▶ listen, + add at the playhead; per-clip gain, fades, mute, loop.
  - *Chữ*: 12 templates (free text, centred title, corner caption, typewriter, date tag, lower third, callout, title card, question, chapter, stat, typed quote); free text has font, size, x/y, colour, stroke, shadow, box, entrance (fade, slide, typewriter). Subtitle style for the whole film: font, size, UPPERCASE, colour, position, outline width/colour, shadow, background (opacity, colour, padding, rounded corners), two presets.
  - *Lời nói*: *Phụ đề* = every burned-in cue (window around the playhead, search, "only edited"), click to edit; *Câu đọc* = narration sentences, click to jump. Paused, a click on the subtitle in the preview opens the same editor (text, start/end, hide, restore original). Edits go to `subtitle_overrides`; only that cue's range re-renders. *Quay*: microphone recording → WAV in `media/import/` → a clip on Nền/Tiếng động/Nhạc.
  - *Chuyển động*: 10 Ken Burns presets for the selected shots; custom start/end zoom, x, y, easing, handheld shake.
  - *Hiệu ứng*: presets (old film light/heavy, 1950s newsreel, grain, dust & scratches, flicker, gate jitter, vignette, warm light leak, blur, 2.35 letterbox, white flash, colour layer) and *Lớp phủ media* (your own or built-in footage/image with blend mode normal/screen/multiply/overlay/add/lighten/darken/soft light, opacity, size, position, speed, loop). Every effect clip has opacity and fade in/out.
  - *Chuyển cảnh*: cut, fade, dip to black/white, wipe ×4, slide ×4, zoom, blur, circle open/close, radial, pixelize; duration; applied to the start of the selected shots.
  - *Màu*: 10 presets + sliders (exposure, brightness, contrast, saturation, temperature, tint, gamma, shadows, highlights, fade, sepia) per shot or group, or as a colour layer over a range / the whole film.
  - *Góp ý*: press C, drag a box on the frame, type, Ctrl+Enter → `review_notes`. *Bản dựng*: range previews, export, jobs. *Lịch sử*: who changed what.
- **Xuất bản:** shows what will happen (audio-only vs N ranges to re-render) before it starts.
- **Agent edits:** the UI polls the ETag and reloads when the agent changes the timeline.

## Effects in the renderer
All of it lives in `scripts/render_fx.py`, called by `render.py`, so the preview, range previews and the export draw the same frames. New timeline fields are optional; a timeline without them renders exactly as before. Built-in overlay loops (`assets/overlays/`, own work) come from `PY scripts/make_overlays.py`. Speed (measured on this machine, 20 threads, RTX 4070 Ti SUPER):
- **GPU frames** (`scripts/render_gl.py`, OpenGL 3.3 via `moderngl`, on by default, *Bản dựng → Tốc độ dựng*): the photo's Ken Burns view (PIL's bicubic, kernel widened like PIL when shrinking), fade/dip, grain, the Pillow-drawn layers (credit, overlays, subtitle; uploaded only when they change) and the vignette are drawn on the graphics card. Matches the CPU frame to 51 dB (59 frames across the film, worst 51.1 dB; tests/test_render_gl.py). One GL thread per process owns the context (the server draws from many threads).
- Throughput: ~130-157 fps with NVENC (3 parts are enough), ~75 fps when splicing into the old picture.mp4 (same x264 settings, 6 parts). A whole 65-min picture: ~10-12 min (CPU only: ~70 min). A studio preview frame: ~18 ms.
- **Effects and transitions on the GPU too** (phase 2): frames with effect layers or one of the 18 transitions take a multi-pass path (source -> transition -> each effect in order -> the same final pass). Random draws (jitter, flicker, grain field, scratch/dust images, colour matrix + LUT, overlay frames) come from `render_fx.effect_plan`, i.e. the same numbers as the CPU path; every effect, all 8 overlay blend modes and every transition match the CPU frame at > 42 dB in tests (measured 46.7-51.6 dB). A range with heavy old film + dust overlay + circle transitions renders at ~73 fps (CPU ~7).
- Effect randomness and grain phase follow film time (`t_offset` of a range render), so a range looks the same however it is cut into parts.
- Still on the CPU: the Pillow drawing of overlays/subtitles, photo decoding + grading (once per shot), and the audio mix (~10 min).
- Without a GPU or moderngl, or with the switch off, everything renders on the CPU in parallel parts (default 6, like Whisk).

## Agent loop
1. `list_review_notes` returns each note with what is on screen and heard at that time.
2. Fix it with `update_clips`, passing the `if_match` etag.
3. Check the result with `render_frame` (returns the image) or `render_preview`.
4. Call `set_note_status` with `doing` and a reply. The user closes notes as `done` after looking.
5. Run `export` only when the user asks.

## Decision: built here, nothing taken from SyHQ/TOOL SY
`TOOL SY/editable-project` was inspected read-only on 2026-10-30. Its "SyHQ studio" is the proprietary **Revo Studio 1.2.0** code rebranded:
- the editor is a minified React bundle;
- the render path is compiled `.pyc` behind a vendor licence check;
- the "Apache-2.0" field in its package.json was edited locally.

It was used only as a reference for the layout and the Timeline v2 data model (tracks video/overlay/voice/bgm/original). No code was copied. TOOL SY is never modified.
