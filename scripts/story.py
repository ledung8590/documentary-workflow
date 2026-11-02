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
import difflib, json, re, subprocess, unicodedata
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


# music beds by emotion (assets/music/MOODS.md): drum-free beds under narration. The user heard "lộc cộc" drum beds under
# whole chapters and music far under the voice on story 89 (2026-11-02): drums only as a short accent on urgent passages.
MOODS = {'tense': 'darkdrone', 'urgent': 'warstrings', 'dramatic': 'darkdrone', 'hook': 'darkdrone', 'somber': 'somber',
         'sad': 'lament', 'reflective': 'nostalgia', 'calm': 'europe1870', 'neutral': 'strategy', 'hopeful': 'resolve',
         'triumphant': 'resolve', 'warm': 'nostalgia'}
ALT = {'darkdrone': ['strategy', 'europe1870'], 'strategy': ['europe1870', 'darkdrone'], 'europe1870': ['strategy', 'darkdrone'],
       'warstrings': ['darkdrone', 'strategy'], 'somber': ['lament', 'nostalgia'], 'lament': ['somber', 'nostalgia'],
       'nostalgia': ['somber', 'europe1870'], 'resolve': ['nostalgia', 'europe1870']}
DRUM_BED, DRUM_MAX, DRUM_GAP = 'tension', 70.0, 300.0   # a drum accent: ≤70 s, on an urgent/dramatic passage, ≥5 min apart
BED_MAX = 112.0      # one pass of a ~120 s file at most, then the bed changes (never loop a file for minutes)
EMO_GAIN = {'urgent': 2.5, 'dramatic': 2.0, 'tense': 1.5, 'hook': 1.5, 'question': 0.5, 'neutral': 0.0, 'triumphant': 1.0,
            'hopeful': 0.0, 'somber': -0.5, 'sad': -0.5, 'calm': -1.0, 'reflective': -1.5, 'warm': -1.0}  # music follows the voice: up in tension, down in reflection
MIN_RUN = 35.0       # an emotion run shorter than this joins its neighbour (no bed changes every few sentences)
MUSIC_UNDER = 11.0   # neutral narration bed: dB under the voice (LUFS over speech); tense beds come up to BED_GAP_MIN
BED_GAP_MIN, BED_GAP_MAX = 9.0, 13.5    # ducked music sits this many dB under the voice (measured; 13-15 dB sounded like a bare reading)


def _speech_level(x, sr, floor=25.0):
    """Median 400 ms RMS (dB) over the active part of a signal (frames within `floor` dB of its loudest)."""
    n, h = int(0.4 * sr), int(0.1 * sr)
    if len(x) < n:
        return -120.0
    e = np.array([np.mean(x[i:i + n].astype(np.float64) ** 2) for i in range(0, len(x) - n, h)])
    db = 10 * np.log10(np.maximum(e, 1e-12))
    return float(np.median(db[db > db.max() - floor]))


def _lufs_m(path):
    """Momentary loudness (LUFS, 10 values/s) of a file, from ffmpeg's ebur128 filter."""
    import re, subprocess
    o = subprocess.run(['ffmpeg', '-hide_banner', '-i', str(path), '-af', 'ebur128=metadata=1,ametadata=print:key=lavfi.r128.M',
                        '-f', 'null', '-'], capture_output=True, text=True).stderr
    return np.array([float(x) for x in re.findall(r'lavfi.r128.M=(-?[\d.]+)', o)])


