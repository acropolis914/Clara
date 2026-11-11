#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2011-2025 Filipe Coelho <falktx@falktx.com>
# SPDX-License-Identifier: GPL-2.0-or-later

# ------------------------------------------------------------------------------------------------------------
# Imports (Global)

import os
import sys
from math import fmod

# ------------------------------------------------------------------------------------------------------------
# Imports (Signal)
from signal import SIGINT, SIGTERM, signal

try:
    from signal import SIGUSR1
    haveSIGUSR1 = True
except Exception:
    haveSIGUSR1 = False

# ------------------------------------------------------------------------------------------------------------
# Imports (PyQt)

from qt_compat import (
    PYQT_VERSION_STR,
    QDir,
    QFileDialog,
    QIcon,
    QMessageBox,
    QSettings,
    QT_VERSION,
    QT_VERSION_STR,
    qFatal,
    qWarning,
    qt_config,
)
# pylint: disable=possibly-used-before-assignment

# ------------------------------------------------------------------------------------------------------------
# Imports (Custom)

from carla_backend import (
    CARLA_OS_64BIT,
    CARLA_OS_HAIKU,
    CARLA_OS_MAC,
    CARLA_OS_WIN,
    CARLA_VERSION_STRING,
    MAX_DEFAULT_PARAMETERS,
    ENGINE_PROCESS_MODE_MULTIPLE_CLIENTS,
    ENGINE_PROCESS_MODE_PATCHBAY,
    ENGINE_TRANSPORT_MODE_INTERNAL,
    ENGINE_TRANSPORT_MODE_JACK,
)

def _get_clara_version():
    base_version = "1.2.1"
    try:
        import subprocess
        tag = subprocess.check_output(
            ["git", "describe", "--tags", "--exact-match"],
            cwd=os.path.dirname(__file__),
            stderr=subprocess.DEVNULL
        ).decode("utf-8").strip()
        if tag.startswith("v"):
            tag = tag[1:]
        if tag:
            return tag
    except Exception:
        pass
    return base_version

CLARA_VERSION_STRING = _get_clara_version()

# ------------------------------------------------------------------------------------------------------------
# Startup banner

def printStartupBanner(extraInfo=None):
    """Print the Clara startup banner, crediting the underlying Carla version.

    Shows "Clara vX.Y.Z" followed by "based on Carla version A.B.C", rendered with
    rich when available and falling back to plain text otherwise. extraInfo is an
    optional list of (label, value) rows shown underneath the version lines.
    """
    claraVer = CLARA_VERSION_STRING
    carlaVer = CARLA_VERSION_STRING

    try:
        from rich.console import Console
        from rich.text import Text

        body = Text()
        body.append("Clara ", style="bold white")
        body.append(f"v{claraVer}", style="bold bright_magenta")
        body.append("\n\n")
        body.append("based on ", style="dim")
        body.append("Carla", style="bold cyan")
        body.append(" version ", style="dim")
        body.append(carlaVer, style="bold cyan")

        if extraInfo:
            body.append("\n")
            for label, value in extraInfo:
                body.append(f"\n  {label}: ", style="dim")
                body.append(str(value), style="dim white")

        Console().print(body)
        return
    except ImportError:
        pass

    print(f"Clara v{claraVer}")
    print(f"based on Carla version {carlaVer}")
    if extraInfo:
        for label, value in extraInfo:
            print(f"  {label}: {value}")

# ------------------------------------------------------------------------------------------------------------
# Config

# These will be modified during install
X_LIBDIR_X = None
X_DATADIR_X = None

# ------------------------------------------------------------------------------------------------------------
# Platform specific stuff

if CARLA_OS_WIN:
    WINDIR = os.getenv("WINDIR")

# ------------------------------------------------------------------------------------------------------------
# Set TMP

envTMP = os.getenv("TMP")

if envTMP is None:
    if CARLA_OS_WIN:
        qWarning("TMP variable not set")
    TMP = QDir.tempPath()
else:
    TMP = envTMP

if not os.path.exists(TMP):
    qWarning("TMP does not exist")
    TMP = "/"

del envTMP

# ------------------------------------------------------------------------------------------------------------
# Set HOME

envHOME = os.getenv("HOME")

if envHOME is None:
    if not CARLA_OS_WIN:
        qWarning("HOME variable not set")
    HOME = QDir.toNativeSeparators(QDir.homePath())
else:
    HOME = envHOME

if not os.path.exists(HOME):
    qWarning("HOME does not exist")
    HOME = TMP

del envHOME

# ------------------------------------------------------------------------------------------------------------
# Set PATH

envPATH = os.getenv("PATH")

if envPATH is None:
    qWarning("PATH variable not set")
    if CARLA_OS_MAC:
        PATH = ("/opt/local/bin", "/usr/local/bin", "/usr/bin", "/bin")
    elif CARLA_OS_WIN:
        PATH = (os.path.join(WINDIR, "system32"), WINDIR)
    else:
        PATH = ("/usr/local/bin", "/usr/bin", "/bin")
else:
    PATH = envPATH.split(os.pathsep)

del envPATH

# ------------------------------------------------------------------------------------------------------------
# Static MIDI CC list

MIDI_CC_LIST = (
    "01 [0x01] Modulation",
    "02 [0x02] Breath",
    "04 [0x04] Foot",
    "05 [0x05] Portamento",
    "07 [0x07] Volume",
    "08 [0x08] Balance",
    "10 [0x0A] Pan",
    "11 [0x0B] Expression",
    "12 [0x0C] FX Control 1",
    "13 [0x0D] FX Control 2",
    "16 [0x10] General Purpose 1",
    "17 [0x11] General Purpose 2",
    "18 [0x12] General Purpose 3",
    "19 [0x13] General Purpose 4",
    "70 [0x46] Control 1 [Variation]",
    "71 [0x47] Control 2 [Timbre]",
    "72 [0x48] Control 3 [Release]",
    "73 [0x49] Control 4 [Attack]",
    "74 [0x4A] Control 5 [Brightness]",
    "75 [0x4B] Control 6 [Decay]",
    "76 [0x4C] Control 7 [Vib Rate]",
    "77 [0x4D] Control 8 [Vib Depth]",
    "78 [0x4E] Control 9 [Vib Delay]",
    "79 [0x4F] Control 10 [Undefined]",
    "80 [0x50] General Purpose 5",
    "81 [0x51] General Purpose 6",
    "82 [0x52] General Purpose 7",
    "83 [0x53] General Purpose 8",
    "84 [0x54] Portamento Control",
    "91 [0x5B] FX 1 Depth [Reverb]",
    "92 [0x5C] FX 2 Depth [Tremolo]",
    "93 [0x5D] FX 3 Depth [Chorus]",
    "94 [0x5E] FX 4 Depth [Detune]",
    "95 [0x5F] FX 5 Depth [Phaser]"
)

MAX_MIDI_CC_LIST_ITEM = 95

# ------------------------------------------------------------------------------------------------------------
# PatchCanvas defines

CANVAS_ANTIALIASING_SMALL = 1
CANVAS_EYECANDY_SMALL     = 1

# ------------------------------------------------------------------------------------------------------------
# Carla Settings keys

