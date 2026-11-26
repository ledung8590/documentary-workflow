"""Workflow gate: ONE command per stage that runs every check and records PASS/FAIL, so no check depends on the agent
remembering it (user 2026-11-21: almost every /genvideo session shipped a draft with one forgotten check and was redone).

  PY scripts/gate.py JOB plan       before the draft render (archival): plan.py check, the film's plan.py vs the template,
                                    fontcheck, timeline checks, the test suite when shared code was edited
  PY scripts/gate.py JOB studio     before the studio stop: all of the above + lookcheck, music level, render/picture.mp4,
                                    contact sheets of every shot (qa/shots-NN.jpg) and the written record that each was looked at
  PY scripts/gate.py JOB export     before an export (export.py runs it itself): timeline checks, fonts, overlay text
  PY scripts/gate.py JOB deliver --video FILE   after the export: doc.py qa, card sheets + record, description, thumbnail
  PY scripts/gate.py JOB status     what passed, for which timeline

Exit 1 while any `!!` is open. `!` lines are to look at. The result goes to projects/JOB/gate.json with the timeline's
fingerprint: `doc.py studio JOB` refuses to open without a `studio` PASS for the current timeline, and export.py refuses
to export while the `export` checks fail. Both honour the environment variable DOC_GATE_SKIP="reason" (recorded in
gate.json), for the user's own explicit "skip the checks" only.

A finding that is right to keep (a deliberate exception) is waived by its id in projects/JOB/gate_ok.txt:
    repeat:media/commons-123.jpg | the same seal shown again on purpose as the film's closing image (user asked)
One line per finding, id + reason of at least 15 characters. Waived findings are printed at every run and must be listed
in the report to the user. The agent never waives a finding it could fix.

Looking at pictures cannot be checked by code, so the gate demands the record of it: qa/sheets-seen.txt (and
qa/cards-seen.txt) with one line per sheet, `shots-03.jpg | what was seen, what was fixed`, written after the sheets.
"""
import hashlib, json, os, re, subprocess, sys, time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PY = sys.executable
STAGES = ('plan', 'studio', 'export', 'deliver')
IMG = ('.jpg', '.jpeg', '.png', '.webp', '.gif', '.tif', '.tiff')
EPS = 0.06            # under two frames at 24 fps
RETURN_GAP = 10.0     # a scene/map back after more than this is a repeat for the viewer (user 2026-11-19)
OPEN_FIRST, OPEN_SPAN, OPEN_SHOTS, OPEN_VOICE = 3.0, 15.0, 4, 1.0  # archival opening: first shot <= 3 s, >= 4 shots in 15 s, voice within 1 s
OPEN_CALM = 5.0       # no blast, gunfire or launch SFX before this: the first sound must not startle (user 2026-11-26)
LOUD = re.compile(r'(?:^|[\\/])(artillery|boom|cannon\d*|shellburst|navalblast|impact|gunshot|mg50|mgburst|gau8|rifles|musket|missilelaunch|sublaunch|torpedolaunch|thunder|spearvolley|blast|explosion)', re.I)
STORY_STILL = 8.05   # story images longer than 8 s risk YouTube's "static image" demonetization
SOURCED = re.compile(r'(commons|dvids|nara|openverse)-[\w-]+\.\w+$')
SUBSCRIBE = re.compile(r"subscrib|đăng ký kênh|abonnier|suscr[ií]b|s'abonn|チャンネル登録", re.I)
SHARED = ('scripts', 'studio', 'templates', 'maps/engine.html', 'tests')
TEMPLATE_TOKENS = {  # a film's plan.py is often copied from an older film: these calls must survive the copy
    'plan.py': ('dollcheck.check(', 'reviewcheck.check(', 'filmrepeat.check(', 'combat_check(', "['hide_subtitles'] = True", 'pick_intro('),
    'gen_sound.py': ('QUIETER', 'SUBSCRIBE_AT', 'FIRE'),
}


def job_dir(job):
    p = Path(job)
    return p if p.is_dir() and (p / 'brief.json').exists() else ROOT / 'projects' / job


def load(p, default=None):
    try:
        return json.loads(Path(p).read_text(encoding='utf-8'))
    except (OSError, ValueError):
        return default


def fingerprint(tl):
    """Identity of the edit: everything but the user's review notes."""
    return hashlib.sha1(json.dumps({k: v for k, v in tl.items() if k != 'review_notes'}, sort_keys=True, ensure_ascii=False).encode()).hexdigest()[:16]


CARD_TYPES = ('chapter', 'title', 'question', 'quote', 'stat')


def clips(tl, tid):
    return sorted((c for t in tl.get('tracks', []) if t.get('id') == tid for c in t.get('clips', [])), key=lambda c: c.get('start', 0))


def base(src):
    return Path(src).name.lower()


def is_scene(src):
    return base(src).startswith(('scene-', 'map-'))


def tc(t):
    return f'{int(t // 60)}:{t % 60:04.1f}'


