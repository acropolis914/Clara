# -*- coding: utf-8 -*-

# Clara Update Checker & Notification Banner
# Non-blocking background updater querying structured releases.json

import json
import re
import urllib.request
from qt_compat import (
    QThread, pyqtSignal, QWidget, QHBoxLayout, QVBoxLayout,
    QLabel, QPushButton, QFrame, QMessageBox, QDialog, QTextEdit,
    QSettings, QDesktopServices, QUrl
)
from carla_shared import CLARA_VERSION_STRING as VERSION, CARLA_VERSION_STRING

GITHUB_RELEASES_URL = "https://raw.githubusercontent.com/acropolis914/Clara/main/releases.json"
GITHUB_API_LATEST = "https://api.github.com/repos/acropolis914/Clara/releases/latest"

# ------------------------------------------------------------------------------------------------------------
# Shared helpers (banner styling and updater launching)

_VERSION_RE = re.compile(r"^\d+(?:\.\d+){1,3}$")

_TERMINALS = (
    "x-terminal-emulator", "kitty", "alacritty", "gnome-terminal", "konsole",
    "xfce4-terminal", "foot", "wezterm", "tilix", "terminator", "xterm",
)

_UPDATER_SCRIPT_PATHS = (
    "/usr/share/clara/scripts/clara_self_updater.sh",
    "/usr/lib/carla/scripts/clara_self_updater.sh",
    "/usr/local/share/clara/scripts/clara_self_updater.sh",
    "/usr/share/carla/scripts/clara_self_updater.sh",
)


def _safe_version(version):
    """Version strings come from the network and end up in a shell command, so whitelist them."""
    ver = str(version or "").strip().lstrip("v")
    return ver if _VERSION_RE.match(ver) else ""


def launch_self_updater(parent, version, current_version):
    """Opens a terminal running clara_self_updater.sh. Returns True when a terminal was launched."""
    import os, shutil, subprocess

    ver = _safe_version(version)
    if not ver:
        QMessageBox.warning(
            parent,
            "Invalid Update",
            "The update server returned an invalid version number, so the updater was not started.",
        )
        return False

    script_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "scripts", "clara_self_updater.sh"))
    if not os.path.exists(script_path):
        for sp in _UPDATER_SCRIPT_PATHS:
            if os.path.exists(sp):
                script_path = sp
                break

    cmd_str = f"bash '{script_path}' '{ver}' '{_safe_version(current_version)}'"

    found_term = None
    for cand in (os.environ.get("TERMINAL"),) + _TERMINALS:
        if cand and shutil.which(cand):
            found_term = cand
            break

    if not found_term:
        QMessageBox.warning(
            parent,
            "Terminal Not Found",
            f"Could not automatically locate a terminal emulator.\nPlease run the following command manually in your terminal:\n\n{cmd_str}"
        )
        return False

    try:
        if found_term in ("gnome-terminal", "mate-terminal", "xfce4-terminal", "tilix"):
            subprocess.Popen([found_term, "--", "bash", "-c", cmd_str])
        elif found_term in ("konsole", "terminator"):
            subprocess.Popen([found_term, "-e", f"bash -c \"{cmd_str}\""])
        else:
            subprocess.Popen([found_term, "-e", "bash", "-c", cmd_str])
        return True
    except Exception as e:
        QMessageBox.warning(
            parent,
            "Error Launching Terminal",
            f"Failed to launch {found_term}:\n{e}\n\nPlease run:\n{cmd_str}"
        )
        return False


