# Operate the saved island blend: move and hide semantic parts, then restore them.
# Blender: blender --background source/S1_T07_islands.blend --python assemble_island_parts.py

import json
import os
import sys

import bpy

PARTS = ("Beach", "Grass", "Trees", "Reef")
ASSETS = ("ISL-S", "ISL-M", "ISL-L")


def find_part(asset, lod, part):
    name = "%s_LOD%d_%s" % (asset, lod, part)
    obj = bpy.data.objects.get(name)
    if obj is None:
        raise RuntimeError("missing " + name)
    return obj


def sample(obj):
    if obj.type != "MESH" or obj.data is None or len(obj.data.vertices) == 0:
        return None
    bpy.context.view_layer.update()
    point = obj.matrix_world @ obj.data.vertices[0].co
    return [round(point.x, 5), round(point.y, 5), round(point.z, 5)]


def check(asset, lod):
    named = {part: find_part(asset, lod, part) for part in PARTS}
    before = {part: sample(obj) for part, obj in named.items()}
    origin = {part: tuple(obj.location) for part, obj in named.items()}
    named["Trees"].location.x += 4.0
    named["Reef"].location.x -= 3.0
    bpy.context.view_layer.update()
    during = {part: sample(obj) for part, obj in named.items()}
    named["Grass"].hide_set(True)
    named["Reef"].hide_set(True)
    hidden = {
        "beach": named["Beach"].hide_get(),
        "grass": named["Grass"].hide_get(),
        "trees": named["Trees"].hide_get(),
        "reef": named["Reef"].hide_get(),
    }
    named["Grass"].hide_set(False)
    named["Reef"].hide_set(False)
    for part, obj in named.items():
        obj.location = origin[part]
    bpy.context.view_layer.update()
    restored = {part: sample(obj) for part, obj in named.items()}
    triangles = {}
    for part, obj in named.items():
        count = 0 if obj.type != "MESH" or obj.data is None else len(obj.data.polygons)
        triangles[part] = count
    ok = (
        during["Beach"] == before["Beach"]
        and during["Grass"] == before["Grass"]
        and during["Reef"] != before["Reef"]
        and hidden["beach"] is False
        and hidden["grass"] is True
        and hidden["reef"] is True
        and restored == before
        and triangles["Beach"] > 0
        and triangles["Grass"] > 0
        and triangles["Reef"] > 0
    )
    if before["Trees"] is not None:
        ok = ok and during["Trees"] != before["Trees"] and triangles["Trees"] > 0
    else:
        ok = ok and triangles["Trees"] == 0 and asset == "ISL-S"
    return {
        "asset": asset,
        "lod": lod,
        "ok": ok,
        "triangles": triangles,
        "beach_unchanged": during["Beach"] == before["Beach"],
        "reef_moved": during["Reef"] != before["Reef"],
        "trees_moved": None if before["Trees"] is None else during["Trees"] != before["Trees"],
        "hidden": hidden,
        "restored": restored == before,
    }


def main():
    results = [check(asset, lod) for asset in ASSETS for lod in (0, 1, 2)]
    failed = [item for item in results if not item["ok"]]
    payload = {"status": "MATCH" if not failed else "MISMATCH", "results": results}
    text = json.dumps(payload, indent=2)
    print(text)
    out = os.environ.get("T07_PART_REPORT")
    if out:
        with open(out, "w", encoding="utf-8") as handle:
            handle.write(text + "\n")
    if failed:
        sys.exit(1)


if __name__ == "__main__":
    main()
