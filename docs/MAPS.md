# Animated map scenes

**Film looks (2026-11-14):** with `brief.json` `"look"` (`paper`/`dark`, default `paper`), `mapscene.mjs` passes the look and
`maps/engine.html` draws a flat sketch map instead of satellite terrain: Natural Earth land/lakes/rivers (`assets/geo`,
public domain; 1:50m below zoom 4, 1:10m above) in the look's land colour on its sea with a faint wave pattern, top-down
(pitch and bearing forced to 0), printed flat arrows, no glow or bloom, serif labels on navy (paper) boxes. Colours in a
spec are pulled into the look by hue (reds → accent2, blues → accent, ambers → highlight, greys → fg). A spec with
`"base": "satellite"` keeps the old 3D satellite map unchanged (look films use both, like the reference: atlas maps for
history, satellite for real distances and terrain; plan.py gives it the satellite credit). Credit of flat maps:
"Karte: Natural Earth (gemeinfrei) · Positionen, Pfeile: schematisch" (plan.py sets it per language). The satellite
section below applies only to films without a look.


`node scripts/mapscene.mjs projects/<id>/maps/<scene>.json projects/<id>/media/map-<scene>.mp4 [--fps 24]`

`maps/engine.html` runs MapLibre GL in headless Chromium. Each frame waits for its tiles, so renders are deterministic (an 8 s scene takes about 20 s on the GPU).

- **Base map:** Sentinel-2 cloudless **2016** by EOX (`s2cloudless_3857`, CC BY 4.0). Later EOX years are NC and must not be used. It is draped over AWS Terrain Tiles (terrarium) with hillshade, darkened and desaturated.
- **Credit line:** "Địa hình: AWS Terrain Tiles · Ảnh vệ tinh: Sentinel-2 cloudless 2016 (EOX, CC BY 4.0) · Vị trí, mũi tên: minh hoạ".

## Scene JSON
- `duration` (s).
- `camera`: keyframes `{t, center:[lng,lat], zoom, pitch, bearing}`, eased between.
  - Use zoom 10.5–11.5 for a 40–80 km theatre and pitch 45–60 for the tilted look.
  - Keep every label inside the frame for the whole move.
- `saturation`, `brightness`, `exaggeration`: optional base-map tweaks.
- `layers`: drawn in order; times are in scene seconds; `until` fades a layer out.

| kind | what it does | key fields |
|---|---|---|
| `zone` | dashed outline drawn on, then fill fades in | `coords`, `draw`, `fill`, `color` |
| `arrow` | glowing tapered arrow that grows, then pulses | `path` (2 pts → arc, more → polyline), `bend`, `width`, `color` |
| `route` | glowing dashed line drawn on (marching dashes) | `path`, `draw`, `color` |
| `label` | black tag with leader line, pops in | `at`, `text`, `sub`, `dy`, `accent` |
| `pulse` | glow and expanding rings on a point | `at`, `color` |
| `column` | illustrated units travelling a path: walking soldiers or driving tanks | `unit` (`soldier`/`tank`), `n`, `size`, `spread`, `gap`, `travel`, `reach`, `color` |
| `battery` | gun line firing: muzzle blasts, glowing shells on arcs, impacts with smoke at the target | `at`, `target`, `n`, `every`, `fly`, `arc`, `size`, `boom`, `spread` |
| `impacts` | shelling: bursts with flash, ring and smoke scattered over an area | `at`, `every`, `spread`, `size` |

## 3D, not a flat overlay (user review 2026-10-30: "nhìn y 2D")
- `zone`, `arrow` and `route` are real map layers, so they get true perspective:
  - zones are draped fills plus translucent extruded blocks (`height`, default 380 m);
  - arrows are extruded tapered solids standing on the terrain (`height` 520 m, `lift` 120 m) with a pulsing glow draped under them;
  - routes are draped glowing dashed lines.
- Units, guns and explosions are anchored to the ground and scaled by perspective, so near ones are bigger.
- The sky, horizon fog and haze come from `setSky`.
- Cameras orbit 40–55° of bearing at a pitch of 60–65.
- The clip gets `"bloom": true` in the timeline (a glow on bright parts, added by the ffmpeg post-process in render.py).

## Ocean and continental scenes
- Terrarium tiles include bathymetry, so the seafloor relief shows through the sea under hillshade.
- Use `exaggeration` 1.0–1.2, `brightness` ~0.75 and `saturation` ~-0.35, at zoom 3.5–5.
- At this scale the extruded arrows can be clipped by land relief. Check frames, and use wider arrows or a red `route` if that happens.
- World-scale maps (zoom under 3): set `"shade": 0, "exaggeration": 0.2` in the spec. Bathymetry hillshade reads as white marble swirls over the oceans at that scale (film 92).
- English credit: "Terrain: AWS Terrain Tiles · Imagery: Sentinel-2 cloudless 2016 (EOX, CC BY 4.0) · Positions illustrative".

## Colours
- Attacker red `#e0402f` / `#b8433a`.
- Defender blue `#5f8fe0` / `#6f94d8`.
- Neutral zones: white dash with blue fill.

## Scene grammar
- Build each beat on the narrator's word, never all at once.
- Something should be moving in every second of the scene: camera, a drawing line, units, fire.
- Mark approximate geography as "minh hoạ".
