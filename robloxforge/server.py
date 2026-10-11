"""RobloxForge: one MCP server for building, scripting, seeing and measuring a Roblox place.

  * every robloxstudio-mcp tool, re-exported unchanged (Studio control, playtests, evals, screenshots,
    input, profilers, assets, docs) -- see studio.py for why it is a child rather than a fork;
  * modelling:  model_build, model_export, model_audit, model_seat, parts_audit
  * visual aid: model_shots, parts_render, map_plan
  * scripting:  repo_lint, luau_check, repo_drift, rojo_status, notes_search
  * measuring:  perf_snapshot, perf_glide, profile_summary, game_selftest
  * forge_status
"""
from __future__ import annotations

import asyncio
import base64
import contextlib
import io
import json
import math
import os
import re
import socket
import subprocess
import sys
import tempfile
import zlib
from contextlib import asynccontextmanager
from pathlib import Path

import mcp_types as types
import numpy as np
from mcp import Client
from mcp.server import Server
from mcp.server.stdio import stdio_server

from . import audit_parts, render
from .studio import ForgeError, Studio, child_params, template

# Machine-specific settings: environment variables first, then forge.local.json next to server.py (git-ignored),
# then generic defaults (tools on PATH, the current directory as the game repo).
_LOCAL = Path(__file__).resolve().parent.parent / "forge.local.json"
_CFG = json.loads(_LOCAL.read_text(encoding="utf-8")) if _LOCAL.is_file() else {}


def _setting(env, key, default):
    return os.environ.get(env) or _CFG.get(key) or default


REPO = Path(_setting("FORGE_REPO", "repo", "."))
SELENE = _setting("FORGE_SELENE", "selene", "selene")
ROJO = _setting("FORGE_ROJO", "rojo", "rojo")
ROJO_PORT = int(_setting("FORGE_ROJO_PORT", "rojo_port", "34872"))

STUDIO = Studio()
NATIVE: dict[str, tuple[types.Tool, callable]] = {}


# ---------------------------------------------------------------- registry helpers
def tool(name, description, props=None, required=None, read_only=False, destructive=False):
    def deco(fn):
        schema = {"type": "object", "properties": props or {}}
        if required:
            schema["required"] = required
        NATIVE[name] = (types.Tool(
            name=name, description=description, input_schema=schema,
            annotations=types.ToolAnnotations(read_only_hint=read_only, destructive_hint=destructive),
        ), fn)
        return fn
    return deco


def text(obj) -> types.TextContent:
    if not isinstance(obj, str):
        obj = json.dumps(obj, indent=1, default=str)
    return types.TextContent(type="text", text=obj)


def image(data: bytes, mime="image/png") -> types.ImageContent:
    return types.ImageContent(type="image", data=base64.b64encode(data).decode(), mime_type=mime)


PEER = {"type": "string", "description": "edit (Studio edit DataModel, default), server, or client / client-N (running playtest)"}
PART_SPEC = {
    "type": "array",
    "description": ("Part list in the model's own space. Each item: {n: name, sz: [x,y,z], off: [x,y,z], "
                    "rot: [rx,ry,rz] degrees applied as CFrame.Angles (R = Rx*Ry*Rz), shape: Block|Cylinder|Ball|"
                    "Wedge|CornerWedge, color: [r,g,b] 0-255 or '#rrggbb', mat: Enum.Material name, tr: transparency, "
                    "cc: CanCollide, primary: true for the PrimaryPart}. Cylinders run along local X. Front is -Z."),
    "items": {"type": "object"},
}
SHAPES = {"Block", "Cylinder", "Ball", "Wedge", "CornerWedge"}


