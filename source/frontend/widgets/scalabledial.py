#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2011-2024 Filipe Coelho <falktx@falktx.com>
# SPDX-License-Identifier: GPL-2.0-or-later

# ---------------------------------------------------------------------------------------------------------------------
# Imports (Global)

from math import cos, floor, pi, sin

from qt_compat import (
    pyqtSlot,
    Qt,
    QEvent,
    QPointF,
    QRectF,
    QTimer,
    QSize,
    QColor,
    QConicalGradient,
    QFontMetrics,
    QPainterPath,
    QPen,
    QPixmap,
    QSvgWidget,
)

from .commondial import CommonDial
from carla_shared import fontMetricsHorizontalAdvance

# ---------------------------------------------------------------------------------------------------------------------
# Widget Class

class ScalableDial(CommonDial):
    def __init__(self, parent, index=0):
        CommonDial.__init__(self, parent, index)

        self.fImage = QSvgWidget(self)
        self.fImage.load(":/scalable/dial_03.svg")
        # paintDial() renders the image itself; the child widget must never paint on top
        self.fImage.hide()
        self.fImageNum = "01"

        if self.fImage.sizeHint().width() > self.fImage.sizeHint().height():
            self.fImageOrientation = self.HORIZONTAL
        else:
            self.fImageOrientation = self.VERTICAL

        self.updateSizes()

    def getBaseSize(self):
        return self.fImageBaseSize

    def setFixedSize(self, *args):
        self.fCustomSize = True
        super().setFixedSize(*args)

    def setFixedWidth(self, w):
        self.fCustomSize = True
        super().setFixedWidth(w)

    def updateSizes(self):
        if isinstance(self.fImage, QPixmap):
            self.fImageWidth  = self.fImage.width()
            self.fImageHeight = self.fImage.height()
        else:
            self.fImageWidth  = self.fImage.sizeHint().width()
            self.fImageHeight = self.fImage.sizeHint().height()

        if self.fImageWidth < 1:
            self.fImageWidth = 1

        if self.fImageHeight < 1:
            self.fImageHeight = 1

        if self.fImageOrientation == self.HORIZONTAL:
            self.fImageBaseSize    = self.fImageHeight
            self.fImageLayersCount = self.fImageWidth / self.fImageHeight
        else:
            self.fImageBaseSize    = self.fImageWidth
            self.fImageLayersCount = self.fImageHeight / self.fImageWidth

        if not self.fLabel:
            self.fLabelHeight = 0
            self.fLabelWidth  = 0
        else:
            metrics = QFontMetrics(self.fLabelFont)
            self.fLabelWidth  = fontMetricsHorizontalAdvance(metrics, self.fLabel)
            self.fLabelHeight = metrics.height()

            self.fLabelPos.setX(float(self.fImageBaseSize)/2.0 - float(self.fLabelWidth)/2.0)

            if self.fImageNum in ("01", "02", "07", "08", "09", "10"):
                self.fLabelPos.setY(self.fImageBaseSize + self.fLabelHeight)
            elif self.fImageNum in ("11",):
                self.fLabelPos.setY(self.fImageBaseSize + self.fLabelHeight*2/3)
            else:
                self.fLabelPos.setY(self.fImageBaseSize + self.fLabelHeight/2)

            self.fLabelGradient.setStart(0, float(self.fImageBaseSize)/2.0)
            self.fLabelGradient.setFinalStop(0, self.fImageBaseSize + self.fLabelHeight + 5)

            self.fLabelGradientRect = QRectF(float(self.fImageBaseSize)/8.0, float(self.fImageBaseSize)/2.0,
                                             float(self.fImageBaseSize*3)/4.0, self.fImageBaseSize+self.fLabelHeight+5)

        if getattr(self, 'fCustomSize', False):
            return

        dialWidth = max(self.fImageBaseSize, self.fLabelWidth + 8)
        # paintEvent draws the label AND a value line below it; leave room for both
        dialHeight = self.fImageBaseSize + self.fLabelHeight + 5
        if self.fLabel:
            dialHeight = max(dialHeight, int(self.fLabelPos.y() + metrics.lineSpacing() + 4))
        self.setMinimumSize(dialWidth, dialHeight)
        self.setMaximumSize(dialWidth, dialHeight)

    def setImage(self, imageId):
        self.fImageNum = "%02i" % imageId
        if imageId in (2,6,7,8,9,10,11,12,13):
            img = ":/bitmaps/dial_%s%s.png" % (self.fImageNum, "" if self.isEnabled() else "d")
        else:
            img = ":/scalable/dial_%s%s.svg" % (self.fImageNum, "" if self.isEnabled() else "d")

        if img.endswith(".png"):
            if not isinstance(self.fImage, QPixmap):
                self.fImage = QPixmap()
        else:
            if not isinstance(self.fImage, QSvgWidget):
                self.fImage = QSvgWidget(self)
                self.fImage.hide()

        self.fImage.load(img)

        if self.fImage.width() > self.fImage.height():
            self.fImageOrientation = self.HORIZONTAL
        else:
            self.fImageOrientation = self.VERTICAL

        # special svgs
        if self.fCustomPaintMode == self.CUSTOM_PAINT_MODE_NULL:
            # reserved for carla-wet, carla-vol, carla-pan and color
            if self.fImageNum == "03":
                self.fCustomPaintMode = self.CUSTOM_PAINT_MODE_COLOR

            # reserved for carla-L and carla-R
            elif self.fImageNum == "04":
                self.fCustomPaintMode = self.CUSTOM_PAINT_MODE_CARLA_L

            # reserved for zita
            elif self.fImageNum == "06":
                self.fCustomPaintMode = self.CUSTOM_PAINT_MODE_ZITA

        self.updateSizes()
        self.update()

    @pyqtSlot()
    def slot_updateImage(self):
        self.setImage(int(self.fImageNum))

    def minimumSizeHint(self):
        return QSize(self.fImageBaseSize, self.fImageBaseSize)

    def sizeHint(self):
        return QSize(self.fImageBaseSize, self.fImageBaseSize)

    def changeEvent(self, event):
        CommonDial.changeEvent(self, event)

        # Force svg update if enabled state changes
        if event.type() == QEvent.EnabledChange:
            self.slot_updateImage()

    def paintDial(self, painter):
        painter.save()
        xOffset = max(0.0, float(self.width() - self.fImageBaseSize) / 2.0)
        painter.translate(xOffset, 0.0)

        if self.isEnabled():
            normValue = float(self.fRealValue - self.fMinimum) / float(self.fMaximum - self.fMinimum)
            curLayer = int((self.fImageLayersCount - 1) * normValue)

            if self.fImageOrientation == self.HORIZONTAL:
                xpos = self.fImageBaseSize * curLayer
                ypos = 0.0
            else:
                xpos = 0.0
                ypos = self.fImageBaseSize * curLayer

            source = QRectF(xpos, ypos, self.fImageBaseSize, self.fImageBaseSize)

            if self.fCustomPaintMode == self.CUSTOM_PAINT_MODE_FLAT:
                # Draw flat background circle
                bg_color = QColor("#D0D0D0" if self.fHoverStep == 0 else "#C0C0C0")
                painter.setBrush(bg_color)
                painter.setPen(Qt.NoPen)
                painter.drawEllipse(QRectF(3.0, 3.0, 24.0, 24.0))

                # Draw indicator
                color = self.fCustomPaintColor.lighter(100 + self.fHoverStep*6)
                painter.setPen(QPen(color, 2.5, Qt.SolidLine, Qt.RoundCap))
                
                startAngle = 218 * 16
                spanAngle  = -255 * 16 * normValue
                painter.drawArc(QRectF(7.0, 7.0, 16.0, 16.0), int(startAngle), int(spanAngle))

                # draw ball point
                ballRect = QRectF(7.0, 7.0, 16.0, 16.0)
                ballPath = QPainterPath()
                ballPath.addEllipse(ballRect)
                tmpValue  = (0.375 + 0.75*normValue)
                ballValue = tmpValue - floor(tmpValue)
                ballPoint = ballPath.pointAtPercent(ballValue)
                
                painter.setBrush(color)
                painter.setPen(Qt.NoPen)
                painter.drawEllipse(QRectF(ballPoint.x()-1.5, ballPoint.y()-1.5, 3.0, 3.0))

            else:
                if isinstance(self.fImage, QPixmap):
                    target = QRectF(0.0, 0.0, self.fImageBaseSize, self.fImageBaseSize)
                    painter.drawPixmap(target, self.fImage, source)
                else:
                    self.fImage.renderer().render(painter, source)

            # Custom knobs (Dry/Wet and Volume)
            if self.fCustomPaintMode in (self.CUSTOM_PAINT_MODE_CARLA_WET, self.CUSTOM_PAINT_MODE_CARLA_VOL):
                # knob color
                colorGreen = QColor(0x5D, 0xE7, 0x3D).lighter(100 + self.fHoverStep*6)
                colorBlue  = QColor(0x3E, 0xB8, 0xBE).lighter(100 + self.fHoverStep*6)

                # draw small circle
                ballRect = QRectF(8.0, 8.0, 15.0, 15.0)
                ballPath = QPainterPath()
                ballPath.addEllipse(ballRect)
                #painter.drawRect(ballRect)
                tmpValue  = (0.375 + 0.75*normValue)
                ballValue = tmpValue - floor(tmpValue)
                ballPoint = ballPath.pointAtPercent(ballValue)

                # draw arc
                startAngle = 218*16
                spanAngle  = -255*16*normValue

                if self.fCustomPaintMode == self.CUSTOM_PAINT_MODE_CARLA_WET:
                    painter.setBrush(colorBlue)
                    painter.setPen(QPen(colorBlue, 0))
                    painter.drawEllipse(QRectF(ballPoint.x(), ballPoint.y(), 2.2, 2.2))

                    gradient = QConicalGradient(15.5, 15.5, -45)
                    gradient.setColorAt(0.0,   colorBlue)
                    gradient.setColorAt(0.125, colorBlue)
                    gradient.setColorAt(0.625, colorGreen)
                    gradient.setColorAt(0.75,  colorGreen)
                    gradient.setColorAt(0.76,  colorGreen)
                    gradient.setColorAt(1.0,   colorGreen)
                    painter.setBrush(gradient)
                    painter.setPen(QPen(gradient, 3))

                else:
                    painter.setBrush(colorBlue)
                    painter.setPen(QPen(colorBlue, 0))
                    painter.drawEllipse(QRectF(ballPoint.x(), ballPoint.y(), 2.2, 2.2))

                    painter.setBrush(colorBlue)
                    painter.setPen(QPen(colorBlue, 3))

                painter.drawArc(QRectF(4.0, 4.0, 26.0, 26.0), int(startAngle), int(spanAngle))

            # Custom knobs (L and R)
            elif self.fCustomPaintMode in (self.CUSTOM_PAINT_MODE_CARLA_L, self.CUSTOM_PAINT_MODE_CARLA_R):
                # knob color
                color = QColor(0xAD, 0xD5, 0x48).lighter(100 + self.fHoverStep*6)

                # draw small circle
                ballRect = QRectF(7.0, 8.0, 11.0, 12.0)
                ballPath = QPainterPath()
                ballPath.addEllipse(ballRect)
                #painter.drawRect(ballRect)
                tmpValue  = (0.375 + 0.75*normValue)
                ballValue = tmpValue - floor(tmpValue)
                ballPoint = ballPath.pointAtPercent(ballValue)

                painter.setBrush(color)
                painter.setPen(QPen(color, 0))
                painter.drawEllipse(QRectF(ballPoint.x(), ballPoint.y(), 2.0, 2.0))

                # draw arc
                if self.fCustomPaintMode == self.CUSTOM_PAINT_MODE_CARLA_L:
                    startAngle = 218*16
                    spanAngle  = -255*16*normValue
                else:
                    startAngle = 322.0*16
                    spanAngle  = 255.0*16*(1.0-normValue)

                painter.setPen(QPen(color, 2.5))
                painter.drawArc(QRectF(3.5, 3.5, 22.0, 22.0), int(startAngle), int(spanAngle))

            # Custom knobs (Color)
            elif self.fCustomPaintMode == self.CUSTOM_PAINT_MODE_COLOR:
                # knob color
                color = self.fCustomPaintColor.lighter(100 + self.fHoverStep*6)

                # draw small circle
                ballRect = QRectF(8.0, 8.0, 15.0, 15.0)
                ballPath = QPainterPath()
                ballPath.addEllipse(ballRect)
                tmpValue  = (0.375 + 0.75*normValue)
                ballValue = tmpValue - floor(tmpValue)
                ballPoint = ballPath.pointAtPercent(ballValue)

                # draw arc
                startAngle = 218*16
                spanAngle  = -255*16*normValue

                painter.setBrush(color)
                painter.setPen(QPen(color, 0))
                painter.drawEllipse(QRectF(ballPoint.x(), ballPoint.y(), 2.2, 2.2))

                painter.setBrush(color)
                painter.setPen(QPen(color, 3))
                painter.drawArc(QRectF(4.0, 4.8, 26.0, 26.0), int(startAngle), int(spanAngle))

            # Custom knobs (Zita)
            elif self.fCustomPaintMode == self.CUSTOM_PAINT_MODE_ZITA:
                a = normValue * pi * 1.5 - 2.35
                r = 10.0
                x = 10.5
                y = 10.5
                x += r * sin(a)
                y -= r * cos(a)
                painter.setBrush(Qt.black)
                painter.setPen(QPen(Qt.black, 2))
                painter.drawLine(QPointF(11.0, 11.0), QPointF(x, y))

            # Custom knobs
            else:
                painter.restore()
                return

            if self.HOVER_MIN < self.fHoverStep < self.HOVER_MAX:
                self.fHoverStep += 1 if self.fIsHovered else -1
                QTimer.singleShot(20, self.update)

        else: # isEnabled()
            target = QRectF(0.0, 0.0, self.fImageBaseSize, self.fImageBaseSize)
            if isinstance(self.fImage, QPixmap):
                painter.drawPixmap(target, self.fImage, target)
            else:
                self.fImage.renderer().render(painter, target)

        painter.restore()

# ---------------------------------------------------------------------------------------------------------------------
