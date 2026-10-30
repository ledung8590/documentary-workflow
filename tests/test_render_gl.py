"""GPU compositor parity: a frame drawn by render_gl must match the CPU composite (skipped without moderngl / a GPU)."""
import sys
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import render as R

moderngl = pytest.importorskip('moderngl')


@pytest.fixture(scope='module')
def gl():
    R.USE_GPU = True; R._gl = None
    g = R.gpu()
    if g is None:
        pytest.skip('no OpenGL 3.3 context')
    return g


def psnr(a, b):
    m = ((a.astype(np.float32) - b.astype(np.float32)) ** 2).mean()
    return 99.0 if m == 0 else 10 * np.log10(255 ** 2 / m)


def scene(tmp_path, w, h):
    """A synthetic photo (gradients + edges) so Ken Burns sampling differences would show."""
    from PIL import Image
    y, x = np.mgrid[0:h, 0:w]
    a = np.dstack([(x * 255 / w), (y * 255 / h), ((x // 40 + y // 40) % 2) * 255]).astype(np.uint8)
    p = tmp_path / f'p{w}x{h}.png'; Image.fromarray(a).save(p); return p


@pytest.mark.parametrize('w,h,motion', [(3000, 2000, None), (1200, 1600, None), (3000, 2000, {'type': 'pull', 'dx': -0.04}),
                                        (3000, 2000, {'type': 'custom', 'from': {'zoom': 1.0}, 'to': {'zoom': 1.4, 'x': 0.3}})])
def test_photo_frame_matches_cpu(tmp_path, gl, w, h, motion):
    c = {'id': 'V1', 'start': 0.0, 'end': 8.0, 'src': 'x', 'caption': 'Ảnh: thử nghiệm', 'motion': motion}
    ph = R.Photo(scene(tmp_path, w, h), c, 0)
    vids = [c]; ov = [{'id': 'O1', 'type': 'date_tag', 'start': 1.0, 'end': 6.0, 'props': {'text': '03:17 · 23.11.1970'}}]
    for t in (0.0, 2.5, 7.9):
        cpu = R.composite(ph.frame(t), c, t, ov, 'Phụ đề thử nghiệm.', {'grain': True}, {})
        gpu = R.render_frame(t, vids, 0, lambda j: ph, ov, 'Phụ đề thử nghiệm.', {'grain': True}, {}, as_bytes=False)
        assert psnr(cpu, gpu) > 40, (w, h, motion, t, psnr(cpu, gpu))


def test_fade_and_dip_match_cpu(tmp_path, gl):
    a = {'id': 'V1', 'start': 0.0, 'end': 4.0, 'src': 'x'}
    b = {'id': 'V2', 'start': 4.0, 'end': 8.0, 'src': 'y', 'transition_in': {'type': 'fade', 'dur': 1.0}}
    pa, pb = R.Photo(scene(tmp_path, 3000, 2000), a, 0), R.Photo(scene(tmp_path, 2400, 1800), b, 1)
    src = lambda j: (pa, pb)[j]
    for t in (4.3, 4.7):
        cpu = R.composite(R.transition_in(pb.frame(t - 4), b, t, lambda: pa.frame(t), 1), b, t, [], None, {}, {})
        gpu = R.render_frame(t, [a, b], 1, src, [], None, {}, {}, as_bytes=False)
        assert psnr(cpu, gpu) > 40
    b['transition_in'] = {'type': 'dip', 'dur': 1.0}
    cpu = R.composite(R.transition_in(pb.frame(0.5), b, 4.5, None, 1), b, 4.5, [], None, {}, {})
    assert psnr(cpu, R.render_frame(4.5, [a, b], 1, src, [], None, {}, {}, as_bytes=False)) > 40


def _pair(tmp_path):
    import render_fx as FX  # noqa: F401
    a = {'id': 'V1', 'start': 0.0, 'end': 10.0, 'src': 'x'}
    b = {'id': 'V2', 'start': 10.0, 'end': 20.0, 'src': 'y'}
    pa, pb = R.Photo(scene(tmp_path, 3000, 2000), a, 0), R.Photo(scene(tmp_path, 2400, 1800), b, 1)
    return a, b, (lambda j: (pa, pb)[j])


def _both(t, vids, k, src, effects=(), media=None):
    gpu = R.render_frame(t, vids, k, src, [], 'Phụ đề.', {'grain': True}, {}, effects, media, 24, None, as_bytes=False)
    c = vids[k]; lt = t - c['start']
    cur = R.transition_in(src(k).frame(lt), c, t, lambda: src(k - 1).frame(t - vids[k - 1]['start']), k)
    return psnr(R.composite(cur, c, t, [], 'Phụ đề.', {'grain': True}, {}, effects, media, 24, None), gpu)


def test_every_effect_matches_cpu(tmp_path, gl):
    import render_fx as FX
    a, b, src = _pair(tmp_path)
    for label, typ, params in FX.EFFECT_PRESETS:
        if typ == 'media_overlay':
            continue
        e = {'id': 'F1', 'type': typ, 'start': 2.0, 'end': 9.0, 'params': params, 'opacity': 0.9, 'fade_in': 0.5, 'fade_out': 0.5}
        for t in (2.25, 5.0):
            assert _both(t, [a, b], 0, src, [e]) > 42, (label, t)


def test_media_overlay_blends_match_cpu(tmp_path, gl):
    import render_fx as FX
    from PIL import Image
    a, b, src = _pair(tmp_path)
    ov = tmp_path / 'ov.png'
    Image.fromarray((np.random.default_rng(1).random((300, 500, 4)) * 255).astype(np.uint8)).save(ov)
    for blend in FX.BLENDS:
        p = {'src': 'ov', 'blend': blend, 'scale': 'contain', 'x': 0.4, 'y': 0.6, 'size': 0.5, 'speed': 1.0, 'loop': True}
        e = {'id': 'F2', 'type': 'media_overlay', 'start': 2.0, 'end': 9.0, 'params': p, 'opacity': 0.8}
        assert _both(5.0, [a, b], 0, src, [e], {'F2': FX.MediaLayer(ov, p, 24, sequential=False)}) > 42, blend


def test_every_transition_matches_cpu(tmp_path, gl):
    import render_fx as FX
    a, b, src = _pair(tmp_path)
    for typ in FX.TRANSITIONS:
        b['transition_in'] = {'type': typ, 'dur': 1.0}
        for t in (10.2, 10.45, 10.8):
            assert _both(t, [a, b], 1, src) > 42, (typ, t)
