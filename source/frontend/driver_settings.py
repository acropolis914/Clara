#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2011-2025 Filipe Coelho <falktx@falktx.com>
# SPDX-License-Identifier: GPL-2.0-or-later

# ---------------------------------------------------------------------------------------------------------------------
# Imports (PyQt)

from qt_compat import (
    pyqtSlot,
    QT_VERSION,
    Qt,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFont,
    QFontDatabase,
    QHeaderView,
    QIcon,
    QSize,
    QCheckBox,
    QComboBox,
    QSlider,
    QSpinBox,
    QLabel,
    QHBoxLayout,
    QGroupBox,
    QFormLayout,
    QApplication,
    QPalette,
    QTimer,
)

# ---------------------------------------------------------------------------------------------------------------------
# Imports (Custom)

import ui_carla_settings
import ui_carla_settings_driver
from carla_backend import (
    CARLA_OS_LINUX,
    CARLA_OS_MAC,
    CARLA_OS_WIN,
    ENGINE_DRIVER_DEVICE_CAN_TRIPLE_BUFFER,
    ENGINE_DRIVER_DEVICE_HAS_CONTROL_PANEL,
    ENGINE_DRIVER_DEVICE_VARIABLE_BUFFER_SIZE,
    ENGINE_DRIVER_DEVICE_VARIABLE_SAMPLE_RATE,
    ENGINE_OPTION_FILE_PATH,
    ENGINE_OPTION_PLUGIN_PATH,
    ENGINE_PROCESS_MODE_CONTINUOUS_RACK,
    FILE_AUDIO,
    FILE_MIDI,
    PLUGIN_CLAP,
    PLUGIN_DSSI,
    PLUGIN_JSFX,
    PLUGIN_LADSPA,
    PLUGIN_LV2,
    PLUGIN_SF2,
    PLUGIN_SFZ,
    PLUGIN_VST2,
    PLUGIN_VST3,
)
from carla_shared import (
    CARLA_DEFAULT_AUDIO_BUFFER_SIZE,
    CARLA_DEFAULT_AUDIO_DRIVER,
    CARLA_DEFAULT_AUDIO_SAMPLE_RATE,
    CARLA_DEFAULT_AUDIO_TRIPLE_BUFFER,
    CARLA_DEFAULT_CANVAS_ANTIALIASING,
    CARLA_DEFAULT_CANVAS_AUTO_HIDE_GROUPS,
    CARLA_DEFAULT_CANVAS_AUTO_SELECT_ITEMS,
    CARLA_DEFAULT_CANVAS_EYE_CANDY,
    CARLA_DEFAULT_CANVAS_FANCY_EYE_CANDY,
    CARLA_DEFAULT_CANVAS_FULL_REPAINTS,
    CARLA_DEFAULT_CANVAS_HQ_ANTIALIASING,
    CARLA_DEFAULT_CANVAS_INLINE_DISPLAYS,
    CARLA_DEFAULT_CANVAS_LINE_OPACITY,
    CARLA_DEFAULT_CANVAS_LINE_STROKE,
    CARLA_DEFAULT_CANVAS_LINE_STYLE,
    CARLA_DEFAULT_CANVAS_NODE_MIN_WIDTH,
    CARLA_DEFAULT_CANVAS_NODE_RADIUS,
    CARLA_DEFAULT_CANVAS_ROUNDED_NODES,
    CARLA_DEFAULT_CANVAS_SIZE,
    # CARLA_DEFAULT_MAIN_EXPERIMENTAL,
    CARLA_DEFAULT_CANVAS_THEME,
    CARLA_DEFAULT_CANVAS_USE_BEZIER_LINES,
    CARLA_DEFAULT_CANVAS_USE_OPENGL,
    CARLA_DEFAULT_CLAP_PATH,
    CARLA_DEFAULT_DSSI_PATH,
    CARLA_DEFAULT_EXPERIMENTAL_JACK_APPS,
    CARLA_DEFAULT_EXPERIMENTAL_LOAD_LIB_GLOBAL,
    CARLA_DEFAULT_EXPERIMENTAL_LV2_EXPORT,
    CARLA_DEFAULT_EXPERIMENTAL_PLUGIN_BRIDGES,
    CARLA_DEFAULT_EXPERIMENTAL_PREVENT_BAD_BEHAVIOUR,
    CARLA_DEFAULT_EXPERIMENTAL_WINE_BRIDGES,
    CARLA_DEFAULT_FILE_PATH_AUDIO,
    CARLA_DEFAULT_FILE_PATH_MIDI,
    CARLA_DEFAULT_FORCE_STEREO,
    CARLA_DEFAULT_JSFX_PATH,
    CARLA_DEFAULT_LADSPA_PATH,
    CARLA_DEFAULT_LV2_PATH,
    CARLA_DEFAULT_MAIN_AUTOSAVE_ENABLED,
    CARLA_DEFAULT_MAIN_AUTOSAVE_INTERVAL,
    CARLA_DEFAULT_MAIN_AUTOSAVE_MAX,
    CARLA_DEFAULT_MAIN_LOG_TO_CONSOLE,
    CARLA_DEFAULT_MAIN_CLASSIC_SKIN,
    CARLA_DEFAULT_MAIN_CONFIRM_EXIT,
    CARLA_DEFAULT_MAIN_MINIMIZE_TO_TRAY,
    CARLA_DEFAULT_MAIN_PRO_THEME_COLOR,
    CARLA_DEFAULT_MAIN_PROJECT_FOLDER,
    CARLA_DEFAULT_MAIN_REFRESH_INTERVAL,
    CARLA_DEFAULT_MAIN_SHOW_LOGS,
    CARLA_DEFAULT_MAIN_SYSTEM_ICONS,
    CARLA_DEFAULT_MAIN_USE_PRO_THEME,
    CARLA_DEFAULT_MANAGE_UIS,
    CARLA_DEFAULT_MAX_PARAMETERS,
    CARLA_DEFAULT_OSC_ENABLED,
    CARLA_DEFAULT_OSC_TCP_PORT_ENABLED,
    CARLA_DEFAULT_OSC_TCP_PORT_NUMBER,
    CARLA_DEFAULT_OSC_TCP_PORT_RANDOM,
    CARLA_DEFAULT_OSC_UDP_PORT_ENABLED,
    CARLA_DEFAULT_OSC_UDP_PORT_NUMBER,
    CARLA_DEFAULT_OSC_UDP_PORT_RANDOM,
    CARLA_DEFAULT_PREFER_PLUGIN_BRIDGES,
    CARLA_DEFAULT_PREFER_UI_BRIDGES,
    CARLA_DEFAULT_PROCESS_MODE,
    CARLA_DEFAULT_RESET_XRUNS,
    CARLA_DEFAULT_SF2_PATH,
    CARLA_DEFAULT_SFZ_PATH,
    CARLA_DEFAULT_UI_BRIDGES_TIMEOUT,
    CARLA_DEFAULT_UIS_ALWAYS_ON_TOP,
    CARLA_DEFAULT_VST2_PATH,
    CARLA_DEFAULT_VST3_PATH,
    CARLA_DEFAULT_WINE_AUTO_PREFIX,
    CARLA_DEFAULT_WINE_BASE_RT_PRIO,
    CARLA_DEFAULT_WINE_EXECUTABLE,
    CARLA_DEFAULT_WINE_FALLBACK_PREFIX,
    CARLA_DEFAULT_WINE_RT_PRIO_ENABLED,
    CARLA_DEFAULT_WINE_SERVER_RT_PRIO,
    CARLA_KEY_CANVAS_ANTIALIASING,
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
    CARLA_KEY_CANVAS_SIZE,
    CARLA_KEY_CANVAS_THEME,
    CARLA_KEY_CANVAS_USE_BEZIER_LINES,
    CARLA_KEY_CANVAS_USE_OPENGL,
    CARLA_KEY_ENGINE_AUDIO_DRIVER,
    CARLA_KEY_ENGINE_DRIVER_PREFIX,
    CARLA_KEY_ENGINE_FORCE_STEREO,
    CARLA_KEY_ENGINE_MANAGE_UIS,
    CARLA_KEY_ENGINE_MAX_PARAMETERS,
    CARLA_KEY_ENGINE_PREFER_PLUGIN_BRIDGES,
    CARLA_KEY_ENGINE_PREFER_UI_BRIDGES,
    CARLA_KEY_ENGINE_PROCESS_MODE,
    CARLA_KEY_ENGINE_RESET_XRUNS,
    CARLA_KEY_ENGINE_UI_BRIDGES_TIMEOUT,
    CARLA_KEY_ENGINE_UIS_ALWAYS_ON_TOP,
    CARLA_KEY_EXPERIMENTAL_EXPORT_LV2,
    CARLA_KEY_EXPERIMENTAL_JACK_APPS,
    CARLA_KEY_EXPERIMENTAL_LOAD_LIB_GLOBAL,
    CARLA_KEY_EXPERIMENTAL_PLUGIN_BRIDGES,
    CARLA_KEY_EXPERIMENTAL_PREVENT_BAD_BEHAVIOUR,
    CARLA_KEY_EXPERIMENTAL_WINE_BRIDGES,
    CARLA_KEY_MAIN_AUTOSAVE_ENABLED,
    CARLA_KEY_MAIN_AUTOSAVE_INTERVAL,
    CARLA_KEY_MAIN_AUTOSAVE_MAX,
    CARLA_KEY_MAIN_LOG_TO_CONSOLE,
    CARLA_KEY_MAIN_CLASSIC_SKIN,
    CARLA_KEY_MAIN_CONFIRM_EXIT,
    CARLA_KEY_MAIN_EXPERIMENTAL,
    CARLA_KEY_MAIN_PRO_THEME_COLOR,
    CARLA_KEY_MAIN_PROJECT_FOLDER,
    CARLA_KEY_MAIN_REFRESH_INTERVAL,
    CARLA_KEY_MAIN_SHOW_LOGS,
    CARLA_KEY_MAIN_SYSTEM_ICONS,
    CARLA_KEY_MAIN_MINIMIZE_TO_TRAY,
    CARLA_KEY_MAIN_USE_PRO_THEME,
    CARLA_KEY_OSC_ENABLED,
    CARLA_KEY_OSC_TCP_PORT_ENABLED,
    CARLA_KEY_OSC_TCP_PORT_NUMBER,
    CARLA_KEY_OSC_TCP_PORT_RANDOM,
    CARLA_KEY_OSC_UDP_PORT_ENABLED,
    CARLA_KEY_OSC_UDP_PORT_NUMBER,
    CARLA_KEY_OSC_UDP_PORT_RANDOM,
    CARLA_KEY_PATHS_AUDIO,
    CARLA_KEY_PATHS_CLAP,
    CARLA_KEY_PATHS_DSSI,
    CARLA_KEY_PATHS_JSFX,
    CARLA_KEY_PATHS_LADSPA,
    CARLA_KEY_PATHS_LV2,
    CARLA_KEY_PATHS_MIDI,
    CARLA_KEY_PATHS_SF2,
    CARLA_KEY_PATHS_SFZ,
    CARLA_KEY_PATHS_VST2,
    CARLA_KEY_PATHS_VST3,
    CARLA_KEY_WINE_AUTO_PREFIX,
    CARLA_KEY_WINE_BASE_RT_PRIO,
    CARLA_KEY_WINE_EXECUTABLE,
    CARLA_KEY_WINE_FALLBACK_PREFIX,
    CARLA_KEY_WINE_RT_PRIO_ENABLED,
    CARLA_KEY_WINE_SERVER_RT_PRIO,
    fontMetricsHorizontalAdvance,
    gCarla,
    getAndSetPath,
    getIcon,
    splitter,
)
from patchcanvas.linealgos import line_algorithms
from patchcanvas.theme import Theme, getThemeName
from utils import QSafeSettings
from settings_schema import (
    SettingsFormBuilder,
    GENERAL_SCHEMA,
    PATCHBAY_SCHEMA,
    OSC_SCHEMA,
    WINE_SCHEMA,
    EXPERIMENTAL_SCHEMA,
)

