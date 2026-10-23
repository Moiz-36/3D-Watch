# Step 2 of the Blender cleanup: materials, photo dial, crystal, real-world scale, export.
# Needs blender/watch.blend (from cleanup.py) and photos/clean/dial.png (from make_dial_texture.py).
# Run: "blender app\blender.exe" blender\watch.blend -b -P blender\dress.py
import bpy, bmesh, os, math, glob
from mathutils import Vector

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DIAL_IMG = os.path.join(ROOT, "photos", "clean", "dial.png")
CASEBACK_IMG = os.path.join(ROOT, "photos", "clean", "caseback.png")   # from make_caseback_texture.py
OUT_BLEND = os.path.join(ROOT, "blender", "watch-dressed.blend")
OUT_GLB = os.path.join(ROOT, "models", "watch.glb")
PREVIEW = os.path.join(ROOT, "blender", "previews")

BEZEL_R = 0.52          # bezel outer radius in model units (from measure_dial.py)
REAL_BEZEL_R = 0.0205   # real bezel radius in metres (~41 mm across) -> correct size in AR
CRYSTAL_R = 0.42        # glass dome radius
CRYSTAL_H = 0.03        # dome height
CASEBACK_R = 0.46       # engraved caseback radius (real one is ~0.88x the bezel)
CASEBACK_DY = 0.203     # flat back of the AI case sits ~0.198 behind the front (measured)

watch = bpy.data.objects["Watch"]
me = watch.data

# ---------------------------------------------------------------- measure
vs = [v.co for v in me.vertices]                       # object is at origin, unrotated
ymin, ymax = min(v.y for v in vs), max(v.y for v in vs)
front = [v for v in vs if v.y < ymin + 0.06]
cx = (min(v.x for v in front) + max(v.x for v in front)) / 2
cz = (min(v.z for v in front) + max(v.z for v in front)) / 2
print(f"dial centre x={cx:.3f} z={cz:.3f}, front y={ymin:.3f}")

# ---------------------------------------------------------------- strap loop geometry
# The strap is a loop around the X axis. Angle 0 = back of the loop, -90 = bottom, ±180 = front.
LOOP_YC = (ymin + ymax) / 2
LOOP_ZC = (min(v.z for v in vs) + max(v.z for v in vs)) / 2
BUCKLE_FROM, BUCKLE_TO = -58.0, -12.0   # where the AI made a lumpy buckle (from measure_strap.py)

def loop_angle(co):
    return math.degrees(math.atan2(co.z - LOOP_ZC, co.y - LOOP_YC))

def loop_radius(co):
    return math.hypot(co.y - LOOP_YC, co.z - LOOP_ZC)

def strap_band(a0, a1):
    """outer radius and x range of the strap between two angles"""
    pts = [v for v in vs if a0 <= loop_angle(v) < a1]
    return (max(loop_radius(v) for v in pts), min(v.x for v in pts), max(v.x for v in pts))

r_before, xmin_b, xmax_b = strap_band(BUCKLE_FROM - 10, BUCKLE_FROM)
r_after, xmin_a, xmax_a = strap_band(BUCKLE_TO, BUCKLE_TO + 10)
STRAP_XMIN, STRAP_XMAX = (xmin_b + xmin_a) / 2, (xmax_b + xmax_a) / 2

def strap_outer_r(angle):
    t = (angle - BUCKLE_FROM) / (BUCKLE_TO - BUCKLE_FROM)
    return r_before + (r_after - r_before) * min(max(t, 0), 1)

# flatten the AI buckle bump back into a plain strap (the new buckle goes on top)
flattened = 0
for v in me.vertices:
    a = loop_angle(v.co)
    if BUCKLE_FROM < a < BUCKLE_TO:
        dy, dz = v.co.y - LOOP_YC, v.co.z - LOOP_ZC
        r = math.hypot(dy, dz)
        r_new = min(r, strap_outer_r(a))
        v.co.y, v.co.z = LOOP_YC + dy / r * r_new, LOOP_ZC + dz / r * r_new
        v.co.x = min(max(v.co.x, STRAP_XMIN), STRAP_XMAX)
        flattened += 1
