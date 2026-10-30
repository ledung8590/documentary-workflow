"""GPU frame compositor (OpenGL 3.3 via moderngl): the per-pixel work of render.composite on the graphics card.

Same steps and order as the CPU path, so a frame matches it to a few levels (tests/test_render_gl.py):
  source (photo Ken Burns view sampled with PIL's bicubic, or an uploaded frame) -> legacy fade/dip transition ->
  HyperFrames grain -> layers pasted through their alpha (credit line, overlays, subtitle; drawn by Pillow on the CPU,
  uploaded only when they change) -> vignette.
Frames with effect layers or the newer transitions still come from the CPU (render.render_frame decides).
Measured on an RTX 4070 Ti SUPER: ~560 frames/s drawn and read back, ~160 frames/s with NVENC encoding.
"""
import queue
import threading

import numpy as np
from PIL import Image

W, H = 1920, 1080

VS = """#version 330
in vec2 p; out vec2 uv;
void main() { uv = vec2((p.x + 1.0) / 2.0, (p.y + 1.0) / 2.0); gl_Position = vec4(p, 0.0, 1.0); }  // rows read bottom-up = image top-down
"""
FS = """#version 330
in vec2 uv; out vec4 o;
uniform sampler2D srcA; uniform vec2 sizeA; uniform vec4 boxA;   // box = x0, y0, w, h in source pixels
uniform sampler2D srcB; uniform vec2 sizeB; uniform vec4 boxB;
uniform int mixmode; uniform float mixval;                       // 0 none, 1 fade from B, 2 dip from black
uniform sampler2D grain; uniform vec2 goff; uniform int use_grain;
uniform sampler2D lay0; uniform sampler2D lay1; uniform sampler2D lay2; uniform ivec3 use_lay;

float cr(float x) { x = abs(x); return x < 1.0 ? (1.5 * x - 2.5) * x * x + 1.0 : (x < 2.0 ? ((-0.5 * x + 2.5) * x - 4.0) * x + 2.0 : 0.0); }

// PIL BICUBIC with a box: Catmull-Rom (a = -0.5), kernel widened by the scale when shrinking
vec3 sample_box(sampler2D tex, vec2 size, vec4 box) {
  vec2 scale = box.zw / vec2(1920.0, 1080.0);
  vec2 fs = max(scale, vec2(1.0));
  vec2 c = box.xy + uv * box.zw;                       // source position of this output pixel's centre
  vec2 sup = 2.0 * fs;
  ivec2 lo = ivec2(floor(c - sup)), hi = ivec2(ceil(c + sup));
  vec3 s = vec3(0.0); float ws = 0.0;
  for (int y = lo.y; y <= hi.y; y++) {
    float wy = cr((float(y) + 0.5 - c.y) / fs.y);
    if (wy == 0.0) continue;
    for (int x = lo.x; x <= hi.x; x++) {
      float w = cr((float(x) + 0.5 - c.x) / fs.x) * wy;
      if (w == 0.0) continue;
      ivec2 q = clamp(ivec2(x, y), ivec2(0), ivec2(size) - 1);
      s += texelFetch(tex, q, 0).rgb * w; ws += w;
    }
  }
  return clamp(s / ws, 0.0, 1.0);
}

vec3 paste(vec3 c, sampler2D l) {
  vec4 v = texelFetch(l, ivec2(uv * vec2(1920.0, 1080.0)), 0);
  return mix(c, v.rgb, v.a);
}

void main() {
  vec3 c = sample_box(srcA, sizeA, boxA);
  if (mixmode == 1) c = mix(sample_box(srcB, sizeB, boxB), c, mixval);
  else if (mixmode == 2) c = c * mixval;
  // the CPU path holds 8-bit frames between steps: PIL rounds the resize, numpy truncates the fade
  c = mixmode == 0 ? floor(c * 255.0 + 0.5) / 255.0 : floor(c * 255.0 + 0.0001) / 255.0;
  ivec2 px = ivec2(uv * vec2(1920.0, 1080.0));
  if (use_grain == 1) {
    vec4 t = texelFetch(grain, ivec2(mod(vec2(px) - goff, 200.0)), 0);
    c = mix(c, t.rgb, floor(t.a * 0.09 * 255.0 + 0.5) / 255.0);
  }
  if (use_lay.x == 1) c = paste(c, lay0);
  if (use_lay.y == 1) c = paste(c, lay1);
  if (use_lay.z == 1) c = paste(c, lay2);
  vec2 d = (vec2(px) - vec2(960.0, 540.0)) / (vec2(1920.0, 1080.0) * 0.62);
  float v = 1.0 - 0.38 * pow(clamp(length(d) - 0.45, 0.0, 1.0), 1.6);
  c *= floor(v * 255.0 + 0.5) / 255.0;
  o = vec4(c, 1.0);
}
"""


