import json
from pathlib import Path

import bpy


def _import_obj(path):
    before = set(bpy.data.objects)
    bpy.ops.wm.obj_import(filepath=str(path), forward_axis='Y', up_axis='Z')
    new = [o for o in bpy.data.objects if o not in before]
    if len(new) != 1:
        raise RuntimeError(f"{path.name}: expected one object, got {len(new)}")
    tmp = new[0]
    mesh = tmp.data
    mesh.transform(tmp.matrix_world)
    bpy.data.objects.remove(tmp, do_unlink=True)
    return mesh


def _slot(mesh, name):
    for i, m in enumerate(mesh.materials):
        if m and m.name == name:
            return i
    mat = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    mesh.materials.append(mat)
    return len(mesh.materials) - 1


def adopt(folder, tag, protect_prefixes=("hcr_turret_mount_", "hcr_dock_", "hcr_bridge_")):
    folder = Path(folder)
    changes = json.loads((folder / "changes.json").read_text())
    fmap_path = folder / "face_source_map.json"
    fmap = json.loads(fmap_path.read_text()) if fmap_path.exists() else {}
    overrides = changes.get("material_overrides", {})
    report = []
    for name in changes.get("replaced", []):
        if name.startswith(protect_prefixes):
            raise RuntimeError(f"{name} is protected")
        obj = bpy.data.objects[name]
        old = obj.data
        old.use_fake_user = True
        old.name = f"bak_{tag}_{name}"
        mesh = _import_obj(folder / "meshes" / f"{name}.obj")
        mesh.transform(obj.matrix_world.inverted())
        mesh.materials.clear()
        for m in old.materials:
            mesh.materials.append(m)
        src = fmap.get(name, [])
        old_idx = [p.material_index for p in old.polygons]
        for i, poly in enumerate(mesh.polygons):
            if i < len(src) and 0 <= src[i] < len(old_idx):
                poly.material_index = old_idx[src[i]]
        for mat_name, faces in overrides.get(name, {}).items():
            k = _slot(mesh, mat_name)
            for i in faces:
                mesh.polygons[i].material_index = k
        mesh.name = name
        obj.data = mesh
        report.append(f"replaced {name}: {len(mesh.polygons)} faces")
    for entry in changes.get("new", []):
        name = entry["name"]
        mesh = _import_obj(folder / "meshes" / f"new_{name}.obj")
        mesh.name = name
        mesh.materials.clear()
        if entry.get("material"):
            _slot(mesh, entry["material"])
        obj = bpy.data.objects.new(name, mesh)
        parts = name.split("_")
        sibling = None
        for n in range(len(parts) - 1, 1, -1):
            prefix = "_".join(parts[:n])
            sibling = next((o for o in bpy.data.objects if o.name.startswith(prefix) and o.name != name and o.users_collection), None)
            if sibling:
                break
        coll = sibling.users_collection[0] if sibling else bpy.context.scene.collection
        coll.objects.link(obj)
        report.append(f"new {name} in {coll.name}")
    for name in changes.get("deleted", []):
        obj = bpy.data.objects.get(name)
        if obj is None:
            report.append(f"deleted {name}: not found")
            continue
        if obj.type == 'MESH':
            obj.data.use_fake_user = True
            obj.data.name = f"bak_{tag}_{name}"
        bpy.data.objects.remove(obj, do_unlink=True)
        report.append(f"deleted {name}")
    return report
