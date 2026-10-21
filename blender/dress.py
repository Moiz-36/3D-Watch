# Step 2 of the Blender cleanup: materials, photo dial, crystal, real-world scale, export.
# Needs blender/watch.blend (from cleanup.py) and photos/clean/dial.png (from make_dial_texture.py).
# Run: "blender app\blender.exe" blender\watch.blend -b -P blender\dress.py
import bpy, bmesh, os, math, glob
from mathutils import Vector

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DIAL_IMG = os.path.join(ROOT, "photos", "clean", "dial.png")
OUT_BLEND = os.path.join(ROOT, "blender", "watch-dressed.blend")
OUT_GLB = os.path.join(ROOT, "models", "watch.glb")
PREVIEW = os.path.join(ROOT, "blender", "previews")

BEZEL_R = 0.52          # bezel outer radius in model units (from measure_dial.py)
REAL_BEZEL_R = 0.0205   # real bezel radius in metres (~41 mm across) -> correct size in AR
CRYSTAL_R = 0.42        # glass dome radius
CRYSTAL_H = 0.03        # dome height

watch = bpy.data.objects["Watch"]
me = watch.data

# ---------------------------------------------------------------- measure
vs = [v.co for v in me.vertices]                       # object is at origin, unrotated
ymin, ymax = min(v.y for v in vs), max(v.y for v in vs)
front = [v for v in vs if v.y < ymin + 0.06]
cx = (min(v.x for v in front) + max(v.x for v in front)) / 2
cz = (min(v.z for v in front) + max(v.z for v in front)) / 2
print(f"dial centre x={cx:.3f} z={cz:.3f}, front y={ymin:.3f}")

# ---------------------------------------------------------------- materials
def principled(name, color, metallic=0.0, rough=0.5):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (*color, 1)
    b.inputs["Metallic"].default_value = metallic
    b.inputs["Roughness"].default_value = rough
    return m, b

steel, _ = principled("Steel", (0.80, 0.80, 0.82), metallic=1.0, rough=0.2)
strap, _ = principled("Strap", (0.015, 0.018, 0.028), rough=0.8)

dial_mat, dial_bsdf = principled("Dial", (1, 1, 1), rough=0.7)
dial_bsdf.inputs["Specular IOR Level"].default_value = 0.1   # the crystal does the shine
tex = dial_mat.node_tree.nodes.new("ShaderNodeTexImage")
tex.image = bpy.data.images.load(DIAL_IMG)
dial_mat.node_tree.links.new(tex.outputs["Color"], dial_bsdf.inputs["Base Color"])

glass, glass_bsdf = principled("Crystal", (1, 1, 1), rough=0.02)
glass_bsdf.inputs["Transmission Weight"].default_value = 1.0
glass_bsdf.inputs["IOR"].default_value = 1.5

me.materials.clear()
me.materials.append(strap)   # index 0
me.materials.append(steel)   # index 1

# ---------------------------------------------------------------- split case / strap
# Rule of thumb from the preview renders: the case is the front block around the dial axis,
# plus the lugs (outside the strap width) and the clasp at the very back of the loop.
def is_steel(p):
    dx, dz, dy = p.x - cx, p.z - cz, p.y - ymin
    r = math.hypot(dx, dz)
    strap_lane = abs(dx) < 0.27                 # the strap runs between the lugs
    case_body = dy < 0.42 and r < (0.53 if strap_lane else 0.60)
    lugs = dy < 0.42 and not strap_lane and abs(dz) < 0.72
    clasp = p.y > ymax - 0.15 and -0.62 < dz < -0.12   # buckle sits low on the back
    return case_body or lugs or clasp

strap_vg = watch.vertex_groups.new(name="strap")
strap_verts = set()
for poly in me.polygons:
    steel_face = is_steel(poly.center)
    poly.material_index = 1 if steel_face else 0
    if not steel_face:
        strap_verts.update(poly.vertices)
strap_vg.add(list(strap_verts), 1.0, "REPLACE")

# flatten spikes: a vertex sticking far out from the average of its neighbours is pulled back
bm = bmesh.new(); bm.from_mesh(me)
for _ in range(4):
    moved = 0
    for v in bm.verts:
        nbrs = [e.other_vert(v).co for e in v.link_edges]
        if not nbrs:
            continue
        avg = sum(nbrs, Vector()) / len(nbrs)
        edge_len = sum((n - avg).length for n in nbrs) / len(nbrs)
        if (v.co - avg).length > max(0.012, 1.5 * edge_len):
            v.co = avg; moved += 1
    print("spike vertices flattened:", moved)
bm.to_mesh(me); bm.free()

# smooth only the strap: removes lumps
sm = watch.modifiers.new("StrapSmooth", "SMOOTH")
sm.factor, sm.iterations, sm.vertex_group = 0.6, 10, "strap"
bpy.context.view_layer.objects.active = watch
bpy.ops.object.modifier_apply(modifier=sm.name)

