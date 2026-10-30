"""timeline.json -> picture (1080p H.264), voice-led mix (-14 LUFS, <= -1 dBTP), muxed MP4. House style: docs/STYLE.md.

Picture: one Python frame loop piped into ffmpeg.
- Photos: cover-cropped with a slow push (portrait/square: "print on black"), graded as archival sepia.
- Video: decoded by ffmpeg (cover crop) and graded per frame (film / modern).
- Film grain and a smooth vignette everywhere; hard cuts unless a clip asks for transition_in.
- Animated overlays: date tag, lower third, callout, credit line, and full-screen cards (title, question, chapter,
  stat on parchment, typewriter quote).
"""
import json, math, subprocess, sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageFont, ImageOps

import render_fx as FX

W, H = 1920, 1080
ROOT = Path(__file__).resolve().parents[1]
FONTS = ROOT / 'assets' / 'fonts'
LANG = 'en'
LOC = {'chapter': {'vi': 'CHƯƠNG', 'en': 'CHAPTER', 'es': 'CAPÍTULO', 'fr': 'CHAPITRE', 'de': 'KAPITEL'}}  # fixed card words by script language
OFFWHITE, RED, AMBER = (237, 231, 220), (200, 55, 45), (224, 160, 48)
PARCH, BROWN, INK = (217, 204, 170), (43, 33, 25), (38, 32, 28)
_fc = {}
ENC_THREADS = []  # e.g. ['-threads', '2'] when several picture() renders run side by side (studio parallel ranges)
X264 = ['-c:v', 'libx264', '-preset', 'medium', '-crf', '17']  # the house picture encode (render/picture.mp4)
NVENC = ['-c:v', 'h264_nvenc', '-preset', 'p5', '-tune', 'hq', '-rc', 'vbr', '-cq', '18', '-b:v', '0', '-profile:v', 'high']
FRAME_STEP = 1  # studio fast previews: 2 = draw every other frame and repeat it (like a 12 fps capture)
VIDEO_ENC = X264  # the studio switches to NVENC for previews and whole-picture renders (frees the CPU for the frame loop)


def font(kind, size):
    """kind: head (Oswald Bold), mono, monomed, body (Be Vietnam Pro SemiBold), bodyreg."""
    key = (kind, size)
    if key not in _fc:
        if kind == 'head':
            f = ImageFont.truetype(str(FONTS / 'Oswald.ttf'), size)
            try:
                f.set_variation_by_axes([700])
            except (OSError, ValueError):
                pass
        else:
            name = {'mono': 'IBMPlexMono-Regular.ttf', 'monomed': 'IBMPlexMono-Medium.ttf',
                    'body': 'BeVietnamPro-SemiBold.ttf', 'bodyreg': 'BeVietnamPro-Regular.ttf'}[kind]
            f = ImageFont.truetype(str(FONTS / name), size)
        _fc[key] = f
    return _fc[key]


def ease(x):
    x = min(1.0, max(0.0, x)); return 1 - (1 - x) ** 3


# ------------------------------------------------------------------ grading
def _lut(kind):
    """Per-channel tone curves (256 entries) for each grade; applied to luminance-mixed RGB."""
    x = np.linspace(0, 1, 256, dtype=np.float32)
    s = x * x * (3 - 2 * x)                       # gentle S contrast
    base = 0.06 + 0.88 * (0.65 * s + 0.35 * x)    # lifted blacks, soft highlights
    if kind == 'archival':
        tint = np.stack([base * 1.05, base * 0.98, base * 0.86], 1)
    elif kind == 'film':
        tint = np.stack([base * 0.92, base * 1.0, base * 0.97], 1)
    else:  # modern
        tint = np.stack([base * (0.96 + 0.06 * x), base, base * (1.04 - 0.08 * x)], 1)
    return (np.clip(tint, 0, 1) * 255).astype(np.uint8)


LUTS = {k: _lut(k) for k in ('archival', 'film', 'modern')}
SAT = {'archival': 0.0, 'film': 0.25, 'modern': 0.35}


def grade(a, kind):
    """a: HxWx3 uint8 -> graded uint8."""
    if kind == 'none':
        return a
    f = a.astype(np.float32)
    y = f @ np.array([0.299, 0.587, 0.114], np.float32)
    s = SAT.get(kind, 0.35)
    f = y[..., None] + (f - y[..., None]) * s
    idx = np.clip(f, 0, 255).astype(np.uint8)
    lut = LUTS.get(kind, LUTS['modern'])
    return np.stack([lut[idx[..., c], c] for c in range(3)], -1)


_vig = None
_grain = None
_hf = None


def hf_grain(a, t):
    """AutoVeo3 HyperFrames "Film grain" exactly: the Chromium-rendered fractalNoise tile (assets/fx/grain_tile.png,
    scripts/grain_tile.mjs) tiled at 200 px, layer opacity 0.09, background-position stepping 0,0 -> 50,-30 ->
    -20,40 every 0.05 s (CSS `grainAnim 0.15s steps(3)`). Applied to the picture under the text overlays."""
    global _hf
    if _hf is None:
        tile = np.asarray(Image.open(ROOT / 'assets' / 'fx' / 'grain_tile.png').convert('RGBA'), np.float32) / 255
        _hf = []
        for ox, oy in ((0, 0), (50, -30), (-20, 40)):
            yy = (np.arange(H)[:, None] - oy) % 200; xx = (np.arange(W)[None, :] - ox) % 200
            t4 = tile[yy, xx]
            # one C pass (PIL composite with a per-pixel mask) instead of float numpy: same result to +-1 level
            _hf.append((Image.fromarray(np.round(t4[..., :3] * 255).astype(np.uint8)),
                        Image.fromarray(np.round(t4[..., 3] * 0.09 * 255).astype(np.uint8), 'L')))
    return np.asarray(_grain_img(Image.fromarray(a), t))


