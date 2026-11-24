import bpy
import bmesh
import math
import numpy as np
from mathutils import Vector

exec(bpy.data.texts["hc_materials.py"].as_string(), globals())

MM = "p2multimat.p2_multimat_01"
P2 = "/home/darkona/development/x4/heavy-centaur/source/materials/p2/multimat_layers/"
TEX_SIZE[MM] = (512, 512)
MM_M_PER_TILE = 3.0
MM_PX_PER_M = 512.0 / MM_M_PER_TILE
MM_LAYER_ID = 25
MM_SMOOTH = 0xB0
MM_METAL = 0xFF
CK_MM = (0xAE, 0x00, 16)
CK_COL = (0xDE, 0xEC, 0xFF)

C_PLATE_TONES = [((0xC3, 0xC2, 0xC0), 45), ((0x80, 0x80, 0x80), 30), ((0x70, 0x70, 0x70), 15), ((0x63, 0x63, 0x63), 10)]
C_MECH_TONES = [((0x64, 0x64, 0x64), 60), ((0x80, 0x80, 0x80), 25), ((0x50, 0x50, 0x50), 15)]
C_TOWER_PLATE = (0xC3, 0xC2, 0xC0)
C_PLATE_SIDE = (0x80, 0x80, 0x80)
C_UNDER = (0x40, 0x40, 0x40)
C_FX = (0x80, 0x80, 0x80)
C_GR = (0x00, 0x00, 0x00)
C_WHITE = (0xFF, 0xFF, 0xFF)
C_FACTION = (0xFF, 0x00, 0x00)

TOWER = {"hcr_tower_core", "hcr_tower_armor", "hcr_tower_fins", "hcr_tower_bridge_armor"}
ALL_HP = {"hcr_bow_bulb_core"}
SEAM_UNWRAP = {"hcr_bow_bulb_core"}
BULB_LIGHT_AREA = 150.0
ARMOUR_EXTRA = {"hcr_stern_lobes", "hcr_wing_lobes", "hcr_tower_core", "hcr_bow_prow"}
UNDER_EXTRA = {"hcr_bow_trunk", "hcr_keel_ball", "hcr_keel_ball_sphere", "hcr_stern_antenna", "hcr_orig_details", "rb_bay_s_support", "rb_dock_pad_wall", "hcr_stern_spine", "hcr_stern_cowls"}
SKIP = {"rb_dock_s_clearance", "hcr_bridge_window_cap"}
FX_OBJECTS = {"hcr_poslight_housings"}
KEEP_MM = {"hcr_stern_nozzles"}
STEEL = {"hcr_bow_antenna", "hcr_roof_dish"}

BANDS = [
    (("hcr_wing_armor",), 0, True, [(39.3, 39.9, 1), (39.9, 41.4, 2), (41.4, 42.0, 1)]),
    (("hcr_bow_bulb_core",), 1, False, [(104.5, 105.1, 1), (105.1, 106.6, 2), (106.6, 107.2, 1)]),
    (("hcr_tower_armor", "hcr_tower_core"), 1, False, [(-87.0, -86.4, 1), (-86.4, -84.9, 2), (-84.9, -84.3, 1)]),
    (("hcr_mid_armor",), 1, False, [(-101.0, -100.4, 1)]),
    (("hcr_neck_armor",), 1, False, [(50.4, 51.0, 1)]),
]

SHIP = Vector((420.0, 0.0, 0.0))


def is_armour(n):
    return n.endswith("_armor") or n in ARMOUR_EXTRA or n.startswith(("anim_vlshatch", "anim_dockdoor"))


def is_under(n):
    return (n.endswith("_core") and n not in ALL_HP and n not in TOWER) or n in UNDER_EXTRA


def hull_objects():
    return [o for o in bpy.data.collections["HCP_rebuild"].all_objects if o.type == "MESH" and o.name not in SKIP and o.data.library is None]


