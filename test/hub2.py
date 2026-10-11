"""Direction 2 -- OVERHAUL: the same six facilities and the same content, re-laid-out.

  Extraction log  tile grid of what came up + a live yield card + material sliders
  Fabrication     master-detail: recipe list on the left, the selected recipe large on the right
  Vault           two lockers of tiles with the transfer controls between them
  Upgrades        ability cards in a 2x2 grid + descent as an elevator floor ladder
  Black market    lots as taped tiles in a 2x2 grid
  Squad           four seat cards (two open), an invite banner, the server list
"""
from hub import (ABILITIES, BALANCE, CARRIED, INVITES, MARKET, MATS, RECIPES, SALVAGE, SERVER, SQUAD, VAULTED,
                 T, hazard_stops, ingredient, preview, swatch)

R2 = {"radius": {"sm": 6, "md": 10, "lg": 14, "pill": 999}, "stroke": 1, "scrimT": 0.45,
      "space": {"xs": 4, "sm": 8, "md": 12, "lg": 16, "xl": 24, "xxl": 32},
      "size": {"caption": 12, "label": 14, "body": 15, "title": 18, "heading": 26, "display": 34}}
SANS = {"family": "BuilderSans", "display": "BuilderSans", "mono": "RobotoMono",
        "regular": "Regular", "medium": "Medium", "strong": "SemiBold", "heavy": "Bold"}

DOCKET2 = {**R2, "extends": "modern-dark", "name": "docket-2", "font": SANS, "surfaceT": 0.02, "strokeT": 0.4,
           "color": {"bg": "#0e0c09", "surface": "#1b1813", "surface2": "#26221b", "raised": "#2f2a21",
                     "border": "#5c4f36", "text": "#f0ead8", "muted": "#b2a98f", "subtle": "#7f775f",
                     "accent": "#e9cf6e", "accentFg": "#f0d98a", "accentText": "#1a1505", "accentSoft": "#3a3220",
                     "success": "#9ed096", "warning": "#e8c47a", "danger": "#ec8f80", "dangerFill": "#8e2f24",
                     "dangerText": "#ffffff", "scrim": "#000000"}}
MACHINE2 = {**R2, "extends": "modern-dark", "name": "machine-2", "font": SANS, "surfaceT": 0.02, "strokeT": 0.35,
            "color": {"bg": "#070b10", "surface": "#0f161e", "surface2": "#16202b", "raised": "#1d2a37",
                      "border": "#34506a", "text": "#e8f0f6", "muted": "#9cb0c0", "subtle": "#6a8092",
                      "accent": "#6fb6ff", "accentFg": "#9ccbff", "accentText": "#04111e", "accentSoft": "#14304d",
                      "success": "#7fd7a0", "warning": "#f0c674", "danger": "#ff8f86", "dangerFill": "#a3312a",
                      "dangerText": "#ffffff", "scrim": "#000000"}}
CONTRA2 = {**R2, "extends": "modern-dark", "name": "contraband-2", "surfaceT": 0.02, "strokeT": 0.35,
           "font": {"family": "Oswald", "display": "SpecialElite", "mono": "SpecialElite",
                    "regular": "Regular", "medium": "Medium", "strong": "Bold", "heavy": "Bold"},
           "radius": {"sm": 2, "md": 3, "lg": 4, "pill": 999},
           "color": {"bg": "#0b0907", "surface": "#17130f", "surface2": "#241e18", "raised": "#2d261f",
                     "border": "#5e4c3a", "text": "#ecdcbc", "muted": "#b3a286", "subtle": "#7f705c",
                     "accent": "#d2513b", "accentFg": "#f08a73", "accentText": "#fbf0dc", "accentSoft": "#3e1e17",
                     "success": "#a8d39a", "warning": "#e8c47a", "danger": "#f08a73", "dangerFill": "#7a2618",
                     "dangerText": "#fbf0dc", "scrim": "#000000"}}


