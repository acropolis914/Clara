#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2011-2025 Filipe Coelho <falktx@falktx.com>
# SPDX-License-Identifier: GPL-2.0-or-later

# ------------------------------------------------------------------------------------------------------------
# Imports (Global)

import os

# ------------------------------------------------------------------------------------------------------------
# Imports (PyQt)

from qt_compat import (
    Qt,
    QSize,
    QRect,
    QColor,
    QPainter,
    QPixmap,
    QAbstractItemView,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPalette,
    QPushButton,
    QTimer,
)

# ------------------------------------------------------------------------------------------------------------
# Imports (Custom Stuff)

from carla_backend import CARLA_OS_MAC, CUSTOM_DATA_TYPE_PROPERTY
from carla_shared import gCarla, CustomMessageBox, CARLA_KEY_CANVAS_THEME, CARLA_DEFAULT_CANVAS_THEME
from carla_skin import createPluginSlot
from utils import QSafeSettings
from patchcanvas.theme import Theme
from project_storage import storage_manager

# ------------------------------------------------------------------------------------------------------------
# Rack Widget item

class RackListItem(QListWidgetItem):
    kRackItemType = QListWidgetItem.UserType + 1
    kMinimumWidth = 200

    def __init__(self, parent, pluginId, useClassicSkin):
        QListWidgetItem.__init__(self, parent, self.kRackItemType)
        self.host = parent.host

        # ----------------------------------------------------------------------------------------------------
        # Internal stuff

        self.fParent   = parent
        self.fPluginId = pluginId
        self.fWidget   = None

        color   = self.host.get_custom_data_value(pluginId, CUSTOM_DATA_TYPE_PROPERTY, "CarlaColor")
        skin    = self.host.get_custom_data_value(pluginId, CUSTOM_DATA_TYPE_PROPERTY, "CarlaSkin")
        compact = bool(self.host.get_custom_data_value(pluginId,
                                                       CUSTOM_DATA_TYPE_PROPERTY,
                                                       "CarlaSkinIsCompacted") == "true")

        if color:
            try:
                color = tuple(int(i) for i in color.split(";",3))
            except Exception as e:
                print("Color value decode failed for", color, "error was:", e)
                color = None
        else:
            color = None

        if useClassicSkin and not skin:
            skin = "minimal-dark"

        layer_mode_data = self.host.get_custom_data_value(pluginId, CUSTOM_DATA_TYPE_PROPERTY, "CarlaSkinLayerMode")
        layer_mode = bool(layer_mode_data == "true") if layer_mode_data is not None else False

        self.fOptions = {
            'color'     : color,
            'skin'      : skin,
            'compact'   : compact,
            'layer_mode': layer_mode,
        }

        self.setFlags(Qt.ItemIsSelectable|Qt.ItemIsEnabled)
        #self.setFlags(Qt.ItemIsSelectable|Qt.ItemIsEnabled|Qt.ItemIsDragEnabled)

        # ----------------------------------------------------------------------------------------------------
        # Set-up GUI

        self.recreateWidget(firstInit = True)

    # --------------------------------------------------------------------------------------------------------

    def close(self):
        if self.fWidget is None:
            return

        widget = self.fWidget
        self.fWidget = None

        self.fParent.customClearSelection()
        self.fParent.setItemWidget(self, None)

        widget.fEditDialog.close()
        widget.fEditDialog.setParent(None)
        widget.fEditDialog.deleteLater()
        widget.fEditDialog = None

        widget.close()
        widget.setParent(None)
        widget.deleteLater()
        del widget

    def getEditDialog(self):
        if self.fWidget is None:
            return None

        return self.fWidget.fEditDialog

    def getPluginId(self):
        return self.fPluginId

    def getWidget(self):
        return self.fWidget

    def isCompacted(self):
        return self.fOptions['compact']

    def isGuiShown(self):
        if self.fWidget is None or self.fWidget.b_gui is not None:
            return None
        return self.fWidget.b_gui.isChecked()

    # --------------------------------------------------------------------------------------------------------

    def setPluginId(self, pluginId):
        self.fPluginId = pluginId

        if self.fWidget is not None:
            self.fWidget.setPluginId(pluginId)

    def setSelected(self, select):
        if self.fWidget is not None:
            self.fWidget.setSelected(select)

        QListWidgetItem.setSelected(self, select)

    # --------------------------------------------------------------------------------------------------------

    def setCompacted(self, compact):
        self.fOptions['compact'] = compact

    # --------------------------------------------------------------------------------------------------------

    def compact(self):
        if self.fOptions['compact']:
            return
        self.recreateWidget(True)

    def expand(self):
        if not self.fOptions['compact']:
            return
        self.recreateWidget(True)

    def recreateWidget(self, invertCompactOption = False, firstInit = False, newColor = None, newSkin = None):
        if invertCompactOption:
            self.fOptions['compact'] = not self.fOptions['compact']
        if newColor is not None:
            self.fOptions['color'] = newColor
        if newSkin is not None:
            self.fOptions['skin'] = newSkin

        wasGuiShown = None

        if self.fWidget is not None and self.fWidget.b_gui is not None:
            wasGuiShown = self.fWidget.b_gui.isChecked()

        self.close()

        self.fWidget = createPluginSlot(self.fParent, self.host, self.fPluginId, self.fOptions)
        self.fWidget.setFixedHeight(self.fWidget.getFixedHeight())

        if wasGuiShown and self.fWidget.b_gui is not None:
            self.fWidget.b_gui.setChecked(True)

        self.setSizeHint(QSize(self.kMinimumWidth, self.fWidget.getFixedHeight()))

        self.fParent.setItemWidget(self, self.fWidget)

        # Apply rack item color to patchbay canvas node
        try:
            from carla_shared import gCarla
            if hasattr(gCarla, "gui") and getattr(gCarla.gui, "fWithCanvas", False):
                import patchcanvas
                skin_col = getattr(self.fWidget, "fSkinColor", None)
                if skin_col and skin_col not in ((40, 40, 40), (255, 255, 255)):
                    hex_col = f"#{skin_col[0]:02x}{skin_col[1]:02x}{skin_col[2]:02x}"
                else:
                    hex_col = None
                for group in patchcanvas.canvas.group_list:
                    if getattr(group, "plugin_id", -1) == self.fPluginId:
                        for w in getattr(group, "widgets", []):
                            if w is not None:
                                w.setCustomColor(hex_col, notify=False)
                        break
        except Exception:
            pass

        if not firstInit:
            self.host.set_custom_data(self.fPluginId, CUSTOM_DATA_TYPE_PROPERTY,
                                      "CarlaSkinIsCompacted", "true" if self.fOptions['compact'] else "false")

    def recreateWidget2(self, wasCompacted, wasGuiShown):
        self.fOptions['compact'] = wasCompacted

        self.close()

        self.fWidget = createPluginSlot(self.fParent, self.host, self.fPluginId, self.fOptions)
        self.fWidget.setFixedHeight(self.fWidget.getFixedHeight())

        if wasGuiShown and self.fWidget.b_gui is not None:
            self.fWidget.b_gui.setChecked(True)

        self.setSizeHint(QSize(self.kMinimumWidth, self.fWidget.getFixedHeight()))

        self.fParent.setItemWidget(self, self.fWidget)

        self.host.set_custom_data(self.fPluginId, CUSTOM_DATA_TYPE_PROPERTY,
                                  "CarlaSkinIsCompacted", "true" if wasCompacted else "false")

