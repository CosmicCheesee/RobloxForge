"""Parity: browsing, inspecting and editing instances, properties, attributes, tags, collision groups,
selection, undo/redo and class reflection."""
from __future__ import annotations

import ast
import math
import operator

from .parity import ANY, ARR, B, L, N, O, PATH, S, run_body
from .server import PEER, text, tool
from .studio import ForgeError

# ---------------------------------------------------------------- browse / inspect
L("get_file_tree", "Instance hierarchy as a nested tree (name, class, children) from a root.",
  {"path": PATH, "maxDepth": N}, r'''
local root = A.path and resolve(A.path) or game
if not root then return err("no instance at " .. tostring(A.path)) end
local maxD = math.clamp(tonumber(A.maxDepth) or 4, 1, 12)
local count = 0
local function node(i, d)
	count += 1
	local n = {name = i.Name, class = i.ClassName}
	if d < maxD and count < 4000 then
		local kids = i:GetChildren()
		if #kids > 0 then
			n.children = {}
			for _, c in ipairs(kids) do
				if count >= 4000 then n.truncated = true break end
				n.children[#n.children + 1] = node(c, d + 1)
			end
		end
	elseif #i:GetChildren() > 0 then
		n.more = #i:GetChildren()
	end
	return n
end
return {tree = node(root, 1), nodes = count}
''', ro=True)

L("search_files", "Search instances by name, by class, or by script CONTENT (plain substring).",
  {"query": S, "searchType": {"type": "string", "enum": ["name", "type", "content"]}, "root": PATH, "limit": N}, r'''
local q = tostring(A.query or "")
if q == "" then return err("query is required") end
local mode = A.searchType or "name"
local root = A.root and resolve(A.root) or game
if not root then return err("no root " .. tostring(A.root)) end
local limit = math.clamp(tonumber(A.limit) or 200, 1, 2000)
local out, lq = {}, string.lower(q)
for _, d in ipairs(root:GetDescendants()) do
	local hit = false
	if mode == "name" then hit = string.find(string.lower(d.Name), lq, 1, true) ~= nil
	elseif mode == "type" then hit = d.ClassName == q or d:IsA(q) == true and classExists(q)
	elseif mode == "content" and d:IsA("LuaSourceContainer") then
		local ok, src = pcall(function() return d.Source end)
		if ok and src then
			local at = string.find(string.lower(src), lq, 1, true)
			if at then
				local line = select(2, string.gsub(string.sub(src, 1, at), "\n", "")) + 1
				out[#out + 1] = {path = d:GetFullName(), class = d.ClassName, line = line}
			end
		end
	end
	if hit then out[#out + 1] = {path = d:GetFullName(), class = d.ClassName} end
	if #out >= limit then break end
end
return {count = #out, results = out}
''', ["query"], ro=True)

L("get_services", "List the DataModel's services with their child counts, or the children of one service.",
  {"serviceName": S}, r'''
if A.serviceName then
	local s = resolve(A.serviceName)
	if not s then return err("no service " .. tostring(A.serviceName)) end
	local kids = {}
	for _, c in ipairs(s:GetChildren()) do kids[#kids + 1] = {name = c.Name, class = c.ClassName} end
	return {service = s.Name, children = kids}
end
local out = {}
for _, s in ipairs(game:GetChildren()) do
	out[#out + 1] = {name = s.Name, class = s.ClassName, children = #s:GetChildren()}
end
table.sort(out, function(a, b) return a.name < b.name end)
return {services = out}
''', ro=True)

L("get_instance_children", "Children of an instance with their classes.", {"instancePath": PATH}, r'''
local i = resolve(A.instancePath)
if not i then return err("no instance at " .. tostring(A.instancePath)) end
local out = {}
for _, c in ipairs(i:GetChildren()) do
	out[#out + 1] = {name = c.Name, class = c.ClassName, children = #c:GetChildren()}
end
return {path = i:GetFullName(), children = out}
''', ["instancePath"], ro=True)

