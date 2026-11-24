import bpy
import os
import sys
from mathutils import Matrix

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from hcp_vdata import add_vertex_data

COMPONENT = 'turret_arg_m_hcp_vls_01_mk1'
OUT = '/home/darkona/development/x4/p1[assets]/extensions/heavy_centaur_prototype/assets/props/weaponsystems/hcp/' + COMPONENT + '.blend'
ROOT = 'con_turret_vls_01'
PREFIX = 'vls_'
COMPONENT_CON = ('con_turret_vls', 'turret medium missile component hittable hcp_vls')
EXTRA_CONS = [('container', 'contents', 0)]
PART_TAGS = {
    'part_socket': ['forceoutline'],
    'part_rotator': ['iklink', 'nocollision', 'forceoutline'],
    'part_gun': ['iklink', 'nocollision', 'forceoutline'],
}

layouts = bpy.propertyGroupLayouts
names_in = {g: {d['name'] for d in defs} for g, defs in layouts.items()}
TAG_GROUPS = [g for g in ('ConnectionTags', 'NPC ConnectionTags', 'Symmetry') if g in names_in]


def apply_tags(e, tagstr):
    extra = []
    for t in tagstr.split():
        g = next((g for g in TAG_GROUPS if t in names_in[g]), None)
        if g:
            setattr(getattr(e, g), t, True)
        else:
            extra.append(t)
    if extra:
        e['extratags'] = ' '.join(extra)


root = bpy.data.objects[ROOT]
src = bpy.data.collections['HCP_turret_vls']
out_col = bpy.data.collections.new('vls_export_tmp')
bpy.context.scene.collection.children.link(out_col)

mapping = {}
for o in src.objects:
    if not o.name.startswith(PREFIX):
        continue
    if o.type == 'MESH':
        ob = o.copy()
        ob.data = o.data.copy()
        ob.animation_data_clear()
        for uv in list(ob.data.uv_layers)[:1]:
            uv.name = 'uv1'
    else:
        ob = bpy.data.objects.new('tmp_' + o.name, None)
        ob.empty_display_type = 'SINGLE_ARROW'
        ob.empty_display_size = 0.5
        apply_tags(ob, o.get('tags') or '')
    for c in list(ob.users_collection):
        c.objects.unlink(ob)
    out_col.objects.link(ob)
    mapping[o] = ob

for o, ob in mapping.items():
    if o.parent in mapping:
        ob.parent = mapping[o.parent]
        ob.matrix_parent_inverse = Matrix.Identity(4)
        ob.matrix_basis = o.matrix_basis.copy()
    else:
        ob.parent = None
        ob.matrix_world = root.matrix_world.inverted() @ o.matrix_world
    if o.type == 'MESH':
        add_vertex_data(ob)

cname, ctags = COMPONENT_CON
ce = bpy.data.objects.new('tmp_' + cname, None)
out_col.objects.link(ce)
ce.empty_display_type = 'ARROWS'
apply_tags(ce, ctags)
extra_objs = [(ce, cname)]
for nm, tags, value in EXTRA_CONS:
    e = bpy.data.objects.new('tmp_' + nm, None)
    out_col.objects.link(e)
    apply_tags(e, tags)
    e.value = value
    extra_objs.append((e, nm))

final = [(ob, o.get('x4_part') or o.name[len(PREFIX):]) for o, ob in mapping.items()] + extra_objs

keep = set(out_col.objects)
for o in list(bpy.data.objects):
    if o not in keep:
        bpy.data.objects.remove(o, do_unlink=True)
for s in list(bpy.data.scenes):
    if s != bpy.context.scene:
        bpy.data.scenes.remove(s)
scene = bpy.context.scene
for c in list(bpy.data.collections):
    if c != out_col:
        bpy.data.collections.remove(c)
for o in list(out_col.objects):
    scene.collection.objects.link(o)
    out_col.objects.unlink(o)
bpy.data.collections.remove(out_col)
for t in list(bpy.data.texts):
    bpy.data.texts.remove(t)
for a in list(bpy.data.actions):
    bpy.data.actions.remove(a)
bpy.data.orphans_purge(do_local_ids=True, do_linked_ids=False, do_recursive=True)

for ob, nm in final:
    ob.name = nm
    if ob.data is not None:
        ob.data.name = nm
for nm, tags in PART_TAGS.items():
    for t in tags:
        setattr(scene.objects[nm].GeometryTags, t, True)

scene.classAttr = 'missileturret'
scene.name = COMPONENT
os.makedirs(os.path.dirname(OUT), exist_ok=True)
bpy.ops.wm.save_as_mainfile(filepath=OUT, relative_remap=True)

for o in sorted(scene.objects, key=lambda o: o.name):
    tg = [t for g in TAG_GROUPS + ['GeometryTags'] for t in names_in[g] if getattr(getattr(o, g), t)]
    print('VLS', o.name, o.type, 'parent', o.parent.name if o.parent else None, 'loc', tuple(round(v, 3) for v in o.matrix_world.translation), 'tags', tg, o.get('extratags'), 'cons', [(c.type, round(c.min_x, 4), round(c.max_x, 4), round(c.min_z, 4), round(c.max_z, 4)) for c in o.constraints])
