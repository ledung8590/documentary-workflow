"""Thumbnail fact check, BEFORE the thumbnail is shown to the user (user 2026-11-14: the Barbarossa thumbnail showed a wrong
tank type and was only caught when the user asked "xe tăng ở thum đúng loại chưa", then had to be redone in a hurry).

  PY scripts/thumbcheck.py JOB out.jpg        (reads out.json, the spec that scripts/thumb.py writes next to the image)

Checks, printed as !! (must fix) / ! (look) lines and a review sheet:
  1. every number and year in the thumbnail text appears in the script (script.txt) or FACTS.md;
  2. every photo has a source id (spec "photo_id"/"photo2_id": a Commons file page id or "File:..." title, or a film media
     file named commons-<id>.*); its Commons record (title, description, date, categories) is fetched and printed;
  3. names and type words in the text (capitalised words, model designations like "Panzer III", "Bf 109", "Yamato") are
     looked up in the photo records: a word the text puts next to a photo but its record never mentions is flagged;
  4. the credit line names every photo's archive number and author;
  5. the year label: a year in "tag" that no photo record and no script line supports is flagged; a photo dated to a
     different year than the label says "Foto"/"写真"/"Photo" for is flagged.
Then a FRESH reviewer (a subagent that did not make the thumbnail) looks at the image and the sheet and states what each
photo really shows (vehicle/ship model, person, uniform, era) and whether every word, number and label is right.
"""
import json, re, sys, urllib.parse
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))


def commons_record(pid):
    import media
    q = {'action': 'query', 'format': 'json', 'prop': 'imageinfo|categories', 'iiprop': 'extmetadata', 'cllimit': 50,
         'iiextmetadatafilter': 'ImageDescription|DateTimeOriginal|ObjectName|Artist'}
    if str(pid).isdigit():
        q['pageids'] = pid
    else:
        q['titles'] = pid if str(pid).startswith('File:') else 'File:' + str(pid)
    d = json.loads(media._get('https://commons.wikimedia.org/w/api.php?' + urllib.parse.urlencode(q)))
    p = next(iter(d['query']['pages'].values()))
    md = ((p.get('imageinfo') or [{}])[0]).get('extmetadata', {})
    strip = lambda s: re.sub(r'<[^>]+>', ' ', s or '').replace('&nbsp;', ' ')
    return {'artist': re.sub(r'\s+', ' ', strip(md.get('Artist', {}).get('value'))).strip()[:120], 'title': p.get('title', ''), 'description': re.sub(r'\s+', ' ', strip(md.get('ImageDescription', {}).get('value')))[:600],
            'date': strip(md.get('DateTimeOriginal', {}).get('value')), 'categories': [c['title'].removeprefix('Category:') for c in p.get('categories', [])]}


def norm_num(s):
    return re.sub(r'[\s., ]', '', s)


