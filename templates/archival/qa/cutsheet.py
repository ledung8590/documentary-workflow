"""Contact sheets of every film cut (10/50/90 % frames) with id, time and caption: qa/cuts-NN.jpg (8 cuts per sheet)."""
import json, subprocess, io, textwrap
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

D = Path(__file__).resolve().parents[1]
tl = json.loads((D / 'timeline.json').read_text(encoding='utf-8'))
cl = [c for t in tl['tracks'] if t['id'] == 'video' for c in t['clips'] if c.get('kind') == 'video' and Path(c.get('src', '')).name.startswith('V')]
font = ImageFont.truetype('C:/Windows/Fonts/arial.ttf', 16)
W, H = 320, 180


def frame(src, t):
    r = subprocess.run(['ffmpeg', '-v', 'error', '-ss', f'{t:.2f}', '-i', str(D / src), '-frames:v', '1', '-vf', f'scale={W}:{H}',
                        '-f', 'image2pipe', '-vcodec', 'png', '-'], capture_output=True)
    try:
        return Image.open(io.BytesIO(r.stdout)).convert('RGB')
    except Exception:
        return Image.new('RGB', (W, H), (90, 0, 0))


per = 8
for n in range(0, len(cl), per):
    sheet = Image.new('RGB', (W * 3 + 420, (H + 6) * per), (20, 20, 20)); dr = ImageDraw.Draw(sheet)
    for i, c in enumerate(cl[n:n + per]):
        d = c['end'] - c['start']; s0 = c.get('in', 0) or 0
        for j, f in enumerate((0.1, 0.5, 0.9)):
            sheet.paste(frame(c['src'], s0 + d * f), (j * W, i * (H + 6)))
        txt = f"{c['id']}  {int(c['start'] // 60)}:{c['start'] % 60:04.1f}  {d:.1f}s\n" + '\n'.join(textwrap.wrap(c.get('caption', ''), 44))
        dr.text((W * 3 + 8, i * (H + 6) + 6), txt, fill=(240, 240, 240), font=font)
    sheet.save(D / 'qa' / f'cuts-{n // per + 1:02d}.jpg', quality=82)
print(len(cl), 'cuts,', (len(cl) + per - 1) // per, 'sheets')