# ---------------------------------------------------------------- timeline checks (no rendering, under a second)
def timeline_checks(d, tl, story):
    """[(level, id, message)] from timeline.json alone. level '!!' blocks, '!' is to look at."""
    out = []
    add = lambda lv, fid, msg: out.append((lv, fid, msg))  # noqa: E731
    hard = '!' if story else '!!'
    cards = [o for o in clips(tl, 'overlay') if o.get('type') in CARD_TYPES]
    # a `card` clip is a blank plate the renderer covers with its chapter/title card (render.py Blank): picture, not a hole
    # (film 126: 19 chapter cards read as 3 s black holes); an uncovered card clip still counts as a hole
    vid = [c for c in clips(tl, 'video') if c.get('src')]
    pic = [c for c in clips(tl, 'video') if c.get('src') or (c.get('kind') == 'card' and any(
        o['start'] <= c['start'] + 0.35 and o['end'] >= c['end'] - 0.35 for o in cards))]
    dur = tl.get('duration') or (vid[-1]['end'] if vid else 0)
    if tl.get('mock_voice'):
        add('!!', 'mock-voice', 'mock voice in the timeline: timing tests only, never reviewed or delivered')

    # files that do not exist
    for t in tl.get('tracks', []):
        for c in t.get('clips', []):
            for s in [c.get('src'), (c.get('params') or {}).get('src')] + list(c.get('uses') or []):
                if s and not (d / s).exists():
                    add('!!', f'missing:{s}', f'{t.get("id")} {c.get("id")} at {tc(c.get("start", 0))}: file not found: {s}')

    # holes and overlaps on the picture track
    prev = 0.0
    for c in pic:
        if c['start'] - prev > EPS:
            add(hard, f'hole:{prev:.1f}', f'no picture from {tc(prev)} to {tc(c["start"])} ({c["start"] - prev:.2f} s before {c.get("id")}): black frames')
        elif prev - c['start'] > EPS:
            add('!', f'overlap:{c.get("id")}', f'{c.get("id")} at {tc(c["start"])} starts {prev - c["start"]:.2f} s before the shot under it ends')
        if c['end'] - c['start'] <= 0:
            add('!!', f'length:{c.get("id")}', f'{c.get("id")} at {tc(c["start"])} has no length')
        prev = max(prev, c['end'])
    if pic and dur - prev > 0.5:
        add(hard, f'hole:{prev:.1f}', f'no picture from {tc(prev)} to the end ({tc(dur)})')

    # the same picture twice (user rule: never; a scene or map may continue after a short inserted cut)
    seen = {}  # unit -> [(start, end, source in, source out, clip id)]
    for c in vid:
        n = c['end'] - c['start']; a = float(c.get('in') or 0.0)
        for u in {c['src'], *(c.get('uses') or [])}:  # [5]: the scene a photo hangs in (None for the clip's own source)
            seen.setdefault(u, []).append((c['start'], c['end'], a, a + n * float(c.get('speed') or 1.0), c.get('id'), None if u == c['src'] else c['src']))
    for u, rows in seen.items():
        if len(rows) < 2:
            continue
        if u.lower().endswith(IMG):  # a still, alone or inside a scene: one appearance (touching clips are one appearance)
            runs = [rows[0]]
            for r in rows[1:]:  # an exhibit inside a board that continues after a short inserted cut (<= RETURN_GAP,
                # the same board returning, which the return check allows) is still one appearance (film 126)
                if r[0] - runs[-1][1] <= EPS or (r[5] and r[5] == runs[-1][5] and r[0] - runs[-1][1] <= RETURN_GAP):
                    runs[-1] = (runs[-1][0], r[1], 0, 0, runs[-1][4], runs[-1][5])
                else:
                    runs.append(r)
            if len(runs) > 1:
                add(hard, f'repeat:{u}', f'picture shown {len(runs)} times: {u} at ' + ', '.join(f'{tc(r[0])} ({r[4]})' for r in runs[:6]))
        elif is_scene(u):
            back = [(p, r) for p, r in zip(rows, rows[1:]) if r[0] - p[1] > RETURN_GAP]
            if back:
                add(hard, f'return:{u}', f'{base(u)} comes back after more than {RETURN_GAP:g} s: ' + ', '.join(f'{tc(p[1])} -> {tc(r[0])} ({r[4]})' for p, r in back[:6]))
        else:  # film: different seconds of one reel are different shots, the same seconds are a repeat
            rows = sorted(rows, key=lambda r: r[2]); hits = []
            for i, p in enumerate(rows):
                for r in rows[i + 1:]:
                    if r[2] >= p[3] - 0.5:
                        break
                    hits.append((p, r))
            if hits:
                add(hard, f'repeat:{u}', f'the same seconds of {base(u)} are shown {len(hits) + 1} times: '
                    + ', '.join(f'{p[4]} {tc(p[0])} / {r[4]} {tc(r[0])}' for p, r in hits[:5]))

    # sourced archive files need their credit
    credited = {c.get('file') for c in tl.get('credits', [])}
    if not story:
        for c in vid:
            for s in {c['src'], *(c.get('uses') or [])}:
                if SOURCED.search(s) and s not in credited and not c.get('credit'):
                    add('!!', f'credit:{s}', f'{c.get("id")} at {tc(c["start"])}: {s} has no credit line (doc.py media pick writes it)')

    # overlays against the graphics under them
    ovs = clips(tl, 'overlay'); sfx = [c for c in clips(tl, 'sfx') if not c.get('mute')]
    scenes = [c for c in vid if is_scene(c['src'])]
    for o in ovs:
        if o.get('type') == 'date_tag':
            for c in scenes:
                if min(o['end'], c['end']) - max(o['start'], c['start']) > 0.3:
                    add('!!', f'tag-on-scene:{o.get("id")}', f'date tag {o.get("id")} "{(o.get("props") or {}).get("text", "")[:40]}" at {tc(o["start"])} '
                        f'lies over {base(c["src"])}, which draws its own title: trim or delete the tag')
                    break
    for c in scenes:
        if not c.get('hide_subtitles') and not story:
            add('!', f'subs-on-scene:{c.get("id")}', f'{c.get("id")} {base(c["src"])} at {tc(c["start"])} keeps the subtitles on: only for a scene with no text of its own (SUBS_OVER)')

    # cards land on a sound
    for o in ovs:
        t = o.get('type')
        if t == 'quote' and (o.get('props') or {}).get('typewriter', True):
            if not any('typewriter' in (s.get('src') or '') and o['start'] - 0.2 <= s['start'] <= o['start'] + 2.0 for s in sfx):
                add('!!', f'quote-silent:{o.get("id")}', f'quote card {o.get("id")} at {tc(o["start"])} types without a typewriter sound')
        elif t in ('title_card', 'chapter', 'question'):
            if not any(o['start'] - 0.8 <= s['start'] <= o['start'] + 1.5 for s in sfx):
                add('!!', f'card-silent:{o.get("id")}', f'{t} {o.get("id")} at {tc(o["start"])} has no SFX hit')

    # no background music (user 2026-11-22: only SFX), unless the brief turns it on for this film
    brief = load(d / 'brief.json', {}) or {}
    wants = (brief.get('story') or {}).get('music', False) if story else brief.get('music', False)
    beds = [c for c in clips(tl, 'music') if not c.get('mute')]
    if beds and not wants:
        add('!!', 'music', f'{len(beds)} music clip(s) on the music track, first at {tc(beds[0]["start"])}: films carry no background music, only SFX')

    # sound from frame 0, sound on the opening film cuts
    audio = [c for tid in ('music', 'sfx', 'original') for c in clips(tl, tid) if not c.get('mute')]
    if dur and not any(c['start'] <= 0.15 for c in audio):
        add('!!', 'silent-open', 'nothing sounds at 0:00 (no music, SFX or field sound starts there): the film opens silent')
    for c in clips(tl, 'sfx'):
        if c['start'] < OPEN_CALM - EPS and not c.get('mute') and LOUD.search(c.get('src', '')):
            add('!!', f'open-blast:{c.get("id")}', f'{LOUD.search(c["src"]).group(1)} SFX at {tc(c["start"])}: no blast, gunfire or launch in the first '
                f'{OPEN_CALM:.0f} s, it startles the viewer. Open on ambience (wind, engine, room, distant rumble) that fades in; the first hit comes under the voice, later')
    if not story:
        for c in vid:
            if c['start'] < 12.0 and not c['src'].lower().endswith(IMG) and not is_scene(c['src']) and not c.get('uses'):
                if not any(s['start'] < c['end'] and s['end'] > c['start'] for tid in ('sfx', 'original') for s in clips(tl, tid) if not s.get('mute')):
                    add('!', f'open-cut-silent:{c.get("id")}', f'opening film cut {c.get("id")} at {tc(c["start"])} has no sound of its own (jets, launches, guns need SFX)')

    # the first seconds decide whether the viewer stays (user 2026-11-24, film 126 opened on 7.3 s of a clock graphic while
    # the voice said "2,700 guns opened fire" and the real gun film came at 7.3 s)
    if not story and vid and dur > 60:
        first = vid[0]; n = first['end'] - first['start']
        if is_scene(first['src']) and not base(first['src']).startswith('scene-r-'):
            add('!!', 'open-graphic', f'the film opens on a graphic or map ({base(first["src"])}): frame 0 is the strongest real picture of the opening moment '
                '(film or photo; a reconstruction print r-* when no real picture can exist). Graphics come after the first 5 s')
        if n > OPEN_FIRST + 0.05:
            add('!!', 'open-long', f'the first shot runs {n:.1f} s: at most {OPEN_FIRST:g} s, then cut')
        early = [c for c in vid if c['start'] < OPEN_SPAN]
        if len(early) < OPEN_SHOTS:
            add('!!', 'open-slow', f'{len(early)} shot(s) in the first {OPEN_SPAN:g} s: at least {OPEN_SHOTS} (cuts of 2-3 s)')
        voice = clips(tl, 'voice')
        if voice and voice[0]['start'] > OPEN_VOICE + 0.05:
            add('!!', 'open-voice', f'the narration starts at {voice[0]["start"]:.1f} s: within {OPEN_VOICE:g} s (brief.json voice.lead_in, then doc.py assemble)')

    # the subscribe line gets the animated button
    marks = [c for t in tl.get('tracks', []) for c in t.get('clips', []) if 'subscribe' in ((c.get('params') or {}).get('src') or c.get('src') or '').lower() and t.get('id') not in ('sfx',)]
    for s in clips(tl, 'voice'):
        if SUBSCRIBE.search(s.get('text') or '') and not any(m['start'] < s['end'] + 3 and m['end'] > s['start'] - 1 for m in marks):
            add('!!', f'subscribe:{s.get("id")}', f'{s.get("id")} at {tc(s["start"])} asks to subscribe but no subscribe overlay plays there')

    if story:
        for c in vid:
            src_lo = c['src'].lower()
            if src_lo.endswith(IMG) and not src_lo.endswith(('black.png', 'endscreen.png')) and c['end'] - c['start'] > STORY_STILL:
                add('!!', f'long-still:{c.get("id")}', f'{c.get("id")} at {tc(c["start"])}: one image for {c["end"] - c["start"]:.1f} s (limit 8 s)')
        brief = load(d / 'brief.json', {}) or {}
        if (brief.get('story') or {}).get('old_film', True) and not any(c.get('start', 0) <= 0.5 and c.get('end', 0) >= dur - 1 for c in clips(tl, 'fx')):
            add('!!', 'old-film', 'no whole-film effect clip on the fx track: every story gets "Phim cũ nhẹ" (doc.py story adds it)')
    return out


