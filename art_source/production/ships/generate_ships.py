# Procedural production meshes for S1-T06.
# Coordinates in this file are Unity space: +X starboard, +Y up, +Z bow.
# Pivot is the waterline center. Frozen meters come from S1_T05_visual_sample_spec.md
# section 4.1 and 4.5. Freeboard, lesser mast heights, and the light-ship mast step
# are production choices. The light-ship step follows the sailplan drawing but that
# drawing explicitly does not freeze a meter value.

import array
import json
import math
import os
import sys
import traceback

import bpy
from mathutils import Vector

ROOT = os.path.dirname(os.path.abspath(__file__))
EXPORT_DIR = os.path.join(ROOT, "export")
TEXTURE_DIR = os.path.join(ROOT, "textures")
EVIDENCE_DIR = os.path.join(ROOT, "evidence")
TURN_DIR = os.path.join(EVIDENCE_DIR, "turntable")
SOURCE_BLEND = os.path.join(ROOT, "source", "S1_T06_ships.blend")

WOOD = (0x8A / 255, 0x5A / 255, 0x32 / 255)
SAIL = (0x3A / 255, 0x41 / 255, 0x4C / 255)
TRIM_WOOD = (0x5C / 255, 0x3E / 255, 0x28 / 255)
TRIM_METAL = (0x8A / 255, 0x86 / 255, 0x78 / 255)

# UV rectangles inside the single atlas: (u0, v0, u1, v1)
UV_HULL = (0.02, 0.02, 0.48, 0.70)
UV_DECK = (0.02, 0.74, 0.48, 0.98)
UV_SAIL = (0.52, 0.52, 0.98, 0.98)
UV_TRIM = (0.52, 0.02, 0.98, 0.48)

SHIPS = [
    {
        "id": "SHIP-L",
        "name": "轻型纵帆快船",
        "length": 16.0,
        "beam": 4.0,
        "draft": 1.2,
        "mast_height": 14.0,
        "r_nav": 4.5,
        "wake": [0.0, 0.0, -7.4],
        "kind": "cutter",
        "fb_mid": 1.05,
        "fb_bow": 1.55,
        "fb_stern": 1.25,
        "caps": [1800, 700, 280],
        "masts": [{"name": "main", "z": 1.278, "h": 14.0, "r": 0.11}],
    },
    {
        "id": "SHIP-M",
        "name": "中型双桅帆船",
        "length": 24.0,
        "beam": 5.6,
        "draft": 1.6,
        "mast_height": 18.0,
        "r_nav": 6.5,
        "wake": [0.0, 0.0, -11.2],
        "kind": "brig",
        "fb_mid": 1.35,
        "fb_bow": 1.90,
        "fb_stern": 1.55,
        "caps": [3200, 1200, 420],
        "masts": [
            {"name": "fore", "z": 4.20, "h": 16.2, "r": 0.14},
            {"name": "main", "z": -2.60, "h": 18.0, "r": 0.16},
        ],
    },
    {
        "id": "SHIP-H",
        "name": "重型三桅帆船",
        "length": 32.0,
        "beam": 7.2,
        "draft": 2.0,
        "mast_height": 24.0,
        "r_nav": 8.0,
        "wake": [0.0, 0.0, -15.2],
        "kind": "threemast",
        "fb_mid": 1.70,
        "fb_bow": 2.35,
        "fb_stern": 1.95,
        "caps": [5200, 1800, 600],
        "masts": [
            {"name": "fore", "z": 7.20, "h": 21.0, "r": 0.18},
            {"name": "main", "z": 0.40, "h": 24.0, "r": 0.22},
            {"name": "mizzen", "z": -7.60, "h": 17.5, "r": 0.16},
        ],
    },
]

LOD_PARAMS = {
    0: {"stations": 18, "rings": 8, "sail_u": 4, "sail_v": 5, "sides": 8, "yards": "full", "cabin": True, "rails": True},
    1: {"stations": 11, "rings": 6, "sail_u": 2, "sail_v": 2, "sides": 5, "yards": "mid", "cabin": True, "rails": False},
    2: {"stations": 7, "rings": 4, "sail_u": 1, "sail_v": 1, "sides": 4, "yards": "min", "cabin": False, "rails": False},
}


class Builder:
    def __init__(self):
        self.verts = []
        self.faces = []
        self.uvs = []

    def add_vert(self, p):
        self.verts.append((float(p[0]), float(p[1]), float(p[2])))
        return len(self.verts) - 1

    def _push(self, idxs, uvs):
        area = tri_area(self.verts[idxs[0]], self.verts[idxs[1]], self.verts[idxs[2]])
        if area < 1e-10:
            return
        self.faces.append((int(idxs[0]), int(idxs[1]), int(idxs[2])))
        self.uvs.extend(uvs)

    def add_tri(self, i0, i1, i2, u0, u1, u2):
        self._push((i0, i1, i2), (u0, u1, u2))

    def add_quad(self, i0, i1, i2, i3, u0, u1, u2, u3):
        self._push((i0, i1, i2), (u0, u1, u2))
        self._push((i0, i2, i3), (u0, u2, u3))

    def extend(self, other):
        offset = len(self.verts)
        self.verts.extend(other.verts)
        for f in other.faces:
            self.faces.append((f[0] + offset, f[1] + offset, f[2] + offset))
        self.uvs.extend(other.uvs)

    def tri_count(self):
        return len(self.faces)


def tri_area(a, b, c):
    ax, ay, az = a
    bx, by, bz = b[0] - ax, b[1] - ay, b[2] - az
    cx, cy, cz = c[0] - ax, c[1] - ay, c[2] - az
    nx = by * cz - bz * cy
    ny = bz * cx - bx * cz
    nz = bx * cy - by * cx
    return 0.5 * math.sqrt(nx * nx + ny * ny + nz * nz)


def sub(a, b):
    return (a[0] - b[0], a[1] - b[1], a[2] - b[2])


def add(a, b):
    return (a[0] + b[0], a[1] + b[1], a[2] + b[2])


def mul(a, s):
    return (a[0] * s, a[1] * s, a[2] * s)


def dot(a, b):
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


def cross(a, b):
    return (
        a[1] * b[2] - a[2] * b[1],
        a[2] * b[0] - a[0] * b[2],
        a[0] * b[1] - a[1] * b[0],
    )


def length(a):
    return math.sqrt(dot(a, a))


