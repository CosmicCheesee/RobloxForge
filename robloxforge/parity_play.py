"""Parity: playtests and their output, running code and tests in play, waiting on conditions, navigation,
live debugging (property watch, collisions, 3D picking), the script editor, script source sync to disk,
running/inserting from local files, and Studio identity/health."""
from __future__ import annotations

import asyncio
import base64
import hashlib
import json
import os
import re
import subprocess
import time
from pathlib import Path

from .parity import ARR, B, N, O, PATH, S, L, run_body
from .server import PEER, STUDIO, text, tool
from .studio import ForgeError

_LOG = {"cursor": None, "started": None}


async def bridge(name, args, timeout=120):
    """Call a bridged robloxstudio-mcp tool and return its structured result (or parsed text)."""
    res = await STUDIO.call(name, args, timeout)
    sc = res.structured_content
    if sc is None:
        for b in res.content:
            t = getattr(b, "text", None)
            if t:
                try:
                    sc = json.loads(t)
                except ValueError:
                    sc = {"text": t}
                break
    if res.is_error:
        raise ForgeError(f"{name}: {json.dumps(sc)[:600] if sc else 'failed'}")
    return sc or {}


def _entries(logs):
    out = []
    for e in (logs or {}).get("entries", []):
        out.append({"level": e.get("level"), "message": e.get("message")})
    return out


async def _read_logs(advance=True, tail=None, flt=None):
    args = {}
    if _LOG["cursor"]:
        args["cursor"] = _LOG["cursor"]
    if tail:
        args["tail"] = tail
    if flt:
        args["filter"] = flt
    logs = await bridge("get_runtime_logs", args)
    if advance and logs.get("nextCursor"):
        _LOG["cursor"] = logs["nextCursor"]
    return logs


# ---------------------------------------------------------------- playtest lifecycle with captured output
@tool("start_playtest", "Start a playtest and begin capturing its output (print/warn/error). mode play|run; "
      "numPlayers > 1 starts a multiplayer test. Poll with get_playtest_output, end with stop_playtest.",
      {"mode": {"type": "string", "enum": ["play", "run"]}, "numPlayers": N})
async def start_playtest(a):
    n = int(a.get("numPlayers") or 1)
    # take the cursor BEFORE starting, so everything the test prints is after it
    with_logs = await bridge("get_runtime_logs", {"tail": 1})
    _LOG["cursor"] = with_logs.get("nextCursor")
    if n > 1:
        res = await bridge("multiplayer_playtest", {"action": "start", "numPlayers": n, "timeout": 90}, 150)
    else:
        res = await bridge("solo_playtest", {"action": "start", "mode": a.get("mode", "play"), "timeout": 90}, 150)
    _LOG["started"] = time.time()
    return [text({"started": True, "players": n, "result": res})]


@tool("get_playtest_output", "Output captured since start_playtest (or since the last poll), plus whether a test is "
      "running. Does not stop anything.", {"filter": S, "tail": N}, read_only=True)
async def get_playtest_output(a):
    logs = await _read_logs(True, a.get("tail"), a.get("filter"))
    status = await bridge("solo_playtest", {"action": "status"})
    return [text({"status": status, "output": _entries(logs)})]


@tool("stop_playtest", "Stop the playtest and return everything it printed since start_playtest.", {})
async def stop_playtest(a):
    logs = await _read_logs(True)
    res = None
    for name, args in (("solo_playtest", {"action": "stop"}), ("multiplayer_playtest", {"action": "end"})):
        try:
            res = await bridge(name, args, 60)
            break
        except ForgeError:
            continue
    took = round(time.time() - _LOG["started"], 1) if _LOG["started"] else None
    _LOG["started"] = None
    return [text({"stopped": res is not None, "seconds": took, "output": _entries(logs)})]


L("get_output_log", "Studio's output history (LogService), in edit or play. messageType filters "
  "MessageOutput/MessageWarning/MessageError/MessageInfo.", {"maxEntries": N, "messageType": S}, r'''
local hist = game:GetService("LogService"):GetLogHistory()
local out = {}
local maxN = math.clamp(tonumber(A.maxEntries) or 200, 1, 5000)
for k = #hist, 1, -1 do
	local h = hist[k]
	if not A.messageType or tostring(h.messageType):find(A.messageType, 1, true) then
		table.insert(out, 1, {type = tostring(h.messageType):match("([%w_]+)$"), message = h.message, t = h.timestamp})
		if #out >= maxN then break end
	end
end
return {count = #out, entries = out}
''', ro=True)