# ---------------------------------------------------------------- checks that run other tools
def run(cmd, cwd=None, timeout=900):
    env = dict(os.environ, PYTHONIOENCODING='utf-8', PYTHONUTF8='1')
    try:
        r = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=timeout, env=env)
        return r.returncode, (r.stdout or '') + (r.stderr or '')
    except subprocess.TimeoutExpired:
        return 124, f'timed out after {timeout} s'


def from_tool(name, code, text, bang_only=False):
    """Findings from a checker's output: its `!!` lines; with a non-zero exit and none, its last lines."""
    rows = [ln.strip() for ln in text.splitlines() if '!!' in ln]
    out = [('!!', f'{name}:{hashlib.sha1(re.sub(r"[\d.]+", "#", ln).encode()).hexdigest()[:8]}', f'{name}: {ln[:400]}') for ln in rows]
    if code and not out and not bang_only:
        tail = ' / '.join(x.strip() for x in text.strip().splitlines()[-6:])[:700]
        out.append(('!!', f'{name}:exit', f'{name} failed (exit {code}): {tail}'))
    return out


def voice_unchecked(d):
    """Poorly heard sentences must be settled while the timeline is only the voice: a sentence voiced again later has
    another length and moves every shot after it (user 2026-11-26)."""
    if not (d / 'sentences.json').exists() or not (d / 'voice' / 'clips').exists():
        return []
    import voicecheck
    ids = voicecheck.open_items(d)
    if not ids:
        return []
    return [('!!', 'voice-unchecked', f'{len(ids)} sentence(s) Whisper heard poorly have no verdict for their current clip ({", ".join(ids[:8])}'
             f'{" ..." if len(ids) > 8 else ""}): PY scripts/voicecheck.py {d.name} --run, redo the misread ones now, before more picture work')]


