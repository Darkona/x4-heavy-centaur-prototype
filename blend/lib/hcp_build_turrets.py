import bpy
import bmesh
import json
import re
import math
import os
import sys
from mathutils import Matrix, Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from hcp_vdata import add_vertex_data

ARGS = sys.argv[sys.argv.index('--') + 1:]
SPEC = json.load(open(ARGS[0]))
UV_PER_M = 20.0 / 2048.0
MOUNT = ('con_turret', 'turret medium hittable component combat hcp_turret')
SPHERE_RADIUS = 3.65
BALL_MATERIALS = ('generic.generic_p1_hulltexture', 'p2generic.gen_p2_hulltexture_01')
BALL_UV_PER_M = 0.0067
SWAP = Matrix(((1, 0, 0, 0), (0, 0, 1, 0), (0, 1, 0, 0), (0, 0, 0, 1)))
MATERIALS = {
    'argon_armor': 'generic.generic_p1_hullpattern',
    'argon_armor_light': 'generic.generic_p1_hullpattern',
    'argon_armor_dark': 'generic.generic_p1_hulltexture',
    'argon_edge': 'generic.generic_p1_hulltexture',
    'argon_mechanism': 'generic.generic_p1_hulltexture',
    'argon_recess': 'generic.generic_p1_hulltexture',
    'visor_glass': 'p2generic.gen_p2_cockpitglassoutside_01',
    'visor_sensor': 'generic.generic_p1_hulltexture',
}
PART_TAGS = {
    'part_base': ['forceoutline'],
    'part_rotator': ['iklink', 'nocollision', 'forceoutline'],
    'part_gun': ['iklink', 'nocollision', 'forceoutline'],
}
ORIGIN = (0.0, 0.0, 0.0)
HIDDEN_MATERIAL = 'generic.generic_p1_hulltexture'


def read_obj(path):
    verts = []
    colors = []
    uvs = []
    norms = []
    objects = []
    cur = None
    mat = None
    with open(path) as fh:
        for line in fh:
            if not line.strip() or line[0] == '#':
                continue
            tag, *rest = line.split()
            if tag == 'v':
                verts.append(tuple(float(v) for v in rest[:3]))
                colors.append(tuple(float(v) for v in reversed(rest[3:6])) if len(rest) >= 6 else (1.0, 1.0, 1.0))
            elif tag == 'vt':
                uvs.append((float(rest[0]), float(rest[1])))
            elif tag == 'vn':
                norms.append(tuple(float(v) for v in rest[:3]))
            elif tag in ('o', 'g'):
                cur = {'name': rest[0] if rest else 'obj', 'faces': []}
                objects.append(cur)
            elif tag == 'usemtl':
                mat = rest[0]
            elif tag == 'f':
                if cur is None:
                    cur = {'name': os.path.splitext(os.path.basename(path))[0], 'faces': []}
                    objects.append(cur)
                corners = []
                for c in rest:
                    idx = c.split('/')
                    vi = int(idx[0])
                    ti = int(idx[1]) if len(idx) > 1 and idx[1] else 0
                    ni = int(idx[2]) if len(idx) > 2 and idx[2] else 0
                    corners.append((vi - 1 if vi > 0 else len(verts) + vi, ti - 1 if ti > 0 else (len(uvs) + ti if ti else -1), ni - 1 if ni > 0 else (len(norms) + ni if ni else -1)))
                cur['faces'].append((corners, mat))
    return verts, uvs, norms, objects, colors


def material(name):
    base = re.sub(r'\.\d{3}$', '', name)
    name = MATERIALS.get(base, base)
    m = bpy.data.materials.get(name)
    return m or bpy.data.materials.new(name)


def build_mesh(name, data, obj, swap):
    verts, uvs, norms, _, colors = data
    sw = (lambda p: (p[0], p[2], p[1])) if swap else (lambda p: p)
    bm = bmesh.new()
    vmap = {}
    mats = []
    uv_layer = bm.loops.layers.uv.new('uv1')
    col_layer = bm.loops.layers.color.new('col')
    agree = 0
    total = 0
    for corners, mname in obj['faces']:
        bv = []
        for vi, ti, ni in corners:
            if vi not in vmap:
                vmap[vi] = bm.verts.new(sw(verts[vi]))
            bv.append(vmap[vi])
        if len(set(bv)) < 3:
            continue
        try:
            f = bm.faces.new(bv)
        except ValueError:
            continue
        mname = mname or 'generic.generic_p1_hulltexture'
        if mname not in mats:
            mats.append(mname)
        f.material_index = mats.index(mname)
        for loop, (vi, ti, ni) in zip(f.loops, corners):
            if ti >= 0:
                loop[uv_layer].uv = uvs[ti]
        for loop, (vi, ti, ni) in zip(f.loops, corners):
            loop[col_layer] = (*colors[vi], 1.0)
        if norms and corners[0][2] >= 0:
            f.normal_update()
            n = Vector((0.0, 0.0, 0.0))
            for _, _, ni in corners:
                n += Vector(sw(norms[ni]))
            total += 1
            agree += 1 if f.normal.dot(n) > 0 else 0
    if total and agree < total / 2:
        bmesh.ops.reverse_faces(bm, faces=bm.faces[:])
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    for m in mats:
        me.materials.append(material(m))
    if not uvs:
        box_uv(me)
    ob = bpy.data.objects.new(name, me)
    return ob


