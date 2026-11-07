#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2011-2025 Filipe Coelho <falktx@falktx.com>
# SPDX-License-Identifier: GPL-2.0-or-later

# ------------------------------------------------------------------------------------------------------------
# Imports (Global)

# ------------------------------------------------------------------------------------------------------------
# Imports (Custom)
import ui_carla_plugin_calf
import ui_carla_plugin_classic
import ui_carla_plugin_compact
import ui_carla_plugin_default
import ui_carla_plugin_presets
from carla_backend import *
from carla_shared import *
from carla_widgets import *
from patchcanvas.theme import Theme
from qt_compat import (
    QAbstractSpinBox,
    QColor,
    QColorDialog,
    QComboBox,
    QDoubleSpinBox,
    QEvent,
    QFont,
    QFontDatabase,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QLayout,
    QLineEdit,
    QLineF,
    QMenu,
    QMessageBox,
    QPainter,
    QPainterPath,
    QPen,
    QPoint,
    QPushButton,
    QRect,
    QRectF,
    QScrollArea,
    QSize,
    QSizePolicy,
    QSlider,
    QSpacerItem,
    Qt,
    QTimer,
    QVBoxLayout,
    QWidget,
    QWidgetAction,
)
from utils import QSafeSettings
from widgets.digitalpeakmeter import DigitalPeakMeter
from widgets.paramspinbox import CustomInputDialog
from widgets.scalabledial import ScalableDial

# ------------------------------------------------------------------------------------------------------------
# ------------------------------------------------------------------------------------------------------------
# Catppuccin Palette Definitions

CATPPUCCIN_MOCHA = {
    'base': '#1e1e2e',
    'mantle': '#181825',
    'crust': '#11111b',
    'surface0': '#313244',
    'surface1': '#45475a',
    'surface2': '#585b70',
    'overlay0': '#6c7086',
    'overlay1': '#7f849c',
    'overlay2': '#9399b2',
    'subtext0': '#a6adc8',
    'subtext1': '#bac2de',
    'text': '#cdd6f4',
    'lavender': '#b4befe',
    'blue': '#89b4fa',
    'sapphire': '#74c7ec',
    'sky': '#89dceb',
    'teal': '#94e2d5',
    'green': '#a6e3a1',
    'yellow': '#f9e2af',
    'peach': '#fab387',
    'maroon': '#eba0ac',
    'red': '#f38ba8',
    'mauve': '#cba6f7',
    'pink': '#f5c2e7',
    'flamingo': '#f2cdcd',
    'rosewater': '#f5e0dc',
}

CATPPUCCIN_LATTE = {
    'base': '#eff1f5',
    'mantle': '#e6e9ef',
    'crust': '#dce0e8',
    'surface0': '#ccd0da',
    'surface1': '#bcc0cc',
    'surface2': '#acb0be',
    'overlay0': '#9ca0b0',
    'overlay1': '#8c8fa1',
    'overlay2': '#7c7f93',
    'subtext0': '#6c6f85',
    'subtext1': '#5c5f77',
    'text': '#4c4f69',
    'lavender': '#7287fd',
    'blue': '#1e66f5',
    'sapphire': '#209fb5',
    'sky': '#04a5e5',
    'teal': '#179299',
    'green': '#40a02b',
    'yellow': '#df8e1d',
    'peach': '#fe640b',
    'maroon': '#e64553',
    'red': '#d20f39',
    'mauve': '#8839ef',
    'pink': '#ea76cb',
    'flamingo': '#dd7878',
    'rosewater': '#dc8a78',
}


def get_active_skin_palette(is_dark=True):
    """Retrieve active palette dynamically from theme_manager with fallback to Catppuccin."""
    try:
        from styles.theme_manager import theme_manager
        t = theme_manager.engine.active_tokens
        if t and "bg-surface" in t:
            return {
                'base': t.get("bg-primary", "#1e1e2e" if is_dark else "#eff1f5"),
                'mantle': t.get("bg-primary", "#181825" if is_dark else "#e6e9ef"),
                'crust': t.get("base00", "#11111b" if is_dark else "#dce0e8"),
                'surface0': t.get("border-dim", "#313244" if is_dark else "#ccd0da"),
                'surface1': t.get("bg-surface", "#45475a" if is_dark else "#bcc0cc"),
                'surface2': t.get("bg-hover", "#585b70" if is_dark else "#acb0be"),
                'overlay0': t.get("text-muted", "#6c7086" if is_dark else "#9ca0b0"),
                'overlay1': t.get("text-secondary", "#7f849c" if is_dark else "#8c8fa1"),
                'overlay2': t.get("text-secondary", "#9399b2" if is_dark else "#7c7f93"),
                'subtext0': t.get("text-secondary", "#a6adc8" if is_dark else "#6c6f85"),
                'subtext1': t.get("text-primary", "#bac2de" if is_dark else "#5c5f77"),
                'text': t.get("text-primary", "#cdd6f4" if is_dark else "#4c4f69"),
                'lavender': t.get("purple", "#b4befe" if is_dark else "#7287fd"),
                'blue': t.get("accent", "#89b4fa" if is_dark else "#1e66f5"),
                'sapphire': t.get("cyan", "#74c7ec" if is_dark else "#209fb5"),
                'sky': t.get("cyan", "#89dceb" if is_dark else "#04a5e5"),
                'teal': t.get("cyan", "#94e2d5" if is_dark else "#179299"),
                'green': t.get("green", "#a6e3a1" if is_dark else "#40a02b"),
                'yellow': t.get("yellow", "#f9e2af" if is_dark else "#df8e1d"),
                'peach': t.get("orange", "#fab387" if is_dark else "#fe640b"),
                'maroon': t.get("red", "#eba0ac" if is_dark else "#e64553"),
                'red': t.get("red", "#f38ba8" if is_dark else "#d20f39"),
                'mauve': t.get("magenta", "#cba6f7" if is_dark else "#8839ef"),
                'pink': t.get("magenta", "#f5c2e7" if is_dark else "#ea76cb"),
                'flamingo': t.get("orange", "#f2cdcd" if is_dark else "#dd7878"),
                'rosewater': t.get("accent-tint-15", "#f5e0dc" if is_dark else "#dc8a78"),
            }
    except Exception:
        pass
    return CATPPUCCIN_MOCHA if is_dark else CATPPUCCIN_LATTE


class FlowLayout(QLayout):
    """A QLayout that wraps child items like CSS flex-wrap: wrap."""

    def __init__(self, parent=None, hSpacing=4, vSpacing=4):
        super().__init__(parent)
        self._hSpacing = hSpacing
        self._vSpacing = vSpacing
        self._items = []

    def addItem(self, item):
        self._items.append(item)

    def horizontalSpacing(self):
        return self._hSpacing

    def verticalSpacing(self):
        return self._vSpacing

    def count(self):
        return len(self._items)

    def itemAt(self, index):
        if 0 <= index < len(self._items):
            return self._items[index]
        return None

    def takeAt(self, index):
        if 0 <= index < len(self._items):
            return self._items.pop(index)
        return None

    def expandingDirections(self):
        try:
            return Qt.Orientations()
        except Exception:
            try:
                return Qt.Orientation(0)
            except Exception:
                return 0

    def hasHeightForWidth(self):
        return True

    def heightForWidth(self, width):
        return self._doLayout(QRect(0, 0, width, 0), testOnly=True)

    def setGeometry(self, rect):
        super().setGeometry(rect)
        self._doLayout(rect, testOnly=False)

    def sizeHint(self):
        return self.minimumSize()

    def minimumSize(self):
        size = QSize()
        for item in self._items:
            size = size.expandedTo(item.minimumSize())
        m = self.contentsMargins()
        size += QSize(m.left() + m.right(), m.top() + m.bottom())
        return size

    def _doLayout(self, rect, testOnly):
        m = self.contentsMargins()
        effectiveRect = rect.adjusted(m.left(), m.top(), -m.right(), -m.bottom())
        x = effectiveRect.x()
        y = effectiveRect.y()
        lineHeight = 0

        for item in self._items:
            spaceX = self._hSpacing
            spaceY = self._vSpacing
            nextX = x + item.sizeHint().width() + spaceX

            if effectiveRect.width() > 0 and (nextX - spaceX > effectiveRect.right()) and lineHeight > 0:
                x = effectiveRect.x()
                y = y + lineHeight + spaceY
                nextX = x + item.sizeHint().width() + spaceX
                lineHeight = 0

            if not testOnly:
                item.setGeometry(QRect(QPoint(x, y), item.sizeHint()))

            x = nextX
            lineHeight = max(lineHeight, item.sizeHint().height())

        return y + lineHeight - rect.y() + m.top() + m.bottom()

# ------------------------------------------------------------------------------------------------------------
# Plugin Skin Rules (WORK IN PROGRESS)

# Base is a QFrame (NoFrame, Plain, 0-size lines), with "PluginWidget" as object name.
# Spacing of the top-most layout must be 1px.
# Top and bottom margins must be 3px (can be split between different Qt layouts).
# Left and right margins must be 6px (can be split between different Qt layouts).
# If the left or right side has built-in margins, say a transparent svg border,
# those margins must be taken into consideration.
#
# There's a top and bottom layout, separated by a horizontal line.
# Compacted skins do not have the bottom layout and separating line.

#  T O P  A R E A
#
#  -----------------------------------------------------------------
# |          <> | <>                            [ WIDGETS ] [ LEDS ] |
# | BUTTONS <> | <> PLUGIN NAME   < spacer >   [ WIDGETS ] [ LEDS ] |
# |          <> | <>                            [ WIDGETS ] [ LEDS ] |
#  -----------------------------------------------------------------
#
# Buttons area has size fixed. (TBA)
# Spacers at the left of the plugin name must be 8x1 in size (fixed).
# The line before the plugin name must be height-10px (fixed).
# WIDGETS area can be extended to the left, if using meters they should have 80px.
# WIDGETS margins are 4px for left+right and 2px for top+bottom, with 4px spacing.

# ------------------------------------------------------------------------------------------------------------
# Try to "shortify" a parameter name

def getParameterShortName(paramName):
    paramName = paramName.split("/",1)[0].split(" (",1)[0].split(" [",1)[0].strip()
    paramLow  = paramName.lower()

    if paramLow.startswith("compressor "):
        paramName = paramName.replace("ompressor ", ".", 1)
        paramLow  = paramName.lower()
    elif paramLow.startswith("room "):
        paramName = paramName.split(" ",1)[1]
        paramLow  = paramName.lower()

    if paramLow.endswith((" level", " time")):
        paramName = paramName.rsplit(" ",1)[0]
        paramLow  = paramName.lower()

    if "attack" in paramLow:
        paramName = paramName.replace("ttack", "tk")
    elif "bandwidth" in paramLow:
        paramName = paramName.replace("andwidth", "w")
    elif "damping" in paramLow:
        paramName = paramName.replace("amping", "amp")
    elif "distortion" in paramLow:
        paramName = paramName.replace("istortion", "ist")
    elif "feedback" in paramLow:
        paramName = paramName.replace("eedback", "b")
    elif "frequency" in paramLow:
        paramName = paramName.replace("requency", "req")
    elif "input" in paramLow:
        paramName = paramName.replace("nput", "n")
    elif "makeup" in paramLow:
        paramName = paramName.replace("akeup", "kUp" if "Make" in paramName else "kup")
    elif "output" in paramLow:
        paramName = paramName.replace("utput", "ut")
    elif "random" in paramLow:
        paramName = paramName.replace("andom", "nd")
    elif "threshold" in paramLow:
        paramName = paramName.replace("hreshold", "hres")

    if " " in paramName:
        name1, name2 = paramName.split(" ", 1)
        if (name1[-1].islower() and name2[0].isupper()) or name2.isdigit():
            paramName = paramName.replace(" ", "", 1)

    if len(paramName) > 10:
        paramName = paramName[:10]

    return paramName.strip()

# ------------------------------------------------------------------------------------------------------------
# Get RGB colors for a plugin category

def getColorFromCategory(category):
    r = 40
    g = 40
    b = 40

    if category == PLUGIN_CATEGORY_MODULATOR:
        r += 10
    elif category == PLUGIN_CATEGORY_EQ:
        g += 10
    elif category == PLUGIN_CATEGORY_FILTER:
        b += 10
    elif category == PLUGIN_CATEGORY_DELAY:
        r += 15
        b -= 15
    elif category == PLUGIN_CATEGORY_DISTORTION:
        g += 10
        b += 10
    elif category == PLUGIN_CATEGORY_DYNAMICS:
        r += 10
        b += 10
    elif category == PLUGIN_CATEGORY_UTILITY:
        r += 10
        g += 10

    return (r, g, b)

# ------------------------------------------------------------------------------------------------------------

def setScalableDialStyle(widget, parameterId, parameterCount, whiteLabels, skinStyle):
    is_dark = "light" not in skinStyle

    if is_dark:
        color = QColor("#00bcd4")
        colorEnabled  = QColor("#FFFFFF")
        colorDisabled = QColor("#787c88")
    else:
        color = QColor("#00838f")
        colorEnabled  = QColor("#14151b")
        colorDisabled = QColor("#858896")

    widget.setCustomPaintColor(color)
    widget.setCustomPaintMode(ScalableDial.CUSTOM_PAINT_MODE_FLAT)
    widget.setLabelColor(colorEnabled, colorDisabled)
    widget.setImage(3)

# ------------------------------------------------------------------------------------------------------------
# Abstract plugin slot