def _level_music(d, tl, log):
    """Level EACH bed against the voice it plays under (perceived loudness, momentary LUFS over the bed's speech),
    so no bed comes closer than BED_GAP_MIN dB: a film-wide average of 8.6 dB still had tense beds 4.7 dB under the voice
    on story 89 ("nhạc to hơn voice"). Target gap per bed = MUSIC_UNDER - its emotion offset (EMO_GAIN), clamped."""
    import tempfile
    import render
    clips = next(t for t in tl['tracks'] if t['id'] == 'music')['clips']
    if not clips:
        return None
    with tempfile.TemporaryDirectory() as tmp:
        pv, pm = Path(tmp) / 'premix_v.wav', Path(tmp) / 'premix_m.wav'
        render.premix(d, tl, pv, only={'voice'}); render.premix(d, tl, pm, only={'music'})
        V, M = _lufs_m(pv), _lufs_m(pm)
    k = min(len(V), len(M)); V, M = V[:k], M[:k]; sp = V > -40
    before, after = [], []
    for c in clips:
        a, b = int(c['start'] * 10) + 20, int(c['end'] * 10) - 20     # skip the crossfades
        w = slice(max(0, a), min(k, b)); s = sp[w]
        if s.sum() < 30:
            continue
        g = float(np.median(V[w][s]) - np.median(M[w][s]))
        want = float(np.clip(MUSIC_UNDER - EMO_GAIN.get(c.get('emotion'), 0.0), BED_GAP_MIN, BED_GAP_MAX))
        c['gain_db'] = round(c['gain_db'] + g - want, 1); before.append(g); after.append(want)
    log(f'music: per-bed levelling, gaps under the voice were {min(before):.1f}-{max(before):.1f} dB '
        f'(median {np.median(before):.1f}), now {min(after):.1f}-{max(after):.1f} dB (LUFS, over speech)')
    return float(np.median(after))


def _clipped(p, _cache={}):
    """Percent of samples at full scale (|x| > 0.97): ElevenLabs SFX often come hard-clipped and crackle at any gain."""
    if str(p) not in _cache:
        from common import load_audio
        _cache[str(p)] = float((np.abs(load_audio(p, 22050)) > 0.97).mean() * 100)
    return _cache[str(p)]


def _lufs(p, length=None, src_in=0.0, _cache={}):
    """Integrated loudness (LUFS) of a file, or of the section that actually plays (src_in .. src_in + length)."""
    key = (str(p), length, src_in)
    if key not in _cache:
        cut = ['-ss', f'{src_in:.3f}'] + (['-t', f'{length:.3f}'] if length else [])
        o = subprocess.run(['ffmpeg', '-hide_banner', '-nostats', *cut, '-i', str(p), '-af', 'ebur128', '-f', 'null', '-'],
                           capture_output=True, text=True, encoding='utf-8', errors='replace').stderr
        v = re.findall(r'I:\s+(-?[\d.]+) LUFS', o)
        _cache[key] = float(v[-1]) if v else -70.0
    return _cache[key]


END_WORDS = {'vi': ('CẢM ƠN CÁC BẠN ĐÃ XEM', 'Xem tiếp những câu chuyện khác của kênh'),
             'en': ('THANKS FOR WATCHING', 'More stories from the channel'),
             'es': ('GRACIAS POR VER', 'Más historias del canal'), 'de': ('DANKE FÜRS ZUSEHEN', 'Weitere Geschichten vom Kanal')}
SUB_WORDS = {'vi': 'đăng ký', 'en': 'subscribe', 'es': 'suscr', 'de': 'abonn'}   # the narration's subscribe call
CHANNEL_WORDS = {'vi': 'kênh', 'en': 'channel', 'es': 'canal', 'de': 'kanal'}     # fallback: the welcome / sign-off


def end_screen_image(d, bg_img, lang):
    """20 s end screen: the last picture blurred and dark, a thank-you line, and outlines sized and placed like YouTube's own
    end-screen elements (two video/playlist slots 34.1 % of the width, a subscribe circle 16.6 %), so the user drags them on
    and they cover the outlines (story 89: my slots were 35 % / 10 % and did not match)."""
    from PIL import Image, ImageDraw, ImageEnhance, ImageFilter
    import render as R
    W, H = 1920, 1080
    im = Image.open(bg_img).convert('L').convert('RGB').resize((W, H))
    im = ImageEnhance.Brightness(im.filter(ImageFilter.GaussianBlur(14))).enhance(0.36)
    d_ = ImageDraw.Draw(im, 'RGBA'); t1, t2 = END_WORDS.get(lang, END_WORDS['en'])
    f = R.font('head', 72); d_.text(((W - R.text_w(d_, t1, f)) / 2, 90), t1, font=f, fill=(236, 230, 220))
    fs = R.font('body', 34); d_.text(((W - R.text_w(d_, t2, fs)) / 2, 192), t2, font=fs, fill=(205, 198, 188))
    vw = round(W * 0.341); vh = round(vw * 9 / 16); y0 = 290
    for x in (round(W * 0.08), W - round(W * 0.08) - vw):
        d_.rounded_rectangle((x, y0, x + vw, y0 + vh), radius=12, outline=(236, 230, 220, 210), width=4, fill=(0, 0, 0, 90))
    r = round(W * 0.166 / 2); cy = y0 + vh + 40 + r
    d_.ellipse((W / 2 - r, cy - r, W / 2 + r, cy + r), outline=(200, 40, 40, 230), width=5, fill=(0, 0, 0, 90))
    out = d / 'media' / 'endscreen.png'; im.save(out)
    return out


