#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2011-2024 Filipe Coelho <falktx@falktx.com>
# SPDX-License-Identifier: GPL-2.0-or-later

# ------------------------------------------------------------------------------------------------------------
# Imports (Global)

from qt_compat import QColor, QGraphicsDropShadowEffect

# ------------------------------------------------------------------------------------------------------------
# Imports (Custom)

from . import canvas

# ------------------------------------------------------------------------------------------------------------

class CanvasBoxShadow(QGraphicsDropShadowEffect):
    def __init__(self, parent):
        QGraphicsDropShadowEffect.__init__(self, parent)

        self.m_fakeParent = None

        self.setBlurRadius(14)
        self.setColor(canvas.theme.box_shadow)
        self.setOffset(0, 3)

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
