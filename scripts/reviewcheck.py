"""Automatic review checks for an archival film: the misses a manual checklist let through (film 76, 2026-11-03).

Called from each film's `plan.py check` (checks 1-3) and runnable alone:
  PY scripts/reviewcheck.py JOB            checks 1-3 on timeline.json + the plan files
  PY scripts/reviewcheck.py JOB --sheet    also 4: contact sheets of every shot from render/picture.mp4 (qa/shots-NN.jpg)

1. Overlay text inside the frame: every overlay is drawn by render.py's own draw_overlay at its fully-shown moment and each
   text box is measured; text past the safe margin is an error (film 76's title card ran off both edges at 132 px).
2. Typed text has typing sound: every scene shot whose source calls `L.typed(` needs scenes/typing-NAME.txt
   (gen_sound.py writes it from `jsscene.mjs --typing`; film 76 had two typed scenes without sound).
3. Film that fires has firing sound: a film cut whose caption says it fires or explodes needs a FIRE entry in gen_sound.py
   (film 76's Hürtgen turret fired on screen in silence).
4. Contact sheets: the middle frame of every shot, captioned with shot id, time and caption, to look at all of them before
   the studio stop (sampling ~20 frames missed the title overflow).
"""
import ast, json, re, subprocess, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MARGIN = 40  # px from the frame edge; text beyond it is cut or touches the edge
FIRE_WORDS = re.compile(r'feuer|beschuss|einschl[äa]g|schie(ß|ss)|abschuss|explo|salve|detonat|\bfir(e|es|ing)\b|launch|blast|'
                        r'\bshell|bắn|nổ|phóng|dispar|explos|tir(e|ent|s)\b', re.I)


def overlay_fit(d):
    """Errors for overlays whose text leaves the frame. Draws each overlay with render.draw_overlay and records text boxes."""
    sys.path[:0] = [str(ROOT / 'scripts'), str(ROOT / 'studio')]
    import render as R
    from PIL import Image, ImageDraw
    tl = json.loads((Path(d) / 'timeline.json').read_text(encoding='utf-8'))
    ovs = [c for t in tl['tracks'] if t.get('id') == 'overlay' or t.get('kind') == 'overlay' for c in t.get('clips', [])]
    boxes, orig = [], ImageDraw.ImageDraw.text

    def rec(self, xy, text, *a, **k):
        if str(text).strip():
            try:
                boxes.append((self.textbbox(xy, text, font=k.get('font')), str(text)))
            except Exception:
                pass
        return orig(self, xy, text, *a, **k)

    errs = []
    ImageDraw.ImageDraw.text = rec
    try:
        for o in ovs:
            dur = o['end'] - o['start']
            boxes.clear()
            try:
                R.draw_overlay(Image.new('RGBA', (R.W, R.H)), o, max(0.0, dur - 0.4))  # fully built, before the fade-out
            except Exception as e:
                errs.append(f'!! overlay {o.get("id")} ({o.get("type")}) at {o["start"]:.1f}s failed to draw: {e}')
                continue
            for (x0, y0, x1, y1), s in boxes:
                if x0 < MARGIN or x1 > R.W - MARGIN or y0 < MARGIN / 2 or y1 > R.H - MARGIN / 2:
                    errs.append(f'!! overlay {o.get("id")} ({o.get("type")}) at {o["start"]:.1f}s: text leaves the frame '
                                f'(x {x0:.0f}-{x1:.0f}, y {y0:.0f}-{y1:.0f}): "{s[:60]}"')
    finally:
        ImageDraw.ImageDraw.text = orig
    return errs


def typing_sound(d, shots):
    errs = []
    for s in shots:
        k, _, name = s['src'].partition(':')
        src = Path(d) / 'scenes' / 'src' / f'{name}.js'
        if k == 'scene' and src.exists() and 'L.typed(' in src.read_text(encoding='utf-8'):
            if not (Path(d) / 'scenes' / f'typing-{name}.txt').exists():
                errs.append(f'!! scene {name} at {s["t0"]:.1f}s types text (L.typed) but has no typing sound: run gen_sound.py')
    return errs


