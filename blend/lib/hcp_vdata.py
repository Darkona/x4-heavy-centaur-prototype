import bpy


VDATA = ('col', 'paintmodmask', 'dirt', 'multimatsmooth', 'multimatmetal', 'multimatid')


def add_vertex_data(ob):
    me = ob.data
    if 'col' in me.color_attributes and all(nm in me.color_attributes for nm in VDATA):
        return
    for nm in ('col', 'ao') + VDATA:
        if nm in me.color_attributes:
            me.color_attributes.remove(me.color_attributes[nm])
    pattern = {i for i, m in enumerate(me.materials) if m is not None and 'hullpattern' in m.name}
    n = len(me.loops)
    col = me.color_attributes.new('col', 'BYTE_COLOR', 'CORNER')
    col.data.foreach_set('color', [1.0, 1.0, 1.0, 1.0] * n)
    pm = me.color_attributes.new('paintmodmask', 'BYTE_COLOR', 'CORNER')
    flat = [0.0, 0.0, 0.0, 1.0] * n
    for p in me.polygons:
        if p.material_index in pattern:
            for li in p.loop_indices:
                flat[li * 4] = 1.0
    pm.data.foreach_set('color', flat)
    for nm in VDATA[2:]:
        a = me.color_attributes.new(nm, 'BYTE_COLOR', 'CORNER')
        a.data.foreach_set('color', [0.0, 0.0, 0.0, 1.0] * n)
