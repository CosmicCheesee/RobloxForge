"""Direction 2, pushed further ("Overhaul II"): the Overhaul layouts with the panel dressed on every side --
a spine down the left (facility name stacked letter by letter + status lights), a tick ruler down the right,
corner brackets, a bay tab above, a serial + barcode below -- a stat strip under every header, category
chips, richer detail cards, and a dense small-tile vault built to hold a lot.

No Rotation anywhere: the vertical name is stacked letters, so it renders the same in Roblox (rotation is
dropped under clipping ancestors) and in the offline preview.
"""
from hub import (ABILITIES, BALANCE, CARRIED, INVITES, MARKET, MATS, RECIPES, SALVAGE, SERVER, SQUAD, T,
                 hazard_stops, ingredient, preview, swatch)
from hub2 import CONTRA2, DOCKET2, MACHINE2

PANEL_W, PANEL_H = 1000, 602


# ------------------------------------------------------------------ frame dressing
def frame(name, **props):
    props.setdefault("BorderSizePixel", 0)
    return {"type": "Frame", "name": name, "props": props, "children": []}


def bracket(corner, col="@accent", arm=22, t=2, off=10):
    """An L at one corner of the wrapper, standing `off` px outside it."""
    x = {"tl": 0, "tr": 1, "bl": 0, "br": 1}[corner]
    y = {"tl": 0, "tr": 0, "bl": 1, "br": 1}[corner]
    sx, sy = (-off if x == 0 else off - arm), (-off if y == 0 else off - arm)
    h = frame("BracketH", Size=[0, arm, 0, t], Position=[x, sx, y, sy if y == 0 else sy + arm - t],
              BackgroundColor3=col, BackgroundTransparency=0.15)
    v = frame("BracketV", Size=[0, t, 0, arm], Position=[x, sx if x == 0 else sx + arm - t, y, sy],
              BackgroundColor3=col, BackgroundTransparency=0.15)
    return [h, v]


def led(col, name="Led"):
    return {"type": "Frame", "name": name, "props": {"Size": [0, 8, 0, 8], "BackgroundColor3": col, "BorderSizePixel": 0},
            "children": [{"type": "UICorner", "props": {"CornerRadius": 999}},
                         {"type": "UIStroke", "props": {"Color": col, "Thickness": 2, "Transparency": 0.7,
                                                        "ApplyStrokeMode": "Border"}}]}


def spine(word, leds):
    letters = "\n".join(word.upper().replace(" ", "·"))
    sp = frame("Spine", Size=[0, 30, 1, -96], Position=[0, -42, 0, 48], BackgroundColor3="@surface",
               BackgroundTransparency=0.05)
    sp["children"] = [
        {"type": "UICorner", "props": {"CornerRadius": 6}},
        {"type": "UIStroke", "props": {"Color": "@border", "Transparency": 0.35, "ApplyStrokeMode": "Border"}},
        {"type": "UIListLayout", "props": {"FillDirection": "Vertical", "HorizontalAlignment": "Center",
                                           "VerticalAlignment": "Top", "Padding": 10, "SortOrder": "LayoutOrder"}},
        {"type": "UIPadding", "props": {"PaddingTop": 12, "PaddingBottom": 12}},
        {"type": "Frame", "name": "Leds", "props": {"Size": [0, 8, 0, 0], "AutomaticSize": "Y",
                                                    "BackgroundTransparency": 1, "LayoutOrder": 0},
         "children": [{"type": "UIListLayout", "props": {"FillDirection": "Vertical", "Padding": 6,
                                                         "SortOrder": "LayoutOrder"}}] + [led(c, f"Led{i}") for i, c in enumerate(leds)]},
        {"type": "TextLabel", "name": "Word", "props": {
            "Text": letters, "Size": [0, 20, 0, 0], "AutomaticSize": "Y", "BackgroundTransparency": 1,
            "TextColor3": "@muted", "TextSize": 12, "LineHeight": 1.05, "LayoutOrder": 1,
            "FontFace": {"family": "RobotoMono", "weight": "Bold"}}}]
    return sp


def ruler(n=28):
    r = frame("Ruler", Size=[0, 16, 1, -96], Position=[1, 12, 0, 48], BackgroundTransparency=1)
    r["children"] = [{"type": "UIListLayout", "props": {"FillDirection": "Vertical", "Padding": [0.0, 0],
                                                        "VerticalFlex": "SpaceBetween", "SortOrder": "LayoutOrder"}}]
    for i in range(n):
        major = i % 5 == 0
        r["children"].append(frame(f"Tick{i}", Size=[0, 16 if major else 8, 0, 2], BackgroundColor3="@border",
                                   BackgroundTransparency=0.1 if major else 0.45, LayoutOrder=i))
    return r


