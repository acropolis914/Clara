#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2011-2025 Filipe Coelho <falktx@falktx.com>
# SPDX-License-Identifier: GPL-2.0-or-later

# ------------------------------------------------------------------------------------------------------------
# Imports (Global)

import os
from abc import abstractmethod

# ------------------------------------------------------------------------------------------------------------
# Imports (PyQt)

from qt_compat import (
    QApplication,
    QByteArray,
    QCursor,
    QDialog,
    QFileDialog,
    QHBoxLayout,
    QIcon,
    QInputDialog,
    QLabel,
    QMenu,
    QMessageBox,
    QPalette,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QTextEdit,
    QVBoxLayout,
    QWidget,
    Qt,
    pyqtSignal,
    pyqtSlot,
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

def _themeColor(name, fallback):
    from styles.theme_manager import theme_manager
    return theme_manager.engine.get_token(name, fallback) or fallback


class ProjectSessionOfferDialog(QDialog):
    """Session offer/recover prompt ("Recent Session:" / "Recover Session:").

    Sunset note: this used to be the legacy ProjectLoadingDialog, which also
    doubled as the project loading UI. Loading progress lives exclusively in
    InlineLoadingBanner now - do not reintroduce dialog-based loading here.
    """

    def __init__(self, parent=None, filename="", offer_mode=True, on_load_accepted=None, on_load_declined=None,
                 recover_mode=False, offer_detail=None):
        super().__init__(parent)
        from qt_compat import QTimer, QPushButton, QCheckBox

        self.setWindowTitle(self.tr("Loading Project..."))
        self.setFixedSize(460, 180 if offer_detail else 150)
        app_modal = getattr(Qt, "ApplicationModal", None) or getattr(getattr(Qt, "WindowModality", object), "ApplicationModal", None)
        if app_modal is not None:
            self.setWindowModality(app_modal)

        self._offer_mode = True
        self._recover_mode = recover_mode
        self._offer_detail = offer_detail
        self._on_load_accepted = on_load_accepted
        self._on_load_declined = on_load_declined
        self._accepted = False

        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 14, 18, 14)
        layout.setSpacing(8)

        header_layout = QHBoxLayout()
        header_layout.setSpacing(8)

        basename = os.path.basename(filename) if filename else self.tr("Project")
        title_prefix = self.tr("Recover Session:") if recover_mode else self.tr("Recent Session:")
        self.lbl_title = QLabel(f"<b>{title_prefix}</b> {basename}", self)
        header_layout.addWidget(self.lbl_title, 1)
        layout.addLayout(header_layout)

        initial_detail = offer_detail or self.tr("No project is currently open. Would you like to restore this session?")
        self.lbl_detail = QLabel(initial_detail, self)
        self.lbl_detail.setStyleSheet("color: %s; font-size: 11px;" % _themeColor("text-secondary", "#a6adc8"))
        self.lbl_detail.setWordWrap(True)
        layout.addWidget(self.lbl_detail)

        offer_layout = QVBoxLayout()
        offer_layout.setContentsMargins(0, 4, 0, 0)
        offer_layout.setSpacing(6)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)

        self.cb_autoload = QCheckBox(self.tr("Always load last save on startup"), self)
        self.cb_autoload.setStyleSheet("color: %s; font-size: 11px;" % _themeColor("text-muted", "#6c7086"))
        btn_row.addWidget(self.cb_autoload, 1)

        self.b_skip = QPushButton(self.tr("Start Empty"), self)
        self.b_skip.setStyleSheet("""
            QPushButton {
                background-color: %s;
                color: %s;
                border: 1px solid %s;
                border-radius: 4px;
                padding: 4px 12px;
                font-size: 11px;
            }
            QPushButton:hover {
                background-color: %s;
            }
        """ % (_themeColor("bg-hover", "#313244"), _themeColor("text-primary", "#cdd6f4"),
               _themeColor("border-dim", "#45475a"), _themeColor("border-dim", "#45475a")))
        self.b_skip.clicked.connect(self._on_skip_clicked)
        btn_row.addWidget(self.b_skip)

        self.b_load = QPushButton(self.tr("Recover Session") if recover_mode else self.tr("Load Session"), self)
        self.b_load.setStyleSheet("""
            QPushButton {
                background-color: %s;
                color: %s;
                border: none;
                border-radius: 4px;
                padding: 4px 14px;
                font-weight: bold;
                font-size: 11px;
            }
            QPushButton:hover {
                background-color: %s;
            }
        """ % (_themeColor("purple", "#cba6f7"), _themeColor("bg-primary", "#11111b"),
               _themeColor("magenta", "#b4befe")))
        self.b_load.clicked.connect(self._on_load_clicked)
        btn_row.addWidget(self.b_load)

        offer_layout.addLayout(btn_row)
        layout.addLayout(offer_layout)

    def _on_load_clicked(self):
        self._accepted = True
        if self.cb_autoload.isChecked():
            try:
                from carla_shared import gCarla, QSafeSettings
                QSafeSettings().setValue("Main/AutoloadLastSave", True)
                gCarla.autoload_lastsave = True
            except Exception:
                pass
        self.dismiss()
        if callable(self._on_load_accepted):
            self._on_load_accepted()

    def _on_skip_clicked(self):
        self._accepted = False
        self.dismiss()
        if callable(self._on_load_declined):
            self._on_load_declined()

    def closeEvent(self, event):
        if not self._accepted:
            if callable(self._on_load_declined):
                self._on_load_declined()
        super().closeEvent(event)

    def dismiss(self, min_dwell_ms=0):
        self.close()
        self.deleteLater()