def box_uv(me, per_m=UV_PER_M):
    if not me.uv_layers:
        me.uv_layers.new(name='uv1')
    uvl = me.uv_layers[0]
    for p in me.polygons:
        n = p.normal
        ax = max(range(3), key=lambda i: abs(n[i]))
        a, b = [i for i in range(3) if i != ax]
        for li in p.loop_indices:
            co = me.vertices[me.loops[li].vertex_index].co
            uvl.data[li].uv = (co[a] * per_m + 0.5, co[b] * per_m + 0.5)


def load_pieces(paths):
    out = []
    for path in paths:
        data = read_obj(path)
        for obj in data[3]:
            ob = build_mesh(obj['name'], data, obj, swap=False)
            bpy.context.scene.collection.objects.link(ob)
            out.append(ob)
    return out


def join_copies(objs, name, frame, origin):
    deps = bpy.context.evaluated_depsgraph_get()
    copies = []
    for o in objs:
        me = bpy.data.meshes.new_from_object(o.evaluated_get(deps))
        me.transform(frame @ o.matrix_world)
        if not me.uv_layers:
            box_uv(me)
        me.uv_layers[0].name = 'uv1'
        for i, m in enumerate(me.materials):
            if m is not None:
                me.materials[i] = material(m.name)
        c = bpy.data.objects.new(o.name + '_copy', me)
        bpy.context.scene.collection.objects.link(c)
        copies.append(c)
    return join(copies, name, origin)


def join(objs, name, origin):
    bpy.context.view_layer.update()
    for o in bpy.context.scene.objects:
        o.select_set(False)
    for o in objs:
        if o.name not in bpy.context.scene.collection.objects:
            bpy.context.scene.collection.objects.link(o)
        o.data.transform(o.matrix_world)
        o.parent = None
        o.matrix_world = Matrix.Identity(4)
        o.select_set(True)
    bpy.context.view_layer.objects.active = objs[0]
    if len(objs) > 1:
        bpy.ops.object.join()
    ob = bpy.context.view_layer.objects.active
    ob.data.transform(Matrix.Translation(-Vector(origin)))
    ob.location = origin
    ob.name = name
    ob.data.name = name
    return ob


layouts = None
names_in = None
TAG_GROUPS = None


def tag_setup():
    global layouts, names_in, TAG_GROUPS
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


def empty(name, tags, loc=(0.0, 0.0, 0.0), parent=None):
    e = bpy.data.objects.new(name, None)
    e.empty_display_type = 'ARROWS'
    e.empty_display_size = 0.5
    bpy.context.scene.collection.objects.link(e)
    if parent is not None:
        e.parent = parent
        e.matrix_parent_inverse = Matrix.Identity(4)
    e.location = loc
    apply_tags(e, tags)
    return e


def limit(ob, x=None, y=None, z=None):
    c = ob.constraints.new('LIMIT_ROTATION')
    c.owner_space = 'LOCAL'
    for axis, rng in (('x', x), ('y', y), ('z', z)):
        if rng is None:
            setattr(c, 'use_limit_' + axis, False)
        else:
            setattr(c, 'use_limit_' + axis, True)
            setattr(c, 'min_' + axis, math.radians(rng[0]))
            setattr(c, 'max_' + axis, math.radians(rng[1]))


def hidden_part(name, shape, size):
    bm = bmesh.new()
    if shape == 'sphere':
        bmesh.ops.create_icosphere(bm, subdivisions=2, radius=size)
    else:
        bmesh.ops.create_cube(bm, size=size)
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    me.materials.append(material(HIDDEN_MATERIAL))
    box_uv(me)
    me.uv_layers[0].name = 'uv1'
    ob = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(ob)
    ob.Meshflags.hidden = True
    return ob


