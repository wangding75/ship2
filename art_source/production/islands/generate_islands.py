# Procedural ISL-S / ISL-M / ISL-L modules and the port attachment.
# Builder coordinates are Unity metres: +X east, +Y up, water Y=0, +Z north.
# Module origin is the island centre. The port prefab uses the same origin.
# FBX follows the T06 mapping: mesh-local (x, -z, y), axis_forward=Y, axis_up=Z.
# Unity mesh children keep Rx(-90) so an identity root restores this space.

import datetime
import json
import math
import os
import sys

import bpy

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT)
import geometry_hash as geo
EXPORT_DIR = os.path.join(ROOT, "export")
TEXTURE_DIR = os.path.join(ROOT, "textures")
EVIDENCE_DIR = os.path.join(ROOT, "evidence")
TURN_DIR = os.path.join(EVIDENCE_DIR, "turntable")
DATA_DIR = os.path.join(ROOT, "data")
SOURCE_BLEND = os.path.join(ROOT, "source", "S1_T07_islands.blend")

SAND, GRASS, ROCK = "sand", "grass", "rock"
WOOD, WALL = "wood", "wall"
SAND_UV = (0.02, 0.02, 0.48, 0.48)
GRASS_UV = (0.52, 0.02, 0.98, 0.48)
ROCK_UV = (0.02, 0.52, 0.48, 0.98)
LEAF_UV = (0.52, 0.52, 0.98, 0.98)
WOOD_UV = (0.02, 0.02, 0.98, 0.48)
WALL_UV = (0.02, 0.52, 0.98, 0.98)
ISLAND_SLOTS = (SAND, GRASS, ROCK)
PORT_SLOTS = (WOOD, WALL)

# Diameter, triangle caps and the 12 m clearance are frozen.
# Heights, shallow widths, pier length and tree counts are production choices.
ISLANDS = [
    {
        "id": "ISL-S",
        "diameter": 48.0,
        "caps": (1500, 600, 200),
        "harmonics": ((0.10, 2, 0.4), (0.06, 3, 1.1), (0.04, 5, 2.0)),
        "shallow": 6.0,
        "peak": 8.0,
        "beach": 0.8,
        "sand_t": 0.70,
        "count": 60,
        "grass_theta": (2.1, 3.5),
        "reefs": ((0.4, 2.2), (2.6, 1.8)),
        "rocks": ((0.18, 0.5, 2.6), (0.30, 1.7, 2.2), (0.24, 3.4, 2.4), (0.48, 5.1, 1.6)),
        "trees": (),
        "lod": (
            {"step": 1, "rings": 6, "rock_sub": 1, "rock_keep": 4},
            {"step": 2, "rings": 4, "rock_sub": 0, "rock_keep": 3},
            {"step": 3, "rings": 2, "rock_sub": 0, "rock_keep": 2},
        ),
    },
    {
        "id": "ISL-M",
        "diameter": 110.0,
        "caps": (3500, 1400, 400),
        "harmonics": ((0.07, 2, 0.3), (0.05, 3, 1.7), (0.03, 4, 0.6)),
        "shallow": 8.0,
        "peak": 14.0,
        "beach": 1.0,
        "sand_t": 0.78,
        "count": 80,
        "grass_theta": None,
        "reefs": ((1.2, 3.5),),
        "rocks": ((0.86, 0.8, 2.2), (0.84, 3.6, 1.8)),
        "trees": ((0.34, 0.6, 5.2), (0.40, 2.4, 4.6), (0.30, 4.2, 3.8)),
        "lod": (
            {"step": 1, "rings": 7, "rock_sub": 1, "rock_keep": 2, "trunk": 8, "leaf": 1},
            {"step": 2, "rings": 5, "rock_sub": 0, "rock_keep": 2, "trunk": 6, "leaf": 0},
            {"step": 4, "rings": 2, "rock_sub": 0, "rock_keep": 1, "trunk": 4, "leaf": 0},
        ),
    },
    {
        "id": "ISL-L",
        "diameter": 200.0,
        "caps": (7000, 2500, 700),
        "harmonics": ((0.08, 2, 0.8), (0.05, 3, 0.2), (0.035, 5, 1.4)),
        "shallow": 10.0,
        "peak": 22.0,
        "beach": 1.2,
        "sand_t": 0.80,
        "count": 96,
        "grass_theta": None,
        "reefs": ((2.2, 4.5), (4.0, 3.5)),
        "rocks": ((0.84, 2.2, 3.0), (0.86, 4.4, 2.4), (0.72, 3.5, 2.0)),
        "trees": (
            (0.28, 2.0, 7.0),
            (0.36, 2.8, 6.2),
            (0.30, 3.6, 5.4),
            (0.42, 4.5, 4.8),
            (0.24, 5.2, 5.6),
            (0.38, 1.2, 4.4),
        ),
        "lod": (
            {"step": 1, "rings": 8, "rock_sub": 1, "rock_keep": 3, "trunk": 8, "leaf": 1},
            {"step": 2, "rings": 5, "rock_sub": 0, "rock_keep": 2, "trunk": 6, "leaf": 0},
            {"step": 4, "rings": 2, "rock_sub": 0, "rock_keep": 2, "trunk": 4, "leaf": 0},
        ),
    },
]

PORT_LOD = (
    {"sides": 12, "piles": 6, "pile_sides": 8, "rails": True},
    {"sides": 8, "piles": 5, "pile_sides": 6, "rails": False},
    {"sides": 6, "piles": 4, "pile_sides": 4, "rails": False},
)
SKIRT_Y = -1.5
PIER_HALF_W = 2.4
CONTRACT_CLEARANCE = 12.0
CAPSULE_TIP = 16.0


PART_NAMES = ("Beach", "Grass", "Trees", "Reef")
PART_ZH = {"Beach": "沙滩", "Grass": "草坡", "Trees": "树团", "Reef": "礁石"}
PART_SLOT = {"Beach": SAND, "Grass": GRASS, "Trees": ROCK, "Reef": ROCK}
SEMANTIC_PART = {"beach": "Beach", "grass": "Grass", "trees": "Trees", "reef": "Reef"}


class Builder:
    def __init__(self):
        self.verts = []
        self.faces = []
        self.uvs = []
        # None uses the material default. Trees set this so they do not share the reef part.
        self.semantic_override = None

    def v(self, point):
        self.verts.append((float(point[0]), float(point[1]), float(point[2])))
        return len(self.verts) - 1

    def semantic_for(self, mat):
        if self.semantic_override:
            return self.semantic_override
        return {SAND: "beach", GRASS: "grass", ROCK: "reef", WOOD: "wood", WALL: "wall"}[mat]

    def tri(self, a, b, c, mat, uvs):
        if len({a, b, c}) < 3:
            return
        ax, ay, az = self.verts[a]
        bx, by, bz = self.verts[b]
        cx, cy, cz = self.verts[c]
        nx = (by - ay) * (cz - az) - (bz - az) * (cy - ay)
        ny = (bz - az) * (cx - ax) - (bx - ax) * (cz - az)
        nz = (bx - ax) * (cy - ay) - (by - ay) * (cx - ax)
        if nx * nx + ny * ny + nz * nz < 1e-16:
            return
        self.faces.append((a, b, c, mat, self.semantic_for(mat)))
        self.uvs.append(uvs)

    def tri_dot(self, a, b, c, mat, uvs, direction):
        ax, ay, az = self.verts[a]
        bx, by, bz = self.verts[b]
        cx, cy, cz = self.verts[c]
        nx = (by - ay) * (cz - az) - (bz - az) * (cy - ay)
        ny = (bz - az) * (cx - ax) - (bx - ax) * (cz - az)
        nz = (bx - ax) * (cy - ay) - (by - ay) * (cx - ax)
        if nx * direction[0] + ny * direction[1] + nz * direction[2] < 0.0:
            self.tri(a, c, b, mat, (uvs[0], uvs[2], uvs[1]))
        else:
            self.tri(a, b, c, mat, uvs)

    def counts(self):
        totals = {}
        for face in self.faces:
            totals[face[3]] = totals.get(face[3], 0) + 1
        return totals


def uv(rect, u, v):
    u0, v0, u1, v1 = rect
    u = 0.0 if u < 0.0 else 1.0 if u > 1.0 else u
    v = 0.0 if v < 0.0 else 1.0 if v > 1.0 else v
    return (u0 + u * (u1 - u0), v0 + v * (v1 - v0))


def planar(rect, x, z, diameter):
    return uv(rect, x / diameter + 0.5, z / diameter + 0.5)


def radius_at(theta, spec):
    wobble = 0.0
    for amp, freq, phase in spec["harmonics"]:
        wobble += amp * math.sin(freq * theta + phase)
    return spec["diameter"] * 0.5 * (1.0 + wobble)


def height_at(t, spec):
    if t >= 1.0:
        return 0.0
    sand_t = spec["sand_t"]
    if t >= sand_t:
        u = (1.0 - t) / (1.0 - sand_t)
        return spec["beach"] * u * u
    u = t / sand_t
    hump = math.cos(u * math.pi * 0.5)
    return spec["beach"] + (spec["peak"] - spec["beach"]) * hump


def build_radial_ring(spec, offset):
    count = spec["count"]
    raw = []
    max_r = 0.0
    for index in range(count):
        theta = (index / count) * math.tau
        value = radius_at(theta, spec) + offset
        raw.append((theta, value))
        if offset == 0.0 and value > max_r:
            max_r = value
    scale = 1.0 if offset else (spec["diameter"] * 0.5) / max_r
    points = []
    for theta, value in raw:
        radius = value * scale if offset == 0.0 else value
        # Shallow uses the already scaled land radius plus width, so pass offset
        # only after land scale is known. This branch is land-only.
        points.append((radius * math.cos(theta), radius * math.sin(theta)))
    return points


def scaled_land(spec):
    count = spec["count"]
    samples = []
    max_r = 0.0
    for index in range(count):
        theta = (index / count) * math.tau
        value = radius_at(theta, spec)
        samples.append((theta, value))
        if value > max_r:
            max_r = value
    scale = (spec["diameter"] * 0.5) / max_r
    points = []
    for theta, value in samples:
        radius = value * scale
        points.append((radius * math.cos(theta), radius * math.sin(theta), theta, radius))
    return points


def quantize_ring(points_xz):
    ring = geo.ensure_ccw(geo.ring_ints(points_xz))
    # A quantum nudge keeps the farthest land sample on the frozen diameter.
    return ring


def nudge_diameter(ring, diameter):
    target = diameter * 0.5
    best_index = 0
    best = -1.0
    for index, (x, z) in enumerate(ring):
        radius = math.hypot(x / geo.QUANTUM, z / geo.QUANTUM)
        if radius > best:
            best = radius
            best_index = index
    if target - best > 0.5 / geo.QUANTUM:
        x, z = ring[best_index]
        radius = math.hypot(x, z)
        ring[best_index] = [int(round(x * target / (radius / geo.QUANTUM))), int(round(z * target / (radius / geo.QUANTUM)))]
    return ring