def tile(title, sub, glyph="◆", selected=False, w=132, badge=None):
    kids = [preview(glyph, 64), T(title, "label", align="center", truncate=True),
            T(sub, "caption", align="center", truncate=True)]
    card = {"ui": "column", "name": "Tile", "gap": 6, "width": w, "align": "center", "padding": "md", "radius": "md",
            "bg": "@accentSoft" if selected else "@surface2", "bg_transparency": 0, "border": True,
            "props": {"Size": [0, w, 0, 0]}, "children": kids}
    card["children"].insert(0, {"type": "TextLabel", "name": "Check", "props": {
        "Size": [0, 20, 0, 20], "BackgroundColor3": "@accent", "BackgroundTransparency": 0 if selected else 1,
        "Text": "✓" if selected else "", "TextColor3": "@accentText",
        "TextSize": 13, "FontFace": {"family": "BuilderSans", "weight": "Bold"}},
        "children": [{"type": "UICorner", "props": {"CornerRadius": 999}}]})
    return card


def panel(title, sub, body, status, actions, search="Search", filter_text="All", tape=False, max_w=1000, max_h=602):
    header = {"ui": "row", "justify": "between", "width": "fill", "align": "center", "children": [
        {"ui": "column", "gap": 2, "width": "auto", "children": [T(title, "heading", width="auto"),
                                                                 T(sub, "caption", width="auto")]},
        {"ui": "row", "gap": "sm", "children": [
            {"ui": "input", "placeholder": search, "width": 220, "height": 34},
            {"ui": "button", "text": filter_text, "variant": "secondary", "size": "sm"},
            {"ui": "currency", "amount": BALANCE, "icon": "◆", "tone": "accent"},
            {"ui": "icon_button", "icon": "×", "size": "sm", "attrs": {"ForgeRole": "dismiss"}}]}]}
    foot = {"ui": "row", "gap": "sm", "width": "fill", "justify": "between", "padding": "sm", "radius": "md",
            "bg": "@surface2", "bg_transparency": 0.2, "children": [
                {"ui": "row", "gap": "sm", "width": "auto", "children": [
                    {"type": "Frame", "name": "Dot", "props": {"Size": [0, 8, 0, 8], "BackgroundColor3": "@success",
                                                               "BorderSizePixel": 0},
                     "children": [{"type": "UICorner", "props": {"CornerRadius": 999}}]},
                    T(status, "caption", width="auto", color="@muted")]},
                {"ui": "row", "gap": "sm", "children": actions}]}
    kids = []
    if tape:
        kids.append({"type": "Frame", "name": "Tape", "props": {"Size": [1, 0, 0, 5], "BackgroundColor3": "@accent",
                                                                "BorderSizePixel": 0},
                     "children": [{"type": "UIGradient", "props": {"Color": hazard_stops(9, "#e9cf6e", "#1b1813")}},
                                  {"type": "UICorner", "props": {"CornerRadius": 2}}]})
    kids += [header, {"ui": "column", "name": "Body", "grow": True, "width": "fill", "height": 120, "gap": "md",
                      "children": body}, foot]
    card = {"ui": "card", "name": "Panel", "padding": "xl", "gap": "lg", "width": [0.96, 0], "height": [0.94, 0],
            "pos": [0.5, 0, 0.5, 0], "anchor": [0.5, 0.5], "max_w": max_w, "max_h": max_h, "children": kids}
    return {"ui": "screen", "name": title.replace(" ", ""), "children": [
        {"type": "Frame", "name": "City", "props": {"Size": "fill", "BackgroundColor3": "#05070a",
                                                    "BackgroundTransparency": 0, "BorderSizePixel": 0},
         "children": [{"type": "UIGradient", "props": {"Color": ["#2a3442", "#0b0e12", "#141a22"], "Rotation": 90}}]},
        card]}


