"""Labelled presentation sheets for the two hub-menu directions."""
from PIL import Image, ImageDraw, ImageFont


def font(name, size):
    try:
        return ImageFont.truetype(f"C:/Windows/Fonts/{name}", size)
    except OSError:
        return ImageFont.load_default()


H1, BODY = font("seguisb.ttf", 46), font("segoeui.ttf", 24)
SHEETS = [
    ("test/hub_REFIT_r3.png", "test/hub_direction1_refit.png", "Direction 1  ·  REFIT",
     ["Your hub as it is, made cleaner. Same three skins (docket paper, machine readout, contraband card), same rules:",
      "no tab row, name + balance header, one search bar, footer with what happened on the left and the action on the right.",
      "New: readable ingredient chips with shortfall + bar, steppers with MAX, status stripes, hazard tape, taped price stickers."]),
    ("test/hub_OVERHAUL_r3.png", "test/hub_direction2_overhaul.png", "Direction 2  ·  OVERHAUL",
     ["Same facilities and content, re-laid-out. Extraction log: tile grid + live yield card + material sliders.",
      "Fabrication: master-detail. Vault: two lockers with transfer controls. Upgrades: ability cards + descent as an elevator ladder.",
      "Market: lots as tiles. Squad: four seats (open seats shown), invite banner, server list. Softer, rounder, sans + mono numerals."]),
]
for src, dst, title, lines in SHEETS:
    im = Image.open(src).convert("RGB")
    head = 60 + 34 * len(lines) + 30
    out = Image.new("RGB", (im.width, im.height + head), (12, 12, 14))
    d = ImageDraw.Draw(out)
    d.text((24, 18), title, font=H1, fill=(236, 230, 210))
    for i, l in enumerate(lines):
        d.text((26, 80 + i * 34), l, font=BODY, fill=(178, 172, 158))
    out.paste(im, (0, head))
    out = out.resize((1800, round(out.height * 1800 / out.width)), Image.LANCZOS)
    out.save(dst, optimize=True)
    print(dst, out.size)
