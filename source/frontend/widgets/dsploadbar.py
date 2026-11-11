#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Clara contributors
# SPDX-License-Identifier: GPL-2.0-or-later

"""Borderless DSP load sparkline.

Stores (timestamp, load) samples, paints the configured time window as an
accent line with a soft fill and a faint baseline. The current/average text
lives outside the widget (status bar labels); no color literals - palette
roles and theme tokens only.
"""

import time
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
    """Drop-in for the old DSP progress bar; keeps the setValue API."""

    def __init__(self, parent=None, window_seconds=60):
        QProgressBar.__init__(self, parent)
        self._samples = deque()  # (t, value)
        self._window = max(10, int(window_seconds))
        self._value = 0.0
        self._last_push = 0.0
        self.setTextVisible(False)
        self.setMinimumHeight(16)
        self.setToolTip("DSP load history")

    def setWindow(self, seconds):
        self._window = max(10, int(seconds))
        self._prune()
        self.update()

    def window(self):
        return self._window

    def push(self, value, when=None):
        try:
            value = max(0.0, min(100.0, float(value)))
        except (TypeError, ValueError):
            return
        now = time.monotonic() if when is None else float(when)
        # decimate: at most ~8 samples per second
        if now - self._last_push < 0.12 and self._samples:
            self._samples[-1] = (now, value)
        else:
            self._samples.append((now, value))
        self._last_push = now
        self._value = value
        self._prune()
        self.setValue(int(value))
        self.update()

    def current(self):
        return self._value

    def average(self):
        self._prune()
        if not self._samples:
            return 0.0
        return sum(v for _t, v in self._samples) / len(self._samples)

    def stats(self):
        self._prune()
        vals = [v for _t, v in self._samples]
        avg = sum(vals) / len(vals) if vals else 0.0
        return self._value, avg, (max(vals) if vals else 0.0), self._window

    def _prune(self):
        cutoff = time.monotonic() - (self._window + 2.0)
        while self._samples and self._samples[0][0] < cutoff:
            self._samples.popleft()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, True)
        pal = self.palette()
        role_get = pal.color
        role = (QPalette.ColorRole.Highlight if hasattr(QPalette, "ColorRole")
                else QPalette.Highlight)
        accent = role_get(role)
        muted = role_get(QPalette.ColorRole.Mid if hasattr(QPalette, "ColorRole")
                         else QPalette.Mid)

        w, h = self.width(), self.height()
        clip = QRectF(0.5, 1.5, w - 1.0, h - 3.0)

        # faint baseline
        painter.setPen(QColor(muted))
        painter.drawLine(int(clip.left()), int(clip.bottom()),
                         int(clip.right()), int(clip.bottom()))

        self._prune()
        samples = [s for s in self._samples if s[0] >= time.monotonic() - self._window]
        if samples:
            t0 = samples[0][0]
            span = max(1.0, self._window)
            points = []
            for t, v in samples:
                x = clip.left() + (t - t0) / span * (clip.width() - 2.0)
                y = clip.bottom() - (clip.height() - 2.0) * (v / 100.0)
                points.append((x, y))
            if points:
                from qt_compat import QPainterPath
                path = QPainterPath()
                path.moveTo(points[0][0], clip.bottom())
                for x, y in points:
                    path.lineTo(x, y)
                last_x = points[-1][0]
                path.lineTo(last_x, clip.bottom())
                path.closeSubpath()
                grad = QLinearGradient(0, clip.top(), 0, clip.bottom())
                top = QColor(accent)
                top.setAlpha(95)
                bottom = QColor(accent)
                bottom.setAlpha(15)
                grad.setColorAt(0.0, top)
                grad.setColorAt(1.0, bottom)
                painter.setPen(Qt.NoPen)
                painter.setBrush(grad)
                painter.drawPath(path)

                painter.setBrush(Qt.NoBrush)
                pen = QColor(accent)
                painter.setPen(pen)
                for i in range(1, len(points)):
                    painter.drawLine(int(points[i - 1][0]), int(points[i - 1][1]),
                                     int(points[i][0]), int(points[i][1]))
        painter.end()
