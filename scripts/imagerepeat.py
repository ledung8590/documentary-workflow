"""Story pictures that are the same picture as one of an earlier story (or of this story), by what they show.

  PY scripts/imagerepeat.py JOB            compare every scene picture with all earlier generated pictures; exit 1 on !!
  PY scripts/imagerepeat.py --index        only bring the index of C:/ComfyUI/output up to date

Story 14 (2026-11-28): the user saw a column of soldiers in the snow and knew the picture from an earlier film. All 646
pictures were newly generated (no file reused, no near-identical pixels), yet 15 of them were the same picture as one of
an earlier story: the same column, the same row of tanks, the same bridge, the same transport plane. Z-Image falls back on
one stock composition for a generic line ("soldiers march through snow"), whatever the prompt adds; picture 396 was asked
as a night charge under flares and came out as the daylight column. The projects of earlier stories are deleted, but their
pictures stay in C:/ComfyUI/output, so they can be compared there.

Measure: CLIP image embedding (openai/clip-vit-base-patch32), cosine similarity. Looked at in pairs on story 14:
  >= 0.95  the same picture again (same subject, framing, light): !!
  0.92-0.95 the same kind of picture, visibly another one: counted, reported as !
  about 0.90 same subject, different picture
Needs a Python with torch and transformers (the one Whisper uses); the script starts itself there. The index
(stories/image-index/) is filled once (about 4 minutes for 33,000 pictures) and then only gets the new files.

Remedy for a !!: remake that beat as another picture OF THE SAME SENTENCE, not another seed of the same prompt and not
another subject (story 14: the first remakes fled to unrelated pictures, an alley for an explosion, a barn for squealing tracks): take the one thing in the
narration that only this moment has (a named man doing something, an object, a particular place) and make it the subject
in the foreground; change shot size and angle. A stock wide shot of "soldiers / tanks / a bridge in snow" is what repeats.
"""
import hashlib, json, os, subprocess, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parent))
INDEX = ROOT / 'stories' / 'image-index'
COMFY = Path(os.environ.get('COMFY_OUTPUT', 'C:/ComfyUI/output'))
SAME = 0.95      # the same picture again
NEAR = 0.92      # the same kind of picture
MODEL = 'openai/clip-vit-base-patch32'


def torch_python():
    home = Path.home()
    for c in (os.environ.get('WHISPER_PYTHON'), sys.executable, home / 'AppData/Local/Programs/Python/Python313/python.exe',
              home / 'AppData/Local/Programs/Python/Python312/python.exe'):
        if c and Path(c).exists() and subprocess.run([str(c), '-c', 'import torch, transformers'], capture_output=True).returncode == 0:
            return str(c)
    raise RuntimeError('no Python with torch and transformers found: set env WHISPER_PYTHON')


def embed(files):
    """float16 array (n, 512), rows normalised."""
    import numpy as np, torch
    from concurrent.futures import ThreadPoolExecutor
    from PIL import Image
    from transformers import CLIPModel, CLIPProcessor
    dev = 'cuda' if torch.cuda.is_available() else 'cpu'
    model = CLIPModel.from_pretrained(MODEL).to(dev).eval(); proc = CLIPProcessor.from_pretrained(MODEL)

    def load(f):
        try:
            im = Image.open(f).convert('RGB'); im.thumbnail((448, 448))
        except Exception:
            im = Image.new('RGB', (224, 224))
        return im
    out = []
    with torch.no_grad(), ThreadPoolExecutor(8) as ex:
        for k in range(0, len(files), 128):
            ims = list(ex.map(load, files[k:k + 128]))
            e = model.get_image_features(pixel_values=proc(images=ims, return_tensors='pt')['pixel_values'].to(dev))
            e = e if isinstance(e, torch.Tensor) else e.pooler_output
            out.append(torch.nn.functional.normalize(e.float(), dim=-1).cpu().numpy().astype('float16'))
    return np.concatenate(out) if out else np.zeros((0, 512), 'float16')


def update_index():
    """(paths, embeddings) of every PNG under the ComfyUI output folder; new files are added."""
    import numpy as np
    INDEX.mkdir(parents=True, exist_ok=True)
    pf, ef = INDEX / 'paths.json', INDEX / 'emb.npy'
    paths = json.loads(pf.read_text(encoding='utf-8')) if pf.exists() and ef.exists() else []
    emb = np.load(ef) if paths else np.zeros((0, 512), 'float16')
    have = set(paths); new = []
    for root, _, fs in os.walk(COMFY):
        for f in fs:
            p = os.path.join(root, f).replace('\\', '/')
            if f.lower().endswith('.png') and p not in have:
                new.append(p)
    if new:
        print(f'  indexing {len(new)} new pictures of {COMFY} ...', flush=True)
        emb = np.concatenate([emb, embed(sorted(new))]); paths += sorted(new)
        np.save(ef, emb); pf.write_text(json.dumps(paths), encoding='utf-8')
    return paths, emb


