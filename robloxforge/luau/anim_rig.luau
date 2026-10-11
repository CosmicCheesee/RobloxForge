-- Rig utilities for the animation tools. Never throws: every branch returns {error = ...} instead.
--   op "audit"  {path}            joints, animator, problems
--   op "r6"     {at = {x,y,z}}    build a standard R6 test dummy under workspace.ForgeRigs
--   op "remove" {}                delete workspace.ForgeRigs
local HS = game:GetService("HttpService")
local A = HS:JSONDecode(__ARGS__)

local function resolve(path)
	if type(path) ~= "string" then return nil end
	local o = game
	for part in string.gmatch(path, "[^%.]+") do
		if not o then return nil end
		o = o:FindFirstChild(part)
	end
	return o
end

if A.op == "remove" then
	local f = workspace:FindFirstChild("ForgeRigs")
	if f then f:Destroy() end
	return {removed = f ~= nil}
end

if A.op == "r6" then
	local f = workspace:FindFirstChild("ForgeRigs") or Instance.new("Folder")
	f.Name = "ForgeRigs"
	f.Parent = workspace
	local at = A.at or {0, 1500, 0}
	local base = CFrame.new(at[1], at[2] + 3, at[3])
	local rig = Instance.new("Model")
	rig.Name = A.name or "R6Dummy"
	local function part(n, sz, off, col)
		local p = Instance.new("Part")
		p.Name = n
		p.Size = sz
		p.CFrame = base * CFrame.new(off)
		p.Anchored = false
		p.CanCollide = false
		p.Color = col
		p.Parent = rig
		return p
	end
	local skin, shirt, pants = Color3.fromRGB(234, 184, 146), Color3.fromRGB(88, 96, 112), Color3.fromRGB(52, 58, 72)
	local root = part("HumanoidRootPart", Vector3.new(2, 2, 1), Vector3.zero, Color3.new(1, 1, 1))
	root.Anchored = true
	root.Transparency = 1
	local torso = part("Torso", Vector3.new(2, 2, 1), Vector3.zero, shirt)
	local head = part("Head", Vector3.new(2, 1, 1), Vector3.new(0, 1.5, 0), skin)
	local la = part("Left Arm", Vector3.new(1, 2, 1), Vector3.new(-1.5, 0, 0), skin)
	local ra = part("Right Arm", Vector3.new(1, 2, 1), Vector3.new(1.5, 0, 0), skin)
	local ll = part("Left Leg", Vector3.new(1, 2, 1), Vector3.new(-0.5, -2, 0), pants)
	local rl = part("Right Leg", Vector3.new(1, 2, 1), Vector3.new(0.5, -2, 0), pants)
	local function m6(n, p0, p1, c0, c1)
		local m = Instance.new("Motor6D")
		m.Name = n
		m.Part0, m.Part1, m.C0, m.C1 = p0, p1, c0, c1
		m.Parent = p0
	end
	-- the standard R6 joint frames
	local R = CFrame.new(0, 0, 0, -1, 0, 0, 0, 0, 1, 0, 1, 0)
	m6("RootJoint", root, torso, R, R)
	m6("Neck", torso, head, CFrame.new(0, 1, 0, -1, 0, 0, 0, 0, 1, 0, 1, 0), CFrame.new(0, -0.5, 0, -1, 0, 0, 0, 0, 1, 0, 1, 0))
	m6("Right Shoulder", torso, ra, CFrame.new(1, 0.5, 0, 0, 0, 1, 0, 1, 0, -1, 0, 0), CFrame.new(-0.5, 0.5, 0, 0, 0, 1, 0, 1, 0, -1, 0, 0))
	m6("Left Shoulder", torso, la, CFrame.new(-1, 0.5, 0, 0, 0, -1, 0, 1, 0, 1, 0, 0), CFrame.new(0.5, 0.5, 0, 0, 0, -1, 0, 1, 0, 1, 0, 0))
	m6("Right Hip", torso, rl, CFrame.new(1, -1, 0, 0, 0, 1, 0, 1, 0, -1, 0, 0), CFrame.new(0.5, 1, 0, 0, 0, 1, 0, 1, 0, -1, 0, 0))
	m6("Left Hip", torso, ll, CFrame.new(-1, -1, 0, 0, 0, -1, 0, 1, 0, 1, 0, 0), CFrame.new(-0.5, 1, 0, 0, 0, -1, 0, 1, 0, 1, 0, 0))
	local hum = Instance.new("Humanoid")
	hum.RigType = Enum.HumanoidRigType.R6
	hum.Parent = rig
	Instance.new("Animator").Parent = hum
	rig.PrimaryPart = root
	rig.Parent = f
	return {path = rig:GetFullName()}
end

-- ---- audit
local rig = resolve(A.path)
if not rig then return {error = "no rig at " .. tostring(A.path)} end
local problems, joints, parts = {}, {}, 0
local hum = rig:FindFirstChildOfClass("Humanoid")
local ac = rig:FindFirstChildOfClass("AnimationController")
local owner = hum or ac
if not owner then problems[#problems + 1] = "no Humanoid or AnimationController -- nothing can play an animation" end
local animator = owner and owner:FindFirstChildOfClass("Animator")
if owner and not animator then problems[#problems + 1] = "no Animator under the " .. owner.ClassName .. " (one is created at runtime on the server for Humanoids, never for AnimationControllers)" end
local root = rig.PrimaryPart or rig:FindFirstChild("HumanoidRootPart")
if not root then problems[#problems + 1] = "no PrimaryPart / HumanoidRootPart" end
local seen1 = {}
for _, d in ipairs(rig:GetDescendants()) do
	if d:IsA("BasePart") then
		parts += 1
		if d.Anchored and d ~= root then
			problems[#problems + 1] = d.Name .. " is anchored -- an anchored part ignores its joint and will not animate"
		end
	elseif d:IsA("Motor6D") then
		local j = {name = d.Name, part0 = d.Part0 and d.Part0.Name, part1 = d.Part1 and d.Part1.Name}
		joints[#joints + 1] = j
		if not d.Part0 or not d.Part1 then problems[#problems + 1] = d.Name .. " has a nil Part0 or Part1" end
		if d.Part1 then
			if seen1[d.Part1] then problems[#problems + 1] = d.Part1.Name .. " is Part1 of two joints" end
			seen1[d.Part1] = true
		end
	elseif d:IsA("Weld") or d:IsA("WeldConstraint") then
		-- fine, but note welds on animated limbs
	end
end
-- every part should hang off the root through joints (or be welded to something that does)
local reach = {}
if root then
	reach[root] = true
	local changed = true
	while changed do
		changed = false
		for _, d in ipairs(rig:GetDescendants()) do
			if (d:IsA("Motor6D") or d:IsA("Weld") or d:IsA("WeldConstraint")) and d.Part0 and d.Part1 then
				if reach[d.Part0] and not reach[d.Part1] then reach[d.Part1] = true; changed = true end
				if reach[d.Part1] and not reach[d.Part0] then reach[d.Part0] = true; changed = true end
			end
		end
	end
	for _, d in ipairs(rig:GetDescendants()) do
		if d:IsA("BasePart") and not reach[d] then
			problems[#problems + 1] = d.Name .. " is not connected to the root by any joint -- it will not follow the animation"
		end
	end
end
return {path = rig:GetFullName(), parts = parts, joints = joints, owner = owner and owner.ClassName,
	animator = animator ~= nil, root = root and root.Name, problems = problems}
