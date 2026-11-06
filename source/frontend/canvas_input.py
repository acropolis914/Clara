#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Clara contributors
# SPDX-License-Identifier: GPL-2.0-or-later

# Canvas scrollbars and keyboard shortcuts, split out of host_app.py.
# HostWindow inherits this mixin.

from carla_backend import CUSTOM_DATA_TYPE_PROPERTY
from qt_compat import pyqtSlot


class CanvasInputMixin:
    # --------------------------------------------------------------------------------------------------------
    # Canvas scrollbars

    @pyqtSlot(int)
    def slot_horizontalScrollBarChanged(self, value):
        maximum = self.ui.graphicsView.horizontalScrollBar().maximum()
        if maximum == 0:
            xp = 0
        else:
            xp = float(value) / maximum
        self.ui.miniCanvasPreview.setViewPosX(xp)
        widget = self._miniCanvasViewWidget()
        if widget is not None and widget is not self.ui.miniCanvasPreview:
            widget.setViewPosX(xp)
        self.updateCanvasInitialPos()

    @pyqtSlot(int)
    def slot_verticalScrollBarChanged(self, value):
        maximum = self.ui.graphicsView.verticalScrollBar().maximum()
        if maximum == 0:
            yp = 0
        else:
            yp = float(value) / maximum
        self.ui.miniCanvasPreview.setViewPosY(yp)
        widget = self._miniCanvasViewWidget()
        if widget is not None and widget is not self.ui.miniCanvasPreview:
            widget.setViewPosY(yp)
        self.updateCanvasInitialPos()

    # --------------------------------------------------------------------------------------------------------
    # Canvas keyboard

    @pyqtSlot(int)
    def slot_noteOn(self, note):
        if self.fPluginCount == 0:
            return

        for pluginId in self.fSelectedPlugins:
            self.host.send_midi_note(pluginId, 0, note, 100)

            pedit = self.getPluginEditDialog(pluginId)
            pedit.noteOn(0, note, 100)

    @pyqtSlot(int)
    def slot_noteOff(self, note):
        if self.fPluginCount == 0:
            return

        for pluginId in self.fSelectedPlugins:
            self.host.send_midi_note(pluginId, 0, note, 0)

            pedit = self.getPluginEditDialog(pluginId)
            pedit.noteOff(0, note)

    # --------------------------------------------------------------------------------------------------------
    # Canvas keyboard (host callbacks)

    @pyqtSlot(int, int, int, int)
    def slot_handleNoteOnCallback(self, pluginId, channel, note, velocity):
        if pluginId in self.fSelectedPlugins:
            self.ui.keyboard.sendNoteOn(note, False)

    @pyqtSlot(int, int, int)
    def slot_handleNoteOffCallback(self, pluginId, channel, note):
        if pluginId in self.fSelectedPlugins:
            self.ui.keyboard.sendNoteOff(note, False)

    # --------------------------------------------------------------------------------------------------------

    @pyqtSlot(int)
    def slot_handleUpdateCallback(self, pluginId):
        pitem = self.getPluginItem(pluginId)

        if pitem is None:
            return

        wasCompacted = pitem.isCompacted()
        isCompacted = wasCompacted
        needsRecreate = False

        check = self.host.get_custom_data_value(
            pluginId, CUSTOM_DATA_TYPE_PROPERTY, "CarlaSkinIsCompacted"
        )
        if check:
            isCompacted = bool(check == "true")
            if wasCompacted != isCompacted:
                pitem.fOptions["compact"] = isCompacted
                needsRecreate = True

        newSkin = self.host.get_custom_data_value(
            pluginId, CUSTOM_DATA_TYPE_PROPERTY, "CarlaSkin"
        )
        if newSkin and newSkin != pitem.fOptions.get("skin"):
            pitem.fOptions["skin"] = newSkin
            needsRecreate = True

        newColor = self.host.get_custom_data_value(
            pluginId, CUSTOM_DATA_TYPE_PROPERTY, "CarlaColor"
        )
        if newColor:
            try:
                parsed_color = tuple(int(i) for i in newColor.split(";", 3))
                if parsed_color != pitem.fOptions.get("color"):
                    pitem.fOptions["color"] = parsed_color
                    needsRecreate = True
            except Exception:
                pass

        if needsRecreate:
            wasGuiShown = (
                pitem.fWidget.b_gui.isChecked()
                if pitem.fWidget and pitem.fWidget.b_gui
                else False
            )
            pitem.recreateWidget2(isCompacted, wasGuiShown)

        widget = pitem.getWidget()
        if widget is not None and hasattr(widget, "refreshState"):
            widget.refreshState()

