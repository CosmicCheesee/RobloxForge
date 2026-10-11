"""Offline rendering: part lists (orthographic multi-view, flat shaded) and top-down floor plans.

Part list format (shared with model_build / model_export / audit_parts):
  {"n": name, "sz": [x,y,z], "off": [x,y,z], "rot": [rx,ry,rz] degrees (R = Rx*Ry*Rz, like CFrame.Angles),
   "shape": Block|Cylinder|Ball|Wedge|CornerWedge, "color": [r,g,b] 0-255, "tr": transparency}
Cylinders run along local X, exactly like Roblox. Wedges slope from the top-back (+Z) edge down to
the bottom-front (-Z) edge, like a Roblox WedgePart.
"""
from __future__ import annotations

import io
import math

import numpy as np
from PIL import Image, ImageDraw, ImageFont

LIGHT = np.array([0.45, 0.8, -0.4])
LIGHT = LIGHT / np.linalg.norm(LIGHT)


def _rot(deg):
    rx, ry, rz = (math.radians(v) for v in deg)
    cx, sx, cy, sy, cz, sz = math.cos(rx), math.sin(rx), math.cos(ry), math.sin(ry), math.cos(rz), math.sin(rz)
    Rx = np.array([[1, 0, 0], [0, cx, -sx], [0, sx, cx]])
    Ry = np.array([[cy, 0, sy], [0, 1, 0], [-sy, 0, cy]])
    Rz = np.array([[cz, -sz, 0], [sz, cz, 0], [0, 0, 1]])
    return Rx @ Ry @ Rz


def _box_faces(h):
    x, y, z = h
    v = np.array([[sx * x, sy * y, sz * z] for sx in (-1, 1) for sy in (-1, 1) for sz in (-1, 1)])
    # index = (sx>0)*4 + (sy>0)*2 + (sz>0)
    quads = [(4, 6, 7, 5), (0, 1, 3, 2), (2, 3, 7, 6), (0, 4, 5, 1), (1, 5, 7, 3), (0, 2, 6, 4)]
    return [v[list(q)] for q in quads]


def _wedge_faces(h):
    x, y, z = h
    # bottom rectangle, top edge at back (+Z)
    b = [np.array(p) for p in ([-x, -y, -z], [x, -y, -z], [x, -y, z], [-x, -y, z])]
    t0, t1 = np.array([-x, y, z]), np.array([x, y, z])
    return [
        np.array([b[0], b[3], b[2], b[1]]),          # bottom
        np.array([b[3], t0, t1, b[2]]),              # back
        np.array([b[0], b[1], t1, t0]),              # slope
        np.array([b[0], t0, b[3]]),                  # left tri
        np.array([b[1], b[2], t1]),                  # right tri
    ]


def _cornerwedge_faces(h):
    x, y, z = h
    b = [np.array(p) for p in ([-x, -y, -z], [x, -y, -z], [x, -y, z], [-x, -y, z])]
    apex = np.array([x, y, z])
    return [np.array([b[0], b[3], b[2], b[1]]), np.array([b[0], b[1], apex]), np.array([b[1], b[2], apex]),
            np.array([b[2], b[3], apex]), np.array([b[3], b[0], apex])]


def _cyl_faces(h, seg=18):
    x, r = h[0], min(h[1], h[2])
    ring = [np.array([0.0, r * math.cos(2 * math.pi * i / seg), r * math.sin(2 * math.pi * i / seg)]) for i in range(seg)]
    faces = []
    for i in range(seg):
        a, b = ring[i], ring[(i + 1) % seg]
        faces.append(np.array([a + [-x, 0, 0], b + [-x, 0, 0], b + [x, 0, 0], a + [x, 0, 0]]))
    faces.append(np.array([p + [x, 0, 0] for p in ring]))
    faces.append(np.array([p + [-x, 0, 0] for p in reversed(ring)]))
    return faces


