"""Remakes of the Scrap Hub's facility panels (ReplicatedStorage.HubMenus), two directions.

Rules carried over from HubMenus' own notes (the designer's calls): no tab row -- each facility opens alone from
its sign; no subtitle sentence; header = facility name + balance; one search/filter bar; one footer with
what just happened on the left and the action on the right; the SKIN follows the facility (docket paper
for the extraction log and squad, machine readout for fabrication / vault / upgrades, contraband for the
black market). Content is the real catalogue: LootDefs resources, recipes, ability ladders, descent,
market stock. Object previews (ViewportFrames in game) are drawn as placeholders here.
"""

# ------------------------------------------------------------------ real data (from LootDefs)
MATS = [("RUBBER PARTS", "#4a4846", 6, 212), ("PLASTIC PARTS", "#cec6b0", 7, 58), ("FABRIC", "#b29c7c", 8, 17),
        ("METAL PARTS", "#989ca2", 10, 131), ("CHEMICALS", "#7ec4d6", 22, 230), ("TECH", "#60c88c", 44, 9),
        ("ANOMALOUS DUST", "#c68ae2", 112, 12)]
SALVAGE = [("OFFICE CHAIR", 6.5, "$184", "◆"), ("DESK FAN", 2.1, "$96", "⚙"), ("FILING BOX", 3.2, "$71", "☗"),
           ("CRT MONITOR", 9.0, "$262", "◉"), ("WALL CLOCK", 1.4, "kept whole", "○"), ("MUG", 0.3, "$12", "◆")]
RECIPES = [
    ("BANDAGE", "Stops bleeding. Five to a roll.", [("FABRIC", "#b29c7c", 40, 28), ("CHEM", "#7ec4d6", 230, 12)], "ready", 2),
    ("DOOR CLAMP", "Wedges a door so nothing opens it from the far side.",
     [("METAL", "#989ca2", 131, 38), ("RUBBER", "#4a4846", 212, 8)], "ready", 0),
    ("SNARE PLATE", "Pins whatever steps on it for six seconds.",
     [("METAL", "#989ca2", 131, 62), ("RUBBER", "#4a4846", 212, 12), ("PLASTIC", "#cec6b0", 58, 8)], "ready", 1),
    ("REVOLVER", "Six rounds. Loud. Brings the floor to you.",
     [("METAL", "#989ca2", 131, 160), ("TECH", "#60c88c", 9, 32), ("CHEM", "#7ec4d6", 230, 40),
      ("DUST", "#c68ae2", 12, 6), ("PISTOL BODY", "#96badc", 0, 1)], "missing", 0),
    ("FLARE GUN", "One flare. Lights a room for a minute.",
     [("CHEM", "#7ec4d6", 230, 150), ("METAL", "#989ca2", 131, 100), ("DUST", "#c68ae2", 12, 8)], "bagfull", 0),
]
CARRIED = [("STEEL BAT", 2.1), ("BANDAGE", 0.4), ("DRIVER CLIP", 1.6), ("DESK FAN", 2.1)]
VAULTED = [("REVOLVER", 1.9, "vaulted"), ("RED CARD", 0.1, "vaulted"), ("CRT MONITOR", 9.0, "extracted"),
           ("OFFICE CHAIR", 6.5, "extracted"), ("FILING BOX", 3.2, "extracted")]
ABILITIES = [("REINFORCED FRAME", "Carry more before the weight tells.", 7, "+4.5 kg carried", "+5.0 kg carried", "$484"),
             ("CONDITIONING", "Faster on your feet, loaded or not.", 4, "+2.8% move speed", "+3.5% move speed", "$393"),
             ("LOAD BEARING", "A full bag costs you less speed.", 12, "-16.8% load penalty", "-18.2% load penalty", "$899"),
             ("SOFT STEP", "They hear you from closer in.", 0, "-0.0% noise carried", "-1.0% noise carried", "$270")]
MARKET = [("01", "BLUE KEYCARD", "KEYCARD  ·  0.1 KG  ·  ONE DOOR, ONE CARD", "$2,000", "NONE ON YOU", "buy"),
          ("02", "AMBER KEYCARD", "KEYCARD  ·  0.1 KG  ·  ONE DOOR, ONE CARD", "$4,400", "1 IN YOUR BAG", "buy"),
          ("03", "RED KEYCARD", "KEYCARD  ·  0.1 KG  ·  ONE DOOR, ONE CARD", "$9,000", "NONE ON YOU", "buy"),
          ("04", "PISTOL BODY", "HARDWARE  ·  1.2 KG  ·  THE FABRICATOR MAKES IT A REVOLVER", "$10,000", "NONE ON YOU",
           "short")]
