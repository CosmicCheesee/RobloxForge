-- UI QA on a live (laid-out) GUI: text overflow, tiny text, contrast, clipping, off-screen content,
-- colliding siblings, small touch targets, fixed-pixel layouts, invisible hit areas, and a census of
-- the design tokens in use. Never throws: every read is of a property the class is checked to have.
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

local root = resolve(A.path or "")
if not root then return {error = "not found: " .. tostring(A.path)} end
local cam = workspace.CurrentCamera
local vp = cam and cam.ViewportSize or Vector2.new(1280, 720)
local inset = GuiService:GetGuiInset()

local out, counts = {}, {}
local function flag(code, inst, msg)
	counts[code] = (counts[code] or 0) + 1
	if (counts[code] or 0) <= (A.per_code or 12) then
		out[#out + 1] = ("%-9s %s  %s"):format(code, inst:GetFullName(), msg)
	end
end

local function lin(c)
	if c <= 0.03928 then return c / 12.92 end
	return ((c + 0.055) / 1.055) ^ 2.4
end
local function lum(c) return 0.2126 * lin(c.R) + 0.7152 * lin(c.G) + 0.0722 * lin(c.B) end
local function contrast(a, b)
	local la, lb = lum(a), lum(b)
	if la < lb then la, lb = lb, la end
	return (la + 0.05) / (lb + 0.05)
end

local function shown(g)
	local cur = g
	while cur and cur ~= game do
		if cur:IsA("GuiObject") and not cur.Visible then return false end
		if cur:IsA("LayerCollector") then return cur.Enabled end
		cur = cur.Parent
	end
	return true
end

-- the colour actually behind a GuiObject: walk up to the first mostly-opaque background
local function backdrop(g)
	local cur = g
	while cur and cur:IsA("GuiObject") do
		if cur.BackgroundTransparency < 0.35 then return cur.BackgroundColor3, cur end
		cur = cur.Parent
	end
	-- no opaque ancestor: a menu often paints its background as a full-screen SIBLING behind the content.
	-- Accept an opaque top-level frame of the same gui that covers this object and sits behind it.
	local gui = g:FindFirstAncestorWhichIsA("LayerCollector")
	if gui then
		local p, s = g.AbsolutePosition, g.AbsoluteSize
		for _, c in ipairs(gui:GetChildren()) do
			if c:IsA("GuiObject") and c.Visible and c.BackgroundTransparency < 0.35 and not g:IsDescendantOf(c) then
				local cp, cs = c.AbsolutePosition, c.AbsoluteSize
				if cp.X <= p.X and cp.Y <= p.Y and cp.X + cs.X >= p.X + s.X and cp.Y + cs.Y >= p.Y + s.Y then
					return c.BackgroundColor3, c
				end
			end
		end
	end
	return nil, nil
end

local function scaleOf(g)
	local s, cur = 1, g
	while cur and cur ~= game do
		local u = cur:FindFirstChildOfClass("UIScale")
		if u then s *= u.Scale end
		cur = cur.Parent
	end
	return s
end

local function managed(p)
	return p and (p:FindFirstChildOfClass("UIListLayout") or p:FindFirstChildOfClass("UIGridLayout")
		or p:FindFirstChildOfClass("UIPageLayout") or p:FindFirstChildOfClass("UITableLayout"))
end

local tokens = {colors = {}, textSizes = {}, fonts = {}, radii = {}}
local function bump(t, k) t[k] = (t[k] or 0) + 1 end
local function hex(c)
	return string.format("#%02x%02x%02x", math.floor(c.R * 255 + 0.5), math.floor(c.G * 255 + 0.5), math.floor(c.B * 255 + 0.5))
end

local list = root:GetDescendants()
if root:IsA("GuiObject") then table.insert(list, 1, root) end
local n = 0
local perf = {canvas = 0, canvasPx = 0, scaled = 0, gradients = 0, scrolling = 0, objects = 0}
for _, g in ipairs(list) do
	if g:IsA("UICorner") then bump(tokens.radii, tostring(g.CornerRadius)) end
	if g:IsA("UIGradient") then perf.gradients += 1 end
	if g:IsA("GuiObject") then
		perf.objects += 1
		if g:IsA("CanvasGroup") then
			perf.canvas += 1
			perf.canvasPx += g.AbsoluteSize.X * g.AbsoluteSize.Y
		elseif g:IsA("ScrollingFrame") then
			perf.scrolling += 1
		end
		if (g:IsA("TextLabel") or g:IsA("TextButton") or g:IsA("TextBox")) and g.TextScaled then perf.scaled += 1 end
	end
	if g:IsA("GuiObject") and shown(g) then
		n += 1
		local pos, size = g.AbsolutePosition, g.AbsoluteSize
		if g.BackgroundTransparency < 1 then bump(tokens.colors, hex(g.BackgroundColor3)) end
		local isText = g:IsA("TextLabel") or g:IsA("TextButton") or g:IsA("TextBox")
		if isText and g.Text ~= "" then
			bump(tokens.textSizes, g.TextScaled and "scaled" or tostring(g.TextSize))
			bump(tokens.fonts, (string.match(g.FontFace.Family, "families/([%w_]+)") or "?") .. "/" .. g.FontFace.Weight.Name)
			bump(tokens.colors, hex(g.TextColor3))
			if not g.TextFits and not g.TextScaled then
				flag("OVERFLOW", g, ("text does not fit %dx%d (bounds %dx%d)"):format(size.X, size.Y, g.TextBounds.X, g.TextBounds.Y))
			end
			local px = (g.TextScaled and g.TextBounds.Y or g.TextSize) * scaleOf(g)
			if px < (A.min_text or 11) and g.TextTransparency < 0.9 then
				flag("TINY", g, ("text renders at ~%.0fpx"):format(px))
			end
			local bg = backdrop(g)
			if bg and g.TextTransparency < 0.5 then
				local r = contrast(g.TextColor3, bg)
				local need = (px >= 18 or (px >= 14 and g.FontFace.Weight.Value >= 600)) and 3 or 4.5
				-- a glyph icon (no letters or digits, at most two characters) is a graphic: WCAG 1.4.11 asks 3:1
				local glyphs = utf8.len(g.Text) or 99
				if glyphs <= 2 and not string.find(g.Text, "%w") then need = 3 end
				if r < need then flag("CONTRAST", g, ("%.2f:1 against %s (needs %.1f)"):format(r, hex(bg), need)) end
			elseif not bg and g.TextStrokeTransparency >= 1 and not g:FindFirstChildOfClass("UIStroke") then
				flag("NOBACKDROP", g, "text over the 3D world with no backdrop or stroke -- legibility depends on the scene")
			end
		end
		-- off-screen / clipped
		if size.X > 0 and size.Y > 0 then
			-- AbsolutePosition is measured from below the topbar for every ScreenGui; screen = abs + inset
			local x0, y0 = pos.X, pos.Y + inset.Y
			-- content inside a ScrollingFrame is meant to extend past the screen; judge the frame, not its rows
			local scrolled = g:FindFirstAncestorWhichIsA("ScrollingFrame") ~= nil
			if not scrolled and (x0 < -1 or y0 < -1 or x0 + size.X > vp.X + 1 or y0 + size.Y > vp.Y + 1) then
				flag("OFFSCREEN", g, ("rect %d,%d %dx%d vs viewport %dx%d"):format(x0, y0, size.X, size.Y, vp.X, vp.Y))
			end
			local p = g.Parent
			while p and p:IsA("GuiObject") do
				if p.ClipsDescendants and not p:IsA("ScrollingFrame") then
					local pp, ps = p.AbsolutePosition, p.AbsoluteSize
					if pos.X < pp.X - 1 or pos.Y < pp.Y - 1 or pos.X + size.X > pp.X + ps.X + 1 or pos.Y + size.Y > pp.Y + ps.Y + 1 then
						flag("CLIPPED", g, "partly cut off by " .. p.Name)
					end
					break
				end
				p = p.Parent
			end
		end
		-- Roblox does not draw Rotation under a clipping ancestor (ClipsDescendants or any ScrollingFrame):
		-- the object silently renders upright
		if g.Rotation % 360 ~= 0 then
			local p = g.Parent
			while p and p:IsA("GuiObject") do
				if p.ClipsDescendants or p:IsA("ScrollingFrame") then
					flag("ROTCLIP", g, ("Rotation %g is ignored inside clipping %s -- it renders upright"):format(g.Rotation, p.Name))
					break
				end
				p = p.Parent
			end
		end
		if (g:IsA("GuiButton") or g:IsA("TextBox")) and g.Active ~= false then
			if size.X < (A.min_touch or 32) or size.Y < (A.min_touch or 32) then
				flag("TOUCH", g, ("hit area %dx%d is small for touch (aim 44)"):format(size.X, size.Y))
			end
			local txt = isText and g.Text ~= "" and g.TextTransparency < 1
			local img = (g:IsA("ImageButton") and g.Image ~= "" and g.ImageTransparency < 1)
			if g.BackgroundTransparency >= 1 and not txt and not img and #g:GetChildren() == 0 then
				flag("INVISIBLE", g, "an invisible button (fine for a click-away scrim -- check it is meant)")
			end
		end
		local par = g.Parent
		if par and par:IsA("LayerCollector") and g.Size.X.Scale == 0 and g.Size.X.Offset > vp.X * 0.6 then
			flag("FIXED", g, ("%dpx wide in offset only -- will not fit a phone; use Scale + UISizeConstraint"):format(g.Size.X.Offset))
		end
	end
end

-- colliding siblings (outside layouts): partial overlaps between visible content of equal ZIndex
local function content(g)
	if not (g:IsA("GuiObject") and shown(g)) then return false end
	if g.BackgroundTransparency < 0.95 then return true end
	if (g:IsA("TextLabel") or g:IsA("TextButton") or g:IsA("TextBox")) and g.Text ~= "" then return true end
	return false
end
for _, parent in ipairs(list) do
	if (parent:IsA("GuiObject") or parent:IsA("LayerCollector")) and not managed(parent) then
		local kids = {}
		for _, c in ipairs(parent:GetChildren()) do if content(c) then kids[#kids + 1] = c end end
		for i = 1, #kids do
			for j = i + 1, #kids do
				local a, b = kids[i], kids[j]
				if a.ZIndex == b.ZIndex then
					local ap, as, bp, bs = a.AbsolutePosition, a.AbsoluteSize, b.AbsolutePosition, b.AbsoluteSize
					local ix = math.min(ap.X + as.X, bp.X + bs.X) - math.max(ap.X, bp.X)
					local iy = math.min(ap.Y + as.Y, bp.Y + bs.Y) - math.max(ap.Y, bp.Y)
					local aInB = ap.X >= bp.X and ap.Y >= bp.Y and ap.X + as.X <= bp.X + bs.X and ap.Y + as.Y <= bp.Y + bs.Y
					local bInA = bp.X >= ap.X and bp.Y >= ap.Y and bp.X + bs.X <= ap.X + as.X and bp.Y + bs.Y <= ap.Y + as.Y
					if ix > 4 and iy > 4 and not aInB and not bInA then
						flag("OVERLAP", a, ("overlaps %s by %dx%d at the same ZIndex"):format(b.Name, ix, iy))
					end
				end
			end
		end
	end
end

local function top(t, k)
	local arr = {}
	for name, v in pairs(t) do arr[#arr + 1] = {name, v} end
	table.sort(arr, function(a, b) return a[2] > b[2] end)
	local s = {}
	for i = 1, math.min(k, #arr) do s[#s + 1] = arr[i][1] .. " x" .. arr[i][2] end
	return #arr, table.concat(s, ", ")
end
local summary = {}
for code, c in pairs(counts) do summary[#summary + 1] = code .. "=" .. c end
table.sort(summary)
local nc, cs = top(tokens.colors, 8)
local nt, ts = top(tokens.textSizes, 8)
local nf, fs = top(tokens.fonts, 6)
local nr, rs = top(tokens.radii, 6)
table.insert(out, 1, ("UI audit of %s: %d visible objects, viewport %dx%d"):format(root:GetFullName(), n, vp.X, vp.Y))
out[#out + 1] = ("tokens  %d colours (%s)"):format(nc, cs)
out[#out + 1] = ("        %d text sizes (%s)"):format(nt, ts)
out[#out + 1] = ("        %d fonts (%s)"):format(nf, fs)
out[#out + 1] = ("        %d corner radii (%s)"):format(nr, rs)
out[#out + 1] = ("perf    %d GuiObjects, %d CanvasGroups (~%.1f Mpx of offscreen texture -- each one is its own render target), "
	.. "%d TextScaled (re-fits on every resize), %d gradients, %d scrolling frames"):format(perf.objects, perf.canvas,
	perf.canvasPx / 1e6, perf.scaled, perf.gradients, perf.scrolling)
out[#out + 1] = "RESULT  " .. (#summary > 0 and table.concat(summary, " ") or "clean")
return table.concat(out, "\n")
