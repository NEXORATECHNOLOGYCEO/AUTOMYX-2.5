"""
Automyx 2.5 — Professional Subtitle Presets
============================================
A single source of truth for all subtitle styles used by `auto_subtitles`.

Each preset is a dict with ASS (Advanced SubStation Alpha) Style fields plus
a few Automyx-specific extras (margin_v override, alignment override, etc.).

Available presets (use `list_presets()` for a user-facing list):

  Bold/Energetic:
    - hype          Big white text with yellow outline, centered (default)
    - beast_gold    MrBeast-style: Arial Black 30, white fill, gold outline
    - tiktok_pop    CapCut-style: bold white with red highlight
    - reel_clean    Instagram Reels: medium bold, soft shadow
    - youtube_shorts White text with black outline, bottom

  Minimal/Clean:
    - minimal       Thin Arial 20, white, no outline
    - documentary   Serif font, lower-third style
    - news_banner   White on black bar (CNN/BBC style)
    - subtitle_bar  White text on semi-transparent black bar
    - clean_white   Plain white, thin shadow

  Cinematic:
    - cinematic     Georgia 20, italic, soft shadow
    - film_noir     White text, slow fade-in
    - netflix       Netflix-style: medium gray, white outline
    - letterbox     21:9 film look, white with thin black border

  Neon/Glow:
    - neon          Cyan glow effect
    - neon_pink     Magenta glow
    - neon_green    Green Matrix-style
    - synthwave     Pink/cyan gradient vibe
    - retro_arcade  Yellow pixel-style outline

  Social:
    - karaoke       Word-by-word highlight (yellow + white)
    - capcut_bold   CapCut default: bold white with black outline
    - tiktok_classic  Original TikTok style
    - meme          White Impact, all caps, top
    - explainer     Friendly rounded font, blue

  Animated (default Karaoke-style highlighting):
    - karaoke_word  Highlight current word
    - fade_in       Slow fade-in per line

  Premium/Pro:
    - studio        Pro studio look: white on dark bar
    - podcast       Lower-third name + caption
    - sports        Yellow Impact, all caps
    - vlog          Casual handwritten feel
    - interview     Two-line, name on top

You can also pass `font_color`, `outline_color`, `font_size`, `font_family`,
`outline_width`, `shadow`, `bold`, `italic`, `margin_v`, `alignment`, etc. as
keyword args and they'll override the preset's defaults.
"""
from __future__ import annotations

from typing import Optional


# ASS color table — BGR hex (NOT RGB). Use the helper `ass_color(name)` below.
_COLORS = {
    "blanco":  "&H00FFFFFF", "white":  "&H00FFFFFF",
    "negro":   "&H00000000", "black":  "&H00000000",
    "rojo":    "&H000000FF", "red":    "&H000000FF",
    "verde":   "&H0000FF00", "green":  "&H0000FF00",
    "azul":    "&H00FF0000", "blue":   "&H00FF0000",
    "amarillo":"&H0000FFFF", "yellow": "&H0000FFFF",
    "cyan":    "&H00FFFF00", "celeste":"&H00FFFF00",
    "magenta": "&H00FF00FF", "fucsia": "&H00FF00FF",
    "naranja": "&H0000A5FF", "orange": "&H0000A5FF",
    "morado":  "&H00800080", "purple": "&H00800080",
    "dorado":  "&H0000CCFF", "gold":   "&H0000CCFF",
    "plateado":"&H00C0C0C0", "silver": "&H00C0C0C0",
    "rosa":    "&H00CB92FF", "pink":   "&H00CB92FF",
    "lima":    "&H0000FF80", "lime":   "&H0000FF80",
}


def ass_color(name: Optional[str], default: str = "&H00FFFFFF") -> str:
    """Translate a color name (ES/EN) to ASS BGR hex. Unknown names pass through."""
    if not name:
        return default
    key = str(name).lower().strip()
    return _COLORS.get(key, default)


# ASS Style line fields:
#   Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour,
#   BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing,
#   Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV,
#   Encoding

# Default alignment (ASS numpad):
#   1 3 = bottom-left/right,    2 = bottom-center (default)
#   4 6 = mid-left/right,       5 = mid-center
#   7 9 = top-left/right,       8 = top-center