print(f"buckle bump flattened ({flattened} verts), strap x {STRAP_XMIN:.3f}..{STRAP_XMAX:.3f}")
vs = [v.co for v in me.vertices]

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
brushed, _ = principled("BrushedSteel", (0.75, 0.75, 0.77), metallic=1.0, rough=0.38)
engrave, _ = principled("Engraving", (0.35, 0.35, 0.37), metallic=1.0, rough=0.45)

# fabric strap: generated weave texture + normal map (scripts/make_strap_texture.py)
TEX_DIR = os.path.join(ROOT, "blender", "textures")
strap, strap_bsdf = principled("Strap", (1, 1, 1), rough=0.8)
strap_bsdf.inputs["Sheen Weight"].default_value = 0.12         # faint fabric glow (more washes it out)
strap_bsdf.inputs["Sheen Tint"].default_value = (0.4, 0.4, 0.42, 1)
strap_bsdf.inputs["Specular IOR Level"].default_value = 0.3   # fabric is not shiny
st = strap.node_tree
col_tex = st.nodes.new("ShaderNodeTexImage")
col_tex.image = bpy.data.images.load(os.path.join(TEX_DIR, "strap-color.png"))
st.links.new(col_tex.outputs["Color"], strap_bsdf.inputs["Base Color"])
nrm_tex = st.nodes.new("ShaderNodeTexImage")
nrm_tex.image = bpy.data.images.load(os.path.join(TEX_DIR, "strap-normal.png"))
nrm_tex.image.colorspace_settings.name = "Non-Color"
nrm_map = st.nodes.new("ShaderNodeNormalMap")
nrm_map.inputs["Strength"].default_value = 1.0
st.links.new(nrm_tex.outputs["Color"], nrm_map.inputs["Color"])
st.links.new(nrm_map.outputs["Normal"], strap_bsdf.inputs["Normal"])

dial_mat, dial_bsdf = principled("Dial", (1, 1, 1), rough=0.7)
dial_bsdf.inputs["Specular IOR Level"].default_value = 0.1   # the crystal does the shine
tex = dial_mat.node_tree.nodes.new("ShaderNodeTexImage")
tex.image = bpy.data.images.load(DIAL_IMG)
dial_mat.node_tree.links.new(tex.outputs["Color"], dial_bsdf.inputs["Base Color"])

# Nearly invisible glass: a faint see-through layer that only adds reflections.
# (Full transmission made the web viewer draw a milky haze over the dial.)
# engraved caseback: photo texture on brushed steel (the photo already holds the shading)
caseback_mat, cb_bsdf = principled("Caseback", (1, 1, 1), metallic=0.6, rough=0.35)
cb_tex = caseback_mat.node_tree.nodes.new("ShaderNodeTexImage")
cb_tex.image = bpy.data.images.load(CASEBACK_IMG)
caseback_mat.node_tree.links.new(cb_tex.outputs["Color"], cb_bsdf.inputs["Base Color"])

glass, glass_bsdf = principled("Crystal", (1, 1, 1), rough=0.0)
glass_bsdf.inputs["Alpha"].default_value = 0.06
glass_bsdf.inputs["IOR"].default_value = 1.5
glass.surface_render_method = "BLENDED"

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
    return case_body or lugs

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