def clean_spec(parts) -> list[dict]:
    """Validate a part list in Python so the Luau side never meets a value that would throw."""
    if not isinstance(parts, list) or not parts:
        raise ForgeError("parts must be a non-empty list")
    if len(parts) > 3000:
        raise ForgeError("more than 3000 parts -- split the model")
    out = []

    def vec(v, what, i, positive=False):
        if not (isinstance(v, (list, tuple)) and len(v) == 3 and all(isinstance(x, (int, float)) and math.isfinite(x) for x in v)):
            raise ForgeError(f"part {i}: {what} must be three finite numbers, got {v!r}")
        if positive and min(v) <= 0:
            raise ForgeError(f"part {i}: {what} must be positive, got {v!r}")
        return [float(x) for x in v]

    for i, p in enumerate(parts, 1):
        if not isinstance(p, dict):
            raise ForgeError(f"part {i} is not an object")
        q = {"n": str(p.get("n", f"Part{i}")), "sz": vec(p.get("sz"), "sz", i, True),
             "off": vec(p.get("off", [0, 0, 0]), "off", i), "rot": vec(p.get("rot", [0, 0, 0]), "rot", i)}
        shape = p.get("shape", "Block")
        if shape not in SHAPES:
            raise ForgeError(f"part {i}: shape {shape!r} is not one of {sorted(SHAPES)}")
        q["shape"] = shape
        col = p.get("color")
        if isinstance(col, str):
            m = re.fullmatch(r"#?([0-9a-fA-F]{6})", col.strip())
            if not m:
                raise ForgeError(f"part {i}: color {col!r} is not #rrggbb")
            col = [int(m.group(1)[k:k + 2], 16) for k in (0, 2, 4)]
        if col is not None:
            if not (isinstance(col, (list, tuple)) and len(col) == 3 and all(isinstance(c, (int, float)) for c in col)):
                raise ForgeError(f"part {i}: color must be [r,g,b] 0-255")
            q["color"] = [int(max(0, min(255, round(c)))) for c in col]
        if "mat" in p:
            q["mat"] = str(p["mat"])
        for k in ("tr", "refl"):
            if k in p:
                if not isinstance(p[k], (int, float)):
                    raise ForgeError(f"part {i}: {k} must be a number")
                q[k] = float(max(0.0, min(1.0, p[k])))
        if "cc" in p:
            q["cc"] = bool(p["cc"])
        if p.get("primary"):
            q["primary"] = True
        out.append(q)
    return out


def offline_audit(spec, gap=0.006) -> str:
    """Run the visual-pass part-list audit (vendored audit_parts.py) on an in-memory spec."""
    parts = []
    for p in spec:
        if p.get("tr", 0) >= 0.99:
            continue
        R = render._rot(p.get("rot", [0, 0, 0]))
        shape = {"Cylinder": "Cylinder", "Ball": "Ball"}.get(p.get("shape", "Block"), "Block")
        parts.append((p["n"], np.array(p["sz"], float), np.array(p.get("off", [0, 0, 0]), float), shape, R))
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        audit_parts.audit(parts, gap)
    note = ""
    if any(p.get("shape") in ("Wedge", "CornerWedge") for p in spec):
        note = "\n  (wedges were audited as their bounding blocks -- check slopes by eye)"
    return buf.getvalue().strip() + note


# ---------------------------------------------------------------- modelling
@tool("model_build", "Build a Model in Studio from a part list (validated first), then run the numeric audit "
      "on it. Use this instead of hand-writing Instance.new chains.",
      {"parts": PART_SPEC, "name": {"type": "string"}, "parent": {"type": "string", "description": "dotted path, default Workspace"},
       "origin": {"type": "array", "items": {"type": "number"}, "description": "world position of the model origin"},
       "anchored": {"type": "boolean"}, "peer": PEER, "audit": {"type": "boolean", "description": "default true"}},
      ["parts"], destructive=False)
