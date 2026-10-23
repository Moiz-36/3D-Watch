# Crop the bezel + dial out of the straight-on dial photo (no glare) into a square texture for the 3D face.
# Centre and radius come from scripts/find_bezel.py (checked by eye in bezel-check.png).
# Run: python scripts\make_dial_texture.py
import os
from PIL import Image, ImageEnhance, ImageFilter

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CX, CY, R = 904, 660, 657       # bezel centre and outer radius in dial-front-4x.png (pixels)
SIZE = 2048                     # final texture size (sharp text when zoomed in)

img = Image.open(os.path.join(ROOT, "photos", "clean", "dial-front-4x.png")).convert("RGB")
dial = img.crop((CX - R, CY - R, CX + R, CY + R)).resize((SIZE, SIZE), Image.LANCZOS)
out = os.path.join(ROOT, "photos", "clean", "dial.png")
# crisper markers and numbers: a touch more contrast, then sharpen fine edges
dial = ImageEnhance.Contrast(dial).enhance(1.08)
dial = dial.filter(ImageFilter.UnsharpMask(radius=2, percent=120, threshold=2))
dial.save(out)
print("saved", out)
