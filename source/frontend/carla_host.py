#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2011-2025 Filipe Coelho <falktx@falktx.com>
# SPDX-License-Identifier: GPL-2.0-or-later

# ------------------------------------------------------------------------------------------------------------
# Imports (Global)
# ------------------------------------------------------------------------------------------------------------

import json
import os
import sys
import xml.etree.ElementTree as ET
from datetime import datetime

# ------------------------------------------------------------------------------------------------------------
# Imports (ctypes)
# ------------------------------------------------------------------------------------------------------------
from ctypes import byref, pointer

# ------------------------------------------------------------------------------------------------------------
# Imports (Custom)
# ------------------------------------------------------------------------------------------------------------
import ui_carla_host
from update_checker import UpdateCheckThread, UpdateNotificationBanner, SupportNotificationBanner
from carla_app import *
from carla_backend import *
from carla_backend_qt import CarlaHostQtDLL, CarlaHostQtNull
from carla_frontend import CarlaFrontendLib
from carla_settings import *
from carla_shared import *
from carla_utils import *
from carla_widgets import *
from patchcanvas import patchcanvas
from carla_canvas import (
    CanvasViewportFilter,
    autoConnectStereoPair,
    canvasCallback,
    findStereoPartner,
    findStereoPartnerConnection,
    log_carla,
)
from project_storage import storage_manager
from project_session import ProjectSessionManager
from carla_logger import logger, KNOWN_TAGS, LEVEL_NAMES

# ------------------------------------------------------------------------------------------------------------
# Imports (PyQt)
# ------------------------------------------------------------------------------------------------------------
from qt_compat import (
    PYQT_VERSION,
    QT_VERSION,
    QAction,
    QApplication,
    QBrush,
    QBuffer,
    QCursor,
    QCheckBox,
    QEvent,
    QFileInfo,
    QFileSystemModel,
    QFrame,
    QGraphicsView,
    QImage,
    QImageWriter,
    QIODevice,
    QKeySequence,
    QLabel,
    QMainWindow,
    QMenu,
    QMimeData,
    QModelIndex,
    QMouseEvent,
    QPainter,
    QPalette,
    QPoint,
    QPointF,
    QRectF,
    QShortcut,
    QSizePolicy,
    QSplitter,
    QSurfaceFormat,
    QSystemTrayIcon,
    QTimer,
    QHBoxLayout,
    QToolButton,
    QVBoxLayout,
    QWidget,
    qCritical,
)
from widgets.digitalpeakmeter import DigitalPeakMeter
from widgets.pixmapkeyboard import PixmapKeyboardHArea

# ------------------------------------------------------------------------------------------------------------
# Try Import OpenGL

try:
    from qt_compat import QGLWidget

    hasGL = QGLWidget is not None
except ImportError:
    QGLWidget = None
    hasGL = False

# ------------------------------------------------------------------------------------------------------------
# Safe exception hook, needed for PyQt5


def sys_excepthook(typ, value, tback):
    import traceback

    err_str = "".join(traceback.format_exception(typ, value, tback))
    log_carla(f"CRITICAL TRACEBACK:\n{err_str}")
    return sys.__excepthook__(typ, value, tback)


# ------------------------------------------------------------------------------------------------------------
# Session Management support

CARLA_CLIENT_NAME = os.getenv("CARLA_CLIENT_NAME")
LADISH_APP_NAME = os.getenv("LADISH_APP_NAME")
NSM_URL = os.getenv("NSM_URL")

# ------------------------------------------------------------------------------------------------------------
# Small print helper


def processMode2Str(processMode):
    if processMode == ENGINE_PROCESS_MODE_SINGLE_CLIENT:
        return "Single client"
    if processMode == ENGINE_PROCESS_MODE_MULTIPLE_CLIENTS:
        return "Multi client"
    if processMode == ENGINE_PROCESS_MODE_CONTINUOUS_RACK:
        return "Continuous Rack"
    if processMode == ENGINE_PROCESS_MODE_PATCHBAY:
        return "Patchbay"
    if processMode == ENGINE_PROCESS_MODE_BRIDGE:
        return "Bridge"
    return "Unknown"


# ------------------------------------------------------------------------------------------------------------
# Carla Print class


class CarlaPrint:
    def __init__(self, err):
        self.err = err

    def flush(self):
        gCarla.utils.fflush(self.err)

    def write(self, string):
        gCarla.utils.fputs(self.err, string)


# ------------------------------------------------------------------------------------------------------------
# Host Window


