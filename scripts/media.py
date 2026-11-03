"""Search and download licensed archival images, with licence metadata per file (docs/MEDIA.md).

Sources: Wikimedia Commons (API, per-file licence fields), Openverse (CC/PD aggregator; confirm on the origin page),
DVIDS (US military, public domain; needs DVIDS_API_KEY). Google Images' "Creative Commons" filter is only a hint built
from page metadata, so we query the origin archives directly and read the licence of each file.

Licence gate: public domain / PD-* / CC0 / CC BY / CC BY-SA only. NC, ND, fair use, "editorial", unknown -> rejected.
A re-photograph of a print in a museum is flagged: the photographer's CC licence does not clear the original photo.
"""
import html, json, os, re, sys, urllib.error, urllib.parse, urllib.request
from pathlib import Path

# Wikimedia's User-Agent policy wants contact info; clients without it get much tighter rate limits.
# The user may set WIKIMEDIA_CONTACT (an email or URL they choose) in their environment; it is never stored here.
def _user_env(name):
    """Process environment, else the Windows user environment (so a value set after the shell started still counts)."""
    v = os.environ.get(name)
    if not v and sys.platform == 'win32':
        try:
            import winreg
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, 'Environment') as k:
                v = winreg.QueryValueEx(k, name)[0]
        except OSError:
            v = None
    return v


UA = 'documentary-workflow/0.1 (' + (_user_env('WIKIMEDIA_CONTACT') or 'personal research tool') + ') python-urllib'
PREVIEW_W, FULL_W, PAUSE = 500, 1920, 3.0   # browse at 500 px, download 1920 px only for picked files
ALLOWED = re.compile(r'^(public domain|pd\b|pd-|cc0|cc[- ]?by(-sa)?[- ]?\d|cc[- ]?by(-sa)?$|no restrictions|no known copyright)', re.I)
REJECT = re.compile(r'(\bnc\b|non-?commercial|\bnd\b|noderiv|fair use|editorial|all rights reserved)', re.I)
REPHOTO = re.compile(r'(museum|bảo tàng|exhibit|display|on show|plaque|poster at)', re.I)


def _get(url, headers=None, timeout=40, tries=4):
    """Polite GET: Wikimedia rate-limits bursts (HTTP 429), so back off and honour Retry-After."""
    import time
    # thumbnails are also served by thumb.wikimedia.org, which stays reachable when upload.wikimedia.org hangs
    url = url.replace('://upload.wikimedia.org/wikipedia/commons/thumb/', '://thumb.wikimedia.org/wikipedia/commons/thumb/')
    for k in range(tries):
        req = urllib.request.Request(url, headers={'User-Agent': UA, **(headers or {})})
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return r.read()
        except urllib.error.HTTPError as e:
            wait = float(e.headers.get('Retry-After') or 0) or 3 * 2 ** k
            if e.code != 429 or k == tries - 1:
                raise
            if wait > 60:
                raise RuntimeError(f'rate-limited by {urllib.parse.urlparse(url).netloc} for {wait:.0f} s; retry later') from None
            time.sleep(wait)


def _text(v):
    return re.sub(r'\s+', ' ', html.unescape(re.sub(r'<[^>]+>', '', v or ''))).strip()


def _smaller(thumb):
    """Same Commons thumbnail at the 500 px standard step (cheap browsing)."""
    return re.sub(r'/(\d+)px-', f'/{PREVIEW_W}px-', thumb) if thumb and '/thumb/' in thumb else thumb


def _as_thumb(url, width, want):
    """A Commons original (served when the file is narrower than iiurlwidth) as a thumbnail at the largest standard step
    below its width, so it comes from thumb.wikimedia.org too. Non-Commons or tiny files stay as they are."""
    m = re.match(r'(https://upload\.wikimedia\.org/wikipedia/commons)/(\w/\w\w)/([^/?]+)(\?.*)?$', url or '')
    if not m or not width or not re.search(r'\.(jpe?g|png|tiff?|webp)$', m.group(3), re.I):
        return url
    if want >= FULL_W and width < want:  # a picked file narrower than 1920 px: keep the original, never a smaller thumb step
        return url
    step = next((w for w in (want, 1280, 960, 500, 330, 250) if w <= want and w < width), None)
    if not step:
        return url
    base, hashdir, name, _ = m.groups()
    return f'{base}/thumb/{hashdir}/{name}/{step}px-{name}' + ('.jpg' if name.lower().endswith(('.tif', '.tiff')) else '')


