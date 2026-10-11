-- Point the camera. In edit mode a plain CFrame write holds. In a playtest client the game's own
-- camera scripts rewrite it every frame, so we bind after them (and unbind on "release").
local HS = game:GetService("HttpService")
local A = HS:JSONDecode(__ARGS__)
local RunService = game:GetService("RunService")
local cam = workspace.CurrentCamera
if not cam then return {error = "no camera"} end

if A.release then
	if RunService:IsRunning() and RunService:IsClient() then RunService:UnbindFromRenderStep("ForgeShotCam") end
	if A.restore then
		cam.CFrame = CFrame.new(table.unpack(A.restore))
		if A.camType then
			for _, e in ipairs(Enum.CameraType:GetEnumItems()) do
				if e.Name == A.camType then cam.CameraType = e end
			end
		end
	end
	if A.fov then cam.FieldOfView = A.fov end
	return {released = true}
end

local cf = CFrame.lookAt(Vector3.new(A.eye[1], A.eye[2], A.eye[3]), Vector3.new(A.at[1], A.at[2], A.at[3]))
if RunService:IsRunning() and RunService:IsClient() then
	_G.ForgeShot = {cf = cf, fov = A.fov or 50}
	RunService:UnbindFromRenderStep("ForgeShotCam")
	RunService:BindToRenderStep("ForgeShotCam", Enum.RenderPriority.Last.Value + 5, function()
		local s = _G.ForgeShot
		if s then
			cam.CameraType = Enum.CameraType.Scriptable
			cam.CFrame = s.cf
			cam.FieldOfView = s.fov
		end
	end)
else
	cam.CameraType = Enum.CameraType.Scriptable
	cam.CFrame = cf
	cam.FieldOfView = A.fov or 50
end
return {ok = true}