CARLA_KEY_MAIN_PROJECT_FOLDER   = "Main/ProjectFolder"   # str
CARLA_KEY_MAIN_USE_PRO_THEME    = "Main/UseProTheme"     # bool
CARLA_KEY_MAIN_PRO_THEME_COLOR  = "Main/ProThemeColor"   # str
CARLA_KEY_MAIN_USE_SYSTEM_THEME = "Main/UseSystemTheme" # bool
CARLA_KEY_MAIN_APP_THEME        = "Main/AppTheme"        # str
CARLA_KEY_MAIN_REFRESH_INTERVAL = "Main/RefreshInterval" # int
CARLA_KEY_STATUSBAR_SPARKLINE        = "Statusbar/SparklineEnabled"  # bool
CARLA_KEY_STATUSBAR_SPARKLINE_WINDOW = "Statusbar/SparklineWindow"   # int seconds
CARLA_DEFAULT_STATUSBAR_SPARKLINE        = True
CARLA_DEFAULT_STATUSBAR_SPARKLINE_WINDOW = 60
CARLA_KEY_MAIN_CONFIRM_EXIT     = "Main/ConfirmExit"     # bool
CARLA_KEY_MAIN_CLASSIC_SKIN     = "Main/ClassicSkin"     # bool
CARLA_KEY_MAIN_SHOW_LOGS        = "Main/ShowLogs"        # bool
CARLA_KEY_MAIN_SYSTEM_ICONS     = "Main/SystemIcons"     # bool
CARLA_KEY_MAIN_MINIMIZE_TO_TRAY = "Main/MinimizeToTray" # bool
CARLA_KEY_MAIN_EXPERIMENTAL     = "Main/Experimental"    # bool
CARLA_KEY_MAIN_RECENT_PROJECTS   = "Main/RecentProjects"  # str list / json
CARLA_KEY_MAIN_AUTOSAVE_ENABLED  = "Main/AutosaveEnabled" # bool
CARLA_KEY_MAIN_AUTOSAVE_INTERVAL = "Main/AutosaveInterval"# int (minutes)
CARLA_KEY_MAIN_AUTOSAVE_MAX      = "Main/AutosaveMax"     # int
CARLA_KEY_MAIN_PROJECT_FORMAT    = "Main/ProjectFormat"   # str (xml or json)
CARLA_KEY_MAIN_LOG_TO_CONSOLE     = "Main/LogToConsole"    # bool

CARLA_KEY_CANVAS_THEME             = "Canvas/Theme"           # str
CARLA_KEY_CANVAS_SIZE              = "Canvas/Size"            # str "NxN"
CARLA_KEY_CANVAS_USE_BEZIER_LINES  = "Canvas/UseBezierLines"  # bool
CARLA_KEY_CANVAS_AUTO_HIDE_GROUPS  = "Canvas/AutoHideGroups"  # bool
CARLA_KEY_CANVAS_AUTO_SELECT_ITEMS = "Canvas/AutoSelectItems" # bool
CARLA_KEY_CANVAS_EYE_CANDY         = "Canvas/EyeCandy2"       # bool
CARLA_KEY_CANVAS_FANCY_EYE_CANDY   = "Canvas/FancyEyeCandy"   # bool
CARLA_KEY_CANVAS_USE_OPENGL        = "Canvas/UseOpenGL"       # bool
CARLA_KEY_CANVAS_ANTIALIASING      = "Canvas/Antialiasing"    # enum
CARLA_KEY_CANVAS_HQ_ANTIALIASING   = "Canvas/HQAntialiasing"  # bool
CARLA_KEY_CANVAS_INLINE_DISPLAYS   = "Canvas/InlineDisplays"  # bool
CARLA_KEY_CANVAS_FULL_REPAINTS     = "Canvas/FullRepaints"    # bool
CARLA_KEY_CANVAS_ROUNDED_NODES     = "Canvas/RoundedNodes"    # bool
CARLA_KEY_CANVAS_NODE_RADIUS       = "Canvas/NodeRadius"      # int
CARLA_KEY_CANVAS_LINE_STYLE         = "Canvas/LineStyle"       # str (registered line algorithm name)
CARLA_KEY_CANVAS_LINE_STROKE        = "Canvas/LineStroke"      # str ("solid", "dotted", "dashed")
CARLA_KEY_CANVAS_LINE_OPACITY       = "Canvas/LineOpacity"     # int (20 - 100)
CARLA_KEY_CANVAS_SELECTED_LINE_ENABLED   = "Canvas/SelectedLineEnabled"   # bool
CARLA_KEY_CANVAS_SELECTED_LINE_STYLE     = "Canvas/SelectedLineStyle"     # str ("" = inherit)
CARLA_KEY_CANVAS_SELECTED_LINE_STROKE    = "Canvas/SelectedLineStroke"    # str ("inherit" or solid/dotted/dashed)
CARLA_KEY_CANVAS_SELECTED_LINE_THICKNESS = "Canvas/SelectedLineThickness" # int (2 - 12)
CARLA_KEY_CANVAS_SELECTED_LINE_SKIP_ALL  = "Canvas/SelectedLineSkipAll"   # bool
CARLA_KEY_CANVAS_ARRANGE_STYLE      = "Canvas/ArrangeStyle"    # str (registered arrange algorithm name)
CARLA_KEY_CANVAS_NODE_MIN_WIDTH     = "Canvas/NodeMinWidth"    # int (100 - 350)
CARLA_KEY_CANVAS_SIGNAL_FLOW        = "Canvas/SignalFlow"      # bool (animated signal/event flow)
CARLA_KEY_CANVAS_SIGNAL_FLOW_EXT    = "Canvas/SignalFlowExternal"  # bool (capture levels for external/pipewire nodes)
CARLA_KEY_CANVAS_BOX_SHADOWS        = "Canvas/BoxShadows"      # bool (drop shadows beneath node boxes)
CARLA_KEY_CANVAS_SHADOW_OPACITY     = "Canvas/ShadowOpacity"   # int (0 - 100, scales the theme alpha)
CARLA_KEY_CANVAS_SHADOW_SPREAD      = "Canvas/ShadowSpread"    # int (0 - 40, blur in px)
CARLA_KEY_CANVAS_SHADOW_DISTANCE    = "Canvas/ShadowDistance"  # int (0 - 20, vertical offset in px)
CARLA_KEY_CANVAS_SHADOW_DRAG        = "Canvas/ShadowWhileDragging"  # bool
CARLA_KEY_CANVAS_NODE_TRANSITIONS   = "Canvas/NodeTransitions" # bool (fade/scale animations for node changes)
CARLA_KEY_CANVAS_SHOW_EXTERNAL      = "Canvas/ShowExternal"    # bool (show PipeWire/JACK external nodes in patchbay)

CARLA_KEY_ENGINE_DRIVER_PREFIX         = "Engine/Driver-"
CARLA_KEY_ENGINE_AUDIO_DRIVER          = "Engine/AudioDriver"         # str
CARLA_KEY_ENGINE_AUDIO_DEVICE          = "Engine/AudioDevice"         # str
CARLA_KEY_ENGINE_BUFFER_SIZE           = "Engine/BufferSize"          # int
CARLA_KEY_ENGINE_SAMPLE_RATE           = "Engine/SampleRate"          # int
CARLA_KEY_ENGINE_TRIPLE_BUFFER         = "Engine/TripleBuffer"        # bool
CARLA_KEY_ENGINE_PROCESS_MODE          = "Engine/ProcessMode"         # enum
CARLA_KEY_ENGINE_TRANSPORT_MODE        = "Engine/TransportMode"       # enum
CARLA_KEY_ENGINE_TRANSPORT_EXTRA       = "Engine/TransportExtra"      # str
CARLA_KEY_ENGINE_FORCE_STEREO          = "Engine/ForceStereo"         # bool
CARLA_KEY_ENGINE_PREFER_PLUGIN_BRIDGES = "Engine/PreferPluginBridges" # bool
CARLA_KEY_ENGINE_PREFER_UI_BRIDGES     = "Engine/PreferUiBridges"     # bool
CARLA_KEY_ENGINE_MANAGE_UIS            = "Engine/ManageUIs"           # bool
CARLA_KEY_ENGINE_UIS_ALWAYS_ON_TOP     = "Engine/UIsAlwaysOnTop"      # bool
CARLA_KEY_ENGINE_MAX_PARAMETERS        = "Engine/MaxParameters"       # int
CARLA_KEY_ENGINE_RESET_XRUNS           = "Engine/ResetXruns"          # bool
CARLA_KEY_ENGINE_UI_BRIDGES_TIMEOUT    = "Engine/UiBridgesTimeout"    # int