def material_for(spec, t, theta):
    if t >= spec["sand_t"] - 1e-9:
        return SAND
    wedge = spec["grass_theta"]
    if wedge is not None and wedge[0] <= theta <= wedge[1] and 0.12 <= t < spec["sand_t"]:
        return GRASS
    if spec["id"] == "ISL-S":
        return ROCK
    return GRASS


def rect_for(mat, leaf=False):
    if leaf:
        return LEAF_UV
    return {SAND: SAND_UV, GRASS: GRASS_UV, ROCK: ROCK_UV, WOOD: WOOD_UV, WALL: WALL_UV}[mat]


def icosphere_triangles(subdiv):
    return 20 * (4 ** subdiv)


def estimate_prop_triangles(spec, lod):
    total = 0
    for _rock in spec["rocks"][: lod["rock_keep"]]:
        total += icosphere_triangles(lod["rock_sub"])
    sides = lod.get("trunk", 4)
    leaf = lod.get("leaf", 0)
    for t, theta, _height in spec["trees"]:
        if spec["id"] == "ISL-L" and t > 0.62 and abs((theta + math.pi) % math.tau - math.pi) < 0.45:
            continue
        total += 4 * sides + icosphere_triangles(leaf)
    return total


def terrain_triangles(shore_n, inner_n, rings, cone):
    # Coarse interior bands, one full-resolution sand annulus, then the cap.
    # A wall skirt is 3N (sides + bottom). A cone cap is N and stays underwater.
    bands = max(rings - 2, 0)
    skirt = shore_n if cone else shore_n * 3
    return inner_n + (2 * inner_n * bands) + (shore_n + inner_n) + skirt


def skirt_is_cone(spec, lod, shore_n, inner_n, lod_index):
    props = estimate_prop_triangles(spec, lod)
    cap = spec["caps"][lod_index]
    wall = terrain_triangles(shore_n, inner_n, lod["rings"], False) + props
    cone = terrain_triangles(shore_n, inner_n, lod["rings"], True) + props
    if wall <= cap:
        return False, wall, cone, props
    if cone <= cap:
        return True, wall, cone, props
    raise RuntimeError(
        "%s LOD%d cannot keep the full waterline inside cap %d (wall %d, cone %d)"
        % (spec["id"], lod_index, cap, wall, cone)
    )


def radial_ts(spec, rings):
    # The last sample is the waterline. The sample before it is sand_t,
    # so the outer top annulus is the beach and does not straddle the grass.
    if rings < 2:
        raise RuntimeError("%s needs a sand ring and a waterline" % spec["id"])
    inner_rings = rings - 1
    samples = [spec["sand_t"] * index / inner_rings for index in range(1, inner_rings + 1)]
    samples.append(1.0)
    return samples


def add_annulus(builder, spec, shore, kept, inner_ids, outer_ids, t0, t1):
    inner_n = len(inner_ids)
    outer_n = len(outer_ids)
    if outer_n % inner_n != 0:
        raise RuntimeError("%s annulus %d/%d" % (spec["id"], outer_n, inner_n))
    span = outer_n // inner_n
    full_outer = outer_n == len(shore)
    for slot in range(inner_n):
        shore_index = kept[slot]
        nxt_slot = (slot + 1) % inner_n
        theta = shore[shore_index][2]
        mat = material_for(spec, 0.5 * (t0 + t1), theta)
        rect = rect_for(mat)
        origin = shore_index if full_outer else slot

        def shore_at(outer_slot):
            if full_outer:
                return outer_slot % len(shore)
            return kept[outer_slot % inner_n]

        for step_index in range(span):
            o0 = (origin + step_index) % outer_n
            o1 = (origin + step_index + 1) % outer_n
            s0 = shore_at(o0)
            s1 = shore_at(o1)
            builder.tri_dot(
                inner_ids[slot],
                outer_ids[o0],
                outer_ids[o1],
                mat,
                (
                    planar(rect, shore[shore_index][0] * t0, shore[shore_index][1] * t0, spec["diameter"]),
                    planar(rect, shore[s0][0] * t1, shore[s0][1] * t1, spec["diameter"]),
                    planar(rect, shore[s1][0] * t1, shore[s1][1] * t1, spec["diameter"]),
                ),
                (0, 1, 0),
            )
        o_end = (origin + span) % outer_n
        s_end = shore_at(o_end)
        nxt_shore = kept[nxt_slot]
        builder.tri_dot(
            inner_ids[slot],
            outer_ids[o_end],
            inner_ids[nxt_slot],
            mat,
            (
                planar(rect, shore[shore_index][0] * t0, shore[shore_index][1] * t0, spec["diameter"]),
                planar(rect, shore[s_end][0] * t1, shore[s_end][1] * t1, spec["diameter"]),
                planar(rect, shore[nxt_shore][0] * t0, shore[nxt_shore][1] * t0, spec["diameter"]),
            ),
            (0, 1, 0),
        )


def add_terrain(builder, spec, lod, land_ring, lod_index):
    # Waterline vertices are the shared canonical ring. Interior rings use
    # lod["step"] so the triangle budget comes out of the mound, not the shore.
    step = lod["step"]
    rings = lod["rings"]
    shore = []
    for x_i, z_i in land_ring:
        x = x_i / geo.QUANTUM
        z = z_i / geo.QUANTUM
        shore.append((x, z, math.atan2(z, x) % math.tau))
    count = len(shore)
    if step < 1 or count % step != 0:
        raise RuntimeError("%s land %d step %d" % (spec["id"], count, step))
    kept = list(range(0, count, step))
    inner_count = len(kept)
    cone, wall_total, cone_total, props = skirt_is_cone(spec, lod, count, inner_count, lod_index)
    ts = radial_ts(spec, rings)
    centre = builder.v((0.0, height_at(0.0, spec), 0.0))
    grid = []
    for ring_index, t in enumerate(ts):
        row = []
        if ring_index == len(ts) - 1:
            for x, z, _theta in shore:
                row.append(builder.v((x, 0.0, z)))
        else:
            y = height_at(t, spec)
            for index in kept:
                x, z, _theta = shore[index]
                row.append(builder.v((x * t, y, z * t)))
        grid.append(row)
    t_mid = ts[0] * 0.5
    for slot, index in enumerate(kept):
        nxt = kept[(slot + 1) % inner_count]
        theta = shore[index][2]
        mat = material_for(spec, t_mid, theta)
        rect = rect_for(mat)
        builder.tri_dot(
            centre,
            grid[0][slot],
            grid[0][(slot + 1) % inner_count],
            mat,
            (
                planar(rect, 0, 0, spec["diameter"]),
                planar(rect, shore[index][0] * ts[0], shore[index][1] * ts[0], spec["diameter"]),
                planar(rect, shore[nxt][0] * ts[0], shore[nxt][1] * ts[0], spec["diameter"]),
            ),
            (0, 1, 0),
        )
    for ring_index in range(rings - 1):
        add_annulus(builder, spec, shore, kept, grid[ring_index], grid[ring_index + 1], ts[ring_index], ts[ring_index + 1])
    top = grid[-1]
    if cone:
        bottom = builder.v((0.0, SKIRT_Y, 0.0))
        for index in range(count):
            nxt = (index + 1) % count
            outward = (shore[index][0] + shore[nxt][0], -1.0, shore[index][1] + shore[nxt][1])
            builder.tri_dot(
                top[index],
                top[nxt],
                bottom,
                SAND,
                (uv(SAND_UV, 0.2, 0.8), uv(SAND_UV, 0.8, 0.8), uv(SAND_UV, 0.5, 0.2)),
                outward,
            )
    else:
        skirt = [builder.v((x, SKIRT_Y, z)) for x, z, _theta in shore]
        for index in range(count):
            nxt = (index + 1) % count
            outward = (shore[index][0] + shore[nxt][0], 0.0, shore[index][1] + shore[nxt][1])
            builder.tri_dot(top[index], top[nxt], skirt[nxt], SAND, (uv(SAND_UV, 0.2, 0.8), uv(SAND_UV, 0.8, 0.8), uv(SAND_UV, 0.8, 0.2)), outward)
            builder.tri_dot(top[index], skirt[nxt], skirt[index], SAND, (uv(SAND_UV, 0.2, 0.8), uv(SAND_UV, 0.8, 0.2), uv(SAND_UV, 0.2, 0.2)), outward)
        bottom = builder.v((0.0, SKIRT_Y, 0.0))
        for index in range(count):
            nxt = (index + 1) % count
            builder.tri_dot(bottom, skirt[nxt], skirt[index], SAND, (uv(SAND_UV, 0.5, 0.5), uv(SAND_UV, 0.7, 0.4), uv(SAND_UV, 0.4, 0.4)), (0, -1, 0))
    return {
        "shore": shore,
        "shore_ids": top,
        "skirt": "cone" if cone else "wall",
        "estimate_wall": wall_total,
        "estimate_cone": cone_total,
        "estimate_props": props,
    }


def add_icosphere(builder, centre, radius, subdiv, mat, rect, displace):
    t = (1.0 + math.sqrt(5.0)) / 2.0
    plain = []
    for x, y, z in [
        (-1, t, 0), (1, t, 0), (-1, -t, 0), (1, -t, 0),
        (0, -1, t), (0, 1, t), (0, -1, -t), (0, 1, -t),
        (t, 0, -1), (t, 0, 1), (-t, 0, -1), (-t, 0, 1),
    ]:
        length = math.sqrt(x * x + y * y + z * z)
        plain.append((x / length, y / length, z / length))
    verts = plain
    faces = [
        (0, 11, 5), (0, 5, 1), (0, 1, 7), (0, 7, 10), (0, 10, 11),
        (1, 5, 9), (5, 11, 4), (11, 10, 2), (10, 7, 6), (7, 1, 8),
        (3, 9, 4), (3, 4, 2), (3, 2, 6), (3, 6, 8), (3, 8, 9),
        (4, 9, 5), (2, 4, 11), (6, 2, 10), (8, 6, 7), (9, 8, 1),
    ]
    for _ in range(subdiv):
        cache = {}
        nxt = []

        def mid(i, j):
            key = (i, j) if i < j else (j, i)
            if key in cache:
                return cache[key]
            ax, ay, az = verts[i]
            bx, by, bz = verts[j]
            mx, my, mz = ax + bx, ay + by, az + bz
            length = math.sqrt(mx * mx + my * my + mz * mz)
            cache[key] = len(verts)
            verts.append((mx / length, my / length, mz / length))
            return cache[key]

        for a, b, c in faces:
            ab, bc, ca = mid(a, b), mid(b, c), mid(c, a)
            nxt.extend(((a, ab, ca), (b, bc, ab), (c, ca, bc), (ab, bc, ca)))
        faces = nxt
    ids = []
    for x, y, z in verts:
        warp = 1.0 + displace * math.sin(3.0 * x + 1.7 * y) * math.cos(2.0 * z + y)
        px = centre[0] + x * radius * warp
        py = centre[1] + y * radius * warp
        pz = centre[2] + z * radius * warp
        ids.append(builder.v((px, py, pz)))
    for a, b, c in faces:
        pa, pb, pc = (verts[a], verts[b], verts[c])
        builder.tri(ids[a], ids[b], ids[c], mat, (
            uv(rect, pa[0] * 0.5 + 0.5, pa[1] * 0.5 + 0.5),
            uv(rect, pb[0] * 0.5 + 0.5, pb[1] * 0.5 + 0.5),
            uv(rect, pc[0] * 0.5 + 0.5, pc[1] * 0.5 + 0.5),
        ))


