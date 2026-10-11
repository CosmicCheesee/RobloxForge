"""Render + audit hub facility remakes. usage: run_hub.py <direction: REFIT|OVERHAUL> <tag> [only-title]"""
import asyncio
import importlib
import sys

sys.path.insert(0, ".")
sys.path.insert(0, "test")
import robloxforge.server  # noqa: F401,E402
from robloxforge import ui_tools  # noqa: E402
from robloxforge.ui import components, render, schema, themes  # noqa: E402
import hub  # noqa: E402
import hub2  # noqa: E402
import hub3  # noqa: E402

importlib.reload(hub)
importlib.reload(hub2)
importlib.reload(hub3)
direction = sys.argv[1] if len(sys.argv) > 1 else "REFIT"
tag = sys.argv[2] if len(sys.argv) > 2 else "r1"
only = sys.argv[3] if len(sys.argv) > 3 else None


async def main():
    shots, labels = [], []
    for title, fn, theme in getattr({"OVERHAUL": hub2, "OVERHAUL2": hub3}.get(direction, hub), direction):
        if only and only != title:
            continue
        spec = fn()
        out = await ui_tools.ui_render({"spec": spec, "theme": theme, "viewports": [[1280, 720], "phone"]})
        lines = [l for l in out[0].text.splitlines() if l and not l.startswith("(")]
        print(f"===== {title}: " + " | ".join(l for l in lines if "RESULT" in l))
        for l in lines:
            if "RESULT" not in l:
                print("   ", l[:150])
        th = themes.load(theme)
        root = ui_tools._as_screen(schema.normalize(spec, schema.Resolver(th), components.expand))
        VP = tuple(int(x) for x in __import__("os").environ.get("HUB_VP", "1280x720").split("x"))
        img = render.render(root, VP, bg=tuple(schema.hex_rgb(th["color"]["bg"])))
        shots.append(img)
        labels.append(title)
    # 2 x 3 contact sheet of the desktop renders
    from PIL import Image, ImageDraw
    cw, chh = shots[0].size
    cols = 2
    rows = (len(shots) + cols - 1) // cols
    sheet = Image.new("RGB", (cols * cw + (cols + 1) * 20, rows * (chh + 40) + 20), (12, 12, 14))
    d = ImageDraw.Draw(sheet)
    for i, (im, lab) in enumerate(zip(shots, labels)):
        x = 20 + (i % cols) * (cw + 20)
        y = 20 + (i // cols) * (chh + 40)
        d.text((x, y), lab, fill=(230, 230, 230), font=render.pil_font("SourceSansPro", "SemiBold", 22))
        sheet.paste(im, (x, y + 30))
    sheet.save(f"test/hub_{direction}_{tag}.png")
    print("sheet", sheet.size)


asyncio.run(main())