class HostWindow(QMainWindow):
    # class HostWindow(QMainWindow, PluginEditParentMeta, metaclass=PyQtMetaClass):
    # signals
    SIGTERM = pyqtSignal()
    SIGUSR1 = pyqtSignal()
    SIGINT = pyqtSignal()

    # CustomActions
    CUSTOM_ACTION_NONE = 0
    CUSTOM_ACTION_APP_CLOSE = 1
    CUSTOM_ACTION_PROJECT_LOAD = 2

    # --------------------------------------------------------------------------------------------------------

    def __init__(self, host, withCanvas, parent=None):
        QMainWindow.__init__(self, parent)
        self.host = host
        self.ui = ui_carla_host.Ui_CarlaHostW()
        self.ui.setupUi(self)
        gCarla.gui = self

        # Clara update checker & top notification banner
        self.fUpdateBanner = None
        self.fUpdateThread = UpdateCheckThread(self)
        self.fUpdateThread.update_available.connect(self._on_update_available)
        self.fUpdateThread.finished.connect(self._onUpdateCheckThreadFinished)
        self.fUpdateThread.start()

        # Clara Support banner (triggers immediately with hidden arg --show-support-banner, otherwise after 10 mins: 600,000 ms)
        self.fSupportBanner = None
        if "--show-support-banner" in sys.argv:
            QTimer.singleShot(100, lambda: self._check_and_show_support_banner(force=True))
        else:
            QTimer.singleShot(600000, self._check_and_show_support_banner)

        # Remove rack padding left and right
        self.ui.pad_left.hide()
        self.ui.pad_right.hide()

        if False:
            # kdevelop likes this :)
            host = CarlaHostNull()
            self.host = host

        self._true = c_char_p(b"true")

        self.fParentOrSelf = parent or self

        # ----------------------------------------------------------------------------------------------------
        # Internal stuff

        self.fIdleTimerNull = self.startTimer(1000)  # keep application signals alive
        self.fIdleTimerFast = 0
        self.fIdleTimerSlow = 0

        self.fLadspaRdfNeedsUpdate = True
        self.fLadspaRdfList = []

        self.fPluginCount = 0
        self.fPluginList = []
        self.fConnections = {}

        # External patchbay clients whose audio is only tapped for the signal-flow
        # meters (or third-party peak-detect observers); hidden from the canvas.
        self.fFilteredPatchbayClients = set()

        self.fPluginListDialog = None
        self._settingsDialog = None
        self.fFavoritePlugins = []

        self.fProjectFilename = ""
        self.fRecentProjects = []
        self.fRecentProjectActions = []
        self.fIsProjectLoading = False
        self.fLoadingPluginTotal = 0
        self.fLoadingBridgePlugins = None
        self.fBridgePlugins = []
        self.fCurrentlyRemovingAllPlugins = False
        self.fHasLoadedLv2Plugins = False

        self.fLastTransportBPM = 0.0
        self.fLastTransportFrame = 0
        self.fLastTransportState = False
        self.fBufferSize = 0
        self.fSampleRate = 0.0
        self.fOscAddressTCP = ""
        self.fOscAddressUDP = ""

        if CARLA_OS_MAC:
            self.fMacClosingHelper = True

        # CancelableActionCallback Box
        self.fCancelableActionBox = None

        # run a custom action after engine is properly closed
        self.fCustomStopAction = self.CUSTOM_ACTION_NONE

        # first attempt of auto-start engine doesn't show an error
        self.fFirstEngineInit = True

        # to be filled with key-value pairs of current settings
        self.fSavedSettings = {}

        # system tray icon when minimized to tray
        self.fSystemTrayIcon = None

        # whether the application is quitting explicitly
        self.fForceQuit = False

        # true if NSM server handles our window management
        self.fWindowCloseHideGui = False

        if host.isControl:
            self.fClientName = "Carla-Control"
            self.fSessionManagerName = "Control"
        elif host.isPlugin:
            self.fClientName = "Carla-Plugin"
            self.fSessionManagerName = "Plugin"
        elif LADISH_APP_NAME:
            self.fClientName = LADISH_APP_NAME
            self.fSessionManagerName = ""
        elif NSM_URL and host.nsmOK:
            self.fClientName = "Carla.tmp"
            self.fSessionManagerName = "Non Session Manager TMP"
            self.fWindowCloseHideGui = True
        else:
            default_name = "Clara"
            if gCarla.app_name and "carla" in gCarla.app_name.lower() and "clara" not in gCarla.app_name.lower():
                default_name = "Carla"
            self.fClientName = CARLA_CLIENT_NAME or default_name
            self.fSessionManagerName = ""

        # ----------------------------------------------------------------------------------------------------
        # Internal stuff (patchbay)

        self.fPeaksCleared = True

        _saved_show_ext = QSafeSettings("falkTX", "Carla2").value(
            CARLA_KEY_CANVAS_SHOW_EXTERNAL,
            CARLA_DEFAULT_CANVAS_SHOW_EXTERNAL,
            bool,
        )
        self.fExternalPatchbay = bool(_saved_show_ext) if not host.isPlugin else False
        self.fSelectedPlugins = []

        self.fCanvasWidth = 0
        self.fCanvasHeight = 0
        self.fMiniCanvasUpdateTimeout = 150

        self.fWithCanvas = withCanvas

        # ----------------------------------------------------------------------------------------------------
        # Internal stuff (logs)

        self.autoscrollOnNewLog = True
        self.lastLogSliderPos = 0

        # ----------------------------------------------------------------------------------------------------
        # Set up GUI (engine stopped)

        if self.host.isPlugin or self.host.isControl:
            self.ui.act_file_save.setVisible(False)
            self.ui.act_engine_start.setEnabled(False)
            self.ui.act_engine_start.setVisible(False)
            self.ui.act_engine_stop.setEnabled(False)
            self.ui.act_engine_stop.setVisible(False)
            self.ui.menu_Engine.setEnabled(False)
            self.ui.menu_Engine.setVisible(False)
            self.ui.menu_Engine.menuAction().setVisible(False)
            self.ui.tabWidget.removeTab(2)

            if self.host.isControl:
                self.ui.act_file_new.setVisible(False)
                self.ui.act_file_open.setVisible(False)
                self.ui.act_file_save_as.setVisible(False)
                self.ui.tabUtils.removeTab(0)
            else:
                self.ui.act_file_save_as.setText(self.tr("Export as..."))

                if not withCanvas:
                    self.ui.tabWidget.tabBar().hide()

        else:
            self.ui.act_engine_start.setEnabled(True)

            if CARLA_OS_WIN:
                self.ui.tabWidget.removeTab(2)

        if self.host.isControl:
            self.ui.act_file_refresh.setEnabled(False)
        else:
            self.ui.act_file_connect.setEnabled(False)
            self.ui.act_file_connect.setVisible(False)
            self.ui.act_file_refresh.setEnabled(False)
            self.ui.act_file_refresh.setVisible(False)

        if self.fSessionManagerName and not self.host.isPlugin:
            self.ui.act_file_new.setEnabled(False)

        self.ui.act_file_open.setEnabled(True)
        self.ui.act_file_save.setEnabled(not self.host.isPlugin)
        self.ui.act_file_save_as.setEnabled(not self.host.isPlugin)
        self.ui.act_engine_stop.setEnabled(False)
        self.ui.act_plugin_remove_all.setEnabled(False)

        self.ui.act_canvas_show_internal.setChecked(False)
        self.ui.act_canvas_show_internal.setVisible(False)
        self.ui.act_canvas_show_external.setChecked(False)
        self.ui.act_canvas_show_external.setVisible(False)

        self.ui.menu_PluginMacros.setEnabled(False)
        self.ui.menu_Canvas.setEnabled(False)

        self.ui.dockWidgetTitleBar = QWidget(self)
        self.ui.dockWidget.setTitleBarWidget(self.ui.dockWidgetTitleBar)

        if not withCanvas:
            self.ui.act_canvas_show_internal.setVisible(False)
            self.ui.act_canvas_show_external.setVisible(False)
            self.ui.act_canvas_arrange.setVisible(False)
            self.ui.act_canvas_refresh.setVisible(False)
            self.ui.act_canvas_save_image.setVisible(False)
            self.ui.act_canvas_zoom_100.setVisible(False)
            self.ui.act_canvas_zoom_fit.setVisible(False)
            self.ui.act_canvas_zoom_in.setVisible(False)
            self.ui.act_canvas_zoom_out.setVisible(False)
            self.ui.act_settings_show_meters.setVisible(False)
            self.ui.act_settings_show_keyboard.setVisible(False)
            self.ui.menu_Canvas_Zoom.setEnabled(False)
            self.ui.menu_Canvas_Zoom.setVisible(False)
            self.ui.menu_Canvas_Zoom.menuAction().setVisible(False)
            self.ui.menu_Canvas.setEnabled(False)
            self.ui.menu_Canvas.setVisible(False)
            self.ui.menu_Canvas.menuAction().setVisible(False)
            self.ui.tw_miniCanvas.hide()
            self.ui.tabWidget.removeTab(1)
            if CARLA_OS_WIN:
                self.ui.tabWidget.tabBar().hide()

        # ----------------------------------------------------------------------------------------------------
        # Set up GUI (disk)

        exts = gCarla.utils.get_supported_file_extensions()

        self.fDirModel = QFileSystemModel(self)
        self.fDirModel.setRootPath(HOME)
        self.fDirModel.setNameFilters(tuple(("*." + i) for i in exts))

        self.ui.fileTreeView.setModel(self.fDirModel)
        self.ui.fileTreeView.setRootIndex(self.fDirModel.index(HOME))
        self.ui.fileTreeView.setColumnHidden(1, True)
        self.ui.fileTreeView.setColumnHidden(2, True)
        self.ui.fileTreeView.setColumnHidden(3, True)
        self.ui.fileTreeView.setHeaderHidden(True)

        # ----------------------------------------------------------------------------------------------------
        # Set up GUI (transport)

        fontMetrics = self.ui.l_transport_bbt.fontMetrics()
        minValueWidth = fontMetricsHorizontalAdvance(fontMetrics, "000|00|0000")
        minLabelWidth = fontMetricsHorizontalAdvance(
            fontMetrics, self.ui.label_transport_frame.text()
        )

        labelTimeWidth = fontMetricsHorizontalAdvance(
            fontMetrics, self.ui.label_transport_time.text()
        )
        labelBBTWidth = fontMetricsHorizontalAdvance(
            fontMetrics, self.ui.label_transport_bbt.text()
        )

        minLabelWidth = max(minLabelWidth, labelTimeWidth)
        minLabelWidth = max(minLabelWidth, labelBBTWidth)

        self.ui.label_transport_frame.setMinimumWidth(minLabelWidth + 3)
        self.ui.label_transport_time.setMinimumWidth(minLabelWidth + 3)
        self.ui.label_transport_bbt.setMinimumWidth(minLabelWidth + 3)

        self.ui.l_transport_bbt.setMinimumWidth(minValueWidth + 3)
        self.ui.l_transport_frame.setMinimumWidth(minValueWidth + 3)
        self.ui.l_transport_time.setMinimumWidth(minValueWidth + 3)

        if host.isPlugin:
            self.ui.b_transport_play.setEnabled(False)
            self.ui.b_transport_stop.setEnabled(False)
            self.ui.b_transport_backwards.setEnabled(False)
            self.ui.b_transport_forwards.setEnabled(False)
            self.ui.group_transport_controls.setEnabled(False)
            self.ui.group_transport_controls.setVisible(False)
            self.ui.cb_transport_link.setEnabled(False)
            self.ui.cb_transport_link.setVisible(False)
            self.ui.cb_transport_jack.setEnabled(False)
            self.ui.cb_transport_jack.setVisible(False)
            self.ui.dsb_transport_bpm.setEnabled(False)
            self.ui.dsb_transport_bpm.setReadOnly(True)

        self.ui.w_transport.setEnabled(False)

        # ----------------------------------------------------------------------------------------------------
        # Set up GUI (rack)

        self.ui.listWidget.setHostAndParent(self.host, self)
        self.ui.listWidget.setObjectName("rackListWidget")

        sb = self.ui.listWidget.verticalScrollBar()
        self.ui.rackScrollBar.setMinimum(sb.minimum())
        self.ui.rackScrollBar.setMaximum(sb.maximum())
        self.ui.rackScrollBar.setValue(sb.value())

        sb.rangeChanged.connect(self.ui.rackScrollBar.setRange)
        sb.valueChanged.connect(self.ui.rackScrollBar.setValue)
        self.ui.rackScrollBar.rangeChanged.connect(sb.setRange)
        self.ui.rackScrollBar.valueChanged.connect(sb.setValue)

        self.updateStyle()

        if QSafeSettings("falkTX", "Carla2").value(
            CARLA_KEY_MAIN_USE_PRO_THEME, CARLA_DEFAULT_MAIN_USE_PRO_THEME, bool
        ):
            pass

        # ----------------------------------------------------------------------------------------------------
        # Set up GUI (patchbay)

        self.ui.peak_in.setChannelCount(2)
        self.ui.peak_in.setMeterColor(DigitalPeakMeter.COLOR_BLUE)
        self.ui.peak_in.setMeterOrientation(DigitalPeakMeter.VERTICAL)
        self.ui.peak_in.setFixedWidth(25)

        self.ui.peak_out.setChannelCount(2)
        self.ui.peak_out.setMeterColor(DigitalPeakMeter.COLOR_GREEN)
        self.ui.peak_out.setMeterOrientation(DigitalPeakMeter.VERTICAL)
        self.ui.peak_out.setFixedWidth(25)

        self.ui.scrollArea = PixmapKeyboardHArea(self.ui.patchbay)
        self.ui.keyboard = self.ui.scrollArea.keyboard
        self.ui.patchbay.layout().addWidget(self.ui.scrollArea, 1, 0, 1, 0)

        self.ui.scrollArea.setEnabled(False)

        self.ui.miniCanvasPreview.setRealParent(self)
        self.ui.tw_miniCanvas.tabBar().hide()

        self._miniCanvasTimer = QTimer(self)
        self._miniCanvasTimer.setSingleShot(True)
        self._miniCanvasTimer.timeout.connect(self._doUpdateMiniCanvas)

        # ----------------------------------------------------------------------------------------------------
        # Set up GUI (logs)
        logger.parse_cli_args()
        logger.console_enabled = self.fSavedSettings.get(
            CARLA_KEY_MAIN_LOG_TO_CONSOLE, CARLA_DEFAULT_MAIN_LOG_TO_CONSOLE
        )

        try:
            with open("/tmp/carla.log", "w") as f:
                f.write("=== Carla Log Started ===\n")
        except Exception:
            pass

        self._orig_log_append = self.ui.text_logs.appendPlainText

        # Tag checklist layout in log_options
        self.ui.group_log_tags = QFrame(self.ui.log_options)
        self.ui.group_log_tags.setObjectName("group_log_tags")
        self.ui.group_log_tags_layout = QVBoxLayout(self.ui.group_log_tags)
        self.ui.group_log_tags_layout.setContentsMargins(0, 8, 0, 0)
        self.ui.group_log_tags_layout.setSpacing(4)

        lbl_tags = QLabel(self.tr("Filter Tags:"), self.ui.group_log_tags)
        lbl_tags.setStyleSheet("font-weight: bold;")
        self.ui.group_log_tags_layout.addWidget(lbl_tags)

        self.log_tag_checkboxes = {}
        for tag_name in KNOWN_TAGS:
            chk = QCheckBox(tag_name, self.ui.group_log_tags)
            chk.setChecked(True)
            chk.stateChanged.connect(self.slot_logFilterChanged)
            self.ui.group_log_tags_layout.addWidget(chk)
            self.log_tag_checkboxes[tag_name] = chk

        self.ui.verticalLayout_8.addWidget(self.ui.group_log_tags)

        # Connect logger signal
        logger.logAdded.connect(self.slot_onLogAdded)

        # Batch incoming log lines and flush them on a timer. Appending one
        # line at a time re-lays-out the entire document per call, which melts
        # the UI when the backend floods the log (JACK/pipewire churn).
        self._logPendingLines = []
        self._logFlushTimer = QTimer(self)
        self._logFlushTimer.setInterval(100)
        self._logFlushTimer.timeout.connect(self._flushLogPending)
        self._logFlushTimer.start()

        def _log_append(text):
            logger.log_raw_string(text)

        self.ui.text_logs.appendPlainText = _log_append

        # Bound the widget so a log flood cannot grow the document forever.
        try:
            self.ui.text_logs.setMaximumBlockCount(5000)
        except Exception:
            pass

        self.ui.text_logs.textChanged.connect(self.slot_logButtonsState)
        self.ui.logs_clear.clicked.connect(self.slot_logClear)
        self.ui.logs_save.clicked.connect(self.slot_logSave)
        self.ui.logs_autoscroll.stateChanged.connect(self.slot_toggleLogAutoscroll)
        self.ui.text_logs.verticalScrollBar().valueChanged.connect(
            self.slot_logSliderMoved
        )

        # ----------------------------------------------------------------------------------------------------
        # Set up GUI (special stuff for Mac OS)

        if CARLA_OS_MAC:
            self.ui.act_file_quit.setMenuRole(QAction.QuitRole)
            self.ui.act_settings_configure.setMenuRole(QAction.PreferencesRole)
            self.ui.act_help_about.setMenuRole(QAction.AboutRole)
            self.ui.act_help_about_qt.setMenuRole(QAction.AboutQtRole)
            self.ui.menu_Settings.setTitle("Panels")

        # ----------------------------------------------------------------------------------------------------
        # Menubar toggle action & compact hamburger tool button
        self.act_settings_show_menubar = QAction(self.tr("Show Menubar"), self)
        self.act_settings_show_menubar.setCheckable(True)
        self.act_settings_show_menubar.setChecked(True)
        self.act_settings_show_menubar.setShortcut("Ctrl+M")
        shortcut_context = getattr(Qt.ShortcutContext, "WindowShortcut", getattr(Qt, "WindowShortcut", None))
        if shortcut_context is not None:
            self.act_settings_show_menubar.setShortcutContext(shortcut_context)
        self.act_settings_show_menubar.toggled.connect(self.slot_showMenubar)

        # Modern vs Classic UI mode toggle
        self.act_settings_modern_ui = QAction(self.tr("Modern UI Mode"), self)
        self.act_settings_modern_ui.setCheckable(True)
        self.act_settings_modern_ui.setChecked(True)
        self.act_settings_modern_ui.toggled.connect(self.slot_toggleModernUi)

        # Statusbar toggle action (Buffer, DSP, Sample Rate panel)
        self.act_settings_show_statusbar = QAction(self.tr("Show Statusbar"), self)
        self.act_settings_show_statusbar.setCheckable(True)
        self.act_settings_show_statusbar.setChecked(True)
        self.act_settings_show_statusbar.toggled.connect(self.slot_showStatusbar)

        # Standalone Logs Window action
        self.act_settings_show_logs = QAction(self.tr("Show Logs Window"), self)
        self.act_settings_show_logs.triggered.connect(self.slot_showLogsWindow)

        # Cleanly reorder Settings menu: panels/toggles first, then standalone tools, then configure/preferences last
        self.ui.menu_Settings.clear()
        self.ui.menu_Settings.addAction(self.act_settings_modern_ui)
        self.ui.menu_Settings.addAction(self.act_settings_show_menubar)
        self.ui.menu_Settings.addAction(self.ui.act_settings_show_toolbar)
        self.ui.menu_Settings.addAction(self.act_settings_show_statusbar)
        self.ui.menu_Settings.addAction(self.ui.act_settings_show_side_panel)
        self.ui.menu_Settings.addAction(self.ui.act_settings_show_meters)
        self.ui.menu_Settings.addAction(self.ui.act_settings_show_keyboard)
        self.ui.menu_Settings.addSeparator()
        self.ui.menu_Settings.addAction(self.act_settings_show_logs)
        self.ui.menu_Settings.addSeparator()
        self.ui.menu_Settings.addAction(self.ui.act_settings_configure)

        self.addAction(self.act_settings_show_menubar)
        self.addAction(self.act_settings_show_statusbar)
        self.addAction(self.ui.act_file_save)
        self.addAction(self.ui.act_file_save_as)
        self.addAction(self.ui.act_file_open)
        self.addAction(self.ui.act_file_new)

        sc_app = getattr(Qt, "ApplicationShortcut", getattr(Qt.ShortcutContext, "ApplicationShortcut", Qt.WindowShortcut))
        self.ui.act_file_save.setShortcutContext(sc_app)
        self.ui.act_file_save_as.setShortcutContext(sc_app)
        self.ui.act_file_open.setShortcutContext(sc_app)
        self.ui.act_file_new.setShortcutContext(sc_app)

        self.ui.act_help_about.setText(self.tr("&About Clara"))

        self.act_help_check_updates = QAction(self.tr("Check for Updates..."), self)
        self.act_help_check_updates.triggered.connect(self.slot_checkForUpdates)
        self.ui.menu_Help.insertAction(self.ui.act_help_about, self.act_help_check_updates)

        self.act_help_support = QAction(self.tr("Support Clara..."), self)
        self.act_help_support.triggered.connect(lambda: self._check_and_show_support_banner(force=True))
        self.ui.menu_Help.insertAction(self.ui.act_help_about, self.act_help_support)
        self.ui.menu_Help.insertSeparator(self.ui.act_help_about)

        # Hamburger Menu button for when menubar is hidden
        self.btn_hamburger_menu = QToolButton(self.ui.toolBar)
        self.btn_hamburger_menu.setText("☰")
        self.btn_hamburger_menu.setToolTip(self.tr("Main Menu (Ctrl+M to toggle full menubar)"))
        popup_mode = getattr(QToolButton.ToolButtonPopupMode, "InstantPopup", getattr(QToolButton, "InstantPopup", None))
        if popup_mode is not None:
            self.btn_hamburger_menu.setPopupMode(popup_mode)
        self._hamburger_popup = QMenu(self.btn_hamburger_menu)
        self._hamburger_popup.addAction(self.ui.menu_File.menuAction())
        self._hamburger_popup.addAction(self.ui.menu_Engine.menuAction())
        self._hamburger_popup.addAction(self.ui.menu_Plugin.menuAction())
        self._hamburger_popup.addAction(self.ui.menu_Canvas.menuAction())
        self._hamburger_popup.addAction(self.ui.menu_Settings.menuAction())
        self._hamburger_popup.addAction(self.act_settings_show_logs)
        self._hamburger_popup.addAction(self.ui.menu_Help.menuAction())
        self.btn_hamburger_menu.setMenu(self._hamburger_popup)
        first_action = self.ui.toolBar.actions()[0] if self.ui.toolBar.actions() else None
        self.act_hamburger_toolbutton = self.ui.toolBar.insertWidget(first_action, self.btn_hamburger_menu)
        self.act_hamburger_toolbutton.setVisible(False)
        self.btn_hamburger_menu.setVisible(False)

        # ----------------------------------------------------------------------------------------------------
        # Load Settings

        self.loadSettings(True)

        # ----------------------------------------------------------------------------------------------------
        # Set-up System Tray

        self._setupSystemTray()

        # ----------------------------------------------------------------------------------------------------
        # Set-up Canvas

        if withCanvas:
            self.scene = patchcanvas.PatchScene(self, self.ui.graphicsView)
            self.ui.graphicsView.setScene(self.scene)

            if self.fSavedSettings[CARLA_KEY_CANVAS_USE_OPENGL] and hasGL:
                self.ui.glView = QGLWidget(self)
                if self.fSavedSettings[CARLA_KEY_CANVAS_ANTIALIASING] != patchcanvas.ANTIALIASING_NONE:
                    gl_format = QSurfaceFormat()
                    gl_format.setSamples(4)
                    self.ui.glView.setFormat(gl_format)
                self.ui.graphicsView.setViewport(self.ui.glView)

            self.setupCanvas()

        # ----------------------------------------------------------------------------------------------------
        # Set-up Icons

        if self.fSavedSettings[CARLA_KEY_MAIN_SYSTEM_ICONS]:
            self.ui.act_file_connect.setIcon(getIcon("network-connect", 16, "svgz"))
            self.ui.act_file_refresh.setIcon(getIcon("view-refresh", 16, "svgz"))
            self.ui.act_file_new.setIcon(getIcon("document-new", 16, "svgz"))
            self.ui.act_file_open.setIcon(getIcon("document-open", 16, "svgz"))
            self.ui.act_file_save.setIcon(getIcon("document-save", 16, "svgz"))
            self.ui.act_file_save_as.setIcon(getIcon("document-save-as", 16, "svgz"))
            self.ui.act_file_quit.setIcon(getIcon("application-exit", 16, "svgz"))
            self.ui.act_engine_start.setIcon(
                getIcon("media-playback-start", 16, "svgz")
            )
            self.ui.act_engine_stop.setIcon(getIcon("media-playback-stop", 16, "svgz"))
            self.ui.act_engine_panic.setIcon(getIcon("dialog-warning", 16, "svgz"))
            self.ui.act_engine_config.setIcon(getIcon("configure", 16, "svgz"))
            self.ui.act_plugin_add.setIcon(getIcon("list-add", 16, "svgz"))
            self.ui.act_plugin_add_jack.setIcon(getIcon("list-add", 16, "svgz"))
            self.ui.act_plugin_remove_all.setIcon(getIcon("edit-delete", 16, "svgz"))
            self.ui.act_canvas_arrange.setIcon(
                getIcon("view-sort-ascending", 16, "svgz")
            )
            self.ui.act_canvas_refresh.setIcon(getIcon("view-refresh", 16, "svgz"))
            self.ui.act_canvas_zoom_fit.setIcon(getIcon("zoom-fit-best", 16, "svgz"))
            self.ui.act_canvas_zoom_in.setIcon(getIcon("zoom-in", 16, "svgz"))
            self.ui.act_canvas_zoom_out.setIcon(getIcon("zoom-out", 16, "svgz"))
            self.ui.act_canvas_zoom_100.setIcon(getIcon("zoom-original", 16, "svgz"))
            self.ui.act_settings_configure.setIcon(getIcon("configure", 16, "svgz"))
            self.ui.b_disk_add.setIcon(getIcon("list-add", 16, "svgz"))
            self.ui.b_disk_remove.setIcon(getIcon("list-remove", 16, "svgz"))
            self.ui.b_transport_play.setIcon(
                getIcon("media-playback-start", 16, "svgz")
            )
            self.ui.b_transport_stop.setIcon(getIcon("media-playback-stop", 16, "svgz"))
            self.ui.b_transport_backwards.setIcon(
                getIcon("media-seek-backward", 16, "svgz")
            )
            self.ui.b_transport_forwards.setIcon(
                getIcon("media-seek-forward", 16, "svgz")
            )
            self.ui.logs_clear.setIcon(getIcon("edit-clear", 16, "svgz"))
            self.ui.logs_save.setIcon(getIcon("document-save", 16, "svgz"))

        # ----------------------------------------------------------------------------------------------------
        # Connect actions to functions

        self.ui.act_file_new.triggered.connect(self.slot_fileNew)
        self.ui.act_file_open.triggered.connect(self.slot_fileOpen)
        self.ui.act_file_save.triggered.connect(self.slot_fileSave)
        self.ui.act_file_save_as.triggered.connect(self.slot_fileSaveAs)

        self.updateRecentProjectsMenu()

        self.ui.act_engine_start.triggered.connect(self.slot_engineStart)
        self.ui.act_engine_stop.triggered.connect(self.slot_engineStop)
        self.ui.act_engine_panic.triggered.connect(self.slot_pluginsDisable)
        self.ui.act_engine_config.triggered.connect(self.slot_engineConfig)

        self.ui.act_plugin_add.triggered.connect(self.slot_pluginAdd)
        self.ui.act_plugin_add_jack.triggered.connect(self.slot_jackAppAdd)
        self.ui.act_plugin_remove_all.triggered.connect(self.slot_confirmRemoveAll)

        self.ui.act_plugins_enable.triggered.connect(self.slot_pluginsEnable)
        self.ui.act_plugins_disable.triggered.connect(self.slot_pluginsDisable)
        self.ui.act_plugins_volume100.triggered.connect(self.slot_pluginsVolume100)
        self.ui.act_plugins_mute.triggered.connect(self.slot_pluginsMute)
        self.ui.act_plugins_wet100.triggered.connect(self.slot_pluginsWet100)
        self.ui.act_plugins_bypass.triggered.connect(self.slot_pluginsBypass)
        self.ui.act_plugins_center.triggered.connect(self.slot_pluginsCenter)
        self.ui.act_plugins_compact.triggered.connect(self.slot_pluginsCompact)
        self.ui.act_plugins_expand.triggered.connect(self.slot_pluginsExpand)

        # Allow right-clicking top toolbar to toggle menubar/toolbar
        self.ui.toolBar.setContextMenuPolicy(Qt.CustomContextMenu)
        self.ui.toolBar.customContextMenuRequested.connect(self._slot_toolbarContextMenu)

        self.ui.act_settings_show_toolbar.toggled.connect(self.slot_showToolbar)
        self.ui.act_settings_show_meters.toggled.connect(self.slot_showCanvasMeters)
        self.ui.act_settings_show_keyboard.toggled.connect(self.slot_showCanvasKeyboard)
        self.ui.act_settings_show_side_panel.toggled.connect(self.slot_showSidePanel)
        self.ui.act_settings_configure.triggered.connect(self.slot_configureCarla)

        self.ui.act_help_about.triggered.connect(self.slot_aboutCarla)
        self.ui.act_help_about_qt.triggered.connect(self.slot_aboutQt)

        self.ui.cb_disk.currentIndexChanged.connect(self.slot_diskFolderChanged)
        self.ui.b_disk_add.clicked.connect(self.slot_diskFolderAdd)
        self.ui.b_disk_remove.clicked.connect(self.slot_diskFolderRemove)
        self.ui.fileTreeView.doubleClicked.connect(self.slot_fileTreeDoubleClicked)

        self.ui.b_transport_play.clicked.connect(self.slot_transportPlayPause)
        self.ui.b_transport_stop.clicked.connect(self.slot_transportStop)
        self.ui.b_transport_backwards.clicked.connect(self.slot_transportBackwards)
        self.ui.b_transport_forwards.clicked.connect(self.slot_transportForwards)
        self.ui.dsb_transport_bpm.valueChanged.connect(self.slot_transportBpmChanged)
        self.ui.cb_transport_jack.clicked.connect(self.slot_transportJackEnabled)
        self.ui.cb_transport_link.clicked.connect(self.slot_transportLinkEnabled)

        self.ui.b_xruns.clicked.connect(self.slot_xrunClear)

        self.ui.listWidget.customContextMenuRequested.connect(
            self.slot_showPluginActionsMenu
        )

        self.ui.keyboard.noteOn.connect(self.slot_noteOn)
        self.ui.keyboard.noteOff.connect(self.slot_noteOff)

        self.ui.tabWidget.currentChanged.connect(self.slot_tabChanged)
        self.ui.toolBar.visibilityChanged.connect(self.slot_toolbarVisibilityChanged)

        if withCanvas:
            self.ui.act_canvas_show_internal.setChecked(not self.fExternalPatchbay)
            self.ui.act_canvas_show_external.setChecked(self.fExternalPatchbay)
            self.ui.act_canvas_show_internal.triggered.connect(
                self.slot_canvasShowInternal
            )
            self.ui.act_canvas_show_external.triggered.connect(
                self.slot_canvasShowExternal
            )
            self.ui.act_canvas_arrange.triggered.connect(self.slot_canvasArrange)
            self.ui.act_canvas_refresh.triggered.connect(self.slot_canvasRefresh)
            self.ui.act_canvas_zoom_fit.triggered.connect(self.slot_canvasZoomFit)
            self.ui.act_canvas_zoom_in.triggered.connect(self.slot_canvasZoomIn)
            self.ui.act_canvas_zoom_out.triggered.connect(self.slot_canvasZoomOut)
            self.ui.act_canvas_zoom_100.triggered.connect(self.slot_canvasZoomReset)
            self.ui.act_canvas_save_image.triggered.connect(self.slot_canvasSaveImage)
            self.ui.act_canvas_save_image_2x.triggered.connect(
                self.slot_canvasSaveImage
            )
            self.ui.act_canvas_save_image_4x.triggered.connect(
                self.slot_canvasSaveImage
            )
            self.ui.act_canvas_copy_clipboard.triggered.connect(
                self.slot_canvasCopyToClipboard
            )
            self.ui.act_canvas_arrange.setEnabled(True)

            self.act_canvas_side_by_side = QAction(self.tr("Side-by-Side View"), self)
            self.act_canvas_side_by_side.setCheckable(True)
            self.act_canvas_side_by_side.setChecked(False)
            self.act_canvas_side_by_side.setShortcut("Ctrl+Shift+R")
            self.act_canvas_side_by_side.setIcon(getIcon("view-refresh", 16, "svgz"))
            self.act_canvas_side_by_side.toggled.connect(self.slot_toggleSideBySideView)
            self.ui.menu_Canvas.addAction(self.act_canvas_side_by_side)
            self.ui.toolBar.addAction(self.act_canvas_side_by_side)

            # Restore side-by-side settings if saved. Modern UI is the master
            # switch (toggling it forces this layout), so it wins over a stale
            # SideBySideEnabled=false and the startup view matches the menu.
            settings = QSettings()
            modernUi = settings.value("ModernUiMode", True, bool)
            sideBySide = settings.value("SideBySideEnabled", modernUi, bool)
            if modernUi:
                sideBySide = True
            if sideBySide:
                self.act_canvas_side_by_side.setChecked(True)
                self.slot_toggleSideBySideView(True)
                saved_sizes = settings.value("SideBySideSizes", None)
                if saved_sizes and hasattr(self, "splitter") and self.splitter is not None:
                    try:
                        int_sizes = [int(s) for s in saved_sizes]
                        if len(int_sizes) == 2:
                            self.splitter.setSizes(int_sizes)
                    except Exception:
                        pass

            self.ui.listWidget.itemClicked.connect(self.slot_rackItemClicked)
            self.ui.listWidget.itemSelectionChanged.connect(self.slot_rackSelectionChanged)

            self.ui.graphicsView.horizontalScrollBar().valueChanged.connect(
                self.slot_horizontalScrollBarChanged
            )
            self.ui.graphicsView.verticalScrollBar().valueChanged.connect(
                self.slot_verticalScrollBarChanged
            )
            self.ui.miniCanvasPreview.miniCanvasMoved.connect(self.slot_miniCanvasMoved)
            self.scene.scaleChanged.connect(self.slot_canvasScaleChanged)
            self.scene.pluginSelected.connect(self.slot_canvasPluginSelected)
            self.scene.selectionChanged.connect(self.slot_canvasSelectionChanged)

        self.SIGUSR1.connect(self.slot_handleSIGUSR1)
        self.SIGTERM.connect(self.slot_handleSIGTERM)
        self.SIGINT.connect(self.slot_handleSIGINT)

        host.EngineStartedCallback.connect(self.slot_handleEngineStartedCallback)
        host.EngineStoppedCallback.connect(self.slot_handleEngineStoppedCallback)
        host.TransportModeChangedCallback.connect(
            self.slot_handleTransportModeChangedCallback
        )
        host.BufferSizeChangedCallback.connect(
            self.slot_handleBufferSizeChangedCallback
        )
        host.SampleRateChangedCallback.connect(
            self.slot_handleSampleRateChangedCallback
        )
        host.CancelableActionCallback.connect(self.slot_handleCancelableActionCallback)
        host.ProjectLoadFinishedCallback.connect(
            self.slot_handleProjectLoadFinishedCallback
        )

        host.PluginAddedCallback.connect(self.slot_handlePluginAddedCallback)
        host.PluginRemovedCallback.connect(self.slot_handlePluginRemovedCallback)
        host.ReloadAllCallback.connect(self.slot_handleReloadAllCallback)

        host.NoteOnCallback.connect(self.slot_handleNoteOnCallback)
        host.NoteOffCallback.connect(self.slot_handleNoteOffCallback)

        host.UpdateCallback.connect(self.slot_handleUpdateCallback)

        if withCanvas:
            host.PatchbayClientAddedCallback.connect(
                self.slot_handlePatchbayClientAddedCallback
            )
            host.PatchbayClientRemovedCallback.connect(
                self.slot_handlePatchbayClientRemovedCallback
            )
            host.PatchbayClientRenamedCallback.connect(
                self.slot_handlePatchbayClientRenamedCallback
            )
            host.PatchbayClientDataChangedCallback.connect(
                self.slot_handlePatchbayClientDataChangedCallback
            )
            host.PatchbayClientPositionChangedCallback.connect(
                self.slot_handlePatchbayClientPositionChangedCallback
            )
            host.PatchbayPortAddedCallback.connect(
                self.slot_handlePatchbayPortAddedCallback
            )
            host.PatchbayPortRemovedCallback.connect(
                self.slot_handlePatchbayPortRemovedCallback
            )
            host.PatchbayPortChangedCallback.connect(
                self.slot_handlePatchbayPortChangedCallback
            )
            host.PatchbayPortGroupAddedCallback.connect(
                self.slot_handlePatchbayPortGroupAddedCallback
            )
            host.PatchbayPortGroupRemovedCallback.connect(
                self.slot_handlePatchbayPortGroupRemovedCallback
            )
            host.PatchbayPortGroupChangedCallback.connect(
                self.slot_handlePatchbayPortGroupChangedCallback
            )
            host.PatchbayConnectionAddedCallback.connect(
                self.slot_handlePatchbayConnectionAddedCallback
            )
            host.PatchbayConnectionRemovedCallback.connect(
                self.slot_handlePatchbayConnectionRemovedCallback
            )

        host.NSMCallback.connect(self.slot_handleNSMCallback)

        host.DebugCallback.connect(self.slot_handleDebugCallback)
        host.InfoCallback.connect(self.slot_handleInfoCallback)
        host.ErrorCallback.connect(self.slot_handleErrorCallback)
        host.QuitCallback.connect(self.slot_handleQuitCallback)
        host.InlineDisplayRedrawCallback.connect(
            self.slot_handleInlineDisplayRedrawCallback
        )

        # ----------------------------------------------------------------------------------------------------
        # Final setup

        self.ui.text_logs.clear()
        self.slot_logButtonsState(False)
        self.setProperWindowTitle()

        # Disable non-supported features
        features = gCarla.utils.get_supported_features()

        if "link" not in features:
            self.ui.cb_transport_link.setEnabled(False)
            self.ui.cb_transport_link.setVisible(False)

        # Plugin needs to have timers always running so it receives messages
        if self.host.isPlugin or self.host.isRemote:
            self.startTimers()

        # Qt needs this so it properly creates & resizes the canvas
        self.ui.tabWidget.blockSignals(True)
        self.ui.tabWidget.setCurrentIndex(1)
        self.ui.tabWidget.setCurrentIndex(0)
        self.ui.tabWidget.blockSignals(False)

        # Start in patchbay tab if using forced patchbay mode
        if host.processModeForced and host.processMode == ENGINE_PROCESS_MODE_PATCHBAY:
            self.ui.tabWidget.setCurrentIndex(1)

        # Load initial project file if set
        if not (self.host.isControl or self.host.isPlugin):
            projectFile = getInitialProjectFile(QApplication.instance())

            if projectFile:
                self.loadProjectLater(projectFile)

        # Initialize ProjectSessionManager
        self.fSessionManager = ProjectSessionManager(self)
        self.fSessionManager.start(
            interval_minutes=self.fSavedSettings.get(CARLA_KEY_MAIN_AUTOSAVE_INTERVAL, CARLA_DEFAULT_MAIN_AUTOSAVE_INTERVAL),
            max_autosaves=self.fSavedSettings.get(CARLA_KEY_MAIN_AUTOSAVE_MAX, CARLA_DEFAULT_MAIN_AUTOSAVE_MAX),
            enabled=self.fSavedSettings.get(CARLA_KEY_MAIN_AUTOSAVE_ENABLED, CARLA_DEFAULT_MAIN_AUTOSAVE_ENABLED),
        )

        # Autosave and project status indicators in statusbar
        self.label_save_status = QLabel(self.ui.tw_statusbar)
        self.label_save_status.setObjectName("label_save_status")
        self.label_save_status.setStyleSheet("font-weight: bold; margin-left: 6px; margin-right: 4px;")
        self.label_save_status.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Fixed)
        self.label_save_status.setMinimumWidth(0)
        self.ui.horizontalLayout_3.addWidget(self.label_save_status)

        self.label_autosave_status = QLabel(self.ui.tw_statusbar)
        self.label_autosave_status.setObjectName("label_autosave_status")
        self.label_autosave_status.setStyleSheet("color: gray; margin-left: 4px; margin-right: 6px;")
        self.label_autosave_status.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Fixed)
        self.label_autosave_status.setMinimumWidth(0)
        self.ui.horizontalLayout_3.addWidget(self.label_autosave_status)

        # Allow statusbar controls to flex on narrow screens (e.g. half-screen tiling)
        if hasattr(self.ui, "pb_dsp_load") and self.ui.pb_dsp_load is not None:
            self.ui.pb_dsp_load.setMinimumWidth(40)
            self.ui.pb_dsp_load.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        if hasattr(self.ui, "cb_buffer_size") and self.ui.cb_buffer_size is not None:
            self.ui.cb_buffer_size.setMinimumWidth(40)
            self.ui.cb_buffer_size.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
        if hasattr(self.ui, "cb_sample_rate") and self.ui.cb_sample_rate is not None:
            self.ui.cb_sample_rate.setMinimumWidth(40)
            self.ui.cb_sample_rate.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
        if hasattr(self.ui, "b_xruns") and self.ui.b_xruns is not None:
            self.ui.b_xruns.setMinimumWidth(40)
            self.ui.b_xruns.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
        if hasattr(self.ui, "tw_statusbar") and self.ui.tw_statusbar is not None:
            self.ui.tw_statusbar.setMinimumWidth(0)

        self.updateSessionStatusIndicators()

        # For NSM we wait for the open message
        if NSM_URL and host.nsmOK:
            host.nsm_ready(NSM_CALLBACK_INIT)
            return

        if not host.isControl:
            if not (self.host.isPlugin or projectFile):
                QTimer.singleShot(0, self.checkRecentOnStartup)
            else:
                QTimer.singleShot(0, self.slot_engineStart)
            if not self.host.isPlugin:
                QTimer.singleShot(1500, self.startStartupPluginScanner)
            QTimer.singleShot(400, self._prewarmSettingsDialog)

    # --------------------------------------------------------------------------------------------------------
    # Manage visibility state, needed for NSM

    def hideForNSM(self):
        for pitem in reversed(self.fPluginList):
            if pitem is None:
                continue
            pitem.getWidget().hideCustomUI()
        self.hide()

    def showIfNeeded(self):
        if self.host.nsmOK:
            self.ui.act_file_quit.setText(self.tr("Hide"))
            QApplication.instance().setQuitOnLastWindowClosed(False)
        else:
            self.show()

    # --------------------------------------------------------------------------------------------------------
    # Setup

    def compactPlugin(self, pluginId):
        pitem = self.getPluginItem(pluginId)
        if pitem is None:
            return

        widget = pitem.getWidget() if hasattr(pitem, "getWidget") else None
        if widget is not None and hasattr(widget, "toggleCompacted"):
            widget.toggleCompacted()
            return

        pitem.recreateWidget(True)
        if self.ui.listWidget is not None:
            self.ui.listWidget.doItemsLayout()

    def changePluginColor(self, pluginId, color, colorStr):
        pitem = self.getPluginItem(pluginId)
        if pitem is None:
            return

        self.host.set_custom_data(
            pluginId, CUSTOM_DATA_TYPE_PROPERTY, "CarlaColor", colorStr
        )
        self.fHasUnsavedChanges = True
        if hasattr(self, "markProjectModified"):
            self.markProjectModified()
        pitem.recreateWidget(newColor=color)
        if self.ui.listWidget is not None:
            self.ui.listWidget.doItemsLayout()

        # Sync color to patchbay canvas node
        if self.fWithCanvas:
            hex_col = f"#{color[0]:02x}{color[1]:02x}{color[2]:02x}" if color != (255, 255, 255) else None
            for group in patchcanvas.canvas.group_list:
                if getattr(group, "plugin_id", -1) == pluginId:
                    for w in getattr(group, "widgets", []):
                        if w is not None:
                            w.setCustomColor(hex_col, notify=False)
                    break

    def changePluginSkin(self, pluginId, skin):
        pitem = self.getPluginItem(pluginId)
        if pitem is None:
            return

        self.host.set_custom_data(
            pluginId, CUSTOM_DATA_TYPE_PROPERTY, "CarlaSkin", skin
        )
        self.fHasUnsavedChanges = True
        existingColor = self.host.get_custom_data_value(
            pluginId, CUSTOM_DATA_TYPE_PROPERTY, "CarlaColor"
        )
        if existingColor:
            try:
                col = tuple(int(i) for i in existingColor.split(";", 3))
                pitem.recreateWidget(newSkin=skin, newColor=col)
                if self.ui.listWidget is not None:
                    self.ui.listWidget.doItemsLayout()
                return
            except Exception:
                pass

        if skin not in ("default", "rncbc", "presets", "mpresets"):
            self.host.set_custom_data(
                pluginId, CUSTOM_DATA_TYPE_PROPERTY, "CarlaColor", "255;255;255"
            )
            pitem.recreateWidget(newSkin=skin, newColor=(255, 255, 255))
        else:
            pitem.recreateWidget(newSkin=skin)

        if self.ui.listWidget is not None:
            self.ui.listWidget.doItemsLayout()

    def findPluginInPatchbay(self, pluginId):
        if pluginId > self.fPluginCount:
            return

        if self.fExternalPatchbay:
            self.slot_canvasShowInternal()

        if not patchcanvas.focusGroupUsingPluginId(pluginId):
            name = self.host.get_plugin_info(pluginId)["name"]
            if not patchcanvas.focusGroupUsingGroupName(name):
                return

        self.ui.tabWidget.setCurrentIndex(1)

    def switchPlugins(self, pluginIdA, pluginIdB):
        if pluginIdA == pluginIdB:
            return
        if pluginIdA < 0 or pluginIdB < 0:
            return
        if pluginIdA >= len(self.fPluginList) or pluginIdB >= len(self.fPluginList):
            return

        itemA = self.fPluginList[pluginIdA]
        itemB = self.fPluginList[pluginIdB]
        if itemA is None or itemB is None:
            return

        # 1. Fetch visual options and custom data before swap
        compactA = itemA.isCompacted()
        guiShownA = itemA.isGuiShown()
        colorA = itemA.fOptions.get("color") if hasattr(itemA, "fOptions") else None
        skinA = itemA.fOptions.get("skin") if hasattr(itemA, "fOptions") else None
        colorStrA = self.host.get_custom_data_value(
            pluginIdA, CUSTOM_DATA_TYPE_PROPERTY, "CarlaColor"
        )
        skinStrA = self.host.get_custom_data_value(
            pluginIdA, CUSTOM_DATA_TYPE_PROPERTY, "CarlaSkin"
        )
        compactStrA = self.host.get_custom_data_value(
            pluginIdA, CUSTOM_DATA_TYPE_PROPERTY, "CarlaSkinIsCompacted"
        )

        compactB = itemB.isCompacted()
        guiShownB = itemB.isGuiShown()
        colorB = itemB.fOptions.get("color") if hasattr(itemB, "fOptions") else None
        skinB = itemB.fOptions.get("skin") if hasattr(itemB, "fOptions") else None
        colorStrB = self.host.get_custom_data_value(
            pluginIdB, CUSTOM_DATA_TYPE_PROPERTY, "CarlaColor"
        )
        skinStrB = self.host.get_custom_data_value(
            pluginIdB, CUSTOM_DATA_TYPE_PROPERTY, "CarlaSkin"
        )
        compactStrB = self.host.get_custom_data_value(
            pluginIdB, CUSTOM_DATA_TYPE_PROPERTY, "CarlaSkinIsCompacted"
        )

        # Determine which rack item was selected/active before swap
        was_selected_b = itemB.isSelected() or (
            self.ui.listWidget is not None
            and self.ui.listWidget.currentRow() == pluginIdB
        )
        target_row = pluginIdA if was_selected_b else pluginIdB
        other_row = pluginIdB if was_selected_b else pluginIdA

        # 2. Perform engine switch
        self.host.switch_plugins(pluginIdA, pluginIdB)
        self.fHasUnsavedChanges = True

        # 3. Swap custom data on the host so it persists and matches the moved plugins
        if colorStrB:
            self.host.set_custom_data(
                pluginIdA, CUSTOM_DATA_TYPE_PROPERTY, "CarlaColor", colorStrB
            )
        elif colorB:
            self.host.set_custom_data(
                pluginIdA,
                CUSTOM_DATA_TYPE_PROPERTY,
                "CarlaColor",
                "%i;%i;%i" % colorB[:3],
            )
        else:
            self.host.set_custom_data(
                pluginIdA, CUSTOM_DATA_TYPE_PROPERTY, "CarlaColor", ""
            )

        if colorStrA:
            self.host.set_custom_data(
                pluginIdB, CUSTOM_DATA_TYPE_PROPERTY, "CarlaColor", colorStrA
            )
        elif colorA:
            self.host.set_custom_data(
                pluginIdB,
                CUSTOM_DATA_TYPE_PROPERTY,
                "CarlaColor",
                "%i;%i;%i" % colorA[:3],
            )
        else:
            self.host.set_custom_data(
                pluginIdB, CUSTOM_DATA_TYPE_PROPERTY, "CarlaColor", ""
            )

        if skinStrB:
            self.host.set_custom_data(
                pluginIdA, CUSTOM_DATA_TYPE_PROPERTY, "CarlaSkin", skinStrB
            )
        elif skinB:
            self.host.set_custom_data(
                pluginIdA, CUSTOM_DATA_TYPE_PROPERTY, "CarlaSkin", skinB
            )

        if skinStrA:
            self.host.set_custom_data(
                pluginIdB, CUSTOM_DATA_TYPE_PROPERTY, "CarlaSkin", skinStrA
            )
        elif skinA:
            self.host.set_custom_data(
                pluginIdB, CUSTOM_DATA_TYPE_PROPERTY, "CarlaSkin", skinA
            )

        if compactStrB:
            self.host.set_custom_data(
                pluginIdA,
                CUSTOM_DATA_TYPE_PROPERTY,
                "CarlaSkinIsCompacted",
                compactStrB,
            )
        if compactStrA:
            self.host.set_custom_data(
                pluginIdB,
                CUSTOM_DATA_TYPE_PROPERTY,
                "CarlaSkinIsCompacted",
                compactStrA,
            )

        # 4. Swap fOptions on the CarlaRackItem objects
        if hasattr(itemA, "fOptions") and hasattr(itemB, "fOptions"):
            itemA.fOptions["color"] = colorB
            itemA.fOptions["skin"] = skinB
            itemA.fOptions["compact"] = compactB

            itemB.fOptions["color"] = colorA
            itemB.fOptions["skin"] = skinA
            itemB.fOptions["compact"] = compactA

        # 5. Recreate widgets with the swapped states
        itemA.setPluginId(pluginIdA)
        itemA.recreateWidget2(compactB, guiShownB)

        itemB.setPluginId(pluginIdB)
        itemB.recreateWidget2(compactA, guiShownA)

        # 6. Restore keyboard focus and selection to the moved rack item
        if self.ui.listWidget is not None:
            self.ui.listWidget.setFocus()
            self.ui.listWidget.setCurrentRow(target_row)
            target_item = self.fPluginList[target_row]
            if target_item is not None:
                self.ui.listWidget.setCurrentItem(target_item)
                target_item.setSelected(True)
                target_widget = (
                    target_item.getWidget()
                    if hasattr(target_item, "getWidget")
                    else None
                )
                if target_widget is not None:
                    if hasattr(target_widget, "setSelected"):
                        target_widget.setSelected(True)
                    target_widget.setFocus()

            other_item = self.fPluginList[other_row]
            if other_item is not None:
                other_item.setSelected(False)
                other_widget = (
                    other_item.getWidget() if hasattr(other_item, "getWidget") else None
                )
                if other_widget is not None and hasattr(other_widget, "setSelected"):
                    other_widget.setSelected(False)

            self.ui.listWidget.doItemsLayout()

        # 7. Only refresh canvas if the patchbay canvas tab is actually active
        if self.fWithCanvas:
            if self.ui.tabWidget.currentIndex() == 1:
                if (
                    not hasattr(self, "_canvasRefreshTimer")
                    or self._canvasRefreshTimer is None
                ):
                    self._canvasRefreshTimer = QTimer(self)
                    self._canvasRefreshTimer.setSingleShot(True)
                    self._canvasRefreshTimer.timeout.connect(self.slot_canvasRefresh)
                self._canvasRefreshTimer.start(300)
            else:
                self.fNeedCanvasRefresh = True

    def setLoadRDFsNeeded(self):
        self.fLadspaRdfNeedsUpdate = True

    def setProperWindowTitle(self):
        title = self.fClientName

        if self.fProjectFilename and not self.host.nsmOK:
            title += " - %s" % os.path.basename(self.fProjectFilename)
        if self.fSessionManagerName:
            title += " (%s)" % self.fSessionManagerName

        if getattr(self, "fHasUnsavedChanges", False):
            title = "* " + title

        self.setWindowTitle(title)
        self.updateSessionStatusIndicators()

    def markProjectModified(self):
        if not getattr(self, "fHasUnsavedChanges", False):
            self.fHasUnsavedChanges = True
            self.setProperWindowTitle()

    def updateSessionStatusIndicators(self):
        if not hasattr(self, "label_save_status") or not hasattr(self, "label_autosave_status"):
            return

        is_dirty = getattr(self, "fHasUnsavedChanges", False)
        if is_dirty:
            self.label_save_status.setText(self.tr("● Unsaved"))
            self.label_save_status.setStyleSheet("color: #ffaa00; font-weight: bold; margin-left: 8px; margin-right: 4px;")
        else:
            self.label_save_status.setText(self.tr("✓ Saved"))
            self.label_save_status.setStyleSheet("color: #55ff55; font-weight: bold; margin-left: 8px; margin-right: 4px;")

        if hasattr(self, "fSessionManager") and self.fSessionManager is not None and self.fSessionManager.enabled:
            secs_left = self.fSessionManager.get_seconds_until_next_autosave()
            last_time = self.fSessionManager.last_autosave_time
            last_str = last_time.strftime("%H:%M:%S") if last_time else self.tr("None")

            if secs_left is not None:
                mins = secs_left // 60
                secs = secs_left % 60
                self.label_autosave_status.setText(self.tr(f"Autosave: last {last_str} | next in {mins:02d}:{secs:02d}"))
            else:
                self.label_autosave_status.setText(self.tr(f"Autosave: last {last_str}"))
        else:
            self.label_autosave_status.setText(self.tr("Autosave: Off"))

    def updateBufferSize(self, newBufferSize):
        if self.fBufferSize == newBufferSize:
            return
        self.fBufferSize = newBufferSize
        self.ui.cb_buffer_size.clear()
        self.ui.cb_buffer_size.addItem(str(newBufferSize))
        self.ui.cb_buffer_size.setCurrentIndex(0)

    def updateSampleRate(self, newSampleRate):
        if self.fSampleRate == newSampleRate:
            return
        self.fSampleRate = newSampleRate
        self.ui.cb_sample_rate.clear()
        self.ui.cb_sample_rate.addItem(str(newSampleRate))
        self.ui.cb_sample_rate.setCurrentIndex(0)
        self.refreshTransport(True)

    # --------------------------------------------------------------------------------------------------------
    # Files

    def _prepareCanvasForLoad(self, load_source):
        """Seed saved positions and containers before plugins arrive, so boxes are born
        in place instead of jumping there after the load."""
        if not self.fWithCanvas:
            return

        self.fUserPannedCanvas = False
        self._lastAutoCenter = None

        try:
            positions = storage_manager.load_canvas_positions(load_source)
        except Exception as e:
            logger.warning("CANVAS", f"prepareCanvasForLoad failed: {e}")
            return

        if not positions:
            return

        bridge_plugins = getattr(positions, "bridge_plugins", None)
        self.fLoadingBridgePlugins = list(bridge_plugins) if bridge_plugins is not None else None

        patchcanvas.canvas.old_group_pos = {}
        for data in positions:
            name = data.get("name")
            if not name:
                continue
            split = bool(data.get("split"))
            patchcanvas.canvas.old_group_pos[name] = (
                split,
                QPointF(float(data.get("pos1x", 0)), float(data.get("pos1y", 0))),
                QPointF(float(data.get("pos2x", 0)), float(data.get("pos2y", 0))) if split else None,
            )

        containers = getattr(positions, "patchbay_containers", None)
        if containers:
            try:
                patchcanvas.loadContainers(containers)
            except Exception as e:
                logger.warning("CANVAS", f"prepareCanvasForLoad containers failed: {e}")

        plugin_names = set()
        root = None
        try:
            root = storage_manager.get_project_root(load_source)
            if root is not None:
                for plugin in root.findall("Plugin"):
                    info = plugin.find("Info")
                    if info is not None:
                        plugin_names.add(info.findtext("Name", "") or "")
        except Exception as e:
            logger.warning("CANVAS", f"prepareCanvasForLoad project root failed: {e}")

        # Skeleton: draw every node from the file now, replace it as the real one arrives.
        patchcanvas.clearGhosts()
        patchcanvas.clearGhostCables()
        for data in positions:
            name = data.get("name")
            if not name:
                continue
            try:
                patchcanvas.addGroupShell(
                    name,
                    QPointF(float(data.get("pos1x", 0)), float(data.get("pos1y", 0))),
                    bool(data.get("split")),
                    data.get("left") or [],
                    data.get("right") or [],
                    bool(data.get("hide_unconnected_ports")),
                    data.get("color") or "",
                    data.get("port_modes") or {},
                    name in plugin_names,
                    data.get("port_types") or {},
                    (data.get("width"), data.get("height")) if data.get("width") and data.get("height") else None,
                )
            except Exception as e:
                logger.warning("CANVAS", f"prepareCanvasForLoad shell '{name}' failed: {e}")

        try:
            if root is not None:
                for section in ("ExternalPatchbay", "Patchbay"):
                    patchbay = root.find(section)
                    if patchbay is None:
                        continue
                    for conn in patchbay.findall("Connection"):
                        src = conn.findtext("Source") or conn.findtext("PortOut")
                        dst = conn.findtext("Target") or conn.findtext("PortIn")
                        if not src or not dst:
                            continue
                        src_group, _, src_port = src.rpartition(":")
                        dst_group, _, dst_port = dst.rpartition(":")
                        patchcanvas.addShellConnection(src_group, src_port, dst_group, dst_port)
        except Exception as e:
            logger.warning("CANVAS", f"prepareCanvasForLoad connections failed: {e}")

        patchcanvas.snapshotShellSizes()

    def loadProjectNow(self, source_override=None):
        if not self.fProjectFilename:
            qCritical("ERROR: loading project without filename set")
            return False
        if self.host.nsmOK and not os.path.exists(self.fProjectFilename):
            return True

        # Ensure canonical project filename to prevent nested .autosaves/
        if hasattr(self, "fSessionManager") and self.fSessionManager is not None:
            self.fProjectFilename = self.fSessionManager.get_canonical_project_filepath(self.fProjectFilename)
            self.setProperWindowTitle()

        load_source = source_override or self.fProjectFilename
        # Remember what was actually read so a recovery load restores canvas positions from the
        # autosave, while the project keeps its last-saved name/path (fProjectFilename).
        self.fLastLoadedSource = load_source
        self.projectLoadingStarted(load_source)
        if getattr(self, "fLoadingDialog", None) is not None:
            self.fLoadingDialog.setDetail(f"Preparing {os.path.basename(load_source)}...")
        self.fIsProjectLoading = True
        # Build the shells before the engine enumerates external clients, so every client
        # finds its shell already in place instead of creating a duplicate node.
        self._prepareCanvasForLoad(load_source)

        if not (self.host.isControl or self.host.is_engine_running()):
            self.slot_engineStart()

        # Check if project contains plugins prone to in-process UI/GL thread collisions
        force_bridged = False
        # A saved per-plugin map already says exactly which plugins need a bridge: never ask.
        bridge_plugins = getattr(self, "fLoadingBridgePlugins", None)
        self.fLoadingPluginTotal = 0
        try:
            # Format-agnostic: the save manager resolves the file (XML or JSON) and hands back a
            # common ElementTree root, so nothing here needs to know any extension.
            root = storage_manager.get_project_root(load_source)
            if root is not None:
                self.fLoadingPluginTotal = len(root.findall("Plugin"))
                eng_settings = root.find("EngineSettings")
                prefer_bridges = eng_settings.findtext("PreferPluginBridges") if eng_settings is not None else None
                if bridge_plugins is None and (not prefer_bridges or prefer_bridges.lower() in ("false", "0")):
                    # Plugins that create their own GL/UI context or run via Wine/yabridge and crash the host
                    # when loaded in-process.
                    collision_tokens = ("element", "juce", "cardinal", "decentsampler", "yabridge", "wine")
                    risky_plugin = None
                    for p in root.findall("Plugin"):
                        info = p.find("Info")
                        if info is None:
                            continue
                        p_name = (info.findtext("Name", "") or "").lower()
                        p_uri = (info.findtext("URI", "") or "").lower()
                        p_bin = (info.findtext("Binary", "") or "").lower()
                        if any(tok in p_name or tok in p_uri or tok in p_bin for tok in collision_tokens):
                            risky_plugin = info.findtext("Name", "") or info.findtext("URI", "") or self.tr("unknown")
                            break
                    if risky_plugin:
                        if getattr(gCarla, "autoload_lastsave", False):
                            force_bridged = True
                        else:
                            ask = QMessageBox.question(
                                self,
                                self.tr("Plugin Bridge Recommendation"),
                                self.tr(
                                    "This project contains plugins that may crash if loaded in-process "
                                    "(e.g. KV-Element / JUCE, Cardinal).\n\n"
                                    "Would you like to load plugins bridged in separate processes for stability?"
                                ),
                                QMessageBox.Yes | QMessageBox.No,
                                QMessageBox.Yes,
                            )
                            if ask == QMessageBox.Yes:
                                force_bridged = True
        except Exception as e:
            logger.warning("BRIDGE", f"Bridge pre-check warning: {e}")

        if bridge_plugins is not None:
            force_bridged = False

        logger.debug("SESSION", f"load_source='{load_source}', fProjectFilename='{self.fProjectFilename}', engine_running={self.host.is_engine_running()}")
        actual_load_filename = load_source
        tmp_cleanup_file = None
        try:
            actual_load_filename = storage_manager.prepare_for_backend_load(
                load_source, force_bridged=force_bridged, bridge_plugins=bridge_plugins
            )
            if actual_load_filename != load_source:
                tmp_cleanup_file = actual_load_filename
            logger.debug("BRIDGE", f"bridge_plugins={bridge_plugins} prepared={actual_load_filename}")
            logger.debug("SESSION", f"prepared actual_load_filename='{actual_load_filename}', exists={os.path.exists(actual_load_filename)}")
        except Exception as e:
            logger.error("SESSION", f"Failed to prepare project for loading: {e}")

        # Ensure engine backend is started before loading project
        if not (self.host.isControl or self.host.is_engine_running()):
            logger.info("SESSION", "Engine not running; calling slot_engineStart()")
            self.slot_engineStart()

        load_errors = []
        def _on_load_error(err):
            load_errors.append(str(err))
        self.host.ErrorCallback.connect(_on_load_error)

        load_ok = False
        load_exception = None
        log_history_start = len(logger.history)

        try:
            logger.debug("SESSION", f"Calling self.host.load_project('{actual_load_filename}')")
            load_ok = self.host.load_project(actual_load_filename)
            if load_ok:
                logger.info("SESSION", f"Project loaded successfully: {self.fProjectFilename or actual_load_filename}")
            else:
                logger.error("SESSION", f"load_project failed, last_error='{self.host.get_last_error()}'")
        except Exception as e:
            load_exception = str(e)
            logger.error("SESSION", f"Exception during load_project: {e}")
        finally:
            try:
                self.host.ErrorCallback.disconnect(_on_load_error)
            except Exception:
                pass

        if tmp_cleanup_file and os.path.exists(tmp_cleanup_file):
            try:
                os.remove(tmp_cleanup_file)
            except Exception:
                pass

        # Collect issues and log entries
        last_backend_err = self.host.get_last_error()
        issues = []
        if load_exception:
            issues.append(f"Load Exception: {load_exception}")
        if last_backend_err:
            issues.append(f"Backend message: {last_backend_err}")
        for err_msg in load_errors:
            if err_msg not in issues:
                issues.append(err_msg)

        recent_entries = logger.history[log_history_start:]

        # Check for any plugin load failures in recent log entries
        for e in recent_entries:
            msg = e.message
            if ("error" in msg.lower() or "failed" in msg.lower() or "cannot open" in msg.lower()) and msg not in issues:
                issues.append(msg)

        self._setLoadingProgress(90, "Restoring patchbay layout...")
        self.projectLoadingFinished(False, restore_positions=load_ok)

        if not load_ok:
            self.fIsProjectLoading = False
            self.fLastLoadedSource = None
            if issues:
                raw_log_str = "\n".join(
                    f"[{e.timestamp.strftime('%H:%M:%S')}] [{LEVEL_NAMES.get(e.level, 'INFO')}] [{e.tag}] {e.message}"
                    for e in recent_entries
                ) or (last_backend_err or "No detailed log entries.")
                summary_dlg = ProjectLoadSummaryDialog(self, load_source, issues=issues, raw_log=raw_log_str)
                summary_dlg.exec_()
            return False

        self.fIsProjectLoading = False
        self.fHasUnsavedChanges = False
        self.fLoadingBridgePlugins = None
        try:
            from carla_backend import PLUGIN_HAS_CUSTOM_UI
            self.fBridgePlugins = [
                index for index, pitem in enumerate(self.fPluginList)
                if pitem is not None and (self.host.get_plugin_info(index)["hints"] & PLUGIN_HAS_CUSTOM_UI)
            ]
        except Exception:
            self.fBridgePlugins = []
        self.setProperWindowTitle()

        for pitem in self.fPluginList:
            if pitem is None:
                continue
            widget = pitem.getWidget()
            if widget is not None and hasattr(widget, "refreshState"):
                widget.refreshState()

        return True

    def loadProjectLater(self, filename, source_override=None):
        self.fProjectFilename = QFileInfo(filename).absoluteFilePath()
        self.fProjectSourceOverride = source_override
        self.setProperWindowTitle()
        QTimer.singleShot(1, self.slot_loadProjectNow)

    def saveProjectNow(self):
        if not self.fProjectFilename:
            return qCritical("ERROR: saving project without filename set")

        backend_save_target, _is_temp = storage_manager.prepare_for_backend_save(self.fProjectFilename)

        if not self.host.save_project(backend_save_target):
            CustomMessageBox(
                self,
                QMessageBox.Critical,
                self.tr("Error"),
                self.tr("Failed to save project"),
                self.host.get_last_error(),
                QMessageBox.Ok,
                QMessageBox.Ok,
            )
            return

        positions = patchcanvas.saveGroupPositions() if self.fWithCanvas else []

        extra_meta = {}
        is_split = hasattr(self, "tabSplit") and self.ui.tabWidget.indexOf(self.tabSplit) == self.ui.tabWidget.currentIndex()
        extra_meta["split_view_enabled"] = is_split
        if hasattr(self, "splitter"):
            extra_meta["split_view_sizes"] = self.splitter.sizes()
        if self.fWithCanvas:
            extra_meta["patchbay_containers"] = patchcanvas.saveContainers()
        extra_meta["bridge_plugins"] = list(getattr(self, "fBridgePlugins", []))

        saved = storage_manager.finalize_from_backend_save(
            self.fProjectFilename, backend_save_target, positions, extra_metadata=extra_meta
        ) is not False

        if not saved:
            CustomMessageBox(
                self,
                QMessageBox.Critical,
                self.tr("Error"),
                self.tr("Failed to save project"),
                self.host.get_last_error() or self.tr("The project file could not be written to disk."),
                QMessageBox.Ok,
                QMessageBox.Ok,
            )
            return

        # Clean manual save succeeded: prune outstanding autosaves for this project
        if hasattr(self, "fSessionManager") and self.fSessionManager is not None:
            self.fSessionManager.prune_all_autosaves_on_manual_save(self.fProjectFilename)

        self.fHasUnsavedChanges = False
        self.setProperWindowTitle()
        self.addRecentProject(self.fProjectFilename)

    def projectLoadingStarted(self, filename=""):
        self.ui.rack.setEnabled(False)
        # keep the canvas visible and pannable, but not editable
        self.ui.graphicsView.setEnabled(True)
        if hasattr(self.ui.graphicsView, "setInteractive"):
            self.ui.graphicsView.setInteractive(False)
        if self.ui.listWidget is not None:
            # keep painting during load so rows appear in place instead of all at the end
            self.ui.listWidget.setUpdatesEnabled(True)
            self.ui.listWidget.blockSignals(True)

        if not hasattr(self, "fLoadingDialog") or self.fLoadingDialog is None:
            try:
                fn = filename or getattr(self, "fProjectFilename", "")
                self.fLoadingDialog = InlineLoadingBanner(self.ui.centralwidget, fn)
                layout = self.ui.centralwidget.layout()
                if layout is not None:
                    layout.insertWidget(0, self.fLoadingDialog)
                self.fLoadingDialog.show()
                QApplication.processEvents()
            except Exception:
                self.fLoadingDialog = None

    def _dismissLoadingDialog(self):
        if getattr(self, "fLoadingDialog", None) is not None:
            try:
                if hasattr(self.fLoadingDialog, "dismiss"):
                    self.fLoadingDialog.dismiss(500)
                else:
                    self.fLoadingDialog.close()
                    self.fLoadingDialog.deleteLater()
            except Exception:
                pass
            self.fLoadingDialog = None

    def _setLoadingProgress(self, percent, detail=None):
        dialog = getattr(self, "fLoadingDialog", None)
        if dialog is not None and hasattr(dialog, "setProgress"):
            dialog.setProgress(percent, detail)

    def projectLoadingFinished(self, refreshCanvas, restore_positions=True):
        if self.ui.listWidget is not None:
            self.ui.listWidget.setUpdatesEnabled(True)
            self.ui.listWidget.blockSignals(False)
            self.ui.listWidget.doItemsLayout()
            self.ui.listWidget.scrollToTop()

        self.ui.rack.setEnabled(True)
        self.ui.graphicsView.setEnabled(True)
        if hasattr(self.ui.graphicsView, "setInteractive"):
            self.ui.graphicsView.setInteractive(True)

        # Restore the canvas before dismissing the dialog, so 100% means "done" and not
        # "now reconnecting every node".
        if restore_positions and self.fCustomStopAction != self.CUSTOM_ACTION_APP_CLOSE and self.fWithCanvas:
            positions_loaded = False
            source_for_positions = getattr(self, "fLastLoadedSource", None) or self.fProjectFilename
            if self.fProjectFilename and os.path.exists(self.fProjectFilename):
                self.addRecentProject(self.fProjectFilename)

            if source_for_positions and os.path.exists(source_for_positions):
                self._setLoadingProgress(93, "Restoring node positions...")
                positions_loaded = self.loadCanvasGroupPositionsFromProject(source_for_positions)

            if (
                not positions_loaded
                and refreshCanvas
                and not self.loadExternalCanvasGroupPositionsIfNeeded(source_for_positions)
            ):
                QTimer.singleShot(1, self.slot_canvasRefresh)

            self.fLastLoadedSource = None

        # The engine sends plugin cables a moment after the plugins themselves, so give the
        # pre-wired shells time to bind before dropping anything unclaimed.
        QTimer.singleShot(1200, self._finalizeShellsAfterLoad)
        self._revealAllGhostHidden()
        patchcanvas.clearGhosts()
        patchcanvas.clearGhostCables()
        self._dismissLoadingDialog()

    def _finalizeShellsAfterLoad(self):
        try:
            patchcanvas.finalizeShellConnections()
            patchcanvas.finalizeShells()
            patchcanvas.auditGroupAABBs()
            patchcanvas.auditContainerAABBs()
        except Exception as e:
            logger.warning("CANVAS", f"finalizeShellsAfterLoad failed: {e}")

    def loadCanvasGroupPositionsFromProject(self, filename):
        if not filename or not os.path.exists(filename):
            return False

        try:
            data_list = storage_manager.load_canvas_positions(filename)
            if not data_list:
                return False

            patchcanvas.restoreGroupPositions(data_list)
            self._setLoadingProgress(94, "Restoring node positions...")

            # Restore layout containers (VBox, HBox, Grid)
            containers_data = getattr(data_list, "patchbay_containers", None)
            logger.info("CANVAS", f"loadCanvasGroupPositionsFromProject: containers_data count={len(containers_data) if containers_data else 0}")
            if containers_data:
                patchcanvas.loadContainers(containers_data)
                self._setLoadingProgress(96, "Restoring containers...")
                # Also schedule a deferred sweep in case PipeWire / external clients are still arriving
                QTimer.singleShot(150, lambda: patchcanvas.loadContainers(containers_data))

            # Auto-recenter legacy saves that do NOT have infinite_canvas == True
            is_infinite = getattr(data_list, "infinite_canvas", False)
            if not is_infinite:
                patchcanvas.centerGraphInCanvas()

            # Restore side-by-side view layout if persisted
            split_enabled = getattr(data_list, "split_view_enabled", None)
            split_sizes = getattr(data_list, "split_view_sizes", None)
            if split_enabled is not None:
                self._setLoadingProgress(97, "Restoring layout...")
                self.slot_toggleSideBySideView(bool(split_enabled), refresh=False)
                if split_sizes and hasattr(self, "splitter"):
                    self.splitter.setSizes(split_sizes)

            # Update context toolbar state if visible
            if hasattr(self, "canvasFilter") and hasattr(self.canvasFilter, "contextToolBar"):
                self.canvasFilter.contextToolBar.updateSelection()

            self._setLoadingProgress(99, "Finishing up...")
            return True
        except Exception as e:
            logger.warning("CANVAS", f"Failed to load canvas positions from project: {e}")
            return False

    def loadExternalCanvasGroupPositionsIfNeeded(self, filename):
        # Which projects keep positions in a sidecar file is decided by the save manager.
        extrafile = storage_manager.sidecar_positions_path(filename)
        if not extrafile:
            return False

        with open(extrafile, "r") as fh:
            try:
                canvasdata = json.load(fh)["canvas"]
            except Exception:
                return False

        log_carla("NOTICE: loading old-style canvas group positions via legacy json file", level="debug")
        patchcanvas.restoreGroupPositions(canvasdata)
        QTimer.singleShot(1, self.slot_canvasRefresh)
        return True

    # --------------------------------------------------------------------------------------------------------
    # Recent Projects

    def addRecentProject(self, filename):
        if not filename or not storage_manager.is_project_file(filename):
            return
        absPath = os.path.abspath(filename)
        if absPath in self.fRecentProjects:
            self.fRecentProjects.remove(absPath)
        self.fRecentProjects.insert(0, absPath)
        self.fRecentProjects = self.fRecentProjects[:10]
        self.updateRecentProjectsMenu()

    def updateRecentProjectsMenu(self):
        for act in self.fRecentProjectActions:
            self.ui.menu_File.removeAction(act)
        self.fRecentProjectActions = []

        valid_recents = [f for f in self.fRecentProjects if os.path.exists(f)]
        if not valid_recents:
            return

        for path in valid_recents:
            act = QAction(os.path.basename(path), self)
            act.setToolTip(path)
            act.setStatusTip(path)
            act.triggered.connect(
                lambda checked=False, p=path: self.loadRecentProject(p)
            )
            self.ui.menu_File.insertAction(self.ui.act_file_save, act)
            self.fRecentProjectActions.append(act)

        sep = self.ui.menu_File.insertSeparator(self.ui.act_file_save)
        self.fRecentProjectActions.append(sep)

    def loadRecentProject(self, filename):
        if not os.path.exists(filename):
            CustomMessageBox(
                self,
                QMessageBox.Critical,
                self.tr("Error"),
                self.tr("File does not exist"),
                filename,
                QMessageBox.Ok,
                QMessageBox.Ok,
            )
            return

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

        # Check for newer autosave recovery
        if hasattr(self, "fSessionManager") and self.fSessionManager is not None:
            newer_autosave = self.fSessionManager.check_newer_autosave(filename)
            if newer_autosave:
                mtime_str = datetime.fromtimestamp(os.path.getmtime(newer_autosave)).strftime("%Y-%m-%d %H:%M:%S")
                rec_ask = QMessageBox.question(
                    self,
                    self.tr("Autosave Recovery Detected"),
                    self.tr(
                        f"A newer autosave exists from {mtime_str} for this project.\n\nWould you like to recover the autosaved session instead?"
                    ),
                    QMessageBox.Yes | QMessageBox.No,
                    QMessageBox.Yes,
                )
                if rec_ask == QMessageBox.Yes:
                    filename = newer_autosave

        self.pluginRemoveAll()
        self.loadProjectLater(filename)

    def checkRecentOnStartup(self):
        if self.fProjectFilename or self.host.isControl or self.host.isPlugin:
            if not self.host.isControl:
                self.slot_engineStart()
            return

        recent_file = None
        for path in self.fRecentProjects:
            if os.path.exists(path):
                recent_file = path
                break

        if recent_file:
            recovery_source = None
            recovery_mtime = None
            if hasattr(self, "fSessionManager") and self.fSessionManager is not None:
                newer_autosave = self.fSessionManager.check_newer_autosave(recent_file)
                if newer_autosave:
                    recovery_source = newer_autosave
                    try:
                        recovery_mtime = os.path.getmtime(newer_autosave)
                    except OSError:
                        recovery_mtime = None

            is_autoload = getattr(gCarla, "autoload_lastsave", False) or QSafeSettings().value("Main/AutoloadLastSave", False, bool)
            if is_autoload:
                self.loadProjectLater(recent_file, source_override=recovery_source)
                return

            def _on_recent_load():
                # Recovered autosaves are loaded as the last-saved project: content comes from
                # the autosave, but the name/path stays the real project so saving writes there.
                self.loadProjectLater(recent_file, source_override=recovery_source)

            def _on_recent_skip():
                self.fLoadingDialog = None
                if not self.host.isControl:
                    self.slot_engineStart()
                    if self.fWithCanvas:
                        QTimer.singleShot(600, self.slot_canvasArrange)

            offer_detail = None
            if recovery_source:
                if recovery_mtime is not None:
                    mtime_str = datetime.fromtimestamp(recovery_mtime).strftime("%Y-%m-%d %H:%M:%S")
                else:
                    mtime_str = self.tr("an unknown time")
                offer_detail = self.tr(
                    f"A newer autosave from {mtime_str} was found for this project.\n\n"
                    f"Recovering restores the autosaved session but keeps the last-saved name and path "
                    f"('{os.path.basename(recent_file)}')."
                )

            self.fLoadingDialog = ProjectLoadingDialog(
                self.fParentOrSelf,
                recent_file,
                offer_mode=True,
                recover_mode=bool(recovery_source),
                offer_detail=offer_detail,
                on_load_accepted=_on_recent_load,
                on_load_declined=_on_recent_skip,
            )
            self.fLoadingDialog.show()
            return

        # Not loading recent: start engine and auto-arrange canvas
        if not self.host.isControl:
            self.slot_engineStart()
            if self.fWithCanvas:
                QTimer.singleShot(600, self.slot_canvasArrange)

    # --------------------------------------------------------------------------------------------------------
    # Files (menu actions)

    @pyqtSlot()
    def slot_fileNew(self):
        if (
            self.fPluginCount > 0
            and QMessageBox.question(
                self,
                self.tr("New File"),
                self.tr(
                    "Plugins that are currently loaded will be removed. Are you sure?"
                ),
                QMessageBox.Yes | QMessageBox.No,
            )
            == QMessageBox.No
        ):
            return

        self.pluginRemoveAll()
        self.fProjectFilename = ""
        self.setProperWindowTitle()
        self.host.clear_project_filename()

    @pyqtSlot()
    def slot_fileOpen(self):
        fileFilter = storage_manager.open_filter()
        filename, ok = QFileDialog.getOpenFileName(
            self,
            self.tr("Open Carla Project File"),
            self.fSavedSettings[CARLA_KEY_MAIN_PROJECT_FOLDER],
            filter=fileFilter,
        )

        if not filename:
            return

        # Check for newer autosave recovery
        load_source = filename
        if hasattr(self, "fSessionManager") and self.fSessionManager is not None:
            newer_autosave = self.fSessionManager.check_newer_autosave(filename)
            if newer_autosave:
                mtime_str = datetime.fromtimestamp(os.path.getmtime(newer_autosave)).strftime("%Y-%m-%d %H:%M:%S")
                rec_ask = QMessageBox.question(
                    self,
                    self.tr("Autosave Recovery Detected"),
                    self.tr(
                        f"A newer autosave exists from {mtime_str} for this project.\n\nWould you like to recover the autosaved session instead?"
                    ),
                    QMessageBox.Yes | QMessageBox.No,
                    QMessageBox.Yes,
                )
                if rec_ask == QMessageBox.Yes:
                    load_source = newer_autosave

        newFile = True

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
            newFile = ask == QMessageBox.Yes

        if newFile:
            self.pluginRemoveAll()
            self.fProjectFilename = filename
            self.setProperWindowTitle()
            if not self.loadProjectNow(source_override=load_source):
                # Rack is already empty and the new file did not load: start clean rather than
                # keeping a filename that cannot be read (a later save would overwrite it).
                self.fProjectFilename = ""
                self.setProperWindowTitle()
        else:
            filenameOld = self.fProjectFilename
            self.fProjectFilename = filename
            self.loadProjectNow(source_override=load_source)
            self.fProjectFilename = filenameOld

    @pyqtSlot()
    def slot_fileSave(self, *args, **kwargs):
        saveAs = kwargs.get("saveAs", False)
        if self.fProjectFilename and not saveAs:
            return self.saveProjectNow()

        fileFilter = storage_manager.save_filter()
        selected_filter = ""
        filename, selected_filter = QFileDialog.getSaveFileName(
            self,
            self.tr("Save Carla Project File"),
            self.fSavedSettings[CARLA_KEY_MAIN_PROJECT_FOLDER],
            filter=fileFilter,
        )

        if not filename:
            return

        # The chosen format travels as a tag; the save manager alone decides the extension.
        chosen_tag = storage_manager.tag_from_filter(selected_filter)
        filename = storage_manager.ensure_extension(filename, tag=chosen_tag)

        if self.fProjectFilename != filename:
            self.fProjectFilename = filename
            self.setProperWindowTitle()

        self.saveProjectNow()
        self.ui.act_file_save.setEnabled(True)

    @pyqtSlot()
    def slot_fileSaveAs(self, *args, **kwargs):
        self.slot_fileSave(saveAs=True)

    @pyqtSlot()
    def slot_loadProjectNow(self):
        source_override = getattr(self, "fProjectSourceOverride", None)
        self.fProjectSourceOverride = None
        if not self.loadProjectNow(source_override=source_override):
            # Keep the app honest about an empty session instead of saving over the unreadable file.
            self.fProjectFilename = ""
            self.setProperWindowTitle()
        if self.fProjectFilename and os.path.exists(self.fProjectFilename):
            self.ui.act_file_save.setEnabled(True)

    # --------------------------------------------------------------------------------------------------------
    # Engine (menu actions)

    @pyqtSlot()
    def slot_engineStart(self):
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

    # --------------------------------------------------------------------------------------------------------
    # Engine (host callbacks)

    @pyqtSlot(int, int, int, int, float, str)
    def slot_handleEngineStartedCallback(
        self,
        pluginCount,
        processMode,
        transportMode,
        bufferSize,
        sampleRate,
        driverName,
    ):
        self.ui.menu_PluginMacros.setEnabled(True)
        self.ui.menu_Canvas.setEnabled(True)
        self.ui.w_transport.setEnabled(True)

        self.ui.act_canvas_show_internal.blockSignals(True)
        self.ui.act_canvas_show_external.blockSignals(True)

        if processMode == ENGINE_PROCESS_MODE_PATCHBAY and not self.host.isPlugin:
            settings = QSafeSettings("falkTX", "Carla2")
            show_external = settings.value(
                CARLA_KEY_CANVAS_SHOW_EXTERNAL,
                CARLA_DEFAULT_CANVAS_SHOW_EXTERNAL,
                bool,
            )
            self.ui.act_canvas_show_internal.setChecked(not show_external)
            self.ui.act_canvas_show_internal.setVisible(True)
            self.ui.act_canvas_show_external.setChecked(show_external)
            self.ui.act_canvas_show_external.setVisible(True)
            self.fExternalPatchbay = bool(show_external)
        else:
            self.ui.act_canvas_show_internal.setChecked(False)
            self.ui.act_canvas_show_internal.setVisible(False)
            self.ui.act_canvas_show_external.setChecked(True)
            self.ui.act_canvas_show_external.setVisible(False)
            self.fExternalPatchbay = not self.host.isPlugin

        self.ui.act_canvas_show_internal.blockSignals(False)
        self.ui.act_canvas_show_external.blockSignals(False)

        if not (self.host.isControl or self.host.isPlugin):
            self.ui.act_file_save.setEnabled(True)
            self.ui.act_engine_start.setEnabled(False)
            self.ui.act_engine_stop.setEnabled(True)

        if not self.host.isPlugin:
            self.enableTransport(transportMode != ENGINE_TRANSPORT_MODE_DISABLED)

        if self.host.isPlugin or not self.fSessionManagerName:
            self.ui.act_file_open.setEnabled(True)
            self.ui.act_file_save_as.setEnabled(True)

        self.ui.cb_transport_jack.setChecked(
            transportMode == ENGINE_TRANSPORT_MODE_JACK
        )
        self.ui.cb_transport_jack.setEnabled(
            driverName == "JACK" and processMode != ENGINE_PROCESS_MODE_MULTIPLE_CLIENTS
        )

        if self.ui.cb_transport_link.isEnabled():
            self.ui.cb_transport_link.setChecked(":link:" in self.host.transportExtra)

        self.updateBufferSize(bufferSize)
        self.updateSampleRate(int(sampleRate))
        self.refreshRuntimeInfo(0.0, 0)
        self.startTimers()

        self.ui.text_logs.appendPlainText("======= Engine started ========")
        self.ui.text_logs.appendPlainText("Carla engine started, details:")
        self.ui.text_logs.appendPlainText("  Driver name:  %s" % driverName)
        self.ui.text_logs.appendPlainText("  Sample rate:  %i" % int(sampleRate))
        self.ui.text_logs.appendPlainText(
            "  Process mode: %s" % processMode2Str(processMode)
        )

    @pyqtSlot()
    def slot_handleEngineStoppedCallback(self):
        self.ui.text_logs.appendPlainText("======= Engine stopped ========")

        if self.fWithCanvas:
            patchcanvas.clear()

        self.killTimers()

        # just in case
        self.removeAllPlugins()
        self.refreshRuntimeInfo(0.0, 0)

        self.ui.menu_PluginMacros.setEnabled(False)
        self.ui.menu_Canvas.setEnabled(False)
        self.ui.w_transport.setEnabled(False)

        if not (self.host.isControl or self.host.isPlugin):
            self.ui.act_engine_start.setEnabled(True)
            self.ui.act_engine_stop.setEnabled(False)

        if not self.host.isPlugin:
            self.ui.act_file_open.setEnabled(True)
            self.ui.act_file_save.setEnabled(True)
            self.ui.act_file_save_as.setEnabled(True)

    @pyqtSlot(int, str)
    def slot_handleTransportModeChangedCallback(self, transportMode, transportExtra):
        self.enableTransport(transportMode != ENGINE_TRANSPORT_MODE_DISABLED)

        self.ui.cb_transport_jack.setChecked(
            transportMode == ENGINE_TRANSPORT_MODE_JACK
        )
        self.ui.cb_transport_link.setChecked(":link:" in transportExtra)

    @pyqtSlot(int)
    def slot_handleBufferSizeChangedCallback(self, newBufferSize):
        self.updateBufferSize(newBufferSize)

    @pyqtSlot(float)
    def slot_handleSampleRateChangedCallback(self, newSampleRate):
        self.updateSampleRate(int(newSampleRate))

    @pyqtSlot(int, bool, str)
    def slot_handleCancelableActionCallback(self, pluginId, started, action):
        if started:
            if not hasattr(self, "fLoadingDialog") or self.fLoadingDialog is None:
                fn = getattr(self, "fProjectFilename", "")
                self.fLoadingDialog = ProjectLoadingDialog(self.fParentOrSelf, fn)
                self.fLoadingDialog.show()
            if action:
                self.fLoadingDialog.setDetail(action)
            QApplication.processEvents()
        else:
            if hasattr(self, "fLoadingDialog") and self.fLoadingDialog is not None:
                try:
                    if hasattr(self.fLoadingDialog, "dismiss"):
                        self.fLoadingDialog.dismiss(500)
                    else:
                        self.fLoadingDialog.close()
                        self.fLoadingDialog.deleteLater()
                except Exception:
                    pass
                self.fLoadingDialog = None

    @pyqtSlot()
    def slot_canlableActionBoxClicked(self):
        self.host.cancel_engine_action()

    @pyqtSlot()
    def slot_handleProjectLoadFinishedCallback(self):
        self.fIsProjectLoading = False
        self.projectLoadingFinished(False)

        # Synchronize active state, button styles, labels, parameters, and colors across all plugin widgets
        for pluginId, pitem in enumerate(self.fPluginList):
            if pitem is None:
                continue
            widget = pitem.getWidget()
            if widget is not None and hasattr(widget, "refreshState"):
                widget.refreshState()

            # Ensure saved CarlaColor is synchronized between rack item and patchbay canvas node
            saved_color = self.host.get_custom_data_value(
                pluginId, CUSTOM_DATA_TYPE_PROPERTY, "CarlaColor"
            )
            color_tup = None
            hex_col = None
            if saved_color:
                try:
                    parts = tuple(int(i) for i in saved_color.split(";", 3))
                    if parts != (255, 255, 255):
                        color_tup = parts
                        hex_col = f"#{parts[0]:02x}{parts[1]:02x}{parts[2]:02x}"
                except Exception:
                    pass

            if color_tup is not None and pitem.fOptions.get("color") != color_tup:
                pitem.recreateWidget(newColor=color_tup)

            if self.fWithCanvas and hex_col:
                for group in patchcanvas.canvas.group_list:
                    if getattr(group, "plugin_id", -1) == pluginId:
                        for w in getattr(group, "widgets", []):
                            if w is not None:
                                w.setCustomColor(hex_col, notify=False)
                        break

    # --------------------------------------------------------------------------------------------------------
    # Plugins

    def removeAllPlugins(self):
        self.ui.act_plugin_remove_all.setEnabled(False)
        patchcanvas.handleAllPluginsRemoved()

        while self.ui.listWidget.takeItem(0):
            pass

        self.clearSideStuff()

        for pitem in self.fPluginList:
            if pitem is None:
                continue

            pitem.close()
            del pitem

        self.fPluginCount = 0
        self.fPluginList = []

    # --------------------------------------------------------------------------------------------------------
    # Plugins (menu actions)

    def showAddPluginDialog(self):
        # TODO self.fHasLoadedLv2Plugins
        if self.fPluginListDialog is None:
            hostSettings = {
                "showPluginBridges": self.fSavedSettings[
                    CARLA_KEY_EXPERIMENTAL_PLUGIN_BRIDGES
                ],
                "showWineBridges": self.fSavedSettings[
                    CARLA_KEY_EXPERIMENTAL_WINE_BRIDGES
                ],
                "useSystemIcons": self.fSavedSettings[CARLA_KEY_MAIN_SYSTEM_ICONS],
                "wineAutoPrefix": self.fSavedSettings[CARLA_KEY_WINE_AUTO_PREFIX],
                "wineExecutable": self.fSavedSettings[CARLA_KEY_WINE_EXECUTABLE],
                "wineFallbackPrefix": self.fSavedSettings[
                    CARLA_KEY_WINE_FALLBACK_PREFIX
                ],
            }
            self.fPluginListDialog = d = gCarla.felib.createPluginListDialog(
                self.fParentOrSelf, hostSettings
            )
            if hasattr(d, "pluginAddRequested"):
                d.pluginAddRequested.connect(self.loadPluginFromInfo)

            gCarla.felib.setPluginListDialogPath(
                d, PLUGIN_LADSPA, self.fSavedSettings[CARLA_KEY_PATHS_LADSPA]
            )
            gCarla.felib.setPluginListDialogPath(
                d, PLUGIN_DSSI, self.fSavedSettings[CARLA_KEY_PATHS_DSSI]
            )
            gCarla.felib.setPluginListDialogPath(
                d, PLUGIN_LV2, self.fSavedSettings[CARLA_KEY_PATHS_LV2]
            )
            gCarla.felib.setPluginListDialogPath(
                d, PLUGIN_VST2, self.fSavedSettings[CARLA_KEY_PATHS_VST2]
            )
            gCarla.felib.setPluginListDialogPath(
                d, PLUGIN_VST3, self.fSavedSettings[CARLA_KEY_PATHS_VST3]
            )
            gCarla.felib.setPluginListDialogPath(
                d, PLUGIN_SF2, self.fSavedSettings[CARLA_KEY_PATHS_SF2]
            )
            gCarla.felib.setPluginListDialogPath(
                d, PLUGIN_SFZ, self.fSavedSettings[CARLA_KEY_PATHS_SFZ]
            )
            gCarla.felib.setPluginListDialogPath(
                d, PLUGIN_JSFX, self.fSavedSettings[CARLA_KEY_PATHS_JSFX]
            )
            gCarla.felib.setPluginListDialogPath(
                d, PLUGIN_CLAP, self.fSavedSettings[CARLA_KEY_PATHS_CLAP]
            )

        self._lastLoadedFromDialog = False
        ret = gCarla.felib.execPluginListDialog(self.fPluginListDialog)

        if not ret or getattr(self, "_lastLoadedFromDialog", False):
            return None

        if not self.host.is_engine_running():
            QMessageBox.warning(
                self,
                self.tr("Warning"),
                self.tr("Cannot add new plugins while engine is stopped"),
            )
            return

        btype = ret["build"]
        ptype = ret["type"]
        filename = ret["filename"]
        label = ret["label"]
        uniqueId = ret["uniqueId"]
        extraPtr = None

        return (btype, ptype, filename, label, uniqueId, extraPtr)

    def showAddJackAppDialog(self):
        ret = gCarla.felib.createAndExecJackAppDialog(
            self.fParentOrSelf, self.fProjectFilename
        )

        if not ret:
            return

        if not self.host.is_engine_running():
            QMessageBox.warning(
                self,
                self.tr("Warning"),
                self.tr("Cannot add new plugins while engine is stopped"),
            )
            return

        return ret

    @pyqtSlot()
    def slot_favoritePluginAdd(self):
        plugin = self.sender().data()

        if plugin is None:
            return

        self._preparePluginAddCanvasPos()
        if not self.host.add_plugin(
            plugin["build"],
            plugin["type"],
            plugin["filename"],
            None,
            plugin["label"],
            plugin["uniqueId"],
            None,
            PLUGIN_OPTIONS_NULL,
        ):
            # remove plugin from favorites
            try:
                self.fFavoritePlugins.remove(plugin)
            except ValueError:
                pass
            else:
                settingsDBf = QSafeSettings("falkTX", "CarlaDatabase2")
                settingsDBf.setValue("PluginDatabase/Favorites", self.fFavoritePlugins)
                settingsDBf.sync()
                del settingsDBf

            CustomMessageBox(
                self,
                QMessageBox.Icon.Critical,
                self.tr("Error"),
                self.tr("Failed to load plugin"),
                self.host.get_last_error(),
                QMessageBox.StandardButton.Ok,
                QMessageBox.StandardButton.Ok,
            )

    def slot_showPluginActionsMenu(self, sceneX=None, sceneY=None):
        if sceneX is not None and sceneY is not None and (sceneX != 0 or sceneY != 0):
            self._targetPluginAddPos = QPointF(float(sceneX), float(sceneY))
        else:
            self._targetPluginAddPos = None

        menu = QMenu(self)

        menu.addSection("Plugins")
        menu.addAction(self.ui.act_plugin_add)

        if len(self.fFavoritePlugins) != 0:
            fmenu = QMenu("Add from favorites", self)
            for p in self.fFavoritePlugins:
                act = fmenu.addAction(p["name"])
                act.setData(p)
                act.triggered.connect(self.slot_favoritePluginAdd)
            menu.addMenu(fmenu)

        menu.addAction(self.ui.act_plugin_remove_all)

        menu.addSection("All plugins (macros)")
        menu.addAction(self.ui.act_plugins_enable)
        menu.addAction(self.ui.act_plugins_disable)
        menu.addSeparator()
        menu.addAction(self.ui.act_plugins_volume100)
        menu.addAction(self.ui.act_plugins_mute)
        menu.addSeparator()
        menu.addAction(self.ui.act_plugins_wet100)
        menu.addAction(self.ui.act_plugins_bypass)
        menu.addSeparator()
        menu.addAction(self.ui.act_plugins_center)
        menu.addSeparator()
        menu.addAction(self.ui.act_plugins_compact)
        menu.addAction(self.ui.act_plugins_expand)
        menu.addSeparator()

        arrangeMenu = QMenu("Arrange & Align", menu)
        act_auto_arrange = arrangeMenu.addAction("Auto-arrange All")
        act_auto_arrange.triggered.connect(self.slot_canvasArrange)
        arrangeMenu.addSeparator()

        act_align_h = arrangeMenu.addAction("Align Horizontally")
        act_align_h.triggered.connect(lambda: self._alignSelectedCanvasNodes("align_h"))

        act_align_v = arrangeMenu.addAction("Align Vertically")
        act_align_v.triggered.connect(lambda: self._alignSelectedCanvasNodes("align_v"))

        act_dist_h = arrangeMenu.addAction("Distribute Horizontally")
        act_dist_h.triggered.connect(lambda: self._alignSelectedCanvasNodes("distribute_h"))

        act_dist_v = arrangeMenu.addAction("Distribute Vertically")
        act_dist_v.triggered.connect(lambda: self._alignSelectedCanvasNodes("distribute_v"))

        arrangeMenu.addSeparator()
        act_move_aside = arrangeMenu.addAction("Move Aside Non-Connected Nodes")
        act_move_aside.triggered.connect(self._moveAsideNonConnectedNodes)

        num_sel = len(self.scene.selectedItems()) if hasattr(self, "scene") and self.scene else 0
        if num_sel < 2:
            act_align_h.setEnabled(False)
            act_align_v.setEnabled(False)
            act_dist_h.setEnabled(False)
            act_dist_v.setEnabled(False)

        menu.addMenu(arrangeMenu)

        selectMenu = QMenu("Select", menu)
        act_sel_all = selectMenu.addAction("Select All\tCtrl+A")
        act_sel_all.triggered.connect(self._selectAllCanvasNodes)
        act_desel = selectMenu.addAction("Deselect\tCtrl+D")
        act_desel.triggered.connect(self._deselectAllCanvasNodes)
        act_inv = selectMenu.addAction("Invert Selection\tCtrl+Shift+I")
        act_inv.triggered.connect(self._invertCanvasSelection)
        selectMenu.addSeparator()

        from patchcanvas.patchcanvas import getAvailableNodeTypes, selectNodesByType
        byTypeMenu = QMenu("By Type", selectMenu)
        for t_name in getAvailableNodeTypes():
            act_t = byTypeMenu.addAction(t_name)
            act_t.triggered.connect(lambda checked=False, t=t_name: (selectNodesByType(t), self.updateMiniCanvasLater()))
        selectMenu.addMenu(byTypeMenu)

        menu.addMenu(selectMenu)

        menu.exec_(QCursor.pos())

    def _selectAllCanvasNodes(self):
        from patchcanvas.patchcanvas import selectAllNodes
        selectAllNodes()
        self.updateMiniCanvasLater()

    def _deselectAllCanvasNodes(self):
        from patchcanvas.patchcanvas import deselectAllNodes
        deselectAllNodes()
        self.updateMiniCanvasLater()

    def _invertCanvasSelection(self):
        from patchcanvas.patchcanvas import invertNodeSelection
        invertNodeSelection()
        self.updateMiniCanvasLater()

    def _alignSelectedCanvasNodes(self, mode):
        from patchcanvas.patchcanvas import alignSelected
        alignSelected(mode)
        self.updateMiniCanvasLater()

    def _moveAsideNonConnectedNodes(self):
        from patchcanvas.patchcanvas import moveAsideNonConnectedNodes
        moveAsideNonConnectedNodes()
        self.updateMiniCanvasLater()

    def startStartupPluginScanner(self):
        try:
            from pluginlist.startup_scanner import getGlobalScanner
            scanner = getGlobalScanner()
            paths = {
                PLUGIN_LADSPA: self.fSavedSettings.get(CARLA_KEY_PATHS_LADSPA, ""),
                PLUGIN_DSSI: self.fSavedSettings.get(CARLA_KEY_PATHS_DSSI, ""),
                PLUGIN_LV2: self.fSavedSettings.get(CARLA_KEY_PATHS_LV2, ""),
                PLUGIN_VST2: self.fSavedSettings.get(CARLA_KEY_PATHS_VST2, ""),
                PLUGIN_VST3: self.fSavedSettings.get(CARLA_KEY_PATHS_VST3, ""),
                PLUGIN_CLAP: self.fSavedSettings.get(CARLA_KEY_PATHS_CLAP, ""),
                PLUGIN_JSFX: self.fSavedSettings.get(CARLA_KEY_PATHS_JSFX, ""),
                PLUGIN_SF2: self.fSavedSettings.get(CARLA_KEY_PATHS_SF2, ""),
                PLUGIN_SFZ: self.fSavedSettings.get(CARLA_KEY_PATHS_SFZ, ""),
            }
            scanner.configure(paths=paths)
            scanner.start()
        except Exception as exc:
            log_carla(f"HostWindow: startStartupPluginScanner failed: {exc}", level="debug")

    def _preparePluginAddCanvasPos(self):
        try:
            if getattr(self, "_targetPluginAddPos", None) is not None:
                patchcanvas.setInitialPos(self._targetPluginAddPos.x(), self._targetPluginAddPos.y())
                self._targetPluginAddPos = None
            elif hasattr(self.ui, "graphicsView"):
                vp = self.ui.graphicsView.viewport()
                if vp:
                    center_scene = self.ui.graphicsView.mapToScene(vp.rect().center())
                    patchcanvas.setInitialPos(center_scene.x(), center_scene.y())
        except Exception:
            pass

    def loadPluginFromData(self, btype, ptype, filename, label, uniqueId, extraPtr, options=PLUGIN_OPTIONS_NULL):
        self._preparePluginAddCanvasPos()
        # Auto-sandbox plugins that create their own GL/UI context and crash the host when
        # loaded in-process (e.g. Cardinal/VCV Rack GLX races), unless the user explicitly
        # picked a bridge mode in the Add Plugin dialog.
        if not (options & (PLUGIN_OPTION_USE_BRIDGE | PLUGIN_OPTION_AVOID_BRIDGE)):
            ident = f"{label or ''} {filename or ''}".lower()
            if "cardinal" in ident or "decentsampler" in ident:
                options |= PLUGIN_OPTION_USE_BRIDGE
        cursor = getattr(Qt, "WaitCursor", None) or getattr(getattr(Qt, "CursorShape", object), "WaitCursor", None)
        if cursor is not None:
            QApplication.setOverrideCursor(cursor)
        try:
            ok = self.host.add_plugin(
                btype, ptype, filename, None, label, uniqueId, extraPtr, options
            )
        finally:
            if cursor is not None:
                QApplication.restoreOverrideCursor()

        if not ok:
            CustomMessageBox(
                self,
                QMessageBox.Critical,
                self.tr("Error"),
                self.tr("Failed to load plugin"),
                self.host.get_last_error(),
                QMessageBox.Ok,
                QMessageBox.Ok,
            )
            return False
        return True

    def loadPluginFromInfo(self, info):
        self._lastLoadedFromDialog = True
        if not self.host.is_engine_running():
            QMessageBox.warning(
                self,
                self.tr("Warning"),
                self.tr("Cannot add new plugins while engine is stopped"),
            )
            return False

        btype = info["build"]
        ptype = info["type"]
        filename = info["filename"]
        label = info["label"]
        uniqueId = info["uniqueId"]
        extraPtr = None
        options = info.get("__bridgeOption", PLUGIN_OPTIONS_NULL) | PLUGIN_OPTIONS_NULL
        return self.loadPluginFromData(btype, ptype, filename, label, uniqueId, extraPtr, options)

    @pyqtSlot()
    def slot_pluginAdd(self):
        data = self.showAddPluginDialog()

        if data is None:
            return

        btype, ptype, filename, label, uniqueId, extraPtr = data
        self.loadPluginFromData(btype, ptype, filename, label, uniqueId, extraPtr)

    @pyqtSlot()
    def slot_confirmRemoveAll(self):
        if self.fPluginCount == 0:
            return

        if (
            QMessageBox.question(
                self,
                self.tr("Remove All"),
                self.tr("Are you sure you want to remove all plugins?"),
                QMessageBox.Yes | QMessageBox.No,
            )
            == QMessageBox.No
        ):
            return

        self.pluginRemoveAll()

    def pluginRemoveAll(self):
        if self.fPluginCount == 0:
            return

        self.fCurrentlyRemovingAllPlugins = True
        self.projectLoadingStarted()

        if not self.host.remove_all_plugins():
            self.projectLoadingFinished(True)
            self.fCurrentlyRemovingAllPlugins = False
            CustomMessageBox(
                self,
                QMessageBox.Warning,
                self.tr("Error"),
                self.tr("Operation failed"),
                self.host.get_last_error(),
                QMessageBox.Ok,
                QMessageBox.Ok,
            )

    @pyqtSlot()
    def slot_jackAppAdd(self):
        data = self.showAddJackAppDialog()

        if data is None:
            return

        if not data["command"]:
            CustomMessageBox(
                self,
                QMessageBox.Critical,
                self.tr("Error"),
                self.tr("Cannot add jack application"),
                self.tr("command is empty"),
                QMessageBox.Ok,
                QMessageBox.Ok,
            )
            return

        if not self.host.add_plugin(
            BINARY_NATIVE,
            PLUGIN_JACK,
            data["command"],
            data["name"],
            data["labelSetup"],
            0,
            None,
            PLUGIN_OPTIONS_NULL,
        ):
            CustomMessageBox(
                self,
                QMessageBox.Critical,
                self.tr("Error"),
                self.tr("Failed to load plugin"),
                self.host.get_last_error(),
                QMessageBox.Ok,
                QMessageBox.Ok,
            )

    # --------------------------------------------------------------------------------------------------------
    # Plugins (macros)

    @pyqtSlot()
    def slot_pluginsEnable(self):
        if not self.host.is_engine_running():
            return

        for pitem in self.fPluginList:
            if pitem is None:
                break

            pitem.getWidget().setActive(True, True, True)

    @pyqtSlot()
    def slot_pluginsDisable(self):
        if not self.host.is_engine_running():
            return

        for pitem in self.fPluginList:
            if pitem is None:
                break

            pitem.getWidget().setActive(False, True, True)

    @pyqtSlot()
    def slot_pluginsVolume100(self):
        if not self.host.is_engine_running():
            return

        for pitem in self.fPluginList:
            if pitem is None:
                break

            pitem.getWidget().setInternalParameter(PLUGIN_CAN_VOLUME, 1.0)

    @pyqtSlot()
    def slot_pluginsMute(self):
        if not self.host.is_engine_running():
            return

        for pitem in self.fPluginList:
            if pitem is None:
                break

            pitem.getWidget().setInternalParameter(PLUGIN_CAN_VOLUME, 0.0)

    @pyqtSlot()
    def slot_pluginsWet100(self):
        if not self.host.is_engine_running():
            return

        for pitem in self.fPluginList:
            if pitem is None:
                break

            pitem.getWidget().setInternalParameter(PLUGIN_CAN_DRYWET, 1.0)

    @pyqtSlot()
    def slot_pluginsBypass(self):
        if not self.host.is_engine_running():
            return

        for pitem in self.fPluginList:
            if pitem is None:
                break

            pitem.getWidget().setInternalParameter(PLUGIN_CAN_DRYWET, 0.0)

    @pyqtSlot()
    def slot_pluginsCenter(self):
        if not self.host.is_engine_running():
            return

        for pitem in self.fPluginList:
            if pitem is None:
                break

            pitem.getWidget().setInternalParameter(PARAMETER_BALANCE_LEFT, -1.0)
            pitem.getWidget().setInternalParameter(PARAMETER_BALANCE_RIGHT, 1.0)
            pitem.getWidget().setInternalParameter(PARAMETER_PANNING, 0.0)

    @pyqtSlot()
    def slot_pluginsCompact(self):
        for pitem in self.fPluginList:
            if pitem is None:
                break
            pitem.compact()

    @pyqtSlot()
    def slot_pluginsExpand(self):
        for pitem in self.fPluginList:
            if pitem is None:
                break
            pitem.expand()

    # --------------------------------------------------------------------------------------------------------
    # Plugins (host callbacks)

    @pyqtSlot(int, int, str)
    def slot_handlePluginAddedCallback(self, pluginId, pluginType, pluginName):
        log_carla(
            f"carla_host: slot_handlePluginAddedCallback id={pluginId}, type={pluginType}, name='{pluginName}'",
            level="debug"
        )

        if getattr(self, "fLoadingDialog", None) is not None:
            type_names = {
                PLUGIN_LV2: "LV2",
                PLUGIN_VST2: "VST2",
                PLUGIN_VST3: "VST3",
                PLUGIN_CLAP: "CLAP",
                PLUGIN_LADSPA: "LADSPA",
                PLUGIN_DSSI: "DSSI",
                PLUGIN_JSFX: "JSFX",
                PLUGIN_SF2: "SF2",
                PLUGIN_SFZ: "SFZ",
            }
            type_str = type_names.get(pluginType, "")
            suffix = f" [{type_str}]" if type_str else ""
            total = getattr(self, "fLoadingPluginTotal", 0)
            done = pluginId + 1
            if total > 0:
                percent = 8.0 + 82.0 * min(1.0, done / float(total))
                detail = f"Loading plugin {done}/{total}: {pluginName}{suffix}..."
            else:
                percent = min(90.0, 8.0 + done * 2.0)
                detail = f"Loading plugin: {pluginName}{suffix}..."
            self.fLoadingDialog.setProgress(percent, detail)

        while len(self.fPluginList) <= pluginId:
            self.fPluginList.append(None)

        pitem = self.fPluginList[pluginId]
        if pitem is not None:
            pitem.recreateWidget()
            return

        pitem = self.ui.listWidget.createItem(
            pluginId, self.fSavedSettings[CARLA_KEY_MAIN_CLASSIC_SKIN]
        )
        while len(self.fPluginList) <= pluginId:
            self.fPluginList.append(None)
        self.fPluginList[pluginId] = pitem
        self.fPluginCount = len([p for p in self.fPluginList if p is not None])

        self.ui.act_plugin_remove_all.setEnabled(self.fPluginCount > 0)

        if pluginType == PLUGIN_LV2:
            self.fHasLoadedLv2Plugins = True

    @pyqtSlot(int)
    def slot_handlePluginRemovedCallback(self, pluginId):
        if self.fWithCanvas:
            patchcanvas.handlePluginRemoved(pluginId)

        if pluginId in self.fSelectedPlugins:
            self.clearSideStuff()

        pitem = self.getPluginItem(pluginId)

        if pluginId < len(self.fPluginList):
            self.fPluginList[pluginId] = None

        if pitem is not None:
            row = self.ui.listWidget.row(pitem)
            if row >= 0:
                self.ui.listWidget.takeItem(row)
            pitem.close()
            del pitem

        while self.fPluginList and self.fPluginList[-1] is None:
            self.fPluginList.pop()

        self.fPluginCount = len([p for p in self.fPluginList if p is not None])

        if self.fPluginCount == 0:
            self.ui.act_plugin_remove_all.setEnabled(False)
            if self.fCurrentlyRemovingAllPlugins:
                self.fCurrentlyRemovingAllPlugins = False
                self.projectLoadingFinished(False)
            return

        self.ui.act_plugin_remove_all.setEnabled(True)

    # --------------------------------------------------------------------------------------------------------
    # Canvas

    def clearSideStuff(self):
        if self.fWithCanvas:
            self.scene.clearSelection()

        self.fSelectedPlugins = []

        self.ui.keyboard.allNotesOff(False)
        self.ui.scrollArea.setEnabled(False)

        self.fPeaksCleared = True
        self.ui.peak_in.displayMeter(1, 0.0, True)
        self.ui.peak_in.displayMeter(2, 0.0, True)
        self.ui.peak_out.displayMeter(1, 0.0, True)
        self.ui.peak_out.displayMeter(2, 0.0, True)

    def setupCanvas(self):
        pOptions = patchcanvas.options_t()
        pOptions.theme_name = self.fSavedSettings[CARLA_KEY_CANVAS_THEME]
        pOptions.auto_hide_groups = self.fSavedSettings[
            CARLA_KEY_CANVAS_AUTO_HIDE_GROUPS
        ]
        pOptions.auto_select_items = self.fSavedSettings[
            CARLA_KEY_CANVAS_AUTO_SELECT_ITEMS
        ]
        pOptions.use_bezier_lines = self.fSavedSettings[
            CARLA_KEY_CANVAS_USE_BEZIER_LINES
        ]
        pOptions.antialiasing = self.fSavedSettings[CARLA_KEY_CANVAS_ANTIALIASING]
        pOptions.inline_displays = self.fSavedSettings[CARLA_KEY_CANVAS_INLINE_DISPLAYS]
        pOptions.rounded_nodes = self.fSavedSettings.get(
            CARLA_KEY_CANVAS_ROUNDED_NODES, CARLA_DEFAULT_CANVAS_ROUNDED_NODES
        )
        pOptions.node_radius = self.fSavedSettings.get(
            CARLA_KEY_CANVAS_NODE_RADIUS, CARLA_DEFAULT_CANVAS_NODE_RADIUS
        )
        pOptions.node_min_width = self.fSavedSettings.get(
            CARLA_KEY_CANVAS_NODE_MIN_WIDTH, CARLA_DEFAULT_CANVAS_NODE_MIN_WIDTH
        )
        pOptions.line_style = self.fSavedSettings.get(
            CARLA_KEY_CANVAS_LINE_STYLE, CARLA_DEFAULT_CANVAS_LINE_STYLE
        )
        pOptions.line_stroke = self.fSavedSettings.get(
            CARLA_KEY_CANVAS_LINE_STROKE, CARLA_DEFAULT_CANVAS_LINE_STROKE
        )
        pOptions.line_opacity = self.fSavedSettings.get(
            CARLA_KEY_CANVAS_LINE_OPACITY, CARLA_DEFAULT_CANVAS_LINE_OPACITY
        )
        pOptions.arrange_style = self.fSavedSettings.get(
            CARLA_KEY_CANVAS_ARRANGE_STYLE, CARLA_DEFAULT_CANVAS_ARRANGE_STYLE
        )

        if self.fSavedSettings[CARLA_KEY_CANVAS_FANCY_EYE_CANDY]:
            pOptions.eyecandy = patchcanvas.EYECANDY_FULL
        elif self.fSavedSettings[CARLA_KEY_CANVAS_EYE_CANDY]:
            pOptions.eyecandy = patchcanvas.EYECANDY_SMALL
        else:
            pOptions.eyecandy = patchcanvas.EYECANDY_NONE

        pFeatures = patchcanvas.features_t()
        pFeatures.group_info = False
        pFeatures.group_rename = False
        pFeatures.port_info = False
        pFeatures.port_rename = False
        pFeatures.handle_group_pos = False

        patchcanvas.setOptions(pOptions)
        patchcanvas.setFeatures(pFeatures)
        patchcanvas.init("Carla2", self.scene, canvasCallback, False)

        tryCanvasSize = self.fSavedSettings[CARLA_KEY_CANVAS_SIZE].split("x")

        if (
            len(tryCanvasSize) == 2
            and tryCanvasSize[0].isdigit()
            and tryCanvasSize[1].isdigit()
        ):
            self.fCanvasWidth = int(tryCanvasSize[0])
            self.fCanvasHeight = int(tryCanvasSize[1])
        else:
            self.fCanvasWidth = CARLA_DEFAULT_CANVAS_SIZE_WIDTH
            self.fCanvasHeight = CARLA_DEFAULT_CANVAS_SIZE_HEIGHT

        patchcanvas.setCanvasSize(0, 0, self.fCanvasWidth, self.fCanvasHeight)
        patchcanvas.setInitialPos(self.fCanvasWidth / 2, self.fCanvasHeight / 2)
        self.ui.graphicsView.setSceneRect(0, 0, self.fCanvasWidth, self.fCanvasHeight)

        # Setup canvas viewport auto-scrolling & quick disconnect filter
        self.canvasFilter = CanvasViewportFilter(self, self.ui.graphicsView)

        self.ui.miniCanvasPreview.setViewTheme(
            patchcanvas.canvas.theme.canvas_bg,
            patchcanvas.canvas.theme.rubberband_brush.color(),
            patchcanvas.canvas.theme.rubberband_pen.color(),
        )
        self.ui.miniCanvasPreview.init(
            self.scene,
            self.fCanvasWidth,
            self.fCanvasHeight,
            self.fSavedSettings[CARLA_KEY_CUSTOM_PAINTING],
        )

        # Resolve minimap placement only after the preview is initialized.
        self._updateMiniCanvasPlacement()

        if (
            self.fSavedSettings[CARLA_KEY_CANVAS_ANTIALIASING]
            != patchcanvas.ANTIALIASING_NONE
        ):
            self.ui.graphicsView.setRenderHint(QPainter.Antialiasing, True)

            fullAA = (
                self.fSavedSettings[CARLA_KEY_CANVAS_ANTIALIASING]
                == patchcanvas.ANTIALIASING_FULL
            )
            self.ui.graphicsView.setRenderHint(QPainter.SmoothPixmapTransform, fullAA)
            self.ui.graphicsView.setRenderHint(QPainter.TextAntialiasing, fullAA)

            hq_aa_attr = getattr(QPainter.RenderHint, "HighQualityAntialiasing", getattr(QPainter, "HighQualityAntialiasing", None)) if hasattr(QPainter, "RenderHint") else getattr(QPainter, "HighQualityAntialiasing", None)
            if (
                self.fSavedSettings[CARLA_KEY_CANVAS_USE_OPENGL]
                and hasGL
                and hq_aa_attr is not None
            ):
                self.ui.graphicsView.setRenderHint(
                    hq_aa_attr,
                    self.fSavedSettings[CARLA_KEY_CANVAS_HQ_ANTIALIASING],
                )

        else:
            self.ui.graphicsView.setRenderHint(QPainter.Antialiasing, False)

        if self.fSavedSettings[CARLA_KEY_CANVAS_FULL_REPAINTS]:
            self.ui.graphicsView.setViewportUpdateMode(QGraphicsView.FullViewportUpdate)
        else:
            smart_mode = getattr(QGraphicsView, "SmartViewportUpdate", None)
            if smart_mode is None and hasattr(QGraphicsView, "ViewportUpdateMode"):
                smart_mode = getattr(QGraphicsView.ViewportUpdateMode, "SmartViewportUpdate", None)
            if smart_mode is not None:
                self.ui.graphicsView.setViewportUpdateMode(smart_mode)
            else:
                self.ui.graphicsView.setViewportUpdateMode(
                    QGraphicsView.MinimalViewportUpdate
                )

        # Store painter state is not needed here and costs us fairly big, so skip it.
        try:
            self.ui.graphicsView.setOptimizationFlag(
                QGraphicsView.DontSavePainterState, True
            )
        except Exception:
            pass

        # Do not inflate update rects for antialiasing; keeps scroll repaints small.
        try:
            self.ui.graphicsView.setOptimizationFlag(
                QGraphicsView.DontAdjustForAntialiasing, True
            )
        except Exception:
            pass

        # The scene paints an opaque background, so tell Qt not to erase first.
        try:
            self.ui.graphicsView.viewport().setAttribute(Qt.WA_OpaquePaintEvent, True)
        except Exception:
            pass

        # Report which viewport we ended up with, so it is obvious from the log
        # whether the patchbay is GPU-accelerated or software-rendered.
        try:
            vp = self.ui.graphicsView.viewport()
            is_gl = "GL" in type(vp).__name__.upper()
            logger.info(
                "CANVAS",
                "Patchbay viewport: %s (%s), update mode %s, UseOpenGL setting=%s, GL available=%s"
                % (
                    "OpenGL" if is_gl else "Software raster",
                    type(vp).__name__,
                    self.ui.graphicsView.viewportUpdateMode(),
                    self.fSavedSettings.get(CARLA_KEY_CANVAS_USE_OPENGL),
                    hasGL,
                ),
            )
        except Exception:
            pass

        # The grid background is static between zoom changes, so let Qt cache it
        # instead of repainting every dot on each drag/pan frame.
        try:
            cache_bg = getattr(QGraphicsView, "CacheBackground", None)
            if cache_bg is None and hasattr(QGraphicsView, "CacheModeFlag"):
                cache_bg = getattr(QGraphicsView.CacheModeFlag, "CacheBackground", None)
            if cache_bg is not None:
                self.ui.graphicsView.setCacheMode(cache_bg)
        except Exception:
            pass

    def updateCanvasInitialPos(self):
        x = self.ui.graphicsView.horizontalScrollBar().value() + self.width() / 4
        y = self.ui.graphicsView.verticalScrollBar().value() + self.height() / 4
        patchcanvas.setInitialPos(x, y)

    def updateMiniCanvasLater(self):
        if hasattr(self, "_miniCanvasTimer"):
            self._miniCanvasTimer.start(self.fMiniCanvasUpdateTimeout)
        else:
            self._doUpdateMiniCanvas()

    def _doUpdateMiniCanvas(self):
        if self._isModernMiniCanvasMode():
            self._expandSceneRectForMinimap()
            if hasattr(self.ui, "modernMiniCanvas") and self.ui.modernMiniCanvas is not None:
                self.ui.modernMiniCanvas.update()
            return
        if hasattr(self.ui, "miniCanvasPreview") and self.ui.miniCanvasPreview is not None:
            self.ui.miniCanvasPreview.update()

    # --------------------------------------------------------------------------------------------------------
    # Canvas (menu actions)

    @pyqtSlot()
    def slot_canvasShowInternal(self):
        self.fExternalPatchbay = False
        QSafeSettings("falkTX", "Carla2").setValue(CARLA_KEY_CANVAS_SHOW_EXTERNAL, False)
        self.ui.act_canvas_show_internal.blockSignals(True)
        self.ui.act_canvas_show_external.blockSignals(True)
        self.ui.act_canvas_show_internal.setChecked(True)
        self.ui.act_canvas_show_external.setChecked(False)
        self.ui.act_canvas_show_internal.blockSignals(False)
        self.ui.act_canvas_show_external.blockSignals(False)
        self.slot_canvasRefresh()

    @pyqtSlot()
    def slot_canvasShowExternal(self):
        self.fExternalPatchbay = True
        QSafeSettings("falkTX", "Carla2").setValue(CARLA_KEY_CANVAS_SHOW_EXTERNAL, True)
        self.ui.act_canvas_show_internal.blockSignals(True)
        self.ui.act_canvas_show_external.blockSignals(True)
        self.ui.act_canvas_show_internal.setChecked(False)
        self.ui.act_canvas_show_external.setChecked(True)
        self.ui.act_canvas_show_internal.blockSignals(False)
        self.ui.act_canvas_show_external.blockSignals(False)
        self.slot_canvasRefresh()

    @pyqtSlot()
    def slot_canvasArrange(self):
        patchcanvas.arrange()
        self.updateMiniCanvasLater()

    @pyqtSlot()
    def slot_canvasRefresh(self):
        patchcanvas.clear()
        # a full refresh re-enumerates every client, so no id stays filtered from the old pass
        self.fFilteredPatchbayClients.clear()

        if (
            self.host.processMode == ENGINE_PROCESS_MODE_CONTINUOUS_RACK
            and self.host.isPlugin
        ):
            return

        if self.host.is_engine_running():
            self.host.patchbay_refresh(self.fExternalPatchbay)

        self.updateMiniCanvasLater()

    @pyqtSlot()
    def slot_canvasZoomFit(self):
        self.scene.zoom_fit()

    @pyqtSlot()
    def slot_canvasZoomIn(self):
        self.scene.zoom_in()

    @pyqtSlot()
    def slot_canvasZoomOut(self):
        self.scene.zoom_out()

    @pyqtSlot()
    def slot_canvasZoomReset(self):
        self.scene.zoom_reset()

    def _canvasImageRender(self, zoom=1.0):
        img_format = (
            QImage.Format.Format_RGB32 if qt_config == 6 else QImage.Format_RGB32
        )
        image = QImage(
            self.scene.width() * zoom, self.scene.height() * zoom, img_format
        )
        painter = QPainter(image)
        painter.save()
        painter.setRenderHints(
            painter.renderHints() | QPainter.Antialiasing | QPainter.TextAntialiasing
        )
        self.scene.clearSelection()
        self.scene.render(painter)
        painter.restore()
        del painter
        return image

    def _canvasImageWrite(self, iw: QImageWriter, imgFormat: bytes, image: QImage):
        iw.setFormat(imgFormat)
        iw.setCompression(-1)
        if QT_VERSION >= 0x50500:
            iw.setOptimizedWrite(True)
        iw.write(image)

    @pyqtSlot()
    def slot_canvasSaveImage(self):
        if self.fProjectFilename:
            dir = QFileInfo(self.fProjectFilename).absoluteDir().absolutePath()
        else:
            dir = self.fSavedSettings[CARLA_KEY_MAIN_PROJECT_FOLDER]

        fileDialog = QFileDialog(self)
        fileDialog.setAcceptMode(QFileDialog.AcceptSave)
        fileDialog.setDirectory(dir)
        fileDialog.setFileMode(QFileDialog.AnyFile)
        fileDialog.setMimeTypeFilters(("image/png", "image/jpeg"))
        fileDialog.setNameFilter(self.tr("Images (*.png *.jpg)"))
        fileDialog.setOptions(QFileDialog.DontUseCustomDirectoryIcons)
        fileDialog.setWindowTitle(self.tr("Save Image"))

        ok = fileDialog.exec_()

        if not ok:
            return

        newPath = fileDialog.selectedFiles()

        if len(newPath) != 1:
            return

        newPath = newPath[0]

        if QT_VERSION >= 0x50900:
            if fileDialog.selectedMimeTypeFilter() == "image/jpeg":
                imgFormat = b"JPG"
            else:
                imgFormat = b"PNG"
        else:
            if newPath.lower().endswith((".jpg", ".jpeg")):
                imgFormat = b"JPG"
            else:
                imgFormat = b"PNG"

        sender = self.sender()
        if sender == self.ui.act_canvas_save_image_2x:
            zoom = 2.0
        elif sender == self.ui.act_canvas_save_image_4x:
            zoom = 4.0
        else:
            zoom = 1.0

        image = self._canvasImageRender(zoom)
        iw = QImageWriter(newPath)
        self._canvasImageWrite(iw, imgFormat, image)

    @pyqtSlot()
    def slot_canvasCopyToClipboard(self):
        buffer = QBuffer()
        buffer.open(QIODevice.WriteOnly)

        image = self._canvasImageRender()
        iw = QImageWriter(buffer, b"PNG")
        self._canvasImageWrite(iw, b"PNG", image)

        buffer.close()

        mimeData = QMimeData()
        mimeData.setData("image/png", buffer.buffer())
        QApplication.clipboard().setMimeData(mimeData)

    # --------------------------------------------------------------------------------------------------------
    # Canvas (canvas callbacks)

    @pyqtSlot()
    def slot_canvasSelectionChanged(self):
        self.updateMiniCanvasLater()

    @pyqtSlot(float)
    def slot_canvasScaleChanged(self, scale):
        self.ui.miniCanvasPreview.setViewScale(scale)
        widget = self._miniCanvasViewWidget()
        if widget is not None and widget is not self.ui.miniCanvasPreview:
            widget.setViewScale(scale)

    @pyqtSlot(list)
    def slot_canvasPluginSelected(self, pluginList):
        self.ui.keyboard.allNotesOff(False)
        self.ui.scrollArea.setEnabled(len(pluginList) != 0)  # and self.fPluginCount > 0
        self.fSelectedPlugins = pluginList

        # Synchronize selection to Rack only if rack is visible (e.g. in dual-view)
        is_split = hasattr(self, "tabSplit") and self.ui.tabWidget.indexOf(self.tabSplit) == self.ui.tabWidget.currentIndex()
        if is_split and pluginList and len(pluginList) > 0 and self.ui.listWidget is not None:
            firstPluginId = pluginList[0]
            if 0 <= firstPluginId < len(self.fPluginList):
                pitem = self.fPluginList[firstPluginId]
                if pitem is not None:
                    try:
                        self._sync_guard = getattr(self, "_sync_guard", False)
                        if not self._sync_guard:
                            self._sync_guard = True
                            self.ui.listWidget.setCurrentItem(pitem)
                            if hasattr(self.ui.listWidget, "scrollToItemSmooth"):
                                self.ui.listWidget.scrollToItemSmooth(pitem)
                            else:
                                self.ui.listWidget.scrollToItem(pitem)
                    finally:
                        self._sync_guard = False

    @pyqtSlot()
    def slot_rackItemClicked(self, item=None):
        if getattr(self, "_sync_guard", False):
            return
        if item is None and self.ui.listWidget is not None:
            item = self.ui.listWidget.currentItem()
        if item is not None and hasattr(item, "getPluginId"):
            pluginId = item.getPluginId()
            if pluginId >= 0:
                try:
                    self._sync_guard = True
                    patchcanvas.focusGroupUsingPluginId(pluginId)
                finally:
                    self._sync_guard = False

    @pyqtSlot()
    def slot_rackSelectionChanged(self):
        if getattr(self, "_sync_guard", False):
            return
        if self.ui.listWidget is not None:
            item = self.ui.listWidget.currentItem()
            if item is not None and hasattr(item, "getPluginId"):
                pluginId = item.getPluginId()
                if pluginId >= 0:
                    try:
                        self._sync_guard = True
                        patchcanvas.focusGroupUsingPluginId(pluginId)
                    finally:
                        self._sync_guard = False

    @pyqtSlot(bool)
    def slot_toggleSideBySideView(self, enabled, refresh=True):
        if not hasattr(self, "tabSplit"):
            self.tabSplit = QWidget(self.ui.tabWidget)
            self.splitLayout = QVBoxLayout(self.tabSplit)
            self.splitLayout.setContentsMargins(0, 0, 0, 0)
            self.splitLayout.setSpacing(0)

            self.splitter = QSplitter(Qt.Horizontal, self.tabSplit)
            self.splitter.setChildrenCollapsible(False)
            self.splitLayout.addWidget(self.splitter)

        is_modern = getattr(self, "act_settings_modern_ui", None) is not None and self.act_settings_modern_ui.isChecked()

        if enabled:
            # Dynamically reparent patchbay and rack into the splitter
            self.splitter.addWidget(self.ui.patchbay)
            self.splitter.addWidget(self.ui.rack)
            self.ui.rack.setMinimumWidth(self.ui.listWidget.minimumWidth() if hasattr(self.ui, "listWidget") and self.ui.listWidget is not None else 200)
            self.ui.patchbay.show()
            self.ui.rack.show()

            # Set split proportion: 65% Patchbay Canvas, 35% Rack
            w = max(self.width(), 1000)
            self.splitter.setSizes([int(w * 0.65), int(w * 0.35)])

            # In Modern mode, remove the logs tab from central tabWidget
            if is_modern:
                logs_idx = self.ui.tabWidget.indexOf(self.ui.logs)
                if logs_idx != -1:
                    self.ui.tabWidget.removeTab(logs_idx)

                # Only apply custom flush styling if not using system desktop theme
                from styles.theme_manager import theme_manager
                if not theme_manager.is_using_system():
                    bg_hex = "#181825"
                    if hasattr(patchcanvas, "theme") and hasattr(patchcanvas.theme, "canvas_bg"):
                        bg_hex = patchcanvas.theme.canvas_bg.name()

                    self.splitter.setStyleSheet(f"""
                        QSplitter {{
                            background: {bg_hex};
                        }}
                        QSplitter::handle {{
                            background-color: #313244;
                            width: 1px;
                        }}
                        QSplitter::handle:hover {{
                            background-color: #89b4fa;
                            width: 3px;
                        }}
                    """)
                    self.ui.tabWidget.setStyleSheet(f"""
                        QTabWidget::pane {{
                            border: none;
                            background-color: {bg_hex};
                            margin: 0px;
                            padding: 0px;
                        }}
                    """)
                    self.ui.frame.setFrameShape(QFrame.NoFrame)
                    self.ui.frame.setStyleSheet(f"QFrame#frame {{ background-color: {bg_hex}; border: none; }}")
                    self.ui.rack.setStyleSheet(f"QWidget#rack {{ background-color: {bg_hex}; border: none; }}")
                    self.ui.patchbay.setStyleSheet(f"QWidget#patchbay {{ background-color: {bg_hex}; border: none; }}")
                    self.ui.graphicsView.setStyleSheet("QGraphicsView { border: none; outline: none; }")
                    self.ui.listWidget.setStyleSheet(f"""
                        QListWidget {{
                            background-color: {bg_hex};
                            border: none;
                            outline: none;
                            padding: 4px;
                        }}
                        QListWidget::item {{
                            background: transparent;
                            border: none;
                            margin-bottom: 5px;
                        }}
                        QListWidget::item:selected {{
                            background: transparent;
                            border: none;
                        }}
                    """)
                else:
                    self.splitter.setStyleSheet("")
                    self.ui.tabWidget.setStyleSheet("")
                    self.ui.frame.setFrameShape(QFrame.StyledPanel)
                    self.ui.frame.setStyleSheet("")
                    self.ui.rack.setStyleSheet("")
                    self.ui.patchbay.setStyleSheet("")
                    self.ui.graphicsView.setStyleSheet("")
                    self.ui.listWidget.setStyleSheet("")
            else:
                self.splitter.setStyleSheet("")
                self.ui.tabWidget.setStyleSheet("")
                self.ui.frame.setFrameShape(QFrame.StyledPanel)
                self.ui.frame.setStyleSheet("")
                self.ui.rack.setStyleSheet("")
                self.ui.patchbay.setStyleSheet("")
                self.ui.graphicsView.setStyleSheet("")
                self.ui.listWidget.setStyleSheet("")

            splitTabIndex = self.ui.tabWidget.indexOf(self.tabSplit)
            if splitTabIndex == -1:
                self.ui.tabWidget.insertTab(2, self.tabSplit, self.tr("Patchbay + Rack"))
                splitTabIndex = self.ui.tabWidget.indexOf(self.tabSplit)

            self.ui.tabWidget.setCurrentIndex(splitTabIndex)

            # In Modern mode, patchbay+rack is the primary unified workspace; hide the tab bar
            if is_modern:
                self.ui.tabWidget.tabBar().hide()
            else:
                self.ui.tabWidget.tabBar().show()

            self.ui.graphicsView.setFocus()
            if refresh:
                self.slot_canvasRefresh()
        else:
            self.splitter.setStyleSheet("")
            self.ui.tabWidget.setStyleSheet("")
            self.ui.frame.setFrameShape(QFrame.StyledPanel)
            self.ui.frame.setStyleSheet("")
            self.ui.rack.setStyleSheet("")
            self.ui.patchbay.setStyleSheet("")
            self.ui.graphicsView.setStyleSheet("")

            # Restore patchbay and rack into their standalone tab positions
            self.ui.tabWidget.insertTab(0, self.ui.rack, self.tr("Rack"))
            self.ui.tabWidget.insertTab(1, self.ui.patchbay, self.tr("Patchbay"))

            splitTabIndex = self.ui.tabWidget.indexOf(self.tabSplit)
            if splitTabIndex != -1:
                self.ui.tabWidget.removeTab(splitTabIndex)

            # Restore logs tab if missing
            if self.ui.tabWidget.indexOf(self.ui.logs) == -1:
                # If logs was moved to a dialog, reparent it back
                if hasattr(self, "_logsDialog") and self._logsDialog is not None:
                    self._logsDialog.hide()
                    self.ui.logs.setParent(self.ui.tabWidget)
                self.ui.tabWidget.addTab(self.ui.logs, self.tr("Log"))

            self.ui.tabWidget.tabBar().show()
            self.ui.tabWidget.setCurrentIndex(1)
            self.ui.graphicsView.setFocus()
            if refresh:
                self.slot_canvasRefresh()

    # --------------------------------------------------------------------------------------------------------
    # Canvas (host callbacks)

    # Names matching any of these tokens are pure peak-detect observers (ours or
    # third-party like pavucontrol / pwvucontrol) and must not clutter the canvas.
    _PATCHBAY_HIDDEN_NAME_TOKENS = (
        "clarameter",
        "clara meters",
        "peak-detect",
        "peak detect",
        "pavucontrol",
        "pwvucontrol",
        "pw-record",
    )

    def _findGhost(self, name):
        for ghost in getattr(patchcanvas.canvas, "ghost_list", []):
            if ghost.m_group_name == name:
                return ghost
        return None

    def _hideGroupForGhost(self, name, group):
        """Keep the real box hidden while its ports arrive; the ghost covers the build."""
        ghost = self._findGhost(name)
        if ghost is None or not group or not group.widgets:
            return
        if not ghost.bind(group):
            # ghost and real group disagree: invalidate the ghost instead of hiding the node
            patchcanvas.removeGhostGroup(name)
            return
        for widget in group.widgets:
            if widget is None:
                continue
            try:
                widget.setVisible(False)
                widget._ghost_hidden = True
            except RuntimeError:
                pass
        QTimer.singleShot(1500, lambda: self._revealGhost(name))

    @staticmethod
    def _stopWidgetFade(widget):
        for animation in list(getattr(patchcanvas.canvas, "animation_list", [])):
            try:
                if animation.item() is widget:
                    animation.forceStop()
                    patchcanvas.canvas.animation_list.remove(animation)
            except (ValueError, RuntimeError):
                pass
        try:
            widget.setOpacity(1.0)
            if hasattr(widget, "setShadowOpacity"):
                widget.setShadowOpacity(1.0)
        except RuntimeError:
            pass

    def _revealGhost(self, name):
        group = next((g for g in patchcanvas.canvas.group_list if g.group_name == name), None)
        if group is not None:
            for widget in group.widgets:
                if widget is None or not getattr(widget, "_ghost_hidden", False):
                    continue
                try:
                    delattr(widget, "_ghost_hidden")
                    has_ports = bool(getattr(widget, "m_port_list_ids", []))
                    if has_ports or not getattr(patchcanvas.options, "auto_hide_groups", False):
                        self._stopWidgetFade(widget)
                        widget.setVisible(True)
                    widget.update()
                except RuntimeError:
                    pass
        if group is not None:
            for port in list(patchcanvas.canvas.port_list):
                if port.group_id == group.group_id and port.widget is not None:
                    self._stopWidgetFade(port.widget)
                    try:
                        patchcanvas.snapGhostCables(
                            group.group_name, port.port_name,
                            port.widget.sceneBoundingRect().center(),
                        )
                    except RuntimeError:
                        pass
        patchcanvas.removeGhostGroup(name)

    def _maybeRevealGhost(self, clientId):
        group = next((g for g in patchcanvas.canvas.group_list if g.group_id == clientId), None)
        if group is None:
            return
        ghost = self._findGhost(group.group_name)
        if ghost is None:
            return
        expected = len(ghost.m_left) + len(ghost.m_right)
        if expected <= 0:
            # project saved before port names were recorded: give the box a moment to fill
            QTimer.singleShot(200, lambda: self._revealGhost(group.group_name))
            return
        count = sum(1 for p in patchcanvas.canvas.port_list if p.group_id == clientId)
        if count < expected:
            return
        self._revealGhost(group.group_name)

    def _revealAllGhostHidden(self):
        for group in list(patchcanvas.canvas.group_list):
            for widget in group.widgets:
                if widget is None or not getattr(widget, "_ghost_hidden", False):
                    continue
                try:
                    delattr(widget, "_ghost_hidden")
                    if getattr(widget, "m_port_list_ids", []) or not getattr(patchcanvas.options, "auto_hide_groups", False):
                        self._stopWidgetFade(widget)
                        widget.setVisible(True)
                    widget.update()
                except RuntimeError:
                    pass

    def _centerCanvasOnGroup(self, group):
        """While a project loads, pan the canvas to the node that was just created."""
        try:
            if getattr(self, "fUserPannedCanvas", False):
                return
            if not self.fWithCanvas or not group or not group.widgets:
                return
            box = group.widgets[0]
            view = getattr(self.ui, "graphicsView", None)
            if view is None or box is None or box.scene() is None:
                return
            viewport = view.viewport()
            if viewport is None:
                return
            current = view.mapToScene(viewport.rect().center())
            last = getattr(self, "_lastAutoCenter", None)
            if last is not None and (current - last).manhattanLength() > 200.0:
                self.fUserPannedCanvas = True
                return
            view.centerOn(box)
            self._lastAutoCenter = view.mapToScene(viewport.rect().center())
        except Exception:
            pass

    def _isHiddenPatchbayClientName(self, clientName):
        if not clientName:
            return False
        low = clientName.lower()
        return any(token in low for token in self._PATCHBAY_HIDDEN_NAME_TOKENS)

    @pyqtSlot(int, int, int, str)
    def slot_handlePatchbayClientAddedCallback(
        self, clientId, clientIcon, pluginId, clientName
    ):
        log_carla(
            f"carla_host: slot_handlePatchbayClientAddedCallback clientId={clientId}, clientIcon={clientIcon}, pluginId={pluginId}, clientName='{clientName}'",
            level="debug"
        )
        if self._isHiddenPatchbayClientName(clientName):
            self.fFilteredPatchbayClients.add(clientId)
            return
        # The engine reuses client ids without always sending a removal first (for
        # example a pw-record capture client disappears and its id is given to a
        # plugin). Never let a stale filtered id hide a real client's ports.
        self.fFilteredPatchbayClients.discard(clientId)
        pcSplit = patchcanvas.SPLIT_UNDEF
        pcIcon = patchcanvas.ICON_APPLICATION

        if clientIcon == PATCHBAY_ICON_PLUGIN:
            pcIcon = patchcanvas.ICON_PLUGIN
        if clientIcon == PATCHBAY_ICON_HARDWARE:
            pcIcon = patchcanvas.ICON_HARDWARE
        elif clientIcon == PATCHBAY_ICON_CARLA:
            pass
        elif clientIcon == PATCHBAY_ICON_DISTRHO:
            pcIcon = patchcanvas.ICON_DISTRHO
        elif clientIcon == PATCHBAY_ICON_FILE:
            pcIcon = patchcanvas.ICON_FILE

        group_dict = patchcanvas.bindGroupShell(clientName, clientId, pluginId)
        if group_dict is None:
            group_dict = patchcanvas.addGroup(clientId, clientName, pcSplit, pcIcon)
        if getattr(self, "fIsProjectLoading", False):
            self._centerCanvasOnGroup(group_dict)
            if group_dict is not None and not getattr(group_dict.widgets[0], "_shell", False):
                self._hideGroupForGhost(clientName, group_dict)

        self.updateMiniCanvasLater()

        if pluginId < 0:
            return

        if pluginId == MAIN_CARLA_PLUGIN_ID:
            hasCustomUI = False
            hasInlineDisplay = False
            patchcanvas.setGroupAsPlugin(
                clientId, pluginId, hasCustomUI, hasInlineDisplay
            )
        else:
            try:
                hints = self.host.get_plugin_info(pluginId)["hints"]
                hasCustomUI = bool(hints & PLUGIN_HAS_CUSTOM_UI)
                hasInlineDisplay = bool(hints & PLUGIN_HAS_INLINE_DISPLAY)
                patchcanvas.setGroupAsPlugin(
                    clientId, pluginId, hasCustomUI, hasInlineDisplay
                )
                pitem = self.getPluginItem(pluginId)
                if pitem and pitem.getWidget():
                    sc = getattr(pitem.getWidget(), "fSkinColor", None)
                    if sc and sc not in ((40, 40, 40), (255, 255, 255)):
                        hex_col = f"#{sc[0]:02x}{sc[1]:02x}{sc[2]:02x}"
                        for group in patchcanvas.canvas.group_list:
                            if getattr(group, "plugin_id", -1) == pluginId:
                                for w in getattr(group, "widgets", []):
                                    if w is not None:
                                        w.setCustomColor(hex_col, notify=False)
                                break
            except Exception as e:
                log_carla(f"Error mapping plugin to canvas client: {clientName} {e}", level="debug")
                return

    @pyqtSlot(int)
    def slot_handlePatchbayClientRemovedCallback(self, clientId):
        if clientId in self.fFilteredPatchbayClients:
            self.fFilteredPatchbayClients.discard(clientId)
            return
        patchcanvas.removeGroup(clientId)
        self.updateMiniCanvasLater()

    @pyqtSlot(int, str)
    def slot_handlePatchbayClientRenamedCallback(self, clientId, newClientName):
        if clientId in self.fFilteredPatchbayClients or self._isHiddenPatchbayClientName(newClientName):
            self.fFilteredPatchbayClients.add(clientId)
            return
        patchcanvas.renameGroup(clientId, newClientName)
        self.updateMiniCanvasLater()

    @pyqtSlot(int, int, int)
    def slot_handlePatchbayClientDataChangedCallback(
        self, clientId, clientIcon, pluginId
    ):
        if clientId in self.fFilteredPatchbayClients:
            return
        pcIcon = patchcanvas.ICON_APPLICATION

        if clientIcon == PATCHBAY_ICON_PLUGIN:
            pcIcon = patchcanvas.ICON_PLUGIN
        if clientIcon == PATCHBAY_ICON_HARDWARE:
            pcIcon = patchcanvas.ICON_HARDWARE
        elif clientIcon == PATCHBAY_ICON_CARLA:
            pass
        elif clientIcon == PATCHBAY_ICON_DISTRHO:
            pcIcon = patchcanvas.ICON_DISTRHO
        elif clientIcon == PATCHBAY_ICON_FILE:
            pcIcon = patchcanvas.ICON_FILE

        patchcanvas.setGroupIcon(clientId, pcIcon)
        self.updateMiniCanvasLater()

        if pluginId < 0:
            return

        if pluginId == MAIN_CARLA_PLUGIN_ID:
            hasCustomUI = False
            hasInlineDisplay = False
            patchcanvas.setGroupAsPlugin(
                clientId, pluginId, hasCustomUI, hasInlineDisplay
            )
        else:
            try:
                hints = self.host.get_plugin_info(pluginId)["hints"]
                hasCustomUI = bool(hints & PLUGIN_HAS_CUSTOM_UI)
                hasInlineDisplay = bool(hints & PLUGIN_HAS_INLINE_DISPLAY)
                patchcanvas.setGroupAsPlugin(
                    clientId, pluginId, hasCustomUI, hasInlineDisplay
                )
            except Exception:
                return

    @pyqtSlot(int, int, int, int, int)
    def slot_handlePatchbayClientPositionChangedCallback(
        self, clientId, x1, y1, x2, y2
    ):
        if clientId in self.fFilteredPatchbayClients:
            return
        if (x1 != 0 and x2 != 0) or (y1 != 0 and y2 != 0):
            patchcanvas.splitGroup(clientId)
        else:
            patchcanvas.joinGroup(clientId)
        patchcanvas.setGroupPosFull(clientId, x1, y1, x2, y2)
        self.updateMiniCanvasLater()

    @pyqtSlot(int, int, int, int, str)
    def slot_handlePatchbayPortAddedCallback(
        self, clientId, portId, portFlags, portGroupId, portName
    ):
        log_carla(
            f"carla_host: slot_handlePatchbayPortAddedCallback clientId={clientId}, portId={portId}, name='{portName}'",
            level="debug"
        )
        if clientId in self.fFilteredPatchbayClients:
            return
        if portFlags & PATCHBAY_PORT_IS_INPUT:
            portMode = patchcanvas.PORT_MODE_INPUT
        else:
            portMode = patchcanvas.PORT_MODE_OUTPUT

        if portFlags & PATCHBAY_PORT_TYPE_AUDIO:
            portType = patchcanvas.PORT_TYPE_AUDIO_JACK
            isAlternate = False
        elif portFlags & PATCHBAY_PORT_TYPE_CV:
            portType = patchcanvas.PORT_TYPE_PARAMETER
            isAlternate = False
        elif portFlags & PATCHBAY_PORT_TYPE_MIDI:
            portType = patchcanvas.PORT_TYPE_MIDI_JACK
            isAlternate = False
        else:
            portType = patchcanvas.PORT_TYPE_NULL
            isAlternate = False

        patchcanvas.addPort(clientId, portId, portName, portMode, portType, isAlternate)
        if getattr(self, "fIsProjectLoading", False):
            self._maybeRevealGhost(clientId)
            try:
                group = next((g for g in patchcanvas.canvas.group_list if g.group_id == clientId), None)
                port = next((p for p in patchcanvas.canvas.port_list if p.group_id == clientId and p.port_id == portId), None)
                if group is not None and port is not None and port.widget is not None:
                    patchcanvas.snapGhostCables(
                        group.group_name, port.port_name,
                        port.widget.sceneBoundingRect().center(),
                    )
            except RuntimeError:
                pass
        self.updateMiniCanvasLater()

    @pyqtSlot(int, int)
    def slot_handlePatchbayPortRemovedCallback(self, groupId, portId):
        if groupId in self.fFilteredPatchbayClients:
            return
        patchcanvas.removePort(groupId, portId)
        self.updateMiniCanvasLater()

    @pyqtSlot(int, int, int, int, str)
    def slot_handlePatchbayPortChangedCallback(
        self, groupId, portId, portFlags, portGroupId, newPortName
    ):
        if groupId in self.fFilteredPatchbayClients:
            return
        patchcanvas.renamePort(groupId, portId, newPortName)
        self.updateMiniCanvasLater()

    @pyqtSlot(int, int, int, str)
    def slot_handlePatchbayPortGroupAddedCallback(
        self, groupId, portId, portGroupId, newPortName
    ):
        # TODO
        pass

    @pyqtSlot(int, int)
    def slot_handlePatchbayPortGroupRemovedCallback(self, groupId, portId):
        # TODO
        pass

    @pyqtSlot(int, int, int, str)
    def slot_handlePatchbayPortGroupChangedCallback(
        self, groupId, portId, portGroupId, newPortName
    ):
        # TODO
        pass

    @pyqtSlot(int, int, int, int, int)
    def slot_handlePatchbayConnectionAddedCallback(
        self, connectionId, groupOutId, portOutId, groupInId, portInId
    ):
        if groupOutId in self.fFilteredPatchbayClients or groupInId in self.fFilteredPatchbayClients:
            return
        self.fConnections[connectionId] = (groupOutId, portOutId, groupInId, portInId)
        if not patchcanvas.bindShellConnection(connectionId, groupOutId, portOutId, groupInId, portInId):
            patchcanvas.connectPorts(
                connectionId, groupOutId, portOutId, groupInId, portInId
            )
        if getattr(self, "fLoadingDialog", None) is not None:
            self.fLoadingDialog.setDetail("Restoring audio/MIDI graph routing connections...")
        self.updateMiniCanvasLater()

    @pyqtSlot(int, int, int)
    def slot_handlePatchbayConnectionRemovedCallback(
        self, connectionId, portOutId, portInId
    ):
        if self.fConnections.pop(connectionId, None) is None:
            return
        patchcanvas.disconnectPorts(connectionId)
        self.updateMiniCanvasLater()

    # --------------------------------------------------------------------------------------------------------
    # Settings

    def saveSettings(self):
        settings = QSafeSettings()

        settings.setValue("Geometry", self.saveGeometry())
        settings.setValue("ShowToolbar", self.ui.toolBar.isEnabled())
        settings.setValue("ShowMenubar", self.ui.menubar.isVisible())
        show_sb = self.act_settings_show_statusbar.isChecked() if hasattr(self, "act_settings_show_statusbar") else True
        settings.setValue("ShowStatusBar", show_sb)
        settings.setValue("ShowSidePanel", self.ui.dockWidget.isEnabled())

        # Persist side-by-side view state and splitter ratio.
        # The action state is the truth; the old "is split tab current" check
        # saved false whenever another tab was focused on close, producing
        # ModernUiMode=true + SideBySideEnabled=false configs that started
        # classic while the menu claimed modern.
        if hasattr(self, "act_canvas_side_by_side") and self.act_canvas_side_by_side is not None:
            is_split = bool(self.act_canvas_side_by_side.isChecked())
        else:
            is_split = hasattr(self, "tabSplit") and self.ui.tabWidget.indexOf(self.tabSplit) == self.ui.tabWidget.currentIndex()
        settings.setValue("SideBySideEnabled", bool(is_split))
        if hasattr(self, "act_settings_modern_ui") and self.act_settings_modern_ui is not None:
            settings.setValue("ModernUiMode", self.act_settings_modern_ui.isChecked())
        if hasattr(self, "splitter") and self.splitter is not None:
            settings.setValue("SideBySideSizes", self.splitter.sizes())

        diskFolders = []

        for i in range(self.ui.cb_disk.count()):
            diskFolders.append(self.ui.cb_disk.itemData(i))

        settings.setValue("DiskFolders", diskFolders)
        settings.setValue("LastBPM", self.fLastTransportBPM)

        settings.setValue("ShowMeters", self.ui.act_settings_show_meters.isChecked())
        settings.setValue(
            "ShowKeyboard", self.ui.act_settings_show_keyboard.isChecked()
        )
        settings.setValue(
            "HorizontalScrollBarValue",
            self.ui.graphicsView.horizontalScrollBar().value(),
        )
        settings.setValue(
            "VerticalScrollBarValue", self.ui.graphicsView.verticalScrollBar().value()
        )

        settings.setValue(CARLA_KEY_ENGINE_TRANSPORT_MODE, self.host.transportMode)
        settings.setValue(CARLA_KEY_ENGINE_TRANSPORT_EXTRA, self.host.transportExtra)
        settings.setValue(CARLA_KEY_MAIN_RECENT_PROJECTS, self.fRecentProjects)

        self._saveMiniCanvasState()

        return settings

    def loadSettings(self, firstTime):
        settings = QSafeSettings()

        if self.fPluginListDialog is not None:
            gCarla.felib.destroyPluginListDialog(self.fPluginListDialog)
            self.fPluginListDialog = None

        if firstTime:
            geometry = settings.value("Geometry", QByteArray(), QByteArray)
            if not geometry.isNull():
                self.restoreGeometry(geometry)

            showToolbar = settings.value("ShowToolbar", False, bool)
            self.ui.act_settings_show_toolbar.setChecked(showToolbar)
            self.ui.toolBar.blockSignals(True)
            self.ui.toolBar.setEnabled(showToolbar)
            self.ui.toolBar.setVisible(showToolbar)
            self.ui.toolBar.blockSignals(False)

            showMenubar = settings.value("ShowMenubar", False, bool)
            self.slot_showMenubar(showMenubar)

            showStatusBar = settings.value("ShowStatusBar", True, bool)
            self.slot_showStatusbar(showStatusBar)

            # Apply rack spacing & padding from settings
            rackSpacing = settings.value("RackItemSpacing", 4, int)
            rackMinWidth = settings.value("RackItemMinWidth", 200, int)
            if hasattr(self.ui, "listWidget") and self.ui.listWidget is not None:
                from widgets.racklistwidget import RackListItem
                RackListItem.kMinimumWidth = rackMinWidth
                self.ui.listWidget.setMinimumWidth(rackMinWidth)
                self.ui.rack.setMinimumWidth(rackMinWidth)
                self.ui.listWidget.setSpacing(rackSpacing)

            # Restore Modern UI mode (default True)
            modernUi = settings.value("ModernUiMode", True, bool)
            if hasattr(self, "act_settings_modern_ui") and self.act_settings_modern_ui is not None:
                self.act_settings_modern_ui.blockSignals(True)
                self.act_settings_modern_ui.setChecked(modernUi)
                self.act_settings_modern_ui.blockSignals(False)

            # Restore side-by-side view state and splitter ratio (default True for modern)
            default_split = True if modernUi else False
            sideBySide = settings.value("SideBySideEnabled", default_split, bool)
            # Modern UI is the master switch; a stale SideBySideEnabled=false
            # must not start the UI classic while the menu claims modern.
            if modernUi:
                sideBySide = True
            if sideBySide and self.fWithCanvas and hasattr(self, "act_canvas_side_by_side") and self.act_canvas_side_by_side is not None:
                self.act_canvas_side_by_side.setChecked(True)
                self.slot_toggleSideBySideView(True)
                saved_sizes = settings.value("SideBySideSizes", None)
                if saved_sizes and hasattr(self, "splitter") and self.splitter is not None:
                    try:
                        int_sizes = [int(s) for s in saved_sizes]
                        if len(int_sizes) == 2:
                            self.splitter.setSizes(int_sizes)
                    except Exception:
                        pass
            elif not sideBySide and self.fWithCanvas and hasattr(self, "act_canvas_side_by_side") and self.act_canvas_side_by_side is not None:
                self.act_canvas_side_by_side.setChecked(False)
                self.slot_toggleSideBySideView(False)

            # if settings.contains("SplitterState"):
            # self.ui.splitter.restoreState(settings.value("SplitterState", b""))
            # else:
            # self.ui.splitter.setSizes([210, 99999])

            # Modern UI uses a clean canvas with no side panel; any stale
            # ShowSidePanel=true saved by classic-era defaults must not
            # override the modern layout.
            showSidePanel = settings.value("ShowSidePanel", not modernUi, bool)
            if modernUi:
                showSidePanel = False
            self.ui.act_settings_show_side_panel.setChecked(showSidePanel)
            self.slot_showSidePanel(showSidePanel)

            diskFolders = settings.value("DiskFolders", [HOME], list)

            self.ui.cb_disk.setItemData(0, HOME)

            for i in range(len(diskFolders)):
                if i == 0:
                    continue
                folder = diskFolders[i]
                self.ui.cb_disk.addItem(os.path.basename(folder), folder)

            # if CARLA_OS_MAC and not settings.value(CARLA_KEY_MAIN_USE_PRO_THEME, True, bool):
            #     self.setUnifiedTitleAndToolBarOnMac(True)

            # Modern UI uses a clean canvas: canvas meters are hidden by
            # default. A stale ShowMeters=true saved by classic-era defaults
            # must not override the modern layout.
            showMeters = settings.value("ShowMeters", not modernUi, bool)
            if modernUi:
                showMeters = False
            self.ui.act_settings_show_meters.setChecked(showMeters)
            self.ui.peak_in.setVisible(showMeters)
            self.ui.peak_out.setVisible(showMeters)

            showKeyboard = settings.value("ShowKeyboard", True, bool)
            self.ui.act_settings_show_keyboard.setChecked(showKeyboard)
            self.ui.scrollArea.setVisible(showKeyboard)

            settingsDBf = QSafeSettings("falkTX", "CarlaDatabase2")
            self.fFavoritePlugins = settingsDBf.value(
                "PluginDatabase/Favorites", [], list
            )

            rawRecents = settings.value(CARLA_KEY_MAIN_RECENT_PROJECTS, [], list)
            if isinstance(rawRecents, list):
                self.fRecentProjects = [
                    p for p in rawRecents if isinstance(p, str) and os.path.exists(p)
                ]
            self.updateRecentProjectsMenu()

            QTimer.singleShot(100, self.slot_restoreCanvasScrollbarValues)

        # TODO - complete this
        oldSettings = self.fSavedSettings

        if self.host.audioDriverForced is not None:
            audioDriver = self.host.audioDriverForced
        else:
            audioDriver = settings.value(
                CARLA_KEY_ENGINE_AUDIO_DRIVER, CARLA_DEFAULT_AUDIO_DRIVER, str
            )

        audioDriverPrefix = CARLA_KEY_ENGINE_DRIVER_PREFIX + audioDriver

        # One-time migration to enable OpenGL canvas for existing configs
        if not settings.value("Canvas/OpenGLMigrationV1", False, bool):
            settings.setValue(CARLA_KEY_CANVAS_USE_OPENGL, True)
            settings.setValue("Canvas/OpenGLMigrationV1", True)

        self.fSavedSettings = {
            CARLA_KEY_MAIN_PROJECT_FOLDER: settings.value(
                CARLA_KEY_MAIN_PROJECT_FOLDER, CARLA_DEFAULT_MAIN_PROJECT_FOLDER, str
            ),
            CARLA_KEY_MAIN_CONFIRM_EXIT: settings.value(
                CARLA_KEY_MAIN_CONFIRM_EXIT, CARLA_DEFAULT_MAIN_CONFIRM_EXIT, bool
            ),
            CARLA_KEY_MAIN_CLASSIC_SKIN: settings.value(
                CARLA_KEY_MAIN_CLASSIC_SKIN, CARLA_DEFAULT_MAIN_CLASSIC_SKIN, bool
            ),
            CARLA_KEY_MAIN_REFRESH_INTERVAL: settings.value(
                CARLA_KEY_MAIN_REFRESH_INTERVAL,
                CARLA_DEFAULT_MAIN_REFRESH_INTERVAL,
                int,
            ),
            CARLA_KEY_MAIN_SYSTEM_ICONS: settings.value(
                CARLA_KEY_MAIN_SYSTEM_ICONS, CARLA_DEFAULT_MAIN_SYSTEM_ICONS, bool
            ),
            CARLA_KEY_MAIN_MINIMIZE_TO_TRAY: settings.value(
                CARLA_KEY_MAIN_MINIMIZE_TO_TRAY, CARLA_DEFAULT_MAIN_MINIMIZE_TO_TRAY, bool
            ),
            CARLA_KEY_MAIN_EXPERIMENTAL: settings.value(
                CARLA_KEY_MAIN_EXPERIMENTAL, CARLA_DEFAULT_MAIN_EXPERIMENTAL, bool
            ),
            CARLA_KEY_MAIN_AUTOSAVE_ENABLED: settings.value(
                CARLA_KEY_MAIN_AUTOSAVE_ENABLED, CARLA_DEFAULT_MAIN_AUTOSAVE_ENABLED, bool
            ),
            CARLA_KEY_MAIN_AUTOSAVE_INTERVAL: settings.value(
                CARLA_KEY_MAIN_AUTOSAVE_INTERVAL,
                CARLA_DEFAULT_MAIN_AUTOSAVE_INTERVAL,
                int,
            ),
            CARLA_KEY_MAIN_AUTOSAVE_MAX: settings.value(
                CARLA_KEY_MAIN_AUTOSAVE_MAX,
                CARLA_DEFAULT_MAIN_AUTOSAVE_MAX,
                int,
            ),
            CARLA_KEY_MAIN_LOG_TO_CONSOLE: settings.value(
                CARLA_KEY_MAIN_LOG_TO_CONSOLE,
                CARLA_DEFAULT_MAIN_LOG_TO_CONSOLE,
                bool,
            ),
            CARLA_KEY_CANVAS_THEME: settings.value(
                CARLA_KEY_CANVAS_THEME, CARLA_DEFAULT_CANVAS_THEME, str
            ),
            CARLA_KEY_CANVAS_SIZE: settings.value(
                CARLA_KEY_CANVAS_SIZE, CARLA_DEFAULT_CANVAS_SIZE, str
            ),
            CARLA_KEY_CANVAS_AUTO_HIDE_GROUPS: settings.value(
                CARLA_KEY_CANVAS_AUTO_HIDE_GROUPS,
                CARLA_DEFAULT_CANVAS_AUTO_HIDE_GROUPS,
                bool,
            ),
            CARLA_KEY_CANVAS_AUTO_SELECT_ITEMS: settings.value(
                CARLA_KEY_CANVAS_AUTO_SELECT_ITEMS,
                CARLA_DEFAULT_CANVAS_AUTO_SELECT_ITEMS,
                bool,
            ),
            CARLA_KEY_CANVAS_USE_BEZIER_LINES: settings.value(
                CARLA_KEY_CANVAS_USE_BEZIER_LINES,
                CARLA_DEFAULT_CANVAS_USE_BEZIER_LINES,
                bool,
            ),
            CARLA_KEY_CANVAS_EYE_CANDY: settings.value(
                CARLA_KEY_CANVAS_EYE_CANDY, CARLA_DEFAULT_CANVAS_EYE_CANDY, bool
            ),
            CARLA_KEY_CANVAS_FANCY_EYE_CANDY: settings.value(
                CARLA_KEY_CANVAS_FANCY_EYE_CANDY,
                CARLA_DEFAULT_CANVAS_FANCY_EYE_CANDY,
                bool,
            ),
            CARLA_KEY_CANVAS_USE_OPENGL: settings.value(
                CARLA_KEY_CANVAS_USE_OPENGL, CARLA_DEFAULT_CANVAS_USE_OPENGL, bool
            ),
            CARLA_KEY_CANVAS_ANTIALIASING: settings.value(
                CARLA_KEY_CANVAS_ANTIALIASING, CARLA_DEFAULT_CANVAS_ANTIALIASING, int
            ),
            CARLA_KEY_CANVAS_HQ_ANTIALIASING: settings.value(
                CARLA_KEY_CANVAS_HQ_ANTIALIASING,
                CARLA_DEFAULT_CANVAS_HQ_ANTIALIASING,
                bool,
            ),
            CARLA_KEY_CANVAS_FULL_REPAINTS: settings.value(
                CARLA_KEY_CANVAS_FULL_REPAINTS, CARLA_DEFAULT_CANVAS_FULL_REPAINTS, bool
            ),
            CARLA_KEY_CANVAS_ROUNDED_NODES: settings.value(
                CARLA_KEY_CANVAS_ROUNDED_NODES,
                CARLA_DEFAULT_CANVAS_ROUNDED_NODES,
                bool,
            ),
            CARLA_KEY_CANVAS_NODE_RADIUS: settings.value(
                CARLA_KEY_CANVAS_NODE_RADIUS,
                CARLA_DEFAULT_CANVAS_NODE_RADIUS,
                int,
            ),
            CARLA_KEY_CANVAS_NODE_MIN_WIDTH: settings.value(
                CARLA_KEY_CANVAS_NODE_MIN_WIDTH,
                CARLA_DEFAULT_CANVAS_NODE_MIN_WIDTH,
                int,
            ),
            CARLA_KEY_CANVAS_LINE_STYLE: settings.value(
                CARLA_KEY_CANVAS_LINE_STYLE,
                CARLA_DEFAULT_CANVAS_LINE_STYLE,
                str,
            ),
            CARLA_KEY_CANVAS_LINE_STROKE: settings.value(
                CARLA_KEY_CANVAS_LINE_STROKE,
                CARLA_DEFAULT_CANVAS_LINE_STROKE,
                str,
            ),
            CARLA_KEY_CANVAS_LINE_OPACITY: settings.value(
                CARLA_KEY_CANVAS_LINE_OPACITY,
                CARLA_DEFAULT_CANVAS_LINE_OPACITY,
                int,
            ),
            CARLA_KEY_CUSTOM_PAINTING: (
                settings.value(CARLA_KEY_MAIN_USE_PRO_THEME, True, bool)
                and settings.value(CARLA_KEY_MAIN_PRO_THEME_COLOR, "Black", str).lower()
                == "black"
            ),
            # engine
            CARLA_KEY_ENGINE_AUDIO_DRIVER: audioDriver,
            CARLA_KEY_ENGINE_AUDIO_DEVICE: settings.value(
                audioDriverPrefix + "/Device", "", str
            ),
            CARLA_KEY_ENGINE_BUFFER_SIZE: settings.value(
                audioDriverPrefix + "/BufferSize", CARLA_DEFAULT_AUDIO_BUFFER_SIZE, int
            ),
            CARLA_KEY_ENGINE_SAMPLE_RATE: settings.value(
                audioDriverPrefix + "/SampleRate", CARLA_DEFAULT_AUDIO_SAMPLE_RATE, int
            ),
            CARLA_KEY_ENGINE_TRIPLE_BUFFER: settings.value(
                audioDriverPrefix + "/TripleBuffer",
                CARLA_DEFAULT_AUDIO_TRIPLE_BUFFER,
                bool,
            ),
            # file paths
            CARLA_KEY_PATHS_AUDIO: splitter.join(
                settings.value(
                    CARLA_KEY_PATHS_AUDIO, CARLA_DEFAULT_FILE_PATH_AUDIO, list
                )
            ),
            CARLA_KEY_PATHS_MIDI: splitter.join(
                settings.value(CARLA_KEY_PATHS_MIDI, CARLA_DEFAULT_FILE_PATH_MIDI, list)
            ),
            # plugin paths
            CARLA_KEY_PATHS_LADSPA: splitter.join(
                settings.value(CARLA_KEY_PATHS_LADSPA, CARLA_DEFAULT_LADSPA_PATH, list)
            ),
            CARLA_KEY_PATHS_DSSI: splitter.join(
                settings.value(CARLA_KEY_PATHS_DSSI, CARLA_DEFAULT_DSSI_PATH, list)
            ),
            CARLA_KEY_PATHS_LV2: splitter.join(
                settings.value(CARLA_KEY_PATHS_LV2, CARLA_DEFAULT_LV2_PATH, list)
            ),
            CARLA_KEY_PATHS_VST2: splitter.join(
                settings.value(CARLA_KEY_PATHS_VST2, CARLA_DEFAULT_VST2_PATH, list)
            ),
            CARLA_KEY_PATHS_VST3: splitter.join(
                settings.value(CARLA_KEY_PATHS_VST3, CARLA_DEFAULT_VST3_PATH, list)
            ),
            CARLA_KEY_PATHS_SF2: splitter.join(
                settings.value(CARLA_KEY_PATHS_SF2, CARLA_DEFAULT_SF2_PATH, list)
            ),
            CARLA_KEY_PATHS_SFZ: splitter.join(
                settings.value(CARLA_KEY_PATHS_SFZ, CARLA_DEFAULT_SFZ_PATH, list)
            ),
            CARLA_KEY_PATHS_JSFX: splitter.join(
                settings.value(CARLA_KEY_PATHS_JSFX, CARLA_DEFAULT_JSFX_PATH, list)
            ),
            CARLA_KEY_PATHS_CLAP: splitter.join(
                settings.value(CARLA_KEY_PATHS_CLAP, CARLA_DEFAULT_CLAP_PATH, list)
            ),
            # osc
            CARLA_KEY_OSC_ENABLED: settings.value(
                CARLA_KEY_OSC_ENABLED, CARLA_DEFAULT_OSC_ENABLED, bool
            ),
            CARLA_KEY_OSC_TCP_PORT_ENABLED: settings.value(
                CARLA_KEY_OSC_TCP_PORT_ENABLED, CARLA_DEFAULT_OSC_TCP_PORT_ENABLED, bool
            ),
            CARLA_KEY_OSC_TCP_PORT_RANDOM: settings.value(
                CARLA_KEY_OSC_TCP_PORT_RANDOM, CARLA_DEFAULT_OSC_TCP_PORT_RANDOM, bool
            ),
            CARLA_KEY_OSC_TCP_PORT_NUMBER: settings.value(
                CARLA_KEY_OSC_TCP_PORT_NUMBER, CARLA_DEFAULT_OSC_TCP_PORT_NUMBER, int
            ),
            CARLA_KEY_OSC_UDP_PORT_ENABLED: settings.value(
                CARLA_KEY_OSC_UDP_PORT_ENABLED, CARLA_DEFAULT_OSC_UDP_PORT_ENABLED, bool
            ),
            CARLA_KEY_OSC_UDP_PORT_RANDOM: settings.value(
                CARLA_KEY_OSC_UDP_PORT_RANDOM, CARLA_DEFAULT_OSC_UDP_PORT_RANDOM, bool
            ),
            CARLA_KEY_OSC_UDP_PORT_NUMBER: settings.value(
                CARLA_KEY_OSC_UDP_PORT_NUMBER, CARLA_DEFAULT_OSC_UDP_PORT_NUMBER, int
            ),
            # wine
            CARLA_KEY_WINE_EXECUTABLE: settings.value(
                CARLA_KEY_WINE_EXECUTABLE, CARLA_DEFAULT_WINE_EXECUTABLE, str
            ),
            CARLA_KEY_WINE_AUTO_PREFIX: settings.value(
                CARLA_KEY_WINE_AUTO_PREFIX, CARLA_DEFAULT_WINE_AUTO_PREFIX, bool
            ),
            CARLA_KEY_WINE_FALLBACK_PREFIX: settings.value(
                CARLA_KEY_WINE_FALLBACK_PREFIX, CARLA_DEFAULT_WINE_FALLBACK_PREFIX, str
            ),
            CARLA_KEY_WINE_RT_PRIO_ENABLED: settings.value(
                CARLA_KEY_WINE_RT_PRIO_ENABLED, CARLA_DEFAULT_WINE_RT_PRIO_ENABLED, bool
            ),
            CARLA_KEY_WINE_BASE_RT_PRIO: settings.value(
                CARLA_KEY_WINE_BASE_RT_PRIO, CARLA_DEFAULT_WINE_BASE_RT_PRIO, int
            ),
            CARLA_KEY_WINE_SERVER_RT_PRIO: settings.value(
                CARLA_KEY_WINE_SERVER_RT_PRIO, CARLA_DEFAULT_WINE_SERVER_RT_PRIO, int
            ),
            # experimental switches
            CARLA_KEY_EXPERIMENTAL_PLUGIN_BRIDGES: settings.value(
                CARLA_KEY_EXPERIMENTAL_PLUGIN_BRIDGES,
                CARLA_DEFAULT_EXPERIMENTAL_PLUGIN_BRIDGES,
                bool,
            ),
            CARLA_KEY_EXPERIMENTAL_WINE_BRIDGES: settings.value(
                CARLA_KEY_EXPERIMENTAL_WINE_BRIDGES,
                CARLA_DEFAULT_EXPERIMENTAL_WINE_BRIDGES,
                bool,
            ),
        }

        if not self.host.isControl:
            self.fSavedSettings[CARLA_KEY_CANVAS_INLINE_DISPLAYS] = settings.value(
                CARLA_KEY_CANVAS_INLINE_DISPLAYS,
                CARLA_DEFAULT_CANVAS_INLINE_DISPLAYS,
                bool,
            )
        else:
            self.fSavedSettings[CARLA_KEY_CANVAS_INLINE_DISPLAYS] = False

        settings2 = QSafeSettings("falkTX", "Carla2")

        if self.host.experimental:
            visible = settings2.value(
                CARLA_KEY_EXPERIMENTAL_JACK_APPS,
                CARLA_DEFAULT_EXPERIMENTAL_JACK_APPS,
                bool,
            )
            self.ui.act_plugin_add_jack.setVisible(visible)
        else:
            self.ui.act_plugin_add_jack.setVisible(False)

        self.fMiniCanvasUpdateTimeout = (
            1000 if self.fSavedSettings[CARLA_KEY_CANVAS_FANCY_EYE_CANDY] else 0
        )

        setEngineSettings(self.host, self.fSavedSettings)
        self.restartTimersIfNeeded()

        if oldSettings.get(CARLA_KEY_MAIN_CLASSIC_SKIN, None) not in (
            self.fSavedSettings[CARLA_KEY_MAIN_CLASSIC_SKIN],
            None,
        ):
            newSkin = (
                "classic" if self.fSavedSettings[CARLA_KEY_MAIN_CLASSIC_SKIN] else None
            )

            for pitem in self.fPluginList:
                if pitem is None:
                    continue
                pitem.recreateWidget(newSkin=newSkin)

        return settings

    # --------------------------------------------------------------------------------------------------------
    # Settings (helpers)

    def enableTransport(self, enabled):
        self.ui.group_transport_controls.setEnabled(enabled)
        self.ui.group_transport_settings.setEnabled(enabled)

    @pyqtSlot()
    def slot_restoreCanvasScrollbarValues(self):
        settings = QSafeSettings()
        horiz = settings.value(
            "HorizontalScrollBarValue",
            int(self.ui.graphicsView.horizontalScrollBar().maximum() / 2),
            int,
        )
        vertc = settings.value(
            "VerticalScrollBarValue",
            int(self.ui.graphicsView.verticalScrollBar().maximum() / 2),
            int,
        )
        self.ui.graphicsView.horizontalScrollBar().setValue(horiz)
        self.ui.graphicsView.verticalScrollBar().setValue(vertc)

    # --------------------------------------------------------------------------------------------------------
    # Settings (menu actions)

    @pyqtSlot(bool)
    def slot_showMenubar(self, yesNo):
        self.ui.menubar.setVisible(yesNo)
        if hasattr(self, "act_settings_show_menubar"):
            self.act_settings_show_menubar.blockSignals(True)
            self.act_settings_show_menubar.setChecked(yesNo)
            self.act_settings_show_menubar.blockSignals(False)
        if hasattr(self, "act_hamburger_toolbutton"):
            self.act_hamburger_toolbutton.setVisible(not yesNo)
        if hasattr(self, "btn_hamburger_menu"):
            self.btn_hamburger_menu.setVisible(not yesNo)
        # Update floating canvas menu button if canvas overlay exists
        if hasattr(self, "canvasFilter") and hasattr(self.canvasFilter, "toolBar") and hasattr(self.canvasFilter.toolBar, "btnMenu"):
            self.canvasFilter.toolBar.btnMenu.setVisible(not yesNo)

    def _slot_toolbarContextMenu(self, pos):
        menu = QMenu(self.ui.toolBar)
        if hasattr(self, "act_settings_show_menubar"):
            menu.addAction(self.act_settings_show_menubar)
        menu.addAction(self.ui.act_settings_show_toolbar)
        menu.exec_(self.ui.toolBar.mapToGlobal(pos))

    @pyqtSlot(bool)
    def slot_showSidePanel(self, yesNo):
        self.ui.dockWidget.setEnabled(yesNo)
        self.ui.dockWidget.setVisible(yesNo)

    @pyqtSlot(bool)
    def slot_showToolbar(self, yesNo):
        self.ui.toolBar.blockSignals(True)
        self.ui.toolBar.setEnabled(yesNo)
        self.ui.toolBar.setVisible(yesNo)
        self.ui.toolBar.blockSignals(False)

    @pyqtSlot(bool)
    def slot_showStatusbar(self, yesNo):
        if hasattr(self, "act_settings_show_statusbar"):
            self.act_settings_show_statusbar.blockSignals(True)
            self.act_settings_show_statusbar.setChecked(yesNo)
            self.act_settings_show_statusbar.blockSignals(False)
        if hasattr(self.ui, "tw_statusbar") and self.ui.tw_statusbar is not None:
            self.ui.tw_statusbar.setVisible(yesNo)
        if hasattr(self.ui, "statusbar") and self.ui.statusbar is not None:
            self.ui.statusbar.setVisible(yesNo)

    @pyqtSlot(bool)
    def slot_showCanvasMeters(self, yesNo):
        self.ui.peak_in.setVisible(yesNo)
        self.ui.peak_out.setVisible(yesNo)
        QTimer.singleShot(0, self.slot_miniCanvasCheckAll)

    @pyqtSlot(bool)
    def slot_showCanvasKeyboard(self, yesNo):
        self.ui.scrollArea.setVisible(yesNo)
        QTimer.singleShot(0, self.slot_miniCanvasCheckAll)

    @pyqtSlot(bool)
    def slot_toggleModernUi(self, yesNo):
        if hasattr(self, "act_settings_modern_ui") and self.act_settings_modern_ui is not None:
            self.act_settings_modern_ui.blockSignals(True)
            self.act_settings_modern_ui.setChecked(yesNo)
            self.act_settings_modern_ui.blockSignals(False)

        if self.fWithCanvas and hasattr(self, "act_canvas_side_by_side") and self.act_canvas_side_by_side is not None:
            # Modern mode default is unified side-by-side view; Classic mode default is classic multi-tab view
            self.act_canvas_side_by_side.setChecked(yesNo)
            self.slot_toggleSideBySideView(yesNo)

        if yesNo and hasattr(self.ui, "act_settings_show_side_panel") and self.ui.act_settings_show_side_panel is not None:
            # Modern UI hides the side panel by default
            self.ui.act_settings_show_side_panel.setChecked(False)
            self.slot_showSidePanel(False)

        if yesNo and hasattr(self.ui, "act_settings_show_meters") and self.ui.act_settings_show_meters is not None:
            # Modern UI hides the canvas meters by default
            self.ui.act_settings_show_meters.setChecked(False)
            self.slot_showCanvasMeters(False)

        self._updateMiniCanvasPlacement()

    @pyqtSlot()
    def slot_showLogsWindow(self):
        if not hasattr(self, "_logsDialog") or self._logsDialog is None:
            self._logsDialog = QDialog(self)
            self._logsDialog.setWindowTitle(self.tr("Clara Logs"))
            self._logsDialog.resize(800, 500)
            layout = QVBoxLayout(self._logsDialog)
            layout.setContentsMargins(8, 8, 8, 8)
            layout.setSpacing(6)
            self._logsDialogLayout = layout

            # When closed, reparent logs back if in classic mode
            def _on_logs_dialog_close(event):
                is_split = hasattr(self, "tabSplit") and self.ui.tabWidget.indexOf(self.tabSplit) == self.ui.tabWidget.currentIndex()
                if not is_split:
                    self.ui.logs.setParent(self.ui.tabWidget)
                    if self.ui.tabWidget.indexOf(self.ui.logs) == -1:
                        self.ui.tabWidget.addTab(self.ui.logs, self.tr("Log"))
                event.accept()

            self._logsDialog.closeEvent = _on_logs_dialog_close

        # Move logs widget into the dialog if not already inside
        if self.ui.logs.parent() != self._logsDialog:
            logs_idx = self.ui.tabWidget.indexOf(self.ui.logs)
            if logs_idx != -1:
                self.ui.tabWidget.removeTab(logs_idx)
            self.ui.logs.setParent(self._logsDialog)
            self._logsDialogLayout.addWidget(self.ui.logs)

        self.ui.logs.show()
        self._logsDialog.show()
        self._logsDialog.raise_()
        self._logsDialog.activateWindow()

    def _prewarmSettingsDialog(self):
        if getattr(self, "_settingsDialog", None) is None:
            try:
                self._settingsDialog = CarlaSettingsW(self.fParentOrSelf, self.host, True, hasGL)
            except Exception:
                pass

    @pyqtSlot()
    def slot_configureCarla(self):
        if not hasattr(self, "_settingsDialog") or self._settingsDialog is None:
            self._settingsDialog = CarlaSettingsW(self.fParentOrSelf, self.host, True, hasGL)
        else:
            self._settingsDialog.loadSettings()

        if not self._settingsDialog.exec_():
            return

        self.loadSettings(False)

        # Recreate rack items to apply new theme
        if self.ui.listWidget is not None:
            for i in range(self.ui.listWidget.count()):
                item = self.ui.listWidget.item(i)
                if item and hasattr(item, "recreateWidget"):
                    item.recreateWidget(firstInit=True)
            self.ui.listWidget.update()

        if self.fWithCanvas:
            # Non-destructive in-place options update
            self.setupCanvas()
            self.slot_miniCanvasCheckAll()
            if hasattr(self.ui, "graphicsView") and self.ui.graphicsView is not None:
                vp = self.ui.graphicsView.viewport()
                if vp is not None:
                    vp.update()

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

    # --------------------------------------------------------------------------------------------------------
    # Canvas scrollbars

    @pyqtSlot(int)
    def slot_horizontalScrollBarChanged(self, value):
        maximum = self.ui.graphicsView.horizontalScrollBar().maximum()
        if maximum == 0:
            xp = 0
        else:
            xp = float(value) / maximum
        self.ui.miniCanvasPreview.setViewPosX(xp)
        widget = self._miniCanvasViewWidget()
        if widget is not None and widget is not self.ui.miniCanvasPreview:
            widget.setViewPosX(xp)
        self.updateCanvasInitialPos()

    @pyqtSlot(int)
    def slot_verticalScrollBarChanged(self, value):
        maximum = self.ui.graphicsView.verticalScrollBar().maximum()
        if maximum == 0:
            yp = 0
        else:
            yp = float(value) / maximum
        self.ui.miniCanvasPreview.setViewPosY(yp)
        widget = self._miniCanvasViewWidget()
        if widget is not None and widget is not self.ui.miniCanvasPreview:
            widget.setViewPosY(yp)
        self.updateCanvasInitialPos()

    # --------------------------------------------------------------------------------------------------------
    # Canvas keyboard

    @pyqtSlot(int)
    def slot_noteOn(self, note):
        if self.fPluginCount == 0:
            return

        for pluginId in self.fSelectedPlugins:
            self.host.send_midi_note(pluginId, 0, note, 100)

            pedit = self.getPluginEditDialog(pluginId)
            pedit.noteOn(0, note, 100)

    @pyqtSlot(int)
    def slot_noteOff(self, note):
        if self.fPluginCount == 0:
            return

        for pluginId in self.fSelectedPlugins:
            self.host.send_midi_note(pluginId, 0, note, 0)

            pedit = self.getPluginEditDialog(pluginId)
            pedit.noteOff(0, note)

    # --------------------------------------------------------------------------------------------------------
    # Canvas keyboard (host callbacks)

    @pyqtSlot(int, int, int, int)
    def slot_handleNoteOnCallback(self, pluginId, channel, note, velocity):
        if pluginId in self.fSelectedPlugins:
            self.ui.keyboard.sendNoteOn(note, False)

    @pyqtSlot(int, int, int)
    def slot_handleNoteOffCallback(self, pluginId, channel, note):
        if pluginId in self.fSelectedPlugins:
            self.ui.keyboard.sendNoteOff(note, False)

    # --------------------------------------------------------------------------------------------------------

    @pyqtSlot(int)
    def slot_handleUpdateCallback(self, pluginId):
        pitem = self.getPluginItem(pluginId)

        if pitem is None:
            return

        wasCompacted = pitem.isCompacted()
        isCompacted = wasCompacted
        needsRecreate = False

        check = self.host.get_custom_data_value(
            pluginId, CUSTOM_DATA_TYPE_PROPERTY, "CarlaSkinIsCompacted"
        )
        if check:
            isCompacted = bool(check == "true")
            if wasCompacted != isCompacted:
                pitem.fOptions["compact"] = isCompacted
                needsRecreate = True

        newSkin = self.host.get_custom_data_value(
            pluginId, CUSTOM_DATA_TYPE_PROPERTY, "CarlaSkin"
        )
        if newSkin and newSkin != pitem.fOptions.get("skin"):
            pitem.fOptions["skin"] = newSkin
            needsRecreate = True

        newColor = self.host.get_custom_data_value(
            pluginId, CUSTOM_DATA_TYPE_PROPERTY, "CarlaColor"
        )
        if newColor:
            try:
                parsed_color = tuple(int(i) for i in newColor.split(";", 3))
                if parsed_color != pitem.fOptions.get("color"):
                    pitem.fOptions["color"] = parsed_color
                    needsRecreate = True
            except Exception:
                pass

        if needsRecreate:
            wasGuiShown = (
                pitem.fWidget.b_gui.isChecked()
                if pitem.fWidget and pitem.fWidget.b_gui
                else False
            )
            pitem.recreateWidget2(isCompacted, wasGuiShown)

        widget = pitem.getWidget()
        if widget is not None and hasattr(widget, "refreshState"):
            widget.refreshState()

    # --------------------------------------------------------------------------------------------------------
    # MiniCanvas stuff

    @pyqtSlot()
    def slot_miniCanvasCheckAll(self):
        if self._isModernMiniCanvasMode():
            return
        self.slot_miniCanvasCheckSize()
        self.slot_horizontalScrollBarChanged(
            self.ui.graphicsView.horizontalScrollBar().value()
        )
        self.slot_verticalScrollBarChanged(
            self.ui.graphicsView.verticalScrollBar().value()
        )

    @pyqtSlot()
    def slot_miniCanvasCheckSize(self):
        if self._isModernMiniCanvasMode():
            return
        if self.fCanvasWidth == 0 or self.fCanvasHeight == 0:
            return

        currentIndex = self.ui.tabWidget.currentIndex()

        if currentIndex == 1:
            width = self.ui.graphicsView.width()
            height = self.ui.graphicsView.height()
        else:
            self.ui.tabWidget.blockSignals(True)
            self.ui.tabWidget.setCurrentIndex(1)
            width = self.ui.graphicsView.width()
            height = self.ui.graphicsView.height()
            self.ui.tabWidget.setCurrentIndex(currentIndex)
            self.ui.tabWidget.blockSignals(False)

        self.scene.updateLimits()

        scene_w = self.scene.sceneRect().width() if not self.scene.sceneRect().isNull() and self.scene.sceneRect().width() > 0 else self.fCanvasWidth
        scene_h = self.scene.sceneRect().height() if not self.scene.sceneRect().isNull() and self.scene.sceneRect().height() > 0 else self.fCanvasHeight

        self.ui.miniCanvasPreview.setViewSize(
            float(width) / scene_w, float(height) / scene_h
        )
        widget = self._miniCanvasViewWidget()
        if widget is not None and widget is not self.ui.miniCanvasPreview:
            widget.setViewSize(float(width) / scene_w, float(height) / scene_h)
        self._repositionMiniCanvasFloat()

    def _isModernMiniCanvasMode(self):
        if hasattr(self, "act_settings_modern_ui") and self.act_settings_modern_ui is not None:
            try:
                return bool(self.act_settings_modern_ui.isChecked())
            except Exception:
                return True
        return True

    def _miniCanvasViewWidget(self):
        if self._isModernMiniCanvasMode():
            widget = getattr(self.ui, "modernMiniCanvas", None)
            if widget is not None:
                return widget
        return getattr(self.ui, "miniCanvasPreview", None)

    def _ensureMiniCanvasOverlay(self):
        if getattr(self.ui, "miniCanvasOverlay", None) is not None:
            return self.ui.miniCanvasOverlay
        try:
            from widgets.canvasminimapframe import CanvasMinimapOverlay
            # Anchor the map to the patchbay container (the graphics view's
            # parent), matching the floating toolbars, so it stays put when
            # the view is panned/zoomed/resized.
            overlayParent = self.ui.graphicsView.parentWidget() or self.ui.graphicsView.viewport()
            overlay = CanvasMinimapOverlay(
                overlayParent,
                self.ui.graphicsView,
                self.scene,
                self,
            )
            self.ui.miniCanvasOverlay = overlay
            self.ui.miniCanvasFloatFrame = overlay
            self.ui.modernMiniCanvas = overlay.map
            overlay.visibilityChanged.connect(self._onMiniCanvasVisibilityRequested)
            overlay.geometryChanged.connect(self._onMiniCanvasGeometryChanged)
            overlay.collapsedChanged.connect(lambda *_: self._saveMiniCanvasState())
            overlay.zoomChanged.connect(lambda *_: self._saveMiniCanvasState())
            return overlay
        except Exception as ex:
            logger.warning("CANVAS", f"Could not create floating minimap overlay: {ex}")
            return None

    def _ensureMiniCanvasRestoreButton(self):
        if getattr(self.ui, "btnShowMiniCanvas", None) is not None:
            return self.ui.btnShowMiniCanvas
        try:
            btnParent = self.ui.graphicsView.parentWidget() or self.ui.graphicsView.viewport()
            btn = QToolButton(btnParent)
            btn.setObjectName("btnShowMiniCanvas")
            btn.setText("\U0001F5FA  Map")
            btn.setToolTip("Show minimap")
            btn.setToolButtonStyle(Qt.ToolButtonTextOnly)
            btn.setAutoRaise(False)
            btn.setStyleSheet(
                "QToolButton { background-color: rgba(24,24,37,0.86); "
                "border: 1px solid rgba(137,180,250,0.35); border-radius: 6px; "
                "padding: 2px 8px; }"
            )
            btn.clicked.connect(self._showMiniCanvasFloat)
            btn.hide()
            self.ui.btnShowMiniCanvas = btn
            return btn
        except Exception as ex:
            logger.warning("CANVAS", f"Could not create minimap restore button: {ex}")
            return None


    def _updateMiniCanvasPlacement(self):
        if not hasattr(self.ui, "miniCanvasPreview"):
            return

        modern = self._isModernMiniCanvasMode()

        if modern:
            overlay = self._ensureMiniCanvasOverlay()
            self._ensureMiniCanvasRestoreButton()
            if overlay is None:
                return

            # Classic preview is inactive in modern mode.
            try:
                self.ui.miniCanvasPreview.hide()
            except Exception:
                pass

            # Theme sync + (re)bind the scene for the modern widget.
            # Guard so init()'s resetView() does not clobber the saved zoom.
            self._miniCanvasRestoring = True
            try:
                overlay.map.setViewTheme(
                    patchcanvas.canvas.theme.canvas_bg,
                    patchcanvas.canvas.theme.rubberband_brush.color(),
                    patchcanvas.canvas.theme.rubberband_pen.color(),
                )
                overlay.map.init(
                    self.scene,
                    self.fCanvasWidth,
                    self.fCanvasHeight,
                    self.fSavedSettings[CARLA_KEY_CUSTOM_PAINTING],
                )
            except Exception:
                pass
            finally:
                self._miniCanvasRestoring = False

            if hasattr(self.ui, "tw_miniCanvas"):
                try:
                    self.ui.tw_miniCanvas.hide()
                except Exception:
                    pass

            self._expandSceneRectForMinimap()
            self._restoreMiniCanvasState()
            self._repositionMiniCanvasFloat()
            QTimer.singleShot(100, self._repositionMiniCanvasFloat)
            QTimer.singleShot(400, self._repositionMiniCanvasFloat)
        else:
            # Restore the classic sidebar placement.
            if getattr(self.ui, "miniCanvasFloatFrame", None) is not None:
                try:
                    self.ui.miniCanvasPreview.setParent(self.ui.tab_3)
                    if hasattr(self.ui, "verticalLayout_7"):
                        self.ui.verticalLayout_7.addWidget(self.ui.miniCanvasPreview)
                    self.ui.miniCanvasFloatFrame.hide()
                except Exception:
                    pass
            if getattr(self.ui, "btnShowMiniCanvas", None) is not None:
                try:
                    self.ui.btnShowMiniCanvas.hide()
                except Exception:
                    pass
            if getattr(self.ui, "modernMiniCanvas", None) is not None:
                try:
                    self.ui.modernMiniCanvas.hide()
                except Exception:
                    pass
            if hasattr(self.ui, "tw_miniCanvas"):
                try:
                    self.ui.tw_miniCanvas.show()
                except Exception:
                    pass

    def _onMiniCanvasVisibilityRequested(self, visible):
        if visible:
            self._showMiniCanvasFloat()
        else:
            self._hideMiniCanvasFloat()

    def _onMiniCanvasGeometryChanged(self):
        self._miniCanvasUserPositioned = True
        self._saveMiniCanvasState()

    def _hideMiniCanvasFloat(self):
        overlay = getattr(self.ui, "miniCanvasFloatFrame", None)
        if overlay is not None:
            overlay.hide()
        self._miniCanvasUserVisible = False
        self._repositionMiniCanvasFloat()
        self._saveMiniCanvasState()

    def _showMiniCanvasFloat(self):
        overlay = getattr(self.ui, "miniCanvasFloatFrame", None)
        if overlay is not None:
            overlay.show()
            overlay.raise_()
        self._miniCanvasUserVisible = True
        self._expandSceneRectForMinimap()
        self._repositionMiniCanvasFloat()
        self._saveMiniCanvasState()

    def _restoreMiniCanvasState(self):
        overlay = getattr(self.ui, "miniCanvasFloatFrame", None)
        if overlay is None:
            return
        self._miniCanvasRestoring = True
        try:
            settings = QSafeSettings()
            zoom = settings.value("Minimap/Zoom", 1.0, float)
            collapsed = settings.value("Minimap/Collapsed", False, bool)
            visible = settings.value("Minimap/Visible", True, bool)
            pos_x = settings.value("Minimap/X", -1, int)
            pos_y = settings.value("Minimap/Y", -1, int)

            overlay.map.setZoom(zoom)
            overlay.toggleCollapsed(collapsed)

            if pos_x >= 0 and pos_y >= 0:
                overlay.move(int(pos_x), int(pos_y))
                self._miniCanvasUserPositioned = True
            else:
                self._miniCanvasUserPositioned = False

            self._miniCanvasUserVisible = bool(visible)
            if visible:
                overlay.show()
            else:
                overlay.hide()
        except Exception as ex:
            logger.warning("CANVAS", f"Could not restore minimap state: {ex}")
        finally:
            self._miniCanvasRestoring = False
        self._saveMiniCanvasState()

    def _saveMiniCanvasState(self):
        if getattr(self, "_miniCanvasRestoring", False):
            return
        overlay = getattr(self.ui, "miniCanvasFloatFrame", None)
        if overlay is None:
            return
        try:
            settings = QSafeSettings()
            if getattr(self, "_miniCanvasUserPositioned", False):
                settings.setValue("Minimap/X", int(overlay.x()))
                settings.setValue("Minimap/Y", int(overlay.y()))
            else:
                settings.setValue("Minimap/X", -1)
                settings.setValue("Minimap/Y", -1)
            settings.setValue("Minimap/Zoom", float(overlay.map.getZoom()))
            settings.setValue("Minimap/Collapsed", bool(overlay.isCollapsed()))
            settings.setValue(
                "Minimap/Visible", bool(getattr(self, "_miniCanvasUserVisible", True))
            )
        except Exception as ex:
            logger.warning("CANVAS", f"Could not save minimap state: {ex}")

    def _expandSceneRectForMinimap(self):
        try:
            scene = self.scene
            if scene is None:
                return
            bounds = None
            for item in scene.items():
                if not (hasattr(item, "m_group_id") and hasattr(item, "p_height")):
                    continue
                try:
                    if not item.isVisible():
                        continue
                except Exception:
                    pass
                r = item.sceneBoundingRect()
                bounds = QRectF(r) if bounds is None else bounds.united(r)
            if bounds is None or bounds.isNull():
                return
            margin = 500.0
            needed = bounds.adjusted(-margin, -margin, margin, margin)
            current = scene.sceneRect()
            if not current.isNull() and current.contains(needed):
                return
            expanded = needed if current.isNull() else current.united(needed)
            try:
                patchcanvas.canvas.size_rect = expanded
            except Exception:
                pass
            scene.setSceneRect(expanded)
            try:
                self.ui.graphicsView.setSceneRect(expanded)
            except Exception:
                pass
            if hasattr(scene, "updateLimits"):
                scene.updateLimits()
        except Exception as ex:
            logger.warning("CANVAS", f"Could not expand scene rect for minimap: {ex}")

    def _repositionMiniCanvasFloat(self):
        overlay = getattr(self.ui, "miniCanvasFloatFrame", None)
        if overlay is None:
            return
        try:
            # Position against the overlay's parent (the patchbay container,
            # matching the floating toolbars); fall back to the viewport.
            base = overlay.parentWidget() or self.ui.graphicsView.viewport()
            if overlay.isVisible():
                overlay.adjustSize()
                if getattr(self, "_miniCanvasUserPositioned", False):
                    pos = overlay.pos()
                else:
                    pos = QPoint(
                        base.width() - overlay.width() - 10,
                        base.height() - overlay.height() - 10,
                    )
                max_x = max(0, base.width() - overlay.width())
                max_y = max(0, base.height() - overlay.height())
                pos.setX(max(0, min(pos.x(), max_x)))
                pos.setY(max(0, min(pos.y(), max_y)))
                overlay.move(pos)
                overlay.raise_()

            btn = getattr(self.ui, "btnShowMiniCanvas", None)
            if btn is not None:
                if not overlay.isVisible():
                    btn.move(base.width() - btn.width() - 12, base.height() - btn.height() - 12)
                    btn.raise_()
                    btn.show()
                else:
                    btn.hide()
        except Exception:
            pass

    @pyqtSlot(float, float)
    def slot_miniCanvasMoved(self, xp, yp):
        hsb = self.ui.graphicsView.horizontalScrollBar()
        vsb = self.ui.graphicsView.verticalScrollBar()
        hsb.setValue(xp * hsb.maximum())
        vsb.setValue(yp * vsb.maximum())
        self.updateCanvasInitialPos()

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
        # a GUI dialog. This blocks the UI while waiting for an answer, which is
        # fine because the user is interacting with the terminal anyway. Pressing
        # Enter (the default) quits Clara.
        has_tray = getattr(self, "fSystemTrayIcon", None) is not None
        answer = ""

        try:
            from rich.console import Console
            from rich.prompt import Prompt
            from rich.text import Text

            body = Text()
            body.append("Ctrl+C received from the terminal.\n", style="bold yellow")
            body.append("Quit Clara now?", style="bold white")
            body.append("\n\n")
            body.append("[Enter]", style="bold bright_magenta")
            body.append("  Quit now", style="dim")
            body.append("  (default)\n", style="bold dim")
            if has_tray:
                body.append("[T]", style="bold bright_cyan")
                body.append("      Keep running in the system tray\n", style="dim")

            Console().print(body)

            answer = Prompt.ask("[bold yellow]Choice[/]", default="",
                                show_default=False).strip().lower()
        except Exception:
            try:
                print("")
                print("Ctrl+C received from the terminal.")
                print("Quit Clara now?")
                print("  [Enter] Quit now (default)")
                if has_tray:
                    print("  [T]     Keep running in the system tray")
                sys.stdout.write("Choice [Enter/T]: " if has_tray else "Choice [Enter]: ")
                sys.stdout.flush()
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

    # --------------------------------------------------------------------------------------------------------
    # show/hide event

    def showEvent(self, event):
        self.getAndRefreshRuntimeInfo()
        self.refreshTransport(True)
        QMainWindow.showEvent(self, event)

        if QT_VERSION >= 0x50600:
            self.host.set_engine_option(
                ENGINE_OPTION_FRONTEND_UI_SCALE,
                int(self.devicePixelRatioF() * 1000),
                "",
            )
            log_carla(f"Frontend pixel ratio is {self.devicePixelRatioF()}", level="debug")

        # set our gui as parent for all plugins UIs
        if self.host.manageUIs and not self.host.isControl:
            if CARLA_OS_MAC:
                nsViewPtr = int(self.winId())
                winIdStr = "%x" % gCarla.utils.cocoa_get_window(nsViewPtr)
            elif CARLA_OS_WIN or QApplication.platformName() == "xcb":
                winIdStr = "%x" % int(self.winId())
            else:
                winIdStr = "0"
            self.host.set_engine_option(ENGINE_OPTION_FRONTEND_WIN_ID, 0, winIdStr)

    def hideEvent(self, event):
        # disable parent
        if not self.host.isControl:
            self.host.set_engine_option(ENGINE_OPTION_FRONTEND_WIN_ID, 0, "0")

        QMainWindow.hideEvent(self, event)

    # --------------------------------------------------------------------------------------------------------
    # resize event

    def resizeEvent(self, event):
        QMainWindow.resizeEvent(self, event)

        if self.fWithCanvas:
            self.slot_miniCanvasCheckSize()

    # --------------------------------------------------------------------------------------------------------
    # timer event

    def refreshRuntimeInfo(self, load, xruns):
        txt1 = str(xruns) if (xruns >= 0) else "--"
        txt2 = "" if (xruns == 1) else "s"
        self.ui.b_xruns.setText("%s Xrun%s" % (txt1, txt2))
        self.ui.pb_dsp_load.setValue(int(load))

    def getAndRefreshRuntimeInfo(self):
        if not self.ui.pb_dsp_load.isVisible():
            return
        if not self.host.is_engine_running():
            return
        info = self.host.get_runtime_engine_info()
        self.refreshRuntimeInfo(info["load"], info["xruns"])

    def idleFast(self):
        self.host.engine_idle()
        self.refreshTransport()

        if self.fPluginCount == 0 or self.fCurrentlyRemovingAllPlugins:
            return

        for pitem in self.fPluginList:
            if pitem is None:
                break

            widget = pitem.getWidget()
            if widget is not None and widget.isVisible():
                if hasattr(widget, "idleFast"):
                    widget.idleFast()

        for pluginId in self.fSelectedPlugins:
            self.fPeaksCleared = False
            if self.ui.peak_in.isVisible():
                self.ui.peak_in.displayMeter(
                    1, self.host.get_input_peak_value(pluginId, True)
                )
                self.ui.peak_in.displayMeter(
                    2, self.host.get_input_peak_value(pluginId, False)
                )
            if self.ui.peak_out.isVisible():
                self.ui.peak_out.displayMeter(
                    1, self.host.get_output_peak_value(pluginId, True)
                )
                self.ui.peak_out.displayMeter(
                    2, self.host.get_output_peak_value(pluginId, False)
                )
            return

        if self.fPeaksCleared:
            return

        self.fPeaksCleared = True
        self.ui.peak_in.displayMeter(1, 0.0, True)
        self.ui.peak_in.displayMeter(2, 0.0, True)
        self.ui.peak_out.displayMeter(1, 0.0, True)
        self.ui.peak_out.displayMeter(2, 0.0, True)

    def idleSlow(self):
        self.getAndRefreshRuntimeInfo()
        self.updateSessionStatusIndicators()

        if self.fPluginCount == 0 or self.fCurrentlyRemovingAllPlugins:
            return

        for pitem in self.fPluginList:
            if pitem is None:
                break

            widget = pitem.getWidget()
            if widget is not None:
                if hasattr(widget, "idleSlow"):
                    widget.idleSlow()

    def timerEvent(self, event):
        if event.timerId() == self.fIdleTimerFast:
            self.idleFast()

        elif event.timerId() == self.fIdleTimerSlow:
            self.idleSlow()

        QMainWindow.timerEvent(self, event)

    # --------------------------------------------------------------------------------------------------------
    # color/style change event

    def changeEvent(self, event):
        if event.type() in (QEvent.PaletteChange, QEvent.StyleChange):
            self.updateStyle()

        if event.type() == QEvent.WindowStateChange:
            if (
                self.isMinimized()
                and self.fSavedSettings.get(
                    CARLA_KEY_MAIN_MINIMIZE_TO_TRAY, CARLA_DEFAULT_MAIN_MINIMIZE_TO_TRAY
                )
                and self.fSystemTrayIcon is not None
            ):
                self._minimizeToSystemTray()

        QMainWindow.changeEvent(self, event)

    # --------------------------------------------------------------------------------------------------------
    # system tray

    def _setupSystemTray(self):
        # Make the standard Quit action perform a real quit instead of hiding to tray
        try:
            self.ui.act_file_quit.triggered.disconnect()
        except (TypeError, RuntimeError):
            pass
        self.ui.act_file_quit.triggered.connect(self._requestQuit)

        if not QSystemTrayIcon.isSystemTrayAvailable():
            self.fSystemTrayIcon = None
            return

        try:
            icon = self.windowIcon()
            if icon is None or icon.isNull():
                icon = QApplication.instance().windowIcon()
            if icon is None or icon.isNull():
                icon = QIcon(":/scalable/carla.svg")
            if icon is None or icon.isNull():
                icon = QIcon.fromTheme("carla")
        except Exception:
            icon = QIcon(":/scalable/carla.svg")

        self.fSystemTrayIcon = QSystemTrayIcon(icon, self)
        self.fSystemTrayIcon.setToolTip(self.windowTitle())

        tray_menu = QMenu(self)

        # Summary / status items (kept up to date when the menu is shown)
        title_action = QAction(self.tr("Clara"), self)
        title_action.setEnabled(False)
        tray_menu.addAction(title_action)
        tray_menu.addSeparator()

        self.fTrayInfoEngine = QAction("", self)
        self.fTrayInfoEngine.setEnabled(False)
        tray_menu.addAction(self.fTrayInfoEngine)

        self.fTrayInfoLoad = QAction("", self)
        self.fTrayInfoLoad.setEnabled(False)
        tray_menu.addAction(self.fTrayInfoLoad)

        self.fTrayInfoBuffer = QAction("", self)
        self.fTrayInfoBuffer.setEnabled(False)
        tray_menu.addAction(self.fTrayInfoBuffer)

        self.fTrayInfoSampleRate = QAction("", self)
        self.fTrayInfoSampleRate.setEnabled(False)
        tray_menu.addAction(self.fTrayInfoSampleRate)

        tray_menu.addSeparator()

        show_action = QAction(self.tr("Show"), self)
        show_action.triggered.connect(self._restoreFromSystemTray)
        tray_menu.addAction(show_action)

        hide_action = QAction(self.tr("Hide"), self)
        hide_action.triggered.connect(self._minimizeToSystemTray)
        tray_menu.addAction(hide_action)

        quit_action = QAction(self.tr("Quit"), self)
        quit_action.triggered.connect(self._requestQuit)
        tray_menu.addAction(quit_action)

        tray_menu.aboutToShow.connect(self._updateTrayMenuInfo)

        # Show a native context menu on right click and also let the activated
        # signal handle left-click popups.
        self.fSystemTrayMenu = tray_menu
        self.fSystemTrayIcon.setContextMenu(tray_menu)
        self.fSystemTrayIcon.activated.connect(self._onSystemTrayActivated)

        # Show the tray icon as soon as the application starts so it can be
        # reopened/restored from Hyprland/tiling WMs that lack minimize buttons.
        self.fSystemTrayIcon.show()
        QApplication.instance().setQuitOnLastWindowClosed(False)

    def _requestQuit(self):
        self.fForceQuit = True
        self.close()

    def _minimizeToSystemTray(self):
        if self.fSystemTrayIcon is None:
            return
        QApplication.instance().setQuitOnLastWindowClosed(False)
        self.hide()
        self.fSystemTrayIcon.show()
        self.fSystemTrayIcon.setToolTip(self.windowTitle())

    def _restoreFromSystemTray(self):
        self.showNormal()
        self.show()
        self.raise_()
        self.activateWindow()
        QTimer.singleShot(0, self._requestWindowFocus)

    def _requestWindowFocus(self):
        # Ask Qt/the compositor to activate the window (best effort).
        try:
            handle = self.windowHandle()
            if handle is not None:
                handle.requestActivate()
        except Exception:
            pass
        self.raise_()
        self.activateWindow()

        # Otherwise rely solely on the standard xdg-activation request above.

    def _onSystemTrayActivated(self, reason):
        # Right-click is handled natively by the context menu.
        if reason == QSystemTrayIcon.ActivationReason.Context:
            return

        # Any other click (left click, middle click, double click) shows an
        # interactive summary instead of silently doing nothing.
        if self.fSystemTrayIcon is None:
            return

        self._updateTrayMenuInfo()
        menu = getattr(self, "fSystemTrayMenu", None)
        if menu is not None:
            menu.popup(QCursor.pos())

    def _updateTrayMenuInfo(self):
        running = False
        try:
            running = self.host.is_engine_running()
        except Exception:
            running = False

        load = "--"
        try:
            info = self.host.get_runtime_engine_info()
            if isinstance(info, dict):
                load = info.get("load", "--")
        except Exception:
            pass

        self.fTrayInfoEngine.setText(
            self.tr("Engine: Running") if running else self.tr("Engine: Stopped")
        )
        self.fTrayInfoLoad.setText(self.tr("DSP Load: %s%%") % load)
        self.fTrayInfoBuffer.setText(
            self.tr("Buffer: %s") % (self.fBufferSize if self.fBufferSize not in (0, None) else "--")
        )
        sr = self.fSampleRate
        self.fTrayInfoSampleRate.setText(
            self.tr("Sample Rate: %s") % (sr if sr not in (0, None, 0.0) else "--")
        )

    def updateStyle(self):
        self.ui.pad_left.hide()
        self.ui.pad_right.hide()
        if not QSafeSettings("falkTX", "Carla2").value(
            CARLA_KEY_MAIN_USE_PRO_THEME, CARLA_DEFAULT_MAIN_USE_PRO_THEME, bool
        ):
            self.ui.pad_left.setAutoFillBackground(False)
            self.ui.pad_right.setAutoFillBackground(False)
            return

        # Rack padding images setup
        rack_imgL = QImage(":/bitmaps/rack_padding_left.png")
        rack_imgR = QImage(":/bitmaps/rack_padding_right.png")

        min_value = 0.07

        if PYQT_VERSION >= 0x50600:
            value_fix = 1.0 / (
                1.0
                - rack_imgL.scaled(1, 1, Qt.IgnoreAspectRatio, Qt.SmoothTransformation)
                .pixelColor(0, 0)
                .blackF()
            )
        else:
            value_fix = 1.5

        rack_pal = self.ui.rack.palette()
        bg_color = rack_pal.window().color()
        fg_color = rack_pal.text().color()
        bg_value = 1.0 - bg_color.blackF()
        if bg_value != 0.0 and bg_value < min_value:
            pad_color = bg_color.lighter(int(100 * min_value / bg_value * value_fix))
        else:
            pad_color = QColor.fromHsvF(0.0, 0.0, min_value * value_fix)

        painter = QPainter()
        fillRect = rack_imgL.rect().adjusted(-1, -1, 1, 1)

        painter.begin(rack_imgL)
        painter.setCompositionMode(QPainter.CompositionMode_Multiply)
        painter.setBrush(pad_color)
        painter.drawRect(fillRect)
        painter.end()
        rack_pixmapL = QPixmap(rack_imgL)
        self.imgL_palette = QPalette()
        self.imgL_palette.setBrush(QPalette.Window, QBrush(rack_pixmapL))
        self.ui.pad_left.setPalette(self.imgL_palette)
        self.ui.pad_left.setAutoFillBackground(True)

        painter.begin(rack_imgR)
        painter.setCompositionMode(QPainter.CompositionMode_Multiply)
        painter.setBrush(pad_color)
        painter.drawRect(fillRect)
        painter.end()
        rack_pixmapR = QPixmap(rack_imgR)
        self.imgR_palette = QPalette()
        self.imgR_palette.setBrush(QPalette.Window, QBrush(rack_pixmapR))
        self.ui.pad_right.setPalette(self.imgR_palette)
        self.ui.pad_right.setAutoFillBackground(True)

        # qt's rgba is actually argb, so convert that
        bg_color_value = bg_color.rgba()
        bg_color_value = ((bg_color_value & 0xFFFFFF) << 8) | (bg_color_value >> 24)

        fg_color_value = fg_color.rgba()
        fg_color_value = ((fg_color_value & 0xFFFFFF) << 8) | (fg_color_value >> 24)

        self.host.set_engine_option(
            ENGINE_OPTION_FRONTEND_BACKGROUND_COLOR, bg_color_value, ""
        )
        self.host.set_engine_option(
            ENGINE_OPTION_FRONTEND_FOREGROUND_COLOR, fg_color_value, ""
        )

    # --------------------------------------------------------------------------------------------------------
    # close event

    def shouldIgnoreClose(self):
        if self.host.isControl or self.host.isPlugin:
            return False
        if self.fCustomStopAction == self.CUSTOM_ACTION_APP_CLOSE:
            return False
        if self.fWindowCloseHideGui:
            return False

        # If project has unsaved changes, offer Save, Discard, Cancel
        if getattr(self, "fHasUnsavedChanges", False):
            proj_name = os.path.basename(self.fProjectFilename) if self.fProjectFilename else self.tr("Untitled Project")
            res = QMessageBox.question(
                self,
                self.tr("Save Changes"),
                self.tr(f"The project '{proj_name}' has unsaved changes.\n\nDo you want to save before closing?"),
                QMessageBox.Save | QMessageBox.Discard | QMessageBox.Cancel,
                QMessageBox.Save,
            )
            if res == QMessageBox.Cancel:
                return True
            if res == QMessageBox.Save:
                self.slot_fileSave()
                # If still unsaved (e.g. user canceled file dialog), abort close
                if getattr(self, "fHasUnsavedChanges", False):
                    return True
            return False

        if self.fSavedSettings[CARLA_KEY_MAIN_CONFIRM_EXIT]:
            return (
                QMessageBox.question(
                    self,
                    self.tr("Quit"),
                    self.tr("Are you sure you want to quit Carla?"),
                    QMessageBox.Yes | QMessageBox.No,
                )
                == QMessageBox.No
            )
        return False

    def closeEvent(self, event):
        # When "minimize to system tray" is enabled, closing the window simply
        # hides the application into the tray instead of quitting. The save/discard
        # prompt is therefore reserved for an explicit quit (Tray -> Quit / Ctrl+Q).
        if (
            not getattr(self, "fForceQuit", False)
            and self.fSystemTrayIcon is not None
            and self.fSavedSettings.get(
                CARLA_KEY_MAIN_MINIMIZE_TO_TRAY, CARLA_DEFAULT_MAIN_MINIMIZE_TO_TRAY
            )
        ):
            event.ignore()
            self._minimizeToSystemTray()
            return

        if self.shouldIgnoreClose():
            event.ignore()
            return

        # Pre-emptively hide the main window immediately so the UI disappears without stutter
        self.hide()
        QApplication.instance().processEvents()

        if (
            self.fWindowCloseHideGui
            and self.fCustomStopAction != self.CUSTOM_ACTION_APP_CLOSE
        ):
            self.hideForNSM()
            self.host.nsm_ready(NSM_CALLBACK_HIDE_OPTIONAL_GUI)
            return

        patchcanvas.handleAllPluginsRemoved()

        if (
            CARLA_OS_MAC
            and self.fMacClosingHelper
            and not (self.host.isControl or self.host.isPlugin)
        ):
            self.fCustomStopAction = self.CUSTOM_ACTION_APP_CLOSE
            self.fMacClosingHelper = False
            event.ignore()

            for i in reversed(range(self.fPluginCount)):
                self.host.show_custom_ui(i, False)

            QTimer.singleShot(100, self.close)
            return

        self.killTimers()
        self.saveSettings()

        # Give an in-flight update check a moment to finish, so Qt never destroys a running QThread.
        # shortcut: urllib has no cancel, a very slow DNS lookup can still outlive this wait.
        for _name in ("fUpdateThread", "_manualUpdateThread"):
            _thread = getattr(self, _name, None)
            if _thread is None:
                continue
            try:
                if _thread.isRunning():
                    _thread.wait(2500)
            except RuntimeError:
                setattr(self, _name, None)

        if self.host.is_engine_running() and not (
            self.host.isControl or self.host.isPlugin
        ):
            if not self.slot_engineStop(True):
                self.fCustomStopAction = self.CUSTOM_ACTION_APP_CLOSE
                event.ignore()
                return

        QMainWindow.closeEvent(self, event)

        # if we reach this point, fully close ourselves
        gCarla.gui = None
        QApplication.instance().quit()

    @pyqtSlot()
    def slot_checkForUpdates(self):
        self._manualUpdateThread = UpdateCheckThread(self, is_manual=True)
        self._manualUpdateThread.update_available.connect(self._on_update_available)
        self._manualUpdateThread.no_update_found.connect(self._on_manual_check_uptodate)
        self._manualUpdateThread.check_failed.connect(self._on_manual_check_failed)
        self._manualUpdateThread.finished.connect(self._onUpdateCheckThreadFinished)
        self._manualUpdateThread.start()

    @pyqtSlot()
    def _onUpdateCheckThreadFinished(self):
        # deleteLater() would leave self.fUpdateThread pointing at a dead C++ object,
        # which made closeEvent raise RuntimeError and the app unkillable via SIGTERM.
        thread = self.sender()
        if thread is self.fUpdateThread:
            self.fUpdateThread = None
        if thread is getattr(self, "_manualUpdateThread", None):
            self._manualUpdateThread = None
        if thread is not None:
            thread.deleteLater()

    def _on_manual_check_uptodate(self, current_ver):
        QMessageBox.information(
            self,
            self.tr("Up to Date"),
            self.tr("You are running the latest version of Clara (v%s).") % current_ver
        )

    def _on_manual_check_failed(self, err_msg):
        QMessageBox.warning(
            self,
            self.tr("Update Check Failed"),
            self.tr("Could not check for updates:\n%s") % err_msg
        )

    def _on_update_available(self, release_info):
        try:
            if not self.fUpdateBanner:
                self.fUpdateBanner = UpdateNotificationBanner(release_info, self)
                layout = self.ui.centralwidget.layout()
                if layout:
                    layout.insertWidget(0, self.fUpdateBanner)
            else:
                self.fUpdateBanner.release_info = release_info
                self.fUpdateBanner.version = release_info.get("version", "")
                self.fUpdateBanner.show()
                self.fUpdateBanner.raise_()

            # For critical or suggested updates, also prompt modal changelog dialog immediately
            if release_info.get("urgency", "").lower() in ("critical", "suggested"):
                from carla_shared import CLARA_VERSION_STRING
                dlg = UpdateChangelogDialog(release_info, self, current_version=CLARA_VERSION_STRING.lstrip("v"))
                dlg.exec_()
        except Exception:
            pass

    def _check_and_show_support_banner(self, force=False):
        try:
            import time
            settings = QSettings("falkTX", "Carla2")
            if not force:
                if settings.value("Clara/SupportBannerNeverShow", False, type=bool):
                    return

                snooze_until = settings.value("Clara/SupportBannerSnoozeUntil", 0, type=int)
                if time.time() < snooze_until:
                    return

            if not self.fSupportBanner:
                self.fSupportBanner = SupportNotificationBanner(self)
                layout = self.ui.centralwidget.layout()
                if layout:
                    insert_idx = 1 if (self.fUpdateBanner and self.fUpdateBanner.isVisible()) else 0
                    layout.insertWidget(insert_idx, self.fSupportBanner)
            else:
                self.fSupportBanner.show()
                self.fSupportBanner.raise_()
        except Exception:
            pass


