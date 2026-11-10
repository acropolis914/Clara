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


from driver_settings import DriverSettingsW, RuntimeDriverSettingsW

_GLYPH_ICON_CACHE = {}


class CarlaSettingsW(QDialog):
    # Tab indexes
    TAB_INDEX_MAIN = 0
    TAB_INDEX_CANVAS = 1
    TAB_INDEX_ENGINE = 2
    TAB_INDEX_OSC = 3
    TAB_INDEX_FILEPATHS = 4
    TAB_INDEX_PLUGINPATHS = 5
    TAB_INDEX_WINE = 6
    TAB_INDEX_EXPERIMENTAL = 7
    TAB_INDEX_NONE = 8

    # File Path indexes
    FILEPATH_INDEX_AUDIO = 0
    FILEPATH_INDEX_MIDI = 1

    # Plugin Path indexes
    PLUGINPATH_INDEX_LADSPA = 0
    PLUGINPATH_INDEX_DSSI = 1
    PLUGINPATH_INDEX_LV2 = 2
    PLUGINPATH_INDEX_VST2 = 3
    PLUGINPATH_INDEX_VST3 = 4
    PLUGINPATH_INDEX_SF2 = 5
    PLUGINPATH_INDEX_SFZ = 6
    PLUGINPATH_INDEX_JSFX = 7
    PLUGINPATH_INDEX_CLAP = 8

    # Single and Multiple client mode is only for JACK,
    # but we still want to match QComboBox index to backend defines,
    # so add +2 pos padding if driverName != "JACK".
    PROCESS_MODE_NON_JACK_PADDING = 2

    # -----------------------------------------------------------------------------------------------------------------

    @staticmethod
    def _make_glyph_icon(glyph, size=18, color=None):
        if not color:
            try:
                from styles.theme_manager import theme_manager
                color = theme_manager.engine.get_token("accent") or "#89b4fa"
            except Exception:
                app = QApplication.instance()
                color = app.palette().color(QPalette.Highlight).name() if app else "#89b4fa"
        if not color:
            color = "#89b4fa"
        from carla_shared import getBestNerdFont
        nerd_family = getBestNerdFont()
        cache_key = (glyph, size, nerd_family, color)
        if cache_key in _GLYPH_ICON_CACHE:
            return _GLYPH_ICON_CACHE[cache_key]
        if not nerd_family:
            return QIcon()
        from qt_compat import QPixmap, QPainter, QColor, QImage, QRect
        font_size = max(9, int(size * 0.72))
        font = QFont(nerd_family, font_size)

        # Probe exact ink bounding box for optical centering
        img = QImage(size, size, QImage.Format_ARGB32)
        img.fill(0)
        probe = QPainter(img)
        probe.setFont(font)
        probe.setPen(QColor(255, 255, 255))
        probe.drawText(QRect(0, 0, size, size), Qt.AlignCenter, glyph)
        probe.end()

        min_x, max_x = size, -1
        min_y, max_y = size, -1
        for y in range(size):
            for x in range(size):
                if (img.pixel(x, y) >> 24) & 0xFF > 20:
                    if x < min_x:
                        min_x = x
                    if x > max_x:
                        max_x = x
                    if y < min_y:
                        min_y = y
                    if y > max_y:
                        max_y = y

        if max_x != -1:
            cx = (min_x + max_x) / 2.0
            cy = (min_y + max_y) / 2.0
            dx = int(round((size - 1) / 2.0 - cx))
            dy = int(round((size - 1) / 2.0 - cy))
        else:
            dx, dy = 0, 0

        pm = QPixmap(size, size)
        pm.fill(QColor(0, 0, 0, 0))
        p = QPainter(pm)
        p.setFont(font)
        p.setPen(QColor(color))
        draw_rect = QRect(0, 0, size, size).translated(dx, dy)
        p.drawText(draw_rect, Qt.AlignCenter, glyph)
        p.end()
        icon = QIcon(pm)
        _GLYPH_ICON_CACHE[cache_key] = icon
        return icon

    def _update_sidebar_icons(self):
        tab_titles = [
            self.tr("General"),
            self.tr("Patchbay"),
            self.tr("Engine"),
            self.tr("OSC"),
            self.tr("File Paths"),
            self.tr("Plugin Paths"),
            self.tr("Wine"),
            self.tr("Experimental"),
        ]
        tab_glyphs = [
            "\uf013",  # nf-fa-cog          General
            "\uf0e8",  # nf-fa-sitemap      Patchbay
            "\uf085",  # nf-fa-cogs         Engine
            "\uf0ac",  # nf-fa-globe        OSC
            "\uf07b",  # nf-fa-folder       File Paths
            "\uf12e",  # nf-fa-puzzle-piece Plugin Paths
            "\uf000",  # nf-fa-glass        Wine
            "\uf0eb",  # nf-fa-lightbulb    Experimental
        ]
        try:
            from carla_shared import getBestNerdFont
            nerd_family = getBestNerdFont()
        except Exception:
            nerd_family = ""

        sidebar_font = self.ui.lw_page.font()
        sidebar_font.setPointSize(11)
        sidebar_font.setBold(True)

        for row in range(self.ui.lw_page.rowCount()):
            item = self.ui.lw_page.item(row, 0)
            if item is not None and row < len(tab_titles):
                if nerd_family and row < len(tab_glyphs):
                    item.setIcon(self._make_glyph_icon(tab_glyphs[row]))
                item.setText(tab_titles[row])
                item.setFont(sidebar_font)

    def __init__(self, parent, host, hasCanvas, hasCanvasGL):
        QDialog.__init__(self, parent)
        self.host = host
        self.ui = ui_carla_settings.Ui_CarlaSettingsW()
        self.ui.setupUi(self)

        # -------------------------------------------------------------------------------------------------------------
        # Set-up GUI

        # Modern compact sidebar layout & styling
        self.ui.lw_page.setIconSize(QSize(18, 18))
        self.ui.lw_page.setFixedWidth(195)
        self.ui.lw_page.setShowGrid(False)
        stretch_mode = getattr(QHeaderView.ResizeMode, "Stretch", None) if hasattr(QHeaderView, "ResizeMode") else getattr(QHeaderView, "Stretch", 1)
        self.ui.lw_page.horizontalHeader().setSectionResizeMode(stretch_mode)
        self.ui.lw_page.verticalHeader().setDefaultSectionSize(36)

        sidebar_font = self.ui.lw_page.font()
        sidebar_font.setPointSize(11)
        sidebar_font.setBold(True)
        self.ui.lw_page.setFont(sidebar_font)

        # Tab titles with refined typography (applied by _update_sidebar_icons)
        self._update_sidebar_icons()

        # Remove hideous page header glyphs (upper-right corner of every tab)
        for icon_attr in (
            "label_icon_main",
            "label_10",             # Canvas
            "label_icon_engine",    # Engine
            "label_icon_engine_5",  # OSC
            "label_31",             # File Paths
            "label_19",             # Plugin Paths
            "label_icon_wine",      # Wine
            "label_icon_experimental",
        ):
            if hasattr(self.ui, icon_attr):
                getattr(self.ui, icon_attr).hide()

        # Remove the legacy 16px info / warning glyphs (their descriptive text stays)
        for glyph_attr in (
            "label_22", "label_39", "label_41", "label_32",
            "label_4", "label_26", "label_37", "label_16",
        ):
            if hasattr(self.ui, glyph_attr):
                getattr(self.ui, glyph_attr).hide()

        # Deprecated option: its toggled handler is disabled upstream
        if hasattr(self.ui, "cb_canvas_fancy_eyecandy"):
            self.ui.cb_canvas_fancy_eyecandy.hide()

        # Legacy / superseded options that are no longer worth exposing
        for legacy_attr in (
            "group_experimental_canvas", # Canvas settings are unified under Patchbay tab
            "cb_canvas_full_repaints",   # slow workaround, superseded by modern rendering
            "ch_exp_load_lib_global",    # explicitly "NOT RECOMMENDED"
        ):
            if hasattr(self.ui, legacy_attr):
                getattr(self.ui, legacy_attr).hide()

        # Let the help / descriptive text wrap instead of clipping into one unreadable
        # line. heightForWidth is enabled so the layout reserves the wrapped height and
        # the text never overlaps itself / the row below.
        for help_attr in (
            "label_23", "label_40", "label_42", "label_35", "label_38",
            "label_12", "label_13", "label_5", "label_30", "label_27",
            "label_17", "label_engine_ui_bridges_mac_note",
        ):
            if hasattr(self.ui, help_attr):
                lbl = getattr(self.ui, help_attr)
                lbl.setWordWrap(True)
                lbl.setAlignment(Qt.AlignLeft | Qt.AlignTop)
                _pol = lbl.sizePolicy()
                _pol.setHeightForWidth(True)
                lbl.setSizePolicy(_pol)
                lbl.setProperty("role", "help")

        # Dialog inherits theme from ThemeManager / QApplication stylesheet

        for i in range(host.get_engine_driver_count()):
            self.ui.cb_engine_audio_driver.addItem(host.get_engine_driver_name(i))

        for i in range(Theme.THEME_MAX):
            self.ui.cb_canvas_theme.addItem(getThemeName(i))

        if CARLA_OS_MAC:
            self.ui.group_main_theme.setEnabled(False)
            self.ui.group_main_theme.setVisible(False)

        if CARLA_OS_WIN or host.isControl:
            self.ui.ch_main_show_logs.setEnabled(False)
            self.ui.ch_main_show_logs.setVisible(False)

        if host.isControl:
            self.ui.lw_page.hideRow(self.TAB_INDEX_ENGINE)
            self.ui.lw_page.hideRow(self.TAB_INDEX_FILEPATHS)
            self.ui.lw_page.hideRow(self.TAB_INDEX_PLUGINPATHS)
            self.ui.ch_exp_export_lv2.hide()
            self.ui.group_experimental_engine.hide()
            self.ui.cb_canvas_inline_displays.hide()

        elif not hasCanvas:
            self.ui.lw_page.hideRow(self.TAB_INDEX_CANVAS)

        elif not hasCanvasGL:
            self.ui.cb_canvas_use_opengl.setEnabled(False)
            self.ui.cb_canvas_render_hq_aa.setEnabled(False)

        # Build clean declarative 2-column settings pages
        # 1. General Tab
        if hasattr(self.ui, "page_main"):
            for old_grp in ("label_main", "group_main_paths", "group_main_theme", "group_main_misc", "group_main_experimental", "label_icon_main", "label", "label_2", "label_3"):
                if hasattr(self.ui, old_grp):
                    getattr(self.ui, old_grp).hide()
            self.general_form_builder = SettingsFormBuilder(self, GENERAL_SCHEMA)
            self.general_form_builder.build_page(self.ui.page_main)
            
            # Live update hooks for rack spacing sliders
            if "rack_spacing" in self.general_form_builder.widgets:
                def _on_live_rack_spacing(val):
                    if hasattr(gCarla, "gui") and gCarla.gui is not None and hasattr(gCarla.gui.ui, "listWidget"):
                        gCarla.gui.ui.listWidget.setSpacing(val)
                self.general_form_builder.widgets["rack_spacing"].valueChanged.connect(_on_live_rack_spacing)

            if "rack_padding" in self.general_form_builder.widgets:
                def _on_live_rack_padding(val):
                    if hasattr(gCarla, "gui") and gCarla.gui is not None and hasattr(gCarla.gui.ui, "listWidget"):
                        lw = gCarla.gui.ui.listWidget
                        for i in range(lw.count()):
                            item = lw.item(i)
                            if hasattr(item, "fWidget") and item.fWidget is not None:
                                w = item.fWidget
                                if hasattr(w, "ui") and hasattr(w.ui, "verticalLayout"):
                                    w.ui.verticalLayout.setContentsMargins(14, val, 6, val)
                                    if hasattr(w, "updateRackItemSize"):
                                        w.updateRackItemSize()
                self.general_form_builder.widgets["rack_padding"].valueChanged.connect(_on_live_rack_padding)

            if "rack_min_width" in self.general_form_builder.widgets:
                def _on_live_rack_min_width(val):
                    if hasattr(gCarla, "gui") and gCarla.gui is not None and hasattr(gCarla.gui.ui, "listWidget"):
                        from widgets.racklistwidget import RackListItem
                        RackListItem.kMinimumWidth = val
                        gCarla.gui.ui.listWidget.setMinimumWidth(val)
                        lw = gCarla.gui.ui.listWidget
                        for i in range(lw.count()):
                            item = lw.item(i)
                            if hasattr(item, "fWidget") and item.fWidget is not None:
                                w = item.fWidget
                                if hasattr(w, "setMinimumWidth"):
                                    w.setMinimumWidth(val)
                self.general_form_builder.widgets["rack_min_width"].valueChanged.connect(_on_live_rack_min_width)

            if "show_statusbar" in self.general_form_builder.widgets:
                def _on_live_statusbar_toggle(checked):
                    if hasattr(gCarla, "gui") and gCarla.gui is not None and hasattr(gCarla.gui.ui, "statusbar"):
                        gCarla.gui.ui.statusbar.setVisible(checked)
                self.general_form_builder.widgets["show_statusbar"].toggled.connect(_on_live_statusbar_toggle)

            # Populate dynamic theme list and connect live theme switching
            if "app_theme" in self.general_form_builder.widgets and "use_system_theme" in self.general_form_builder.widgets:
                from styles.theme_manager import theme_manager
                cb_theme = self.general_form_builder.widgets["app_theme"]
                ch_sys = self.general_form_builder.widgets["use_system_theme"]
                
                # Refresh available themes dynamically from disk
                current_text = cb_theme.currentText()
                cb_theme.clear()
                avail_themes = theme_manager.get_available_themes()
                cb_theme.addItems(avail_themes)
                if current_text and cb_theme.findText(current_text) >= 0:
                    cb_theme.setCurrentText(current_text)

                self._theme_apply_timer = QTimer(self)
                self._theme_apply_timer.setSingleShot(True)
                self._theme_apply_timer.setInterval(120)

                def _apply_live_theme():
                    use_system = ch_sys.isChecked()
                    chosen_theme = cb_theme.currentText()
                    theme_manager.apply_theme(chosen_theme, use_system=use_system)
                    self._update_sidebar_icons()
                    try:
                        from carla_shared import gCarla
                        if hasattr(gCarla, "gui") and gCarla.gui is not None and hasattr(gCarla.gui, "_update_split_tab_views"):
                            gCarla.gui._update_split_tab_views()
                    except Exception:
                        pass

                self._theme_apply_timer.timeout.connect(_apply_live_theme)

                def _on_live_theme_change(*_):
                    self._theme_apply_timer.start()

                ch_sys.toggled.connect(_on_live_theme_change)
                cb_theme.activated.connect(_on_live_theme_change)
                cb_theme.currentIndexChanged.connect(_on_live_theme_change)
        else:
            self.general_form_builder = None

        # Declarative schema form builders (Patchbay, OSC, Wine, Experimental are built lazily)
        self._built_tabs = {self.TAB_INDEX_MAIN}
        self.canvas_form_builder = None
        self.osc_form_builder = None
        self.wine_form_builder = None
        self.experimental_form_builder = None

        if host.isPlugin:
            self.ui.cb_engine_audio_driver.setEnabled(False)

        if host.audioDriverForced is not None:
            self.ui.cb_engine_audio_driver.setEnabled(False)
            self.ui.tb_engine_driver_config.setEnabled(False)

        if host.processModeForced:
            self.ui.cb_engine_process_mode_jack.setEnabled(False)
            self.ui.cb_engine_process_mode_other.setEnabled(False)

            if self.host.processMode == ENGINE_PROCESS_MODE_CONTINUOUS_RACK:
                self.ui.ch_engine_force_stereo.setEnabled(False)

        if host.isControl or host.isPlugin:
            self.ui.ch_main_confirm_exit.hide()
            self.ui.ch_exp_load_lib_global.hide()
            self.ui.lw_page.hideRow(self.TAB_INDEX_OSC)
            self.ui.lw_page.hideRow(self.TAB_INDEX_WINE)

        if not CARLA_OS_LINUX:
            self.ui.ch_exp_wine_bridges.setVisible(False)
            self.ui.ch_exp_prevent_bad_behaviour.setVisible(False)
            self.ui.lw_page.hideRow(self.TAB_INDEX_WINE)

        if not CARLA_OS_MAC:
            self.ui.label_engine_ui_bridges_mac_note.setVisible(False)

        if not (CARLA_OS_LINUX or CARLA_OS_MAC):
            self.ui.ch_exp_jack_apps.setVisible(False)

        self.ui.ch_engine_uis_always_on_top.hide()

        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)


        if CARLA_OS_MAC:
            self.setWindowModality(Qt.WindowModal)

        # -------------------------------------------------------------------------------------------------------------
        # Load settings

        self.loadSettings()

        # -------------------------------------------------------------------------------------------------------------
        # Set-up Icons

        try:
            from carla_shared import getBestNerdFont
            _nerd = getBestNerdFont()
        except Exception:
            _nerd = ""

        if _nerd:
            # Modern Nerd Font glyph buttons with optical centering
            for _btn, _glyph in (
                (self.ui.b_main_proj_folder_open, "\uf07c"),  # nf-fa-folder-open
                (self.ui.b_filepaths_add, "\uf067"),          # nf-fa-plus
                (self.ui.b_filepaths_change, "\uf040"),       # nf-fa-pencil
                (self.ui.b_filepaths_remove, "\uf068"),       # nf-fa-minus
                (self.ui.b_paths_add, "\uf067"),
                (self.ui.b_paths_change, "\uf040"),
                (self.ui.b_paths_remove, "\uf068"),
            ):
                if _btn is not None:
                    _btn.setText("")
                    from styles.theme_manager import theme_manager
                    _btn.setIcon(self._make_glyph_icon(
                        _glyph, 16, color=theme_manager.engine.get_token("text-primary", "#cdd6f4")))
        elif self.ui.ch_main_system_icons.isChecked():
            self.ui.b_main_proj_folder_open.setIcon(
                getIcon("document-open", 16, "svgz")
            )
            self.ui.b_filepaths_add.setIcon(getIcon("list-add", 16, "svgz"))
            self.ui.b_filepaths_change.setIcon(getIcon("edit-rename", 16, "svgz"))
            self.ui.b_filepaths_remove.setIcon(getIcon("list-remove", 16, "svgz"))
            self.ui.b_paths_add.setIcon(getIcon("list-add", 16, "svgz"))
            self.ui.b_paths_change.setIcon(getIcon("edit-rename", 16, "svgz"))
            self.ui.b_paths_remove.setIcon(getIcon("list-remove", 16, "svgz"))

        # -------------------------------------------------------------------------------------------------------------
        # Set-up connections

        self.accepted.connect(self.slot_saveSettings)
        self.ui.buttonBox.addButton(QDialogButtonBox.Apply).clicked.connect(
            self.slot_applySettings
        )
        self.ui.buttonBox.button(QDialogButtonBox.Reset).clicked.connect(
            self.slot_resetSettings
        )

        self.ui.b_main_proj_folder_open.clicked.connect(self.slot_getAndSetProjectPath)

        self.ui.cb_engine_audio_driver.currentIndexChanged.connect(
            self.slot_engineAudioDriverChanged
        )
        self.ui.tb_engine_driver_config.clicked.connect(
            self.slot_showAudioDriverSettings
        )

        self.ui.b_paths_add.clicked.connect(self.slot_addPluginPath)
        self.ui.b_paths_remove.clicked.connect(self.slot_removePluginPath)
        self.ui.b_paths_change.clicked.connect(self.slot_changePluginPath)
        self.ui.cb_paths.currentIndexChanged.connect(self.slot_pluginPathTabChanged)
        self.ui.lw_ladspa.currentRowChanged.connect(self.slot_pluginPathRowChanged)
        self.ui.lw_dssi.currentRowChanged.connect(self.slot_pluginPathRowChanged)
        self.ui.lw_lv2.currentRowChanged.connect(self.slot_pluginPathRowChanged)
        self.ui.lw_vst.currentRowChanged.connect(self.slot_pluginPathRowChanged)
        self.ui.lw_vst3.currentRowChanged.connect(self.slot_pluginPathRowChanged)
        self.ui.lw_sf2.currentRowChanged.connect(self.slot_pluginPathRowChanged)
        self.ui.lw_sfz.currentRowChanged.connect(self.slot_pluginPathRowChanged)
        self.ui.lw_jsfx.currentRowChanged.connect(self.slot_pluginPathRowChanged)
        self.ui.lw_clap.currentRowChanged.connect(self.slot_pluginPathRowChanged)

        self.ui.b_filepaths_add.clicked.connect(self.slot_addFilePath)
        self.ui.b_filepaths_remove.clicked.connect(self.slot_removeFilePath)
        self.ui.b_filepaths_change.clicked.connect(self.slot_changeFilePath)
        self.ui.cb_filepaths.currentIndexChanged.connect(self.slot_filePathTabChanged)
        self.ui.lw_files_audio.currentRowChanged.connect(self.slot_filePathRowChanged)
        self.ui.lw_files_midi.currentRowChanged.connect(self.slot_filePathRowChanged)

        self.ui.ch_main_experimental.toggled.connect(self.slot_enableExperimental)
        self.ui.ch_exp_wine_bridges.toggled.connect(self.slot_enableWineBridges)
        self.ui.cb_exp_plugin_bridges.toggled.connect(self.slot_pluginBridgesToggled)
        self.ui.cb_canvas_eyecandy.toggled.connect(self.slot_canvasEyeCandyToggled)
        self.ui.cb_canvas_fancy_eyecandy.toggled.connect(self.slot_canvasFancyEyeCandyToggled)
        self.ui.cb_canvas_use_opengl.toggled.connect(self.slot_canvasOpenGLToggled)
        if hasattr(self.ui, "cb_canvas_rounded_nodes"):
            self.ui.cb_canvas_rounded_nodes.toggled.connect(
                self.ui.sl_canvas_node_radius.setEnabled
            )
            self.ui.cb_canvas_rounded_nodes.toggled.connect(
                self.ui.label_canvas_node_radius.setEnabled
            )
            self.ui.sl_canvas_node_radius.valueChanged.connect(
                lambda v: self.ui.label_canvas_node_radius.setText(f"{v} px")
            )

        self.ui.stackedWidget.currentChanged.connect(self._ensure_tab_built)

        # -------------------------------------------------------------------------------------------------------------
        # Post-connect setup

        self.ui.lw_ladspa.setCurrentRow(0)
        self.ui.lw_dssi.setCurrentRow(0)
        self.ui.lw_lv2.setCurrentRow(0)
        self.ui.lw_vst.setCurrentRow(0)
        self.ui.lw_vst3.setCurrentRow(0)
        self.ui.lw_sf2.setCurrentRow(0)
        self.ui.lw_sfz.setCurrentRow(0)
        self.ui.lw_jsfx.setCurrentRow(0)
        self.ui.lw_clap.setCurrentRow(0)

        self.ui.lw_files_audio.setCurrentRow(0)
        self.ui.lw_files_midi.setCurrentRow(0)

        self.ui.lw_page.setCurrentCell(0, 0)

        self.slot_filePathTabChanged(0)
        self.slot_pluginPathTabChanged(0)

        self.adjustSize()

    # -----------------------------------------------------------------------------------------------------------------

    @pyqtSlot(int)
    def _ensure_tab_built(self, index):
        if index in self._built_tabs:
            return

        settings = QSafeSettings("falkTX", "Carla2")

        if index == self.TAB_INDEX_CANVAS and hasattr(self.ui, "page_canvas"):
            self._built_tabs.add(index)
            for old_grp in ("label_9", "label_10", "group_canvas_theme", "group_canvas_options", "group_canvas_render"):
                if hasattr(self.ui, old_grp):
                    getattr(self.ui, old_grp).hide()
            self.canvas_form_builder = SettingsFormBuilder(self, PATCHBAY_SCHEMA)
            self.canvas_form_builder.build_page(self.ui.page_canvas)
            self.canvas_form_builder.load_values(settings)

        elif index == self.TAB_INDEX_OSC and hasattr(self.ui, "page_osc"):
            self._built_tabs.add(index)
            for old_grp in ("label_14", "label_36", "label_icon_engine_5", "label_20", "label_21", "group_osc_core", "group_osc_tcp_port", "group_osc_udp_port", "ch_osc_enable"):
                if hasattr(self.ui, old_grp):
                    getattr(self.ui, old_grp).hide()
            self.osc_form_builder = SettingsFormBuilder(self, OSC_SCHEMA)
            self.osc_form_builder.build_page(self.ui.page_osc)
            self.osc_form_builder.load_values(settings)

        elif index == self.TAB_INDEX_WINE and hasattr(self.ui, "page_wine"):
            self._built_tabs.add(index)
            for old_grp in ("label_29", "label_icon_wine", "label_36", "label_26", "label_27", "label_28", "group_wine_exec", "group_wine_prefix", "group_wine_environment", "group_wine_realtime"):
                if hasattr(self.ui, old_grp):
                    getattr(self.ui, old_grp).hide()
            self.wine_form_builder = SettingsFormBuilder(self, WINE_SCHEMA)
            self.wine_form_builder.build_page(self.ui.page_wine)
            self.wine_form_builder.load_values(settings)

        elif index == self.TAB_INDEX_EXPERIMENTAL and hasattr(self.ui, "page_experimental"):
            self._built_tabs.add(index)
            for old_grp in ("label_11", "label_icon_experimental", "label_16", "label_17", "label_25", "group_experimental_main", "group_experimental_canvas", "group_experimental_engine"):
                if hasattr(self.ui, old_grp):
                    getattr(self.ui, old_grp).hide()
            self.experimental_form_builder = SettingsFormBuilder(self, EXPERIMENTAL_SCHEMA)
            self.experimental_form_builder.build_page(self.ui.page_experimental)
            self.experimental_form_builder.load_values(settings)


    # -----------------------------------------------------------------------------------------------------------------

    def loadSettings(self):
        settings = QSafeSettings("falkTX", "Carla2")

        # -------------------------------------------------------------------------------------------------------------
        # General & Canvas

        if getattr(self, "general_form_builder", None) is not None:
            self.general_form_builder.load_values(settings)

        if getattr(self, "canvas_form_builder", None) is not None:
            self.canvas_form_builder.load_values(settings)

        # -------------------------------------------------------------------------------------------------------------

        # Main

        self.ui.ch_main_experimental.setChecked(self.host.experimental)

        if not self.host.experimental:
            self.ui.lw_page.hideRow(self.TAB_INDEX_EXPERIMENTAL)
            self.ui.lw_page.hideRow(self.TAB_INDEX_WINE)

        elif not self.host.showWineBridges:
            self.ui.lw_page.hideRow(self.TAB_INDEX_WINE)

        # -------------------------------------------------------------------------------------------------------------
        # Engine

        if self.host.isPlugin:
            audioDriver = "Plugin"
            self.ui.cb_engine_audio_driver.setCurrentIndex(0)
        elif self.host.audioDriverForced:
            audioDriver = self.host.audioDriverForced
            self.ui.cb_engine_audio_driver.setCurrentIndex(0)
        else:
            audioDriver = settings.value(
                CARLA_KEY_ENGINE_AUDIO_DRIVER, CARLA_DEFAULT_AUDIO_DRIVER, str
            )

            for i in range(self.ui.cb_engine_audio_driver.count()):
                if self.ui.cb_engine_audio_driver.itemText(i) == audioDriver:
                    self.ui.cb_engine_audio_driver.setCurrentIndex(i)
                    break
            else:
                self.ui.cb_engine_audio_driver.setCurrentIndex(-1)

        if audioDriver == "JACK":
            self.ui.sw_engine_process_mode.setCurrentIndex(0)
        else:
            self.ui.sw_engine_process_mode.setCurrentIndex(1)

        self.ui.tb_engine_driver_config.setEnabled(
            self.host.audioDriverForced is None and not self.host.isPlugin
        )

        self.ui.cb_engine_process_mode_jack.setCurrentIndex(self.host.nextProcessMode)

        if self.host.nextProcessMode >= self.PROCESS_MODE_NON_JACK_PADDING:
            self.ui.cb_engine_process_mode_other.setCurrentIndex(
                self.host.nextProcessMode - self.PROCESS_MODE_NON_JACK_PADDING
            )
        else:
            self.ui.cb_engine_process_mode_other.setCurrentIndex(0)

        self.ui.sb_engine_max_params.setValue(self.host.maxParameters)
        self.ui.cb_engine_reset_xruns.setChecked(self.host.resetXruns)
        self.ui.ch_engine_manage_uis.setChecked(self.host.manageUIs)
        self.ui.ch_engine_prefer_ui_bridges.setChecked(self.host.preferUIBridges)
        self.ui.sb_engine_ui_bridges_timeout.setValue(self.host.uiBridgesTimeout)
        self.ui.ch_engine_force_stereo.setChecked(
            self.host.forceStereo or not self.ui.ch_engine_force_stereo.isEnabled()
        )
        self.ui.ch_engine_prefer_plugin_bridges.setChecked(
            self.host.preferPluginBridges
        )
        self.ui.ch_exp_export_lv2.setChecked(self.host.exportLV2)
        self.ui.cb_exp_plugin_bridges.setChecked(self.host.showPluginBridges)
        self.ui.ch_exp_wine_bridges.setChecked(self.host.showWineBridges)

        # -------------------------------------------------------------------------------------------------------------
        # OSC

        if getattr(self, "osc_form_builder", None) is not None:
            self.osc_form_builder.load_values(settings)

        # -------------------------------------------------------------------------------------------------------------
        # File Paths
        self.ui.lw_files_audio.clear()
        self.ui.lw_files_midi.clear()

        audioPaths = list(dict.fromkeys(settings.value(
            CARLA_KEY_PATHS_AUDIO, CARLA_DEFAULT_FILE_PATH_AUDIO, list
        ) or []))
        midiPaths = list(dict.fromkeys(settings.value(
            CARLA_KEY_PATHS_MIDI, CARLA_DEFAULT_FILE_PATH_MIDI, list
        ) or []))

        audioPaths.sort()
        midiPaths.sort()

        for audioPath in audioPaths:
            if not audioPath:
                continue
            self.ui.lw_files_audio.addItem(audioPath)

        for midiPath in midiPaths:
            if not midiPath:
                continue
            self.ui.lw_files_midi.addItem(midiPath)

        # -------------------------------------------------------------------------------------------------------------
        # Plugin Paths
        self.ui.lw_ladspa.clear()
        self.ui.lw_dssi.clear()
        self.ui.lw_lv2.clear()
        self.ui.lw_vst.clear()
        self.ui.lw_vst3.clear()
        self.ui.lw_sf2.clear()
        self.ui.lw_sfz.clear()
        self.ui.lw_jsfx.clear()
        self.ui.lw_clap.clear()

        ladspas = list(dict.fromkeys(settings.value(
            CARLA_KEY_PATHS_LADSPA, CARLA_DEFAULT_LADSPA_PATH, list
        ) or []))
        dssis = list(dict.fromkeys(settings.value(CARLA_KEY_PATHS_DSSI, CARLA_DEFAULT_DSSI_PATH, list) or []))
        lv2s = list(dict.fromkeys(settings.value(CARLA_KEY_PATHS_LV2, CARLA_DEFAULT_LV2_PATH, list) or []))
        vst2s = list(dict.fromkeys(settings.value(CARLA_KEY_PATHS_VST2, CARLA_DEFAULT_VST2_PATH, list) or []))
        vst3s = list(dict.fromkeys(settings.value(CARLA_KEY_PATHS_VST3, CARLA_DEFAULT_VST3_PATH, list) or []))
        sf2s = list(dict.fromkeys(settings.value(CARLA_KEY_PATHS_SF2, CARLA_DEFAULT_SF2_PATH, list) or []))
        sfzs = list(dict.fromkeys(settings.value(CARLA_KEY_PATHS_SFZ, CARLA_DEFAULT_SFZ_PATH, list) or []))
        jsfxs = list(dict.fromkeys(settings.value(CARLA_KEY_PATHS_JSFX, CARLA_DEFAULT_JSFX_PATH, list) or []))
        claps = list(dict.fromkeys(settings.value(CARLA_KEY_PATHS_CLAP, CARLA_DEFAULT_CLAP_PATH, list) or []))

        ladspas.sort()
        dssis.sort()
        lv2s.sort()
        vst2s.sort()
        vst3s.sort()
        sf2s.sort()
        sfzs.sort()
        jsfxs.sort()
        claps.sort()

        for ladspa in ladspas:
            if not ladspa:
                continue
            self.ui.lw_ladspa.addItem(ladspa)

        for dssi in dssis:
            if not dssi:
                continue
            self.ui.lw_dssi.addItem(dssi)

        for lv2 in lv2s:
            if not lv2:
                continue
            self.ui.lw_lv2.addItem(lv2)

        for vst2 in vst2s:
            if not vst2:
                continue
            self.ui.lw_vst.addItem(vst2)

        for vst3 in vst3s:
            if not vst3:
                continue
            self.ui.lw_vst3.addItem(vst3)

        for sf2 in sf2s:
            if not sf2:
                continue
            self.ui.lw_sf2.addItem(sf2)

        for sfz in sfzs:
            if not sfz:
                continue
            self.ui.lw_sfz.addItem(sfz)

        for jsfx in jsfxs:
            if not jsfx:
                continue
            self.ui.lw_jsfx.addItem(jsfx)

        for clap in claps:
            if not clap:
                continue
            self.ui.lw_clap.addItem(clap)

        # -------------------------------------------------------------------------------------------------------------
        # Wine

        if getattr(self, "wine_form_builder", None) is not None:
            self.wine_form_builder.load_values(settings)

        # -------------------------------------------------------------------------------------------------------------
        # Experimental

        if getattr(self, "experimental_form_builder", None) is not None:
            self.experimental_form_builder.load_values(settings)

    # -----------------------------------------------------------------------------------------------------------------

    @pyqtSlot()
    def slot_saveSettings(self):
        settings = QSafeSettings("falkTX", "Carla2")

        self.host.experimental = self.ui.ch_main_experimental.isChecked()

        if not self.host.experimental:
            # Disabling experimental mode resets the experimental page to its
            # defaults, but OpenGL rendering and fancy eye-candy are also
            # exposed as regular Canvas options, so a plain save must not
            # silently turn them off.
            keep_opengl = self.ui.cb_canvas_use_opengl.isChecked()
            keep_hq_aa = self.ui.cb_canvas_render_hq_aa.isChecked()
            keep_fancy = self.ui.cb_canvas_fancy_eyecandy.isChecked()
            self.resetExperimentalSettings()
            self.ui.cb_canvas_use_opengl.setChecked(keep_opengl)
            self.ui.cb_canvas_render_hq_aa.setChecked(keep_hq_aa)
            self.ui.cb_canvas_fancy_eyecandy.setChecked(keep_fancy)

        # -------------------------------------------------------------------------------------------------------------
        # Ensure lazy tab form builders are initialized so all settings save properly
        for _tab_idx in (self.TAB_INDEX_CANVAS, self.TAB_INDEX_OSC, self.TAB_INDEX_WINE, self.TAB_INDEX_EXPERIMENTAL):
            self._ensure_tab_built(_tab_idx)

        # General & Canvas

        if getattr(self, "general_form_builder", None) is not None:
            self.general_form_builder.save_values(settings)

        if getattr(self, "canvas_form_builder", None) is not None:
            self.canvas_form_builder.save_values(settings)

        # -------------------------------------------------------------------------------------------------------------

        # Main

        settings.setValue(CARLA_KEY_MAIN_EXPERIMENTAL, self.host.experimental)

        # -------------------------------------------------------------------------------------------------------------
        # Engine

        audioDriver = self.ui.cb_engine_audio_driver.currentText()

        if (
            audioDriver
            and self.host.audioDriverForced is None
            and not self.host.isPlugin
        ):
            settings.setValue(CARLA_KEY_ENGINE_AUDIO_DRIVER, audioDriver)

        if not self.host.processModeForced:
            # engine sends callback if processMode really changes
            if audioDriver == "JACK":
                self.host.nextProcessMode = (
                    self.ui.cb_engine_process_mode_jack.currentIndex()
                )
            else:
                self.host.nextProcessMode = (
                    self.ui.cb_engine_process_mode_other.currentIndex()
                    + self.PROCESS_MODE_NON_JACK_PADDING
                )

            settings.setValue(CARLA_KEY_ENGINE_PROCESS_MODE, self.host.nextProcessMode)

        self.host.exportLV2 = self.ui.ch_exp_export_lv2.isChecked()
        self.host.forceStereo = self.ui.ch_engine_force_stereo.isChecked()
        self.host.resetXruns = self.ui.cb_engine_reset_xruns.isChecked()
        self.host.maxParameters = self.ui.sb_engine_max_params.value()
        self.host.manageUIs = self.ui.ch_engine_manage_uis.isChecked()
        self.host.preferPluginBridges = (
            self.ui.ch_engine_prefer_plugin_bridges.isChecked()
        )
        self.host.preferUIBridges = self.ui.ch_engine_prefer_ui_bridges.isChecked()
        self.host.showLogs = self.ui.ch_main_show_logs.isChecked()
        self.host.showPluginBridges = self.ui.cb_exp_plugin_bridges.isChecked()
        self.host.showWineBridges = self.ui.ch_exp_wine_bridges.isChecked()
        self.host.uiBridgesTimeout = self.ui.sb_engine_ui_bridges_timeout.value()
        self.host.uisAlwaysOnTop = self.ui.ch_engine_uis_always_on_top.isChecked()

        if self.ui.ch_engine_force_stereo.isEnabled():
            settings.setValue(CARLA_KEY_ENGINE_FORCE_STEREO, self.host.forceStereo)

        settings.setValue(CARLA_KEY_MAIN_SHOW_LOGS, self.host.showLogs)
        settings.setValue(CARLA_KEY_ENGINE_MAX_PARAMETERS, self.host.maxParameters)
        settings.setValue(CARLA_KEY_ENGINE_RESET_XRUNS, self.host.resetXruns)
        settings.setValue(CARLA_KEY_ENGINE_MANAGE_UIS, self.host.manageUIs)
        settings.setValue(
            CARLA_KEY_ENGINE_PREFER_PLUGIN_BRIDGES, self.host.preferPluginBridges
        )
        settings.setValue(CARLA_KEY_ENGINE_PREFER_UI_BRIDGES, self.host.preferUIBridges)
        settings.setValue(
            CARLA_KEY_ENGINE_UI_BRIDGES_TIMEOUT, self.host.uiBridgesTimeout
        )
        settings.setValue(CARLA_KEY_ENGINE_UIS_ALWAYS_ON_TOP, self.host.uisAlwaysOnTop)
        settings.setValue(CARLA_KEY_EXPERIMENTAL_EXPORT_LV2, self.host.exportLV2)
        settings.setValue(
            CARLA_KEY_EXPERIMENTAL_PLUGIN_BRIDGES, self.host.showPluginBridges
        )
        settings.setValue(
            CARLA_KEY_EXPERIMENTAL_WINE_BRIDGES, self.host.showWineBridges
        )

        # -------------------------------------------------------------------------------------------------------------
        # OSC

        if getattr(self, "osc_form_builder", None) is not None:
            self.osc_form_builder.save_values(settings)

        # -------------------------------------------------------------------------------------------------------------
        # File Paths

        audioPaths = []
        midiPaths = []

        for i in range(self.ui.lw_files_audio.count()):
            audioPaths.append(self.ui.lw_files_audio.item(i).text())

        for i in range(self.ui.lw_files_midi.count()):
            midiPaths.append(self.ui.lw_files_midi.item(i).text())

        self.host.set_engine_option(
            ENGINE_OPTION_FILE_PATH, FILE_AUDIO, splitter.join(audioPaths)
        )
        self.host.set_engine_option(
            ENGINE_OPTION_FILE_PATH, FILE_MIDI, splitter.join(midiPaths)
        )

        settings.setValue(CARLA_KEY_PATHS_AUDIO, audioPaths)
        settings.setValue(CARLA_KEY_PATHS_MIDI, midiPaths)

        # -------------------------------------------------------------------------------------------------------------
        # Plugin Paths

        ladspas = []
        dssis = []
        lv2s = []
        vst2s = []
        vst3s = []
        sf2s = []
        sfzs = []
        jsfxs = []
        claps = []

        for i in range(self.ui.lw_ladspa.count()):
            ladspas.append(self.ui.lw_ladspa.item(i).text())

        for i in range(self.ui.lw_dssi.count()):
            dssis.append(self.ui.lw_dssi.item(i).text())

        for i in range(self.ui.lw_lv2.count()):
            lv2s.append(self.ui.lw_lv2.item(i).text())

        for i in range(self.ui.lw_vst.count()):
            vst2s.append(self.ui.lw_vst.item(i).text())

        for i in range(self.ui.lw_vst3.count()):
            vst3s.append(self.ui.lw_vst3.item(i).text())

        for i in range(self.ui.lw_sf2.count()):
            sf2s.append(self.ui.lw_sf2.item(i).text())

        for i in range(self.ui.lw_sfz.count()):
            sfzs.append(self.ui.lw_sfz.item(i).text())

        for i in range(self.ui.lw_jsfx.count()):
            jsfxs.append(self.ui.lw_jsfx.item(i).text())

        for i in range(self.ui.lw_clap.count()):
            claps.append(self.ui.lw_clap.item(i).text())

        self.host.set_engine_option(
            ENGINE_OPTION_PLUGIN_PATH, PLUGIN_LADSPA, splitter.join(ladspas)
        )
        self.host.set_engine_option(
            ENGINE_OPTION_PLUGIN_PATH, PLUGIN_DSSI, splitter.join(dssis)
        )
        self.host.set_engine_option(
            ENGINE_OPTION_PLUGIN_PATH, PLUGIN_LV2, splitter.join(lv2s)
        )
        self.host.set_engine_option(
            ENGINE_OPTION_PLUGIN_PATH, PLUGIN_VST2, splitter.join(vst2s)
        )
        self.host.set_engine_option(
            ENGINE_OPTION_PLUGIN_PATH, PLUGIN_VST3, splitter.join(vst3s)
        )
        self.host.set_engine_option(
            ENGINE_OPTION_PLUGIN_PATH, PLUGIN_SF2, splitter.join(sf2s)
        )
        self.host.set_engine_option(
            ENGINE_OPTION_PLUGIN_PATH, PLUGIN_SFZ, splitter.join(sfzs)
        )
        self.host.set_engine_option(
            ENGINE_OPTION_PLUGIN_PATH, PLUGIN_JSFX, splitter.join(jsfxs)
        )
        self.host.set_engine_option(
            ENGINE_OPTION_PLUGIN_PATH, PLUGIN_CLAP, splitter.join(claps)
        )

        settings.setValue(CARLA_KEY_PATHS_LADSPA, ladspas)
        settings.setValue(CARLA_KEY_PATHS_DSSI, dssis)
        settings.setValue(CARLA_KEY_PATHS_LV2, lv2s)
        settings.setValue(CARLA_KEY_PATHS_VST2, vst2s)
        settings.setValue(CARLA_KEY_PATHS_VST3, vst3s)
        settings.setValue(CARLA_KEY_PATHS_SF2, sf2s)
        settings.setValue(CARLA_KEY_PATHS_SFZ, sfzs)
        settings.setValue(CARLA_KEY_PATHS_JSFX, jsfxs)
        settings.setValue(CARLA_KEY_PATHS_CLAP, claps)

        # -------------------------------------------------------------------------------------------------------------
        # Wine

        if getattr(self, "wine_form_builder", None) is not None:
            self.wine_form_builder.save_values(settings)

        # -------------------------------------------------------------------------------------------------------------
        # Experimental

        if getattr(self, "experimental_form_builder", None) is not None:
            self.experimental_form_builder.save_values(settings)

        settings.sync()

    # -----------------------------------------------------------------------------------------------------------------

    @pyqtSlot()
    def slot_applySettings(self):
        self.slot_saveSettings()
        host_gui = None
        try:
            from carla_shared import gCarla
            if hasattr(gCarla, "gui") and gCarla.gui is not None:
                host_gui = gCarla.gui
        except Exception:
            pass
        if host_gui is None:
            host_gui = self.parent()

        if host_gui is not None:
            if hasattr(host_gui, "loadSettings"):
                host_gui.loadSettings(False)
            if hasattr(host_gui, "setupCanvas"):
                host_gui.setupCanvas()
            if hasattr(host_gui, "slot_miniCanvasCheckAll"):
                host_gui.slot_miniCanvasCheckAll()
            if hasattr(host_gui, "ui") and hasattr(host_gui.ui, "graphicsView") and host_gui.ui.graphicsView is not None:
                vp = host_gui.ui.graphicsView.viewport()
                if vp is not None:
                    vp.update()

    # -----------------------------------------------------------------------------------------------------------------

    @pyqtSlot()
    def slot_resetSettings(self):
        currentRow = self.ui.lw_page.currentRow()
        self._ensure_tab_built(currentRow)

        # -------------------------------------------------------------------------------------------------------------
        # Main

        if currentRow == self.TAB_INDEX_MAIN:
            if getattr(self, "general_form_builder", None) is not None:
                self.general_form_builder.reset_defaults()

        # -------------------------------------------------------------------------------------------------------------
        # Canvas

        elif currentRow == self.TAB_INDEX_CANVAS:
            if getattr(self, "canvas_form_builder", None) is not None:
                self.canvas_form_builder.reset_defaults()

        # -------------------------------------------------------------------------------------------------------------
        # Engine

        elif currentRow == self.TAB_INDEX_ENGINE:
            if not self.host.isPlugin:
                self.ui.cb_engine_audio_driver.setCurrentIndex(0)

            if not self.host.processModeForced:
                if self.ui.cb_engine_audio_driver.currentText() == "JACK":
                    self.ui.cb_engine_process_mode_jack.setCurrentIndex(
                        CARLA_DEFAULT_PROCESS_MODE
                    )
                    self.ui.sw_engine_process_mode.setCurrentIndex(0)  # show all modes
                else:
                    self.ui.cb_engine_process_mode_other.setCurrentIndex(
                        CARLA_DEFAULT_PROCESS_MODE - self.PROCESS_MODE_NON_JACK_PADDING
                    )
                    self.ui.sw_engine_process_mode.setCurrentIndex(
                        1
                    )  # hide single+multi client modes

            self.ui.sb_engine_max_params.setValue(CARLA_DEFAULT_MAX_PARAMETERS)
            self.ui.cb_engine_reset_xruns.setChecked(CARLA_DEFAULT_RESET_XRUNS)
            self.ui.ch_engine_uis_always_on_top.setChecked(
                CARLA_DEFAULT_UIS_ALWAYS_ON_TOP
            )
            self.ui.ch_engine_prefer_ui_bridges.setChecked(
                CARLA_DEFAULT_PREFER_UI_BRIDGES
            )
            self.ui.sb_engine_ui_bridges_timeout.setValue(
                CARLA_DEFAULT_UI_BRIDGES_TIMEOUT
            )
            self.ui.ch_engine_manage_uis.setChecked(CARLA_DEFAULT_MANAGE_UIS)

        # -------------------------------------------------------------------------------------------------------------
        # OSC

        elif currentRow == self.TAB_INDEX_OSC:
            if getattr(self, "osc_form_builder", None) is not None:
                self.osc_form_builder.reset_defaults()

        # -------------------------------------------------------------------------------------------------------------
        # Plugin Paths

        elif currentRow == self.TAB_INDEX_FILEPATHS:
            curIndex = self.ui.tw_filepaths.currentIndex()

            if curIndex == self.FILEPATH_INDEX_AUDIO:
                self.ui.lw_files_audio.clear()

            elif curIndex == self.FILEPATH_INDEX_MIDI:
                self.ui.lw_files_midi.clear()

        # -------------------------------------------------------------------------------------------------------------
        # Plugin Paths

        elif currentRow == self.TAB_INDEX_PLUGINPATHS:
            curIndex = self.ui.tw_paths.currentIndex()

            if curIndex == self.PLUGINPATH_INDEX_LADSPA:
                paths = CARLA_DEFAULT_LADSPA_PATH
                paths.sort()
                self.ui.lw_ladspa.clear()

                for path in paths:
                    if not path:
                        continue
                    self.ui.lw_ladspa.addItem(path)

            elif curIndex == self.PLUGINPATH_INDEX_DSSI:
                paths = CARLA_DEFAULT_DSSI_PATH
                paths.sort()
                self.ui.lw_dssi.clear()

                for path in paths:
                    if not path:
                        continue
                    self.ui.lw_dssi.addItem(path)

            elif curIndex == self.PLUGINPATH_INDEX_LV2:
                paths = CARLA_DEFAULT_LV2_PATH
                paths.sort()
                self.ui.lw_lv2.clear()

                for path in paths:
                    if not path:
                        continue
                    self.ui.lw_lv2.addItem(path)

            elif curIndex == self.PLUGINPATH_INDEX_VST2:
                paths = CARLA_DEFAULT_VST2_PATH
                paths.sort()
                self.ui.lw_vst.clear()

                for path in paths:
                    if not path:
                        continue
                    self.ui.lw_vst.addItem(path)

            elif curIndex == self.PLUGINPATH_INDEX_VST3:
                paths = CARLA_DEFAULT_VST3_PATH
                paths.sort()
                self.ui.lw_vst3.clear()

                for path in paths:
                    if not path:
                        continue
                    self.ui.lw_vst3.addItem(path)

            elif curIndex == self.PLUGINPATH_INDEX_SF2:
                paths = CARLA_DEFAULT_SF2_PATH
                paths.sort()
                self.ui.lw_sf2.clear()

                for path in paths:
                    if not path:
                        continue
                    self.ui.lw_sf2.addItem(path)

            elif curIndex == self.PLUGINPATH_INDEX_SFZ:
                paths = CARLA_DEFAULT_SFZ_PATH
                paths.sort()
                self.ui.lw_sfz.clear()

                for path in paths:
                    if not path:
                        continue
                    self.ui.lw_sfz.addItem(path)

            elif curIndex == self.PLUGINPATH_INDEX_JSFX:
                paths = CARLA_DEFAULT_JSFX_PATH
                paths.sort()
                self.ui.lw_jsfx.clear()

                for path in paths:
                    if not path:
                        continue
                    self.ui.lw_jsfx.addItem(path)

            elif curIndex == self.PLUGINPATH_INDEX_CLAP:
                paths = CARLA_DEFAULT_CLAP_PATH
                paths.sort()
                self.ui.lw_clap.clear()

                for path in paths:
                    if not path:
                        continue
                    self.ui.lw_clap.addItem(path)

        # -------------------------------------------------------------------------------------------------------------
        # Wine

        elif currentRow == self.TAB_INDEX_WINE:
            if getattr(self, "wine_form_builder", None) is not None:
                self.wine_form_builder.reset_defaults()

        # -------------------------------------------------------------------------------------------------------------
        # Experimental

        elif currentRow == self.TAB_INDEX_EXPERIMENTAL:
            if getattr(self, "experimental_form_builder", None) is not None:
                self.experimental_form_builder.reset_defaults()

    def resetExperimentalSettings(self):
        # Forever experimental
        self.ui.cb_exp_plugin_bridges.setChecked(
            CARLA_DEFAULT_EXPERIMENTAL_PLUGIN_BRIDGES
        )
        self.ui.ch_exp_wine_bridges.setChecked(CARLA_DEFAULT_EXPERIMENTAL_WINE_BRIDGES)
        self.ui.ch_exp_jack_apps.setChecked(CARLA_DEFAULT_EXPERIMENTAL_JACK_APPS)
        self.ui.ch_exp_export_lv2.setChecked(CARLA_DEFAULT_EXPERIMENTAL_LV2_EXPORT)
        self.ui.ch_exp_load_lib_global.setChecked(
            CARLA_DEFAULT_EXPERIMENTAL_LOAD_LIB_GLOBAL
        )
        self.ui.ch_exp_prevent_bad_behaviour.setChecked(
            CARLA_DEFAULT_EXPERIMENTAL_PREVENT_BAD_BEHAVIOUR
        )

        # Temporary, until stable
        self.ui.ch_main_system_icons.setChecked(CARLA_DEFAULT_MAIN_SYSTEM_ICONS)
        self.ui.cb_canvas_fancy_eyecandy.setChecked(
            CARLA_DEFAULT_CANVAS_FANCY_EYE_CANDY
        )
        self.ui.cb_canvas_use_opengl.setChecked(
            CARLA_DEFAULT_CANVAS_USE_OPENGL and self.ui.cb_canvas_use_opengl.isEnabled()
        )
        self.ui.cb_canvas_render_hq_aa.setChecked(
            CARLA_DEFAULT_CANVAS_HQ_ANTIALIASING
            and self.ui.cb_canvas_render_hq_aa.isEnabled()
        )
        self.ui.cb_canvas_inline_displays.setChecked(
            CARLA_DEFAULT_CANVAS_INLINE_DISPLAYS
        )
        self.ui.ch_engine_force_stereo.setChecked(CARLA_DEFAULT_FORCE_STEREO)
        self.ui.ch_engine_prefer_plugin_bridges.setChecked(
            CARLA_DEFAULT_PREFER_PLUGIN_BRIDGES
        )

    # -----------------------------------------------------------------------------------------------------------------

    @pyqtSlot(bool)
    def slot_enableExperimental(self, toggled):
        if toggled:
            self.ui.lw_page.showRow(self.TAB_INDEX_EXPERIMENTAL)
            if self.ui.ch_exp_wine_bridges.isChecked() and not self.host.isControl:
                self.ui.lw_page.showRow(self.TAB_INDEX_WINE)
        else:
            self.ui.lw_page.hideRow(self.TAB_INDEX_EXPERIMENTAL)
            self.ui.lw_page.hideRow(self.TAB_INDEX_WINE)

    @pyqtSlot(bool)
    def slot_enableWineBridges(self, toggled):
        if toggled and not self.host.isControl:
            self.ui.lw_page.showRow(self.TAB_INDEX_WINE)
        else:
            self.ui.lw_page.hideRow(self.TAB_INDEX_WINE)

    @pyqtSlot(bool)
    def slot_pluginBridgesToggled(self, toggled):
        if not toggled:
            self.ui.ch_exp_wine_bridges.setChecked(False)
            self.ui.ch_engine_prefer_plugin_bridges.setChecked(False)
            self.ui.lw_page.hideRow(self.TAB_INDEX_WINE)

    @pyqtSlot(bool)
    def slot_canvasEyeCandyToggled(self, toggled):
        if not toggled:
            # disable fancy eyecandy too
            self.ui.cb_canvas_fancy_eyecandy.setChecked(False)

    @pyqtSlot(bool)
    def slot_canvasFancyEyeCandyToggled(self, toggled):
        if toggled:
            # make sure normal eyecandy is enabled too
            self.ui.cb_canvas_eyecandy.setChecked(True)

    @pyqtSlot(bool)
    def slot_canvasOpenGLToggled(self, toggled):
        if not toggled:
            # uncheck GL specific option
            self.ui.cb_canvas_render_hq_aa.setChecked(False)

    # -----------------------------------------------------------------------------------------------------------------

    @pyqtSlot()
    def slot_getAndSetProjectPath(self):
        # FIXME
        getAndSetPath(self, self.ui.le_main_proj_folder)

    # -----------------------------------------------------------------------------------------------------------------

    @pyqtSlot()
    def slot_engineAudioDriverChanged(self):
        if self.ui.cb_engine_audio_driver.currentText() == "JACK":
            self.ui.sw_engine_process_mode.setCurrentIndex(0)
        else:
            self.ui.sw_engine_process_mode.setCurrentIndex(1)

    @pyqtSlot()
    def slot_showAudioDriverSettings(self):
        driverIndex = self.ui.cb_engine_audio_driver.currentIndex()
        driverName = self.ui.cb_engine_audio_driver.currentText()
        DriverSettingsW(self, self.host, driverIndex, driverName).exec_()

    # -----------------------------------------------------------------------------------------------------------------

    @pyqtSlot()
    def slot_addPluginPath(self):
        newPath = QFileDialog.getExistingDirectory(
            self, self.tr("Add Path"), "", QFileDialog.ShowDirsOnly
        )

        if not newPath:
            return

        curIndex = self.ui.tw_paths.currentIndex()

        if curIndex == self.PLUGINPATH_INDEX_LADSPA:
            self.ui.lw_ladspa.addItem(newPath)
        elif curIndex == self.PLUGINPATH_INDEX_DSSI:
            self.ui.lw_dssi.addItem(newPath)
        elif curIndex == self.PLUGINPATH_INDEX_LV2:
            self.ui.lw_lv2.addItem(newPath)
        elif curIndex == self.PLUGINPATH_INDEX_VST2:
            self.ui.lw_vst.addItem(newPath)
        elif curIndex == self.PLUGINPATH_INDEX_VST3:
            self.ui.lw_vst3.addItem(newPath)
        elif curIndex == self.PLUGINPATH_INDEX_SF2:
            self.ui.lw_sf2.addItem(newPath)
        elif curIndex == self.PLUGINPATH_INDEX_SFZ:
            self.ui.lw_sfz.addItem(newPath)
        elif curIndex == self.PLUGINPATH_INDEX_JSFX:
            self.ui.lw_jsfx.addItem(newPath)
        elif curIndex == self.PLUGINPATH_INDEX_CLAP:
            self.ui.lw_clap.addItem(newPath)

    @pyqtSlot()
    def slot_removePluginPath(self):
        curIndex = self.ui.tw_paths.currentIndex()

        if curIndex == self.PLUGINPATH_INDEX_LADSPA:
            self.ui.lw_ladspa.takeItem(self.ui.lw_ladspa.currentRow())
        elif curIndex == self.PLUGINPATH_INDEX_DSSI:
            self.ui.lw_dssi.takeItem(self.ui.lw_dssi.currentRow())
        elif curIndex == self.PLUGINPATH_INDEX_LV2:
            self.ui.lw_lv2.takeItem(self.ui.lw_lv2.currentRow())
        elif curIndex == self.PLUGINPATH_INDEX_VST2:
            self.ui.lw_vst.takeItem(self.ui.lw_vst.currentRow())
        elif curIndex == self.PLUGINPATH_INDEX_VST3:
            self.ui.lw_vst3.takeItem(self.ui.lw_vst3.currentRow())
        elif curIndex == self.PLUGINPATH_INDEX_SF2:
            self.ui.lw_sf2.takeItem(self.ui.lw_sf2.currentRow())
        elif curIndex == self.PLUGINPATH_INDEX_SFZ:
            self.ui.lw_sfz.takeItem(self.ui.lw_sfz.currentRow())
        elif curIndex == self.PLUGINPATH_INDEX_JSFX:
            self.ui.lw_jsfx.takeItem(self.ui.lw_jsfx.currentRow())
        elif curIndex == self.PLUGINPATH_INDEX_CLAP:
            self.ui.lw_clap.takeItem(self.ui.lw_clap.currentRow())

    @pyqtSlot()
    def slot_changePluginPath(self):
        curIndex = self.ui.tw_paths.currentIndex()

        if curIndex == self.PLUGINPATH_INDEX_LADSPA:
            currentPath = self.ui.lw_ladspa.currentItem().text()
        elif curIndex == self.PLUGINPATH_INDEX_DSSI:
            currentPath = self.ui.lw_dssi.currentItem().text()
        elif curIndex == self.PLUGINPATH_INDEX_LV2:
            currentPath = self.ui.lw_lv2.currentItem().text()
        elif curIndex == self.PLUGINPATH_INDEX_VST2:
            currentPath = self.ui.lw_vst.currentItem().text()
        elif curIndex == self.PLUGINPATH_INDEX_VST3:
            currentPath = self.ui.lw_vst3.currentItem().text()
        elif curIndex == self.PLUGINPATH_INDEX_SF2:
            currentPath = self.ui.lw_sf2.currentItem().text()
        elif curIndex == self.PLUGINPATH_INDEX_SFZ:
            currentPath = self.ui.lw_sfz.currentItem().text()
        elif curIndex == self.PLUGINPATH_INDEX_JSFX:
            currentPath = self.ui.lw_jsfx.currentItem().text()
        elif curIndex == self.PLUGINPATH_INDEX_CLAP:
            currentPath = self.ui.lw_clap.currentItem().text()
        else:
            currentPath = ""

        newPath = QFileDialog.getExistingDirectory(
            self, self.tr("Add Path"), currentPath, QFileDialog.ShowDirsOnly
        )

        if not newPath:
            return

        if curIndex == self.PLUGINPATH_INDEX_LADSPA:
            self.ui.lw_ladspa.currentItem().setText(newPath)
        elif curIndex == self.PLUGINPATH_INDEX_DSSI:
            self.ui.lw_dssi.currentItem().setText(newPath)
        elif curIndex == self.PLUGINPATH_INDEX_LV2:
            self.ui.lw_lv2.currentItem().setText(newPath)
        elif curIndex == self.PLUGINPATH_INDEX_VST2:
            self.ui.lw_vst.currentItem().setText(newPath)
        elif curIndex == self.PLUGINPATH_INDEX_VST3:
            self.ui.lw_vst3.currentItem().setText(newPath)
        elif curIndex == self.PLUGINPATH_INDEX_SF2:
            self.ui.lw_sf2.currentItem().setText(newPath)
        elif curIndex == self.PLUGINPATH_INDEX_SFZ:
            self.ui.lw_sfz.currentItem().setText(newPath)
        elif curIndex == self.PLUGINPATH_INDEX_JSFX:
            self.ui.lw_jsfx.currentItem().setText(newPath)
        elif curIndex == self.PLUGINPATH_INDEX_CLAP:
            self.ui.lw_clap.currentItem().setText(newPath)

    # -----------------------------------------------------------------------------------------------------------------

    @pyqtSlot(int)
    def slot_pluginPathTabChanged(self, index):
        if index == self.PLUGINPATH_INDEX_LADSPA:
            row = self.ui.lw_ladspa.currentRow()
        elif index == self.PLUGINPATH_INDEX_DSSI:
            row = self.ui.lw_dssi.currentRow()
        elif index == self.PLUGINPATH_INDEX_LV2:
            row = self.ui.lw_lv2.currentRow()
        elif index == self.PLUGINPATH_INDEX_VST2:
            row = self.ui.lw_vst.currentRow()
        elif index == self.PLUGINPATH_INDEX_VST3:
            row = self.ui.lw_vst3.currentRow()
        elif index == self.PLUGINPATH_INDEX_SF2:
            row = self.ui.lw_sf2.currentRow()
        elif index == self.PLUGINPATH_INDEX_SFZ:
            row = self.ui.lw_sfz.currentRow()
        elif index == self.PLUGINPATH_INDEX_JSFX:
            row = self.ui.lw_jsfx.currentRow()
        elif index == self.PLUGINPATH_INDEX_CLAP:
            row = self.ui.lw_clap.currentRow()
        else:
            row = -1

        self.slot_pluginPathRowChanged(row)

    @pyqtSlot(int)
    def slot_pluginPathRowChanged(self, row):
        check = bool(row >= 0)
        self.ui.b_paths_remove.setEnabled(check)
        self.ui.b_paths_change.setEnabled(check)

    # -----------------------------------------------------------------------------------------------------------------

    @pyqtSlot()
    def slot_addFilePath(self):
        newPath = QFileDialog.getExistingDirectory(
            self, self.tr("Add Path"), "", QFileDialog.ShowDirsOnly
        )

        if not newPath:
            return

        curIndex = self.ui.tw_filepaths.currentIndex()

        if curIndex == self.FILEPATH_INDEX_AUDIO:
            self.ui.lw_files_audio.addItem(newPath)
        elif curIndex == self.FILEPATH_INDEX_MIDI:
            self.ui.lw_files_midi.addItem(newPath)

    @pyqtSlot()
    def slot_removeFilePath(self):
        curIndex = self.ui.tw_filepaths.currentIndex()

        if curIndex == self.FILEPATH_INDEX_AUDIO:
            self.ui.lw_files_audio.takeItem(self.ui.lw_files_audio.currentRow())
        elif curIndex == self.FILEPATH_INDEX_MIDI:
            self.ui.lw_files_midi.takeItem(self.ui.lw_files_midi.currentRow())

    @pyqtSlot()
    def slot_changeFilePath(self):
        curIndex = self.ui.tw_filepaths.currentIndex()

        if curIndex == self.FILEPATH_INDEX_AUDIO:
            currentPath = self.ui.lw_files_audio.currentItem().text()
        elif curIndex == self.FILEPATH_INDEX_MIDI:
            currentPath = self.ui.lw_files_midi.currentItem().text()
        else:
            currentPath = ""

        newPath = QFileDialog.getExistingDirectory(
            self, self.tr("Add Path"), currentPath, QFileDialog.ShowDirsOnly
        )

        if not newPath:
            return

        if curIndex == self.FILEPATH_INDEX_AUDIO:
            self.ui.lw_files_audio.currentItem().setText(newPath)
        elif curIndex == self.FILEPATH_INDEX_MIDI:
            self.ui.lw_files_midi.currentItem().setText(newPath)

    # -----------------------------------------------------------------------------------------------------------------

    @pyqtSlot(int)
    def slot_filePathTabChanged(self, index):
        if index == self.FILEPATH_INDEX_AUDIO:
            row = self.ui.lw_files_audio.currentRow()
        elif index == self.FILEPATH_INDEX_MIDI:
            row = self.ui.lw_files_midi.currentRow()
        else:
            row = -1

        self.slot_filePathRowChanged(row)

    @pyqtSlot(int)
    def slot_filePathRowChanged(self, row):
        check = bool(row >= 0)
        self.ui.b_filepaths_remove.setEnabled(check)
        self.ui.b_filepaths_change.setEnabled(check)


# ---------------------------------------------------------------------------------------------------------------------
# Main

if __name__ == "__main__":
    from carla_app import CarlaApplication
    from host_app import initHost as _initHost, loadHostSettings as _loadHostSettings

    # pylint: disable=ungrouped-imports
    from carla_shared import handleInitialCommandLineArguments
    # pylint: enable=ungrouped-imports

    initName, libPrefix = handleInitialCommandLineArguments(
        __file__ if "__file__" in dir() else None
    )

    _app = CarlaApplication("Carla2-Settings", libPrefix)
    _host = _initHost("Carla2-Settings", libPrefix, False, False, False)
    _loadHostSettings(_host)

    _gui = CarlaSettingsW(None, _host, True, True)
    _gui.show()

    _app.exit_exec()

# ---------------------------------------------------------------------------------------------------------------------
