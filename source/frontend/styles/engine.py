"""Core Theming Engine for Clara.

Implements layered theme resolution, native Base16 / Base24 ingestion,
automatic grayscale luminance inversion (light/dark mode flip), semantic token mapping,
and compilation of UI primitives down to clean, fast Qt StyleSheets (QSS).
"""

import copy
import re
from typing import Any, Dict, Optional, Tuple, Union

# ------------------------------------------------------------------------------------------------------------
# 1. System Core Geometry & Spacing Defaults
# ------------------------------------------------------------------------------------------------------------

SYSTEM_DEFAULTS: Dict[str, str] = {
    # Geometry & Radii
    "radius-xs": "2px",
    "radius-sm": "4px",
    "radius-md": "8px",
    "radius-lg": "12px",
    "radius-full": "9999px",

    # Spacing scale
    "space-xs": "4px",
    "space-sm": "8px",
    "space-md": "12px",
    "space-lg": "16px",
    "space-xl": "24px",

    # Typography
    "font-family": "inherit",
    "font-size-base": "10pt",
    "font-size-xs": "9px",
    "font-size-sm": "11px",
    "font-size-md": "13px",
    "font-size-lg": "15px",
    "font-size-xl": "18px",

    # Controls & Dimensions
    "input-height": "28px",
    "btn-height": "28px",
    "table-row-height": "30px",
    "header-height": "28px",
    "rack-item-height": "48px",
    "card-width": "195px",
    "card-height": "120px",
}

# ------------------------------------------------------------------------------------------------------------
# 2. Base16 / Base24 Scale Inversion for Light / Dark Mode
# ------------------------------------------------------------------------------------------------------------

def invert_grayscale_scale(palette: Dict[str, str]) -> Dict[str, str]:
    """Invert the luminance range (base00 <-> base07) for light mode.

    Dark mode convention:
      base00: Darkest background
      base01: Lighter background / surface
      base02: Selection background / hover
      base03: Comments / subtle borders
      base04: Dark foreground / muted text
      base05: Default foreground
      base06: Light foreground
      base07: Lightest foreground

    Light mode inversion swaps the pairs without modifying accents (base08-base17):
      base00 <-> base07
      base01 <-> base06
      base02 <-> base05
      base03 <-> base04
    """
    inverted = copy.deepcopy(palette)
    pairs = [
        ("base00", "base07"),
        ("base01", "base06"),
        ("base02", "base05"),
        ("base03", "base04"),
    ]
    for low, high in pairs:
        val_low = palette.get(low)
        val_high = palette.get(high)
        if val_low and val_high:
            inverted[low] = val_high
            inverted[high] = val_low
        elif val_low and not val_high:
            inverted[high] = val_low
        elif val_high and not val_low:
            inverted[low] = val_high
    return inverted

def normalize_color(col: str) -> str:
    """Ensure color string starts with '#' if it is a 6-digit or 3-digit hex."""
    c = (col or "").strip()
    if re.match(r"^[0-9a-fA-F]{3,8}$", c):
        return f"#{c}"
    return c

# ------------------------------------------------------------------------------------------------------------
# 3. Semantic Color Token Mapping
# ------------------------------------------------------------------------------------------------------------

def map_base_to_semantic(palette: Dict[str, str], mode: str = "dark") -> Dict[str, str]:
    """Map Base16 / Base24 tokens to semantic color variables."""
    p = {k: normalize_color(v) for k, v in palette.items()}

    # Base00 - Base07 (Monochrome scale)
    base00 = p.get("base00", "#181926" if mode == "dark" else "#eff1f5")
    base01 = p.get("base01", "#1e2030" if mode == "dark" else "#e6e9ef")
    base02 = p.get("base02", "#24273a" if mode == "dark" else "#ccd0da")
    base03 = p.get("base03", "#363a4f" if mode == "dark" else "#bcc0cc")
    base04 = p.get("base04", "#5b6078" if mode == "dark" else "#acb0be")
    base05 = p.get("base05", "#cad3f5" if mode == "dark" else "#4c4f69")
    base06 = p.get("base06", "#ed8796" if mode == "dark" else "#5c5f77")
    base07 = p.get("base07", "#f4dbd6" if mode == "dark" else "#6c6f85")

    # Accents (Base08 - Base0F)
    base08 = p.get("base08", "#ed8796")  # Red
    base09 = p.get("base09", "#f5a97f")  # Orange
    base0A = p.get("base0A", "#eed49f")  # Yellow
    base0B = p.get("base0B", "#a6da95")  # Green
    base0C = p.get("base0C", "#8bd5ca")  # Cyan
    base0D = p.get("base0D", "#8aadf4")  # Blue
    base0E = p.get("base0E", "#c6a0f6")  # Purple
    base0F = p.get("base0F", "#f0c6c6")  # Magenta / Brown

    # Base24 extended accents (if provided)
    base10 = p.get("base10", base00)
    base11 = p.get("base11", base00)
    base12 = p.get("base12", base08)
    base13 = p.get("base13", base0A)
    base14 = p.get("base14", base0B)
    base15 = p.get("base15", base0C)
    base16 = p.get("base16", base0D)
    base17 = p.get("base17", base0E)

    # Core Semantic Roles
    bg_primary = base00
    bg_surface = base01
    bg_hover = base02
    bg_selected = base02
    border_dim = base03
    border_focus = base0D
    text_muted = base04
    text_secondary = base05
    # Inversion above already puts the background in base00 and the text in base05.
    text_primary = base05
    accent = base0D

    semantic: Dict[str, str] = {
        # Raw base slots
        "base00": base00, "base01": base01, "base02": base02, "base03": base03,
        "base04": base04, "base05": base05, "base06": base06, "base07": base07,
        "base08": base08, "base09": base09, "base0A": base0A, "base0B": base0B,
        "base0C": base0C, "base0D": base0D, "base0E": base0E, "base0F": base0F,
        "base10": base10, "base11": base11, "base12": base12, "base13": base13,
        "base14": base14, "base15": base15, "base16": base16, "base17": base17,

        # Semantic UI tokens
        "bg-primary": bg_primary,
        "bg-surface": bg_surface,
        "bg-hover": bg_hover,
        "bg-selected": bg_selected,
        "border-dim": border_dim,
        "border-focus": border_focus,
        "text-primary": text_primary,
        "text-secondary": text_secondary,
        "text-muted": text_muted,
        "accent": accent,

        # Status / Syntax tokens
        "red": base08,
        "orange": base09,
        "yellow": base0A,
        "green": base0B,
        "cyan": base0C,
        "blue": base0D,
        "purple": base0E,
        "magenta": base0F,

        # Alpha highlights (RGBA approximations)
        "accent-tint-10": _hex_to_rgba(accent, 0.10),
        "accent-tint-15": _hex_to_rgba(accent, 0.15),
        "accent-tint-20": _hex_to_rgba(accent, 0.20),
        "accent-tint-50": _hex_to_rgba(accent, 0.50),
        "border-subtle": _hex_to_rgba(text_primary, 0.08),
    }

    return semantic