# ------------------------------------------------------------------------------------------------
# ------------------------------------------------------------------------------------------------------------
# Engine callback


def engineCallback(host, action, pluginId, value1, value2, value3, valuef, valueStr):
    # kdevelop likes this :)
    if False:
        host = CarlaHostNull()

    valueStr = charPtrToString(valueStr)

    if action == ENGINE_CALLBACK_ENGINE_STARTED:
        host.processMode = value1
        host.transportMode = value2
    elif action == ENGINE_CALLBACK_PROCESS_MODE_CHANGED:
        host.processMode = value1
    elif action == ENGINE_CALLBACK_TRANSPORT_MODE_CHANGED:
        host.transportMode = value1
        host.transportExtra = valueStr

    if action == ENGINE_CALLBACK_DEBUG:
        host.DebugCallback.emit(pluginId, value1, value2, value3, valuef, valueStr)
    elif action == ENGINE_CALLBACK_PLUGIN_ADDED:
        log_carla(
            f"engineCallback: PLUGIN_ADDED id={pluginId}, type={value1}, name='{valueStr}'"
        )
        host.PluginAddedCallback.emit(pluginId, value1, valueStr)
        if gCarla.gui is not None and not getattr(gCarla.gui, "fIsProjectLoading", False):
            gCarla.gui.markProjectModified()
    elif action == ENGINE_CALLBACK_PLUGIN_REMOVED:
        log_carla(f"engineCallback: PLUGIN_REMOVED id={pluginId}")
        host.PluginRemovedCallback.emit(pluginId)
        if gCarla.gui is not None and not getattr(gCarla.gui, "fIsProjectLoading", False):
            gCarla.gui.markProjectModified()
    elif action == ENGINE_CALLBACK_PLUGIN_RENAMED:
        log_carla(f"engineCallback: PLUGIN_RENAMED id={pluginId}, name='{valueStr}'")
        host.PluginRenamedCallback.emit(pluginId, valueStr)
        if gCarla.gui is not None and not getattr(gCarla.gui, "fIsProjectLoading", False):
            gCarla.gui.markProjectModified()
    elif action == ENGINE_CALLBACK_PLUGIN_UNAVAILABLE:
        host.PluginUnavailableCallback.emit(pluginId, valueStr)
    elif action == ENGINE_CALLBACK_PARAMETER_VALUE_CHANGED:
        host.ParameterValueChangedCallback.emit(pluginId, value1, valuef)
    elif action == ENGINE_CALLBACK_PARAMETER_DEFAULT_CHANGED:
        host.ParameterDefaultChangedCallback.emit(pluginId, value1, valuef)
    elif action == ENGINE_CALLBACK_PARAMETER_MAPPED_CONTROL_INDEX_CHANGED:
        host.ParameterMappedControlIndexChangedCallback.emit(pluginId, value1, value2)
    elif action == ENGINE_CALLBACK_PARAMETER_MAPPED_RANGE_CHANGED:
        minimum, maximum = (float(v) for v in valueStr.split(":", 2))
        host.ParameterMappedRangeChangedCallback.emit(
            pluginId, value1, minimum, maximum
        )
    elif action == ENGINE_CALLBACK_PARAMETER_MIDI_CHANNEL_CHANGED:
        host.ParameterMidiChannelChangedCallback.emit(pluginId, value1, value2)
    elif action == ENGINE_CALLBACK_PROGRAM_CHANGED:
        host.ProgramChangedCallback.emit(pluginId, value1)
    elif action == ENGINE_CALLBACK_MIDI_PROGRAM_CHANGED:
        host.MidiProgramChangedCallback.emit(pluginId, value1)
    elif action == ENGINE_CALLBACK_OPTION_CHANGED:
        host.OptionChangedCallback.emit(pluginId, value1, bool(value2))
    elif action == ENGINE_CALLBACK_UI_STATE_CHANGED:
        host.UiStateChangedCallback.emit(pluginId, value1)
    elif action == ENGINE_CALLBACK_NOTE_ON:
        host.NoteOnCallback.emit(pluginId, value1, value2, value3)
    elif action == ENGINE_CALLBACK_NOTE_OFF:
        host.NoteOffCallback.emit(pluginId, value1, value2)
    elif action == ENGINE_CALLBACK_UPDATE:
        host.UpdateCallback.emit(pluginId)
    elif action == ENGINE_CALLBACK_RELOAD_INFO:
        host.ReloadInfoCallback.emit(pluginId)
    elif action == ENGINE_CALLBACK_RELOAD_PARAMETERS:
        host.ReloadParametersCallback.emit(pluginId)
    elif action == ENGINE_CALLBACK_RELOAD_PROGRAMS:
        host.ReloadProgramsCallback.emit(pluginId)
    elif action == ENGINE_CALLBACK_RELOAD_ALL:
        host.ReloadAllCallback.emit(pluginId)
    elif action == ENGINE_CALLBACK_PATCHBAY_CLIENT_ADDED:
        log_carla(
            f"engineCallback: PATCHBAY_CLIENT_ADDED clientId={pluginId}, icon={value1}, pluginId={value2}, name='{valueStr}'",
            level="debug"
        )
        host.PatchbayClientAddedCallback.emit(pluginId, value1, value2, valueStr)
    elif action == ENGINE_CALLBACK_PATCHBAY_CLIENT_REMOVED:
        log_carla(f"engineCallback: PATCHBAY_CLIENT_REMOVED clientId={pluginId}", level="debug")
        host.PatchbayClientRemovedCallback.emit(pluginId)
    elif action == ENGINE_CALLBACK_PATCHBAY_CLIENT_RENAMED:
        log_carla(
            f"engineCallback: PATCHBAY_CLIENT_RENAMED clientId={pluginId}, name='{valueStr}'",
            level="debug"
        )
        host.PatchbayClientRenamedCallback.emit(pluginId, valueStr)
    elif action == ENGINE_CALLBACK_PATCHBAY_CLIENT_DATA_CHANGED:
        host.PatchbayClientDataChangedCallback.emit(pluginId, value1, value2)
    elif action == ENGINE_CALLBACK_PATCHBAY_CLIENT_POSITION_CHANGED:
        host.PatchbayClientPositionChangedCallback.emit(
            pluginId, value1, value2, value3, int(round(valuef))
        )
    elif action == ENGINE_CALLBACK_PATCHBAY_PORT_ADDED:
        log_carla(
            f"engineCallback: PATCHBAY_PORT_ADDED clientId={pluginId}, portId={value1}, flags={value2}, name='{valueStr}'",
            level="debug"
        )
        host.PatchbayPortAddedCallback.emit(pluginId, value1, value2, value3, valueStr)
    elif action == ENGINE_CALLBACK_PATCHBAY_PORT_REMOVED:
        log_carla(
            f"engineCallback: PATCHBAY_PORT_REMOVED clientId={pluginId}, portId={value1}",
            level="debug"
        )
        host.PatchbayPortRemovedCallback.emit(pluginId, value1)
    elif action == ENGINE_CALLBACK_PATCHBAY_PORT_CHANGED:
        host.PatchbayPortChangedCallback.emit(
            pluginId, value1, value2, value3, valueStr
        )
    elif action == ENGINE_CALLBACK_PATCHBAY_PORT_GROUP_ADDED:
        host.PatchbayPortGroupAddedCallback.emit(pluginId, value1, value2, valueStr)
    elif action == ENGINE_CALLBACK_PATCHBAY_PORT_GROUP_REMOVED:
        host.PatchbayPortGroupRemovedCallback.emit(pluginId, value1)
    elif action == ENGINE_CALLBACK_PATCHBAY_PORT_GROUP_CHANGED:
        host.PatchbayPortGroupChangedCallback.emit(pluginId, value1, value2, valueStr)
    elif action == ENGINE_CALLBACK_PATCHBAY_CONNECTION_ADDED:
        log_carla(
            f"engineCallback: PATCHBAY_CONNECTION_ADDED clientId={pluginId}, conn='{valueStr}'",
            level="debug"
        )
        gOut, pOut, gIn, pIn = [int(i) for i in valueStr.split(":")]  # FIXME
        host.PatchbayConnectionAddedCallback.emit(pluginId, gOut, pOut, gIn, pIn)
        if gCarla.gui is not None and not getattr(gCarla.gui, "fIsProjectLoading", False):
            gCarla.gui.markProjectModified()
    elif action == ENGINE_CALLBACK_PATCHBAY_CONNECTION_REMOVED:
        log_carla(
            f"engineCallback: PATCHBAY_CONNECTION_REMOVED clientId={pluginId}, connId={value1}",
            level="debug"
        )
        host.PatchbayConnectionRemovedCallback.emit(pluginId, value1, value2)
        if gCarla.gui is not None and not getattr(gCarla.gui, "fIsProjectLoading", False):
            gCarla.gui.markProjectModified()
    elif action == ENGINE_CALLBACK_ENGINE_STARTED:
        host.EngineStartedCallback.emit(
            pluginId, value1, value2, value3, valuef, valueStr
        )
    elif action == ENGINE_CALLBACK_ENGINE_STOPPED:
        host.EngineStoppedCallback.emit()
    elif action == ENGINE_CALLBACK_PROCESS_MODE_CHANGED:
        host.ProcessModeChangedCallback.emit(value1)
    elif action == ENGINE_CALLBACK_TRANSPORT_MODE_CHANGED:
        host.TransportModeChangedCallback.emit(value1, valueStr)
    elif action == ENGINE_CALLBACK_BUFFER_SIZE_CHANGED:
        host.BufferSizeChangedCallback.emit(value1)
    elif action == ENGINE_CALLBACK_SAMPLE_RATE_CHANGED:
        host.SampleRateChangedCallback.emit(valuef)
    elif action == ENGINE_CALLBACK_CANCELABLE_ACTION:
        host.CancelableActionCallback.emit(pluginId, bool(value1 != 0), valueStr)
        QApplication.processEvents()
    elif action == ENGINE_CALLBACK_PROJECT_LOAD_FINISHED:
        host.ProjectLoadFinishedCallback.emit()
    elif action == ENGINE_CALLBACK_NSM:
        host.NSMCallback.emit(value1, value2, valueStr)
    elif action == ENGINE_CALLBACK_IDLE:
        QApplication.processEvents()
    elif action == ENGINE_CALLBACK_INFO:
        host.InfoCallback.emit(valueStr)
    elif action == ENGINE_CALLBACK_ERROR:
        host.ErrorCallback.emit(valueStr)
    elif action == ENGINE_CALLBACK_QUIT:
        host.QuitCallback.emit()
    elif action == ENGINE_CALLBACK_INLINE_DISPLAY_REDRAW:
        host.InlineDisplayRedrawCallback.emit(pluginId)
    else:
        log_carla(f"Unhandled engine action: {action}", level="debug")


