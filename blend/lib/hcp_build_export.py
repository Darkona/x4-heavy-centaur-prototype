import bpy
import json
import math
import os
import sys
from mathutils import Matrix, Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from hcp_vdata import add_vertex_data

OUT = '/home/darkona/development/x4/p1[assets]/extensions/heavy_centaur_prototype/assets/units/size_l/ship_arg_l_hcp_01.blend'
LIB = '/home/darkona/development/x4/heavy-centaur/blend/lib/thruster_ship_m_01.blend'
COL_OBJ = '/home/darkona/development/x4/heavy-centaur/blend/lib/vhacd/part_main.obj'
ENGINE_BODY_LIB = '/home/darkona/development/x4/heavy-centaur/blend/lib/engine_arg_m_allround_01_body.blend'
ENGINE_BODY_TAGS = ['engineeffect', 'forceoutline', 'nocollision']
FLAME_UV_KEYS = [(1, 0.3), (10, 3.0)]
SHIFT = Matrix.Translation((420.0, 0.0, 0.0))

EXCLUDE = {'rb_dock_s_clearance', 'rb_dock_s_pad'}
DETAIL = {'hcr_greebles', 'hcr_orig_details', 'hcr_poslight_housings', 'hcr_vls_frames'}
CAPS = {'hcr_bridge_window_cap'}
RADARS = {
    'rb_work_Bships_animprops_m6mainradar1_4': 'anim_radar_01',
    'rb_work_Bships_animprops_m6radarspike1_5': 'anim_radar_02',
    'rb_work_Bships_animprops_m6radarspike1_6': 'anim_radar_03',
    'hcr_roof_dish': 'anim_radar_04',
    'hcr_keel_ball_sphere': 'anim_radar_05',
}
HATCHES = {'anim_vlshatch_01_a', 'anim_vlshatch_01_b', 'anim_vlshatch_02_a', 'anim_vlshatch_02_b'}
LODS = [(1, 0.5), (2, 0.25), (3, 0.10)]
HATCH_ACTIONS = {}
HATCH_OBS = {}
VLS_HATCHES = {'con_turret_vls_01': ('anim_vlshatch_01_a', 'anim_vlshatch_01_b'), 'con_turret_vls_02': ('anim_vlshatch_02_a', 'anim_vlshatch_02_b')}
HATCH_DUMMY_SIZE = 0.17
RADAR_PIVOTS = {'anim_radar_01': (-0.019, -81.998, -25.364), 'anim_radar_02': (23.42, -82.045, 11.939), 'anim_radar_03': (-22.048, -82.045, 12.927), 'anim_radar_04': (0.0, -86.2, 34.15), 'anim_radar_05': (0.07, -34.57, -35.63)}
RADAR_AXES = {'anim_radar_01': (0.0, 0.0, 1.0), 'anim_radar_02': (0.309, 0.0119, 0.951), 'anim_radar_03': (-0.309, 0.0119, 0.951), 'anim_radar_04': (0.0, 0.0, 1.0), 'anim_radar_05': (0.0, 0.0, 1.0)}
SPIN_STEPS = 8
RADAR_FRAMES = {'anim_radar_01': 1000, 'anim_radar_02': 600, 'anim_radar_03': 600, 'anim_radar_04': 1000, 'anim_radar_05': 1500}
HATCH_STATES = [('inactive', 1, 2), ('activating', 2, 20), ('active', 20, 21), ('deactivating', 21, 40)]
DOCKDOORS = {'anim_dockdoor_xs'}
WALK_PARTS = {'hcr_dock_well': 'part_dock_well'}
DOCKDOOR_OBS = []
DOCKDOOR_STATES = [('closed', 1, 2), ('opening', 2, 25), ('open', 25, 26), ('closing', 26, 50)]
DOCKDOOR_KEYS = [(1, 0.0, 0.0), (2, 0.0, 0.0), (9, -0.25, 0.0), (25, -0.25, -3.6), (26, -0.25, -3.6), (43, -0.25, 0.0), (50, 0.0, 0.0)]

