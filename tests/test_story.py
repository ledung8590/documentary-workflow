"""Story mode (docs/STORY_MODE.md): input discovery, prompt files, image placement on the new voice. Offline."""
import json, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import story as ST


def images(d, n):
    from PIL import Image
    d.mkdir(parents=True, exist_ok=True)
    for k in range(1, n + 1):
        Image.new('RGB', (64, 36)).save(d / f'{k:03d}.png')


def test_discover_both_layouts(tmp_path):
    images(tmp_path / 'Tale A', 3)
    (tmp_path / 'Tale A.txt').write_text('Once.', encoding='utf-8')
    (tmp_path / 'Tale A_3 scene.txt').write_text('{"scenes 1": "a"}\n{"scenes 2": "b"}\n{"scenes 3": "c"}\n', encoding='utf-8')
    images(tmp_path / 'Tale B', 4)
    (tmp_path / 'Tale B' / 'script.txt').write_text('Twice.', encoding='utf-8')
    (tmp_path / 'Tale B' / 'prompts.txt').write_text('x\ny\n', encoding='utf-8')
    images(tmp_path / '_done', 5)
    jobs = {j['name']: j for j in ST.discover(tmp_path)}
    assert set(jobs) == {'Tale A', 'Tale B'}  # '_done' is skipped
    assert jobs['Tale A']['script'].name == 'Tale A.txt' and jobs['Tale A']['prompts'].name == 'Tale A_3 scene.txt'
    assert jobs['Tale B']['script'].name == 'script.txt' and jobs['Tale B']['count'] == 4
    assert ST.load_prompts(jobs['Tale A']['prompts']) == {1: 'a', 2: 'b', 3: 'c'}
    assert ST.load_prompts(jobs['Tale B']['prompts']) == {1: 'x', 2: 'y'}


def timing_of(text, rate=0.4):
    """Fake voice timing: one sentence per line, a word every `rate` s."""
    out, t = {}, 1.0
    for k, line in enumerate(text.strip().split('\n'), 1):
        ws = [{'w': w, 'start': t + i * rate} for i, w in enumerate(line.split())]
        out[f'S{k:03d}'] = {'start': t, 'end': t + len(ws) * rate, 'words': ws}; t += len(ws) * rate + 1.5
    return out


def test_images_follow_their_srt_text(tmp_path):
    story = 'the keeper climbed the stairs\nthe lamp burned all night long\na ship came close to the rocks\nthe ship turned away at dawn'
    # the images were made for an older, faster reading: 2 s per image, one line each
    srt = tmp_path / 'old.srt'
    srt.write_text(''.join(f'{k}\n00:00:{2 * (k - 1):02d},000 --> 00:00:{2 * k:02d},000\n{line}\n\n'
                           for k, line in enumerate(story.split('\n'), 1)), encoding='utf-8')
    timing = timing_of(story)
    vt, starts = ST.image_starts(4, timing, srt, 2.0)
    assert [vt[i][1:] for i in starts] == [('S001', 0), ('S002', 0), ('S003', 0), ('S004', 0)]


def test_even_spread_is_strictly_increasing():
    timing = timing_of('a b\nc d e\nf')
    vt, starts = ST.image_starts(5, timing)
    assert starts == sorted(set(starts)) and len(starts) == 5
