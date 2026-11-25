# House style (from a frame-by-frame study of the reference, 2026-10-30)

## Film look: one colour family per film (user 2026-11-14, overrides the colours and type below for archival films)
Reference: `通史3` (艦は買えた、海軍は買えなかった), a 22-minute film that stays in one palette the whole way: cream paper, navy, ink.
Our films mixed dark navy graphics, brown cards, satellite-green maps, sepia photos, bright reds and condensed caps, and
read as modern and patchy. Every archival film now has exactly one **look** (`brief.json` `"look"`, set by `doc.py plan`,
default `paper`; colours in `assets/looks.json`, read by `scenes/lib.js`, `maps/engine.html` and `scripts/render.py`):
- **`paper`** (default): cream paper ground, ink text, navy as the calm second colour, one muted red for marks
  (arrows, rules, dots), rare gold. **`dark`**: warm near-black ground, cream text, muted red, cool grey-blue. Pick
  `dark` only when the subject is better served by it (night war, submarines); never mix looks in one film.
- **Type:** one vintage serif for everything (Source Serif 4; Japanese Shippori Mincho, both OFL), book case, no caps,
  no glow, no drop shadows. Write overlay and card text in book case ("Der Mythos „Blitzkrieg“", not caps).
- **Real media:** standalone photos and film fill the frame (the reference does too), with a source label top-right.
  On analysis boards a photo is a small exhibit inside the argument (`K.board`); `pick:TAG#K+exhibit` hangs a
  standalone one as a mounted print on the paper (documents, small portraits). Use real media where it proves
  something, not as wallpaper: boards, maps and drawn characters carry most of the film.
- **Labels** (date tags, name plates, map labels, the source label top-right, scene tags): near-black box at ~80 %,
  a thin cream bar on its left edge, cream serif text (user correction 2026-11-14: not navy or paper boxes).
- **Maps:** flat Natural Earth sketch maps (land in the look's land colour, navy sea with a faint wave pattern, rivers,
  top-down camera, printed flat arrows, serif labels on navy boxes). No satellite imagery, terrain or bloom.
- **Graphics:** "poor on purpose", like a history book: thin rules, plain bars, small dots, boxes joined by thin lines,
  silhouettes. No glowing rings, gradient icons, neon or infographic dashboards.
- **Subtitles:** bold sans (`subsans`, Be Vietnam Pro SemiBold; Japanese M PLUS 1p). Over paper (JS scenes, boards, exhibits) they sit on a full-width cream band in dark text; over maps, photos and film they are plain white with a dark outline (user correction 2026-11-14: the band is not on every frame).
- `scripts/lookcheck.py JOB` (after `render_all.sh`) flags scenes and maps whose ground or accent colours leave the look.
- Films finished before 2026-11-14 have no `look` in their timeline and keep rendering in the old style below.

Reference: `Chiến Dịch Điện Biên Phủ 1954.mp4` (154.5 s, 24 fps, −14.1 LUFS). It was sampled at 1 fps for the whole film, then densely at transitions, at card reveals, and at full resolution for typography.

## Rhythm and structure
- **One idea per shot.** A new picture every 3–6 s; long holds of 6–8 s only on a strong photo, a map build or a quote.
- **Keep the picture changing through the narration.** Use full-screen cards for structural turns that need the whole frame. Place most dates, names and conclusions briefly over the image or action that gives them meaning.
- **Card types:**
  - Cold-open title on black: big off-white date, red letter-spaced subtitle.
  - Rhetorical question in big red caps on black ("VÌ SAO?").
  - Chapter card: small "CHƯƠNG 1", a huge red numeral, the title, a red rule, on a dark brown or warm-grey textured background.
  - Stat card on parchment: a heading with a rule, then big numbers revealed one by one, each with a red underline and a red/grey label.
    - Each item appears on the word that reads it out: set `"at"` (card seconds = word start − card start, from `voice/words.json`), with a soft `reveal` SFX on each item. Without it the items pop in 0.45 s apart, and a read-out list such as "Was it A… B… C" shows everything at once. This rule comes from the user review on 2026-10-31.
  - Calendar card with a hand-drawn red circle.
  - Typewriter quote card: dark brown background, monospace text typed with a block cursor, strikethrough of a rejected idea, then an amber highlight on the key phrase.
  - Closing card: title plus a red date line, then a dedication on black that fades out.
- **Maps** (satellite + terrain, darkened) are themselves sequences that build over 4–10 s:
  - zones fade in with white dashed outlines and blue fill;
  - labels pop in as black tags;
  - routes draw on;
  - red attack arrows grow;
  - trench arcs draw;
  - target pulses ring.
