"""Before/after of the title plate's light, with UIGradient Transparency + Rotation modelled per pixel
(the offline UI renderer draws gradient-transparent frames flat)."""
import math

import numpy as np
from PIL import Image, ImageDraw, ImageFont

S = 2
PW, PH = 700, 158
PAD = 60
W, H = (PW + 2 * PAD) * S, (PH + 2 * PAD) * S
TUBE = np.array([196, 214, 210], float)
BONE = (228, 226, 210)
PLATE = np.array([23, 21, 16], float)


def backdrop():
    y = np.linspace(0, 1, H)[:, None, None]
    top, bot = np.array([150, 140, 92]), np.array([96, 88, 54])
    return np.broadcast_to(top * (1 - y) + bot * y, (H, W, 3)).astype(float).copy()


def seq(keys, t):
    ks = [k[0] for k in keys]
    vs = [k[1] for k in keys]
    return np.interp(t, ks, vs)


def gradient_layer(img, x, y, w, h, rot, keys, base_t):
    """Composite a TUBE-coloured frame whose alpha = (1-base_t) * (1-gradient(t))."""
    x0, y0, x1, y1 = int(x * S), int(y * S), int((x + w) * S), int((y + h) * S)
    yy, xx = np.mgrid[y0:y1, x0:x1].astype(float)
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    r = math.radians(rot)
    dx, dy = math.cos(r), math.sin(r)
    ext = ((x1 - x0) * abs(dx) + (y1 - y0) * abs(dy)) / 2
    t = np.clip(0.5 + ((xx - cx) * dx + (yy - cy) * dy) / (2 * ext), 0, 1)
    a = (1 - base_t) * (1 - seq(keys, t))
    img[y0:y1, x0:x1] = img[y0:y1, x0:x1] * (1 - a[..., None]) + TUBE * a[..., None]


def rect(img, x, y, w, h, col, tr):
    x0, y0, x1, y1 = int(x * S), int(y * S), int((x + w) * S), int((y + h) * S)
    img[y0:y1, x0:x1] = img[y0:y1, x0:x1] * tr + np.array(col, float) * (1 - tr)


def plate(variant):
    img = backdrop()
    px, py = PAD, PAD
    rect(img, px, py, PW, PH, PLATE, 0.42)
    if variant == "before":
        gradient_layer(img, px + (PW - 440) / 2, py + 12, 440, 132, 90, [(0, 0.55), (0.6, 0.9), (1, 1)], 0.80)
        rect(img, px + (PW - 440) / 2, py + 10, 440, 2, TUBE, 0.15)
    else:
        gradient_layer(img, px, py, PW, PH, 28, [(0, 0.25), (0.2, 0.42), (0.45, 0.66), (0.75, 0.86), (1, 1)], 0.74)
        gradient_layer(img, px, py, PW, PH, 34, [(0, 0.05), (0.12, 0.35), (0.3, 0.75), (0.5, 1), (1, 1)], 0.84)
        rect(img, px + 36, py + 10, 300, 2, TUBE, 0.15)
    im = Image.fromarray(np.clip(img, 0, 255).astype(np.uint8))
    d = ImageDraw.Draw(im)
    f = ImageFont.truetype("C:/Windows/Fonts/consola.ttf", 52 * S)
    total = 9 * 66
    for i, ch in enumerate("BACKROOMS"):
        x = px + (PW - total) / 2 + i * 66
        for (ox, oy, col) in ((4, -2, (150, 176, 178, 66)), (0, 0, BONE + (255,))):
            tw = d.textlength(ch, font=f)
            d.text(((x + ox) * S + (66 * S - tw) / 2, (py + 52 + oy) * S), ch, font=f, fill=col)
    return im.resize((im.width // S, im.height // S), Image.LANCZOS)


a, b = plate("before"), plate("after")
H1 = ImageFont.truetype("C:/Windows/Fonts/seguisb.ttf", 22)
out = Image.new("RGB", (a.width, a.height * 2 + 80), (12, 12, 14))
d = ImageDraw.Draw(out)
d.text((14, 8), "BEFORE  ·  straight down, middle of the word only", font=H1, fill=(230, 224, 206))
out.paste(a, (0, 40))
d.text((14, a.height + 48), "AFTER  ·  raked diagonally from the upper left, over every letter", font=H1, fill=(230, 224, 206))
out.paste(b, (0, a.height + 80))
out.save("test/live/title_light.png")
print(out.size)
