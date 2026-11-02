"""Story thumbnail in the channel's style (user reference 2026-11-02, "XÓA SỔ? / BÓNG MA TRƯỜNG SƠN"):
gritty B&W photo with aged, torn edges; the hero on the right looking at the viewer; two overlay lines on the left in a
worn military stencil (never the title; GEM brief: one line has a strong verb, 2-4 words each, white/grey, no glow); red hand-drawn notes (circle, arrow, dashed path, short labels).

  PY scripts/story_thumb.py spec.json out.jpg

spec: {"image": path, "hook": "LỆCH 1 NỐT?", "sub": "NGƯỜI THỢ ĐÀN ĐÀ LẠT", "hook_xy": [70, 330],
       "notes": [{"type": "circle", "box": [x0, y0, x1, y1], "label": "BẰNG CHỨNG", "label_xy": [x, y]},
                 {"type": "arrow", "from": [x, y], "to": [x, y], "label": "AN NINH", "label_xy": [x, y]},
                 {"type": "dashed", "points": [[x, y], ...], "label": "...", "label_xy": [x, y]}]}
Coordinates are in the 1280x720 output. Keep the bottom-right corner clear (YouTube's duration badge)."""
import json, math, random, sys
from pathlib import Path
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageOps

sys.path.insert(0, str(Path(__file__).resolve().parent))
import render as R

W, H = 1280, 720
RED = (205, 32, 30)
rng = random.Random(7)


def photo(path):
    im = ImageOps.fit(Image.open(path).convert('L'), (W, H))
    im = ImageEnhance.Contrast(im).enhance(1.3).filter(ImageFilter.UnsharpMask(2, 110, 2))
    return ImageOps.colorize(im, (10, 9, 8), (238, 232, 220))


def aged(im):
    """Paper texture, dark torn border, a few scratches and fold lines."""
    px = Image.effect_noise((W, H), 28).convert('L').filter(ImageFilter.GaussianBlur(0.6))
    im = Image.blend(im, ImageOps.colorize(px, (60, 56, 50), (200, 194, 182)), 0.10)
    edge = Image.new('L', (W, H), 0); d = ImageDraw.Draw(edge)
    for side in range(4):  # ragged border: random-depth bites along each edge
        for k in range(0, (W if side % 2 == 0 else H), 6):
            depth = int(abs(rng.gauss(0, 1)) * 10 + 6 + (rng.random() < 0.04) * rng.randint(10, 40))
            if side == 0: d.rectangle((k, 0, k + 6, depth), fill=255)
            if side == 1: d.rectangle((W - depth, k, W, k + 6), fill=255)
            if side == 2: d.rectangle((k, H - depth, k + 6, H), fill=255)
            if side == 3: d.rectangle((0, k, depth, k + 6), fill=255)
    edge = edge.filter(ImageFilter.GaussianBlur(3))
    im = Image.composite(Image.new('RGB', (W, H), (12, 11, 10)), im, edge)
    vig = Image.radial_gradient('L').resize((W, H)).point(lambda v: int(min(255, v * 0.9)))
    im = Image.composite(Image.new('RGB', (W, H), (0, 0, 0)), im, vig.point(lambda v: int(v * 0.55)))
    d = ImageDraw.Draw(im)
    for _ in range(6):  # a few faint hairline scratches
        x = rng.randint(0, W); y = rng.randint(0, H); L = rng.randint(40, 220); a = rng.uniform(-0.4, 0.4) + math.pi / 2
        d.line((x, y, x + L * math.cos(a), y + L * math.sin(a)), fill=(rng.randint(90, 140),) * 3, width=1)
    return im


def stencil_line(im, xy, s, height, fill, squeeze=0.84):
    """One overlay line in the channel's thumbnail font (GEM brief: military stencil, distressed, white/grey, no glow,
    horizontal): Saira Stencil One, squeezed to a condensed cut, worn with speckled holes. Returns its width."""
    f = R.font('stencil', int(height / 0.74))
    tmp = Image.new('L', (W * 2, int(height * 2)), 0); td = ImageDraw.Draw(tmp)
    bb = td.textbbox((0, 0), s, font=f); td.text((-bb[0], -bb[1]), s, font=f, fill=255)
    tmp = tmp.crop((0, 0, bb[2] - bb[0], bb[3] - bb[1]))
    tmp = tmp.resize((int(tmp.width * squeeze), tmp.height), Image.LANCZOS)
    holes = Image.effect_noise(tmp.size, 70).convert('L').filter(ImageFilter.GaussianBlur(1.1)).point(lambda v: 0 if v > 172 else 255)
    worn = Image.composite(tmp, Image.new('L', tmp.size, 0), holes)
    sh = tmp.filter(ImageFilter.MaxFilter(5)).point(lambda v: int(v * 0.85))   # hard dark shadow (not a glow): legible on bright areas
    im.paste((0, 0, 0), (int(xy[0]) + 5, int(xy[1]) + 5), sh)
    im.paste(fill, (int(xy[0]), int(xy[1])), worn)
    return tmp.width


def label(d, xy, s, size=34):
    f = R.font('head', size); x, y = xy
    d.text((x + 2, y + 2), s, font=f, fill=(0, 0, 0)); d.text((x, y), s, font=f, fill=RED)


def notes(im, spec):
    d = ImageDraw.Draw(im)
    for n in spec.get('notes', []):
        if n['type'] == 'circle':
            x0, y0, x1, y1 = n['box']
            for j, w in ((0, 5), (1, 3)):  # two slightly offset strokes: hand-drawn
                o = j * 5
                d.arc((x0 - o, y0 + o, x1 + o, y1 - o), start=rng.randint(-20, 10), end=rng.randint(330, 370), fill=RED, width=w)
        elif n['type'] == 'arrow':
            (ax, ay), (bx, by) = n['from'], n['to']
            d.line((ax, ay, bx, by), fill=RED, width=6)
            ang = math.atan2(by - ay, bx - ax)
            for s in (-0.5, 0.5):
                d.line((bx, by, bx - 30 * math.cos(ang + s), by - 30 * math.sin(ang + s)), fill=RED, width=6)
        elif n['type'] == 'dashed':
            pts = n['points']
            for (ax, ay), (bx, by) in zip(pts, pts[1:]):
                L = math.hypot(bx - ax, by - ay); k = 0
                while k < L:
                    t0, t1 = k / L, min(1, (k + 18) / L)
                    d.line((ax + (bx - ax) * t0, ay + (by - ay) * t0, ax + (bx - ax) * t1, ay + (by - ay) * t1), fill=RED, width=6)
                    k += 30
        if n.get('label'):
            label(d, n['label_xy'], n['label'])


def main():
    spec = json.loads(Path(sys.argv[1]).read_text(encoding='utf-8'))
    im = photo(spec['image'])
    if spec.get('aged', True):  # off when the base image is already a damaged print (GEM [STYLE] prompt)
        im = aged(im)
    x, y = spec.get('hook_xy', [56, 300])
    h1, h2 = spec.get('line1_h', 130), spec.get('line2_h', 70)   # GEM: each line big (15-20 % of the frame for line 1)
    stencil_line(im, (x, y), spec['hook'], h1, (232, 230, 224))
    if spec.get('sub'):
        stencil_line(im, (x + 4, y + h1 * 1.5), spec['sub'], h2, (196, 194, 188))  # room for the next line's accents
    notes(im, spec)
    im.save(sys.argv[2], quality=93)


if __name__ == '__main__':
    main()
