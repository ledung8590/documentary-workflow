# Music (stage 7: shared library + placement built; beat grid planned)

## Source: ElevenLabs Music (default, official API)
- Same `ELEVENLABS_API_KEY` as SFX.
- **Licence:** on 2026-10-30 ElevenLabs confirmed to the user that the **Starter plan's commercial licence covers Eleven Music in monetized YouTube videos**, exactly as for Sound Effects. Each generated file gets a row in `assets/music/LICENSES.md`: file, prompt, duration, plan at generation time (Starter), date, "ElevenLabs Music, commercial licence confirmed 2026-10-30".
- **Budget:**
  - The Starter plan has 40,000 credits per period.
  - The 72-file SFX library cost 6,034 credits, about 10 credits per second of audio.
  - On 2026-10-30 the balance was 33,966 left, resetting 2026-11-30.
  - Never trust these numbers: the dry run reads the **live balance** from `GET /v1/user/subscription` (remaining = `character_limit - character_count`; `elevenlabs.subscription()` in this repo, `balance()` in `history-video-workflow/scripts/sfx_elevenlabs.py`).
  - Music is never generated per scene.
  - Build a **small shared library of reusable mood beds** in `assets/music/<mood>/`, reused by every film. It is generated once, like `assets/sfx`, and existing files are never regenerated.
  - Each bed is about 60–120 s, instrumental, with a steady tempo so it can be cut and looped on bars, plus a separate ending or sting where useful.
  - Starting set (one or two variants each): `tension`, `somber`, `battle`, `resolve`, `mystery`, `march`, `elegy`.
- **Always dry-run first.** Before generating, print the planned tracks (mood, prompt, duration) and the estimated credits, then ask the user in chat; only then pass `--run`.
  - Estimate from **measured** costs, not documented rates. The music rate is not measured yet. With the user's OK, generate one short bed, record the balance before and after, and store credits per second in the script. Only then estimate a batch.
  - If the estimate exceeds the remaining monthly credits, generate only the moods the current film needs, or wait for the next month.

## Optional manual path: Suno
- Suno has no public API (October 2026). Use it only manually, on **Suno Pro/Premier at suno.com**. Songs made while subscribed carry commercial rights; Free-plan songs do not.
- The agent writes prompts (instrumental, BPM, instruments, mood, "no vocals") to `projects/<id>/music/PROMPTS.md`. The user generates, downloads into `projects/<id>/music/`, and notes the song URL in `LICENSES.md`.
- **Unofficial Suno resellers (sunoapi.org and similar) are not used.** They break Suno's terms and the output rights are unclear. A key from them is not integrated.

## Fitting music to the film
1. **Plan per chapter** from the narration (STORY.md + pacing chapters): mood, intensity curve, where the music rests. Several chapters can reuse the same bed.
2. **Beat grid:** `librosa` beat/downbeat detection per file, cached as `<file>.beats.json`.
3. **Cuts on the beat:**
   - A music clip's start is anchored to the chapter's first unit (minus a pre-roll).
   - Entries, swells and cuts snap to the nearest downbeat within ±0.25 s of the story beat.
   - Changes between beds are 1–2 s crossfades on a bar line.
   - Loops repeat whole bars.
4. **Voice-led mix:**
   - Sidechain ducking under speech (about −10 dB while the voice is active); music rises in the designed long pauses and title cards.
   - Music never covers words.
   - Final mix is −14 LUFS integrated, true peak ≤ −1 dBTP (two-pass loudnorm on the full mix).
5. Silence or a drone only for the heaviest moments; a rest is a choice, not a gap.
