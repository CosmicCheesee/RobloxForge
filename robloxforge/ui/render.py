"""Offline renderer for normalized UI specs: a small Roblox-style layout engine + PIL drawing.

Covers what the component library uses: UDim2 sizing, AnchorPoint, UIPadding, UIListLayout (alignment,
HorizontalFlex/VerticalFlex Fill + Space*, UIFlexItem grow), UIGridLayout, AutomaticSize, UISizeConstraint,
UIAspectRatioConstraint, UICorner, UIStroke (Border/Contextual), UIGradient on backgrounds, text
(wrap, truncate, scaled, alignment, line height), ScrollingFrame/ClipsDescendants clipping, CanvasGroup,
ZIndex among siblings. Not modelled: Rotation, Wraps, RichText styling (tags are stripped), images (a
placeholder is drawn). Fonts are approximated with Windows system fonts -- spacing is close, glyphs are not
Roblox's, so judge layout here and typography in Studio (ui_preview).
"""
from __future__ import annotations

import io
import math
import os
import re
from functools import lru_cache

import numpy as np
from PIL import Image, ImageDraw, ImageFont

from .schema import GUI_OBJECTS, get

FONT_DIR = os.path.join(os.environ.get("WINDIR", r"C:\Windows"), "Fonts")
MONO = {"RobotoMono", "Inconsolata", "SourceCodePro", "Code", "UbuntuMono", "Courier"}
COND = {"Oswald", "BebasNeue", "Bahnschrift", "Sarpanch", "Michroma", "TitilliumWeb", "RobotoCondensed"}
SERIF = {"Merriweather", "Garamond", "Fondamento", "AccanthisADFStd", "GrenzeGotisch"}
HAND = {"PermanentMarker", "PatrickHand", "IndieFlower", "Kalam", "AmaticSC", "ComicNeueAngular"}
TYPEWRITER = {"SpecialElite"}
HEAVY = {"SemiBold", "Bold", "ExtraBold", "Heavy"}
TOPBAR_INSET = 58


def _first(*names):
    for n in names:
        p = os.path.join(FONT_DIR, n)
        if os.path.exists(p):
            return p
    return None


@lru_cache(maxsize=256)
def font_file(family, weight):
    bold = weight in HEAVY
    semi = weight in ("Medium", "SemiBold")
    if family in MONO:
        return _first("consolab.ttf" if bold else "consola.ttf", "cour.ttf", "arial.ttf")
    if family in COND:
        return _first("bahnschrift.ttf", "arialbd.ttf" if bold else "arial.ttf")
    if family in SERIF:
        return _first("georgiab.ttf" if bold else "georgia.ttf", "arial.ttf")
    if family in HAND:
        return _first("segoepr.ttf", "comic.ttf", "arial.ttf")
    if family in TYPEWRITER:
        return _first("courbd.ttf" if bold else "cour.ttf", "arial.ttf")
    if weight in ("Bold", "ExtraBold", "Heavy"):
        return _first("segoeuib.ttf", "arialbd.ttf")
    if semi or weight == "SemiBold":
        return _first("seguisb.ttf", "segoeuib.ttf", "arialbd.ttf")
    if weight in ("Light", "ExtraLight", "Thin"):
        return _first("segoeuil.ttf", "segoeui.ttf", "arial.ttf")
    return _first("segoeui.ttf", "arial.ttf")


def _needs_symbols(text):
    return any(ord(ch) > 0x2000 for ch in text or "")


@lru_cache(maxsize=512)
def pil_font(family, weight, size, symbols=False):
    if symbols:
        f = _first("seguisym.ttf", "seguiemj.ttf")
        if f:
            try:
                return ImageFont.truetype(f, max(1, int(round(size))))
            except OSError:
                pass
    f = font_file(family, weight)
    size = max(1, int(round(size)))
    try:
        return ImageFont.truetype(f, size) if f else ImageFont.load_default()
    except OSError:
        return ImageFont.load_default()


def _p(node, prop, default=None):
    v = get(node, prop)
    if v is None:
        return default
    t = v[0]
    if t in ("udim2", "udim", "vec2", "color", "num", "bool", "str", "cseq", "nseq"):
        return v[1]
    if t == "enum":
        return v[2]
    if t == "font":
        return {"family": v[1], "weight": v[2]}
    return v


def _child(node, cls):
    for c in node["children"]:
        if c["type"] == cls:
            return c
    return None


