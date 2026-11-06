#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2011-2025 Filipe Coelho <falktx@falktx.com>
# SPDX-License-Identifier: GPL-2.0-or-later

# ------------------------------------------------------------------------------------------------------------
# Jack Application Dialog (pure Python port of jackappdialog.cpp)

import sys

from qt_compat import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileInfo,
    QFrame,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPixmap,
    QPushButton,
    QRadioButton,
    QSettings,
    QSizePolicy,
    QSpacerItem,
    QSpinBox,
    QStackedWidget,
    Qt,
    QVBoxLayout,
    QWidget,
)

# ------------------------------------------------------------------------------------------------------------
# Constants (mirrors CarlaLibJackHints.h)

LIBJACK_FLAG_CONTROL_WINDOW = 0x01
LIBJACK_FLAG_CAPTURE_FIRST_WINDOW = 0x02
LIBJACK_FLAG_AUDIO_BUFFERS_ADDITION = 0x10
LIBJACK_FLAG_MIDI_OUTPUT_CHANNEL_MIXDOWN = 0x20
LIBJACK_FLAG_EXTERNAL_START = 0x40

LIBJACK_SESSION_MANAGER_NONE = 0
LIBJACK_SESSION_MANAGER_LADISH = 3
LIBJACK_SESSION_MANAGER_NSM = 4

# UI session manager combo indexes (mirrors JackAppDialog enum)
UI_SESSION_NONE = 0
UI_SESSION_LADISH = 1
UI_SESSION_NSM = 2

# QSettings organisation/application (mirrors QSafeSettings usage in the C++ code)
_SETTINGS_ORG = "falkTX"
_SETTINGS_APP = "CarlaAddJackApp"


# ------------------------------------------------------------------------------------------------------------
# Safe settings readers (equivalent of QSafeSettings valueString/valueIntPositive/valueBool)

def _settings_value_string(settings, key, default):
    try:
        value = settings.value(key, default, type=str)
    except Exception:
        return default
    return default if value is None else str(value)


def _settings_value_int(settings, key, default):
    try:
        value = settings.value(key, default, type=int)
    except Exception:
        return default
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        return default
    return value


def _settings_value_bool(settings, key, default):
    try:
        value = settings.value(key, default, type=bool)
    except Exception:
        return default
    if not isinstance(value, bool):
        return default
    return value


# ------------------------------------------------------------------------------------------------------------
# Jack Application Dialog

