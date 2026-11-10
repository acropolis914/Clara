#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2011-2024 Filipe Coelho <falktx@falktx.com>
# SPDX-License-Identifier: GPL-2.0-or-later

# ------------------------------------------------------------------------------------------------------------
# Imports (Global)

from math import floor, ceil

from qt_compat import (
    QT_VERSION,
    pyqtSignal,
    pyqtSlot,
    qFatal,
    Qt,
    QColor,
    QBrush,
    QPen,
    QPointF,
    QRectF,
    QTimer,
    QCursor,
    QPixmap,
    QPolygonF,
    QGraphicsRectItem,
    QGraphicsScene,
)

# ------------------------------------------------------------------------------------------------------------
# Imports (Custom)

from . import (
    canvas,
    options,
    CanvasBoxType,
    CanvasContainerType,
    CanvasIconType,
    CanvasPortType,
    CanvasLineType,
    CanvasBezierLineType,
    CanvasRubberbandType,
    ACTION_BG_RIGHT_CLICK,
    MAX_PLUGIN_ID_ALLOWED,
)

# ------------------------------------------------------------------------------------------------------------

class RubberbandRect(QGraphicsRectItem):
    def __init__(self, scene):
        QGraphicsRectItem.__init__(self, QRectF(0, 0, 0, 0))

        self.setZValue(-1)
        self.hide()

        scene.addItem(self)

    def type(self):
        return CanvasRubberbandType

# ------------------------------------------------------------------------------------------------------------

