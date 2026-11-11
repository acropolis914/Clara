#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2011-2025 Filipe Coelho <falktx@falktx.com>
# SPDX-License-Identifier: GPL-2.0-or-later

# Pure-PyQt6 port of source/frontend/dialogs/aboutdialog.cpp
# (no dependency on the Qt-linked native libcarla_frontend)

from ctypes import c_bool, c_char_p, c_void_p

from qt_compat import (
    QDialog,
    QDialogButtonBox,
    QFrame,
    QGridLayout,
    QLabel,
    QLineEdit,
    QTabWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
    Qt,
)
from carla_shared import CARLA_OS_MAC, CARLA_OS_WIN, CARLA_VERSION_STRING, CLARA_VERSION_STRING, gCarla
from carla_utils import *  # noqa: F401,F403  (repo convention, shared utils namespace)

# ------------------------------------------------------------------------------------------------------------
# Static text

def _token(name, fallback):
    from styles.theme_manager import theme_manager
    return theme_manager.engine.get_token(name, fallback) or fallback


_ABOUT_HTML = (
    "<div style='text-align: center; font-family: sans-serif; line-height: 1.6;'>"
    "<h2 style='margin: 0; color: {blue};'>Clara</h2>"
    "<p style='margin: 4px 0 12px 0; color: {subtext}; font-size: 11px;'>"
    "Modernized Audio Plugin Host & Patchbay (v%3 &bull; Carla %1%2)</p>"
    "<p style='margin: 8px 0; font-size: 12px;'>"
    "Maintained & Modernized by <b>acropolis914</b><br>"
    "Original Carla core created by <b>falkTX</b>"
    "</p>"
    "<p style='margin: 12px 0 4px 0;'>"
    "<a style='color: {blue}; text-decoration: none; font-weight: bold;' href='https://github.com/acropolis914/Clara'>🌐 GitHub Project Page</a>"
    "&nbsp;&nbsp;&bull;&nbsp;&nbsp;"
    "<a style='color: {green}; text-decoration: none; font-weight: bold;' href='https://github.com/acropolis914/Clara/releases'>🚀 Releases</a>"
    "&nbsp;&nbsp;&bull;&nbsp;&nbsp;"
    "<a style='color: {red}; text-decoration: none; font-weight: bold;' href='https://github.com/sponsors/acropolis914'>💖 Sponsor</a>"
    "</p>"
    "<p style='margin: 12px 0 0 0; font-size: 10px; color: {muted};'>"
    "Copyright &copy; 2011-2026 falkTX &amp; acropolis914<br>Licensed under GPLv2+"
    "</p>"
    "<p style='margin: 8px 0 0 0; font-size: 10px; color: {muted};'>"
    "UI icons by <a style='color: {muted}; text-decoration: underline;' href='https://lucide.dev'>Lucide</a> (ISC)"
    "</p>"
    "</div>"
)

_OSC_CMDS_HTML = (
    "<table>"
    "<tr><td>" "/set_active" "&nbsp;</td><td>&lt;i-value&gt;</td></tr>"
    "<tr><td>" "/set_drywet" "&nbsp;</td><td>&lt;f-value&gt;</td></tr>"
    "<tr><td>" "/set_volume" "&nbsp;</td><td>&lt;f-value&gt;</td></tr>"
    "<tr><td>" "/set_balance_left" "&nbsp;</td><td>&lt;f-value&gt;</td></tr>"
    "<tr><td>" "/set_balance_right" "&nbsp;</td><td>&lt;f-value&gt;</td></tr>"
    "<tr><td>" "/set_panning" "&nbsp;</td><td>&lt;f-value&gt;</td></tr>"
    "<tr><td>" "/set_parameter_value" "&nbsp;</td><td>&lt;i-index&gt; &lt;f-value&gt;</td></tr>"
    "<tr><td>" "/set_parameter_midi_cc" "&nbsp;</td><td>&lt;i-index&gt; &lt;i-cc&gt;</td></tr>"
    "<tr><td>" "/set_parameter_midi_channel" "&nbsp;</td><td>&lt;i-index&gt; &lt;i-channel&gt;</td></tr>"
    "<tr><td>" "/set_program" "&nbsp;</td><td>&lt;i-index&gt;</td></tr>"
    "<tr><td>" "/set_midi_program" "&nbsp;</td><td>&lt;i-index&gt;</td></tr>"
    "<tr><td>" "/note_on" "&nbsp;</td><td>&lt;i-channel&gt; &lt;i-note&gt; &lt;i-velo&gt;</td></tr>"
    "<tr><td>" "/note_off" "&nbsp;</td><td>&lt;i-note</td></tr>"
    "</table>"
)