# ------------------------------------------------------------------------------------------------------------
# File callback


def fileCallback(ptr, action, isDir, title, filter):
    title = charPtrToString(title)
    filter = charPtrToString(filter)

    if action == FILE_CALLBACK_OPEN:
        ret, _selected_filter = QFileDialog.getOpenFileName(
            gCarla.gui, title, "", filter
        )  # , QFileDialog.ShowDirsOnly if isDir else 0x0)
    elif action == FILE_CALLBACK_SAVE:
        ret, _selected_filter = QFileDialog.getSaveFileName(
            gCarla.gui, title, "", filter, QFileDialog.ShowDirsOnly if isDir else 0x0
        )
    else:
        ret, _selected_filter = ("", "")

    # FIXME use ok value, test if it works as expected
    if not ret:
        return None

    # FIXME
    global fileRet
    fileRet = c_char_p(ret.encode("utf-8"))
    retval = cast(byref(fileRet), POINTER(c_uintptr))
    return retval.contents.value


# ------------------------------------------------------------------------------------------------------------
# Init host


def initHost(initName, libPrefix, isControl, isPlugin, failError, HostClass=None):
    pathBinaries, pathResources = getPaths(libPrefix)

    # --------------------------------------------------------------------------------------------------------
    # Fail if binary dir is not found

    if not os.path.exists(pathBinaries):
        if failError:
            QMessageBox.critical(
                None, "Error", "Failed to find the carla binaries, cannot continue"
            )
            sys.exit(1)
        return

    # --------------------------------------------------------------------------------------------------------
    # Check if we should open main lib as local or global

    settings = QSafeSettings("falkTX", "Carla2")

    loadGlobal = settings.value(
        CARLA_KEY_EXPERIMENTAL_LOAD_LIB_GLOBAL,
        CARLA_DEFAULT_EXPERIMENTAL_LOAD_LIB_GLOBAL,
        bool,
    )

    # --------------------------------------------------------------------------------------------------------
    # Set Carla library name

    libname = "libcarla_{}2.{}".format(
        "control" if isControl else "standalone",
        DLL_EXTENSION,
    )
    libname = os.path.join(pathBinaries, libname)
    felibname = os.path.join(pathBinaries, f"libcarla_frontend.{DLL_EXTENSION}")
    utilsname = os.path.join(pathBinaries, f"libcarla_utils.{DLL_EXTENSION}")

    # --------------------------------------------------------------------------------------------------------
    # Print info

    if not (gCarla.nogui and isinstance(gCarla.nogui, int)):
        printStartupBanner([
            ("Python", sys.version.split(" ", 1)[0]),
            ("Qt", QT_VERSION_STR),
            ("PyQt", PYQT_VERSION_STR),
            ("Binaries", pathBinaries),
            ("Resources", pathResources),
        ])

    # --------------------------------------------------------------------------------------------------------
    # Init host

    if failError:
        # no try
        host = (
            HostClass()
            if HostClass is not None
            else CarlaHostQtDLL(libname, loadGlobal)
        )
    else:
        try:
            host = (
                HostClass()
                if HostClass is not None
                else CarlaHostQtDLL(libname, loadGlobal)
            )
        except Exception:
            host = CarlaHostQtNull()

    host.isControl = isControl
    host.isPlugin = isPlugin

    host.set_engine_callback(
        lambda h, a, p, v1, v2, v3, vf, vs: engineCallback(
            host, a, p, v1, v2, v3, vf, vs
        )
    )
    host.set_file_callback(fileCallback)

    # If it's a plugin the paths are already set
    if not isPlugin:
        host.pathBinaries = pathBinaries
        host.pathResources = pathResources
        host.set_engine_option(ENGINE_OPTION_PATH_BINARIES, 0, pathBinaries)
        host.set_engine_option(ENGINE_OPTION_PATH_RESOURCES, 0, pathResources)

        if not isControl:
            host.nsmOK = host.nsm_init(os.getpid(), initName)

    # --------------------------------------------------------------------------------------------------------
    # Init frontend lib

    if not gCarla.nogui:
        gCarla.felib = CarlaFrontendLib(felibname)

    # --------------------------------------------------------------------------------------------------------
    # Init utils

    gCarla.utils = CarlaUtils(utilsname)
    gCarla.utils.set_process_name(os.path.basename(initName))

    try:
        sys.stdout.flush()
    except Exception:
        pass

    sys.stdout = CarlaPrint(False)
    sys.stderr = CarlaPrint(True)
    sys.excepthook = sys_excepthook

    # --------------------------------------------------------------------------------------------------------
    # Done

    return host


