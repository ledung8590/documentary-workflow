"""Generate a reusable music mood bed with the ElevenLabs Music API into assets/music/<mood>/ (docs/MUSIC.md).

  PY scripts/music_elevenlabs.py tension --seconds 90 --prompt "..."          dry run: plan + live balance
  PY scripts/music_elevenlabs.py tension --seconds 90 --prompt "..." --run    generate, measure the real credit cost

Licence: Starter plan commercial licence covers Eleven Music in monetized YouTube videos (confirmed by ElevenLabs to the
user, 2026-10-30). Each file is logged in assets/music/LICENSES.md with prompt, length, plan and measured credits.
Existing files are never regenerated.
"""
import argparse, datetime, json, sys, urllib.error, urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import ROOT, elevenlabs_key
from elevenlabs import subscription

OUT = ROOT / 'assets' / 'music'


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('mood'); ap.add_argument('--seconds', type=float, default=90); ap.add_argument('--prompt', required=True)
    ap.add_argument('--run', action='store_true')
    a = ap.parse_args()
    folder = OUT / a.mood; folder.mkdir(parents=True, exist_ok=True)
    n = len(list(folder.glob('el_*.mp3'))) + 1
    path = folder / f'el_{n:02d}.mp3'
    before = subscription()
    left = before['limit'] - before['used'] if before and before.get('limit') else None
    print(f'plan: {path.relative_to(ROOT)}  {a.seconds:.0f} s  "{a.prompt[:90]}"')
    print(f'balance: {left} credits left' if left is not None else 'balance: unknown')
    if not a.run:
        print('dry run: add --run to generate'); return
    body = {'prompt': a.prompt, 'music_length_ms': int(a.seconds * 1000), 'model_id': 'music_v1', 'force_instrumental': True}
    req = urllib.request.Request('https://api.elevenlabs.io/v1/music?output_format=mp3_44100_192', method='POST',
                                 data=json.dumps(body).encode(),
                                 headers={'xi-api-key': elevenlabs_key(), 'Content-Type': 'application/json'})
    try:
        with urllib.request.urlopen(req, timeout=600) as r:
            path.write_bytes(r.read())
    except urllib.error.HTTPError as e:
        sys.exit(f'HTTP {e.code}: {e.read()[:500].decode("utf-8", "replace")}')
    after = subscription()
    cost = (after['used'] - before['used']) if after and before and 'used' in after and 'used' in before else None
    print(f'saved {path} ({path.stat().st_size // 1024} KB); measured cost: {cost} credits')
    lic = OUT / 'LICENSES.md'
    if not lic.exists():
        lic.write_text('# Music beds: sources and licences\n\n', encoding='utf-8')
    with open(lic, 'a', encoding='utf-8') as f:
        f.write(f'- `{a.mood}/{path.name}` — ElevenLabs Music (music_v1), {datetime.date.today()}, Starter plan; commercial use in '
                f'monetized YouTube confirmed by ElevenLabs 2026-10-30. {a.seconds:.0f} s, {cost} credits. Prompt: "{a.prompt}"\n')


if __name__ == '__main__':
    main()
