import bpy
import bmesh
import math
from mathutils import Vector

NAME = "hcr_bow_bulb_core"
MAT = "generic.generic_p1_hullpattern"
ORIGIN = Vector((-420.0, 0.0, 0.0))
TAN_A = 0.24
TAN_B = 0.6
STRIP_SEGS = 8
BEVEL_W = 0.25
BEVEL_MIN_DEG = 6.0
HOLE_04_R = 5.6
PART_FLAT = 1
PART_STRIP = 2
PART_BEVEL = 3
PART_CAP = 4

FLANK_N = Vector((0.99997, -0.00771, 0.00245)).normalized()
FLANK_P = Vector((25.392, 88.495, -13.09))
SHIELD_N = Vector((0.0, -0.35332, -0.93550)).normalized()
SHIELD_P = Vector((0.0, 75.11, -23.43))
T04_N = Vector((0.0, 0.0112, -0.99994)).normalized()
T04_P = Vector((0.0, 97.506, -27.97))

STATIONS = [
    (53.0, -5.0, 5.6, -6.0, -12.0, 2.6, "shield", 0.8),
    (64.0, -0.1, 16.3, -3.4, -15.0, 7.0, "shield", 2.5),
    (75.5, -0.1, None, -4.2, -21.6, 11.0, "shield", 3.9),
    (87.43, -0.1, None, -4.2, -21.6, 11.0, "t04", 3.9),
    (99.0, -0.1, None, -4.2, -21.6, 11.0, "t04", 3.9),
    (106.0, -2.45, 19.5, -5.0, -21.0, 8.0, "t04", 3.0),
    (111.0, -6.5, 12.0, -8.6, -19.0, 5.0, -25.0, 2.0),
    (116.0, -9.0, 5.5, -10.0, -17.0, 2.5, -20.8, 0.8),
]


def plane_z(n, p, y):
    return p.z - n.y * (y - p.y) / n.z


def flank_x(y, z):
    return FLANK_P.x - (FLANK_N.y * (y - FLANK_P.y) + FLANK_N.z * (z - FLANK_P.z)) / FLANK_N.x


def half_section(st):
    y, zt, xf, zfu, zfl, a, zb, wb = st
    if zb == "shield":
        zb = plane_z(SHIELD_N, SHIELD_P, y)
    elif zb == "t04":
        zb = plane_z(T04_N, T04_P, y)
    x3 = flank_x(y, zfu) if xf is None else xf
    x4 = flank_x(y, zfl) if xf is None else xf
    p3 = (x3, zfu)
    p2 = (x3 - wb, zfu + wb * TAN_B)
    p1 = (p2[0] - (zt - p2[1]) / TAN_A, zt)
    if p1[0] <= 0.2:
        raise ValueError("top flat vanished at y %.2f" % y)
    pts = [(p1, PART_FLAT), (p2, PART_FLAT), (p3, PART_FLAT), ((x4, zfl), PART_FLAT)]
    b = zfl - zb
    cx = x4 - a
    for k in range(1, STRIP_SEGS + 1):
        t = -0.5 * math.pi * k / STRIP_SEGS
        pts.append(((cx + a * math.cos(t), zfl + b * math.sin(t)), PART_STRIP))
    return y, zt, zb, pts


def full_ring(st):
    y, zt, zb, half = half_section(st)
    ring = [((0.0, zt), PART_FLAT)]
    ring += half
    ring.append(((0.0, zb), PART_FLAT))
    ring += [((-p[0], p[1]), part) for p, part in reversed(half)]
    return y, [(Vector((p[0], y, p[1])), part) for p, part in ring]