def hull_material(me):
    me.materials.clear()
    for name in BALL_MATERIALS:
        me.materials.append(material(name))
    for p in me.polygons:
        p.material_index = len(BALL_MATERIALS) - 1
    for uv in list(me.uv_layers):
        me.uv_layers.remove(uv)
    box_uv(me, BALL_UV_PER_M)


def x4_matrix(rows):
    return SWAP @ Matrix(rows) @ SWAP


def part_mesh(q):
    data = read_obj(q['obj'])
    ob = build_mesh(q['name'], data, data[3][0], swap=True)
    bpy.context.scene.collection.objects.link(ob)
    return ob


def set_geometry_tags(ob, tags):
    for tg in tags:
        if hasattr(ob.GeometryTags, tg):
            setattr(ob.GeometryTags, tg, True)


def build(t):
    for o in list(bpy.data.objects):
        bpy.data.objects.remove(o, do_unlink=True)
    bpy.data.orphans_purge(do_local_ids=True, do_linked_ids=True, do_recursive=True)
    tag_setup()
    ball_src = load_pieces([SPEC['ball']])
    keep_src = set(bpy.data.objects)
    base = hidden_part('part_base', 'sphere', SPHERE_RADIUS - 0.1)
    rotator = hidden_part('part_rotator', 'cube', 0.17)
    ball = join_copies(ball_src, 'ball_tmp', Matrix.Identity(4), ORIGIN)
    hull_material(ball.data)
    merged = [part_mesh(q) for q in t['parts'] if q['merged']]
    gun = join([ball] + merged, 'part_gun', ORIGIN)
    rotator.parent = base
    rotator.matrix_parent_inverse = Matrix.Identity(4)
    rotator.location = ORIGIN
    gun.parent = rotator
    gun.matrix_parent_inverse = Matrix.Identity(4)
    gun.location = ORIGIN
    gun.rotation_euler = (math.radians(90.0), 0.0, 0.0)
    limit(rotator, x=(0, 0), y=(0, 0), z=None)
    limit(gun, x=(-1, 91), y=(0, 0), z=(0, 0))
    objects = {'part_gun': gun}
    pending = [q for q in t['parts'] if not q['merged']]
    while pending:
        q = next(q for q in pending if q['parent'] in objects)
        pending.remove(q)
        ob = part_mesh(q)
        ob.parent = objects[q['parent']]
        ob.matrix_parent_inverse = Matrix.Identity(4)
        ob.matrix_basis = x4_matrix(q['frame'])
        set_geometry_tags(ob, q['tags'])
        objects[q['name']] = ob
    for s in t['shooters']:
        e = empty(s['name'], 'laser', ORIGIN, parent=objects[s['parent']])
        e.matrix_basis = x4_matrix(s['frame'])
    empty(MOUNT[0], MOUNT[1], ORIGIN)
    empty('con_aimtarget_01', 'aimtarget', ORIGIN)
    cont = empty('container', 'contents')
    cont.value = 0
    meshes = [base, rotator] + list(objects.values())
    for o in meshes:
        add_vertex_data(o)
    ours = set(meshes) | {o for o in bpy.context.scene.objects if o.type == 'EMPTY' and o not in keep_src}
    for o in list(bpy.data.objects):
        if o not in ours:
            bpy.data.objects.remove(o, do_unlink=True)
    scene = bpy.context.scene
    for s in list(bpy.data.scenes):
        if s != scene:
            bpy.data.scenes.remove(s)
    for c in list(bpy.data.collections):
        bpy.data.collections.remove(c)
    for o in ours:
        if o.name not in scene.collection.objects:
            scene.collection.objects.link(o)
    for a in list(bpy.data.actions):
        bpy.data.actions.remove(a)
    for tx in list(bpy.data.texts):
        bpy.data.texts.remove(tx)
    bpy.data.orphans_purge(do_local_ids=True, do_linked_ids=True, do_recursive=True)
    for nm, tags in PART_TAGS.items():
        for tg in tags:
            setattr(scene.objects[nm].GeometryTags, tg, True)
    scene.classAttr = 'turret'
    scene.name = t['component']
    out = os.path.join(SPEC['out_dir'], t['component'] + '.blend')
    os.makedirs(SPEC['out_dir'], exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=out, relative_remap=True)
    print(f"TURRET {t['component']}: parts {[o.name for o in meshes]}, {len(t['shooters'])} shooters, gun {len(gun.data.vertices)} v")


for turret in SPEC['turrets']:
    build(turret)
