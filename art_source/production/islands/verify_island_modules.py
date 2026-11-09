"""Development-side checks for the T07 module package. Not an acceptance verdict."""

import hashlib
import json
import os
import struct
import sys

import geometry_hash as geo

SPECS = {
    "ISL-S": {"diameter": 48.0, "caps": [1500, 600, 200]},
    "ISL-M": {"diameter": 110.0, "caps": [3500, 1400, 400]},
    "ISL-L": {"diameter": 200.0, "caps": [7000, 2500, 700]},
}
PORT_CAPS = [2500, 900, 300]
KINDS = {"land", "shallow", "reef"}
POLYGON_KEYS = {"polygon_id", "kind", "outer", "holes"}
CONTRACT_CLEARANCE_M = 12.0
CAPSULE_TIP_M = 16.0  # SHIP-H length 32, R_nav 8, tip = 8 + 8


def self_check():
    square = [[0, 0], [200000, 0], [200000, 200000], [0, 200000]]
    if geo.shoelace_twice(square) <= 0:
        raise RuntimeError("square shoelace")
    if not geo.point_in_ring(1.0, 1.0, square):
        raise RuntimeError("point inside square")
    if geo.point_in_ring(3.0, 1.0, square):
        raise RuntimeError("point outside square")
    digest = geo.geometry_sha({"b": 1, "a": [2, 1]})
    if len(digest) != 64:
        raise RuntimeError("sha length")


def load_json(path):
    with open(path, "r", encoding="utf-8") as handle:
        return json.load(handle)


def check_ring(ring, name, want_ccw):
    errors = geo.ring_errors(ring, name)
    area = geo.shoelace_twice(ring)
    if want_ccw and area <= 0:
        errors.append(name + " is not counterclockwise")
    if not want_ccw and area >= 0:
        errors.append(name + " is not clockwise")
    return errors


def check_polygon(polygon, name):
    errors = []
    if set(polygon.keys()) != {"polygon_id", "kind", "outer", "holes"}:
        errors.append(name + " keys " + ",".join(sorted(polygon.keys())))
    if polygon.get("kind") not in KINDS:
        errors.append(name + " kind " + str(polygon.get("kind")))
    errors.extend(check_ring(polygon["outer"], name + " outer", True))
    for index, hole in enumerate(polygon["holes"]):
        errors.extend(check_ring(hole, "%s hole %d" % (name, index), False))
    return errors


def decimals_match(ring_m, ring_i):
    if len(ring_m) != len(ring_i):
        return False
    for point, ints in zip(ring_m, ring_i):
        if list(point.keys()) != ["x_m", "z_m"] and set(point.keys()) != {"x_m", "z_m"}:
            return False
        if geo.q_int(point["x_m"]) != ints[0] or geo.q_int(point["z_m"]) != ints[1]:
            return False
    return True


def png_size(path):
    with open(path, "rb") as handle:
        header = handle.read(24)
    if header[:8] != b"\x89PNG\r\n\x1a\n":
        raise RuntimeError("not png " + path)
    return struct.unpack(">II", header[16:24])


