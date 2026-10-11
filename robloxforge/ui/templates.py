"""Whole screens, built from the component library and responsive by construction: panels are sized by
Scale and capped with UISizeConstraint, HUD pieces are pinned to corners with AnchorPoint. Every template
takes optional params; anything not given gets plausible sample content so the result is reviewable."""
from __future__ import annotations

from ..studio import ForgeError

DOCS: dict[str, str] = {}
TPL = {}


def tpl(name, doc):
    def deco(fn):
        TPL[name] = fn
        DOCS[name] = doc
        return fn
    return deco


def panel(name, children, max_w=520, max_h=None, scale_w=0.92, scale_h=None, title=None, gap="lg", modal=True):
    """A centred card that fits phones (scale) and stops growing on desktop (max size)."""
    card = {"ui": "card", "name": name, "padding": "xl", "gap": gap, "title": title, "width": [scale_w, 0],
            "children": children, "pos": [0.5, 0, 0.5, 0], "anchor": [0.5, 0.5], "_cls": "TextButton"}
    if scale_h:
        card["height"] = [scale_h, 0]
    cons = {"type": "UISizeConstraint", "props": {"MaxSize": [max_w, max_h or 100000]}}
    card["children"] = [cons] + card["children"]
    if not modal:
        return card
    return {"type": "Frame", "name": name + "Layer", "props": {"Size": [1, 0, 1, 0], "BackgroundTransparency": 1},
            "children": [{"type": "TextButton", "name": "Scrim", "props": {
                "Size": [1, 0, 1, 0], "BackgroundColor3": "@scrim", "BackgroundTransparency": "@scrimT", "Text": "",
                "AutoButtonColor": False, "BorderSizePixel": 0}, "attrs": {"ForgeRole": "dismiss"}}, card]}


@tpl("hud", "In-game HUD: health + stamina bottom-left, hotbar bottom-centre, currency top-right, objective "
     "top-left, crosshair, interact hint. {health, stamina, slots, selected, coins, objective: {title, steps}, hint}")
def t_hud(p):
    obj = p.get("objective") or {"title": "Find the exit", "steps": [{"text": "Restore power", "done": True},
                                                                     {"text": "Locate the stairwell"}]}
    return {"ui": "screen", "name": p.get("name", "HUD"), "children": [
        {"ui": "crosshair", "style": p.get("crosshair", "dot")},
        {"ui": "column", "name": "Vitals", "gap": "sm", "width": 220, "pos": [0, 20, 1, -96], "anchor": [0, 1], "children": [
            {"ui": "stat_bar", "label": "Health", "icon": "♥", "value": p.get("health", 0.82), "tone": "danger",
             "text": f"{round(p.get('health', 0.82) * 100)}", "width": "fill"},
            {"ui": "stat_bar", "label": "Stamina", "icon": "⚡", "value": p.get("stamina", 0.55), "tone": "success",
             "width": "fill", "height": 6}]},
        {"ui": "hotbar", "pos": [0.5, 0, 1, -20], "anchor": [0.5, 1], "selected": p.get("selected", 0), "size": 52,
         "slots": p.get("slots") or [{"icon": "⚔"}, {"icon": "✚", "count": 3}, {"icon": "◉"}, {}, {}]},
        {"ui": "currency", "amount": p.get("coins", "1,250"), "pos": [1, -20, 0, 20], "anchor": [1, 0]},
        {"ui": "objective", **obj, "pos": [0, 20, 0, 20], "width": [0.6, 0], "max_w": 280},
        {"ui": "keycap", "key": "E", "label": p.get("hint", "Open door"), "pos": [0.5, 0, 0.62, 0], "anchor": [0.5, 0.5]},
    ]}


