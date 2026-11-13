"""Write maps/<name>.json for every map spec maps/src/<name>.json, stretched to its shot length.
Two spec styles are accepted:
  - 10 s scale: {"camera": [from, to], "layers": [...]} with times for a 10 s shot (template default);
  - real seconds: {"duration": D, "camera": [{"t": 0, ...}, {"t": ..., ...}, ...], "layers": [...]} (any number of camera keys).
Times (layer t/draw/until, camera t) are scaled by shot length / spec length.
python write_maps.py [durations.json]  (durations: {name: seconds}; default = the spec's own length)"""
import json, sys, pathlib
here = pathlib.Path(__file__).parent
base = {'exaggeration': 1.1, 'saturation': -0.35, 'brightness': 0.74}
KEEP = ('shade', 'exaggeration', 'brightness', 'saturation', 'base')  # base 'satellite': the old 3D satellite map inside a look film


def write(dur=None):
    dur = dur or {}
    for p in sorted((here / 'src').glob('*.json')):
        s = json.loads(p.read_text(encoding='utf-8')); name = p.stem
        own = float(s.get('duration', 10))
        d = dur.get(name, own); k = d / own
        ls = []
        for L in s['layers']:
            L = dict(L)
            for f in ('t', 'draw', 'until'):
                if f in L: L[f] = round(L[f] * k, 2)
            ls.append(L)
        cam = s['camera']
        if all('t' in c for c in cam):
            cam = [{**c, 't': round(c['t'] * k, 3)} for c in cam]
        else:
            a, b = cam[0], cam[-1]
            cam = [{**a, 't': 0}, {**b, 't': d}]
        (here / f'{name}.json').write_text(json.dumps({**base, **{x: s[x] for x in KEEP if x in s}, 'duration': d, 'camera': cam, 'layers': ls}, ensure_ascii=False), encoding='utf-8')


if __name__ == '__main__':
    write(json.loads(pathlib.Path(sys.argv[1]).read_text()) if len(sys.argv) > 1 else None)
