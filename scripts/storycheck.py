"""Story script lint (/gentruyen): catch the template feel viewers complain about before any voice credit is spent.

  PY scripts/storycheck.py input/<story>.txt [--corpus DIR ...]

Compares the script with itself and with earlier stories (default corpus: stories/published/*.txt, plus every other .txt
given with --corpus). Viewers of stories 87/88 (2026-11-02): "cốt truyện na ná như nhiều truyện đã đăng", "một cốt chuyện
rồi thêm râu ria". Measured there: the same cold-open line word for word, the same biography beat, shared props, a third of
all sentences 4 words or shorter, 24-34 runs of sentences with the same opener, and story 88 with no ending.

Findings: `!!` = fix before tts (exit 1), `!` = look at it. Rules and remedies: docs/STORY_WRITING.md.
"""
import argparse, collections, re, sys, unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STOCK = {  # narrator stock lines that make every episode open/turn the same way
    'vi': ['tôi muốn bắt đầu câu chuyện', 'câu chuyện hôm nay', 'thưa quý vị và các bạn', 'đó là phần ít được nhìn thấy',
           'trong nghề tình báo', 'trong nghề này', 'có lẽ điều khiến tôi nhớ nhất', 'nhưng có một điều không thay đổi',
           'chiến tranh thường được nhớ bằng', 'sự yên ổn lại đáng ngờ'],
    'en': ["i want to begin today's story", 'ladies and gentlemen', 'in the world of espionage', 'but one thing never changed'],
    'de': ['ich möchte die geschichte heute', 'meine damen und herren', 'in der welt der spionage'],
    'es': ['quiero comenzar la historia de hoy', 'señoras y señores', 'en el mundo del espionaje'],
}
OUTRO = re.compile(r'tạm biệt|hẹn gặp lại|cảm ơn quý vị|thanks for (listening|watching)|thank you for (listening|watching|staying|sitting|being here)|like and (a )?subscri|subscribe|see you|bis zum nächsten|danke fürs|hasta la próxima|gracias por', re.I)
STOP = set('khác và của là có không một những các người ông bà anh chị đã đang sẽ được bị cho với trong ra vào lên xuống rồi thì mà này đó ấy '
           'nhưng nếu khi lại cũng còn chỉ như từ tại để vì nên hai ba bốn năm ngày tháng the a an of to and in on at is was he she it'.split())

# 7. names: viewers notice a recurring character name across episodes (Military Chronicle, 2026-11-15: "How come in all these
# videos there's a soldier named Beddo?" = Benno in 4 stories, plus Hinnerk, Emil and the hometown Kassel repeated).
# Capitalised words used mid-sentence that are not common words, months, nations, ranks, armies or big places.
COMMONCAPS = set("""I I'm I'd I'll I've Mr Mrs Herr Frau Fräulein Sir Madam God Lord Christ Jesus Mother Father Mama Papa Mutti Vati
January February March April May June July August September October November December Monday Tuesday Wednesday Thursday Friday
Saturday Sunday Christmas Easter German Germans Germany Russian Russians Russia Soviet Soviets Soviet Union Polish Poland Poles
French France British Britain English England American Americans America Allied Allies Europe European Jewish Jews Italian Italy
Japanese Japan Vietnamese Vietnam Chinese China Austrian Austria Prussian Prussia Ukrainian Ukraine Belarus Hungarian Romanian
Army Armies Division Divisions Regiment Battalion Company Platoon Corps Group Centre Center North South East West Front River
Sea Lake Forest Bridge Street Station Road Leutnant Oberleutnant Hauptmann Major Oberst General Feldwebel Unteroffizier Gefreiter
Obergefreiter Grenadier Grenadiers Gefreite Sergeant Corporal Private Lieutenant Captain Colonel Doctor Doktor Pastor Father
Wehrmacht Luftwaffe Kriegsmarine Waffen Volkssturm Führer Reich Nazi Nazis Party Red White Black Iron Cross Knight
Berlin Moscow Paris London Vienna Warsaw Saigon Hanoi Huế Đà Nẵng Hà Nội Sài Gòn Hitler Stalin Churchill Roosevelt Truman
Operation Panzerfaust Panzer Panzers Infantry Artillery Platz Strasse Straße Kessel Tiger Panther Stuka Katyusha Mass The Two Now
Mỹ Việt Nam Pháp Nga Đức Trung Quốc Liên Xô Sư Đoàn Trung Đoàn Tiểu Đoàn Đại Đội Trung Đội Ông Bà Anh Chị Em Cô Chú Bác""".split())


