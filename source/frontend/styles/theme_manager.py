"""Data-driven QSS Theme Manager for Clara.

Dynamically scans theme directories (.qss files), loads user custom themes,
and applies styles live to QApplication without requiring application restart.
Canvasbox theming is handled independently via patchcanvas/themes.json.
"""

import glob
import math
import os
import re
import weakref

# Global minimal scrollbar QSS applied to all themes
MINIMAL_SCROLLBAR_QSS = """QScrollBar:vertical {
    border: none;
    background-color: transparent;
    width: 8px;
    margin: 0px;
    border-radius: 4px;
}
QScrollBar::handle:vertical {
    min-height: 24px;
    border-radius: 4px;
}
QScrollBar::handle:vertical:hover {
    /* inherits theme colors */
}
QScrollBar:horizontal {
    border: none;
    background-color: transparent;
    height: 8px;
    margin: 0px;
    border-radius: 4px;
}
QScrollBar::handle:horizontal {
    min-width: 24px;
    border-radius: 4px;
}
QScrollBar::handle:horizontal:hover {
    /* inherits theme colors */
}
"""
from qt_compat import QApplication, QColor, QPalette
from .engine import ThemeEngine

_STYLES_DIR = os.path.dirname(os.path.abspath(__file__))
_PRIMITIVES_PATH = os.path.join(_STYLES_DIR, "base_primitives.qss")

def _load_base_primitives() -> str:
    if os.path.isfile(_PRIMITIVES_PATH):
        try:
            with open(_PRIMITIVES_PATH, "r", encoding="utf-8") as f:
                return f.read()
        except Exception:
            pass
    return ""

CARLA_KEY_MAIN_USE_SYSTEM_THEME = "Main/UseSystemTheme"
CARLA_DEFAULT_MAIN_USE_SYSTEM_THEME = False

CARLA_KEY_MAIN_APP_THEME = "Main/AppTheme"
CARLA_DEFAULT_MAIN_APP_THEME = "Catppuccin Macchiato"


def find_closest_system_color(color, palette=None, threshold=0.75) -> QColor:
    """
    Find the closest color in the active system palette to `color`.
    Evaluates perceptual likeliness: (1.0 - delta_c / max_distance).
    If likeliness >= threshold (default 0.75 / 75%), return the closest system color.
    Otherwise, adjust the color towards the system theme tone by blending 25% of the
    closest system color into the target color, preserving its role while harmonizing
    with the platform theme.
    """
    if isinstance(color, str):
        c = color.strip()
        if not c.startswith("#") and not c.startswith("rgb"):
            c = "#" + c
        qcol = QColor(c)
    elif isinstance(color, QColor):
        qcol = color
    elif isinstance(color, (list, tuple)) and len(color) >= 3:
        qcol = QColor(int(color[0]), int(color[1]), int(color[2]))
    else:
        qcol = QColor(color)

    if not qcol.isValid():
        qcol = QColor(0, 0, 0)

    tr, tg, tb = qcol.red(), qcol.green(), qcol.blue()

    if palette is None:
        app = QApplication.instance()
        palette = app.palette() if app else QPalette()

    roles = (
        QPalette.Window,
        QPalette.WindowText,
        QPalette.Base,
        QPalette.AlternateBase,
        QPalette.Text,
        QPalette.Button,
        QPalette.ButtonText,
        QPalette.Highlight,
        QPalette.HighlightedText,
        QPalette.Mid,
        QPalette.Dark,
        QPalette.Light,
    )

    best_sys_col = None
    best_likeliness = -1.0

    for role in roles:
        sys_col = palette.color(role)
        sr, sg, sb = sys_col.red(), sys_col.green(), sys_col.blue()
        # Perceptual Euclidean distance with eye sensitivity weights
        dr = tr - sr
        dg = tg - sg
        db = tb - sb
        dist = math.sqrt(0.299 * (dr ** 2) + 0.587 * (dg ** 2) + 0.114 * (db ** 2))
        likeliness = 1.0 - (dist / 255.0)

        if likeliness > best_likeliness:
            best_likeliness = likeliness
            best_sys_col = sys_col

    if best_sys_col is None:
        return qcol

    if best_likeliness >= threshold:
        return best_sys_col

    # Else adjust it a bit: blend 25% of closest system color and calibrate brightness
    sys_win = palette.color(QPalette.Window)
    is_sys_dark = (0.299 * sys_win.red() + 0.587 * sys_win.green() + 0.114 * sys_win.blue()) < 128

    sr, sg, sb = best_sys_col.red(), best_sys_col.green(), best_sys_col.blue()
    blend_r = int(round(tr * 0.75 + sr * 0.25))
    blend_g = int(round(tg * 0.75 + sg * 0.25))
    blend_b = int(round(tb * 0.75 + sb * 0.25))

    cur_lum = 0.299 * blend_r + 0.587 * blend_g + 0.114 * blend_b
    if not is_sys_dark and cur_lum > 180:
        factor = 0.35
        blend_r = int(blend_r * factor)
        blend_g = int(blend_g * factor)
        blend_b = int(blend_b * factor)
    elif is_sys_dark and cur_lum < 40:
        factor = 1.4
        blend_r = min(255, int(blend_r * factor))
        blend_g = min(255, int(blend_g * factor))
        blend_b = min(255, int(blend_b * factor))

    return QColor(blend_r, blend_g, blend_b)