@tool("get_studio_mode", "What Studio is doing: edit, or a playtest (play / run, solo or multiplayer).", {}, read_only=True)
async def get_studio_mode(a):
    status = await bridge("solo_playtest", {"action": "status"})
    running = bool(status.get("running")) if isinstance(status, dict) else False
    return [text({"mode": "playtest" if running else "edit", "status": status})]


@tool("run_script_in_play_mode", "Start a playtest, run Luau on the server (or a client), collect what it returned "
      "and printed, and stop the test again (unless keep=true). Roblox's own Studio MCP has this.",
      {"code": S, "target": {"type": "string", "description": "server (default) or client-1"},
       "mode": {"type": "string", "enum": ["play", "run"]}, "settle": {"type": "number", "description": "seconds to wait after start (default 3)"},
       "keep": B}, ["code"])
async def run_script_in_play_mode(a):
    await start_playtest({"mode": a.get("mode", "play")})
    await asyncio.sleep(float(a.get("settle", 3)))
    target = a.get("target", "server")
    t0 = time.time()
    error = None
    try:
        if target == "server":
            res = await bridge("eval_server_runtime", {"code": a["code"]}, 90)
        else:
            res = await bridge("eval_client_runtime", {"code": a["code"], "target": target}, 90)
    except ForgeError as e:
        res, error = None, str(e)
    took = round(time.time() - t0, 2)
    logs = await _read_logs(True)
    if not a.get("keep"):
        await stop_playtest({})
    return [text({"result": res, "error": error, "seconds": took, "output": _entries(logs), "stopped": not a.get("keep")})]


@tool("run_tests", "Run the place's tests in a playtest and summarise pass/fail. Waits for a workspace attribute "
      "(default SelfTestOut, Backroom's SelfTest) or, with no attribute, just runs for `seconds`; any error in the "
      "output counts as a failure.",
      {"attribute": S, "seconds": N, "mode": {"type": "string", "enum": ["play", "run"]}})
async def run_tests(a):
    attr = a.get("attribute", "SelfTestOut")
    limit = float(a.get("seconds", 60))
    await start_playtest({"mode": a.get("mode", "play")})
    verdict, t0 = None, time.time()
    while time.time() - t0 < limit:
        await asyncio.sleep(2)
        try:
            v = await bridge("eval_server_runtime", {"code": f'return tostring(workspace:GetAttribute("{attr}"))'}, 30)
        except ForgeError:
            continue
        rv = v.get("result") if isinstance(v, dict) else v
        if rv and rv != "nil":
            verdict = rv
            break
    logs = await _read_logs(True)
    await stop_playtest({})
    errors = [e for e in _entries(logs) if (e.get("level") or "").upper().startswith("ERR")]
    passed = failed = None
    if verdict:
        m = re.search(r"(\d+)\s+passed\s+(\d+)\s+FAILED", verdict)
        if m:
            passed, failed = int(m.group(1)), int(m.group(2))
    ok = (failed == 0 if failed is not None else verdict is not None) and not errors
    return [text({"pass": ok, "passed": passed, "failed": failed, "runtime_errors": errors[:30],
                  "report": (verdict or "")[:4000] or f"no {attr} attribute within {limit:.0f}s"})]


@tool("wait_for", "Poll a Luau condition until it is true (or time runs out). condition is an expression, e.g. "
      "'workspace:FindFirstChild(\"Boss\") ~= nil'.",
      {"condition": S, "peer": PEER, "timeout": N, "interval": N}, ["condition"], read_only=True)
