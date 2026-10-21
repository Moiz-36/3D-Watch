# Crop the bezel + dial out of the front photo into a square texture for the 3D face.
# Centre and radius come from scripts/find_bezel.py (checked by eye in bezel-check.png).
# Run: python scripts\make_dial_texture.py
import os
from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CX, CY, R = 1002, 902, 600      # bezel centre and outer radius in front-4x.png (pixels)
SIZE = 1024                     # final texture size (keeps the web model small)

img = Image.open(os.path.join(ROOT, "photos", "clean", "front-4x.png")).convert("RGB")
dial = img.crop((CX - R, CY - R, CX + R, CY + R)).resize((SIZE, SIZE), Image.LANCZOS)
out = os.path.join(ROOT, "photos", "clean", "dial.png")
dial.save(out)
print("saved", out)
