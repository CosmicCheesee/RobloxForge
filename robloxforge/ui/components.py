"""Component library. {"ui": "<name>", ...params} expands to plain spec nodes built from theme tokens.

Interactive parts carry a ForgeFx attribute (button / item / tab / toggle / input / slider) and modal
dismissers ForgeRole = "dismiss"; ui_codegen's runtime wires hover, press, focus and open/close
animation to those tags, fast in and slow out.
"""
from __future__ import annotations

from ..studio import ForgeError

DOCS: dict[str, str] = {}
REG = {}


def comp(name, doc):
    def deco(fn):
        REG[name] = fn
        DOCS[name] = doc
        return fn
    return deco


# ---------------------------------------------------------------- helpers
def T(R, *path):
    cur = R.theme
    for p in path:
        cur = cur[p]
    return cur


def font(R, role="family", weight="regular"):
    return {"family": T(R, "font", role), "weight": T(R, "font", weight)}


def corner(r):
    return {"type": "UICorner", "props": {"CornerRadius": r}}


def stroke(R, col="@border", thick=None, transp=None):
    return {"type": "UIStroke", "props": {"Color": col, "Thickness": thick if thick is not None else R.theme.get("stroke", 1),
                                          "Transparency": transp if transp is not None else R.theme.get("strokeT", 0),
                                          "ApplyStrokeMode": "Border"}}


def pad(v=None, x=None, y=None):
    x = v if x is None else x
    y = v if y is None else y
    return {"type": "UIPadding", "props": {"PaddingLeft": x, "PaddingRight": x, "PaddingTop": y, "PaddingBottom": y}}


def sp(R, v):
    """spacing: token name (xs..xxl) or a number."""
    if isinstance(v, str):
        if v not in R.theme["space"]:
            raise ForgeError(f"unknown spacing {v!r}; use {list(R.theme['space'])} or a number")
        return R.theme["space"][v]
    return v or 0


def listing(direction="Vertical", gap=0, halign=None, valign=None, hflex=None, vflex=None, wraps=None):
    p = {"FillDirection": direction, "Padding": gap, "SortOrder": "LayoutOrder"}
    if halign:
        p["HorizontalAlignment"] = halign
    if valign:
        p["VerticalAlignment"] = valign
    if hflex:
        p["HorizontalFlex"] = hflex
    if vflex:
        p["VerticalFlex"] = vflex
    if wraps:
        p["Wraps"] = True
    return {"type": "UIListLayout", "props": p}


def flex_fill():
    return {"type": "UIFlexItem", "props": {"FlexMode": "Fill"}}


def sizing(width, height, default_h=0):
    """width/height: "fill" | "auto" | number (px) | [scale, offset]. Returns (Size, AutomaticSize)."""
    auto = ""

    def axis(v, d):
        nonlocal auto
        if v == "fill":
            return 1, 0, ""
        if v == "auto" or v is None:
            return 0, d, "a"
        if isinstance(v, list):
            return v[0], v[1], ""
        return 0, v, ""
    xs, xo, ax = axis(width, 0)
    ys, yo, ay = axis(height, default_h)
    auto = ("X" if ax else "") + ("Y" if ay else "")
    return [xs, xo, ys, yo], {"": "None", "X": "X", "Y": "Y", "XY": "XY"}[auto]


def common(p, node):
    """Apply the parameters every component accepts."""
    props = node.setdefault("props", {})
    if "name" in p:
        node["name"] = p["name"]
    if "order" in p:
        props["LayoutOrder"] = p["order"]
    if "pos" in p:
        props["Position"] = p["pos"]
    if "anchor" in p:
        props["AnchorPoint"] = p["anchor"]
    if "visible" in p:
        props["Visible"] = p["visible"]
    if "z" in p:
        props["ZIndex"] = p["z"]
    if p.get("grow"):
        node.setdefault("children", []).append(flex_fill())
    if "max_w" in p or "max_h" in p:
        # responsive cap: size by Scale, stop growing past this many pixels
        node.setdefault("children", []).append({"type": "UISizeConstraint", "props": {
            "MaxSize": [p.get("max_w", 100000), p.get("max_h", 100000)]}})
    if "attrs" in p:
        node.setdefault("attrs", {}).update(p["attrs"])
    if "props" in p:
        props.update(p["props"])
    return node


def frame(name="Frame", cls="Frame", **props):
    props.setdefault("BackgroundTransparency", 1)
    props.setdefault("BorderSizePixel", 0)
    return {"type": cls, "name": name, "props": props, "children": []}


def kids(p):
    return list(p.get("children") or [])


TEXT_VARIANTS = {
    # variant: (size key, font role, weight key, colour)
    "display": ("display", "display", "heavy", "@text"),
    "heading": ("heading", "display", "strong", "@text"),
    "title": ("title", "family", "strong", "@text"),
    "body": ("body", "family", "regular", "@text"),
    "label": ("label", "family", "medium", "@text"),
    "caption": ("caption", "family", "regular", "@muted"),
    "mono": ("label", "mono", "regular", "@text"),
}