def template_drift(d):
    out = []
    for name, tokens in TEMPLATE_TOKENS.items():
        tpl, mine = ROOT / 'templates' / 'archival' / name, d / name
        if not mine.exists():
            out.append(('!!', f'template:{name}', f'{name} is missing: run doc.py plan JOB (archival films are built from the edit plan)'))
            continue
        t, m = tpl.read_text(encoding='utf-8'), mine.read_text(encoding='utf-8')
        for tok in tokens:
            if tok in t and tok not in m:
                out.append(('!!', f'template:{name}:{tok}', f'{name} lost `{tok}` that templates/archival/{name} has (copied from an older film?): merge the template back in'))
    return out


def shared_code(state):
    """The test suite, when scripts/studio/templates differ from the last commit. Cached by the diff's hash."""
    code, st = run(['git', 'status', '--porcelain', '--', *SHARED], cwd=ROOT, timeout=60)
    if code or not st.strip():
        return []
    _, diff = run(['git', 'diff', 'HEAD', '--', *SHARED], cwd=ROOT, timeout=60)
    untracked = [ln[3:].strip().strip('"') for ln in st.splitlines() if ln.startswith('??')]
    h = hashlib.sha1((diff + ''.join(f'{u}:{(ROOT / u).stat().st_mtime_ns if (ROOT / u).is_file() else 0}' for u in untracked)).encode('utf-8', 'replace')).hexdigest()[:16]
    cache = ROOT / 'projects' / '.gate-shared.json'
    if (load(cache) or {}).get('pass') == h:
        return []
    print('  shared code differs from the last commit: running the test suite ...', flush=True)
    code, text = run([PY, '-m', 'pytest', 'tests', '-q', '-x'], cwd=ROOT, timeout=600)
    if code:
        return [('!!', 'tests', 'shared code (scripts/studio/templates) was edited and the tests fail: ' + ' / '.join(text.strip().splitlines()[-8:])[:900])]
    cache.write_text(json.dumps({'pass': h, 'time': time.strftime('%Y-%m-%d %H:%M')}), encoding='utf-8')
    return []