PRESETS = {
    # ============== BOLD / ENERGETIC ==============
    "hype": {
        "label": "Hype (default)",
        "category": "Bold",
        "description": "Bold white, yellow outline, centered. Ideal for hooks and Shorts.",
        "font_family": "Arial Black", "font_size": 30,
        "primary": ass_color("blanco"), "outline": ass_color("amarillo"),
        "outline_w": 3, "shadow": 2, "bold": True, "italic": False,
        "alignment": 5, "margin_v": 80,  # centered
    },
    "beast_gold": {
        "label": "Beast Gold (YouTube)",
        "category": "Bold",
        "description": "MrBeast-style: Arial Black 30, white fill, gold outline, drop shadow.",
        "font_family": "Arial Black", "font_size": 32,
        "primary": ass_color("blanco"), "outline": ass_color("dorado"),
        "outline_w": 4, "shadow": 3, "bold": True, "italic": False,
        "alignment": 5, "margin_v": 80,
    },
    "tiktok_pop": {
        "label": "TikTok Pop",
        "category": "Bold",
        "description": "CapCut-style: extra bold white with red highlight, all caps.",
        "font_family": "Impact", "font_size": 34,
        "primary": ass_color("blanco"), "outline": ass_color("rojo"),
        "outline_w": 3, "shadow": 2, "bold": True, "italic": False,
        "alignment": 2, "margin_v": 60,
        "uppercase": True,
    },
    "reel_clean": {
        "label": "Reel Clean",
        "category": "Bold",
        "description": "Instagram Reels: medium bold, soft shadow, white.",
        "font_family": "Arial", "font_size": 26,
        "primary": ass_color("blanco"), "outline": ass_color("negro"),
        "outline_w": 2, "shadow": 1, "bold": True, "italic": False,
        "alignment": 2, "margin_v": 90,
    },
    "youtube_shorts": {
        "label": "YouTube Shorts",
        "category": "Bold",
        "description": "Bold white with black outline, bottom — Shorts default.",
        "font_family": "Arial", "font_size": 28,
        "primary": ass_color("blanco"), "outline": ass_color("negro"),
        "outline_w": 3, "shadow": 1, "bold": True, "italic": False,
        "alignment": 2, "margin_v": 70,
    },

    # ============== MINIMAL / CLEAN ==============
    "minimal": {
        "label": "Minimal",
        "category": "Minimal",
        "description": "Thin Arial 20, white, no outline. Documentary style.",
        "font_family": "Arial", "font_size": 22,
        "primary": ass_color("blanco"), "outline": ass_color("negro"),
        "outline_w": 1, "shadow": 0, "bold": False, "italic": False,
        "alignment": 2, "margin_v": 50,
    },
    "documentary": {
        "label": "Documentary",
        "category": "Minimal",
        "description": "Serif font, lower-third, classic look.",
        "font_family": "Georgia", "font_size": 22,
        "primary": ass_color("blanco"), "outline": ass_color("negro"),
        "outline_w": 1, "shadow": 0, "bold": False, "italic": True,
        "alignment": 2, "margin_v": 60,
    },
    "news_banner": {
        "label": "News Banner",
        "category": "Minimal",
        "description": "White on black bar (CNN/BBC style).",
        "font_family": "Arial", "font_size": 24,
        "primary": ass_color("blanco"), "outline": ass_color("blanco"),
        "outline_w": 0, "shadow": 0, "bold": True, "italic": False,
        "alignment": 2, "margin_v": 50, "back": ass_color("negro"),
        "border_style": 3,  # opaque box
    },
    "subtitle_bar": {
        "label": "Subtitle Bar",
        "category": "Minimal",
        "description": "White text on semi-transparent black bar (default YouTube).",
        "font_family": "Arial", "font_size": 22,
        "primary": ass_color("blanco"), "outline": ass_color("blanco"),
        "outline_w": 0, "shadow": 0, "bold": False, "italic": False,
        "alignment": 2, "margin_v": 50, "back": "&H80000000",
        "border_style": 3,
    },
    "clean_white": {
        "label": "Clean White",
        "category": "Minimal",
        "description": "Plain white text with thin shadow, no outline.",
        "font_family": "Arial", "font_size": 24,
        "primary": ass_color("blanco"), "outline": ass_color("negro"),
        "outline_w": 0, "shadow": 1, "bold": False, "italic": False,
        "alignment": 2, "margin_v": 60,
    },

    # ============== CINEMATIC ==============
    "cinematic": {
        "label": "Cinematic",
        "category": "Cinematic",
        "description": "Georgia italic, soft shadow, lower-third.",
        "font_family": "Georgia", "font_size": 22,
        "primary": ass_color("blanco"), "outline": ass_color("negro"),
        "outline_w": 1, "shadow": 2, "bold": False, "italic": True,
        "alignment": 2, "margin_v": 60,
    },
    "film_noir": {
        "label": "Film Noir",
        "category": "Cinematic",
        "description": "White text with thin black border, classic 4:3 feel.",
        "font_family": "Courier New", "font_size": 22,
        "primary": ass_color("blanco"), "outline": ass_color("negro"),
        "outline_w": 2, "shadow": 0, "bold": False, "italic": False,
        "alignment": 2, "margin_v": 40,
    },
    "netflix": {
        "label": "Netflix",
        "category": "Cinematic",
        "description": "Netflix-style: medium gray with white outline, bottom.",
        "font_family": "Arial", "font_size": 22,
        "primary": ass_color("blanco"), "outline": ass_color("blanco"),
        "outline_w": 1, "shadow": 1, "bold": False, "italic": False,
        "alignment": 2, "margin_v": 50,
    },
    "letterbox": {
        "label": "Letterbox (21:9)",
        "category": "Cinematic",
        "description": "21:9 film look, white with thin black border, centered.",
        "font_family": "Georgia", "font_size": 20,
        "primary": ass_color("blanco"), "outline": ass_color("negro"),
        "outline_w": 1, "shadow": 1, "bold": False, "italic": False,
        "alignment": 5, "margin_v": 60,
    },

    # ============== NEON / GLOW ==============
    "neon": {
        "label": "Neon Cyan",
        "category": "Neon",
        "description": "Cyan glow effect on dark background.",
        "font_family": "Arial", "font_size": 30,
        "primary": ass_color("cyan"), "outline": ass_color("cyan"),
        "outline_w": 0, "shadow": 4, "bold": True, "italic": False,
        "alignment": 2, "margin_v": 60, "back": ass_color("negro"),
    },
    "neon_pink": {
        "label": "Neon Pink",
        "category": "Neon",
        "description": "Magenta/pink neon glow, party look.",
        "font_family": "Arial", "font_size": 30,
        "primary": ass_color("magenta"), "outline": ass_color("magenta"),
        "outline_w": 0, "shadow": 4, "bold": True, "italic": False,
        "alignment": 2, "margin_v": 60, "back": ass_color("negro"),
    },
    "neon_green": {
        "label": "Neon Green (Matrix)",
        "category": "Neon",
        "description": "Green Matrix-style glow, hacker aesthetic.",
        "font_family": "Courier New", "font_size": 28,
        "primary": ass_color("verde"), "outline": ass_color("verde"),
        "outline_w": 0, "shadow": 3, "bold": True, "italic": False,
        "alignment": 2, "margin_v": 60, "back": ass_color("negro"),
    },
    "synthwave": {
        "label": "Synthwave",
        "category": "Neon",
        "description": "Pink + cyan retro 80s vibe, italic.",
        "font_family": "Arial", "font_size": 28,
        "primary": ass_color("rosa"), "outline": ass_color("cyan"),
        "outline_w": 2, "shadow": 3, "bold": True, "italic": True,
        "alignment": 5, "margin_v": 80, "back": ass_color("negro"),
    },
    "retro_arcade": {
        "label": "Retro Arcade",
        "category": "Neon",
        "description": "Yellow pixel-style outline on black, 8-bit feel.",
        "font_family": "Courier New", "font_size": 26,
        "primary": ass_color("amarillo"), "outline": ass_color("amarillo"),
        "outline_w": 1, "shadow": 2, "bold": True, "italic": False,
        "alignment": 2, "margin_v": 60, "back": ass_color("negro"),
    },

    # ============== SOCIAL ==============
    "karaoke": {
        "label": "Karaoke Highlight",
        "category": "Social",
        "description": "Word-by-word highlight (yellow current + white rest).",
        "font_family": "Arial Black", "font_size": 28,
        "primary": ass_color("blanco"), "outline": ass_color("negro"),
        "outline_w": 2, "shadow": 1, "bold": True, "italic": False,
        "alignment": 2, "margin_v": 60, "secondary": ass_color("amarillo"),
        "karaoke": True,
    },
    "capcut_bold": {
        "label": "CapCut Bold",
        "category": "Social",
        "description": "CapCut default: bold white with black outline.",
        "font_family": "Arial", "font_size": 28,
        "primary": ass_color("blanco"), "outline": ass_color("negro"),
        "outline_w": 2, "shadow": 1, "bold": True, "italic": False,
        "alignment": 2, "margin_v": 60,
    },
    "tiktok_classic": {
        "label": "TikTok Classic",
        "category": "Social",
        "description": "Original TikTok caption: bold sans-serif, top.",
        "font_family": "Arial", "font_size": 26,
        "primary": ass_color("blanco"), "outline": ass_color("negro"),
        "outline_w": 2, "shadow": 1, "bold": True, "italic": False,
        "alignment": 8, "margin_v": 30,
    },
    "meme": {
        "label": "Meme (Impact)",
        "category": "Social",
        "description": "White Impact, all caps, top — classic meme.",
        "font_family": "Impact", "font_size": 36,
        "primary": ass_color("blanco"), "outline": ass_color("negro"),
        "outline_w": 3, "shadow": 1, "bold": True, "italic": False,
        "alignment": 8, "margin_v": 30, "uppercase": True,
    },
    "explainer": {
        "label": "Explainer",
        "category": "Social",
        "description": "Friendly rounded font, blue, educational.",
        "font_family": "Comic Sans MS", "font_size": 24,
        "primary": ass_color("azul"), "outline": ass_color("blanco"),
        "outline_w": 2, "shadow": 1, "bold": True, "italic": False,
        "alignment": 2, "margin_v": 60,
    },

    # ============== ANIMATED ==============
    "karaoke_word": {
        "label": "Karaoke Word",
        "category": "Animated",
        "description": "Word-by-word highlight, fast karaoke effect.",
        "font_family": "Arial Black", "font_size": 28,
        "primary": ass_color("blanco"), "outline": ass_color("negro"),
        "outline_w": 2, "shadow": 1, "bold": True, "italic": False,
        "alignment": 2, "margin_v": 60, "secondary": ass_color("amarillo"),
        "karaoke": True, "word_highlight": True,
    },
    "fade_in": {
        "label": "Fade In Lines",
        "category": "Animated",
        "description": "Slow fade-in per line, soft white.",
        "font_family": "Arial", "font_size": 24,
        "primary": ass_color("blanco"), "outline": ass_color("negro"),
        "outline_w": 1, "shadow": 1, "bold": False, "italic": False,
        "alignment": 2, "margin_v": 60, "fade": True,
    },
    "typewriter": {
        "label": "Typewriter",
        "category": "Animated",
        "description": "Letter-by-letter reveal.",
        "font_family": "Courier New", "font_size": 24,
        "primary": ass_color("lima"), "outline": ass_color("negro"),
        "outline_w": 1, "shadow": 1, "bold": False, "italic": False,
        "alignment": 2, "margin_v": 60, "back": ass_color("negro"),
    },

    # ============== PREMIUM / PRO ==============
    "studio": {
        "label": "Studio Pro",
        "category": "Pro",
        "description": "Pro studio look: white on dark bar, sans-serif.",
        "font_family": "Arial", "font_size": 24,
        "primary": ass_color("blanco"), "outline": ass_color("blanco"),
        "outline_w": 0, "shadow": 0, "bold": True, "italic": False,
        "alignment": 2, "margin_v": 50, "back": "&H80000000",
        "border_style": 3,
    },
    "podcast": {
        "label": "Podcast (lower third)",
        "category": "Pro",
        "description": "Lower-third name + caption.",
        "font_family": "Arial", "font_size": 22,
        "primary": ass_color("blanco"), "outline": ass_color("negro"),
        "outline_w": 1, "shadow": 1, "bold": True, "italic": False,
        "alignment": 4, "margin_v": 80,  # mid-left
    },
    "sports": {
        "label": "Sports Score",
        "category": "Pro",
        "description": "Yellow Impact, all caps — sports highlight style.",
        "font_family": "Impact", "font_size": 32,
        "primary": ass_color("amarillo"), "outline": ass_color("negro"),
        "outline_w": 3, "shadow": 1, "bold": True, "italic": False,
        "alignment": 8, "margin_v": 30, "uppercase": True,
    },
    "vlog": {
        "label": "Vlog Casual",
        "category": "Pro",
        "description": "Casual handwritten feel, soft white.",
        "font_family": "Comic Sans MS", "font_size": 24,
        "primary": ass_color("blanco"), "outline": ass_color("negro"),
        "outline_w": 1, "shadow": 1, "bold": False, "italic": False,
        "alignment": 2, "margin_v": 70,
    },
    "interview": {
        "label": "Interview (two-line)",
        "category": "Pro",
        "description": "Two-line: name on top in yellow, quote below in white.",
        "font_family": "Arial", "font_size": 22,
        "primary": ass_color("blanco"), "outline": ass_color("negro"),
        "outline_w": 1, "shadow": 1, "bold": False, "italic": False,
        "alignment": 7, "margin_v": 50,  # top-left
    },
}


