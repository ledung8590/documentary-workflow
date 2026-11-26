"""Picture pace of an archival film: no drawn scene held over a long stretch of narration.

  PY scripts/pacecheck.py JOB            cuts per minute, long shots, and scenes that stop moving (reads timeline.json)
  PY scripts/pacecheck.py JOB --fast     without the frame measurement

Film 183 (2026-11-26, a Codex session): 77 shots for 54 minutes, half of them longer than 35 s, one scene of 160 s. The user:
"toàn kiểu 1 cảnh xuyên suốt voice dài ... js hết vẽ rùi mà vẫn ko thấy chuyển cảnh khác ... 2 nhân vật nhảy lên xuống lặp lại
thì khác gì nhau". One scene stood under eight sentences that each say something else, so the picture no longer followed the
voice, and the gate still said PASS. Measured on the nine finished films in evidence/: 6-10 shots per minute, median shot 5-8 s,
longest shot 22-47 s, at most 2 % of the shots over 30 s. Film 183: 1.4 per minute, median 35 s, 1,100 s of scenes standing still.

Findings (level, id, message) for scripts/gate.py:
  !! pace-slow      fewer than MIN_PER_MIN shots per minute over the whole film
  !! shot-long      a shot longer than MAX_SHOT, or more than LONG_SHARE of the shots longer than LONG
  !! scene-frozen   a drawn scene or map that shows no change for more than FROZEN seconds (a loop of bobbing figures is no change:
                    the measure compares small grey frames STEP seconds apart)
The remedy is never to stretch or loop the scene: cut the stretch into shots that each show what their sentence says.
"""
import io, json, subprocess, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

MIN_PER_MIN = 5.0     # finished films: 5.9-10.0 (the 2026-11 films); 183 had 1.4
MAX_SHOT = 40.0       # seconds; finished films: longest 22-47
LONG, LONG_SHARE = 30.0, 0.03
FROZEN = 12.0         # seconds a scene may stand without any change (finished films: boards hold 10-12 s to be read; 1-2 scenes per film go over)
STEP, MOVE = 2.0, 0.35   # frame spacing and the mean grey difference (0-255, 320x180) that counts as a change
MIN_SCENE = 12.0      # shorter scenes are not measured


def video(tl):
    return next((t['clips'] for t in tl['tracks'] if t.get('id') == 'video'), [])


def drawn(c):
    s = (c.get('src') or '').replace('\\', '/').split('/')[-1]
    return s.startswith(('scene-', 'map-'))


def frame(src, at):
    from PIL import Image
    out = subprocess.run(['ffmpeg', '-v', 'error', '-ss', f'{at:.2f}', '-i', str(src), '-frames:v', '1', '-vf', 'scale=320:180', '-f', 'image2pipe',
                          '-vcodec', 'png', '-'], capture_output=True, timeout=60).stdout
    return Image.open(io.BytesIO(out)).convert('L') if out else None


def longest_still(src, start, dur):
    """Longest stretch (seconds) of the clip without a change between frames STEP apart."""
    from PIL import ImageChops, ImageStat
    prev, run, best, t = None, 0.0, 0.0, 0.0
    while t < dur - 0.2:
        f = frame(src, start + t)
        if f is None:
            break
        if prev is not None:
            if ImageStat.Stat(ImageChops.difference(f, prev)).mean[0] > MOVE:
                run = 0.0
            else:
                run += STEP; best = max(best, run)
        prev = f; t += STEP
    return best


def frozen(d, clips):
    """[(clip, seconds still)] for drawn scenes; measurements are cached in qa/pace.json by file, in-point, length and mtime."""
    cache_p = Path(d) / 'qa' / 'pace.json'
    try:
        cache = json.loads(cache_p.read_text(encoding='utf-8'))
    except (OSError, ValueError):
        cache = {}
    out, new = [], {}
    for c in clips:
        dur = c['end'] - c['start']
        src = Path(d) / (c.get('src') or '')
        if not drawn(c) or dur < MIN_SCENE or not src.exists():
            continue
        key = f"{c['src']}|{c.get('in') or 0:.2f}|{dur:.2f}|{int(src.stat().st_mtime)}"
        still = cache.get(key)
        if still is None:
            still = longest_still(src, c.get('in') or 0, dur)
        new[key] = still
        if still > FROZEN:
            out.append((c, still))
    try:
        cache_p.parent.mkdir(exist_ok=True); cache_p.write_text(json.dumps(new, indent=1), encoding='utf-8')
    except OSError:
        pass
    return out


def stamp(t):
    return f'{int(t // 60)}:{int(t % 60):02d}'


def check(d, tl, frames=True):
    clips = video(tl)
    total = tl.get('duration') or (clips[-1]['end'] if clips else 0)
    if not clips or total < 120:
        return []
    finds = []
    per_min = len(clips) / (total / 60)
    if per_min < MIN_PER_MIN:
        finds.append(('!!', 'pace-slow', f'{len(clips)} shots for {total / 60:.0f} minutes = {per_min:.1f} per minute (finished films: 6-10; floor {MIN_PER_MIN:.0f}). '
                      'The picture does not follow the narration: plan a shot for what each sentence or pair of sentences says (real photo or film first, then board, map, scene), '
                      'instead of one scene over a whole passage'))
    durs = [(c['end'] - c['start'], c) for c in clips]
    for dur, c in durs:
        if dur > MAX_SHOT:
            finds.append(('!!', f'shot-long:{c["id"]}', f'{c["id"]} at {stamp(c["start"])} runs {dur:.0f} s ({(c.get("src") or "").split("/")[-1]}): longer than {MAX_SHOT:.0f} s. '
                          'Cut it into shots that each show what their sentence says; do not stretch or loop the scene'))
    over = [c for dur, c in durs if LONG < dur <= MAX_SHOT]
    if len([1 for dur, _ in durs if dur > LONG]) > LONG_SHARE * len(clips) and over:
        finds.append(('!!', 'shot-long:share', f'{len([1 for dur, _ in durs if dur > LONG])} of {len(clips)} shots run longer than {LONG:.0f} s (finished films: at most {LONG_SHARE:.0%}): '
                      + ', '.join(f'{c["id"]} {c["end"] - c["start"]:.0f}s' for c in over[:12]) + (' ...' if len(over) > 12 else '')))
    if frames:
        for c, still in frozen(d, clips):
            if c['end'] - c['start'] > MAX_SHOT:
                continue   # already reported as too long
            finds.append(('!!', f'scene-frozen:{c["id"]}', f'{c["id"]} at {stamp(c["start"])} ({(c.get("src") or "").split("/")[-1]}, {c["end"] - c["start"]:.0f} s) shows no change for {still:.0f} s '
                          f'(limit {FROZEN:.0f} s): the drawing ends and the narration goes on. Shorten the shot to the sentence it shows and give the next sentences their own pictures; '
                          'a loop of bobbing figures is not movement'))
    return finds


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    from common import job_dir
    d = job_dir(sys.argv[1])
    found = check(d, json.loads((d / 'timeline.json').read_text(encoding='utf-8')), frames='--fast' not in sys.argv)
    for lv, i, m in found:
        print(lv, i, m)
    print(f'{len(found)} finding(s)')
    sys.exit(1 if found else 0)