class AbstractPluginSlot(QFrame, PluginEditParentMeta):
    def __init__(self, parent, host, pluginId, skinColor, skinStyle):
        QFrame.__init__(self, parent)
        self.host = host
        self.fParent = parent

        self.fPluginId   = pluginId
        self.fPluginInfo = host.get_plugin_info(self.fPluginId)
        self.fSkinColor  = skinColor
        self.fSkinStyle  = skinStyle

        if skinStyle in ("minimal-light", "sliders-light"):
            self.fDarkStyle = False
        elif skinStyle in ("minimal-dark", "sliders-dark"):
            self.fDarkStyle = True
        else:
            self.fDarkStyle = QColor(skinColor[0], skinColor[1], skinColor[2]).blackF() > 0.4

        self.fIsActive   = False
        self.fIsSelected = False

        self.fLastGreenLedState = False
        self.fLastBlueLedState  = False

        self.fParameterIconTimer = ICON_STATE_NULL
        self.fParameterList      = []

        audioCountInfo = host.get_audio_port_count_info(self.fPluginId)

        self.fPeaksInputCount  = audioCountInfo['ins']
        self.fPeaksOutputCount = audioCountInfo['outs']

        self.fPeaksInputCount = min(self.fPeaksInputCount, 2)

        self.fPeaksOutputCount = min(self.fPeaksOutputCount, 2)

        self.fAdjustViewableKnobCountScheduled = False
        self.fIdleTimerId = 0

        self.fEditDialog = None

        self.b_enable = None
        self.b_gui    = None
        self.b_edit   = None
        self.b_remove = None

        self.cb_presets = None

        self.label_name    = None
        self.line_rename   = None
        self.label_presets = None
        self.label_type    = None

        self.led_control   = None
        self.led_midi      = None
        self.led_audio_in  = None
        self.led_audio_out = None

        self.peak_in  = None
        self.peak_out = None

        self.w_knobs_left  = None
        self.w_knobs_right = None
        self.spacer_knobs  = None

        self.customContextMenuRequested.connect(self.slot_showCustomMenu)
        host.PluginRenamedCallback.connect(self.slot_handlePluginRenamedCallback)
        host.PluginUnavailableCallback.connect(self.slot_handlePluginUnavailableCallback)
        host.ParameterValueChangedCallback.connect(self.slot_handleParameterValueChangedCallback)
        host.ParameterDefaultChangedCallback.connect(self.slot_handleParameterDefaultChangedCallback)
        host.ParameterMappedControlIndexChangedCallback.connect(self.slot_handleParameterMappedControlIndexChangedCallback)
        host.ParameterMappedRangeChangedCallback.connect(self.slot_handleParameterMappedRangeChangedCallback)
        host.ParameterMidiChannelChangedCallback.connect(self.slot_handleParameterMidiChannelChangedCallback)
        host.ProgramChangedCallback.connect(self.slot_handleProgramChangedCallback)
        host.MidiProgramChangedCallback.connect(self.slot_handleMidiProgramChangedCallback)
        host.OptionChangedCallback.connect(self.slot_handleOptionChangedCallback)
        host.UiStateChangedCallback.connect(self.slot_handleUiStateChangedCallback)

        self.sel_pen = QPen(Qt.cyan, 1, Qt.SolidLine, Qt.FlatCap, Qt.MiterJoin)
        self.sel_pen.setDashPattern([2.0, 4.0])
        self.sel_side_pen = QPen(Qt.cyan, 2, Qt.SolidLine, Qt.FlatCap)
        self.shadow_pen = QPen(Qt.black, 1)

    @pyqtSlot(int, str)
    def slot_handlePluginRenamedCallback(self, pluginId, newName):
        if self.fEditDialog is not None and self.fPluginId == pluginId:
            self.setName(newName)

    @pyqtSlot(int, str)
    def slot_handlePluginUnavailableCallback(self, pluginId, errorMsg):
        if self.fEditDialog is not None and self.fPluginId == pluginId:
            pass

    @pyqtSlot(int, int, float)
    def slot_handleParameterValueChangedCallback(self, pluginId, index, value):
        if self.fEditDialog is not None and self.fPluginId == pluginId:
            self.setParameterValue(index, value, True)

    @pyqtSlot(int, int, float)
    def slot_handleParameterDefaultChangedCallback(self, pluginId, index, value):
        if self.fEditDialog is not None and self.fPluginId == pluginId:
            self.setParameterDefault(index, value)

    @pyqtSlot(int, int, int)
    def slot_handleParameterMappedControlIndexChangedCallback(self, pluginId, index, ctrl):
        if self.fEditDialog is not None and self.fPluginId == pluginId:
            self.setParameterMappedControlIndex(index, ctrl)

    @pyqtSlot(int, int, float, float)
    def slot_handleParameterMappedRangeChangedCallback(self, pluginId, index, minimum, maximum):
        if self.fEditDialog is not None and self.fPluginId == pluginId:
            self.setParameterMappedRange(index, minimum, maximum)

    @pyqtSlot(int, int, int)
    def slot_handleParameterMidiChannelChangedCallback(self, pluginId, index, channel):
        if self.fEditDialog is not None and self.fPluginId == pluginId:
            self.setParameterMidiChannel(index, channel)

    @pyqtSlot(int, int)
    def slot_handleProgramChangedCallback(self, pluginId, index):
        if self.fEditDialog is not None and self.fPluginId == pluginId:
            self.setProgram(index, True)

    @pyqtSlot(int, int)
    def slot_handleMidiProgramChangedCallback(self, pluginId, index):
        if self.fEditDialog is not None and self.fPluginId == pluginId:
            self.setMidiProgram(index, True)

    @pyqtSlot(int, int, bool)
    def slot_handleOptionChangedCallback(self, pluginId, option, yesNo):
        if self.fEditDialog is not None and self.fPluginId == pluginId:
            self.setOption(option, yesNo)

    @pyqtSlot(int, int)
    def slot_handleUiStateChangedCallback(self, pluginId, state):
        if self.fEditDialog is not None and self.fPluginId == pluginId:
            self.customUiStateChanged(state)

    def refreshState(self):
        self.fIsActive = bool(self.host.get_internal_parameter_value(self.fPluginId, PARAMETER_ACTIVE) >= 0.5)

        if self.b_enable is not None:
            self.b_enable.blockSignals(True)
            self.b_enable.setChecked(self.fIsActive)
            self.b_enable.blockSignals(False)

        if self.label_name is not None:
            self.label_name.setEnabled(self.fIsActive)

        if self.b_gui is not None:
            self.b_gui.setEnabled(bool(self.fPluginInfo['hints'] & PLUGIN_HAS_CUSTOM_UI))

        self.updateParameterValues()

        if not self.fAdjustViewableKnobCountScheduled:
            self.fAdjustViewableKnobCountScheduled = True
            QTimer.singleShot(50, self.adjustViewableKnobCount)

    def ready(self):
        self.fIsActive = bool(self.host.get_internal_parameter_value(self.fPluginId, PARAMETER_ACTIVE) >= 0.5)

        isCalfSkin = self.fSkinStyle.startswith("calf") and not isinstance(self, PluginSlot_Compact)

        if self.fSkinStyle in ("minimal-light", "sliders-light"):
            imageSuffix = "black"
            whiteLabels = False
        elif self.fSkinStyle in ("minimal-dark", "sliders-dark") or self.fSkinStyle.startswith("calf") or self.fSkinStyle.startswith("openav") or self.fSkinStyle in (
            "3bandeq", "3bandsplitter", "pingpongpan", "nekobi", "calf_black", "zynfx"):
            imageSuffix = "white"
            whiteLabels = True
        else:
            imageSuffix = "white" if self.fDarkStyle else "black"
            whiteLabels = self.fDarkStyle

        if self.b_enable is not None:
            self.b_enable.setChecked(self.fIsActive)
            self.b_enable.clicked.connect(self.slot_enableClicked)

            if isCalfSkin:
                self.b_enable.setPixmaps(":/bitmaps/button_calf3.png",
                                         ":/bitmaps/button_calf3_down.png",
                                         ":/bitmaps/button_calf3.png")
            else:
                self.b_enable.setSvgs(":/scalable/button_off.svg",
                                      ":/scalable/button_on.svg",
                                      ":/scalable/button_off.svg")

        if self.b_gui is not None:
            self.b_gui.clicked.connect(self.slot_showCustomUi)
            self.b_gui.setEnabled(bool(self.fPluginInfo['hints'] & PLUGIN_HAS_CUSTOM_UI))

            if isCalfSkin:
                self.b_gui.setPixmaps(":/bitmaps/button_calf2.png",
                                      ":/bitmaps/button_calf2_down.png",
                                      ":/bitmaps/button_calf2_hover.png")
            elif self.fPluginInfo['iconName'] == "distrho" or self.fSkinStyle in ("3bandeq", "3bandsplitter", "pingpongpan", "nekobi"):
                self.b_gui.setPixmaps(f":/bitmaps/button_distrho-{imageSuffix}.png",
                                      f":/bitmaps/button_distrho_down-{imageSuffix}.png",
                                      f":/bitmaps/button_distrho_hover-{imageSuffix}.png")
            elif self.fPluginInfo['iconName'] == "file":
                self.b_gui.setPixmaps(f":/bitmaps/button_file-{imageSuffix}.png",
                                      f":/bitmaps/button_file_down-{imageSuffix}.png",
                                      f":/bitmaps/button_file_hover-{imageSuffix}.png")
            else:
                if imageSuffix == "black":
                    self.b_gui.setPixmaps(f":/bitmaps/button_gui-{imageSuffix}.png",
                                          f":/bitmaps/button_gui_down-{imageSuffix}.png",
                                          f":/bitmaps/button_gui_hover-{imageSuffix}.png")
                else:
                    self.b_gui.setSvgs(f":/scalable/button_gui-{imageSuffix}.svg",
                                       f":/scalable/button_gui_down-{imageSuffix}.svg",
                                       f":/scalable/button_gui_hover-{imageSuffix}.svg")

        if self.b_edit is not None:
            self.b_edit.clicked.connect(self.slot_showEditDialog)

            if isCalfSkin:
                self.b_edit.setPixmaps(":/bitmaps/button_calf2.png",
                                       ":/bitmaps/button_calf2_down.png",
                                       ":/bitmaps/button_calf2_hover.png")
            else:
                self.b_edit.setSvgs(f":/scalable/button_edit-{imageSuffix}.svg",
                                    f":/scalable/button_edit_down-{imageSuffix}.svg",
                                    f":/scalable/button_edit_hover-{imageSuffix}.svg")
        else:
            self.b_edit = QPushButton(self)
            self.b_edit.setCheckable(True)
            self.b_edit.hide()

        if self.b_remove is not None:
            self.b_remove.clicked.connect(self.slot_removePlugin)

        if self.label_name is not None:
            self.label_name.setEnabled(self.fIsActive)
            self.label_name.setText(self.fPluginInfo['name'])

            nameFont = self.label_name.font()

            if self.fSkinStyle.startswith("calf"):
                nameFont.setBold(True)
                nameFont.setPixelSize(12)
            elif self.fSkinStyle.startswith("openav"):
                QFontDatabase.addApplicationFont(":/fonts/uranium.ttf")
                nameFont.setFamily("Uranium")
                nameFont.setPixelSize(15)
                nameFont.setCapitalization(QFont.AllUppercase)
            else:
                nameFont.setBold(True)
                nameFont.setPixelSize(11)

            self.label_name.setFont(nameFont)
            self.setupInlineRename()

        if self.label_presets is not None:
            presetFont = self.label_presets.font()
            presetFont.setBold(True)
            presetFont.setPixelSize(10)
            self.label_presets.setFont(presetFont)

        if self.label_type is not None:
            self.label_type.setText(getPluginTypeAsString(self.fPluginInfo['type']))

        if self.led_control is not None:
            self.led_control.setColor(self.led_control.YELLOW)
            self.led_control.setEnabled(False)

        if self.led_midi is not None:
            self.led_midi.setColor(self.led_midi.RED)
            self.led_midi.setEnabled(False)

        if self.led_audio_in is not None:
            self.led_audio_in.setColor(self.led_audio_in.GREEN)
            self.led_audio_in.setEnabled(False)

        if self.led_audio_out is not None:
            self.led_audio_out.setColor(self.led_audio_out.BLUE)
            self.led_audio_out.setEnabled(False)

        if self.peak_in is not None:
            self.peak_in.setChannelCount(self.fPeaksInputCount)
            self.peak_in.setMeterColor(DigitalPeakMeter.COLOR_GREEN)
            self.peak_in.setMeterOrientation(DigitalPeakMeter.HORIZONTAL)

            if self.fSkinStyle.startswith("calf"):
                self.peak_in.setMeterStyle(DigitalPeakMeter.STYLE_CALF)
            elif self.fSkinStyle == "rncbc":
                self.peak_in.setMeterStyle(DigitalPeakMeter.STYLE_RNCBC)
            elif self.fSkinStyle.startswith("openav") or self.fSkinStyle == "zynfx":
                self.peak_in.setMeterStyle(DigitalPeakMeter.STYLE_OPENAV)

            if self.fPeaksInputCount == 0 and not isinstance(self, PluginSlot_Classic):
                self.peak_in.hide()

        if self.peak_out is not None:
            self.peak_out.setChannelCount(self.fPeaksOutputCount)
            self.peak_out.setMeterColor(DigitalPeakMeter.COLOR_BLUE)
            self.peak_out.setMeterOrientation(DigitalPeakMeter.HORIZONTAL)

            if self.fSkinStyle.startswith("calf"):
                self.peak_out.setMeterStyle(DigitalPeakMeter.STYLE_CALF)
            elif self.fSkinStyle == "rncbc":
                self.peak_out.setMeterStyle(DigitalPeakMeter.STYLE_RNCBC)
            elif self.fSkinStyle.startswith("openav") or self.fSkinStyle == "zynfx":
                self.peak_out.setMeterStyle(DigitalPeakMeter.STYLE_OPENAV)

            if self.fPeaksOutputCount == 0 and not isinstance(self, PluginSlot_Classic):
                self.peak_out.hide()

        if self.fSkinStyle == "openav":
            styleSheet = """
                QFrame#PluginWidget {
                    background-color: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                                                      stop: 0 #383838, stop: %f #111111, stop: 1.0 #111111);
                }
                QLabel#label_name          { color: #FFFFFF; }
                QLabel#label_name:disabled { color: #505050; }
            """ % (0.95 if isinstance(self, PluginSlot_Compact) else 0.35)

        elif self.fSkinStyle == "openav-old":
            styleSheet = """
                QFrame#PluginWidget {
                    background-color: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                                                      stop: 0 #303030, stop: %f #111111, stop: 1.0 #111111);
                }
                QLabel#label_name          { color: #FF5100; }
                QLabel#label_name:disabled { color: #505050; }
            """ % (0.95 if isinstance(self, PluginSlot_Compact) else 0.35)

        else:
            settings = QSafeSettings("falkTX", "Carla2")
            theme_name = settings.value(CARLA_KEY_CANVAS_THEME, CARLA_DEFAULT_CANVAS_THEME, str)
            theme = Theme(theme_name)

            box_bg_1 = theme.box_bg_1.name() if hasattr(theme, "box_bg_1") else "#444444"
            box_bg_2 = theme.box_bg_2.name() if hasattr(theme, "box_bg_2") else "#333333"
            box_text = theme.box_text.color().name() if hasattr(theme, "box_text") else "#FFFFFF"

            colorEnabled  = box_text
            colorDisabled = "#777777"

            if self.fSkinStyle in ("3bandeq", "calf_black", "calf_blue", "nekobi", "zynfx"):
                styleSheet2  = f"background-color: {box_bg_2};"
                styleSheet2 += f"background-image: url(:/bitmaps/background_{self.fSkinStyle}.png);"
            else:
                styleSheet2  = f"background-color: {box_bg_2};"
                styleSheet2 += f"border: 1px solid {box_bg_1};"
                styleSheet2 += "border-radius: 4px;"

            styleSheet = f"""
                QFrame#PluginWidget {{
                    {styleSheet2}
                    background-repeat: repeat-xy;
                }}
                QLabel#label_name,
                QLabel#label_audio_in,
                QLabel#label_audio_out,
                QLabel#label_midi,
                QLabel#label_presets       {{ color: {colorEnabled}; }}
                QLabel#label_name:disabled {{ color: {colorDisabled}; }}
            """

        styleSheet += """
            QComboBox#cb_presets,
            QLabel#label_audio_in,
            QLabel#label_audio_out,
            QLabel#label_midi { font-size: 10px; }
        """
        self.setStyleSheet(styleSheet)

        if self.w_knobs_left is not None:
            parameterCount = self.host.get_parameter_count(self.fPluginId)

            index = 0
            oldLayout = self.w_knobs_left.layout()
            if oldLayout is not None:
                while oldLayout.count():
                    oldLayout.takeAt(0)
                QWidget().setLayout(oldLayout)

            flowLayout = FlowLayout(self.w_knobs_left, hSpacing=4, vSpacing=2)
            flowLayout.setContentsMargins(4, 2, 4, 2)
            layout = flowLayout
            self.w_knobs_left.setMinimumWidth(120)
            self.w_knobs_left.setMaximumWidth(16777215)

            exp_policy = getattr(QSizePolicy, "Expanding", None) or getattr(getattr(QSizePolicy, "Policy", None), "Expanding", None)
            pref_policy = getattr(QSizePolicy, "Preferred", None) or getattr(getattr(QSizePolicy, "Policy", None), "Preferred", None)
            if exp_policy and pref_policy:
                self.w_knobs_left.setSizePolicy(exp_policy, pref_policy)

            has_right_knobs = bool(self.w_knobs_right is not None and (
                (self.fPluginInfo['hints'] & PLUGIN_CAN_DRYWET) or (self.fPluginInfo['hints'] & PLUGIN_CAN_VOLUME)
            ))

            if self.spacer_knobs is not None:
                if has_right_knobs:
                    self.spacer_knobs.changeSize(6, 1, pref_policy, pref_policy)
                else:
                    self.spacer_knobs.changeSize(0, 0, pref_policy, pref_policy)

            if hasattr(self.ui, 'layout_bottom') and self.ui.layout_bottom is not None:
                self.ui.layout_bottom.setStretch(0, 1)
                if self.ui.layout_bottom.count() > 2:
                    self.ui.layout_bottom.setStretch(2, 0)

            for i in range(parameterCount):
                if index >= 50:
                    break

                paramInfo   = self.host.get_parameter_info(self.fPluginId, i)
                paramData   = self.host.get_parameter_data(self.fPluginId, i)
                paramRanges = self.host.get_parameter_ranges(self.fPluginId, i)
                isInteger   = (paramData['hints'] & PARAMETER_IS_INTEGER) != 0

                if paramData['type'] != PARAMETER_INPUT:
                    continue
                if paramData['hints'] & PARAMETER_IS_BOOLEAN:
                    continue
                if (paramData['hints'] & PARAMETER_IS_ENABLED) == 0:
                    continue
                if (paramData['hints'] & PARAMETER_USES_SCALEPOINTS) != 0 and not isInteger:
                    continue
                if isInteger and paramRanges['max']-paramRanges['min'] <= 3:
                    continue
                if paramInfo['name'].startswith("unused"):
                    continue

                paramName = getParameterShortName(paramInfo['name'])

                widget = ScalableDial(self, i)
                widget.setLabel(paramName, paramInfo['name'])
                widget.setMinimum(paramRanges['min'])
                widget.setMaximum(paramRanges['max'])
                widget.hide()

                if isInteger:
                    widget.setPrecision(paramRanges['max']-paramRanges['min'], True)

                setScalableDialStyle(widget, i, parameterCount, whiteLabels, self.fSkinStyle)

                index += 1
                self.fParameterList.append([i, widget])
                layout.addWidget(widget)

        if self.w_knobs_right is not None and (self.fPluginInfo['hints'] & PLUGIN_CAN_DRYWET) != 0:
            widget = ScalableDial(self, PARAMETER_DRYWET)
            widget.setLabel("Dry/Wet")
            widget.setMinimum(0.0)
            widget.setMaximum(1.0)
            setScalableDialStyle(widget, PARAMETER_DRYWET, 0, whiteLabels, self.fSkinStyle)

            self.fParameterList.append([PARAMETER_DRYWET, widget])
            self.w_knobs_right.layout().addWidget(widget)

        if self.w_knobs_right is not None and (self.fPluginInfo['hints'] & PLUGIN_CAN_VOLUME) != 0:
            widget = ScalableDial(self, PARAMETER_VOLUME)
            widget.setLabel("Volume")
            widget.setMinimum(0.0)
            widget.setMaximum(1.27)
            setScalableDialStyle(widget, PARAMETER_VOLUME, 0, whiteLabels, self.fSkinStyle)

            self.fParameterList.append([PARAMETER_VOLUME, widget])
            self.w_knobs_right.layout().addWidget(widget)

        for paramIndex, paramWidget in self.fParameterList:
            paramWidget.setContextMenuPolicy(Qt.CustomContextMenu)
            paramWidget.customContextMenuRequested.connect(self.slot_knobCustomMenu)
            paramWidget.dragStateChanged.connect(self.slot_parameterDragStateChanged)
            paramWidget.realValueChanged.connect(self.slot_parameterValueChanged)
            paramWidget.blockSignals(True)
            if paramIndex < 0:
                paramWidget.setValue(self.host.get_internal_parameter_value(self.fPluginId, paramIndex))
            else:
                paramWidget.setValue(self.host.get_current_parameter_value(self.fPluginId, paramIndex))
            paramWidget.blockSignals(False)

        self.setWindowTitle(self.fPluginInfo['name'])

        if not self.fAdjustViewableKnobCountScheduled:
            self.fAdjustViewableKnobCountScheduled = True
            QTimer.singleShot(5, self.adjustViewableKnobCount)

    def getFixedHeight(self):
        return 32

    def getHints(self):
        return self.fPluginInfo['hints']

    def getPluginId(self):
        return self.fPluginId

    def setPluginId(self, idx):
        self.fPluginId = idx
        if self.fEditDialog is not None:
            self.fEditDialog.setPluginId(idx)

    def setName(self, name):
        self.fPluginInfo['name'] = name
        if self.fEditDialog is not None:
            self.fEditDialog.setName(name)

        if self.label_name is not None:
            self.label_name.setText(name)

        if getattr(self, 'line_rename', None) is not None and not self.line_rename.isVisible():
            self.line_rename.setText(name)

    def setSelected(self, yesNo):
        if self.fIsSelected == yesNo:
            return

        self.fIsSelected = yesNo
        self.update()

    def setActive(self, active, sendCallback=False, sendHost=True):
        self.fIsActive = active

        if sendCallback:
            self.fParameterIconTimer = ICON_STATE_ON
            self.activeChanged(active)

        if sendHost:
            self.host.set_active(self.fPluginId, active)

        if active:
            if self.fEditDialog is not None:
                self.fEditDialog.clearNotes()
            self.midiActivityChanged(False)

        if self.b_enable is not None:
            self.b_enable.blockSignals(True)
            self.b_enable.setChecked(active)
            self.b_enable.blockSignals(False)

        if self.label_name is not None:
            self.label_name.setEnabled(self.fIsActive)

    def setInternalParameter(self, parameterId, value):
        if parameterId <= PARAMETER_MAX or parameterId >= PARAMETER_NULL:
            return

        elif parameterId == PARAMETER_ACTIVE:
            return self.setActive(bool(value), True, True)

        elif parameterId == PARAMETER_DRYWET:
            if (self.fPluginInfo['hints'] & PLUGIN_CAN_DRYWET) == 0: return
            self.host.set_drywet(self.fPluginId, value)

        elif parameterId == PARAMETER_VOLUME:
            if (self.fPluginInfo['hints'] & PLUGIN_CAN_VOLUME) == 0: return
            self.host.set_volume(self.fPluginId, value)

        elif parameterId == PARAMETER_BALANCE_LEFT:
            if (self.fPluginInfo['hints'] & PLUGIN_CAN_BALANCE) == 0: return
            self.host.set_balance_left(self.fPluginId, value)

        elif parameterId == PARAMETER_BALANCE_RIGHT:
            if (self.fPluginInfo['hints'] & PLUGIN_CAN_BALANCE) == 0: return
            self.host.set_balance_right(self.fPluginId, value)

        elif parameterId == PARAMETER_PANNING:
            if (self.fPluginInfo['hints'] & PLUGIN_CAN_PANNING) == 0: return
            self.host.set_panning(self.fPluginId, value)

        elif parameterId == PARAMETER_CTRL_CHANNEL:
            self.host.set_ctrl_channel(self.fPluginId, value)

        if self.fEditDialog is not None:
            self.fEditDialog.setParameterValue(parameterId, value)

    def setParameterValue(self, parameterId, value, sendCallback):
        if parameterId == PARAMETER_ACTIVE:
            return self.setActive(bool(value), True, False)

        if self.fEditDialog is not None:
            self.fEditDialog.setParameterValue(parameterId, value)

        if sendCallback:
            self.fParameterIconTimer = ICON_STATE_ON
            self.editDialogParameterValueChanged(self.fPluginId, parameterId, value)

    def setParameterDefault(self, parameterId, value):
        if self.fEditDialog is not None:
            self.fEditDialog.setParameterDefault(parameterId, value)

    def setParameterMappedControlIndex(self, parameterId, control):
        if self.fEditDialog is not None:
            self.fEditDialog.setParameterMappedControlIndex(parameterId, control)

    def setParameterMappedRange(self, parameterId, minimum, maximum):
        if self.fEditDialog is not None:
            self.fEditDialog.setParameterMappedRange(parameterId, minimum, maximum)

    def setParameterMidiChannel(self, parameterId, channel):
        if self.fEditDialog is not None:
            self.fEditDialog.setParameterMidiChannel(parameterId, channel)

    def setProgram(self, index, sendCallback):
        if self.fEditDialog is not None:
            self.fEditDialog.setProgram(index)

        if sendCallback:
            self.fParameterIconTimer = ICON_STATE_ON
            self.editDialogProgramChanged(self.fPluginId, index)

        self.updateParameterValues()

    def setMidiProgram(self, index, sendCallback):
        if self.fEditDialog is not None:
            self.fEditDialog.setMidiProgram(index)

        if sendCallback:
            self.fParameterIconTimer = ICON_STATE_ON
            self.editDialogMidiProgramChanged(self.fPluginId, index)

        self.updateParameterValues()

    def setOption(self, option, yesNo):
        if self.fEditDialog is not None:
            self.fEditDialog.setOption(option, yesNo)

    def showCustomUI(self):
        self.host.show_custom_ui(self.fPluginId, True)

        if self.b_gui is not None:
            self.b_gui.setChecked(True)

    def hideCustomUI(self):
        self.host.show_custom_ui(self.fPluginId, False)

        if self.b_gui is not None:
            self.b_gui.setChecked(False)

    def _ensureEditDialog(self):
        if self.fEditDialog is None:
            self.fEditDialog = PluginEdit(self, self.host, self.fPluginId)
        return self.fEditDialog

    def showEditDialog(self):
        dialog = self._ensureEditDialog()
        dialog.show()
        dialog.activateWindow()

        if self.b_edit is not None:
            self.b_edit.setChecked(True)

    def showRenameDialog(self):
        oldName    = self.fPluginInfo['name']
        newNameTry = QInputDialog.getText(self, self.tr("Rename Plugin"), self.tr("New plugin name:"), QLineEdit.Normal, oldName)

        if not (newNameTry[1] and newNameTry[0] and oldName != newNameTry[0]):
            return

        newName = newNameTry[0]

        if not self.host.rename_plugin(self.fPluginId, newName):
            CustomMessageBox(self, QMessageBox.Warning, self.tr("Error"), self.tr("Operation failed"),
                                   self.host.get_last_error(), QMessageBox.Ok, QMessageBox.Ok)
            return

    def setupInlineRename(self):
        if self.label_name is None:
            return
        if getattr(self, 'line_rename', None) is not None:
            return

        self.label_name.setToolTip(self.tr("Double-click to rename"))

        parent_widget = self.label_name.parentWidget()
        if parent_widget is None:
            parent_widget = self

        self.line_rename = QLineEdit(parent_widget)
        self.line_rename.setObjectName("inline_plugin_rename")
        self.line_rename.setFont(self.label_name.font())
        self.line_rename.setMaximumHeight(22)
        self.line_rename.setMinimumWidth(80)
        self.line_rename.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        self.line_rename.setStyleSheet(
            "QLineEdit#inline_plugin_rename {"
            " background-color: #313244;"
            " color: #cdd6f4;"
            " border: 1px solid #89b4fa;"
            " border-radius: 3px;"
            " padding: 1px 4px;"
            " selection-background-color: #585b70;"
            " selection-color: #ffffff;"
            "}"
            "QLineEdit#inline_plugin_rename:focus {"
            " border: 1px solid #b4befe;"
            "}"
        )
        self.line_rename.hide()

        inserted = False
        for attr in ("layout_top", "horizontalLayout", "horizontalLayout_2", "verticalLayout"):
            l = getattr(getattr(self, "ui", None), attr, None)
            if l is not None and l.indexOf(self.label_name) != -1:
                idx = l.indexOf(self.label_name)
                l.insertWidget(idx + 1, self.line_rename)
                inserted = True
                break

        if not inserted:
            try:
                for layout in parent_widget.findChildren(QLayout):
                    idx = layout.indexOf(self.label_name)
                    if idx != -1:
                        layout.insertWidget(idx + 1, self.line_rename)
                        inserted = True
                        break
            except Exception:
                pass

        if not inserted and parent_widget.layout() is not None:
            parent_widget.layout().addWidget(self.line_rename)

        self.label_name.installEventFilter(self)
        self.line_rename.installEventFilter(self)
        self.line_rename.returnPressed.connect(self.slot_finishInlineRename)

    def eventFilter(self, watched, event):
        if self.label_name is not None and watched is self.label_name:
            if event.type() == QEvent.MouseButtonDblClick and event.button() == Qt.LeftButton:
                self.startInlineRename()
                return True
        elif getattr(self, 'line_rename', None) is not None and watched is self.line_rename:
            if event.type() == QEvent.KeyPress:
                if event.key() == Qt.Key_Escape:
                    self.cancelInlineRename()
                    return True
                elif event.key() in (Qt.Key_Return, Qt.Key_Enter):
                    self.slot_finishInlineRename()
                    return True
            elif event.type() == QEvent.FocusOut:
                self.slot_finishInlineRename()
                return False
        return QFrame.eventFilter(self, watched, event)

    def startInlineRename(self):
        if getattr(self, 'line_rename', None) is None or self.label_name is None:
            return
        current_name = self.fPluginInfo.get('name', '')
        self.line_rename.setText(current_name)
        self.label_name.hide()
        self.line_rename.show()
        self.line_rename.setFocus()
        self.line_rename.selectAll()

    def slot_finishInlineRename(self):
        if getattr(self, 'line_rename', None) is None or self.label_name is None:
            return
        if not self.line_rename.isVisible():
            return

        new_name = self.line_rename.text().strip()
        old_name = self.fPluginInfo.get('name', '')
        self.line_rename.hide()
        self.label_name.show()

        if new_name and new_name != old_name:
            if not self.host.rename_plugin(self.fPluginId, new_name):
                CustomMessageBox(self, QMessageBox.Warning, self.tr("Error"), self.tr("Operation failed"),
                                 self.host.get_last_error(), QMessageBox.Ok, QMessageBox.Ok)
            else:
                self.setName(new_name)

    def cancelInlineRename(self):
        if getattr(self, 'line_rename', None) is None or self.label_name is None:
            return
        if not self.line_rename.isVisible():
            return
        self.line_rename.hide()
        self.label_name.show()

    def showReplaceDialog(self):
        if hasattr(gCarla.gui, "showReplaceWithRewire"):
            gCarla.gui.showReplaceWithRewire(self.fPluginId)
            return

        data = gCarla.gui.showAddPluginDialog()

        if data is None:
            return

        btype, ptype, filename, label, uniqueId, extraPtr = data

        if not self.host.replace_plugin(self.fPluginId):
            CustomMessageBox(self, QMessageBox.Critical, self.tr("Error"), self.tr("Failed to replace plugin"), self.host.get_last_error(), QMessageBox.Ok, QMessageBox.Ok)
            return

        ok = self.host.add_plugin(btype, ptype, filename, None, label, uniqueId, extraPtr, PLUGIN_OPTIONS_NULL)

        if not ok:
            CustomMessageBox(self, QMessageBox.Critical, self.tr("Error"), self.tr("Failed to load plugin"), self.host.get_last_error(), QMessageBox.Ok, QMessageBox.Ok)

    def activeChanged(self, onOff):
        self.fIsActive = onOff

        if self.b_enable is None:
            return

        self.b_enable.blockSignals(True)
        self.b_enable.setChecked(onOff)
        self.b_enable.blockSignals(False)

        if self.label_name is not None:
            self.label_name.setEnabled(onOff)

    def customUiStateChanged(self, state):
        if self.b_gui is None:
            return

        self.b_gui.blockSignals(True)
        if state == 0:
            self.b_gui.setChecked(False)
            self.b_gui.setEnabled(True)
        elif state == 1:
            self.b_gui.setChecked(True)
            self.b_gui.setEnabled(True)
        elif state == -1:
            self.b_gui.setChecked(False)
            self.b_gui.setEnabled(False)
        self.b_gui.blockSignals(False)

    def parameterActivityChanged(self, onOff):
        if self.led_control is None:
            return

        self.led_control.setChecked(onOff)

    def midiActivityChanged(self, onOff):
        if self.led_midi is None:
            return

        self.led_midi.setChecked(onOff)

    def optionChanged(self, option, yesNo):
        pass

    def editDialogVisibilityChanged(self, pluginId, visible):
        if self.b_edit is None:
            return

        self.b_edit.blockSignals(True)
        self.b_edit.setChecked(visible)
        self.b_edit.blockSignals(False)

    def editDialogPluginHintsChanged(self, pluginId, hints):
        self.fPluginInfo['hints'] = hints

        for paramIndex, paramWidget in self.fParameterList:
            if paramIndex == PARAMETER_DRYWET:
                paramWidget.setVisible(hints & PLUGIN_CAN_DRYWET)
            elif paramIndex == PARAMETER_VOLUME:
                paramWidget.setVisible(hints & PLUGIN_CAN_VOLUME)

        if self.b_gui is not None:
            self.b_gui.setEnabled(bool(hints & PLUGIN_HAS_CUSTOM_UI))

    def editDialogParameterValueChanged(self, pluginId, parameterId, value):
        for paramIndex, paramWidget in self.fParameterList:
            if paramIndex != parameterId:
                continue

            paramWidget.blockSignals(True)
            paramWidget.setValue(value)
            paramWidget.blockSignals(False)
            break

    def editDialogProgramChanged(self, pluginId, index):
        if self.cb_presets is None:
            return

        self.cb_presets.blockSignals(True)
        self.cb_presets.setCurrentIndex(index)
        self.cb_presets.blockSignals(False)
        self.updateParameterValues()

    def editDialogMidiProgramChanged(self, pluginId, index):
        if self.cb_presets is None:
            return

        self.cb_presets.blockSignals(True)
        self.cb_presets.setCurrentIndex(index)
        self.cb_presets.blockSignals(False)
        self.updateParameterValues()

    def editDialogNotePressed(self, pluginId, note):
        pass

    def editDialogNoteReleased(self, pluginId, note):
        pass

    def editDialogMidiActivityChanged(self, pluginId, onOff):
        self.midiActivityChanged(onOff)

    def idleFast(self):
        if not self.isVisible():
            return

        if self.fPeaksInputCount > 0:
            if self.fPeaksInputCount > 1:
                peak1 = self.host.get_input_peak_value(self.fPluginId, True)
                peak2 = self.host.get_input_peak_value(self.fPluginId, False)
                ledState = bool(peak1 != 0.0 or peak2 != 0.0)

                if self.peak_in is not None:
                    self.peak_in.displayMeter(1, peak1)
                    self.peak_in.displayMeter(2, peak2)
            else:
                peak = self.host.get_input_peak_value(self.fPluginId, True)
                ledState = bool(peak != 0.0)

                if self.peak_in is not None:
                    self.peak_in.displayMeter(1, peak)

            if self.fLastGreenLedState != ledState and self.led_audio_in is not None:
                self.fLastGreenLedState = ledState
                self.led_audio_in.setChecked(ledState)

        if self.fPeaksOutputCount > 0:
            if self.fPeaksOutputCount > 1:
                peak1 = self.host.get_output_peak_value(self.fPluginId, True)
                peak2 = self.host.get_output_peak_value(self.fPluginId, False)
                ledState = bool(peak1 != 0.0 or peak2 != 0.0)

                if self.peak_out is not None:
                    self.peak_out.displayMeter(1, peak1)
                    self.peak_out.displayMeter(2, peak2)
            else:
                peak = self.host.get_output_peak_value(self.fPluginId, True)
                ledState = bool(peak != 0.0)

                if self.peak_out is not None:
                    self.peak_out.displayMeter(1, peak)

            if self.fLastBlueLedState != ledState and self.led_audio_out is not None:
                self.fLastBlueLedState = ledState
                self.led_audio_out.setChecked(ledState)

    def idleSlow(self):
        if not self.isVisible() and (self.fEditDialog is None or not self.fEditDialog.isVisible()):
            return

        if self.fParameterIconTimer == ICON_STATE_ON:
            self.parameterActivityChanged(True)
            self.fParameterIconTimer = ICON_STATE_WAIT

        elif self.fParameterIconTimer == ICON_STATE_WAIT:
            self.fParameterIconTimer = ICON_STATE_OFF

        elif self.fParameterIconTimer == ICON_STATE_OFF:
            self.parameterActivityChanged(False)
            self.fParameterIconTimer = ICON_STATE_NULL

        if self.fEditDialog is not None:
            self.fEditDialog.idleSlow()

    def drawOutline(self, painter):
        painter.save()
        painter.setBrush(Qt.transparent)
        w = float(self.width())
        h = float(self.height())

        painter.setPen(self.shadow_pen)
        painter.drawLine(QLineF(0.5, h-1, w-1, h-1))

        if self.fIsSelected:
            painter.setCompositionMode(QPainter.CompositionMode_Plus)

            painter.setPen(self.sel_pen)
            painter.drawRect(QRectF(0.5, 0.5, w-1, h-1))
            sidelines = [QLineF(1, 1, 1, h-1), QLineF(w-1, 1, w-1, h-1)]
            painter.setPen(self.sel_side_pen)
            painter.drawLines(sidelines)

            painter.setCompositionMode(QPainter.CompositionMode_SourceOver)

        painter.restore()

    def updateParameterValues(self):
        for paramIndex, paramWidget in self.fParameterList:
            paramWidget.blockSignals(True)
            if paramIndex < 0:
                paramWidget.setValue(self.host.get_internal_parameter_value(self.fPluginId, paramIndex))
            else:
                paramWidget.setValue(self.host.get_current_parameter_value(self.fPluginId, paramIndex))
            paramWidget.blockSignals(False)

    @pyqtSlot(bool)
    def slot_enableClicked(self, yesNo):
        self.setActive(yesNo, False, True)

    @pyqtSlot()
    def slot_showCustomMenu(self):
        menu = QMenu(self)

        actCompact = menu.addAction(self.tr("Expand") if isinstance(self, PluginSlot_Compact) else self.tr("Minimize"))

        menuAppearance = menu.addMenu(self.tr("Appearance"))

        actSliderMode = menuAppearance.addAction(self.tr("Slider Mode"))
        actSliderMode.setCheckable(True)
        is_sliders = isinstance(self, PluginSlot_Sliders) or self.fSkinStyle.startswith("sliders")
        actSliderMode.setChecked(is_sliders)

        actModernSlice = menuAppearance.addAction(self.tr("Modernized Header Slice"))
        actModernSlice.setCheckable(True)
        is_modern_slice = getattr(self, "is_modernized_slice", False)
        actModernSlice.setChecked(is_modern_slice)

        actDarkMode = menuAppearance.addAction(self.tr("Dark Mode"))
        actDarkMode.setCheckable(True)
        is_dark = getattr(self, "is_dark", True)
        actDarkMode.setChecked(is_dark)

        menuAppearance.addSeparator()

        colorMenu = menuAppearance.addMenu(self.tr("Color"))
        paletteWidget = QWidget()
        palLayout = QHBoxLayout(paletteWidget)
        palLayout.setContentsMargins(6, 4, 6, 4)
        palLayout.setSpacing(4)

        catppuccin_colors = [
            ("#f38ba8", "Red"),
            ("#fab387", "Peach"),
            ("#f9e2af", "Yellow"),
            ("#a6e3a1", "Green"),
            ("#94e2d5", "Teal"),
            ("#89dceb", "Sky"),
            ("#89b4fa", "Blue"),
            ("#b4befe", "Lavender"),
            ("#cba6f7", "Mauve"),
            ("#f5c2e7", "Pink"),
        ]

        btn_reset = QPushButton("✕")
        btn_reset.setToolTip(self.tr("Reset to Default Color"))
        btn_reset.setFixedSize(22, 22)
        btn_reset.setStyleSheet("QPushButton { font-weight: bold; color: #888; background: transparent; border: 1px solid #555; border-radius: 3px; } QPushButton:hover { color: #fff; border-color: #888; background: #333; }")
        btn_reset.clicked.connect(lambda: (gCarla.gui.changePluginColor(self.fPluginId, (255, 255, 255), "255;255;255"), menu.close()))
        palLayout.addWidget(btn_reset)

        for col_hex, col_name in catppuccin_colors:
            btn_col = QPushButton()
            btn_col.setToolTip(col_name)
            btn_col.setFixedSize(22, 22)
            btn_col.setStyleSheet(f"QPushButton {{ background-color: {col_hex}; border: 1px solid rgba(0,0,0,0.4); border-radius: 3px; }} QPushButton:hover {{ border: 2px solid #ffffff; }}")
            c = QColor(col_hex)
            col_tup = (c.red(), c.green(), c.blue())
            col_str = f"{c.red()};{c.green()};{c.blue()}"
            btn_col.clicked.connect(lambda checked=False, t=col_tup, s=col_str: (gCarla.gui.changePluginColor(self.fPluginId, t, s), menu.close()))
            palLayout.addWidget(btn_col)

        colorWidgetAction = QWidgetAction(colorMenu)
        colorWidgetAction.setDefaultWidget(paletteWidget)
        colorMenu.addAction(colorWidgetAction)
        colorMenu.addSeparator()
        actColor = colorMenu.addAction(self.tr("Custom Color..."))
        actResetColor = colorMenu.addAction(self.tr("Reset Color"))

        menu.addSeparator()

        if self.host.processMode in (ENGINE_PROCESS_MODE_MULTIPLE_CLIENTS,
                                     ENGINE_PROCESS_MODE_PATCHBAY):
            actFindInPatchbay = menu.addAction(self.tr("Find plugin in patchbay"))
            menu.addSeparator()
        else:
            actFindInPatchbay = None

        actMoveUp   = menu.addAction(self.tr("Move Up"))
        actMoveDown = menu.addAction(self.tr("Move Down"))

        if self.fPluginId == 0:
            actMoveUp.setEnabled(False)
        if self.fPluginId >= self.fParent.getPluginCount() - 1:
            actMoveDown.setEnabled(False)

        actBypass = menu.addAction(self.tr("Bypass"))
        actEnable = menu.addAction(self.tr("Disable") if self.fIsActive else self.tr("Enable"))
        menu.addSeparator()

        if self.fPluginInfo['hints'] & PLUGIN_CAN_DRYWET:
            actBypass.setCheckable(True)
            actBypass.setChecked(self.host.get_internal_parameter_value(self.fPluginId, PARAMETER_DRYWET) == 0.0)
        else:
            actBypass.setVisible(False)

        actReset  = menu.addAction(self.tr("Reset parameters"))
        actRandom = menu.addAction(self.tr("Randomize parameters"))
        menu.addSeparator()

        actEdit = menu.addAction(self.tr("Edit"))
        actGui  = menu.addAction(self.tr("Show Custom UI"))
        menu.addSeparator()

        if self.b_edit is not None:
            actEdit.setCheckable(True)
            actEdit.setChecked(self.b_edit.isChecked())
        else:
            actEdit.setVisible(False)

        if self.b_gui is not None:
            actGui.setCheckable(True)
            actGui.setChecked(self.b_gui.isChecked())
            actGui.setEnabled(self.b_gui.isEnabled())
        else:
            actGui.setVisible(False)

        actClone   = menu.addAction(self.tr("Clone"))
        actRename  = menu.addAction(self.tr("Rename..."))
        actReplace = menu.addAction(self.tr("Replace..."))
        actRemove  = menu.addAction(self.tr("Remove"))

        if self.fIdleTimerId != 0:
            actRemove.setVisible(False)

        if self.host.exportLV2:
            menu.addSeparator()
            actExportLV2 = menu.addAction(self.tr("Export LV2..."))
        else:
            actExportLV2 = None

        actSel = menu.exec_(QCursor.pos())

        if not actSel:
            return

        elif actSel == actCompact:
            if hasattr(self, 'toggleCompacted'):
                self.toggleCompacted()
            else:
                gCarla.gui.compactPlugin(self.fPluginId)


        elif actSel == actSliderMode:
            new_sliders = actSliderMode.isChecked()
            if hasattr(self, 'setSliderMode'):
                self.setSliderMode(new_sliders)
            else:
                is_dark = getattr(self, "is_dark", True)
                new_skin = ("sliders-dark" if is_dark else "sliders-light") if new_sliders else ("minimal-dark" if is_dark else "minimal-light")
                gCarla.gui.changePluginSkin(self.fPluginId, new_skin)

        elif actSel == actModernSlice:
            new_slice = actModernSlice.isChecked()
            if hasattr(self, 'setModernizedHeaderSlice'):
                self.setModernizedHeaderSlice(new_slice)

        elif actSel == actDarkMode:
            new_dark = actDarkMode.isChecked()
            is_sliders = isinstance(self, PluginSlot_Sliders) or self.fSkinStyle.startswith("sliders")
            if is_sliders:
                new_skin = "sliders-dark" if new_dark else "sliders-light"
            else:
                new_skin = "minimal-dark" if new_dark else "minimal-light"
            gCarla.gui.changePluginSkin(self.fPluginId, new_skin)

        elif actSel == actColor:
            initial = QColor(self.fSkinColor[0], self.fSkinColor[1], self.fSkinColor[2])
            color   = QColorDialog.getColor(initial, self, self.tr("Change Color"), QColorDialog.DontUseNativeDialog)

            if not color.isValid():
                return

            color    = color.getRgb()[0:3]
            colorStr = "%i;%i;%i" % color
            gCarla.gui.changePluginColor(self.fPluginId, color, colorStr)

        elif actSel == actResetColor:
            gCarla.gui.changePluginColor(self.fPluginId, (255, 255, 255), "255;255;255")

        elif actSel == actFindInPatchbay:
            gCarla.gui.findPluginInPatchbay(self.fPluginId)

        elif actSel == actMoveUp:
            gCarla.gui.switchPlugins(self.fPluginId, self.fPluginId-1)

        elif actSel == actMoveDown:
            gCarla.gui.switchPlugins(self.fPluginId, self.fPluginId+1)

        elif actSel == actBypass:
            value = 0.0 if actBypass.isChecked() else 1.0
            self.host.set_drywet(self.fPluginId, value)
            self.setParameterValue(PARAMETER_DRYWET, value, True)

        elif actSel == actEnable:
            self.setActive(not self.fIsActive, True, True)

        elif actSel == actReset:
            self.host.reset_parameters(self.fPluginId)

        elif actSel == actRandom:
            self.host.randomize_parameters(self.fPluginId)

        elif actSel == actEdit:
            self.b_edit.click()

        elif actSel == actGui:
            self.b_gui.click()

        elif actSel == actClone:
            if not self.host.clone_plugin(self.fPluginId):
                CustomMessageBox(self, QMessageBox.Warning, self.tr("Error"), self.tr("Operation failed"),
                                       self.host.get_last_error(), QMessageBox.Ok, QMessageBox.Ok)

        elif actSel == actRename:
            self.showRenameDialog()

        elif actSel == actReplace:
            self.showReplaceDialog()

        elif actSel == actRemove:
            self.slot_removePlugin()

        elif actSel == actExportLV2:
            filepath = QInputDialog.getItem(self, self.tr("Export LV2 Plugin"),
                                                  self.tr("Select LV2 Path where plugin will be exported to:"),
                                                  CARLA_DEFAULT_LV2_PATH, editable=False)
            if not all(filepath):
                return

            plugname = self.fPluginInfo['name']
            filepath = os.path.join(filepath[0], plugname.replace(" ","_"))

            if not filepath.endswith(".lv2"):
                filepath += ".lv2"

            if os.path.exists(filepath):
                if QMessageBox.question(self, self.tr("Export to LV2"),
                                              self.tr("Plugin bundle already exists, overwrite?")) == QMessageBox.Ok:
                    return

            if not self.host.export_plugin_lv2(self.fPluginId, filepath):
                return CustomMessageBox(self, QMessageBox.Warning, self.tr("Error"), self.tr("Operation failed"),
                                              self.host.get_last_error(), QMessageBox.Ok, QMessageBox.Ok)

            QMessageBox.information(self, self.tr("Plugin exported"),
                                          self.tr(f"Plugin exported successfully, saved in folder:\n{filepath}"))

    @pyqtSlot()
    def slot_knobCustomMenu(self):
        sender  = self.sender()
        index   = sender.fIndex
        minimum = sender.fMinimum
        maximum = sender.fMaximum
        current = sender.fRealValue
        label   = sender.fLabel

        if index in (PARAMETER_NULL, PARAMETER_CTRL_CHANNEL) or index <= PARAMETER_MAX:
            return
        elif index in (PARAMETER_DRYWET, PARAMETER_VOLUME):
            default = 1.0
        elif index == PARAMETER_BALANCE_LEFT:
            default = -1.0
        elif index == PARAMETER_BALANCE_RIGHT:
            default = 1.0
        elif index == PARAMETER_PANNING:
            default = 0.0
        else:
            default = self.host.get_default_parameter_value(self.fPluginId, index)

        if index < PARAMETER_NULL:
            textReset = self.tr("Reset (%i%%)"          % round(default*100.0))
            textMinim = self.tr("Set to Minimum (%i%%)" % round(minimum*100.0))
            textMaxim = self.tr("Set to Maximum (%i%%)" % round(maximum*100.0))
        else:
            textReset = self.tr("Reset (%f)"          % default)
            textMinim = self.tr("Set to Minimum (%f)" % minimum)
            textMaxim = self.tr("Set to Maximum (%f)" % maximum)

        menu = QMenu(self)
        actReset = menu.addAction(textReset)
        menu.addSeparator()
        actMinimum = menu.addAction(textMinim)
        actCenter  = menu.addAction(self.tr("Set to Center"))
        actMaximum = menu.addAction(textMaxim)
        menu.addSeparator()
        actSet = menu.addAction(self.tr("Set value..."))

        if index > PARAMETER_NULL or index not in (PARAMETER_BALANCE_LEFT, PARAMETER_BALANCE_RIGHT, PARAMETER_PANNING):
            menu.removeAction(actCenter)

        actSelected = menu.exec_(QCursor.pos())

        if actSelected == actSet:
            if index < PARAMETER_NULL:
                value, ok = QInputDialog.getInt(self, self.tr("Set value"), label, round(current*100), round(minimum*100), round(maximum*100), 1)

                if not ok:
                    return

                value = float(value)/100.0

            else:
                paramInfo   = self.host.get_parameter_info(self.fPluginId, index)
                paramRanges = self.host.get_parameter_ranges(self.fPluginId, index)
                scalePoints = []

                for i in range(paramInfo['scalePointCount']):
                    scalePoints.append(self.host.get_parameter_scalepoint_info(self.fPluginId, index, i))

                prefix = ""
                suffix = paramInfo['unit'].strip()

                if suffix == "(coef)":
                    prefix = "* "
                    suffix = ""
                else:
                    suffix = " " + suffix

                dialog = CustomInputDialog(self, label, current, minimum, maximum,
                                                  paramRanges['step'], paramRanges['stepSmall'], scalePoints, prefix, suffix)

                if not dialog.exec_():
                    return

                value = dialog.returnValue()

        elif actSelected == actMinimum:
            value = minimum
        elif actSelected == actMaximum:
            value = maximum
        elif actSelected == actReset:
            value = default
        elif actSelected == actCenter:
            value = 0.0
        else:
            return

        sender.setValue(value, True)

    @pyqtSlot(bool)
    def slot_showCustomUi(self, show):
        self.host.show_custom_ui(self.fPluginId, show)

    @pyqtSlot(bool)
    def slot_showEditDialog(self, show):
        if show:
            self._ensureEditDialog()
        if self.fEditDialog is not None:
            self.fEditDialog.setVisible(show)

    def keyPressEvent(self, event):
        if event.key() in (Qt.Key_Delete, Qt.Key_Backspace):
            event.accept()
            self.slot_removePlugin()
            return
        super().keyPressEvent(event)

    @pyqtSlot()
    def slot_removePlugin(self):
        name = self.fPluginInfo.get("name", self.tr("this plugin")) if isinstance(self.fPluginInfo, dict) else self.tr("this plugin")
        top_window = self.window() or gCarla.gui or self
        ask = QMessageBox.question(
            top_window,
            self.tr("Remove Plugin"),
            self.tr(f"Are you sure you want to remove '{name}'?"),
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if ask != QMessageBox.Yes:
            return

        if not self.host.remove_plugin(self.fPluginId):
            CustomMessageBox(top_window, QMessageBox.Warning, self.tr("Error"), self.tr("Operation failed"),
                                    self.host.get_last_error(), QMessageBox.Ok, QMessageBox.Ok)

    @pyqtSlot(bool)
    def slot_parameterDragStateChanged(self, touch):
        index = self.sender().getIndex()

        if index >= 0:
            self.host.set_parameter_touch(self.fPluginId, index, touch)

    @pyqtSlot(float)
    def slot_parameterValueChanged(self, value):
        index = self.sender().getIndex()

        if index < 0:
            self.setInternalParameter(index, value)
        else:
            self.host.set_parameter_value(self.fPluginId, index, value)
            self.setParameterValue(index, value, False)

        if hasattr(gCarla, "gui") and gCarla.gui is not None:
            gCarla.gui.fHasUnsavedChanges = True

    @pyqtSlot(int)
    def slot_programChanged(self, index):
        self.host.set_program(self.fPluginId, index)
        self.setProgram(index, False)

    @pyqtSlot(int)
    def slot_midiProgramChanged(self, index):
        self.host.set_midi_program(self.fPluginId, index)
        self.setMidiProgram(index, False)

    def updateRackItemSize(self):
        h = self.getFixedHeight()
        self.setFixedHeight(h)
        if hasattr(gCarla, "gui") and gCarla.gui is not None:
            pitem = gCarla.gui.getPluginItem(self.fPluginId)
            if pitem is not None:
                current_hint = pitem.sizeHint()
                if current_hint.height() != h:
                    w = current_hint.width() if current_hint.width() > 0 else 200
                    pitem.setSizeHint(QSize(w, h))
                    if hasattr(gCarla.gui, "ui") and hasattr(gCarla.gui.ui, "listWidget") and gCarla.gui.ui.listWidget is not None:
                        gCarla.gui.ui.listWidget.scheduleDelayedItemsLayout()

    def adjustViewableKnobCount(self):
        if self.w_knobs_left is None:
            return

        layout = self.w_knobs_left.layout()
        if layout is None:
            return

        if getattr(self, 'is_compacted', False) or getattr(self, 'is_slider_mode', False) or not self.w_knobs_left.isVisible():
            self.fAdjustViewableKnobCountScheduled = False
            return

        if self.w_knobs_left.width() <= 10:
            self.fAdjustViewableKnobCountScheduled = True
            QTimer.singleShot(50, self.adjustViewableKnobCount)
            return

        for _, widget in self.fParameterList:
            widget.show()

        self.w_knobs_left.updateGeometry()
        if self.w_knobs_left.parentWidget():
            self.w_knobs_left.parentWidget().updateGeometry()

        self.updateRackItemSize()
        self.fAdjustViewableKnobCountScheduled = False

    def testTimer(self):
        self.fIdleTimerId = self.startTimer(25)

    def showEvent(self, event):
        QFrame.showEvent(self, event)
        if not self.fAdjustViewableKnobCountScheduled:
            self.fAdjustViewableKnobCountScheduled = True
            QTimer.singleShot(50, self.adjustViewableKnobCount)

    def mouseDoubleClickEvent(self, event):
        QFrame.mouseDoubleClickEvent(self, event)
        gCarla.gui.compactPlugin(self.fPluginId)

    def closeEvent(self, event):
        if self.fIdleTimerId != 0:
            self.killTimer(self.fIdleTimerId)
            self.fIdleTimerId = 0
            if self.parentWidget() is None:
                self.host.engine_close()

        QFrame.closeEvent(self, event)

    def resizeEvent(self, event):
        if not self.fAdjustViewableKnobCountScheduled:
            self.fAdjustViewableKnobCountScheduled = True
            QTimer.singleShot(100, self.adjustViewableKnobCount)
        if self.height() != self.getFixedHeight():
            self.updateRackItemSize()
        QFrame.resizeEvent(self, event)

    def timerEvent(self, event):
        if event.timerId() == self.fIdleTimerId:
            self.host.engine_idle()
            self.idleFast()
            self.idleSlow()

        QFrame.timerEvent(self, event)

    def paintEvent(self, event):
        painter = QPainter(self)

        if self.fSkinColor != (0,0,0):
            painter.setCompositionMode(QPainter.CompositionMode_Multiply)
            r,g,b = self.fSkinColor
            painter.setBrush(QColor(r,g,b))
            painter.setPen(Qt.NoPen)
            painter.drawRect(QRectF(0,0,self.width(),self.height()))
            painter.setCompositionMode(QPainter.CompositionMode_SourceOver)

        self.drawOutline(painter)
        QFrame.paintEvent(self, event)

# ------------------------------------------------------------------------------------------------------------

class PluginSlot_Calf(AbstractPluginSlot):
    def __init__(self, parent, host, pluginId, skinColor, skinStyle):
        AbstractPluginSlot.__init__(self, parent, host, pluginId, skinColor, skinStyle)
        self.ui = ui_carla_plugin_calf.Ui_PluginWidget()
        self.ui.setupUi(self)

        audioCount = self.host.get_audio_port_count_info(self.fPluginId)
        midiCount  = self.host.get_midi_port_count_info(self.fPluginId)

        self.fButtonFont = self.ui.b_gui.font()
        self.fButtonFont.setBold(False)
        self.fButtonFont.setPixelSize(10)

        self.fButtonColorOn  = QColor( 18,  41,  87)
        self.fButtonColorOff = QColor(150, 150, 150)

        self.ui.label_active.setFont(self.fButtonFont)

        self.ui.b_remove.setPixmaps(":/bitmaps/button_calf1.png",
                                    ":/bitmaps/button_calf1_down.png",
                                    ":/bitmaps/button_calf1_hover.png")

        self.ui.b_edit.setTopText(self.tr("Edit"), self.fButtonColorOn, self.fButtonFont)
        self.ui.b_remove.setTopText(self.tr("Remove"), self.fButtonColorOn, self.fButtonFont)

        if self.fPluginInfo['hints'] & PLUGIN_HAS_CUSTOM_UI:
            self.ui.b_gui.setTopText(self.tr("GUI"), self.fButtonColorOn, self.fButtonFont)
        else:
            self.ui.b_gui.setTopText(self.tr("GUI"), self.fButtonColorOff, self.fButtonFont)

        if audioCount['ins'] == 0:
            self.ui.label_audio_in.hide()

        if audioCount['outs'] == 0:
            self.ui.label_audio_out.hide()

        if midiCount['ins'] == 0:
            self.ui.label_midi.hide()
            self.ui.led_midi.hide()

        if self.fIdleTimerId != 0:
            self.ui.b_remove.setEnabled(False)
            self.ui.b_remove.setVisible(False)

        self.b_enable = self.ui.b_enable
        self.b_gui    = self.ui.b_gui
        self.b_edit   = self.ui.b_edit
        self.b_remove = self.ui.b_remove
        if self.b_remove is not None:
            self.b_remove.clicked.connect(self.slot_removePlugin)

        self.label_name = self.ui.label_name
        self.led_midi   = self.ui.led_midi

        self.peak_in  = self.ui.peak_in
        self.peak_out = self.ui.peak_out

        self.w_knobs_left = self.ui.w_knobs
        self.spacer_knobs = self.ui.layout_bottom.itemAt(1).spacerItem()

        self.ready()
        self.ui.led_midi.setColor(self.ui.led_midi.CALF)

    def getFixedHeight(self):
        return 94 if max(self.peak_in.channelCount(), self.peak_out.channelCount()) < 2 else 106

    def editDialogPluginHintsChanged(self, pluginId, hints):
        if hints & PLUGIN_HAS_CUSTOM_UI:
            self.ui.b_gui.setTopText(self.tr("GUI"), self.fButtonColorOn, self.fButtonFont)
        else:
            self.ui.b_gui.setTopText(self.tr("GUI"), self.fButtonColorOff, self.fButtonFont)

        AbstractPluginSlot.editDialogPluginHintsChanged(self, pluginId, hints)

    def paintEvent(self, event):
        isBlack = bool(self.fSkinStyle == "calf_black")

        painter = QPainter(self)
        painter.setBrush(Qt.transparent)

        painter.setPen(QPen(QColor(20, 20, 20) if isBlack else QColor(75, 86, 99), 1))
        painter.drawRect(0, 1, self.width()-1, self.height()-3)

        painter.setPen(QPen(QColor(45, 45, 45) if isBlack else QColor(86, 99, 114), 1))
        painter.drawLine(0, 0, self.width(), 0)

        AbstractPluginSlot.paintEvent(self, event)

# ------------------------------------------------------------------------------------------------------------

class PluginSlot_Classic(AbstractPluginSlot):
    def __init__(self, parent, host, pluginId):
        AbstractPluginSlot.__init__(self, parent, host, pluginId, (0,0,0), "classic")
        self.ui = ui_carla_plugin_classic.Ui_PluginWidget()
        self.ui.setupUi(self)

        self.fColorTop    = QColor(60, 60, 60)
        self.fColorBottom = QColor(47, 47, 47)
        self.fColorSeprtr = QColor(70, 70, 70)

        self.b_enable = self.ui.b_enable
        self.b_gui    = self.ui.b_gui
        self.b_edit   = self.ui.b_edit

        self.label_name    = self.ui.label_name
        self.led_control   = self.ui.led_control
        self.led_midi      = self.ui.led_midi
        self.led_audio_in  = self.ui.led_audio_in
        self.led_audio_out = self.ui.led_audio_out

        self.peak_in  = self.ui.peak_in
        self.peak_out = self.ui.peak_out

        self.ready()

    def getFixedHeight(self):
        return 36

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.save()

        areaX  = self.ui.area_right.x()+7
        width  = self.width()
        height = self.height()

        painter.setPen(QPen(QColor(17, 17, 17), 1))
        painter.setBrush(QColor(17, 17, 17))
        painter.drawRect(0, 0, width, height)

        painter.setPen(self.fColorSeprtr.lighter(110))
        painter.setBrush(self.fColorBottom)
        painter.setRenderHint(QPainter.Antialiasing, True)

        path = QPainterPath()
        path.moveTo(areaX-20, height-4)
        path.cubicTo(areaX, height-5, areaX-20, 4.75, areaX, 4.75)
        path.lineTo(areaX, height-5)
        painter.drawPath(path)

        painter.setPen(self.fColorSeprtr)
        painter.setRenderHint(QPainter.Antialiasing, False)

        painter.drawLine(0, height-5, areaX-20, height-5)
        painter.drawLine(areaX, 4, width, 4)

        painter.setPen(self.fColorBottom)
        painter.setBrush(self.fColorBottom)

        painter.drawLine(0, 0, width, 0)
        painter.drawRect(0, height-4, areaX, 4)
        painter.drawRoundedRect(areaX-20, height-5, areaX, 5, 22, 22)
        painter.drawLine(0, 0, 0, height)

        painter.drawRect(areaX-1, 5, width, height)

        painter.setPen(self.fColorSeprtr)
        painter.drawLine(0, height-1, width, height-1)

        painter.restore()
        AbstractPluginSlot.paintEvent(self, event)

# ------------------------------------------------------------------------------------------------------------

class PluginSlot_Compact(AbstractPluginSlot):
    def __init__(self, parent, host, pluginId, skinColor, skinStyle):
        AbstractPluginSlot.__init__(self, parent, host, pluginId, skinColor, skinStyle)
        self.ui = ui_carla_plugin_compact.Ui_PluginWidget()
        self.ui.setupUi(self)
        self.ui.horizontalLayout_2.setContentsMargins(14, 3, 6, 3)

        self.is_dark = skinStyle in ("minimal-dark", "sliders-dark") or "light" not in skinStyle
        p = CATPPUCCIN_MOCHA if self.is_dark else CATPPUCCIN_LATTE

        if skinColor != (0, 0, 0) and skinColor != (255, 255, 255):
            bg_r, bg_g, bg_b = skinColor
            if self.is_dark:
                bg_r = int(0.80 * 24 + 0.20 * bg_r)
                bg_g = int(0.80 * 24 + 0.20 * bg_g)
                bg_b = int(0.80 * 37 + 0.20 * bg_b)
            else:
                bg_r = int(0.85 * 230 + 0.15 * bg_r)
                bg_g = int(0.85 * 233 + 0.15 * bg_g)
                bg_b = int(0.85 * 239 + 0.15 * bg_b)
        else:
            if self.is_dark:
                bg_r, bg_g, bg_b = 24, 24, 37
            else:
                bg_r, bg_g, bg_b = 230, 233, 239

        self.minimal_bg_color = QColor(bg_r, bg_g, bg_b)
        self.border_color = QColor(p['surface0'])
        self.selection_color = QColor(p['lavender'])

        text_color = p['text']
        text_disabled = p['overlay0']
        badge_bg = "rgba(203, 166, 247, 0.12)" if self.is_dark else "rgba(136, 57, 239, 0.10)"
        badge_text = p['mauve']
        bypass_active = p['peach']

        self.b_enable = self.ui.b_enable
        self.b_gui    = self.ui.b_gui
        self.b_edit   = self.ui.b_edit

        self.label_name = self.ui.label_name

        self.led_control   = self.ui.led_control
        self.led_midi      = self.ui.led_midi
        self.led_audio_in  = self.ui.led_audio_in
        self.led_audio_out = self.ui.led_audio_out

        self.peak_in  = self.ui.peak_in
        self.peak_out = self.ui.peak_out

        self.ui.w_buttons.setMinimumSize(0, 24)
        self.ui.w_buttons.setMaximumSize(16777215, 24)
        self.ui.horizontalLayout.setSpacing(4)

        self.b_bypass = QPushButton("BYP", parent=self.ui.w_buttons)
        self.b_bypass.setObjectName("btn_bypass")
        self.b_bypass.setMinimumSize(32, 22)
        self.b_bypass.setMaximumSize(38, 22)
        self.b_bypass.setFlat(True)
        self.b_bypass.setCheckable(True)

        if bool(self.getHints() & PLUGIN_CAN_DRYWET):
            is_bypassed = bool(self.host.get_internal_parameter_value(self.fPluginId, PARAMETER_DRYWET) == 0.0)
            self._update_bypass_state(is_bypassed)
            def _on_bypass_clicked(checked):
                bypassed = self.b_bypass.isChecked()
                val = 0.0 if bypassed else 1.0
                self.host.set_drywet(self.fPluginId, val)
                self.setParameterValue(PARAMETER_DRYWET, val, True)
                self._update_bypass_state(bypassed)
            self.b_bypass.clicked.connect(_on_bypass_clicked)
        else:
            self.b_bypass.hide()

        self.ui.horizontalLayout.insertWidget(1, self.b_bypass)

        plugin_type_str = getPluginTypeAsString(self.fPluginInfo['type'])
        self.label_badge = QLabel(f" {plugin_type_str} ", parent=self)
        self.label_badge.setObjectName("label_badge")
        idx = self.ui.horizontalLayout_2.indexOf(self.label_name)
        if idx >= 0:
            self.ui.horizontalLayout_2.insertWidget(idx + 1, self.label_badge)

        self.b_expand = QPushButton("▼", parent=self)
        self.b_expand.setFlat(True)
        self.b_expand.setObjectName("btn_expand")
        self.b_expand.setMinimumSize(22, 20)
        self.b_expand.setMaximumSize(24, 20)
        self.b_expand.setToolTip("Expand")
        self.b_expand.clicked.connect(lambda _=None: gCarla.gui.compactPlugin(self.fPluginId))
        self.ui.horizontalLayout_2.addWidget(self.b_expand)

        if not bool(self.getHints() & PLUGIN_HAS_CUSTOM_UI):
            self.b_gui.hide()

        styleSheet = f"""
            QFrame#PluginWidget {{
                background: transparent;
            }}
            QPushButton {{
                background: rgba(255, 255, 255, 0.05);
                border: 1px solid rgba(255, 255, 255, 0.12);
                color: {p['subtext0']};
                font-size: 10px;
                font-weight: 700;
                padding: 2px 6px;
                border-radius: 3px;
            }}
            QPushButton:hover {{
                background: rgba(255, 255, 255, 0.13);
                border-color: rgba(255, 255, 255, 0.35);
                color: {p['text']};
            }}
            QPushButton:pressed {{
                background: rgba(255, 255, 255, 0.25);
                border-color: rgba(255, 255, 255, 0.6);
                color: #ffffff;
            }}
            QPushButton#btn_bypass {{
                background: rgba(255, 255, 255, 0.05);
                border: 1px solid rgba(255, 255, 255, 0.12);
                font-size: 10px;
                font-weight: 700;
                color: {p['overlay1']};
                padding: 2px 6px;
                border-radius: 3px;
            }}
            QPushButton#btn_bypass:hover {{
                color: {p['text']};
                background: rgba(255, 255, 255, 0.13);
                border-color: rgba(255, 255, 255, 0.35);
            }}
            QPushButton#btn_bypass:checked {{
                background: rgba(250, 179, 135, 0.18);
                border: 1px solid rgba(250, 179, 135, 0.45);
                color: {bypass_active};
                font-weight: 800;
            }}
            QPushButton#btn_bypass:checked:hover {{
                color: {p['yellow']};
                background: rgba(250, 179, 135, 0.28);
                border-color: rgba(250, 179, 135, 0.65);
            }}
            QPushButton#btn_expand, QPushButton#btn_minimize {{
                background: rgba(255, 255, 255, 0.04);
                border: 1px solid rgba(255, 255, 255, 0.10);
                color: {p['overlay1']};
                font-size: 11px;
                font-weight: bold;
                min-width: 20px;
                max-width: 24px;
                min-height: 20px;
                max-height: 22px;
                padding: 0px;
                border-radius: 3px;
            }}
            QPushButton#btn_expand:hover, QPushButton#btn_minimize:hover {{
                background: rgba(255, 255, 255, 0.13);
                border-color: rgba(255, 255, 255, 0.35);
                color: {p['text']};
            }}
            QPushButton#btn_expand:pressed, QPushButton#btn_minimize:pressed {{
                background: rgba(255, 255, 255, 0.25);
                color: #ffffff;
            }}
            QLabel#label_name {{
                font-size: 11px;
                font-weight: bold;
                color: {text_color};
            }}
            QLabel#label_name:disabled {{
                color: {text_disabled};
            }}
            QLabel#label_badge {{
                background-color: {badge_bg};
                border: none;
                border-radius: 4px;
                padding: 2px 6px;
                font-size: 9px;
                font-weight: bold;
                color: {badge_text};
            }}
        """
        self.setStyleSheet(styleSheet)
        self.ready()
        self.updateRackItemSize()

    def _update_bypass_state(self, is_bypassed):
        if not hasattr(self, 'b_bypass') or self.b_bypass is None:
            return
        self.b_bypass.blockSignals(True)
        self.b_bypass.setChecked(is_bypassed)
        self.b_bypass.setText("BYP")
        if is_bypassed:
            self.b_bypass.setToolTip("Bypassed (Dry/Wet = 0%) - Click to activate")
        else:
            self.b_bypass.setToolTip("Active (Dry/Wet = 100%) - Click to bypass")
        self.b_bypass.blockSignals(False)

    def toggleCompacted(self):
        if hasattr(gCarla, 'gui') and gCarla.gui is not None:
            gCarla.gui.compactPlugin(self.fPluginId)

    def getFixedHeight(self):
        return 34

    def setParameterValue(self, parameterId, value, sendCallback):
        AbstractPluginSlot.setParameterValue(self, parameterId, value, sendCallback)
        if parameterId == PARAMETER_DRYWET and hasattr(self, "_update_bypass_state"):
            self._update_bypass_state(value == 0.0)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        w = float(self.width())
        h = float(self.getFixedHeight())
        rect = QRectF(1.0, 1.0, w - 2.0, h - 2.0)

        painter.setBrush(self.minimal_bg_color)
        painter.setPen(QPen(self.border_color, 1.0))
        painter.drawRoundedRect(rect, 6.0, 6.0)

        stripePath = QPainterPath()
        stripePath.addRoundedRect(QRectF(3.0, 4.0, 3.5, h - 8.0), 1.75, 1.75)
        categoryColor = QColor(self.fSkinColor[0], self.fSkinColor[1], self.fSkinColor[2])
        if categoryColor.red() == 0 and categoryColor.green() == 0 and categoryColor.blue() == 0:
            catRgb = getColorFromCategory(self.fPluginInfo['category'])
            categoryColor = QColor(*catRgb)
        painter.fillPath(stripePath, categoryColor)

        if self.fIsSelected:
            selPen = QPen(self.selection_color, 1.8)
            painter.setPen(selPen)
            painter.setBrush(Qt.NoBrush)
            painter.drawRoundedRect(rect, 6.0, 6.0)

        QFrame.paintEvent(self, event)

class PluginSlot_Default(AbstractPluginSlot):
    def __init__(self, parent, host, pluginId, skinColor, skinStyle):
        AbstractPluginSlot.__init__(self, parent, host, pluginId, skinColor, skinStyle)
        self.ui = ui_carla_plugin_default.Ui_PluginWidget()
        self.ui.setupUi(self)

        self.b_enable = self.ui.b_enable
        self.b_gui    = self.ui.b_gui
        self.b_edit   = self.ui.b_edit

        self.label_name = self.ui.label_name

        self.led_control   = self.ui.led_control
        self.led_midi      = self.ui.led_midi
        self.led_audio_in  = self.ui.led_audio_in
        self.led_audio_out = self.ui.led_audio_out

        self.peak_in  = self.ui.peak_in
        self.peak_out = self.ui.peak_out

        self.w_knobs_left  = self.ui.w_knobs_left
        self.w_knobs_right = self.ui.w_knobs_right
        self.spacer_knobs  = self.ui.layout_bottom.itemAt(1).spacerItem()

        self.ready()

    def getFixedHeight(self):
        return 80

    def paintEvent(self, event):
        AbstractPluginSlot.paintEvent(self, event)

class SliderParamWidget(QWidget):
    realValueChanged = pyqtSignal(float)
    dragStateChanged = pyqtSignal(bool)

    def __init__(self, parent, index, name, min_val, max_val, is_integer, full_name="", is_mini=False, accent_color=None):
        QWidget.__init__(self, parent)
        self.fIndex = index
        self.fName = name
        self.fFullName = full_name or name
        self.fMinimum = min_val
        self.fMaximum = max_val
        self.fIsInteger = is_integer
        self.fIsMini = None
        self.fAccentColor = accent_color

        self.grid_layout = QGridLayout(self)
        self.grid_layout.setContentsMargins(3, 1, 3, 1)
        self.grid_layout.setSpacing(4)

        self.label = QLabel(name)
        self.label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        f = self.label.font()
        f.setPointSize(8)
        f.setBold(True)
        self.label.setFont(f)
        if accent_color:
            self.label.setStyleSheet(f"color: {accent_color}; font-weight: bold;")

        self.slider = QSlider(Qt.Horizontal)
        self.slider.setMinimum(0)
        self.slider.setMaximum(1000)
        self.slider.setSingleStep(20)
        self.slider.setPageStep(50)
        self.slider.setMinimumWidth(80)
        self.slider.setMaximumHeight(14)
        if accent_color:
            self.slider.setStyleSheet(f"""
                QSlider::sub-page:horizontal {{
                    background: {accent_color};
                    height: 4px;
                    border-radius: 2px;
                }}
                QSlider::handle:horizontal {{
                    border: 1px solid {accent_color};
                }}
            """)

        self.spinbox = QDoubleSpinBox()
        self.spinbox.setFrame(False)
        self.spinbox.setMinimum(min_val)
        self.spinbox.setMaximum(max_val)
        self.spinbox.setDecimals(0 if is_integer else 2)
        self.spinbox.setButtonSymbols(QAbstractSpinBox.NoButtons)
        self.spinbox.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.spinbox.setFont(f)
        fm = self.spinbox.fontMetrics()
        self.fSpinMinW = fm.horizontalAdvance("00000") if hasattr(fm, "horizontalAdvance") else fm.width("00000")
        self.spinbox.setMinimumWidth(self.fSpinMinW)
        if hasattr(self.spinbox, "lineEdit") and self.spinbox.lineEdit() is not None:
            self.spinbox.lineEdit().setAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self.spinbox.lineEdit().setContentsMargins(0, 0, 0, 0)
            self.spinbox.lineEdit().setMinimumWidth(self.fSpinMinW)
        step = 1.0 if is_integer else max(0.01, (max_val - min_val) / 100.0)
        self.spinbox.setSingleStep(step)
        self.spinbox.setFixedHeight(20)

        self.slider.valueChanged.connect(self._on_slider)
        self.spinbox.valueChanged.connect(self._on_spinbox)

        self.fRealValue = min_val
        self.setIsMini(is_mini)
        self._updateTooltip()

    def setIsMini(self, is_mini):
        is_mini = bool(is_mini)
        if self.fIsMini == is_mini:
            return
        self.fIsMini = is_mini

        self.grid_layout.removeWidget(self.label)
        self.grid_layout.removeWidget(self.slider)
        self.grid_layout.removeWidget(self.spinbox)

        if self.fIsMini:
            self.setFixedHeight(34)
            self.label.setMinimumWidth(0)
            self.label.setMaximumWidth(16777215)
            self.spinbox.setMinimumWidth(self.fSpinMinW)
            self.spinbox.setMaximumWidth(16777215)
            self.grid_layout.setColumnStretch(0, 1)
            self.grid_layout.setColumnStretch(1, 0)
            self.grid_layout.setColumnStretch(2, 0)
            self.grid_layout.addWidget(self.label, 0, 0, 1, 1, Qt.AlignLeft | Qt.AlignVCenter)
            self.grid_layout.addWidget(self.spinbox, 0, 1, 1, 1, Qt.AlignRight | Qt.AlignVCenter)
            self.grid_layout.addWidget(self.slider, 1, 0, 1, 2)
        else:
            self.setFixedHeight(22)
            self.label.setFixedWidth(70)
            self.spinbox.setMinimumWidth(self.fSpinMinW)
            self.spinbox.setMaximumWidth(self.fSpinMinW + 24)
            self.grid_layout.setColumnStretch(0, 0)
            self.grid_layout.setColumnStretch(1, 1)
            self.grid_layout.setColumnStretch(2, 0)
            self.grid_layout.addWidget(self.label, 0, 0, 1, 1, Qt.AlignLeft | Qt.AlignVCenter)
            self.grid_layout.addWidget(self.slider, 0, 1, 1, 1)
            self.grid_layout.addWidget(self.spinbox, 0, 2, 1, 1, Qt.AlignRight | Qt.AlignVCenter)
        self._updateTooltip()

    def _updateTooltip(self):
        val_str = f"{self.fRealValue:.2f}"
        if val_str.endswith(".00"):
            val_str = val_str[:-3]
        elif val_str[-1] == '0':
            val_str = val_str[:-1]
        tip = f"{self.fFullName} ({val_str})"
        self.label.setToolTip(tip)
        self.slider.setToolTip(tip)
        self.spinbox.setToolTip(tip)

    def getIndex(self):
        return self.fIndex

    def blockSignals(self, block):
        self.slider.blockSignals(block)
        self.spinbox.blockSignals(block)
        QWidget.blockSignals(self, block)

    def setValue(self, value, emitSignal=False):
        self.fRealValue = value

        self.slider.blockSignals(True)
        self.spinbox.blockSignals(True)

        slider_val = int((value - self.fMinimum) / (self.fMaximum - self.fMinimum) * 1000.0) if self.fMaximum > self.fMinimum else 0
        self.slider.setValue(slider_val)
        self.spinbox.setValue(value)

        self.spinbox.blockSignals(False)
        self.slider.blockSignals(False)
        self._updateTooltip()

        if emitSignal:
            self.realValueChanged.emit(self.fRealValue)

    def _on_slider(self, value):
        val = (value / 1000.0) * (self.fMaximum - self.fMinimum) + self.fMinimum
        if self.fIsInteger:
            val = round(val)
        self.fRealValue = val
        self.spinbox.blockSignals(True)
        self.spinbox.setValue(val)
        self.spinbox.blockSignals(False)
        self._updateTooltip()
        if hasattr(gCarla, "gui") and gCarla.gui is not None:
            gCarla.gui.fHasUnsavedChanges = True
        self.realValueChanged.emit(self.fRealValue)

    def _on_spinbox(self, value):
        self.fRealValue = value
        slider_val = int((value - self.fMinimum) / (self.fMaximum - self.fMinimum) * 1000.0) if self.fMaximum > self.fMinimum else 0
        self.slider.blockSignals(True)
        self.slider.setValue(slider_val)
        self.slider.blockSignals(False)
        self._updateTooltip()
        if hasattr(gCarla, "gui") and gCarla.gui is not None:
            gCarla.gui.fHasUnsavedChanges = True
        self.realValueChanged.emit(self.fRealValue)

# ------------------------------------------------------------------------------------------------------------

class PluginSlot_Minimal(PluginSlot_Default):
    def __init__(self, parent, host, pluginId, skinColor, skinStyle):
        PluginSlot_Default.__init__(self, parent, host, pluginId, skinColor, skinStyle)

        self.is_dark = skinStyle in ("minimal-dark", "sliders-dark") or "light" not in skinStyle
        self.is_slider_mode = isinstance(self, PluginSlot_Sliders) or skinStyle.startswith("sliders")
        self.is_compacted = False
        self.is_layer_mode = False
        self.show_mini_params = False
        self.scroll_area = None
        self.sliders_container = None
        self.fSliderParameterList = []
        self.mini_params_tray = None
        self.mini_scroll_area = None
        self.w_subrow = None
        self.fMiniSliderParameterList = []

        p = get_active_skin_palette(self.is_dark)
        has_custom_color = (skinColor != (0, 0, 0) and skinColor != (255, 255, 255))

        if has_custom_color:
            bg_r, bg_g, bg_b = skinColor
            if self.is_dark:
                bg_r = int(0.80 * 24 + 0.20 * bg_r)
                bg_g = int(0.80 * 24 + 0.20 * bg_g)
                bg_b = int(0.80 * 37 + 0.20 * bg_b)
            else:
                bg_r = int(0.85 * 230 + 0.15 * bg_r)
                bg_g = int(0.85 * 233 + 0.15 * bg_g)
                bg_b = int(0.85 * 239 + 0.15 * bg_b)
            accent_color = f"rgb({skinColor[0]}, {skinColor[1]}, {skinColor[2]})"
            arcColor = QColor(skinColor[0], skinColor[1], skinColor[2])
        else:
            if self.is_dark:
                bg_r, bg_g, bg_b = 24, 24, 37
            else:
                bg_r, bg_g, bg_b = 230, 233, 239
            accent_color = p['blue']
            arcColor = QColor(p['blue'])

        self.minimal_bg_color = QColor(bg_r, bg_g, bg_b)
        self.border_color = QColor(p['surface0'])
        self.selection_color = QColor(p['lavender'])

        text_color = p['text']
        text_disabled = p['overlay0']
        badge_bg = "rgba(203, 166, 247, 0.12)" if self.is_dark else "rgba(136, 57, 239, 0.10)"
        badge_text = p['mauve']
        slider_groove = p['surface0']
        slider_track = accent_color
        slider_handle = p['text']
        slider_handle_border = p['blue'] if not has_custom_color else accent_color

        # Create clean QPushButton instances with FontAwesome Nerd Font glyphs for minimal style
        # Power / DSP Active: \uf011
        btn_power = QPushButton("\uf011", parent=self.ui.w_buttons)
        btn_power.setObjectName("btn_power")
        btn_power.setCheckable(True)
        btn_power.setChecked(self.fIsActive)
        btn_power.setMinimumSize(22, 22)
        btn_power.setMaximumSize(22, 22)
        btn_power.setFlat(True)
        btn_power.setToolTip("Power / DSP Active (Toggle DSP processing)")
        btn_power.clicked.connect(self.slot_enableClicked)

        # Bypass (Dry/Wet): \uf05e
        self.b_bypass = QPushButton("\uf05e", parent=self.ui.w_buttons)
        self.b_bypass.setObjectName("btn_bypass")
        self.b_bypass.setMinimumSize(22, 22)
        self.b_bypass.setMaximumSize(22, 22)
        self.b_bypass.setFlat(True)
        self.b_bypass.setCheckable(True)

        if bool(self.getHints() & PLUGIN_CAN_DRYWET):
            is_bypassed = bool(self.host.get_internal_parameter_value(self.fPluginId, PARAMETER_DRYWET) == 0.0)
            self._update_bypass_state(is_bypassed)
            def _on_bypass_clicked(checked):
                bypassed = self.b_bypass.isChecked()
                val = 0.0 if bypassed else 1.0
                self.host.set_drywet(self.fPluginId, val)
                self.setParameterValue(PARAMETER_DRYWET, val, True)
                self._update_bypass_state(bypassed)
            self.b_bypass.clicked.connect(_on_bypass_clicked)
        else:
            self.b_bypass.setEnabled(False)
            self.b_bypass.setToolTip("Bypass: Not supported for this plugin")

        # Custom UI: \uf2d0
        has_custom_ui = bool(self.getHints() & PLUGIN_HAS_CUSTOM_UI)
        btn_gui = QPushButton("\uf2d0", parent=self.ui.w_buttons)
        btn_gui.setObjectName("btn_gui")
        btn_gui.setCheckable(True)
        btn_gui.setChecked(getattr(self.b_gui, "isChecked", lambda: False)())
        btn_gui.setMinimumSize(22, 22)
        btn_gui.setMaximumSize(22, 22)
        btn_gui.setFlat(True)
        btn_gui.setEnabled(has_custom_ui)
        btn_gui.clicked.connect(self.slot_showCustomUi)
        if has_custom_ui:
            btn_gui.setToolTip("Custom UI (Toggle plugin editor window)")
        else:
            btn_gui.setToolTip("Custom UI: Not available for this plugin")

        # Edit Parameters: \uf013
        btn_edit = QPushButton("\uf013", parent=self.ui.w_buttons)
        btn_edit.setObjectName("btn_edit")
        btn_edit.setCheckable(True)
        btn_edit.setChecked(getattr(self.b_edit, "isChecked", lambda: False)())
        btn_edit.setMinimumSize(22, 22)
        btn_edit.setMaximumSize(22, 22)
        btn_edit.setFlat(True)
        btn_edit.setToolTip("Edit Parameters (Open plugin controls and MIDI settings)")
        btn_edit.clicked.connect(self.slot_showEditDialog)

        # Remove old ScalableButtons from horizontalLayout
        for old_b in (self.b_enable, self.b_gui, self.b_edit):
            if old_b is not None:
                self.ui.horizontalLayout.removeWidget(old_b)
                old_b.hide()
                old_b.deleteLater()

        self.b_enable = btn_power
        self.b_gui = btn_gui
        self.b_edit = btn_edit

        self.ui.w_buttons.setMinimumSize(0, 24)
        self.ui.w_buttons.setMaximumSize(16777215, 24)
        self.ui.w_buttons.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        self.ui.horizontalLayout.setContentsMargins(0, 0, 0, 0)
        self.ui.horizontalLayout.setSpacing(1)

        self.ui.horizontalLayout.addWidget(self.b_enable)
        self.ui.horizontalLayout.addWidget(self.b_bypass)
        self.ui.horizontalLayout.addWidget(self.b_gui)
        self.ui.horizontalLayout.addWidget(self.b_edit)

        plugin_cat = self.fPluginInfo.get('category', PLUGIN_CATEGORY_OTHER)
        CATPPUCCIN_CATEGORY_COLORS = {
            PLUGIN_CATEGORY_SYNTH: '#89b4fa',      # Blue
            PLUGIN_CATEGORY_DELAY: '#fab387',      # Peach
            PLUGIN_CATEGORY_EQ: '#a6e3a1',         # Green
            PLUGIN_CATEGORY_FILTER: '#94e2d5',     # Teal
            PLUGIN_CATEGORY_DISTORTION: '#f38ba8', # Red
            PLUGIN_CATEGORY_DYNAMICS: '#cba6f7',   # Mauve
            PLUGIN_CATEGORY_MODULATOR: '#f9e2af',  # Yellow
            PLUGIN_CATEGORY_UTILITY: '#89dceb',    # Sky
            PLUGIN_CATEGORY_OTHER: '#b4befe',      # Lavender
        }
        CATPPUCCIN_CATEGORY_NAMES = {
            PLUGIN_CATEGORY_SYNTH: "Synth",
            PLUGIN_CATEGORY_DELAY: "Delay",
            PLUGIN_CATEGORY_EQ: "EQ",
            PLUGIN_CATEGORY_FILTER: "Filter",
            PLUGIN_CATEGORY_DISTORTION: "Distortion",
            PLUGIN_CATEGORY_DYNAMICS: "Dynamics",
            PLUGIN_CATEGORY_MODULATOR: "Modulator",
            PLUGIN_CATEGORY_UTILITY: "Utility",
            PLUGIN_CATEGORY_OTHER: "FX",
        }
        self.cat_color = CATPPUCCIN_CATEGORY_COLORS.get(plugin_cat, p['mauve'])
        cat_name = CATPPUCCIN_CATEGORY_NAMES.get(plugin_cat, "")
        plugin_type_str = getPluginTypeAsString(self.fPluginInfo['type'])
        type_sub = f"{plugin_type_str} • {cat_name.upper()}" if cat_name else plugin_type_str

        # Title & Type Stack (Vertical 2-line layout)
        self.w_title_stack = QWidget(parent=self)
        self.w_title_stack.setObjectName("w_title_stack")
        self.layout_title_stack = QVBoxLayout(self.w_title_stack)
        self.layout_title_stack.setContentsMargins(0, 0, 0, 0)
        self.layout_title_stack.setSpacing(0)
        self.layout_title_stack.setAlignment(Qt.AlignVCenter)

        self.fFullTitle = self.fPluginInfo['name']
        self.label_name.setToolTip(self.fFullTitle)
        self.label_name.setText(self.fFullTitle)
        self.label_name.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
        self.label_name.setAutoFillBackground(False)
        self.label_name.setStyleSheet("background: transparent;")

        self.label_badge = QLabel(type_sub, parent=self.w_title_stack)
        self.label_badge.setObjectName("label_badge")
        self.label_badge.setAutoFillBackground(False)
        self.label_badge.setToolTip(f"Plugin: {self.fFullTitle} ({type_sub})")
        self.label_badge.setStyleSheet(f"color: {self.cat_color}; font-size: 8px; font-weight: 700; background: transparent; padding: 0px; margin: 0px;")

        self.layout_title_stack.addWidget(self.label_name)
        self.layout_title_stack.addWidget(self.label_badge)

        self.w_title_stack.mouseDoubleClickEvent = lambda ev: self.slot_toggleExpandOrMini()
        self.label_name.mouseDoubleClickEvent = lambda ev: self.slot_toggleExpandOrMini()
        self.label_badge.mouseDoubleClickEvent = lambda ev: self.slot_toggleExpandOrMini()

        # Title Row for Ultra-Thin mode (< 230px)
        self.w_title_row = QWidget(parent=self)
        self.w_title_row.setObjectName("w_title_row")
        self.layout_title_row = QHBoxLayout(self.w_title_row)
        self.layout_title_row.setContentsMargins(0, 0, 0, 0)
        self.layout_title_row.setSpacing(0)

        # Clear legacy items and fixed spacers from layout_top to construct clean flex layout:
        if hasattr(self.ui, 'line_sep') and self.ui.line_sep is not None:
            self.ui.line_sep.hide()
            self.ui.layout_top.removeWidget(self.ui.line_sep)

        for w in (self.ui.w_buttons, self.label_badge, self.label_name):
            self.ui.layout_top.removeWidget(w)

        for i in range(self.ui.layout_top.count() - 1, -1, -1):
            it = self.ui.layout_top.itemAt(i)
            if it and it.spacerItem():
                self.ui.layout_top.removeItem(it)

        # 1. <buttons> at far-left (index 0)
        self.ui.layout_top.insertWidget(0, self.ui.w_buttons)
        # 2. <title stack> (index 1)
        self.ui.layout_top.insertWidget(1, self.w_title_stack)

        # 3. <auto-expanding spacer> (index 2) pushing right controls to the right
        self.spacer_flex = QSpacerItem(8, 1, QSizePolicy.Expanding, QSizePolicy.Minimum)
        self.ui.layout_top.insertItem(2, self.spacer_flex)

        self.setMinimumWidth(160)
        self.ui.layout_top.setSpacing(4)
        self.ui.layout_top.setContentsMargins(0, 0, 0, 0)

        # 4. Row 1 right controls: Slider mode toggle, and unified chevron minimize
        self.b_slider_mode = QPushButton("\uf0c9" if not self.is_slider_mode else "\uf1de", parent=self)
        self.b_slider_mode.setObjectName("btn_slider_mode")
        self.b_slider_mode.setMinimumSize(22, 22)
        self.b_slider_mode.setMaximumSize(22, 22)
        self.b_slider_mode.setFlat(True)
        self.b_slider_mode.setToolTip("Switch to Sliders view" if not self.is_slider_mode else "Switch to Knobs view")
        self.b_slider_mode.clicked.connect(self.slot_toggleSliderMode)
        self.ui.layout_top.addWidget(self.b_slider_mode)

        self.b_minimize = QPushButton("\uf077", parent=self)
        self.b_minimize.setFlat(True)
        self.b_minimize.setObjectName("btn_minimize")
        self.b_minimize.setMinimumSize(22, 22)
        self.b_minimize.setMaximumSize(22, 22)
        self.b_minimize.setToolTip("Minimize / Collapse Rack Slot")
        self.b_minimize.clicked.connect(self.slot_toggleExpandOrMini)
        self.ui.layout_top.addWidget(self.b_minimize)

        # 5. Row 2 (Subrow container) for secondary controls: presets dropdown
        self.w_subrow = QWidget(parent=self)
        self.w_subrow.setObjectName("w_slot_subrow")
        self.layout_subrow = QHBoxLayout(self.w_subrow)
        self.layout_subrow.setContentsMargins(0, 0, 0, 0)
        self.layout_subrow.setSpacing(4)

        top_idx = self.ui.verticalLayout.indexOf(self.ui.layout_top)
        if top_idx >= 0:
            self.ui.verticalLayout.insertWidget(top_idx + 1, self.w_title_row)
            self.ui.verticalLayout.insertWidget(top_idx + 2, self.w_subrow)
        else:
            self.ui.verticalLayout.addWidget(self.w_title_row)
            self.ui.verticalLayout.addWidget(self.w_subrow)
        self.w_title_row.setVisible(False)

        progCount = self.host.get_program_count(self.fPluginId)
        usingMidiPrograms = False
        if progCount == 0:
            progCount = self.host.get_midi_program_count(self.fPluginId)
            usingMidiPrograms = True
        if progCount > 0:
            self.cb_presets = QComboBox(parent=self.w_subrow)
            self.cb_presets.setObjectName("cb_presets")
            self.cb_presets.setMinimumWidth(80)
            self.cb_presets.setMaximumWidth(180)
            self.cb_presets.setFixedHeight(20)
            self.cb_presets.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
            self.cb_presets.setToolTip("Preset Selector")
            curProg = self.host.get_current_midi_program_index(self.fPluginId) if usingMidiPrograms else self.host.get_current_program_index(self.fPluginId)

            # Lazy load: only fetch the current active preset name on startup
            curName = ""
            if 0 <= curProg < progCount:
                curName = self.host.get_midi_program_data(self.fPluginId, curProg)['name'] if usingMidiPrograms else self.host.get_program_name(self.fPluginId, curProg)
            self.cb_presets.addItem(curName or "Default")

            self._presetsLoaded = False
            self._usingMidiPrograms = usingMidiPrograms
            self._progCount = progCount

            def _populate_all_presets():
                if getattr(self, '_presetsLoaded', False):
                    return
                self._presetsLoaded = True
                self.cb_presets.blockSignals(True)
                self.cb_presets.clear()
                for i in range(self._progCount):
                    pname = self.host.get_midi_program_data(self.fPluginId, i)['name'] if self._usingMidiPrograms else self.host.get_program_name(self.fPluginId, i)
                    self.cb_presets.addItem(pname)
                curP = self.host.get_current_midi_program_index(self.fPluginId) if self._usingMidiPrograms else self.host.get_current_program_index(self.fPluginId)
                self.cb_presets.setCurrentIndex(curP)
                self.cb_presets.blockSignals(False)

            self._populate_all_presets = _populate_all_presets
            QTimer.singleShot(250, _populate_all_presets)

            if usingMidiPrograms:
                self.cb_presets.currentIndexChanged.connect(self.slot_midiProgramChanged)
            else:
                self.cb_presets.currentIndexChanged.connect(self.slot_programChanged)
            self.layout_subrow.addWidget(self.cb_presets)

        self.spacer_subrow = QSpacerItem(8, 1, QSizePolicy.Expanding, QSizePolicy.Minimum)
        self.layout_subrow.addItem(self.spacer_subrow)

        self.ui.verticalLayout.setContentsMargins(8, 4, 6, 4)
        self.ui.verticalLayout.setSpacing(2)

        styleSheet = f"""
            QFrame#PluginWidget, QWidget#w_title_stack, QWidget#w_title_row, QWidget#w_slot_subrow, QWidget#w_buttons {{
                background: transparent;
            }}
            QWidget {{
                background: transparent;
            }}
            QPushButton {{
                background: transparent;
                border: none;
                outline: none;
                color: {p['subtext0']};
                font-weight: 700;
                font-size: 13px;
                padding: 0px;
                border-radius: 4px;
            }}
            QPushButton:hover {{
                background: rgba(255, 255, 255, 0.08);
                border: none;
                outline: none;
                color: {p['text']};
            }}
            QPushButton:pressed {{
                background: rgba(255, 255, 255, 0.16);
                border: none;
                outline: none;
                color: {p['blue']};
                padding-top: 2px;
            }}
            QPushButton:disabled {{
                background: transparent;
                border: none;
                outline: none;
                color: rgba(140, 145, 160, 0.30);
            }}
            QPushButton#btn_power {{
                background: transparent;
                border: none;
                outline: none;
                font-size: 13px;
                font-weight: 700;
                color: {p['overlay0']};
                padding: 0px;
                border-radius: 4px;
            }}
            QPushButton#btn_power:checked {{
                color: {p['green']};
            }}
            QPushButton#btn_power:hover {{
                background: rgba(255, 255, 255, 0.08);
                color: {p['text']};
            }}
            QPushButton#btn_power:checked:hover {{
                color: {p['green']};
                background: rgba(166, 227, 161, 0.12);
            }}
            QPushButton#btn_bypass {{
                background: transparent;
                border: none;
                outline: none;
                font-size: 13px;
                font-weight: 700;
                color: {p['overlay0']};
                padding: 0px;
                border-radius: 4px;
            }}
            QPushButton#btn_bypass:hover {{
                color: {p['yellow']};
                background: rgba(255, 255, 255, 0.08);
                border: none;
                outline: none;
            }}
            QPushButton#btn_bypass:pressed {{
                background: rgba(255, 255, 255, 0.16);
                border: none;
                outline: none;
                padding-top: 2px;
            }}
            QPushButton#btn_bypass:checked {{
                background: transparent;
                border: none;
                outline: none;
                color: {p['peach']};
                font-weight: 800;
            }}
            QPushButton#btn_bypass:checked:hover {{
                color: {p['yellow']};
                background: rgba(250, 179, 135, 0.12);
                border: none;
                outline: none;
            }}
            QPushButton#btn_bypass:disabled {{
                background: transparent;
                border: none;
                outline: none;
                color: rgba(140, 145, 160, 0.25);
            }}
            QPushButton#btn_gui {{
                color: {p['overlay0']};
                font-size: 13px;
            }}
            QPushButton#btn_gui:checked {{
                color: {p['lavender']};
            }}
            QPushButton#btn_gui:hover {{
                color: {p['text']};
                background: rgba(255, 255, 255, 0.08);
            }}
            QPushButton#btn_edit {{
                color: {p['overlay0']};
                font-size: 13px;
            }}
            QPushButton#btn_edit:checked {{
                color: {p['mauve']};
            }}
            QPushButton#btn_edit:hover {{
                color: {p['text']};
                background: rgba(255, 255, 255, 0.08);
            }}
            QPushButton#btn_slider_mode {{
                background: transparent;
                border: none;
                outline: none;
                color: {p['blue']};
                font-weight: 700;
                font-size: 13px;
                padding: 0px;
                border-radius: 4px;
            }}
            QPushButton#btn_slider_mode:hover {{
                color: {p['lavender']};
                background: rgba(255, 255, 255, 0.08);
                border: none;
                outline: none;
            }}
            QPushButton#btn_slider_mode:pressed {{
                color: {p['sapphire']};
                background: rgba(255, 255, 255, 0.16);
                border: none;
                outline: none;
                padding-top: 2px;
            }}
            QPushButton#btn_minimize, QPushButton#btn_expand, QPushButton#btn_layer_expand {{
                background: transparent;
                border: none;
                outline: none;
                border-radius: 4px;
                color: {p['overlay1']};
                font-size: 11px;
                font-weight: bold;
                min-width: 20px;
                max-width: 20px;
                min-height: 20px;
                max-height: 20px;
                padding: 0px;
            }}
            QPushButton#btn_minimize:hover, QPushButton#btn_expand:hover, QPushButton#btn_layer_expand:hover {{
                background: rgba(255, 255, 255, 0.08);
                border: none;
                outline: none;
                color: {p['text']};
            }}
            QPushButton#btn_minimize:pressed, QPushButton#btn_expand:pressed {{
                color: {p['blue']};
                background: rgba(255, 255, 255, 0.16);
                border: none;
                outline: none;
                padding-top: 2px;
            }}
            QLabel,
            QLabel#label_name,
            QLabel#label_audio_in,
            QLabel#label_audio_out,
            QLabel#label_midi,
            QLabel#label_presets {{
                background: transparent;
                color: {text_color};
                font-weight: 600;
            }}
            QLabel#label_name {{
                background: transparent;
                font-weight: bold;
                font-size: 12px;
            }}
            QLabel:disabled,
            QLabel#label_name:disabled {{
                background: transparent;
                color: {text_disabled};
            }}
            QLabel#label_badge {{
                background-color: {badge_bg};
                border: none;
                border-radius: 4px;
                padding: 2px 6px;
                font-size: 9px;
                font-weight: bold;
                color: {badge_text};
            }}
            QComboBox#cb_presets {{
                background-color: rgba(255, 255, 255, 0.05);
                border: 1px solid rgba(255, 255, 255, 0.12);
                border-radius: 4px;
                color: {p['subtext1']};
                font-size: 10px;
                font-weight: 600;
                padding-left: 6px;
                padding-right: 16px;
                padding-top: 1px;
                padding-bottom: 1px;
            }}
            QComboBox#cb_presets:hover {{
                background-color: rgba(255, 255, 255, 0.09);
                border: 1px solid {p['blue']};
                color: {p['text']};
            }}
            QComboBox#cb_presets:focus, QComboBox#cb_presets:on {{
                border: 1px solid {p['blue']};
                color: {p['text']};
            }}
            QComboBox#cb_presets::drop-down {{
                subcontrol-origin: padding;
                subcontrol-position: top right;
                width: 14px;
                border: none;
                background: transparent;
            }}
            QComboBox#cb_presets::down-arrow {{
                image: none;
                width: 0px;
                height: 0px;
                border-left: 3px solid transparent;
                border-right: 3px solid transparent;
                border-top: 4px solid {p['subtext0']};
                margin-right: 4px;
            }}
            QComboBox#cb_presets QAbstractItemView {{
                background-color: {p['base']};
                border: 1px solid {p['surface1']};
                border-radius: 4px;
                color: {p['text']};
                selection-background-color: {p['surface0']};
                selection-color: {p['blue']};
                outline: none;
                padding: 2px;
            }}
            QComboBox {{
                background: {p['surface0']};
                border: 1px solid {p['surface1']};
                color: {p['text']};
                border-radius: 4px;
                padding: 2px 6px;
                font-size: 10px;
                font-weight: 600;
            }}
            QComboBox:hover {{
                border-color: {p['blue']};
            }}
            QDoubleSpinBox {{
                background: transparent;
                border: none;
                color: {p['text']};
                padding: 0px;
                font-size: 10px;
                font-weight: 600;
            }}
            QDoubleSpinBox:hover, QDoubleSpinBox:focus {{
                background: {"rgba(255, 255, 255, 0.08)" if self.is_dark else "rgba(0, 0, 0, 0.06)"};
                border: none;
                border-radius: 2px;
            }}
            QDoubleSpinBox::up-button, QDoubleSpinBox::down-button {{
                width: 0px;
                height: 0px;
                border: none;
            }}
            QDoubleSpinBox QLineEdit {{
                background: transparent;
                border: none;
                color: {p['text']};
                padding: 0px;
                margin: 0px;
                font-size: 10px;
                font-weight: 600;
                selection-background-color: {p['lavender']};
            }}
            QSlider::groove:horizontal {{
                background: {slider_groove};
                height: 4px;
                border-radius: 2px;
            }}
            QSlider::sub-page:horizontal {{
                background: {slider_track};
                height: 4px;
                border-radius: 2px;
            }}
            QSlider::handle:horizontal {{
                background: {slider_handle};
                border: 1px solid {slider_handle_border};
                width: 12px;
                height: 12px;
                margin: -4px 0;
                border-radius: 6px;
            }}
            QSlider::handle:horizontal:hover {{
                background: {p['rosewater'] if self.is_dark else '#ffffff'};
                border: 2px solid {p['lavender']};
            }}
        """
        self.setStyleSheet(styleSheet)

        colorEnabled = QColor(text_color)
        colorDisabled = QColor(text_disabled)
        dial_col_width = 68
        dial_col_height = 54
        for _, paramWidget in self.fParameterList:
            if hasattr(paramWidget, "setLabelColor"):
                paramWidget.setLabelColor(colorEnabled, colorDisabled)
            if hasattr(paramWidget, "setCustomPaintColor"):
                paramWidget.setCustomPaintColor(arcColor)
                paramWidget.setCustomPaintMode(ScalableDial.CUSTOM_PAINT_MODE_FLAT)
            if isinstance(paramWidget, ScalableDial):
                paramWidget.setFixedSize(dial_col_width, dial_col_height)

        if self.w_knobs_left is not None:
            leftLayout = self.w_knobs_left.layout()
            if leftLayout is not None:
                try:
                    leftLayout.setSpacing(6)
                    leftLayout.setContentsMargins(6, 4, 6, 4)
                except Exception:
                    pass

        if self.is_slider_mode:
            self.setSliderMode(True)
        else:
            self.setSliderMode(False)

        # Initialize modernized header layout mode (default True for minimal/sliders skin)
        self.is_modernized_slice = True
        custom_slice = self.host.get_custom_data_value(self.fPluginId, CUSTOM_DATA_TYPE_PROPERTY, "CarlaModernizedHeaderSlice")
        if custom_slice is not None and custom_slice != "":
            self.is_modernized_slice = (custom_slice.lower() in ("1", "true"))
        self._apply_modernized_slice_layout(self.is_modernized_slice)

    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.LeftButton:
            header_h = 40 if self.width() >= 440 else (52 if self.width() >= 230 else 62)
            if event.pos().y() <= header_h:
                self.slot_toggleExpandOrMini()
                event.accept()
                return
        super().mouseDoubleClickEvent(event)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._reflowResponsiveLayout()
        self._updateTitleElision()

    def _reflowResponsiveLayout(self):
        w = self.width()
        is_compact = getattr(self, 'is_compacted', False)

        # Tier 1: Ultra-Thin (< 230px)
        if w < 230:
            if hasattr(self, 'b_minimize') and self.b_minimize is not None:
                self.b_minimize.setVisible(False)
            if hasattr(self, 'b_slider_mode') and self.b_slider_mode is not None:
                self.b_slider_mode.setVisible(False)

            # Move w_title_stack to Row 2 (layout_title_row) for 100% full-width display
            if hasattr(self, 'w_title_stack') and hasattr(self, 'layout_title_row'):
                if self.ui.layout_top.indexOf(self.w_title_stack) >= 0:
                    self.ui.layout_top.removeWidget(self.w_title_stack)
                if self.layout_title_row.indexOf(self.w_title_stack) < 0:
                    self.layout_title_row.addWidget(self.w_title_stack)
                if hasattr(self, 'w_title_row') and self.w_title_row is not None:
                    self.w_title_row.setVisible(True)

            # Presets in Row 3 (w_subrow)
            if hasattr(self, 'cb_presets') and self.cb_presets is not None and hasattr(self, 'layout_subrow'):
                if self.ui.layout_top.indexOf(self.cb_presets) >= 0:
                    self.ui.layout_top.removeWidget(self.cb_presets)
                if self.layout_subrow.indexOf(self.cb_presets) < 0:
                    self.layout_subrow.insertWidget(0, self.cb_presets)
            if hasattr(self, 'w_subrow') and self.w_subrow is not None:
                self.w_subrow.setVisible(not is_compact)

        # Tier 2: Medium (230px <= w < 440px)
        elif w < 440:
            if hasattr(self, 'b_minimize') and self.b_minimize is not None:
                self.b_minimize.setVisible(True)
            if hasattr(self, 'b_slider_mode') and self.b_slider_mode is not None:
                self.b_slider_mode.setVisible(not is_compact)

            # Move w_title_stack back to Row 1 (layout_top, right after buttons)
            if hasattr(self, 'w_title_stack') and hasattr(self, 'layout_title_row'):
                if self.layout_title_row.indexOf(self.w_title_stack) >= 0:
                    self.layout_title_row.removeWidget(self.w_title_stack)
                if hasattr(self, 'w_title_row') and self.w_title_row is not None:
                    self.w_title_row.setVisible(False)
                if self.ui.layout_top.indexOf(self.w_title_stack) < 0:
                    btn_idx = self.ui.layout_top.indexOf(self.ui.w_buttons)
                    self.ui.layout_top.insertWidget(btn_idx + 1 if btn_idx >= 0 else 0, self.w_title_stack)

            # Presets stay in Row 2 (w_subrow) so title has full breathing room
            if hasattr(self, 'cb_presets') and self.cb_presets is not None and hasattr(self, 'layout_subrow'):
                if self.ui.layout_top.indexOf(self.cb_presets) >= 0:
                    self.ui.layout_top.removeWidget(self.cb_presets)
                if self.layout_subrow.indexOf(self.cb_presets) < 0:
                    self.layout_subrow.insertWidget(0, self.cb_presets)
            if hasattr(self, 'w_subrow') and self.w_subrow is not None:
                self.w_subrow.setVisible(not is_compact)

        # Tier 3: Wide (w >= 440px)
        else:
            if hasattr(self, 'b_minimize') and self.b_minimize is not None:
                self.b_minimize.setVisible(True)
            if hasattr(self, 'b_slider_mode') and self.b_slider_mode is not None:
                self.b_slider_mode.setVisible(not is_compact)

            # w_title_stack in Row 1
            if hasattr(self, 'w_title_stack') and hasattr(self, 'layout_title_row'):
                if self.layout_title_row.indexOf(self.w_title_stack) >= 0:
                    self.layout_title_row.removeWidget(self.w_title_stack)
                if hasattr(self, 'w_title_row') and self.w_title_row is not None:
                    self.w_title_row.setVisible(False)
                if self.ui.layout_top.indexOf(self.w_title_stack) < 0:
                    btn_idx = self.ui.layout_top.indexOf(self.ui.w_buttons)
                    self.ui.layout_top.insertWidget(btn_idx + 1 if btn_idx >= 0 else 0, self.w_title_stack)

            # Move cb_presets into Row 1 (before spacer_flex)
            if hasattr(self, 'cb_presets') and self.cb_presets is not None and hasattr(self, 'layout_subrow'):
                if self.layout_subrow.indexOf(self.cb_presets) >= 0:
                    self.layout_subrow.removeWidget(self.cb_presets)
                if self.ui.layout_top.indexOf(self.cb_presets) < 0:
                    idx = self.ui.layout_top.indexOf(self.spacer_flex)
                    if idx >= 0:
                        self.ui.layout_top.insertWidget(idx, self.cb_presets)
                    else:
                        self.ui.layout_top.addWidget(self.cb_presets)
            if hasattr(self, 'w_subrow') and self.w_subrow is not None:
                self.w_subrow.setVisible(False)

        # Parameter slider drawer card stacking: stacked if w < 320, inline if w >= 320
        if hasattr(self, 'fSliderParameterList'):
            stacked = (w < 320)
            for _, sWidget in self.fSliderParameterList:
                if hasattr(sWidget, 'setIsMini'):
                    sWidget.setIsMini(stacked)

        if hasattr(self, 'sliders_layout') and self.sliders_layout is not None:
            if w < 260:
                self.sliders_layout.setContentsMargins(2, 2, 2, 2)
                self.sliders_layout.setSpacing(2)
            else:
                self.sliders_layout.setContentsMargins(6, 4, 6, 4)
                self.sliders_layout.setSpacing(3)

        # Responsive knobs layout: adapt dial size, spacing, and right knob column
        if hasattr(self, 'fParameterList'):
            dial_w = 46 if w < 260 else (52 if w < 440 else 58)
            dial_h = 44 if w < 260 else (48 if w < 440 else 50)
            for _, pWidget in self.fParameterList:
                if isinstance(pWidget, ScalableDial):
                    pWidget.setFixedSize(dial_w, dial_h)

        is_sliders = getattr(self, 'is_slider_mode', False)

        if hasattr(self, 'w_knobs_left') and self.w_knobs_left is not None:
            if is_sliders:
                self.w_knobs_left.setVisible(False)
            else:
                self.w_knobs_left.setVisible(not is_compact)
                kLayout = self.w_knobs_left.layout()
                if kLayout is not None:
                    kLayout.setSpacing(3 if w < 260 else 5)
                    kLayout.setContentsMargins(1, 2, 1, 2)
                self.w_knobs_left.setMinimumWidth(0)

        if hasattr(self, 'w_knobs_right') and self.w_knobs_right is not None:
            show_right = (w >= 320) and not is_compact and not is_sliders
            self.w_knobs_right.setVisible(show_right)
            if hasattr(self, 'spacer_knobs') and self.spacer_knobs is not None:
                pref_policy = getattr(QSizePolicy, "Preferred", None) or getattr(getattr(QSizePolicy, "Policy", None), "Preferred", None)
                if show_right and pref_policy is not None:
                    self.spacer_knobs.changeSize(6, 1, pref_policy, pref_policy)
                elif pref_policy is not None:
                    self.spacer_knobs.changeSize(0, 0, pref_policy, pref_policy)

        # Notify rack item size if fixed height changed
        new_h = self.getFixedHeight()
        if not hasattr(self, '_lastFixedHeight') or self._lastFixedHeight != new_h:
            self._lastFixedHeight = new_h
            self.updateRackItemSize()

    def _updateTitleElision(self):
        if not hasattr(self, 'label_name') or not hasattr(self, 'fFullTitle'):
            return
        fm = self.label_name.fontMetrics()
        full_text = self.fFullTitle
        total_w = fm.horizontalAdvance(full_text) if hasattr(fm, 'horizontalAdvance') else fm.width(full_text)
        w = self.width()
        if w < 230:
            max_allowed = max(100, w - 24)
        elif w < 440:
            max_allowed = max(90, w - 160)
        else:
            max_allowed = max(120, w - 290)
        if total_w <= max_allowed:
            self.label_name.setText(full_text)
        else:
            elided = fm.elidedText(full_text, Qt.ElideRight, max_allowed)
            self.label_name.setText(elided)

    def setModernizedHeaderSlice(self, enabled):
        self.is_modernized_slice = bool(enabled)
        self.host.set_custom_data(self.fPluginId, CUSTOM_DATA_TYPE_PROPERTY, "CarlaModernizedHeaderSlice", "true" if self.is_modernized_slice else "false")
        if hasattr(gCarla, "gui") and gCarla.gui is not None:
            gCarla.gui.fHasUnsavedChanges = True
        self._apply_modernized_slice_layout(self.is_modernized_slice)

    def _apply_modernized_slice_layout(self, modernized):
        if not hasattr(self.ui, 'layout_leds') or not hasattr(self.ui, 'layout_peaks'):
            return

        # Ensure container widgets exist
        if not hasattr(self, '_modern_slice_container'):
            self._modern_slice_container = QWidget(parent=self)
            self._modern_slice_container.setObjectName("w_modern_slice")
            self._modern_slice_container.setStyleSheet(
                "QWidget#w_modern_slice { background: rgba(0, 0, 0, 50); border: 1px solid rgba(255, 255, 255, 15); border-radius: 4px; }"
            )
            slice_layout = QHBoxLayout(self._modern_slice_container)
            slice_layout.setContentsMargins(2, 2, 2, 2)
            slice_layout.setSpacing(3)
            slice_layout.setAlignment(Qt.AlignVCenter)

            # Container for vertical 2x2 LEDs - strictly 18x18 square
            self._led_grid_container = QWidget(self._modern_slice_container)
            self._led_grid_layout = QGridLayout(self._led_grid_container)
            self._led_grid_layout.setContentsMargins(0, 0, 0, 0)
            self._led_grid_layout.setSpacing(2)
            self._led_grid_container.setFixedSize(18, 18)
            self._led_grid_container.setStyleSheet("background: rgba(0, 0, 0, 40); border-radius: 2px;")

            # Meter slice container
            self._meter_slice_container = QWidget(self._modern_slice_container)
            self._meter_slice_layout = QHBoxLayout(self._meter_slice_container)
            self._meter_slice_layout.setContentsMargins(1, 0, 0, 0)
            self._meter_slice_layout.setSpacing(1)
            self._meter_slice_container.setFixedHeight(18)
            self._meter_slice_container.setStyleSheet("border-left: 1px solid rgba(255, 255, 255, 15);")

            slice_layout.addWidget(self._led_grid_container)
            slice_layout.addWidget(self._meter_slice_container)

            # Place in top row before chevron minimize button
            min_idx = self.ui.layout_top.indexOf(self.b_minimize) if hasattr(self, 'b_minimize') and self.b_minimize is not None else -1
            if min_idx >= 0:
                self.ui.layout_top.insertWidget(min_idx, self._modern_slice_container)
            else:
                self.ui.layout_top.addWidget(self._modern_slice_container)

        if modernized:
            # Hide old horizontal layouts
            if hasattr(self.ui, 'layout_peaks'):
                self.ui.layout_peaks.removeWidget(self.peak_in)
                self.ui.layout_peaks.removeWidget(self.peak_out)
            if hasattr(self.ui, 'layout_leds'):
                self.ui.layout_leds.removeWidget(self.led_control)
                self.ui.layout_leds.removeWidget(self.led_midi)
                self.ui.layout_leds.removeWidget(self.led_audio_in)
                self.ui.layout_leds.removeWidget(self.led_audio_out)

            # Place LEDs in a tight 2x2 grid (8x8 tiles with 2px spacing = 18x18 total)
            self._led_grid_layout.addWidget(self.led_control, 0, 0)
            self._led_grid_layout.addWidget(self.led_midi, 0, 1)
            self._led_grid_layout.addWidget(self.led_audio_in, 1, 0)
            self._led_grid_layout.addWidget(self.led_audio_out, 1, 1)

            for led in (self.led_control, self.led_midi, self.led_audio_in, self.led_audio_out):
                if led is not None:
                    if hasattr(led, 'setMinimalMode'):
                        led.setMinimalMode(True)
                    led.setFixedSize(8, 8)
                    led.setStyleSheet("background: transparent; border: none; padding: 0px; margin: 0px; border-radius: 1px;")

            # Place Peak Meters in modern vertical slice
            self._meter_slice_layout.addWidget(self.peak_in)
            self._meter_slice_layout.addWidget(self.peak_out)
            for pm in (self.peak_in, self.peak_out):
                if pm is not None:
                    pm.setMeterOrientation(DigitalPeakMeter.VERTICAL)
                    pm.setFixedSize(6, 18)
                    pm.setStyleSheet("background: rgba(15, 15, 20, 180); border-radius: 2px;")

            self._modern_slice_container.setVisible(True)
        else:
            # Restore legacy layout
            self._modern_slice_container.setVisible(False)
            if hasattr(self.ui, 'layout_leds') and hasattr(self.ui, 'layout_peaks'):
                for led in (self.led_control, self.led_midi, self.led_audio_in, self.led_audio_out):
                    if led is not None:
                        if hasattr(led, 'setMinimalMode'):
                            led.setMinimalMode(False)
                        led.setFixedSize(14, 14)
                        led.setStyleSheet("")
                self.ui.layout_leds.addWidget(self.led_control)
                self.ui.layout_leds.addWidget(self.led_midi)
                self.ui.layout_leds.addWidget(self.led_audio_in)
                self.ui.layout_leds.addWidget(self.led_audio_out)

                for pm in (self.peak_in, self.peak_out):
                    if pm is not None:
                        pm.setMeterOrientation(DigitalPeakMeter.HORIZONTAL)
                        pm.setMinimumSize(100, 0)
                        pm.setMaximumSize(100, 16777215)
                        pm.setStyleSheet("")
                self.ui.layout_peaks.addWidget(self.peak_in)
                self.ui.layout_peaks.addWidget(self.peak_out)

    def _update_bypass_state(self, is_bypassed):
        if not hasattr(self, 'b_bypass') or self.b_bypass is None:
            return
        self.b_bypass.blockSignals(True)
        self.b_bypass.setChecked(is_bypassed)
        self.b_bypass.setText("\uf05e")
        if is_bypassed:
            self.b_bypass.setToolTip("Bypassed (Dry/Wet = 0%) - Click to activate audio")
        else:
            self.b_bypass.setToolTip("Active (Dry/Wet = 100%) - Click to bypass")
        self.b_bypass.blockSignals(False)

    def _ensure_sliders_created(self):
        if hasattr(self, 'scroll_area') and self.scroll_area is not None:
            return

        self.sliders_container = QWidget()
        self.sliders_container.setUpdatesEnabled(False)
        self.sliders_layout = QVBoxLayout(self.sliders_container)
        self.sliders_layout.setContentsMargins(6, 4, 6, 4)
        self.sliders_layout.setSpacing(3)

        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setWidget(self.sliders_container)
        from styles.theme_manager import MINIMAL_SCROLLBAR_QSS
        self.scroll_area.setStyleSheet("QScrollArea { border: none; background: transparent; }\n" + MINIMAL_SCROLLBAR_QSS)

        self.ui.verticalLayout.addWidget(self.scroll_area, 1)

        self.fSliderParameterList = []
        parameterCount = self.host.get_parameter_count(self.fPluginId)

        p = get_active_skin_palette(self.is_dark)
        wet_color = p['peach']
        vol_color = p['green']

        # Master slot parameters pinned at top: Dry/Wet (Amber) & Volume (Emerald)
        if self.fPluginInfo['hints'] & PLUGIN_CAN_DRYWET:
            widget = SliderParamWidget(self.sliders_container, PARAMETER_DRYWET, "Dry/Wet", 0.0, 1.0, False, accent_color=wet_color)
            self.fSliderParameterList.append([PARAMETER_DRYWET, widget])
            self.sliders_layout.addWidget(widget)
            widget.realValueChanged.connect(self.slot_parameterValueChanged)

        if self.fPluginInfo['hints'] & PLUGIN_CAN_VOLUME:
            widget = SliderParamWidget(self.sliders_container, PARAMETER_VOLUME, "Volume", 0.0, 1.27, False, accent_color=vol_color)
            self.fSliderParameterList.append([PARAMETER_VOLUME, widget])
            self.sliders_layout.addWidget(widget)
            widget.realValueChanged.connect(self.slot_parameterValueChanged)

        has_masters = bool((self.fPluginInfo['hints'] & PLUGIN_CAN_DRYWET) or (self.fPluginInfo['hints'] & PLUGIN_CAN_VOLUME))
        if has_masters and parameterCount > 0:
            sep = QFrame(self.sliders_container)
            sep.setFrameShape(QFrame.HLine)
            sep.setFixedHeight(1)
            sep.setStyleSheet(f"background: {p['surface0']}; border: none; margin: 2px 2px;")
            self.sliders_layout.addWidget(sep)

        for i in range(parameterCount):
            paramInfo   = self.host.get_parameter_info(self.fPluginId, i)
            paramData   = self.host.get_parameter_data(self.fPluginId, i)
            paramRanges = self.host.get_parameter_ranges(self.fPluginId, i)
            isInteger   = (paramData['hints'] & PARAMETER_IS_INTEGER) != 0

            if paramData['type'] != PARAMETER_INPUT: continue
            if paramData['hints'] & PARAMETER_IS_BOOLEAN: continue
            if (paramData['hints'] & PARAMETER_IS_ENABLED) == 0: continue
            if paramInfo['name'].startswith("unused"): continue

            paramName = getParameterShortName(paramInfo['name'])

            widget = SliderParamWidget(self.sliders_container, i, paramName, paramRanges['min'], paramRanges['max'], isInteger, paramInfo['name'])
            self.fSliderParameterList.append([i, widget])
            self.sliders_layout.addWidget(widget)

            widget.realValueChanged.connect(self.slot_parameterValueChanged)

        self.sliders_layout.addStretch()
        self.sliders_container.setUpdatesEnabled(True)
        self.syncSliderValues()

    def setSliderMode(self, slider_mode):
        self.is_slider_mode = bool(slider_mode)
        newSkin = ("sliders-dark" if self.is_dark else "sliders-light") if self.is_slider_mode else ("minimal-dark" if self.is_dark else "minimal-light")
        self.fSkinStyle = newSkin
        self.host.set_custom_data(self.fPluginId, CUSTOM_DATA_TYPE_PROPERTY, "CarlaSkin", newSkin)
        if hasattr(gCarla, "gui") and gCarla.gui is not None:
            gCarla.gui.fHasUnsavedChanges = True
            pitem = gCarla.gui.getPluginItem(self.fPluginId)
            if pitem is not None and hasattr(pitem, "fOptions"):
                pitem.fOptions['skin'] = newSkin

        pref_policy = getattr(QSizePolicy, "Preferred", None) or getattr(getattr(QSizePolicy, "Policy", None), "Preferred", None)

        if self.is_slider_mode:
            self._ensure_sliders_created()
            self._reflowResponsiveLayout()
            if self.w_knobs_left is not None:
                self.w_knobs_left.setVisible(False)
            if self.w_knobs_right is not None:
                self.w_knobs_right.setVisible(False)
            if self.spacer_knobs is not None and pref_policy is not None:
                self.spacer_knobs.changeSize(0, 0, pref_policy, pref_policy)
            if self.scroll_area is not None:
                self.scroll_area.setVisible(True)
                self.syncSliderValues()
            self.b_slider_mode.setText("\uf1de")
            self.b_slider_mode.setToolTip("Switch to Knobs view")
        else:
            if self.scroll_area is not None:
                self.scroll_area.setVisible(False)
            if self.w_knobs_left is not None:
                self.w_knobs_left.setVisible(True)
            if self.w_knobs_right is not None:
                self.w_knobs_right.setVisible(True)
            has_right_knobs = bool(self.w_knobs_right is not None and (
                (self.fPluginInfo['hints'] & PLUGIN_CAN_DRYWET) or (self.fPluginInfo['hints'] & PLUGIN_CAN_VOLUME)
            ))
            if self.spacer_knobs is not None and pref_policy is not None:
                self.spacer_knobs.changeSize(6 if has_right_knobs else 0, 1 if has_right_knobs else 0, pref_policy, pref_policy)
            self.b_slider_mode.setText("\uf0c9")
            self.b_slider_mode.setToolTip("Switch to Sliders view")

        self.updateRackItemSize()

    def slot_toggleSliderMode(self):
        self.setSliderMode(not self.is_slider_mode)

    def syncSliderValues(self):
        if not hasattr(self, 'fSliderParameterList') or not self.fSliderParameterList:
            return
        for paramIndex, paramWidget in self.fSliderParameterList:
            paramWidget.blockSignals(True)
            if paramIndex < 0:
                val = self.host.get_internal_parameter_value(self.fPluginId, paramIndex)
            else:
                val = self.host.get_current_parameter_value(self.fPluginId, paramIndex)
            paramWidget.setValue(val)
            paramWidget.blockSignals(False)

    def slot_parameterValueChanged(self, value):
        sender = self.sender()
        if sender is not None and isinstance(sender, SliderParamWidget):
            pIndex = sender.getIndex()
            for kIndex, kWdg in self.fParameterList:
                if kIndex == pIndex:
                    kWdg.blockSignals(True)
                    kWdg.setValue(value)
                    kWdg.blockSignals(False)
                    break
        PluginSlot_Default.slot_parameterValueChanged(self, value)

    def setCompacted(self, compacted):
        self.is_compacted = bool(compacted)
        self.host.set_custom_data(self.fPluginId, CUSTOM_DATA_TYPE_PROPERTY, "CarlaSkinIsCompacted", "true" if self.is_compacted else "false")
        if hasattr(gCarla, "gui") and gCarla.gui is not None:
            gCarla.gui.fHasUnsavedChanges = True
            pitem = gCarla.gui.getPluginItem(self.fPluginId)
            if pitem is not None and hasattr(pitem, "fOptions"):
                pitem.fOptions['compact'] = self.is_compacted

        if self.is_compacted:
            if hasattr(self.ui, 'line') and self.ui.line is not None:
                self.ui.line.setVisible(False)
            if hasattr(self, 'w_subrow') and self.w_subrow is not None:
                self.w_subrow.setVisible(False)
            if self.w_knobs_left is not None:
                self.w_knobs_left.setVisible(False)
            if self.w_knobs_right is not None:
                self.w_knobs_right.setVisible(False)
            if hasattr(self, 'scroll_area') and self.scroll_area is not None:
                self.scroll_area.setVisible(False)
            if hasattr(self, 'b_slider_mode') and self.b_slider_mode is not None:
                self.b_slider_mode.setVisible(False)
            if hasattr(self, 'b_minimize') and self.b_minimize is not None:
                self.b_minimize.setText("\uf078")
                self.b_minimize.setToolTip("Expand Rack Slot")
        else:
            w = self.width() if hasattr(self, 'width') and self.width() > 0 else 300
            if hasattr(self, 'w_subrow') and self.w_subrow is not None:
                self.w_subrow.setVisible(w < 440)
            if hasattr(self.ui, 'line') and self.ui.line is not None:
                self.ui.line.setVisible(True)
            if hasattr(self, 'b_slider_mode') and self.b_slider_mode is not None:
                self.b_slider_mode.setVisible(w >= 230)

            if self.is_slider_mode:
                if self.w_knobs_left is not None:
                    self.w_knobs_left.setVisible(False)
                if self.w_knobs_right is not None:
                    self.w_knobs_right.setVisible(False)
                if hasattr(self, 'scroll_area') and self.scroll_area is not None:
                    self.scroll_area.setVisible(True)
            else:
                if hasattr(self, 'scroll_area') and self.scroll_area is not None:
                    self.scroll_area.setVisible(False)
                if self.w_knobs_left is not None:
                    self.w_knobs_left.setVisible(True)
                if self.w_knobs_right is not None:
                    self.w_knobs_right.setVisible(True)

            if hasattr(self, 'b_minimize') and self.b_minimize is not None:
                self.b_minimize.setText("\uf077")
                self.b_minimize.setToolTip("Minimize / Collapse Rack Slot")

        self._reflowResponsiveLayout()
        self.updateRackItemSize()

    def setLayerMode(self, layer_mode):
        """Deprecated compatibility shim: layer mode is unified into dynamic responsive layout."""
        pass

    def slot_toggleExpandOrMini(self):
        """Unified disclosure toggle: toggles compacted state in dynamic mode."""
        self.toggleCompacted()

    def _ensure_mini_params_created(self):
        """Build compact Photoshop adjustment-layer style mini slider tray with scroll area."""
        if hasattr(self, 'mini_scroll_area') and self.mini_scroll_area is not None:
            return

        self.mini_params_tray = QWidget()
        self.mini_params_tray.setObjectName("w_mini_params_tray")
        self.mini_params_layout = QVBoxLayout(self.mini_params_tray)
        self.mini_params_layout.setContentsMargins(4, 2, 4, 2)
        self.mini_params_layout.setSpacing(3)

        self.mini_scroll_area = QScrollArea()
        self.mini_scroll_area.setObjectName("mini_scroll_area")
        self.mini_scroll_area.setWidgetResizable(True)
        self.mini_scroll_area.setWidget(self.mini_params_tray)
        from styles.theme_manager import MINIMAL_SCROLLBAR_QSS
        self.mini_scroll_area.setStyleSheet("QScrollArea { border: none; background: transparent; }\n" + MINIMAL_SCROLLBAR_QSS)

        self.fMiniSliderParameterList = []
        parameterCount = self.host.get_parameter_count(self.fPluginId)

        p = get_active_skin_palette(self.is_dark)
        wet_color = p['peach']
        vol_color = p['green']

        # Master slot parameters pinned at top: Dry/Wet (Amber) & Volume (Emerald)
        if self.fPluginInfo['hints'] & PLUGIN_CAN_DRYWET:
            widget = SliderParamWidget(
                self.mini_params_tray, PARAMETER_DRYWET, "Dry/Wet", 0.0, 1.0, False, is_mini=True, accent_color=wet_color
            )
            self.fMiniSliderParameterList.append([PARAMETER_DRYWET, widget])
            self.mini_params_layout.addWidget(widget)
            widget.realValueChanged.connect(self.slot_parameterValueChanged)

        if self.fPluginInfo['hints'] & PLUGIN_CAN_VOLUME:
            widget = SliderParamWidget(
                self.mini_params_tray, PARAMETER_VOLUME, "Volume", 0.0, 1.27, False, is_mini=True, accent_color=vol_color
            )
            self.fMiniSliderParameterList.append([PARAMETER_VOLUME, widget])
            self.mini_params_layout.addWidget(widget)
            widget.realValueChanged.connect(self.slot_parameterValueChanged)

        has_masters = bool((self.fPluginInfo['hints'] & PLUGIN_CAN_DRYWET) or (self.fPluginInfo['hints'] & PLUGIN_CAN_VOLUME))
        if has_masters and parameterCount > 0:
            sep = QFrame(self.mini_params_tray)
            sep.setFrameShape(QFrame.HLine)
            sep.setFixedHeight(1)
            sep.setStyleSheet(f"background: {p['surface0']}; border: none; margin: 2px 2px;")
            self.mini_params_layout.addWidget(sep)

        # Essential parameters: top active parameters
        for i in range(parameterCount):
            paramInfo = self.host.get_parameter_info(self.fPluginId, i)
            paramData = self.host.get_parameter_data(self.fPluginId, i)
            paramRanges = self.host.get_parameter_ranges(self.fPluginId, i)
            isInteger = (paramData['hints'] & PARAMETER_IS_INTEGER) != 0

            if paramData['type'] != PARAMETER_INPUT:
                continue
            if paramData['hints'] & PARAMETER_IS_BOOLEAN:
                continue
            if (paramData['hints'] & PARAMETER_IS_ENABLED) == 0:
                continue
            if paramInfo['name'].startswith("unused"):
                continue

            paramName = getParameterShortName(paramInfo['name'])
            widget = SliderParamWidget(
                self.mini_params_tray,
                i,
                paramName,
                paramRanges['min'],
                paramRanges['max'],
                isInteger,
                paramInfo['name'],
                is_mini=True,
            )
            self.fMiniSliderParameterList.append([i, widget])
            self.mini_params_layout.addWidget(widget)
            widget.realValueChanged.connect(self.slot_parameterValueChanged)

        self.ui.verticalLayout.addWidget(self.mini_scroll_area, 1)
        self.syncMiniSliderValues()

    def syncMiniSliderValues(self):
        if not hasattr(self, 'fMiniSliderParameterList') or not self.fMiniSliderParameterList:
            return
        for paramIndex, paramWidget in self.fMiniSliderParameterList:
            paramWidget.blockSignals(True)
            if paramIndex < 0:
                val = self.host.get_internal_parameter_value(self.fPluginId, paramIndex)
            else:
                val = self.host.get_current_parameter_value(self.fPluginId, paramIndex)
            paramWidget.setValue(val)
            paramWidget.blockSignals(False)

    def toggleCompacted(self):
        self.setCompacted(not self.is_compacted)

    def getFixedHeight(self):
        w = self.width() if hasattr(self, 'width') and self.width() > 0 else 300
        is_compact = getattr(self, 'is_compacted', False)

        if is_compact:
            if w < 230:
                return 54
            return 38

        base_h = 38 if w >= 440 else (52 if w >= 230 else 72)

        if getattr(self, 'is_slider_mode', False):
            count = len(getattr(self, 'fSliderParameterList', []))
            if count == 0 and hasattr(self, 'fParameterList'):
                count = len(self.fParameterList)
            slider_item_h = 36 if w < 320 else 24
            req_height = base_h + (count * slider_item_h) + 8
            return max(base_h + 40, min(req_height, 360))

        if hasattr(self, 'w_knobs_left') and self.w_knobs_left is not None and self.w_knobs_left.layout() is not None:
            kw = self.w_knobs_left.width()
            if kw > 50:
                knobs_h = self.w_knobs_left.layout().heightForWidth(kw)
                if knobs_h > 40:
                    return max(base_h + 40, min(base_h + knobs_h + 8, 360))
        return max(base_h + 54, 112)

    def setParameterValue(self, parameterId, value, sendCallback):
        PluginSlot_Default.setParameterValue(self, parameterId, value, sendCallback)
        if parameterId == PARAMETER_DRYWET and hasattr(self, "_update_bypass_state"):
            self._update_bypass_state(value == 0.0)
        if hasattr(self, 'fSliderParameterList'):
            for pIndex, widget in self.fSliderParameterList:
                if pIndex == parameterId:
                    widget.blockSignals(True)
                    widget.setValue(value)
                    widget.blockSignals(False)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        w = float(self.width())
        h = float(self.height())
        rect = QRectF(1.0, 1.0, w - 2.0, h - 2.0)

        painter.setBrush(self.minimal_bg_color)
        painter.setPen(QPen(self.border_color, 1.0))
        painter.drawRoundedRect(rect, 6.0, 6.0)

        stripePath = QPainterPath()
        stripePath.addRoundedRect(QRectF(3.0, 4.0, 4.0, h - 8.0), 2.0, 2.0)
        categoryColor = QColor(self.fSkinColor[0], self.fSkinColor[1], self.fSkinColor[2])
        if (categoryColor.red() == 0 and categoryColor.green() == 0 and categoryColor.blue() == 0) or (categoryColor.red() == 255 and categoryColor.green() == 255 and categoryColor.blue() == 255):
            categoryColor = QColor(getattr(self, 'cat_color', '#cba6f7'))
        painter.fillPath(stripePath, categoryColor)

        if self.fIsSelected:
            selPen = QPen(self.selection_color, 1.8)
            painter.setPen(selPen)
            painter.setBrush(Qt.NoBrush)
            painter.drawRoundedRect(rect, 6.0, 6.0)

        QFrame.paintEvent(self, event)

class PluginSlot_Presets(AbstractPluginSlot):
    def __init__(self, parent, host, pluginId, skinColor, skinStyle):
        AbstractPluginSlot.__init__(self, parent, host, pluginId, skinColor, skinStyle)
        self.ui = ui_carla_plugin_presets.Ui_PluginWidget()
        self.ui.setupUi(self)

        usingMidiPrograms = bool(skinStyle != "presets")

        if usingMidiPrograms:
            programCount = self.host.get_midi_program_count(self.fPluginId)
        else:
            programCount = self.host.get_program_count(self.fPluginId)

        if programCount > 0:
            self.ui.cb_presets.setEnabled(True)
            self.ui.label_presets.setEnabled(True)

            for i in range(programCount):
                if usingMidiPrograms:
                    progName = self.host.get_midi_program_data(self.fPluginId, i)['name']
                else:
                    progName = self.host.get_program_name(self.fPluginId, i)

                self.ui.cb_presets.addItem(progName)

            if usingMidiPrograms:
                curProg = self.host.get_current_midi_program_index(self.fPluginId)
            else:
                curProg = self.host.get_current_program_index(self.fPluginId)

            self.ui.cb_presets.setCurrentIndex(curProg)

        else:
            self.ui.cb_presets.setEnabled(False)
            self.ui.cb_presets.setVisible(False)
            self.ui.label_presets.setEnabled(False)
            self.ui.label_presets.setVisible(False)

        self.b_enable = self.ui.b_enable
        self.b_gui    = self.ui.b_gui
        self.b_edit   = self.ui.b_edit

        self.cb_presets = self.ui.cb_presets

        self.label_name    = self.ui.label_name
        self.label_presets = self.ui.label_presets

        self.led_control   = self.ui.led_control
        self.led_midi      = self.ui.led_midi
        self.led_audio_in  = self.ui.led_audio_in
        self.led_audio_out = self.ui.led_audio_out

        self.peak_in  = self.ui.peak_in
        self.peak_out = self.ui.peak_out

        if skinStyle == "zynfx":
            self.setupZynFxParams()
        else:
            self.w_knobs_left  = self.ui.w_knobs_left
            self.w_knobs_right = self.ui.w_knobs_right
            self.spacer_knobs  = self.ui.layout_bottom.itemAt(1).spacerItem()

            if self.w_knobs_left.layout() is not None:
                self.w_knobs_left.layout().setSpacing(8)
                self.w_knobs_left.layout().setContentsMargins(6, 2, 6, 2)
            if self.w_knobs_right.layout() is not None:
                self.w_knobs_right.layout().setSpacing(8)
                self.w_knobs_right.layout().setContentsMargins(6, 2, 6, 2)

        self.ready()

        if usingMidiPrograms:
            self.ui.cb_presets.currentIndexChanged.connect(self.slot_midiProgramChanged)
        else:
            self.ui.cb_presets.currentIndexChanged.connect(self.slot_programChanged)

    def setupZynFxParams(self):
        parameterCount = min(self.host.get_parameter_count(self.fPluginId), 8)

        for i in range(parameterCount):
            paramInfo   = self.host.get_parameter_info(self.fPluginId, i)
            paramData   = self.host.get_parameter_data(self.fPluginId, i)
            paramRanges = self.host.get_parameter_ranges(self.fPluginId, i)

            if paramData['type'] != PARAMETER_INPUT:
                continue
            if paramData['hints'] & PARAMETER_IS_BOOLEAN:
                continue
            if (paramData['hints'] & PARAMETER_IS_ENABLED) == 0:
                continue

            paramName = paramInfo['name']

            if paramName.startswith("unused"):
                continue

            if self.fPluginInfo['label'] == "zynalienwah":
                if   i == 0: paramName = "Freq"
                elif i == 1: paramName = "Rnd"
                elif i == 2: paramName = "L type"
                elif i == 3: paramName = "St.df"
                elif i == 5: paramName = "Fb"
                elif i == 7: paramName = "L/R"

            elif self.fPluginInfo['label'] == "zynchorus":
                if   i == 0: paramName = "Freq"
                elif i == 1: paramName = "Rnd"
                elif i == 2: paramName = "L type"
                elif i == 3: paramName = "St.df"
                elif i == 6: paramName = "Fb"
                elif i == 7: paramName = "L/R"
                elif i == 8: paramName = "Flngr"
                elif i == 9: paramName = "Subst"

            elif self.fPluginInfo['label'] == "zyndistortion":
                if   i == 0: paramName = "LRc."
                elif i == 4: paramName = "Neg."
                elif i == 5: paramName = "LPF"
                elif i == 6: paramName = "HPF"
                elif i == 7: paramName = "St."
                elif i == 8: paramName = "PF"

            elif self.fPluginInfo['label'] == "zyndynamicfilter":
                if   i == 0: paramName = "Freq"
                elif i == 1: paramName = "Rnd"
                elif i == 2: paramName = "L type"
                elif i == 3: paramName = "St.df"
                elif i == 4: paramName = "LfoD"
                elif i == 5: paramName = "A.S."
                elif i == 6: paramName = "A.Inv."
                elif i == 7: paramName = "A.M."

            elif self.fPluginInfo['label'] == "zynecho":
                if   i == 1: paramName = "LRdl."
                elif i == 2: paramName = "LRc."
                elif i == 3: paramName = "Fb."
                elif i == 4: paramName = "Damp"

            elif self.fPluginInfo['label'] == "zynphaser":
                if   i ==  0: paramName = "Freq"
                elif i ==  1: paramName = "Rnd"
                elif i ==  2: paramName = "L type"
                elif i ==  3: paramName = "St.df"
                elif i ==  5: paramName = "Fb"
                elif i ==  7: paramName = "L/R"
                elif i ==  8: paramName = "Subst"
                elif i ==  9: paramName = "Phase"
                elif i == 11: paramName = "Dist"

            elif self.fPluginInfo['label'] == "zynreverb":
                if   i ==  2: paramName = "I.delfb"
                elif i ==  5: paramName = "LPF"
                elif i ==  6: paramName = "HPF"
                elif i ==  9: paramName = "R.S."
                elif i == 10: paramName = "I.del"

            else:
                paramName = getParameterShortName(paramName)

            widget = ScalableDial(self, i)
            widget.setLabel(paramName, paramInfo['name'])
            widget.setMinimum(paramRanges['min'])
            widget.setMaximum(paramRanges['max'])
            widget.setImage(3)
            widget.setCustomPaintColor(QColor(83, 173, 10))
            widget.setCustomPaintMode(ScalableDial.CUSTOM_PAINT_MODE_COLOR)
            widget.forceWhiteLabelGradientText()
            widget.hide()

            if (paramData['hints'] & PARAMETER_IS_ENABLED) == 0:
                widget.setEnabled(False)

            self.fParameterList.append([i, widget])
            self.ui.w_knobs_left.layout().addWidget(widget)

        if self.fPluginInfo['hints'] & PLUGIN_CAN_DRYWET:
            widget = ScalableDial(self, PARAMETER_DRYWET)
            widget.setLabel("Wet")
            widget.setMinimum(0.0)
            widget.setMaximum(1.0)
            widget.setImage(3)
            widget.setCustomPaintMode(ScalableDial.CUSTOM_PAINT_MODE_CARLA_WET)
            widget.forceWhiteLabelGradientText()

            self.fParameterList.append([PARAMETER_DRYWET, widget])
            self.ui.w_knobs_right.layout().addWidget(widget)

        if self.fPluginInfo['hints'] & PLUGIN_CAN_VOLUME:
            widget = ScalableDial(self, PARAMETER_VOLUME)
            widget.setLabel("Volume")
            widget.setMinimum(0.0)
            widget.setMaximum(1.27)
            widget.setImage(3)
            widget.setCustomPaintMode(ScalableDial.CUSTOM_PAINT_MODE_CARLA_VOL)
            widget.forceWhiteLabelGradientText()

            self.fParameterList.append([PARAMETER_VOLUME, widget])
            self.ui.w_knobs_right.layout().addWidget(widget)

    def getFixedHeight(self):
        return 80

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setBrush(Qt.transparent)

        painter.setPen(QPen(QColor(50, 50, 50), 1))
        painter.drawRect(0, 1, self.width()-1, self.height()-3)

        painter.setPen(QPen(QColor(64, 64, 64), 1))
        painter.drawLine(0, 0, self.width(), 0)

        AbstractPluginSlot.paintEvent(self, event)

# ------------------------------------------------------------------------------------------------------------

def getColorAndSkinStyle(host, pluginId):
    pluginInfo  = host.get_plugin_info(pluginId)
    colorCategory = getColorFromCategory(pluginInfo['category'])

    savedSkin  = host.get_custom_data_value(pluginId, CUSTOM_DATA_TYPE_PROPERTY, "CarlaSkin")
    savedColor = host.get_custom_data_value(pluginId, CUSTOM_DATA_TYPE_PROPERTY, "CarlaColor")

    color = colorCategory
    if savedColor:
        try:
            color = tuple(int(i) for i in savedColor.split(";", 3))
        except Exception:
            pass

    if savedSkin:
        if savedSkin in ("sliders-dark", "sliders-light", "minimal-dark", "minimal-light"):
            return (color, savedSkin)
        if "slider" in savedSkin:
            return (color, "sliders-light" if "light" in savedSkin else "sliders-dark")
        if "light" in savedSkin:
            return (color, "minimal-light")

    return (color, "minimal-dark")

def createPluginSlot(parent, host, pluginId, options):
    skinColor, skinStyle = getColorAndSkinStyle(host, pluginId)

    if options['color'] is not None:
        skinColor = options['color']

    if options['skin']:
        skinStyle = options['skin']

    is_compact = bool("compact" in skinStyle or options.get('compact', False))
    is_layer = bool(
        options.get('layer_mode', False)
        or host.get_custom_data_value(pluginId, CUSTOM_DATA_TYPE_PROPERTY, "CarlaSkinLayerMode") == "true"
    )

    if skinStyle.startswith("sliders"):
        slot = PluginSlot_Sliders(parent, host, pluginId, skinColor, skinStyle)
        if is_compact:
            slot.setCompacted(True)
        if is_layer:
            slot.setLayerMode(True)
        return slot

    slot = PluginSlot_Minimal(parent, host, pluginId, skinColor, skinStyle)
    if is_compact:
        slot.setCompacted(True)
    if is_layer:
        slot.setLayerMode(True)
    return slot

class PluginSlot_Sliders(PluginSlot_Minimal):
    def __init__(self, parent, host, pluginId, skinColor, skinStyle):
        PluginSlot_Minimal.__init__(self, parent, host, pluginId, skinColor, skinStyle)
        self.setSliderMode(True)

# ------------------------------------------------------------------------------------------------------------
# Main Testing

if __name__ == '__main__':
    from carla_app import CarlaApplication
    from host_app import initHost, loadHostSettings


    app = CarlaApplication("Carla-Skins")
    host = initHost("Skins", None, False, False, False)
    loadHostSettings(host)

    host.engine_init("JACK", "Carla-Widgets")
    host.add_plugin(BINARY_NATIVE, PLUGIN_INTERNAL, "", "", "zynreverb", 0, None, PLUGIN_OPTIONS_NULL)
    host.set_active(0, True)

    gui = PluginSlot_Compact(None, host, 0, (0, 0, 0), "default")
    gui.testTimer()
    gui.show()

    app.exec_()