def add_props(builder, spec, lod, land_points):
    limit = spec["diameter"] * 0.5 - 0.2
    for index, (t, theta, radius) in enumerate(spec["rocks"][: lod["rock_keep"]]):
        x, z = point_on(land_points, theta, t)
        if math.hypot(x, z) + radius > limit:
            scale = (limit - radius) / max(math.hypot(x, z), 1e-6)
            x *= scale
            z *= scale
        y = height_at(t, spec) + radius * 0.35
        add_icosphere(builder, (x, y, z), radius, lod["rock_sub"], ROCK, ROCK_UV, 0.14)
    trunk_sides = lod.get("trunk", 4)
    leaf = lod.get("leaf", 0)
    builder.semantic_override = "trees"
    try:
        for t, theta, height in spec["trees"]:
            if spec["id"] == "ISL-L" and t > 0.62 and abs((theta + math.pi) % math.tau - math.pi) < 0.45:
                continue
            x, z = point_on(land_points, theta, t)
            ground = height_at(t, spec)
            add_cylinder(builder, (x, ground, z), (x, ground + height * 0.42, z), height * 0.06, height * 0.045, trunk_sides, ROCK, ROCK_UV)
            add_icosphere(builder, (x, ground + height * 0.62, z), height * 0.34, leaf, ROCK, LEAF_UV, 0.08)
    finally:
        builder.semantic_override = None


def point_on(land_points, theta, t):
    # land_points: (x, z, theta, radius) before quantization, scaled.
    count = len(land_points)
    theta = theta % math.tau
    slot = theta / math.tau * count
    i0 = int(math.floor(slot)) % count
    i1 = (i0 + 1) % count
    frac = slot - math.floor(slot)
    r0 = land_points[i0][3]
    r1 = land_points[i1][3]
    radius = (r0 + (r1 - r0) * frac) * t
    return radius * math.cos(theta), radius * math.sin(theta)


def add_cylinder(builder, p0, p1, r0, r1, sides, mat, rect):
    dx, dy, dz = p1[0] - p0[0], p1[1] - p0[1], p1[2] - p0[2]
    length = math.sqrt(dx * dx + dy * dy + dz * dz) or 1.0
    ax, ay, az = dx / length, dy / length, dz / length
    helper = (1.0, 0.0, 0.0) if abs(ay) > 0.9 else (0.0, 1.0, 0.0)
    sx = helper[1] * az - helper[2] * ay
    sy = helper[2] * ax - helper[0] * az
    sz = helper[0] * ay - helper[1] * ax
    sl = math.sqrt(sx * sx + sy * sy + sz * sz) or 1.0
    sx, sy, sz = sx / sl, sy / sl, sz / sl
    ux, uy, uz = ay * sz - az * sy, az * sx - ax * sz, ax * sy - ay * sx
    rings = []
    for origin, radius in ((p0, r0), (p1, r1)):
        row = []
        for index in range(sides):
            ang = (index / sides) * math.tau
            row.append(builder.v((
                origin[0] + (sx * math.cos(ang) + ux * math.sin(ang)) * radius,
                origin[1] + (sy * math.cos(ang) + uy * math.sin(ang)) * radius,
                origin[2] + (sz * math.cos(ang) + uz * math.sin(ang)) * radius,
            )))
        rings.append(row)
    c0 = builder.v(p0)
    c1 = builder.v(p1)
    for index in range(sides):
        nxt = (index + 1) % sides
        outward = (
            math.cos((index + 0.5) / sides * math.tau),
            0.0,
            math.sin((index + 0.5) / sides * math.tau),
        )
        # Outward in the side plane, approximated by the world radial of the side midpoint.
        mid = builder.verts[rings[0][index]]
        other = builder.verts[rings[0][nxt]]
        outward = (
            (mid[0] + other[0]) * 0.5 - p0[0],
            (mid[1] + other[1]) * 0.5 - p0[1],
            (mid[2] + other[2]) * 0.5 - p0[2],
        )
        builder.tri_dot(rings[0][index], rings[1][index], rings[1][nxt], mat, (uv(rect, 0.1, 0.1), uv(rect, 0.1, 0.9), uv(rect, 0.4, 0.9)), outward)
        builder.tri_dot(rings[0][index], rings[1][nxt], rings[0][nxt], mat, (uv(rect, 0.1, 0.1), uv(rect, 0.4, 0.9), uv(rect, 0.4, 0.1)), outward)
        builder.tri_dot(c0, rings[0][nxt], rings[0][index], mat, (uv(rect, 0.5, 0.5), uv(rect, 0.7, 0.6), uv(rect, 0.6, 0.4)), (-ax, -ay, -az))
        builder.tri_dot(c1, rings[1][index], rings[1][nxt], mat, (uv(rect, 0.5, 0.5), uv(rect, 0.6, 0.4), uv(rect, 0.7, 0.6)), (ax, ay, az))


def add_box(builder, xmin, xmax, ymin, ymax, zmin, zmax, mat, rect):
    p = [
        builder.v((xmin, ymin, zmin)), builder.v((xmax, ymin, zmin)),
        builder.v((xmax, ymin, zmax)), builder.v((xmin, ymin, zmax)),
        builder.v((xmin, ymax, zmin)), builder.v((xmax, ymax, zmin)),
        builder.v((xmax, ymax, zmax)), builder.v((xmin, ymax, zmax)),
    ]
    faces = (
        (0, 2, 1, (0, -1, 0)), (0, 3, 2, (0, -1, 0)),
        (4, 5, 6, (0, 1, 0)), (4, 6, 7, (0, 1, 0)),
        (0, 1, 5, (0, 0, -1)), (0, 5, 4, (0, 0, -1)),
        (3, 6, 2, (0, 0, 1)), (3, 7, 6, (0, 0, 1)),
        (0, 4, 7, (-1, 0, 0)), (0, 7, 3, (-1, 0, 0)),
        (1, 2, 6, (1, 0, 0)), (1, 6, 5, (1, 0, 0)),
    )
    for a, b, c, direction in faces:
        builder.tri_dot(p[a], p[b], p[c], mat, (uv(rect, 0.05, 0.05), uv(rect, 0.95, 0.05), uv(rect, 0.5, 0.95)), direction)


def add_roof(builder, xmin, xmax, zmin, zmax, y0, y1, mat, rect):
    mid_x = 0.5 * (xmin + xmax)
    a = builder.v((xmin, y0, zmin))
    b = builder.v((xmax, y0, zmin))
    c = builder.v((xmax, y0, zmax))
    d = builder.v((xmin, y0, zmax))
    e = builder.v((mid_x, y1, zmin))
    f = builder.v((mid_x, y1, zmax))
    builder.tri_dot(a, b, e, mat, (uv(rect, 0.1, 0.2), uv(rect, 0.9, 0.2), uv(rect, 0.5, 0.9)), (0, 0.4, -1))
    builder.tri_dot(d, f, c, mat, (uv(rect, 0.1, 0.2), uv(rect, 0.5, 0.9), uv(rect, 0.9, 0.2)), (0, 0.4, 1))
    builder.tri_dot(a, e, f, mat, (uv(rect, 0.1, 0.2), uv(rect, 0.5, 0.9), uv(rect, 0.9, 0.8)), (-1, 0.3, 0))
    builder.tri_dot(a, f, d, mat, (uv(rect, 0.1, 0.2), uv(rect, 0.9, 0.8), uv(rect, 0.1, 0.8)), (-1, 0.3, 0))
    builder.tri_dot(b, c, f, mat, (uv(rect, 0.1, 0.2), uv(rect, 0.1, 0.8), uv(rect, 0.9, 0.8)), (1, 0.3, 0))
    builder.tri_dot(b, f, e, mat, (uv(rect, 0.1, 0.2), uv(rect, 0.9, 0.8), uv(rect, 0.5, 0.9)), (1, 0.3, 0))


def circle_ring(cx, cz, radius, count=12):
    points = []
    for index in range(count):
        theta = (index / count) * math.tau
        points.append((cx + radius * math.cos(theta), cz + radius * math.sin(theta)))
    return geo.ensure_ccw(geo.ring_ints(points))


def polygon(polygon_id, kind, outer, holes=None):
    return {"polygon_id": polygon_id, "kind": kind, "outer": outer, "holes": holes or []}


def build_contours():
    modules = []
    land_cache = {}
    for spec in ISLANDS:
        samples = scaled_land(spec)
        land_cache[spec["id"]] = samples
        land = nudge_diameter(geo.ensure_ccw(geo.ring_ints([(p[0], p[1]) for p in samples])), spec["diameter"])
        shallow_pts = []
        for index in range(spec["count"]):
            x = land[index][0] / geo.QUANTUM
            z = land[index][1] / geo.QUANTUM
            radius = math.hypot(x, z) + spec["shallow"]
            theta = math.atan2(z, x)
            shallow_pts.append((radius * math.cos(theta), radius * math.sin(theta)))
        shallow = geo.ensure_ccw(geo.ring_ints(shallow_pts))
        reefs = []
        for ordinal, (theta, reef_r) in enumerate(spec["reefs"], start=1):
            sx, sz = point_on(samples, theta, 1.0)
            radius = math.hypot(sx, sz)
            centre_r = radius + spec["shallow"] * 0.45
            reefs.append(polygon(
                "%s-REEF-%02d" % (spec["id"], ordinal),
                "reef",
                circle_ring(centre_r * math.cos(theta), centre_r * math.sin(theta), reef_r),
            ))
        polys = [
            polygon(spec["id"] + "-LAND", "land", land),
            polygon(spec["id"] + "-SHALLOW", "shallow", shallow, [list(reversed(land))]),
        ] + reefs
        polys.sort(key=lambda item: item["polygon_id"])
        modules.append({"archetype_id": spec["id"], "polygons": polys, "samples": samples, "land": land})
    return modules