# 8. motifs: a renamed character is still the same character. Viewers of "The Last Line Before Berlin" (2026-11-17): "Railway
# timetable again, seriously?", "How come in every story the tank crewmen are a prototype of the crewmen in the previous
# videos?" The crewman who knows the railway timetable by heart was in 4 stories (Leo, Kranich, Thiel, Jost), the zoo hippo in 3,
# a hero with a musical craft in 6. Each family = one regex on the lowercased text; more in stories/motifs.txt ("name = regex").
MOTIFS = {
    'the man who knows the railway timetable by heart / railway family': r'timetable|train schedule|reichsbahn|station ?master|railway signalman|signal ?box|sold tickets|fahrplan|kursbuch|giờ tàu',
    'zoo animal / hippo and its keeper': r'\bhippo|\bzoo\b|zoo ?keeper|nilpferd',
    'musical craft or perfect ear (tuner, organ, bells, tuning fork, harmonium)': r'tuning fork|piano tuner|organ builder|organist|harmonium|bell founder|bellows|\bbayan\b|accordion|stimmgabel|orgelbau|lên dây đàn',
    'the stammerer who speaks clearly in action': r'stammer|stutter|stotter',
    'chess by post / chess board': r'\bchess|schach',
    'stamp collector': r'stamp collect|stamp album|postage stamp|overprint|philatel|briefmarke',
    'postman / lost letter chased through the field post': r'field post|feldpost|postman|undelivered letter|briefträger',
    'the man who writes receipts / keeps an inventory of everything': r'receipt|inventory|quittung',
    'a pet or mascot carried in the vehicle': r'\bchicken\b|\brooster\b|\bkitten\b|\bpuppy\b|mascot',
    'the lucky jar / food saved for the end': r'\bplums?\b|pflaumen',
}
CAST = re.compile(r"\b(son of an?|daughter of an?|worked as|had been an?|apprentice|by heart|before the war|before they drafted|in civilian life|"
                  r"his father (?:was|is|had|ran|kept)|von beruf|lehrling|auswendig|vor dem krieg|con trai (?:của )?(?:một|ông)|vốn là|thuộc lòng)\b", re.I)


# 9. skeleton: new names, trades and props on the same frame are still the same video. Read 2026-11-26 after YouTube's
# "highly similar storyline template" wording: all 14 published soldier stories were dated diaries that open with a roll call of
# trades, end with the narrator in Soviet captivity, released in 1949, and close with an epilogue listing every man's fate
# (a comrade dead of dysentery, the narrator's age at death). Each mark = one test on the text; a new script that carries most
# of the marks most earlier stories carry is the same frame again.
MONTHS = r'(?:January|February|March|April|May|June|July|August|September|October|November|December)'
FATES = re.compile(r'died (?:of|in|at)|was released|released in|came home|returned (?:home|to)|survived the|was (?:listed|reported) (?:as )?missing|'
                   r'never (?:learned|found out|traced)|fate (?:is|was|remains) unknown|went back to|reopened|became an? ', re.I)
SKELETON = {
    'a diary in dated entries': lambda t, head, tail: len(re.findall(rf'^{MONTHS} \d{{1,2}}, 19\d\d\.?\s*$', t, re.M)) >= 6,
    'a roll call of comrades by pre-war trade near the start': lambda t, head, tail: len(CAST.findall(head)) >= 3,
    'the narrator ends in Soviet captivity': lambda t, head, tail: bool(re.search(r'prisoner|captiv|\bcamps?\b|captured', tail, re.I)
                                                                         and re.search(r'soviet|russian|siberia|urals|kazakh', tail, re.I)),
    'an epilogue that lists what became of each person': lambda t, head, tail: len(FATES.findall(tail)) >= 4,
    'released / home in 1949': lambda t, head, tail: '1949' in tail,
    'a comrade dead of dysentery in a camp': lambda t, head, tail: 'dysentery' in tail.lower(),
    "the narrator's year and age of death": lambda t, head, tail: bool(re.search(r'died in (?:19|20)\d\d|at the age of|aged? (?:sixty|seventy|eighty)', tail, re.I)),
    'passages that open with "X is dead."': lambda t, head, tail: bool(re.search(r'^[A-ZÄÖÜ][a-zäöüß]+ is dead\.', t, re.M)),
    'the narrator swears he writes it down honestly': lambda t, head, tail: bool(re.search(r"writ(?:e|ing) (?:that|this|it|both things) down (?:honestly|because both)|"
                                                                                           r"(?:put|write) down only what i (?:know|saw)", t, re.I)),
}


