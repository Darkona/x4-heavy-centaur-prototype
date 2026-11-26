import bpy
import json
import os
from pathlib import Path
from mathutils import Matrix, Vector

LIB = Path(__file__).resolve().parent
POINTS = LIB / 'hcp_turret_points.json'
SOURCE = Path.home() / 'development/x4/heavy-centaur/publish/turret_hcp_final'
SHIP_X = 420.0
UV_PER_M = 20.0 / 2048.0
PIECES = {
    'socket': ('socket.obj', 'p2generic.gen_p2_hulltexture_01'),
    'shell': ('rear_shell.obj', 'p2generic.gen_p2_hulltexture_01'),
    'visor': ('visor.obj', 'p2generic.gen_p2_cockpitglassoutside_01'),
}
PREFIX = 'hcr_turret_mount_'


def blender_vec(v):
    return Vector((v[0], v[2], v[1]))


def frames(point):
    c = point['centre_x4']
    centre = Vector((c[0] - SHIP_X, c[2], c[1]))
    y = blender_vec(point['axis_out_x4']).normalized()
    z = blender_vec(point['z_axis_x4'])
    z = (z - y * z.dot(y)).normalized()
    mount = Matrix((y.cross(z), y, z)).transposed().to_4x4()
    mount.translation = centre
    con_y = -z
    con_z = y
    con = Matrix((con_y.cross(con_z), con_y, con_z)).transposed().to_4x4()
    con.translation = centre
    return mount, con


def box_uv(me):
    if not me.uv_layers:
        me.uv_layers.new(name='UVMap')
    uvl = me.uv_layers[0]
    for p in me.polygons:
        n = p.normal
        ax = max(range(3), key=lambda i: abs(n[i]))
        a, b = [i for i in range(3) if i != ax]
        for li in p.loop_indices:
            co = me.vertices[me.loops[li].vertex_index].co
            uvl.data[li].uv = (co[a] * UV_PER_M + 0.5, co[b] * UV_PER_M + 0.5)


def template(key):
    fname, mat_name = PIECES[key]
    before = set(bpy.data.objects)
    bpy.ops.wm.obj_import(filepath=str(SOURCE / fname), forward_axis='Y', up_axis='Z')
    new = [o for o in bpy.data.objects if o not in before]
    assert len(new) == 1, (fname, [o.name for o in new])
    me = new[0].data.copy()
    bpy.data.objects.remove(new[0], do_unlink=True)
    me.materials.clear()
    mat = bpy.data.materials.get(mat_name)
    assert mat is not None, mat_name
    me.materials.append(mat)
    for uv in list(me.uv_layers):
        me.uv_layers.remove(uv)
    box_uv(me)
    return me


def main():
    points = json.loads(POINTS.read_text())
    rebuild = bpy.data.collections['HCP_rebuild']
    for o in list(bpy.data.objects):
        if o.name.startswith(PREFIX):
            bpy.data.objects.remove(o, do_unlink=True)
    meshes = {k: template(k) for k in PIECES}
    cons = {o.get('x4_name') or o.name: o for o in bpy.data.collections['HCP_rebuild_connections'].objects}
    for slot, point in sorted(points.items()):
        n = slot.split('_')[-1]
        mount, con = frames(point)
        for key, me in meshes.items():
            name = f'{PREFIX}{n}_{key}'
            data = me.copy()
            data.name = name
            ob = bpy.data.objects.new(name, data)
            rebuild.objects.link(ob)
            ob.matrix_world = mount
        e = cons.get(f'con_turret_{n}') or cons.get(f'rb_con_turret_{n}')
        if e is None:
            raise SystemExit(f'no con_turret_{n} empty')
        e.matrix_world = con
        print('MOUNT', n, 'centre', tuple(round(v, 3) for v in mount.translation), 'empty', e.name)
    for me in meshes.values():
        bpy.data.meshes.remove(me)
    bpy.ops.wm.save_mainfile()


main()
