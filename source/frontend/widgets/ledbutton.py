#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2011-2024 Filipe Coelho <falktx@falktx.com>
# SPDX-License-Identifier: GPL-2.0-or-later

# ---------------------------------------------------------------------------------------------------------------------
# Imports (Global)

from qt_compat import (
    QRectF,
    QColor,
    QPainter,
    QPen,
    QPixmap,
    QSize,
    QSvgWidget,
    QPushButton,
    Qt,
)

# ---------------------------------------------------------------------------------------------------------------------
# Widget Class

class LEDButton(QPushButton):
    # Natural size of the LED tile drawn in minimal mode; layouts read this
    # through sizeHint()/minimumSizeHint() instead of being pinned from outside.
    MINIMAL_LED_SIZE = 14

    # unset
    UNSET  = -1
    # normal
    OFF    = 0
    BLUE   = 1
    GREEN  = 2
    RED    = 3
    YELLOW = 4
    # extra
    CALF   = 5

    def __init__(self, parent):
        QPushButton.__init__(self, parent)

        self.fLastColor = self.UNSET
        self.fColor     = self.UNSET

        self.fImage = QSvgWidget(self)
        self.fImage.load(":/scalable/led_off.svg")
        # paintEvent() renders the image itself; the child widget must never paint on top
        self.fImage.hide()
        self.fRect = QRectF(self.fImage.rect())

        self.setCheckable(True)
        self.setText("")
        # Opt out of the global QPushButton chrome (min-height/padding/border):
        # this widget paints its own LED tile.
        self.setProperty("ledTile", True)

        self.fCustomSize = False
        self.fMinimalMode = False

        self.setColor(self.BLUE)

    def setMinimalMode(self, enabled):
        self.fMinimalMode = bool(enabled)
        self.updateGeometry()
        self.update()

    def sizeHint(self):
        if self.fMinimalMode:
            return QSize(self.MINIMAL_LED_SIZE, self.MINIMAL_LED_SIZE)
        return super().sizeHint()

    def minimumSizeHint(self):
        if self.fMinimalMode:
            return QSize(self.MINIMAL_LED_SIZE, self.MINIMAL_LED_SIZE)
        return super().minimumSizeHint()

    def setFixedSize(self, *args):
        self.fCustomSize = True
        super().setFixedSize(*args)

    def setColor(self, color):
        self.fColor = color

        if color == self.CALF:
            self.fLastColor = self.UNSET

        if self._loadImageNowIfNeeded():
            self.fRect = QRectF(self.fImage.rect())
            if not getattr(self, 'fCustomSize', False) and not self.fMinimalMode:
                super().setFixedSize(self.fImage.size())

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, True)
        event.accept()

        if getattr(self, 'fMinimalMode', False):
            self._paintMinimalLed(painter)
            return

        self._loadImageNowIfNeeded()

        target_rect = QRectF(self.rect())
        if isinstance(self.fImage, QPixmap):
            painter.drawPixmap(target_rect.toRect(), self.fImage)
        else:
            self.fImage.renderer().render(painter, target_rect)

    def _paintMinimalLed(self, painter):
        w = float(self.width())
        h = float(self.height())
        size = min(w, h)
        if size <= 1.0:
            return

        cx = w / 2.0
        cy = h / 2.0
        tile_size = size - 1.0
        tile_rect = QRectF(cx - tile_size / 2.0, cy - tile_size / 2.0, tile_size, tile_size)

        is_on = self.isChecked()

        # Resolve theme colors for signal types
        # Control (Yellow), MIDI (Red/Coral), Audio In (Green), Audio Out (Cyan/Blue)
        color_map = {
            self.YELLOW: (QColor(249, 226, 175), QColor(250, 204, 21, 80)),   # Amber / Gold
            self.RED:    (QColor(243, 139, 168), QColor(248, 113, 113, 80)),  # Coral / Red
            self.GREEN:  (QColor(166, 227, 161), QColor(74, 222, 128, 80)),   # Emerald / Green
            self.BLUE:   (QColor(137, 220, 235), QColor(56, 189, 248, 80)),   # Sky / Cyan
            self.CALF:   (QColor(166, 227, 161), QColor(74, 222, 128, 80)),
        }
        solid_col, glow_col = color_map.get(self.fColor, (QColor(137, 220, 235), QColor(56, 189, 248, 80)))

        if is_on:
            # Active square pixel tile with crisp 1px bevel
            painter.setPen(Qt.NoPen)
            painter.setBrush(solid_col)
            painter.drawRoundedRect(tile_rect, 1.2, 1.2)

            # High-intensity top specular edge
            spec_rect = QRectF(tile_rect.x(), tile_rect.y(), tile_rect.width(), 1.0)
            painter.setBrush(QColor(255, 255, 255, 140))
            painter.drawRoundedRect(spec_rect, 0.5, 0.5)
        else:
            # Clean dark inactive state: recessed square tile with subtle bezel
            bg_col = QColor(255, 255, 255, 14)
            border_col = QColor(255, 255, 255, 25)
            painter.setBrush(bg_col)
            painter.setPen(QPen(border_col, 0.75))
            painter.drawRoundedRect(tile_rect, 1.2, 1.2)

            # Subtle dormant diode tint
            dormant_col = QColor(solid_col.red(), solid_col.green(), solid_col.blue(), 25)
            painter.setPen(Qt.NoPen)
            painter.setBrush(dormant_col)
            inner_rect = QRectF(tile_rect.x() + 1.5, tile_rect.y() + 1.5, tile_rect.width() - 3.0, tile_rect.height() - 3.0)
            painter.drawRoundedRect(inner_rect, 0.8, 0.8)

    def _loadImageNowIfNeeded(self):
        if self.isChecked():
            if self.fLastColor == self.fColor:
                return False
            if self.fColor == self.OFF:
                img = ":/scalable/led_off.svg"
            elif self.fColor == self.BLUE:
                img = ":/scalable/led_blue.svg"
            elif self.fColor == self.GREEN:
                img = ":/scalable/led_green.svg"
            elif self.fColor == self.RED:
                img = ":/scalable/led_red.svg"
            elif self.fColor == self.YELLOW:
                img = ":/scalable/led_yellow.svg"
            elif self.fColor == self.CALF:
                img = ":/bitmaps/led_calf_on.png"
            else:
                return False
            self.fLastColor = self.fColor

        elif self.fLastColor != self.OFF:
            img = ":/bitmaps/led_calf_off.png" if self.fColor == self.CALF else ":/scalable/led_off.svg"
            self.fLastColor = self.OFF

        else:
            return False

        if img.endswith(".png"):
            if not isinstance(self.fImage, QPixmap):
                self.fImage = QPixmap()
        else:
            if not isinstance(self.fImage, QSvgWidget):
                self.fImage = QSvgWidget(self)

        self.fImage.load(img)
        self.update()

        return True

# ---------------------------------------------------------------------------------------------------------------------
