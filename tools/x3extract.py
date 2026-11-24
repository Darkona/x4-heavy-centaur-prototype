"""Extract the Heavy Centaur Prototype model files from the X3 cats into source/x3 (game-relative paths).
Scene: the official 06.cat revision (the base game's patched one), not the owner's 14.cat / addon/06.cat mod revision."""
import sys, os, re
sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, os.path.expanduser('~/development/python/modkeeper/src'))
from pathlib import Path
import x3cat, x3bob
from modkeeper.games.x3tc.catdat import CatFile
from modkeeper.games.x3tc import pck

OUT = Path(os.path.expanduser('~/development/x4/heavy-centaur/source/x3'))
SCENE_CAT = '06.cat'
SCENE = 'objects/ships/mm6/argon_mm6_scene.pbd'
SKIP = ('cameradummy',)

def save(rel, data):
    p = OUT / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_bytes(data)

def main():
    idx = x3cat.index()
    cf = CatFile(Path(x3cat.G) / SCENE_CAT)
    scene = pck.unpack(cf.read(cf.find(SCENE)))
    save('objects/ships/mm6/argon_mm6_scene.bod', scene)
    text = re.sub(r'/[^\n]*', '', scene.decode('latin-1'))
    bodies = sorted(set(re.findall(r'B\s+(ships\\[^;\s]+)\s*;', text)))
    texs = set()
    for b in bodies + ['ships\\mm6\\argon_mm6']:
        rel = 'objects/' + b.replace('\\', '/').lower()
        if rel.rsplit('/', 1)[-1] in SKIP: continue
        for ext in ('.pbb', '.bob', '.pbd', '.bod'):
            if rel + ext in idx: break
        else:
            print('missing body', b); continue
        cf2, e, src = idx[rel + ext]
        raw = pck.unpack(cf2.read(e)) if ext.startswith('.p') else cf2.read(e)
        outext = '.bob' if ext in ('.pbb', '.bob') else '.bod'
        save(rel + outext, raw)
        print('body', rel + outext, src)
        if raw[:4] == b'BOB1':
            for m in x3bob.read_bob(raw)['mats']:
                for k, v in m.get('params', {}).items():
                    if k in ('t_DiffuseTexture', 't_AlphaTexture', 't_BumpTexture', 't_SpecularTexture', 't_LightMapTexture') and isinstance(v, str) and 'NONE_' not in v.upper():
                        texs.add(v.replace('\\', '/').rsplit('/', 1)[-1].rsplit('.', 1)[0].lower())
    for t in sorted(texs):
        key = 'dds/' + t + '.pck'
        if key not in idx: print('missing tex', t); continue
        cf2, e, src = idx[key]
        save('dds/' + t + '.dds', pck.unpack(cf2.read(e)))
    print(len(bodies), 'scene bodies,', len(texs), 'textures')

main()