def cut_bands():
    done = []
    for names, axis, mirror, bands in BANDS:
        for n in names:
            o = bpy.data.objects[n]
            if o.get("hc_bands"):
                continue
            mw = o.matrix_world
            mi = mw.inverted()
            bm = bmesh.new()
            bm.from_mesh(o.data)
            planes = sorted({v for lo, hi, k in bands for v in (lo, hi)})
            signs = (1, -1) if mirror else (1,)
            for s in signs:
                for v in planes:
                    co = Vector((0, 0, 0))
                    co[axis] = s * v
                    co = mi @ (co - SHIP)
                    no = Vector((0, 0, 0))
                    no[axis] = 1.0
                    no = (mi.to_3x3() @ no).normalized()
                    geom = list(bm.verts) + list(bm.edges) + list(bm.faces)
                    bmesh.ops.bisect_plane(bm, geom=geom, dist=1e-4, plane_co=co, plane_no=no)
            lay = bm.faces.layers.int.get("hc_stripe") or bm.faces.layers.int.new("hc_stripe")
            for f in bm.faces:
                c = mw @ f.calc_center_median() + SHIP
                x = abs(c[axis]) if mirror else c[axis]
                f[lay] = 0
                for lo, hi, k in bands:
                    if lo < x < hi:
                        f[lay] = k
            bm.to_mesh(o.data)
            o.data.update()
            bm.free()
            o["hc_bands"] = 1
            done.append(n)
    return done


def current_names(o):
    names = [s.material.name if s.material else "" for s in o.material_slots] or [""]
    mi = np.zeros(len(o.data.polygons), dtype=np.int32)
    o.data.polygons.foreach_get("material_index", mi)
    return [names[i] if i < len(names) else "" for i in mi]


def part_attr(o):
    a = o.data.attributes.get("hc_part")
    if a is None or a.domain != "FACE":
        return None
    v = np.zeros(len(o.data.polygons), dtype=np.int32)
    a.data.foreach_get("value", v)
    return v


def zones_for(o):
    n = o.name
    cur = current_names(o)
    bm = bmesh.new()
    bm.from_mesh(o.data)
    bm.faces.ensure_lookup_table()
    if n in STEEL:
        want = [HP] * len(cur)
    elif n in ALL_HP:
        hp = part_attr(o)
        want = [HT if hp is not None and hp[i] == 3 else HP for i in range(len(cur))]
    elif n == "hcr_cockpit_pod":
        want = [HP if "hullpattern" in c else (FX if "_fx" in c else HT) for c in cur]
    elif n == "hcr_tower_fins":
        want = [HT] * len(cur)
    elif n in FX_OBJECTS:
        want = [FX] * len(cur)
    elif is_armour(n):
        want = zone_armor(o, bm)
    elif n == "hcr_keel_intakes":
        want = zone_intakes(o, bm)
    else:
        want = [HT] * len(cur)
    bm.free()
    for i, c in enumerate(cur):
        if c in (FX, GR) or c.endswith("gen_p2_fx_01"):
            want[i] = FX if c != GR else GR
        elif c == MM and n in KEEP_MM:
            want[i] = MM
    if is_under(n):
        want = [MM if w == HT else w for w in want]
    hp = part_attr(o)
    if n == "hcr_turret_seats" and hp is not None:
        want = [MM if hp[i] == 3 else w for i, w in enumerate(want)]
    return want


def assign_all():
    rep = {}
    for o in hull_objects():
        want = zones_for(o)
        set_face_materials(o, want)
        rep[o.name] = {k: want.count(k) for k in set(want)}
    return rep