def loft(bm, lay):
    rings = []
    for st in STATIONS:
        y, r = full_ring(st)
        rings.append(([bm.verts.new(p) for p, part in r], r))
    n = len(rings[0][0])
    for (va, ra), (vb, rb) in zip(rings, rings[1:]):
        for i in range(n):
            j = (i + 1) % n
            f = bm.faces.new((va[i], vb[i], vb[j], va[j]))
            strip = ra[i][1] == PART_STRIP and ra[j][1] == PART_STRIP
            first = ra[i][1] != ra[j][1] and (abs(ra[i][0].z - ra[j][0].z) > 1e-6) and (ra[i][1] == PART_STRIP or ra[j][1] == PART_STRIP)
            f[lay] = PART_STRIP if (strip or first) else PART_FLAT
    for k, verts in ((0, rings[0][0]), (len(rings) - 1, rings[-1][0])):
        c = sum((v.co for v in verts), Vector()) / len(verts)
        cv = bm.verts.new(c)
        for i in range(n):
            j = (i + 1) % n
            f = bm.faces.new((verts[j], verts[i], cv) if k == 0 else (verts[i], verts[j], cv))
            f[lay] = PART_CAP
    return rings


def fix_strip_tags(bm, lay):
    for f in bm.faces:
        if f[lay] != PART_STRIP:
            continue
        no = f.normal
        if abs(no.x) > 0.9995 or abs(no.z) > 0.9995:
            f[lay] = PART_FLAT


def orient(bm):
    bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))
    top = max(bm.faces, key=lambda f: f.calc_center_median().z)
    if top.normal.z < 0:
        bmesh.ops.reverse_faces(bm, faces=list(bm.faces))
    bm.normal_update()


def bevel_edges(bm, lay):
    lim = math.radians(BEVEL_MIN_DEG)
    edges = []
    for e in bm.edges:
        lf = e.link_faces
        if len(lf) != 2:
            continue
        if lf[0][lay] != PART_FLAT or lf[1][lay] != PART_FLAT:
            continue
        if e.calc_face_angle(0.0) > lim:
            edges.append(e)
    res = bmesh.ops.bevel(bm, geom=edges + list({v for e in edges for v in e.verts}), offset=BEVEL_W, offset_type="OFFSET", segments=2, profile=0.5, affect="EDGES", clamp_overlap=True)
    for f in res["faces"]:
        f[lay] = PART_BEVEL
    return len(edges)


def region_faces(bm, lay, n, p, tol=0.03, ymin=None, ymax=None):
    out = []
    for f in bm.faces:
        if f[lay] != PART_FLAT:
            continue
        if f.normal.dot(n) < 0.9999:
            continue
        if any(abs((v.co - p).dot(n)) > tol for v in f.verts):
            continue
        c = f.calc_center_median()
        if ymin is not None and not (ymin <= c.y <= ymax):
            continue
        out.append(f)
    return out


def walk(edges):
    nxt = {}
    for e in edges:
        a, b = e.verts
        nxt.setdefault(a, []).append(b)
        nxt.setdefault(b, []).append(a)
    start = edges[0].verts[0]
    loop = [start]
    prev = None
    cur = start
    while True:
        cand = [v for v in nxt[cur] if v is not prev]
        if not cand:
            break
        nx = cand[0]
        if nx is start:
            break
        loop.append(nx)
        prev, cur = cur, nx
    return loop


def cut_hole(bm, lay, faces, hole_pts, n):
    from mathutils.geometry import delaunay_2d_cdt
    region = set(faces)
    boundary = list({e for f in faces for e in f.edges if sum(1 for g in e.link_faces if g in region) == 1})
    bmesh.ops.delete(bm, geom=list(region), context="FACES")
    boundary = [e for e in boundary if e.is_valid]
    outer = walk(boundary)
    hv = [bm.verts.new(p) for p in hole_pts]
    u = n.orthogonal().normalized()
    w = n.cross(u)
    allv = outer + hv
    co2 = [Vector((v.co.dot(u), v.co.dot(w))) for v in allv]
    no = len(outer)
    loops = [list(range(no)), list(range(no, no + len(hv)))]
    vo, eo, fo, ov, oe, of = delaunay_2d_cdt(co2, [], loops, 2, 1e-6)
    if len(vo) != len(allv):
        raise ValueError("cdt added vertices")
    idx = [ov[i][0] for i in range(len(vo))]
    new = []
    for f in fo:
        vs = [allv[idx[i]] for i in f]
        if len(set(vs)) < 3:
            continue
        g = bm.faces.new(vs)
        g[lay] = PART_FLAT
        new.append(g)
    bm.normal_update()
    for g in new:
        if g.normal.dot(n) < 0:
            g.normal_flip()
    j = bmesh.ops.join_triangles(bm, faces=new, angle_face_threshold=math.radians(2.0), angle_shape_threshold=math.radians(40.0), cmp_seam=False, cmp_sharp=False, cmp_uvs=False, cmp_vcols=False, cmp_materials=False)
    for g in j.get("faces", []):
        g[lay] = PART_FLAT
    return len(new), len(hv), len(outer)


