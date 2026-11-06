#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Clara contributors
# SPDX-License-Identifier: GPL-2.0-or-later

# Logs, timers, misc helpers and internal utilities, split out of host_app.py.
# HostWindow inherits this mixin.

import json
import os
import sys
from ctypes import pointer

from carla_backend import (
    NSM_CALLBACK_ANNOUNCE,
    NSM_CALLBACK_ERROR,
    NSM_CALLBACK_HIDE_OPTIONAL_GUI,
    NSM_CALLBACK_INIT,
    NSM_CALLBACK_OPEN,
    NSM_CALLBACK_SAVE,
    NSM_CALLBACK_SESSION_IS_LOADED,
    NSM_CALLBACK_SET_CLIENT_NAME_ID,
    NSM_CALLBACK_SHOW_OPTIONAL_GUI,
    PLUGIN_LADSPA,
    PLUGIN_SF2,
)
from carla_logger import logger
from carla_shared import (
    CARLA_KEY_MAIN_PROJECT_FOLDER,
    CARLA_KEY_MAIN_REFRESH_INTERVAL,
    HOME,
)
from carla_widgets import PluginEdit
from patchcanvas import patchcanvas
from project_storage import storage_manager
from qt_compat import (
    QApplication,
    QFileDialog,
    QFileInfo,
    QMessageBox,
    QTimer,
    Qt,
    pyqtSlot,
)

try:
    import ladspa_rdf

    haveLRDF = True
except ImportError:
    ladspa_rdf = None
    haveLRDF = False