def _apply_banner_style(widget, badge, frame_name, border_color, badge_fg,
                        accent_color, accent_hover, accent_selector,
                        padding="3px 10px", extra_rules=""):
    """One place for both notification banners' stylesheet, system palette or Catppuccin."""
    try:
        from styles.theme_manager import theme_manager, find_closest_system_color
        from qt_compat import QApplication, QPalette
    except ImportError:
        return

    if theme_manager.is_using_system():
        app = QApplication.instance()
        pal = app.palette() if app else QPalette()
        bg_col = find_closest_system_color("#181825", pal).name()
        border_col = find_closest_system_color(border_color, pal).name()
        text_col = pal.color(QPalette.WindowText).name()
        btn_bg = pal.color(QPalette.Button).name()
        btn_fg = pal.color(QPalette.ButtonText).name()
        accent_bg = pal.color(QPalette.Highlight).name()
        accent_fg = pal.color(QPalette.HighlightedText).name()
        mid_border = pal.color(QPalette.Mid).name()

        widget.setStyleSheet(f"""
            QFrame#{frame_name} {{
                background-color: {bg_col};
                border-bottom: 2px solid {border_col};
                padding: 4px 10px;
            }}
            QLabel {{
                color: {text_col};
                font-size: 12px;
            }}
            QPushButton {{
                background-color: {btn_bg};
                color: {btn_fg};
                border: 1px solid {mid_border};
                border-radius: 4px;
                padding: {padding};
                font-size: 11px;
            }}
            QPushButton:hover {{
                background-color: {pal.color(QPalette.Midlight).name()};
            }}
            QPushButton{accent_selector} {{
                background-color: {accent_bg};
                color: {accent_fg};
                font-weight: bold;
                border: none;
            }}
        """)
        badge.setStyleSheet(
            f"background-color: {border_col}; color: {pal.color(QPalette.Base).name()}; "
            "font-weight: bold; border-radius: 3px; padding: 2px 4px;"
        )
    else:
        widget.setStyleSheet(f"""
            QFrame#{frame_name} {{
                background-color: #181825;
                border-bottom: 2px solid {border_color};
                padding: 4px 10px;
            }}
            QLabel {{
                color: #CDD6F4;
                font-size: 12px;
            }}
            QPushButton {{
                background-color: #313244;
                color: #CDD6F4;
                border: 1px solid #45475A;
                border-radius: 4px;
                padding: {padding};
                font-size: 11px;
            }}
            QPushButton:hover {{
                background-color: #45475A;
            }}
            QPushButton{accent_selector} {{
                background-color: {accent_color};
                color: #11111B;
                font-weight: bold;
                border: none;
            }}
            QPushButton{accent_selector}:hover {{
                background-color: {accent_hover};
            }}
            {extra_rules}
        """)
        badge.setStyleSheet(
            f"background-color: {border_color}; color: {badge_fg}; "
            "font-weight: bold; border-radius: 3px; padding: 2px 4px;"
        )

def parse_semver(ver_str):
    """Normalize version string into comparable tuple of ints."""
    clean = ver_str.strip().lstrip("v").split("-")[0]
    parts = []
    for p in clean.split("."):
        try:
            parts.append(int(p))
        except ValueError:
            parts.append(0)
    while len(parts) < 3:
        parts.append(0)
    return tuple(parts)

class UpdateCheckThread(QThread):
    update_available = pyqtSignal(dict)  # emits release dict
    no_update_found = pyqtSignal(str)    # emits current version
    check_failed = pyqtSignal(str)       # emits error message

    def __init__(self, parent=None, is_manual=False):
        super().__init__(parent)
        self.is_manual = is_manual

    def run(self):
        try:
            req = urllib.request.Request(
                GITHUB_RELEASES_URL,
                headers={"User-Agent": f"Clara/{VERSION}"}
            )
            with urllib.request.urlopen(req, timeout=5) as resp:
                if resp.status == 200:
                    data = json.loads(resp.read().decode("utf-8"))
                    latest_ver = data.get("latest", "")
                    if not latest_ver:
                        if self.is_manual:
                            self.check_failed.emit("Invalid release response received.")
                        return

                    # Check against skipped version in settings (only for background check)
                    if not self.is_manual:
                        settings = QSettings("falkTX", "Carla2")
                        skipped = settings.value("Clara/SkippedUpdateVersion", "")
                        if skipped == latest_ver:
                            return

                    if parse_semver(latest_ver) > parse_semver(VERSION):
                        # Verify that the GitHub release and its built assets actually exist
                        has_built_assets = False
                        try:
                            api_req = urllib.request.Request(
                                GITHUB_API_LATEST,
                                headers={"User-Agent": f"Clara/{VERSION}", "Accept": "application/vnd.github.v3+json"}
                            )
                            with urllib.request.urlopen(api_req, timeout=5) as api_resp:
                                if api_resp.status == 200:
                                    rel_data = json.loads(api_resp.read().decode("utf-8"))
                                    rel_tag = rel_data.get("tag_name", "").lstrip("v")
                                    assets = rel_data.get("assets", [])
                                    # Filter for compiled package assets (.deb, .rpm, .tar.zst)
                                    pkg_assets = [
                                        a for a in assets
                                        if any(a.get("name", "").endswith(ext) for ext in (".deb", ".rpm", ".tar.zst"))
                                    ]
                                    # If the latest release matches and has compiled distro binaries uploaded
                                    if parse_semver(rel_tag) >= parse_semver(latest_ver) and len(pkg_assets) >= 3:
                                        has_built_assets = True
                        except Exception:
                            # If GitHub API fails or is rate-limited, fall through to release info
                            has_built_assets = True


                        if has_built_assets:
                            rel_info = data.get("releases", {}).get(latest_ver, {})
                            rel_info["version"] = latest_ver
                            rel_info["_all_releases"] = data.get("releases", {})
                            self.update_available.emit(rel_info)
                        else:
                            # Update was tagged but packaging workflow is still compiling/uploading
                            if self.is_manual:
                                self.check_failed.emit(f"Clara v{latest_ver} is currently being built and packaged on GitHub. Please check back in a few minutes!")
                    else:
                        if self.is_manual:
                            self.no_update_found.emit(VERSION)
                else:
                    if self.is_manual:
                        self.check_failed.emit(f"Server returned status {resp.status}")
        except Exception as e:
            if self.is_manual:
                self.check_failed.emit(str(e))


