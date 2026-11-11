#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Clara Contributors
# SPDX-License-Identifier: GPL-2.0-or-later

"""Floating minimap for the Clara patchbay.

The minimap renders the live QGraphicsScene (like the classic sidebar
preview) so nodes, ports, headers and cables keep their real appearance.
On top of the render, every node is outlined with its own custom color,
contrast-corrected against the background so even uncolored nodes remain
clearly visible. The view supports zoom (mouse wheel) and pan
(middle-drag), which makes large patches navigable.
"""


from qt_compat import (
    Qt,
    QEvent,
    QObject,
    QRectF,
    QPoint,
    QPointF,
    QPainter,
    QPen,
    QBrush,
    QColor,
    QFont,
    QPixmap,
    QTimer,
    QFrame,
    QLabel,
    QMenu,
    QToolButton,
    QHBoxLayout,
    QVBoxLayout,
    QSizePolicy,
    pyqtSignal,
    QT_VERSION,
)

from patchcanvas import patchcanvas


class _ViewportEventFilter(QObject):
    def __init__(self, minimap):
        super().__init__(minimap)
        self.minimap = minimap

    def eventFilter(self, obj, event):
        if event.type() in (QEvent.Resize, QEvent.Move, QEvent.Show, QEvent.Hide):
            self.minimap.update()
        return False