def bay_tab(code, title, state="ONLINE", col="@success"):
    tab = {"ui": "row", "name": "BayTab", "gap": "sm", "padding": "xs", "radius": "sm", "bg": "@surface",
           "bg_transparency": 0.05, "border": True, "pos": [0, 0, 0, -38], "children": [
        led(col), T(code, "mono", width="auto", color="@accentFg"),
        T(title.upper(), "caption", width="auto", color="@muted"),
        T(state, "caption", width="auto", color=col)]}
    return tab


def serial(text):
    bars = frame("Barcode", Size=[0, 120, 0, 14], BackgroundTransparency=1)
    widths = [2, 1, 3, 1, 1, 2, 1, 3, 2, 1, 1, 2, 3, 1, 2, 1, 1, 3, 1, 2, 2, 1, 3, 1]
    bars["children"] = [{"type": "UIListLayout", "props": {"FillDirection": "Horizontal", "Padding": 2,
                                                           "SortOrder": "LayoutOrder"}}]
    for i, w in enumerate(widths):
        bars["children"].append(frame(f"B{i}", Size=[0, w, 1, 0], BackgroundColor3="@muted", BackgroundTransparency=0.35,
                                      LayoutOrder=i))
    return {"ui": "row", "name": "Serial", "gap": "md", "pos": [1, 0, 1, 18], "anchor": [1, 0], "children": [
        T(text, "caption", width="auto", color="@muted"), bars]}


def stat_strip(items):
    """Small key/value cells under the header."""
    cells = []
    for i, (k, v, tone) in enumerate(items):
        cells.append({"ui": "column", "gap": 0, "width": "auto", "padding": "xs", "order": i, "children": [
            T(k, "caption", width="auto"), T(v, "label", width="auto", color=tone or "@text",
                                             props={"FontFace": {"family": "RobotoMono", "weight": "Bold"}})]})
        if i < len(items) - 1:
            cells.append({"ui": "divider", "vertical": True, "order": i})
    return {"ui": "row", "name": "Stats", "gap": "md", "width": "fill", "padding": "xs", "radius": "md",
            "bg": "@surface2", "bg_transparency": 0.35, "children": cells}


def chips(labels, sel=0):
    return {"ui": "row", "gap": 6, "children": [
        {"ui": "button", "text": l, "variant": "soft" if i == sel else "ghost", "size": "sm", "pill": True, "order": i}
        for i, l in enumerate(labels)]}


def dressed(code, title, sub, stats, body, status, actions, word, leds, tape=False, search="Search", num=None):
    header = {"ui": "row", "justify": "between", "width": "fill", "align": "center", "children": [
        {"ui": "row", "gap": "md", "width": "auto", "children": [
            {"type": "TextLabel", "name": "Glyph", "props": {
                "Size": [0, 44, 0, 44], "BackgroundColor3": "@accentSoft", "Text": num or code[-2:],
                "TextColor3": "@accentFg", "TextSize": 18, "FontFace": {"family": "RobotoMono", "weight": "Bold"}},
             "children": [{"type": "UICorner", "props": {"CornerRadius": 10}},
                          {"type": "UIStroke", "props": {"Color": "@accent", "Transparency": 0.55,
                                                         "ApplyStrokeMode": "Border"}}]},
            {"ui": "column", "gap": 2, "width": "auto", "children": [T(title, "heading", width="auto"),
                                                                     T(sub, "caption", width="auto")]}]},
        {"ui": "row", "gap": "sm", "children": [
            {"ui": "input", "placeholder": search, "width": 200, "height": 34},
            {"ui": "currency", "amount": BALANCE, "icon": "◆", "tone": "accent"},
            {"ui": "icon_button", "icon": "×", "size": "sm", "attrs": {"ForgeRole": "dismiss"}}]}]}
    foot = {"ui": "row", "gap": "sm", "width": "fill", "justify": "between", "padding": "sm", "radius": "md",
            "bg": "@surface2", "bg_transparency": 0.2, "children": [
                {"ui": "row", "gap": "sm", "width": "auto", "children": [led("@success"),
                                                                          T(status, "caption", width="auto", color="@muted")]},
                {"ui": "row", "gap": "sm", "children": actions}]}
    kids = []
    if tape:
        kids.append({"type": "Frame", "name": "Tape", "props": {"Size": [1, 0, 0, 5], "BackgroundColor3": "@accent",
                                                                "BorderSizePixel": 0},
                     "children": [{"type": "UIGradient", "props": {"Color": hazard_stops(9, "#e9cf6e", "#1b1813")}},
                                  {"type": "UICorner", "props": {"CornerRadius": 2}}]})
    kids += [header, stat_strip(stats),
             {"ui": "column", "name": "Body", "grow": True, "width": "fill", "height": 120, "gap": "md", "children": body},
             foot]
    card = {"ui": "card", "name": "Panel", "padding": "xl", "gap": "md", "width": "fill", "height": "fill",
            "children": kids + [{"type": "UIGradient", "props": {"Color": ["#ffffff", "#e2e2e6"], "Rotation": 90}}]}
    wrap = frame("Wrap", Size=[0.86, 0, 0.8, 0], Position=[0.5, 0, 0.5, 0], AnchorPoint=[0.5, 0.5],
                 BackgroundTransparency=1)
    wrap["children"] = [{"type": "UISizeConstraint", "props": {"MaxSize": [PANEL_W, PANEL_H]}},
                        spine(word, leds), ruler(), bay_tab(code, title), serial(f"HUB-OPS  ·  {code}  ·  REV 4"),
                        *bracket("tl"), *bracket("tr"), *bracket("bl"), *bracket("br"), card]
    return {"ui": "screen", "name": title.replace(" ", ""), "children": [
        {"type": "Frame", "name": "City", "props": {"Size": "fill", "BackgroundColor3": "#05070a",
                                                    "BackgroundTransparency": 0, "BorderSizePixel": 0},
         "children": [{"type": "UIGradient", "props": {"Color": ["#2a3442", "#0b0e12", "#141a22"], "Rotation": 90}}]},
        wrap]}


