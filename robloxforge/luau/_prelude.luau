-- Shared prelude for the parity tools. Everything here is written so it CANNOT throw: Studio's debugger
-- pauses on any error inside an MCP eval, even one caught by pcall, which freezes play. So values are
-- validated against ReflectionService (does the property exist, is it writable, what type is it)
-- before anything is touched, and pcall is only the last guard on the assignment itself.
local HS = game:GetService("HttpService")
local RFS = game:GetService("ReflectionService")
local A = HS:JSONDecode(__ARGS__)

local function err(msg) return {error = msg} end

local SERVICE_ALIAS = {workspace = "Workspace", game = nil}
local function resolve(path)
	if typeof(path) == "Instance" then return path end
	if type(path) ~= "string" or path == "" then return nil end
	if path == "game" then return game end
	local o = game
	local first = true
	for seg in string.gmatch(path, "[^%.]+") do
		if first and seg == "game" then
			first = false
		else
			if first and SERVICE_ALIAS[seg] then seg = SERVICE_ALIAS[seg] end
			first = false
			if not o then return nil end
			local nxt = o:FindFirstChild(seg)
			if not nxt and o == game then
				-- services that have not been created yet are still reachable by name
				for _, s in ipairs(game:GetChildren()) do
					if s.ClassName == seg then nxt = s break end
				end
			end
			o = nxt
		end
	end
	return o
end

local function pathOf(i)
	if not i then return nil end
	return i:GetFullName()
end

-- ---- reflection
local propCache = {}
local function propsOf(className)
	local c = propCache[className]
	if c then return c end
	c = {}
	local list = RFS:GetPropertiesOfClass(className)
	for _, p in ipairs(list or {}) do
		local t = p.Type or {}
		local perm = p.Permits or {}
		c[p.Name] = {st = t.ScriptType or t.EngineType, enum = t.EnumType, write = perm.Write ~= nil,
			read = perm.Read ~= nil, category = p.Display and p.Display.Category, owner = p.Owner}
	end
	propCache[className] = c
	return c
end
local function propInfo(inst, name)
	return propsOf(inst.ClassName)[name]
end

local classCache = {}
local function classExists(name)
	if type(name) ~= "string" or name == "" then return false end
	if classCache[name] ~= nil then return classCache[name] end
	local ok = RFS:GetClass(name) ~= nil
	classCache[name] = ok
	return ok
end

-- ---- JSON -> Roblox values, by the property's reflected type
local NUM = {float = true, double = true, int = true, int64 = true, number = true, int32 = true}
local function num(v) return type(v) == "number" and v or tonumber(v) end
local function arr(v, n)
	if type(v) ~= "table" then return nil end
	local out = {}
	for i = 1, n do
		local x = v[i]
		if x == nil then
			local keys = ({{"x", "X", "r", "R"}, {"y", "Y", "g", "G"}, {"z", "Z", "b", "B"}, {"w", "W"}})[i] or {}
			for _, k in ipairs(keys) do if v[k] ~= nil then x = v[k] break end end
		end
		x = num(x)
		if x == nil then return nil end
		out[i] = x
	end
	return out
end
local function color(v)
	if type(v) == "string" then
		local h = v:gsub("^#", "")
		if h:match("^%x%x%x%x%x%x$") then return Color3.fromHex(h) end
		return nil
	end
	local c = arr(v, 3)
	if not c then return nil end
	if c[1] > 1 or c[2] > 1 or c[3] > 1 then return Color3.fromRGB(c[1], c[2], c[3]) end
	return Color3.new(c[1], c[2], c[3])
end
local function enumItem(enumType, v)
	local E = enumType and Enum[enumType]
	if not E then return nil end
	if type(v) == "string" then
		local name = v:match("([%w_]+)$")
		for _, it in ipairs(E:GetEnumItems()) do
			if it.Name == name then return it end
		end
	elseif type(v) == "number" then
		for _, it in ipairs(E:GetEnumItems()) do
			if it.Value == v then return it end
		end
	end
	return nil
