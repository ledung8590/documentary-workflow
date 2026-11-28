"""What a story turns on, compared with every earlier story, before any voice is made.

  PY scripts/storycore.py JOB          print the brief for the reader (earlier stories' cores, where to write the verdict)
  PY scripts/storycore.py JOB --check  findings for scripts/gate.py (also run by the gate for every story)

Stories 14 and 15 (2026-11-28) came out of one batch with other names, trades, forms, openings and fates, and both turned
on the same device: a paper with a wrong hour written on it and wounded men left behind when something was destroyed too
early. storycheck.py compares words, names, motifs and the frame, so it passed both; the reader of /kiem-duyet-kich-ban reads
one script alone and never sees the earlier ones. What a story turns on can only be compared by reading, so a reader does it
and this script makes sure it was done for the script as it is now:

  projects/<id>/qa/core.json
  {"script": "<digest printed by this script>",
   "core": "what the story turns on, at most 45 words: the central event or mistake, the object or paper everything hangs on,
            the moral question of the narrator (no names)",
   "compared": <number of earlier stories read against, the number this script prints>,
   "same": false, "with": "", "why": ""}

A fresh reader (a sub-agent that did not write or fix the script) reads the WHOLE script, writes "core", then reads every
earlier core this script prints and answers: would a regular viewer say this story turns on the same kind of thing as one
of them? Same kind = the same device or turning point with other names and places (a paper with a wrong or falsified time;
wounded left behind by an early demolition; a civilian hidden from the police; a debt to a dead comrade's family; a guilt
he cannot confess). A shared battle, season or the retreat itself does not count. "same": true stops the film: the story
is not voiced; tell the user which earlier story it repeats (the script is rewritten in the app, not patched here).
After the film is delivered the core goes into stories/published/cores.json (story_done.py), so the next story is compared with it.
"""
import hashlib, json, re, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parent))
CORES = ROOT / 'stories' / 'published' / 'cores.json'
LOG = ROOT / 'stories' / 'published' / 'LOG.md'


def digest(d):
    p = Path(d) / 'script.txt'
    return hashlib.md5(' '.join(p.read_text(encoding='utf-8', errors='replace').split()).encode()).hexdigest()[:10] if p.exists() else ''


def earlier():
    """[(title, what it turned on)]: cores.json first, then the 'Twist / turn type' column of LOG.md for stories without one."""
    out = {}
    try:
        for k, v in json.loads(CORES.read_text(encoding='utf-8')).items():
            out[k] = v
    except (OSError, ValueError):
        pass
    try:
        for ln in LOG.read_text(encoding='utf-8').splitlines():
            c = [x.strip() for x in ln.strip().strip('|').split('|')]
            if len(c) >= 6 and c[1] and not set(c[1]) <= set('-: ') and c[1].lower() != 'title':
                out.setdefault(c[1][:90], '; '.join(x for x in (c[5], c[4]) if x)[:420])
    except OSError:
        pass
    return list(out.items())


def check(d):
    """Findings (level, id, message) for the gate."""
    d = Path(d)
    if not (d / 'script.txt').exists():
        return []
    old = earlier(); dg = digest(d); f = d / 'qa' / 'core.json'
    how = f'PY scripts/storycore.py {d.name} prints the brief; a fresh reader agent reads the whole script and writes qa/core.json'
    try:
        j = json.loads(f.read_text(encoding='utf-8'))
    except (OSError, ValueError):
        return [('!!', 'story-core', f'nobody compared what this story turns on with the {len(old)} earlier stories. {how}')]
    if j.get('script') != dg:
        return [('!!', 'story-core', f'qa/core.json was written for another text of the script (digest {j.get("script")}, now {dg}). {how}')]
    if len(str(j.get('core') or '').split()) < 12:
        return [('!!', 'story-core', f'qa/core.json has no "core" (what the story turns on, 12-45 words). {how}')]
    if not isinstance(j.get('same'), bool) or int(j.get('compared') or 0) < len(old):
        return [('!!', 'story-core', f'qa/core.json compares with {j.get("compared") or 0} earlier stories, there are {len(old)}, or has no "same": true/false. {how}')]
    if j['same']:
        return [('!!', 'story-core-same', f'this story turns on the same kind of thing as "{j.get("with")}": {j.get("why")}. Do not voice it: tell the user; the script is '
                 'rewritten with another core (in the app), a patched name or prop does not change what it turns on')]
    return []


def publish(d, title):
    """After delivery: keep this story's core for the next comparisons. Returns True when written."""
    try:
        j = json.loads((Path(d) / 'qa' / 'core.json').read_text(encoding='utf-8'))
    except (OSError, ValueError):
        return False
    try:
        all_ = json.loads(CORES.read_text(encoding='utf-8'))
    except (OSError, ValueError):
        all_ = {}
    all_[title[:90]] = str(j.get('core') or '')[:420]
    CORES.parent.mkdir(parents=True, exist_ok=True)
    CORES.write_text(json.dumps(all_, ensure_ascii=False, indent=1), encoding='utf-8')
    return True


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    from common import job_dir
    d = job_dir(sys.argv[1])
    if '--check' in sys.argv:
        found = check(d)
        for lv, i, m in found:
            print(lv, i, m)
        print(f'{len(found)} finding(s)'); sys.exit(1 if found else 0)
    old = earlier()
    print(f'script: {d / "script.txt"}\nscript digest: {digest(d)}\nwrite: {d / "qa" / "core.json"}\ncompared: {len(old)}\n')
    print('Earlier stories and what each turned on:')
    for t, c in old:
        print(f'- {t}: {c}')
    print('\n' + re.sub(r'^.*?(A fresh reader)', r'\1', __doc__.split('projects/<id>/qa/core.json')[1], flags=re.S).strip())
