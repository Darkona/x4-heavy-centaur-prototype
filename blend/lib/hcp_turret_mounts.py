import bpy
import bmesh
import json
import re
import sys
import numpy as np
from pathlib import Path
from mathutils import Matrix

LIB = Path(__file__).resolve().parent
POINTS = LIB / 'hcp_turret_points.json'
SOURCE = Path.home() / 'development/x4/heavy-centaur/publish/turret_hcp_final'
SOURCE_COLLECTION = 'turrets_hcp_on_ship'
SHIP_X = 420.0
UV_PER_M = 20.0 / 2048.0
SHELL_RATIO = 0.135
SHELL_INNER = 3.656
PIECES = {'socket': 'socket', 'shell': 'rear_shell', 'visor': 'visor'}
MATERIALS = {
    'argon_armor': 'generic.generic_p1_hullpattern',
    'argon_armor_light': 'generic.generic_p1_hullpattern',
    'argon_armor_dark': 'generic.generic_p1_hulltexture',
    'argon_edge': 'generic.generic_p1_hulltexture',
    'argon_mechanism': 'generic.generic_p1_hulltexture',
    'argon_recess': 'generic.generic_p1_hulltexture',
    'visor_cyan': 'p2generic.gen_p2_cockpitglassoutside_01',
    'visor_glass': 'p2generic.gen_p2_cockpitglassoutside_01',
}
PREFIX = 'hcr_turret_mount_'


def obj_verts(name):
    return np.array([[float(v) for v in line.split()[1:4]] for line in open(SOURCE / f'{name}.obj') if line.startswith('v ')])


def import_obj(name):
    before = set(bpy.data.objects)
    bpy.ops.wm.obj_import(filepath=str(SOURCE / f'{name}.obj'), forward_axis='Y', up_axis='Z')
    ob = next(o for o in bpy.data.objects if o not in before)
    me = ob.data
    bpy.data.objects.remove(ob, do_unlink=True)
    return me


def simplified_shell():
    me = import_obj(PIECES['shell'])
    ob = bpy.data.objects.new('shell_tmp', me)
    bpy.context.scene.collection.objects.link(ob)
    mod = ob.modifiers.new('decimate', 'DECIMATE')
    mod.ratio = SHELL_RATIO
    out = bpy.data.meshes.new_from_object(ob.evaluated_get(bpy.context.evaluated_depsgraph_get()))
    bpy.data.objects.remove(ob, do_unlink=True)
    for _ in range(10):
        low = [p for p in out.polygons if p.center.length < SHELL_INNER]
        if not low:
            break
        for p in low:
            f = SHELL_INNER / p.center.length
            for vi in p.vertices:
                v = out.vertices[vi]
                if v.co.length < SHELL_INNER + 0.1:
                    v.co *= f
        out.update()
    return out


def fit(src, ob):
    m = np.array(ob.matrix_world)
    world = np.array([m[:3, :3] @ np.array(v.co) + m[:3, 3] for v in ob.data.vertices])
    assert len(world) == len(src), ob.name
    ca = src.mean(0)
    cb = world.mean(0)
    x, *_ = np.linalg.lstsq(src - ca, world - cb, rcond=None)
    rot = x.T
    u, _, vt = np.linalg.svd(rot)
    rot = u @ vt
    err = np.abs((src - ca) @ rot.T + cb - world).max()
    return rot, cb - rot @ ca, err


def source_pieces(path):
    with bpy.data.libraries.load(str(path), link=False) as (src, dst):
        dst.objects = [n for n in src.objects if re.match(r'turret_0\d(_|$)', n)]
    tmp = bpy.data.collections.new('turret_mounts_source_tmp')
    bpy.context.scene.collection.children.link(tmp)
    for ob in dst.objects:
        if ob is not None:
            tmp.objects.link(ob)
    bpy.context.view_layer.update()
    found = {}
    for ob in dst.objects:
        if ob is None or ob.type != 'MESH':
            continue
        n = ob.name[7:9]
        for key, stem in PIECES.items():
            if stem in ob.name:
                found.setdefault(n, {})[key] = ob
    return found, dst.objects


def signed_volume(me):
    total = 0.0
    for p in me.polygons:
        v = [me.vertices[i].co for i in p.vertices]
        for k in range(1, len(v) - 1):
            total += v[0].dot(v[k].cross(v[k + 1]))
    return total


