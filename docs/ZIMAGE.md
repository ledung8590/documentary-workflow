# Z-Image local: the default image source

**Default for every generated image since 2026-11-14** (user: TST Auto Generate Image is broken and switched off; use it only if the user asks for it again): story scenes (`/gentruyen`), story title images and thumbnail bases, and on the archival path (`/genvideo`) the reconstruction prints and the image-model thumbnail fallback (`docs/WORKFLOW.md`). It is free, offline and needs no reference images. Speed is about 8–9 s per image on the user's GPU, so 700 images take about 1.5 h; that GPU time is the floor, so the rest of the run is planned around it.

It was proven on Army Group Centre (2026-11-12): 794/794 images, characters consistent. Vitebsk (2026-11-14, 612 images) showed where the time goes: prompts written for TST had to be remade (~210 images, 1 h 15 min), so write them for Z-Image from the start (section 3) and check them while the batch runs (section 5).

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

- Write the scene prompts as JSON lines `{"n", "refs", "prompt"}` with `@Name` (e.g. "@Pohl sits beside …"), one per beat from `beats.json` (`scripts/story_beats.py`). Follow `docs/STORY_MODE.md` (images and pacing) and the brief in `_gen/PROMPT_BRIEF.md`:
  - the first sentence gives shot size, angle, camera move and light;
  - every person without a sheet gets a nationality and a place;
  - prompts are policy-safe.
  - **Z-Image-safe from the first draft:** every rule in "What Z-Image cannot draw" below goes into the brief given to prompt-writing agents. Never write "the man from reference image 1": that is the TST format.
- Write `chars.json` with one fixed sheet per main character, in the format of `G:\YOUTUBE\US- Military Chronicle\GEM_PROMPT_MILITARY_CHRONICLE.txt`:
  - give the full name;
  - in brackets: nationality, age, face shape, glasses/moustache, hair, headgear, uniform with rank details, and one signature item;
  - make the faces visibly different from earlier stories (`stories/published/refs/`);
  - a recurring vehicle or object is `{"object": "…"}`. A vehicle sheet states its real size: "a large heavy 24-ton armored vehicle as long as a truck, its thick armored hull as tall as a grown man". Never "low", "small", "compact" or "box-shaped" (Korsun 2026-11-15: "low and wide" drew a toy-sized gun with the commander out to the waist in 14 images; "box-shaped" drew white vans).
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

## 5. Checks: while the batch runs, then before `doc.py story`

