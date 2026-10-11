"""Export any live PlayerGui and render it offline over a stand-in for the level.
usage: shoot_gui.py <PlayerGui.Name> <tag> [wall|dark]
`wall` is the hard case for a HUD: lit Backrooms wallpaper, where amber-on-yellow disappears."""
import asyncio
import json
import sys

from mcp import Client
from mcp.client.stdio import StdioServerParameters
from mcp_types import TextContent

BACKS = {
    "wall": [[0, [214, 196, 120]], [0.6, [190, 172, 100]], [1, [120, 104, 70]]],
    "dark": [[0, [92, 94, 70]], [0.55, [70, 72, 52]], [1, [34, 34, 26]]],
}


async def main(path, tag, back):
    params = StdioServerParameters(command=sys.executable, args=["server.py"])
    async with Client(params, read_timeout_seconds=180) as c:
        r = await c.call_tool("ui_export", {"path": path, "peer": "client", "save_to": f"test/live/{tag}.json"})
        print("export error" if r.is_error else "exported")
        spec = json.load(open(f"test/live/{tag}.json", encoding="utf-8"))
        spec.setdefault("props", {})["Enabled"] = True
        spec.setdefault("children", []).insert(0, {
            "name": "Backdrop", "type": "Frame", "props": {
                "Size": [1, 0, 1, 0], "BackgroundColor3": [128, 118, 74], "BorderSizePixel": 0, "ZIndex": 0},
            "children": [{"name": "G", "type": "UIGradient", "props": {"Rotation": 90, "Color": BACKS[back]},
                          "children": []}]})
        r = await c.call_tool("ui_render", {"spec": spec, "viewports": ["desktop"], "scale": 1,
                                            "save_to": f"test/live/{tag}.png"})
        for b in r.content:
            if isinstance(b, TextContent):
                print(b.text[:1200])


asyncio.run(main(sys.argv[1], sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else "wall"))
