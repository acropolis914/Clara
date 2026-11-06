#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Clara contributors
# SPDX-License-Identifier: GPL-2.0-or-later

# Engine start/stop/config menu actions, split out of host_app.py.
# HostWindow inherits this mixin.

from carla_app import QSafeSettings
from carla_backend import (
    ENGINE_OPTION_AUDIO_BUFFER_SIZE,
    ENGINE_OPTION_AUDIO_DEVICE,
    ENGINE_OPTION_AUDIO_SAMPLE_RATE,
    NSM_CALLBACK_OPEN,
)
from carla_settings import DriverSettingsW, RuntimeDriverSettingsW
from carla_shared import CARLA_DEFAULT_AUDIO_DRIVER, CARLA_KEY_ENGINE_AUDIO_DRIVER
from patchcanvas import patchcanvas
from qt_compat import QMessageBox, QTimer, pyqtSlot


class EngineMenuMixin:
    # --------------------------------------------------------------------------------------------------------
    # Engine (menu actions)

    @pyqtSlot()
    def slot_engineStart(self):
        from host_app import setEngineSettings  # lazy: host_app imports this mixin

        audioDriver = setEngineSettings(self.host, self.fSavedSettings)

        firstInit = self.fFirstEngineInit
        self.fFirstEngineInit = False

        self.ui.text_logs.appendPlainText("======= Starting engine =======")

        if self.host.engine_init(audioDriver, self.fClientName):
            if firstInit and not (self.host.isControl or self.host.isPlugin):
                settings = QSafeSettings()
                lastBpm = settings.value("LastBPM", 120.0, float)
                del settings
                if lastBpm >= 20.0:
                    self.host.transport_bpm(lastBpm)
            return

        elif firstInit:
            self.ui.text_logs.appendPlainText(
                "Failed to start engine on first try, ignored"
            )
            return

        audioError = self.host.get_last_error()

        if audioError:
            QMessageBox.critical(
                self,
                self.tr("Error"),
                self.tr(
                    f"Could not connect to Audio backend '{audioDriver}', possible reasons:\n{audioError}"
                ),
            )
        else:
            QMessageBox.critical(
                self,
                self.tr("Error"),
                self.tr(f"Could not connect to Audio backend '{audioDriver}'"),
            )

    @pyqtSlot()
    def slot_engineStop(self, forced=False):
        self.ui.text_logs.appendPlainText("======= Stopping engine =======")

        if self.fPluginCount == 0 or not self.host.is_engine_running():
            self.engineStopFinal()
            return True

        if not forced:
            ask = QMessageBox.question(
                self,
                self.tr("Warning"),
                self.tr(
                    "There are still some plugins loaded, you need to remove them to stop the engine.\n"
                    "Do you want to do this now?"
                ),
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No,
            )
            if ask != QMessageBox.Yes:
                return False

        return self.slot_engineStopTryAgain()

    @pyqtSlot()
    def slot_engineConfig(self):
        engineRunning = self.host.is_engine_running()

        if engineRunning:
            dialog = RuntimeDriverSettingsW(self.fParentOrSelf, self.host)

        else:
            if self.host.isPlugin:
                driverName = "Plugin"
                driverIndex = 0
            elif self.host.audioDriverForced:
                driverName = self.host.audioDriverForced
                driverIndex = 0
            else:
                settings = QSafeSettings()
                driverName = settings.value(
                    CARLA_KEY_ENGINE_AUDIO_DRIVER, CARLA_DEFAULT_AUDIO_DRIVER, str
                )
                for i in range(self.host.get_engine_driver_count()):
                    if self.host.get_engine_driver_name(i) == driverName:
                        driverIndex = i
                        break
                else:
                    driverIndex = -1
                del settings
            dialog = DriverSettingsW(
                self.fParentOrSelf, self.host, driverIndex, driverName
            )
            dialog.ui.ico_restart.hide()
            dialog.ui.label_restart.hide()
            dialog.adjustSize()

        if not dialog.exec_():
            return

        audioDevice, bufferSize, sampleRate = dialog.getValues()

        if engineRunning:
            self.host.set_engine_buffer_size_and_sample_rate(bufferSize, sampleRate)
        else:
            self.host.set_engine_option(ENGINE_OPTION_AUDIO_DEVICE, 0, audioDevice)
            self.host.set_engine_option(ENGINE_OPTION_AUDIO_BUFFER_SIZE, bufferSize, "")
            self.host.set_engine_option(ENGINE_OPTION_AUDIO_SAMPLE_RATE, sampleRate, "")

    @pyqtSlot()
    def slot_engineStopTryAgain(self):
        if self.host.is_engine_running() and not self.host.set_engine_about_to_close():
            # 50 ms between retries: singleShot(0) spun a full CPU core while waiting
            QTimer.singleShot(50, self.slot_engineStopTryAgain)
            return False

        self.engineStopFinal()
        return True

    def engineStopFinal(self):
        patchcanvas.handleAllPluginsRemoved()
        self.killTimers()

        if self.fCustomStopAction == self.CUSTOM_ACTION_PROJECT_LOAD:
            self.removeAllPlugins()
        else:
            self.fProjectFilename = ""
            self.setProperWindowTitle()
            if self.fPluginCount != 0:
                self.fCurrentlyRemovingAllPlugins = True
                self.projectLoadingStarted()

        if self.host.is_engine_running() and not self.host.remove_all_plugins():
            self.ui.text_logs.appendPlainText(
                "Failed to remove all plugins, error was:"
            )
            self.ui.text_logs.appendPlainText(self.host.get_last_error())

        if not self.host.engine_close():
            self.ui.text_logs.appendPlainText("Failed to stop engine, error was:")
            self.ui.text_logs.appendPlainText(self.host.get_last_error())

        if self.fCustomStopAction == self.CUSTOM_ACTION_APP_CLOSE:
            self.close()
        elif self.fCustomStopAction == self.CUSTOM_ACTION_PROJECT_LOAD:
            self.slot_engineStart()
            self.loadProjectNow()
            self.host.nsm_ready(NSM_CALLBACK_OPEN)

        self.fCustomStopAction = self.CUSTOM_ACTION_NONE

