"""MCP server (stdio, JSON-RPC 2.0, stdlib only) so Claude Code can edit a finished film's timeline.json while the user
reviews in the web studio (studio/server.py). Same store as the UI: ETag-guarded writes, history in render/studio/history.

Tools: get_timeline, update_clips, list_review_notes, set_note_status, render_preview, render_frame, export, get_job,
effect_catalog.
Registered in the repo's .mcp.json. The project defaults to the one the studio last opened (studio/.last_project).
"""
import base64, json, sys, traceback
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import core as C  # noqa: E402

PROJ = {'type': 'string', 'description': 'Project id in projects/ (default: the project the studio last opened).'}
TOOLS = [
    {'name': 'get_timeline',
     'description': 'Read the film timeline. Without t0/t1 returns a summary (tracks, clip counts, markers, open notes, picture-dirty '
                    'ranges, etag). With t0/t1 returns every clip overlapping that window (seconds) plus the narration there. '
                    'ids returns exactly those clips. Use the etag as if_match in update_clips.',
     'inputSchema': {'type': 'object', 'properties': {'project': PROJ, 't0': {'type': 'number'}, 't1': {'type': 'number'},
                                                      'tracks': {'type': 'array', 'items': {'type': 'string'}, 'description': 'video overlay voice music original sfx'},
                                                      'ids': {'type': 'array', 'items': {'type': 'string'}}}}},
    {'name': 'update_clips',
     'description': 'Apply clip edits atomically (all or nothing) to timeline.json. Ops, in order:\n'
                    '{"op":"move","id":"X012","start":812.4} or {"op":"move","id":"X012","delta":-0.25}  (keeps length)\n'
                    '{"op":"trim","id":"V101","start":400.0,"end":404.5,"roll":true}  (roll: touching video neighbour follows)\n'
                    '{"op":"split","id":"V101","t":402.0}\n'
                    '{"op":"set","id":"X012","fields":{"gain_db":-6,"mute":true,"props":{...},"src":"media/x.jpg"}}  (null deletes a field)\n'
                    '{"op":"add","track":"sfx","clip":{"src":"../../assets/sfx/x.mp3","start":10,"end":12,"gain_db":-12}}\n'
                    '{"op":"delete","id":"X012"}   {"op":"fx","fields":{"subtitles":true}}\n'
                    '{"op":"insert","src":"media/import/x.jpg","t":120.0,"dur":5}  (new shot on the video track, cuts the shot under it)\n'
                    '{"op":"add_track","kind":"fx"}  then {"op":"add","track":"fx","clip":{"type":"old_film","start":10,"end":30,'
                    '"params":{"grain":0.5,"scratches":0.4},"opacity":1,"fade_in":0.5,"fade_out":0.5}}  (effect layer; see effect_catalog)\n'
                    '{"op":"subtitle","key":"1399566","text":"...","start":1399.6,"end":1401.8} edits one burned-in cue (key = original '
                    'start in ms, see get_timeline subtitle_cues; "text":"" hides it, "reset":true restores voice.srt)\n'
                    '{"op":"subtitle_style","fields":{"size":50,"y":0.86,"upper":true,"box":0.6,"box_color":"#000000","box_pad":16,'
                    '"box_radius":8,"stroke":3,"stroke_color":"#0A0908","shadow":1}}  {"op":"track","id":"fx","fields":{"hidden":true}}\n'
                    'Per video clip: "color" {exposure,brightness,contrast,saturation,temperature,tint,gamma,shadows,highlights,fade,sepia}, '
                    '"motion" {"type":"custom","from":{"zoom":1,"x":0.5,"y":0.5},"to":{...},"ease":"smooth","shake":0}, '
                    '"transition_in" {"type":"fade|dip|circle_open|...","dur":0.6}. Overlay type "text" props: text,x,y,size,font,color,'
                    'align,stroke,shadow,box,box_color,anim,upper.\n'
                    'Moved clips are re-anchored to the nearest word/sentence edge so voice changes still retime them. The voice '
                    'track is read-only. Times snap to frames. Returns the new etag, whether the edit is audio-only (fast export) '
                    'or picture (those ranges re-render), and the picture-dirty ranges.',
     'inputSchema': {'type': 'object', 'required': ['ops'], 'properties': {
         'project': PROJ, 'ops': {'type': 'array', 'items': {'type': 'object'}},
         'if_match': {'type': 'string', 'description': 'etag from get_timeline; the edit fails if the user changed the timeline since'},
         'why': {'type': 'string', 'description': 'Short reason, shown in the studio history'}}}},
    {'name': 'list_review_notes',
     'description': "The user's review notes (press C in the studio, box on the frame, text). Each note has t (s), rect "
                    '[x,y,w,h] as fractions of the frame, text, status open|doing|done, and what is on screen and heard at t.',
     'inputSchema': {'type': 'object', 'properties': {'project': PROJ, 'status': {'type': 'string', 'enum': ['open', 'doing', 'done', 'all']}}}},
    {'name': 'set_note_status',
     'description': 'Set a review note to doing (working on it) or done, with an optional reply the user sees under the note. '
                    'Per docs/SCHEMA.md only the user closes notes as done after looking, unless they said otherwise: '
                    'normally set doing + reply.',
     'inputSchema': {'type': 'object', 'required': ['id', 'status'], 'properties': {
         'project': PROJ, 'id': {'type': 'string'}, 'status': {'type': 'string', 'enum': ['open', 'doing', 'done']}, 'reply': {'type': 'string'}}}},
    {'name': 'render_preview',
     'description': 'Render a short MP4 (max 180 s) of [t0, t1] from the current timeline: frames are rendered only where the '
                    'picture changed (mode auto), else cut from render/picture.mp4; the audio is re-mixed for the window. '
                    'Waits for it (about 5 frames/s when frames are rendered) and returns the file path and loudness. The '
                    'user can also play it in the studio (Bản dựng tab).',
     'inputSchema': {'type': 'object', 'required': ['t0', 't1'], 'properties': {
         'project': PROJ, 't0': {'type': 'number'}, 't1': {'type': 'number'}, 'mode': {'type': 'string', 'enum': ['auto', 'frames', 'fast', 'cut'], 'description': 'fast = draw every other frame (quick look)'},
         'wait_s': {'type': 'number', 'description': 'max seconds to wait (default 900)'}}}},
    {'name': 'render_frame',
     'description': 'One frame at t exactly as the final render draws it (photo + Ken Burns + overlays + subtitle + grain), '
                    'returned as an image so you can check a fix. Also saved under render/studio/frames/.',
     'inputSchema': {'type': 'object', 'required': ['t'], 'properties': {'project': PROJ, 't': {'type': 'number'},
                                                                          'width': {'type': 'number', 'description': 'default 960'}}}},
    {'name': 'export',
     'description': 'Start the export in the background: re-render only the picture ranges that changed (spliced into '
                    'render/picture.mp4), the same voice-led mix (-14 LUFS) and mux as doc.py build, to a NEW file '
                    'output/<id>/video-studio-<time>.mp4 (video.mp4 is never overwritten). Audio-only edits take ~7 min '
                    'for a 65-min film. Only export when the user asked for it. Returns a job id for get_job.',
     'inputSchema': {'type': 'object', 'properties': {'project': PROJ}}},
    {'name': 'effect_catalog',
     'description': 'Every effect type with default params and ranges, blend modes, transitions, motion presets, colour '
                    'defaults/presets, text/subtitle defaults and the overlay media available (assets/overlays, media/import). '
                    'Use before adding effects, colour or motion with update_clips.',
     'inputSchema': {'type': 'object', 'properties': {'project': PROJ}}},
    {'name': 'get_job',
     'description': 'Status, progress, log tail and result of a studio job (preview or export). Without id: the latest jobs.',
     'inputSchema': {'type': 'object', 'properties': {'project': PROJ, 'id': {'type': 'string'}}}},
]

