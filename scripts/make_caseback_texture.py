# Turn the angled caseback photo into a flat, round texture for the back of the 3D case.
# The caseback has 6 notches spaced evenly (every 60 degrees). Their positions in the photo
# tell us how the circle was tilted, so a perspective warp makes it round again.
# Run: python scripts\make_caseback_texture.py
import os, math
import numpy as np
from PIL import Image, ImageEnhance, ImageFilter

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "photos", "clean", "caseback-engraved-4x.png")
OUT = os.path.join(ROOT, "photos", "clean", "caseback.png")
SIZE = 2048
EDGE = 1.12          # texture edge radius / notch-ring radius (caseback rim sits just outside)

# Notch centres in caseback-engraved-4x.png (pixels), clockwise from the top, picked by eye.
NOTCHES = [(1123, 292), (1471, 539), (1481, 937), (1098, 1100), (736, 832), (761, 421)]
CROWN = (676, 1030)  # the crown, used to turn the image so the crown sits at 9 o'clock

def homography(src, dst):
    """3x3 matrix H with dst ~ H @ src (least squares over all point pairs)."""
    rows = []
    for (x, y), (u, v) in zip(src, dst):
        rows.append([x, y, 1, 0, 0, 0, -u * x, -u * y, -u])
        rows.append([0, 0, 0, x, y, 1, -v * x, -v * y, -v])
    h = np.linalg.svd(np.array(rows, float))[2][-1]
    return h.reshape(3, 3) / h[-1]

def apply(H, p):
    q = H @ np.array([p[0], p[1], 1.0])
    return q[:2] / q[2]

c, ring = SIZE / 2, SIZE / 2 / EDGE

def targets(rot):
    # image y points down, so clockwise in the photo = increasing angle here
    return [(c + ring * math.cos(math.radians(-90 + 60 * i + rot)),
             c + ring * math.sin(math.radians(-90 + 60 * i + rot))) for i in range(6)]

# first pass: find where the crown lands, then rotate so it points left (9 o'clock)
H = homography(NOTCHES, targets(0))
cx, cy = apply(H, CROWN)
rot = 180 - math.degrees(math.atan2(cy - c, cx - c))
# snap to the notch grid isn't needed; just rotate the notch targets by that angle
Hinv = homography(targets(rot), NOTCHES)          # output pixel -> photo pixel

img = Image.open(SRC).convert("RGB")
flat = img.transform((SIZE, SIZE), Image.PERSPECTIVE, tuple(Hinv.flatten()[:8]), Image.BICUBIC)
flat = ImageEnhance.Contrast(flat).enhance(1.1)
flat = flat.filter(ImageFilter.UnsharpMask(radius=2, percent=100, threshold=2))
flat.save(OUT)
print(f"rotated {rot:.0f} deg so the crown is at 9 o'clock; saved {OUT}")