def bake(me, local, outward, name, mats):
    data = me.copy()
    data.name = name
    data.transform(Matrix(local.tolist()))
    if (signed_volume(data) > 0) != outward:
        bm = bmesh.new()
        bm.from_mesh(data)
        bmesh.ops.reverse_faces(bm, faces=bm.faces[:])
        bm.to_mesh(data)
        bm.free()
    data.materials.clear()
    for m in mats:
        base = re.sub(r'\.\d{3}$', '', m)
        mat = bpy.data.materials.get(MATERIALS.get(base, base))
        assert mat is not None, m
        data.materials.append(mat)
    if not data.uv_layers:
        box_uv(data)
    return data


def box_uv(me):
    uvl = me.uv_layers.new(name='UVMap')
    for p in me.polygons:
        n = p.normal
        ax = max(range(3), key=lambda i: abs(n[i]))
        a, b = [i for i in range(3) if i != ax]
        for li in p.loop_indices:
            co = me.vertices[me.loops[li].vertex_index].co
            uvl.data[li].uv = (co[a] * UV_PER_M + 0.5, co[b] * UV_PER_M + 0.5)


def x4(v, point=False):
    return [round(float(v[0]) + (SHIP_X if point else 0.0), 4), round(float(v[2]), 4), round(float(v[1]), 4)]


def main():
    source = Path(sys.argv[sys.argv.index('--') + 1])
    rebuild = bpy.data.collections['HCP_rebuild']
    for o in list(bpy.data.objects):
        if o.name.startswith(PREFIX):
            bpy.data.objects.remove(o, do_unlink=True)
    shell_src = obj_verts(PIECES['shell'])
    shell = simplified_shell()
    outward = {}
    for key, stem in PIECES.items():
        me = import_obj(stem)
        outward[key] = signed_volume(me) > 0
        bpy.data.meshes.remove(me)
    found, loaded = source_pieces(source)
    cons = {o.get('x4_name') or o.name: o for o in bpy.data.collections['HCP_rebuild_connections'].objects}
    points = {}
    for n in sorted(found):
        pieces = found[n]
        rot, centre, err = fit(shell_src, pieces['shell'])
        mirror = np.linalg.det(rot) < 0
        frame = rot @ np.diag([-1.0, 1.0, 1.0]) if mirror else rot
        flip = np.diag([-1.0, 1.0, 1.0]) if mirror else np.eye(3)
        to_world = np.eye(4)
        to_world[:3, :3] = frame
        to_world[:3, 3] = centre
        to_local = np.linalg.inv(to_world)
        for key in ('socket', 'visor'):
            ob = pieces[key]
            local = to_local @ np.array(ob.matrix_world)
            name = f'{PREFIX}{n}_{key}'
            data = bake(ob.data, local, outward[key], name, [m.name for m in ob.data.materials if m])
            new = bpy.data.objects.new(name, data)
            rebuild.objects.link(new)
            new.matrix_world = Matrix(to_world.tolist())
        local = np.eye(4)
        local[:3, :3] = flip
        name = f'{PREFIX}{n}_shell'
        data = bake(shell, local, outward['shell'], name, ['argon_armor'])
        new = bpy.data.objects.new(name, data)
        rebuild.objects.link(new)
        new.matrix_world = Matrix(to_world.tolist())
        y = frame[:, 1]
        z = frame[:, 2]
        con = np.eye(4)
        con[:3, 0] = np.cross(-z, y)
        con[:3, 1] = -z
        con[:3, 2] = y
        con[:3, 3] = centre
        e = cons.get(f'con_turret_{n}') or cons.get(f'rb_con_turret_{n}')
        if e is None:
            raise SystemExit(f'no con_turret_{n} empty')
        e.matrix_world = Matrix(con.tolist())
        points[f'turret_{n}'] = {'centre_x4': x4(centre, True), 'axis_out_x4': x4(y), 'z_axis_x4': x4(z), 'mirrored': bool(mirror)}
        print('MOUNT', n, 'centre_x4', points[f'turret_{n}']['centre_x4'], 'mirrored', bool(mirror), 'shell fit err', round(float(err), 4))
    for ob in loaded:
        if ob is not None:
            bpy.data.objects.remove(ob, do_unlink=True)
    bpy.data.collections.remove(bpy.data.collections['turret_mounts_source_tmp'])
    bpy.data.meshes.remove(shell)
    bpy.data.orphans_purge(do_local_ids=True, do_linked_ids=True, do_recursive=True)
    POINTS.write_text(json.dumps(points, indent=1) + '\n')
    bpy.ops.wm.save_mainfile()


main()
