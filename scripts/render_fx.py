"""Picture effects for render.py (and the studio preview): per-clip colour, custom Ken Burns, transitions, effect layers.

Timeline fields (docs/SCHEMA.md):
- video clip "color": {exposure, brightness, contrast, saturation, temperature, tint, gamma, fade, sepia}  (0/1 = neutral)
- video clip "motion": {"type": "push"|"pull", "dx"} (classic) or
    {"type": "custom", "from": {"zoom": 1.0, "x": 0.5, "y": 0.5}, "to": {...}, "ease": "smooth"|"linear"|"in"|"out", "shake": 0..1}
    or {"type": "none"}; x/y = centre of the view as a fraction of the image, zoom >= 1.
- video clip "transition_in": {"type": fade|dip|dip_white|wipe_left|wipe_right|wipe_up|slide_left|slide_right|zoom|blur, "dur"}
- tracks of kind "fx": effect clips {"type", "start", "end", "params", "opacity", "fade_in", "fade_out"} applied, in track
  order, to the picture under the text overlays. Types: see EFFECTS.
"""
import json, math, subprocess
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

W, H = 1920, 1080

# ------------------------------------------------------------------ colour
COLOR_DEFAULT = {'exposure': 0.0, 'brightness': 0.0, 'contrast': 1.0, 'saturation': 1.0, 'temperature': 0.0, 'tint': 0.0,
                 'gamma': 1.0, 'shadows': 0.0, 'highlights': 0.0, 'fade': 0.0, 'sepia': 0.0}


def color_active(c):
    return bool(c) and any(abs(float(c.get(k, v)) - v) > 1e-6 for k, v in COLOR_DEFAULT.items())


_cm = {}


def _color_ops(p):
    """(3x3 matrix, 1021-entry LUT) for colour params p: the linear part (exposure, temperature/tint, saturation, sepia)
    is one matrix product, the tone part (contrast, brightness, shadows, highlights, gamma, fade) one lookup."""
    key = json.dumps(p, sort_keys=True)
    if key not in _cm:
        w = np.array([0.299, 0.587, 0.114], np.float32)
        m = np.eye(3, dtype=np.float32) * (2 ** p['exposure'])
        if p['temperature'] or p['tint']:
            m = m @ np.diag([1 + 0.12 * p['temperature'] + 0.04 * p['tint'], 1 - 0.08 * p['tint'], 1 - 0.12 * p['temperature'] + 0.04 * p['tint']]).astype(np.float32)
        lum = np.outer(w, np.ones(3, np.float32))  # f @ lum = luminance in every channel
        m = m @ (p['saturation'] * np.eye(3, dtype=np.float32) + (1 - p['saturation']) * lum)
        if p['sepia']:
            m = m @ ((1 - p['sepia']) * np.eye(3, dtype=np.float32) + p['sepia'] * np.outer(w, np.array([1.07, 0.94, 0.74], np.float32)))
        x = np.arange(1021, dtype=np.float32) / 255  # input 0..4 after the matrix
        x = (x - 0.5) * p['contrast'] + 0.5 + p['brightness'] * 0.5
        x = np.clip(x, 0, 1)
        if p['shadows']:  # lift (+) or crush (-) the darks only
            x = x + p['shadows'] * 0.3 * (1 - x) ** 3
        if p['highlights']:  # recover (-) or push (+) the brights only
            x = x + p['highlights'] * 0.3 * x ** 3
        x = np.clip(x, 0, 1)
        if p['gamma'] != 1:
            x = x ** (1 / max(0.05, p['gamma']))
        if p['fade']:
            x = p['fade'] * 0.22 + x * (1 - p['fade'] * 0.3)  # lifted, matte blacks
        _cm[key] = (m.astype(np.float32), np.round(np.clip(x, 0, 1) * 255).astype(np.uint8))
        if len(_cm) > 64:
            _cm.pop(next(iter(_cm)))
    return _cm[key]


def apply_color(a, c, amount=1.0):
    """a: HxWx3 uint8; c: colour params. amount blends toward neutral (effect fades)."""
    if not color_active(c):
        return a
    p = {k: COLOR_DEFAULT[k] + (float(c.get(k, v)) - COLOR_DEFAULT[k]) * amount for k, v in COLOR_DEFAULT.items()}
    m, lut = _color_ops(p)
    g = a.reshape(-1, 3).astype(np.float32) @ m
    idx = np.clip(g + 0.5, 0, 1020).astype(np.uint16)
    return lut[idx].reshape(a.shape)


# ------------------------------------------------------------------ motion
def ease_fn(name):
    return {'linear': lambda p: p, 'in': lambda p: p * p, 'out': lambda p: 1 - (1 - p) ** 2}.get(name, lambda p: p * p * (3 - 2 * p))