def rescale_islands(o, target=TARGET_PX_PER_M):
    from bpy_extras.mesh_utils import mesh_linked_uv_islands
    me = o.data
    uvl = me.uv_layers.active
    nl = len(me.loops)
    uv = np.zeros(nl * 2)
    uvl.data.foreach_get("uv", uv)
    uv = uv.reshape(-1, 2)
    ls = np.zeros(len(me.polygons), dtype=np.int32)
    me.polygons.foreach_get("loop_start", ls)
    lt = np.zeros(len(me.polygons), dtype=np.int32)
    me.polygons.foreach_get("loop_total", lt)
    area = np.zeros(len(me.polygons))
    me.polygons.foreach_get("area", area)
    area *= object_area_scale(o)
    cen = np.zeros(len(me.polygons) * 3)
    me.polygons.foreach_get("center", cen)
    cen = (np.array(o.matrix_world)[:3, :3] @ cen.reshape(-1, 3).T).T
    nrm = np.zeros(len(me.polygons) * 3)
    me.polygons.foreach_get("normal", nrm)
    nrm = nrm.reshape(-1, 3)
    mi, names = face_material_names(o)
    for isl in mesh_linked_uv_islands(me):
        isl = np.array(isl)
        for m in np.unique(mi[isl]):
            faces = isl[mi[isl] == m]
            name = names[m] if m < len(names) else ""
            loops = np.concatenate([np.arange(ls[f], ls[f] + lt[f]) for f in faces])
            if name == GR:
                uv[loops] = GRADIENT_UV
                continue
            w, h = TEX_SIZE.get(name, (2048, 2048))
            tgt = MM_PX_PER_M if name == MM else target
            p = uv[loops].copy()
            uva = 0.0
            for f in faces:
                q = uv[ls[f]:ls[f] + lt[f]]
                uva += 0.5 * abs(np.dot(q[:, 0], np.roll(q[:, 1], -1)) - np.dot(q[:, 1], np.roll(q[:, 0], -1)))
            a3 = area[faces].sum()
            if uva <= 1e-12 or a3 <= 1e-9:
                continue
            k = np.sqrt(a3 / uva) * tgt
            c = p.mean(0)
            p = (p - c) * k
            p = p @ principal_rotation(p, np.ones(len(p))).T
            if name == FX:
                ext = np.abs(p).max(0).max() * 2.0
                if ext > FX_MAX_PX:
                    p *= FX_MAX_PX / ext
                p[:, 0] = p[:, 0] / w + FX_GLOW_UV[0]
                p[:, 1] = p[:, 1] / h + FX_GLOW_UV[1]
                uv[loops] = p
                continue
            if name == MM:
                p[:, 0] = p[:, 0] / w
                p[:, 1] = p[:, 1] / h
                wc = (cen[faces] * area[faces, None]).sum(0) / a3
                off = np.array([wc[0] + wc[2], wc[1]]) / MM_M_PER_TILE
                off = off - np.floor(off)
                uv[loops] = p + off
                continue
            wc = (cen[faces] * area[faces, None]).sum(0) / a3
            n = (nrm[faces] * area[faces, None]).sum(0)
            ax = int(np.argmax(np.abs(n)))
            other = [i for i in range(3) if i != ax]
            p = p + wc[other] * target
            p[:, 0] = p[:, 0] / w + 0.5
            p[:, 1] = p[:, 1] / h + 0.5
            uv[loops] = p
    uvl.data.foreach_set("uv", uv.ravel())
    me.update()


def seam_unwrap(o, angle=40.0):
    me = o.data
    if not me.uv_layers:
        me.uv_layers.new(name="UVMap")
    bm = bmesh.new()
    bm.from_mesh(me)
    lim = math.radians(angle)
    for e in bm.edges:
        lf = e.link_faces
        e.seam = len(lf) != 2 or lf[0].material_index != lf[1].material_index or e.calc_face_angle(0.0) > lim
    bm.to_mesh(me)
    bm.free()
    view = bpy.context.view_layer
    prev = view.objects.active
    for x in bpy.context.selected_objects:
        x.select_set(False)
    o.select_set(True)
    view.objects.active = o
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.uv.unwrap(method="CONFORMAL", margin=0.0)
    bpy.ops.object.mode_set(mode="OBJECT")
    o.select_set(False)
    view.objects.active = prev
    rescale_islands(o)


