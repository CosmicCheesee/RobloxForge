"""UI spec: a declarative JSON tree, validated against a whitelist so the Luau side never meets a
class or property that would throw (Studio pauses on any eval error, pcall included).

Node:  {"type": "Frame", "name": "Card", "props": {...}, "attrs": {...}, "children": [...]}
   or  {"ui": "<component>", ...component params...}   (expanded by components.py)

Prop values (JSON):
  UDim2     [xs, xo, ys, yo]  |  {"scale": [x, y], "offset": [x, y]}  |  "fill" (= [1,0,1,0])
  UDim      number (offset)   |  [scale, offset]
  Vector2   [x, y]
  Color3    "#rrggbb" | [r, g, b] | "@token" (theme colour)
  numbers / bools / strings as-is; "@token.path" resolves theme numbers (e.g. "@size.body")
  enums     the item name, e.g. "Left", "Vertical", "SpaceBetween"
  FontFace  "Family" | {"family": "BuilderSans", "weight": "SemiBold", "style": "Normal"}
  ColorSequence   ["#a", "#b"]  |  [[t, "#hex"], ...]
  NumberSequence  number | [[t, v], ...]
"""
from __future__ import annotations

import re

from ..studio import ForgeError

UDIM2 = {"Size", "Position", "CanvasSize", "CellSize", "CellPadding"}
UDIM = {"CornerRadius", "Padding", "PaddingTop", "PaddingBottom", "PaddingLeft", "PaddingRight"}
VEC2 = {"AnchorPoint", "MinSize", "MaxSize", "Offset"}
COLOR = {"BackgroundColor3", "TextColor3", "ImageColor3", "TextStrokeColor3", "ScrollBarImageColor3",
         "PlaceholderColor3", "GroupColor3", "BorderColor3"}
NUM = {"BackgroundTransparency", "TextTransparency", "Transparency", "Thickness", "Rotation", "TextSize", "ZIndex",
       "LayoutOrder", "ScrollBarThickness", "AspectRatio", "Scale", "ImageTransparency", "MaxTextSize", "MinTextSize",
       "LineHeight", "DisplayOrder", "BorderSizePixel", "TextStrokeTransparency", "GroupTransparency",
       "ScrollBarImageTransparency", "GrowRatio", "ShrinkRatio", "FillDirectionMaxCells", "MaxVisibleGraphemes"}
BOOL = {"Visible", "TextWrapped", "TextScaled", "RichText", "ClipsDescendants", "IgnoreGuiInset", "ResetOnSpawn",
        "AutoButtonColor", "Active", "ClearTextOnFocus", "Enabled", "MultiLine", "TextEditable", "Wraps",
        "ScrollingEnabled", "Interactable"}