# ---------------------------------------------------------------- structure
@comp("screen", "ScreenGui root. {children, display_order?, inset?: false keeps the topbar inset}")
def c_screen(p, R):
    return common(p, {"type": "ScreenGui", "name": p.get("name", "ForgeUI"),
                      "props": {"IgnoreGuiInset": not p.get("inset", False), "ResetOnSpawn": False,
                                "ZIndexBehavior": "Sibling", "DisplayOrder": p.get("display_order", 10)},
                      "children": kids(p)})


@comp("stack", "Flex container. {direction: vertical|horizontal, gap, align: start|center|end|stretch (cross axis), "
      "justify: start|center|end|between|around|evenly (main axis), wrap?, padding?, width, height, bg?, radius?, border?}")
def c_stack(p, R):
    vert = p.get("direction", "vertical") == "vertical"
    align, justify = p.get("align", "start"), p.get("justify", "start")
    cross = {"start": "Left" if vert else "Top", "center": "Center", "end": "Right" if vert else "Bottom",
             "stretch": None}
    main = {"start": "Top" if vert else "Left", "center": "Center", "end": "Bottom" if vert else "Right"}
    flexmap = {"between": "SpaceBetween", "around": "SpaceAround", "evenly": "SpaceEvenly"}
    if align not in cross or (justify not in main and justify not in flexmap):
        raise ForgeError("stack: align start|center|end|stretch, justify start|center|end|between|around|evenly")
    lay = {"direction": "Vertical" if vert else "Horizontal", "gap": sp(R, p.get("gap", "md")), "wraps": p.get("wrap")}
    if vert:
        lay["halign"] = cross[align]
        lay["valign"] = main.get(justify)
        lay["hflex"] = "Fill" if align == "stretch" else None
        lay["vflex"] = flexmap.get(justify)
    else:
        lay["valign"] = cross[align]
        lay["halign"] = main.get(justify)
        lay["vflex"] = "Fill" if align == "stretch" else None
        lay["hflex"] = flexmap.get(justify)
    size, auto = sizing(p.get("width", "fill" if vert else "auto"), p.get("height", "auto"))
    node = frame(p.get("name", "Stack"), Size=size, AutomaticSize=auto)
    if p.get("bg"):
        node["props"]["BackgroundColor3"] = p["bg"]
        node["props"]["BackgroundTransparency"] = p.get("bg_transparency", 0)
    if p.get("radius") is not None:
        r = p["radius"]
        node["children"].append(corner(R.theme["radius"][r] if isinstance(r, str) else r))
    if p.get("border"):
        node["children"].append(stroke(R))
    node["children"].append(listing(**lay))
    if p.get("padding") is not None:
        node["children"].append(pad(sp(R, p["padding"])))
    node["children"] += kids(p)
    return common(p, node)


@comp("row", "stack with direction horizontal (same params).")
def c_row(p, R):
    return c_stack({**p, "direction": "horizontal", "align": p.get("align", "center")}, R)


@comp("column", "stack with direction vertical (same params).")
def c_column(p, R):
    return c_stack({**p, "direction": "vertical"}, R)


@comp("center", "Full-size invisible frame that centres its children both ways. {children, gap}")
def c_center(p, R):
    node = frame(p.get("name", "Center"), Size=[1, 0, 1, 0])
    node["children"] = [listing("Vertical", sp(R, p.get("gap", "md")), "Center", "Center")] + kids(p)
    return common(p, node)


@comp("spacer", "Empty space. {size: px} or {grow: true} to push siblings apart in a stack.")
def c_spacer(p, R):
    s = p.get("size", 0)
    node = frame("Spacer", Size=[0, s, 0, s])
    return common(p, node)


@comp("divider", "1px rule. {vertical?, inset?}")
def c_divider(p, R):
    if p.get("vertical"):
        node = frame("Divider", Size=[0, 1, 1, 0])
    else:
        node = frame("Divider", Size=[1, 0, 0, 1])
    node["props"].update(BackgroundColor3="@border", BackgroundTransparency=R.theme.get("strokeT", 0))
    return common(p, node)


@comp("scroll", "Vertical scrolling list that sizes its canvas to content. {children, height: px|'fill', gap, padding?}")
def c_scroll(p, R):
    h = p.get("height", 300)
    size = [1, 0, 1, 0] if h == "fill" else [1, 0, 0, h]
    node = {"type": "ScrollingFrame", "name": p.get("name", "Scroll"), "props": {
        "Size": size, "BackgroundTransparency": 1, "BorderSizePixel": 0, "CanvasSize": [0, 0, 0, 0],
        "AutomaticCanvasSize": "Y", "ScrollingDirection": "Y", "ScrollBarThickness": 4,
        "ScrollBarImageColor3": "@subtle", "ScrollBarImageTransparency": 0.3},
        "children": [listing("Vertical", sp(R, p.get("gap", "md"))),
                     {"type": "UIPadding", "props": {
                         "PaddingRight": max(8, sp(R, p.get("padding", 0))),
                         # pad_top may be a UDim ([scale, offset]) -- e.g. [0.12, 0] drops content a share of the height
                         "PaddingTop": p["pad_top"] if "pad_top" in p else sp(R, p.get("padding", 0)),
                         "PaddingBottom": sp(R, p.get("padding", 0)),
                         "PaddingLeft": sp(R, p.get("padding", 0))}}] + kids(p)}
    return common(p, node)


