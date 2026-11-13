# Z-Image local: backup image source for stories

Use this when the user says **"gen qua z-image"** (or "z-image local"), or when TST/auto-image and Google Flow keep failing. It is free, offline and needs no reference images. Speed is about 7.7 s per image on the user's GPU, so 700 images take about 1.5 h.

It was proven on the Army Group Centre story (2026-11-12): 794/794 images, no failures, characters consistent.

## 1. The server: started automatically, never ask the user

- ComfyUI lives in `C:\ComfyUI` on port 8188. `zimage_batch.py` checks the port and, if ComfyUI is down, starts it by itself (user rule 2026-11-12: "cho nó bật luôn chứ").
  - It uses exactly AutoVeo3's launch from `gui/whisk_widget.py`: Python313 `pythonw.exe C:\ComfyUI\main.py --listen --port 8188 --highvram --cuda-device 0 --force-channels-last --preview-method none --dont-print-server --disable-xformers`, with the same env and no window.
  - The process is detached, waits up to 180 s for the model and logs to `comfyui_zimage.log`.
- If ComfyUI is already running (the user's AutoVeo3 or TOOL SY started it), the script uses that one.
- Do not launch it with the system Python (it lacks ComfyUI's packages) or with other flags (slower).

## 2. Settings: copy these exactly

| setting | value |
|---|---|
| model | `zimage_turbo_gguf_q4` (Z-Image Turbo GGUF Q4) |
| size | **1024×576** |
| steps | **8** |
| CFG | **1.0** |
| sampler | euler / simple |

**Never use the CFG 5.5 / 10 steps from `z_image_config.md` or the code's "Nhanh" preset.** On the turbo model those give black blobs; they cost an hour of wrong debugging on 2026-11-12.

When a local model misbehaves, read a good image's PNG metadata first (`prompt` chunk). The user's own Whisk-tab output is the reference.

## 3. Prompts: Character Sheet + one Seed, no reference images

- Write the scene prompts as usual: JSON lines `{"n", "refs", "prompt"}` with `@Name`, one per ~8 s beat. Follow `docs/STORY_MODE.md` (images and pacing) and the brief in `_gen/PROMPT_BRIEF.md`:
  - the first sentence gives shot size, angle, camera move and light;
  - every person without a reference gets a nationality and a place;
  - prompts are policy-safe.
- Write `chars.json` with one fixed sheet per main character, in the format of `G:\YOUTUBE\US- Military Chronicle\GEM_PROMPT_MILITARY_CHRONICLE.txt`:
  - give the full name;
  - in brackets: nationality, age, face shape, glasses/moustache, hair, headgear, uniform with rank details, and one signature item;
  - make the faces visibly different from earlier stories (`stories/published/refs/`);
  - a recurring vehicle or object is `{"object": "…"}`.
- Convert:

  ```
  PY scripts/zimage_prompts.py chars.json _gen/zimage_jobs.json _gen/prompts_*.jsonl --seed 44817 --tail "Authentic 1944 period photograph, well exposed, clear detail, full tonal range."
  ```

  Each prompt becomes: `black-and-white war documentary style. <camera sentence> Character Sheet: <each visible character>. <scene> <tail> Seed: 44817.`
  - The sheet is repeated in every image where that character appears, and one seed is used for the whole film. That is what keeps faces the same.
  - Use a new seed for a new story.

## 4. Running: Smart Queue, no idle GPU

```
PY scripts/zimage_batch.py "input/<story>" _gen/zimage_jobs.json --threads 8 > _gen/zimage_run.log
```

- It uses AutoVeo3's own `core/comfyui_api.py` client, which provides the tool's "Smart Queue & Polling":
  - the timeout is frozen while the job is pending;
  - `/queue` is polled every 2 s;
  - `/history` and `/view` fetch the result;
  - negative prompt, quote stripping and Seed handling match the tool.
- 8 threads keep jobs waiting in ComfyUI's queue, so the GPU never idles between images. More threads do not help, because the GPU is the limit.
- It skips images that already exist (`NNN.png`), so a rerun only makes what is missing. Each image gets 3 tries; failures are listed at the end. `--only 7,30 --force` remakes chosen images.
- Run it in the background. A stall check means comparing the log time with the image count; the log prints every 10 images.
- The title image (`story.title_image`) and the thumbnail base use the same script with a small jobs file of their own, written directly in Z-Image form (Character Sheet + Seed).

## 5. Checks before `doc.py story`

- **First, the defect check from `docs/STORY_MODE.md`.** It applies to every image source: numbered 9-per-sheet review by parallel agents, then a second strict pass.
- To remake an image, rewrite its scene in positive words and change the seed (`Seed: 52219` …). CFG 1.0 ignores "no …" phrases, so a fix like "no road markings" draws road markings.

- Make contact sheets with the beat text using `PY scripts/story_sheet.py "input/<story>" JOB out.jpg 1-10` for the first 10, then spot-check about every 9th image across the film (`100-370:9`, `375-600:9`, …). Check that:
  - faces match the sheets;
  - nationality and era are right;
  - the picture matches the words.
- Some images come out in colour. That is fine: the `archival` grade renders them monochrome.
- Tanks may not look exactly like the named model. Accept that unless the beat is about the vehicle.
- Do not mix sources without telling the user. Flow/TST images are sharper than Z-Image, so offer to remake them for a uniform look (about 10 min per 79 images).

## What Z-Image cannot draw: avoid it in prompts (Refugees Filled Every Road, 2026-11-12)

About 25 % of 730 images failed the first defect check, and some subjects failed again after two rewrites. Leave these out of the prompts from the start:
- **Helmets** always come out as US M1 helmets. Soldiers wear soft field caps or side caps.
- **Headphones, throat microphones and radios** draw a microphone ball at the moustache and hands on the head. Never put them in a Character Sheet.
- **Panzerfausts and launchers** come out as a trumpet or a pipe held to the ear. Show a rifle or an ammunition crate instead.
- **Tank interiors** draw car steering wheels and windows. Show crew faces outdoors, and tanks from the side, outdoors, alone in the frame.
- **Ships** come out white and modern, with names on the hull. Show them as small dark cutters far away in mist.
- **Mailboxes and letter boxes** draw an American roadside mailbox. Write "a small square wooden crate of letters".
- **Bicycles and horse herds** come out merged. Show one horse between the two shafts of one wagon.
- **People lying down** (wounded, stretchers, the dead) are flagged every time. Show an object or an empty landscape instead.

## Not to do

- No Google Flow bulk runs through Claude in Chrome. After about 60 images it showed "unusual activity"; stop, and never evade bot detection or reCAPTCHA.
- Do not overwrite the tool's `comfyui_server.log` or restart its server.