def world_aligned_unwrap(o, angle=60.0, target=TARGET_PX_PER_M):
    from bpy_extras.mesh_utils import mesh_linked_uv_islands
    me = o.data
    if not me.uv_layers:
        me.uv_layers.new(name="UVMap")
    view = bpy.context.view_layer
    prev = view.objects.active
    for x in bpy.context.selected_objects:
        x.select_set(False)
    o.select_set(True)
    view.objects.active = o
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.uv.smart_project(angle_limit=math.radians(angle), island_margin=0.0, area_weight=0.0, correct_aspect=False, scale_to_bounds=False)
    bpy.ops.object.mode_set(mode="OBJECT")
    o.select_set(False)
    view.objects.active = prev
    uvl = me.uv_layers.active
    uv = np.zeros(len(me.loops) * 2)
    uvl.data.foreach_get("uv", uv)
    uv = uv.reshape(-1, 2)
    co = np.zeros(len(me.vertices) * 3)
    me.vertices.foreach_get("co", co)
    co = co.reshape(-1, 3) @ np.array(o.matrix_world)[:3, :3].T
    lv = np.zeros(len(me.loops), dtype=np.int32)
    me.loops.foreach_get("vertex_index", lv)
    ls = np.zeros(len(me.polygons), dtype=np.int32)
    me.polygons.foreach_get("loop_start", ls)
    lt = np.zeros(len(me.polygons), dtype=np.int32)
    me.polygons.foreach_get("loop_total", lt)
    mi, names = face_material_names(o)
    for isl in mesh_linked_uv_islands(me):
        isl = np.array(isl)
        loops = np.concatenate([np.arange(ls[f], ls[f] + lt[f]) for f in isl])
        name = names[mi[isl[0]]] if mi[isl[0]] < len(names) else ""
        w, h = TEX_SIZE.get(name, (2048, 2048))
        P = co[lv[loops]]
        Q = uv[loops]
        A = np.hstack([P, np.ones((len(P), 1))])
        sol, *_ = np.linalg.lstsq(A, Q, rcond=None)
        M = sol[:3]
        dy = M[1]
        uva = 0.0
        a3 = 0.0
        for f in isl:
            qq = uv[ls[f]:ls[f] + lt[f]]
            uva += 0.5 * abs(np.dot(qq[:, 0], np.roll(qq[:, 1], -1)) - np.dot(qq[:, 1], np.roll(qq[:, 0], -1)))
            a3 += me.polygons[int(f)].area
        if uva <= 1e-12 or a3 <= 1e-9:
            continue
        unit = math.sqrt(uva / a3)
        q = Q - Q.mean(0)
        if np.linalg.norm(dy) > 0.5 * unit:
            ang = -math.atan2(dy[1], dy[0])
            R = np.array([[math.cos(ang), -math.sin(ang)], [math.sin(ang), math.cos(ang)]])
        else:
            R = principal_rotation(q, np.ones(len(q)))
        q = q @ R.T
        q = q * (target / unit)
        A2 = np.hstack([P, np.ones((len(P), 1))])
        sol2, *_ = np.linalg.lstsq(A2, q, rcond=None)
        q = q - sol2[3]
        q[:, 0] = q[:, 0] / w + 0.5
        q[:, 1] = q[:, 1] / h + 0.5
        uv[loops] = q
    uvl.data.foreach_set("uv", uv.ravel())
    me.update()


def unwrap(objs=None):
    out = {}
    for o in objs or hull_objects():
        if o.name in SEAM_UNWRAP:
            world_aligned_unwrap(o)
        else:
            uv_density(o)
        if o.data.uv_layers.active.name != "UVMap":
            o.data.uv_layers.active.name = "UVMap"
        out[o.name] = density_report(o)
    return out


def pick(tones, key):
    tot = sum(w for c, w in tones)
    r = key % tot
    for c, w in tones:
        if r < w:
            return c
        r -= w
    return tones[0][0]


