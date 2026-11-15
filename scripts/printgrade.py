"""Grade a generated reconstruction like the 通史3 prints: luminance mapped onto a dark-indigo -> aged-tan ramp, a little
contrast, print grain and a soft vignette. PY scripts/printgrade.py in.png out.jpg  (Z-Image prints for "Reconstruction (generated)" scenes, docs/WORKFLOW.md stage 6)"""
import sys
import numpy as np
from PIL import Image, ImageFilter
im = Image.open(sys.argv[1]).convert('RGB').resize((1920, 1080), Image.LANCZOS)
a = np.asarray(im, dtype=np.float32) / 255
l = (0.3 * a[..., 0] + 0.55 * a[..., 1] + 0.15 * a[..., 2])
l = np.clip((l - 0.06) / 0.9, 0, 1) ** 1.12                       # deeper shadows, keep paper light
dark, mid, light = np.array([24, 38, 66]), np.array([104, 112, 122]), np.array([230, 208, 166])
t = l[..., None]
rgb = np.where(t < 0.42, dark + (mid - dark) * (t / 0.42), mid + (light - mid) * np.clip((t - 0.42) / 0.58, 0, 1) ** 0.8)
rng = np.random.default_rng(7); g = rng.normal(0, 5, l.shape)[..., None]
yy, xx = np.mgrid[0:1080, 0:1920]; v = 1 - 0.28 * (((xx - 960) / 1100) ** 2 + ((yy - 540) / 700) ** 2)
out = np.clip(rgb * v[..., None] + g, 0, 255).astype(np.uint8)
Image.fromarray(out).filter(ImageFilter.UnsharpMask(1.2, 40, 2)).save(sys.argv[2], quality=93)
