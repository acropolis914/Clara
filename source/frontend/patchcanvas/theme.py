#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2011-2025 Filipe Coelho <falktx@falktx.com>
# SPDX-License-Identifier: GPL-2.0-or-later

# ------------------------------------------------------------------------------------------------------------
# Imports (Global)

import json
import os

from qt_compat import Qt, QBrush, QColor, QFont, QPen, QPixmap

# ------------------------------------------------------------------------------------------------------------
# Theme definition file path

THEMES_JSON_FILE = os.path.join(os.path.dirname(__file__), "themes.json")

# ------------------------------------------------------------------------------------------------------------
# Color, Pen & Contrast Helpers

def parse_rgb(c):
    """Return (r, g, b) tuple from hex string, list/tuple, or QColor."""
    if isinstance(c, QColor):
        return (c.red(), c.green(), c.blue())
    if isinstance(c, str):
        c = c.strip().lstrip("#")
        if len(c) in (3, 4):
            return (int(c[0] * 2, 16), int(c[1] * 2, 16), int(c[2] * 2, 16))
        elif len(c) >= 6:
            return (int(c[0:2], 16), int(c[2:4], 16), int(c[4:6], 16))
    if isinstance(c, (list, tuple)) and len(c) >= 3:
        return (int(c[0]), int(c[1]), int(c[2]))
    return (0, 0, 0)


def calculate_contrast(rgb1, rgb2):
    """Calculate WCAG 2.1 contrast ratio between two RGB tuples."""
    def channel_lum(val):
        c = val / 255.0
        return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4

    l1 = (
        0.2126 * channel_lum(rgb1[0])
        + 0.7152 * channel_lum(rgb1[1])
        + 0.0722 * channel_lum(rgb1[2])
    )
    l2 = (
        0.2126 * channel_lum(rgb2[0])
        + 0.7152 * channel_lum(rgb2[1])
        + 0.0722 * channel_lum(rgb2[2])
    )
    return (max(l1, l2) + 0.05) / (min(l1, l2) + 0.05)


def adjust_text_for_contrast(text_color_val, bg_color_val, min_contrast=4.5):
    """
    Adjust text color towards white or black until it meets min_contrast ratio
    against the background color.
    """
    text_rgb = parse_rgb(text_color_val)
    bg_rgb = parse_rgb(bg_color_val)
    if calculate_contrast(text_rgb, bg_rgb) >= min_contrast:
        return text_color_val

    cr_white = calculate_contrast((255, 255, 255), bg_rgb)
    cr_black = calculate_contrast((0, 0, 0), bg_rgb)
    target_rgb = (255, 255, 255) if cr_white >= cr_black else (0, 0, 0)

    for step in range(1, 101):
        t = step / 100.0
        candidate = (
            int(text_rgb[0] * (1 - t) + target_rgb[0] * t),
            int(text_rgb[1] * (1 - t) + target_rgb[1] * t),
            int(text_rgb[2] * (1 - t) + target_rgb[2] * t),
        )
        if calculate_contrast(candidate, bg_rgb) >= min_contrast:
            return f"#{candidate[0]:02x}{candidate[1]:02x}{candidate[2]:02x}"

    return f"#{target_rgb[0]:02x}{target_rgb[1]:02x}{target_rgb[2]:02x}"


def _with_alpha(color_val, alpha):
    """Return a #rrggbbaa string with the given alpha byte."""
    r, g, b = parse_rgb(color_val)
    return "#%02x%02x%02x%02x" % (r, g, b, int(alpha))


def parse_color(c):
    """Parse color from hex string, list/tuple, or QColor."""
    if isinstance(c, QColor):
        return c
    if isinstance(c, str):
        c = c.strip()
        if c.startswith("#"):
            h = c[1:]
            if len(h) == 3:
                return QColor(int(h[0] * 2, 16), int(h[1] * 2, 16), int(h[2] * 2, 16))
            elif len(h) == 4:
                return QColor(
                    int(h[0] * 2, 16),
                    int(h[1] * 2, 16),
                    int(h[2] * 2, 16),
                    int(h[3] * 2, 16),
                )
            elif len(h) == 6:
                return QColor(int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16))
            elif len(h) == 8:
                return QColor(
                    int(h[0:2], 16),
                    int(h[2:4], 16),
                    int(h[4:6], 16),
                    int(h[6:8], 16),
                )
        return QColor(c)
    if isinstance(c, (list, tuple)):
        if len(c) == 3:
            return QColor(int(c[0]), int(c[1]), int(c[2]))
        elif len(c) >= 4:
            return QColor(int(c[0]), int(c[1]), int(c[2]), int(c[3]))
    return QColor(0, 0, 0)


