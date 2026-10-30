"""Offline tests for the studio core: ETag store, clip ops with re-anchoring, picture-dirty ranges, notes, windowed mix graph."""
import json, sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'studio'))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import core as C
import render as R

TIMING = {'S001': {'start': 1.0, 'end': 4.0, 'words': [{'w': 'a', 'start': 1.0}, {'w': 'b', 'start': 2.0}, {'w': 'c', 'start': 3.0}]},
          'S002': {'start': 5.0, 'end': 8.0, 'words': [{'w': 'd', 'start': 5.0}, {'w': 'e', 'start': 6.5}]}}


def make(tmp_path, monkeypatch):
    monkeypatch.setattr(C, 'ROOT', tmp_path)
    d = tmp_path / 'projects' / 'p'; (d / 'voice').mkdir(parents=True); (d / 'render').mkdir()
    (d / 'voice' / 'timing.json').write_text(json.dumps({'sentences': TIMING}), encoding='utf-8')
    tl = {'version': 1, 'id': 'p', 'fps': 24, 'width': 1920, 'height': 1080, 'duration': 10.0, 'review_notes': [], 'markers': [],
          'tracks': [{'id': 'video', 'kind': 'video', 'clips': [
              {'id': 'V1', 'start': 0.0, 'end': 5.0, 'src': 'a.jpg', 'anchor': {'sentence': 'S001', 'edge': 'start', 'offset': -1.0}},
              {'id': 'V2', 'start': 5.0, 'end': 10.0, 'src': 'b.jpg', 'anchor': {'sentence': 'S002', 'edge': 'start'}}]},
                     {'id': 'overlay', 'kind': 'overlay', 'clips': []},
                     {'id': 'voice', 'kind': 'voiceover', 'clips': [{'id': 'S001', 'start': 1.0, 'end': 4.0}]},
                     {'id': 'music', 'kind': 'music', 'clips': []}, {'id': 'original', 'kind': 'original', 'clips': []},
                     {'id': 'sfx', 'kind': 'sfx', 'clips': [{'id': 'X1', 'start': 2.0, 'end': 3.0, 'src': 's.mp3', 'gain_db': -9,
                                                             'anchor': {'sentence': 'S001', 'word': 1, 'offset': 0.0}}]}]}
    (d / 'timeline.json').write_bytes(C.dumps(tl))
    return C.Project('p')


def test_etag_guards_writes(tmp_path, monkeypatch):
    p = make(tmp_path, monkeypatch); tl, tag = p.read()
    tl['title'] = 'agent edit'
    tag2 = p.put(tl, tag, why='agent')
    with pytest.raises(C.Conflict):
        p.put(tl, tag)  # stale etag: the other writer's change must not be overwritten
    assert p.etag() == tag2 and len(p.history()) == 1


def test_move_reanchors_to_nearest_word(tmp_path, monkeypatch):
    p = make(tmp_path, monkeypatch); tl, _ = p.read()
    C.apply_ops(tl, [{'op': 'move', 'id': 'X1', 'start': 3.1}], p.anchors())
    x = C.find(tl, 'X1')[2]
    assert x['start'] == C.T.snap(3.1, 24) and x['end'] == C.T.snap(x['start'] + 1.0, 24)
    assert x['anchor']['sentence'] == 'S001' and x['anchor']['word'] == 2 and abs(x['anchor']['offset'] - (x['start'] - 3.0)) < 1e-6
    timing = json.loads(json.dumps(TIMING)); timing['S001']['words'][2]['start'] = 3.5  # the voice moves: the sfx follows
    C.T.retime(tl, timing)
    assert abs(C.find(tl, 'X1')[2]['start'] - 3.5 - x['anchor']['offset']) < 1 / 24


def test_roll_trim_moves_touching_neighbour(tmp_path, monkeypatch):
    p = make(tmp_path, monkeypatch); tl, _ = p.read()
    C.apply_ops(tl, [{'op': 'trim', 'id': 'V1', 'end': 4.5, 'roll': True}], p.anchors())
    assert C.find(tl, 'V1')[2]['end'] == 4.5 and C.find(tl, 'V2')[2]['start'] == 4.5


def test_split_audio_keeps_source_position(tmp_path, monkeypatch):
    p = make(tmp_path, monkeypatch); tl, _ = p.read()
    C.apply_ops(tl, [{'op': 'split', 'id': 'X1', 't': 2.5}], p.anchors())
    a, b = C.find(tl, 'X1')[2], C.find(tl, 'X1.2')[2]
    assert a['end'] == 2.5 and b['start'] == 2.5 and b['in'] == 0.5 and b['fade_in'] == 0.02