def norm(a):
    L = length(a)
    if L < 1e-12:
        return (0.0, 1.0, 0.0)
    return (a[0] / L, a[1] / L, a[2] / L)


def lerp(a, b, t):
    return add(mul(a, 1.0 - t), mul(b, t))


def uv_in(rect, u, v):
    return (rect[0] + (rect[2] - rect[0]) * u, rect[1] + (rect[3] - rect[1]) * v)


def fix_winding(builder, interior):
    faces = []
    uvs = []
    for n, f in enumerate(builder.faces):
        a = builder.verts[f[0]]
        b = builder.verts[f[1]]
        c = builder.verts[f[2]]
        ab = sub(b, a)
        ac = sub(c, a)
        normal = cross(ab, ac)
        center = ((a[0] + b[0] + c[0]) / 3.0, (a[1] + b[1] + c[1]) / 3.0, (a[2] + b[2] + c[2]) / 3.0)
        u0, u1, u2 = builder.uvs[n * 3 : n * 3 + 3]
        if dot(normal, sub(center, interior)) < 0.0:
            faces.append((f[0], f[2], f[1]))
            uvs.extend((u0, u2, u1))
        else:
            faces.append(f)
            uvs.extend((u0, u1, u2))
    builder.faces = faces
    builder.uvs = uvs


def face_normal(builder, index):
    f = builder.faces[index]
    a = builder.verts[f[0]]
    b = builder.verts[f[1]]
    c = builder.verts[f[2]]
    return norm(cross(sub(b, a), sub(c, a)))


def beam_half(t, beam):
    # t=0 stern, t=1 bow. Midship reaches exactly beam/2.
    if t < 0.05:
        k = t / 0.05
        return (beam * 0.5) * (0.46 + 0.20 * k)
    full = math.sin(min(t, 0.995) * math.pi) ** 0.62
    if t > 0.80:
        bow = (t - 0.80) / 0.20
        full *= max(0.0, 1.0 - bow) ** 0.50
        full = max(full, 0.018)
    return (beam * 0.5) * full


def draft_at(t, draft):
    return draft * max(0.18, math.sin(max(0.001, min(0.999, t)) * math.pi) ** 0.78)


def freeboard_at(t, ship):
    if t < 0.5:
        k = (0.5 - t) / 0.5
        return ship["fb_mid"] + (ship["fb_stern"] - ship["fb_mid"]) * (k ** 1.35)
    k = (t - 0.5) / 0.5
    return ship["fb_mid"] + (ship["fb_bow"] - ship["fb_mid"]) * (k ** 1.15)


def section_xy(t, ship, rings):
    hb = beam_half(t, ship["beam"])
    dr = draft_at(t, ship["draft"])
    fb = freeboard_at(t, ship)
    pts = []
    for i in range(rings):
        a = i / (rings - 1)
        if a <= 0.64:
            u = a / 0.64
            y = -dr * math.cos(u * math.pi * 0.5)
            x = hb * (math.sin(u * math.pi * 0.5) ** 0.70)
        else:
            u = (a - 0.64) / 0.36
            y = fb * (u ** 0.90)
            x = hb * (1.0 - 0.07 * u)
        pts.append((x, y))
    pts[0] = (0.0, -dr)
    # Keep the deepest keel exactly on the frozen draft.
    if abs(t - 0.5) < 1e-6:
        pts[0] = (0.0, -ship["draft"])
    return pts


def side_uv(rect, t, y, y_keel, y_sheer):
    if y <= 0.0:
        v = 0.08 + 0.47 * ((y - y_keel) / max(1e-6, -y_keel))
    else:
        v = 0.55 + 0.40 * (y / max(1e-6, y_sheer))
    u = 0.04 + 0.92 * t
    return uv_in(rect, u, max(0.0, min(1.0, v)))


def cap_boundary_loops(builder):
    counts = {}
    for f in builder.faces:
        for a, b in ((f[0], f[1]), (f[1], f[2]), (f[2], f[0])):
            key = (a, b) if a < b else (b, a)
            counts[key] = counts.get(key, 0) + 1
    neighbors = {}
    for (a, b), count in counts.items():
        if count != 1:
            continue
        neighbors.setdefault(a, []).append(b)
        neighbors.setdefault(b, []).append(a)
    unused = set()
    for a, b in counts:
        if counts[(a, b)] == 1:
            unused.add((a, b) if a < b else (b, a))
    loops = []
    while unused:
        a, b = unused.pop()
        loop = [a, b]
        prev, cur = a, b
        while cur != loop[0]:
            nxts = [n for n in neighbors[cur] if n != prev and ((min(cur, n), max(cur, n)) in unused)]
            if not nxts:
                break
            nxt = nxts[0]
            unused.discard((min(cur, nxt), max(cur, nxt)))
            loop.append(nxt)
            prev, cur = cur, nxt
        if len(loop) >= 4 and loop[-1] == loop[0]:
            loop = loop[:-1]
        if len(loop) >= 3:
            loops.append(loop)
    for loop in loops:
        acc = (0.0, 0.0, 0.0)
        for idx in loop:
            acc = add(acc, builder.verts[idx])
        center = builder.add_vert(mul(acc, 1.0 / len(loop)))
        cu = uv_in(UV_HULL, 0.5, 0.35)
        for i in range(len(loop)):
            j = loop[i]
            k = loop[(i + 1) % len(loop)]
            builder.add_tri(center, j, k, cu, uv_in(UV_HULL, 0.2, 0.2), uv_in(UV_HULL, 0.8, 0.6))


