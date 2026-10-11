"""A small perspective renderer for Roblox part assemblies -- no Studio needed.

Painter's algorithm over flat-shaded faces: blocks are boxes, cylinders are 16-sided prisms along local
X (as in Roblox), balls are low-poly spheres, wedges are wedges. Faces are clipped against the near
plane, back faces are culled, and each face is lit by a key light plus ambient. It is not Roblox's
renderer -- no materials, shadows or fog -- but proportions, placement, interpenetration and how a thing
sits in a hand or reads from the player's eye are exactly right, which is what a pass needs.

Coordinates are Roblox's: camera looks down its own -Z, +Y up. A part is
    {"sz": [x, y, z], "cf": 4x4 (or 12 CFrame components), "shape": "Block"|"Cylinder"|"Ball"|"Wedge",
     "color": [r, g, b] or "#rrggbb", "tr": transparency 0..1}
"""
from __future__ import annotations

import math

import numpy as np
from PIL import Image, ImageDraw

KEY = np.array([-0.45, 0.8, 0.4])
KEY = KEY / np.linalg.norm(KEY)


def cf_matrix(c) -> np.ndarray:
    """12 CFrame components (x y z R00..R22) or a 4x4 -> 4x4."""
    a = np.asarray(c, float)
    if a.shape == (4, 4):
        return a
    m = np.eye(4)
    m[:3, 3] = a[0:3]
    m[:3, :3] = a[3:12].reshape(3, 3)
    return m


def angles(rx, ry, rz) -> np.ndarray:
    """CFrame.Angles in degrees -> 3x3 (R = Rx * Ry * Rz)."""
    x, y, z = math.radians(rx), math.radians(ry), math.radians(rz)
    cx, sx, cy, sy, cz, sz = math.cos(x), math.sin(x), math.cos(y), math.sin(y), math.cos(z), math.sin(z)
    Rx = np.array([[1, 0, 0], [0, cx, -sx], [0, sx, cx]])
    Ry = np.array([[cy, 0, sy], [0, 1, 0], [-sy, 0, cy]])
    Rz = np.array([[cz, -sz, 0], [sz, cz, 0], [0, 0, 1]])
    return Rx @ Ry @ Rz


def tf(pos=(0, 0, 0), rot=None) -> np.ndarray:
    m = np.eye(4)
    m[:3, 3] = pos
    if rot is not None:
        m[:3, :3] = rot
    return m


def look_at(eye, target, up=(0, 1, 0)) -> np.ndarray:
    eye, target, up = (np.asarray(v, float) for v in (eye, target, up))
    back = eye - target
    back /= np.linalg.norm(back)
    right = np.cross(up, back)
    if np.linalg.norm(right) < 1e-6:
        right = np.array([1.0, 0, 0])
    right /= np.linalg.norm(right)
    upv = np.cross(back, right)
    m = np.eye(4)
    m[:3, 0], m[:3, 1], m[:3, 2], m[:3, 3] = right, upv, back, eye
    return m


def _color(c):
    if isinstance(c, str):
        c = c.lstrip("#")
        return np.array([int(c[i:i + 2], 16) for i in (0, 2, 4)], float)
    return np.array(c if c is not None else (163, 162, 165), float)