def licence_ok(name):
    name = (name or '').strip()
    return bool(name) and bool(ALLOWED.search(name)) and not REJECT.search(name)


def commons(query, n=20, kind='photo'):
    q = urllib.parse.urlencode({
        'action': 'query', 'format': 'json', 'generator': 'search',
        'gsrsearch': f'{query} filetype:{"video" if kind == "video" else "bitmap"}',
        'gsrnamespace': 6, 'gsrlimit': n, 'prop': 'imageinfo', 'iiprop': 'url|extmetadata|size|mime',
        'iiurlwidth': FULL_W,  # standard thumb steps only (https://w.wiki/GHai); for video this is the poster jpg
        'iiextmetadatafilter': 'LicenseShortName|Artist|ImageDescription|DateTimeOriginal|Credit|LicenseUrl|UsageTerms'})
    data = json.loads(_get(f'https://commons.wikimedia.org/w/api.php?{q}'))
    if 'error' in data:
        raise ValueError(data['error'].get('info', 'commons API error'))
    out = []
    for p in sorted(data.get('query', {}).get('pages', {}).values(), key=lambda p: p.get('index', 0)):
        ii = (p.get('imageinfo') or [{}])[0]; md = ii.get('extmetadata', {})
        g = lambda k: _text(md.get(k, {}).get('value'))
        out.append({'source': 'commons', 'id': str(p['pageid']), 'title': p['title'].removeprefix('File:'),
                    'kind': kind, 'duration': ii.get('duration'), 'mime': ii.get('mime'),
                    'page': ii.get('descriptionurl'),
                    'preview': _as_thumb(_smaller(ii.get('thumburl')), ii.get('width'), PREVIEW_W),
                    'download': ii.get('url') if kind == 'video' else _as_thumb(ii.get('thumburl') or ii.get('url'), ii.get('width'), FULL_W),
                    'width': ii.get('width'), 'height': ii.get('height'), 'licence': g('LicenseShortName'),
                    'licence_url': g('LicenseUrl'), 'author': g('Artist'), 'credit': g('Credit'),
                    'date': g('DateTimeOriginal'), 'description': g('ImageDescription')[:400]})
    return out


def openverse(query, n=20, kind='photo'):
    if kind == 'video':
        return []
    q = urllib.parse.urlencode({'q': query, 'license': 'by,by-sa,cc0,pdm', 'page_size': n})
    data = json.loads(_get(f'https://api.openverse.org/v1/images/?{q}'))
    lic = lambda r: 'Public domain' if r['license'] == 'pdm' else ('CC0' if r['license'] == 'cc0' else f"CC {r['license'].upper()} {r.get('license_version') or ''}".strip())
    return [{'source': 'openverse:' + (r.get('source') or ''), 'id': r['id'], 'title': r.get('title') or '',
             'page': r.get('foreign_landing_url'), 'download': r.get('url'), 'width': r.get('width'),
             'height': r.get('height'), 'licence': lic(r), 'licence_url': r.get('license_url'),
             'author': r.get('creator') or '', 'credit': r.get('attribution') or '', 'date': '', 'description': ''}
            for r in data.get('results', [])]


def _key(name):
    """API key from the process environment, else the Windows user environment (set after this shell started)."""
    key = os.environ.get(name)
    if not key and sys.platform == 'win32':
        import winreg
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, 'Environment') as h:
                key = winreg.QueryValueEx(h, name)[0]
        except OSError:
            key = None
    return key


def dvids(query, n=20, kind='photo'):
    key = _key('DVIDS_API_KEY')
    if not key:
        return []
    if kind == 'video':
        return _dvids_video(query, n, key)
    q = urllib.parse.urlencode({'q': query, 'type[]': 'image', 'max_results': n, 'api_key': key})
    data = json.loads(_get(f'https://api.dvidshub.net/search?{q}'))
    return [{'source': 'dvids', 'id': r['id'], 'title': r.get('title') or '', 'page': r.get('url'),
             'download': (r.get('thumbnail') or {}).get('url') if isinstance(r.get('thumbnail'), dict) else r.get('thumbnail'),
             'width': None, 'height': None, 'licence': 'Public domain (US government work)', 'licence_url': '',
             'author': r.get('credit') or 'DVIDS', 'credit': 'DVIDS', 'date': r.get('date') or '', 'description': (r.get('description') or '')[:400]}
            for r in data.get('results', [])]