STR = {"Text", "Image", "PlaceholderText"}
ENUM = {
    "Font": "Font", "TextXAlignment": "TextXAlignment", "TextYAlignment": "TextYAlignment",
    "TextTruncate": "TextTruncate", "AutomaticSize": "AutomaticSize", "SizeConstraint": "SizeConstraint",
    "ScaleType": "ScaleType", "ScrollingDirection": "ScrollingDirection", "AutomaticCanvasSize": "AutomaticSize",
    "ZIndexBehavior": "ZIndexBehavior", "ScreenInsets": "ScreenInsets", "ApplyStrokeMode": "ApplyStrokeMode",
    "LineJoinMode": "LineJoinMode", "FillDirection": "FillDirection", "HorizontalAlignment": "HorizontalAlignment",
    "VerticalAlignment": "VerticalAlignment", "SortOrder": "SortOrder", "StartCorner": "StartCorner",
    "AspectType": "AspectType", "DominantAxis": "DominantAxis", "HorizontalFlex": "UIFlexAlignment",
    "VerticalFlex": "UIFlexAlignment", "ItemLineAlignment": "ItemLineAlignment", "FlexMode": "UIFlexMode",
}
ENUM_ITEMS = {
    "TextXAlignment": {"Left", "Right", "Center"}, "TextYAlignment": {"Top", "Center", "Bottom"},
    "TextTruncate": {"None", "AtEnd", "SplitWord"}, "AutomaticSize": {"None", "X", "Y", "XY"},
    "SizeConstraint": {"RelativeXY", "RelativeXX", "RelativeYY"}, "ScaleType": {"Stretch", "Slice", "Tile", "Fit", "Crop"},
    "ScrollingDirection": {"X", "Y", "XY"}, "ZIndexBehavior": {"Global", "Sibling"},
    "ScreenInsets": {"None", "DeviceSafeInsets", "CoreUISafeInsets", "TopbarSafeInsets"},
    "ApplyStrokeMode": {"Contextual", "Border"}, "LineJoinMode": {"Round", "Bevel", "Miter"},
    "FillDirection": {"Horizontal", "Vertical"}, "HorizontalAlignment": {"Center", "Left", "Right"},
    "VerticalAlignment": {"Center", "Top", "Bottom"}, "SortOrder": {"Name", "Custom", "LayoutOrder"},
    "StartCorner": {"TopLeft", "TopRight", "BottomLeft", "BottomRight"},
    "AspectType": {"FitWithinMaxSize", "ScaleWithParentSize"}, "DominantAxis": {"Width", "Height"},
    "UIFlexAlignment": {"None", "Fill", "SpaceAround", "SpaceBetween", "SpaceEvenly"},
    "ItemLineAlignment": {"Automatic", "Start", "Center", "End", "Stretch"},
    "UIFlexMode": {"None", "Grow", "Shrink", "Fill", "Custom"},
    "Font": {"Legacy", "Arial", "ArialBold", "SourceSans", "SourceSansBold", "SourceSansLight", "SourceSansItalic",
             "SourceSansSemibold", "Bodoni", "Garamond", "Cartoon", "Code", "Highway", "SciFi", "Arcade", "Fantasy",
             "Antique", "Gotham", "GothamMedium", "GothamBold", "GothamBlack", "AmaticSC", "Bangers", "Creepster",
             "DenkOne", "Fondamento", "FredokaOne", "GrenzeGotisch", "IndieFlower", "JosefinSans", "Jura", "Kalam",
             "LuckiestGuy", "Merriweather", "Michroma", "Nunito", "Oswald", "PatrickHand", "PermanentMarker", "Roboto",
             "RobotoCondensed", "RobotoMono", "Sarpanch", "SpecialElite", "TitilliumWeb", "Ubuntu", "BuilderSans",
             "BuilderSansMedium", "BuilderSansBold", "BuilderSansExtraBold", "Arimo", "ArimoBold"},
}
FONT_WEIGHTS = {"Thin", "ExtraLight", "Light", "Regular", "Medium", "SemiBold", "Bold", "ExtraBold", "Heavy"}

GUI = {"Size", "Position", "AnchorPoint", "BackgroundColor3", "BackgroundTransparency", "BorderSizePixel", "Visible",
       "ZIndex", "LayoutOrder", "ClipsDescendants", "Rotation", "AutomaticSize", "SizeConstraint", "Active",
       "Interactable", "BorderColor3"}
TEXT = {"Text", "TextColor3", "TextSize", "TextTransparency", "TextWrapped", "TextScaled", "TextXAlignment",
        "TextYAlignment", "RichText", "Font", "FontFace", "LineHeight", "TextTruncate", "TextStrokeTransparency",
        "TextStrokeColor3", "MaxVisibleGraphemes"}
IMAGE = {"Image", "ImageColor3", "ImageTransparency", "ScaleType"}
LAYOUT = {"FillDirection", "HorizontalAlignment", "VerticalAlignment", "SortOrder"}

