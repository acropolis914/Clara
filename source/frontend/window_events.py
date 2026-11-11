#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Clara contributors
# SPDX-License-Identifier: GPL-2.0-or-later

# Window events, timers, system tray, style and update checks, split out of
# host_app.py. HostWindow inherits this mixin.

import os
import time

from carla_logger import logger

from carla_app import (
    CARLA_DEFAULT_MAIN_USE_PRO_THEME,
    CARLA_KEY_MAIN_USE_PRO_THEME,
    CARLA_OS_MAC,
    CARLA_OS_WIN,
    QT_VERSION,
    QSafeSettings,
    gCarla,
)
from carla_backend import (
    ENGINE_OPTION_FRONTEND_BACKGROUND_COLOR,
    ENGINE_OPTION_FRONTEND_FOREGROUND_COLOR,
    ENGINE_OPTION_FRONTEND_UI_SCALE,
    ENGINE_OPTION_FRONTEND_WIN_ID,
    NSM_CALLBACK_HIDE_OPTIONAL_GUI,
)
from carla_shared import (
    CARLA_DEFAULT_MAIN_MINIMIZE_TO_TRAY,
    CARLA_KEY_MAIN_CONFIRM_EXIT,
    CARLA_KEY_STATUSBAR_SPARKLINE,
    CARLA_KEY_STATUSBAR_SPARKLINE_WINDOW,
    CARLA_DEFAULT_STATUSBAR_SPARKLINE,
    CARLA_DEFAULT_STATUSBAR_SPARKLINE_WINDOW,
    CARLA_KEY_MAIN_MINIMIZE_TO_TRAY,
    log_carla,
)
from update_checker import (
    SupportNotificationBanner,
    UpdateChangelogDialog,
    UpdateCheckThread,
    UpdateNotificationBanner,
)
from patchcanvas import patchcanvas
from qt_compat import (
    PYQT_VERSION,
    QAction,
    QApplication,
    QBrush,
    QColor,
    QCursor,
    QEvent,
    QIcon,
    QImage,
    QMainWindow,
    QMenu,
    QMessageBox,
    QPainter,
    QPalette,
    QPixmap,
    QSettings,
    QSystemTrayIcon,
    QTimer,
    Qt,
    pyqtSlot,
)


class EventsMixin:
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

        # Xruns chip: semantic dot color + context logging on increase
        try:
            x = int(xruns) if xruns >= 0 else 0
            last = getattr(self, "_lastSeenXruns", None)
            if last is not None and x > last:
                for _ in range(min(5, x - last)):
                    self._onXrunsIncreased(x, x - last)
            self._lastSeenXruns = x
            chip = self.ui.b_xruns
            from styles.theme_manager import theme_manager
            token = theme_manager.engine.get_token
            color = (token("green") if x == 0
                     else token("yellow") if x <= 5
                     else token("red"))
            chip.setStyleSheet(
                "QToolButton { color: %s; background: transparent;"
                " border: none; border-radius: 4px; padding: 2px 8px;"
                " font-size: 11px; }" % color)
            if self._xrunRing:
                chip.setToolTip(self.tr(
                    "%d xruns this session\nClick for details and context" % x))
        except Exception:
            pass

        self.ui.b_xruns.setText("%s Xrun%s" % (txt1, txt2))

        # DSP sparkline: settings-driven (enabled, window), decimated pushes
        try:
            enabled = self.fSavedSettings.get(CARLA_KEY_STATUSBAR_SPARKLINE, True)
            window = int(self.fSavedSettings.get(
                CARLA_KEY_STATUSBAR_SPARKLINE_WINDOW,
                CARLA_DEFAULT_STATUSBAR_SPARKLINE_WINDOW))
            spark = getattr(self.ui, "pb_dsp_load", None)
            spark.setVisible(bool(enabled) and spark is not None)
            if enabled and spark is not None and hasattr(spark, "push"):
                if getattr(spark, "window", lambda: None)() != window:
                    spark.setWindow(window)
                now = time.monotonic()
                if now - getattr(self, "_lastDspPush", 0.0) >= 0.25:
                    self._lastDspPush = now
                    spark.push(load)
                cur, avg, mx, win, mn = spark.stats()
                self._lblDspLoad.setText(
                    "<b style='color: %s'>%d%%</b> <span style='color: %s'>"
                    "· avg %.1f%% · %ds</span>" % (
                        token("text-primary"),
                        int(cur), token("text-muted"), avg, win))
                self._lblDspLoad.setToolTip(self.tr(
                    "Current: %d%%\nAverage (%ds window): %.1f%%\n"
                    "Window range: %d%% - %d%%"
                    % (int(cur), win, avg, int(mn), int(mx))))
        except Exception as ex:
            logger.warning("APP", "statusbar sparkline update failed: %s" % ex)

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

        # Only the standalone app owns a tray item. Nested plugin windows and
        # control instances must not add more icons to the tray.
        if getattr(self.host, "isPlugin", False) or getattr(self.host, "isControl", False):
            self.fSystemTrayIcon = None
            return

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

        # Explicit quit paths (claramsg quit, tray quit, SIGINT handling) set
        # fForceQuit; a programmatic exit must never prompt.
        if getattr(self, "fForceQuit", False):
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