def test_voice_is_read_only_and_ops_are_atomic(tmp_path, monkeypatch):
    p = make(tmp_path, monkeypatch); before = p.read_bytes()
    with pytest.raises(C.OpError):
        p.transact(lambda tl: C.apply_ops(tl, [{'op': 'set', 'id': 'X1', 'fields': {'gain_db': -3}},
                                                {'op': 'move', 'id': 'S001', 'start': 2}], p.anchors()))
    assert p.read_bytes() == before


def test_edit_kind_and_dirty_ranges(tmp_path, monkeypatch):
    p = make(tmp_path, monkeypatch); tl, _ = p.read()
    p.picture.write_bytes(b'x'); C.save_state(p, tl)
    after = json.loads(json.dumps(tl)); C.apply_ops(after, [{'op': 'set', 'id': 'X1', 'fields': {'gain_db': -3}}])
    assert C.edit_kind(tl, after) == 'audio' and C.dirty_ranges(p, after) == []
    C.apply_ops(after, [{'op': 'set', 'id': 'V2', 'fields': {'caption': 'x'}}])
    assert C.edit_kind(tl, after) == 'picture' and C.dirty_ranges(p, after) == [[5.0, 10.0]]


def test_notes(tmp_path, monkeypatch):
    p = make(tmp_path, monkeypatch)
    n, _ = p.transact(lambda tl: C.note_ops(tl, {'op': 'add', 't': 2.0, 'rect': [0.1, 0.1, 0.5, 0.5], 'text': ' too dark '}))
    assert n['id'] == 'N1' and n['status'] == 'open' and n['text'] == 'too dark'
    n, _ = p.transact(lambda tl: C.note_ops(tl, {'op': 'update', 'id': 'N1', 'status': 'doing', 'reply': 'brightened'}))
    assert p.read()[0]['review_notes'][0]['reply'] == 'brightened'
    with pytest.raises(C.OpError):
        C.note_ops(p.read()[0], {'op': 'update', 'id': 'N1', 'status': 'closed'})


def test_window_mix_graph_offsets_clips(tmp_path, monkeypatch):
    p = make(tmp_path, monkeypatch); tl, _ = p.read()
    monkeypatch.setattr(R, '_has_audio', lambda path: True)
    (p.d / 's.mp3').write_bytes(b'')
    ins, fc, n = R.mix_graph(p.d, tl, 2.5, 6.0)
    assert n == 1 and ins[:4] == ['-ss', '2.500', '-t', '3.500']
    assert 'atrim=start=0.5:duration=0.500' in fc[1] and 'adelay=0|0' in fc[1]  # the window starts inside X1
    ins, fc, n = R.mix_graph(p.d, tl, 0.0, 6.0, only={'sfx'})
    assert fc[1] == '[v0]volume=0[v]'  # voice muted for monitoring, still the ducking key


def test_insert_cuts_the_shot_under_it(tmp_path, monkeypatch):
    p = make(tmp_path, monkeypatch); tl, _ = p.read()
    C.apply_ops(tl, [{'op': 'insert', 'src': 'n.jpg', 't': 1.0, 'dur': 2.0}], p.anchors())
    v = sorted(C.track(tl, 'video')['clips'], key=lambda c: c['start'])
    assert [(c['start'], c['end']) for c in v] == [(0.0, 1.0), (1.0, 3.0), (3.0, 5.0), (5.0, 10.0)]
    assert v[1]['src'] == 'n.jpg' and v[1]['motion']['type'] == 'push' and v[2]['src'] == 'a.jpg'


def test_effect_track_is_picture_and_dirty(tmp_path, monkeypatch):
    p = make(tmp_path, monkeypatch); tl, _ = p.read()
    p.picture.write_bytes(b'x'); C.save_state(p, tl)
    after = json.loads(json.dumps(tl))
    C.apply_ops(after, [{'op': 'add_track', 'kind': 'fx'}, {'op': 'add', 'track': 'fx', 'clip': {'type': 'old_film', 'start': 2.0, 'end': 4.0}}], p.anchors())
    assert C.edit_kind(tl, after) == 'picture' and C.dirty_ranges(p, after) == [[2.0, 4.0]]
    C.apply_ops(after, [{'op': 'track', 'id': 'fx', 'fields': {'hidden': True}}])
    assert C.dirty_ranges(p, after) == []  # a hidden effect track is not rendered


def test_transitions_and_neutral_colour():
    import numpy as np
    import render_fx as FX
    a = np.full((FX.H, FX.W, 3), 40, np.uint8); b = np.full((FX.H, FX.W, 3), 200, np.uint8)
    for k in FX.TRANSITIONS:
        assert FX.transition(a, b, k, 0.999).mean() > 150 or k in ('dip', 'dip_white', 'blur', 'pixelize'), k
        assert FX.transition(a, b, k, 0.0).shape == a.shape
    assert FX.apply_color(a, {}) is a and (FX.apply_color(a, {'saturation': 0.0}) == a).all()