_projects = {}


def project(args):
    pid = args.get('project') or C.last_project()
    if not pid:
        raise C.OpError(f'no project given and the studio has not opened one yet; projects: {C.projects()}')
    if pid not in _projects:
        _projects[pid] = C.open_project(pid)
    return _projects[pid]


def slim(c, keep_need=False):
    out = {k: v for k, v in c.items() if k != 'frame' and (keep_need or k != 'need')}
    if 'need' in c and not keep_need:
        out['need'] = c['need'][:120]
    return out


def get_timeline(a):
    proj = project(a); tl, tag = proj.read()
    if a.get('ids'):
        want = set(a['ids'])
        return {'etag': tag, 'clips': [dict(slim(c, True), track=tr['id']) for tr in tl['tracks'] for c in tr['clips'] if c.get('id') in want]}
    if a.get('t0') is None:
        return {'etag': tag, 'id': tl['id'], 'title': tl.get('title'), 'fps': tl['fps'], 'duration': tl['duration'], 'language': tl.get('language'),
                'fx': tl.get('fx'), 'loudness': tl.get('loudness'),
                'tracks': [{'id': tr['id'], 'clips': len(tr['clips'])} for tr in tl['tracks']],
                'markers': tl.get('markers', []), 'open_notes': [n for n in tl.get('review_notes', []) if n.get('status') != 'done'],
                'picture_dirty': C.dirty_ranges(proj, tl),
                'hint': 'pass t0/t1 (seconds) to list the clips in a window'}
    t0, t1 = float(a['t0']), float(a.get('t1', a['t0'] + 30))
    tracks = set(a.get('tracks') or [tr['id'] for tr in tl['tracks']])
    out = {'etag': tag, 'window': [t0, t1], 'tracks': {}}
    for tr in tl['tracks']:
        if tr['id'] not in tracks:
            continue
        cs = [c for c in tr['clips'] if 'start' in c and c['start'] < t1 and c.get('end', c['start']) > t0]
        if tr['id'] == 'voice':
            cs = [{k: c[k] for k in ('id', 'start', 'end', 'text') if k in c} for c in cs]
            out['subtitle_cues'] = [c for c in C.subtitle_cues(proj, tl) if c['start'] < t1 and c['end'] > t0]
        else:
            cs = [slim(c) for c in cs]
        out['tracks'][tr['id']] = cs
    return out