SQUAD = [("player_one", "leader  ·  in the hub", True), ("orchid_77", "in the hub", False)]
INVITES = ["kite_runner"]
SERVER = [("pallid", "friend", False), ("vexillum", "in the hub", True), ("nightjar", "in the hub", False)]
BALANCE = "$47,866"

# ------------------------------------------------------------------ the three skins, direction 1 (Refit)
BASE = {"radius": {"sm": 2, "md": 3, "lg": 3, "pill": 999}, "stroke": 1, "scrimT": 0.45,
        "space": {"xs": 4, "sm": 8, "md": 12, "lg": 16, "xl": 24, "xxl": 32},
        "size": {"caption": 12, "label": 13, "body": 14, "title": 17, "heading": 24, "display": 30}}

DOCKET = {**BASE, "extends": "backroom", "name": "docket",
          "color": {"bg": "#0d0c0a", "surface": "#1a1712", "surface2": "#24201a", "raised": "#2b261e",
                    "border": "#5a4c32", "text": "#e9e4d4", "muted": "#a8a08a", "subtle": "#7a7362",
                    "accent": "#e9d892", "accentFg": "#e9d892", "accentText": "#14110a", "accentSoft": "#332d1d",
                    "success": "#9ed096", "warning": "#e2c47e", "danger": "#e08a7e", "dangerFill": "#4a221f",
                    "dangerText": "#f2d0c8", "scrim": "#000000"},
          "font": {"family": "Inconsolata", "display": "Inconsolata", "mono": "Inconsolata",
                   "regular": "Regular", "medium": "Medium", "strong": "Bold", "heavy": "Bold"},
          "surfaceT": 0.04, "strokeT": 0.35}
MACHINE = {**BASE, "extends": "backroom", "name": "machine",
           "color": {"bg": "#070a0e", "surface": "#0e1319", "surface2": "#141c25", "raised": "#1a2430",
                     "border": "#33495a", "text": "#e1e8ee", "muted": "#94a5b3", "subtle": "#6c7e8c",
                     "accent": "#96badc", "accentFg": "#a9c9e6", "accentText": "#06121c", "accentSoft": "#18283a",
                     "success": "#9ed096", "warning": "#e2c47e", "danger": "#e08a7e", "dangerFill": "#4a221f",
                     "dangerText": "#f2d0c8", "scrim": "#000000"},
           "font": {"family": "Inconsolata", "display": "Inconsolata", "mono": "Inconsolata",
                    "regular": "Regular", "medium": "Medium", "strong": "Bold", "heavy": "Bold"},
           "surfaceT": 0.04, "strokeT": 0.3, "radius": {"sm": 1, "md": 2, "lg": 2, "pill": 999}}
CONTRA = {**BASE, "extends": "backroom", "name": "contraband",
          "color": {"bg": "#0b0907", "surface": "#15120f", "surface2": "#221d18", "raised": "#2a241e",
                    "border": "#5a4a3a", "text": "#e2d4b6", "muted": "#ab9c84", "subtle": "#7d705e",
                    "accent": "#cc4a36", "accentFg": "#e8826e", "accentText": "#f6ead2", "accentSoft": "#3a1d16",
                    "success": "#9ed096", "warning": "#e2c47e", "danger": "#e8826e", "dangerFill": "#5a2018",
                    "dangerText": "#f6ead2", "scrim": "#000000"},
          "font": {"family": "Oswald", "display": "SpecialElite", "mono": "SpecialElite",
                   "regular": "Regular", "medium": "Medium", "strong": "Bold", "heavy": "Bold"},
          "surfaceT": 0.02, "strokeT": 0.3, "radius": {"sm": 0, "md": 0, "lg": 0, "pill": 999}}


# ------------------------------------------------------------------ shared pieces
def T(text, variant="body", **kw):
    return {"ui": "text", "text": text, "variant": variant, **kw}


def swatch(col, size=8):
    return {"type": "Frame", "name": "Swatch", "props": {"Size": [0, size, 0, size], "BackgroundColor3": col,
                                                         "BorderSizePixel": 0}}


