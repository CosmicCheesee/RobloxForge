"""Animation tools: audit a rig, author a KeyframeSequence from JSON, inspect a clip, sample poses,
render filmstrips offline, and trace a motion for floor penetration, popping joints, loop seams and
limbs passing through each other.

Everything here works WITHOUT a playtest and WITHOUT Studio rendering: a clone of the rig is stepped
with Animator:StepAnimations in edit mode (see luau/anim_sample.luau), and pictures come from the
offline perspective renderer (render3d).
"""
from __future__ import annotations

import io
import json
import math
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

from . import render3d as r3
from .server import PEER, STUDIO, image, text, tool
from .studio import ForgeError

SOURCE = {"type": "string", "description": "a KeyframeSequence or Animation path in the place (e.g. "
          "ServerStorage.ForgeAnimations.Walk), or an animation asset id / rbxassetid://..."}
RIG = {"type": "string", "description": "dotted path to the rig Model (Humanoid or AnimationController, Motor6D joints)"}


async def _sample(a, times=None, fps=None):
    args = {"rig": a["rig"], "source": a["source"], "speed": a.get("speed", 1)}
    if times is not None:
        args["times"] = times
    if fps is not None:
        args["fps"] = fps
    res = await STUDIO.run("anim_sample", args, a.get("peer", "edit"), 90)
    if isinstance(res, dict) and res.get("error"):
        raise ForgeError(res["error"])
    return res


def _parts_at(res, frame, highlight=None):
    out = []
    for key, c in frame["parts"].items():
        info = res["parts"].get(key) or {}
        col = info.get("color") or "#a3a2a5"
        if highlight and info.get("name") in highlight:
            col = "#e0503c"
        out.append({"sz": info.get("size", [1, 1, 1]), "cf": r3.cf_matrix(c), "shape": info.get("shape", "Block"),
                    "color": col})
    return out


def _corners(sz, M):
    h = np.asarray(sz, float) / 2
    pts = np.array([[x, y, z] for x in (-h[0], h[0]) for y in (-h[1], h[1]) for z in (-h[2], h[2])])
    return (M[:3, :3] @ pts.T).T + M[:3, 3]


def _bounds(res):
    lo, hi = np.full(3, 1e9), np.full(3, -1e9)
    for fr in res["frames"]:
        for key, c in fr["parts"].items():
            sz = res["parts"].get(key, {}).get("size", [1, 1, 1])
            cs = _corners(sz, r3.cf_matrix(c))
            lo, hi = np.minimum(lo, cs.min(0)), np.maximum(hi, cs.max(0))
    return lo, hi


def _floor_y(res):
    if res.get("rest_floor") is not None and abs(res["rest_floor"]) < 1e6:
        return float(res["rest_floor"])
    fr = res["frames"][0]
    ys = [_corners(res["parts"].get(k, {}).get("size", [1, 1, 1]), r3.cf_matrix(c))[:, 1].min()
          for k, c in fr["parts"].items()]
    return float(min(ys)) if ys else 0.0


VIEW_DIRS = {"front": (0, 0.25, -1), "back": (0, 0.25, 1), "right": (1, 0.25, 0), "left": (-1, 0.25, 0),
             "iso": (0.8, 0.55, -0.8), "top": (0, 1, -0.02)}