L("get_descendants", "All descendants of an instance with depth, optionally filtered by class (IsA).",
  {"instancePath": PATH, "maxDepth": N, "classFilter": S, "limit": N}, r'''
local i = resolve(A.instancePath)
if not i then return err("no instance at " .. tostring(A.instancePath)) end
local maxD = math.clamp(tonumber(A.maxDepth) or 50, 1, 200)
local limit = math.clamp(tonumber(A.limit) or 2000, 1, 20000)
local cf = A.classFilter
if cf and not classExists(cf) then return err("unknown class " .. tostring(cf)) end
local out = {}
local function walk(o, d)
	for _, c in ipairs(o:GetChildren()) do
		if #out >= limit then return end
		if not cf or c:IsA(cf) then out[#out + 1] = {path = c:GetFullName(), class = c.ClassName, depth = d} end
		if d < maxD then walk(c, d + 1) end
	end
end
walk(i, 1)
return {count = #out, truncated = #out >= limit, descendants = out}
''', ["instancePath"], ro=True)

L("list_scripts", "Every script under a root (default the whole place): path, class, line count, enabled, RunContext.",
  {"root": PATH, "scriptType": {"type": "string", "enum": ["Script", "LocalScript", "ModuleScript"]}}, r'''
local root = A.root and resolve(A.root) or game
if not root then return err("no root " .. tostring(A.root)) end
local out = {}
for _, d in ipairs(root:GetDescendants()) do
	if d:IsA("LuaSourceContainer") and (not A.scriptType or d.ClassName == A.scriptType) then
		local ok, src = pcall(function() return d.Source end)
		local lines = ok and src and (select(2, string.gsub(src, "\n", "")) + 1) or nil
		local e = {path = d:GetFullName(), class = d.ClassName, lines = lines}
		if d:IsA("BaseScript") then
			e.enabled = d.Enabled
			e.runContext = tostring(d.RunContext)
		end
		out[#out + 1] = e
	end
end
table.sort(out, function(a, b) return a.path < b.path end)
return {count = #out, scripts = out}
''', ro=True)

L("search_by_property", "Find instances whose property equals a value (compared after conversion to JSON).",
  {"propertyName": S, "propertyValue": ANY, "root": PATH, "classFilter": S, "limit": N}, r'''
local root = A.root and resolve(A.root) or game
if not root then return err("no root " .. tostring(A.root)) end
local name, want = A.propertyName, HS:JSONEncode(A.propertyValue)
local cf = A.classFilter
local out = {}
for _, d in ipairs(root:GetDescendants()) do
	if (not cf or d:IsA(cf)) and propInfo(d, name) then
		local v = getProp(d, name)
		if v ~= nil then
			local j = toJson(v)
			if HS:JSONEncode(j) == want or (type(j) == "string" and type(A.propertyValue) == "string"
				and (j == A.propertyValue or j:match("([%w_]+)$") == A.propertyValue)) then
				out[#out + 1] = d:GetFullName()
				if #out >= (tonumber(A.limit) or 500) then break end
			end
		end
	end
end
return {count = #out, results = out}
''', ["propertyName", "propertyValue"], ro=True)

L("get_class_info", "Reflection for a class: superclass, every property (type, writable, category), methods and "
  "events -- the engine's own API, without docs.", {"className": S}, r'''
local name = A.className
if not classExists(name) then return err("unknown class " .. tostring(name)) end
local cls = RFS:GetClass(name)
local props = {}
for pn, p in pairs(propsOf(name)) do
	props[#props + 1] = {name = pn, type = p.st, enum = p.enum, writable = p.write, category = p.category, from = p.owner}
end
table.sort(props, function(a, b) return a.name < b.name end)
local methods, events = {}, {}
for _, m in ipairs(RFS:GetMethodsOfClass(name) or {}) do methods[#methods + 1] = m.Name end
local okE, ev = pcall(function() return RFS:GetEventsOfClass(name) end)
if okE then for _, e in ipairs(ev or {}) do events[#events + 1] = e.Name end end
table.sort(methods)
table.sort(events)
return {class = name, superclass = cls and cls.Superclass, properties = props, methods = methods, events = events}
''', ["className"], ro=True)