def _hex_to_rgba(hex_color: str, alpha: float) -> str:
    h = hex_color.lstrip("#")
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    if len(h) >= 6:
        r = int(h[0:2], 16)
        g = int(h[2:4], 16)
        b = int(h[4:6], 16)
        return f"rgba({r}, {g}, {b}, {alpha:.2f})"
    return hex_color

# ------------------------------------------------------------------------------------------------------------
# 4. Layered Theme Resolver Pipeline
# ------------------------------------------------------------------------------------------------------------

class ThemeEngine:
    """Resolves and compiles theme definitions into robust QSS stylesheets."""

    def __init__(self, base_primitives_template: Optional[str] = None):
        self.base_template = base_primitives_template or ""
        self.active_tokens: Dict[str, str] = {}

    def get_token(self, name: str, default: str = "") -> str:
        """Get an active resolved token value by key name (with or without -- prefix)."""
        key = name[2:] if name.startswith("--") else name
        return self.active_tokens.get(key, self.active_tokens.get(f"--{key}", default))

    def resolve_tokens(
        self,
        theme_def: Dict[str, Any],
        mode: Optional[str] = None,
        structural_overrides: Optional[Dict[str, str]] = None,
    ) -> Dict[str, str]:
        """Strict cascade resolution:
        Defaults -> Base16/Base24 Inversion -> Semantic Map -> Overrides
        """
        # 1. System core defaults
        tokens = copy.deepcopy(SYSTEM_DEFAULTS)

        # 2. Extract palette
        raw_palette = theme_def.get("palette", theme_def)
        palette = {k: str(v) for k, v in raw_palette.items() if k.startswith("base")}

        # 3. Determine if palette needs light inversion
        # The theme definition itself knows its mode; an omitted mode argument
        # must never silently invert a light theme through the "dark" default.
        if mode is None:
            mode = str(theme_def.get("mode", "dark"))
        target_mode = mode.lower()
        is_already_light = theme_def.get("mode", "dark").lower() == "light"
        if target_mode == "light" and not is_already_light:
            palette = invert_grayscale_scale(palette)
        elif target_mode == "dark" and is_already_light:
            palette = invert_grayscale_scale(palette)

        # 4. Map to semantic variables
        semantic = map_base_to_semantic(palette, mode=target_mode)
        tokens.update(semantic)

        # 5. Apply explicit theme overrides
        if "overrides" in theme_def and isinstance(theme_def["overrides"], dict):
            tokens.update(theme_def["overrides"])

        # 6. Apply structural runtime overrides (e.g. custom user font, spacing)
        if structural_overrides:
            tokens.update(structural_overrides)

        return tokens

    def compile_qss(
        self,
        theme_def: Dict[str, Any],
        mode: str = "dark",
        structural_overrides: Optional[Dict[str, str]] = None,
    ) -> str:
        """Compile the resolved theme tokens into valid QSS by interpolating variables."""
        tokens = self.resolve_tokens(theme_def, mode, structural_overrides)
        self.active_tokens = tokens
        template = self.base_template

        # Support both var(--name) and {{name}} syntax in QSS template
        def replace_var(match):
            token_name = match.group(1).strip()
            # Strip '--' prefix if present
            if token_name.startswith("--"):
                token_name = token_name[2:]
            return tokens.get(token_name, tokens.get(f"--{token_name}", match.group(0)))

        compiled = re.sub(r"var\((--?[a-zA-Z0-9_\-]+)\)", replace_var, template)
        compiled = re.sub(r"\{\{([a-zA-Z0-9_\-]+)\}\}", replace_var, compiled)

        return compiled
