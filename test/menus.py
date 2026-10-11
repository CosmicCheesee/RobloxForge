"""Two themed main-menu prototypes for the Backroom place, built from RobloxForge components.

A  "Night Shift"  -- the game's own brass-on-black plate, as a facility terminal: nav rail on the left,
                     an expedition briefing on the right.
B  "Lost Memo"    -- the level as an office that was let go: a manila memo with a rubber-stamp accent,
                     a sticky note for the shift's orders.
"""

NIGHT_SHIFT = {
    "extends": "backroom", "name": "night-shift",
    "color": {"bg": "#090806", "surface": "#12100c", "surface2": "#1c1914", "raised": "#211d17",
              "border": "#6f664c", "text": "#ece6d2", "muted": "#a49d89", "subtle": "#7a7362",
              "accent": "#e9d892", "accentFg": "#e9d892", "accentText": "#14110a", "accentSoft": "#2b2617",
              "success": "#9ed096", "warning": "#e2c47e", "danger": "#d67a6e", "dangerFill": "#4a221f",
              "dangerText": "#eec6be", "scrim": "#000000"},
    "font": {"family": "RobotoMono", "display": "RobotoMono", "mono": "RobotoMono",
             "regular": "Regular", "medium": "Medium", "strong": "Bold", "heavy": "Bold"},
    "size": {"caption": 12, "label": 13, "body": 14, "title": 17, "heading": 22, "display": 30},
    "radius": {"sm": 2, "md": 3, "lg": 4, "pill": 999},
    "surfaceT": 0.12, "strokeT": 0.55,
}

LOST_MEMO = {
    "extends": "modern-light", "name": "lost-memo",
    "color": {"bg": "#cdbb7c", "surface": "#f4ecd2", "surface2": "#e8dcb6", "raised": "#fbf5e2",
              "border": "#a8945c", "text": "#2b2416", "muted": "#5e523a", "subtle": "#8a7b57",
              "accent": "#a8261d", "accentFg": "#8e1f17", "accentText": "#fff6e8", "accentSoft": "#efd2c3",
              "success": "#2f6b34", "warning": "#8a5a00", "danger": "#a8261d", "dangerFill": "#a8261d",
              "dangerText": "#fff6e8", "scrim": "#1a140a"},
    "font": {"family": "Merriweather", "display": "SpecialElite", "mono": "SpecialElite",
             "regular": "Regular", "medium": "Regular", "strong": "Bold", "heavy": "Bold"},
    "size": {"caption": 12, "label": 14, "body": 15, "title": 18, "heading": 26, "display": 40},
    "radius": {"sm": 2, "md": 3, "lg": 4, "pill": 999},
    "surfaceT": 0, "strokeT": 0,
}


def nav(label, icon, primary=False, order=0):
    return {"ui": "button", "text": f"{icon}   {label}", "variant": "primary" if primary else "ghost",
            "size": "lg", "width": "fill", "order": order, "props": {"TextXAlignment": "Left"}}


