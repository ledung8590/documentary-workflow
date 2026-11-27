"""Drawn scenes cast from one mould: the same diagram with other words, placeholder scenes, long runs without a real picture.

  PY scripts/templatecheck.py JOB        reads timeline.json and scenes/*.js, no rendering

Film 183 (2026-11-27, a Codex session, second draft): after the pace gate asked for 6-10 shots per minute the session filled
the film with 417 drawn scenes. 99 of them shared their code with other scenes and only the words and numbers differed (one
mould 20 times, others 16, 11, 11), 26 were placeholders titled "S018 時点" (a line with a dot, "moment of sentence 18"), and
from 29:21 on 55 of 56 shots in a row were dot-and-line diagrams. The gate said PASS. A mould repeated through a film is what
YouTube calls templated content, and it shows nothing of what the sentence says.
Measured on 28 finished films in evidence/: a code shape is used by at most 8 scenes (usually 1-3), no placeholder titles,
at most 18 drawn shots in a row.

Findings (level, id, message) for scripts/gate.py:
  !! scene-mould        one code shape (strings and numbers ignored) drawn by more than MAX_SAME scenes
  !! scene-placeholder  a scene whose visible text is a sentence id ("S018 時点", "S027 moment")
  !! drawn-run          more than MAX_RUN drawn scenes or maps in a row without a real photo or film cut
  !! scene-empty        more than 15 % of the drawn scenes are an almost blank page (measured on the rendered media/scene-*.mp4)
Scenes that only frame a picture file (prints, exhibits) are not counted as a mould: their picture differs.
The remedy is never a renamed copy: give the sentence its own picture (real photo or film first, a map with the real
positions, or a scene drawn for what this sentence says).
"""
import hashlib, json, re, sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

MAX_SAME = 8     # finished films: at most 8 (Akula), usually 1-3; film 183 had 20, 16, 11, 11
MAX_RUN = 25     # drawn shots in a row; finished films: at most 18; film 183 had 60
MIN_INK = 0.02   # share of the frame drawn on; finished films: median 17-20 % of the frame
MAX_BARE = 0.15  # share of drawn scenes under MIN_INK; finished films 0-8 %, film 183 third draft 38 %
STRING = re.compile(r"'[^'\n]*'|\"[^\"\n]*\"|`[^`]*`")
PICTURE = re.compile(r"['\"`][^'\"`\n]*\.(jpe?g|png|webp|mp4|mov)['\"`]", re.I)
# a title made of a sentence id and "moment" ('S311+0', 'S228 eighty' are timing anchors, not text on screen)
# or any title that begins with a sentence id ("S044 図解切替" = "diagram switch", "S147 要点": 16 were left after the first fix)
PLACEHOLDER = re.compile(r"['\"`]\s*S\d{3}\s*(の?時点|moment|point|Zeitpunkt|thời điểm)\s*['\"`]|\b(title|heading|label)[\"']?\s*:\s*['\"`]\s*S\d{3}\b[^'\"`\n]*['\"`]", re.I)


def video(tl):
    return next((t['clips'] for t in tl['tracks'] if t.get('id') == 'video'), [])


def base(c):
    return (c.get('src') or '').replace('\\', '/').split('/')[-1]


def shape(code):
    """The scene's code with every string and number taken out: two scenes with the same shape differ only in words and values."""
    s = re.sub(r'\d+(\.\d+)?', 'N', STRING.sub('S', code))
    return hashlib.md5(re.sub(r'\s+', '', s).encode()).hexdigest()[:10]


def stamp(t):
    return f'{int(t // 60)}:{int(t % 60):02d}'


def sources(d, clips):
    """{clip id: the scene's own code}. scenes/src/<name>.js when the film still has it; otherwise the built scenes/<name>.js
    without the drawing kit that build.py puts in front of every scene (the part all built scenes share)."""
    own, built = {}, {}
    for c in clips:
        b = base(c)
        if not b.startswith('scene-'):
            continue
        name = b[6:].rsplit('.', 1)[0] + '.js'
        for folder, into in (('scenes/src', own), ('scenes', built)):
            try:
                into[c['id']] = (Path(d) / folder / name).read_text(encoding='utf-8', errors='replace')
                break
            except OSError:
                pass
    if len(built) > 1:
        import os
        kit = len(os.path.commonprefix(list(built.values())))
        built = {k: v[kit:] for k, v in built.items()}
    return {**built, **own}