- **Transitions:**
  - Hard cuts between shots (no crossfades).
  - Dip-to-black or straight-to-card at section breaks.
  - Overlays animate in after the cut, never with it.

- **Cold open timing** (user 2026-11-24, replaces the 2026-10-30 rule "narration after the title card"): the film starts on its strongest real picture with the narration inside the first second (`docs/WORKFLOW.md` "The first 15 seconds"). The title comes after the hook, in a pause of the narration or as a title box over the picture. Never speak over a full-screen title.

## Picture treatment
- **Archival photos:** full-frame **cover crop** (never letterboxed, never blurred fill), black-and-white with a warm sepia cast, lifted blacks, strong but smooth vignette, film grain, a slow push-in or drift (≈ 4–8 % over the shot).
  - A portrait or square photo is shown as a **print on black**: fitted to ~85 % of the height, centred, no blur, optionally with the archive's own label strip.
- **Archival film:** desaturated with a teal/green cast, crushed corners, grain. Cut short (2–5 s) on the action.
- **Modern footage (2014+):** the same family. Desaturate 60–70 % with cool shadows, warm highlights, grain and vignette, so it sits with the photos. Avoid vertical phone video; if unavoidable, show it as a print on black.
- **Never** a visible hard dark border, frame lines or a blurred side band.

## Typography (all OFL, in `assets/fonts`)
- **Oswald Bold** (condensed): dates, names, card titles, numbers, map labels; uppercase for titles, mixed case allowed in date tags ("13/3/1954 · khoảng 17:00").
- **IBM Plex Mono:** kickers above names ("KHẨU ĐỘI TRƯỞNG"), typewriter quotes, small eyebrow labels.
- **Be Vietnam Pro SemiBold:** sub-lines and the credit line.
- **Military fonts** (added 2026-10-31, OFL), as `font` kinds in `render.font` and the studio's font menus:
  - `military` = Saira Condensed Bold. It is the burned-in subtitle style for military films: upper case, size 50, on a 62 % dark box.
  - Subtitles hide automatically while a callout, a lower third or a full card is on screen (`render.hide_under_text`). Text never doubles up.
  - `stencil` = Saira Stencil One, and `blackops` = Black Ops One. Use these two for titles only; a stencil is tiring to read for a whole film.
- **Colours:**
  - off-white #EDE7DC;
  - signal red #C8372D for rules, underlines, numerals and arrows;
  - amber #E0A030 for highlights;
  - parchment #D9CCAA;
  - dark brown #2B2119.

## Overlay grammar
- **Date tag:** top-left, a dark translucent box with a 6 px red bar, Oswald 44 px. It fades and slides in 0.3 s after the cut and stays for the sequence.
- **Lower third:**
  - a red bar that grows;
  - a mono kicker typed in;
  - the name in Oswald 84 px rising in;
  - a Be Vietnam sub-line.
- **Callout on footage:** a big Oswald line low-centre with a red underline drawn left to right ("HƠN 261.000 DÂN CÔNG").
- **Credit line:** bottom-right, Be Vietnam SemiBold 22 px, off-white 85 %, soft shadow. It reads "what it shows · source/author" and says "(minh hoạ)" when not the exact event.

## Sound
- Narration leads.
- One music bed per section, ducked under the voice; it swells in designed pauses and on cards.
- Sparse SFX: artillery on artillery shots, a typewriter clack on typed cards, a low hit on chapter cards.
  - Every card hit also gets an audible mid/high layer (`cardslam/el_01`, about -15 dB; at -4 it startles). The sub-bass hits (`impact`, `titlehit`, `chapterhit`, `reveal`) are almost silent on laptop speakers and earbuds.
- Archival film sound is used only when it is real field sound. **Clip audio is muted by default:** many uploads carry their own music, which is a copyright risk.

## Optional film grain (AutoVeo3 HyperFrames look)
- `timeline.json` `"fx": {"grain": true}` turns on the exact HyperFrames "Film grain" from AutoVeo3 (`core/whisk_hf_engine.py`, `_CSS_GRAIN`).
- How it is drawn:
  - a fractalNoise tile (baseFrequency 0.75, 4 octaves, desaturated, 200 px), rendered by Chromium (`scripts/grain_tile.mjs`);
  - layer opacity 0.09;
  - the noise jumps through 3 positions every 0.15 s.
- It sits on the picture, under the text overlays.
- This is the only grain allowed. The earlier synthetic per-pixel grain was rejected by the user.