def build_palette(tokens: dict) -> QPalette:
    """Map theme tokens onto Qt palette roles so a theme switch is a palette
    swap, not a full QSS repolish of every widget."""
    def color(name: str) -> QColor:
        value = tokens[name]
        qcolor = QColor(value)
        if not qcolor.isValid():
            match = re.match(r"rgba?\(([^)]+)\)", value)
            if match is not None:
                parts = [part.strip() for part in match.group(1).split(",")]
                if len(parts) >= 3:
                    red, green, blue = (int(part) for part in parts[:3])
                    alpha = 255
                    if len(parts) > 3:
                        raw_alpha = parts[3]
                        alpha = int(float(raw_alpha) * 255) if "." in raw_alpha else int(raw_alpha)
                    qcolor = QColor(red, green, blue, alpha)
        if not qcolor.isValid():
            raise ValueError(f"invalid theme color for {name}: {value!r}")
        return qcolor

    pal = QPalette()
    pal.setColor(QPalette.Window,          color("bg-primary"))
    pal.setColor(QPalette.WindowText,      color("text-primary"))
    pal.setColor(QPalette.Base,            color("bg-surface"))
    pal.setColor(QPalette.AlternateBase,   color("bg-hover"))
    pal.setColor(QPalette.ToolTipBase,     color("bg-surface"))
    pal.setColor(QPalette.ToolTipText,     color("text-primary"))
    pal.setColor(QPalette.Text,            color("text-primary"))
    pal.setColor(QPalette.Button,          color("bg-surface"))
    pal.setColor(QPalette.ButtonText,      color("text-primary"))
    pal.setColor(QPalette.BrightText,      color("text-primary"))
    pal.setColor(QPalette.Highlight,       color("accent"))
    pal.setColor(QPalette.HighlightedText, color("bg-primary"))
    pal.setColor(QPalette.Mid,             color("border-dim"))
    pal.setColor(QPalette.Midlight,        color("accent-tint-50"))
    pal.setColor(QPalette.Dark,            color("border-subtle"))
    pal.setColor(QPalette.Shadow,          color("accent-tint-20"))
    pal.setColor(QPalette.Light,           color("orange"))
    pal.setColor(QPalette.Link,            color("cyan"))
    pal.setColor(QPalette.LinkVisited,     color("red"))
    pal.setColor(QPalette.PlaceholderText, color("text-muted"))

    muted = color("text-muted")
    for role in (QPalette.WindowText, QPalette.Text, QPalette.ButtonText):
        pal.setColor(QPalette.Disabled, role, muted)
    return pal


