"""Add documentary/motion-graphics sound effects to assets/sfx/<type>/ with the ElevenLabs Sound Effects API.
The chibi workflow's library (history-video-workflow/assets/sfx) is reused for battlefield sounds; this adds what
title cards, typed text and maps need. Existing files are never regenerated.

  PY scripts/sfx_elevenlabs.py            dry run (plan + live balance)
  PY scripts/sfx_elevenlabs.py --run      generate missing files, log measured credits in assets/sfx/LICENSES.md
"""
import argparse, datetime, json, sys, urllib.error, urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import ROOT, elevenlabs_key
from elevenlabs import subscription

OUT = ROOT / 'assets' / 'sfx'
LIB = {  # type -> [(seconds, prompt)]
    'typewriter': [(4.0, 'Vintage mechanical typewriter typing fast, crisp key strikes, close, dry, no music'),
                   (2.0, 'Old typewriter typing a few slow deliberate keys, close, dry, no music'),
                   (10.0, 'Vintage manual typewriter typing continuously at a steady even pace, loud crisp mechanical key strikes, '
                          'close mic, dry, no bell, no carriage return, no music')],
    # card hits (the first set was too thin under narration; first used by nguoi-gac-dem)
    'titlehit': [(5.0, 'Massive cinematic movie trailer title hit, huge sub bass boom, metallic slam and deep dark braam, '
                       'long reverb tail, thriller, no melody'),
                 (4.0, 'Epic dark cinematic impact, heavy orchestral drum slam with distorted sub drop and long tail, no melody')],
    'chapterhit': [(3.0, 'Deep dark cinematic documentary transition hit, low boom with short metallic ring and reverb tail, no melody'),
                   (3.0, 'Heavy low taiko slam with sub boom, cinematic chapter card, dark, no melody')],
    'subdrop': [(3.0, 'Deep cinematic sub bass drop, low rumble falling in pitch, no melody')],
    'revswell': [(3.0, 'Reverse cymbal and reverse piano swell rising into a hit, dark cinematic suck-in, no melody')],
    'whooshdark': [(1.5, 'Fast deep cinematic whoosh pass-by, dark, airy, no music')],
    'typebell': [(1.5, 'Typewriter carriage return lever with end-of-line bell ding, close, dry')],
    'impact': [(3.0, 'Deep cinematic trailer impact hit with sub boom and long dark reverb tail, no music'),
               (2.5, 'Heavy cinematic braam hit, low brass and distorted sub, documentary title, no melody')],
    'riser': [(3.0, 'Dark cinematic riser building tension into a hit, reverse swell, no melody')],
    'reveal': [(1.2, 'Short low whoosh with soft metallic shimmer for a text reveal, cinematic, no music')],
    'mapping': [(1.5, 'Subtle digital UI sweep and soft beep for a map marker appearing, military briefing, no music')],
    # espionage / night-story foley (first used by nguoi-gac-dem)
    'knock': [(2.5, 'Three slow firm knocks on an old wooden door at night, close, dry, no music')],
    'jeep': [(5.0, 'Old 1960s military jeep approaching slowly on a dirt road at night and stopping with a soft brake squeal, engine idle, no music')],
    'brakes': [(3.5, 'Several old military trucks braking hard and stopping on a dirt road, doors slamming, no music')],
    'motorbike': [(3.0, 'Old motorbike pulling up fast and braking on gravel, engine cut, no music')],
    'clang': [(1.5, 'Iron rod pushed through liquid striking the metal bottom of an oil drum, single dull clang, close, no music')],
    'knockfloor': [(1.5, 'Bayonet tip tapping a hard wooden floor plank, one dull hollow knock, close, dry, no music')],
    'glass': [(1.5, 'Small glass bottle dropped and shattering on a hard floor, close, no music')],
    'rooster': [(4.0, 'Distant rooster crowing at dawn over a quiet rural village, soft, no music')],
    'match': [(3.0, 'Match struck, a small slip of paper catches fire and burns briefly, close, quiet, no music')],
    'night': [(10.0, 'Quiet tropical night ambience, crickets and distant insects, faint far-off dog bark, no music')],
    'lock': [(2.0, 'Old padlock mechanism clicking open as a key turns, metallic, close, dry, no music')],
    'heartbeat': [(4.0, 'Slow deep heartbeat thumps, low and muffled, cinematic tension, no music')],
    'clock': [(6.0, 'Old wall clock ticking slowly in a silent room, close, no music')],
}


def main():
    ap = argparse.ArgumentParser(); ap.add_argument('--run', action='store_true'); a = ap.parse_args()
    todo = [(t, i, s, p) for t, items in LIB.items() for i, (s, p) in enumerate(items, 1)
            if not (OUT / t / f'el_{i:02d}.mp3').exists()]
    sub = subscription(); left = sub['limit'] - sub['used'] if sub and sub.get('limit') else None
    print(f'{len(todo)} to generate, {sum(s for _, _, s, _ in todo):.1f} s (~{sum(s for _, _, s, _ in todo) * 10:.0f} credits '
          f'at the measured ~10 credits/s); balance {left}')
    if not a.run:
        return
    lic = OUT / 'LICENSES.md'
    for t, i, s, p in todo:
        before = subscription()
        req = urllib.request.Request('https://api.elevenlabs.io/v1/sound-generation?output_format=mp3_44100_128', method='POST',
                                     data=json.dumps({'text': p, 'duration_seconds': s, 'prompt_influence': 0.5}).encode(),
                                     headers={'xi-api-key': elevenlabs_key(), 'Content-Type': 'application/json'})
        try:
            with urllib.request.urlopen(req, timeout=300) as r:
                data = r.read()
        except urllib.error.HTTPError as e:
            sys.exit(f'{t}: HTTP {e.code}: {e.read()[:300].decode("utf-8", "replace")}')
        f = OUT / t / f'el_{i:02d}.mp3'; f.parent.mkdir(parents=True, exist_ok=True); f.write_bytes(data)
        after = subscription(); cost = after['used'] - before['used'] if after and before and 'used' in after and 'used' in before else None
        with open(lic, 'a', encoding='utf-8') as fh:
            fh.write(f'- `{t}/{f.name}` — ElevenLabs Sound Effects, {datetime.date.today()}, Starter plan commercial licence '
                     f'(confirmed 2026-10-30). {s} s, {cost} credits. Prompt: "{p}"\n')
        print(f'{t}/{f.name} ok ({cost} credits)')


if __name__ == '__main__':
    main()