def build_hull(ship, params):
    stations_n = params["stations"]
    rings = params["rings"]
    shell = Builder()
    stations = []
    ts = []
    for s in range(stations_n):
        t = s / (stations_n - 1)
        ts.append(t)
        xy = section_xy(t, ship, rings)
        z = -ship["length"] * 0.5 + t * ship["length"]
        keel = shell.add_vert((0.0, xy[0][1], z))
        star = [keel]
        port = [keel]
        for x, y in xy[1:]:
            star.append(shell.add_vert((x, y, z)))
            port.append(shell.add_vert((-x, y, z)))
        deck_y = xy[-1][1] + 0.10 * ship["fb_mid"]
        center = shell.add_vert((0.0, deck_y, z))
        stations.append({"star": star, "port": port, "center": center, "xy": xy, "t": t, "z": z})

    for s in range(stations_n - 1):
        a = stations[s]
        b = stations[s + 1]
        for i in range(rings - 1):
            ua0 = side_uv(UV_HULL, a["t"], a["xy"][i][1], a["xy"][0][1], a["xy"][-1][1])
            ua1 = side_uv(UV_HULL, a["t"], a["xy"][i + 1][1], a["xy"][0][1], a["xy"][-1][1])
            ub1 = side_uv(UV_HULL, b["t"], b["xy"][i + 1][1], b["xy"][0][1], b["xy"][-1][1])
            ub0 = side_uv(UV_HULL, b["t"], b["xy"][i][1], b["xy"][0][1], b["xy"][-1][1])
            shell.add_quad(a["star"][i], a["star"][i + 1], b["star"][i + 1], b["star"][i], ua0, ua1, ub1, ub0)
            shell.add_quad(a["port"][i], b["port"][i], b["port"][i + 1], a["port"][i + 1], ua0, ub0, ub1, ua1)
        da0 = uv_in(UV_DECK, a["t"], 0.50)
        da1 = uv_in(UV_DECK, a["t"], 0.92)
        db1 = uv_in(UV_DECK, b["t"], 0.92)
        db0 = uv_in(UV_DECK, b["t"], 0.50)
        shell.add_quad(a["center"], b["center"], b["star"][-1], a["star"][-1], da0, db0, db1, da1)
        pa0 = uv_in(UV_DECK, a["t"], 0.50)
        pa1 = uv_in(UV_DECK, a["t"], 0.08)
        pb1 = uv_in(UV_DECK, b["t"], 0.08)
        pb0 = uv_in(UV_DECK, b["t"], 0.50)
        shell.add_quad(a["center"], a["port"][-1], b["port"][-1], b["center"], pa0, pa1, pb1, pb0)

    cap_boundary_loops(shell)
    fix_winding(shell, (0.0, 0.0, 0.0))

    if params["cabin"]:
        deck_y = freeboard_at(0.40, ship)
        cabin = add_box(
            (0.0, deck_y + 0.28, -ship["length"] * 0.08),
            (ship["beam"] * 0.28, 0.56, ship["length"] * 0.16),
            UV_DECK,
        )
        shell.extend(cabin)
    return shell, stations


def add_box(center, size, rect):
    b = Builder()
    hx, hy, hz = size[0] * 0.5, size[1] * 0.5, size[2] * 0.5
    cx, cy, cz = center
    x0, x1 = cx - hx, cx + hx
    y0, y1 = cy - hy, cy + hy
    z0, z1 = cz - hz, cz + hz
    p = [
        b.add_vert((x0, y0, z0)),
        b.add_vert((x1, y0, z0)),
        b.add_vert((x1, y1, z0)),
        b.add_vert((x0, y1, z0)),
        b.add_vert((x0, y0, z1)),
        b.add_vert((x1, y0, z1)),
        b.add_vert((x1, y1, z1)),
        b.add_vert((x0, y1, z1)),
    ]
    def U(u, v):
        return uv_in(rect, u, v)
    # Outward CCW in Unity/right-hand space.
    b.add_quad(p[3], p[2], p[6], p[7], U(0, 1), U(1, 1), U(1, 0.6), U(0, 0.6))  # +Y
    b.add_quad(p[0], p[4], p[5], p[1], U(0, 0), U(0, 0.4), U(1, 0.4), U(1, 0))  # -Y
    b.add_quad(p[4], p[7], p[6], p[5], U(0, 0), U(0, 1), U(1, 1), U(1, 0))  # +Z
    b.add_quad(p[0], p[1], p[2], p[3], U(0, 0), U(1, 0), U(1, 1), U(0, 1))  # -Z
    b.add_quad(p[1], p[5], p[6], p[2], U(0, 0), U(1, 0), U(1, 1), U(0, 1))  # +X
    b.add_quad(p[4], p[0], p[3], p[7], U(0, 0), U(1, 0), U(1, 1), U(0, 1))  # -X
    fix_winding(b, center)
    return b


def add_cylinder(p0, p1, radius, sides, rect):
    b = Builder()
    axis = norm(sub(p1, p0))
    tmp = (1.0, 0.0, 0.0) if abs(axis[0]) < 0.85 else (0.0, 1.0, 0.0)
    u = norm(cross(axis, tmp))
    v = cross(axis, u)
    rings = []
    for pi, along in ((p0, 0.0), (p1, 1.0)):
        ring = []
        for s in range(sides):
            ang = 2.0 * math.pi * s / sides
            offset = add(mul(u, math.cos(ang) * radius), mul(v, math.sin(ang) * radius))
            ring.append(b.add_vert(add(pi, offset)))
        rings.append(ring)
    for s in range(sides):
        s2 = (s + 1) % sides
        u0 = uv_in(rect, s / sides, 0.15)
        u1 = uv_in(rect, (s + 1) / sides, 0.15)
        u2 = uv_in(rect, (s + 1) / sides, 0.85)
        u3 = uv_in(rect, s / sides, 0.85)
        b.add_quad(rings[0][s], rings[0][s2], rings[1][s2], rings[1][s], u0, u1, u2, u3)
    c0 = b.add_vert(p0)
    c1 = b.add_vert(p1)
    cu0 = uv_in(rect, 0.5, 0.08)
    cu1 = uv_in(rect, 0.5, 0.92)
    for s in range(sides):
        s2 = (s + 1) % sides
        b.add_tri(c0, rings[0][s2], rings[0][s], cu0, uv_in(rect, 0.2, 0.2), uv_in(rect, 0.8, 0.2))
        b.add_tri(c1, rings[1][s], rings[1][s2], cu1, uv_in(rect, 0.2, 0.8), uv_in(rect, 0.8, 0.8))
    fix_winding(b, lerp(p0, p1, 0.5))
    return b