def pier_rectangle(land_samples, shallow_w):
    shore_x, shore_z = point_on(land_samples, 0.0, 1.0)
    shore = math.hypot(shore_x, shore_z)
    inner = shore - 8.0
    outer = shore + shallow_w + 8.0
    rect = [
        (inner, -PIER_HALF_W),
        (outer, -PIER_HALF_W),
        (outer, PIER_HALF_W),
        (inner, PIER_HALF_W),
    ]
    return {
        "inner": inner,
        "outer": outer,
        "shore": shore,
        "ring": geo.ensure_ccw(geo.ring_ints(rect)),
        "rect_m": rect,
    }


def foam_for_large(land, pier):
    thetas = []
    for x, z in land:
        thetas.append(math.atan2(z / geo.QUANTUM, x / geo.QUANTUM) % math.tau)
    for x, z in pier["rect_m"]:
        thetas.append(math.atan2(z, x) % math.tau)
    thetas = sorted(set(int(round(theta * 100000)) for theta in thetas))
    points = []
    xmin = min(p[0] for p in pier["rect_m"])
    xmax = max(p[0] for p in pier["rect_m"])
    zmin = min(p[1] for p in pier["rect_m"])
    zmax = max(p[1] for p in pier["rect_m"])
    land_lookup = [(math.atan2(z / geo.QUANTUM, x / geo.QUANTUM) % math.tau, math.hypot(x / geo.QUANTUM, z / geo.QUANTUM)) for x, z in land]
    land_lookup.sort()
    for key in thetas:
        theta = key / 100000.0
        radius = land_lookup[0][1]
        for slot, (sample_theta, sample_r) in enumerate(land_lookup):
            nxt = land_lookup[(slot + 1) % len(land_lookup)]
            radius = sample_r
            if sample_theta <= theta <= nxt[0] or (nxt[0] < sample_theta and (theta >= sample_theta or theta <= nxt[0])):
                span = (nxt[0] - sample_theta) % math.tau
                along = (theta - sample_theta) % math.tau
                frac = 0.0 if span == 0 else along / span
                radius = sample_r + (nxt[1] - sample_r) * frac
                break
        pier_r = ray_rect(theta, xmin, xmax, zmin, zmax)
        if pier_r is not None and pier_r > radius:
            radius = pier_r
        points.append((radius * math.cos(theta), radius * math.sin(theta)))
    ring = geo.ensure_ccw(geo.ring_ints(points))
    deduped = []
    for point in ring:
        if not deduped or point != deduped[-1]:
            deduped.append(list(point))
    if len(deduped) >= 2 and deduped[0] == deduped[-1]:
        deduped.pop()
    return geo.ensure_ccw(deduped)


def ray_rect(theta, xmin, xmax, zmin, zmax):
    c = math.cos(theta)
    s = math.sin(theta)
    hits = []
    if abs(c) > 1e-9:
        for x in (xmin, xmax):
            t = x / c
            if t > 0 and zmin - 1e-6 <= t * s <= zmax + 1e-6:
                hits.append(t)
    if abs(s) > 1e-9:
        for z in (zmin, zmax):
            t = z / s
            if t > 0 and xmin - 1e-6 <= t * c <= xmax + 1e-6:
                hits.append(t)
    return max(hits) if hits else None


def place_port(module, shallow_w):
    samples = module["samples"]
    pier = pier_rectangle(samples, shallow_w)
    shore = pier["shore"]
    lx = shore - 18.0
    lz = -8.0
    # Pull the lighthouse inland until it is inside the quantized land ring.
    land_poly = next(item for item in module["polygons"] if item["kind"] == "land")
    while not geo.point_in_polygon(lx, lz, land_poly) and lx > 0:
        lx -= 0.5
    shed = (shore - 14.0, 7.5)
    while not geo.point_in_polygon(shed[0], shed[1], land_poly) and shed[0] > 0:
        shed = (shed[0] - 0.5, shed[1])
    solids = list(module["polygons"]) + [polygon("PORT-PIER-LAND", "land", pier["ring"])]
    ax = pier["outer"] + CAPSULE_TIP + 1.0
    az = 0.0
    for _ in range(80):
        clearance = min(geo.distance_to_polygon(ax, az, item) for item in solids)
        if clearance >= CAPSULE_TIP + 0.25:
            break
        ax += 0.5
    return {
        "pier": pier,
        "landmark": (lx, lz),
        "shed": shed,
        "anchor": (ax, az),
        "lighthouse_ground": height_at(lx / shore, next(spec for spec in ISLANDS if spec["id"] == "ISL-L")),
        "shed_ground": height_at(shed[0] / shore, next(spec for spec in ISLANDS if spec["id"] == "ISL-L")),
    }


def build_port_mesh(lod, port):
    builder = Builder()
    sides = lod["sides"]
    pier = port["pier"]
    deck_y0, deck_y1 = 0.45, 0.78
    add_box(builder, pier["inner"], pier["outer"], deck_y0, deck_y1, -PIER_HALF_W, PIER_HALF_W, WOOD, WOOD_UV)
    span = pier["outer"] - pier["inner"]
    for index in range(lod["piles"]):
        x = pier["inner"] + span * (index + 0.5) / lod["piles"]
        for z in (-1.35, 1.35):
            add_cylinder(builder, (x, -1.1, z), (x, deck_y0, z), 0.28, 0.24, lod["pile_sides"], WOOD, WOOD_UV)
    if lod["rails"]:
        for index in range(6):
            x = pier["inner"] + span * (index + 0.5) / 6.0
            for z in (-PIER_HALF_W, PIER_HALF_W):
                add_box(builder, x - 0.08, x + 0.08, deck_y1, deck_y1 + 0.85, z - 0.08, z + 0.08, WOOD, WOOD_UV)
        add_box(builder, pier["inner"], pier["outer"], deck_y1 + 0.7, deck_y1 + 0.86, PIER_HALF_W - 0.08, PIER_HALF_W + 0.08, WOOD, WOOD_UV)
        add_box(builder, pier["inner"], pier["outer"], deck_y1 + 0.7, deck_y1 + 0.86, -PIER_HALF_W - 0.08, -PIER_HALF_W + 0.08, WOOD, WOOD_UV)
    sx, sz = port["shed"]
    ground = port["shed_ground"]
    add_box(builder, sx - 2.1, sx + 2.1, ground, ground + 2.5, sz - 1.7, sz + 1.7, WOOD, WOOD_UV)
    add_roof(builder, sx - 2.45, sx + 2.45, sz - 2.0, sz + 2.0, ground + 2.5, ground + 3.7, WOOD, WOOD_UV)
    lx, lz = port["landmark"]
    gy = port["lighthouse_ground"]
    add_cylinder(builder, (lx, gy, lz), (lx, gy + 8.2, lz), 1.7, 1.15, sides, WALL, WALL_UV)
    add_cylinder(builder, (lx, gy + 8.2, lz), (lx, gy + 8.7, lz), 2.05, 2.05, sides, WALL, WALL_UV)
    add_cylinder(builder, (lx, gy + 8.7, lz), (lx, gy + 10.5, lz), 0.95, 0.95, max(6, sides - 2), WALL, WALL_UV)
    add_cylinder(builder, (lx, gy + 10.5, lz), (lx, gy + 11.8, lz), 1.15, 0.08, max(6, sides - 2), WALL, WALL_UV)
    return builder


def bounds_of(builder):
    xs = [v[0] for v in builder.verts]
    ys = [v[1] for v in builder.verts]
    zs = [v[2] for v in builder.verts]
    return {
        "min": [min(xs), min(ys), min(zs)],
        "max": [max(xs), max(ys), max(zs)],
    }


def _point_segment(px, pz, ax, az, bx, bz):
    return geo._dist_point_seg(px, pz, ax, az, bx, bz)


def waterline_report(builder, land_ring, shore_ids):
    """Error of the authored y=0 loop against every canonical land vertex."""
    wanted = [(point[0] / geo.QUANTUM, point[1] / geo.QUANTUM) for point in land_ring]
    loop = [(builder.verts[index][0], builder.verts[index][2]) for index in shore_ids]
    y_zero = [(vx, vz) for vx, vy, vz in builder.verts if abs(vy) <= 1e-8]
    worst_vertex = 0.0
    for x, z in wanted:
        best = None
        for vx, vz in y_zero:
            dist = math.hypot(vx - x, vz - z)
            if best is None or dist < best:
                best = dist
        worst_vertex = max(worst_vertex, 0.0 if best is None else best)
    worst_edge = 0.0
    count = len(loop)
    for x, z in wanted:
        best = None
        for index in range(count):
            ax, az = loop[index]
            bx, bz = loop[(index + 1) % count]
            dist = _point_segment(x, z, ax, az, bx, bz)
            if best is None or dist < best:
                best = dist
        worst_edge = max(worst_edge, 0.0 if best is None else best)
    upward = {}
    for a, b, c, mat, _semantic in builder.faces:
        ax, ay, az = builder.verts[a]
        bx, by, bz = builder.verts[b]
        cx, cy, cz = builder.verts[c]
        nx = (by - ay) * (cz - az) - (bz - az) * (cy - ay)
        ny = (bz - az) * (cx - ax) - (bx - ax) * (cz - az)
        nz = (bx - ax) * (cy - ay) - (by - ay) * (cx - ax)
        length = math.sqrt(nx * nx + ny * ny + nz * nz)
        if length < 1e-12:
            continue
        if ny / length > 0.5:
            upward[mat] = upward.get(mat, 0) + 1
    return {
        "waterline_vertices": len(shore_ids),
        "y0_vertices": len(y_zero),
        "canonical_vertices": len(wanted),
        "waterline_max_error_m": worst_vertex,
        "mesh_waterline_chord_deviation_m": worst_edge,
        "upward_triangles": upward,
        "upward_sand_triangles": upward.get(SAND, 0),
    }


