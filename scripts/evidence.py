"""Copyright evidence pack for a finished film, after the user has uploaded it (docs/WORKFLOW.md stage 14).

  PY scripts/evidence.py JOB            dry run: what would move, copy and be fetched
  PY scripts/evidence.py JOB --run      build evidence/<film name>/

Moves (not copies) the deliverables, the media files on screen and the project's record into evidence/<film name>/,
fetches each source's licence record (NARA catalog record, Commons file metadata + page, DVIDS asset + page),
copies the music/SFX actually used from assets/ (assets stay in place for later films) and writes INDEX.csv
(film time -> file -> source -> licence) and README.md (how to answer a claim). What stays in projects/<id>/ is
regenerable cache (render/, unused candidates, studio history) and is reported, never deleted here.
"""
import argparse, csv, json, re, shutil, sys, urllib.parse
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import ROOT
import media as M

OWN = {'scene-': 'Own work: animated graphic rendered from scenes/*.js in this pack (illustrative)',
       'map-': 'Own work: animated map (maps/*.json); basemap EOX Sentinel-2 cloudless 2016 (CC BY 4.0), terrain AWS Terrain Tiles'}
RECORD = ['timeline.json', 'script.txt', 'STORY.md', 'FACTS.md', 'brief.json', 'sentences.json', 'LICENSES.md',
          'description_youtube.txt', 'thumbnail.py', 'scenes', 'maps', 'voice/voice.wav', 'voice/voice.srt', 'voice/words.json']


def hms(t):
    return f'{int(t // 3600)}:{int(t % 3600 // 60):02d}:{t % 60:06.3f}'


def licence_rows(proj):
    rows = {}
    for line in (proj / 'LICENSES.md').read_text(encoding='utf-8').splitlines():
        if line.startswith('| media/'):
            c = [x.strip() for x in line.strip('|').split('|')]
            rows.setdefault(c[0], {'page': c[1], 'author': c[2], 'licence': c[3], 'credit': c[4], 'date': c[5]})
    return rows


def asset_rows(kind):
    rows = {}
    for line in (ROOT / 'assets' / kind / 'LICENSES.md').read_text(encoding='utf-8').splitlines():
        m = re.match(r'- `([^`]+)` — (.*)', line)
        if m:
            rows[m.group(1)] = m.group(2)
    return rows


def fetch_source(page, dest):
    """Licence record of one source page into dest.json (+ dest.html for human-readable pages). Never stores keys."""
    out = {'page': page}
    try:
        if 'catalog.archives.gov/id/' in page:
            na = page.rstrip('/').split('/')[-1]; key = M._key('NARA_API_KEY')
            r = json.loads(M._get(f'https://catalog.archives.gov/api/v2/records/search?naId={na}',
                                  headers={'x-api-key': key, 'Accept': 'application/json'}))
            hits = r.get('body', {}).get('hits', {}).get('hits', [])
            out['record'] = hits[0]['_source']['record'] if hits else None
        elif 'commons.wikimedia.org' in page:
            title = urllib.parse.unquote(page.split('/wiki/')[-1])
            q = urllib.parse.urlencode({'action': 'query', 'titles': title, 'prop': 'imageinfo', 'format': 'json',
                                        'iiprop': 'url|user|timestamp|extmetadata'})
            out['record'] = json.loads(M._get(f'https://commons.wikimedia.org/w/api.php?{q}'))
            dest.with_suffix('.html').write_bytes(M._get(page))
        elif 'dvidshub.net' in page:
            vid = re.search(r'/(video|image)/(\d+)', page)
            key = M._key('DVIDS_API_KEY')
            if vid and key:
                a = M._get('https://api.dvidshub.net/asset?' + urllib.parse.urlencode({'id': f'{vid.group(1)}:{vid.group(2)}', 'api_key': key}))
                out['record'] = json.loads(a.decode('utf-8', 'replace').replace(key, '<key>'))
            dest.with_suffix('.html').write_bytes(M._get(page))
    except Exception as e:  # noqa: BLE001 - a dead page is itself worth recording
        out['error'] = f'{type(e).__name__}: {e}'
    dest.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding='utf-8')
    return 'error' not in out


