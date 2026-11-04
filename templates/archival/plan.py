"""Template: templates/archival/plan.py, copied into projects/<id>/ by `doc.py plan JOB`. Edit SUBS_OVER per film.

Build this film's picture, overlay, sfx and music tracks from the plan files (shots.txt, overlays.txt, sound.txt).

  PY plan.py check            resolve every anchor, print shot lengths, warnings (long stills, repeats, gaps)
  PY plan.py durations        write scene/map durations (scenes/src/durations.json, maps/*.json) from shot lengths
  PY plan.py apply            replace video/overlay/sfx/music clips in timeline.json (studio store), then pick media

Anchor syntax: `S012` sentence start · `S012 "word phrase"` first word of that phrase · `S012+1.5` / `S012 "x"-0.3` offset
· `S012$` sentence end. shots.txt:  ANCHOR | SRC | caption      SRC = scene:NAME · map:NAME · pick:TAG#K · vid:TAG#K@IN · card
overlays.txt: ANCHOR .. ANCHOR | type | {json props}      sound.txt: ANCHOR | sfx/type/el_01 | gain [| dur]   or   ANCHOR .. ANCHOR | music/mood/el_01 | gain   or   ANCHOR .. ANCHOR | dip | dB (music dips under a key line)
"""
import json, re, sys, unicodedata
from pathlib import Path

D = Path(__file__).resolve().parent
ROOT = D.parents[1]
sys.path[:0] = [str(ROOT / 'scripts'), str(ROOT / 'studio')]
from common import read, write  # noqa: E402

JOB = D.name
timing = read(D / 'voice' / 'timing.json')
S = timing['sentences']
DUR = timing['duration']
FPS = 24
LANG = (read(D / 'brief.json') or {}).get('language', 'en')
CREDITS = {  # on-screen credit lines follow the script language
    'en': ('Terrain: AWS Terrain Tiles · Satellite: Sentinel-2 cloudless 2016 (EOX, CC BY 4.0) · Positions, arrows: schematic', 'Animated graphic (illustrative)', 'Effects'),
    'de': ('Gelände: AWS Terrain Tiles · Satellitenbild: Sentinel-2 cloudless 2016 (EOX, CC BY 4.0) · Positionen, Pfeile: schematisch', 'Animierte Grafik (schematisch)', 'Effekte'),
    'es': ('Relieve: AWS Terrain Tiles · Satélite: Sentinel-2 cloudless 2016 (EOX, CC BY 4.0) · Posiciones, flechas: esquemáticas', 'Gráfico animado (ilustrativo)', 'Efectos'),
    'vi': ('Địa hình: AWS Terrain Tiles · Vệ tinh: Sentinel-2 cloudless 2016 (EOX, CC BY 4.0) · Vị trí, mũi tên: minh hoạ', 'Đồ hoạ động (minh hoạ)', 'Hiệu ứng'),
    'fr': ('Relief : AWS Terrain Tiles · Satellite : Sentinel-2 cloudless 2016 (EOX, CC BY 4.0) · Positions, flèches : schématiques', 'Graphique animé (illustratif)', 'Effets'),
}
MAPCREDIT, SCENECREDIT, FXNAME = CREDITS.get(LANG, CREDITS['en'])
SUBS_OVER = set()  # scenes with no text of their own: subtitles stay on. Every other scene hides them (films 74-88; user review)
SCENE_MEDIA = {}  # JS scenes that draw real photos (film 6): {'scene-name': ('credit line', ['media/x.jpg', ...])}; listed as `uses` so LICENSES/credits keep them
ORIGINAL = {}  # film clips whose own field sound plays: {'v-tag#K': gain dB}; only after Scribe tags it as no music/speech (docs/SOUND.md)


def norm(w):
    w = unicodedata.normalize('NFC', w.lower())
    return re.sub(r'[^\w]', '', w)