CLASSES: dict[str, set[str]] = {
    "ScreenGui": {"Enabled", "IgnoreGuiInset", "ResetOnSpawn", "ZIndexBehavior", "DisplayOrder", "ScreenInsets"},
    "Frame": GUI,
    "CanvasGroup": GUI | {"GroupTransparency", "GroupColor3"},
    "TextLabel": GUI | TEXT,
    "TextButton": GUI | TEXT | {"AutoButtonColor"},
    "TextBox": GUI | TEXT | {"PlaceholderText", "PlaceholderColor3", "ClearTextOnFocus", "MultiLine", "TextEditable"},
    "ImageLabel": GUI | IMAGE,
    "ImageButton": GUI | IMAGE | {"AutoButtonColor"},
    "ScrollingFrame": GUI | {"CanvasSize", "ScrollBarThickness", "ScrollBarImageColor3", "ScrollBarImageTransparency",
                              "ScrollingDirection", "AutomaticCanvasSize", "ScrollingEnabled"},
    "UICorner": {"CornerRadius"},
    "UIStroke": {"Color", "Thickness", "Transparency", "ApplyStrokeMode", "LineJoinMode", "Enabled"},
    "UIPadding": {"PaddingTop", "PaddingBottom", "PaddingLeft", "PaddingRight"},
    "UIListLayout": LAYOUT | {"Padding", "HorizontalFlex", "VerticalFlex", "ItemLineAlignment", "Wraps"},
    "UIGridLayout": LAYOUT | {"CellSize", "CellPadding", "StartCorner", "FillDirectionMaxCells"},
    "UIGradient": {"Color", "Transparency", "Rotation", "Offset", "Enabled"},
    "UIAspectRatioConstraint": {"AspectRatio", "AspectType", "DominantAxis"},
    "UISizeConstraint": {"MinSize", "MaxSize"},
    "UITextSizeConstraint": {"MinTextSize", "MaxTextSize"},
    "UIScale": {"Scale"},
    "UIFlexItem": {"FlexMode", "GrowRatio", "ShrinkRatio", "ItemLineAlignment"},
}
GUI_OBJECTS = {"Frame", "CanvasGroup", "TextLabel", "TextButton", "TextBox", "ImageLabel", "ImageButton", "ScrollingFrame"}


def prop_type(cls: str, prop: str) -> str:
    if prop == "Color":
        return "cseq" if cls == "UIGradient" else "color"
    if prop == "Transparency" and cls == "UIGradient":
        return "nseq"
    if prop == "FontFace":
        return "font"
    for kind, names in (("udim2", UDIM2), ("udim", UDIM), ("vec2", VEC2), ("color", COLOR), ("num", NUM),
                        ("bool", BOOL), ("str", STR)):
        if prop in names:
            return kind
    if prop in ENUM:
        return "enum"
    raise ForgeError(f"no type known for {cls}.{prop}")


HEX = re.compile(r"#?([0-9a-fA-F]{6})")


def hex_rgb(s: str):
    m = HEX.fullmatch(s.strip())
    if not m:
        raise ForgeError(f"bad colour {s!r} (use #rrggbb)")
    h = m.group(1)
    return [int(h[i:i + 2], 16) for i in (0, 2, 4)]


def _num(v, where):
    if isinstance(v, bool) or not isinstance(v, (int, float)):
        raise ForgeError(f"{where}: expected a number, got {v!r}")
    return float(v)


class Resolver:
    """Resolves "@token" references against a theme dict."""

    def __init__(self, theme: dict):
        self.theme = theme

    def lookup(self, ref: str):
        path = ref[1:].split(".")
        if len(path) == 1 and path[0] in self.theme.get("color", {}):
            return self.theme["color"][path[0]]
        cur = self.theme
        for p in path:
            if isinstance(cur, dict) and p in cur:
                cur = cur[p]
            else:
                raise ForgeError(f"unknown theme token {ref}")
        return cur

    def deref(self, v):
        return self.lookup(v) if isinstance(v, str) and v.startswith("@") else v


