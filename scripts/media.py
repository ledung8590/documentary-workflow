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
UA = 'documentary-workflow/0.1 (' + (os.environ.get('WIKIMEDIA_CONTACT') or 'personal research tool') + ') python-urllib'
PREVIEW_W, FULL_W, PAUSE = 500, 1920, 3.0   # browse at 500 px, download 1920 px only for picked files
ALLOWED = re.compile(r'^(public domain|pd\b|pd-|cc0|cc[- ]?by(-sa)?[- ]?\d|cc[- ]?by(-sa)?$|no restrictions|no known copyright)', re.I)
REJECT = re.compile(r'(\bnc\b|non-?commercial|\bnd\b|noderiv|fair use|editorial|all rights reserved)', re.I)
REPHOTO = re.compile(r'(museum|bảo tàng|exhibit|display|on show|plaque|poster at)', re.I)


def _get(url, headers=None, timeout=40, tries=4):
    """Polite GET: Wikimedia rate-limits bursts (HTTP 429), so back off and honour Retry-After."""
    import time
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
                    'page': ii.get('descriptionurl'), 'preview': _smaller(ii.get('thumburl')),
                    'download': ii.get('url') if kind == 'video' else (ii.get('thumburl') or ii.get('url')),
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


def dvids(query, n=20, kind='photo'):
    if kind == 'video':  # DVIDS video files need its asset API; not wired yet
        return []
    key = os.environ.get('DVIDS_API_KEY')
    if not key and sys.platform == 'win32':
        import winreg
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, 'Environment') as h:
                key = winreg.QueryValueEx(h, 'DVIDS_API_KEY')[0]
        except OSError:
            key = None
    if not key:
        return []
    q = urllib.parse.urlencode({'q': query, 'type[]': 'image', 'max_results': n, 'api_key': key})
    data = json.loads(_get(f'https://api.dvidshub.net/search?{q}'))
    return [{'source': 'dvids', 'id': r['id'], 'title': r.get('title') or '', 'page': r.get('url'),
             'download': (r.get('thumbnail') or {}).get('url') if isinstance(r.get('thumbnail'), dict) else r.get('thumbnail'),
             'width': None, 'height': None, 'licence': 'Public domain (US government work)', 'licence_url': '',
             'author': r.get('credit') or 'DVIDS', 'credit': 'DVIDS', 'date': r.get('date') or '', 'description': (r.get('description') or '')[:400]}
            for r in data.get('results', [])]


SOURCES = {'commons': commons, 'openverse': openverse, 'dvids': dvids}


def search(query, sources=('commons', 'openverse', 'dvids'), n=20, kind='photo'):
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
        if not url:
            raise ValueError('no preview image')
        p.write_bytes(_get(url, timeout=60)); time.sleep(PAUSE)
    return p


def fetch_video(c, folder):
    """Download one video file (transcoded derivative first) into the candidate cache."""
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


def fetch_range(src, start, dur, out):
    """Cut [start, start+dur] of a local video to an H.264/AAC intermediate."""
    import subprocess
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-ss', f'{start:.3f}', '-i', str(src), '-t', f'{dur:.3f}',
                    '-c:v', 'libx264', '-crf', '16', '-preset', 'veryfast', '-pix_fmt', 'yuv420p',
                    '-c:a', 'aac', '-ar', '48000', '-ac', '2', str(out)], check=True, capture_output=True, timeout=600)
    return out


def download(c, folder):
    folder = Path(folder); folder.mkdir(parents=True, exist_ok=True)
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
