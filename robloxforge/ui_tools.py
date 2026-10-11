"""UI tools: design (components, themes), see (offline render + audit, Studio previews across devices),
build (Studio), read (export, tree, at-point), check (live audit, repo style scan), ship (codegen)
and drive (click / type by name)."""
from __future__ import annotations

import asyncio
import base64
import contextlib
import io
import json
import re
from collections import Counter
from pathlib import Path

import mcp_types as types
from PIL import Image

from .server import PEER, REPO, STUDIO, _selene, image, text, tool
from .studio import ForgeError, long_string
from .ui import codegen, components, render, schema, themes

DEVICES = {
    "desktop": (1920, 1080), "laptop": (1366, 768), "tablet": (1180, 820), "tablet_portrait": (820, 1180),
    "phone": (844, 390), "phone_portrait": (390, 844), "small_phone": (667, 375), "android_phone": (800, 360),
    "console": (1920, 1080),
}
# the same names as Studio device-simulator presets (deviceId, orientation)
SIM = {
    "desktop": ("hd_1080", None), "laptop": ("average_laptop", None), "tablet": ("ipad_10th_generation", "LandscapeLeft"),
    "tablet_portrait": ("ipad_10th_generation", "Portrait"), "phone": ("iphone_14", "LandscapeLeft"),
    "phone_portrait": ("iphone_14", "Portrait"), "small_phone": ("iphone_7", "LandscapeLeft"),
    "android_phone": ("samsung_galaxy_a06", "LandscapeLeft"), "console": ("xbox", None),
}
THEME_ARG = {"description": "preset name (modern-dark, modern-light, glass, terminal, backroom), a saved theme, "
                            "or an inline token dict with optional 'extends'"}
SPEC_ARG = {"type": "object", "description": (
    "UI tree. Plain node: {type, name, props, attrs, children} (props: UDim2 [xs,xo,ys,yo] | 'fill', UDim number|[s,o], "
    "colour '#rrggbb'|[r,g,b]|'@token', FontFace 'Family'|{family,weight}, enums by item name). Component node: "
    "{ui: <component>, ...params} -- see ui_components. Theme tokens: '@accent', '@size.body', '@space.md'.")}


def _prep(spec, theme):
    th = themes.load(theme)
    R = schema.Resolver(th)
    root = schema.normalize(spec, R, components.expand)
    return th, root


def _as_screen(root, name="ForgeUI"):
    if root["type"] == "ScreenGui":
        return root
    return {"type": "ScreenGui", "name": name, "attrs": {},
            "props": [["IgnoreGuiInset", "bool", True], ["ResetOnSpawn", "bool", False],
                      ["ZIndexBehavior", "enum", "ZIndexBehavior", "Sibling"]], "children": [root]}


def _viewports(v):
    out = []
    for item in v or ["desktop"]:
        if isinstance(item, str):
            if item not in DEVICES:
                raise ForgeError(f"unknown device {item!r}; use {list(DEVICES)} or [w, h]")
            out.append((item, DEVICES[item]))
        elif isinstance(item, list) and len(item) == 2:
            out.append((f"{item[0]}x{item[1]}", (int(item[0]), int(item[1]))))
        else:
            raise ForgeError("viewports: device names or [w, h]")
    return out


def _clean_export(node):
    """Roblox reports the legacy Font as Unknown whenever a custom FontFace is set; drop it so the spec
    re-imports (FontFace carries the real typeface)."""
    props = node.get("props") or {}
    if props.get("Font") == "Unknown":
        props.pop("Font")
    for c in node.get("children") or []:
        _clean_export(c)
    return node


def _export_classes():
    out = {}
    for cls, props in schema.CLASSES.items():
        out[cls] = [[p, schema.prop_type(cls, p)] for p in sorted(props)]
    return out


# ---------------------------------------------------------------- design
@tool("ui_components", "The UI component library: list every component with its parameters, or expand one into "
      "plain spec nodes to see/modify exactly what it builds.",
      {"action": {"type": "string", "description": "list (default) | expand"},
       "component": {"type": "object", "description": "for expand: a component node, e.g. {ui:'button', text:'Play'}"},
       "theme": THEME_ARG}, read_only=True)