def island_keys(bm, mat_of):
    key = [0] * len(bm.faces)
    seen = set()
    for f in bm.faces:
        if f.index in seen:
            continue
        m = mat_of[f.index]
        stack = [f]
        seen.add(f.index)
        comp = []
        while stack:
            g = stack.pop()
            comp.append(g)
            for e in g.edges:
                for h in e.link_faces:
                    if h.index not in seen and mat_of[h.index] == m:
                        seen.add(h.index)
                        stack.append(h)
        c = sum((g.calc_center_median() for g in comp), Vector()) / len(comp)
        k = int(abs(c.x + 0.0) * 7.31 + c.y * 3.17 + c.z * 5.73 + len(comp) * 13) & 0x7FFFFFFF
        k = (k * 2654435761) >> 7
        for g in comp:
            key[g.index] = k
    return key


def face_colours(o):
    n = o.name
    want = current_names(o)
    bm = bmesh.new()
    bm.from_mesh(o.data)
    bm.faces.ensure_lookup_table()
    stripe_l = bm.faces.layers.int.get("hc_stripe")
    keys = island_keys(bm, want)
    big = set()
    if n in ALL_HP:
        area = {}
        for f in bm.faces:
            area[keys[f.index]] = area.get(keys[f.index], 0.0) + f.calc_area()
        big = {k for k, a in area.items() if a > BULB_LIGHT_AREA}
    out = []
    for f in bm.faces:
        m = want[f.index]
        stripe = f[stripe_l] if stripe_l else 0
        mm = (0, 0, 0)
        mask = 0
        if m == MM:
            col = C_UNDER
            mm = (MM_SMOOTH, MM_METAL, MM_LAYER_ID)
        elif m == FX:
            col = C_FX
        elif m == GR:
            col = C_GR
        elif m == HP:
            mask = 255
            col = C_TOWER_PLATE if (n in TOWER or keys[f.index] in big) else pick(C_PLATE_TONES, keys[f.index])
        else:
            col = C_PLATE_SIDE if (is_armour(n) or n in TOWER or n in ALL_HP) else pick(C_MECH_TONES, keys[f.index])
        if n in STEEL:
            col = C_TOWER_PLATE
            mask = 0
            stripe = 0
        if stripe and m in (HP, HT):
            col = C_WHITE if stripe == 1 else C_FACTION
            mask = 255
        out.append((col, mask, mm))
    bm.free()
    return out


def set_byte(me, name, per_face, ls, lt):
    if name in me.color_attributes:
        me.color_attributes.remove(me.color_attributes[name])
    a = me.color_attributes.new(name, "BYTE_COLOR", "CORNER")
    flat = np.zeros((len(me.loops), 4), dtype=np.float32)
    flat[:, 3] = 1.0
    for f, v in enumerate(per_face):
        flat[ls[f]:ls[f] + lt[f], 0:3] = v
    a.data.foreach_set("color_srgb", flat.ravel())
    return a


def write_vertex_data(o, per):
    me = o.data
    ls = np.zeros(len(me.polygons), dtype=np.int32)
    me.polygons.foreach_get("loop_start", ls)
    lt = np.zeros(len(me.polygons), dtype=np.int32)
    me.polygons.foreach_get("loop_total", lt)
    for nm in ("col", "ao", "paintmodmask", "dirt", "multimatsmooth", "multimatmetal", "multimatid"):
        if nm in me.color_attributes:
            me.color_attributes.remove(me.color_attributes[nm])
    b = 1.0 / 255.0
    set_byte(me, "col", [tuple(c * b for c in p[0]) for p in per], ls, lt)
    set_byte(me, "paintmodmask", [(p[1] * b, 0, 0) for p in per], ls, lt)
    set_byte(me, "dirt", [(0, 0, 0)] * len(per), ls, lt)
    set_byte(me, "multimatsmooth", [(p[2][0] * b, 0, 0) for p in per], ls, lt)
    set_byte(me, "multimatmetal", [(p[2][1] * b, 0, 0) for p in per], ls, lt)
    set_byte(me, "multimatid", [(p[2][2] * b, 0, 0) for p in per], ls, lt)
    me.color_attributes.active_color = me.color_attributes["col"]
    me.color_attributes.render_color_index = list(me.color_attributes).index(me.color_attributes["col"])


