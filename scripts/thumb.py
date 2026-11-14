"""Archival thumbnail from real photos, in the four layouts of the reference channel's best thumbnails (user 2026-11-14,
C:/Users/<user>/Downloads/thum: 164k/97k/52k/41k views). Every layout carries a YEAR/DATE LABEL (the user noticed the
high-view ones all show one), one real archival photo filling the frame, a few big words, ONE red emphasis and a tiny
photo credit.

  PY scripts/thumb.py spec.json out.jpg

spec: {"layout": "panel" | "portrait" | "question" | "band", "lang": "de",
       "photo": "path.jpg", "photo2": "path.jpg" (panel: inset; portrait: the portrait on the left),
       "tag": "Unternehmen Barbarossa · Juni 1941"   (the year label: always),
       "kicker": "small line above the title" (band), "title": "big words", "title2": "second line (panel)",
       "red": "the one red emphasis (number, question, event name)", "date": "line on the red band (band)",
       "credit": "Foto: Bundesarchiv, Bild 101I-...", "fx": 0.5, "fy": 0.5 (photo focus),
       "photo_id" / "photo2_id": Commons page id or "File:..." title (needed by scripts/thumbcheck.py unless the file is commons-<id>.*)}
After making it: PY scripts/thumbcheck.py JOB out.jpg, then a fresh reviewer checks the picture (docs/WORKFLOW.md "Thumbnail").
  panel    (thum1): photo full, dark panel bottom-left with a serif title and a red number, inset photo, label top-left
  portrait (thum2): portrait strip left, photo right, navy label, two white lines, a huge red event name with white outline
  question (thum3): grey photo, huge serif title top-left, white question on a red box, navy label bottom-left
  band     (thum4): light top with kicker + black title, navy label top-right, photo, red band with date + headline
"""
import json, sys
from pathlib import Path
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageOps

ROOT = Path(__file__).resolve().parents[1]
F = ROOT / 'assets' / 'fonts'
W, H = 1280, 720
RED, NAVY, INK, CREAM = (205, 45, 38), (27, 43, 74), (20, 20, 22), (240, 236, 226)


def font(kind, size, lang):
    from PIL import ImageFont
    if lang == 'ja':
        f = ImageFont.truetype(str(F / ('ShipporiMincho-Bold.ttf' if kind == 'serif' else 'MPLUS1p-Bold.ttf')), size)
        return f
    if kind == 'serif':
        f = ImageFont.truetype(str(F / 'SourceSerif4.ttf'), size)
        try:
            f.set_variation_by_axes([800, 60])
        except (OSError, ValueError):
            pass
        return f
    if kind == 'sans':
        f = ImageFont.truetype(str(F / 'Oswald.ttf'), size)
        try:
            f.set_variation_by_axes([700])
        except (OSError, ValueError):
            pass
        return f
    return ImageFont.truetype(str(F / 'BeVietnamPro-SemiBold.ttf'), size)  # 'small'


def fit(d, s, kind, size, lang, maxw):
    while size > 18 and d.textlength(s, font=font(kind, size, lang)) > maxw:
        size -= 2
    return font(kind, size, lang)


def photo(p, w, h, fx=0.5, fy=0.5, grey=True):
    im = ImageOps.exif_transpose(Image.open(p)).convert('RGB')
    im = ImageOps.fit(im, (w, h), Image.LANCZOS, centering=(fx, fy))
    if grey:
        g = ImageOps.grayscale(im); g = ImageOps.autocontrast(g, cutoff=1)
        im = ImageOps.colorize(g, (18, 16, 14), (238, 232, 220))  # neutral archival print, faint warmth
    return ImageEnhance.Contrast(im).enhance(1.08)


def outlined(d, xy, s, f, fill, stroke, sw):
    d.text(xy, s, font=f, fill=fill, stroke_width=sw, stroke_fill=stroke)


def label(d, x, y, s, lang, size=26, bg=NAVY, fg=(255, 255, 255), anchor='l'):
    f = font('small', size, lang); w = d.textlength(s, font=f); pad = 12
    x0 = x - w - 2 * pad if anchor == 'r' else x
    d.rectangle((x0, y, x0 + w + 2 * pad, y + size + 16), fill=bg); d.text((x0 + pad, y + 5), s, font=f, fill=fg)


CREDIT_LEFT = False


def credit(d, s, lang, dark=True):
    if not s:
        return
    f = font('small', 14, lang); w = d.textlength(s, font=f)
    x0 = 4 if CREDIT_LEFT else W - w - 22  # "credit_left": YouTube's duration stamp covers the bottom-right corner (reviewer 2026-11-14)
    d.rectangle((x0, H - 26, x0 + w + 18, H - 4), fill=(0, 0, 0, 150) if dark else (255, 255, 255, 170))
    d.text((x0 + 9, H - 24), s, font=f, fill=(235, 235, 235) if dark else (40, 40, 40))