def subscribe_scene(d, lang, log=print):
    """media/scene-subscribe.mov (alpha) in the film's language, rendered once per project (docs/SCENES.md)."""
    import subprocess
    out = d / 'media' / 'scene-subscribe.mov'
    if not out.exists():
        log(f'rendering the subscribe overlay ({lang})')
        subprocess.run(['node', str(ROOT / 'scripts' / 'jsscene.mjs'), str(ROOT / 'scenes' / 'subscribe.js'), str(out), '--alpha',
                        '--lang', lang if lang in ('vi', 'en', 'es', 'de') else 'en'], check=True, cwd=ROOT, timeout=900)
    return out


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
    # sound before picture: ~2.4 s of black under ambience before the first image fades in (story.cold_black: false = off)
    if st.get('cold_black', True) and timing[order[0]]['start'] > 2.0:
        from PIL import Image
        blk = d / 'media' / 'black.png'
        if not blk.exists():
            Image.new('RGB', (1920, 1080), (0, 0, 0)).save(blk)
        cut = {'sentence': order[0], 'edge': 'start', 'offset': -1.0}
        vids.insert(0, {'id': 'V000', 'start': 0.0, 'end': 0.0, 'src': 'media/black.png', 'kind': 'photo', 'grade': 'archival',
                        'motion': {'type': 'none'}, 'anchor': {'sentence': order[0], 'edge': 'start', 'offset': -99.0}, 'end_anchor': cut})
        vids[1]['anchor'] = cut; vids[1]['transition_in'] = {'type': 'dip', 'dur': 1.0}
    # 20 s end screen after the last picture (YouTube end-screen slots drawn in), every story; story.end_screen: false = off
    lang = (brief.get('language') or 'en')[:2]
    if st.get('end_screen', True):
        last = order[-1]; t_end = timing[last]['end'] + 3.0
        end_screen_image(d, imgs[-1], lang)
        vids.append({'id': f'V{len(vids) + 1:03d}', 'start': round(t_end, 3), 'end': round(t_end + 20.0, 3), 'src': 'media/endscreen.png',
                     'kind': 'photo', 'grade': grade, 'motion': {'type': 'none'}, 'transition_in': {'type': 'dip', 'dur': 1.0},
                     'anchor': {'sentence': last, 'edge': 'end', 'offset': 3.0}, 'end_anchor': {'sentence': last, 'edge': 'end', 'offset': 23.0}})
        tl['duration'] = round(max(tl['duration'], t_end + 20.0), 3)
    track['video']['clips'] = vids

    # cards: title after the first paragraph (if early), a chapter card in each chapter's pause
    ov = []

    def card(kind, a, length, **props):
        ov.append({'id': f'O{len(ov) + 1:03d}', 'type': kind, 'start': 0.0, 'end': length, 'anchor': a, 'props': props})
    first_par = [s for s in sents if s.get('paragraph', 0) == sents[0].get('paragraph', 0)]
    title_a = None; title_img = None
    if brief.get('title') and st.get('title_card', True):
        last = st.get('title_after') if st.get('title_after') in by_id else (first_par[-1]['id'] if timing[first_par[-1]['id']]['end'] < 120 else order[0])
        title_a = {'sentence': last, 'edge': 'end', 'offset': 0.35}
        card('title_card', title_a, 5.0, text=brief['title'].upper())
        ti = d / st['title_image'] if st.get('title_image') else None   # story.title_image: a symbol/prop shot made for the title
        if ti and ti.exists():
            ov[-1]['props'].update(background='scrim', scrim=0.25, y=105)   # title text in the dark top third, over the picture
            title_img = (ti.relative_to(d).as_posix(), title_a)
    chap_a = []
    for n, ch in enumerate([c for c in chapters if c.get('sentence') in by_id], 1):
        i = order.index(ch['sentence'])
        a = {'sentence': order[i - 1], 'edge': 'end', 'offset': 0.3} if i > 0 else {'sentence': ch['sentence'], 'edge': 'start', 'offset': -3.6}
        gap = timing[ch['sentence']]['start'] - (timing[order[i - 1]]['end'] if i > 0 else 0)
        card('chapter', a, round(max(2.4, min(3.4, gap - 0.4)), 2), n=n, title=ch['title'])
        chap_a.append((a, ch['sentence']))
    track['overlay']['clips'] = ov

    # music: drum-free beds per section (cold open, title, each chapter), each at most one file pass, 2 s crossfades, measured 9 dB under the voice
    moods = sorted(p.name for p in (ROOT / 'assets' / 'music').iterdir() if p.is_dir() and any(p.glob('*.mp3')))
    music = []
    if moods and st.get('music', True):
        bounds = [(0.0, order[0])]
        if title_a:
            bounds.append((T(title_a) - 1.0, None))
        bounds += [(T(a) - 0.5, sid) for a, sid in chap_a]
        bounds.sort(key=lambda b: b[0])
        lens, used, level = {}, {}, {}
        prev_src, last_drum = None, -1e9
        vi = (brief.get('language') or '').startswith('vi')
        moods_map = {**MOODS, **(st.get('moods') or {})}   # brief story.moods: a genre's own beds (e.g. espionage)
        alt_map = {**ALT, **(st.get('alt') or {})}
        drums = st.get('drum_accent', True)

        def emotions(a, b):
            return [by_id[x].get('emotion', 'neutral') for x in order if timing[x]['start'] < b and timing[x]['end'] > a] or ['neutral']

        def pick(mood):
            """Least-used file of the mood (or its alternatives) that is not the bed just played."""
            cands = [mood] + alt_map.get(mood, [])
            if not vi:
                cands = [m for m in cands if m != 'nostalgia'] or ['somber']  # bamboo flute: Vietnamese/Asian stories only
            for m in cands:
                fs = [f for f in sorted((ROOT / 'assets' / 'music' / m).glob('*.mp3')) if f != prev_src] if m in moods else []
                if fs:
                    return m, min(fs, key=lambda f: used.get(f, 0))
            return mood, prev_src

        def place(t, e, mood, src, emo='neutral'):
            nonlocal prev_src
            if src not in lens:
                lens[src] = len(load_audio(src, 22050)) / 22050
                level[src] = _speech_level(load_audio(src, 16000), 16000, floor=30.0)
            k = len(music) + 1
            anchor_sid = max((x for x in order if timing[x]['start'] <= t), key=lambda x: timing[x]['start'], default=order[0])
            music.append({'id': f'M{k:03d}', 'src': '../../' + src.relative_to(ROOT).as_posix(), 'start': round(t, 3),
                          'end': round(min(e, t + lens[src] - 1.0), 3), 'in': 0.0, 'fade_in': 1.0 if not music else 2.5, 'fade_out': 2.5,
                          'gain_db': round(-30.0 - level[src] + EMO_GAIN.get(emo, 0.0), 1),  # equal loudness + the scene's emotion; _level_music sets the offset
                          'mood': mood, 'emotion': emo, 'anchor': {'sentence': anchor_sid, 'edge': 'start', 'offset': round(t - timing[anchor_sid]['start'], 3)}})
            used[src] = used.get(src, 0) + 1; prev_src = src

        def runs(t0, t1):
            """[(start, end, top emotion)] inside a section: sentences grouped by the bed their emotion asks for, short runs merged."""
            ids = [x for x in order if timing[x]['start'] >= t0 - 0.5 and timing[x]['start'] < t1]
            out = []
            for x in ids:
                e = by_id[x].get('emotion', 'neutral'); m = moods_map.get(e, 'strategy')
                a = timing[x]['start'] - 0.6
                if out and out[-1][3] == m:
                    out[-1][1] = timing[x]['end']; out[-1][2].append(e)
                else:
                    out.append([a, timing[x]['end'], [e], m])
            merged = []
            for r in out:
                if merged and (r[1] - r[0] < MIN_RUN or merged[-1][1] - merged[-1][0] < MIN_RUN):
                    merged[-1][1] = r[1]; merged[-1][2] += r[2]
                    merged[-1][3] = moods_map.get(max(set(merged[-1][2]), key=merged[-1][2].count), 'strategy')
                else:
                    merged.append(r)
            if not merged:
                return [(t0, t1, 'neutral')]
            merged[0][0] = t0; merged[-1][1] = t1
            for a, b in zip(merged, merged[1:]):
                a[1] = b[0]
            return [(a, b, max(set(es), key=es.count)) for a, b, es, _ in merged]

        plan = [p for p in st.get('music_plan') or [] if p.get('sentence') in timing]
        if plan:  # brief story.music_plan: [{sentence, mood, emotion, drums?}], each bed from its sentence to the next entry
            plan.sort(key=lambda p: timing[p['sentence']]['start'])
            for i, p in enumerate(plan):
                a = 0.0 if i == 0 else timing[p['sentence']]['start'] - 0.6
                b = timing[plan[i + 1]['sentence']]['start'] - 0.6 + 2.0 if i + 1 < len(plan) else tl['duration']
                emo = p.get('emotion', 'neutral')
                if p.get('drums') and DRUM_BED in moods and b - a > DRUM_MAX:
                    src = sorted((ROOT / 'assets' / 'music' / DRUM_BED).glob('*.mp3'))[0]
                    place(a, a + DRUM_MAX, DRUM_BED, src, emo); a += DRUM_MAX - 2.0
                n = max(1, int(np.ceil((b - a) / BED_MAX))); seg = (b - a) / n
                for j in range(n):
                    s0 = a + j * seg; s1 = b if j == n - 1 else s0 + seg + 2.0
                    mood, src = pick(p['mood'])
                    place(s0, s1, mood, src, emo)
            bounds = []
        for i, (t0, sid) in enumerate(bounds):
            t1 = bounds[i + 1][0] + 1.5 if i + 1 < len(bounds) else tl['duration']
            if t1 - t0 < 4:
                continue
            for r0, r1, top in runs(t0, t1):
                n = max(1, int(np.ceil((r1 - r0) / BED_MAX))); seg = (r1 - r0) / n   # each bed at most one file pass
                for j in range(n):
                    a = r0 + j * seg; b = r1 + 2.0 if j == n - 1 else a + seg + 2.0    # 2 s crossfade into the next bed
                    emo = emotions(a, b); hot = sum(e in ('urgent', 'dramatic') for e in emo) / len(emo)
                    if drums and hot >= 0.5 and a - last_drum >= DRUM_GAP and DRUM_BED in moods and b - a > DRUM_MAX + 20:
                        src = sorted((ROOT / 'assets' / 'music' / DRUM_BED).glob('*.mp3'))[0]
                        place(a, a + DRUM_MAX, DRUM_BED, src, top); last_drum = a        # a short drum accent, then strings again
                        a += DRUM_MAX - 2.0
                    mood, src = pick(moods_map.get(top, 'strategy'))
                    place(a, b, mood, src, top)
    track['music']['clips'] = music
    if music:
        try:
            _level_music(d, tl, log)
        except Exception as e:  # noqa: BLE001  (a failed measurement must not lose the build; studio gains stay adjustable)
            log(f'!! music level not measured ({e}); check the music against the voice by ear')

    # card SFX at measured levels (loudest 400 ms in the premix): whoosh in, hit as the card lands, sub drop
    fx = []

    def sfx(name, a, length, level, f='01', **kw):
        p = ROOT / 'assets' / 'sfx' / name / f'el_{f}.mp3'
        if not p.exists():
            p = next(iter(sorted((ROOT / 'assets' / 'sfx' / name).glob('el_*.*'))), None)   # some are .wav (whoosh)
            if p is None:
                return
        if _clipped(p) > 1.0:  # hard-clipped files crackle ("4:18 fx lỗi rè rè", story 51): take the cleanest of the type
            best = min((q for q in (ROOT / 'assets' / 'sfx' / name).glob('el_*.*') if q.suffix in ('.mp3', '.wav')), key=_clipped)
            if _clipped(best) < _clipped(p):
                p = best
            if _clipped(p) > 1.0:
                log(f'!! sfx {name}/{p.name} is {_clipped(p):.1f} % clipped (crackles): regenerate it')
        c = {'id': f'X{len(fx) + 1:03d}', 'src': '../../' + p.relative_to(ROOT).as_posix(), 'start': 0.0, 'end': length,
             'gain_db': round(level - _lufs(p, length, kw.get('in', 0.0)), 1), 'anchor': a}
        c.update(kw); fx.append(c)
    sh = lambda a, dt: {**a, 'offset': round(a['offset'] + dt, 3)}
    # Voice and SFX both in LUFS (integrated voice vs the SFX section that plays): card hits 3 dB under the voice, riser
    # 4, whoosh/drop 6. Story 89 had hits 7-10 dB OVER the voice ("fx cũng bị to hơn"); story 51 then had them 13-18 dB
    # under it, inaudible ("v006 thiếu fx"), because the voice was a median RMS and each SFX its loudest 400 ms.
    VI = _lufs(d / 'voice' / 'voice.wav')
    if st.get('card_sfx', True):
        if title_a:
            sfx('riser', sh(title_a, -3.3), 3.0, VI - 4)
            sfx('titlehit', sh(title_a, 0.1), 5.0, VI - 3, fade_out=1.5)
            sfx('subdrop', sh(title_a, 0.1), 3.0, VI - 6, fade_out=1.0)
            sfx('whooshdark', sh(title_a, 0.65), 1.5, VI - 6)
        for n, (a, _) in enumerate(chap_a, 1):
            sfx('whooshdark', sh(a, -0.55), 1.5, VI - 6)
            sfx('chapterhit', sh(a, 0.05), 3.0, VI - 3, f='01' if n % 2 else '02', fade_out=0.8)
            sfx('subdrop', sh(a, 0.05), 3.0, VI - 6, fade_out=1.0)
        log(f'card sfx: voice {VI:.1f} LUFS; hits 3 dB, riser 4 dB, whoosh/drop 6 dB under it (LUFS of the part that plays)')
    # subscribe call in the narration -> animated button, cursor click, SUBSCRIBED, bell, with their SFX (memory rule, every film)
    sub_at = None
    if st.get('subscribe', True):
        key = SUB_WORDS.get(lang, 'subscribe')
        for sid in order:
            ws = [norm(w.get('w', '')) for w in timing[sid].get('words') or []]
            k = next((i for i in range(len(ws)) if ' '.join(ws[i:i + len(key.split())]).startswith(norm(key.split()[0])) and
                      (len(key.split()) == 1 or ws[i + 1:i + 2] == [norm(key.split()[1])])), None)
            if k is not None:
                sub_at = (sid, k); break
        if not sub_at:   # no explicit subscribe call: the channel mention in the welcome (first 10 %) or the sign-off (last 5 %)
            ch = CHANNEL_WORDS.get(lang, 'channel'); n = len(order)
            for sid in order[:max(1, n // 10)] + order[-max(1, n // 20):]:
                ws = [norm(w.get('w', '')) for w in timing[sid].get('words') or []]
                if ch in ws:
                    sub_at = (sid, ws.index(ch)); key = ch; break
    if sub_at:
        subscribe_scene(d, lang, log)
        if 'fx' not in track:
            tl['tracks'].append({'id': 'fx', 'kind': 'fx', 'name': 'Hiệu ứng', 'clips': []}); track['fx'] = tl['tracks'][-1]
        fxc = track['fx']['clips']; fxc[:] = [c for c in fxc if c.get('label') != 'subscribe']
        ids = {x.get('id') for t in tl['tracks'] for x in t['clips']}
        a = {'sentence': sub_at[0], 'word': sub_at[1], 'offset': -1.3}       # first click lands on the word
        fxc.append({'id': next(f'F{k:03d}' for k in range(1, 999) if f'F{k:03d}' not in ids), 'type': 'media_overlay', 'label': 'subscribe',
                    'start': 0.0, 'end': 4.2, 'params': {'src': 'media/scene-subscribe.mov', 'blend': 'normal'}, 'anchor': a})
        for name, at, under in (('whoosh', 0.0, 6), ('mouseclick', 1.27, 5), ('subscribed', 1.3, 4), ('mouseclick', 2.42, 5), ('notifybell', 2.45, 4)):
            sfx(name, sh(a, at), 1.5, VI - under, fade_out=0.4)
        log(f'subscribe overlay on "{key}" in {sub_at[0]}')
    if title_img:
        if 'fx' not in track:
            tl['tracks'].append({'id': 'fx', 'kind': 'fx', 'name': 'Hiệu ứng', 'clips': []}); track['fx'] = tl['tracks'][-1]
        fxc = track['fx']['clips']; fxc[:] = [c for c in fxc if c.get('label') != 'title image']
        ids = {x.get('id') for t in tl['tracks'] for x in t['clips']}
        fxc.append({'id': next(f'F{k:03d}' for k in range(1, 999) if f'F{k:03d}' not in ids), 'type': 'media_overlay', 'label': 'title image',
                    'start': 0.0, 'end': 5.5, 'fade_in': 0.5, 'fade_out': 0.5, 'params': {'src': title_img[0], 'blend': 'normal'},
                    'anchor': sh(title_img[1], -0.2)})
    # story SFX on words (brief story.word_sfx: [{sentence, word, sfx, f?, under, length, offset?}]): gunshots, blasts, planes
    # on the exact word, `under` dB under the voice in LUFS of the part that plays; kept across story rebuilds
    for e in st.get('word_sfx') or []:
        ws = (timing.get(e['sentence']) or {}).get('words') or []
        i = next((k for k, w in enumerate(ws) if norm(w['w']).startswith(norm(e['word']))), None)
        if i is None:
            log(f'!! word_sfx: "{e["word"]}" not in {e["sentence"]}'); continue
        sfx(e['sfx'], {'sentence': e['sentence'], 'word': i, 'offset': e.get('offset', 0.0)}, e.get('length', 2.5),
            VI - e.get('under', 8), f=e.get('f', '01'), fade_out=e.get('fade_out', 0.4))
    if st.get('cold_black', True) and timing[order[0]]['start'] > 2.0:   # the ambience that plays over the black opening
        first_txt = ' '.join(by_id[x]['text'] for x in order[:4]).lower()
        amb = st.get('open_ambience') or ('rainroof' if any(w in first_txt for w in ('mưa', 'rain', 'lluvia', 'regen')) else 'wind')
        # alone over black, so clearly audible: 8 dB under the voice, from 3 s into the file (wind/el_02 is 9 dB quieter
        # in its first 3 s: story 51 measured -44 LUFS over the black at VI - 18, "tôi ko hề nghe thấy tiếng gió nào"),
        # then out over the first words (2 s fade)
        sfx(amb, {'sentence': order[0], 'edge': 'start', 'offset': round(-timing[order[0]]['start'], 3)},
            round(timing[order[0]]['start'] + 2.0, 2), VI - 8, fade_in=0.6, fade_out=2.0, **{'in': 3.0})
    track['sfx']['clips'] = fx

    # "Phim cũ nhẹ" over the whole film, every story (user rule 2026-11-02); brief story.old_film: false turns it off
    if st.get('old_film', True):
        from render_fx import EFFECT_PRESETS
        label, typ, params = next(p for p in EFFECT_PRESETS if p[0] == 'Phim cũ nhẹ')
        if 'fx' not in track:
            tl['tracks'].append({'id': 'fx', 'kind': 'fx', 'name': 'Hiệu ứng', 'clips': []}); track['fx'] = tl['tracks'][-1]
        fxc = track['fx']['clips']
        c = next((c for c in fxc if c.get('type') == typ and c.get('start', 0) <= 0.5), None)
        if c is None:
            ids = {x.get('id') for t in tl['tracks'] for x in t['clips']}
            c = {'id': next(f'F{k:03d}' for k in range(1, 999) if f'F{k:03d}' not in ids), 'type': typ, 'label': label,
                 'params': dict(params), 'opacity': 1, 'fade_in': 0.3, 'fade_out': 0.3}
            fxc.insert(0, c)
        c.pop('anchor', None); c['start'] = 0.0; c['end'] = round(tl['duration'], 3)

    tl['fx'] = {'grain': True, 'subtitles': True}
    tl['language'] = brief.get('language') or tl.get('language') or 'en'
    if brief.get('title'):
        tl['title'] = brief['title']
    moved, orphan, loose = TL.retime(tl, timing)
    msg = (f'{len(vids)} images ({"aligned to " + Path(st["srt"]).name if st.get("srt") else "spread evenly"}), '
           f'{len(ov)} cards, {len(music)} music tiles, {len(fx)} card sfx; orphans {orphan}')
    log(msg)
    return msg