def main(job, img):
    d = Path(job) if Path(job).is_dir() else ROOT / 'projects' / job
    spec = json.loads(Path(img).with_suffix('.json').read_text(encoding='utf-8'))
    script = ''.join((d / f).read_text(encoding='utf-8') for f in ('script.txt', 'FACTS.md') if (d / f).exists())
    snum = norm_num(script)
    texts = {k: spec[k] for k in ('tag', 'kicker', 'title', 'title2', 'red', 'date') if spec.get(k)}
    texts.update({f'line{i + 1}': ln['text'] for i, ln in enumerate(spec.get('lines') or []) if ln.get('text')})  # layout "free" (thumb.py)
    warn = 0
    # 1. numbers and years
    for k, s in texts.items():
        for n in re.findall(r'\d[\d., ]*(?:\s*[–-]\s*\d[\d.,]*)?', s):
            parts = [norm_num(x) for x in re.split(r'\s*[–-]\s*', n) if x.strip()]
            missing = [x for x in parts if x and x not in snum]
            if missing:
                print(f'!! {k} "{s}": number {n} is not in script.txt/FACTS.md: check it or change the text'); warn += 1
    # 2. photo records
    recs = {}
    for key in ('photo', 'photo2'):
        if not spec.get(key):
            continue
        pid = spec.get(f'{key}_id') or (re.search(r'commons-(\d+)', Path(spec[key]).name) or [None, None])[1]
        if not pid:
            print(f'!! {key} {Path(spec[key]).name}: no source id: set "{key}_id" (Commons page id or File: title)'); warn += 1; continue
        try:
            recs[key] = commons_record(pid)
        except Exception as e:  # noqa: BLE001
            print(f'!! {key}: Commons record {pid} could not be read ({e})'); warn += 1
    # 2b. the credit line names every photo (archive number or title) and its author (Bundesarchiv attribution needs both)
    cred = spec.get('credit', '')
    for key, r in recs.items():
        num = re.search(r'Bild[ _]([\w-]+)', r['title'])
        if num and num.group(1) not in cred:
            print(f'!! credit does not name {key} ({r["title"]}): add its archive number'); warn += 1
        au = re.split(r'[,(/]', r.get('artist', ''))[0].strip()
        if au and not re.search(r'unknown|unbekannt|anonym|missing name', au, re.I) and au.split()[-1].lower() not in cred.lower() and au.split()[0].lower() not in cred.lower():
            print(f'!! credit lacks the author of {key}: "{r["artist"]}"'); warn += 1
    # 3. names / type words vs the photo records
    blob = ' '.join(json.dumps(r, ensure_ascii=False) for r in recs.values()).lower()
    words = set()
    for s in texts.values():
        words |= set(re.findall(r'\b(?:[A-ZÄÖÜ][\w-]+(?:\s+(?:[IVX]+\b|\d{1,3}[A-Za-z]?\b))?)', s))  # 'Panzer III', 'Typ 97'; not 'Juni 1941'
        words |= set(re.findall(r'\b[A-Z][a-z]{0,3}\s?\d{2,3}[A-Za-z]?\b', s))  # Bf 109, Ju 87, T-34 style
    common = {'Der', 'Die', 'Das', 'Warum', 'Ein', 'Eine', 'Foto', 'The', 'Why', 'How', 'Sieg', 'Fehler', 'Krieg', 'Juni', 'Juli', 'Mai'}
    for w in sorted(words):
        if w in common or len(w) < 3:
            continue
        if w.lower() not in blob and w.lower() not in script.lower():
            print(f'! "{w}" is neither in the photo records nor in the script: is it right?')
        elif w.lower() not in blob and re.search(r'[IVX]+$|\d', w):
            print(f'!! "{w}" (a type/model) is not in any photo record: confirm the photo really shows it'); warn += 1
    # 4. year label
    years_tag = re.findall(r'1[0-9]{3}|20[0-9]{2}', spec.get('tag', ''))
    for y in years_tag:
        in_rec = any(y in json.dumps(r) for r in recs.values())
        if not in_rec and y not in script:
            print(f'!! tag year {y} is in neither the photo records nor the script'); warn += 1
        if re.search(r'Foto|Photo|写真|Ảnh', spec.get('tag', '')) and recs.get('photo') and y not in json.dumps(recs['photo']):
            print(f'!! tag says the photo is from {y}, but its record does not say so: {recs["photo"]["date"] or "no date"}'); warn += 1
    MONTHS = r'Januar|Februar|März|April|Mai|Juni|Juli|August|September|Oktober|November|Dezember|January|February|March|June|July|October|December|tháng|月'
    if re.search(r'Foto|Photo|写真|Ảnh', spec.get('tag', '')) and re.search(MONTHS, spec.get('tag', '')) and recs.get('photo') \
            and not re.search(r'\d{4}-(?:0[1-9]|1[0-2])-|' + MONTHS, recs['photo']['date'] + ' ' + recs['photo']['title']):
        print(f'!! tag gives the photo a month, its record only says "{recs["photo"]["date"][:40]}": drop the month or name the event instead'); warn += 1
    print('\n== review sheet (give it, with the image, to a fresh reviewer) ==')
    print('text:', json.dumps(texts, ensure_ascii=False))
    for k, r in recs.items():
        print(f'{k}: {r["title"]} | date: {r["date"] or "-"}\n   description: {r["description"]}\n   categories: {", ".join(r["categories"][:20])}')
    print(f'\nthumbcheck: {warn} must-fix')
    return warn


if __name__ == '__main__':
    sys.exit(1 if main(sys.argv[1], sys.argv[2]) else 0)