@comp("grid", "Uniform grid. {children, cell: [w, h] px, gap, width: fill|px|[s,o]}")
def c_grid(p, R):
    cw, ch = p.get("cell", [120, 120])
    g = sp(R, p.get("gap", "sm"))
    size, _ = sizing(p.get("width", "fill"), 0)
    node = frame(p.get("name", "Grid"), Size=size, AutomaticSize="Y")
    node["children"] = [{"type": "UIGridLayout", "props": {"CellSize": [0, cw, 0, ch], "CellPadding": [0, g, 0, g],
                                                           "SortOrder": "LayoutOrder"}}] + kids(p)
    return common(p, node)


# ---------------------------------------------------------------- content
@comp("text", "Text. {text, variant: display|heading|title|body|label|caption|mono, color?, align: left|center|right, "
      "width: fill|auto|px, wrap?, weight?, size?, rich?, truncate?}")
def c_text(p, R):
    var = p.get("variant", "body")
    if var not in TEXT_VARIANTS:
        raise ForgeError(f"text variant {var!r} not in {list(TEXT_VARIANTS)}")
    sk, role, wk, col = TEXT_VARIANTS[var]
    width = p.get("width", "fill")
    size, auto = sizing(width, "auto")
    f = font(R, role, wk)
    if p.get("weight"):
        f["weight"] = p["weight"]
    props = {"Text": str(p.get("text", "")), "TextColor3": p.get("color", col), "FontFace": f,
             "TextSize": p.get("size", R.theme["size"][sk]), "BackgroundTransparency": 1, "BorderSizePixel": 0,
             "TextXAlignment": {"left": "Left", "center": "Center", "right": "Right"}[p.get("align", "left")],
             "TextYAlignment": "Center", "Size": size, "AutomaticSize": auto,
             "TextWrapped": p.get("wrap", width != "auto"), "RichText": bool(p.get("rich", False))}
    if var in ("body", "caption"):
        props["LineHeight"] = 1.15
    if p.get("truncate"):
        props["TextTruncate"] = "AtEnd"
        props["TextWrapped"] = False
    return common(p, {"type": "TextLabel", "name": p.get("name", var.capitalize()), "props": props})


BUTTON_H = {"sm": 32, "md": 40, "lg": 48}
BUTTON_PAD = {"sm": 12, "md": 16, "lg": 20}


def _variant_colors(R, v):
    tbl = {
        "primary": ("@accent", 0, "@accentText", None),
        "secondary": ("@surface2", 0, "@text", "@border"),
        "ghost": ("@surface2", 1, "@text", None),
        "soft": ("@accentSoft", 0, "@accentFg", None),
        "danger": ("@dangerFill", 0, "@dangerText", None),
        "outline": ("@surface", 1, "@text", "@border"),
    }
    if v not in tbl:
        raise ForgeError(f"button variant {v!r} not in {list(tbl)}")
    return tbl[v]


@comp("button", "Button. {text, variant: primary|secondary|ghost|soft|danger|outline, size: sm|md|lg, width: auto|fill|px, "
      "icon?: leading glyph, pill?, disabled?}")
def c_button(p, R):
    v, s = p.get("variant", "primary"), p.get("size", "md")
    if s not in BUTTON_H:
        raise ForgeError("button size sm|md|lg")
    bg, bgt, fg, border = _variant_colors(R, v)
    size, auto = sizing(p.get("width", "auto"), BUTTON_H[s])
    if auto == "XY":
        auto = "X"
    label = str(p.get("text", "Button"))
    if p.get("icon"):
        label = f"{p['icon']}  {label}"
    node = {"type": "TextButton", "name": p.get("name", "Button"), "props": {
        "Text": label, "TextColor3": fg, "FontFace": font(R, "family", "strong" if v == "primary" else "medium"),
        "TextSize": R.theme["size"]["label"] + (1 if s == "lg" else 0), "BackgroundColor3": bg,
        "BackgroundTransparency": bgt, "BorderSizePixel": 0, "AutoButtonColor": False, "Size": size,
        "AutomaticSize": auto},
        "attrs": {"ForgeFx": "button", "ForgeVariant": v},
        "children": [corner(R.theme["radius"]["pill" if p.get("pill") else "md"]),
                     pad(x=BUTTON_PAD[s], y=0)]}
    if border:
        node["children"].append(stroke(R, border))
    if p.get("disabled"):
        node["props"].update(TextTransparency=0.5, Interactable=False)
        node["props"]["BackgroundTransparency"] = min(1, bgt + 0.5)
    return common(p, node)