L("compare_instances", "Diff two instances property by property (useful when a duplicate behaves differently).",
  {"instancePathA": PATH, "instancePathB": PATH}, r'''
local a, b = resolve(A.instancePathA), resolve(A.instancePathB)
if not a or not b then return err("both instances must exist") end
local diffs, same = {}, 0
local pa, pb = propsOf(a.ClassName), propsOf(b.ClassName)
for name, info in pairs(pa) do
	if info.read and pb[name] and name ~= "Parent" then
		local va, vb = getProp(a, name), getProp(b, name)
		local ja, jb = HS:JSONEncode(toJson(va)), HS:JSONEncode(toJson(vb))
		if ja ~= jb then diffs[#diffs + 1] = {property = name, a = toJson(va), b = toJson(vb)} else same += 1 end
	end
end
table.sort(diffs, function(x, y) return x.property < y.property end)
return {a = a:GetFullName(), b = b:GetFullName(), classA = a.ClassName, classB = b.ClassName, different = diffs, same = same}
''', ["instancePathA", "instancePathB"], ro=True)

_SNAP = r'''
local function snap(root, maxD)
	local out = {}
	local function walk(o, rel, d)
		local props = {}
		for name, info in pairs(propsOf(o.ClassName)) do
			if info.read and name ~= "Parent" and info.st ~= "Instance" and info.st ~= "Object" then
				local v = getProp(o, name)
				if v ~= nil and typeof(v) ~= "Instance" then props[name] = toJson(v) end
			end
		end
		out[rel] = {class = o.ClassName, props = props}
		if d < maxD then
			local seen = {}
			for _, c in ipairs(o:GetChildren()) do
				local key = c.Name
				seen[key] = (seen[key] or 0) + 1
				if seen[key] > 1 then key = key .. "#" .. seen[key] end
				walk(c, rel .. "/" .. key, d + 1)
			end
		end
	end
	walk(root, ".", 0)
	return out
end
'''

L("diff_subtree", "Snapshot two subtrees (properties of every node down to maxDepth) and report what differs: nodes "
  "only in A, only in B, and changed properties.", {"pathA": PATH, "pathB": PATH, "maxDepth": N}, _SNAP + r'''
local a, b = resolve(A.pathA), resolve(A.pathB)
if not a or not b then return err("both subtrees must exist") end
local md = math.clamp(tonumber(A.maxDepth) or 4, 0, 10)
local sa, sb = snap(a, md), snap(b, md)
local onlyA, onlyB, changed = {}, {}, {}
for rel, na in pairs(sa) do
	local nb = sb[rel]
	if not nb then onlyA[#onlyA + 1] = rel
	else
		if na.class ~= nb.class then changed[#changed + 1] = {node = rel, property = "ClassName", a = na.class, b = nb.class}
		else
			for k, v in pairs(na.props) do
				if HS:JSONEncode(v) ~= HS:JSONEncode(nb.props[k]) then
					changed[#changed + 1] = {node = rel, property = k, a = v, b = nb.props[k]}
				end
			end
		end
	end
end
for rel in pairs(sb) do if not sa[rel] then onlyB[#onlyB + 1] = rel end end
table.sort(onlyA); table.sort(onlyB)
table.sort(changed, function(x, y) return x.node .. x.property < y.node .. y.property end)
return {onlyInA = onlyA, onlyInB = onlyB, changed = changed}
''', ["pathA", "pathB"], ro=True)

L("get_selection", "The objects currently selected in Studio.", {}, r'''
local sel = game:GetService("Selection"):Get()
local out = {}
for _, s in ipairs(sel) do out[#out + 1] = {path = s:GetFullName(), class = s.ClassName} end
return {count = #out, selection = out}
''', ro=True)

# ---------------------------------------------------------------- properties
L("set_property", "Set one property; the value is converted to the property's real type (see the value formats).",
  {"instancePath": PATH, "propertyName": S, "propertyValue": ANY}, r'''
local i = resolve(A.instancePath)
if not i then return err("no instance at " .. tostring(A.instancePath)) end
local ok, e = setProp(i, A.propertyName, A.propertyValue)
if not ok then return err(e) end
waypoint("set " .. tostring(A.propertyName))
return {path = i:GetFullName(), property = A.propertyName, value = toJson(i[A.propertyName])}
''', ["instancePath", "propertyName", "propertyValue"])

L("mass_set_property", "Set the same property on many instances.",
  {"paths": ARR, "propertyName": S, "propertyValue": ANY}, r'''
local done, failed = 0, {}
for _, p in ipairs(A.paths or {}) do
	local i = resolve(p)
	if not i then failed[#failed + 1] = {path = p, error = "not found"}
	else
		local ok, e = setProp(i, A.propertyName, A.propertyValue)
		if ok then done += 1 else failed[#failed + 1] = {path = p, error = e} end
	end
end
waypoint("mass set " .. tostring(A.propertyName))
return {set = done, failed = failed}
''', ["paths", "propertyName", "propertyValue"])