DEFAULTS = {"Size": [0, 100, 0, 100], "BackgroundTransparency": 0, "BackgroundColor3": [163, 162, 165]}


class Box:
    __slots__ = ("node", "x", "y", "w", "h", "kids", "canvas")

    def __init__(self, node):
        self.node, self.x, self.y, self.w, self.h, self.kids, self.canvas = node, 0.0, 0.0, 0.0, 0.0, [], None


def _text_props(node):
    f = _p(node, "FontFace") or {"family": "SourceSansPro", "weight": "Regular"}
    enum_font = _p(node, "Font")
    if enum_font:
        f = {"family": "RobotoMono" if enum_font in ("Code", "RobotoMono") else "SourceSansPro",
             "weight": "Bold" if "Bold" in enum_font else "Regular"}
    return f, _p(node, "TextSize", 14), _p(node, "LineHeight", 1.0)


def _clean(text):
    return re.sub(r"<[^>]+>", "", text or "")


def wrap_lines(text, font, width):
    out = []
    for para in _clean(text).split("\n"):
        words = para.split(" ")
        line = ""
        for w in words:
            trial = (line + " " + w) if line else w
            if width is None or font.getlength(trial) <= width or not line:
                line = trial
            else:
                out.append(line)
                line = w
        out.append(line)
    return out


def measure_text(node, width=None):
    f, size, lh = _text_props(node)
    text = _p(node, "Text", "") if node["type"] != "TextBox" else (_p(node, "Text", "") or _p(node, "PlaceholderText", ""))
    font = pil_font(f["family"], f["weight"], size, _needs_symbols(text))
    wrap = _p(node, "TextWrapped", False)
    lines = wrap_lines(text, font, width if wrap else None)
    tw = max((font.getlength(l) for l in lines), default=0)
    th = len(lines) * size * lh
    return tw, th


def _udim(u, total):
    return u[0] * total + u[1]


def _padding(node):
    pd = _child(node, "UIPadding")
    if not pd:
        return [0, 0], [0, 0], [0, 0], [0, 0]
    return tuple(_p(pd, k, [0, 0]) for k in ("PaddingLeft", "PaddingRight", "PaddingTop", "PaddingBottom"))


def layout(node, pw, ph, force_w=None, force_h=None):
    """Size this node against a parent content size, and lay out its subtree. Positions of `node`
    itself are set by the caller."""
    b = Box(node)
    size = _p(node, "Size", DEFAULTS["Size"])
    w = force_w if force_w is not None else size[0] * pw + size[1]
    h = force_h if force_h is not None else size[2] * ph + size[3]
    auto = _p(node, "AutomaticSize", "None")
    pl, pr, pt, pb = _padding(node)
    padl, padr = _udim(pl, w), _udim(pr, w)
    padt, padb = _udim(pt, h), _udim(pb, h)

    if auto != "None" and (force_w is None or force_h is None):
        cw, ch = content_extent(node, w - padl - padr, h - padt - padb, auto)
        if "X" in auto and force_w is None:
            w = max(w, cw + padl + padr)
        if "Y" in auto and force_h is None:
            h = max(h, ch + padt + padb)
    sc = _child(node, "UISizeConstraint")
    if sc:
        mn, mx = _p(sc, "MinSize", [0, 0]), _p(sc, "MaxSize", [1e9, 1e9])
        w, h = min(max(w, mn[0]), mx[0]), min(max(h, mn[1]), mx[1])
    ar = _child(node, "UIAspectRatioConstraint")
    if ar:
        ratio = _p(ar, "AspectRatio", 1) or 1
        if _p(ar, "DominantAxis", "Width") == "Width":
            h = w / ratio
        else:
            w = h * ratio
    b.w, b.h = max(0.0, w), max(0.0, h)
    place_children(b, padl, padr, padt, padb)
    return b


