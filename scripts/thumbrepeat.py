"""Thumbnail template check: a new thumbnail must not look like the channel's last ones (user 2026-11-24: "YouTube giờ quét
gắt về vụ template"; its repetitive-content rule judges the channel as a whole, and four archival thumbnails in a row were
the same layout: portrait strip left, small white line, huge red word bottom right).

  PY scripts/thumbrepeat.py NEW.jpg              against the last archival thumbnails (evidence/*/video/*.jpg)
  PY scripts/thumbrepeat.py NEW.jpg --story      against stories/published/thumbs/*.jpg
  PY scripts/thumbrepeat.py NEW.jpg --sheet OUT.jpg   also write NEW next to the last ones at small size, to look at

What is compared is the LAYOUT, not the subject: on a 32x18 grid, where the red emphasis sits, where the bright lettering
sits, where the dark and the light masses are. `!!` (exit 1) when the new one matches any of the last LAST thumbnails more
than HARD, or when the red emphasis sits in the same place as on two of them; `!` above SOFT. The numbers were set on the
30 archival thumbnails of 2026-11: thumbnails of one layout family score 0.24-0.46 against each other (the four "portrait
strip + red word" ones, the two "serif title on a bottom panel" ones 0.39), unrelated layouts 0.02-0.20.
"""
import sys
import os
from pathlib import Path

import numpy as np
from PIL import Image, ImageFilter

ROOT = Path(__file__).resolve().parents[1]
GW, GH = 32, 18
LONG = chr(92) * 2 + '?' + chr(92)  # Windows long-path prefix
LAST, HARD, SOFT, RED_SAME = 5, 0.33, 0.24, 0.42


def maps(path):
    """Four layout maps on the grid: red emphasis, bright lettering, dark mass, tone."""
    im = Image.open(path).convert('RGB').resize((GW * 10, GH * 10), Image.BILINEAR)
    a = np.asarray(im, np.float32); r, g, b = a[..., 0], a[..., 1], a[..., 2]
    lum = 0.299 * r + 0.587 * g + 0.114 * b
    edges = np.asarray(im.convert('L').filter(ImageFilter.FIND_EDGES), np.float32)
    cell = lambda m: m.reshape(GH, 10, GW, 10).mean(axis=(1, 3))  # noqa: E731
    red = cell(((r > 150) & (g < 95) & (b < 95)).astype(np.float32))
    text = cell(((lum > 205) & (edges > 60)).astype(np.float32))   # bright pixels on hard edges: lettering
    dark = cell((lum < 38).astype(np.float32))
    return red, text, dark, cell(lum) / 255.0


def corr(a, b):
    a, b = a - a.mean(), b - b.mean()
    d = float(np.sqrt((a * a).sum() * (b * b).sum()))
    return float((a * b).sum() / d) if d > 1e-6 else 0.0


def overlap(a, b):
    """Shared share of two masses (0..1), after a one-cell blur so a small shift still counts."""
    blur = lambda m: np.asarray(Image.fromarray((np.clip(m, 0, 1) * 255).astype(np.uint8)).filter(ImageFilter.BoxBlur(1)), np.float32)  # noqa: E731
    a, b = blur(a), blur(b)
    return float(np.minimum(a, b).sum() / max(1e-6, np.maximum(a, b).sum())) if max(a.sum(), b.sum()) > 40 else 0.0


def similarity(x, y):
    """(score 0..1, red-position overlap 0..1) of two map sets."""
    red, text = overlap(x[0], y[0]), overlap(x[1], y[1])
    dark, tone = max(0.0, corr(x[2], y[2])), max(0.0, corr(x[3], y[3]))
    return 0.30 * red + 0.30 * text + 0.20 * dark + 0.20 * tone, red


def previous(story=False, skip=None):
    """Earlier thumbnails, newest first."""
    pat = 'stories/published/thumbs/*.jpg' if story else 'evidence/*/video/*.jpg'
    fs = [f for f in ROOT.glob(pat) if f.name.lower() != 'thumbnail.jpg' or len(list(f.parent.glob('*.jpg'))) == 1]  # the renamed copy stands for the film
    if os.name == 'nt':  # evidence folders carry the full script title: paths over 260 chars need the long-path prefix (film 196)
        fs = [Path(LONG + str(f.absolute())) if len(str(f.absolute())) > 240 else f for f in fs]
    fs = sorted(fs, key=lambda f: f.stat().st_mtime, reverse=True)
    return [f for f in fs if skip is None or f.resolve() != Path(skip).resolve()]


def check(new, story=False, last=LAST, quiet=False):
    """[(level, id, message)] for the gate; prints the same lines."""
    mine = maps(new); out = []; same_red = []
    for f in previous(story, new)[:last]:
        s, red = similarity(mine, maps(f)); who = (f.parent.parent.name if not story else f.stem)[:60]
        if red >= RED_SAME:
            same_red.append(who)
        if s >= HARD:
            out.append(('!!', f'thumb-template:{who[:30]}', f'the thumbnail has the layout of "{who}" (layout match {s:.2f}, limit {HARD}): '
                        'move the subject and the text, change the form of the hook'))
        elif s >= SOFT:
            out.append(('!', f'thumb-alike:{who[:30]}', f'the thumbnail is close to "{who}" (layout match {s:.2f}): look at them side by side'))
    if len(same_red) >= 2:
        out.append(('!!', 'thumb-red-place', f'the red emphasis sits where it sat on {len(same_red)} of the last {last} thumbnails ({", ".join(same_red)[:160]}): put it elsewhere or drop it'))
    if not quiet:
        for lv, _, msg in out:
            print(lv, msg)
        print(f'thumbrepeat: {sum(1 for o in out if o[0] == "!!")} to fix, compared with the last {last}')
    return out


def sheet(new, out, story=False, last=LAST):
    tw, th = 384, 216; fs = [Path(new)] + previous(story, new)[:last]
    im = Image.new('RGB', (tw * len(fs), th), 'black')
    for i, f in enumerate(fs):
        im.paste(Image.open(f).convert('RGB').resize((tw, th)), (i * tw, 0))
    im.save(out, quality=88); print(f'{out}: the new one on the left, then the last {len(fs) - 1}, newest first')


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    story = '--story' in sys.argv
    if '--sheet' in sys.argv:
        sheet(sys.argv[1], sys.argv[sys.argv.index('--sheet') + 1], story)
    sys.exit(1 if any(o[0] == '!!' for o in check(sys.argv[1], story)) else 0)