def _filmstrip(res, views, size=(240, 300), highlight_at=None):
    lo, hi = _bounds(res)
    floor = _floor_y(res)
    centre = (lo + hi) / 2
    radius = max(1.5, float(np.linalg.norm(hi - lo)) / 2)
    fov = 34
    dist = radius * 1.3 / math.tan(math.radians(fov / 2))
    font = ImageFont.truetype("C:/Windows/Fonts/consola.ttf", 13) if Path("C:/Windows/Fonts/consola.ttf").exists() else None
    rows = []
    for v in views:
        if v not in VIEW_DIRS:
            raise ForgeError(f"unknown view {v}; use {list(VIEW_DIRS)}")
        d = np.asarray(VIEW_DIRS[v], float)
        d /= np.linalg.norm(d)
        cam = r3.look_at(centre + d * dist, centre)
        tiles = []
        for i, fr in enumerate(res["frames"]):
            hl = (highlight_at or {}).get(i)
            ground = [{"sz": [radius * 6, 0.05, radius * 6], "cf": r3.tf([centre[0], floor - 0.025, centre[2]]),
                       "color": (84, 86, 92)}]
            img = r3.render(ground + _parts_at(res, fr, hl), cam, fov=fov, size=size, bg=(26, 27, 31), ss=1)
            dr = ImageDraw.Draw(img)
            dr.text((6, 4), f"{v}  t={fr['t']:.2f}", font=font, fill=(220, 218, 206))
            tiles.append(img)
        rows.append(tiles)
    cols = max(len(r) for r in rows)
    sheet = Image.new("RGB", (cols * size[0] + (cols - 1) * 4, len(rows) * size[1] + (len(rows) - 1) * 4), (12, 12, 14))
    for ri, tiles in enumerate(rows):
        for ci, t in enumerate(tiles):
            sheet.paste(t, (ci * (size[0] + 4), ri * (size[1] + 4)))
    if sheet.width > 2400:
        k = 2400 / sheet.width
        sheet = sheet.resize((2400, int(sheet.height * k)), Image.LANCZOS)
    buf = io.BytesIO()
    sheet.save(buf, "PNG")
    return buf.getvalue()


def _obb_pen(sa, Ma, sb, Mb):
    """Penetration depth of two oriented boxes (0 if apart), by the separating-axis test."""
    Ra, Rb = Ma[:3, :3], Mb[:3, :3]
    ha, hb = np.asarray(sa) / 2, np.asarray(sb) / 2
    d = Mb[:3, 3] - Ma[:3, 3]
    axes = [Ra[:, i] for i in range(3)] + [Rb[:, i] for i in range(3)]
    for i in range(3):
        for j in range(3):
            c = np.cross(Ra[:, i], Rb[:, j])
            n = np.linalg.norm(c)
            if n > 1e-6:
                axes.append(c / n)
    pen = 1e9
    for L in axes:
        ra = sum(abs(L @ Ra[:, i]) * ha[i] for i in range(3))
        rb = sum(abs(L @ Rb[:, i]) * hb[i] for i in range(3))
        o = ra + rb - abs(d @ L)
        if o <= 0:
            return 0.0
        pen = min(pen, o)
    return pen


def _angle(Ra, Rb):
    c = (np.trace(Ra.T @ Rb) - 1) / 2
    return math.degrees(math.acos(max(-1.0, min(1.0, c))))


