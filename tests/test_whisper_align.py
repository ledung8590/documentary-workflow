"""Whisper alignment (OmniVoice logic) and cutting a chunked AI84 job into sentences. Offline, no Whisper model."""
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import whisper_align as WA

SR = 48000


def test_subtitles_split_like_omnivoice():
    assert WA.split_subtitles('Gạo. Muối. Đèn.') == ['Gạo.', 'Muối.', 'Đèn.']
    long = 'Một tối tháng 9 năm 1969, một người phụ trách tuyến mang tới ba gói giấy bọc vải dầu.'
    parts = WA.split_subtitles(long)
    assert parts == ['Một tối tháng 9 năm 1969,', 'một người phụ trách tuyến mang tới ba', 'gói giấy bọc vải dầu.']  # = OmniVoice
    assert ' '.join(parts) == long


def test_char_times_follow_whisper_even_with_misheard_numbers():
    words = [{'word': w, 'start': i * 0.3, 'end': i * 0.3 + 0.25} for i, w in enumerate('3 giờ 17 phút sáng ngày'.split())]
    t = WA.char_times('Ba giờ mười bảy phút sáng ngày', words)
    assert t[0] == 0.0 and abs(t[-1] - 1.5 - 0.25 * 3 / 4) < 0.05  # 'ngày' last char, inside the last word
    assert all(b >= a for a, b in zip(t, t[1:]))  # monotonic


def test_cue_times_never_overlap():
    cues = WA.cue_times([(0.0, 0.2, 'Gạo.'), (0.3, 0.5, 'Muối.'), (0.6, 2.0, 'Một câu dài hơn nhiều chữ.')])
    assert all(a1 >= b0 for (_, b0, _), (a1, _, _) in zip(cues, cues[1:]))
    assert cues[0][1] - cues[0][0] >= 0.5


def tone(sec, f=220):
    t = np.arange(int(sec * SR)) / SR
    return (0.3 * np.sin(2 * np.pi * f * t) * np.minimum(1, np.minimum(t, sec - t) / 0.01)).astype(np.float32)


def test_cuts_land_in_the_pauses_even_when_predictions_are_off():
    # five "sentences" (tones) with 0.3 s pauses; Whisper's predicted boundaries are off by up to 0.25 s
    parts, bounds, t = [], [], 0.0
    for k, d in enumerate((1.2, 0.35, 0.4, 0.35, 1.5)):  # three one-word sentences in the middle
        parts.append(tone(d, 200 + 40 * k)); t += d
        if k < 4:
            parts.append(np.zeros(int(0.3 * SR), np.float32)); bounds.append((t, t + 0.3)); t += 0.3
    x = np.concatenate([np.zeros(int(0.2 * SR), np.float32)] + parts)
    bounds = [(a + 0.2, b + 0.2) for a, b in bounds]
    offs = (0.2, -0.25, 0.22, -0.2)
    spans, s = [], 0.2
    for (a, b), o in zip(bounds, offs):
        spans.append((s, (a + b) / 2 + o - 0.01)); s = (a + b) / 2 + o + 0.01
    spans.append((s, len(x) / SR))
    cuts = WA.cut_points(x, SR, spans)
    assert len(cuts) == 4
    for c, (a, b) in zip(cuts, bounds):
        assert a <= c / SR <= b, (c / SR, a, b)