def fire_table(d):
    p = Path(d) / 'gen_sound.py'
    if not p.exists():
        return {}
    for node in ast.parse(p.read_text(encoding='utf-8')).body:
        if isinstance(node, ast.Assign) and any(getattr(t, 'id', '') == 'FIRE' for t in node.targets):
            return ast.literal_eval(node.value)
    return {}


def firing_sound(d, shots):
    fire, errs = fire_table(d), []
    for s in shots:
        k, _, rest = s['src'].partition(':')
        if k == 'vid' and FIRE_WORDS.search(s.get('caption', '')) and rest not in fire and rest.split('@')[0] not in fire:
            errs.append(f'!! film cut {rest} at {s["t0"]:.1f}s: caption says it fires ("{s["caption"][:60]}") but FIRE in '
                        f'gen_sound.py has no sound for it: find the muzzle/impact frame on the clip, or reword the caption')
    return errs


def check(d, shots):
    """Checks 1-3. Prints findings, returns the warning count (plan.py check adds it to its own)."""
    errs = typing_sound(d, shots) + firing_sound(d, shots)
    if (Path(d) / 'timeline.json').exists():
        errs += overlay_fit(d)
    for e in errs:
        print(e)
    return len(errs)


def sheets(d, per=56, cols=7):
    """Check 4: qa/shots-NN.jpg, the middle frame of every video-track shot from render/picture.mp4."""
    from PIL import Image, ImageDraw
    d = Path(d); pic = d / 'render' / 'picture.mp4'
    if not pic.exists():
        sys.exit('no render/picture.mp4: render the draft first (doc.py build JOB --only picture)')
    tl = json.loads((d / 'timeline.json').read_text(encoding='utf-8'))
    vids = sorted((c for t in tl['tracks'] if t.get('id') == 'video' for c in t.get('clips', [])), key=lambda c: c['start'])
    tw, th = 320, 180; out = []
    for p in range(0, len(vids), per):
        part = vids[p:p + per]; rows = (len(part) + cols - 1) // cols
        sheet = Image.new('RGB', (cols * tw, rows * (th + 30)), 'black'); dr = ImageDraw.Draw(sheet)
        for i, c in enumerate(part):
            t = (c['start'] + c['end']) / 2
            raw = subprocess.run(['ffmpeg', '-v', 'error', '-ss', f'{t:.3f}', '-i', str(pic), '-frames:v', '1', '-vf', f'scale={tw}:{th}',
                                  '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-'], capture_output=True).stdout
            x, y = (i % cols) * tw, (i // cols) * (th + 30)
            if len(raw) == tw * th * 3:
                sheet.paste(Image.frombytes('RGB', (tw, th), raw), (x, y))
            dr.text((x + 3, y + th + 2), f'{c["id"]} {int(t // 60)}:{t % 60:04.1f}', fill=(255, 220, 0))
            dr.text((x + 3, y + th + 15), (c.get('caption') or c.get('need') or '')[:52], fill=(220, 220, 220))
        f = d / 'qa' / f'shots-{p // per + 1:02d}.jpg'; f.parent.mkdir(exist_ok=True); sheet.save(f, quality=82); out.append(f)
    print(f'{len(vids)} shots on {len(out)} sheets: ' + ', '.join(str(f.relative_to(d)) for f in out) + ' -> look at every sheet')
    return out


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    job = Path(sys.argv[1]); d = job if job.is_dir() else ROOT / 'projects' / sys.argv[1]
    sys.path.insert(0, str(d))
    import plan  # noqa: E402  the film's own plan.py: shot list with captions
    n = check(d, plan.shots())
    print(f'reviewcheck: {n} warning(s)')
    if '--sheet' in sys.argv:
        sheets(d)
