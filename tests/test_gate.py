"""Offline tests for the workflow gate (scripts/gate.py): made-up timelines, no rendering, no API."""
import json, sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import gate as G


def tl_of(video, overlay=(), sfx=(), music=(), voice=(), fx=(), silent=False, **top):
    sfx = list(sfx) + ([] if silent else [{'id': 'X0', 'start': 0.0, 'end': 0.6, 'src': 'hit.mp3'}])  # films open on an SFX, not on music
    return {'duration': 30.0, 'credits': [], **top, 'tracks': [
        {'id': 'video', 'clips': list(video)}, {'id': 'overlay', 'clips': list(overlay)}, {'id': 'sfx', 'clips': list(sfx)},
        {'id': 'music', 'clips': list(music)}, {'id': 'voice', 'clips': list(voice)}, {'id': 'fx', 'clips': list(fx)}]}


def v(i, a, b, src, **kw):
    return {'id': f'V{i}', 'start': a, 'end': b, 'src': src, 'in': 0.0, **kw}


def project(tmp_path, tl, files=('a.jpg', 'b.jpg', 'c.jpg', 'film.mp4', 'scene-x.mp4', 'map-y.mp4', 'm.mp3', 'hit.mp3', 'typewriter.mp3')):
    d = tmp_path / 'p'; d.mkdir(exist_ok=True)
    for f in files:
        (d / f).write_bytes(b'x')
    (d / 'brief.json').write_text('{}', encoding='utf-8')
    (d / 'timeline.json').write_text(json.dumps(tl), encoding='utf-8')
    return d


def ids(d, tl, story=False):
    return {f[1]: f[0] for f in G.timeline_checks(d, tl, story)}


def test_clean_timeline_has_no_findings(tmp_path):
    tl = tl_of([v(1, 0, 12, 'a.jpg'), v(2, 12, 20, 'film.mp4'), v(3, 20, 30, 'b.jpg')])
    assert ids(project(tmp_path, tl), tl) == {}
    tl = tl_of([v(1, 0, 5, 'a.jpg'), v(2, 5, 10, 'film.mp4'), v(3, 10, 30, 'b.jpg')])
    assert ids(project(tmp_path, tl), tl) == {'open-cut-silent:V2': '!'}  # an opening film cut with no sound of its own: look


def test_same_picture_twice_blocks_and_touching_clips_do_not(tmp_path):
    tl = tl_of([v(1, 0, 5, 'a.jpg'), v(2, 5, 10, 'a.jpg'), v(3, 10, 20, 'b.jpg'), v(4, 20, 30, 'c.jpg')])
    assert ids(project(tmp_path, tl), tl) == {}  # one picture cut in two touching clips is one appearance
    tl = tl_of([v(1, 0, 10, 'a.jpg'), v(2, 10, 20, 'b.jpg'), v(3, 20, 30, 'a.jpg')])
    assert ids(project(tmp_path, tl), tl) == {'repeat:a.jpg': '!!'}


def test_photo_inside_a_scene_counts_as_shown(tmp_path):
    tl = tl_of([v(1, 0, 10, 'a.jpg'), v(2, 10, 20, 'scene-x.mp4', uses=['a.jpg'], hide_subtitles=True), v(3, 20, 30, 'b.jpg')])
    assert ids(project(tmp_path, tl), tl) == {}  # touching
    tl = tl_of([v(1, 0, 8, 'a.jpg'), v(2, 8, 20, 'b.jpg'), v(3, 20, 30, 'scene-x.mp4', uses=['a.jpg'], hide_subtitles=True)])
    assert ids(project(tmp_path, tl), tl) == {'repeat:a.jpg': '!!'}


def test_film_same_seconds_repeat_other_seconds_do_not(tmp_path):
    tl = tl_of([v(0, 0, 12, 'b.jpg'), v(1, 12, 16, 'film.mp4', **{'in': 0.0}), v(2, 16, 20, 'a.jpg'), v(3, 20, 30, 'film.mp4', **{'in': 40.0})])
    assert ids(project(tmp_path, tl), tl) == {}
    tl = tl_of([v(0, 0, 12, 'b.jpg'), v(1, 12, 16, 'film.mp4', **{'in': 5.0}), v(2, 16, 20, 'film.mp4', **{'in': 5.0}), v(3, 20, 30, 'a.jpg')])
    assert ids(project(tmp_path, tl), tl) == {'repeat:film.mp4': '!!'}  # the replay right after the cut (a real draft had four)


def test_scene_back_after_gap(tmp_path):
    s = lambda i, a, b: v(i, a, b, 'scene-x.mp4', hide_subtitles=True)  # noqa: E731
    tl = tl_of([s(1, 0, 6), v(2, 6, 12, 'a.jpg'), s(3, 12, 30)])
    assert ids(project(tmp_path, tl), tl) == {}  # continues after a short inserted cut
    tl = tl_of([s(1, 0, 6), v(2, 6, 18, 'a.jpg'), s(3, 18, 30)])
    assert ids(project(tmp_path, tl), tl) == {'return:scene-x.mp4': '!!'}


