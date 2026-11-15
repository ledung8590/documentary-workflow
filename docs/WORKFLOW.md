# Canonical /gendoc procedure

**Reply to the user in Vietnamese at every step** (AGENTS.md); film text follows the script language.

Fiction over the user's own images is a different path: `/gentruyen`, `docs/STORY_MODE.md`.

Run from the workspace root with `.venv/Scripts/python.exe` (PY). Built stages are marked **[built]**; the others are **[planned]**: say so plainly and stop there, do not improvise a substitute. Stage 10 is a hard stop: the user reviews in the studio before any final output. Every paying command dry-runs first to show the cost; the user has pre-authorized AI84 and ElevenLabs spend for quality (2026-11-01), so then run it with `--run` without asking.

## 0. Start gate [first thing, user still present]
**Before anything long, do every step that can raise a permission prompt, so the rest can run unattended (user rule 2026-11-12).** `evidence/` is a junction to drive F:, and a copy from it asks for permission; asked later, it stops an unattended run (film 95, 2026-11-11). So in the first minutes: copy every reference you will need from `evidence/` (newest `plan.py`, scene helpers such as `_j.js`, `thumbnail.py`) and run any other command you already know will ask (writes outside the project, junction paths). Say in your first message, in Vietnamese: "Bấm Allow cho các lệnh sắp tới, sau đó bạn có thể đi ngủ." Reading `evidence/` needs no prompt: media-search subagents grep `evidence/*/project/timeline.json` to avoid earlier films' footage. Never drop a quality step to avoid a prompt; move the prompt to this gate.

