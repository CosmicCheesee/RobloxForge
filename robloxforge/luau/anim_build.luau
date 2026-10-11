-- Build a KeyframeSequence from a JSON spec against a rig's joint tree, save it, and register it so it
-- can be played straight away (the content id lasts for this Studio session).
-- spec: {name, loop, priority, keyframes = {{t, poses = {[PartName] = {pos = {x,y,z}, rot = {rx,ry,rz} (deg),
--        easing = "Linear|Constant|Elastic|Cubic|Bounce", dir = "In|Out|InOut"}}}}, markers = {{t, name, value}}}
-- A pose is the Part1 of a Motor6D, nested under its Part0's pose, the way the Animation Editor saves them.
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

local rig = resolve(A.rig)
if not rig then return {error = "no rig at " .. tostring(A.rig)} end
local spec = A.spec
if type(spec) ~= "table" or type(spec.keyframes) ~= "table" then return {error = "spec.keyframes is required"} end
local root = rig.PrimaryPart or rig:FindFirstChild("HumanoidRootPart")
if not root then return {error = "rig has no PrimaryPart / HumanoidRootPart"} end

-- the joint tree: parent part -> child parts
local kids, parentOf = {}, {}
for _, d in ipairs(rig:GetDescendants()) do
	if d:IsA("Motor6D") and d.Part0 and d.Part1 then
		kids[d.Part0] = kids[d.Part0] or {}
		table.insert(kids[d.Part0], d.Part1)
		parentOf[d.Part1.Name] = d.Part0
	end
end
local byName = {}
for _, d in ipairs(rig:GetDescendants()) do
	if d:IsA("BasePart") then byName[d.Name] = d end
end

local warnings = {}
local function enumItem(enum, name, default)
	if type(name) ~= "string" then return default end
	local ok, v = pcall(function() return enum[name] end)
	return (ok and v) or default
end

local kfs = Instance.new("KeyframeSequence")
kfs.Name = spec.name or "ForgeAnimation"
kfs.Loop = spec.loop == true
kfs.Priority = enumItem(Enum.AnimationPriority, spec.priority, Enum.AnimationPriority.Action)

for _, kf in ipairs(spec.keyframes) do
	local k = Instance.new("Keyframe")
	k.Time = tonumber(kf.t) or 0
	k.Parent = kfs
	local poses = kf.poses or {}
	-- which parts need a Pose: every posed part and all its ancestors up to the root
	local need = {}
	for name in pairs(poses) do
		if not byName[name] then
			warnings[#warnings + 1] = ("t=%.2f: no part named %q in the rig"):format(k.Time, name)
		else
			local p = byName[name]
			while p do
				need[p] = true
				p = parentOf[p.Name]
			end
		end
	end
	local function build(part, parentPose)
		if not need[part] then return end
		local pose = Instance.new("Pose")
		pose.Name = part.Name
		local spec1 = poses[part.Name]
		if spec1 then
			local pos = spec1.pos or {0, 0, 0}
			local rot = spec1.rot or {0, 0, 0}
			pose.CFrame = CFrame.new(pos[1], pos[2], pos[3])
				* CFrame.Angles(math.rad(rot[1]), math.rad(rot[2]), math.rad(rot[3]))
			pose.EasingStyle = enumItem(Enum.PoseEasingStyle, spec1.easing, Enum.PoseEasingStyle.Cubic)
			pose.EasingDirection = enumItem(Enum.PoseEasingDirection, spec1.dir, Enum.PoseEasingDirection.InOut)
			pose.Weight = 1
		else
			pose.Weight = 0           -- an ancestor present only to carry the hierarchy
		end
		pose.Parent = parentPose or k
		for _, c in ipairs(kids[part] or {}) do build(c, pose) end
	end
	build(root, nil)
	for _, m in ipairs(spec.markers or {}) do
		if math.abs((tonumber(m.t) or -1) - k.Time) < 1e-6 then
			local mk = Instance.new("KeyframeMarker")
			mk.Name = tostring(m.name or "Marker")
			mk.Value = tostring(m.value or "")
			mk.Parent = k
		end
	end
end

local saveTo = resolve(A.save_to or "ServerStorage")
if not saveTo then return {error = "no save target " .. tostring(A.save_to)} end
local folder = saveTo:FindFirstChild("ForgeAnimations")
if not folder then
	folder = Instance.new("Folder")
	folder.Name = "ForgeAnimations"
	folder.Parent = saveTo
end
local old = folder:FindFirstChild(kfs.Name)
if old and old:IsA("KeyframeSequence") then old:Destroy() end
kfs.Parent = folder
local okReg, id = pcall(function()
	return game:GetService("KeyframeSequenceProvider"):RegisterKeyframeSequence(kfs)
end)
local length = 0
for _, k in ipairs(kfs:GetChildren()) do
	if k:IsA("Keyframe") then length = math.max(length, k.Time) end
end
return {path = kfs:GetFullName(), contentId = okReg and id or nil, length = length,
	keyframes = #kfs:GetChildren(), warnings = warnings}