def test_holes_missing_files_and_silent_opening(tmp_path):
    tl = tl_of([v(1, 0, 10, 'a.jpg'), v(2, 12, 30, 'gone.jpg')], silent=True)
    got = ids(project(tmp_path, tl), tl)
    assert got == {'missing:gone.jpg': '!!', 'hole:10.0': '!!', 'silent-open': '!!'}
    assert ids(project(tmp_path, tl), tl, story=True)['hole:10.0'] == '!'  # a story may open on black


def test_cards_tags_subscribe(tmp_path):
    ov = [{'id': 'O1', 'type': 'quote', 'start': 2.0, 'end': 8.0, 'props': {'text': 'x'}},
          {'id': 'O2', 'type': 'chapter', 'start': 12.0, 'end': 15.0, 'props': {}},
          {'id': 'O3', 'type': 'date_tag', 'start': 21.0, 'end': 24.0, 'props': {'text': '1941'}}]
    vid = [v(1, 0, 10, 'a.jpg'), v(2, 10, 20, 'b.jpg'), v(3, 20, 30, 'map-y.mp4', hide_subtitles=True)]
    voice = [{'id': 'S001', 'start': 25.0, 'end': 28.0, 'text': 'Please subscribe to the channel.'}]
    tl = tl_of(vid, overlay=ov, voice=voice)
    assert ids(project(tmp_path, tl), tl) == {'quote-silent:O1': '!!', 'card-silent:O2': '!!', 'tag-on-scene:O3': '!!', 'subscribe:S001': '!!'}
    sfx = [{'id': 'X1', 'start': 2.7, 'end': 7.0, 'src': 'typewriter.mp3'}, {'id': 'X2', 'start': 12.0, 'end': 13.0, 'src': 'hit.mp3'}]
    fx = [{'id': 'F1', 'type': 'media_overlay', 'start': 26.0, 'end': 29.0, 'params': {'src': 'scene-x.mp4'.replace('x', 'subscribe')}}]
    ov[2]['end'] = 20.2
    tl = tl_of(vid, overlay=ov, voice=voice, sfx=sfx, fx=fx)
    d = project(tmp_path, tl); (d / 'scene-subscribe.mp4').write_bytes(b'x')
    assert ids(d, tl) == {}


def test_sourced_file_needs_credit(tmp_path):
    tl = tl_of([v(1, 0, 30, 'commons-123.jpg')])
    d = project(tmp_path, tl, files=('commons-123.jpg', 'hit.mp3'))
    assert ids(d, tl) == {'credit:commons-123.jpg': '!!'}
    tl['credits'] = [{'file': 'commons-123.jpg', 'line': 'X · CC BY 4.0'}]
    assert ids(d, tl) == {}


def test_story_long_still_and_old_film(tmp_path):
    tl = tl_of([v(1, 0, 9, 'a.jpg'), v(2, 9, 16, 'b.jpg'), v(3, 16, 30, 'film.mp4')])
    assert ids(project(tmp_path, tl), tl, story=True) == {'long-still:V1': '!!', 'old-film': '!!'}


def test_fingerprint_ignores_review_notes_only():
    a = tl_of([v(1, 0, 30, 'a.jpg')], review_notes=[])
    b = json.loads(json.dumps(a)); b['review_notes'] = [{'id': 'N1', 'text': 'x'}]
    c = json.loads(json.dumps(a)); c['tracks'][0]['clips'][0]['end'] = 29.0
    assert G.fingerprint(a) == G.fingerprint(b) != G.fingerprint(c)


def test_gate_records_waives_and_require_follows_the_timeline(tmp_path, monkeypatch):
    monkeypatch.setattr(G, 'run', lambda *a, **k: (0, ''))          # no fontcheck subprocess
    monkeypatch.setattr(G, 'overlay_text', lambda d: [])
    monkeypatch.delenv('DOC_GATE_SKIP', raising=False)
    tl = tl_of([v(1, 0, 10, 'a.jpg'), v(2, 10, 20, 'b.jpg'), v(3, 20, 30, 'a.jpg')])
    d = project(tmp_path, tl)
    ok, _ = G.gate(str(d), 'export', quiet=True)
    assert not ok and json.loads((d / 'gate.json').read_text(encoding='utf-8'))['stages']['export']['fails'] == ['repeat:a.jpg']
    with pytest.raises(SystemExit):
        G.require(str(d), 'export')
    (d / 'gate_ok.txt').write_text('repeat:a.jpg | short\n', encoding='utf-8')  # a waiver needs a real reason
    assert not G.gate(str(d), 'export', quiet=True)[0]
    (d / 'gate_ok.txt').write_text('repeat:a.jpg | the seal returns on purpose as the closing image\n', encoding='utf-8')
    ok, _ = G.gate(str(d), 'export', quiet=True)
    rec = json.loads((d / 'gate.json').read_text(encoding='utf-8'))['stages']['export']
    assert ok and rec['status'] == 'PASS' and list(rec['waived']) == ['repeat:a.jpg']
    G.require(str(d), 'export')  # passes for this timeline
    tl['tracks'][0]['clips'][1]['src'] = 'c.jpg'; (d / 'timeline.json').write_text(json.dumps(tl), encoding='utf-8')
    with pytest.raises(SystemExit):  # an edit after the pass needs a new run
        G.require(str(d), 'export')
    with pytest.raises(SystemExit):  # a stage that never ran
        G.require(str(d), 'studio')
    monkeypatch.setenv('DOC_GATE_SKIP', 'user asked to skip the checks')
    G.require(str(d), 'studio')
    assert json.loads((d / 'gate.json').read_text(encoding='utf-8'))['overrides'][0]['reason'] == 'user asked to skip the checks'


