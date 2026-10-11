"""Game HUD components: meters, slots and hotbars, reticles, currency, timers, objectives, NPC dialogue,
settings rows, shop tiles, leaderboard rows. Registered into components.REG on import."""
from __future__ import annotations

from .components import c_card, c_column, c_row, common, comp, corner, font, frame, stroke


@comp("stat_bar", "Labelled meter for health / stamina / ammo. {label, value: 0..1, text?: right-hand readout, "
      "tone: accent|success|warning|danger, icon?: glyph, height?, width}")
def c_stat_bar(p, R):
    v = max(0.0, min(1.0, float(p.get("value", 1))))
    tone = p.get("tone", "accent")
    h = p.get("height", 8)
    head = []
    if p.get("icon"):
        head.append({"ui": "text", "text": p["icon"], "variant": "label", "color": f"@{tone}", "width": "auto"})
    head.append({"ui": "text", "text": p.get("label", ""), "variant": "caption", "width": "auto", "grow": True})
    if p.get("text") is not None:
        head.append({"ui": "text", "text": str(p["text"]), "variant": "mono", "width": "auto", "name": "Value",
                     "color": "@text"})
    bar = frame("Bar", Size=[1, 0, 0, h], BackgroundColor3="@surface2", BackgroundTransparency=0)
    bar["children"] = [corner(999), {"type": "Frame", "name": "Fill", "props": {
        "Size": [v, 0, 1, 0], "BackgroundColor3": f"@{tone}", "BorderSizePixel": 0},
        "children": [corner(999), {"type": "UIGradient", "props": {"Color": ["#ffffff", "#c8c8c8"], "Rotation": 90}}]}]
    return common(p, c_column({"name": p.get("name", "StatBar"), "gap": "xs", "width": p.get("width", 240),
                               "children": [{"ui": "row", "gap": "xs", "width": "fill", "children": head}, bar]}, R))


@comp("slot", "Inventory / hotbar slot. {key?: '1', icon?: glyph or text, label?, count?, selected?, empty?, size: px}")
def c_slot(p, R):
    s = p.get("size", 56)
    sel = bool(p.get("selected"))
    kids = [corner(R.theme["radius"]["md"]), stroke(R, "@accent" if sel else "@border", 2 if sel else 1)]
    if p.get("icon") and not p.get("empty"):
        kids.append({"type": "TextLabel", "name": "Icon", "props": {
            "Text": str(p["icon"]), "TextColor3": "@text", "FontFace": font(R, "family", "strong"),
            "TextSize": int(s * 0.36), "BackgroundTransparency": 1, "Size": [1, 0, 1, 0]}})
    if p.get("key") is not None:
        kids.append({"type": "TextLabel", "name": "Key", "props": {
            "Text": str(p["key"]), "TextColor3": "@muted", "FontFace": font(R, "mono", "medium"),
            "TextSize": R.theme["size"]["caption"], "BackgroundTransparency": 1, "Size": [0, 16, 0, 14],
            "Position": [0, 5, 0, 3], "TextXAlignment": "Left"}})
    if p.get("count") is not None:
        kids.append({"type": "TextLabel", "name": "Count", "props": {
            "Text": str(p["count"]), "TextColor3": "@text", "FontFace": font(R, "mono", "strong"),
            "TextSize": R.theme["size"]["caption"], "BackgroundTransparency": 1, "Size": [0, 24, 0, 14],
            "AnchorPoint": [1, 1], "Position": [1, -5, 1, -3], "TextXAlignment": "Right"}})
    node = {"type": "TextButton", "name": p.get("name", "Slot"), "props": {
        "Size": [0, s, 0, s], "Text": "", "AutoButtonColor": False, "BorderSizePixel": 0,
        "BackgroundColor3": "@surface2" if sel else "@surface",
        "BackgroundTransparency": 0 if sel else R.theme.get("surfaceT", 0)},
        "attrs": {"ForgeFx": "button", "ForgeSlot": True}, "children": kids}
    if p.get("label"):
        return common(p, c_column({"name": p.get("name", "Slot"), "gap": 4, "width": "auto", "align": "center",
                                   "children": [node, {"ui": "text", "text": p["label"], "variant": "caption",
                                                       "width": "auto", "align": "center"}]}, R))
    return common(p, node)


