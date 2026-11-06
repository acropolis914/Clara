#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2011-2025 Filipe Coelho <falktx@falktx.com>
# SPDX-License-Identifier: GPL-2.0-or-later

# ------------------------------------------------------------------------------------------------------------
# Imports (Global)
# ------------------------------------------------------------------------------------------------------------
import re

# ------------------------------------------------------------------------------------------------------------
# Imports (Custom)
# ------------------------------------------------------------------------------------------------------------

from carla_backend import *
from carla_shared import *
from carla_widgets import *
from patchcanvas import patchcanvas

# ------------------------------------------------------------------------------------------------------------
# Imports (PyQt)
# ------------------------------------------------------------------------------------------------------------
from qt_compat import (
    QAction,
    QApplication,
    QColor,
    QColorDialog,
    QCursor,
    QEvent,
    QFont,
    QFontDatabase,
    QFrame,
    QHBoxLayout,
    QIcon,
    QImage,
    QLabel,
    QLineEdit,
    QMenu,
    QMouseEvent,
    QObject,
    QPainter,
    QPainterPathStroker,
    QPixmap,
    QPoint,
    QPointF,
    QPushButton,
    QRect,
    QStyle,
    QStyleOptionButton,
    Qt,
    QTimer,
    QVBoxLayout,
    QWidget,
)

# ------------------------------------------------------------------------------------------------------------
# Stereo Autowiring and Disconnect Helpers
# ------------------------------------------------------------------------------------------------------------


def _get_event_global_pos(event):
    if hasattr(event, "globalPosition"):
        return event.globalPosition().toPoint()
    return event.globalPos()


# ------------------------------------------------------------------------------------------------------------
# Floating Photoshop-style Modal Toolbar (Left Vertical Palette)
# ------------------------------------------------------------------------------------------------------------

from carla_shared import getBestNerdFont

_GLYPH_OFFSET_CACHE = {}


def get_glyph_visual_offset(glyph, font, size):
    """Calculate the precise (dx, dy) pixel shift required to visually center a glyph."""
    if not glyph:
        return (0, 0)
    family = font.family() if hasattr(font, "family") else ""
    pt_size = font.pointSize() if hasattr(font, "pointSize") else 0
    key = (glyph, family, pt_size, size)
    if key in _GLYPH_OFFSET_CACHE:
        return _GLYPH_OFFSET_CACHE[key]

    W, H = size, size
    img = QImage(W, H, QImage.Format_ARGB32)
    img.fill(0)
    p = QPainter(img)
    p.setFont(font)
    p.setPen(QColor(255, 255, 255))
    p.drawText(QRect(0, 0, W, H), Qt.AlignCenter, glyph)
    p.end()

    min_x, max_x = W, -1
    min_y, max_y = H, -1
    for y in range(H):
        for x in range(W):
            if (img.pixel(x, y) >> 24) & 0xFF > 20:
                if x < min_x:
                    min_x = x
                if x > max_x:
                    max_x = x
                if y < min_y:
                    min_y = y
                if y > max_y:
                    max_y = y

    if max_x == -1:
        offset = (0, 0)
    else:
        cx = (min_x + max_x) / 2.0
        cy = (min_y + max_y) / 2.0
        offset = (int(round((W - 1) / 2.0 - cx)), int(round((H - 1) / 2.0 - cy)))

    _GLYPH_OFFSET_CACHE[key] = offset
    return offset


def _canvas_locked():
    gui = getattr(gCarla, "gui", None)
    return bool(gui is not None and getattr(gui, "fIsProjectLoading", False))
