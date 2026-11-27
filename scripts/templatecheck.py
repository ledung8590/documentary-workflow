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
STRING = re.compile(r"'[^'\n]*'|\"[^\"\n]*\"|`[^`]*`")
PICTURE = re.compile(r"['\"`][^'\"`\n]*\.(jpe?g|png|webp|mp4|mov)['\"`]", re.I)
# a title made of a sentence id and "moment" ('S311+0', 'S228 eighty' are timing anchors, not text on screen)
PLACEHOLDER = re.compile(r"['\"`]\s*S\d{3}\s*(の?時点|moment|point|Zeitpunkt|thời điểm)\s*['\"`]", re.I)


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
    return finds


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    from common import job_dir
    d = job_dir(sys.argv[1])
    found = check(d, json.loads((d / 'timeline.json').read_text(encoding='utf-8')))
    for lv, i, m in found:
        print(lv, i, m)
    print(f'{len(found)} finding(s)')
    sys.exit(1 if found else 0)
