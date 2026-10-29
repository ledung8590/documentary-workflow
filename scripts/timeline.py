"""timeline.json: the single editable project file shared by the scripts, the agent and the studio (docs/SCHEMA.md).

Clips on any track may carry an `anchor` (and `end_anchor`) that ties them to narration:
  {"sentence": "S004", "edge": "start"|"end", "offset": 0.0}
  {"sentence": "S004", "word": 3, "offset": 0.0}      # 0-based word in that sentence -> exact word onset
  {"cue": 123, "edge": "start"} / {"cue": 123, "word": 2}   # original SRT cue number (narration mode)
In narration mode "sentence" ids are pacing units (U001...); in TTS mode they are S001...
When the voice is regenerated or pauses change, `retime` moves every anchored clip, so scenes, music cuts
and SFX follow the new voice instead of drifting.
"""
TRACKS = [('video', 'video'), ('overlay', 'overlay'), ('voice', 'voiceover'), ('music', 'music'),
          ('original', 'original'), ('sfx', 'sfx')]


def snap(t, fps):
    return round(round(t * fps) / fps, 4)


def resolve(anchor, timing):
    key = anchor['sentence'] if 'sentence' in anchor else f"C{int(anchor['cue']):04d}"
    s = timing.get(key)
    if s is None:
        return None
    if 'word' in anchor:
        words = s['words']
        if not words:
            return None
        t = words[min(anchor['word'], len(words) - 1)]['start']
    else:
        t = s['end'] if anchor.get('edge') == 'end' else s['start']
    return t + anchor.get('offset', 0.0)


def retime(tl, timing):
    """Move anchored clips to the current voice timing. Returns (moved, orphaned, unanchored) counts."""
    fps, moved, orphan, loose = tl['fps'], 0, [], 0
    for tr in tl['tracks']:
        if tr['id'] == 'voice':
            continue
        for c in tr['clips']:
            if 'anchor' not in c:
                loose += 1
                continue
            t = resolve(c['anchor'], timing)
            if t is None:
                orphan.append(c['id']); continue
            length = c.get('end', c['start']) - c['start']
            start = snap(max(0.0, t), fps)
            if 'end_anchor' in c:
                e = resolve(c['end_anchor'], timing)
                end = snap(e, fps) if e is not None else start + length
            else:
                end = snap(start + length, fps)
            if (start, end) != (c['start'], c.get('end', c['start'])):
                moved += 1
            c['start'], c['frame'] = start, round(start * fps)
            if 'end' in c:
                c['end'] = max(end, start + 1 / fps)
    return moved, orphan, loose


def voice_clips(sents, timing):
    out = []
    for s in sents:
        t = timing[s['id']]
        c = {'id': s['id'], 'start': t['start'], 'end': t['end'], 'src': t['src'], 'text': s['text'],
             'emotion': s['emotion'], 'gain_db': 0.0, 'pause_after': s['pause_after']}
        if 'in' in t:  # narration mode: all units live in one rebuilt voice.wav
            c['in'] = t['in']
        out.append(c)
    return out


def placeholders(sents):
    """One video slot per sentence, anchored start->next start, plus a cold-open slot. The agent merges/splits
    these into real scenes (reference pacing: a new shot every ~3-6 s)."""
    out = []
    for i, s in enumerate(sents):
        c = {'id': f'V{i + 1:03d}', 'start': 0.0, 'end': 0.0, 'src': None, 'need': s['text'],
             'anchor': {'sentence': s['id'], 'edge': 'start', 'offset': 0.0 if i else -99.0}}
        if i + 1 < len(sents):
            c['end_anchor'] = {'sentence': sents[i + 1]['id'], 'edge': 'start'}
        else:
            c['end_anchor'] = {'sentence': s['id'], 'edge': 'end', 'offset': 1.5}
        out.append(c)
    return out


def build(job, cfg, sents, chapters, timing, duration, old=None):
    fps = cfg['video']['fps']
    if old:
        tl = old
        tl['duration'] = duration
    else:
        tl = {'version': 1, 'id': job, 'fps': fps, 'width': cfg['video']['width'], 'height': cfg['video']['height'],
              'duration': duration, 'loudness': {'target_lufs': -14.0, 'true_peak': -1.0},
              'tracks': [{'id': i, 'kind': k, 'name': i, 'clips': []} for i, k in TRACKS],
              'markers': [], 'review_notes': [], 'credits': []}
        next(t for t in tl['tracks'] if t['id'] == 'video')['clips'] = placeholders(sents)
    next(t for t in tl['tracks'] if t['id'] == 'voice')['clips'] = voice_clips(sents, timing)
    tl['markers'] = [m for m in tl['markers'] if m.get('kind') != 'chapter']
    for c in chapters:
        if c['sentence']:
            tl['markers'].append({'t': timing[c['sentence']]['start'], 'kind': 'chapter', 'label': c['title'],
                                  'anchor': {'sentence': c['sentence'], 'edge': 'start', 'offset': 0.0}})
    for m in tl['markers']:
        if 'anchor' in m:
            m['t'] = snap(max(0.0, resolve(m['anchor'], timing) or m['t']), fps)
    return tl, retime(tl, timing)  # the first slot's -99 s offset clamps to 0: the cold open covers the lead-in