COUNTER = (  # a quoted label ending in a zero-padded counter, typed out or built with padStart(2, '0')
    re.compile(r"""['"`]([^'"`\n]*?[^\W\d_]{2,}[ .:#-]{0,2}0\d)['"`]"""),
    re.compile(r"""['"`]([^'"`\n]*?[^\W\d_]{2,}\s*)['"`]\s*\+\s*[^\n;]{0,40}?padStart\(2"""),
    re.compile(r"""`([^`\n]*?[^\W\d_]{2,}\s*)\$\{[^}]*padStart\(2[^}]*\}"""),
)


def scene_labels(d):
    """Scene sources: counter labels the script never says ("MỤC 01", "LUẬN ĐIỂM 02", "POINT 03": film Trần Thủ Độ, 2026-11-22,
    a per-film helper numbered its note cards and boxed them like slides), and per-film helper libraries to look at."""
    out = []; src = d / 'scenes' / 'src'
    if not src.exists():
        return out
    kit = {f.name for f in (ROOT / 'templates' / 'archival' / 'scenes' / 'src').glob('_*.js')}
    for f in sorted(src.glob('*.js')):
        code = re.sub(r'/\*.*?\*/', '', f.read_text(encoding='utf-8', errors='replace'), flags=re.S)
        code = '\n'.join(re.sub(r'(^|\s)//.*$', '', ln) for ln in code.splitlines())  # comments may quote the old labels
        hits = {h.strip()[:40] for rx in COUNTER for h in rx.findall(code)}
        hits = {h for h in hits if h and not re.search(r'\d{3,}|[./\\]|^#', h)}  # years, paths and colours are not labels
        if hits:
            out.append(('!!', f'counter-label:{f.name}', f'{f.name} draws numbered labels the narration never says ({", ".join(sorted(hits)[:5])}): '
                        'notes are a year or number plus one or two serif lines, no slide-style section tags (GROUPS2.template.md "Notes, not boxes")'))
        if f.name.startswith('_') and f.name not in kit:
            out.append(('!', f'own-helper:{f.name}', f'{f.name} is a drawing library written for this film only: check every frame type it draws full size '
                        'against the look reference; a helper worth keeping belongs in templates/archival/scenes/src'))
    return out


def overlay_text(d):
    """reviewcheck's timeline-only checks (overlay text inside the frame, readable time, subtitle heads)."""
    sys.path[:0] = [str(ROOT / 'scripts'), str(ROOT / 'studio')]
    try:
        import reviewcheck as RC
        errs = RC.overlay_fit(d) + RC.overlay_shown(d) + RC.subtitle_heads(d)
    except Exception as e:  # a crash in a check is a failed check, never a pass
        return [('!!', 'overlay-text:crash', f'reviewcheck crashed: {type(e).__name__}: {e}')]
    return [('!!', f'overlay-text:{hashlib.sha1(e.encode()).hexdigest()[:8]}', e) for e in errs]


def seen_record(d, sheets, record, what):
    """The written record that every sheet was looked at, newer than the sheets."""
    rec = d / 'qa' / record
    if not sheets:
        return []
    names = [s.name for s in sheets]
    how = f'look at every sheet ({", ".join(names[:4])}{" …" if len(names) > 4 else ""}), fix what is wrong, then write qa/{record}: one line per sheet, `{names[0]} | what you saw and fixed`'
    if not rec.exists():
        return [('!!', f'seen:{record}', f'{len(sheets)} {what} sheets were not reviewed: {how}')]
    if rec.stat().st_mtime < max(s.stat().st_mtime for s in sheets):
        return [('!!', f'seen:{record}', f'qa/{record} is older than the sheets (the picture changed since): {how}')]
    notes = {}
    for ln in rec.read_text(encoding='utf-8').splitlines():
        k, _, v = ln.partition('|')
        notes[k.strip()] = v.strip()
    lack = [n for n in names if len(notes.get(n, '')) < 15]
    return [('!!', f'seen:{record}', f'qa/{record} has no real note for {", ".join(lack[:8])}: {how}')] if lack else []


def shot_sigs(tl):
    """{clip id: signature of what that shot shows}: the clip, the overlays over it and the film-wide picture settings."""
    ovs = clips(tl, 'overlay') + clips(tl, 'fx')
    top = json.dumps({k: tl.get(k) for k in ('look', 'fx', 'subtitle_style', 'language')}, sort_keys=True, ensure_ascii=False)
    out = {}
    for c in clips(tl, 'video'):
        over = [{k: v for k, v in o.items() if k not in ('frame', 'anchor', 'end_anchor')} for o in ovs if o['start'] < c['end'] and o['end'] > c['start']]
        body = {k: v for k, v in c.items() if k not in ('frame', 'anchor', 'end_anchor', 'need')}
        out[c.get('id')] = hashlib.sha1((json.dumps([body, over], sort_keys=True, ensure_ascii=False) + top).encode()).hexdigest()[:12]
    return out


