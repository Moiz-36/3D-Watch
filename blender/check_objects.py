# Print size and sanity of every object in the dressed file.
import bpy, math
for ob in bpy.data.objects:
    if ob.type != "MESH":
        print(ob.name, ob.type, tuple(round(x, 4) for x in ob.matrix_world.translation)); continue
    cos = [ob.matrix_world @ v.co for v in ob.data.vertices]
    bad = sum(1 for c in cos if any(math.isnan(x) or math.isinf(x) for x in c))
    lo = [min(c[i] for c in cos) for i in range(3)]
    hi = [max(c[i] for c in cos) for i in range(3)]
    print(f"{ob.name:14s} verts {len(cos):6d} faces {len(ob.data.polygons):6d} bad {bad} "
          f"min {[round(x,4) for x in lo]} max {[round(x,4) for x in hi]} "
          f"uv {[l.name for l in ob.data.uv_layers]}")
