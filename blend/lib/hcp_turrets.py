#!/usr/bin/env python3
import argparse
import importlib.machinery
import importlib.util
import json
import os
import re
import shutil
import subprocess
import sys
import time
import xml.etree.ElementTree as ET
import numpy as np
from pathlib import Path

HOME = Path.home()
LIB = Path(__file__).resolve().parent
REPO = LIB.parent.parent
REFS = HOME / 'development/x4/refs/x4-9.00'
X4 = HOME / 'development/x4'
ASSETS = X4 / 'p1[assets]'
P1DATA = X4 / 'p1data'
SUB = 'extensions/heavy_centaur_prototype/assets/props/weaponsystems/hcp'
WORK = X4 / 'work/hcp_turrets'
SOURCE_DIR = X4 / 'heavy-centaur/publish/turret_hcp_final'
MOD = REPO / 'mod/heavy_centaur_prototype'
WINEPREFIX = HOME / '.local/share/wineprefixes/egosoft'
WIN_BLENDER = r'C:\Program Files\Blender Foundation\Blender 4.5\blender.exe'
WIN_CONVERTER = r'C:\Program Files\EGOSOFT\Egosoft Blender Mod Tools\Converter\XUConverter.exe'
LOCK = X4 / '.xuconverter.lock'

W = 'base/assets/props/WeaponSystems/'
B = 'ego_dlc_boron/assets/props/weaponsystems/boron/'
TURRETS = {
    'laser': (W + 'standard/turret_arg_m_laser_02_mk1.xml', 'part_gun', (), 0.0),
    'gatling': (W + 'heavy/turret_arg_m_gatling_02_mk1.xml', 'part_gun', (), 0.0),
    'plasma': (W + 'heavy/turret_arg_m_plasma_02_mk1.xml', 'part_gun', (), 0.10),
    'beam': (W + 'energy/turret_arg_m_beam_02_mk1.xml', 'detail_xl_gun', ('detail_xl_rotator',), 0.0),
    'shotgun': (W + 'standard/turret_arg_m_shotgun_02_mk1.xml', 'part_gun', (), 0.0),
    'flak': (W + 'heavy/turret_arg_m_flak_02_mk1.xml', 'part_gun', (), 0.0),
    'borlaser': (B + 'turret_bor_m_laser_02_mk1.xml', 'part_gun', ('part_detail_rotator',), 0.0),
    'railgun': (B + 'weapon_bor_m_railgun_01_mk1.xml', None, (), 0.0),
    'arc': (B + 'turret_bor_m_arc_02_mk1.xml', 'part_gun', (), 0.0),
}
BALL = 'flak_ball.obj'
GUNS = 'guns.json'
MERGED = {'part_gun'}
ELEVATION = (-93, 93)
VANILLA = {
    'laser': ('base', 'turret_arg_m_laser_02_mk1', 'Laser', 'láser'),
    'gatling': ('base', 'turret_arg_m_gatling_02_mk1', 'Bolt Repeater', 'repetidora'),
    'plasma': ('base', 'turret_arg_m_plasma_02_mk1', 'Plasma', 'de plasma'),
    'beam': ('base', 'turret_arg_m_beam_02_mk1', 'Beam', 'de haz'),
    'shotgun': ('base', 'turret_arg_m_shotgun_02_mk1', 'Shard Battery', 'de esquirlas'),
    'flak': ('base', 'turret_arg_m_flak_02_mk1', 'Flak', 'antiaérea'),
    'borlaser': ('ego_dlc_boron', 'turret_bor_m_laser_02_mk1', 'Boron Laser', 'láser borón'),
    'railgun': ('ego_dlc_boron', 'turret_bor_m_railgun_02_mk1', 'Railgun', 'de riel'),
    'arc': ('ego_dlc_boron', 'turret_bor_m_arc_02_mk1', 'Arc', 'de arco'),
}
DAMAGE_FACTOR = 1.0
PRICE_FACTOR = 1.0
ROTATION_FACTOR = 1.15
TEXT_PAGE = 1931170
TEXT_BASE = 400
TEXTS = {
    'en': ('t/0001-l044.xml', 'HCP {n} Turret', 'HCP {n} T', 'A ball turret made only for the Heavy Centaur Prototype: fixed guns in a ball joint that turns all the way round, set in a socket on the hull. It fits only the turret mounts of that ship. Same damage as the medium turret of the same weapon.'),
    'es': ('t/0001-l034.xml', 'Torreta {n} PCP', 'Torr. {n} PCP', 'Una torreta de rótula hecha solo para el Prototipo de Centauro Pesado: cañones fijos en una rótula que gira la vuelta entera, montada en un zócalo del casco. Solo cabe en los anclajes de torreta de esa nave. Hace el mismo daño que la torreta mediana del mismo arma.'),
}
SKIP_PART = re.compile(r'(^fx_|decal|wreck|^anim_lights|^detail_m_)')


