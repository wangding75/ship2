"""Shared contour checks for the T07 island module package.

Coordinates in the canonical document are integers of 1e-5 metre.
Rings do not repeat the first point. Outer rings are counterclockwise
under the XZ shoelace sign. Hole rings are clockwise. This module does
not import Blender and does not write a WorldNavigationData record.
"""

import hashlib
import json

QUANTUM = 100000  # 1e-5 m


def q_int(value):
    return int(round(float(value) * QUANTUM))


def q_m(value):
    return q_int(value) / QUANTUM


def canonical_bytes(document):
    payload = json.dumps(
        document, sort_keys=True, separators=(",", ":"), ensure_ascii=True
    )
    return payload.encode("utf-8")


def geometry_sha(document):
    return hashlib.sha256(canonical_bytes(document)).hexdigest()


def ring_ints(points_xz):
    ring = [[q_int(x), q_int(z)] for x, z in points_xz]
    if len(ring) >= 2 and ring[0] == ring[-1]:
        ring = ring[:-1]
    return ring


def ring_meters(ring):
    return [{"x_m": point[0] / QUANTUM, "z_m": point[1] / QUANTUM} for point in ring]


def shoelace_twice(ring):
    total = 0
    count = len(ring)
    for index in range(count):
        x1, z1 = ring[index]
        x2, z2 = ring[(index + 1) % count]
        total += x1 * z2 - x2 * z1
    return total


def ensure_ccw(ring):
    if shoelace_twice(ring) < 0:
        ring = list(reversed(ring))
    return ring


def ensure_cw(ring):
    if shoelace_twice(ring) > 0:
        ring = list(reversed(ring))
    return ring


def _orient(ax, az, bx, bz, cx, cz):
    return (bx - ax) * (cz - az) - (bz - az) * (cx - ax)


def proper_intersection(a, b, c, d):
    """True when open segments ab and cd cross. Shared endpoints do not count."""
    o1 = _orient(a[0], a[1], b[0], b[1], c[0], c[1])
    o2 = _orient(a[0], a[1], b[0], b[1], d[0], d[1])
    o3 = _orient(c[0], c[1], d[0], d[1], a[0], a[1])
    o4 = _orient(c[0], c[1], d[0], d[1], b[0], b[1])
    return o1 > 0 and o2 < 0 and o3 > 0 and o4 < 0 or o1 < 0 and o2 > 0 and o3 < 0 and o4 > 0


def ring_errors(ring, closed_name):
    errors = []
    if len(ring) < 3:
        errors.append(closed_name + " has fewer than 3 points")
        return errors
    if ring[0] == ring[-1]:
        errors.append(closed_name + " repeats the closing point")
    for index, point in enumerate(ring):
        nxt = ring[(index + 1) % len(ring)]
        if point == nxt:
            errors.append(closed_name + " zero-length edge at %d" % index)
    count = len(ring)
    for i in range(count):
        a = ring[i]
        b = ring[(i + 1) % count]
        for j in range(i + 1, count):
            if abs(i - j) <= 1 or (i == 0 and j == count - 1):
                continue
            c = ring[j]
            d = ring[(j + 1) % count]
            if j == i + 1 or (i == 0 and j == count - 1):
                continue
            # Skip adjacent edges. The wrap pair (last, first) is adjacent to edge 0.
            if {i, (i + 1) % count} & {j, (j + 1) % count}:
                continue
            if proper_intersection(a, b, c, d):
                errors.append(closed_name + " self-intersects at edges %d and %d" % (i, j))
                return errors
    return errors


def point_in_ring(x, z, ring):
    """Even-odd test on metre coordinates. Boundary counts as inside."""
    inside = False
    count = len(ring)
    for index in range(count):
        x1, z1 = ring[index][0] / QUANTUM, ring[index][1] / QUANTUM
        x2, z2 = ring[(index + 1) % count][0] / QUANTUM, ring[(index + 1) % count][1] / QUANTUM
        if _dist_point_seg(x, z, x1, z1, x2, z2) <= 1e-6:
            return True
        if (z1 > z) != (z2 > z):
            xin = (x2 - x1) * (z - z1) / (z2 - z1) + x1
            if x < xin:
                inside = not inside
    return inside


def point_in_polygon(x, z, polygon):
    if not point_in_ring(x, z, polygon["outer"]):
        return False
    for hole in polygon["holes"]:
        if point_in_ring(x, z, hole):
            return False
    return True


def _dist_point_seg(px, pz, ax, az, bx, bz):
    dx = bx - ax
    dz = bz - az
    length2 = dx * dx + dz * dz
    if length2 <= 0.0:
        return ((px - ax) ** 2 + (pz - az) ** 2) ** 0.5
    t = ((px - ax) * dx + (pz - az) * dz) / length2
    if t < 0.0:
        t = 0.0
    elif t > 1.0:
        t = 1.0
    qx = ax + t * dx
    qz = az + t * dz
    return ((px - qx) ** 2 + (pz - qz) ** 2) ** 0.5


def distance_to_polygon(x, z, polygon):
    if point_in_polygon(x, z, polygon):
        return 0.0
    best = None
    rings = [polygon["outer"]] + list(polygon["holes"])
    for ring in rings:
        count = len(ring)
        for index in range(count):
            ax, az = ring[index][0] / QUANTUM, ring[index][1] / QUANTUM
            bx, bz = ring[(index + 1) % count][0] / QUANTUM, ring[(index + 1) % count][1] / QUANTUM
            dist = _dist_point_seg(x, z, ax, az, bx, bz)
            if best is None or dist < best:
                best = dist
    return best


def max_radius_m(ring):
    best = 0.0
    for x, z in ring:
        r = ((x / QUANTUM) ** 2 + (z / QUANTUM) ** 2) ** 0.5
        if r > best:
            best = r
    return best


def chord_deviation_m(full_ring, step):
    """Max distance from a skipped vertex to the chord kept by a LOD subsample."""
    count = len(full_ring)
    if step <= 1 or count == 0:
        return 0.0
    worst = 0.0
    kept = list(range(0, count, step))
    for slot, start in enumerate(kept):
        end = kept[(slot + 1) % len(kept)]
        ax, az = full_ring[start][0] / QUANTUM, full_ring[start][1] / QUANTUM
        bx, bz = full_ring[end][0] / QUANTUM, full_ring[end][1] / QUANTUM
        index = (start + 1) % count
        while index != end:
            px, pz = full_ring[index][0] / QUANTUM, full_ring[index][1] / QUANTUM
            dist = _dist_point_seg(px, pz, ax, az, bx, bz)
            if dist > worst:
                worst = dist
            index = (index + 1) % count
    return worst
