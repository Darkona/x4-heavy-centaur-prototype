"""Convert the extracted X3 scene (bod text) + bodies (bob) into OBJ/MTL (+PNG textures) for Blender.
usage: x3convert.py SRC_X3_DIR OUT_DIR [units_per_metre=500]
Output axes: X3 (x right, y up, z forward, left-handed) -> (x, y, -z), right-handed Y-up; face winding flipped."""
import sys, os, re, math
sys.path.insert(0, os.path.dirname(__file__))
from pathlib import Path
import x3bob
from PIL import Image

SKIP_BODIES = ('cameradummy',)

def parse_scene(text):
    text = re.sub(r'/[^\n]*', '', text)
    parts = []
    for m in re.finditer(r'P\s+(\d+)\s*;\s*B\s+([^;]+);(.*?)(?=\bP\s+\d+\s*;\s*B|\Z)', text, re.S):
        n, body, rest = int(m.group(1)), m.group(2).strip(), m.group(3)
        name = re.search(r'\bN\s*([^;]+);', rest)
        key = re.search(r'\{\s*(0x[0-9a-fA-F]+)\s*;([^}]*)\}', rest)
        if not key: continue
        flags = int(key.group(1), 16)
        f = [float(x) for x in key.group(2).split(';') if x.strip()]
        assert flags & 0x2 and not flags & 0x10, flags
        parts.append(dict(n=n, body=body, name=name.group(1).strip() if name else body, pos=f[0:3], rot=f[3:7]))
    return parts

def quat_mat(w, x, y, z):
    n = math.sqrt(w*w + x*x + y*y + z*z) or 1.0
    w, x, y, z = w/n, x/n, y/n, z/n
    return [[1-2*(y*y+z*z), 2*(x*y-z*w), 2*(x*z+y*w)],
            [2*(x*y+z*w), 1-2*(x*x+z*z), 2*(y*z-x*w)],
            [2*(x*z-y*w), 2*(y*z+x*w), 1-2*(x*x+y*y)]]

def part_transform(p):
    ang, ax, ay, az = p['rot']
    h = ang * math.pi
    s = math.sin(h)
    # engine stores the axis negated; X3 -> mirrored space turns (ax,ay,az) into (-ax,-ay,az) after un-negating
    R = quat_mat(math.cos(h), -ax * s, -ay * s, az * s)
    x, y, z = p['pos']
    return R, (x, y, -z)

def tex_name(m):
    t = m.get('params', {}).get('t_DiffuseTexture') if 'params' in m else None
    return t.replace('\\', '/').rsplit('/', 1)[-1].rsplit('.', 1)[0] if t else 'untextured_%d' % m['index']

def main():
    src, out = Path(sys.argv[1]), Path(sys.argv[2])
    upm = float(sys.argv[3]) if len(sys.argv) > 3 else 500.0
    k = 1.0 / upm
    out.mkdir(parents=True, exist_ok=True)
    (out / 'textures').mkdir(exist_ok=True)
    parts = parse_scene((src / 'objects/ships/mm6/argon_mm6_scene.bod').read_text('latin-1'))
    obj, mats_used = [], {}
    vbase = vtbase = vnbase = 0
    obj.append('mtllib heavy_centaur_proto.mtl')
    lo = [1e18]*3; hi = [-1e18]*3
    cache = {}
    for p in parts:
        b = p['body']
        if not b.startswith('ships\\') or b.rsplit('\\', 1)[-1] in SKIP_BODIES: continue
        f = src / 'objects' / (b.replace('\\', '/').lower() + '.bob')
        if not f.exists(): print('skip', b); continue
        if f not in cache: cache[f] = x3bob.read_bob(f.read_bytes())
        bob = cache[f]
        lod = bob['lods'][0]
        sc = lod['value'] / 65536.0
        R, t = part_transform(p)
        obj.append('o %s_%d' % (re.sub(r'\W', '_', p['name']), p['n']))
        for (px, py, pz) in lod['pos']:
            v = (px * sc, py * sc, -pz * sc)
            w = [sum(R[r][c] * v[c] for c in range(3)) + t[r] for r in range(3)]
            for i in range(3):
                lo[i] = min(lo[i], w[i]); hi[i] = max(hi[i], w[i])
            obj.append('v %.5f %.5f %.5f' % (w[0]*k, w[1]*k, w[2]*k))
        for (u, v) in lod['uv']:
            obj.append('vt %.6f %.6f' % (u / 65536.0, 1.0 - v / 65536.0))
        for (nx, ny, nz) in lod['nor']:
            a, b2, c = nx, ny, -nz
            a, b2, c = (sum(R[r][i] * (a, b2, c)[i] for i in range(3)) for r in range(3))
            l = math.sqrt(a*a + b2*b2 + c*c) or 1.0
            obj.append('vn %.5f %.5f %.5f' % (a/l, b2/l, c/l))
        mats = bob['mats']
        for groups in lod['parts']:
            for mi, faces in groups:
                mname = tex_name(mats[mi]) if 0 <= mi < len(mats) else 'none'
                mats_used[mname] = 1
                obj.append('usemtl ' + mname)
                for (a, b2, c, _w) in faces:
                    ia, ib, ic = (vbase + a + 1), (vbase + c + 1), (vbase + b2 + 1)
                    obj.append('f %d/%d/%d %d/%d/%d %d/%d/%d' % (ia, ia - vbase + vtbase, ia - vbase + vnbase, ib, ib - vbase + vtbase, ib - vbase + vnbase, ic, ic - vbase + vtbase, ic - vbase + vnbase))
        vbase += len(lod['pos']); vtbase += len(lod['uv']); vnbase += len(lod['nor'])
    (out / 'heavy_centaur_proto.obj').write_text('\n'.join(obj) + '\n')
    mtl = []
    for m in sorted(mats_used):
        mtl.append('newmtl %s\nKd 1 1 1\nKs 0.2 0.2 0.2\nNs 30' % m)
        d = src / 'dds' / (m.lower() + '.dds')
        if d.exists():
            try:
                im = Image.open(d); im.load()
                png = 'textures/%s.png' % m
                im.save(out / png)
                mtl.append('map_Kd ' + png)
                if im.mode == 'RGBA' and im.getchannel('A').getextrema()[0] < 250: mtl.append('map_d ' + png)
            except Exception as e: print('tex fail', m, e)
        mtl.append('')
    (out / 'heavy_centaur_proto.mtl').write_text('\n'.join(mtl))
    size = [(hi[i] - lo[i]) for i in range(3)]
    print('bbox units (x,y,z):', [round(s) for s in size], 'metres @%g u/m:' % upm, [round(s * k, 2) for s in size])
    print('bbox min/max (m):', [round(x * k, 2) for x in lo], [round(x * k, 2) for x in hi])

main()
