# Music beds: which to use where

User rule (2026-11-01; film 74, and again in another session): a pulsing or drumming bed under long narration sounds like
"lộc cộc" (knocking) and does not fit. The default bed under narration has **no drums, no percussion, no pulse**.

| bed | character (from its prompt) | use |
|---|---|---|
| `milsuspense` | Cold War military thriller: deep low brass, tremolo strings, menacing horn motif, building to strong peaks, no drums (2026-11-03; el_01 stalking under ice, el_02 arms-race ostinato (use the first 138 s), el_03 surfacing/launch build from quiet, el_04 hunter dread) | **military films: the default bed for threat, weapons, hunting, launches** |
| `milintro` | mysterious, quietly heroic: low strings, distant horns rising, sense of scale and secrecy, no drums (2026-11-03) | **military group 1: opening, introducing the machine** |
| `miltech` | steady bowed string ostinato / soft synth arpeggio / cold metallic pads, analytical, moderate tempo, no drums (2026-11-03; `el_02`/`el_03.dips.off`: 15-35 s silences mid-file, rejected; el_05 ends at 135 s) | **military group 3: design, missiles, reactors, radar, sonar, logistics** |
| `milverdict` | lightly heroic and reflective: warm strings with a solemn brass chorale, dignified close, no drums (2026-11-03) | **military group 6: verdict, strategic lessons** |
| `europe1870` | sustained low strings, soft horns, legato, no percussion | **narration: analysis, history, politics** |
| `strategy` | legato pulsing low strings, soft piano, no drums | **narration: armies, weapons, numbers** |
| `darkdrone` | low string and brass drones, ominous, no percussion | **narration: tension, threat, intrigue** |
| `warstrings` | driving legato strings and brass, urgent, no drums | **narration: battles and attacks** |
| `lament` | solo violin and cello, sorrowful, no percussion | **narration: losses, the fallen, tragedy** |
| `somber` | solo cello over piano, slow elegy | **narration: defeat, loss** |
| `resolve` | piano growing into warm strings and horn | **narration: summary, ending** |
| `nostalgia` | warm piano, bamboo flute (Southeast Asian colour) | narration, Vietnamese/Asian films only |
| `spyintrigue` | low cello / bass clarinet creeping line, sparse high piano, no drums (`el_01.pulse.off`: pizzicato pulse, rejected) | **espionage stories: tension, threat** |
| `spynoir` | muted trumpet or clarinet over soft piano, slow upright bass, 1960s noir, no drums | **espionage stories: narration** |
| `spypiano` | solo felt piano theme in A minor (with soft strings in el_02) | **espionage stories: reflection, memory, history passages** |
| `spychase` | tremolo strings, rising low brass swells, no drums (`el_03.drums.off`: percussive 0.18, rejected) | **espionage stories: escape, urgency** |
| `spysuspense` | tremolo strings, low bowed ostinato, dissonant swells, heartbeat drone, no drum kit (2026-11-03; `el_01`/`el_04.dips.off`: stop-start 20 dB dips, rejected; originals of levelled beds in `_raw/`) | **espionage stories: the default bed: suspense, surveillance, interrogation, traps** |
| `imperial` | brass chorale with timpani rolls | short: title, ceremony (≤ 90 s) |
| `noir` | string drone, pizzicato, ticking and brushed snare | short only (≤ 90 s); prefer `darkdrone` |
| `combat`, `battle`, `tension`, `naval`, `coldwar`, `mystery`, `deepocean` | taiko, war drums, snare ostinato, ticking, heartbeat or pings | **only a short climax (≤ 60–90 s) of a battle, never as a long bed**; several carry another film's colour (tropical swamp, Southeast Asian river, submarine) |
| `march`, `suspense` | snare march; sub-kick pulse | **retired: do not use** |

Espionage stories are suspense first. The user said of story 89 Ngọn Hải Đăng (2026-11-03): "nhạc ko kịch tính hồi hộp tý nào… ko khác gì nhạc ru ngủ". That plan was 60 % spynoir/spypiano/nostalgia. Use `spysuspense`/`spyintrigue`/`spychase` for about 70 % of the film, and calm beds only for family, grief and the ending.

