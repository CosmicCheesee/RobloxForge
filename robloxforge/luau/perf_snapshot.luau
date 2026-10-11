-- Client frame numbers over a window. Run on a playtest CLIENT. Reports whether the window is
-- focused: an unfocused Studio is throttled to exactly 60 fps (or 1x1 and not rendering at all),
-- and a number taken then is a phantom (HANDOFF trap 4).
local HS = game:GetService("HttpService")
local A = HS:JSONDecode(__ARGS__)
local RS = game:GetService("RunService")
local Stats = game:GetService("Stats")
local secs = math.clamp(A.seconds or 3, 0.5, 20)
local n, gpu, cpu, worst, last = 0, 0, 0, 0, os.clock()
local t0 = os.clock()
local c = RS.RenderStepped:Connect(function()
	local now = os.clock()
	worst = math.max(worst, now - last); last = now
	n += 1
	gpu += Stats.RenderGPUFrameTime; cpu += Stats.RenderCPUFrameTime
end)
task.wait(secs)
c:Disconnect()
local dt = os.clock() - t0
local cam = workspace.CurrentCamera
local vp = cam and cam.ViewportSize or Vector2.zero
local fps = n / dt
local warn
if vp.X <= 1 then warn = "viewport is 1x1: Studio is not rendering -- focus the game window"
elseif math.abs(fps - 60) < 1.5 then warn = "exactly ~60 fps: Studio window is probably unfocused (throttled)" end
local chunks = workspace:FindFirstChild("Backrooms") and workspace.Backrooms:FindFirstChild("Chunks")
return {
	fps = math.floor(fps * 10) / 10, worst_ms = math.floor(worst * 10000) / 10,
	gpu_ms = n > 0 and math.floor(gpu / n * 1e4) / 10 or 0, render_cpu_ms = n > 0 and math.floor(cpu / n * 1e4) / 10 or 0,
	draw_calls = Stats.SceneDrawcallCount, shadow_draw_calls = Stats.ShadowsDrawcallCount,
	triangles = Stats.SceneTriangleCount, instances = Stats.InstanceCount,
	memory_mb = math.floor(Stats:GetTotalMemoryUsageMb()), viewport = {vp.X, vp.Y},
	chunks = chunks and #chunks:GetChildren() or nil, warning = warn,
}