class UpdateChangelogDialog(QDialog):
    """Changelog & Installation guide viewer dialog."""
    def __init__(self, release_info, parent=None, current_version=None):
        super().__init__(parent)
        self.release_info = release_info
        target_ver = release_info.get("version", "")
        from carla_shared import CLARA_VERSION_STRING
        curr_ver_display = current_version or CLARA_VERSION_STRING.lstrip("v")
        self.setWindowTitle("Clara Update Details")
        self.resize(580, 480)
        layout = QVBoxLayout(self)

        title = QLabel(f"<h2>Update Available: v{curr_ver_display} \u2192 v{target_ver}</h2>")
        summary = QLabel(f"<b>{release_info.get('summary', '')}</b>")
        summary.setWordWrap(True)
        layout.addWidget(title)
        layout.addWidget(summary)

        text_edit = QTextEdit()
        text_edit.setReadOnly(True)

        html_content = ""
        curr = current_version or CLARA_VERSION_STRING.lstrip("v")
        releases = release_info.get("_all_releases")
        if not releases:
            try:
                import urllib.request
                req = urllib.request.Request(
                    "https://raw.githubusercontent.com/acropolis914/Clara/main/releases.json",
                    headers={"User-Agent": f"Clara/{curr}"}
                )
                with urllib.request.urlopen(req, timeout=5) as resp:
                    if resp.status == 200:
                        releases = json.loads(resp.read().decode("utf-8")).get("releases", {})
            except Exception:
                releases = None

        entries = []
        for ver_key, rel_data in (releases or {}).items():
            try:
                version = parse_semver(ver_key)
                if version > parse_semver(curr) and version <= parse_semver(target_ver):
                    entries.append((version, ver_key, rel_data))
            except Exception:
                continue
        entries.sort(key=lambda item: item[0])

        for _version, ver_key, rel_data in entries:
            date = rel_data.get("date", "")
            summary_text = rel_data.get("summary", "")
            html_content += f"<h3>v{ver_key}" + (f" \u2014 {date}" if date else "") + "</h3>"
            if summary_text:
                html_content += f"<p><b>{summary_text}</b></p>"
            changes = rel_data.get("changes", [])
            if changes:
                html_content += "<ul>"
                for change in changes:
                    html_content += f"<li>{change}</li>"
                html_content += "</ul>"

        if not html_content:
            html_content = "<h3>What's Changed</h3><ul>"
            for change in release_info.get("changes", []):
                html_content += f"<li>{change}</li>"
            html_content += "</ul>"

        inst = release_info.get("installation", {})
        if inst:
            html_content += "<h3>Installation Guide</h3><ul>"
            for distro, cmd in inst.items():
                html_content += f"<li><b>{distro.title()}</b>: <code>{cmd}</code></li>"
            html_content += "</ul>"

        text_edit.setHtml(html_content)
        layout.addWidget(text_edit)

        btn_row = QHBoxLayout()
        install_btn = QPushButton("Update Now")
        install_btn.setStyleSheet("background-color: #A6E3A1; color: #11111B; font-weight: bold; padding: 4px 12px;")
        install_btn.clicked.connect(self.run_terminal_installer)
        btn_row.addWidget(install_btn)

        releases_btn = QPushButton("Releases Page")
        releases_btn.clicked.connect(self.open_download_page)
        btn_row.addWidget(releases_btn)

        btn_row.addStretch()

        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.accept)
        btn_row.addWidget(close_btn)

        layout.addLayout(btn_row)

    def run_terminal_installer(self):
        from carla_shared import CLARA_VERSION_STRING
        if launch_self_updater(self, self.release_info.get("version", ""), CLARA_VERSION_STRING.lstrip("v")):
            self.accept()

    def open_download_page(self):
        url = self.release_info.get("url") or f"https://github.com/acropolis914/Clara/releases/tag/v{self.release_info.get('version', '')}"
        QDesktopServices.openUrl(QUrl(url))


