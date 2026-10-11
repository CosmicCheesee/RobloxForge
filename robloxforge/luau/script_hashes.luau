-- Length + Adler-32 of every script in the synced services, keyed by full name. Edit peer only
-- (.Source needs plugin capability). Used to catch Studio-side edits Rojo has not overwritten.
local out = {}
local function adler(s)
	local a, b = 1, 0
	for i = 1, #s do
		a = (a + string.byte(s, i)) % 65521
		b = (b + a) % 65521
	end
	return b * 65536 + a
end
for _, r in ipairs({game.ReplicatedStorage, game.ServerScriptService, game.ServerStorage, game.StarterPlayer}) do
	for _, d in ipairs(r:GetDescendants()) do
		if d:IsA("LuaSourceContainer") then
			local src = d.Source
			out[d:GetFullName()] = {#src, adler(src)}
		end
	end
end
return out
