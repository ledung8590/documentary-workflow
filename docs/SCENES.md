# Animated JS graphic scenes

These scenes fill shots that have no unique archival picture. Never merge shots or repeat a picture to cover a gap (`docs/WORKFLOW.md` stage 6).

## Commands
- Render a still to check a frame:
  `node scripts/jsscene.mjs projects/<id>/scenes/<name>.js <out.jpg> --still <t>`
- Render the clip:
  `node scripts/jsscene.mjs projects/<id>/scenes/<name>.js projects/<id>/media/scene-<name>.mp4`
  - It runs at 24 fps by default. A 10 s scene takes about 25 s to render.
- Render a transparent overlay (`bg: 'none'`, `vignette: 0`) to lay over footage:
  `node scripts/jsscene.mjs <scene.js> projects/<id>/media/scene-<name>.mov --alpha`
  - The output is PNG-in-MOV with alpha. Put it on the fx track as a `media_overlay` clip with `blend: normal`, `loop: false`.

`scenes/engine.html` draws each frame in headless Chromium at 1920×1080. It then adds the background texture and a vignette.

## Scene file
A scene file sets `window.SCENE`:
```js
window.SCENE = { duration: 8, bg: 'brown', draw(c, t, L) { /* paint frame t (s) on 2D context c */ } };
```
- `bg` is one of: `brown` (dark brown, quote/diagram cards), `parchment` (stat cards; use dark ink), `black`, `ocean` (dark blue-green), `slate`, `none`.
- `vignette` is optional; the default is 0.55.
- `draw` must be a pure function of `t`, so every frame can be drawn alone. Do not keep state between frames. Use `L.rnd(i, k)` for fixed randomness.

## Kit (`scenes/lib.js`, all on `L`)
**Timing**
- `L.seg(t, a, b)`: eased 0→1 progress from second a to second b.
- `L.lin` is the linear version.
- `L.ease`, `L.easeOut`, `L.lerp`, `L.clamp`.

**Colours**
- `L.C.offwhite`, `L.C.red`, `L.C.redhot`, `L.C.amber`, `L.C.parch`, `L.C.brown`, `L.C.ink`.
- `L.C.blue` is for US/defender, `L.C.bluedeep`, `L.C.grey`, `L.C.steel`.

**Text**
- `L.text(c, str, x, y, {size, font: head|headlight|body|mono, color, align, alpha, shadow, upper})`.
  - Oswald text is uppercase by default.
- `L.typed(c, str, x, y, t, t0, {cps, size})` types text with a block cursor.
- `L.heading(c, kicker, title, t, {x, y, dark})` draws a card heading with a red rule.
- `L.tag(c, text, x, y, t, t0, {sub, align, accent, size})` draws the black map-style label tag, which pops in.

**Lines**
- `L.line(c, pts, p, {color, width, dash, march, glow, alpha})` draws a polyline on to progress p.
- `L.curve(a, b, bend)` gives arc points.
- `L.arrow(c, pts, p, {color, width})` draws a glowing tapered arrow that grows.
- `L.circle`, `L.dot`.
- `L.rings(c, x, y, t, {t0, every, life, rmax, color, a0, a1, count})` draws expanding rings (sonar ping, blast, pulse).

**Naval**
- `L.sub(c, x, y, len, {kind, dir, color, alpha, glow})` draws a side-view silhouette.
  - `kind` is one of `akula`, `la` (US Los Angeles), `victor`, `typhoon`, `ssbn`, `ship`.
  - `dir: -1` faces left.
- `L.noise(c, x, y, t, {dir, strength, color, reach})` draws propeller noise arcs.
- `L.sea(c, {top, t})` draws the water column with a moving surface.
- `L.wavePts` gives wave points.

**Data**
- `L.hbars(c, items, t, t0, {x, y, w, h}, {max, stagger, dark, fmt})` draws growing bars with counters.
- `L.counter(v, p)`.
- `L.timeline(c, y0, y1, [yearA, yearB], events, t, {tick})`.
- `L.network(c, nodes, edges, t)` draws a spy-ring or flow graph.
- `L.grid(c, alpha)`.

## Rules
- **Keep the subtitle band free.** Burned-in subtitles sit at y ≈ 895–985 (1080 p frame, `subtitle_style.y` 0.868).
  - Put no text, counters, labels or key graphics below **y = 860**. Ground, smoke and background are fine there.
  - If a scene must draw in that band, turn the subtitles off for its clip with `"hide_subtitles": true` (render.hide_under_text; in plan.py, every scene except the `SUBS_OVER` set).
  - Check one still at the scene's busiest moment with the subtitle in mind before rendering.
  - In film 74, 13 scenes had their bottom line under the subtitle and had to be redrawn (user review 2026-11-01).