async def wait_for(a):
    from .parity import run_body as rb
    t0, limit, iv = time.time(), float(a.get("timeout", 20)), max(0.1, float(a.get("interval", 0.5)))
    n = 0
    while True:
        n += 1
        v = await rb("local ok = (" + a["condition"] + ")\nreturn {ok = ok == true}", {}, a.get("peer", "edit"), 30)
        if isinstance(v, dict) and v.get("ok"):
            return [text({"met": True, "seconds": round(time.time() - t0, 2), "polls": n})]
        if time.time() - t0 > limit:
            return [text({"met": False, "seconds": round(time.time() - t0, 2), "polls": n})]
        await asyncio.sleep(iv)


L("character_navigation", "Walk the local character to a position or instance with PathfindingService (waypoints, "
  "jumps), in a running playtest. Returns whether it arrived.",
  {"position": ARR, "instancePath": PATH, "timeout": N}, r'''
local plr = game:GetService("Players").LocalPlayer
local ch = plr and plr.Character
local hum = ch and ch:FindFirstChildOfClass("Humanoid")
local root = ch and ch:FindFirstChild("HumanoidRootPart")
if not (hum and root) then return err("no character with a Humanoid -- run this on a playtest client") end
local goal
if A.instancePath then
	local i = resolve(A.instancePath)
	if not i then return err("no instance at " .. A.instancePath) end
	goal = i:IsA("Model") and i:GetPivot().Position or (i:IsA("BasePart") and i.Position)
else
	local p = arr(A.position, 3)
	goal = p and Vector3.new(p[1], p[2], p[3])
end
if not goal then return err("give position [x,y,z] or instancePath") end
local path = game:GetService("PathfindingService"):CreatePath({AgentCanJump = true})
local ok = pcall(function() path:ComputeAsync(root.Position, goal) end)
if not ok or path.Status ~= Enum.PathStatus.Success then
	return {arrived = false, reason = "no path (" .. tostring(path.Status) .. ")", distance = (root.Position - goal).Magnitude}
end
local t0 = os.clock()
local limit = tonumber(A.timeout) or 30
for _, wp in ipairs(path:GetWaypoints()) do
	if wp.Action == Enum.PathWaypointAction.Jump then hum.Jump = true end
	hum:MoveTo(wp.Position)
	local reached = false
	local c = hum.MoveToFinished:Connect(function(r) reached = true end)
	while not reached and os.clock() - t0 < limit do task.wait(0.05) end
	c:Disconnect()
	if os.clock() - t0 >= limit then break end
end
local d = (root.Position - goal).Magnitude
return {arrived = d < 4, distance = d, seconds = os.clock() - t0, waypoints = #path:GetWaypoints()}
''', timeout=90)

L("debug_watch", "Record changes on an instance for 1-15 s: property changes (all, or the listed ones), children "
  "added/removed, attribute changes -- a timeline of what touched it.",
  {"instancePath": PATH, "properties": ARR, "seconds": N}, r'''
local i = resolve(A.instancePath)
if not i then return err("no instance at " .. tostring(A.instancePath)) end
local secs = math.clamp(tonumber(A.seconds) or 5, 1, 15)
local want = nil
if type(A.properties) == "table" and #A.properties > 0 then
	want = {}
	for _, p in ipairs(A.properties) do want[p] = true end
end
local t0 = os.clock()
local log = {}
local conns = {}
local function add(e) if #log < 2000 then e.t = math.floor((os.clock() - t0) * 1000) / 1000; log[#log + 1] = e end end
conns[#conns + 1] = i.Changed:Connect(function(prop)
	if (not want or want[prop]) and propInfo(i, prop) then
		local v = getProp(i, prop)
		add({kind = "property", name = prop, value = toJson(v)})
	end
end)
conns[#conns + 1] = i.AttributeChanged:Connect(function(n) add({kind = "attribute", name = n, value = toJson(i:GetAttribute(n))}) end)
conns[#conns + 1] = i.ChildAdded:Connect(function(c) add({kind = "childAdded", name = c.Name, class = c.ClassName}) end)
conns[#conns + 1] = i.ChildRemoved:Connect(function(c) add({kind = "childRemoved", name = c.Name, class = c.ClassName}) end)
task.wait(secs)
for _, c in ipairs(conns) do c:Disconnect() end
return {path = i:GetFullName(), seconds = secs, events = #log, timeline = log}
''', ["instancePath"], ro=True, timeout=40)

