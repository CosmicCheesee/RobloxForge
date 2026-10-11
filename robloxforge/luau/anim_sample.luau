-- Pose a rig at chosen times of an animation WITHOUT a playtest: a clone of the rig is put in a booth
-- far from the level, the clip is loaded on its Animator and stepped with Animator:StepAnimations,
-- and every part's CFrame (relative to the clone's root at rest) is read back. The clone is always
-- removed. Works in edit mode and does not need Studio to render.
-- args: rig (path), source (path to a KeyframeSequence / Animation, or an id: number or "rbxassetid://..."),
--       times = {...} or fps = n, speed = 1, inspect_only = bool
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

local function comps(cf)
	return {cf:GetComponents()}
end

-- ---- the clip
local src = A.source
local kfs, animId
if type(src) == "number" or (type(src) == "string" and (src:match("^%d+$") or src:match("^rbxassetid://"))) then
	animId = tostring(src)
	if not animId:match("^rbxassetid://") then animId = "rbxassetid://" .. animId end
else
	local o = resolve(src)
	if not o then return {error = "no animation at " .. tostring(src)} end
	if o:IsA("KeyframeSequence") then
		kfs = o
	elseif o:IsA("Animation") then
		animId = o.AnimationId
	else
		return {error = tostring(src) .. " is a " .. o.ClassName .. ", not a KeyframeSequence or Animation"}
	end
end
local KSP = game:GetService("KeyframeSequenceProvider")
if not kfs and animId and A.inspect_only then
	local ok, got = pcall(function() return KSP:GetKeyframeSequenceAsync(animId) end)
	if not ok then return {error = "could not load " .. animId .. ": " .. tostring(got)} end
	kfs = got
end

