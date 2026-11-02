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
OUTRO = re.compile(r'tạm biệt|hẹn gặp lại|cảm ơn quý vị|thanks for (listening|watching)|see you|bis zum nächsten|danke fürs|hasta la próxima|gracias por', re.I)
STOP = set('khác và của là có không một những các người ông bà anh chị đã đang sẽ được bị cho với trong ra vào lên xuống rồi thì mà này đó ấy '
           'nhưng nếu khi lại cũng còn chỉ như từ tại để vì nên hai ba bốn năm ngày tháng the a an of to and in on at is was he she it'.split())


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
        if ss and sentences(ob) and words(ss[0])[:2] == words(sentences(ob)[0])[:2]:
            warn.append(f'opens with the same two words as {o.name[:40]}')

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