def skeleton(t):
    """The marks of the worn frame this text carries (English stories)."""
    head, tail = t[:int(len(t) * 0.15)], t[-3500:]
    return {k for k, f in SKELETON.items() if f(t, head, tail)}


def motifs():
    m = dict(MOTIFS)
    p = ROOT / 'stories' / 'motifs.txt'
    if p.exists():
        for line in p.read_text(encoding='utf-8').splitlines():
            if '=' in line and not line.lstrip().startswith('#'):
                k, v = line.split('=', 1)
                m[k.strip()] = v.strip()
    return {k: re.compile(v, re.I) for k, v in m.items()}


def names_of(t):
    """Capitalised words used mid-sentence (so not just sentence starts), counted."""
    c = collections.Counter()
    for s in sentences(t):
        for piece in re.split(r'[“”"«»„:;—–(]|\s-\s', s):  # the first word after a quote mark or dash starts a sentence too
            for w in re.findall(r"[\w’']+", piece)[1:]:
                if len(w) >= 3 and w[0].isupper() and w[1:].islower() and w.isalpha() and w not in COMMONCAPS:
                    c[w] += 1
    return c


def names_ok():
    """stories/names_ok.txt: real places or people a story may share on purpose (one per line)."""
    real = set('Königsberg Vitebsk Minsk Bobruisk Orsha Mogilev Belorussia Bagration Danzig Pillau Stalingrad Kursk Leningrad Normandy '
               'Oder Vistula Dnieper Prussia Pomerania Silesia Kurland Kharkov Kiev Smolensk Rzhev Seelow Spree Elbe'.split())
    p = ROOT / 'stories' / 'names_ok.txt'
    return real | (set(p.read_text(encoding='utf-8').split()) if p.exists() else set())


def norm(t):
    return unicodedata.normalize('NFC', t)


def words(t):
    return re.findall(r'\w+', norm(t).lower())


def sentences(t):
    return [s.strip() for s in re.split(r'(?<=[.!?…”"])\s+|\n+', norm(t)) if s.strip() and re.search(r'\w', s)]


def body(t):
    """Drop the closing sign-off so shared channel outros are not counted as copying."""
    ss = sentences(t)
    cut = len(ss)
    for i in range(len(ss) - 1, max(len(ss) - 8, 0) - 1, -1):
        if OUTRO.search(ss[i]):
            cut = i
    return ' '.join(ss[:cut])


def grams(ws, n):
    return collections.Counter(tuple(ws[i:i + n]) for i in range(len(ws) - n + 1))


def plain(g):  # skip n-grams that are dates, numbers or only function words
    return not any(ch.isdigit() for w in g for ch in w) and sum(w not in STOP for w in g) >= 2


CLS = r'(?:chiếc|mảnh|vòng|hạt|đoạn|bao|cuốn|tấm|sợi|lá|cái|hộp|gói|bức|tờ|cây|que)'


def props_of(t):
    """Story objects (vi): classifier + the next one or two words, e.g. "vòng dây đồng" -> "dây đồng"."""
    out = collections.Counter()
    for m in re.finditer(CLS + r'\s+(\w+)(?:\s+(\w+))?', t.lower()):
        a, b = m.group(1), m.group(2)
        if a in STOP or a.isdigit():
            continue
        out[f'{a} {b}' if b and b not in STOP and not b.isdigit() else a] += 1
    return {k for k, c in out.items() if c >= 2 and ' ' in k}