@comp("icon_button", "Square/round icon button. {icon: glyph like '×' '↑' '⋯', variant, size, round?}")
def c_icon_button(p, R):
    v, s = p.get("variant", "ghost"), p.get("size", "md")
    bg, bgt, fg, border = _variant_colors(R, v)
    h = BUTTON_H[s]
    node = {"type": "TextButton", "name": p.get("name", "IconButton"), "props": {
        "Text": str(p.get("icon", "•")), "TextColor3": fg, "FontFace": font(R, "family", "strong"),
        "TextSize": R.theme["size"]["title"], "BackgroundColor3": bg, "BackgroundTransparency": bgt,
        "BorderSizePixel": 0, "AutoButtonColor": False, "Size": [0, h, 0, h]},
        "attrs": {"ForgeFx": "button", "ForgeVariant": v},
        "children": [corner(R.theme["radius"]["pill" if p.get("round", True) else "md"])]}
    if border:
        node["children"].append(stroke(R, border))
    return common(p, node)


@comp("card", "Surface panel. {title?, subtitle?, children, variant: surface|raised|outline|accent, padding, gap, width, height}")
def c_card(p, R):
    var = p.get("variant", "surface")
    bg = {"surface": "@surface", "raised": "@raised", "outline": "@surface", "accent": "@accentSoft"}.get(var)
    if bg is None:
        raise ForgeError("card variant surface|raised|outline|accent")
    size, auto = sizing(p.get("width", "fill"), p.get("height", "auto"))
    node = frame(p.get("name", "Card"), cls=p.get("_cls", "Frame"), Size=size, AutomaticSize=auto,
                 BackgroundColor3=bg, BackgroundTransparency=1 if var == "outline" else R.theme.get("surfaceT", 0))
    if node["type"] == "TextButton":
        node["props"].update(Text="", AutoButtonColor=False)
    g = sp(R, p.get("gap", "md"))
    node["children"] = [corner(R.theme["radius"]["lg"]), stroke(R, "@accent" if var == "accent" else "@border"),
                        pad(sp(R, p.get("padding", "lg"))), listing("Vertical", g)]
    if var == "raised":
        node["children"].append({"type": "UIGradient", "props": {"Color": ["#ffffff", "#d9d9de"], "Rotation": 90}})
    order = -100
    if p.get("title"):
        node["children"].append({"ui": "text", "text": p["title"], "variant": "title", "order": order})
    if p.get("subtitle"):
        node["children"].append({"ui": "text", "text": p["subtitle"], "variant": "caption", "order": order + 1})
    node["children"] += kids(p)
    return common(p, node)


@comp("modal", "Centred dialog over a click-away scrim (a real GuiButton, as the Backroom HANDOFF requires); the card "
      "itself is a button so clicks on it do not fall through. {title, body?, children (actions), width: px max}")
def c_modal(p, R):
    width = p.get("width", 440)
    actions = kids(p)
    card_children = [
        {"ui": "row", "justify": "between", "align": "center", "width": "fill", "order": 0, "children": [
            {"ui": "text", "text": p.get("title", "Dialog"), "variant": "heading", "width": "auto"},
            {"ui": "icon_button", "icon": "×", "size": "sm", "name": "Close", "attrs": {"ForgeRole": "dismiss"}},
        ]},
    ]
    if p.get("body"):
        card_children.append({"ui": "text", "text": p["body"], "variant": "body", "color": "@muted", "order": 1})
    if actions:
        card_children.append({"ui": "row", "justify": "end", "gap": "sm", "order": 2, "width": "fill",
                              "children": actions})
    card = c_card({"_cls": "TextButton", "name": "Dialog", "padding": "xl", "gap": "lg", "children": card_children,
                   "width": [0.92, 0], "variant": "raised" if p.get("raised") else "surface"}, R)
    card["props"].update(AnchorPoint=[0.5, 0.5], Position=[0.5, 0, 0.5, 0])
    card["children"].append({"type": "UISizeConstraint", "props": {"MaxSize": [width, 100000]}})
    scrim = {"type": "TextButton", "name": "Scrim", "props": {
        "Size": [1, 0, 1, 0], "BackgroundColor3": "@scrim", "BackgroundTransparency": R.theme.get("scrimT", 0.45),
        "Text": "", "AutoButtonColor": False, "BorderSizePixel": 0}, "attrs": {"ForgeRole": "dismiss"}}
    node = frame(p.get("name", "Modal"), Size=[1, 0, 1, 0])
    node["props"]["ZIndex"] = p.get("z", 50)
    node["children"] = [scrim, card]
    node["attrs"] = {"ForgeModal": True}
    return node


@comp("input", "Text field. {placeholder, value?, label?, width, multiline?, height?}")
def c_input(p, R):
    h = p.get("height", 96 if p.get("multiline") else 40)
    box = frame("Field", Size=[1, 0, 0, h], BackgroundColor3="@surface2", BackgroundTransparency=0)
    box["children"] = [corner(R.theme["radius"]["md"]), stroke(R), pad(x=12, y=8 if p.get("multiline") else 0),
                       {"type": "TextBox", "name": "Box", "props": {
                           "Size": [1, 0, 1, 0], "BackgroundTransparency": 1, "Text": str(p.get("value", "")),
                           "PlaceholderText": str(p.get("placeholder", "")), "PlaceholderColor3": "@subtle",
                           "TextColor3": "@text", "FontFace": font(R), "TextSize": R.theme["size"]["body"],
                           "TextXAlignment": "Left", "TextYAlignment": "Top" if p.get("multiline") else "Center",
                           "ClearTextOnFocus": False, "MultiLine": bool(p.get("multiline")),
                           "TextWrapped": bool(p.get("multiline"))},
                        "attrs": {"ForgeFx": "input"}}]
    if not p.get("label"):
        box["name"] = p.get("name", "Input")
        size, _ = sizing(p.get("width", "fill"), h)
        box["props"]["Size"] = size
        return common(p, box)
    return common(p, c_column({"name": p.get("name", "Input"), "gap": "xs", "width": p.get("width", "fill"), "children": [
        {"ui": "text", "text": p["label"], "variant": "label", "color": "@muted"}, box]}, R))


