#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2011-2025 Filipe Coelho <falktx@falktx.com>
# SPDX-License-Identifier: GPL-2.0-or-later

# ------------------------------------------------------------------------------------------------------------
# Signal / event flow animation support for the patchbay canvas.
#
# A single lightweight animator owns the global animation phase and a map of
# per-node activity levels (0.0 - 1.0), keyed by canvas group id. The frontend
# feeds it real levels (engine peaks for plugins, sampled peaks for external
# PipeWire nodes); cable items and node boxes read the shared state from
# canvasline.py / canvasbox.py during paint().
# ------------------------------------------------------------------------------------------------------------

from qt_compat import QObject, QTimer


class _SignalFlowState(object):
    __slots__ = ("enabled", "phase", "levels", "flow")

    def __init__(self):
        self.enabled = False
        self.phase = 0.0
        self.levels = {}  # plugin_id -> smoothed activity 0.0 - 1.0 (node glow)
        self.flow = {}    # plugin_id -> source-side output level (cable pulses)


state = _SignalFlowState()


class SignalFlowAnimator(QObject):
    """Drives the animation clock and smooths per-plugin activity levels."""

    INTERVAL_MS = 16          # ~60 FPS, butter-smooth with OpenGL
    PHASE_STEP = 0.018        # one full pulse cycle per ~0.9 s
    ATTACK = 0.4              # smoothing toward a rising level
    DECAY = 0.82              # falloff when a plugin goes silent

    def __init__(self, parent=None):
        super().__init__(parent)
        self._timer = QTimer(self)
        self._timer.setInterval(self.INTERVAL_MS)
        self._timer.timeout.connect(self._tick)
        self._provider = None       # callable() -> {plugin_id: level}
        self._frame_callbacks = []
        self._active_ids = set()

    def set_level_provider(self, provider):
        self._provider = provider

    def add_frame_callback(self, callback):
        self._frame_callbacks.append(callback)

    def is_enabled(self):
        return state.enabled

    def active_ids(self):
        return self._active_ids

    def start(self):
        state.enabled = True
        if not self._timer.isActive():
            self._timer.start()

    def stop(self):
        state.enabled = False
        self._timer.stop()
        state.levels = {}
        state.flow = {}
        self._active_ids = set()
        self._emit_frame()

    def _tick(self):
        state.phase = (state.phase + self.PHASE_STEP) % 1.0

        raw = {}
        if self._provider is not None:
            try:
                raw = self._provider() or {}
            except Exception:
                raw = {}

        levels = state.levels
        for pid, value in raw.items():
            try:
                target = min(1.0, max(0.0, float(value)))
            except (TypeError, ValueError):
                continue
            current = levels.get(pid, 0.0)
            levels[pid] = current + (target - current) * self.ATTACK

        for pid in list(levels):
            if pid in raw:
                continue
            value = levels[pid] * self.DECAY
            if value < 0.01:
                del levels[pid]
            else:
                levels[pid] = value

        self._active_ids = {pid for pid, value in levels.items() if value > 0.03}
        self._emit_frame()

    def _emit_frame(self):
        for callback in self._frame_callbacks:
            try:
                callback()
            except Exception:
                pass


_animator = None


def get_animator():
    global _animator
    if _animator is None:
        _animator = SignalFlowAnimator()
    return _animator
