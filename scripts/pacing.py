"""Re-pace supplied narration (WAV + Whisper SRT) by emotion, without regenerating the voice.

1. analyse: find a silent stretch at every SRT cue boundary and at sentence ends inside cues (time estimated
   from character position, then searched in the audio). A cut is made only inside silence (10 ms RMS below an
   adaptive threshold), never inside a word; boundaries with no silence stay glued.
2. units: the audio between two cuts. Each unit keeps its source range and the original gap after it.
3. design: sentence-ending units get the emotion pause from sentences.py (also shortens MiniMax's over-long
   pauses); mid-sentence (clause) cuts keep their natural gap, only capped at 0.45 s.
4. rebuild: units are laid out with the new gaps; an optional replacement file per unit (re-read sentence)
   is spliced in at the same cut points. `remap` moves any source time (cues, words) to the new timeline.
"""
import re
from pathlib import Path

import numpy as np

import sentences as SENT

HOP = 0.01
MIN_GAP_CUE, MIN_GAP_INNER = 0.06, 0.12    # shortest silence accepted as a cut
CUE_SLOP, INNER_SLOP = 0.35, 0.6           # Whisper timing error we search around
CLAUSE_MAX = 0.45
HEAD_PAD, TAIL_PAD = 0.04, 0.09
SENT_END = re.compile(r'(\.\.\.|…|[.!?])["”’»)\]]*$')
AUDIO_EXT = ('.wav', '.flac', '.mp3', '.m4a', '.ogg')


def parse_srt(raw):
    cues = []
    for block in re.split(r'\n\s*\n', raw.replace('\r\n', '\n').strip()):
        m = re.search(r'(\d+):(\d+):(\d+)[,.](\d+)\s*-->\s*(\d+):(\d+):(\d+)[,.](\d+)', block)
        if not m:
            continue
        g = [int(x) for x in m.groups()]
        start = g[0] * 3600 + g[1] * 60 + g[2] + g[3] / 1000
        end = g[4] * 3600 + g[5] * 60 + g[6] + g[7] / 1000
        text = ' '.join(l.strip() for l in block[m.end():].split('\n') if l.strip())
        text = re.sub(r'<[^>]+>', '', text).strip()
        if text:
            cues.append({'i': len(cues) + 1, 'start': start, 'end': max(end, start + 0.05), 'text': text})
    return cues


def rms_db(x, sr):
    hop = int(sr * HOP); n = len(x) // hop
    r = np.sqrt(np.mean(np.square(x[:n * hop].reshape(n, hop), dtype=np.float64), axis=1))
    return 20 * np.log10(np.maximum(r, 1e-9))


def threshold(rdb):
    floor = np.percentile(rdb, 5)
    return float(np.clip(floor + 15, -50, -35))


def find_gap(rdb, thr, t0, t1, min_len):
    """Longest run of quiet frames inside [t0, t1]; (a, b) in seconds or None."""
    i0, i1 = max(0, int(t0 / HOP)), min(len(rdb), int(np.ceil(t1 / HOP)))
    if i1 - i0 < 2:
        return None
    q = np.concatenate([[0], (rdb[i0:i1] < thr).astype(np.int8), [0]])
    edges = np.diff(q); starts, ends = np.nonzero(edges == 1)[0], np.nonzero(edges == -1)[0]
    if not len(starts):
        return None
    k = int(np.argmax(ends - starts))
    if (ends[k] - starts[k]) * HOP < min_len:
        return None
    return (i0 + starts[k]) * HOP, (i0 + ends[k]) * HOP


def inner_positions(text):
    """Character positions just after each sentence end inside a cue (not the last)."""
    out, cur = [], 0
    for s in SENT._split_paragraph(text)[:-1]:
        p = text.find(s, cur)
        if p < 0:
            break
        cur = p + len(s); out.append(cur)
    return out


def analyse(x, sr, cues):
    rdb = rms_db(x, sr); thr = threshold(rdb)
    cuts, glued = [], 0
    for i, c in enumerate(cues):
        dur, L = c['end'] - c['start'], len(c['text'])
        for pos in inner_positions(c['text']):
            t = c['start'] + dur * pos / L
            g = find_gap(rdb, thr, max(c['start'], t - INNER_SLOP), min(c['end'], t + INNER_SLOP), MIN_GAP_INNER)
            if g:
                cuts.append({'cue': i, 'pos': pos, 'kind': 'inner', 'a': g[0], 'b': g[1]})
        if i + 1 < len(cues):
            n = cues[i + 1]
            t0 = max(c['start'] + dur / 2, c['end'] - CUE_SLOP)
            t1 = min(n['start'] + CUE_SLOP, (n['start'] + n['end']) / 2)
            g = find_gap(rdb, thr, t0, t1, MIN_GAP_CUE)
            if g:
                cuts.append({'cue': i, 'pos': L, 'kind': 'cue', 'a': g[0], 'b': g[1]})
            else:
                glued += 1
    clean, last_b = [], -1.0
    for c in sorted(cuts, key=lambda c: c['a']):
        if c['a'] >= last_b:
            clean.append(c); last_b = c['b']
    loud = np.nonzero(rdb > thr)[0]
    speech = (max(0.0, loud[0] * HOP - HEAD_PAD), min(len(x) / sr, (loud[-1] + 1) * HOP + TAIL_PAD)) if len(loud) else (0.0, len(x) / sr)
    return units_from(cues, clean, speech), {'threshold_db': thr, 'cuts': len(clean), 'glued_cue_boundaries': glued}


