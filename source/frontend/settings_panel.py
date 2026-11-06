#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Clara contributors
# SPDX-License-Identifier: GPL-2.0-or-later

# Settings dialog persistence and menu actions, split out of host_app.py.
# HostWindow inherits this mixin.

import os

from carla_app import *
from carla_shared import *
from carla_settings import CarlaSettingsW
from carla_widgets import QByteArray
from qt_compat import QDialog, QMenu, QTimer, QVBoxLayout, pyqtSlot

try:
    from qt_compat import QGLWidget

    hasGL = QGLWidget is not None
except ImportError:
    QGLWidget = None
    hasGL = False


class SettingsMixin:
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

        from host_app import setEngineSettings  # lazy: host_app imports this mixin

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