# 0.08: a box limb swinging about its joint dips its corner up to ~0.06 below the bind height (an R6 leg
# at 14 degrees), which is geometry, not a mistake
def _trace(res, floor_y=None, pen_tol=0.08, spike_dps=900, clip_tol=0.15):
    frames = res["frames"]
    floor = _floor_y(res) if floor_y is None else floor_y
    names = {k: res["parts"].get(k, {}).get("name", k) for k in frames[0]["parts"]}
    sizes = {k: res["parts"].get(k, {}).get("size", [1, 1, 1]) for k in frames[0]["parts"]}
    adj = set()
    for _, p0, p1 in res.get("joints", []):
        adj.add((p0, p1))
        adj.add((p1, p0))
    out = {"floor_y": round(floor, 3), "samples": len(frames), "length": res.get("length")}
    # 1. through the floor
    under = []
    for fr in frames:
        for k, c in fr["parts"].items():
            low = _corners(sizes[k], r3.cf_matrix(c))[:, 1].min()
            if low < floor - pen_tol:
                under.append((fr["t"], names[k], round(floor - low, 3)))
    worst = {}
    for t, n, dep in under:
        if dep > worst.get(n, (0, 0))[1]:
            worst[n] = (t, dep)
    out["floor_penetration"] = [{"part": n, "t": round(t, 2), "depth": d} for n, (t, d) in sorted(worst.items(), key=lambda x: -x[1][1])]
    # 2. pops: a part turning much faster in one step than it does anywhere else
    pops = []
    for k in frames[0]["parts"]:
        rates = []
        for a, b in zip(frames, frames[1:]):
            dt = max(1e-4, b["t"] - a["t"])
            rates.append((_angle(r3.cf_matrix(a["parts"][k])[:3, :3], r3.cf_matrix(b["parts"][k])[:3, :3]) / dt, a["t"], b["t"]))
        if not rates:
            continue
        med = float(np.median([r[0] for r in rates])) + 1e-6
        peak = max(rates, key=lambda r: r[0])
        if peak[0] > spike_dps and peak[0] > 4 * med:
            pops.append({"part": names[k], "between": [round(peak[1], 2), round(peak[2], 2)], "deg_per_s": round(peak[0]),
                         "median_deg_per_s": round(med)})
    out["pops"] = pops
    # 3. the loop seam
    if res.get("looped") or (res.get("clip") or {}).get("loop"):
        a, b = frames[0], frames[-1]
        seam = []
        for k in a["parts"]:
            Ma, Mb = r3.cf_matrix(a["parts"][k]), r3.cf_matrix(b["parts"][k])
            dp = float(np.linalg.norm(Ma[:3, 3] - Mb[:3, 3]))
            da = _angle(Ma[:3, :3], Mb[:3, :3])
            if dp > 0.05 or da > 3:
                seam.append({"part": names[k], "moves": round(dp, 3), "turns_deg": round(da, 1)})
        out["loop_seam"] = seam
    # 4. limbs through each other (not through the part they are jointed to)
    clips = {}
    keys = list(frames[0]["parts"])
    for fr in frames:
        for i in range(len(keys)):
            for j in range(i + 1, len(keys)):
                na, nb = names[keys[i]], names[keys[j]]
                if (na, nb) in adj:
                    continue
                pen = _obb_pen(sizes[keys[i]], r3.cf_matrix(fr["parts"][keys[i]]), sizes[keys[j]], r3.cf_matrix(fr["parts"][keys[j]]))
                if pen > clip_tol and pen > clips.get((na, nb), (0, 0))[1]:
                    clips[(na, nb)] = (fr["t"], pen)
    out["interpenetration"] = [{"parts": [a, b], "t": round(t, 2), "depth": round(d, 3)}
                               for (a, b), (t, d) in sorted(clips.items(), key=lambda x: -x[1][1])]
    # 5. reach, for scale
    lo, hi = _bounds(res)
    out["extent"] = {"lo": [round(x, 2) for x in lo], "hi": [round(x, 2) for x in hi]}
    issues = len(out["floor_penetration"]) + len(out["pops"]) + len(out.get("loop_seam", [])) + len(out["interpenetration"])
    out["verdict"] = "clean" if issues == 0 else f"{issues} issue(s)"
    return out


# ---------------------------------------------------------------- tools
@tool("anim_rig", "Rig utilities for animation work. op=audit: joints, Animator, anchored/unjointed parts and "
      "other reasons a rig will not animate. op=r6: build a standard R6 test dummy (workspace.ForgeRigs) to author "
      "or test animations on. op=remove: delete the test dummies.",
      {"op": {"type": "string", "description": "audit (default) | r6 | remove"}, "path": RIG,
       "at": {"type": "array", "description": "r6: where to stand it, [x, y, z] (default far above the level)"},
       "name": {"type": "string"}, "peer": PEER})
async def anim_rig(a):
    op = a.get("op", "audit")
    args = {"op": op, "path": a.get("path"), "at": a.get("at"), "name": a.get("name")}
    return [text(await STUDIO.run("anim_rig", args, a.get("peer", "edit"), 60))]


@tool("anim_build", "Author a KeyframeSequence from JSON against a rig's joint tree and save it (ServerStorage."
      "ForgeAnimations by default); it is registered at once so anim_sample / anim_filmstrip / anim_trace can play it "
      "with no upload. spec = {name, loop, priority, keyframes: [{t, poses: {PartName: {rot: [rx, ry, rz] degrees, "
      "pos: [x, y, z], easing: Linear|Constant|Cubic|Elastic|Bounce, dir: In|Out|InOut}}}], markers: [{t, name, value}]}. "
      "A pose is the joint's Transform: the rotation of that part about its joint, in the joint's own frame.",
      {"rig": RIG, "spec": {"type": "object"}, "save_to": {"type": "string"}, "peer": PEER}, ["rig", "spec"])
