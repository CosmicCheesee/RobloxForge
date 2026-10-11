-- Build a Model from a part list. __ARGS__ is replaced with a JSON long-string by studio.py.
-- Inputs are validated in Python first; this still nil-checks every lookup, because Studio pauses
-- on any error inside an eval -- pcall included.
local HS = game:GetService("HttpService")
local A = HS:JSONDecode(__ARGS__)

local function resolve(path)
	local cur = game
	for name in string.gmatch(path, "[^%.]+") do
		if not cur then return nil end
		if cur == game and name == "game" then continue end
		cur = cur:FindFirstChild(name)
	end
	return cur
end

local parent = resolve(A.parent or "Workspace")
if not parent then return {error = "parent not found: " .. tostring(A.parent)} end

local mats = {}
for _, e in ipairs(Enum.Material:GetEnumItems()) do mats[e.Name] = e end

local model = Instance.new("Model")
model.Name = A.name or "ForgeModel"
local o = A.origin or {0, 0, 0}
local origin = CFrame.new(o[1], o[2], o[3])
local made, warns, primary, first = 0, {}, nil, nil

for i, p in ipairs(A.parts) do
	local shape = p.shape or "Block"
	local part
	if shape == "Wedge" then
		part = Instance.new("WedgePart")
	elseif shape == "CornerWedge" then
		part = Instance.new("CornerWedgePart")
	else
		part = Instance.new("Part")
		if shape == "Cylinder" then part.Shape = Enum.PartType.Cylinder
		elseif shape == "Ball" then part.Shape = Enum.PartType.Ball end
	end
	part.Name = p.n or ("Part" .. i)
	local sz = p.sz
	part.Size = Vector3.new(sz[1], sz[2], sz[3])
	local off, r = p.off or {0, 0, 0}, p.rot or {0, 0, 0}
	part.CFrame = origin * CFrame.new(off[1], off[2], off[3])
		* CFrame.Angles(math.rad(r[1]), math.rad(r[2]), math.rad(r[3]))
	if p.color then part.Color = Color3.fromRGB(p.color[1], p.color[2], p.color[3]) end
	if p.mat then
		local m = mats[p.mat]
		if m then part.Material = m else warns[#warns + 1] = "unknown material " .. tostring(p.mat) end
	end
	if p.tr then part.Transparency = p.tr end
	if p.refl then part.Reflectance = p.refl end
	if p.cc ~= nil then part.CanCollide = p.cc end
	part.Anchored = A.anchored ~= false
	part.TopSurface = Enum.SurfaceType.Smooth
	part.BottomSurface = Enum.SurfaceType.Smooth
	part.Parent = model
	first = first or part
	if p.primary then primary = part end
	made += 1
end

model.PrimaryPart = primary or first
model.Parent = parent
if A.waypoint then
	game:GetService("ChangeHistoryService"):SetWaypoint("RobloxForge build " .. model.Name)
end
return {path = model:GetFullName(), parts = made, warnings = warns}
