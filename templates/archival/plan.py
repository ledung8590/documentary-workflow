"""Template: templates/archival/plan.py, copied into projects/<id>/ by `doc.py plan JOB`. Edit SUBS_OVER per film.

Build this film's picture, overlay, sfx and music tracks from the plan files (shots.txt, overlays.txt, sound.txt).

  PY plan.py check            resolve every anchor, print shot lengths, warnings (long stills, repeats, gaps)
  PY plan.py durations        write scene/map durations (scenes/src/durations.json, maps/*.json) from shot lengths
  PY plan.py apply            replace video/overlay/sfx/music clips in timeline.json (studio store), then pick media

Anchor syntax: `S012` sentence start · `S012 "word phrase"` first word of that phrase · `S012+1.5` / `S012 "x"-0.3` offset
· `S012$` sentence end. shots.txt:  ANCHOR | SRC | caption      SRC = scene:NAME · map:NAME · pick:TAG#K · vid:TAG#K@IN · card
  (looks: photos fill the frame; `pick:TAG#K+exhibit` hangs one as a mounted print on the paper, e.g. a document or small portrait)
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
LOOK = (read(D / 'brief.json') or {}).get('look', 'paper')  # assets/looks.json: paper | dark (one colour family per film, 2026-11-14)
CREDITS = {  # on-screen credit lines follow the script language
    'en': ('Terrain: AWS Terrain Tiles · Satellite: Sentinel-2 cloudless 2016 (EOX, CC BY 4.0) · Positions, arrows: schematic', 'Animated graphic (illustrative)', 'Effects'),
    'de': ('Gelände: AWS Terrain Tiles · Satellitenbild: Sentinel-2 cloudless 2016 (EOX, CC BY 4.0) · Positionen, Pfeile: schematisch', 'Animierte Grafik (schematisch)', 'Effekte'),
    'es': ('Relieve: AWS Terrain Tiles · Satélite: Sentinel-2 cloudless 2016 (EOX, CC BY 4.0) · Posiciones, flechas: esquemáticas', 'Gráfico animado (ilustrativo)', 'Efectos'),
    'vi': ('Địa hình: AWS Terrain Tiles · Vệ tinh: Sentinel-2 cloudless 2016 (EOX, CC BY 4.0) · Vị trí, mũi tên: minh hoạ', 'Đồ hoạ động (minh hoạ)', 'Hiệu ứng'),
    'fr': ('Relief : AWS Terrain Tiles · Satellite : Sentinel-2 cloudless 2016 (EOX, CC BY 4.0) · Positions, flèches : schématiques', 'Graphique animé (illustratif)', 'Effets'),
    'ja': ('地形: AWS Terrain Tiles · 衛星画像: Sentinel-2 cloudless 2016 (EOX, CC BY 4.0) · 位置・矢印は模式図', 'アニメーション図解(イメージ)', '効果'),
}
MAPCREDIT, SCENECREDIT, FXNAME = CREDITS.get(LANG, CREDITS['en'])
FLATMAP = {'en': 'Map: Natural Earth (public domain) · Positions, arrows: schematic', 'de': 'Karte: Natural Earth (gemeinfrei) · Positionen, Pfeile: schematisch',
           'es': 'Mapa: Natural Earth (dominio público) · Posiciones, flechas: esquemáticas', 'vi': 'Bản đồ: Natural Earth (phạm vi công cộng) · Vị trí, mũi tên: minh hoạ',
           'fr': 'Carte : Natural Earth (domaine public) · Positions, flèches : schématiques', 'ja': '地図: Natural Earth（パブリックドメイン）· 位置・矢印は模式図'}
if LOOK in ('paper', 'dark'):  # looks draw flat Natural Earth maps (maps/engine.html), not satellite imagery
    MAPCREDIT = FLATMAP.get(LANG, FLATMAP['en'])
INTRO_GAIN = -6.0  # opening music intro level (dB, after the bed levelling): about the voice's level before the first word
SUBS_OVER = set()  # scenes with no text of their own: subtitles stay on. Every other scene hides them (films 74-88; user review)
VID_ZOOM = {}  # {'v-tag#K': 1.2}: zoom a film in from the bottom-right to crop a logo off its top-left corner
SCENE_MEDIA = {}  # JS scenes that draw real photos (film 6): {'scene-name': ('credit line', ['media/x.jpg', ...])}; listed as `uses` so LICENSES/credits keep them
ORIGINAL = {}  # film clips whose own field sound plays: {'v-tag#K': gain dB}; only after Scribe tags it as no music/speech (docs/SOUND.md)


def norm(w):
    w = unicodedata.normalize('NFC', w.lower())
    return re.sub(r'[^\w]', '', w)


def resolve(a):
    a = a.strip()
    m = re.match(r'^(S\d{3,4})(\$)?(?:\s+"([^"]+)")?\s*([+-][\d.]+)?$', a)
    if not m:
        raise SystemExit(f'bad anchor: {a}')
    sid, end, phrase, off = m.groups()
    s = S[sid]
    t = s['end'] if end else s['start']
    if phrase:
        ws = [norm(w.get('w') or w.get('text') or w.get('word', '')) for w in s['words']]
        ph = [norm(x) for x in phrase.split()]
        hit = next((i for i in range(len(ws)) if ws[i:i + len(ph)] == ph), None)
        if hit is None and LANG == 'ja':  # no spaces: the phrase may start inside a word; interpolate within it
            joined, pos = ''.join(ws), ''.join(ph)
            at = joined.find(pos)
            if at >= 0:
                for i, w in enumerate(ws):
                    if at < len(w):
                        x = s['words'][i]; t = x['start'] + (x['end'] - x['start']) * at / max(1, len(w))
                        return round(t + float(off or 0), 3)
                    at -= len(w)
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
    part = __import__('os').environ.get('PLAN_PART')  # group agents check their own shots-X.txt / overlays-X.txt
    if part and name in ('shots.txt', 'overlays.txt'):
        name = name.replace('.txt', f'-{part}.txt')
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
        t0 = 0.0 if i == 0 and not __import__('os').environ.get('PLAN_PART') else resolve(r[0])  # a group part starts at its own anchor
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
        if kind == 'scene' and not (D / 'scenes' / 'src' / f"{s['src'].split(':', 1)[1]}.js").exists():
            flag += ' !! MISSING scene source'  # film 2026-11-16: e-zivil was planned but never written, the draft render crashed at the end
        if kind == 'map' and not (D / 'maps' / 'src' / f"{s['src'].split(':', 1)[1]}.json").exists():
            flag += ' !! MISSING map source'
        key, _, tin = s['src'].replace('+exhibit', '').partition('@')  # a mounted exhibit is the same candidate
        if kind in ('pick', 'vid'):  # the same file can sit under several search tags: compare the source id
            tag, _, k = key.split(':', 1)[1].partition('#')
            try:
                key = read(D / 'media' / 'candidates' / tag / 'candidates.json')['candidates'][int(k) - 1]['page']
            except (OSError, IndexError, ValueError, KeyError):
                flag += ' !! MISSING candidate'
            if kind == 'vid':  # several cuts from one long film are different shots; overlapping ranges are not
                t_in = float((tin or '0').rstrip('!'))
                for (pk, a, b) in [x for x in vid_ranges if x[0] == key]:
                    if t_in < b and a < t_in + L:
                        flag += ' !! OVERLAPS another cut of this film'
                vid_ranges.append((key, t_in, t_in + L))
                key = f'{key}@{t_in}'
        if key != 'card' and key in seen and not key.startswith(('scene:', 'map:')):  # a scene/map listed again continues after an inserted cut
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
    if LOOK in ('paper', 'dark'):  # 2026-11-14: one picture per sentence reads as a slideshow; arguments go on analysis boards
        run, worst = 0, (0, None)
        for s in sh:
            run = run + 1 if s['src'].startswith('pick:') else 0
            if run > worst[0]: worst = (run, s['anchor'])
        bd = sum(s['t1'] - s['t0'] for s in sh if s['src'].startswith('scene:bd-')); tot = sum(s['t1'] - s['t0'] for s in sh) or 1
        print(f'analysis boards (scene:bd-*): {bd:.0f}s of {tot:.0f}s ({bd / tot:.0%}); target 30-50 %; longest run of standalone photos {worst[0]}')
        if worst[0] >= 4:
            print(f'!! {worst[0]} standalone photos in a row (ending {worst[1]}): put some on an analysis board with what they prove (K.board, docs/SCENES.md)'); warn += 1
        if bd / tot < 0.25:
            print('!! analysis boards under 25 % of the film: analysis, comparison and cause/effect sentences go on K.board boards'); warn += 1
    v0 = S['S001']['start']
    has_intro = any(r[1].startswith('music/') and r[0].split('..')[0].strip().startswith('S001-') for r in lines('sound.txt'))
    if v0 > 1.0 and not has_intro and not lines('sound.txt'):
        print(f'!! the voice starts at {v0:.1f} s and sound.txt has no music: the opening is silent (plan.py apply adds the intro once a bed is placed)'); warn += 1
    warn += combat_check(sh)
    import reviewcheck  # overlay text inside the frame, typing sound, firing sound (scripts/reviewcheck.py, film 76)
    warn += reviewcheck.check(D, sh)
    import filmrepeat  # footage an earlier film already showed (scripts/filmrepeat.py, film 88)
    warn += filmrepeat.check(D, sh)
    print({k: round(v) for k, v in kinds.items()}, f'total {DUR:.0f}s, {len(sh)} shots, {warn} warnings')


def durations():
    import importlib.util
    dur, maps, starts = {}, set(), {}
    for s in shots():
        k, _, name = s['src'].partition(':')
        if k in ('scene', 'map'):
            starts.setdefault(name, round(s['t0'], 3))  # a name listed again after a film cut CONTINUES the scene (apply sets 'in'): one span from its first start
            dur[name] = round(s['t1'] - starts[name] + 0.25, 3)
            if k == 'map':
                maps.add(name)  # by shot kind, not name prefix (film 77 maps are m1-…, o-empire)
    sc = {k: v for k, v in dur.items() if k not in maps}
    st = {k: v for k, v in starts.items() if k not in maps}
    if __import__('os').environ.get('PLAN_PART'):  # group editors in parallel: merge into the other groups' entries, never overwrite them
        old = lambda n: read(D / 'scenes' / 'src' / n) if (D / 'scenes' / 'src' / n).exists() else {}
        sc = {**old('durations.json'), **sc}; st = {**old('starts.json'), **st}
        print(f'{len(sc)} scene durations (merged part)'); write(D / 'scenes' / 'src' / 'durations.json', sc); write(D / 'scenes' / 'src' / 'starts.json', st)
        return  # maps are written by the lead editor's full `plan.py durations`
    write(D / 'scenes' / 'src' / 'durations.json', sc)
    write(D / 'scenes' / 'src' / 'starts.json', st)  # build.py: @{S146 "word"} -> scene seconds
    spec = importlib.util.spec_from_file_location('write_maps', D / 'maps' / 'write_maps.py'); m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
    m.write({k: v for k, v in dur.items() if k in maps})
    print(f'{len(sc)} scene durations, {len(dur) - len(sc)} map durations')


LABELS = {'en': ('Photo', 'Film', 'Document', 'Map (schematic)', 'Map (satellite)', 'Diagram (shapes simplified)', 'Illustration', 'Reconstruction (generated)', 'Painting'),
          'de': ('Foto', 'Film', 'Dokument', 'Karte (schematisch)', 'Karte (Satellit)', 'Grafik (Formen vereinfacht)', 'Illustration', 'Rekonstruktion (generiert)', 'Gemälde'),
          'vi': ('Ảnh', 'Phim', 'Tư liệu', 'Bản đồ (minh hoạ)', 'Bản đồ (vệ tinh)', 'Đồ hoạ (hình giản lược)', 'Minh hoạ', 'Tái hiện (dựng lại)', 'Tranh'),
          'es': ('Foto', 'Película', 'Documento', 'Mapa (esquemático)', 'Mapa (satélite)', 'Gráfico (formas simplificadas)', 'Ilustración', 'Reconstrucción (generada)', 'Pintura'),
          'ja': ('写真', '映像', '史料', '地図（略図）', '地図（衛星）', '図解（形は略図）', '図解', '再現（生成）', '絵画')}


def source_label(k, rest, caption):
    """The 通史3 two-line source label's first line: what kind of picture this is, with its year when the caption has one."""
    L = LABELS.get(LANG, LABELS['en'])
    y = re.search(r'\b(1[5-9]\d\d|20[0-2]\d)\b', caption or ''); yr = f' ({y.group(1)})' if y else ''
    if k == 'map':
        spec = D / 'maps' / 'src' / f'{rest}.json'
        return L[4] if spec.exists() and json.loads(spec.read_text(encoding='utf-8')).get('base') == 'satellite' else L[3]
    if k == 'scene':
        if rest.startswith('r-'): return L[7]
        if rest.startswith('bd-'): return L[5]
        return L[6]
    if k == 'vid': return L[1] + yr
    if k == 'pick':
        if re.search(r'(?i)\b(memo|report|treaty|document|letter|page|newspaper|front page|order|telegram|record|minutes)\b', caption or ''): return L[2] + yr
        if re.search(r'(?i)\b(painting|lithograph|engraving|drawing|print)\b', caption or ''): return L[8] + yr
        return L[0] + yr
    return None


