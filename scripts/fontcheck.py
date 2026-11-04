"""Glyph check before the draft render: every character the film shows must exist in the font that draws it,
otherwise it renders as an empty box (film 74, 2026-10-31: "→" is not in Oswald).

  PY scripts/fontcheck.py JOB      exit 1 and list each missing character with where it is used

Checked: overlay text (Oswald / Plex Mono / Be Vietnam Pro), burned-in subtitles (the timeline's subtitle font),
string literals in projects/JOB/scenes/*.js, and map labels (Oswald / Be Vietnam Pro). Uppercased forms are checked too
(the renderer uppercases titles: ß -> SS)."""
import json, re, sys
from pathlib import Path
from fontTools.ttLib import TTFont

ROOT = Path(__file__).resolve().parents[1]
FONTS = ROOT / 'assets' / 'fonts'
FILES = {'head': 'Oswald.ttf', 'mono': 'IBMPlexMono-Regular.ttf', 'monomed': 'IBMPlexMono-Medium.ttf',
         'body': 'BeVietnamPro-SemiBold.ttf', 'bodyreg': 'BeVietnamPro-Regular.ttf', 'military': 'SairaCondensed-Bold.ttf',
         'stencil': 'SairaStencilOne-Regular.ttf', 'blackops': 'BlackOpsOne-Regular.ttf'}
CMAP = {k: TTFont(str(FONTS / f)).getBestCmap() for k, f in FILES.items()}
CARD = ('head', 'mono', 'monomed', 'body', 'bodyreg')  # overlays and scenes mix these: a char must exist in all of them


def missing(s, kinds):
    out = set()
    for ch in set(s + s.upper()):
        if ch.isspace() or ord(ch) < 32:
            continue
        for k in kinds:
            if ord(ch) not in CMAP[k]:
                out.add((ch, k))
    return out


def strings(v):
    if isinstance(v, str):
        yield v
    elif isinstance(v, dict):
        for x in v.values():
            yield from strings(x)
    elif isinstance(v, list):
        for x in v:
            yield from strings(x)


def main(job):
    d = ROOT / 'projects' / job
    tl = json.loads((d / 'timeline.json').read_text(encoding='utf-8'))
    if (tl.get('language') or '')[:2] == 'ja':  # render.py and the scene/map engines draw Japanese films in M PLUS 1p
        jp = TTFont(str(FONTS / 'MPLUS1p-Bold.ttf')).getBestCmap()
        for k in FILES:
            CMAP[k] = jp; FILES[k] = 'MPLUS1p-Bold.ttf'
    found = {}

    def note(miss, where):
        for ch, k in miss:
            found.setdefault((ch, k), []).append(where)

    for tr in tl['tracks']:
        if tr['id'] == 'overlay':
            for c in tr['clips']:
                for s in strings(c.get('props', {})):
                    note(missing(s, CARD), f'overlay {c["id"]} "{s[:40]}"')
    sub = (tl.get('subtitle_style') or {}).get('font', 'body')
    srt = d / 'voice' / 'voice.srt'
    if srt.exists():
        for line in srt.read_text(encoding='utf-8-sig').splitlines():
            if line and not line[0].isdigit():
                note(missing(line, (sub if sub in CMAP else 'body',)), f'subtitle "{line[:40]}"')
    for js in sorted((d / 'scenes').glob('*.js')):
        src = js.read_text(encoding='utf-8')
        src = re.sub(r'//[^\n]*', '', src)  # comments are never drawn
        for m in re.finditer(r"'((?:[^'\\\n]|\\.)*)'|\"((?:[^\"\\\n]|\\.)*)\"|`([^`]*)`", src):
            s = next(g for g in m.groups() if g is not None)
            if re.search(r'[A-Za-zÀ-ÿ぀-ヿ一-鿿]', s):
                note(missing(s, CARD), f'scene {js.stem} "{s[:40]}"')
    for mp in sorted((d / 'maps').glob('*.json')):
        for L in json.loads(mp.read_text(encoding='utf-8')).get('layers', []):
            for key in ('text', 'sub'):
                if L.get(key):
                    note(missing(L[key], ('head', 'body')), f'map {mp.stem} "{L[key][:40]}"')
    if not found:
        print('fontcheck ok: every shown character exists in its font')
        return 0
    for (ch, k), where in sorted(found.items()):
        print(f'MISSING {ch!r} (U+{ord(ch):04X}) in {FILES[k]}: {len(where)}x, e.g. {where[0]}')
    return 1


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    sys.exit(main(sys.argv[1]))