L("mass_get_property", "Read the same property from many instances.", {"paths": ARR, "propertyName": S}, r'''
local out = {}
for _, p in ipairs(A.paths or {}) do
	local i = resolve(p)
	if not i then out[#out + 1] = {path = p, error = "not found"}
	else
		local v, e = getProp(i, A.propertyName)
		out[#out + 1] = e and {path = p, error = e} or {path = p, value = toJson(v)}
	end
end
return {values = out}
''', ["paths", "propertyName"], ro=True)

# ---- formula and relative setters: computed in Python from the current values, then written back
_OPS = {ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul, ast.Div: operator.truediv,
        ast.Pow: operator.pow, ast.Mod: operator.mod, ast.USub: operator.neg, ast.UAdd: operator.pos}
_FUN = {k: getattr(math, k) for k in ("sin", "cos", "tan", "sqrt", "floor", "ceil", "log", "exp", "pi", "atan2", "radians", "degrees")}
_FUN.update({"min": min, "max": max, "round": round, "abs": abs})


def _eval(expr: str, env: dict):
    """Arithmetic only: numbers, the env names, + - * / ** %, and a few math functions. No attribute
    access, no calls outside the whitelist -- a formula is not a place to run code."""
    node = ast.parse(expr, mode="eval").body

    def ev(n):
        if isinstance(n, ast.Constant) and isinstance(n.value, (int, float)):
            return n.value
        if isinstance(n, ast.Name):
            if n.id in env:
                return env[n.id]
            if n.id in _FUN:
                return _FUN[n.id]
            raise ForgeError(f"unknown name {n.id} in formula")
        if isinstance(n, ast.BinOp) and type(n.op) in _OPS:
            return _OPS[type(n.op)](ev(n.left), ev(n.right))
        if isinstance(n, ast.UnaryOp) and type(n.op) in _OPS:
            return _OPS[type(n.op)](ev(n.operand))
        if isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id in _FUN:
            return _FUN[n.func.id](*[ev(x) for x in n.args])
        raise ForgeError("formulas may only use numbers, i, n, value/x/y/z, + - * / ** % and math functions")
    return ev(node)


async def _get_values(paths, prop, peer):
    res = await run_body(r'''
local out = {}
for _, p in ipairs(A.paths) do
	local i = resolve(p)
	local v = i and getProp(i, A.prop)
	out[#out + 1] = v ~= nil and toJson(v) or HS:JSONEncode(nil)
end
return {values = out}
''', {"paths": paths, "prop": prop}, peer)
    return res["values"]


async def _set_values(paths, prop, values, peer):
    return await run_body(r'''
local done, failed = 0, {}
for k, p in ipairs(A.paths) do
	local i = resolve(p)
	local ok, e = false, "not found"
	if i then ok, e = setProp(i, A.prop, A.values[k]) end
	if ok then done += 1 else failed[#failed + 1] = {path = p, error = e} end
end
waypoint("computed " .. A.prop)
return {set = done, failed = failed}
''', {"paths": paths, "prop": prop, "values": values}, peer)


def _apply(value, fn):
    if isinstance(value, (int, float)):
        return fn(value, None)
    if isinstance(value, list) and all(isinstance(x, (int, float)) for x in value):
        return [fn(x, k) for k, x in enumerate(value)]
    raise ForgeError(f"cannot do arithmetic on {value!r} (numbers and vectors only)")


@tool("set_calculated_property", "Set a property on many instances from an arithmetic formula. Names: i (1-based "
      "index), n (count), value (the current value, per component for vectors), x/y/z (current components). "
      "Example: positions in a row: propertyName=Position, formula='[i*4, y, z]' -- or one formula applied to "
      "every component.",
      {"paths": ARR, "propertyName": S, "formula": {"type": "string",
       "description": "a number formula, or a JSON-style list of per-component formulas like '[i*4, y, z]'"},
       "peer": PEER}, ["paths", "propertyName", "formula"])