COMBAT = {  # words that narrate fighting (user 2026-11-14/15: "toàn ảnh tĩnh, ko hề có xung đột hay chiến đấu")
    'en': r"\b(attack(?:ed|s|ing)?|invad(?:ed|es|e|ing)|invasion|battle|battles|charge|fought|fighting|firefight|bomb(?:ed|ing)|shell(?:ed|ing)|"
          r"sank|sunk|torpedo(?:ed|es)?|strafing|ambush(?:ed)?|assault|offensive|shot down|opened fire|explod(?:ed|es)|"
          r"raid(?:ed|s)?|siege|stormed|landed on the beach|counterattack|massacre|casualties)\b",  # not war/strike/landing/bombers (Cold War, first strike, Moon landing, a bomber force)
    'de': r"\b(angriff|angriffe|angegriffen|schlacht|gefecht|kämpf\w*|bomb\w*|beschoss\w*|versenkt|sank|torpedier\w*|offensive|"
          r"sturm|stürmt\w*|landung|explodier\w*|feuer\w*|gefallen|verluste|überfall\w*|krieg\b)",
    'vi': r"(tấn công|đánh chiếm|trận|chiến đấu|giao tranh|ném bom|pháo kích|đánh chìm|ngư lôi|tập kích|đổ bộ|phản công|nổ súng|bắn hạ|thương vong|bao vây)",
    'es': r"\b(ataca\w*|ataque|invadi\w*|invasión|batalla|combat\w*|bombarde\w*|hundi\w*|torpede\w*|ofensiva|asalto|desembarco|explot\w*|bajas)",
    'ja': r"(攻撃|侵攻|会戦|海戦|戦闘|砲撃|爆撃|撃沈|雷撃|突撃|上陸|空襲|奇襲|反撃|戦死)",
}