L("debug_collisions", "Record every Touched contact on the BaseParts under an instance for 1-15 s during a "
  "playtest: which part hit what, when and where.", {"instancePath": PATH, "seconds": N}, r'''
local i = resolve(A.instancePath)
if not i then return err("no instance at " .. tostring(A.instancePath)) end
local secs = math.clamp(tonumber(A.seconds) or 5, 1, 15)
local parts = {}
if i:IsA("BasePart") then parts[1] = i end
for _, d in ipairs(i:GetDescendants()) do if d:IsA("BasePart") then parts[#parts + 1] = d end end
local t0, log, conns = os.clock(), {}, {}
for _, p in ipairs(parts) do
	conns[#conns + 1] = p.Touched:Connect(function(other)
		if #log < 1000 then
			log[#log + 1] = {t = math.floor((os.clock() - t0) * 1000) / 1000, part = p.Name, hit = other:GetFullName(),
				at = toJson(p.Position), speed = math.floor(p.AssemblyLinearVelocity.Magnitude * 100) / 100}
		end
	end)
end
task.wait(secs)
for _, c in ipairs(conns) do c:Disconnect() end
return {parts = #parts, seconds = secs, contacts = #log, log = log}
''', ["instancePath"], ro=True, timeout=40)

L("viewport_pick", "What 3D object is under a viewport pixel (raycast from the camera). Edit mode uses the "
  "Studio camera; on a client, the player's camera.", {"x": N, "y": N, "maxDistance": N}, r'''
local cam = workspace.CurrentCamera
if not cam then return err("no camera") end
local ray = cam:ViewportPointToRay(tonumber(A.x) or 0, tonumber(A.y) or 0)
local rp = RaycastParams.new()
rp.FilterType = Enum.RaycastFilterType.Exclude
local plr = game:GetService("Players").LocalPlayer
if plr and plr.Character then rp.FilterDescendantsInstances = {plr.Character} end
local hit = workspace:Raycast(ray.Origin, ray.Direction * (tonumber(A.maxDistance) or 2000), rp)
if not hit then return {hit = false, viewport = toJson(cam.ViewportSize)} end
return {hit = true, path = hit.Instance:GetFullName(), class = hit.Instance.ClassName, position = toJson(hit.Position),
	normal = toJson(hit.Normal), material = tostring(hit.Material), distance = (hit.Position - ray.Origin).Magnitude}
''', ["x", "y"], ro=True)

L("script_editor", "Studio script editor tabs: action=list (open documents), read (the editor's text, unsaved edits "
  "included), open (open a script, optionally at a line), edit (apply {old, new} replacements through the editor, "
  "so it is undoable and keeps unsaved work).",
  {"action": {"type": "string", "enum": ["list", "read", "open", "edit"]}, "path": PATH, "line": N, "edits": ARR}, r'''
local SES = game:GetService("ScriptEditorService")
local act = A.action or "list"
if act == "list" then
	local out = {}
	for _, d in ipairs(SES:GetScriptDocuments()) do
		if not d:IsCommandBar() then
			local s = d:GetScript()
			out[#out + 1] = {path = s and s:GetFullName(), lines = d:GetLineCount()}
		end
	end
	return {documents = out}
end
local s = resolve(A.path)
if not s or not s:IsA("LuaSourceContainer") then return err("no script at " .. tostring(A.path)) end
if act == "read" then
	return {path = s:GetFullName(), source = SES:GetEditorSource(s)}
elseif act == "open" then
	local ok, e = pcall(function() return SES:OpenScriptDocumentAsync(s) end)
	if not ok then return err(tostring(e)) end
	if A.line then
		for _, d in ipairs(SES:GetScriptDocuments()) do
			if d:GetScript() == s then pcall(function() d:ForceSetSelectionAsync(A.line, 1) end) end
		end
	end
	return {opened = s:GetFullName()}
elseif act == "edit" then
	local applied, missing = 0, {}
	local okU, e = pcall(function()
		SES:UpdateSourceAsync(s, function(old)
			local src = old
			for k, ed in ipairs(A.edits or {}) do
				local a, b = string.find(src, tostring(ed.old or ""), 1, true)
				if a and ed.old ~= "" then
					src = string.sub(src, 1, a - 1) .. tostring(ed.new or "") .. string.sub(src, b + 1)
					applied += 1
				else
					missing[#missing + 1] = k
				end
			end
			return src
		end)
	end)
	if not okU then return err(tostring(e)) end
	return {applied = applied, notFound = missing}
end
return err("unknown action " .. tostring(act))
''', peer=False)

