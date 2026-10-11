"""Design tokens. A theme is plain JSON so it can be saved, edited and passed inline.

color: bg surface surface2 raised border text muted subtle accent (fills) accentFg (accent-coloured text on
       surfaces) accentText (text on an accent fill) accentSoft
       success warning danger scrim
font:  family (body/UI), display (headings), mono, weights
size:  caption label body title heading display  (TextSize, px)
space: xs sm md lg xl xxl                           (px)
radius: sm md lg pill                               (px)
"""
from __future__ import annotations

import json
from pathlib import Path

from ..studio import ForgeError

THEME_DIR = Path(__file__).resolve().parents[2] / "themes"

BASE_SIZES = {"caption": 12, "label": 14, "body": 15, "title": 18, "heading": 24, "display": 34}
BASE_SPACE = {"xs": 4, "sm": 8, "md": 12, "lg": 16, "xl": 24, "xxl": 32}

PRESETS = {
    # Neutral dark chat-app look: near-black layers, one warm accent, soft borders, generous spacing.
    "modern-dark": {
        "color": {"bg": "#141416", "surface": "#1c1c1f", "surface2": "#26262a", "raised": "#2d2d32",
                  "border": "#34343a", "text": "#ececf1", "muted": "#a1a1aa", "subtle": "#71717a",
                  "accent": "#b85a3a", "accentFg": "#e8a089", "accentText": "#ffffff", "accentSoft": "#3a2a24",
                  "success": "#4ade80", "warning": "#fbbf24", "danger": "#f87171", "dangerFill": "#b91c1c", "dangerText": "#ffffff", "scrim": "#000000"},
        "font": {"family": "BuilderSans", "display": "BuilderSans", "mono": "RobotoMono",
                 "regular": "Regular", "medium": "Medium", "strong": "SemiBold", "heavy": "Bold"},
        "size": BASE_SIZES, "space": BASE_SPACE, "radius": {"sm": 6, "md": 10, "lg": 14, "pill": 999},
        "stroke": 1, "surfaceT": 0, "scrimT": 0.45,
    },
    "modern-light": {
        "color": {"bg": "#f7f7f8", "surface": "#ffffff", "surface2": "#f0f0f2", "raised": "#ffffff",
                  "border": "#e4e4e7", "text": "#18181b", "muted": "#52525b", "subtle": "#a1a1aa",
                  "accent": "#4f46e5", "accentFg": "#4338ca", "accentText": "#ffffff", "accentSoft": "#e0e7ff",
                  "success": "#16a34a", "warning": "#b45309", "danger": "#dc2626", "dangerFill": "#dc2626", "dangerText": "#ffffff", "scrim": "#0a0a0a"},
        "font": {"family": "BuilderSans", "display": "BuilderSans", "mono": "RobotoMono",
                 "regular": "Regular", "medium": "Medium", "strong": "SemiBold", "heavy": "Bold"},
        "size": BASE_SIZES, "space": BASE_SPACE, "radius": {"sm": 6, "md": 10, "lg": 14, "pill": 999},
        "stroke": 1, "surfaceT": 0, "scrimT": 0.55,
    },
    # Frosted panels over the 3D world: translucent surfaces, bright hairline borders.
    "glass": {
        "color": {"bg": "#0b0f17", "surface": "#141b26", "surface2": "#1e2836", "raised": "#243042",
                  "border": "#9fb4d8", "text": "#f1f5ff", "muted": "#b6c2d9", "subtle": "#7d8aa3",
                  "accent": "#5ec8ff", "accentFg": "#8fd8ff", "accentText": "#04121c", "accentSoft": "#16374a",
                  "success": "#5eead4", "warning": "#fcd34d", "danger": "#fb7185", "dangerFill": "#be123c", "dangerText": "#ffffff", "scrim": "#000000"},
        "font": {"family": "Montserrat", "display": "Montserrat", "mono": "RobotoMono",
                 "regular": "Regular", "medium": "Medium", "strong": "SemiBold", "heavy": "Bold"},
        "size": BASE_SIZES, "space": BASE_SPACE, "radius": {"sm": 8, "md": 12, "lg": 18, "pill": 999},
        "stroke": 1, "surfaceT": 0.3, "strokeT": 0.78, "scrimT": 0.5,
    },
    "terminal": {
        "color": {"bg": "#050805", "surface": "#0a110a", "surface2": "#101a10", "raised": "#142214",
                  "border": "#1f7a3a", "text": "#b8f7c8", "muted": "#5fbf7a", "subtle": "#3a7a4c",
                  "accent": "#39ff88", "accentFg": "#39ff88", "accentText": "#021006", "accentSoft": "#0f2e19",
                  "success": "#39ff88", "warning": "#ffd166", "danger": "#ff5c7a", "dangerFill": "#b0213b", "dangerText": "#ffffff", "scrim": "#000000"},
        "font": {"family": "RobotoMono", "display": "RobotoMono", "mono": "RobotoMono",
                 "regular": "Regular", "medium": "Medium", "strong": "Bold", "heavy": "Bold"},
        "size": {"caption": 12, "label": 13, "body": 14, "title": 16, "heading": 20, "display": 28},
        "space": BASE_SPACE, "radius": {"sm": 2, "md": 3, "lg": 4, "pill": 999},
        "stroke": 1, "surfaceT": 0, "scrimT": 0.35,
    },
    # Mirrors the Backroom place's ReplicatedStorage.UITheme: dark plate, brass edge, Code font. Two deliberate
    # departures, both measured: muted is #9a9482 (the game's #847f70 falls to 4.0:1 on raised plates) and the
    # caption/label sizes are 11/12 (the game's 10/11 are under the 11px legibility floor).
    "backroom": {
        "color": {"bg": "#0d0c0a", "surface": "#0d0c0a", "surface2": "#1a1814", "raised": "#24211b",
                  "border": "#928868", "text": "#e4e0d2", "muted": "#9a9482", "subtle": "#736d60",
                  "accent": "#e9d892", "accentFg": "#e9d892", "accentText": "#0d0c0a", "accentSoft": "#2b281c",
                  "success": "#9ed096", "warning": "#e2c47e", "danger": "#d67a6e", "dangerFill": "#4a221f", "dangerText": "#eec6be", "scrim": "#000000"},
        "font": {"family": "Inconsolata", "display": "Inconsolata", "mono": "Inconsolata",
                 "regular": "Regular", "medium": "Medium", "strong": "Bold", "heavy": "Bold"},
        "size": {"caption": 11, "label": 12, "body": 13, "title": 17, "heading": 20, "display": 26},
        "space": {"xs": 3, "sm": 6, "md": 9, "lg": 12, "xl": 18, "xxl": 24},
        "radius": {"sm": 3, "md": 5, "lg": 6, "pill": 999},
        "stroke": 1, "surfaceT": 0.28, "strokeT": 0.74, "scrimT": 0.4,
    },
}