# ---------------------------------------------------------------------------------------------------------------------
# ...

BUFFER_SIZE_LIST = (16, 32, 64, 128, 256, 512, 1024, 2048, 4096, 8192)
SAMPLE_RATE_LIST = (22050, 32000, 44100, 48000, 88200, 96000, 176400, 192000)

# ---------------------------------------------------------------------------------------------------------------------
# Driver Settings


class DriverSettingsW(QDialog):
    AUTOMATIC_OPTION = "(Auto)"

    def __init__(self, parent, host, driverIndex, driverName):
        QDialog.__init__(self, parent)
        self.host = host
        self.ui = ui_carla_settings_driver.Ui_DriverSettingsW()
        self.ui.setupUi(self)

        # -------------------------------------------------------------------------------------------------------------
        # Internal stuff

        self.fDriverIndex = driverIndex
        self.fDriverName = driverName
        self.fDeviceNames = host.get_engine_driver_device_names(driverIndex)

        self.fBufferSizes = BUFFER_SIZE_LIST
        self.fSampleRates = SAMPLE_RATE_LIST

        # -------------------------------------------------------------------------------------------------------------
        # Set-up GUI

        for name in self.fDeviceNames:
            self.ui.cb_device.addItem(name)

        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)

        if CARLA_OS_MAC:
            self.setWindowModality(Qt.WindowModal)

        # -------------------------------------------------------------------------------------------------------------
        # Load settings

        self.loadSettings()

        # -------------------------------------------------------------------------------------------------------------
        # Set-up connections

        self.accepted.connect(self.slot_saveSettings)
        self.ui.b_panel.clicked.connect(self.slot_showDevicePanel)
        self.ui.cb_device.currentIndexChanged.connect(self.slot_updateDeviceInfo)

    # -----------------------------------------------------------------------------------------------------------------

    def getValues(self):
        audioDevice = self.ui.cb_device.currentText()
        bufferSize = self.ui.cb_buffersize.currentText()
        sampleRate = self.ui.cb_samplerate.currentText()

        if bufferSize == self.AUTOMATIC_OPTION:
            bufferSize = "0"
        if sampleRate == self.AUTOMATIC_OPTION:
            sampleRate = "0"

        return (audioDevice, int(bufferSize), int(sampleRate))

    # -----------------------------------------------------------------------------------------------------------------

    def loadSettings(self):
        settings = QSafeSettings("falkTX", "Carla2")

        args = (CARLA_KEY_ENGINE_DRIVER_PREFIX, self.fDriverName)
        audioDevice = settings.value("%s%s/Device" % args, "", str)
        audioBufferSize = settings.value(
            "%s%s/BufferSize" % args, CARLA_DEFAULT_AUDIO_BUFFER_SIZE, int
        )
        audioSampleRate = settings.value(
            "%s%s/SampleRate" % args, CARLA_DEFAULT_AUDIO_SAMPLE_RATE, int
        )
        audioTripleBuffer = settings.value(
            "%s%s/TripleBuffer" % args, CARLA_DEFAULT_AUDIO_TRIPLE_BUFFER, bool
        )

        if audioDevice and audioDevice in self.fDeviceNames:
            self.ui.cb_device.setCurrentIndex(self.fDeviceNames.index(audioDevice))
        else:
            self.ui.cb_device.setCurrentIndex(-1)

        # fill combo-boxes first
        self.slot_updateDeviceInfo()

        if audioBufferSize and audioBufferSize in self.fBufferSizes:
            self.ui.cb_buffersize.setCurrentIndex(
                self.fBufferSizes.index(audioBufferSize)
            )
        elif self.fBufferSizes == BUFFER_SIZE_LIST:
            self.ui.cb_buffersize.setCurrentIndex(
                BUFFER_SIZE_LIST.index(CARLA_DEFAULT_AUDIO_BUFFER_SIZE)
            )
        else:
            self.ui.cb_buffersize.setCurrentIndex(int(len(self.fBufferSizes) / 2))

        if audioSampleRate and audioSampleRate in self.fSampleRates:
            self.ui.cb_samplerate.setCurrentIndex(
                self.fSampleRates.index(audioSampleRate)
            )
        elif self.fSampleRates == SAMPLE_RATE_LIST:
            self.ui.cb_samplerate.setCurrentIndex(
                SAMPLE_RATE_LIST.index(CARLA_DEFAULT_AUDIO_SAMPLE_RATE)
            )
        else:
            self.ui.cb_samplerate.setCurrentIndex(int(len(self.fSampleRates) / 2))

        self.ui.cb_triple_buffer.setChecked(
            audioTripleBuffer and self.ui.cb_triple_buffer.isEnabled()
        )

    # -----------------------------------------------------------------------------------------------------------------

    @pyqtSlot()
    def slot_saveSettings(self):
        settings = QSafeSettings("falkTX", "Carla2")

        bufferSize = self.ui.cb_buffersize.currentText()
        sampleRate = self.ui.cb_samplerate.currentText()

        if bufferSize == self.AUTOMATIC_OPTION:
            bufferSize = "0"
        if sampleRate == self.AUTOMATIC_OPTION:
            sampleRate = "0"

        args = (CARLA_KEY_ENGINE_DRIVER_PREFIX, self.fDriverName)
        settings.setValue("%s%s/Device" % args, self.ui.cb_device.currentText())
        settings.setValue("%s%s/BufferSize" % args, bufferSize)
        settings.setValue("%s%s/SampleRate" % args, sampleRate)
        settings.setValue(
            "%s%s/TripleBuffer" % args, self.ui.cb_triple_buffer.isChecked()
        )

    # -----------------------------------------------------------------------------------------------------------------

    @pyqtSlot()
    def slot_showDevicePanel(self):
        self.host.show_engine_driver_device_control_panel(
            self.fDriverIndex, self.ui.cb_device.currentText()
        )

    @pyqtSlot()
    def slot_updateDeviceInfo(self):
        deviceName = self.ui.cb_device.currentText()

        oldBufferSize = self.ui.cb_buffersize.currentText()
        oldSampleRate = self.ui.cb_samplerate.currentText()

        self.ui.cb_buffersize.clear()
        self.ui.cb_samplerate.clear()

        driverDeviceInfo = self.host.get_engine_driver_device_info(
            self.fDriverIndex, deviceName
        )
        driverDeviceHints = driverDeviceInfo["hints"]
        self.fBufferSizes = driverDeviceInfo["bufferSizes"]
        self.fSampleRates = driverDeviceInfo["sampleRates"]

        if driverDeviceHints & ENGINE_DRIVER_DEVICE_CAN_TRIPLE_BUFFER:
            self.ui.cb_triple_buffer.setEnabled(True)
        else:
            self.ui.cb_triple_buffer.setEnabled(False)

        if driverDeviceHints & ENGINE_DRIVER_DEVICE_HAS_CONTROL_PANEL:
            self.ui.b_panel.setEnabled(True)
        else:
            self.ui.b_panel.setEnabled(False)

        if self.fBufferSizes:
            match = False
            for bsize in self.fBufferSizes:
                sbsize = str(bsize)
                self.ui.cb_buffersize.addItem(sbsize)

                if oldBufferSize == sbsize:
                    match = True
                    self.ui.cb_buffersize.setCurrentIndex(
                        self.ui.cb_buffersize.count() - 1
                    )

            if not match:
                if CARLA_DEFAULT_AUDIO_BUFFER_SIZE in self.fBufferSizes:
                    self.ui.cb_buffersize.setCurrentIndex(
                        self.fBufferSizes.index(CARLA_DEFAULT_AUDIO_BUFFER_SIZE)
                    )
                else:
                    self.ui.cb_buffersize.setCurrentIndex(
                        int(len(self.fBufferSizes) / 2)
                    )

        else:
            self.ui.cb_buffersize.addItem(self.AUTOMATIC_OPTION)
            self.ui.cb_buffersize.setCurrentIndex(0)

        if self.fSampleRates:
            match = False
            for srate in self.fSampleRates:
                ssrate = str(int(srate))
                self.ui.cb_samplerate.addItem(ssrate)

                if oldSampleRate == ssrate:
                    match = True
                    self.ui.cb_samplerate.setCurrentIndex(
                        self.ui.cb_samplerate.count() - 1
                    )

            if not match:
                if CARLA_DEFAULT_AUDIO_SAMPLE_RATE in self.fSampleRates:
                    self.ui.cb_samplerate.setCurrentIndex(
                        self.fSampleRates.index(CARLA_DEFAULT_AUDIO_SAMPLE_RATE)
                    )
                else:
                    self.ui.cb_samplerate.setCurrentIndex(
                        int(len(self.fSampleRates) / 2)
                    )

        else:
            self.ui.cb_samplerate.addItem(self.AUTOMATIC_OPTION)
            self.ui.cb_samplerate.setCurrentIndex(0)