L("studio_activity", "What is going on in this Studio: open script tabs, the selection, undo/redo availability, the "
  "last output lines, and Team Create collaborators when the place is in Team Create.", {}, r'''
local SES = game:GetService("ScriptEditorService")
local tabs = {}
for _, d in ipairs(SES:GetScriptDocuments()) do
	if not d:IsCommandBar() and d:GetScript() then tabs[#tabs + 1] = d:GetScript():GetFullName() end
end
local sel = {}
for _, s in ipairs(game:GetService("Selection"):Get()) do sel[#sel + 1] = s:GetFullName() end
local hist = game:GetService("LogService"):GetLogHistory()
local last = {}
for k = math.max(1, #hist - 9), #hist do last[#last + 1] = hist[k].message end
local people = {}
for _, p in ipairs(game:GetService("Players"):GetPlayers()) do people[#people + 1] = p.Name end
return {openTabs = tabs, selection = sel, canUndo = CHS:GetCanUndo(), canRedo = CHS:GetCanRedo(),
	lastOutput = last, teamCreatePlayers = people}
''', ro=True, peer=False)


@tool("get_handler_health", "Health of the Studio bridge: connected Studio instances and the round-trip time of a "
      "trivial eval on each peer that is up.", {}, read_only=True)
async def get_handler_health(a):
    out = {}
    try:
        out["instances"] = await bridge("get_connected_instances", {})
    except ForgeError as e:
        out["instances"] = str(e)
    for peer in ("edit", "server", "client"):
        t0 = time.time()
        try:
            await STUDIO.luau("return 1", peer, 15)
            out[f"{peer}_ms"] = round((time.time() - t0) * 1000)
        except Exception as e:  # noqa: BLE001 -- a peer that is not running is an answer, not an error
            out[f"{peer}_ms"] = None
            out[f"{peer}_note"] = str(e)[:120]
    return [text(out)]


@tool("studio_identity", "Which Studio and place this session is talking to: place id/name, game id, the "
      "connected instance ids.", {}, read_only=True)
async def studio_identity(a):
    info = await STUDIO.luau('return {placeId = game.PlaceId, gameId = game.GameId, name = game.Name, '
                             'creatorId = game.CreatorId}', "edit", 15)
    try:
        inst = await bridge("get_connected_instances", {})
    except ForgeError:
        inst = None
    return [text({"place": info, "instances": inst})]


# ---------------------------------------------------------------- local files
@tool("execute_luau_from_file", "Run a .luau / .lua file from disk in Studio (edit, server or client).",
      {"file": S, "peer": PEER}, ["file"])
async def execute_luau_from_file(a):
    p = Path(a["file"])
    if not p.is_file():
        raise ForgeError(f"no file {p}")
    return [text(await STUDIO.luau(p.read_text(encoding="utf-8"), a.get("peer", "edit"), 120))]


@tool("insert_asset_from_file", "Insert a local file into the place: .rbxm/.rbxmx models (via SerializationService), "
      "or a script file (.lua/.luau; .server.lua -> Script, .client.lua -> LocalScript, else ModuleScript).",
      {"file": S, "parentPath": PATH, "name": S}, ["file"])
