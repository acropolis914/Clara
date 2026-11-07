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
