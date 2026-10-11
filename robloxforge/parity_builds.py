"""Parity: a local BUILD LIBRARY (6xvl's export_build / create_build / generate_build / import_build /
list_library / get_build / import_scene), on top of RobloxForge's own model_build / export_parts.

A build is a compact JSON file under library/<style>/<id>.json:
  {id, style, palette: [{color: "#rrggbb", mat: "Wood"}], parts: [[ox,oy,oz, sx,sy,sz, rx,ry,rz, palette, shape]],
   bounds: [sx,sy,sz], generator?: {code, seed}}
Offsets are in the build's own space (pivot at the bottom centre); rotations in degrees (CFrame.Angles order).
Every import goes through model_build, so it is validated in Python first and audited after.
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import tempfile
from pathlib import Path

from .parity import ARR, N, O, PATH, S
from .server import PEER, STUDIO, text, tool
from .studio import ForgeError

LIB = Path(os.environ.get("FORGE_LIBRARY", Path(__file__).resolve().parent.parent / "library"))
SHAPES = ["Block", "Cylinder", "Ball", "Wedge", "CornerWedge"]


def _safe(s, what):
    if not isinstance(s, str) or not re.fullmatch(r"[A-Za-z0-9_\-]+", s):
        raise ForgeError(f"{what} must be letters, digits, _ or - (got {s!r})")
    return s


def _path(build_id):
    if "/" in build_id:
        style, name = build_id.split("/", 1)
    else:
        style, name = "misc", build_id
    return LIB / _safe(style, "style") / f"{_safe(name, 'id')}.json", style, name


def compact(parts):
    """Part list -> (palette, rows, bounds)."""
    palette, rows = [], []
    lo, hi = [1e9] * 3, [-1e9] * 3
    for p in parts:
        key = {"color": p.get("color", "#a3a2a5"), "mat": p.get("mat", "SmoothPlastic")}
        if key not in palette:
            palette.append(key)
        off, sz, rot = p.get("off", [0, 0, 0]), p["sz"], p.get("rot", [0, 0, 0])
        rows.append([round(v, 4) for v in (*off, *sz, *rot)] + [palette.index(key), SHAPES.index(p.get("shape", "Block"))
                                                                 if p.get("shape", "Block") in SHAPES else 0])
        for k in range(3):
            lo[k] = min(lo[k], off[k] - sz[k] / 2)
            hi[k] = max(hi[k], off[k] + sz[k] / 2)
    return palette, rows, [round(hi[k] - lo[k], 3) for k in range(3)]


def expand(build):
    """Build JSON -> RobloxForge part list."""
    pal = build.get("palette") or [{"color": "#a3a2a5", "mat": "SmoothPlastic"}]
    out = []
    for i, r in enumerate(build.get("parts") or []):
        if len(r) < 6:
            raise ForgeError(f"part {i}: needs at least [ox,oy,oz, sx,sy,sz]")
        rot = r[6:9] if len(r) >= 9 else [0, 0, 0]
        pi = int(r[9]) if len(r) >= 10 else 0
        sh = SHAPES[int(r[10])] if len(r) >= 11 and 0 <= int(r[10]) < len(SHAPES) else "Block"
        c = pal[pi] if 0 <= pi < len(pal) else pal[0]
        if isinstance(c, str):
            c = {"color": c}
        out.append({"n": f"P{i + 1}", "off": list(r[0:3]), "sz": list(r[3:6]), "rot": list(rot), "shape": sh,
                    "color": c.get("color", "#a3a2a5"), "mat": c.get("mat", "SmoothPlastic")})
    if not out:
        raise ForgeError("the build has no parts")
    return out


def _save(build):
    f, style, name = _path(build["id"])
    build["style"] = build.get("style") or style
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_text(json.dumps(build, separators=(",", ":")), encoding="utf-8")
    return f


def _load(ref):
    if isinstance(ref, dict):
        return ref
    f, _, _ = _path(ref)
    if not f.is_file():
        raise ForgeError(f"no build {ref!r} in {LIB}")
    return json.loads(f.read_text(encoding="utf-8"))


@tool("export_build", "Export a Model into the compact build format and save it in the local build library "
      "(library/<style>/<id>.json) for re-use, scenes and diffs.",
      {"instancePath": PATH, "outputId": S, "style": S, "peer": PEER}, ["instancePath", "outputId"], read_only=True)
async def export_build(a):
    res = await STUDIO.run("export_parts", {"path": a["instancePath"]}, a.get("peer", "edit"))
    palette, rows, bounds = compact(res["parts"])
    bid = a["outputId"] if "/" in a["outputId"] else f"{a.get('style', 'misc')}/{a['outputId']}"
    f = _save({"id": bid, "style": a.get("style"), "palette": palette, "parts": rows, "bounds": bounds,
               "source": a["instancePath"]})
    return [text({"id": bid, "file": str(f), "parts": len(rows), "palette": len(palette), "bounds": bounds})]


@tool("create_build", "Create a build from compact rows and save it to the library: palette = [{color, mat}], parts = "
      "[[ox,oy,oz, sx,sy,sz, rx,ry,rz, paletteIndex, shapeIndex(0 Block,1 Cylinder,2 Ball,3 Wedge,4 CornerWedge)]].",
      {"id": S, "style": S, "palette": ARR, "parts": ARR, "bounds": ARR}, ["id", "parts"])
async def create_build(a):
    build = {"id": a["id"] if "/" in a["id"] else f"{a.get('style', 'misc')}/{a['id']}", "style": a.get("style"),
             "palette": a.get("palette") or [], "parts": a["parts"]}
    parts = expand(build)
    build["bounds"] = a.get("bounds") or compact(parts)[2]
    f = _save(build)
    return [text({"id": build["id"], "file": str(f), "parts": len(parts)})]


_JS = r"""
const SEED = %SEED%;
let s = SEED >>> 0 || 1;
function rng() { s ^= s << 13; s >>>= 0; s ^= s >>> 17; s ^= s << 5; s >>>= 0; return s / 4294967296; }
const parts = [];
function part(pos, size, pal = 0, rot = [0, 0, 0], shape = 0) {
  if (!Array.isArray(pos) || !Array.isArray(size)) throw new Error('part(pos, size, pal, rot, shape)');
  parts.push([...pos, ...size, ...rot, pal, shape]);
}
function box(x, y, z, sx, sy, sz, pal = 0) { part([x, y, z], [sx, sy, sz], pal); }
(function () {
%CODE%
})();
process.stdout.write(JSON.stringify(parts));
"""


@tool("generate_build", "Procedurally generate a build with JavaScript and save it to the library. The code gets "
      "part(pos, size, paletteIndex, rot=[rx,ry,rz], shape), box(x,y,z, sx,sy,sz, pal) and a seeded rng(); loops "
      "and maths are plain JS. Runs in a separate Node process with a 20 s limit. Generate the whole thing in one call.",
      {"id": S, "style": S, "palette": ARR, "code": S, "seed": N}, ["id", "code"])
async def generate_build(a):
    src = _JS.replace("%SEED%", str(int(a.get("seed", 1)))).replace("%CODE%", a["code"])
    with tempfile.TemporaryDirectory() as d:
        f = Path(d) / "gen.cjs"
        f.write_text(src, encoding="utf-8")
        try:
            r = subprocess.run(["node", str(f)], capture_output=True, text=True, timeout=20, cwd=d)
        except subprocess.TimeoutExpired:
            raise ForgeError("the generator ran past 20 s")
    if r.returncode != 0:
        raise ForgeError("generator failed: " + (r.stderr or r.stdout)[-800:])
    rows = json.loads(r.stdout or "[]")
    build = {"id": a["id"] if "/" in a["id"] else f"{a.get('style', 'misc')}/{a['id']}", "style": a.get("style"),
             "palette": a.get("palette") or [], "parts": rows, "generator": {"code": a["code"], "seed": a.get("seed", 1)}}
    parts = expand(build)
    build["bounds"] = compact(parts)[2]
    out = _save(build)
    return [text({"id": build["id"], "file": str(out), "parts": len(rows), "bounds": build["bounds"]})]


@tool("import_build", "Build a library build (by id, or inline build data) in Studio through model_build "
      "(validated first, audited after).", {"buildData": {"description": "library id 'style/name' or a build object"},
      "targetPath": PATH, "position": ARR, "name": S, "peer": PEER}, ["buildData"])
async def import_build(a):
    build = _load(a["buildData"])
    parts = expand(build)
    from .server import NATIVE
    handler = NATIVE["model_build"][1]
    return await handler({"parts": parts, "name": a.get("name") or str(build.get("id", "Build")).split("/")[-1],
                          "parent": a.get("targetPath", "Workspace"), "origin": a.get("position", [0, 0, 0]),
                          "peer": a.get("peer", "edit")})


@tool("list_library", "Builds in the local library: id, style, part count, bounds.", {"style": S}, read_only=True)
async def list_library(a):
    out = []
    if LIB.exists():
        for f in sorted(LIB.glob("*/*.json")):
            if a.get("style") and f.parent.name != a["style"]:
                continue
            try:
                b = json.loads(f.read_text(encoding="utf-8"))
            except ValueError:
                continue
            out.append({"id": f"{f.parent.name}/{f.stem}", "parts": len(b.get("parts") or []), "bounds": b.get("bounds"),
                        "generated": "generator" in b})
    return [text({"library": str(LIB), "builds": out})]


@tool("get_build", "One build from the library: metadata, palette, rows, and its generator code if it has one.",
      {"id": S}, ["id"], read_only=True)
async def get_build(a):
    return [text(_load(a["id"]))]


@tool("import_scene", "Place several library builds in one call: sceneData = {models: [{id, position [x,y,z], "
      "name?}]}, under targetPath.", {"sceneData": O, "targetPath": PATH, "peer": PEER}, ["sceneData"])
async def import_scene(a):
    placed, failed = [], []
    for m in (a["sceneData"] or {}).get("models", []):
        try:
            res = await import_build({"buildData": m["id"], "targetPath": a.get("targetPath", "Workspace"),
                                      "position": m.get("position", [0, 0, 0]), "name": m.get("name"), "peer": a.get("peer", "edit")})
            placed.append({"id": m["id"], "result": json.loads(res[0].text) if res and hasattr(res[0], "text") else None})
        except (ForgeError, KeyError) as e:
            failed.append({"model": m, "error": str(e)})
    return [text({"placed": len(placed), "failed": failed, "details": placed})]
