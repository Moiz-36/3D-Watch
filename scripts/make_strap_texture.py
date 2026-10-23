# Generate a seamless black canvas fabric texture for the strap (matches the clasp photo):
# a colour map and a normal map (bumps that catch the light). No photo needed.
# Run: python scripts\make_strap_texture.py
import os
import numpy as np
from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "blender", "textures")
N = 1024
rng = np.random.default_rng(7)

u, v = np.meshgrid(np.arange(N) / N, np.arange(N) / N)
tau = 2 * np.pi

def tileable_noise(scale):
    """Smooth random noise that wraps around seamlessly (filtered in frequency space)."""
    f = np.fft.fftfreq(N)
    fx, fy = np.meshgrid(f, f)
    spectrum = np.fft.fft2(rng.standard_normal((N, N)))
    spectrum *= np.exp(-(fx ** 2 + fy ** 2) * (N / scale) ** 2)
    n = np.real(np.fft.ifft2(spectrum))
    return (n - n.mean()) / n.std()

# Integer frequencies keep every layer seamless.
RIBS = 26                                                       # diagonal ribs per tile (fine canvas twill)
ribs = np.sin(tau * (RIBS * u + RIBS * v))
weave = np.sin(tau * 90 * u) * np.sin(tau * 90 * v)            # fine cross-weave
threads = np.sin(tau * (RIBS * u + RIBS * v) + 0.3 * tileable_noise(40))  # slight wobble
sharp = np.sign(threads) * np.abs(threads) ** 0.5              # flatter tops, crisp grooves
height = 0.6 * sharp + 0.1 * ribs + 0.22 * weave + 0.1 * tileable_noise(8)
height = (height - height.min()) / (height.max() - height.min())

# colour: black canvas, ribs slightly lighter on top
base = np.array([26, 26, 28], float)
shade = 0.55 + 0.9 * height + 0.05 * tileable_noise(4)
color = np.clip(base[None, None, :] * shade[..., None], 0, 255).astype(np.uint8)

# normal map from height slope (OpenGL / glTF convention: green = up)
strength = 6.0
dx = (np.roll(height, -1, 1) - np.roll(height, 1, 1)) * strength
dy = (np.roll(height, -1, 0) - np.roll(height, 1, 0)) * strength
nz = 1 / np.sqrt(dx ** 2 + dy ** 2 + 1)
normal = np.stack([-dx * nz, dy * nz, nz], -1)
normal = ((normal * 0.5 + 0.5) * 255).astype(np.uint8)

os.makedirs(OUT, exist_ok=True)
Image.fromarray(color).save(os.path.join(OUT, "strap-color.png"))
Image.fromarray(normal).save(os.path.join(OUT, "strap-normal.png"))
print("saved strap-color.png and strap-normal.png in", OUT)