def o_recycle():
    tiles = []
    for i, (n, kg, val, g) in enumerate(SALVAGE):
        tiles.append(tile(n, f"{kg} kg · {val}", g, selected=i in (0, 1, 3)))
    sell = []
    for i, (n, col, price, held) in enumerate(MATS[:5]):
        v = [0.2, 0, 0, 0.45, 0.52][i]
        sell.append({"ui": "column", "gap": 2, "width": "fill", "children": [
            {"ui": "row", "gap": "sm", "width": "fill", "children": [
                swatch(col, 8), T(n.title(), "label", grow=True),
                T(f"{int(held * v)} / {held}", "mono", width="auto", color="@muted")]},
            {"ui": "slider", "value": v}]})
    right = {"ui": "scroll", "gap": "md", "width": 320, "height": 100, "props": {"Size": [0, 320, 1, 0]}, "children": [
        {"ui": "card", "variant": "raised", "padding": "lg", "gap": "sm", "children": [
            T("Yield from 3 selected", "caption"),
            T("$542", "display", color="@accentFg"),
            {"ui": "stat_bar", "label": "Metal parts", "value": 0.7, "text": "+48", "tone": "accent", "width": "fill"},
            {"ui": "stat_bar", "label": "Plastic parts", "value": 0.35, "text": "+22", "tone": "warning", "width": "fill"},
            {"ui": "stat_bar", "label": "Tech", "value": 0.15, "text": "+3", "tone": "success", "width": "fill"},
            {"ui": "button", "text": "Recycle 3 items", "variant": "primary", "width": "fill", "size": "lg"}]},
        {"ui": "card", "padding": "lg", "gap": "md", "children": [
            {"ui": "row", "justify": "between", "width": "fill", "children": [
                T("Sell materials", "title", width="auto"), T("$2,720", "title", width="auto", color="@accentFg")]},
            {"ui": "column", "gap": "md", "children": sell}]}]}
    body = [{"ui": "row", "gap": "lg", "width": "fill", "align": "stretch", "grow": True, "height": 100, "children": [
        {"ui": "column", "gap": "sm", "grow": True, "width": 420, "props": {"Size": [0, 420, 1, 0], "AutomaticSize": "None"}, "children": [
            {"ui": "row", "justify": "between", "width": "fill", "children": [
                T("What came up with you", "title", width="auto"),
                {"ui": "button", "text": "Clear", "variant": "ghost", "size": "sm"}]},
            {"ui": "scroll", "height": 100, "grow": True, "children": [{"ui": "grid", "cell": [132, 160], "gap": "sm", "children": tiles}]}]},
        right]}]
    return panel("Extraction log", "6 stored · breaking down pays more than selling whole", body,
                 "Recycled 2 items · +$318", [{"ui": "button", "text": "Sell $2,720", "variant": "secondary"}], tape=True)


def o_craft():
    lst = []
    for i, (name, desc, reqs, state, carried) in enumerate(RECIPES):
        tone = {"ready": "success", "missing": "danger", "bagfull": "warning"}[state]
        lst.append({"ui": "list_item", "title": name.title(), "subtitle": f"{len(reqs)} ingredients · {carried} carried",
                    "trailing": {"ui": "chip", "text": {"ready": "Ready", "missing": "Missing", "bagfull": "Bag full"}[state],
                                 "tone": tone}, "selected": i == 3, "order": i})
    name, desc, reqs, state, carried = RECIPES[3]
    detail_body = [
        {"ui": "row", "gap": "lg", "width": "fill", "children": [
            preview("◆", 120),
            {"ui": "column", "gap": "xs", "grow": True, "width": "fill", "children": [
                {"ui": "chip", "text": "Weapon", "tone": "accent"}, T(name.title(), "heading"), T(desc, "body", color="@muted")]}]},
        {"ui": "divider"},
        T("Ingredients", "caption"),
        {"ui": "row", "gap": 6, "width": "fill", "wrap": True, "children": [ingredient(n, c, h, nd) for n, c, h, nd in reqs]},
        {"ui": "row", "gap": "sm", "width": "fill", "padding": "sm", "radius": "md", "bg": "@dangerFill",
         "bg_transparency": 0.7, "children": [
            T("⚠", "label", width="auto", color="@danger"),
            T("Missing 29 metal · 23 tech · 1 pistol body", "label", grow=True, color="@danger")]},
        {"ui": "button", "text": "Missing ingredients", "variant": "secondary", "size": "lg", "width": "fill", "disabled": True}]
    detail = {"ui": "card", "variant": "raised", "padding": "lg", "gap": 0, "grow": True, "width": 420, "children": [
        {"ui": "scroll", "height": 100, "props": {"Size": [1, 0, 1, 0]}, "gap": "md", "padding": 4, "children": detail_body}]}
    body = [{"ui": "row", "gap": "lg", "width": "fill", "align": "stretch", "grow": True, "height": 100, "children": [
        {"ui": "column", "gap": "sm", "width": 320, "children": [
            T("What the bay can build", "title"),
            {"ui": "scroll", "height": 100, "grow": True, "gap": 2, "children": lst}]},
        detail]}]
    return panel("Fabrication", "3 of 17 ready · 14.2 / 50.0 kg carried", body, "Built snare plate",
                 [{"ui": "toggle", "label": "Only what I can build", "on": False, "width": "auto"}])