async def set_calculated_property(a):
    peer = a.get("peer", "edit")
    paths = a["paths"]
    cur = await _get_values(paths, a["propertyName"], peer)
    f = a["formula"].strip()
    per = None
    if f.startswith("[") and f.endswith("]"):
        per = [x.strip() for x in f[1:-1].split(",")]
    out = []
    for k, v in enumerate(cur, 1):
        env = {"i": k, "n": len(paths)}
        if isinstance(v, list):
            env.update(dict(zip("xyzw", v)))
        if per:
            out.append([_eval(e, env | {"value": (v[c] if isinstance(v, list) and c < len(v) else v)}) for c, e in enumerate(per)])
        elif isinstance(v, list):
            out.append([_eval(f, env | {"value": x}) for x in v])
        else:
            out.append(_eval(f, env | {"value": v if isinstance(v, (int, float)) else 0}))
    return [text(await _set_values(paths, a["propertyName"], out, peer))]


@tool("set_relative_property", "Change a property relative to its current value on many instances: add, subtract, "
      "multiply or divide by a number or a per-component vector (Position +[0,5,0], Transparency *0.5...).",
      {"paths": ARR, "propertyName": S, "operation": {"type": "string", "enum": ["add", "subtract", "multiply", "divide"]},
       "value": {"description": "number or [x, y, z, ...]"}, "peer": PEER}, ["paths", "propertyName", "operation", "value"])
async def set_relative_property(a):
    peer = a.get("peer", "edit")
    op = {"add": operator.add, "subtract": operator.sub, "multiply": operator.mul, "divide": operator.truediv}[a["operation"]]
    val = a["value"]
    cur = await _get_values(a["paths"], a["propertyName"], peer)
    out = [_apply(v, lambda x, k: op(x, val[k] if isinstance(val, list) else val)) for v in cur]
    return [text(await _set_values(a["paths"], a["propertyName"], out, peer))]


# ---------------------------------------------------------------- create / delete / move
_CREATE = r'''
local function create(spec)
	local cls = spec.className
	if not classExists(cls) then return nil, "unknown class " .. tostring(cls) end
	local parent = resolve(spec.parent or "Workspace")
	if not parent then return nil, "no parent " .. tostring(spec.parent) end
	local ok, inst = pcall(function() return Instance.new(cls) end)
	if not ok or not inst then return nil, cls .. " cannot be created with Instance.new" end
	if spec.name then inst.Name = tostring(spec.name) end
	local bad = setProps(inst, spec.properties)
	local okP, e = pcall(function() inst.Parent = parent end)
	if not okP then inst:Destroy() return nil, tostring(e) end
	return inst, (#bad > 0) and bad or nil
end
'''

L("create_object", "Create an instance (any creatable class), optionally with properties.",
  {"className": S, "parent": PATH, "name": S, "properties": O}, _CREATE + r'''
local inst, e = create(A)
if not inst then return err(e) end
waypoint("create " .. A.className)
return {path = inst:GetFullName(), warnings = e}
''', ["className", "parent"])

L("mass_create_objects", "Create many instances in one call: objects = [{className, parent, name, properties}].",
  {"objects": ARR}, _CREATE + r'''
local made, failed = {}, {}
for k, spec in ipairs(A.objects or {}) do
	local inst, e = create(spec)
	if inst then
		made[#made + 1] = inst:GetFullName()
		if e then failed[#failed + 1] = {index = k, path = inst:GetFullName(), propertyProblems = e} end
	else
		failed[#failed + 1] = {index = k, error = e}
	end
end
waypoint("mass create")
return {created = made, failed = failed}
''', ["objects"])

L("delete_object", "Delete an instance (undoable).", {"instancePath": PATH}, r'''
local i = resolve(A.instancePath)
if not i then return err("no instance at " .. tostring(A.instancePath)) end
if i == game or i.Parent == game then return err("refusing to delete a service or the DataModel") end
local p = i:GetFullName()
i:Destroy()
waypoint("delete")
return {deleted = p}
''', ["instancePath"], destructive=True)

L("clone_object", "Deep-copy an instance to a new parent.", {"instancePath": PATH, "targetParentPath": PATH, "name": S}, r'''
local i, t = resolve(A.instancePath), resolve(A.targetParentPath or "Workspace")
if not i or not t then return err("source and target must exist") end
local c = i:Clone()
if not c then return err(i.Name .. " is not Archivable, so it cannot be cloned") end
if A.name then c.Name = A.name end
c.Parent = t
waypoint("clone")
return {path = c:GetFullName()}
''', ["instancePath"])

