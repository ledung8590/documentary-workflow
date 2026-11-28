"""What a story turns on, compared with every earlier story, before any voice is made.

One story inside the workflow (/gentruyen):
  PY scripts/storycore.py JOB                          the brief for the reader: what to read, what to compare with
  PY scripts/storycore.py JOB --set-core @core.txt     record what the story turns on (text, or @file with the text)
  PY scripts/storycore.py JOB --verdict different      record the comparison (or: --verdict same --with "TITLE" --why "...")
  PY scripts/storycore.py JOB --check                  findings for scripts/gate.py (the gate runs this for every story)

A whole batch of scripts before any of them is built (user 2026-11-28: let Codex or Antigravity do the heavy reading once,
then the workflow pass is light):
  PY scripts/storycore.py --batch DIR                  the brief: every script of the folder, and what is still missing
  PY scripts/storycore.py --batch DIR --set-core "FILE.txt" @core.txt
  PY scripts/storycore.py --batch DIR --verdict "FILE.txt" different | same --with "TITLE or FILE" --why "..."
  PY scripts/storycore.py --batch DIR --check          the table; exit 1 while a script has no core, no verdict or repeats another

Stories 14 and 15 (2026-11-28) came out of one batch with other names, trades, forms, openings and fates, and both turned
on the same device: a paper with a wrong hour on it and wounded men left behind when something was destroyed too early.
storycheck.py compares words, names, motifs and the frame, so it passed both; the reader of /kiem-duyet-kich-ban reads one
script alone and never sees the earlier ones. What a story turns on can only be compared by reading. A reader does that;
this script keeps the result per script TEXT (a digest), so that
  - a verdict made in a batch check is taken over by the workflow without reading the script again,
  - any edit of the script makes the verdict void,
  - a story published or started after the verdict still has to be compared (only the cores, a few lines).

THE READER'S JOB
1. Core: a reader that did not write or fix the script reads the WHOLE script (first line to last) and writes what it
   TURNS ON in 20-45 words: the central event or mistake, the object or paper everything hangs on, the moral question the
   narrator faces. No names of people, no battle name.
2. Verdict: would a regular viewer say this story turns on the SAME KIND of thing as one of the listed stories? Same kind =
   the same device or turning point with other names, places and jobs (a paper or record with a wrong or falsified time;
   wounded left behind by an early demolition; a civilian hidden from the police; a debt to a dead comrade's family; a
   guilt he cannot confess; a superior's order he must bend). A shared battle, front, season or the retreat itself does
   NOT count, and a loose thematic echo is not "same".
3. "same" stops the story: it is not voiced. Tell the user which story it repeats; a story with another core is written
   in the app (renaming a prop does not change what a story turns on).

Kept in stories/checked-cores.json (per script digest) and, after delivery, in stories/published/cores.json (story_done.py).
"""
import hashlib, json, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parent))
CORES = ROOT / 'stories' / 'published' / 'cores.json'
LOG = ROOT / 'stories' / 'published' / 'LOG.md'
STORE = ROOT / 'stories' / 'checked-cores.json'
PROJECTS = True   # tests switch the scan of projects/*/qa/core.json off


def text_digest(p):
    return hashlib.md5(' '.join(Path(p).read_text(encoding='utf-8', errors='replace').split()).encode()).hexdigest()[:10]


def digest(d):
    p = Path(d) / 'script.txt'
    return text_digest(p) if p.exists() else ''


def key(core):
    """A core's identity in "against": its text, so a title written another way still counts as compared."""
    return hashlib.md5(' '.join(str(core).lower().split()).encode()).hexdigest()[:10]


def load(p):
    try:
        return json.loads(Path(p).read_text(encoding='utf-8'))
    except (OSError, ValueError):
        return {}


def save(p, j):
    Path(p).parent.mkdir(parents=True, exist_ok=True)
    Path(p).write_text(json.dumps(j, ensure_ascii=False, indent=1), encoding='utf-8')


def earlier(skip=None):
    """[(title, what it turned on)]: published cores, then the 'Twist / turn type' column of LOG.md for stories without one,
    then stories still in work (projects/*/qa/core.json)."""
    out = dict(load(CORES))
    try:
        for ln in LOG.read_text(encoding='utf-8').splitlines():
            c = [x.strip() for x in ln.strip().strip('|').split('|')]
            if len(c) >= 6 and c[1] and not set(c[1]) <= set('-: ') and c[1].lower() != 'title':
                out.setdefault(c[1][:90], '; '.join(x for x in (c[5], c[4]) if x)[:420])
    except OSError:
        pass
    seen = {key(v) for v in out.values()}
    for f in sorted((ROOT / 'projects').glob('*/qa/core.json')) if PROJECTS else []:
        if skip and f.parent.parent.resolve() == Path(skip).resolve():
            continue
        c = str(load(f).get('core') or '')
        if c and key(c) not in seen:
            out.setdefault(f'(in work) {f.parent.parent.name}'[:90], c[:420]); seen.add(key(c))
    return list(out.items())


