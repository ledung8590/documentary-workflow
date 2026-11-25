# Antigravity / Gemini adapter

`AGENTS.md` (loaded with this file) is the rule book; `docs/WORKFLOW.md` (`/genvideo`, `/gendoc`) and `docs/STORY_MODE.md` (`/gentruyen`) are the procedures. This file only maps what those documents name in Claude Code terms onto Antigravity. Avoid loading all documentation at once. Luôn trả lời người dùng bằng tiếng Việt.

## Same workflow, these names differ
| The docs say | In Antigravity |
|---|---|
| `/genvideo`, `/gendoc`, `/gentruyen`, `/kiem-duyet-kich-ban` | workspace skills in `.agents/skills/` (same slash names) |
| subagent, "Agent tool", group editors, media-search agents | swarm workers (built-in skill `native_swarm`), briefed from `GROUPS.template.md` / `GROUPS2.template.md` |
| "a fresh reviewer" (thumbnail, drawn scenes, frames) | a NEW worker that gets the files and the rule, never your conclusion |
| `documentary-studio` MCP tools (`list_review_notes`, `update_clips`, `render_frame`, `render_preview`, `set_note_status`) | the same server, registered globally (`agy mcp list`); if it is missing, use `PY scripts\doc.py ops JOB ops.json` and read `review_notes` in `timeline.json` |
| PY | `.venv\Scripts\python.exe` (never bare `python`: no GPU render) |
| `bash render_all.sh` | `& "C:\Program Files\Git\usr\bin\bash.exe" render_all.sh` from the project folder (the terminal is PowerShell: no `&&`, use `;`) |
| the user's memory, "memory: NAME" | lessons index `C:\Users\Le Dung\.claude\projects\d--YOUTUBE-TOOL-CODE-BY-ME-documentary-workflow\memory\MEMORY.md`: read it at the start of every job and open an entry's file when its line touches what you are doing (`[archival]` entries do not apply to stories). Read-only. |

## Models (user 2026-11-21: fit the work to the models available here)
- Do not hard-code a model name; `swarm{action:"models"}` lists what this account can run.
- **Main agent, and every worker that judges or creates** (script fact check, shot lists, JS scenes, maps, frame and thumbnail review, review-note fixes): the model the user chose for the conversation. Leave `model` off.
- **Workers that only search or read in bulk** (media search with `doc.py media JOB search`, reading a whole script to mark suspicious passages): the cheapest Flash tier in the list is enough. Their output is always checked by a main-model step, never trusted alone.
- When a model runs out of quota, switch that worker (`swarm{action:"model"}`) and keep the job; never drop a check to save quota.
- At most 3–4 workers at a time. Parallel media-search workers each write their own tag, never the same `candidates.json` tag.

## Rules that code enforces (do not work around them)
- No background music in films or stories, only SFX (user 2026-11-22); the gate fails on music clips.
- `PY scripts\gate.py JOB plan|studio|deliver` until it prints PASS (`docs/WORKFLOW.md` "Gates"). `doc.py studio` and `scripts\export.py` refuse on a failed gate. Never set `DOC_GATE_SKIP` unless the user says in chat to skip the checks.
- The studio review is the only stop: open it, tell the user in Vietnamese what to check, end the turn. Export only after the user approves in chat, with `PY scripts\export.py JOB`. Script fixes are never a stop: fix, then report before/after.
- Paying commands dry-run first, then `--run` (AI84 / ElevenLabs spend is pre-authorized). Never print keys.
- Long commands run in the background with a progress check within 5 minutes; never wait without a limit. Stop only processes whose command line belongs to this project, never by name.
- Do not edit `scripts/`, `studio/` or `templates/` in the middle of a film unless a check or tool is wrong; after such an edit `PY -m pytest tests -q` must pass (the gate runs it).