def shot_sheets(d, tl, state):
    """Contact sheets and the record that they were looked at. After a reviewed draft, only the shots that changed since are
    put on sheets again (qa/delta-NN.jpg + qa/delta-seen.txt): film 126 (2026-11-24) re-read all 14 sheets after each of five
    30-minute splices, most of a night."""
    pic = d / 'render' / 'picture.mp4'
    if not pic.exists():
        return [('!!', 'no-picture', 'no render/picture.mp4: render the draft first (doc.py build JOB --only picture)')]
    sys.path[:0] = [str(ROOT / 'scripts'), str(ROOT / 'studio')]
    import reviewcheck as RC
    sigs = shot_sigs(tl); seen = state.get('shots_seen') or {}
    changed = sorted(i for i in sigs if seen.get(i) != sigs[i])
    if not changed:
        return []  # every shot on the timeline was reviewed as it is now
    if seen and len(changed) <= 0.4 * len(sigs):
        key = hashlib.sha1(json.dumps([changed, [sigs[i] for i in changed]]).encode()).hexdigest()[:12]
        sheets = sorted((d / 'qa').glob('delta-*.jpg'))
        if state.get('delta_key') != key or not sheets or min(s.stat().st_mtime for s in sheets) < pic.stat().st_mtime:
            print(f'  writing contact sheets of the {len(changed)} shots changed since the reviewed draft ...', flush=True)
            for s in sheets:
                s.unlink()
            sheets = RC.sheets(d, only=set(changed), name='delta'); state['delta_key'] = key
        out = seen_record(d, sheets, 'delta-seen.txt', 'changed-shot')
    else:
        sheets = sorted((d / 'qa').glob('shots-*.jpg'))
        if not sheets or min(s.stat().st_mtime for s in sheets) < pic.stat().st_mtime:
            print('  writing contact sheets of every shot ...', flush=True)
            for s in sheets:
                s.unlink()
            sheets = RC.sheets(d)
        out = seen_record(d, sheets, 'sheets-seen.txt', 'shot')
    if not out:
        state['shots_seen'] = sigs
    return out


def music_level(d, tl, state):
    tool = d / 'qa' / 'music_level.py'
    if not tool.exists() or not clips(tl, 'music'):
        return []
    h = hashlib.sha1(json.dumps([clips(tl, 'music'), [(c.get('id'), c.get('start'), c.get('end'), c.get('gain_db')) for c in clips(tl, 'voice')], tl.get('duck')], sort_keys=True).encode()).hexdigest()[:16]
    if state.get('music_level') == h:
        return []
    print(f'  measuring {len(clips(tl, "music"))} music beds against the voice ...', flush=True)
    code, text = run([PY, str(tool)], cwd=d, timeout=1800)
    bad = [ln.strip() for ln in text.splitlines() if '<-- adjust' in ln and 'intro' not in ln]
    if code and not bad:
        return [('!!', 'music-level:exit', 'qa/music_level.py failed: ' + ' / '.join(text.strip().splitlines()[-4:])[:500])]
    if bad:
        return [('!!', f'music-level:{ln.split()[0]}', f'music not 29.5–33 dB under the voice: {ln[:200]}') for ln in bad]
    state['music_level'] = h
    return []


def deliver_checks(d, job, tl, video, story):
    out = []
    if not video or not Path(video).exists():
        return [('!!', 'no-video', 'deliver needs --video FILE (the exported file in output/JOB/)')]
    print('  doc.py qa on the exported file ...', flush=True)
    code, text = run([PY, str(ROOT / 'scripts' / 'doc.py'), 'qa', job, '--video', str(video)], cwd=ROOT, timeout=3600)
    rep = load(d / 'qa' / 'qa.json')
    if code or not rep or rep.get('video') != str(video):
        return [('!!', 'qa:exit', 'doc.py qa failed: ' + ' / '.join(text.strip().splitlines()[-4:])[:500])]
    for b in rep.get('black', []):
        if not b.get('expected'):
            out.append(('!!', f'black:{b["start"]:.1f}', f'black picture {tc(b["start"])}–{tc(b["end"])} outside any card'))
    for f in rep.get('freeze', []):
        if not f.get('expected'):
            out.append(('!', f'freeze:{f["start"]:.1f}', f'still picture from {tc(f["start"])}: look at the frames'))
    if rep.get('lufs') is None or abs(rep['lufs'] + 14.0) > 1.0:
        out.append(('!!', 'lufs', f'loudness {rep.get("lufs")} LUFS, target -14 ± 1'))
    if rep.get('true_peak') is None or rep['true_peak'] > -0.9:
        out.append(('!!', 'peak', f'true peak {rep.get("true_peak")} dBFS, limit -1'))
    for c in rep.get('cards', []):
        if not c.get('ok'):
            out.append(('!!', f'card-sound:{c["start"]}', f'{c["type"]} at {tc(c["start"])} is silent in the export ({c["rms_db"]} dB RMS, cue {c["sfx_cue"]})'))
    if clips(tl, 'overlay'):
        sheets = sorted((d / 'qa').glob('cards-*.jpg'))
        if not sheets or min(s.stat().st_mtime for s in sheets) < Path(video).stat().st_mtime:
            print('  cutting every card from the exported file ...', flush=True)
            sys.path[:0] = [str(ROOT / 'scripts'), str(ROOT / 'studio')]
            import reviewcheck as RC
            for s in sheets:
                s.unlink()
            sheets = RC.card_sheets(d, video)
        out += seen_record(d, sheets, 'cards-seen.txt', 'card')
    outd = Path(video).parent
    if not story:
        desc = outd / 'description_youtube.txt'
        if not desc.exists():
            out.append(('!!', 'description', f'no {desc.name} next to the video (scripts/description.py)'))
        else:
            s = desc.read_text(encoding='utf-8')
            if len(s) > 5000:
                out.append(('!!', 'description:long', f'description is {len(s)} characters, YouTube takes 5,000'))
            if re.search(r'credits\.txt|LICENSES\.md|projects/', s):
                out.append(('!!', 'description:internal', 'description points to an internal file the viewer cannot see'))
            if 'TAGS' not in s:
                out.append(('!!', 'description:tags', 'description has no TAGS block (7 comma-separated tags)'))
            if not any(len(re.findall(r'#\w+', ln)) == 7 for ln in s.splitlines()):
                out.append(('!!', 'description:hashtags', 'description has no line of exactly 7 #hashtags'))
    thumbs = sorted(outd.glob('*.jpg'), key=lambda f: f.stat().st_mtime, reverse=True)
    if not thumbs:
        out.append(('!!', 'thumbnail', 'no thumbnail .jpg next to the video'))
    else:  # not the channel's last layouts again (YouTube judges templates across the channel)
        try:
            sys.path[:0] = [str(ROOT / 'scripts')]
            import thumbrepeat
            out += thumbrepeat.check(thumbs[0], story, quiet=True)
        except Exception as e:
            out.append(('!!', 'thumb-template:crash', f'thumbrepeat crashed: {type(e).__name__}: {e}'))
    return out