# ------------------------------------------------------------------------------------------------------------
# Load host settings


def loadHostSettings(host):
    # kdevelop likes this :)
    if False:
        host = CarlaHostNull()

    settings = QSafeSettings("falkTX", "Carla2")

    host.experimental = settings.value(
        CARLA_KEY_MAIN_EXPERIMENTAL, CARLA_DEFAULT_MAIN_EXPERIMENTAL, bool
    )
    host.exportLV2 = settings.value(
        CARLA_KEY_EXPERIMENTAL_EXPORT_LV2, CARLA_DEFAULT_EXPERIMENTAL_LV2_EXPORT, bool
    )
    host.manageUIs = settings.value(
        CARLA_KEY_ENGINE_MANAGE_UIS, CARLA_DEFAULT_MANAGE_UIS, bool
    )
    host.maxParameters = settings.value(
        CARLA_KEY_ENGINE_MAX_PARAMETERS, CARLA_DEFAULT_MAX_PARAMETERS, int
    )
    host.resetXruns = settings.value(
        CARLA_KEY_ENGINE_RESET_XRUNS, CARLA_DEFAULT_RESET_XRUNS, bool
    )
    host.forceStereo = settings.value(
        CARLA_KEY_ENGINE_FORCE_STEREO, CARLA_DEFAULT_FORCE_STEREO, bool
    )
    host.preferPluginBridges = settings.value(
        CARLA_KEY_ENGINE_PREFER_PLUGIN_BRIDGES,
        CARLA_DEFAULT_PREFER_PLUGIN_BRIDGES,
        bool,
    )
    host.preferUIBridges = settings.value(
        CARLA_KEY_ENGINE_PREFER_UI_BRIDGES, CARLA_DEFAULT_PREFER_UI_BRIDGES, bool
    )
    host.preventBadBehaviour = settings.value(
        CARLA_KEY_EXPERIMENTAL_PREVENT_BAD_BEHAVIOUR,
        CARLA_DEFAULT_EXPERIMENTAL_PREVENT_BAD_BEHAVIOUR,
        bool,
    )
    host.showLogs = (
        settings.value(CARLA_KEY_MAIN_SHOW_LOGS, CARLA_DEFAULT_MAIN_SHOW_LOGS, bool)
        and not CARLA_OS_WIN
    )
    host.showPluginBridges = settings.value(
        CARLA_KEY_EXPERIMENTAL_PLUGIN_BRIDGES,
        CARLA_DEFAULT_EXPERIMENTAL_PLUGIN_BRIDGES,
        bool,
    )
    host.showWineBridges = settings.value(
        CARLA_KEY_EXPERIMENTAL_WINE_BRIDGES,
        CARLA_DEFAULT_EXPERIMENTAL_WINE_BRIDGES,
        bool,
    )
    host.uiBridgesTimeout = settings.value(
        CARLA_KEY_ENGINE_UI_BRIDGES_TIMEOUT, CARLA_DEFAULT_UI_BRIDGES_TIMEOUT, int
    )
    host.uisAlwaysOnTop = settings.value(
        CARLA_KEY_ENGINE_UIS_ALWAYS_ON_TOP, CARLA_DEFAULT_UIS_ALWAYS_ON_TOP, bool
    )

    if host.isPlugin:
        return

    host.transportExtra = settings.value(CARLA_KEY_ENGINE_TRANSPORT_EXTRA, "", str)

    # enums
    if host.audioDriverForced is None:
        host.transportMode = settings.value(
            CARLA_KEY_ENGINE_TRANSPORT_MODE, CARLA_DEFAULT_TRANSPORT_MODE, int
        )

    if not host.processModeForced:
        host.processMode = settings.value(
            CARLA_KEY_ENGINE_PROCESS_MODE, CARLA_DEFAULT_PROCESS_MODE, int
        )

    host.nextProcessMode = host.processMode

    # --------------------------------------------------------------------------------------------------------
    # fix things if needed

    if host.processMode == ENGINE_PROCESS_MODE_MULTIPLE_CLIENTS:
        if LADISH_APP_NAME:
            print(
                "LADISH detected but using multiple clients (not allowed), forcing single client now"
            )
            host.nextProcessMode = host.processMode = ENGINE_PROCESS_MODE_SINGLE_CLIENT

        else:
            host.transportMode = ENGINE_TRANSPORT_MODE_JACK

    if gCarla.nogui:
        host.showLogs = False

    # --------------------------------------------------------------------------------------------------------
    # run headless host now if nogui option enabled

    if gCarla.nogui:
        runHostWithoutUI(host)