def _dvids_video(query, n, key):
    """DVIDS video search: one asset call per hit for its MP4 renditions (1080p preferred, never the multi-GB master).
    US Department of Defense productions are public domain; the credit names the unit."""
    q = urllib.parse.urlencode({'q': query, 'type[]': 'video', 'max_results': n, 'api_key': key})
    out = []
    for r in json.loads(_get(f'https://api.dvidshub.net/search?{q}')).get('results', []):
        try:
            a = json.loads(_get('https://api.dvidshub.net/asset?' + urllib.parse.urlencode({'id': r['id'], 'api_key': key})))
        except Exception:  # noqa: BLE001 - one bad asset must not sink the search
            continue
        a = a.get('results', a)
        files = [f for f in a.get('files') or [] if f.get('type') == 'video/mp4' and (f.get('width') or 0) <= 1920]
        if not files:
            continue
        f = max(files, key=lambda f: ((f.get('width') or 0), -(f.get('size') or 0)))
        out.append({'source': 'dvids', 'id': str(r['id']).replace('video:', 'video'), 'title': r.get('title') or '', 'kind': 'video',
                    'duration': a.get('duration'), 'page': a.get('url') or r.get('url'), 'preview': a.get('image'),
                    'download': f['src'], 'width': f.get('width'), 'height': f.get('height'),
                    'licence': 'Public domain (US government work)', 'licence_url': '',
                    'author': a.get('unit_name') or 'DVIDS', 'credit': 'DVIDS', 'date': (a.get('date') or '')[:10],
                    'description': (a.get('description') or '')[:400]})
    return out


def nara(query, n=20, kind='photo'):
    """US National Archives catalog (API v2, needs NARA_API_KEY). Only records whose use restriction is
    "Unrestricted" pass the licence gate; donated material with restrictions is labelled and rejected."""
    key = _key('NARA_API_KEY')
    if not key:
        return []
    # typeOfMaterials keeps text documents (deck logs, reports) out of photo searches
    q = urllib.parse.urlencode({'q': query, 'limit': n, 'availableOnline': 'true',
                                'typeOfMaterials': 'Moving Images' if kind == 'video' else 'Photographs and other Graphic Materials'})
    data = json.loads(_get(f'https://catalog.archives.gov/api/v2/records/search?{q}',
                           headers={'x-api-key': key, 'Content-Type': 'application/json', 'Accept': 'application/json'}))
    want = 'audio/visual file (mp4)' if kind == 'video' else 'image'  # NARA objectType: "Image (JPG)", "Audio/Visual File (MP4)"
    out = []
    for h in data.get('body', {}).get('hits', {}).get('hits', []):
        r = h.get('_source', {}).get('record', {})
        objs = [o for o in r.get('digitalObjects') or [] if want in (o.get('objectType') or '').lower()]
        if kind != 'video':  # browse JPG/PNG only; multi-hundred-MB TIFF masters are not worth a preview
            objs = [o for o in objs if re.search(r'\.(jpe?g|png)$', o.get('objectUrl') or '', re.I)
                    and (o.get('objectFileSize') or 0) < 40e6]
        status = (r.get('useRestriction') or {}).get('status') or 'Undetermined'
        lic = 'Public domain (NARA, unrestricted use)' if status.lower() == 'unrestricted' else f'NARA use restriction: {status}'
        date = ((r.get('productionDates') or [{}])[0] or {}).get('logicalDate') or ''
        author = '; '.join(c.get('heading', '') for c in (r.get('creators') or [])[:2]) or 'National Archives'
        for k, o in enumerate(objs[:2]):  # a file unit can hold hundreds of scans: keep the first two
            out.append({'source': 'nara', 'id': f"{r.get('naId')}-{k}" if k else str(r.get('naId')),
                        'title': r.get('title') or '', 'kind': kind, 'duration': None,
                        'page': f"https://catalog.archives.gov/id/{r.get('naId')}",
                        'preview': None, 'download': o.get('objectUrl'), 'width': None, 'height': None,
                        'licence': lic, 'licence_url': 'https://www.archives.gov/global-pages/privacy.html#copyright',
                        'author': author, 'credit': 'U.S. National Archives', 'date': date,
                        'description': _text((r.get('scopeAndContentNote') or ''))[:400]})
    return out[:n]