@comp("toggle", "Switch. {on?, label?}")
def c_toggle(p, R):
    on = bool(p.get("on"))
    rail = {"type": "Frame", "name": "Rail", "props": {
        "Size": [0, 48, 0, 28], "AnchorPoint": [0.5, 0.5], "Position": [0.5, 0, 0.5, 0],
        "BackgroundColor3": "@accent" if on else "@surface2", "BorderSizePixel": 0},
        "children": [corner(999)] + ([] if on else [stroke(R)]) + [
            {"type": "Frame", "name": "Knob", "props": {
                "Size": [0, 22, 0, 22], "AnchorPoint": [0, 0.5], "Position": [1, -25, 0.5, 0] if on else [0, 3, 0.5, 0],
                "BackgroundColor3": "#ffffff" if on else "@muted", "BorderSizePixel": 0},
             "children": [corner(999)]}]}
    # the hit area is bigger than the rail: 52x36 is comfortable for a thumb
    track = {"type": "TextButton", "name": "Track", "props": {
        "Size": [0, 52, 0, 36], "BackgroundTransparency": 1, "Text": "", "AutoButtonColor": False, "BorderSizePixel": 0},
        "attrs": {"ForgeFx": "toggle", "ForgeOn": on}, "children": [rail]}
    if not p.get("label"):
        return common(p, track)
    return common(p, c_row({"name": p.get("name", "Toggle"), "width": p.get("width", "fill"), "justify": "between",
                            "children": [{"ui": "text", "text": p["label"], "variant": "body", "width": "auto"}, track]}, R))


@comp("slider", "Slider (visual; ui_codegen makes it draggable). {value: 0..1, label?, show_value?}")
def c_slider(p, R):
    v = max(0.0, min(1.0, float(p.get("value", 0.5))))
    track = frame("Track", Size=[1, 0, 0, 4], AnchorPoint=[0, 0.5], Position=[0, 0, 0.5, 0],
                  BackgroundColor3="@surface2", BackgroundTransparency=0)
    track["children"] = [corner(999), {"type": "Frame", "name": "Fill", "props": {
        "Size": [v, 0, 1, 0], "BackgroundColor3": "@accent", "BorderSizePixel": 0}, "children": [corner(999)]}]
    knob = {"type": "Frame", "name": "Knob", "props": {
        "Size": [0, 18, 0, 18], "AnchorPoint": [0.5, 0.5], "Position": [v, 0, 0.5, 0], "BackgroundColor3": "#ffffff",
        "BorderSizePixel": 0, "ZIndex": 2}, "children": [corner(999), stroke(R, "@accent", 2, 0)]}
    body = {"type": "TextButton", "name": "Slider", "props": {
        "Size": [1, 0, 0, 32], "BackgroundTransparency": 1, "Text": "", "AutoButtonColor": False},
        "attrs": {"ForgeFx": "slider", "ForgeValue": v}, "children": [track, knob]}
    if not (p.get("label") or p.get("show_value")):
        return common(p, body)
    head = {"ui": "row", "justify": "between", "width": "fill", "children": [
        {"ui": "text", "text": p.get("label", ""), "variant": "label", "width": "auto"},
        {"ui": "text", "text": f"{round(v * 100)}%", "variant": "caption", "width": "auto", "name": "Value"}]}
    return common(p, c_column({"name": p.get("name", "Slider"), "gap": "xs", "children": [head, body]}, R))


@comp("progress", "Progress bar. {value: 0..1, label?, tone: accent|success|warning|danger, height?}")
def c_progress(p, R):
    v = max(0.0, min(1.0, float(p.get("value", 0.5))))
    h = p.get("height", 6)
    bar = frame("Bar", Size=[1, 0, 0, h], BackgroundColor3="@surface2", BackgroundTransparency=0)
    bar["children"] = [corner(999), {"type": "Frame", "name": "Fill", "props": {
        "Size": [v, 0, 1, 0], "BackgroundColor3": f"@{p.get('tone', 'accent')}", "BorderSizePixel": 0},
        "children": [corner(999)]}]
    if not p.get("label"):
        return common(p, bar)
    return common(p, c_column({"name": p.get("name", "Progress"), "gap": "xs", "children": [
        {"ui": "row", "justify": "between", "width": "fill", "children": [
            {"ui": "text", "text": p["label"], "variant": "label", "width": "auto"},
            {"ui": "text", "text": f"{round(v * 100)}%", "variant": "caption", "width": "auto"}]}, bar]}, R))