# ------------------------------------------------------------------ tiles
TIER = {"$262": "@warning", "$184": "@accent", "$96": "@success", "$71": "@success", "$12": "@muted",
        "kept whole": "@border"}


def tile(title, sub, glyph="◆", selected=False, w=132, tier="@border"):
    return {"ui": "column", "name": "Tile", "gap": 6, "width": w, "align": "center", "padding": "sm", "radius": "md",
            "bg": "@accentSoft" if selected else "@surface2", "bg_transparency": 0, "border": True,
            "props": {"Size": [0, w, 0, 0]}, "children": [
                {"ui": "row", "justify": "between", "width": "fill", "children": [
                    frame("Tier", Size=[0, 26, 0, 4], BackgroundColor3=tier),
                    {"type": "TextLabel", "name": "Check", "props": {
                        "Size": [0, 18, 0, 18], "BackgroundColor3": "@accent", "BackgroundTransparency": 0 if selected else 1,
                        "Text": "✓" if selected else "", "TextColor3": "@accentText", "TextSize": 12,
                        "FontFace": {"family": "BuilderSans", "weight": "Bold"}},
                     "children": [{"type": "UICorner", "props": {"CornerRadius": 999}}]}]},
                preview(glyph, 60), T(title, "label", align="center", truncate=True),
                T(sub, "caption", align="center", truncate=True)]}


def mini(name, count=None, glyph="◆", tier="@border", sel=False):
    """Vault slot: 64 wide, glyph + short name + stack count."""
    kids = [{"type": "UICorner", "props": {"CornerRadius": 6}},
            {"type": "UIStroke", "props": {"Color": "@accent" if sel else "@border", "Transparency": 0.1 if sel else 0.5,
                                           "ApplyStrokeMode": "Border"}},
            frame("Tier", Size=[1, -12, 0, 2], Position=[0, 6, 0, 4], BackgroundColor3=tier),
            {"type": "TextLabel", "name": "Glyph", "props": {
                "Size": [1, 0, 0, 30], "Position": [0, 0, 0, 8], "BackgroundTransparency": 1, "Text": glyph,
                "TextColor3": "@muted", "TextSize": 18, "FontFace": {"family": "BuilderSans", "weight": "Bold"}}},
            {"type": "TextLabel", "name": "Name", "props": {
                "Size": [1, -6, 0, 14], "Position": [0, 3, 1, -18], "BackgroundTransparency": 1, "Text": name,
                "TextColor3": "@text", "TextSize": 11, "TextTruncate": "AtEnd",
                "FontFace": {"family": "BuilderSans", "weight": "Medium"}}}]
    if count:
        kids.append({"type": "TextLabel", "name": "Count", "props": {
            "Size": [0, 22, 0, 14], "Position": [1, -24, 0, 8], "BackgroundColor3": "@bg", "BackgroundTransparency": 0.2,
            "Text": f"x{count}", "TextColor3": "@accentFg", "TextSize": 11,
            "FontFace": {"family": "RobotoMono", "weight": "Bold"}},
            "children": [{"type": "UICorner", "props": {"CornerRadius": 4}}]})
    return {"type": "TextButton", "name": "Slot", "props": {
        "Size": [0, 64, 0, 64], "BackgroundColor3": "@accentSoft" if sel else "@surface2", "Text": "",
        "AutoButtonColor": False, "BorderSizePixel": 0}, "attrs": {"ForgeFx": "item"}, "children": kids}