def paint_all():
    for o in hull_objects():
        write_vertex_data(o, face_colours(o))


def paint_cockpit_interior():
    done = []
    for o in (bpy.data.collections["HCP_rebuild_cockpit"].objects if "HCP_rebuild_cockpit" in bpy.data.collections else []):
        if o.type != "MESH" or o.data.library is not None:
            continue
        names = current_names(o)
        per = []
        for c in names:
            if c == MM:
                per.append((CK_COL, 0, CK_MM))
            else:
                per.append(((255, 255, 255), 0, (0, 0, 0)))
        write_vertex_data(o, per)
        done.append(o.name)
    return done


def preview_attr_colour(mat):
    nt = mat.node_tree
    bsdf = next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED")
    link = next((l for l in nt.links if l.to_socket == bsdf.inputs["Base Color"]), None)
    src = link.from_socket if link else None
    base_val = tuple(bsdf.inputs["Base Color"].default_value)
    for nm in ("hc col", "hc mask", "hc mask sep", "hc hue", "hc mix mask", "hc mul col"):
        n = nt.nodes.get(nm)
        if n:
            nt.nodes.remove(n)
    x, y = bsdf.location.x - 700, bsdf.location.y + 500
    col = nt.nodes.new("ShaderNodeVertexColor")
    col.name = col.label = "hc col"
    col.layer_name = "col"
    col.location = (x - 400, y + 200)
    msk = nt.nodes.new("ShaderNodeVertexColor")
    msk.name = msk.label = "hc mask"
    msk.layer_name = "paintmodmask"
    msk.location = (x - 400, y - 50)
    sep = nt.nodes.new("ShaderNodeSeparateColor")
    sep.name = sep.label = "hc mask sep"
    sep.location = (x - 200, y - 50)
    nt.links.new(msk.outputs["Color"], sep.inputs[0])
    hue = nt.nodes.new("ShaderNodeHueSaturation")
    hue.name = "hc hue"
    hue.label = "paint mod (preview: red to faction blue)"
    hue.location = (x - 200, y + 250)
    hue.inputs["Hue"].default_value = 0.12
    nt.links.new(col.outputs["Color"], hue.inputs["Color"])
    mixm = nt.nodes.new("ShaderNodeMix")
    mixm.name = mixm.label = "hc mix mask"
    mixm.data_type = "RGBA"
    mixm.location = (x, y + 200)
    nt.links.new(sep.outputs[0], mixm.inputs[0])
    nt.links.new(col.outputs["Color"], mixm.inputs[6])
    nt.links.new(hue.outputs[0], mixm.inputs[7])
    mul = nt.nodes.new("ShaderNodeMix")
    mul.name = mul.label = "hc mul col"
    mul.data_type = "RGBA"
    mul.blend_type = "MULTIPLY"
    mul.inputs[0].default_value = 1.0
    mul.location = (x + 200, y + 100)
    if src is not None:
        nt.links.new(src, mul.inputs[6])
    else:
        mul.inputs[6].default_value = base_val
    nt.links.new(mixm.outputs[2], mul.inputs[7])
    nt.links.new(mul.outputs[2], bsdf.inputs["Base Color"])


def layer_img(name):
    path = P2 + name + ".png"
    im = next((i for i in bpy.data.images if i.filepath and bpy.path.abspath(i.filepath) == path), None)
    if im is None:
        im = bpy.data.images.load(path)
    im.colorspace_settings.name = "Non-Color"
    return im