def units_from(cues, cuts, speech):
    units, start, from_cue, from_pos = [], speech[0], 0, 0
    for k, c in enumerate(cuts + [None]):
        to_cue, to_pos = (c['cue'], c['pos']) if c else (len(cues) - 1, len(cues[-1]['text']))
        parts = []
        for ci in range(from_cue, to_cue + 1):
            t = cues[ci]['text']
            parts.append(t[(from_pos if ci == from_cue else 0):(to_pos if ci == to_cue else len(t))].strip())
        if c:
            gap = c['b'] - c['a']
            tail, head = min(TAIL_PAD, 0.4 * gap), min(HEAD_PAD, 0.2 * gap)
            end, nxt = c['a'] + tail, c['b'] - head
        else:
            end, nxt = speech[1], None
        text = ' '.join(p for p in parts if p)
        units.append({'id': f'U{len(units) + 1:03d}', 'src_start': round(start, 3), 'src_end': round(end, 3),
                      'orig_gap': round(nxt - end, 3) if c else 0.0, 'cut': c['kind'] if c else 'end',
                      'cues': [cues[i]['i'] for i in range(from_cue, to_cue + 1)], 'text': text,
                      'ends_sentence': bool(SENT_END.search(text))})
        if c:
            start = nxt
            from_cue, from_pos = (c['cue'], c['pos']) if c['pos'] < len(cues[c['cue']]['text']) else (c['cue'] + 1, 0)
    return [u for u in units if u['src_end'] > u['src_start']]


def design(units, old=None):
    """Emotion + pause per unit. Emotion is judged on the whole sentence (clause units joined) and the
    designed pause goes on the sentence's last unit; mid-sentence cuts keep their natural gap (only capped).
    Agent edits on the sentence's last unit (emotion + source agent, paragraph_end, chapter_after/
    chapter_title) and locked pauses on any unit are kept while the unit text is unchanged."""
    keep = {u['text']: u for u in (old or [])}
    for u in units:
        o = keep.get(u['text'], {})
        for k in ('paragraph_end', 'chapter_after', 'chapter_title'):
            if k in o: u[k] = o[k]
        if o.get('source') == 'agent':
            u['agent_emotion'] = o['emotion']
        if o.get('locked'):
            u['locked'], u['pause_after'], u['pause_why'] = True, o['pause_after'], o.get('pause_why', 'locked')
    groups, cur = [], []
    for u in units:
        cur.append(u)
        if u['ends_sentence'] or u.get('chapter_after') or u.get('paragraph_end'):
            groups.append(cur); cur = []
    if cur:
        groups.append(cur)
    sents = []
    for g in groups:
        last = g[-1]
        sents.append({'text': ' '.join(u['text'] for u in g), 'emotion': last.pop('agent_emotion', None),
                      'paragraph_end': last.get('paragraph_end'), 'chapter_after': last.get('chapter_after'),
                      'locked': last.get('locked'), 'pause_after': last.get('pause_after')})
        if sents[-1]['emotion']:
            sents[-1]['source'] = 'agent'
    SENT.design_pauses(sents)
    for g, s in zip(groups, sents):
        for u in g:
            u.pop('agent_emotion', None)
            u['emotion'], u['source'], u['sentence_words'] = s['emotion'], s['source'], s['words']
            if u.get('locked'):
                continue
            if u is g[-1]:
                u['pause_after'], u['pause_why'] = s['pause_after'], s['pause_why']
            else:  # mid-sentence: keep MiniMax's own breath, only cap an over-long one
                u['pause_after'] = round(min(u['orig_gap'], CLAUSE_MAX), 3)
                u['pause_why'] = 'clause (natural)' if u['orig_gap'] <= CLAUSE_MAX else 'clause (capped)'
    units[-1]['pause_after'] = 0.0
    return units


def merge_to_sentences(units):
    """Keep only sentence-end cuts (for re-voicing whole sentences): clause units join the next unit."""
    out = []
    for u in units:
        if out and not out[-1]['ends_sentence']:
            p = out[-1]
            p.update(src_end=u['src_end'], orig_gap=u['orig_gap'], cut=u['cut'], cues=sorted(set(p['cues'] + u['cues'])),
                     text=(p['text'] + ' ' + u['text']).strip(), ends_sentence=u['ends_sentence'])
        else:
            out.append(dict(u))
    for i, u in enumerate(out):
        u['id'] = f'U{i + 1:03d}'
    return out