async def insert_asset_from_file(a):
    p = Path(a["file"])
    if not p.is_file():
        raise ForgeError(f"no file {p}")
    parent = a.get("parentPath") or "game.Workspace"
    low = p.name.lower()
    if low.endswith(".rbxm") or low.endswith(".rbxmx"):
        if low.endswith(".rbxmx"):
            raise ForgeError(".rbxmx (XML) cannot be loaded by SerializationService; save it as binary .rbxm")
        res = await bridge("import_rbxm", {"source": {"path": str(p.resolve())}, "parent_path": parent}, 120)
        return [text(res)]
    if low.endswith((".lua", ".luau")):
        cls = "Script" if ".server." in low else "LocalScript" if ".client." in low else "ModuleScript"
        name = a.get("name") or re.sub(r"(\.server|\.client)?\.luau?$", "", p.name, flags=re.I)
        res = await run_body(r'''
local parent = resolve(A.parent)
if not parent then return err("no parent " .. tostring(A.parent)) end
local s = Instance.new(A.class)
s.Name = A.name
s.Source = A.source
s.Parent = parent
waypoint("insert script")
return {path = s:GetFullName(), class = A.class, lines = select(2, string.gsub(A.source, "\n", "")) + 1}
''', {"parent": parent, "class": cls, "name": name, "source": p.read_text(encoding="utf-8")})
        return [text(res)]
    raise ForgeError("supported: .rbxm, .lua, .luau (images need upload_asset)")


@tool("insert_model", "Search the Creator Store for a model and insert the best match (what Roblox's own Studio MCP "
      "offers). Defaults to ROBLOX-CREATED models only: community models can carry hidden scripts (backdoors), so "
      "allowCommunity=true is an explicit choice -- preview_asset first when you take one.",
      {"query": S, "parentPath": PATH, "position": O, "allowCommunity": B}, ["query"])
async def insert_model(a):
    found = await bridge("search_assets", {"assetType": "Model", "query": a["query"], "maxResults": 10,
                                           "robloxCreatedOnly": not a.get("allowCommunity", False)}, 60)
    items = found.get("assets") or found.get("results") or found.get("items") or []
    if not items:
        raise ForgeError(f"no models found for {a['query']!r}: {json.dumps(found)[:300]}")
    first = items[0]
    aid = first.get("assetId") or first.get("id") or first.get("AssetId")
    args = {"assetId": int(aid)}
    if a.get("parentPath"):
        args["parentPath"] = a["parentPath"]
    if a.get("position"):
        args["position"] = a["position"]
    res = await bridge("insert_asset", args, 120)
    return [text({"inserted": first, "result": res})]


# ---------------------------------------------------------------- source sync (scripts <-> a folder on disk)
EXT = {"Script": ".server.lua", "LocalScript": ".client.lua", "ModuleScript": ".lua"}


async def _list_sources(roots, exclude):
    return await run_body(r'''
local out = {}
local roots = A.roots
if type(roots) ~= "table" or #roots == 0 then
	roots = {"Workspace", "ReplicatedFirst", "ReplicatedStorage", "ServerScriptService", "ServerStorage",
		"StarterGui", "StarterPack", "StarterPlayer", "Lighting", "SoundService", "Teams", "Chat", "TextChatService"}
end
for _, r in ipairs(roots) do
	local root = resolve(r)
	if root then
		local list = root:GetDescendants()
		if root:IsA("LuaSourceContainer") then table.insert(list, 1, root) end
		for _, d in ipairs(list) do
			if d:IsA("LuaSourceContainer") then
				local skip = false
				for _, ex in ipairs(A.exclude or {}) do if d:GetFullName():find(ex, 1, true) then skip = true end end
				local ok, src = pcall(function() return d.Source end)
				if not skip and ok then
					local hasKids = false
					for _, c in ipairs(d:GetChildren()) do if c:IsA("LuaSourceContainer") then hasKids = true end end
					out[#out + 1] = {path = d:GetFullName(), class = d.ClassName, len = #src, kids = hasKids}
				end
			end
		end
	end
end
return {scripts = out}
''', {"roots": roots, "exclude": exclude}, "edit", 120)


async def _fetch_sources(paths):
    out = {}
    batch, size = [], 0
    async def flush():
        if not batch:
            return
        res = await run_body(r'''
local o = {}
for _, p in ipairs(A.paths) do
	local s = resolve(p)
	if s and s:IsA("LuaSourceContainer") then o[p] = s.Source end
end
return o
''', {"paths": list(batch)}, "edit", 120)
        out.update(res or {})
        batch.clear()
    for p, n in paths:
        batch.append(p)
        size += n
        if size > 180_000:
            await flush()
            size = 0
    await flush()
    return out


