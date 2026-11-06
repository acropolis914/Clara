#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2011-2025 Filipe Coelho <falktx@falktx.com>
# SPDX-License-Identifier: GPL-2.0-or-later

# ------------------------------------------------------------------------------------------------------------
# Pure-Python/PyQt6 port of the C++ PluginListDialog ("Carla - Add New" plugin browser).
#
# This replaces the Qt-linked native libcarla_frontend for the Add-Plugin dialog. Plugin discovery still comes
# from the NON-Qt native backend `libcarla_utils`, through pluginlist/discovery_py.py.
# ------------------------------------------------------------------------------------------------------------

# ------------------------------------------------------------------------------------------------------------
# Imports (Global)

import os
import struct
import sys

# Make sure the frontend folder and this folder are importable regardless of how we were loaded.
_HERE = os.path.dirname(os.path.abspath(__file__))
_FRONTEND_DIR = os.path.dirname(_HERE)
for _d in (_FRONTEND_DIR, _HERE):
    if _d not in sys.path:
        sys.path.insert(0, _d)

# ------------------------------------------------------------------------------------------------------------
# Imports (PyQt)

from qt_compat import (
    QAbstractItemView,
    QAction,
    QApplication,
    QCheckBox,
    QColor,
    QDialog,
    QFileInfo,
    QFrame,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QIcon,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMenu,
    QPalette,
    QPoint,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QSettings,
    QSize,
    QSizePolicy,
    QStackedWidget,
    QTabWidget,
    QTableWidget,
    QTableWidgetItem,
    QTimer,
    QToolButton,
    QVBoxLayout,
    QByteArray,
    QListView,
    QRadioButton,
    QToolBox,
    QWidget,
    Qt,
    pyqtSignal,
)

# ------------------------------------------------------------------------------------------------------------
# Imports (Custom)

from carla_backend import (
    BINARY_NATIVE,
    BINARY_NONE,
    BINARY_OTHER,
    BINARY_POSIX32,
    BINARY_POSIX64,
    BINARY_WIN32,
    BINARY_WIN64,
    CARLA_OS_64BIT,
    CARLA_OS_MAC,
    CARLA_OS_WIN,
    ENGINE_OPTION_WINE_AUTO_PREFIX,
    ENGINE_OPTION_WINE_EXECUTABLE,
    ENGINE_OPTION_WINE_FALLBACK_PREFIX,
    PLUGIN_AU,
    PLUGIN_CLAP,
    PLUGIN_DSSI,
    PLUGIN_INTERNAL,
    PLUGIN_JSFX,
    PLUGIN_LADSPA,
    PLUGIN_LV2,
    PLUGIN_NONE,
    PLUGIN_SF2,
    PLUGIN_SFZ,
    PLUGIN_VST2,
    PLUGIN_VST3,
    PLUGIN_IS_BRIDGE,
    PLUGIN_IS_RTSAFE,
    PLUGIN_IS_SYNTH,
    PLUGIN_HAS_CUSTOM_UI,
    PLUGIN_HAS_INLINE_DISPLAY,
    PLUGIN_OPTION_AVOID_BRIDGE,
    PLUGIN_OPTIONS_NULL,
    PLUGIN_OPTION_USE_BRIDGE,
)
from carla_shared import getIcon, log_carla
from carla_utils import getPluginCategoryAsString, getPluginTypeAsString

from utils import QSafeSettings

try:
    from carla_skin import FlowLayout
except ImportError:
    from ..carla_skin import FlowLayout

try:
    from .discovery_py import PluginDiscovery, get_library_folder, set_option
except ImportError:  # loaded as a top-level module
    from discovery_py import PluginDiscovery, get_library_folder, set_option  # type: ignore

# ------------------------------------------------------------------------------------------------------------
# Table / role constants (must match the C++ enums)

TW_FAVORITE = 0
TW_NAME     = 1
TW_LABEL    = 2
TW_MAKER    = 3
TW_BINARY   = 4

UR_PLUGIN_INFO = 1
UR_SEARCH_TEXT = 2

_TABLE_COLUMNS = 5

# ------------------------------------------------------------------------------------------------------------
# Enum compatibility helpers (PyQt5 uses short forms, PyQt6 requires scoped enums)

def _qt_checkstate(checked):
    try:
        return Qt.CheckState.Checked if checked else Qt.CheckState.Unchecked
    except AttributeError:  # PyQt5
        return Qt.Checked if checked else Qt.Unchecked  # noqa: F821


def _qt_accepted():
    try:
        return QDialog.DialogCode.Accepted
    except AttributeError:  # PyQt5
        return QDialog.Accepted  # noqa: F821


_NO_EDIT_TRIGGERS = getattr(QAbstractItemView, "NoEditTriggers", None)
if _NO_EDIT_TRIGGERS is None:
    _NO_EDIT_TRIGGERS = QAbstractItemView.EditTrigger.NoEditTriggers

_SELECT_ROWS = getattr(QAbstractItemView, "SelectRows", None)
if _SELECT_ROWS is None:
    _SELECT_ROWS = QAbstractItemView.SelectionBehavior.SelectRows

_SINGLE_SELECTION = getattr(QAbstractItemView, "SingleSelection", None)
if _SINGLE_SELECTION is None:
    _SINGLE_SELECTION = QAbstractItemView.SelectionMode.SingleSelection

_EXTENDED_SELECTION = getattr(QAbstractItemView, "ExtendedSelection", None)
if _EXTENDED_SELECTION is None:
    _EXTENDED_SELECTION = QAbstractItemView.SelectionMode.ExtendedSelection

_SCROLL_PER_PIXEL = getattr(QAbstractItemView, "ScrollPerPixel", None)
if _SCROLL_PER_PIXEL is None:
    _SCROLL_PER_PIXEL = QAbstractItemView.ScrollMode.ScrollPerPixel

_ICON_MODE = getattr(QListView, "IconMode", None)
if _ICON_MODE is None:
    _ICON_MODE = QListView.ViewMode.IconMode

_ADJUST = getattr(QListView, "Adjust", None)
if _ADJUST is None:
    _ADJUST = QListView.ResizeMode.Adjust

_STATIC = getattr(QListView, "Static", None)
if _STATIC is None:
    _STATIC = QListView.Movement.Static

_ALIGN_RIGHT = getattr(Qt, "AlignRight", None)
if _ALIGN_RIGHT is None:
    _ALIGN_RIGHT = Qt.AlignmentFlag.AlignRight


def _checkstate_checked(item):
    try:
        return item.checkState() == Qt.CheckState.Checked
    except AttributeError:  # PyQt5
        return item.checkState() == Qt.Checked  # noqa: F821

# ------------------------------------------------------------------------------------------------------------
# PluginInfo / PluginFavorite binary serialization (identical to the C++ asByteArray/asPluginInfo)

# PluginInfoHeader: uint16 build, uint16 type, uint32 hints, uint64 uniqueId,
#                   uint16 audioIns, audioOuts, cvIns, cvOuts, midiIns, midiOuts, parameterIns, parameterOuts
_INFO_HEADER = struct.Struct("<HHIQHHHHHHHH")

# PluginFavoriteHeader: uint16 type, (6 bytes padding), uint64 uniqueId
_FAV_HEADER = struct.Struct("<H6xQ")

_INFO_STRINGS = ("category", "filename", "name", "label", "maker")


def _infoToBytes(info):
    out = bytearray()
    out += _INFO_HEADER.pack(
        int(info["build"]) & 0xFFFF,
        int(info["type"]) & 0xFFFF,
        int(info["hints"]) & 0xFFFFFFFF,
        int(info["uniqueId"]) & 0xFFFFFFFFFFFFFFFF,
        int(info["audioIns"]) & 0xFFFF,
        int(info["audioOuts"]) & 0xFFFF,
        int(info["cvIns"]) & 0xFFFF,
        int(info["cvOuts"]) & 0xFFFF,
        int(info["midiIns"]) & 0xFFFF,
        int(info["midiOuts"]) & 0xFFFF,
        int(info["parameterIns"]) & 0xFFFF,
        int(info["parameterOuts"]) & 0xFFFF,
    )
    for key in _INFO_STRINGS:
        out += (info.get(key) or "").encode("utf-8", errors="replace") + b"\0"
    return bytes(out)


def _bytesToInfo(data, offset=0):
    if isinstance(data, QByteArray):
        data = bytes(data)
    if len(data) < offset + _INFO_HEADER.size:
        return None, offset

    (build, ptype, hints, uniqueId,
     aIn, aOut, cvIn, cvOut, mIn, mOut, pIn, pOut) = _INFO_HEADER.unpack_from(data, offset)
    pos = offset + _INFO_HEADER.size

    def readStr():
        nonlocal pos
        end = data.find(b"\0", pos)
        if end < 0:
            end = len(data)
        value = data[pos:end].decode("utf-8", errors="replace")
        pos = end + 1
        return value

    info = {
        "build": build,
        "type": ptype,
        "hints": hints,
        "uniqueId": uniqueId,
        "audioIns": aIn,
        "audioOuts": aOut,
        "cvIns": cvIn,
        "cvOuts": cvOut,
        "midiIns": mIn,
        "midiOuts": mOut,
        "parameterIns": pIn,
        "parameterOuts": pOut,
        "category": readStr(),
        "filename": readStr(),
        "name": readStr(),
        "label": readStr(),
        "maker": readStr(),
    }
    return info, pos


def _infoListToBytes(infos):
    out = bytearray()
    for info in infos:
        out += _infoToBytes(info)
    return bytes(out)


def _bytesToInfoList(data):
    infos = []
    offset = 0
    while offset < len(data):
        info, offset = _bytesToInfo(data, offset)
        if info is None or info["build"] == BINARY_NONE:
            break
        infos.append(info)
    return infos

# ------------------------------------------------------------------------------------------------------------
# Settings helpers

_SETTINGS_ORG = "falkTX"
_SETTINGS_APP = "CarlaDatabase3"


def _newSettings():
    settings = QSettings(_SETTINGS_ORG, _SETTINGS_APP)
    return settings


def _getBool(settings, key, default):
    try:
        value = settings.value(key, default)
    except Exception:
        return default
    if value is None:
        return default
    if isinstance(value, str):
        return value.lower() in ("true", "1", "yes")
    return bool(value)


def _getStr(settings, key, default):
    try:
        value = settings.value(key, default)
    except Exception:
        return default
    if value is None:
        return default
    return str(value)


def _getInt(settings, key, default):
    try:
        value = settings.value(key, default)
    except Exception:
        return default
    if value is None:
        return default
    try:
        return int(value)
    except Exception:
        return default


def _getBytes(settings, key):
    try:
        value = settings.value(key, QByteArray())
    except Exception:
        return b""
    if value is None:
        return b""
    if isinstance(value, QByteArray):
        return bytes(value)
    if isinstance(value, (bytes, bytearray)):
        return bytes(value)
    return b""

# ------------------------------------------------------------------------------------------------------------
# Default plugin paths (env vars + common locations). Mirrors the C++ PluginPaths helper.

def _defaultPluginPaths():
    home = os.path.expanduser("~")
    paths = {
        PLUGIN_LADSPA: "",
        PLUGIN_DSSI: "",
        PLUGIN_LV2: "",
        PLUGIN_VST2: "",
        PLUGIN_VST3: "",
        PLUGIN_CLAP: "",
        PLUGIN_JSFX: "",
        PLUGIN_SF2: "",
        PLUGIN_SFZ: "",
    }
    if CARLA_OS_MAC:
        paths[PLUGIN_AU] = os.path.join(home, "Library/Audio/Plug-Ins/Components") + \
                          ":/Library/Audio/Plug-Ins/Components:/System/Library/Components"

    if CARLA_OS_WIN:
        appdata = os.environ.get("APPDATA", "")
        localappdata = os.environ.get("LOCALAPPDATA", appdata)
        programfiles = os.environ.get("PROGRAMFILES", "")
        common = os.environ.get("COMMONPROGRAMFILES", "")

        paths[PLUGIN_LADSPA] = os.environ.get("LADSPA_PATH", appdata + "\\LADSPA;" + programfiles + "\\LADSPA")
        paths[PLUGIN_DSSI] = os.environ.get("DSSI_PATH", appdata + "\\DSSI;" + programfiles + "\\DSSI")
        paths[PLUGIN_LV2] = os.environ.get("LV2_PATH", appdata + "\\LV2;" + common + "\\LV2")
        paths[PLUGIN_VST2] = os.environ.get("VST_PATH",
            programfiles + "\\VSTPlugins;" + programfiles + "\\Steinberg\\VSTPlugins;"
            + common + "\\VST2;" + common + "\\Steinberg\\VST2")
        paths[PLUGIN_VST3] = os.environ.get("VST3_PATH", localappdata + "\\Programs\\Common\\VST3;" + common + "\\VST3")
        paths[PLUGIN_CLAP] = os.environ.get("CLAP_PATH", localappdata + "\\Programs\\Common\\CLAP;" + common + "\\CLAP")
        paths[PLUGIN_JSFX] = os.environ.get("JSFX_PATH", appdata + "\\REAPER\\Effects")
        paths[PLUGIN_SF2] = os.environ.get("SF2_PATH", appdata + "\\SF2")
        paths[PLUGIN_SFZ] = os.environ.get("SFZ_PATH", appdata + "\\SFZ")
        return paths

    # Unix-ish
    config_home = os.environ.get("XDG_CONFIG_HOME", os.path.join(home, ".config"))

    paths[PLUGIN_LADSPA] = os.environ.get("LADSPA_PATH",
        os.path.join(home, ".ladspa") + ":/usr/local/lib/ladspa:/usr/lib/ladspa")
    paths[PLUGIN_DSSI] = os.environ.get("DSSI_PATH",
        os.path.join(home, ".dssi") + ":/usr/local/lib/dssi:/usr/lib/dssi")
    paths[PLUGIN_LV2] = os.environ.get("LV2_PATH",
        os.path.join(home, ".lv2") + ":/usr/local/lib/lv2:/usr/lib/lv2")
    paths[PLUGIN_VST2] = os.environ.get("VST_PATH",
        os.path.join(home, ".vst") + ":" + os.path.join(home, ".lxvst")
        + ":/usr/local/lib/vst:/usr/local/lib/lxvst:/usr/lib/vst:/usr/lib/lxvst")
    paths[PLUGIN_VST3] = os.environ.get("VST3_PATH",
        os.path.join(home, ".vst3") + ":/usr/local/lib/vst3:/usr/lib/vst3")
    paths[PLUGIN_CLAP] = os.environ.get("CLAP_PATH",
        os.path.join(home, ".clap") + ":/usr/local/lib/clap:/usr/lib/clap")
    paths[PLUGIN_JSFX] = os.environ.get("JSFX_PATH", config_home + "/REAPER/Effects")
    paths[PLUGIN_SF2] = os.environ.get("SF2_PATH",
        os.path.join(home, ".sounds/sf2") + ":" + os.path.join(home, ".sounds/sf3")
        + ":/usr/share/sounds/sf2:/usr/share/sounds/sf3:/usr/share/soundfonts")
    paths[PLUGIN_SFZ] = os.environ.get("SFZ_PATH",
        os.path.join(home, ".sounds/sfz") + ":/usr/share/sounds/sfz")

    # Add wine prefixes (bridged Windows plugins)
    wine_prefix = os.environ.get("WINEPREFIX") or os.path.join(home, ".wine")
    if os.path.isdir(wine_prefix):
        drive_c = os.path.join(wine_prefix, "drive_c")
        for base in ("Program Files", "Program Files (x86)"):
            d = os.path.join(drive_c, base)
            if os.path.isdir(d):
                paths[PLUGIN_VST2] += ":" + os.path.join(d, "VstPlugins")
                paths[PLUGIN_VST2] += ":" + os.path.join(d, "Steinberg/VstPlugins")
                paths[PLUGIN_VST2] += ":" + os.path.join(d, "Common Files/VST2")
                paths[PLUGIN_VST3] += ":" + os.path.join(d, "Common Files/VST3")
                paths[PLUGIN_CLAP] += ":" + os.path.join(d, "Common Files/CLAP")

    return paths

# ------------------------------------------------------------------------------------------------------------
# Plugin Refresh dialog (ported from pluginrefreshdialog.ui)

