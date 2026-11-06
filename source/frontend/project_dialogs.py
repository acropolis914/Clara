#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2011-2025 Filipe Coelho <falktx@falktx.com>
# SPDX-License-Identifier: GPL-2.0-or-later

# ------------------------------------------------------------------------------------------------------------
# Imports (Global)

import os
from abc import abstractmethod

# ------------------------------------------------------------------------------------------------------------
# Imports (PyQt)

from qt_compat import qt_config

if qt_config == 5:
    from PyQt5.QtCore import pyqtSignal, pyqtSlot, Qt, QByteArray
    from PyQt5.QtGui import QCursor, QIcon, QPalette, QPixmap
    from PyQt5.QtWidgets import (
        QApplication,
        QDialog,
        QFileDialog,
        QHBoxLayout,
        QInputDialog,
        QLabel,
        QMenu,
        QMessageBox,
        QProgressBar,
        QPushButton,
        QScrollArea,
        QTextEdit,
        QVBoxLayout,
        QWidget,
    )
elif qt_config == 6:
    from PyQt6.QtCore import pyqtSignal, pyqtSlot, Qt, QByteArray
    from PyQt6.QtGui import QCursor, QIcon, QPalette, QPixmap
    from PyQt6.QtWidgets import (
        QApplication,
        QDialog,
        QFileDialog,
        QHBoxLayout,
        QInputDialog,
        QLabel,
        QMenu,
        QMessageBox,
        QProgressBar,
        QPushButton,
        QScrollArea,
        QTextEdit,
        QVBoxLayout,
        QWidget,
    )

# ------------------------------------------------------------------------------------------------------------
# Imports (Custom)

import ui_carla_edit
import ui_carla_parameter

from carla_backend import (
    BINARY_NATIVE,
    CARLA_VERSION_STRING,
    CARLA_OS_MAC,
    CARLA_OS_WIN,
    PLUGIN_INTERNAL,
    PLUGIN_DSSI,
    PLUGIN_LV2,
    PLUGIN_VST2,
    PLUGIN_SF2,
    PLUGIN_SFZ,
    PLUGIN_CAN_DRYWET,
    PLUGIN_CAN_VOLUME,
    PLUGIN_CAN_BALANCE,
    PLUGIN_CAN_PANNING,
    PLUGIN_CATEGORY_SYNTH,
    PLUGIN_OPTION_FIXED_BUFFERS,
    PLUGIN_OPTION_FORCE_STEREO,
    PLUGIN_OPTION_MAP_PROGRAM_CHANGES,
    PLUGIN_OPTION_USE_CHUNKS,
    PLUGIN_OPTION_SEND_CONTROL_CHANGES,
    PLUGIN_OPTION_SEND_CHANNEL_PRESSURE,
    PLUGIN_OPTION_SEND_NOTE_AFTERTOUCH,
    PLUGIN_OPTION_SEND_PITCHBEND,
    PLUGIN_OPTION_SEND_ALL_SOUND_OFF,
    PLUGIN_OPTION_SEND_PROGRAM_CHANGES,
    PLUGIN_OPTION_SKIP_SENDING_NOTES,
    PARAMETER_DRYWET,
    PARAMETER_VOLUME,
    PARAMETER_BALANCE_LEFT,
    PARAMETER_BALANCE_RIGHT,
    PARAMETER_PANNING,
    PARAMETER_CTRL_CHANNEL,
    PARAMETER_IS_ENABLED,
    PARAMETER_IS_AUTOMATABLE,
    PARAMETER_IS_READ_ONLY,
    PARAMETER_USES_SCALEPOINTS,
    PARAMETER_USES_CUSTOM_TEXT,
    PARAMETER_CAN_BE_CV_CONTROLLED,
    PARAMETER_INPUT, PARAMETER_OUTPUT,
    CONTROL_INDEX_NONE,
    CONTROL_INDEX_MIDI_PITCHBEND,
    CONTROL_INDEX_MIDI_LEARN,
    CONTROL_INDEX_CV
)