def _ball_faces(h, seg=12, rings=8):
    r = min(h)
    faces = []
    for j in range(rings):
        t0, t1 = math.pi * j / rings, math.pi * (j + 1) / rings
        for i in range(seg):
            p0, p1 = 2 * math.pi * i / seg, 2 * math.pi * (i + 1) / seg
            def pt(t, p):
                return np.array([r * math.sin(t) * math.cos(p), r * math.cos(t), r * math.sin(t) * math.sin(p)])
            faces.append(np.array([pt(t0, p0), pt(t0, p1), pt(t1, p1), pt(t1, p0)]))
    return faces


def part_polys(spec):
    """World-space (model-space) polygons with a colour per polygon."""
    polys = []
    for p in spec:
        if p.get("tr", 0) >= 0.99:
            continue
        h = np.array(p["sz"], float) / 2
        R = _rot(p.get("rot", [0, 0, 0]))
        off = np.array(p.get("off", [0, 0, 0]), float)
        shape = p.get("shape", "Block")
        if shape == "Cylinder":
            faces = _cyl_faces(h)
        elif shape == "Ball":
            faces = _ball_faces(h)
        elif shape == "Wedge":
            faces = _wedge_faces(h)
        elif shape == "CornerWedge":
            faces = _cornerwedge_faces(h)
        else:
            faces = _box_faces(h)
        col = np.array(p.get("color", [163, 162, 165]), float)
        for f in faces:
            polys.append(((R @ f.T).T + off, col, p.get("tr", 0)))
    return polys


VIEWS = {
    # name: (camera forward = direction the camera LOOKS, up)
    "front": (np.array([0, 0, 1.0]), np.array([0, 1.0, 0])),     # looks along +Z: sees the -Z (Front) face
    "back": (np.array([0, 0, -1.0]), np.array([0, 1.0, 0])),
    "right": (np.array([-1.0, 0, 0]), np.array([0, 1.0, 0])),
    "left": (np.array([1.0, 0, 0]), np.array([0, 1.0, 0])),
    "top": (np.array([0, -1.0, 0]), np.array([0, 0, -1.0])),
    "iso": (np.array([-1.0, -0.8, 1.0]), np.array([0, 1.0, 0])),
}


def _basis(fwd, up):
    f = fwd / np.linalg.norm(fwd)
    r = np.cross(f, up)
    r = r / np.linalg.norm(r)
    u = np.cross(r, f)
    return r, u, f