CARLA_KEY_OSC_ENABLED          = "OSC/Enabled"
CARLA_KEY_OSC_TCP_PORT_ENABLED = "OSC/TCPEnabled"
CARLA_KEY_OSC_TCP_PORT_NUMBER  = "OSC/TCPNumber"
CARLA_KEY_OSC_TCP_PORT_RANDOM  = "OSC/TCPRandom"
CARLA_KEY_OSC_UDP_PORT_ENABLED = "OSC/UDPEnabled"
CARLA_KEY_OSC_UDP_PORT_NUMBER  = "OSC/UDPNumber"
CARLA_KEY_OSC_UDP_PORT_RANDOM  = "OSC/UDPRandom"

CARLA_KEY_PATHS_AUDIO = "Paths/Audio"
CARLA_KEY_PATHS_MIDI  = "Paths/MIDI"

CARLA_KEY_PATHS_LADSPA = "Paths/LADSPA"
CARLA_KEY_PATHS_DSSI   = "Paths/DSSI"
CARLA_KEY_PATHS_LV2    = "Paths/LV2"
CARLA_KEY_PATHS_VST2   = "Paths/VST2"
CARLA_KEY_PATHS_VST3   = "Paths/VST3"
CARLA_KEY_PATHS_CLAP   = "Paths/CLAP"
CARLA_KEY_PATHS_SF2    = "Paths/SF2"
CARLA_KEY_PATHS_SFZ    = "Paths/SFZ"
CARLA_KEY_PATHS_JSFX   = "Paths/JSFX"

CARLA_KEY_WINE_EXECUTABLE      = "Wine/Executable"     # str
CARLA_KEY_WINE_AUTO_PREFIX     = "Wine/AutoPrefix"     # bool
CARLA_KEY_WINE_FALLBACK_PREFIX = "Wine/FallbackPrefix" # str
CARLA_KEY_WINE_RT_PRIO_ENABLED = "Wine/RtPrioEnabled"  # bool
CARLA_KEY_WINE_BASE_RT_PRIO    = "Wine/BaseRtPrio"     # int
CARLA_KEY_WINE_SERVER_RT_PRIO  = "Wine/ServerRtPrio"   # int

CARLA_KEY_EXPERIMENTAL_PLUGIN_BRIDGES        = "Experimental/PluginBridges"       # bool
CARLA_KEY_EXPERIMENTAL_WINE_BRIDGES          = "Experimental/WineBridges"         # bool
CARLA_KEY_EXPERIMENTAL_JACK_APPS             = "Experimental/JackApplications"    # bool
CARLA_KEY_EXPERIMENTAL_EXPORT_LV2            = "Experimental/ExportLV2"           # bool
CARLA_KEY_EXPERIMENTAL_PREVENT_BAD_BEHAVIOUR = "Experimental/PreventBadBehaviour" # bool
CARLA_KEY_EXPERIMENTAL_LOAD_LIB_GLOBAL       = "Experimental/LoadLibGlobal"       # bool

# if pro theme is on and color is black
CARLA_KEY_CUSTOM_PAINTING = "UseCustomPainting" # bool

# ------------------------------------------------------------------------------------------------------------
# Carla Settings defaults

# Main
CARLA_DEFAULT_MAIN_PROJECT_FOLDER   = HOME
CARLA_DEFAULT_MAIN_USE_PRO_THEME    = True
CARLA_DEFAULT_MAIN_PRO_THEME_COLOR  = "Black"
CARLA_DEFAULT_MAIN_USE_SYSTEM_THEME = False
CARLA_DEFAULT_MAIN_APP_THEME        = "Catppuccin Macchiato"
CARLA_DEFAULT_MAIN_REFRESH_INTERVAL = 20
CARLA_DEFAULT_MAIN_CONFIRM_EXIT     = False
CARLA_DEFAULT_MAIN_CLASSIC_SKIN     = False
CARLA_DEFAULT_MAIN_SHOW_LOGS        = bool(not CARLA_OS_WIN)
CARLA_DEFAULT_MAIN_SYSTEM_ICONS     = False
CARLA_DEFAULT_MAIN_MINIMIZE_TO_TRAY = True
CARLA_DEFAULT_MAIN_EXPERIMENTAL     = False
CARLA_DEFAULT_MAIN_AUTOSAVE_ENABLED  = True
CARLA_DEFAULT_MAIN_AUTOSAVE_INTERVAL = 3
CARLA_DEFAULT_MAIN_AUTOSAVE_MAX      = 5
CARLA_DEFAULT_MAIN_PROJECT_FORMAT    = "xml"
CARLA_DEFAULT_MAIN_LOG_TO_CONSOLE     = True

# Canvas
CARLA_DEFAULT_CANVAS_THEME             = "Catppuccin Macchiato"
CARLA_DEFAULT_CANVAS_SIZE              = "3100x2400"
CARLA_DEFAULT_CANVAS_SIZE_WIDTH        = 3100
CARLA_DEFAULT_CANVAS_SIZE_HEIGHT       = 2400
CARLA_DEFAULT_CANVAS_USE_BEZIER_LINES  = True
CARLA_DEFAULT_CANVAS_AUTO_HIDE_GROUPS  = True
CARLA_DEFAULT_CANVAS_AUTO_SELECT_ITEMS = False
CARLA_DEFAULT_CANVAS_EYE_CANDY         = True
CARLA_DEFAULT_CANVAS_FANCY_EYE_CANDY   = True
CARLA_DEFAULT_CANVAS_USE_OPENGL        = True
CARLA_DEFAULT_CANVAS_ANTIALIASING      = CANVAS_ANTIALIASING_SMALL
CARLA_DEFAULT_CANVAS_HQ_ANTIALIASING   = False
CARLA_DEFAULT_CANVAS_INLINE_DISPLAYS   = False
CARLA_DEFAULT_CANVAS_FULL_REPAINTS     = False
CARLA_DEFAULT_CANVAS_ROUNDED_NODES     = True
CARLA_DEFAULT_CANVAS_NODE_RADIUS       = 8
CARLA_DEFAULT_CANVAS_LINE_STYLE        = "bezier"
CARLA_DEFAULT_CANVAS_LINE_STROKE       = "solid"
CARLA_DEFAULT_CANVAS_LINE_OPACITY      = 100
CARLA_DEFAULT_CANVAS_SELECTED_LINE_ENABLED   = False
CARLA_DEFAULT_CANVAS_SELECTED_LINE_STYLE     = ""
CARLA_DEFAULT_CANVAS_SELECTED_LINE_STROKE    = "inherit"
CARLA_DEFAULT_CANVAS_SELECTED_LINE_THICKNESS = 5
CARLA_DEFAULT_CANVAS_SELECTED_LINE_SKIP_ALL  = True
CARLA_DEFAULT_CANVAS_ARRANGE_STYLE     = "flow"
CARLA_DEFAULT_CANVAS_NODE_MIN_WIDTH    = 160
CARLA_DEFAULT_CANVAS_BOX_SHADOWS        = True
CARLA_DEFAULT_CANVAS_SHADOW_OPACITY     = 100
CARLA_DEFAULT_CANVAS_SHADOW_SPREAD      = 14
CARLA_DEFAULT_CANVAS_SHADOW_DISTANCE    = 3
CARLA_DEFAULT_CANVAS_SHADOW_DRAG        = False
CARLA_DEFAULT_CANVAS_NODE_TRANSITIONS   = True
CARLA_DEFAULT_CANVAS_SIGNAL_FLOW        = False
CARLA_DEFAULT_CANVAS_SHOW_EXTERNAL      = True

# Engine
CARLA_DEFAULT_FORCE_STEREO          = False
CARLA_DEFAULT_PREFER_PLUGIN_BRIDGES = False
CARLA_DEFAULT_PREFER_UI_BRIDGES     = True
CARLA_DEFAULT_MANAGE_UIS            = True
CARLA_DEFAULT_UIS_ALWAYS_ON_TOP     = False
CARLA_DEFAULT_MAX_PARAMETERS        = MAX_DEFAULT_PARAMETERS
CARLA_DEFAULT_RESET_XRUNS           = False
CARLA_DEFAULT_UI_BRIDGES_TIMEOUT    = 4000