layouts = bpy.propertyGroupLayouts
names_in = {g: {d['name'] for d in defs} for g, defs in layouts.items()}

src_rebuild = bpy.data.collections['HCP_rebuild']
src_cons = bpy.data.collections['HCP_rebuild_connections']
src_engines = bpy.data.collections.get('HCP_rebuild_engines')

out_col = bpy.data.collections.new('hcp_export_tmp')
bpy.context.scene.collection.children.link(out_col)


def set_geo_tags(ob, tags):
    for t in tags:
        setattr(ob.GeometryTags, t, True)


def copy_mesh(src, apply_transform=True):
    ob = src.copy()
    ob.data = src.data.copy()
    ob.animation_data_clear()
    for c in list(ob.users_collection):
        c.objects.unlink(ob)
    out_col.objects.link(ob)
    ob.parent = None
    if apply_transform:
        ob.data.transform(SHIFT @ src.matrix_world)
        ob.matrix_world = Matrix.Identity(4)
    else:
        ob.matrix_world = SHIFT @ src.matrix_world
    uvs = ob.data.uv_layers
    for i, uv in enumerate(list(uvs)):
        uv.name = 'uv1' if i == 0 else 'uv%d' % (i + 1)
    return ob


def join(objs, name):
    for o in bpy.context.view_layer.objects:
        o.select_set(False)
    for o in objs:
        o.select_set(True)
    act = objs[0]
    bpy.context.view_layer.objects.active = act
    with bpy.context.temp_override(active_object=act, object=act, selected_objects=objs, selected_editable_objects=objs):
        bpy.ops.object.join()
    act.name = name
    act.data.name = name
    return act


main_src = []
detail_src = []
anim_parts = []
cap_parts = []
walk_parts = []
for o in src_rebuild.all_objects:
    if o.type != 'MESH' or o.name in EXCLUDE:
        continue
    if o.name in RADARS:
        ob = copy_mesh(o, True)
        ob.name = RADARS[o.name]
        ob.data.name = ob.name
        rest = Matrix.Translation(RADAR_PIVOTS[ob.name]) @ Vector(RADAR_AXES[ob.name]).normalized().to_track_quat('Z', 'Y').to_matrix().to_4x4()
        ob.data.transform(rest.inverted())
        ob.matrix_world = rest
        anim_parts.append(ob)
    elif o.name in HATCHES:
        ob = copy_mesh(o, False)
        anim_parts.append(ob)
        HATCH_OBS[o.name] = ob
        if o.animation_data and o.animation_data.action:
            act = o.animation_data.action.copy()
            act.name = 'hcpkeep_' + o.name
            act.use_fake_user = True
            HATCH_ACTIONS[ob] = act
    elif o.name in DOCKDOORS:
        ob = copy_mesh(o, False)
        anim_parts.append(ob)
        DOCKDOOR_OBS.append(ob)
    elif o.name in WALK_PARTS:
        ob = copy_mesh(o, True)
        ob.name = WALK_PARTS[o.name]
        ob.data.name = ob.name
        walk_parts.append(ob)
    elif o.name in DETAIL:
        detail_src.append(copy_mesh(o, True))
    elif o.name in CAPS:
        cap = copy_mesh(o, True)
        anim_parts.append(cap)
        cap_parts.append(cap)
    else:
        main_src.append(copy_mesh(o, True))

part_main = join(main_src, 'part_main')
detail = join(detail_src, 'detail_s_main')
set_geo_tags(detail, ['detail_s', 'forceoutline', 'nocollision'])
for ob in anim_parts:
    set_geo_tags(ob, ['detail_xl', 'forceoutline', 'nocollision'])
for ob in cap_parts:
    set_geo_tags(ob, ['noshadowcaster'])
for ob in walk_parts:
    set_geo_tags(ob, ['detail_xl', 'forceoutline', 'platformcollision'])
