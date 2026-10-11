"""Presentation sheet for the two menu prototypes."""
from PIL import Image, ImageDraw, ImageFont

W = 1800
BG = (14, 14, 16)


def font(name, size):
    try:
        return ImageFont.truetype(f"C:/Windows/Fonts/{name}", size)
    except OSError:
        return ImageFont.load_default()


H1, H2, BODY, SMALL = font("seguisb.ttf", 40), font("seguisb.ttf", 28), font("segoeui.ttf", 19), font("segoeui.ttf", 16)


def fit(path, width):
    im = Image.open(path).convert("RGB")
    h = round(im.height * width / im.width)
    return im.resize((width, h), Image.LANCZOS)


sections = [
    ("A  ·  Night Shift", "The game's own brass-on-black plate as a facility terminal: nav rail on the left, an expedition "
     "briefing on the right (last run, work orders, floor conditions, notices). Roboto Mono throughout.",
     "test/ui_preview_3035.jpeg", "test/menu_night_shift_final.png"),
    ("B  ·  Lost Memo", "Level 0 as an office that was let go: a manila memo in Special Elite + Merriweather, a red "
     "rubber-stamp accent, and a sticky note carrying the shift's orders.",
     "test/ui_preview_6670.jpeg", "test/menu_lost_memo_final.png"),
]

blocks = []
for title, blurb, real, final in sections:
    r, f = fit(real, W - 80), fit(final, W - 80)
    blocks.append((title, blurb, r, f))

height = 150 + sum(130 + b[2].height + 50 + b[3].height + 60 for b in blocks)
sheet = Image.new("RGB", (W, height), BG)
d = ImageDraw.Draw(sheet)
d.text((40, 36), "Backroom main-menu prototypes  —  built with RobloxForge", font=H1, fill=(236, 230, 210))
d.text((40, 92), "Each: desktop 1920×1080 and iPhone 14 landscape. Top row is a real Roblox Studio render (round 3); "
       "bottom row is the final round (wordmark + rotation fixes),", font=SMALL, fill=(160, 156, 145))
d.text((40, 114), "rendered offline because Studio stopped drawing frames once the session went remote. "
       "Every audit is clean on both.", font=SMALL, fill=(160, 156, 145))
y = 150
for title, blurb, r, f in blocks:
    d.text((40, y), title, font=H2, fill=(233, 216, 146))
    d.text((40, y + 44), blurb, font=BODY, fill=(205, 200, 186))
    y += 90
    d.text((40, y + 8), "ROBLOX STUDIO  ·  real engine fonts", font=SMALL, fill=(130, 190, 140))
    y += 34
    sheet.paste(r, (40, y))
    y += r.height + 14
    d.text((40, y + 8), "FINAL ROUND  ·  offline render (fonts approximated)", font=SMALL, fill=(200, 170, 110))
    y += 34
    sheet.paste(f, (40, y))
    y += f.height + 60
sheet = sheet.crop((0, 0, W, y))
sheet.save("test/menu_prototypes.png", optimize=True)
print(sheet.size)