# Backwards-compat aliases — old template names still work but route to a modern preset.
_ALIASES = {
    "mrbeast":      "beast_gold",
    "default":      "hype",
    "simple":       "minimal",
    "bold":         "hype",
    "minimal":      "minimal",
}


def get_preset(name: str) -> dict:
    """Resolve a preset name (with aliases) to its config dict.

    Returns the 'hype' preset as default if the name is unknown.
    """
    if not name:
        return PRESETS["hype"]
    key = str(name).lower().strip().replace(" ", "_").replace("-", "_")
    if key in _ALIASES:
        key = _ALIASES[key]
    if key in PRESETS:
        return dict(PRESETS[key])
    # Unknown — return hype
    return dict(PRESETS["hype"])


def list_presets() -> list[dict]:
    """Return a list of presets for the UI."""
    out = []
    for key, cfg in PRESETS.items():
        out.append({
            "id":          key,
            "label":       cfg.get("label", key.title()),
            "category":    cfg.get("category", "Other"),
            "description": cfg.get("description", ""),
        })
    return out


def categories() -> list[str]:
    """Return ordered list of unique categories."""
    seen = []
    for cfg in PRESETS.values():
        cat = cfg.get("category", "Other")
        if cat not in seen:
            seen.append(cat)
    return seen


