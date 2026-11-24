import sys,glob,os
sys.path.insert(0,os.path.expanduser('~/development/python/modkeeper/src'))
from modkeeper.games.x3tc.catdat import CatFile
G="/media/darkona/Lake/Steam/steamapps/common/X3 Terran Conflict"
def index():
    """returns dict lowerpath -> (CatFile, entry, source); later cats override earlier"""
    idx={}
    for sub in ("","addon","addon2"):
        for c in sorted(glob.glob(f"{G}/{sub}/[0-9][0-9].cat".replace("//","/"))):
            cf=CatFile(__import__('pathlib').Path(c))
            for e in cf.entries: idx[e.path.lower()]=(cf,e,os.path.relpath(c,G))
    return idx
def read(idx,p):
    cf,e,_=idx[p.lower()]; return cf.read(e)
