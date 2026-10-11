"""Export the live title screen and render it over a stand-in for the blurred flythrough."""
import asyncio
import json
import sys

from mcp import Client
from mcp.client.stdio import StdioServerParameters
from mcp_types import TextContent


async def main(tag):
    params = StdioServerParameters(command=sys.executable, args=["server.py"])
    async with Client(params, read_timeout_seconds=180) as c:
        r = await c.call_tool("ui_export", {"path": "PlayerGui.MainMenu", "peer": "client",
                                            "save_to": f"test/live/menu_{tag}.json"})
        print("export error" if r.is_error else "exported")
        spec = json.load(open(f"test/live/menu_{tag}.json", encoding="utf-8"))
        # the blurred, desaturated Backrooms behind the menu: a warm wall wash, darker at the floor
        spec.setdefault("children", []).insert(0, {
            "name": "Backdrop", "type": "Frame", "props": {
                "Size": [1, 0, 1, 0], "BackgroundColor3": [128, 118, 74], "BorderSizePixel": 0, "ZIndex": 0},
            "children": [{"name": "G", "type": "UIGradient", "props": {
                "Rotation": 90,
                "Color": [[0, [92, 94, 70]], [0.55, [70, 72, 52]], [1, [34, 34, 26]]]}, "children": []}]})
        r = await c.call_tool("ui_render", {"spec": spec, "viewports": ["desktop"], "scale": 1,
                                            "save_to": f"test/live/menu_{tag}.png"})
        for b in r.content:
            if isinstance(b, TextContent):
                print(b.text[:1500])


asyncio.run(main(sys.argv[1] if len(sys.argv) > 1 else "rest"))