async def ui_components(a):
    if a.get("action", "list") == "expand":
        th, root = _prep(a.get("component") or {}, a.get("theme"))
        return [text(json.dumps(root))]
    lines = [f"{k:<12} {v}" for k, v in sorted(components.DOCS.items())]
    lines.append("\nEvery component also takes: name, order (LayoutOrder), pos (UDim2), anchor, visible, z, grow "
                 "(flex-fill in a stack), attrs, props (raw property overrides).")
    lines.append("Widths/heights: 'fill' | 'auto' | px | [scale, offset]. Spacing: xs sm md lg xl xxl or px.")
    lines.append("Icon glyphs verified to render in Roblox: " + schema.SAFE_GLYPHS + "  (plus colour emoji). "
                 "Broken (empty box): " + " ".join(schema.BROKEN_GLYPHS) + ".")
    return [text("\n".join(lines))]


@tool("ui_theme", "Design tokens: list presets, show one, check its contrast (WCAG), or save a custom theme "
      "(inline dict, may 'extends' a preset).",
      {"action": {"type": "string", "description": "list | show | contrast | save"}, "theme": THEME_ARG,
       "name": {"type": "string", "description": "for save"}}, read_only=False)
async def ui_theme(a):
    act = a.get("action", "list")
    if act == "list":
        return [text({"presets": sorted(themes.PRESETS), "saved": themes.saved()})]
    th = themes.load(a.get("theme"))
    if act == "show":
        return [text(th)]
    if act == "contrast":
        return [text(themes.contrast_report(th))]
    if act == "save":
        name = a.get("name")
        if not name or not re.fullmatch(r"[A-Za-z0-9_-]+", name):
            raise ForgeError("save needs a name of letters, digits, _ or -")
        raw = a.get("theme") if isinstance(a.get("theme"), dict) else th
        themes.save(name, raw)
        return [text(f"saved theme {name}\n" + themes.contrast_report(themes.load(name)))]
    raise ForgeError("action: list | show | contrast | save")


# ---------------------------------------------------------------- see (offline)
@tool("ui_render", "Render a UI spec OFFLINE (no Studio) at one or more screen sizes, with an automatic audit: "
      "text overflow, contrast, off-screen, clipping, overlaps, small tap targets. The fastest design loop.",
      {"spec": SPEC_ARG, "theme": THEME_ARG,
       "viewports": {"type": "array", "description": f"device names {list(DEVICES)} or [w, h]; default desktop"},
       "scale": {"type": "number", "description": "output image scale, default fits ~1600px wide"},
       "audit": {"type": "boolean", "description": "default true"},
       "save_to": {"type": "string", "description": "also write the PNG here (for ui_diff later)"}}, ["spec"], read_only=True)
async def ui_render(a):
    th, root = _prep(a["spec"], a.get("theme"))
    root = _as_screen(root)
    bg = tuple(schema.hex_rgb(th["color"]["bg"]))
    imgs, labels, reports = [], [], []
    for label, vp in _viewports(a.get("viewports")):
        boxes = []
        img = render.render(root, vp, bg=bg, boxes_out=boxes)
        imgs.append(img)
        labels.append(f"{label}  {vp[0]}x{vp[1]}")
        if a.get("audit", True):
            lines, counts = render.audit(boxes, vp, bg)
            summary = " ".join(f"{k}={v}" for k, v in sorted(counts.items())) or "clean"
            reports.append(f"[{label}] RESULT {summary}" + ("\n" + "\n".join(lines) if lines else ""))
    sheet = render.sheet(imgs, labels) if len(imgs) > 1 else imgs[0]
    target = float(a.get("scale") or min(1.0, 1600 / sheet.width))
    if target != 1.0:
        sheet = sheet.resize((max(1, int(sheet.width * target)), max(1, int(sheet.height * target))), Image.LANCZOS)
    png = render.to_png(sheet)
    if a.get("save_to"):
        Path(a["save_to"]).write_bytes(png)
    out = [image(png)]
    gw = schema.glyph_warnings(root)
    if gw:
        reports.insert(0, chr(10).join(gw))
    if reports:
        out.insert(0, text("\n\n".join(reports) + "\n(offline fonts are approximations -- confirm typography with ui_preview)"))
    return out


