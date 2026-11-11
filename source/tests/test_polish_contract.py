#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Clara contributors
# SPDX-License-Identifier: GPL-2.0-or-later

"""Polish contract test: the active theme QSS must never override the sizes
the code requests for its custom widgets.

This is the regression class that kept resurfacing: global QPushButton /
QLineEdit rules (min-height, padding) re-derive widget minimums at polish
time, so `setFixedSize(24, 24)` silently renders as 24x30 and icons clip in
their containers. The contract: after polish, every pinned widget is exactly
the size its code requested, and no widget has minimum > maximum.
"""

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
FRONTEND = os.path.join(HERE, "..", "frontend")
sys.path.insert(0, FRONTEND)

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

try:
    from PyQt6.QtWidgets import QApplication
except ImportError:
    try:
        from PyQt5.QtWidgets import QApplication
    except ImportError:
        QApplication = None

if QApplication is None:  # pragma: no cover - CI without Qt
    print("polish_contract: skipped (no Qt)")
    sys.exit(0)

app = QApplication.instance() or QApplication(sys.argv)

from styles.theme_manager import theme_manager  # noqa: E402

theme_manager.apply_theme()

failures = []


def check(widget, requested, label):
    """Assert a polished widget is exactly the requested size and consistent."""
    widget.ensurePolished()
    w, h = widget.width(), widget.height()
    minw, minh = widget.minimumSize().width(), widget.minimumSize().height()
    maxw, maxh = widget.maximumSize().width(), widget.maximumSize().height()
    if (w, h) != requested:
        failures.append("%s: renders %sx%s after polish, code requested %sx%s" % (
            label, w, h, requested[0], requested[1]))
    if minw > maxw or minh > maxh:
        failures.append("%s: QSS polish left minimum (%d, %d) above maximum "
                        "(%d, %d) - the global stylesheet overrode the code" % (
                            label, minw, minh, maxw, maxh))


from qt_compat import QFrame, QLineEdit, QVBoxLayout, QWidget  # noqa: E402
from canvas_toolbar import CanvasToolButton  # noqa: E402
from widgets.ledbutton import LEDButton  # noqa: E402
from widgets.scalabledial import ScalableDial  # noqa: E402


def _frame(object_name):
    frame = QFrame()
    frame.setObjectName(object_name)
    QVBoxLayout(frame)
    return frame


# Icon buttons inside the two toolbar overlays.
# QSS tile rules use the CONTENT box: 26px content + 1px border = 28px widget.
toolbar_frame = _frame("canvas_toolbar_overlay")
btn = CanvasToolButton("", toolbar_frame)
btn.setFixedSize(28, 28)
toolbar_frame.show()
check(btn, (28, 28), "canvas toolbar button")

ctx_frame = _frame("canvas_context_toolbar_overlay")
btn2 = CanvasToolButton("", ctx_frame)
btn2.setFixedSize(26, 26)
search = QLineEdit(ctx_frame)
search.setFixedHeight(24)
ctx_frame.show()
check(btn2, (26, 26), "context toolbar button")
check(search, (search.width(), 24), "context toolbar search field")

# LED tile: exempt from button chrome via the ledTile property
led = LEDButton(None)
led.setFixedSize(14, 14)
check(led, (14, 14), "LED tile")
if not led.property("ledTile"):
    failures.append("LED tile lost its ledTile QSS exemption property")

# Dial: natural size, and QSS must not push minimum above maximum
dial = ScalableDial(None)
dial.setLabel("Gain")
dial.ensurePolished()
if dial.minimumSizeHint().width() != dial.sizeHint().width() or \
        dial.minimumSizeHint().height() != dial.sizeHint().height():
    failures.append("ScalableDial: minimumSizeHint %s != sizeHint %s (pinned "
                    "or QSS-inflated)" % (dial.minimumSizeHint(), dial.sizeHint()))
if dial.width() != dial.sizeHint().width() or dial.height() < dial.sizeHint().height():
    failures.append("ScalableDial: rendered %dx%d outside its hint %s" % (
        dial.width(), dial.height(), dial.sizeHint()))

# Small color-swatch push buttons (plugin color menus) carry their own
# stylesheet; it must zero the global min-height/padding to stay 22x22.
from qt_compat import QPushButton  # noqa: E402
sw = QPushButton("")
sw.setFixedSize(22, 22)
sw.setStyleSheet(
    "QPushButton { background-color: #000000; border: 1px solid #000000;"
    " border-radius: 3px; padding: 0px; min-height: 0px; min-width: 0px; }")
check(sw, (22, 22), "color swatch button")

if failures:
    print("polish_contract: FAILED")
    for f in failures:
        print("  -", f)
    sys.exit(1)
print("polish_contract: all checks passed")