L("reparent_instance", "Move an instance to a new parent (keeps its identity, unlike delete + create).",
  {"sourcePath": PATH, "destinationPath": PATH}, r'''
local s, d = resolve(A.sourcePath), resolve(A.destinationPath)
if not s or not d then return err("source and destination must exist") end
if d == s or d:IsDescendantOf(s) then return err("cannot parent an instance into itself") end
local ok, e = pcall(function() s.Parent = d end)
if not ok then return err(tostring(e)) end
waypoint("reparent")
return {path = s:GetFullName()}
''', ["sourcePath", "destinationPath"])

_DUP = r'''
local function dup(spec)
	local src = resolve(spec.instancePath)
	if not src then return nil, "no instance at " .. tostring(spec.instancePath) end
	local o = spec.options or {}
	local n = math.clamp(tonumber(spec.count) or 1, 1, 500)
	local made = {}
	local off = o.positionOffset and arr(o.positionOffset, 3)
	local rot = o.rotationOffset and arr(o.rotationOffset, 3)
	local parents = o.targetParents
	for k = 1, n do
		local c = src:Clone()
		if not c then return nil, "not Archivable" end
		local pattern = o.namePattern or (src.Name .. "{n}")
		c.Name = (string.gsub(pattern, "{n}", tostring(k)))
		local parent = resolve((parents and parents[((k - 1) % #parents) + 1]) or "") or src.Parent
		if off or rot then
			local step = CFrame.new(off and Vector3.new(off[1] * k, off[2] * k, off[3] * k) or Vector3.zero)
				* (rot and CFrame.Angles(math.rad(rot[1] * k), math.rad(rot[2] * k), math.rad(rot[3] * k)) or CFrame.identity)
			if c:IsA("Model") then
				c:PivotTo(c:GetPivot() * step)
			elseif c:IsA("BasePart") then
				c.CFrame = c.CFrame * step
			end
		end
		for prop, values in pairs(o.propertyVariations or {}) do
			if type(values) == "table" and #values > 0 then setProp(c, prop, values[((k - 1) % #values) + 1]) end
		end
		c.Parent = parent
		made[#made + 1] = c:GetFullName()
	end
	return made
end
'''

L("smart_duplicate", "Duplicate an instance N times with a name pattern ('{n}'), a cumulative position/rotation "
  "offset, cycling property variations and target parents. options = {namePattern, positionOffset [x,y,z], "
  "rotationOffset [rx,ry,rz] deg, propertyVariations {Prop: [v1, v2...]}, targetParents [paths]}",
  {"instancePath": PATH, "count": N, "options": O}, _DUP + r'''
local made, e = dup(A)
if not made then return err(e) end
waypoint("smart duplicate")
return {created = made}
''', ["instancePath", "count"])

L("mass_duplicate", "Several smart_duplicate operations in one call: duplications = [{instancePath, count, options}].",
  {"duplications": ARR}, _DUP + r'''
local all, failed = {}, {}
for k, spec in ipairs(A.duplications or {}) do
	local made, e = dup(spec)
	if made then for _, p in ipairs(made) do all[#all + 1] = p end else failed[#failed + 1] = {index = k, error = e} end
end
waypoint("mass duplicate")
return {created = all, failed = failed}
''', ["duplications"])

L("insert_service", "Get or create a service by class name (e.g. Teams, VRService).", {"name": S}, r'''
if not classExists(A.name) then return err("unknown class " .. tostring(A.name)) end
local ok, s = pcall(function() return game:GetService(A.name) end)
if not ok or not s then return err(tostring(A.name) .. " is not a service") end
return {service = s:GetFullName(), class = s.ClassName}
''', ["name"])

L("undo", "Undo the last change in Studio (ChangeHistoryService).", {}, r'''
local can = CHS:GetCanUndo()
if not can then return {undone = false, reason = "nothing to undo"} end
CHS:Undo()
return {undone = true}
''', peer=False)

L("redo", "Redo the last undone change in Studio.", {}, r'''
local can = CHS:GetCanRedo()
if not can then return {redone = false, reason = "nothing to redo"} end
CHS:Redo()
return {redone = true}
''', peer=False)