# ---------------------------------------------------------------- build / read in Studio
@tool("ui_build", "Build a UI spec in Studio (validated against a whitelist checked against the live engine, so it "
      "cannot throw). Edit mode -> StarterGui (shows in the viewport); a playtest client -> PlayerGui. Runs the live "
      "UI audit afterwards.",
      {"spec": SPEC_ARG, "theme": THEME_ARG, "parent": {"type": "string", "description": "StarterGui (edit default) | PlayerGui | dotted path"},
       "replace": {"type": "boolean", "description": "replace an existing gui of the same name (default true)"},
       "peer": PEER, "audit": {"type": "boolean"}}, ["spec"])
async def ui_build(a):
    th, root = _prep(a["spec"], a.get("theme"))
    peer = a.get("peer", "edit")
    parent = a.get("parent") or ("PlayerGui" if peer.startswith("client") else "StarterGui")
    if parent in ("StarterGui", "PlayerGui"):
        root = _as_screen(root)
    res = await STUDIO.run("ui_build", {"spec": root, "parent": parent, "replace": a.get("replace", True),
                                         "waypoint": peer == "edit"}, peer, 90)
    out = [text(res)]
    gw = schema.glyph_warnings(root)
    if gw:
        out.append(text(chr(10).join(gw)))
    if a.get("audit", True):
        await asyncio.sleep(0.3)
        out.append(text(await STUDIO.run("ui_audit", {"path": _path_for(res["path"], peer)}, peer, 60)))
    return out


def _path_for(full, peer):
    """GetFullName on a client gives Players.<name>.PlayerGui.X; our resolver takes PlayerGui.X."""
    m = re.match(r"Players\.[^.]+\.PlayerGui\.(.*)", full)
    return f"PlayerGui.{m.group(1)}" if m else full


@tool("ui_export", "Export an existing GUI from Studio as a spec (only properties that differ from defaults) -- "
      "to restyle it, render it offline, audit it, or codegen it. Game UIs built by scripts exist only on a playtest "
      "client: use peer=client and a PlayerGui.<Name> path.",
      {"path": {"type": "string", "description": "e.g. StarterGui.Menu or PlayerGui.HealthHud"}, "peer": PEER,
       "save_to": {"type": "string"}}, ["path"], read_only=True)
async def ui_export(a):
    res = await STUDIO.run("ui_export", {"path": a["path"], "classes": _export_classes()}, a.get("peer", "edit"), 90)
    _clean_export(res["spec"])
    if a.get("save_to"):
        Path(a["save_to"]).write_text(json.dumps(res["spec"], indent=1), encoding="utf-8")
    return [text({"instances": res["instances"], "skipped_non_ui": res["skipped_non_ui"]}), text(json.dumps(res["spec"]))]


@tool("ui_audit", "Live UI audit in Studio on the real layout: OVERFLOW, TINY text, CONTRAST (WCAG vs the actual "
      "backdrop), NOBACKDROP, OFFSCREEN, CLIPPED, OVERLAP, TOUCH targets, FIXED pixel layouts, INVISIBLE buttons, plus "
      "a census of colours / text sizes / fonts / radii in use.",
      {"path": {"type": "string"}, "peer": PEER, "min_text": {"type": "number"}, "min_touch": {"type": "number"}},
      ["path"], read_only=True)
async def ui_audit(a):
    args = {"path": a["path"]} | {k: a[k] for k in ("min_text", "min_touch") if k in a}
    return [text(await STUDIO.run("ui_audit", args, a.get("peer", "edit"), 60))]


@tool("ui_tree", "Compact outline of a GUI: class, name, absolute rect, hidden/disabled, text. Fast way to "
      "understand an existing UI.",
      {"path": {"type": "string"}, "peer": PEER, "depth": {"type": "integer"}}, ["path"], read_only=True)
async def ui_tree(a):
    return [text(await STUDIO.run("ui_tools", {"op": "tree", "path": a["path"], "depth": a.get("depth", 8)},
                                  a.get("peer", "edit"), 60))]


@tool("ui_at", "Which GUI objects are under a viewport pixel on the playtest client (top-most first) -- debug "
      "'why does my click not land'.", {"x": {"type": "number"}, "y": {"type": "number"}, "peer": PEER},
      ["x", "y"], read_only=True)