# ------------------------------------------------------------------------------------------------------------
# Set host settings


def setHostSettings(host):
    # kdevelop likes this :)
    if False:
        host = CarlaHostNull()

    host.set_engine_option(ENGINE_OPTION_FORCE_STEREO, host.forceStereo, "")
    host.set_engine_option(ENGINE_OPTION_MAX_PARAMETERS, host.maxParameters, "")
    host.set_engine_option(ENGINE_OPTION_RESET_XRUNS, host.resetXruns, "")
    host.set_engine_option(
        ENGINE_OPTION_PREFER_PLUGIN_BRIDGES, host.preferPluginBridges, ""
    )
    host.set_engine_option(ENGINE_OPTION_PREFER_UI_BRIDGES, host.preferUIBridges, "")
    host.set_engine_option(
        ENGINE_OPTION_PREVENT_BAD_BEHAVIOUR, host.preventBadBehaviour, ""
    )
    host.set_engine_option(ENGINE_OPTION_UI_BRIDGES_TIMEOUT, host.uiBridgesTimeout, "")
    host.set_engine_option(ENGINE_OPTION_UIS_ALWAYS_ON_TOP, host.uisAlwaysOnTop, "")

    if host.isPlugin or host.isRemote or host.is_engine_running():
        return

    host.set_engine_option(ENGINE_OPTION_PROCESS_MODE, host.nextProcessMode, "")
    host.set_engine_option(
        ENGINE_OPTION_TRANSPORT_MODE, host.transportMode, host.transportExtra
    )
    host.set_engine_option(ENGINE_OPTION_DEBUG_CONSOLE_OUTPUT, host.showLogs, "")

    if not (NSM_URL and host.nsmOK):
        host.set_engine_option(ENGINE_OPTION_CLIENT_NAME_PREFIX, 0, gCarla.cnprefix)