def seat_outline(conname):
    s = bpy.data.objects["hcr_turret_seats"]
    me = s.data
    hp = me.attributes["hc_part"].data
    v1 = set()
    v9 = set()
    for p in me.polygons:
        k = hp[p.index].value
        if k == 1:
            v1.update(p.vertices)
        elif k == 9:
            v9.update(p.vertices)
    c = bpy.data.objects[conname].matrix_world
    ci = c.inverted()
    ids = [i for i in v1 & v9 if (s.matrix_world @ me.vertices[i].co - c.translation).length < 13]
    pts = [(s.matrix_world @ me.vertices[i].co) for i in ids]
    pts.sort(key=lambda w: math.atan2((ci @ w).y, (ci @ w).x))
    return [w - ORIGIN for w in pts]


def circle_04():
    c = bpy.data.objects["rb_con_turret_04"].matrix_world
    return [(c @ Vector((HOLE_04_R * math.cos(t), HOLE_04_R * math.sin(t), -0.34))) - ORIGIN for t in [2 * math.pi * k / 72 for k in range(72)]]


def shade(bm, lay):
    for f in bm.faces:
        f.smooth = True
    for e in bm.edges:
        lf = e.link_faces
        if len(lf) != 2:
            e.smooth = False
            continue
        a = lf[0][lay]
        b = lf[1][lay]
        if a == b and a in (PART_STRIP, PART_BEVEL):
            e.smooth = True
        elif e.calc_face_angle(0.0) < math.radians(0.5) and a == b:
            e.smooth = True
        else:
            e.smooth = False


def build():
    me = bpy.data.meshes.new(NAME)
    bm = bmesh.new()
    lay = bm.faces.layers.int.new("hc_part")
    loft(bm, lay)
    orient(bm)
    fix_strip_tags(bm, lay)
    nb = bevel_edges(bm, lay)
    bm.normal_update()
    holes = {}
    for cn, sgn in (("rb_con_turret_01", -1), ("rb_con_turret_02", 1)):
        n = Vector((sgn * FLANK_N.x, FLANK_N.y, FLANK_N.z))
        p = Vector((sgn * FLANK_P.x, FLANK_P.y, FLANK_P.z))
        faces = region_faces(bm, lay, n, p, ymin=76.0, ymax=99.0)
        holes[cn] = cut_hole(bm, lay, faces, seat_outline(cn), n)
    faces = region_faces(bm, lay, T04_N, T04_P, ymin=86.0, ymax=107.0)
    holes["rb_con_turret_04"] = cut_hole(bm, lay, faces, circle_04(), T04_N)
    bm.normal_update()
    shade(bm, lay)
    bm.to_mesh(me)
    bm.free()
    me.materials.append(bpy.data.materials[MAT])
    old = bpy.data.objects.get(NAME)
    if old is not None:
        bpy.data.objects.remove(old, do_unlink=True)
    ob = bpy.data.objects.new(NAME, me)
    ob.location = ORIGIN
    bpy.data.collections["HCP_rebuild"].objects.link(ob)
    return ob, nb, holes