def test_sheet_record_must_be_newer_and_complete(tmp_path):
    import os
    d = tmp_path / 'p'; (d / 'qa').mkdir(parents=True)
    sheets = [d / 'qa' / 'shots-01.jpg', d / 'qa' / 'shots-02.jpg']
    for s in sheets:
        s.write_bytes(b'x'); os.utime(s, (1000, 1000))
    assert G.seen_record(d, sheets, 'sheets-seen.txt', 'shot')  # no record
    rec = d / 'qa' / 'sheets-seen.txt'
    rec.write_text('shots-01.jpg | all 56 frames match their captions\n', encoding='utf-8')
    assert 'shots-02.jpg' in G.seen_record(d, sheets, 'sheets-seen.txt', 'shot')[0][2]  # one sheet without a note
    rec.write_text('shots-01.jpg | all 56 frames match their captions\nshots-02.jpg | V071 caption fixed, rest fine\n', encoding='utf-8')
    assert G.seen_record(d, sheets, 'sheets-seen.txt', 'shot') == []
    os.utime(rec, (500, 500))
    assert G.seen_record(d, sheets, 'sheets-seen.txt', 'shot')  # sheets re-made after the record


def test_template_drift(tmp_path, monkeypatch):
    root = tmp_path; (root / 'templates' / 'archival').mkdir(parents=True); d = root / 'projects' / 'p'; d.mkdir(parents=True)
    monkeypatch.setattr(G, 'ROOT', root)
    (root / 'templates' / 'archival' / 'plan.py').write_text('dollcheck.check(D, sh)\nfilmrepeat.check(D, sh)\n', encoding='utf-8')
    (root / 'templates' / 'archival' / 'gen_sound.py').write_text('QUIETER = 12\n', encoding='utf-8')
    (d / 'plan.py').write_text('dollcheck.check(D, sh)\n', encoding='utf-8')
    (d / 'gen_sound.py').write_text('QUIETER = 12\n', encoding='utf-8')
    assert [f[1] for f in G.template_drift(d)] == ['template:plan.py:filmrepeat.check(']


def test_counter_labels_in_scene_sources(tmp_path, monkeypatch):
    root = tmp_path; (root / 'templates' / 'archival' / 'scenes' / 'src').mkdir(parents=True)
    (root / 'templates' / 'archival' / 'scenes' / 'src' / '_kit.js').write_text('', encoding='utf-8')
    monkeypatch.setattr(G, 'ROOT', root)
    d = root / 'projects' / 'p'; src = d / 'scenes' / 'src'; src.mkdir(parents=True)
    (src / '_kit.js').write_text("L.text('1226', 100, 100)\n// old: 'MỤC 01'\nc.fillStyle = '#0a0f05'\n", encoding='utf-8')
    (src / 'a.js').write_text("K.board(c, L, t, {notes: [{big: '1226', text: 'Nhà Trần lên ngôi'}], img: 'media/p-05.jpg'})\n", encoding='utf-8')
    assert G.scene_labels(d) == []
    (src / '_tran.js').write_text("const tag = 'LUẬN ĐIỂM ' + String(i + 1).padStart(2, '0')\n"
                                  "L.text(`MỤC ${String(n).padStart(2, '0')}`, 80, 90)\nL.text('SƠ ĐỒ 01', 1, 2)\n", encoding='utf-8')
    assert {f[1]: f[0] for f in G.scene_labels(d)} == {'counter-label:_tran.js': '!!', 'own-helper:_tran.js': '!'}


def test_no_background_music_unless_the_brief_asks(tmp_path):
    tl = tl_of([v(1, 0, 30, 'a.jpg')], music=[{'id': 'M1', 'start': 0.0, 'end': 30.0, 'src': 'm.mp3'}])
    d = project(tmp_path, tl)
    assert ids(d, tl) == {'music': '!!'} and ids(d, tl, story=True)['music'] == '!!'
    (d / 'brief.json').write_text('{"music": true, "story": {"music": true, "old_film": false}}', encoding='utf-8')
    assert ids(d, tl) == {} and 'music' not in ids(d, tl, story=True)