engine_parts = []
for o in (src_engines.objects if src_engines else []):
    if o.type != 'MESH':
        continue
    ob = copy_mesh(o, not o.name.startswith('anim_flame'))
    set_geo_tags(ob, [t for t in (o.get('tags') or '').split() if t != 'part'])
    engine_parts.append(ob)
src_pos = bpy.data.collections.get('HCP_rebuild_poslights')
POS_BLINK = {}
for o in (src_pos.objects if src_pos else []):
    if o.type != 'MESH':
        continue
    ob = copy_mesh(o, False)
    set_geo_tags(ob, [t for t in (o.get('tags') or '').split() if t != 'part'])
    POS_BLINK[ob] = json.loads(o['blink'])
for ob in [part_main, detail] + anim_parts + walk_parts + engine_parts + list(POS_BLINK):
    add_vertex_data(ob)

for idx, ratio in LODS:
    lod = part_main.copy()
    lod.data = part_main.data.copy()
    out_col.objects.link(lod)
    lod.name = 'part_main.LOD%d' % idx
    lod.data.name = lod.name
    m = lod.modifiers.new('Decimate', 'DECIMATE')
    m.decimate_type = 'COLLAPSE'
    m.ratio = ratio
    bpy.context.view_layer.objects.active = lod
    with bpy.context.temp_override(active_object=lod, object=lod):
        bpy.ops.object.modifier_apply(modifier=m.name)

wreck = bpy.data.objects['part_main.LOD2'].copy()
wreck.data = bpy.data.objects['part_main.LOD2'].data.copy()
out_col.objects.link(wreck)
wreck.name = 'part_main.wreck'
wreck.data.name = wreck.name

TAG_OVERRIDE = {}
EXTRA_CONS = []
EXPORT_RCS = False
TAG_GROUPS = [g for g in ('ConnectionTags', 'NPC ConnectionTags', 'Symmetry') if g in names_in]
GEO_TAGS = names_in.get('GeometryTags', set())


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


cons = []
rcs = []
for o in src_cons.objects:
    if o.type != 'EMPTY':
        continue
    if o.name.startswith('rcs_'):
        rcs.append(o)
        continue
    name = o.get('x4_name') or o.name
    e = bpy.data.objects.new(name, None)
    out_col.objects.link(e)
    e.empty_display_type = 'ARROWS'
    e.empty_display_size = 2.0
    e.matrix_world = SHIFT @ o.matrix_world
    apply_tags(e, TAG_OVERRIDE.get(name, o.get('tags') or ''))
    grp = o.get('group') or ''
    if grp:
        e.groups = grp + ' '
    if 'dynamicroom' in (o.get('tags') or ''):
        e.value = -1
    cons.append(e)
    leaves = VLS_HATCHES.get(name)
    if leaves:
        e_world = SHIFT @ o.matrix_world
        dname = 'anim_dummy_turrethatch_' + name[len('con_turret_'):]
        dme = bpy.data.meshes.new(dname)
        h = HATCH_DUMMY_SIZE / 2.0
        dme.from_pydata([(x, y, z) for x in (-h, h) for y in (-h, h) for z in (-h, h)], [], [(0, 1, 3, 2), (4, 6, 7, 5), (0, 4, 5, 1), (2, 3, 7, 6), (0, 2, 6, 4), (1, 5, 7, 3)])
        dme.uv_layers.new(name='uv1')
        dme.materials.append(bpy.data.materials['generic.generic_p1_hulltexture'])
        dummy = bpy.data.objects.new(dname, dme)
        out_col.objects.link(dummy)
        dummy.parent = e
        dummy.matrix_parent_inverse = Matrix.Identity(4)
        dummy.Meshflags.hidden = True
        add_vertex_data(dummy)
        for leaf in leaves:
            hob = HATCH_OBS[leaf]
            hatch_world = hob.matrix_basis.copy()
            hob.parent = dummy
            hob.matrix_parent_inverse = e_world.inverted()
            hob.matrix_basis = hatch_world

