# Measure the watch face: find dial centre, then print how far forward the surface is
# at each distance from the centre (shows where crystal, bezel and case edge are).
# Run after cleanup.py:  "blender app\blender.exe" blender\watch.blend -b -P blender\measure_dial.py
import bpy
from collections import defaultdict

ob = bpy.data.objects["Watch"]
vs = [ob.matrix_world @ v.co for v in ob.data.vertices]
ymin = min(v.y for v in vs)
ymax = max(v.y for v in vs)
print(f"Y range {ymin:.3f} .. {ymax:.3f}")
print(f"X range {min(v.x for v in vs):.3f} .. {max(v.x for v in vs):.3f}")
print(f"Z range {min(v.z for v in vs):.3f} .. {max(v.z for v in vs):.3f}")

# dial centre = centre of the front-most slice
front = [v for v in vs if v.y < ymin + 0.06]
cx = (min(v.x for v in front) + max(v.x for v in front)) / 2
cz = (min(v.z for v in front) + max(v.z for v in front)) / 2
print(f"front slice: {len(front)} verts, centre x={cx:.3f} z={cz:.3f}, "
      f"half-width {(max(v.x for v in front)-min(v.x for v in front))/2:.3f}")

# radial profile, only the front half of the object (ignore the strap loop behind)
bins = defaultdict(list)
for v in vs:
    if v.y > ymin + 0.5:
        continue
    r = ((v.x - cx) ** 2 + (v.z - cz) ** 2) ** 0.5
    bins[round(r / 0.02)].append(v.y)
print(" r      front_y   depth_from_front  count")
for b in sorted(bins):
    if b * 0.02 > 0.8:
        break
    ys = bins[b]
    print(f"{b*0.02:.2f}   {min(ys):.3f}    {min(ys)-ymin:.3f}         {len(ys)}")