def test_chapter_card_clip_is_picture_not_hole(tmp_path):
    ov = [{'id': 'O1', 'type': 'chapter', 'start': 10.0, 'end': 13.3, 'props': {}}]
    sfx = [{'id': 'X1', 'start': 10.0, 'end': 11.0, 'src': 'hit.mp3'}]
    card = {'id': 'V2', 'start': 10.0, 'end': 13.0, 'src': None, 'kind': 'card'}
    vid = [v(1, 0, 10, 'a.jpg'), card, v(3, 13, 30, 'b.jpg')]
    tl = tl_of(vid, overlay=ov, sfx=sfx)
    assert not any(k.startswith('hole') for k in ids(project(tmp_path, tl), tl))
    tl = tl_of(vid, sfx=sfx)  # no card overlay over it: black frames
    assert 'hole:10.0' in ids(project(tmp_path, tl), tl)


def test_board_exhibit_after_short_insert_is_one_appearance(tmp_path):
    vid = [v(1, 0, 10, 'scene-x.mp4', uses=['a.jpg'], hide_subtitles=True), v(2, 10, 13, 'film.mp4'),
           v(3, 13, 20, 'scene-x.mp4', uses=['a.jpg'], hide_subtitles=True), v(4, 20, 30, 'b.jpg')]
    tl = tl_of(vid)
    assert 'repeat:a.jpg' not in ids(project(tmp_path, tl), tl)
    vid[3:] = [v(4, 20, 25, 'b.jpg'), v(5, 25, 30, 'scene-z.mp4', uses=['a.jpg'], hide_subtitles=True)]  # another scene: a real repeat
    tl = tl_of(vid)
    d = project(tmp_path, tl); (d / 'scene-z.mp4').write_bytes(b'x')
    assert ids(d, tl).get('repeat:a.jpg') == '!!'


def test_short_render_is_flagged(tmp_path):
    import subprocess
    d = tmp_path / 'p'; d.mkdir()
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-f', 'lavfi', '-i', 'color=c=white:s=64x36:d=2', '-pix_fmt', 'yuv420p', str(d / 'map-y.mp4')], check=True)
    tl = tl_of([v(1, 0, 5, 'map-y.mp4')])
    assert [f[1] for f in G.short_renders(d, tl)] == ['short-render:map-y.mp4']
    tl = tl_of([v(1, 0, 1.9, 'map-y.mp4')])
    assert G.short_renders(d, tl) == []


def test_unreadable_film_cut_is_flagged(tmp_path):
    d = tmp_path / 'p'; d.mkdir(); (d / 'V1.mp4').write_bytes(b'')
    assert [f[1] for f in G.short_renders(d, tl_of([v(1, 0, 2, 'V1.mp4')]))] == ['bad-media:V1.mp4']


def test_only_changed_shots_are_reviewed_again(tmp_path, monkeypatch):
    import types
    made = []

    def fake_sheets(d, per=56, cols=7, only=None, name='shots'):
        f = Path(d) / 'qa' / f'{name}-01.jpg'; f.write_bytes(b'x'); made.append((name, only)); return [f]
    monkeypatch.setitem(sys.modules, 'reviewcheck', types.SimpleNamespace(sheets=fake_sheets))
    vid = [v(i, i * 3, i * 3 + 3, f'{i}.jpg') for i in range(10)]
    tl = tl_of(vid); d = project(tmp_path, tl); (d / 'qa').mkdir(); (d / 'render').mkdir(); (d / 'render' / 'picture.mp4').write_bytes(b'x')
    state = {}
    assert G.shot_sheets(d, tl, state) and made[-1] == ('shots', None)           # first draft: every shot, record missing
    (d / 'qa' / 'sheets-seen.txt').write_text('shots-01.jpg | all ten frames match their captions\n', encoding='utf-8')
    assert G.shot_sheets(d, tl, state) == [] and len(state['shots_seen']) == 10
    n = len(made)
    assert G.shot_sheets(d, tl, state) == [] and len(made) == n                  # nothing changed: nothing to look at again
    tl['tracks'][0]['clips'][3]['src'] = 'new.jpg'                               # one shot replaced after the review
    got = G.shot_sheets(d, tl, state)
    assert got and got[0][1] == 'seen:delta-seen.txt' and made[-1] == ('delta', {'V3'})
    (d / 'qa' / 'delta-seen.txt').write_text('delta-01.jpg | V3 now shows the supply wagons, caption fits\n', encoding='utf-8')
    assert G.shot_sheets(d, tl, state) == [] and G.shot_sheets(d, tl, state) == []
    tl['look'] = 'dark'                                                          # a film-wide change is a new draft: all shots
    import os, time
    os.utime(d / 'render' / 'picture.mp4', (time.time() + 60, time.time() + 60))  # ... and a new render
    assert G.shot_sheets(d, tl, state) and made[-1] == ('shots', None)