def check(d, tl):
    clips = video(tl)
    if not clips:
        return []
    codes = sources(d, clips)
    finds, moulds = [], defaultdict(list)
    run, longest = [], []
    for c in clips:
        b = base(c)
        if not b.startswith(('scene-', 'map-')):
            run = []
            continue
        code = codes.get(c['id'])
        if code and PICTURE.search(code):
            run = []      # a scene that frames a picture file (print, exhibit) shows a picture
            continue
        run.append(c)
        if len(run) > len(longest):
            longest = list(run)
        if not code:
            continue
        m = PLACEHOLDER.search(code)
        if m:
            finds.append(('!!', f'scene-placeholder:{c["id"]}', f'{c["id"]} at {stamp(c["start"])} ({b}) shows {m.group(0)}: a sentence id is not a picture of what the sentence says. '
                          'Replace the scene by a real photo, a film cut, a map with the real positions, or a scene drawn for this sentence'))
        moulds[shape(code)].append(c)
    for cs in sorted(moulds.values(), key=len, reverse=True):
        if len(cs) > MAX_SAME:
            finds.append(('!!', f'scene-mould:{cs[0]["id"]}', f'{len(cs)} scenes are the same drawing with other words and numbers (finished films: at most {MAX_SAME}): '
                          + ', '.join(c['id'] for c in cs[:14]) + (' ...' if len(cs) > 14 else '')
                          + f'. Keep at most {MAX_SAME} and give the others their own picture (real photo or film first, a map with the real positions, or a scene drawn for that sentence); '
                          'a renamed copy or a reshuffled copy of the same diagram is the same mould'))
    if len(longest) > MAX_RUN:
        finds.append(('!!', f'drawn-run:{longest[0]["id"]}', f'{len(longest)} drawn scenes in a row from {longest[0]["id"]} at {stamp(longest[0]["start"])} to {longest[-1]["id"]} at {stamp(longest[-1]["end"])} '
                      f'without one real photo or film cut (finished films: at most 18; limit {MAX_RUN}). Put real pictures of the ships, people and places named in these sentences into the stretch'))
    return finds + empty(d, clips)


W, H = 320, 180


def ink(path, at):
    """Share of the frame that is drawn on: pixels that differ from the page colour (the median). None when the frame cannot be read."""
    import subprocess
    import numpy as np
    r = subprocess.run(['ffmpeg', '-v', 'error', '-ss', f'{at:.2f}', '-i', str(path), '-frames:v', '1', '-vf', f'scale={W}:{H}',
                        '-f', 'rawvideo', '-pix_fmt', 'gray', '-'], capture_output=True)
    if len(r.stdout) != W * H:
        return None
    a = np.frombuffer(r.stdout, np.uint8).reshape(H, W).astype(int)[22:, :]   # the top strip holds the source label
    return float((abs(a - np.median(a)) > 28).mean())


def empty(d, clips):
    """!! scene-empty: too many drawn scenes whose rendered frame is almost a blank page (reads media/scene-*.mp4, cached in qa/ink.json).

    Film 183, third draft: the code shapes all differed (other variable names, a loop here and written out there), so the mould
    check passed, but 134 of 351 drawn scenes were two or three small circles on a line with a word under each: less than 2 % of
    the frame drawn on, nearly all after minute 20. Six finished films measured the same way: 0-8 % of their drawn scenes."""
    from concurrent.futures import ThreadPoolExecutor
    scenes = [c for c in clips if base(c).startswith('scene-') and (Path(d) / 'media' / base(c)).exists()]
    if len(scenes) < 20:
        return []
    cache_file = Path(d) / 'qa' / 'ink.json'
    try:
        cache = json.loads(cache_file.read_text(encoding='utf-8'))
    except (OSError, ValueError):
        cache = {}

    def one(c):
        p = Path(d) / 'media' / base(c)
        at = (c.get('in') or 0) + (c['end'] - c['start']) * 0.85    # near the end: everything has appeared
        st = p.stat()
        key = f'{base(c)}|{st.st_size}|{int(st.st_mtime)}|{at:.1f}'
        if key not in cache:
            try:
                cache[key] = ink(p, at)
            except Exception:
                cache[key] = None
        return key
    with ThreadPoolExecutor(8) as ex:
        keys = list(ex.map(one, scenes))
    try:
        cache_file.parent.mkdir(exist_ok=True)
        cache_file.write_text(json.dumps({k: cache[k] for k in set(keys)}), encoding='utf-8')
    except OSError:
        pass
    seen = [(c, cache[k]) for c, k in zip(scenes, keys) if cache[k] is not None]
    bare = [c for c, v in seen if v < MIN_INK]
    if not seen or len(bare) <= MAX_BARE * len(seen):
        return []
    return [('!!', f'scene-empty:{bare[0]["id"]}', f'{len(bare)} of {len(seen)} drawn scenes are an almost blank page (less than {MIN_INK:.0%} of the frame drawn on; '
             f'finished films: at most 8 % of the drawn scenes, limit {MAX_BARE:.0%}): ' + ', '.join(c['id'] for c in bare)
             + '. A few dots on a line with a word under each is not a picture of the sentence. Replace them with real photos or film of the ships, people and places '
             'the sentences name, maps with the real positions, or full analysis boards (K.board) and character scenes as in the first half of the film; '
             'making the same dots larger or adding a frame is not a remedy')]


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    from common import job_dir
    d = job_dir(sys.argv[1])
    found = check(d, json.loads((d / 'timeline.json').read_text(encoding='utf-8')))
    for lv, i, m in found:
        print(lv, i, m)
    print(f'{len(found)} finding(s)')
    sys.exit(1 if found else 0)