def component_name(kind):
    return f'turret_arg_m_hcp_{kind}_01_mk1'


def xmf_module():
    path = HOME / 'development/tools/x4-xmf/x4-xmf'
    loader = importlib.machinery.SourceFileLoader('x4_xmf', str(path))
    spec = importlib.util.spec_from_loader('x4_xmf', loader)
    mod = importlib.util.module_from_spec(spec)
    loader.exec_module(mod)
    return mod


def connection_frames(xml_path, xmf):
    comp = ET.parse(xml_path).getroot().find('component')
    conns = {}
    part_conn = {}
    for c in comp.iter('connection'):
        local = xmf.IDENTITY
        off = c.find('offset')
        if off is not None:
            pos = off.find('position')
            q = off.find('quaternion')
            t = tuple(float(pos.get(a, 0)) for a in 'xyz') if pos is not None else (0.0, 0.0, 0.0)
            r = xmf.quat_matrix(*(float(q.get(a, 0)) for a in ('qx', 'qy', 'qz', 'qw'))) if q is not None else xmf.IDENTITY[0]
            local = (r, t)
        conns[c.get('name')] = (c.get('parent'), local, (c.get('tags') or '').split())
        parts = c.find('parts')
        if parts is not None:
            for p in parts.findall('part'):
                part_conn[p.get('name')] = c.get('name')

    def world(name):
        parent, local, _ = conns[name]
        if parent and parent in part_conn:
            return xmf.compose(world(part_conn[parent]), local)
        return local

    return conns, part_conn, world


def subtree(part_conn, conns, root):
    keep = {root}
    changed = True
    while changed:
        changed = False
        for part, cname in part_conn.items():
            parent = conns[cname][0]
            if part not in keep and parent in keep:
                keep.add(part)
                changed = True
    return keep


def read_obj(path):
    verts = []
    colors = []
    uvs = []
    objects = {}
    cur = None
    for line in open(path):
        tag = line[:2]
        if tag in ('o ', 'g '):
            cur = objects.setdefault(line.split()[1], [])
        elif tag == 'v ':
            vals = [float(v) for v in line.split()[1:7]]
            verts.append(vals[:3])
            colors.append(vals[3:6] if len(vals) == 6 else [1.0, 1.0, 1.0])
        elif line.startswith('vt '):
            uvs.append(line.split()[1:3])
        elif line.startswith('usemtl '):
            cur.append(('usemtl', line.split()[1]))
        elif tag == 'f ':
            cur.append(('f', [tuple(int(i) if i else 0 for i in (c.split('/') + ['', ''])[:2]) for c in line.split()[1:]]))
    return np.array(verts), uvs, objects, colors


def kabsch(a, b):
    ca = a.mean(0)
    cb = b.mean(0)
    u, _, vt = np.linalg.svd((a - ca).T @ (b - cb))
    d = np.sign(np.linalg.det(vt.T @ u.T))
    rot = vt.T @ np.diag([1.0, 1.0, d]) @ u.T
    m = np.eye(4)
    m[:3, :3] = rot
    m[:3, 3] = cb - rot @ ca
    return m


def frame(local):
    m = np.eye(4)
    m[:3, :3] = np.array(local[0])
    m[:3, 3] = local[1]
    return m


def used_verts(items):
    return sorted({c[0] for kind, data in items if kind == 'f' for c in data})


def write_part_obj(path, name, verts, colors, uvs, items, transform, shift_of_face):
    idx = used_verts(items)
    out = [f'o {name}']
    remap = {}
    lines_v = []
    faces = []
    for kind, data in items:
        if kind == 'usemtl':
            faces.append(f'usemtl {data}')
            continue
        side = shift_of_face(data)
        corners = []
        for vi, ti in data:
            key = (vi, side[0])
            if key not in remap:
                p = transform(verts[vi - 1]) + side[1]
                lines_v.append('v %.6f %.6f %.6f %.4f %.4f %.4f' % (*p, *colors[vi - 1]))
                remap[key] = len(lines_v)
            corners.append(f'{remap[key]}/{ti}' if ti else f'{remap[key]}')
        faces.append('f ' + ' '.join(corners))
    out += lines_v + [f'vt {u} {v}' for u, v in uvs] + faces
    Path(path).write_text('\n'.join(out) + '\n')
    return len(idx)