from carla_shared import (
    MIDI_CC_LIST, MAX_MIDI_CC_LIST_ITEM,
    countDecimalPoints,
    fontMetricsHorizontalAdvance,
    setUpSignals,
    gCarla
)

from carla_utils import getPluginTypeAsString

from widgets.collapsablewidget import CollapsibleBox
from widgets.pixmapkeyboard import PixmapKeyboardHArea

from project_storage import storage_manager

# ------------------------------------------------------------------------------------------------------------
# Carla GUI defines

ICON_STATE_ON   = 3 # turns on, sets as wait
ICON_STATE_WAIT = 2 # nothing, sets as off
ICON_STATE_OFF  = 1 # turns off, sets as null
ICON_STATE_NULL = 0 # nothing

# ------------------------------------------------------------------------------------------------------------
# Plugin Parameter

class ProjectLoadSummaryDialog(QDialog):
    def __init__(self, parent, filename, issues=None, raw_log=None):
        super().__init__(parent)
        self.setWindowTitle(self.tr("Project Load Summary - Issues Detected"))
        self.setMinimumSize(600, 420)

        layout = QVBoxLayout(self)
        layout.setSpacing(8)
        layout.setContentsMargins(12, 12, 12, 12)

        title = QLabel(f"<b>{self.tr('Warnings / Issues occurred while loading:')}</b><br>{os.path.basename(filename)}")
        layout.addWidget(title)

        if issues:
            issues_box = QTextEdit(self)
            issues_box.setReadOnly(True)
            issues_box.setMaximumHeight(110)
            issues_text = self.tr("Skipped / Errored Items:\n") + "\n".join(f"• {i}" for i in issues)
            issues_box.setPlainText(issues_text)
            layout.addWidget(issues_box)

        lbl_log = QLabel(self.tr("<b>Diagnostic Log:</b>"))
        layout.addWidget(lbl_log)

        self.log_text = QTextEdit(self)
        self.log_text.setReadOnly(True)
        self.full_log_content = raw_log or "No log messages recorded."
        self.log_text.setPlainText(self.full_log_content)
        layout.addWidget(self.log_text)

        btn_layout = QHBoxLayout()
        copy_btn = QPushButton(self.tr("Copy Log to Clipboard"), self)
        copy_btn.clicked.connect(self._copy_to_clipboard)
        btn_layout.addWidget(copy_btn)

        btn_layout.addStretch()

        close_btn = QPushButton(self.tr("Close"), self)
        close_btn.clicked.connect(self.accept)
        btn_layout.addWidget(close_btn)

        layout.addLayout(btn_layout)

    def _copy_to_clipboard(self):
        from qt_compat import QTimer
        clip = QApplication.clipboard()
        if clip:
            clip.setText(self.full_log_content)
            orig_title = self.windowTitle()
            self.setWindowTitle(self.tr("✓ Log Copied to Clipboard!"))
            QTimer.singleShot(2000, lambda: self.setWindowTitle(orig_title))


# ------------------------------------------------------------------------------------------------------------
# Modern Project Loading Dialog with indeterminate animation and detailed status text

