-- Heartbeat glide: reports the pose the way GModMovement would, so the server streams around a moving
-- player even when Studio is not rendering (RenderStepped does not fire then). Returns immediately.
local RS = game:GetService("ReplicatedStorage")
local Run = game:GetService("RunService")
local plr = game.Players.LocalPlayer
local hrp = plr.Character and plr.Character:FindFirstChild("HumanoidRootPart")
if not hrp then return "no hrp" end
local ev = RS:FindFirstChild("ChunkPos")
if not ev then return "no ChunkPos" end
local HEADING = _G.GLIDE_HEADING or 0
local SECS = _G.GLIDE_SECS or 15
local SPEED = _G.GLIDE_SPEED or 30
local dir = Vector3.new(math.cos(math.rad(HEADING)), 0, math.sin(math.rad(HEADING)))
local start = hrp.Position
local yaw = math.atan2(-dir.X, -dir.Z)
local t0 = os.clock()
local acc = 0
local root = workspace:FindFirstChild("Backrooms")
local built0 = 0
if root then for _, c in ipairs(root:GetChildren()) do if c:GetAttribute("Built") then built0 += 1 end end end
_G.GLIDE_DONE = nil
local conn
conn = Run.Heartbeat:Connect(function(dt)
	local t = os.clock() - t0
	if t > SECS then
		conn:Disconnect()
		local built = 0
		if root then for _, c in ipairs(root:GetChildren()) do if c:GetAttribute("Built") then built += 1 end end end
		_G.GLIDE_DONE = {secs = t, dist = (hrp.Position - start).Magnitude, built0 = built0, built1 = built}
		return
	end
	local p = start + dir * (SPEED * t)
	hrp.CFrame = CFrame.lookAt(p, p + dir)
	acc += dt
	if acc >= 1 / 20 then
		acc = 0
		ev:FireServer(p, false, yaw, dir * SPEED, true, 0, 1, false, false, 0, 0, false, false, false)
	end
end)
return "gliding"