def load(theme) -> dict:
    """theme: preset name, saved theme name, or an inline dict (merged over modern-dark)."""
    if theme is None:
        theme = "modern-dark"
    if isinstance(theme, dict):
        base = json.loads(json.dumps(PRESETS[theme.get("extends", "modern-dark")]))
        for k, v in theme.items():
            if isinstance(v, dict) and isinstance(base.get(k), dict):
                base[k].update(v)
            else:
                base[k] = v
        base.setdefault("name", "custom")
        return base
    if theme in PRESETS:
        t = json.loads(json.dumps(PRESETS[theme]))
        t["name"] = theme
        return t
    p = THEME_DIR / f"{theme}.json"
    if p.exists():
        return load(json.loads(p.read_text(encoding="utf-8")))
    raise ForgeError(f"unknown theme {theme!r}; presets: {sorted(PRESETS)}, saved: {saved()}")


def saved():
    return sorted(p.stem for p in THEME_DIR.glob("*.json")) if THEME_DIR.exists() else []


def save(name, theme: dict):
    THEME_DIR.mkdir(exist_ok=True)
    (THEME_DIR / f"{name}.json").write_text(json.dumps(theme, indent=1), encoding="utf-8")


def _lin(c):
    c = c / 255
    return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4


def luminance(rgb):
    r, g, b = (_lin(x) for x in rgb)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast(a, b):
    la, lb = sorted((luminance(a), luminance(b)), reverse=True)
    return (la + 0.05) / (lb + 0.05)


def blend(fg, bg, alpha):
    """fg drawn at opacity alpha over bg."""
    return [round(f * alpha + b * (1 - alpha)) for f, b in zip(fg, bg)]


def contrast_report(theme: dict):
    from .schema import hex_rgb
    c = {k: hex_rgb(v) for k, v in theme["color"].items()}
    pairs = [("text", "bg"), ("text", "surface"), ("text", "surface2"), ("muted", "surface"), ("muted", "bg"),
             ("subtle", "surface"), ("accentText", "accent"), ("accentFg", "surface"), ("accentFg", "accentSoft"),
             ("accent", "surface"), ("dangerText", "dangerFill"), ("danger", "surface"),
             ("success", "surface"), ("warning", "surface")]
    rows = []
    for fg, bg in pairs:
        r = contrast(c[fg], c[bg])
        grade = "AAA" if r >= 7 else "AA" if r >= 4.5 else "AA-large" if r >= 3 else "FAIL"
        rows.append(f"{fg:>10} on {bg:<8} {r:5.2f}  {grade}")
    return "\n".join(rows)