class UpdateNotificationBanner(QFrame):
    """Sleek top banner displayed when an update is available."""
    def __init__(self, release_info, parent=None):
        super().__init__(parent)
        self.release_info = release_info
        self.version = release_info.get("version", "")
        self.urgency = release_info.get("urgency", "minor").lower()
        self.setObjectName("UpdateNotificationBanner")

        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 4, 8, 4)
        layout.setSpacing(10)

        # Urgency badge
        self.badge = QLabel(f" {self.urgency.upper()} ")
        layout.addWidget(self.badge)

        self.update_theme_styling()

        msg = QLabel(f"A new version of <b>Clara (v{self.version})</b> is available!")
        layout.addWidget(msg)

        layout.addStretch()

        # Buttons
        install_btn = QPushButton("Update Now")
        install_btn.setObjectName("InstallBtn")
        install_btn.setToolTip("Run automated interactive terminal installer")
        install_btn.clicked.connect(self.run_terminal_installer)
        layout.addWidget(install_btn)

        releases_btn = QPushButton("Releases Page")
        releases_btn.setObjectName("ReleasesBtn")
        releases_btn.setToolTip("Open GitHub Releases page in web browser")
        releases_btn.clicked.connect(self.open_releases_page)
        layout.addWidget(releases_btn)

        changelog_btn = QPushButton("View Notes")
        changelog_btn.setObjectName("ChangelogBtn")
        changelog_btn.clicked.connect(self.show_changelog)
        layout.addWidget(changelog_btn)

        hide_btn = QPushButton("Hide")
        hide_btn.setToolTip("Dismiss banner for this session")
        hide_btn.clicked.connect(self.hide_banner)
        layout.addWidget(hide_btn)

        skip_btn = QPushButton("Skip Version")
        skip_btn.setToolTip("Do not prompt again for this version")
        skip_btn.clicked.connect(self.confirm_skip)
        layout.addWidget(skip_btn)

    def run_terminal_installer(self):
        from carla_shared import CLARA_VERSION_STRING
        launch_self_updater(self, self.version, CLARA_VERSION_STRING.lstrip("v"))

    def open_releases_page(self):
        url = self.release_info.get("url") or f"https://github.com/acropolis914/Clara/releases/tag/v{self.version}"
        QDesktopServices.openUrl(QUrl(url))

    def show_changelog(self):
        dlg = UpdateChangelogDialog(self.release_info, self)
        dlg.exec_()

    def hide_banner(self):
        self.setVisible(False)

    def update_theme_styling(self):
        badge_colors = {
            "critical": ("#F38BA8", "#1E1E2E"),
            "suggested": ("#89B4FA", "#1E1E2E"),
            "minor": ("#A6ADC8", "#1E1E2E")
        }
        badge_bg, badge_fg = badge_colors.get(self.urgency, badge_colors["minor"])

        _apply_banner_style(
            self, self.badge, "UpdateNotificationBanner",
            border_color=badge_bg, badge_fg=badge_fg,
            accent_color="#A6E3A1", accent_hover="#94E2D5", accent_selector="#InstallBtn",
            extra_rules="""
                QPushButton#ReleasesBtn {
                    background-color: #313244;
                    color: #CDD6F4;
                }
                QPushButton#ReleasesBtn:hover {
                    background-color: #45475A;
                }
                QPushButton#ChangelogBtn {
                    background-color: #89B4FA;
                    color: #11111B;
                    font-weight: bold;
                }
            """,
        )

    def confirm_skip(self):
        reply = QMessageBox.question(
            self,
            "Skip Version",
            f"Are you sure you want to skip Clara v{self.version}?\nYou won't be notified about this update again.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            settings = QSettings("falkTX", "Carla2")
            settings.setValue("Clara/SkippedUpdateVersion", self.version)
            self.setVisible(False)


class SupportNotificationBanner(QFrame):
    """Subtle support banner prompted after runtime duration with snooze / never options."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("SupportNotificationBanner")

        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 4, 8, 4)
        layout.setSpacing(8)

        self.badge = QLabel(" SUPPORT ")
        layout.addWidget(self.badge)

        self.update_theme_styling()

        msg = QLabel("Enjoying Clara? Consider supporting ongoing development and maintenance:")
        layout.addWidget(msg)

        # Sponsor Buttons from FUNDING.yml
        btn_gh_acro = QPushButton("GitHub (acropolis914)")
        btn_gh_acro.setObjectName("SponsorBtn")
        btn_gh_acro.clicked.connect(lambda: QDesktopServices.openUrl(QUrl("https://github.com/sponsors/acropolis914")))
        layout.addWidget(btn_gh_acro)

        btn_gh_falk = QPushButton("GitHub (falkTX)")
        btn_gh_falk.setObjectName("SponsorBtn")
        btn_gh_falk.clicked.connect(lambda: QDesktopServices.openUrl(QUrl("https://github.com/sponsors/falkTX")))
        layout.addWidget(btn_gh_falk)

        btn_patreon = QPushButton("Patreon")
        btn_patreon.clicked.connect(lambda: QDesktopServices.openUrl(QUrl("https://patreon.com/falkTX")))
        layout.addWidget(btn_patreon)

        btn_liberapay = QPushButton("Liberapay")
        btn_liberapay.clicked.connect(lambda: QDesktopServices.openUrl(QUrl("https://liberapay.com/falkTX")))
        layout.addWidget(btn_liberapay)

        btn_paypal = QPushButton("PayPal")
        btn_paypal.clicked.connect(lambda: QDesktopServices.openUrl(QUrl("https://paypal.me/paulharveysuarnaba")))
        layout.addWidget(btn_paypal)

        layout.addStretch()

        btn_month = QPushButton("Hide for 1 Month")
        btn_month.setToolTip("Do not prompt again for 30 days")
        btn_month.clicked.connect(self.hide_for_month)
        layout.addWidget(btn_month)

        btn_never = QPushButton("Never Show Again")
        btn_never.setToolTip("Never show this banner again")
        btn_never.clicked.connect(self.hide_forever)
        layout.addWidget(btn_never)

        btn_close = QPushButton("Close")
        btn_close.setToolTip("Dismiss for current session")
        btn_close.clicked.connect(self.close_session)
        layout.addWidget(btn_close)

    def update_theme_styling(self):
        _apply_banner_style(
            self, self.badge, "SupportNotificationBanner",
            border_color="#F5C2E7", badge_fg="#11111B",
            accent_color="#F5C2E7", accent_hover="#F5E0DC", accent_selector="#SponsorBtn",
            padding="3px 8px",
        )

    def close_session(self):
        self.setVisible(False)

    def hide_for_month(self):
        import time
        settings = QSettings("falkTX", "Carla2")
        # Hide for 30 days (seconds)
        settings.setValue("Clara/SupportBannerSnoozeUntil", int(time.time() + (30 * 86400)))
        self.setVisible(False)

    def hide_forever(self):
        settings = QSettings("falkTX", "Carla2")
        settings.setValue("Clara/SupportBannerNeverShow", True)
        self.setVisible(False)