def update_clips(a):
    proj = project(a); before = {}
    def fn(tl):
        before['tl'] = json.loads(json.dumps(tl))
        return C.apply_ops(tl, a['ops'], proj.anchors())
    log, tag = proj.transact(fn, a.get('if_match'), who='agent', why=a.get('why') or '; '.join(f"{o.get('op')} {o.get('id', o.get('track', ''))}" for o in a['ops']))
    tl, _ = proj.read()
    kind = C.edit_kind(before['tl'], tl)
    return {'etag': tag, 'changes': log, 'kind': kind,
            'note': {'audio': 'audio-only: export re-mixes and muxes onto the existing picture (fast)',
                     'picture': 'picture changed: render_preview the range to check it; export re-renders only the dirty ranges',
                     None: 'no effective change'}[kind],
            'picture_dirty': C.dirty_ranges(proj, tl)}


def list_review_notes(a):
    proj = project(a); tl, tag = proj.read(); st = a.get('status') or 'open'
    notes = [n for n in tl.get('review_notes', []) if st == 'all' or n.get('status') == st]
    return {'etag': tag, 'notes': [dict(n, context=C.at_time(proj, tl, n['t'])) for n in sorted(notes, key=lambda n: n['t'])]}


def set_note_status(a):
    proj = project(a)
    op = {'op': 'update', 'id': a['id'], 'status': a['status']}
    if a.get('reply'):
        op['reply'] = a['reply']
    note, tag = proj.transact(lambda tl: C.note_ops(tl, op), who='agent', why=f'note {a["id"]} -> {a["status"]}')
    return {'etag': tag, 'note': note}


def render_preview(a):
    proj = project(a)
    jid = C.start_job(proj, 'preview', {'t0': float(a['t0']), 't1': float(a['t1']), 'mode': a.get('mode', 'auto')})
    j = C.wait_job(proj, jid, float(a.get('wait_s', 900)))
    return {k: j.get(k) for k in ('id', 'status', 'result', 'error', 'progress')} | {'log': (j.get('log') or [])[-4:]}


