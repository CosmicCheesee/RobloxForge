"""Every prop as the player sees it in hand (camera at the origin, the real viewmodel arms at their hold
pose), plus a 3/4 view of it lying on a floor next to a fist for scale. Contact sheets of N props."""
import json
import math
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFont

HERE = __import__("pathlib").Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1]))
from robloxforge import render3d as r3  # noqa: E402

import importlib.util  # noqa: E402
spec = importlib.util.spec_from_file_location("pa", str(HERE / "props_audit.py"))
pa = importlib.util.module_from_spec(spec)
spec.loader.exec_module(pa)

SHIRT = (88, 96, 112)
FLOOR = (118, 104, 66)


def item_parts(p, M):
    out = []
    for q in p["parts"] or []:
        local = r3.tf(q["off"], pa.rotm(q.get("rot")))
        out.append({"sz": q["sz"], "cf": M @ local, "shape": q.get("sh") or "Block", "color": q.get("col") or "#a3a2a5"})
    return out


def arms(p):
    if p.get("twoHand"):
        h = pa.hand_checks(p, pa.parts_of(p))
        poses = [pa.HOLD2_R, h.get("left_solved", pa.HOLD2_L)]       # the left arm as WeaponSelect.leftGripPose solves it
    else:
        poses = [pa.HOLD_R, r3.tf([-1.94, -2.16, -1.82], r3.angles(66, -18, 12))]
    return [{"sz": [1, 2, 1], "cf": A, "color": SHIRT} for A in poses]


def held_view(p, size=(480, 270)):
    M = pa.item_cf(p)
    return r3.render(item_parts(p, M) + arms(p), None, fov=70, size=size, bg=(40, 36, 26))


def floor_view(p, size=(270, 270)):
    sz = np.array(p["sz"] or [1, 1, 1], float)
    M = r3.tf([0, p["restY"] if p.get("restY") is not None else sz[1] / 2, 0])
    big = float(max(sz))
    eye = np.array([big * 1.4 + 1.2, big * 0.9 + 0.8, big * 1.4 + 1.2])
    cam = r3.look_at(eye, [0, sz[1] * 0.4, 0])
    floor = [{"sz": [big * 4 + 4, 0.2, big * 4 + 4], "cf": r3.tf([0, -0.1, 0]), "color": FLOOR}]
    return r3.render(floor + item_parts(p, M), cam, fov=40, size=size, bg=(30, 30, 34))


def sheet(props, out):
    font = ImageFont.truetype("C:/Windows/Fonts/seguisb.ttf", 18)
    rows = []
    for p in props:
        a, b = held_view(p), floor_view(p)
        row = Image.new("RGB", (a.width + b.width + 8, a.height + 26), (12, 12, 14))
        ImageDraw.Draw(row).text((6, 3), f"{p['id']}  ·  {p.get('name') or ''}{'  ·  two-handed' if p.get('twoHand') else ''}", font=font, fill=(230, 224, 206))
        row.paste(a, (0, 26))
        row.paste(b, (a.width + 8, 26))
        rows.append(row)
    cols = 2
    w = rows[0].width
    h = rows[0].height
    n = len(rows)
    img = Image.new("RGB", (w * cols + 8, h * math.ceil(n / cols)), (12, 12, 14))
    for i, r in enumerate(rows):
        img.paste(r, ((i % cols) * (w + 8), (i // cols) * h))
    img.save(out)
    print(out, img.size)


if __name__ == "__main__":
    props = [p for p in json.load(open(sys.argv[1], encoding="utf-8")) if p.get("parts")]
    props.sort(key=lambda p: p["id"])
    only = set(sys.argv[3:])
    if only:
        props = [p for p in props if p["id"] in only]
    per = 8
    for k in range(0, len(props), per):
        sheet(props[k:k + per], f"{sys.argv[2]}_{k // per + 1}.png")
