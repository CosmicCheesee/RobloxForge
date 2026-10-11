-- Export a GUI subtree as a spec (props that differ from a fresh instance's defaults). The class and
-- property lists come from Python's whitelist, so every read is of a property that exists.
local HS = game:GetService("HttpService")
local A = HS:JSONDecode(__ARGS__)
local Players = game:GetService("Players")

local function resolve(path)
	local cur = game
	if string.sub(path, 1, 9) == "PlayerGui" then
		local lp = Players.LocalPlayer
		cur = lp and lp:FindFirstChild("PlayerGui")
		path = string.sub(path, 11)
	end
	for name in string.gmatch(path, "[^%.]+") do
		if not cur then return nil end
		if cur == game and name == "game" then continue end
		cur = cur:FindFirstChild(name)
	end
	return cur
end

local root = resolve(A.path or "")
if not root then return {error = "not found: " .. tostring(A.path)} end
local CLASSES = A.classes
if not CLASSES[root.ClassName] then return {error = root.ClassName .. " is not a supported UI class"} end

local function hex(c)
	return string.format("#%02x%02x%02x", math.floor(c.R * 255 + 0.5), math.floor(c.G * 255 + 0.5), math.floor(c.B * 255 + 0.5))
end
local function enc(t, v)
	if t == "udim2" then return {v.X.Scale, v.X.Offset, v.Y.Scale, v.Y.Offset}
	elseif t == "udim" then return {v.Scale, v.Offset}
	elseif t == "vec2" then return {v.X, v.Y}
	elseif t == "color" then return hex(v)
	elseif t == "enum" then return v.Name
	elseif t == "font" then
		local fam = string.match(v.Family, "families/([%w_]+)%.json") or "SourceSansPro"
		return {family = fam, weight = v.Weight.Name, style = v.Style.Name}
	elseif t == "cseq" then
		local out = {}
		for _, k in ipairs(v.Keypoints) do out[#out + 1] = {k.Time, hex(k.Value)} end
		return out
	elseif t == "nseq" then
		local out = {}
		for _, k in ipairs(v.Keypoints) do out[#out + 1] = {k.Time, k.Value} end
		return out
	end
	return v
end

local defaults, skipped, n = {}, 0, 0
local function export(inst, depth)
	local plist = CLASSES[inst.ClassName]
	if not plist then skipped += 1; return nil end
	n += 1
	if n > (A.max or 3000) then return nil end
	local d = defaults[inst.ClassName]
	if not d then d = Instance.new(inst.ClassName); defaults[inst.ClassName] = d end
	local props = {}
	for _, pt in ipairs(plist) do
		local name, t = pt[1], pt[2]
		local v = inst[name]
		local dv = d[name]
		local same = (t ~= "cseq" and t ~= "nseq") and v == dv
		if not same then props[name] = enc(t, v) end
	end
	local attrs
	for k, v in pairs(inst:GetAttributes()) do
		local tv = typeof(v)
		if tv == "string" or tv == "number" or tv == "boolean" then
			attrs = attrs or {}
			attrs[k] = v
		end
	end
	local kids = {}
	if depth < 40 then
		for _, c in ipairs(inst:GetChildren()) do
			local e = export(c, depth + 1)
			if e then kids[#kids + 1] = e end
		end
	end
	local node = {type = inst.ClassName, name = inst.Name, props = props, children = kids}
	if attrs then node.attrs = attrs end
	return node
end
local spec = export(root, 0)
for _, d in pairs(defaults) do d:Destroy() end
return {spec = spec, instances = n, skipped_non_ui = skipped}