CARLA_DEFAULT_AUDIO_BUFFER_SIZE     = 512
CARLA_DEFAULT_AUDIO_SAMPLE_RATE     = 44100
CARLA_DEFAULT_AUDIO_TRIPLE_BUFFER   = False

if CARLA_OS_HAIKU:
    CARLA_DEFAULT_AUDIO_DRIVER = "SDL"
elif CARLA_OS_MAC:
    CARLA_DEFAULT_AUDIO_DRIVER = "CoreAudio"
elif CARLA_OS_WIN:
    CARLA_DEFAULT_AUDIO_DRIVER = "Windows Audio"
else:
    def _detect_default_linux_audio_driver():
        import shutil, glob, ctypes.util
        if shutil.which("jackd") or shutil.which("jackdbus") or shutil.which("pw-jack"):
            return "JACK"
        if os.path.exists("/usr/bin/jackd") or os.path.exists("/usr/bin/jackdbus") or os.path.exists("/usr/bin/pw-jack"):
            return "JACK"
        # PipeWire active session socket or PipeWire-JACK library presence (e.g. Fedora / Bazzite / Debian)
        runtime_dir = os.environ.get("XDG_RUNTIME_DIR") or f"/run/user/{os.getuid()}"
        if glob.glob(os.path.join(runtime_dir, "pipewire-*")):
            return "JACK"
        for p in ("/usr/lib64/pipewire-0.3/jack", "/usr/lib/pipewire-0.3/jack", "/usr/lib/x86_64-linux-gnu/pipewire-0.3/jack", "/usr/lib/aarch64-linux-gnu/pipewire-0.3/jack"):
            if os.path.isdir(p):
                return "JACK"
        if ctypes.util.find_library("jack"):
            return "JACK"
        return "PulseAudio"

    CARLA_DEFAULT_AUDIO_DRIVER = _detect_default_linux_audio_driver()

CARLA_DEFAULT_PROCESS_MODE = ENGINE_PROCESS_MODE_PATCHBAY

if CARLA_DEFAULT_AUDIO_DRIVER == "JACK":
    CARLA_DEFAULT_TRANSPORT_MODE = ENGINE_TRANSPORT_MODE_JACK
else:
    CARLA_DEFAULT_TRANSPORT_MODE = ENGINE_TRANSPORT_MODE_INTERNAL

# OSC
CARLA_DEFAULT_OSC_ENABLED = not (CARLA_OS_MAC or CARLA_OS_WIN)
CARLA_DEFAULT_OSC_TCP_PORT_ENABLED = True
CARLA_DEFAULT_OSC_TCP_PORT_NUMBER  = 22752
CARLA_DEFAULT_OSC_TCP_PORT_RANDOM  = False
CARLA_DEFAULT_OSC_UDP_PORT_ENABLED = True
CARLA_DEFAULT_OSC_UDP_PORT_NUMBER  = 22752
CARLA_DEFAULT_OSC_UDP_PORT_RANDOM  = False

# Wine
CARLA_DEFAULT_WINE_EXECUTABLE      = "wine"
CARLA_DEFAULT_WINE_AUTO_PREFIX     = True
CARLA_DEFAULT_WINE_FALLBACK_PREFIX = os.path.expanduser("~/.wine")
CARLA_DEFAULT_WINE_RT_PRIO_ENABLED = True
CARLA_DEFAULT_WINE_BASE_RT_PRIO    = 15
CARLA_DEFAULT_WINE_SERVER_RT_PRIO  = 10

# Experimental
CARLA_DEFAULT_EXPERIMENTAL_PLUGIN_BRIDGES        = False
CARLA_DEFAULT_EXPERIMENTAL_WINE_BRIDGES          = False
CARLA_DEFAULT_EXPERIMENTAL_JACK_APPS             = False
CARLA_DEFAULT_EXPERIMENTAL_LV2_EXPORT            = False
CARLA_DEFAULT_EXPERIMENTAL_PREVENT_BAD_BEHAVIOUR = False
CARLA_DEFAULT_EXPERIMENTAL_LOAD_LIB_GLOBAL       = False

# ------------------------------------------------------------------------------------------------------------
# Default File Folders

CARLA_DEFAULT_FILE_PATH_AUDIO = []
CARLA_DEFAULT_FILE_PATH_MIDI  = []

# ------------------------------------------------------------------------------------------------------------
# Default Plugin Folders (get)

DEFAULT_LADSPA_PATH = ""
DEFAULT_DSSI_PATH   = ""
DEFAULT_LV2_PATH    = ""
DEFAULT_VST2_PATH   = ""
DEFAULT_VST3_PATH   = ""
DEFAULT_CLAP_PATH   = ""
DEFAULT_SF2_PATH    = ""
DEFAULT_SFZ_PATH    = ""
DEFAULT_JSFX_PATH   = ""

if CARLA_OS_WIN:
    splitter = ";"

    APPDATA = os.getenv("APPDATA")
    LOCALAPPDATA = os.getenv("LOCALAPPDATA", APPDATA)
    PROGRAMFILES = os.getenv("PROGRAMFILES")
    PROGRAMFILESx86 = os.getenv("PROGRAMFILES(x86)")
    COMMONPROGRAMFILES = os.getenv("COMMONPROGRAMFILES")
    COMMONPROGRAMFILESx86 = os.getenv("COMMONPROGRAMFILES(x86)")

    # Small integrity tests
    if not APPDATA:
        qFatal("APPDATA variable not set, cannot continue")
        sys.exit(1)

    if not PROGRAMFILES:
        qFatal("PROGRAMFILES variable not set, cannot continue")
        sys.exit(1)

    if not COMMONPROGRAMFILES:
        qFatal("COMMONPROGRAMFILES variable not set, cannot continue")
        sys.exit(1)

    DEFAULT_LADSPA_PATH  = APPDATA + "\\LADSPA"
    DEFAULT_LADSPA_PATH += ";" + PROGRAMFILES + "\\LADSPA"

    DEFAULT_DSSI_PATH    = APPDATA + "\\DSSI"
    DEFAULT_DSSI_PATH   += ";" + PROGRAMFILES + "\\DSSI"

    DEFAULT_LV2_PATH     = APPDATA + "\\LV2"
    DEFAULT_LV2_PATH    += ";" + COMMONPROGRAMFILES + "\\LV2"

    DEFAULT_VST2_PATH    = PROGRAMFILES + "\\VstPlugins"
    DEFAULT_VST2_PATH   += ";" + PROGRAMFILES + "\\Steinberg\\VstPlugins"

    DEFAULT_JSFX_PATH    = APPDATA + "\\REAPER\\Effects"
    #DEFAULT_JSFX_PATH   += ";" + PROGRAMFILES + "\\REAPER\\InstallData\\Effects"

    if CARLA_OS_64BIT:
        DEFAULT_VST2_PATH  += ";" + COMMONPROGRAMFILES + "\\VST2"

    DEFAULT_VST3_PATH    = COMMONPROGRAMFILES + "\\VST3"
    DEFAULT_VST3_PATH   += ";" + LOCALAPPDATA + "\\Programs\\Common\\VST3"

    DEFAULT_CLAP_PATH    = COMMONPROGRAMFILES + "\\CLAP"
    DEFAULT_CLAP_PATH   += ";" + LOCALAPPDATA + "\\Programs\\Common\\CLAP"

    DEFAULT_SF2_PATH     = APPDATA + "\\SF2"
    DEFAULT_SFZ_PATH     = APPDATA + "\\SFZ"

    if PROGRAMFILESx86:
        DEFAULT_LADSPA_PATH += ";" + PROGRAMFILESx86 + "\\LADSPA"
        DEFAULT_DSSI_PATH   += ";" + PROGRAMFILESx86 + "\\DSSI"
        DEFAULT_VST2_PATH   += ";" + PROGRAMFILESx86 + "\\VstPlugins"
        DEFAULT_VST2_PATH   += ";" + PROGRAMFILESx86 + "\\Steinberg\\VstPlugins"
        #DEFAULT_JSFX_PATH   += ";" + PROGRAMFILESx86 + "\\REAPER\\InstallData\\Effects"

    if COMMONPROGRAMFILESx86:
        DEFAULT_VST3_PATH   += COMMONPROGRAMFILESx86 + "\\VST3"
        DEFAULT_CLAP_PATH   += COMMONPROGRAMFILESx86 + "\\CLAP"

