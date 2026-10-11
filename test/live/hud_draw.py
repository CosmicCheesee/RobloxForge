"""Draw the live HUD dump (AbsolutePosition/Size/Rotation of the real instances) with PIL.

RobloxForge's offline renderer does not model Rotation and the load arc is built from rotated frames,
so this draws the dumped instances directly: rotated rects, rounded rects, strokes, text.
"""
import json
import math
import sys

from PIL import Image, ImageDraw, ImageFont

SS = 2  # supersample


def font(size, bold=False):
    for name in (["consolab.ttf"] if bold else []) + ["consola.ttf"]:
        try:
            return ImageFont.truetype(f"C:/Windows/Fonts/{name}", size)
        except OSError:
            pass
    return ImageFont.load_default()


def rgba(hexs, t):
    h = hexs.lstrip("#")
    return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16), int(round(255 * (1 - t))))


def backdrop(w, h):
    im = Image.new("RGBA", (w, h))
    d = ImageDraw.Draw(im)
    for y in range(h):
        k = y / h
        c = (int(150 - 40 * k), int(138 - 38 * k), int(78 - 24 * k), 255)
        d.line([(0, y), (w, y)], fill=c)
    # faint wallpaper stripes
    for x in range(0, w, 18 * SS):
        d.line([(x, 0), (x, h)], fill=(120, 110, 60, 255), width=SS)
    return im


def draw_scene(items, origin, size, pad=30):
    ox, oy = origin
    W, H = (size[0] + 2 * pad) * SS, (size[1] + 2 * pad) * SS
    base = backdrop(W, H)
    for e in sorted((i for i in items if i["c"] != "Root"), key=lambda i: i.get("z", 0)):
        layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        d = ImageDraw.Draw(layer)
        x, y = (e["x"] - ox + pad) * SS, (e["y"] - oy + pad) * SS
        w, h = e["w"] * SS, e["h"] * SS
        r = e.get("r") or 0
        if e.get("bt", 1) < 0.999:
            fill = rgba(e["bg"], e["bt"])
            if abs(r) > 0.01:
                cx, cy = x + w / 2, y + h / 2
                a = math.radians(r)
                pts = []
                for dx, dy in ((-w / 2, -h / 2), (w / 2, -h / 2), (w / 2, h / 2), (-w / 2, h / 2)):
                    pts.append((cx + dx * math.cos(a) - dy * math.sin(a), cy + dx * math.sin(a) + dy * math.cos(a)))
                d.polygon(pts, fill=fill)
            else:
                rad = 0
                if e.get("cr"):
                    rad = min(e["cr"][0] * min(w, h) + e["cr"][1] * SS, min(w, h) / 2)
                d.rounded_rectangle([x, y, x + w - 1, y + h - 1], radius=rad, fill=fill)
        if e.get("st") and abs(r) < 0.01 and e["c"] != "TextLabel":
            col = rgba(e["st"][0], e["st"][1])
            rad = 0
            if e.get("cr"):
                rad = min(e["cr"][0] * min(w, h) + e["cr"][1] * SS, min(w, h) / 2)
            th = max(1, int(e["st"][2] * SS))
            d.rounded_rectangle([x - th, y - th, x + w - 1 + th, y + h - 1 + th], radius=rad + th, outline=col, width=th)
        if e.get("t") and e.get("tt", 0) < 0.999:
            f = font(int(e["ts"] * SS), bold=e["ts"] >= 24)
            col = rgba(e["tc"], e["tt"])
            tw = d.textlength(e["t"], font=f)
            asc, desc = f.getmetrics()
            ty = y + h / 2 - (asc + desc) / 2
            if e.get("xa") == "Left":
                tx = x
            elif e.get("xa") == "Right":
                tx = x + w - tw
            else:
                tx = x + w / 2 - tw / 2
            # the arch's off-plate labels carry a dark outline
            if e["n"] == "Scale":
                for ddx, ddy in ((-SS, 0), (SS, 0), (0, -SS), (0, SS)):
                    d.text((tx + ddx, ty + ddy), e["t"], font=f, fill=(8, 8, 6, 170))
            d.text((tx, ty), e["t"], font=f, fill=col)
        base = Image.alpha_composite(base, layer)
    return base.resize((W // SS, H // SS), Image.LANCZOS)


def bounds(items):
    roots = [i for i in items if i["c"] == "Root"]
    x0 = min(r["x"] for r in roots); y0 = min(r["y"] for r in roots)
    x1 = max(r["x"] + r["w"] for r in roots); y1 = max(r["y"] + r["h"] for r in roots)
    return (x0, y0), (x1 - x0, y1 - y0)


raw = json.load(open(sys.argv[1], encoding="utf-8"))
items = json.loads(raw["result"])
by = {}
for i in items:
    if i["c"] == "Root" and i["scene"] in ("archhp", "resthp"):
        # the health plate is the dump's root, so its own fill was not in the dump: add it from the source
        items.append(dict(i, c="Frame", n="Plate", z=3, bg="090807", bt=0.28, cr=[0, 4], st=["928868", 0.74, 1]))
for i in items:
    by.setdefault(i["scene"], []).append(i)

scenes = [
    (by["arch"] + by["archhp"], "LOAD ARC  ·  24 kg, +5.5 just picked up"),
    (by["red"], "LOAD ARC  ·  past the redline (33.5 / 40)"),
    (by["resthp"] + by["mini"], "RESTING  ·  HP over KG"),
]
H1 = ImageFont.truetype("C:/Windows/Fonts/seguisb.ttf", 22)
imgs = []
for its, label in scenes:
    o, s = bounds(its)
    im = draw_scene(its, o, s)
    out = Image.new("RGB", (im.width, im.height + 44), (14, 14, 16))
    ImageDraw.Draw(out).text((14, 10), label, font=H1, fill=(230, 224, 206))
    out.paste(im.convert("RGB"), (0, 44))
    imgs.append(out)
W = max(i.width for i in imgs[:2]) * 2 + 20
top_h = max(i.height for i in imgs[:2])
sheet = Image.new("RGB", (max(W, imgs[2].width), top_h + imgs[2].height + 20), (10, 10, 12))
sheet.paste(imgs[0], (0, 0))
sheet.paste(imgs[1], (imgs[0].width + 20, 0))
sheet.paste(imgs[2], ((sheet.width - imgs[2].width) // 2, top_h + 20))
sheet.save(sys.argv[2])
print(sheet.size)