class PatchScene(QGraphicsScene):
    scaleChanged = pyqtSignal(float)
    pluginSelected = pyqtSignal(list)

    def __init__(self, parent, view):
        QGraphicsScene.__init__(self, parent)

        self.m_connection_cut_mode = False
        self.m_scale_area = False
        self.m_mouse_down_init = False
        self.m_mouse_rubberband = False
        self.m_scale_min = 0.1
        self.m_scale_max = 4.0

        self.m_rubberband = RubberbandRect(self)
        self.m_rubberband_selection = False
        self.m_rubberband_orig_point = QPointF(0, 0)
        self.m_right_drag_active = False
        self.m_right_press_pos = None
        self.m_right_click_timer = QTimer(self)
        self.m_right_click_timer.setSingleShot(True)
        self.m_right_click_timer.timeout.connect(self._slot_rightClickHoldTimeout)

        self.m_view = view
        if not self.m_view:
            qFatal("PatchCanvas::PatchScene() - invalid view")

        self.m_cursor_cut = None
        self.m_cursor_zoom = None

        self.setItemIndexMethod(QGraphicsScene.NoIndex)
        self.selectionChanged.connect(self.slot_selectionChanged)

    def getDevicePixelRatioF(self):
        if QT_VERSION < 0x50600:
            return 1.0

        return self.m_view.devicePixelRatioF()

    def getScaleFactor(self):
        return self.m_view.transform().m11()

    def getView(self):
        return self.m_view

    def fixScaleFactor(self, transform=None):
        fix, set_view = False, False
        if not transform:
            set_view = True
            view = self.m_view
            transform = view.transform()

        scale = transform.m11()
        if scale > self.m_scale_max:
            fix = True
            transform.reset()
            transform.scale(self.m_scale_max, self.m_scale_max)
        elif scale < self.m_scale_min:
            fix = True
            transform.reset()
            transform.scale(self.m_scale_min, self.m_scale_min)

        if set_view:
            if fix:
                view.setTransform(transform)
            self.scaleChanged.emit(transform.m11())

        return fix

    def updateLimits(self):
        w0 = max(1.0, canvas.size_rect.width())
        h0 = max(1.0, canvas.size_rect.height())
        w1 = max(1.0, self.m_view.width())
        h1 = max(1.0, self.m_view.height())
        fit_scale = w1 / w0 if w0 / h0 > w1 / h1 else h1 / h0
        # Allow flexible zoom out without breaking lower bounds
        self.m_scale_min = min(0.1, max(0.01, fit_scale))

    def updateTheme(self):
        self.setBackgroundBrush(canvas.theme.canvas_bg)
        self.m_rubberband.setPen(canvas.theme.rubberband_pen)
        self.m_rubberband.setBrush(canvas.theme.rubberband_brush)

        cur_color = "black" if canvas.theme.canvas_bg.blackF() < 0.5 else "white"
        self.m_cursor_cut = QCursor(QPixmap(":/cursors/cut_"+cur_color+".png"), 1, 1)
        self.m_cursor_zoom = QCursor(QPixmap(":/cursors/zoom-area_"+cur_color+".png"), 8, 7)

    def drawBackground(self, painter, rect):
        # Draw solid background color from theme
        painter.fillRect(rect, canvas.theme.canvas_bg)

        # The minimap re-renders the whole scene at a tiny scale; the grid is
        # invisible there and expensive to build, so skip it.
        if getattr(canvas, "minimap_rendering", False):
            return

        if not getattr(options, "grid_enabled", True):
            return

        base_grid = getattr(options, "grid_size", 20)
        if base_grid <= 4:
            return

        # Adaptive grid step based on camera zoom factor
        scale = self.getScaleFactor() if hasattr(self, "getScaleFactor") else 1.0
        if scale <= 0.001:
            return

        # Choose LOD step multiplier so screen spacing stays within comfortable 15px - 40px range
        step = float(base_grid)
        screen_dist = step * scale
        if screen_dist < 15.0:
            while step * scale < 15.0:
                step *= 2.0
        elif screen_dist > 40.0:
            while step * scale > 40.0 and (step / 2.0) >= 10.0:
                step /= 2.0

        grid_step = max(5, int(round(step)))

        # Grid marks are the theme text colour at low opacity, so they stay
        # visible on both dark and light backgrounds.
        line_color = QColor(canvas.theme.color_text)
        line_color.setAlpha(10)
        dot_color = QColor(canvas.theme.color_text)
        dot_color.setAlpha(24)

        # Draw secondary major grid lines if zoomed in
        major_step = grid_step * 5

        left = int(floor(rect.left() / grid_step) * grid_step)
        top = int(floor(rect.top() / grid_step) * grid_step)
        right = int(ceil(rect.right()))
        bottom = int(ceil(rect.bottom()))

        # 1. Subtle major grid reference lines
        if scale >= 0.3 and major_step <= 800:
            painter.setPen(QPen(line_color, max(0.5, 1.0 / scale), Qt.DotLine))
            painter.setBrush(Qt.NoBrush)
            major_left = int(floor(rect.left() / major_step) * major_step)
            major_top = int(floor(rect.top() / major_step) * major_step)
            for x in range(major_left, right + major_step, major_step):
                painter.drawLine(QPointF(x, rect.top()), QPointF(x, rect.bottom()))
            for y in range(major_top, bottom + major_step, major_step):
                painter.drawLine(QPointF(rect.left(), y), QPointF(rect.right(), y))

        # 2. Dynamic zoom-scaled intersection dots (guaranteed visible and crisp)
        dot_size = max(1.2, 2.0 / scale)
        points = QPolygonF()
        for x in range(left, right + grid_step, grid_step):
            for y in range(top, bottom + grid_step, grid_step):
                points.append(QPointF(x, y))
        dot_pen = QPen(dot_color)
        dot_pen.setWidthF(dot_size)
        dot_pen.setCapStyle(Qt.RoundCap)
        painter.setPen(dot_pen)
        painter.drawPoints(points)

    def zoom_fit(self):
        min_x = min_y = max_x = max_y = None
        first_value = True

        items_list = self.items()

        if len(items_list) > 0:
            for item in items_list:
                if item and item.isVisible() and item.type() == CanvasBoxType:
                    pos = item.scenePos()
                    rect = item.boundingRect()

                    x = pos.x()
                    y = pos.y()
                    if first_value:
                        first_value = False
                        min_x, min_y = x, y
                        max_x = x + rect.width()
                        max_y = y + rect.height()
                    else:
                        min_x = min(min_x, x)
                        min_y = min(min_y, y)
                        max_x = max(max_x, x + rect.width())
                        max_y = max(max_y, y + rect.height())

            if not first_value:
                self.m_view.fitInView(min_x, min_y, abs(max_x - min_x), abs(max_y - min_y), Qt.KeepAspectRatio)
                self.fixScaleFactor()

    def zoom_in(self):
        view = self.m_view
        transform = view.transform()
        if transform.m11() < self.m_scale_max:
            transform.scale(1.2, 1.2)
            if transform.m11() > self.m_scale_max:
                transform.reset()
                transform.scale(self.m_scale_max, self.m_scale_max)
            view.setTransform(transform)
        self.scaleChanged.emit(transform.m11())

    def zoom_out(self):
        view = self.m_view
        transform = view.transform()
        if transform.m11() > self.m_scale_min:
            transform.scale(0.833333333333333, 0.833333333333333)
            if transform.m11() < self.m_scale_min:
                transform.reset()
                transform.scale(self.m_scale_min, self.m_scale_min)
            view.setTransform(transform)
        self.scaleChanged.emit(transform.m11())

    def zoom_reset(self):
        self.m_view.resetTransform()
        self.scaleChanged.emit(1.0)

    def handleMouseRelease(self):
        rubberband_active = self.m_rubberband_selection

        if self.m_scale_area and not self.m_rubberband_selection:
            self.m_scale_area = False
            self.m_view.viewport().unsetCursor()

        if self.m_rubberband_selection:
            if self.m_scale_area:
                self.m_scale_area = False
                self.m_view.viewport().unsetCursor()

                rect = self.m_rubberband.rect()
                self.m_view.fitInView(rect.x(), rect.y(), rect.width(), rect.height(), Qt.KeepAspectRatio)
                self.fixScaleFactor()

            else:
                orig_x = self.m_rubberband_orig_point.x()
                curr_x = getattr(self, "m_rubberband_last_pos", self.m_rubberband_orig_point).x()
                # Left -> Right: select all touched (intersecting)
                # Right -> Left: select only fully enclosed
                select_touched = (curr_x >= orig_x)

                rb_rect = self.m_rubberband.rect()
                items_list = self.items()
                for item in items_list:
                    if item and item.isVisible() and item.type() == CanvasBoxType:
                        item_rect = item.sceneBoundingRect()
                        if select_touched:
                            if rb_rect.intersects(item_rect):
                                item.setSelected(True)
                        else:
                            if rb_rect.contains(item_rect):
                                item.setSelected(True)

            self.m_rubberband.hide()
            self.m_rubberband.setRect(0, 0, 0, 0)
            self.m_rubberband_selection = False

        self.m_mouse_rubberband = False

        self.stopConnectionCut()

        return rubberband_active

    def startConnectionCut(self):
        if self.m_cursor_cut:
            self.m_connection_cut_mode = True
            self.m_view.viewport().setCursor(self.m_cursor_cut)

    def stopConnectionCut(self):
        if self.m_connection_cut_mode:
            self.m_connection_cut_mode = False
            self.m_view.viewport().unsetCursor()

    def triggerRubberbandScale(self):
        self.m_scale_area = True
        if self.m_cursor_zoom:
            self.m_view.viewport().setCursor(self.m_cursor_zoom)

    @pyqtSlot()
    def slot_selectionChanged(self):
        items_list = self.selectedItems()

        if len(items_list) == 0:
            self.pluginSelected.emit([])
            return

        plugin_list = []

        for item in items_list:
            if item and item.isVisible():
                group_item = None

                if item.type() == CanvasBoxType:
                    group_item = item
                elif item.type() == CanvasPortType:
                    group_item = item.parentItem()
                #elif item.type() in (CanvasLineType, CanvasBezierLineType, CanvasLineMovType, CanvasBezierLineMovType):
                    #plugin_list = []
                    #break

                if group_item is not None and group_item.m_plugin_id >= 0:
                    plugin_id = group_item.m_plugin_id
                    if plugin_id > MAX_PLUGIN_ID_ALLOWED:
                        plugin_id = 0
                    plugin_list.append(plugin_id)

        self.pluginSelected.emit(plugin_list)

    def keyPressEvent(self, event):
        if not self.m_view:
            event.ignore()
            return

        if self.focusItem() is not None:
            QGraphicsScene.keyPressEvent(self, event)
            return

        if event.key() == Qt.Key_Home:
            event.accept()
            self.zoom_fit()
            return

        if event.modifiers() & Qt.ControlModifier:
            if event.key() == Qt.Key_S:
                import carla_shared
                if hasattr(carla_shared.gCarla, "gui") and hasattr(carla_shared.gCarla.gui, "slot_fileSave"):
                    event.accept()
                    if event.modifiers() & Qt.ShiftModifier:
                        carla_shared.gCarla.gui.slot_fileSaveAs()
                    else:
                        carla_shared.gCarla.gui.slot_fileSave()
                    return

            if event.key() == Qt.Key_F:
                if hasattr(self.m_view, "toggleSearch"):
                    event.accept()
                    self.m_view.toggleSearch()
                    return

            if event.key() == Qt.Key_Plus:
                event.accept()
                self.zoom_in()
                return

            if event.key() == Qt.Key_Minus:
                event.accept()
                self.zoom_out()
                return

            if event.key() == Qt.Key_1:
                event.accept()
                self.zoom_reset()
                return

        QGraphicsScene.keyPressEvent(self, event)

    def keyReleaseEvent(self, event):
        self.stopConnectionCut()
        QGraphicsScene.keyReleaseEvent(self, event)

    def _slot_rightClickHoldTimeout(self):
        # Stationary right-click hold elapsed: trigger background context menu immediately if not already dragging
        if getattr(self, "m_mouse_down_init", False) and not self.m_right_drag_active:
            self.m_mouse_down_init = False
            self.m_mouse_rubberband = False
            pos = self.m_right_press_pos
            self.m_right_press_pos = None
            if pos is not None:
                canvas.callback(ACTION_BG_RIGHT_CLICK, int(pos.x()), int(pos.y()), f"{pos.x()}:{pos.y()}")
            else:
                canvas.callback(ACTION_BG_RIGHT_CLICK, 0, 0, "")

    def mousePressEvent(self, event):
        ctrlDown = bool(event.modifiers() & Qt.ControlModifier)

        if event.button() == Qt.RightButton:
            items = self.items(event.scenePos())
            on_item = any(item and item.type() in (CanvasBoxType, CanvasIconType, CanvasPortType) for item in items)
            if not on_item:
                self.m_mouse_down_init = True
                self.m_mouse_rubberband = False
                self.m_right_drag_active = False
                self.m_right_press_pos = event.scenePos()
                self.m_rubberband_last_pos = event.scenePos()
                self.m_right_click_timer.start(150)
            else:
                self.m_mouse_down_init = False
                self.m_right_press_pos = None
        else:
            self.m_mouse_down_init = False
            self.m_right_click_timer.stop()
            self.m_right_press_pos = None

        if event.button() == Qt.MiddleButton and ctrlDown:
            self.startConnectionCut()
            items = self.items(event.scenePos())
            for item in items:
                if item and item.type() in (CanvasLineType, CanvasBezierLineType, CanvasPortType):
                    item.triggerDisconnect()

        if event.button() != Qt.RightButton or on_item:
            QGraphicsScene.mousePressEvent(self, event)

    def mouseMoveEvent(self, event):
        if self.m_mouse_down_init and self.m_right_press_pos is not None:
            delta = event.scenePos() - self.m_right_press_pos
            dist = (delta.x()**2 + delta.y()**2) ** 0.5
            if dist >= 4.0:
                self.m_right_click_timer.stop()
                self.m_mouse_rubberband = True
                self.m_right_drag_active = True
                self.m_mouse_down_init = False

        if self.m_mouse_rubberband:
            event.accept()
            pos = event.scenePos()
            self.m_rubberband_last_pos = pos
            pos_x = pos.x()
            pos_y = pos.y()
            if not self.m_rubberband_selection:
                self.m_rubberband.show()
                self.m_rubberband_selection = True
                self.m_rubberband_orig_point = self.m_right_press_pos if self.m_right_press_pos is not None else pos
            rubberband_orig_point = self.m_rubberband_orig_point

            x = min(pos_x, rubberband_orig_point.x())
            y = min(pos_y, rubberband_orig_point.y())

            # Throttle tiny sub-pixel rect adjustments
            last_p = getattr(self, "_last_rubberband_rect_pos", None)
            if last_p is not None:
                dx = pos_x - last_p.x()
                dy = pos_y - last_p.y()
                if (dx * dx + dy * dy) < 4.0:
                    return

            self._last_rubberband_rect_pos = pos

            lineHinting = canvas.theme.rubberband_pen.widthF() / 2
            self.m_rubberband.setRect(x+lineHinting,
                                      y+lineHinting,
                                      abs(pos_x - rubberband_orig_point.x()),
                                      abs(pos_y - rubberband_orig_point.y()))
            return

        if self.m_connection_cut_mode:
            trail = QPolygonF([event.scenePos(), event.lastScenePos(), event.scenePos()])
            items = self.items(trail)
            for item in items:
                if item and item.type() in (CanvasLineType, CanvasBezierLineType):
                    item.triggerDisconnect()

        QGraphicsScene.mouseMoveEvent(self, event)

    def mouseReleaseEvent(self, event):
        self.m_right_click_timer.stop()
        was_short_click = (event.button() == Qt.RightButton and self.m_mouse_down_init and not self.m_right_drag_active)
        self.m_mouse_down_init = False
        self.m_right_press_pos = None

        if not self.handleMouseRelease():
            items_list = self.selectedItems()
            needs_update = False
            for item in items_list:
                if item and item.isVisible() and item.type() == CanvasBoxType:
                    item.checkItemPos()
                    needs_update = True

            if needs_update:
                canvas.scene.update()

            if was_short_click:
                event.accept()
                sp = event.scenePos()
                canvas.callback(ACTION_BG_RIGHT_CLICK, int(sp.x()), int(sp.y()), f"{sp.x()}:{sp.y()}")
                return

        QGraphicsScene.mouseReleaseEvent(self, event)

    def zoom_wheel(self, delta):
        transform = self.m_view.transform()
        scale = transform.m11()

        if (delta > 0 and scale < self.m_scale_max) or (delta < 0 and scale > self.m_scale_min):
            factor = 1.41 ** (delta / 240.0)
            transform.scale(factor, factor)
            self.fixScaleFactor(transform)
            self.m_view.setTransform(transform)
            self.scaleChanged.emit(transform.m11())

    def wheelEvent(self, event):
        if not self.m_view:
            event.ignore()
            return

        if event.modifiers() & Qt.ControlModifier:
            event.accept()
            self.zoom_wheel(event.delta())
            return

        QGraphicsScene.wheelEvent(self, event)

    def contextMenuEvent(self, event):
        self.m_right_click_timer.stop()
        if getattr(self, "m_right_drag_active", False):
            self.m_right_drag_active = False
            event.accept()
            return

        if self.handleMouseRelease():
            self.m_mouse_down_init = False
            QGraphicsScene.contextMenuEvent(self, event)
            return

        if event.modifiers() & Qt.ControlModifier:
            event.accept()
            self.triggerRubberbandScale()
            return

        items = self.items(event.scenePos())
        on_item = any(item and item.type() in (CanvasBoxType, CanvasContainerType, CanvasIconType, CanvasPortType) for item in items)
        if not on_item:
            self.m_mouse_down_init = False
            event.accept()
            sp = event.scenePos()
            canvas.callback(ACTION_BG_RIGHT_CLICK, int(sp.x()), int(sp.y()), f"{sp.x()}:{sp.y()}")
            return

        self.m_mouse_down_init = False
        QGraphicsScene.contextMenuEvent(self, event)

# ------------------------------------------------------------------------------------------------------------
