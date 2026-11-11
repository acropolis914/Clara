#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Clara contributors
# SPDX-License-Identifier: GPL-2.0-or-later

# MiniCanvas controls and placement, split out of host_app.py.
# HostWindow inherits this mixin.

from carla_app import QSafeSettings
from carla_logger import logger
from carla_shared import CARLA_KEY_CUSTOM_PAINTING
from patchcanvas import patchcanvas
from qt_compat import QPoint, QRectF, QTimer, QToolButton, Qt, pyqtSlot


class MiniCanvasMixin:
    # --------------------------------------------------------------------------------------------------------
    # MiniCanvas stuff

    @pyqtSlot()
    def slot_miniCanvasCheckAll(self):
        if self._isModernMiniCanvasMode():
            return
        self.slot_miniCanvasCheckSize()
        self.slot_horizontalScrollBarChanged(
            self.ui.graphicsView.horizontalScrollBar().value()
        )
        self.slot_verticalScrollBarChanged(
            self.ui.graphicsView.verticalScrollBar().value()
        )

    @pyqtSlot()
    def slot_miniCanvasCheckSize(self):
        if self._isModernMiniCanvasMode():
            return
        if self.fCanvasWidth == 0 or self.fCanvasHeight == 0:
            return

        currentIndex = self.ui.tabWidget.currentIndex()

        if currentIndex == 1:
            width = self.ui.graphicsView.width()
            height = self.ui.graphicsView.height()
        else:
            self.ui.tabWidget.blockSignals(True)
            self.ui.tabWidget.setCurrentIndex(1)
            width = self.ui.graphicsView.width()
            height = self.ui.graphicsView.height()
            self.ui.tabWidget.setCurrentIndex(currentIndex)
            self.ui.tabWidget.blockSignals(False)

        self.scene.updateLimits()

        scene_w = self.scene.sceneRect().width() if not self.scene.sceneRect().isNull() and self.scene.sceneRect().width() > 0 else self.fCanvasWidth
        scene_h = self.scene.sceneRect().height() if not self.scene.sceneRect().isNull() and self.scene.sceneRect().height() > 0 else self.fCanvasHeight

        self.ui.miniCanvasPreview.setViewSize(
            float(width) / scene_w, float(height) / scene_h
        )
        widget = self._miniCanvasViewWidget()
        if widget is not None and widget is not self.ui.miniCanvasPreview:
            widget.setViewSize(float(width) / scene_w, float(height) / scene_h)
        self._repositionMiniCanvasFloat()

    def _isModernMiniCanvasMode(self):
        if hasattr(self, "act_settings_modern_ui") and self.act_settings_modern_ui is not None:
            try:
                return bool(self.act_settings_modern_ui.isChecked())
            except Exception:
                return True
        return True

    def _miniCanvasViewWidget(self):
        if self._isModernMiniCanvasMode():
            widget = getattr(self.ui, "modernMiniCanvas", None)
            if widget is not None:
                return widget
        return getattr(self.ui, "miniCanvasPreview", None)

    def _ensureMiniCanvasOverlay(self):
        if getattr(self.ui, "miniCanvasOverlay", None) is not None:
            return self.ui.miniCanvasOverlay
        try:
            from widgets.canvasminimapframe import CanvasMinimapOverlay
            # Anchor the map to the patchbay container (the graphics view's
            # parent), matching the floating toolbars, so it stays put when
            # the view is panned/zoomed/resized.
            overlayParent = self.ui.graphicsView.parentWidget() or self.ui.graphicsView.viewport()
            overlay = CanvasMinimapOverlay(
                overlayParent,
                self.ui.graphicsView,
                self.scene,
                self,
            )
            self.ui.miniCanvasOverlay = overlay
            self.ui.miniCanvasFloatFrame = overlay
            self.ui.modernMiniCanvas = overlay.map
            overlay.visibilityChanged.connect(self._onMiniCanvasVisibilityRequested)
            overlay.dockRequested.connect(self._onMiniCanvasDockRequested)
            overlay.geometryChanged.connect(self._onMiniCanvasGeometryChanged)
            overlay.collapsedChanged.connect(lambda *_: self._saveMiniCanvasState())
            overlay.zoomChanged.connect(lambda *_: self._saveMiniCanvasState())
            return overlay
        except Exception as ex:
            logger.warning("CANVAS", f"Could not create floating minimap overlay: {ex}")
            return None

    def _ensureMiniCanvasRestoreButton(self):
        if getattr(self.ui, "btnShowMiniCanvas", None) is not None:
            return self.ui.btnShowMiniCanvas
        try:
            btnParent = self.ui.graphicsView.parentWidget() or self.ui.graphicsView.viewport()
            btn = QToolButton(btnParent)
            btn.setObjectName("btnShowMiniCanvas")
            btn.setText("\U0001F5FA  Map")
            btn.setToolTip("Show minimap")
            btn.setToolButtonStyle(Qt.ToolButtonTextOnly)
            btn.setAutoRaise(False)
            from styles.theme_manager import theme_manager
            engine = theme_manager.engine
            btn.setStyleSheet(
                "QToolButton { background-color: %s; "
                "border: 1px solid %s; border-radius: 6px; "
                "padding: 2px 8px; color: %s; }"
                % (engine.get_token("bg-surface", "#181825"),
                   engine.get_token("accent-tint-50", "#89b4fa"),
                   engine.get_token("text-primary", "#cdd6f4"))
            )
            btn.clicked.connect(self._showMiniCanvasFloat)
            btn.hide()
            self.ui.btnShowMiniCanvas = btn
            return btn
        except Exception as ex:
            logger.warning("CANVAS", f"Could not create minimap restore button: {ex}")
            return None


    def _updateMiniCanvasPlacement(self):
        if not hasattr(self.ui, "miniCanvasPreview"):
            return

        modern = self._isModernMiniCanvasMode()

        if modern:
            overlay = self._ensureMiniCanvasOverlay()
            self._ensureMiniCanvasRestoreButton()
            if overlay is None:
                return

            # Classic preview is inactive in modern mode.
            try:
                self.ui.miniCanvasPreview.hide()
            except Exception:
                pass

            # Theme sync + (re)bind the scene for the modern widget.
            # Guard so init()'s resetView() does not clobber the saved zoom.
            self._miniCanvasRestoring = True
            try:
                overlay.map.setViewTheme(
                    patchcanvas.canvas.theme.canvas_bg,
                    patchcanvas.canvas.theme.rubberband_brush.color(),
                    patchcanvas.canvas.theme.rubberband_pen.color(),
                )
                overlay.map.init(
                    self.scene,
                    self.fCanvasWidth,
                    self.fCanvasHeight,
                    self.fSavedSettings[CARLA_KEY_CUSTOM_PAINTING],
                )
            except Exception:
                pass
            finally:
                self._miniCanvasRestoring = False

            if hasattr(self.ui, "tw_miniCanvas"):
                try:
                    self.ui.tw_miniCanvas.hide()
                except Exception:
                    pass

            self._expandSceneRectForMinimap()
            self._restoreMiniCanvasState()
            self._repositionMiniCanvasFloat()
            QTimer.singleShot(100, self._repositionMiniCanvasFloat)
            QTimer.singleShot(400, self._repositionMiniCanvasFloat)
        else:
            # Restore the classic sidebar placement.
            if getattr(self.ui, "miniCanvasFloatFrame", None) is not None:
                try:
                    self.ui.miniCanvasPreview.setParent(self.ui.tab_3)
                    if hasattr(self.ui, "verticalLayout_7"):
                        self.ui.verticalLayout_7.addWidget(self.ui.miniCanvasPreview)
                    self.ui.miniCanvasFloatFrame.hide()
                except Exception:
                    pass
            if getattr(self.ui, "btnShowMiniCanvas", None) is not None:
                try:
                    self.ui.btnShowMiniCanvas.hide()
                except Exception:
                    pass
            if getattr(self.ui, "modernMiniCanvas", None) is not None:
                try:
                    self.ui.modernMiniCanvas.hide()
                except Exception:
                    pass
            if hasattr(self.ui, "tw_miniCanvas"):
                try:
                    self.ui.tw_miniCanvas.show()
                except Exception:
                    pass

    def _onMiniCanvasVisibilityRequested(self, visible):
        if visible:
            self._showMiniCanvasFloat()
        else:
            self._hideMiniCanvasFloat()

    def _onMiniCanvasDockRequested(self, mode):
        """Dock the minimap at the top/bottom of the rack list, or undock."""
        overlay = self._ensureMiniCanvasOverlay()
        if overlay is None:
            return
        frame = getattr(self.ui, "frame", None)
        if frame is None:
            return
        old_layout = frame.layout()
        if old_layout is None:
            return

        from qt_compat import QVBoxLayout

        # Restructure the rack frame once: a vertical outer layout with the
        # original horizontal row (pads + list + scrollbar) inside.
        outer = getattr(self, "_rackDockLayout", None)
        if outer is None or outer.parent() is not frame:
            outer = QVBoxLayout(frame)
            outer.setContentsMargins(0, 0, 0, 0)
            outer.setSpacing(2)
            self._rackDockLayout = outer
            inner = getattr(self, "_rackDockInner", None)
            if inner is None:
                from qt_compat import QHBoxLayout
                inner = QHBoxLayout()
                inner.setContentsMargins(0, 0, 0, 0)
                inner.setSpacing(0)
                self._rackDockInner = inner
            items = []
            while old_layout.count():
                items.append(old_layout.takeAt(0))
            for item in items:
                w = item.widget()
                if w is not None:
                    inner.addWidget(w)
                else:
                    inner.addItem(item)
            outer.addLayout(inner)

        overlay.setParent(frame)
        if mode == "top":
            outer.insertWidget(0, overlay)
        elif mode == "bottom":
            outer.addWidget(overlay)
        else:
            # Undock: back to floating over the canvas.
            self._rackDockLayout.removeWidget(overlay)
            overlay.setParent(self.ui.graphicsView.parentWidget() or self.ui.graphicsView.viewport())
            overlay.show()
            overlay.raise_()
            self._repositionMiniCanvasFloat()

        overlay.setDockMode(mode)
        overlay.setVisible(getattr(self, "_miniCanvasUserVisible", True))
        self._saveMiniCanvasState()

    def _onMiniCanvasGeometryChanged(self):
        self._miniCanvasUserPositioned = True
        self._saveMiniCanvasState()

    def _hideMiniCanvasFloat(self):
        overlay = getattr(self.ui, "miniCanvasFloatFrame", None)
        if overlay is not None:
            overlay.hide()
        self._miniCanvasUserVisible = False
        self._repositionMiniCanvasFloat()
        self._saveMiniCanvasState()

    def _showMiniCanvasFloat(self):
        overlay = getattr(self.ui, "miniCanvasFloatFrame", None)
        if overlay is not None:
            overlay.show()
            overlay.raise_()
        self._miniCanvasUserVisible = True
        self._expandSceneRectForMinimap()
        self._repositionMiniCanvasFloat()
        self._saveMiniCanvasState()

    def _restoreMiniCanvasState(self):
        overlay = getattr(self.ui, "miniCanvasFloatFrame", None)
        if overlay is None:
            return
        self._miniCanvasRestoring = True
        try:
            settings = QSafeSettings()
            zoom = settings.value("Minimap/Zoom", 1.0, float)
            collapsed = settings.value("Minimap/Collapsed", False, bool)
            visible = settings.value("Minimap/Visible", True, bool)
            dock = str(settings.value("Minimap/Dock", "float") or "float")
            pos_x = settings.value("Minimap/X", -1, int)
            pos_y = settings.value("Minimap/Y", -1, int)

            overlay.map.setZoom(zoom)
            overlay.toggleCollapsed(collapsed)

            if pos_x >= 0 and pos_y >= 0:
                overlay.move(int(pos_x), int(pos_y))
                self._miniCanvasUserPositioned = True
            else:
                self._miniCanvasUserPositioned = False

            self._miniCanvasUserVisible = bool(visible)
            # Size from the layout hint so the map never opens with a stale
            # or collapsed geometry from a previous session.
            overlay.adjustSize()
            overlay._relayoutFloatButtons()
            if dock in ("top", "bottom"):
                QTimer.singleShot(0, lambda: self._onMiniCanvasDockRequested(dock))
            if visible:
                overlay.show()
            else:
                overlay.hide()
        except Exception as ex:
            logger.warning("CANVAS", f"Could not restore minimap state: {ex}")
        finally:
            self._miniCanvasRestoring = False
        self._saveMiniCanvasState()

    def _saveMiniCanvasState(self):
        if getattr(self, "_miniCanvasRestoring", False):
            return
        overlay = getattr(self.ui, "miniCanvasFloatFrame", None)
        if overlay is None:
            return
        try:
            settings = QSafeSettings()
            if getattr(self, "_miniCanvasUserPositioned", False):
                settings.setValue("Minimap/X", int(overlay.x()))
                settings.setValue("Minimap/Y", int(overlay.y()))
            else:
                settings.setValue("Minimap/X", -1)
                settings.setValue("Minimap/Y", -1)
            settings.setValue("Minimap/Dock", str(overlay.dockMode() if hasattr(overlay, "dockMode") else "float"))
            settings.setValue("Minimap/Zoom", float(overlay.map.getZoom()))
            settings.setValue("Minimap/Collapsed", bool(overlay.isCollapsed()))
            settings.setValue(
                "Minimap/Visible", bool(getattr(self, "_miniCanvasUserVisible", True))
            )
        except Exception as ex:
            logger.warning("CANVAS", f"Could not save minimap state: {ex}")

    def _expandSceneRectForMinimap(self):
        try:
            scene = self.scene
            if scene is None:
                return
            bounds = None
            for item in scene.items():
                if not (hasattr(item, "m_group_id") and hasattr(item, "p_height")):
                    continue
                try:
                    if not item.isVisible():
                        continue
                except Exception:
                    pass
                r = item.sceneBoundingRect()
                bounds = QRectF(r) if bounds is None else bounds.united(r)
            if bounds is None or bounds.isNull():
                return
            margin = 500.0
            needed = bounds.adjusted(-margin, -margin, margin, margin)
            current = scene.sceneRect()
            if not current.isNull() and current.contains(needed):
                return
            expanded = needed if current.isNull() else current.united(needed)
            try:
                patchcanvas.canvas.size_rect = expanded
            except Exception:
                pass
            scene.setSceneRect(expanded)
            try:
                self.ui.graphicsView.setSceneRect(expanded)
            except Exception:
                pass
            if hasattr(scene, "updateLimits"):
                scene.updateLimits()
        except Exception as ex:
            logger.warning("CANVAS", f"Could not expand scene rect for minimap: {ex}")

    def _repositionMiniCanvasFloat(self):
        overlay = getattr(self.ui, "miniCanvasFloatFrame", None)
        if overlay is None:
            return
        try:
            # Position against the overlay's parent (the patchbay container,
            # matching the floating toolbars); fall back to the viewport.
            base = overlay.parentWidget() or self.ui.graphicsView.viewport()
            if overlay.isVisible():
                overlay.adjustSize()
                if getattr(self, "_miniCanvasUserPositioned", False):
                    pos = overlay.pos()
                else:
                    pos = QPoint(
                        base.width() - overlay.width() - 10,
                        base.height() - overlay.height() - 10,
                    )
                max_x = max(0, base.width() - overlay.width())
                max_y = max(0, base.height() - overlay.height())
                pos.setX(max(0, min(pos.x(), max_x)))
                pos.setY(max(0, min(pos.y(), max_y)))
                overlay.move(pos)
                overlay.raise_()

            btn = getattr(self.ui, "btnShowMiniCanvas", None)
            if btn is not None:
                if not overlay.isVisible():
                    btn.move(base.width() - btn.width() - 12, base.height() - btn.height() - 12)
                    btn.raise_()
                    btn.show()
                else:
                    btn.hide()
        except Exception:
            pass

    @pyqtSlot(float, float)
    def slot_miniCanvasMoved(self, xp, yp):
        hsb = self.ui.graphicsView.horizontalScrollBar()
        vsb = self.ui.graphicsView.verticalScrollBar()
        hsb.setValue(xp * hsb.maximum())
        vsb.setValue(yp * vsb.maximum())
        self.updateCanvasInitialPos()

