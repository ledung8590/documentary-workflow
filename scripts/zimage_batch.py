"""Story images on the local Z-Image Turbo (ComfyUI), with the exact settings of the user's AutoVeo3 Whisk tab
("Z-Image Turbo GGUF Q4" as it really runs, read from its PNG metadata 2026-11-12: 1024x576, 8 steps, cfg 1.0,
euler/simple; z_image_config.md says cfg 5.5 / 10 steps and that breaks the turbo model into black blobs; its own ComfyUIClient, so the
negative prompt, quote stripping and Seed handling are identical). No reference images: prompts carry Character Sheets.

    PY scripts/zimage_batch.py "input/<story>" jobs.json [--only 7,30] [--threads 6] [--force]

jobs.json: [{"n": 12, "prompt": "... Seed: 44817."}]. Saves <story>/NNN.png; skips existing ones unless --force.
"""
import argparse, json, shutil, sys, threading, time, queue
from pathlib import Path
TOOL = Path(r'D:\YOUTUBE\TOOL_CODE_BY_ME\AutoVeo3_LeDung\VEO3_LD0201')
import importlib.util  # load the client file alone (the tool's core/__init__ pulls in its whole app)
_spec = importlib.util.spec_from_file_location('comfyui_api', TOOL / 'core' / 'comfyui_api.py')
_m = importlib.util.module_from_spec(_spec); _spec.loader.exec_module(_m); ComfyUIClient = _m.ComfyUIClient

COMFY = Path(r'C:\ComfyUI')
PY313 = Path.home() / 'AppData' / 'Local' / 'Programs' / 'Python' / 'Python313' / 'pythonw.exe'


def comfy_up():
    import urllib.request
    try:
        urllib.request.urlopen('http://127.0.0.1:8188/system_stats', timeout=3).read(); return True
    except Exception:
        return False


def ensure_comfy():
    """Start ComfyUI exactly as AutoVeo3's Whisk tab does (gui/whisk_widget.py: Python313 pythonw, same flags and env,
    no window), detached so it outlives this run; log in this repo, never the tool's comfyui_server.log."""
    if comfy_up():
        return
    import os, subprocess
    env = {**os.environ, 'TQDM_DISABLE': '1', 'DISABLE_TQDM': '1', 'HF_HUB_DISABLE_PROGRESS_BARS': '1',
           'AUTOVEO3_DISABLE_COMFY_PROGRESS': '1', 'PYTHONUNBUFFERED': '1', 'TORCHDYNAMO_DISABLE': '1',
           'TRITON_CACHE_MANAGER': 'disabled', 'TORCH_LOGS': '-all'}
    log = open(Path(__file__).resolve().parents[1] / 'comfyui_zimage.log', 'a', encoding='utf-8', errors='replace')
    print('ComfyUI not running: starting it like AutoVeo3 does', flush=True)
    subprocess.Popen([str(PY313), str(COMFY / 'main.py'), '--listen', '--port', '8188', '--highvram', '--cuda-device', '0',
                      '--force-channels-last', '--preview-method', 'none', '--dont-print-server', '--disable-xformers'],
                     cwd=str(COMFY), stdout=log, stderr=log, env=env,
                     creationflags=0x08000000 | 0x00000008 | 0x00000200)  # no window, detached, own process group
    for s in range(1, 181):
        if comfy_up():
            print(f'ComfyUI ready after {s} s', flush=True); return
        time.sleep(1)
    sys.exit('ComfyUI did not answer in 180 s: see comfyui_zimage.log')


ap = argparse.ArgumentParser(); ap.add_argument('story'); ap.add_argument('jobs')
ap.add_argument('--only'); ap.add_argument('--threads', type=int, default=6); ap.add_argument('--force', action='store_true')
a = ap.parse_args()
story = Path(a.story).resolve(); jobs = json.loads(Path(a.jobs).read_text(encoding='utf-8'))
if a.only:
    want = {int(x) for x in a.only.split(',')}; jobs = [j for j in jobs if j['n'] in want]
if not a.force:
    jobs = [j for j in jobs if not (story / f"{j['n']:03}.png").exists()]
print(f'{len(jobs)} images to make', flush=True)
if jobs:
    ensure_comfy()
q = queue.Queue(); [q.put(j) for j in jobs]
lock = threading.Lock(); done, failed, t0 = [0], [], time.time()


def work():
    cli = ComfyUIClient()
    while True:
        try:
            j = q.get_nowait()
        except queue.Empty:
            return
        for attempt in range(3):
            try:
                paths = cli.generate_image(prompt=j['prompt'], aspect_ratio='IMAGE_ASPECT_RATIO_LANDSCAPE',
                                           width_override=1024, height_override=576, steps=8, cfg=1.0,
                                           prompt_mode='light_only', model_key='zimage_turbo_gguf_q4', timeout=300)
                shutil.copy2(paths[0], story / f"{j['n']:03}.png")
                with lock:
                    done[0] += 1
                    if done[0] % 10 == 0 or done[0] == len(jobs):
                        el = time.time() - t0
                        print(f'{time.strftime("%H:%M:%S")} done {done[0]}/{len(jobs)} ({el / done[0]:.1f} s/img)', flush=True)
                break
            except Exception as e:
                print(f"n={j['n']} try {attempt + 1}: {str(e)[:160]}", flush=True)
                time.sleep(3)
        else:
            failed.append(j['n'])


ts = [threading.Thread(target=work) for _ in range(a.threads)]
[t.start() for t in ts]; [t.join() for t in ts]
print(f'finished: {done[0]} ok, failed {sorted(failed)}', flush=True)