def preview(glyph="◆", size=44):
    """The game draws the real object in a ViewportFrame here."""
    return {"type": "TextLabel", "name": "Preview", "props": {
        "Size": [0, size, 0, size], "BackgroundColor3": "@surface2", "BorderSizePixel": 0, "Text": glyph,
        "TextColor3": "@subtle", "TextSize": int(size * 0.42), "FontFace": {"family": "BuilderSans", "weight": "Bold"}},
        "children": [{"type": "UIStroke", "props": {"Color": "@border", "Transparency": 0.4, "ApplyStrokeMode": "Border"}},
                     {"type": "UICorner", "props": {"CornerRadius": "@radius.sm"}}]}


def section(title, right=None):
    kids = [T(title, "caption", width="auto", color="@accentFg", props={"FontFace": {"family": "Inconsolata", "weight": "Bold"}})]
    if right:
        kids.append(right)
    return {"ui": "row", "justify": "between", "width": "fill", "children": kids}


def ingredient(name, col, have, need):
    ok = have >= need
    tone = "@success" if ok else "@danger"
    frac = max(0.0, min(1.0, have / max(need, 1)))
    return {"type": "Frame", "name": "Chip", "props": {"Size": [0, 122, 0, 40], "BackgroundColor3": "@surface2",
                                                       "BorderSizePixel": 0},
            "children": [
                {"type": "UIStroke", "props": {"Color": tone, "Transparency": 0.55 if ok else 0.2, "ApplyStrokeMode": "Border"}},
                {"type": "UICorner", "props": {"CornerRadius": 2}},
                {"type": "Frame", "name": "Sw", "props": {"Position": [0, 7, 0, 8], "Size": [0, 6, 0, 6],
                                                          "BackgroundColor3": col, "BorderSizePixel": 0}},
                {"type": "TextLabel", "name": "Name", "props": {
                    "Position": [0, 18, 0, 3], "Size": [1, -24, 0, 16], "BackgroundTransparency": 1, "Text": name,
                    "TextXAlignment": "Left", "TextColor3": "@muted", "TextSize": 12,
                    "FontFace": {"family": "Inconsolata", "weight": "Medium"}}},
                {"type": "TextLabel", "name": "Count", "props": {
                    "Position": [0, 7, 0, 18], "Size": [1, -14, 0, 16], "BackgroundTransparency": 1,
                    "Text": f"{min(have, 99999)} / {need}", "TextXAlignment": "Left", "TextColor3": "@text",
                    "TextSize": 14, "FontFace": {"family": "Inconsolata", "weight": "Bold"}}},
                {"type": "TextLabel", "name": "Short", "props": {
                    "Position": [0, 7, 0, 18], "Size": [1, -14, 0, 16], "BackgroundTransparency": 1,
                    "Text": "OK" if ok else f"-{need - have}", "TextXAlignment": "Right", "TextColor3": tone,
                    "TextSize": 13, "FontFace": {"family": "Inconsolata", "weight": "Bold"}}},
                {"type": "Frame", "name": "Bar", "props": {"Position": [0, 6, 1, -5], "Size": [1, -12, 0, 2],
                                                           "BackgroundColor3": "@border", "BorderSizePixel": 0},
                 "children": [{"type": "Frame", "name": "Fill", "props": {"Size": [frac, 0, 1, 0],
                                                                         "BackgroundColor3": tone, "BorderSizePixel": 0}}]}]}


def stepper(qty, have):
    small = {"variant": "secondary", "size": "sm"}
    return {"ui": "row", "gap": 4, "children": [
        {"ui": "icon_button", "icon": "-", **small, "round": False},
        {"type": "TextLabel", "name": "Qty", "props": {"Size": [0, 52, 0, 32], "BackgroundColor3": "@bg",
                                                       "BackgroundTransparency": 0.2, "Text": str(qty),
                                                       "TextColor3": "@text", "TextSize": 14,
                                                       "FontFace": {"family": "Inconsolata", "weight": "Bold"}},
         "children": [{"type": "UICorner", "props": {"CornerRadius": 2}}]},
        {"ui": "icon_button", "icon": "+", **small, "round": False},
        {"ui": "button", "text": "MAX", "variant": "ghost", "size": "sm"}]}


