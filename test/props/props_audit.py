"""Numeric visual/collision/in-hand audit for every holdable prop in a game's item catalogue (dumped from Studio).

Input: props.json, dumped from Studio (every def in Loot.byId / Loot.byTool with its part list, hold,
holdRot, gripAt, twoHand and draw tilt -- see the dump eval in the session log).

Per prop:
  AUDIT     z-fight / floating / hidden, using the roblox-visual-pass skill's own audit functions
  BOUNDS    parts poking outside the declared `sz` box (placement uses `sz`: a part past its floor
            face sinks into the floor, past its sides clips into the wall it was pushed against)
  PICKUP    how much of the visible silhouette the FIRST part covers -- it is the only queryable one,
            so a look at the rest of the object misses it
  HAND      at the resting hold: does the fist touch the item, how much of the item is buried in the
            forearm, how close the nearest point comes to the camera, how much of the screen it covers
"""
import importlib.util
import json
import math
import sys

import numpy as np

from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from robloxforge import audit_parts as ap  # noqa: E402  -- the same face/float audit the model tools use


def rotm(c):
    """CFrame components -> 3x3 (rows R00.., as GetComponents returns R00 R01 R02 R10 ...)."""
    if not c:
        return np.eye(3)
    return np.array(c[3:12], float).reshape(3, 3)


def cfm(c):
    m = np.eye(4)
    if c:
        m[:3, :3] = rotm(c)
        m[:3, 3] = c[0:3]
    return m


def angles(deg):
    x, y, z = [math.radians(v) for v in deg]
    return ap.rx(x) @ ap.ry(y) @ ap.rz(z)


def T(v):
    m = np.eye(4)
    m[:3, 3] = v
    return m


def R4(R):
    m = np.eye(4)
    m[:3, :3] = R
    return m


def parts_of(p):
    """(name, size, centre, shape, R) in the item's own space, exactly as buildItem places them."""
    out = []
    for s in p["parts"] or []:
        out.append((s["n"], np.array(s["sz"], float), np.array(s["off"], float), s.get("sh") or "Block", rotm(s.get("rot"))))
    if not out and p.get("sz"):
        out.append(("Body", np.array(p["sz"], float), np.zeros(3), p.get("shape") or "Block", np.eye(3)))
    return out


def corners(part):
    _, sz, c, shape, R = part
    h = sz / 2
    pts = []
    for sx in (-1, 1):
        for sy in (-1, 1):
            for sz_ in (-1, 1):
                pts.append(c + R @ (np.array([sx, sy, sz_]) * h))
    return np.array(pts)


def samples(part, n=5, step=None):
    """Points filling a part's volume (cylinder/ball respected), item space. With `step`, the density is
    per STUD rather than per part -- a fixed count per part under-samples big parts against small ones."""
    _, sz, c, shape, R = part
    if step:
        gs = [np.linspace(-0.5, 0.5, max(2, int(math.ceil(sz[i] / step)) + 1)) for i in range(3)]
    else:
        gs = [np.linspace(-0.5, 0.5, n)] * 3
    pts = []
    for a in gs[0]:
        for b in gs[1]:
            for d in gs[2]:
                loc = np.array([a, b, d])
                if shape == "Cylinder" and (loc[1] ** 2 + loc[2] ** 2) > 0.25:
                    continue
                if shape == "Ball" and (loc @ loc) > 0.25:
                    continue
                pts.append(c + R @ (loc * sz))
    return np.array(pts) if pts else np.array([c])


def inside_box(pts, centre, R, size, pad=0.0):
    local = (pts - centre) @ R          # R columns are the box axes
    return np.all(np.abs(local) <= size / 2 + pad, axis=1)


