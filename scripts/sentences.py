"""Narration script -> sentences with an emotion and a designed pause after each one.

Script format (UTF-8 .txt/.md, see docs/VOICE.md):
  # Chapter title          -> chapter marker; the sentence before it gets the long `chapter` pause
  blank line               -> paragraph break (adds `paragraph` pause)
  {somber} Sentence.       -> explicit emotion for that sentence (overrides the heuristic)
  [pause 2.5]              -> explicit pause after the previous sentence, in seconds (overrides the design)
  <!-- note -->            -> ignored

The heuristic emotion is only a first draft; the agent reviews sentences.json and edits `emotion`
(or `pause_after` with `locked: true`) before TTS. Pauses are recomputed from emotions on every split
unless locked.
"""
import re, unicodedata

EMOTIONS = ('neutral', 'calm', 'hook', 'tense', 'urgent', 'dramatic', 'somber', 'reflective', 'triumphant', 'question')

# Seconds of silence after a sentence, by its emotion. Tuned to documentary pacing: action runs on,
# grief and reveals breathe. The reference film averages ~0.5 s between sentences with a few long holds.
BASE_PAUSE = {
    'neutral': 0.45, 'calm': 0.55, 'hook': 0.7, 'tense': 0.32, 'urgent': 0.22, 'dramatic': 0.95,
    'somber': 1.15, 'reflective': 0.85, 'triumphant': 0.75, 'question': 1.0,
}
PARAGRAPH = 0.5      # added at a paragraph end
CHAPTER = 2.2        # added before a chapter title (room for a title card + music turn)
SHIFT = 0.3          # added when the emotional temperature changes sharply between sentences
ELLIPSIS = 0.3       # sentence trails off with … / ...
LONG = 0.1           # long sentence (> 28 words): the listener needs a beat
MIN_PAUSE, MAX_PAUSE = 0.15, 4.0
HEAT = {'urgent': 3, 'tense': 2, 'triumphant': 2, 'hook': 1, 'dramatic': 1, 'question': 1, 'neutral': 1,
        'calm': 0, 'reflective': 0, 'somber': -1}

ABBR = {'mr', 'mrs', 'ms', 'dr', 'gen', 'col', 'lt', 'capt', 'maj', 'sgt', 'cpl', 'pvt', 'adm', 'st', 'mt', 'ft',
        'no', 'vs', 'etc', 'jr', 'sr', 'jan', 'feb', 'mar', 'apr', 'jun', 'jul', 'aug', 'sep', 'sept', 'oct', 'nov', 'dec', 'u.s', 'u.k', 'u.s.s.r', 'h.m.s', 'u.s.s', 'e.g', 'i.e', 'approx', 'ca', 'tp', 'ths', 'ts'}

KEYWORDS = {  # lower-case stems, English + Vietnamese; first match wins in this order
    'somber': ['died', 'dead', 'death', 'killed', 'graves', 'mourn', 'perished', 'massacre', 'never came home',
               'his own life', 'her own life', 'suicide', 'wounded',
               'hy sinh', 'tử trận', 'chết', 'mất mát', 'nước mắt', 'đau thương', 'tang'],
    'triumphant': ['victory', 'victorious', 'triumph', 'flag over', 'raised the flag', 'raised their flag', 'surrendered', 'liberat',
                   'chiến thắng', 'thắng lợi', 'cắm cờ', 'đầu hàng', 'giải phóng'],
    'urgent': ['suddenly', 'at once', 'opened fire', 'charged', 'stormed', 'bất ngờ', 'đột nhiên', 'nổ súng', 'xung phong'],
    'tense': ['attack', 'assault', 'bombard', 'shell', 'artillery', 'ambush', 'siege', 'enemy', 'trapped',
              'tấn công', 'pháo', 'bao vây', 'phục kích', 'quân địch', 'kẻ thù'],
    'reflective': ['today', 'remember', 'legacy', 'history would', 'decades later', 'generations',
                   'hôm nay', 'ngày nay', 'ký ức', 'tri ân', 'thế hệ', 'lịch sử'],
}


def _norm(s):
    return unicodedata.normalize('NFC', s)