async def model_build(a):
    spec = clean_spec(a.get("parts"))
    peer = a.get("peer", "edit")
    res = await STUDIO.run("build_model", {"parts": spec, "name": a.get("name", "ForgeModel"),
                                           "parent": a.get("parent", "Workspace"), "origin": a.get("origin", [0, 0, 0]),
                                           "anchored": a.get("anchored", True), "waypoint": peer == "edit"}, peer)
    out = [text(res)]
    if a.get("audit", True):
        out.append(text("offline part-list audit:\n" + offline_audit(spec)))
        out.append(text("in-Studio audit:\n" + await _audit(res["path"], peer)))
    return out


@tool("model_export", "Export a Model/BasePart as a part list (pivot space) -- feed it to parts_render / "
      "parts_audit, edit it, or rebuild it with model_build.",
      {"path": {"type": "string", "description": "dotted path, e.g. Workspace.Desk"}, "peer": PEER,
       "save_to": {"type": "string", "description": "optional .json file to write"}}, ["path"], read_only=True)
async def model_export(a):
    res = await STUDIO.run("export_parts", {"path": a["path"]}, a.get("peer", "edit"))
    if a.get("save_to"):
        Path(a["save_to"]).write_text(json.dumps(res["parts"], indent=1), encoding="utf-8")
    summary = {k: v for k, v in res.items() if k != "parts"} | {"part_count": len(res["parts"])}
    return [text(summary), text(json.dumps(res["parts"]))]


async def _audit(path, peer):
    code = template("audit").replace('local ROOT_PATH = ""', f"local ROOT_PATH = {json.dumps(path)}", 1)
    val = await STUDIO.luau(code, peer)
    return val if isinstance(val, str) else json.dumps(val)


@tool("model_audit", "Numeric visual-pass audit of a built model in Studio: z-fighting faces, floating groups, "
      "hidden parts, hover/sink against the ground. Must end with RESULT 0/0/0.",
      {"path": {"type": "string"}, "peer": PEER}, ["path"], read_only=True)
async def model_audit(a):
    return [text(await _audit(a["path"], a.get("peer", "edit")))]


@tool("model_seat", "Seat a model by its lowest TRUE corner onto the surface below it (raycast) or onto floor_y.",
      {"path": {"type": "string"}, "floor_y": {"type": "number"}, "peer": PEER}, ["path"])
async def model_seat(a):
    args = {"path": a["path"]}
    if "floor_y" in a:
        args["floor_y"] = a["floor_y"]
    return [text(await STUDIO.run("seat_model", args, a.get("peer", "edit")))]


@tool("parts_audit", "Offline z-fight / floating audit of a part list before it is built (no Studio needed).",
      {"parts": PART_SPEC, "gap": {"type": "number", "description": "default 0.006"}}, ["parts"], read_only=True)
async def parts_audit(a):
    return [text(offline_audit(clean_spec(a.get("parts")), a.get("gap", 0.006)))]


# ---------------------------------------------------------------- visual aid
@tool("parts_render", "Render a part list offline as flat-shaded orthographic views (front/back/left/right/top/iso) "
      "-- see a model before it exists, or without Studio.",
      {"parts": PART_SPEC, "views": {"type": "array", "items": {"type": "string"}},
       "size": {"type": "integer", "description": "pixels per view, default 420"}}, ["parts"], read_only=True)
async def parts_render(a):
    views = a.get("views") or ["front", "right", "top", "iso"]
    bad = [v for v in views if v not in render.VIEWS]
    if bad:
        raise ForgeError(f"unknown view(s) {bad}; use {list(render.VIEWS)}")
    png = render.render_parts(clean_spec(a.get("parts")), views, int(a.get("size", 420)))
    return [image(png)]


@tool("model_shots", "Real Studio screenshots of a model from several angles, framed automatically, returned "
      "as one labelled contact sheet. Works in edit mode or on a playtest client.",
      {"path": {"type": "string"}, "views": {"type": "array", "items": {"type": "string"}},
       "peer": PEER, "fov": {"type": "number"}, "pad": {"type": "number", "description": "framing margin, default 1.25"},
       "light": {"type": "boolean", "description": "temporary lit booth (floor + 3 lights), default true"}},
      ["path"], read_only=True)