def _faces(part):
    """Local-space polygons (lists of 3-vectors) for one part."""
    sx, sy, sz = (np.asarray(part["sz"], float) / 2)
    shape = part.get("shape") or "Block"
    if shape == "Cylinder":
        n = 16
        r = min(sy, sz)
        ring = [(math.cos(2 * math.pi * i / n) * r, math.sin(2 * math.pi * i / n) * r) for i in range(n)]
        polys = [[np.array([sx, y, z]) for y, z in ring], [np.array([-sx, y, z]) for y, z in reversed(ring)]]
        for i in range(n):
            (y0, z0), (y1, z1) = ring[i], ring[(i + 1) % n]
            polys.append([np.array([-sx, y0, z0]), np.array([-sx, y1, z1]), np.array([sx, y1, z1]), np.array([sx, y0, z0])])
        return polys
    if shape == "Ball":
        r = min(sx, sy, sz)
        polys, la, lo = [], 8, 12
        for i in range(la):
            t0, t1 = math.pi * i / la - math.pi / 2, math.pi * (i + 1) / la - math.pi / 2
            for j in range(lo):
                p0, p1 = 2 * math.pi * j / lo, 2 * math.pi * (j + 1) / lo
                def pt(t, p):
                    return np.array([math.cos(t) * math.cos(p), math.sin(t), math.cos(t) * math.sin(p)]) * r
                polys.append([pt(t0, p0), pt(t1, p0), pt(t1, p1), pt(t0, p1)])
        return polys
    v = [np.array([x, y, z]) for x in (-sx, sx) for y in (-sy, sy) for z in (-sz, sz)]
    if shape == "Wedge":
        # Roblox wedge: slope rises from the front (-Z) bottom to the back (+Z) top
        A, B = np.array([-sx, -sy, -sz]), np.array([sx, -sy, -sz])
        C, D = np.array([-sx, -sy, sz]), np.array([sx, -sy, sz])
        E, F = np.array([-sx, sy, sz]), np.array([sx, sy, sz])
        return [[A, B, D, C], [C, D, F, E], [A, E, F, B], [A, C, E], [B, F, D]]
    idx = [(0, 1, 3, 2), (4, 6, 7, 5), (0, 4, 5, 1), (2, 3, 7, 6), (0, 2, 6, 4), (1, 5, 7, 3)]
    return [[v[i] for i in f] for f in idx]


def _clip_near(poly, near):
    """Sutherland-Hodgman against z = -near (keep z <= -near) in camera space."""
    out = []
    n = len(poly)
    for i in range(n):
        a, b = poly[i], poly[(i + 1) % n]
        ia, ib = a[2] <= -near, b[2] <= -near
        if ia:
            out.append(a)
        if ia != ib:
            t = (-near - a[2]) / (b[2] - a[2])
            out.append(a + (b - a) * t)
    return out


def render(parts, camera=None, fov=70.0, size=(960, 540), bg=(22, 22, 26), near=0.1, outline=True,
           ambient=0.42, ss=2):
    """Render `parts` from `camera` (4x4, Roblox camera CFrame; identity = origin looking down -Z).
    `fov` is VERTICAL degrees, like Camera.FieldOfView. Returns a PIL RGB image.

    A real depth buffer (perspective-correct 1/z per pixel), not a painter's sort: sorting faces by their
    average depth goes wrong as soon as a big face (a floor, an arm) sits next to small ones."""
    W, H = size[0] * ss, size[1] * ss
    cam = np.eye(4) if camera is None else cf_matrix(camera)
    inv = np.linalg.inv(cam)
    f = (H / 2) / math.tan(math.radians(fov) / 2)
    color = np.zeros((H, W, 3), float)
    color[:] = np.array(bg, float)
    zbuf = np.zeros((H, W), float)                 # 1/z of the nearest surface so far (0 = nothing)
    edge = np.zeros((H, W), bool)
    glass = []                                      # transparent faces, composited after the opaque pass
    for part in parts:
        M = inv @ cf_matrix(part["cf"])
        col = _color(part.get("color"))
        tr = float(part.get("tr", 0) or 0)
        if tr >= 0.98:
            continue
        for poly in _faces(part):
            pc = [M[:3, :3] @ p + M[:3, 3] for p in poly]
            nrm = np.cross(pc[1] - pc[0], pc[2] - pc[0])
            if np.linalg.norm(nrm) < 1e-12:
                continue
            nrm = nrm / np.linalg.norm(nrm)
            if nrm @ (-pc[0]) <= 0:
                continue
            cp = _clip_near(pc, near)
            if len(cp) < 3:
                continue
            wn = cam[:3, :3] @ nrm
            lit = ambient + (1 - ambient) * max(0.0, float(wn @ KEY))
            shade = np.clip(col * lit, 0, 255)
            scr = [(W / 2 + q[0] / -q[2] * f, H / 2 - q[1] / -q[2] * f, 1.0 / -q[2]) for q in cp]
            for k in range(1, len(scr) - 1):
                tri = (scr[0], scr[k], scr[k + 1])
                if tr > 0.02:
                    glass.append((tri, shade, tr))
                else:
                    _raster(tri, shade, color, zbuf, edge if outline else None, W, H)
    for tri, shade, tr in glass:
        _raster(tri, shade, color, zbuf, None, W, H, alpha=1 - tr, write_depth=False)
    if outline:
        # darken pixels on silhouette / crease boundaries for readability
        color[edge] *= 0.72
    img = Image.fromarray(np.clip(color, 0, 255).astype(np.uint8), "RGB")
    return img.resize(size, Image.LANCZOS)