SOURCES = {'commons': commons, 'openverse': openverse, 'dvids': dvids, 'nara': nara}


def search(query, sources=('commons', 'openverse', 'dvids', 'nara'), n=20, kind='photo'):
    found, errors = [], []
    for s in sources:
        try:
            found += [{'kind': kind, **c} for c in SOURCES[s](query, n, kind)]
        except (urllib.error.URLError, OSError, ValueError, KeyError) as e:
            errors.append(f'{s}: {str(e)[:120]}')
    for c in found:
        c['allowed'] = licence_ok(c['licence'])
        c['flags'] = []
        if REPHOTO.search(c['title'] + ' ' + c['description']):
            c['flags'].append('re-photo of a display: check the original photo is PD before use')
        if c.get('width') and c['width'] < 1280:
            c['flags'].append(f'low resolution {c["width"]}px')
        if c.get('width') and c.get('height') and c['height'] > c['width']:
            c['flags'].append('portrait/vertical: needs a blurred-fill frame')
    return found, errors


def preview(c, folder):
    """Small preview for browsing (photo thumbnail or video poster at 500 px); the full file waits for `pick`."""
    import time
    folder = Path(folder); folder.mkdir(parents=True, exist_ok=True)
    p = folder / f"prev-{c['source'].split(':')[0]}-{re.sub(r'[^A-Za-z0-9_-]', '', str(c['id']))[:40]}.jpg"
    if not p.exists():
        url = c.get('preview') or (None if c.get('kind') == 'video' else c.get('download'))
        if not url and c.get('kind') == 'video' and c.get('download'):  # no poster (NARA): grab a frame over HTTP
            import subprocess
            subprocess.run(['ffmpeg', '-v', 'error', '-y', '-ss', '20', '-i', c['download'], '-frames:v', '1',
                            '-vf', f'scale={PREVIEW_W}:-2', str(p)], check=True, capture_output=True, timeout=120)
            return p
        if not url:
            raise ValueError('no preview image')
        p.write_bytes(_get(url, timeout=60)); time.sleep(PAUSE)
        from PIL import Image  # NARA has no thumbnail: the "preview" is the full scan (up to 236 MP), shrink it
        Image.MAX_IMAGE_PIXELS = None
        with Image.open(p) as im:
            big = im.width > 2 * PREVIEW_W
            if big:
                im.draft('RGB', (PREVIEW_W, PREVIEW_W)); sm = im.convert('RGB'); sm.thumbnail((PREVIEW_W, PREVIEW_W * 4))
        if big:
            sm.save(p, quality=88)
    return p


def fetch_video(c, folder):
    """Download one video file (transcoded derivative first) into the candidate cache."""
    if c['source'] in ('nara', 'dvids'):  # long reels / 1080p productions: ffmpeg reads only the needed range over HTTP
        return c['download']
    folder = Path(folder); folder.mkdir(parents=True, exist_ok=True)
    p = folder / f"{c['source'].split(':')[0]}-{c['id']}.webm"
    if p.exists():
        return p
    last = None
    for u in video_urls(c['download']):
        try:
            p.write_bytes(_get(u, timeout=300)); return p
        except urllib.error.HTTPError as e:
            last = e
            if e.code != 404:
                raise
    raise last