def o_vault():
    def locker(title, data, store):
        tiles = [tile(d[0].title(), f"{d[1]} kg · {'on you' if store else d[2]}", "◆", w=124) for d in data]
        return {"ui": "card", "padding": "lg", "gap": "md", "grow": True, "width": 330, "props": {"Size": [0, 330, 1, 0], "AutomaticSize": "None"}, "children": [
            {"ui": "row", "justify": "between", "width": "fill", "children": [
                T(title, "title", width="auto"), {"ui": "chip", "text": f"{len(data)} items", "tone": "neutral"}]},
            {"ui": "scroll", "height": 60, "grow": True, "children": [{"ui": "grid", "cell": [124, 156], "gap": "sm", "children": tiles}]}]}
    mid = {"ui": "column", "gap": "sm", "width": 120, "align": "center", "children": [
        {"ui": "spacer", "size": 120},
        {"ui": "button", "text": "Store »", "variant": "primary", "width": "fill"},
        {"ui": "button", "text": "« Take", "variant": "secondary", "width": "fill"},
        T("Drag tiles across, or select and move", "caption", align="center")]}
    body = [{"ui": "row", "gap": "md", "width": "fill", "align": "stretch", "grow": True, "height": 100, "children": [
        locker("Carried", CARRIED, True), mid, locker("In the vault", VAULTED, False)]}]
    return panel("Vault", "6.2 / 50.0 kg carried · 5 stored", body, "Stored bandage",
                 [{"ui": "button", "text": "Store everything carried", "variant": "primary"}])