- **First, the defect check from `docs/STORY_MODE.md`.** It applies to every image source: numbered 9-per-sheet review by parallel agents, then a second strict pass.
- **Start it during the batch, not after.** The batch fills numbers in order, so as soon as a block of ~100 images exists (count `NNN.png`), make its sheets (`story_sheet.py "input/<story>" JOB qa/sheets_NNN --qa 101-200`) and hand them to a review agent; queue the rewritten prompts as a second `zimage_batch.py … --force` run next to the main one (both share ComfyUI's queue). By the time the last image is made, only its block is left to check.
- **Remakes go back through the same review**: a fresh agent checks every remade image against its old defect. Plan on two rounds; after that, accept a minor flaw rather than a fourth try (a rewrite that changes the composition works better than repeating the same subject).
- **Then `doc.py story`, once**: it copies the images into `media/scenes/`. Any image changed after that needs `doc.py story` again before the draft render.
- To remake an image, rewrite its scene in positive words and change the seed (`Seed: 52219` …). CFG 1.0 ignores "no …" phrases, so a fix like "no road markings" draws road markings.

- Make contact sheets with the beat text using `PY scripts/story_sheet.py "input/<story>" JOB out.jpg 1-10` for the first 10, then spot-check about every 9th image across the film (`100-370:9`, `375-600:9`, …). Check that:
  - faces match the sheets;
  - nationality and era are right;
  - the picture matches the words.
- Some images come out in colour. That is fine: the `archival` grade renders them monochrome.
- **The hero's vehicle must read as its named model.** Viewers know tanks: on Refugees a viewer commented at 1:26 "just what is this tank supposed to be? It sure ain't a Panther" (2026-11-15). So for every named vehicle that recurs (the crew's tank, gun or plane):
  1. Write the sheet from the model's **visible features**, not its name. Example Panther: "sloped front armor plate, long gun with a double-baffle muzzle brake, large overlapping interleaved road wheels, armor skirt plates over the upper tracks, rounded gun mantlet"; StuG III: "turretless, low flat-roofed armored casemate, short thick gun set in the front plate, six small road wheels". Plus the real size (§3).
  2. **Test the sheet before the batch**: 8 seeds on one plain side-view prompt, contact sheet, and check it against a real photo of the model. Keep the wording that reads right.
  3. If no wording works (Z-Image cannot draw a turretless StuG; it adds a turret, tested Korsun 2026-11-15), use **real archival photos** of the model for the beats where the vehicle is the subject (user idea, Korsun): `doc.py media JOB search "Bundesarchiv Sturmgeschütz III" --tag T --sources commons`, then `doc.py media JOB pick V### T K --caption "…"` on that beat's clip (5–10 per film, winter/mud ones first; Bundesarchiv CC BY-SA 3.0 DE, same strict credits as `/genvideo`: `pick` draws "caption · Bundesarchiv, Bild <signature> / <photographer> / CC BY-SA 3.0 de" on screen and writes the `LICENSES.md` row; check one frame with `render_frame`; the story description gets the block printed by `PY scripts/description.py JOB --intro x --tags … --hashtags … --cc-links --credits-only` (every file with its Bild signature and Commons link, plus the licence deed), pasted above the hashtags). Never paste a real vehicle into a generated image (light and grain never match). In all other images do not show the vehicle whole and clear. Show details (tracks, hatch rim, gun barrel, muzzle, mud on the road wheels), the crew beside it, the vehicle far off, at night, in snow or smoke. Tell the user at the review stop which model could not be drawn.
  4. Other, unnamed vehicles may stay generic.
- Do not mix sources without telling the user. Flow/TST images are sharper than Z-Image, so offer to remake them for a uniform look (about 10 min per 79 images).

## What Z-Image cannot draw: avoid it in prompts (Refugees Filled Every Road, 2026-11-12)

About 25 % of 730 images (Refugees) and 30 % of 612 (Vitebsk, prompts written for TST) failed the first defect check, and some subjects failed again after two rewrites. Leave these out of the prompts from the start:
- **Helmets** always come out as US M1 helmets. Soldiers wear soft field caps or side caps.
- **Headphones, throat microphones and radios** draw a microphone ball at the moustache and hands on the head. Never put them in a Character Sheet.
- **Panzerfausts and launchers** come out as a trumpet or a pipe held to the ear. Show a rifle or an ammunition crate instead.
- **Tank interiors** draw car steering wheels and windows. Show crew faces outdoors, and tanks from the side, outdoors, alone in the frame.
- **Crew in a hatch shrinks the vehicle**: "head and shoulders above the hatch" with a character sheet draws the man out to the waist on a go-kart-sized tank. Write the vehicle as "the big heavy …, filling the frame" and the man "small on the armored roof, only head and shoulders above the hatch rim", or show the crew beside or seated high on the hull ("boots dangling well above the snow"). When the character is not needed, leave him out of `refs` (with a ref the model puts him standing in front of the vehicle). Every vehicle-with-people image gets a scale check in the defect pass.
- **"Track" alone draws railway tracks and locomotives** (Korsun 511: "hit our left track" became a railway). Write "the heavy steel caterpillar tread of an armored vehicle on an open snowy field". To hide a vehicle's shape, "Extreme close-up … the whole frame is filled by tread links and one road wheel"; a plain "close-up of the track" still draws the whole tank.
- **Ships** come out white and modern, with names on the hull. Show them as small dark cutters far away in mist.
- **Mailboxes and letter boxes** draw an American roadside mailbox. Write "a small square wooden crate of letters".
- **Bicycles and horse herds** come out merged. Show one horse between the two shafts of one wagon.
- **People lying down** (wounded, stretchers, the dead) are flagged every time. Show an object or an empty landscape instead.
- **Soldiers in general get US M1 helmets** even when no helmet is named (Vitebsk: whole columns). Write the headgear for every soldier and crowd: "plain soft field-grey side caps", Soviets "pilotka side caps".
- **Insignia:** caps grow eagle or swastika-like badges, collars Iron Crosses and SS-like runes. Write "a plain side cap", "plain collar"; keep medals and badges out of every prompt.
- **Anything with writing** (crates, signs, maps, gauges, dials, cigarette packs, tins, wagon plates, tank hulls, notes) gets gibberish letters or numbers. Show papers closed or folded, crates plain and unmarked, maps as a folded paper in a hand; tanks "plain, from the side".
- **Radios and batteries** come out as 1950s transistor radios, boomboxes or rows of AA cells; a hand near the ear becomes a phone or walkie-talkie. Write "a heavy square grey steel army field radio case, lid closed, seen from the side" with nobody holding anything to the ear, batteries "small square grey steel cases".
- **Machine guns (MG42)** come out as rifles or with odd shields; accept a rifle, or show the gun small on a parapet.
- **Accordions, pianos, harmoniums up close** get impossible keys, buttons and logos. Show them closed, at a distance, or hands with a small file over a plain wooden block.
- **Hands at the head** (temple, ear, cap) read as salutes; write where the hands are: on a rifle sling, in pockets, around a mess tin, on the knees.
- **Modern backgrounds:** cities draw high-rises, asphalt with lane lines and 1960s trucks; write "a wide cobbled boulevard with 1930s stone buildings", "a canvas-covered 1940s truck" far away, and keep cars out.

## Not to do

- No Google Flow bulk runs through Claude in Chrome. After about 60 images it showed "unusual activity"; stop, and never evade bot detection or reCAPTCHA.
- Do not overwrite the tool's `comfyui_server.log` or restart its server.