def _split_paragraph(text):
    """Split a paragraph into sentences; keeps abbreviations, decimals (7.5) and dotted numbers (1.954) intact."""
    out, start = [], 0
    for m in re.finditer(r'(\.\.\.|…|[.!?])(["”’»)\]]*)(\s+|$)', text):
        end = m.end(2)
        before = text[start:m.start()]
        word = re.findall(r'([\w.]+)$', before)
        if m.group(1) == '.' and word and word[0].lower().rstrip('.') in ABBR and m.end() < len(text):
            continue
        nxt = text[m.end():m.end() + 1]
        if m.group(1) == '.' and nxt and nxt.islower():  # "approx. five" / mid-sentence period
            continue
        s = text[start:end].strip()
        if s:
            out.append(s)
        start = m.end()
    tail = text[start:].strip()
    if tail:
        out.append(tail)
    return out


def guess_emotion(text, index, words):
    t = text.lower()
    if index == 0:
        return 'hook'
    if t.rstrip('"”’» )').endswith('?'):
        return 'question'
    for emo, keys in KEYWORDS.items():
        if any(k in t for k in keys):
            return emo
    if t.rstrip('"”’» )').endswith('!'):
        return 'urgent'
    if t.rstrip('"”’» )').endswith(('…', '...')) or words <= 5:
        return 'dramatic'
    return 'neutral'


def parse(script):
    """Return (sentences, chapters). Each sentence: id, text, paragraph, emotion, source, pause_override."""
    script = _norm(script.replace('\r\n', '\n'))
    script = re.sub(r'<!--.*?-->', '', script, flags=re.S)
    sents, chapters, para, pending_chapter = [], [], 0, None
    blocks = re.split(r'\n\s*\n', script)
    for block in blocks:
        lines = [l.strip() for l in block.split('\n') if l.strip()]
        body = []
        for l in lines:
            if l.startswith('#'):
                if body:  # chapter heading inside a block closes the paragraph before it
                    _emit(' '.join(body), para, sents); body = []; para += 1
                pending_chapter = l.lstrip('#').strip()
                chapters.append({'title': pending_chapter, 'before': len(sents)})
                if sents:
                    sents[-1]['chapter_after'] = True
            else:
                body.append(l)
        if body:
            _emit(' '.join(body), para, sents)
            para += 1
    for i, s in enumerate(sents):
        s['id'] = f'S{i + 1:03d}'
    for c in chapters:
        c['sentence'] = sents[c['before']]['id'] if c['before'] < len(sents) else None
    return sents, chapters


def _emit(text, para, sents):
    # explicit pauses: "[pause 2.5]" attaches to the sentence before it
    pieces = re.split(r'\[pause\s+([0-9.]+)\s*s?\]', text)
    for k, piece in enumerate(pieces):
        if k % 2 == 1:
            if sents:
                sents[-1]['pause_override'] = float(piece)
            continue
        for raw in _split_paragraph(piece.strip()):
            m = re.match(r'\{(\w+)\}\s*', raw)
            emo = None
            if m and m.group(1).lower() in EMOTIONS:
                emo, raw = m.group(1).lower(), raw[m.end():]
            if not raw.strip():
                continue
            sents.append({'text': raw.strip(), 'paragraph': para, 'emotion': emo, 'source': 'script' if emo else None})
    if sents:
        sents[-1]['paragraph_end'] = True


def design_pauses(sents):
    """Fill emotion (heuristic where missing) and pause_after (unless locked). Mutates and returns sents."""
    for i, s in enumerate(sents):
        words = len(s['text'].split())
        s['words'] = words
        if not s.get('emotion'):
            s['emotion'], s['source'] = guess_emotion(s['text'], i, words), 'heuristic'
    for i, s in enumerate(sents):
        if s.get('locked'):
            continue
        if s.get('pause_override') is not None:
            s['pause_after'], s['pause_why'] = round(s['pause_override'], 3), 'script [pause]'
            continue
        p, why = BASE_PAUSE[s['emotion']], [s['emotion']]
        if s['text'].rstrip('"”’» )').endswith(('…', '...')):
            p += ELLIPSIS; why.append('ellipsis')
        if s['words'] > 28:
            p += LONG; why.append('long')
        if s.get('paragraph_end'):
            p += PARAGRAPH; why.append('paragraph')
        if s.get('chapter_after'):
            p += CHAPTER; why.append('chapter')
        nxt = sents[i + 1] if i + 1 < len(sents) else None
        if nxt and nxt.get('emotion') and abs(HEAT[s['emotion']] - HEAT[nxt['emotion']]) >= 3:
            p += SHIFT; why.append(f'shift->{nxt["emotion"]}')
        if nxt is None:
            p = 0.0; why = ['last']
        s['pause_after'] = round(min(MAX_PAUSE, max(MIN_PAUSE, p)) if nxt else 0.0, 3)
        s['pause_why'] = '+'.join(why)
    return sents
