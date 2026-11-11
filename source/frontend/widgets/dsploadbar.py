#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Clara contributors
# SPDX-License-Identifier: GPL-2.0-or-later

"""DSP load bar with a sparkline history.

Paints a rounded bar with the load history as a filled sparkline, the current
value as a marker, and centered text - all from theme palette roles so every
theme renders correctly without literals.
"""

from collections import deque

from qt_compat import (
    QPalette,
    QPainter,
    QColor,
    QLinearGradient,
    QProgressBar,
    QRectF,
    Qt,
)


class DspLoadBar(QProgressBar):
    """Drop-in replacement for the status bar DSP progress bar.

    Keeps the QProgressBar API (setValue/maximum) but paints a sparkline of
    recent load values instead of a flat chunk.
    """

    def __init__(self, parent=None, history=120):
        QProgressBar.__init__(self, parent)
        self._history = deque(maxlen=history)
        self._value = 0
        self.setTextVisible(False)
        self.setMinimumHeight(14)

    def push(self, value):
        """Record one load sample (0-100) and repaint."""
        try:
            value = max(0.0, min(100.0, float(value)))
        except (TypeError, ValueError):
            return
        self._value = value
        self._history.append(value)
        self.setValue(int(value))
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, True)
        pal = self.palette()
        bg = pal.color(QPalette.ColorRole.Base if hasattr(QPalette, "ColorRole") else QPalette.Base)
        border = pal.color(QPalette.ColorRole.Mid if hasattr(QPalette, "ColorRole") else QPalette.Mid)
        accent = pal.color(QPalette.ColorRole.Highlight if hasattr(QPalette, "ColorRole") else QPalette.Highlight)
        text = pal.color(QPalette.ColorRole.WindowText if hasattr(QPalette, "ColorRole") else QPalette.WindowText)

        w, h = self.width(), self.height()
        rect = QRectF(0.5, 0.5, w - 1.0, h - 1.0)
        painter.setPen(QColor(border))
        painter.setBrush(bg)
        painter.drawRoundedRect(rect, 3, 3)

        clip = QRectF(2, 2, w - 4, h - 4)
        painter.setClipRect(clip)

        hist = list(self._history)
        if hist:
            n = len(hist)
            step = max(1.0, (w - 4.0) / max(1, self.maximum() and self._history.maxlen or history_len(self)))
            # x axis: newest at the right edge, older values to the left
            points = []
            for i, v in enumerate(hist):
                x = clip.right() - (len(hist) - 1 - i) * 2.0
                if x < clip.left():
                    continue
                y = clip.bottom() - (clip.height() - 3) * (v / 100.0) - 1
                points.append((x, y))
            if points:
                # filled area under the sparkline
                from qt_compat import QPainterPath
                path = QPainterPath()
                path.moveTo(points[0][0], clip.bottom())
                for x, y in points:
                    path.lineTo(x, y)
                path.lineTo(points[-1][0], clip.bottom())
                path.closeSubpath()
                grad = QLinearGradient(0, clip.top(), 0, clip.bottom())
                top = QColor(accent)
                top.setAlpha(110)
                bottom = QColor(accent)
                bottom.setAlpha(20)
                grad.setColorAt(0.0, top)
                grad.setColorAt(1.0, bottom)
                painter.setPen(Qt.NoPen)
                painter.setBrush(grad)
                painter.drawPath(path)

                # sparkline stroke
                painter.setBrush(Qt.NoBrush)
                stroke = QColor(accent)
                painter.setPen(stroke)
                for i in range(1, len(points)):
                    painter.drawLine(int(points[i - 1][0]), int(points[i - 1][1]),
                                     int(points[i][0]), int(points[i][1]))

        painter.setClipping(False)
        painter.setPen(text)
        painter.setFont(self.font())
        painter.drawText(self.rect(), Qt.AlignCenter, "DSP Load: %d%%" % int(self._value))
        painter.end()


def history_len(widget):
    try:
        return widget._history.maxlen
    except Exception:
        return 1
