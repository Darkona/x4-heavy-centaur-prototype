"""X3 BOB1 binary body reader (format per DIMOSUS/x3model docs/formats.md). Big-endian."""
import struct

class R:
    def __init__(s, d): s.d = d; s.p = 0
    def u16(s): v = struct.unpack_from('>H', s.d, s.p)[0]; s.p += 2; return v
    def u32(s): v = struct.unpack_from('>I', s.d, s.p)[0]; s.p += 4; return v
    def i32(s): v = struct.unpack_from('>i', s.d, s.p)[0]; s.p += 4; return v
    def arr(s, n):
        v = struct.unpack_from('>%di' % n, s.d, s.p); s.p += 4 * n; return v
    def str(s):
        e = s.d.index(b'\0', s.p); v = s.d[s.p:e].decode('latin-1'); s.p = e + 1; return v
    def peek(s): return s.d[s.p:s.p + 4].decode('latin-1')
    def tag(s): v = s.peek(); s.p += 4; return v
    def expect(s, t):
        g = s.tag()
        assert g == t, (t, g, s.p)

PARAM_N = {0: 1, 1: 1, 2: 1, 3: 2, 4: 3, 5: 4, 6: 9, 7: 16}

def read_material(r, ver):
    m = {'index': r.u16()}
    flags = r.u32() if ver == 6 else 0
    m['flags'] = flags
    if ver == 6 and flags & 0x02000000:
        m['technique'] = r.u16(); m['effect'] = r.str(); params = {}
        for _ in range(r.u16()):
            name = r.str(); t = r.u16()
            if t == 8: params[name] = r.str()
            else: params[name] = r.arr(PARAM_N[t])
        m['params'] = params
        return m
    m['texture'] = r.str() if ver == 6 else r.u16()
    r.arr  # words are u16
    for _ in range(14): r.u16()
    if ver < 6: r.u16()
    r.u16()
    for _ in range(5 if ver == 6 else 3):
        if ver == 6: r.str()
        else: r.u16()
        r.u16()
    return m

def read_lod(r):
    lod = {'value': r.i32(), 'flags': r.u32()}
    if r.peek() == 'BONE':
        r.tag()
        for _ in range(r.i32()): r.str()
        r.expect('/BON')
    r.expect('POIN')
    n = r.i32()
    pos = []; uv = []; uv2 = []; nor = []
    for _ in range(n):
        f = r.u16()
        p = u = u2 = nn = (0, 0, 0)
        if f & 1: p = r.arr(3)
        if f & 2:
            u = r.arr(2)
            if f & 4: u2 = r.arr(2)
        if f & 8: nn = r.arr(3)
        if f & 16: r.u32()
        pos.append(p); uv.append(u[:2]); uv2.append(u2[:2]); nor.append(nn)
    lod.update(pos=pos, uv=uv, uv2=uv2, nor=nor)
    r.expect('/POI')
    if r.peek() == 'WEIG':
        r.tag(); assert r.i32() == n
        for _ in range(n):
            for _ in range(r.u16()): r.u16(); r.i32()
        r.expect('/WEI')
    r.expect('PART')
    parts = []
    for _ in range(r.i32()):
        fl = r.u32(); groups = []
        for _ in range(r.u16()):
            mat = r.i32(); nf = r.i32()
            faces = [r.arr(4) for _ in range(nf)]
            if fl & 0x10000000:
                nt = r.i32(); r.p += nt * 28
            groups.append((mat, faces))
        if fl & 0x10000000: r.p += 40
        parts.append(groups)
    lod['parts'] = parts
    r.expect('/PAR')
    return lod

def read_bob(d):
    r = R(d); r.expect('BOB1'); out = {'mats': [], 'lods': []}
    while True:
        t = r.tag()
        if t == '/BOB': break
        if t == 'INFO': out['info'] = r.str(); r.expect('/INF')
        elif t == 'NAME': r.str(); r.expect('/NAM')
        elif t == 'VERS': r.u32(); r.expect('/VER')
        elif t == 'SND1': r.u32(); r.expect('/SND')
        elif t in ('MAT3', 'MAT5', 'MAT6'):
            v = int(t[3])
            out['mats'] = [read_material(r, v) for _ in range(r.i32())]
            r.expect('/MAT')
        elif t == 'BODY':
            out['lods'] = [read_lod(r) for _ in range(r.u16())]
            r.expect('/BOD')
        else: raise ValueError(t)
    return out