def paint(size, kind):
    buf = [0.0] * (size * size * 4)

    def put(x, y, rgb):
        i = (y * size + x) * 4
        buf[i] = rgb[0]
        buf[i + 1] = rgb[1]
        buf[i + 2] = rgb[2]
        buf[i + 3] = 1.0

    for y in range(size):
        v = y / (size - 1)
        for x in range(size):
            u = x / (size - 1)
            if kind == "island":
                if u < 0.5 and v < 0.5:
                    grain = 0.04 * math.sin(u * 90.0) + 0.03 * math.sin(v * 70.0)
                    col = (0.86 + grain, 0.74 + grain * 0.6, 0.52)
                elif u >= 0.5 and v < 0.5:
                    blade = 0.05 * math.sin((u + v) * 80.0)
                    col = (0.45 + blade, 0.68 + blade, 0.28)
                elif u < 0.5:
                    crack = 0.08 if int(u * 40) % 7 == 0 or int(v * 30) % 9 == 0 else 0.0
                    col = (0.55 - crack, 0.52 - crack, 0.48 - crack)
                else:
                    col = (0.42 + 0.06 * math.sin(u * 50), 0.62, 0.24 + 0.05 * math.sin(v * 40))
            else:
                if v < 0.5:
                    seam = 0.12 if (v * 18) % 1.0 < 0.08 else 0.0
                    col = (0.55 - seam, 0.36 - seam, 0.20 - seam * 0.5)
                else:
                    band = 0.0
                    if 0.62 < v < 0.70:
                        band = 0.35 if int(u * 18) % 2 == 0 else -0.05
                    if 0.78 < v < 0.86 and 0.42 < u < 0.58:
                        col = (0.95, 0.78, 0.35)
                    else:
                        col = (0.93 - band * 0.2, 0.92 - band, 0.88 - band)
            put(x, y, tuple(max(0.0, min(1.0, c)) for c in col))
    image = bpy.data.images.new(kind + "_atlas_%d" % size, size, size, alpha=False)
    image.pixels.foreach_set(buf)
    path = os.path.join(TEXTURE_DIR, "%s_atlas_%d.png" % (("island" if kind == "island" else "port"), size))
    image.filepath_raw = path
    image.file_format = "PNG"
    image.save()
    return image


def make_material(name, image):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    mat.use_backface_culling = False
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    bsdf = nodes.get("Principled BSDF")
    tex = nodes.new("ShaderNodeTexImage")
    tex.image = image
    links.new(tex.outputs["Color"], bsdf.inputs["Base Color"])
    bsdf.inputs["Roughness"].default_value = 0.82
    return mat


def to_blender(name, builder, materials, slot_names):
    mesh = bpy.data.meshes.new(name)
    verts = [(v[0], -v[2], v[1]) for v in builder.verts]
    faces = [(f[0], f[1], f[2]) for f in builder.faces]
    mesh.from_pydata(verts, [], faces)
    mesh.validate(clean_customdata=False)
    mesh.update()
    if len(mesh.polygons) != len(builder.faces):
        raise RuntimeError("%s dropped faces %d -> %d" % (name, len(builder.faces), len(mesh.polygons)))
    uvlayer = mesh.uv_layers.new(name="UVMap")
    for mat in materials:
        mesh.materials.append(mat)
    for poly, src, uvs in zip(mesh.polygons, builder.faces, builder.uvs):
        poly.material_index = slot_names.index(src[3])
        poly.use_smooth = True
        for corner, loop in enumerate(poly.loop_indices):
            uvlayer.data[loop].uv = uvs[corner]
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    return obj


def blender_build_hash():
    value = getattr(bpy.app, "build_hash", "")
    if isinstance(value, bytes):
        value = value.decode("ascii", "replace")
    return str(value)


def make_waterline_ribbon(name, land_ring, material):
    builder = Builder()
    points = [(point[0] / geo.QUANTUM, point[1] / geo.QUANTUM) for point in land_ring]
    count = len(points)
    height = 0.7
    half = 0.6
    inner = []
    outer = []
    for index, (x, z) in enumerate(points):
        previous = points[(index - 1) % count]
        nxt = points[(index + 1) % count]
        tx, tz = nxt[0] - previous[0], nxt[1] - previous[1]
        length = math.hypot(tx, tz) or 1.0
        nx, nz = tz / length, -tx / length
        if nx * x + nz * z < 0.0:
            nx, nz = -nx, -nz
        inner.append(builder.v((x - nx * half, height, z - nz * half)))
        outer.append(builder.v((x + nx * half, height, z + nz * half)))
    for index in range(count):
        nxt = (index + 1) % count
        builder.tri(inner[index], outer[index], outer[nxt], SAND, (uv(SAND_UV, 0.1, 0.1), uv(SAND_UV, 0.9, 0.1), uv(SAND_UV, 0.9, 0.9)))
        builder.tri(inner[index], outer[nxt], inner[nxt], SAND, (uv(SAND_UV, 0.1, 0.1), uv(SAND_UV, 0.9, 0.9), uv(SAND_UV, 0.1, 0.9)))
    return to_blender(name, builder, [material], (SAND,))


def waterline_material():
    mat = bpy.data.materials.new("Waterline")
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    bsdf.inputs["Base Color"].default_value = (1.0, 0.22, 0.05, 1.0)
    for key, value in (("Emission Color", (1.0, 0.15, 0.04, 1.0)), ("Emission", (1.0, 0.15, 0.04, 1.0))):
        if key in bsdf.inputs:
            bsdf.inputs[key].default_value = value
    if "Emission Strength" in bsdf.inputs:
        bsdf.inputs["Emission Strength"].default_value = 8.0
    return mat


def blender_upward(obj):
    mesh = obj.data
    mesh.calc_loop_triangles()
    counts = {}
    for tri in mesh.loop_triangles:
        if tri.normal.z > 0.5:
            name = mesh.materials[tri.material_index].name
            counts[name] = counts.get(name, 0) + 1
    return counts


def split_parts(builder):
    buckets = {name: Builder() for name in PART_NAMES}
    index_maps = {name: {} for name in PART_NAMES}
    for face, uvs in zip(builder.faces, builder.uvs):
        a, b, c, mat, semantic = face
        if semantic not in SEMANTIC_PART:
            raise RuntimeError("island face has no semantic part: %s" % semantic)
        name = SEMANTIC_PART[semantic]
        part = buckets[name]
        mapping = index_maps[name]

        def take(old, mapping=mapping, part=part):
            if old not in mapping:
                mapping[old] = part.v(builder.verts[old])
            return mapping[old]

        part.faces.append((take(a), take(b), take(c), mat, semantic))
        part.uvs.append(uvs)
    return buckets


def face_signature(builder):
    rows = []
    for a, b, c, mat, semantic in builder.faces:
        corners = tuple(sorted((builder.verts[a], builder.verts[b], builder.verts[c])))
        rows.append((corners, mat, semantic))
    rows.sort()
    return rows


def face_signature_of_parts(parts):
    rows = []
    for name in PART_NAMES:
        rows.extend(face_signature(parts[name]))
    rows.sort()
    return rows


def object_list(value):
    if isinstance(value, (list, tuple)):
        return list(value)
    return [value]


def flatten_objects(mapping):
    result = []
    for value in mapping.values():
        result.extend(object_list(value))
    return result


def reveal(value):
    for obj in object_list(value):
        obj.hide_render = False
        obj.hide_set(False)


def world_sample(obj):
    if obj.type != "MESH" or obj.data is None or len(obj.data.vertices) == 0:
        return None
    bpy.context.view_layer.update()
    point = obj.matrix_world @ obj.data.vertices[0].co
    return (round(point.x, 5), round(point.y, 5), round(point.z, 5))


def prove_parts_independent(part_objects):
    beach = part_objects["Beach"]
    grass = part_objects["Grass"]
    trees = part_objects["Trees"]
    reef = part_objects["Reef"]
    before = {name: world_sample(obj) for name, obj in part_objects.items()}
    origin = {name: tuple(obj.location) for name, obj in part_objects.items()}
    trees.location.x += 4.0
    reef.location.x -= 3.0
    bpy.context.view_layer.update()
    beach_during = world_sample(beach)
    grass_during = world_sample(grass)
    trees_during = world_sample(trees)
    reef_during = world_sample(reef)
    grass.hide_set(True)
    reef.hide_set(True)
    hidden = {"grass": grass.hide_get(), "reef": reef.hide_get(), "beach": beach.hide_get(), "trees": trees.hide_get()}
    grass.hide_set(False)
    reef.hide_set(False)
    for name, obj in part_objects.items():
        obj.location = origin[name]
    bpy.context.view_layer.update()
    restored = {name: world_sample(obj) for name, obj in part_objects.items()}
    report = {
        "beach_unchanged_while_others_moved": beach_during == before["Beach"],
        "grass_unchanged_while_reef_and_trees_moved": grass_during == before["Grass"],
        "reef_sample_moved": reef_during != before["Reef"],
        "trees_sample_moved": None if before["Trees"] is None else trees_during != before["Trees"],
        "beach_stayed_visible": hidden["beach"] is False,
        "trees_stayed_visible": hidden["trees"] is False,
        "grass_hidden": hidden["grass"] is True,
        "reef_hidden": hidden["reef"] is True,
        "restored": restored == before,
    }
    ok = (
        report["beach_unchanged_while_others_moved"]
        and report["grass_unchanged_while_reef_and_trees_moved"]
        and report["reef_sample_moved"]
        and report["beach_stayed_visible"]
        and report["grass_hidden"]
        and report["reef_hidden"]
        and report["restored"]
    )
    if before["Trees"] is not None:
        ok = ok and report["trees_sample_moved"] is True
    report["ok"] = ok
    return report


def export_fbx(obj, path):
    bpy.ops.object.select_all(action="DESELECT")
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    bpy.ops.export_scene.fbx(
        filepath=path,
        use_selection=True,
        object_types={"MESH"},
        apply_scale_options="FBX_SCALE_UNITS",
        axis_forward="Y",
        axis_up="Z",
        bake_space_transform=True,
        apply_unit_scale=True,
        global_scale=1.0,
        mesh_smooth_type="FACE",
        use_mesh_modifiers=True,
        add_leaf_bones=False,
        colors_type="NONE",
        path_mode="STRIP",
        embed_textures=False,
    )


def look_at(cam, location, target):
    cam.location = location
    direction = target - cam.location
    cam.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()


def blender_vec(x, y, z):
    from mathutils import Vector
    return Vector((x, -z, y))


def render_path(scene, path):
    scene.render.filepath = path
    bpy.ops.render.render(write_still=True)


def hide_all(objects, hidden):
    for obj in objects:
        obj.hide_render = hidden
        obj.hide_set(hidden)