def test_opening_seconds(tmp_path):
    files = ('a.jpg', 'b.jpg', 'c.jpg', 'film.mp4', 'scene-x.mp4', 'scene-r-open.mp4', 'map-y.mp4', 'hit.mp3')
    tail = [v(9, 12, 120, 'c.jpg')]
    voice = [{'id': 'S001', 'start': 0.8, 'end': 9.0, 'text': 'The guns opened fire.'}]
    good = [v(1, 0, 3, 'film.mp4'), v(2, 3, 6, 'a.jpg'), v(3, 6, 9, 'b.jpg'), v(4, 9, 12, 'map-y.mp4', hide_subtitles=True)] + tail
    sfx = [{'id': 'X1', 'start': 0.0, 'end': 3.0, 'src': 'hit.mp3'}]
    tl = tl_of(good, voice=voice, sfx=sfx, duration=120.0); d = project(tmp_path, tl, files=files)
    assert ids(d, tl) == {}
    tl = tl_of([v(1, 0, 3, 'scene-r-open.mp4', hide_subtitles=True)] + good[1:], voice=voice, duration=120.0)
    assert ids(d, tl) == {}                                    # a reconstruction print may open a film with no real picture
    slow = [v(1, 0, 7.3, 'scene-x.mp4', hide_subtitles=True), v(2, 7.3, 12, 'film.mp4')] + tail   # film 126
    late = [{'id': 'S001', 'start': 2.6, 'end': 9.0, 'text': 'The guns opened fire.'}]
    tl = tl_of(slow, voice=late, sfx=[{'id': 'X1', 'start': 7.3, 'end': 9.0, 'src': 'hit.mp3'}], duration=120.0)
    assert ids(d, tl) == {'open-graphic': '!!', 'open-long': '!!', 'open-slow': '!!', 'open-voice': '!!'}
    assert 'open-long' not in ids(d, tl, story=True)           # stories open on black with their notice


def test_thumbnail_layout_repeat(tmp_path):
    from PIL import Image, ImageDraw
    import thumbrepeat as T

    def draw(name, red_box, text_box, dark_box, seed):
        im = Image.new('RGB', (1280, 720), (150 + seed, 150, 150)); d = ImageDraw.Draw(im)
        d.rectangle(dark_box, fill=(10, 10, 12)); d.rectangle(red_box, fill=(210, 40, 36))
        for k in range(text_box[0], text_box[2], 26):   # white strokes: lettering
            d.rectangle((k, text_box[1], k + 12, text_box[3]), fill=(255, 255, 255))
        f = tmp_path / name; im.save(f, quality=92); return T.maps(f)
    a = draw('a.jpg', (700, 520, 1240, 690), (760, 200, 1240, 280), (0, 0, 420, 720), 0)
    b = draw('b.jpg', (680, 500, 1230, 680), (780, 210, 1230, 290), (0, 0, 430, 720), 30)   # the same layout, another film
    c = draw('c.jpg', (60, 60, 520, 190), (60, 560, 700, 640), (0, 420, 1280, 720), 10)      # a different layout
    same, red_same = T.similarity(a, b); other, red_other = T.similarity(a, c)
    assert same >= T.HARD and red_same >= T.RED_SAME
    assert other < T.SOFT and red_other < 0.2


def test_thumbnail_stencil_lettering(tmp_path):
    from PIL import Image
    import thumb, thumbcheck
    Image.new('RGB', (1600, 900), (90, 90, 90)).save(tmp_path / 'p.jpg')
    spec = {'layout': 'free', 'lang': 'ja', 'photo': str(tmp_path / 'p.jpg'), 'tag': '1942年4月9日', 'tag_xy': [1250, 650], 'tag_anchor': 'r',
            'lines': [{'text': '空母5隻', 'xy': [44, 40], 'h': 120, 'font': 'stencil', 'maxw': 470}, {'text': '来襲', 'xy': [44, 202], 'h': 120, 'font': 'stencil'}]}
    im = Image.open(thumb.make(dict(spec), tmp_path / 't.jpg'))
    px = list(im.crop((44, 40, 470, 160)).convert('L').getdata())
    assert sum(v > 215 for v in px) > 0.12 * len(px) and sum(v < 30 for v in px) > 0.12 * len(px)   # off-white letters on a black outline
    assert thumbcheck.lettering(spec) == []
    bad = dict(spec, lines=[dict(spec['lines'][0], color='red'), dict(spec['lines'][1], font='sans'), {'text': '退却', 'xy': [0, 0], 'h': 72, 'font': 'stencil'}])
    assert len(thumbcheck.lettering(bad)) == 3
    assert len(thumbcheck.lettering(dict(bad, lang='de'))) == 3          # every language (user 2026-11-28)
    de = {'layout': 'free', 'lang': 'de', 'photo': str(tmp_path / 'p.jpg'), 'tag': 'April 1942', 'lines': [{'text': 'FÜNF TRÄGER', 'xy': [40, 60], 'h': 120, 'font': 'stencil'}]}
    assert thumb.make(dict(de), tmp_path / 'de.jpg') and thumbcheck.lettering(de) == []
    assert thumbcheck.lettering({'layout': 'panel', 'title': 'Old'})