_EXAMPLE_TEXT = "/Carla/2/set_parameter_value 5 1.0"
_EXAMPLE_HELP_TEXT = "<i>(as in this example, \"2\" is the plugin number and \"5\" the parameter)</i>"

_LADSPA_TEXT = "Everything! (Including LRDF)"
_DSSI_TEXT = "Everything! (Including CustomData/Chunks)"
_LV2_TEXT = (
    "About 110&#37; complete (using custom extensions)<br/>"
    "Implemented Feature/Extensions:"
    "<ul>"
    "<li>http://lv2plug.in/ns/ext/atom</li>"
    "<li>http://lv2plug.in/ns/ext/buf-size</li>"
    "<li>http://lv2plug.in/ns/ext/data-access</li>"
    "<li>http://lv2plug.in/ns/ext/event</li>"
    "<li>http://lv2plug.in/ns/ext/instance-access</li>"
    "<li>http://lv2plug.in/ns/ext/log</li>"
    "<li>http://lv2plug.in/ns/ext/midi</li>"
    "<li>http://lv2plug.in/ns/ext/options</li>"
    "<li>http://lv2plug.in/ns/ext/parameters</li>"
    "<li>http://lv2plug.in/ns/ext/port-props</li>"
    "<li>http://lv2plug.in/ns/ext/presets</li>"
    "<li>http://lv2plug.in/ns/ext/resize-port</li>"
    "<li>http://lv2plug.in/ns/ext/state</li>"
    "<li>http://lv2plug.in/ns/ext/time</li>"
    "<li>http://lv2plug.in/ns/ext/uri-map</li>"
    "<li>http://lv2plug.in/ns/ext/urid</li>"
    "<li>http://lv2plug.in/ns/ext/worker</li>"
    "<li>http://lv2plug.in/ns/extensions/ui</li>"
    "<li>http://lv2plug.in/ns/extensions/units</li>"
    "<li>http://home.gna.org/lv2dynparam/rtmempool/v1</li>"
    "<li>http://kxstudio.sf.net/ns/lv2ext/external-ui</li>"
    "<li>http://kxstudio.sf.net/ns/lv2ext/programs</li>"
    "<li>http://kxstudio.sf.net/ns/lv2ext/props</li>"
    "<li>http://kxstudio.sf.net/ns/lv2ext/rtmempool</li>"
    "<li>http://ll-plugins.nongnu.org/lv2/ext/midimap</li>"
    "<li>http://ll-plugins.nongnu.org/lv2/ext/miditype</li>"
    "</ul>"
)
_VST2_TEXT = "About 85&#37; complete (missing vst bank/presets and some minor stuff)"
_VST3_TEXT = "About 66&#37; complete"
_AU_TEXT = "About 20&#37; complete"

_ENGINE_NOT_RUNNING = "(Engine not running)"

# ------------------------------------------------------------------------------------------------------------
# Helpers


def _makeHLine():
    line = QFrame()
    line.setFrameShape(QFrame.HLine)
    line.setFrameShadow(QFrame.Sunken)
    line.setLineWidth(0)
    line.setMidLineWidth(1)
    return line


def _getOscUrl(funcName, hostHandle):
    # Calls into libcarla_utils (carla_get_host_osc_url_tcp/udp), returning None on any failure.
    try:
        func = getattr(gCarla.utils.lib, funcName)
        func.argtypes = [c_void_p]
        func.restype = c_char_p
        result = func(hostHandle)
        if result:
            return result.decode("utf-8")
    except Exception:
        pass
    return None