async def ui_at(a):
    return [text(await STUDIO.run("ui_tools", {"op": "at", "x": a["x"], "y": a["y"]}, a.get("peer", "client"), 30))]


@tool("ui_preview", "Real Studio screenshots of a GUI across device sizes (device simulator), optionally isolated "
      "from every other ScreenGui, as one contact sheet. Edit mode shows StarterGui guis.",
      {"path": {"type": "string", "description": "a ScreenGui path (or anything inside one)"},
       "devices": {"type": "array", "description": f"names {list(DEVICES)} or [w, h]; default desktop, phone"},
       "isolate": {"type": "boolean", "description": "hide other ScreenGuis during the shots (default true)"},
       "peer": PEER}, ["path"], read_only=True)
async def ui_preview(a):
    peer = a.get("peer", "edit")
    target = "edit" if peer == "edit" else (peer if "-" in peer else "client-1")
    vps = _viewports(a.get("devices") or ["desktop", "phone"])
    iso = a.get("isolate", True)
    if iso:
        await STUDIO.run("ui_tools", {"op": "isolate", "path": a["path"]}, peer, 30)
    try:
        entries = []
        for lab, (w, h) in vps:
            dev, orient = SIM.get(lab, ("hd_1080", None))
            e = {"label": lab, "deviceId": dev}
            if orient:
                e["orientation"] = orient
            if lab not in SIM:
                e["resolution"] = {"width": w, "height": h}
            entries.append(e)
        # Activate a MOBILE preset first: the matrix restores the prior device afterwards, and restoring an
        # orientation onto a desktop preset is refused by Studio (we stop simulation ourselves at the end).
        first = {"target": target, "deviceId": "iphone_14"}
        await STUDIO.call("set_device_simulator", first, 60)
        res = await STUDIO.call("capture_device_matrix", {"entries": entries, "target": target, "format": "jpeg",
                                                         "quality": 85}, 180)
        imgs = [base64.b64decode(b.data) for b in res.content if isinstance(b, types.ImageContent)]
        if not imgs:
            raise ForgeError(f"device matrix returned no images: {json.dumps(res.structured_content, default=str)[:600]}")
    finally:
        if iso:
            with contextlib.suppress(Exception):
                await STUDIO.run("ui_tools", {"op": "restore", "path": a["path"]}, peer, 30)
        with contextlib.suppress(Exception):
            await STUDIO.call("set_device_simulator", {"target": target, "stopSimulation": True}, 30)
    from .render import contact_sheet
    labels = [f"{lab} {w}x{h}" for lab, (w, h) in vps][:len(imgs)]
    return [image(contact_sheet(imgs, labels, cols=min(3, len(imgs)), width=900), "image/jpeg")]


# ---------------------------------------------------------------- drive
async def _locate(path, peer):
    loc = await STUDIO.run("ui_tools", {"op": "locate", "path": path}, peer, 30)
    if not loc.get("visible", True):
        raise ForgeError(f"{path} is not visible")
    return loc


@tool("ui_click", "Click a GUI button BY PATH on the playtest client (finds its centre, clicks it). Use instead of "
      "guessing pixel coordinates. Needs the Studio window focused (play_focus).",
      {"path": {"type": "string", "description": "e.g. PlayerGui.MainMenu.Play"}, "peer": PEER,
       "button": {"type": "string", "description": "Left (default) | Right"}}, ["path"])
async def ui_click(a):
    peer = a.get("peer", "client")
    loc = await _locate(a["path"], peer)
    await STUDIO.call("simulate_mouse_input", {"action": "click", "x": loc["x"], "y": loc["y"],
                                               "button": a.get("button", "Left")}, 30)
    return [text({"clicked": a["path"], "at": [loc["x"], loc["y"]]})]


@tool("ui_click_text", "Click the first visible button whose text contains a phrase (case-insensitive, plain text) on "
      "the playtest client -- e.g. 'play' on a title screen.", {"pattern": {"type": "string"}, "peer": PEER}, ["pattern"])