TONES = {"neutral": ("@surface2", 0, "@muted"), "accent": ("@accent", 0.82, "@accentFg"),
         "success": ("@success", 0.84, "@success"), "warning": ("@warning", 0.84, "@warning"),
         "danger": ("@danger", 0.84, "@danger")}


@comp("chip", "Small pill label. {text, tone: neutral|accent|success|warning|danger}")
def c_chip(p, R):
    tone = p.get("tone", "neutral")
    if tone not in TONES:
        raise ForgeError(f"chip tone {tone!r} not in {list(TONES)}")
    bg, bgt, fg = TONES[tone]
    return common(p, {"type": "TextLabel", "name": p.get("name", "Chip"), "props": {
        "Text": str(p.get("text", "")), "TextColor3": fg, "FontFace": font(R, "family", "medium"),
        "TextSize": R.theme["size"]["caption"], "BackgroundColor3": bg, "BackgroundTransparency": bgt,
        "BorderSizePixel": 0, "Size": [0, 0, 0, 22], "AutomaticSize": "X"},
        "children": [corner(999), pad(x=10, y=0)]})


@comp("badge", "Count bubble. {count, tone}")
def c_badge(p, R):
    tone = p.get("tone", "accent")
    return common(p, {"type": "TextLabel", "name": p.get("name", "Badge"), "props": {
        "Text": str(p.get("count", 1)), "TextColor3": "@accentText", "FontFace": font(R, "family", "strong"),
        "TextSize": R.theme["size"]["caption"], "BackgroundColor3": f"@{tone}", "BorderSizePixel": 0,
        "Size": [0, 20, 0, 20], "AutomaticSize": "X"}, "children": [corner(999), pad(x=6, y=0)]})


@comp("avatar", "Round initials avatar. {text, size: px, tone}")
def c_avatar(p, R):
    s = p.get("size", 32)
    tone = p.get("tone", "accent")
    return common(p, {"type": "TextLabel", "name": p.get("name", "Avatar"), "props": {
        "Text": str(p.get("text", "AI"))[:3], "TextColor3": "@accentFg" if tone == "accent" else f"@{tone}",
        "FontFace": font(R, "family", "strong"),
        "TextSize": max(12, int(s * 0.42)), "BackgroundColor3": "@accentSoft" if tone == "accent" else "@surface2",
        "BorderSizePixel": 0, "Size": [0, s, 0, s]}, "children": [corner(999)]})


@comp("keycap", "Key prompt, e.g. the E-to-interact hint. {key: 'E', label?}")
def c_keycap(p, R):
    cap = {"type": "TextLabel", "name": "Key", "props": {
        "Text": str(p.get("key", "E")), "TextColor3": "@text", "FontFace": font(R, "mono", "strong"),
        "TextSize": R.theme["size"]["label"], "BackgroundColor3": "@surface2", "BorderSizePixel": 0,
        "Size": [0, 26, 0, 26]}, "children": [corner(R.theme["radius"]["sm"]), stroke(R)]}
    if not p.get("label"):
        return common(p, cap)
    return common(p, c_row({"name": p.get("name", "KeyHint"), "gap": "sm", "children": [
        cap, {"ui": "text", "text": p["label"], "variant": "label", "color": "@muted", "width": "auto"}]}, R))


@comp("image", "Image. {image: rbxassetid://..., width, height, radius?, fit: Fit|Crop|Stretch}")
def c_image(p, R):
    size, auto = sizing(p.get("width", 64), p.get("height", 64))
    node = {"type": "ImageLabel", "name": p.get("name", "Image"), "props": {
        "Image": str(p.get("image", "")), "Size": size, "BackgroundColor3": "@surface2", "BorderSizePixel": 0,
        "ScaleType": p.get("fit", "Crop")}, "children": []}
    if p.get("radius") is not None:
        r = p["radius"]
        node["children"].append(corner(R.theme["radius"][r] if isinstance(r, str) else r))
    return common(p, node)


# ---------------------------------------------------------------- composites
@comp("header", "Title row with actions on the right. {title, subtitle?, children (actions)}")
def c_header(p, R):
    left = {"ui": "column", "gap": "xs", "width": "auto", "children": [
        {"ui": "text", "text": p.get("title", ""), "variant": p.get("variant", "heading"), "width": "auto"}]}
    if p.get("subtitle"):
        left["children"].append({"ui": "text", "text": p["subtitle"], "variant": "caption", "width": "auto"})
    return common(p, c_row({"name": p.get("name", "Header"), "justify": "between", "width": "fill", "children": [
        left, {"ui": "row", "gap": "sm", "children": kids(p)}]}, R))


