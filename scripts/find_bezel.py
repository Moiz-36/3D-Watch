# Find the bezel circle (centre + radius in pixels) in the front photo, and save a
# check image with the circle drawn on it.
# Run: python scripts\find_bezel.py
import os, numpy as np
from PIL import Image, ImageDraw

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
src = os.path.join(ROOT, "photos", "clean", "front-4x.png")
img = Image.open(src).convert("RGBA")
a = np.asarray(img).astype(float)
h, w = a.shape[:2]
lum = a[..., :3].mean(axis=2)
dark = (lum < 60) & (a[..., 3] > 128)

# rough centre: the middle of the dark area in the middle rows
rows = range(int(h * 0.35), int(h * 0.55))
pts = []
for y in rows:
    xs = np.where(dark[y])[0]
    if len(xs) < 10:
        continue
    pts.append((xs[0], y)); pts.append((xs[-1], y))
pts = np.array(pts, float)

# least-squares circle fit: x^2 + y^2 + D x + E y + F = 0
A = np.c_[pts[:, 0], pts[:, 1], np.ones(len(pts))]
b = -(pts[:, 0] ** 2 + pts[:, 1] ** 2)
D, E, F = np.linalg.lstsq(A, b, rcond=None)[0]
cx, cy = -D / 2, -E / 2
r = np.sqrt(cx ** 2 + cy ** 2 - F)
print(f"image {w}x{h}  bezel centre=({cx:.0f},{cy:.0f})  radius={r:.0f}px")

chk = img.copy()
d = ImageDraw.Draw(chk)
d.ellipse([cx - r, cy - r, cx + r, cy + r], outline=(255, 0, 0, 255), width=6)
d.line([cx - 30, cy, cx + 30, cy], fill=(255, 0, 0, 255), width=6)
d.line([cx, cy - 30, cx, cy + 30], fill=(255, 0, 0, 255), width=6)
out = os.path.join(ROOT, "blender", "previews", "bezel-check.png")
chk.convert("RGB").resize((w // 3, h // 3)).save(out)
print("check image:", out)