async def ui_click_text(a):
    peer = a.get("peer", "client")
    pat = long_string(re.sub(r"\s+", "", a["pattern"].lower()))
    code = f"""
local lp = game:GetService("Players").LocalPlayer
local pg = lp and lp:FindFirstChild("PlayerGui")
if not pg then return {{error = "no PlayerGui"}} end
local function shown(g)
	local cur = g
	while cur and cur ~= pg do
		if cur:IsA("GuiObject") and not cur.Visible then return false end
		if cur:IsA("LayerCollector") and not cur.Enabled then return false end
		cur = cur.Parent
	end
	return true
end
-- prefer a TextButton whose own text matches; else a TextLabel (a label drawn over a button -- clicking its
-- centre lands on whatever button is underneath); exact matches beat substring matches
local best, bestScore = nil, 0
for _, d in ipairs(pg:GetDescendants()) do
	if (d:IsA("TextButton") or d:IsA("TextLabel")) and shown(d) and d.AbsoluteSize.X > 0 and d.TextTransparency < 0.95 then
		local t = string.lower(string.gsub(d.Text, "<[^>]+>", ""))
		t = string.gsub(t, "%s+", "")   -- spacing-insensitive: "P L A Y" matches "play"
		if string.find(t, {pat}, 1, true) then
			local score = (d:IsA("TextButton") and 2 or 1) + ((t == {pat}) and 4 or 0)
			if score > bestScore then best, bestScore = d, score end
		end
	end
end
if not best then return {{error = "no visible button matches"}} end
local p, s = best.AbsolutePosition, best.AbsoluteSize
-- AbsolutePosition is measured from below the topbar for EVERY ScreenGui (an IgnoreGuiInset root sits at
-- y = -inset), so screen pixels are always AbsolutePosition + inset
local y = p.Y + s.Y / 2 + game:GetService("GuiService"):GetGuiInset().Y
return {{path = best:GetFullName(), text = best.Text, x = math.floor(p.X + s.X / 2 + 0.5), y = math.floor(y + 0.5)}}
"""
    loc = await STUDIO.luau(code, peer, 30)
    if isinstance(loc, dict) and loc.get("error"):
        raise ForgeError(loc["error"])
    await STUDIO.call("simulate_mouse_input", {"action": "click", "x": loc["x"], "y": loc["y"]}, 30)
    return [text({"clicked": loc["path"], "text": loc["text"], "at": [loc["x"], loc["y"]]})]


@tool("ui_type", "Type into a TextBox by path on the playtest client: clicks it to focus, then types the text "
      "(and Enter with submit=true).",
      {"path": {"type": "string"}, "text": {"type": "string"}, "submit": {"type": "boolean"}, "peer": PEER},
      ["path", "text"])
async def ui_type(a):
    peer = a.get("peer", "client")
    loc = await _locate(a["path"], peer)
    await STUDIO.call("simulate_mouse_input", {"action": "click", "x": loc["x"], "y": loc["y"]}, 30)
    await asyncio.sleep(0.15)
    await STUDIO.call("simulate_keyboard_input", {"text": a["text"]}, 30)
    if a.get("submit"):
        await STUDIO.call("simulate_keyboard_input", {"keyCode": "Return", "action": "tap"}, 30)
    return [text({"typed": len(a["text"]), "into": a["path"]})]


@tool("ui_destroy", "Delete a GUI (e.g. a preview built with ui_build) from Studio.",
      {"path": {"type": "string"}, "peer": PEER}, ["path"], destructive=True)
async def ui_destroy(a):
    return [text(await STUDIO.run("ui_tools", {"op": "destroy", "path": a["path"]}, a.get("peer", "edit"), 30))]


# ---------------------------------------------------------------- ship
@tool("ui_codegen", "Turn a UI spec (or an existing GUI exported from Studio) into a standalone Luau file: build() "
      "plus a runtime that animates every control (hover/press, focus rings, toggles, draggable sliders, tabs, "
      "click-away dismiss, fade+scale open/close -- fast in, slow out). kind=module returns {build, wire, open, close, "
      "THEME}; kind=localscript mounts itself in PlayerGui. Optionally writes into the repo and lints it.",
      {"spec": SPEC_ARG, "from_path": {"type": "string", "description": "export this GUI from Studio instead of a spec"},
       "peer": PEER, "theme": THEME_ARG, "kind": {"type": "string", "description": "module (default) | localscript"},
       "fx": {"type": "boolean", "description": "include the interaction runtime (default true)"},
       "keep_enabled": {"type": "boolean", "description": "re-assert Enabled on Heartbeat while open (Backroom HANDOFF rule)"},
       "write_to": {"type": "string", "description": "file path; relative paths are inside the Rojo repo, e.g. "
                                                       "src/StarterPlayer/StarterPlayerScripts/MyPanel.client.lua"}})