# ---------------------------------------------------------------- attributes and tags
L("set_attribute", "Set an attribute. Primitives as-is; Vector3/Vector2/UDim2 by shape, or say valueType "
  "(Vector3, Color3, UDim2, BrickColor, NumberRange, CFrame...).",
  {"instancePath": PATH, "attributeName": S, "attributeValue": ANY, "valueType": S}, r'''
local i = resolve(A.instancePath)
if not i then return err("no instance at " .. tostring(A.instancePath)) end
local v = attrValue(A.attributeValue, A.valueType)
if v == nil then return err("could not convert the value" .. (A.valueType and (" to " .. A.valueType) or "")) end
local ok, e = pcall(function() i:SetAttribute(A.attributeName, v) end)
if not ok then return err(tostring(e)) end
waypoint("attribute")
return {path = i:GetFullName(), attribute = A.attributeName, value = toJson(i:GetAttribute(A.attributeName))}
''', ["instancePath", "attributeName", "attributeValue"])

L("bulk_set_attributes", "Set several attributes on one instance: attributes = {name: value} (types inferred).",
  {"instancePath": PATH, "attributes": O}, r'''
local i = resolve(A.instancePath)
if not i then return err("no instance at " .. tostring(A.instancePath)) end
local set, failed = 0, {}
for k, v in pairs(A.attributes or {}) do
	local val = attrValue(v, nil)
	local ok = val ~= nil and pcall(function() i:SetAttribute(k, val) end)
	if ok then set += 1 else failed[#failed + 1] = k end
end
waypoint("attributes")
return {set = set, failed = failed}
''', ["instancePath", "attributes"])

L("delete_attribute", "Remove an attribute.", {"instancePath": PATH, "attributeName": S}, r'''
local i = resolve(A.instancePath)
if not i then return err("no instance at " .. tostring(A.instancePath)) end
local had = i:GetAttribute(A.attributeName) ~= nil
i:SetAttribute(A.attributeName, nil)
waypoint("delete attribute")
return {removed = had}
''', ["instancePath", "attributeName"])

L("attribute_schema_validate", "Check an instance's attributes against a schema {key: {type, required, min, max, oneOf}}.",
  {"targetPath": PATH, "schema": O}, r'''
local i = resolve(A.targetPath)
if not i then return err("no instance at " .. tostring(A.targetPath)) end
local problems = {}
for key, rule in pairs(A.schema or {}) do
	local v = i:GetAttribute(key)
	if v == nil then
		if rule.required then problems[#problems + 1] = key .. " is missing" end
	else
		if rule.type and typeof(v) ~= rule.type then problems[#problems + 1] = ("%s is a %s, not a %s"):format(key, typeof(v), rule.type) end
		if type(v) == "number" then
			if rule.min and v < rule.min then problems[#problems + 1] = ("%s = %s is below %s"):format(key, v, rule.min) end
			if rule.max and v > rule.max then problems[#problems + 1] = ("%s = %s is above %s"):format(key, v, rule.max) end
		end
		if rule.oneOf then
			local okv = false
			for _, x in ipairs(rule.oneOf) do if x == v then okv = true end end
			if not okv then problems[#problems + 1] = key .. " is not one of the allowed values" end
		end
	end
end
local extra = {}
for k in pairs(i:GetAttributes()) do if not (A.schema or {})[k] then extra[#extra + 1] = k end end
return {valid = #problems == 0, problems = problems, notInSchema = extra}
''', ["targetPath", "schema"], ro=True)

L("get_tags", "CollectionService tags on an instance.", {"instancePath": PATH}, r'''
local i = resolve(A.instancePath)
if not i then return err("no instance at " .. tostring(A.instancePath)) end
return {tags = game:GetService("CollectionService"):GetTags(i)}
''', ["instancePath"], ro=True)

L("add_tag", "Add a CollectionService tag.", {"instancePath": PATH, "tagName": S}, r'''
local i = resolve(A.instancePath)
if not i then return err("no instance at " .. tostring(A.instancePath)) end
game:GetService("CollectionService"):AddTag(i, tostring(A.tagName))
waypoint("tag")
return {tags = game:GetService("CollectionService"):GetTags(i)}
''', ["instancePath", "tagName"])

L("remove_tag", "Remove a CollectionService tag.", {"instancePath": PATH, "tagName": S}, r'''
local i = resolve(A.instancePath)
if not i then return err("no instance at " .. tostring(A.instancePath)) end
game:GetService("CollectionService"):RemoveTag(i, tostring(A.tagName))
waypoint("untag")
return {tags = game:GetService("CollectionService"):GetTags(i)}
''', ["instancePath", "tagName"])

