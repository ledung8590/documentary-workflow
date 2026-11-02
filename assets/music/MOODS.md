# Music beds: which to use where

User rule (2026-11-01; film 74, and again in another session): a pulsing or drumming bed under long narration sounds like
"lộc cộc" (knocking) and does not fit. The default bed under narration has **no drums, no percussion, no pulse**.

| bed | character (from its prompt) | use |
|---|---|---|
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