async def model_shots(a):
    peer = a.get("peer", "edit")
    views = a.get("views") or ["front", "right", "back", "left", "top", "iso"]
    fov = float(a.get("fov", 40))
    b = await STUDIO.run("bounds", {"path": a["path"]}, peer)
    lo, hi = b["lo"], b["hi"]
    centre = [(lo[i] + hi[i]) / 2 for i in range(3)]
    radius = max(0.5, math.dist(lo, hi) / 2)
    dist = radius * float(a.get("pad", 1.25)) / math.tan(math.radians(fov / 2))
    shots, labels = [], []
    light = a.get("light", True)
    try:
        if light:
            await STUDIO.run("booth", {"lo": lo, "hi": hi}, peer)
        for v in views:
            if v not in render.VIEWS:
                raise ForgeError(f"unknown view {v}; use {list(render.VIEWS)}")
            f = render.VIEWS[v][0]
            f = f / (sum(x * x for x in f) ** 0.5)
            eye = [centre[i] - f[i] * dist for i in range(3)]
            if v == "top":
                eye[2] += dist * 0.01   # lookAt cannot look straight down its own up vector
            await STUDIO.run("set_camera", {"eye": eye, "at": centre, "fov": fov}, peer)
            await asyncio.sleep(0.35)
            shots.append(await STUDIO.screenshot())
            labels.append(v)
    finally:
        restore = {"release": True}
        if b.get("cam"):
            restore |= {"restore": b["cam"], "camType": b.get("camType"), "fov": b.get("fov")}
        with contextlib.suppress(Exception):
            await STUDIO.run("set_camera", restore, peer)
        if light:
            with contextlib.suppress(Exception):
                await STUDIO.run("booth", {"remove": True}, peer)
    return [text(f"{a['path']}: {b['parts']} parts, span {[round(hi[i] - lo[i], 3) for i in range(3)]}"),
            image(render.contact_sheet(shots, labels), "image/jpeg")]


@tool("map_plan", "Top-down floor plan of the world around a point (default: the first player) as an image: "
      "walls/pillars light, floors dim, furniture in its own colour, players in red with facing.",
      {"x": {"type": "number"}, "z": {"type": "number"}, "radius": {"type": "number", "description": "default 120"},
       "cut_y": {"type": "number", "description": "slice height; default player y + 2"},
       "peer": PEER, "size": {"type": "integer"}}, read_only=True)
async def map_plan(a):
    args = {k: a[k] for k in ("x", "z", "radius", "cut_y") if k in a}
    data = await STUDIO.run("topdown", args, a.get("peer", "server"), timeout=90)
    png = render.render_plan(data, int(a.get("size", 900)))
    note = f"{len(data['parts'])} parts" + (f", {data['dropped']} dropped (raise max)" if data.get("dropped") else "")
    return [text(note), image(png)]


# ---------------------------------------------------------------- measuring
@tool("perf_snapshot", "Client frame numbers over a window: fps, worst frame, GPU / render-CPU ms, draw and "
      "shadow draw calls, triangles, instances, memory -- and a warning if Studio is unfocused (60 fps throttle).",
      {"seconds": {"type": "number"}, "peer": PEER}, read_only=True)
async def perf_snapshot(a):
    return [text(await STUDIO.run("perf_snapshot", {"seconds": a.get("seconds", 3)}, a.get("peer", "client"), 40))]


@tool("perf_glide", "Repeatable moving-fps test: glide the player in a straight line through fresh chunks at a "
      "fixed speed and report fps, worst frame, worst second, per-second fps and chunk arrivals. <= 25 s per run; "
      "alternate headings and interleave A/B runs.",
      {"heading": {"type": "number", "description": "degrees, 0 = +X, 90 = +Z"}, "seconds": {"type": "number"},
       "speed": {"type": "number", "description": "studs/s, default 30"}, "peer": PEER})
