-- Build a normalized UI spec. Every class/property/enum was validated in Python (ui/schema.py), so the
-- only lookups left are the parent path and enum items -- both nil-checked, never indexed blind.
local HS = game:GetService("HttpService")
local A = HS:JSONDecode(__ARGS__)
local Players = game:GetService("Players")

local function resolve(path)
	if path == "PlayerGui" then
		local lp = Players.LocalPlayer
		return lp and lp:FindFirstChild("PlayerGui")
	end
	local cur = game
	for name in string.gmatch(path, "[^%.]+") do
		if not cur then return nil end
		if cur == game and name == "game" then continue end
		cur = cur:FindFirstChild(name)
	end
	return cur
end

local parent = resolve(A.parent or "StarterGui")
if not parent then return {error = "parent not found: " .. tostring(A.parent)} end

local enumCache, warns = {}, {}
local function enumItem(enumName, item)
	local t = enumCache[enumName]
	if not t then
		t = {}
		for _, e in ipairs(Enum[enumName]:GetEnumItems()) do t[e.Name] = e end
		enumCache[enumName] = t
	end
	return t[item]
end
local function rgb(c) return Color3.fromRGB(c[1], c[2], c[3]) end

local function value(p)
	local t = p[2]
	if t == "udim2" then local v = p[3]; return UDim2.new(v[1], v[2], v[3], v[4])
	elseif t == "udim" then return UDim.new(p[3][1], p[3][2])
	elseif t == "vec2" then return Vector2.new(p[3][1], p[3][2])
	elseif t == "color" then return rgb(p[3])
	elseif t == "num" or t == "bool" or t == "str" then return p[3]
	elseif t == "enum" then
		local e = enumItem(p[3], p[4])
		if not e then warns[#warns + 1] = ("Enum.%s.%s does not exist"):format(p[3], p[4]) end
		return e
	elseif t == "font" then
		return Font.new("rbxasset://fonts/families/" .. p[3] .. ".json",
			enumItem("FontWeight", p[4]) or Enum.FontWeight.Regular, enumItem("FontStyle", p[5]) or Enum.FontStyle.Normal)
	elseif t == "cseq" then
		local k = {}
		for _, s in ipairs(p[3]) do k[#k + 1] = ColorSequenceKeypoint.new(s[1], rgb(s[2])) end
		return ColorSequence.new(k)
	elseif t == "nseq" then
		local k = {}
		for _, s in ipairs(p[3]) do k[#k + 1] = NumberSequenceKeypoint.new(s[1], s[2]) end
		return NumberSequence.new(k)
	end
	return nil
end

local count = 0
local function build(n, par)
	local inst = Instance.new(n.type)
	inst.Name = n.name
	for _, p in ipairs(n.props) do
		local v = value(p)
		if v ~= nil then inst[p[1]] = v end
	end
	if n.attrs then
		for k, v in pairs(n.attrs) do inst:SetAttribute(k, v) end
	end
	for _, c in ipairs(n.children) do build(c, inst) end
	inst.Parent = par
	count += 1
	return inst
end

if A.replace then
	local old = parent:FindFirstChild(A.spec.name)
	if old then old:Destroy() end
end
local root = build(A.spec, parent)
if A.waypoint then
	game:GetService("ChangeHistoryService"):SetWaypoint("RobloxForge UI " .. root.Name)
end
return {path = root:GetFullName(), instances = count, warnings = warns}