@comp("hotbar", "Row of slots on a translucent tray. {slots: [{icon?, count?, label?}], selected: index, size: px}")
def c_hotbar(p, R):
    sl = [{"ui": "slot", **it, "key": i + 1, "selected": i == p.get("selected", 0), "size": p.get("size", 56),
           "order": i} for i, it in enumerate(p.get("slots") or [])]
    return common(p, c_row({"name": p.get("name", "Hotbar"), "gap": "sm", "children": sl, "bg": "@bg",
                            "bg_transparency": 0.35, "radius": "lg", "padding": "sm"}, R))


@comp("crosshair", "Centre-screen reticle. {style: dot|cross|ring, size, color}")
def c_crosshair(p, R):
    st = p.get("style", "dot")
    col = p.get("color", "@text")
    size = p.get("size", 6 if st == "dot" else 18)
    node = frame(p.get("name", "Crosshair"), Size=[0, size, 0, size], AnchorPoint=[0.5, 0.5], Position=[0.5, 0, 0.5, 0])
    if st == "dot":
        node["props"].update(BackgroundColor3=col, BackgroundTransparency=0.1)
        node["children"] = [corner(999), stroke(R, "#000000", 1, 0.6)]
    elif st == "ring":
        node["children"] = [corner(999), stroke(R, col, 2, 0.15)]
    else:
        node["children"] = [
            {"type": "Frame", "name": "H", "props": {"Size": [1, 0, 0, 2], "AnchorPoint": [0.5, 0.5],
                                                    "Position": [0.5, 0, 0.5, 0], "BackgroundColor3": col,
                                                    "BorderSizePixel": 0}},
            {"type": "Frame", "name": "V", "props": {"Size": [0, 2, 1, 0], "AnchorPoint": [0.5, 0.5],
                                                    "Position": [0.5, 0, 0.5, 0], "BackgroundColor3": col,
                                                    "BorderSizePixel": 0}}]
    return common(p, node)


@comp("currency", "Amount with a glyph, e.g. coins. {amount, icon: glyph, tone}")
def c_currency(p, R):
    tone = p.get("tone", "warning")
    return common(p, c_row({"name": p.get("name", "Currency"), "gap": "xs", "bg": "@surface", "radius": "pill",
                            "padding": "sm", "border": True, "children": [
        {"ui": "text", "text": p.get("icon", "◆"), "variant": "label", "color": f"@{tone}", "width": "auto"},
        {"ui": "text", "text": str(p.get("amount", 0)), "variant": "mono", "width": "auto", "weight": "Bold"}]}, R))


@comp("timer", "Big countdown / clock readout. {text, label?}")
def c_timer(p, R):
    ch = [{"ui": "text", "text": str(p.get("text", "00:00")), "variant": "heading", "align": "center", "width": "auto",
           "props": {"FontFace": {"family": R.theme["font"]["mono"], "weight": "Bold"}}}]
    if p.get("label"):
        ch.insert(0, {"ui": "text", "text": p["label"], "variant": "caption", "align": "center", "width": "auto"})
    return common(p, c_column({"name": p.get("name", "Timer"), "gap": 0, "width": "auto", "align": "center",
                               "children": ch}, R))


@comp("objective", "Quest / objective tracker. {title, steps: [{text, done?}], width}")
def c_objective(p, R):
    rows = []
    for i, stp in enumerate(p.get("steps") or []):
        done = bool(stp.get("done"))
        rows.append({"ui": "row", "gap": "sm", "width": "fill", "order": i, "children": [
            {"ui": "text", "text": "✓" if done else "○", "variant": "label", "color": "@success" if done else "@muted",
             "width": "auto"},
            {"ui": "text", "text": stp.get("text", ""), "variant": "body", "color": "@muted" if done else "@text",
             "grow": True}]})
    return common(p, c_card({"name": p.get("name", "Objective"), "title": p.get("title", "Objective"), "gap": "sm",
                             "padding": "md", "width": p.get("width", 300), "children": rows}, R))


@comp("dialog_box", "NPC / story dialogue pinned to the bottom of the screen. {speaker, text, choices: [str], "
      "portrait?: initials, max_width}")