def silhouette_cover(parts, res=64):
    """Fraction of the three axis-aligned silhouettes covered by part 1."""
    big = max(float(np.max(p[1])) for p in parts)
    step = big / 48
    allp = np.vstack([samples(p, step=step) for p in parts])
    lo, hi = allp.min(0), allp.max(0)
    fr = []
    for ax in range(3):
        u, v = [a for a in range(3) if a != ax]
        span = np.maximum(hi - lo, 1e-6)
        def grid(pts):
            g = np.zeros((res, res), bool)
            iu = np.clip(((pts[:, u] - lo[u]) / span[u] * (res - 1)).astype(int), 0, res - 1)
            iv = np.clip(((pts[:, v] - lo[v]) / span[v] * (res - 1)).astype(int), 0, res - 1)
            g[iu, iv] = True
            return g
        whole = grid(allp)
        first = grid(samples(parts[0], step=step))
        if whole.sum():
            fr.append((first & whole).sum() / whole.sum())
    return min(fr) if fr else 1.0


# ---- the viewmodel (WeaponSelect): camera space, camera at origin looking down -Z
HOLD_R = T([1.62, -2.00, -2.24]) @ R4(angles([99, 15, -8]))
HOLD2_R = T([1.48, -2.06, -2.56]) @ R4(angles([103, 22, -12]))
HOLD2_L = T([-1.48, -2.06, -2.56]) @ R4(angles([103, -22, 12]))
ARM = np.array([1.0, 2.0, 1.0])
FOV_V = math.radians(70)
ASPECT = 16 / 9


def item_cf(p):
    """Item CFrame in camera space at the resting hold: handRest * grip * (-gripAt), and since the hand
    IS at its rest pose, grip collapses to hold * holdRot * tilt (see WeaponSelect's grip note)."""
    m = cfm(p["hold"])
    if p.get("holdRot"):
        m = m @ R4(rotm(p["holdRot"]))
    if p.get("tilt"):
        m = m @ R4(angles(p["tilt"]))
    if p.get("gripAt"):
        m = m @ T(-np.array(p["gripAt"]))
    return m


