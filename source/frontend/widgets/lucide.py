#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Clara contributors
# SPDX-License-Identifier: GPL-2.0-or-later

# Lucide icon loader. Icons are vendored in resources/lucide (ISC license,
# see LICENSE in that folder) and drawn as stroke="currentColor", so the SVG
# is recolored at load time to match the active theme palette.

import os

from qt_compat import (
    QIcon,
    QPainter,
    QPixmap,
    QSvgRenderer,
    QColor,
    QSize,
    QRectF,
    Qt,
)

try:
    from carla_shared import get_active_skin_palette
except ImportError:  # noqa: F401 - standalone/resource contexts
    get_active_skin_palette = None

LUCIDE_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "resources", "lucide")

# FreeDesktop theme names used by the legacy getIcon() helper, mapped to the
# Lucide icon that replaces them everywhere in the app.
THEME_ICON_MAP = {
    "application-exit": "log-out",
    "configure": "settings",
    "dialog-cancel": "x",
    "dialog-warning": "triangle-alert",
    "document-new": "file-plus",
    "document-open": "folder-open",
    "document-save": "save",
    "document-save-as": "save-all",
    "edit-clear": "eraser",
    "edit-delete": "trash-2",
    "edit-rename": "pencil",
    "list-add": "plus",
    "list-remove": "minus",
    "media-playback-pause": "pause",
    "media-playback-start": "play",
    "media-playback-stop": "square",
    "media-seek-backward": "skip-back",
    "media-seek-forward": "skip-forward",
    "network-connect": "cable",
    "view-refresh": "refresh-cw",
    "view-sort-ascending": "arrow-up-wide-narrow",
    "zoom-fit-best": "maximize-2",
    "zoom-in": "zoom-in",
    "zoom-original": "maximize",
    "zoom-out": "zoom-out",
}

_icon_cache = {}


def _svg_bytes(name, color):
    path = os.path.join(LUCIDE_DIR, "%s.svg" % name)
    if not os.path.isfile(path):
        return None
    with open(path, "r", encoding="utf-8") as f:
        data = f.read()
    # Lucide draws with stroke="currentColor"; bind it to the requested color.
    data = data.replace("currentColor", color)
    return data.encode("utf-8")


def lucide_icon(name, size=24, color=None):
    """QIcon for a vendored Lucide SVG, recolored to the given hex color.

    Falls back to None when the icon file is missing, so callers can keep
    their previous behavior. Without an explicit color the icon follows the
    application palette's WindowText role (which the theme engine sets).
    """
    if color is None:
        color = None
        try:
            from qt_compat import QApplication, QPalette
            app = QApplication.instance()
            if app is not None:
                color = app.palette().color(
                    QPalette.ColorRole.WindowText if hasattr(QPalette, "ColorRole") else QPalette.WindowText
                ).name()
        except Exception:
            pass
        if color is None:
            color = "#dddddd"

    key = (name, int(size), color)
    cached = _icon_cache.get(key)
    if cached is not None:
        return cached

    data = _svg_bytes(name, color)
    if data is None:
        return None

    renderer = QSvgRenderer(data)
    if not renderer.isValid():
        return None

    icon = QIcon()
    for scale in (1.0, 2.0):
        px = int(size * scale)
        pixmap = QPixmap(px, px)
        pixmap.fill(Qt.transparent)
        painter = QPainter(pixmap)
        renderer.render(painter, QRectF(0, 0, px, px))
        painter.end()
        icon.addPixmap(pixmap, QIcon.Mode.Normal, QIcon.State.Off)

    # Disabled mode: same shape, faint fill (Qt greys it down automatically).
    data_dim = _svg_bytes(name, color)
    _icon_cache[key] = icon
    return icon


def theme_icon(theme_name, size=16, color=None):
    """getIcon() replacement: Lucide icon for a legacy theme icon name."""
    lucide_name = THEME_ICON_MAP.get(theme_name)
    if lucide_name is None:
        return None
    return lucide_icon(lucide_name, size, color)


def bind_icon(button, name, size=16, color=None, checked_color=None):
    """Attach a Lucide icon to a button, following its check state.

    Missing SVG files are a no-op: the button keeps whatever text/icon it
    already has (important when the vendored icons are not fetched). Rebinding
    a button updates the icon name; the toggle hook is connected once.
    """
    button._lucide_name = name
    button._lucide_color = color
    button._lucide_checked_color = checked_color
    button._lucide_size = size

    if not getattr(button, "_lucide_bound", False):
        def refresh():
            active = button._lucide_color
            if button._lucide_checked_color is not None and button.isChecked():
                active = button._lucide_checked_color
            icon = lucide_icon(button._lucide_name, button._lucide_size, active)
            if icon is not None:
                button.setIcon(icon)
                button.setText("")
        button._lucide_refresh = refresh
        button.toggled.connect(lambda _checked: refresh())
        button._lucide_bound = True

    button._lucide_refresh()


def lucide_pixmap(name, size=24, color=None):
    """Convenience QPixmap variant (same recoloring rules as lucide_icon)."""
    icon = lucide_icon(name, size, color)
    if icon is None:
        return None
    return icon.pixmap(QSize(int(size), int(size)))


def lucide_paint(painter, rect, name, color):
    """Paint a vendored Lucide icon directly with a painter (canvas use).

    color: QColor or any string Qt accepts. Returns False when the icon file
    is missing, so callers can fall back to their previous rendering.
    """
    col = color.name() if hasattr(color, "name") else color
    data = _svg_bytes(name, col)
    if data is None:
        return False
    renderer = QSvgRenderer(data)
    if not renderer.isValid():
        return False
    renderer.render(painter, rect)
    return True