def content_extent(node, cw, ch, auto):
    """How big the content of `node` is (text and/or children), for AutomaticSize."""
    ew = eh = 0.0
    if node["type"] in ("TextLabel", "TextButton", "TextBox"):
        tw, th = measure_text(node, cw if (auto == "Y" and _p(node, "TextWrapped", False)) else None)
        # with AutomaticSize XY and a UISizeConstraint max width, wrap at that width
        sc = _child(node, "UISizeConstraint")
        if auto == "XY" and sc and _p(node, "TextWrapped", False):
            mx = _p(sc, "MaxSize", [1e9, 1e9])[0]
            pl, pr, _, _ = _padding(node)
            tw, th = measure_text(node, mx - pl[1] - pr[1])
        ew, eh = tw, th
    gui = [c for c in node["children"] if c["type"] in GUI_OBJECTS and _p(c, "Visible", True)]
    lst, grid = _child(node, "UIListLayout"), _child(node, "UIGridLayout")
    if gui:
        boxes = [layout(c, cw if "X" not in auto else 0, ch if "Y" not in auto else 0) for c in gui]
        if lst:
            vert = _p(lst, "FillDirection", "Vertical") == "Vertical"
            gap = _udim(_p(lst, "Padding", [0, 0]), ch if vert else cw)
            boxes = [bx for _, bx in sorted(zip(gui, boxes), key=lambda t: _p(t[0], "LayoutOrder", 0))]
            mains_ = [bx.h if vert else bx.w for bx in boxes]
            limit = (ch if vert else cw) if ("Y" if vert else "X") not in auto else 0
            lines = _lines(mains_, limit, gap, bool(_p(lst, "Wraps", False)))
            main = max(sum(mains_[i] for i in ln) + gap * (len(ln) - 1) for ln in lines)
            cross = sum(max((boxes[i].w if vert else boxes[i].h) for i in ln) for ln in lines) + gap * (len(lines) - 1)
            mw, mh = (cross, main) if vert else (main, cross)
        elif grid:
            cell = _p(grid, "CellSize", [0, 100, 0, 100])
            cpad = _p(grid, "CellPadding", [0, 5, 0, 5])
            cwid, chei = _udim(cell[:2], cw), _udim(cell[2:], ch)
            per = max(1, int((cw + _udim(cpad[:2], cw)) // max(1, cwid + _udim(cpad[:2], cw)))) if cw > 0 else len(boxes)
            rows = math.ceil(len(boxes) / per)
            mw = per * cwid + (per - 1) * _udim(cpad[:2], cw)
            mh = rows * chei + (rows - 1) * _udim(cpad[2:], ch)
        else:
            mw = max((_p(c, "Position", [0, 0, 0, 0])[1] + bx.w for c, bx in zip(gui, boxes)), default=0)
            mh = max((_p(c, "Position", [0, 0, 0, 0])[3] + bx.h for c, bx in zip(gui, boxes)), default=0)
        ew, eh = max(ew, mw), max(eh, mh)
    return ew, eh


def place_children(b, padl, padr, padt, padb):
    node = b.node
    gui = [c for c in node["children"] if c["type"] in GUI_OBJECTS and _p(c, "Visible", True)]
    cw, ch = max(0.0, b.w - padl - padr), max(0.0, b.h - padt - padb)
    lst, grid = _child(node, "UIListLayout"), _child(node, "UIGridLayout")
    if node["type"] == "ScrollingFrame":
        ch = max(ch, 0)
    if lst and gui:
        _place_list(b, gui, lst, cw, ch, padl, padt)
    elif grid and gui:
        cell = _p(grid, "CellSize", [0, 100, 0, 100])
        cpad = _p(grid, "CellPadding", [0, 5, 0, 5])
        cwid, chei = _udim(cell[:2], cw), _udim(cell[2:], ch)
        gx, gy = _udim(cpad[:2], cw), _udim(cpad[2:], ch)
        per = max(1, int((cw + gx) // max(1, cwid + gx)))
        for i, c in enumerate(sorted(gui, key=lambda c: _p(c, "LayoutOrder", 0))):
            k = layout(c, cwid, chei, cwid, chei)
            k.x, k.y = padl + (i % per) * (cwid + gx), padt + (i // per) * (chei + gy)
            b.kids.append(k)
    else:
        for c in gui:
            k = layout(c, cw, ch)
            pos = _p(c, "Position", [0, 0, 0, 0])
            anc = _p(c, "AnchorPoint", [0, 0])
            k.x = padl + pos[0] * cw + pos[1] - anc[0] * k.w
            k.y = padt + pos[2] * ch + pos[3] - anc[1] * k.h
            b.kids.append(k)
    b.kids.sort(key=lambda k: _p(k.node, "ZIndex", 1))


def _lines(mains, main_size, gap, wraps):
    """Greedy line breaking for UIListLayout.Wraps: indices per line."""
    if not wraps or main_size <= 0:
        return [list(range(len(mains)))]
    lines, cur, used = [], [], 0.0
    for i, m in enumerate(mains):
        need = m if not cur else used + gap + m
        if cur and need > main_size + 0.5:
            lines.append(cur)
            cur, used = [i], m
        else:
            cur.append(i)
            used = need
    if cur:
        lines.append(cur)
    return lines


def _place_list(b, gui, lst, cw, ch, padl, padt):
    vert = _p(lst, "FillDirection", "Vertical") == "Vertical"
    gap = _udim(_p(lst, "Padding", [0, 0]), ch if vert else cw)
    main_size, cross_size = (ch, cw) if vert else (cw, ch)
    main_flex = _p(lst, "VerticalFlex" if vert else "HorizontalFlex", "None")
    cross_flex = _p(lst, "HorizontalFlex" if vert else "VerticalFlex", "None")
    item_align = _p(lst, "ItemLineAlignment", "Automatic")
    wraps = bool(_p(lst, "Wraps", False))
    order = sorted(gui, key=lambda c: _p(c, "LayoutOrder", 0))
    base = [layout(c, cw, ch) for c in order]
    lines = _lines([k.h if vert else k.w for k in base], main_size, gap, wraps)
    cross_al = _p(lst, "HorizontalAlignment" if vert else "VerticalAlignment", "Left" if vert else "Top")
    cross_cursor = 0.0
    for line in lines:
        lorder = [order[i] for i in line]
        kids = [base[i] for i in line]
        line_cross = cross_size if not wraps else max(((k.w if vert else k.h) for k in kids), default=0)
        if cross_flex == "Fill" or item_align == "Stretch":
            kids = [layout(c, cw, ch, *((line_cross, None) if vert else (None, line_cross))) for c in lorder]
        mains = [k.h if vert else k.w for k in kids]
        free = main_size - sum(mains) - gap * (len(kids) - 1)
        growers = [i for i, c in enumerate(lorder)
                   if (_child(c, "UIFlexItem") and _p(_child(c, "UIFlexItem"), "FlexMode", "None") in ("Fill", "Grow", "Custom"))]
        if main_flex == "Fill" and not growers:
            growers = list(range(len(kids)))
        if free > 0 and growers and main_size > 0:
            add = free / len(growers)
            for i in growers:
                mains[i] += add
                k = kids[i]
                kids[i] = layout(lorder[i], cw, ch, *((k.w, mains[i]) if vert else (mains[i], k.h)))
                # a UISizeConstraint can stop the growth short: keep the size it really got, and let the
                # leftover go back to the line's alignment / spacing like Roblox does
                mains[i] = kids[i].h if vert else kids[i].w
            free = max(0.0, main_size - sum(mains) - gap * (len(kids) - 1))
        elif free < 0 and growers and not wraps:
            for i in growers:
                mains[i] = max(0, mains[i] + free / len(growers))
                k = kids[i]
                kids[i] = layout(lorder[i], cw, ch, *((k.w, mains[i]) if vert else (mains[i], k.h)))
            free = 0
        if wraps:
            line_cross = max(((k.w if vert else k.h) for k in kids), default=0)
        n = len(kids)
        extra_gap, start = 0.0, 0.0
        if free > 0 and main_flex in ("SpaceBetween", "SpaceAround", "SpaceEvenly") and n:
            if main_flex == "SpaceBetween":
                extra_gap = free / (n - 1) if n > 1 else 0
                start = 0  # a lone item in a space-between line sits at the start (CSS and Roblox agree)
            elif main_flex == "SpaceAround":
                extra_gap, start = free / n, free / n / 2
            else:
                extra_gap = start = free / (n + 1)
        elif free > 0:
            al = _p(lst, "VerticalAlignment" if vert else "HorizontalAlignment", "Top" if vert else "Left")
            start = {"Center": free / 2, "Bottom": free, "Right": free}.get(al, 0)
        span = cross_size if not wraps else line_cross
        cur = start
        for k, m in zip(kids, mains):
            kc = k.w if vert else k.h
            own = _child(k.node, "UIFlexItem")
            al = _p(own, "ItemLineAlignment", "Automatic") if own else "Automatic"
            if al == "Automatic":
                al = {"Automatic": None}.get(item_align, item_align)
            if al in (None, "Automatic"):
                off = {"Center": (span - kc) / 2, "Right": span - kc, "Bottom": span - kc}.get(cross_al, 0)
            else:
                off = {"Center": (span - kc) / 2, "End": span - kc}.get(al, 0)
            if vert:
                k.x, k.y = padl + cross_cursor + off, padt + cur
            else:
                k.x, k.y = padl + cur, padt + cross_cursor + off
            cur += m + gap + extra_gap
            b.kids.append(k)
        cross_cursor += line_cross + gap


# ---------------------------------------------------------------- drawing
def _rgba(col, transp):
    return tuple(int(c) for c in col) + (int(round(255 * max(0.0, min(1.0, 1 - transp)))),)


def _radius(node, w, h):
    c = _child(node, "UICorner")
    if not c:
        return 0
    u = _p(c, "CornerRadius", [0, 8])
    return max(0, min(_udim(u, min(w, h)), min(w, h) / 2))


def _gradient_layer(node, w, h, base_col, transp):
    g = _child(node, "UIGradient")
    W, H = max(1, int(round(w))), max(1, int(round(h)))
    if not g or _p(g, "Enabled", True) is False:
        return None
    cs = _p(g, "Color") or [[0, [255, 255, 255]], [1, [255, 255, 255]]]
    ts = _p(g, "Transparency") or [[0, 0], [1, 0]]
    rot = math.radians(_p(g, "Rotation", 0))
    yy, xx = np.mgrid[0:H, 0:W]
    u = ((xx + 0.5) / W - 0.5) * math.cos(rot) + ((yy + 0.5) / H - 0.5) * math.sin(rot) + 0.5
    u = np.clip(u, 0, 1)
    ct = np.array([p[0] for p in cs])
    cols = np.array([p[1] for p in cs], float)
    rgb = np.stack([np.interp(u, ct, cols[:, i]) for i in range(3)], -1) / 255.0 * np.array(base_col, float)
    tt = np.interp(u, [p[0] for p in ts], [p[1] for p in ts])
    alpha = (1 - transp) * (1 - tt)
    arr = np.dstack([rgb, alpha * 255]).astype(np.uint8)
    return Image.fromarray(arr, "RGBA")


def draw(img, b, ox, oy, clip, group_alpha=1.0):
    node = b.node
    if not _p(node, "Visible", True):
        return
    x, y = ox + b.x, oy + b.y
    w, h = b.w, b.h
    if node["type"] == "CanvasGroup":
        layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
        _draw_self_and_kids(layer, b, x, y, clip, 1.0)
        a = 1 - _p(node, "GroupTransparency", 0)
        if a < 1:
            layer.putalpha(layer.getchannel("A").point(lambda v: int(v * a)))
        img.alpha_composite(layer)
        return
    _draw_self_and_kids(img, b, x, y, clip, group_alpha)


def _draw_self_and_kids(img, b, x, y, clip, ga):
    node = b.node
    w, h = b.w, b.h
    layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    r = _radius(node, w, h)
    bt = _p(node, "BackgroundTransparency", 0)
    bc = _p(node, "BackgroundColor3", DEFAULTS["BackgroundColor3"])
    box = [x, y, x + w - 1, y + h - 1]
    if w >= 1 and h >= 1 and bt < 1:
        gl = _gradient_layer(node, w, h, bc, bt)
        if gl is not None:
            mask = Image.new("L", gl.size, 0)
            ImageDraw.Draw(mask).rounded_rectangle([0, 0, gl.size[0] - 1, gl.size[1] - 1], radius=r, fill=255)
            gl.putalpha(Image.fromarray((np.array(gl.getchannel("A"), float) * np.array(mask, float) / 255).astype(np.uint8)))
            layer.alpha_composite(gl, (int(round(x)), int(round(y))))
        else:
            d.rounded_rectangle(box, radius=r, fill=_rgba(bc, bt))
    if node["type"] in ("ImageLabel", "ImageButton") and w > 4 and h > 4:
        it = _p(node, "ImageTransparency", 0)
        d.rounded_rectangle(box, radius=r, outline=_rgba([140, 140, 150], it + 0.3), width=1)
        d.line([x, y, x + w, y + h], fill=_rgba([140, 140, 150], it + 0.5))
        d.line([x + w, y, x, y + h], fill=_rgba([140, 140, 150], it + 0.5))
    st = _child(node, "UIStroke")
    text_stroke = None
    if st and _p(st, "Enabled", True) is not False:
        mode = _p(st, "ApplyStrokeMode", "Contextual")
        scol, sth, stt = _p(st, "Color", [0, 0, 0]), _p(st, "Thickness", 1), _p(st, "Transparency", 0)
        if mode == "Contextual" and node["type"] in ("TextLabel", "TextButton", "TextBox"):
            text_stroke = (scol, sth, stt)
        elif sth > 0:
            t = max(1, int(round(sth)))
            d.rounded_rectangle([x - t, y - t, x + w - 1 + t, y + h - 1 + t], radius=r + t if r else 0,
                                outline=_rgba(scol, stt), width=t)
    if node["type"] in ("TextLabel", "TextButton", "TextBox"):
        _draw_text(d, node, x, y, w, h, text_stroke)
    _paste_clipped(img, layer, clip, ga)
    inner_clip = clip
    if _p(node, "ClipsDescendants", False) or node["type"] == "ScrollingFrame":
        inner_clip = _intersect(clip, (x, y, x + w, y + h))
    for k in b.kids:
        draw(img, k, x, y, inner_clip, ga)


def _intersect(a, b):
    return (max(a[0], b[0]), max(a[1], b[1]), min(a[2], b[2]), min(a[3], b[3]))


def _paste_clipped(img, layer, clip, ga):
    x0, y0, x1, y1 = (int(round(v)) for v in clip)
    x0, y0 = max(0, x0), max(0, y0)
    x1, y1 = min(img.size[0], x1), min(img.size[1], y1)
    if x1 <= x0 or y1 <= y0:
        return
    region = layer.crop((x0, y0, x1, y1))
    if ga < 1:
        region.putalpha(region.getchannel("A").point(lambda v: int(v * ga)))
    img.alpha_composite(region, (x0, y0))


def _draw_text(d, node, x, y, w, h, stroke):
    f, size, lh = _text_props(node)
    text = _p(node, "Text", "")
    tcol = _p(node, "TextColor3", [27, 42, 53])
    tt = _p(node, "TextTransparency", 0)
    if node["type"] == "TextBox" and not text:
        text, tcol = _p(node, "PlaceholderText", ""), _p(node, "PlaceholderColor3", [178, 178, 178])
    text = _clean(text)
    if not text:
        return
    pl, pr, pt, pb = (_udim(u, w if i < 2 else h) for i, u in enumerate(_padding(node)))
    iw, ih = max(1, w - pl - pr), max(1, h - pt - pb)
    wrap = _p(node, "TextWrapped", False)
    if _p(node, "TextScaled", False):
        lo, hi = 1, 100
        while lo < hi:
            mid = (lo + hi + 1) // 2
            fnt = pil_font(f["family"], f["weight"], mid, _needs_symbols(text))
            lines = wrap_lines(text, fnt, iw if wrap or True else None)
            tw = max(fnt.getlength(l) for l in lines)
            if tw <= iw and len(lines) * mid * lh <= ih:
                lo = mid
            else:
                hi = mid - 1
        size = lo
        tsc = None
        for c in node["children"]:
            if c["type"] == "UITextSizeConstraint":
                tsc = c
        if tsc:
            size = max(_p(tsc, "MinTextSize", 1), min(size, _p(tsc, "MaxTextSize", 100)))
        wrap = True
    fnt = pil_font(f["family"], f["weight"], size, _needs_symbols(text))
    lines = wrap_lines(text, fnt, iw if wrap else None)
    if _p(node, "TextTruncate", "None") == "AtEnd" and lines:
        line = lines[0]
        if fnt.getlength(line) > iw:
            while line and fnt.getlength(line + "…") > iw:
                line = line[:-1]
            line += "…"
        lines = [line]
    line_h = size * lh
    total = len(lines) * line_h
    ya = _p(node, "TextYAlignment", "Center")
    ty = y + pt + {"Top": 0, "Bottom": ih - total}.get(ya, (ih - total) / 2)
    xa = _p(node, "TextXAlignment", "Center")
    asc = fnt.getmetrics()[0] if hasattr(fnt, "getmetrics") else size
    for i, line in enumerate(lines):
        lw = fnt.getlength(line)
        tx = x + pl + {"Left": 0, "Right": iw - lw}.get(xa, (iw - lw) / 2)
        yy = ty + i * line_h + (line_h - size) / 2 - (asc - size * 0.8) * 0.5
        kw = {}
        if stroke:
            kw = {"stroke_width": max(1, int(round(stroke[1]))), "stroke_fill": _rgba(stroke[0], stroke[2])}
        d.text((tx, yy), line, font=fnt, fill=_rgba(tcol, tt), **kw)


def render(spec, viewport=(1280, 720), bg=(24, 26, 30), checker=False, boxes_out=None):
    W, H = viewport
    img = Image.new("RGBA", (W, H), bg + (255,))
    if checker:
        d = ImageDraw.Draw(img)
        for yy in range(0, H, 24):
            for xx in range(0, W, 24):
                if (xx // 24 + yy // 24) % 2:
                    d.rectangle([xx, yy, xx + 23, yy + 23], fill=(bg[0] + 8, bg[1] + 8, bg[2] + 8, 255))
    roots = [spec] if spec["type"] != "ScreenGui" else [c for c in spec["children"] if c["type"] in GUI_OBJECTS]
    inset = 0 if spec["type"] != "ScreenGui" or _p(spec, "IgnoreGuiInset", False) else TOPBAR_INSET
    rects = []
    for r in sorted(roots, key=lambda n: _p(n, "ZIndex", 1)):
        b = layout(r, W, H - inset)
        pos = _p(r, "Position", [0, 0, 0, 0])
        anc = _p(r, "AnchorPoint", [0, 0])
        b.x = pos[0] * W + pos[1] - anc[0] * b.w
        b.y = inset + pos[2] * (H - inset) + pos[3] - anc[1] * b.h
        draw(img, b, 0, 0, (0, 0, W, H))
        rects.append(b)
    if boxes_out is not None:
        boxes_out.extend(rects)
    if inset:
        ImageDraw.Draw(img).rectangle([0, 0, W, inset - 1], outline=(255, 255, 255, 40))
    return img.convert("RGB")


def to_png(img):
    buf = io.BytesIO()
    img.save(buf, "PNG", optimize=True)
    return buf.getvalue()


def sheet(images, labels):
    pad, top = 16, 26
    w = sum(i.width for i in images) + pad * (len(images) + 1)
    h = max(i.height for i in images) + top + pad
    out = Image.new("RGB", (w, h), (12, 12, 14))
    d = ImageDraw.Draw(out)
    x = pad
    for im, lab in zip(images, labels):
        out.paste(im, (x, top))
        d.text((x, 6), lab, fill=(220, 220, 220), font=pil_font("SourceSansPro", "SemiBold", 14))
        x += im.width + pad
    return out


# ---------------------------------------------------------------- offline audit
def _lum(c):
    def lin(v):
        v = v / 255
        return v / 12.92 if v <= 0.03928 else ((v + 0.055) / 1.055) ** 2.4
    r, g, b = (lin(x) for x in c)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def _contrast(a, b):
    la, lb = sorted((_lum(a), _lum(b)), reverse=True)
    return (la + 0.05) / (lb + 0.05)


def audit(roots, viewport, canvas_bg, min_text=11, min_touch=32):
    """Checks on laid-out boxes. Returns (lines, counts)."""
    W, H = viewport
    out, counts = [], {}

    def flag(code, path, msg):
        counts[code] = counts.get(code, 0) + 1
        if counts[code] <= 12:
            out.append(f"{code:<9} {path}  {msg}")

    def walk(b, ox, oy, path, bgstack, clip, in_scroll=False):
        node = b.node
        if not _p(node, "Visible", True):
            return
        x, y = ox + b.x, oy + b.y
        here = f"{path}.{node['name']}"
        bt = _p(node, "BackgroundTransparency", 0)
        bc = _p(node, "BackgroundColor3", DEFAULTS["BackgroundColor3"])
        under = bgstack[-1]
        mine = [round(c * (1 - bt) + u * bt) for c, u in zip(bc, under)] if bt < 1 else under
        if node["type"] in ("TextLabel", "TextButton", "TextBox"):
            text = _clean(_p(node, "Text", "") or (_p(node, "PlaceholderText", "") if node["type"] == "TextBox" else ""))
            if text:
                f, size, lh = _text_props(node)
                pl, pr, pt, pb = (_udim(u, b.w if i < 2 else b.h) for i, u in enumerate(_padding(node)))
                iw, ih = b.w - pl - pr, b.h - pt - pb
                scaled = _p(node, "TextScaled", False)
                if not scaled and _p(node, "TextTruncate", "None") == "None":
                    tw, th = measure_text(node, iw if _p(node, "TextWrapped", False) else None)
                    if tw > iw + 1 or th > ih + 1:
                        flag("OVERFLOW", here, f"text {tw:.0f}x{th:.0f} in {iw:.0f}x{ih:.0f}")
                if not scaled and size < min_text:
                    flag("TINY", here, f"{size}px text")
                tc = _p(node, "TextColor3", [27, 42, 53])
                if node["type"] == "TextBox" and not _p(node, "Text", ""):
                    tc = _p(node, "PlaceholderColor3", [178, 178, 178])
                r = _contrast(tc, mine)
                need = 3 if size >= 18 or (size >= 14 and (_text_props(node)[0]["weight"] in HEAVY)) else 4.5
                if node["type"] == "TextBox" and not _p(node, "Text", ""):
                    need = 3  # placeholders are allowed to be quieter
                if len(text.strip()) <= 2 and not any(ch.isalnum() for ch in text):
                    need = 3  # a glyph icon is a graphic: WCAG 1.4.11 asks 3:1
                if r < need:
                    flag("CONTRAST", here, f"{r:.2f}:1 (needs {need})")
        if node["type"] in ("TextButton", "ImageButton", "TextBox") and _p(node, "Interactable", True):
            if (b.w < min_touch or b.h < min_touch) and not (b.w >= W * 0.9 and b.h >= H * 0.9):
                flag("TOUCH", here, f"hit area {b.w:.0f}x{b.h:.0f}")
        if not in_scroll and b.w > 0 and b.h > 0 and (x < -1 or y < -1 or x + b.w > W + 1 or y + b.h > H + 1):
            flag("OFFSCREEN", here, f"{x:.0f},{y:.0f} {b.w:.0f}x{b.h:.0f} vs {W}x{H}")
        if clip and (x < clip[0] - 1 or y < clip[1] - 1 or x + b.w > clip[2] + 1 or y + b.h > clip[3] + 1)                 and node["type"] != "ScrollingFrame":
            flag("CLIPPED", here, "partly cut off by a clipping ancestor")
        if (_p(node, "Rotation", 0) or 0) % 360 and (clip is not None or in_scroll):
            flag("ROTCLIP", here, "Rotation is ignored under a clipping ancestor / ScrollingFrame -- renders upright")
        inner = clip
        if _p(node, "ClipsDescendants", False) and node["type"] != "ScrollingFrame":
            inner = (x, y, x + b.w, y + b.h)
        if node["type"] == "ScrollingFrame":
            inner = None
        managed = _child(node, "UIListLayout") or _child(node, "UIGridLayout")
        kids = [k for k in b.kids if _p(k.node, "Visible", True)]
        if not managed:
            for i in range(len(kids)):
                for j in range(i + 1, len(kids)):
                    a, c = kids[i], kids[j]
                    if _p(a.node, "ZIndex", 1) != _p(c.node, "ZIndex", 1):
                        continue
                    ix = min(a.x + a.w, c.x + c.w) - max(a.x, c.x)
                    iy = min(a.y + a.h, c.y + c.h) - max(a.y, c.y)
                    ain = a.x >= c.x and a.y >= c.y and a.x + a.w <= c.x + c.w and a.y + a.h <= c.y + c.h
                    cin = c.x >= a.x and c.y >= a.y and c.x + c.w <= a.x + a.w and c.y + c.h <= a.y + a.h
                    if ix > 4 and iy > 4 and not ain and not cin:
                        flag("OVERLAP", f"{here}.{a.node['name']}", f"overlaps {c.node['name']} by {ix:.0f}x{iy:.0f}")
        for k in kids:
            walk(k, x, y, here, bgstack + [mine], inner, in_scroll or node["type"] == "ScrollingFrame")

    for r in roots:
        walk(r, 0, 0, "", [list(canvas_bg)], None)
    # top-level pieces of a screen collide too (a HUD's corners meet on a phone)
    vis = [r for r in roots if _p(r.node, "Visible", True)]
    for i in range(len(vis)):
        for j in range(i + 1, len(vis)):
            a, c = vis[i], vis[j]
            if _p(a.node, "ZIndex", 1) != _p(c.node, "ZIndex", 1):
                continue
            ix = min(a.x + a.w, c.x + c.w) - max(a.x, c.x)
            iy = min(a.y + a.h, c.y + c.h) - max(a.y, c.y)
            ain = a.x >= c.x and a.y >= c.y and a.x + a.w <= c.x + c.w and a.y + a.h <= c.y + c.h
            cin = c.x >= a.x and c.y >= a.y and c.x + c.w <= a.x + a.w and c.y + c.h <= a.y + a.h
            if ix > 4 and iy > 4 and not ain and not cin:
                counts["OVERLAP"] = counts.get("OVERLAP", 0) + 1
                out.append(f"OVERLAP   .{a.node['name']}  overlaps {c.node['name']} by {ix:.0f}x{iy:.0f}")
    return out, counts
