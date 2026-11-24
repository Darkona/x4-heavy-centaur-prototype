import bpy
import bmesh
import json
import itertools
from mathutils import Vector

PROTECT = '/home/darkona/development/x4/heavy-centaur/blend/lib/vhacd/protect.json'
MIN_VOLUME = 0.05
SAMPLE_STEP = 0.5


def hull_bm(points):
    bm = bmesh.new()
    for p in points:
        bm.verts.new(p)
    if len(bm.verts) < 4:
        return bm
    res = bmesh.ops.convex_hull(bm, input=list(bm.verts))
    bmesh.ops.delete(bm, geom=[v for v in res['geom_interior'] if isinstance(v, bmesh.types.BMVert)], context='VERTS')
    loose = [v for v in bm.verts if not v.link_faces]
    if loose:
        bmesh.ops.delete(bm, geom=loose, context='VERTS')
    bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))
    return bm


def clip(points, co, no):
    bm = hull_bm(points)
    if len(bm.faces) < 4:
        bm.free()
        return []
    geom = list(bm.verts) + list(bm.edges) + list(bm.faces)
    bmesh.ops.bisect_plane(bm, geom=geom, dist=1e-5, plane_co=co, plane_no=no, clear_outer=True)
    pts = [v.co.copy() for v in bm.verts]
    bm.free()
    return pts


def volume(points):
    bm = hull_bm(points)
    v = bm.calc_volume() if len(bm.faces) >= 4 else 0.0
    bm.free()
    return abs(v)


def overlaps(points, box):
    lo, hi = box
    for i in range(3):
        if max(p[i] for p in points) <= lo[i] + 1e-4 or min(p[i] for p in points) >= hi[i] - 1e-4:
            return False
    return True


def subtract_box(points, box):
    lo, hi = box
    if not overlaps(points, box):
        return [points]
    out = []
    rest = points
    for i in range(3):
        a = Vector((0, 0, 0))
        a[i] = 1.0
        below = clip(rest, Vector(lo), a)
        if below and volume(below) > MIN_VOLUME:
            out.append(below)
        above = clip(rest, Vector(hi), -a)
        if above and volume(above) > MIN_VOLUME:
            out.append(above)
        rest = clip(rest, Vector(lo), -a)
        rest = clip(rest, Vector(hi), a) if rest else []
        if not rest:
            break
    return out


def inside(planes, p):
    return all(n.dot(p) - d < -1e-4 for n, d in planes)


def hull_planes(points):
    bm = hull_bm(points)
    pl = [(f.normal.copy(), f.normal.dot(f.verts[0].co)) for f in bm.faces]
    bm.free()
    return pl


def main():
    boxes = json.load(open(PROTECT))
    hc = bpy.data.collections['Hulls']
    src = sorted(hc.objects, key=lambda o: int(o.name.rsplit('_', 1)[1]) if o.name.rsplit('_', 1)[1].isdigit() else 0)
    pieces = []
    for o in src:
        pts = [o.matrix_world @ v.co for v in o.data.vertices]
        cur = [pts]
        for name, b in boxes.items():
            nxt = []
            for c in cur:
                nxt.extend(subtract_box(c, (b[0], b[1])))
            cur = nxt
        pieces.extend(cur)
    for o in list(hc.objects):
        bpy.data.objects.remove(o, do_unlink=True)
    for m in list(bpy.data.meshes):
        if m.users == 0:
            bpy.data.meshes.remove(m)
    for i, pts in enumerate(pieces):
        bm = hull_bm(pts)
        me = bpy.data.meshes.new('part_main_hull_%d' % i)
        bm.to_mesh(me)
        bm.free()
        ob = bpy.data.objects.new(me.name, me)
        ob.display_type = 'WIRE'
        hc.objects.link(ob)
    print('CLIP hulls in', len(src), 'out', len(pieces), 'verts', sum(len(o.data.vertices) for o in hc.objects), 'max verts', max(len(o.data.vertices) for o in hc.objects))
    planes = [hull_planes([v.co for v in o.data.vertices]) for o in hc.objects]
    bad_total = 0
    for name, b in boxes.items():
        lo, hi = Vector(b[0]), Vector(b[1])
        n = [max(1, int((hi[i] - lo[i]) / SAMPLE_STEP)) for i in range(3)]
        bad = 0
        tot = 0
        for ix, iy, iz in itertools.product(range(n[0] + 1), range(n[1] + 1), range(n[2] + 1)):
            p = Vector((lo.x + 0.05 + (hi.x - lo.x - 0.1) * ix / n[0], lo.y + 0.05 + (hi.y - lo.y - 0.1) * iy / n[1], lo.z + 0.05 + (hi.z - lo.z - 0.1) * iz / n[2]))
            tot += 1
            if any(inside(pl, p) for pl in planes):
                bad += 1
        bad_total += bad
        print('CHECK', name, 'samples', tot, 'inside a hull', bad)
    print('CHECK total inside', bad_total)
    bpy.ops.wm.save_mainfile()


main()