def _raster(tri, shade, color, zbuf, edge, W, H, alpha=1.0, write_depth=True):
    (x0, y0, w0), (x1, y1, w1), (x2, y2, w2) = tri
    minx, maxx = max(int(math.floor(min(x0, x1, x2))), 0), min(int(math.ceil(max(x0, x1, x2))), W - 1)
    miny, maxy = max(int(math.floor(min(y0, y1, y2))), 0), min(int(math.ceil(max(y0, y1, y2))), H - 1)
    if minx > maxx or miny > maxy:
        return
    area = (x1 - x0) * (y2 - y0) - (x2 - x0) * (y1 - y0)
    if abs(area) < 1e-9:
        return
    ys, xs = np.mgrid[miny:maxy + 1, minx:maxx + 1]
    px, py = xs + 0.5, ys + 0.5
    b0 = ((x1 - px) * (y2 - py) - (x2 - px) * (y1 - py)) / area
    b1 = ((x2 - px) * (y0 - py) - (x0 - px) * (y2 - py)) / area
    b2 = 1 - b0 - b1
    inside = (b0 >= -1e-6) & (b1 >= -1e-6) & (b2 >= -1e-6)
    if not inside.any():
        return
    w = b0 * w0 + b1 * w1 + b2 * w2               # 1/z, linear in screen space
    region = zbuf[miny:maxy + 1, minx:maxx + 1]
    win = inside & (w > region * (1 + 1e-5))
    if not win.any():
        return
    c = color[miny:maxy + 1, minx:maxx + 1]
    if alpha >= 1:
        c[win] = shade
    else:
        c[win] = c[win] * (1 - alpha) + shade * alpha
    if write_depth:
        region[win] = w[win]
    if edge is not None:
        # pixels within ~1 px of this triangle's own edges become outline candidates
        e = inside & ((np.minimum(np.minimum(b0, b1), b2) * abs(area) /
                       max(1e-6, max(math.dist((x0, y0), (x1, y1)), math.dist((x1, y1), (x2, y2)),
                                     math.dist((x2, y2), (x0, y0))))) < 0.9)
        ed = edge[miny:maxy + 1, minx:maxx + 1]
        ed[win] = e[win]


# ---- an R6 body, for references and rigs
R6 = {
    "Head": ((2, 1, 1), (0, 1.5, 0)),
    "Torso": ((2, 2, 1), (0, 0, 0)),
    "Left Arm": ((1, 2, 1), (-1.5, 0, 0)),
    "Right Arm": ((1, 2, 1), (1.5, 0, 0)),
    "Left Leg": ((1, 2, 1), (-0.5, -2, 0)),
    "Right Leg": ((1, 2, 1), (0.5, -2, 0)),
}


def r6_reference(at=(0, 0, 0), color=(150, 150, 158)):
    """A standing 5-stud R6 dummy with its feet at `at`."""
    base = np.asarray(at, float) + np.array([0, 3, 0])
    return [{"sz": s, "cf": tf(base + np.array(o)), "color": color} for s, o in R6.values()]