# ---------------------------------------------------------------------------------------------------------------------
# Set Engine settings according to carla preferences. Returns selected audio driver.


def setEngineSettings(host, settings, oscPort=None):
    # kdevelop likes this :)
    if False:
        host = CarlaHostNull()

    # -----------------------------------------------------------------------------------------------------------------
    # do nothing if control

    if host.isControl:
        return "Control"

    # -----------------------------------------------------------------------------------------------------------------
    # fetch settings as needed

    if settings is None:
        qsettings = QSafeSettings("falkTX", "Carla2")

        if host.audioDriverForced is not None:
            audioDriver = host.audioDriverForced
        else:
            audioDriver = qsettings.value(
                CARLA_KEY_ENGINE_AUDIO_DRIVER, CARLA_DEFAULT_AUDIO_DRIVER, str
            )

        audioDriverPrefix = CARLA_KEY_ENGINE_DRIVER_PREFIX + audioDriver

        settings = {
            # engine
            CARLA_KEY_ENGINE_AUDIO_DRIVER: audioDriver,
            CARLA_KEY_ENGINE_AUDIO_DEVICE: qsettings.value(
                audioDriverPrefix + "/Device", "", str
            ),
            CARLA_KEY_ENGINE_BUFFER_SIZE: qsettings.value(
                audioDriverPrefix + "/BufferSize", CARLA_DEFAULT_AUDIO_BUFFER_SIZE, int
            ),
            CARLA_KEY_ENGINE_SAMPLE_RATE: qsettings.value(
                audioDriverPrefix + "/SampleRate", CARLA_DEFAULT_AUDIO_SAMPLE_RATE, int
            ),
            CARLA_KEY_ENGINE_TRIPLE_BUFFER: qsettings.value(
                audioDriverPrefix + "/TripleBuffer",
                CARLA_DEFAULT_AUDIO_TRIPLE_BUFFER,
                bool,
            ),
            # file paths
            CARLA_KEY_PATHS_AUDIO: splitter.join(
                qsettings.value(
                    CARLA_KEY_PATHS_AUDIO, CARLA_DEFAULT_FILE_PATH_AUDIO, list
                )
            ),
            CARLA_KEY_PATHS_MIDI: splitter.join(
                qsettings.value(
                    CARLA_KEY_PATHS_MIDI, CARLA_DEFAULT_FILE_PATH_MIDI, list
                )
            ),
            # plugin paths
            CARLA_KEY_PATHS_LADSPA: splitter.join(
                qsettings.value(CARLA_KEY_PATHS_LADSPA, CARLA_DEFAULT_LADSPA_PATH, list)
            ),
            CARLA_KEY_PATHS_DSSI: splitter.join(
                qsettings.value(CARLA_KEY_PATHS_DSSI, CARLA_DEFAULT_DSSI_PATH, list)
            ),
            CARLA_KEY_PATHS_LV2: splitter.join(
                qsettings.value(CARLA_KEY_PATHS_LV2, CARLA_DEFAULT_LV2_PATH, list)
            ),
            CARLA_KEY_PATHS_VST2: splitter.join(
                qsettings.value(CARLA_KEY_PATHS_VST2, CARLA_DEFAULT_VST2_PATH, list)
            ),
            CARLA_KEY_PATHS_VST3: splitter.join(
                qsettings.value(CARLA_KEY_PATHS_VST3, CARLA_DEFAULT_VST3_PATH, list)
            ),
            CARLA_KEY_PATHS_SF2: splitter.join(
                qsettings.value(CARLA_KEY_PATHS_SF2, CARLA_DEFAULT_SF2_PATH, list)
            ),
            CARLA_KEY_PATHS_SFZ: splitter.join(
                qsettings.value(CARLA_KEY_PATHS_SFZ, CARLA_DEFAULT_SFZ_PATH, list)
            ),
            CARLA_KEY_PATHS_JSFX: splitter.join(
                qsettings.value(CARLA_KEY_PATHS_JSFX, CARLA_DEFAULT_JSFX_PATH, list)
            ),
            CARLA_KEY_PATHS_CLAP: splitter.join(
                qsettings.value(CARLA_KEY_PATHS_CLAP, CARLA_DEFAULT_CLAP_PATH, list)
            ),
            # osc
            CARLA_KEY_OSC_ENABLED: qsettings.value(
                CARLA_KEY_OSC_ENABLED, CARLA_DEFAULT_OSC_ENABLED, bool
            ),
            CARLA_KEY_OSC_TCP_PORT_ENABLED: qsettings.value(
                CARLA_KEY_OSC_TCP_PORT_ENABLED, CARLA_DEFAULT_OSC_TCP_PORT_ENABLED, bool
            ),
            CARLA_KEY_OSC_TCP_PORT_RANDOM: qsettings.value(
                CARLA_KEY_OSC_TCP_PORT_RANDOM, CARLA_DEFAULT_OSC_TCP_PORT_RANDOM, bool
            ),
            CARLA_KEY_OSC_TCP_PORT_NUMBER: qsettings.value(
                CARLA_KEY_OSC_TCP_PORT_NUMBER, CARLA_DEFAULT_OSC_TCP_PORT_NUMBER, int
            ),
            CARLA_KEY_OSC_UDP_PORT_ENABLED: qsettings.value(
                CARLA_KEY_OSC_UDP_PORT_ENABLED, CARLA_DEFAULT_OSC_UDP_PORT_ENABLED, bool
            ),
            CARLA_KEY_OSC_UDP_PORT_RANDOM: qsettings.value(
                CARLA_KEY_OSC_UDP_PORT_RANDOM, CARLA_DEFAULT_OSC_UDP_PORT_RANDOM, bool
            ),
            CARLA_KEY_OSC_UDP_PORT_NUMBER: qsettings.value(
                CARLA_KEY_OSC_UDP_PORT_NUMBER, CARLA_DEFAULT_OSC_UDP_PORT_NUMBER, int
            ),
            # wine
            CARLA_KEY_WINE_EXECUTABLE: qsettings.value(
                CARLA_KEY_WINE_EXECUTABLE, CARLA_DEFAULT_WINE_EXECUTABLE, str
            ),
            CARLA_KEY_WINE_AUTO_PREFIX: qsettings.value(
                CARLA_KEY_WINE_AUTO_PREFIX, CARLA_DEFAULT_WINE_AUTO_PREFIX, bool
            ),
            CARLA_KEY_WINE_FALLBACK_PREFIX: qsettings.value(
                CARLA_KEY_WINE_FALLBACK_PREFIX, CARLA_DEFAULT_WINE_FALLBACK_PREFIX, str
            ),
            CARLA_KEY_WINE_RT_PRIO_ENABLED: qsettings.value(
                CARLA_KEY_WINE_RT_PRIO_ENABLED, CARLA_DEFAULT_WINE_RT_PRIO_ENABLED, bool
            ),
            CARLA_KEY_WINE_BASE_RT_PRIO: qsettings.value(
                CARLA_KEY_WINE_BASE_RT_PRIO, CARLA_DEFAULT_WINE_BASE_RT_PRIO, int
            ),
            CARLA_KEY_WINE_SERVER_RT_PRIO: qsettings.value(
                CARLA_KEY_WINE_SERVER_RT_PRIO, CARLA_DEFAULT_WINE_SERVER_RT_PRIO, int
            ),
        }

    # -----------------------------------------------------------------------------------------------------------------
    # main settings

    setHostSettings(host)

    # -----------------------------------------------------------------------------------------------------------------
    # file paths

    host.set_engine_option(
        ENGINE_OPTION_FILE_PATH, FILE_AUDIO, settings[CARLA_KEY_PATHS_AUDIO]
    )
    host.set_engine_option(
        ENGINE_OPTION_FILE_PATH, FILE_MIDI, settings[CARLA_KEY_PATHS_MIDI]
    )

    # -----------------------------------------------------------------------------------------------------------------
    # plugin paths

    host.set_engine_option(
        ENGINE_OPTION_PLUGIN_PATH, PLUGIN_LADSPA, settings[CARLA_KEY_PATHS_LADSPA]
    )
    host.set_engine_option(
        ENGINE_OPTION_PLUGIN_PATH, PLUGIN_DSSI, settings[CARLA_KEY_PATHS_DSSI]
    )
    host.set_engine_option(
        ENGINE_OPTION_PLUGIN_PATH, PLUGIN_LV2, settings[CARLA_KEY_PATHS_LV2]
    )
    host.set_engine_option(
        ENGINE_OPTION_PLUGIN_PATH, PLUGIN_VST2, settings[CARLA_KEY_PATHS_VST2]
    )
    host.set_engine_option(
        ENGINE_OPTION_PLUGIN_PATH, PLUGIN_VST3, settings[CARLA_KEY_PATHS_VST3]
    )
    host.set_engine_option(
        ENGINE_OPTION_PLUGIN_PATH, PLUGIN_SF2, settings[CARLA_KEY_PATHS_SF2]
    )
    host.set_engine_option(
        ENGINE_OPTION_PLUGIN_PATH, PLUGIN_SFZ, settings[CARLA_KEY_PATHS_SFZ]
    )
    host.set_engine_option(
        ENGINE_OPTION_PLUGIN_PATH, PLUGIN_JSFX, settings[CARLA_KEY_PATHS_JSFX]
    )
    host.set_engine_option(
        ENGINE_OPTION_PLUGIN_PATH, PLUGIN_CLAP, settings[CARLA_KEY_PATHS_CLAP]
    )

    # -----------------------------------------------------------------------------------------------------------------
    # don't continue if plugin

    if host.isPlugin:
        return "Plugin"

    # -----------------------------------------------------------------------------------------------------------------
    # osc settings

    if oscPort is not None and isinstance(oscPort, int):
        oscEnabled = True
        portNumTCP = portNumUDP = oscPort

    else:
        oscEnabled = settings[CARLA_KEY_OSC_ENABLED]

        if not settings[CARLA_KEY_OSC_TCP_PORT_ENABLED]:
            portNumTCP = -1
        elif settings[CARLA_KEY_OSC_TCP_PORT_RANDOM]:
            portNumTCP = 0
        else:
            portNumTCP = settings[CARLA_KEY_OSC_TCP_PORT_NUMBER]

        if not settings[CARLA_KEY_OSC_UDP_PORT_ENABLED]:
            portNumUDP = -1
        elif settings[CARLA_KEY_OSC_UDP_PORT_RANDOM]:
            portNumUDP = 0
        else:
            portNumUDP = settings[CARLA_KEY_OSC_UDP_PORT_NUMBER]

    host.set_engine_option(ENGINE_OPTION_OSC_ENABLED, 1 if oscEnabled else 0, "")
    host.set_engine_option(ENGINE_OPTION_OSC_PORT_TCP, portNumTCP, "")
    host.set_engine_option(ENGINE_OPTION_OSC_PORT_UDP, portNumUDP, "")

    # -----------------------------------------------------------------------------------------------------------------
    # wine settings

    host.set_engine_option(
        ENGINE_OPTION_WINE_EXECUTABLE, 0, settings[CARLA_KEY_WINE_EXECUTABLE]
    )
    host.set_engine_option(
        ENGINE_OPTION_WINE_AUTO_PREFIX,
        1 if settings[CARLA_KEY_WINE_AUTO_PREFIX] else 0,
        "",
    )
    host.set_engine_option(
        ENGINE_OPTION_WINE_FALLBACK_PREFIX,
        0,
        os.path.expanduser(settings[CARLA_KEY_WINE_FALLBACK_PREFIX]),
    )
    host.set_engine_option(
        ENGINE_OPTION_WINE_RT_PRIO_ENABLED,
        1 if settings[CARLA_KEY_WINE_RT_PRIO_ENABLED] else 0,
        "",
    )
    host.set_engine_option(
        ENGINE_OPTION_WINE_BASE_RT_PRIO, settings[CARLA_KEY_WINE_BASE_RT_PRIO], ""
    )
    host.set_engine_option(
        ENGINE_OPTION_WINE_SERVER_RT_PRIO, settings[CARLA_KEY_WINE_SERVER_RT_PRIO], ""
    )

    # -----------------------------------------------------------------------------------------------------------------
    # driver and device settings

    # driver name
    audioDriver = settings[CARLA_KEY_ENGINE_AUDIO_DRIVER]

    # Only setup audio things if engine is not running
    if not host.is_engine_running():
        host.set_engine_option(ENGINE_OPTION_AUDIO_DRIVER, 0, audioDriver)
        host.set_engine_option(
            ENGINE_OPTION_AUDIO_DEVICE, 0, settings[CARLA_KEY_ENGINE_AUDIO_DEVICE]
        )

        if not audioDriver.startswith("JACK"):
            host.set_engine_option(
                ENGINE_OPTION_AUDIO_BUFFER_SIZE,
                settings[CARLA_KEY_ENGINE_BUFFER_SIZE],
                "",
            )
            host.set_engine_option(
                ENGINE_OPTION_AUDIO_SAMPLE_RATE,
                settings[CARLA_KEY_ENGINE_SAMPLE_RATE],
                "",
            )
            host.set_engine_option(
                ENGINE_OPTION_AUDIO_TRIPLE_BUFFER,
                1 if settings[CARLA_KEY_ENGINE_TRIPLE_BUFFER] else 0,
                "",
            )

    # -----------------------------------------------------------------------------------------------------------------
    # fix things if needed

    if audioDriver != "JACK" and host.transportMode == ENGINE_TRANSPORT_MODE_JACK:
        host.transportMode = ENGINE_TRANSPORT_MODE_INTERNAL
        host.set_engine_option(
            ENGINE_OPTION_TRANSPORT_MODE,
            ENGINE_TRANSPORT_MODE_INTERNAL,
            host.transportExtra,
        )

    # -----------------------------------------------------------------------------------------------------------------
    # return selected driver name

    return audioDriver