for name, tagstr, pos in EXTRA_CONS:
    e = bpy.data.objects.new(name, None)
    out_col.objects.link(e)
    e.empty_display_type = 'ARROWS'
    e.empty_display_size = 2.0
    e.location = pos
    apply_tags(e, tagstr)
    cons.append(e)

with bpy.data.libraries.load(LIB, link=True, relative=True) as (src, dst):
    dst.meshes = ['anim_thruster_00']
thr = dst.meshes[0]
for o in (sorted(rcs, key=lambda x: x.name) if EXPORT_RCS else []):
    ob = bpy.data.objects.new('anim_thruster_00', thr)
    out_col.objects.link(ob)
    ob.matrix_world = SHIFT @ o.matrix_world
    ob.GeometryTags.animation = True


with bpy.data.libraries.load(ENGINE_BODY_LIB, link=True, relative=True) as (src, dst):
    dst.meshes = ['part_main']
body_mesh = dst.meshes[0]
engine_bodies = []
for i, o in enumerate(sorted((c for c in src_cons.objects if (c.get('x4_name') or '').startswith('con_engine_')), key=lambda c: c['x4_name'])):
    ob = bpy.data.objects.new('part_main.%03d' % (951 + i), body_mesh)
    out_col.objects.link(ob)
    ob.matrix_world = SHIFT @ o.matrix_world
    set_geo_tags(ob, ENGINE_BODY_TAGS)
    engine_bodies.append(ob)

src_ck = bpy.data.collections.get('HCP_rebuild_cockpit')
ck_map = {}
if src_ck:
    for o in src_ck.objects:
        if o.type == 'MESH':
            ob = o.copy()
            if not o.data.library:
                ob.data = o.data.copy()
            ob.animation_data_clear()
            for c in list(ob.users_collection):
                c.objects.unlink(ob)
            out_col.objects.link(ob)
            for uv in list(ob.data.uv_layers)[:1] if not o.data.library else []:
                uv.name = 'uv1'
        else:
            ob = bpy.data.objects.new('tmp_' + o.name, None)
            out_col.objects.link(ob)
            ob.empty_display_type = 'ARROWS'
            ob.empty_display_size = 0.5
            tagstr = o.get('tags') or ''
            for t in tagstr.split():
                g = next((g for g in TAG_GROUPS if t in names_in[g]), None)
                if g:
                    setattr(getattr(ob, g), t, True)
        if o.groups:
            ob.groups = o.groups
        ck_map[o] = ob
    for o, ob in ck_map.items():
        if o.parent in ck_map:
            ob.parent = ck_map[o.parent]
            ob.matrix_parent_inverse = Matrix.Identity(4)
            ob.matrix_basis = o.matrix_basis.copy()
        else:
            ob.parent = None
            ob.matrix_world = SHIFT @ o.matrix_world
    for o, ob in ck_map.items():
        if o.type == 'MESH' and not o.data.library:
            add_vertex_data(ob)
    ck_final = [(ob, ('%s.%03d' % (o.data.name, 900 + i)) if (o.data is not None and o.data.library) else (o.get('x4_part') or o.get('x4_name') or o.name)) for i, (o, ob) in enumerate(ck_map.items())]
else:
    ck_final = []

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
    if not a.name.startswith('hcpkeep_'):
        bpy.data.actions.remove(a)
bpy.data.orphans_purge(do_local_ids=True, do_linked_ids=False, do_recursive=True)
for ob, nm in ck_final:
    ob.name = nm
    if ob.data is not None and not ob.data.library:
        ob.data.name = nm
ck_names = {ob.name for ob, nm in ck_final}
for i, ob in enumerate(engine_bodies):
    ob.name = 'part_main.%03d' % (951 + i)
import re
for o in list(scene.objects):
    if (o.data is not None and o.data.library) or '.LOD' in o.name or o.name in ck_names:
        continue
    m = re.match(r'^(.*)\.\d{3}$', o.name)
    if m:
        o.name = m.group(1)
        if o.data is not None:
            o.data.name = o.name