def gun_spec(kind, source_dir, xmf):
    rel, root, extra, gap = TURRETS[kind]
    want = json.loads((source_dir / GUNS).read_text())['types'][kind]
    scale = want['scale']
    pose = want.get('pose')
    xml_path = REFS / rel
    rest_obj = WORK / f'gun_{kind}_rest.obj'
    subprocess.run(['x4-xmf', 'ship', str(xml_path), '-o', str(rest_obj), '--colors'], check=True, stdout=subprocess.DEVNULL)
    posed_obj = rest_obj
    if pose:
        posed_obj = WORK / f'gun_{kind}_{pose}.obj'
        subprocess.run(['x4-xmf', 'ship', str(xml_path), '-o', str(posed_obj), '--colors', '--pose', pose], check=True, stdout=subprocess.DEVNULL)
    rv, uvs, robjs, vcols = read_obj(rest_obj)
    pv, _, pobjs, _ = read_obj(posed_obj)
    conns, part_conn, world = connection_frames(xml_path, xmf)
    parts = [p for p in part_conn if not SKIP_PART.search(p) and p in robjs]
    if root:
        keep = subtree(part_conn, conns, root) | set(extra)
        parts = [p for p in parts if p in keep]
    merged = set(parts) if root is None else MERGED & set(parts)
    moves = {}
    for p in robjs:
        idx = used_verts(robjs[p])
        moves[p] = kabsch(rv[[i - 1 for i in idx]], pv[[i - 1 for i in idx]]) if pose and idx else np.eye(4)
    dep = np.array([pv[i - 1] for p in parts for i in used_verts(pobjs[p])])
    lo = dep.min(0) * scale
    hi = dep.max(0) * scale
    offset = np.array([-(lo[0] + hi[0]) / 2, -(lo[1] + hi[1]) / 2, want['y_min'] - lo[2]])
    place = lambda v: np.asarray(v) * scale + offset
    shifts = {0: np.zeros(3), 1: np.zeros(3), -1: np.zeros(3)}
    if gap:
        cradle = np.array([place(pv[i - 1]) for i in used_verts(pobjs['part_gun'])])
        shifts[1] = np.array([gap / 2 - cradle[cradle[:, 0] > 0, 0].min(), 0, 0])
        shifts[-1] = np.array([-gap / 2 - cradle[cradle[:, 0] < 0, 0].max(), 0, 0])

    def side_of(x):
        return 0 if not gap else (1 if x > 0 else -1)

    absolute = {}

    def abs_frame(p):
        if p in absolute:
            return absolute[p]
        cname = part_conn[p]
        parent = conns[cname][0]
        if parent in parts and parent not in merged:
            m = abs_frame(parent) @ scaled(frame(conns[cname][1]))
        else:
            m = moves.get(parent, np.eye(4)) @ frame(world(cname))
            m[:3, 3] = place(m[:3, 3])
        absolute[p] = m
        return m

    def scaled(m):
        m = m.copy()
        m[:3, 3] *= scale
        return m

    out_parts = []
    for p in parts:
        items = robjs[p]
        if p in merged:
            def transform(v, p=p):
                return place(moves[p][:3, :3] @ v + moves[p][:3, 3])
            parent = 'part_gun'
            rel_frame = np.eye(4)
            rot_back = np.eye(3)
        else:
            inv = np.linalg.inv(frame(world(part_conn[p])))
            def transform(v, inv=inv):
                return (inv[:3, :3] @ v + inv[:3, 3]) * scale
            cname = part_conn[p]
            vparent = conns[cname][0]
            parent = vparent if vparent in parts and vparent not in merged else 'part_gun'
            rel_frame = scaled(frame(conns[cname][1])) if parent != 'part_gun' else abs_frame(p)
            rot_back = abs_frame(p)[:3, :3].T

        def shift_of_face(data, p=p, rot_back=rot_back):
            x = np.mean([place(pv[vi - 1])[0] for vi, _ in data])
            side = side_of(x)
            return side, rot_back @ shifts[side]

        obj = WORK / f'{component_name(kind)}_{p}.obj'
        write_part_obj(obj, p, rv, vcols, uvs, items, transform, shift_of_face)
        out_parts.append({'name': p, 'obj': str(obj), 'merged': p in merged, 'parent': parent, 'frame': rel_frame.tolist(), 'tags': [t for t in conns[part_conn[p]][2] if t != 'part']})
    shooters = []
    for name, (vparent, local, tags) in conns.items():
        if 'laser' not in tags or vparent not in parts:
            continue
        world_dep = moves[vparent] @ frame(world(name))
        side = side_of(place(world_dep[:3, 3])[0])
        if vparent in merged:
            m = world_dep.copy()
            m[:3, 3] = place(m[:3, 3]) + shifts[side]
            parent = 'part_gun'
        else:
            m = scaled(frame(local))
            m[:3, 3] += abs_frame(vparent)[:3, :3].T @ shifts[side]
            parent = vparent
        shooters.append({'name': name, 'parent': parent, 'frame': m.tolist(), 'muzzle': (place(world_dep[:3, 3]) + shifts[side]).tolist()})
    deployed = []
    for p in parts:
        for i in used_verts(pobjs[p]):
            q = place(pv[i - 1])
            deployed.append(q + shifts[side_of(q[0])])
    deployed = np.array(deployed)
    ani = None
    if pose:
        src_ani = next((f for f in xml_path.parent.iterdir() if f.name.lower() == xml_path.stem.lower() + '_data.ani'), None)
        ani = {'source': str(src_ani), 'parts': [q['name'] for q in out_parts if not q['merged']], 'scale': scale}
        root_anims = ET.parse(xml_path).getroot().find('component').find('connections')
        block = next((c.find('animations') for c in root_anims.findall('connection') if c.find('animations') is not None and len(c.find('animations'))), None)
        ani['states'] = [(a.get('name'), a.get('start'), a.get('end')) for a in block] if block is not None else []
    spec = {'kind': kind, 'component': component_name(kind), 'parts': out_parts, 'shooters': shooters, 'scale': scale, 'source': rel, 'ani': ani}
    lo = deployed.min(0).round(3)
    hi = deployed.max(0).round(3)
    print(f"{kind}: scale {scale}, parts {[(q['name'], 'ball' if q['merged'] else q['parent']) for q in out_parts]}, {len(shooters)} shooters, muzzles {sorted({round(m['muzzle'][2], 2) for m in shooters})}; deployed x {lo[0]}..{hi[0]} y {lo[2]}..{hi[2]} z {lo[1]}..{hi[1]} (turret axes); guns.json x {want['x']} y {want['y_min']}..{want['y_max']} z {want['z']}")
    return spec


