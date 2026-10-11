-- Seat a Model/BasePart by its lowest TRUE corner (not GetBoundingBox, which is in the
-- PrimaryPart's frame and lies for tilted roots). Optionally onto whatever is below it.
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
if not (root:IsA("Model") or root:IsA("BasePart")) then return {error = "not a Model or BasePart"} end

local list = root:GetDescendants()
if root:IsA("BasePart") then table.insert(list, root) end
local minY, sx, sz, n = math.huge, 0, 0, 0
for _, d in ipairs(list) do
	if d:IsA("BasePart") and d.Transparency < 0.99 then
		local h = d.Size / 2
		for _, s in ipairs({{1,1,1},{1,1,-1},{1,-1,1},{1,-1,-1},{-1,1,1},{-1,1,-1},{-1,-1,1},{-1,-1,-1}}) do
			local w = d.CFrame:PointToWorldSpace(Vector3.new(h.X * s[1], h.Y * s[2], h.Z * s[3]))
			if w.Y < minY then minY = w.Y end
		end
		sx += d.Position.X; sz += d.Position.Z; n += 1
	end
end
if n == 0 then return {error = "no visible parts"} end

local floorY = A.floor_y
local onto = "floor_y"
if floorY == nil then
	local params = RaycastParams.new()
	params.FilterType = Enum.RaycastFilterType.Exclude
	params.FilterDescendantsInstances = {root}
	local hit = workspace:Raycast(Vector3.new(sx / n, minY + 0.5, sz / n), Vector3.new(0, -200, 0), params)
	if not hit then return {error = "nothing below to seat on; pass floor_y"} end
	floorY = hit.Position.Y
	onto = hit.Instance:GetFullName()
end
local dy = floorY - minY
root:PivotTo(root:GetPivot() + Vector3.new(0, dy, 0))
return {path = root:GetFullName(), moved = dy, lowest_was = minY, onto = onto}