@comp("list_item", "Selectable row. {title, subtitle?, trailing?, avatar?: initials, selected?}")
def c_list_item(p, R):
    inner = [{"ui": "text", "text": p.get("title", ""), "variant": "label", "truncate": True}]
    if p.get("subtitle"):
        inner.append({"ui": "text", "text": p["subtitle"], "variant": "caption", "truncate": True})
    row = []
    if p.get("avatar"):
        row.append({"ui": "avatar", "text": p["avatar"], "size": 32})
    row.append({"ui": "column", "gap": 2, "grow": True, "width": "fill", "children": inner})
    if p.get("trailing") is not None:
        t = p["trailing"]
        row.append(t if isinstance(t, dict) else {"ui": "text", "text": str(t), "variant": "caption", "width": "auto"})
    node = {"type": "TextButton", "name": p.get("name", "Item"), "props": {
        "Size": [1, 0, 0, 0], "AutomaticSize": "Y", "Text": "", "AutoButtonColor": False, "BorderSizePixel": 0,
        "BackgroundColor3": "@surface2", "BackgroundTransparency": 0 if p.get("selected") else 1},
        "attrs": {"ForgeFx": "item", "ForgeSelected": bool(p.get("selected"))},
        "children": [corner(R.theme["radius"]["md"]), pad(x=sp(R, "md"), y=sp(R, "sm")),
                     listing("Horizontal", sp(R, "md"), valign="Center")] + row}
    return common(p, node)


@comp("list", "Column of list_items. {items: [{title, subtitle?, trailing?, avatar?}], selected?: index}")
def c_list(p, R):
    items = [{"ui": "list_item", **it, "order": i, "selected": i == p.get("selected")}
             for i, it in enumerate(p.get("items") or [])]
    return common(p, c_column({"name": p.get("name", "List"), "gap": 2, "children": items + kids(p)}, R))


@comp("tabs", "Tabs / segmented control. {items: [str], selected: index, variant: pill|underline}")
def c_tabs(p, R):
    sel = p.get("selected", 0)
    pill = p.get("variant", "pill") == "pill"
    tabs = []
    for i, label in enumerate(p.get("items") or []):
        on = i == sel
        t = {"type": "TextButton", "name": f"Tab{i}", "props": {
            "Text": str(label), "TextColor3": "@text" if on else "@muted",
            "FontFace": font(R, "family", "strong" if on else "medium"), "TextSize": R.theme["size"]["label"],
            "BackgroundColor3": "@raised", "BackgroundTransparency": 0 if (on and pill) else 1,
            "AutoButtonColor": False, "BorderSizePixel": 0, "Size": [0, 0, 0, 32], "AutomaticSize": "X",
            "LayoutOrder": i},
            "attrs": {"ForgeFx": "tab", "ForgeSelected": on, "ForgeTabStyle": "pill" if pill else "underline"},
            "children": [corner(999 if pill else 0), pad(x=14, y=0)]}
        if not pill:
            t["children"].append({"type": "Frame", "name": "Underline", "props": {
                "Size": [1, 0, 0, 2], "Position": [0, 0, 1, 0], "AnchorPoint": [0, 1], "BackgroundColor3": "@accent",
                "BorderSizePixel": 0, "Visible": on}})
        tabs.append(t)
    node = frame(p.get("name", "Tabs"), Size=[0, 0, 0, 0], AutomaticSize="XY")
    if pill:
        node["props"].update(BackgroundColor3="@surface2", BackgroundTransparency=0)
        node["children"] = [corner(999), pad(4), listing("Horizontal", 4, valign="Center")] + tabs
    else:
        node["children"] = [listing("Horizontal", 4, valign="Bottom")] + tabs
    return common(p, node)


@comp("tooltip", "Small floating hint. {text}")
def c_tooltip(p, R):
    return common(p, {"type": "TextLabel", "name": p.get("name", "Tooltip"), "props": {
        "Text": str(p.get("text", "")), "TextColor3": "@text", "FontFace": font(R), "TextSize": R.theme["size"]["caption"],
        "BackgroundColor3": "@raised", "BorderSizePixel": 0, "Size": [0, 0, 0, 26], "AutomaticSize": "X"},
        "children": [corner(R.theme["radius"]["sm"]), pad(x=8, y=0), stroke(R)]})


@comp("toast", "Notification card with a tone bar. {text, title?, tone, width}")
def c_toast(p, R):
    tone = p.get("tone", "accent")
    col = [{"ui": "text", "text": p.get("text", ""), "variant": "body", "color": "@muted"}]
    if p.get("title"):
        col.insert(0, {"ui": "text", "text": p["title"], "variant": "label"})
    bar = frame("Tone", Size=[0, 3, 1, 0], BackgroundColor3=f"@{tone}", BackgroundTransparency=0)
    bar["children"] = [corner(999), {"type": "UIFlexItem", "props": {"FlexMode": "None"}}]
    card = c_row({"name": p.get("name", "Toast"), "gap": "md", "align": "stretch", "width": p.get("width", 360),
                  "bg": "@raised", "radius": "lg", "border": True, "padding": "md",
                  "children": [bar, {"ui": "column", "gap": 2, "grow": True, "width": "fill", "children": col}]}, R)
    return common(p, card)