elif CARLA_OS_HAIKU:
    splitter = ":"

    DEFAULT_LADSPA_PATH  = HOME + "/.ladspa"
    DEFAULT_LADSPA_PATH += ":/system/add-ons/media/ladspaplugins"
    DEFAULT_LADSPA_PATH += ":/system/lib/ladspa"

    DEFAULT_DSSI_PATH    = HOME + "/.dssi"
    DEFAULT_DSSI_PATH   += ":/system/add-ons/media/dssiplugins"
    DEFAULT_DSSI_PATH   += ":/system/lib/dssi"

    DEFAULT_LV2_PATH     = HOME + "/.lv2"
    DEFAULT_LV2_PATH    += ":/system/add-ons/media/lv2plugins"

    DEFAULT_VST2_PATH    = HOME + "/.vst"
    DEFAULT_VST2_PATH   += ":/system/add-ons/media/vstplugins"

    DEFAULT_VST3_PATH    = HOME + "/.vst3"
    DEFAULT_VST3_PATH   += ":/system/add-ons/media/vst3plugins"

    DEFAULT_CLAP_PATH    = HOME + "/.clap"
    DEFAULT_CLAP_PATH   += ":/system/add-ons/media/clapplugins"

elif CARLA_OS_MAC:
    splitter = ":"

    DEFAULT_LADSPA_PATH  = HOME + "/Library/Audio/Plug-Ins/LADSPA"
    DEFAULT_LADSPA_PATH += ":/Library/Audio/Plug-Ins/LADSPA"

    DEFAULT_DSSI_PATH    = HOME + "/Library/Audio/Plug-Ins/DSSI"
    DEFAULT_DSSI_PATH   += ":/Library/Audio/Plug-Ins/DSSI"

    DEFAULT_LV2_PATH     = HOME + "/Library/Audio/Plug-Ins/LV2"
    DEFAULT_LV2_PATH    += ":/Library/Audio/Plug-Ins/LV2"

    DEFAULT_VST2_PATH    = HOME + "/Library/Audio/Plug-Ins/VST"
    DEFAULT_VST2_PATH   += ":/Library/Audio/Plug-Ins/VST"

    DEFAULT_VST3_PATH    = HOME + "/Library/Audio/Plug-Ins/VST3"
    DEFAULT_VST3_PATH   += ":/Library/Audio/Plug-Ins/VST3"

    DEFAULT_CLAP_PATH    = HOME + "/Library/Audio/Plug-Ins/CLAP"
    DEFAULT_CLAP_PATH   += ":/Library/Audio/Plug-Ins/CLAP"

    DEFAULT_JSFX_PATH    = HOME + "/Library/Application Support/REAPER/Effects"
    #DEFAULT_JSFX_PATH   += ":/Applications/REAPER.app/Contents/InstallFiles/Effects"

else:
    splitter = ":"

    CONFIG_HOME = os.getenv("XDG_CONFIG_HOME", HOME + "/.config")

    DEFAULT_LADSPA_PATH  = HOME + "/.ladspa"
    DEFAULT_LADSPA_PATH += ":/usr/lib/ladspa"
    DEFAULT_LADSPA_PATH += ":/usr/local/lib/ladspa"

    DEFAULT_DSSI_PATH    = HOME + "/.dssi"
    DEFAULT_DSSI_PATH   += ":/usr/lib/dssi"
    DEFAULT_DSSI_PATH   += ":/usr/local/lib/dssi"

    DEFAULT_LV2_PATH     = HOME + "/.lv2"
    DEFAULT_LV2_PATH    += ":/usr/lib/lv2"
    DEFAULT_LV2_PATH    += ":/usr/local/lib/lv2"

    DEFAULT_VST2_PATH    = HOME + "/.vst"
    DEFAULT_VST2_PATH   += ":/usr/lib/vst"
    DEFAULT_VST2_PATH   += ":/usr/local/lib/vst"

    DEFAULT_VST2_PATH   += HOME + "/.lxvst"
    DEFAULT_VST2_PATH   += ":/usr/lib/lxvst"
    DEFAULT_VST2_PATH   += ":/usr/local/lib/lxvst"

    DEFAULT_VST3_PATH    = HOME + "/.vst3"
    DEFAULT_VST3_PATH   += ":/usr/lib/vst3"
    DEFAULT_VST3_PATH   += ":/usr/local/lib/vst3"

    DEFAULT_CLAP_PATH    = HOME + "/.clap"
    DEFAULT_CLAP_PATH   += ":/usr/lib/clap"
    DEFAULT_CLAP_PATH   += ":/usr/local/lib/clap"

    DEFAULT_SF2_PATH     = HOME + "/.sounds/sf2"
    DEFAULT_SF2_PATH    += ":" + HOME + "/.sounds/sf3"
    DEFAULT_SF2_PATH    += ":/usr/share/sounds/sf2"
    DEFAULT_SF2_PATH    += ":/usr/share/sounds/sf3"
    DEFAULT_SF2_PATH    += ":/usr/share/soundfonts"

    DEFAULT_SFZ_PATH     = HOME + "/.sounds/sfz"
    DEFAULT_SFZ_PATH    += ":/usr/share/sounds/sfz"

    DEFAULT_JSFX_PATH    = CONFIG_HOME + "/REAPER/Effects"
    #DEFAULT_JSFX_PATH   += ":" + "/opt/REAPER/InstallData/Effects"

if not CARLA_OS_WIN:
    winePrefix = os.getenv("WINEPREFIX")

    if not winePrefix:
        winePrefix = HOME + "/.wine"

    DEFAULT_VST2_PATH += ":" + winePrefix + "/drive_c/Program Files/VstPlugins"
    DEFAULT_VST2_PATH += ":" + winePrefix + "/drive_c/Program Files/VSTPlugins"
    DEFAULT_VST2_PATH += ":" + winePrefix + "/drive_c/Program Files/Steinberg/VstPlugins"
    DEFAULT_VST2_PATH += ":" + winePrefix + "/drive_c/Program Files/Steinberg/VSTPlugins"
    DEFAULT_VST2_PATH += ":" + winePrefix + "/drive_c/Program Files/Common Files/VST2"
    DEFAULT_VST3_PATH += ":" + winePrefix + "/drive_c/Program Files/Common Files/VST3"
    DEFAULT_CLAP_PATH += ":" + winePrefix + "/drive_c/Program Files/Common Files/CLAP"

    if CARLA_OS_64BIT:
        DEFAULT_VST2_PATH += ":" + winePrefix + "/drive_c/Program Files (x86)/VstPlugins"
        DEFAULT_VST2_PATH += ":" + winePrefix + "/drive_c/Program Files (x86)/VSTPlugins"
        DEFAULT_VST2_PATH += ":" + winePrefix + "/drive_c/Program Files (x86)/Steinberg/VstPlugins"
        DEFAULT_VST2_PATH += ":" + winePrefix + "/drive_c/Program Files (x86)/Steinberg/VSTPlugins"
        DEFAULT_VST3_PATH += ":" + winePrefix + "/drive_c/Program Files (x86)/Common Files/VST3"
        DEFAULT_CLAP_PATH += ":" + winePrefix + "/drive_c/Program Files (x86)/Common Files/CLAP"

    del winePrefix