def add_thick_grid(grid, thickness, rect, interior_hint=None):
    rows = len(grid)
    cols = len(grid[0])
    b = Builder()
    front_i = [[None] * cols for _ in range(rows)]
    back_i = [[None] * cols for _ in range(rows)]
    normals = [[(0.0, 1.0, 0.0) for _ in range(cols)] for _ in range(rows)]
    for r in range(rows):
        for c in range(cols):
            acc = (0.0, 0.0, 0.0)
            if r < rows - 1 and c < cols - 1:
                acc = add(acc, cross(sub(grid[r][c + 1], grid[r][c]), sub(grid[r + 1][c], grid[r][c])))
            if r > 0 and c > 0:
                acc = add(acc, cross(sub(grid[r][c - 1], grid[r][c]), sub(grid[r - 1][c], grid[r][c])))
            normals[r][c] = norm(acc)
    for r in range(rows):
        for c in range(cols):
            n = normals[r][c]
            front_i[r][c] = b.add_vert(add(grid[r][c], mul(n, thickness * 0.5)))
            back_i[r][c] = b.add_vert(sub(grid[r][c], mul(n, thickness * 0.5)))
    def gu(r, c):
        return uv_in(rect, c / max(1, cols - 1), 1.0 - r / max(1, rows - 1))
    for r in range(rows - 1):
        for c in range(cols - 1):
            b.add_quad(
                front_i[r][c], front_i[r][c + 1], front_i[r + 1][c + 1], front_i[r + 1][c],
                gu(r, c), gu(r, c + 1), gu(r + 1, c + 1), gu(r + 1, c),
            )
            b.add_quad(
                back_i[r][c], back_i[r + 1][c], back_i[r + 1][c + 1], back_i[r][c + 1],
                gu(r, c), gu(r + 1, c), gu(r + 1, c + 1), gu(r, c + 1),
            )
    def stitch(index_pairs):
        m = len(index_pairs)
        for i in range(m - 1):
            a, b0 = index_pairs[i]
            c, d = index_pairs[i + 1]
            b.add_quad(a, c, d, b0, uv_in(rect, 0.02, 0.02), uv_in(rect, 0.98, 0.02), uv_in(rect, 0.98, 0.12), uv_in(rect, 0.02, 0.12))
    top = [(front_i[0][c], back_i[0][c]) for c in range(cols)]
    bot = [(front_i[rows - 1][c], back_i[rows - 1][c]) for c in range(cols - 1, -1, -1)]
    left = [(front_i[r][0], back_i[r][0]) for r in range(rows - 1, -1, -1)]
    right = [(front_i[r][cols - 1], back_i[r][cols - 1]) for r in range(rows)]
    stitch(top)
    stitch(right)
    stitch(bot)
    stitch(left)
    if interior_hint is None:
        acc = (0.0, 0.0, 0.0)
        n = 0
        for row in grid:
            for p in row:
                acc = add(acc, p)
                n += 1
        interior_hint = mul(acc, 1.0 / n)
    fix_winding(b, interior_hint)
    return b


def grid_from_corners(corners, nu, nv, camber, camber_dir):
    # corners: head/top-left, top-right, bottom-right, bottom-left in (u,v)
    c00, c10, c11, c01 = corners
    grid = []
    for iv in range(nv + 1):
        v = iv / nv
        row = []
        for iu in range(nu + 1):
            u = iu / nu
            p0 = lerp(c00, c01, v)
            p1 = lerp(c10, c11, v)
            p = lerp(p0, p1, u)
            belly = math.sin(u * math.pi) * math.sin(v * math.pi) * camber
            p = add(p, mul(camber_dir, belly))
            row.append(p)
        grid.append(row)
    return grid


def yard_levels(mast, mode):
    base = mast["h"]
    if mode == "full":
        fracs = [0.42, 0.62, 0.80]
    elif mode == "mid":
        fracs = [0.48, 0.74]
    else:
        fracs = [0.58]
    return [base * f for f in fracs]


def build_rig(ship, params, stations):
    trim = Builder()
    sails = Builder()
    records = []
    deck = freeboard_at(0.5, ship)
    kind = ship["kind"]
    for mast in ship["masts"]:
        foot = (0.0, deck * 0.92, mast["z"])
        top = (0.0, mast["h"], mast["z"])
        trim.extend(add_cylinder(foot, top, mast["r"], params["sides"], UV_TRIM))
        records.append({"type": "mast", "name": mast["name"], "z": mast["z"], "h": mast["h"]})
        if kind == "cutter":
            continue
        half_w = ship["beam"] * 0.42
        for yi, y in enumerate(yard_levels(mast, params["yards"])):
            y = min(y, mast["h"] - 0.35)
            yard_a = (-half_w, y, mast["z"])
            yard_b = (half_w, y, mast["z"])
            trim.extend(add_cylinder(yard_a, yard_b, mast["r"] * 0.45, max(4, params["sides"] - 2), UV_TRIM))
            drop = ship["mast_height"] * (0.16 if params["yards"] == "min" else 0.14)
            drop = min(drop, y - deck - 0.25)
            camber = min(0.35, ship["length"] * 0.012)
            z0 = mast["z"] + 0.05
            corners = [
                (-half_w, y, z0),
                (half_w, y, z0),
                (half_w * 0.92, y - drop, z0),
                (-half_w * 0.92, y - drop, z0),
            ]
            grid = grid_from_corners(corners, params["sail_u"], params["sail_v"], camber, (0.0, 0.0, 1.0))
            sails.extend(add_thick_grid(grid, 0.035, UV_SAIL))
            records.append({
                "type": "sail",
                "rig": "square",
                "mast": mast["name"],
                "index": yi,
                "bbox": bbox_of_grid(grid),
            })

    if kind == "cutter":
        mast = ship["masts"][0]
        mz = mast["z"]
        boom_len = min(7.4, mz - (-ship["length"] * 0.5) - 0.55)
        gaff_len = boom_len * 0.72
        tack = (0.0, deck + 0.35, mz)
        clew = (0.0, deck + 0.55, mz - boom_len)
        head = (0.0, mast["h"] * 0.78, mz)
        peak = (0.0, mast["h"] * 0.62, mz - gaff_len)
        trim.extend(add_cylinder(tack, clew, 0.045, max(4, params["sides"] - 2), UV_TRIM))
        trim.extend(add_cylinder((0.0, mast["h"] * 0.55, mz), peak, 0.04, max(4, params["sides"] - 2), UV_TRIM))
        grid = grid_from_corners(
            [head, peak, clew, tack],
            params["sail_u"] + 1,
            params["sail_v"] + 1,
            0.28,
            (1.0, 0.0, 0.0),
        )
        sails.extend(add_thick_grid(grid, 0.03, UV_SAIL))
        records.append({"type": "sail", "rig": "mainsail", "mast": "main", "bbox": bbox_of_grid(grid)})
        bow_z = ship["length"] * 0.5 - 0.08
        heads = [
            ("inner", mast["h"] * 0.62, bow_z - 1.35, 0.22),
            ("outer", mast["h"] * 0.84, bow_z, 0.18),
        ]
        for name, head_y, tack_z, camber in heads:
            h = (0.0, head_y, mz + 0.05)
            t = (0.0, deck + 0.25, tack_z)
            c = (0.55, deck + 0.70, (mz + tack_z) * 0.5)
            grid = grid_from_corners(
                [h, add(h, (0.05, -0.05, 0.08)), c, t],
                max(1, params["sail_u"]),
                max(2, params["sail_v"]),
                camber,
                (1.0, 0.0, 0.0),
            )
            sails.extend(add_thick_grid(grid, 0.025, UV_SAIL))
            records.append({"type": "sail", "rig": "headsail", "name": name, "mast": "main", "bbox": bbox_of_grid(grid)})

    # Rudder stays inside the frozen length and draft.
    rudder_z = -ship["length"] * 0.5 + 0.18
    rudder = add_box(
        (0.0, -ship["draft"] * 0.35, rudder_z),
        (0.08, ship["draft"] * 0.85, 0.28),
        UV_TRIM,
    )
    trim.extend(rudder)

    if params["rails"]:
        sheer_pts = []
        for st in stations[::2]:
            x, y = st["xy"][-1]
            sheer_pts.append((x * 0.98, y + 0.02, st["z"]))
        for i in range(len(sheer_pts) - 1):
            a = sheer_pts[i]
            b = sheer_pts[i + 1]
            trim.extend(add_cylinder(a, b, 0.035, 4, UV_TRIM))
            trim.extend(add_cylinder((-a[0], a[1], a[2]), (-b[0], b[1], b[2]), 0.035, 4, UV_TRIM))
    return trim, sails, records


