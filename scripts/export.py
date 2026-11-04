"""Export a reviewed film (stage 11) without the studio job runner. The studio is for review only: its export job hung
at start twice on 2026-10-31 (workers at 0.1 s CPU, no frames), so exports run here, in the foreground process.

  PY scripts/export.py JOB            re-render only the edited picture ranges (spliced into render/picture.mp4),
                                      voice-led mix (-14 LUFS) and mux; output/<id>/video.mp4 (+ LICENSES.md, credits.txt)
  PY scripts/export.py JOB --no-mix   reuse render/mix.wav (picture-only edits, nothing on the audio tracks changed)

No usable picture.mp4 -> the whole picture is rendered on the GPU (NVENC). The first export writes video.mp4; later ones
write video-<time>.mp4 next to it, so a delivered file is never overwritten. Prints progress; wrap long runs in a
watchdog (memory: no-infinite-waits).
"""
import os, sys, time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'scripts'), str(ROOT / 'studio')]
import core, render as R  # noqa: E402


def main():
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    job = sys.argv[1]
    proj = core.Project(job); tl, _ = proj.read(); t0 = time.time()
    if tl.get('mock_voice'):
        sys.exit('mock voice in the timeline: not deliverable')
    log = lambda m: print(f'{time.time() - t0:6.0f}s {m}', flush=True)  # noqa: E731
    dirty = core.dirty_ranges(proj, tl)
    if dirty is None:
        log('no usable picture.mp4: whole picture on the GPU')
        new = proj.d / 'render' / 'picture.new.mp4'
        core.render_range(proj, tl, 0.0, tl['duration'], new, log, enc='nvenc')
        os.replace(new, proj.picture); core.save_state(proj, tl)
    elif dirty:
        log(f'{len(dirty)} edited range(s): {[(round(a, 1), round(b, 1)) for a, b in dirty]}')
        new, _segs = core.splice(proj, tl, dirty, log)
        os.replace(new, proj.picture); core.save_state(proj, tl)
    else:
        log('picture.mp4 matches the timeline')
    mix = proj.d / 'render' / 'mix.wav'
    if '--no-mix' not in sys.argv or not mix.exists():
        R.mix(proj.d, tl, mix); log('mixed')
    outd = ROOT / 'output' / job; outd.mkdir(parents=True, exist_ok=True)
    out = outd / 'video.mp4'
    if out.exists():
        out = outd / f'video-{time.strftime("%Y%m%d-%H%M%S")}.mp4'
    R.mux(proj.picture, mix, out); log(f'muxed -> {out}')
    used = {c['src'] for t in tl['tracks'] for c in t['clips'] if c.get('src') and t['id'] != 'voice'} | {u for t in tl['tracks'] for c in t['clips'] for u in c.get('uses', [])}  # photos drawn inside a JS scene (film 6)
    rows = (proj.d / 'LICENSES.md').read_text(encoding='utf-8').split('\n')
    (outd / 'LICENSES.md').write_text('\n'.join(r for r in rows if not r.startswith('| media/') or r.split('|')[1].strip() in used), encoding='utf-8')
    lines = sorted({c['line'] + (f' - {c["page"]}' if c.get('page') else '') for c in tl.get('credits', []) if c['file'] in used})
    (outd / 'credits.txt').write_text('Archival media:\n' + '\n'.join(lines) + '\n', encoding='utf-8')
    log(f'done. next: doc.py qa {job} --video "{out}"')


if __name__ == '__main__':
    main()