def resolve(a):
    a = a.strip()
    m = re.match(r'^(S\d{3})(\$)?(?:\s+"([^"]+)")?\s*([+-][\d.]+)?$', a)
    if not m:
        raise SystemExit(f'bad anchor: {a}')
    sid, end, phrase, off = m.groups()
    s = S[sid]
    t = s['end'] if end else s['start']
    if phrase:
        ws = [norm(w.get('w') or w.get('text') or w.get('word', '')) for w in s['words']]
        ph = [norm(x) for x in phrase.split()]
        hit = next((i for i in range(len(ws)) if ws[i:i + len(ph)] == ph), None)
        if hit is None:
            raise SystemExit(f'{a}: phrase not found in {sid}: {" ".join(ws)[:200]}')
        t = s['words'][hit]['start']
    return round(t + float(off or 0), 3)


def asset(rel):
    """assets/<type>/el_NN with whatever extension exists (mp3/wav); falls back to the first file of that type."""
    base = ROOT / 'assets' / rel
    for ext in ('.mp3', '.wav'):
        if base.with_suffix(ext).exists():
            return f'../../assets/{rel}{ext}'
    alt = sorted(base.parent.glob('el_*'))
    if not alt:
        raise SystemExit(f'missing asset {rel}')
    return f'../../assets/{rel.rsplit("/", 1)[0]}/{alt[0].name}'


def lines(name):
    p = D / name
    if not p.exists():
        return []
    out = []
    for raw in p.read_text(encoding='utf-8').splitlines():
        raw = raw.split(' #', 1)[0].rstrip() if not raw.lstrip().startswith('#') else ''
        if raw.strip():
            out.append([x.strip() for x in raw.split('|')])
    return out


def shots():
    rows = lines('shots.txt')
    out = []
    for i, r in enumerate(rows):
        t0 = 0.0 if i == 0 else resolve(r[0])
        out.append({'t0': t0, 'src': r[1], 'caption': r[2] if len(r) > 2 else '', 'anchor': r[0]})
    for i, s in enumerate(out):
        s['t1'] = out[i + 1]['t0'] if i + 1 < len(out) else DUR
    # `pick:A, pick:B, vid:C` with captions `a ;; b ;; c`: split the span evenly, each cut on the nearest word onset
    onsets = sorted(w['start'] for s in S.values() for w in s['words'])
    res = []
    for s in out:
        srcs = [x.strip() for x in s['src'].split(',')]
        caps = [x.strip() for x in s['caption'].split(';;')]
        n = len(srcs)
        cuts = [s['t0']]
        for k in range(1, n):
            want = s['t0'] + (s['t1'] - s['t0']) * k / n
            near = [o for o in onsets if cuts[-1] + 1.5 < o < s['t1'] - 1.5]
            cuts.append(min(near, key=lambda o: abs(o - want)) if near else want)
        cuts.append(s['t1'])
        for k in range(n):
            res.append({'t0': cuts[k], 't1': cuts[k + 1], 'src': srcs[k], 'caption': caps[min(k, len(caps) - 1)], 'anchor': s['anchor'] + (f' [{k + 1}/{n}]' if n > 1 else '')})
    return res


def check():
    sh = shots(); seen = {}; warn = 0; vid_ranges = []
    for i, s in enumerate(sh):
        L = s['t1'] - s['t0']; kind = s['src'].split(':')[0]
        flag = ''
        if L <= 0.4:
            flag = '!! too short / out of order'
        elif kind in ('pick',) and L > 7.0:
            flag = '! long still'
        elif kind == 'vid' and L > 6.5:
            flag = '! long clip'
        key, _, tin = s['src'].partition('@')
        if kind in ('pick', 'vid'):  # the same file can sit under several search tags: compare the source id
            tag, _, k = key.split(':', 1)[1].partition('#')
            try:
                key = read(D / 'media' / 'candidates' / tag / 'candidates.json')['candidates'][int(k) - 1]['page']
            except (OSError, IndexError, ValueError, KeyError):
                flag += ' !! MISSING candidate'
            if kind == 'vid':  # several cuts from one long film are different shots; overlapping ranges are not
                t_in = float(tin or 0)
                for (pk, a, b) in [x for x in vid_ranges if x[0] == key]:
                    if t_in < b and a < t_in + L:
                        flag += ' !! OVERLAPS another cut of this film'
                vid_ranges.append((key, t_in, t_in + L))
                key = f'{key}@{t_in}'
        if key != 'card' and key in seen:
            flag += f' !! REPEAT of shot {seen[key]}'
        seen.setdefault(key, i)
        if flag:
            warn += 1
        print(f'{i:3d} {s["t0"]:8.2f} {L:5.1f}s {s["anchor"][:28]:28s} {s["src"][:30]:30s} {flag}')
    kinds = {}
    for s in sh:
        k = s['src'].split(':')[0]; kinds[k] = kinds.get(k, 0) + s['t1'] - s['t0']
    import dollcheck  # drawn-character budget (scripts/dollcheck.py): archival first
    warn += dollcheck.check(D, sh)
    import reviewcheck  # overlay text inside the frame, typing sound, firing sound (scripts/reviewcheck.py, film 76)
    warn += reviewcheck.check(D, sh)
    print({k: round(v) for k, v in kinds.items()}, f'total {DUR:.0f}s, {len(sh)} shots, {warn} warnings')


