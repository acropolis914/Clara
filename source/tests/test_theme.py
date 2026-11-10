#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Clara contributors
# SPDX-License-Identifier: GPL-2.0-or-later

# The global QSS must not carry colors. Theme switches map tokens onto Qt
# palette roles, so a color literal here bypasses the theme engine.

import os
import re
import sys

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "frontend"))

_PRIMITIVES = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "frontend", "styles", "base_primitives.qss")


def test_qss_has_no_color_literals():
    with open(_PRIMITIVES, "r", encoding="utf-8") as f:
        qss = f.read()
    assert not re.search(r"#[0-9a-fA-F]{3,8}\b", qss), "hardcoded hex color in base_primitives.qss"
    assert not re.search(r"rgba?\(", qss), "hardcoded rgb color in base_primitives.qss"


def test_qss_uses_palette_roles():
    with open(_PRIMITIVES, "r", encoding="utf-8") as f:
        qss = f.read()
    for role in ("palette(window)", "palette(base)", "palette(highlight)", "palette(mid)"):
        assert role in qss, f"missing {role}"


_FRONTEND = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "frontend")

# Widget code may only carry a colour literal as a fallback next to a token
# lookup, never as the value it actually uses.
_TOKEN_CALL = (
    "get_token(",
    "_token(",
    "_themeColor(",
    "_themeRgba(",
    "find_closest_system_color(",
    "t.get(",
)

# Files whose colours are their own content, not chrome:
# - canvas_context_toolbar: user-facing colour swatches
# - digitalpeakmeter: LED level colours
# - scalabledial: knob plate
# - patchcanvas: separate canvas theme system (themes.json)
_ALLOWLIST = (
    "canvas_context_toolbar.py",
    "widgets/digitalpeakmeter.py",
    "widgets/scalabledial.py",
    "carla_settings.py",
    "ladspa_rdf.py",
    "widgets/commondial.py",
    "resources_rc.py",
    "patchcanvas/",
)

# A named palette definition, e.g. CATPPUCCIN_MOCHA's entries.
_PALETTE_ENTRY = re.compile(r"^\s*'[a-z0-9]+':\s*'#[0-9a-fA-F]{3,8}',\s*$")
# A literal rgba(1, 2, 3, ...) color, as opposed to the "%d" format placeholders
# that _themeRgba() and friends build.
_LITERAL_RGB = re.compile(r"rgba?\(\s*\d+\s*,\s*\d+\s*,\s*\d+")


def test_widget_code_has_no_bare_color_literals():
    offenders = []
    for dirpath, _dirs, files in os.walk(_FRONTEND):
        for name in files:
            if not name.endswith(".py") or name.startswith("ui_"):
                continue
            path = os.path.join(dirpath, name)
            rel = os.path.relpath(path, _FRONTEND).replace(os.sep, "/")
            if rel.startswith("styles/") or rel.startswith(_ALLOWLIST):
                continue
            with open(path, "r", encoding="utf-8", errors="replace") as f:
                for lineno, line in enumerate(f, 1):
                    if not (re.search(r"#[0-9a-fA-F]{3,8}\b", line)
                            or _LITERAL_RGB.search(line)):
                        continue
                    if "noqa: theme-color" in line or _PALETTE_ENTRY.match(line):
                        continue
                    if any(call in line for call in _TOKEN_CALL):
                        continue
                    offenders.append(f"{rel}:{lineno}: {line.strip()}")
    assert not offenders, "colour literal outside the theme engine:\n" + "\n".join(offenders)


def test_theme_text_contrasts_with_background():
    from qt_compat import QColor
    from styles.engine import ThemeEngine
    from styles.registry import registry

    for name in ("Catppuccin Mocha", "Catppuccin Macchiato", "Clara Light"):
        theme = registry.get_theme(name)
        tokens = ThemeEngine().resolve_tokens(theme, mode=theme.get("mode", "dark"))
        text = QColor(tokens["text-primary"])
        background = QColor(tokens["bg-primary"])
        assert abs(text.lightness() - background.lightness()) > 80, (
            f"{name} text-primary and bg-primary have no contrast")


def test_unknown_theme_falls_back():
    from styles.theme_manager import theme_manager

    assert theme_manager.resolve_theme_name("Catppuccin Latte") == "Catppuccin Macchiato"
    assert theme_manager.resolve_theme_name("catppuccin mocha") == "Catppuccin Mocha"
    assert theme_manager.resolve_theme_name("") == "Catppuccin Macchiato"


def test_bundled_themes_load():
    from styles.registry import registry

    names = registry.list_theme_names()
    assert "Clara Light" in names, "missing light theme"
    assert "Catppuccin Latte" not in names, "Latte should be gone"
    assert registry.get_theme("Clara Light")["mode"] == "light"


def test_palette_maps_theme_tokens():
    from qt_compat import QPalette
    from styles.engine import ThemeEngine
    from styles.registry import registry
    from styles.theme_manager import build_palette

    tokens = ThemeEngine().resolve_tokens(registry.get_theme("Catppuccin Macchiato", mode="dark"), mode="dark")
    tokens.update({
        "bg-primary": "#101010",
        "bg-surface": "#202020",
        "bg-hover": "#303030",
        "text-primary": "#f0f0f0",
        "text-muted": "#808080",
        "border-dim": "#404040",
        "accent": "#00ff00",
    })
    pal = build_palette(tokens)
    assert pal.color(QPalette.Window).name() == "#101010"
    assert pal.color(QPalette.Base).name() == "#202020"
    assert pal.color(QPalette.Highlight).name() == "#00ff00"
    assert pal.color(QPalette.Mid).name() == "#404040"


if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
    print("theme: all checks passed")