def encode(cls: str, prop: str, v, R: Resolver):
    """-> [type, ...payload] ready for Luau / codegen."""
    where = f"{cls}.{prop}"
    v = R.deref(v)
    t = prop_type(cls, prop)
    if t == "udim2":
        if v == "fill":
            return ["udim2", [1, 0, 1, 0]]
        if isinstance(v, dict):
            s, o = v.get("scale", [0, 0]), v.get("offset", [0, 0])
            v = [s[0], o[0], s[1], o[1]]
        if not (isinstance(v, list) and len(v) == 4):
            raise ForgeError(f"{where}: UDim2 must be [xs, xo, ys, yo]")
        return ["udim2", [_num(x, where) for x in v]]
    if t == "udim":
        if isinstance(v, (int, float)) and not isinstance(v, bool):
            return ["udim", [0.0, float(v)]]
        if isinstance(v, list) and len(v) == 2:
            return ["udim", [_num(x, where) for x in v]]
        raise ForgeError(f"{where}: UDim must be a number or [scale, offset]")
    if t == "vec2":
        if isinstance(v, list) and len(v) == 2:
            return ["vec2", [_num(x, where) for x in v]]
        raise ForgeError(f"{where}: Vector2 must be [x, y]")
    if t == "color":
        return ["color", color(v, where, R)]
    if t == "num":
        return ["num", _num(R.deref(v), where)]
    if t == "bool":
        if not isinstance(v, bool):
            raise ForgeError(f"{where}: expected true/false")
        return ["bool", v]
    if t == "str":
        return ["str", str(v)]
    if t == "enum":
        if not (isinstance(v, str) and re.fullmatch(r"[A-Za-z0-9]+", v)):
            raise ForgeError(f"{where}: enum item must be a name like 'Left'")
        items = ENUM_ITEMS.get(ENUM[prop])
        if items is not None and v not in items:
            raise ForgeError(f"{where}: {v!r} is not an Enum.{ENUM[prop]} item ({sorted(items)})")
        return ["enum", ENUM[prop], v]
    if t == "font":
        if isinstance(v, str):
            v = {"family": v}
        fam = str(R.deref(v.get("family", "BuilderSans")))
        if not re.fullmatch(r"[A-Za-z0-9]+", fam):
            raise ForgeError(f"{where}: font family must be a bare name like 'BuilderSans'")
        w = R.deref(v.get("weight", "Regular"))
        if w not in FONT_WEIGHTS:
            raise ForgeError(f"{where}: weight {w!r} not in {sorted(FONT_WEIGHTS)}")
        st = v.get("style", "Normal")
        if st not in ("Normal", "Italic"):
            raise ForgeError(f"{where}: style must be Normal or Italic")
        return ["font", fam, w, st]
    if t == "cseq":
        # ["#a", "#b", ...] evenly spaced, or [[t, colour], ...] stops; a lone colour is flat
        if isinstance(v, list) and v and isinstance(v[0], (str, list)) and not (len(v) == 3 and isinstance(v[0], (int, float))):
            n = len(v)
            pts = []
            for i, x in enumerate(v):
                if isinstance(x, list) and len(x) == 2:
                    pts.append([_num(x[0], where), color(x[1], where, R)])
                else:
                    pts.append([i / max(n - 1, 1), color(x, where, R)])
            if len(pts) == 1:
                pts.append([1.0, pts[0][1]])
            pts.sort(key=lambda p: p[0])
            pts[0][0], pts[-1][0] = 0.0, 1.0
            return ["cseq", pts]
        c = color(v, where, R)
        return ["cseq", [[0.0, c], [1.0, c]]]
    if t == "nseq":
        if isinstance(v, (int, float)):
            return ["nseq", [[0.0, float(v)], [1.0, float(v)]]]
        pts = sorted([[max(0.0, min(1.0, _num(x[0], where))), max(0.0, min(1.0, _num(x[1], where)))] for x in v])
        if len(pts) == 1:
            pts.append([1.0, pts[0][1]])
        pts[0][0], pts[-1][0] = 0.0, 1.0
        return ["nseq", pts]
    raise ForgeError(f"{where}: unhandled")


