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
    """Pipeline-aware loading banner - a Qt port of the approved HTML/CSS
    prototype, built with plain box layouts (padding, gaps and rounded
    fills like the CSS box model). One segment per pipeline step: engine,
    each plugin, canvas restore, session finish.
    """

    def __init__(self, parent=None, filename=""):
        super().__init__(parent)
        from qt_compat import (
            QTimer, QProgressBar, QHBoxLayout, QVBoxLayout, QLabel, QWidget,
        )

        self.setObjectName("InlineLoadingBanner")
        # CSS: .banner { padding: 10px 16px 12px; background: gradient
        # surface2 -> surface; border-bottom: 1px solid border; }
        self.setStyleSheet(
            "QWidget#InlineLoadingBanner {"
            " background: qlineargradient(x1:0, y1:0, x2:0, y2:1,"
            " stop:0 %s, stop:1 %s);"
            " border-bottom: 1px solid %s; }"
            % (_themeColor("bg-hover", "#24273a"),
               _themeColor("bg-surface", "#1e2030"),
               _themeColor("border-dim", "#313244")))

        self._accent = _themeColor("accent", "#89b4fa")
        self._mauve = _themeColor("magenta", "#f5c2e7")
        self._muted = _themeColor("text-muted", "#6c7086")
        self._text = _themeColor("text-primary", "#cdd6f4")
        self._border = _themeColor("border-dim", "#313244")
        self._green = _themeColor("green", "#a6e3a1")
        self._soft_accent = _themeColor("accent-tint-15", "#2a3550")
        self._surface2 = _themeColor("bg-hover", "#24273a")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 10, 16, 12)
        layout.setSpacing(0)

        # ---- row 1: name | phases | percent  (CSS .row1, gap 14)
        row1 = QHBoxLayout()
        row1.setContentsMargins(0, 0, 0, 0)
        row1.setSpacing(14)
        name = os.path.basename(filename) if filename else "Project"
        self.lbl_title = QLabel(name, self)
        self.lbl_title.setStyleSheet(
            "font-weight: 600; font-size: 13px; color: %s; background: transparent;"
            % self._text)
        row1.addWidget(self.lbl_title)

        # ---- phase chips (CSS .phase: tick dot + label, padding 3/10/3/8)
        self._phases_order = ("engine", "plugins", "canvas", "session")
        self._current_phase = "engine"
        self._phase_done = set()
        self._phase_dots = {}
        self._phase_texts = {}
        self._phase_chips = {}
        self._phases_row = QHBoxLayout()
        self._phases_row.setContentsMargins(0, 0, 0, 0)
        self._phases_row.setSpacing(4)
        for key in self._phases_order:
            chip = QWidget(self)
            chip.setObjectName("loadPhaseChip")
            inner = QHBoxLayout(chip)
            inner.setContentsMargins(8, 3, 10, 3)
            inner.setSpacing(6)
            dot = QLabel(chip)
            dot.setFixedSize(8, 8)
            text = QLabel(self._phaseName(key), chip)
            text.setStyleSheet(
                "font-size: 11px; color: %s; background: transparent;"
                % self._muted)
            inner.addWidget(dot)
            inner.addWidget(text)
            chip.setStyleSheet(
                "QWidget#loadPhaseChip { background: transparent; border-radius: 999px; }")
            self._phase_chips[key] = chip
            self._phase_dots[key] = dot
            self._phase_texts[key] = text
            self._phases_row.addWidget(chip)
        row1.addLayout(self._phases_row)

        self.lbl_percent = QLabel("0%", self)
        self.lbl_percent.setStyleSheet(
            "font-family: 'JetBrains Mono', monospace; font-size: 13px;"
            " color: %s; background: transparent;" % self._text)
        row1.addStretch(1)
        row1.addWidget(self.lbl_percent)
        layout.addLayout(row1)

        # ---- row 2: segment bar (CSS .segbar: margin 9/7, height 6, gap 3)
        self._segments = []
        self._active_segment = -1
        self._segbar_widget = QWidget(self)
        self._segbar_widget.setObjectName("loadSegbar")
        self._segbar_layout = QHBoxLayout(self._segbar_widget)
        self._segbar_layout.setContentsMargins(0, 9, 0, 7)
        self._segbar_layout.setSpacing(3)
        self._segbar_widget.setStyleSheet("background: transparent;")
        layout.addWidget(self._segbar_widget)

        # plain shimmering bar fallback (CSS-less path for unknown totals)
        self.progressBar = QProgressBar(self)
        self.progressBar.setRange(0, 100)
        self.progressBar.setValue(0)
        self.progressBar.setTextVisible(False)
        self.progressBar.setFixedHeight(6)
        self.progressBar.setStyleSheet(
            "QProgressBar { background: transparent; border: none; }"
            "QProgressBar::chunk { background: %s; border-radius: 3px; }"
            % self._accent)
        self.progressBar.hide()
        layout.addWidget(self.progressBar)

        # ---- row 3: READ-ONLY chip | detail | eta (CSS .row2, gap 10)
        row2 = QHBoxLayout()
        row2.setContentsMargins(0, 0, 0, 0)
        row2.setSpacing(10)
        self.lbl_readonly = QLabel("READ-ONLY", self)
        self.lbl_readonly.setStyleSheet(
            "color: %s; font-size: 10px; font-weight: bold; letter-spacing: .6px;"
            " border: 1px solid %s; border-radius: 999px; padding: 1px 8px;"
            " background: transparent;"
            % (self._yellow(), self._yellow()))
        self.lbl_readonly.setToolTip(
            "Pan and zoom stay available, but nodes, plugins and cables cannot be "
            "edited until the project has finished loading.")
        row2.addWidget(self.lbl_readonly)

        self.lbl_detail = QLabel("Preparing project & engine...", self)
        self.lbl_detail.setStyleSheet(
            "color: %s; font-family: 'JetBrains Mono', monospace; font-size: 11.5px;"
            " background: transparent;" % self._text_dim())
        row2.addWidget(self.lbl_detail, 1)

        self.lbl_eta = QLabel("", self)
        self.lbl_eta.setStyleSheet(
            "color: %s; font-family: 'JetBrains Mono', monospace; font-size: 11px;"
            " background: transparent;" % self._muted)
        row2.addWidget(self.lbl_eta)
        layout.addLayout(row2)

        self._current = 8.0
        self._target = 20.0
        self._explicit = False
        self._timer = QTimer(self)
        self._timer.setInterval(40)
        self._timer.timeout.connect(self._tick)

        self._shimmer_phase = 0.0
        self._shimmer_timer = QTimer(self)
        self._shimmer_timer.setInterval(60)
        self._shimmer_timer.timeout.connect(self._shimmer_step)
        self._shimmer_timer.start()

        self._height_anim = None

    # ------------------------------------------------------------ colors

    def _yellow(self):
        return _themeColor("yellow", "#f9e2af")

    def _text_dim(self):
        return _themeColor("text-secondary", "#a6adc8")

    def _phaseName(self, key):
        return {"engine": "Engine", "plugins": "Plugins",
                "canvas": "Canvas", "session": "Session"}[key]

    # ------------------------------------------------------------ phases

    def _applyPhaseChip(self, key, state):
        """CSS parity: tick dot colors; text muted except the active phase;
        the active chip gets the accent-soft background."""
        chip = self._phase_chips[key]
        dot = self._phase_dots[key]
        text = self._phase_texts[key]
        if state == "active":
            chip.setStyleSheet(
                "QWidget#loadPhaseChip { background: %s; border-radius: 999px; }"
                % self._soft_accent)
            text.setStyleSheet(
                "font-size: 11px; color: %s; background: transparent;" % self._accent)
            dot.setStyleSheet(
                "background: %s; border-radius: 4px;" % self._accent)
        elif state == "done":
            chip.setStyleSheet(
                "QWidget#loadPhaseChip { background: transparent; border-radius: 999px; }")
            text.setStyleSheet(
                "font-size: 11px; color: %s; background: transparent;" % self._muted)
            dot.setStyleSheet(
                "background: %s; border-radius: 4px;" % self._green)
        else:
            chip.setStyleSheet(
                "QWidget#loadPhaseChip { background: transparent; border-radius: 999px; }")
            text.setStyleSheet(
                "font-size: 11px; color: %s; background: transparent;" % self._muted)
            dot.setStyleSheet(
                "background: %s; border-radius: 4px;" % self._border)

    def setPhase(self, name):
        """Highlight the active phase; earlier phases show a done tick."""
        if name not in self._phases_order:
            return
        self._current_phase = name
        cur = self._phases_order.index(name)
        for key in self._phases_order:
            k = self._phases_order.index(key)
            if k < cur or key in self._phase_done:
                self._applyPhaseChip(key, "done")
            elif k == cur:
                self._applyPhaseChip(key, "active")
            else:
                self._applyPhaseChip(key, "pending")

    def markPhaseDone(self, name):
        self._phase_done.add(name)
        self.setPhase(self._current_phase)

    # ------------------------------------------------------------ segments

    def setPipeline(self, total_plugins):
        """Build the segment bar: [engine] + plugins + [canvas] + [session]."""
        from qt_compat import QLabel
        total_plugins = max(0, int(total_plugins))
        count = total_plugins + 3

        for seg in self._segments:
            seg.setParent(None)
            seg.deleteLater()
        self._segments = []

        if total_plugins <= 0:
            self._segbar_widget.hide()
            self.progressBar.show()
            return
        self.progressBar.hide()
        self._segbar_widget.show()

        for i in range(count):
            seg = QLabel(self._segbar_widget)
            seg.setFixedHeight(6)
            seg.setStyleSheet(
                "background: %s; border: 1px solid %s; border-radius: 2px;"
                % (self._surface2, self._border))
            self._segbar_layout.addWidget(seg, 1)
            self._segments.append(seg)
        self.setSegment(0)

    def setSegment(self, index):
        """Mark the segment at `index` as in-progress (0-based over the pipeline)."""
        total = len(self._segments)
        if total == 0 or index < 0:
            return
        self._active_segment = index
        for i, seg in enumerate(self._segments):
            if i < index:
                seg.setStyleSheet(
                    "background: qlineargradient(x1:0, y1:0, x2:1, y2:0,"
                    " stop:0 %s, stop:1 %s); border-radius: 2px;"
                    % (self._accent, self._mauve))
            elif i == index:
                seg.setStyleSheet(
                    "background: %s; border: 1px solid %s; border-radius: 2px;"
                    % (self._soft_accent, self._accent))
            else:
                seg.setStyleSheet(
                    "background: %s; border: 1px solid %s; border-radius: 2px;"
                    % (self._surface2, self._border))
        if index <= 0:
            self.setPhase("engine")
        elif total > 2 and index >= total - 2:
            self.setPhase("canvas" if index == total - 2 else "session")
        elif total > 2:
            self.setPhase("plugins")
        self.lbl_percent.setText(
            "%d<small style=\"color: %s; font-size: 10px\">%%</small>"
            % (round(index / total * 100), self._muted))

    def _shimmer_step(self):
        """CSS parity: a light sweep band travels across the active segment."""
        self._shimmer_phase = (self._shimmer_phase + 0.07) % 1.3
        index = self._active_segment
        if index < 0 or index >= len(self._segments):
            if not self._segments:
                self._apply_shimmer()
            return
        seg = self._segments[index]
        phase = self._shimmer_phase
        a = max(0.0, phase - 0.25)
        b = min(1.0, phase + 0.25)
        seg.setStyleSheet(
            "background: qlineargradient(x1:0, y1:0, x2:1, y2:0,"
            " stop:0 %s, stop:%.2f %s, stop:%.2f %s, stop:1 %s);"
            " border: 1px solid %s; border-radius: 2px;"
            % (self._accent, a, self._text, b, self._accent, self._accent, self._accent))

    def _apply_shimmer(self):
        """Plain-bar fallback shimmer (unknown totals)."""
        phase = self._shimmer_phase
        a = max(0.0, phase - 0.35)
        b = min(1.0, phase + 0.35)
        self.progressBar.setStyleSheet(
            "QProgressBar { background: transparent; border: none; }"
            "QProgressBar::chunk { border-radius: 3px; background: qlineargradient("
            "x1:0, y1:0, x2:1, y2:0, stop:0 %s, stop:%.2f %s, stop:%.2f %s, stop:1 %s); }"
            % (self._border, a, self._accent, b, self._accent, self._border))

    # ------------------------------------------------------------ existing API

    def _tick(self):
        if self._current < self._target:
            self._current = min(self._target, self._current + max(0.5, (self._target - self._current) * 0.28))
        elif not self._explicit and self._current < 93.0:
            self._current += 0.12
        self.lbl_percent.setText(
            "%d<small style=\"color: %s; font-size: 10px\">%%</small>"
            % (int(self._current), self._muted))
        if self._segments:
            self.progressBar.setValue(int(self._current))

    def setDetail(self, text):
        if text:
            self.lbl_detail.setText(str(text))

    def setDone(self):
        """Loaded: the whole strip collapses to one solid highlight pill."""
        try:
            if self._shimmer_timer is not None:
                self._shimmer_timer.stop()
        except Exception:
            pass
        if self._segbar_widget is not None:
            self._segbar_widget.hide()
        self.progressBar.hide()
        pill = getattr(self, "_done_pill", None)
        if pill is None:
            from qt_compat import QLabel
            pill = QLabel(self)
            pill.setFixedHeight(6)
            self._done_pill = pill
            self.layout().insertWidget(1, pill)
        pill.setStyleSheet(
            "background: %s; border-radius: 3px;" % _themeColor("purple", "#cba6f7"))
        pill.show()
        self.lbl_percent.setText("100%")
        self.lbl_detail.setText("Ready!")
        for key in self._phases_order:
            self._applyPhaseChip(key, "done")
        self.lbl_eta.setText("")

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
        self.lbl_percent.setText(
            "%d<small style=\"color: %s; font-size: 10px\">%%</small>"
            % (int(min(self._target, self._current)), self._muted))
        if detail:
            self.lbl_detail.setText(str(detail))

    # ------------------------------------------------------------ smooth height

    def _animateHeight(self, from_h, to_h, on_done=None):
        """CSS-like smooth height change on show/hide (QVariantAnimation)."""
        from qt_compat import QVariantAnimation, QEasingCurve
        if self._height_anim is not None:
            self._height_anim.stop()
            self._height_anim = None

        def _step(v):
            self.setFixedHeight(max(0, int(v)))

        def _done():
            self._height_anim = None
            if to_h > 0:
                # release the fixed height so docking can manage geometry
                self.setFixedSize(16777215, 16777215)
                self.setMinimumHeight(0)
                self.setMaximumHeight(16777215)
            if on_done is not None:
                on_done()

        anim = QVariantAnimation(self)
        anim.setDuration(220)
        anim.setEasingCurve(QEasingCurve.Type.OutQuad if hasattr(QEasingCurve, "Type") else QEasingCurve.OutQuad)
        anim.setStartValue(float(from_h))
        anim.setEndValue(float(to_h))
        anim.valueChanged.connect(_step)
        anim.finished.connect(_done)
        self._height_anim = anim
        anim.start()

    def showEvent(self, event):
        QWidget_showEvent = getattr(type(self).__mro__[1], "showEvent", None)
        if QWidget_showEvent is not None:
            QWidget_showEvent(self, event)
        target = max(self.sizeHint().height(), 34)
        self._animateHeight(0, target)

    def dismiss(self, min_dwell_ms=0):
        try:
            self._timer.stop()
            self._shimmer_timer.stop()
        except Exception:
            pass
        self.lbl_percent.setText("100%")
        self.lbl_detail.setText("Ready!")
        self._animateHeight(self.height(), 0, on_done=lambda: (
            self.hide(), self.setParent(None), self.deleteLater()))


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