def parse_pen(color_val, width=1, style="solid"):
    """Parse pen from color, width, and style string."""
    if isinstance(color_val, QPen):
        return color_val
    color = parse_color(color_val)
    pen_style = Qt.SolidLine
    if style == "dash":
        pen_style = Qt.DashLine
    elif style == "dot":
        pen_style = Qt.DotLine
    elif style == "none":
        pen_style = Qt.NoPen
    return QPen(color, width, pen_style)


def parse_theme_dict(raw):
    """
    Parse a raw flat theme dict from themes.json into Qt objects in memory,
    automatically calculating and adjusting port text contrast if needed.
    """
    data = dict(raw)

    # 1. Calculate & adjust node port text contrast if not in socket mode
    is_socket = str(data.get("port_mode", "")).lower() == "socket"
    if not is_socket:
        for ptype in ("audio_jack", "midi_jack", "midi_alsa", "parameter"):
            for state in ("", "_sel"):
                bg_key = f"port_{ptype}_bg{state}"
                text_key = f"port_{ptype}_text{state}"
                if bg_key in data and text_key in data:
                    data[text_key] = adjust_text_for_contrast(
                        data[text_key], data[bg_key], min_contrast=4.5
                    )

    # 1b. Keep the selected node title readable on the header background, otherwise it can
    #     blend into the header and the node name appears to vanish while the node is focused
    header_bg = data.get("box_bg_2") or data.get("box_bg_1")
    if header_bg and "box_text_sel" in data:
        data["box_text_sel"] = adjust_text_for_contrast(
            data["box_text_sel"], header_bg, min_contrast=4.5
        )

    parsed = {}

    # 2. Reassemble flattened pens (box_pen, box_pen_sel, rubberband_pen, port pens)
    pen_bases = ["box_pen", "box_pen_sel", "rubberband_pen"]
    for ptype in ("audio_jack", "midi_jack", "midi_alsa", "parameter"):
        pen_bases.append(f"port_{ptype}_pen")
        pen_bases.append(f"port_{ptype}_pen_sel")

    for base in pen_bases:
        color_k = f"{base}_color"
        width_k = f"{base}_width"
        style_k = f"{base}_style"
        if color_k in data:
            parsed[base] = parse_pen(
                data[color_k], data.get(width_k, 1), data.get(style_k, "solid")
            )
        elif base in data:
            v = data[base]
            if isinstance(v, list):
                c = v[0]
                w = v[1] if len(v) > 1 else 1
                s = v[2] if len(v) > 2 else "solid"
                parsed[base] = parse_pen(c, w, s)
            else:
                parsed[base] = parse_pen(v)

    # 3. Process all other attributes
    for k, v in data.items():
        if k.endswith("_color") or k.endswith("_width") or k.endswith("_style"):
            continue
        if k == "rubberband_brush":
            c = parse_color(v)
            parsed[k] = QBrush(c)
        elif (
            k in ("canvas_bg", "box_bg_1", "box_bg_2", "box_shadow")
            or k.endswith("_bg")
            or k.endswith("_bg_sel")
            or k.startswith("line_")
        ):
            parsed[k] = parse_color(v)
        elif k.endswith("_text") or k.endswith("_text_sel"):
            parsed[k] = parse_pen(v, width=0)
        elif k in ("box_font_state", "port_font_state"):
            parsed[k] = QFont.Bold if str(v).lower() == "bold" else QFont.Normal
        elif k == "box_bg_type":
            parsed[k] = (
                Theme.THEME_BG_GRADIENT
                if (str(v).lower() == "gradient" or v == 1)
                else Theme.THEME_BG_SOLID
            )
        elif k == "port_mode":
            mode_str = str(v).lower()
            if mode_str == "socket" or v == 2:
                parsed[k] = Theme.THEME_PORT_SOCKET
            elif mode_str == "polygon" or v == 1:
                parsed[k] = Theme.THEME_PORT_POLYGON
            else:
                parsed[k] = Theme.THEME_PORT_SQUARE
        elif k in ("box_header_pixmap", "port_bg_pixmap"):
            parsed[k] = QPixmap(v) if v else None
        else:
            parsed[k] = v

    return parsed


# ------------------------------------------------------------------------------------------------------------
# Theme Loader & Registry

_CACHED_THEMES_RAW = None