@comp("stat", "Metric tile. {label, value, delta?, tone?}")
def c_stat(p, R):
    ch = [{"ui": "text", "text": p.get("label", ""), "variant": "caption"},
          {"ui": "text", "text": str(p.get("value", "")), "variant": "display"}]
    if p.get("delta"):
        ch.append({"ui": "chip", "text": p["delta"], "tone": p.get("tone", "success")})
    return common(p, c_card({"name": p.get("name", "Stat"), "gap": "xs", "children": ch,
                             "width": p.get("width", "fill")}, R))


@comp("empty_state", "Centred placeholder. {title, body?, children (actions)}")
def c_empty(p, R):
    ch = [{"ui": "text", "text": p.get("title", "Nothing here"), "variant": "title", "align": "center"}]
    if p.get("body"):
        ch.append({"ui": "text", "text": p["body"], "variant": "body", "color": "@muted", "align": "center"})
    if kids(p):
        ch.append({"ui": "row", "gap": "sm", "children": kids(p)})
    return common(p, c_column({"name": p.get("name", "Empty"), "align": "center", "gap": "sm", "padding": "xl",
                               "children": ch}, R))


@comp("sidebar", "Full-height side panel. {side: left|right, width, title?, children}")
def c_sidebar(p, R):
    right = p.get("side", "left") == "right"
    node = frame(p.get("name", "Sidebar"), Size=[0, p.get("width", 300), 1, 0], BackgroundColor3="@surface",
                 BackgroundTransparency=R.theme.get("surfaceT", 0),
                 AnchorPoint=[1, 0] if right else [0, 0], Position=[1, 0, 0, 0] if right else [0, 0, 0, 0])
    node["children"] = [stroke(R), pad(sp(R, "lg")), listing("Vertical", sp(R, "md"))]
    if p.get("title"):
        node["children"].append({"ui": "text", "text": p["title"], "variant": "title", "order": -100})
    node["children"] += kids(p)
    return common(p, node)


@comp("message", "Chat message. {role: user|assistant, text, name?}")
def c_message(p, R):
    text = str(p.get("text", ""))
    if p.get("role", "assistant") == "user":
        bubble = {"type": "TextLabel", "name": "Bubble", "props": {
            "Text": text, "TextColor3": "@text", "FontFace": font(R), "TextSize": R.theme["size"]["body"],
            "BackgroundColor3": "@surface2", "BorderSizePixel": 0, "TextWrapped": True, "TextXAlignment": "Left",
            "Size": [0, 0, 0, 0], "AutomaticSize": "XY", "LineHeight": 1.15},
            "children": [corner(R.theme["radius"]["lg"]), pad(x=sp(R, "lg"), y=sp(R, "md")),
                         {"type": "UISizeConstraint", "props": {"MaxSize": [p.get("max_width", 520), 100000]}}]}
        return common(p, c_row({"name": p.get("name", "UserMessage"), "justify": "end", "width": "fill",
                                "children": [bubble]}, R))
    col = [{"ui": "text", "text": text, "variant": "body", "rich": p.get("rich", False)}]
    if p.get("name_label"):
        col.insert(0, {"ui": "text", "text": p["name_label"], "variant": "caption"})
    return common(p, c_row({"name": p.get("name", "AssistantMessage"), "align": "start", "gap": "md", "width": "fill",
                            "children": [{"ui": "avatar", "text": p.get("avatar", "AI"), "size": 28},
                                         {"ui": "column", "gap": "xs", "grow": True, "width": "fill", "children": col}]}, R))


@comp("composer", "Chat input bar with send button. {placeholder}")
def c_composer(p, R):
    box = {"type": "TextBox", "name": "Box", "props": {
        "Size": [1, 0, 0, 36], "BackgroundTransparency": 1, "Text": "", "PlaceholderText": p.get("placeholder", "Message…"),
        "PlaceholderColor3": "@subtle", "TextColor3": "@text", "FontFace": font(R), "TextSize": R.theme["size"]["body"],
        "TextXAlignment": "Left", "ClearTextOnFocus": False}, "attrs": {"ForgeFx": "input"},
        "children": [flex_fill()]}
    send = {"ui": "icon_button", "icon": "↑", "variant": "primary", "size": "sm", "name": "Send"}
    return common(p, c_row({"name": p.get("name", "Composer"), "gap": "sm", "width": "fill", "bg": "@surface2",
                            "radius": "lg", "border": True, "padding": "sm", "children": [box, send]}, R))


@comp("chat", "Whole chat panel: scrolling messages + composer. {messages: [{role, text}], placeholder, height}")
def c_chat(p, R):
    msgs = [{"ui": "message", **m, "order": i} for i, m in enumerate(p.get("messages") or [])]
    return common(p, c_column({"name": p.get("name", "Chat"), "gap": "md", "width": "fill", "children": [
        {"ui": "scroll", "height": p.get("height", 360), "gap": "lg", "children": msgs, "order": 0},
        {"ui": "composer", "placeholder": p.get("placeholder", "Message…"), "order": 1}]}, R))


def expand(node, R):
    name = node["ui"]
    if name not in REG:
        raise ForgeError(f"unknown component {name!r}; available: {sorted(REG)}")
    out = REG[name](node, R)
    while "ui" in out:          # a component that returned another component
        out = expand(out, R)
    return out


from . import components_game  # noqa: E402,F401  (registers the game HUD components)
