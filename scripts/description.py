"""Paste-ready YouTube description (stage 13): projects/JOB/description_youtube.txt.

  PY scripts/description.py JOB --intro intro.txt [--note note.txt] --tags "t1, t2, ..., t7" --hashtags "#A #B ... #G" [--no-links]

The agent writes the intro (what the film is about) and an optional note (what is illustrative / reconstructed), in the
script's language. This script adds everything else from the project's own records, so the text can be pasted into
YouTube as it is:
- chapters from the timeline's chapter cards (first line 0:00);
- public-domain sources named by archive and author;
- every Creative Commons file on screen with author, licence and Commons ID (attribution the licences require);
- map basemap credit and music/SFX credit;
- a line of 7 #hashtags just above TAGS (YouTube shows the first ones above the title; user request 2026-11-01);
- the TAGS line (7 tags, comma-separated).
Few links (user 2026-11-04: a block of 49 archive links looks like spam): sources are named, Commons files by ID, with one link
that explains the IDs. --no-links strips every URL, only for a new channel the user names.
It never refers to files the viewer cannot see (no "see credits.txt"; user review 2026-11-01) and keeps the text under
YouTube's 5,000-character limit by shortening the public-domain author list first."""
import argparse, json, re, sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
T = {
    'en': dict(ch='CHAPTERS', first='Introduction', src='SOURCES & CREDITS', own='Narration, maps and animated graphics: original work of this channel.',
               pd='Public domain', cc='Creative Commons files on Wikimedia Commons (ID = Commons page ID):',
               maps='Map imagery: Sentinel-2 cloudless 2016 by EOX IT Services GmbH (CC BY 4.0). Terrain: AWS Terrain Tiles.',
               music='Music and sound effects: ElevenLabs (commercial licence).', other='Other open licences:', ccc='Creative Commons files on Wikimedia Commons, by licence and author:'),
    'de': dict(ch='KAPITEL', first='Einleitung', src='QUELLEN & NACHWEISE', own='Sprechertext, Karten und animierte Grafiken: eigenes Werk dieses Kanals.',
               pd='Gemeinfrei', cc='Creative-Commons-Bilder von Wikimedia Commons (ID = Commons-Seiten-ID):',
               maps='Kartenbilder: Sentinel-2 cloudless 2016 von EOX IT Services GmbH (CC BY 4.0). Gelände: AWS Terrain Tiles.',
               music='Musik und Soundeffekte: ElevenLabs (kommerzielle Lizenz).', other='Weitere offene Lizenzen:', ccc='Creative-Commons-Bilder von Wikimedia Commons, nach Lizenz und Urheber:'),
    'vi': dict(ch='CHƯƠNG', first='Mở đầu', src='NGUỒN & GHI CÔNG', own='Lời bình, bản đồ và đồ hoạ động: sản phẩm của kênh.',
               pd='Phạm vi công cộng', cc='Ảnh Creative Commons trên Wikimedia Commons (ID = mã trang tệp trên Commons):',
               maps='Ảnh bản đồ: Sentinel-2 cloudless 2016 của EOX IT Services GmbH (CC BY 4.0). Địa hình: AWS Terrain Tiles.',
               music='Nhạc và hiệu ứng âm thanh: ElevenLabs (giấy phép thương mại).', other='Giấy phép mở khác:'),
    'ja': dict(ch='チャプター', first='はじめに', src='出典とクレジット', own='ナレーション、地図、アニメーション図解: 当チャンネルのオリジナル制作。',
               pd='パブリックドメイン', cc='Wikimedia Commons のクリエイティブ・コモンズ素材:',
               maps='地図画像: Sentinel-2 cloudless 2016 (EOX IT Services GmbH, CC BY 4.0)。地形: AWS Terrain Tiles。',
               music='音楽と効果音: ElevenLabs (商用ライセンス)。', other='その他のオープンライセンス:', ccc='Wikimedia Commons のクリエイティブ・コモンズ素材(ライセンスと作者別):',
               idurl='各素材のページ: https://commons.wikimedia.org/?curid= の後に ID を付けてください。', pdids='パブリックドメイン素材の Commons ID:'),
    'es': dict(ch='CAPÍTULOS', first='Introducción', src='FUENTES Y CRÉDITOS', own='Narración, mapas y gráficos animados: obra original de este canal.',
               pd='Dominio público', cc='Archivos Creative Commons en Wikimedia Commons (ID = ID de página en Commons):',
               maps='Imágenes de mapas: Sentinel-2 cloudless 2016 de EOX IT Services GmbH (CC BY 4.0). Relieve: AWS Terrain Tiles.',
               music='Música y efectos de sonido: ElevenLabs (licencia comercial).', other='Otras licencias abiertas:'),
}
LIMIT = 5000
# --no-links only: a new channel without advanced-feature verification may not put external links in a description
URL = re.compile(r'\s*:?\s*https?://[^\s,]+|\s*:?\s*\b(?:www\.)?[\w-]+(?:\.[\w-]+)*\.(?:com|org|net|eu|be|gov|edu|io|uk|fr|de|vn|ru|jp|info)\b(?:/[^\s,]*)?', re.I)