def bbox_of_grid(grid):
    xs, ys, zs = [], [], []
    for row in grid:
        for p in row:
            xs.append(p[0])
            ys.append(p[1])
            zs.append(p[2])
    return {
        "min": [min(xs), min(ys), min(zs)],
        "max": [max(xs), max(ys), max(zs)],
    }


def bounds_of(builder):
    xs = [v[0] for v in builder.verts]
    ys = [v[1] for v in builder.verts]
    zs = [v[2] for v in builder.verts]
    return (min(xs), min(ys), min(zs)), (max(xs), max(ys), max(zs))


def combined_bounds(parts):
    lo = [1e9, 1e9, 1e9]
    hi = [-1e9, -1e9, -1e9]
    for part in parts:
        if not part.verts:
            continue
        a, b = bounds_of(part)
        for i in range(3):
            lo[i] = min(lo[i], a[i])
            hi[i] = max(hi[i], b[i])
    return lo, hi


def enforce_metrics(ship, hull, others):
    """Hit the frozen beam, draft, and length box without moving the masthead."""
    min_y = min(v[1] for v in hull.verts)
    if min_y < -1e-8:
        scale = ship["draft"] / abs(min_y)
        hull.verts = [(v[0], v[1] * scale if v[1] < 0.0 else v[1], v[2]) for v in hull.verts]
    parts = [hull] + list(others)
    max_x = max(abs(v[0]) for part in parts for v in part.verts)
    if max_x > 1e-8:
        sx = (ship["beam"] * 0.5) / max_x
        for part in parts:
            part.verts = [(v[0] * sx, v[1], v[2]) for v in part.verts]
    half_l = ship["length"] * 0.5
    half_b = ship["beam"] * 0.5
    for part in parts:
        part.verts = [
            (
                min(half_b, max(-half_b, v[0])),
                min(ship["mast_height"], max(-ship["draft"], v[1])),
                min(half_l, max(-half_l, v[2])),
            )
            for v in part.verts
        ]


def params_for(ship, lod):
    params = dict(LOD_PARAMS[lod])
    if ship["id"] == "SHIP-M" and lod == 0:
        params["stations"] = 22
        params["sail_u"] = 5
        params["sail_v"] = 6
    elif ship["id"] == "SHIP-H" and lod == 0:
        params["stations"] = 26
        params["rings"] = 9
        params["sail_u"] = 5
        params["sail_v"] = 6
    elif ship["id"] == "SHIP-H" and lod == 1:
        params["stations"] = 14
        params["sail_u"] = 3
        params["sail_v"] = 3
    return params


def assert_bounds(ship, parts):
    lo, hi = combined_bounds(parts)
    errors = []
    if hi[0] - lo[0] > ship["beam"] + 0.02:
        errors.append("beam %.4f > %.4f" % (hi[0] - lo[0], ship["beam"]))
    if abs(lo[0] + hi[0]) > 0.05:
        errors.append("beam not centered %s %s" % (lo[0], hi[0]))
    if lo[1] < -ship["draft"] - 0.01:
        errors.append("below draft %.4f" % lo[1])
    if abs(lo[1] + ship["draft"]) > 0.03:
        errors.append("keel %.4f != draft %.4f" % (lo[1], -ship["draft"]))
    if hi[1] > ship["mast_height"] + 0.01:
        errors.append("above mast %.4f" % hi[1])
    if abs(hi[1] - ship["mast_height"]) > 0.03:
        errors.append("mast top %.4f != %.4f" % (hi[1], ship["mast_height"]))
    if hi[2] > ship["length"] * 0.5 + 0.01 or lo[2] < -ship["length"] * 0.5 - 0.01:
        errors.append("length overrun %s %s" % (lo[2], hi[2]))
    if abs((hi[2] + lo[2]) * 0.5) > 0.08:
        errors.append("length center %s" % ((hi[2] + lo[2]) * 0.5))
    span_z = hi[2] - lo[2]
    if abs(span_z - ship["length"]) > 0.08:
        errors.append("length span %.4f != %.4f" % (span_z, ship["length"]))
    if errors:
        raise RuntimeError(ship["id"] + " bounds: " + "; ".join(errors))
    return {"min": lo, "max": hi}