def custom_box(m, p, bw, bh, t=0.0):
    """Crop box (x0, y0, x1, y1) in a bw x bh image for motion m at progress p (0..1)."""
    a, b = m.get('from') or {}, m.get('to') or {}
    e = ease_fn(m.get('ease'))(min(1.0, max(0.0, p)))
    lerp = lambda k, d: a.get(k, d) + (b.get(k, a.get(k, d)) - a.get(k, d)) * e
    z = max(1.0, lerp('zoom', 1.0)); cx = lerp('x', 0.5); cy = lerp('y', 0.5)
    ww, wh = bw / z, bh / z
    if m.get('shake'):
        s = float(m['shake']) * 0.012
        cx += s * (math.sin(t * 13.1) + 0.5 * math.sin(t * 29.7)); cy += s * (math.cos(t * 11.3) + 0.5 * math.sin(t * 23.9))
    x = min(max(0.0, cx * bw - ww / 2), bw - ww); y = min(max(0.0, cy * bh - wh / 2), bh - wh)
    return x, y, x + ww, y + wh


MOTION_PRESETS = {  # names shown in the studio (Chuyển động)
    'push': {'type': 'custom', 'from': {'zoom': 1.0}, 'to': {'zoom': 1.08}},
    'pull': {'type': 'custom', 'from': {'zoom': 1.08}, 'to': {'zoom': 1.0}},
    'pan_left': {'type': 'custom', 'from': {'zoom': 1.1, 'x': 0.56}, 'to': {'zoom': 1.1, 'x': 0.44}},
    'pan_right': {'type': 'custom', 'from': {'zoom': 1.1, 'x': 0.44}, 'to': {'zoom': 1.1, 'x': 0.56}},
    'pan_up': {'type': 'custom', 'from': {'zoom': 1.1, 'y': 0.56}, 'to': {'zoom': 1.1, 'y': 0.44}},
    'pan_down': {'type': 'custom', 'from': {'zoom': 1.1, 'y': 0.44}, 'to': {'zoom': 1.1, 'y': 0.56}},
    'push_left': {'type': 'custom', 'from': {'zoom': 1.0, 'x': 0.5}, 'to': {'zoom': 1.15, 'x': 0.4}},
    'push_right': {'type': 'custom', 'from': {'zoom': 1.0, 'x': 0.5}, 'to': {'zoom': 1.15, 'x': 0.6}},
    'none': {'type': 'none'},
    'handheld': {'type': 'custom', 'from': {'zoom': 1.06}, 'to': {'zoom': 1.08}, 'shake': 0.5},
}


# ------------------------------------------------------------------ transitions
TRANSITIONS = ('fade', 'dip', 'dip_white', 'wipe_left', 'wipe_right', 'wipe_up', 'wipe_down', 'slide_left', 'slide_right',
               'slide_up', 'slide_down', 'zoom', 'blur', 'circle_open', 'circle_close', 'radial', 'pixelize')
_grid = None


def _polar():
    global _grid
    if _grid is None:
        y, x = np.mgrid[0:H, 0:W].astype(np.float32)
        r = np.sqrt((x - W / 2) ** 2 + (y - H / 2) ** 2) / math.hypot(W / 2, H / 2)
        a = (np.arctan2(x - W / 2, -(y - H / 2)) / (2 * math.pi)) % 1.0
        _grid = (r, a)
    return _grid