def durations():
    import importlib.util
    dur = {}
    for s in shots():
        k, _, name = s['src'].partition(':')
        if k in ('scene', 'map'):
            dur[name] = round(s['t1'] - s['t0'] + 0.25, 3)
    sc = {k: v for k, v in dur.items() if not k.startswith('m-')}
    write(D / 'scenes' / 'src' / 'durations.json', sc)
    spec = importlib.util.spec_from_file_location('write_maps', D / 'maps' / 'write_maps.py'); m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
    m.write({k: v for k, v in dur.items() if k.startswith('m-')})
    print(f'{len(sc)} scene durations, {len(dur) - len(sc)} map durations')


def apply(sound_only=False):
    import core as C
    proj = C.Project(JOB)
    anchors = proj.anchors()
    sh = shots()
    vids, picks = [], []
    for i, s in enumerate(sh):
        k, _, rest = s['src'].partition(':')
        c = {'id': f'V{i + 1:03d}', 'start': s['t0'], 'end': s['t1'], 'need': s['caption'], 'frame': round(s['t0'] * FPS)}
        c['anchor'] = anchors.anchor(s['t0']) if i else {'sentence': 'S001', 'edge': 'start', 'offset': -S['S001']['start']}
        c['end_anchor'] = anchors.anchor(s['t1'])
        if k == 'scene':
            c.update(src=f'media/scene-{rest}.mp4', kind='video', grade='none', credit=SCENECREDIT, caption=s['caption'], mute=True, **{'in': 0.0})
            if rest in SCENE_MEDIA:
                c.update(credit=f'{SCENECREDIT} · {SCENE_MEDIA[rest][0]}', uses=SCENE_MEDIA[rest][1])
            if rest not in SUBS_OVER:  # graphics with their own text: subtitles step aside (render.hide_under_text)
                c['hide_subtitles'] = True
        elif k == 'map':
            c.update(src=f'media/map-{rest}.mp4', kind='video', grade='none', credit=MAPCREDIT, caption=s['caption'], mute=True, bloom=True, **{'in': 0.0})
        elif k == 'card':
            c.update(src=None, kind='card')
        elif k in ('pick', 'vid'):
            tag, _, kk = rest.partition('#'); kk, _, tin = kk.partition('@')
            picks.append((c['id'], tag, int(kk), s['caption'], float(tin or 0), k == 'vid'))
            c.update(src=None, caption=s['caption'])
            if k == 'vid':
                c['mute'] = True
                if f'{tag}#{kk}' in ORIGINAL:  # real field sound (film 90: riveting under the factory line, instead of a generated SFX)
                    c.update(mute=False, original_audio=True, gain_db=ORIGINAL[f'{tag}#{kk}'])
        else:
            raise SystemExit(f'unknown src {s["src"]}')
        vids.append(c)
    ovs = []
    for j, r in enumerate(lines('overlays.txt')):
        a, b = [x.strip() for x in r[0].split('..')]
        t0, t1 = resolve(a), resolve(b)
        card = next((v for v in vids if v.get('kind') == 'card' and abs(v['start'] - t0) < 0.3), None)
        if card:  # a card overlay fills its whole card shot: ending early shows the bare black card
            t1 = card['end']
        props = json.loads(r[2]) if len(r) > 2 and r[2] else {}
        for it in props.get('items', []):  # stat items revealed on the word that reads them: "at": "S043 \"500.000\""
            if isinstance(it.get('at'), str):
                it['at'] = round(resolve(it['at']) - t0, 2)
        ovs.append({'id': f'O{j + 1:03d}', 'type': r[1], 'start': t0, 'end': t1, 'props': props,
                    'anchor': anchors.anchor(t0), 'end_anchor': anchors.anchor(t1), 'frame': round(t0 * FPS)})
    sfx, mus, fx, dips = [], [], [], []
    for j, r in enumerate(lines('sound.txt') + lines('sound_scenes.txt')):
        if r[1] == 'dip':  # key line: the music drops (or pauses, -40) under it, user guide rule 6 (assets/music/MOODS.md)
            a, b = [x.strip() for x in r[0].split('..')]
            dips.append([round(resolve(a), 3), round(resolve(b), 3), float(r[2]) if len(r) > 2 else -6.0])
        elif r[1].startswith('music/'):
            a, b = [x.strip() for x in r[0].split('..')]
            def _pt(x):
                return float(x[6:]) if x.startswith('START+') else resolve(x)
            t0, t1 = (0.0 if a == 'S001-start' else _pt(a)), (DUR if b == 'END' else _pt(b))
            mus.append({'id': f'M{len(mus) + 1:03d}', 'src': asset(r[1]), 'start': t0, 'end': t1, 'in': float(r[3]) if len(r) > 3 else 0, 'loop': False,
                        'gain_db': float(r[2]), 'fade_in': 2, 'fade_out': 2.5, 'duck': True, 'mood': r[1].split('/')[1],
                        'anchor': anchors.anchor(t0), 'end_anchor': anchors.anchor(t1), 'frame': round(t0 * FPS)})
        elif r[1].startswith('fx:'):  # fx:subscribe -> media overlay
            t0 = resolve(r[0])
            fx.append({'id': f'F{len(fx) + 1:03d}', 'type': 'media_overlay', 'start': t0, 'end': t0 + float(r[2]),
                       'params': {'src': f'media/{r[1][3:]}.mov', 'blend': 'normal', 'scale': 'cover', 'loop': False}, 'opacity': 1,
                       'anchor': anchors.anchor(t0), 'frame': round(t0 * FPS)})
        else:
            t0 = 0.05 if r[0].startswith('START') else resolve(r[0])
            if r[0].startswith('START+'):
                t0 = float(r[0][6:])
            dur = float(r[3]) if len(r) > 3 else 4.0
            c = {'id': f'X{len(sfx) + 1:03d}', 'src': asset(r[1]), 'start': t0, 'end': t0 + dur, 'gain_db': float(r[2]),
                 'label': r[1].split('/')[1], 'anchor': anchors.anchor(t0), 'frame': round(t0 * FPS)}
            if len(r) > 4 and r[4] == 'loop':
                c.update(loop=True, fade_out=2)
            sfx.append(c)

    for m in mus:
        m['dips'] = [d for d in dips if d[0] < m['end'] and d[1] > m['start']]

    def edit(tl):
        for tr in tl['tracks']:
            if tr['id'] == 'video' and not sound_only: tr['clips'] = vids
            if tr['id'] == 'overlay' and not sound_only: tr['clips'] = ovs
            if tr['id'] == 'sfx': tr['clips'] = sfx
            if tr['id'] == 'music': tr['clips'] = mus
        f = next((t for t in tl['tracks'] if t['id'] == 'fx'), None)
        if f is None:
            tl['tracks'].append({'id': 'fx', 'kind': 'fx', 'name': FXNAME, 'clips': fx})
        else:
            f['clips'] = fx
        tl['fx'] = {'subtitles': True, 'grain': True}
        tl['subtitle_style'] = {'font': 'military', 'size': 50, 'upper': True, 'stroke': 0, 'box': 0.62, 'box_pad': 16, 'box_color': '#0A0908', 'y': 0.868}
        if not sound_only:
            tl['credits'] = [x for x in tl.get('credits', []) if x.get('file', '').startswith('media/') and 'scene-' not in x['file'] and 'map-' not in x['file']]
        return f'{len(vids)} shots, {len(ovs)} overlays, {len(sfx)} sfx, {len(mus)} music, {len(fx)} fx'
    print(proj.transact(edit, who='agent', why='plan.py ' + ('sound' if sound_only else 'apply'))[0])
    if sound_only:
        return
    import doc  # media picks: download, credit, LICENSES row
    for slot, tag, k, cap, tin, isvid in picks:
        try:
            if isvid:
                doc.media_pick(JOB, slot, tag, k, cap, tin)
            else:
                doc.media_pick(JOB, slot, tag, k, cap)
        except Exception as e:  # noqa: BLE001
            print(f'!! {slot} {tag}#{k}: {e}')
    fix_photos()