## 1. Ingest [built]
`PY scripts/doc.py doctor` (setup: `powershell -ExecutionPolicy Bypass -File scripts/setup.ps1`). Then `PY scripts/doc.py ingest`.
**Default input:** a narration script `input/<name>.txt` (or `input/<name>/script.txt`), with mode `tts`.
- Ingest detects the language (ja/vi/es/de/en; `job.json` "language" overrides) and picks the narrator voice for it (`VOICES` in doc.py: en Brian, es Alberto, de Robert Ranger, vi Tung Dang, ja Koichi Yashiro - Deep Cinematic `4oeIbMTUt5QeJy4ZX1FC`, chosen by the user 2026-11-04; `voice.voice_id` overrides). Japanese is detected by kana. Japanese text is drawn in M PLUS 1p Bold (`assets/fonts/MPLUS1p-Bold.ttf`, OFL, the user's font 2026-11-04): render.py uses it for every card and subtitle when the language is ja, and the scene and map engines fall back to it for kana and kanji only (Latin keeps Oswald, Be Vietnam Pro and Plex). Card titles break between characters, preferring after 、。 The chapter label is 第N章. fontcheck.py checks Japanese films against M PLUS 1p.
- The voice is the user's MiniMax cloned narrator for the script language (TUNG_DUY_V2 vi, LS_US en, LS_ĐỨC de, LS_NHAT ja, LS_TBN es), read in whole chunks without emotion tags; Whisper cuts it into sentence clips with real word timings, and the SRT comes from those clips (user 2026-11-14: viewers disliked the sudden emphasis of per-sentence eleven_v4 jobs with emotion tags).
- **Everything visible follows the script language:** overlays, captions, "illustrative" notes, map labels, card words, credits wording.
- **Supplied narration** (`<name>.wav` + `<name>.srt`, mode `narration`) is still supported; its voice is only re-paced, never regenerated, unless the user asks for `voice`.
- Empty input: ask for a script.
- Ingest resumes unchanged jobs. Read `brief.json` and `state.json`.

## 2. Research and outline [manual, agent]
Read the whole narration (SRT text, a chunk at a time for long films). Write `projects/<id>/FACTS.md` (claims, dates, places, sources, uncertainties) and `STORY.md` (acts, chapters, emotional curve, where the big beats and title cards go). If the script has a factual error, fix it yourself in the script (smallest change), record it in `FACTS.md`, and list every change (before/after) in your Vietnamese report. Do not ask first (user rule 2026-11-12).

**Script review (do it in this stage, before `split` and any voice):** run the skill `/kiem-duyet-kich-ban <script .txt>` (user-level skill; scan.py + Haiku reads all + Opus verifies only flagged parts). It catches stray notes read aloud by TTS (a 2026-11-04 test script had `---` and a note "(TTSには入れない注記) ... 直してください" mid-script, plus the wrong detail the note pointed to), clichéd openings, repeated ideas, internal contradictions, wrong dates and weekdays. Run it with `--auto`: it fixes group 1 itself (exact-text edit, backup in the temp folder), and you fix the clear group-2 items too (repeated idea, clichéd opening, mixed Japanese style) without asking (user rule 2026-11-12). Leave `chua_chac` items unchanged and record them in `FACTS.md` as uncertainties. Show the user the before/after table in your Vietnamese report afterwards. Do not run `split` or `tts` while a group-1 item is unresolved.

## 3a. Script jobs (default): sentences, emotion, voice [built]
1. Run `split JOB`. The agent reviews every sentence's `emotion`, and may set `tag` (v4 audio tag), `say` (spoken form of numbers or names) or a locked `pause_after`.
2. Run `tts JOB` (dry run: characters ≈ AI84 credits), then `tts JOB --run`. The MiniMax cloned voice reads whole chunks (up to 9,500 characters, cut at chapters) with its own continuous expression, no emotion tags; Whisper cuts each chunk into one clip per sentence at the real pauses and gives real word timings, so shots, boards and subtitles anchor on words exactly as before (`docs/VOICE.md`, MiniMax section). The per-sentence eleven_v4 mode with emotion tags is only a fallback for a language without a cloned voice. Results are cached; `--only S004` redoes one sentence. Read the list of poorly heard sentences it prints.
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
  - **Real combat film in the first ~10 s, even when the cold open is calm** (user review 2026-10-31: a ship photo at 0:06 was "nhạt"). Put 1–2 short cuts of weapons firing (a launch, a torpedo or missile hit, gunfire; DVIDS SINKEX/launch film) on the line that names the threat or the weapon ("a heavily armed adversary"), with launch/blast SFX about 14 dB under the voice (2026-11-14: all SFX 12 dB quieter than before, `gen_sound.QUIETER`). Where the script's moment is a dud or a near miss, show the firing, not a blast.
  - Plan the hook in STORY.md at Stage 2.
  - **The whole intro is creative motion design** (user review 2026-11-04, film 6). The intro is the cold open plus the setup lines up to the first chapter, about 60–90 s. Its first draft was photos with a few cards; the user called it "quá nhạt… khán giả dễ bỏ đi" (too bland, viewers leave easily) and said you are free to think creatively ("phải biết tư duy sáng tạo, ko hẳn theo khuôn"), in the style of a military-history analysis documentary.
    - Design each intro sentence as its own visual idea, not one template. Examples:
      - an old map with marching lines that race to one point and pop a portrait frame, with a flash;
      - a portrait that flies in, with a light sweep, a name plate and a crack;
      - accusation words slammed as stamps;
      - province plates flipping to the enemy flag;
      - a year counter rewinding;
      - two civilisations colliding on a diagonal split;
      - a life counter, plus measured panels for wall thickness and muzzle velocity.
    - **This is a separate rule from the combat-film rule above; both apply** (user 2026-11-04: "vẫn ưu tiên kèm cả video nổ đầu đó… nó riêng").
      - The real combat/blast clips in the first ~10 s (the bullet above) stay as their own full-frame cuts, with priority. They are not a background under the graphics.
      - The motion-design scenes are their own cuts too, never a replacement for the combat clips.
      - For pre-film eras, use reenactment fire and blast film labelled illustrative (film 6: cannon crews firing).
    - Build with real archival images inside JS scenes (`images:` + `K.photo`, `K.stamp`, `K.sweep`, `K.flashAt`, `K.streaks`), with SFX on every hit. Reference: film 6 `evidence/6. Phan Thanh Giản…/project/scenes/src/o-*.js`.
- **Weapons footage.** Wherever the narration names a weapon or a strike, show real weapons film (DVIDS SINKEX and launch footage, `docs/MEDIA.md`) with blast or launch SFX on the hit frame. Under the voice, keep SFX peaks 2–3 dB below the voice peaks.
- **Subscribe call-to-action.** The narration's "subscribe" line always gets the animated subscribe overlay: the button, a cursor click, the switch to "Subscribed" with FX, and the bell, with click SFX (`docs/SCENES.md`, Subscribe overlay). This rule comes from the user review on 2026-10-31.
- Never more than ~25 s without a map, scene, card or callout. Still photos fill at most about half the screen time.
- **Never merge shots to hide a missing picture, and never use the same picture twice in a film** (user rule). A shot with no unique archival picture gets a map, a JS scene or a card.
- **Across films** (user 2026-11-04, film 88). YouTube's policy allows reused footage with a storyline or commentary, and it names no limit in seconds. The risk at hundreds of films is its "inauthentic content" rule: repetitive or mass-produced videos, judged across the channel. So films must not look like one template:
  - `plan.py check` (`scripts/filmrepeat.py`) compares against `evidence/*/project/timeline.json`: `!!` for anything repeated in the first 90 s and for any repeated film cut, `!` for later stills, which may repeat.
  - Every opening is its own idea drawn from that script's subject, in its era where possible. Do not start from the previous film's opening or from generic firing film; `cannon fire` searches return the same few files (film 88's first draft opened with the cannon of films 6 and 75).
  - Tell media-search subagents which sources earlier films used.
- Before the studio stop, count media keys used more than once (must be zero) and compare a contact sheet of the draft with the reference (2026-11-14: the `通史3` look reference: one colour family, exhibits, flat maps).
- **Analysis boards, not a slideshow** (user 2026-11-14): sentences that analyse, compare or explain cause and effect go on `K.board` boards (`scene:bd-NAME`, one scene over the sentences of one idea, items on their words, `docs/SCENES.md`); a photo there is an exhibit inside the argument. Plan boards first when writing shots.txt: target 30–50 % of the running time, exhibits standing alone only between them.
- **Real media only where it proves something** (user 2026-11-14): the reference uses few archive photos, shown as exhibits; most of the film is look-coloured graphics, flat maps and drawn characters. Standalone photos fill the frame; on boards they are exhibits; `+exhibit` mounts a standalone one on the paper.
- **Picture mix: real media plus drawn characters** (user, 2026-11-14). After film 75 the rule "drawn characters last" left every film from 76 to Barbarossa at 0–2 % dolls, almost all maps and graphs, which the user found dry. Film 75 (34 % dolls) is the model.
  - Real period media (photos, paintings, engravings, film) stays first for things that were photographed or filmed: the real person, weapon, ship, place, event.
  - **Drawn characters (`K.doll`) carry the key human moments** that no picture shows as such: a decision in a room, a meeting, an order, an argument, a soldier's or civilian's experience, a cause and its effect acted out. Rank them level with maps and figure-less JS graphics, and prefer them for any beat about what people did, thought or felt.
  - A modern stand-in (reenactment, museum object, the place today) is captioned "(illustrative)" in the script's language.
  - **Reconstruction prints** (the 通史3 再現（生成） pictures, user 2026-11-14) for key moments with no real picture, besides the dolls: media keys starting `r-`, label "Reconstruction (generated)" plus "… imagined; shapes simplified", never the word AI. Generate them on the local **Z-Image** (`docs/ZIMAGE.md`: the default image source since 2026-11-14; TST Auto Generate Image is switched off), one seed per film, with the indigo-lithograph prompt prefix, and follow ZIMAGE.md "What Z-Image cannot draw" from the first prompt (no helmets, writing, insignia, radios, people lying down). Run the 9-per-sheet defect check (`docs/STORY_MODE.md`) on every print before it goes into shots.txt.
  - Budget, enforced by `plan.py check` via `scripts/dollcheck.py`: **target 20–30 %** of running time; `!!` below **15 %** and above **35 %** of shots or time; no limit on doll shots in a row, and dolls may appear in the opening (user 2026-11-14: film 75 did both and viewers liked it); every doll scene file carries `// no-real-media: <what was searched>`.
  - A film's `plan.py` is copied from the newest `evidence/*/project/plan.py`. Its `check()` must end with `dollcheck.check(D, sh)`; add the call if the copy lacks it. Fix every `!!` line before the draft render.
  - **Style: exactly film 75's dolls.** Only `K.doll` (egg body, dot eyes, one-stroke mouth, hat on top) on the kit's backgrounds or `K.stage`; no second character style, no images from an image model in their place. Costume reference: `templates/archival/scenes/doll_sheet.jpg` (1815 Prussian beside the 20th-century sides).
  - **Missing costume → draw it into the kit.** When the film needs people the kit lacks (another army, era, uniform, headgear, robe), add the side/hat to `doll()` in `templates/archival/scenes/src/_kit.js` (and the project copy), drawn the same way: same egg, collar, chest details, felt/steel gradients and rim stroke. Check it accurately against period references (colour, collar insignia, helmet shape), render a still (`node scripts/jsscene.mjs <scene.js> <out.jpg> --still 1 x`) and look at it before using it.
**Edit plan (the archival toolkit, never `doc.py story`).** The picture, overlays and sound are written as plan files and built into the timeline by the film's `plan.py`. Do not fill per-sentence slots one by one: that gave the "crude slideshow" of 2026-10-31.
1. `PY scripts/doc.py plan JOB` copies `templates/archival/` into the project: `plan.py`, `gen_sound.py`, `render_all.sh`, `scenes/src/_kit.js` + `build.py`, `maps/write_maps.py`, and skeletons of `shots.txt`, `overlays.txt`, `sound.txt`. It refuses story jobs. Improve the template in `templates/archival/` when a film teaches something general, not only the project copy.
2. Write `sentence-index.txt` (S-id + text) and split the film into 3–4 groups. Search media for the groups in parallel (subagents): `doc.py media JOB search "short query" --tag T [--kind photo|video]`, look at `qa/media-T.jpg`, note picks in `picks-*.txt`. Short queries work; long ones return nothing. Start the search while TTS runs.
3. Per group, write `shots.txt` lines: `ANCHOR | pick:T#K / vid:T#K@IN / scene:NAME / map:NAME / card | caption` (a new shot every ~3–6 s, anchors on the word the picture belongs to; syntax in the `plan.py` docstring). Write `overlays.txt` (cards, date tags, lower thirds, callouts; list items `"at"` on their word) and the music beds in `sound.txt`. Merge the groups.
4. `PY projects/JOB/plan.py check` until it prints no `!!`: anchors, shot lengths, repeats across groups, overlapping film cuts, the drawn-character budget (`scripts/dollcheck.py`), and `scripts/reviewcheck.py` (film 76, 2026-11-03): overlay text inside the frame (each overlay drawn by render.py and measured), every `L.typed` scene has typing sound, and every film cut whose caption says it fires or explodes has a `FIRE` entry in gen_sound.py. Find the muzzle or impact frame on the cut clip (a blast can be a dark smoke puff, not a bright flash) or reword the caption.
5. **Maps: mix flat and 3D** (user 2026-11-14): real places, terrain and distances get `"base": "satellite"` 3D maps (tilted, slow orbit), about 40–50 % of the maps; overviews and label-heavy maps stay flat Natural Earth (`docs/MAPS.md`).
6. **Film look first** (`docs/STYLE.md` "Film look"): `brief.json` `"look"` is `paper` (default) or `dark`; every scene, map, card, overlay and doll follows it. `plan.py durations`, then write the JS scenes (`scenes/src/NAME.js`, `docs/SCENES.md`) and map specs (`maps/src/NAME.json`, `docs/MAPS.md`) for the scene and map shots; `scenes/src/build.py` and `maps/write_maps.py`, then `bash render_all.sh` (3 renders at a time, hard timeouts, plus the subscribe overlay in the film's language), then `PY scripts/lookcheck.py JOB` until it prints no `!!`.
7. `plan.py apply` writes the video, overlay, sfx and music tracks through the studio store and downloads every pick (`doc.py media pick`: credit + `LICENSES.md` row). Then contact-sheet every film cut against its caption (in-points drift and shared footage repeats).
8. Later changes: edit the plan files and rerun `check` / `apply`, or small fixes with `update_clips` / `doc.py ops` (moved clips re-anchor to the nearest word).

## 7. Music [built: shared library + placement; beat grid planned]
Per chapter, pick a mood bed from `assets/music/<mood>/` (read `assets/music/MOODS.md`: no drum or pulse beds under narration, 2–3 min per bed; military films give each chapter one of the six music groups in MOODS.md, from the user's guide `Huong_dan_nhac_nen_phan_tich_lich_su_quan_su.md`, including key-line music dips `ANCHOR .. ANCHOR | dip | dB`) and write it in `sound.txt` (`ANCHOR .. ANCHOR | music/mood/el_01 | gain`); `plan.py apply` places it, ducked. Measure the ducked music **about 30–32 dB under the voice, only a faint trace** (user 2026-11-14, four times; 21 and 26 dB still too loud on the space-race film, "nhạc nền chỉ tý xíu thui": viewers complained the music was loud; was 8–10 dB. The 通史3 reference keeps a bed under ~90 % of the film but about 28 dB under the speech peaks in the pauses, so it is heard only in real pauses and at section breaks; `tl.duck` release 2000 ms keeps it down between sentences) (`render.premix(only={'music'})` vs `only={'voice'}`) and adjust the gains before the studio stop. Missing moods: `PY scripts/music_elevenlabs.py MOOD --seconds 90 --prompt "..."` dry-runs with the live balance, then `--run` (spend pre-authorized; stay within the balance, `docs/MUSIC.md`). Suno only as the user's manual Pro downloads. Beat-grid snapping (librosa) is **planned**: cut on phrase ends by ear instead. Rerun `assemble` after placing music if sentence starts should land on beats.

**Opening music intro (automatic, user 2026-11-14/15):** the voice starts at 2.6 s (`voice.lead_in`); `plan.py apply` adds an intro bed from 0 s (about the voice's level, not ducked, fading out over ~6 s under the first words), like the 通史3 opening. The file changes every film ("xoay vòng đỡ nhàm, hợp video"): a bed of the opening chapter's mood (or brief `intro_mood`) that earlier films used least as an intro, never the first bed's own file. Never deliver silent first seconds; the picture moves from frame 0 (fade from black on a moving print, title over it).

## 8. SFX [built: shared library + placement]
`PY projects/JOB/gen_sound.py` writes `sound_scenes.txt`: card hits, typing, scene events (`scenes/events-NAME.txt`), film-clip firing (`FIRE`) and the subscribe sequence (`SUBSCRIBE_AT`), each gain set from the file's own loudness at a fixed dB under the voice and cut at its shot end. Then `plan.py sound`. Hand-placed one-shots go in `sound.txt`.
Word-anchored one-shots from `assets/sfx/<type>/` on the `sfx` track (`add` with the event's time: the anchor goes to the word naming it), plus field sound of archival film on `original` (`docs/SOUND.md`). Sparse, under the voice; cards get an audible hit.
**Card and typing checklist (before the studio stop; missed twice, user review 2026-10-31):**
- Every `quote` overlay: `typewriter/el_03` from card start + 0.7 s for chars/cps (`render.card_quote`), stopping on the last character, then `typebell`. Gain about -18 (≈22 dB under the voice above 400 Hz).
- Every JS scene that uses `L.typed`: `gen_sound.py` writes `scenes/typing-NAME.txt` itself from `jsscene.mjs --typing` and puts a typewriter on each span (film 76: two typed scenes were silent when the files were hand-written).
- Every chapter card: whoosh + chapterhit + subdrop + `cardslam` (mid/high layer); every question card: `cardslam` + impact; title cards: revswell + titlehit.
- Every JS scene that draws gunfire, cannon shots, bursts or a charge gets one sound per visible flash or burst, in sync with the frame. Write a per-scene table of events (nominal scene seconds, scaled to the shot) and use `gunshot`, `rifles`, `artillery`, `shellburst`, `mgburst`. The user caught silent firing in film 74's Dreyse/Chassepot graphic (2026-11-01).
- No callout or date tag over a JS scene that has its own labels: the text overlaps. Design scenes with the subtitle band (y > 860) free of text (docs/SCENES.md). plan.py hides the subtitles on every scene clip (`"hide_subtitles": true`, render.hide_under_text) so they never repeat or cover the graphic's own words; only scenes with no text of their own go in `SUBS_OVER` (films 74-88 did this; the 2026-11-02 template had flipped it to opt-in, and film 89 showed subtitles over its graphics). Both rules come from user review 2026-11-01.
- Grep the sfx track for each quote overlay's start before opening the studio.
- **Closing A/B/C question:** each item appears on its own letter word (`"at": "S280 \"A\""`), never one sentence early or late. Sentence ids shift when `split` is rerun, so read the text from `voice/timing.json` before anchoring, and check with `render_frame` 0.3 s before and after each letter. The user has had to point this out in almost every film (film 75, 2026-11-02).
- New SFX types via `scripts/sfx_elevenlabs.py` (dry run, then `--run`; spend is pre-authorized).

## 9. Draft render [built: `doc.py build JOB --only picture`]
First run `PY scripts/fontcheck.py JOB`. It must pass. A character missing from its font renders as an empty box: in film 74, "→" was missing from Oswald. The check covers overlays, subtitles, JS scenes and map labels. The house fonts cover vi/en/de/fr/es completely, including ä ö ü ß ẞ „ “ « » – —. Subtitles use `military` (Saira Condensed Bold) for every language.
Renders `render/picture.mp4` from the timeline on the GPU (`scripts/render_gl.py`) in 3 parallel parts with NVENC encoding, the same path as the studio's whole-picture render (`core.render_range`, ~157 fps: ~10–12 min for a 65-min film; x264/CPU fallback), and saves the render state so studio exports only re-render edited ranges. (Before 2026-10-31 `build` rendered in one process with x264 at ~31 fps: 3–4× slower.) Not a deliverable: it is what the studio plays and splices into. Then run `PY scripts/reviewcheck.py JOB --sheet` and look at every sheet it writes (`qa/shots-NN.jpg`: the middle frame of every shot with its id, time and caption) before the studio stop. Sampling ~20 frames missed film 76's title running off both edges.

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
`PY scripts/doc.py qa JOB --video FILE` on the exported file: black, freeze (flags anything not on an intentional card), loudness, true peak. `--stt` dry-runs; with the user's OK `--stt --run` transcribes with ElevenLabs Scribe and compares words with the SRT/script (target ≥ 97 %; judge names/spellings rather than hiding them). Then inspect real frames at every flagged time, transitions and maps. `doc.py qa` does not read text: run `PY scripts/reviewcheck.py JOB --cards FILE` and look at every `qa/cards-NN.jpg` (each overlay cut from the exported file), never a sample; one text defect means scanning all cards and subtitles of that kind. Japanese cards that wrap need a chosen break, a space in the text (`plan.py check` flags them, cues that start with punctuation, and name cards or callouts under 2 s). Say a film is ready only after this. Record what was and was not checked.

## 13. Deliver
`output/<id>/video.mp4` (or the approved `video-studio-<time>.mp4`), `LICENSES.md`, `credits.txt` (description-ready attribution), `qa.json`. Never upload.
- **Thumbnail** (user 2026-11-14: build every archival thumbnail around the reference channel's best thumbnails, `C:/Users/<user>/Downloads/thum`, 164k–41k views; the high-view ones all carry a **year/date label**). Make a 1280×720 JPG with `PY scripts/thumb.py spec.json out.jpg` (the film's `thumbnail.py` keeps the spec):
  - **A real archival photo** fills the frame (B/W print, light grade), the film's strongest picture of the subject: a ship, a tank column, a portrait. Use the same licensed photos as the film and name them in the description note.
  - **A year/date label, always** (`tag`): a small navy or black box with white text, e.g. "Unternehmen Barbarossa · 22. Juni 1941", "Foto: Juni 1941".
  - **A few big words plus ONE red emphasis** in the script's language: a number ("9–17 Wochen", "約2倍"), a question ("Warum scheiterte er 1941?") or the event's name in huge red letters with a white outline.
  - **Four layouts** (pick by the hook): `panel` (dark panel bottom-left, serif title, red number, inset second photo), `portrait` (commander's portrait strip left, two white lines, huge red event name), `question` (serif title top-left, white question on a red box, label bottom-left), `band` (light top with kicker and black title, red bottom band with the date and the headline).
  - A tiny photo credit sits bottom-right, like the reference. It must read at 320×180; look at it full size before showing it.
  - The older image-model composite (portrait + disaster + stencil hook) is now only a fallback when no strong real photo exists. Make it on Z-Image (`docs/ZIMAGE.md`, a few seeds, the person described in a Character Sheet) or, when the real face must be kept, on Google Flow with the photo as reference; not on TST Auto Generate Image (switched off 2026-11-14).
  - **Check it before showing it** (user 2026-11-14: the Barbarossa thumbnail showed the wrong tank type and was caught only when the user asked). Every thumbnail, every variant, every redo:
    1. `PY scripts/thumbcheck.py JOB out.jpg`: numbers and years against the script/FACTS, each photo's Commons record (title, date, categories), type/model words and names against those records, a year/month label the record does not support. Fix every `!!`.
    2. A **fresh reviewer** (Agent subagent that did not make it) reads the image and the check sheet, identifies independently what each photo shows (vehicle/ship/aircraft model by its visible features, the person, uniform, era; web search allowed) and checks every word, number, label and the spelling. Fix every error and run both again.
    3. Show the user the thumbnail with one line on what was checked ("Panzer III confirmed: cupola, 6 road wheels; label 1941 matches the record"). Never present an unchecked thumbnail.
- **Description.** Build `description_youtube.txt` with `PY scripts/description.py JOB --intro intro.txt [--note note.txt] --tags "t1, …, t7" --hashtags "#A #B #C #D #E #F #G"`. You write the intro and the note in the script's language; the script adds the rest:
  - chapters, starting at 0:00;
  - public-domain sources by archive;
  - every Creative Commons file on screen, with author, licence and Commons ID (grouped by author; Bundesarchiv as "Bundesarchiv, Bild …");
  - map and music credits;
  - few links (user 2026-11-04: a block of 49 archive links looks like spam): sources are named in text, with one Commons ID link and no source-URL blocks. Add `--no-links` only when the user says the film is for a new channel; it strips every URL and domain;
  - a line of 7 #hashtags (one word each, script language) just above TAGS, so YouTube picks them up and shows them above the title (user request, 2026-11-01);
  - the TAGS line.
  The text must be ready to paste into YouTube and stay under 5,000 characters. Never write "see credits.txt" or point to any internal file: the viewer cannot see them (user review 2026-11-01).
- **Names.** Rename the video and the thumbnail to the input script's file name, e.g. `85. Soviets Make … Fa.mp4` and `.jpg`. Copy `description_youtube.txt` next to them.
- **Tags.** End `description_youtube.txt` with a `TAGS` block. It holds 7 YouTube tags in the script's language, comma-separated on one line, under 500 characters: the topic, the war or event, the key people, and the genre (e.g. "Militärgeschichte"). The user pastes this line into YouTube's tag field (user request, 2026-11-01). Also give the tags and the 7 hashtags in the chat when delivering.
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
- **Leftovers:** once the pack is built, delete everything left in `projects/<id>/` (render, unused candidates, voice clips, working notes, logs) without asking: anything not needed as evidence goes (user rule 2026-11-03). Before deleting, copy into `evidence/<name>/project/` whatever the evidence still needs that evidence.py does not move (e.g. the image-model sources of the thumbnail in `thumb/`, intro.txt, note.txt).
- **Reruns:** the script can be rerun after a partial run. A folder the studio holds open is copied and its empty shell is left behind.
