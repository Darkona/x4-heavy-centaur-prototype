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
PIECE_PREFIXES = {'gun': ('ball',), 'gun_flak': ('flak',)}
MOD = REPO / 'mod/heavy_centaur_prototype'
WINEPREFIX = HOME / '.local/share/wineprefixes/egosoft'
WIN_BLENDER = r'C:\Program Files\Blender Foundation\Blender 4.5\blender.exe'
WIN_CONVERTER = r'C:\Program Files\EGOSOFT\Egosoft Blender Mod Tools\Converter\XUConverter.exe'
LOCK = X4 / '.xuconverter.lock'

TURRETS = {
    'laser': ('base/assets/props/WeaponSystems/standard/weapon_gen_m_laser_01_mk1.xml', None, 2, None),
    'gatling': ('base/assets/props/WeaponSystems/heavy/turret_arg_m_gatling_02_mk1.xml', 'part_gun', 1, 1.0),
    'plasma': ('base/assets/props/WeaponSystems/heavy/weapon_gen_m_plasma_01_mk1.xml', None, 2, None),
    'beam': ('base/assets/props/WeaponSystems/energy/weapon_gen_m_beam_01_mk1.xml', None, 2, None),
    'shotgun': ('base/assets/props/WeaponSystems/standard/turret_arg_m_shotgun_02_mk1.xml', 'part_gun', 1, 1.0),
    'flak': ('base/assets/props/WeaponSystems/heavy/turret_arg_m_flak_02_mk1.xml', 'part_gun', 1, 0.67),
    'borlaser': ('ego_dlc_boron/assets/props/weaponsystems/boron/turret_bor_m_laser_02_mk1.xml', 'part_gun', 1, 1.0),
    'railgun': ('ego_dlc_boron/assets/props/weaponsystems/boron/weapon_bor_m_railgun_01_mk1.xml', None, 1, 1.0),
    'arc': ('ego_dlc_boron/assets/props/weaponsystems/boron/turret_bor_m_arc_02_mk1.xml', 'part_gun', 1, 1.0),
}
GEOMETRY = {
    'sphere_radius': 3.65,
    'shell_radius': 3.79,
    'socket_radius': 5.12,
    'slot_rear': -0.42,
    'socket_front': -1.4,
    'dual_centres': [-1.095, 1.095],
    'dual_slot': 1.97,
    'side_gap': 0.04,
}
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
DEPLOYED_POSE = 'turret_active'
DAMAGE_FACTOR = 1.0
PRICE_FACTOR = 1.0
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


def pieces(source_dir):
    found = {part: sorted(str(p) for p in source_dir.glob('*.obj') if p.stem.lower().startswith(prefixes) and (part == 'gun_flak' or 'flak' not in p.stem.lower())) for part, prefixes in PIECE_PREFIXES.items()}
    for part in PIECE_PREFIXES:
        if not found[part]:
            sys.exit(f'hcp_turrets: no {part} meshes in {source_dir}')
    for part, paths in found.items():
        print(f'pieces {part}: ' + ', '.join(Path(p).name for p in paths))
    return found


def obj_parts(path):
    verts = []
    parts = {}
    cur = None
    for line in open(path):
        if line.startswith(('o ', 'g ')):
            cur = line.split()[1]
        elif line.startswith('v '):
            verts.append([float(v) for v in line.split()[1:4]])
            parts.setdefault(cur, []).append(len(verts) - 1)
    return {name: [verts[i] for i in idx] for name, idx in parts.items()}


def posed_parts(xml_path, posed_obj):
    import numpy as np
    rest_obj = posed_obj.with_name(posed_obj.stem + '_rest.obj')
    subprocess.run(['x4-xmf', 'ship', str(xml_path), '-o', str(rest_obj)], check=True, stdout=subprocess.DEVNULL)
    rest = obj_parts(rest_obj)
    posed = obj_parts(posed_obj)
    moves = {}
    for name, pts in posed.items():
        a = np.array(rest.get(name, []))
        b = np.array(pts)
        if len(a) != len(b) or len(a) < 3:
            continue
        ca = a.mean(0)
        cb = b.mean(0)
        u, _, vt = np.linalg.svd((a - ca).T @ (b - cb))
        d = np.sign(np.linalg.det(vt.T @ u.T))
        rot = vt.T @ np.diag([1.0, 1.0, d]) @ u.T
        moves[name] = (rot.tolist(), (cb - rot @ ca).tolist())
    return moves


def prepare(kinds, source_dir=SOURCE_DIR):
    xmf = xmf_module()
    WORK.mkdir(parents=True, exist_ok=True)
    spec = {'pieces': pieces(source_dir), 'out_dir': str(ASSETS / SUB), 'geometry': GEOMETRY, 'turrets': []}
    for kind in kinds:
        rel, root_part, count, scale = TURRETS[kind]
        xml_path = REFS / rel
        obj = WORK / f'gun_{kind}.obj'
        pose = DEPLOYED_POSE if root_part else None
        subprocess.run(['x4-xmf', 'ship', str(xml_path), '-o', str(obj)] + (['--pose', pose] if pose else []), check=True, stdout=subprocess.DEVNULL)
        moves = posed_parts(xml_path, obj) if pose else {}
        conns, part_conn, world = connection_frames(xml_path, xmf)
        parts = [p for p in part_conn if not SKIP_PART.search(p)]
        if root_part:
            parts = [p for p in parts if p in subtree(part_conn, conns, root_part)]
        shooters = []
        for name, (parent, _, tags) in conns.items():
            if 'laser' in tags and (not root_part or parent in parts):
                pos = world(name)[1]
                if parent in moves:
                    rot, shift = moves[parent]
                    pos = [sum(rot[i][k] * pos[k] for k in range(3)) + shift[i] for i in range(3)]
                shooters.append([round(v, 6) for v in pos])
        spec['turrets'].append({'kind': kind, 'component': component_name(kind), 'obj': str(obj), 'parts': parts, 'shooters': shooters, 'count': count, 'scale': scale, 'source': rel})
        print(f'{kind}: {len(parts)} parts {parts}, {len(shooters)} shooters {shooters}')
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


def patch_component(xml_path):
    text = xml_path.read_text()
    text = re.sub(r'(<restriction type="rotation_x">\s*<limits>\s*<min value=")-0\.99\d*(")', r'\g<1>0\2', text)
    xml_path.write_text(text)
    ET.parse(xml_path)


def install(kinds):
    dest = MOD / 'assets/props/weaponsystems/hcp'
    for kind in kinds:
        name = component_name(kind)
        src = P1DATA / SUB
        shutil.rmtree(dest / f'{name}_data', ignore_errors=True)
        shutil.copytree(src / f'{name}_data', dest / f'{name}_data', ignore=shutil.ignore_patterns('*.dae'))
        shutil.copy2(src / f'{name}.xml', dest / f'{name}.xml')
        ani = src / f'{name}_data.ani'
        if ani.exists():
            shutil.copy2(ani, dest / ani.name)
        patch_component(dest / f'{name}.xml')
        n = len(list((dest / f'{name}_data').glob('*-lod0.xmf')))
        print(f'install {kind}: {n} parts')


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
    ap.add_argument('--source', type=Path, help=f'folder of turret OBJs in turret axes (+Y out of the hull, +Z up, origin at the sphere centre); file name prefixes pick the part_gun pieces: ball* for the twin-gun turrets, flak* for the single-gun turrets (default {SOURCE_DIR}); socket, rear shell and visor are hull pieces (hcp_turret_mounts.py)')
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