def prepare(kinds, source_dir=SOURCE_DIR):
    xmf = xmf_module()
    WORK.mkdir(parents=True, exist_ok=True)
    ball = source_dir / BALL
    if not ball.is_file():
        sys.exit(f'hcp_turrets: no {BALL} in {source_dir}')
    spec = {'ball': str(ball), 'out_dir': str(ASSETS / SUB), 'turrets': [gun_spec(kind, source_dir, xmf) for kind in kinds]}
    for t in spec['turrets']:
        (WORK / f"spec_{t['kind']}.json").write_text(json.dumps(t, indent=1))
    path = WORK / 'spec.json'
    path.write_text(json.dumps(spec, indent=1))
    return path


def blender_build(spec_path):
    cmd = ['blender', '-b', '--python', str(LIB / 'hcp_build_turrets.py'), '--', str(spec_path)]
    out = subprocess.run(cmd, capture_output=True, text=True)
    lines = [l for l in out.stdout.splitlines() if l.startswith(('TURRET', 'CLIP'))]
    print('\n'.join(lines))
    wanted = len(json.loads(Path(spec_path).read_text())['turrets'])
    if out.returncode != 0 or sum(l.startswith('TURRET') for l in lines) != wanted:
        print(out.stderr[-3000:])
        sys.exit('hcp_turrets: blender build failed')


def winpath(p):
    return 'Z:' + str(p).replace('/', '\\')


def wine_env():
    env = dict(os.environ)
    env['WINEPREFIX'] = str(WINEPREFIX)
    env['WINEDEBUG'] = '-all'
    return env


