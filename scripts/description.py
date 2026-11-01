"""Paste-ready YouTube description (stage 13): projects/JOB/description_youtube.txt.

  PY scripts/description.py JOB --intro intro.txt [--note note.txt] --tags "t1, t2, ..., t7" --hashtags "#A #B ... #G"

The agent writes the intro (what the film is about) and an optional note (what is illustrative / reconstructed), in the
script's language. This script adds everything else from the project's own records, so the text can be pasted into
YouTube as it is:
- chapters from the timeline's chapter cards (first line 0:00);
- public-domain sources named by archive and author;
- every Creative Commons file on screen with author, licence and Commons ID (attribution the licences require);
- map basemap credit and music/SFX credit;
- a line of 7 #hashtags just above TAGS (YouTube shows the first ones above the title; user request 2026-11-01);
- the TAGS line (7 tags, comma-separated).
It never refers to files the viewer cannot see (no "see credits.txt"; user review 2026-11-01) and keeps the text under
YouTube's 5,000-character limit by shortening the public-domain author list first."""
import argparse, json, re, sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
T = {
    'en': dict(ch='CHAPTERS', first='Introduction', src='SOURCES & CREDITS', own='Narration, maps and animated graphics: original work of this channel.',
               pd='Public domain', cc='Creative Commons files on Wikimedia Commons (licences: creativecommons.org/licenses; file page: commons.wikimedia.org/?curid=ID):',
               maps='Map imagery: Sentinel-2 cloudless 2016 by EOX IT Services GmbH (CC BY 4.0, s2maps.eu). Terrain: AWS Terrain Tiles.',
               music='Music and sound effects: ElevenLabs (commercial licence).', other='Other open licences:'),
    'de': dict(ch='KAPITEL', first='Einleitung', src='QUELLEN & NACHWEISE', own='Sprechertext, Karten und animierte Grafiken: eigenes Werk dieses Kanals.',
               pd='Gemeinfrei', cc='Creative-Commons-Bilder von Wikimedia Commons (Lizenzen: creativecommons.org/licenses; Dateiseite: commons.wikimedia.org/?curid=ID):',
               maps='Kartenbilder: Sentinel-2 cloudless 2016 von EOX IT Services GmbH (CC BY 4.0, s2maps.eu). Gelände: AWS Terrain Tiles.',
               music='Musik und Soundeffekte: ElevenLabs (kommerzielle Lizenz).', other='Weitere offene Lizenzen:'),
    'vi': dict(ch='CHƯƠNG', first='Mở đầu', src='NGUỒN & GHI CÔNG', own='Lời bình, bản đồ và đồ hoạ động: sản phẩm của kênh.',
               pd='Phạm vi công cộng', cc='Ảnh Creative Commons trên Wikimedia Commons (giấy phép: creativecommons.org/licenses; trang tệp: commons.wikimedia.org/?curid=ID):',
               maps='Ảnh bản đồ: Sentinel-2 cloudless 2016 của EOX IT Services GmbH (CC BY 4.0, s2maps.eu). Địa hình: AWS Terrain Tiles.',
               music='Nhạc và hiệu ứng âm thanh: ElevenLabs (giấy phép thương mại).', other='Giấy phép mở khác:'),
    'es': dict(ch='CAPÍTULOS', first='Introducción', src='FUENTES Y CRÉDITOS', own='Narración, mapas y gráficos animados: obra original de este canal.',
               pd='Dominio público', cc='Archivos Creative Commons en Wikimedia Commons (licencias: creativecommons.org/licenses; página: commons.wikimedia.org/?curid=ID):',
               maps='Imágenes de mapas: Sentinel-2 cloudless 2016 de EOX IT Services GmbH (CC BY 4.0, s2maps.eu). Relieve: AWS Terrain Tiles.',
               music='Música y efectos de sonido: ElevenLabs (licencia comercial).', other='Otras licencias abiertas:'),
}
LIMIT = 5000
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
    a = re.sub(r'\s+', ' ', re.sub(r'<[^>]+>', '', a or '')).strip()
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
    ap.add_argument('--hashtags', required=True)
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
    used = {c['src'] for t in tl['tracks'] if t['id'] == 'video' for c in t['clips'] if c.get('src')}
    rows = []
    for line in (d / 'LICENSES.md').read_text(encoding='utf-8').splitlines():
        if line.startswith('| media/'):
            c = [x.strip() for x in line.split('|')]
            if c[1] in used:
                rows.append({'file': c[1], 'page': c[2], 'author': c[3], 'licence': c[4].split(' http')[0]})
    latest = {r['file']: r for r in rows}  # the last row per file wins
    pd, cc, other = Counter(), {}, []
    for r in latest.values():
        lic, au = r['licence'], clean_author(r['author'], r['page'])
        m = re.search(r'commons-(\d+)\.', r['file'])
        if re.search(r'\bCC BY', lic):
            if au.startswith('Bundesarchiv, Bild '):  # all Bundesarchiv files on one line: "Bundesarchiv, Bild A, Bild B …"
                cc.setdefault(('Bundesarchiv', lic), []).append(au.split(', ', 1)[1])
            else:
                cc.setdefault((au, lic), []).append('ID ' + m.group(1) if m else r['page'])  # one line per author + licence
        elif re.search(r'public domain|CC0|PDM|no restrictions|no known', lic, re.I):
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

    def build(n_pd):
        orgs = {name for _, name in ORGS}
        names = [k for k, _ in pd.most_common() if k in orgs] + [k for k, _ in pd.most_common() if k not in orgs][:min(n_pd, 12)]
        out = [intro, '', L['ch'], f'0:00 {L["first"]}'] + [f'{ts(s)} {t}' for s, t in sorted(chapters)]
        if note:
            out += ['', note]
        out += ['', L['src'], L['own']]
        if pd:
            out.append(f'{L["pd"]}: ' + ', '.join(names) + (', …' if len(names) < len(pd) else '') + '.')
        if cc:
            out += [L['cc']] + [f'- {au}, {lic}: ' + ', '.join(sorted(set(ids))) for (au, lic), ids in sorted(cc.items(), key=lambda x: x[0][0].lower())]
        if other:
            out += [L['other']] + sorted(set(other))
        out += [L['maps'], L['music'], '', ' '.join(hashtags), '', 'TAGS', ', '.join(tags)]
        return '\n'.join(out)

    n = len(pd)
    txt = build(n)
    while len(txt) > LIMIT and n > 3:
        n -= 3; txt = build(n)
    if len(txt) > LIMIT:
        sys.exit(f'{len(txt)} characters even with a short author list: shorten the intro or note')
    (d / 'description_youtube.txt').write_text(txt + '\n', encoding='utf-8')
    print(f'description_youtube.txt: {len(txt)} characters, {len(chapters) + 1} chapters, {len(cc)} CC credit lines ('
          f'{sum(len(v) for v in cc.values())} files) {len(pd)} public-domain authors ({n} named), {len(other)} other')


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    main()