class ProjectLoadingDialog(QDialog):
    def __init__(self, parent=None, filename="", offer_mode=False, on_load_accepted=None, on_load_declined=None,
                 recover_mode=False, offer_detail=None):
        super().__init__(parent)
        from qt_compat import QTimer, QPushButton, QCheckBox

        self.setWindowTitle(self.tr("Loading Project..."))
        self.setFixedSize(460, 180 if offer_detail else (150 if offer_mode else 120))
        app_modal = getattr(Qt, "ApplicationModal", None) or getattr(getattr(Qt, "WindowModality", object), "ApplicationModal", None)
        if app_modal is not None:
            self.setWindowModality(app_modal)

        self._start_time = 0
        self._current_progress = 12.0
        self._target_progress = 20.0
        self._explicit_progress = False
        self._offer_mode = offer_mode
        self._recover_mode = recover_mode
        self._offer_detail = offer_detail
        self._on_load_accepted = on_load_accepted
        self._on_load_declined = on_load_declined
        self._accepted = False

        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 14, 18, 14)
        layout.setSpacing(8)

        # 1. Top row: Filename & Percentage
        header_layout = QHBoxLayout()
        header_layout.setSpacing(8)

        basename = os.path.basename(filename) if filename else self.tr("Project")
        if recover_mode:
            title_prefix = self.tr("Recover Session:")
        elif offer_mode:
            title_prefix = self.tr("Recent Session:")
        else:
            title_prefix = self.tr("Loading:")
        self.lbl_title = QLabel(f"<b>{title_prefix}</b> {basename}", self)
        header_layout.addWidget(self.lbl_title, 1)

        self.lbl_percent = QLabel(f"{int(self._current_progress)}%", self)
        self.lbl_percent.setStyleSheet("font-weight: bold; color: #89b4fa;")
        if offer_mode:
            self.lbl_percent.hide()
        header_layout.addWidget(self.lbl_percent)
        layout.addLayout(header_layout)

        # 2. Glowing gradient progress bar (never frozen)
        self.progressBar = QProgressBar(self)
        self.progressBar.setRange(0, 100)
        self.progressBar.setValue(int(self._current_progress))
        self.progressBar.setTextVisible(False)
        self.progressBar.setFixedHeight(6)
        self.progressBar.setStyleSheet("""
            QProgressBar {
                background-color: #313244;
                border: none;
                border-radius: 3px;
            }
            QProgressBar::chunk {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #89b4fa, stop:0.5 #cba6f7, stop:1 #f5c2e7);
                border-radius: 3px;
            }
        """)
        if offer_mode:
            self.progressBar.hide()
        layout.addWidget(self.progressBar)

        # 3. Status detail label
        if offer_mode and offer_detail:
            initial_detail = offer_detail
        elif offer_mode:
            initial_detail = self.tr("No project is currently open. Would you like to restore this session?")
        else:
            initial_detail = self.tr("Reading project file & canvas geometry...")
        self.lbl_detail = QLabel(initial_detail, self)
        self.lbl_detail.setStyleSheet("color: #a6adc8; font-size: 11px;")
        self.lbl_detail.setWordWrap(True)
        layout.addWidget(self.lbl_detail)

        # 4. Offer button container (visible only in offer_mode)
        self.offer_widget = QWidget(self)
        offer_layout = QVBoxLayout(self.offer_widget)
        offer_layout.setContentsMargins(0, 4, 0, 0)
        offer_layout.setSpacing(6)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)

        self.cb_autoload = QCheckBox(self.tr("Always load last save on startup"), self.offer_widget)
        self.cb_autoload.setStyleSheet("color: #6c7086; font-size: 11px;")
        btn_row.addWidget(self.cb_autoload, 1)

        self.b_skip = QPushButton(self.tr("Start Empty"), self.offer_widget)
        self.b_skip.setStyleSheet("""
            QPushButton {
                background-color: #313244;
                color: #cdd6f4;
                border: 1px solid #45475a;
                border-radius: 4px;
                padding: 4px 12px;
                font-size: 11px;
            }
            QPushButton:hover {
                background-color: #45475a;
            }
        """)
        self.b_skip.clicked.connect(self._on_skip_clicked)
        btn_row.addWidget(self.b_skip)

        self.b_load = QPushButton(self.tr("Recover Session") if recover_mode else self.tr("Load Session"), self.offer_widget)
        self.b_load.setStyleSheet("""
            QPushButton {
                background-color: #cba6f7;
                color: #11111b;
                border: none;
                border-radius: 4px;
                padding: 4px 14px;
                font-weight: bold;
                font-size: 11px;
            }
            QPushButton:hover {
                background-color: #b4befe;
            }
        """)
        self.b_load.clicked.connect(self._on_load_clicked)
        btn_row.addWidget(self.b_load)

        offer_layout.addLayout(btn_row)
        layout.addWidget(self.offer_widget)

        if not offer_mode:
            self.offer_widget.hide()

        # Smooth auto-crawler timer so progress bar NEVER looks frozen during long tasks
        self._anim_timer = QTimer(self)
        self._anim_timer.setInterval(40)
        self._anim_timer.timeout.connect(self._on_tick)
        if not offer_mode:
            self._anim_timer.start()

    def _on_load_clicked(self):
        self._accepted = True
        if self.cb_autoload.isChecked():
            try:
                from carla_shared import gCarla, QSafeSettings
                QSafeSettings().setValue("Main/AutoloadLastSave", True)
                gCarla.autoload_lastsave = True
            except Exception:
                pass
        self.startLoading()
        if callable(self._on_load_accepted):
            self._on_load_accepted()

    def _on_skip_clicked(self):
        self._accepted = False
        self.dismiss()
        if callable(self._on_load_declined):
            self._on_load_declined()

    def closeEvent(self, event):
        if self._offer_mode and not self._accepted:
            if callable(self._on_load_declined):
                self._on_load_declined()
        super().closeEvent(event)

    def startLoading(self, detail=None):
        self._offer_mode = False
        self.offer_widget.hide()
        self.progressBar.show()
        self.lbl_percent.show()
        title_text = self.lbl_title.text()
        self.lbl_title.setText(
            title_text.replace(self.tr("Recent Session:"), self.tr("Loading:"))
                      .replace(self.tr("Recover Session:"), self.tr("Loading:"))
        )
        self.lbl_detail.setText(detail or self.tr("Preparing project file & engine..."))
        self._explicit_progress = False
        self._target_progress = 22.0
        self.setFixedSize(450, 120)
        self._anim_timer.start()
        self.repaint()
        QApplication.processEvents()

    def _on_tick(self):
        if self._offer_mode:
            return
        if self._current_progress < self._target_progress:
            step = max(0.5, (self._target_progress - self._current_progress) * 0.28)
            self._current_progress = min(self._target_progress, self._current_progress + step)
        elif not self._explicit_progress and self._current_progress < 93.0:
            # Background crawl only while the real progress is unknown
            self._current_progress += 0.12

        val_int = int(self._current_progress)
        self.progressBar.setValue(val_int)
        self.lbl_percent.setText(f"{val_int}%")

    def show(self):
        import time
        self._start_time = time.time()
        self._current_progress = 12.0
        self._target_progress = 22.0
        self._explicit_progress = False
        super().show()
        QApplication.processEvents()

    def setDetail(self, text):
        if text:
            self.lbl_detail.setText(str(text))
            self.repaint()
            QApplication.processEvents()

    def setProgress(self, value, detail=None):
        """Set real progress (0-99). Once set, the bar stops crawling on its own."""
        try:
            value = float(value)
        except (TypeError, ValueError):
            return
        self._explicit_progress = True
        self._target_progress = max(0.0, min(99.0, value))
        if detail:
            self.lbl_detail.setText(str(detail))
        self.repaint()
        QApplication.processEvents()

    def dismiss(self, min_dwell_ms=0):
        try:
            self._anim_timer.stop()
        except Exception:
            pass
        self._current_progress = 100.0
        self.progressBar.setValue(100)
        self.lbl_percent.setText("100%")
        self.lbl_detail.setText(self.tr("Ready!"))
        self.repaint()
        QApplication.processEvents()
        self.close()
        self.deleteLater()