def pips(level, total=20, w=18):
    return {"ui": "row", "gap": 3, "children": [
        {"type": "Frame", "name": f"P{i}", "props": {
            "Size": [0, w, 0, 8], "BorderSizePixel": 0, "LayoutOrder": i,
            "BackgroundColor3": "@accent" if i < level else "@border",
            "BackgroundTransparency": 0.05 if i < level else 0.5}} for i in range(total)]}


def hazard_stops(n=9, a="#e9d892", b="#14110a"):
    """Hard-edged stripes from a ColorSequence (max 20 keypoints): each stripe is two keypoints a hair apart."""
    stops = []
    for i in range(n + 1):
        t = i / n
        col = a if i % 2 == 0 else b
        if i:
            stops.append([min(1.0, t - 1e-4), a if (i - 1) % 2 == 0 else b])
        stops.append([t, col])
    return stops[:20]


def hub_panel(title, sub, body, status, actions, search="SEARCH", filter_text="ALL", width=1000, height=602,
              tape=False, stamp=None):
    """The one hub card: header (name + subhead + balance + close), search bar, body, footer."""
    header_left = [T(title, "heading", width="auto"), T(sub, "caption", width="auto")]
    header = {"ui": "row", "justify": "between", "width": "fill", "align": "start", "children": [
        {"ui": "column", "gap": 2, "width": "auto", "children": header_left},
        {"ui": "row", "gap": "sm", "children": [{"ui": "currency", "amount": BALANCE, "icon": "◆", "tone": "accent"},
                                                {"ui": "icon_button", "icon": "×", "size": "sm",
                                                 "attrs": {"ForgeRole": "dismiss"}}]}]}
    bar = {"ui": "row", "gap": "sm", "width": "fill", "children": [
        {"ui": "input", "placeholder": search, "grow": True, "width": "fill", "height": 32},
        {"ui": "button", "text": filter_text, "variant": "secondary", "size": "sm"}]}
    foot = {"ui": "row", "gap": "sm", "width": "fill", "justify": "between", "children": [
        T(status, "caption", width="auto", color="@muted"), {"ui": "row", "gap": "sm", "children": actions}]}
    kids = []
    if tape:
        kids.append({"type": "Frame", "name": "Tape", "props": {"Size": [1, 0, 0, 6], "BackgroundColor3": "@accent",
                                                                "BorderSizePixel": 0},
                     "children": [{"type": "UIGradient", "props": {"Color": hazard_stops(), "Rotation": 0}}]})
    kids += [header, {"ui": "divider"}, bar,
             {"ui": "column", "name": "Body", "grow": True, "width": "fill", "height": 120, "gap": "sm",
              "children": body},
             {"ui": "divider"}, foot]
    card = {"ui": "card", "name": "Panel", "padding": "xl", "gap": "md", "width": [0.96, 0], "height": [0.94, 0],
            "pos": [0.5, 0, 0.5, 0], "anchor": [0.5, 0.5], "max_w": width, "max_h": height, "children": kids}
    if stamp:
        card["children"].insert(0, stamp)
    return {"ui": "screen", "name": title.replace(" ", ""), "children": [
        {"type": "Frame", "name": "City", "props": {"Size": "fill", "BackgroundColor3": "#05070a",
                                                    "BackgroundTransparency": 0, "BorderSizePixel": 0},
         "children": [{"type": "UIGradient", "props": {"Color": ["#2a3442", "#0b0e12", "#141a22"], "Rotation": 90}}]},
        card]}


def row(children, h=None, pad="sm", sel=False, stripe=None, bg="@surface2"):
    r = {"ui": "row", "gap": "md", "width": "fill", "padding": pad, "radius": "sm", "bg": bg,
         "bg_transparency": 0 if sel else 0.35, "children": children}
    if stripe:
        r["children"] = [{"type": "Frame", "name": "Stripe", "props": {"Size": [0, 4, 0, 52], "BackgroundColor3": stripe,
                                                                       "BorderSizePixel": 0}}] + children
    if sel:
        r["border"] = True
    return r