def load_themes_data(reload=False):
    """Load themes dictionary from themes.json (cached unless reload=True)."""
    global _CACHED_THEMES_RAW
    if _CACHED_THEMES_RAW is not None and not reload:
        return _CACHED_THEMES_RAW

    if os.path.exists(THEMES_JSON_FILE):
        try:
            with open(THEMES_JSON_FILE, "r", encoding="utf-8") as f:
                _CACHED_THEMES_RAW = json.load(f)
                Theme.THEME_MAX = len(_CACHED_THEMES_RAW)
                return _CACHED_THEMES_RAW
        except Exception as e:
            print(f"Warning: Failed to load patchcanvas themes from {THEMES_JSON_FILE}: {e}")

    if _CACHED_THEMES_RAW is None:
        _CACHED_THEMES_RAW = {}
    Theme.THEME_MAX = len(_CACHED_THEMES_RAW)
    return _CACHED_THEMES_RAW


def get_swatch_colors():
    """User-facing tint choices, resolved from the active theme."""
    try:
        from styles.theme_manager import theme_manager
        t = theme_manager.engine.active_tokens or {}
    except Exception:
        t = {}
    return [
        (t.get("red", "#f38ba8"), "Red"),
        (t.get("orange", "#fab387"), "Peach"),
        (t.get("yellow", "#f9e2af"), "Yellow"),
        (t.get("green", "#a6e3a1"), "Green"),
        (t.get("cyan", "#94e2d5"), "Teal"),
        (t.get("blue", "#89b4fa"), "Blue"),
        (t.get("purple", "#cba6f7"), "Mauve"),
        (t.get("magenta", "#f5c2e7"), "Pink"),
    ]


def getThemeNames():
    """Return list of all theme names loaded from themes.json."""
    return list(load_themes_data().keys())


def getThemeName(idx):
    """Get theme name by integer index."""
    names = getThemeNames()
    if isinstance(idx, int) and 0 <= idx < len(names):
        return names[idx]
    if isinstance(idx, str) and idx in names:
        return idx
    return ""


def getDefaultThemeName():
    names = getThemeNames()
    return names[0] if names else "Catppuccin Macchiato"


def getDefaultTheme():
    return 0


# ------------------------------------------------------------------------------------------------------------