def transition(prev, cur, kind, a):
    """Blend prev -> cur at progress a (0..1). prev may be None (first clip): dips still work."""
    a = min(1.0, max(0.0, a)); e = a * a * (3 - 2 * a)
    if kind == 'dip':
        return (cur * e).astype(np.uint8) if prev is None else (prev * max(0, 1 - 2 * e) if e < 0.5 else cur * (2 * e - 1)).astype(np.uint8)
    if kind == 'dip_white':
        w = 1 - abs(2 * e - 1); src = cur if (prev is None or e >= 0.5) else prev
        return (src * (1 - w) + 255 * w).astype(np.uint8)
    if prev is None:
        return cur
    if kind in ('wipe_left', 'wipe_right', 'wipe_up', 'wipe_down'):
        out = prev.copy()
        if kind == 'wipe_left':
            x = int(W * e)
            if x:
                out[:, W - x:] = cur[:, W - x:]
        elif kind == 'wipe_right':
            x = int(W * e); out[:, :x] = cur[:, :x]
        elif kind == 'wipe_up':
            y = int(H * e)
            if y:
                out[H - y:] = cur[H - y:]
        else:
            y = int(H * e); out[:y] = cur[:y]
        return out
    if kind in ('slide_left', 'slide_right', 'slide_up', 'slide_down'):
        out = np.empty_like(cur)
        if kind in ('slide_left', 'slide_right'):
            x = int(W * e)
            if kind == 'slide_left':
                out[:, :W - x] = prev[:, x:]; out[:, W - x:] = cur[:, :x]
            else:
                out[:, x:] = prev[:, :W - x]; out[:, :x] = cur[:, W - x:]
        else:
            y = int(H * e)
            if kind == 'slide_up':
                out[:H - y] = prev[y:]; out[H - y:] = cur[:y]
            else:
                out[y:] = prev[:H - y]; out[:y] = cur[H - y:]
        return out
    if kind in ('circle_open', 'circle_close', 'radial'):
        r, ang = _polar(); soft = 0.03
        if kind == 'circle_open':
            m = np.clip((e * (1 + soft) - r) / soft, 0, 1)
        elif kind == 'circle_close':
            m = np.clip((r - (1 - e) * (1 + soft) + soft) / soft, 0, 1)
        else:
            m = np.clip((e * (1 + soft) - ang) / soft, 0, 1)
        m = m[..., None]
        return (prev * (1 - m) + cur * m).astype(np.uint8)
    if kind == 'pixelize':
        k = 1 - abs(2 * e - 1); src = prev if e < 0.5 else cur
        bs = max(1, int(round(1 + k * 60)))
        if bs <= 1:
            return src
        small = Image.fromarray(src).resize((max(1, W // bs), max(1, H // bs)), Image.BILINEAR)
        return np.asarray(small.resize((W, H), Image.NEAREST))
    if kind == 'zoom':
        z = 1 + 0.25 * e; im = Image.fromarray(prev); ww, wh = W / z, H / z
        p = np.asarray(im.resize((W, H), Image.BILINEAR, box=((W - ww) / 2, (H - wh) / 2, (W + ww) / 2, (H + wh) / 2)))
        return (p * (1 - e) + cur * e).astype(np.uint8)
    if kind == 'blur':
        r = 18 * (1 - abs(2 * e - 1)); src = prev if e < 0.5 else cur
        return np.asarray(Image.fromarray(src).filter(ImageFilter.GaussianBlur(r))) if r > 0.5 else src
    return (prev * (1 - e) + cur * e).astype(np.uint8)  # fade


# ------------------------------------------------------------------ effect layers
EFFECTS = {  # type -> default params (the studio builds its sliders from these + RANGES)
    'old_film': {'grain': 0.5, 'scratches': 0.4, 'dust': 0.4, 'flicker': 0.3, 'jitter': 0.2, 'vignette': 0.5, 'sepia': 0.4},
    'grain': {'amount': 0.4, 'size': 1.5},
    'dust_scratches': {'dust': 0.6, 'scratches': 0.6},
    'flicker': {'amount': 0.4},
    'jitter': {'amount': 0.4},
    'vignette': {'amount': 0.6, 'size': 0.5},
    'light_leak': {'amount': 0.5, 'hue': 30.0, 'speed': 0.3},
    'blur': {'radius': 6.0},
    'letterbox': {'ratio': 2.35},
    'color': dict(COLOR_DEFAULT),
    'flash': {'amount': 0.8},
    'media_overlay': {'src': '', 'blend': 'screen', 'scale': 'cover', 'x': 0.5, 'y': 0.5, 'size': 1.0, 'speed': 1.0, 'loop': True},
}
RANGES = {'grain': (0, 1), 'scratches': (0, 1), 'dust': (0, 1), 'flicker': (0, 1), 'jitter': (0, 1), 'vignette': (0, 1), 'sepia': (0, 1),
          'amount': (0, 1), 'size': (0.05, 3), 'hue': (0, 360), 'speed': (0.05, 3), 'radius': (0, 40), 'ratio': (1.5, 3),
          'exposure': (-2, 2), 'brightness': (-1, 1), 'contrast': (0, 2), 'saturation': (0, 2), 'temperature': (-1, 1),
          'tint': (-1, 1), 'gamma': (0.3, 2.5), 'fade': (0, 1), 'x': (0, 1), 'y': (0, 1), 'shadows': (-1, 1), 'highlights': (-1, 1)}
BLENDS = ('normal', 'screen', 'multiply', 'overlay', 'add', 'lighten', 'darken', 'soft_light')

COLOR_PRESETS = {  # label -> colour params (studio Màu)
    'Gốc': {},
    'Tư liệu ấm': {'temperature': 0.35, 'contrast': 1.08, 'fade': 0.15},
    'Tư liệu lạnh': {'temperature': -0.35, 'contrast': 1.1, 'saturation': 0.8},
    'Đen trắng': {'saturation': 0.0, 'contrast': 1.12},
    'Sepia đậm': {'sepia': 0.85, 'contrast': 1.1, 'fade': 0.1},
    'Phim bạc màu': {'saturation': 0.55, 'fade': 0.45, 'contrast': 0.92, 'temperature': 0.15},
    'Tương phản mạnh': {'contrast': 1.35, 'brightness': -0.04},
    'Tối & nặng': {'exposure': -0.45, 'contrast': 1.2, 'saturation': 0.7},
    'Sáng lên': {'exposure': 0.35, 'gamma': 1.15},
    'Đêm xanh': {'temperature': -0.6, 'tint': 0.15, 'exposure': -0.35, 'saturation': 0.7},
}
EFFECT_PRESETS = [  # (label, type, params) shown as tiles in the studio (Hiệu ứng)
    ('Phim cũ nhẹ', 'old_film', {'grain': 0.35, 'scratches': 0.2, 'dust': 0.25, 'flicker': 0.15, 'jitter': 0.1, 'vignette': 0.35, 'sepia': 0.2}),
    ('Phim cũ nặng', 'old_film', {'grain': 0.75, 'scratches': 0.8, 'dust': 0.8, 'flicker': 0.6, 'jitter': 0.5, 'vignette': 0.7, 'sepia': 0.6}),
    ('Thời sự 1950', 'old_film', {'grain': 0.6, 'scratches': 0.5, 'dust': 0.6, 'flicker': 0.5, 'jitter': 0.35, 'vignette': 0.55, 'sepia': 0.0}),
    ('Hạt phim', 'grain', {'amount': 0.4, 'size': 1.5}),
    ('Bụi & xước', 'dust_scratches', {'dust': 0.6, 'scratches': 0.6}),
    ('Nháy sáng', 'flicker', {'amount': 0.4}),
    ('Rung khung', 'jitter', {'amount': 0.4}),
    ('Viền tối', 'vignette', {'amount': 0.6, 'size': 0.5}),
    ('Lóa sáng ấm', 'light_leak', {'amount': 0.5, 'hue': 30.0, 'speed': 0.3}),
    ('Làm mờ', 'blur', {'radius': 6.0}),
    ('Khung điện ảnh 2.35', 'letterbox', {'ratio': 2.35}),
    ('Chớp trắng', 'flash', {'amount': 0.8}),
    ('Chỉnh màu cả đoạn', 'color', {'saturation': 0.6, 'contrast': 1.1}),
    ('Lớp phủ media', 'media_overlay', {'src': '', 'blend': 'screen'}),
]

_noise = {}


def _noise_bank(size):
    """24 precomputed grain fields (float32 -1..1) at grain size `size` px, tiled per frame index."""
    key = round(size, 1)
    if key not in _noise:
        rng = np.random.default_rng(7); bank = []
        sw, sh = max(8, int(W / max(0.5, size))), max(8, int(H / max(0.5, size)))
        for _ in range(24):
            n = rng.normal(0, 1, (sh, sw)).astype(np.float32)
            im = Image.fromarray(np.clip(n * 40 + 128, 0, 255).astype(np.uint8)).resize((W, H), Image.BILINEAR)
            bank.append((np.asarray(im, np.float32) - 128) / 40)
        _noise[key] = bank
    return _noise[key]


_vigm = {}


def _vignette_mask(size):
    k = round(size, 2)
    if k not in _vigm:
        y, x = np.mgrid[0:H, 0:W].astype(np.float32)
        r = np.sqrt(((x - W / 2) / (W / 2)) ** 2 + ((y - H / 2) / (H / 2)) ** 2) / 1.414
        _vigm[k] = np.clip((r - (0.25 + 0.5 * size) * 0.7) / 0.6, 0, 1) ** 1.5
    return _vigm[k]


def _rng(seed):
    return np.random.default_rng(abs(int(seed)) % (2 ** 31))


def grain(f, amount, size, fi):
    n = _noise_bank(size)[fi % 24]
    return f + n[..., None] * (amount * 28)


def scratches_dust(f, scratches, dust, fi, seed):
    """Thin vertical scratches and dust specks/hairs, bright or dark, new every frame. Drawn at half size (soft edges)."""
    sl = scratch_layers(scratches, dust, fi, seed)
    if sl is None:
        return f
    lay, dark = sl
    a = np.asarray(lay.resize((W, H), Image.BILINEAR), np.float32)[..., None] * (0.7 / 255)
    b = np.asarray(dark.resize((W, H), Image.BILINEAR), np.float32)[..., None] * (0.85 / 255)
    return f * (1 - b - a) + 255 * a


def scratch_layers(scratches, dust, fi, seed):
    """(bright, dark) half-size L images of this frame's scratches and dust, or None. Shared by CPU and GPU."""
    r = _rng(seed * 7919 + fi); w2, h2 = W // 2, H // 2
    lay = Image.new('L', (w2, h2), 0); d = ImageDraw.Draw(lay); dark = Image.new('L', (w2, h2), 0); dd = ImageDraw.Draw(dark)
    n = 0
    for _ in range(int(r.poisson(3 * scratches))):
        x = r.uniform(0, w2); y0 = r.uniform(-h2, h2 * 0.5); y1 = y0 + r.uniform(h2 * 0.4, h2 * 1.6)
        (d if r.random() < 0.6 else dd).line((x, y0, x + r.uniform(-3, 3), y1), fill=int(r.uniform(90, 200)), width=1); n += 1
    for _ in range(int(r.poisson(12 * dust))):
        x, y = r.uniform(0, w2), r.uniform(0, h2); sz = r.uniform(0.5, 2.3)
        tgt = d if r.random() < 0.35 else dd
        if r.random() < 0.15:
            tgt.arc((x, y, x + sz * 4, y + sz * 3), r.uniform(0, 180), r.uniform(180, 360), fill=220, width=1)
        else:
            tgt.ellipse((x, y, x + sz, y + sz * r.uniform(0.6, 1.4)), fill=int(r.uniform(150, 255)))
        n += 1
    return (lay, dark) if n else None


def light_leak(f, amount, hue, speed, t):
    import colorsys
    rgb = np.array(colorsys.hsv_to_rgb((hue % 360) / 360, 0.75, 1.0), np.float32) * 255
    cx = W * (0.15 + 0.7 * (0.5 + 0.5 * math.sin(t * speed * 0.9))); cy = H * (0.2 + 0.3 * math.sin(t * speed * 0.6 + 1))
    y, x = np.ogrid[0:H, 0:W]
    g = np.exp(-(((x - cx) / (W * 0.45)) ** 2 + ((y - cy) / (H * 0.6)) ** 2)).astype(np.float32)
    g *= amount * (0.75 + 0.25 * math.sin(t * speed * 2.3))
    return f + (rgb - f * 0.3) * g[..., None] * 0.8


def _blend(base, top, mode):
    b, s = base / 255, top / 255
    if mode == 'screen':
        r = 1 - (1 - b) * (1 - s)
    elif mode == 'multiply':
        r = b * s
    elif mode == 'overlay':
        r = np.where(b < 0.5, 2 * b * s, 1 - 2 * (1 - b) * (1 - s))
    elif mode == 'soft_light':
        r = (1 - 2 * s) * b * b + 2 * s * b
    elif mode == 'add':
        r = b + s
    elif mode == 'lighten':
        r = np.maximum(b, s)
    elif mode == 'darken':
        r = np.minimum(b, s)
    else:
        r = s
    return np.clip(r, 0, 1) * 255


class MediaLayer:
    """An image or video used as an overlay effect (dust/grain/light-leak footage, a logo, a picture-in-picture).
    sequential=True (render loop) decodes frames in order; else each frame is grabbed at its time (studio preview)."""
    VIDEO = ('.mp4', '.webm', '.mov', '.mkv', '.gif', '.avi')

    def __init__(self, path, params, fps, sequential):
        self.path, self.p, self.fps, self.seq = Path(path), params, fps, sequential
        self.video = self.path.suffix.lower() in self.VIDEO
        self.size = self._target()
        self.proc = None; self.last = None; self.alpha = None
        if not self.video:
            im = Image.open(self.path).convert('RGBA')
            im = self._fit(im)
            a = np.asarray(im, np.float32); self.last = a[..., :3]; self.alpha = a[..., 3:4] / 255
        else:
            out = subprocess.run(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', str(self.path)],
                                 capture_output=True, text=True).stdout.strip()
            self.dur = float(out or 1) or 1

    def _target(self):
        s = float(self.p.get('size', 1.0))
        return max(2, int(W * s)) // 2 * 2, max(2, int(H * s)) // 2 * 2

    def _fit(self, im):
        tw, th = self.size
        if self.p.get('scale', 'cover') == 'contain':
            from PIL import ImageOps
            fg = ImageOps.contain(im, (tw, th)); bg = Image.new('RGBA', (tw, th), (0, 0, 0, 0))
            bg.paste(fg, ((tw - fg.width) // 2, (th - fg.height) // 2)); return bg
        if self.p.get('scale') == 'stretch':
            return im.resize((tw, th), Image.LANCZOS)
        from PIL import ImageOps
        return ImageOps.fit(im, (tw, th), Image.LANCZOS)

    def _vf(self):
        tw, th = self.size; sc = self.p.get('scale', 'cover')
        if sc == 'stretch':
            return f'scale={tw}:{th}'
        if sc == 'contain':
            return f'scale={tw}:{th}:force_original_aspect_ratio=decrease,pad={tw}:{th}:(ow-iw)/2:(oh-ih)/2'
        return f'scale={tw}:{th}:force_original_aspect_ratio=increase,crop={tw}:{th}'

    def frame(self, lt, as_float=True):
        """Advance to clip time lt; returns (float RGB, alpha or None). as_float=False skips the float copy (GPU path)."""
        if not self.video:
            return self.last, self.alpha
        tw, th = self.size; speed = float(self.p.get('speed', 1.0)) or 1.0
        if self.seq:
            if self.proc is None:
                loop = ['-stream_loop', '-1'] if self.p.get('loop', True) else []
                skip = float(self.p.get('_skip', 0)) * speed  # a range render that starts inside this effect
                if skip:
                    skip = skip % self.dur if self.p.get('loop', True) else min(skip, self.dur)
                self.proc = subprocess.Popen(['ffmpeg', '-v', 'error', *loop, '-ss', f'{skip:.3f}', '-i', str(self.path), '-an', '-vf',
                                              f'setpts=PTS/{speed},{self._vf()},fps={self.fps},format=rgb24', '-f', 'rawvideo', '-'],
                                             stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
            raw = self.proc.stdout.read(tw * th * 3)
            if len(raw) == tw * th * 3:
                self.raw = np.frombuffer(raw, np.uint8).reshape(th, tw, 3); self.last = None  # float copy made only if the CPU needs it
        else:
            st = (lt * speed) % self.dur if self.p.get('loop', True) else min(lt * speed, self.dur - 0.05)
            raw = subprocess.run(['ffmpeg', '-v', 'error', '-ss', f'{st:.3f}', '-i', str(self.path), '-an', '-frames:v', '1', '-vf',
                                  f'{self._vf()},format=rgb24', '-f', 'rawvideo', '-'], capture_output=True).stdout
            if len(raw) == tw * th * 3:
                self.raw = np.frombuffer(raw, np.uint8).reshape(th, tw, 3); self.last = None
        if getattr(self, 'raw', None) is None:
            self.raw = np.zeros((th, tw, 3), np.uint8)
        if as_float and self.last is None:
            self.last = self.raw.astype(np.float32)
        return self.last, None

    def apply(self, f, lt, k):
        top, alpha = self.frame(lt)
        tw, th = self.size
        x0 = int(float(self.p.get('x', 0.5)) * W - tw / 2); y0 = int(float(self.p.get('y', 0.5)) * H - th / 2)
        xs, ys = max(0, x0), max(0, y0); xe, ye = min(W, x0 + tw), min(H, y0 + th)
        if xe <= xs or ye <= ys:
            return f
        sub = f[ys:ye, xs:xe]; t = top[ys - y0:ye - y0, xs - x0:xe - x0]
        mixed = _blend(sub, t, self.p.get('blend', 'screen'))
        a = k if alpha is None else alpha[ys - y0:ye - y0, xs - x0:xe - x0] * k
        f = f.copy(); f[ys:ye, xs:xe] = sub * (1 - a) + mixed * a
        return f

    def rgba_u8(self):
        """The current frame as uint8 for the GPU: images are converted once, video frames are the decoder's bytes."""
        if not self.video:
            if getattr(self, '_u8', None) is None:
                self._u8 = np.concatenate([np.clip(self.last, 0, 255).astype(np.uint8), np.clip(self.alpha * 255 + 0.5, 0, 255).astype(np.uint8)], -1)
            return self._u8
        return self.raw

    def close(self):
        if self.proc:
            self.proc.kill(); self.proc.stdout.close(); self.proc.wait(); self.proc = None


def strength(e, t):
    """Opacity of effect clip e at film time t, with its fade in/out."""
    lt, dur = t - e['start'], e['end'] - e['start']
    k = float(e.get('opacity', 1.0))
    fi, fo = float(e.get('fade_in', 0)), float(e.get('fade_out', 0))
    if fi > 0:
        k *= min(1.0, max(0.0, lt / fi))
    if fo > 0:
        k *= min(1.0, max(0.0, (dur - lt) / fo))
    return k


def apply_effects(cur, effects, t, fps, media, toff=0.0):
    """cur: graded uint8 frame; effects: active effect clips in order; media: dict id -> MediaLayer (caller-owned).
    toff: film time of t = 0 (a range render): random draws and animation follow film time, so they do not depend on how
    a render is cut into parts."""
    if not effects:
        return cur
    f = cur.astype(np.float32); fi = int(round((t + toff) * fps))
    for e in effects:
        k = strength(e, t)
        if k <= 0.001:
            continue
        p = dict(EFFECTS.get(e['type'], {})); p.update(e.get('params') or {})
        typ = e['type']; seed = sum(map(ord, e.get('id', 'fx')))
        before = f
        if typ == 'old_film':
            if p['jitter'] > 0:
                r = _rng(seed + fi * 31); dy = int(round(r.normal(0, 2.2) * p['jitter'])); dx = int(round(r.normal(0, 1.2) * p['jitter']))
                f = np.roll(f, (dy, dx), (0, 1))
            if p['sepia'] > 0:
                f = apply_color(np.clip(f, 0, 255).astype(np.uint8), {'sepia': p['sepia'], 'saturation': 1 - 0.6 * p['sepia']}).astype(np.float32)
            if p['flicker'] > 0:
                f = f * (1 + (_rng(seed + fi).random() - 0.5) * 0.16 * p['flicker'])
            if p['grain'] > 0:
                f = grain(f, p['grain'], 1.6, fi + seed)
            if p['scratches'] > 0 or p['dust'] > 0:
                f = scratches_dust(f, p['scratches'], p['dust'], fi, seed)
            if p['vignette'] > 0:
                f = f * (1 - _vignette_mask(0.5)[..., None] * 0.85 * p['vignette'])
        elif typ == 'grain':
            f = grain(f, p['amount'], p['size'], fi + seed)
        elif typ == 'dust_scratches':
            f = scratches_dust(f, p['scratches'], p['dust'], fi, seed)
        elif typ == 'flicker':
            f = f * (1 + (_rng(seed + fi).random() - 0.5) * 0.25 * p['amount'])
        elif typ == 'jitter':
            r = _rng(seed + fi * 31); f = np.roll(f, (int(round(r.normal(0, 3) * p['amount'])), int(round(r.normal(0, 2) * p['amount']))), (0, 1))
        elif typ == 'vignette':
            f = f * (1 - _vignette_mask(p['size'])[..., None] * p['amount'])
        elif typ == 'light_leak':
            f = light_leak(f, p['amount'], p['hue'], p['speed'], t + toff)
        elif typ == 'blur':
            if p['radius'] > 0.3:
                f = np.asarray(Image.fromarray(np.clip(f, 0, 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(p['radius'])), np.float32)
        elif typ == 'letterbox':
            bh = int(max(0, (H - W / max(1.0, p['ratio'])) / 2))
            if bh:
                f = f.copy(); f[:bh] = 0; f[H - bh:] = 0
        elif typ == 'color':
            f = apply_color(np.clip(f, 0, 255).astype(np.uint8), p).astype(np.float32)
        elif typ == 'flash':
            f = f + (255 - f) * p['amount']
        elif typ == 'media_overlay':
            if p.get('src') and e['id'] in media:
                f = media[e['id']].apply(f, t - e['start'], 1.0)
        if k < 0.999 and typ not in ('media_overlay',):
            f = before * (1 - k) + f * k
        elif typ == 'media_overlay' and k < 0.999:
            f = before * (1 - k) + f * k
    return np.clip(f, 0, 255).astype(np.uint8)


def effect_plan(effects, t, fps, media, toff=0.0):
    """What the GPU needs to draw the active effects at t: the same parameters and random draws as apply_effects
    (jitter offsets, flicker factor, grain field, scratch/dust images, colour matrix + LUT, overlay frame)."""
    fi = int(round((t + toff) * fps)); plan = []; ta = t + toff
    for e in effects:
        k = strength(e, t)
        if k <= 0.001:
            continue
        p = dict(EFFECTS.get(e['type'], {})); p.update(e.get('params') or {})
        typ = e['type']; seed = sum(map(ord, e.get('id', 'fx'))); s = {'type': typ, 'k': k, 'p': p}
        if typ == 'old_film':
            if p['jitter'] > 0:
                r = _rng(seed + fi * 31); s['dy'] = int(round(r.normal(0, 2.2) * p['jitter'])); s['dx'] = int(round(r.normal(0, 1.2) * p['jitter']))
            if p['sepia'] > 0:
                s['color'] = _color_ops({k2: COLOR_DEFAULT[k2] for k2 in COLOR_DEFAULT} | {'sepia': p['sepia'], 'saturation': 1 - 0.6 * p['sepia']})
            if p['flicker'] > 0:
                s['flicker'] = 1 + (_rng(seed + fi).random() - 0.5) * 0.16 * p['flicker']
            if p['grain'] > 0:
                s['grain'] = (1.6, (fi + seed) % 24, p['grain'])
            if p['scratches'] > 0 or p['dust'] > 0:
                s['scratch'] = scratch_layers(p['scratches'], p['dust'], fi, seed)
        elif typ == 'grain':
            s['grain'] = (p['size'], (fi + seed) % 24, p['amount'])
        elif typ == 'dust_scratches':
            s['scratch'] = scratch_layers(p['scratches'], p['dust'], fi, seed)
        elif typ == 'flicker':
            s['flicker'] = 1 + (_rng(seed + fi).random() - 0.5) * 0.25 * p['amount']
        elif typ == 'jitter':
            r = _rng(seed + fi * 31); s['dy'] = int(round(r.normal(0, 3) * p['amount'])); s['dx'] = int(round(r.normal(0, 2) * p['amount']))
        elif typ == 'light_leak':
            import colorsys
            s['rgb'] = tuple(np.array(colorsys.hsv_to_rgb((p['hue'] % 360) / 360, 0.75, 1.0)) * 255)
            s['cx'] = W * (0.15 + 0.7 * (0.5 + 0.5 * math.sin(ta * p['speed'] * 0.9))); s['cy'] = H * (0.2 + 0.3 * math.sin(ta * p['speed'] * 0.6 + 1))
            s['amp'] = p['amount'] * (0.75 + 0.25 * math.sin(ta * p['speed'] * 2.3))
        elif typ == 'letterbox':
            s['bh'] = int(max(0, (H - W / max(1.0, p['ratio'])) / 2))
        elif typ == 'color':
            cp = {k2: COLOR_DEFAULT[k2] + (float(p.get(k2, v)) - COLOR_DEFAULT[k2]) for k2, v in COLOR_DEFAULT.items()}
            if not color_active(p):
                continue
            s['color'] = _color_ops(cp)
        elif typ == 'media_overlay':
            ml = media.get(e['id']) if p.get('src') else None
            if ml is None:
                continue
            ml.frame(t - e['start'], as_float=False); tw, th = ml.size
            s['rgba'] = ml.rgba_u8()  # HxWx3 (opaque video frame) or HxWx4 (image with alpha), uint8
            s['rect'] = (int(float(p.get('x', 0.5)) * W - tw / 2), int(float(p.get('y', 0.5)) * H - th / 2), tw, th)
        plan.append(s)
    return plan


def noise_field(size, idx):
    """One of the 24 precomputed grain fields (float32 HxW, about -3..3)."""
    return _noise_bank(size)[idx]


def effect_clips(tl):
    return [c for tr in tl['tracks'] if tr.get('kind') == 'fx' and not tr.get('hidden') for c in tr['clips'] if 'start' in c]


# ------------------------------------------------------------------ free text overlay + subtitle style
TEXT_DEFAULT = {'text': 'Chữ', 'x': 0.5, 'y': 0.5, 'size': 72, 'font': 'head', 'color': '#EDE7DC', 'align': 'center',
                'stroke': 0, 'stroke_color': '#000000', 'shadow': 0.6, 'box': 0.0, 'box_color': '#100E0C', 'anim': 'fade',
                'upper': False, 'line_gap': 1.15}
SUB_DEFAULT = {'size': 46, 'y': None, 'color': '#EDE7DC', 'stroke': 3, 'stroke_color': '#0A0908', 'shadow': 1.0, 'upper': False,
               'box': 0.0, 'box_color': '#0A0908', 'box_pad': 18, 'box_radius': 0, 'font': 'body'}  # y None = 128 px above the bottom


def hex_rgb(h, default=(237, 231, 220)):
    try:
        h = h.lstrip('#'); return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))
    except (ValueError, AttributeError):
        return default


def draw_text(lay, pr, lt, dur, font):
    """Generic text overlay (studio 'Chữ'). font: callable(kind, size)."""
    p = dict(TEXT_DEFAULT); p.update(pr or {})
    d = ImageDraw.Draw(lay); f = font(p['font'], int(p['size']))
    out = min(1.0, max(0.0, (dur - lt) / 0.35)); anim = p['anim']
    a = (min(1.0, max(0.0, lt / 0.4)) if anim in ('fade', 'slide_up', 'slide_left', 'pop') else 1.0) * out
    if a <= 0:
        return
    text = str(p['text']).upper() if p['upper'] else str(p['text'])
    if anim == 'typewriter':
        text = text[:int(len(text) * min(1.0, lt / max(0.3, min(2.5, dur * 0.5))))]
    lines = text.split('\n'); lh = int(p['size'] * p['line_gap'])
    ws = [d.textlength(l, font=f) for l in lines]; bw = max(ws or [0]); bh = lh * len(lines)
    cx, cy = p['x'] * W, p['y'] * H
    dy = (1 - min(1.0, lt / 0.4)) * 30 if anim == 'slide_up' else 0
    dx = (1 - min(1.0, lt / 0.4)) * 60 if anim == 'slide_left' else 0
    x0 = cx - bw / 2 if p['align'] == 'center' else cx if p['align'] == 'left' else cx - bw
    y0 = cy - bh / 2 + dy
    if p['box'] > 0:
        pad = p['size'] * 0.35
        d.rectangle((x0 - pad + dx, y0 - pad * 0.6, x0 + bw + pad + dx, y0 + bh + pad * 0.4), fill=hex_rgb(p['box_color']) + (int(255 * p['box'] * a),))
    col = hex_rgb(p['color'])
    for i, l in enumerate(lines):
        lx = (cx - ws[i] / 2 if p['align'] == 'center' else cx if p['align'] == 'left' else cx - ws[i]) + dx; ly = y0 + i * lh
        if p['shadow'] > 0:
            d.text((lx + 3, ly + 3), l, font=f, fill=(0, 0, 0, int(200 * p['shadow'] * a)))
        d.text((lx, ly), l, font=f, fill=col + (int(255 * a),), stroke_width=int(p['stroke']),
               stroke_fill=hex_rgb(p['stroke_color'], (0, 0, 0)) + (int(235 * a),))