def lang_of(t):
    w = words(t[:4000])
    if sum(x in ('và', 'của', 'không', 'người') for x in w) > 10:
        return 'vi'
    if sum(x in ('und', 'der', 'die', 'nicht') for x in w) > 10:
        return 'de'
    if sum(x in ('que', 'los', 'una', 'para') for x in w) > 10:
        return 'es'
    return 'en'


def check(path, corpus):
    t = norm(path.read_text(encoding='utf-8')); lang = lang_of(t); low = t.lower()
    err, warn = [], []
    ss = sentences(t); n = len(ss) or 1
    lens = [len(s.split()) for s in ss]

    # 1. stock narrator lines
    for p in STOCK.get(lang, []):
        c = low.count(p)
        if c:
            (err if p.startswith(('tôi muốn bắt đầu', "i want", 'ich möchte', 'quiero')) else warn).append(f'stock line x{c}: "{p}"')

    # 2. sentence rhythm: fragments and same-opener runs
    short = sum(x <= 4 for x in lens) / n
    if short > 0.22:
        err.append(f'{short:.0%} of sentences have 4 words or fewer (keep under 15 %; fragments only at climaxes)')
    elif short > 0.15:
        warn.append(f'{short:.0%} of sentences have 4 words or fewer (target under 15 %)')
    firsts = [(s.split() or [''])[0].lower() for s in ss]
    runs = [i for i in range(len(firsts) - 2) if firsts[i] == firsts[i + 1] == firsts[i + 2]]
    if len(runs) > 12:
        err.append(f'{len(runs)} runs of 3+ sentences starting with the same word (e.g. "{ss[runs[0]][:50]}…"); keep under 8')
    elif len(runs) > 8:
        warn.append(f'{len(runs)} runs of 3+ sentences starting with the same word; keep under 8')
    top = collections.Counter(firsts).most_common(3)
    for w, c in top:
        if w not in ('', ) and c / n > 0.06 and w in ('nhưng', 'một', 'không', 'but', 'and', 'aber', 'pero'):
            warn.append(f'"{w}" opens {c} sentences ({c / n:.0%})')

    # 3. repeats inside the story (7-word phrases, not dates)
    own = grams(words(body(t)), 7)
    rep = [(' '.join(g), c) for g, c in own.items() if c >= 3 and plain(g)]
    if rep:
        warn.append(f'{len(rep)} phrases repeated 3+ times inside the story: ' + '; '.join(f'"{g}" x{c}' for g, c in rep[:5]))

    # 4. history lecture before the hero lives: years packed in the first 12 %
    head = t[:int(len(t) * 0.12)]
    years = len(re.findall(r'\b1[89]\d\d\b', head))
    if years > 8:
        warn.append(f'{years} year numbers in the first 12 %: the history passage sits right after the hook, the 87/88 slot (move it to another scene)')

    # 5. ending
    tail = ' '.join(ss[-12:])
    if not OUTRO.search(tail):
        err.append('no closing: the last sentences have no sign-off (story 88 stopped mid-cliffhanger)')
    elif re.search(r'chưa biết|không ngờ|to be continued|còn tiếp', ' '.join(ss[-15:-3]), re.I):
        warn.append('the ending reads like a cliffhanger: make sure the story is resolved before the sign-off')

    # 6. against earlier stories
    mine6 = {g for g in grams(words(body(t)), 6) if plain(g)}
    used = collections.defaultdict(list)  # motif family -> earlier stories that built on it
    mots = motifs()
    for o in corpus:
        if o.resolve() == path.resolve():
            continue
        ot = norm(o.read_text(encoding='utf-8')); ob = body(ot)
        shared = sorted(' '.join(g) for g in mine6 & {g for g in grams(words(ob), 6) if plain(g)})
        if len(shared) >= 3:
            err.append(f'{len(shared)} six-word phrases shared with {o.name[:50]}: ' + '; '.join(f'"{s}"' for s in shared[:6]))
        elif shared:
            warn.append(f'shared with {o.name[:50]}: ' + '; '.join(f'"{s}"' for s in shared))
        mp, op = props_of(body(t)), props_of(ob)
        both = sorted(k for k in mp if k in op)
        if both:
            warn.append(f'same props/objects as {o.name[:40]}: ' + ', '.join(both[:12]) + ' (give each story its own)')
        bio = r'sinh năm 19\d\d|born in 19\d\d|geboren 19\d\d'
        par = r'cha ông|his father|sein vater'
        if re.search(bio, t[:len(t) // 3], re.I) and re.search(bio, ot[:len(ot) // 3], re.I) \
                and re.search(par, t[:len(t) // 3], re.I) and re.search(par, ot[:len(ot) // 3], re.I):
            warn.append(f'same biography beat as {o.name[:40]} (birth year + father\'s trade in the first third): introduce the hero differently')
        mine_n, ok_n = names_of(body(t)), names_ok()
        same = sorted(k for k, c in mine_n.items() if c >= 1 and names_of(ob).get(k, 0) >= 2 and k not in ok_n)
        if same:
            # Vietnamese syllables double as places and words (Bình, Tây, Tết): warn there; elsewhere a shared name blocks the voice
            (warn if lang == 'vi' else err).append(f'names already used in {o.name[:45]}: ' + ', '.join(same) + ' (viewers notice recurring names across episodes,'
                       ' "a soldier named Beddo in all these videos": rename them; a real place/person shared on purpose goes in stories/names_ok.txt)')
        for k, rx in mots.items():
            if len(rx.findall(ob)) >= 2:
                used[k].append(o.name[:28])
        if ss and sentences(ob) and words(ss[0])[:2] == words(sentences(ob)[0])[:2]:
            warn.append(f'opens with the same two words as {o.name[:40]}')

    # 8. motifs: character types and running gags an earlier story already built on
    for k, rx in mots.items():
        hits = rx.findall(body(t))
        if len(hits) >= 2 and used[k]:
            err.append(f'motif used before, x{len(hits)} here ({", ".join(sorted(set(h.lower() for h in hits))[:5])}): {k}; already in {len(used[k])} '
                       f'earlier stories ({"; ".join(used[k][:4])}). Viewers: "Railway timetable again, seriously?" Replace this character\'s trade, '
                       'quirk and running gag with ones no earlier story has, then add the new family to stories/motifs.txt')
    # 9. skeleton: marks of the frame that most earlier stories share
    if lang == 'en':
        others = [skeleton(norm(o.read_text(encoding='utf-8'))) for o in corpus if o.resolve() != path.resolve() and lang_of(o.read_text(encoding='utf-8')) == 'en']
        mine = skeleton(t)
        worn = sorted(k for k in mine if sum(k in o for o in others) >= max(4, len(others) // 2))
        msg = (f'same skeleton as the earlier stories, {len(worn)} of {len(SKELETON)} marks: ' + '; '.join(f'{k} (in {sum(k in o for o in others)} of {len(others)})' for k in worn)
               + '. YouTube: "highly similar storyline template across multiple videos" = no monetization. Change the frame, not the props: another form '
                 '(memoir, letters, a diary with gaps), another fate for the narrator, people who enter by what they do, an outro without the roll call. '
                 'docs/STORY_WRITING.md "A new frame every story"')
        if len(worn) >= 4:
            err.append(msg)
        elif len(worn) == 3:
            warn.append(msg)
    cast = [s2 for s2 in ss if CAST.search(s2)]
    if cast:
        warn.append(f'{len(cast)} cast introductions; compare each trade/quirk with the "Cast" column of stories/published/LOG.md (no type twice):\n     - '
                    + '\n     - '.join(c[:170] for c in cast[:25]))

    print(f'{path.name}: {lang}, {len(t)} chars, {n} sentences, {len(corpus)} earlier stories compared')
    for e in err:
        print('!!', e)
    for w in warn:
        print('! ', w)
    if not err and not warn:
        print('ok')
    return len(err)


if __name__ == '__main__':
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('script'); ap.add_argument('--corpus', action='append', default=[])
    a = ap.parse_args()
    sys.stdout.reconfigure(encoding='utf-8')
    corpus = []
    for c in a.corpus + [str(ROOT / 'stories' / 'published')]:
        p = Path(c)
        corpus += [p] if p.is_file() else sorted(p.glob('*.txt')) if p.is_dir() else []
    sys.exit(1 if check(Path(a.script), corpus) else 0)