def hand_checks(p, parts):
    if not p.get("hold"):
        return None
    M = item_cf(p)
    pts = np.vstack([samples(q, 6) for q in parts])
    cam = (M[:3, :3] @ pts.T).T + M[:3, 3]
    arms = [HOLD2_R, HOLD2_L] if p.get("twoHand") else [HOLD_R]
    res = {}
    # the fist: the far end of the arm block (local -Y is the hand end on an R6 arm)
    fist_gap = []
    buried = 0
    for A in arms:
        Rm, c = A[:3, :3], A[:3, 3]
        fist = c + Rm @ np.array([0, -0.85, 0])
        d = np.linalg.norm(cam - fist, axis=1).min()
        fist_gap.append(d)
        # forearm = the upper 70% of the arm, away from the fist
        fore_c = c + Rm @ np.array([0, 0.3, 0])
        buried += inside_box(cam, fore_c, Rm, np.array([1.0, 1.4, 1.0])).sum()
    res["fist_gap"] = fist_gap[0]
    res["left_gap"] = fist_gap[1] if len(fist_gap) > 1 else None
    if p.get("twoHand") and max(p.get("sz") or [0]) >= 2.4:
        # emulate WeaponSelect.leftGripPose: the nearest corner / edge-mid / face-centre of any part to the
        # resting left fist, and the arm solved onto it from the same shoulder
        L = HOLD2_L
        fist = L[:3, 3] - L[:3, 1]
        shoulder = L[:3, 3] + L[:3, 1]
        best, bd = None, 1e9
        for q in parts:
            _, qsz, qc, _, qR = q
            for a in (-1, 0, 1):
                for b in (-1, 0, 1):
                    for c in (-1, 0, 1):
                        if a == b == c == 0:
                            continue
                        loc = qc + qR @ (np.array([a, b, c]) * qsz / 2)
                        w = M[:3, :3] @ loc + M[:3, 3]
                        d = np.linalg.norm(w - fist)
                        if d < bd:
                            best, bd = w, d
        up = shoulder - best
        up = up / np.linalg.norm(up)
        right = np.cross([0, 1, 0], up)
        right = right / (np.linalg.norm(right) + 1e-9)
        fwd = np.cross(right, up)
        A = np.eye(4)
        A[:3, 0], A[:3, 1], A[:3, 2], A[:3, 3] = right, up, fwd, best + up
        # the occlusion guard (WeaponSelect.leftGripPose): rays from the eye to every part corner against
        # the solved arm's box; past a third hidden, the shared pose is kept
        hid, n = 0, 0
        Ainv = np.linalg.inv(A)
        for q in parts:
            for c in corners(q):
                w = M[:3, :3] @ c + M[:3, 3]
                o = Ainv[:3, 3]
                dv = Ainv[:3, :3] @ w
                t0, t1 = 0.0, 1.0
                for ax, lim in enumerate((0.5, 1.0, 0.5)):
                    if abs(dv[ax]) < 1e-9:
                        if abs(o[ax]) > lim:
                            t0 = 2
                    else:
                        a, b = (-lim - o[ax]) / dv[ax], (lim - o[ax]) / dv[ax]
                        a, b = min(a, b), max(a, b)
                        t0, t1 = max(t0, a), min(t1, b)
                n += 1
                if t0 <= t1 and t0 < 0.97:
                    hid += 1
        res["left_hidden"] = hid / max(n, 1)
        if res["left_hidden"] > 0.34:
            res["left_solved"] = HOLD2_L              # kept the shared pose
        else:
            res["left_solved"] = A
            fore_c = A[:3, 3] + A[:3, :3] @ np.array([0, 0.3, 0])
            res["left_buried"] = inside_box(cam, fore_c, A[:3, :3], np.array([1.0, 1.4, 1.0])).mean()
            res["left_gap"] = 0.0
    res["buried"] = buried / len(cam)
    res["near"] = float((-cam[:, 2]).min())
    # hidden inside the hand: any part of the item inside the whole right arm block
    res["in_hand"] = inside_box(cam, arms[0][:3, 3], arms[0][:3, :3], ARM).mean()
    # screen coverage of the bounding rectangle of the projected points
    z = -cam[:, 2]
    ok = z > 0.05
    if ok.any():
        t = math.tan(FOV_V / 2)
        sx = cam[ok, 0] / (z[ok] * t * ASPECT)
        sy = cam[ok, 1] / (z[ok] * t)
        w = (np.clip(sx.max(), -1, 1) - np.clip(sx.min(), -1, 1)) / 2
        h = (np.clip(sy.max(), -1, 1) - np.clip(sy.min(), -1, 1)) / 2
        res["screen"] = w * h
        res["offscreen"] = float(np.mean((np.abs(sx) > 1) | (np.abs(sy) > 1)))
    return res