# ------------------------------------------------------------------ direction 1: REFIT (the six facilities)
def r_recycle():
    items = []
    for i, (n, kg, val, g) in enumerate(SALVAGE):
        sel = i in (0, 1, 3)
        whole = val == "kept whole"
        items.append(row([preview(g, 40),
                          {"ui": "column", "gap": 2, "grow": True, "width": "fill", "children": [
                              T(n, "label"), T(f"{kg} kg  ·  {val}{'' if whole else ' in materials'}", "caption")]},
                          T("■" if sel else ("—" if whole else "□"), "title", width=28, align="center",
                            color="@accent" if sel else "@subtle")], sel=sel))
    mats = []
    for i, (n, col, price, held) in enumerate(MATS[:5]):
        qty = [40, 0, 0, 60, 120][i]
        mats.append({"ui": "column", "gap": 6, "width": "fill", "padding": "sm", "radius": "sm", "bg": "@surface2",
                     "bg_transparency": 0.35, "children": [
            {"ui": "row", "gap": "sm", "width": "fill", "children": [
                swatch(col), T(n, "label", grow=True),
                T(f"${qty * price:,}", "label", width="auto", color="@accentFg" if qty else "@muted")]},
            {"ui": "row", "gap": "sm", "width": "fill", "justify": "between", "children": [
                T(f"{held} held  ·  ${price} each", "caption", width="auto"), stepper(qty, held)]}]})
    body = [{"ui": "row", "gap": "lg", "width": "fill", "align": "stretch", "grow": True, "height": 100, "children": [
        {"ui": "column", "gap": "sm", "grow": True, "width": 520, "children": [
            section("BREAK DOWN  ·  WHAT CAME UP WITH YOU", {"ui": "button", "text": "CLEAR", "variant": "ghost", "size": "sm"}),
            {"ui": "scroll", "height": 100, "grow": True, "gap": "xs", "children": items}]},
        {"ui": "divider", "vertical": True},
        {"ui": "column", "gap": "sm", "width": 340, "children": [
            section("SELL  ·  MATERIALS"),
            {"ui": "scroll", "height": 100, "grow": True, "gap": "xs", "children": mats}]}]}]
    return hub_panel("EXTRACTION LOG", "6 stored  ·  breaking down pays more than selling whole", body,
                     "3 selected  ·  220 materials queued to sell",
                     [{"ui": "button", "text": "RECYCLE 3  ·  $542", "variant": "secondary"},
                      {"ui": "button", "text": "SELL  ·  $2,720", "variant": "primary"}], tape=True)


def r_craft():
    rows = []
    for name, desc, reqs, state, carried in RECIPES:
        col = {"ready": "@success", "missing": "@danger", "bagfull": "@warning"}[state]
        missing = [f"{need - have} {n}" for n, _, have, need in reqs if have < need]
        verdict = ("MISSING  " + "  ·  ".join(missing)) if missing else (
            "READY TO BUILD" if state == "ready" else "READY -- BUT NO ROOM IN YOUR BAG")
        rows.append(row([
            preview("✚" if name == "BANDAGE" else "◆", 60),
            {"ui": "column", "gap": 4, "width": 230, "children": [
                T(name, "label"), T(desc, "caption"), T(verdict, "caption", color=col, truncate=True)]},
            {"ui": "row", "gap": 6, "grow": True, "width": 260, "wrap": True, "children": [
                ingredient(n, c, h, nd) for n, c, h, nd in reqs]},
            {"ui": "column", "gap": 4, "width": 120, "align": "center", "children": [
                {"ui": "button", "text": {"ready": "BUILD", "missing": "MISSING", "bagfull": "BAG FULL"}[state],
                 "variant": "primary" if state == "ready" else "secondary", "width": "fill", "disabled": state != "ready"},
                T(f"{carried} carried", "caption", align="center")]}], stripe=col))
    body = [section("WHAT THE BAY CAN BUILD"), {"ui": "scroll", "height": 100, "grow": True, "gap": "xs", "children": rows}]
    return hub_panel("FABRICATION", "3 of 17 ready  ·  14.2 / 50.0 kg carried", body,
                     "built: SNARE PLATE  ·  metal -62  rubber -12  plastic -8",
                     [{"ui": "button", "text": "WHAT I CAN BUILD", "variant": "ghost"}], filter_text="ALL")


