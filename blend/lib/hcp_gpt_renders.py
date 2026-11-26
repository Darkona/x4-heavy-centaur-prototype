"""blender -b COPY.blend --python hcp_gpt_renders.py -- OUT_DIR REF_X3.obj REF_BULGES.obj
Workbench renders (STUDIO light, cavity, outline, flat colour per zone) of the ship and of the X3 reference placed the same."""
import bpy, sys, math, os
from mathutils import Vector

out, ref_x3, ref_bulges = sys.argv[sys.argv.index('--') + 1:][:3]
os.makedirs(out, exist_ok=True)
SHOW = ('HCP_rebuild', 'HCP_rebuild_engines', 'HCP_rebuild_poslights')
COL = {'belly': (0.85, 0.25, 0.2, 1), 'rad': (0.95, 0.75, 0.15, 1), 'wing': (0.2, 0.45, 0.9, 1),
       'prow': (0.2, 0.75, 0.35, 1), 'rest': (0.62, 0.62, 0.62, 1)}

def zone(n):
    if n == 'hcr_bow_prow': return 'prow'
    if n.startswith('hcr_keel_intake'): return 'rad'
    if n.startswith(('hcr_keel', 'hcr_hangar_pit')): return 'belly'
    if n.startswith(('hcr_wing', 'hcr_wingtip')): return 'wing'
    return 'rest'

ship = []
for o in bpy.data.objects:
    if o.type != 'MESH':
        continue
    if any(c.name in SHOW for c in o.users_collection) and not o.name.startswith(('rb_dock_s_', 'anim_vlshatch')):
        o.hide_render = False
        o.hide_viewport = False
        o.color = COL[zone(o.name)]
        ship.append(o)
    else:
        o.hide_render = True
        o.hide_viewport = True

def bounds(objs):
    pts = [o.matrix_world @ Vector(c) for o in objs for c in o.bound_box]
    return Vector(map(min, zip(*pts))), Vector(map(max, zip(*pts)))

bpy.ops.wm.obj_import(filepath=ref_x3, forward_axis='Y', up_axis='Z')
x3 = [o for o in bpy.context.selected_objects]
bpy.ops.wm.obj_import(filepath=ref_bulges, forward_axis='Y', up_axis='Z')
bul = [o for o in bpy.context.selected_objects]
for o in x3:
    o.location.x -= 130
    o.color = COL['rest']
for o in bul:
    o.color = COL['belly']
bpy.context.view_layer.update()
sm, sx = bounds(ship)
cx = (sm.x + sx.x) / 2
print('SHIP', sm, sx)

sc = bpy.context.scene
sc.render.engine = 'BLENDER_WORKBENCH'
sh = sc.display.shading
sh.light = 'STUDIO'
sh.color_type = 'OBJECT'
sh.show_cavity = True
sh.cavity_type = 'BOTH'
sh.show_object_outline = True
sh.object_outline_color = (0, 0, 0)
sc.world = bpy.data.worlds.new('w')
sc.world.color = (0.5, 0.52, 0.55)
sc.render.resolution_x, sc.render.resolution_y = 1600, 1000
sc.render.image_settings.file_format = 'JPEG'
sc.render.image_settings.quality = 88
sc.view_settings.view_transform = 'Standard'
cam = bpy.data.objects.new('cam', bpy.data.cameras.new('cam'))
sc.collection.objects.link(cam)
sc.camera = cam

ctr = Vector((cx, (sm.y + sx.y) / 2, (sm.z + sx.z) / 2))
span = max(sx - sm)
wing = [o for o in ship if o.name.startswith('hcr_wing_core')]
wm, wx = bounds(wing) if wing else (sm, sx)
wing_pt = Vector((wx.x if wx.x - cx > cx - wm.x else wm.x, (wm.y + wx.y) / 2, (wm.z + wx.z) / 2))
prow = [o for o in ship if o.name == 'hcr_bow_prow']
pm, px = bounds(prow)
prow_pt = (pm + px) / 2
side = [o for o in wing if bounds([o])[0].x > cx]
sm2, sx2 = bounds(side) if side else (wm, wx)
wj = Vector((sm2.x + 4, (sm2.y + sx2.y) / 2, (sm2.z + sx2.z) / 2))

def shot(name, target, direction, dist, ortho=None, lens=50):
    d = Vector(direction).normalized()
    cam.location = target + d * dist
    cam.rotation_euler = (target - cam.location).to_track_quat('-Z', 'Y').to_euler()
    if ortho:
        cam.data.type = 'ORTHO'
        cam.data.ortho_scale = ortho
    else:
        cam.data.type = 'PERSP'
        cam.data.lens = lens
        cam.data.clip_end = 5000
    cam.data.clip_start = 0.5
    sc.render.filepath = '%s/%s.jpg' % (out, name)
    bpy.ops.render.render(write_still=True)

views = [
    ('bottom', ctr, (0, 0.0001, -1), span * 3, span * 1.5, None),
    ('side', ctr, (1, 0, 0), span * 3, span * 1.05, None),
    ('q34_bow_below', ctr, (0.8, 0.9, -0.55), span * 1.6, None, 50),
    ('q34_stern_below', ctr, (0.8, -0.9, -0.55), span * 1.6, None, 50),
    ('front', ctr, (0, 1, 0), span * 3, span * 0.75, None),
    ('close_wing_body', wj, (1, 0.7, -0.45), 70, None, 50),
    ('close_prow', prow_pt, (0.6, 0.8, 0.35), 60, None, 50),
]
def run(prefix):
    for n, t, d, dist, ort, lens in views:
        shot(prefix + n, t, d, dist, ort, lens or 50)

for o in x3 + bul:
    o.hide_render = True
for o in ship:
    o.hide_render = False
run('ship_')
for o in ship:
    o.hide_render = True
for o in x3 + bul:
    o.hide_render = False
run('x3_')
print('RENDERS_DONE')