class InlineLoadingBanner(QWidget):
    """Pipeline-aware loading banner: phase chips, one segment per pipeline
    step (engine, each plugin, canvas, session), mono detail + ETA."""

    def __init__(self, parent=None, filename=""):
        super().__init__(parent)
        from qt_compat import QTimer, QProgressBar, QHBoxLayout, QVBoxLayout, QLabel

        self.setObjectName("InlineLoadingBanner")
        self.setStyleSheet(
            "QWidget#InlineLoadingBanner { background-color: %s; border-bottom: 1px solid %s; }"
            % (_themeColor("bg-surface", "#181825"), _themeColor("border-dim", "#313244")))

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 7, 12, 8)
        layout.setSpacing(6)

        # Row 1: project name | phase chips | percent
        row1 = QHBoxLayout()
        row1.setSpacing(10)
        name = os.path.basename(filename) if filename else "Project"
        self.lbl_title = QLabel(name, self)
        self.lbl_title.setStyleSheet(
            "font-weight: 650; font-size: 13px; color: %s;"
            % _themeColor("text-primary", "#cdd6f4"))

        self._phases_order = ("engine", "plugins", "canvas", "session")
        self._phase_labels = {
            "engine": "Engine", "plugins": "Plugins",
            "canvas": "Canvas", "session": "Session",
        }
        self._current_phase = "engine"
        self._phase_done = set()
        self._phase_labels_widgets = {}
        for key in self._phases_order:
            chip = QLabel(self._phase_labels[key], self)
            chip.setObjectName("loadPhase")
            self._phase_labels_widgets[key] = chip
            row1.addWidget(chip)

        self.lbl_percent = QLabel("0%", self)
        self.lbl_percent.setStyleSheet(
            "font-family: 'JetBrains Mono', monospace; font-size: 13px; color: %s;"
            % _themeColor("text-primary", "#cdd6f4"))
        row1.addStretch(1)
        row1.addWidget(self.lbl_title)
        row1.addStretch(1)
        row1.addWidget(self.lbl_percent)
        layout.addLayout(row1)

        # Row 2: the segment bar (built by setPipeline; hidden for unknown
        # totals, where the plain shimmering bar takes over).
        self._segments = []
        self._active_segment = -1
        self._segbar_widget = None
        self._shimmer_phase = 0.0

        self.progressBar = QProgressBar(self)
        self.progressBar.setRange(0, 100)
        self.progressBar.setValue(0)
        self.progressBar.setTextVisible(False)
        self.progressBar.setFixedHeight(6)
        self.progressBar.setStyleSheet(
            "QProgressBar { background: transparent; border: none; }"
            "QProgressBar::chunk { background: %s; border-radius: 3px; }"
            % _themeColor("text-primary", "#cdd6f4"))
        layout.addWidget(self.progressBar)

        # Row 3: READ-ONLY chip | detail | eta
        row2 = QHBoxLayout()
        row2.setSpacing(10)
        self.lbl_readonly = QLabel("READ-ONLY", self)
        self.lbl_readonly.setStyleSheet(
            "color: %s; font-size: 10px; font-weight: bold; letter-spacing: 1px;"
            " border: 1px solid %s; border-radius: 999px; padding: 1px 8px;"
            % (_themeColor("text-secondary", "#a6adc8"),
               _themeColor("border-dim", "#313244")))
        self.lbl_readonly.setToolTip(
            "Pan and zoom stay available, but nodes, plugins and cables cannot be "
            "edited until the project has finished loading.")
        row2.addWidget(self.lbl_readonly)

        self.lbl_detail = QLabel("Preparing project & engine...", self)
        self.lbl_detail.setStyleSheet(
            "color: %s; font-family: 'JetBrains Mono', monospace; font-size: 11.5px;"
            % _themeColor("text-secondary", "#a6adc8"))
        row2.addWidget(self.lbl_detail, 1)

        self.lbl_eta = QLabel("", self)
        self.lbl_eta.setStyleSheet(
            "color: %s; font-family: 'JetBrains Mono', monospace; font-size: 11px;"
            % _themeColor("text-muted", "#6c7086"))
        row2.addWidget(self.lbl_eta)
        layout.addLayout(row2)

        self._current = 8.0
        self._target = 20.0
        self._explicit = False
        self._timer = QTimer(self)
        self._timer.setInterval(40)
        self._timer.timeout.connect(self._tick)

        self._shimmer_timer = QTimer(self)
        self._shimmer_timer.setInterval(80)
        self._shimmer_timer.timeout.connect(self._shimmer_step)
        self._apply_shimmer()
        self._shimmer_timer.start()

    # ------------------------------------------------- color helpers

    def _ink(self):
        """Accent ink for filled segments and shimmer (highlight color)."""
        return _themeColor("accent", "#89b4fa")

    def _apply_shimmer(self):
        """Plain-bar fallback: white shimmer sweeping across the chunk."""
        phase = self._shimmer_phase
        ink = self._ink()
        a = max(0.0, phase - 0.35)
        b = min(1.0, phase + 0.35)
        dim = _themeColor("border-dim", "#313244")
        self.progressBar.setStyleSheet(
            "QProgressBar { background: transparent; border: none; }"
            "QProgressBar::chunk { border-radius: 3px; background: qlineargradient("
            "x1:0, y1:0, x2:1, y2:0, stop:0 %s, stop:%.2f %s, stop:%.2f %s, stop:1 %s); }"
            % (dim, a, ink, b, ink, dim))

    def _shimmer_step(self):
        self._shimmer_phase = (self._shimmer_phase + 0.08) % 1.35
        if not self._segments:
            self._apply_shimmer()
        else:
            self._paint_active_segment()

    # ------------------------------------------------- pipeline segments

    def setPipeline(self, total_plugins):
        """Build the segment bar: [engine] + plugins + [canvas] + [session]."""
        from qt_compat import QWidget, QHBoxLayout
        total_plugins = max(0, int(total_plugins))
        count = total_plugins + 3

        if self._segbar_widget is not None:
            self._segbar_widget.setParent(None)
            self._segbar_widget.deleteLater()
            self._segbar_widget = None
        self._segments = []

        if total_plugins <= 0:
            self.progressBar.show()
            self._apply_shimmer()
            return
        self.progressBar.hide()

        self._segbar_widget = QWidget(self)
        self._segbar_widget.setObjectName("loadSegbar")
        seg_layout = QHBoxLayout(self._segbar_widget)
        seg_layout.setContentsMargins(0, 0, 0, 0)
        seg_layout.setSpacing(4)
        for _ in range(count):
            seg = QLabel(self._segbar_widget)
            seg.setFixedHeight(6)
            seg_layout.addWidget(seg, 1)
            self._segments.append(seg)
        self._segbar_widget.setStyleSheet("QWidget#loadSegbar { background: transparent; }")
        self.layout().insertWidget(1, self._segbar_widget)
        self._segbar_widget.show()
        self.setSegment(0)

    def _paint_active_segment(self):
        """The active segment: accent fill with a subtle lighter shimmer band."""
        index = self._active_segment
        if index < 0 or index >= len(self._segments):
            return
        seg = self._segments[index]
        accent = self._ink()
        tint = _themeColor("accent-tint-15", "#2a3550")
        phase = self._shimmer_phase
        a = max(0.0, phase - 0.25)
        b = min(1.0, phase + 0.25)
        seg.setStyleSheet(
            "QLabel { background: qlineargradient(x1:0, y1:0, x2:1, y2:0,"
            " stop:0 %s, stop:%.2f %s, stop:%.2f %s, stop:1 %s);"
            " border: 1px solid %s; border-radius: 2px; }"
            % (tint, a, accent, b, accent, tint, accent))

    def setSegment(self, index):
        """Mark the segment at `index` as in-progress (0-based over the pipeline)."""
        total = len(self._segments)
        if total == 0 or index < 0:
            return
        self._active_segment = index
        accent = self._ink()
        empty = _themeColor("bg-primary", "#11111b")
        for i, seg in enumerate(self._segments):
            if i < index:
                seg.setStyleSheet(
                    "QLabel { background: %s; border-radius: 2px; }" % accent)
            elif i == index:
                self._paint_active_segment()
            else:
                seg.setStyleSheet(
                    "QLabel { background: %s; border-radius: 2px; }" % empty)
        if index <= 0:
            self.setPhase("engine")
        elif total > 2 and index >= total - 2:
            self.setPhase("canvas" if index == total - 2 else "session")
        elif total > 2:
            self.setPhase("plugins")

    def setPhase(self, name):
        """Highlight the active phase; earlier phases show as done."""
        if name not in self._phases_order:
            return
        self._current_phase = name
        order = self._phases_order
        cur = order.index(name)
        accent = _themeColor("accent", "#89b4fa")
        muted = _themeColor("text-muted", "#6c7086")
        soft_accent = _themeColor("accent-tint-15", "#2a3550")
        for key in order:
            chip = self._phase_labels_widgets[key]
            k = order.index(key)
            if k < cur or key in self._phase_done:
                chip.setStyleSheet(
                    "QLabel#loadPhase { color: %s; font-size: 10px; font-weight: bold;"
                    " padding: 1px 8px; border-radius: 999px; background: transparent; }"
                    % accent)
            elif k == cur:
                chip.setStyleSheet(
                    "QLabel#loadPhase { color: %s; font-size: 10px; font-weight: bold;"
                    " padding: 1px 8px; border-radius: 999px; background: %s; }"
                    % (accent, soft_accent))
            else:
                chip.setStyleSheet(
                    "QLabel#loadPhase { color: %s; font-size: 10px; font-weight: bold;"
                    " padding: 1px 8px; border-radius: 999px; background: transparent; }"
                    % muted)

    def markPhaseDone(self, name):
        self._phase_done.add(name)
        self.setPhase(self._current_phase)

    # ------------------------------------------------- existing API

    def _tick(self):
        if self._current < self._target:
            self._current = min(self._target, self._current + max(0.5, (self._target - self._current) * 0.28))
        elif not self._explicit and self._current < 93.0:
            self._current += 0.12
        value = int(self._current)
        self.lbl_percent.setText(f"{value}%")
        if self._segments:
            self.progressBar.setValue(value)

    def setDetail(self, text):
        if text:
            self.lbl_detail.setText(str(text))

    def setEta(self, text):
        self.lbl_eta.setText(str(text) if text else "")

    def setProgress(self, value, detail=None):
        try:
            value = float(value)
        except (TypeError, ValueError):
            return
        self._explicit = True
        self._target = max(0.0, min(99.0, value))
        self._current = max(self._current, min(self._target, self._current + 25))
        self.lbl_percent.setText("%d%%" % int(min(self._target, self._current)))
        if detail:
            self.lbl_detail.setText(str(detail))

    def dismiss(self, min_dwell_ms=0):
        try:
            self._timer.stop()
            self._shimmer_timer.stop()
        except Exception:
            pass
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