class _PluginRefreshDialog(QDialog):
    def __init__(self, parent, firstInit=False):
        super().__init__(parent)
        self._firstInit = firstInit

        self.setWindowTitle(self.tr("Carla - Refresh Plugins"))
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)
        if CARLA_OS_MAC:
            self.setWindowModality(Qt.WindowModal)

        main = QVBoxLayout(self)

        top = QHBoxLayout()
        self.group = QGroupBox(self.tr("Refresh Options"), self)
        groupLayout = QVBoxLayout(self.group)
        self.ch_all = QRadioButton(self.tr("Scan all plugins"))
        self.ch_updated = QRadioButton(self.tr("Only scan updated/new"))
        self.ch_invalid = QCheckBox(self.tr("Check for invalid plugins"))
        groupLayout.addWidget(self.ch_all)
        groupLayout.addWidget(self.ch_updated)
        groupLayout.addWidget(self.ch_invalid)
        top.addWidget(self.group)
        top.addStretch(1)
        main.addLayout(top)
        main.addStretch(1)

        self.group_formats = QGroupBox(self.tr("Restrict Formats"), self)
        self.group_formats.setCheckable(True)
        formatsLayout = QGridLayout(self.group_formats)
        self.ch_ladspa = QCheckBox("LADSPA")
        self.ch_dssi = QCheckBox("DSSI")
        self.ch_lv2 = QCheckBox("LV2")
        self.ch_vst2 = QCheckBox("VST2")
        self.ch_vst3 = QCheckBox("VST3")
        self.ch_clap = QCheckBox("CLAP")
        self.ch_au = QCheckBox("AU")
        self.ch_jsfx = QCheckBox("JSFX")
        self.ch_sf2 = QCheckBox("SF2")
        self.ch_sfz = QCheckBox("SFZ")
        for i, w in enumerate((self.ch_ladspa, self.ch_dssi, self.ch_lv2, self.ch_vst2, self.ch_vst3,
                               self.ch_clap, self.ch_au, self.ch_jsfx, self.ch_sf2, self.ch_sfz)):
            formatsLayout.addWidget(w, i // 5, i % 5)
        main.addWidget(self.group_formats)

        self.progressBar = QProgressBar(self)
        main.addWidget(self.progressBar)

        buttons = QHBoxLayout()
        buttons.addStretch(1)
        self.b_start = QPushButton(self.tr("Start"))
        self.b_skip = QPushButton(self.tr("Skip Current"))
        buttons.addWidget(self.b_start)
        buttons.addWidget(self.b_skip)
        main.addLayout(buttons)

        self.b_skip.setEnabled(False)
        self.ch_invalid.setEnabled(False)

        if not firstInit:
            self._loadSettings()

        self.finished.connect(self._saveSettings)

    def _loadSettings(self):
        settings = _newSettings()
        if _getBool(settings, "PluginRefreshDialog/RefreshAll", False):
            self.ch_all.setChecked(True)
        else:
            self.ch_updated.setChecked(True)
        self.ch_invalid.setChecked(_getBool(settings, "PluginRefreshDialog/CheckInvalid", False))
        self.group_formats.setChecked(_getBool(settings, "PluginRefreshDialog/RestrictFormats", False))
        self.ch_ladspa.setChecked(_getBool(settings, "PluginRefreshDialog/SearchLADSPA", True))
        self.ch_dssi.setChecked(_getBool(settings, "PluginRefreshDialog/SearchDSSI", True))
        self.ch_lv2.setChecked(_getBool(settings, "PluginRefreshDialog/SearchLV2", True))
        self.ch_vst2.setChecked(_getBool(settings, "PluginRefreshDialog/SearchVST2", True))
        self.ch_vst3.setChecked(_getBool(settings, "PluginRefreshDialog/SearchVST3", True))
        self.ch_clap.setChecked(_getBool(settings, "PluginRefreshDialog/SearchCLAP", True))
        self.ch_au.setChecked(_getBool(settings, "PluginRefreshDialog/SearchAU", True))
        self.ch_jsfx.setChecked(_getBool(settings, "PluginRefreshDialog/SearchJSFX", True))
        self.ch_sf2.setChecked(_getBool(settings, "PluginRefreshDialog/SearchSF2", True))
        self.ch_sfz.setChecked(_getBool(settings, "PluginRefreshDialog/SearchSFZ", True))

    def _saveSettings(self, *_args):
        if self._firstInit:
            return
        settings = _newSettings()
        settings.setValue("PluginRefreshDialog/RefreshAll", self.ch_all.isChecked())
        settings.setValue("PluginRefreshDialog/CheckInvalid", self.ch_invalid.isChecked())
        settings.setValue("PluginRefreshDialog/RestrictFormats", self.group_formats.isChecked())
        settings.setValue("PluginRefreshDialog/SearchLADSPA", self.ch_ladspa.isChecked())
        settings.setValue("PluginRefreshDialog/SearchDSSI", self.ch_dssi.isChecked())
        settings.setValue("PluginRefreshDialog/SearchLV2", self.ch_lv2.isChecked())
        settings.setValue("PluginRefreshDialog/SearchVST2", self.ch_vst2.isChecked())
        settings.setValue("PluginRefreshDialog/SearchVST3", self.ch_vst3.isChecked())
        settings.setValue("PluginRefreshDialog/SearchCLAP", self.ch_clap.isChecked())
        settings.setValue("PluginRefreshDialog/SearchAU", self.ch_au.isChecked())
        settings.setValue("PluginRefreshDialog/SearchJSFX", self.ch_jsfx.isChecked())
        settings.setValue("PluginRefreshDialog/SearchSF2", self.ch_sf2.isChecked())
        settings.setValue("PluginRefreshDialog/SearchSFZ", self.ch_sfz.isChecked())

# ------------------------------------------------------------------------------------------------------------
# Pill Filter Group (Modern left-sidebar multiselect toggle pills)

class PillFilterGroup(QWidget):
    """Group of checkable QPushButton pills with [All] mutual exclusion and multiselect."""
    changed = pyqtSignal()

    def __init__(self, title, pills, parent=None, all_label="All"):
        super().__init__(parent)
        self._block_updates = False

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 3, 0, 3)
        layout.setSpacing(3)

        # Header with title
        headerLayout = QHBoxLayout()
        headerLayout.setContentsMargins(0, 0, 0, 0)
        self.label = QLabel(title.upper(), self)
        font = self.label.font()
        font.setPointSize(max(8, font.pointSize() - 1))
        font.setBold(True)
        self.label.setFont(font)
        headerLayout.addWidget(self.label)
        headerLayout.addStretch(1)
        layout.addLayout(headerLayout)

        # Pills container with FlowLayout
        pillContainer = QWidget(self)
        self.flow = FlowLayout(pillContainer, hSpacing=4, vSpacing=4)
        self.flow.setContentsMargins(0, 0, 0, 0)

        # "All" master pill
        self.btn_all = QPushButton(all_label, pillContainer)
        self.btn_all.setCheckable(True)
        self.btn_all.setChecked(True)
        self.btn_all.setProperty("pill", True)
        self.btn_all.clicked.connect(self._onAllClicked)
        self.flow.addWidget(self.btn_all)

        # Specific pills
        self.buttons = {}
        for key, btn in pills:
            btn.setParent(pillContainer)
            btn.setCheckable(True)
            btn.setChecked(False)
            btn.setProperty("pill", True)
            btn.clicked.connect(lambda _checked=False, k=key: self._onPillClicked(k))
            self.flow.addWidget(btn)
            self.buttons[key] = btn

        layout.addWidget(pillContainer)

    def _onAllClicked(self):
        if self._block_updates:
            return
        self._block_updates = True
        self.btn_all.setChecked(True)
        for btn in self.buttons.values():
            btn.setChecked(False)
        self._block_updates = False
        self.changed.emit()

    def _onPillClicked(self, key):
        if self._block_updates:
            return
        self._block_updates = True
        active = [b for b in self.buttons.values() if b.isChecked()]
        if not active:
            self.btn_all.setChecked(True)
        else:
            self.btn_all.setChecked(False)
        self._block_updates = False
        self.changed.emit()

    def isAllChecked(self):
        return self.btn_all.isChecked()

    def setAll(self, all_active):
        self._block_updates = True
        self.btn_all.setChecked(all_active)
        if all_active:
            for b in self.buttons.values():
                b.setChecked(False)
        self._block_updates = False

    def syncFromPills(self):
        """Called after programmatic setChecked on specific pills."""
        self._block_updates = True
        active = [b for b in self.buttons.values() if b.isChecked()]
        if not active:
            self.btn_all.setChecked(True)
        else:
            self.btn_all.setChecked(False)
        self._block_updates = False

# ------------------------------------------------------------------------------------------------------------
# Helper for category indicator colors

def _getCategoryColor(category, isSynth=False):
    c = (category or "").lower()
    if isSynth or "synth" in c:
        return "#a6e3a1"  # Green
    if "reverb" in c or "delay" in c:
        return "#cba6f7"  # Mauve
    if "distortion" in c or "drive" in c:
        return "#f38ba8"  # Red
    if "dynamic" in c or "compress" in c or "limiter" in c:
        return "#89b4fa"  # Blue
    if "eq" in c or "filter" in c:
        return "#fab387"  # Peach
    if "modulat" in c or "chorus" in c or "flanger" in c or "phaser" in c:
        return "#89dceb"  # Cyan
    return "#6c7086"      # Subdued Slate

# ------------------------------------------------------------------------------------------------------------
def _formatIoText(ains, aouts):
    if ains == 2 and aouts == 2:
        return "Stereo"
    if ains == 1 and aouts == 1:
        return "Mono"
    if ains == 0 and aouts == 2:
        return "Stereo Out"
    if ains == 1 and aouts == 2:
        return "1 In / 2 Out"
    if ains == 0 and aouts == 0:
        return "MIDI"
    return f"{ains} In / {aouts} Out"

# ------------------------------------------------------------------------------------------------------------
def _getFormatBadgeStyle(ptype):
    if ptype == PLUGIN_CLAP:
        return "background-color: rgba(137, 180, 250, 0.16); border: 1px solid rgba(137, 180, 250, 0.4); color: #89b4fa;"
    if ptype == PLUGIN_VST3:
        return "background-color: rgba(250, 179, 135, 0.16); border: 1px solid rgba(250, 179, 135, 0.4); color: #fab387;"
    if ptype == PLUGIN_LV2:
        return "background-color: rgba(166, 227, 161, 0.16); border: 1px solid rgba(166, 227, 161, 0.4); color: #a6e3a1;"
    if ptype == PLUGIN_VST2:
        return "background-color: rgba(243, 139, 168, 0.16); border: 1px solid rgba(243, 139, 168, 0.4); color: #f38ba8;"
    if ptype == PLUGIN_JSFX:
        return "background-color: rgba(203, 166, 247, 0.16); border: 1px solid rgba(203, 166, 247, 0.4); color: #cba6f7;"
    return "background-color: rgba(108, 112, 134, 0.16); border: 1px solid rgba(108, 112, 134, 0.4); color: #a6adc8;"

# ------------------------------------------------------------------------------------------------------------
# Rack-style Plugin Item Widget (Default View)

class RackPluginItemWidget(QFrame):
    """Sleek horizontal rack capsule item (~44px) matching Clara rack items."""

    def __init__(self, info, isFav=False, parent=None):
        super().__init__(parent)
        self.setObjectName("rackPluginItem")
        self.setFrameShape(QFrame.NoFrame)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 4, 12, 4)
        layout.setSpacing(10)

        # Left Accent Color Strip
        isSynth = bool(info.get("hints", 0) & PLUGIN_IS_SYNTH)
        color = _getCategoryColor(info.get("category", ""), isSynth)
        self.strip = QFrame(self)
        self.strip.setFixedWidth(5)
        self.strip.setFixedHeight(28)
        self.strip.setStyleSheet(f"background-color: {color}; border-radius: 2.5px;")
        layout.addWidget(self.strip)

        # Star Favorite icon
        self.lbl_star = QLabel("★" if isFav else "☆", self)
        self.lbl_star.setObjectName("itemStar")
        self.lbl_star.setFixedWidth(20)
        cursor = getattr(Qt, "PointingHandCursor", None) or getattr(Qt.CursorShape, "PointingHandCursor", None)
        if cursor is not None:
            self.lbl_star.setCursor(cursor)
        self.lbl_star.setProperty("starred", bool(isFav))
        self.lbl_star.setStyleSheet("color: #eed49f; font-size: 14px;" if isFav else "color: #6c7086; font-size: 14px;")
        layout.addWidget(self.lbl_star)

        # Format Badge
        ptype = info.get("type", PLUGIN_NONE)
        fmt = getPluginTypeAsString(ptype)
        self.lbl_badge = QLabel(fmt, self)
        self.lbl_badge.setObjectName("infoBadge")
        self.lbl_badge.setStyleSheet(f"{_getFormatBadgeStyle(ptype)} font-size: 10px; font-weight: bold; border-radius: 3px; padding: 1px 6px;")
        layout.addWidget(self.lbl_badge)

        # Name & Subtitle
        textLayout = QVBoxLayout()
        textLayout.setContentsMargins(0, 0, 0, 0)
        textLayout.setSpacing(2)

        self.lbl_name = QLabel(info.get("name", "---"), self)
        self.lbl_name.setObjectName("rackPluginName")
        f_name = self.lbl_name.font()
        f_name.setBold(True)
        self.lbl_name.setFont(f_name)

        maker = info.get("maker") or "---"
        cat = info.get("category") or ("Synth" if isSynth else "Plugin")
        self.lbl_sub = QLabel(f"{maker}  •  {cat}", self)
        self.lbl_sub.setObjectName("infoCategory")
        textLayout.addWidget(self.lbl_name)
        textLayout.addWidget(self.lbl_sub)
        layout.addLayout(textLayout, 1)

        # Right: I/O Pill
        ains = info.get("audioIns", 0)
        aouts = info.get("audioOuts", 0)
        self.lbl_io = QLabel(_formatIoText(ains, aouts), self)
        self.lbl_io.setObjectName("infoTag")
        self.lbl_io.setStyleSheet("background-color: rgba(255, 255, 255, 0.05); border: 1px solid rgba(255, 255, 255, 0.08); border-radius: 4px; padding: 1px 7px; font-size: 11px;")
        layout.addWidget(self.lbl_io)

    def setFavorite(self, isFav):
        self.lbl_star.setText("★" if isFav else "☆")
        self.lbl_star.setProperty("starred", bool(isFav))
        self.lbl_star.setStyleSheet("color: #eed49f; font-size: 14px;" if isFav else "color: #6c7086; font-size: 14px;")
        self.lbl_star.style().unpolish(self.lbl_star)
        self.lbl_star.style().polish(self.lbl_star)

    def setSelected(self, isSelected):
        self.setProperty("selected", bool(isSelected))
        self.style().unpolish(self)
        self.style().polish(self)

# ------------------------------------------------------------------------------------------------------------
# Card-style Plugin Item Widget

