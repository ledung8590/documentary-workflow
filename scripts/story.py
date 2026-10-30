"""Story mode (/gentruyen, docs/STORY_MODE.md): a fiction story narrated over the user's own images (e.g. AI images
made per ~8 s of an earlier narration). No archival search, no fact-check, no "(illustrative)" labels.

Input (input/README.md), either
  input/<name>.txt + input/<name>/ (images) [+ input/<name>.srt] [+ input/<name>*scene*.txt prompts]
  input/<name>/ with script.txt (or one script .txt) + images [+ one .srt] [+ *scene*/*prompt* .txt]
The .srt here is the timing the images were made for (one image per seconds_per_image of it), not narration.

`build()` fills timeline.json after `assemble`: one video clip per image anchored to the word where its part of the
story starts, title and chapter cards, music beds per chapter (mood from the sentences' emotions) and measured card
SFX. Everything is anchored to sentences/words, so a later voice change retimes it.
"""
import difflib, json, re, unicodedata
from pathlib import Path

import numpy as np

IMG_EXT = ('.png', '.jpg', '.jpeg', '.webp')
ROOT = Path(__file__).resolve().parents[1]


def natural(p):
    return [int(x) if x.isdigit() else x.lower() for x in re.split(r'(\d+)', Path(p).name)]


def is_prompts(p):
    return bool(re.search(r'scene|prompt', Path(p).stem, re.I))


def images_in(d):
    return sorted([p for p in Path(d).iterdir() if p.suffix.lower() in IMG_EXT], key=natural) if Path(d).is_dir() else []


def discover(folder):
    """[{name, script, images, srt, prompts}] story jobs in input/. Folders starting with '_' are skipped."""
    folder = Path(folder); out = []
    for d in sorted(p for p in folder.iterdir() if p.is_dir() and not p.name.startswith('_')):
        imgs = images_in(d)
        if len(imgs) < 2:
            continue
        side = folder / f'{d.name}.txt'  # layout A: files beside the image folder
        if side.exists():
            script = side
            srt = folder / f'{d.name}.srt'
            prompts = next((p for p in sorted(folder.glob(f'{glob_escape(d.name)}*.txt')) if is_prompts(p)), None)
        else:  # layout B: everything inside the folder
            txts = [p for p in d.glob('*.txt') if not is_prompts(p) and p.name.lower() != 'readme.txt']
            script = next((p for p in txts if p.stem.lower() == 'script'), txts[0] if len(txts) == 1 else None)
            if script is None:
                print(f'skip {d.name}: no script.txt (or several .txt and none named script.txt)'); continue
            srts = sorted(d.glob('*.srt')); srt = srts[0] if len(srts) == 1 else None
            prompts = next((p for p in sorted(d.glob('*.txt')) if is_prompts(p)), None)
        out.append({'name': d.name, 'script': script, 'images': d, 'srt': srt if srt and srt.exists() else None,
                    'prompts': prompts, 'count': len(imgs)})
    return out


def glob_escape(s):
    return re.sub(r'([\[\]*?])', r'[\1]', s)


def load_prompts(p):
    """{1-based scene number: prompt} from JSON lines ({"scenes 12": "..."}) or one prompt per line."""
    if not p:
        return {}
    out = {}
    for k, line in enumerate([l for l in Path(p).read_text(encoding='utf-8-sig').split('\n') if l.strip()], 1):
        try:
            obj = json.loads(line)
            key, val = next(iter(obj.items()))
            m = re.search(r'\d+', key); out[int(m.group()) if m else k] = str(val)
        except (json.JSONDecodeError, StopIteration, AttributeError):
            out[k] = line.strip()
    return out


def norm(w):
    w = unicodedata.normalize('NFC', w.lower())
    return re.sub(r'[^\w]', '', w)


def voice_tokens(timing):
    """[(token, sentence id, word index)] of the assembled voice, in order."""
    out = []
    for sid, s in sorted(timing.items(), key=lambda kv: kv[1]['start']):
        for i, w in enumerate(s.get('words') or []):
            t = norm(w.get('w', ''))
            if t:
                out.append((t, sid, i))
    return out


