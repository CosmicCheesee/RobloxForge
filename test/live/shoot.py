"""Open each hub facility on the live playtest client, export the real GUI tree, render it offline.

Studio is not drawing frames (remote session), so screenshots are impossible; the exported tree is the
game's own instances with their real properties, laid out by RobloxForge's offline renderer.
"""
import asyncio
import base64
import json
import sys

from mcp import Client
from mcp.client.stdio import StdioServerParameters
from mcp_types import ImageContent, TextContent

FACILITIES = ["ExtractLog", "CraftTerminal", "Vault", "Upgrades", "Market", "Squad"]
VP = [[1180, 760]]


async def call(c, name, args):
    r = await c.call_tool(name, args)
    texts = [b.text for b in r.content if isinstance(b, TextContent)]
    imgs = [b for b in r.content if isinstance(b, ImageContent)]
    if r.is_error:
        print(name, "ERROR", texts[:1])
    return texts, imgs


async def main(which):
    params = StdioServerParameters(command=sys.executable, args=["server.py"])
    async with Client(params, read_timeout_seconds=180) as c:
        t, _ = await call(c, "eval_client_runtime", {"code": open("test/live/seed.lua", encoding="utf-8").read()})
        print("seeded", t[:1])
        for fac in which:
            code = ("local lg = game.Players.LocalPlayer.PlayerGui.LootGui "
                    "for _, n in ipairs({'ExtractLog','CraftTerminal','Vault','Upgrades','Market','Squad'}) do lg[n].Visible = false end "
                    f"task.wait(0.15) lg['{fac}'].Visible = true task.wait(0.5) return lg.HubMenus.Card.Title.Text")
            t, _ = await call(c, "eval_client_runtime", {"code": code})
            print(fac, t[0][:120] if t else "")
            t, _ = await call(c, "ui_export", {"path": "PlayerGui.LootGui.HubMenus", "peer": "client",
                                               "save_to": f"test/live/{fac}.json"})
            spec = json.load(open(f"test/live/{fac}.json", encoding="utf-8"))
            t, imgs = await call(c, "ui_render", {"spec": spec, "viewports": VP, "scale": 1,
                                                  "save_to": f"test/live/{fac}.png"})
            print("\n".join(x[:600] for x in t))
        await call(c, "eval_client_runtime", {"code": "local lg = game.Players.LocalPlayer.PlayerGui.LootGui "
                   "for _, n in ipairs({'ExtractLog','CraftTerminal','Vault','Upgrades','Market','Squad'}) do lg[n].Visible = false end"})


asyncio.run(main(sys.argv[1:] or FACILITIES))
