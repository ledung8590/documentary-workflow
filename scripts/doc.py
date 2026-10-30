"""Documentary pipeline CLI. Run from the workspace root with the venv python (PY).

  PY scripts/doc.py doctor
  PY scripts/doc.py ingest                      input/<name>.wav + <name>.srt (default, "narration" mode)
                                                or input/<job>/script.txt ("tts" fallback) -> projects/<job>/
  Narration mode (voice made elsewhere, e.g. AI84/MiniMax; never regenerated here):
  PY scripts/doc.py pace JOB                    pacing.json: cut points in silence, emotion + new pause per unit
  PY scripts/doc.py assemble JOB                rebuild voice.wav with the new pauses (+ voice/replace/U###.wav
                                                re-reads spliced in), retimed SRT, words, timeline.json
  TTS fallback mode:
  PY scripts/doc.py split JOB                   sentences.json: emotion + designed pause per sentence
  PY scripts/doc.py tts JOB [--run|--mock] [--only S003,S010]   ElevenLabs per sentence (dry run by default)
  PY scripts/doc.py assemble JOB                trim clips, lay them out with the designed gaps
  PY scripts/doc.py status JOB
  PY scripts/doc.py qa JOB --video FILE [--stt [--run]]   black/freeze/loudness; STT match (costs credits)

Later stages (media, maps, music, sfx, render, mix, studio) are designed in docs/ARCHITECTURE.md and not built yet.
"""
import argparse, difflib, json, re, shutil, subprocess, sys, unicodedata
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import ROOT, PROJECTS, SR, read, write, digest, run, probe, load_audio, save_wav, db, job_dir, mark, elevenlabs_key
import sentences as SENT
import timeline as TL
import pacing as PACE

DEFAULTS = {
    'title': '', 'language': None, 'mode': 'tts',
    'pacing': {'lead_in': 1.5, 'tail': 2.0, 'beat_snap': True},
    # default voice path: script.txt -> AI84 eleven_v4 per sentence with emotion tags (voice chosen by language)
    'voice': {'provider': 'ai84', 'voice_id': '', 'model': 'eleven_v4', 'language_code': None, 'audio_tags': True,
              'format': 'mp3_44100_128', 'lead_in': 3.4, 'tail': 2.5, 'settings': {}},
    'video': {'width': 1920, 'height': 1080, 'fps': 24},
    'qa': {'stt_model': 'scribe_v1', 'stt_min_match': 0.97},
}
# narrator per script language (AI84 shared voices chosen by the user, 2026-10-30); job.json voice.voice_id overrides
VOICES = {'en': ('Gubgw9l4dtIoQA9YZHgx', 'Brian - Deep, Resonant and Comforting'),
          'es': ('l1zE9xgNpUTaQCZzpNJa', 'Alberto Rodríguez - Serious, Narrative'),
          'vi': ('3VnrjnYrskPMDsapTr8X', 'Tung Dang - Deep, Warm and Resonant')}
EDGE_DB = -40.0          # clip head/tail must be quieter than this after trimming
TRIM_DB = -42.0          # speech onset/offset threshold (10 ms RMS)
HEAD_PAD, TAIL_PAD = 0.04, 0.09


def merge(a, b):
    import copy
    out = copy.deepcopy(a)  # never share nested defaults between jobs
    for k, v in (b or {}).items():
        out[k] = merge(a[k], v) if isinstance(v, dict) and isinstance(a.get(k), dict) else v
    return out


