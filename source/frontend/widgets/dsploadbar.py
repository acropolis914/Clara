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

def _token(name):
    from styles.theme_manager import theme_manager
    return theme_manager.engine.get_token(name) or "#89b4fa"


from qt_compat import (
    QPalette,
    QPointF,
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

    def _valueAt(self, index):
        """Load value for the sample at `index` in the current visible set."""
        try:
            return self._visible[index][1]
        except Exception:
            return self._value

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
        lo = min(vals) if vals else 0.0
        hi = max(vals) if vals else 0.0
        return self._value, avg, hi, self._window, lo

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

        self._prune()
        samples = [s for s in self._samples if s[0] >= time.monotonic() - self._window]
        self._visible = samples

        # autoscale: the y range follows the visible data (min..max with a
        # little headroom), floored to a 5% span so flat loads stay readable
        vals = [v for _t, v in samples] + ([self._value] if self._samples else [])
        lo = min(vals) if vals else 0.0
        hi = max(vals) if vals else 100.0
        pad = max(2.0, (hi - lo) * 0.15)
        lo = max(0.0, lo - pad)
        hi = min(100.0, hi + pad)
        if hi - lo < 5.0:
            mid = (hi + lo) / 2.0
            lo, hi = max(0.0, mid - 2.5), max(2.5, mid + 2.5)

        # semantic colors by standard deviation: points within 1 sigma of the
        # window mean are calm (green), 1-2 sigma warn (yellow), beyond 2
        # sigma are spikes (red). A flat window (std ~ 0) stays green.
        green = QColor(_token("green"))
        yellow = QColor(_token("yellow"))
        red = QColor(_token("red"))

        vals_for_stats = [v for _t, v in samples] + ([self._value] if self._samples else [])
        mean_v = sum(vals_for_stats) / len(vals_for_stats) if vals_for_stats else 0.0
        var = sum((v - mean_v) ** 2 for v in vals_for_stats) / len(vals_for_stats) if vals_for_stats else 0.0
        std_v = var ** 0.5

        def color_for(v):
            v = max(0.0, min(100.0, v))
            if std_v < 0.75:
                return green
            z = (v - mean_v) / std_v
            if z <= 0.0:
                return green
            if z < 1.0:
                t = z
                return QColor(int(green.red() + (yellow.red() - green.red()) * t),
                              int(green.green() + (yellow.green() - green.green()) * t),
                              int(green.blue() + (yellow.blue() - green.blue()) * t))
            if z < 2.0:
                t = z - 1.0
                return QColor(int(yellow.red() + (red.red() - yellow.red()) * t),
                              int(yellow.green() + (red.green() - yellow.green()) * t),
                              int(yellow.blue() + (red.blue() - yellow.blue()) * t))
            return red

        # faint baseline
        painter.setPen(QColor(muted))
        painter.drawLine(int(clip.left()), int(clip.bottom()),
                         int(clip.right()), int(clip.bottom()))

        if samples:
            t0 = samples[0][0]
            span = max(1.0, self._window)
            points = []
            for t, v in samples:
                x = clip.left() + (t - t0) / span * (clip.width() - 2.0)
                points.append((x, clip.bottom() - (clip.height() - 2.0) * ((v - lo) / (hi - lo))))
            if points:
                from qt_compat import QPainterPath
                # per-point fill: a soft trapezoid per segment in that
                # segment's semantic color (low alpha)
                painter.setPen(Qt.NoPen)
                for i in range(1, len(points)):
                    x0, y0 = points[i - 1]
                    x1, y1 = points[i]
                    v = self._valueAt(i)
                    col = QColor(color_for(v))
                    col.setAlpha(55)
                    painter.setBrush(col)
                    painter.drawPolygon([QPointF(x0, clip.bottom()),
                                         QPointF(x0, y0), QPointF(x1, y1),
                                         QPointF(x1, clip.bottom())])

                # per-point stroke: each line segment colored by its load
                painter.setBrush(Qt.NoBrush)
                for i in range(1, len(points)):
                    x0, y0 = points[i - 1]
                    x1, y1 = points[i]
                    v = self._valueAt(i)
                    painter.setPen(QColor(color_for(v)))
                    painter.drawLine(int(x0), int(y0), int(x1), int(y1))

                # current-value marker dot in its own color
                lx, ly = points[-1]
                cur_col = QColor(color_for(self._value))
                painter.setBrush(cur_col)
                painter.setPen(Qt.NoPen)
                painter.drawEllipse(QPointF(lx, ly), 2.5, 2.5)

        painter.setClipping(False)

        # min/max labels (tiny, muted, corners)
        f = painter.font()
        f.setPointSizeF(max(6.0, f.pointSizeF() - 2.0))
        painter.setFont(f)
        painter.setPen(QColor(muted))
        if samples:
            painter.drawText(QRectF(clip.left() + 2, clip.top(), 90, 12),
                             0, "max %d%%" % int(hi))
            painter.drawText(QRectF(clip.left() + 2, clip.bottom() - 11, 90, 12),
                             0, "min %d%%" % int(lo))

        painter.end()


def text_color(pal):
    role = QPalette.ColorRole.WindowText if hasattr(QPalette, "ColorRole") else QPalette.WindowText
    return pal.color(role)