# ------------------------------------------------------------------ the six facilities
def x_recycle():
    tiles = [tile(n, f"{kg} kg · {val}", g, selected=i in (0, 1, 3), tier=TIER.get(val, "@border"))
             for i, (n, kg, val, g) in enumerate(SALVAGE)]
    sell = []
    for i, (n, col, price, held) in enumerate(MATS[:5]):
        v = [0.2, 0, 0, 0.45, 0.52][i]
        sell.append({"ui": "column", "gap": 2, "width": "fill", "children": [
            {"ui": "row", "gap": "sm", "width": "fill", "children": [
                swatch(col, 8), T(n.title(), "label", grow=True),
                T(f"{int(held * v)} / {held}", "mono", width="auto", color="@muted")]},
            {"ui": "slider", "value": v}]})
    right = {"ui": "scroll", "gap": "md", "width": 300, "height": 100, "props": {"Size": [0, 300, 1, 0]}, "children": [
        {"ui": "card", "variant": "raised", "padding": "lg", "gap": "sm", "children": [
            T("Yield from 3 selected", "caption"), T("$542", "display", color="@accentFg"),
            {"ui": "stat_bar", "label": "Metal parts", "value": 0.7, "text": "+48", "tone": "accent", "width": "fill"},
            {"ui": "stat_bar", "label": "Plastic parts", "value": 0.35, "text": "+22", "tone": "warning", "width": "fill"},
            {"ui": "stat_bar", "label": "Tech", "value": 0.15, "text": "+3", "tone": "success", "width": "fill"},
            {"ui": "button", "text": "Recycle 3 items", "variant": "primary", "width": "fill", "size": "lg"}]},
        {"ui": "card", "padding": "lg", "gap": "md", "children": [
            {"ui": "row", "justify": "between", "width": "fill", "children": [
                T("Sell materials", "title", width="auto"), T("$2,720", "title", width="auto", color="@accentFg")]},
            {"ui": "column", "gap": "md", "children": sell}]}]}
    body = [{"ui": "row", "gap": "lg", "width": "fill", "align": "stretch", "grow": True, "height": 100, "children": [
        {"ui": "column", "gap": "sm", "grow": True, "width": 420, "props": {"Size": [0, 420, 1, 0], "AutomaticSize": "None"},
         "children": [{"ui": "row", "justify": "between", "width": "fill", "children": [
             chips(["All", "Furniture", "Electronics", "Junk"]),
             {"ui": "button", "text": "Select all", "variant": "ghost", "size": "sm"}]},
             {"ui": "scroll", "height": 100, "grow": True, "children": [
                 {"ui": "grid", "cell": [132, 168], "gap": "sm", "children": tiles}]}]},
        right]}]
    return dressed("BAY-01", "Extraction log", "breaking down pays more than selling whole",
                   [("Stashed", "6", None), ("Selected", "3", "@accentFg"), ("Bag", "14.2 / 50 kg", None),
                    ("Materials", "657", None), ("Best yield", "CRT monitor", "@warning")],
                   body, "Recycled 2 items · +$318", [{"ui": "button", "text": "Sell $2,720", "variant": "secondary"}],
                   "EXTRACTION", ["@success", "@accent", "@border"], tape=True)