def _grain_img(img, t):
    if _hf is None:
        hf_grain(np.zeros((H, W, 3), np.uint8), 0)
    top, mask = _hf[int(t / 0.05) % 3]
    return Image.composite(top, img, mask)


def finish(a, i):
    """Smooth vignette only. No synthetic grain (user review 2026-10-30: it reads as noise); old-film texture comes
    from the archival sources themselves."""
    global _vig
    if _vig is None:
        y, x = np.mgrid[0:H, 0:W].astype(np.float32)
        r = np.sqrt(((x - W / 2) / (W * 0.62)) ** 2 + ((y - H / 2) / (H * 0.62)) ** 2)
        g = np.round((1 - 0.38 * np.clip(r - 0.45, 0, 1) ** 1.6) * 255).astype(np.uint8)
        _vig = Image.merge('RGB', [Image.fromarray(g, 'L')] * 3)  # multiplied in one C pass (ImageChops)
    return np.asarray(_finish_img(Image.fromarray(a)))


def _finish_img(img):
    if _vig is None:
        finish(np.zeros((H, W, 3), np.uint8), 0)
    return ImageChops.multiply(img, _vig)


# ------------------------------------------------------------------ sources
def is_print(w, h):
    return w / h < 1.2  # portrait/square photos become a print on black


