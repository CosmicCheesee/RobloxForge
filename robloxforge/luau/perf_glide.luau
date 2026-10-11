-- Glide the local body in a straight line at a fixed speed (through walls) and record frame times:
-- a repeatable "moving through fresh chunks" measurement. Pauses GModMovement and anchors the root
-- for the run, and ALWAYS puts both back. Keep runs under ~25 s: the eval bridge times out at ~30 s
-- and a killed run leaves the body anchored.
local HS = game:GetService("HttpService")
local A = HS:JSONDecode(__ARGS__)
local RS = game:GetService("RunService")
local plr = game:GetService("Players").LocalPlayer
local ch = plr and plr.Character
local hrp = ch and ch:FindFirstChild("HumanoidRootPart")
if not hrp then return {error = "no character root"} end
local gm = ch:FindFirstChild("GModMovement")
local secs = math.clamp(A.seconds or 12, 1, 25)
local speed = A.speed or 30
local ang = math.rad(A.heading or 0)
local dir = Vector3.new(math.cos(ang), 0, math.sin(ang))
local chunks = workspace:FindFirstChild("Backrooms") and workspace.Backrooms:FindFirstChild("Chunks")

local wasDisabled = gm and gm.Disabled
if gm then gm.Disabled = true end
local wasAnchored = hrp.Anchored
hrp.Anchored = true
local start = hrp.Position
local cam = workspace.CurrentCamera
local frames, buckets, arrived = {}, {}, 0
local t0, last = os.clock(), os.clock()
local ca = chunks and chunks.ChildAdded:Connect(function() arrived += 1 end)
local conn = RS.RenderStepped:Connect(function()
	local now = os.clock()
	frames[#frames + 1] = now - last; last = now
	local b = math.floor(now - t0) + 1
	buckets[b] = (buckets[b] or 0) + 1
	local p = start + dir * speed * (now - t0)
	hrp.CFrame = CFrame.lookAt(p, p + dir)
	if cam then cam.CFrame = CFrame.lookAt(p + Vector3.new(0, 1.5, 0), p + Vector3.new(0, 1.5, 0) + dir) end
end)
task.wait(secs)
conn:Disconnect()
if ca then ca:Disconnect() end
local dt = os.clock() - t0
hrp.Anchored = wasAnchored
if gm then gm.Disabled = wasDisabled end

table.sort(frames)
local n = #frames
if n == 0 then return {error = "no frames rendered -- Studio not focused/rendering"} end
local perSec, minSec = {}, math.huge
for i, v in ipairs(buckets) do
	perSec[i] = v
	if i < #buckets and v > 0 then minSec = math.min(minSec, v) end
end
return {
	fps = math.floor(n / dt * 10) / 10, worst_ms = math.floor(frames[n] * 10000) / 10,
	p99_ms = math.floor(frames[math.max(1, math.floor(n * 0.99))] * 10000) / 10,
	worst_second_fps = minSec ~= math.huge and minSec or nil, per_second = perSec,
	chunks_arrived = arrived, chunks_now = chunks and #chunks:GetChildren() or nil,
	from = {start.X, start.Y, start.Z}, heading = A.heading or 0, speed = speed,
}