@tpl("pause_menu", "Pause menu over a click-away scrim. {title, buttons: [str]}")
def t_pause(p):
    labels = p.get("buttons") or ["Resume", "Settings", "Controls", "Leave game"]
    btns = []
    for i, b in enumerate(labels):
        var = "primary" if i == 0 else ("danger" if "leave" in b.lower() or "quit" in b.lower() else "secondary")
        btns.append({"ui": "button", "text": b, "variant": var, "size": "lg", "width": "fill", "order": i})
    return {"ui": "screen", "name": p.get("name", "PauseMenu"), "children": [
        panel("Pause", [{"ui": "text", "text": p.get("title", "Paused"), "variant": "heading", "align": "center"},
                        {"ui": "column", "gap": "sm", "children": btns}], max_w=360)]}


@tpl("settings", "Settings dialog with tabs and rows of toggles/sliders, Reset + Save footer. {tabs, rows: [{label, "
     "description?, kind: toggle|slider, value}]}")
def t_settings(p):
    rows = p.get("rows") or [
        {"label": "Shadows", "description": "Fixtures cast shadows (costs frames)", "kind": "toggle", "value": True},
        {"label": "Field of view", "kind": "slider", "value": 0.45},
        {"label": "Motion blur", "kind": "toggle", "value": False},
        {"label": "Master volume", "kind": "slider", "value": 0.8},
        {"label": "Subtitles", "description": "Show captions for voices", "kind": "toggle", "value": True}]
    items = []
    for i, r in enumerate(rows):
        if r.get("kind") == "slider":
            ctl = {"ui": "slider", "value": r.get("value", 0.5), "width": 180, "props": {"Size": [0, 180, 0, 32]}}
        else:
            ctl = {"ui": "toggle", "on": bool(r.get("value"))}
        items.append({"ui": "settings_row", "label": r["label"], "description": r.get("description"), "control": ctl,
                      "order": i})
        if i < len(rows) - 1:
            items.append({"ui": "divider", "order": i})
    return {"ui": "screen", "name": p.get("name", "Settings"), "children": [
        panel("Settings", [
            {"ui": "header", "title": p.get("title", "Settings"), "children": [
                {"ui": "icon_button", "icon": "×", "size": "sm", "attrs": {"ForgeRole": "dismiss"}}]},
            {"ui": "tabs", "items": p.get("tabs") or ["General", "Graphics", "Audio", "Controls"], "selected": 1},
            {"ui": "scroll", "height": 120, "grow": True, "gap": "sm", "children": items},
            {"ui": "row", "justify": "end", "gap": "sm", "width": "fill", "children": [
                {"ui": "button", "text": "Reset", "variant": "ghost"},
                {"ui": "button", "text": "Save changes", "variant": "primary"}]}], max_w=560, max_h=560, scale_h=0.9)]}


@tpl("inventory", "Inventory: slot grid + selected-item details and actions. {title, slots, selected, coins, item: "
     "{name, description, stats: [[label, value]]}}")
def t_inventory(p):
    slots = p.get("slots") or ([{"icon": g} for g in "⚔✚◉☗⚙★☂◆"] + [{} for _ in range(8)])
    sel = p.get("selected", 0)
    grid = [{"ui": "slot", **s, "selected": i == sel, "size": 60, "order": i} for i, s in enumerate(slots)]
    item = p.get("item") or {"name": "Steel bat", "description": "Heavy, slow, loud. Knocks things over.",
                             "stats": [["Damage", "34"], ["Weight", "2.1 kg"], ["Value", "◆ 120"]]}
    stats = [{"ui": "row", "justify": "between", "width": "fill", "order": i, "children": [
        {"ui": "text", "text": k, "variant": "caption", "width": "auto"},
        {"ui": "text", "text": v, "variant": "mono", "width": "auto"}]} for i, (k, v) in enumerate(item.get("stats", []))]
    detail = {"ui": "card", "variant": "raised", "width": 240, "gap": "md", "children": [
        {"ui": "text", "text": item["name"], "variant": "title"},
        {"ui": "text", "text": item.get("description", ""), "variant": "body", "color": "@muted"},
        {"ui": "column", "gap": "xs", "children": stats},
        {"ui": "button", "text": "Equip", "variant": "primary", "width": "fill"},
        {"ui": "button", "text": "Drop", "variant": "ghost", "width": "fill"}]}
    return {"ui": "screen", "name": p.get("name", "Inventory"), "children": [
        panel("Inventory", [
            {"ui": "header", "title": p.get("title", "Inventory"), "children": [
                {"ui": "currency", "amount": p.get("coins", "1,250")},
                {"ui": "icon_button", "icon": "×", "size": "sm", "attrs": {"ForgeRole": "dismiss"}}]},
            {"ui": "scroll", "height": 120, "grow": True, "children": [
                {"ui": "row", "gap": "lg", "align": "start", "width": "fill", "wrap": True, "children": [
                    {"ui": "grid", "cell": [60, 60], "gap": "sm", "width": 264, "grow": True, "children": grid},
                    detail]}]}],
              max_w=820, max_h=620, scale_h=0.9)]}