def framed_print(im):
    bg = Image.new('RGB', (W, H), (12, 11, 10))
    fg = ImageOps.contain(im, (int(W * 0.8), int(H * 0.86)), Image.LANCZOS)
    sh = Image.new('L', (fg.width + 60, fg.height + 60), 0)
    ImageDraw.Draw(sh).rectangle((30, 30, fg.width + 30, fg.height + 30), fill=150)
    bg.paste((0, 0, 0), ((W - fg.width) // 2 - 30, (H - fg.height) // 2 - 22), sh.filter(ImageFilter.GaussianBlur(18)))
    bg.paste(fg, ((W - fg.width) // 2, (H - fg.height) // 2))
    return bg


class Photo:
    def __init__(self, path, clip, idx):
        im = ImageOps.exif_transpose(Image.open(path)).convert('RGB')
        g = clip.get('grade', 'archival')
        if is_print(im.width, im.height):
            self.base = Image.fromarray(grade(np.asarray(framed_print(im)), g)); self.push = 0.03
        else:
            self.base = Image.fromarray(grade(np.asarray(ImageOps.fit(im, (int(W * 1.1), int(H * 1.1)), Image.LANCZOS)), g))
            self.push = 0.07
        if FX.color_active(clip.get('color')):  # studio colour (Màu), on top of the grade
            self.base = Image.fromarray(FX.apply_color(np.asarray(self.base), clip['color']))
        m = clip.get('motion') or {}
        self.m = m if m.get('type') in ('custom', 'none') else None
        self.out = m.get('type') == 'pull' or (idx % 3 == 2 and not m)
        self.dx = m.get('dx', (0.04 if idx % 2 else -0.04))
        self.dur = max(0.1, clip['end'] - clip['start'])

    def box(self, t):
        """(x0, y0, x1, y1): the part of self.base shown at clip time t (Ken Burns). Shared by the CPU resize below
        and the GPU sampler (render_gl), so both frame the same view."""
        bw, bh = self.base.size
        if self.m:  # studio motion (Chuyển động): explicit from/to view
            return FX.custom_box(self.m, t / self.dur, bw, bh, t) if self.m['type'] == 'custom' else FX.custom_box({}, 0, bw, bh)
        p = min(1.0, max(0.0, t / self.dur)); p = p * p * (3 - 2 * p) * 0.6 + p * 0.4
        f = (1 - self.push * (1 - p)) if self.out else (1 - self.push * p)
        ww, wh = bw * f, bh * f
        cx = bw / 2 + self.dx * bw * (p - 0.5) * 0.5
        x = min(max(0, cx - ww / 2), bw - ww); y = (bh - wh) / 2
        return x, y, x + ww, y + wh

    def frame(self, t):
        return np.asarray(self.base.resize((W, H), Image.BICUBIC, box=self.box(t)))

    def close(self):
        pass


class Video:
    def __init__(self, path, clip, fps):
        info = json.loads(subprocess.run(['ffprobe', '-v', 'error', '-select_streams', 'v:0', '-show_entries',
                                          'stream=width,height', '-of', 'json', str(path)], capture_output=True).stdout)
        s = info['streams'][0]
        self.g = clip.get('grade', 'modern'); self.color = clip.get('color')
        if is_print(s['width'], s['height']):
            vf = (f'scale={int(W * 0.8)}:{int(H * 0.86)}:force_original_aspect_ratio=decrease,'
                  f'pad={W}:{H}:(ow-iw)/2:(oh-ih)/2:color=0x0c0b0a')
        else:
            vf = f'scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H}'
        if clip.get('bloom'):  # glow on bright parts (map arrows, fire): threshold, blur, screen-blend back
            vf += (',split[a][b];[b]colorlevels=rimin=0.5:gimin=0.55:bimin=0.55,gblur=sigma=16[g];'
                   '[a][g]blend=all_mode=screen:all_opacity=0.8')
        self.p = subprocess.Popen(['ffmpeg', '-v', 'error', '-ss', str(clip.get('in', 0.0)), '-i', str(path), '-an',
                                   '-vf', f'{vf},fps={fps},format=rgb24', '-f', 'rawvideo', '-'],
                                  stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
        self.last = np.zeros((H, W, 3), np.uint8)

    def frame(self, t):
        raw = self.p.stdout.read(W * H * 3) if self.p else b''
        if len(raw) == W * H * 3:
            self.last = FX.apply_color(grade(np.frombuffer(raw, np.uint8).reshape(H, W, 3), self.g), self.color)
        return self.last

    def close(self):
        if self.p:
            self.p.kill(); self.p.stdout.close(); self.p.wait(); self.p = None


class Blank:
    def __init__(self, color=(10, 9, 8)):
        self.a = np.full((H, W, 3), color, np.uint8)

    def frame(self, t):
        return self.a

    def close(self):
        pass


# ------------------------------------------------------------------ textures
_tex = {}


def texture(kind):
    if kind not in _tex:
        rng = np.random.default_rng(3)
        low = np.asarray(Image.fromarray((rng.random((27, 48)) * 255).astype(np.uint8)).resize((W, H), Image.BICUBIC), np.float32) / 255
        fine = rng.normal(0, 1, (H, W)).astype(np.float32)
        col = np.array(PARCH if kind == 'parchment' else BROWN if kind == 'brown' else (14, 13, 12), np.float32)
        amp = {'parchment': (26, 5), 'brown': (14, 3), 'black': (6, 2)}[kind]
        a = col + (low[..., None] - 0.5) * amp[0] + fine[..., None] * amp[1]
        y, x = np.mgrid[0:H, 0:W].astype(np.float32)
        r = np.sqrt(((x - W / 2) / W) ** 2 + ((y - H / 2) / H) ** 2)
        a *= (1 - 0.5 * np.clip(r - 0.25, 0, 1))[..., None]
        _tex[kind] = Image.fromarray(np.clip(a, 0, 255).astype(np.uint8)).convert('RGBA')
    return _tex[kind]


# ------------------------------------------------------------------ overlays (drawn per frame, animated)
_sh = {}


def _shade(a):
    """Soft dark gradient in the lower-left quarter behind a lower third (alpha a)."""
    k = round(a, 2)
    if k not in _sh:
        y, x = np.mgrid[0:H, 0:W].astype(np.float32)
        m = np.clip((y - H * 0.5) / (H * 0.5), 0, 1) ** 1.2 * np.clip(1 - x / (W * 0.75), 0, 1) ** 0.8
        al = (m * 170 * k).astype(np.uint8)
        _sh[k] = Image.fromarray(np.dstack([np.zeros((H, W, 3), np.uint8), al]), 'RGBA')
    return _sh[k]


def text_w(d, s, f):
    return d.textlength(s, font=f)


def shadow_text(d, xy, s, f, fill, sh=150):
    d.text((xy[0] + 2, xy[1] + 2), s, font=f, fill=(0, 0, 0, sh)); d.text(xy, s, font=f, fill=fill)


def draw_overlay(lay, o, lt):
    """lt: seconds since the overlay started; dur: its length. Returns True if it covers the whole frame."""
    d = ImageDraw.Draw(lay); pr = o.get('props', {}); t = o.get('type'); dur = o['end'] - o['start']
    out = min(1.0, max(0.0, (dur - lt) / 0.35))                     # fade-out multiplier
    if t == 'date_tag':
        a = ease((lt - 0.3) / 0.4) * out
        if a <= 0: return False
        f = font('head', 44); s = pr['text']; w = text_w(d, s, f); x = 60 - (1 - a) * 30
        d.rectangle((x, 50, x + w + 46, 116), fill=(16, 14, 12, int(185 * a)))
        d.rectangle((x, 50, x + 7, 116), fill=RED + (int(255 * a),))
        d.text((x + 24, 52), s, font=f, fill=OFFWHITE + (int(255 * a),))
    elif t == 'lower_third':
        x, y = 90, H - 330
        g = ease((lt - 0.2) / 0.5) * out
        if g <= 0: return False
        lay.alpha_composite(_shade(min(1.0, g * 1.4)))  # keeps small text readable over bright footage
        d = ImageDraw.Draw(lay)
        d.rectangle((x, y + 172 * (1 - g), x + 7, y + 172), fill=RED + (int(255 * out),))
        k = pr.get('kicker', '').upper(); n = int(len(k) * min(1, max(0, (lt - 0.3) / 0.6)))
        d.text((x + 30, y + 2), k[:n], font=font('monomed', 30), fill=(225, 220, 210, int(235 * out)))
        a2 = ease((lt - 0.5) / 0.5) * out
        shadow_text(d, (x + 28, y + 40 + 18 * (1 - a2)), pr.get('name', '').upper(), font('head', 84), OFFWHITE + (int(255 * a2),), int(140 * a2))
        a3 = ease((lt - 0.8) / 0.5) * out
        shadow_text(d, (x + 30, y + 146), pr.get('sub', ''), font('body', 30), (225, 220, 210, int(240 * a3)), int(120 * a3))
    elif t == 'callout':
        a = ease((lt - 0.25) / 0.5) * out
        if a <= 0: return False
        f = font('head', 78); s = pr['text'].upper(); w = text_w(d, s, f); x = (W - w) / 2; y = H - 300 + 14 * (1 - a)
        shadow_text(d, (x, y), s, f, OFFWHITE + (int(255 * a),), int(160 * a))
        r = ease((lt - 0.55) / 0.6) * out
        d.rectangle((x, y + 112, x + w * r, y + 118), fill=RED + (int(255 * out),))
    elif t == 'text':
        FX.draw_text(lay, pr, lt, dur, font)
    elif t in ('title_card', 'question', 'chapter', 'stat', 'quote'):
        fade_in = ease(lt / 0.25)
        bg = {'stat': 'parchment', 'quote': 'brown', 'chapter': 'brown'}.get(t, 'black')
        if pr.get('background'): bg = pr['background']
        lay.alpha_composite(Image.blend(Image.new('RGBA', (W, H), (0, 0, 0, 0)), texture(bg), min(fade_in, out)))
        d = ImageDraw.Draw(lay)
        fn = {'title_card': card_title, 'question': card_question, 'chapter': card_chapter, 'stat': card_stat, 'quote': card_quote}[t]
        fn(d, pr, lt, out)
        return fade_in >= 1 and out >= 1
    return False


def card_title(d, pr, lt, out):
    a = ease((lt - 0.2) / 0.6) * out; f = font('head', 132); s = pr['text']; w = text_w(d, s, f)
    d.text(((W - w) / 2, H / 2 - 120 + 16 * (1 - a)), s, font=f, fill=OFFWHITE + (int(255 * a),))
    if pr.get('sub'):
        b = ease((lt - 0.8) / 0.6) * out; fs = font('head', 40); s2 = '  '.join(pr['sub'].upper()); w2 = text_w(d, s2, fs)
        d.text(((W - w2) / 2, H / 2 + 60), s2, font=fs, fill=RED + (int(255 * b),))


def card_question(d, pr, lt, out):
    a = ease((lt - 0.15) / 0.4) * out; f = font('head', 170); s = pr['text'].upper(); w = text_w(d, s, f)
    d.text(((W - w) / 2, H / 2 - 130), s, font=f, fill=RED + (int(255 * a),))


def card_chapter(d, pr, lt, out):
    a = ease((lt - 0.1) / 0.5) * out
    k = f"{LOC['chapter'].get(LANG, 'CHAPTER')} {pr.get('n', '')}"; fk = font('monomed', 28); d.text(((W - text_w(d, k, fk)) / 2, 300), k, font=fk, fill=(220, 210, 195, int(230 * a)))
    fn = font('head', 230); n = str(pr.get('n', '')); d.text(((W - text_w(d, n, fn)) / 2, 330 + 20 * (1 - a)), n, font=fn, fill=RED + (int(255 * a),))
    b = ease((lt - 0.5) / 0.5) * out; ft = font('head', 76); s = pr['title'].upper(); w = text_w(d, s, ft)
    d.text(((W - w) / 2, 640), s, font=ft, fill=OFFWHITE + (int(255 * b),))
    r = ease((lt - 0.8) / 0.6) * out; d.rectangle((W / 2 - 70 * r, 752, W / 2 + 70 * r, 758), fill=RED + (int(255 * out),))


def card_stat(d, pr, lt, out):
    a = ease((lt - 0.15) / 0.4) * out
    if pr.get('title'):
        d.text((150, 150), pr['title'].upper(), font=font('head', 56), fill=INK + (int(255 * a),))
        r = ease((lt - 0.3) / 0.7) * out; d.rectangle((150, 236, 150 + (W - 300) * r, 239), fill=INK + (int(200 * out),))
    items = pr['items']; colw = (W - 300) / len(items)
    for k, it in enumerate(items):
        b = ease((lt - 0.6 - 0.45 * k) / 0.45) * out
        if b <= 0: continue
        cx = 150 + colw * (k + 0.5); f = font('head', 170 if len(items) < 3 else 140)
        if it.get('pre'):
            fp = font('head', 34); d.text((cx - text_w(d, it['pre'], fp) / 2, 400), it['pre'], font=fp, fill=INK + (int(220 * b),))
        v = it['value']; w = text_w(d, v, f); y = 440 + 24 * (1 - b)
        d.text((cx - w / 2, y), v, font=f, fill=INK + (int(255 * b),))
        u = ease((lt - 0.9 - 0.45 * k) / 0.5) * out; d.rectangle((cx - w / 2, y + 232, cx - w / 2 + w * u, y + 238), fill=RED + (int(255 * out),))
        fl = font('head', 40); lw = text_w(d, it['label'].upper(), fl)
        d.text((cx - lw / 2, y + 256), it['label'].upper(), font=fl, fill=RED + (int(255 * b),))
        if it.get('sub'):
            fs = font('bodyreg', 30); sw = text_w(d, it['sub'], fs); d.text((cx - sw / 2, y + 310), it['sub'], font=fs, fill=INK + (int(220 * b),))


def card_quote(d, pr, lt, out):
    a = ease((lt - 0.1) / 0.4) * out
    if pr.get('kicker'):
        d.text((150, 170), pr['kicker'].upper(), font=font('mono', 24), fill=(205, 190, 170, int(220 * a)))
    if pr.get('title'):
        d.text((150, 204), pr['title'].upper(), font=font('head', 50), fill=OFFWHITE + (int(255 * a),))
        d.rectangle((150, 280, 150 + 70 * ease((lt - 0.3) / 0.4), 285), fill=RED + (int(255 * out),))
    f = font('monomed', 62); cps = pr.get('cps', 16); start = 0.7
    lines = pr['lines']; y = 380; shown = max(0, (lt - start) * cps)
    hl = pr.get('highlight', '')
    for ln in lines:
        n = int(min(len(ln), shown)); shown -= len(ln)
        part = ln[:n]
        if hl and hl in ln and n >= ln.index(hl) + len(hl) and lt > pr.get('highlight_at', 0):
            i = ln.index(hl); x0 = 150 + text_w(d, ln[:i], f); x1 = x0 + text_w(d, hl, f)
            d.rectangle((x0 - 6, y + 4, x1 + 6, y + 84), fill=AMBER + (int(235 * out),))
        d.text((150, y), part, font=f, fill=OFFWHITE + (int(255 * out),))
        if 0 < n < len(ln) or (n == len(ln) and shown <= 0 and int(lt * 2) % 2 == 0):
            cx = 150 + text_w(d, part, f); d.rectangle((cx + 4, y + 10, cx + 34, y + 80), fill=OFFWHITE + (int(255 * out),))
            break
        y += 96
    if pr.get('source') and lt > start + sum(len(l) for l in lines) / cps:
        d.text((150, y + 120), pr['source'], font=font('body', 26), fill=(205, 190, 170, int(220 * out)))


def read_srt(path):
    """[(start, end, text)] from an SRT file (burned-in subtitles)."""
    out = []
    for block in Path(path).read_text(encoding='utf-8-sig').replace('\r\n', '\n').strip().split('\n\n'):
        rows = block.split('\n')
        tm = next((r for r in rows if '-->' in r), None)
        if not tm:
            continue
        a, b = [sum(float(x) * m for x, m in zip(s.strip().replace(',', '.').split(':'), (3600, 60, 1))) for s in tm.split('-->')]
        out.append((a, b, ' '.join(rows[rows.index(tm) + 1:]).strip()))
    return out


def sub_key(start):
    """Stable id of a subtitle cue: its start in ms (studio edits are stored under it)."""
    return str(int(round(start * 1000)))


def subtitles(d, tl):
    """[(start, end, text)] burned-in cues: voice/voice.srt with the studio's edits applied (timeline
    "subtitle_overrides": {cue key: {"text", "start", "end"}}; empty text hides the cue)."""
    p = d / 'voice' / 'voice.srt'
    subs = read_srt(p) if p.exists() else []
    ov = tl.get('subtitle_overrides') or {}
    if not ov:
        return subs
    out = []
    for a, b, x in subs:
        o = ov.get(sub_key(a)) or {}
        a2, b2, x2 = o.get('start', a), o.get('end', b), o.get('text', x)
        if x2 and x2.strip() and b2 > a2:
            out.append((a2, b2, x2))
    return sorted(out)


def subtitle_layout(text, style=None):
    """(style, font, lines [(x, y, line)], box (x0, y0, x1, y1)) of a cue. y is the top of the last line, so a
    one-line cue sits exactly where the house style always put it (128 px above the bottom)."""
    s = dict(FX.SUB_DEFAULT); s.update(style or {})
    if s.get('upper'):
        text = text.upper()
    f = font(s['font'], int(s['size'])); d = ImageDraw.Draw(Image.new('L', (1, 1)))
    rows = text.split('\n'); lh = int(s['size'] * s.get('line_gap', 1.3))
    y_last = H - 128 if s.get('y') is None else H * s['y']
    lines = []
    for k, ln in enumerate(rows):
        w = d.textlength(ln, font=f); lines.append(((W - w) / 2, y_last - (len(rows) - 1 - k) * lh, ln, w))
    pad = s.get('box_pad', 18); wmax = max(l[3] for l in lines)
    box = ((W - wmax) / 2 - pad, lines[0][1] - pad * 0.35, (W + wmax) / 2 + pad, y_last + s['size'] * 1.3 + pad * 0.1)
    return s, f, lines, box


def subtitle_layer(text, style=None):
    """Burned-in subtitle: Be Vietnam Pro SemiBold, off-white with a dark outline, bottom centre. style: timeline
    "subtitle_style" from the studio (size, y, color, stroke, stroke_color, shadow, upper, box, box_color, box_pad,
    box_radius, font); the defaults draw exactly the house style."""
    s, f, lines, box = subtitle_layout(text, style)
    lay = Image.new('RGBA', (W, H)); d = ImageDraw.Draw(lay)
    if s['box'] > 0:
        fill = FX.hex_rgb(s.get('box_color', '#0A0908'), (10, 9, 8)) + (int(255 * s['box']),)
        r = int(s.get('box_radius', 0))
        (d.rounded_rectangle(box, radius=r, fill=fill) if r else d.rectangle(box, fill=fill))
    sh = s.get('shadow', 1.0); col = FX.hex_rgb(s['color']) + (255,)
    stroke = FX.hex_rgb(s.get('stroke_color', '#0A0908'), (10, 9, 8)) + (235,)
    for x, y, ln, _ in lines:
        if sh > 0:
            d.text((x + 3, y + 3), ln, font=f, fill=(0, 0, 0, int(150 * sh)))
        d.text((x, y), ln, font=f, fill=col, stroke_width=int(s['stroke']), stroke_fill=stroke)
    return lay


def credit_layer(text):
    lay = Image.new('RGBA', (W, H)); d = ImageDraw.Draw(lay); f = font('body', 22)
    text = text[:180]; w = d.textlength(text, font=f)
    d.text((W - 64 - w + 2, H - 62 + 2), text, font=f, fill=(0, 0, 0, 170))
    d.text((W - 64 - w, H - 62), text, font=f, fill=OFFWHITE + (220,))
    return lay


# ------------------------------------------------------------------ picture
def transition_in(cur, c, t, prev, k):
    """Clip c's transition_in at film time t. prev(): the previous clip's frame (called only when needed)."""
    tr = c.get('transition_in') or {}; typ = tr.get('type'); lt = t - c['start']
    if typ == 'fade':
        if k > 0 and lt < tr.get('dur', 0.4):
            a = lt / tr.get('dur', 0.4); cur = (prev() * (1 - a) + cur * a).astype(np.uint8)
    elif typ == 'dip':
        if lt < tr.get('dur', 0.5):
            cur = (cur * (lt / tr.get('dur', 0.5))).astype(np.uint8)
    elif typ in FX.TRANSITIONS and lt < tr.get('dur', 0.5):
        cur = FX.transition(prev() if k > 0 else None, cur, typ, lt / tr.get('dur', 0.5))
    return cur


def frame_layers(c, t, overlays, sub, cache, sub_style=None):
    """The RGBA layers pasted over the picture at t, in order: credit line, overlays (cards, tags), subtitle.
    Returns [(cache key or None, image)]: a key means the layer is unchanged while the key is (credit text, cue)."""
    covered = False; lay = None; out = []
    for o in overlays:
        if o['start'] <= t < o['end']:
            if lay is None:
                lay = Image.new('RGBA', (W, H))
            covered |= draw_overlay(lay, o, t - o['start'])
    if not covered and c.get('kind') != 'card':
        line = ' · '.join(x for x in (c.get('caption'), c.get('credit')) if x)
        if line:
            cache.setdefault(line, credit_layer(line)); out.append((('credit', line), cache[line]))
    if lay is not None:
        out.append((None, lay))
    if not covered and sub:
        key = (sub, json.dumps(sub_style, sort_keys=True))
        if cache.get('\0sub', (None,))[0] != key:
            cache['\0sub'] = (key, subtitle_layer(sub, sub_style))  # one cue at a time: keep only the current layer
        out.append((('sub',) + key, cache['\0sub'][1]))
    return out


def composite(cur, c, t, overlays, sub, fx, cache, effects=(), media=None, fps=24, sub_style=None, toff=0.0):
    """One finished frame on the CPU: graded source `cur` of video clip `c` at film time t, plus effect layers, grain,
    credit line, overlays and the burned-in subtitle `sub`. cache: dict kept by the caller (credit layers by text, the
    current subtitle layer). render_gl does the same on the GPU."""
    if effects:
        cur = FX.apply_effects(cur, effects, t, fps, media or {}, toff)
    # one RGB image from here on: layers are pasted through their alpha (= alpha-compositing onto an opaque frame)
    img = Image.fromarray(cur)
    if fx.get('grain'):
        img = _grain_img(img, t + toff)
    for _, layer in frame_layers(c, t, overlays, sub, cache, sub_style):
        img.paste(layer, (0, 0), layer)
    return np.asarray(_finish_img(img))


GRAIN_OFFSETS = ((0, 0), (50, -30), (-20, 40))
USE_GPU = True  # studio setting; without moderngl or an OpenGL 3.3 GPU frames fall back to the CPU
_gl = None


def gpu():
    """The process's GPU compositor, or None (disabled / unavailable)."""
    global _gl
    if not USE_GPU:
        return None
    if _gl is None:
        try:
            import render_gl
            _gl = render_gl.GLCompositor(ROOT / 'assets' / 'fx' / 'grain_tile.png')
        except Exception as e:  # noqa: BLE001 - no GPU / driver: render on the CPU
            print(f'GPU compositor unavailable, frames on the CPU: {e}', flush=True)
            _gl = False
    return _gl or None


def render_frame(t, vids, k, src, overlays, sub, fx, cache, effects=(), media=None, fps=24, sub_style=None, as_bytes=True, toff=0.0):
    """Frame t of the film (video clip vids[k], sources from src(j)), on the GPU (render_gl) when one is available,
    else on the CPU. Plain frames take the one-pass GPU shader; frames with a newer transition or effect layers take
    the multi-pass one, fed with the same parameters and random draws as the CPU path (render_fx.effect_plan)."""
    c = vids[k]; lt = t - c['start']
    tr = c.get('transition_in') or {}; typ = tr.get('type')
    in_tr = bool(typ) and lt < tr.get('dur', 0.4 if typ == 'fade' else 0.5)
    g = gpu()
    if g is not None:
        layers = frame_layers(c, t, overlays, sub, cache, sub_style)  # Pillow drawing stays on the caller's thread
        goff = GRAIN_OFFSETS[int((t + toff) / 0.05) % 3] if fx.get('grain') else None
        if not effects and (not in_tr or typ in ('fade', 'dip')):
            def draw():  # runs on the compositor's GL thread
                A = g.source(0, src(k), lt); B = None; mode, val = 0, 1.0
                if in_tr and typ == 'fade' and k > 0:
                    B = g.source(1, src(k - 1), t - vids[k - 1]['start']); mode, val = 1, lt / tr.get('dur', 0.4)
                elif in_tr and typ == 'dip':
                    mode, val = 2, lt / tr.get('dur', 0.5)
                return g.frame(A, B, mode, val, layers, goff)
        else:
            plan = FX.effect_plan(effects, t, fps, media or {}, toff)
            trans = None
            if in_tr and (typ in ('fade', 'dip') or typ in FX.TRANSITIONS):
                dur = tr.get('dur', 0.4 if typ == 'fade' else 0.5)
                trans = ({'fade': 'fade_legacy', 'dip': 'dip_legacy'}.get(typ, typ), min(1.0, max(0.0, lt / dur)))
            need_prev = trans is not None and k > 0 and typ != 'dip'

            def draw():
                A = g.source(0, src(k), lt)
                B = g.source(1, src(k - 1), t - vids[k - 1]['start']) if need_prev else None
                return g.frame_multi(A, B, trans, plan, layers, goff)
        try:
            b = g.call(draw)
            return b if as_bytes else np.frombuffer(b, np.uint8).reshape(H, W, 3)
        except Exception as e:  # noqa: BLE001 - a GPU failure must not lose the frame: draw it on the CPU
            print(f'GPU frame {t:.3f} failed, CPU instead: {e}', flush=True)
    cur = transition_in(src(k).frame(lt), c, t, lambda: src(k - 1).frame(t - vids[k - 1]['start']), k)
    a = composite(cur, c, t, overlays, sub, fx, cache, effects, media, fps, sub_style, toff)
    return a.tobytes() if as_bytes else a


def picture(d, tl, out):
    global LANG
    LANG = tl.get('language') or 'en'
    fps = tl['fps']; n = int(math.ceil(tl['duration'] * fps))
    vids = sorted([c for tr in tl['tracks'] if tr['id'] == 'video' for c in tr['clips']], key=lambda c: c['start'])
    overlays = sorted([c for tr in tl['tracks'] if tr['id'] == 'overlay' for c in tr['clips'] if 'start' in c],
                      key=lambda o: o.get('type') in ('date_tag', 'lower_third', 'callout'))  # cards under the small overlays
    clay = {}; toff = float(tl.get('t_offset', 0.0))  # film time of this render's first frame (range renders)
    subs = subtitles(d, tl) if (tl.get('fx') or {}).get('subtitles') else []
    si = 0
    ff = subprocess.Popen(['ffmpeg', '-v', 'error', '-y', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{W}x{H}', '-r', str(fps),
                           '-i', '-', *VIDEO_ENC, '-pix_fmt', 'yuv420p', *(ENC_THREADS if VIDEO_ENC is X264 else []),
                           '-movflags', '+faststart', str(out)], stdin=subprocess.PIPE)
    live = {}
    effects = sorted(FX.effect_clips(tl), key=lambda e: e['start']); media = {}

    def src(k):
        c = vids[k]
        if k not in live:
            if c.get('kind') == 'card' or not c.get('src'):
                live[k] = Blank()
            elif c.get('kind') == 'video' or str(c['src']).lower().endswith(('.mp4', '.webm', '.mov', '.mkv')):
                live[k] = Video(d / c['src'], c, fps)
            else:
                live[k] = Photo(d / c['src'], c, k)
        return live[k]

    k = 0; last = None
    for i in range(n):
        t = i / fps
        while k + 1 < len(vids) and t >= vids[k + 1]['start']:
            k += 1
        for j in [j for j in live if j < k - 1]:
            live.pop(j).close()
        c = vids[k]
        if FRAME_STEP > 1 and i % FRAME_STEP and last is not None and not media and not isinstance(src(k), Video):
            ff.stdin.write(last)  # fast preview: draw every FRAME_STEP-th frame and repeat it (sequential sources excluded)
            continue
        act = [e for e in effects if e['start'] <= t < e['end']]
        for e in act:
            if e['type'] == 'media_overlay' and e['id'] not in media and (e.get('params') or {}).get('src'):
                media[e['id']] = FX.MediaLayer(d / e['params']['src'], e['params'], fps, sequential=True)
        for eid in [x for x in media if not any(e['id'] == x for e in act)]:
            media.pop(eid).close()
        while si < len(subs) and subs[si][1] <= t:
            si += 1
        sub = subs[si][2] if si < len(subs) and subs[si][0] <= t else None
        last = render_frame(t, vids, k, src, overlays, sub, tl.get('fx') or {}, clay, act, media, fps, tl.get('subtitle_style'), toff=toff)
        ff.stdin.write(last)
        if i % (fps * 10) == 0:
            print(f'  frame {i}/{n}', flush=True)
    for v in list(live.values()) + list(media.values()):
        v.close()
    ff.stdin.close(); ff.wait()
    if ff.returncode:
        sys.exit('ffmpeg picture encode failed')


# ------------------------------------------------------------------ audio
def _has_audio(p):
    out = subprocess.run(['ffprobe', '-v', 'error', '-select_streams', 'a', '-show_entries', 'stream=index', '-of', 'csv=p=0', str(p)],
                         capture_output=True, text=True).stdout
    return bool(out.strip())


_probe = {}


def mix_graph(d, tl, t0=0.0, t1=None, only=None):
    """(ffmpeg inputs, filter lines, bed+hit count) of the voice-led premix. With t0/t1 only that window is mixed
    (studio monitor and range previews); `only` limits it to a set of track ids (studio mute/solo). Clips with
    "mute": true are left out. The default arguments give exactly the full-film graph."""
    win = t1 is not None
    total = (t1 - t0) if win else tl['duration']
    voice = ['-ss', f'{t0:.3f}', '-t', f'{total:.3f}'] if win else []
    ins, beds, hits = [*voice, '-i', str(d / 'voice' / 'voice.wav')], [], []  # beds are ducked under the voice; hits (sfx) are not
    k = 1
    for tr in tl['tracks']:
        if tr['id'] not in ('video', 'original', 'music', 'sfx') or (only is not None and tr['id'] not in only):
            continue
        for c in tr['clips']:
            if not c.get('src') or c.get('mute') or (tr['id'] == 'video' and not (c.get('kind') == 'video' and c.get('original_audio'))):
                continue
            dur = max(0.05, c.get('end', c['start'] + 2) - c['start'])
            if win and (c['start'] >= t1 or c['start'] + dur <= t0):
                continue
            p = (d / c['src']).resolve()
            if p not in _probe:
                _probe[p] = p.exists() and _has_audio(p)
            if not _probe[p]:
                continue
            gain = c.get('gain_db', {'video': -20, 'original': -18, 'music': -16, 'sfx': -9}[tr['id']])
            ins += (['-stream_loop', '-1'] if c.get('loop') else []) + ['-i', str(p)]  # loop: short ambience under a long span
            fi, fo = c.get('fade_in', 0.15 if tr['id'] != 'sfx' else 0.005), c.get('fade_out', 0.3)
            skip = max(0.0, t0 - c['start']) if win else 0.0  # window starts inside the clip
            ms = int(max(0.0, c['start'] - t0) * 1000) if win else int(c['start'] * 1000)
            src_in = c.get('in', 0) if tr['id'] != 'video' else 0
            fade_in = f'afade=t=in:d={fi},' if not win or skip < fi else ''
            # music beds often build from near-silence (measured: -31 LUFS intro, -12 at the climax): even them out
            level = 'dynaudnorm=f=400:g=31:p=0.9:m=8,loudnorm=I=-16:TP=-2:LRA=7,' if tr['id'] == 'music' else ''
            if win:
                src_in = round(src_in + skip, 3)
            (hits if tr['id'] == 'sfx' else beds).append(
                (k, f'[{k}:a]atrim=start={src_in}:duration={dur - skip:.3f},asetpts=PTS-STARTPTS,{level}'
                    f'{fade_in}afade=t=out:st={max(0, dur - fo - skip):.3f}:d={fo},volume={gain}dB,'
                    f'aresample=48000,aformat=channel_layouts=stereo,adelay={ms}|{ms}[b{k}]'))
            k += 1
    fc = ['[0:a]aresample=48000,aformat=channel_layouts=stereo,apad,atrim=duration=%.3f,asplit=2[v][vsc]' % total]
    if only is not None and 'voice' not in only:  # studio monitor: voice muted but still ducking the beds
        fc = [fc[0].replace('[v][vsc]', '[v0][vsc]'), '[v0]volume=0[v]']
    fc += [f for _, f in beds + hits]
    mixin = '[v]'
    if beds:
        fc.append(''.join(f'[b{j}]' for j, _ in beds) + f'amix=inputs={len(beds)}:normalize=0:duration=longest,apad,atrim=duration={total:.3f}[bed]')
        # gentle ducking (about -6 dB under speech) so the score stays audible and swells back in the pauses
        fc.append('[bed][vsc]sidechaincompress=threshold=0.06:ratio=3:attack=30:release=600:knee=4:makeup=1[duck]')
        mixin += '[duck]'
    else:
        fc.append('[vsc]anullsink')
    mixin += ''.join(f'[b{j}]' for j, _ in hits)
    n_in = 1 + bool(beds) + len(hits)
    if n_in > 1:
        # card hits can stack above the voice peaks: limit them so the loudnorm pass below stays linear
        fc.append(f'{mixin}amix=inputs={n_in}:normalize=0:duration=first,alimiter=limit=0.89:attack=2:release=80:level=disabled[pre]')
    else:
        fc.append('[v]anull[pre]')
    return ins, fc, len(beds) + len(hits)


def premix(d, tl, pre, t0=0.0, t1=None, only=None, codec='pcm_s24le'):
    """Render the (window of the) premix to `pre`; its graph goes next to it. Returns the bed+hit count."""
    ins, fc, n = mix_graph(d, tl, t0, t1, only)
    graph = pre.with_name(pre.stem.replace('premix', 'mix') + '_graph.txt')  # ~100 cues overflow the Windows 32k command line inline
    graph.write_text(';\n'.join(fc), encoding='utf-8')
    subprocess.run(['ffmpeg', '-v', 'error', '-y', *ins, '-filter_complex_script', str(graph), '-map', '[pre]', '-ar', '48000',
                    '-c:a', codec, str(pre)], check=True)
    return n


def mix(d, tl, out, target=-14.0, tp=-1.5):
    """Voice-led mix: beds (verified field sound, music, sfx) are sidechain-ducked under the voice, then two-pass
    loudnorm. Video clip audio is muted unless the clip says original_audio: true (uploads often carry music)."""
    pre = out.with_name('premix.wav')
    n = premix(d, tl, pre)
    meas = subprocess.run(['ffmpeg', '-hide_banner', '-i', str(pre), '-af', f'loudnorm=I={target}:TP={tp}:LRA=11:print_format=json',
                           '-f', 'null', '-'], capture_output=True, text=True).stderr
    m = json.loads(meas[meas.rindex('{'):meas.rindex('}') + 1])
    ln = (f'loudnorm=I={target}:TP={tp}:LRA=11:measured_I={m["input_i"]}:measured_TP={m["input_tp"]}:'
          f'measured_LRA={m["input_lra"]}:measured_thresh={m["input_thresh"]}:offset={m["target_offset"]}:linear=true')
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', str(pre), '-af', f'{ln},aresample=48000', '-ar', '48000',
                    '-c:a', 'pcm_s24le', str(out)], check=True)
    return n


def mux(picture_path, audio_path, out):
    out.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', str(picture_path), '-i', str(audio_path), '-map', '0:v', '-map', '1:a',
                    '-c:v', 'copy', '-c:a', 'aac', '-b:a', '256k', '-ar', '48000', '-shortest', '-movflags', '+faststart', str(out)],
                   check=True)
