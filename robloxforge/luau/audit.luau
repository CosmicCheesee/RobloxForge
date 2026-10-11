-- ===== ROBLOX VISUAL-PASS AUDIT =====
--
-- Numeric half of the visual pass. Paste into execute_luau (edit mode) or eval_client_runtime /
-- eval_server_runtime (play mode) after setting ROOT below. Returns a plain-text report.
--
-- Written to NEVER THROW: Studio pauses on errors inside evals even under pcall, so every lookup is
-- nil-checked and nothing here calls an API that can fail on a valid instance.
--
-- What it reports:
--   ZFIGHT   two same-facing flat faces closer than GAP that overlap in-plane (they will flicker)
--   FLOAT    parts (or groups of parts) not touching the rest of the model
--   HIDDEN   a part entirely inside another solid block (invisible; usually a mistake or waste)
--   GROUND   the model's lowest point vs the surface under it (hovering or sunk)
--   SKIPPED  parts the face test cannot judge exactly (meshes, wedges, balls) -- inspect these by eye

local ROOT = nil          -- set to an Instance, e.g. workspace:FindFirstChild("MyModel")
local ROOT_PATH = ""      -- or a dotted path from game, e.g. "Workspace.ItemBooth"; "" = use Selection
local GAP = 0.006         -- faces nearer than this fight at normal viewing distances
local TOUCH_TOL = 0.002   -- how close two parts must be to count as touching
local CHECK_GROUND = true -- also measure the gap to whatever is below the model
local SAMPLES = 7         -- per-side samples for the in-plane overlap test

