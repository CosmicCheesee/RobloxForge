"""Parity: terrain, lighting (+ presets), particles, sound previews and effects, tweens, TextChatService,
MaterialService variants, HumanoidDescription, animation playback, and Stats profiling."""
from __future__ import annotations

from .parity import ANY, ARR, B, L, N, O, PATH, S

_MAT = r'''
local function terrainMaterial(name)
	local m = enumItem("Material", name or "Grass")
	return m
end
'''

# ---------------------------------------------------------------- terrain
L("terrain_fill_block", "Fill a block of terrain: cframe ([x,y,z] / 12 numbers / {position, rotation}), size [x,y,z], "
  "material (Enum.Material name).", {"cframe": ANY, "size": ARR, "material": S}, _MAT + r'''
local cf = toValue(A.cframe, "CFrame")
local s = arr(A.size, 3)
local m = terrainMaterial(A.material)
if not (cf and s and m) then return err("need cframe, size [x,y,z] and a valid material") end
workspace.Terrain:FillBlock(cf, Vector3.new(s[1], s[2], s[3]), m)
waypoint("terrain block")
return {filled = "block", material = m.Name}
''', ["cframe", "size", "material"])

L("terrain_fill_ball", "Fill a sphere of terrain.", {"center": ARR, "radius": N, "material": S}, _MAT + r'''
local c = arr(A.center, 3)
local m = terrainMaterial(A.material)
if not (c and tonumber(A.radius) and m) then return err("need center, radius and a valid material") end
workspace.Terrain:FillBall(Vector3.new(c[1], c[2], c[3]), tonumber(A.radius), m)
waypoint("terrain ball")
return {filled = "ball", material = m.Name}
''', ["center", "radius", "material"])

L("terrain_fill_wedge", "Fill a wedge of terrain (like a WedgePart).", {"cframe": ANY, "size": ARR, "material": S}, _MAT + r'''
local cf = toValue(A.cframe, "CFrame")
local s = arr(A.size, 3)
local m = terrainMaterial(A.material)
if not (cf and s and m) then return err("need cframe, size and a valid material") end
workspace.Terrain:FillWedge(cf, Vector3.new(s[1], s[2], s[3]), m)
waypoint("terrain wedge")
return {filled = "wedge", material = m.Name}
''', ["cframe", "size", "material"])

L("terrain_fill_cylinder", "Fill a cylinder of terrain (axis along the CFrame's Y).",
  {"cframe": ANY, "height": N, "radius": N, "material": S}, _MAT + r'''
local cf = toValue(A.cframe, "CFrame")
local m = terrainMaterial(A.material)
if not (cf and tonumber(A.height) and tonumber(A.radius) and m) then return err("need cframe, height, radius, material") end
workspace.Terrain:FillCylinder(cf, tonumber(A.height), tonumber(A.radius), m)
waypoint("terrain cylinder")
return {filled = "cylinder", material = m.Name}
''', ["cframe", "height", "radius", "material"])

L("terrain_clear", "Clear ALL terrain in the place (undoable in edit mode).", {"confirm": B}, r'''
if A.confirm ~= true then return err("terrain_clear removes every voxel -- pass confirm=true") end
workspace.Terrain:Clear()
waypoint("terrain clear")
return {cleared = true}
''', destructive=True)

L("terrain_get_materials", "Every Enum.Material usable as a terrain material.", {}, r'''
local out = {}
for _, m in ipairs(Enum.Material:GetEnumItems()) do
	local ok = pcall(function() workspace.Terrain:GetMaterialColor(m) end)
	if ok then out[#out + 1] = m.Name end
end
return {materials = out}
''', ro=True)

