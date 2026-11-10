#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2011-2025 Filipe Coelho <falktx@falktx.com>
# SPDX-License-Identifier: GPL-2.0-or-later

# ------------------------------------------------------------------------------------------------------------
# Imports (Global)

from qt_compat import QColor, QGraphicsDropShadowEffect

# ------------------------------------------------------------------------------------------------------------
# Imports (Custom)

from . import canvas

# ------------------------------------------------------------------------------------------------------------

# Qt renders the shadow blur in device pixels, so the radius has to follow the
# view scale or the shadow looks huge when zoomed out and tiny when zoomed in.
SHADOW_BLUR = 14.0
SHADOW_OFFSET_Y = 3.0


def updateShadowScale(scale=None):
    """Keep every node/container shadow proportional to the view zoom."""
    if canvas.scene is None:
        return
    if scale is None:
        scale = canvas.scene.getScaleFactor()
    scale = max(0.1, min(4.0, float(scale)))
    for group in getattr(canvas, "group_list", []):
        for widget in getattr(group, "widgets", []):
            effect = widget.graphicsEffect() if widget is not None else None
            if isinstance(effect, CanvasBoxShadow):
                effect.setScale(scale)
    from . import CanvasContainerType
    for item in canvas.scene.items():
        if item.type() == CanvasContainerType:
            effect = item.graphicsEffect()
            if isinstance(effect, CanvasBoxShadow):
                effect.setScale(scale)


class CanvasBoxShadow(QGraphicsDropShadowEffect):
    def __init__(self, parent):
        QGraphicsDropShadowEffect.__init__(self, parent)

        self.m_fakeParent = None

        self.setColor(canvas.theme.box_shadow)
        self.setScale(canvas.scene.getScaleFactor() if canvas.scene is not None else 1.0)

    def setScale(self, scale):
        # Cap the radius: blur cost grows with its size and deep zoom already
        # makes nodes huge.
        self.setBlurRadius(min(max(1.0, SHADOW_BLUR * scale), SHADOW_BLUR * 2.5))
        self.setOffset(0, SHADOW_OFFSET_Y * scale)

    def setFakeParent(self, fakeParent):
        self.m_fakeParent = fakeParent

    def setOpacity(self, opacity):
        color = QColor(canvas.theme.box_shadow)
        color.setAlphaF(opacity)
        self.setColor(color)

    def draw(self, painter):
        # NOTE: repaintLines() intentionally removed from here.
        # Previously this caused updateLinePos() to be called on every shadow
        # paint event, cascading into expensive line updates for every box on
        # each frame with many connections. Lines are already updated in
        # CanvasBox.mouseMoveEvent() and repaintLines(forced=True) where needed.
        #
        # While a box is being dragged the blur is recomputed every frame for
        # every moved box, which is the main source of drag lag. Skip the blur
        # and paint the source directly for a smooth drag.
        if getattr(canvas, "dragging", False):
            self.drawSource(painter)
            return
        QGraphicsDropShadowEffect.draw(self, painter)

# ------------------------------------------------------------------------------------------------------------