async def anim_build(a):
    res = await STUDIO.run("anim_build", {"rig": a["rig"], "spec": a["spec"], "save_to": a.get("save_to")},
                           a.get("peer", "edit"), 60)
    return [text(res)]


@tool("anim_inspect", "Summarise an animation clip: length, loop, priority, keyframe times, which parts it poses "
      "and how often, and its markers.", {"source": SOURCE, "peer": PEER}, ["source"], read_only=True)
async def anim_inspect(a):
    res = await STUDIO.run("anim_sample", {"source": a["source"], "inspect_only": True}, a.get("peer", "edit"), 60)
    return [text(res)]


@tool("anim_sample", "Pose a rig at given times of an animation (no playtest needed -- a clone is stepped with "
      "Animator:StepAnimations in edit mode) and return every part's CFrame relative to the rig's root, plus joint "
      "Transforms in degrees. Use times=[...] or fps.",
      {"rig": RIG, "source": SOURCE, "times": {"type": "array"}, "fps": {"type": "number"}, "speed": {"type": "number"},
       "save_to": {"type": "string", "description": "write the full JSON here"}, "peer": PEER}, ["rig", "source"], read_only=True)
async def anim_sample(a):
    res = await _sample(a, a.get("times"), a.get("fps"))
    if a.get("save_to"):
        Path(a["save_to"]).write_text(json.dumps(res), encoding="utf-8")
    brief = {"length": res["length"], "looped": res["looped"], "samples": len(res["frames"]),
             "parts": sorted({v["name"] for v in res["parts"].values()}), "clip": res.get("clip")}
    if not a.get("save_to"):
        brief["frames"] = res["frames"]
    return [text(brief)]


@tool("anim_filmstrip", "Render an animation as a filmstrip WITHOUT Studio rendering: the rig is sampled at N "
      "evenly spaced times and every pose is drawn offline (perspective, a floor at the rest foot level), one row "
      "per view. Parts that go through the floor at a frame are drawn red.",
      {"rig": RIG, "source": SOURCE, "frames": {"type": "integer", "description": "default 8"},
       "views": {"type": "array", "description": "front | back | left | right | iso | top (default front, right)"},
       "save_to": {"type": "string"}, "peer": PEER}, ["rig", "source"], read_only=True)
async def anim_filmstrip(a):
    n = max(2, min(24, int(a.get("frames", 8))))
    first = await _sample(a, [0])
    L = first["length"]
    res = await _sample(a, [L * i / (n - 1) for i in range(n)])
    floor = _floor_y(res)
    hl = {}
    for i, fr in enumerate(res["frames"]):
        bad = set()
        for k, c in fr["parts"].items():
            info = res["parts"].get(k, {})
            if _corners(info.get("size", [1, 1, 1]), r3.cf_matrix(c))[:, 1].min() < floor - 0.08:
                bad.add(info.get("name"))
        if bad:
            hl[i] = bad
    png = _filmstrip(res, a.get("views") or ["front", "right"], highlight_at=hl)
    if a.get("save_to"):
        Path(a["save_to"]).write_bytes(png)
    return [text({"length": L, "frames": n, "red": {res["frames"][i]["t"]: sorted(v) for i, v in hl.items()}}), image(png)]


@tool("anim_trace", "Check a motion numerically: parts going through the floor (below the rest foot level), "
      "joints that POP (one step much faster than the rest of the clip), a loop whose last pose does not meet its "
      "first, and limbs passing through each other (jointed neighbours excepted). Samples at fps (default 30). The "
      "floor is the rig's REST pose lowest point, with 0.08 of tolerance for box corners dipping as a limb swings.",
      {"rig": RIG, "source": SOURCE, "fps": {"type": "number"}, "floor_y": {"type": "number",
       "description": "floor height in the root's space (default: the lowest point at t=0)"},
       "spike_dps": {"type": "number", "description": "pop threshold in degrees per second (default 900)"},
       "peer": PEER}, ["rig", "source"], read_only=True)
async def anim_trace(a):
    res = await _sample(a, None, a.get("fps", 30))
    return [text(_trace(res, a.get("floor_y"), spike_dps=float(a.get("spike_dps", 900))))]