# ---------------------------------------------------------------- run, record, require
def waivers(d):
    out = {}
    p = d / 'gate_ok.txt'
    for ln in p.read_text(encoding='utf-8').splitlines() if p.exists() else []:
        k, _, why = ln.partition('|')
        if k.strip() and not k.lstrip().startswith('#') and len(why.strip()) >= 15:
            out[k.strip()] = why.strip()
    return out


def short_renders(d, tl):
    """A rendered scene/map clip shorter than the timeline needs freezes on its last frame (film 126, 2026-11-24:
    maps/write_maps.py run after plan.py durations reset 69 map lengths to the spec, 8 maps came out seconds short)."""
    need = {}
    for c in clips(tl, 'video'):
        s = c.get('src') or ''
        if s.lower().endswith(('.mp4', '.mov', '.webm')):
            need[s] = max(need.get(s, 0.0), float(c.get('in') or 0) + (c['end'] - c['start']) * float(c.get('speed') or 1.0))
    out = []
    for s, n in sorted(need.items()):
        f = d / s
        if not f.exists():
            continue
        try:
            r = subprocess.run(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', str(f)],
                               capture_output=True, text=True, timeout=60)
            have = float(r.stdout.strip())
        except ValueError:  # film 116, 2026-11-26: an empty film cut (interrupted download) killed the draft render after 34 minutes
            out.append(('!!', f'bad-media:{s}', f'{base(s)} has no readable video: pick or render it again'))
            continue
        except (OSError, subprocess.TimeoutExpired):
            continue
        if have + 0.25 < n and is_scene(s):
            out.append(('!!', f'short-render:{s}', f'{base(s)} is {have:.2f} s but the timeline needs {n:.2f} s: it freezes; '
                        'run plan.py durations (after write_maps.py), then re-render it'))
    return out


