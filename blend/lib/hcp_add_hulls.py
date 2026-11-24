import bpy, glob, os
D = '/home/darkona/development/x4/heavy-centaur/blend/lib/vhacd'
scene = bpy.context.scene
if 'Hulls' in bpy.data.collections:
    hc = bpy.data.collections['Hulls']
    for o in list(hc.objects):
        bpy.data.objects.remove(o, do_unlink=True)
else:
    hc = bpy.data.collections.new('Hulls')
    scene.collection.children.link(hc)
files = sorted(glob.glob(os.path.join(D, 'part_main[0-9][0-9][0-9].obj')))
for i, f in enumerate(files):
    bpy.ops.wm.obj_import(filepath=f, forward_axis='Y', up_axis='Z')
    for ob in list(bpy.context.selected_objects):
        for c in list(ob.users_collection):
            c.objects.unlink(ob)
        hc.objects.link(ob)
        ob.name = 'part_main_hull_%d' % i
        ob.data.name = ob.name
        ob.display_type = 'WIRE'
        ob.select_set(False)
for m in list(bpy.data.materials):
    if m.users == 0:
        bpy.data.materials.remove(m)
bpy.ops.wm.save_mainfile()
print('HULLS', len(hc.objects), 'verts', sum(len(o.data.vertices) for o in hc.objects))
