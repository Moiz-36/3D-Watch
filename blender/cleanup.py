# Step 1 of the Blender cleanup: import the AI mesh, reduce triangles, smooth shading,
# save a .blend file, and render quick preview images from 4 sides.
# Run: "blender app\blender.exe" -b -P blender\cleanup.py
import bpy, os, math
from mathutils import Vector

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "models", "watch-raw.glb")
BLEND = os.path.join(ROOT, "blender", "watch.blend")
PREVIEW = os.path.join(ROOT, "blender", "previews")
TARGET_TRIS = 80_000

# --- start from an empty scene ---
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=SRC)
watch = [o for o in bpy.context.scene.objects if o.type == "MESH"][0]
watch.name = "Watch"
bpy.context.view_layer.objects.active = watch
watch.select_set(True)

# --- reduce triangle count (Decimate "Collapse" keeps the overall shape) ---
tris = len(watch.data.polygons)
dec = watch.modifiers.new("Decimate", "DECIMATE")
dec.ratio = TARGET_TRIS / tris
bpy.ops.object.modifier_apply(modifier=dec.name)
print(f"triangles: {tris} -> {len(watch.data.polygons)}")

# --- smooth shading, but keep sharp edges (e.g. case edges) crisp ---
bpy.ops.object.shade_auto_smooth(angle=math.radians(35))

# --- centre the model on the origin ---
bpy.ops.object.origin_set(type="ORIGIN_GEOMETRY", center="BOUNDS")
watch.location = (0, 0, 0)

bpy.ops.wm.save_as_mainfile(filepath=BLEND)

# --- preview renders (Workbench = fast grey clay look) ---
scene = bpy.context.scene
scene.render.engine = "BLENDER_WORKBENCH"
scene.render.resolution_x = scene.render.resolution_y = 600
scene.display.shading.light = "MATCAP"
os.makedirs(PREVIEW, exist_ok=True)

cam_data = bpy.data.cameras.new("PreviewCam")
cam = bpy.data.objects.new("PreviewCam", cam_data)
scene.collection.objects.link(cam)
scene.camera = cam
dist = max(watch.dimensions) * 2.5

views = {"+X": Vector((1, 0, 0)), "-X": Vector((-1, 0, 0)),
         "+Y": Vector((0, 1, 0)), "-Y": Vector((0, -1, 0))}
for name, d in views.items():
    cam.location = d * dist
    cam.rotation_euler = (-d).to_track_quat("-Z", "Y").to_euler()
    scene.render.filepath = os.path.join(PREVIEW, f"view{name}.png")
    bpy.ops.render.render(write_still=True)

# remove preview camera so it doesn't end up in the saved file later
bpy.data.objects.remove(cam)
print("done")