def x_craft():
    lst = []
    for i, (name, desc, reqs, state, carried) in enumerate(RECIPES):
        tone = {"ready": "success", "missing": "danger", "bagfull": "warning"}[state]
        lst.append({"ui": "list_item", "title": name.title(), "subtitle": f"{len(reqs)} ingredients · {carried} carried",
                    "trailing": {"ui": "chip", "text": {"ready": "Ready", "missing": "Missing", "bagfull": "Bag full"}[state],
                                 "tone": tone}, "selected": i == 3, "order": i})
    name, desc, reqs, state, carried = RECIPES[3]
    facts = {"ui": "row", "gap": "sm", "width": "fill", "children": [
        {"ui": "column", "gap": 0, "grow": True, "width": "fill", "padding": "sm", "radius": "md", "bg": "@surface2",
         "bg_transparency": 0.3, "children": [T(k, "caption"), T(v, "label", props={"FontFace": {"family": "RobotoMono", "weight": "Bold"}})]}
        for k, v in [("Weight", "1.9 kg"), ("Uses", "6 rounds"), ("Build", "instant"), ("Carried", "0")]]}
    detail_body = [
        {"ui": "row", "gap": "lg", "width": "fill", "children": [
            preview("◆", 110),
            {"ui": "column", "gap": "xs", "grow": True, "width": "fill", "children": [
                {"ui": "row", "gap": 6, "children": [{"ui": "chip", "text": "Weapon", "tone": "accent"},
                                                     {"ui": "chip", "text": "Loud", "tone": "warning"}]},
                T(name.title(), "heading"), T(desc, "body", color="@muted")]}]},
        facts,
        T("Ingredients", "caption"),
        {"ui": "row", "gap": 6, "width": "fill", "wrap": True, "children": [ingredient(n, c, h, nd) for n, c, h, nd in reqs]},
        {"ui": "row", "gap": "sm", "width": "fill", "padding": "sm", "radius": "md", "bg": "@dangerFill",
         "bg_transparency": 0.7, "children": [T("⚠", "label", width="auto", color="@danger"),
                                              T("Missing 29 metal · 23 tech · 1 pistol body", "label", grow=True, color="@danger")]},
        {"ui": "button", "text": "Missing ingredients", "variant": "secondary", "size": "lg", "width": "fill", "disabled": True}]
    detail = {"ui": "card", "variant": "raised", "padding": "lg", "gap": 0, "grow": True, "width": 420, "children": [
        {"ui": "scroll", "height": 100, "props": {"Size": [1, 0, 1, 0]}, "gap": "md", "padding": 4, "children": detail_body}]}
    body = [{"ui": "row", "gap": "lg", "width": "fill", "align": "stretch", "grow": True, "height": 100, "children": [
        {"ui": "column", "gap": "sm", "width": 300, "children": [
            chips(["All", "Medical", "Traps", "Weapons"], sel=0),
            {"ui": "scroll", "height": 100, "grow": True, "gap": 2, "children": lst}]},
        detail]}]
    return dressed("BAY-02", "Fabrication", "what the bay can build",
                   [("Ready", "3 of 17", "@success"), ("Bag", "14.2 / 50 kg", None), ("Metal", "131", None),
                    ("Tech", "9", "@danger"), ("Dust", "12", None)],
                   body, "Built snare plate", [{"ui": "toggle", "label": "Only what I can build", "on": False, "width": "auto"}],
                   "FABRICATION", ["@success", "@accent", "@accent"])


VAULT_ITEMS = [("Revolver", None, "◆", "@warning"), ("Red card", 2, "◆", "@danger"), ("Blue card", 3, "◆", "@accent"),
               ("CRT monitor", None, "◉", "@warning"), ("Office chair", None, "◆", "@accent"), ("Filing box", 4, "☗", "@success"),
               ("Bandage", 5, "✚", "@success"), ("Driver clip", 6, "◆", "@accent"), ("Desk fan", 2, "⚙", "@success"),
               ("Wall clock", None, "○", "@border"), ("Mug", 7, "◆", "@muted"), ("Snare plate", 2, "◆", "@accent"),
               ("Door clamp", 3, "◆", "@accent"), ("Flare gun", None, "◆", "@warning"), ("Steel bat", None, "◆", "@accent"),
               ("Lantern", None, "☀", "@success"), ("Rope", 2, "∞", "@muted"), ("Map", None, "☗", "@muted"),
               ("Amber card", 1, "◆", "@warning"), ("Wrench", None, "⚙", "@accent"), ("Crowbar", None, "◆", "@accent"),
               ("Knife", None, "◆", "@accent"), ("Marker", 4, "◆", "@muted"), ("Speedloader", 3, "◉", "@accent"),
               ("Pistol body", None, "◆", "@warning"), ("Battery", 9, "⚡", "@success"), ("Fuse", 6, "◆", "@muted"),
               ("Keyring", None, "○", "@muted"), ("Tape", 3, "○", "@muted"), ("Radio", None, "◉", "@accent")]