def test_free_thumbnail_layout(tmp_path):
    from PIL import Image
    import thumb
    Image.new('RGB', (1600, 900), (120, 120, 120)).save(tmp_path / 'p.jpg')
    spec = {'layout': 'free', 'photo': str(tmp_path / 'p.jpg'), 'tag': 'Meuse-Argonne · 1918', 'tag_xy': [22, 640],
            'shades': [{'box': [700, 0, 1280, 720], 'alpha': 220, 'fade': 'left'}],
            'lines': [{'text': '47 DAYS', 'xy': [1230, 60], 'h': 150, 'font': 'serif', 'align': 'right'},
                      {'text': '26,000 DEAD', 'xy': [1230, 250], 'h': 96, 'box': 'red', 'align': 'right'}]}
    out = thumb.make(spec, tmp_path / 't.jpg')
    im = Image.open(out)
    assert im.size == (1280, 720) and (tmp_path / 't.json').exists()
    assert im.getpixel((1000, 300))[0] > 150 and im.getpixel((1000, 300))[2] < 90     # the red box sits where the spec put it
    assert thumb.make({'photo': str(tmp_path / 'p.jpg'), 'tag': '1918', 'title': 'Old spec'}, tmp_path / 'old.jpg')  # no layout, no lines: still the panel


def test_evidence_cleanup_only_when_whole(tmp_path, monkeypatch):
    import evidence as E
    monkeypatch.setattr(E, 'ROOT', tmp_path)
    proj = tmp_path / 'projects' / 'j'; (proj / 'render').mkdir(parents=True); (proj / 'render' / 'x.bin').write_bytes(b'1')
    (proj / 'thumb').mkdir(); (proj / 'thumb' / 'src.jpg').write_bytes(b'1')
    dst = tmp_path / 'evidence' / 'Film'
    for sub in ('video', 'media', 'sources', 'project'):
        (dst / sub).mkdir(parents=True)
    index = [{'file': 'media/a.jpg'}]
    for f in ('video/Film.mp4', 'video/Film.jpg', 'INDEX.csv', 'README.md', 'project/timeline.json'):
        (dst / f).write_text('x')
    (dst / 'sources' / 's.json').write_text('{}')
    with pytest.raises(SystemExit):                      # the on-screen picture is not in the pack
        E.cleanup(proj, dst, index, 1)
    assert (proj / 'render' / 'x.bin').exists()
    (dst / 'media' / 'a.jpg').write_text('x')
    E.cleanup(proj, dst, index, 1)
    assert not proj.exists() and (dst / 'project' / 'thumb' / 'src.jpg').exists()


def test_no_blast_in_the_first_seconds(tmp_path):
    files = ('a.jpg', 'b.jpg', 'wind_01.mp3', 'shellburst_02.mp3', 'hit.mp3')
    vid = [v(1, 0, 15, 'a.jpg'), v(2, 15, 30, 'b.jpg')]
    calm = [{'id': 'X1', 'start': 0.0, 'end': 6.0, 'src': 'wind_01.mp3'}, {'id': 'X2', 'start': 7.0, 'end': 9.0, 'src': 'shellburst_02.mp3'}]
    tl = tl_of(vid, sfx=calm, silent=True); d = project(tmp_path, tl, files=files)
    assert ids(d, tl) == {}
    loud = [{'id': 'X1', 'start': 0.1, 'end': 2.0, 'src': 'shellburst_02.mp3'}]
    assert ids(d, tl_of(vid, sfx=loud, silent=True)) == {'open-blast:X1': '!!'}
    path = [{'id': 'X1', 'start': 1.3, 'end': 3.0, 'src': '../../assets/sfx/boom/el_01.wav'}]
    assert 'open-blast:X1' in ids(d, tl_of(vid, sfx=path))


def test_voice_unchecked(tmp_path, monkeypatch):
    import json
    import voicecheck as V
    import doc
    d = tmp_path / 'j'; (d / 'voice' / 'clips').mkdir(parents=True)
    sents = [{'id': 'S001', 'text': 'The cruiser turned away from the line.'}, {'id': 'S002', 'text': 'Nobody followed the flagship that night.'}]
    (d / 'sentences.json').write_text(json.dumps({'sentences': sents}), encoding='utf-8')
    (d / 'brief.json').write_text(json.dumps({'voice': {}}), encoding='utf-8')
    for s, r in zip(sents, (0.9, 0.2)):
        (d / 'voice' / 'clips' / f'{s["id"]}-c-aa.wav').write_bytes(b'x')
        (d / 'voice' / 'clips' / f'{s["id"]}-c-aa.json').write_text(json.dumps({'heard_ratio': r}), encoding='utf-8')
    monkeypatch.setattr(doc, 'current_clip', lambda d, s, v: (d / 'voice' / 'clips' / f'{s["id"]}-c-aa.wav', d / 'voice' / 'clips' / f'{s["id"]}-c-aa.json'))
    assert V.open_items(d) == ['S002']
    assert [f[1] for f in G.voice_unchecked(d)] == ['voice-unchecked']
    (d / 'voice' / 'checked.json').write_text(json.dumps({'S002': {'clip': 'S002-c-old.wav', 'verdict': 'ok'}}), encoding='utf-8')
    assert V.open_items(d) == ['S002']                      # the verdict belongs to an older clip
    (d / 'voice' / 'checked.json').write_text(json.dumps({'S002': {'clip': 'S002-c-aa.wav', 'verdict': 'redo'}}), encoding='utf-8')
    assert V.open_items(d) == ['S002']
    (d / 'voice' / 'checked.json').write_text(json.dumps({'S002': {'clip': 'S002-c-aa.wav', 'verdict': 'ok'}}), encoding='utf-8')
    assert V.open_items(d) == [] and G.voice_unchecked(d) == []