def r_vault():
    def col(title, data, store):
        rs = []
        for d in data:
            n, kg = d[0], d[1]
            where = "on you" if store else d[2]
            rs.append(row([preview("◆", 40), {"ui": "column", "gap": 2, "grow": True, "width": "fill", "children": [
                T(n, "label"), T(f"{kg} kg  ·  {where}", "caption")]},
                {"ui": "icon_button", "icon": "»" if store else "«", "variant": "secondary", "size": "sm",
                 "round": False}]))
        return {"ui": "column", "gap": "sm", "grow": True, "width": 300, "children": [
            section(title, T(f"{len(data)}", "caption", width="auto")),
            {"ui": "scroll", "height": 100, "grow": True, "gap": "xs", "children": rs}]}
    body = [{"ui": "row", "gap": "lg", "width": "fill", "align": "stretch", "grow": True, "height": 100, "children": [
        col("CARRIED", CARRIED, True), {"ui": "divider", "vertical": True}, col("IN THE VAULT", VAULTED, False)]}]
    return hub_panel("VAULT", "6.2 / 50.0 kg carried  ·  5 stored", body, "stored: BANDAGE",
                     [{"ui": "button", "text": "STORE EVERYTHING CARRIED", "variant": "primary"}])


def r_upgrades():
    rows = []
    for name, blurb, lvl, now, nxt, cost in ABILITIES:
        rows.append(row([{"ui": "column", "gap": 5, "grow": True, "width": "fill", "children": [
            {"ui": "row", "gap": "sm", "children": [T(name, "label", width="auto"),
                                                    T(f"{lvl}/20", "label", width="auto", color="@accentFg")]},
            T(blurb, "caption"), pips(lvl, 20, 16), T(f"{now}  →  {nxt}", "caption", color="@text")]},
            {"ui": "button", "text": cost, "variant": "primary" if lvl < 12 else "secondary", "width": 120}]))
    rows.append(row([{"ui": "column", "gap": 3, "grow": True, "width": "fill", "children": [
        T("WIDE LAMP", "label"), T("A broader beam from the same battery.", "caption")]},
        {"ui": "button", "text": "OWNED", "variant": "secondary", "width": 120, "disabled": True}]))
    descent = {"ui": "scroll", "gap": "md", "width": 250, "height": 100, "props": {"Size": [0, 250, 1, 0]}, "children": [
        section("DESCENT"),
        T("YOU START ON", "caption", align="center"),
        T("-3", "display", align="center", color="@accent", size=48),
        {"ui": "row", "gap": "sm", "width": "fill", "justify": "between", "children": [
            {"ui": "button", "text": "‹", "variant": "secondary", "width": 56},
            T("5 unlocked", "caption", width="auto"),
            {"ui": "button", "text": "›", "variant": "secondary", "width": 56}]},
        {"ui": "divider"},
        {"ui": "row", "gap": "sm", "children": [swatch("#c68ae2", 10), T("ANOMALOUS DUST  12", "label", width="auto")]},
        T("Floor -6 costs 9 dust", "caption"),
        {"ui": "button", "text": "UNLOCK FLOOR -6", "variant": "primary", "width": "fill"}]}
    body = [{"ui": "row", "gap": "lg", "width": "fill", "align": "stretch", "grow": True, "height": 100, "children": [
        {"ui": "column", "gap": "sm", "grow": True, "width": 520, "children": [
            section("PERMANENT  ·  THESE COME BACK UP WITH YOU"),
            {"ui": "scroll", "height": 100, "grow": True, "gap": "xs", "children": rows}]},
        {"ui": "divider", "vertical": True}, descent]}]
    return hub_panel("UPGRADES", "paid in dust  ·  you can always start higher than you have unlocked", body,
                     "bought: LOAD BEARING 12", [])