-- ---- inspect: what is in the clip
local function summary(k)
	if not k then return nil end
	local times, posed, markers, len = {}, {}, {}, 0
	for _, kf in ipairs(k:GetChildren()) do
		if kf:IsA("Keyframe") then
			times[#times + 1] = kf.Time
			len = math.max(len, kf.Time)
			for _, d in ipairs(kf:GetDescendants()) do
				if d:IsA("Pose") and d.Weight > 0 then posed[d.Name] = (posed[d.Name] or 0) + 1 end
				if d:IsA("KeyframeMarker") then markers[#markers + 1] = {t = kf.Time, name = d.Name, value = d.Value} end
			end
		end
	end
	table.sort(times)
	return {name = k.Name, loop = k.Loop, priority = k.Priority.Name, length = len, keyframes = times,
		posed = posed, markers = markers}
end
if A.inspect_only then
	return {clip = summary(kfs)}
end

local rig = resolve(A.rig)
if not rig then return {error = "no rig at " .. tostring(A.rig)} end
if kfs then
	local ok, id = pcall(function() return KSP:RegisterKeyframeSequence(kfs) end)
	if not ok then return {error = "could not register the KeyframeSequence: " .. tostring(id)} end
	animId = id
end

-- ---- the clone, in a booth
local booth = workspace:FindFirstChild("ForgeAnimBooth") or Instance.new("Folder")
booth.Name = "ForgeAnimBooth"
booth.Parent = workspace
local clone = rig:Clone()
if not clone then return {error = "rig cannot be cloned (Archivable false?)"} end
local root = clone.PrimaryPart or clone:FindFirstChild("HumanoidRootPart")
if not root then
	booth:Destroy()
	return {error = "rig has no PrimaryPart / HumanoidRootPart"}
end
clone.Parent = booth
local home = CFrame.new(0, 2000, 0)
clone:PivotTo(home * (root.CFrame:Inverse() * clone:GetPivot()))
for _, d in ipairs(clone:GetDescendants()) do
	if d:IsA("BasePart") then d.Anchored = (d == root) end
	if d:IsA("Script") or d:IsA("LocalScript") then d:Destroy() end
end
local owner = clone:FindFirstChildOfClass("Humanoid") or clone:FindFirstChildOfClass("AnimationController")
if not owner then
	owner = Instance.new("AnimationController")
	owner.Parent = clone
end
local animator = owner:FindFirstChildOfClass("Animator") or Instance.new("Animator")
animator.Parent = owner
local rootCF = root.CFrame

local anim = Instance.new("Animation")
anim.AnimationId = animId
local okLoad, track = pcall(function() return animator:LoadAnimation(anim) end)
if not okLoad or not track then
	booth:Destroy()
	return {error = "LoadAnimation failed: " .. tostring(track)}
end
local t0 = os.clock()
while track.Length == 0 and os.clock() - t0 < 4 do task.wait(0.05) end
if track.Length == 0 then
	booth:Destroy()
	return {error = "the clip never loaded (length 0) -- is the id an animation you can access?"}
end

local times = {}
if type(A.times) == "table" and #A.times > 0 then
	for _, t in ipairs(A.times) do times[#times + 1] = math.clamp(tonumber(t) or 0, 0, track.Length) end
else
	local fps = math.clamp(tonumber(A.fps) or 10, 1, 60)
	local n = math.max(1, math.floor(track.Length * fps + 0.5))
	for i = 0, n do times[#times + 1] = track.Length * i / n end
end
table.sort(times)

-- the parts and their looks, once
local partList, info = {}, {}
for _, d in ipairs(clone:GetDescendants()) do
	if d:IsA("BasePart") and d ~= root and d.Transparency < 0.99 then
		partList[#partList + 1] = d
		local shape = "Block"
		if d:IsA("Part") then
			if d.Shape == Enum.PartType.Cylinder then shape = "Cylinder"
			elseif d.Shape == Enum.PartType.Ball then shape = "Ball" end
		elseif d:IsA("WedgePart") then
			shape = "Wedge"
		end
		info[d.Name .. "#" .. #partList] = {size = {d.Size.X, d.Size.Y, d.Size.Z}, shape = shape, color = d.Color:ToHex(),
			name = d.Name}
	end
end
local joints, pairsOut = {}, {}
for _, d in ipairs(clone:GetDescendants()) do
	if d:IsA("Motor6D") then
		joints[#joints + 1] = d
		pairsOut[#pairsOut + 1] = {d.Name, d.Part0 and d.Part0.Name or "", d.Part1 and d.Part1.Name or ""}
	end
end

-- The REST floor: the lowest point of the rig in its bind pose, before anything plays. Taking it from
-- the first frame instead was wrong for any clip that starts mid-stride.
local restLow = math.huge
for _, p in ipairs(partList) do
	local cf, h = rootCF:ToObjectSpace(p.CFrame), p.Size / 2
	for _, x in ipairs({-h.X, h.X}) do
		for _, y in ipairs({-h.Y, h.Y}) do
			for _, z in ipairs({-h.Z, h.Z}) do
				restLow = math.min(restLow, (cf * Vector3.new(x, y, z)).Y)
			end
		end
	end
end

track:Play(0, 1, tonumber(A.speed) or 1)
-- A looped track stepped to exactly its length wraps to its first pose, which reads as a pop on the
-- last sample and hides the loop seam. Stop a millisecond short.
if track.Looped then
	for i, t in ipairs(times) do times[i] = math.min(t, track.Length - 0.001) end
end
local frames = {}
local now = 0
animator:StepAnimations(0)
for _, t in ipairs(times) do
	local dt = t - now
	if dt > 0 then animator:StepAnimations(dt) end
	now = t
	local fr = {t = t, parts = {}, joints = {}}
	for i, p in ipairs(partList) do
		fr.parts[p.Name .. "#" .. i] = comps(rootCF:ToObjectSpace(p.CFrame))
	end
	for _, j in ipairs(joints) do
		local rx, ry, rz = j.Transform:ToEulerAnglesXYZ()
		fr.joints[j.Name] = {math.deg(rx), math.deg(ry), math.deg(rz), j.Transform.Position.X, j.Transform.Position.Y, j.Transform.Position.Z}
	end
	frames[#frames + 1] = fr
end
track:Stop(0)
booth:Destroy()
return {length = track.Length, looped = track.Looped, frames = frames, parts = info, joints = pairsOut,
	rest_floor = restLow,
	root = root.Name, clip = summary(kfs)}
