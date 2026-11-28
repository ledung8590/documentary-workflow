"""render.video_vf is shared by the export (render.Video) and the studio preview (core._video_frame): film 129."""
import sys
from pathlib import Path

sys.path[:0] = [str(Path(__file__).resolve().parents[1] / 'scripts')]
import render  # noqa: E402


def test_fill_by_default():
    assert render.video_vf(1920, 1080, {}).startswith('scale=1920:1080:force_original_aspect_ratio=increase')


def test_fit_shows_the_whole_frame():
    vf = render.video_vf(400, 300, {'fit': True})
    assert 'force_original_aspect_ratio=decrease' in vf and 'pad=' in vf


def test_zoom_and_centre_crop_come_first():
    vf = render.video_vf(1920, 1080, {'zoom': 1.2, 'crop_center': 1.34})
    assert vf.startswith('crop=iw/1.34:ih/1.34,crop=iw/1.2:ih/1.2:iw-iw/1.2:ih-ih/1.2,')


def test_studio_preview_uses_the_shared_filter():
    src = (Path(__file__).resolve().parents[1] / 'studio' / 'core.py').read_text(encoding='utf-8')
    assert 'R.video_vf(' in src


def test_exhibit_caption_fits_the_frame():
    from PIL import Image, ImageDraw
    d = ImageDraw.Draw(Image.new('RGB', (10, 10)))
    long = 'The sail of USS George Washington (SSBN-598) at the Submarine Force Museum, Groton, Connecticut, with its memorial stone and the Thames River behind it'
    lines = render.exhibit_caption_lines(d, long, render.W - 160)
    assert 1 <= len(lines) <= 2 and all(d.textlength(t, font=f) <= render.W - 160 for t, f in lines)
    assert render.exhibit_caption_lines(d, 'Short caption', 1000)[0][0] == 'Short caption'
