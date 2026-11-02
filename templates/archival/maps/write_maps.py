"""Write maps/<name>.json for every map spec maps/src/<name>.json ({"camera":[from,to],"layers":[...]}, times for a 10 s shot).
python write_maps.py [durations.json]  (durations: {name: seconds}; default 10 s)"""
import json, sys, pathlib
here = pathlib.Path(__file__).parent
base = {'exaggeration': 1.1, 'saturation': -0.35, 'brightness': 0.74}
def write(dur=None):
    dur = dur or {}
    for p in sorted((here / 'src').glob('*.json')):
        s = json.loads(p.read_text(encoding='utf-8')); name = p.stem
        d = dur.get(name, 10); k = d / 10
        ls = []
        for L in s['layers']:
            L = dict(L)
            for f in ('t', 'draw', 'until'):
                if f in L: L[f] = round(L[f] * k, 2)
            ls.append(L)
        a, b = s['camera']
        (here / f'{name}.json').write_text(json.dumps({'duration': d, **base, 'camera': [{'t': 0, **a}, {'t': d, **b}], 'layers': ls}, ensure_ascii=False), encoding='utf-8')
if __name__ == '__main__':
    write(json.loads(pathlib.Path(sys.argv[1]).read_text()) if len(sys.argv) > 1 else None)