class JackAppDialog(QDialog):
    def __init__(self, parent, projectFilename):
        QDialog.__init__(self, parent)

        if isinstance(projectFilename, bytes):
            projectFilename = projectFilename.decode("utf-8", "ignore")
        self._projectFilename = projectFilename or ""

        # ----------------------------------------------------------------------------------------------------------------
        # UI setup

        self._setup_ui()

        self.group_error.setVisible(False)

        self.adjustSize()
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)

        if sys.platform == "darwin" and parent is not None:
            self.setWindowModality(Qt.WindowModal)

        # ----------------------------------------------------------------------------------------------------------------
        # Load settings

        self._load_settings()

        # ----------------------------------------------------------------------------------------------------------------
        # Set-up connections

        self.finished.connect(self._slot_saveSettings)
        self.cb_session_mgr.currentIndexChanged.connect(self._slot_sessionManagerChanged)
        self.le_command.textChanged.connect(self._slot_commandChanged)

        self.buttonBox.accepted.connect(self.accept)
        self.buttonBox.rejected.connect(self.reject)

    # ----------------------------------------------------------------------------------------------------------------
    # UI construction (mirrors jackappdialog.ui)

    def _setup_ui(self):
        self.setWindowTitle("Add JACK Application")
        self.resize(458, 546)

        self.verticalLayout = QVBoxLayout(self)

        self.l_note_features = QLabel("Note: Features not implemented yet are greyed out", self)
        self.verticalLayout.addWidget(self.l_note_features)

        # ---- Application group

        self.group_command = QGroupBox("Application", self)
        self.gridLayout = QGridLayout(self.group_command)
        self.gridLayout.addItem(QSpacerItem(20, 60, QSizePolicy.Fixed, QSizePolicy.Minimum), 0, 0, 3, 1)

        self.label_10 = QLabel("Name:", self.group_command)
        self.label_10.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.gridLayout.addWidget(self.label_10, 0, 1)

        self.le_name = QLineEdit(self.group_command)
        self.gridLayout.addWidget(self.le_name, 0, 2, 1, 2)

        self.gridLayout.addItem(QSpacerItem(20, 60, QSizePolicy.Fixed, QSizePolicy.Minimum), 0, 4, 3, 1)

        self.label_5 = QLabel("Application:", self.group_command)
        self.label_5.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.gridLayout.addWidget(self.label_5, 1, 1)

        self.rb_template = QRadioButton("From template", self.group_command)
        self.rb_template.setEnabled(False)
        self.gridLayout.addWidget(self.rb_template, 1, 2)

        self.rb_custom = QRadioButton("Custom", self.group_command)
        self.rb_custom.setChecked(True)
        self.gridLayout.addWidget(self.rb_custom, 1, 3)

        self.stackedWidget = QStackedWidget(self.group_command)

        self.page_template = QWidget(self.stackedWidget)
        self.horizontalLayout_2 = QHBoxLayout(self.page_template)
        self.horizontalLayout_2.setContentsMargins(0, 0, 0, 0)
        self.l_template = QLabel("Template:", self.page_template)
        self.l_template.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.horizontalLayout_2.addWidget(self.l_template)
        self.cb_template = QComboBox(self.page_template)
        self.cb_template.setEditable(False)
        self.horizontalLayout_2.addWidget(self.cb_template)
        self.stackedWidget.addWidget(self.page_template)

        self.page_command = QWidget(self.stackedWidget)
        self.horizontalLayout_3 = QHBoxLayout(self.page_command)
        self.horizontalLayout_3.setContentsMargins(0, 0, 0, 0)
        self.l_command = QLabel("Command:", self.page_command)
        self.l_command.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.horizontalLayout_3.addWidget(self.l_command)
        self.le_command = QLineEdit(self.page_command)
        self.horizontalLayout_3.addWidget(self.le_command)
        self.stackedWidget.addWidget(self.page_command)

        self.gridLayout.addWidget(self.stackedWidget, 2, 1, 1, 3)
        self.stackedWidget.setCurrentIndex(1)

        self.verticalLayout.addWidget(self.group_command)

        # ---- Setup group

        self.group_setup = QGroupBox("Setup", self)
        self.gridLayout_2 = QGridLayout(self.group_setup)
        self.gridLayout_2.addItem(QSpacerItem(20, 1, QSizePolicy.Fixed, QSizePolicy.Minimum), 2, 0)

        self.horizontalLayout = QHBoxLayout()
        self.horizontalLayout.addItem(QSpacerItem(40, 20, QSizePolicy.Expanding, QSizePolicy.Minimum))

        self.label_6 = QLabel("Session Manager:", self.group_setup)
        self.label_6.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.horizontalLayout.addWidget(self.label_6)

        self.cb_session_mgr = QComboBox(self.group_setup)
        self.cb_session_mgr.addItem("None")
        self.cb_session_mgr.addItem("LADISH (SIGUSR1)")
        self.cb_session_mgr.addItem("NSM")
        self.cb_session_mgr.setCurrentIndex(0)
        self.horizontalLayout.addWidget(self.cb_session_mgr)

        self.horizontalLayout.addItem(QSpacerItem(40, 20, QSizePolicy.Expanding, QSizePolicy.Minimum))
        self.gridLayout_2.addLayout(self.horizontalLayout, 0, 1, 1, 8)

        self.label_3 = QLabel("Audio inputs:", self.group_setup)
        self.label_3.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.gridLayout_2.addWidget(self.label_3, 2, 1)

        self.sb_audio_ins = QSpinBox(self.group_setup)
        self.sb_audio_ins.setMaximum(64)
        self.gridLayout_2.addWidget(self.sb_audio_ins, 2, 2)

        self.gridLayout_2.addItem(QSpacerItem(20, 1, QSizePolicy.Fixed, QSizePolicy.Minimum), 2, 3)

        self.line = QFrame(self.group_setup)
        self.line.setFrameShape(QFrame.VLine)
        self.line.setFrameShadow(QFrame.Raised)
        self.line.setLineWidth(0)
        self.line.setMidLineWidth(1)
        self.gridLayout_2.addWidget(self.line, 2, 4, 2, 1)

        self.gridLayout_2.addItem(QSpacerItem(20, 1, QSizePolicy.Fixed, QSizePolicy.Minimum), 2, 5)

        self.label_7 = QLabel("MIDI inputs:", self.group_setup)
        self.label_7.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.gridLayout_2.addWidget(self.label_7, 2, 6)

        self.sb_midi_ins = QSpinBox(self.group_setup)
        self.sb_midi_ins.setMaximum(1)
        self.gridLayout_2.addWidget(self.sb_midi_ins, 2, 7)

        self.gridLayout_2.addItem(QSpacerItem(1, 1, QSizePolicy.Minimum, QSizePolicy.Minimum), 2, 8)

        self.gridLayout_2.addItem(QSpacerItem(20, 1, QSizePolicy.Fixed, QSizePolicy.Minimum), 3, 0)

        self.label_4 = QLabel("Audio outputs:", self.group_setup)
        self.label_4.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.gridLayout_2.addWidget(self.label_4, 3, 1)

        self.sb_audio_outs = QSpinBox(self.group_setup)
        self.sb_audio_outs.setMaximum(64)
        self.gridLayout_2.addWidget(self.sb_audio_outs, 3, 2)

        self.gridLayout_2.addItem(QSpacerItem(20, 1, QSizePolicy.Fixed, QSizePolicy.Minimum), 3, 3)

        self.gridLayout_2.addItem(QSpacerItem(20, 1, QSizePolicy.Fixed, QSizePolicy.Minimum), 3, 5)

        self.label_8 = QLabel("MIDI outputs:", self.group_setup)
        self.label_8.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.gridLayout_2.addWidget(self.label_8, 3, 6)

        self.sb_midi_outs = QSpinBox(self.group_setup)
        self.sb_midi_outs.setMaximum(1)
        self.gridLayout_2.addWidget(self.sb_midi_outs, 3, 7)

        self.gridLayout_2.addItem(QSpacerItem(1, 1, QSizePolicy.Minimum, QSizePolicy.Minimum), 3, 8)

        self.cb_manage_window = QCheckBox("Take control of main application window", self.group_setup)
        self.gridLayout_2.addWidget(self.cb_manage_window, 1, 2, 1, 7)

        self.verticalLayout.addWidget(self.group_setup)

        # ---- Workarounds group

        self.group_workarounds = QGroupBox("Workarounds", self)
        self.gridLayout_3 = QGridLayout(self.group_workarounds)
        self.gridLayout_3.addItem(QSpacerItem(20, 1, QSizePolicy.Fixed, QSizePolicy.Minimum), 0, 0)

        self.cb_capture_first_window = QCheckBox("Capture only the first X11 Window", self.group_workarounds)
        self.cb_capture_first_window.setEnabled(False)
        self.gridLayout_3.addWidget(self.cb_capture_first_window, 0, 1)

        self.gridLayout_3.addItem(QSpacerItem(135, 1, QSizePolicy.Minimum, QSizePolicy.Minimum), 0, 2)

        self.cb_out_midi_mixdown = QCheckBox(
            "Simulate 16 JACK MIDI outputs, with MIDI channel as port index", self.group_workarounds
        )
        self.gridLayout_3.addWidget(self.cb_out_midi_mixdown, 1, 1)

        self.cb_buffers_addition_mode = QCheckBox(
            "Use previous client output buffer as input for the next client", self.group_workarounds
        )
        self.gridLayout_3.addWidget(self.cb_buffers_addition_mode, 2, 1)

        self.cb_external_start = QCheckBox(
            "Wait for external application start (Advanced, for Debug only)", self.group_workarounds
        )
        self.gridLayout_3.addWidget(self.cb_external_start, 4, 1)

        self.verticalLayout.addWidget(self.group_workarounds)

        # ---- Error group

        self.group_error = QFrame(self)
        self.group_error.setFrameShape(QFrame.StyledPanel)
        self.group_error.setFrameShadow(QFrame.Raised)
        self.horizontalLayout_4 = QHBoxLayout(self.group_error)

        self.ico_error = QLabel(self.group_error)
        self.ico_error.setMinimumSize(16, 16)
        self.ico_error.setMaximumSize(16, 16)
        self.ico_error.setScaledContents(True)
        self._error_pixmap = QPixmap(":/16x16/dialog-cancel.svgz")
        if not self._error_pixmap.isNull():
            self.ico_error.setPixmap(self._error_pixmap)
        self.horizontalLayout_4.addWidget(self.ico_error)

        self.l_error = QLabel("Error here", self.group_error)
        self.horizontalLayout_4.addWidget(self.l_error)

        self.verticalLayout.addWidget(self.group_error)

        # ---- Bottom spacer and button box

        self.verticalSpacer = QSpacerItem(20, 40, QSizePolicy.Minimum, QSizePolicy.Expanding)
        self.verticalLayout.addItem(self.verticalSpacer)

        self.buttonBox = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel, self)
        self.buttonBox.setOrientation(Qt.Horizontal)
        self.verticalLayout.addWidget(self.buttonBox)

    # ----------------------------------------------------------------------------------------------------------------
    # public methods

    def getCommandAndFlags(self):
        command = self.le_command.text()
        name = self.le_name.text()

        if not name:
            name = QFileInfo(command.split(" ")[0]).baseName()
            if name:
                name = name[0].upper() + name[1:]

        index = self.cb_session_mgr.currentIndex()
        if index == UI_SESSION_LADISH:
            smgr = LIBJACK_SESSION_MANAGER_LADISH
        elif index == UI_SESSION_NSM:
            smgr = LIBJACK_SESSION_MANAGER_NSM
        else:
            smgr = LIBJACK_SESSION_MANAGER_NONE

        flags = 0x0
        if self.cb_manage_window.isChecked():
            flags |= LIBJACK_FLAG_CONTROL_WINDOW
        if self.cb_capture_first_window.isChecked():
            flags |= LIBJACK_FLAG_CAPTURE_FIRST_WINDOW
        if self.cb_buffers_addition_mode.isChecked():
            flags |= LIBJACK_FLAG_AUDIO_BUFFERS_ADDITION
        if self.cb_out_midi_mixdown.isChecked():
            flags |= LIBJACK_FLAG_MIDI_OUTPUT_CHANNEL_MIXDOWN
        if self.cb_external_start.isChecked():
            flags |= LIBJACK_FLAG_EXTERNAL_START

        labelSetup = "".join(
            chr(ord("0") + value)
            for value in (
                self.sb_audio_ins.value(),
                self.sb_audio_outs.value(),
                self.sb_midi_ins.value(),
                self.sb_midi_outs.value(),
                smgr,
                flags,
            )
        )

        return {
            "command": command,
            "name": name,
            "labelSetup": labelSetup,
        }

    # ----------------------------------------------------------------------------------------------------------------
    # private methods

    def _checkIfButtonBoxShouldBeEnabled(self, index, command):
        enabled = bool(command)
        showErr = ""

        # NSM applications must not be abstract or absolute paths, and must not contain arguments
        if enabled and index == UI_SESSION_NSM:
            if command[0] in "./":
                showErr = self.tr("NSM applications cannot use abstract or absolute paths")
            elif " " in command or ";" in command or "&" in command:
                showErr = self.tr("NSM applications cannot use CLI arguments")
            elif not self._projectFilename:
                showErr = self.tr("You need to save the current Carla project before NSM can be used")

        if showErr:
            enabled = False
            self.l_error.setText(showErr)
            self.group_error.setVisible(True)
        else:
            self.group_error.setVisible(False)

        button = self.buttonBox.button(QDialogButtonBox.Ok)
        if button is not None:
            button.setEnabled(enabled)

    def _load_settings(self):
        settings = QSettings(_SETTINGS_ORG, _SETTINGS_APP)

        smName = _settings_value_string(settings, "SessionManager", "")

        if smName == "LADISH (SIGUSR1)":
            self.cb_session_mgr.setCurrentIndex(UI_SESSION_LADISH)
        elif smName == "NSM":
            self.cb_session_mgr.setCurrentIndex(UI_SESSION_NSM)
        else:
            self.cb_session_mgr.setCurrentIndex(UI_SESSION_NONE)

        self.le_command.setText(_settings_value_string(settings, "Command", ""))
        self.le_name.setText(_settings_value_string(settings, "Name", ""))
        self.sb_audio_ins.setValue(_settings_value_int(settings, "NumAudioIns", 2))
        self.sb_audio_outs.setValue(_settings_value_int(settings, "NumAudioOuts", 2))
        self.sb_midi_ins.setValue(_settings_value_int(settings, "NumMidiIns", 0))
        self.sb_midi_outs.setValue(_settings_value_int(settings, "NumMidiOuts", 0))
        self.cb_manage_window.setChecked(_settings_value_bool(settings, "ManageWindow", True))
        self.cb_capture_first_window.setChecked(_settings_value_bool(settings, "CaptureFirstWindow", False))
        self.cb_out_midi_mixdown.setChecked(_settings_value_bool(settings, "MidiOutMixdown", False))

        self._checkIfButtonBoxShouldBeEnabled(self.cb_session_mgr.currentIndex(),
                                              self.le_command.text())

    # ----------------------------------------------------------------------------------------------------------------
    # private slots

    def _slot_commandChanged(self, command):
        self._checkIfButtonBoxShouldBeEnabled(self.cb_session_mgr.currentIndex(), command)

    def _slot_sessionManagerChanged(self, index):
        self._checkIfButtonBoxShouldBeEnabled(index, self.le_command.text())

    def _slot_saveSettings(self):
        settings = QSettings(_SETTINGS_ORG, _SETTINGS_APP)
        settings.setValue("Command", self.le_command.text())
        settings.setValue("Name", self.le_name.text())
        settings.setValue("SessionManager", self.cb_session_mgr.currentText())
        settings.setValue("NumAudioIns", self.sb_audio_ins.value())
        settings.setValue("NumAudioOuts", self.sb_audio_outs.value())
        settings.setValue("NumMidiIns", self.sb_midi_ins.value())
        settings.setValue("NumMidiOuts", self.sb_midi_outs.value())
        settings.setValue("ManageWindow", self.cb_manage_window.isChecked())
        settings.setValue("CaptureFirstWindow", self.cb_capture_first_window.isChecked())
        settings.setValue("MidiOutMixdown", self.cb_out_midi_mixdown.isChecked())


# ------------------------------------------------------------------------------------------------------------

def createAndExecJackAppDialog(parent, projectFilename):
    gui = JackAppDialog(parent, projectFilename)

    if gui.exec():
        return gui.getCommandAndFlags()

    return None


# ------------------------------------------------------------------------------------------------------------
