#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Clara contributors
# SPDX-License-Identifier: GPL-2.0-or-later

# Patchbay canvas setup, menu actions and callbacks, split out of host_app.py.
# HostWindow inherits this mixin.

from carla_app import QSafeSettings
from carla_backend import (
    ENGINE_PROCESS_MODE_CONTINUOUS_RACK,
    MAIN_CARLA_PLUGIN_ID,
    PATCHBAY_ICON_CARLA,
    PATCHBAY_ICON_DISTRHO,
    PATCHBAY_ICON_FILE,
    PATCHBAY_ICON_HARDWARE,
    PATCHBAY_ICON_PLUGIN,
    PATCHBAY_PORT_IS_INPUT,
    PATCHBAY_PORT_TYPE_AUDIO,
    PATCHBAY_PORT_TYPE_CV,
    PATCHBAY_PORT_TYPE_MIDI,
    PLUGIN_HAS_CUSTOM_UI,
    PLUGIN_HAS_INLINE_DISPLAY,
)
from canvas_ui import CanvasViewportFilter, canvasCallback
from carla_logger import logger
from carla_shared import (
    CARLA_DEFAULT_CANVAS_ARRANGE_STYLE,
    CARLA_DEFAULT_CANVAS_LINE_OPACITY,
    CARLA_DEFAULT_CANVAS_LINE_STROKE,
    CARLA_DEFAULT_CANVAS_LINE_STYLE,
    CARLA_DEFAULT_CANVAS_NODE_MIN_WIDTH,
    CARLA_DEFAULT_CANVAS_NODE_RADIUS,
    CARLA_DEFAULT_CANVAS_ROUNDED_NODES,
    CARLA_DEFAULT_CANVAS_SIZE_HEIGHT,
    CARLA_DEFAULT_CANVAS_SIZE_WIDTH,
    CARLA_KEY_CANVAS_ANTIALIASING,
    CARLA_KEY_CANVAS_ARRANGE_STYLE,
    CARLA_KEY_CANVAS_AUTO_HIDE_GROUPS,
    CARLA_KEY_CANVAS_AUTO_SELECT_ITEMS,
    CARLA_KEY_CANVAS_EYE_CANDY,
    CARLA_KEY_CANVAS_FANCY_EYE_CANDY,
    CARLA_KEY_CANVAS_FULL_REPAINTS,
    CARLA_KEY_CANVAS_HQ_ANTIALIASING,
    CARLA_KEY_CANVAS_INLINE_DISPLAYS,
    CARLA_KEY_CANVAS_LINE_OPACITY,
    CARLA_KEY_CANVAS_LINE_STROKE,
    CARLA_KEY_CANVAS_LINE_STYLE,
    CARLA_KEY_CANVAS_NODE_MIN_WIDTH,
    CARLA_KEY_CANVAS_NODE_RADIUS,
    CARLA_KEY_CANVAS_ROUNDED_NODES,
    CARLA_KEY_CANVAS_SHOW_EXTERNAL,
    CARLA_KEY_CANVAS_SIZE,
    CARLA_KEY_CANVAS_THEME,
    CARLA_KEY_CANVAS_USE_BEZIER_LINES,
    CARLA_KEY_CANVAS_USE_OPENGL,
    CARLA_KEY_CUSTOM_PAINTING,
    CARLA_KEY_MAIN_PROJECT_FOLDER,
    log_carla,
)
from patchcanvas import patchcanvas
from qt_compat import (
    QApplication,
    QBuffer,
    QFileDialog,
    QFileInfo,
    QFrame,
    QGraphicsView,
    QIODevice,
    QImage,
    QImageWriter,
    QMimeData,
    QPainter,
    QSplitter,
    QT_VERSION,
    QTimer,
    QVBoxLayout,
    QWidget,
    Qt,
    pyqtSlot,
    qt_config,
)

try:
    from qt_compat import QGLWidget

    hasGL = QGLWidget is not None
except ImportError:
    QGLWidget = None
    hasGL = False


