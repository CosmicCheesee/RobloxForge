"""One A/B sample: fresh playtest -> leave the title screen -> 15 s glide -> server script profile.

Works while Studio is not rendering: the glide reports the pose on Heartbeat (see glide.lua).
usage: ab_glide.py <label> [heading]
"""
import asyncio
import json
import re
import sys

from mcp import Client
from mcp.client.stdio import StdioServerParameters
from mcp_types import TextContent

EXIT_MENU = """local RS = game:GetService("ReplicatedStorage")
local plr = game.Players.LocalPlayer
task.wait(4)
RS.MenuDone:FireServer()
pcall(function() game:GetService("RunService"):UnbindFromRenderStep("MenuCam") end)
local mm = plr.PlayerGui:FindFirstChild("MainMenu") if mm then mm:Destroy() end
for _, n in ipairs({"MenuBlur", "MenuGrade"}) do local e = game.Lighting:FindFirstChild(n) if e then e:Destroy() end end
task.wait(6)
return tostring(plr:GetAttribute("InMenu"))"""

STATE = """local r = workspace:FindFirstChild("Backrooms") local c = r and r:FindFirstChild("Chunks")
local n, b = 0, 0 if c then for _, x in ipairs(c:GetChildren()) do n += 1 if x:GetAttribute("Built") then b += 1 end end end
return ("chunks=%d built=%d parked=%s"):format(n, b, tostring(workspace:GetAttribute("DetailParked")))"""


def texts(r):
    return " ".join(b.text for b in r.content if isinstance(b, TextContent))


async def main(label, heading):
    params = StdioServerParameters(command=sys.executable, args=["server.py"])
    async with Client(params, read_timeout_seconds=240) as c:
        await c.call_tool("solo_playtest", {"action": "stop"})
        await c.call_tool("solo_playtest", {"action": "start", "mode": "play", "timeout": 90})
        await c.call_tool("eval_client_runtime", {"code": EXIT_MENU})
        glide = open("test/live/glide.lua", encoding="utf-8").read()
        await c.call_tool("eval_client_runtime", {"code": f"_G.GLIDE_HEADING = {heading} _G.GLIDE_SECS = 15 " + glide})
        prof = texts(await c.call_tool("profile_summary", {"target": "server", "seconds": 14, "top": 8}))
        await asyncio.sleep(2)
        st = texts(await c.call_tool("eval_server_runtime", {"code": STATE}))
        tot = re.search(r"total Lua ([\d.]+)", prof)
        per = re.search(r"per script \(ms/s\): (.*)", prof)
        ds = re.search(r"DetailStreamer ([\d.]+)", prof)
        mg = re.search(r"MapGenerator ([\d.]+)", prof)
        print(json.dumps({"label": label, "heading": heading, "total": tot and float(tot.group(1)),
                          "DetailStreamer": ds and float(ds.group(1)), "MapGenerator": mg and float(mg.group(1)),
                          "scripts": per and per.group(1)[:300], "state": st[:300]}))
        await c.call_tool("solo_playtest", {"action": "stop"})


asyncio.run(main(sys.argv[1], float(sys.argv[2]) if len(sys.argv) > 2 else 0))
