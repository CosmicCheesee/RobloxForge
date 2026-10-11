"""Compute the smallest data edits that clear the skill audit for each prop, then apply them to the
LootDefs source. Z-fight: the LATER part of the pair (decoration comes after the body) grows by 2*STEP
along the axis of the coplanar face, so its face steps out STEP past the other. Float: the part is slid
toward its nearest neighbour until it touches, then embedded EMBED further. Iterates per prop until the
audit is clean (or gives up after 12 rounds and says so)."""
import io
import contextlib
import json
import re
import sys

import numpy as np

HERE = __import__("pathlib").Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import importlib.util  # noqa: E402
spec = importlib.util.spec_from_file_location("pa", str(HERE / "props_audit.py"))
pa = importlib.util.module_from_spec(spec)
spec.loader.exec_module(pa)
ap = pa.ap

STEP, EMBED = 0.008, 0.01
# the catalogue source to patch: FORGE_LOOTDEFS, or "lootdefs" in forge.local.json
_cfg = HERE.parents[1] / "forge.local.json"
LOOTDEFS = __import__("os").environ.get("FORGE_LOOTDEFS") or (json.loads(_cfg.read_text()).get("lootdefs") if _cfg.is_file() else "LootDefs.lua")


def zfights(parts):
    out = []
    fs = [(i, p[0], f, ax) for i, p in enumerate(parts) for ax, f in enumerate(ap.faces(p))]
    for a in range(len(fs)):
        for b in range(a + 1, len(fs)):
            ia, na, fa, _ = fs[a]
            ib, nb, fb, fbi = fs[b]
            if ia == ib or fa[0] @ fb[0] < 0.999:
                continue
            if abs((fb[1] - fa[1]) @ fa[0]) < 0.006 and max(ap.overlap(fa, fb), ap.overlap(fb, fa)):
                out.append((ia, ib, fbi))
    return out


def face_axis(part, face_index):
    """faces() emits 2 faces per axis in axis order (cylinders: only axis 0)."""
    if part[3] == "Cylinder":
        return 0
    return face_index // 2


def floats(parts):
    par = list(range(len(parts)))
    def find(i):
        while par[i] != i:
            i = par[i]
        return i
    for i in range(len(parts)):
        for j in range(i + 1, len(parts)):
            if ap.touching(parts[i], parts[j]):
                par[find(i)] = find(j)
    groups = {}
    for i in range(len(parts)):
        groups.setdefault(find(i), []).append(i)
    gl = sorted(groups.values(), key=len, reverse=True)
    return gl[0], [i for g in gl[1:] for i in g]


def fix(p):
    parts = [list(q) for q in pa.parts_of(p)]
    edits = {}
    for _ in range(12):
        tup = [tuple(q) for q in parts]
        zs = zfights(tup)
        main, fl = floats(tup)
        if not zs and not fl:
            return edits, True
        grown = set()
        for ia, ib, fbi in zs:
            later = max(ia, ib)
            # the face index belongs to ib's face list; if the later part is ia, recompute its axis from
            # the shared normal instead
            q = parts[later]
            if later == ib:
                ax = face_axis(q, fbi)
            else:
                nrm = ap.faces(tuple(parts[ib]))[fbi][0]
                ax = int(np.argmax(np.abs(q[4].T @ nrm)))
            if (later, ax) in grown:
                continue                  # once per part per axis per round: both faces of a pair report
            grown.add((later, ax))
            sz = q[1].copy()
            sz[ax] += 2 * STEP
            q[1] = sz
            edits.setdefault(q[0], {})["sz"] = sz
        for i in fl:
            q = parts[i]
            others = [parts[k] for k in main]
            near = min(others, key=lambda o: np.linalg.norm(o[2] - q[2]))
            d = near[2] - q[2]
            u = d / (np.linalg.norm(d) + 1e-9)
            moved = 0.0
            while not ap.touching(tuple(q), tuple(near)) and moved < 2.0:
                q[2] = q[2] + u * 0.004
                moved += 0.004
            q[2] = q[2] + u * EMBED
            edits.setdefault(q[0], {})["off"] = q[2].copy()
    return edits, False


def fmt(v):
    return "V(" + ", ".join(f"{x:.3f}".rstrip("0").rstrip(".") if abs(x) > 1e-9 else "0" for x in v) + ")"


def apply(src, pid, name, ed):
    """Edit the P("name", V(size), V(off), ...) line inside the prop's PARTS block."""
    m = re.search(r"(^\t" + re.escape(pid) + r" = \{$|^L\.PARTS\." + re.escape(pid) + r" = \{$)", src, re.M)
    if not m:
        return src, False
    start = m.end()
    end = src.find("\n}", start) if m.group(0).startswith("L.PARTS") else src.find("\n\t},", start)
    block = src[start:end]
    pat = re.compile(r'P\("' + re.escape(name) + r'",\s*(V\([^)]*\)),\s*(V\([^)]*\))')
    mm = pat.search(block)
    if not mm:
        return src, False
    new = mm.group(0)
    if "sz" in ed:
        new = new.replace(mm.group(1), fmt(ed["sz"]), 1)
    if "off" in ed:
        new = new[:new.rfind(mm.group(2))] + fmt(ed["off"]) + new[new.rfind(mm.group(2)) + len(mm.group(2)):]
    block = block[:mm.start()] + new + block[mm.end():]
    return src[:start] + block + src[end:], True


if __name__ == "__main__":
    props = json.load(open(sys.argv[1], encoding="utf-8"))
    write = "--write" in sys.argv
    src = open(LOOTDEFS, encoding="utf-8", newline="").read() if write else None
    for p in sorted(props, key=lambda x: x["id"]):
        if not p.get("parts"):
            continue
        edits, clean = fix(p)
        if not edits:
            continue
        print(f"{p['id']}: {'clean' if clean else 'NOT CLEAN'}")
        for name, ed in edits.items():
            desc = ", ".join(f"{k} -> {fmt(v)}" for k, v in ed.items())
            ok = ""
            if write:
                src, done = apply(src, p["id"], name, ed)
                ok = "  [applied]" if done else "  [NOT FOUND IN SOURCE]"
            print(f"   {name}: {desc}{ok}")
    if write:
        open(LOOTDEFS, "w", encoding="utf-8", newline="").write(src)
