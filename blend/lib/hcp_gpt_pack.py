"""blender -b COPY.blend --python hcp_gpt_pack.py -- OUT_DIR PACK_NUMBER [REF.obj ...]
Writes the GPT mesh pack: meshes/<name>.obj (world coordinates, Y forward, Z up, UVs and normals, no materials),
manifest.json and README.txt. Objects of HCP_rebuild and HCP_rebuild_engines are editable unless protected."""
import bpy, sys, os, json, shutil, datetime

out, num = sys.argv[sys.argv.index('--') + 1:][:2]
refs = sys.argv[sys.argv.index('--') + 3:]
EDIT_COLS = ('HCP_rebuild', 'HCP_rebuild_engines')
PROTECT_COLS = ('HCP_rebuild_poslights',)
EMPTY_COLS = ('HCP_rebuild_connections', 'HCP_rebuild_waypoints', 'HCP_rebuild_lights')
PROTECT_PREFIX = ('hcr_turret_mount_', 'hcr_dock_', 'hcr_bridge_', 'rb_dock_s_', 'hcr_cockpit', 'brref_')
NOTES = {
    'bridge_box': 'the 17.3 x 19.4 x 7 m game bridge box at rb_con_cockpit must stay fully enclosed',
    'eva_recess': 'rb_con_dock_xs recess, 4.5 m opening, 0.8 m deep',
    'dock_s_top': 'the walkable fighter dock S on the neck (hcr_dock_*) is protected; the old belly dock bay is gone',
}

def protected(o):
    cols = [c.name for c in o.users_collection]
    return o.name.startswith(PROTECT_PREFIX) or any(c in PROTECT_COLS for c in cols)

sel = [o for o in bpy.data.objects if o.type == 'MESH' and any(c.name in EDIT_COLS + PROTECT_COLS for c in o.users_collection)]
sel.sort(key=lambda o: o.name)
os.makedirs(out + '/meshes', exist_ok=True)
objs, edit = [], 0
dg = bpy.context.evaluated_depsgraph_get()
for o in sel:
    p = protected(o)
    mn = [min((o.matrix_world @ v.co)[i] for v in o.data.vertices) for i in range(3)]
    mx = [max((o.matrix_world @ v.co)[i] for v in o.data.vertices) for i in range(3)]
    objs.append({'name': o.name, 'protected': p, 'collections': [c.name for c in o.users_collection],
                 'materials': [s.material.name for s in o.material_slots if s.material],
                 'faces': len(o.data.polygons), 'bbox_min': [round(x, 3) for x in mn], 'bbox_max': [round(x, 3) for x in mx]})
    if p:
        continue
    bpy.ops.object.select_all(action='DESELECT')
    o.select_set(True)
    bpy.context.view_layer.objects.active = o
    bpy.ops.wm.obj_export(filepath='%s/meshes/%s.obj' % (out, o.name), export_selected_objects=True,
                          forward_axis='Y', up_axis='Z', export_materials=False, apply_modifiers=True)
    edit += 1
empties = []
for o in sorted((o for o in bpy.data.objects if o.type == 'EMPTY' and any(c.name in EMPTY_COLS for c in o.users_collection)), key=lambda o: o.name):
    mw = o.matrix_world
    empties.append({'name': o.name, 'location': [round(x, 3) for x in mw.to_translation()],
                    'rotation_quat': [round(x, 4) for x in mw.to_quaternion()]})
refinfo = {}
for r in refs:
    shutil.copy(r, out)
    refinfo[os.path.basename(r)] = 'reference only, do not return it.'
json.dump({'units': 'meters, Blender world coords (Z up, ship nose toward +Y, X symmetry plane at x = -420)',
           'objects': objs, 'empties': empties, 'notes': NOTES, 'references': refinfo},
          open(out + '/manifest.json', 'w'), indent=1)
head = """HCP mesh pack for editing without Blender.
- meshes/<object>.obj : one OBJ per editable hull object, in Blender WORLD coordinates (meters, Z up, ship nose toward +Y (X symmetry plane at x = -420 m in this file), X = left/right, symmetric on X). UVs and normals included. Object names are the file names and must stay the same.
- manifest.json : every object (editable or protected, collections, materials, bbox), every empty (connections, waypoints, light anchors) with world location/rotation, plus notes.bridge_box (the 17.3 x 19.4 x 7 m game bridge box at rb_con_cockpit that must stay fully enclosed) and notes.eva_recess (rb_con_dock_xs recess, 4.5 m opening, 0.8 m deep).
- Objects with "protected": true are NOT included as OBJ and must not be changed; empties must not move.
How to return your work: a zip with
  meshes/<object>.obj for every object you changed (same name = replace that object's mesh), new objects as meshes/new_<name>.obj,
  changes.json = {"replaced":[...], "new":[{"name":..,"material":..}], "deleted":[...], "notes":"per-object summary"}.
Keep geometry clean: no duplicate/coplanar overlapping faces, planar quads, symmetric on X, keep turret seats/weapon mounts/VLS footprints unchanged.

"""
body = os.environ.get('PACK_TEXT', 'Pack %s (%s).' % (num, datetime.date.today()))
open(out + '/README.txt', 'w').write(head + body + '\n')
print('PACK_DONE editable=%d protected=%d empties=%d' % (edit, len(objs) - edit, len(empties)))