# ---------------------------------------------------------------- photo dial ("puck")
# A short cylinder over the AI bezel+dial. Front face shows the photo, side is steel.
def make_face_puck(segments=128, depth=0.04):
    bm = bmesh.new()
    uv = bm.loops.layers.uv.new("UVMap")
    yf = ymin - 0.004
    ring_f, ring_b = [], []
    for i in range(segments):
        a = 2 * math.pi * i / segments
        x, z = cx + BEZEL_R * math.cos(a), cz + BEZEL_R * math.sin(a)
        ring_f.append(bm.verts.new((x, yf, z)))
        ring_b.append(bm.verts.new((x, yf + depth, z)))
    front_face = bm.faces.new(list(reversed(ring_f)))     # normal points to -Y (viewer)
    front_face.material_index = 0
    for i in range(segments):
        j = (i + 1) % segments
        f = bm.faces.new((ring_f[i], ring_f[j], ring_b[j], ring_b[i]))
        f.material_index = 1
    bm.normal_update()
    if front_face.normal.y > 0:
        front_face.normal_flip()
    for loop in front_face.loops:                         # planar UV from the photo
        co = loop.vert.co
        loop[uv].uv = (0.5 + 0.5 * (co.x - cx) / BEZEL_R, 0.5 + 0.5 * (co.z - cz) / BEZEL_R)
    m = bpy.data.meshes.new("FaceMesh")
    bm.to_mesh(m); bm.free()
    m.materials.append(dial_mat); m.materials.append(steel)
    ob = bpy.data.objects.new("Face", m)
    bpy.context.scene.collection.objects.link(ob)
    return ob

# ---------------------------------------------------------------- crystal dome
def make_crystal(rings=16, segments=96):
    bm = bmesh.new()
    y0 = ymin - 0.006
    grid = []
    for ri in range(rings + 1):
        t = ri / rings
        r = CRYSTAL_R * t
        y = y0 - CRYSTAL_H * (1 - t * t)                 # dome bulges toward the viewer
        if ri == 0:
            grid.append([bm.verts.new((cx, y, cz))])
            continue
        grid.append([bm.verts.new((cx + r * math.cos(2 * math.pi * s / segments), y,
                                   cz + r * math.sin(2 * math.pi * s / segments)))
                     for s in range(segments)])
    for s in range(segments):
        bm.faces.new((grid[0][0], grid[1][(s + 1) % segments], grid[1][s]))
    for ri in range(1, rings):
        for s in range(segments):
            n = (s + 1) % segments
            bm.faces.new((grid[ri][s], grid[ri][n], grid[ri + 1][n], grid[ri + 1][s]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    m = bpy.data.meshes.new("CrystalMesh")
    bm.to_mesh(m); bm.free()
    for p in m.polygons:
        p.use_smooth = True
    m.materials.append(glass)
    ob = bpy.data.objects.new("Crystal", m)
    bpy.context.scene.collection.objects.link(ob)
    return ob

face = make_face_puck()
crystal = make_crystal()

# ---------------------------------------------------------------- real-world size
# Parent everything to one empty, scale it to metres, and centre the dial on the origin.
root = bpy.data.objects.new("WatchRoot", None)
bpy.context.scene.collection.objects.link(root)
s = REAL_BEZEL_R / BEZEL_R
root.scale = (s, s, s)
for ob in (watch, face, crystal):
    ob.parent = root
root.location = (-cx * s, 0, -cz * s)

bpy.ops.wm.save_as_mainfile(filepath=OUT_BLEND)

# ---------------------------------------------------------------- export glTF binary
bpy.ops.export_scene.gltf(
    filepath=OUT_GLB, export_format="GLB",
    export_draco_mesh_compression_enable=True,
    export_image_format="WEBP",   # smaller than PNG; gltf-transform's webp step crashes here
    export_apply=True,
)
print("exported", OUT_GLB)

if os.environ.get("NO_PREVIEW"):          # set NO_PREVIEW=1 to skip the slow renders
    print("done")
    raise SystemExit

# ---------------------------------------------------------------- preview render
# Cycles on CPU: Eevee crashes in background mode with the AMD OpenGL driver (atio6axx.dll).
scene = bpy.context.scene
scene.render.engine = "CYCLES"
scene.cycles.device = "CPU"
scene.cycles.samples = 48
scene.cycles.use_denoising = True
scene.render.resolution_x, scene.render.resolution_y = 700, 700
scene.render.film_transparent = False
world = bpy.data.worlds.new("World"); scene.world = world
env = world.node_tree.nodes.new("ShaderNodeTexEnvironment")
hdr = glob.glob(os.path.join(os.path.dirname(bpy.app.binary_path), "*", "datafiles",
                             "studiolights", "world", "studio.exr"))[0]
env.image = bpy.data.images.load(hdr)
world.node_tree.links.new(env.outputs["Color"], world.node_tree.nodes["Background"].inputs["Color"])

cam = bpy.data.objects.new("Cam", bpy.data.cameras.new("Cam"))
scene.collection.objects.link(cam); scene.camera = cam
cam.data.lens = 85
size = 0.09    # metres, roughly the whole watch
for name, d in {"front": Vector((0, -1, 0)),
                "three-quarter": Vector((0.6, -1, 0.35)).normalized(),
                "side": Vector((1, -0.15, 0.1)).normalized(),
                "back": Vector((-0.4, 1, 0.3)).normalized()}.items():
    cam.location = d * size * 3.2
    cam.rotation_euler = (-d).to_track_quat("-Z", "Y").to_euler()
    scene.render.filepath = os.path.join(PREVIEW, f"dressed-{name}.png")
    bpy.ops.render.render(write_still=True)
print("done")