def key_all(ob, act, frames_values):
    ob.animation_data.action = act
    for f, rot in frames_values:
        ob.rotation_euler = rot
        ob.keyframe_insert('rotation_euler', frame=f)
    for fc in act.fcurves:
        for kp in fc.keyframe_points:
            kp.interpolation = 'LINEAR'
    ob.animation_data.action = None


for nm, end in RADAR_FRAMES.items():
    ob = scene.objects[nm]
    ob.GeometryTags.animation = True
    ob.animation_data_create()
    ob.rotation_mode = 'ZYX'
    x0, y0, z0 = ob.matrix_world.to_euler('ZYX')
    act = bpy.data.actions.new(nm + '_spin')
    key_all(ob, act, [(1 + (end - 1) * i / SPIN_STEPS, (x0, y0, z0 + 2.0 * math.pi * i / SPIN_STEPS)) for i in range(SPIN_STEPS + 1)])
    ob.rotation_euler = (x0, y0, z0)
    tr = ob.animation_data.nla_tracks.new()
    tr.name = 'generic'
    st = tr.strips.new('loop_random', 1, act)
    st.name = 'loop_random'
    print('ANIM', nm, 'strip', st.frame_start, st.frame_end, 'keys', len(act.fcurves), 'axis', tuple(round(v, 3) for v in (ob.matrix_world.to_3x3() @ Vector((0, 0, 1)))))
for ob, src_act in HATCH_ACTIONS.items():
    ob.GeometryTags.animation = True
    ob.animation_data_create()
    ob.animation_data.action = None
    tilt = ob.rotation_euler[0]
    w = ob.matrix_basis.copy()
    ob.data.transform(Matrix.Rotation(math.pi / 2.0, 4, 'X'))
    ob.rotation_mode = 'ZYX'
    ob.matrix_basis = Matrix.Translation(w.to_translation()) @ Matrix.Rotation(tilt, 4, 'X') @ Matrix.Rotation(-math.pi / 2.0, 4, 'X')
    hinge = next(fc for fc in src_act.fcurves if fc.data_path == 'rotation_euler' and fc.array_index == 1)
    x0 = ob.rotation_euler[0]
    act = bpy.data.actions.new(ob.name + '_hinge')
    key_all(ob, act, [(kp.co[0], (x0, 0.0, kp.co[1])) for kp in hinge.keyframe_points])
    ob.rotation_euler = (x0, 0.0, 0.0)
    tr = ob.animation_data.nla_tracks.new()
    tr.name = 'turrethatch'
    for nm, a, b in HATCH_STATES:
        st = tr.strips.new(nm, a, act)
        st.action_frame_start = a
        st.action_frame_end = b
        st.frame_end = b
        st.name = nm
    print('ANIM', ob.name, [(s.name, s.frame_start, s.frame_end) for s in tr.strips], 'hinge keys', [(kp.co[0], round(kp.co[1], 3)) for kp in hinge.keyframe_points])
for ob in DOCKDOOR_OBS:
    ob.GeometryTags.animation = True
    ob.GeometryTags.anim_dockdoor = True
    ob.animation_data_create()
    rest = ob.matrix_world.copy()
    ob.rotation_mode = 'XYZ'
    act = bpy.data.actions.new(ob.name + '_door')
    ob.animation_data.action = act
    for f, lift, slide in DOCKDOOR_KEYS:
        ob.matrix_world = Matrix.Translation(rest.to_3x3() @ Vector((-slide, 0.0, lift))) @ rest
        ob.keyframe_insert('location', frame=f)
        ob.keyframe_insert('rotation_euler', frame=f)
    for fc in act.fcurves:
        for kp in fc.keyframe_points:
            kp.interpolation = 'LINEAR'
    ob.animation_data.action = None
    ob.matrix_world = rest
    tr = ob.animation_data.nla_tracks.new()
    tr.name = 'dockingbay'
    for nm, a, b in DOCKDOOR_STATES:
        st = tr.strips.new(nm, a, act)
        st.action_frame_start = a
        st.action_frame_end = b
        st.frame_end = b
        st.name = nm
    print('ANIM', ob.name, [(s.name, s.frame_start, s.frame_end) for s in tr.strips], 'fcurves', len(act.fcurves))