local out = {}
local function say(s) out[#out + 1] = s end

-- ---------- find the root ----------
if not ROOT and ROOT_PATH ~= "" then
	local cur = game
	for name in string.gmatch(ROOT_PATH, "[^%.]+") do
		cur = cur and cur:FindFirstChild(name)
	end
	ROOT = cur
end
if not ROOT then
	local okSel, sel = pcall(function() return game:GetService("Selection"):Get() end)
	if okSel and type(sel) == "table" then ROOT = sel[1] end
end
if not ROOT then return "audit: no root (set ROOT or ROOT_PATH, or select the model)" end

-- ---------- collect parts ----------
local parts = {}
local skipped = {}
local list = ROOT:GetDescendants()
if ROOT:IsA("BasePart") then table.insert(list, ROOT) end
for _, d in ipairs(list) do
	if d:IsA("BasePart") and d.Transparency < 0.99 then
		local kind = "block"
		if d:IsA("Part") then
			if d.Shape == Enum.PartType.Cylinder then kind = "cyl"
			elseif d.Shape == Enum.PartType.Ball then kind = "ball"
			elseif d.Shape ~= Enum.PartType.Block then kind = "other" end
		elseif d:IsA("WedgePart") then kind = "wedge"
		elseif d:IsA("CornerWedgePart") then kind = "other"
		elseif d:IsA("MeshPart") or d:IsA("UnionOperation") then kind = "other"
		end
		if d:FindFirstChildWhichIsA("SpecialMesh") or d:FindFirstChildWhichIsA("BlockMesh") then kind = "other" end
		parts[#parts + 1] = {p = d, kind = kind, cf = d.CFrame, h = d.Size / 2}
		if kind == "other" or kind == "ball" or kind == "wedge" then
			skipped[#skipped + 1] = d.Name .. "(" .. kind .. ")"
		end
	end
end
say(("audit of %s: %d visible parts"):format(ROOT:GetFullName(), #parts))

-- ---------- faces ----------
local function axes(cf) return {cf.RightVector, cf.UpVector, cf.LookVector} end
local function faces(e)
	local res = {}
	if e.kind == "ball" or e.kind == "other" then return res end
	local A = axes(e.cf)
	local H = {e.h.X, e.h.Y, e.h.Z}
	local allow = {{1, -1}, {1, -1}, {1, -1}}
	if e.kind == "cyl" then allow = {{1, -1}, {}, {}} end          -- only the end caps are flat
	if e.kind == "wedge" then allow = {{1, -1}, {-1}, {-1}} end     -- sides, bottom, back (-LookVector)
	for i = 1, 3 do
		for _, sg in ipairs(allow[i]) do
			local n = A[i] * sg
			local j, k = (i % 3) + 1, ((i + 1) % 3) + 1
			res[#res + 1] = {n = n, c = e.cf.Position + n * H[i], U = A[j] * H[j], V = A[k] * H[k], e = e}
		end
	end
	return res
end

local function inside(pt, f)
	local d = pt - f.c
	local um, vm = f.U.Magnitude, f.V.Magnitude
	if um < 1e-6 or vm < 1e-6 then return false end
	return math.abs(d:Dot(f.U) / um) <= um + 1e-6 and math.abs(d:Dot(f.V) / vm) <= vm + 1e-6
end

local function overlapCount(a, b)
	local hits = 0
	for i = 0, SAMPLES - 1 do
		for j = 0, SAMPLES - 1 do
			local s = (i / (SAMPLES - 1)) * 2 - 1
			local t = (j / (SAMPLES - 1)) * 2 - 1
			if inside(a.c + a.U * s * 0.96 + a.V * t * 0.96, b) then hits += 1 end
		end
	end
	return hits
end

local allFaces = {}
for _, e in ipairs(parts) do
	for _, f in ipairs(faces(e)) do allFaces[#allFaces + 1] = f end
end

local zf = 0
for i = 1, #allFaces do
	local a = allFaces[i]
	for j = i + 1, #allFaces do
		local b = allFaces[j]
		if a.e ~= b.e and a.n:Dot(b.n) > 0.999 then
			local dist = math.abs((b.c - a.c):Dot(a.n))
			if dist < GAP then
				local k = math.max(overlapCount(a, b), overlapCount(b, a))
				if k > 0 then
					zf += 1
					if zf <= 40 then
						say(("ZFIGHT  %s / %s  %.4f apart, %d/%d samples overlap%s"):format(a.e.p.Name, b.e.p.Name,
							dist, k, SAMPLES * SAMPLES,
							(a.e.kind ~= "block" or b.e.kind ~= "block") and "  (non-block: confirm by eye)" or ""))
					end
				end
			end
		end
	end
end
if zf > 40 then say(("ZFIGHT  ...and %d more"):format(zf - 40)) end

-- ---------- touching (OBB separating-axis test) ----------
local function touching(a, b)
	local Aa, Ab = axes(a.cf), axes(b.cf)
	local ha, hb = {a.h.X, a.h.Y, a.h.Z}, {b.h.X, b.h.Y, b.h.Z}
	local d = b.cf.Position - a.cf.Position
	local test = {Aa[1], Aa[2], Aa[3], Ab[1], Ab[2], Ab[3]}
	for i = 1, 3 do
		for j = 1, 3 do
			local c = Aa[i]:Cross(Ab[j])
			if c.Magnitude > 1e-5 then test[#test + 1] = c.Unit end
		end
	end
	for _, L in ipairs(test) do
		local ra = math.abs(L:Dot(Aa[1])) * ha[1] + math.abs(L:Dot(Aa[2])) * ha[2] + math.abs(L:Dot(Aa[3])) * ha[3]
		local rb = math.abs(L:Dot(Ab[1])) * hb[1] + math.abs(L:Dot(Ab[2])) * hb[2] + math.abs(L:Dot(Ab[3])) * hb[3]
		if math.abs(d:Dot(L)) > ra + rb + TOUCH_TOL then return false end
	end
	return true
end

local parent = {}
for i = 1, #parts do parent[i] = i end
local function find(i) while parent[i] ~= i do parent[i] = parent[parent[i]]; i = parent[i] end return i end
for i = 1, #parts do
	for j = i + 1, #parts do
		if touching(parts[i], parts[j]) then parent[find(i)] = find(j) end
	end
end
local groups, order = {}, {}
for i = 1, #parts do
	local r = find(i)
	if not groups[r] then groups[r] = {}; order[#order + 1] = r end
	table.insert(groups[r], parts[i].p.Name)
end
if #order > 1 then
	table.sort(order, function(x, y) return #groups[x] > #groups[y] end)
	for gi = 2, #order do
		say(("FLOAT   not attached to the main body: %s"):format(table.concat(groups[order[gi]], ", ")))
	end
end

-- ---------- hidden inside another block ----------
local hidden = 0
for i, a in ipairs(parts) do
	for j, b in ipairs(parts) do
		if i ~= j and b.kind == "block" then
			local allIn = true
			for _, sx in ipairs({-1, 1}) do
				for _, sy in ipairs({-1, 1}) do
					for _, sz in ipairs({-1, 1}) do
						local corner = a.cf * Vector3.new(sx * a.h.X, sy * a.h.Y, sz * a.h.Z)
						local l = b.cf:PointToObjectSpace(corner)
						if math.abs(l.X) > b.h.X + 1e-4 or math.abs(l.Y) > b.h.Y + 1e-4 or math.abs(l.Z) > b.h.Z + 1e-4 then
							allIn = false
						end
					end
				end
			end
			if allIn then
				hidden += 1
				if hidden <= 20 then say(("HIDDEN  %s is entirely inside %s"):format(a.p.Name, b.p.Name)) end
				break
			end
		end
	end
end

-- ---------- ground ----------
if CHECK_GROUND and #parts > 0 then
	local minY, sum = math.huge, Vector3.zero
	for _, e in ipairs(parts) do
		local A = axes(e.cf)
		local ext = math.abs(A[1].Y) * e.h.X + math.abs(A[2].Y) * e.h.Y + math.abs(A[3].Y) * e.h.Z
		minY = math.min(minY, e.cf.Position.Y - ext)
		sum += e.cf.Position
	end
	local centre = sum / #parts
	local params = RaycastParams.new()
	params.FilterType = Enum.RaycastFilterType.Exclude
	params.FilterDescendantsInstances = {ROOT}
	local hit = workspace:Raycast(Vector3.new(centre.X, minY + 0.5, centre.Z), Vector3.new(0, -50, 0), params)
	if hit then
		local gap = minY - hit.Position.Y
		if math.abs(gap) > 0.02 then
			say(("GROUND  lowest point is %.3f %s %s under it"):format(math.abs(gap), gap > 0 and "ABOVE" or "BELOW",
				hit.Instance.Name))
		else
			say(("ground  rests on %s (%.3f)"):format(hit.Instance.Name, gap))
		end
	else
		say("ground  nothing below within 50 studs (fine for a held item or a booth-less test)")
	end
end

if #skipped > 0 then
	say("SKIPPED (inspect by eye): " .. table.concat(skipped, ", "))
end
say(("RESULT  %d z-fight pair(s), %d floating group(s), %d hidden part(s)"):format(zf, math.max(#order - 1, 0), hidden))
return table.concat(out, "\n")