class CanvasMinimapFrame(QFrame):
    miniCanvasMoved = pyqtSignal(float, float)
    zoomChanged = pyqtSignal(float)

    _MIN_ZOOM = 1.0
    _MAX_ZOOM = 12.0
    _NODE_MIN_CONTRAST = 3.0
    _NODE_FILL_CONTRAST = 2.0

    def __init__(self, parent, graphics_view, scene, host=None, width=250, height=170):
        super().__init__(parent)
        self.graphics_view = graphics_view
        self.fScene = scene
        self.host = host
        self._zoom = 1.0
        self._center = None
        self._grabbed = False
        self._panning = False
        self._pan_last = None
        self._drag_pos = None
        self._edge_margin = 14.0

        self._edge_timer = QTimer(self)
        self._edge_timer.setInterval(16)
        self._edge_timer.timeout.connect(self._edge_tick)

        # Coalesce scene-change repaints. During a node drag the scene emits
        # changed on every frame; re-rendering the whole scene into the minimap
        # cache each frame is expensive and makes dragging laggy.
        self._scene_timer = QTimer(self)
        self._scene_timer.setSingleShot(True)
        self._scene_timer.setInterval(33)
        self._scene_timer.timeout.connect(self._flush_scene_change)

        self._bounds = QRectF()
        self._src = QRectF()
        self._eff = 1.0
        self._cache = None
        self._cache_key = None

        self.fViewBg = QColor(0, 0, 0)
        self.fViewBrush = QBrush(QColor(75, 75, 255, 30))
        self.fViewPen = QPen(Qt.blue, 1)

        self.setMinimumSize(width, height)
        self.setMaximumSize(width, height)
        self.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        self.setFrameShape(QFrame.NoFrame)
        self.setMouseTracking(True)
        self.setToolTip(
            "Scroll: zoom  \u2022  middle-drag: pan  \u2022  left-drag: navigate canvas  "
            "\u2022  double-click: reset"
        )

        try:
            self.fViewBg = QColor(patchcanvas.canvas.theme.canvas_bg)
        except Exception:
            pass

        try:
            if graphics_view is not None:
                self._viewFilter = _ViewportEventFilter(self)
                graphics_view.viewport().installEventFilter(self._viewFilter)
        except Exception:
            pass

        try:
            if scene is not None and hasattr(scene, "changed"):
                scene.changed.connect(self._on_scene_changed)
        except Exception:
            pass

        for signal_name in ("horizontalScrollBar", "verticalScrollBar"):
            try:
                bar = getattr(graphics_view, signal_name)()
                bar.valueChanged.connect(lambda *args: self.update())
            except Exception:
                pass

        try:
            if hasattr(graphics_view, "transformed"):
                graphics_view.transformed.connect(lambda *args: self.update())
        except Exception:
            pass
        try:
            if hasattr(scene, "scaleChanged"):
                scene.scaleChanged.connect(lambda *args: self.update())
        except Exception:
            pass

    # ---------------------------------------------------------------- API

    def _on_scene_changed(self, *args):
        if not self._scene_timer.isActive():
            self._scene_timer.start()

    def _flush_scene_change(self):
        self._cache = None
        self.update()

    def setRealParent(self, parent):
        # compatibility no-op
        pass

    def setViewTheme(self, bg, brush, pen):
        try:
            self.fViewBg = QColor(bg)
        except Exception:
            pass
        try:
            self.fViewBrush = QBrush(QColor(brush))
        except Exception:
            pass
        try:
            self.fViewPen = QPen(QColor(pen), 1)
        except Exception:
            pass
        self.update()

    def init(self, scene, realWidth, realHeight, useCustomPaint=False):
        self.fScene = scene
        self.resetView()

    def setViewPosX(self, xp):
        self.update()

    def setViewPosY(self, yp):
        self.update()

    def setViewScale(self, scale):
        self.update()

    def setViewSize(self, width, height):
        self.update()

    def resetView(self):
        self._zoom = 1.0
        self._center = None
        self.update()
        self.zoomChanged.emit(self._zoom)

    def getZoom(self):
        return self._zoom

    def setZoom(self, zoom, center=None):
        try:
            self._zoom = min(self._MAX_ZOOM, max(self._MIN_ZOOM, float(zoom)))
        except Exception:
            self._zoom = 1.0
        self._center = center
        self.update()
        self.zoomChanged.emit(self._zoom)

    # ---------------------------------------------------------------- bounds

    def _is_box(self, item):
        try:
            if not item.isVisible():
                return False
        except Exception:
            pass
        try:
            if isinstance(item, patchcanvas.CanvasBox):
                r = item.sceneBoundingRect()
                return r.width() > 0.5 and r.height() > 0.5
        except Exception:
            pass
        return hasattr(item, "m_group_id") and hasattr(item, "p_height")

    def _scene_bounds(self):
        bounds = None
        try:
            for item in self.fScene.items():
                if not self._is_box(item):
                    continue
                r = item.sceneBoundingRect()
                bounds = QRectF(r) if bounds is None else bounds.united(r)
        except Exception:
            bounds = None
        if bounds is None or bounds.isNull() or bounds.width() <= 0 or bounds.height() <= 0:
            try:
                scene_rect = self.fScene.sceneRect()
                if scene_rect is not None and not scene_rect.isNull():
                    bounds = QRectF(scene_rect)
            except Exception:
                bounds = None
        if bounds is None or bounds.isNull() or bounds.width() <= 0 or bounds.height() <= 0:
            bounds = QRectF(0.0, 0.0, 1000.0, 1000.0)
        try:
            bounds.adjust(-48.0, -48.0, 48.0, 48.0)
        except Exception:
            pass
        return bounds

    def _compute_view(self, bounds):
        w = max(1.0, float(self.width()))
        h = max(1.0, float(self.height()))
        bw = max(1.0, bounds.width())
        bh = max(1.0, bounds.height())

        fit = min(w / bw, h / bh)
        eff = max(0.0001, fit * self._zoom)
        src_w = w / eff
        src_h = h / eff

        center = self._center if self._center is not None else bounds.center()
        cx = center.x()
        cy = center.y()
        if src_w < bw:
            half = src_w * 0.5
            cx = min(max(cx, bounds.left() + half), bounds.right() - half)
        else:
            cx = bounds.center().x()
        if src_h < bh:
            half = src_h * 0.5
            cy = min(max(cy, bounds.top() + half), bounds.bottom() - half)
        else:
            cy = bounds.center().y()

        self._center = QPointF(cx, cy)
        src = QRectF(cx - src_w * 0.5, cy - src_h * 0.5, src_w, src_h)
        return src, eff

    def _current_view(self):
        bounds = self._scene_bounds()
        src, eff = self._compute_view(bounds)
        self._bounds = bounds
        self._src = src
        self._eff = eff
        return bounds, src, eff

    def _viewport_scene_rect(self):
        try:
            return self.graphics_view.mapToScene(
                self.graphics_view.viewport().rect()
            ).boundingRect()
        except Exception:
            return QRectF()

    # ---------------------------------------------------------------- render

    def _render_cache(self, src):
        bg = self.fViewBg if isinstance(self.fViewBg, QColor) else QColor(24, 24, 37)
        pix = QPixmap(self.width(), self.height())
        pix.fill(bg)
        painter = QPainter(pix)
        painter.setRenderHint(QPainter.Antialiasing, True)
        painter.setRenderHint(QPainter.SmoothPixmapTransform, True)
        painter.fillRect(pix.rect(), bg)
        try:
            target = QRectF(0.0, 0.0, float(self.width()), float(self.height()))
            # The grid is meaningless at minimap scale and expensive to draw,
            # so tell the scene to skip it for this off-screen render.
            try:
                patchcanvas.canvas.minimap_rendering = True
            except Exception:
                pass
            try:
                self.fScene.render(painter, target, src, Qt.KeepAspectRatio)
            finally:
                try:
                    patchcanvas.canvas.minimap_rendering = False
                except Exception:
                    pass
        except Exception:
            pass
        painter.end()
        return pix

    def _cache_signature(self, bounds, src):
        def r(v):
            return round(float(v) * 2.0) / 2.0
        return (
            (self.width(), self.height()),
            (r(bounds.x()), r(bounds.y()), r(bounds.width()), r(bounds.height())),
            (r(src.x()), r(src.y()), r(src.width()), r(src.height())),
        )

    # ---------------------------------------------------------------- paint

    def paintEvent(self, event):
        if self.fScene is None:
            super().paintEvent(event)
            return
        try:
            bounds, src, eff = self._current_view()
        except Exception:
            super().paintEvent(event)
            return

        key = self._cache_signature(bounds, src)
        if self._cache is None or self._cache_key != key:
            try:
                self._cache = self._render_cache(src)
                self._cache_key = key
            except Exception:
                self._cache = None

        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, True)

        if self._cache is not None:
            painter.drawPixmap(0, 0, self._cache)

        self._draw_node_outlines(painter, src, eff)
        self._draw_viewport(painter, src, eff)
        self._draw_hud(painter)
        painter.end()

    def _draw_hud(self, painter):
        try:
            fg = QColor(205, 214, 244)
            if self.fViewBg is not None and self.fViewBg.black() > 140:
                fg = QColor(40, 44, 60)

            font = QFont()
            font.setPointSizeF(7.5)
            font.setBold(True)
            painter.setFont(font)

            if self._zoom <= 1.001:
                label = "FIT"
            else:
                label = f"{int(round(self._zoom * 100))}%"

            metrics = painter.fontMetrics()
            pad = 3
            tw = metrics.horizontalAdvance(label)
            th = metrics.height()
            badge = QRectF(pad, pad, tw + pad * 2, th + pad)
            painter.setPen(Qt.NoPen)
            badge_bg = QColor(0, 0, 0, 150) if fg.lightness() > 128 else QColor(255, 255, 255, 150)
            painter.setBrush(badge_bg)
            painter.drawRoundedRect(badge, 3, 3)
            painter.setPen(fg)
            painter.drawText(badge, int(Qt.AlignCenter), label)

            if self.height() >= 90:
                hint_font = QFont()
                hint_font.setPointSizeF(6.5)
                painter.setFont(hint_font)
                hint = "scroll zoom  \u00b7  mid-drag pan  \u00b7  double-click reset"
                hmetrics = painter.fontMetrics()
                hw = hmetrics.horizontalAdvance(hint)
                x = (self.width() - hw) * 0.5
                y = self.height() - 4
                painter.setPen(QColor(0, 0, 0, 130))
                painter.drawText(QPointF(x + 1, y + 1), hint)
                painter.setPen(QColor(fg.red(), fg.green(), fg.blue(), 170))
                painter.drawText(QPointF(x, y), hint)
        except Exception:
            pass

    def _draw_node_outlines(self, painter, src, eff):
        try:
            bg = self.fViewBg if isinstance(self.fViewBg, QColor) else QColor(24, 24, 37)
        except Exception:
            bg = QColor(24, 24, 37)
        try:
            box_fill = QColor(patchcanvas.canvas.theme.box_bg_1)
        except Exception:
            box_fill = QColor(30, 30, 45)
        try:
            default_color = QColor(patchcanvas.canvas.theme.box_bg_2)
        except Exception:
            default_color = QColor(90, 90, 110)

        painter.setBrush(Qt.NoBrush)
        try:
            items = list(self.fScene.items())
        except Exception:
            return
        for item in items:
            if not self._is_box(item):
                continue
            r = item.sceneBoundingRect()
            x = (r.left() - src.left()) * eff
            y = (r.top() - src.top()) * eff
            w = r.width() * eff
            h = r.height() * eff
            if x > self.width() or y > self.height() or x + w < 0 or y + h < 0:
                continue

            color = None
            try:
                color = item.getCustomColor()
            except Exception:
                color = None
            if not isinstance(color, QColor) or not color.isValid():
                color = QColor(default_color)

            visible = self._ensure_visible(color, bg, self._NODE_MIN_CONTRAST)
            visible = self._ensure_visible(visible, box_fill, self._NODE_FILL_CONTRAST)

            pen = QPen(visible)
            pen.setWidthF(1.5)
            painter.setPen(pen)
            painter.drawRect(
                QRectF(x, y, max(1.0, w), max(1.0, h))
            )

    def _draw_viewport(self, painter, src, eff):
        try:
            vp = self._viewport_scene_rect()
            x = (vp.left() - src.left()) * eff
            y = (vp.top() - src.top()) * eff
            w = max(1.0, vp.width() * eff)
            h = max(1.0, vp.height() * eff)
            painter.setBrush(self.fViewBrush)
            painter.setPen(Qt.NoPen)
            painter.drawRect(QRectF(x, y, w, h))
            painter.setBrush(Qt.NoBrush)
            painter.setPen(self.fViewPen)
            painter.drawRect(QRectF(x, y, w, h))
        except Exception:
            pass

    # ---------------------------------------------------------------- contrast

    @staticmethod
    def _luminance(color):
        def channel(v):
            v = v / 255.0
            if v <= 0.03928:
                return v / 12.92
            return ((v + 0.055) / 1.055) ** 2.4

        return (
            0.2126 * channel(color.red())
            + 0.7152 * channel(color.green())
            + 0.0722 * channel(color.blue())
        )

    @classmethod
    def _contrast(cls, c1, c2):
        l1 = CanvasMinimapFrame._luminance(c1)
        l2 = CanvasMinimapFrame._luminance(c2)
        if l1 < l2:
            l1, l2 = l2, l1
        return (l1 + 0.05) / (l2 + 0.05)

    @classmethod
    def _ensure_visible(cls, color, background, min_ratio):
        try:
            color = QColor(color)
            bg = QColor(background)
        except Exception:
            return QColor(color)

        if cls._contrast(color, bg) >= min_ratio:
            return color

        bg_luminance = cls._luminance(bg)
        target = QColor(255, 255, 255) if bg_luminance < 0.5 else QColor(0, 0, 0)
        best = color
        for step in range(1, 21):
            t = step / 20.0
            candidate = QColor(
                int(round(color.red() * (1.0 - t) + target.red() * t)),
                int(round(color.green() * (1.0 - t) + target.green() * t)),
                int(round(color.blue() * (1.0 - t) + target.blue() * t)),
            )
            best = candidate
            if cls._contrast(candidate, bg) >= min_ratio:
                break
        return best

    # ---------------------------------------------------------------- mapping

    def _widget_to_scene(self, px, py):
        _, src, eff = self._current_view()
        return (
            src.left() + px / max(0.0001, eff),
            src.top() + py / max(0.0001, eff),
        )

    def _event_pos(self, event):
        if QT_VERSION >= 0x60000:
            pos = event.position()
            return pos.x(), pos.y()
        return event.x(), event.y()

    # ---------------------------------------------------------------- mouse

    def wheelEvent(self, event):
        if self.fScene is None:
            super().wheelEvent(event)
            return
        try:
            delta = event.angleDelta().y()
        except Exception:
            delta = 0
        if delta == 0:
            return
        event.accept()

        px, py = self._event_pos(event)
        bounds, src, eff = self._current_view()
        sx = src.left() + px / max(0.0001, eff)
        sy = src.top() + py / max(0.0001, eff)

        new_zoom = min(self._MAX_ZOOM, max(self._MIN_ZOOM, self._zoom * (1.2 ** (delta / 120.0))))
        if abs(new_zoom - self._zoom) < 1e-4:
            return
        self._zoom = new_zoom

        w = max(1.0, float(self.width()))
        h = max(1.0, float(self.height()))
        new_eff = max(0.0001, min(w / max(1.0, bounds.width()),
                                  h / max(1.0, bounds.height())) * new_zoom)
        self._center = QPointF(
            sx - (px - w * 0.5) / new_eff,
            sy - (py - h * 0.5) / new_eff,
        )
        self.update()
        self.zoomChanged.emit(self._zoom)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._grabbed = True
            x, y = self._event_pos(event)
            self._drag_pos = (x, y)
            if not self._edge_timer.isActive():
                self._edge_timer.start()
            self._pan_to(x, y)
            event.accept()
        elif event.button() == Qt.MiddleButton:
            self._panning = True
            self._pan_last = self._event_pos(event)
            self.setCursor(Qt.SizeAllCursor)
            event.accept()
        else:
            super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self._panning and self._pan_last is not None:
            x, y = self._event_pos(event)
            _, _, eff = self._current_view()
            lx, ly = self._pan_last
            center = self._center if self._center is not None else self._bounds.center()
            self._center = QPointF(
                center.x() - (x - lx) / max(0.0001, eff),
                center.y() - (y - ly) / max(0.0001, eff),
            )
            self._pan_last = (x, y)
            self.update()
            event.accept()
        elif self._grabbed:
            x, y = self._event_pos(event)
            self._drag_pos = (x, y)
            self._pan_to(
                min(max(0.0, x), float(self.width())),
                min(max(0.0, y), float(self.height())),
            )
            if not self._edge_timer.isActive():
                self._edge_timer.start()
            event.accept()
        else:
            super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._grabbed = False
            self._drag_pos = None
            self._edge_timer.stop()
            event.accept()
        elif event.button() == Qt.MiddleButton:
            self._panning = False
            self._pan_last = None
            self.unsetCursor()
            event.accept()
        else:
            super().mouseReleaseEvent(event)

    def _edge_tick(self):
        if not self._grabbed or self._drag_pos is None:
            self._edge_timer.stop()
            return
        x, y = self._drag_pos
        w = max(1.0, float(self.width()))
        h = max(1.0, float(self.height()))
        margin = self._edge_margin

        overflow_x = 0.0
        if x < margin:
            overflow_x = x - margin
        elif x > w - margin:
            overflow_x = x - (w - margin)
        overflow_y = 0.0
        if y < margin:
            overflow_y = y - margin
        elif y > h - margin:
            overflow_y = y - (h - margin)

        if overflow_x == 0.0 and overflow_y == 0.0:
            self._edge_timer.stop()
            return

        try:
            bounds, src, eff = self._current_view()
        except Exception:
            return
        eff = max(0.0001, eff)
        center = self._center if self._center is not None else bounds.center()
        prev = (center.x(), center.y())
        speed = 0.25
        self._center = QPointF(
            center.x() + (overflow_x / eff) * speed,
            center.y() + (overflow_y / eff) * speed,
        )
        self._pan_to(
            min(max(0.0, x), w),
            min(max(0.0, y), h),
        )
        clamped = self._center if self._center is not None else center
        if abs(clamped.x() - prev[0]) < 1e-6 and abs(clamped.y() - prev[1]) < 1e-6:
            self._edge_timer.stop()
        self.update()

    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.resetView()
            event.accept()
        else:
            super().mouseDoubleClickEvent(event)

    def _pan_to(self, px, py):
        try:
            sx, sy = self._widget_to_scene(px, py)
            self.graphics_view.centerOn(sx, sy)
            bounds = self._bounds
            if bounds.width() > 0 and bounds.height() > 0:
                xp = (sx - bounds.left()) / bounds.width()
                yp = (sy - bounds.top()) / bounds.height()
                self.miniCanvasMoved.emit(float(xp), float(yp))
        except Exception:
            pass