def export(kinds):
    for kind in kinds:
        blend = ASSETS / SUB / f'{component_name(kind)}.blend'
        out = subprocess.run(['wine', WIN_BLENDER, '-b', winpath(blend), '--python', winpath(LIB / 'hcp_export.py')], cwd=X4, env=wine_env(), capture_output=True, text=True)
        xml = blend.with_suffix('.xml')
        dae = blend.with_name(blend.stem + '_data.dae')
        blend.with_suffix('.blend1').unlink(missing_ok=True)
        ok = xml.exists() and dae.exists() and xml.stat().st_mtime > time.time() - 600
        print(f'export {kind}: {"ok" if ok else "FAILED"}')
        if not ok:
            print(out.stdout[-2000:], out.stderr[-2000:])
            sys.exit(1)


def kill_tree(pid):
    kids = subprocess.run(['pgrep', '-P', str(pid)], capture_output=True, text=True).stdout.split()
    for kid in kids:
        comm = Path(f'/proc/{kid}/comm')
        if comm.exists() and 'wineserver' not in comm.read_text():
            kill_tree(int(kid))
    try:
        os.kill(pid, 15)
    except ProcessLookupError:
        pass


def convert(timeout=600):
    import fcntl
    log = X4 / 'XUConverterLog.txt'
    with open(LOCK, 'w') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        start = time.time()
        proc = subprocess.Popen(['wine', WIN_CONVERTER, winpath(ASSETS), winpath(P1DATA)], cwd=X4, env=wine_env(), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)
        result = None
        while time.time() - start < timeout:
            time.sleep(3)
            if log.exists() and log.stat().st_mtime > start:
                m = re.search(r'Processed:\s*(\d+)\s*-\s*Errors:\s*(\d+)', log.read_text(errors='replace'))
                if m:
                    result = (int(m.group(1)), int(m.group(2)))
                    break
            if proc.poll() is not None and result is None:
                time.sleep(2)
        kill_tree(proc.pid)
    if result is None:
        sys.exit('hcp_turrets: converter timed out')
    print(f'convert: Processed {result[0]} - Errors {result[1]}')
    if result[1]:
        sys.exit('hcp_turrets: converter errors, see XUConverterLog.txt')


def patch_component(xml_path, states):
    text = xml_path.read_text()
    text, k = re.subn(r'(<restriction type="rotation_x">\s*<limits>\s*<min value=")[^"]*("\s*/>\s*<max value=")[^"]*(")', rf'\g<1>{ELEVATION[0]}\g<2>{ELEVATION[1]}\g<3>', text)
    assert k == 1, xml_path
    if states and '<animations>' not in text:
        block = ''.join(f'          <animation name="{n}" start="{a}" end="{b}" />\n' for n, a, b in states)
        text, k = re.subn(r'(<connection name="ConnectionForpart_base" tags=")([^"]*)("[^>]*>\n)', lambda m: m.group(1) + 'animation ' + m.group(2) + m.group(3) + '        <animations>\n' + block + '        </animations>\n', text, count=1)
        assert k == 1, xml_path
    xml_path.write_text(text)
    ET.parse(xml_path)


def install(kinds):
    dest = MOD / 'assets/props/weaponsystems/hcp'
    for kind in kinds:
        name = component_name(kind)
        src = P1DATA / SUB
        spec = json.loads((WORK / f'spec_{kind}.json').read_text())
        shutil.rmtree(dest / f'{name}_data', ignore_errors=True)
        shutil.copytree(src / f'{name}_data', dest / f'{name}_data', ignore=shutil.ignore_patterns('*.dae'))
        shutil.copy2(src / f'{name}.xml', dest / f'{name}.xml')
        ani = dest / f'{name}_data.ani'
        ani.unlink(missing_ok=True)
        info = spec['ani']
        states = []
        if info and info['parts']:
            subprocess.run(['x4-ani', 'subset', info['source'], str(ani), '--parts', ','.join(info['parts']), '--scale', str(info['scale'])], check=True, stdout=subprocess.DEVNULL)
            subprocess.run(['x4-ani', 'static', str(ani), '--parts', 'part_base,part_rotator,part_gun'], check=True, stdout=subprocess.DEVNULL)
            states = info['states']
        patch_component(dest / f'{name}.xml', states)
        n = len(list((dest / f'{name}_data').glob('*-lod0.xmf')))
        print(f'install {kind}: {n} parts' + (f', {ani.name} with {",".join(info["parts"])} x{info["scale"]}' if states else ''))


