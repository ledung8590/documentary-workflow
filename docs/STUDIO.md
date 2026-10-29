# Studio (stage 9, planned)

## Decision: build a small studio; do not extract SyHQ/TOOL SY
`TOOL SY/editable-project` was inspected read-only (2026-10-30):
- The "SyHQ studio" editor is a **minified React 18 bundle** (`desktop/dist/assets/index-syhq-studio.js`, ~1.5 MB, one line) recovered from the **Revo Studio 1.2.0** installer; the original sources are gone. Render/export lives in **compiled CPython 3.12 `.pyc`** files (`backend/bytecode-runtime/app/render/*.pyc`) behind a FastAPI sidecar, SQLite and a vendor licence check.
- It is the vendor's proprietary code rebranded; the "Apache-2.0" field in its package.json was edited locally. Copying it into a new tool is a legal risk and technically weeks of un-minifying for a fragile result.
- Useful as a **reference only**: its Timeline v2 idea (tracks video/overlay/voice/bgm/original/subtitle; clips with start/end, source in/out, speed, transform, keyframes, transition), mixer/ducking parameters, export options. The user's own readable ffmpeg helpers (`backend/bytecode-runtime/app/adapters/ffmpeg.py`, `render/filtergraph.py`, `fx.py`, `zoom.py`) may be read for ideas. TOOL SY is never modified.

## What to build (≈ 3–6 working days for a usable v1)
`studio/` in this repo:
- **Server** (Python, stdlib `http.server` or FastAPI): serves the UI and media of one project; `GET/PUT /api/timeline` (ETag-guarded so the agent and the user never overwrite each other), `POST /api/render?range=a,b` (preview), `GET /api/notes`, `POST /api/notes`. Writes only `projects/<id>/timeline.json`.
- **UI** (plain JS + Canvas/WebAudio, no build step): preview player compositing the current frame (image + motion + overlay templates), multi-track timeline (video, overlay, voice, music, original, sfx) with drag/trim/split, snapping to sentences, words and beats, mute/solo, per-clip gain, a loudness meter; **review-notes mode** (press C, drag a box on the frame, type the note → `review_notes`).
- **MCP server** (`studio/mcp_server.py`, stdio): tools `get_timeline`, `update_clips` (JSON patch), `list_review_notes`, `set_note_status`, `render_preview`, `export`. Claude Code then edits the film the same way the reference was made with Goha AVS.
- **Renderer** (`scripts/render.py`, shared with `doc.py render`): ffmpeg filter graph from timeline.json; overlays drawn as PNG sequences/ASS by Pillow.