def write_note(package, metrics):
    lines = [
        "# S1 T07 岛屿与港口模块",
        "",
        "这是制作候选，不是验收结论。视觉由 A07 看，模块数据和技术约束由 A04 看。",
        "",
        "- 作者 UUID `%s`" % metrics["author"]["uuid"],
        "- 作者 Run `%s`" % metrics["author"]["run"],
        "- Grok 会话 `%s`" % metrics["author"]["session"],
        "- 实际模型 grok-4.7 / high。平台身份说明里的 gpt-6.1-sol 名称没有沿用。",
        "- Blender %s，构建哈希 %s。" % (metrics["blender"], metrics["blender_hash"]),
        "- 基线 `ca391a4f341f25d7a99aa27a35de678fd684eaf4` 在 `refs/heads/t06/ship-assets-rework-1`，`refs/heads/main` 是 `bddd5441777b521045edd0549958704b23d82036`。该基线不是 main 已合并。",
        "- 已验收舰船目录没有修改。",
        "- 模块包 `data/island_module_package.json` 的 geometry_sha `%s`。" % package["geometry_sha"],
        "",
        "## 冻结数字",
        "",
        "ISL-S / ISL-M / ISL-L 的陆地包围直径是 48 / 110 / 200 米，取模块原点到陆地外环的最大半径的两倍。三角上限是 1500/600/200、3500/1400/400、7000/2500/700。港口附加件上限 2500/900/300。材质槽是岛 3、港口 2。LOD0 与 LOD1 共用一张 1024 图，LOD2 用一张 512 图。没有给 LOD1 另造贴图上限。",
        "",
        "锚点净空下限是 1.5 × R_nav,max = 12 米。重型船船长 32 米、R_nav 8 米，轴向胶囊中心线半长 8 米，艏艉尖端距枢轴 16 米。本模块把锚点放到实测净空大于 16 米的可航水里，使允许的全部朝向都放得下这只胶囊。16 米是这只已验收船的几何结果，不是新的冻结阈值，也不把 12 米下限降掉。",
        "",
        "LOD 切换建议仍是相机高度 50 米和 140 米，不是硬阈值。假定垂直 FOV 60° 时，大岛在这两个高度会铺满或超出画面，旧换算把 screenRelativeHeight 夹到 0.99，质量 lodBias 放大后又让 35/85/220 米自然机位停在 LOD0。预制件只在建议值能分出两档时沿用建议；建议值饱和时用一组更低的过渡，让连续拉远能经过三档，LOD2 保留到 0.01，避免突然消失。这些数不是新的冻结门槛。",
        "",
        "## T07-REWORK-1 水线与沙环",
        "",
        "每个 LOD 的 y=0 水线使用同一条 canonical 陆地环的全部顶点。减面发生在沙环以内的山体，以及放不下竖向裙边时的水下封底。沙环内缘放在各自 sand_t（S 0.70、M 0.78、L 0.80），外缘就是水线，顶面按这个环分到沙，不再把两环中点 0.75 整圈分给草。",
        "",
        "## T07-REWORK-2 语义分件",
        "",
        "源 blend 里每个岛的每个 LOD 是四件可独立移动和隐藏的对象，不是一张岛网格。名字是 `{岛}_LOD{n}_Beach`（沙滩）、`_Grass`（草坡）、`_Trees`（树团）、`_Reef`（礁石）。沙滩用 Sand 槽，草坡用 Grass 槽，树团和礁石共用 Rock 槽。活动渲染仍把这四件确定性装成每个 LOD 一个网格、三个材质槽，三角数是四件之和，不是额外的面。ISL-S 的生产选择没有树，`_Trees` 是空对象，不新增树，也不改外形。LOD1/LOD2 不是 LOD0 的抽稀结果，而是同一条 canonical 岸线和同一套语义规则按该档 step/rings/rock_keep/trunk/leaf 重算。",
        "",
        "操作入口：`assemble_island_parts.py` 在源 blend 上移动树团、隐藏礁石和草坡，再还原并核对三角签名。Unity 预制件的 `SemanticParts` 默认关闭，不进 LODGroup；菜单 `Game/T07/Reassemble Island Parts` 和导入里的 `T07Import.Run` 会做同样的拆装核对。对应表在 `data/semantic_part_map.json`。",
        "",
        "## 图4 和 T05",
        "",
        "图4 右图是圆岛、沙、草、树、岸沫和水深，没有港口建筑。灯塔、木棚和短栈桥来自 T05 的港口方案。本模块不做 T08 水面 shader，也不做 T09 的 12 岛装配。",
        "",
        "## 模块数据",
        "",
        "导出的是 IslandModulePackage，不是 WorldNavigationData。polygon.kind 只有 land、shallow、reef。浅滩的孔是陆地环的反向。栈桥多边形 kind 为 land，覆盖桩柱之间的空档，船不能从桩间穿过。地标 ID 是 LM-PORT-01，锚点 ID 是 ANCHOR-PORT-01。",
        "",
        "浅滩宽度、山高、海滩高度、裙边深度、栈桥长度和树的个数是生产选择，写在包内 production_choices_not_thresholds。岸线、浅滩、泡沫环、深度外环和禁航多边形都在同一份 canonical_integers 里，geometry_sha 只覆盖这份整数文档。",
        "",
        "## 实测",
        "",
        "锚点实测到陆地、浅滩、礁和栈桥的最小距离是 %.4f 米。" % metrics["clearance_m"]["measured_to_solid_m"],
        "",
    ]
    for key, mesh in metrics["meshes"].items():
        counts = [mesh["lods"][str(lod)]["triangles"] for lod in (0, 1, 2)]
        lines.append("- %s 三角 %d / %d / %d" % (key, counts[0], counts[1], counts[2]))
        for lod in (0, 1, 2):
            item = mesh["lods"][str(lod)]
            if "waterline_max_error_m" not in item:
                continue
            lines.append(
                "  - LOD%d 水线顶点误差 %.6f m，弦偏离 %.6f m，向上沙三角 %d，裙边 %s"
                % (
                    lod,
                    item["waterline_max_error_m"],
                    item["mesh_waterline_chord_deviation_m"],
                    item["upward_sand_triangles"],
                    item["skirt"],
                )
            )
    path = os.path.join(ROOT, "S1_T07_production_note.md")
    with open(path, "w", encoding="utf-8") as handle:
        handle.write("\n".join(lines) + "\n")


def mirror_modules(canon):
    modules = []
    for module in canon["archetypes"]:
        modules.append({
            "archetype_id": module["archetype_id"],
            "polygons": [
                {
                    "polygon_id": polygon["polygon_id"],
                    "kind": polygon["kind"],
                    "outer": geo.ring_meters(polygon["outer"]),
                    "holes": [geo.ring_meters(hole) for hole in polygon["holes"]],
                }
                for polygon in module["polygons"]
            ],
        })
    return modules