def render_parts(spec, views=("front", "right", "top", "iso"), size=420, outline=True):
    polys = part_polys(spec)
    if not polys:
        raise ValueError("nothing visible to render")
    allpts = np.vstack([p[0] for p in polys])
    centre = (allpts.min(0) + allpts.max(0)) / 2
    tiles = []
    try:
        font = ImageFont.truetype("arial.ttf", 15)
    except OSError:
        font = ImageFont.load_default()
    for name in views:
        fwd, up = VIEWS[name]
        r, u, f = _basis(fwd, up)
        proj = []
        for pts, col, tr in polys:
            rel = pts - centre
            xy = np.stack([rel @ r, rel @ u], 1)
            depth = (rel @ f).mean()
            # face normal (polygon winding is not guaranteed, so use the side facing the camera)
            n = np.cross(pts[1] - pts[0], pts[2] - pts[0])
            nn = np.linalg.norm(n)
            if nn < 1e-12:
                continue
            n = n / nn
            if n @ f > 0:
                n = -n
            shade = 0.45 + 0.55 * max(0.0, float(n @ LIGHT))
            proj.append((depth, xy, np.clip(col * shade, 0, 255), tr))
        proj.sort(key=lambda t: -t[0])  # far first
        span = np.vstack([p[1] for p in proj])
        lo, hi = span.min(0), span.max(0)
        scale = (size - 40) / max(hi[0] - lo[0], hi[1] - lo[1], 1e-6)
        mid = (lo + hi) / 2
        img = Image.new("RGB", (size, size), (34, 36, 40))
        d = ImageDraw.Draw(img, "RGBA")
        for _, xy, col, tr in proj:
            pts = [(size / 2 + (x - mid[0]) * scale, size / 2 - (y - mid[1]) * scale) for x, y in xy]
            fill = tuple(int(c) for c in col) + (int(255 * (1 - tr)),)
            d.polygon(pts, fill=fill, outline=(0, 0, 0, 90) if outline else None)
        d.text((8, 6), f"{name}   {1 / scale:.3f} studs/px", fill=(230, 230, 230), font=font)
        tiles.append(img)
    cols = 2 if len(tiles) > 1 else 1
    rows = math.ceil(len(tiles) / cols)
    sheet = Image.new("RGB", (cols * size, rows * size), (20, 20, 22))
    for i, t in enumerate(tiles):
        sheet.paste(t, ((i % cols) * size, (i // cols) * size))
    return _png(sheet)


def render_plan(data, size=900):
    """Top-down floor plan from the topdown.luau payload."""
    parts = data.get("parts", [])
    cx, cz = data["centre"]
    R = data["radius"]
    cut = data["cut"]
    scale = size / (2 * R)
    img = Image.new("RGB", (size, size), (10, 10, 12))
    d = ImageDraw.Draw(img, "RGBA")

    def px(x, z):
        return (size / 2 + (x - cx) * scale, size / 2 + (z - cz) * scale)

    for p in sorted(parts, key=lambda p: p["t"]):
        pts = [px(x, z) for x, z in p["xz"]]
        crosses = p["t"] >= cut  # stands through the cut: a wall, a column, tall furniture
        col = tuple(p["c"])
        if crosses:
            name = p["n"]
            if name in ("Wall", "Pillar", "Shell"):
                col = (235, 225, 190)
            d.polygon(pts, fill=col + (255,), outline=(0, 0, 0, 255))
        else:
            dim = tuple(int(c * 0.55) for c in col)
            d.polygon(pts, fill=dim + (255,))
    for pl in data.get("players", []):
        x, y = px(pl["p"][0], pl["p"][2])
        lx, lz = pl["look"]
        d.ellipse([x - 6, y - 6, x + 6, y + 6], fill=(230, 40, 40, 255))
        d.line([x, y, x + lx * 18, y + lz * 18], fill=(230, 40, 40, 255), width=3)
        d.text((x + 8, y - 8), pl["name"], fill=(255, 120, 120))
    try:
        font = ImageFont.truetype("arial.ttf", 14)
    except OSError:
        font = ImageFont.load_default()
    d.text((8, 6), f"plan  centre ({cx:.0f}, {cz:.0f})  r {R}  cut y {cut:.1f}  parts {len(parts)}  "
                   f"+X right, +Z down", fill=(230, 230, 230), font=font)
    # 20-stud scale bar
    d.line([10, size - 14, 10 + 20 * scale, size - 14], fill=(230, 230, 230), width=3)
    d.text((14 + 20 * scale, size - 22), "20 studs", fill=(230, 230, 230), font=font)
    return _png(img)


def contact_sheet(images, labels, cols=3, width=600):
    tiles = []
    for data, label in zip(images, labels):
        im = Image.open(io.BytesIO(data)).convert("RGB")
        im.thumbnail((width, width))
        d = ImageDraw.Draw(im)
        d.rectangle([0, 0, 8 + 8 * len(label), 20], fill=(0, 0, 0))
        d.text((4, 4), label, fill=(255, 255, 255))
        tiles.append(im)
    w = max(t.width for t in tiles)
    h = max(t.height for t in tiles)
    cols = min(cols, len(tiles))
    rows = math.ceil(len(tiles) / cols)
    sheet = Image.new("RGB", (cols * w, rows * h), (20, 20, 22))
    for i, t in enumerate(tiles):
        sheet.paste(t, ((i % cols) * w, (i // cols) * h))
    return _png(sheet, jpeg=True)


def _png(img, jpeg=False):
    buf = io.BytesIO()
    if jpeg:
        img.save(buf, "JPEG", quality=85)
    else:
        img.save(buf, "PNG", optimize=True)
    return buf.getvalue()
