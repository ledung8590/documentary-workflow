"""Voice check right after `tts --run`, BEFORE any picture is planned (user 2026-11-26: "nếu chờ tới studio xong gen lại
audio thì lâu lắm, vì mỗi câu time gen các lần ra khác"): a sentence voiced again later has another length and moves every
shot after it, so misread sentences are found and redone while the timeline is still only the voice.

  PY scripts/voicecheck.py JOB                 list the sentences Whisper heard poorly (dry run, no credits)
  PY scripts/voicecheck.py JOB --run           transcribe each of them with ElevenLabs Scribe and compare with the text
  PY scripts/voicecheck.py JOB --ok S012,S040 "same reading, Scribe wrote the number in kanji"
                                               the agent's verdict after reading what Scribe heard (reason >= 15 characters)

Verdicts go to voice/checked.json, tied to the clip file: a sentence voiced again must be checked again.
`redo` sentences: set `say` in sentences.json where the reading was wrong (kana for names and codes, numbers spelled out), then
`doc.py tts JOB --only S012,S040 --run` (each sentence as its own job; no need to touch voice.chunked), `doc.py assemble JOB`,
then this script again.
The plan and studio gates fail while a poorly heard sentence has no `ok` for its current clip (gate id voice-unchecked).
"""
import difflib, re, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import job_dir, read, write  # noqa: E402

AUTO_OK = 0.80   # Scribe agrees with the text this well: the clip is right, Whisper was the one that misheard


def weak_limit(text):
    return 0.6 if len(text) >= 15 else 0.34   # the limits of doc.py's "poorly heard" list


def norm(t):
    return re.sub(r'[\W_]+', '', (t or '').lower())


def edges(text, heard):
    """A cut that slipped into the neighbour sentence (film 183: S311 ended on "命中", S312 began with "命中します"):
    words at the start of the clip that the text does not have, or the end of the text missing from the clip."""
    a, b = norm(text), norm(heard)
    blocks = [m for m in difflib.SequenceMatcher(None, a, b, autojunk=False).get_matching_blocks() if m.size]
    if not blocks:
        return 'nothing of the text is heard'
    first, last = blocks[0], blocks[-1]
    if first.a == 0 and first.b >= 3:
        return f'the clip starts with "{b[:first.b]}", which is not in this sentence (cut slipped: redo this sentence and the one before)'
    if last.b + last.size == len(b) and len(a) - (last.a + last.size) >= 2:
        return f'the clip ends before "{a[last.a + last.size:]}" (cut slipped: redo this sentence and the next)'
    return ''


def judge(s, meta, heard):
    want = meta.get('spoken') or s['text']
    r = max(difflib.SequenceMatcher(None, norm(t), norm(heard), autojunk=False).ratio() for t in (want, s['text']))
    edge = edges(want, heard)
    return {'verdict': 'ok' if r >= AUTO_OK and not edge else 'redo', 'by': 'scribe', 'scribe_ratio': round(r, 3), 'heard': heard, **({'edge': edge} if edge else {})}


def state(d):
    """[(sentence, clip audio path, meta dict, entry or None, needs)] for every sentence that needs a verdict."""
    import doc
    cfg = read(d / 'brief.json'); voice = cfg.get('voice') or {}
    checked = read(d / 'voice' / 'checked.json') if (d / 'voice' / 'checked.json').exists() else {}
    out = []
    for s in read(d / 'sentences.json')['sentences']:
        cur = doc.current_clip(d, s, voice)
        if not cur or cur[0].name.split('-', 1)[1].startswith('mock-'):
            continue
        meta = read(cur[1]); e = checked.get(s['id'])
        ratio = meta.get('heard_ratio')
        weak = ratio is not None and ratio < weak_limit(s['text'])
        if not weak and not e:
            continue
        done = bool(e) and e.get('clip') == cur[0].name and e.get('verdict') == 'ok'
        out.append((s, cur[0], meta, e if e and e.get('clip') == cur[0].name else None, not done))
    return out, checked


def open_items(d):
    """Sentence ids still without an `ok` for their current clip (for scripts/gate.py)."""
    try:
        return [s['id'] for s, _, _, _, needs in state(d)[0] if needs]
    except FileNotFoundError:
        return []


def main():
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    args = sys.argv[1:]
    if not args:
        sys.exit(__doc__)
    d = job_dir(args[0]); rows, checked = state(d)
    if '--ok' in args:
        i = args.index('--ok'); ids = args[i + 1].split(','); why = args[i + 2] if len(args) > i + 2 else ''
        if len(why.strip()) < 15:
            sys.exit('give the reason (>= 15 characters): what Scribe heard and why the reading is right')
        byid = {s['id']: (clip, meta) for s, clip, meta, _, _ in rows}
        for sid in ids:
            if sid not in byid:
                print(f'{sid}: not on the list'); continue
            e = checked.get(sid) if (checked.get(sid) or {}).get('clip') == byid[sid][0].name else {}
            checked[sid] = {**(e or {}), 'clip': byid[sid][0].name, 'verdict': 'ok', 'by': 'agent', 'why': why.strip()}
        write(d / 'voice' / 'checked.json', checked)
        rows, checked = state(d)
    todo = [r for r in rows if r[4]]
    if '--run' in args:
        import elevenlabs
        lang = (read(d / 'brief.json').get('voice') or {}).get('language_code')
        for s, clip, meta, e, _ in todo:
            if e and e.get('heard') is not None:
                continue   # Scribe already heard this clip: it waits for a redo or the agent's verdict
            heard = (elevenlabs.stt(clip, language_code=lang) or {}).get('text', '')
            checked[s['id']] = {'clip': clip.name, **judge(s, meta, heard)}
            write(d / 'voice' / 'checked.json', checked)
        for s, clip, meta, e, _ in rows:   # verdicts Scribe gave earlier are judged again by the current rules (no credits)
            if e and e.get('by') == 'scribe' and e.get('heard') is not None:
                checked[s['id']] = {'clip': clip.name, **judge(s, meta, e['heard'])}
        write(d / 'voice' / 'checked.json', checked)
        rows, checked = state(d); todo = [r for r in rows if r[4]]
    print(f'{len(rows)} sentences on the list, {len(rows) - len(todo)} ok, {len(todo)} open')
    for s, clip, meta, e, _ in todo:
        if e:
            print(f'!! {s["id"]} Scribe {e.get("scribe_ratio", 0):.0%}' + (f'  CUT: {e["edge"]}' if e.get('edge') else '') + f'\n     text:  {s["text"][:110]}\n     heard: {(e.get("heard") or "(nothing)")[:110]}')
        else:
            print(f'!! {s["id"]} Whisper {meta.get("heard_ratio", 0):.0%}, not checked: {s["text"][:90]}')
    if todo:
        print('\nFor each: the same words in another script (kanji/kana, digits) = `--ok IDS "reason"`; a wrong, missing or cut reading = set `say`, redo '
              'with `doc.py tts JOB --only IDS --run`, `assemble`, run this again. Do it now, before shots are planned.' if any(r[3] for r in todo)
              else '\nrun with --run (ElevenLabs Scribe, a few credits) before planning any picture')
    sys.exit(1 if todo else 0)


if __name__ == '__main__':
    main()
