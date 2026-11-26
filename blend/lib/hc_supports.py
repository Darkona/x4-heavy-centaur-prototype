import bpy
import bmesh
import math
from mathutils import Vector

SEATS = "hcr_turret_seats"
HULL_SKIP = {"hcr_turret_seats", "hcr_shield_seats", "hcr_greebles", "hcr_orig_details", "hcr_poslight_housings", "hcr_vls_frames", "rb_dock_s_clearance", "rb_dock_s_pad", "hcr_cockpit_pod"}
M_SIZE = dict(ax0=-8.1, ax1=8.1, ay0=-8.1, ay1=8.1, corner=2.0, rim=5.9, pit=5.3, depth=3.3, skirt=3.5, sink=0.45, drop_max=4.0)
BOW_SIZE = dict(M_SIZE, skirt=1.5, drop_max=1.5)
SUPPORTS = {
    "rb_con_turret_01": BOW_SIZE,
    "rb_con_turret_02": BOW_SIZE,
    "rb_con_turret_04": M_SIZE,
    "rb_con_turret_05": M_SIZE,
    "rb_con_turret_06": M_SIZE,
    "rb_con_turret_07": M_SIZE,
    "rb_con_turret_08": M_SIZE,
    "rb_con_turret_03": dict(ax0=-5.2, ax1=5.2, ay0=-7.2, ay1=8.4, corner=1.4, rim=3.55, pit=3.18, depth=2.0, skirt=1.3, sink=0.3, drop_max=2.4),
}
BULLNOSE = [(0.0, 0.0), (0.12, -0.03), (0.24, -0.11), (0.31, -0.22), (0.34, -0.36)]
SKIRT_RINGS = 7
H_WIN = 4
N_OUT = 72


def rounded_rect(ax0, ax1, ay0, ay1, r, n):
    cx = [(ax1 - r, ay1 - r, 0.0), (ax0 + r, ay1 - r, 0.5 * math.pi), (ax0 + r, ay0 + r, math.pi), (ax1 - r, ay0 + r, 1.5 * math.pi)]
    segs = []
    for i, (x, y, a0) in enumerate(cx):
        segs.append(("arc", x, y, a0))
        nx, ny, _ = cx[(i + 1) % 4]
        p0 = (x + r * math.cos(a0 + 0.5 * math.pi), y + r * math.sin(a0 + 0.5 * math.pi))
        p1 = (nx + r * math.cos(a0 + 0.5 * math.pi), ny + r * math.sin(a0 + 0.5 * math.pi))
        segs.append(("line", p0, p1, a0 + 0.5 * math.pi))
    lens = []
    for s in segs:
        if s[0] == "arc":
            lens.append(0.5 * math.pi * r)
        else:
            lens.append(math.dist(s[1], s[2]))
    total = sum(lens)
    out = []
    for k in range(n):
        d = total * k / n
        for s, L in zip(segs, lens):
            if d <= L or s is segs[-1]:
                t = d / L if L > 0 else 0.0
                if s[0] == "arc":
                    a = s[3] + 0.5 * math.pi * t
                    out.append((Vector((s[1] + r * math.cos(a), s[2] + r * math.sin(a))), Vector((math.cos(a), math.sin(a)))))
                else:
                    p = Vector(s[1]).lerp(Vector(s[2]), t)
                    out.append((p, Vector((math.cos(s[3]), math.sin(s[3])))))
                break
            d -= L
    return out


def hull_objects():
    return [o for o in bpy.data.collections["HCP_rebuild"].all_objects if o.type == "MESH" and o.get("hcr_group", o.name) not in HULL_SKIP and not o.name.startswith(("anim_", "rb_work", "hcr_shield_seat_"))]


def hull_height(objs, M, x, y, top=3.0, depth=12.0):
    p = M @ Vector((x, y, top))
    d = (M.to_3x3() @ Vector((0, 0, -1))).normalized()
    best = None
    for o in objs:
        mi = o.matrix_world.inverted()
        ok, loc, n, i = o.ray_cast(mi @ p, (mi.to_3x3() @ d).normalized(), distance=top + depth)
        if ok:
            z = (M.inverted() @ (o.matrix_world @ loc)).z
            if best is None or z > best:
                best = z
    return best


def smooth(t):
    return t * t * (3 - 2 * t)