async def perf_glide(a):
    args = {"heading": a.get("heading", 0), "seconds": min(float(a.get("seconds", 12)), 25), "speed": a.get("speed", 30)}
    return [text(await STUDIO.run("perf_glide", args, a.get("peer", "client"), 45))]


@tool("profile_summary", "Script-profile a peer and summarise it: total Lua ms/s, ms/s per script, hottest lines.",
      {"target": {"type": "string", "description": "server or client-1"}, "seconds": {"type": "number"},
       "top": {"type": "integer"}}, read_only=True)
async def profile_summary(a):
    secs = min(float(a.get("seconds", 8)), 15)
    out = Path(tempfile.gettempdir()) / f"robloxforge_prof_{os.getpid()}.json"
    await STUDIO.call("capture_script_profiler", {"target": a.get("target", "client-1"),
                                                  "duration_ms": int(secs * 1000), "output_path": str(out),
                                                  "max_functions": 5}, secs + 60)
    d = json.loads(out.read_text(encoding="utf-8"))
    dur = (d["SessionEndTime"] - d["SessionStartTime"]) / 1000
    total = sum(d["Nodes"][c["NodeId"] - 1]["TotalDuration"] for c in d["Categories"])
    fns = d["Functions"]
    scripts = sorted(((f["TotalDuration"] / 1000 / dur, f.get("Name", "?")) for f in fns
                      if "Line" not in f and f.get("Source") is None), reverse=True)
    lines = sorted(((f["TotalDuration"] / 1000 / dur, f.get("Name", "?"), (f.get("Source") or "").split(".")[-1], f.get("Line"))
                    for f in fns if f.get("Line")), reverse=True)
    top = int(a.get("top", 20))
    rep = [f"total Lua {total / 1000 / dur:.1f} ms/s over {dur:.1f} s",
           "per script (ms/s): " + ", ".join(f"{n} {v:.1f}" for v, n in scripts[:top]),
           "hot lines:"] + [f"  {v:6.2f}  {src}:{ln}  {n}" for v, n, src, ln in lines[:top]]
    return [text("\n".join(rep))]


@tool("game_selftest", "Read the place's SelfTest verdict (workspace.SelfTestOut) from a running playtest server.",
      {"full": {"type": "boolean"}}, read_only=True)
async def game_selftest(a):
    val = await STUDIO.luau('return tostring(workspace:GetAttribute("SelfTestOut"))', "server")
    if not a.get("full"):
        s = str(val)
        i = s.find("---- passed")
        val = s[:i] if i > 0 else s[:3000]
    return [text(val)]