# ------------------------------------------------------------------------------------------------------------
# Default Plugin Folders (set)

readEnvVars = True

if CARLA_OS_WIN:
    # Check if running Wine. If yes, ignore env vars
    # pylint: disable=import-error
    from winreg import ConnectRegistry, OpenKey, CloseKey, HKEY_CURRENT_USER
    # pylint: enable=import-error
    _reg = ConnectRegistry(None, HKEY_CURRENT_USER)

    try:
        _key = OpenKey(_reg, r"SOFTWARE\Wine")
        CloseKey(_key)
        del _key
        readEnvVars = False
    except Exception:
        pass

    CloseKey(_reg)
    del _reg

if readEnvVars:
    CARLA_DEFAULT_LADSPA_PATH = os.getenv("LADSPA_PATH", DEFAULT_LADSPA_PATH).split(splitter)
    CARLA_DEFAULT_DSSI_PATH   = os.getenv("DSSI_PATH",   DEFAULT_DSSI_PATH).split(splitter)
    CARLA_DEFAULT_LV2_PATH    = os.getenv("LV2_PATH",    DEFAULT_LV2_PATH).split(splitter)
    CARLA_DEFAULT_VST2_PATH   = os.getenv("VST_PATH",    DEFAULT_VST2_PATH).split(splitter)
    CARLA_DEFAULT_VST3_PATH   = os.getenv("VST3_PATH",   DEFAULT_VST3_PATH).split(splitter)
    CARLA_DEFAULT_CLAP_PATH   = os.getenv("CLAP_PATH",   DEFAULT_CLAP_PATH).split(splitter)
    CARLA_DEFAULT_SF2_PATH    = os.getenv("SF2_PATH",    DEFAULT_SF2_PATH).split(splitter)
    CARLA_DEFAULT_SFZ_PATH    = os.getenv("SFZ_PATH",    DEFAULT_SFZ_PATH).split(splitter)
    CARLA_DEFAULT_JSFX_PATH   = os.getenv("JSFX_PATH",   DEFAULT_JSFX_PATH).split(splitter)

else:
    CARLA_DEFAULT_LADSPA_PATH = DEFAULT_LADSPA_PATH.split(splitter)
    CARLA_DEFAULT_DSSI_PATH   = DEFAULT_DSSI_PATH.split(splitter)
    CARLA_DEFAULT_LV2_PATH    = DEFAULT_LV2_PATH.split(splitter)
    CARLA_DEFAULT_VST2_PATH   = DEFAULT_VST2_PATH.split(splitter)
    CARLA_DEFAULT_VST3_PATH   = DEFAULT_VST3_PATH.split(splitter)
    CARLA_DEFAULT_CLAP_PATH   = DEFAULT_CLAP_PATH.split(splitter)
    CARLA_DEFAULT_SF2_PATH    = DEFAULT_SF2_PATH.split(splitter)
    CARLA_DEFAULT_SFZ_PATH    = DEFAULT_SFZ_PATH.split(splitter)
    CARLA_DEFAULT_JSFX_PATH   = DEFAULT_JSFX_PATH.split(splitter)

# ------------------------------------------------------------------------------------------------------------
# Default Plugin Folders (cleanup)

del DEFAULT_LADSPA_PATH
del DEFAULT_DSSI_PATH
del DEFAULT_LV2_PATH
del DEFAULT_VST2_PATH
del DEFAULT_VST3_PATH
del DEFAULT_CLAP_PATH
del DEFAULT_SF2_PATH
del DEFAULT_SFZ_PATH

# ------------------------------------------------------------------------------------------------------------
# Global Carla object

class CarlaObject():
    def __init__(self):
        self.cnprefix    = ""       # Client name prefix
        self.gui         = None     # Host Window
        self.nogui       = False    # Skip UI
        self.term        = False    # Terminated by OS signal
        self.felib       = None     # Frontend lib object
        self.utils       = None     # Utils object
        self.debug_level = "info"   # "info", "warn", "critical"
        self.log_file    = None     # Log file path
        self.autoload_lastsave = False # Autoload last saved project on startup without prompting
        self.hidden = False # Start minimized/hidden to system tray
        self.app_name = None

gCarla = CarlaObject()

DEBUG_LEVEL_MAP = {
    "debug": -1,
    "info": 0,
    "warn": 1,
    "warning": 1,
    "critical": 2,
    "error": 2,
}

def log_carla(msg, level="info"):
    msg_str = str(msg)
    if "CRITICAL" in msg_str or "Traceback" in msg_str:
        level = "critical"

    current_threshold = DEBUG_LEVEL_MAP.get(str(gCarla.debug_level).lower(), 0)
    msg_level = DEBUG_LEVEL_MAP.get(str(level).lower(), 0)
    if msg_level < current_threshold:
        return

    log_path = gCarla.log_file if gCarla.log_file else "/tmp/carla.log"
    try:
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(msg_str + "\n")
    except Exception:
        pass

    try:
        from carla_logger import (
            logger,
            LOG_LEVEL_DEBUG,
            LOG_LEVEL_INFO,
            LOG_LEVEL_WARNING,
            LOG_LEVEL_ERROR,
            LOG_LEVEL_CRITICAL,
        )
        lvl_map = {
            "debug": LOG_LEVEL_DEBUG,
            "info": LOG_LEVEL_INFO,
            "warn": LOG_LEVEL_WARNING,
            "warning": LOG_LEVEL_WARNING,
            "error": LOG_LEVEL_ERROR,
            "critical": LOG_LEVEL_CRITICAL,
        }
        exp_lvl = lvl_map.get(str(level).lower(), None)
        logger.log_raw_string(msg_str, explicit_level=exp_lvl)
    except Exception:
        print(msg_str, file=sys.stderr, flush=True)

# ------------------------------------------------------------------------------------------------------------
# Nerd Font Detection (Cached)

_CACHED_NERD_FONT_FAMILY = None

def getBestNerdFont():
    global _CACHED_NERD_FONT_FAMILY
    if _CACHED_NERD_FONT_FAMILY is not None:
        return _CACHED_NERD_FONT_FAMILY

    try:
        from qt_compat import QFontDatabase
        try:
            families = QFontDatabase.families()
        except (TypeError, AttributeError):
            families = QFontDatabase().families()
    except Exception:
        families = []

    nerd_candidates = [
        "JetBrainsMono Nerd Font",
        "JetBrainsMonoNF",
        "CommitMono Nerd Font Mono",
        "Liga SFMono Nerd Font",
        "FiraCode Nerd Font",
        "Hack Nerd Font",
        "MesloLGS NF",
    ]
    family_set = set(families)
    for cand in nerd_candidates:
        if cand in family_set:
            _CACHED_NERD_FONT_FAMILY = cand
            return cand

    for fam in families:
        if "nerd" in fam.lower():
            _CACHED_NERD_FONT_FAMILY = fam
            return fam

    _CACHED_NERD_FONT_FAMILY = ""
    return _CACHED_NERD_FONT_FAMILY


# ------------------------------------------------------------------------------------------------------------
# Set CWD

CWD = sys.path[0]

if not CWD:
    CWD = os.path.dirname(sys.argv[0])

# make it work with cxfreeze
if os.path.isfile(CWD):
    CWD = os.path.dirname(CWD)
    if CWD.endswith("/lib"):
        CWD = CWD.rsplit("/lib",1)[0]
    CXFREEZE = True
    if not CARLA_OS_WIN:
        os.environ['CARLA_MAGIC_FILE'] = os.path.join(CWD, "magic.mgc")
else:
    CXFREEZE = False

# ------------------------------------------------------------------------------------------------------------
# Set DLL_EXTENSION

if CARLA_OS_WIN:
    DLL_EXTENSION = "dll"
elif CARLA_OS_MAC:
    DLL_EXTENSION = "dylib"
else:
    DLL_EXTENSION = "so"

# ------------------------------------------------------------------------------------------------------------
# Find decimal points for a parameter, using step and stepSmall

