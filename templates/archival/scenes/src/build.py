"""Build scenes/<name>.js = _kit.js + src/<name>.js, with duration set from durations.json (written by plan.py).
python build.py [name ...]"""
import json, re, sys
from pathlib import Path

SRC = Path(__file__).parent
OUT = SRC.parent
kit = (SRC / '_kit.js').read_text(encoding='utf-8')
dur = json.loads((SRC / 'durations.json').read_text(encoding='utf-8')) if (SRC / 'durations.json').exists() else {}
names = sys.argv[1:] or [p.stem for p in SRC.glob('*.js') if not p.stem.startswith('_')]
for n in names:
    body = (SRC / f'{n}.js').read_text(encoding='utf-8')
    if n in dur:
        body = re.sub(r'duration:\s*[\d.]+', f'duration: {dur[n]:.3f}', body, count=1)
    (OUT / f'{n}.js').write_text(kit + '\n' + body, encoding='utf-8')
print(f'built {len(names)} scenes')