# ---------------------------------------------------------------------------------------------------------------------
# Run Carla without showing UI


def runHostWithoutUI(host):
    # kdevelop likes this :)
    if False:
        host = CarlaHostNull()

    # --------------------------------------------------------------------------------------------------------
    # Some initial checks

    if not gCarla.nogui:
        return

    projectFile = getInitialProjectFile(True)

    if gCarla.nogui is True:
        oscPort = None

        if not projectFile:
            print("Carla no-gui mode can only be used together with a project file.")
            sys.exit(1)

    else:
        oscPort = gCarla.nogui

    # --------------------------------------------------------------------------------------------------------
    # Additional imports

    from time import sleep

    # --------------------------------------------------------------------------------------------------------
    # Init engine

    audioDriver = setEngineSettings(host, None, oscPort)
    if not host.engine_init(audioDriver, CARLA_CLIENT_NAME or "Carla"):
        print(
            f"Engine failed to initialize, possible reasons:\n{host.get_last_error()}"
        )
        sys.exit(1)

    if projectFile and not host.load_project(projectFile):
        print(
            f"Failed to load selected project file, possible reasons:\n{host.get_last_error()}"
        )
        host.engine_close()
        sys.exit(1)

    # --------------------------------------------------------------------------------------------------------
    # Idle

    print("Carla ready!")

    while host.is_engine_running() and not gCarla.term:
        host.engine_idle()
        sleep(0.0333)  # 30 Hz

    # --------------------------------------------------------------------------------------------------------
    # Stop

    host.engine_close()
    sys.exit(0)