def combat_check(sh):
    """Every sentence that narrates fighting shows fighting: a real film cut, or a moving scene with its own shot/blast events
    (scenes/events-NAME.txt, e.g. the w-* combat scenes in scenes/examples/combat). Stills, boards and maps alone are flagged
    (space-race film 2026-11-14, and again on the next film 2026-11-15)."""
    rx = re.compile(COMBAT.get(LANG, COMBAT['en']), re.I)
    moving = lambda s: s['src'].startswith('vid:') or (s['src'].startswith('scene:') and (
        (D / 'scenes' / f"events-{s['src'][6:]}.txt").exists() or s['src'][6:].startswith('w-')))
    bad = []
    ok = set((read(D / 'brief.json') or {}).get('combat_ok', []))  # sentences checked by hand: the word is not a fight ("pledged not to invade")
    for sid, s in S.items():
        if sid in ok:
            continue
        text = ' '.join(w.get('w') or w.get('word', '') for w in s['words'])
        m = rx.search(text)
        if not m:
            continue
        a, b = s['start'], s['end']
        near = [x for x in sh if x['t1'] > a - 1.5 and x['t0'] < b + 1.5]  # the fight may be shown just around the sentence
        if not any(moving(x) for x in near):
            bad.append(f'{sid} "{m.group(0)}"')
    for x in bad[:40]:
        print(f'!! {x}: the sentence narrates fighting but the picture is stills/boards/maps only: add a real combat film cut '
              f'(FIRE sound) or a moving combat scene with events (scenes/examples/combat); not a fight? add the id to brief "combat_ok"')
    if len(bad) > 40:
        print(f'!! ... and {len(bad) - 40} more combat sentences without a combat picture')
    return len(bad)


