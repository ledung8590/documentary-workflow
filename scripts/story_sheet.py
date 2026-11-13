"""Contact sheets of story images NNN.png (docs/STORY_MODE.md image checks, docs/ZIMAGE.md).

    PY scripts/story_sheet.py "input/<story>" JOB out.jpg 1-10          first ten, beat text under each
    PY scripts/story_sheet.py "input/<story>" JOB out.jpg 100-370:9     every 9th image from 100 to 370
    PY scripts/story_sheet.py "input/<story>" JOB out.jpg 7,30,61       chosen images
    PY scripts/story_sheet.py "input/<story>" JOB outdir --qa [SPEC]    defect check: 9 big numbered images per sheet,
                                                                        all images (or SPEC) -> outdir/sheet_NNN.jpg
Beat text comes from projects/JOB/beats.json ({"k", "text"}) when it exists.
"""
import json, sys, textwrap
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
args = [x for x in sys.argv[1:] if x != '--qa']; qa = '--qa' in sys.argv
story, job, out = Path(args[0]), args[1], Path(args[2]); spec = args[3] if len(args) > 3 else None


def numbers(spec):
    if spec is None:
        return sorted(int(p.stem) for p in story.glob('[0-9][0-9][0-9].png'))
    if ',' in spec or '-' not in spec:
        return [int(x) for x in spec.split(',')]
    rng, _, step = spec.partition(':'); a, b = map(int, rng.split('-'))
    return list(range(a, b + 1, int(step or 1)))


def font(name, size):
    try:
        return ImageFont.truetype(name, size)
    except OSError:
        return ImageFont.load_default()


ns = [n for n in numbers(spec) if (story / f'{n:03}.png').exists()]
if qa:   # 3x3 at 560x315: large enough to see ears, fingers and limbs (defect check, user rule 2026-11-12)
    out.mkdir(parents=True, exist_ok=True); W, H, f = 560, 315, font('arialbd.ttf', 28)
    for s in range(0, len(ns), 9):
        part = ns[s:s + 9]; sh = Image.new('RGB', (W * 3, H * 3), 'black'); d = ImageDraw.Draw(sh)
        for i, n in enumerate(part):
            x, y = (i % 3) * W, (i // 3) * H
            sh.paste(Image.open(story / f'{n:03}.png').convert('RGB').resize((W, H)), (x, y))
            d.rectangle((x, y, x + 70, y + 36), fill='yellow'); d.text((x + 4, y + 2), str(n), fill='black', font=f)
        sh.save(out / f'sheet_{part[0]:03}.jpg', quality=82)
    print(f'{len(ns)} images -> {(len(ns) + 8) // 9} sheets in {out}')
    sys.exit()
bf = ROOT / 'projects' / job / 'beats.json'
beats = {b['k']: b['text'] for b in json.loads(bf.read_text(encoding='utf-8'))} if bf.exists() else {}
W, H, T, cols = 320, 180, 56, 5
rows = (len(ns) + cols - 1) // cols
sheet = Image.new('RGB', (W * cols, (H + T) * rows), 'white'); d = ImageDraw.Draw(sheet); f = font('arial.ttf', 11)
for i, n in enumerate(ns):
    im = Image.open(story / f'{n:03}.png').convert('RGB'); im.thumbnail((W, H))
    x, y = (i % cols) * W, (i // cols) * (H + T); sheet.paste(im, (x, y))
    d.multiline_text((x + 3, y + H + 2), '\n'.join(textwrap.wrap(f'{n}: ' + beats.get(n, ''), 55)[:4]), fill='black', font=f)
sheet.save(out, quality=78); print(len(ns), 'images ->', out)