L("terrain_read_voxels", "Read a region of terrain (min, max corners): material histogram and filled volume. "
  "Resolution 4 (the voxel size).", {"min": ARR, "max": ARR}, r'''
local a, b = arr(A.min, 3), arr(A.max, 3)
if not (a and b) then return err("need min and max [x,y,z]") end
local lo = Vector3.new(math.min(a[1], b[1]), math.min(a[2], b[2]), math.min(a[3], b[3]))
local hi = Vector3.new(math.max(a[1], b[1]), math.max(a[2], b[2]), math.max(a[3], b[3]))
local size = hi - lo
if size.X * size.Y * size.Z > 4096 * 64 * 64 then return err("region too large (keep it under ~4M cubic studs)") end
local region = Region3.new(lo, hi):ExpandToGrid(4)
local mats, occ = workspace.Terrain:ReadVoxels(region, 4)
local hist, filled, total = {}, 0, 0
local sx, sy, sz = #mats, #mats[1], #mats[1][1]
for x = 1, sx do for y = 1, sy do for z = 1, sz do
	total += 1
	local o = occ[x][y][z]
	if o > 0 then
		local name = mats[x][y][z].Name
		hist[name] = (hist[name] or 0) + 1
		filled += o
	end
end end end
return {voxels = total, grid = {sx, sy, sz}, filledFraction = total > 0 and filled / total or 0, materials = hist}
''', ["min", "max"], ro=True)

# ---------------------------------------------------------------- lighting
_PRESETS = r'''
local PRESETS = {
	day = {ClockTime = 13, Brightness = 2, Ambient = "#8a8a8a", OutdoorAmbient = "#808080", FogEnd = 100000, ExposureCompensation = 0},
	dusk = {ClockTime = 18.2, Brightness = 1.2, Ambient = "#5a4a5a", OutdoorAmbient = "#6a5060", FogEnd = 2500, FogColor = "#c08a70"},
	night = {ClockTime = 0, Brightness = 0.3, Ambient = "#1c2030", OutdoorAmbient = "#202838", FogEnd = 800, FogColor = "#101622"},
	horror = {ClockTime = 0, Brightness = 0, Ambient = "#0c0c0c", OutdoorAmbient = "#000000", FogEnd = 120, FogColor = "#050505",
		ExposureCompensation = -0.4},
	studio = {ClockTime = 14, Brightness = 3, Ambient = "#a0a0a0", OutdoorAmbient = "#a0a0a0", FogEnd = 100000,
		EnvironmentDiffuseScale = 1, EnvironmentSpecularScale = 1},
	backrooms = {ClockTime = 12, Brightness = 0, Ambient = "#3a3626", OutdoorAmbient = "#000000", FogEnd = 140,
		FogStart = 20, FogColor = "#b8a868", ExposureCompensation = 0},
}
'''

L("lighting_get", "Lighting's properties and its post effects (Atmosphere, Bloom, ColorCorrection, Blur, SunRays, DoF, Sky).",
  {}, r'''
local L0 = game:GetService("Lighting")
local props = {}
for name, info in pairs(propsOf("Lighting")) do
	if info.read and info.write and name ~= "Parent" and name ~= "Name" and name ~= "Archivable"
		and name ~= "Capabilities" and name ~= "Sandboxed" then
		local v = getProp(L0, name)
		if v ~= nil then props[name] = toJson(v) end
	end
end
local fx = {}
for _, c in ipairs(L0:GetChildren()) do
	local e = {class = c.ClassName, name = c.Name}
	for name, info in pairs(propsOf(c.ClassName)) do
		if info.read and info.write and info.category ~= "Data" then
			local v = getProp(c, name)
			if v ~= nil then e[name] = toJson(v) end
		end
	end
	fx[#fx + 1] = e
end
return {lighting = props, effects = fx}
''', ro=True)

L("lighting_set", "Set Lighting properties in one undoable step: properties = {Brightness: 2, Ambient: '#404040', "
  "ClockTime: 14, Technology: 'Future', ...}.", {"properties": O}, r'''
local bad = setProps(game:GetService("Lighting"), A.properties)
waypoint("lighting")
return {set = true, problems = bad}
''', ["properties"])

L("lighting_list_presets", "The lighting presets lighting_set_preset knows.", {}, _PRESETS + r'''
local out = {}
for k, v in pairs(PRESETS) do out[k] = v end
return out
''', ro=True)

L("lighting_set_preset", "Apply a lighting preset: day, dusk, night, horror, studio, backrooms.", {"preset": S},
  _PRESETS + r'''
local p = PRESETS[A.preset]
if not p then return err("unknown preset " .. tostring(A.preset)) end
local bad = setProps(game:GetService("Lighting"), p)
waypoint("lighting preset")
return {applied = A.preset, problems = bad}
''', ["preset"])