for ob, blink in POS_BLINK.items():
    warp = ob.modifiers.new('UVWarp', 'UV_WARP')
    warp.uv_layer = 'uv1'
    ob.animation_data_create()
    act = bpy.data.actions.new(ob.name + '_blink')
    ob.animation_data.action = act
    for f, u in blink:
        warp.offset = (u, 0.0)
        ob.keyframe_insert('modifiers["UVWarp"].offset', index=0, frame=f)
        ob.keyframe_insert('rotation_euler', frame=f)
    for fc in act.fcurves:
        for kp in fc.keyframe_points:
            kp.interpolation = 'LINEAR'
    ob.animation_data.action = None
    warp.offset = (0.0, 0.0)
    tr = ob.animation_data.nla_tracks.new()
    tr.name = 'generic'
    st = tr.strips.new('loop', 1, act)
    st.name = 'loop'
    print('ANIM', ob.name, 'strip', st.frame_start, st.frame_end, 'keys', len(blink))
for ob in engine_parts:
    if not ob.name.startswith('anim_flame'):
        continue
    ob.GeometryTags.animation = True
    warp = ob.modifiers.new('UVWarp', 'UV_WARP')
    warp.uv_layer = 'uv1'
    ob.animation_data_create()
    act = bpy.data.actions.new(ob.name + '_loop')
    ob.animation_data.action = act
    for f, u in FLAME_UV_KEYS:
        warp.offset = (u, 0.0)
        ob.keyframe_insert('modifiers["UVWarp"].offset', index=0, frame=f)
        ob.keyframe_insert('rotation_euler', frame=f)
    for fc in act.fcurves:
        for kp in fc.keyframe_points:
            kp.interpolation = 'LINEAR'
    ob.animation_data.action = None
    warp.offset = (0.0, 0.0)
    tr = ob.animation_data.nla_tracks.new()
    tr.name = 'generic'
    st = tr.strips.new('loop', 1, act)
    st.name = 'loop'
    print('ANIM', ob.name, 'strip', st.frame_start, st.frame_end, 'fcurves', len(act.fcurves))
print('ENGINES', [(o.name, o.data.library is not None) for o in engine_bodies], [o.name for o in engine_parts])
scene.classAttr = 'ship_m'
scene.name = 'ship_arg_l_hcp_01'

import os
os.makedirs(os.path.dirname(COL_OBJ), exist_ok=True)
for o in scene.objects:
    o.select_set(o == part_main or o in cap_parts)
bpy.context.view_layer.objects.active = part_main
bpy.ops.wm.obj_export(filepath=COL_OBJ, export_selected_objects=True, forward_axis='Y', up_axis='Z', export_materials=False, export_uv=False, export_normals=False)

bpy.ops.wm.save_as_mainfile(filepath=OUT, relative_remap=True)

def tris(o):
    return sum(len(p.vertices) - 2 for p in o.data.polygons)
for o in sorted(scene.objects, key=lambda o: o.name):
    if o.type == 'MESH':
        print('BUILT', o.name, 'tris', tris(o), 'dims', tuple(round(v, 1) for v in o.dimensions), 'mats', [m.name for m in o.data.materials], 'lib', bool(o.data.library))
print('BUILT connections', len(cons), 'rcs', len(rcs))
for e in sorted(cons, key=lambda e: e.name):
    tg = [t for g in TAG_GROUPS for t in names_in[g] if getattr(getattr(e, g), t)]
    print('CON', e.name, tg, e.get('extratags'), repr(e.groups), e.value)
