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
                   (2.0, 'Old typewriter typing a few slow deliberate keys, close, dry, no music')],
    'typebell': [(1.5, 'Typewriter carriage return lever with end-of-line bell ding, close, dry')],
    'impact': [(3.0, 'Deep cinematic trailer impact hit with sub boom and long dark reverb tail, no music'),
               (2.5, 'Heavy cinematic braam hit, low brass and distorted sub, documentary title, no melody')],
    'riser': [(3.0, 'Dark cinematic riser building tension into a hit, reverse swell, no melody')],
    'reveal': [(1.2, 'Short low whoosh with soft metallic shimmer for a text reveal, cinematic, no music')],
    'mapping': [(1.5, 'Subtle digital UI sweep and soft beep for a map marker appearing, military briefing, no music')],
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
        after = subscription(); cost = after['used'] - before['used'] if after and before else None
        with open(lic, 'a', encoding='utf-8') as fh:
            fh.write(f'- `{t}/{f.name}` — ElevenLabs Sound Effects, {datetime.date.today()}, Starter plan commercial licence '
                     f'(confirmed 2026-10-30). {s} s, {cost} credits. Prompt: "{p}"\n')
        print(f'{t}/{f.name} ok ({cost} credits)')


if __name__ == '__main__':
    main()