def render_frame(a):
    proj = project(a); tl, tag = proj.read(); t = float(a['t'])
    jpg = C.Framer(proj).jpeg(tl, t, int(a.get('width', 960)), 85)
    p = proj.work / 'frames' / f'frame-{t:09.3f}.jpg'; p.write_bytes(jpg)
    return [{'type': 'image', 'data': base64.b64encode(jpg).decode(), 'mimeType': 'image/jpeg'},
            {'type': 'text', 'text': json.dumps({'t': t, 'etag': tag, 'path': str(p), 'on_screen': C.at_time(proj, tl, t)}, ensure_ascii=False)}]


def export(a):
    proj = project(a)
    if (proj.work / 'export.lock').exists():
        raise C.OpError('an export is already running')
    tl, _ = proj.read(); d = C.dirty_ranges(proj, tl)
    jid = C.start_job(proj, 'export', {})
    return {'job': jid, 'picture': 'full render' if d is None else (f'{len(d)} dirty range(s) re-render' if d else 'reuse picture.mp4 (audio only)'),
            'output': f'output/{proj.id}/video-studio-<time>.mp4', 'next': 'poll get_job with this id'}


def effect_catalog(a):
    proj = project(a); cat = C.catalog()
    cat['overlay_media'] = [f['src'] for f in C.library(proj, 'overlays')]
    return cat


def get_job(a):
    proj = project(a)
    if a.get('id'):
        return C.job(proj, a['id'])
    return {'jobs': [{k: j.get(k) for k in ('id', 'kind', 'status', 'progress', 'error', 'started', 'ended')} for j in C.jobs(proj, 10)]}


HANDLERS = {f.__name__: f for f in (get_timeline, update_clips, list_review_notes, set_note_status, render_preview, render_frame, export,
                                     get_job, effect_catalog)}


def reply(mid, result=None, error=None):
    msg = {'jsonrpc': '2.0', 'id': mid}
    if error:
        msg['error'] = error
    else:
        msg['result'] = result
    sys.stdout.write(json.dumps(msg, ensure_ascii=False) + '\n'); sys.stdout.flush()


def main():
    sys.stdout.reconfigure(encoding='utf-8'); sys.stdin.reconfigure(encoding='utf-8')
    for line in sys.stdin:
        if not line.strip():
            continue
        try:
            msg = json.loads(line)
        except json.JSONDecodeError:
            reply(None, error={'code': -32700, 'message': 'parse error'}); continue
        mid, method, params = msg.get('id'), msg.get('method'), msg.get('params') or {}
        if mid is None:  # notification (initialized, cancelled)
            continue
        if method == 'initialize':
            reply(mid, {'protocolVersion': params.get('protocolVersion', '2025-06-18'), 'capabilities': {'tools': {}},
                        'serverInfo': {'name': 'documentary-studio', 'version': '1.0.0'},
                        'instructions': 'Edit a finished documentary timeline (projects/<id>/timeline.json) while the user reviews '
                                        'it in the studio web UI. Read review notes, fix with update_clips, check with render_frame/'
                                        'render_preview, mark notes doing with a reply. Export only when the user asks.'})
        elif method == 'ping':
            reply(mid, {})
        elif method == 'tools/list':
            reply(mid, {'tools': TOOLS})
        elif method == 'tools/call':
            name, args = params.get('name'), params.get('arguments') or {}
            try:
                if name not in HANDLERS:
                    raise C.OpError(f'unknown tool {name}')
                out = HANDLERS[name](args)
                content = out if isinstance(out, list) else [{'type': 'text', 'text': json.dumps(out, ensure_ascii=False, indent=1)}]
                reply(mid, {'content': content})
            except C.Conflict as e:
                reply(mid, {'content': [{'type': 'text', 'text': f'CONFLICT: the timeline changed (etag now {e.etag}); the user may '
                                                                   f'have edited it in the studio. Read it again and redo the edit.'}], 'isError': True})
            except Exception as e:  # noqa: BLE001 - errors go back to the agent as tool errors
                traceback.print_exc(file=sys.stderr)
                reply(mid, {'content': [{'type': 'text', 'text': f'{type(e).__name__}: {e}'}], 'isError': True})
        else:
            reply(mid, error={'code': -32601, 'message': f'method not found: {method}'})


if __name__ == '__main__':
    main()