class CanvasMixin:
    # --------------------------------------------------------------------------------------------------------
    # Canvas

    def clearSideStuff(self):
        if self.fWithCanvas:
            self.scene.clearSelection()

        self.fSelectedPlugins = []

        self.ui.keyboard.allNotesOff(False)
        self.ui.scrollArea.setEnabled(False)

        self.fPeaksCleared = True
        self.ui.peak_in.displayMeter(1, 0.0, True)
        self.ui.peak_in.displayMeter(2, 0.0, True)
        self.ui.peak_out.displayMeter(1, 0.0, True)
        self.ui.peak_out.displayMeter(2, 0.0, True)

    def setupCanvas(self):
        pOptions = patchcanvas.options_t()
        pOptions.theme_name = self.fSavedSettings[CARLA_KEY_CANVAS_THEME]
        pOptions.auto_hide_groups = self.fSavedSettings[
            CARLA_KEY_CANVAS_AUTO_HIDE_GROUPS
        ]
        pOptions.auto_select_items = self.fSavedSettings[
            CARLA_KEY_CANVAS_AUTO_SELECT_ITEMS
        ]
        pOptions.use_bezier_lines = self.fSavedSettings[
            CARLA_KEY_CANVAS_USE_BEZIER_LINES
        ]
        pOptions.antialiasing = self.fSavedSettings[CARLA_KEY_CANVAS_ANTIALIASING]
        pOptions.inline_displays = self.fSavedSettings[CARLA_KEY_CANVAS_INLINE_DISPLAYS]
        pOptions.rounded_nodes = self.fSavedSettings.get(
            CARLA_KEY_CANVAS_ROUNDED_NODES, CARLA_DEFAULT_CANVAS_ROUNDED_NODES
        )
        pOptions.node_radius = self.fSavedSettings.get(
            CARLA_KEY_CANVAS_NODE_RADIUS, CARLA_DEFAULT_CANVAS_NODE_RADIUS
        )
        pOptions.node_min_width = self.fSavedSettings.get(
            CARLA_KEY_CANVAS_NODE_MIN_WIDTH, CARLA_DEFAULT_CANVAS_NODE_MIN_WIDTH
        )
        pOptions.line_style = self.fSavedSettings.get(
            CARLA_KEY_CANVAS_LINE_STYLE, CARLA_DEFAULT_CANVAS_LINE_STYLE
        )
        pOptions.line_stroke = self.fSavedSettings.get(
            CARLA_KEY_CANVAS_LINE_STROKE, CARLA_DEFAULT_CANVAS_LINE_STROKE
        )
        pOptions.line_opacity = self.fSavedSettings.get(
            CARLA_KEY_CANVAS_LINE_OPACITY, CARLA_DEFAULT_CANVAS_LINE_OPACITY
        )
        pOptions.arrange_style = self.fSavedSettings.get(
            CARLA_KEY_CANVAS_ARRANGE_STYLE, CARLA_DEFAULT_CANVAS_ARRANGE_STYLE
        )

        if self.fSavedSettings[CARLA_KEY_CANVAS_FANCY_EYE_CANDY]:
            pOptions.eyecandy = patchcanvas.EYECANDY_FULL
        elif self.fSavedSettings[CARLA_KEY_CANVAS_EYE_CANDY]:
            pOptions.eyecandy = patchcanvas.EYECANDY_SMALL
        else:
            pOptions.eyecandy = patchcanvas.EYECANDY_NONE

        pFeatures = patchcanvas.features_t()
        pFeatures.group_info = False
        pFeatures.group_rename = False
        pFeatures.port_info = False
        pFeatures.port_rename = False
        pFeatures.handle_group_pos = False

        patchcanvas.setOptions(pOptions)
        patchcanvas.setFeatures(pFeatures)
        patchcanvas.init("Carla2", self.scene, canvasCallback, False)

        tryCanvasSize = self.fSavedSettings[CARLA_KEY_CANVAS_SIZE].split("x")

        if (
            len(tryCanvasSize) == 2
            and tryCanvasSize[0].isdigit()
            and tryCanvasSize[1].isdigit()
        ):
            self.fCanvasWidth = int(tryCanvasSize[0])
            self.fCanvasHeight = int(tryCanvasSize[1])
        else:
            self.fCanvasWidth = CARLA_DEFAULT_CANVAS_SIZE_WIDTH
            self.fCanvasHeight = CARLA_DEFAULT_CANVAS_SIZE_HEIGHT

        patchcanvas.setCanvasSize(0, 0, self.fCanvasWidth, self.fCanvasHeight)
        patchcanvas.setInitialPos(self.fCanvasWidth / 2, self.fCanvasHeight / 2)
        self.ui.graphicsView.setSceneRect(0, 0, self.fCanvasWidth, self.fCanvasHeight)

        # Setup canvas viewport auto-scrolling & quick disconnect filter
        self.canvasFilter = CanvasViewportFilter(self, self.ui.graphicsView)

        self.ui.miniCanvasPreview.setViewTheme(
            patchcanvas.canvas.theme.canvas_bg,
            patchcanvas.canvas.theme.rubberband_brush.color(),
            patchcanvas.canvas.theme.rubberband_pen.color(),
        )
        self.ui.miniCanvasPreview.init(
            self.scene,
            self.fCanvasWidth,
            self.fCanvasHeight,
            self.fSavedSettings[CARLA_KEY_CUSTOM_PAINTING],
        )

        # Resolve minimap placement only after the preview is initialized.
        self._updateMiniCanvasPlacement()

        if (
            self.fSavedSettings[CARLA_KEY_CANVAS_ANTIALIASING]
            != patchcanvas.ANTIALIASING_NONE
        ):
            self.ui.graphicsView.setRenderHint(QPainter.Antialiasing, True)

            fullAA = (
                self.fSavedSettings[CARLA_KEY_CANVAS_ANTIALIASING]
                == patchcanvas.ANTIALIASING_FULL
            )
            self.ui.graphicsView.setRenderHint(QPainter.SmoothPixmapTransform, fullAA)
            self.ui.graphicsView.setRenderHint(QPainter.TextAntialiasing, fullAA)

            hq_aa_attr = getattr(QPainter.RenderHint, "HighQualityAntialiasing", getattr(QPainter, "HighQualityAntialiasing", None)) if hasattr(QPainter, "RenderHint") else getattr(QPainter, "HighQualityAntialiasing", None)
            if (
                self.fSavedSettings[CARLA_KEY_CANVAS_USE_OPENGL]
                and hasGL
                and hq_aa_attr is not None
            ):
                self.ui.graphicsView.setRenderHint(
                    hq_aa_attr,
                    self.fSavedSettings[CARLA_KEY_CANVAS_HQ_ANTIALIASING],
                )

        else:
            self.ui.graphicsView.setRenderHint(QPainter.Antialiasing, False)

        if self.fSavedSettings[CARLA_KEY_CANVAS_FULL_REPAINTS]:
            self.ui.graphicsView.setViewportUpdateMode(QGraphicsView.FullViewportUpdate)
        else:
            smart_mode = getattr(QGraphicsView, "SmartViewportUpdate", None)
            if smart_mode is None and hasattr(QGraphicsView, "ViewportUpdateMode"):
                smart_mode = getattr(QGraphicsView.ViewportUpdateMode, "SmartViewportUpdate", None)
            if smart_mode is not None:
                self.ui.graphicsView.setViewportUpdateMode(smart_mode)
            else:
                self.ui.graphicsView.setViewportUpdateMode(
                    QGraphicsView.MinimalViewportUpdate
                )

        # Store painter state is not needed here and costs us fairly big, so skip it.
        try:
            self.ui.graphicsView.setOptimizationFlag(
                QGraphicsView.DontSavePainterState, True
            )
        except Exception:
            pass

        # Do not inflate update rects for antialiasing; keeps scroll repaints small.
        try:
            self.ui.graphicsView.setOptimizationFlag(
                QGraphicsView.DontAdjustForAntialiasing, True
            )
        except Exception:
            pass

        # The scene paints an opaque background, so tell Qt not to erase first.
        try:
            self.ui.graphicsView.viewport().setAttribute(Qt.WA_OpaquePaintEvent, True)
        except Exception:
            pass

        # Report which viewport we ended up with, so it is obvious from the log
        # whether the patchbay is GPU-accelerated or software-rendered.
        try:
            vp = self.ui.graphicsView.viewport()
            is_gl = "GL" in type(vp).__name__.upper()
            logger.debug(
                "CANVAS",
                "viewport: %s (%s), %s, OpenGL=%s/%s"
                % (
                    "OpenGL" if is_gl else "Software raster",
                    type(vp).__name__,
                    self.ui.graphicsView.viewportUpdateMode(),
                    self.fSavedSettings.get(CARLA_KEY_CANVAS_USE_OPENGL),
                    hasGL,
                ),
            )
        except Exception:
            pass

        # The grid background is static between zoom changes, so let Qt cache it
        # instead of repainting every dot on each drag/pan frame.
        try:
            cache_bg = getattr(QGraphicsView, "CacheBackground", None)
            if cache_bg is None and hasattr(QGraphicsView, "CacheModeFlag"):
                cache_bg = getattr(QGraphicsView.CacheModeFlag, "CacheBackground", None)
            if cache_bg is not None:
                self.ui.graphicsView.setCacheMode(cache_bg)
        except Exception:
            pass

    def updateCanvasInitialPos(self):
        x = self.ui.graphicsView.horizontalScrollBar().value() + self.width() / 4
        y = self.ui.graphicsView.verticalScrollBar().value() + self.height() / 4
        patchcanvas.setInitialPos(x, y)

    def updateMiniCanvasLater(self):
        if hasattr(self, "_miniCanvasTimer"):
            self._miniCanvasTimer.start(self.fMiniCanvasUpdateTimeout)
        else:
            self._doUpdateMiniCanvas()

    def _doUpdateMiniCanvas(self):
        if self._isModernMiniCanvasMode():
            self._expandSceneRectForMinimap()
            if hasattr(self.ui, "modernMiniCanvas") and self.ui.modernMiniCanvas is not None:
                self.ui.modernMiniCanvas.update()
            return
        if hasattr(self.ui, "miniCanvasPreview") and self.ui.miniCanvasPreview is not None:
            self.ui.miniCanvasPreview.update()

    # --------------------------------------------------------------------------------------------------------
    # Canvas (menu actions)

    @pyqtSlot()
    def slot_canvasShowInternal(self):
        self.fExternalPatchbay = False
        QSafeSettings("falkTX", "Carla2").setValue(CARLA_KEY_CANVAS_SHOW_EXTERNAL, False)
        self.ui.act_canvas_show_internal.blockSignals(True)
        self.ui.act_canvas_show_external.blockSignals(True)
        self.ui.act_canvas_show_internal.setChecked(True)
        self.ui.act_canvas_show_external.setChecked(False)
        self.ui.act_canvas_show_internal.blockSignals(False)
        self.ui.act_canvas_show_external.blockSignals(False)
        self.slot_canvasRefresh()

    @pyqtSlot()
    def slot_canvasShowExternal(self):
        self.fExternalPatchbay = True
        QSafeSettings("falkTX", "Carla2").setValue(CARLA_KEY_CANVAS_SHOW_EXTERNAL, True)
        self.ui.act_canvas_show_internal.blockSignals(True)
        self.ui.act_canvas_show_external.blockSignals(True)
        self.ui.act_canvas_show_internal.setChecked(False)
        self.ui.act_canvas_show_external.setChecked(True)
        self.ui.act_canvas_show_internal.blockSignals(False)
        self.ui.act_canvas_show_external.blockSignals(False)
        self.slot_canvasRefresh()

    @pyqtSlot()
    def slot_canvasArrange(self):
        patchcanvas.arrange()
        self.updateMiniCanvasLater()

    @pyqtSlot()
    def slot_canvasRefresh(self):
        patchcanvas.clear()
        # a full refresh re-enumerates every client, so no id stays filtered from the old pass
        self.fFilteredPatchbayClients.clear()

        if (
            self.host.processMode == ENGINE_PROCESS_MODE_CONTINUOUS_RACK
            and self.host.isPlugin
        ):
            return

        if self.host.is_engine_running():
            self.host.patchbay_refresh(self.fExternalPatchbay)

        self.updateMiniCanvasLater()

    @pyqtSlot()
    def slot_canvasZoomFit(self):
        self.scene.zoom_fit()

    @pyqtSlot()
    def slot_canvasZoomIn(self):
        self.scene.zoom_in()

    @pyqtSlot()
    def slot_canvasZoomOut(self):
        self.scene.zoom_out()

    @pyqtSlot()
    def slot_canvasZoomReset(self):
        self.scene.zoom_reset()

    def _canvasImageRender(self, zoom=1.0):
        img_format = (
            QImage.Format.Format_RGB32 if qt_config == 6 else QImage.Format_RGB32
        )
        image = QImage(
            self.scene.width() * zoom, self.scene.height() * zoom, img_format
        )
        painter = QPainter(image)
        painter.save()
        painter.setRenderHints(
            painter.renderHints() | QPainter.Antialiasing | QPainter.TextAntialiasing
        )
        self.scene.clearSelection()
        self.scene.render(painter)
        painter.restore()
        del painter
        return image

    def _canvasImageWrite(self, iw: QImageWriter, imgFormat: bytes, image: QImage):
        iw.setFormat(imgFormat)
        iw.setCompression(-1)
        if QT_VERSION >= 0x50500:
            iw.setOptimizedWrite(True)
        iw.write(image)

    @pyqtSlot()
    def slot_canvasSaveImage(self):
        if self.fProjectFilename:
            dir = QFileInfo(self.fProjectFilename).absoluteDir().absolutePath()
        else:
            dir = self.fSavedSettings[CARLA_KEY_MAIN_PROJECT_FOLDER]

        fileDialog = QFileDialog(self)
        fileDialog.setAcceptMode(QFileDialog.AcceptSave)
        fileDialog.setDirectory(dir)
        fileDialog.setFileMode(QFileDialog.AnyFile)
        fileDialog.setMimeTypeFilters(("image/png", "image/jpeg"))
        fileDialog.setNameFilter(self.tr("Images (*.png *.jpg)"))
        fileDialog.setOptions(QFileDialog.DontUseCustomDirectoryIcons)
        fileDialog.setWindowTitle(self.tr("Save Image"))

        ok = fileDialog.exec_()

        if not ok:
            return

        newPath = fileDialog.selectedFiles()

        if len(newPath) != 1:
            return

        newPath = newPath[0]

        if QT_VERSION >= 0x50900:
            if fileDialog.selectedMimeTypeFilter() == "image/jpeg":
                imgFormat = b"JPG"
            else:
                imgFormat = b"PNG"
        else:
            if newPath.lower().endswith((".jpg", ".jpeg")):
                imgFormat = b"JPG"
            else:
                imgFormat = b"PNG"

        sender = self.sender()
        if sender == self.ui.act_canvas_save_image_2x:
            zoom = 2.0
        elif sender == self.ui.act_canvas_save_image_4x:
            zoom = 4.0
        else:
            zoom = 1.0

        image = self._canvasImageRender(zoom)
        iw = QImageWriter(newPath)
        self._canvasImageWrite(iw, imgFormat, image)

    @pyqtSlot()
    def slot_canvasCopyToClipboard(self):
        buffer = QBuffer()
        buffer.open(QIODevice.WriteOnly)

        image = self._canvasImageRender()
        iw = QImageWriter(buffer, b"PNG")
        self._canvasImageWrite(iw, b"PNG", image)

        buffer.close()

        mimeData = QMimeData()
        mimeData.setData("image/png", buffer.buffer())
        QApplication.clipboard().setMimeData(mimeData)

    # --------------------------------------------------------------------------------------------------------
    # Canvas (canvas callbacks)

    @pyqtSlot()
    def slot_canvasSelectionChanged(self):
        self.updateMiniCanvasLater()

    @pyqtSlot(float)
    def slot_canvasScaleChanged(self, scale):
        self.ui.miniCanvasPreview.setViewScale(scale)
        widget = self._miniCanvasViewWidget()
        if widget is not None and widget is not self.ui.miniCanvasPreview:
            widget.setViewScale(scale)

    @pyqtSlot(list)
    def slot_canvasPluginSelected(self, pluginList):
        self.ui.keyboard.allNotesOff(False)
        self.ui.scrollArea.setEnabled(len(pluginList) != 0)  # and self.fPluginCount > 0
        self.fSelectedPlugins = pluginList

        # Synchronize selection to Rack only if rack is visible (e.g. in dual-view)
        is_split = hasattr(self, "tabSplit") and self.ui.tabWidget.indexOf(self.tabSplit) == self.ui.tabWidget.currentIndex()
        if is_split and pluginList and len(pluginList) > 0 and self.ui.listWidget is not None:
            firstPluginId = pluginList[0]
            if 0 <= firstPluginId < len(self.fPluginList):
                pitem = self.fPluginList[firstPluginId]
                if pitem is not None:
                    try:
                        self._sync_guard = getattr(self, "_sync_guard", False)
                        if not self._sync_guard:
                            self._sync_guard = True
                            self.ui.listWidget.setCurrentItem(pitem)
                            if hasattr(self.ui.listWidget, "scrollToItemSmooth"):
                                self.ui.listWidget.scrollToItemSmooth(pitem)
                            else:
                                self.ui.listWidget.scrollToItem(pitem)
                    finally:
                        self._sync_guard = False

    @pyqtSlot()
    def slot_rackItemClicked(self, item=None):
        if getattr(self, "_sync_guard", False):
            return
        if item is None and self.ui.listWidget is not None:
            item = self.ui.listWidget.currentItem()
        if item is not None and hasattr(item, "getPluginId"):
            pluginId = item.getPluginId()
            if pluginId >= 0:
                try:
                    self._sync_guard = True
                    patchcanvas.focusGroupUsingPluginId(pluginId)
                finally:
                    self._sync_guard = False

    @pyqtSlot()
    def slot_rackSelectionChanged(self):
        if getattr(self, "_sync_guard", False):
            return
        if self.ui.listWidget is not None:
            item = self.ui.listWidget.currentItem()
            if item is not None and hasattr(item, "getPluginId"):
                pluginId = item.getPluginId()
                if pluginId >= 0:
                    try:
                        self._sync_guard = True
                        patchcanvas.focusGroupUsingPluginId(pluginId)
                    finally:
                        self._sync_guard = False

    @pyqtSlot(bool)
    def slot_toggleSideBySideView(self, enabled, refresh=True):
        if not hasattr(self, "tabSplit"):
            self.tabSplit = QWidget(self.ui.tabWidget)
            self.splitLayout = QVBoxLayout(self.tabSplit)
            self.splitLayout.setContentsMargins(0, 0, 0, 0)
            self.splitLayout.setSpacing(0)

            self.splitter = QSplitter(Qt.Horizontal, self.tabSplit)
            self.splitter.setChildrenCollapsible(False)
            self.splitLayout.addWidget(self.splitter)

        is_modern = getattr(self, "act_settings_modern_ui", None) is not None and self.act_settings_modern_ui.isChecked()

        if enabled:
            # Dynamically reparent patchbay and rack into the splitter
            self.splitter.addWidget(self.ui.patchbay)
            self.splitter.addWidget(self.ui.rack)
            self.ui.rack.setMinimumWidth(self.ui.listWidget.minimumWidth() if hasattr(self.ui, "listWidget") and self.ui.listWidget is not None else 200)
            self.ui.patchbay.show()
            self.ui.rack.show()

            # Set split proportion: 65% Patchbay Canvas, 35% Rack
            w = max(self.width(), 1000)
            self.splitter.setSizes([int(w * 0.65), int(w * 0.35)])

            # In Modern mode, remove the logs tab from central tabWidget
            if is_modern:
                logs_idx = self.ui.tabWidget.indexOf(self.ui.logs)
                if logs_idx != -1:
                    self.ui.tabWidget.removeTab(logs_idx)

                # Only apply custom flush styling if not using system desktop theme
                from styles.theme_manager import theme_manager
                if not theme_manager.is_using_system():
                    bg_hex = "#181825"
                    if hasattr(patchcanvas, "theme") and hasattr(patchcanvas.theme, "canvas_bg"):
                        bg_hex = patchcanvas.theme.canvas_bg.name()

                    self.splitter.setStyleSheet(f"""
                        QSplitter {{
                            background: {bg_hex};
                        }}
                        QSplitter::handle {{
                            background-color: #313244;
                            width: 1px;
                        }}
                        QSplitter::handle:hover {{
                            background-color: #89b4fa;
                            width: 3px;
                        }}
                    """)
                    self.ui.tabWidget.setStyleSheet(f"""
                        QTabWidget::pane {{
                            border: none;
                            background-color: {bg_hex};
                            margin: 0px;
                            padding: 0px;
                        }}
                    """)
                    self.ui.frame.setFrameShape(QFrame.NoFrame)
                    self.ui.frame.setStyleSheet(f"QFrame#frame {{ background-color: {bg_hex}; border: none; }}")
                    self.ui.rack.setStyleSheet(f"QWidget#rack {{ background-color: {bg_hex}; border: none; }}")
                    self.ui.patchbay.setStyleSheet(f"QWidget#patchbay {{ background-color: {bg_hex}; border: none; }}")
                    self.ui.graphicsView.setStyleSheet("QGraphicsView { border: none; outline: none; }")
                    self.ui.listWidget.setStyleSheet(f"""
                        QListWidget {{
                            background-color: {bg_hex};
                            border: none;
                            outline: none;
                            padding: 4px;
                        }}
                        QListWidget::item {{
                            background: transparent;
                            border: none;
                            margin-bottom: 5px;
                        }}
                        QListWidget::item:selected {{
                            background: transparent;
                            border: none;
                        }}
                    """)
                else:
                    self.splitter.setStyleSheet("")
                    self.ui.tabWidget.setStyleSheet("")
                    self.ui.frame.setFrameShape(QFrame.StyledPanel)
                    self.ui.frame.setStyleSheet("")
                    self.ui.rack.setStyleSheet("")
                    self.ui.patchbay.setStyleSheet("")
                    self.ui.graphicsView.setStyleSheet("")
                    self.ui.listWidget.setStyleSheet("")
            else:
                self.splitter.setStyleSheet("")
                self.ui.tabWidget.setStyleSheet("")
                self.ui.frame.setFrameShape(QFrame.StyledPanel)
                self.ui.frame.setStyleSheet("")
                self.ui.rack.setStyleSheet("")
                self.ui.patchbay.setStyleSheet("")
                self.ui.graphicsView.setStyleSheet("")
                self.ui.listWidget.setStyleSheet("")

            splitTabIndex = self.ui.tabWidget.indexOf(self.tabSplit)
            if splitTabIndex == -1:
                self.ui.tabWidget.insertTab(2, self.tabSplit, self.tr("Patchbay + Rack"))
                splitTabIndex = self.ui.tabWidget.indexOf(self.tabSplit)

            self.ui.tabWidget.setCurrentIndex(splitTabIndex)

            # In Modern mode, patchbay+rack is the primary unified workspace; hide the tab bar
            if is_modern:
                self.ui.tabWidget.tabBar().hide()
            else:
                self.ui.tabWidget.tabBar().show()

            self.ui.graphicsView.setFocus()
            if refresh:
                self.slot_canvasRefresh()
        else:
            self.splitter.setStyleSheet("")
            self.ui.tabWidget.setStyleSheet("")
            self.ui.frame.setFrameShape(QFrame.StyledPanel)
            self.ui.frame.setStyleSheet("")
            self.ui.rack.setStyleSheet("")
            self.ui.patchbay.setStyleSheet("")
            self.ui.graphicsView.setStyleSheet("")

            # Restore patchbay and rack into their standalone tab positions
            self.ui.tabWidget.insertTab(0, self.ui.rack, self.tr("Rack"))
            self.ui.tabWidget.insertTab(1, self.ui.patchbay, self.tr("Patchbay"))

            splitTabIndex = self.ui.tabWidget.indexOf(self.tabSplit)
            if splitTabIndex != -1:
                self.ui.tabWidget.removeTab(splitTabIndex)

            # Restore logs tab if missing
            if self.ui.tabWidget.indexOf(self.ui.logs) == -1:
                # If logs was moved to a dialog, reparent it back
                if hasattr(self, "_logsDialog") and self._logsDialog is not None:
                    self._logsDialog.hide()
                    self.ui.logs.setParent(self.ui.tabWidget)
                self.ui.tabWidget.addTab(self.ui.logs, self.tr("Log"))

            self.ui.tabWidget.tabBar().show()
            self.ui.tabWidget.setCurrentIndex(1)
            self.ui.graphicsView.setFocus()
            if refresh:
                self.slot_canvasRefresh()

    # --------------------------------------------------------------------------------------------------------
    # Canvas (host callbacks)

    # Names matching any of these tokens are pure peak-detect observers (ours or
    # third-party like pavucontrol / pwvucontrol) and must not clutter the canvas.
    _PATCHBAY_HIDDEN_NAME_TOKENS = (
        "clarameter",
        "clara meters",
        "peak-detect",
        "peak detect",
        "pavucontrol",
        "pwvucontrol",
        "pw-record",
    )

    def _findGhost(self, name):
        for ghost in getattr(patchcanvas.canvas, "ghost_list", []):
            if ghost.m_group_name == name:
                return ghost
        return None

    def _hideGroupForGhost(self, name, group):
        """Keep the real box hidden while its ports arrive; the ghost covers the build."""
        ghost = self._findGhost(name)
        if ghost is None or not group or not group.widgets:
            return
        if not ghost.bind(group):
            # ghost and real group disagree: invalidate the ghost instead of hiding the node
            patchcanvas.removeGhostGroup(name)
            return
        for widget in group.widgets:
            if widget is None:
                continue
            try:
                widget.setVisible(False)
                widget._ghost_hidden = True
            except RuntimeError:
                pass
        QTimer.singleShot(1500, lambda: self._revealGhost(name))

    @staticmethod
    def _stopWidgetFade(widget):
        for animation in list(getattr(patchcanvas.canvas, "animation_list", [])):
            try:
                if animation.item() is widget:
                    animation.forceStop()
                    patchcanvas.canvas.animation_list.remove(animation)
            except (ValueError, RuntimeError):
                pass
        try:
            widget.setOpacity(1.0)
            if hasattr(widget, "setShadowOpacity"):
                widget.setShadowOpacity(1.0)
        except RuntimeError:
            pass

    def _revealGhost(self, name):
        group = next((g for g in patchcanvas.canvas.group_list if g.group_name == name), None)
        if group is not None:
            for widget in group.widgets:
                if widget is None or not getattr(widget, "_ghost_hidden", False):
                    continue
                try:
                    delattr(widget, "_ghost_hidden")
                    has_ports = bool(getattr(widget, "m_port_list_ids", []))
                    if has_ports or not getattr(patchcanvas.options, "auto_hide_groups", False):
                        self._stopWidgetFade(widget)
                        widget.setVisible(True)
                    widget.update()
                except RuntimeError:
                    pass
        if group is not None:
            for port in list(patchcanvas.canvas.port_list):
                if port.group_id == group.group_id and port.widget is not None:
                    self._stopWidgetFade(port.widget)
                    try:
                        patchcanvas.snapGhostCables(
                            group.group_name, port.port_name,
                            port.widget.sceneBoundingRect().center(),
                        )
                    except RuntimeError:
                        pass
        patchcanvas.removeGhostGroup(name)

    def _maybeRevealGhost(self, clientId):
        group = next((g for g in patchcanvas.canvas.group_list if g.group_id == clientId), None)
        if group is None:
            return
        ghost = self._findGhost(group.group_name)
        if ghost is None:
            return
        expected = len(ghost.m_left) + len(ghost.m_right)
        if expected <= 0:
            # project saved before port names were recorded: give the box a moment to fill
            QTimer.singleShot(200, lambda: self._revealGhost(group.group_name))
            return
        count = sum(1 for p in patchcanvas.canvas.port_list if p.group_id == clientId)
        if count < expected:
            return
        self._revealGhost(group.group_name)

    def _revealAllGhostHidden(self):
        for group in list(patchcanvas.canvas.group_list):
            for widget in group.widgets:
                if widget is None or not getattr(widget, "_ghost_hidden", False):
                    continue
                try:
                    delattr(widget, "_ghost_hidden")
                    if getattr(widget, "m_port_list_ids", []) or not getattr(patchcanvas.options, "auto_hide_groups", False):
                        self._stopWidgetFade(widget)
                        widget.setVisible(True)
                    widget.update()
                except RuntimeError:
                    pass

    def _centerCanvasOnGroup(self, group):
        """While a project loads, pan the canvas to the node that was just created."""
        try:
            if getattr(self, "fUserPannedCanvas", False):
                return
            if not self.fWithCanvas or not group or not group.widgets:
                return
            box = group.widgets[0]
            view = getattr(self.ui, "graphicsView", None)
            if view is None or box is None or box.scene() is None:
                return
            viewport = view.viewport()
            if viewport is None:
                return
            current = view.mapToScene(viewport.rect().center())
            last = getattr(self, "_lastAutoCenter", None)
            if last is not None and (current - last).manhattanLength() > 200.0:
                self.fUserPannedCanvas = True
                return
            view.centerOn(box)
            self._lastAutoCenter = view.mapToScene(viewport.rect().center())
        except Exception:
            pass

    def _isHiddenPatchbayClientName(self, clientName):
        if not clientName:
            return False
        low = clientName.lower()
        return any(token in low for token in self._PATCHBAY_HIDDEN_NAME_TOKENS)

    @pyqtSlot(int, int, int, str)
    def slot_handlePatchbayClientAddedCallback(
        self, clientId, clientIcon, pluginId, clientName
    ):
        log_carla(
            f"host_app: slot_handlePatchbayClientAddedCallback clientId={clientId}, clientIcon={clientIcon}, pluginId={pluginId}, clientName='{clientName}'",
            level="debug"
        )
        if self._isHiddenPatchbayClientName(clientName):
            self.fFilteredPatchbayClients.add(clientId)
            return
        # The engine reuses client ids without always sending a removal first (for
        # example a pw-record capture client disappears and its id is given to a
        # plugin). Never let a stale filtered id hide a real client's ports.
        self.fFilteredPatchbayClients.discard(clientId)
        pcSplit = patchcanvas.SPLIT_UNDEF
        pcIcon = patchcanvas.ICON_APPLICATION

        if clientIcon == PATCHBAY_ICON_PLUGIN:
            pcIcon = patchcanvas.ICON_PLUGIN
        if clientIcon == PATCHBAY_ICON_HARDWARE:
            pcIcon = patchcanvas.ICON_HARDWARE
        elif clientIcon == PATCHBAY_ICON_CARLA:
            pass
        elif clientIcon == PATCHBAY_ICON_DISTRHO:
            pcIcon = patchcanvas.ICON_DISTRHO
        elif clientIcon == PATCHBAY_ICON_FILE:
            pcIcon = patchcanvas.ICON_FILE

        group_dict = patchcanvas.bindGroupShell(clientName, clientId, pluginId)
        if group_dict is None:
            group_dict = patchcanvas.addGroup(clientId, clientName, pcSplit, pcIcon)
        if getattr(self, "fIsProjectLoading", False):
            self._centerCanvasOnGroup(group_dict)
            if group_dict is not None and not getattr(group_dict.widgets[0], "_shell", False):
                self._hideGroupForGhost(clientName, group_dict)

        self.updateMiniCanvasLater()

        if pluginId < 0:
            return

        if pluginId == MAIN_CARLA_PLUGIN_ID:
            hasCustomUI = False
            hasInlineDisplay = False
            patchcanvas.setGroupAsPlugin(
                clientId, pluginId, hasCustomUI, hasInlineDisplay
            )
        else:
            try:
                hints = self.host.get_plugin_info(pluginId)["hints"]
                hasCustomUI = bool(hints & PLUGIN_HAS_CUSTOM_UI)
                hasInlineDisplay = bool(hints & PLUGIN_HAS_INLINE_DISPLAY)
                patchcanvas.setGroupAsPlugin(
                    clientId, pluginId, hasCustomUI, hasInlineDisplay
                )
                pitem = self.getPluginItem(pluginId)
                if pitem and pitem.getWidget():
                    sc = getattr(pitem.getWidget(), "fSkinColor", None)
                    if sc and sc not in ((40, 40, 40), (255, 255, 255)):
                        hex_col = f"#{sc[0]:02x}{sc[1]:02x}{sc[2]:02x}"
                        for group in patchcanvas.canvas.group_list:
                            if getattr(group, "plugin_id", -1) == pluginId:
                                for w in getattr(group, "widgets", []):
                                    if w is not None:
                                        w.setCustomColor(hex_col, notify=False)
                                break
            except Exception as e:
                log_carla(f"Error mapping plugin to canvas client: {clientName} {e}", level="debug")
                return

    @pyqtSlot(int)
    def slot_handlePatchbayClientRemovedCallback(self, clientId):
        if clientId in self.fFilteredPatchbayClients:
            self.fFilteredPatchbayClients.discard(clientId)
            return
        if any(group.group_id == clientId for group in patchcanvas.canvas.group_list):
            patchcanvas.removeGroup(clientId)
        self.updateMiniCanvasLater()

    @pyqtSlot(int, str)
    def slot_handlePatchbayClientRenamedCallback(self, clientId, newClientName):
        if clientId in self.fFilteredPatchbayClients or self._isHiddenPatchbayClientName(newClientName):
            self.fFilteredPatchbayClients.add(clientId)
            return
        patchcanvas.renameGroup(clientId, newClientName)
        self.updateMiniCanvasLater()

    @pyqtSlot(int, int, int)
    def slot_handlePatchbayClientDataChangedCallback(
        self, clientId, clientIcon, pluginId
    ):
        if clientId in self.fFilteredPatchbayClients:
            return
        pcIcon = patchcanvas.ICON_APPLICATION

        if clientIcon == PATCHBAY_ICON_PLUGIN:
            pcIcon = patchcanvas.ICON_PLUGIN
        if clientIcon == PATCHBAY_ICON_HARDWARE:
            pcIcon = patchcanvas.ICON_HARDWARE
        elif clientIcon == PATCHBAY_ICON_CARLA:
            pass
        elif clientIcon == PATCHBAY_ICON_DISTRHO:
            pcIcon = patchcanvas.ICON_DISTRHO
        elif clientIcon == PATCHBAY_ICON_FILE:
            pcIcon = patchcanvas.ICON_FILE

        patchcanvas.setGroupIcon(clientId, pcIcon)
        self.updateMiniCanvasLater()

        if pluginId < 0:
            return

        if pluginId == MAIN_CARLA_PLUGIN_ID:
            hasCustomUI = False
            hasInlineDisplay = False
            patchcanvas.setGroupAsPlugin(
                clientId, pluginId, hasCustomUI, hasInlineDisplay
            )
        else:
            try:
                hints = self.host.get_plugin_info(pluginId)["hints"]
                hasCustomUI = bool(hints & PLUGIN_HAS_CUSTOM_UI)
                hasInlineDisplay = bool(hints & PLUGIN_HAS_INLINE_DISPLAY)
                patchcanvas.setGroupAsPlugin(
                    clientId, pluginId, hasCustomUI, hasInlineDisplay
                )
            except Exception:
                return

    @pyqtSlot(int, int, int, int, int)
    def slot_handlePatchbayClientPositionChangedCallback(
        self, clientId, x1, y1, x2, y2
    ):
        if clientId in self.fFilteredPatchbayClients:
            return
        if (x1 != 0 and x2 != 0) or (y1 != 0 and y2 != 0):
            patchcanvas.splitGroup(clientId)
        else:
            patchcanvas.joinGroup(clientId)
        patchcanvas.setGroupPosFull(clientId, x1, y1, x2, y2)
        self.updateMiniCanvasLater()

    @pyqtSlot(int, int, int, int, str)
    def slot_handlePatchbayPortAddedCallback(
        self, clientId, portId, portFlags, portGroupId, portName
    ):
        log_carla(
            f"host_app: slot_handlePatchbayPortAddedCallback clientId={clientId}, portId={portId}, name='{portName}'",
            level="debug"
        )
        if clientId in self.fFilteredPatchbayClients:
            return
        if portFlags & PATCHBAY_PORT_IS_INPUT:
            portMode = patchcanvas.PORT_MODE_INPUT
        else:
            portMode = patchcanvas.PORT_MODE_OUTPUT

        if portFlags & PATCHBAY_PORT_TYPE_AUDIO:
            portType = patchcanvas.PORT_TYPE_AUDIO_JACK
            isAlternate = False
        elif portFlags & PATCHBAY_PORT_TYPE_CV:
            portType = patchcanvas.PORT_TYPE_PARAMETER
            isAlternate = False
        elif portFlags & PATCHBAY_PORT_TYPE_MIDI:
            portType = patchcanvas.PORT_TYPE_MIDI_JACK
            isAlternate = False
        else:
            portType = patchcanvas.PORT_TYPE_NULL
            isAlternate = False

        patchcanvas.addPort(clientId, portId, portName, portMode, portType, isAlternate)
        if getattr(self, "fIsProjectLoading", False):
            self._maybeRevealGhost(clientId)
            try:
                group = next((g for g in patchcanvas.canvas.group_list if g.group_id == clientId), None)
                port = next((p for p in patchcanvas.canvas.port_list if p.group_id == clientId and p.port_id == portId), None)
                if group is not None and port is not None and port.widget is not None:
                    patchcanvas.snapGhostCables(
                        group.group_name, port.port_name,
                        port.widget.sceneBoundingRect().center(),
                    )
            except RuntimeError:
                pass
        self.updateMiniCanvasLater()

    @pyqtSlot(int, int)
    def slot_handlePatchbayPortRemovedCallback(self, groupId, portId):
        if groupId in self.fFilteredPatchbayClients:
            return
        patchcanvas.removePort(groupId, portId)
        self.updateMiniCanvasLater()

    @pyqtSlot(int, int, int, int, str)
    def slot_handlePatchbayPortChangedCallback(
        self, groupId, portId, portFlags, portGroupId, newPortName
    ):
        if groupId in self.fFilteredPatchbayClients:
            return
        patchcanvas.renamePort(groupId, portId, newPortName)
        self.updateMiniCanvasLater()

    @pyqtSlot(int, int, int, str)
    def slot_handlePatchbayPortGroupAddedCallback(
        self, groupId, portId, portGroupId, newPortName
    ):
        # TODO
        pass

    @pyqtSlot(int, int)
    def slot_handlePatchbayPortGroupRemovedCallback(self, groupId, portId):
        # TODO
        pass

    @pyqtSlot(int, int, int, str)
    def slot_handlePatchbayPortGroupChangedCallback(
        self, groupId, portId, portGroupId, newPortName
    ):
        # TODO
        pass

    @pyqtSlot(int, int, int, int, int)
    def slot_handlePatchbayConnectionAddedCallback(
        self, connectionId, groupOutId, portOutId, groupInId, portInId
    ):
        if groupOutId in self.fFilteredPatchbayClients or groupInId in self.fFilteredPatchbayClients:
            return
        self.fConnections[connectionId] = (groupOutId, portOutId, groupInId, portInId)
        if not patchcanvas.bindShellConnection(connectionId, groupOutId, portOutId, groupInId, portInId):
            patchcanvas.connectPorts(
                connectionId, groupOutId, portOutId, groupInId, portInId
            )
        if getattr(self, "fLoadingDialog", None) is not None:
            self.fLoadingDialog.setDetail("Restoring audio/MIDI graph routing connections...")
        self.updateMiniCanvasLater()

    @pyqtSlot(int, int, int)
    def slot_handlePatchbayConnectionRemovedCallback(
        self, connectionId, portOutId, portInId
    ):
        if self.fConnections.pop(connectionId, None) is None:
            return
        patchcanvas.disconnectPorts(connectionId)
        self.updateMiniCanvasLater()

