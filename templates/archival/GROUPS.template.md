# Brief template for group editors (copied from the space-race film, 2026-11-14): replace <job>, the film facts, ranges and chapter cards

Workspace root: D:\YOUTUBE\TOOL_CODE_BY_ME\documentary-workflow (run everything from there with `.venv/Scripts/python.exe`, call it PY).
Project: projects/<job> (call it P). Job id = that folder name.
English film, ~73 min, look **paper** (cream paper, navy, ink, one muted red; Source Serif; book case, no caps).

Read first (in this order, only these): P/STORY.md (chapters, cold open design, emotional curve), P/FACTS.md,
docs/STYLE.md section "Film look", docs/SCENES.md, docs/MAPS.md (top paragraph on flat maps + scene JSON), docs/MEDIA.md,
the docstring of P/plan.py, P/sentence-index.txt (your sentence range), P/voice/timing.json (word timings).
Reference films (read-only, to copy the craft): projects/_ref/moon/barb (newest, same look: shots-*.txt, overlays-*.txt,
scenes/src/*.js incl. boards), projects/_ref/moon/ww1, projects/_ref/moon/f88. Board examples: P/scenes/examples/bd-*.js;
board/doll API: comments above `board(` and `doll(` in P/scenes/src/_kit.js.

## Your output (only these files; never touch another group's files, never edit _kit.js, plan.py, shots.txt, overlays.txt, sound.txt, timeline.json)
- P/shots-X.txt and P/overlays-X.txt (X = your group letter), lines in time order covering exactly your sentence range.
  Start with a comment line naming your range and film sources. Your first line anchors on your first sentence's start
  (or the chapter card just before it, `S149$+0.2 | card | …`).
- P/scenes/src/X-*.js (JS scenes and boards; boards are named `bd-X-*.js`), P/maps/src/m-X-*.json (flat maps).
  Optional helper `P/scenes/src/_X.js` (shared helpers for your group only; prefix every function name with your letter).
- P/picks-X.txt: one line per used pick `TAG#K | Commons/NARA/DVIDS file title or URL | licence | what it shows`.
- Media search tags: `p-X-name` (photos) and `v-X-name` (film). Never reuse a tag name of another group, never run searches
  in the background after you report, and kill nothing you did not start.
- P/qa/X/ for your stills and sheets.
- When done, report: sentence range covered, number of shots, seconds of boards / dolls / photos / film / maps, list of scene and map files, anything unresolved.

## Picture mix for your range (enforced by `plan.py check`)
- Analysis boards (`scene:bd-X-…`, K.board) 30–50 % of your running time: sentences that analyse, compare, explain cause and effect.
  One board spans several sentences of one idea (10–30 s); each item on its word: `at: @{S146 "word"}` (built later from starts.json).
  Real photos on boards are exhibits (put them in `SCENE.images` as '/projects/<job>/media/<file>' – see below for the file names).
- Drawn characters (K.doll) 20–30 % of time (doll shots or boards with a doll count by shot; target your share): key human moments
  no photo shows: decisions in the Oval Office/Kremlin/Pentagon, engineers arguing, Korolev in the Gulag, Leonov's spacewalk,
  NSC meeting, Congress vote, analysts at NRO… Costumes available: `suit` (politicians, officials; hat 'none' or 'fedora'),
  `usaf` (USAF officer, hat 'peaked'), `us` (Army, 'm1'/'peaked'), `navy`, `sov` ('peaked' officer, 'pilotka', 'ushanka'),
  `lab` (engineer in white coat), `work`, `astro` (US pressure suit) and `cosmo` (Soviet suit) with hat 'space'. Each doll
  scene file starts with `// no-real-media: <what was searched>`. Opposing sides must read apart (red star / СССР vs US flag).
- Real media only where it proves something: the real rocket, person, place, document. Standalone photos fill the frame;
  `pick:TAG#K+exhibit` mounts one on paper (documents, small portraits). Never 4+ standalone photos in a row.
- Flat maps for every place, route, range (Natural Earth look, labels in English, book case). Credit is automatic.
- A new picture every ~3–6 s; never > ~25 s without a map, scene, card or callout; still photos ≤ 7 s; film cuts 2–6 s.
- **Never the same picture twice in the film, never merge shots to hide a gap** (gap → map, JS scene, board, card).
- **Across films:** `plan.py check` (filmrepeat) flags footage earlier films used: `!!` for any repeated film cut and for
  anything in the first 90 s. Earlier films used Operation Dominic/Starfish-era nuclear test film (film 87), Project Pluto,
  Typhoon/Ohio/Akula/Kirov naval film, WWI/WWII film. Grep `evidence/*/project/timeline.json` for a file name before using it.

## Media rules
- Licences: public domain, US federal works (NASA, USAF, US Army, NARA, DVIDS US units), CC0, CC BY, CC BY-SA only.
  No NC/ND, no Roscosmos/TASS/RIA unless the Commons file carries a valid PD/CC tag (PD-RU-exempt / PD-Russia-1996 etc. are fine when the file page says so).
- Search: `PY scripts/doc.py media <job> search "short query" --tag p-X-name [--kind photo|video] [--n 8] [--sources commons,nara,dvids]`,
  then look at P/qa/media-<tag>.jpg. Short queries work. NASA images: Commons category files from NASA are PD.
- Every `vid:` cut gets an exact in-point `@IN!` that you checked on a 1 s strip of the cached source
  (frames at IN, IN+1, IN+2 … from media/candidates/<tag>/; low-res sheets drift up to ~100 s on long reels, intertitles and leader).
- Captions say what the picture really shows ("Saturn V AS-506 lifts off, 16 July 1969"); a stand-in gets "(illustrative)".
- Shots that show firing, launching or exploding: caption says so only if the clip really shows it at that frame.

## Text and overlays (overlays-X.txt)
Types used in the reference: `chapter` {"n", "title"}, `date_tag` {"text"}, `lower_third` {"kicker","name","sub","plate":true,"plate2":true},
`callout` {"text","plate":true}, `quote` {"kicker","title","lines":[…],"cps":16}, `question` {"text"}, `stat` cards with
`items` (each `"at": "S043 \"500,000\""` on its word). See projects/_ref/moon/barb/overlays-*.txt for exact props.
Book case English, no caps. Never a callout or date tag over a JS scene that has its own labels. Scene text never below y 860. Scene text never under the top-right source label (y < 120 right of x 820; render adds it, stills do not show it): board titles top-left or below y 120; lookcheck flags it (film 91).
Chapter cards: chapter numbers and titles exactly as in STORY.md. Group A also does the title card (film title) after S022.

## Checks before you report
1. `PLAN_PART=X PY P/plan.py check` until no `!!` lines for your part (doll/board shares are printed; the first shot of a part
   always starts at 0 s in a part check, ignore that and the last shot's length).
2. Every scene and board: build and render two stills (mid-build and full) and LOOK at them:
   `cd P/scenes/src && PY build.py X-name && cd -` then `node scripts/jsscene.mjs P/scenes/X-name.js P/qa/X/X-name.jpg --still <t>`.
   @{…} anchors need starts.json: first run `PLAN_PART=X PY P/plan.py durations` (merges your scenes' durations/starts
   into the shared files, other groups' entries are kept; maps are not written). Rerun it after changing shot anchors.
   Look for overlapping text, text out of frame, text below y 860, colours outside the look.
3. Every map: `PY P/maps/write_maps.py` is NOT for you (it rewrites all maps); render a still with
   `node scripts/mapscene.mjs P/maps/src/m-X-name.json P/qa/X/m-X-name.mp4` only if quick, else check the JSON carefully.
4. Do not render final scene/map videos and do not run `plan.py durations/apply`, `render_all.sh` – the lead editor merges and renders.
Work autonomously; never ask questions (no one is there). Commands only, no interactive prompts.

## Chapter cards and holds (voice pacing already set)
The last sentence of each chapter (S031, S056, S127, S149, S200, S289, S391, S443, S516, S580, S678) has a locked 3.2 s pause.
Put the chapter card in that silence: `S056$+0.2 | card | Chapter 1: …` in shots and `S056$+0.2 .. S057+0.3 | chapter | {"n": 1, "title": "…"}` in overlays.
Group A: the film title after S022 (S022 has a 3.0 s pause) is a designed JS scene `scene:a-title` (like barb `a-title.js`), title "What If the USSR Reached the Moon First?" with a short subtitle.
Dramatic holds (1.6–2.8 s silence after): S010, S013, S039, S077, S124, S145, S173, S333, S435, S438, S515, S702, S705 – give these a strong picture beat.


## Also required (lessons of the space-race film, 2026-11-14/15)
- Read GROUPS2.template.md: draw boards in the 通史3 grammar (exhibit, note, craft line-ups, legend), not chains of boxes.
- Combat lines get combat: every attack/battle/invasion/sinking sentence shows a real film cut or a moving combat scene
  (scenes/examples/combat, helpers scenes/src/_w.js); `plan.py check` flags it.
- Moments with no real picture may get a reconstruction print (scenes/examples/r-open.js style, scripts/printgrade.py),
  labelled "Reconstruction (generated)" with "imagined" in the description; dolls stay.