# ---------------------------------------------------------------- strap UVs
# Unroll the loop: U runs along the strap (angle x radius), V runs across it (x).
# The seam is at the front, hidden under the case.
TILE = 0.46                       # one texture tile ≈ strap width
uv_layer = me.uv_layers.new(name="UVMap")
for poly in me.polygons:
    us = []
    for li in poly.loop_indices:
        co = me.vertices[me.loops[li].vertex_index].co
        a = math.atan2(co.z - LOOP_ZC, co.y - LOOP_YC)       # -pi..pi, wraps at the front
        us.append((a + math.pi) * 0.9 / TILE)
    span = 2 * math.pi * 0.9 / TILE
    if max(us) - min(us) > span / 2:                          # face crosses the seam
        us = [u + span if u < span / 2 else u for u in us]
    for li, u in zip(poly.loop_indices, us):
        co = me.vertices[me.loops[li].vertex_index].co
        uv_layer.data[li].uv = (u, (co.x - STRAP_XMIN) / TILE)

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

# ---------------------------------------------------------------- engraved caseback
# A thin disc on the flat back of the case, facing +Y (into the strap loop).
# Seen from the back, +X (the crown side) is on the left, so U is mirrored compared to the dial.
def make_caseback(segments=128, depth=0.012):
    bm = bmesh.new()
    uv = bm.loops.layers.uv.new("UVMap")
    yb = ymin + CASEBACK_DY
    ring_b, ring_f = [], []
    for i in range(segments):
        a = 2 * math.pi * i / segments
        x, z = cx + CASEBACK_R * math.cos(a), cz + CASEBACK_R * math.sin(a)
        ring_b.append(bm.verts.new((x, yb, z)))
        ring_f.append(bm.verts.new((x, yb - depth, z)))
    back_face = bm.faces.new(ring_b)
    back_face.material_index = 0
    for i in range(segments):
        j = (i + 1) % segments
        f = bm.faces.new((ring_b[j], ring_b[i], ring_f[i], ring_f[j]))
        f.material_index = 1
    bm.normal_update()
    if back_face.normal.y < 0:
        back_face.normal_flip()
    for f in bm.faces[1:]:
        if (f.calc_center_median() - Vector((cx, f.calc_center_median().y, cz))).dot(f.normal) < 0:
            f.normal_flip()
    for loop in back_face.loops:
        co = loop.vert.co
        loop[uv].uv = (0.5 - 0.5 * (co.x - cx) / CASEBACK_R, 0.5 + 0.5 * (co.z - cz) / CASEBACK_R)
    m = bpy.data.meshes.new("CasebackMesh")
    bm.to_mesh(m); bm.free()
    m.materials.append(caseback_mat); m.materials.append(steel)
    ob = bpy.data.objects.new("Caseback", m)
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

# ---------------------------------------------------------------- folding buckle
# A steel folding clasp that follows the curve of the strap, with side push-buttons and an Ω.
def loft_on_strap(name, a0, a1, x0, x1, r_lo, r_hi, corner, mat, steps=28):
    """Rounded-rectangle tube bent along the strap between angles a0..a1 (degrees).
    r_lo/r_hi are offsets from the strap's outer surface."""
    w, h = (x1 - x0) / 2, (r_hi - r_lo) / 2
    xc, rc = (x0 + x1) / 2, (r_lo + r_hi) / 2
    c = min(corner, w * 0.9, h * 0.9)
    prof = []                                   # rounded rectangle in (x, r)
    for qx, qy, start in ((1, 1, 0), (-1, 1, 90), (-1, -1, 180), (1, -1, 270)):
        for k in range(5):
            t = math.radians(start + k * 22.5)
            prof.append((xc + qx * (w - c) + c * math.cos(t), rc + qy * (h - c) + c * math.sin(t)))
    bm = bmesh.new()
    rings = []
    for i in range(steps + 1):
        a = a0 + (a1 - a0) * i / steps
        ar = math.radians(a)
        r0 = strap_outer_r(a)
        rings.append([bm.verts.new((px, LOOP_YC + (r0 + pr) * math.cos(ar),
                                    LOOP_ZC + (r0 + pr) * math.sin(ar))) for px, pr in prof])
    n = len(prof)
    for i in range(steps):
        for k in range(n):
            bm.faces.new((rings[i][k], rings[i][(k + 1) % n], rings[i + 1][(k + 1) % n], rings[i + 1][k]))
    bm.faces.new(rings[0]); bm.faces.new(list(reversed(rings[-1])))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    m = bpy.data.meshes.new(name + "Mesh")
    bm.to_mesh(m); bm.free()
    m.materials.append(mat)
    ob = bpy.data.objects.new(name, m)
    bpy.context.scene.collection.objects.link(ob)
    bpy.context.view_layer.objects.active = ob
    for o in bpy.context.selected_objects:
        o.select_set(False)
    ob.select_set(True)
    bpy.ops.object.shade_auto_smooth(angle=math.radians(40))
    return ob