class CanvasMinimapOverlay(QFrame):
    """Frameless floating container for the minimap.

    Blender-style: a thin grip row (drag to move, no title), a corner
    collapse tab, and a right-click context menu. The minimap itself is
    exposed as ``.map``.
    """

    visibilityChanged = pyqtSignal(bool)
    collapsedChanged = pyqtSignal(bool)
    geometryChanged = pyqtSignal()
    zoomChanged = pyqtSignal(float)

    def __init__(self, parent, graphics_view, scene, host=None):
        super().__init__(parent)
        self.setObjectName("miniCanvasFloatFrame")
        self.setFrameShape(QFrame.StyledPanel)

        self._collapsed = False
        self._drag_origin = None
        self._drag_start = None
        self._dock = "float"
        self.dockRequested = pyqtSignal(str)  # "float" | "top" | "bottom"

        self.map = CanvasMinimapFrame(self, graphics_view, scene, host)
        self.map.zoomChanged.connect(self.zoomChanged.emit)

        root = QVBoxLayout(self)
        root.setContentsMargins(3, 3, 3, 3)
        root.setSpacing(2)
        self._root = root

        # No header row: the grip and collapse buttons float INSIDE the map
        # with a small offset, out of the map's own mouse handlers' way.
        self._grip = QToolButton(self.map)
        self._grip.setObjectName("miniCanvasGrip")
        self._grip.setToolTip("Drag to move \u2022 right-click for options")
        self._grip.setAutoRaise(True)
        self._grip.setCursor(Qt.SizeAllCursor)
        self._grip.setFixedSize(20, 20)
        self._grip.installEventFilter(self)

        self._collapseBtn = QToolButton(self.map)
        self._collapseBtn.setObjectName("miniCanvasCollapse")
        try:
            from widgets.lucide import bind_icon
            bind_icon(self._collapseBtn, "chevron-down", size=12)
        except Exception:
            self._collapseBtn.setText("\u25be")
        self._collapseBtn.setToolTip("Collapse / expand minimap")
        self._collapseBtn.setAutoRaise(True)
        self._collapseBtn.setFixedSize(20, 20)
        self._collapseBtn.clicked.connect(lambda *_: self.toggleCollapsed())

        root.addWidget(self.map)
        self._relayoutFloatButtons()

        for w in (self, self.map):
            w.setContextMenuPolicy(Qt.CustomContextMenu)
            w.customContextMenuRequested.connect(
                lambda pos, widget=w: self._showContextMenu(widget, pos)
            )

    def _relayoutFloatButtons(self):
        """Keep the floating buttons pinned to the map's top corners."""
        if getattr(self, "map", None) is None:
            return
        try:
            self._grip.move(6, 6)
            self._collapseBtn.move(self.map.width() - self._collapseBtn.width() - 6, 6)
            self._grip.raise_()
            self._collapseBtn.raise_()
        except Exception:
            pass

    def resizeEvent(self, event):
        self._relayoutFloatButtons()
        QFrame.resizeEvent(self, event)

    # ------------------------------------------------------------ state

    def isCollapsed(self):
        return self._collapsed

    def toggleCollapsed(self, collapsed=None):
        if collapsed is None:
            collapsed = not self._collapsed
        collapsed = bool(collapsed)
        if collapsed == self._collapsed:
            return
        self._collapsed = collapsed
        self.map.setVisible(not collapsed)
        if getattr(self._collapseBtn, "_lucide_bound", False):
            self._collapseBtn._lucide_name = "chevron-up" if collapsed else "chevron-down"
            self._collapseBtn._lucide_refresh()
        else:
            self._collapseBtn.setText("\u25b8" if collapsed else "\u25be")
        self.adjustSize()
        self.updateGeometry()
        self.collapsedChanged.emit(collapsed)

    # ------------------------------------------------------------ drag

    def _global_pos(self, event):
        if QT_VERSION >= 0x60000:
            return event.globalPosition().toPoint()
        return event.globalPos()

    def eventFilter(self, obj, event):
        if obj is self._grip:
            et = event.type()
            if et == QEvent.MouseButtonPress and event.button() == Qt.LeftButton:
                self._drag_origin = self._global_pos(event)
                self._drag_start = QPoint(self.pos())
                return True
            if event.type() == QEvent.MouseMove and self._drag_origin is not None:
                gp = self._global_pos(event)
                new_pos = self._drag_start + (gp - self._drag_origin)
                self._clamp_and_move(new_pos)
                return True
            if event.type() == QEvent.MouseButtonRelease and self._drag_origin is not None:
                self._drag_origin = None
                self._drag_start = None
                self.geometryChanged.emit()
                return True
        return super().eventFilter(obj, event)

    def _clamp_and_move(self, pos):
        parent = self.parentWidget()
        if parent is not None:
            max_x = max(0, parent.width() - self.width())
            max_y = max(0, parent.height() - self.height())
            pos.setX(min(max(0, pos.x()), max_x))
            pos.setY(min(max(0, pos.y()), max_y))
        self.move(pos)

    # ------------------------------------------------------------ menu

    def dockMode(self):
        return self._dock

    def setDockMode(self, mode):
        """Track the dock mode; the host performs the actual reparenting."""
        if mode not in ("float", "top", "bottom"):
            return
        self._dock = mode
        # Floating is the only mode where dragging the map makes sense.
        self._grip.setEnabled(True)
        self._grip.setCursor(Qt.SizeAllCursor if mode == "float" else Qt.ArrowCursor)

    def _showContextMenu(self, widget, pos):
        try:
            menu = QMenu(self)
            act_collapse = menu.addAction("Expand" if self._collapsed else "Collapse")
            act_reset = menu.addAction("Reset zoom")
            menu.addSeparator()
            dock_menu = menu.addMenu("Dock")
            act_float = dock_menu.addAction("Float over canvas")
            act_top = dock_menu.addAction("Dock at top of rack")
            act_bottom = dock_menu.addAction("Dock at bottom of rack")
            act_float.setCheckable(True)
            act_top.setCheckable(True)
            act_bottom.setCheckable(True)
            act_float.setChecked(self._dock == "float")
            act_top.setChecked(self._dock == "top")
            act_bottom.setChecked(self._dock == "bottom")
            menu.addSeparator()
            act_hide = menu.addAction("Hide minimap")
            chosen = menu.exec(widget.mapToGlobal(pos))
            if chosen == act_collapse:
                self.toggleCollapsed()
            elif chosen == act_reset:
                self.map.resetView()
            elif chosen in (act_float, act_top, act_bottom):
                mode = {act_float: "float", act_top: "top", act_bottom: "bottom"}[chosen]
                self.dockRequested.emit(mode)
            elif chosen == act_hide:
                self.visibilityChanged.emit(False)
        except Exception:
            pass