# ---------------------------------------------------------------- scripting / repo
def _selene(args, cwd=REPO):
    p = subprocess.run([SELENE, *args], cwd=cwd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    return (p.stdout or "") + (p.stderr or "")


@tool("repo_lint", "Run selene on the Rojo repo (or given paths) from the repo root and summarise: errors in full, "
      "warnings grouped by rule.",
      {"paths": {"type": "array", "items": {"type": "string"}}, "max_listed": {"type": "integer"}}, read_only=True)
async def repo_lint(a):
    out = _selene(a.get("paths") or ["src"])
    blocks = re.split(r"\n(?=(?:error|warning)\[)", out)
    errs = [b.strip() for b in blocks if b.startswith("error")]
    warns = [b for b in blocks if b.startswith("warning")]
    rules = {}
    for w in warns:
        m = re.match(r"warning\[(\w+)\]", w)
        rules[m.group(1) if m else "?"] = rules.get(m.group(1) if m else "?", 0) + 1
    tail = "\n".join(out.strip().splitlines()[-4:])
    rep = [tail, "warnings by rule: " + json.dumps(rules)] + errs[: int(a.get("max_listed", 30))]
    return [text("\n\n".join(rep))]


@tool("luau_check", "Syntax/lint-check a Luau snippet with selene (repo config) without touching Studio -- run it "
      "before sending code to an eval, since Studio pauses on any eval error.",
      {"code": {"type": "string"}}, ["code"], read_only=True)
async def luau_check(a):
    with tempfile.NamedTemporaryFile("w", suffix=".lua", delete=False, encoding="utf-8") as f:
        f.write(a["code"])
        path = f.name
    try:
        return [text(_selene([path]).replace(path, "snippet.lua"))]
    finally:
        os.unlink(path)


def _disk_hashes():
    root = REPO / "src"
    rows = {}
    for p in root.rglob("*.lua*"):
        if p.suffix not in (".lua", ".luau"):
            continue
        rel = p.relative_to(root).as_posix()
        name = re.sub(r"(\.server|\.client)?\.luau?$", "", rel)
        if name.endswith("/init"):
            name = name[:-5]
        data = p.read_bytes()
        rows[name.replace("/", ".")] = (len(data), zlib.adler32(data))
    return rows


@tool("repo_drift", "Compare every script in Studio against the Rojo files on disk (length + Adler-32). Finds "
      "Studio-side edits that playtests run but git does not have.", {}, read_only=True)
async def repo_drift(a):
    studio = await STUDIO.run("script_hashes", None, "edit", 90)
    disk = _disk_hashes()
    diff, studio_only = [], []
    for name, (ln, ad) in studio.items():
        if name in disk:
            if disk[name][1] != ad:
                diff.append(f"DIFF {name}: studio {ln} bytes, disk {disk[name][0]} bytes")
        else:
            studio_only.append(name)
    disk_only = sorted(set(disk) - set(studio))
    rep = {"studio_scripts": len(studio), "disk_scripts": len(disk), "differ": diff,
           "studio_only": studio_only, "disk_only": disk_only}
    return [text(rep)]


def _port_open(port):
    with socket.socket() as s:
        s.settimeout(0.3)
        return s.connect_ex(("127.0.0.1", port)) == 0


@tool("rojo_status", "Is `rojo serve` running for the repo? With start=true, start it detached (Studio's Rojo "
      "plugin still has to press Connect).", {"start": {"type": "boolean"}})
async def rojo_status(a):
    up = _port_open(ROJO_PORT)
    if not up and a.get("start"):
        log = Path(tempfile.gettempdir()) / "robloxforge_rojo.log"
        flags = (0x00000008 | 0x00000200) if os.name == "nt" else 0  # DETACHED_PROCESS | NEW_PROCESS_GROUP
        subprocess.Popen([ROJO, "serve"], cwd=REPO, stdout=open(log, "w"), stderr=subprocess.STDOUT,
                         creationflags=flags)
        for _ in range(20):
            await asyncio.sleep(0.25)
            if _port_open(ROJO_PORT):
                break
        up = _port_open(ROJO_PORT)
        return [text({"rojo": "started" if up else "failed to start", "port": ROJO_PORT, "log": str(log)})]
    return [text({"rojo": "serving" if up else "not running", "port": ROJO_PORT, "repo": str(REPO)})]


NOTE_FILES = ["src/ServerStorage/HANDOFF.lua", "src/ServerScriptService/MapGeneratorNotes.lua",
              "src/ServerStorage/LIMINAL_AMBIENCE_HANDOFF.lua", "src/ServerStorage/AUDIO_REQUISITION.lua"]


@tool("notes_search", "Search the place's handoff/notes files (HANDOFF, MapGeneratorNotes, LIMINAL_AMBIENCE_HANDOFF, "
      "AUDIO_REQUISITION) for prior attempts, rejected ideas and traps before building something.",
      {"query": {"type": "string", "description": "regex, case-insensitive"}, "context": {"type": "integer"},
       "max_hits": {"type": "integer"}}, ["query"], read_only=True)
async def notes_search(a):
    rx = re.compile(a["query"], re.I)
    ctx, cap = int(a.get("context", 2)), int(a.get("max_hits", 25))
    out, hits = [], 0
    for rel in NOTE_FILES:
        p = REPO / rel
        if not p.exists():
            continue
        lines = p.read_text(encoding="utf-8", errors="replace").splitlines()
        for i, ln in enumerate(lines):
            if rx.search(ln):
                hits += 1
                if hits > cap:
                    break
                lo, hi = max(0, i - ctx), min(len(lines), i + ctx + 1)
                out.append(f"{rel}:{i + 1}\n" + "\n".join(lines[lo:hi]))
    return [text(f"{hits} hit(s)" + (f", first {cap} shown" if hits > cap else "") + "\n\n" + "\n---\n".join(out))]


# ---------------------------------------------------------------- status
@tool("forge_status", "RobloxForge health: Studio bridge, connected Studio instances, Rojo, repo state.", {}, read_only=True)
async def forge_status(a):
    st = {"bridge": "up" if STUDIO.child else f"down: {STUDIO.error}", "bridged_tools": len(STUDIO.tools),
          "native_tools": len(NATIVE), "rojo": "serving" if _port_open(ROJO_PORT) else "not running", "repo": str(REPO)}
    if STUDIO.child:
        with contextlib.suppress(Exception):
            r = await STUDIO.call("get_connected_instances", {}, 20)
            st["studio"] = r.structured_content
    with contextlib.suppress(Exception):
        g = subprocess.run(["git", "status", "--short"], cwd=REPO, capture_output=True, text=True)
        st["git_dirty_files"] = len([l for l in g.stdout.splitlines() if l.strip()])
    return [text(st)]


# ---------------------------------------------------------------- server plumbing
@asynccontextmanager
async def lifespan(_server):
    async with contextlib.AsyncExitStack() as stack:
        try:
            child = await stack.enter_async_context(Client(child_params(), read_timeout_seconds=120))
            STUDIO.tools = {t.name: t for t in (await child.list_tools()).tools if t.name not in NATIVE}
            STUDIO.child = child
        except Exception as e:  # keep serving the native tools without Studio
            STUDIO.error = repr(e)
        try:
            yield {}
        finally:
            STUDIO.child = None


async def on_list_tools(ctx, params):
    return types.ListToolsResult(tools=[t for t, _ in NATIVE.values()] + list(STUDIO.tools.values()))


async def on_call_tool(ctx, params):
    name, args = params.name, params.arguments or {}
    if name in NATIVE:
        try:
            return types.CallToolResult(content=await NATIVE[name][1](args))
        except ForgeError as e:
            return types.CallToolResult(content=[text(f"{name}: {e}")], is_error=True)
        except Exception as e:
            return types.CallToolResult(content=[text(f"{name} failed: {type(e).__name__}: {e}")], is_error=True)
    if name in STUDIO.tools:
        return await STUDIO.call(name, args)
    return types.CallToolResult(content=[text(f"unknown tool {name}")], is_error=True)


INSTRUCTIONS = """RobloxForge: Roblox Studio control plus modelling, visual and measuring tools.
- Studio pauses on ANY error inside an eval, even under pcall: nil-check everything; luau_check code first.
- Build models with model_build (part lists), then model_audit + model_shots before calling them done.
- Edit scripts on disk in the Rojo repo, not in Studio; repo_drift finds Studio-side edits.
- Measure fps only in a focused Studio window (perf_snapshot warns); A/B interleaved, one perf_glide per call.
- Search notes_search for prior attempts before building something in the game repo."""

server = Server("robloxforge", version="0.1.0", instructions=INSTRUCTIONS, lifespan=lifespan,
                on_list_tools=on_list_tools, on_call_tool=on_call_tool)


async def main():
    async with stdio_server() as (r, w):
        await server.run(r, w, server.create_initialization_options())


def run():
    asyncio.run(main())


# tool families in their own modules register themselves on import
from . import anim_tools, parity, play_tools, ui_tools  # noqa: E402,F401
