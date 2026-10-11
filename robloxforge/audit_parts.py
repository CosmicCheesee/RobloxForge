"""Face-plane (z-fight) and connectivity audit for a part list that has not been built yet.

Usage:  python audit_parts.py spec.json  [--gap 0.006]

spec.json is a list of parts in the model's own space:
  [{"n": "Frame", "sz": [0.09, 0.2, 0.34], "off": [0, 0, 0.02], "shape": "Block", "rot": [0, 0, 0]}, ...]
`shape` is Block (default), Cylinder (axis = local X, like Roblox) or Ball. `rot` is degrees in the
order of CFrame.Angles(rx, ry, rz), i.e. R = Rx * Ry * Rz, applied about the part's own centre.
Same rules as audit.luau: same-facing flat faces within --gap that overlap in-plane are reported, and
parts that touch nothing else are reported as floating groups.
"""
import itertools, json, math, sys

import numpy as np


def rx(a): c, s = math.cos(a), math.sin(a); return np.array([[1, 0, 0], [0, c, -s], [0, s, c]])
def ry(a): c, s = math.cos(a), math.sin(a); return np.array([[c, 0, s], [0, 1, 0], [-s, 0, c]])
def rz(a): c, s = math.cos(a), math.sin(a); return np.array([[c, -s, 0], [s, c, 0], [0, 0, 1]])


def load(path):
    parts = []
    for p in json.load(open(path, encoding="utf-8")):
        r = [math.radians(v) for v in p.get("rot", [0, 0, 0])]
        R = rx(r[0]) @ ry(r[1]) @ rz(r[2])
        parts.append((p["n"], np.array(p["sz"], float), np.array(p["off"], float), p.get("shape", "Block"), R))
    return parts


def faces(p):
    n, sz, off, shape, R = p
    if shape == "Ball":
        return []
    h = sz / 2
    out = []
    for ax in range(3):
        if shape == "Cylinder" and ax != 0:
            continue
        for sg in (1, -1):
            nrm = R[:, ax] * sg
            u, v = [a for a in range(3) if a != ax]
            out.append((nrm, off + nrm * h[ax], R[:, u] * h[u], R[:, v] * h[v]))
    return out


def inside(pt, f):
    _, c, U, V = f
    d = pt - c
    return abs(d @ U) <= U @ U + 1e-9 and abs(d @ V) <= V @ V + 1e-9


def overlap(a, b, N=9):
    _, c, U, V = a
    return sum(inside(c + U * (i / (N - 1) * 2 - 1) * 0.98 + V * (j / (N - 1) * 2 - 1) * 0.98, b)
               for i in range(N) for j in range(N))


def touching(a, b, tol=0.002):
    Ra, Rb = a[4], b[4]
    ha, hb = a[1] / 2, b[1] / 2
    axes = [Ra[:, i] for i in range(3)] + [Rb[:, i] for i in range(3)]
    for i in range(3):
        for j in range(3):
            c = np.cross(Ra[:, i], Rb[:, j])
            if np.linalg.norm(c) > 1e-6:
                axes.append(c / np.linalg.norm(c))
    d = b[2] - a[2]
    for L in axes:
        ra = sum(abs(L @ Ra[:, i]) * ha[i] for i in range(3))
        rb = sum(abs(L @ Rb[:, i]) * hb[i] for i in range(3))
        if abs(d @ L) > ra + rb + tol:
            return False
    return True


def audit(parts, gap):
    bad = []
    fs = [(p[0], f) for p in parts for f in faces(p)]
    for (na, fa), (nb, fb) in itertools.combinations(fs, 2):
        if na == nb or fa[0] @ fb[0] < 0.999:
            continue
        dist = abs((fb[1] - fa[1]) @ fa[0])
        if dist < gap:
            k = max(overlap(fa, fb), overlap(fb, fa))
            if k:
                bad.append(f"ZFIGHT  {na} / {nb}: {dist:.4f} apart, overlap {k}/81")
    par = list(range(len(parts)))
    def find(i):
        while par[i] != i:
            i = par[i]
        return i
    for i, j in itertools.combinations(range(len(parts)), 2):
        if touching(parts[i], parts[j]):
            par[find(i)] = find(j)
    groups = {}
    for i, p in enumerate(parts):
        groups.setdefault(find(i), []).append(p[0])
    gl = sorted(groups.values(), key=len, reverse=True)
    for g in gl[1:]:
        bad.append("FLOAT   not attached to the main body: " + ", ".join(g))
    print(f"{len(parts)} parts, {len(bad)} problem(s)")
    for b in bad:
        print("  " + b)
    return len(bad)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(2)
    g = float(sys.argv[sys.argv.index("--gap") + 1]) if "--gap" in sys.argv else 0.006
    sys.exit(1 if audit(load(sys.argv[1]), g) else 0)