def main(path, only=None):
    props = json.load(open(path, encoding="utf-8"))
    report, worst = [], 0
    for p in sorted(props, key=lambda x: x["id"]):
        if only and p["id"] not in only:
            continue
        parts = parts_of(p)
        if not parts:
            report.append(f"[--] {p['id']:<12} no geometry (not a physical prop)")
            continue
        lines = []
        # AUDIT -- the skill's own checks, captured
        import io, contextlib
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            nbad = ap.audit(parts, 0.006)
        for ln in buf.getvalue().splitlines()[1:]:
            lines.append("AUDIT  " + ln.strip())
        # PLACEMENT -- through the true extents when the def carries them (LootDefs, WHERE A THING ACTUALLY
        # ENDS): the lowest point must land on the floor, and the clearance cube must hold the object
        allc = np.vstack([corners(q) for q in parts])
        if p.get("restY") is not None:
            low = allc[:, 1].min() + p["restY"]          # 0 = touching the floor
            if low < -0.03:
                lines.append(f"FLOOR  lowest point {-low:.2f} below the floor at rest")
            if low > 0.03:
                lines.append(f"HOVER  lowest point {low:.2f} above the floor at rest")
            reach = max(np.abs(allc[:, 0]).max(), np.abs(allc[:, 2]).max())
            if p.get("clear") and reach > p["clear"] / 2 + 1e-6:
                lines.append(f"CLEAR  reaches {reach:.2f} sideways, past the clearance cube ({p['clear']:.2f})")
        elif p.get("sz"):
            half = np.array(p["sz"]) / 2
            allc = np.vstack([corners(q) for q in parts])
            over = np.maximum(np.abs(allc) - half, 0).max(0)
            below = max(0.0, -allc[:, 1].min() - half[1])
            if below > 0.03:
                lines.append(f"FLOOR  parts reach {below:.2f} below the declared bottom -- sinks into the floor")
            side = max(over[0], over[2])
            if side > 0.05:
                lines.append(f"BOUNDS parts reach {side:.2f} past the declared sides (sz {p['sz']})")
            if over[1] > 0.05 and below <= 0.03:
                lines.append(f"BOUNDS parts reach {over[1]:.2f} above the declared top")
        # PICKUP -- LootClient targets the PrimaryPart's CENTRE inside a look-cone (then a line-of-sight
        # ray to it), so what matters is that centre sitting near the middle of what you see
        allp = np.vstack([corners(q) for q in parts])
        mid = (allp.min(0) + allp.max(0)) / 2
        span = float(np.max(allp.max(0) - allp.min(0)))
        off = float(np.linalg.norm(parts[0][2] - mid))
        cov = 1 - off / max(span, 1e-6)
        if off > 0.35 * span and off > 0.4:
            lines.append(f"PICKUP the aim point ({parts[0][0]}) is {off:.2f} studs off the object's middle")
        # HAND
        h = hand_checks(p, parts)
        if h:
            if h["fist_gap"] > 0.6:
                lines.append(f"HAND   right fist is {h['fist_gap']:.2f} studs from the item -- not holding it")
            if h.get("left_buried", 0) > 0.12:
                lines.append(f"HAND   the solved left arm passes through {h['left_buried']:.0%} of the item")
            if h.get("left_gap") is not None and h["left_gap"] > 0.6:
                lines.append(f"HAND   two-handed, but the LEFT fist is {h['left_gap']:.2f} studs from the item")
            if h["buried"] > 0.12:
                lines.append(f"HAND   {h['buried']:.0%} of the item is inside the forearm")
            if h["in_hand"] > 0.45:
                lines.append(f"HAND   {h['in_hand']:.0%} of the item is inside the hand -- hidden")
            if h["near"] < 0.55:
                lines.append(f"HAND   nearest point {h['near']:.2f} studs from the lens -- clips / fills the view")
            if h.get("offscreen", 0) > 0.5:
                lines.append(f"HAND   {h['offscreen']:.0%} of the item is off screen at rest")
        tag = "OK " if not lines else "FIX"
        info = ""
        if h:
            lg = f"/{h['left_gap']:.2f}" if h.get('left_gap') is not None else ""
            if h.get("left_hidden") is not None:
                lg += f" (left {'kept' if h['left_hidden'] > 0.34 else 'on it'}, hides {h['left_hidden']:.0%})"
            info = f"fist {h['fist_gap']:.2f}{lg}  arm {h['buried']:.0%}  near {h['near']:.2f}  screen {h.get('screen', 0):.0%}"
        report.append(f"[{tag}] {p['id']:<12} {len(parts):>2} parts  aim {cov:.0%}  {info}")
        for ln in lines:
            report.append("        " + ln)
        worst += len(lines)
    print("\n".join(report))
    print(f"\n{len([r for r in report if r.startswith('[FIX]')])} of {len([r for r in report if r.startswith('[')])} props have findings, {worst} findings")


if __name__ == "__main__":
    main(sys.argv[1], set(sys.argv[2:]) or None)