def build_multimat():
    mat = get_mat(MM)
    t = Tree(mat)
    a = t.n("ShaderNodeTexImage", -1300, 300, "multimat layer 26 (id 25)")
    a.image = layer_img("diff_26")
    t.link(t.uv.outputs["UV"], a.inputs["Vector"])
    b = t.n("ShaderNodeTexImage", -1300, -100, "multimat layer 17 (id 16, cockpit)")
    b.image = layer_img("diff_17")
    t.link(t.uv.outputs["UV"], b.inputs["Vector"])
    ida = t.n("ShaderNodeVertexColor", -1300, 700, "multimatid")
    ida.layer_name = "multimatid"
    sid = t.n("ShaderNodeSeparateColor", -1100, 700)
    t.link(ida.outputs["Color"], sid.inputs[0])
    pick_hex = t.math("GREATER_THAN", sid.outputs[0], 0.08, -900, 700)
    lay = t.mix("MIX", 0.0, (1, 1, 1, 1), (1, 1, 1, 1), -900, 200, "layer by id")
    mix_node = t.nt.nodes[-1]
    t.link(pick_hex, mix_node.inputs[0])
    t.link(b.outputs["Color"], mix_node.inputs[6])
    t.link(a.outputs["Color"], mix_node.inputs[7])
    sep = t.n("ShaderNodeSeparateColor", -700, 200)
    t.link(lay, sep.inputs[0])
    col = t.n("ShaderNodeVertexColor", -700, 600, "col")
    col.layer_name = "col"
    base = t.mix("MULTIPLY", 1.0, (1, 1, 1, 1), col.outputs["Color"], -400, 400, "col x layer R")
    t.link(sep.outputs[0], t.nt.nodes[-1].inputs[6])
    t.link(base, t.bsdf.inputs["Base Color"])
    sm = t.n("ShaderNodeVertexColor", -700, -300, "multimatsmooth")
    sm.layer_name = "multimatsmooth"
    sms = t.n("ShaderNodeSeparateColor", -500, -300)
    t.link(sm.outputs["Color"], sms.inputs[0])
    smooth = t.math("MULTIPLY", sep.outputs[1], sms.outputs[0], -300, -200)
    t.link(t.math("SUBTRACT", 1.0, smooth, -150, -200), t.bsdf.inputs["Roughness"])
    me_ = t.n("ShaderNodeVertexColor", -700, -500, "multimatmetal")
    me_.layer_name = "multimatmetal"
    mes = t.n("ShaderNodeSeparateColor", -500, -500)
    t.link(me_.outputs["Color"], mes.inputs[0])
    metal = t.math("MULTIPLY", sep.outputs[2], mes.outputs[0], -300, -450)
    t.link(t.math("MULTIPLY", metal, 0.6, -150, -450), t.bsdf.inputs["Metallic"])
    hgt = t.n("ShaderNodeTexImage", -1300, -900, "height layer 26")
    hgt.image = layer_img("height_26")
    t.link(t.uv.outputs["UV"], hgt.inputs["Vector"])
    bump = t.n("ShaderNodeBump", -300, -900, "hex relief (preview)")
    bump.inputs["Strength"].default_value = 0.6
    bump.inputs["Distance"].default_value = 0.05
    hsel = t.math("MULTIPLY", hgt.outputs["Color"], pick_hex, -600, -900)
    t.link(hsel, bump.inputs["Height"])
    t.link(bump.outputs["Normal"], t.bsdf.inputs["Normal"])


def build_previews():
    build_materials()
    for nm in (HT, HP, FX):
        m = bpy.data.materials[nm]
        tint = next((n for n in m.node_tree.nodes if n.label == "paint tint"), None)
        if tint is not None:
            tint.inputs[0].default_value = 0.0
        preview_attr_colour(m)
    build_multimat()


def run(step="all"):
    out = {}
    if step in ("all", "bands"):
        out["bands"] = cut_bands()
    if step in ("all", "zones"):
        out["zones"] = assign_all()
    if step in ("all", "uv"):
        out["uv"] = unwrap()
    if step in ("all", "paint"):
        paint_all()
        out["cockpit"] = paint_cockpit_interior()
    if step in ("all", "preview"):
        build_previews()
    return out