def entry(d):
    """The verdict for the script as it is now: qa/core.json, or the batch check's result for the same text."""
    d = Path(d); dg = digest(d)
    j = load(d / 'qa' / 'core.json')
    if j.get('script') == dg:
        return j
    b = load(STORE).get(dg)
    if b:
        j = dict(b, script=dg, adopted='batch check')
        save(d / 'qa' / 'core.json', j)
        return j
    return {'script': dg}


def missing(j, old):
    """Earlier stories this verdict was not compared with."""
    done = set(j.get('against') or [])
    return [(t, c) for t, c in old if key(c) not in done and key(c) != key(j.get('core') or '')]


def problems(j, old, how):
    """Findings for one verdict."""
    if len(str(j.get('core') or '').split()) < 12:
        return [('!!', 'story-core', f'nobody has written what this story turns on. {how}')]
    left = missing(j, old)
    if j.get('same') is True:
        return [('!!', 'story-core-same', f'this story turns on the same kind of thing as "{j.get("with")}": {j.get("why")}. Do not voice it: tell the user; '
                 'a story with another core is written in the app, a renamed prop does not change what it turns on')]
    if j.get('same') is not False or left:
        n = f'{len(left)} newer stor{"y" if len(left) == 1 else "ies"}' if j.get('same') is False else f'the {len(old)} earlier stories'
        return [('!!', 'story-core', f'what this story turns on was not compared with {n}. {how}')]
    return []


def check(d):
    """Findings (level, id, message) for the gate."""
    d = Path(d)
    if not (d / 'script.txt').exists():
        return []
    return problems(entry(d), earlier(d), f'PY scripts/storycore.py {d.name} prints what to do (a script edit makes an older verdict void)')


def publish(d, title):
    """After delivery: keep this story's core for the next comparisons. Returns True when written."""
    c = str(load(Path(d) / 'qa' / 'core.json').get('core') or '')
    if not c:
        return False
    all_ = load(CORES); all_[title[:90]] = c[:420]; save(CORES, all_)
    return True


def arg(flag, default=''):
    return sys.argv[sys.argv.index(flag) + 1] if flag in sys.argv and sys.argv.index(flag) + 1 < len(sys.argv) else default


def value(v):
    return Path(v[1:]).read_text(encoding='utf-8-sig').strip() if v.startswith('@') else v.strip()


def set_core(j, text):
    j['core'] = ' '.join(value(text).split())[:420]
    for k in ('same', 'with', 'why', 'against'):
        j.pop(k, None)           # a new core has not been compared with anything
    return j


def set_verdict(j, old, others=()):
    v = arg('--verdict') if '--batch' not in sys.argv else sys.argv[sys.argv.index('--verdict') + 2]
    if v not in ('different', 'same'):
        sys.exit('--verdict different | same --with "TITLE" --why "..."')
    if len(str(j.get('core') or '').split()) < 12:
        sys.exit('set the core first (--set-core): the verdict is about a core')
    j['same'] = v == 'same'
    j['with'], j['why'] = (arg('--with'), arg('--why')) if j['same'] else ('', '')
    if j['same'] and not j['with']:
        sys.exit('--verdict same needs --with "the title it repeats" and --why "..."')
    j['against'] = sorted({key(c) for _, c in list(old) + list(others)})
    return j


BRIEF = __doc__.split("THE READER'S JOB")[1].split('Kept in stories/')[0].strip()