def countDecimalPoints(step, stepSmall):
    if stepSmall >= 1.0:
        return 0
    if step >= 1.0:
        return 2

    count = 0
    value = fmod(abs(step), 1)
    while 0.0001 < value < 0.999 and count < 6:
        value = fmod(value*10, 1)
        count += 1

    return count

# ------------------------------------------------------------------------------------------------------------
# Check if a value is a number (float support)

def isNumber(value):
    try:
        float(value)
        return True
    except Exception:
        return False

# ------------------------------------------------------------------------------------------------------------
# Convert a value to a list

def toList(value):
    if value is None:
        return []
    if not isinstance(value, list):
        return [value]
    return value

# ------------------------------------------------------------------------------------------------------------
# Get Icon from user theme, using our own as backup (Oxygen)

def getIcon(icon, size, qrcformat):
    # Lucide icons (when vendored locally) take precedence over theme icons so
    # the whole app draws one consistent icon set.
    try:
        from widgets.lucide import theme_icon
        lucide = theme_icon(icon, size)
        if lucide is not None:
            return lucide
    except Exception:
        pass
    return QIcon.fromTheme(icon, QIcon(":/%ix%i/%s.%s" % (size, size, icon, qrcformat)))

# ------------------------------------------------------------------------------------------------------------
# Handle some basic command-line arguments shared between all carla variants

def handleInitialCommandLineArguments(file):
    import argparse
    initName  = os.path.basename(file) if (file is not None and os.path.dirname(file) in PATH) else sys.argv[0]
    libPrefix = None

    parser = argparse.ArgumentParser(
        prog=initName,
        description="Carla audio plugin host",
        add_help=False,
    )

    # Logging and diagnostics
    parser.add_argument("--debug", nargs="?", const="info", default=None,
                        help="Set debug level: debug, info, warn, critical.")
    parser.add_argument("--log", nargs="?", const="carla.log", default=None,
                        help="Log output to file (defaults to carla.log).")
    parser.add_argument("--log-level", default=None,
                        help="Set logger filter level: debug, info, warning, error, critical.")
    parser.add_argument("--log-whitelist", default=None,
                        help="Comma-separated list of tags to display (e.g. PATCHBAY,PLUGIN).")
    parser.add_argument("--log-blacklist", default=None,
                        help="Comma-separated list of tags to hide.")
    parser.add_argument("--console-log", action="store_true", default=None,
                        help="Explicitly enable terminal console output.")
    parser.add_argument("--no-console-log", action="store_true", default=None,
                        help="Disable terminal console output.")

    # General configuration
    parser.add_argument("--cnprefix", default=None,
                        help="Set a prefix for client names in multi-client mode.")
    parser.add_argument("--with-appname", default=None,
                        help=argparse.SUPPRESS)
    parser.add_argument("--with-libprefix", default=None,
                        help=argparse.SUPPRESS)
    parser.add_argument("--osc-gui", default=None,
                        help=argparse.SUPPRESS)
    parser.add_argument("--autoload-lastsave", "--autoload-last-save", "--load-autosave",
                        action="store_true", default=False,
                        help="Autoload most recent saved project without prompting.")
    parser.add_argument("--hidden", "--start-hidden",
                        action="store_true", default=False,
                        help="Start minimized/hidden to system tray.")
    parser.add_argument("-n", "--no-gui", "--nogui",
                        action="store_true", default=False,
                        help="Run Carla headless, don't show UI.")
    parser.add_argument("--gdb", action="store_true", default=False,
                        help="Run Carla inside gdb.")
    parser.add_argument("-h", "--help", action="store_true", default=False,
                        help="Print this help text and exit.")
    parser.add_argument("-v", "--version", action="store_true", default=False,
                        help="Print version information and exit.")

    parsed, unknown = parser.parse_known_args()

    # Help handler
    if parsed.help:
        pathBinaries, pathResources = getPaths(libPrefix)
        bold = "\033[1m"
        cyan = "\033[36m"
        green = "\033[32m"
        yellow = "\033[33m"
        magenta = "\033[35m"
        gray = "\033[90m"
        reset = "\033[0m"

        print(f"{bold}{cyan}Carla Plugin Host{reset} {green}v{CARLA_VERSION_STRING}{reset}")
        print(f"{gray}Python {sys.version.split(' ', 1)[0]} | Qt {QT_VERSION_STR} | PyQt {PYQT_VERSION_STR}{reset}")
        print(f"{gray}Binaries:  {pathBinaries}{reset}")
        print(f"{gray}Resources: {pathResources}{reset}")
        print("")
        print(f"{bold}USAGE:{reset}")
        print(f"  {green}{initName}{reset} [{yellow}OPTIONS{reset}]... [{magenta}FILE{reset}|{magenta}URL{reset}]")
        print("")
        print(f"{bold}ARGUMENTS:{reset}")
        print(f"  {magenta}FILE{reset}                  Carla project (.carxp, .bws) or plugin state file")
        print(f"  {magenta}URL{reset}                   Remote Carla-Control OSC address (e.g. osc.udp://...)")
        print("")
        print(f"{bold}OPTIONS:{reset}")
        print(f"  {yellow}--debug{reset} [{cyan}LEVEL{reset}]         Debug verbosity level: {cyan}debug{reset}, {cyan}info{reset}, {cyan}warn{reset}, {cyan}critical{reset} (default: info)")
        print(f"  {yellow}--log{reset} [{cyan}PATH{reset}]           Log raw messages to disk file (default: carla.log)")
        print(f"  {yellow}--log-level{reset} {cyan}LEVEL{reset}      Log filter threshold: {cyan}debug{reset}, {cyan}info{reset}, {cyan}warning{reset}, {cyan}error{reset}, {cyan}critical{reset}")
        print(f"  {yellow}--log-whitelist{reset} {cyan}TAGS{reset}   Comma-separated tags to display.")
        print(f"                        Available tags: {green}APP{reset}, {green}ENGINE{reset}, {green}PATCHBAY{reset}, {green}PLUGIN{reset}, {green}SESSION{reset}, {green}CANVAS{reset}, {green}BACKEND{reset}")
        print(f"  {yellow}--log-blacklist{reset} {cyan}TAGS{reset}   Comma-separated tags to suppress (same tag choices as above)")
        print(f"  {yellow}--console-log{reset}          Force-enable colored terminal console output")
        print(f"  {yellow}--no-console-log{reset}       Disable terminal console output entirely")
        print(f"  {yellow}--autoload-lastsave{reset}    Automatically restore the most recently saved session on launch")
        print(f"  {yellow}--hidden{reset}               Start application hidden/minimized to the system tray")
        print(f"  {yellow}--cnprefix{reset} {cyan}PREFIX{reset}      Set client name prefix when running in multi-client mode")
        if isinstance(gCarla.nogui, bool):
            if X_LIBDIR_X is not None:
                print(f"  {yellow}--gdb{reset}                 Run Carla inside GDB debugger")
            print(f"  {yellow}-n{reset}, {yellow}--no-gui{reset}           Run Carla headless without GUI")
        print(f"  {yellow}-h{reset}, {yellow}--help{reset}             Show this help message and exit")
        print(f"  {yellow}-v{reset}, {yellow}--version{reset}          Show version details and exit")
        print("")
        if not isinstance(gCarla.nogui, bool):
            print(f"{yellow}NOTE:{reset} When using {initName}, the FILE argument is only loaded on first engine launch.")
            sys.exit(1)
        sys.exit(0)

    # Version handler
    if parsed.version:
        pathBinaries, pathResources = getPaths(libPrefix)
        printStartupBanner([
            ("Python", sys.version.split(" ", 1)[0]),
            ("Qt", QT_VERSION_STR),
            ("PyQt", PYQT_VERSION_STR),
            ("Binaries", pathBinaries),
            ("Resources", pathResources),
        ])
        sys.exit(1 if gCarla.nogui else 0)

    # Assign parsed parameters
    if parsed.with_appname:
        initName = os.path.basename(parsed.with_appname)
        gCarla.app_name = initName
    else:
        gCarla.app_name = initName
    if parsed.with_libprefix:
        libPrefix = parsed.with_libprefix
    if parsed.osc_gui:
        try:
            gCarla.nogui = int(parsed.osc_gui)
        except ValueError:
            pass
    if parsed.cnprefix:
        gCarla.cnprefix = parsed.cnprefix
    if parsed.debug is not None:
        gCarla.debug_level = parsed.debug.lower()
    if parsed.log is not None:
        gCarla.log_file = parsed.log
    if parsed.autoload_lastsave:
        gCarla.autoload_lastsave = True
    if parsed.hidden:
        gCarla.hidden = True
    if parsed.no_gui:
        gCarla.nogui = True

    # Forward to CarlaLogger if available
    try:
        from carla_logger import logger, NAME_TO_LEVEL
        if parsed.log_level and parsed.log_level.upper() in NAME_TO_LEVEL:
            logger.min_level = NAME_TO_LEVEL[parsed.log_level.upper()]
        if parsed.log_whitelist:
            logger.whitelist.update([t.strip().upper() for t in parsed.log_whitelist.split(",") if t.strip()])
        if parsed.log_blacklist:
            logger.blacklist.update([t.strip().upper() for t in parsed.log_blacklist.split(",") if t.strip()])
        if parsed.no_console_log:
            logger.console_enabled = False
        elif parsed.console_log:
            logger.console_enabled = True
    except Exception:
        pass

    if gCarla.nogui and not isinstance(gCarla.nogui, bool):
        if os.fork():
            # pylint: disable=protected-access
            os._exit(0)
            # pylint: enable=protected-access
        else:
            os.setsid()

    return (initName, libPrefix)