def judge(names, best, own):
    """best: {scene: (similarity, older file)}; own: [(similarity, scene a, scene b)]. Returns findings (level, id, message)."""
    again = sorted((n for n in names if best.get(n, (0, ''))[0] >= SAME), key=lambda n: -best[n][0])
    near = [n for n in names if NEAR <= best.get(n, (0, ''))[0] < SAME]
    twins = [(a, b) for v, a, b in own if v >= SAME]
    out = []
    how = ('remake each as ANOTHER picture (not another seed of the same prompt): it must still show what the sentence of that beat SAYS (story 14: the remake of "a great flash and a crack" became a quiet lamp-lit alley), seen another way: the thing the sentence names in the foreground, another shot size and angle; '
           'then run scripts/imagerepeat.py again. qa/imagerepeat-*.jpg shows every pair')
    if again:
        out.append(('!!', f'image-repeat:{again[0]}', f'{len(again)} picture(s) are the same picture as one of an earlier story (similarity >= {SAME}): '
                    + ', '.join(f'{n} ({best[n][0]:.2f} {Path(best[n][1]).name})' for n in again[:40]) + f'. {how}'))
    if twins:
        out.append(('!!', f'image-twin:{twins[0][0]}', f'{len(twins)} pair(s) inside this story are the same picture twice: ' + ', '.join(f'{a}={b}' for a, b in twins[:30]) + f'. {how}'))
    if near:
        out.append(('!', 'image-near', f'{len(near)} of {len(names)} pictures are the same kind of picture as an earlier one ({NEAR}-{SAME}); the model keeps a few stock compositions: '
                    'for the next story give more beats a subject of their own'))
    return out


def run(job):
    import numpy as np
    from common import job_dir
    d = Path(job_dir(job)); scenes = sorted((d / 'media' / 'scenes').glob('*.png'))
    if not scenes:
        print('no media/scenes/*.png: nothing to compare'); return []
    paths, emb = update_index()
    start = min(s.stat().st_mtime for s in scenes)
    mt = np.array([os.stat(p).st_mtime if os.path.exists(p) else 9e18 for p in paths])
    old = np.where(mt < start - 60)[0]
    E = embed([str(s) for s in scenes]).astype('float32'); names = [s.name for s in scenes]
    sim = E @ emb[old].astype('float32').T if len(old) else np.zeros((len(scenes), 1), 'float32')
    best = {}
    for k, n in enumerate(names):
        order = np.argsort(-sim[k])[:3]
        for j in order:           # a picture kept from an earlier run of the same story is this picture, not an earlier story's
            p = paths[old[j]] if len(old) else ''
            if p and sim[k, j] > 0.995 and os.stat(p).st_size == scenes[k].stat().st_size and hashlib.md5(open(p, 'rb').read()).hexdigest() == hashlib.md5(scenes[k].read_bytes()).hexdigest():
                continue
            best[n] = (float(sim[k, j]), p); break
    self_sim = E @ E.T
    own = sorted(((float(self_sim[a, b]), names[a], names[b]) for a, b in np.argwhere(np.triu(self_sim, 1) >= NEAR)), reverse=True)
    finds = judge(names, best, own)
    (d / 'qa').mkdir(exist_ok=True)
    key = f'{len(scenes)}|{int(max(s.stat().st_mtime for s in scenes))}'
    (d / 'qa' / 'imagerepeat.json').write_text(json.dumps({'key': key, 'finds': finds, 'best': best, 'own': own[:200]}, ensure_ascii=False), encoding='utf-8')
    sheets(d, [(n, best[n][1], best[n][0]) for n in names if best.get(n, (0,))[0] >= SAME] + [(a, str(d / 'media' / 'scenes' / b), v) for v, a, b in own if v >= SAME])
    return finds


def sheets(d, pairs):
    from PIL import Image, ImageDraw
    for f in (d / 'qa').glob('imagerepeat-*.jpg'):
        f.unlink()
    W, H = 480, 270
    for s in range(0, len(pairs), 12):
        part = pairs[s:s + 12]; sheet = Image.new('RGB', (W * 4, H * ((len(part) + 1) // 2)))
        for i, (n, other, v) in enumerate(part):
            for k, (src, lab) in enumerate(((d / 'media' / 'scenes' / n, f'this story {n}'), (other, f'{v:.2f} {Path(other).name[:28]}'))):
                try:
                    im = Image.open(src).convert('RGB').resize((W, H))
                except Exception:
                    im = Image.new('RGB', (W, H))
                dr = ImageDraw.Draw(im); dr.rectangle((0, 0, 300, 18), fill=(0, 0, 0)); dr.text((4, 3), lab, fill=(255, 220, 0))
                sheet.paste(im, (((i % 2) * 2 + k) * W, (i // 2) * H))
        sheet.save(d / 'qa' / f'imagerepeat-{s // 12 + 1:02d}.jpg', quality=86)


def check(d):
    """For the gate: the stored result when no scene picture changed since, else a fresh run in the torch Python."""
    d = Path(d); scenes = sorted((d / 'media' / 'scenes').glob('*.png'))
    if not scenes:
        return []
    key = f'{len(scenes)}|{int(max(s.stat().st_mtime for s in scenes))}'
    f = d / 'qa' / 'imagerepeat.json'
    try:
        j = json.loads(f.read_text(encoding='utf-8'))
    except (OSError, ValueError):
        j = {}
    if j.get('key') != key:
        try:
            r = subprocess.run([torch_python(), str(Path(__file__).resolve()), d.name], capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=3600)
            j = json.loads(f.read_text(encoding='utf-8'))
        except Exception as e:  # noqa: BLE001
            return [('!!', 'image-repeat:not-run', f'scripts/imagerepeat.py could not compare the pictures with earlier stories ({str(e)[:160]})')]
        if j.get('key') != key:
            return [('!!', 'image-repeat:not-run', 'scripts/imagerepeat.py did not finish: ' + (r.stdout + r.stderr)[-300:])]
    return [tuple(x) for x in j.get('finds', [])]


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    try:
        import torch, transformers  # noqa: F401
    except ImportError:
        sys.exit(subprocess.run([torch_python(), str(Path(__file__).resolve())] + sys.argv[1:]).returncode)
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    if sys.argv[1] == '--index':
        p, _ = update_index(); print(len(p), 'pictures in the index'); sys.exit(0)
    found = run(sys.argv[1])
    for lv, i, m in found:
        print(lv, i, m)
    print(f'{len(found)} finding(s)'); sys.exit(1 if any(f[0] == '!!' for f in found) else 0)
