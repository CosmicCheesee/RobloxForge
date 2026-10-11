"""Presentation: Overhaul II -- full sheet plus a close-up of the vault."""
from PIL import Image, ImageDraw, ImageFont


def font(name, size):
    try:
        return ImageFont.truetype(f"C:/Windows/Fonts/{name}", size)
    except OSError:
        return ImageFont.load_default()


H1, BODY = font("seguisb.ttf", 54), font("segoeui.ttf", 28)
im = Image.open("test/hub_OVERHAUL2_final.png").convert("RGB")
lines = ["Direction 2 pushed further. Every panel is dressed on all four sides: a spine with the facility name and status",
         "lights, a tick ruler, corner brackets, a bay tab above and a serial + barcode below. Each header has a numbered badge",
         "and a stat strip; category chips, value-tier stripes on tiles, a fact row on recipes, an elevator descent ladder.",
         "The vault is a dense 64 px grid with stack counts, slot capacity and a selected-item strip -- built to hold a lot."]
head = 70 + 40 * len(lines) + 30
out = Image.new("RGB", (im.width, im.height + head), (12, 12, 14))
d = ImageDraw.Draw(out)
d.text((28, 20), "Scrap hub  ·  Overhaul II", font=H1, fill=(236, 230, 210))
for i, l in enumerate(lines):
    d.text((30, 92 + i * 40), l, font=BODY, fill=(178, 172, 158))
out.paste(im, (0, head))
out = out.resize((2000, round(out.height * 2000 / out.width)), Image.LANCZOS)
out.save("test/hub_overhaul2_all.png", optimize=True)
print(out.size)