def test_voice_cut_slipped_into_the_neighbour():
    import voicecheck as V
    assert 'ends before' in V.edges('数分後、旗艦デ・ロイテルにも魚雷が命中します。', '数分後、旗艦デロイトルにも魚雷が命中。')
    assert 'starts with' in V.edges('デ・ロイテルは激しく燃え上がり、やがて動けなくなりました。', '命中します。デロイトルは激しく燃え上がり、やがて動けなくなりました。')
    assert V.edges('500名を超える乗員が、この艦と共に最期を迎えたとされています。', '五百名を超える乗員がこの艦と共に最期を迎えたとされています。') == ''
    assert V.edges('The cruiser turned away.', 'The cruiser turned away.') == ''


def test_pace_one_scene_over_a_whole_passage():
    """Film 183: 77 shots for 54 minutes passed the gate (pacecheck, 2026-11-26)."""
    import pacecheck as P

    def tl(lengths):
        t, clips = 0.0, []
        for i, n in enumerate(lengths):
            clips.append({'id': f'V{i + 1:03d}', 'start': t, 'end': t + n, 'src': 'media/scene-a.mp4'}); t += n
        return {'duration': t, 'tracks': [{'id': 'video', 'clips': clips}]}

    ids = [i.split(':')[0] for _, i, _ in P.check('.', tl([35] * 20 + [160]), frames=False)]
    assert 'pace-slow' in ids and 'shot-long' in ids
    assert P.check('.', tl([7] * 100), frames=False) == []
    assert [i for _, i, _ in P.check('.', tl([7] * 100 + [45]), frames=False)] == ['shot-long:V101']


def test_scene_moulds_and_placeholders(tmp_path):
    """Film 183, second draft: the pace was met with one diagram repeated 20 times and "S018 moment" placeholders (templatecheck, 2026-11-27)."""
    import templatecheck as T
    src = tmp_path / 'scenes' / 'src'; src.mkdir(parents=True)
    clips, t = [], 0.0

    def add(name, code=None):
        nonlocal t
        if code is not None:
            (src / f'{name}.js').write_text(code, encoding='utf-8')
        clips.append({'id': f'V{len(clips) + 1:03d}', 'start': t, 'end': t + 6, 'src': f'media/{"scene-" if code is not None else ""}{name}.mp4'}); t += 6

    for i in range(12):   # one mould, other words
        add(f'cut-{i}', f'window.SCENE={{duration:{6 + i},draw(c,t,L){{AE.draw(c,t,L,{{"title":"Range {i}","kind":"range"}});}}}};')
    add('real-1')
    add('hold', 'window.SCENE={duration:7,draw(c,t,L){AE.draw(c,t,L,{"title":"S018 時点","labels":["a","b"]});}};')
    for i in range(5):    # own drawings
        add(f'own-{i}', 'window.SCENE={duration:8,draw(c,t,L){' + 'c.fillRect(1,2,3,4);' * (i + 1) + '}};')
    tl = {'duration': t, 'tracks': [{'id': 'video', 'clips': clips}]}
    ids = [i for _, i, _ in T.check(tmp_path, tl)]
    assert ids == ['scene-placeholder:V014', 'scene-mould:V001']
    for i in range(30):   # 30 different drawings in a row and no real picture
        add(f'row-{i}', 'window.SCENE={duration:8,draw(c,t,L){' + 'c.lineTo(1,2);' * (i + 1) + '}};')
    assert 'drawn-run:V014' in [i for _, i, _ in T.check(tmp_path, {'duration': t, 'tracks': [{'id': 'video', 'clips': clips}]})]
    # a timing anchor is not a placeholder; a scene that frames a picture file is not a mould
    (src / 'own-0.js').write_text("window.SCENE={draw(c,t,L){K.at('S311+0'); K.print(c,'media/print-1.jpg');}};", encoding='utf-8')
    assert not [i for _, i, _ in T.check(tmp_path, {'duration': 90, 'tracks': [{'id': 'video', 'clips': clips[14:16]}]})]


def test_scenes_that_are_an_almost_blank_page(tmp_path, monkeypatch):
    """Film 183, third draft: the mould check passed on code that differed in spelling only, 134 of 351 drawn scenes were dots on a line (2026-11-27)."""
    import templatecheck as T
    (tmp_path / 'media').mkdir()
    clips = []
    for i in range(40):
        name = f'scene-{"bare" if i < 10 else "full"}-{i}.mp4'
        (tmp_path / 'media' / name).write_bytes(b'x')
        clips.append({'id': f'V{i + 1:03d}', 'start': i * 6.0, 'end': i * 6.0 + 6, 'src': f'media/{name}'})
    monkeypatch.setattr(T, 'ink', lambda p, at: 0.012 if 'bare' in str(p) else 0.18)
    assert [i for _, i, _ in T.empty(tmp_path, clips)] == ['scene-empty:V001']      # 10 of 40 = 25 %
    assert not T.empty(tmp_path, clips[5:])                                           # 5 of 35 = 14 %
    monkeypatch.setattr(T, 'ink', lambda p, at: None)                                 # frames unreadable: no finding, no crash
    (tmp_path / 'qa' / 'ink.json').unlink()
    assert not T.empty(tmp_path, clips)


