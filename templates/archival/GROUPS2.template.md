# Rework brief (2026-11-14): redraw the explaining graphics in the reference's style

User: the draft "looks like a PowerPoint"; "draw the notes like they do"; "make it like theirs".
Reference 通史3: contact sheets P/qa/ref/ref-01..07.jpg (one frame every 6 s) and big frames P/qa/ref/big1.jpg. LOOK at them first.
Our frames for comparison: P/qa/ours_big.jpg. Target example (our kit, done right): P/qa/reftest.jpg, source P/scenes/src/zz-reftest.js.

**Keep:** every doll scene (K.doll), every w-* combat scene, maps, real photos/film. The user likes the dolls.
**Redraw:** every board (bd-*) and every non-doll diagram scene in your range, in the reference grammar below.

## The reference grammar (what every explaining frame looks like)
- An annotated page of a history book, calm: cream paper, ink, navy as the second colour, almost no red.
- **Anchor = a real thing.** Almost every frame has a real print or a document scan as an `exhibit` (kept at its own aspect, never cropped into a box, thin light mat, bold caption under it + a grey source line: "Photo (1969) · NASA", "Memo, 20 April 1961 · JFK Library"). Put it left or right, about 35–45 % of the width.
- **Notes, not boxes:** beside the exhibit, a `note`: a big serif year or number, then one or two short serif lines. A handful of words. No bordered text boxes, no dark tag chains, no strike-through boxes, no balance scales, no icons, no arrows between boxes except a single simple one where a flow is the point.
- **Line-ups of real hardware:** `craft` silhouettes (rockets, missiles, satellites, ships, tanks, planes) with name + "country · year · spec" under each, colour = side (ink American, navy Soviet, grey "not yet / planned"), a `legend` line under them. Use real proportions (look them up). One outlined `frame` word (like their 「買」) may mark the key attribute.
- **Documents:** the scan big on one side (`exhibit` with `hl` = navy box around the key line, `hlAt` on the word), the quoted words in serif on the other side (`note`), source line under the scan.
- **Question frames:** `question` = one centred serif line on empty paper (use sparingly, about one per chapter).
- **Flat number frames:** a big number + one label; at most a couple of plain bars (`bar`).
- Items appear on their words (`at: @{S146 "word"}`), slowly; the frame changes every 4–8 s by adding or replacing one element, never a full-screen wall of boxes.
- Real exhibits are needed for most frames: search new media (tags `p-X2-name`, `v-X2-name`; never reuse another group's tag). Good PD sources: NASA, NARA, USAF, US Army, US Navy, JFK/LBJ/Nixon libraries via Commons, CIA/NRO declassified documents on Commons, Library of Congress. Kennedy's memo to LBJ (20 Apr 1961), the Gaither Report, NSC/NSAM papers, the Outer Space Treaty, NRO MOL/HEXAGON documents, NASA budget tables, period newspapers that are PD.
- Board API: the comment block above `board(` in P/scenes/src/_kit.js (new kinds: exhibit, note, craft, legend, frame, question). The old kinds box/tag/strike/link/ring/conclude should almost disappear (a single link or ring is fine when it carries the point).

## Files and checks (same rules as P/GROUPS.md)
- Edit only P/shots-X.txt, P/overlays-X.txt, P/picks-X.txt, P/sfx-notes-X.txt and your own scene sources (P/scenes/src/bd-X-*.js, P/scenes/src/X-*.js non-doll ones; you may create new bd-X-*.js). Never edit _kit.js, plan.py, shots.txt, overlays.txt, timeline.json, other groups' files.
- Scene media: put exhibit images in SCENE.images as '/projects/<job>/media/<file>'; downloaded picks land in media/ as p-X2-tag-K.jpg via the lead's scene_media step, so write file names exactly `p-X2-TAG-K.jpg` (TAG#K from your search). For stills before that exists, copy the preview from media/candidates/<tag>/ into P/qa/X/ and point a temporary still build at it, or use an existing media file.
- `PLAN_PART=X PY P/plan.py durations` (merges), then `cd P/scenes/src && PY build.py NAME`, then stills: `node scripts/jsscene.mjs P/scenes/NAME.js P/qa/X/NAME.jpg --still T` for a mid and a full frame of EVERY redrawn scene; LOOK at them next to P/qa/ref/big1.jpg. Do not render final clips.
- `PLAN_PART=X PY P/plan.py check` until no `!!` for your part.

Report: list of redrawn scenes, new picks (TAG#K, file, licence), how many old box-style boards remain and why, unresolved items. Work autonomously; never ask questions.