# ---------------------------------------------------------------- particles
L("particle_create", "Create a ParticleEmitter with all its properties in one call (sequences as [[t, v], ...], "
  "ranges as [min, max], colours as '#hex' or [[t, '#hex'], ...]).", {"parentPath": PATH, "name": S, "properties": O}, r'''
local parent = resolve(A.parentPath)
if not parent then return err("no parent " .. tostring(A.parentPath)) end
local e = Instance.new("ParticleEmitter")
e.Name = A.name or "ParticleEmitter"
local bad = setProps(e, A.properties)
e.Parent = parent
waypoint("particles")
return {path = e:GetFullName(), problems = bad}
''', ["parentPath"])

L("particle_tune", "Change properties on an existing ParticleEmitter (same formats as particle_create).",
  {"emitterPath": PATH, "properties": O, "emit": N}, r'''
local e = resolve(A.emitterPath)
if not e or not e:IsA("ParticleEmitter") then return err("no ParticleEmitter at " .. tostring(A.emitterPath)) end
local bad = setProps(e, A.properties)
if tonumber(A.emit) then e:Emit(tonumber(A.emit)) end
waypoint("particles")
return {path = e:GetFullName(), problems = bad}
''', ["emitterPath"])

# ---------------------------------------------------------------- sound
L("sound_play_preview", "Play a sound by asset id through SoundService for a quick listen (removed after 60 s). "
  "Returns soundId for sound_stop_preview.", {"assetId": S, "volume": N, "speed": N, "looped": B}, r'''
local id = tostring(A.assetId or "")
if not id:match("^rbxassetid://") then id = "rbxassetid://" .. id:match("(%d+)") end
local s = Instance.new("Sound")
s.Name = "ForgePreview_" .. HS:GenerateGUID(false):sub(1, 8)
s.SoundId = id
s.Volume = tonumber(A.volume) or 0.5
s.PlaybackSpeed = tonumber(A.speed) or 1
s.Looped = A.looped == true
s.Parent = game:GetService("SoundService")
game:GetService("SoundService"):PlayLocalSound(s)
task.delay(60, function() if s.Parent then s:Destroy() end end)
local t0 = os.clock()
while not s.IsLoaded and os.clock() - t0 < 3 do task.wait(0.05) end
return {soundId = s.Name, loaded = s.IsLoaded, length = s.TimeLength}
''', ["assetId"], peer=False)

L("sound_stop_preview", "Stop a preview started by sound_play_preview.", {"soundId": S}, r'''
local s = game:GetService("SoundService"):FindFirstChild(tostring(A.soundId))
if not s then return {stopped = false, reason = "not found (already finished?)"} end
s:Stop()
s:Destroy()
return {stopped = true}
''', ["soundId"], peer=False)

L("sound_load_from_assetid", "Create a persistent Sound under a parent from an asset id.",
  {"parentPath": PATH, "assetId": S, "name": S, "volume": N, "looped": B}, r'''
local parent = resolve(A.parentPath)
if not parent then return err("no parent " .. tostring(A.parentPath)) end
local id = tostring(A.assetId or "")
if not id:match("^rbxassetid://") then id = "rbxassetid://" .. (id:match("(%d+)") or "") end
local s = Instance.new("Sound")
s.Name = A.name or "Sound"
s.SoundId = id
s.Volume = tonumber(A.volume) or 0.5
s.Looped = A.looped == true
s.Parent = parent
waypoint("sound")
return {path = s:GetFullName()}
''', ["parentPath", "assetId"])

L("sound_set_eq", "Add or update an EqualizerSoundEffect on a Sound (gains in dB).",
  {"soundPath": PATH, "lowGain": N, "midGain": N, "highGain": N, "enabled": B}, r'''
local s = resolve(A.soundPath)
if not s or not (s:IsA("Sound") or s:IsA("SoundGroup")) then return err("no Sound at " .. tostring(A.soundPath)) end
local eq = s:FindFirstChildOfClass("EqualizerSoundEffect") or Instance.new("EqualizerSoundEffect")
if tonumber(A.lowGain) then eq.LowGain = A.lowGain end
if tonumber(A.midGain) then eq.MidGain = A.midGain end
if tonumber(A.highGain) then eq.HighGain = A.highGain end
if A.enabled ~= nil then eq.Enabled = A.enabled == true end
eq.Parent = s
waypoint("eq")
return {path = eq:GetFullName(), low = eq.LowGain, mid = eq.MidGain, high = eq.HighGain}
''', ["soundPath"])