def nolinks(s):
    return URL.sub('', s.replace('flickr.com', 'Flickr')).replace(' ,', ',')
# public-domain credits are named by archive, not by raw metadata strings
ORGS = [(r'National Archives|\bNARA\b', 'U.S. National Archives'), (r'U\.?S\.? Navy|\bUSN\b|Naval History', 'U.S. Navy'),
        (r'USAAF|U\.?S\.? Air Force|\bUSAF\b|United States Air Force', 'U.S. Air Force / USAAF'),
        (r'U\.?S\.? Army|United States Army|Signal Corps|Corps of Engineers', 'U.S. Army'), (r'\bNASA\b', 'NASA'),
        (r'DVIDS|Department of Defense|\bDoD\b', 'DVIDS / U.S. Department of Defense'), (r'Library of Congress', 'Library of Congress'),
        (r'Imperial War Museum|\bIWM\b|Royal Air Force official', 'Imperial War Museums (Crown copyright expired)'),
        (r'San Diego Air|SDASM', 'San Diego Air & Space Museum Archives'), (r'Bundesarchiv', 'Bundesarchiv'),
        (r'Australian War Memorial|\bAWM\b|Australian armed forces', 'Australian War Memorial'), (r'Newsreel', 'Universal Newsreels'),
        (r'Office of War Information|\bOWI\b|\bFSA\b', 'FSA/OWI (Library of Congress)')]


def clean_author(a, page):
    a = re.sub(r'<[^>]+>', '', a or '')
    a = re.sub(r'(?:br|span|div)\s*/?>', ' ', a)  # cut-off tags ("Wikipediabr/>", film 89): YouTube refuses < and >
    a = re.sub(r'\s+', ' ', a.replace('<', ' ').replace('>', ' ')).strip()
    a = re.sub(r'^(?:Unknown author|unknown)(?:\s*(?:Unknown author|unknown))*', 'unknown author', a, flags=re.I)
    a = re.split(r'\s*\((?:Original|Originaltext)|\s+—\s+|\.\s+\(', a)[0].strip()
    if 'Fortepan' in a:
        a = 'Fortepan'
    if re.match(r'The original uploader was (.+?) at ', a):
        a = re.match(r'The original uploader was (.+?) at ', a).group(1)
    if re.fullmatch(r'(own work|собственная работа|eigenes werk|trabajo propio|travail personnel)', a, re.I):
        a = 'Wikimedia Commons uploader (own work)'
    m = re.search(r'Bundesarchiv[_ ]((?:B[_ ]\d+[_ ])?Bild[_ -][\w-]+)', page or '')
    if m:  # Bundesarchiv CC BY-SA 3.0 DE requires "Bundesarchiv, Bild <signature>" (also "B 145 Bild-F…")
        return 'Bundesarchiv, ' + m.group(1).replace('_', ' ')
    return (a or 'unknown author')[:70]