def srt_tokens(srt):
    """[(token, time)] with each cue's words spread over the cue by length."""
    import render as R
    out = []
    for a, b, text in R.read_srt(srt):
        ws = [w for w in text.split() if norm(w)]
        tot = sum(len(w) for w in ws) or 1; acc = 0
        for w in ws:
            out.append((norm(w), a + (b - a) * acc / tot)); acc += len(w)
    return out


def align(a, b):
    """Monotonic map index in a -> index in b for two token lists of the same story (difflib matching blocks,
    linear in between)."""
    sm = difflib.SequenceMatcher(None, a, b, autojunk=False)
    pts = [(m.a, m.b) for m in sm.get_matching_blocks() if m.size] + [(len(a), len(b))]
    xs = np.array([0] + [p[0] for p in pts], float); ys = np.array([0] + [p[1] for p in pts], float)
    return lambda i: int(min(len(b) - 1, max(0, round(float(np.interp(i, xs, ys))))))


def image_starts(n, timing, srt=None, seconds_per_image=None):
    """Voice token index where each of the n images starts. With the image SRT: image k covers
    [k * spi, (k+1) * spi) of that SRT's time, its first word is found in the new voice by word alignment.
    Without: images are spread evenly over the voice's words."""
    vt = voice_tokens(timing)
    if not vt:
        raise SystemExit('no word timings: run assemble first')
    if srt:
        st = srt_tokens(srt)
        # images are made per whole seconds of that SRT (8 s for Whisk scenes): 3097 s / 388 = 7.98 -> 8.0
        spi = seconds_per_image or (round(st[-1][1] / n * 2) / 2 if st else 8.0)
        to_voice = align([t for t, _ in st], [t for t, _, _ in vt])
        times = [t for _, t in st]
        idx = [to_voice(int(np.searchsorted(times, k * spi))) for k in range(n)]
    else:
        idx = [round(k * len(vt) / n) for k in range(n)]
    for k in range(1, n):  # strictly increasing: two images never start on the same word
        idx[k] = max(idx[k], idx[k - 1] + 1)
    return vt, [min(i, len(vt) - 1) for i in idx]


MOODS = {'tense': 'tension', 'urgent': 'tension', 'dramatic': 'suspense', 'hook': 'suspense', 'somber': 'somber',
         'sad': 'somber', 'reflective': 'nostalgia', 'calm': 'nostalgia', 'neutral': 'noir', 'hopeful': 'resolve',
         'triumphant': 'resolve', 'warm': 'nostalgia'}
ALT = {'tension': ['tension', 'suspense', 'noir'], 'nostalgia': ['nostalgia', 'somber'], 'noir': ['noir', 'suspense']}


def _loudest(p, length, src_in=0.0, win=0.4, sr=22050, _cache={}):
    """Loudest 400 ms RMS (dBFS) of a file section: card SFX gains are set from this (measured, not guessed)."""
    from common import load_audio
    key = (str(p), length, src_in)
    if key not in _cache:
        x = load_audio(p, sr)[int(src_in * sr):int((src_in + length) * sr)].astype(np.float64)
        n = int(win * sr); e = np.convolve(x * x, np.ones(n) / n, mode='valid') if len(x) > n else [np.mean(x * x)]
        _cache[key] = 10 * np.log10(max(np.max(e), 1e-12))
    return _cache[key]