def beat_grid(x, sr, lo=60, hi=170):
    """Beat times (s) of a music bed: spectral-flux onsets, tempo by autocorrelation, phase by comb sum."""
    hop, n = 512, 2048
    frames = 1 + (len(x) - n) // hop
    if frames < 8:
        return []
    idx = np.arange(n)[None, :] + hop * np.arange(frames)[:, None]
    spec = np.abs(np.fft.rfft(x[idx] * np.hanning(n), axis=1))
    flux = np.maximum(0, np.diff(np.log1p(spec), axis=0)).sum(1)
    flux = (flux - flux.mean()) / (flux.std() + 1e-9)
    fps = sr / hop
    ac = np.correlate(flux, flux, 'full')[len(flux) - 1:]
    lags = np.arange(int(fps * 60 / hi), int(fps * 60 / lo))
    period = lags[np.argmax(ac[lags])]
    phase = max(range(period), key=lambda ph: flux[ph::period].sum())
    return [(phase + k * period + 1) / fps for k in range((len(flux) - phase) // period)]


def trim_bounds(x, sr, thr=-42.0):
    rdb = rms_db(x, sr); loud = np.nonzero(rdb > thr)[0]
    if not len(loud):
        return 0, len(x)
    hop = int(sr * HOP)
    return max(0, loud[0] * hop - int(HEAD_PAD * sr)), min(len(x), (loud[-1] + 1) * hop + int(TAIL_PAD * sr))


def replacement(folder, uid):
    for ext in AUDIO_EXT:
        p = Path(folder) / f'{uid}{ext}'
        if p.exists():
            return p
    return None


def snap(t, beats, early=0.12, late=0.35):
    """Move a sentence start onto the nearest music beat within [-early, +late] seconds; otherwise leave it."""
    best = None
    for b in beats:
        if -early <= b - t <= late and (best is None or abs(b - t) < abs(best - t)):
            best = b
    return best if best is not None else t


def rebuild(x, sr, units, lead_in, tail, load, replace_dir, beats=None):
    """Returns (voice array, placed units). `load(path)` decodes a replacement file at sr. With `beats`, each
    sentence after a designed pause starts on a music beat (the pause grows or shrinks by at most ~0.35 s)."""
    placed, pieces, t = [], [], float(lead_in)
    for k, u in enumerate(units):
        rep = replacement(replace_dir, u['id']) if replace_dir else None
        if rep:
            y = np.asarray(load(rep), dtype=np.float32); a, b = trim_bounds(y, sr); y = y[a:b].copy()
        else:
            y = np.array(x[int(u['src_start'] * sr):int(u['src_end'] * sr)], dtype=np.float32)
        f = min(len(y) // 4, int(0.005 * sr))
        edge = max(float(20 * np.log10(max(1e-9, np.sqrt(np.mean(np.square(s)))))) for s in (y[:f], y[-f:])) if f else -120.0
        if f:
            y[:f] *= np.linspace(0, 1, f); y[-f:] *= np.linspace(1, 0, f)
        dur = len(y) / sr
        placed.append({**u, 'start': round(t, 4), 'end': round(t + dur, 4), 'replaced': str(rep) if rep else None,
                       'edge_db': round(edge, 1),
                       'scale': dur / max(1e-6, u['src_end'] - u['src_start'])})
        pieces.append((int(round(t * sr)), y))
        t += dur + (u['pause_after'] if k + 1 < len(units) else 0.0)
        if beats and k + 1 < len(units) and u.get('pause_after', 0) >= 0.3:   # sentence breaks only, not clause breaths
            t = snap(t, beats)
    out = np.zeros(int((t + tail) * sr) + 1, dtype=np.float32)
    for at, y in pieces:
        out[at:at + len(y)] += y
    return out, placed


def remap(s, placed):
    """Source time -> new time. Inside a unit: linear (scaled for replacements); in a gap: proportional."""
    if s <= placed[0]['src_start']:
        return max(0.0, placed[0]['start'] - (placed[0]['src_start'] - s))
    for k, u in enumerate(placed):
        if s <= u['src_end']:
            return u['start'] + (max(s, u['src_start']) - u['src_start']) * u['scale']
        nxt = placed[k + 1] if k + 1 < len(placed) else None
        if nxt is None:
            return u['end'] + (s - u['src_end'])
        if s < nxt['src_start']:
            frac = (s - u['src_end']) / max(1e-6, nxt['src_start'] - u['src_end'])
            return u['end'] + frac * (nxt['start'] - u['end'])
    return placed[-1]['end']


def cue_words(cue):
    """Approximate word onsets inside a cue by character position (SRT has no word timing)."""
    words, L, dur = [], max(1, len(cue['text'])), cue['end'] - cue['start']
    for m in re.finditer(r'\S+', cue['text']):
        words.append({'w': m.group(), 'src_start': cue['start'] + dur * m.start() / L,
                      'src_end': cue['start'] + dur * m.end() / L})
    return words