def one(job):
    from common import job_dir
    d = job_dir(job)
    old = earlier(d); j = entry(d)
    if '--check' in sys.argv:
        found = check(d)
        for lv, i, m in found:
            print(lv, i, m)
        print(f'{len(found)} finding(s)'); sys.exit(1 if found else 0)
    if '--set-core' in sys.argv:
        save(d / 'qa' / 'core.json', set_core(j, arg('--set-core'))); print('core recorded; now compare it and record the verdict'); return
    if '--verdict' in sys.argv:
        save(d / 'qa' / 'core.json', set_verdict(j, old)); print('verdict recorded:', 'SAME as ' + j['with'] if j['same'] else 'different'); return
    print(f'script: {d / "script.txt"}  (digest {j["script"]})')
    if len(str(j.get('core') or '').split()) < 12:
        print('\nSTEP 1: no core yet. A fresh reader reads the whole script and records the core:')
        print(f'  PY scripts/storycore.py {d.name} --set-core @<file with the 20-45 words>')
        todo = old
    else:
        print(f'\ncore{" (from the batch check)" if j.get("adopted") else ""}: {j["core"]}')
        todo = old if j.get('same') is not False else missing(j, old)
        if j.get('same') is True:
            print(f'\nVERDICT: SAME as "{j.get("with")}": {j.get("why")}. The story is not voiced.'); return
        if not todo:
            print('\nVERDICT: different from every earlier story. Nothing to do.'); return
    print(f'\nSTEP 2: compare the core with these {len(todo)} stories (the script need not be read again), then record:')
    print(f'  PY scripts/storycore.py {d.name} --verdict different        or        --verdict same --with "TITLE" --why "..."\n')
    for t, c in todo:
        print(f'- {t}: {c}')
    print("\nTHE READER'S JOB\n" + BRIEF)


def batch(folder):
    folder = Path(folder)
    files = sorted(p for p in folder.glob('*.txt') if not p.stem.endswith('_old'))
    if not files:
        sys.exit(f'no .txt scripts in {folder}')
    store = load(STORE); old = earlier()
    dg = {p.name: text_digest(p) for p in files}

    def mates(name):   # the other scripts of the batch that have a core
        return [(f'(this batch) {n}', store[g]['core']) for n, g in dg.items() if n != name and store.get(g, {}).get('core')]

    def pick(n):
        if n not in dg:
            sys.exit(f'"{n}" is not a script of this folder: ' + ', '.join(dg))
        return store.setdefault(dg[n], {'title': Path(n).stem})

    if '--set-core' in sys.argv:
        i = sys.argv.index('--set-core'); set_core(pick(sys.argv[i + 1]), sys.argv[i + 2]); save(STORE, store); print('core recorded'); return
    if '--verdict' in sys.argv:
        n = sys.argv[sys.argv.index('--verdict') + 1]; j = pick(n)
        if any(not store.get(g, {}).get('core') for g in dg.values()):
            sys.exit('record the core of EVERY script of the batch first: a verdict compares with all of them')
        set_verdict(j, old, mates(n)); save(STORE, store); print('verdict recorded:', 'SAME as ' + j['with'] if j['same'] else 'different'); return
    rows, bad = [], 0
    for p in files:
        j = store.get(dg[p.name], {})
        found = problems(j, old + mates(p.name), '')
        state = 'OK, different' if not found else ('SAME as ' + str(j.get('with')) if found[0][1] == 'story-core-same' else ('no core' if not j.get('core') else 'not compared yet'))
        bad += bool(found); rows.append((p.name, state, j.get('core', '')))
    if '--check' in sys.argv:
        for n, st, c in rows:
            print(f'{st:18} | {n[:70]}\n{"":18} | {c}')
        print(f'{len(rows) - bad} of {len(rows)} scripts are ready to build'); sys.exit(1 if bad else 0)
    print(f'BATCH: {folder}  ({len(files)} scripts, {len(old)} earlier stories)\n')
    need = [n for n, st, _ in rows if st == 'no core']
    if need:
        print(f'STEP 1: {len(need)} script(s) have no core. One fresh reader per script (they can run in parallel) reads the WHOLE script and records:')
        for n in need:
            print(f'  PY scripts/storycore.py --batch "{folder}" --set-core "{n}" @<file with the 20-45 words>')
        print('\nThen run this command again for step 2.')
    else:
        print('STEP 2: every script has a core. One reader compares each script\'s core with the earlier stories AND with the other scripts of the batch,\n'
              'then records one verdict per script (the scripts need not be read again):')
        print(f'  PY scripts/storycore.py --batch "{folder}" --verdict "FILE.txt" different        or        same --with "TITLE or FILE" --why "..."\n')
        print('Cores of this batch:')
        for n, st, c in rows:
            print(f'- {n} [{st}]: {c}')
        print('\nEarlier stories:')
        for t, c in old:
            print(f'- {t}: {c}')
        print(f'\nWhen two scripts of the batch repeat each other, mark the LATER one "same" (the earlier one stays). Then: PY scripts/storycore.py --batch "{folder}" --check')
    print("\nTHE READER'S JOB\n" + BRIEF)


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    batch(arg('--batch')) if '--batch' in sys.argv else one(sys.argv[1])
