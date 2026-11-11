#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2011-2025 Filipe Coelho <falktx@falktx.com>
# SPDX-License-Identifier: GPL-2.0-or-later

# ------------------------------------------------------------------------------------------------------------
# Imports (Global)
# ------------------------------------------------------------------------------------------------------------
import os
import re

# ------------------------------------------------------------------------------------------------------------
# Imports (Custom)
# ------------------------------------------------------------------------------------------------------------

from carla_backend import *
from carla_shared import *
from carla_widgets import *
from patchcanvas import patchcanvas

# ------------------------------------------------------------------------------------------------------------
# Imports (PyQt)
# ------------------------------------------------------------------------------------------------------------
from canvas_helpers import _canvas_locked, _get_event_global_pos, get_glyph_visual_offset
from qt_compat import (
    QAction,
    QApplication,
    QColor,
    QColorDialog,
    QCursor,
    QEvent,
    QFont,
    QFontDatabase,
    QFrame,
    QHBoxLayout,
    QIcon,
    QImage,
    QLabel,
    QLineEdit,
    QMenu,
    QMouseEvent,
    QObject,
    QPainter,
    QPainterPathStroker,
    QPixmap,
    QPoint,
    QPointF,
    QPushButton,
    QRect,
    QStyle,
    QStyleOptionButton,
    Qt,
    QTimer,
    QVBoxLayout,
    QWidget,
)

# ------------------------------------------------------------------------------------------------------------
# Stereo Autowiring and Disconnect Helpers
# ------------------------------------------------------------------------------------------------------------


class CanvasToolButton(QPushButton):
    """Button that visually centers asymmetrical font and unicode glyph icons."""

    def __init__(self, glyph="", parent=None):
        super().__init__(glyph, parent)
        self._glyph = glyph
        self._cached_offset = None

    def setText(self, text):
        super().setText(text)
        self._glyph = text
        self._cached_offset = None
        self.update()

    def setGlyph(self, glyph):
        self.setText(glyph)

    def paintEvent(self, event):
        if not self._glyph:
            super().paintEvent(event)
            return

        p = QPainter(self)
        opt = QStyleOptionButton()
        self.initStyleOption(opt)

        ce_bevel = getattr(QStyle, "CE_PushButtonBevel", None) or getattr(
            getattr(QStyle, "ControlElement", object), "CE_PushButtonBevel", None
        )
        ce_label = getattr(QStyle, "CE_PushButtonLabel", None) or getattr(
            getattr(QStyle, "ControlElement", object), "CE_PushButtonLabel", None
        )

        if ce_bevel is not None and ce_label is not None:
            self.style().drawControl(ce_bevel, opt, p, self)

            if self._cached_offset is None:
                size = max(self.width(), self.height())
                self._cached_offset = get_glyph_visual_offset(
                    self._glyph, self.font(), size
                )

            dx, dy = self._cached_offset
            if dx != 0 or dy != 0:
                opt.rect = opt.rect.translated(dx, dy)
            self.style().drawControl(ce_label, opt, p, self)
        else:
            super().paintEvent(event)