def r_market():
    lots = []
    for num, name, tag, price, held, state in MARKET:
        ok = state == "buy"
        lots.append(row([
            {"type": "TextLabel", "name": "Lot", "props": {
                "Size": [0, 50, 0, 60], "BackgroundColor3": "@accent", "BackgroundTransparency": 0.86, "Text": num,
                "TextColor3": "@accentFg", "TextSize": 28, "FontFace": {"family": "Oswald", "weight": "Bold"}}},
            preview("◆", 60),
            {"ui": "column", "gap": 3, "grow": True, "width": "fill", "children": [
                T(name, "title", props={"FontFace": {"family": "SpecialElite", "weight": "Regular"}, "TextSize": 20}),
                T(tag, "caption"), T(held, "caption", color="@success" if "BAG" in held else "@muted")]},
            {"type": "TextLabel", "name": "Sticker", "props": {
                "Size": [0, 140, 0, 42], "BackgroundColor3": "#cebA88", "Text": price, "TextColor3": "#26170f",
                "TextSize": 22, "FontFace": {"family": "PermanentMarker", "weight": "Regular"}},
             "children": [{"type": "Frame", "name": "TapeL", "props": {
                 "Size": [0, 22, 0, 8], "Position": [0, -6, 0, -3], "BackgroundColor3": "#e8dfc4",
                 "BackgroundTransparency": 0.35, "BorderSizePixel": 0}}]},
            {"ui": "button", "text": "BUY" if ok else "SHORT $1,866", "variant": "primary" if ok else "secondary",
             "size": "lg", "width": 170, "props": {"FontFace": {"family": "Oswald", "weight": "Bold"},
                                                   "TextSize": 24 if ok else 16,
                                                   "TextColor3": "@accentText" if ok else "@danger"}}],
            pad="sm", bg="@surface2"))
    stamp = None
    body = [{"ui": "row", "justify": "between", "width": "fill", "children": [
        T("UNDER THE COUNTER  ·  CASH ONLY", "title", width="auto",
          props={"FontFace": {"family": "SpecialElite", "weight": "Regular"}}),
        {"type": "TextLabel", "name": "Stamp", "props": {
            "Size": [0, 150, 0, 30], "BackgroundTransparency": 1, "Text": "CONTRABAND", "TextColor3": "@accent",
            "TextSize": 18, "FontFace": {"family": "SpecialElite", "weight": "Regular"}, "Rotation": -6},
         "children": [{"type": "UIStroke", "props": {"Color": "@accent", "Thickness": 2, "Transparency": 0.2,
                                                      "ApplyStrokeMode": "Border"}}]}]},
        {"ui": "scroll", "gap": "xs", "grow": True, "height": 100, "children": lots}]
    return hub_panel("BLACK MARKET", "no questions  ·  no receipts  ·  14.2 / 50.0 kg in the bag", body,
                     "bought: AMBER KEYCARD", [], stamp=stamp)


def r_squad():
    def member(n, sub, me):
        return row([{"ui": "avatar", "text": n[:2].upper(), "size": 32},
                    {"ui": "column", "gap": 2, "grow": True, "width": "fill", "children": [T(n, "label"), T(sub, "caption")]},
                    {"ui": "button", "text": "LEAVE" if me else "REMOVE", "variant": "danger" if me else "secondary",
                     "size": "sm", "width": 100}])
    mine = [member(n, s, me) for n, s, me in SQUAD]
    inv = [{"ui": "column", "gap": "xs", "width": "fill", "padding": "sm", "radius": "sm", "bg": "@accentSoft",
            "children": [T(f"{n} wants you along", "label", color="@accentFg"),
                         {"ui": "row", "gap": "sm", "width": "fill", "children": [
                             {"ui": "button", "text": "ACCEPT", "variant": "primary", "size": "sm", "grow": True, "width": "fill"},
                             {"ui": "button", "text": "DECLINE", "variant": "secondary", "size": "sm", "grow": True,
                              "width": "fill"}]}]} for n in INVITES]
    here = [row([{"ui": "avatar", "text": n[:2].upper(), "size": 32, "tone": "muted"},
                 {"ui": "column", "gap": 2, "grow": True, "width": "fill", "children": [T(n, "label"), T(s, "caption")]},
                 {"ui": "button", "text": "IN A SQUAD" if taken else "INVITE", "variant": "secondary" if taken else "primary",
                  "size": "sm", "width": 110, "disabled": taken}]) for n, s, taken in SERVER]
    body = [{"ui": "row", "gap": "lg", "width": "fill", "align": "stretch", "grow": True, "height": 100, "children": [
        {"ui": "column", "gap": "sm", "grow": True, "width": 400, "children": [
            section("YOUR SQUAD", T("2 / 4", "caption", width="auto")), {"ui": "column", "gap": "xs", "children": mine},
            section("INVITES"), {"ui": "column", "gap": "xs", "children": inv}]},
        {"ui": "divider", "vertical": True},
        {"ui": "column", "gap": "sm", "grow": True, "width": 400, "children": [
            section("IN THIS SERVER"), {"ui": "scroll", "height": 100, "grow": True, "gap": "xs", "children": here}]}]}]
    return hub_panel("SQUAD", "2 / 4  ·  a squad lands together", body, "invited: pallid", [], tape=True)


REFIT = [("EXTRACTION LOG", r_recycle, DOCKET), ("FABRICATION", r_craft, MACHINE), ("VAULT", r_vault, MACHINE),
         ("UPGRADES", r_upgrades, MACHINE), ("BLACK MARKET", r_market, CONTRA), ("SQUAD", r_squad, DOCKET)]