def pick_intro(first):
    """The opening intro bed: a different file for every film (user 2026-11-15: "thay đổi xoay vòng đỡ nhàm, thay hợp video").
    Mood = brief "intro_mood" or the mood of the film's first bed (music_plan picks it from the opening chapter's group);
    among that mood's files, the one used least often as an intro by earlier films (evidence/*/project/timeline.json), and
    never the same file as the first bed when another exists."""
    from collections import Counter
    mood = (read(D / 'brief.json') or {}).get('intro_mood') or first.get('mood') or 'milintro'
    files = sorted(x for x in (ROOT / 'assets' / 'music' / mood).glob('el_*') if x.suffix in ('.mp3', '.wav'))
    if not files:
        return first['src']
    used = Counter()
    for tl in (ROOT / 'evidence').glob('*/project/timeline.json'):
        try:
            for c in next(t for t in json.loads(tl.read_text(encoding='utf-8'))['tracks'] if t['id'] == 'music')['clips']:
                if str(c.get('mood', '')).endswith('-intro') or (c.get('duck') is False and c.get('start', 9) < 0.1):
                    used[Path(c['src']).name if Path(c['src']).parent.name == mood else ''] += 1
        except (OSError, ValueError, StopIteration, KeyError):
            pass
    others = [f for f in files if f.name != Path(first['src']).name] or files
    best = min(others, key=lambda f: (used[f.name], f.name))
    return f'../../assets/music/{mood}/{best.name}'