def test_story_core_needs_a_verdict_for_the_current_script(tmp_path, monkeypatch):
    import json, storycore as C
    for k, v in (('CORES', tmp_path / 'cores.json'), ('LOG', tmp_path / 'LOG.md'), ('STORE', tmp_path / 'store.json'), ('PROJECTS', False)):
        monkeypatch.setattr(C, k, v)
    rows = ['| # | Title | Opening | Hero | Prop | Twist |', '|---|---|---|---|---|---|', '| 1 | Old Story | a | b | a slip of paper | a bridge blown two hours early |']
    (tmp_path / 'LOG.md').write_text(chr(10).join(rows), encoding='utf-8')
    d = tmp_path / 'p'; (d / 'qa').mkdir(parents=True); (d / 'script.txt').write_text('A story.', encoding='utf-8')
    old = C.earlier()
    assert old == [('Old Story', 'a bridge blown two hours early; a slip of paper')]
    assert [f[1] for f in C.check(d)] == ['story-core']                      # nobody wrote the core
    core = {'script': C.digest(d), 'core': 'a mortar round kills a farm family and the gunner lets two other men carry the blame for weeks', 'same': False, 'against': [C.key(old[0][1])]}
    put = lambda j: (d / 'qa' / 'core.json').write_text(json.dumps(j), encoding='utf-8')
    put(core); assert C.check(d) == []
    put(dict(core, same=True, **{'with': 'Old Story', 'why': 'x'})); assert [f[1] for f in C.check(d)] == ['story-core-same']   # the same device: not voiced
    put(dict(core, against=[])); assert [f[1] for f in C.check(d)] == ['story-core']                                             # a story it was not compared with
    put(core); (d / 'script.txt').write_text('A story, edited.', encoding='utf-8')
    assert [f[1] for f in C.check(d)] == ['story-core']                      # the script changed: the verdict is void
    # a batch check made for exactly this text is taken over, and only newer stories still have to be compared
    C.save(C.STORE, {C.digest(d): {'title': 'T', 'core': core['core'], 'same': False, 'against': core['against']}})
    assert C.check(d) == [] and json.loads((d / 'qa' / 'core.json').read_text(encoding='utf-8'))['adopted']
    C.save(C.CORES, {'Newer Story': 'a field telephone line cut by a village boy and the officer who must name the house'})
    assert 'newer stor' in C.check(d)[0][2]
    assert C.publish(d, 'This Story') and len(C.earlier()) == 3
    # sentence fixes by the workflow keep the verdict; another story does not get it
    words = ' '.join(f'word{i} goes' for i in range(900))
    (d / 'script.txt').write_text(words, encoding='utf-8')
    C.save(C.STORE, {C.digest(d): {'title': 'T', 'core': core['core'], 'same': False, 'against': [C.key(c) for _, c in C.earlier()], 'sig': C.signature(d / 'script.txt')}})
    (d / 'qa' / 'core.json').unlink()
    (d / 'script.txt').write_text(words.replace('word450 goes', 'word450 went quietly').replace('word7 goes', 'word7 ran'), encoding='utf-8')
    assert C.check(d) == [] and 'unchanged' in json.loads((d / 'qa' / 'core.json').read_text(encoding='utf-8'))['adopted']
    (d / 'qa' / 'core.json').unlink()
    (d / 'script.txt').write_text(' '.join(f'other{i} stays' for i in range(900)), encoding='utf-8')
    assert [f[1] for f in C.check(d)] == ['story-core']


def test_story_pictures_that_repeat_an_earlier_story():
    import imagerepeat as R
    names = ['001.png', '002.png', '003.png', '004.png', '005.png']
    best = {'001.png': (0.96, 'C:/ComfyUI/output/zimage_1_00001_.png', 0.65),      # same subject, same arrangement: the picture again
            '002.png': (0.93, 'x.png', 0.0), '003.png': (0.80, 'y.png', 0.0),
            '004.png': (0.968, 'tank-on-earth.png', 0.23),                         # a tank again, framed another way: allowed
            '005.png': (0.98, 'z.png', 0.1)}                                       # CLIP is sure on its own
    own = [(0.96, '003.png', '004.png', 0.7), (0.96, '001.png', '002.png', 0.2), (0.93, '002.png', '003.png', 0.0)]
    got = R.judge(names, best, own)
    assert [f[1] for f in got] == ['image-repeat:005.png', 'image-twin:003.png', 'image-near']
    assert '2 picture(s)' in got[0][2] and '001.png' in got[0][2] and '004.png' not in got[0][2]
    assert '1 pair(s)' in got[1][2] and got[2][0] == '!' and '004.png' in got[2][2]
    assert R.judge(names, {n: (0.85, 'o.png', 0.0) for n in names}, []) == []