def _file_for(entry, all_paths):
    segs = entry["path"].split(".")
    name = segs[-1]
    ext = EXT.get(entry["class"], ".lua")
    if entry.get("kids"):
        return os.path.join(*segs, "init" + ext)
    return os.path.join(*segs[:-1], name + ext)


@tool("source_pull", "Write the place's scripts to disk as a Rojo-layout folder tree (Script .server.lua, "
      "LocalScript .client.lua, ModuleScript .lua; a script with script children becomes a folder with init) plus "
      "manifest.json, so git, ripgrep and any editor work on them. dry_run lists without writing.",
      {"out_dir": S, "roots": ARR, "exclude": ARR, "dry_run": B}, ["out_dir"])
async def source_pull(a):
    listing = await _list_sources(a.get("roots"), a.get("exclude") or [])
    entries = listing.get("scripts", [])
    if a.get("dry_run"):
        return [text({"scripts": len(entries), "bytes": sum(e["len"] for e in entries),
                      "files": [_file_for(e, None) for e in entries][:200]})]
    srcs = await _fetch_sources([(e["path"], e["len"]) for e in entries])
    root = Path(a["out_dir"])
    manifest = {}
    for e in entries:
        rel = _file_for(e, None)
        f = root / rel
        f.parent.mkdir(parents=True, exist_ok=True)
        src = srcs.get(e["path"], "")
        f.write_text(src, encoding="utf-8", newline="")
        manifest[rel.replace("\\", "/")] = {"path": e["path"], "class": e["class"],
                                            "sha1": hashlib.sha1(src.encode("utf-8")).hexdigest()}
    (root / "manifest.json").write_text(json.dumps(manifest, indent=1), encoding="utf-8")
    return [text({"written": len(manifest), "dir": str(root.resolve())})]


@tool("source_push", "Send edited files from a source_pull folder back into the place. Only files whose content "
      "changed since the pull (by manifest hash) are sent; dry_run shows what would change.",
      {"in_dir": S, "only": ARR, "dry_run": B}, ["in_dir"])
async def source_push(a):
    root = Path(a["in_dir"])
    mpath = root / "manifest.json"
    if not mpath.is_file():
        raise ForgeError(f"{mpath} not found -- run source_pull first")
    manifest = json.loads(mpath.read_text(encoding="utf-8"))
    changed = []
    for rel, m in manifest.items():
        f = root / rel
        if not f.is_file():
            continue
        if a.get("only") and not any(o in rel or o == m["path"] for o in a["only"]):
            continue
        src = f.read_text(encoding="utf-8")
        h = hashlib.sha1(src.encode("utf-8")).hexdigest()
        if h != m["sha1"]:
            changed.append((rel, m, src, h))
    if a.get("dry_run"):
        return [text({"would_push": [c[1]["path"] for c in changed]})]
    pushed, failed = [], []
    for rel, m, src, h in changed:
        try:
            await bridge("set_script_source", {"instancePath": m["path"], "source": src}, 60)
            m["sha1"] = h
            pushed.append(m["path"])
        except ForgeError as e:
            failed.append({"path": m["path"], "error": str(e)[:200]})
    mpath.write_text(json.dumps(manifest, indent=1), encoding="utf-8")
    return [text({"pushed": pushed, "failed": failed})]


@tool("source_snapshot", "Pull the scripts into a git repository and commit them -- the history a place file cannot "
      "keep (diff, blame, revert). Initialises the repo on first use.",
      {"dir": S, "message": S, "roots": ARR, "exclude": ARR}, ["dir"])
async def source_snapshot(a):
    d = Path(a["dir"])
    d.mkdir(parents=True, exist_ok=True)
    await source_pull({"out_dir": str(d), "roots": a.get("roots"), "exclude": a.get("exclude")})
    def git(*args):
        return subprocess.run(["git", *args], cwd=d, capture_output=True, text=True)
    if not (d / ".git").exists():
        git("init", "-q")
    git("add", "-A")
    r = git("commit", "-q", "-m", a.get("message") or f"snapshot {time.strftime('%Y-%m-%d %H:%M')}")
    head = git("log", "--oneline", "-1").stdout.strip()
    return [text({"dir": str(d.resolve()), "commit": head, "note": (r.stdout + r.stderr).strip()[:300] or "committed"})]
