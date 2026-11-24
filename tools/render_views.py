"""blender -b --python render_views.py -- OBJ OUTDIR  : import OBJ, render front/side/three-quarter/top PNGs (Workbench, textured)."""
import bpy, sys, math, mathutils
obj, outdir = sys.argv[sys.argv.index('--') + 1:][:2]
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.wm.obj_import(filepath=obj)
objs = [o for o in bpy.context.scene.objects if o.type == 'MESH']
mn = mathutils.Vector((1e9,)*3); mx = mathutils.Vector((-1e9,)*3)
for o in objs:
    for c in o.bound_box:
        w = o.matrix_world @ mathutils.Vector(c)
        mn = mathutils.Vector(map(min, mn, w)); mx = mathutils.Vector(map(max, mx, w))
print('BLENDER_BBOX', tuple(round(x, 2) for x in (mx - mn)), 'min', tuple(round(x,2) for x in mn), 'max', tuple(round(x,2) for x in mx))
ctr = (mn + mx) / 2
sc = bpy.context.scene
sc.render.engine = 'BLENDER_WORKBENCH'
sc.display.shading.light = 'STUDIO'
sc.display.shading.color_type = 'TEXTURE'
sc.display.shading.show_cavity = False
sc.render.resolution_x, sc.render.resolution_y = 1400, 1000
sc.world = bpy.data.worlds.new('w'); sc.world.color = (0.05, 0.05, 0.08)
cam = bpy.data.objects.new('cam', bpy.data.cameras.new('cam')); sc.collection.objects.link(cam); sc.camera = cam
cam.data.type = 'ORTHO'
span = max(mx - mn)
cam.data.ortho_scale = span * 1.1
views = {'front': (0, 1, 0), 'side': (1, 0, 0), 'three_quarter': (0.8, 0.9, 0.55), 'top': (0, 0.001, 1), 'front_nose': (0, -1, 0)}
for name, d in views.items():
    d = mathutils.Vector(d).normalized()
    cam.location = ctr + d * span * 3
    cam.rotation_euler = (ctr - cam.location).to_track_quat('-Z', 'Y').to_euler()
    if name == 'top': cam.rotation_euler = (ctr - cam.location).to_track_quat('-Z', 'Y').to_euler()
    sc.render.filepath = '%s/%s.png' % (outdir, name)
    bpy.ops.render.render(write_still=True)