@tpl("shop", "Store: tabs + grid of item tiles + balance. {title, tabs, items: [{item, price, icon?, tag?, owned?}], coins}")
def t_shop(p):
    items = p.get("items") or [
        {"item": "Flashlight", "price": 150, "icon": "◉", "tag": "new"}, {"item": "Bandage", "price": 40, "icon": "✚"},
        {"item": "Lockpick", "price": 220, "icon": "⚙"}, {"item": "Lantern", "price": 480, "icon": "☀", "owned": True},
        {"item": "Map", "price": 90, "icon": "☗"}, {"item": "Rope", "price": 60, "icon": "∞"}]
    tiles = [{"ui": "shop_item", **it, "width": "fill", "order": i} for i, it in enumerate(items)]
    return {"ui": "screen", "name": p.get("name", "Shop"), "children": [
        panel("Shop", [
            {"ui": "header", "title": p.get("title", "Shop"), "subtitle": "Prices refresh daily", "children": [
                {"ui": "currency", "amount": p.get("coins", "1,250")},
                {"ui": "icon_button", "icon": "×", "size": "sm", "attrs": {"ForgeRole": "dismiss"}}]},
            {"ui": "tabs", "items": p.get("tabs") or ["Featured", "Tools", "Cosmetics"], "selected": 0},
            {"ui": "scroll", "height": 120, "grow": True, "children": [
                {"ui": "grid", "cell": [176, 236], "gap": "md", "children": tiles}]}], max_w=860, max_h=640, scale_h=0.9)]}


@tpl("dialog", "NPC dialogue with choices. {speaker, text, choices, portrait}")
def t_dialog(p):
    return {"ui": "screen", "name": p.get("name", "Dialogue"), "children": [
        {"ui": "dialog_box", "speaker": p.get("speaker", "Night Watchman"),
         "text": p.get("text", "You're not supposed to be down here. The lights on this floor haven't worked in years."),
         "choices": p.get("choices") or ["Who are you?", "Which way is out?", "Leave"],
         "portrait": p.get("portrait", "NW")}]}


@tpl("title_menu", "Title screen: big title, subtitle, primary Play + secondary actions, version line. {title, "
     "subtitle, buttons, version}")
def t_title(p):
    labels = p.get("buttons") or ["Play", "Settings", "Credits"]
    btns = [{"ui": "button", "text": b, "variant": "primary" if i == 0 else "ghost", "size": "lg", "width": 260,
             "order": i} for i, b in enumerate(labels)]
    return {"ui": "screen", "name": p.get("name", "TitleMenu"), "children": [
        {"ui": "center", "gap": "xl", "children": [
            {"ui": "column", "gap": "xs", "align": "center", "width": "auto", "order": 0, "children": [
                {"ui": "text", "text": p.get("title", "BACKROOMS"), "variant": "display", "align": "center",
                 "width": "auto", "size": 56},
                {"ui": "text", "text": p.get("subtitle", "level 0  ·  infinite"), "variant": "caption",
                 "align": "center", "width": "auto"}]},
            {"ui": "column", "gap": "sm", "align": "center", "width": "auto", "order": 1, "children": btns}]},
        {"ui": "text", "text": p.get("version", "v0.1 alpha"), "variant": "caption", "width": "auto",
         "pos": [1, -16, 1, -12], "anchor": [1, 1]}]}


