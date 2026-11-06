#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2011-2025 Filipe Coelho <falktx@falktx.com>
# SPDX-License-Identifier: GPL-2.0-or-later

# ------------------------------------------------------------------------------------------------------------
# Imports (Global)

import os
from abc import abstractmethod

# ------------------------------------------------------------------------------------------------------------
# Imports (PyQt)

from qt_compat import qt_config

if qt_config == 5:
    from PyQt5.QtCore import pyqtSignal, pyqtSlot, Qt, QByteArray
    from PyQt5.QtGui import QCursor, QIcon, QPalette, QPixmap
    from PyQt5.QtWidgets import (
        QApplication,
        QDialog,
        QFileDialog,
        QHBoxLayout,
        QInputDialog,
        QLabel,
        QMenu,
        QMessageBox,
        QProgressBar,
        QPushButton,
        QScrollArea,
        QTextEdit,
        QVBoxLayout,
        QWidget,
    )
elif qt_config == 6:
    from PyQt6.QtCore import pyqtSignal, pyqtSlot, Qt, QByteArray
    from PyQt6.QtGui import QCursor, QIcon, QPalette, QPixmap
    from PyQt6.QtWidgets import (
        QApplication,
        QDialog,
        QFileDialog,
        QHBoxLayout,
        QInputDialog,
        QLabel,
        QMenu,
        QMessageBox,
        QProgressBar,
        QPushButton,
        QScrollArea,
        QTextEdit,
        QVBoxLayout,
        QWidget,
    )

# ------------------------------------------------------------------------------------------------------------
# Imports (Custom)

import ui_carla_edit
import ui_carla_parameter

from carla_backend import (
    BINARY_NATIVE,
    CARLA_VERSION_STRING,
    CARLA_OS_MAC,
    CARLA_OS_WIN,
    PLUGIN_INTERNAL,
    PLUGIN_DSSI,
    PLUGIN_LV2,
    PLUGIN_VST2,
    PLUGIN_SF2,
    PLUGIN_SFZ,
    PLUGIN_CAN_DRYWET,
    PLUGIN_CAN_VOLUME,
    PLUGIN_CAN_BALANCE,
    PLUGIN_CAN_PANNING,
    PLUGIN_CATEGORY_SYNTH,
    PLUGIN_OPTION_FIXED_BUFFERS,
    PLUGIN_OPTION_FORCE_STEREO,
    PLUGIN_OPTION_MAP_PROGRAM_CHANGES,
    PLUGIN_OPTION_USE_CHUNKS,
    PLUGIN_OPTION_SEND_CONTROL_CHANGES,
    PLUGIN_OPTION_SEND_CHANNEL_PRESSURE,
    PLUGIN_OPTION_SEND_NOTE_AFTERTOUCH,
    PLUGIN_OPTION_SEND_PITCHBEND,
    PLUGIN_OPTION_SEND_ALL_SOUND_OFF,
    PLUGIN_OPTION_SEND_PROGRAM_CHANGES,
    PLUGIN_OPTION_SKIP_SENDING_NOTES,
    PARAMETER_DRYWET,
    PARAMETER_VOLUME,
    PARAMETER_BALANCE_LEFT,
    PARAMETER_BALANCE_RIGHT,
    PARAMETER_PANNING,
    PARAMETER_CTRL_CHANNEL,
    PARAMETER_IS_ENABLED,
    PARAMETER_IS_AUTOMATABLE,
    PARAMETER_IS_READ_ONLY,
    PARAMETER_USES_SCALEPOINTS,
    PARAMETER_USES_CUSTOM_TEXT,
    PARAMETER_CAN_BE_CV_CONTROLLED,
    PARAMETER_INPUT, PARAMETER_OUTPUT,
    CONTROL_INDEX_NONE,
    CONTROL_INDEX_MIDI_PITCHBEND,
    CONTROL_INDEX_MIDI_LEARN,
    CONTROL_INDEX_CV
)

from carla_shared import (
    MIDI_CC_LIST, MAX_MIDI_CC_LIST_ITEM,
    countDecimalPoints,
    fontMetricsHorizontalAdvance,
    setUpSignals,
    gCarla
)

from carla_utils import getPluginTypeAsString

from widgets.collapsablewidget import CollapsibleBox
from widgets.pixmapkeyboard import PixmapKeyboardHArea

from project_storage import storage_manager

# ------------------------------------------------------------------------------------------------------------
# Carla GUI defines

ICON_STATE_ON   = 3 # turns on, sets as wait
ICON_STATE_WAIT = 2 # nothing, sets as off
ICON_STATE_OFF  = 1 # turns off, sets as null
ICON_STATE_NULL = 0 # nothing

# ------------------------------------------------------------------------------------------------------------
# Plugin Parameter

from plugin_edit import *
from project_dialogs import *
