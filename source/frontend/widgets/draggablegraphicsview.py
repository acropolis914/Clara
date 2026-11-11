#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2011-2025 Filipe Coelho <falktx@falktx.com>
# SPDX-License-Identifier: GPL-2.0-or-later

# ---------------------------------------------------------------------------------------------------------------------
# Imports (Global)

import os

from qt_compat import (
    Qt,
    QT_VERSION,
    QEvent,
    pyqtSignal,
    QCursor,
    QMouseEvent,
    QKeySequence,
    QShortcut,
    QGraphicsItem,
    QGraphicsView,
    QMessageBox,
    QListWidget,
    QListWidgetItem,
    QRectF,
    QPoint,
    QPointF,
    QEasingCurve,
    QVariantAnimation,
)

# ---------------------------------------------------------------------------------------------------------------------
# Imports (Custom Stuff)

from carla_backend import CARLA_OS_MAC
from carla_shared import CustomMessageBox, gCarla

# Modal Tool Constants
TOOL_POINTER = 0   # Default mode (Q / Esc)
TOOL_SELECT  = 1   # Marquee selection mode (V)
TOOL_HAND    = 2   # Canvas hand/drag mode (H / Space)

# ---------------------------------------------------------------------------------------------------------------------
# Widget Class

class DraggableGraphicsView(QGraphicsView):
    toolModeChanged = pyqtSignal(int)

    def __init__(self, parent):
        QGraphicsView.__init__(self, parent)

        self.fPanning = False
        self.fToolMode = TOOL_POINTER
        self.fSpacePanning = False

        exts = gCarla.utils.get_supported_file_extensions()

        self.fSupportedExtensions = tuple(("." + i) for i in exts)
        self.fWasLastDragValid = False

        self.setAcceptDrops(True)
        self.initSearchWidgets()

    def setToolMode(self, mode):
        self.fToolMode = mode
        if mode == TOOL_HAND:
            self.setCursor(QCursor(Qt.OpenHandCursor))
            self.setDragMode(QGraphicsView.ScrollHandDrag)
        elif mode == TOOL_SELECT:
            self.setCursor(QCursor(Qt.CrossCursor))
            self.setDragMode(QGraphicsView.RubberBandDrag)
        else:
            self.fToolMode = TOOL_POINTER
            self.unsetCursor()
            self.setDragMode(QGraphicsView.NoDrag)
        self.toolModeChanged.emit(self.fToolMode)

    def keyPressEvent(self, event):
        # Ignore tool hotkeys if an in-scene item (e.g. rename editor) has keyboard focus
        sc = self.scene()
        if sc is not None and sc.focusItem() is not None:
            QGraphicsView.keyPressEvent(self, event)
            return

        # Ignore tool hotkeys if searching
        edit = self._searchWidget()
        if edit is not None and edit.hasFocus():
            QGraphicsView.keyPressEvent(self, event)
            return

        if (event.modifiers() & Qt.ControlModifier):
            if (event.modifiers() & Qt.ShiftModifier) and event.key() == Qt.Key_I:
                event.accept()
                self._clearHighlights()
                import patchcanvas.patchcanvas as pc
                pc.invertNodeSelection()
                if hasattr(gCarla.gui, "updateMiniCanvasLater"):
                    gCarla.gui.updateMiniCanvasLater()
                return
            elif event.key() == Qt.Key_A:
                event.accept()
                self._clearHighlights()
                import patchcanvas.patchcanvas as pc
                pc.selectAllNodes()
                if hasattr(gCarla.gui, "updateMiniCanvasLater"):
                    gCarla.gui.updateMiniCanvasLater()
                return
            elif event.key() == Qt.Key_D:
                event.accept()
                self._clearHighlights()
                import patchcanvas.patchcanvas as pc
                pc.deselectAllNodes()
                if hasattr(gCarla.gui, "updateMiniCanvasLater"):
                    gCarla.gui.updateMiniCanvasLater()
                return
            elif event.key() == Qt.Key_F:
                event.accept()
                self.toggleSearch()
                return
            elif event.key() == Qt.Key_S:
                event.accept()
                if hasattr(gCarla, "gui") and hasattr(gCarla.gui, "slot_fileSave"):
                    if event.modifiers() & Qt.ShiftModifier:
                        gCarla.gui.slot_fileSaveAs()
                    else:
                        gCarla.gui.slot_fileSave()
                return

        # Modal shortcuts: V = Select, H = Hand, Q/Esc = Pointer
        if not (event.modifiers() & (Qt.ControlModifier | Qt.AltModifier)):
            if event.key() == Qt.Key_V:
                event.accept()
                self.setToolMode(TOOL_SELECT)
                return
            elif event.key() == Qt.Key_H:
                event.accept()
                self.setToolMode(TOOL_HAND)
                return
            elif event.key() in (Qt.Key_Q, Qt.Key_Escape):
                event.accept()
                self.setToolMode(TOOL_POINTER)
                return
            elif event.key() == Qt.Key_Space and not event.isAutoRepeat():
                event.accept()
                self.fSpacePanning = True
                self.setCursor(QCursor(Qt.OpenHandCursor))
                self.setDragMode(QGraphicsView.ScrollHandDrag)
                return

        QGraphicsView.keyPressEvent(self, event)

    def keyReleaseEvent(self, event):
        if event.key() == Qt.Key_Space and not event.isAutoRepeat() and getattr(self, "fSpacePanning", False):
            event.accept()
            self.fSpacePanning = False
            self.setToolMode(self.fToolMode)
            return
        QGraphicsView.keyReleaseEvent(self, event)

    # -----------------------------------------------------------------------------------------------------------------

    def isDragUrlValid(self, filename):
        lfilename = filename.lower()

        if os.path.isdir(filename):
            #if os.path.exists(os.path.join(filename, "manifest.ttl")):
                #return True
            if CARLA_OS_MAC and lfilename.endswith(".vst"):
                return True
            if lfilename.endswith(".vst3") and ".vst3" in self.fSupportedExtensions:
                return True

        elif os.path.isfile(filename):
            if lfilename.endswith(self.fSupportedExtensions):
                return True

        return False

    # -----------------------------------------------------------------------------------------------------------------

    def dragEnterEvent(self, event):
        urls = event.mimeData().urls()

        for url in urls:
            if self.isDragUrlValid(url.toLocalFile()):
                self.fWasLastDragValid = True
                event.acceptProposedAction()
                return

        self.fWasLastDragValid = False
        QGraphicsView.dragEnterEvent(self, event)

    def dragMoveEvent(self, event):
        if not self.fWasLastDragValid:
            QGraphicsView.dragMoveEvent(self, event)
            return

        event.acceptProposedAction()

    def dragLeaveEvent(self, event):
        self.fWasLastDragValid = False
        QGraphicsView.dragLeaveEvent(self, event)

    # -----------------------------------------------------------------------------------------------------------------

    def dropEvent(self, event):
        event.acceptProposedAction()

        urls = event.mimeData().urls()

        if len(urls) == 0:
            return

        for url in urls:
            filename = url.toLocalFile()

            if not gCarla.gui.host.load_file(filename):
                CustomMessageBox(self, QMessageBox.Critical, self.tr("Error"),
                                 self.tr("Failed to load file"),
                                 gCarla.gui.host.get_last_error(), QMessageBox.Ok, QMessageBox.Ok)

    def mousePressEvent(self, event):
        # A canvas click counts as user interaction and ends the persistent
        # search selection (see TODO #21).
        if getattr(self, "_searchSelectedBoxes", None):
            self._clearHighlights()
        pos = event.position().toPoint() if hasattr(event, "position") else event.pos()

        # Check if left click occurred on empty canvas (no interactive nodes/cables/ports)
        clicked_on_empty_canvas = False
        if event.button() == Qt.LeftButton and self.fToolMode == TOOL_POINTER and not (event.modifiers() & (Qt.ControlModifier | Qt.ShiftModifier | Qt.AltModifier)):
            item = self.itemAt(pos)
            if item is None:
                clicked_on_empty_canvas = True
            else:
                top_item = item.topLevelItem() if hasattr(item, "topLevelItem") and item.topLevelItem() is not None else item
                itype = getattr(item, "type", lambda: 0)()
                top_type = getattr(top_item, "type", lambda: 0)()
                is_node_or_conn = (
                    itype in (QGraphicsItem.UserType + 1, QGraphicsItem.UserType + 2, QGraphicsItem.UserType + 3,
                              QGraphicsItem.UserType + 4, QGraphicsItem.UserType + 5, QGraphicsItem.UserType + 6,
                              QGraphicsItem.UserType + 7, QGraphicsItem.UserType + 8, QGraphicsItem.UserType + 10)
                    or top_type in (QGraphicsItem.UserType + 1, QGraphicsItem.UserType + 2, QGraphicsItem.UserType + 3,
                                    QGraphicsItem.UserType + 4, QGraphicsItem.UserType + 5, QGraphicsItem.UserType + 6,
                                    QGraphicsItem.UserType + 7, QGraphicsItem.UserType + 8, QGraphicsItem.UserType + 10)
                )
                if not is_node_or_conn:
                    clicked_on_empty_canvas = True

        if (event.button() == Qt.MiddleButton and not (event.modifiers() & Qt.ControlModifier)) or (
            event.button() == Qt.LeftButton and (self.fToolMode == TOOL_HAND or getattr(self, "fSpacePanning", False) or clicked_on_empty_canvas)
        ):
            self.fPanning = True
            self.fPanStartPos = pos
            self.fPanStartScroll = (
                self.horizontalScrollBar().value() if self.horizontalScrollBar() else 0,
                self.verticalScrollBar().value() if self.verticalScrollBar() else 0
            )
            self.setCursor(QCursor(Qt.ClosedHandCursor))
            # Shadows are only recomputed while repainting; skipping them during
            # a pan keeps the exposed strips cheap to redraw.
            try:
                import patchcanvas.patchcanvas as pc
                if hasattr(pc, "canvas"):
                    pc.canvas.dragging = True
            except Exception:
                pass
            event.accept()
            return

        if event.button() == Qt.LeftButton and self.fToolMode == TOOL_SELECT:
            self.setDragMode(QGraphicsView.RubberBandDrag)
            QGraphicsView.mousePressEvent(self, event)
            return

        QGraphicsView.mousePressEvent(self, event)

    def mouseMoveEvent(self, event):
        if getattr(self, "fPanning", False):
            pos = event.position().toPoint() if hasattr(event, "position") else event.pos()
            delta = pos - getattr(self, "fPanStartPos", pos)
            hsb = self.horizontalScrollBar()
            vsb = self.verticalScrollBar()
            if hsb and vsb:
                start_h, start_v = getattr(self, "fPanStartScroll", (hsb.value(), vsb.value()))
                target_h = start_h - delta.x()
                target_v = start_v - delta.y()

                # In infinite canvas mode, dynamically expand sceneRect when panning near boundaries
                sc = self.scene()
                if sc is not None:
                    s_rect = sc.sceneRect()
                    margin = 800.0
                    needs_expand = False
                    new_x = s_rect.x()
                    new_y = s_rect.y()
                    new_w = s_rect.width()
                    new_h = s_rect.height()

                    if target_h >= hsb.maximum() - 50:
                        new_w += margin
                        needs_expand = True
                    elif target_h <= hsb.minimum() + 50 and target_h < 0:
                        new_x -= margin
                        new_w += margin
                        needs_expand = True

                    if target_v >= vsb.maximum() - 50:
                        new_h += margin
                        needs_expand = True
                    elif target_v <= vsb.minimum() + 50 and target_v < 0:
                        new_y -= margin
                        new_h += margin
                        needs_expand = True

                    if needs_expand:
                        expanded = QRectF(new_x, new_y, new_w, new_h)
                        sc.setSceneRect(expanded)
                        self.setSceneRect(expanded)
                        import patchcanvas.patchcanvas as pc
                        if hasattr(pc, "canvas"):
                            pc.canvas.size_rect = expanded

                hsb.setValue(target_h)
                vsb.setValue(target_v)
            event.accept()
            return

        QGraphicsView.mouseMoveEvent(self, event)

    def mouseReleaseEvent(self, event):
        if getattr(self, "fPanning", False) and (
            event.button() == Qt.MiddleButton or event.button() == Qt.LeftButton
        ):
            self.fPanning = False
            try:
                import patchcanvas.patchcanvas as pc
                if hasattr(pc, "canvas"):
                    pc.canvas.dragging = False
            except Exception:
                pass
            if getattr(self, "fSpacePanning", False):
                self.setCursor(QCursor(Qt.OpenHandCursor))
            else:
                self.setToolMode(self.fToolMode)
            event.accept()
            return

        QGraphicsView.mouseReleaseEvent(self, event)

    def wheelEvent(self, event):
        if event.buttons() & Qt.MiddleButton:
            event.ignore()
            return
            
        # Standard: Ctrl+Scroll -> Zoom
        if event.modifiers() & Qt.ControlModifier:
            delta = event.angleDelta().y() if hasattr(event, "angleDelta") else event.delta()
            sc = self.scene()
            if sc and hasattr(sc, "zoom_wheel"):
                sc.zoom_wheel(delta)
            else:
                zoom_factor = 1.15 if delta > 0 else 1.0 / 1.15
                self.scale(zoom_factor, zoom_factor)
            event.accept()
            return
            
        # Standard: Shift+Scroll -> Horizontal Pan
        if event.modifiers() & Qt.ShiftModifier:
            delta = event.angleDelta().y() if hasattr(event, "angleDelta") else event.delta()
            if hasattr(event, "angleDelta") and event.angleDelta().x() != 0:
                delta = event.angleDelta().x()
                
            sb = self.horizontalScrollBar()
            if sb:
                sb.setValue(sb.value() - delta)
            event.accept()
            return

        QGraphicsView.wheelEvent(self, event)

    # -----------------------------------------------------------------------------------------------------------------
    # Canvas Node Quick Search

    def initSearchWidgets(self):
        if hasattr(self, "fSearchList"):
            return

        self._searchSelectedBoxes = []

        # The search *input* now lives in the top context toolbar
        # (CanvasContextToolBarOverlay.searchEdit). This view only owns the
        # floating results list shown below that field.
        self.fSearchList = QListWidget(self)
        self.fSearchList.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.fSearchList.setTextElideMode(Qt.ElideRight)
        self.fSearchList.setWordWrap(False)
        self.fSearchList.setUniformItemSizes(True)
        self.fSearchList.setObjectName("canvasNodeSearchList")
        self.fSearchList.hide()

        self.fSearchList.itemClicked.connect(self._onSearchItemClicked)
        self.fSearchList.currentRowChanged.connect(self._onSearchRowChanged)

        self.fSearchList.installEventFilter(self)

        shortcut = QShortcut(QKeySequence("Ctrl+F"), self)
        shortcut.activated.connect(self.toggleSearch)

    def _searchWidget(self):
        toolbar = getattr(self, "canvasContextToolBar", None)
        return getattr(toolbar, "searchEdit", None) if toolbar is not None else None

    def toggleSearch(self):
        self.initSearchWidgets()
        edit = self._searchWidget()
        if edit is None:
            return
        if edit.hasFocus():
            self.hideSearch()
            self.setFocus()
        else:
            self.fSearchList.hide()
            edit.setFocus()
            edit.selectAll()

    def hideSearch(self):
        # Closing the search keeps matched nodes selected until the user
        # interacts with the canvas (see TODO #21). Callers that want to drop
        # the selection as well should invoke _clearHighlights() explicitly.
        if hasattr(self, "fSearchList"):
            self.fSearchList.hide()
        self.setFocus()

    def _getCanvasBoxes(self):
        from patchcanvas import canvas
        boxes = []
        for grp in getattr(canvas, "group_list", []):
            if grp.widgets and grp.widgets[0]:
                boxes.append((grp.group_name, grp.widgets[0]))
        return boxes

    def _clearHighlights(self):
        for box in getattr(self, "_searchSelectedBoxes", []):
            try:
                if box.isSelected():
                    box.setSelected(False)
            except Exception:
                pass
        self._searchSelectedBoxes = []
        for _, box in self._getCanvasBoxes():
            if getattr(box, "m_search_highlight", 0) != 0:
                box.m_search_highlight = 0
                box.update()

    def _fuzzyScore(self, pattern, text):
        import difflib
        p, t = pattern.lower(), text.lower()
        if p in t:
            return 100.0 + (len(p) / float(len(t)))
        return difflib.SequenceMatcher(None, p, t).ratio() * 100.0

    def _onSearchTextChanged(self, text):
        pattern = text.strip()
        self._clearHighlights()
        self.fSearchList.clear()

        if not pattern:
            self.fSearchList.hide()
            return

        matches = []
        for name, box in self._getCanvasBoxes():
            score = self._fuzzyScore(pattern, name)
            if score > 35.0:
                matches.append((score, name, box))

        matches.sort(key=lambda x: x[0], reverse=True)

        for _, name, box in matches:
            box.m_search_highlight = 1
            try:
                box.setSelected(True)
            except Exception:
                pass
            box.update()
            item = QListWidgetItem(name)
            item.setData(Qt.UserRole, box)
            self.fSearchList.addItem(item)

        # Remember which nodes the search selected so the selection can persist
        # after the search box closes, until the user interacts with the canvas.
        self._searchSelectedBoxes = [box for _, _, box in matches]

        if matches:
            list_h = min(160, max(40, len(matches) * 26 + 6))
            edit = self._searchWidget()
            if edit is not None:
                # The search field lives in the context toolbar, a SIBLING of
                # this view, not a child — map through global coordinates so
                # the results list lands directly under the field (and stays
                # correct when the toolbar is dragged).
                gp = edit.mapToGlobal(QPoint(0, edit.height() + 2))
                top_left = self.mapFromGlobal(gp)
                list_w = max(180, edit.width())
                self.fSearchList.setGeometry(top_left.x(), top_left.y(), list_w, list_h)
            else:
                self.fSearchList.setGeometry(12, 42, 260, list_h)
            self.fSearchList.show()
            self.fSearchList.raise_()
            self.fSearchList.setCurrentRow(0)
        else:
            # Empty state: show why nothing matched (disabled row)
            self.fSearchList.clear()
            no_match = QListWidgetItem("No nodes match")
            no_match.setFlags(no_match.flags() & ~getattr(Qt.ItemFlag, "ItemIsEnabled", Qt.ItemIsEnabled))
            self.fSearchList.addItem(no_match)
            edit = self._searchWidget()
            if edit is not None:
                gp = edit.mapToGlobal(QPoint(0, edit.height() + 2))
                top_left = self.mapFromGlobal(gp)
                self.fSearchList.setGeometry(top_left.x(), top_left.y(), max(180, edit.width()), 30)
            else:
                self.fSearchList.setGeometry(12, 42, 260, 30)
            self.fSearchList.show()
            self.fSearchList.raise_()

    def _onSearchRowChanged(self, row):
        for i in range(self.fSearchList.count()):
            item = self.fSearchList.item(i)
            box = item.data(Qt.UserRole)
            if box:
                box.m_search_highlight = 2 if i == row else 1
                box.update()

    def _onSearchAccept(self):
        item = self.fSearchList.currentItem()
        if item:
            self._selectAndCenter(item.data(Qt.UserRole))

    def _onSearchItemClicked(self, item):
        if item:
            self._selectAndCenter(item.data(Qt.UserRole))

    def animateFocusOn(self, target_item, duration=260):
        if not target_item or not self.scene():
            return

        # Stop any existing animation
        if hasattr(self, "_focusAnim") and self._focusAnim is not None:
            self._focusAnim.stop()

        # Target center point in scene coords
        if hasattr(target_item, "sceneBoundingRect"):
            target_pt = target_item.sceneBoundingRect().center()
        elif hasattr(target_item, "scenePos"):
            target_pt = target_item.scenePos()
        elif isinstance(target_item, (QPointF,)):
            target_pt = target_item
        else:
            self.centerOn(target_item)
            return

        # Start center point in scene coords
        viewport_rect = self.viewport().rect()
        start_pt = self.mapToScene(viewport_rect.center())

        curve = QEasingCurve(QEasingCurve.Type.InOutCubic if hasattr(QEasingCurve, "Type") else QEasingCurve.InOutCubic)

        anim = QVariantAnimation(self)
        anim.setDuration(duration)
        anim.setStartValue(0.0)
        anim.setEndValue(1.0)

        def _on_step(val):
            t = float(val)
            e = curve.valueForProgress(t)

            # Smoothly interpolate position via cubic bezier curve
            curr_x = start_pt.x() + (target_pt.x() - start_pt.x()) * e
            curr_y = start_pt.y() + (target_pt.y() - start_pt.y()) * e

            self.centerOn(curr_x, curr_y)

        def _on_finish():
            self.centerOn(target_pt)

        anim.valueChanged.connect(_on_step)
        anim.finished.connect(_on_finish)
        self._focusAnim = anim
        anim.start()

    def _selectAndCenter(self, target_box):
        self.hideSearch()
        if not target_box or not self.scene():
            return
        # Keep the whole search match set selected so it persists after the
        # search closes; just focus and ensure the chosen node is selected.
        self.animateFocusOn(target_box)
        try:
            target_box.setSelected(True)
        except Exception:
            pass

    def eventFilter(self, obj, event):
        key_press_type = QEvent.Type.KeyPress if hasattr(QEvent, "Type") else QEvent.KeyPress
        if event.type() == key_press_type:
            if obj == self.fSearchList:
                if event.key() in (Qt.Key_Return, Qt.Key_Enter):
                    self._onSearchAccept()
                    return True
                elif event.key() == Qt.Key_Escape:
                    self.hideSearch()
                    return True
                elif event.key() == Qt.Key_Up and self.fSearchList.currentRow() == 0:
                    edit = self._searchWidget()
                    if edit is not None:
                        edit.setFocus()
                    return True
        return QGraphicsView.eventFilter(self, obj, event)

# ---------------------------------------------------------------------------------------------------------------------