def panel(s, lang):
    img = photo(s['photo'], W, H, s.get('fx', 0.5), s.get('fy', 0.4))
    ov = Image.new('RGBA', (W, H)); od = ImageDraw.Draw(ov)
    for y in range(int(H * 0.42), H):  # dark panel rising from the bottom
        a = min(235, int(255 * (y - H * 0.42) / (H * 0.22)))
        od.line((0, y, W, y), fill=(22, 26, 34, a))
    img = Image.alpha_composite(img.convert('RGBA'), ov); d = ImageDraw.Draw(img)
    if s.get('photo2'):
        p2 = photo(s['photo2'], 330, 210); img.paste(Image.new('RGB', (342, 222), (235, 232, 224)), (W - 372, H - 262)); img.paste(p2, (W - 366, H - 256))
    maxw = W - (420 if s.get('photo2') else 80) - 40
    ft = fit(d, s['title'], 'serif', 118, lang, maxw); d.text((40, H - 300), s['title'], font=ft, fill=(255, 255, 255))
    if s.get('title2') or s.get('red'):
        f2 = font('serif', 58, lang); x = 44; y = H - 150
        if s.get('title2'):
            d.text((x, y + 20), s['title2'], font=f2, fill=(238, 236, 230)); x += d.textlength(s['title2'] + ' ', font=f2)
        if s.get('red'):
            fr = fit(d, s['red'], 'serif', 96, lang, maxw - (x - 44)); d.text((x, y - 6), s['red'], font=fr, fill=RED)
    label(d, 22, 18, s['tag'], lang, 24, bg=(14, 14, 16))
    credit(d, s.get('credit'), lang)
    return img


def portrait(s, lang):
    img = Image.new('RGB', (W, H)); pw = 430
    img.paste(photo(s['photo'], W - pw, H, s.get('fx', 0.5), s.get('fy', 0.4)), (pw, 0))
    img.paste(photo(s['photo2'], pw, H, 0.5, 0.25), (0, 0))
    d = ImageDraw.Draw(img)
    label(d, pw + 30, 18, s['tag'], lang, 30)
    fs = font('sans', 64, lang)
    for i, ln in enumerate([x for x in (s.get('title'), s.get('title2')) if x]):
        w = d.textlength(ln, font=fs); outlined(d, (W - w - 50, 210 + i * 86), ln, fs, (255, 255, 255), INK, 5)
    if s.get('kicker'):
        fk = fit(d, s['kicker'], 'sans', 74, lang, pw - 20); outlined(d, (16, H - 330), s['kicker'], fk, (255, 255, 255), INK, 6)
    fr = fit(d, s['red'], 'sans', 190, lang, W - 300); w = d.textlength(s['red'], font=fr)
    outlined(d, (W - w - 40, H - 250), s['red'], fr, RED, (255, 255, 255), 10)
    credit(d, s.get('credit'), lang)
    return img


def question(s, lang):
    img = photo(s['photo'], W, H, s.get('fx', 0.5), s.get('fy', 0.5)).convert('RGBA')
    ov = Image.new('RGBA', (W, H)); od = ImageDraw.Draw(ov)
    for y in range(0, 330):  # dark top so the light serif title reads on any photo
        od.line((0, y, W, y), fill=(14, 14, 16, int(200 * (1 - y / 330) ** 1.2)))
    img = Image.alpha_composite(img, ov); d = ImageDraw.Draw(img, 'RGBA')
    ft = fit(d, s['title'], 'serif', 120, lang, W - 80)
    outlined(d, (36, 18), s['title'], ft, (246, 243, 236), (30, 30, 30), 3)
    fq = fit(d, s['red'], 'serif', 76, lang, W - 160); w = d.textlength(s['red'], font=fq)
    d.rectangle((36, 168, 36 + w + 40, 168 + 108), fill=RED); d.text((56, 176), s['red'], font=fq, fill=(255, 255, 255))
    label(d, 30, H - 74, s['tag'], lang, 30)
    credit(d, s.get('credit'), lang)
    return img


def band(s, lang):
    img = Image.new('RGB', (W, H), (246, 244, 240)); top, bot = 205, 165
    img.paste(photo(s['photo'], W, H - top - bot, s.get('fx', 0.5), s.get('fy', 0.5)), (0, top))
    d = ImageDraw.Draw(img)
    if s.get('kicker'):
        d.text((40, 16), s['kicker'], font=font('sans', 44, lang), fill=INK)
    ft = fit(d, s['title'], 'sans', 104, lang, W - 80); d.text((38, 66), s['title'], font=ft, fill=INK)
    label(d, W - 24, 16, s['tag'], lang, 26, anchor='r')
    d.rectangle((0, H - bot, W, H), fill=RED)
    if s.get('date'):
        d.text((40, H - bot + 8), s['date'], font=font('small', 32, lang), fill=(255, 255, 255))
    fr = fit(d, s['red'], 'sans', 100, lang, W - 80); w = d.textlength(s['red'], font=fr)
    d.text(((W - w) / 2, H - bot + 34), s['red'], font=fr, fill=(255, 255, 255))
    credit(d, s.get('credit'), lang)
    return img


def make(spec, out):
    s = json.loads(Path(spec).read_text(encoding='utf-8')) if not isinstance(spec, dict) else spec
    global CREDIT_LEFT; CREDIT_LEFT = bool(s.get("credit_left"))
    lang = s.get('lang', 'en')
    img = {'panel': panel, 'portrait': portrait, 'question': question, 'band': band}[s.get('layout', 'panel')](s, lang)
    img.convert('RGB').save(out, quality=94)
    Path(out).with_suffix('.json').write_text(json.dumps(s, ensure_ascii=False, indent=1), encoding='utf-8')  # for scripts/thumbcheck.py
    return out


if __name__ == '__main__':
    print(make(sys.argv[1], sys.argv[2]))