def build(d, tl, brief, timing, sents, chapters, log=print):
    """Fill tl (in place) for story mode. d: project dir. Returns a summary string."""
    import shutil
    import timeline as TL
    from common import load_audio
    st = brief.get('story') or {}
    imgs = images_in(st['images'])
    if not imgs:
        raise SystemExit(f'no images in {st.get("images")}')
    prompts = load_prompts(st.get('prompts'))
    vt, starts = image_starts(len(imgs), timing, st.get('srt'), st.get('seconds_per_image'))
    grade = st.get('grade', 'archival'); fps = tl['fps']
    by_id = {s['id']: s for s in sents}; order = [s['id'] for s in sents]
    T = lambda a: TL.resolve(a, timing)
    track = {t['id']: t for t in tl['tracks']}

    # pictures: one clip per image, anchored to its first word
    (d / 'media' / 'scenes').mkdir(parents=True, exist_ok=True)
    vids = []
    for k, (img, vi) in enumerate(zip(imgs, starts)):
        dst = d / 'media' / 'scenes' / f'{k + 1:03d}{img.suffix.lower()}'
        if not dst.exists() or dst.stat().st_size != img.stat().st_size:
            shutil.copy2(img, dst)
        _, sid, wi = vt[vi]
        a = {'sentence': sid, 'edge': 'start', 'offset': -0.12} if wi == 0 else {'sentence': sid, 'word': wi, 'offset': -0.05}
        if k == 0:
            a = {'sentence': sid, 'edge': 'start', 'offset': -99.0}  # covers the lead-in
        v = {'id': f'V{k + 1:03d}', 'start': 0.0, 'end': 0.0, 'src': f'media/scenes/{dst.name}', 'kind': 'photo', 'grade': grade,
             'anchor': a, 'motion': {'type': 'pull' if k % 3 == 2 else 'push', 'dx': 0.04 if k % 2 else -0.04}}
        if prompts.get(k + 1):
            v['need'] = prompts[k + 1][:200]
        vids.append(v)
    for a, b in zip(vids, vids[1:]):
        a['end_anchor'] = b['anchor']
    vids[-1]['end_anchor'] = {'sentence': order[-1], 'edge': 'end', 'offset': 3.0}
    vids[0]['transition_in'] = {'type': 'dip', 'dur': 1.2}
    track['video']['clips'] = vids

    # cards: title after the first paragraph (if early), a chapter card in each chapter's pause
    ov = []

    def card(kind, a, length, **props):
        ov.append({'id': f'O{len(ov) + 1:03d}', 'type': kind, 'start': 0.0, 'end': length, 'anchor': a, 'props': props})
    first_par = [s for s in sents if s.get('paragraph', 0) == sents[0].get('paragraph', 0)]
    title_a = None
    if brief.get('title') and st.get('title_card', True):
        last = first_par[-1]['id'] if timing[first_par[-1]['id']]['end'] < 120 else order[0]
        title_a = {'sentence': last, 'edge': 'end', 'offset': 0.35}
        card('title_card', title_a, 5.0, text=brief['title'].upper())
    chap_a = []
    for n, ch in enumerate([c for c in chapters if c.get('sentence') in by_id], 1):
        i = order.index(ch['sentence'])
        a = {'sentence': order[i - 1], 'edge': 'end', 'offset': 0.3} if i > 0 else {'sentence': ch['sentence'], 'edge': 'start', 'offset': -3.6}
        gap = timing[ch['sentence']]['start'] - (timing[order[i - 1]]['end'] if i > 0 else 0)
        card('chapter', a, round(max(2.4, min(3.4, gap - 0.4)), 2), n=n, title=ch['title'])
        chap_a.append((a, ch['sentence']))
    track['overlay']['clips'] = ov

    # music: a bed per section (cold open, title, each chapter), tiled with 2 s crossfades, ~13 dB under the voice
    moods = sorted(p.name for p in (ROOT / 'assets' / 'music').iterdir() if p.is_dir() and any(p.glob('*.mp3')))
    music = []
    if moods and st.get('music', True):
        bounds = [(0.0, order[0])]
        if title_a:
            bounds.append((T(title_a) - 1.0, None))
        bounds += [(T(a) - 0.5, sid) for a, sid in chap_a]
        bounds.sort(key=lambda b: b[0])
        prev_mood = None; k = 0; lens = {}
        for i, (t0, sid) in enumerate(bounds):
            t1 = bounds[i + 1][0] + 1.5 if i + 1 < len(bounds) else tl['duration']
            if t1 - t0 < 4:
                continue
            j0 = order.index(sid) if sid else 0
            j1 = order.index(bounds[i + 1][1]) if i + 1 < len(bounds) and bounds[i + 1][1] else len(order)
            emo = [by_id[x].get('emotion', 'neutral') for x in order[j0:max(j1, j0 + 1)]]
            mood = MOODS.get(max(set(emo), key=emo.count), 'noir')
            if i == 0:
                mood = 'suspense' if 'suspense' in moods else mood
            if mood == prev_mood:  # the same bed twice in a row: take its alternative
                mood = next((m for m in ALT.get(mood, []) if m != prev_mood and m in moods), mood)
            if mood not in moods:
                mood = moods[0]
            prev_mood = mood
            src = sorted((ROOT / 'assets' / 'music' / mood).glob('*.mp3'))[0]
            if src not in lens:
                lens[src] = len(load_audio(src, 22050)) / 22050
            seg, t, first = lens[src] - 6.0, t0, True
            while t < t1 - 0.5:
                e = min(t + seg, t1); k += 1
                anchor_sid = max((x for x in order if timing[x]['start'] <= t), key=lambda x: timing[x]['start'], default=order[0])
                music.append({'id': f'M{k:03d}', 'src': '../../' + src.relative_to(ROOT).as_posix(), 'start': round(t, 3), 'end': round(e, 3),
                              'in': 0.0 if first else 3.0, 'fade_in': 1.0 if i == 0 and first else 2.0, 'fade_out': 2.0, 'gain_db': -7.0,
                              'mood': mood, 'anchor': {'sentence': anchor_sid, 'edge': 'start', 'offset': round(t - timing[anchor_sid]['start'], 3)}})
                first = False
                if e >= t1:
                    break
                t = e - 2.0
    track['music']['clips'] = music

    # card SFX at measured levels (loudest 400 ms in the premix): whoosh in, hit as the card lands, sub drop
    fx = []

    def sfx(name, a, length, level, f='01', **kw):
        p = ROOT / 'assets' / 'sfx' / name / f'el_{f}.mp3'
        if not p.exists():
            p = next(iter(sorted((ROOT / 'assets' / 'sfx' / name).glob('*.mp3'))), None)
            if p is None:
                return
        c = {'id': f'X{len(fx) + 1:03d}', 'src': '../../' + p.relative_to(ROOT).as_posix(), 'start': 0.0, 'end': length,
             'gain_db': round(level - _loudest(p, length, kw.get('in', 0.0)), 1), 'anchor': a}
        c.update(kw); fx.append(c)
    sh = lambda a, dt: {**a, 'offset': round(a['offset'] + dt, 3)}
    if st.get('card_sfx', True):
        if title_a:
            sfx('riser', sh(title_a, -3.3), 3.0, -21)
            sfx('titlehit', sh(title_a, 0.1), 5.0, -8, fade_out=1.5)
            sfx('subdrop', sh(title_a, 0.1), 3.0, -15, fade_out=1.0)
            sfx('whooshdark', sh(title_a, 0.65), 1.5, -20)
        for n, (a, _) in enumerate(chap_a, 1):
            sfx('whooshdark', sh(a, -0.55), 1.5, -19)
            sfx('chapterhit', sh(a, 0.05), 3.0, -11, f='01' if n % 2 else '02', fade_out=0.8)
            sfx('subdrop', sh(a, 0.05), 3.0, -19, fade_out=1.0)
    track['sfx']['clips'] = fx

    tl['fx'] = {'grain': True, 'subtitles': True}
    tl['language'] = brief.get('language') or tl.get('language') or 'en'
    if brief.get('title'):
        tl['title'] = brief['title']
    moved, orphan, loose = TL.retime(tl, timing)
    msg = (f'{len(vids)} images ({"aligned to " + Path(st["srt"]).name if st.get("srt") else "spread evenly"}), '
           f'{len(ov)} cards, {len(music)} music tiles, {len(fx)} card sfx; orphans {orphan}')
    log(msg)
    return msg
