# Print basic facts about the AI mesh: size, triangle count, loose pieces.
# Run: "blender app\blender.exe" -b -P blender\inspect_mesh.py
import bpy, bmesh, os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=os.path.join(ROOT, "models", "watch-raw.glb"))

for ob in [o for o in bpy.context.scene.objects if o.type == "MESH"]:
    print("OBJECT", ob.name, "dims", tuple(round(d, 3) for d in ob.dimensions),
          "loc", tuple(round(v, 3) for v in ob.matrix_world.translation))
    bm = bmesh.new(); bm.from_mesh(ob.data)
    print("verts", len(bm.verts), "faces", len(bm.faces))
    # find connected pieces
    seen, pieces = set(), []
    for v in bm.verts:
        if v.index in seen: continue
        stack, n = [v], 0
        seen.add(v.index)
        while stack:
            cur = stack.pop(); n += 1
            for e in cur.link_edges:
                o = e.other_vert(cur)
                if o.index not in seen:
                    seen.add(o.index); stack.append(o)
        pieces.append(n)
    pieces.sort(reverse=True)
    print("pieces", len(pieces), "largest", pieces[:10])
    print("non-manifold edges", sum(1 for e in bm.edges if not e.is_manifold))
    bm.free()