L("sound_set_reverb", "Add or update a ReverbSoundEffect on a Sound.",
  {"soundPath": PATH, "decayTime": N, "density": N, "diffusion": N, "dryLevel": N, "wetLevel": N, "enabled": B}, r'''
local s = resolve(A.soundPath)
if not s or not (s:IsA("Sound") or s:IsA("SoundGroup")) then return err("no Sound at " .. tostring(A.soundPath)) end
local r = s:FindFirstChildOfClass("ReverbSoundEffect") or Instance.new("ReverbSoundEffect")
for _, k in ipairs({"DecayTime", "Density", "Diffusion", "DryLevel", "WetLevel"}) do
	local key = string.lower(k:sub(1, 1)) .. k:sub(2)
	if tonumber(A[key]) then r[k] = tonumber(A[key]) end
end
if A.enabled ~= nil then r.Enabled = A.enabled == true end
r.Parent = s
waypoint("reverb")
return {path = r:GetFullName()}
''', ["soundPath"])

# ---------------------------------------------------------------- tween
L("tween_preview", "Run a TweenService tween on an instance to judge timing and easing: tweenInfo = {time, style, "
  "direction, repeatCount, reverses, delay}, goal = {Property: value}. revert=true puts the values back after.",
  {"targetPath": PATH, "tweenInfo": O, "goal": O, "revert": B}, r'''
local i = resolve(A.targetPath)
if not i then return err("no instance at " .. tostring(A.targetPath)) end
local ti = A.tweenInfo or {}
local info = TweenInfo.new(tonumber(ti.time) or 1, enumItem("EasingStyle", ti.style or "Quad") or Enum.EasingStyle.Quad,
	enumItem("EasingDirection", ti.direction or "Out") or Enum.EasingDirection.Out, tonumber(ti.repeatCount) or 0,
	ti.reverses == true, tonumber(ti.delay) or 0)
local goal, before = {}, {}
for k, v in pairs(A.goal or {}) do
	local p = propInfo(i, k)
	if not p or not p.write then return err(("%s has no writable property %s"):format(i.ClassName, k)) end
	local val = toValue(v, p.st, p.enum)
	if val == nil then return err("could not read the goal for " .. k) end
	goal[k] = val
	before[k] = i[k]
end
local tw = game:GetService("TweenService"):Create(i, info, goal)
tw:Play()
local t0 = os.clock()
while tw.PlaybackState ~= Enum.PlaybackState.Completed and os.clock() - t0 < (info.Time + info.DelayTime) * (info.RepeatCount + 1) * (info.Reverses and 2 or 1) + 2 do
	task.wait(0.05)
end
local after = {}
for k in pairs(goal) do after[k] = toJson(i[k]) end
if A.revert then for k, v in pairs(before) do i[k] = v end end
return {state = tostring(tw.PlaybackState), seconds = os.clock() - t0, reached = after, reverted = A.revert == true}
''', ["targetPath", "goal"], timeout=90)

# ---------------------------------------------------------------- text chat
L("textchat_configure", "Configure TextChatService: chatVersion, createDefaultCommands, createDefaultTextChannels, "
  "bubbleChat {props}, chatWindow {props}.", {"chatVersion": S, "createDefaultCommands": B,
  "createDefaultTextChannels": B, "bubbleChat": O, "chatWindow": O}, r'''
local T = game:GetService("TextChatService")
local bad = {}
if A.chatVersion then for _, e in ipairs(setProps(T, {ChatVersion = A.chatVersion})) do bad[#bad + 1] = e end end
if A.createDefaultCommands ~= nil then for _, e in ipairs(setProps(T, {CreateDefaultCommands = A.createDefaultCommands})) do bad[#bad + 1] = e end end
if A.createDefaultTextChannels ~= nil then for _, e in ipairs(setProps(T, {CreateDefaultTextChannels = A.createDefaultTextChannels})) do bad[#bad + 1] = e end end
local bc = T:FindFirstChildOfClass("BubbleChatConfiguration")
if A.bubbleChat and bc then for _, e in ipairs(setProps(bc, A.bubbleChat)) do bad[#bad + 1] = e end end
local cw = T:FindFirstChildOfClass("ChatWindowConfiguration")
if A.chatWindow and cw then for _, e in ipairs(setProps(cw, A.chatWindow)) do bad[#bad + 1] = e end end
waypoint("text chat")
return {chatVersion = tostring(T.ChatVersion), problems = bad}
''')