Drum check without listening: run a harmonic/percussive split and compare the percussive energy share.
- Rejected beds: pulse bed 0.054 with 2 hits/s; drum beds 0.15–0.24.
- Accepted beds: about 0.01–0.04 with under 0.1 hits/s.

Rules:
- A bed plays at most about 2–3 minutes, then the music changes at a chapter or emotion turn. A 120 s file is never looped for minutes.
- Follow the voice's emotion: battle → `warstrings`; losses → `lament` or `somber`; analysis → `europe1870` or `strategy`.
- New beds: write "no drums, no percussion, no pulse" into the prompt. Then measure that the file has no regular beat before using it.

- Espionage stories set `story.moods` / `story.alt` / `drum_accent: false` in brief.json to use the spy beds (story 89, 2026-11-02: darkdrone/strategy sounded like "ú ú máy bay", not espionage). `doc.py story` changes the bed where the voice's emotion turns (runs ≥ 35 s) and lifts tense/urgent beds 1.5–2.5 dB, lowers reflective ones 1–1.5 dB.

Military films are tension first (film 89 Typhoon vs Ohio, 2026-11-03): the user said the first plan (europe1870/strategy/darkdrone, about 70 %) was "hiền", too gentle for a military theme, like the espionage-story lullaby case. Use `milsuspense`, `warstrings`, `spysuspense`, `spyintrigue` and `spychase` for about 70 % of a military film; keep `europe1870`/`strategy`/`darkdrone` for short analysis or crew-life passages, `lament`/`somber` for losses, `resolve` for the verdict. Tension beds sit about 8.5 dB under the voice, calm ones about 9.5 dB.

## Military history films: six music groups (user guide, 2026-11-03)
The user's guide `Huong_dan_nhac_nen_phan_tich_lich_su_quan_su.md` (workspace root) is the standard for archival military films. Overall colour: dark, mysterious, serious military documentary underscore with moderate tension; it serves the narration and never competes with it. No vocals, slow to moderate tempo, deep low end, few prominent melodies, no loud drums, no sudden climaxes.

Give every chapter one group by its content and emotion, then pick beds from that group:

| group | style | use for | beds |
|---|---|---|---|
| 1 | mysterious, lightly heroic | opening, introducing the machine, curiosity | `milintro`, `milsuspense` el_03 |
| 2 | tense, low and dark | historical context, strategy, rivalry, geography | `milsuspense` el_01/el_02/el_04, `darkdrone`, `spyintrigue` |
| 3 | military technology | design, hulls, missiles, reactors, noise, radar, logistics | `miltech`, `strategy` |
| 4 | suspense, danger | pursuit, confrontation, combat, launches, under-ice drama | `warstrings`, `spysuspense`, `spychase`, `milsuspense` el_03 |
| 5 | quiet, reflective | cost, failure, losses, consequences, decline | `somber`, `lament`, `europe1870` |
| 6 | lightly heroic, deep | conclusion, strategic lessons | `milverdict`, `resolve` |

Rules:
- Change music where the content turns, not every few minutes by the clock.
- A group may run 5–12 minutes across a chapter, but a single file is never looped. Rotate 2–3 different beds of the same group inside it (each file plays at most one pass, about 2–3 min).
- Crossfade 3–5 s between beds (the 3 s overlap in sound.txt).
- Keep the music clearly under the voice: tension beds about 8.5 dB, calm ones about 9.5 dB, measured per bed with `render.premix`.
- Key lines (rule 6): the central question, a rhetorical question, a punchline, a big number, the verdict sentence and the closing question get a music dip. Write `S009 .. S009$ | dip | -10` in sound.txt; plan.py attaches it to the music clip, and render dips the bed after its levelling with 0.6 s ramps. Use -6 to -10 dB for a dip, and -40 for a short pause at a dramatic beat (film 89: S214 "But now, it is completely exposed."). Use about 5–8 per film so they keep their effect. Measure each dip on the music stem: it should be at least 5 dB below the bed around it; where the bed is already quiet, deepen it.
- Only beds with YouTube-safe rights (ElevenLabs Starter commercial licence, logged in LICENSES.md).
- Library target: 12–18 beds, 2–3 per group. Workflow per film: read the script → list chapters → assign a group per chapter → pick beds → balance against the voice → check the transitions → export.