def build(conname, prm, bm, lay, T, hull):
    con = bpy.data.objects[conname]
    M = con.matrix_world
    outline = rounded_rect(prm["ax0"], prm["ax1"], prm["ay0"], prm["ay1"], prm["corner"], N_OUT)
    angs = [math.atan2(p.y, p.x) for p, n in outline]
    def ring(pts):
        return [bm.verts.new(T @ Vector(p)) for p in pts]
    def bridge(a, b, part):
        for i in range(len(a)):
            j = (i + 1) % len(a)
            f = bm.faces.new((a[i], a[j], b[j], b[i]))
            f[lay] = part
    z0 = -0.02
    rim = ring([(prm["rim"] * math.cos(t), prm["rim"] * math.sin(t), z0) for t in angs])
    rim2 = ring([(prm["pit"] * math.cos(t), prm["pit"] * math.sin(t), z0 - 0.3) for t in angs])
    pitb = ring([(prm["pit"] * math.cos(t), prm["pit"] * math.sin(t), z0 - prm["depth"]) for t in angs])
    rings = [ring([(p.x + n.x * dx, p.y + n.y * dx, z0 + dz) for p, n in outline]) for dx, dz in BULLNOSE]
    ex, ez = BULLNOSE[-1]
    ze = z0 + ez
    skirt = []
    for k in range(1, SKIRT_RINGS + 1):
        t = k / SKIRT_RINGS
        xy = []
        hs = []
        for p, n in outline:
            off = ex + prm["skirt"] * t
            x = p.x + n.x * off
            y = p.y + n.y * off
            h = hull_height(hull, M, x, y)
            if h is None or h < ze - prm["drop_max"]:
                h = ze - prm["drop_max"]
            xy.append((x, y))
            hs.append(h)
        nn = len(hs)
        hs = [sum(hs[(i + j) % nn] for j in range(-H_WIN, H_WIN + 1)) / (2 * H_WIN + 1) for i in range(nn)]
        pts = []
        for (x, y), h in zip(xy, hs):
            zt = ze + (h - prm["sink"] - ze) * smooth(t)
            pts.append((x, y, zt))
        skirt.append(ring(pts))
    bridge(rings[0], rim, 1)
    bridge(rim, rim2, 2)
    bridge(rim2, pitb, 3)
    fl = bm.faces.new(pitb)
    fl[lay] = 3
    allr = rings + skirt
    for i in range(len(allr) - 1):
        bridge(allr[i + 1], allr[i], 9 if i < len(rings) - 1 else 8)
    new = set(rim + rim2 + pitb + [v for r in allr for v in r])
    faces = [f for f in bm.faces if any(v in new for v in f.verts)]
    bmesh.ops.triangulate(bm, faces=[fl])
    Ti = T.inverted()
    bm.normal_update()
    for f in [f for f in bm.faces if f.is_valid and any(v in new for v in f.verts)]:
        c = Ti @ f.calc_center_median()
        nl = Ti.to_3x3() @ f.normal
        if f[lay] == 3 and abs(nl.z) < 0.7:
            if Vector((c.x, c.y)).dot(Vector((nl.x, nl.y))) > 0:
                f.normal_flip()
        elif nl.z < 0:
            f.normal_flip()
        f.smooth = f[lay] in (8, 9)
    return len(faces)


def rebuild(names=None):
    o = bpy.data.objects[SEATS]
    hull = hull_objects()
    bm = bmesh.new()
    bm.from_mesh(o.data)
    lay = bm.faces.layers.int.get("hc_part")
    names = names or list(SUPPORTS)
    for cn in names:
        c = bpy.data.objects[cn].matrix_world.translation
        rad = 12.0 if cn.endswith("03") else 15.0
        rm = [f for f in bm.faces if (o.matrix_world @ f.calc_center_median() - c).length < rad]
        bmesh.ops.delete(bm, geom=rm, context="FACES")
    loose = [v for v in bm.verts if not v.link_faces]
    bmesh.ops.delete(bm, geom=loose, context="VERTS")
    out = {}
    for cn in names:
        T = o.matrix_world.inverted() @ bpy.data.objects[cn].matrix_world
        out[cn] = build(cn, SUPPORTS[cn], bm, lay, T, hull)
    bm.to_mesh(o.data)
    o.data.update()
    bm.free()
    return out