# Build an ASS Style line for a resolved preset + user overrides.
def build_ass_style(preset: dict, overrides: Optional[dict] = None) -> str:
    """Build a complete ASS `Style:` line from a preset and user overrides.

    Accepted override keys (all optional):
        font_family, font_size, primary, secondary, outline, back,
        outline_w, shadow, bold, italic, alignment, margin_v, margin_l, margin_r,
        border_style, scale_x, scale_y, spacing
    """
    p = dict(preset)
    if overrides:
        for k, v in overrides.items():
            if v is not None:
                p[k] = v
    # Translate any color names that arrived as strings
    for ckey in ("primary", "secondary", "outline", "back"):
        if p.get(ckey) and not str(p[ckey]).startswith("&H"):
            p[ckey] = ass_color(p[ckey], p[ckey])
    primary   = p.get("primary",   "&H00FFFFFF")
    secondary = p.get("secondary", "&H000000FF")
    outline   = p.get("outline",   "&H00000000")
    back      = p.get("back",      "&H00000000")
    bold      = -1 if p.get("bold") else 0
    italic    = -1 if p.get("italic") else 0
    align     = int(p.get("alignment", 2))
    margin_l  = int(p.get("margin_l", 10))
    margin_r  = int(p.get("margin_r", 10))
    margin_v  = int(p.get("margin_v", 40))
    border_style = int(p.get("border_style", 1))
    outline_w = int(p.get("outline_w", 2))
    shadow    = int(p.get("shadow", 1))
    scale_x   = int(p.get("scale_x", 100))
    scale_y   = int(p.get("scale_y", 100))
    spacing   = int(p.get("spacing", 0))
    font_size = int(p.get("font_size", 24))
    font      = str(p.get("font_family", "Arial"))
    return (
        f"Style: Default,{font},{font_size},"
        f"{primary},{secondary},{outline},{back},"
        f"{bold},{italic},0,0,0,0,{scale_x},{scale_y},{spacing},0,"
        f"{border_style},{outline_w},{shadow},{align},"
        f"{margin_l},{margin_r},{margin_v},1"
    )