class GLCompositor:
    """One OpenGL context per process, owned by one thread: an OpenGL context must not be used from several threads
    (the studio server answers each request on its own thread). call(fn) runs fn on that thread and returns its
    result; source() and frame() must only be used inside such a call."""

    def __init__(self, grain_tile):
        self._q = queue.Queue(); ready = threading.Event(); err = []

        def loop():
            try:
                self._init(grain_tile)
            except Exception as e:  # noqa: BLE001 - reported to the creating thread
                err.append(e); ready.set(); return
            ready.set()
            while True:
                fn, box, done = self._q.get()
                try:
                    box.append((True, fn()))
                except Exception as e:  # noqa: BLE001 - re-raised in the caller's thread
                    box.append((False, e))
                done.set()

        threading.Thread(target=loop, name='gl', daemon=True).start()
        ready.wait()
        if err:
            raise err[0]

    def call(self, fn):
        box, done = [], threading.Event()
        self._q.put((fn, box, done)); done.wait()
        ok, v = box[0]
        if not ok:
            raise v
        return v

    def _init(self, grain_tile):
        import moderngl
        self.mgl = moderngl
        self.ctx = moderngl.create_standalone_context(require=330)
        self.prog = self.ctx.program(vertex_shader=VS, fragment_shader=FS)
        quad = self.ctx.buffer(np.array([-1, -1, 1, -1, -1, 1, 1, 1], 'f4').tobytes())
        self.vao = self.ctx.simple_vertex_array(self.prog, quad, 'p')
        self.fbo = self.ctx.simple_framebuffer((W, H), components=3)
        tile = Image.open(grain_tile).convert('RGBA')
        self.grain = self.ctx.texture(tile.size, 4, tile.tobytes())
        self.photos = {}                         # id(Photo) -> texture of its graded base image
        self.slots = [self.ctx.texture((W, H), 3), self.ctx.texture((W, H), 3)]  # uploaded frames for A / B
        self.lays = [[None, self.ctx.texture((W, H), 4)] for _ in range(3)]       # [key, texture]
        for i, name in enumerate(('srcA', 'srcB', 'grain', 'lay0', 'lay1', 'lay2')):
            self.prog[name] = i
        self.renderer = self.ctx.info.get('GL_RENDERER', '?')

    def _photo_tex(self, ph):
        key = id(ph)
        if key not in self.photos:
            if len(self.photos) >= 8:
                k = next(iter(self.photos)); self.photos.pop(k)[0].release()
            self.photos[key] = (self.ctx.texture(ph.base.size, 3, ph.base.tobytes()), ph)  # keep ph alive: id() stays unique
        return self.photos[key][0], ph.base.size

    def source(self, slot, obj, lt):
        """(texture, size, box) for slot 0 (A) or 1 (B): a render.Photo is sampled through its Ken Burns box on the
        GPU; anything else (Video, Blank, or an HxWx3 array) is uploaded as a full frame."""
        if hasattr(obj, 'box') and hasattr(obj, 'base'):
            tex, size = self._photo_tex(obj)
            x0, y0, x1, y1 = obj.box(lt)
            return tex, size, (x0, y0, x1 - x0, y1 - y0)
        arr = obj if isinstance(obj, np.ndarray) else obj.frame(lt)
        self.slots[slot].write(np.ascontiguousarray(arr, np.uint8).tobytes())
        return self.slots[slot], (W, H), (0.0, 0.0, float(W), float(H))

    def frame(self, A, B=None, mixmode=0, mixval=1.0, layers=(), grain_offset=None):
        """A/B: from source(). layers: up to 3 (key, RGBA PIL image) pasted in order; key None = upload every time."""
        if True:  # keeps the block below as it was; runs on the GL thread (inside call())
            p = self.prog
            A[0].use(0); p['sizeA'] = A[1]; p['boxA'] = A[2]
            if B is not None:
                B[0].use(1); p['sizeB'] = B[1]; p['boxB'] = B[2]
            p['mixmode'] = mixmode if (B is not None or mixmode == 2) else 0; p['mixval'] = float(mixval)
            self.grain.use(2); p['use_grain'] = int(grain_offset is not None)
            if grain_offset is not None:
                p['goff'] = grain_offset
            use = [0, 0, 0]
            for i, (key, img) in enumerate(list(layers)[:3]):
                slot = self.lays[i]
                if key is None or slot[0] != key:
                    slot[1].write(img.tobytes()); slot[0] = key
                slot[1].use(3 + i); use[i] = 1
            p['use_lay'] = tuple(use)
            self.fbo.use(); self.vao.render(self.mgl.TRIANGLE_STRIP)
            return self.fbo.read(components=3, alignment=1)

    # ------------------------------------------------------------------ phase 2: multi-pass (transitions + effect layers)
    def _init_multi(self):
        if getattr(self, 'trans', None) is not None:
            return
        ctx = self.ctx; quad = self.ctx.buffer(np.array([-1, -1, 1, -1, -1, 1, 1, 1], 'f4').tobytes())

        def prog(fs):
            pr = ctx.program(vertex_shader=VS, fragment_shader=fs); return pr, ctx.simple_vertex_array(pr, quad, 'p')
        self.srcp = prog(SRC_FS); self.trans = prog(TRANS_FS); self.blurp = prog(BLUR_FS); self.fxp = prog(FX_FS)

        def target(dtype):
            t = ctx.texture((W, H), 4, dtype=dtype); t.repeat_x = t.repeat_y = False
            return t, ctx.framebuffer(color_attachments=[t])
        self.T = [target('f1') for _ in range(3)]        # 8-bit: cur source, prev source, transition result
        self.P = [target('f2') for _ in range(3)]        # float: effect ping-pong (+ 1 for blur)
        self.half = [ctx.texture((W // 2, H // 2), 1) for _ in range(2)]  # scratch / dust layers
        for t in self.half:
            t.repeat_x = t.repeat_y = False
        self.lut = ctx.texture((1021, 1), 1)
        self.noise = {}                                   # (size, idx) -> R32F field
        self.media = None

    def _pass(self, pv, fbo, **uni):
        pr, vao = pv
        for k, v in uni.items():
            if k in pr:
                pr[k].value = v
        fbo.use(); vao.render(self.mgl.TRIANGLE_STRIP)

    def _draw_source(self, i, S):
        S[0].use(0)
        self._pass(self.srcp, self.T[i][1], src=0, size=S[1], box=S[2])
        return self.T[i][0]

    def _noise_tex(self, size, idx):
        import render_fx as FX
        key = (round(size, 1), idx)
        if key not in self.noise:
            self.noise[key] = self.ctx.texture((W, H), 1, np.ascontiguousarray(FX.noise_field(size, idx), np.float32).tobytes(), dtype='f4')
        return self.noise[key]

    def _blur(self, src, sigma, before=None, k=1.0):
        """Separable Gaussian (std = sigma px, like PIL GaussianBlur(radius)) into a float target; optional mix with before."""
        outs = [t for t in self.P if t[0] is not src and t[0] is not before]
        a, b = outs[0], outs[1]
        src.use(0)
        self._pass(self.blurp, a[1], src=0, dirv=(1.0, 0.0), sigma=float(sigma), use_before=0)
        a[0].use(0)
        if before is not None:
            before.use(1)
        self._pass(self.blurp, b[1], src=0, before=1, dirv=(0.0, 1.0), sigma=float(sigma), use_before=int(before is not None), k=float(k))
        return b[0]

    def frame_multi(self, A, B, trans, plan, layers=(), grain_offset=None):
        """A, B: sources (B may be None). trans: (type, progress 0..1) or None. plan: render_fx.effect_plan(). Then the
        same final pass as frame() (grain, layers, vignette)."""
        self._init_multi()
        cur = self._draw_source(0, A)
        if trans:
            typ, a = trans; e = a * a * (3 - 2 * a)
            prev = self._draw_source(1, B) if B is not None else None
            if typ == 'blur':
                r = 18 * (1 - abs(2 * e - 1)); src = prev if (prev is not None and e < 0.5) else cur
                cur = self._blur(src, r) if r > 0.5 else src
            else:
                tid = TRANS_IDS[typ]
                if typ == 'pixelize':
                    for t in (cur, prev):
                        if t is not None:
                            t.build_mipmaps(); t.filter = (self.mgl.LINEAR_MIPMAP_LINEAR, self.mgl.LINEAR)
                cur.use(0)
                if prev is not None:
                    prev.use(1)
                self._pass(self.trans, self.T[2][1], cur=0, prev=1, has_prev=int(prev is not None), ttype=tid, a=float(a), e=float(e))
                for t in (self.T[0][0], self.T[1][0]):
                    t.filter = (self.mgl.LINEAR, self.mgl.LINEAR)
                cur = self.T[2][0]
        for s in plan:
            p = s['p']
            if s['type'] == 'blur':
                if p['radius'] > 0.3:
                    cur = self._blur(cur, p['radius'], before=cur, k=s['k'])
                continue
            dst = next(t for t in self.P if t[0] is not cur)
            uni = {'src': 0, 'etype': FX_IDS[s['type']], 'k': float(s['k']), 'shift': (s.get('dx', 0), s.get('dy', 0)),
                   'flick': float(s.get('flicker', 1.0)), 'use_color': 0, 'use_grain': 0, 'use_scr': 0, 'vig_mode': 0}
            cur.use(0)
            if 'color' in s:
                m, lut = s['color']; self.lut.write(np.ascontiguousarray(lut, np.uint8).tobytes()); self.lut.use(1)
                uni.update(use_color=1, lut=1, cm=tuple(float(x) for x in np.asarray(m, np.float32).T.flatten()))
            if s.get('grain'):
                size, idx, amt = s['grain']; self._noise_tex(size, idx).use(2); uni.update(use_grain=1, noise=2, gamt=float(amt) * 28 / 255)
            if s.get('scratch'):
                lay, dark = s['scratch']; self.half[0].write(lay.tobytes()); self.half[1].write(dark.tobytes())
                self.half[0].use(3); self.half[1].use(4); uni.update(use_scr=1, slay=3, sdark=4)
            t = s['type']
            if t == 'old_film':
                uni.update(vig_mode=1 if p['vignette'] > 0 else 0, vig_amt=float(p['vignette']), vig_size=0.5)
            elif t == 'vignette':
                uni.update(vig_mode=2, vig_amt=float(p['amount']), vig_size=float(p['size']))
            elif t == 'light_leak':
                uni.update(lrgb=tuple(float(x) / 255 for x in s['rgb']), lc=(float(s['cx']), float(s['cy'])), lamp=float(s['amp']))
            elif t == 'letterbox':
                uni.update(bh=int(s['bh']))
            elif t == 'flash':
                uni.update(flash=float(p['amount']))
            elif t == 'media_overlay':
                rgba = s['rgba']; th, tw, nc = rgba.shape  # 3 channels: opaque video frame (alpha reads as 1)
                if self.media is None or self.media.size != (tw, th) or self.media.components != nc:
                    if self.media is not None:
                        self.media.release()
                    self.media = self.ctx.texture((tw, th), nc); self.media.repeat_x = self.media.repeat_y = False
                self.media.write(np.ascontiguousarray(rgba).tobytes()); self.media.use(5)
                uni.update(media=5, rect=tuple(int(x) for x in s['rect']), blend=BLEND_IDS.get(p.get('blend', 'screen'), 1))
            self._pass(self.fxp, dst[1], **uni)
            cur = dst[0]
        return self.frame((cur, (W, H), (0.0, 0.0, float(W), float(H))), None, 0, 1.0, layers, grain_offset)


TRANS_IDS = {'fade_legacy': 1, 'dip_legacy': 2, 'fade': 3, 'dip': 4, 'dip_white': 5, 'wipe_left': 6, 'wipe_right': 7, 'wipe_up': 8,
             'wipe_down': 9, 'slide_left': 10, 'slide_right': 11, 'slide_up': 12, 'slide_down': 13, 'zoom': 14, 'circle_open': 16,
             'circle_close': 17, 'radial': 18, 'pixelize': 19}
FX_IDS = {'old_film': 1, 'grain': 2, 'dust_scratches': 3, 'flicker': 4, 'jitter': 5, 'vignette': 6, 'light_leak': 7, 'letterbox': 9,
          'color': 10, 'flash': 11, 'media_overlay': 12}
BLEND_IDS = {'normal': 0, 'screen': 1, 'multiply': 2, 'overlay': 3, 'add': 4, 'lighten': 5, 'darken': 6, 'soft_light': 7}

_SAMPLE = FS[FS.index('float cr('):FS.index('vec3 paste(')]  # the PIL-bicubic Ken Burns sampler of the one-pass shader
SRC_FS = """#version 330
in vec2 uv; out vec4 o;
""" + _SAMPLE + """
uniform sampler2D src; uniform vec2 size; uniform vec4 box;
void main() { o = vec4(sample_box(src, size, box), 1.0); }
"""
TRANS_FS = """#version 330
in vec2 uv; out vec4 o;
uniform sampler2D cur; uniform sampler2D prev; uniform int has_prev; uniform int ttype; uniform float a; uniform float e;
const vec2 WH = vec2(1920.0, 1080.0);
vec3 C(ivec2 q) { return texelFetch(cur, clamp(q, ivec2(0), ivec2(WH) - 1), 0).rgb; }
vec3 P(ivec2 q) { return texelFetch(prev, clamp(q, ivec2(0), ivec2(WH) - 1), 0).rgb; }
void main() {
  ivec2 px = ivec2(uv * WH); vec3 c = C(px);
  if (ttype == 2) { o = vec4(c * a, 1.0); return; }
  if (ttype == 4) { o = vec4(has_prev == 1 ? (e < 0.5 ? P(px) * max(0.0, 1.0 - 2.0 * e) : c * (2.0 * e - 1.0)) : c * e, 1.0); return; }
  if (ttype == 5) { float w = 1.0 - abs(2.0 * e - 1.0); vec3 s = (has_prev == 0 || e >= 0.5) ? c : P(px); o = vec4(s * (1.0 - w) + w, 1.0); return; }
  if (has_prev == 0) { o = vec4(c, 1.0); return; }
  vec3 p = P(px);
  int x = px.x, y = px.y, Wi = 1920, Hi = 1080;
  if (ttype == 1) { o = vec4(p * (1.0 - a) + c * a, 1.0); return; }
  if (ttype == 3) { o = vec4(p * (1.0 - e) + c * e, 1.0); return; }
  if (ttype >= 6 && ttype <= 9) {
    int xw = int(float(Wi) * e), yh = int(float(Hi) * e);
    bool showc = ttype == 6 ? (xw > 0 && x >= Wi - xw) : ttype == 7 ? x < xw : ttype == 8 ? (yh > 0 && y >= Hi - yh) : y < yh;
    o = vec4(showc ? c : p, 1.0); return;
  }
  if (ttype >= 10 && ttype <= 13) {
    int xw = int(float(Wi) * e), yh = int(float(Hi) * e); vec3 r;
    if (ttype == 10) r = x < Wi - xw ? P(ivec2(x + xw, y)) : C(ivec2(x - (Wi - xw), y));
    else if (ttype == 11) r = x >= xw ? P(ivec2(x - xw, y)) : C(ivec2(x + Wi - xw, y));
    else if (ttype == 12) r = y < Hi - yh ? P(ivec2(x, y + yh)) : C(ivec2(x, y - (Hi - yh)));
    else r = y >= yh ? P(ivec2(x, y - yh)) : C(ivec2(x, y + Hi - yh));
    o = vec4(r, 1.0); return;
  }
  if (ttype == 14) {
    float z = 1.0 + 0.25 * e; vec2 bw = WH / z; vec2 b0 = (WH - bw) / 2.0;
    vec3 pz = texture(prev, (b0 + uv * bw) / WH).rgb;
    o = vec4(pz * (1.0 - e) + c * e, 1.0); return;
  }
  if (ttype >= 16 && ttype <= 18) {
    vec2 d = vec2(px) - WH / 2.0; float r = length(d) / length(WH / 2.0);
    float ang = mod(atan(d.x, -d.y) / 6.28318530718, 1.0); float soft = 0.03; float m;
    if (ttype == 16) m = clamp((e * (1.0 + soft) - r) / soft, 0.0, 1.0);
    else if (ttype == 17) m = clamp((r - (1.0 - e) * (1.0 + soft) + soft) / soft, 0.0, 1.0);
    else m = clamp((e * (1.0 + soft) - ang) / soft, 0.0, 1.0);
    o = vec4(p * (1.0 - m) + c * m, 1.0); return;
  }
  if (ttype == 19) {
    float k = 1.0 - abs(2.0 * e - 1.0); float bs = floor(1.0 + k * 60.0 + 0.5);
    if (bs <= 1.0) { o = vec4(e < 0.5 ? p : c, 1.0); return; }
    // PIL: resize BILINEAR down to (W//bs, H//bs) (triangle filter, support = scale), then NEAREST back up
    vec2 sw = floor(WH / bs); vec2 cell = floor((vec2(px) + 0.5) * sw / WH);
    vec2 sc = WH / sw; vec2 cc = (cell + 0.5) * sc; const int N = 12; vec2 st = 2.0 * sc / float(N);
    float lod = log2(max(st.x, 1.0)); vec3 acc = vec3(0.0); float wsum = 0.0;
    for (int j = 0; j < N; j++) for (int i = 0; i < N; i++) {
      vec2 q = cc - sc + (vec2(i, j) + 0.5) * st;
      vec2 tw = max(1.0 - abs(q - cc) / sc, 0.0); float w = tw.x * tw.y;
      vec2 quv = clamp(q / WH, vec2(0.0), vec2(1.0));
      acc += (e < 0.5 ? textureLod(prev, quv, lod).rgb : textureLod(cur, quv, lod).rgb) * w; wsum += w;
    }
    o = vec4(acc / wsum, 1.0); return;
  }
  o = vec4(c, 1.0);
}
"""
BLUR_FS = """#version 330
in vec2 uv; out vec4 o;
uniform sampler2D src; uniform sampler2D before; uniform vec2 dirv; uniform float sigma; uniform int use_before; uniform float k;
void main() {
  vec2 WH = vec2(1920.0, 1080.0); ivec2 px = ivec2(uv * WH);
  int rad = int(ceil(3.0 * sigma)); vec3 s = vec3(0.0); float ws = 0.0;
  for (int i = -rad; i <= rad; i++) {
    float w = exp(-0.5 * float(i * i) / (sigma * sigma));
    ivec2 q = clamp(px + ivec2(dirv * float(i)), ivec2(0), ivec2(WH) - 1);
    s += clamp(texelFetch(src, q, 0).rgb, 0.0, 1.0) * w; ws += w;
  }
  vec3 b = s / ws;
  if (use_before == 1) b = mix(texelFetch(before, px, 0).rgb, b, k);
  o = vec4(b, 1.0);
}
"""
FX_FS = """#version 330
in vec2 uv; out vec4 o;
uniform sampler2D src; uniform int etype; uniform float k; uniform ivec2 shift; uniform float flick;
uniform int use_color; uniform mat3 cm; uniform sampler2D lut;
uniform int use_grain; uniform sampler2D noise; uniform float gamt;
uniform int use_scr; uniform sampler2D slay; uniform sampler2D sdark;
uniform int vig_mode; uniform float vig_amt; uniform float vig_size;
uniform vec3 lrgb; uniform vec2 lc; uniform float lamp; uniform int bh; uniform float flash;
uniform sampler2D media; uniform ivec4 rect; uniform int blend;
const vec2 WH = vec2(1920.0, 1080.0);
vec3 F(ivec2 q) { return texelFetch(src, ivec2(mod(vec2(q), WH)), 0).rgb; }
vec3 colorop(vec3 v) {
  vec3 g = floor(clamp(v, 0.0, 1.0) * 255.0) * cm;
  ivec3 i = ivec3(clamp(floor(g + 0.5), 0.0, 1020.0));
  return vec3(texelFetch(lut, ivec2(i.r, 0), 0).r, texelFetch(lut, ivec2(i.g, 0), 0).r, texelFetch(lut, ivec2(i.b, 0), 0).r);
}
float vmask(vec2 px, float size) {
  vec2 d = (px - WH / 2.0) / (WH / 2.0); float r = length(d) / 1.414;
  return pow(clamp((r - (0.25 + 0.5 * size) * 0.7) / 0.6, 0.0, 1.0), 1.5);
}
vec3 bl(vec3 b, vec3 s, int m) {
  vec3 r = s;
  if (m == 1) r = 1.0 - (1.0 - b) * (1.0 - s);
  else if (m == 2) r = b * s;
  else if (m == 3) r = mix(2.0 * b * s, 1.0 - 2.0 * (1.0 - b) * (1.0 - s), step(0.5, b));
  else if (m == 4) r = b + s;
  else if (m == 5) r = max(b, s);
  else if (m == 6) r = min(b, s);
  else if (m == 7) r = (1.0 - 2.0 * s) * b * b + 2.0 * s * b;
  return clamp(r, 0.0, 1.0);
}
void main() {
  ivec2 px = ivec2(uv * WH); vec3 f = F(px); vec3 g = f;
  if (etype == 1 || etype == 5) g = F(px - shift);
  if (use_color == 1) g = colorop(g);
  g *= flick;
  if (use_grain == 1) g += texelFetch(noise, px, 0).r * gamt;
  if (use_scr == 1) { float sa = texture(slay, uv).r * 0.7; float sb = texture(sdark, uv).r * 0.85; g = g * (1.0 - sb - sa) + sa; }
  if (vig_mode == 1) g *= 1.0 - vmask(vec2(px), 0.5) * 0.85 * vig_amt;
  if (vig_mode == 2) g *= 1.0 - vmask(vec2(px), vig_size) * vig_amt;
  if (etype == 7) {
    vec2 q = (vec2(px) - lc) / vec2(WH.x * 0.45, WH.y * 0.6);
    g = g + (lrgb - g * 0.3) * exp(-dot(q, q)) * lamp * 0.8;
  }
  if (etype == 9 && (px.y < bh || px.y >= 1080 - bh)) g = vec3(0.0);
  if (etype == 11) g = g + (1.0 - g) * flash;
  if (etype == 12) {
    ivec2 q = px - rect.xy;
    if (q.x >= 0 && q.y >= 0 && q.x < rect.z && q.y < rect.w) {
      vec4 t = texelFetch(media, q, 0); vec3 b = clamp(f, 0.0, 1.0);
      g = f * (1.0 - t.a) + bl(b, t.rgb, blend) * t.a;
    }
  }
  o = vec4(mix(f, g, k), 1.0);
}
"""