# ------------------------------------------------------------------------------------------------------------
# Get initial project file (as passed in the command-line parameters)

def getInitialProjectFile(skipExistCheck = False):
    # NOTE: PyQt mishandles unicode characters, we directly use sys.argv instead of qApp->arguments()
    # see https://riverbankcomputing.com/pipermail/pyqt/2015-January/035395.html
    args = sys.argv[1:]
    skipNext = False
    # options that take a value in the next argv entry (must not be mistaken for the project file)
    value_options = ("--cnprefix", "--log-level", "--log-whitelist", "--log-blacklist", "--log", "--debug")
    for arg in args:
        if skipNext:
            skipNext = False
            continue
        if arg.startswith("--cnprefix="):
            continue
        if arg.startswith("--osc-gui="):
            continue
        if arg.startswith("--with-appname="):
            continue
        if arg.startswith("--with-libprefix="):
            continue
        if arg.startswith("--log-level=") or arg.startswith("--log="):
            continue
        if arg in value_options:
            skipNext = True
            continue
        if arg.startswith("-"):
            continue
        arg = os.path.expanduser(arg)
        if skipExistCheck or os.path.exists(arg):
            return arg

    return None

# ------------------------------------------------------------------------------------------------------------
# Get paths (binaries, resources)

def getPaths(libPrefix = None):
    CWDl = CWD.lower()

    # adjust for special distros
    libdir  = os.path.basename(os.path.normpath(X_LIBDIR_X))  if X_LIBDIR_X  else "lib"
    datadir = os.path.basename(os.path.normpath(X_DATADIR_X)) if X_DATADIR_X else "share"

    # standalone, installed system-wide linux
    if libPrefix is not None:
        pathBinaries  = os.path.join(libPrefix, libdir, "carla")
        pathResources = os.path.join(libPrefix, datadir, "carla", "resources")

    # standalone, local source
    elif CWDl.endswith("frontend"):
        pathBinaries  = os.path.abspath(os.path.join(CWD, "..", "..", "bin"))
        pathResources = os.path.join(pathBinaries, "resources")

    # plugin
    elif CWDl.endswith("resources"):
        # installed system-wide linux
        if CWDl.endswith("/share/carla/resources"):
            pathBinaries  = os.path.abspath(os.path.join(CWD, "..", "..", "..", libdir, "carla"))
            pathResources = CWD

        # local source
        elif CWDl.endswith("native-plugins%sresources" % os.sep):
            pathBinaries  = os.path.abspath(os.path.join(CWD, "..", "..", "..", "bin"))
            pathResources = CWD

        # other
        else:
            pathBinaries  = os.path.abspath(os.path.join(CWD, ".."))
            pathResources = CWD

    # everything else
    else:
        pathBinaries  = CWD
        pathResources = os.path.join(pathBinaries, "resources")

    return (pathBinaries, pathResources)

# ------------------------------------------------------------------------------------------------------------
# Signal handler
# TODO move to host_app.py or something

def signalHandler(sig, frame):
    if sig == SIGINT:
        # Ctrl+C from a terminal. When the GUI supports it, let it decide
        # between quitting and minimising to the tray, so we do not set the
        # global term flag here (the app may keep running).
        if gCarla.gui is not None and hasattr(gCarla.gui, "SIGINT"):
            gCarla.gui.SIGINT.emit()
            return
        gCarla.term = True
        if gCarla.gui is not None:
            gCarla.gui.SIGTERM.emit()

    elif sig == SIGTERM:
        gCarla.term = True
        if gCarla.gui is not None:
            gCarla.gui.SIGTERM.emit()

    elif haveSIGUSR1 and sig == SIGUSR1:
        if gCarla.gui is not None:
            gCarla.gui.SIGUSR1.emit()

def setUpSignals():
    signal(SIGINT,  signalHandler)
    signal(SIGTERM, signalHandler)

    if not haveSIGUSR1:
        return

    signal(SIGUSR1, signalHandler)

# ------------------------------------------------------------------------------------------------------------
# QLineEdit and QPushButton combo

def getAndSetPath(parent, lineEdit):
    newPath = QFileDialog.getExistingDirectory(parent, parent.tr("Set Path"), lineEdit.text(), QFileDialog.ShowDirsOnly)
    if newPath:
        lineEdit.setText(newPath)
    return newPath

# ------------------------------------------------------------------------------------------------------------
# Backwards-compatible horizontalAdvance/width call, depending on Qt version

def fontMetricsHorizontalAdvance(fontMetrics, string):
    if QT_VERSION >= 0x50b00:
        return fontMetrics.horizontalAdvance(string)
    return fontMetrics.width(string)

# ------------------------------------------------------------------------------------------------------------
# Custom QMessageBox which resizes itself to fit text

class QMessageBoxWithBetterWidth(QMessageBox):
    def __init__(self, parent):
        QMessageBox.__init__(self, parent)

    def showEvent(self, event):
        fontMetrics = self.fontMetrics()

        lines = self.text().strip().split("\n") + self.informativeText().strip().split("\n")

        if lines:
            width = 0

            for line in lines:
                width = max(fontMetricsHorizontalAdvance(fontMetrics, line), width)

            self.layout().setColumnMinimumWidth(2, width + 12)

        QMessageBox.showEvent(self, event)

# ------------------------------------------------------------------------------------------------------------
# Custom MessageBox

# pylint: disable=too-many-arguments
def CustomMessageBox(parent, icon, title, text,
                     extraText="",
                     buttons=QMessageBox.Yes|QMessageBox.No,
                     defButton=QMessageBox.No):
    msgBox = QMessageBoxWithBetterWidth(parent)
    msgBox.setIcon(icon)
    msgBox.setWindowTitle(title)
    msgBox.setText(text)
    msgBox.setInformativeText(extraText)
    msgBox.setStandardButtons(buttons)
    msgBox.setDefaultButton(defButton)
    # pylint: disable=no-value-for-parameter
    return msgBox.exec_()
    # pylint: enable=no-value-for-parameter
# pylint: enable=too-many-arguments

# ------------------------------------------------------------------------------------------------------------
# pylint: enable=possibly-used-before-assignment
