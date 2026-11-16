"""Every real photo a JS scene embeds (p-X-tag-K.jpg or commons-<id>.jpg under media/): make sure the file exists,
add a LICENSES.md row, and write qa/scene_media.json {scene: [credit, [media/files]]} for plan.py SCENE_MEDIA.
PY qa/scene_media2.py"""
import json, re, shutil, sys, datetime
from pathlib import Path

D = Path(__file__).resolve().parents[1]
ROOT = D.parents[1]
sys.path[:0] = [str(ROOT / 'scripts')]
import media as M  # noqa: E402

cands = {}  # commons id -> candidate
bytag = {}
for cj in (D / 'media' / 'candidates').glob('*/candidates.json'):
    cs = json.loads(cj.read_text(encoding='utf-8'))['candidates']
    bytag[cj.parent.name] = cs
    for c in cs:
        cands.setdefault(f"{c['source']}-{c['id']}", c)
pat = re.compile(r"([A-Za-z0-9_.-]+)\.(jpg|jpeg|png)")
lic = (D / 'LICENSES.md').read_text(encoding='utf-8')
out, miss = {}, []
for f in sorted((D / 'scenes' / 'src').glob('*.js')):
    if f.stem.startswith('_'):
        continue
    names = {m.group(0) for m in pat.finditer(f.read_text(encoding='utf-8'))}
    for gj in (D / 'qa').glob('scene_media-*.json'):  # group lists: scenes that build file names in code (dImg('p-d-kut-2'))
        names |= {Path(x).name for x in json.loads(gj.read_text(encoding='utf-8')).get(f.stem, [None, []])[1]}
    names = sorted(names)
    credits, files = [], []
    for name in names:
        stem = name.rsplit('.', 1)[0]
        m = re.match(r'^(p-[a-e]2?-[a-z0-9-]+?)-(\d+)$', stem)
        c = None
        if m and m.group(1) in bytag:
            c = bytag[m.group(1)][int(m.group(2)) - 1]
        elif stem in cands:
            c = cands[stem]
        if c is None:
            miss.append(f'{f.stem}: {name}'); continue
        dst = D / 'media' / name
        if not dst.exists():
            src = M.download(c, D / 'media' / '_scene_dl')
            shutil.copyfile(src, dst)
        author = re.sub(r'\s+', ' ', c.get('author') or 'unknown author')[:80]
        credit = f'{author} / {c["source"].split(":")[-1].title()} ({c["licence"]})'
        rel = f'media/{name}'
        if rel not in lic:
            row = (f'| {rel} | {c["page"]} | {author} | {c["licence"]} {c.get("licence_url") or ""} | {credit} | '
                   f'{datetime.date.today()} | in scene {f.stem}: {c["title"][:100]} |\n')
            with open(D / 'LICENSES.md', 'a', encoding='utf-8') as fh:
                fh.write(row)
            lic += row
        credits.append(credit); files.append(rel)
    if files:
        out[f.stem] = [' · '.join(dict.fromkeys(credits)), files]
(D / 'qa' / 'scene_media.json').write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding='utf-8')
print(f'{len(out)} scenes, {sum(len(v[1]) for v in out.values())} files')
for x in miss:
    print('!! no candidate for', x)
