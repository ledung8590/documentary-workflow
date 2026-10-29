"""Offline tests: sentence split, pause design, anchor retiming. No API calls.  PY -m pytest tests -q"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import sentences as S
import timeline as T


def test_split_keeps_abbreviations_and_numbers():
    sents, _ = S.parse('Gen. Navarre flew in on Nov. 20. The drop took 7.5 hours! Was it worth it?')
    assert [s['text'] for s in sents] == ['Gen. Navarre flew in on Nov. 20.', 'The drop took 7.5 hours!', 'Was it worth it?']


def test_vietnamese_and_directives():
    sents, ch = S.parse('Năm mươi lăm ngày đêm. Ngày 7/5/1954, quân ta cắm cờ trên nóc hầm. [pause 2.5]\n\n'
                        '# Thư khen\n\n{somber} Nhiều người đã hy sinh…')
    S.design_pauses(sents)
    assert len(sents) == 3 and ch[0]['sentence'] == 'S003' and sents[0]['emotion'] == 'hook'
    assert sents[1]['pause_after'] == 2.5 and sents[1]['emotion'] == 'triumphant'
    assert sents[2]['emotion'] == 'somber' and sents[2]['source'] == 'script'


def test_pauses_follow_emotion():
    sents, _ = S.parse('{urgent} They ran. {neutral} They waited for orders. {somber} Many were killed. {neutral} Then night fell.')
    S.design_pauses(sents)
    p = {s['emotion']: s['pause_after'] for s in sents[:-1]}
    assert p['urgent'] < p['neutral'] < p['somber']
    assert sents[-1]['pause_after'] == 0.0
    assert 'chapter' not in sents[0]['pause_why']


def test_chapter_pause_is_long():
    sents, _ = S.parse('It was wrong.\n\n# Part two\n\nThe guns arrived.')
    S.design_pauses(sents)
    assert sents[0]['pause_after'] > 2.5


def test_retime_moves_word_anchored_sfx():
    timing = {'S001': {'start': 2.0, 'end': 4.0, 'words': [{'w': 'the', 'start': 2.0}, {'w': 'guns', 'start': 2.4}]}}
    tl = {'fps': 24, 'tracks': [{'id': 'sfx', 'clips': [{'id': 'X1', 'start': 0, 'end': 1.0,
                                                       'anchor': {'sentence': 'S001', 'word': 1, 'offset': -0.05}}]}]}
    moved, orphan, loose = T.retime(tl, timing)
    c = tl['tracks'][0]['clips'][0]
    assert moved == 1 and not orphan and c['frame'] == round(2.35 * 24) and abs(c['end'] - c['start'] - 1.0) < 0.05
    timing['S001']['words'][1]['start'] = 5.0          # voice regenerated: the word moved
    T.retime(tl, timing)
    assert c['frame'] == round(4.95 * 24)
