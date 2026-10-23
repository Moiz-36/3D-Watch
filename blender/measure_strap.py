# Measure the strap loop around the X axis: outer/inner radius and width at each angle.
# Shows where the AI buckle bump is. Run on watch.blend.
import bpy, math
from collections import defaultdict

ob = bpy.data.objects["Watch"]
vs = [v.co for v in ob.data.vertices]
ymin = min(v.y for v in vs)
# loop centre: middle of the strap's Y/Z extent
yc = (min(v.y for v in vs) + max(v.y for v in vs)) / 2
zc = (min(v.z for v in vs) + max(v.z for v in vs)) / 2
print(f"loop centre y={yc:.3f} z={zc:.3f}")

bins = defaultdict(list)
for v in vs:
    dy, dz = v.y - yc, v.z - zc
    th = math.degrees(math.atan2(dz, dy))   # 0 = back (+Y), 90 = top, -90 = bottom, 180 = front
    bins[int(th // 10) * 10].append((math.hypot(dy, dz), v.x))
print("angle  r_in   r_out  x_min  x_max  n")
for a in sorted(bins):
    rs = [r for r, _ in bins[a]]; xs = [x for _, x in bins[a]]
    print(f"{a:5d}  {min(rs):.3f}  {max(rs):.3f}  {min(xs):.3f}  {max(xs):.3f}  {len(rs)}")