class CardPluginItemWidget(QFrame):
    """Modular card item (~195x120px) for grid view."""

    def __init__(self, info, isFav=False, parent=None):
        super().__init__(parent)
        self.setObjectName("cardPluginItem")
        self.setFrameShape(QFrame.NoFrame)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 0, 10, 8)
        layout.setSpacing(4)

        isSynth = bool(info.get("hints", 0) & PLUGIN_IS_SYNTH)
        color = _getCategoryColor(info.get("category", ""), isSynth)

        # Top Category Accent Strip
        self.top_strip = QFrame(self)
        self.top_strip.setFixedHeight(4)
        self.top_strip.setStyleSheet(f"background-color: {color}; border-top-left-radius: 10px; border-top-right-radius: 10px;")
        layout.addWidget(self.top_strip)

        # Top Bar: Badge + Star
        topBar = QHBoxLayout()
        topBar.setContentsMargins(0, 4, 0, 0)
        ptype = info.get("type", PLUGIN_NONE)
        fmt = getPluginTypeAsString(ptype)
        self.lbl_badge = QLabel(fmt, self)
        self.lbl_badge.setObjectName("infoBadge")
        self.lbl_badge.setStyleSheet(f"{_getFormatBadgeStyle(ptype)} font-size: 10px; font-weight: bold; border-radius: 3px; padding: 1px 5px;")
        topBar.addWidget(self.lbl_badge)
        topBar.addStretch(1)

        self.lbl_star = QLabel("★" if isFav else "☆", self)
        self.lbl_star.setObjectName("itemStar")
        cursor = getattr(Qt, "PointingHandCursor", None) or getattr(Qt.CursorShape, "PointingHandCursor", None)
        if cursor is not None:
            self.lbl_star.setCursor(cursor)
        self.lbl_star.setProperty("starred", bool(isFav))
        self.lbl_star.setStyleSheet("color: #eed49f; font-size: 14px;" if isFav else "color: #6c7086; font-size: 14px;")
        topBar.addWidget(self.lbl_star)
        layout.addLayout(topBar)

        # Center: Name & Maker
        self.lbl_name = QLabel(info.get("name", "---"), self)
        self.lbl_name.setObjectName("cardPluginName")
        self.lbl_name.setAutoFillBackground(False)
        f_name = self.lbl_name.font()
        f_name.setBold(True)
        self.lbl_name.setFont(f_name)
        self.lbl_name.setWordWrap(True)
        layout.addWidget(self.lbl_name, 1)

        self.lbl_maker = QLabel(info.get("maker") or "---", self)
        self.lbl_maker.setObjectName("infoMaker")
        self.lbl_maker.setAutoFillBackground(False)
        self.lbl_maker.setStyleSheet("background: transparent; color: #8aadf4; font-size: 11px;")
        layout.addWidget(self.lbl_maker)

        # Subtle divider above bottom bar
        self.div_line = QFrame(self)
        self.div_line.setFixedHeight(1)
        self.div_line.setStyleSheet("background-color: rgba(255, 255, 255, 0.08); border: none;")
        layout.addWidget(self.div_line)

        # Bottom: Category & I/O
        botBar = QHBoxLayout()
        botBar.setContentsMargins(0, 2, 0, 0)
        cat = info.get("category") or ("Synth" if isSynth else "Plugin")
        self.lbl_cat = QLabel(cat, self)
        self.lbl_cat.setObjectName("infoCategory")
        self.lbl_cat.setAutoFillBackground(False)
        self.lbl_cat.setStyleSheet("background: transparent; color: #a5adcb; font-size: 11px;")
        botBar.addWidget(self.lbl_cat)
        botBar.addStretch(1)

        ains = info.get("audioIns", 0)
        aouts = info.get("audioOuts", 0)
        self.lbl_io = QLabel(_formatIoText(ains, aouts), self)
        self.lbl_io.setObjectName("infoTag")
        self.lbl_io.setStyleSheet("background-color: rgba(255, 255, 255, 0.05); border: 1px solid rgba(255, 255, 255, 0.08); border-radius: 4px; padding: 1px 6px; font-size: 11px;")
        botBar.addWidget(self.lbl_io)
        layout.addLayout(botBar)

    def setFavorite(self, isFav):
        self.lbl_star.setText("★" if isFav else "☆")
        self.lbl_star.setProperty("starred", bool(isFav))
        self.lbl_star.setStyleSheet("color: #eed49f; font-size: 14px;" if isFav else "color: #6c7086; font-size: 14px;")
        self.lbl_star.style().unpolish(self.lbl_star)
        self.lbl_star.style().polish(self.lbl_star)

    def setSelected(self, isSelected):
        self.setProperty("selected", bool(isSelected))
        self.style().unpolish(self)
        self.style().polish(self)

# ------------------------------------------------------------------------------------------------------------
# The main dialog