def apply(sound_only=False):
    import core as C
    proj = C.Project(JOB)
    anchors = proj.anchors()
    sh = shots()
    vids, picks = [], []
    first = {}  # scene/map listed again after an inserted film cut: continue it where the timeline is ('in'), not from its start
    for s in sh:
        if s['src'].split(':')[0] in ('scene', 'map'):
            first.setdefault(s['src'], s['t0'])
    for i, s in enumerate(sh):
        k, _, rest = s['src'].partition(':')
        c = {'id': f'V{i + 1:03d}', 'start': s['t0'], 'end': s['t1'], 'need': s['caption'], 'frame': round(s['t0'] * FPS)}
        c['anchor'] = anchors.anchor(s['t0']) if i else {'sentence': 'S001', 'edge': 'start', 'offset': -S['S001']['start']}
        c['end_anchor'] = anchors.anchor(s['t1'])
        if k == 'scene':
            c.update(src=f'media/scene-{rest}.mp4', kind='video', grade='none', credit=SCENECREDIT, caption=s['caption'], mute=True, **{'in': round(s['t0'] - first[s['src']], 3)})
            if LOOK in ('paper', 'dark'):  # the two-line label already says Diagram/Illustration: keep only the exhibits' sources (通史3)
                c['credit'] = ''
            if rest in SCENE_MEDIA:
                c.update(credit=(SCENE_MEDIA[rest][0] if LOOK in ('paper', 'dark') else f'{SCENECREDIT} · {SCENE_MEDIA[rest][0]}'), uses=SCENE_MEDIA[rest][1])
            if rest.startswith('r-'):  # reconstruction prints (generated, 通史3 再現): the label says what they are; subtitles run over them like the reference
                c['credit'] = ''
            if rest not in SUBS_OVER and not rest.startswith('r-'):  # graphics with their own text, boards included: subtitles step aside (render.hide_under_text); user 2026-11-14: labels + subtitles = the same words twice
                c['hide_subtitles'] = True
        elif k == 'map':
            c.update(src=f'media/map-{rest}.mp4', kind='video', grade='none', credit=MAPCREDIT, caption=s['caption'], mute=True, **{'in': round(s['t0'] - first[s['src']], 3)})
            spec = D / 'maps' / 'src' / f'{rest}.json'
            sat = spec.exists() and json.loads(spec.read_text(encoding='utf-8')).get('base') == 'satellite'
            if LOOK not in ('paper', 'dark') or sat:
                c['bloom'] = True  # glow belongs to the old satellite maps only
            c['hide_subtitles'] = True  # maps carry their own labels (user 2026-11-14)
            if sat:
                c['credit'] = CREDITS.get(LANG, CREDITS['en'])[0]  # the satellite/terrain credit
        elif k == 'card':
            c.update(src=None, kind='card')
        elif k in ('pick', 'vid'):
            if rest.endswith('+exhibit'):  # looks: a mounted print on the paper with its caption under it
                rest = rest[:-8]; c['exhibit'] = True
            tag, _, kk = rest.partition('#'); kk, _, tin = kk.partition('@')
            picks.append((c['id'], tag, int(kk), s['caption'], tin or '0', k == 'vid'))  # '@IN!' = exact in-point, no clean_in
            c.update(src=None, caption=s['caption'])
            if k == 'vid':
                c['mute'] = True
                if f'{tag}#{kk}' in VID_ZOOM:  # crop a broadcaster logo / burned-in corner off a film (render.Video 'zoom', anchored away from the top-left)
                    c['zoom'] = VID_ZOOM[f'{tag}#{kk}']
                if f'{tag}#{kk}' in ORIGINAL:  # real field sound (film 90: riveting under the factory line, instead of a generated SFX)
                    c.update(mute=False, original_audio=True, gain_db=ORIGINAL[f'{tag}#{kk}'])
        else:
            raise SystemExit(f'unknown src {s["src"]}')
        c['label'] = source_label(k, rest, s['caption'])
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
                        'gain_db': float(r[2]), 'fade_in': 0.4 if t0 < 0.1 else 2, 'fade_out': 2.5, 'duck': True, 'mood': r[1].split('/')[1],  # the opening bed comes in at once (通史3: music at 0.4 s)
                        'anchor': anchors.anchor(t0), 'end_anchor': anchors.anchor(t1), 'frame': round(t0 * FPS)})
            for kv in (r[4].split() if len(r) > 4 else []):  # e.g. `fade_out=5 noduck` (opening bed fading out smoothly under the first words)
                if kv == 'noduck': mus[-1]['duck'] = False
                elif '=' in kv: k_, v_ = kv.split('=', 1); mus[-1][k_] = float(v_)
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

    # opening music intro (通史3 opening, user 2026-11-14/15: "câm đầu" twice): before the first word the bed plays alone at about
    # the voice's level, then fades out over ~6 s under the first words, not ducked. Added automatically unless sound.txt has one.
    v0 = S['S001']['start']
    if mus and v0 > 0.8 and not any(m['start'] < 0.1 and m.get('duck') is False for m in mus):
        first = min(mus, key=lambda m: m['start'])
        src = pick_intro(first)
        mus.append({'id': f'M{len(mus) + 1:03d}', 'src': src, 'start': 0.0, 'end': round(v0 + 5.4, 3), 'in': 0, 'loop': False,
                    'gain_db': INTRO_GAIN, 'fade_in': 0.4, 'fade_out': 6.0, 'duck': False, 'mood': first.get('mood', 'intro') + '-intro',
                    'anchor': anchors.anchor(0.0), 'end_anchor': anchors.anchor(v0 + 5.4), 'frame': 0})
        print(f'opening music intro: {src.split("music/")[-1]} 0-{v0 + 5.4:.1f} s, fades under the first words')
    for m in mus:
        m['dips'] = [d for d in dips if d[0] < m['end'] and d[1] > m['start']]

    def edit(tl):
        for tr in tl['tracks']:
            if tr['id'] == 'video' and not sound_only: tr['clips'] = vids
            if tr['id'] == 'overlay': tr['clips'] = ovs  # overlays need no downloads: `plan.py sound` refreshes them too
            if tr['id'] == 'sfx': tr['clips'] = sfx
            if tr['id'] == 'music': tr['clips'] = mus
        f = next((t for t in tl['tracks'] if t['id'] == 'fx'), None)
        if f is None:
            tl['tracks'].append({'id': 'fx', 'kind': 'fx', 'name': FXNAME, 'clips': fx})
        else:
            f['clips'] = fx
        tl['fx'] = {'subtitles': True, 'grain': True}
        tl['subtitle_style'] = {'font': 'military', 'size': 50, 'upper': True, 'stroke': 0, 'box': 0.62, 'box_pad': 16, 'box_color': '#0A0908', 'y': 0.868}
        if LOOK in ('paper', 'dark'):  # book-case serif on a full-width band in the look's colours (render.subtitle_layer)
            tl['subtitle_style'] = {'font': 'subsans', 'size': 46, 'upper': False, 'stroke': 0, 'box': 0, 'y': 0.875}  # bold gothic like the reference; cream band only over paper
        tl['look'] = LOOK if LOOK in ('paper', 'dark') else None
        tl['duck'] = {'release': 2000, 'ratio': 4}  # music stays down between sentences, rises only in real pauses (render.mix_graph, 2026-11-14)
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
                doc.media_pick(JOB, slot, tag, k, cap, float(tin.rstrip('!')), exact=tin.endswith('!'))
            else:
                doc.media_pick(JOB, slot, tag, k, cap)
        except Exception as e:  # noqa: BLE001
            print(f'!! {slot} {tag}#{k}: {e}')
    fix_photos()
    auto_exhibit()


