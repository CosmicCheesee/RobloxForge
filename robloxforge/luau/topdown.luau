-- Floor-plan slice: every part whose bottom is under the cut height inside a square around a centre,
-- as XZ footprints. Ceilings (bottom above the cut) are left out so the plan is readable.
local HS = game:GetService("HttpService")
local A = HS:JSONDecode(__ARGS__)
local Players = game:GetService("Players")

-- centre: given, else the first player's live position (Pose attribute first -- see HANDOFF)
local cx, cz, cy = A.x, A.z, nil
local players = {}
for _, plr in ipairs(Players:GetPlayers()) do
	local ch = plr.Character
	local hrp = ch and ch:FindFirstChild("HumanoidRootPart")
	if hrp then
		local pos = hrp.Position
		local pose = hrp:GetAttribute("Pose")
		if typeof(pose) == "CFrame" then pos = pose.Position end
		local look = (typeof(pose) == "CFrame" and pose.LookVector) or hrp.CFrame.LookVector
		players[#players + 1] = {name = plr.Name, p = {pos.X, pos.Y, pos.Z}, look = {look.X, look.Z}}
		if cx == nil then cx, cz, cy = pos.X, pos.Z, pos.Y end
	end
end
if cx == nil then cx, cz = 0, 0 end
local cut = A.cut_y or ((cy or 3) + 2)
local R = A.radius or 120

local params = OverlapParams.new()
params.MaxParts = 0
local box = workspace:GetPartBoundsInBox(CFrame.new(cx, cut - 60, cz), Vector3.new(R * 2, 120, R * 2), params)
local out, dropped = {}, 0
for _, p in ipairs(box) do
	if p.Transparency < 0.95 then
		local h = p.Size / 2
		local cf = p.CFrame
		local bottom, top = math.huge, -math.huge
		local corners = {}
		for _, s in ipairs({{1,1},{1,-1},{-1,-1},{-1,1}}) do
			local w1 = cf:PointToWorldSpace(Vector3.new(h.X * s[1], h.Y, h.Z * s[2]))
			local w2 = cf:PointToWorldSpace(Vector3.new(h.X * s[1], -h.Y, h.Z * s[2]))
			bottom = math.min(bottom, w1.Y, w2.Y); top = math.max(top, w1.Y, w2.Y)
			corners[#corners + 1] = {w1.X, w1.Z}
		end
		if bottom <= cut then
			if #out < (A.max or 8000) then
				local c = p.Color
				local isChar = p:FindFirstAncestorOfClass("Model") and p:FindFirstAncestorOfClass("Model"):FindFirstChildOfClass("Humanoid")
				if not isChar then
					out[#out + 1] = {n = p.Name, c = {math.floor(c.R * 255), math.floor(c.G * 255), math.floor(c.B * 255)},
						b = bottom, t = top, xz = corners, a = p.Anchored}
				end
			else
				dropped += 1
			end
		end
	end
end
return {centre = {cx, cz}, cut = cut, radius = R, parts = out, dropped = dropped, players = players}