def verify(package_path, metrics_path=None):
    self_check()
    errors = []
    package = load_json(package_path)
    if package.get("record_type") == "WorldNavigationData":
        errors.append("package is a world record")
    if package.get("record_type") != "IslandModulePackage":
        errors.append("record_type " + str(package.get("record_type")))
    if "islands" in package and isinstance(package["islands"], list) and len(package["islands"]) == 12:
        errors.append("package carries a 12-island world list")
    canon = package["canonical_integers"]
    digest = geo.geometry_sha(canon)
    if digest != package.get("geometry_sha"):
        errors.append("geometry_sha mismatch")
    archetypes = canon["archetypes"]
    if [item["archetype_id"] for item in archetypes] != ["ISL-L", "ISL-M", "ISL-S"] and [
        item["archetype_id"] for item in archetypes
    ] != sorted(SPECS):
        # Sorted by id: ISL-L, ISL-M, ISL-S.
        if [item["archetype_id"] for item in archetypes] != sorted(SPECS):
            errors.append("archetype order")
    by_id = {item["archetype_id"]: item for item in archetypes}
    if set(by_id) != set(SPECS):
        errors.append("archetype set")
    port = canon["port_attachment"]
    if port["landmark_id"] == port["anchor_id"]:
        errors.append("landmark and anchor ids collide")
    if port["host_archetype_id"] != "ISL-L":
        errors.append("port host")
    for archetype_id, spec in SPECS.items():
        module = by_id[archetype_id]
        kinds = {}
        for polygon in module["polygons"]:
            errors.extend(check_polygon(polygon, archetype_id + " " + polygon["polygon_id"]))
            kinds.setdefault(polygon["kind"], []).append(polygon)
        if len(kinds.get("land", [])) != 1 or len(kinds.get("shallow", [])) != 1:
            errors.append(archetype_id + " needs one land and one shallow")
        if not kinds.get("reef"):
            errors.append(archetype_id + " needs a reef polygon")
        land = kinds["land"][0]
        shallow = kinds["shallow"][0]
        diameter = 2.0 * geo.max_radius_m(land["outer"])
        if abs(diameter - spec["diameter"]) > 1.1e-4:
            errors.append("%s diameter %.6f" % (archetype_id, diameter))
        if not geo.point_in_polygon(0.0, 0.0, land):
            errors.append(archetype_id + " origin outside land")
        if geo.point_in_polygon(0.0, 0.0, shallow):
            errors.append(archetype_id + " origin inside shallow")
        if shallow["holes"] != [list(reversed(land["outer"]))]:
            errors.append(archetype_id + " shallow hole is not the reversed land ring")
    host = by_id["ISL-L"]
    solids = list(host["polygons"]) + list(port["polygons"])
    for polygon in port["polygons"]:
        errors.extend(check_polygon(polygon, polygon["polygon_id"]))
        if polygon["kind"] != "land":
            errors.append("pier kind must stay land")
    pier = port["polygons"][0]
    # The whole pier rectangle, including gaps between piles, is land.
    xs = [point[0] / geo.QUANTUM for point in pier["outer"]]
    zs = [point[1] / geo.QUANTUM for point in pier["outer"]]
    for u in (0.2, 0.5, 0.8):
        for v in (0.2, 0.5, 0.8):
            x = min(xs) + (max(xs) - min(xs)) * u
            z = min(zs) + (max(zs) - min(zs)) * v
            if not geo.point_in_polygon(x, z, pier):
                errors.append("pier interior sample missed at %.3f %.3f" % (x, z))
    ax = port["anchor_q"][0] / geo.QUANTUM
    az = port["anchor_q"][1] / geo.QUANTUM
    lx = port["landmark_q"][0] / geo.QUANTUM
    lz = port["landmark_q"][1] / geo.QUANTUM
    if not geo.point_in_polygon(lx, lz, host["polygons"][0] if False else next(
        polygon for polygon in host["polygons"] if polygon["kind"] == "land"
    )):
        errors.append("landmark is not on ISL-L land")
    clearance = None
    for polygon in solids:
        dist = geo.distance_to_polygon(ax, az, polygon)
        clearance = dist if clearance is None else min(clearance, dist)
    if clearance is None or clearance < CONTRACT_CLEARANCE_M:
        errors.append("anchor clearance below 12 m: %s" % clearance)
    if clearance is None or clearance < CAPSULE_TIP_M:
        errors.append("anchor clearance ignores SHIP-H capsule tip: %s" % clearance)
    if (lx, lz) == (ax, az):
        errors.append("anchor coordinate equals landmark")
    # Decimal mirror follows the integers.
    mirror = {item["archetype_id"]: item for item in package["modules_xz_m"]}
    for archetype_id, module in by_id.items():
        for polygon, copy in zip(module["polygons"], mirror[archetype_id]["polygons"]):
            if set(copy.keys()) != POLYGON_KEYS:
                errors.append("decimal keys")
            if copy["kind"] != polygon["kind"] or copy["polygon_id"] != polygon["polygon_id"]:
                errors.append("decimal identity")
            if not decimals_match(copy["outer"], polygon["outer"]):
                errors.append("decimal outer drift " + copy["polygon_id"])
            if len(copy["holes"]) != len(polygon["holes"]):
                errors.append("decimal holes")
            for hole_m, hole_i in zip(copy["holes"], polygon["holes"]):
                if not decimals_match(hole_m, hole_i):
                    errors.append("decimal hole drift")
    foam_ids = [item["loop_id"] for item in canon["foam_loops"]]
    depth_ids = [item["loop_id"] for item in canon["depth_loops"]]
    if foam_ids != sorted(foam_ids) or depth_ids != sorted(depth_ids):
        errors.append("loop order")
    for loop in canon["foam_loops"] + canon["depth_loops"]:
        errors.extend(check_ring(loop["outer"], loop["loop_id"], True))
    if metrics_path:
        metrics = load_json(metrics_path)
        if metrics.get("geometry_sha") != digest:
            errors.append("metrics sha")
        for archetype_id, spec in SPECS.items():
            counts = [metrics["meshes"][archetype_id]["lods"][str(lod)]["triangles"] for lod in (0, 1, 2)]
            if not (counts[0] > counts[1] > counts[2]):
                errors.append(archetype_id + " lod counts not strictly decreasing " + str(counts))
            for lod, count in enumerate(counts):
                if count > spec["caps"][lod] or count < 1:
                    errors.append("%s LOD%d triangles %d" % (archetype_id, lod, count))
            for lod in (0, 1, 2):
                slots = metrics["meshes"][archetype_id]["lods"][str(lod)]["material_triangles"]
                if sorted(slots) != ["grass", "rock", "sand"]:
                    errors.append(archetype_id + " material slots")
                if min(slots.values()) < 1:
                    errors.append(archetype_id + " empty material")
            if metrics["meshes"][archetype_id]["lod0_shore_max_error_m"] > 1e-6:
                errors.append(archetype_id + " lod0 shore drift")
        port_counts = [metrics["meshes"]["PORT"]["lods"][str(lod)]["triangles"] for lod in (0, 1, 2)]
        if not (port_counts[0] > port_counts[1] > port_counts[2]):
            errors.append("port lod counts " + str(port_counts))
        for lod, count in enumerate(port_counts):
            if count > PORT_CAPS[lod]:
                errors.append("port LOD%d triangles %d" % (lod, count))
            slots = metrics["meshes"]["PORT"]["lods"][str(lod)]["material_triangles"]
            if sorted(slots) != ["wall", "wood"] or min(slots.values()) < 1:
                errors.append("port materials")
        if abs(metrics["clearance_m"]["measured_to_solid_m"] - clearance) > 1e-4:
            errors.append("clearance report drift")
        root = os.path.dirname(os.path.dirname(metrics_path))
        # metrics live in evidence/, textures live beside the generator.
        texture_dir = os.path.join(os.path.dirname(root), "textures") if False else os.path.join(
            os.path.dirname(os.path.dirname(metrics_path)), "textures"
        )
        # metrics path is art_source/production/islands/evidence/mesh_metrics.json
        texture_dir = os.path.join(os.path.dirname(os.path.dirname(metrics_path)), "textures")
        expected = {
            "island_atlas_1024.png": (1024, 1024),
            "island_atlas_512.png": (512, 512),
            "port_atlas_1024.png": (1024, 1024),
            "port_atlas_512.png": (512, 512),
        }
        for name, size in expected.items():
            width, height = png_size(os.path.join(texture_dir, name))
            if (width, height) != size:
                errors.append("%s is %dx%d" % (name, width, height))
    return errors, clearance, digest


def main():
    root = os.path.dirname(os.path.abspath(__file__))
    package_path = os.path.join(root, "data", "island_module_package.json")
    metrics_path = os.path.join(root, "evidence", "mesh_metrics.json")
    if len(sys.argv) > 1:
        package_path = sys.argv[1]
    if len(sys.argv) > 2:
        metrics_path = sys.argv[2]
    errors, clearance, digest = verify(package_path, metrics_path if os.path.exists(metrics_path) else None)
    report = {
        "package": package_path,
        "geometry_sha": digest,
        "measured_clearance_m": clearance,
        "contract_min_clearance_m": CONTRACT_CLEARANCE_M,
        "capsule_tip_m": CAPSULE_TIP_M,
        "error_count": len(errors),
        "errors": errors,
        "verdict": "DEVELOPMENT_OK" if not errors else "DEVELOPMENT_FAIL",
        "acceptance": "NOT_RUN",
    }
    out = os.path.join(root, "evidence", "verify.json")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "w", encoding="utf-8") as handle:
        json.dump(report, handle, indent=2, ensure_ascii=False)
        handle.write("\n")
    print(json.dumps(report, ensure_ascii=False))
    if errors:
        sys.exit(1)


if __name__ == "__main__":
    main()
