"""Film look check (assets/looks.json, brief.json "look"): every rendered scene and map must sit in the film's colour family.

PY scripts/lookcheck.py JOB      run after render_all.sh (docs/WORKFLOW.md stage 6). Prints !! lines, exit 1 when any.
For each media/scene-*.mp4 and media/map-*.mp4 used on the video track, three frames (25/50/75 %) are measured:
  - ground: the median colour of the frame border (outer 8 %) must be near the look's bg (scenes) or its land/sea (maps);
  - accents: strongly saturated pixels whose hue is far from the look's accent/accent2/highlight (and not a drawn doll or
    a photo inside the scene) are counted; more than 3 % of the frame is flagged as off-palette colour.
User 2026-11-14: the 通史3 reference keeps one colour family for the whole film; our films mixed dark navy, brown,
satellite green and bright reds, which read as modern and patchy.
"""
import colorsys, json, subprocess, sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]


def hexrgb(h):
    h = h.lstrip('#'); return np.array([int(h[i:i + 2], 16) for i in (0, 2, 4)], np.float32)


def frame(path, t):
    raw = subprocess.run(['ffmpeg', '-v', 'error', '-ss', f'{t:.2f}', '-i', str(path), '-frames:v', '1', '-vf', 'scale=480:270',
                          '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-'], capture_output=True).stdout
    return np.frombuffer(raw, np.uint8).reshape(270, 480, 3).astype(np.float32) if len(raw) == 480 * 270 * 3 else None


def dur(path):
    r = subprocess.run(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', str(path)], capture_output=True, text=True)
    try:
        return float(r.stdout.strip())
    except ValueError:
        return 0.0


def hue(rgb):
    return colorsys.rgb_to_hsv(*(rgb / 255))[0] * 360


def main(job):
    d = Path(job) if Path(job).is_dir() else ROOT / 'projects' / job
    brief = json.loads((d / 'brief.json').read_text(encoding='utf-8'))
    name = brief.get('look')
    looks = json.loads((ROOT / 'assets' / 'looks.json').read_text(encoding='utf-8'))
    if name not in looks:
        print(f'no look set in brief.json ("look": paper | dark): nothing to check'); return 0
    lk = looks[name]
    grounds = {'scene': [hexrgb(lk['bg']), hexrgb(lk['bg2']), hexrgb(lk['panel'])], 'map': [hexrgb(lk['land']), hexrgb(lk['sea'])]}
    ok_hues = [hue(hexrgb(lk[k])) for k in ('accent', 'accent2', 'highlight')]
    tl = json.loads((d / 'timeline.json').read_text(encoding='utf-8'))
    srcs = sorted({c['src'] for t in tl['tracks'] if t['id'] == 'video' for c in t['clips']
                   if str(c.get('src', '')).startswith(('media/scene-', 'media/map-'))})
    warn = 0
    for s in srcs:
        p = d / s; kind = 'map' if '/map-' in s else 'scene'
        if not p.exists():
            continue
        L = dur(p); bad_g, bad_c = [], []
        for f in (0.25, 0.5, 0.75):
            a = frame(p, L * f)
            if a is None:
                continue
            b = 0.08; h, w = a.shape[:2]
            border = np.concatenate([a[:int(h * b)].reshape(-1, 3), a[-int(h * b):].reshape(-1, 3), a[:, :int(w * b)].reshape(-1, 3), a[:, -int(w * b):].reshape(-1, 3)])
            med = np.median(border, 0)
            near = np.min(np.stack([np.linalg.norm(border - g, axis=1) for g in grounds[kind]]), 0) < 60
            if near.mean() < 0.6:  # most of the border must be the look's ground (maps: its land or sea)
                bad_g.append(tuple(int(x) for x in med))
            mx, mn = a.max(2), a.min(2); sat = (mx - mn) / np.maximum(mx, 1)
            strong = (sat > 0.55) & (mx > 90)
            if strong.mean() > 0.002:
                px = a[strong][:: max(1, int(strong.sum() // 2000))]
                hs = np.array([hue(q) for q in px])
                off = np.ones(len(hs), bool)
                for oh in ok_hues:
                    off &= np.minimum(abs(hs - oh), 360 - abs(hs - oh)) > 28
                share = strong.mean() * off.mean()
                if share > 0.03:
                    bad_c.append(round(share * 100, 1))
        if bad_g:
            print(f'!! {s}: ground {bad_g[0]} is not the {name} look ({lk["bg"] if kind == "scene" else "flat land/sea: render with the look, no satellite"}): use the default background / L.C.bg, not a fixed colour'); warn += 1
        if bad_c:
            print(f'!! {s}: {max(bad_c)} % of the frame in colours outside the {name} palette: use L.C.accent / accent2 / highlight'); warn += 1
    print(f'look {name}: {len(srcs)} scenes/maps checked, {warn} warnings')
    return warn


if __name__ == '__main__':
    sys.exit(1 if main(sys.argv[1]) else 0)