- **Fit the beat.** One scene covers one beat (usually 1–3 shots, 4–12 s). Each element appears on the narrator's word.
- **Keep it moving.** Something must move in every second.
- **Stay in the film's look** (`docs/STYLE.md` "Film look"; the engine loads it from `brief.json`). Colours only from `L.C`: `bg`, `bg2`, `panel` (grounds and boxes), `fg`, `fg2` (text, lines), `accent` (calm second colour), `accent2` (the one mark colour: arrows, rules, dots), `highlight` (rare). `L.FG(a)` / `L.FG2(a)` / `L.BOX(a)` give them with alpha. Never a fixed hex or `rgba(237,231,220,…)`: in the paper look the text is dark ink. Leave `bg` to the engine (any kind becomes the look's ground). Text is book case serif; glow (`shadowBlur`) is switched off in a look. Graphics stay plain like a history book: thin rules, flat bars, dots, boxes with thin connectors, silhouettes. Keep text large: at least 26 px for body, 34 px for labels.
- **Analysis boards (`K.board`, scene names `bd-*`) carry the argument** (user 2026-11-14, the `通史3` reference at 3:13–3:21: one frame = one argument). Our films cut to one picture per sentence and read as a slideshow. A board is one scene over several sentences of the same idea (10–30 s): a small real photo as an exhibit with its caption, beside a diagram (boxes, bars, silhouettes, a doll), links between them, a struck-out claim, and a takeaway line (`conclude`). Each item appears on its word: write `at: @{S146 "vier Jahre"}` (build.py turns it into scene seconds from `starts.json`, written by `plan.py durations`). Later sentences add to the board, move or shrink earlier items (`move`) or dim them (`dim`) instead of cutting away. Boards keep the subtitles (keep content above y 870). Put the board's photos in `SCENE.images` and in `SCENE_MEDIA` of plan.py so credits and LICENSES keep them. Target 30–50 % of the running time; `plan.py check` flags under 25 % and 4+ exhibit photos in a row. Examples: `templates/archival/scenes/examples/bd-*.js` (Barbarossa 19:00–20:00 test; image paths point at that test) and the item list in `_kit.js` above `board(`.
- **Drawn characters (`K.doll`) carry the key human moments** that no real picture shows (decisions, meetings, orders, soldiers' and civilians' experience; `docs/WORKFLOW.md` stage 6, picture mix).
  - Style is exactly film 75's: the kit's egg doll, no other character style. Costumes: 1806–1815 armies, Vietnam 1860s, and since 2026-11-14 `wehr`, `sov`, `us`, `tommy`, `jap`, `navy`, `suit`, `work` with hats `stahlhelm`, `pilotka`, `ushanka`, `m1`, `brodie`, `jpcap`, `peaked`, `fedora`, `flatcap` (sheet: `templates/archival/scenes/doll_sheet.jpg`). A missing costume is added to the kit's `doll()` in the same drawing style.
  - Put `// no-real-media: <what was searched>` in the scene file.
  - `scripts/dollcheck.py` holds the budget: target 20–30 % of running time, `!!` below 15 % or above 35 %; no limit on shots in a row, dolls allowed in the opening.
  - Opposing armies must read apart at a glance.
- **Treat it as an illustration.** Its credit line is "Animated graphic (illustrative)", plus the data source when there is one.
  - The timeline clip gets `kind: video`, `grade: none`.
- **Typed text needs typing sound.** A scene that uses `L.typed` gets typewriter SFX only while the text is typing:
  1. `node scripts/jsscene.mjs <scene.js> <spans.json> --typing` lists the spans in scene seconds.
  2. Map them to film time: clip start + span − clip `in`.
  3. Add `typewriter/el_03` on each span, with a peak about -22 dBFS and an 80 ms fade-out.
- **Check before you finish.** Check at least two stills, mid-build and full, before rendering. Look for overlapping text and labels outside the frame.

## Subscribe overlay (every film)
Every film's subscribe call-to-action ("hit that subscribe button…") gets `scenes/subscribe.js` over its footage:
1. The button pops in.
2. A cursor clicks it, and it turns into a grey "SUBSCRIBED" with a check mark and a burst.
3. The cursor clicks the bell, which rings.

To add it:
1. Render it once per project in the film's language: `node scripts/jsscene.mjs scenes/subscribe.js projects/<id>/media/scene-subscribe.mov --alpha --lang <vi|es|de|en>`. The labels are SUBSCRIBE/SUBSCRIBED, ĐĂNG KÝ/ĐÃ ĐĂNG KÝ, SUSCRIBIRSE/SUSCRITO or ABONNIEREN/ABONNIERT.
2. Add a fx-track `media_overlay` clip (4.2 s) that starts 1.3 s before the word "button" in `voice/words.json`, so the first click lands on "button". In a Vietnamese script, anchor it on "đăng ký".
3. Add these SFX, in film time = clip start + scene time:
   - `whoosh/el_01` at 0 s, gain about -9.
   - `mouseclick/el_01` at 1.27 s and 2.42 s, gain about +9.
   - `subscribed/el_01` at 1.3 s, gain about +11.
   - `notifybell/el_01` at 2.45 s, gain about +8.
   - These gains put the peaks about 15–18 dB under the voice (2026-11-14: SFX 12 dB quieter than before, viewers found effects loud).