L("textchat_create_command", "Create a TextChatCommand (e.g. /dance).", {"name": S, "primaryAlias": S, "secondaryAlias": S,
  "autocompleteVisible": B, "enabled": B}, r'''
local T = game:GetService("TextChatService")
local folder = T:FindFirstChild("TextChatCommands") or Instance.new("Folder")
folder.Name = "TextChatCommands"
folder.Parent = T
local c = Instance.new("TextChatCommand")
c.Name = A.name or "Command"
c.PrimaryAlias = A.primaryAlias or ("/" .. string.lower(c.Name))
if A.secondaryAlias then c.SecondaryAlias = A.secondaryAlias end
if A.autocompleteVisible ~= nil then c.AutocompleteVisible = A.autocompleteVisible == true end
if A.enabled ~= nil then c.Enabled = A.enabled == true end
c.Parent = folder
waypoint("chat command")
return {path = c:GetFullName()}
''', ["name"])

L("textchat_list_channels", "TextChannels (and commands) under TextChatService.", {}, r'''
local T = game:GetService("TextChatService")
local ch, cmds = {}, {}
for _, d in ipairs(T:GetDescendants()) do
	if d:IsA("TextChannel") then ch[#ch + 1] = d:GetFullName() end
	if d:IsA("TextChatCommand") then cmds[#cmds + 1] = {path = d:GetFullName(), alias = d.PrimaryAlias} end
end
return {chatVersion = tostring(T.ChatVersion), channels = ch, commands = cmds}
''', ro=True)

# ---------------------------------------------------------------- materials
L("material_list_variants", "Every MaterialVariant in MaterialService, and which base materials are overridden.", {}, r'''
local MS = game:GetService("MaterialService")
local out = {}
for _, v in ipairs(MS:GetDescendants()) do
	if v:IsA("MaterialVariant") then
		out[#out + 1] = {name = v.Name, base = tostring(v.BaseMaterial), pattern = tostring(v.MaterialPattern), studsPerTile = v.StudsPerTile}
	end
end
return {variants = out}
''', ro=True)

L("search_materials", "Find MaterialVariants by name (substring).", {"query": S, "maxResults": N}, r'''
local q = string.lower(tostring(A.query or ""))
local out = {}
for _, v in ipairs(game:GetService("MaterialService"):GetDescendants()) do
	if v:IsA("MaterialVariant") and string.find(string.lower(v.Name), q, 1, true) then
		out[#out + 1] = {name = v.Name, base = tostring(v.BaseMaterial), path = v:GetFullName()}
		if #out >= (tonumber(A.maxResults) or 50) then break end
	end
end
return {results = out}
''', ro=True)

L("material_create_variant", "Create a MaterialVariant (texture maps are asset ids).",
  {"name": S, "baseMaterial": S, "materialPattern": S, "colorMap": S, "normalMap": S, "metalnessMap": S,
   "roughnessMap": S, "studsPerTile": N}, r'''
local v = Instance.new("MaterialVariant")
v.Name = A.name or "Variant"
local props = {BaseMaterial = A.baseMaterial or "Plastic", StudsPerTile = A.studsPerTile, MaterialPattern = A.materialPattern,
	ColorMap = A.colorMap, NormalMap = A.normalMap, MetalnessMap = A.metalnessMap, RoughnessMap = A.roughnessMap}
local bad = setProps(v, props)
v.Parent = game:GetService("MaterialService")
waypoint("material variant")
return {path = v:GetFullName(), problems = bad}
''', ["name", "baseMaterial"])

L("material_override_base", "Make a MaterialVariant the default look of a base material (e.g. every Grass part).",
  {"material": S, "variantName": S}, r'''
local MS = game:GetService("MaterialService")
local m = enumItem("Material", A.material)
if not m then return err("unknown material " .. tostring(A.material)) end
local ok, e = pcall(function() MS:SetBaseMaterialOverride(m, A.variantName or "") end)
if not ok then return err(tostring(e)) end
waypoint("material override")
return {material = m.Name, override = MS:GetBaseMaterialOverride(m)}
''', ["material"])

