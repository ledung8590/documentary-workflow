# Combat scene examples (space-race film, 2026-11-14)

Moving drawn combat scenes for narrated battles and attacks that have no usable real film ("phim còn tĩnh"):
V-2 on London, Bay of Pigs landing, Pickett's Charge, Soviet tanks in Prague, Vietnam air assault, Tet night fighting,
Pearl Harbor dive bombers, Ostfriesland sinking, Midway dive bombers, Lee's army, U-boat torpedo, Desert Storm left hook.

- Helpers: `scenes/src/_w.js` (object `wK`: tanks, planes, biplanes, Huey, battleship, carrier, cargo ship, U-boat, sea,
  blasts, splashes, fire, smoke columns, tracers, bombs, field guns, flags, firing dolls, houses), copied into every film.
- Each scene lists its shots/blasts in `SCENE.events = [[t, kind, note], ...]` and draws them from that list; the matching
  `scenes/events-NAME.txt` (first line `# REAL scene seconds`) gives gen_sound.py the same times, so picture and sound match.
- Copy a file to `scenes/src/w-NAME.js` and `events-w-NAME.txt` to `scenes/`, then change place, sides, costumes
  (doll sides `union`, `confed`, `us`, `sov`, `wehr`, `iraq`, …) and the events to fit the sentence.
