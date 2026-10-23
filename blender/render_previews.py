# Render preview images of the finished watch (opens blender/watch-dressed.blend).
# Run: "blender app\blender.exe" blender\watch-dressed.blend -b -P blender\render_previews.py
# Cycles on CPU: Eevee crashes in background mode with the AMD OpenGL driver (atio6axx.dll).
import bpy, os, glob
from mathutils import Vector

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PREVIEW = os.path.join(ROOT, "blender", "previews")
os.makedirs(PREVIEW, exist_ok=True)

scene = bpy.context.scene
scene.render.engine = "CYCLES"
scene.cycles.device = "CPU"
scene.cycles.samples = 32
scene.cycles.use_denoising = True
scene.cycles.denoising_use_gpu = False     # GPU denoiser runs out of shared memory on the 780M
scene.render.resolution_x = scene.render.resolution_y = 600

# soft studio lighting from Blender's built-in light files
world = bpy.data.worlds.new("World"); scene.world = world
nt = world.node_tree
env = nt.nodes.new("ShaderNodeTexEnvironment")
hdr = glob.glob(os.path.join(os.path.dirname(bpy.app.binary_path), "*", "datafiles",
                             "studiolights", "world", "studio.exr"))[0]
env.image = bpy.data.images.load(hdr)
nt.links.new(env.outputs["Color"], nt.nodes["Background"].inputs["Color"])
nt.nodes["Background"].inputs["Strength"].default_value = 1.6

cam = bpy.data.objects.new("Cam", bpy.data.cameras.new("Cam"))
scene.collection.objects.link(cam); scene.camera = cam
cam.data.lens = 85
size = 0.09    # metres, roughly the whole watch
views = {
    "front": Vector((0, -1, 0)),
    "three-quarter": Vector((0.6, -1, 0.35)),
    "side": Vector((1, -0.15, 0.1)),
    "back": Vector((-0.4, 1, 0.3)),
    "buckle": Vector((0.45, 0.85, -0.6)),
    "strap-closeup": Vector((0.3, 0.2, 1)),
    "dial-closeup": Vector((0, -1, 0.05)),
    "clasp-closeup": Vector((0.5, 0.6, -0.9)),
}
CLOSE = {"strap-closeup": 0.45, "dial-closeup": 0.5, "clasp-closeup": 0.6}           # zoom factor for close-up views
only = os.environ.get("VIEWS")             # e.g. VIEWS=buckle,front to render just some
for name, d in views.items():
    if only and name not in only.split(","):
        continue
    d = d.normalized()
    cam.location = d * size * 3.2 * CLOSE.get(name, 1)
    cam.rotation_euler = (-d).to_track_quat("-Z", "Y").to_euler()
    scene.render.filepath = os.path.join(PREVIEW, f"dressed-{name}.png")
    bpy.ops.render.render(write_still=True)
    print("rendered", name)
