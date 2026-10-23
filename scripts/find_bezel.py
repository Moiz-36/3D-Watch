# Find the bezel circle (centre + radius in pixels) in the front dial photo, and save a
# check image with the circle drawn on it. Copy the printed numbers into make_dial_texture.py.
# Run: python scripts\find_bezel.py
import os, math, numpy as np
from PIL import Image, ImageDraw

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
src = os.path.join(ROOT, "photos", "clean", "dial-front-4x.png")
img = Image.open(src).convert("RGB")
lum = np.asarray(img).astype(float).mean(axis=2)
h, w = lum.shape

def bright(x, y):
    return 0 <= x < w and 0 <= y < h and lum[y, x] > 100

# Start from a rough guess, then repeat: walk outward from the centre at many angles until
# the black bezel turns into bright steel (bright for 8 px, so white numerals are skipped),
# and fit a circle through those edge points.
cx, cy = w / 2, h / 2
for _ in range(4):
    pts = []
    for deg in range(0, 360, 2):
        t = math.radians(deg)
        for r in range(int(h * 0.38), int(h * 0.58)):
            x, y = int(cx + r * math.cos(t)), int(cy + r * math.sin(t))
            if not (0 <= x < w and 0 <= y < h):
                break
            if lum[y, x] > 120 and all(bright(int(cx + (r + k) * math.cos(t)),
                                              int(cy + (r + k) * math.sin(t))) for k in range(1, 8)):
                pts.append((x, y, r))
                break
    P = np.array(pts, float)
    P = P[np.abs(P[:, 2] - np.median(P[:, 2])) < 25]          # drop crowns / stray hits
    A = np.c_[P[:, 0], P[:, 1], np.ones(len(P))]
    D, E, F = np.linalg.lstsq(A, -(P[:, 0] ** 2 + P[:, 1] ** 2), rcond=None)[0]
    cx, cy = -D / 2, -E / 2
    r = math.sqrt(cx ** 2 + cy ** 2 - F)
print(f"image {w}x{h}  bezel centre=({cx:.0f},{cy:.0f})  radius={r:.0f}px")

d = ImageDraw.Draw(img)
d.ellipse([cx - r, cy - r, cx + r, cy + r], outline=(255, 0, 0), width=4)
out = os.path.join(ROOT, "blender", "previews", "bezel-check.png")
img.resize((w // 2, h // 2)).save(out)
print("check image:", out)