def _isEngineRunning(hostHandle):
    # Calls into libcarla_utils (carla_is_engine_running); the About dialog no longer
    # receives the host object, only its handle.
    try:
        func = gCarla.utils.lib.carla_is_engine_running
        func.argtypes = [c_void_p]
        func.restype = c_bool
        return bool(func(hostHandle))
    except Exception:
        return False


# ------------------------------------------------------------------------------------------------------------
# About Dialog


class AboutDialog(QDialog):
    def __init__(self, parent, hostHandle, isControl, isPlugin):
        QDialog.__init__(self, parent)
        self.setObjectName("AboutDialog")
        self.setWindowTitle("About Clara")

        extraInfo = ""
        if isControl:
            extraInfo = " - <b>%s</b>" % "OSC Bridge Version"
        elif isPlugin:
            extraInfo = " - <b>%s</b>" % "Plugin Version"

        # ------------------------------------------------------------------------------------------------
        # About tab

        self.l_icons = QLabel()
        self.l_icons.setObjectName("l_icons")
        self.l_icons.setAlignment(Qt.AlignCenter)
        self.l_icons.hide()

        self.l_about = QLabel()
        self.l_about.setObjectName("l_about")
        self.l_about.setTextFormat(Qt.RichText)
        self.l_about.setOpenExternalLinks(True)
        self.l_about.setText(
            _ABOUT_HTML.replace("%1", CARLA_VERSION_STRING)
            .replace("%2", extraInfo)
            .replace("%3", CLARA_VERSION_STRING)
            .format(blue=_token("blue", "#89b4fa"),
                    subtext=_token("text-secondary", "#a6adc8"),
                    green=_token("green", "#a6e3a1"),
                    red=_token("red", "#f38ba8"),
                    muted=_token("text-muted", "#6c7086"))
        )

        self.l_extended = QLabel()
        self.l_extended.setObjectName("l_extended")
        self.l_extended.setTextFormat(Qt.RichText)
        self.l_extended.setWordWrap(True)
        self.l_extended.setMargin(1)
        self.l_extended.setIndent(1)

        aboutTab = QWidget()
        aboutTab.setObjectName("about")
        aboutLayout = QGridLayout(aboutTab)
        aboutLayout.setColumnStretch(0, 1)
        aboutLayout.setColumnStretch(2, 1)
        aboutLayout.addWidget(self.l_icons, 1, 0, 1, 3)
        aboutLayout.addWidget(self.l_about, 2, 1)
        aboutLayout.addWidget(self.l_extended, 3, 0, 1, 3)
        aboutLayout.setRowStretch(0, 1)
        aboutLayout.setRowStretch(4, 1)

        # ------------------------------------------------------------------------------------------------
        # OSC tab

        self.le_osc_url_tcp = QLineEdit()
        self.le_osc_url_tcp.setObjectName("le_osc_url_tcp")
        self.le_osc_url_tcp.setFrame(False)
        self.le_osc_url_tcp.setReadOnly(True)

        self.le_osc_url_udp = QLineEdit()
        self.le_osc_url_udp.setObjectName("le_osc_url_udp")
        self.le_osc_url_udp.setFrame(False)
        self.le_osc_url_udp.setReadOnly(True)

        self.l_osc_cmds = QLabel()
        self.l_osc_cmds.setObjectName("l_osc_cmds")
        self.l_osc_cmds.setAlignment(Qt.AlignLeft | Qt.AlignTop)
        self.l_osc_cmds.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self.l_osc_cmds.setText(_OSC_CMDS_HTML)

        self.l_example = QLabel()
        self.l_example.setObjectName("l_example")
        self.l_example.setText(_EXAMPLE_TEXT)

        self.l_example_help = QLabel()
        self.l_example_help.setObjectName("l_example_help")
        self.l_example_help.setText(_EXAMPLE_HELP_TEXT)

        oscLabelHostUrls = QLabel("Host URLs:")
        oscLabelHostUrls.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        oscLabelCommands = QLabel("Valid commands:")
        oscLabelCommands.setAlignment(Qt.AlignRight | Qt.AlignTop)
        oscLabelExample = QLabel("Example:")
        oscLabelExample.setAlignment(Qt.AlignRight | Qt.AlignVCenter)

        oscTab = QWidget()
        oscTab.setObjectName("osc")
        oscLayout = QGridLayout(oscTab)
        oscLayout.addWidget(oscLabelHostUrls, 0, 0)
        oscLayout.addWidget(self.le_osc_url_tcp, 0, 1)
        oscLayout.addWidget(self.le_osc_url_udp, 1, 1)
        oscLayout.addWidget(oscLabelCommands, 3, 0)
        oscLayout.addWidget(self.l_osc_cmds, 3, 1)
        oscLayout.addWidget(oscLabelExample, 4, 0)
        oscLayout.addWidget(self.l_example, 4, 1)
        oscLayout.addWidget(self.l_example_help, 5, 1)
        oscLayout.setRowStretch(6, 1)

        # ------------------------------------------------------------------------------------------------
        # Features tab

        self.l_ladspa = QLabel(_LADSPA_TEXT)
        self.l_ladspa.setObjectName("l_ladspa")
        self.l_ladspa.setAlignment(Qt.AlignLeft | Qt.AlignTop)
        self.l_dssi = QLabel(_DSSI_TEXT)
        self.l_dssi.setObjectName("l_dssi")
        self.l_dssi.setAlignment(Qt.AlignLeft | Qt.AlignTop)
        self.l_lv2 = QLabel(_LV2_TEXT)
        self.l_lv2.setObjectName("l_lv2")
        self.l_lv2.setTextFormat(Qt.RichText)
        self.l_lv2.setAlignment(Qt.AlignLeft | Qt.AlignTop)
        self.l_lv2.setWordWrap(True)
        self.l_vst2 = QLabel(_VST2_TEXT)
        self.l_vst2.setObjectName("l_vst2")
        self.l_vst2.setTextFormat(Qt.RichText)
        self.l_vst2.setAlignment(Qt.AlignLeft | Qt.AlignTop)
        self.l_vst3 = QLabel(_VST3_TEXT)
        self.l_vst3.setObjectName("l_vst3")
        self.l_vst3.setTextFormat(Qt.RichText)
        self.l_vst3.setAlignment(Qt.AlignLeft | Qt.AlignTop)
        self.l_au = QLabel(_AU_TEXT)
        self.l_au.setObjectName("l_au")
        self.l_au.setTextFormat(Qt.RichText)
        self.l_au.setAlignment(Qt.AlignLeft | Qt.AlignTop)

        self.lid_ladspa = QLabel("LADSPA:")
        self.lid_ladspa.setAlignment(Qt.AlignRight | Qt.AlignTop)
        self.lid_dssi = QLabel("DSSI:")
        self.lid_dssi.setAlignment(Qt.AlignRight | Qt.AlignTop)
        self.lid_lv2 = QLabel("LV2:")
        self.lid_lv2.setAlignment(Qt.AlignRight | Qt.AlignTop)
        self.lid_vst2 = QLabel("VST2:")
        self.lid_vst2.setAlignment(Qt.AlignRight | Qt.AlignTop)
        self.lid_vst3 = QLabel("VST3:")
        self.lid_vst3.setAlignment(Qt.AlignRight | Qt.AlignTop)
        self.lid_au = QLabel("AU/AudioUnit:")
        self.lid_au.setAlignment(Qt.AlignRight | Qt.AlignTop)

        self.line_vst3 = _makeHLine()
        self.line_vst3.setObjectName("line_vst3")

        featuresTab = QWidget()
        featuresTab.setObjectName("features")
        featuresLayout = QGridLayout(featuresTab)
        featuresLayout.setColumnStretch(1, 1)
        featuresLayout.addWidget(self.lid_ladspa, 0, 0)
        featuresLayout.addWidget(self.l_ladspa, 0, 1)
        featuresLayout.addWidget(_makeHLine(), 1, 0, 1, 2)
        featuresLayout.addWidget(self.lid_dssi, 2, 0)
        featuresLayout.addWidget(self.l_dssi, 2, 1)
        featuresLayout.addWidget(_makeHLine(), 3, 0, 1, 2)
        featuresLayout.addWidget(self.lid_lv2, 4, 0)
        featuresLayout.addWidget(self.l_lv2, 4, 1)
        featuresLayout.addWidget(_makeHLine(), 5, 0, 1, 2)
        featuresLayout.addWidget(self.lid_vst2, 6, 0)
        featuresLayout.addWidget(self.l_vst2, 6, 1)
        featuresLayout.addWidget(_makeHLine(), 7, 0, 1, 2)
        featuresLayout.addWidget(self.lid_vst3, 8, 0)
        featuresLayout.addWidget(self.l_vst3, 8, 1)
        featuresLayout.addWidget(self.line_vst3, 9, 0, 1, 2)
        featuresLayout.addWidget(self.lid_au, 10, 0)
        featuresLayout.addWidget(self.l_au, 10, 1)
        featuresLayout.setRowStretch(11, 1)

        # ------------------------------------------------------------------------------------------------
        # License tab

        licenseTab = QWidget()
        licenseTab.setObjectName("tab_license")
        licenseText = QTextEdit()
        licenseText.setObjectName("plainTextEdit")
        licenseText.setReadOnly(True)
        licenseText.setUndoRedoEnabled(False)
        licenseLayout = QVBoxLayout(licenseTab)
        licenseLayout.addWidget(licenseText)

        # ------------------------------------------------------------------------------------------------
        # Tabs + buttons

        self.tabWidget = QTabWidget()
        self.tabWidget.setObjectName("tabWidget")
        self.tabWidget.addTab(aboutTab, "About")
        self.tabWidget.addTab(oscTab, "OSC")
        self.tabWidget.addTab(featuresTab, "Features")
        self.tabWidget.addTab(licenseTab, "License")

        self.buttonBox = QDialogButtonBox()
        self.buttonBox.setObjectName("buttonBox")
        self.buttonBox.setOrientation(Qt.Horizontal)
        self.buttonBox.setStandardButtons(QDialogButtonBox.Ok)
        self.buttonBox.accepted.connect(self.accept)
        self.buttonBox.rejected.connect(self.reject)

        mainLayout = QVBoxLayout(self)
        mainLayout.addWidget(self.tabWidget)
        mainLayout.addWidget(self.buttonBox)

        # ------------------------------------------------------------------------------------------------
        # Conditional content

        if isControl or isPlugin:
            self.l_extended.hide()
            self.tabWidget.removeTab(3)
            self.tabWidget.removeTab(2)
        else:
            tcpUrl = _ENGINE_NOT_RUNNING
            udpUrl = _ENGINE_NOT_RUNNING

            if _isEngineRunning(hostHandle):
                tcpUrl = _getOscUrl("carla_get_host_osc_url_tcp", hostHandle) or tcpUrl
                udpUrl = _getOscUrl("carla_get_host_osc_url_udp", hostHandle) or udpUrl

            self.le_osc_url_tcp.setText(tcpUrl)
            self.le_osc_url_udp.setText(udpUrl)

        try:
            licenseHtml = gCarla.utils.get_complete_license_text() or ""
        except Exception:
            licenseHtml = ""

        self.l_extended.setText(licenseHtml)
        licenseText.setHtml(licenseHtml)

        if CARLA_OS_MAC:
            self.l_au.setText(_AU_TEXT)
        else:
            self.line_vst3.hide()
            self.l_au.hide()
            self.lid_au.hide()

        # ------------------------------------------------------------------------------------------------
        # Sizing / window flags

        # 3rd tab is usually longer than the 1st, adjust appropriately
        self.tabWidget.setCurrentIndex(2)
        self.adjustSize()
        self.tabWidget.setCurrentIndex(0)
        self.setFixedSize(self.size())

        flags = self.windowFlags()
        flags &= ~Qt.WindowContextHelpButtonHint
        if CARLA_OS_WIN:
            flags |= Qt.MSWindowsFixedSizeDialogHint
        self.setWindowFlags(flags)

        if CARLA_OS_MAC and parent is not None:
            self.setWindowModality(Qt.WindowModal)


# ------------------------------------------------------------------------------------------------------------


def createAndExecAboutDialog(parent, hostHandle, isControl, isPlugin):
    dialog = AboutDialog(parent, hostHandle, isControl, isPlugin)
    dialog.exec()
    return None