class HostInternalMixin:
    # --------------------------------------------------------------------------------------------------------
    # Logs autoscroll, save and clear

    @pyqtSlot(int)
    def slot_toggleLogAutoscroll(self, checkState):
        self.autoscrollOnNewLog = checkState == Qt.Checked
        if self.autoscrollOnNewLog:
            self.ui.text_logs.verticalScrollBar().setValue(
                self.ui.text_logs.verticalScrollBar().maximum()
            )

    @pyqtSlot(int)
    def slot_logSliderMoved(self, slider_pos):
        if (
            self.ui.text_logs.verticalScrollBar().hasTracking()
            or self.autoscrollOnNewLog
        ):
            self.lastLogSliderPos = slider_pos
        else:
            self.ui.text_logs.verticalScrollBar().setValue(self.lastLogSliderPos)

    @pyqtSlot()
    def slot_logButtonsState(self, enabled=True):
        self.ui.logs_clear.setEnabled(enabled)
        self.ui.logs_save.setEnabled(enabled)

    @pyqtSlot()
    def slot_logSave(self):
        filename = os.path.join(
            self.fSavedSettings[CARLA_KEY_MAIN_PROJECT_FOLDER], "carla_log.txt"
        )
        filename, _ = QFileDialog.getSaveFileName(self, self.tr("Save Logs"), filename)

        if not filename:
            return

        try:
            with open(filename, "w") as logfile:
                logfile.write(self.ui.text_logs.toPlainText())
                logfile.close()
        except Exception:
            return

    @pyqtSlot()
    def slot_logClear(self):
        self._logPendingLines = []
        logger.history.clear()
        self.ui.text_logs.clear()
        self.ui.text_logs.appendPlainText("======= Logs cleared ========")
        self.slot_logButtonsState(False)

    @pyqtSlot(object)
    def slot_onLogAdded(self, entry):
        if not hasattr(self, "log_tag_checkboxes"):
            return
        # Check if entry's tag is checked
        chk = self.log_tag_checkboxes.get(entry.tag)
        if chk is not None and not chk.isChecked():
            return
        self._logPendingLines.append(entry.formatted_ui())

    @pyqtSlot()
    def _flushLogPending(self):
        if not self._logPendingLines:
            return
        lines = self._logPendingLines
        self._logPendingLines = []
        if hasattr(self, "_orig_log_append"):
            self._orig_log_append("\n".join(lines))

    @pyqtSlot()
    def slot_logFilterChanged(self):
        """Re-render visible logs from history when checklist changes"""
        if not hasattr(self, "_orig_log_append"):
            return
        self._logPendingLines = []
        self.ui.text_logs.clear()
        for entry in logger.history:
            chk = self.log_tag_checkboxes.get(entry.tag)
            if chk is None or chk.isChecked():
                self._orig_log_append(entry.formatted_ui())

    # --------------------------------------------------------------------------------------------------------
    # Timers

    def startTimers(self):
        if self.fIdleTimerFast == 0:
            self.fIdleTimerFast = self.startTimer(
                self.fSavedSettings[CARLA_KEY_MAIN_REFRESH_INTERVAL]
            )

        if self.fIdleTimerSlow == 0:
            self.fIdleTimerSlow = self.startTimer(
                self.fSavedSettings[CARLA_KEY_MAIN_REFRESH_INTERVAL] * 4
            )

    def restartTimersIfNeeded(self):
        if self.fIdleTimerFast != 0:
            self.killTimer(self.fIdleTimerFast)
            self.fIdleTimerFast = self.startTimer(
                self.fSavedSettings[CARLA_KEY_MAIN_REFRESH_INTERVAL]
            )

        if self.fIdleTimerSlow != 0:
            self.killTimer(self.fIdleTimerSlow)
            self.fIdleTimerSlow = self.startTimer(
                self.fSavedSettings[CARLA_KEY_MAIN_REFRESH_INTERVAL] * 4
            )

    def killTimers(self):
        if self.fIdleTimerFast != 0:
            self.killTimer(self.fIdleTimerFast)
            self.fIdleTimerFast = 0

        if self.fIdleTimerSlow != 0:
            self.killTimer(self.fIdleTimerSlow)
            self.fIdleTimerSlow = 0

    # --------------------------------------------------------------------------------------------------------
    # Misc

    @pyqtSlot(bool)
    def slot_toolbarVisibilityChanged(self, visible):
        self.ui.toolBar.blockSignals(True)
        self.ui.toolBar.setEnabled(visible)
        self.ui.toolBar.blockSignals(False)
        self.ui.act_settings_show_toolbar.setChecked(visible)

    @pyqtSlot(int)
    def slot_tabChanged(self, index):
        isPatchbayTab = (index == 1)
        if hasattr(self, "tabSplit") and self.ui.tabWidget.indexOf(self.tabSplit) == index:
            isPatchbayTab = True

        if not isPatchbayTab:
            return

        if getattr(self, "fNeedCanvasRefresh", False):
            self.fNeedCanvasRefresh = False
            self.slot_canvasRefresh()

        self.ui.graphicsView.setFocus()

    @pyqtSlot(int)
    def slot_handleReloadAllCallback(self, pluginId):
        if pluginId >= self.fPluginCount:
            return

        pitem = self.fPluginList[pluginId]
        if pitem is None:
            return

        pitem.recreateWidget()

    # --------------------------------------------------------------------------------------------------------

    @pyqtSlot(int, int, str)
    def slot_handleNSMCallback(self, opcode, valueInt, valueStr):
        if opcode == NSM_CALLBACK_INIT:
            return

        # Error
        elif opcode == NSM_CALLBACK_ERROR:
            pass

        # Reply
        elif opcode == NSM_CALLBACK_ANNOUNCE:
            self.fFirstEngineInit = False
            self.fSessionManagerName = valueStr
            self.setProperWindowTitle()

            # If NSM server does not support optional-gui, revert our initial assumptions that it does
            if (valueInt & (1 << 1)) == 0x0:
                self.fWindowCloseHideGui = False
                self.ui.act_file_quit.setText(self.tr("&Quit"))
                QApplication.instance().setQuitOnLastWindowClosed(True)
                self.show()

        # Open
        elif opcode == NSM_CALLBACK_OPEN:
            self.fProjectFilename = QFileInfo(valueStr + storage_manager.default_extension()).absoluteFilePath()
            self.setProperWindowTitle()

            self.fCustomStopAction = self.CUSTOM_ACTION_PROJECT_LOAD
            self.slot_engineStop(True)
            return

        # Save
        elif opcode == NSM_CALLBACK_SAVE:
            self.saveProjectNow()

        # Session is Loaded
        elif opcode == NSM_CALLBACK_SESSION_IS_LOADED:
            pass

        # Show Optional Gui
        elif opcode == NSM_CALLBACK_SHOW_OPTIONAL_GUI:
            self.show()

        # Hide Optional Gui
        elif opcode == NSM_CALLBACK_HIDE_OPTIONAL_GUI:
            self.hideForNSM()

        # Set client name
        elif opcode == NSM_CALLBACK_SET_CLIENT_NAME_ID:
            self.fClientName = valueStr
            return

        self.host.nsm_ready(opcode)

    # --------------------------------------------------------------------------------------------------------

    def fixLogText(self, text):
        return (
            text.replace("\x1b[30;1m", "")
            .replace("\x1b[31m", "")
            .replace("\x1b[0m", "")
        )

    @pyqtSlot(int, int, int, int, float, str)
    def slot_handleDebugCallback(
        self, pluginId, value1, value2, value3, valuef, valueStr
    ):
        self.ui.text_logs.appendPlainText(self.fixLogText(valueStr))

    @pyqtSlot(str)
    def slot_handleInfoCallback(self, info):
        QMessageBox.information(self, "Information", info)

    @pyqtSlot(str)
    def slot_handleErrorCallback(self, error):
        QMessageBox.critical(self, "Error", error)

    @pyqtSlot()
    def slot_handleQuitCallback(self):
        self.fIsProjectLoading = False
        self.killTimers()
        self.removeAllPlugins()
        self.projectLoadingFinished(False)

    @pyqtSlot(int)
    def slot_handleInlineDisplayRedrawCallback(self, pluginId):
        # FIXME
        if (
            self.fIdleTimerSlow != 0
            and self.fIdleTimerFast != 0
            and pluginId < self.fPluginCount
            and not self.fIsProjectLoading
        ):
            patchcanvas.redrawPluginGroup(pluginId)

    # --------------------------------------------------------------------------------------------------------

    @pyqtSlot()
    def slot_handleSIGUSR1(self):
        print("Got SIGUSR1 -> Saving project now")
        self.slot_fileSave()

    @pyqtSlot()
    def slot_handleSIGTERM(self):
        print("Got SIGTERM -> Closing now")
        self.fCustomStopAction = self.CUSTOM_ACTION_APP_CLOSE
        # A stuck plugin bridge must never hold a logout/shutdown hostage.
        QTimer.singleShot(4000, lambda: os._exit(0))
        self.close()

    @pyqtSlot()
    def slot_handleSIGINT(self):
        # Ctrl+C from a terminal. There is nothing to do (and no UI to prompt
        # with) when launched outside a terminal or without a system tray, so
        # keep the old immediate-close behaviour for those cases.
        is_tty = False
        try:
            is_tty = os.isatty(0)
        except Exception:
            is_tty = False
        if not is_tty:
            print("Got SIGINT -> Closing now")
            self.fCustomStopAction = self.CUSTOM_ACTION_APP_CLOSE
            self.fForceQuit = True
            self.close()
            return
        # Defer so the prompt runs from the event loop, not the signal frame.
        QTimer.singleShot(0, self._promptSIGINT)

    def _promptSIGINT(self):
        # Ctrl+C came from a terminal, so ask right there instead of popping up
        # a GUI dialog. Write to the saved terminal fd: fd 1 is captured by the
        # logger, and routing this through it would print the prompt as log lines.
        has_tray = getattr(self, "fSystemTrayIcon", None) is not None
        answer = ""

        try:
            from carla_logger import logger
            out = getattr(logger, "_terminal_out", None) or sys.__stdout__
            out.write("\n")
            out.write("Ctrl+C received from the terminal.\n")
            out.write("Quit Clara now?\n")
            out.write("  [Enter] Quit now (default)\n")
            if has_tray:
                out.write("  [T]     Keep running in the system tray\n")
            out.write("Choice [Enter/T]: " if has_tray else "Choice [Enter]: ")
            out.flush()
        except Exception:
            pass

        try:
            answer = input().strip().lower()
        except Exception:
            answer = ""

        if has_tray and answer.startswith("t"):
            print("Keeping Clara running in the system tray; detached from terminal.")
            self._minimizeToSystemTray()
            self._detachFromTerminal()
        else:
            print("Quitting Clara now.")
            self.fCustomStopAction = self.CUSTOM_ACTION_APP_CLOSE
            self.fForceQuit = True
            self.close()

    def _detachFromTerminal(self):
        # Detach from the controlling terminal so the application keeps running
        # after the terminal/shell is closed, then silence the standard streams.
        try:
            if os.name == "posix":
                try:
                    os.setsid()
                except OSError:
                    pass
                try:
                    from signal import SIGHUP, SIG_IGN, signal as _signal

                    _signal(SIGHUP, SIG_IGN)
                except Exception:
                    pass
                try:
                    devnull = os.open(os.devnull, os.O_RDWR)
                    for fd in (0, 1, 2):
                        try:
                            os.dup2(devnull, fd)
                        except OSError:
                            pass
                except Exception:
                    pass
        except Exception as ex:
            logger.warning("APP", f"Could not detach from terminal: {ex}")

    # --------------------------------------------------------------------------------------------------------
    # Internal stuff

    def getExtraPtr(self, plugin):
        ptype = plugin["type"]

        if ptype == PLUGIN_LADSPA:
            uniqueId = plugin["uniqueId"]

            self.maybeLoadRDFs()

            for rdfItem in self.fLadspaRdfList:
                if rdfItem.UniqueID == uniqueId:
                    return pointer(rdfItem)

        elif ptype == PLUGIN_SF2:
            if plugin["name"].lower().endswith(" (16 outputs)"):
                return self._true

        return None

    def maybeLoadRDFs(self):
        if not self.fLadspaRdfNeedsUpdate:
            return

        self.fLadspaRdfNeedsUpdate = False
        self.fLadspaRdfList = []

        if not haveLRDF:
            return

        settingsDir = os.path.join(HOME, ".config", "falkTX")
        frLadspaFile = os.path.join(settingsDir, "ladspa_rdf.db")

        if os.path.exists(frLadspaFile):
            frLadspa = open(frLadspaFile, "r")

            try:
                self.fLadspaRdfList = ladspa_rdf.get_c_ladspa_rdfs(json.load(frLadspa))
            except Exception:
                pass

            frLadspa.close()

    # --------------------------------------------------------------------------------------------------------

    def getPluginCount(self):
        return len([p for p in self.fPluginList if p is not None])

    def getPluginItem(self, pluginId):
        if pluginId < 0 or pluginId >= len(self.fPluginList):
            return None

        return self.fPluginList[pluginId]

    def getPluginEditDialog(self, pluginId):
        if pluginId >= self.fPluginCount:
            return None

        pitem = self.fPluginList[pluginId]
        if pitem is None:
            return None
        if False:
            return PluginEdit(self, self.host, 0)

        return pitem.getEditDialog()

    def getPluginSlotWidget(self, pluginId):
        if pluginId >= self.fPluginCount:
            return None

        pitem = self.fPluginList[pluginId]
        if pitem is None:
            return None
        # if False:
        # return AbstractPluginSlot()

        return pitem.getWidget()

    # --------------------------------------------------------------------------------------------------------

    def waitForPendingEvents(self):
        pass