BX0, BX1 = STRAP_XMIN - 0.035, STRAP_XMAX + 0.035          # buckle a bit wider than the strap
# Shaped like the Omega folding clasp in photos/raw/clasp.png:
# a polished cover plate, a taller end cap where the strap tucks in, and a push-button on each side.
buckle = loft_on_strap("Buckle", BUCKLE_FROM + 3, BUCKLE_TO - 3, BX0, BX1,
                       -0.02, 0.075, 0.03, steel)
endcap = loft_on_strap("BuckleCap", BUCKLE_FROM + 1, BUCKLE_FROM + 7, BX0 - 0.012, BX1 + 0.012,
                       -0.035, 0.095, 0.035, steel, steps=8)
side_buttons = [loft_on_strap(f"BuckleButton{i}", BUCKLE_TO - 14, BUCKLE_TO - 6, x0, x1,
                              -0.005, 0.05, 0.012, brushed, steps=8)
                for i, (x0, x1) in enumerate(((BX0 - 0.03, BX0 + 0.01), (BX1 - 0.01, BX1 + 0.03)))]
bpy.context.view_layer.objects.active = buckle             # one clasp object: easier in the viewer
for o in bpy.context.selected_objects:
    o.select_set(False)
for o in [buckle, endcap] + side_buttons:
    o.select_set(True)
bpy.ops.object.join()

def make_omega(angle):
    """Raised Ω logo on top of the buckle."""
    cu = bpy.data.curves.new("OmegaText", "FONT")
    cu.body = "Ω"
    cu.size = 0.17
    cu.extrude = 0.004
    cu.align_x, cu.align_y = "CENTER", "CENTER"
    tmp = bpy.data.objects.new("OmegaTmp", cu)
    bpy.context.scene.collection.objects.link(tmp)
    m = bpy.data.meshes.new_from_object(tmp)
    bpy.data.objects.remove(tmp); bpy.data.curves.remove(cu)
    m.materials.append(engrave)
    ob = bpy.data.objects.new("BuckleLogo", m)
    bpy.context.scene.collection.objects.link(ob)
    ar = math.radians(angle)
    nrm = Vector((0, math.cos(ar), math.sin(ar)))            # points out of the strap
    tan = Vector((0, -math.sin(ar), math.cos(ar)))           # along the strap
    from mathutils import Matrix
    rot = Matrix((Vector((-1, 0, 0)), tan, nrm)).transposed()  # columns: text X, Y, Z
    r = strap_outer_r(angle) + 0.075 + 0.002
    ob.matrix_world = Matrix.Translation(((BX0 + BX1) / 2, LOOP_YC + r * math.cos(ar),
                                          LOOP_ZC + r * math.sin(ar))) @ rot.to_4x4()
    return ob

logo = make_omega(BUCKLE_FROM + 15)

face = make_face_puck()
crystal = make_crystal()
caseback = make_caseback()

# ---------------------------------------------------------------- real-world size
# Parent everything to one empty, scale it to metres, and centre the dial on the origin.
root = bpy.data.objects.new("WatchRoot", None)
bpy.context.scene.collection.objects.link(root)
s = REAL_BEZEL_R / BEZEL_R
root.scale = (s, s, s)
for ob in (watch, face, crystal, caseback, buckle, logo):
    ob.parent = root          # child keeps its local transform, so the root's scale applies to all
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
print("done")