def mv(src, dst):
    """Move; a folder some process still holds open (the studio) is copied and its emptied shell left behind."""
    if src.is_dir():
        shutil.copytree(src, dst, dirs_exist_ok=True); shutil.rmtree(src, ignore_errors=True)
    else:
        shutil.move(str(src), dst)


def main():
    ap = argparse.ArgumentParser(); ap.add_argument('job'); ap.add_argument('--run', action='store_true')
    ap.add_argument('--name', help='folder name (default: the renamed video in output/<id>/, else the job id)')
    a = ap.parse_args()
    proj = ROOT / 'projects' / a.job; outd = ROOT / 'output' / a.job
    vids = [p for p in outd.glob('*.mp4')] if outd.exists() else []
    name = a.name or next((p.stem for p in vids if not p.stem.startswith('video')), a.job)
    dst = ROOT / 'evidence' / name
    base = proj if (proj / 'timeline.json').exists() else dst / 'project'  # a rerun after a partial move reads the moved record
    tl = json.loads((base / 'timeline.json').read_text(encoding='utf-8'))

    lic = licence_rows(base); amusic, asfx = asset_rows('music'), asset_rows('sfx')
    used, assets, index = {}, set(), []
    for tr in tl['tracks']:
        for c in tr['clips']:
            src = c.get('src') or (c.get('params') or {}).get('src')
            if not src or tr['id'] == 'voice':
                continue
            if src.startswith('../../assets/'):
                assets.add(src[len('../../assets/'):]); continue
            if src.startswith('media/'):
                used.setdefault(src, []).append(c)
    for src, cs in used.items():
        own = next((OWN[k] for k in OWN if Path(src).name.startswith(k)), None)
        r = lic.get(src) or (own and {'page': '', 'author': 'this channel', 'licence': own, 'date': ''})
        for c in cs:
            index.append({'start': hms(c['start']), 'end': hms(c['end']), 'track': 'fx' if 'params' in c else 'video', 'clip': c['id'],
                          'file': 'media/' + Path(src).name, 'caption': c.get('caption', ''), 'source_page': (r or {}).get('page', ''),
                          'licence': (r or {}).get('licence', 'UNKNOWN - check'), 'author': (r or {}).get('author', ''),
                          'downloaded': (r or {}).get('date', ''), 'source_record': ''})
    index.sort(key=lambda r: r['start'])
    pages = sorted({r['source_page'] for r in index if r['source_page']})
    unknown = sorted({r['file'] for r in index if r['licence'].startswith('UNKNOWN')})
    size = sum((proj / s).stat().st_size for s in used if (proj / s).exists())
    print(f'-> {dst}\n{len(used)} media files on screen ({size / 1e9:.2f} GB) move, {len(pages)} source records to fetch, '
          f'{len(assets)} music/SFX files copy from assets/, deliverables in {outd} move')
    if unknown:
        print('NO LICENCE ROW:', *unknown, sep='\n  ')
    if not a.run:
        print('dry run: add --run'); return

    for sub in ('video', 'media', 'sources', 'audio', 'project'):
        (dst / sub).mkdir(parents=True, exist_ok=True)
    # 1. licence records first (nothing moved yet if the network fails badly)
    rec = {}
    def one(p):
        import hashlib  # short names: the pack folder is long and Windows paths stop at 260 chars
        slug = re.sub(r'[^A-Za-z0-9._-]+', '_', re.sub(r'^https?://(www\.)?', '', p))[:60] + '-' + hashlib.md5(p.encode()).hexdigest()[:8]
        f = dst / 'sources' / f'{slug}.json'; rec[p] = f'sources/{slug}.json'
        if f.exists() and 'error' not in json.loads(f.read_text(encoding='utf-8')):
            return True  # rerun: already fetched
        return fetch_source(p, f)
    with ThreadPoolExecutor(6) as ex:
        ok = sum(ex.map(one, pages))
    print(f'source records: {ok}/{len(pages)} fetched')
    for r in index:
        r['source_record'] = rec.get(r['source_page'], '')
    # 2. move deliverables, media on screen, project record
    if outd.exists():
        for p in outd.iterdir():
            mv(p, dst / 'video' / p.name)
        shutil.rmtree(outd, ignore_errors=True)
    for src in used:
        if (proj / src).exists():
            mv(proj / src, dst / 'media' / Path(src).name)
    for rel in RECORD:
        p = proj / rel
        if p.exists():
            t = dst / 'project' / rel; t.parent.mkdir(parents=True, exist_ok=True); mv(p, t)
    # 3. copy (never move) the shared music/SFX used, with their licence lines
    lines = []
    for rel in sorted(assets):
        f = ROOT / 'assets' / rel
        if f.exists():
            t = dst / 'audio' / rel; t.parent.mkdir(parents=True, exist_ok=True); shutil.copy2(f, t)
        kind, sub = rel.split('/', 1)
        lines.append(f'- `{rel}` — ' + ((amusic if kind == 'music' else asfx).get(sub) or 'see assets/' + kind + '/LICENSES.md'))
    (dst / 'audio' / 'LICENSES.md').write_text('# Music and SFX used (copied from assets/)\n\n' + '\n'.join(lines) + '\n', encoding='utf-8')
    # 4. index + readme
    with open(dst / 'INDEX.csv', 'w', newline='', encoding='utf-8-sig') as fh:
        w = csv.DictWriter(fh, fieldnames=list(index[0])); w.writeheader(); w.writerows(index)
    (dst / 'README.md').write_text(f"""# Copyright evidence: {name}

Built {__import__('datetime').date.today()} from `projects/{a.job}` after upload.

- `video/`: the uploaded video, thumbnail, YouTube description, `LICENSES.md`, `credits.txt` and `qa.json`.
- `media/`: every picture and film clip that is on screen, as downloaded (or rendered, for own-work scenes and maps).
- `sources/`: the licence record of each source page, fetched when this pack was built:
  - NARA catalog record, including `useRestriction`;
  - Wikimedia Commons file metadata (`extmetadata`: LicenseShortName, Artist), plus the page HTML;
  - DVIDS asset record, plus the page HTML.
- `INDEX.csv`: one row per shot, giving film time, file, caption, source page, licence, author, download date and source record.
- `audio/`: copies of the music and SFX used, with their licence lines. The narration is AI voice, kept in `project/voice/voice.wav`.
- `project/`: the timeline, script, research notes, subtitles, the JS scene and map sources, and the thumbnail script.

## Answering a claim or a strike
1. Find the claimed segment's time in `INDEX.csv`. It gives the file, its source page and its licence.
2. For US federal government works (NARA, DVIDS, U.S. Navy/DoD photos, NHHC), cite **17 U.S.C. § 105**: such works are not subject to copyright. A third party's re-upload of the same footage gives that party no rights in it. Attach the record in `sources/` and the source page link.
3. For CC BY or CC0 files, cite the licence and the attribution already in the video description (`video/credits.txt`).
4. Own-work animated scenes and maps: the JS sources are in `project/scenes` and `project/maps`.
5. Music and SFX: see `audio/LICENSES.md`. ElevenLabs Sound Effects are used under the Starter plan's commercial licence.
""", encoding='utf-8')
    left = sum(p.stat().st_size for p in proj.rglob('*') if p.is_file())
    print(f'done: {dst}\nleft in {proj}: {left / 1e9:.2f} GB of regenerable cache (render/, unused candidates, voice clips, studio history)')


if __name__ == '__main__':
    main()