@tpl("loading", "Loading screen: title, progress bar, rotating tip. {title, value, tip}")
def t_loading(p):
    return {"ui": "screen", "name": p.get("name", "Loading"), "children": [
        {"ui": "center", "gap": "lg", "children": [
            {"ui": "text", "text": p.get("title", "Generating level…"), "variant": "title", "align": "center",
             "width": "auto", "order": 0},
            {"ui": "progress", "value": p.get("value", 0.42), "width": 320, "order": 1,
             "props": {"Size": [0, 320, 0, 6]}},
            {"ui": "text", "text": p.get("tip", "Tip: sprinting is loud. Monsters hear it."), "variant": "caption",
             "align": "center", "width": "auto", "order": 2}]}]}


@tpl("leaderboard", "Ranked list with the local player highlighted. {title, rows: [{player, score, me?}]}")
def t_leaderboard(p):
    rows = p.get("rows") or [{"player": n, "score": s, "me": n == "you"} for n, s in
                             [("vex", 9120), ("orchid", 8800), ("you", 7410), ("pallid", 6900), ("kite", 5120)]]
    items = [{"ui": "leaderboard_row", **r, "rank": i + 1, "order": i} for i, r in enumerate(rows)]
    return {"ui": "screen", "name": p.get("name", "Leaderboard"), "children": [
        panel("Leaderboard", [
            {"ui": "header", "title": p.get("title", "Leaderboard"), "subtitle": "This week", "children": [
                {"ui": "icon_button", "icon": "×", "size": "sm", "attrs": {"ForgeRole": "dismiss"}}]},
            {"ui": "column", "gap": "xs", "children": items}], max_w=460)]}


@tpl("results", "End-of-run / death screen: verdict, stats, actions. {title, subtitle, stats: [[label, value]], buttons}")
def t_results(p):
    stats = p.get("stats") or [["Time survived", "12:44"], ["Floors descended", "3"], ["Loot recovered", "◆ 820"]]
    tiles = [{"ui": "stat", "label": k, "value": v, "width": 150, "grow": True, "order": i} for i, (k, v) in enumerate(stats)]
    labels = p.get("buttons") or ["Play again", "Back to hub"]
    btns = [{"ui": "button", "text": b, "variant": "primary" if i == 0 else "secondary", "size": "lg", "order": i}
            for i, b in enumerate(labels)]
    return {"ui": "screen", "name": p.get("name", "Results"), "children": [
        panel("Results", [
            {"ui": "column", "gap": "xs", "align": "center", "children": [
                {"ui": "text", "text": p.get("title", "You didn't make it"), "variant": "display", "align": "center"},
                {"ui": "text", "text": p.get("subtitle", "Something heard you on floor -3."), "variant": "body",
                 "color": "@muted", "align": "center"}]},
            {"ui": "row", "gap": "md", "width": "fill", "align": "stretch", "wrap": True, "children": tiles},
            {"ui": "row", "gap": "sm", "justify": "center", "width": "fill", "children": btns}], max_w=640)]}


@tpl("notifications", "Stack of toasts in the top-right corner. {toasts: [{title?, text, tone}]}")
def t_notifications(p):
    toasts = p.get("toasts") or [{"title": "Saved", "text": "Progress saved to the cloud.", "tone": "success"},
                                 {"title": "Low battery", "text": "Your flashlight is at 12%.", "tone": "warning"}]
    return {"ui": "screen", "name": p.get("name", "Notifications"), "children": [
        {"ui": "column", "gap": "sm", "width": 360, "pos": [1, -20, 0, 20], "anchor": [1, 0],
         "children": [{"ui": "toast", **t, "width": "fill", "order": i} for i, t in enumerate(toasts)]}]}


def build(name, params):
    if name not in TPL:
        raise ForgeError(f"unknown template {name!r}; available: {sorted(TPL)}")
    return TPL[name](params or {})
