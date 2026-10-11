-- World-space bounds of an instance from its parts' true corners, plus the current camera.
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
local list = root:GetDescendants()
if root:IsA("BasePart") then table.insert(list, root) end
local lo, hi = Vector3.new(math.huge, math.huge, math.huge), Vector3.new(-math.huge, -math.huge, -math.huge)
local n = 0
for _, d in ipairs(list) do
	if d:IsA("BasePart") then
		local h = d.Size / 2
		for _, s in ipairs({{1,1,1},{1,1,-1},{1,-1,1},{1,-1,-1},{-1,1,1},{-1,1,-1},{-1,-1,1},{-1,-1,-1}}) do
			local w = d.CFrame:PointToWorldSpace(Vector3.new(h.X * s[1], h.Y * s[2], h.Z * s[3]))
			lo = lo:Min(w); hi = hi:Max(w)
		end
		n += 1
	end
end
if n == 0 then return {error = "no parts under " .. root:GetFullName()} end
local cam = workspace.CurrentCamera
local cf = cam and cam.CFrame
return {
	lo = {lo.X, lo.Y, lo.Z}, hi = {hi.X, hi.Y, hi.Z}, parts = n,
	cam = cf and {cf:GetComponents()} or nil, fov = cam and cam.FieldOfView or 70,
	camType = cam and cam.CameraType.Name or "?",
}