def validate_rig(ship, records):
    masts = [r for r in records if r["type"] == "mast"]
    sails = [r for r in records if r["type"] == "sail"]
    errors = []
    if len(masts) != len(ship["masts"]):
        errors.append("mast count %d" % len(masts))
    if ship["kind"] == "cutter":
        mains = [s for s in sails if s["rig"] == "mainsail"]
        heads = [s for s in sails if s["rig"] == "headsail"]
        squares = [s for s in sails if s["rig"] == "square"]
        if len(mains) < 1 or len(heads) < 2 or squares:
            errors.append("cutter sails main=%d head=%d square=%d" % (len(mains), len(heads), len(squares)))
        mz = ship["masts"][0]["z"]
        for s in mains:
            cz = 0.5 * (s["bbox"]["min"][2] + s["bbox"]["max"][2])
            if cz >= mz:
                errors.append("mainsail not aft")
            if s["bbox"]["max"][2] - s["bbox"]["min"][2] < s["bbox"]["max"][0] - s["bbox"]["min"][0]:
                errors.append("mainsail not fore-and-aft")
        for s in heads:
            cz = 0.5 * (s["bbox"]["min"][2] + s["bbox"]["max"][2])
            if cz <= mz:
                errors.append("headsail not forward")
    else:
        squares = [s for s in sails if s["rig"] == "square"]
        if len(squares) < len(masts):
            errors.append("square sails %d for %d masts" % (len(squares), len(masts)))
        for s in squares:
            sx = s["bbox"]["max"][0] - s["bbox"]["min"][0]
            sz = s["bbox"]["max"][2] - s["bbox"]["min"][2]
            if sx <= sz * 1.2:
                errors.append("square sail aspect %.3f / %.3f" % (sx, sz))
        names = {m["name"] for m in masts}
        used = {s["mast"] for s in squares}
        if names - used:
            errors.append("masts without square sails %s" % (names - used))
    if errors:
        raise RuntimeError(ship["id"] + " rig: " + "; ".join(errors))


def to_blender_mesh(name, builder, material):
    mesh = bpy.data.meshes.new(name)
    # Y/Z swap is a reflection, so reverse winding once on the way into Blender.
    verts = [(v[0], v[2], v[1]) for v in builder.verts]
    faces = [(f[0], f[2], f[1]) for f in builder.faces]
    uvs = []
    for n in range(len(builder.faces)):
        u0, u1, u2 = builder.uvs[n * 3 : n * 3 + 3]
        uvs.extend((u0, u2, u1))
    mesh.from_pydata(verts, [], faces)
    mesh.validate(clean_customdata=False)
    mesh.update()
    uvlayer = mesh.uv_layers.new(name="UVMap")
    k = 0
    for poly in mesh.polygons:
        poly.use_smooth = True
        for li in poly.loop_indices:
            uvlayer.data[li].uv = uvs[k]
            k += 1
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    obj.data.materials.append(material)
    for poly in obj.data.polygons:
        poly.material_index = 0
    # Closed shells: force normals outward so the back of every sail survives a 360 turn.
    import bmesh
    bm = bmesh.new()
    bm.from_mesh(mesh)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(mesh)
    bm.free()
    mesh.update()
    return obj


def ensure_starboard_outward(obj):
    mesh = obj.data
    best = None
    best_x = -1e9
    for poly in mesh.polygons:
        if poly.center.x > best_x and abs(poly.normal.x) > 0.25:
            best_x = poly.center.x
            best = poly
    if best is not None and best.normal.x < 0.0:
        bm_flip(mesh)


def bm_flip(mesh):
    import bmesh
    bm = bmesh.new()
    bm.from_mesh(mesh)
    bmesh.ops.reverse_faces(bm, faces=bm.faces)
    bm.to_mesh(mesh)
    bm.free()
    mesh.update()


def make_material(name, image, tint):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    mat.use_backface_culling = True
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    bsdf = nodes.get("Principled BSDF")
    tex = nodes.new("ShaderNodeTexImage")
    tex.image = image
    links.new(tex.outputs["Color"], bsdf.inputs["Base Color"])
    bsdf.inputs["Roughness"].default_value = 0.72 if "Sail" not in name else 0.84
    bsdf.inputs["Metallic"].default_value = 0.0
    bsdf.inputs["Base Color"].default_value = (tint[0], tint[1], tint[2], 1.0)
    return mat


def paint_atlas(size):
    buf = array.array("f", [0.0]) * (size * size * 4)

    def set_px(x, y, rgb):
        # Blender pixels are bottom-row first.
        i = (y * size + x) * 4
        buf[i] = rgb[0]
        buf[i + 1] = rgb[1]
        buf[i + 2] = rgb[2]
        buf[i + 3] = 1.0

    for y in range(size):
        v = y / (size - 1)
        for x in range(size):
            u = x / (size - 1)
            if u < 0.50 and v < 0.72:
                plank = int(v * 46)
                seam = (v * 46) % 1.0 < 0.06
                shift = 0.06 * math.sin((u * 18.0 + plank) * 1.7)
                col = tuple(max(0.0, min(1.0, c + shift)) for c in WOOD)
                if seam:
                    col = tuple(c * 0.55 for c in col)
                if 0.52 < v < 0.58:
                    col = tuple(c * 0.35 for c in WOOD)
                if v < 0.50:
                    col = (col[0] * 0.72, col[1] * 0.78, col[2] * 0.70)
                set_px(x, y, col)
            elif u < 0.50:
                plank = int(u * 28)
                seam = (u * 28) % 1.0 < 0.05
                col = tuple(min(1.0, c * 1.08) for c in WOOD)
                if seam:
                    col = tuple(c * 0.62 for c in col)
                set_px(x, y, col)
            elif v >= 0.50:
                cloth = (v * 22) % 1.0
                band = 0.08 if cloth < 0.08 or (u * 14) % 1.0 < 0.04 else 0.0
                col = tuple(min(1.0, c + band) for c in SAIL)
                set_px(x, y, col)
            else:
                if u < 0.75:
                    grain = 0.05 * math.sin(v * 80.0)
                    col = tuple(max(0.0, min(1.0, c + grain)) for c in TRIM_WOOD)
                else:
                    col = TRIM_METAL
                    if int(v * 30) % 5 == 0:
                        col = tuple(c * 0.75 for c in col)
                set_px(x, y, col)
    img = bpy.data.images.new("ship_atlas_%d" % size, size, size, alpha=False)
    img.pixels.foreach_set(buf)
    img.pack()
    path = os.path.join(TEXTURE_DIR, "ship_atlas_%d.png" % size)
    img.filepath_raw = path
    img.file_format = "PNG"
    img.save()
    return img


def export_fbx(objects, path):
    bpy.ops.object.select_all(action="DESELECT")
    for obj in objects:
        obj.select_set(True)
    bpy.context.view_layer.objects.active = objects[0]
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
        path_mode="COPY",
        embed_textures=False,
    )


