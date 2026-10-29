# House style (from a frame-by-frame study of the reference, 2026-10-30)

Reference: `Chiến Dịch Điện Biên Phủ 1954.mp4` (154.5 s, 24 fps, −14.1 LUFS). It was sampled at 1 fps for the whole film, then densely at transitions, at card reveals, and at full resolution for typography.

## Rhythm and structure
- **One idea per shot.** A new picture every 3–6 s; long holds of 6–8 s only on a strong photo, a map build or a quote.
- **Designed full-screen cards** alternate with footage about every 15–20 s, so the film never runs more than ~25 s of footage without a card.
- **Card types:**
  - Cold-open title on black: big off-white date, red letter-spaced subtitle.
  - Rhetorical question in big red caps on black ("VÌ SAO?").
  - Chapter card: small "CHƯƠNG 1", a huge red numeral, the title, a red rule, on a dark brown or warm-grey textured background.
  - Stat card on parchment: a heading with a rule, then big numbers revealed one by one, each with a red underline and a red/grey label.
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

- **Cold open timing** (user review, 2026-10-30): the narration starts only after the title card has gone. Set the voice `lead_in` to at least the title card length plus 0.3 s, and anchor the first footage to the end of the title, not to the first word. Never speak over a full-screen title.

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
- Archival film sound is used only when it is real field sound. **Clip audio is muted by default:** many uploads carry their own music, which is a copyright risk.
