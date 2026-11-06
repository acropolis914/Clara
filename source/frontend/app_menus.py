#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Clara contributors
# SPDX-License-Identifier: GPL-2.0-or-later

# About, disk and transport menu actions, split out of host_app.py.
# HostWindow inherits this mixin.

import os

from carla_app import gCarla
from carla_backend import (
    ENGINE_OPTION_TRANSPORT_MODE,
    ENGINE_TRANSPORT_MODE_INTERNAL,
    ENGINE_TRANSPORT_MODE_JACK,
)
from carla_shared import (
    CARLA_KEY_MAIN_SYSTEM_ICONS,
    HOME,
    CustomMessageBox,
    getIcon,
)
from project_storage import storage_manager
from qt_compat import QApplication, QFileDialog, QIcon, QMessageBox, QModelIndex, pyqtSlot


class AppMenusMixin:
    # --------------------------------------------------------------------------------------------------------
    # About (menu actions)

    @pyqtSlot()
    def slot_aboutCarla(self):
        gCarla.felib.createAndExecAboutDialog(
            self.fParentOrSelf,
            self.host.handle,
            self.host.isControl,
            self.host.isPlugin,
        )

    @pyqtSlot()
    def slot_aboutQt(self):
        QApplication.instance().aboutQt()

    # --------------------------------------------------------------------------------------------------------
    # Disk (menu actions)

    @pyqtSlot(int)
    def slot_diskFolderChanged(self, index):
        if index < 0:
            return
        elif index == 0:
            filename = HOME
            self.ui.b_disk_remove.setEnabled(False)
        else:
            filename = self.ui.cb_disk.itemData(index)
            self.ui.b_disk_remove.setEnabled(True)

        self.fDirModel.setRootPath(filename)
        self.ui.fileTreeView.setRootIndex(self.fDirModel.index(filename))

    @pyqtSlot()
    def slot_diskFolderAdd(self):
        newPath = QFileDialog.getExistingDirectory(
            self, self.tr("New Folder"), "", QFileDialog.ShowDirsOnly
        )

        if newPath:
            if newPath[-1] == os.sep:
                newPath = newPath[:-1]
            self.ui.cb_disk.addItem(os.path.basename(newPath), newPath)
            self.ui.cb_disk.setCurrentIndex(self.ui.cb_disk.count() - 1)
            self.ui.b_disk_remove.setEnabled(True)

    @pyqtSlot()
    def slot_diskFolderRemove(self):
        index = self.ui.cb_disk.currentIndex()

        if index <= 0:
            return

        self.ui.cb_disk.removeItem(index)

        if self.ui.cb_disk.currentIndex() == 0:
            self.ui.b_disk_remove.setEnabled(False)

    @pyqtSlot(QModelIndex)
    def slot_fileTreeDoubleClicked(self, modelIndex):
        filename = self.fDirModel.filePath(modelIndex)

        if storage_manager.is_project_file(filename):
            if self.fPluginCount > 0:
                ask = QMessageBox.question(
                    self,
                    self.tr("Question"),
                    self.tr(
                        "There are some plugins loaded, do you want to remove them now?"
                    ),
                    QMessageBox.Yes | QMessageBox.No,
                    QMessageBox.No,
                )
                if ask != QMessageBox.Yes:
                    return

            self.pluginRemoveAll()
            self.loadProjectLater(filename)
            return

        if not self.ui.listWidget.isDragUrlValid(filename):
            return

        if not self.host.load_file(filename):
            CustomMessageBox(
                self,
                QMessageBox.Critical,
                self.tr("Error"),
                self.tr("Failed to load file"),
                self.host.get_last_error(),
                QMessageBox.Ok,
                QMessageBox.Ok,
            )
            return

    # --------------------------------------------------------------------------------------------------------
    # Transport

    def refreshTransport(self, forced=False):
        if not self.ui.l_transport_time.isVisible():
            return
        if self.fSampleRate == 0.0 or not self.host.is_engine_running():
            return

        timeInfo = self.host.get_transport_info()
        playing = timeInfo["playing"]
        frame = timeInfo["frame"]
        bpm = timeInfo["bpm"]

        if playing != self.fLastTransportState or forced:
            if playing:
                if self.fSavedSettings[CARLA_KEY_MAIN_SYSTEM_ICONS]:
                    icon = getIcon("media-playback-pause", 16, "svgz")
                else:
                    icon = QIcon(":/16x16/media-playback-pause.svgz")
                self.ui.b_transport_play.setChecked(True)
                self.ui.b_transport_play.setIcon(icon)
                # self.ui.b_transport_play.setText(self.tr("&Pause"))
            else:
                if self.fSavedSettings[CARLA_KEY_MAIN_SYSTEM_ICONS]:
                    icon = getIcon("media-playback-start", 16, "svgz")
                else:
                    icon = QIcon(":/16x16/media-playback-start.svgz")
                self.ui.b_transport_play.setChecked(False)
                self.ui.b_transport_play.setIcon(icon)
                # self.ui.b_play.setText(self.tr("&Play"))

            self.fLastTransportState = playing

        if frame != self.fLastTransportFrame or forced:
            self.fLastTransportFrame = frame

            time = frame / self.fSampleRate
            secs = time % 60
            mins = (time / 60) % 60
            hrs = (time / 3600) % 60
            self.ui.l_transport_time.setText("%02i:%02i:%02i" % (hrs, mins, secs))

            frame1 = frame % 1000
            frame2 = (frame / 1000) % 1000
            frame3 = (frame / 1000000) % 1000
            self.ui.l_transport_frame.setText(
                "%03i'%03i'%03i" % (frame3, frame2, frame1)
            )

            bar = timeInfo["bar"]
            beat = timeInfo["beat"]
            tick = timeInfo["tick"]
            self.ui.l_transport_bbt.setText("%03i|%02i|%04i" % (bar, beat, tick))

        if bpm != self.fLastTransportBPM or forced:
            self.fLastTransportBPM = bpm

            if bpm > 0.0:
                self.ui.dsb_transport_bpm.blockSignals(True)
                self.ui.dsb_transport_bpm.setValue(bpm)
                self.ui.dsb_transport_bpm.blockSignals(False)
                self.ui.dsb_transport_bpm.setStyleSheet("")
            else:
                self.ui.dsb_transport_bpm.setStyleSheet(
                    "QDoubleSpinBox { color: palette(mid); }"
                )

    # --------------------------------------------------------------------------------------------------------
    # Transport (menu actions)

    @pyqtSlot(bool)
    def slot_transportPlayPause(self, toggled):
        if self.host.isPlugin or not self.host.is_engine_running():
            return

        if toggled:
            self.host.transport_play()
        else:
            self.host.transport_pause()

        self.refreshTransport()

    @pyqtSlot()
    def slot_transportStop(self):
        if self.host.isPlugin or not self.host.is_engine_running():
            return

        self.host.transport_pause()
        self.host.transport_relocate(0)

        self.refreshTransport()

    @pyqtSlot()
    def slot_transportBackwards(self):
        if self.host.isPlugin or not self.host.is_engine_running():
            return

        newFrame = self.host.get_current_transport_frame() - 100000

        newFrame = max(newFrame, 0)

        self.host.transport_relocate(newFrame)

    @pyqtSlot(float)
    def slot_transportBpmChanged(self, newValue):
        self.host.transport_bpm(newValue)

    @pyqtSlot()
    def slot_transportForwards(self):
        if (
            self.fSampleRate == 0.0
            or self.host.isPlugin
            or not self.host.is_engine_running()
        ):
            return

        newFrame = self.host.get_current_transport_frame() + int(self.fSampleRate * 2.5)
        self.host.transport_relocate(newFrame)

    @pyqtSlot(bool)
    def slot_transportJackEnabled(self, clicked):
        if not self.host.is_engine_running():
            return
        self.host.transportMode = (
            ENGINE_TRANSPORT_MODE_JACK if clicked else ENGINE_TRANSPORT_MODE_INTERNAL
        )
        self.host.set_engine_option(
            ENGINE_OPTION_TRANSPORT_MODE,
            self.host.transportMode,
            self.host.transportExtra,
        )

    @pyqtSlot(bool)
    def slot_transportLinkEnabled(self, clicked):
        if not self.host.is_engine_running():
            return
        extra = ":link:" if clicked else ""
        self.host.transportExtra = extra
        self.host.set_engine_option(
            ENGINE_OPTION_TRANSPORT_MODE,
            self.host.transportMode,
            self.host.transportExtra,
        )

    # --------------------------------------------------------------------------------------------------------
    # Other

    @pyqtSlot(bool)
    def slot_xrunClear(self):
        self.host.clear_engine_xruns()