class CanvasToolBarOverlay(QFrame):
    """Floating Photoshop-style vertical navigation/tool palette on the left of the patchbay canvas."""

    def __init__(self, graphicsView, parent=None):
        super().__init__(parent or graphicsView.viewport())
        self.setObjectName("canvas_toolbar_overlay")
        self.graphicsView = graphicsView
        self._dragPos = None
        self._userMoved = False

        layout = QVBoxLayout(self)
        layout.setContentsMargins(3, 4, 3, 4)
        layout.setSpacing(2)

        font_family = getBestNerdFont()
        font = QFont(font_family, 13) if font_family else QFont()
        if not font_family:
            font.setPointSize(11)

        # Icons: Lucide (vendored); bind_icon attaches palette-driven QIcons.
        self.icon_pointer = "mouse-pointer"
        self.icon_select = "box-select"
        self.icon_hand = "hand"
        self.icon_zoomin = "zoom-in"
        self.icon_zoomout = "zoom-out"
        self.icon_fit = "maximize-2"
        self.icon_grid = "grid-3x3"
        self.icon_snap = "magnet"
        self.icon_flow = "activity"
        self.icon_help = "circle-help"
        # Main Application Menu Button (Accessible when Menubar is hidden)
        self.btnMenu = CanvasToolButton("", self)
        self.btnMenu.setObjectName("canvasMenuButton")
        self.btnMenu.setToolTip("Main Menu (Ctrl+M to toggle menubar)")
        self.btnMenu.setFont(font)
        self.btnMenu.setFixedSize(28, 28)
        self.btnMenu.clicked.connect(self._slot_openMainMenu)
        layout.addWidget(self.btnMenu)

        # Mode Selection Buttons (Checkable, Mutually Exclusive)
        self.btnPointer = CanvasToolButton("", self)
        self.btnPointer.setToolTip("Pointer Tool (Q / Esc)")
        self.btnPointer.setFont(font)

        self.btnSelect = CanvasToolButton("", self)
        self.btnSelect.setToolTip("Marquee Selection (V)")
        self.btnSelect.setFont(font)

        self.btnHand = CanvasToolButton("", self)
        self.btnHand.setToolTip("Hand / Pan Canvas (H / Space)")
        self.btnHand.setFont(font)

        for btn in (self.btnPointer, self.btnSelect, self.btnHand):
            btn.setFixedSize(28, 28)
            btn.setCheckable(True)
            layout.addWidget(btn)

        self.btnPointer.clicked.connect(lambda: self._setMode(0))
        self.btnSelect.clicked.connect(lambda: self._setMode(1))
        self.btnHand.clicked.connect(lambda: self._setMode(2))

        def add_sep():
            line = QFrame(self)
            line.setObjectName("canvasToolbarSeparator")
            line.setFrameShape(QFrame.HLine)
            line.setFrameShadow(QFrame.Sunken)
            line.setFixedHeight(1)
            layout.addWidget(line)

        add_sep()

        # Zoom & View Tools
        self.btnZoomIn = CanvasToolButton("", self)
        self.btnZoomIn.setToolTip("Zoom In (+)")
        self.btnZoomIn.setFont(font)
        self.btnZoomIn.setFixedSize(28, 28)
        self.btnZoomIn.clicked.connect(lambda: self._zoom(120))
        layout.addWidget(self.btnZoomIn)

        self.btnZoomOut = CanvasToolButton("", self)
        self.btnZoomOut.setToolTip("Zoom Out (-)")
        self.btnZoomOut.setFont(font)
        self.btnZoomOut.setFixedSize(28, 28)
        self.btnZoomOut.clicked.connect(lambda: self._zoom(-120))
        layout.addWidget(self.btnZoomOut)

        self.btnFit = CanvasToolButton("", self)
        self.btnFit.setToolTip("Zoom to Fit All Nodes (F)")
        self.btnFit.setFont(font)
        self.btnFit.setFixedSize(28, 28)
        self.btnFit.clicked.connect(self._slot_zoomFit)
        layout.addWidget(self.btnFit)

        add_sep()

        # Canvas Dot Grid Toggle
        self.btnGrid = CanvasToolButton("", self)
        self.btnGrid.setToolTip("Toggle Dot Grid Visibility")
        self.btnGrid.setFont(font)
        self.btnGrid.setFixedSize(28, 28)
        self.btnGrid.setCheckable(True)
        self.btnGrid.setChecked(getattr(patchcanvas.options, "grid_enabled", True))
        self.btnGrid.clicked.connect(self._slot_toggleGrid)
        layout.addWidget(self.btnGrid)

        # Coordinate Snapping Toggle
        self.btnSnap = CanvasToolButton("", self)
        self.btnSnap.setToolTip("Toggle Coordinate Snapping to Grid")
        self.btnSnap.setFont(font)
        self.btnSnap.setFixedSize(28, 28)
        self.btnSnap.setCheckable(True)
        self.btnSnap.setChecked(getattr(patchcanvas.options, "snap_enabled", True))
        self.btnSnap.clicked.connect(self._slot_toggleSnap)
        layout.addWidget(self.btnSnap)

        add_sep()

        # Signal / Event Flow Animation Toggle
        self._signalflow_external = True
        self.btnSignalFlow = CanvasToolButton("", self)
        self.btnSignalFlow.setToolTip(
            "Toggle animated signal/event flow over the patchbay\n(right-click for options)"
        )
        self.btnSignalFlow.setFont(font)
        self.btnSignalFlow.setFixedSize(28, 28)
        self.btnSignalFlow.setCheckable(True)
        self.btnSignalFlow.clicked.connect(self._slot_toggleSignalFlow)
        self.btnSignalFlow.setContextMenuPolicy(Qt.CustomContextMenu)
        self.btnSignalFlow.customContextMenuRequested.connect(self._slot_flowMenu)
        layout.addWidget(self.btnSignalFlow)

        add_sep()

        # Patchbay Shortcuts Help Tooltip
        self.btnHelp = CanvasToolButton("", self)
        self.btnHelp.setFont(font)
        self.btnHelp.setFixedSize(28, 28)
        self.btnHelp.setToolTip("""<b>Patchbay Shortcuts:</b><br/>
• <b>Space + Drag</b>: Pan Canvas<br/>
• <b>Wheel</b>: Zoom in/out<br/>
• <b>F</b>: Zoom to Fit All<br/>
• <b>Alt + Drag Wire</b>: Stereo Autowire (L+R)<br/>
• <b>Alt / Shift + Click</b>: Quick Disconnect<br/>
• <b>Middle-Click</b>: Disconnect Wire/Port<br/>
• <b>Right-Click Node</b>: Node Actions & Align""")
        layout.addWidget(self.btnHelp)

        # Attach Lucide icons to every toolbar button; checked tiles fill
        # with the highlight, so icons invert to the theme's background color.
        from widgets.lucide import bind_icon, contrast_on_highlight
        checked_ink = contrast_on_highlight()
        for btn, name in (
            (self.btnMenu, "menu"),
            (self.btnPointer, self.icon_pointer),
            (self.btnSelect, self.icon_select),
            (self.btnHand, self.icon_hand),
            (self.btnZoomIn, self.icon_zoomin),
            (self.btnZoomOut, self.icon_zoomout),
            (self.btnFit, self.icon_fit),
            (self.btnGrid, self.icon_grid),
            (self.btnSnap, self.icon_snap),
            (self.btnSignalFlow, self.icon_flow),
            (self.btnHelp, self.icon_help),
        ):
            bind_icon(btn, name, size=16, checked_color=checked_ink)

        self.updateActiveButton(0)
        self.adjustSize()

        try:
            from utils import QSafeSettings
            from carla_shared import (
                CARLA_KEY_CANVAS_SIGNAL_FLOW,
                CARLA_KEY_CANVAS_SIGNAL_FLOW_EXT,
            )

            settings = QSafeSettings("falkTX", "Carla2")
            self._signalflow_external = settings.value(
                CARLA_KEY_CANVAS_SIGNAL_FLOW_EXT, True, bool
            )
            if settings.value(CARLA_KEY_CANVAS_SIGNAL_FLOW, False, bool):
                self._applySignalFlow(True)
        except Exception:
            pass

    def _slot_openMainMenu(self):
        gui = getattr(gCarla, "gui", None)
        if gui is not None and hasattr(gui, "ui"):
            menu = QMenu(self)
            menu.addAction(gui.ui.menu_File.menuAction())
            menu.addAction(gui.ui.menu_Engine.menuAction())
            menu.addAction(gui.ui.menu_Plugin.menuAction())
            menu.addAction(gui.ui.menu_Canvas.menuAction())
            menu.addAction(gui.ui.menu_Settings.menuAction())
            menu.addAction(gui.ui.menu_Help.menuAction())
            menu.exec_(self.btnMenu.mapToGlobal(QPoint(self.btnMenu.width(), 0)))

    def _setMode(self, mode):
        if hasattr(self.graphicsView, "setToolMode"):
            self.graphicsView.setToolMode(mode)
        self.updateActiveButton(mode)

    def _zoom(self, delta):
        scene = self.graphicsView.scene()
        if scene and hasattr(scene, "zoom_wheel"):
            scene.zoom_wheel(delta)

    def _slot_zoomFit(self):
        scene = self.graphicsView.scene()
        if scene and hasattr(scene, "zoom_fit"):
            scene.zoom_fit()

    def _slot_toggleGrid(self):
        new_state = not getattr(patchcanvas.options, "grid_enabled", True)
        patchcanvas.options.grid_enabled = new_state
        self.btnGrid.setChecked(new_state)
        scene = self.graphicsView.scene()
        if scene:
            scene.update()

    def _slot_toggleSnap(self):
        new_state = not getattr(patchcanvas.options, "snap_enabled", True)
        patchcanvas.options.snap_enabled = new_state
        self.btnSnap.setChecked(new_state)

    def _slot_toggleSignalFlow(self):
        from patchcanvas import signalflow

        animator = signalflow.get_animator()
        new_state = not animator.is_enabled()
        self._applySignalFlow(new_state)
        try:
            from utils import QSafeSettings
            from carla_shared import CARLA_KEY_CANVAS_SIGNAL_FLOW

            QSafeSettings("falkTX", "Carla2").setValue(
                CARLA_KEY_CANVAS_SIGNAL_FLOW, new_state
            )
        except Exception:
            pass

    def _slot_flowMenu(self, pos):
        menu = QMenu(self)
        act_ext = QAction("Include external / PipeWire nodes", menu)
        act_ext.setCheckable(True)
        act_ext.setChecked(bool(self._signalflow_external))
        act_ext.setToolTip(
            "Sample real levels of external nodes (bus, monitors, hardware) via a hidden peak-detect tap"
        )
        menu.addAction(act_ext)
        chosen = menu.exec_(self.btnSignalFlow.mapToGlobal(pos))
        if chosen is act_ext:
            self._signalflow_external = act_ext.isChecked()
            try:
                from utils import QSafeSettings
                from carla_shared import CARLA_KEY_CANVAS_SIGNAL_FLOW_EXT

                QSafeSettings("falkTX", "Carla2").setValue(
                    CARLA_KEY_CANVAS_SIGNAL_FLOW_EXT, self._signalflow_external
                )
            except Exception:
                pass
            if not self._signalflow_external:
                self._stopExternalSampler()
            elif self._signalflow_ready:
                from patchcanvas import signalflow

                if signalflow.get_animator().is_enabled():
                    self._external_sampler()

    def _stopExternalSampler(self):
        for module_name in ("pwlevels", "pwrecord"):
            try:
                module = __import__("patchcanvas." + module_name, fromlist=[module_name])
                module.get_sampler().set_nodes(set())
                module.get_sampler().stop()
            except Exception:
                pass

    def _external_sampler(self):
        if not self._signalflow_external:
            return None
        try:
            from patchcanvas import pwlevels

            sampler = pwlevels.get_sampler()
            if not sampler.is_available():
                return None
            if not sampler.is_running() and not sampler.start():
                return None
            return sampler
        except Exception:
            return None

    def _pwrecord_sampler(self):
        if not self._signalflow_external:
            return None
        try:
            from patchcanvas import pwrecord

            sampler = pwrecord.get_sampler()
            if not sampler.is_available():
                return None
            return sampler
        except Exception:
            return None

    def _applySignalFlow(self, enabled):
        from patchcanvas import signalflow

        animator = signalflow.get_animator()
        if not getattr(self, "_signalflow_ready", False):
            self._signalflow_ready = True
            animator.set_level_provider(self._provideSignalLevels)
            animator.add_frame_callback(self._repaintActiveSignalItems)
        if enabled:
            animator.start()
            self._external_sampler()
        else:
            animator.stop()
            self._stopExternalSampler()
        self.btnSignalFlow.setChecked(bool(enabled))

    def _provideSignalLevels(self):
        import time

        now = time.monotonic()
        cached = getattr(self, "_signal_levels_cache", None)
        if cached is not None and now - cached[0] < 0.1:
            return cached[1]

        from patchcanvas import signalflow

        # While a project is being built the canvas is churning anyway: no pulses, no repaint cost.
        gui = getattr(gCarla, "gui", None)
        if gui is not None and getattr(gui, "fIsProjectLoading", False):
            signalflow.state.flow = {}
            self._signal_levels_cache = (now, {})
            return {}

        # Nobody sees the canvas while the window is minimized or another tab is shown:
        # skip the engine peak polling and the PulseAudio pump entirely.
        view = getattr(self, "graphicsView", None)
        if view is None or not view.isVisible() or view.window().isMinimized():
            signalflow.state.flow = {}
            self._signal_levels_cache = (now, {})
            return {}

        levels, flow = self._collectSignalLevels()

        # Peak-hold smoothing for cables, so a brief dip does not make the pulse flicker.
        previous = getattr(self, "_signal_flow_smoothed", {})
        smoothed = {}
        for gid, value in flow.items():
            old = previous.get(gid, 0.0)
            smoothed[gid] = old + (value - old) * 0.4
        for gid, old in previous.items():
            if gid not in smoothed:
                value = old * 0.82
                if value >= 0.01:
                    smoothed[gid] = value
        self._signal_flow_smoothed = smoothed
        signalflow.state.flow = smoothed

        self._signal_levels_cache = (now, levels)
        return levels

    def _collectSignalLevels(self):
        import time

        # Returns (activity, flow): activity is the node glow (max of input and output),
        # flow is the source-side output only and drives the cable pulses. Carla exposes
        # peak values for real plugins; external / hardware / PipeWire groups have no
        # engine peak, so their flow comes from a hidden peak-detect tap when available.
        gui = getattr(gCarla, "gui", None)
        engine = getattr(gui, "host", None) if gui is not None else None

        groups = list(patchcanvas.canvas.group_list)
        plugin_levels = {}
        plugin_flow = {}
        external_groups = []  # (group_id, pw_node_name)

        # Split clients live in visual sub-groups with negative ids; cables attach to
        # those, so a level keyed by the client id must also be copied to each sub-group.
        visual_map = getattr(patchcanvas.canvas, "pipewire_group_ids", {}) or {}

        def _put(mapping, gid, value):
            if value <= 0.0:
                return
            if value > mapping.get(gid, 0.0):
                mapping[gid] = value
            for visual_id in visual_map.get(gid, ()):
                if value > mapping.get(visual_id, 0.0):
                    mapping[visual_id] = value

        if engine is not None:
            for group in groups:
                gid = getattr(group, "group_id", None)
                if gid is None:
                    continue
                pid = getattr(group, "plugin_id", -1)
                if not (0 <= pid <= patchcanvas.MAX_PLUGIN_ID_ALLOWED):
                    name = getattr(group, "pw_node_name", None) or getattr(
                        group, "group_name", None
                    )
                    external_groups.append((gid, name))
                    continue
                try:
                    in_level = max(
                        engine.get_input_peak_value(pid, True),
                        engine.get_input_peak_value(pid, False),
                    )
                    out_level = max(
                        engine.get_output_peak_value(pid, True),
                        engine.get_output_peak_value(pid, False),
                    )
                except Exception:
                    continue
                _put(plugin_levels, gid, max(in_level, out_level))
                _put(plugin_flow, gid, out_level)
        else:
            for group in groups:
                gid = getattr(group, "group_id", None)
                if gid is None:
                    continue
                if getattr(group, "plugin_id", -1) not in range(
                    0, patchcanvas.MAX_PLUGIN_ID_ALLOWED + 1
                ):
                    name = getattr(group, "pw_node_name", None) or getattr(
                        group, "group_name", None
                    )
                    external_groups.append((gid, name))

        levels = dict(plugin_levels)
        flow = dict(plugin_flow)

        connections = list(patchcanvas.canvas.connection_list)
        connected_ids = set()
        for conn in connections:
            connected_ids.add(getattr(conn, "group_out_id", None))
            connected_ids.add(getattr(conn, "group_in_id", None))

        # Real per-node levels for external groups via a hidden peak-detect tap
        sampler = self._external_sampler()
        if sampler is not None and external_groups:
            desired = [
                name for gid, name in external_groups if gid in connected_ids and name
            ]
            sampler.set_nodes(desired)
            sampler.process()
            for gid, name in external_groups:
                if gid in connected_ids and name:
                    lvl = sampler.level_for(name)
                    _put(levels, gid, lvl)
                    _put(flow, gid, lvl)

        # Playback streams (Spotify, browsers, Electron apps) have no PulseAudio
        # source, so capture the node itself with pw-record.
        pw_sampler = self._pwrecord_sampler()
        if pw_sampler is not None and external_groups:
            if getattr(gui, "fIsProjectLoading", False):
                # Never spawn capture clients while a project is being built
                pw_sampler.set_nodes([])
            else:
                uncovered = []
                for gid, name in external_groups:
                    if gid not in connected_ids or not name:
                        continue
                    if name.lower().startswith("pw-record"):
                        continue
                    if sampler is not None and sampler.has_target(name):
                        continue
                    uncovered.append(name)
                    if len(uncovered) >= 8:
                        break
                pw_sampler.set_nodes(uncovered)
                pw_sampler.process()
            for gid, name in external_groups:
                if gid in connected_ids and name:
                    lvl = pw_sampler.level_for(name)
                    _put(levels, gid, lvl)
                    _put(flow, gid, lvl)

        # Remaining external / hardware groups borrow activity for the node glow only;
        # cable flow is never faked from the far end.
        non_plugin_ids = {gid for gid, _name in external_groups}
        if non_plugin_ids:
            for _ in range(2):
                for conn in connections:
                    out_id = getattr(conn, "group_out_id", None)
                    in_id = getattr(conn, "group_in_id", None)
                    src = levels.get(out_id, 0.0)
                    dst = levels.get(in_id, 0.0)
                    best = max(src, dst)
                    if best <= 0.0:
                        continue
                    if out_id in non_plugin_ids:
                        _put(levels, out_id, best * 0.85)
                    if in_id in non_plugin_ids:
                        _put(levels, in_id, best * 0.85)

        now = time.monotonic()
        if now - getattr(self, "_flow_debug_at", 0.0) > 5.0:
            self._flow_debug_at = now
            if os.environ.get("CLARA_DEBUG_SIGNALFLOW"):
                names = {g.group_id: g.group_name for g in groups}
                conns = [(c.group_out_id, c.group_in_id) for c in patchcanvas.canvas.connection_list][:30]
                log_carla(
                    "SIGNALFLOW flow=%s conns=%s" % (
                        {names.get(k, k): round(v, 3) for k, v in flow.items()},
                        [(names.get(o, o), names.get(i, i)) for o, i in conns],
                    ),
                    level="debug",
                )

        return levels, flow

    def _repaintActiveSignalItems(self):
        from patchcanvas import signalflow

        levels = signalflow.state.levels
        flow = signalflow.state.flow
        if not levels and not flow:
            return
        canvas = patchcanvas.canvas
        for conn in list(canvas.connection_list):
            if flow.get(getattr(conn, "group_out_id", None), 0.0) > 0.05:
                widget = getattr(conn, "widget", None)
                if widget is not None:
                    widget.update()
        for group in list(canvas.group_list):
            if levels.get(getattr(group, "group_id", None), 0.0) > 0.05:
                for w in group.widgets:
                    if w is not None:
                        w.update()

    def updateActiveButton(self, mode):
        self.btnPointer.setChecked(mode == 0)
        self.btnSelect.setChecked(mode == 1)
        self.btnHand.setChecked(mode == 2)

    def mousePressEvent(self, event):
        if _canvas_locked():
            event.accept()
            return
        if event.button() == Qt.LeftButton:
            self._dragPos = (
                _get_event_global_pos(event) - self.frameGeometry().topLeft()
            )
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if _canvas_locked():
            event.accept()
            return
        if self._dragPos is not None and event.buttons() & Qt.LeftButton:
            vp = self.parentWidget()
            if vp:
                new_pos = _get_event_global_pos(event) - self._dragPos
                x = max(0, min(new_pos.x(), vp.width() - self.width()))
                y = max(0, min(new_pos.y(), vp.height() - self.height()))
                self.move(x, y)
                self._userMoved = True
                event.accept()
                return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        self._dragPos = None
        super().mouseReleaseEvent(event)

    def reposition(self):
        if getattr(self, "_userMoved", False):
            return
        parent = self.parentWidget()
        if parent is None:
            return
        # Left palette: pinned to the patchbay's left edge, vertically centered.
        x = 12
        y = max(12, (parent.height() - self.height()) // 2)
        self.move(x, y)
        self.raise_()


# ------------------------------------------------------------------------------------------------------------
# Floating Context Actions Toolbar (Top Centered Palette)
# ------------------------------------------------------------------------------------------------------------