def ts(s):
    return f'{int(s // 3600)}:{int(s % 3600 // 60):02d}:{int(s % 60):02d}' if s >= 3600 else f'{int(s // 60)}:{int(s % 60):02d}'


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('job'); ap.add_argument('--intro', required=True); ap.add_argument('--note'); ap.add_argument('--tags', required=True)
    ap.add_argument('--hashtags', required=True); ap.add_argument('--no-links', action='store_true', help='new channel only: no URL anywhere')
    ap.add_argument('--cc-links', action='store_true', help='通史3 style: a short file link for every CC file and one link per licence deed (user 2026-11-14)')
    ap.add_argument('--credits-only', action='store_true', help='story mode: print only the archival-photo credit lines (with --cc-links) for the story description; writes no file')
    a = ap.parse_args()
    d = ROOT / 'projects' / a.job
    tl = json.loads((d / 'timeline.json').read_text(encoding='utf-8'))
    lang = (json.loads((d / 'brief.json').read_text(encoding='utf-8')).get('language') or 'en')[:2]
    L = T.get(lang, T['en'])
    tags = [t.strip() for t in a.tags.split(',') if t.strip()]
    if len(tags) != 7:
        sys.exit(f'need 7 tags, got {len(tags)}')
    hashtags = a.hashtags.replace(',', ' ').split()
    if len(hashtags) != 7 or not all(re.fullmatch(r'#\w+', h) for h in hashtags):
        sys.exit(f'need 7 one-word hashtags like #ColdWar, got {hashtags}')
    used = {c['src'] for t in tl['tracks'] if t['id'] == 'video' for c in t['clips'] if c.get('src')} | {u for t in tl['tracks'] for c in t['clips'] for u in c.get('uses', [])}  # photos drawn inside a JS scene (film 6)
    rows = []
    for line in (d / 'LICENSES.md').read_text(encoding='utf-8').splitlines():
        if line.startswith('| media/'):
            c = [x.strip() for x in line.split('|')]
            if c[1] in used:
                rows.append({'file': c[1], 'page': c[2], 'author': c[3], 'licence': c[4].split(' http')[0]})
    latest = {r['file']: r for r in rows}  # the last row per file wins
    pd, cc, other = Counter(), {}, []; pd_ids = []
    for r in latest.values():
        lic, au = r['licence'], clean_author(r['author'], r['page'])
        m = re.search(r'commons-(\d+)\.', r['file'])
        if re.search(r'\bCC BY', lic):
            if au.startswith('Bundesarchiv, Bild '):  # all Bundesarchiv files on one line: "Bundesarchiv, Bild A, Bild B …"
                cc.setdefault(('Bundesarchiv', lic), []).append(au.split(', ', 1)[1] + (f' (ID {m.group(1)})' if m else ''))
            else:
                cc.setdefault((au, lic), []).append('ID ' + m.group(1) if m else r['page'])  # one line per author + licence
        elif re.search(r'public domain|CC0|PDM|no restrictions|no known', lic, re.I):
            if m:
                pd_ids.append(m.group(1))
            org = next((name for rx, name in ORGS if re.search(rx, au + ' ' + r['page'])), None)
            if org:
                pd[org] += 1
            elif re.fullmatch(r"[A-ZÀ-Ý][\w.'’-]+(?: [A-ZÀ-Ýa-z][\w.'’-]+){1,3}", au) and not re.search(r'\d|unknown|upload|image', au, re.I):
                pd[au] += 1  # a named painter or photographer (clean 'First Last' names only)
        else:
            other.append(f'- {au}, {lic}, {r["page"]}')
    chapters = [(o['start'], o['props'].get('title', '')) for t in tl['tracks'] if t['id'] == 'overlay' for o in t['clips'] if o['type'] == 'chapter']
    intro = Path(a.intro).read_text(encoding='utf-8').strip()
    note = Path(a.note).read_text(encoding='utf-8').strip() if a.note else ''

    def build(n_pd, compact=False, with_ids=False, nosig=False):
        orgs = {name for _, name in ORGS}
        names = [k for k, _ in pd.most_common() if k in orgs] + [k for k, _ in pd.most_common() if k not in orgs][:min(n_pd, 12)]
        out = [intro, '', L['ch'], f'0:00 {L["first"]}'] + [f'{ts(s)} {t}' for s, t in sorted(chapters)]
        if note:
            out += ['', note]
        out += ['', L['src'], L['own']]
        if pd:
            out.append(f'{L["pd"]}: ' + ', '.join(names) + (', …' if len(names) < len(pd) else '') + '.')
        if cc and a.cc_links:  # one line per author: each file as a short curid link, then one deed link per licence
            curid = {}  # Commons page URL -> page id, from the search candidates (files named p-X-tag-K have no id in their name)
            for cj in (d / 'media' / 'candidates').glob('*/candidates.json'):
                for c_ in json.loads(cj.read_text(encoding='utf-8'))['candidates']:
                    if c_.get('source') == 'commons' and str(c_.get('id', '')).isdigit(): curid[c_['page']] = c_['id']
            ba_ = lambda i: re.sub(r'^(Bild .+?) \(ID (\d+)\)$', r'https://commons.wikimedia.org/?curid=\2' if nosig else r'\1 https://commons.wikimedia.org/?curid=\2', i)  # Bundesarchiv: signature + its file link (link only when too long)
            ids_ = lambda v: sorted({ba_(i) if re.match(r'Bild .+ \(ID \d+\)$', i) else('https://commons.wikimedia.org/?curid=' + (i[3:] if i.startswith('ID ') else curid[i])) if (i.startswith('ID ') or i in curid) else i for i in v})
            short = lambda au: re.sub(r'\s+from\s+[^,]*', '', re.sub(r';.*$', '', au)).strip()[:48]
            out += [L['cc']] + [f'- {short(au)}, {lic}: ' + ' '.join(ids_(ids))
                                for (au, lic), ids in sorted(cc.items(), key=lambda x: x[0][0].lower())]
            deed = {'CC BY 2.0': 'by/2.0', 'CC BY 2.5': 'by/2.5', 'CC BY 3.0': 'by/3.0', 'CC BY 4.0': 'by/4.0', 'CC BY-SA 2.0': 'by-sa/2.0',
                    'CC BY-SA 2.5': 'by-sa/2.5', 'CC BY-SA 3.0': 'by-sa/3.0', 'CC BY-SA 4.0': 'by-sa/4.0', 'CC BY-SA 3.0 de': 'by-sa/3.0/de'}
            lics = sorted({lic for _, lic in cc})
            out += ['Licences: ' + ' · '.join(f'{l} https://creativecommons.org/licenses/{deed[l]}/' for l in lics if l in deed)]
        elif cc and not compact:
            out += [L['cc']] + [f'- {au}, {lic}: ' + ', '.join(sorted(set(ids))) for (au, lic), ids in sorted(cc.items(), key=lambda x: x[0][0].lower())]
        elif cc:  # many CC authors (film 76: 124): one line per licence, authors only (author + licence is the attribution)
            by = {}
            for (au, lic), _ in cc.items():
                s = re.sub(r',?\s*\d{4}-\d\d-\d\d[\d: ]*$', '', au)
                # a 2.6 h film had 157 CC authors (Barbarossa, 2026-11-13): short names so the list fits 5,000 characters
                s = 'Bundesarchiv' if s.startswith('Bundesarchiv') else s
                s = re.sub(r'\s*\([^)]*\)', '', re.sub(r'\s+from\s+.*$', '', re.sub(r'\s*/\s*[^,/]*$', '', s))).strip(' ,')
                s = re.sub(r'https?://(www\.)?([^/]+)/?\S*', r'\2', s)
                by.setdefault(lic, set()).add(s[:40])
            out += [L.get('ccc', T['en']['ccc'])] + [f'- {lic}: ' + ', '.join(sorted(v, key=str.lower)) for lic, v in sorted(by.items())]
        if other:
            out += [L['other']] + sorted(set(other))
        if not a.no_links:
            if with_ids and pd_ids:
                out += [L.get('pdids', 'Public-domain files, Commons ID:') + ' ' + ', '.join(sorted(set(pd_ids)))]
            if not compact and not a.cc_links:  # the compact list names authors only, there are no IDs to look up
                out += [L.get('idurl', 'File pages: https://commons.wikimedia.org/?curid= followed by the ID.')]
        sat = any('Sentinel' in str(c.get('credit', '')) for t in tl['tracks'] for c in t['clips'])  # paper/dark looks draw flat Natural Earth maps (film 91)
        flat = {'en': 'Maps: drawn from Natural Earth (public domain).', 'de': 'Karten: auf Grundlage von Natural Earth (gemeinfrei).',
                'vi': 'Bản đồ: vẽ từ Natural Earth (phạm vi công cộng).', 'ja': '地図: Natural Earth（パブリックドメイン）をもとに作成。',
                'es': 'Mapas: elaborados con Natural Earth (dominio público).'}
        out += [L['maps'] if sat else flat.get(lang, flat['en']), L['music'], '', ' '.join(hashtags), '', 'TAGS', ', '.join(tags)]
        txt = '\n'.join(out)
        return (nolinks(txt) if a.no_links else txt).replace('<', '').replace('>', '')  # YouTube rejects angle brackets anywhere in a description

    if a.credits_only:  # the CC block and licence deeds only; the story description has no maps, PD archives or channel line
        lines = build(len(pd)).split('\n')
        i = lines.index(L['src']) + 2 if L['src'] in lines else 0
        print('\n'.join(x for x in lines[i:next(k for k, x in enumerate(lines) if x == L['maps'] or x.startswith(('Maps:', 'Karten:', 'Bản đồ:', '地図:', 'Mapas:')))] if x))
        return
    n = len(pd)
    txt = build(n, with_ids=True) if len(build(n, with_ids=True)) <= LIMIT else build(n)  # the fullest credits that fit
    while len(txt) > LIMIT and n > 3:
        n -= 3; txt = build(n)
    if len(txt) > LIMIT:
        n = len(pd); txt = build(n, True)
        while len(txt) > LIMIT and n > 3:
            n -= 3; txt = build(n, True)
    if len(txt) > LIMIT and a.cc_links:  # Stalingrad 2026-11-16: ~60 Bundesarchiv files; drop the Bild signatures, keep every file link
        n = len(pd); txt = build(n, True, nosig=True)
        while len(txt) > LIMIT and n > 3:
            n -= 3; txt = build(n, True, nosig=True)
    if len(txt) > LIMIT and a.cc_links:  # Berlin 2026-11-17: 47 CC links still 800 over; YouTube links bare domains, so drop "https://"
        n = len(pd); txt = build(n, True, nosig=True).replace('https://', '')
        while len(txt) > LIMIT and n > 3:
            n -= 3; txt = build(n, True, nosig=True).replace('https://', '')
    if len(txt) > LIMIT:
        (d / "qa" / "description_too_long.txt").write_text(txt, encoding="utf-8"); sys.exit(f"{len(txt)} characters even with a short author list: shorten the intro or note")
    (d / 'description_youtube.txt').write_text(txt + '\n', encoding='utf-8')
    print(f'description_youtube.txt: {len(txt)} characters, {len(chapters) + 1} chapters, {len(cc)} CC credit lines ('
          f'{sum(len(v) for v in cc.values())} files) {len(pd)} public-domain authors ({n} named), {len(other)} other')


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    main()