def clean_in(src, t_in, dur, look=10.0, fps=12):
    """In-point nearest t_in whose [in, in+dur] holds no camera cut, so a picked shot is one take. A cut a fraction
    of a second into a shot reads as a jerk on screen (user review 2026-10-31). Returns (in, cuts found near t_in)."""
    import subprocess
    import numpy as np
    a = max(0.0, t_in - look)
    raw = subprocess.run(['ffmpeg', '-v', 'error', '-ss', f'{a:.3f}', '-i', str(src), '-t', f'{dur + 2 * look:.3f}', '-an',
                          '-vf', f'fps={fps},scale=160:90,format=gray', '-f', 'rawvideo', '-'], capture_output=True, timeout=600).stdout
    x = np.frombuffer(raw, np.uint8)
    n = len(x) // (160 * 90)
    if n < 2:
        return t_in, []
    x = x[:n * 160 * 90].reshape(n, 90, 160).astype(np.float32)
    d = np.abs(np.diff(x, axis=0)).mean(axis=(1, 2))
    cuts = [a + (i + 1) / fps for i in np.where(d > 28)[0]]  # hard cut or flash frame
    end = a + n / fps
    ok = lambda s: s >= a and s + dur <= end and not any(s + 0.05 < c < s + dur - 0.05 for c in cuts)
    for step in range(int(look * fps) + 1):  # nearest clean start, either side of t_in
        for s in (t_in + step / fps, t_in - step / fps):
            if ok(s):
                return round(s, 3), cuts
    return t_in, cuts


def fetch_range(src, start, dur, out):
    """Cut [start, start+dur] of a local video to an H.264/AAC intermediate."""
    import subprocess
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-ss', f'{start:.3f}', '-i', str(src), '-t', f'{dur:.3f}',
                    '-vf', 'scale=trunc(iw/2)*2:trunc(ih/2)*2', '-c:v', 'libx264', '-crf', '16', '-preset', 'veryfast', '-pix_fmt', 'yuv420p',
                    '-c:a', 'aac', '-ar', '48000', '-ac', '2', str(out)], check=True, capture_output=True, timeout=600)
    return out


def dvids_full(c):
    """DVIDS search only returns a 122x92 thumbnail; the asset call names the full-size image (film 89 shipped 32 thumbnails)."""
    if c.get('source') != 'dvids' or c.get('kind') == 'video' or '/thumbs/' not in (c.get('download') or ''):
        return c
    a = json.loads(_get('https://api.dvidshub.net/asset?' + urllib.parse.urlencode({'id': c['id'], 'api_key': _key('DVIDS_API_KEY')})))
    a = a.get('results', a)
    return {**c, 'download': a['image']} if a.get('image') else c


def download(c, folder):
    folder = Path(folder); folder.mkdir(parents=True, exist_ok=True)
    c = dvids_full(c)
    ext = Path(urllib.parse.urlparse(c['download']).path).suffix.lower()
    ext = ext if ext in ('.jpg', '.jpeg', '.png', '.tif', '.tiff', '.webp') else '.jpg'
    p = folder / f"{c['source'].split(':')[0]}-{re.sub(r'[^A-Za-z0-9_-]', '', str(c['id']))[:40]}{ext}"
    if not p.exists():
        import time
        p.write_bytes(_get(c['download'], timeout=120))
        time.sleep(PAUSE)  # stay well under Wikimedia's burst limit
    return p


def video_urls(url):
    """Commons serves transcoded derivatives (1080p/720p VP9) next to the original; try those first."""
    u = url.split('?')[0]
    m = re.match(r'(https://upload\.wikimedia\.org/wikipedia/commons)/(\w/\w\w)/(.+)$', u)
    if not m:
        return [u]
    base, hashdir, name = m.groups()
    return [f'{base}/transcoded/{hashdir}/{name}/{name}.{r}.vp9.webm' for r in ('1080p', '720p')] + [u]


def contact_sheet(items, out, cols=4, w=480):
    from PIL import Image, ImageDraw, ImageOps
    h = int(w * 9 / 16); rows = (len(items) + cols - 1) // cols
    sheet = Image.new('RGB', (cols * w, rows * (h + 34)), (20, 20, 20)); d = ImageDraw.Draw(sheet)
    for k, (label, path) in enumerate(items):
        x, y = (k % cols) * w, (k // cols) * (h + 34)
        try:
            im = ImageOps.contain(Image.open(path).convert('RGB'), (w - 8, h - 8))
            sheet.paste(im, (x + (w - im.width) // 2, y + (h - im.height) // 2))
        except OSError:
            d.text((x + 10, y + 10), 'unreadable', fill=(255, 80, 80))
        d.text((x + 6, y + h + 4), label[:70], fill=(230, 230, 230))
    sheet.save(out, quality=85)
    return out