def find_one(pattern, folder):
    for p in folder.rglob('*'):
        if p.is_file() and re.fullmatch(pattern, p.name, re.I):
            return p
    sys.exit(f'hcp_turrets: {pattern} not found under {folder}')


def scale_damage(text):
    def num(m):
        v = float(m.group(2)) * DAMAGE_FACTOR
        return f'{m.group(1)}="{int(v) if v == int(v) else round(v, 3)}"'

    def tag(m):
        return re.sub(r'\b(value|shield|hull)="([-0-9.eE+]+)"', num, m.group(0))

    return re.sub(r'<(damage|areadamage)\b[^>]*>', tag, text)


def replace_block(text, pattern, new, anchor):
    text = re.sub(pattern, '', text, flags=re.S)
    i = text.rindex(anchor)
    return text[:i] + new + text[i:]


def vanilla_owners(ware_id):
    owners = set()
    for f in sorted(REFS.glob('*/libraries/wares.xml')):
        text = f.read_text()
        m = re.search(rf'<ware id="{ware_id}".*?</ware>', text, re.S)
        if m:
            owners.update(re.findall(r'<owner faction="([^"]+)"', m.group(0)))
        for a in re.finditer(rf'<add sel="[^"]*@id=.{ware_id}.[^"]*"[^>]*>(.*?)</add>', text, re.S):
            owners.update(re.findall(r'<owner faction="([^"]+)"', a.group(1)))
    return sorted(owners)