def o_upgrades():
    cards = []
    for name, blurb, lvl, now, nxt, cost in ABILITIES:
        cards.append({"ui": "card", "padding": "lg", "gap": "sm", "width": "fill", "children": [
            {"ui": "row", "justify": "between", "width": "fill", "children": [
                T(name.title(), "title", width="auto"),
                {"ui": "row", "gap": 2, "children": [T(str(lvl), "heading", width="auto", color="@accentFg"),
                                                     T("/20", "caption", width="auto")]}]},
            T(blurb, "caption"),
            {"ui": "progress", "value": lvl / 20, "height": 6},
            {"ui": "row", "justify": "between", "width": "fill", "children": [
                T(f"{now}  →  {nxt}", "caption", width="auto", color="@text"),
                {"ui": "button", "text": cost, "variant": "primary" if lvl < 12 else "secondary", "size": "sm"}]}]})
    grid = {"ui": "grid", "cell": [300, 132], "gap": "md", "children": cards}
    floors = []
    for f in range(0, 7):
        cur, unlocked = f == 3, f <= 5
        floors.append({"ui": "row", "gap": "sm", "width": "fill", "padding": "xs", "radius": "sm",
                       "bg": "@accentSoft" if cur else "@surface2", "bg_transparency": 0 if cur else 0.5, "order": f,
                       "children": [T(f"{-f if f else 0}", "mono", width=36, align="center",
                                      color="@accentFg" if cur else ("@text" if unlocked else "@muted")),
                                    T("you start here" if cur else ("open" if unlocked else "9 dust"), "caption", grow=True,
                                      color="@accentFg" if cur else "@muted")]})
    elevator = {"ui": "card", "variant": "raised", "padding": "lg", "gap": "sm", "width": 230,
                "props": {"Size": [0, 230, 1, 0], "AutomaticSize": "None"}, "children": [
        T("Descent", "title"),
        {"ui": "scroll", "height": 60, "grow": True, "gap": 3, "children": floors},
        {"ui": "row", "gap": "sm", "children": [swatch("#c68ae2", 10), T("12 anomalous dust", "label", width="auto")]},
        {"ui": "button", "text": "Unlock floor -6 · 9 dust", "variant": "primary", "width": "fill"}]}
    body = [{"ui": "row", "gap": "lg", "width": "fill", "align": "stretch", "grow": True, "height": 100, "children": [
        {"ui": "column", "gap": "sm", "grow": True, "width": 620, "children": [
            T("Permanent · these come back up with you", "caption"),
            {"ui": "scroll", "height": 100, "grow": True, "children": [grid,
                {"ui": "row", "gap": "md", "width": "fill", "padding": "md", "radius": "md", "bg": "@surface2",
                 "bg_transparency": 0.3, "children": [
                    T("Wide lamp", "label", width="auto"), T("A broader beam from the same battery.", "caption", grow=True),
                    {"ui": "chip", "text": "Owned", "tone": "success"}]}]}]},
        elevator]}]
    return panel("Upgrades", "paid in dust · you can always start higher than you have unlocked", body,
                 "Bought load bearing 12", [])


def o_market():
    lots = []
    for num, name, tag, price, held, state in MARKET:
        ok = state == "buy"
        lots.append({"ui": "card", "padding": "md", "gap": "sm", "width": "fill", "variant": "raised", "children": [
            {"ui": "row", "gap": "md", "width": "fill", "children": [
                {"type": "TextLabel", "name": "Lot", "props": {
                    "Size": [0, 46, 0, 46], "BackgroundColor3": "@accent", "BackgroundTransparency": 0.85, "Text": num,
                    "TextColor3": "@accentFg", "TextSize": 26, "FontFace": {"family": "Oswald", "weight": "Bold"}}},
                preview("◆", 64),
                {"ui": "column", "gap": 2, "grow": True, "width": "fill", "children": [
                    T(name, "title", props={"FontFace": {"family": "SpecialElite", "weight": "Regular"}, "TextSize": 19}),
                    T(tag.split("  ·  ")[0] + "  ·  " + tag.split("  ·  ")[1], "caption"),
                    T(held, "caption", color="@success" if "BAG" in held else "@muted")]}]},
            {"ui": "row", "gap": "sm", "width": "fill", "children": [
                {"type": "TextLabel", "name": "Sticker", "props": {
                    "Size": [0, 130, 0, 40], "BackgroundColor3": "#cfba86", "Text": price, "TextColor3": "#26170f",
                    "TextSize": 21, "FontFace": {"family": "PermanentMarker", "weight": "Regular"}}},
                {"ui": "button", "text": "BUY" if ok else "SHORT $1,866", "variant": "primary" if ok else "secondary",
                 "size": "lg", "grow": True, "width": "fill",
                 "props": {"FontFace": {"family": "Oswald", "weight": "Bold"}, "TextSize": 22 if ok else 16,
                           "TextColor3": "@accentText" if ok else "@danger"}}]}]})
    body = [{"ui": "row", "justify": "between", "width": "fill", "children": [
        T("UNDER THE COUNTER · CASH ONLY", "title", width="auto", props={"FontFace": {"family": "SpecialElite", "weight": "Regular"}}),
        {"type": "TextLabel", "name": "Stamp", "props": {
            "Size": [0, 150, 0, 30], "BackgroundTransparency": 1, "Text": "CONTRABAND", "TextColor3": "@accent",
            "TextSize": 18, "FontFace": {"family": "SpecialElite", "weight": "Regular"}, "Rotation": -6},
         "children": [{"type": "UIStroke", "props": {"Color": "@accent", "Thickness": 2, "Transparency": 0.2,
                                                      "ApplyStrokeMode": "Border"}}]}]},
        {"ui": "scroll", "height": 100, "grow": True, "children": [
            {"ui": "grid", "cell": [460, 150], "gap": "md", "children": lots}]}]
    return panel("Black market", "no questions · no receipts · 14.2 / 50.0 kg in the bag", body, "Bought amber keycard", [])


