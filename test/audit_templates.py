"""Render + audit every template in every theme at every listed screen size; save dark/light/backroom sheets."""
import asyncio
import base64
import sys

sys.path.insert(0, ".")
import robloxforge.server  # noqa: F401,E402
from robloxforge import ui_tools  # noqa: E402
from robloxforge.ui import templates  # noqa: E402

SIZES = sys.argv[1].split(",") if len(sys.argv) > 1 else ["desktop", "laptop", "tablet", "phone", "small_phone", "phone_portrait"]
THEMES = ["modern-dark", "modern-light", "glass", "terminal", "backroom"]


async def main():
    bad = 0
    for name in sorted(templates.TPL):
        for th in THEMES:
            out = await ui_tools.ui_template({"name": name, "theme": th, "viewports": SIZES})
            res = [l for l in out[1].text.splitlines() if "RESULT" in l or "GLYPH" in l]
            if not all("clean" in r for r in res):
                bad += 1
                print(f"== {name} [{th}]:", out[1].text[:700])
            if th in ("modern-dark", "backroom", "modern-light"):
                open(f"test/tpl/{name}_{th}.png", "wb").write(base64.b64decode(out[2].data))
    print("combinations with findings:", bad, "of", len(templates.TPL) * len(THEMES), f"({len(SIZES)} screen sizes each)")


asyncio.run(main())
