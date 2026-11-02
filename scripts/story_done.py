"""After a story's upload (/gentruyen, docs/STORY_MODE.md step 10): keep the script for storycheck, delete the rest.

  PY scripts/story_done.py JOB            dry run: what is kept, what is deleted, how many GB
  PY scripts/story_done.py JOB --run      do it (only after the user confirms the upload)
  PY scripts/story_done.py JOB --run --keep-output   keep output/<id>/ (video, thumbnail, description) this once

Stories are fiction over AI images: no evidence pack (that is archival only, scripts/evidence.py). Kept: the final script
in stories/published/<name>.txt (the corpus storycheck.py compares new stories against) and a row in
stories/published/LOG.md (written by the agent first). Deleted: projects/<id>/ (renders, voice chunks, images copied, studio history) and the story's
inputs in input/ (script, image folder, image SRT, prompts) and output/<id>/ (user, 2026-11-02: the video is on YouTube).
Music beds and SFX are never deleted: they live in the shared library assets/music, assets/sfx and are reused by both
paths. Any music/SFX file that sits only inside the project (projects/<id>/music, sfx) is moved into
assets/<music|sfx>/from-<id>/ first, so nothing generated for a story is lost.
STORY.md is kept next to the script (<name>.story.md). The LOG.md row must exist before --run.
"""
import argparse, json, shutil, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def size(p):
    if not p.exists():
        return 0
    return p.stat().st_size if p.is_file() else sum(f.stat().st_size for f in p.rglob('*') if f.is_file())


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('job'); ap.add_argument('--run', action='store_true'); ap.add_argument('--keep-output', action='store_true')
    a = ap.parse_args()
    sys.stdout.reconfigure(encoding='utf-8')
    proj = ROOT / 'projects' / a.job
    brief = json.loads((proj / 'brief.json').read_text(encoding='utf-8'))
    if brief.get('genre') != 'story':
        sys.exit(f'{a.job} is not a story job: archival films go to evidence/ with scripts/evidence.py')
    st = brief.get('story') or {}
    imgs = Path(st['images']) if st.get('images') else None
    name = imgs.name if imgs else a.job
    inp = ROOT / 'input'
    inputs = [p for p in [imgs, *(Path(st[k]) for k in ('srt', 'prompts') if st.get(k))] if p and p.exists()]
    inputs += [p for p in inp.glob(f'{name}*') if p not in inputs and p.exists()]          # script .txt, job .json beside it
    inputs = [p for p in inputs if inp in p.resolve().parents]                             # never outside input/
    out = ROOT / 'output' / a.job
    delete = [proj, *inputs] + ([out] if out.exists() and not a.keep_output else [])
    local = [f for k in ('music', 'sfx') for f in (proj / k).rglob('*') if f.is_file() and f.suffix.lower() in ('.mp3', '.wav', '.m4a', '.ogg', '.flac')]
    keep_script = ROOT / 'stories' / 'published' / f'{name}.txt'
    src_script = proj / 'script.txt'

    print(f'keep: {keep_script.relative_to(ROOT)} (final script, storycheck corpus) + a row in stories/published/LOG.md')
    print('keep: assets/music, assets/sfx (shared library, reused by /genvideo and /gentruyen)')
    for f in local:
        print(f'move to library: {f.relative_to(ROOT)} -> assets/{f.relative_to(proj).parts[0]}/from-{a.job[:40]}/')
    if out.exists() and a.keep_output:
        print(f'keep: output/{a.job}/ ({size(out) / 1e9:.2f} GB)')
    total = 0
    for p in delete:
        s = size(p); total += s
        print(f'delete: {p.relative_to(ROOT)} ({s / 1e9:.2f} GB)')
    print(f'frees {total / 1e9:.2f} GB')
    log = ROOT / 'stories' / 'published' / 'LOG.md'
    logged = log.exists() and name.split('.')[0] in log.read_text(encoding='utf-8')
    if not logged:
        print(f'!! no row for this story in stories/published/LOG.md: add it first (frame, hero trade/region, prop, twist from STORY.md)')
    if not a.run:
        print('dry run: add --run after the user confirms the upload'); return
    if not logged:
        sys.exit('refused: LOG.md row missing')

    for f in local:  # project-only music/SFX into the shared library before the project goes
        t = ROOT / 'assets' / f.relative_to(proj).parts[0] / f'from-{a.job[:40]}' / f.name
        t.parent.mkdir(parents=True, exist_ok=True); shutil.move(str(f), t)
    keep_script.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src_script, keep_script)
    if (proj / 'STORY.md').exists():  # chapters, characters, frame: what the next story must not repeat
        shutil.copy2(proj / 'STORY.md', keep_script.with_suffix('.story.md'))
    for p in delete:
        shutil.rmtree(p, ignore_errors=True) if p.is_dir() else p.unlink(missing_ok=True)
    left = [p for p in delete if p.exists()]
    print('done' if not left else f'could not delete (open in another program?): {", ".join(str(p) for p in left)}')


if __name__ == '__main__':
    main()
