"""Render + audit the menu prototypes offline. usage: run_menus.py <name|all> [round-tag]"""
import asyncio
import base64
import importlib
import sys

sys.path.insert(0, ".")
sys.path.insert(0, "test")
import robloxforge.server  # noqa: F401,E402
from robloxforge import ui_tools  # noqa: E402
import menus  # noqa: E402

importlib.reload(menus)
which = sys.argv[1] if len(sys.argv) > 1 else "all"
tag = sys.argv[2] if len(sys.argv) > 2 else "r1"


async def main():
    for name, (fn, theme) in menus.MENUS.items():
        if which not in ("all", name):
            continue
        out = await ui_tools.ui_render({"spec": fn(), "theme": theme, "viewports": ["desktop", "phone"],
                                        "save_to": f"test/menu_{name}_{tag}.png"})
        print(f"===== {name}\n{out[0].text}")


asyncio.run(main())