def crop_box(im):
    """Bounding box (full-res pixels) of the photograph on a scanned print/caption sheet, or None if it fills the scan.
    Paper is bright and flat; the photo is the largest connected region of textured or dark 8x8 blocks."""
    import numpy as np
    sm = im.convert('L'); sm.thumbnail((480, 480))
    a = np.asarray(sm, dtype=float); bs = 8
    h, w = a.shape[0] // bs, a.shape[1] // bs
    blk = a[:h * bs, :w * bs].reshape(h, bs, w, bs).swapaxes(1, 2).reshape(h, w, bs * bs)
    photo = (blk.std(-1) > 10) | (blk.mean(-1) < 150)
    pad = np.pad(photo, 1).astype(int)
    nb = sum(pad[1 + dy:h + 1 + dy, 1 + dx:w + 1 + dx] for dy in (-1, 0, 1) for dx in (-1, 0, 1))
    photo = nb >= 6
    seen = np.zeros_like(photo); best = None
    for y in range(h):
        for x in range(w):
            if photo[y, x] and not seen[y, x]:
                st, comp = [(y, x)], []; seen[y, x] = True
                while st:
                    cy, cx = st.pop(); comp.append((cy, cx))
                    for ny, nx in ((cy + 1, cx), (cy - 1, cx), (cy, cx + 1), (cy, cx - 1)):
                        if 0 <= ny < h and 0 <= nx < w and photo[ny, nx] and not seen[ny, nx]:
                            seen[ny, nx] = True; st.append((ny, nx))
                if best is None or len(comp) > len(best):
                    best = comp
    if not best:
        return None
    ys, xs = [p[0] for p in best], [p[1] for p in best]
    y0, y1, x0, x1 = min(ys), max(ys) + 1, min(xs), max(xs) + 1
    if (y1 - y0) * (x1 - x0) > 0.88 * h * w or (y1 - y0) * (x1 - x0) < 0.12 * h * w:
        return None
    if not 0.4 < (x1 - x0) / (y1 - y0) < 2.6:  # a sliver (sky band, shoreline) is not the photo: film 89 cut a sub away
        return None
    fx, fy = im.width / (w * bs) * (a.shape[1] / (w * bs)) ** 0, im.height / (h * bs)
    fx = im.width / a.shape[1]; fy = im.height / a.shape[0]
    m = 0.012  # trim a hair inside the edge
    return (int((x0 * bs + m * w * bs) * fx), int((y0 * bs + m * h * bs) * fy), int((x1 * bs - m * w * bs) * fx), int((y1 * bs - m * h * bs) * fy))


def fix_photos():
    """Crop NARA prints out of their mounts and cap every still at 3200 px (renders faster, looks the same)."""
    from PIL import Image
    Image.MAX_IMAGE_PIXELS = None
    tl = read(D / 'timeline.json')
    done = set()
    for c in next(t for t in tl['tracks'] if t['id'] == 'video')['clips']:
        if c.get('kind') != 'photo' or not c.get('src') or c['src'] in done:
            continue
        done.add(c['src']); p = D / c['src']
        flag = p.with_suffix(p.suffix + '.fixed')
        if flag.exists() or not p.exists():
            continue
        im = Image.open(p); im.load(); im = im.convert('RGB')
        if 'catalog.archives.gov' in (c.get('page') or ''):
            box = crop_box(im)
            if box:
                im = im.crop(box); print(f'crop {c["id"]} {p.name} -> {im.width}x{im.height}')
        if max(im.size) > 3200:
            im.thumbnail((3200, 3200))
        im.save(p, quality=92) if p.suffix.lower() in ('.jpg', '.jpeg') else im.save(p)
        flag.write_text('ok')


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    {'check': check, 'durations': durations, 'apply': apply, 'sound': lambda: apply(True)}[sys.argv[1]]()