async def ui_codegen(a):
    note = ""
    if a.get("from_path"):
        res = await STUDIO.run("ui_export", {"path": a["from_path"], "classes": _export_classes()}, a.get("peer", "edit"), 90)
        spec = _clean_export(res["spec"])
        note = f"exported from {a['from_path']}"
    elif a.get("spec"):
        spec = a["spec"]
    else:
        raise ForgeError("give spec or from_path")
    th, root = _prep(spec, a.get("theme"))
    root = _as_screen(root)
    kind = a.get("kind", "module")
    if kind not in ("module", "localscript"):
        raise ForgeError("kind: module | localscript")
    src = codegen.generate(root, th, kind, a.get("fx", True), a.get("keep_enabled", False), note)
    out = []
    dest = a.get("write_to")
    if dest:
        p = Path(dest)
        if not p.is_absolute():
            p = REPO / p
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(src.encode("utf-8"))
        lint = _selene([str(p)])
        out.append(text(f"wrote {p} ({len(src.splitlines())} lines)\n" + "\n".join(lint.strip().splitlines()[-4:])))
    else:
        with contextlib.suppress(Exception):
            import tempfile
            import os
            with tempfile.NamedTemporaryFile("w", suffix=".lua", delete=False, encoding="utf-8") as f:
                f.write(src)
            lint = _selene([f.name])
            os.unlink(f.name)
            out.append(text("lint: " + " / ".join(lint.strip().splitlines()[-3:])))
    out.append(text(src))
    return out


# ---------------------------------------------------------------- check the whole repo
COLOR_RX = re.compile(r"Color3\.fromRGB\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*\)")
SIZE_RX = re.compile(r"TextSize\s*=\s*(\d+(?:\.\d+)?)")
FONT_RX = re.compile(r"Enum\.Font\.(\w+)|families/(\w+)\.json")
RADIUS_RX = re.compile(r"CornerRadius\s*=\s*UDim\.new\(\s*([\d.]+)\s*,\s*([\d.]+)\s*\)")


@tool("ui_style_scan", "Scan the Rojo repo's Luau for hard-coded UI style: colours (with near-duplicate clusters "
      "to merge into tokens), text sizes, fonts, corner radii, and which files hard-code the most -- the map for "
      "moving a game onto one theme.",
      {"paths": {"type": "array", "items": {"type": "string"}, "description": "subfolders of the repo, default src"},
       "top": {"type": "integer"}}, read_only=True)
async def ui_style_scan(a):
    roots = [REPO / p for p in (a.get("paths") or ["src"])]
    colors, sizes, fonts, radii, per_file = Counter(), Counter(), Counter(), Counter(), Counter()
    for root in roots:
        for f in root.rglob("*.lua"):
            src = f.read_text(encoding="utf-8", errors="replace")
            rel = f.relative_to(REPO).as_posix()
            n = 0
            for m in COLOR_RX.finditer(src):
                colors[tuple(int(x) for x in m.groups())] += 1
                n += 1
            for m in SIZE_RX.finditer(src):
                sizes[m.group(1)] += 1
                n += 1
            for m in FONT_RX.finditer(src):
                fonts[m.group(1) or m.group(2)] += 1
                n += 1
            for m in RADIUS_RX.finditer(src):
                radii[f"{m.group(1)},{m.group(2)}"] += 1
                n += 1
            if n:
                per_file[rel] = n
    top = int(a.get("top", 15))
    # cluster near-duplicate colours (max channel distance <= 10)
    clusters = []
    for c, n in colors.most_common():
        for cl in clusters:
            if max(abs(x - y) for x, y in zip(c, cl[0])) <= 10:
                cl[1].append((c, n))
                break
        else:
            clusters.append([c, [(c, n)]])
    merges = [cl for cl in clusters if len(cl[1]) > 1]
    hexc = lambda c: "#%02x%02x%02x" % c
    rep = [f"{sum(colors.values())} colour literals, {len(colors)} distinct, {len(clusters)} after merging near-duplicates",
           "top colours: " + ", ".join(f"{hexc(c)} x{n}" for c, n in colors.most_common(top)),
           f"near-duplicate groups ({len(merges)}): " + "; ".join(
               "/".join(hexc(c) for c, _ in cl[1][:5]) for cl in sorted(merges, key=lambda cl: -len(cl[1]))[:top]),
           f"text sizes ({len(sizes)} distinct): " + ", ".join(f"{s} x{n}" for s, n in sorted(sizes.items(), key=lambda kv: -kv[1])[:top]),
           f"fonts: " + ", ".join(f"{f} x{n}" for f, n in fonts.most_common(top)),
           f"corner radii: " + ", ".join(f"({r}) x{n}" for r, n in radii.most_common(top)),
           "files with the most hard-coded style: " + ", ".join(f"{f} {n}" for f, n in per_file.most_common(top))]
    return [text("\n".join(rep))]