def gate(job, stage, video=None, quiet=False):
    """Run a stage. Returns (ok, findings). Writes projects/JOB/gate.json."""
    d = job_dir(job)
    tl = load(d / 'timeline.json')
    brief = load(d / 'brief.json', {}) or {}
    story = brief.get('genre') == 'story'
    state = load(d / 'gate.json', {}) or {}
    finds = []
    say = (lambda *a: None) if quiet else (lambda m: print(m, flush=True))
    say(f'gate {stage}: {d.name} ({"story" if story else "archival"})')
    if tl is None:
        finds.append(('!!', 'no-timeline', 'no timeline.json (run assemble first)'))
    else:
        if stage in ('plan', 'studio'):
            finds += voice_unchecked(d)
        if stage in ('plan', 'studio') and not story:
            finds += template_drift(d)
            finds += scene_labels(d)
            if (d / 'plan.py').exists():
                say('  plan.py check ...')
                code, text = run([PY, 'plan.py', 'check'], cwd=d)
                finds += from_tool('plan.py check', code, text)
        if stage != 'deliver':
            say('  fontcheck ...')
            code, text = run([PY, str(ROOT / 'scripts' / 'fontcheck.py'), d.name], cwd=ROOT)
            finds += from_tool('fontcheck', code, text) if code else []
        if stage in ('studio', 'export') or (stage == 'plan' and clips(tl, 'video')):
            finds += timeline_checks(d, tl, story)
            if not story:
                import pacecheck   # film 183: 77 shots for 54 minutes passed the gate
                finds += pacecheck.check(d, tl, frames=stage == 'studio')
            finds += short_renders(d, tl)
        if stage == 'export' or (story and stage != 'deliver'):  # archival plan/studio get these through plan.py check
            finds += overlay_text(d)
        if stage in ('plan', 'studio'):
            finds += shared_code(state)
        if stage == 'studio':
            if not story and (d / 'scenes').exists():
                say('  lookcheck ...')
                code, text = run([PY, str(ROOT / 'scripts' / 'lookcheck.py'), d.name], cwd=ROOT, timeout=1800)
                finds += from_tool('lookcheck', code, text)
            finds += music_level(d, tl, state)
            finds += shot_sheets(d, tl, state)
        if stage == 'deliver':
            finds += deliver_checks(d, d.name, tl, video, story)
    ok_ids = waivers(d)
    seen_ids = set(); uniq = []
    for f in finds:
        if f[1] not in seen_ids:
            seen_ids.add(f[1]); uniq.append(f)
    waived = [f for f in uniq if f[0] == '!!' and f[1] in ok_ids]
    fails = [f for f in uniq if f[0] == '!!' and f[1] not in ok_ids]
    looks = [f for f in uniq if f[0] == '!']
    for lv, fid, msg in fails:
        say(f'{lv} [{fid}] {msg}')
    kinds = {}
    for f in looks:
        kinds.setdefault(f[1].split(':')[0], []).append(f)
    for k, rows in kinds.items():  # one line per kind keeps the output short on long films
        say(f'!  [{rows[0][1]}] {rows[0][2]}' + (f'  (+{len(rows) - 1} more of this kind: ' + ', '.join(r[1].split(":", 1)[-1] for r in rows[1:9]) + (' …' if len(rows) > 9 else '') + ')' if len(rows) > 1 else ''))
    for lv, fid, msg in waived:
        say(f'ok [{fid}] waived: {ok_ids[fid]}  ({msg[:120]})')
    ok = not fails
    state.setdefault('stages', {})[stage] = {
        'status': 'PASS' if ok else 'FAIL', 'fingerprint': fingerprint(tl) if tl else None, 'time': time.strftime('%Y-%m-%d %H:%M:%S'),
        'fails': [f[1] for f in fails], 'look': len(looks), 'waived': {f[1]: ok_ids[f[1]] for f in waived}}
    tmp = d / 'gate.json.tmp'
    tmp.write_text(json.dumps(state, ensure_ascii=False, indent=1), encoding='utf-8'); os.replace(tmp, d / 'gate.json')
    say(f'gate {stage}: {"PASS" if ok else "FAIL"}: {len(fails)} to fix (!!), {len(looks)} to look at (!), {len(waived)} waived')
    if not ok:
        say('Fix every !! and run the gate again. Do not open the studio, export or report "ready" on a FAIL.')
    return ok, uniq


def require(job, stage):
    """For doc.py studio: exit unless `stage` passed for the timeline as it is now."""
    d = job_dir(job)
    skip = os.environ.get('DOC_GATE_SKIP', '').strip()
    state = load(d / 'gate.json', {}) or {}
    if skip:
        state.setdefault('overrides', []).append({'stage': stage, 'reason': skip, 'time': time.strftime('%Y-%m-%d %H:%M:%S')})
        (d / 'gate.json').write_text(json.dumps(state, ensure_ascii=False, indent=1), encoding='utf-8')
        print(f'gate {stage} SKIPPED (DOC_GATE_SKIP: {skip}) - recorded in gate.json', flush=True)
        return
    rec = (state.get('stages') or {}).get(stage) or {}
    tl = load(d / 'timeline.json')
    if rec.get('status') == 'PASS' and tl is not None and rec.get('fingerprint') == fingerprint(tl):
        return
    why = 'never run' if not rec else 'FAILED' if rec.get('status') != 'PASS' else 'passed for an older timeline (edited since)'
    sys.exit(f'gate {stage}: {why}. Run: PY scripts/gate.py {d.name} {stage}   and fix every !! first.')


def status(job):
    d = job_dir(job); state = load(d / 'gate.json', {}) or {}; tl = load(d / 'timeline.json')
    now = fingerprint(tl) if tl else None
    for s in STAGES:
        r = (state.get('stages') or {}).get(s)
        if not r:
            print(f'{s:8s} -'); continue
        cur = 'current timeline' if r.get('fingerprint') == now else 'OLDER timeline'
        print(f'{s:8s} {r["status"]:4s} {r["time"]}  {cur}  fails {len(r.get("fails", []))}  waived {len(r.get("waived", {}))}')
    for o in state.get('overrides', []):
        print(f'override {o["stage"]} {o["time"]}: {o["reason"]}')


def main():
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    if len(sys.argv) < 3 or sys.argv[2] not in STAGES + ('status',):
        sys.exit(__doc__)
    job, stage = sys.argv[1], sys.argv[2]
    if stage == 'status':
        return status(job)
    video = sys.argv[sys.argv.index('--video') + 1] if '--video' in sys.argv else None
    ok, _ = gate(job, stage, video)
    sys.exit(0 if ok else 1)


if __name__ == '__main__':
    main()