def night_shift():
    # fixed size, not TextScaled: in the live engine TextScaled squeezed this to 8px inside the rail
    wordmark = {"type": "TextLabel", "name": "Wordmark", "props": {
        "Text": "BACKROOMS", "TextColor3": "@accent", "TextSize": 28, "TextWrapped": False,
        "FontFace": {"family": "RobotoMono", "weight": "Bold"}, "BackgroundTransparency": 1,
        "Size": [1, 0, 0, 34], "TextXAlignment": "Left"}}
    player = {"ui": "card", "variant": "raised", "padding": "md", "gap": "sm", "order": 1, "children": [
        {"ui": "row", "gap": "md", "width": "fill", "children": [
            {"ui": "avatar", "text": "BT", "size": 40},
            {"ui": "column", "gap": 2, "grow": True, "width": "fill", "children": [
                {"ui": "text", "text": "player_one", "variant": "label", "truncate": True},
                {"ui": "text", "text": "Clearance B  ·  12 runs", "variant": "caption", "truncate": True}]}]},
        {"ui": "row", "gap": "xs", "wrap": True, "width": "fill", "children": [
            {"ui": "currency", "amount": "47,866", "icon": "◆"},
            {"ui": "chip", "text": "3 merits", "tone": "accent"},
            {"ui": "chip", "text": "bank online", "tone": "success"}]}]}
    rail = {"ui": "column", "name": "Rail", "width": [0.3, 0], "max_w": 380, "height": "fill", "padding": "xl",
            "gap": "lg", "bg": "@surface", "bg_transparency": 0.05, "border": True, "children": [
        {"ui": "column", "gap": "xs", "order": 0, "children": [
            wordmark,
            {"ui": "text", "text": "LEVEL 0  ·  THE OFFICE THAT DOES NOT END", "variant": "caption"}]},
        {"ui": "divider", "order": 1},
        {"ui": "scroll", "order": 2, "height": 60, "grow": True, "gap": "lg", "children": [
            {"ui": "column", "gap": "xs", "order": 0, "children": [
                nav("Start expedition", "▶", primary=True, order=0),
                nav("Hub & market", "◆", order=1),
                nav("Loadout", "☗", order=2),
                nav("Merits", "★", order=3),
                nav("Settings", "⚙", order=4),
                nav("Leave", "×", order=5)]},
            player]}]}

    last_run = {"ui": "card", "title": "Last expedition", "subtitle": "Ended on floor -3, 4 hours ago",
                "width": "fill", "gap": "md", "children": [
        {"ui": "row", "gap": "sm", "width": "fill", "align": "stretch", "wrap": True, "children": [
            {"ui": "stat", "label": "Survived", "value": "12:44", "width": 100, "grow": True},
            {"ui": "stat", "label": "Floors", "value": "3", "width": 100, "grow": True},
            {"ui": "stat", "label": "Recovered", "value": "820", "delta": "+18%", "width": 100, "grow": True}]},
        {"ui": "progress", "label": "Composure on extraction", "value": 0.41, "tone": "warning"}]}
    orders = {"ui": "objective", "title": "Work orders", "width": "fill", "steps": [
        {"text": "Restore power to wing C", "done": True},
        {"text": "Recover a card from a bulkhead room"},
        {"text": "Descend two floors without sprinting"}]}
    floor = {"ui": "card", "title": "Floor 0 conditions", "width": "fill", "gap": "sm", "children": [
        {"ui": "stat_bar", "label": "Power grid", "icon": "⚡", "value": 0.64, "text": "64%", "tone": "warning", "width": "fill"},
        {"ui": "stat_bar", "label": "Lights holding", "icon": "☀", "value": 0.88, "text": "88%", "tone": "success", "width": "fill"},
        {"ui": "stat_bar", "label": "Activity nearby", "icon": "⚠", "value": 0.22, "text": "low", "tone": "danger", "width": "fill"}]}
    news = {"ui": "card", "title": "Facility notices", "width": "fill", "gap": "xs", "children": [
        {"ui": "list", "items": [
            {"title": "Streaming radius tightened", "subtitle": "Loading hitches down by two thirds", "trailing": "new"},
            {"title": "Diagonal partitions", "subtitle": "Rooms are no longer always square", "trailing": "2d"},
            {"title": "Merit stack opened", "subtitle": "Six upgrades in the hub", "trailing": "5d"}]}]}
    briefing = {"ui": "column", "name": "Briefing", "grow": True, "width": "fill", "height": "fill", "padding": "xl",
                "gap": "lg", "children": [
        {"ui": "header", "title": "Expedition briefing", "subtitle": "Shift 0451  ·  floor 0 is stable", "children": [
            {"ui": "chip", "text": "server  ·  14 ms", "tone": "success"},
            {"ui": "chip", "text": "2 players", "tone": "neutral"}]},
        {"ui": "scroll", "height": 100, "grow": True, "gap": "lg", "children": [
            {"ui": "row", "gap": "lg", "width": "fill", "align": "start", "wrap": True, "children": [
                {"ui": "column", "gap": "lg", "width": 420, "grow": True, "children": [last_run, news]},
                {"ui": "column", "gap": "lg", "width": 300, "grow": True, "children": [orders, floor]}]}]},
        {"ui": "row", "gap": "lg", "width": "fill", "justify": "between", "children": [
            {"ui": "row", "gap": "lg", "children": [
                {"ui": "keycap", "key": "E", "label": "interact"},
                {"ui": "keycap", "key": "⇧", "label": "sprint"},
                {"ui": "keycap", "key": "Q", "label": "tools"}]},
            {"ui": "text", "text": "build 2026.10.10  ·  alpha", "variant": "caption", "width": "auto"}]}]}
    return {"ui": "screen", "name": "NightShiftMenu", "children": [
        {"type": "Frame", "name": "Backdrop", "props": {"Size": "fill", "BackgroundColor3": "@bg",
                                                        "BackgroundTransparency": 0.06, "BorderSizePixel": 0},
         "children": [{"type": "UIGradient", "props": {"Color": ["#ffffff", "#8a8170"], "Rotation": 35}}]},
        {"ui": "row", "name": "Layout", "gap": 0, "width": "fill", "height": "fill", "align": "stretch",
         "children": [rail, briefing]}]}