def x_vault():
    carried = [mini(n, None, "◆", "@accent", sel=i == 1) for i, (n, _) in enumerate(CARRIED)]
    stored = [mini(n, c, g, t, sel=i == 0) for i, (n, c, g, t) in enumerate(VAULT_ITEMS)]
    carried_card = {"ui": "card", "padding": "md", "gap": "sm", "width": 236,
                    "props": {"Size": [0, 236, 1, 0], "AutomaticSize": "None"}, "children": [
        {"ui": "row", "justify": "between", "width": "fill", "children": [
            T("Carried", "title", width="auto"), T("4", "mono", width="auto", color="@muted")]},
        {"ui": "progress", "value": 6.2 / 50, "height": 4},
        T("6.2 / 50 kg", "caption"),
        {"ui": "scroll", "height": 60, "grow": True, "children": [
            {"ui": "grid", "cell": [64, 64], "gap": 6, "children": carried}]},
        {"ui": "button", "text": "Store all »", "variant": "primary", "width": "fill"}]}
    detail = {"ui": "row", "gap": "md", "width": "fill", "padding": "sm", "radius": "md", "bg": "@surface2",
              "bg_transparency": 0.3, "children": [
        preview("◆", 44),
        {"ui": "column", "gap": 2, "grow": True, "width": "fill", "children": [
            T("Revolver", "label"), T("1.9 kg · vaulted 3 days ago · weapon", "caption")]},
        {"ui": "button", "text": "« Take", "variant": "soft", "size": "sm"}]}
    vault_card = {"ui": "card", "padding": "md", "gap": "sm", "grow": True, "width": 400,
                  "props": {"Size": [0, 400, 1, 0], "AutomaticSize": "None"}, "children": [
        {"ui": "row", "justify": "between", "width": "fill", "children": [
            T("In the vault", "title", width="auto"),
            chips(["All", "Weapons", "Cards", "Tools", "Junk"], sel=0)]},
        {"ui": "row", "gap": "sm", "width": "fill", "children": [
            {"ui": "progress", "value": 30 / 60, "height": 4, "grow": True, "width": "fill"},
            T("30 / 60 slots", "caption", width="auto")]},
        {"ui": "scroll", "height": 60, "grow": True, "children": [
            {"ui": "grid", "cell": [64, 64], "gap": 6, "children": stored}]},
        detail]}
    body = [{"ui": "row", "gap": "md", "width": "fill", "align": "stretch", "grow": True, "height": 100,
             "children": [carried_card, vault_card]}]
    return dressed("BAY-03", "Vault", "what stays here cannot be taken off you",
                   [("Stored", "30 stacks", None), ("Items", "71", None), ("Value", "$18,420", "@accentFg"),
                    ("Slots", "30 / 60", None), ("Carried", "6.2 kg", None)],
                   body, "Stored bandage x2", [{"ui": "button", "text": "Sort by value", "variant": "ghost"}],
                   "VAULT", ["@success", "@success", "@accent"])


def x_upgrades():
    icons = ["◆", "▶", "⚙", "○"]
    cards = []
    for k, (name, blurb, lvl, now, nxt, cost) in enumerate(ABILITIES):
        cards.append({"ui": "card", "padding": "md", "gap": "sm", "width": "fill", "children": [
            {"ui": "row", "gap": "sm", "width": "fill", "children": [
                {"type": "TextLabel", "name": "Icon", "props": {
                    "Size": [0, 34, 0, 34], "BackgroundColor3": "@accentSoft", "Text": icons[k], "TextColor3": "@accentFg",
                    "TextSize": 16, "FontFace": {"family": "BuilderSans", "weight": "Bold"}},
                 "children": [{"type": "UICorner", "props": {"CornerRadius": 8}}]},
                {"ui": "column", "gap": 0, "grow": True, "width": "fill", "children": [
                    T(name.title(), "title", truncate=True), T(blurb, "caption", truncate=True)]},
                {"ui": "row", "gap": 2, "children": [T(str(lvl), "heading", width="auto", color="@accentFg"),
                                                     T("/20", "caption", width="auto")]}]},
            {"ui": "progress", "value": lvl / 20, "height": 6},
            {"ui": "row", "justify": "between", "width": "fill", "children": [
                T(f"{now}  →  {nxt}", "caption", width="auto", color="@text"),
                {"ui": "button", "text": cost, "variant": "primary" if lvl < 12 else "secondary", "size": "sm"}]}]})
    grid = {"ui": "grid", "cell": [300, 128], "gap": "md", "children": cards}
    floors = []
    for f in range(0, 8):
        cur, unlocked = f == 3, f <= 5
        floors.append({"ui": "row", "gap": "sm", "width": "fill", "padding": "xs", "radius": "sm",
                       "bg": "@accentSoft" if cur else "@surface2", "bg_transparency": 0 if cur else 0.5, "order": f,
                       "children": [T(f"{-f if f else 0}", "mono", width=36, align="center",
                                      color="@accentFg" if cur else ("@text" if unlocked else "@muted")),
                                    T("you start here" if cur else ("open" if unlocked else f"{3 + f} dust"), "caption",
                                      grow=True, color="@accentFg" if cur else "@muted"),
                                    led("@accent" if cur else ("@success" if unlocked else "@border"))]})
    elevator = {"ui": "card", "variant": "raised", "padding": "md", "gap": "sm", "width": 220,
                "props": {"Size": [0, 220, 1, 0], "AutomaticSize": "None"}, "children": [
        {"ui": "row", "justify": "between", "width": "fill", "children": [T("Descent", "title", width="auto"),
                                                                         T("5 open", "caption", width="auto")]},
        {"ui": "scroll", "height": 60, "grow": True, "gap": 3, "children": floors},
        {"ui": "stat_bar", "label": "Anomalous dust", "value": 12 / 20, "text": "12 / 9", "tone": "accent", "width": "fill"},
        {"ui": "button", "text": "Unlock floor -6", "variant": "primary", "width": "fill"}]}
    body = [{"ui": "row", "gap": "lg", "width": "fill", "align": "stretch", "grow": True, "height": 100, "children": [
        {"ui": "column", "gap": "sm", "grow": True, "width": 620, "children": [
            T("Permanent · these come back up with you", "caption"),
            {"ui": "scroll", "height": 100, "grow": True, "children": [grid,
                {"ui": "row", "gap": "md", "width": "fill", "padding": "md", "radius": "md", "bg": "@surface2",
                 "bg_transparency": 0.3, "children": [
                    T("Wide lamp", "label", width="auto"), T("A broader beam from the same battery.", "caption", grow=True),
                    {"ui": "chip", "text": "Owned", "tone": "success"}]}]}]},
        elevator]}]
    return dressed("BAY-04", "Upgrades", "you can always start higher than you have unlocked",
                   [("Levels", "23 / 80", "@accentFg"), ("Spent", "$11,240", None), ("Dust", "12", None),
                    ("Deepest", "-5", None), ("Start", "-3", "@accentFg")],
                   body, "Bought load bearing 12", [], "UPGRADES", ["@accent", "@accent", "@success"])