class Theme(object):
    # enum PortType
    THEME_PORT_SQUARE = 0
    THEME_PORT_POLYGON = 1
    THEME_PORT_SOCKET = 2

    # enum BackgroundType
    THEME_BG_SOLID = 0
    THEME_BG_GRADIENT = 1

    # Backwards-compat numeric theme name constants
    THEME_MODERN_DARK          = 0
    THEME_MODERN_DARK_TINY     = 1
    THEME_MODERN_LIGHT         = 2
    THEME_CLASSIC_DARK         = 3
    THEME_OOSTUDIO             = 4
    THEME_BLENDER_DARK         = 5
    THEME_CATPPUCCIN_MACCHIATO = 6
    THEME_CATPPUCCIN_MOCHA     = 7
    THEME_CATPPUCCIN_FRAPPE    = 8
    THEME_CATPPUCCIN_LATTE     = 9

    THEME_MAX = 10

    def __init__(self, idx):
        object.__init__(self)
        self.idx = idx

        themes_dict = load_themes_data()
        theme_name = getThemeName(idx) if isinstance(idx, int) else str(idx)

        theme_raw = themes_dict.get(theme_name)
        if not theme_raw:
            default_name = getDefaultThemeName()
            theme_raw = themes_dict.get(default_name, {})

        try:
            from styles.theme_manager import theme_manager, find_closest_system_color
            from qt_compat import QApplication, QPalette

            active_tokens = theme_manager.engine.active_tokens
            if active_tokens and not theme_manager.is_using_system():
                # The canvas follows the app theme: every colour comes from the
                # resolved tokens, so all Catppuccin canvas themes look the same
                # apart from structure (fonts, port mode, header size).
                t = active_tokens
                background = t.get("bg-primary", "#1e1e2e")
                surface = t.get("bg-surface", background)
                text = t.get("text-primary", "#cdd6f4")
                accent = t.get("accent", "#89b4fa")
                line = t.get("border-dim", surface)
                adapted_raw = dict(theme_raw)
                adapted_raw.update({
                    "canvas_bg": background,
                    "box_bg_1": surface,
                    "box_bg_2": surface,
                    "box_text": text,
                    "box_text_sel": accent,
                    "port_text": text,
                    "port_text_sel": accent,
                    "box_pen_color": line,
                    "box_pen_sel_color": accent,
                    "box_shadow": _with_alpha(background, 0xb4),
                    "rubberband_pen_color": accent,
                    "rubberband_brush": _with_alpha(accent, 0x40),
                })
                # Port / cable colours keep their meaning across themes.
                port_tokens = {
                    "audio_jack": t.get("blue", accent),
                    "midi_jack": t.get("purple", accent),
                    "midi_alsa": t.get("green", accent),
                    "parameter": t.get("red", accent),
                }
                glow_tokens = {
                    "audio_jack": t.get("cyan", accent),
                    "midi_jack": t.get("pink", t.get("magenta", accent)),
                    "midi_alsa": t.get("teal", t.get("green", accent)),
                    "parameter": t.get("orange", accent),
                }
                for ptype, colour in port_tokens.items():
                    adapted_raw["port_%s_bg" % ptype] = colour
                    adapted_raw["port_%s_bg_sel" % ptype] = accent
                    adapted_raw["port_%s_pen_color" % ptype] = line
                    adapted_raw["port_%s_pen_sel_color" % ptype] = accent
                    adapted_raw["port_%s_text" % ptype] = text
                    adapted_raw["port_%s_text_sel" % ptype] = accent
                    adapted_raw["line_%s" % ptype] = colour
                    adapted_raw["line_%s_sel" % ptype] = accent
                    adapted_raw["line_%s_glow" % ptype] = glow_tokens[ptype]
                # Keep titles readable on whatever surface the theme provides.
                adapted_raw["box_text"] = adjust_text_for_contrast(text, surface, 4.5)
                adapted_raw["port_text"] = adjust_text_for_contrast(text, surface, 4.5)
                theme_raw = adapted_raw
            elif theme_manager.is_using_system():
                app = QApplication.instance()
                pal = app.palette() if app else None
                if pal:
                    adapted_raw = {}
                    for k, v in theme_raw.items():
                        if k == "canvas_bg":
                            adapted_raw[k] = pal.color(QPalette.Base).name()
                        elif k in ("box_bg_1", "box_bg_2"):
                            adapted_raw[k] = pal.color(QPalette.Window).name()
                        elif k == "box_text":
                            adapted_raw[k] = pal.color(QPalette.WindowText).name()
                        elif k == "box_text_sel":
                            adapted_raw[k] = pal.color(QPalette.HighlightedText).name()
                        elif k == "port_text":
                            adapted_raw[k] = pal.color(QPalette.Text).name()
                        elif k == "port_text_sel":
                            adapted_raw[k] = pal.color(QPalette.HighlightedText).name()
                        elif k == "box_pen_sel_color":
                            adapted_raw[k] = pal.color(QPalette.Highlight).name()
                        elif k == "rubberband_brush":
                            c = pal.color(QPalette.Highlight)
                            adapted_raw[k] = f"#{c.red():02x}{c.green():02x}{c.blue():02x}40"
                        elif isinstance(v, str) and (v.startswith("#") or v.startswith("rgb")):
                            adapted_raw[k] = find_closest_system_color(v, pal, threshold=0.75).name()
                        else:
                            adapted_raw[k] = v
                    theme_raw = adapted_raw
        except Exception as e:
            print(f"[THEME] Warning adapting canvas theme: {e}")

        theme_data = parse_theme_dict(theme_raw)
        for key, value in theme_data.items():
            setattr(self, key, value)

        # Ready-to-use colours for canvas items that paint themselves, all derived
        # from the same parsed theme (and therefore from the app tokens).
        text_pen = theme_data.get("box_text")
        self.color_text = text_pen.color() if isinstance(text_pen, QPen) else QColor("#cdd6f4")
        accent_pen = theme_data.get("box_pen_sel")
        self.color_accent = (accent_pen.color() if isinstance(accent_pen, QPen)
                             else QColor("#89b4fa"))
        self.color_surface = parse_color(theme_data.get("box_bg_1", "#181825"))
        self.color_canvas = parse_color(theme_data.get("canvas_bg", "#11111b"))
        self.color_muted = QColor(self.color_text)
        self.color_muted.setAlpha(160)
        self.color_danger = parse_color(theme_data.get("port_parameter_bg", "#f38ba8"))
        self.color_ok = parse_color(theme_data.get("port_midi_alsa_bg", "#a6e3a1"))
        self.color_info = parse_color(theme_data.get("line_audio_jack_glow", "#94e2d5"))

    def _get_themes_data(self):
        themes_dict = load_themes_data()
        names = getThemeNames()
        result = {}
        for i, name in enumerate(names):
            if name in themes_dict:
                result[i] = parse_theme_dict(themes_dict[name])
        return result