class PyPluginListDialog(QDialog):
    pluginAddRequested = pyqtSignal(dict)

    def __init__(self, parent, hostSettings):
        super().__init__(parent)
        self.setWindowTitle(self.tr("Carla - Add New"))

        hostSettings = hostSettings or {}

        # -- discovery state -----------------------------------------------------------------------------
        self.paths = _defaultPluginPaths()
        self.cache = {}          # sha1 -> [PluginInfo dict]
        self.favorites = []      # [ {'type', 'uniqueId', 'filename', 'label'} ]
        self._plugins = {
            "internal": [], "ladspa": [], "dssi": [], "lv2": [], "vst2": [],
            "vst3": [], "clap": [], "au": [], "jsfx": [], "kits": [],
        }

        self.retPlugin = {}
        self._rowPluginData = {}

        self._lastTableWidgetIndex = 0
        self._refreshDialog = None

        self._discovery = {
            "btype": BINARY_NATIVE,
            "ptype": PLUGIN_NONE,
            "firstInit": True,
            "ignoreCache": False,
            "checkInvalid": False,
            "usePluginBridges": bool(hostSettings.get("showPluginBridges", False)),
            "useWineBridges": bool(hostSettings.get("showWineBridges", False)),
            "handle": None,
            "tool": "",
        }
        self._restartDiscoveryTool()

        # -- search debounce timer -----------------------------------------------------------------------
        self._searchDebounceTimer = QTimer(self)
        self._searchDebounceTimer.setSingleShot(True)
        self._searchDebounceTimer.setInterval(40)
        self._searchDebounceTimer.timeout.connect(self._checkFilters)

        # -- global discovery options --------------------------------------------------------------------
        if not CARLA_OS_WIN:
            try:
                set_option(ENGINE_OPTION_WINE_AUTO_PREFIX, 1 if hostSettings.get("wineAutoPrefix") else 0, None)
                set_option(ENGINE_OPTION_WINE_EXECUTABLE, 0, hostSettings.get("wineExecutable") or "")
                set_option(ENGINE_OPTION_WINE_FALLBACK_PREFIX, 0, hostSettings.get("wineFallbackPrefix") or "")
            except Exception as exc:  # pragma: no cover
                log_carla(f"PyPluginListDialog: set_option failed: {exc}", level="debug")

        # -- build UI ------------------------------------------------------------------------------------
        self._buildUi(hostSettings)

        # -- connections ---------------------------------------------------------------------------------
        self.finished.connect(self._saveSettings)
        self.b_add.clicked.connect(self._slotAddClicked)
        self.b_cancel.clicked.connect(self.reject)
        self.b_clear_filters.clicked.connect(self._clearFilters)

        self.lineEdit.textChanged.connect(lambda _text: self._searchDebounceTimer.start())
        self.table.itemSelectionChanged.connect(self._updateSelectionState)
        self.table.currentCellChanged.connect(self._onTableCurrentCellChanged)
        self.table.cellClicked.connect(self._cellClicked)
        self.table.cellDoubleClicked.connect(self._cellDoubleClicked)
        self.table.horizontalHeader().sectionClicked.connect(self._onHeaderClicked)

        # Custom sorting: the table, rack and cards lists must always share the same row
        # order so their index-based linking stays valid (Qt's built-in sort only reorders
        # the table and would desync the other two views).
        self._sortColumn = TW_NAME
        self._sortOrder = Qt.AscendingOrder

        self.list_rack.itemSelectionChanged.connect(self._onListSelectionChanged)
        self.list_cards.itemSelectionChanged.connect(self._onListSelectionChanged)
        self.list_rack.currentItemChanged.connect(self._onRackCurrentItemChanged)
        self.list_cards.currentItemChanged.connect(self._onCardsCurrentItemChanged)
        self.list_rack.itemDoubleClicked.connect(lambda _it: self._slotAddClicked())
        self.list_cards.itemDoubleClicked.connect(lambda _it: self._slotAddClicked())
        self.list_rack.verticalScrollBar().valueChanged.connect(self._onRackScroll)
        self.list_cards.verticalScrollBar().valueChanged.connect(self._onCardsScroll)

        self._lazyTimer = QTimer(self)
        self._lazyTimer.setInterval(12)
        self._lazyTimer.timeout.connect(self._streamNextChunk)
        self._lazyIndex = 0
        self._lazyTotal = 0

        for grp in (self.group_format, self.group_type, self.group_cat, self.group_arch, self.group_req):
            grp.changed.connect(self._checkFilters)
        self.ch_favorites.clicked.connect(lambda _checked=False: self._checkFilters())

        # Ctrl+F focus search
        self.act_focus_search = QAction(self.tr("Focus Text Search"), self)
        self.act_focus_search.setShortcut("Ctrl+F")
        self.act_focus_search.triggered.connect(self.focusSearchFieldAndSelectAll)
        self.addAction(self.act_focus_search)

        # -- only native by default ----------------------------------------------------------------------
        if CARLA_OS_64BIT:
            self.ch_bridged.setText(self.tr("Bridged (32bit)"))
        else:
            self.ch_bridged.setChecked(False)
            self.ch_bridged.setEnabled(False)

        if not (CARLA_OS_WIN or CARLA_OS_MAC):
            # bridged wine only really usable on linux
            pass

        if CARLA_OS_MAC:
            self.setWindowModality(Qt.WindowModal)
        else:
            self.ch_au.setChecked(False)
            self.ch_au.setEnabled(False)
            self.ch_au.setVisible(False)

        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)

        # -- load settings + cache -----------------------------------------------------------------------
        self._loadSettings()

        # start with no plugin selected
        self._checkPlugin(-1)

        # -- discovery timer -----------------------------------------------------------------------------
        self._timer = QTimer(self)
        self._timer.setInterval(0)
        self._timer.timeout.connect(self._discoveryStep)

    # ----------------------------------------------------------------------------------------------------
    # UI construction

    def _buildUi(self, hostSettings):
        grid = QGridLayout(self)

        # row 0: search + view mode switcher + refresh
        searchRow = QHBoxLayout()
        self.lineEdit = QLineEdit(self)
        self.lineEdit.setClearButtonEnabled(True)
        searchRow.addWidget(self.lineEdit)

        # Single View Mode Toggle Button (cycles Rack -> Cards -> Table)
        self.btn_view_mode = QPushButton(self)
        self.btn_view_mode.setObjectName("btnViewMode")
        self.btn_view_mode.clicked.connect(self._cycleViewMode)
        searchRow.addWidget(self.btn_view_mode)

        # Rescan Buttons (Quick Rescan and Full Rescan separate)
        self.b_refresh = QPushButton(self.tr("Rescan"), self)
        self.b_refresh.setIcon(getIcon("view-refresh", 16, "svgz"))
        self.b_refresh.setToolTip(self.tr("Quick Rescan (New & Modified plugins)"))
        self.b_refresh.clicked.connect(lambda: self._startScan(ignoreCache=False))
        searchRow.addWidget(self.b_refresh)

        self.b_refresh_full = QPushButton(self.tr("Full Rescan"), self)
        self.b_refresh_full.setIcon(getIcon("view-refresh", 16, "svgz"))
        self.b_refresh_full.setToolTip(self.tr("Full Rescan (Check all plugins from scratch)"))
        self.b_refresh_full.clicked.connect(lambda: self._startScan(ignoreCache=True))
        searchRow.addWidget(self.b_refresh_full)

        grid.addLayout(searchRow, 0, 1, 1, 1)

        # row 1: inline scan status bar (hidden by default)
        self.scanBar = QWidget(self)
        scanLayout = QHBoxLayout(self.scanBar)
        scanLayout.setContentsMargins(2, 2, 2, 2)
        self.scanStatusLabel = QLabel(self.tr("Scanning plugins..."), self.scanBar)
        self.scanProgressBar = QProgressBar(self.scanBar)
        self.scanProgressBar.setRange(0, 0)
        self.scanProgressBar.setFixedHeight(12)
        self.b_scan_stop = QPushButton(self.tr("Stop"), self.scanBar)
        self.b_scan_stop.setIcon(getIcon("media-playback-stop", 16, "svgz"))
        self.b_scan_stop.clicked.connect(self._stopScan)
        scanLayout.addWidget(self.scanStatusLabel)
        scanLayout.addWidget(self.scanProgressBar, 1)
        scanLayout.addWidget(self.b_scan_stop)
        self.scanBar.hide()
        grid.addWidget(self.scanBar, 1, 1, 1, 1)

        # col 0: filters sidebar (spans rows 0..4)
        self._buildFilters()
        grid.addWidget(self.filterSidebar, 0, 0, 5, 1)

        # col 1: center stack (0: Rack, 1: Cards, 2: Table)
        self.stackCenter = QStackedWidget(self)
        self.stackCenter.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        # Mode 0: Rack Mode (Default)
        self.list_rack = QListWidget(self)
        self.list_rack.setObjectName("pluginRackListWidget")
        self.list_rack.setSelectionMode(_EXTENDED_SELECTION)
        self.list_rack.setVerticalScrollMode(_SCROLL_PER_PIXEL)
        self.list_rack.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.list_rack.setSpacing(3)
        self.list_rack.setStyleSheet(
            "QListWidget { background: transparent; border: none; outline: none; } "
            "QListWidget::item { border: none; background: transparent; padding: 1px 0px; } "
            "QListWidget::item:selected { border: none; background: transparent; }"
        )
        self.stackCenter.addWidget(self.list_rack)

        # Mode 1: Cards Mode
        self.list_cards = QListWidget(self)
        self.list_cards.setObjectName("pluginCardsListWidget")
        self.list_cards.setViewMode(_ICON_MODE)
        self.list_cards.setResizeMode(_ADJUST)
        self.list_cards.setMovement(_STATIC)
        self.list_cards.setSelectionMode(_EXTENDED_SELECTION)
        self.list_cards.setVerticalScrollMode(_SCROLL_PER_PIXEL)
        self.list_cards.setSpacing(8)
        self.list_cards.setStyleSheet(
            "QListWidget { background: transparent; border: none; outline: none; } "
            "QListWidget::item { border: none; background: transparent; padding: 3px; } "
            "QListWidget::item:selected { border: none; background: transparent; }"
        )
        self.stackCenter.addWidget(self.list_cards)

        # Mode 2: Table Mode
        self.table = QTableWidget(0, _TABLE_COLUMNS, self)
        self.table.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.table.setEditTriggers(_NO_EDIT_TRIGGERS)
        self.table.setShowGrid(False)
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionMode(_EXTENDED_SELECTION)
        self.table.setSelectionBehavior(_SELECT_ROWS)
        self.table.setWordWrap(False)
        self.table.setSortingEnabled(False)
        self.table.verticalHeader().setVisible(False)
        self.table.verticalHeader().setDefaultSectionSize(30)
        self.table.setHorizontalHeaderLabels(["", self.tr("Name"), self.tr("Label/Id/URI"),
                                              self.tr("Maker"), self.tr("Binary/Filename")])
        hh = self.table.horizontalHeader()
        hh.setStretchLastSection(True)
        hh.setMinimumSectionSize(24)
        hh.setFixedHeight(28)
        hh.setHighlightSections(False)
        self.table.setColumnWidth(TW_FAVORITE, 26)
        self.table.setColumnWidth(TW_NAME, 260)
        self.table.setColumnWidth(TW_LABEL, 200)
        self.table.setColumnWidth(TW_MAKER, 160)
        self.stackCenter.addWidget(self.table)

        self.stackCenter.setCurrentIndex(0)
        grid.addWidget(self.stackCenter, 2, 1, 3, 1)

        # col 2: info inspector panel (spans rows 0..4)
        self._buildInfoPanel()
        grid.addWidget(self.infoPanel, 0, 2, 5, 1)

        # row 5: status + buttons
        bottomRow = QHBoxLayout()
        self.label = QLabel(self.tr("(Number of Plugins go here)"), self)
        self.label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        bottomRow.addWidget(self.label)
        bottomRow.addStretch(1)

        self.ch_keep_open = QCheckBox(self.tr("Keep open"), self)
        bottomRow.addWidget(self.ch_keep_open)

        c_bridge_label = QLabel(self.tr("Mode:"), self)
        bottomRow.addWidget(c_bridge_label)

        self.c_bridge_mode = QComboBox(self)
        self.c_bridge_mode.addItem(self.tr("Default"), PLUGIN_OPTIONS_NULL)
        self.c_bridge_mode.addItem(self.tr("In-process (inline display)"), PLUGIN_OPTION_AVOID_BRIDGE)
        self.c_bridge_mode.addItem(self.tr("Bridged (sandboxed)"), PLUGIN_OPTION_USE_BRIDGE)
        self.c_bridge_mode.setToolTip(self.tr(
            "Run this plugin in-process so it can show an inline display, "
            "or through a bridge for sandboxing (no inline display)."))
        bottomRow.addWidget(self.c_bridge_mode)

        self.b_add = QPushButton(self.tr("&Add Plugin"), self)
        self.b_add.setIcon(getIcon("list-add", 16, "svgz"))
        self.b_add.setEnabled(False)
        bottomRow.addWidget(self.b_add)

        self.b_cancel = QPushButton(self.tr("Cancel"), self)
        self.b_cancel.setIcon(getIcon("dialog-cancel", 16, "svgz"))
        bottomRow.addWidget(self.b_cancel)

        grid.addLayout(bottomRow, 5, 0, 1, 3)

        grid.setColumnStretch(0, 0)
        grid.setColumnStretch(1, 1)
        grid.setColumnStretch(2, 0)
        grid.setRowStretch(2, 1)

    def _buildFilters(self):
        self.filterSidebar = QWidget(self)
        self.filterSidebar.setObjectName("filterSidebar")
        self.filterSidebar.setMinimumWidth(210)
        self.filterSidebar.setMaximumWidth(270)

        sidebarLayout = QVBoxLayout(self.filterSidebar)
        sidebarLayout.setContentsMargins(4, 2, 4, 2)
        sidebarLayout.setSpacing(6)

        # Header: Filters label + Favorites pill
        headerRow = QHBoxLayout()
        headerRow.setContentsMargins(0, 0, 0, 0)
        lbl_filters = QLabel(self.tr("FILTERS"), self.filterSidebar)
        font_hf = lbl_filters.font()
        font_hf.setPointSize(max(8, font_hf.pointSize() - 1))
        font_hf.setBold(True)
        lbl_filters.setFont(font_hf)
        headerRow.addWidget(lbl_filters)
        headerRow.addStretch(1)

        self.ch_favorites = QPushButton(self.tr("★ Favorites"), self.filterSidebar)
        self.ch_favorites.setCheckable(True)
        self.ch_favorites.setProperty("pill", True)
        self.ch_favorites.setToolTip(self.tr("Show favorites only"))
        headerRow.addWidget(self.ch_favorites)
        sidebarLayout.addLayout(headerRow)

        # Scroll area for the filter pill groups
        scrollArea = QScrollArea(self.filterSidebar)
        scrollArea.setWidgetResizable(True)
        scrollArea.setFrameShape(QScrollArea.NoFrame)
        scrollArea.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        scrollWidget = QWidget(scrollArea)
        scrollLayout = QVBoxLayout(scrollWidget)
        scrollLayout.setContentsMargins(0, 0, 2, 0)
        scrollLayout.setSpacing(8)

        # 1. Format
        self.ch_clap = QPushButton("CLAP", self)
        self.ch_vst3 = QPushButton("VST3", self)
        self.ch_lv2 = QPushButton("LV2", self)
        self.ch_vst = QPushButton("VST2", self)
        self.ch_jsfx = QPushButton("JSFX", self)
        self.ch_internal = QPushButton(self.tr("Internal"), self)
        self.ch_ladspa = QPushButton("LADSPA", self)
        self.ch_dssi = QPushButton("DSSI", self)
        self.ch_kits = QPushButton(self.tr("Sound Kits"), self)
        self.ch_au = QPushButton("AU", self)
        if not CARLA_OS_MAC:
            self.ch_au.setEnabled(False)

        format_pills = [
            ("clap", self.ch_clap),
            ("vst3", self.ch_vst3),
            ("lv2", self.ch_lv2),
            ("vst2", self.ch_vst),
            ("jsfx", self.ch_jsfx),
            ("internal", self.ch_internal),
            ("ladspa", self.ch_ladspa),
            ("dssi", self.ch_dssi),
            ("kits", self.ch_kits),
        ]
        if CARLA_OS_MAC:
            format_pills.append(("au", self.ch_au))

        self.group_format = PillFilterGroup(self.tr("Format"), format_pills, scrollWidget)
        self.ch_format_all = self.group_format.btn_all
        scrollLayout.addWidget(self.group_format)

        # 2. Type
        self.ch_instruments = QPushButton(self.tr("Instruments"), self)
        self.ch_effects = QPushButton(self.tr("Effects"), self)
        self.ch_midi = QPushButton(self.tr("MIDI Tools"), self)
        self.ch_other = QPushButton(self.tr("Other/Misc"), self)

        type_pills = [
            ("instruments", self.ch_instruments),
            ("effects", self.ch_effects),
            ("midi", self.ch_midi),
            ("other", self.ch_other),
        ]
        self.group_type = PillFilterGroup(self.tr("Type"), type_pills, scrollWidget)
        self.ch_type_all = self.group_type.btn_all
        scrollLayout.addWidget(self.group_type)

        # 3. Category
        self.ch_cat_synth = QPushButton(self.tr("Synth"), self)
        self.ch_cat_delay = QPushButton(self.tr("Delay"), self)
        self.ch_cat_distortion = QPushButton(self.tr("Distortion"), self)
        self.ch_cat_dynamics = QPushButton(self.tr("Dynamics"), self)
        self.ch_cat_eq = QPushButton(self.tr("EQ"), self)
        self.ch_cat_filter = QPushButton(self.tr("Filter"), self)
        self.ch_cat_modulator = QPushButton(self.tr("Modulator"), self)
        self.ch_cat_utility = QPushButton(self.tr("Utility"), self)
        self.ch_cat_other = QPushButton(self.tr("Other"), self)

        cat_pills = [
            ("synth", self.ch_cat_synth),
            ("delay", self.ch_cat_delay),
            ("distortion", self.ch_cat_distortion),
            ("dynamics", self.ch_cat_dynamics),
            ("eq", self.ch_cat_eq),
            ("filter", self.ch_cat_filter),
            ("modulator", self.ch_cat_modulator),
            ("utility", self.ch_cat_utility),
            ("other", self.ch_cat_other),
        ]
        self.group_cat = PillFilterGroup(self.tr("Category"), cat_pills, scrollWidget)
        self.ch_cat_all = self.group_cat.btn_all
        scrollLayout.addWidget(self.group_cat)

        # 4. Architecture
        self.ch_native = QPushButton(self.tr("Native"), self)
        self.ch_bridged = QPushButton(self.tr("Bridged"), self)
        self.ch_bridged_wine = QPushButton(self.tr("Bridged (Wine)"), self)

        arch_pills = [
            ("native", self.ch_native),
            ("bridged", self.ch_bridged),
            ("bridged_wine", self.ch_bridged_wine),
        ]
        self.group_arch = PillFilterGroup(self.tr("Architecture"), arch_pills, scrollWidget)
        self.ch_arch_all = self.group_arch.btn_all
        scrollLayout.addWidget(self.group_arch)

        # 5. Requirements
        self.ch_rtsafe = QPushButton(self.tr("RT-Safe"), self)
        self.ch_stereo = QPushButton(self.tr("Stereo"), self)
        self.ch_cv = QPushButton(self.tr("CV Ports"), self)
        self.ch_gui = QPushButton(self.tr("Custom GUI"), self)
        self.ch_inline_display = QPushButton(self.tr("Inline Display"), self)

        req_pills = [
            ("rtsafe", self.ch_rtsafe),
            ("stereo", self.ch_stereo),
            ("cv", self.ch_cv),
            ("gui", self.ch_gui),
            ("inline_display", self.ch_inline_display),
        ]
        self.group_req = PillFilterGroup(self.tr("Requirements"), req_pills, scrollWidget, all_label=self.tr("Any"))
        self.ch_req_all = self.group_req.btn_all
        scrollLayout.addWidget(self.group_req)

        scrollLayout.addStretch(1)
        scrollArea.setWidget(scrollWidget)
        sidebarLayout.addWidget(scrollArea, 1)

        # Reset filters button anchored at the bottom (simplified flat action)
        self.b_clear_filters = QPushButton(self.tr("Reset filters"), self.filterSidebar)
        self.b_clear_filters.setObjectName("btnClearFilters")
        self.b_clear_filters.setFlat(True)
        self.b_clear_filters.setIcon(getIcon("edit-clear", 16, "svgz"))
        self.b_clear_filters.setToolTip(self.tr("Reset all format, type, category, architecture, and requirement filters"))
        sidebarLayout.addWidget(self.b_clear_filters)

        self.filterBox = self.filterSidebar

        # Ensure filter sidebar pills use the active theme accent/highlight color and stable pill geometry
        app = QApplication.instance()
        if app is not None:
            from styles.theme_manager import theme_manager
            hl = theme_manager.engine.get_token("accent") or app.palette().color(QPalette.Highlight).name()
            txt = theme_manager.engine.get_token("bg-primary") or app.palette().color(QPalette.HighlightedText).name()
            bg_surf = theme_manager.engine.get_token("bg-surface") or app.palette().color(QPalette.Button).name()
            b_dim = theme_manager.engine.get_token("border-dim") or app.palette().color(QPalette.Mid).name()
            t_sec = theme_manager.engine.get_token("text-secondary") or app.palette().color(QPalette.ButtonText).name()
            self.filterSidebar.setStyleSheet(f"""
                QPushButton[pill="true"] {{
                    background-color: {bg_surf};
                    color: {t_sec};
                    border: 1px solid {b_dim};
                    padding: 2px 9px;
                    font-size: 11px;
                    border-radius: 12px;
                    min-height: 20px;
                    max-height: 20px;
                }}
                QPushButton[pill="true"]:hover {{
                    border-color: {hl};
                }}
                QPushButton[pill="true"]:checked {{
                    background-color: {hl};
                    color: {txt};
                    border: 1px solid {hl};
                    border-radius: 12px;
                    padding: 2px 9px;
                    font-size: 11px;
                    min-height: 20px;
                    max-height: 20px;
                    font-weight: bold;
                }}
                QPushButton[pill="true"]:checked:hover {{
                    background-color: {hl};
                    color: {txt};
                    border: 1px solid {hl};
                    border-radius: 12px;
                }}
                QPushButton#btnClearFilters {{
                    background-color: transparent;
                    border: 1px dashed palette(mid);
                    border-radius: 6px;
                    padding: 3px 8px;
                    font-size: 11px;
                    color: palette(text);
                }}
                QPushButton#btnClearFilters:hover {{
                    background-color: palette(midlight);
                    border-color: palette(highlight);
                    color: palette(highlight);
                }}
            """)

    def _buildInfoPanel(self):
        self.infoPanel = QWidget(self)
        self.infoPanel.setObjectName("infoPanel")
        self.infoPanel.setMinimumWidth(250)
        self.infoPanel.setMaximumWidth(310)

        mainLayout = QVBoxLayout(self.infoPanel)
        mainLayout.setContentsMargins(6, 2, 4, 2)
        mainLayout.setSpacing(6)

        # Header: INFORMATION + Format Badge
        headerRow = QHBoxLayout()
        headerRow.setContentsMargins(0, 0, 0, 0)
        lbl_info = QLabel(self.tr("INFORMATION"), self.infoPanel)
        font_h = lbl_info.font()
        font_h.setPointSize(max(8, font_h.pointSize() - 1))
        font_h.setBold(True)
        lbl_info.setFont(font_h)
        headerRow.addWidget(lbl_info)
        headerRow.addStretch(1)

        self.l_badge = QLabel("---", self.infoPanel)
        self.l_badge.setObjectName("infoBadge")
        headerRow.addWidget(self.l_badge)
        mainLayout.addLayout(headerRow)

        # Scroll Area for the inspector cards
        scrollArea = QScrollArea(self.infoPanel)
        scrollArea.setWidgetResizable(True)
        scrollArea.setFrameShape(QScrollArea.NoFrame)
        scrollArea.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        scrollWidget = QWidget(scrollArea)
        scrollLayout = QVBoxLayout(scrollWidget)
        scrollLayout.setContentsMargins(0, 0, 2, 0)
        scrollLayout.setSpacing(8)

        # 1. Title & Maker Card
        cardName = QFrame(scrollWidget)
        cardName.setObjectName("infoCard")
        l_cardName = QVBoxLayout(cardName)
        l_cardName.setContentsMargins(8, 8, 8, 8)
        l_cardName.setSpacing(2)

        self.l_name = QLabel(self.tr("No plugin selected"), cardName)
        font_name = self.l_name.font()
        font_name.setPointSize(font_name.pointSize() + 2)
        font_name.setBold(True)
        self.l_name.setFont(font_name)
        self.l_name.setWordWrap(True)

        self.l_maker = QLabel("---", cardName)
        self.l_maker.setObjectName("infoMaker")

        self.l_category = QLabel("---", cardName)
        self.l_category.setObjectName("infoCategory")

        l_cardName.addWidget(self.l_name)
        l_cardName.addWidget(self.l_maker)
        l_cardName.addWidget(self.l_category)
        scrollLayout.addWidget(cardName)

        # 2. Architecture Card
        lbl_arch_hdr = QLabel(self.tr("ARCHITECTURE"), scrollWidget)
        lbl_arch_hdr.setFont(font_h)
        scrollLayout.addWidget(lbl_arch_hdr)

        cardArch = QFrame(scrollWidget)
        cardArch.setObjectName("infoCard")
        l_cardArch = QGridLayout(cardArch)
        l_cardArch.setContentsMargins(8, 6, 8, 6)
        l_cardArch.setVerticalSpacing(4)

        self.l_arch = QLabel("---", cardArch)
        self.l_exec = QLabel("---", cardArch)
        self.l_bridged = QLabel("---", cardArch)

        l_cardArch.addWidget(QLabel(self.tr("Binary Arch:"), cardArch), 0, 0)
        l_cardArch.addWidget(self.l_arch, 0, 1)
        l_cardArch.addWidget(QLabel(self.tr("Execution:"), cardArch), 1, 0)
        l_cardArch.addWidget(self.l_exec, 1, 1)
        l_cardArch.addWidget(QLabel(self.tr("Bridged:"), cardArch), 2, 0)
        l_cardArch.addWidget(self.l_bridged, 2, 1)
        scrollLayout.addWidget(cardArch)

        # 3. I/O & Signals Card
        lbl_io_hdr = QLabel(self.tr("I/O & SIGNALS"), scrollWidget)
        lbl_io_hdr.setFont(font_h)
        scrollLayout.addWidget(lbl_io_hdr)

        cardIO = QFrame(scrollWidget)
        cardIO.setObjectName("infoCard")
        l_cardIO = QGridLayout(cardIO)
        l_cardIO.setContentsMargins(8, 6, 8, 6)
        l_cardIO.setVerticalSpacing(4)

        self.l_audio_io = QLabel("---", cardIO)
        self.l_midi_io = QLabel("---", cardIO)
        self.l_pins = QLabel("---", cardIO)
        self.l_cv_io = QLabel("---", cardIO)

        l_cardIO.addWidget(QLabel(self.tr("Audio Ins/Outs:"), cardIO), 0, 0)
        l_cardIO.addWidget(self.l_audio_io, 0, 1)
        l_cardIO.addWidget(QLabel(self.tr("MIDI Ins/Outs:"), cardIO), 1, 0)
        l_cardIO.addWidget(self.l_midi_io, 1, 1)
        l_cardIO.addWidget(QLabel(self.tr("Parameters:"), cardIO), 2, 0)
        l_cardIO.addWidget(self.l_pins, 2, 1)
        l_cardIO.addWidget(QLabel(self.tr("CV Ins/Outs:"), cardIO), 3, 0)
        l_cardIO.addWidget(self.l_cv_io, 3, 1)
        scrollLayout.addWidget(cardIO)

        # 4. Requirements & Features Card
        lbl_feat_hdr = QLabel(self.tr("FEATURES & REQUIREMENTS"), scrollWidget)
        lbl_feat_hdr.setFont(font_h)
        scrollLayout.addWidget(lbl_feat_hdr)

        self.cardFeat = QFrame(scrollWidget)
        self.cardFeat.setObjectName("infoCard")
        self.flowFeat = FlowLayout(self.cardFeat, hSpacing=4, vSpacing=4)
        self.flowFeat.setContentsMargins(6, 6, 6, 6)
        tagNone = QLabel(self.tr("None"), self.cardFeat)
        tagNone.setObjectName("infoTag")
        self.flowFeat.addWidget(tagNone)
        scrollLayout.addWidget(self.cardFeat)

        # 5. File Location
        lbl_file_hdr = QLabel(self.tr("FILE LOCATION"), scrollWidget)
        lbl_file_hdr.setFont(font_h)
        scrollLayout.addWidget(lbl_file_hdr)

        self.l_binary = QLineEdit(scrollWidget)
        self.l_binary.setReadOnly(True)
        self.l_binary.setPlaceholderText("---")
        scrollLayout.addWidget(self.l_binary)

        scrollLayout.addStretch(1)
        scrollArea.setWidget(scrollWidget)
        mainLayout.addWidget(scrollArea, 1)

        # Legacy label references for backward compatibility
        self.l_format = self.l_badge
        self.l_type = self.l_category
        self.l_id = QLabel("---", self.infoPanel)
        self.l_ains = QLabel("---", self.infoPanel)
        self.l_aouts = QLabel("---", self.infoPanel)
        self.l_cvins = QLabel("---", self.infoPanel)
        self.l_cvouts = QLabel("---", self.infoPanel)
        self.l_mins = QLabel("---", self.infoPanel)
        self.l_mouts = QLabel("---", self.infoPanel)
        self.l_pouts = QLabel("---", self.infoPanel)
        self.l_gui = QLabel("---", self.infoPanel)
        self.l_idisp = QLabel("---", self.infoPanel)
        self.l_synth = QLabel("---", self.infoPanel)

        self.tab_info = self.infoPanel

    # ----------------------------------------------------------------------------------------------------
    # public API

    def getSelectedPluginInfo(self):
        return self.retPlugin

    def setPluginPath(self, ptype, path):
        if ptype in self.paths:
            self.paths[ptype] = path

    def exec(self):
        try:
            res = super().exec()
        except AttributeError:  # pragma: no cover - PyQt5
            res = super().exec_()
        return bool(res)

    # ----------------------------------------------------------------------------------------------------
    # QDialog overrides

    def done(self, r):
        if r == _qt_accepted() and self.table.currentRow() >= 0:
            item = self.table.item(self.table.currentRow(), TW_NAME)
            data = item.data(int(Qt.UserRole) + UR_PLUGIN_INFO) if item is not None else None
            if data is not None:
                info, _ = _bytesToInfo(bytes(data) if isinstance(data, QByteArray) else bytes(data))
                self.retPlugin = info or {}
            else:
                self.retPlugin = {}
        else:
            self.retPlugin = {}
        super().done(r)

    def showEvent(self, event):
        self.focusSearchFieldAndSelectAll()
        super().showEvent(event)

        if self._discovery["firstInit"]:
            self._discovery["firstInit"] = False
            self._addPluginsToTable()   # show instantly from cache

        self._ensureVisibleWidgets()

        # Connect to background scanner if running
        try:
            from pluginlist.startup_scanner import getGlobalScanner
            scanner = getGlobalScanner()
            if scanner.isRunning():
                self._connectScanner(scanner)
                self.scanBar.show()
            else:
                self.scanBar.hide()
        except Exception as exc:
            log_carla(f"PyPluginListDialog: Failed to check global scanner: {exc}", level="debug")

    # ----------------------------------------------------------------------------------------------------
    # settings

    def _loadSettings(self):
        settings = _newSettings()
        self.ch_keep_open.setChecked(_getBool(settings, "PluginDatabase/KeepOpen", False))

        mode = _getInt(settings, "PluginDatabase/ViewMode", 0)
        self._setViewMode(mode)

        geo = _getBytes(settings, "PluginDatabase/Geometry")
        if geo:
            self.restoreGeometry(QByteArray(geo))

        self.ch_effects.setChecked(_getBool(settings, "PluginDatabase/ShowEffects", True))
        self.ch_instruments.setChecked(_getBool(settings, "PluginDatabase/ShowInstruments", True))
        self.ch_midi.setChecked(_getBool(settings, "PluginDatabase/ShowMIDI", True))
        self.ch_other.setChecked(_getBool(settings, "PluginDatabase/ShowOther", True))
        self.ch_internal.setChecked(_getBool(settings, "PluginDatabase/ShowInternal", True))
        self.ch_ladspa.setChecked(_getBool(settings, "PluginDatabase/ShowLADSPA", True))
        self.ch_dssi.setChecked(_getBool(settings, "PluginDatabase/ShowDSSI", True))
        self.ch_lv2.setChecked(_getBool(settings, "PluginDatabase/ShowLV2", True))
        self.ch_vst.setChecked(_getBool(settings, "PluginDatabase/ShowVST2", True))
        self.ch_vst3.setChecked(_getBool(settings, "PluginDatabase/ShowVST3", True))
        self.ch_clap.setChecked(_getBool(settings, "PluginDatabase/ShowCLAP", True))
        if CARLA_OS_MAC:
            self.ch_au.setChecked(_getBool(settings, "PluginDatabase/ShowAU", True))
        self.ch_jsfx.setChecked(_getBool(settings, "PluginDatabase/ShowJSFX", True))
        self.ch_kits.setChecked(_getBool(settings, "PluginDatabase/ShowKits", True))
        self.ch_native.setChecked(_getBool(settings, "PluginDatabase/ShowNative", True))
        self.ch_bridged.setChecked(_getBool(settings, "PluginDatabase/ShowBridged", True))
        self.ch_bridged_wine.setChecked(_getBool(settings, "PluginDatabase/ShowBridgedWine", True))
        self.ch_favorites.setChecked(_getBool(settings, "PluginDatabase/ShowFavorites", False))
        self.ch_rtsafe.setChecked(_getBool(settings, "PluginDatabase/ShowRtSafe", False))
        self.ch_cv.setChecked(_getBool(settings, "PluginDatabase/ShowHasCV", False))
        self.ch_gui.setChecked(_getBool(settings, "PluginDatabase/ShowHasGUI", False))
        self.ch_inline_display.setChecked(_getBool(settings, "PluginDatabase/ShowHasInlineDisplay", False))
        self.ch_stereo.setChecked(_getBool(settings, "PluginDatabase/ShowStereoOnly", False))
        self.lineEdit.setText(_getStr(settings, "PluginDatabase/SearchText", ""))

        categories = _getStr(settings, "PluginDatabase/ShowCategory", "all")
        if categories == "all" or len(categories) < 2:
            self.group_cat.setAll(True)
        else:
            self.ch_cat_delay.setChecked(":delay:" in categories)
            self.ch_cat_distortion.setChecked(":distortion:" in categories)
            self.ch_cat_dynamics.setChecked(":dynamics:" in categories)
            self.ch_cat_eq.setChecked(":eq:" in categories)
            self.ch_cat_filter.setChecked(":filter:" in categories)
            self.ch_cat_modulator.setChecked(":modulator:" in categories)
            self.ch_cat_synth.setChecked(":synth:" in categories)
            self.ch_cat_utility.setChecked(":utility:" in categories)
            self.ch_cat_other.setChecked(":other:" in categories)
            self.group_cat.syncFromPills()

        # Sync pill groups state from loaded settings
        if all(b.isChecked() for b in self.group_format.buttons.values()):
            self.group_format.setAll(True)
        else:
            self.group_format.syncFromPills()

        if all(b.isChecked() for b in self.group_type.buttons.values()):
            self.group_type.setAll(True)
        else:
            self.group_type.syncFromPills()

        if all(b.isChecked() for b in self.group_arch.buttons.values()):
            self.group_arch.setAll(True)
        else:
            self.group_arch.syncFromPills()

        self.group_req.syncFromPills()

        tableGeometry = _getBytes(settings, "PluginDatabase/TableGeometry")
        hh = self.table.horizontalHeader()
        if tableGeometry:
            hh.restoreState(QByteArray(tableGeometry))
        else:
            self.table.setColumnWidth(TW_NAME, 250)
            self.table.setColumnWidth(TW_LABEL, 200)
            self.table.setColumnWidth(TW_MAKER, 150)

        # Restore the sort column/order from the header state and apply it ourselves so all
        # three views (table, rack, cards) can be rebuilt in the same order.
        col = hh.sortIndicatorSection()
        order = hh.sortIndicatorOrder()
        if not hh.isSortIndicatorShown() or not (0 <= col < _TABLE_COLUMNS):
            col, order = TW_NAME, Qt.AscendingOrder
        self._sortColumn = col
        self._sortOrder = order
        hh.setSortIndicatorShown(True)
        hh.setSortIndicator(self._sortColumn, self._sortOrder)

        hh.setSectionResizeMode(TW_FAVORITE, QHeaderView.Fixed)
        self.table.setColumnWidth(TW_FAVORITE, 24)
        self.table.setSortingEnabled(False)

        # favorites
        self.favorites = self._favoritesFromBytes(_getBytes(settings, "PluginListDialog/Favorites"))

        # load entire plugin cache
        for key in settings.allKeys():
            if not key.startswith("PluginCache/"):
                continue
            sha1 = key[12:]
            data = _getBytes(settings, key)
            if not data:
                self.cache[sha1] = []
                continue
            plist = _bytesToInfoList(data)
            self.cache[sha1] = plist
            for info in plist:
                self._pluginsAdd(info)

    def _saveSettings(self, *args):
        settings = _newSettings()

        settings.setValue("PluginDatabase/ViewMode", self.stackCenter.currentIndex())
        settings.setValue("PluginDatabase/Geometry", self.saveGeometry())
        settings.setValue("PluginDatabase/TableGeometry", self.table.horizontalHeader().saveState())
        settings.setValue("PluginDatabase/KeepOpen", self.ch_keep_open.isChecked())

        fmtAll = self.group_format.isAllChecked()
        settings.setValue("PluginDatabase/ShowInternal", True if fmtAll else self.ch_internal.isChecked())
        settings.setValue("PluginDatabase/ShowLADSPA", True if fmtAll else self.ch_ladspa.isChecked())
        settings.setValue("PluginDatabase/ShowDSSI", True if fmtAll else self.ch_dssi.isChecked())
        settings.setValue("PluginDatabase/ShowLV2", True if fmtAll else self.ch_lv2.isChecked())
        settings.setValue("PluginDatabase/ShowVST2", True if fmtAll else self.ch_vst.isChecked())
        settings.setValue("PluginDatabase/ShowVST3", True if fmtAll else self.ch_vst3.isChecked())
        settings.setValue("PluginDatabase/ShowCLAP", True if fmtAll else self.ch_clap.isChecked())
        settings.setValue("PluginDatabase/ShowAU", True if fmtAll else self.ch_au.isChecked())
        settings.setValue("PluginDatabase/ShowJSFX", True if fmtAll else self.ch_jsfx.isChecked())
        settings.setValue("PluginDatabase/ShowKits", True if fmtAll else self.ch_kits.isChecked())

        typeAll = self.group_type.isAllChecked()
        settings.setValue("PluginDatabase/ShowEffects", True if typeAll else self.ch_effects.isChecked())
        settings.setValue("PluginDatabase/ShowInstruments", True if typeAll else self.ch_instruments.isChecked())
        settings.setValue("PluginDatabase/ShowMIDI", True if typeAll else self.ch_midi.isChecked())
        settings.setValue("PluginDatabase/ShowOther", True if typeAll else self.ch_other.isChecked())

        archAll = self.group_arch.isAllChecked()
        settings.setValue("PluginDatabase/ShowNative", True if archAll else self.ch_native.isChecked())
        settings.setValue("PluginDatabase/ShowBridged", True if archAll else self.ch_bridged.isChecked())
        settings.setValue("PluginDatabase/ShowBridgedWine", True if archAll else self.ch_bridged_wine.isChecked())

        settings.setValue("PluginDatabase/ShowFavorites", self.ch_favorites.isChecked())
        settings.setValue("PluginDatabase/ShowRtSafe", self.ch_rtsafe.isChecked())
        settings.setValue("PluginDatabase/ShowHasCV", self.ch_cv.isChecked())
        settings.setValue("PluginDatabase/ShowHasGUI", self.ch_gui.isChecked())
        settings.setValue("PluginDatabase/ShowHasInlineDisplay", self.ch_inline_display.isChecked())
        settings.setValue("PluginDatabase/ShowStereoOnly", self.ch_stereo.isChecked())
        settings.setValue("PluginDatabase/SearchText", self.lineEdit.text())

        if self.group_cat.isAllChecked():
            settings.setValue("PluginDatabase/ShowCategory", "all")
        else:
            categories = ""
            if self.ch_cat_delay.isChecked():
                categories += ":delay"
            if self.ch_cat_distortion.isChecked():
                categories += ":distortion"
            if self.ch_cat_dynamics.isChecked():
                categories += ":dynamics"
            if self.ch_cat_eq.isChecked():
                categories += ":eq"
            if self.ch_cat_filter.isChecked():
                categories += ":filter"
            if self.ch_cat_modulator.isChecked():
                categories += ":modulator"
            if self.ch_cat_synth.isChecked():
                categories += ":synth"
            if self.ch_cat_utility.isChecked():
                categories += ":utility"
            if self.ch_cat_other.isChecked():
                categories += ":other"
            if categories:
                categories += ":"
            settings.setValue("PluginDatabase/ShowCategory", categories)

        settings.setValue("PluginListDialog/Favorites", self._favoritesToBytes(self.favorites))

    # ----------------------------------------------------------------------------------------------------
    # favorites serialization

    def _favoritesToBytes(self, favlist):
        out = bytearray()
        for fav in favlist:
            out += _FAV_HEADER.pack(int(fav["type"]) & 0xFFFF, int(fav["uniqueId"]) & 0xFFFFFFFFFFFFFFFF)
            out += (fav.get("filename") or "").encode("utf-8", errors="replace") + b"\0"
            out += (fav.get("label") or "").encode("utf-8", errors="replace") + b"\0"
        return QByteArray(bytes(out))

    def _favoritesFromBytes(self, data):
        if isinstance(data, QByteArray):
            data = bytes(data)
        favlist = []
        offset = 0
        while offset + _FAV_HEADER.size <= len(data):
            ptype, uniqueId = _FAV_HEADER.unpack_from(data, offset)
            offset += _FAV_HEADER.size

            def readStr():
                nonlocal offset
                end = data.find(b"\0", offset)
                if end < 0:
                    end = len(data)
                value = data[offset:end].decode("utf-8", errors="replace")
                offset = end + 1
                return value

            filename = readStr()
            label = readStr()
            if ptype == PLUGIN_NONE:
                break
            favlist.append({"type": ptype, "uniqueId": uniqueId, "filename": filename, "label": label})
        return favlist

    @staticmethod
    def _favoriteFromInfo(info):
        return {
            "type": int(info["type"]),
            "uniqueId": int(info["uniqueId"]),
            "filename": info["filename"],
            "label": info["label"],
        }

    def _isFavorite(self, info):
        fav = self._favoriteFromInfo(info)
        return fav in self.favorites

    # ----------------------------------------------------------------------------------------------------
    # plugin containers

    def _pluginsAdd(self, info):
        pinfo = info
        ptype = pinfo["type"]

        if ptype == PLUGIN_INTERNAL:
            vec = self._plugins["internal"]
        elif ptype == PLUGIN_LADSPA:
            vec = self._plugins["ladspa"]
        elif ptype == PLUGIN_DSSI:
            vec = self._plugins["dssi"]
        elif ptype == PLUGIN_LV2:
            vec = self._plugins["lv2"]
        elif ptype == PLUGIN_VST2:
            vec = self._plugins["vst2"]
        elif ptype == PLUGIN_VST3:
            vec = self._plugins["vst3"]
        elif ptype == PLUGIN_CLAP:
            vec = self._plugins["clap"]
        elif ptype == PLUGIN_AU:
            vec = self._plugins["au"]
        elif ptype == PLUGIN_JSFX:
            vec = self._plugins["jsfx"]
        elif ptype in (PLUGIN_SF2, PLUGIN_SFZ):
            vec = self._plugins["kits"]
        else:
            return False

        for existing in vec:
            if (existing["filename"] == pinfo["filename"]
                    and existing["uniqueId"] == pinfo["uniqueId"]
                    and existing["name"] == pinfo["name"]):
                return False

        vec.append(pinfo)
        return True

    # ----------------------------------------------------------------------------------------------------
    # discovery

    def _libraryFolder(self):
        try:
            folder = get_library_folder()
        except Exception:
            folder = ""
        if not folder:
            try:
                from carla_shared import gCarla
                folder = os.path.dirname(gCarla.utils.lib._name)
            except Exception:
                folder = ""
        return folder or ""

    def _restartDiscoveryTool(self):
        d = self._discovery
        d["btype"] = BINARY_NATIVE
        d["ptype"] = PLUGIN_NONE
        tool = os.path.join(self._libraryFolder(), "carla-discovery-native")
        if CARLA_OS_WIN:
            tool += ".exe"
        d["tool"] = tool

    def _formatEnabled(self, name):
        r = self._refreshDialog
        if r is None:
            return True
        if not r.group_formats.isVisible():
            return True
        return getattr(r, "ch_" + name).isChecked()

    def _orderedCandidates(self):
        d = self._discovery
        btype = d["btype"]
        paths = self.paths
        isNative = btype == BINARY_NATIVE

        candidates = [
            (PLUGIN_INTERNAL, "", self.tr("internal plugins"), isNative),
            (PLUGIN_LADSPA, paths.get(PLUGIN_LADSPA, ""), self.tr("LADSPA plugins"),
             self._formatEnabled("ladspa")),
            (PLUGIN_DSSI, paths.get(PLUGIN_DSSI, ""), self.tr("DSSI plugins"),
             self._formatEnabled("dssi")),
            (PLUGIN_LV2, paths.get(PLUGIN_LV2, ""), self.tr("LV2 plugins"),
             isNative and bool(paths.get(PLUGIN_LV2, "")) and self._formatEnabled("lv2")),
            (PLUGIN_VST2, paths.get(PLUGIN_VST2, ""), self.tr("VST2 plugins"),
             self._formatEnabled("vst2")),
            (PLUGIN_VST3, paths.get(PLUGIN_VST3, ""), self.tr("VST3 plugins"),
             self._formatEnabled("vst3")),
            (PLUGIN_CLAP, paths.get(PLUGIN_CLAP, ""), self.tr("CLAP plugins"),
             self._formatEnabled("clap")),
        ]
        if CARLA_OS_MAC:
            candidates.append((PLUGIN_AU, paths.get(PLUGIN_AU, ""), self.tr("AU plugins"),
                               self._formatEnabled("au")))
        candidates += [
            (PLUGIN_JSFX, paths.get(PLUGIN_JSFX, ""), self.tr("JSFX plugins"),
             isNative and bool(paths.get(PLUGIN_JSFX, "")) and self._formatEnabled("jsfx")),
            (PLUGIN_SF2, paths.get(PLUGIN_SF2, ""), self.tr("SF2 kits"),
             isNative and bool(paths.get(PLUGIN_SF2, "")) and self._formatEnabled("sf2")),
            (PLUGIN_SFZ, paths.get(PLUGIN_SFZ, ""), self.tr("SFZ kits"),
             isNative and bool(paths.get(PLUGIN_SFZ, "")) and self._formatEnabled("sfz")),
        ]
        return candidates

    def _discoveryPickNext(self):
        d = self._discovery
        candidates = self._orderedCandidates()

        start = 0
        if d["ptype"] != PLUGIN_NONE:
            for i, (ptype, _p, _t, _ok) in enumerate(candidates):
                if ptype == d["ptype"]:
                    start = i + 1
                    break

        for i in range(start, len(candidates)):
            ptype, path, text, ok = candidates[i]
            if ok:
                return ptype, path, text

        # exhausted this tool, try the next bridge tool if allowed
        if self._nextTool():
            return self._discoveryPickNext()

        return None

    def _nextTool(self):
        d = self._discovery

        if d["handle"] is not None:
            d["handle"].stop()
            d["handle"] = None

        if not d["usePluginBridges"]:
            return False

        folder = self._libraryFolder()

        if not CARLA_OS_WIN:
            if not CARLA_OS_MAC and d["btype"] == BINARY_NATIVE:
                d["btype"] = BINARY_POSIX32
                d["ptype"] = PLUGIN_NONE
                d["tool"] = os.path.join(folder, "carla-discovery-posix32")
                if os.path.isfile(d["tool"]):
                    return True

            if not d["useWineBridges"]:
                return False

            if CARLA_OS_64BIT and d["btype"] in (BINARY_NATIVE, BINARY_POSIX32):
                d["btype"] = BINARY_WIN64
                d["ptype"] = PLUGIN_NONE
                d["tool"] = os.path.join(folder, "carla-discovery-win64.exe")
                if os.path.isfile(d["tool"]):
                    return True

            if d["btype"] != BINARY_WIN32:
                d["btype"] = BINARY_WIN32
                d["ptype"] = PLUGIN_NONE
                d["tool"] = os.path.join(folder, "carla-discovery-win32.exe")
                if os.path.isfile(d["tool"]):
                    return True

            return False

        # Windows host build
        if CARLA_OS_64BIT and d["btype"] == BINARY_NATIVE:
            d["btype"] = BINARY_WIN32
            d["ptype"] = PLUGIN_NONE
            d["tool"] = os.path.join(folder, "carla-discovery-win32.exe")
            if os.path.isfile(d["tool"]):
                return True

        return False

    def _discoveryStep(self):
        d = self._discovery

        if d["handle"] is not None:
            if not d["handle"].idle():
                d["handle"].stop()
                d["handle"] = None
            return

        pick = self._discoveryPickNext()
        if pick is None:
            self._refreshPluginsStop()
            return

        ptype, path, text = pick
        d["ptype"] = ptype
        self.label.setText(text)
        if self._refreshDialog is not None:
            self._refreshDialog.progressBar.setFormat(text)

        runner = PluginDiscovery(self._addPluginInfo, self._checkPluginCache)
        d["handle"] = runner
        runner.start(d["tool"], d["btype"], ptype, path)

    # ----------------------------------------------------------------------------------------------------
    # discovery callbacks

    def _addPluginInfo(self, info, sha1sum):
        if info is None:
            if sha1sum is not None:
                settings = _newSettings()
                settings.setValue("PluginCache/%s" % sha1sum, QByteArray())
                self.cache[sha1sum] = []
            return

        pinfo = {
            "build": int(info["btype"]),
            "type": int(info["ptype"]),
            "hints": int(info["metadata"]["hints"]),
            "uniqueId": int(info["uniqueId"]),
            "audioIns": int(info["io"]["audioIns"]),
            "audioOuts": int(info["io"]["audioOuts"]),
            "cvIns": int(info["io"]["cvIns"]),
            "cvOuts": int(info["io"]["cvOuts"]),
            "midiIns": int(info["io"]["midiIns"]),
            "midiOuts": int(info["io"]["midiOuts"]),
            "parameterIns": int(info["io"]["parameterIns"]),
            "parameterOuts": int(info["io"]["parameterOuts"]),
            "category": getPluginCategoryAsString(int(info["metadata"]["category"])),
            "filename": info["filename"] or "",
            "name": info["metadata"]["name"] or "",
            "label": info["label"] or "",
            "maker": info["metadata"]["maker"] or "",
        }

        if sha1sum is not None:
            settings = _newSettings()
            key = "PluginCache/%s" % sha1sum
            if sha1sum in self.cache:
                data = _getBytes(settings, key)
            else:
                data = b""
            data += _infoToBytes(pinfo)
            settings.setValue(key, QByteArray(data))
            self.cache.setdefault(sha1sum, []).append(pinfo)

        self._pluginsAdd(pinfo)

    def _checkPluginCache(self, filename, sha1sum):
        if filename and self._refreshDialog is not None:
            self._refreshDialog.progressBar.setFormat(filename)

        if sha1sum not in self.cache:
            return False

        plist = self.cache[sha1sum]
        if not plist:
            return self._discovery["ignoreCache"] or not self._discovery["checkInvalid"]

        if not filename or plist[0]["filename"] != filename:
            self.cache.pop(sha1sum, None)
            return False

        for info in plist:
            self._pluginsAdd(info)
        return True

    # ----------------------------------------------------------------------------------------------------
    # scanner & live discovery

    def _connectScanner(self, scanner):
        try:
            scanner.pluginDiscovered.disconnect(self._onScannerPluginDiscovered)
        except Exception:
            pass
        try:
            scanner.statusChanged.disconnect(self._onScannerStatusChanged)
        except Exception:
            pass
        try:
            scanner.fileChanged.disconnect(self._onScannerFileChanged)
        except Exception:
            pass
        try:
            scanner.scanFinished.disconnect(self._onScannerFinished)
        except Exception:
            pass

        scanner.pluginDiscovered.connect(self._onScannerPluginDiscovered)
        scanner.statusChanged.connect(self._onScannerStatusChanged)
        scanner.fileChanged.connect(self._onScannerFileChanged)
        scanner.scanFinished.connect(self._onScannerFinished)

    def _startScan(self, ignoreCache=False):
        from pluginlist.startup_scanner import getGlobalScanner
        scanner = getGlobalScanner()
        if scanner.isRunning():
            return

        if ignoreCache:
            self.table.setRowCount(0)
            self.list_rack.clear()
            self.list_cards.clear()
            self._lastTableWidgetIndex = 0
            self._rowPluginData.clear()
            self._plugins = {k: [] for k in self._plugins}
            self.cache.clear()
            _newSettings().remove("PluginCache")

        scanner.configure(paths=self.paths, ignoreCache=ignoreCache, checkInvalid=ignoreCache)
        self._connectScanner(scanner)
        self.scanStatusLabel.setText(self.tr("Starting discovery..."))
        self.scanBar.show()
        self.b_refresh.setEnabled(False)
        self.b_refresh_full.setEnabled(False)
        scanner.start()

    def _stopScan(self):
        from pluginlist.startup_scanner import getGlobalScanner
        scanner = getGlobalScanner()
        if scanner.isRunning():
            scanner.requestStop()
        self.scanStatusLabel.setText(self.tr("Scan stopped"))
        self.scanBar.hide()
        self.b_refresh.setEnabled(True)
        self.b_refresh_full.setEnabled(True)

    def _onScannerStatusChanged(self, status):
        self.scanStatusLabel.setText(status)

    def _onScannerFileChanged(self, filename):
        if filename:
            self.scanStatusLabel.setText(f"Scanning: {filename}")

    def _onScannerFinished(self, count):
        self.scanBar.hide()
        self.b_refresh.setEnabled(True)
        self.b_refresh_full.setEnabled(True)
        # Rebuild so plugins discovered during the scan land in the active sort order
        # consistently across the table, rack and cards views.
        self._addPluginsToTable()

    def _onScannerPluginDiscovered(self, pinfo, sha1):
        if not self._pluginsAdd(pinfo):
            return
        self._streamPluginToTable(pinfo)

    def _streamPluginToTable(self, info):
        # Append in discovery order while scanning (all views stay index-aligned); the full
        # sorted rebuild happens once the scan finishes.
        row = self.table.rowCount()
        self.table.insertRow(row)
        self._lastTableWidgetIndex = row
        self._addPluginToTable(info, isStream=True)
        self._filterSingleRow(row)
        self._updatePluginsSummaryLabel()

    def _updatePluginsSummaryLabel(self):
        self.label.setText(
            self.tr("Have %1 Internal, %2 LADSPA, %3 DSSI, %4 LV2, %5 VST2, %6 VST3, %7 CLAP and %8 JSFX plugins, plus %9 Sound Kits")
            .replace("%1", str(len(self._plugins["internal"])))
            .replace("%2", str(len(self._plugins["ladspa"])))
            .replace("%3", str(len(self._plugins["dssi"])))
            .replace("%4", str(len(self._plugins["lv2"])))
            .replace("%5", str(len(self._plugins["vst2"])))
            .replace("%6", str(len(self._plugins["vst3"])))
            .replace("%7", str(len(self._plugins["clap"])))
            .replace("%8", str(len(self._plugins["jsfx"])))
            .replace("%9", str(len(self._plugins["kits"])))
        )

    # ----------------------------------------------------------------------------------------------------
    # table

    def _addPluginsToTable(self):
        self.table.setSortingEnabled(False)
        self.table.clearContents()
        self.list_rack.clear()
        self.list_cards.clear()
        self._rowPluginData.clear()

        order = ["internal", "ladspa", "dssi", "lv2", "vst2", "vst3", "clap", "au", "jsfx", "kits"]
        infos = []
        for key in order:
            infos.extend(self._plugins[key])
        infos = self._sortInfos(infos)

        self.table.setRowCount(len(infos))

        self._lastTableWidgetIndex = 0
        for info in infos:
            self._addPluginToTable(info, isStream=False)

        # Pre-instantiate visible rows immediately for current mode only
        self._ensureVisibleWidgets()

        self._updatePluginsSummaryLabel()
        self.table.setSortingEnabled(False)

        self._checkFilters()
        self._ensureVisibleWidgets()
        self._checkPlugin(self.table.currentRow())

    def _sortInfos(self, infos):
        column = getattr(self, "_sortColumn", TW_NAME)
        reverse = getattr(self, "_sortOrder", Qt.AscendingOrder) == Qt.DescendingOrder

        def key(info):
            name = (info.get("name") or "").lower()
            if column == TW_LABEL:
                return ((info.get("label") or "").lower(), name)
            if column == TW_MAKER:
                return ((info.get("maker") or "").lower(), name)
            if column == TW_BINARY:
                return (os.path.basename(info.get("filename") or "").lower(), name)
            if column == TW_FAVORITE:
                return (0 if self._isFavorite(info) else 1, name)
            return (name, (info.get("label") or "").lower())

        return sorted(infos, key=key, reverse=reverse)

    def _onHeaderClicked(self, column):
        if column < 0 or column >= _TABLE_COLUMNS:
            return
        if column == self._sortColumn:
            self._sortOrder = (
                Qt.DescendingOrder if self._sortOrder == Qt.AscendingOrder else Qt.AscendingOrder
            )
        else:
            self._sortColumn = column
            self._sortOrder = Qt.AscendingOrder
        self.table.horizontalHeader().setSortIndicator(self._sortColumn, self._sortOrder)
        self._addPluginsToTable()

    def _cacheRowData(self, index, info, pluginText=None):
        if pluginText is None:
            pluginText = (info["name"] + " " + info["label"] + " " + info["maker"] + " " + info["filename"]).lower()

        if CARLA_OS_WIN:
            nativeBins = (BINARY_WIN32, BINARY_WIN64) if CARLA_OS_64BIT else (BINARY_WIN32, BINARY_NONE)
            wineBins = (BINARY_NONE, BINARY_NONE)
        elif CARLA_OS_MAC:
            nativeBins = (BINARY_POSIX64, BINARY_NONE)
            wineBins = (BINARY_WIN32, BINARY_WIN64)
        else:
            nativeBins = (BINARY_POSIX32, BINARY_POSIX64)
            wineBins = (BINARY_WIN32, BINARY_WIN64)

        aIns = info["audioIns"]
        aOuts = info["audioOuts"]
        cvIns = info["cvIns"]
        cvOuts = info["cvOuts"]
        mIns = info["midiIns"]
        mOuts = info["midiOuts"]
        phints = info["hints"]
        ptype = info["type"]
        categ = (info.get("category") or "").lower()

        isSynth = bool(phints & PLUGIN_IS_SYNTH)
        isEffect = aIns > 0 and aOuts > 0 and not isSynth
        isMidi = aIns == 0 and aOuts == 0 and mIns > 0 and mOuts > 0
        isKit = ptype in (PLUGIN_SF2, PLUGIN_SFZ)
        isOther = not (isEffect or isSynth or isMidi or isKit)
        isNative = info["build"] == BINARY_NATIVE
        isRtSafe = bool(phints & PLUGIN_IS_RTSAFE)
        isStereo = (aIns == 2 and aOuts == 2) or (isSynth and aOuts == 2)
        hasCV = cvIns + cvOuts > 0
        hasGui = bool(phints & PLUGIN_HAS_CUSTOM_UI)
        hasIDisp = bool(phints & PLUGIN_HAS_INLINE_DISPLAY)
        isBridged = (not isNative) and (info["build"] in nativeBins)
        isBridgedWine = (not isNative) and (info["build"] in wineBins)

        data = {
            "info": info,
            "text": pluginText,
            "isEffect": isEffect,
            "isSynth": isSynth,
            "isMidi": isMidi,
            "isKit": isKit,
            "isOther": isOther,
            "isNative": isNative,
            "isRtSafe": isRtSafe,
            "isStereo": isStereo,
            "hasCV": hasCV,
            "hasGui": hasGui,
            "hasIDisp": hasIDisp,
            "isBridged": isBridged,
            "isBridgedWine": isBridgedWine,
            "type": ptype,
            "category": categ,
        }
        self._rowPluginData[index] = data
        return data

    def _ensureVisibleWidgets(self):
        curr_mode = self.stackCenter.currentIndex()
        if curr_mode == 0:
            count = self.list_rack.count()
            found = 0
            for r in range(count):
                if not self.list_rack.isRowHidden(r):
                    self._ensureRackWidget(r)
                    found += 1
                    if found >= 40:
                        break
        elif curr_mode == 1:
            count = self.list_cards.count()
            found = 0
            for r in range(count):
                if not self.list_cards.isRowHidden(r):
                    self._ensureCardWidget(r)
                    found += 1
                    if found >= 40:
                        break

    def _ensureRackWidget(self, row):
        if row < 0 or row >= self.list_rack.count():
            return None
        item = self.list_rack.item(row)
        if item is None:
            return None
        w = self.list_rack.itemWidget(item)
        if w is not None:
            return w
        row_data = self._rowPluginData.get(row)
        if not row_data:
            return None
        info = row_data["info"]
        isFav = self._isFavorite(info)
        rackWidget = RackPluginItemWidget(info, isFav, self.list_rack)
        rackWidget.lbl_star.mousePressEvent = lambda _ev, r=row: self._cellClicked(r, TW_FAVORITE)
        self.list_rack.setItemWidget(item, rackWidget)
        return rackWidget

    def _ensureCardWidget(self, row):
        if row < 0 or row >= self.list_cards.count():
            return None
        item = self.list_cards.item(row)
        if item is None:
            return None
        w = self.list_cards.itemWidget(item)
        if w is not None:
            return w
        row_data = self._rowPluginData.get(row)
        if not row_data:
            return None
        info = row_data["info"]
        isFav = self._isFavorite(info)
        cardWidget = CardPluginItemWidget(info, isFav, self.list_cards)
        cardWidget.lbl_star.mousePressEvent = lambda _ev, r=row: self._cellClicked(r, TW_FAVORITE)
        self.list_cards.setItemWidget(item, cardWidget)
        return cardWidget

    def _streamNextChunk(self):
        if self._lazyIndex >= self._lazyTotal:
            self._lazyTimer.stop()
            return
        end = min(self._lazyTotal, self._lazyIndex + 50)
        curr_mode = self.stackCenter.currentIndex()
        if curr_mode == 0:
            for r in range(self._lazyIndex, end):
                self._ensureRackWidget(r)
        elif curr_mode == 1:
            for r in range(self._lazyIndex, end):
                self._ensureCardWidget(r)
        self._lazyIndex = end
        if self._lazyIndex >= self._lazyTotal:
            self._lazyTimer.stop()

    def _onRackScroll(self):
        count = self.list_rack.count()
        if count == 0:
            return
        sb = self.list_rack.verticalScrollBar()
        first = max(0, (sb.value() // 44) - 5)
        visible_count = max(25, (self.list_rack.viewport().height() // 44) + 15)
        last = min(count, first + visible_count)
        for r in range(first, last):
            self._ensureRackWidget(r)

    def _onCardsScroll(self):
        vp = self.list_cards.viewport()
        w_vp = vp.width()
        h_vp = vp.height()
        if w_vp <= 0 or h_vp <= 0:
            return
        # Scan visible grid points inside the viewport to identify visible items
        visible_rows = set()
        for y in range(0, h_vp + 60, 60):
            for x in range(10, w_vp, 100):
                idx = self.list_cards.indexAt(QPoint(x, y))
                if idx.isValid():
                    visible_rows.add(idx.row())
        for r in visible_rows:
            self._ensureCardWidget(r)

    def _addPluginToTable(self, info, isStream=False):
        index = self._lastTableWidgetIndex
        self._lastTableWidgetIndex += 1

        isFav = self._isFavorite(info)

        itemFav = QTableWidgetItem("★" if isFav else "☆")
        itemFav.setTextAlignment(Qt.AlignCenter)
        itemFav.setForeground(QColor("#eed49f" if isFav else "#6e738d"))
        self.table.setItem(index, TW_FAVORITE, itemFav)

        self.table.setItem(index, TW_NAME, QTableWidgetItem(info["name"]))
        self.table.setItem(index, TW_LABEL, QTableWidgetItem(info["label"]))
        self.table.setItem(index, TW_MAKER, QTableWidgetItem(info["maker"]))
        self.table.setItem(index, TW_BINARY, QTableWidgetItem(os.path.basename(info["filename"])))

        pluginText = (info["name"] + " " + info["label"] + " " + info["maker"] + " " + info["filename"]).lower()

        itemName = self.table.item(index, TW_NAME)
        itemName.setData(int(Qt.UserRole) + UR_PLUGIN_INFO, QByteArray(_infoToBytes(info)))
        itemName.setData(int(Qt.UserRole) + UR_SEARCH_TEXT, pluginText)

        data = self._cacheRowData(index, info, pluginText)
        itemName.setData(int(Qt.UserRole) + 50, data)

        # Rack Item placeholder
        rackItem = QListWidgetItem()
        rackItem.setSizeHint(QSize(0, 48))
        if index < self.list_rack.count():
            self.list_rack.insertItem(index, rackItem)
        else:
            self.list_rack.addItem(rackItem)

        # Cards Item placeholder
        cardItem = QListWidgetItem()
        cardItem.setSizeHint(QSize(195, 120))
        if index < self.list_cards.count():
            self.list_cards.insertItem(index, cardItem)
        else:
            self.list_cards.addItem(cardItem)

        if isStream:
            curr_mode = self.stackCenter.currentIndex()
            if curr_mode == 0:
                self._ensureRackWidget(index)
            elif curr_mode == 1:
                self._ensureCardWidget(index)
            else:
                self._ensureRackWidget(index)

    # ----------------------------------------------------------------------------------------------------
    # slots

    def _cycleViewMode(self):
        next_mode = (self.stackCenter.currentIndex() + 1) % 3
        self._setViewMode(next_mode)

    def _setViewMode(self, mode):
        mode = mode % 3
        self.stackCenter.setCurrentIndex(mode)

        mode_meta = [
            ("☲ " + self.tr("Rack"), self.tr("Current view: Rack (click to switch to Cards)")),
            ("▦ " + self.tr("Cards"), self.tr("Current view: Cards (click to switch to Table)")),
            ("☰ " + self.tr("Table"), self.tr("Current view: Table (click to switch to Rack)")),
        ]
        label, tooltip = mode_meta[mode]
        self.btn_view_mode.setText(label)
        self.btn_view_mode.setToolTip(tooltip)

        cur_row = self.table.currentRow()
        if cur_row >= 0:
            if mode == 0 and cur_row < self.list_rack.count():
                self.list_rack.setCurrentRow(cur_row)
            elif mode == 1 and cur_row < self.list_cards.count():
                self.list_cards.setCurrentRow(cur_row)

        self._syncViewModeVisibility(mode)

        if mode == 0:
            self._onRackScroll()
        elif mode == 1:
            self._onCardsScroll()

        self._ensureVisibleWidgets()
        self._updateSelectionState()

    def _onRackCurrentItemChanged(self, current, previous):
        if not current:
            return
        row = self.list_rack.row(current)
        if row >= 0:
            if self.table.currentRow() != row:
                self.table.blockSignals(True)
                self.table.setCurrentCell(row, TW_NAME)
                self.table.blockSignals(False)
            self._checkPlugin(row)
            self._updateSelectionState()

    def _onCardsCurrentItemChanged(self, current, previous):
        if not current:
            return
        row = self.list_cards.row(current)
        if row >= 0:
            if self.table.currentRow() != row:
                self.table.blockSignals(True)
                self.table.setCurrentCell(row, TW_NAME)
                self.table.blockSignals(False)
            self._checkPlugin(row)
            self._updateSelectionState()

    def _onTableCurrentCellChanged(self, r, c, pr, pc):
        self._checkPlugin(r)
        if r >= 0:
            if r < self.list_rack.count() and self.list_rack.currentRow() != r:
                self.list_rack.blockSignals(True)
                self.list_rack.setCurrentRow(r)
                self.list_rack.blockSignals(False)
            if r < self.list_cards.count() and self.list_cards.currentRow() != r:
                self.list_cards.blockSignals(True)
                self.list_cards.setCurrentRow(r)
                self.list_cards.blockSignals(False)

    def _onListSelectionChanged(self):
        self._updateSelectionState()

    def _hideRow(self, row):
        self.table.hideRow(row)
        if row < self.list_rack.count():
            self.list_rack.setRowHidden(row, True)
        if row < self.list_cards.count():
            self.list_cards.setRowHidden(row, True)

    def _showRow(self, row):
        self.table.showRow(row)
        if row < self.list_rack.count():
            self.list_rack.setRowHidden(row, False)
        if row < self.list_cards.count():
            self.list_cards.setRowHidden(row, False)

    def _syncViewModeVisibility(self, mode):
        if mode == 0:
            self.list_rack.setUpdatesEnabled(False)
            try:
                for r in range(self.table.rowCount()):
                    self.list_rack.setRowHidden(r, self.table.isRowHidden(r))
            finally:
                self.list_rack.setUpdatesEnabled(True)
        elif mode == 1:
            self.list_cards.setUpdatesEnabled(False)
            try:
                for r in range(self.table.rowCount()):
                    self.list_cards.setRowHidden(r, self.table.isRowHidden(r))
            finally:
                self.list_cards.setUpdatesEnabled(True)

    def _updateSelectionState(self):
        curr_mode = self.stackCenter.currentIndex()

        # Update rack widgets selection highlight
        selected_rack_items = self.list_rack.selectedItems() if curr_mode == 0 else []
        if curr_mode == 0 and not selected_rack_items and self.list_rack.currentItem():
            selected_rack_items = [self.list_rack.currentItem()]
        old_rack = getattr(self, "_selected_rack_widgets", set())
        new_rack = set()
        for it in selected_rack_items:
            w = self.list_rack.itemWidget(it) or self._ensureRackWidget(self.list_rack.row(it))
            if w and hasattr(w, "setSelected"):
                new_rack.add(w)
        for w in old_rack - new_rack:
            w.setSelected(False)
        for w in new_rack - old_rack:
            w.setSelected(True)
        self._selected_rack_widgets = new_rack

        # Update cards widgets selection highlight
        selected_cards_items = self.list_cards.selectedItems() if curr_mode == 1 else []
        if curr_mode == 1 and not selected_cards_items and self.list_cards.currentItem():
            selected_cards_items = [self.list_cards.currentItem()]
        old_cards = getattr(self, "_selected_cards_widgets", set())
        new_cards = set()
        for it in selected_cards_items:
            w = self.list_cards.itemWidget(it) or self._ensureCardWidget(self.list_cards.row(it))
            if w and hasattr(w, "setSelected"):
                new_cards.add(w)
        for w in old_cards - new_cards:
            w.setSelected(False)
        for w in new_cards - old_cards:
            w.setSelected(True)
        self._selected_cards_widgets = new_cards

        if curr_mode == 0:
            selected_rows = set(self.list_rack.row(it) for it in self.list_rack.selectedItems())
            cur = self.list_rack.currentRow()
        elif curr_mode == 1:
            selected_rows = set(self.list_cards.row(it) for it in self.list_cards.selectedItems())
            cur = self.list_cards.currentRow()
        else:
            selected_rows = set(idx.row() for idx in self.table.selectedIndexes())
            cur = self.table.currentRow()

        count = len(selected_rows)
        if count == 0:
            self.b_add.setText(self.tr("&Add Plugin"))
            self.b_add.setEnabled(cur >= 0)
        elif count == 1:
            self.b_add.setText(self.tr("&Add Plugin"))
            self.b_add.setEnabled(True)
        else:
            self.b_add.setText(self.tr("&Add Selected (%1)").replace("%1", str(count)))
            self.b_add.setEnabled(True)

    def _slotAddClicked(self):
        curr_mode = self.stackCenter.currentIndex()
        if curr_mode == 0:
            selected_rows = sorted(set(self.list_rack.row(it) for it in self.list_rack.selectedItems()))
            if not selected_rows and self.list_rack.currentRow() >= 0:
                selected_rows = [self.list_rack.currentRow()]
        elif curr_mode == 1:
            selected_rows = sorted(set(self.list_cards.row(it) for it in self.list_cards.selectedItems()))
            if not selected_rows and self.list_cards.currentRow() >= 0:
                selected_rows = [self.list_cards.currentRow()]
        else:
            selected_rows = sorted(set(idx.row() for idx in self.table.selectedIndexes()))
            if not selected_rows and self.table.currentRow() >= 0:
                selected_rows = [self.table.currentRow()]

        if not selected_rows:
            return

        added_infos = []
        bridgeOption = self.c_bridge_mode.currentData()
        for row in selected_rows:
            item = self.table.item(row, TW_NAME)
            if item is None:
                continue
            data = item.data(int(Qt.UserRole) + 50)
            info = data["info"] if isinstance(data, dict) else None
            if not info:
                raw = item.data(int(Qt.UserRole) + UR_PLUGIN_INFO)
                if raw is not None:
                    info, _ = _bytesToInfo(bytes(raw) if isinstance(raw, QByteArray) else bytes(raw))
            if info:
                info = dict(info)
                info["__bridgeOption"] = bridgeOption
                added_infos.append(info)
                self.pluginAddRequested.emit(info)

        if added_infos:
            self.retPlugin = added_infos[-1]
            names = ", ".join(i["name"] for i in added_infos[:3])
            if len(added_infos) > 3:
                names += f" (+{len(added_infos)-3} more)"
            self.label.setText(self.tr("Loaded %1").replace("%1", names))

        if not self.ch_keep_open.isChecked():
            self.accept()

    def _cellClicked(self, row, column):
        if column != TW_FAVORITE:
            return

        item = self.table.item(row, TW_NAME)
        if item is None:
            return
        data = item.data(int(Qt.UserRole) + UR_PLUGIN_INFO)
        info, _ = _bytesToInfo(bytes(data)) if data is not None else (None, 0)
        if info is None:
            return

        fav = self._favoriteFromInfo(info)
        isFavorite = fav in self.favorites

        # Toggle favorite
        itemFav = self.table.item(row, TW_FAVORITE)
        newFav = not isFavorite
        if itemFav:
            self.table.blockSignals(True)
            itemFav.setText("★" if newFav else "☆")
            itemFav.setForeground(QColor("#eed49f" if newFav else "#6e738d"))
            self.table.blockSignals(False)

        if newFav and not isFavorite:
            self.favorites.append(fav)
        elif not newFav and isFavorite:
            self.favorites = [f for f in self.favorites if f != fav]

        # Update rack and cards star widgets
        if 0 <= row < self.list_rack.count():
            w_r = self.list_rack.itemWidget(self.list_rack.item(row))
            if w_r and hasattr(w_r, "setFavorite"):
                w_r.setFavorite(newFav)
        if 0 <= row < self.list_cards.count():
            w_c = self.list_cards.itemWidget(self.list_cards.item(row))
            if w_c and hasattr(w_c, "setFavorite"):
                w_c.setFavorite(newFav)

        settings = _newSettings()
        settings.setValue("PluginListDialog/Favorites", self._favoritesToBytes(self.favorites))

        if self.ch_favorites.isChecked():
            self._checkFilters()

    def _cellDoubleClicked(self, _row, column):
        if column != TW_FAVORITE:
            self._slotAddClicked()

    def focusSearchFieldAndSelectAll(self):
        self.lineEdit.setFocus()
        self.lineEdit.selectAll()

    def _filterSingleRow(self, row):
        item = self.table.item(row, TW_NAME)
        if item is None:
            return
        data = item.data(int(Qt.UserRole) + 50)
        if not data:
            raw = item.data(int(Qt.UserRole) + UR_PLUGIN_INFO)
            info, _ = _bytesToInfo(bytes(raw)) if raw else (None, 0)
            if not info:
                return
            data = self._cacheRowData(row, info)
            item.setData(int(Qt.UserRole) + 50, data)

        text = self.lineEdit.text().lower().strip()
        tokens = [t for t in text.split() if t]
        if tokens and not all(tok in data["text"] for tok in tokens):
            self._hideRow(row)
            return

        # Format (OR within group, bypassed if [All] is active)
        if not self.group_format.isAllChecked():
            fmt_match = False
            t = data["type"]
            if self.ch_clap.isChecked() and t == PLUGIN_CLAP:
                fmt_match = True
            elif self.ch_vst3.isChecked() and t == PLUGIN_VST3:
                fmt_match = True
            elif self.ch_lv2.isChecked() and t == PLUGIN_LV2:
                fmt_match = True
            elif self.ch_vst.isChecked() and t == PLUGIN_VST2:
                fmt_match = True
            elif self.ch_jsfx.isChecked() and t == PLUGIN_JSFX:
                fmt_match = True
            elif self.ch_internal.isChecked() and t == PLUGIN_INTERNAL:
                fmt_match = True
            elif self.ch_ladspa.isChecked() and t == PLUGIN_LADSPA:
                fmt_match = True
            elif self.ch_dssi.isChecked() and t == PLUGIN_DSSI:
                fmt_match = True
            elif self.ch_kits.isChecked() and data["isKit"]:
                fmt_match = True
            elif self.ch_au.isChecked() and t == PLUGIN_AU:
                fmt_match = True
            if not fmt_match:
                self._hideRow(row)
                return

        # Type (OR within group, bypassed if [All] is active)
        if not self.group_type.isAllChecked():
            type_match = False
            if self.ch_instruments.isChecked() and data["isSynth"]:
                type_match = True
            elif self.ch_effects.isChecked() and data["isEffect"]:
                type_match = True
            elif self.ch_midi.isChecked() and data["isMidi"]:
                type_match = True
            elif self.ch_other.isChecked() and data["isOther"]:
                type_match = True
            if not type_match:
                self._hideRow(row)
                return

        # Architecture (OR within group, bypassed if [All] is active)
        if not self.group_arch.isAllChecked():
            arch_match = False
            if self.ch_native.isChecked() and data["isNative"]:
                arch_match = True
            elif self.ch_bridged.isChecked() and data["isBridged"]:
                arch_match = True
            elif self.ch_bridged_wine.isChecked() and data["isBridgedWine"]:
                arch_match = True
            if not arch_match:
                self._hideRow(row)
                return

        # Requirements (AND: must satisfy all checked requirements)
        if not self.group_req.isAllChecked():
            if self.ch_rtsafe.isChecked() and not data["isRtSafe"]:
                self._hideRow(row)
                return
            if self.ch_cv.isChecked() and not data["hasCV"]:
                self._hideRow(row)
                return
            if self.ch_gui.isChecked() and not data["hasGui"]:
                self._hideRow(row)
                return
            if self.ch_inline_display.isChecked() and not data["hasIDisp"]:
                self._hideRow(row)
                return
            if self.ch_stereo.isChecked() and not data["isStereo"]:
                self._hideRow(row)
                return

        # Favorites
        if self.ch_favorites.isChecked() and not self._isFavorite(data["info"]):
            self._hideRow(row)
            return

        # Category (OR within group, bypassed if [All] is active)
        if not self.group_cat.isAllChecked():
            categ = data["category"]
            cat_match = (
                (self.ch_cat_delay.isChecked() and categ == "delay")
                or (self.ch_cat_distortion.isChecked() and categ == "distortion")
                or (self.ch_cat_dynamics.isChecked() and categ == "dynamics")
                or (self.ch_cat_eq.isChecked() and categ == "eq")
                or (self.ch_cat_filter.isChecked() and categ == "filter")
                or (self.ch_cat_modulator.isChecked() and categ == "modulator")
                or (self.ch_cat_synth.isChecked() and categ == "synth")
                or (self.ch_cat_utility.isChecked() and categ == "utility")
                or (self.ch_cat_other.isChecked() and categ == "other")
            )
            if not cat_match:
                self._hideRow(row)
                return

        self._showRow(row)

    def _checkFilters(self):
        text = self.lineEdit.text().lower().strip()
        tokens = [t for t in text.split() if t]

        fmtAll = self.group_format.isAllChecked()
        fmtClap = self.ch_clap.isChecked()
        fmtVst3 = self.ch_vst3.isChecked()
        fmtLv2 = self.ch_lv2.isChecked()
        fmtVst = self.ch_vst.isChecked()
        fmtJsfx = self.ch_jsfx.isChecked()
        fmtInternal = self.ch_internal.isChecked()
        fmtLadspa = self.ch_ladspa.isChecked()
        fmtDssi = self.ch_dssi.isChecked()
        fmtKits = self.ch_kits.isChecked()
        fmtAu = self.ch_au.isChecked()

        typeAll = self.group_type.isAllChecked()
        typeInst = self.ch_instruments.isChecked()
        typeFx = self.ch_effects.isChecked()
        typeMidi = self.ch_midi.isChecked()
        typeOther = self.ch_other.isChecked()

        archAll = self.group_arch.isAllChecked()
        archNative = self.ch_native.isChecked()
        archBridged = self.ch_bridged.isChecked()
        archWine = self.ch_bridged_wine.isChecked()

        reqAll = self.group_req.isAllChecked()
        reqRt = self.ch_rtsafe.isChecked()
        reqCv = self.ch_cv.isChecked()
        reqGui = self.ch_gui.isChecked()
        reqIdisp = self.ch_inline_display.isChecked()
        reqStereo = self.ch_stereo.isChecked()

        favOnly = self.ch_favorites.isChecked()

        catAll = self.group_cat.isAllChecked()
        catDelay = self.ch_cat_delay.isChecked()
        catDist = self.ch_cat_distortion.isChecked()
        catDyn = self.ch_cat_dynamics.isChecked()
        catEq = self.ch_cat_eq.isChecked()
        catFilt = self.ch_cat_filter.isChecked()
        catMod = self.ch_cat_modulator.isChecked()
        catSynth = self.ch_cat_synth.isChecked()
        catUtil = self.ch_cat_utility.isChecked()
        catOther = self.ch_cat_other.isChecked()

        self.table.setUpdatesEnabled(False)
        self.list_rack.setUpdatesEnabled(False)
        self.list_cards.setUpdatesEnabled(False)
        try:
            for i in range(self.table.rowCount()):
                item = self.table.item(i, TW_NAME)
                if item is None:
                    continue
                data = item.data(int(Qt.UserRole) + 50)
                if not data:
                    raw = item.data(int(Qt.UserRole) + UR_PLUGIN_INFO)
                    info, _ = _bytesToInfo(bytes(raw)) if raw else (None, 0)
                    if not info:
                        self._hideRow(i)
                        continue
                    data = self._cacheRowData(i, info)
                    item.setData(int(Qt.UserRole) + 50, data)

                if tokens and not all(tok in data["text"] for tok in tokens):
                    self._hideRow(i)
                    continue

                if not fmtAll:
                    t = data["type"]
                    if not ((fmtClap and t == PLUGIN_CLAP)
                            or (fmtVst3 and t == PLUGIN_VST3)
                            or (fmtLv2 and t == PLUGIN_LV2)
                            or (fmtVst and t == PLUGIN_VST2)
                            or (fmtJsfx and t == PLUGIN_JSFX)
                            or (fmtInternal and t == PLUGIN_INTERNAL)
                            or (fmtLadspa and t == PLUGIN_LADSPA)
                            or (fmtDssi and t == PLUGIN_DSSI)
                            or (fmtKits and data["isKit"])
                            or (fmtAu and t == PLUGIN_AU)):
                        self._hideRow(i)
                        continue

                if not typeAll:
                    if not ((typeInst and data["isSynth"])
                            or (typeFx and data["isEffect"])
                            or (typeMidi and data["isMidi"])
                            or (typeOther and data["isOther"])):
                        self._hideRow(i)
                        continue

                if not archAll:
                    if not ((archNative and data["isNative"])
                            or (archBridged and data["isBridged"])
                            or (archWine and data["isBridgedWine"])):
                        self._hideRow(i)
                        continue

                if not reqAll:
                    if reqRt and not data["isRtSafe"]:
                        self._hideRow(i)
                        continue
                    if reqCv and not data["hasCV"]:
                        self._hideRow(i)
                        continue
                    if reqGui and not data["hasGui"]:
                        self._hideRow(i)
                        continue
                    if reqIdisp and not data["hasIDisp"]:
                        self._hideRow(i)
                        continue
                    if reqStereo and not data["isStereo"]:
                        self._hideRow(i)
                        continue

                if favOnly and not self._isFavorite(data["info"]):
                    self._hideRow(i)
                    continue

                if not catAll:
                    categ = data["category"]
                    if not ((catDelay and categ == "delay")
                            or (catDist and categ == "distortion")
                            or (catDyn and categ == "dynamics")
                            or (catEq and categ == "eq")
                            or (catFilt and categ == "filter")
                            or (catMod and categ == "modulator")
                            or (catSynth and categ == "synth")
                            or (catUtil and categ == "utility")
                            or (catOther and categ == "other")):
                        self._hideRow(i)
                        continue

                self._showRow(i)
        finally:
            self.table.setUpdatesEnabled(True)
            self.list_rack.setUpdatesEnabled(True)
            self.list_cards.setUpdatesEnabled(True)
            self._ensureVisibleWidgets()

    def _checkFiltersCategoryAll(self, clicked=False):
        self.group_cat.setAll(True)
        self._checkFilters()

    def _checkFiltersCategorySpecific(self, clicked=False):
        self.group_cat.syncFromPills()
        self._checkFilters()

    def _clearFilters(self):
        self.group_format.setAll(True)
        self.group_type.setAll(True)
        self.group_cat.setAll(True)
        self.group_arch.setAll(True)
        self.group_req.setAll(True)

        self.ch_favorites.blockSignals(True)
        self.ch_favorites.setChecked(False)
        self.ch_favorites.blockSignals(False)

        self.lineEdit.blockSignals(True)
        self.lineEdit.clear()
        self.lineEdit.blockSignals(False)

        self._checkFilters()

    def _checkPlugin(self, row):
        if row >= 0:
            self.b_add.setEnabled(True)

            item = self.table.item(row, TW_NAME)
            data = item.data(int(Qt.UserRole) + UR_PLUGIN_INFO) if item is not None else None
            info, _ = _bytesToInfo(bytes(data)) if data is not None else (None, 0)
            if info is None:
                info = {"hints": 0, "audioIns": 0, "audioOuts": 0, "midiIns": 0, "midiOuts": 0,
                        "build": BINARY_NONE, "type": PLUGIN_NONE, "uniqueId": 0, "cvIns": 0, "cvOuts": 0,
                        "parameterIns": 0, "parameterOuts": 0, "name": "", "maker": "", "category": "", "filename": ""}

            isSynth = bool(info["hints"] & PLUGIN_IS_SYNTH)
            isEffect = info["audioIns"] > 0 and info["audioOuts"] > 0 and not isSynth
            isMidi = info["audioIns"] == 0 and info["audioOuts"] == 0 and info["midiIns"] > 0 and info["midiOuts"] > 0

            if isSynth:
                ptypeStr = self.tr("Instrument")
            elif isEffect:
                ptypeStr = self.tr("Effect")
            elif isMidi:
                ptypeStr = self.tr("MIDI Plugin")
            else:
                ptypeStr = self.tr("Other")

            fmtStr = getPluginTypeAsString(info["type"])
            self.l_badge.setText(fmtStr)

            name = info.get("name") or (item.text() if item else "")
            maker = info.get("maker") or "---"
            cat = info.get("category") or ptypeStr
            self.l_name.setText(name)
            self.l_maker.setText(maker)
            self.l_category.setText(f"{cat} • {ptypeStr}" if cat and cat != ptypeStr else cat)

            if info["build"] == BINARY_NATIVE:
                parch = self.tr("Native (64-bit)" if CARLA_OS_64BIT else "Native (32-bit)")
            elif info["build"] == BINARY_POSIX32:
                parch = "POSIX 32-bit"
            elif info["build"] == BINARY_POSIX64:
                parch = "POSIX 64-bit"
            elif info["build"] == BINARY_WIN32:
                parch = "Windows 32-bit"
            elif info["build"] == BINARY_WIN64:
                parch = "Windows 64-bit"
            elif info["build"] == BINARY_OTHER:
                parch = self.tr("Other")
            else:
                parch = self.tr("Unknown")

            isBridged = bool(info["hints"] & PLUGIN_IS_BRIDGE)
            self.l_arch.setText(parch)
            self.l_exec.setText(self.tr("Bridged Out-of-Process") if isBridged else self.tr("Native In-Process"))
            self.l_bridged.setText(self.tr("Yes") if isBridged else self.tr("No"))

            self.l_audio_io.setText(f"{info['audioIns']} in / {info['audioOuts']} out")
            self.l_midi_io.setText(f"{info['midiIns']} in / {info['midiOuts']} out")
            self.l_pins.setText(str(info["parameterIns"]))
            self.l_cv_io.setText(f"{info['cvIns']} in / {info['cvOuts']} out")

            # Update feature badges in flow layout
            while self.flowFeat.count() > 0:
                child = self.flowFeat.takeAt(0)
                if child and child.widget():
                    child.widget().deleteLater()

            features = []
            if info["hints"] & PLUGIN_HAS_CUSTOM_UI:
                features.append(self.tr("Custom GUI"))
            if info["hints"] & PLUGIN_HAS_INLINE_DISPLAY:
                features.append(self.tr("Inline Display"))
            if info["hints"] & PLUGIN_IS_RTSAFE:
                features.append(self.tr("Realtime Safe"))
            if isSynth:
                features.append(self.tr("Synth"))
            if info["cvIns"] > 0 or info["cvOuts"] > 0:
                features.append(self.tr("CV Ports"))
            if info["audioIns"] >= 2 or info["audioOuts"] >= 2:
                features.append(self.tr("Stereo"))

            if features:
                for feat in features:
                    tag = QLabel(feat, self.cardFeat)
                    tag.setObjectName("infoTag")
                    self.flowFeat.addWidget(tag)
            else:
                tag = QLabel(self.tr("None"), self.cardFeat)
                tag.setObjectName("infoTag")
                self.flowFeat.addWidget(tag)

            self.l_binary.setText(info.get("filename") or "")
        else:
            self.b_add.setEnabled(False)
            self.l_badge.setText("---")
            self.l_name.setText(self.tr("No plugin selected"))
            self.l_maker.setText("---")
            self.l_category.setText("---")
            self.l_arch.setText("---")
            self.l_exec.setText("---")
            self.l_bridged.setText("---")
            self.l_audio_io.setText("---")
            self.l_midi_io.setText("---")
            self.l_pins.setText("---")
            self.l_cv_io.setText("---")
            self.l_binary.clear()
            while self.flowFeat.count() > 0:
                child = self.flowFeat.takeAt(0)
                if child and child.widget():
                    child.widget().deleteLater()
            tag = QLabel(self.tr("None"), self.cardFeat)
            tag.setObjectName("infoTag")
            self.flowFeat.addWidget(tag)

    # ----------------------------------------------------------------------------------------------------
    # CSV export

    def appendToCSV(self):
        out = []

        def appendVec(vec):
            for info in vec:
                out.append("%d|%d|%d|%s|%s|%s|%s|%s|%d\n" % (
                    int(info["build"]), int(info["type"]), int(info["hints"]),
                    info["category"], info["filename"], info["name"], info["label"],
                    info["maker"], int(info["uniqueId"])))

        order = ["internal", "ladspa", "dssi", "lv2", "vst2", "vst3", "clap", "au", "jsfx", "kits"]
        for key in order:
            appendVec(self._plugins[key])

        return "".join(out)

# ------------------------------------------------------------------------------------------------------------
# Module-level API (drop-in replacement for the native carla_frontend wrappers)

def createPluginListDialog(parent, hostSettings):
    return PyPluginListDialog(parent, hostSettings)


def destroyPluginListDialog(dialog):
    if dialog is None:
        return
    dialog.close()
    dialog.setParent(None)
    dialog.deleteLater()


def setPluginListDialogPath(dialog, ptype, path):
    if dialog is None:
        return
    dialog.setPluginPath(ptype, path)


def execPluginListDialog(dialog):
    if dialog is None:
        return None
    if dialog.exec():
        return dialog.getSelectedPluginInfo()
    return None


def getCachedPluginsCsv(dialog):
    if dialog is None:
        return ""
    return dialog.appendToCSV()

# ------------------------------------------------------------------------------------------------------------