# ------------------------------------------------------------------------------------------------------------
# Rack Widget

class RackListWidget(QListWidget):
    def __init__(self, parent):
        QListWidget.__init__(self, parent)
        self.host = None
        self.fParent = None

        exts = gCarla.utils.get_supported_file_extensions()

        self.fSupportedExtensions = tuple(("." + i) for i in exts)
        self.fLastSelectedItem    = None
        self.fWasLastDragValid    = False

        self.setMinimumWidth(RackListItem.kMinimumWidth)
        self.setSelectionMode(QAbstractItemView.SingleSelection)
        self.setSortingEnabled(False)

        try:
            from qt_compat import QOpenGLWidget
            self.setViewport(QOpenGLWidget(self))
        except Exception:
            pass

        # Smooth scrolling configuration
        scroll_mode = getattr(QAbstractItemView.ScrollMode, "ScrollPerPixel", getattr(QAbstractItemView, "ScrollPerPixel", None))
        if scroll_mode is not None:
            self.setVerticalScrollMode(scroll_mode)

        self._smooth_target_val = None
        self._smooth_timer = QTimer(self)
        self._smooth_timer.setInterval(16)
        self._smooth_timer.timeout.connect(self._on_smooth_scroll_tick)

        self.setDragEnabled(True)
        self.setDragDropMode(QAbstractItemView.DropOnly)
        self.setDropIndicatorShown(True)
        self.setSpacing(4)
        self.viewport().setAcceptDrops(True)


        # Floating "+ Add Plugin" Action Button
        self.btn_floating_add = QPushButton(self)
        self.btn_floating_add.setText("+ Add Plugin")
        self.btn_floating_add.setToolTip("Add new plugin to rack")
        self.btn_floating_add.setCursor(Qt.PointingHandCursor)
        self.btn_floating_add.setObjectName("rackFloatingAddButton")
        self.btn_floating_add.clicked.connect(self._onFloatingAddClicked)
        self.btn_floating_add.adjustSize()
        self.btn_floating_add.show()

    def _onFloatingAddClicked(self):
        if hasattr(gCarla, "gui") and gCarla.gui is not None:
            if hasattr(gCarla.gui, "slot_pluginAdd"):
                gCarla.gui.slot_pluginAdd()
            elif hasattr(gCarla.gui.ui, "act_plugin_add"):
                gCarla.gui.ui.act_plugin_add.trigger()

    def resizeEvent(self, event):
        QListWidget.resizeEvent(self, event)
        if hasattr(self, "btn_floating_add") and self.btn_floating_add is not None:
            btn_w = self.btn_floating_add.width()
            btn_h = self.btn_floating_add.height()
            vsb = self.verticalScrollBar()
            vsb_w = vsb.width() if (vsb and vsb.isVisible()) else 0
            # Position at bottom-right of viewport with 16px margins
            self.btn_floating_add.move(self.width() - btn_w - vsb_w - 16, self.height() - btn_h - 16)
            self.btn_floating_add.raise_()

    # --------------------------------------------------------------------------------------------------------

    def createItem(self, pluginId, useClassicSkin):
        return RackListItem(self, pluginId, useClassicSkin)

    def getPluginCount(self):
        return self.fParent.getPluginCount()

    def setHostAndParent(self, host, parent):
        self.host = host
        self.fParent = parent

    # --------------------------------------------------------------------------------------------------------

    def customClearSelection(self):
        self.setCurrentRow(-1)
        self.clearSelection()
        self.clearFocus()

    def isDragUrlValid(self, filename):
        if not filename:
            return False

        if filename[-1] == '/':
            filename = filename[:-1]

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

    # --------------------------------------------------------------------------------------------------------

    def dragEnterEvent(self, event):
        urls = event.mimeData().urls()

        for url in urls:
            if self.isDragUrlValid(url.toLocalFile()):
                self.fWasLastDragValid = True
                event.acceptProposedAction()
                return

        self.fWasLastDragValid = False
        QListWidget.dragEnterEvent(self, event)

    def dragMoveEvent(self, event):
        if not self.fWasLastDragValid:
            QListWidget.dragMoveEvent(self, event)
            return

        event.acceptProposedAction()

        tryItem = self.itemAt(event.pos())

        if tryItem is not None:
            self.setCurrentRow(tryItem.getPluginId())
        else:
            self.setCurrentRow(-1)

    def dragLeaveEvent(self, event):
        if self.fWasLastDragValid:
            self.fWasLastDragValid = False
        QListWidget.dragLeaveEvent(self, event)

    # --------------------------------------------------------------------------------------------------------

    # FIXME: this needs some attention

    # if dropping project file over 1 plugin, load it in rack or patchbay
    # if dropping regular files over 1 plugin, keep replacing plugins

    def dropEvent(self, event):
        event.acceptProposedAction()

        urls = event.mimeData().urls()

        if not urls:
            return

        tryItem = self.itemAt(event.pos())

        if tryItem is not None:
            pluginId = tryItem.getPluginId()
        else:
            pluginId = -1

        for url in urls:
            if pluginId >= 0:
                self.host.replace_plugin(pluginId)
                pluginId += 1

                if pluginId > self.host.get_current_plugin_count():
                    pluginId = -1

            filename = url.toLocalFile()

            if not filename:
                continue

            if filename[-1] == '/':
                filename = filename[:-1]

            if not self.host.load_file(filename):
                CustomMessageBox(self, QMessageBox.Critical, self.tr("Error"),
                                 self.tr("Failed to load file"),
                                 self.host.get_last_error(), QMessageBox.Ok, QMessageBox.Ok)
                continue

            if storage_manager.is_project_file(filename):
                gCarla.gui.loadCanvasGroupPositionsFromProject(filename)
                gCarla.gui.loadExternalCanvasGroupPositionsIfNeeded(filename)

        if tryItem is not None:
            self.host.replace_plugin(self.host.get_max_plugin_number())
            #tryItem.widget.setActive(True, True, True)

    # --------------------------------------------------------------------------------------------------------

    def mousePressEvent(self, event):
        if self.itemAt(event.pos()) is None and self.currentRow() != -1:
            event.accept()
            self.customClearSelection()
            return

        QListWidget.mousePressEvent(self, event)

    def keyPressEvent(self, event):
        items = self.selectedItems()
        if not items:
            QListWidget.keyPressEvent(self, event)
            return

        item = items[0]
        pluginId = item.getPluginId()

        if event.key() == Qt.Key_Delete:
            pinfo = self.host.get_plugin_info(pluginId) if self.host is not None else {}
            name = pinfo.get("name", self.tr("this plugin")) if isinstance(pinfo, dict) else self.tr("this plugin")
            ask = QMessageBox.question(
                self,
                self.tr("Remove Plugin"),
                self.tr(f"Are you sure you want to remove '{name}'?"),
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No,
            )
            if ask == QMessageBox.Yes and self.host is not None:
                self.host.remove_plugin(pluginId)
            event.accept()
            return

        if event.modifiers() & Qt.ControlModifier:
            if event.key() == Qt.Key_Up:
                gCarla.gui.switchPlugins(pluginId, pluginId - 1)
                event.accept()
                return
            elif event.key() == Qt.Key_Down:
                gCarla.gui.switchPlugins(pluginId, pluginId + 1)
                event.accept()
                return
            elif event.key() == Qt.Key_S:
                if hasattr(gCarla, "gui") and hasattr(gCarla.gui, "slot_fileSave"):
                    event.accept()
                    if event.modifiers() & Qt.ShiftModifier:
                        gCarla.gui.slot_fileSaveAs()
                    else:
                        gCarla.gui.slot_fileSave()
                    return

        QListWidget.keyPressEvent(self, event)

    def wheelEvent(self, event):
        pos = event.pos() if hasattr(event, "pos") else event.position().toPoint()
        delta = 0
        if hasattr(event, "angleDelta"):
            delta = event.angleDelta().y()
        elif hasattr(event, "delta"):
            delta = event.delta()

        w = self.childAt(pos)
        target_scroll_area = None
        while w is not None and w != self and w != self.viewport():
            from widgets.commondial import CommonDial
            from widgets.scalabledial import ScalableDial
            from qt_compat import QSlider, QAbstractSpinBox, QComboBox, QScrollArea
            if isinstance(w, (CommonDial, ScalableDial, QSlider, QAbstractSpinBox, QComboBox)):
                w.wheelEvent(event)
                event.accept()
                return
            if isinstance(w, QScrollArea) and target_scroll_area is None:
                target_scroll_area = w
            w = w.parentWidget()

        if target_scroll_area is not None:
            vsb = target_scroll_area.verticalScrollBar()
            if vsb and vsb.maximum() > vsb.minimum():
                pixel_step = int((delta / 120.0) * -40) if delta != 0 else 0
                if pixel_step != 0:
                    vsb.setValue(max(vsb.minimum(), min(vsb.maximum(), vsb.value() + pixel_step)))
                event.accept()
                return

        if delta != 0:
            vsb = self.verticalScrollBar()
            if vsb and vsb.maximum() > vsb.minimum():
                pixel_step = int((delta / 120.0) * -80)
                vsb.setValue(max(vsb.minimum(), min(vsb.maximum(), vsb.value() + pixel_step)))
                event.accept()
                return

        QListWidget.wheelEvent(self, event)

    def _on_smooth_scroll_tick(self):
        vsb = self.verticalScrollBar()
        if not vsb or self._smooth_target_val is None:
            self._smooth_timer.stop()
            self._smooth_target_val = None
            return

        curr = vsb.value()
        diff = self._smooth_target_val - curr

        if abs(diff) <= 1:
            vsb.setValue(self._smooth_target_val)
            self._smooth_timer.stop()
            self._smooth_target_val = None
        else:
            # Gentle easing interpolation (~10% per 16ms frame) with max speed cap for fluid visual glide
            raw_step = diff * 0.10
            # Cap maximum speed per tick to prevent jumping across long distances
            max_step = 24
            if raw_step > max_step:
                raw_step = max_step
            elif raw_step < -max_step:
                raw_step = -max_step

            step = int(raw_step)
            if step == 0:
                step = 1 if diff > 0 else -1
            vsb.setValue(curr + step)

    def scrollToItemSmooth(self, item):
        if item is None:
            return
        rect = self.visualItemRect(item)
        vsb = self.verticalScrollBar()
        if not vsb or vsb.maximum() <= vsb.minimum():
            return

        curr = vsb.value()
        viewport_h = self.viewport().height()

        # If already completely visible inside the viewport, no scroll needed
        if rect.top() >= 0 and rect.bottom() <= viewport_h:
            return

        # Target centering the rack item smoothly in the visible viewport
        target = curr + rect.top() - int((viewport_h - rect.height()) / 2)
        new_target = max(vsb.minimum(), min(vsb.maximum(), target))

        self._smooth_target_val = new_target
        if not self._smooth_timer.isActive():
            self._smooth_timer.start()

    def paintEvent(self, event):
        # The rack surface comes from the active theme QSS/palette. Do not paint
        # a second background rectangle or inset outline here; it ignored the
        # theme and required rebuilding the canvas Theme on every repaint.
        QListWidget.paintEvent(self, event)

    def selectionChanged(self, selected, deselected):
        for index in deselected.indexes():
            item = self.itemFromIndex(index)
            if item is not None:
                item.setSelected(False)

        for index in selected.indexes():
            item = self.itemFromIndex(index)
            if item is not None:
                item.setSelected(True)

        QListWidget.selectionChanged(self, selected, deselected)

    # --------------------------------------------------------------------------------------------------------

# ------------------------------------------------------------------------------------------------------------