def x_market():
    lots = []
    for num, name, tag, price, held, state in MARKET:
        ok = state == "buy"
        lots.append({"ui": "card", "padding": "md", "gap": "sm", "width": "fill", "variant": "raised", "children": [
            {"ui": "row", "gap": "md", "width": "fill", "children": [
                {"type": "TextLabel", "name": "Lot", "props": {
                    "Size": [0, 46, 0, 46], "BackgroundColor3": "@accent", "BackgroundTransparency": 0.85, "Text": num,
                    "TextColor3": "@accentFg", "TextSize": 26, "FontFace": {"family": "Oswald", "weight": "Bold"}}},
                preview("◆", 60),
                {"ui": "column", "gap": 2, "grow": True, "width": "fill", "children": [
                    T(name, "title", props={"FontFace": {"family": "SpecialElite", "weight": "Regular"}, "TextSize": 19}),
                    T(tag.split("  ·  ")[0] + "  ·  " + tag.split("  ·  ")[1], "caption"),
                    T(held, "caption", color="@success" if "BAG" in held else "@muted")]}]},
            {"ui": "row", "gap": "sm", "width": "fill", "children": [
                {"type": "TextLabel", "name": "Sticker", "props": {
                    "Size": [0, 128, 0, 40], "BackgroundColor3": "#cfba86", "Text": price, "TextColor3": "#26170f",
                    "TextSize": 21, "FontFace": {"family": "PermanentMarker", "weight": "Regular"}}},
                {"ui": "button", "text": "BUY" if ok else "SHORT $1,866", "variant": "primary" if ok else "secondary",
                 "size": "lg", "grow": True, "width": "fill",
                 "props": {"FontFace": {"family": "Oswald", "weight": "Bold"}, "TextSize": 22 if ok else 16,
                           "TextColor3": "@accentText" if ok else "@danger"}}]}]})
    body = [{"ui": "row", "justify": "between", "width": "fill", "children": [
        T("UNDER THE COUNTER · CASH ONLY", "title", width="auto",
          props={"FontFace": {"family": "SpecialElite", "weight": "Regular"}}),
        {"ui": "row", "gap": "sm", "children": [
            {"ui": "chip", "text": "stock turns over in 04:12", "tone": "neutral"},
            {"type": "TextLabel", "name": "Stamp", "props": {
                "Size": [0, 140, 0, 28], "BackgroundTransparency": 1, "Text": "CONTRABAND", "TextColor3": "@accentFg",
                "TextSize": 17, "FontFace": {"family": "SpecialElite", "weight": "Regular"}},
             "children": [{"type": "UIStroke", "props": {"Color": "@accent", "Thickness": 2, "Transparency": 0.2,
                                                          "ApplyStrokeMode": "Border"}}]}]}]},
        {"ui": "scroll", "height": 100, "grow": True, "children": [
            {"ui": "grid", "cell": [436, 148], "gap": "md", "children": lots}]}]
    return dressed("STALL-6", "Black market", "no questions · no receipts",
                   [("Cash", BALANCE, "@accentFg"), ("Bag", "14.2 / 50 kg", None), ("Lots", "4", None),
                    ("Heat", "low", "@success"), ("Fence", "in", "@success")],
                   body, "Bought amber keycard", [], "CONTRABAND", ["@danger", "@accent", "@border"], num="06")