def main():
    os.makedirs(EXPORT_DIR, exist_ok=True)
    os.makedirs(os.path.join(EXPORT_DIR, "parts"), exist_ok=True)
    os.makedirs(TEXTURE_DIR, exist_ok=True)
    os.makedirs(TURN_DIR, exist_ok=True)
    os.makedirs(DATA_DIR, exist_ok=True)
    os.makedirs(os.path.dirname(SOURCE_BLEND), exist_ok=True)
    modules = build_contours()
    large = next(item for item in modules if item["archetype_id"] == "ISL-L")
    shallow_w = next(spec["shallow"] for spec in ISLANDS if spec["id"] == "ISL-L")
    port = place_port(large, shallow_w)
    archetypes = []
    foam = []
    depth = []
    for module in modules:
        archetypes.append({"archetype_id": module["archetype_id"], "polygons": module["polygons"]})
        land = next(item for item in module["polygons"] if item["kind"] == "land")
        shallow = next(item for item in module["polygons"] if item["kind"] == "shallow")
        if module["archetype_id"] == "ISL-L":
            foam_ring = foam_for_large(land["outer"], port["pier"])
        else:
            foam_ring = land["outer"]
        foam.append({"loop_id": module["archetype_id"] + "-FOAM", "outer": foam_ring})
        depth.append({"loop_id": module["archetype_id"] + "-SHALLOW-OUTER", "outer": shallow["outer"]})
    archetypes.sort(key=lambda item: item["archetype_id"])
    foam.sort(key=lambda item: item["loop_id"])
    depth.sort(key=lambda item: item["loop_id"])
    canon = {
        "archetypes": archetypes,
        "depth_loops": depth,
        "foam_loops": foam,
        "port_attachment": {
            "anchor_id": "ANCHOR-PORT-01",
            "anchor_q": [geo.q_int(port["anchor"][0]), geo.q_int(port["anchor"][1])],
            "host_archetype_id": "ISL-L",
            "landmark_id": "LM-PORT-01",
            "landmark_q": [geo.q_int(port["landmark"][0]), geo.q_int(port["landmark"][1])],
            "polygons": [polygon("PORT-PIER-LAND", "land", port["pier"]["ring"])],
        },
        "unit": "1e-5m",
    }
    digest = geo.geometry_sha(canon)
    expected_geometry = "efa7240dc363e00de8b56b48d35c9861285c6e1f02d9dbe0eb24e1b825c57038"
    if digest != expected_geometry:
        raise RuntimeError("geometry_sha changed %s" % digest)
    solids = list(large["polygons"]) + canon["port_attachment"]["polygons"]
    ax = canon["port_attachment"]["anchor_q"][0] / geo.QUANTUM
    az = canon["port_attachment"]["anchor_q"][1] / geo.QUANTUM
    clearance = min(geo.distance_to_polygon(ax, az, item) for item in solids)
    package = {
        "record_type": "IslandModulePackage",
        "adaptation_id": "S1-T07-MODULE-1",
        "not_a_world_navigation_record": True,
        "interface_target": "S1-INTERFACES/1.0.2",
        "geometry_sha": digest,
        "canonical_integers": canon,
        "modules_xz_m": mirror_modules(canon),
        "port_attachment_xz_m": {
            "host_archetype_id": "ISL-L",
            "landmark_id": "LM-PORT-01",
            "landmark_position_xz_m": {"x_m": ax and port["landmark"][0], "z_m": port["landmark"][1]},
            "anchor_id": "ANCHOR-PORT-01",
            "anchor_position_xz_m": {"x_m": port["anchor"][0], "z_m": port["anchor"][1]},
            "polygons": mirror_modules({"archetypes": [{"archetype_id": "PORT", "polygons": canon["port_attachment"]["polygons"]}]})[0]["polygons"],
        },
        "clearance_m": {
            "contract_min_m": CONTRACT_CLEARANCE,
            "r_nav_max_m": 8.0,
            "ratio": 1.5,
            "ship_h_length_m": 32.0,
            "capsule_centerline_half_m": 8.0,
            "capsule_tip_m": CAPSULE_TIP,
            "measured_to_solid_m": clearance,
        },
        "production_choices_not_thresholds": {
            "shallow_width_m": {spec["id"]: spec["shallow"] for spec in ISLANDS},
            "peak_m": {spec["id"]: spec["peak"] for spec in ISLANDS},
            "beach_m": {spec["id"]: spec["beach"] for spec in ISLANDS},
            "skirt_y_m": SKIRT_Y,
            "pier_half_width_m": PIER_HALF_W,
            "pier_inner_m": port["pier"]["inner"],
            "pier_outer_m": port["pier"]["outer"],
            "note": "These shape choices are not new frozen gates. Frozen gates stay the T05 diameters, triangle caps, material slots, texture sizes and the 12 m clearance.",
        },
    }
    # Landmark decimals come from the quantized canonical point.
    package["port_attachment_xz_m"]["landmark_position_xz_m"] = {
        "x_m": canon["port_attachment"]["landmark_q"][0] / geo.QUANTUM,
        "z_m": canon["port_attachment"]["landmark_q"][1] / geo.QUANTUM,
    }
    package["port_attachment_xz_m"]["anchor_position_xz_m"] = {
        "x_m": ax,
        "z_m": az,
    }
    with open(os.path.join(DATA_DIR, "island_module_package.json"), "w", encoding="utf-8") as handle:
        json.dump(package, handle, indent=2, ensure_ascii=False)
        handle.write("\n")

    bpy.ops.wm.read_factory_settings(use_empty=True)
    image_1024 = paint(1024, "island")
    image_512 = paint(512, "island")
    port_1024 = paint(1024, "port")
    port_512 = paint(512, "port")
    island_mats = {
        1024: [make_material(name, image_1024) for name in ("Sand", "Grass", "Rock")],
        512: [make_material(name + "LOD2", image_512) for name in ("Sand", "Grass", "Rock")],
    }
    port_mats = {
        1024: [make_material(name, port_1024) for name in ("Wood", "Wall")],
        512: [make_material(name + "LOD2", port_512) for name in ("Wood", "Wall")],
    }
    metrics_meshes = {}
    objects = {}
    part_index = {}
    reassembly = []
    parts_dir = os.path.join(EXPORT_DIR, "parts")
    for spec, module in zip(ISLANDS, modules):
        # zip follows ISLANDS order, modules follows build order which is the same.
        entry = {"lods": {}}
        for lod_index, lod in enumerate(spec["lod"]):
            builder = Builder()
            terrain = add_terrain(builder, spec, lod, module["land"], lod_index)
            add_props(builder, spec, lod, module["samples"])
            counts = builder.counts()
            total = sum(counts.values())
            cap = spec["caps"][lod_index]
            report = waterline_report(builder, module["land"], terrain["shore_ids"])
            if total > cap:
                raise RuntimeError("%s LOD%d triangles %d over %d" % (spec["id"], lod_index, total, cap))
            for name in ("sand", "grass", "rock"):
                if counts.get(name, 0) < 1:
                    raise RuntimeError("%s LOD%d missing %s" % (spec["id"], lod_index, name))
            if report["waterline_max_error_m"] > 1e-6 or report["mesh_waterline_chord_deviation_m"] > 1e-6:
                raise RuntimeError("%s LOD%d waterline %s" % (spec["id"], lod_index, json.dumps(report)))
            if report["y0_vertices"] != report["canonical_vertices"] or report["waterline_vertices"] != report["canonical_vertices"]:
                raise RuntimeError("%s LOD%d waterline vertex count %s" % (spec["id"], lod_index, json.dumps(report)))
            if report["upward_sand_triangles"] < 1:
                raise RuntimeError("%s LOD%d upward sand %s" % (spec["id"], lod_index, json.dumps(report["upward_triangles"])))
            size = 512 if lod_index == 2 else 1024
            joined = to_blender("%s_LOD%d" % (spec["id"], lod_index), builder, island_mats[size], ISLAND_SLOTS)
            export_fbx(joined, os.path.join(EXPORT_DIR, "%s_LOD%d.fbx" % (spec["id"], lod_index)))
            blender_up = blender_upward(joined)
            sand_names = [name for name in blender_up if name.lower().startswith("sand")]
            blender_sand = sum(blender_up[name] for name in sand_names)
            if blender_sand < 1:
                raise RuntimeError("%s LOD%d blender upward sand %s" % (spec["id"], lod_index, json.dumps(blender_up)))
            parts = split_parts(builder)
            if face_signature(builder) != face_signature_of_parts(parts):
                raise RuntimeError("%s LOD%d part signature drifted" % (spec["id"], lod_index))
            part_total = sum(len(parts[name].faces) for name in PART_NAMES)
            if part_total != total:
                raise RuntimeError("%s LOD%d part triangles %d != %d" % (spec["id"], lod_index, part_total, total))
            parent = bpy.data.objects.new("%s_LOD%d_Parts" % (spec["id"], lod_index), None)
            bpy.context.collection.objects.link(parent)
            parent.empty_display_type = "PLAIN_AXES"
            parent["t07_role"] = "semantic_parts_root"
            named = {}
            shown = []
            part_report = {}
            for part_name in PART_NAMES:
                part_builder = parts[part_name]
                count = len(part_builder.faces)
                obj_name = "%s_LOD%d_%s" % (spec["id"], lod_index, part_name)
                if count == 0:
                    obj = bpy.data.objects.new(obj_name, None)
                    bpy.context.collection.objects.link(obj)
                    exported = None
                else:
                    slot = PART_SLOT[part_name]
                    obj = to_blender(obj_name, part_builder, [island_mats[size][ISLAND_SLOTS.index(slot)]], (slot,))
                    group = obj.vertex_groups.new(name=part_name)
                    group.add(list(range(len(obj.data.vertices))), 1.0, "REPLACE")
                    export_fbx(obj, os.path.join(parts_dir, obj_name + ".fbx"))
                    shown.append(obj)
                    exported = "export/parts/%s.fbx" % obj_name
                obj.parent = parent
                obj["t07_role"] = "semantic_part"
                obj["t07_semantic"] = part_name
                obj["t07_semantic_zh"] = PART_ZH[part_name]
                obj["t07_material_slot"] = PART_SLOT[part_name]
                obj["t07_triangles"] = count
                obj["t07_asset"] = spec["id"]
                obj["t07_lod"] = lod_index
                named[part_name] = obj
                part_report[part_name] = {
                    "zh": PART_ZH[part_name],
                    "object": obj_name,
                    "triangles": count,
                    "material_slot": PART_SLOT[part_name],
                    "exported_fbx": exported,
                }
            for required in ("Beach", "Grass", "Reef"):
                if part_report[required]["triangles"] < 1:
                    raise RuntimeError("%s LOD%d missing %s" % (spec["id"], lod_index, required))
            if spec["id"] != "ISL-S" and part_report["Trees"]["triangles"] < 1:
                raise RuntimeError("%s LOD%d missing Trees" % (spec["id"], lod_index))
            if spec["id"] == "ISL-S" and part_report["Trees"]["triangles"] != 0:
                raise RuntimeError("ISL-S gained trees; shape must stay")
            proof = prove_parts_independent(named)
            if not proof["ok"]:
                raise RuntimeError("%s LOD%d parts are bound %s" % (spec["id"], lod_index, json.dumps(proof)))
            reassembly.append({
                "asset": spec["id"],
                "lod": lod_index,
                "render_triangles": total,
                "part_triangles": part_total,
                "material_slots_on_render_mesh": ["sand", "grass", "rock"],
                "parts": part_report,
                "independence": proof,
                "lod_parameters": lod,
            })
            part_index[(spec["id"], lod_index)] = named
            objects[(spec["id"], lod_index)] = shown
            joined_mesh = joined.data
            bpy.data.objects.remove(joined, do_unlink=True)
            bpy.data.meshes.remove(joined_mesh)
            entry["lods"][str(lod_index)] = {
                "triangles": total,
                "material_triangles": counts,
                "semantic_parts": {name: part_report[name]["triangles"] for name in PART_NAMES},
                "semantic_part_sum": part_total,
                "render_mesh": "%s_LOD%d" % (spec["id"], lod_index),
                "bounds_unity_m": bounds_of(builder),
                "shore_chord_deviation_m": report["mesh_waterline_chord_deviation_m"],
                "mesh_waterline_chord_deviation_m": report["mesh_waterline_chord_deviation_m"],
                "waterline_max_error_m": report["waterline_max_error_m"],
                "waterline_vertices": report["waterline_vertices"],
                "canonical_vertices": report["canonical_vertices"],
                "interior_step": lod["step"],
                "skirt": terrain["skirt"],
                "sand_ring_t": spec["sand_t"],
                "estimate_wall_triangles": terrain["estimate_wall"],
                "estimate_cone_triangles": terrain["estimate_cone"],
                "upward_triangles": report["upward_triangles"],
                "upward_sand_triangles": report["upward_sand_triangles"],
                "blender_upward_triangles": blender_up,
                "blender_upward_sand_triangles": blender_sand,
            }
        entry["lod0_shore_max_error_m"] = entry["lods"]["0"]["waterline_max_error_m"]
        metrics_meshes[spec["id"]] = entry
    port_entry = {"lods": {}}
    for lod_index, lod in enumerate(PORT_LOD):
        builder = build_port_mesh(lod, port)
        counts = builder.counts()
        total = sum(counts.values())
        if total > (2500, 900, 300)[lod_index]:
            raise RuntimeError("PORT LOD%d triangles %d" % (lod_index, total))
        if counts.get("wood", 0) < 1 or counts.get("wall", 0) < 1:
            raise RuntimeError("PORT LOD%d materials %s" % (lod_index, counts))
        size = 512 if lod_index == 2 else 1024
        obj = to_blender("PORT_LOD%d" % lod_index, builder, port_mats[size], PORT_SLOTS)
        export_fbx(obj, os.path.join(EXPORT_DIR, "PORT_LOD%d.fbx" % lod_index))
        objects[("PORT", lod_index)] = obj
        port_entry["lods"][str(lod_index)] = {
            "triangles": total,
            "material_triangles": counts,
            "bounds_unity_m": bounds_of(builder),
        }
    port_entry["lod0_shore_max_error_m"] = 0.0
    metrics_meshes["PORT"] = port_entry
    for key in list(metrics_meshes):
        counts = [metrics_meshes[key]["lods"][str(i)]["triangles"] for i in (0, 1, 2)]
        if not (counts[0] > counts[1] > counts[2]):
            raise RuntimeError("%s lod not strictly decreasing %s" % (key, counts))

    scene = bpy.context.scene
    engine = "BLENDER_WORKBENCH"
    for candidate in ("BLENDER_EEVEE", "BLENDER_EEVEE_NEXT"):
        try:
            scene.render.engine = candidate
            engine = candidate
            break
        except Exception:
            continue
    if engine == "BLENDER_WORKBENCH":
        scene.render.engine = engine
    if hasattr(scene, "eevee"):
        scene.eevee.taa_render_samples = 8
    scene.render.resolution_x = 960
    scene.render.resolution_y = 540
    scene.render.image_settings.file_format = "PNG"
    world = bpy.data.worlds.new("Backdrop")
    scene.world = world
    world.use_nodes = True
    world.node_tree.nodes["Background"].inputs[0].default_value = (0.23, 0.48, 0.62, 1.0)
    sun_data = bpy.data.lights.new("Sun", "SUN")
    sun_data.energy = 3.0
    sun = bpy.data.objects.new("Sun", sun_data)
    bpy.context.collection.objects.link(sun)
    sun.rotation_euler = (math.radians(55), 0.0, math.radians(40))
    cam_data = bpy.data.cameras.new("Cam")
    cam_data.lens_unit = "FOV"
    cam_data.angle = math.radians(50)
    cam_data.clip_start = 0.2
    cam_data.clip_end = 8000.0
    cam = bpy.data.objects.new("Cam", cam_data)
    bpy.context.collection.objects.link(cam)
    scene.camera = cam
    from mathutils import Vector

    rendered = []
    if os.environ.get("T07_SKIP_RENDER") != "1":
        all_objs = flatten_objects(objects)
        for asset in ("ISL-S", "ISL-M", "ISL-L"):
            parts = part_index[(asset, 0)]
            hide_all(all_objs, True)
            reveal(objects[(asset, 0)])
            parts["Reef"].hide_render = True
            parts["Reef"].hide_set(True)
            parts["Trees"].location.x += 8.0
            bpy.context.view_layer.update()
            distance = next(spec["diameter"] for spec in ISLANDS if spec["id"] == asset) * 1.15
            pitch = math.radians(32.0)
            yaw_r = math.radians(40.0)
            location = blender_vec(
                distance * math.cos(pitch) * math.sin(yaw_r),
                distance * math.sin(pitch),
                distance * math.cos(pitch) * math.cos(yaw_r),
            )
            look_at(cam, location, blender_vec(0.0, 2.0, 0.0))
            path = os.path.join(TURN_DIR, "%s_LOD0_parts_reef_hidden_trees_moved.png" % asset)
            render_path(scene, path)
            rendered.append(path)
            parts["Trees"].location.x -= 8.0
            parts["Reef"].hide_render = False
            parts["Reef"].hide_set(False)
            bpy.context.view_layer.update()
        for key, obj in objects.items():
            asset, lod_index = key
            hide_all(all_objs, True)
            reveal(obj)
            if asset == "PORT":
                bounds = metrics_meshes["PORT"]["lods"][str(lod_index)]["bounds_unity_m"]
                target_u = (
                    0.5 * (bounds["min"][0] + bounds["max"][0]),
                    0.5 * (bounds["min"][1] + bounds["max"][1]),
                    0.5 * (bounds["min"][2] + bounds["max"][2]),
                )
                distance = 55.0
            else:
                target_u = (0.0, 4.0, 0.0)
                distance = next(spec["diameter"] for spec in ISLANDS if spec["id"] == asset) * 1.15
            for yaw in (0, 45, 90, 135, 180, 225, 270, 315):
                pitch = math.radians(28)
                yaw_r = math.radians(yaw)
                location = blender_vec(
                    target_u[0] + distance * math.cos(pitch) * math.sin(yaw_r),
                    target_u[1] + distance * math.sin(pitch),
                    target_u[2] + distance * math.cos(pitch) * math.cos(yaw_r),
                )
                look_at(cam, location, blender_vec(*target_u))
                path = os.path.join(TURN_DIR, "%s_LOD%d_yaw%03d.png" % (asset, lod_index, yaw))
                render_path(scene, path)
                rendered.append(path)
            if asset != "PORT":
                for label, pitch_deg, distance_scale in (("top", 78.0, 0.95), ("oblique", 32.0, 1.05)):
                    pitch = math.radians(pitch_deg)
                    yaw_r = math.radians(40.0)
                    location = blender_vec(
                        distance * math.cos(pitch) * math.sin(yaw_r),
                        distance * distance_scale * math.sin(pitch),
                        distance * math.cos(pitch) * math.cos(yaw_r),
                    )
                    look_at(cam, location, blender_vec(0.0, 2.0, 0.0))
                    path = os.path.join(TURN_DIR, "%s_LOD%d_%s.png" % (asset, lod_index, label))
                    render_path(scene, path)
                    rendered.append(path)
        # Suggested sailing-camera heights, pitched toward the beach, not a new threshold.
        for asset, spec in (("ISL-S", ISLANDS[0]), ("ISL-M", ISLANDS[1]), ("ISL-L", ISLANDS[2]), ("PORT", None)):
            hide_all(all_objs, True)
            if asset == "PORT":
                reveal(objects[("ISL-L", 0)])
                reveal(objects[("PORT", 0)])
                look = (port["landmark"][0], 4.0, port["landmark"][1])
            else:
                reveal(objects[(asset, 0)])
                shore = next(item["shore"] for item in (port["pier"],) if asset == "ISL-L") if asset == "ISL-L" else spec["diameter"] * 0.45
                if asset != "ISL-L":
                    shore = spec["diameter"] * 0.42
                else:
                    shore = port["pier"]["shore"] - 6.0
                look = (shore, 3.0, 0.0)
            for name, height in (("near", 35.0), ("mid", 85.0), ("far", 220.0)):
                horiz = height / math.tan(math.radians(55.0))
                cam_x = look[0] + horiz
                radius_limit = (200.0 if asset in ("ISL-L", "PORT") else spec["diameter"] * 0.5) + 6.0
                if math.hypot(cam_x, look[2]) < radius_limit:
                    cam_x = radius_limit + 2.0
                look_at(cam, blender_vec(cam_x, height, look[2]), blender_vec(*look))
                path = os.path.join(TURN_DIR, "%s_LOD0_%s_h%d.png" % (asset, name, int(height)))
                render_path(scene, path)
                rendered.append(path)
        ribbon_mat = waterline_material()
        ribbons = {}
        for module in modules:
            ribbon = make_waterline_ribbon(module["archetype_id"] + "_WATERLINE", module["land"], ribbon_mat)
            ribbon.hide_render = True
            ribbon.hide_set(True)
            ribbons[module["archetype_id"]] = ribbon
        for module in modules:
            asset = module["archetype_id"]
            ribbon = ribbons[asset]
            for lod_index in (0, 1, 2):
                hide_all(all_objs, True)
                for other in ribbons.values():
                    if other is None:
                        continue
                    other.hide_render = True
                    other.hide_set(True)
                reveal(objects[(asset, lod_index)])
                ribbon.hide_render = False
                ribbon.hide_set(False)
                distance = next(spec["diameter"] for spec in ISLANDS if spec["id"] == asset) * 1.2
                pitch = math.radians(80.0)
                look_at(cam, blender_vec(distance * math.cos(pitch), distance * math.sin(pitch), distance * 0.02), blender_vec(0.0, 0.0, 0.0))
                path = os.path.join(TURN_DIR, "%s_LOD%d_waterline.png" % (asset, lod_index))
                render_path(scene, path)
                rendered.append(path)
            bpy.data.objects.remove(ribbon, do_unlink=True)
            ribbons[asset] = None

    for obj in bpy.data.objects:
        role = obj.get("t07_role")
        if role in ("semantic_part", "semantic_parts_root") or obj.name.startswith("PORT_LOD"):
            obj.hide_render = False
            obj.hide_set(False)
            obj.location = (0.0, 0.0, 0.0)
    bpy.ops.wm.save_as_mainfile(filepath=SOURCE_BLEND)
    metrics = {
        "generator": "art_source/production/islands/generate_islands.py",
        "blender": bpy.app.version_string,
        "blender_hash": blender_build_hash(),
        "utc": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "author": {
            "uuid": "913948fc-cfc0-41f2-a6fd-c7f661450afd",
            "run": os.environ.get("MULTICA_TASK_ID", ""),
            "session": os.environ.get("GROK_SESSION_ID", ""),
            "model": "grok-4.7",
            "effort": "high",
        },
        "geometry_sha": digest,
        "render_engine": engine,
        "rendered": [os.path.relpath(path, ROOT).replace("\\", "/") for path in rendered],
        "clearance_m": package["clearance_m"],
        "port_local_m": {
            "landmark_xz": [package["port_attachment_xz_m"]["landmark_position_xz_m"]["x_m"], package["port_attachment_xz_m"]["landmark_position_xz_m"]["z_m"]],
            "anchor_xz": [ax, az],
            "shed_xz": [port["shed"][0], port["shed"][1]],
            "pier_inner_m": port["pier"]["inner"],
            "pier_outer_m": port["pier"]["outer"],
        },
        "meshes": metrics_meshes,
        "semantic_parts": {
            "names": {name: PART_ZH[name] for name in PART_NAMES},
            "material_slots": {name: PART_SLOT[name] for name in PART_NAMES},
            "active_render": "One mesh per LOD, three material slots. Part triangles sum to that mesh. SemanticParts in the prefab stay inactive and are not LOD renderers.",
            "isl_s_trees": "ISL-S production choice has no trees. The Trees object exists and has zero triangles so the silhouette stays the reef body, sand edge and grass wedge.",
            "lod_relation": "LOD1 and LOD2 rebuild the same canonical shoreline and the same Beach/Grass/Trees/Reef partition. They are not decimated copies of LOD0.",
            "operation": "art_source/production/islands/assemble_island_parts.py",
            "reassembly": reassembly,
        },
        "unity_rx_deg": -90,
        "axis_note": "Mesh-local stores Unity (x, y, z) as (x, -z, y). Prefab mesh children use Rx(-90). Identity roots then match this Unity space.",
        "acceptance": "NOT_RUN",
    }
    with open(os.path.join(EVIDENCE_DIR, "mesh_metrics.json"), "w", encoding="utf-8") as handle:
        json.dump(metrics, handle, indent=2)
        handle.write("\n")
    part_map = {
        "record_type": "T07SemanticPartMap",
        "geometry_sha": digest,
        "parts": [
            {"name": name, "zh": PART_ZH[name], "material_slot": PART_SLOT[name]}
            for name in PART_NAMES
        ],
        "active_material_slots": ["sand", "grass", "rock"],
        "active_renderers_per_lod": 1,
        "note": "Part meshes are a partition of the render mesh. Sharing Rock between Trees and Reef does not add a fourth material slot. ISL-S Trees is an empty object.",
        "lods": reassembly,
    }
    with open(os.path.join(DATA_DIR, "semantic_part_map.json"), "w", encoding="utf-8") as handle:
        json.dump(part_map, handle, indent=2, ensure_ascii=False)
        handle.write("\n")
    with open(os.path.join(EVIDENCE_DIR, "part_reassembly.json"), "w", encoding="utf-8") as handle:
        json.dump(part_map, handle, indent=2, ensure_ascii=False)
        handle.write("\n")
    write_note(package, metrics)
    print("T07 geometry_sha", digest)
    print("clearance", clearance)
    for key, mesh in metrics_meshes.items():
        print(key, [mesh["lods"][str(i)]["triangles"] for i in (0, 1, 2)])


if __name__ == "__main__":
    main()