def auto_exhibit():
    """Look films: a portrait photo would become a print on BLACK (render.is_print), which leaves the paper look; hang it as a
    mounted exhibit on the paper instead. Landscape/square photos fill the frame even when small (user 2026-11-14: 'sao ảnh bị
    thu nhỏ'). An exhibit under a callout or lower third drops its own caption (the two texts overlapped)."""
    if LOOK not in ('paper', 'dark'):
        return
    import core as C
    from PIL import Image
    Image.MAX_IMAGE_PIXELS = None
    def edit(tl):
        n = 0
        for c in next(t for t in tl['tracks'] if t['id'] == 'video')['clips']:
            p = D / (c.get('src') or '')
            if c.get('kind') == 'photo' and c.get('src') and p.exists() and not c.get('exhibit') and not str(c.get('id', '')).startswith('#'):
                w, h = Image.open(p).size
                if w / h < 0.95:
                    c['exhibit'] = True; n += 1
            if c.get('exhibit'):
                c['exhibit_nocap'] = any(o['type'] in ('callout', 'lower_third') and o['start'] < c['end'] - 0.2 and c['start'] < o['end'] - 0.2
                                         for o in next(t for t in tl['tracks'] if t['id'] == 'overlay')['clips'])
        return f'{n} portrait photos hung as exhibits'
    print(C.Project(JOB).transact(edit, who='agent', why='plan.py auto_exhibit')[0])


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