def manifold_report(obj):
    import bmesh
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    bm.edges.ensure_lookup_table()
    boundary = sum(1 for e in bm.edges if e.is_boundary)
    nonman = sum(1 for e in bm.edges if not e.is_manifold)
    bm.free()
    return {"triangles": len(obj.data.polygons), "boundary_edges": boundary, "nonmanifold_edges": nonman}


def look_camera(cam, target, distance, yaw_deg, pitch_deg):
    yaw = math.radians(yaw_deg)
    pitch = math.radians(pitch_deg)
    # Blender space: X starboard, Y bow, Z up.
    pos = Vector((
        distance * math.cos(pitch) * math.sin(yaw),
        distance * math.cos(pitch) * math.cos(yaw),
        distance * math.sin(pitch),
    ))
    cam.location = Vector(target) + pos
    direction = Vector(target) - cam.location
    cam.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()


def render_still(scene, path):
    scene.render.filepath = path
    bpy.ops.render.render(write_still=True)


def hide(objs, value):
    for obj in objs:
        obj.hide_render = value
        obj.hide_set(value)


def main():
    os.makedirs(EXPORT_DIR, exist_ok=True)
    os.makedirs(TEXTURE_DIR, exist_ok=True)
    os.makedirs(TURN_DIR, exist_ok=True)
    os.makedirs(os.path.dirname(SOURCE_BLEND), exist_ok=True)
    bpy.ops.wm.read_factory_settings(use_empty=True)
    image = paint_atlas(1024)
    image512 = paint_atlas(512)
    mat_hull = make_material("Hull", image, (1, 1, 1))
    mat_trim = make_material("Trim", image, (1, 1, 1))
    mat_sail = make_material("Sail", image, (1, 1, 1))
    report = {
        "generator": "art_source/production/ships/generate_ships.py",
        "blender": bpy.app.version_string,
        "coordinate_space": "Unity +X starboard, +Y up, +Z bow, pivot waterline center",
        "texture": {
            "lod0_and_lod1": "textures/ship_atlas_1024.png",
            "lod2_optional_drop": "textures/ship_atlas_512.png",
            "lod1_cap": "T05 does not state an LOD1 texture cap. This candidate does not invent one. LOD0 and LOD1 share the single 1024 atlas. LOD2 uses the 512 atlas.",
            "material_roles": ["Hull", "Sail", "Trim"],
        },
        "production_choices_not_new_thresholds": {
            "freeboard_m": "Chosen so the sheer reads above Y=0. Not in the frozen T05 table.",
            "ship_l_mast_z_m": "1.278. Sailplan mast is drawn at x=239 with stern x=72 and 18 px/m, so z=-8+(239-72)/18. The SVG says T06 chooses the step and the drawing does not freeze it.",
            "other_mast_steps_and_minor_mast_heights": "Chosen so fore/main/mizzen silhouettes separate. Only the named main-mast height is the frozen 主桅高.",
            "wake_socket": "T05 suggested stern-centerline coordinates are adopted, not promoted to a new threshold.",
            "bowsprit": "Cutter headsails end at the stem. No geometry extends the frozen length.",
        },
        "ships": [],
    }
    render_groups = []
    for ship in SHIPS:
        ship_report = {
            "id": ship["id"],
            "name": ship["name"],
            "frozen": {
                "length_m": ship["length"],
                "beam_m": ship["beam"],
                "draft_m": ship["draft"],
                "main_mast_m": ship["mast_height"],
                "r_nav_m": ship["r_nav"],
                "wake_suggested_adopted": ship["wake"],
                "lod_triangle_caps": ship["caps"],
            },
            "lods": [],
        }
        for lod in (0, 1, 2):
            params = params_for(ship, lod)
            hull, stations = build_hull(ship, params)
            trim, sails, records = build_rig(ship, params, stations)
            enforce_metrics(ship, hull, [trim, sails])
            assert_bounds(ship, [hull, trim, sails])
            validate_rig(ship, records)
            cap = ship["caps"][lod]
            total = hull.tri_count() + trim.tri_count() + sails.tri_count()
            if total > cap:
                raise RuntimeError("%s LOD%d triangles %d exceed cap %d" % (ship["id"], lod, total, cap))
            objs = []
            for role, builder, mat in (
                ("Hull", hull, mat_hull),
                ("Masts", trim, mat_trim),
                ("Sails", sails, mat_sail),
            ):
                obj = to_blender_mesh("%s_LOD%d_%s" % (ship["id"], lod, role), builder, mat)
                obj["t06_role"] = role
                obj["t06_ship"] = ship["id"]
                obj["t06_lod"] = lod
                if role == "Hull":
                    ensure_starboard_outward(obj)
                objs.append(obj)
            # Export a renamed selection so Unity sees Hull / Masts / Sails.
            temps = []
            for obj in objs:
                dup = obj.copy()
                dup.data = obj.data
                dup.name = obj["t06_role"]
                bpy.context.collection.objects.link(dup)
                temps.append(dup)
            fbx_path = os.path.join(EXPORT_DIR, "%s_LOD%d.fbx" % (ship["id"], lod))
            export_fbx(temps, fbx_path)
            for temp in temps:
                bpy.data.objects.remove(temp, do_unlink=True)
            manifolds = {obj["t06_role"]: manifold_report(obj) for obj in objs}
            bad = {k: v for k, v in manifolds.items() if v["boundary_edges"] or v["nonmanifold_edges"]}
            if bad:
                raise RuntimeError("%s LOD%d open mesh %s" % (ship["id"], lod, json.dumps(bad)))
            lo, hi = combined_bounds([hull, trim, sails])
            ship_report["lods"].append({
                "lod": lod,
                "triangles": {
                    "hull": hull.tri_count(),
                    "masts_trim": trim.tri_count(),
                    "sails": sails.tri_count(),
                    "total": total,
                    "cap": cap,
                },
                "fbx": "export/%s_LOD%d.fbx" % (ship["id"], lod),
                "manifold": manifolds,
                "bounds_unity_m": {"min": lo, "max": hi},
                "different_from_other_lods": True,
            })
            render_groups.append({"ship": ship, "lod": lod, "objects": objs, "records": records})
            print("%s LOD%d tris=%d cap=%d" % (ship["id"], lod, total, cap))
        counts = [item["triangles"]["total"] for item in ship_report["lods"]]
        if not (counts[0] > counts[1] > counts[2]):
            raise RuntimeError("%s LOD counts not strictly decreasing: %s" % (ship["id"], counts))
        # Vertex-hash difference is implied by different triangle counts and topology params.
        ship_report["sail_records_lod0"] = render_groups[[g["ship"]["id"] for g in render_groups].index(ship["id"])]["records"]
        report["ships"].append(ship_report)

    # Render from the Blender-space meshes. Water and cameras are not exported.
    scene = bpy.context.scene
    engines = [item.identifier for item in bpy.types.RenderSettings.bl_rna.properties["engine"].enum_items]
    if "BLENDER_EEVEE_NEXT" in engines:
        scene.render.engine = "BLENDER_EEVEE_NEXT"
    elif "BLENDER_EEVEE" in engines:
        scene.render.engine = "BLENDER_EEVEE"
    else:
        scene.render.engine = "CYCLES"
        scene.cycles.device = "CPU"
        scene.cycles.samples = 16
    if hasattr(scene, "eevee") and hasattr(scene.eevee, "taa_render_samples"):
        scene.eevee.taa_render_samples = 8
    scene.render.resolution_x = 1280
    scene.render.resolution_y = 720
    scene.render.image_settings.file_format = "PNG"
    world = bpy.data.worlds.new("sea")
    scene.world = world
    world.use_nodes = False
    if hasattr(world, "color"):
        world.color = (0.07, 0.22, 0.28)
    sun_data = bpy.data.lights.new("sun", "SUN")
    sun_data.energy = 4.0
    sun = bpy.data.objects.new("sun", sun_data)
    bpy.context.collection.objects.link(sun)
    sun.rotation_euler = (math.radians(48), 0.0, math.radians(35))
    water_mesh = bpy.data.meshes.new("water")
    water_mesh.from_pydata([(-80, -80, 0), (80, -80, 0), (80, 80, 0), (-80, 80, 0)], [], [(0, 1, 2), (0, 2, 3)])
    water = bpy.data.objects.new("RENDER_ONLY_water", water_mesh)
    bpy.context.collection.objects.link(water)
    water_mat = bpy.data.materials.new("water")
    water_mat.use_nodes = True
    water_mat.diffuse_color = (0.16, 0.45, 0.52, 1.0)
    bsdf = water_mat.node_tree.nodes.get("Principled BSDF")
    bsdf.inputs["Base Color"].default_value = (0.10, 0.37, 0.42, 1.0)
    bsdf.inputs["Roughness"].default_value = 0.18
    bsdf.inputs["Alpha"].default_value = 0.55
    water.data.materials.append(water_mat)
    cam_data = bpy.data.cameras.new("cam")
    cam_data.lens = 38
    cam_data.clip_end = 400
    cam = bpy.data.objects.new("cam", cam_data)
    bpy.context.collection.objects.link(cam)
    scene.camera = cam
    skip = os.environ.get("T06_SKIP_RENDER") == "1"
    turntable = []
    if not skip:
        for group in render_groups:
            hide([obj for g in render_groups for obj in g["objects"]], True)
            hide(group["objects"], False)
            ship = group["ship"]
            lod = group["lod"]
            target = (0.0, ship["length"] * 0.0, ship["mast_height"] * 0.38)
            # target is blender (x, y=bow, z=up)
            target = (0.0, 0.0, ship["mast_height"] * 0.34)
            dist = max(ship["length"], ship["mast_height"]) * 1.55
            yaws = list(range(0, 360, 45)) if lod == 0 else [40, 200]
            for yaw in yaws:
                look_camera(cam, target, dist, yaw, 16 if lod else 18)
                name = "%s_LOD%d_yaw%03d.png" % (ship["id"], lod, yaw)
                path = os.path.join(TURN_DIR, name)
                render_still(scene, path)
                turntable.append(name)
                print("rendered", name)
            if lod == 0:
                cam_data.type = "ORTHO"
                cam_data.ortho_scale = ship["length"] * 1.35
                look_camera(cam, (0.0, 0.0, ship["draft"]), ship["length"], 90, 0.01)
                for label, yaw in (("side", 90), ("top", 0), ("bottom", 0)):
                    if label == "top":
                        cam.location = (0.0, 0.0, ship["mast_height"] * 1.4)
                        cam.rotation_euler = (0.0, 0.0, 0.0)
                        cam_data.ortho_scale = ship["length"] * 1.25
                    elif label == "bottom":
                        cam.location = (0.0, 0.0, -ship["mast_height"])
                        cam.rotation_euler = (math.radians(180), 0.0, 0.0)
                        cam_data.ortho_scale = ship["length"] * 1.25
                    else:
                        look_camera(cam, (0.0, 0.0, ship["mast_height"] * 0.35), ship["length"], 90, 0.01)
                        cam_data.ortho_scale = max(ship["length"], ship["mast_height"] + ship["draft"]) * 1.45
                    name = "%s_LOD0_%s.png" % (ship["id"], label)
                    render_still(scene, os.path.join(TURN_DIR, name))
                    turntable.append(name)
                cam_data.type = "PERSP"
        # Lineup of the three LOD0 hulls.
        hide([obj for g in render_groups for obj in g["objects"]], True)
        offsets = {"SHIP-L": -34.0, "SHIP-M": 0.0, "SHIP-H": 38.0}
        moved = []
        for group in render_groups:
            if group["lod"] != 0:
                continue
            hide(group["objects"], False)
            dx = offsets[group["ship"]["id"]]
            for obj in group["objects"]:
                obj.location.x = dx
                moved.append(obj)
        cam_data.type = "ORTHO"
        cam_data.ortho_scale = 130
        cam.location = (55.0, -78.0, 26.0)
        direction = Vector((2.0, 0.0, 8.0)) - cam.location
        cam.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()
        name = "lineup_LOD0_oblique.png"
        render_still(scene, os.path.join(TURN_DIR, name))
        turntable.append(name)
        for obj in moved:
            obj.location.x = 0.0
    report["turntable_files"] = turntable
    report["render_engine"] = scene.render.engine
    report["source_blend"] = "source/S1_T06_ships.blend"
    with open(os.path.join(EVIDENCE_DIR, "mesh_metrics.json"), "w", encoding="utf-8") as fh:
        json.dump(report, fh, ensure_ascii=False, indent=2)
    water.hide_render = True
    bpy.ops.wm.save_as_mainfile(filepath=SOURCE_BLEND)
    print("WROTE", SOURCE_BLEND)


if __name__ == "__main__":
    try:
        main()
    except Exception:
        traceback.print_exc()
        sys.exit(1)