# ---------------------------------------------------------------- avatar
L("humanoid_description_apply", "Apply a HumanoidDescription to a Humanoid (server side of a playtest, or a rig in "
  "edit mode): description = {HeadColor: '#hex', Shirt: id, Pants: id, HatAccessory: 'id,id', BodyTypeScale: 0.3, ...}.",
  {"targetPath": PATH, "description": O}, r'''
local h = resolve(A.targetPath)
if h and h:IsA("Model") then h = h:FindFirstChildOfClass("Humanoid") end
if not h or not h:IsA("Humanoid") then return err("no Humanoid at " .. tostring(A.targetPath)) end
local ok0, desc = pcall(function() return h:GetAppliedDescription() end)
if not ok0 or not desc then desc = Instance.new("HumanoidDescription") end
local bad = setProps(desc, A.description)
local ok, e = pcall(function() h:ApplyDescription(desc) end)
if not ok then return err("ApplyDescription failed (it only works in a running game or on a rig Studio owns): " .. tostring(e)) end
return {applied = true, problems = bad}
''', ["targetPath", "description"], timeout=60)

# ---------------------------------------------------------------- animation playback (live)
L("animation_play", "Play an animation on a Humanoid / AnimationController (a running game, or edit mode -- where it "
  "is stepped for `seconds` so the pose can be seen). Returns trackId for animation_stop.",
  {"targetPath": PATH, "assetId": S, "fadeTime": N, "weight": N, "speed": N, "seconds": N}, r'''
local t = resolve(A.targetPath)
local owner = t and (t:IsA("Humanoid") or t:IsA("AnimationController")) and t
	or (t and (t:FindFirstChildOfClass("Humanoid") or t:FindFirstChildOfClass("AnimationController")))
if not owner then return err("no Humanoid / AnimationController at " .. tostring(A.targetPath)) end
local animator = owner:FindFirstChildOfClass("Animator") or Instance.new("Animator")
animator.Parent = owner
local id = tostring(A.assetId or "")
if id:match("^%d+$") then id = "rbxassetid://" .. id end
local anim = Instance.new("Animation")
anim.AnimationId = id
local tr = animator:LoadAnimation(anim)
local t0 = os.clock()
while tr.Length == 0 and os.clock() - t0 < 4 do task.wait(0.05) end
tr:Play(tonumber(A.fadeTime) or 0.1, tonumber(A.weight) or 1, tonumber(A.speed) or 1)
local trackId = "ForgeTrack_" .. HS:GenerateGUID(false):sub(1, 8)
anim.Name = trackId
anim.Parent = animator
if not game:GetService("RunService"):IsRunning() then
	local secs = math.clamp(tonumber(A.seconds) or 0, 0, 30)
	if secs > 0 then animator:StepAnimations(secs) end
end
return {trackId = trackId, length = tr.Length, looped = tr.Looped}
''', ["targetPath", "assetId"])

L("animation_stop", "Stop a track started by animation_play.", {"trackId": S, "fadeTime": N}, r'''
for _, a in ipairs(game:GetDescendants()) do
	if a:IsA("Animation") and a.Name == A.trackId then
		local animator = a.Parent
		for _, tr in ipairs(animator:GetPlayingAnimationTracks()) do
			if tr.Animation == a then tr:Stop(tonumber(A.fadeTime) or 0.1) end
		end
		a:Destroy()
		return {stopped = true}
	end
end
return {stopped = false, reason = "no track " .. tostring(A.trackId)}
''', ["trackId"])

L("animation_list_tracks", "AnimationTracks playing on a Humanoid / AnimationController.", {"targetPath": PATH}, r'''
local t = resolve(A.targetPath)
local owner = t and (t:IsA("Humanoid") or t:IsA("AnimationController")) and t
	or (t and (t:FindFirstChildOfClass("Humanoid") or t:FindFirstChildOfClass("AnimationController")))
local animator = owner and owner:FindFirstChildOfClass("Animator")
if not animator then return err("no Animator under " .. tostring(A.targetPath)) end
local out = {}
for _, tr in ipairs(animator:GetPlayingAnimationTracks()) do
	out[#out + 1] = {name = tr.Name, id = tr.Animation and tr.Animation.AnimationId, time = tr.TimePosition, length = tr.Length,
		speed = tr.Speed, weight = tr.WeightCurrent, priority = tostring(tr.Priority), looped = tr.Looped}
end
return {tracks = out}
''', ["targetPath"], ro=True)