L("get_tagged", "Every instance carrying a tag.", {"tagName": S}, r'''
local out = {}
for _, i in ipairs(game:GetService("CollectionService"):GetTagged(tostring(A.tagName))) do
	out[#out + 1] = {path = i:GetFullName(), class = i.ClassName}
end
return {count = #out, tagged = out}
''', ["tagName"], ro=True)

L("collision_groups", "Physics collision groups: op=list (groups + collision matrix), create, remove, rename, "
  "set_collidable (name, other, collidable), assign (paths -> group, BaseParts and every BasePart inside a Model).",
  {"op": {"type": "string", "enum": ["list", "create", "remove", "rename", "set_collidable", "assign"]},
   "name": S, "other": S, "newName": S, "collidable": B, "paths": ARR}, r'''
local PS = game:GetService("PhysicsService")
local op = A.op or "list"
local function exists(n)
	for _, g in ipairs(PS:GetRegisteredCollisionGroups()) do if g.name == n then return true end end
	return n == "Default"
end
if op == "list" then
	local groups = {}
	local names = {}
	for _, g in ipairs(PS:GetRegisteredCollisionGroups()) do names[#names + 1] = g.name end
	for _, a in ipairs(names) do
		local row = {}
		for _, b in ipairs(names) do row[b] = PS:CollisionGroupsAreCollidable(a, b) end
		groups[#groups + 1] = {name = a, collides = row}
	end
	return {max = PS:GetMaxCollisionGroups(), groups = groups}
end
if type(A.name) ~= "string" or A.name == "" then return err("name is required") end
if op == "create" then
	if exists(A.name) then return {created = false, reason = "already exists"} end
	PS:RegisterCollisionGroup(A.name)
	return {created = true}
elseif op == "remove" then
	if not exists(A.name) or A.name == "Default" then return err("no removable group " .. A.name) end
	PS:UnregisterCollisionGroup(A.name)
	return {removed = true}
elseif op == "rename" then
	if not exists(A.name) or type(A.newName) ~= "string" then return err("need an existing name and newName") end
	PS:RenameCollisionGroup(A.name, A.newName)
	return {renamed = true}
elseif op == "set_collidable" then
	if not exists(A.name) or not exists(A.other) then return err("both groups must exist") end
	PS:CollisionGroupSetCollidable(A.name, A.other, A.collidable == true)
	return {collidable = PS:CollisionGroupsAreCollidable(A.name, A.other)}
elseif op == "assign" then
	if not exists(A.name) then return err("no group " .. A.name) end
	local n = 0
	for _, p in ipairs(A.paths or {}) do
		local i = resolve(p)
		if i then
			if i:IsA("BasePart") then i.CollisionGroup = A.name; n += 1 end
			for _, d in ipairs(i:GetDescendants()) do
				if d:IsA("BasePart") then d.CollisionGroup = A.name; n += 1 end
			end
		end
	end
	waypoint("collision group")
	return {assigned = n}
end
return err("unknown op " .. tostring(op))
''')

L("streamingenabled_audit", "Workspace streaming settings, plus every Model's ModelStreamingMode and LevelOfDetail "
  "(counts, and the non-default ones listed).", {}, r'''
local ws = workspace
local cfg = {StreamingEnabled = ws.StreamingEnabled}
for _, k in ipairs({"StreamingMinRadius", "StreamingTargetRadius", "StreamingIntegrityMode", "StreamOutBehavior"}) do
	local v = getProp(ws, k)
	if v ~= nil then cfg[k] = toJson(v) end
end
local modes, lods, special = {}, {}, {}
for _, d in ipairs(ws:GetDescendants()) do
	if d:IsA("Model") then
		local m = tostring(d.ModelStreamingMode)
		modes[m] = (modes[m] or 0) + 1
		local l = tostring(d.LevelOfDetail)
		lods[l] = (lods[l] or 0) + 1
		if d.ModelStreamingMode ~= Enum.ModelStreamingMode.Default and #special < 200 then
			special[#special + 1] = {path = d:GetFullName(), mode = m}
		end
	end
end
return {workspace = cfg, modelStreamingModes = modes, levelOfDetail = lods, nonDefault = special}
''', ro=True)
