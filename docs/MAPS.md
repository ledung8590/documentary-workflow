# Animated 3D map scenes

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

## Colours
- Attacker red `#e0402f` / `#b8433a`.
- Defender blue `#5f8fe0` / `#6f94d8`.
- Neutral zones: white dash with blue fill.

## Scene grammar
- Build each beat on the narrator's word, never all at once.
- Something should be moving in every second of the scene: camera, a drawing line, units, fire.
- Mark approximate geography as "minh hoạ".