def detect_language(text):
    """vi / es / en from the script itself (job.json 'language' overrides). Cheap and transparent: Vietnamese
    tone marks, Spanish marks and stop words; English otherwise."""
    t = text.lower()
    if len(re.findall(r'[ăâđêôơưạảấầẩẫậắằẳẵặẹẻẽếềểễệỉịọỏốồổỗộớờởỡợụủứừửữựỳỵỷỹ]', t)) > max(5, len(t) // 200):
        return 'vi'
    words = re.findall(r'[a-záéíóúñü]+', t)
    es = sum(w in {'el', 'la', 'los', 'las', 'que', 'de', 'del', 'y', 'en', 'un', 'una', 'por', 'con', 'para', 'su', 'se', 'fue'} for w in words)
    en = sum(w in {'the', 'and', 'of', 'to', 'in', 'a', 'was', 'that', 'for', 'with', 'his', 'by', 'were', 'it'} for w in words)
    return 'es' if es > en or re.search(r'[ñ¿¡]', t) else 'en'


def slug(s):
    s = unicodedata.normalize('NFKD', s).encode('ascii', 'ignore').decode()
    return re.sub(r'[^a-z0-9]+', '-', s.lower()).strip('-') or 'job'


# ---------------------------------------------------------------- doctor / ingest
def doctor():
    ok = True
    for tool in ('ffmpeg', 'ffprobe'):
        path = shutil.which(tool); ok &= bool(path)
        print(f'{tool:10s} {"ok " + path if path else "MISSING"}')
    for mod in ('numpy', 'soundfile'):
        try:
            __import__(mod); print(f'{mod:10s} ok')
        except ImportError:
            ok = False; print(f'{mod:10s} MISSING (pip install -r requirements.txt)')
    print(f'{"11labs key":10s} {"set" if elevenlabs_key() else "MISSING: set user env ELEVENLABS_API_KEY"}')
    from elevenlabs import subscription
    sub = subscription()
    if sub:
        print(f'{"11labs plan":10s} {sub}')
    sys.exit(0 if ok else 1)


def discover(folder):
    """[(dir, job name, srt, audio | None, script | None)]. Default: a narration script `<name>.txt` (voice is
    generated); a WAV+SRT pair with the same base name is a supplied-narration job."""
    folder = Path(folder); jobs = []
    for d in [folder] + sorted(p for p in folder.iterdir() if p.is_dir() and not p.name.startswith('_')):
        srts = sorted(d.glob('*.srt'))
        for srt in srts:
            audio = next((srt.with_suffix(e) for e in PACE.AUDIO_EXT if srt.with_suffix(e).exists()), None)
            if audio:
                name = d.name if d != folder and len(srts) == 1 else srt.stem
                jobs.append((d, name, srt, audio, None))
            else:
                print(f'skip {srt.name}: no audio with the same base name')
        if d == folder:  # every loose input/<name>.txt is its own job
            stems = {s.stem for s in srts}
            jobs += [(d, p.stem, None, None, p) for p in sorted(d.glob('*.txt')) if p.stem not in stems and p.name.lower() != 'readme.txt']
            continue
        if srts:
            continue
        scripts = [p for p in d.glob('*') if p.suffix.lower() in ('.txt', '.md') and p.name.lower() != 'readme.md']
        named = [p for p in scripts if p.stem.lower() == 'script'] or (scripts if len(scripts) == 1 else [])
        if named:
            jobs.append((d, d.name, None, None, named[0]))
        elif scripts:
            print(f'skip {d}: several scripts and none named script.txt')
    return jobs


def story_title(name):
    """A readable default title from an input name: '86. MẬT DANH ... I Truyện' -> 'Mật danh ...' (agent shortens it)."""
    t = re.sub(r'^\s*\d+\s*[.)-]\s*', '', name)
    t = re.split(r'\s+[I|]\s+', t)[0].strip()
    return t[:1].upper() + t[1:].lower() if t.isupper() else t


def ingest(folder, story=False, only=None):
    """story: fiction narrated over the user's images (docs/STORY_MODE.md, /gentruyen); only: name substring filter."""
    if story:
        import story as STORY
        found = [(Path(folder), j['name'], None, None, j['script'], j) for j in STORY.discover(folder)]
    else:
        found = [f + (None,) for f in discover(folder)]
    if only:
        found = [f for f in found if only.lower() in f[1].lower()]
    if not found:
        sys.exit(f'no {"story (script + image folder)" if story else "narration (name.wav + name.srt) or script"} in {folder}'
                 f'{" matching " + only if only else ""} (see input/README.md)')
    for d, name, srt, audio, script, st in found:
        cfg_file = d / 'job.json' if d != Path(folder) else Path(folder) / f'{name}.json'
        cfg = merge(DEFAULTS, read(cfg_file) if cfg_file.exists() else {})
        cfg['mode'] = 'narration' if srt else 'tts'
        if st:
            cfg['genre'] = 'story'
            cfg['title'] = cfg.get('title') or story_title(name)
            cfg['story'] = merge({'images': str(st['images']), 'srt': str(st['srt']) if st['srt'] else None,
                                  'prompts': str(st['prompts']) if st['prompts'] else None, 'grade': 'archival'}, cfg.get('story') or {})
            print(f'{name}: story, {st["count"]} images' + (f', image timing from {st["srt"].name}' if st['srt'] else ', no image SRT (images spread evenly)'))
        job = slug(cfg.get('id') or name)[:60]
        p = PROJECTS / job
        if st:
            cfg_file = Path(folder) / f'{name}.json' if (Path(folder) / f'{name}.json').exists() else st['images'] / 'job.json'
            if cfg_file.exists():
                cfg = merge(cfg, read(cfg_file))
        if srt:  # originals stay where they are; size+mtime identify the audio (40-min WAVs are large)
            st_a = audio.stat()
            h = digest(srt.read_text(encoding='utf-8-sig'), str(audio), st_a.st_size, int(st_a.st_mtime))
        else:
            h = digest(script.read_text(encoding='utf-8-sig'))
        state = read(p / 'state.json') if (p / 'state.json').exists() else {'stages': {}}
        if state.get('input_digest') == h:
            print(f'{job}: unchanged, resuming'); continue
        for sub in ('voice/clips', 'voice/replace', 'media', 'maps', 'music', 'sfx', 'qa', 'render'):
            (p / sub).mkdir(parents=True, exist_ok=True)
        if srt:
            shutil.copy2(srt, p / 'narration.srt')
            info = probe(audio)
            a = next((s for s in info.get('streams', []) if s.get('codec_type') == 'audio'), {})
            cfg['source'] = {'audio': str(audio), 'srt': str(srt), 'duration': float(info['format']['duration']),
                             'sample_rate': int(a.get('sample_rate', 0) or 0), 'channels': a.get('channels')}
            if cfg['source']['sample_rate'] and cfg['source']['sample_rate'] < 44100:
                print(f'WARNING {job}: audio is {cfg["source"]["sample_rate"]} Hz; export 44.1/48 kHz from AI84 if possible')
        else:
            text = script.read_text(encoding='utf-8-sig')
            (p / 'script.txt').write_text(text, encoding='utf-8')
            cfg['language'] = cfg.get('language') or detect_language(text)
            cfg['voice']['language_code'] = cfg['voice'].get('language_code') or cfg['language']
            if not cfg['voice'].get('voice_id') and cfg['language'] in VOICES:
                cfg['voice']['voice_id'], cfg['voice']['voice_name'] = VOICES[cfg['language']]
            print(f'{job}: language {cfg["language"]}, voice {cfg["voice"].get("voice_name") or cfg["voice"]["voice_id"] or "NOT SET"}')
        write(p / 'brief.json', cfg)
        if state.get('input_digest'):
            print(f'{job}: input changed; rerun {"pace" if srt else "split"} (agent edits are kept for unchanged text)')
            state['stages'] = {}
        state.update(input_digest=h, mode=cfg['mode'], source=str(srt or script))
        write(p / 'state.json', state)
        if not (p / 'LICENSES.md').exists():
            (p / 'LICENSES.md').write_text('# Media licences for this film\n\n| file | source URL | author | licence | '
                                           'attribution line | downloaded |\n|---|---|---|---|---|---|\n', encoding='utf-8')
        print(f'{job}: ingested ({cfg["mode"]}) {srt or script} -> {p}')


# ---------------------------------------------------------------- split
def split(job):
    d = job_dir(job); need_mode(d, 'tts')
    sents, chapters = SENT.parse((d / 'script.txt').read_text(encoding='utf-8'))
    old = {s['text']: s for s in read(d / 'sentences.json')['sentences']} if (d / 'sentences.json').exists() else {}
    for s in sents:  # keep the agent's reviewed emotion / locked pause for unchanged sentences
        prev = old.get(s['text'])
        if prev and prev.get('source') in ('agent', 'script') and s.get('source') != 'script':
            s['emotion'], s['source'] = prev['emotion'], prev['source']
        if prev and prev.get('locked'):
            s['locked'], s['pause_after'], s['pause_why'] = True, prev['pause_after'], prev.get('pause_why', 'locked')
    SENT.design_pauses(sents)
    write(d / 'sentences.json', {'sentences': sents, 'chapters': chapters})
    mark(d, 'split', count=len(sents))
    from collections import Counter
    print(f'{len(sents)} sentences, {len(chapters)} chapters; emotions {dict(Counter(s["emotion"] for s in sents))}')
    print(f'total designed silence {sum(s["pause_after"] for s in sents):.1f} s')
    for s in sents:
        print(f'{s["id"]} {s["emotion"]:10s} {s["source"]:9s} +{s["pause_after"]:.2f}s  {s["text"][:70]}')
    print('\nReview: set "emotion" (and "source": "agent") per sentence in sentences.json, then rerun split.')


def need_mode(d, mode):
    have = read(d / 'brief.json').get('mode', 'tts')
    if have != mode:
        sys.exit(f'this is a {have} job: use {"pace" if have == "narration" else "split/tts"} instead')


# ---------------------------------------------------------------- pace (narration mode)
def pace(job):
    d = job_dir(job); need_mode(d, 'narration')
    cfg = read(d / 'brief.json')
    cues = PACE.parse_srt((d / 'narration.srt').read_text(encoding='utf-8-sig'))
    if not cues:
        sys.exit('narration.srt has no cues')
    x = load_audio(cfg['source']['audio'])
    dur = len(x) / SR
    if cues[-1]['end'] > dur + 1.0:
        sys.exit(f'SRT ends at {cues[-1]["end"]:.1f} s but audio is {dur:.1f} s: wrong pair?')
    units, stats = PACE.analyse(x, SR, cues)
    if cfg['pacing'].get('cut') == 'sentence':  # whole sentences per unit, e.g. before re-voicing with `voice`
        units = PACE.merge_to_sentences(units)
    old = read(d / 'pacing.json')['units'] if (d / 'pacing.json').exists() else None
    PACE.design(units, old)
    orig = sum(u['orig_gap'] for u in units); new = sum(u['pause_after'] for u in units[:-1])
    speech = sum(u['src_end'] - u['src_start'] for u in units)
    write(d / 'pacing.json', {'stats': {**stats, 'units': len(units), 'source_duration': round(dur, 2),
                                        'speech': round(speech, 2), 'gaps_before': round(orig, 2), 'gaps_after': round(new, 2)},
                              'units': units})
    lines = ['# Pacing units (id · source time · emotion · pause old→new · text)\n',
             'To fix a misread unit: regenerate exactly this text on AI84 and save it as voice/replace/<id>.wav, then assemble.\n']
    for u in units:
        lines.append(f'- **{u["id"]}** {u["src_start"]:.2f}s · {u["emotion"]} · {u["orig_gap"]:.2f}→{u["pause_after"]:.2f}s '
                     f'({u["pause_why"]}) · {u["text"]}')
    (d / 'pacing.md').write_text('\n'.join(lines), encoding='utf-8')
    mark(d, 'pace', units=len(units))
    from collections import Counter
    print(f'{len(cues)} cues -> {len(units)} units; {stats["cuts"]} cuts in silence (threshold {stats["threshold_db"]:.0f} dB), '
          f'{stats["glued_cue_boundaries"]} cue boundaries without silence kept glued')
    print(f'speech {speech:.1f} s; pauses {orig:.1f} s -> {new:.1f} s; film {dur:.1f} s -> '
          f'~{speech + new + cfg["pacing"]["lead_in"] + cfg["pacing"]["tail"]:.1f} s')
    print(f'emotions {dict(Counter(u["emotion"] for u in units))}')
    print('Review pacing.md; edit pacing.json (emotion + "source": "agent", paragraph_end, chapter_after + chapter_title, '
          'pause_after + "locked": true), rerun pace, then assemble.')


# eleven_v4 audio tags per emotion (tags offered by AI84's v4 UI); neutral sentences get none
V4_TAGS = {'hook': '[dramatic]', 'dramatic': '[dramatic]', 'tense': '[dramatic]', 'urgent': '[dramatic]',
           'triumphant': '[dramatic]', 'somber': '[thoughtful]', 'reflective': '[thoughtful]', 'question': '[thoughtful]'}
V4_SPEED = {'urgent': 1.05, 'tense': 1.02, 'somber': 0.93, 'reflective': 0.95, 'dramatic': 0.97, 'hook': 0.98}


def spoken(text):
    """Clean Whisper artefacts so the TTS reads them right: '20. 000' -> '20.000', 'Msta- S' -> 'Msta-S', 152mm -> 152 li."""
    text = re.sub(r'(\d)\.\s+(\d{3})', r'\1.\2', text)
    text = re.sub(r'(\w)-\s+(\w)', r'\1-\2', text)
    return re.sub(r'(\d)\s*mm\b', r'\1 li', text)


def voice_gen(job, do_run=False, only=None):
    """Re-voice every pacing unit (whole sentences: set pacing.cut = "sentence") through AI84 with v4 emotion tags.
    Files go to voice/replace/U###.mp3 and are spliced by `assemble` at the original cut points."""
    import ai84
    d = job_dir(job); need_mode(d, 'narration')
    cfg = read(d / 'brief.json'); v = cfg['voice']; units = read(d / 'pacing.json')['units']
    want = set(only.split(',')) if only else None
    rep = d / 'voice' / 'replace'; rep.mkdir(parents=True, exist_ok=True)
    todo = []
    for u in units:
        if want and u['id'] not in want:
            continue
        tag = u.get('tag', V4_TAGS.get(u['emotion'], ''))
        text = f"{tag} {u.get('say') or spoken(u['text'])}".strip()
        settings = {'stability': 0.5, 'similarity_boost': 0.8, 'style': 0.35, 'speed': V4_SPEED.get(u['emotion'], 1.0),
                    'use_speaker_boost': True}
        key = digest(text, v['voice_id'], v['model'], settings)
        meta = rep / f'{u["id"]}.json'
        if (rep / f'{u["id"]}.mp3').exists() and meta.exists() and read(meta).get('key') == key:
            continue
        todo.append((u, text, settings, key))
    print(f'{len(todo)} units to voice with {v["model"]} / {v["voice_id"]}, {sum(len(t) for _, t, _, _ in todo)} chars')
    for u, text, *_ in todo:
        print(f'  {u["id"]} {text[:90]}')
    if not do_run:
        print('dry run: add --run'); return
    total = 0
    for u, text, settings, key in todo:
        for stale in rep.glob(f'{u["id"]}.*'):
            stale.unlink()
        out, cost = ai84.tts(text, v['voice_id'], v['model'], settings, v.get('language_code'), rep / f'{u["id"]}.mp3')
        write(rep / f'{u["id"]}.json', {'key': key, 'text': text, 'credit_cost': cost, 'provider': 'ai84'})
        total += cost or 0
        print(f'  {u["id"]} ok ({cost} AI84 credits)')
    print(f'done, {total} AI84 credits')


def assemble_narration(d, cfg):
    data = read(d / 'pacing.json'); units = data['units']
    cues = PACE.parse_srt((d / 'narration.srt').read_text(encoding='utf-8-sig'))
    x = load_audio(cfg['source']['audio'])
    beats = []
    if cfg['pacing'].get('beat_snap') and (d / 'timeline.json').exists():
        for c in next((t['clips'] for t in read(d / 'timeline.json')['tracks'] if t['id'] == 'music'), []):
            m = load_audio((d / c['src']).resolve(), 22050)
            beats += [c['start'] + b - c.get('in', 0.0) for b in PACE.beat_grid(m, 22050)
                      if c.get('in', 0.0) <= b <= c.get('in', 0.0) + c['end'] - c['start']]
        print(f'beat snap: {len(beats)} music beats (~{60 / max(1e-6, (beats[-1] - beats[0]) / max(1, len(beats) - 1)):.0f} BPM)' if len(beats) > 1 else 'beat snap: no music')
    voice, placed = PACE.rebuild(x, SR, units, cfg['pacing']['lead_in'], cfg['pacing']['tail'], load_audio, d / 'voice' / 'replace', beats)
    del x
    duration = round(len(voice) / SR, 3)
    save_wav(d / 'voice' / 'voice.wav', voice)
    del voice
    thr = max(-40.0, data['stats']['threshold_db'])  # edges measured before the 5 ms splice fades
    edge_bad = [f'{u["id"]} {u["edge_db"]} dB' for u in placed if u['edge_db'] > thr]
    timing = {u['id']: {'start': u['start'], 'end': u['end'], 'src': 'voice/voice.wav', 'in': u['start'], 'words': []}
              for u in placed}
    out_srt, words_out = [], []
    for c in cues:
        s, t = PACE.remap(c['start'], placed), PACE.remap(c['end'], placed)
        cw = []
        for w in PACE.cue_words(c):
            cw.append({'w': w['w'], 'start': round(PACE.remap(w['src_start'], placed), 3), 'end': round(PACE.remap(w['src_end'], placed), 3)})
            owner = next((u for u in reversed(placed) if u['src_start'] <= w['src_start']), placed[0])
            timing[owner['id']]['words'].append(cw[-1])
        timing[f'C{c["i"]:04d}'] = {'start': round(s, 3), 'end': round(t, 3), 'words': cw}
        out_srt.append(f'{c["i"]}\n{srt_time(s)} --> {srt_time(t)}\n{c["text"]}\n')
    (d / 'voice' / 'voice.srt').write_text('\n'.join(out_srt), encoding='utf-8')
    write(d / 'voice' / 'words.json', [{'sentence': k, 'i': i, **w} for k, v in timing.items() if k.startswith('U')
                                       for i, w in enumerate(v['words'])])
    write(d / 'voice' / 'timing.json', {'mock': False, 'words_approx': True, 'duration': duration, 'sentences': timing})
    chapters = [{'title': u.get('chapter_title') or 'Chapter', 'sentence': placed[k + 1]['id']}
                for k, u in enumerate(placed[:-1]) if u.get('chapter_after')]
    old = read(d / 'timeline.json') if (d / 'timeline.json').exists() else None
    tl, (moved, orphan, loose) = TL.build(d.name, cfg, units, chapters, timing, duration, old)
    tl['mock_voice'] = False
    write(d / 'timeline.json', tl)
    reps = [u['id'] for u in placed if u['replaced']]
    mark(d, 'assemble', duration=duration, replaced=reps)
    print(f'voice.wav {duration:.1f} s (source {cfg["source"]["duration"]:.1f} s), {len(placed)} units'
          + (f', replaced {reps}' if reps else ''))
    print(f'voice.srt: {len(cues)} cues retimed; words.json: onsets estimated from characters (approx.)')
    print(f'timeline.json: {"updated" if old else "created"}; {moved} anchored clips moved, {loose} unanchored left in place')
    if orphan:
        print(f'WARNING anchors to missing units/cues: {orphan}')
    if edge_bad:
        print(f'EDGE CHECK FAILED above {thr:.0f} dB: {edge_bad[:20]}'); sys.exit(1)
    print(f'edge check ok: every spliced edge below {thr:.0f} dB')


# ---------------------------------------------------------------- tts
def v4_request(s, voice):
    """Spoken text with the emotion tag, and voice settings, for eleven_v4 via AI84 (per-sentence `tag`/`say` override)."""
    tag = s.get('tag', V4_TAGS.get(s['emotion'], ''))
    settings = {'stability': 0.5, 'similarity_boost': 0.8, 'style': 0.35, 'speed': V4_SPEED.get(s['emotion'], 1.0),
                'use_speaker_boost': True, **voice.get('settings', {}).get(s['emotion'], {})}
    return f"{tag} {s.get('say') or spoken(s['text'])}".strip(), settings


def clip_key(s, voice):
    if voice.get('provider') == 'ai84':
        text, settings = v4_request(s, voice)
        return digest(text, voice['voice_id'], voice['model'], voice.get('language_code'), settings)
    from elevenlabs import SETTINGS, tts_text
    settings = {**SETTINGS[s['emotion']], **voice.get('settings', {}).get(s['emotion'], {})}
    return digest(tts_text(s, voice), voice['voice_id'], voice['model'], voice.get('language_code'), settings)


def clip_paths(d, s, voice, mock=False):
    key = ('mock-' if mock else '') + clip_key(s, voice)
    base = d / 'voice' / 'clips' / f'{s["id"]}-{key}'
    return base.with_suffix('.mp3' if not mock else '.wav'), base.with_suffix('.json')


def current_clip(d, s, voice):
    """Real clip if present, else a mock clip; (audio, meta) paths or None."""
    for mock in (False, True):
        a, m = clip_paths(d, s, voice, mock)
        if a.exists() and m.exists():
            return a, m
    return None


def mock_clip(s, path, meta):
    """Speech-shaped noise with silence around it, sized like real speech (~14 chars/s)."""
    rng = np.random.default_rng(abs(hash(s['text'])) % 2**32)
    speech = 0.3 + len(s['text']) / 14.0
    n, pad = int(speech * SR), int(0.2 * SR)
    t = np.arange(n) / SR
    env = (0.55 + 0.45 * np.sin(2 * np.pi * 4.3 * t) ** 2) * np.minimum(1, np.minimum(t, speech - t) / 0.03)
    x = np.convolve(rng.standard_normal(n), np.ones(24) / 24, 'same') * env * 0.6
    save_wav(path, np.concatenate([np.zeros(pad), x, np.zeros(pad)]))
    chars = list(s['text']); step = speech / max(1, len(chars))
    write(meta, {'text': s['text'], 'emotion': s['emotion'], 'mock': True, 'alignment': {
        'characters': chars, 'character_start_times_seconds': [0.2 + i * step for i in range(len(chars))],
        'character_end_times_seconds': [0.2 + (i + 1) * step for i in range(len(chars))]}})


def tts(job, do_run=False, mock=False, only=None):
    from elevenlabs import credits, subscription, tts as call, ApiError
    d = job_dir(job); need_mode(d, 'tts')
    if 'split' not in read(d / 'state.json').get('stages', {}):
        sys.exit('run split first')
    cfg, data = read(d / 'brief.json'), read(d / 'sentences.json')
    voice, sents = cfg['voice'], data['sentences']
    want = set(only.split(',')) if only else None
    todo = [s for s in sents if (not want or s['id'] in want) and not clip_paths(d, s, voice, mock)[0].exists()]
    if mock:
        for s in todo:
            mock_clip(s, *clip_paths(d, s, voice, True))
        print(f'{len(todo)} mock clips written (not deliverable; real TTS replaces them)')
        return
    if voice.get('provider') == 'ai84':
        return tts_ai84(d, voice, todo, do_run)
    cost = sum(credits(s['text'], voice['model']) for s in todo)
    print(f'{len(todo)}/{len(sents)} sentences to generate, {sum(len(s["text"]) for s in todo)} chars, '
          f'~{cost} credits with {voice["model"]}')
    sub = subscription()
    if sub and 'limit' in sub and sub['limit']:
        print(f'plan {sub["tier"]}: {sub["limit"] - sub["used"]} of {sub["limit"]} credits left this period')
        if sub['limit'] - sub['used'] < cost:
            print('NOT ENOUGH CREDITS for the whole job')
    if not do_run:
        print('dry run: add --run to spend credits (ask the user first)')
        return
    if not voice.get('voice_id'):
        sys.exit('brief.json voice.voice_id is empty: pick a voice in ElevenLabs Voice Library and set it')
    idx = {s['id']: i for i, s in enumerate(sents)}
    for s in todo:
        i = idx[s['id']]
        prev = sents[i - 1]['text'] if i else None
        nxt = sents[i + 1]['text'] if i + 1 < len(sents) else None
        audio, meta = clip_paths(d, s, voice)
        try:
            mp3, align = call(s, prev, nxt, voice)
        except ApiError as e:
            sys.exit(f'{s["id"]}: {e}')
        audio.write_bytes(mp3)
        write(meta, {'text': s['text'], 'emotion': s['emotion'], 'model': voice['model'], 'voice_id': voice['voice_id'],
                     'credits': credits(s['text'], voice['model']), 'alignment': align})
        print(f'{s["id"]} ok {len(mp3) // 1024} KB')
    mark(d, 'tts', model=voice['model'])


def tts_ai84(d, voice, todo, do_run):
    """Default voice path: one AI84 eleven_v4 job per sentence, emotion tag in front (about 1 AI84 credit/char)."""
    import ai84
    reqs = [(s, *v4_request(s, voice)) for s in todo]
    print(f'{len(todo)} sentences to voice via AI84 {voice["model"]} / {voice.get("voice_name") or voice["voice_id"]}, '
          f'{sum(len(t) for _, t, _ in reqs)} chars (~same in AI84 credits)')
    for s, text, _ in reqs[:12]:
        print(f'  {s["id"]} {text[:90]}')
    if not do_run:
        print('dry run: add --run'); return
    if not voice.get('voice_id'):
        sys.exit('brief.json voice.voice_id is empty (no default voice for this language): set one')
    def one(req):
        s, text, settings = req
        audio, meta = clip_paths(d, s, voice)
        audio.parent.mkdir(parents=True, exist_ok=True)
        _, cost = ai84.tts(text, voice['voice_id'], voice['model'], settings, voice.get('language_code'), audio)
        write(meta, {'text': s['text'], 'spoken': text, 'emotion': s['emotion'], 'provider': 'ai84', 'model': voice['model'],
                     'voice_id': voice['voice_id'], 'credit_cost': cost, 'alignment': None})
        return s['id'], cost

    # a few jobs in flight at once (AI84 allows 60 POST/min); each sentence is cached, so a rerun resumes
    from concurrent.futures import ThreadPoolExecutor, as_completed
    total, failed = 0, []
    with ThreadPoolExecutor(max_workers=int(voice.get('workers', 4))) as pool:
        futs = {pool.submit(one, r): r[0]['id'] for r in reqs}
        for k, f in enumerate(as_completed(futs), 1):
            try:
                sid, cost = f.result()
            except RuntimeError as e:
                failed.append(futs[f]); print(f'  {futs[f]} FAILED: {e}', flush=True); continue
            total += cost or 0
            print(f'  [{k}/{len(reqs)}] {sid} ok ({cost} AI84 credits)', flush=True)
    print(f'done, {total} AI84 credits' + (f'; {len(failed)} failed, rerun to retry: {",".join(failed)}' if failed else ''))
    if failed:
        return
    mark(d, 'tts', model=voice['model'], provider='ai84')


def approx_words(text, dur):
    """Word onsets spread by character count over the trimmed clip (when the provider gives no alignment)."""
    toks = [m for m in re.finditer(r'\S+', text)]
    L = max(1, len(text)); lead, span = 0.04, max(0.1, dur - 0.13)
    return [{'w': m.group(), 'start': round(lead + span * m.start() / L, 3), 'end': round(lead + span * m.end() / L, 3)} for m in toks]


def subtitle_cues(text, start, end, words, maxlen=42):
    """Split a sentence into subtitle cues of <= maxlen chars at word boundaries, timed by its words."""
    cues, cur, t0 = [], [], None
    for w in words:
        if cur and len(' '.join(x['w'] for x in cur + [w])) > maxlen:
            cues.append((t0, w['start'] - 0.02, ' '.join(x['w'] for x in cur))); cur, t0 = [], None
        if t0 is None:
            t0 = w['start']
        cur.append(w)
    if cur:
        cues.append((t0, end, ' '.join(x['w'] for x in cur)))
    return cues or [(start, end, text)]


# ---------------------------------------------------------------- assemble
def trim_bounds(x):
    hop = SR // 100
    frames = len(x) // hop
    if not frames:
        return 0, len(x)
    rms = np.sqrt(np.mean(x[:frames * hop].reshape(frames, hop) ** 2, axis=1))
    loud = np.nonzero(db(rms) > TRIM_DB)[0]
    if not len(loud):
        return 0, len(x)
    a = max(0, loud[0] * hop - int(HEAD_PAD * SR))
    b = min(len(x), (loud[-1] + 1) * hop + int(TAIL_PAD * SR))
    return a, b


def words_from(alignment, shift, limit):
    """Group character timings into words; times relative to the trimmed clip."""
    if not alignment:
        return []
    ch, st, en = alignment['characters'], alignment['character_start_times_seconds'], alignment['character_end_times_seconds']
    words, cur = [], None
    for c, a, b in zip(ch, st, en):
        if c.isspace():
            cur = None; continue
        if cur is None:
            cur = {'w': '', 'start': a, 'end': b}; words.append(cur)
        cur['w'] += c; cur['end'] = b
    words = [w for w in words if not (w['w'].startswith('[') and w['w'].endswith(']'))]  # v3 audio tags
    for w in words:
        w['start'] = round(min(limit, max(0.0, w['start'] - shift)), 3)
        w['end'] = round(min(limit, max(0.0, w['end'] - shift)), 3)
    return words


def srt_time(t):
    ms = int(round(t * 1000)); h, ms = divmod(ms, 3600000); m, ms = divmod(ms, 60000); s, ms = divmod(ms, 1000)
    return f'{h:02d}:{m:02d}:{s:02d},{ms:03d}'


def assemble(job):
    d = job_dir(job)
    cfg = read(d / 'brief.json')
    if cfg.get('mode') == 'narration':
        if 'pace' not in read(d / 'state.json').get('stages', {}):
            sys.exit('run pace first')
        return assemble_narration(d, cfg)
    data = read(d / 'sentences.json')
    voice, sents = cfg['voice'], data['sentences']
    missing = [s['id'] for s in sents if not current_clip(d, s, voice)]
    if missing:
        sys.exit(f'no clip for {len(missing)} sentences ({", ".join(missing[:8])}...): run tts')
    beats = []
    if cfg['pacing'].get('beat_snap') and (d / 'timeline.json').exists():
        for c in next((tr['clips'] for tr in read(d / 'timeline.json')['tracks'] if tr['id'] == 'music'), []):
            m = load_audio((d / c['src']).resolve(), 22050)
            beats += [c['start'] + b - c.get('in', 0.0) for b in PACE.beat_grid(m, 22050)]
    t, pieces, timing, edge_bad, mocked = float(voice['lead_in']), [], {}, [], False
    for k, s in enumerate(sents):
        if k and beats and sents[k - 1]['pause_after'] >= 0.3:
            t = PACE.snap(t, beats)  # sentence starts land on the music's beat
        apath, mpath = current_clip(d, s, voice)
        meta = read(mpath); mocked |= bool(meta.get('mock'))
        x = load_audio(apath)
        a, b = trim_bounds(x)
        y = x[a:b].copy()
        f_in, f_out = int(0.008 * SR), int(0.03 * SR)
        y[:f_in] *= np.linspace(0, 1, f_in)[:len(y[:f_in])]
        y[-f_out:] *= np.linspace(1, 0, f_out)[-len(y[-f_out:]):]
        edge = int(0.005 * SR)
        head, tail = db(np.sqrt(np.mean(y[:edge] ** 2))), db(np.sqrt(np.mean(y[-edge:] ** 2)))
        if max(head, tail) > EDGE_DB:
            edge_bad.append(f'{s["id"]} head {head:.0f} dB tail {tail:.0f} dB')
        dur = len(y) / SR
        clip_out = d / 'voice' / 'trimmed' / f'{s["id"]}.wav'
        save_wav(clip_out, y)
        ws = words_from(meta.get('alignment'), a / SR, dur) or approx_words(s['text'], dur)
        timing[s['id']] = {'start': round(t, 4), 'end': round(t + dur, 4), 'src': str(clip_out.relative_to(d)).replace('\\', '/'),
                           'words': [{**w, 'start': round(t + w['start'], 3), 'end': round(t + w['end'], 3)} for w in ws],
                           'approx_words': not meta.get('alignment')}
        pieces.append((int(round(t * SR)), y))
        t += dur + s['pause_after']
    duration = round(t + float(voice['tail']), 3)
    track = np.zeros(int(duration * SR) + 1, dtype=np.float32)
    for at, y in pieces:
        track[at:at + len(y)] += y
    save_wav(d / 'voice' / 'voice.wav', track)
    write(d / 'voice' / 'timing.json', {'mock': mocked, 'lead_in': voice['lead_in'], 'duration': duration, 'sentences': timing})
    write(d / 'voice' / 'words.json', [{'sentence': k, 'i': i, **w} for k, v in timing.items() for i, w in enumerate(v['words'])])
    cues = [c for s in sents for c in subtitle_cues(s['text'], timing[s['id']]['start'], timing[s['id']]['end'], timing[s['id']]['words'])]
    srt = [f'{i + 1}\n{srt_time(a)} --> {srt_time(b)}\n{txt}\n' for i, (a, b, txt) in enumerate(cues)]
    (d / 'voice' / 'voice.srt').write_text('\n'.join(srt), encoding='utf-8')  # generated SRT: no external app needed
    old = read(d / 'timeline.json') if (d / 'timeline.json').exists() else None
    tl, (moved, orphan, loose) = TL.build(d.name, cfg, sents, data['chapters'], timing, duration, old)
    tl['mock_voice'] = mocked
    tl['language'] = cfg.get('language') or tl.get('language')
    write(d / 'timeline.json', tl)
    mark(d, 'assemble', duration=duration, mock=mocked)
    print(f'voice.wav {duration:.2f} s, {len(sents)} clips, lead-in {voice["lead_in"]} s'
          + ('  [MOCK VOICE: not deliverable]' if mocked else ''))
    print(f'timeline.json: {"updated" if old else "created"}; {moved} anchored clips moved, {loose} unanchored left in place')
    if orphan:
        print(f'WARNING anchors to missing sentences: {orphan}')
    if edge_bad:
        print('EDGE CHECK FAILED (clip may be cut):\n  ' + '\n  '.join(edge_bad)); sys.exit(1)
    print(f'edge check ok: every clip starts and ends below {EDGE_DB:.0f} dB')


# ---------------------------------------------------------------- status / qa
def status(job):
    d = job_dir(job)
    st = read(d / 'state.json')
    for k, v in st.get('stages', {}).items():
        print(f'{k:10s} {v}')
    if (d / 'timeline.json').exists():
        tl = read(d / 'timeline.json')
        print(f'timeline   {tl["duration"]:.1f} s; ' + ', '.join(f'{t["id"]}={len(t["clips"])}' for t in tl['tracks'])
              + f'; notes open={sum(n.get("status") != "done" for n in tl["review_notes"])}')
        empty = sum(1 for c in tl['tracks'][0]['clips'] if not c.get('src'))
        if empty:
            print(f'           {empty} video slots still without media')


def norm_words(text):
    text = unicodedata.normalize('NFKD', text.lower())
    text = ''.join(c for c in text if not unicodedata.combining(c)).replace('đ', 'd')
    return re.findall(r'[a-z0-9]+', text)


def qa(job, video, stt=False, do_run=False):
    d = job_dir(job)
    tl = read(d / 'timeline.json') if (d / 'timeline.json').exists() else {'tracks': []}
    report = {'video': str(video)}
    err = subprocess.run(['ffmpeg', '-hide_banner', '-i', str(video), '-vf', 'blackdetect=d=0.4:pix_th=0.10,freezedetect=n=-60dB:d=1.5',
                          '-af', 'ebur128=peak=true', '-f', 'null', '-'], capture_output=True, text=True, errors='replace').stderr
    black = [(float(a), float(b)) for a, b in re.findall(r'black_start:([\d.]+) black_end:([\d.]+)', err)]
    freeze_s = [float(x) for x in re.findall(r'freeze_start: ([\d.]+)', err)]
    freeze_e = [float(x) for x in re.findall(r'freeze_end: ([\d.]+)', err)]
    cards = [(c['start'], c['end']) for t in tl['tracks'] if t['id'] == 'overlay' for c in t['clips']
             if c.get('type') in ('title_card', 'quote', 'black', 'stat', 'chapter', 'question')]
    expected = lambda a, b: any(a >= s - 0.2 and b <= e + 0.2 for s, e in cards)
    report['black'] = [{'start': a, 'end': b, 'expected': expected(a, b)} for a, b in black]
    report['freeze'] = [{'start': a, 'end': b, 'expected': expected(a, b)} for a, b in zip(freeze_s, freeze_e + [None] * 9)]
    lufs = re.findall(r'I:\s+(-?[\d.]+) LUFS', err); peak = re.findall(r'Peak:\s+(-?[\d.]+) dBFS', err)
    report['lufs'] = float(lufs[-1]) if lufs else None
    report['true_peak'] = float(peak[-1]) if peak else None
    # card sound: a title/chapter card must land on an audible hit (two films shipped with card hits 20-35 dB under
    # the voice, "silent" cards), and every card must have an SFX cue starting inside it (quote cards: the typing)
    sfx = [c['start'] for t in tl['tracks'] if t['id'] == 'sfx' for c in t['clips']]
    report['cards'] = []
    for t in tl['tracks']:
        for c in t['clips'] if t['id'] == 'overlay' else []:
            if c.get('type') not in ('title_card', 'chapter', 'quote'):
                continue
            a = subprocess.run(['ffmpeg', '-hide_banner', '-ss', f'{c["start"]:.3f}', '-t', '1.6', '-i', str(video), '-vn', '-af',
                                'astats=measure_perchannel=none:measure_overall=RMS_level', '-f', 'null', '-'],
                               capture_output=True, text=True, errors='replace').stderr
            rms = re.findall(r'RMS level dB: (-?[\d.]+|-inf)', a)
            rms = float(rms[-1]) if rms and rms[-1] != '-inf' else -99.0
            cue = any(c['start'] - 0.8 <= s <= c['start'] + 1.5 for s in sfx)
            ok = cue and (c['type'] == 'quote' or rms >= -20.0)
            report['cards'].append({'type': c['type'], 'start': round(c['start'], 2), 'rms_db': round(rms, 1), 'sfx_cue': cue, 'ok': ok})
    if stt:
        from elevenlabs import stt as transcribe
        cfg = read(d / 'brief.json')
        if not do_run:
            print('STT dry run: transcribing costs credits per audio minute; add --run after the user agrees')
        else:
            res = transcribe(video, cfg['qa']['stt_model'], cfg['voice'].get('language_code'))
            write(d / 'qa' / 'stt.json', res)
            src = read(d / 'pacing.json')['units'] if cfg.get('mode') == 'narration' else read(d / 'sentences.json')['sentences']
            ref = norm_words(' '.join(s['text'] for s in src))
            hyp = norm_words(' '.join(w['text'] for w in res.get('words', []) if w.get('type') == 'word'))
            sm = difflib.SequenceMatcher(a=ref, b=hyp, autojunk=False)
            report['stt_match'] = round(sm.ratio(), 4)
            report['stt_diffs'] = [{'op': op, 'script': ' '.join(ref[a1:a2]), 'heard': ' '.join(hyp[b1:b2])}
                                   for op, a1, a2, b1, b2 in sm.get_opcodes() if op != 'equal'][:60]
    write(d / 'qa' / 'qa.json', report)
    bad_black = [b for b in report['black'] if not b['expected']]
    bad_freeze = [f for f in report['freeze'] if not f['expected']]
    print(f'loudness {report["lufs"]} LUFS (target -14), true peak {report["true_peak"]} dBFS (max -1)')
    print(f'black {len(black)} ({len(bad_black)} unexpected), freeze {len(freeze_s)} ({len(bad_freeze)} unexpected)')
    bad_cards = [c for c in report['cards'] if not c['ok']]
    print(f'card sound: {len(report["cards"]) - len(bad_cards)}/{len(report["cards"])} cards land on an audible SFX cue'
          + ''.join(f'\n  SILENT {c["type"]} at {c["start"]} s: {c["rms_db"]} dB RMS, cue {c["sfx_cue"]}' for c in bad_cards))
    if 'stt_match' in report:
        print(f'STT word match {report["stt_match"]:.1%}; diffs in qa/qa.json (judge names/spellings, do not hide)')
    print('Automated checks only. Inspect the flagged frames yourself before delivering.')


# ---------------------------------------------------------------- media
def media_search(job, query, tag, n, sources, kind='photo'):
    import media as M
    d = job_dir(job)
    tag = slug(tag or query)[:40]
    found, errors = M.search(query, sources.split(','), max(n * 3, 20), kind)
    ok = [c for c in found if c['allowed'] and c.get('download')]
    print(f'{len(found)} results, {len(ok)} with an allowed licence' + (f'; errors: {errors}' if errors else ''))
    folder = d / 'media' / 'candidates' / tag
    keep, sheet = [], []
    for c in ok:
        if len(keep) >= n:
            break
        try:
            got = M.preview(c, folder)
            c['file'] = str(got.relative_to(d)).replace('\\', '/')
        except RuntimeError as e:  # long rate-limit block: stop instead of hammering the server
            print(f'  stop: {e}'); break
        except (OSError, ValueError, subprocess.SubprocessError) as e:
            print(f'  skip {c["source"]} {c["id"]}: {str(e)[:80]}'); continue
        keep.append(c)
        dur = f' {c["duration"]:.0f}s' if c.get('duration') else ''
        sheet.append((f'#{len(keep)}{dur} {c["source"].split(":")[-1]} | {c["licence"]}', d / c['file']))
    write(folder / 'candidates.json', {'query': query, 'candidates': keep})
    if keep:
        out = M.contact_sheet(sheet, d / 'qa' / f'media-{tag}.jpg')
        print(f'contact sheet: {out}')
    for k, c in enumerate(keep, 1):
        dur = f' {c["duration"]:.1f}s' if c.get('duration') else ''
        print(f'#{k} [{c["source"]}]{dur} {c["licence"]} | {c["title"][:80]}' + (f'  !! {"; ".join(c["flags"])}' if c['flags'] else ''))
    extra = ' --in SECONDS [--dur SECONDS]' if kind == 'video' else ''
    print(f'Look at the sheet, read each file page, then: doc.py media {job} pick SLOT {tag} K --caption "what it shows"{extra}')


def media_strip(job, tag, k, every=3.0):
    """Filmstrip of a video candidate with timestamps, to choose --in by looking instead of guessing."""
    import media as M
    d = job_dir(job)
    c = read(d / 'media' / 'candidates' / tag / 'candidates.json')['candidates'][k - 1]
    src = M.fetch_video(c, d / 'media' / 'candidates' / tag)
    out = d / 'qa' / f'strip-{tag}-{k}.jpg'
    n = max(1, int((c.get('duration') or 60) / every))
    rows = (min(n, 36) + 5) // 6
    run(['ffmpeg', '-v', 'error', '-y', '-i', src, '-vf',
         f"fps=1/{every},scale=320:-1,drawtext=fontfile='C\\:/Windows/Fonts/arial.ttf':text='%{{pts\\:hms}}':"
         f"x=5:y=5:fontcolor=yellow:fontsize=20,tile=6x{rows}", '-frames:v', '1', out])
    print(f'filmstrip every {every:g} s: {out}  (then pick with --in at the shot you want)')


def media_pick(job, slot, tag, k, caption, t_in=0.0, dur=None):
    import media as M
    d = job_dir(job)
    c = read(d / 'media' / 'candidates' / tag / 'candidates.json')['candidates'][k - 1]
    tl = read(d / 'timeline.json')
    clip = next((x for t in tl['tracks'] if t['id'] == 'video' for x in t['clips'] if x['id'] == slot), None)
    if clip is None:
        sys.exit(f'no video clip {slot}')
    if c.get('kind') == 'video':  # cut only the needed range (+0.5 s handles) from the original file
        need = dur or (clip['end'] - clip['start'] + 0.5)
        dst = d / 'media' / f'{slot}-{c["source"].split(":")[0]}-{c["id"]}.mp4'
        M.fetch_range(M.fetch_video(c, d / 'media' / 'candidates' / tag), t_in, need, dst)
        clip.update(kind='video', **{'in': 0.0})
    else:
        dst = M.download(c, d / 'media')  # full 1920 px only now, for the picked file
        clip['kind'] = 'photo'
    rel = f'media/{dst.name}'
    author = re.sub(r'\s+', ' ', c['author'] or 'unknown author')[:80]
    credit = f'{author} / {c["source"].split(":")[-1].title()} ({c["licence"]})'
    clip.update(src=rel, credit=credit, caption=caption or clip.get('caption'), page=c['page'])
    tl['credits'] = [x for x in tl['credits'] if x.get('file') != rel] + [{'file': rel, 'line': credit, 'page': c['page']}]
    write(d / 'timeline.json', tl)
    import datetime
    row = (f'| {rel} | {c["page"]} | {author} | {c["licence"]} {c.get("licence_url") or ""} | {credit} | '
           f'{datetime.date.today()} | {(caption or c["title"])[:120]} |\n')
    with open(d / 'LICENSES.md', 'a', encoding='utf-8') as f:
        f.write(row)
    print(f'{slot} <- {rel}  [{c["licence"]}]' + (f'  !! {"; ".join(c["flags"])}' if c['flags'] else ''))


# ---------------------------------------------------------------- build
def build(job, what):
    import render as R
    d = job_dir(job)
    tl = read(d / 'timeline.json')
    if tl.get('mock_voice'):
        print('WARNING: mock voice - test render only, not deliverable')
    (d / 'render').mkdir(exist_ok=True)
    pic, aud = d / 'render' / 'picture.mp4', d / 'render' / 'mix.wav'
    if what in ('picture', 'all'):
        missing = [c['id'] for t in tl['tracks'] if t['id'] == 'video' for c in t['clips'] if not c.get('src') and c.get('kind') != 'card']
        if missing:
            print(f'{len(missing)} video slots without media render as red "MISSING MEDIA" slates: {missing[:10]}')
        R.picture(d, tl, pic); print(f'picture -> {pic}')
    if what in ('mix', 'all'):
        beds = R.mix(d, tl, aud); print(f'mix -> {aud} ({beds} bed clips ducked under the voice)')
    if what == 'all':
        out = ROOT / 'output' / d.name / 'video.mp4'
        R.mux(pic, aud, out)
        used = {c['src'] for t in tl['tracks'] for c in t['clips'] if c.get('src') and t['id'] != 'voice'}
        rows = (d / 'LICENSES.md').read_text(encoding='utf-8').split('\n')
        keep = [r for r in rows if not r.startswith('| media/') or r.split('|')[1].strip() in used]
        (out.parent / 'LICENSES.md').write_text('\n'.join(keep), encoding='utf-8')  # only media actually on screen
        lines = sorted({c['line'] + (f' - {c["page"]}' if c.get('page') else '') for c in tl.get('credits', []) if c['file'] in used})
        (out.parent / 'credits.txt').write_text('Archival media:\n' + '\n'.join(lines) + '\n', encoding='utf-8')
        mark(d, 'build', output=str(out))
        print(f'video -> {out}\nnext: doc.py qa {job} --video "{out}" and inspect frames')


def story_build(job):
    """Story mode: images, cards, music and card SFX into timeline.json (after assemble), via the studio store."""
    import story as STORY
    sys.path.insert(0, str(ROOT / 'studio'))
    import core as C
    d = job_dir(job); brief = read(d / 'brief.json')
    if brief.get('genre') != 'story':
        sys.exit(f'{job} is not a story job (ingest --story)')
    timing = read(d / 'voice' / 'timing.json')['sentences']
    sj = read(d / 'sentences.json')
    proj = C.Project(d.name)
    res, tag = proj.transact(lambda tl: STORY.build(d, tl, brief, timing, sj['sentences'], sj.get('chapters', [])), who='agent', why='story build')
    mark(d, 'story', summary=res)
    print(f'timeline.json saved (etag {tag}). Next: doc.py build {job} --only picture, then doc.py studio {job} (review stop).')


def ops(job, file, why):
    """Apply timeline clip ops (the studio's format, docs/STUDIO.md / studio/core.apply_ops) from a JSON file: same store
    as the studio and its MCP server (ETag lock, history, moved clips re-anchored to the nearest word)."""
    sys.path.insert(0, str(ROOT / 'studio'))
    import core as C
    proj = C.Project(job_dir(job).name)
    lst = json.loads(Path(file).read_text(encoding='utf-8'))
    try:
        log, tag = proj.transact(lambda tl: C.apply_ops(tl, lst if isinstance(lst, list) else lst['ops'], proj.anchors()), who='agent', why=why)
    except (C.OpError, C.Conflict) as e:
        sys.exit(f'ops not applied (timeline unchanged): {e}')
    print('\n'.join(log)); print(f'timeline.json saved (etag {tag})')


PLANNED = {
    'maps': 'terrain + satellite map stills/moves with attribution (docs/MEDIA.md#maps)',
}


def main():
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')  # Vietnamese text on a cp1252 console
    ap =argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest='cmd', required=True)
    sub.add_parser('doctor')
    q = sub.add_parser('ingest'); q.add_argument('--input', default=str(ROOT / 'input'))
    q.add_argument('--story', action='store_true', help='fiction over your own images (docs/STORY_MODE.md)'); q.add_argument('--only')
    q = sub.add_parser('story'); q.add_argument('job')
    for c in ('split', 'pace', 'assemble', 'status'):
        sub.add_parser(c).add_argument('job')
    q = sub.add_parser('tts'); q.add_argument('job'); q.add_argument('--run', action='store_true')
    q.add_argument('--mock', action='store_true'); q.add_argument('--only')
    q = sub.add_parser('qa'); q.add_argument('job'); q.add_argument('--video', required=True)
    q.add_argument('--stt', action='store_true'); q.add_argument('--run', action='store_true')
    q = sub.add_parser('media'); q.add_argument('job'); ms = q.add_subparsers(dest='mcmd', required=True)
    s = ms.add_parser('search'); s.add_argument('query'); s.add_argument('--tag'); s.add_argument('--n', type=int, default=8)
    s.add_argument('--sources', default='commons,openverse,dvids'); s.add_argument('--kind', choices=('photo', 'video'), default='photo')
    s = ms.add_parser('pick'); s.add_argument('slot'); s.add_argument('tag'); s.add_argument('k', type=int)
    s.add_argument('--caption'); s.add_argument('--in', dest='t_in', type=float, default=0.0); s.add_argument('--dur', type=float)
    s = ms.add_parser('strip'); s.add_argument('tag'); s.add_argument('k', type=int); s.add_argument('--every', type=float, default=3.0)
    q = sub.add_parser('build'); q.add_argument('job'); q.add_argument('--only', choices=('picture', 'mix', 'all'), default='all')
    q = sub.add_parser('voice'); q.add_argument('job'); q.add_argument('--run', action='store_true'); q.add_argument('--only')
    q = sub.add_parser('ops'); q.add_argument('job'); q.add_argument('file'); q.add_argument('--why', default='doc.py ops')
    q = sub.add_parser('studio'); q.add_argument('job'); q.add_argument('--port', default='5280'); q.add_argument('--no-browser', action='store_true')
    for c in PLANNED:
        sub.add_parser(c).add_argument('job', nargs='?')
    a = ap.parse_args()
    if a.cmd == 'media':
        if a.mcmd == 'search':
            return media_search(a.job, a.query, a.tag, a.n, a.sources, a.kind)
        if a.mcmd == 'strip':
            return media_strip(a.job, a.tag, a.k, a.every)
        return media_pick(a.job, a.slot, a.tag, a.k, a.caption, a.t_in, a.dur)
    if a.cmd == 'build':
        return build(a.job, a.only)
    if a.cmd == 'voice':
        return voice_gen(a.job, a.run, a.only)
    if a.cmd == 'story':
        return story_build(a.job)
    if a.cmd == 'ops':
        return ops(a.job, a.file, a.why)
    if a.cmd == 'studio':  # web studio + review notes (docs/STUDIO.md); the agent side is studio/mcp_server.py
        return subprocess.call([sys.executable, str(ROOT / 'studio' / 'server.py'), a.job, '--port', a.port] + (['--no-browser'] if a.no_browser else []))
    if a.cmd in PLANNED:
        sys.exit(f'{a.cmd}: not built yet - planned: {PLANNED[a.cmd]}')
    {'doctor': lambda: doctor(), 'ingest': lambda: ingest(a.input, a.story, a.only), 'split': lambda: split(a.job), 'pace': lambda: pace(a.job),
     'assemble': lambda: assemble(a.job), 'status': lambda: status(a.job),
     'tts': lambda: tts(a.job, a.run, a.mock, a.only), 'qa': lambda: qa(a.job, a.video, a.stt, a.run)}[a.cmd]()


if __name__ == '__main__':
    main()