# ---------------------------------------------------------------------------------------------------------------------
# Runtime Driver Settings


class RuntimeDriverSettingsW(QDialog):
    def __init__(self, parent, host):
        QDialog.__init__(self, parent)
        self.host = host
        self.ui = ui_carla_settings_driver.Ui_DriverSettingsW()
        self.ui.setupUi(self)

        driverDeviceInfo = host.get_runtime_engine_driver_device_info()

        # -------------------------------------------------------------------------------------------------------------
        # Set-up GUI

        self.ui.cb_device.clear()
        self.ui.cb_buffersize.clear()
        self.ui.cb_samplerate.clear()
        self.ui.cb_triple_buffer.hide()
        self.ui.ico_restart.hide()
        self.ui.label_restart.hide()

        self.ui.layout_triple_buffer.takeAt(2)
        self.ui.layout_triple_buffer.takeAt(1)
        self.ui.layout_triple_buffer.takeAt(0)
        self.ui.verticalLayout.removeItem(self.ui.layout_triple_buffer)

        self.ui.layout_restart.takeAt(3)
        self.ui.layout_restart.takeAt(2)
        self.ui.layout_restart.takeAt(1)
        self.ui.layout_restart.takeAt(0)
        self.ui.verticalLayout.removeItem(self.ui.layout_restart)

        self.adjustSize()
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)

        if CARLA_OS_MAC:
            self.setWindowModality(Qt.WindowModal)

        # -------------------------------------------------------------------------------------------------------------
        # Load runtime settings

        if host.is_engine_running():
            self.ui.cb_device.addItem(driverDeviceInfo["name"])
            self.ui.cb_device.setCurrentIndex(0)
            self.ui.cb_device.setEnabled(False)
        else:
            self.ui.cb_device.addItem(driverDeviceInfo["name"])
            self.ui.cb_device.setCurrentIndex(0)

        if driverDeviceInfo["bufferSizes"]:
            for bsize in driverDeviceInfo["bufferSizes"]:
                sbsize = str(bsize)
                self.ui.cb_buffersize.addItem(sbsize)

                if driverDeviceInfo["bufferSize"] == bsize:
                    self.ui.cb_buffersize.setCurrentIndex(
                        self.ui.cb_buffersize.count() - 1
                    )

        else:
            self.ui.cb_buffersize.addItem(DriverSettingsW.AUTOMATIC_OPTION)
            self.ui.cb_buffersize.setCurrentIndex(0)

        if (
            driverDeviceInfo["hints"] & ENGINE_DRIVER_DEVICE_VARIABLE_BUFFER_SIZE
        ) == 0x0:
            self.ui.cb_buffersize.setEnabled(False)

        if driverDeviceInfo["sampleRates"]:
            for srate in driverDeviceInfo["sampleRates"]:
                ssrate = str(int(srate))
                self.ui.cb_samplerate.addItem(ssrate)

                if driverDeviceInfo["sampleRate"] == srate:
                    self.ui.cb_samplerate.setCurrentIndex(
                        self.ui.cb_samplerate.count() - 1
                    )

        else:
            self.ui.cb_samplerate.addItem(DriverSettingsW.AUTOMATIC_OPTION)
            self.ui.cb_samplerate.setCurrentIndex(0)

        if (
            driverDeviceInfo["hints"] & ENGINE_DRIVER_DEVICE_VARIABLE_SAMPLE_RATE
        ) == 0x0:
            self.ui.cb_samplerate.setEnabled(False)

        if (driverDeviceInfo["hints"] & ENGINE_DRIVER_DEVICE_HAS_CONTROL_PANEL) == 0x0:
            self.ui.b_panel.setEnabled(False)

        # -------------------------------------------------------------------------------------------------------------
        # Set-up connections

        self.ui.b_panel.clicked.connect(self.slot_showDevicePanel)

    # -----------------------------------------------------------------------------------------------------------------

    def getValues(self):
        audioDevice = self.ui.cb_device.currentText()
        bufferSize = self.ui.cb_buffersize.currentText()
        sampleRate = self.ui.cb_samplerate.currentText()

        if bufferSize == DriverSettingsW.AUTOMATIC_OPTION:
            bufferSize = "0"
        if sampleRate == DriverSettingsW.AUTOMATIC_OPTION:
            sampleRate = "0"

        return (audioDevice, int(bufferSize), int(sampleRate))

    # -----------------------------------------------------------------------------------------------------------------

    @pyqtSlot()
    def slot_showDevicePanel(self):
        self.host.show_engine_device_control_panel()


# ---------------------------------------------------------------------------------------------------------------------
# Settings Dialog