def o_squad():
    seats = []
    for n, sub, me in SQUAD:
        seats.append({"ui": "card", "variant": "raised", "padding": "lg", "gap": "sm", "align": "center", "width": "fill",
                      "children": [{"ui": "avatar", "text": n[:2].upper(), "size": 64, "props": {"TextSize": 22}},
                                   T(n, "label", align="center", truncate=True), T(sub, "caption", align="center"),
                                   {"ui": "button", "text": "Leave" if me else "Remove",
                                    "variant": "danger" if me else "secondary", "size": "sm", "width": "fill"}]})
    for i in range(2):
        seats.append({"ui": "card", "variant": "outline", "padding": "lg", "gap": "sm", "align": "center", "width": "fill",
                      "children": [{"type": "TextLabel", "name": "Open", "props": {
                          "Size": [0, 64, 0, 64], "BackgroundTransparency": 1, "Text": "+", "TextColor3": "@subtle",
                          "TextSize": 30, "FontFace": {"family": "BuilderSans", "weight": "Bold"}},
                          "children": [{"type": "UIStroke", "props": {"Color": "@border", "Thickness": 1,
                                                                       "ApplyStrokeMode": "Border"}},
                                       {"type": "UICorner", "props": {"CornerRadius": 999}}]},
                          T("Open seat", "label", align="center", color="@muted"),
                          T("invite from the list", "caption", align="center")]})
    seat_grid = {"ui": "grid", "cell": [210, 210], "gap": "md", "children": seats}
    banner = {"ui": "row", "gap": "md", "width": "fill", "padding": "md", "radius": "md", "bg": "@accentSoft",
              "children": [{"ui": "avatar", "text": "KR", "size": 36},
                           T(f"{INVITES[0]} wants you along", "label", grow=True, color="@accentFg"),
                           {"ui": "button", "text": "Accept", "variant": "primary", "size": "sm"},
                           {"ui": "button", "text": "Decline", "variant": "ghost", "size": "sm"}]}
    here = [{"ui": "list_item", "title": n, "subtitle": s, "avatar": n[:2].upper(), "order": i,
             "trailing": {"ui": "button", "text": "In a squad" if taken else "Invite",
                          "variant": "secondary" if taken else "soft", "size": "sm", "disabled": taken}}
            for i, (n, s, taken) in enumerate(SERVER)]
    body = [banner, {"ui": "row", "gap": "lg", "width": "fill", "align": "stretch", "grow": True, "height": 100, "children": [
        {"ui": "scroll", "height": 100, "grow": True, "width": 440, "props": {"Size": [0, 440, 1, 0]},
         "children": [seat_grid]},
        {"ui": "column", "gap": "sm", "width": 280, "children": [
            T("In this server", "title"), {"ui": "scroll", "height": 100, "grow": True, "gap": 2, "children": here}]}]}]
    return panel("Squad", "2 / 4 · a squad lands together", body, "Invited pallid", [], tape=True)


OVERHAUL = [("EXTRACTION LOG", o_recycle, DOCKET2), ("FABRICATION", o_craft, MACHINE2), ("VAULT", o_vault, MACHINE2),
            ("UPGRADES", o_upgrades, MACHINE2), ("BLACK MARKET", o_market, CONTRA2), ("SQUAD", o_squad, DOCKET2)]
