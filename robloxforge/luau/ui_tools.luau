-- Small UI utilities, chosen by A.op:
--   isolate  {path}      hide every other ScreenGui in the same container (remembers who was on)
--   restore  {path}      undo isolate
--   tree     {path, depth}  compact outline: class, name, abs rect, visible, text
--   at       {x, y}       GuiObjects under a viewport point (client), top-most first
--   locate   {path}       viewport-pixel centre of a GuiObject, for clicking it
--   destroy  {path}
local HS = game:GetService("HttpService")
local A = HS:JSONDecode(__ARGS__)
local Players = game:GetService("Players")
local GuiService = game:GetService("GuiService")

local function resolve(path)
	local cur = game
	if string.sub(path, 1, 9) == "PlayerGui" then
		local lp = Players.LocalPlayer
		cur = lp and lp:FindFirstChild("PlayerGui")
		path = string.sub(path, 11)
	end
	for name in string.gmatch(path, "[^%.]+") do
		if not cur then return nil end
		if cur == game and name == "game" then continue end
		cur = cur:FindFirstChild(name)
	end
	return cur
end

local op = A.op
if op == "at" then
	local lp = Players.LocalPlayer
	local pg = lp and lp:FindFirstChild("PlayerGui")
	if not pg then return {error = "no PlayerGui (run on a playtest client)"} end
	local inset = GuiService:GetGuiInset()
	local hits = pg:GetGuiObjectsAtPosition(A.x, A.y - inset.Y)
	-- only what is actually on screen: every ancestor visible, its gui enabled
	local function shown(g)
		local cur = g
		while cur and cur ~= pg do
			if cur:IsA("GuiObject") and not cur.Visible then return false end
			if cur:IsA("LayerCollector") and not cur.Enabled then return false end
			cur = cur.Parent
		end
		return true
	end
	local out = {}
	for _, g in ipairs(hits) do
		if #out >= 15 then break end
		if shown(g) then
			out[#out + 1] = {path = g:GetFullName(), class = g.ClassName, active = g.Active,
				clickable = g:IsA("GuiButton") or g:IsA("TextBox")}
		end
	end
	return {hits = out}
end

local target = resolve(A.path or "")
if not target then return {error = "not found: " .. tostring(A.path)} end

if op == "destroy" then
	target:Destroy()
	return {destroyed = A.path}
end

if op == "isolate" or op == "restore" then
	local gui = target:IsA("LayerCollector") and target or target:FindFirstAncestorWhichIsA("LayerCollector")
	if not gui then return {error = "not inside a ScreenGui"} end
	local container = gui.Parent
	local n = 0
	for _, s in ipairs(container:GetChildren()) do
		if s:IsA("LayerCollector") and s ~= gui then
			if op == "isolate" then
				if s:GetAttribute("ForgeWasEnabled") == nil then s:SetAttribute("ForgeWasEnabled", s.Enabled) end
				s.Enabled = false
			else
				local was = s:GetAttribute("ForgeWasEnabled")
				if was ~= nil then s.Enabled = was; s:SetAttribute("ForgeWasEnabled", nil) end
			end
			n += 1
		end
	end
	if op == "isolate" then gui.Enabled = true end
	return {[op] = gui:GetFullName(), others = n}
end

if op == "locate" then
	if not target:IsA("GuiObject") then return {error = "not a GuiObject"} end
	local p, s = target.AbsolutePosition, target.AbsoluteSize
	-- AbsolutePosition is measured from below the topbar for every ScreenGui; screen = abs + inset
	local y = p.Y + s.Y / 2 + GuiService:GetGuiInset().Y
	return {x = math.floor(p.X + s.X / 2 + 0.5), y = math.floor(y + 0.5), w = s.X, h = s.Y,
		visible = target.Visible, active = target.Active}
end

if op == "tree" then
	local lines, maxd, count = {}, A.depth or 8, 0
	local function walk(o, d)
		count += 1
		if count > (A.max or 400) then return end
		local s = string.rep("  ", d) .. o.ClassName .. " " .. o.Name
		if o:IsA("GuiObject") then
			local p, z = o.AbsolutePosition, o.AbsoluteSize
			s ..= ("  [%d,%d %dx%d]"):format(p.X, p.Y, z.X, z.Y)
			if not o.Visible then s ..= " hidden" end
			if (o:IsA("TextLabel") or o:IsA("TextButton") or o:IsA("TextBox")) and o.Text ~= "" then
				s ..= "  \"" .. string.sub(o.Text, 1, 40) .. "\""
			end
		elseif o:IsA("LayerCollector") then
			s ..= o.Enabled and "  enabled" or "  DISABLED"
		end
		lines[#lines + 1] = s
		if d < maxd then for _, c in ipairs(o:GetChildren()) do walk(c, d + 1) end end
	end
	walk(target, 0)
	if count > (A.max or 400) then lines[#lines + 1] = ("... %d more"):format(count - (A.max or 400)) end
	return table.concat(lines, "\n")
end
return {error = "unknown op " .. tostring(op)}