L("animation_load_keyframes", "Build a KeyframeSequence from inline data under parentPath (flat form: keyframes = "
  "[{time, poses: {PartName: {cframe}}}]; poses are not nested -- use anim_build for a rig-aware sequence).",
  {"parentPath": PATH, "name": S, "keyframes": ARR, "loop": B}, r'''
local parent = resolve(A.parentPath or "ServerStorage")
if not parent then return err("no parent " .. tostring(A.parentPath)) end
local kfs = Instance.new("KeyframeSequence")
kfs.Name = A.name or "KeyframeSequence"
kfs.Loop = A.loop == true
for _, k in ipairs(A.keyframes or {}) do
	local kf = Instance.new("Keyframe")
	kf.Time = tonumber(k.time or k.t) or 0
	for part, p in pairs(k.poses or {}) do
		local pose = Instance.new("Pose")
		pose.Name = part
		local cf = toValue(p.cframe or p, "CFrame")
		if cf then pose.CFrame = cf end
		pose.Parent = kf
	end
	kf.Parent = kfs
end
kfs.Parent = parent
local ok, id = pcall(function() return game:GetService("KeyframeSequenceProvider"):RegisterKeyframeSequence(kfs) end)
waypoint("keyframes")
return {path = kfs:GetFullName(), contentId = ok and id or nil}
''', ["keyframes"])

# ---------------------------------------------------------------- Stats profiling (works on any peer)
_STATS = r'''
local St = game:GetService("Stats")
local function sample()
	local mem = {}
	for _, tag in ipairs({"Instances", "Script", "LuaHeap", "PhysicsCollision", "PhysicsParts", "GraphicsTexture",
		"GraphicsMeshParts", "Sounds", "Animation", "Gui", "Navigation", "TerrainVoxels"}) do
		local e = enumItem("DeveloperMemoryTag", tag)
		if e then mem[tag] = math.floor(St:GetMemoryUsageMbForTag(e) * 10) / 10 end
	end
	return {t = os.clock(), heartbeatMs = St.HeartbeatTimeMs, physicsMs = St.PhysicsStepTimeMs,
		instances = St.InstanceCount, primitives = St.PrimitivesCount, movingPrimitives = St.MovingPrimitivesCount,
		memoryMb = math.floor(St:GetTotalMemoryUsageMb()), dataReceiveKbps = St.DataReceiveKbps, dataSendKbps = St.DataSendKbps,
		memoryByTag = mem}
end
'''

L("profile_snapshot", "One Stats snapshot: heartbeat / physics ms, instance and primitive counts, total memory and "
  "memory by tag, network kbps.", {}, _STATS + "return sample()", ro=True)

L("profile_start", "Sample Stats every intervalMs in the background (on that peer) until profile_stop.",
  {"intervalMs": N}, _STATS + r'''
local key = "ForgeProfile"
_G[key] = {samples = {}, running = true, t0 = os.clock()}
local iv = math.clamp((tonumber(A.intervalMs) or 500) / 1000, 0.1, 10)
task.spawn(function()
	local st = _G[key]
	while st and st.running and #st.samples < 2000 do
		st.samples[#st.samples + 1] = sample()
		task.wait(iv)
	end
end)
return {started = true, interval = iv}
''')

L("profile_stop", "Stop the Stats capture and return the samples with averages.", {}, r'''
local st = _G.ForgeProfile
if not st then return err("no capture running (profile_start first)") end
st.running = false
_G.ForgeProfile = nil
local n = #st.samples
local hb, ph = 0, 0
for _, s in ipairs(st.samples) do hb += s.heartbeatMs; ph += s.physicsMs end
return {samples = n, seconds = os.clock() - st.t0, avgHeartbeatMs = n > 0 and hb / n or nil,
	avgPhysicsMs = n > 0 and ph / n or nil, data = st.samples}
''', ro=True)