def lost_memo():
    def field(k, v):
        return {"ui": "row", "gap": "md", "width": "fill", "children": [
            {"ui": "text", "text": k, "variant": "mono", "width": 70, "color": "@muted"},
            {"ui": "text", "text": v, "variant": "body", "grow": True}]}
    stamp = {"type": "TextLabel", "name": "Stamp", "props": {
        "Text": "NIGHT SHIFT", "TextColor3": "@accent", "FontFace": {"family": "SpecialElite", "weight": "Regular"},
        "TextSize": 16, "BackgroundTransparency": 1, "Size": [0, 130, 0, 30], "TextTransparency": 0.1},
        "children": [{"type": "UIStroke", "props": {"Color": "@accent", "Thickness": 2, "Transparency": 0.15,
                                                     "ApplyStrokeMode": "Border"}},
                     {"type": "UICorner", "props": {"CornerRadius": 3}}]}
    memo = {"ui": "card", "name": "Memo", "variant": "raised", "padding": "xxl", "gap": "lg", "width": [0.6, 0],
            "max_w": 600, "children": [
        {"ui": "row", "justify": "between", "width": "fill", "children": [
            {"ui": "text", "text": "INTERNAL MEMORANDUM", "variant": "caption", "width": "auto",
             "props": {"FontFace": {"family": "SpecialElite", "weight": "Regular"}}},
            {"ui": "chip", "text": "CONFIDENTIAL", "tone": "danger"}]},
        {"ui": "row", "gap": "lg", "width": "fill", "align": "center", "children": [
            {"ui": "text", "text": "Level 0", "variant": "display", "width": "auto"}, stamp]},
        {"ui": "column", "gap": "xs", "children": [
            field("TO:", "All night-shift staff"),
            field("FROM:", "Facilities (unstaffed)"),
            field("RE:", "The lights on this floor")]},
        {"ui": "divider"},
        {"ui": "text", "variant": "body", "text": "Please do not report the humming. The carpet is damp because it "
                                                 "has always been damp. If you find a door that was not there "
                                                 "yesterday, log it and keep walking. Do not run."},
        {"ui": "row", "gap": "sm", "wrap": True, "width": "fill", "children": [
            {"ui": "button", "text": "Clock in", "variant": "primary", "size": "lg"},
            {"ui": "button", "text": "Review files", "variant": "secondary", "size": "lg"},
            {"ui": "button", "text": "Settings", "variant": "ghost", "size": "lg"},
            {"ui": "button", "text": "Leave", "variant": "ghost", "size": "lg"}]}]}
    note = {"ui": "column", "name": "StickyNote", "width": 240, "padding": "lg", "gap": "sm", "bg": "#f3dd6b",
            "radius": 2, "children": [
        {"ui": "text", "text": "tonight —", "variant": "title",
         "props": {"FontFace": {"family": "PermanentMarker", "weight": "Regular"}}},
        {"ui": "objective", "title": "Shift orders", "width": "fill", "steps": [
            {"text": "Restore power, wing C", "done": True},
            {"text": "Find a key card"},
            {"text": "Two floors down, quietly"}]},
        {"ui": "row", "gap": "xs", "children": [
            {"ui": "currency", "amount": "47,866", "icon": "◆"},
            {"ui": "chip", "text": "3 merits", "tone": "accent"}]}]}
    return {"ui": "screen", "name": "LostMemoMenu", "children": [
        {"type": "Frame", "name": "Wallpaper", "props": {"Size": "fill", "BackgroundColor3": "@bg",
                                                         "BackgroundTransparency": 0, "BorderSizePixel": 0},
         "children": [{"type": "UIGradient", "props": {"Color": ["#ffffff", "#b7a666"], "Rotation": 90}}]},
        {"ui": "scroll", "name": "Desk", "height": "fill", "padding": 16, "pad_top": [0.12, 0], "children": [
            {"ui": "row", "name": "Papers", "gap": "xl", "align": "start", "justify": "center", "wrap": True,
             "width": "fill", "children": [memo, note]}]},
        {"ui": "text", "text": "build 2026.10.10  ·  alpha", "variant": "caption", "width": "auto", "color": "@text",
         "pos": [1, -16, 1, -12], "anchor": [1, 1]}]}


MENUS = {"night_shift": (night_shift, NIGHT_SHIFT), "lost_memo": (lost_memo, LOST_MEMO)}
