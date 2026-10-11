-- Temporary photo booth around bounds: a neutral floor just under the model and three point lights
-- (key, fill, top), so a model in an unlit place does not photograph as a silhouette. remove=true
-- deletes it. Everything lives in one Folder, Workspace.ForgeBooth.
local HS = game:GetService("HttpService")
local A = HS:JSONDecode(__ARGS__)
local old = workspace:FindFirstChild("ForgeBooth")
if old then old:Destroy() end
if A.remove then return {removed = true} end

local lo, hi = A.lo, A.hi
local c = Vector3.new((lo[1] + hi[1]) / 2, (lo[2] + hi[2]) / 2, (lo[3] + hi[3]) / 2)
local span = Vector3.new(hi[1] - lo[1], hi[2] - lo[2], hi[3] - lo[3])
local r = math.max(span.Magnitude / 2, 1)

local f = Instance.new("Folder")
f.Name = "ForgeBooth"
if A.floor ~= false then
	local floor = Instance.new("Part")
	floor.Name = "BoothFloor"
	floor.Anchored = true
	floor.Size = Vector3.new(r * 8, 0.2, r * 8)
	floor.CFrame = CFrame.new(c.X, lo[2] - 0.1 - 0.02, c.Z)
	floor.Color = Color3.fromRGB(120, 120, 124)
	floor.Material = Enum.Material.SmoothPlastic
	floor.Parent = f
end
local function lamp(name, offset, bright)
	local p = Instance.new("Part")
	p.Name = name
	p.Anchored = true
	p.CanCollide = false
	p.CanQuery = false
	p.Transparency = 1
	p.Size = Vector3.new(0.2, 0.2, 0.2)
	p.CFrame = CFrame.new(c + offset)
	local l = Instance.new("PointLight")
	l.Range = math.min(60, r * 6)
	l.Brightness = bright
	l.Shadows = false
	l.Parent = p
	p.Parent = f
end
lamp("Key", Vector3.new(-r * 1.4, r * 1.6, -r * 1.6), 2.2)
lamp("Fill", Vector3.new(r * 1.6, r * 0.8, r * 1.2), 1.2)
lamp("Top", Vector3.new(0, r * 2.2, 0), 1.0)
f.Parent = workspace
return {booth = f:GetFullName()}