class ThemeManager:
    _instance = None

    def __init__(self):
        # Base bundled themes directory
        self.bundled_themes_dir = os.path.join(os.path.dirname(__file__), "themes")
        # User customized themes directory (~/.config/clara/themes or ~/.config/carla/themes)
        self.user_themes_dir = os.path.expanduser("~/.config/clara/themes")
        self.engine = ThemeEngine(base_primitives_template=_load_base_primitives())
        self._current_theme = None
        self._current_mode = "dark"
        self._previous_mode = "dark"
        self._using_system = False
        self._original_style = None
        self._available_themes = None
        self._applied_qss = None
        self._theme_serial = 0
        self._themed_windows = weakref.WeakSet()
        self._style_is_fusion = False
        self._rack_rebuild_token = 0


    @classmethod
    def instance(cls):
        if cls._instance is None:
            cls._instance = ThemeManager()
        return cls._instance

    def is_using_system(self) -> bool:
        return self._using_system

    def get_available_themes(self, refresh: bool = False) -> list[str]:
        """Return a sorted list of unique available theme names from registry and disk."""
        if not refresh and self._available_themes is not None:
            return list(self._available_themes)

        from .registry import registry
        themes = set(registry.list_theme_names())

        for search_dir in (self.bundled_themes_dir, self.user_themes_dir):
            if os.path.isdir(search_dir):
                for qss_path in glob.glob(os.path.join(search_dir, "*.qss")):
                    base = os.path.splitext(os.path.basename(qss_path))[0]
                    # Convert filename like 'catppuccin_mocha' to 'Catppuccin Mocha'
                    title = " ".join(word.capitalize() for word in base.replace("-", "_").split("_"))
                    themes.add(title)

        if not themes:
            themes.add("Catppuccin Macchiato")

        # Sort with Catppuccin Macchiato first, then alphabetical
        sorted_themes = sorted(list(themes))
        if "Catppuccin Macchiato" in sorted_themes:
            sorted_themes.remove("Catppuccin Macchiato")
            sorted_themes.insert(0, "Catppuccin Macchiato")
        self._available_themes = sorted_themes
        return list(sorted_themes)

    def resolve_theme_name(self, theme_name: str) -> str:
        """Return a theme name we can actually apply for the requested one."""
        available = self.get_available_themes()
        name = (theme_name or "").strip()
        if name in available:
            return name
        lowered = name.lower()
        for candidate in available:
            if candidate.lower() == lowered:
                return candidate
        if CARLA_DEFAULT_MAIN_APP_THEME in available:
            return CARLA_DEFAULT_MAIN_APP_THEME
        return available[0] if available else CARLA_DEFAULT_MAIN_APP_THEME

    def _resolve_theme_file(self, theme_name: str) -> str | None:
        """Find the .qss file corresponding to a given human-readable theme name."""
        filename = theme_name.lower().replace(" ", "_") + ".qss"

        # Check user directory first (allows overriding bundled themes)
        user_path = os.path.join(self.user_themes_dir, filename)
        if os.path.isfile(user_path):
            return user_path

        # Check bundled directory
        bundled_path = os.path.join(self.bundled_themes_dir, filename)
        if os.path.isfile(bundled_path):
            return bundled_path

        # Case-insensitive fallback
        for search_dir in (self.user_themes_dir, self.bundled_themes_dir):
            if os.path.isdir(search_dir):
                for path in glob.glob(os.path.join(search_dir, "*.qss")):
                    if os.path.splitext(os.path.basename(path))[0].lower() == theme_name.lower().replace(" ", "_"):
                        return path
        return None

    def _apply_full_style(self, qss: str):
        """Repolish the windows that are already on screen.

        The stylesheet is palette-only, so a theme switch only needs existing
        widgets to re-resolve their palette roles. Applying it per window is
        much cheaper than a QApplication-wide repolish, and windows that carry
        their own stylesheet (rack list, custom panels) are left alone.
        """
        app = QApplication.instance()
        if self._applied_qss is None:
            # First application: every window, including windows created later.
            app.setStyleSheet(qss)
            self._applied_qss = qss
            return

        self._theme_serial += 1
        forced = qss + "\n/* theme %d */" % self._theme_serial
        for widget in app.topLevelWidgets():
            if widget in self._themed_windows:
                widget.setStyleSheet(forced)
            elif not widget.styleSheet():
                widget.setStyleSheet(forced)
                self._themed_windows.add(widget)
        self._applied_qss = qss

    def _notify_theme_changed(self):
        """Live update patchcanvas, canvasbox, rack list, and banners without application restart."""
        # 1. PatchCanvas & CanvasBoxes
        try:
            import patchcanvas as patchcanvas_pkg
            if getattr(patchcanvas_pkg.canvas, "initiated", False):
                from patchcanvas.theme import Theme
                from carla_shared import CARLA_DEFAULT_CANVAS_THEME
                patchcanvas_pkg.canvas.theme = Theme(CARLA_DEFAULT_CANVAS_THEME)
                patchcanvas_pkg.updateTheme()
        except Exception as e:
            print(f"[THEME] Error live refreshing canvas: {e}")

        # 2. Main GUI, Rack List Widget & Banners
        try:
            from carla_shared import gCarla
            if hasattr(gCarla, "gui") and gCarla.gui is not None:
                if hasattr(gCarla.gui, "_update_split_tab_views"):
                    gCarla.gui._update_split_tab_views()
                if hasattr(gCarla.gui.ui, "listWidget"):
                    gCarla.gui.ui.listWidget.update()
                if hasattr(gCarla.gui, "fUpdateBanner") and gCarla.gui.fUpdateBanner:
                    if hasattr(gCarla.gui.fUpdateBanner, "update_theme_styling"):
                        gCarla.gui.fUpdateBanner.update_theme_styling()
                if hasattr(gCarla.gui, "fSupportBanner") and gCarla.gui.fSupportBanner:
                    if hasattr(gCarla.gui.fSupportBanner, "update_theme_styling"):
                        gCarla.gui.fSupportBanner.update_theme_styling()
                if hasattr(gCarla.gui, "updateSessionStatusIndicators"):
                    gCarla.gui.updateSessionStatusIndicators()
        except Exception as e:
            print(f"[THEME] Error live refreshing GUI views: {e}")

        # 3. Rack slots rebuild their per-widget styles from the new tokens.
        # Rebuilding all 25 slots takes ~4s, so do one per event-loop turn to keep
        # the UI responsive instead of freezing on the theme selection.
        try:
            from carla_shared import gCarla
            from qt_compat import QTimer
            if hasattr(gCarla, "gui") and gCarla.gui is not None:
                items = [p for p in getattr(gCarla.gui, "fPluginList", []) if p is not None]
                if items:
                    self._rack_rebuild_token += 1
                    token = self._rack_rebuild_token
                    queue = list(items)

                    def _restyle_next():
                        if token != self._rack_rebuild_token or not queue:
                            return
                        p = queue.pop(0)
                        list_widget = getattr(gCarla.gui.ui, "listWidget", None)
                        if list_widget is not None:
                            list_widget.setUpdatesEnabled(False)
                        try:
                            restyle = getattr(p.fWidget, "restyle", None)
                            if restyle is not None:
                                follow = getattr(p.fWidget, "follow_theme_mode", None)
                                if follow is not None:
                                    follow(self._previous_mode, self._current_mode)
                                restyle()
                            else:
                                p.recreateWidget(reopenGui=False)
                        except Exception as e:
                            print(f"[THEME] Error restyling rack slot: {e}")
                        finally:
                            if list_widget is not None:
                                list_widget.setUpdatesEnabled(True)
                        if queue:
                            QTimer.singleShot(16, _restyle_next)

                    QTimer.singleShot(0, _restyle_next)
        except Exception as e:
            print(f"[THEME] Error live refreshing rack slots: {e}")


    def apply_theme(
        self,
        theme_name: str = CARLA_DEFAULT_MAIN_APP_THEME,
        mode: str | None = None,
        use_system: bool = False,
    ):
        """Apply the specified theme via the centralized theme engine or revert to native system styling."""
        app = QApplication.instance()
        if not app:
            return

        self._using_system = use_system
        self._previous_mode = self._current_mode
        self._current_theme = theme_name
        self._current_mode = (mode or "dark").lower()

        if self._original_style is None and hasattr(app, "style"):
            curr_style = app.style()
            if curr_style:
                self._original_style = curr_style.name()

        if use_system:
            # Revert to system styling then layer minimal scrollbars
            if self._applied_qss:
                app.setStyleSheet("")
                self._applied_qss = None
            if self._original_style and app.style().name().lower() != self._original_style.lower():
                app.setStyle(self._original_style)
                self._style_is_fusion = False
            app.setPalette(app.style().standardPalette())
            if self._applied_qss != MINIMAL_SCROLLBAR_QSS:
                app.setStyleSheet(MINIMAL_SCROLLBAR_QSS)
                self._applied_qss = MINIMAL_SCROLLBAR_QSS
            self._notify_theme_changed()
            return

        # setStyle() destroys and recreates every widget style, which costs more
        # than the stylesheet itself on a loaded rack. Only switch once.
        if not self._style_is_fusion:
            app.setStyle("Fusion")
            self._style_is_fusion = True

        # The QSS uses palette(...) roles for every color, so switching theme is
        # a palette swap and the stylesheet itself is applied only once.
        from .registry import registry

        theme_def = registry.get_theme(theme_name, mode=mode)
        if theme_def is None and self._resolve_theme_file(theme_name) is None:
            # The saved theme was removed or renamed since it was written.
            theme_name = self.resolve_theme_name(theme_name)
            self._current_theme = theme_name
            theme_def = registry.get_theme(theme_name, mode=mode)

        theme_mode = mode or (theme_def.get("mode", "dark") if theme_def else "dark")
        self._current_mode = theme_mode.lower()
        theme_qss = ""
        tokens = None
        if theme_def:
            theme_qss = self.engine.compile_qss(theme_def, mode=theme_mode)
            tokens = self.engine.active_tokens
        else:
            qss_file = self._resolve_theme_file(theme_name)
            if not theme_qss and qss_file and os.path.isfile(qss_file):
                try:
                    with open(qss_file, "r", encoding="utf-8") as f:
                        theme_qss = f.read() + "\n" + MINIMAL_SCROLLBAR_QSS
                except Exception as e:
                    print(f"[THEME] Failed to load stylesheet {qss_file}: {e}")

        if not theme_qss:
            # Last resort: a bundled theme, so the UI is never left unstyled.
            fallback_name = self.resolve_theme_name(CARLA_DEFAULT_MAIN_APP_THEME)
            fallback = registry.get_theme(fallback_name, mode=theme_mode)
            if fallback is not None:
                self._current_theme = fallback_name
                theme_qss = self.engine.compile_qss(fallback, mode=theme_mode)
                tokens = self.engine.active_tokens
                theme_mode = fallback.get("mode", theme_mode)
                self._current_mode = theme_mode.lower()

        if tokens is not None:
            app.setPalette(build_palette(tokens))

        if not theme_qss:
            return

        self._apply_full_style(theme_qss)
        self._notify_theme_changed()


theme_manager = ThemeManager.instance()