def color(v, where, R: Resolver):
    v = R.deref(v)
    if isinstance(v, str):
        return hex_rgb(v)
    if isinstance(v, list) and len(v) == 3:
        return [int(max(0, min(255, round(_num(c, where))))) for c in v]
    raise ForgeError(f"{where}: colour must be #rrggbb, [r,g,b] or @token")


def normalize(node, R: Resolver, expand, depth=0, counter=None):
    """Validate + expand a spec tree. `expand(node, R)` turns {"ui": ...} into plain nodes."""
    counter = counter if counter is not None else [0]
    if depth > 40:
        raise ForgeError("UI tree deeper than 40")
    if not isinstance(node, dict):
        raise ForgeError(f"UI node must be an object, got {node!r}")
    if "ui" in node:
        node = expand(node, R)
    cls = node.get("type")
    if cls not in CLASSES:
        raise ForgeError(f"unsupported class {cls!r}; supported: {sorted(CLASSES)}")
    counter[0] += 1
    if counter[0] > 4000:
        raise ForgeError("more than 4000 UI instances")
    allowed = CLASSES[cls]
    props = []
    for k, v in (node.get("props") or {}).items():
        if k not in allowed:
            raise ForgeError(f"{cls} has no property {k} (allowed: {sorted(allowed)})")
        props.append([k] + encode(cls, k, v, R))
    attrs = {}
    for k, v in (node.get("attrs") or {}).items():
        if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]{0,99}", str(k)):
            raise ForgeError(f"bad attribute name {k!r}")
        if not isinstance(v, (str, int, float, bool)):
            raise ForgeError(f"attribute {k} must be string/number/bool")
        attrs[str(k)] = v
    kids = [normalize(c, R, expand, depth + 1, counter) for c in (node.get("children") or []) if c is not None]
    if cls not in GUI_OBJECTS and cls != "ScreenGui" and kids:
        raise ForgeError(f"{cls} cannot have children")
    name = str(node.get("name") or cls)
    return {"type": cls, "name": name[:100], "props": props, "attrs": attrs, "children": kids}


def get(node, prop):
    for p in node["props"]:
        if p[0] == prop:
            return p[1:]
    return None


# ===== GLYPHS, MEASURED IN THE ENGINE (2026-10-10, BuilderSans + RobotoMono, Studio playtest) =====
# Render fine: × ✓ ○ ◆ ♥ ★ ▶ ↑ ↓ ← → ⬆ ⬇ ∞ ⚙ ☀ ☂ ◉ ☗ ⚠ ✚ … and colour emoji (⚡ ⚔ come out as emoji).
# Render as an empty box: ✕ ✦ ♜ ⟳ ✎ ☰.  Render as a near-invisible dark emoji: ✖ ✔.
BROKEN_GLYPHS = {"✕": "×", "✦": "★", "♜": "◆", "⟳": "↻ (untested) or the word", "✎": "the word 'Edit'",
                 "☰": "≡ (untested) or three Frames", "✖": "×", "✔": "✓"}
SAFE_GLYPHS = "× ✓ ○ ◆ ♥ ★ ▶ ↑ ↓ ← → ⬆ ⬇ ∞ ⚙ ☀ ☂ ◉ ☗ ⚠ ✚ …"


def glyph_warnings(node, out=None, path=""):
    out = [] if out is None else out
    here = f"{path}.{node['name']}"
    for p in node["props"]:
        if p[0] in ("Text", "PlaceholderText") and p[1] == "str":
            bad = sorted({ch for ch in p[2] if ch in BROKEN_GLYPHS})
            if bad:
                out.append(f"GLYPH  {here}: {' '.join(bad)} render as empty boxes in Roblox -- use "
                           + ", ".join(f"{b} -> {BROKEN_GLYPHS[b]}" for b in bad))
    for c in node["children"]:
        glyph_warnings(c, out, here)
    return out