end
local function seq(v, conv)
	if type(v) ~= "table" or #v < 2 then return nil end
	local pts = {}
	for i, k in ipairs(v) do
		if type(k) ~= "table" then return nil end
		local t = num(k[1])
		local val = conv(k[2])
		if t == nil or val == nil then return nil end
		if (i == 1 and t ~= 0) or (i == #v and t ~= 1) then return nil end
		pts[#pts + 1] = {t, val, num(k[3]) or 0}
	end
	return pts
end

local function toValue(v, st, enumType)
	if st == "bool" or st == "boolean" then return v == true end
	if NUM[st] then return num(v) end
	if st == "string" or st == "Content" or st == "ContentId" then return v ~= nil and tostring(v) or nil end
	if st == "Vector3" then local a = arr(v, 3) return a and Vector3.new(a[1], a[2], a[3]) end
	if st == "Vector2" then local a = arr(v, 2) return a and Vector2.new(a[1], a[2]) end
	if st == "Vector3int16" then local a = arr(v, 3) return a and Vector3int16.new(a[1], a[2], a[3]) end
	if st == "Color3" then return color(v) end
	if st == "BrickColor" then return type(v) == "string" and BrickColor.new(v) or (type(v) == "number" and BrickColor.new(v)) or nil end
	if st == "EnumItem" or st == "Enum" then return enumItem(enumType, v) end
	if st == "UDim" then local a = arr(v, 2) return a and UDim.new(a[1], a[2]) end
	if st == "UDim2" then local a = arr(v, 4) return a and UDim2.new(a[1], a[2], a[3], a[4]) end
	if st == "Rect" then local a = arr(v, 4) return a and Rect.new(a[1], a[2], a[3], a[4]) end
	if st == "NumberRange" then
		if type(v) == "number" then return NumberRange.new(v) end
		local a = arr(v, 2)
		return a and a[1] <= a[2] and NumberRange.new(a[1], a[2]) or nil
	end
	if st == "NumberSequence" then
		if type(v) == "number" then return NumberSequence.new(v) end
		local pts = seq(v, num)
		if not pts then return nil end
		local kp = {}
		for _, p in ipairs(pts) do kp[#kp + 1] = NumberSequenceKeypoint.new(p[1], p[2], p[3]) end
		return NumberSequence.new(kp)
	end
	if st == "ColorSequence" then
		local c = color(v)
		if c then return ColorSequence.new(c) end
		local pts = seq(v, color)
		if not pts then return nil end
		local kp = {}
		for _, p in ipairs(pts) do kp[#kp + 1] = ColorSequenceKeypoint.new(p[1], p[2]) end
		return ColorSequence.new(kp)
	end
	if st == "CFrame" then
		if type(v) ~= "table" then return nil end
		if #v == 12 then
			local a = arr(v, 12)
			return a and CFrame.new(table.unpack(a))
		end
		if #v == 3 then local a = arr(v, 3) return a and CFrame.new(a[1], a[2], a[3]) end
		if #v == 6 then
			local a = arr(v, 6)
			return a and CFrame.new(a[1], a[2], a[3]) * CFrame.Angles(math.rad(a[4]), math.rad(a[5]), math.rad(a[6]))
		end
		local p = arr(v.position or v.pos or {0, 0, 0}, 3)
		if not p then return nil end
		local cf = CFrame.new(p[1], p[2], p[3])
		if v.lookAt then
			local l = arr(v.lookAt, 3)
			if l then cf = CFrame.lookAt(cf.Position, Vector3.new(l[1], l[2], l[3])) end
		elseif v.rotation or v.rot then
			local r = arr(v.rotation or v.rot, 3)
			if r then cf = cf * CFrame.Angles(math.rad(r[1]), math.rad(r[2]), math.rad(r[3])) end
		end
		return cf
	end
	if st == "PhysicalProperties" then
		if v == "default" or v == nil then return nil end
		local a = arr(v, 3)
		return a and PhysicalProperties.new(a[1], a[2], a[3]) or nil
	end
	if st == "Font" then
		if type(v) ~= "table" then return nil end
		local fam = v.family or v.Family
		if type(fam) ~= "string" then return nil end
		if not fam:find("/") then fam = "rbxasset://fonts/families/" .. fam .. ".json" end
		local w = enumItem("FontWeight", v.weight or "Regular") or Enum.FontWeight.Regular
		local s = enumItem("FontStyle", v.style or "Normal") or Enum.FontStyle.Normal
		return Font.new(fam, w, s)
	end
	if st == "Instance" or st == "Object" then
		local o = resolve(v)
		return o
	end
	return nil
end

local function toJson(v)
	local t = typeof(v)
	if t == "nil" or t == "boolean" or t == "number" or t == "string" then return v end
	if t == "Vector3" or t == "Vector3int16" then return {v.X, v.Y, v.Z} end
	if t == "Vector2" then return {v.X, v.Y} end
	if t == "Color3" then return "#" .. v:ToHex() end
	if t == "BrickColor" then return v.Name end
	if t == "EnumItem" then return tostring(v) end
	if t == "UDim" then return {v.Scale, v.Offset} end
	if t == "UDim2" then return {v.X.Scale, v.X.Offset, v.Y.Scale, v.Y.Offset} end
	if t == "CFrame" then return {v:GetComponents()} end
	if t == "Rect" then return {v.Min.X, v.Min.Y, v.Max.X, v.Max.Y} end
	if t == "NumberRange" then return {v.Min, v.Max} end
	if t == "NumberSequence" then
		local o = {}
		for _, k in ipairs(v.Keypoints) do o[#o + 1] = {k.Time, k.Value, k.Envelope} end
		return o
	end
	if t == "ColorSequence" then
		local o = {}
		for _, k in ipairs(v.Keypoints) do o[#o + 1] = {k.Time, "#" .. k.Value:ToHex()} end
		return o
	end
	if t == "Instance" then return v:GetFullName() end
	if t == "Font" then return {family = v.Family, weight = v.Weight.Name, style = v.Style.Name} end
	if t == "PhysicalProperties" then return {v.Density, v.Friction, v.Elasticity} end
	return tostring(v)
end

-- ReflectionService is NOT complete: it omits some properties outright (Script.Source is not listed at
-- all) and under-reports write permission (MaterialVariant.BaseMaterial says read-only and sets fine).
-- So reflection decides the TYPE when it knows it; when it does not, the current value is read (guarded)
-- and its own type is used; and "read-only" is only believed once a guarded write has actually failed.
local SCRIPT_TYPE = {number = "double", boolean = "bool"}
local function liveInfo(inst, name)
	if type(name) ~= "string" or name == "" then return nil end
	local ok, cur = pcall(function() return inst[name] end)
	if not ok or typeof(cur) == "RBXScriptSignal" or typeof(cur) == "function" then return nil end
	local t = typeof(cur)
	local info = {st = SCRIPT_TYPE[t] or t, read = true, write = true}
	if t == "EnumItem" then info.enum = tostring(cur.EnumType) end
	return info
end

local function getProp(inst, name)
	local info = propInfo(inst, name) or liveInfo(inst, name)
	if not info then return nil, ("%s has no property %s"):format(inst.ClassName, tostring(name)) end
	local ok, val = pcall(function() return inst[name] end)
	if not ok then return nil, tostring(val) end
	return val
end

local function setProp(inst, name, json)
	local info = propInfo(inst, name)
	if not info then
		info = liveInfo(inst, name)
		if not info then return false, ("%s has no property %s"):format(inst.ClassName, tostring(name)) end
	end
	local v = toValue(json, info.st, info.enum)
	if v == nil and not (info.st == "Instance" and json == nil) then
		return false, ("could not read %s as a %s%s"):format(HS:JSONEncode(json), tostring(info.st),
			info.enum and (" (" .. info.enum .. ")") or "")
	end
	local ok, e = pcall(function() inst[name] = v end)
	if not ok then
		return false, info.write and tostring(e) or ("%s.%s is read-only (%s)"):format(inst.ClassName, name, tostring(e))
	end
	return true
end

local function setProps(inst, props)
	local bad = {}
	for k, v in pairs(props or {}) do
		local ok, e = setProp(inst, k, v)
		if not ok then bad[#bad + 1] = e end
	end
	return bad
end

-- attribute values: primitives as they are, the rest by valueType or by shape
local function attrValue(v, valueType)
	if valueType then
		if valueType == "Color3" then return color(v) end
		return toValue(v, valueType, nil)
	end
	local t = type(v)
	if t == "number" or t == "boolean" or t == "string" then return v end
	if t == "table" then
		if #v == 3 then local a = arr(v, 3) return a and Vector3.new(a[1], a[2], a[3]) end
		if #v == 2 then local a = arr(v, 2) return a and Vector2.new(a[1], a[2]) end
		if #v == 4 then local a = arr(v, 4) return a and UDim2.new(a[1], a[2], a[3], a[4]) end
	end
	return nil
end

local CHS = game:GetService("ChangeHistoryService")
local function waypoint(name)
	pcall(function() CHS:SetWaypoint("Forge: " .. name) end)
end
