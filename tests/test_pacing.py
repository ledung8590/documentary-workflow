"""Offline tests for narration re-pacing on a synthetic voice (noise bursts = words, zeros = pauses)."""
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import pacing as P

SR = 16000


def voice(spans, total):
    x = np.zeros(int(total * SR), dtype=np.float32)
    rng = np.random.default_rng(1)
    for a, b in spans:
        x[int(a * SR):int(b * SR)] = rng.standard_normal(int(b * SR) - int(a * SR)) * 0.2
    return x


SRT = """1
00:00:00,500 --> 00:00:03,000
The guns opened fire, and the hills shook.

2
00:00:03,900 --> 00:00:05,000
Many were killed.

3
00:00:05,100 --> 00:00:07,000
Then the night fell.
"""
# speech: "...fire," [gap 0.25] "and the hills shook." [gap 0.9] "Many were killed." [gap 0.6] "Then..."
SPANS = [(0.5, 1.6), (1.85, 3.0), (3.9, 5.0), (5.6, 7.0)]


def test_parse_srt():
    cues = P.parse_srt(SRT)
    assert len(cues) == 3 and cues[1]['text'] == 'Many were killed.' and cues[2]['start'] == 5.1


def test_cuts_only_in_silence_and_emotion_pauses():
    x = voice(SPANS, 8.0); cues = P.parse_srt(SRT)
    units, stats = P.analyse(x, SR, cues)
    P.design(units)
    assert [u['text'] for u in units] == ['The guns opened fire, and the hills shook.', 'Many were killed.', 'Then the night fell.']
    for u in units[:-1]:  # cut regions are pure silence in the source
        seg = x[int(u['src_end'] * SR):int((u['src_end'] + u['orig_gap']) * SR)]
        assert not np.any(seg)
    somber = units[1]
    assert somber['emotion'] == 'somber' and somber['pause_after'] > somber['orig_gap']   # lengthened
    assert units[0]['emotion'] == 'hook'


def test_clause_gap_kept_and_rebuild_remap():
    x = voice([(0.5, 1.2), (1.25, 1.6), (1.85, 3.0), (3.9, 5.0), (5.6, 7.0)], 8.0)
    cues = P.parse_srt(SRT.replace('fire, and', 'fire. And'))  # inner sentence end -> inner cut
    units, _ = P.analyse(x, SR, cues)
    P.design(units)
    assert units[0]['text'].endswith('fire.') and units[0]['cut'] == 'inner'
    out, placed = P.rebuild(x, SR, units, 1.0, 1.0, None, None)
    total_speech = sum(u['end'] - u['start'] for u in placed)
    assert abs(total_speech - sum(u['src_end'] - u['src_start'] for u in units)) < 0.01
    # a source time inside unit 3 maps by the same offset as its start
    u = placed[2]
    assert abs(P.remap(u['src_start'] + 0.5, placed) - (u['start'] + 0.5)) < 1e-6
    assert P.remap(0.0, placed) >= 0.0


def test_locked_and_agent_edits_survive():
    x = voice(SPANS, 8.0); cues = P.parse_srt(SRT)
    units, _ = P.analyse(x, SR, cues); P.design(units)
    units[0].update(emotion='dramatic', source='agent'); units[1].update(pause_after=3.0, locked=True)
    again, _ = P.analyse(x, SR, cues); P.design(again, units)
    assert again[0]['emotion'] == 'dramatic' and again[1]['pause_after'] == 3.0