# ---------------------------------------------------------------- templates and regression
from .ui import templates as _templates  # noqa: E402


@tool("ui_template", "Complete, responsive screens to start from: " + ", ".join(sorted(_templates.DOCS)) + ". Returns the "
      "spec (edit it, then ui_build / ui_codegen it) plus an offline render at desktop and phone with the audit.",
      {"name": {"type": "string"}, "params": {"type": "object", "description": "template parameters (see action=list)"},
       "theme": THEME_ARG, "viewports": {"type": "array"}, "action": {"type": "string", "description": "render (default) | list"}},
      read_only=True)
async def ui_template(a):
    if a.get("action") == "list" or not a.get("name"):
        return [text("\n".join(f"{k:<14} {v}" for k, v in sorted(_templates.DOCS.items())))]
    spec = _templates.build(a["name"], a.get("params"))
    out = await ui_render({"spec": spec, "theme": a.get("theme"), "viewports": a.get("viewports") or ["desktop", "phone"]})
    return [text(json.dumps(spec))] + out


@tool("ui_diff", "Visual regression: compare two images (renders, previews, screenshots saved with save_to). Reports "
      "the share of changed pixels, the changed regions, and returns a diff image with changes highlighted.",
      {"a": {"type": "string", "description": "image path (before)"}, "b": {"type": "string", "description": "image path (after)"},
       "threshold": {"type": "number", "description": "per-channel difference counted as a change, default 24"}},
      ["a", "b"], read_only=True)
async def ui_diff(a):
    import numpy as np
    A = Image.open(a["a"]).convert("RGB")
    B = Image.open(a["b"]).convert("RGB")
    if A.size != B.size:
        B = B.resize(A.size, Image.LANCZOS)
    x, y = np.asarray(A, dtype=np.int16), np.asarray(B, dtype=np.int16)
    mask = (np.abs(x - y).max(axis=2) > float(a.get("threshold", 24)))
    share = float(mask.mean())
    # coarse changed regions on a 32px grid
    H, W = mask.shape
    cells = []
    g = 32
    for yy in range(0, H, g):
        for xx in range(0, W, g):
            if mask[yy:yy + g, xx:xx + g].mean() > 0.02:
                cells.append((xx, yy))
    regions = []
    for cx, cy in cells:
        for r in regions:
            if cx <= r[2] + g and cx + g >= r[0] and cy <= r[3] + g and cy + g >= r[1]:
                r[0], r[1], r[2], r[3] = min(r[0], cx), min(r[1], cy), max(r[2], cx + g), max(r[3], cy + g)
                break
        else:
            regions.append([cx, cy, cx + g, cy + g])
    out = (np.asarray(B, dtype=np.float32) * 0.35).astype(np.uint8)
    out[mask] = [255, 60, 60]
    img = Image.fromarray(out)
    from PIL import ImageDraw
    d = ImageDraw.Draw(img)
    for r in regions:
        d.rectangle(r, outline=(255, 220, 0), width=2)
    return [text({"changed_pixels": f"{share * 100:.2f}%", "regions": regions[:30], "size": list(A.size)}),
            image(render.to_png(img))]