def c_dialog_box(p, R):
    choices = [{"ui": "button", "text": f"{i + 1}.  {c}", "variant": "secondary", "width": "fill", "order": i,
                "props": {"TextXAlignment": "Left"}} for i, c in enumerate(p.get("choices") or [])]
    body = [{"ui": "text", "text": p.get("speaker", ""), "variant": "title", "color": "@accentFg"},
            {"ui": "text", "text": p.get("text", ""), "variant": "body"}]
    if choices:
        body.append({"ui": "column", "gap": "xs", "children": choices})
    row = []
    if p.get("portrait"):
        row.append({"ui": "avatar", "text": p["portrait"], "size": 56})
    row.append({"ui": "column", "gap": "sm", "grow": True, "width": "fill", "children": body})
    card = c_card({"name": p.get("name", "Dialog"), "padding": "lg", "width": [0.94, 0], "children": [
        {"ui": "row", "gap": "lg", "align": "start", "width": "fill", "children": row}]}, R)
    card["props"].update(AnchorPoint=[0.5, 1], Position=[0.5, 0, 1, -24])
    card["children"].append({"type": "UISizeConstraint", "props": {"MaxSize": [p.get("max_width", 760), 100000]}})
    return common(p, card)


@comp("settings_row", "Label + description on the left, a control on the right. {label, description?, control: node}")
def c_settings_row(p, R):
    left = [{"ui": "text", "text": p.get("label", ""), "variant": "label"}]
    if p.get("description"):
        left.append({"ui": "text", "text": p["description"], "variant": "caption"})
    ctl = p.get("control") or {"ui": "toggle"}
    return common(p, c_row({"name": p.get("name", "Setting"), "gap": "lg", "width": "fill", "justify": "between",
                            "padding": "xs", "children": [
        {"ui": "column", "gap": 2, "grow": True, "width": "fill", "children": left}, ctl]}, R))


@comp("shop_item", "Store tile. {item, price, icon?: glyph, image?: asset, tag?: chip text, owned?, width}")
def c_shop_item(p, R):
    if p.get("image"):
        pic = {"ui": "image", "image": p["image"], "width": "fill", "height": 96, "radius": "md"}
    else:
        pic = {"type": "TextLabel", "name": "Icon", "props": {
            "Text": str(p.get("icon", "◆")), "TextColor3": "@accentFg", "FontFace": font(R, "family", "heavy"),
            "TextSize": 40, "BackgroundColor3": "@surface2", "Size": [1, 0, 0, 96], "BorderSizePixel": 0},
            "children": [corner(R.theme["radius"]["md"])]}
    head = [{"ui": "text", "text": p.get("item", "Item"), "variant": "label", "truncate": True}]
    if p.get("tag"):
        head.append({"ui": "chip", "text": p["tag"], "tone": "accent"})
    if p.get("owned"):
        buy = {"ui": "button", "text": "Owned", "variant": "secondary", "width": "fill", "disabled": True}
    else:
        buy = {"ui": "button", "text": "◆ " + str(p.get("price", 0)), "variant": "primary", "width": "fill"}
    return common(p, c_card({"name": p.get("name", "ShopItem"), "padding": "md", "gap": "sm",
                             "width": p.get("width", 180), "children": [pic, {"ui": "column", "gap": "xs",
                                                                              "children": head}, buy]}, R))


@comp("leaderboard_row", "Rank / player / score row. {rank, player, score, me?}")
def c_lb_row(p, R):
    me = bool(p.get("me"))
    return common(p, c_row({"name": p.get("name", "Row"), "gap": "md", "width": "fill", "padding": "sm",
                            "radius": "md", "bg": "@accentSoft" if me else "@surface2",
                            "bg_transparency": 0 if me else 0.4, "children": [
        {"ui": "text", "text": "#" + str(p.get("rank", 1)), "variant": "mono", "width": 36, "color": "@muted"},
        {"ui": "avatar", "text": str(p.get("player", "?"))[:2].upper(), "size": 28, "tone": "accent"},
        {"ui": "text", "text": p.get("player", ""), "variant": "label", "grow": True, "truncate": True},
        {"ui": "text", "text": str(p.get("score", 0)), "variant": "mono", "width": "auto", "weight": "Bold"}]}, R))