# ------------------------------------------------------------------------------------------------------------
# Inline project loading banner (part of the main window, not a dialog)

class InlineLoadingBanner(QWidget):
    def __init__(self, parent=None, filename=""):
        super().__init__(parent)
        from qt_compat import QTimer, QProgressBar, QHBoxLayout, QVBoxLayout, QLabel

        self.setObjectName("InlineLoadingBanner")
        self.setStyleSheet("""
            QFrame#InlineLoadingBanner {
                background-color: #181825;
                border-bottom: 2px solid #89b4fa;
            }
            QLabel { color: #cdd6f4; font-size: 11px; }
            QProgressBar { background-color: #313244; border: none; border-radius: 3px; }
            QProgressBar::chunk {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #89b4fa, stop:0.5 #cba6f7, stop:1 #f5c2e7);
                border-radius: 3px;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 6, 10, 8)
        layout.setSpacing(4)

        row = QHBoxLayout()
        name = os.path.basename(filename) if filename else "Project"
        self.lbl_title = QLabel(f"<b>Loading:</b> {name}", self)
        self.lbl_percent = QLabel("8%", self)
        row.addWidget(self.lbl_title, 1)
        row.addWidget(self.lbl_percent)
        layout.addLayout(row)

        self.lbl_readonly = QLabel(
            "READ-ONLY · patchbay and rack are locked until loading finishes", self)
        self.lbl_readonly.setStyleSheet(
            "color: #f9e2af; font-size: 10px; font-weight: bold;")
        self.lbl_readonly.setWordWrap(True)
        self.lbl_readonly.setToolTip(
            "Pan and zoom stay available, but nodes, plugins and cables cannot be "
            "edited until the project has finished loading.")
        layout.addWidget(self.lbl_readonly)

        self.progressBar = QProgressBar(self)
        self.progressBar.setRange(0, 100)
        self.progressBar.setValue(8)
        self.progressBar.setTextVisible(False)
        self.progressBar.setFixedHeight(5)
        layout.addWidget(self.progressBar)

        self.lbl_detail = QLabel("Preparing project & engine...", self)
        layout.addWidget(self.lbl_detail)

        self._current = 8.0
        self._target = 20.0
        self._explicit = False
        self._timer = QTimer(self)
        self._timer.setInterval(40)
        self._timer.timeout.connect(self._tick)
        self._timer.start()

    def _tick(self):
        if self._current < self._target:
            self._current = min(self._target, self._current + max(0.5, (self._target - self._current) * 0.28))
        elif not self._explicit and self._current < 93.0:
            self._current += 0.12
        value = int(self._current)
        self.progressBar.setValue(value)
        self.lbl_percent.setText(f"{value}%")

    def setDetail(self, text):
        if text:
            self.lbl_detail.setText(str(text))

    def setProgress(self, value, detail=None):
        try:
            value = float(value)
        except (TypeError, ValueError):
            return
        self._explicit = True
        self._target = max(0.0, min(99.0, value))
        if detail:
            self.lbl_detail.setText(str(detail))

    def dismiss(self, min_dwell_ms=0):
        try:
            self._timer.stop()
        except Exception:
            pass
        self.progressBar.setValue(100)
        self.lbl_percent.setText("100%")
        self.lbl_detail.setText("Ready!")
        self.hide()
        self.setParent(None)
        self.deleteLater()



# ------------------------------------------------------------------------------------------------------------
# Main

if __name__ == '__main__':
    from carla_app import CarlaApplication
    from host_app import initHost as _initHost, loadHostSettings as _loadHostSettings

    _app  = CarlaApplication()
    _host = _initHost("Widgets", None, False, False, False)
    _loadHostSettings(_host)

    _host.engine_init("JACK", "Carla-Widgets")
    _host.add_plugin(BINARY_NATIVE, PLUGIN_DSSI, "/usr/lib/dssi/karplong.so", "karplong", "karplong", 0, None, 0x0)
    _host.set_active(0, True)

    gui2 = PluginEdit(None, _host, 0)
    gui2.testTimer()
    gui2.show()

    _app.exit_exec()