def data(kinds):
    macros_dir = MOD / 'assets/props/weaponsystems/hcp/macros'
    bullets_dir = MOD / 'assets/fx/weaponfx/macros'
    icons_dir = MOD / 'assets/textures/ui/upgrades'
    for d in (macros_dir, bullets_dir, icons_dir):
        d.mkdir(parents=True, exist_ok=True)
    idx_macros = []
    idx_components = []
    wares = []
    texts = {k: [] for k in TEXTS}
    for i, kind in enumerate(sorted(TURRETS, key=list(TURRETS).index)):
        dlc, vanilla, en_name, es_name = VANILLA[kind]
        comp = component_name(kind)
        macro = comp + '_macro'
        bullet = f'bullet_hcp_turret_m_{kind}_01_mk1_macro'
        tid = TEXT_BASE + 10 * (i + 1)
        vm = find_one(vanilla + '_macro.xml', REFS / dlc / 'assets/props')
        text = vm.read_text()
        old_bullet = re.search(r'<bullet class="([^"]+)"', text).group(1)
        text = re.sub(r'<!--.*?-->\s*', '', text, flags=re.S)
        text = text.replace(f'"{vanilla}_macro"', f'"{macro}"').replace(f'ref="{vanilla}"', f'ref="{comp}"').replace(f'"{old_bullet}"', f'"{bullet}"')
        ident = f'<identification name="{{{TEXT_PAGE},{tid + 1}}}" basename="{{{TEXT_PAGE},{tid + 4}}}" shortname="{{{TEXT_PAGE},{tid + 3}}}" makerrace="argon" description="{{{TEXT_PAGE},{TEXT_BASE + 2}}}" mk="1" />'
        text = re.sub(r'<identification [^>]*/>', ident, text)
        text = re.sub(r'(<rotationspeed max=")([0-9.]+)(")', lambda m: f'{m.group(1)}{round(float(m.group(2)) * ROTATION_FACTOR, 1):g}{m.group(3)}', text)
        (macros_dir / f'{macro}.xml').write_text(text)
        vb = find_one(old_bullet + '.xml', REFS / dlc / 'assets/fx')
        btext = re.sub(r'<!--.*?-->\s*', '', vb.read_text(), flags=re.S).replace(f'"{old_bullet}"', f'"{bullet}"')
        (bullets_dir / f'{bullet}.xml').write_text(scale_damage(btext))
        icon = REFS / dlc / f'assets/textures/ui/upgrades/{vanilla}_macro.gz'
        if icon.exists():
            shutil.copy2(icon, icons_dir / f'{macro}.gz')
        base = 'extensions\\heavy_centaur_prototype\\assets\\'
        idx_macros.append(f'    <entry name="{macro}" value="{base}props\\weaponsystems\\hcp\\macros\\{macro}" />\n')
        idx_macros.append(f'    <entry name="{bullet}" value="{base}fx\\weaponfx\\macros\\{bullet}" />\n')
        idx_components.append(f'    <entry name="{comp}" value="{base}props\\weaponsystems\\hcp\\{comp}" />\n')
        wfile = REFS / dlc / 'libraries/wares.xml'
        ware = re.search(rf'<ware id="{vanilla}".*?</ware>', wfile.read_text(), re.S).group(0)
        ware = ware.replace(f'id="{vanilla}"', f'id="{comp}"').replace(f'ref="{vanilla}_macro"', f'ref="{macro}"')
        ware = re.sub(r'name="\{[0-9]+,[0-9]+\}" description="\{[0-9]+,[0-9]+\}"', f'name="{{{TEXT_PAGE},{tid + 1}}}" description="{{{TEXT_PAGE},{TEXT_BASE + 2}}}"', ware, count=1)
        ware = re.sub(r'\s*<owner faction="[^"]+"\s*/>', '', ware)
        ware = ware.replace('</ware>', ''.join(f'  <owner faction="{f}" />\n' for f in vanilla_owners(vanilla)) + '</ware>')
        ware = re.sub(r'<price min="(\d+)" average="(\d+)" max="(\d+)"', lambda m: '<price min="%d" average="%d" max="%d"' % tuple(round(int(v) * PRICE_FACTOR) for v in m.groups()), ware, count=1)
        lines = ware.split('\n')
        base_indent = len(lines[-1]) - len(lines[-1].lstrip())
        wares.append('\n'.join(['    ' + lines[0]] + ['    ' + l[base_indent:] for l in lines[1:]]) + '\n')
        for lang, (_, full, short, _) in TEXTS.items():
            n = en_name if lang == 'en' else es_name
            texts[lang] += [f'      <t id="{tid + 1}">{full.format(n=n)}</t>\n', f'      <t id="{tid + 3}">{short.format(n=n)}</t>\n', f'      <t id="{tid + 4}">{full.format(n=n)}</t>\n']
        print(f'data {kind}: macro from {vanilla}, bullet {old_bullet} x{DAMAGE_FACTOR}')
    for name, lines in (('index/macros.xml', idx_macros), ('index/components.xml', idx_components)):
        p = MOD / name
        p.write_text(replace_block(p.read_text(), r'[ \t]*<entry name="(turret_arg_m_hcp_|bullet_hcp_turret_)[^\n]*\n', ''.join(lines), '  </add>'))
    p = MOD / 'libraries/wares.xml'
    p.write_text(replace_block(p.read_text(), r'[ \t]*<ware id="turret_arg_m_hcp_.*?</ware>\n', ''.join(wares), '  </add>'))
    for lang, (rel, _, _, desc) in TEXTS.items():
        p = MOD / rel
        lines = [f'      <t id="{TEXT_BASE + 2}">{desc}</t>\n'] + texts[lang]
        p.write_text(replace_block(p.read_text(), r'[ \t]*<t id="4[0-9][0-9]">[^\n]*\n', ''.join(lines), '    </page>'))
    for p in [MOD / 'index/macros.xml', MOD / 'index/components.xml', MOD / 'libraries/wares.xml'] + [MOD / t[0] for t in TEXTS.values()] + list(macros_dir.glob('turret_arg_m_hcp_*')) + list(bullets_dir.glob('*.xml')):
        ET.parse(p)


def main():
    ap = argparse.ArgumentParser(description='Build the HCP turrets: game guns + turret OBJ pieces -> blends -> EgoTools export -> XUConverter -> mod')
    ap.add_argument('step', choices=['all', 'blends', 'export', 'convert', 'install', 'data'])
    ap.add_argument('--source', type=Path, help=f'folder with {BALL} (the gun ball, turret axes: +Y out of the hull, +Z up, origin at the sphere centre) and {GUNS} (scale, pose and placement of each gun; default {SOURCE_DIR}); socket, rear shell and visor are hull pieces (hcp_turret_mounts.py)')
    ap.add_argument('--only', action='append', choices=sorted(TURRETS), help='limit to these turret kinds')
    args = ap.parse_args()
    kinds = args.only or list(TURRETS)
    if args.step in ('all', 'blends'):
        blender_build(prepare(kinds, args.source or SOURCE_DIR))
    if args.step in ('all', 'export'):
        export(kinds)
    if args.step in ('all', 'convert'):
        convert()
    if args.step in ('all', 'install'):
        install(kinds)
    if args.step in ('all', 'data'):
        data(kinds)


if __name__ == '__main__':
    main()
