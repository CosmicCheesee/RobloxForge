-- Export a Model/BasePart as a part list in the root's pivot space (same format model_build reads).
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

local root = resolve(A.path or "")
if not root then return {error = "not found: " .. tostring(A.path)} end
if not (root:IsA("Model") or root:IsA("BasePart")) then return {error = root.ClassName .. " is not a Model or BasePart"} end

local pivot = root:GetPivot()
local list = root:GetDescendants()
if root:IsA("BasePart") then table.insert(list, 1, root) end
local out, skipped = {}, 0
for _, d in ipairs(list) do
	if d:IsA("BasePart") then
		if #out >= (A.max or 2000) then skipped += 1; continue end
		local shape = "Block"
		if d:IsA("WedgePart") then shape = "Wedge"
		elseif d:IsA("CornerWedgePart") then shape = "CornerWedge"
		elseif d:IsA("Part") then
			if d.Shape == Enum.PartType.Cylinder then shape = "Cylinder"
			elseif d.Shape == Enum.PartType.Ball then shape = "Ball" end
		elseif d:IsA("MeshPart") or d:IsA("UnionOperation") then shape = "Mesh" end
		local rel = pivot:ToObjectSpace(d.CFrame)
		local rx, ry, rz = rel:ToEulerAnglesXYZ()
		local c = d.Color
		out[#out + 1] = {
			n = d.Name, shape = shape,
			sz = {d.Size.X, d.Size.Y, d.Size.Z},
			off = {rel.X, rel.Y, rel.Z},
			rot = {math.deg(rx), math.deg(ry), math.deg(rz)},
			color = {math.floor(c.R * 255 + 0.5), math.floor(c.G * 255 + 0.5), math.floor(c.B * 255 + 0.5)},
			mat = d.Material.Name, tr = d.Transparency,
		}
	end
end
local p = pivot.Position
return {path = root:GetFullName(), pivot = {p.X, p.Y, p.Z}, parts = out, skipped = skipped}
