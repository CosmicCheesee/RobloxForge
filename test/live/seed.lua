local RS = game:GetService("ReplicatedStorage")
local Loot = require(RS.LootDefs)
local plr = game.Players.LocalPlayer
local ids = {}
for _, id in ipairs({"slug","case","relay","bearing","bandage","shoprag","marker","wrench","speedloader","bat","clamp","pistolbody","snare","workorder"}) do
  if Loot.byId[id] then ids[#ids+1] = id end
end
local stash, bag, vault = {}, {}, {}
for i, id in ipairs(ids) do
  stash[#stash+1] = id .. ":" .. (40 + i * 13)
  if i <= 5 then bag[#bag+1] = id end
  vault[#vault+1] = id .. ":" .. (20 + i)
  if i % 3 == 0 then vault[#vault+1] = id .. ":" .. (20 + i) end
end
plr:SetAttribute("StashIds", table.concat(stash, ","))
plr:SetAttribute("BagIds", table.concat(bag, ","))
plr:SetAttribute("VaultIds", table.concat(vault, ","))
plr:SetAttribute("Balance", 6400)
plr:SetAttribute("BagKg", 17.5)
for i, r in ipairs(Loot.resources) do plr:SetAttribute("Res_" .. r.id, 6 + i * 5) end
for i, a in ipairs(Loot.abilities) do plr:SetAttribute("Ab_" .. a.id, ({5, 12, 0, 20})[i] or 3) end
plr:SetAttribute("Descent", 2)
plr:SetAttribute("DescentPick", 1)
plr:SetAttribute("Card_blue", 1)
return #ids