def x_squad():
    seats = []
    for n, sub, me in SQUAD:
        seats.append({"ui": "card", "variant": "raised", "padding": "md", "gap": "xs", "align": "center", "width": "fill",
                      "children": [{"ui": "avatar", "text": n[:2].upper(), "size": 56, "props": {"TextSize": 20}},
                                   T(n, "label", align="center", truncate=True), T(sub, "caption", align="center"),
                                   {"ui": "row", "gap": 4, "justify": "center", "width": "fill", "children": [
                                       {"ui": "chip", "text": "Ready", "tone": "success"},
                                       {"ui": "chip", "text": "14 kg", "tone": "neutral"}]},
                                   {"ui": "button", "text": "Leave" if me else "Remove",
                                    "variant": "danger" if me else "secondary", "size": "sm", "width": "fill"}]})
    for i in range(2):
        seats.append({"ui": "card", "variant": "outline", "padding": "md", "gap": "xs", "align": "center", "width": "fill",
                      "children": [{"type": "TextLabel", "name": "Open", "props": {
                          "Size": [0, 56, 0, 56], "BackgroundTransparency": 1, "Text": "+", "TextColor3": "@subtle",
                          "TextSize": 28, "FontFace": {"family": "BuilderSans", "weight": "Bold"}},
                          "children": [{"type": "UIStroke", "props": {"Color": "@border", "ApplyStrokeMode": "Border"}},
                                       {"type": "UICorner", "props": {"CornerRadius": 999}}]},
                          T("Open seat", "label", align="center", color="@muted"),
                          T("invite from the list", "caption", align="center")]})
    seat_grid = {"ui": "grid", "cell": [196, 196], "gap": "md", "children": seats}
    banner = {"ui": "row", "gap": "md", "width": "fill", "padding": "sm", "radius": "md", "bg": "@accentSoft",
              "children": [{"ui": "avatar", "text": "KR", "size": 32},
                           T(f"{INVITES[0]} wants you along", "label", grow=True, color="@accentFg"),
                           {"ui": "button", "text": "Accept", "variant": "primary", "size": "sm"},
                           {"ui": "button", "text": "Decline", "variant": "ghost", "size": "sm"}]}
    here = [{"ui": "list_item", "title": n, "subtitle": s, "avatar": n[:2].upper(), "order": i,
             "trailing": {"ui": "button", "text": "In a squad" if taken else "Invite",
                          "variant": "secondary" if taken else "soft", "size": "sm", "disabled": taken}}
            for i, (n, s, taken) in enumerate(SERVER)]
    body = [banner, {"ui": "row", "gap": "lg", "width": "fill", "align": "stretch", "grow": True, "height": 100, "children": [
        {"ui": "scroll", "height": 100, "grow": True, "width": 420, "props": {"Size": [0, 420, 1, 0]},
         "children": [seat_grid]},
        {"ui": "column", "gap": "sm", "width": 280, "children": [
            {"ui": "row", "justify": "between", "width": "fill", "children": [
                T("In this server", "title", width="auto"), T("3", "mono", width="auto", color="@muted")]},
            {"ui": "scroll", "height": 100, "grow": True, "gap": 2, "children": here}]}]}]
    return dressed("DESK-5", "Squad", "a squad lands together",
                   [("Seats", "2 / 4", "@accentFg"), ("Ready", "2", "@success"), ("Invites", "1", "@accentFg"),
                    ("Server", "5 players", None), ("Lands on", "floor -3", None)],
                   body, "Invited pallid", [{"ui": "button", "text": "Start descent", "variant": "primary"}],
                   "SQUAD", ["@success", "@success", "@border"], tape=True, num="05")


OVERHAUL2 = [("EXTRACTION LOG", x_recycle, DOCKET2), ("FABRICATION", x_craft, MACHINE2), ("VAULT", x_vault, MACHINE2),
             ("UPGRADES", x_upgrades, MACHINE2), ("BLACK MARKET", x_market, CONTRA2), ("SQUAD", x_squad, DOCKET2)]
