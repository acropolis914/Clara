#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2011-2025 Filipe Coelho <falktx@falktx.com>
# SPDX-License-Identifier: GPL-2.0-or-later

# ------------------------------------------------------------------------------------------------------------
# Imports (Global)
# ------------------------------------------------------------------------------------------------------------
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


def findStereoPartner(target_port, candidate_ports):
    target_name = target_port.port_name

    # 1. Single character difference at same index where one is L/l and other is R/r
    for cand in candidate_ports:
        if cand.port_id == target_port.port_id:
            continue
        c_name = cand.port_name
        if len(c_name) == len(target_name):
            diffs = [
                (i, target_name[i], c_name[i])
                for i in range(len(target_name))
                if target_name[i] != c_name[i]
            ]
            if len(diffs) == 1:
                c1, c2 = diffs[0][1].upper(), diffs[0][2].upper()
                if (c1, c2) in [("L", "R"), ("R", "L")]:
                    return cand

    # 2. Single character difference at same index where one is 1 and other is 2
    for cand in candidate_ports:
        if cand.port_id == target_port.port_id:
            continue
        c_name = cand.port_name
        if len(c_name) == len(target_name):
            diffs = [
                (i, target_name[i], c_name[i])
                for i in range(len(target_name))
                if target_name[i] != c_name[i]
            ]
            if len(diffs) == 1:
                c1, c2 = diffs[0][1], diffs[0][2]
                if (c1, c2) in [("1", "2"), ("2", "1")]:
                    return cand

    # 3. Substring 'left' vs 'right' (case-insensitive)
    for cand in candidate_ports:
        if cand.port_id == target_port.port_id:
            continue
        c_name = cand.port_name
        if (
            re.sub(r"(?i)\bleft\b", "right", target_name.lower()) == c_name.lower()
            or re.sub(r"(?i)\bright\b", "left", target_name.lower()) == c_name.lower()
        ):
            return cand

    return None


def autoConnectStereoPair(gOut, pOut, gIn, pIn):
    try:
        port_list = patchcanvas.canvas.port_list
        src_port = None
        dst_port = None
        for p in port_list:
            if p.group_id == gOut and p.port_id == pOut:
                src_port = p
            elif p.group_id == gIn and p.port_id == pIn:
                dst_port = p

        if src_port and dst_port and src_port.port_type == dst_port.port_type:
            src_cands = [
                p
                for p in port_list
                if p.group_id == gOut
                and p.port_mode == src_port.port_mode
                and p.port_type == src_port.port_type
            ]
            dst_cands = [
                p
                for p in port_list
                if p.group_id == gIn
                and p.port_mode == dst_port.port_mode
                and p.port_type == dst_port.port_type
            ]

            src_partner = findStereoPartner(src_port, src_cands)
            dst_partner = findStereoPartner(dst_port, dst_cands)

            if src_partner and dst_partner:
                log_carla(
                    f"carla_canvas: Stereo auto-wire (Alt): {gOut}:{src_partner.port_id} ('{src_partner.port_name}') -> {gIn}:{dst_partner.port_id} ('{dst_partner.port_name}')"
                )
                gCarla.gui.host.patchbay_connect(
                    gCarla.gui.fExternalPatchbay,
                    gOut,
                    src_partner.port_id,
                    gIn,
                    dst_partner.port_id,
                )
    except Exception as e:
        log_carla(f"carla_canvas: Stereo auto-wire error: {e}")


def findStereoPartnerConnection(connectionId):
    try:
        conn_info = gCarla.gui.fConnections.get(connectionId)
        if not conn_info:
            return None
        gOut, pOut, gIn, pIn = conn_info
        port_list = patchcanvas.canvas.port_list
        src_port = None
        dst_port = None
        for p in port_list:
            if p.group_id == gOut and p.port_id == pOut:
                src_port = p
            elif p.group_id == gIn and p.port_id == pIn:
                dst_port = p

        if src_port and dst_port and src_port.port_type == dst_port.port_type:
            src_cands = [
                p
                for p in port_list
                if p.group_id == gOut
                and p.port_mode == src_port.port_mode
                and p.port_type == src_port.port_type
            ]
            dst_cands = [
                p
                for p in port_list
                if p.group_id == gIn
                and p.port_mode == dst_port.port_mode
                and p.port_type == dst_port.port_type
            ]

            src_partner = findStereoPartner(src_port, src_cands)
            dst_partner = findStereoPartner(dst_port, dst_cands)

            if src_partner and dst_partner:
                for cid, (cgOut, cpOut, cgIn, cpIn) in gCarla.gui.fConnections.items():
                    if (
                        cid != connectionId
                        and cgOut == gOut
                        and cpOut == src_partner.port_id
                        and cgIn == gIn
                        and cpIn == dst_partner.port_id
                    ):
                        return cid
    except Exception as e:
        log_carla(f"carla_canvas: findStereoPartnerConnection error: {e}")
    return None


# ------------------------------------------------------------------------------------------------------------
# Patchbay Help Overlay Widget
# ------------------------------------------------------------------------------------------------------------


def _get_event_global_pos(event):
    if hasattr(event, "globalPosition"):
        return event.globalPosition().toPoint()
    return event.globalPos()


# ------------------------------------------------------------------------------------------------------------
# Floating Photoshop-style Modal Toolbar (Left Vertical Palette)
# ------------------------------------------------------------------------------------------------------------

from carla_shared import getBestNerdFont

_GLYPH_OFFSET_CACHE = {}


def get_glyph_visual_offset(glyph, font, size):
    """Calculate the precise (dx, dy) pixel shift required to visually center a glyph."""
    if not glyph:
        return (0, 0)
    family = font.family() if hasattr(font, "family") else ""
    pt_size = font.pointSize() if hasattr(font, "pointSize") else 0
    key = (glyph, family, pt_size, size)
    if key in _GLYPH_OFFSET_CACHE:
        return _GLYPH_OFFSET_CACHE[key]

    W, H = size, size
    img = QImage(W, H, QImage.Format_ARGB32)
    img.fill(0)
    p = QPainter(img)
    p.setFont(font)
    p.setPen(QColor(255, 255, 255))
    p.drawText(QRect(0, 0, W, H), Qt.AlignCenter, glyph)
    p.end()

    min_x, max_x = W, -1
    min_y, max_y = H, -1
    for y in range(H):
        for x in range(W):
            if (img.pixel(x, y) >> 24) & 0xFF > 20:
                if x < min_x:
                    min_x = x
                if x > max_x:
                    max_x = x
                if y < min_y:
                    min_y = y
                if y > max_y:
                    max_y = y

    if max_x == -1:
        offset = (0, 0)
    else:
        cx = (min_x + max_x) / 2.0
        cy = (min_y + max_y) / 2.0
        offset = (int(round((W - 1) / 2.0 - cx)), int(round((H - 1) / 2.0 - cy)))

    _GLYPH_OFFSET_CACHE[key] = offset
    return offset


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

        # Icons: Sensible Nerd Font glyphs or clean unicode symbols
        self.icon_pointer = "\uf245" if font_family else "↖"  # nf-fa-mouse-pointer
        self.icon_select = "\uf247" if font_family else "⛶"  # nf-fa-object-group
        self.icon_hand = "\uf256" if font_family else ","  # nf-fa-hand-paper-o
        self.icon_zoomin = "\uf00e" if font_family else "+"  # nf-fa-search-plus
        self.icon_zoomout = "\uf010" if font_family else "-"  # nf-fa-search-minus
        self.icon_fit = "\uf0b2" if font_family else "⛶"  # nf-fa-arrows-alt
        self.icon_grid = "\uf00a" if font_family else "#"  # nf-fa-th
        self.icon_snap = "\uf076" if font_family else ""  # nf-fa-magnet
        self.icon_flow = "\uf21e" if font_family else "∿"  # nf-fa-heartbeat
        self.icon_help = "\uf059" if font_family else "?"  # nf-fa-question-circle
        # Main Application Menu Button (Accessible when Menubar is hidden)
        self.btnMenu = CanvasToolButton("☰", self)
        self.btnMenu.setObjectName("canvasMenuButton")
        self.btnMenu.setToolTip("Main Menu (Ctrl+M to toggle menubar)")
        self.btnMenu.setFont(font)
        self.btnMenu.setFixedSize(28, 28)
        self.btnMenu.clicked.connect(self._slot_openMainMenu)
        layout.addWidget(self.btnMenu)

        # Mode Selection Buttons (Checkable, Mutually Exclusive)
        self.btnPointer = CanvasToolButton(self.icon_pointer, self)
        self.btnPointer.setToolTip("Pointer Tool (Q / Esc)")
        self.btnPointer.setFont(font)

        self.btnSelect = CanvasToolButton(self.icon_select, self)
        self.btnSelect.setToolTip("Marquee Selection (V)")
        self.btnSelect.setFont(font)

        self.btnHand = CanvasToolButton(self.icon_hand, self)
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
        self.btnZoomIn = CanvasToolButton(self.icon_zoomin, self)
        self.btnZoomIn.setToolTip("Zoom In (+)")
        self.btnZoomIn.setFont(font)
        self.btnZoomIn.setFixedSize(28, 28)
        self.btnZoomIn.clicked.connect(lambda: self._zoom(120))
        layout.addWidget(self.btnZoomIn)

        self.btnZoomOut = CanvasToolButton(self.icon_zoomout, self)
        self.btnZoomOut.setToolTip("Zoom Out (-)")
        self.btnZoomOut.setFont(font)
        self.btnZoomOut.setFixedSize(28, 28)
        self.btnZoomOut.clicked.connect(lambda: self._zoom(-120))
        layout.addWidget(self.btnZoomOut)

        self.btnFit = CanvasToolButton(self.icon_fit, self)
        self.btnFit.setToolTip("Zoom to Fit All Nodes (F)")
        self.btnFit.setFont(font)
        self.btnFit.setFixedSize(28, 28)
        self.btnFit.clicked.connect(self._slot_zoomFit)
        layout.addWidget(self.btnFit)

        add_sep()

        # Canvas Dot Grid Toggle
        self.btnGrid = CanvasToolButton(self.icon_grid, self)
        self.btnGrid.setToolTip("Toggle Dot Grid Visibility")
        self.btnGrid.setFont(font)
        self.btnGrid.setFixedSize(28, 28)
        self.btnGrid.setCheckable(True)
        self.btnGrid.setChecked(getattr(patchcanvas.options, "grid_enabled", True))
        self.btnGrid.clicked.connect(self._slot_toggleGrid)
        layout.addWidget(self.btnGrid)

        # Coordinate Snapping Toggle
        self.btnSnap = CanvasToolButton(self.icon_snap, self)
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
        self.btnSignalFlow = CanvasToolButton(self.icon_flow, self)
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
        self.btnHelp = CanvasToolButton(self.icon_help, self)
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
        if cached is not None and now - cached[0] < 0.05:
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
                level = max(in_level, out_level)
                if level > 0.0:
                    plugin_levels[gid] = level
                if out_level > 0.0:
                    plugin_flow[gid] = out_level
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
                    if lvl > 0.0:
                        levels[gid] = max(levels.get(gid, 0.0), lvl)
                        flow[gid] = max(flow.get(gid, 0.0), lvl)

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
                    if lvl > 0.0:
                        levels[gid] = max(levels.get(gid, 0.0), lvl)
                        flow[gid] = max(flow.get(gid, 0.0), lvl)

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
                    if out_id in non_plugin_ids and out_id not in levels:
                        levels[out_id] = best * 0.85
                    if in_id in non_plugin_ids and in_id not in levels:
                        levels[in_id] = best * 0.85

        return levels, flow

    def _repaintActiveSignalItems(self):
        from patchcanvas import signalflow

        levels = signalflow.state.levels
        flow = signalflow.state.flow
        if not levels and not flow:
            return
        canvas = patchcanvas.canvas
        for conn in list(canvas.connection_list):
            if getattr(conn, "group_out_id", None) in flow:
                widget = getattr(conn, "widget", None)
                if widget is not None:
                    widget.update()
        for group in list(canvas.group_list):
            if getattr(group, "group_id", None) in levels:
                for w in group.widgets:
                    if w is not None:
                        w.update()

    def updateActiveButton(self, mode):
        self.btnPointer.setChecked(mode == 0)
        self.btnSelect.setChecked(mode == 1)
        self.btnHand.setChecked(mode == 2)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._dragPos = (
                _get_event_global_pos(event) - self.frameGeometry().topLeft()
            )
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
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


class CanvasContextToolBarOverlay(QFrame):
    """Floating context-sensitive horizontal action toolbar centered on the patchbay's top edge."""

    def __init__(self, graphicsView, parent=None):
        super().__init__(parent or graphicsView.viewport())
        self.setObjectName("canvas_context_toolbar_overlay")
        self.graphicsView = graphicsView
        self._dragPos = None
        self._userMoved = False

        self.layout = QHBoxLayout(self)
        self.layout.setContentsMargins(6, 3, 6, 3)
        self.layout.setSpacing(3)

        self.font_family = getBestNerdFont()
        self.font = QFont(self.font_family, 12) if self.font_family else QFont()
        if not self.font_family:
            self.font.setPointSize(10)

        # Persistent quick-search field (kept out of the rebuilt action items so
        # it survives selection changes). Rounded textbox housed in the bar.
        self.searchEdit = QLineEdit(self)
        self.searchEdit.setObjectName("canvasSearchEdit")
        self.searchEdit.setPlaceholderText("Search nodes…")
        self.searchEdit.setClearButtonEnabled(True)
        self.searchEdit.setFixedHeight(24)
        self.searchEdit.setFixedWidth(170)
        self.searchEdit.textChanged.connect(self._slot_search_changed)
        self.searchEdit.returnPressed.connect(self._slot_search_accept)
        self.searchEdit.installEventFilter(self)

        self.updateSelection()

    def _slot_search_changed(self, text):
        gv = self.graphicsView
        if hasattr(gv, "_onSearchTextChanged"):
            gv._onSearchTextChanged(text)

    def _slot_search_accept(self):
        gv = self.graphicsView
        if hasattr(gv, "_onSearchAccept"):
            gv._onSearchAccept()

    def eventFilter(self, obj, event):
        if obj is getattr(self, "searchEdit", None):
            ktype = QEvent.Type.KeyPress if hasattr(QEvent, "Type") else QEvent.KeyPress
            if event.type() == ktype:
                if event.key() == Qt.Key_Escape:
                    self.searchEdit.clearFocus()
                    gv = self.graphicsView
                    if hasattr(gv, "hideSearch"):
                        gv.hideSearch()
                    return True
                if event.key() in (Qt.Key_Down, Qt.Key_Up):
                    lst = getattr(self.graphicsView, "fSearchList", None)
                    if lst is not None and lst.isVisible() and lst.count():
                        lst.setFocus()
                        lst.setCurrentRow(
                            0 if event.key() == Qt.Key_Down else lst.count() - 1
                        )
                        return True
        return QFrame.eventFilter(self, obj, event)

    def clearLayout(self):
        while self.layout.count():
            item = self.layout.takeAt(0)
            w = item.widget()
            if w is not None and w is not getattr(self, "searchEdit", None):
                w.setParent(None)
                w.deleteLater()

    def addSeparator(self):
        line = QFrame(self)
        line.setObjectName("canvasToolbarSeparator")
        line.setFrameShape(QFrame.VLine)
        line.setFrameShadow(QFrame.Sunken)
        line.setFixedSize(1, 18)
        self.layout.addWidget(line)
        self._items.append(line)

    def addButton(self, icon, tooltip, callback, checkable=False, checked=False):
        btn = CanvasToolButton(icon, self)
        btn.setToolTip(tooltip)
        btn.setFont(self.font)
        btn.setFixedSize(26, 26)
        if checkable:
            btn.setCheckable(True)
            btn.setChecked(checked)
        btn.clicked.connect(callback)
        self.layout.addWidget(btn)
        self._items.append(btn)
        return btn

    def addLabel(self, text, tooltip=""):
        lbl = QLabel(text, self)
        lbl.setFont(self.font)
        if tooltip:
            lbl.setToolTip(tooltip)
        self.layout.addWidget(lbl)
        self._items.append(lbl)
        return lbl

    def updateSelection(self):
        self._items = []
        self.clearLayout()
        selected = patchcanvas.getSelectedNodes()
        count = len(selected)

        # Quick-search field always leads the bar (rounded textbox)
        search = getattr(self, "searchEdit", None)
        if search is not None:
            search.show()
            self.layout.addWidget(search)
            self._items.append(search)
            self.addSeparator()

        nf = bool(self.font_family)
        # Nerd Font glyphs (FontAwesome / Material exact match)
        icon_arr = "\uf0e8" if nf else "🔀"  # nf-fa-sitemap
        icon_repel = "\uf0b2" if nf else "↔"  # nf-fa-arrows-alt
        icon_aside = "\uf08d" if nf else "⏭"  # nf-fa-thumb-tack
        icon_sel = "\uf046" if nf else "⛶"  # nf-fa-check-square-o
        icon_desel = "\uf00d" if nf else "✕"  # nf-fa-times
        icon_inv = "\uf0ec" if nf else "⇄"  # nf-fa-exchange
        icon_edit = "\uf1de" if nf else "⚙"  # nf-fa-sliders
        icon_ui = "\uf108" if nf else "🖥"  # nf-fa-desktop
        icon_rack = "\uf1b3" if nf else "📦"  # nf-fa-cubes
        icon_clone = "\uf24d" if nf else "⧉"  # nf-fa-clone
        icon_ren = "\uf040" if nf else "✎"  # nf-fa-pencil
        icon_del = "\uf1f8" if nf else "🗑"  # nf-fa-trash
        icon_cut = "\uf127" if nf else "✂"  # nf-fa-chain-broken
        icon_split = "\uf0db" if nf else "⚯"  # nf-fa-columns
        icon_color = "\uf1fc" if nf else "🎨"  # nf-fa-paint-brush
        icon_prop = "\uf05a" if nf else "ℹ"  # nf-fa-info-circle
        icon_power = "\uf011" if nf else "⏻"  # nf-fa-power-off
        icon_bypass = "\uf205" if nf else "⮀"  # nf-fa-toggle-on
        icon_ports = "\uf070" if nf else ""  # nf-fa-eye-slash
        icon_al_h = "󱇆" if nf else "═"  # nf-fa-align-center
        icon_al_v = "󱇃" if nf else "║"  # nf-fa-align-center
        icon_dist_h = "\uf07e" if nf else "⬌"  # nf-fa-arrows-h
        icon_dist_v = "\uf07d" if nf else "⬍"  # nf-fa-arrows-v
        icon_tools = "\uf085" if nf else "🧰"  # nf-fa-cogs

        # Check for selected containers in the scene
        selected_containers = []
        if self.graphicsView and self.graphicsView.scene():
            selected_containers = [
                it for it in self.graphicsView.scene().selectedItems()
                if it and it.type() == patchcanvas.CanvasContainerType
            ]

        if count == 0 and selected_containers:
            # Single or Multiple Container Context Actions
            c = selected_containers[0]
            c_name = getattr(c, "m_title", "Group")
            short_c_name = (c_name[:14] + "…") if len(c_name) > 15 else c_name
            self.addLabel(f"[GROUP] {short_c_name.upper()}", f"Container: {c_name}")
            self.addSeparator()

            # Rename
            self.addButton(icon_ren, "Rename Container...", c.promptRename)

            # Layout Mode switcher
            btnLayout = self.addButton(icon_split, f"Layout Mode: {getattr(c, 'm_layout_mode', 'vbox').upper()}", lambda: None)
            btnLayout.clicked.disconnect()
            btnLayout.clicked.connect(lambda: self._slot_show_container_layout_menu(btnLayout, c))

            # Color Picker
            btnCColor = self.addButton(icon_color, "Container Color...", lambda: None)
            btnCColor.clicked.disconnect()
            btnCColor.clicked.connect(lambda: self._slot_show_color_menu(btnCColor, [c]))

            # Collapse / Expand
            is_col = getattr(c, "m_collapsed", False)
            col_icon = "\uf067" if is_col else "\uf068" if nf else ("[+]" if is_col else "[-]")
            col_tip = "Expand Group" if is_col else "Collapse Group"
            self.addButton(col_icon, col_tip, lambda: (c.toggleCollapse(), self.updateSelection()))

            # Ungroup
            self.addButton(icon_del, "Ungroup / Dissolve Container", lambda: (c.ungroup(), self.updateSelection()))
            self.addSeparator()
            self.addButton(icon_desel, "Deselect (Esc)", patchcanvas.deselectAllNodes)

        elif count == 0:
            # Global Canvas Actions
            self.addLabel("CANVAS", "Patchbay Canvas Actions")
            self.addSeparator()

            self.addButton(
                icon_aside, "Park Disconnected Nodes Aside", self._slot_move_aside_all
            )
            self.addSeparator()
            self.addButton(
                icon_sel, "Select All Nodes (Ctrl+A)", patchcanvas.selectAllNodes
            )

        elif count == 1:
            # Single Node Context Actions
            node = selected[0]
            name = getattr(node, "m_group_name", "Node")
            short_name = (name[:14] + "…") if len(name) > 15 else name

            badge = getattr(node, "m_type_badge", "")
            badge_txt = f"[{badge}] " if badge else ""
            self.addLabel(
                f"{badge_txt}{short_name.upper()}", f"{name} ({badge or 'Node'})"
            )
            self.addSeparator()

            plugin_id = getattr(node, "m_plugin_id", -1)
            has_plugin = 0 <= plugin_id <= patchcanvas.MAX_PLUGIN_ID_ALLOWED
            has_ui = getattr(node, "m_plugin_ui", False)

            if has_plugin:
                # Power & Bypass
                self.addButton(
                    icon_power,
                    "Power / Toggle Active",
                    lambda: self._slot_toggle_power(node),
                )
                self.addButton(
                    icon_bypass,
                    "Toggle Bypass (Dry/Wet)",
                    lambda: self._slot_toggle_bypass(node),
                )
                self.addSeparator()

                # Parameter Edit & Custom UI
                self.addButton(
                    icon_edit,
                    "Edit Parameters",
                    lambda: patchcanvas.canvas.callback(
                        patchcanvas.ACTION_PLUGIN_EDIT, plugin_id, 0, ""
                    ),
                )
                if has_ui:
                    self.addButton(
                        icon_ui,
                        "Show Custom Plugin GUI",
                        lambda: patchcanvas.canvas.callback(
                            patchcanvas.ACTION_PLUGIN_SHOW_UI, plugin_id, 0, ""
                        ),
                    )
                self.addButton(
                    icon_rack,
                    "Jump to Plugin in Rack Tab",
                    lambda: self._slot_jump_rack(plugin_id),
                )
                self.addButton(
                    icon_clone,
                    "Duplicate / Clone Plugin",
                    lambda: patchcanvas.canvas.callback(
                        patchcanvas.ACTION_PLUGIN_CLONE, plugin_id, 0, ""
                    ),
                )
                self.addButton(
                    icon_ren,
                    "Rename Plugin...",
                    lambda: patchcanvas.canvas.callback(
                        patchcanvas.ACTION_PLUGIN_RENAME, plugin_id, 0, ""
                    ),
                )
                self.addButton(
                    icon_del,
                    "Remove Plugin",
                    lambda: patchcanvas.canvas.callback(
                        patchcanvas.ACTION_PLUGIN_REMOVE, plugin_id, 0, ""
                    ),
                )
                self.addSeparator()

            # Appearance & Box Setup
            btnColor = self.addButton(
                icon_color, "Node Tint Color Presets & Custom...", lambda: None
            )
            btnColor.clicked.disconnect()
            btnColor.clicked.connect(
                lambda: self._slot_show_color_menu(btnColor, [node])
            )

            if hasattr(node, "showPropertiesDialog"):
                self.addButton(
                    icon_prop, "Node Properties & Badges...", node.showPropertiesDialog
                )

            # Hide/Show unconnected ports
            hiding_ports = getattr(node, "m_hide_unconnected_ports", False)
            self.addButton(
                icon_ports,
                "Toggle Hide Unconnected Ports",
                lambda: self._slot_toggle_hide_ports(node),
                checkable=True,
                checked=hiding_ports,
            )

            # Split/Join if available
            split_label = "Join" if getattr(node, "m_split", False) else "Split"
            self.addButton(
                icon_split,
                f"{split_label} Input/Output Box Groups",
                lambda: self._slot_split_join(node),
            )

            # Disconnect all cables from this node
            self.addButton(
                icon_cut,
                "Disconnect All Cables from This Node",
                lambda: self._slot_disconnect_node(node),
            )

            self.addSeparator()
            self.addButton(
                icon_arr,
                "Auto-Arrange Subgraph Connected to This Node",
                lambda: patchcanvas.arrangeConnected(node, "both"),
            )
            self.addButton(
                icon_aside,
                "Park This Node Aside",
                lambda: patchcanvas.moveAsideNonConnectedNodes(node),
            )
            self.addButton(icon_desel, "Deselect (Esc)", patchcanvas.deselectAllNodes)

        else:
            # Multiple Nodes Batch Actions
            self.addLabel(f"{count} NODES", f"{count} Selected Nodes")
            self.addSeparator()

            # Batch Align & Distribute
            self.addButton(
                icon_al_h,
                "Align Selected Nodes Horizontally",
                lambda: patchcanvas.alignSelected("horizontal"),
            )
            self.addButton(
                icon_al_v,
                "Align Selected Nodes Vertically",
                lambda: patchcanvas.alignSelected("vertical"),
            )
            self.addButton(
                icon_dist_h,
                "Distribute Horizontally with Equal Spacing",
                lambda: patchcanvas.alignSelected("distribute_h"),
            )
            self.addButton(
                icon_dist_v,
                "Distribute Vertically with Equal Spacing",
                lambda: patchcanvas.alignSelected("distribute_v"),
            )
            self.addButton(
                icon_repel,
                "Auto-Repel Selected Overlaps",
                lambda: patchcanvas.repelNodes(selected),
            )
            self.addSeparator()

            # Batch Operations
            btnBatchColor = self.addButton(
                icon_color, "Batch Color Selected Nodes...", lambda: None
            )
            btnBatchColor.clicked.disconnect()
            btnBatchColor.clicked.connect(
                lambda: self._slot_show_color_menu(btnBatchColor, selected)
            )

            self.addButton(
                icon_power,
                "Batch Toggle Power (Active)",
                lambda: self._slot_batch_power(selected),
            )
            self.addButton(
                icon_bypass,
                "Batch Toggle Bypass",
                lambda: self._slot_batch_bypass(selected),
            )
            self.addButton(
                icon_ports,
                "Batch Toggle Hide Unconnected Ports",
                lambda: self._slot_batch_hide_ports(selected),
            )
            self.addButton(
                icon_cut,
                "Disconnect All Cables on Selected Nodes",
                lambda: self._slot_disconnect_selected(selected),
            )
            # Group into Container
            btnGroup = self.addButton(icon_rack, "Group Selected Nodes into Container...", lambda: None)
            btnGroup.clicked.disconnect()
            btnGroup.clicked.connect(lambda: self._slot_show_group_create_menu(btnGroup))
            self.addSeparator()

            self.addButton(
                icon_inv, "Invert Selection", patchcanvas.invertNodeSelection
            )
            self.addButton(
                icon_desel, "Clear Selection (Esc)", patchcanvas.deselectAllNodes
            )

        # Grouped "Arrange tools" popover, always available so the bar stays uncluttered
        self.addSeparator()
        btnTools = self.addButton(
            icon_tools, "Arrange Tools: auto-arrange, auto-wire, repel", lambda: None
        )
        btnTools.clicked.disconnect()
        btnTools.clicked.connect(lambda: self._slot_show_arrange_menu(btnTools, count))

        # Calculate exact pixel width for pure icon controls
        total_w = (
            self.layout.contentsMargins().left() + self.layout.contentsMargins().right()
        )
        spacing = self.layout.spacing()
        for w in self._items:
            w.show()
            if w is getattr(self, "searchEdit", None):
                w.setFixedSize(170, 24)
                total_w += 170 + spacing
            elif isinstance(w, QFrame) and not isinstance(w, (QLabel, QPushButton)):
                w.setFixedSize(1, 18)
                total_w += 1 + spacing
            elif isinstance(w, QPushButton):
                w.setFixedSize(26, 26)
                total_w += 26 + spacing
            else:
                txt = getattr(w, "text", lambda: "")()
                fm = w.fontMetrics()
                w_item = fm.boundingRect(txt).width() + 14
                w.setFixedSize(w_item, 24)
                total_w += w_item + spacing

        if self._items:
            total_w -= spacing

        self.setFixedSize(max(60, total_w), 32)
        if search is not None and search.hasFocus():
            search.setFocus()
        if not getattr(self, "_userMoved", False):
            self.reposition()

    def _slot_show_color_menu(self, source_button, nodes):
        menu = QMenu(self)

        presets = [
            ("Default Dark", "#1e1e2e"),
            ("Crimson / Red", "#f38ba8"),
            ("Synth / Green", "#a6e3a1"),
            ("Audio / Blue", "#89b4fa"),
            ("MIDI / Yellow", "#f9e2af"),
            ("FX / Mauve", "#cba6f7"),
            ("Dynamics / Peach", "#fab387"),
            ("Teal / Mod", "#94e2d5"),
            ("Sky / Light Blue", "#89dceb"),
            ("Flamingo / Coral", "#f2cdcd"),
        ]

        def create_color_icon(hex_str):
            pix = QPixmap(14, 14)
            pix.fill(Qt.transparent)
            p = QPainter(pix)
            p.setRenderHint(QPainter.Antialiasing, True)
            p.setBrush(QColor(hex_str))
            p.setPen(QColor("#45475a"))
            p.drawRoundedRect(1, 1, 12, 12, 3, 3)
            p.end()
            return QIcon(pix)

        for name, hex_code in presets:
            act = menu.addAction(create_color_icon(hex_code), name)
            act.triggered.connect(
                lambda checked, h=hex_code: self._apply_color_to_nodes(nodes, h)
            )

        menu.addSeparator()
        act_custom = menu.addAction("Custom Color Picker...")
        act_custom.triggered.connect(lambda: self._open_custom_color_dialog(nodes))

        act_reset = menu.addAction("Reset to Theme Default")
        act_reset.triggered.connect(lambda: self._apply_color_to_nodes(nodes, ""))

        btn_pos = source_button.mapToGlobal(QPoint(0, source_button.height() + 4))
        menu.exec_(btn_pos)

    def _slot_show_arrange_menu(self, source_button, count):
        menu = QMenu(self)

        has_selection = count > 0

        arrange_menu = menu.addMenu("Auto arrange")
        for algo_name, algo_label in patchcanvas.layout_algorithms():
            act = arrange_menu.addAction(algo_label)
            act.triggered.connect(
                lambda checked=False, a=algo_name: self._slot_run_arrange(a)
            )

        act_wire = menu.addAction("Auto wire")
        act_wire.triggered.connect(lambda: patchcanvas.autoWire())
        act_wire.setEnabled(has_selection)

        act_both = menu.addAction("Arrange + wire")
        act_both.triggered.connect(lambda: patchcanvas.autoArrangeAndWire())
        act_both.setEnabled(has_selection)

        menu.addSeparator()
        act_repel = menu.addAction(
            "Auto repel all" if not has_selection else "Auto repel selection"
        )
        act_repel.triggered.connect(lambda: patchcanvas.autoRepelNodes())

        btn_pos = source_button.mapToGlobal(QPoint(0, source_button.height() + 4))
        menu.exec_(btn_pos)

    def _slot_run_arrange(self, algorithm):
        patchcanvas.options.arrange_style = algorithm
        try:
            from utils import QSafeSettings
            from carla_shared import CARLA_KEY_CANVAS_ARRANGE_STYLE

            QSafeSettings("falkTX", "Carla2").setValue(
                CARLA_KEY_CANVAS_ARRANGE_STYLE, algorithm
            )
        except Exception:
            pass
        patchcanvas.autoArrangeNodes(algorithm=algorithm)

    def _apply_color_to_nodes(self, nodes, hex_str):
        for n in nodes:
            if hasattr(n, "setColor") and hasattr(n, "m_layout_mode"):
                n.setColor(hex_str if hex_str else "#89b4fa")
                continue
            if hasattr(n, "setCustomColor"):
                n.setCustomColor(hex_str)
            pid = getattr(n, "m_plugin_id", -1)
            if 0 <= pid <= patchcanvas.MAX_PLUGIN_ID_ALLOWED:
                patchcanvas.canvas.callback(
                    patchcanvas.ACTION_PLUGIN_COLOR, pid, 0, hex_str
                )

    def _open_custom_color_dialog(self, nodes):
        initial = QColor("#1e1e2e")
        if nodes:
            if hasattr(nodes[0], "m_color") and nodes[0].m_color:
                initial = nodes[0].m_color
            elif hasattr(nodes[0], "m_custom_color") and nodes[0].m_custom_color:
                initial = QColor(nodes[0].m_custom_color)
        color = QColorDialog.getColor(initial, self, "Choose Tint Color")
        if color.isValid():
            self._apply_color_to_nodes(nodes, color.name())

    def _slot_show_container_layout_menu(self, source_button, container):
        menu = QMenu(self)
        modes = [
            ("vbox", "VBox (Vertical)"),
            ("hbox", "HBox (Horizontal)"),
            ("grid", "Grid (Matrix)"),
            ("freeform", "Freeform (Unconstrained)"),
        ]
        cur = getattr(container, "m_layout_mode", "vbox")
        for mode_key, mode_name in modes:
            act = menu.addAction(mode_name)
            act.setCheckable(True)
            act.setChecked(cur == mode_key)
            act.triggered.connect(lambda checked=False, m=mode_key: (container.setLayoutMode(m), self.updateSelection()))

        btn_pos = source_button.mapToGlobal(QPoint(0, source_button.height() + 4))
        menu.exec_(btn_pos)

    def _slot_show_group_create_menu(self, source_button):
        menu = QMenu(self)
        modes = [
            ("vbox", "VBox (Vertical)"),
            ("hbox", "HBox (Horizontal)"),
            ("grid", "Grid (Matrix)"),
            ("freeform", "Freeform (Unconstrained)"),
        ]
        for mode_key, mode_name in modes:
            act = menu.addAction(mode_name)
            act.triggered.connect(lambda checked=False, m=mode_key: (patchcanvas.createContainerFromSelected(m), self.updateSelection()))

        btn_pos = source_button.mapToGlobal(QPoint(0, source_button.height() + 4))
        menu.exec_(btn_pos)

    def _slot_toggle_power(self, node):
        pid = getattr(node, "m_plugin_id", -1)
        if not (0 <= pid <= patchcanvas.MAX_PLUGIN_ID_ALLOWED):
            return
        try:
            from carla_shared import gCarla
            from carla_backend import PARAMETER_ACTIVE

            pwidget = (
                gCarla.gui.getPluginWidget(pid)
                if hasattr(gCarla.gui, "getPluginWidget")
                else None
            )
            if pwidget is not None and hasattr(pwidget, "fIsActive"):
                cur = bool(pwidget.fIsActive)
            elif hasattr(gCarla.gui, "host") and hasattr(
                gCarla.gui.host, "get_internal_parameter_value"
            ):
                cur = bool(
                    gCarla.gui.host.get_internal_parameter_value(pid, PARAMETER_ACTIVE)
                    >= 0.5
                )
            else:
                cur = True
            new_state = not cur
            gCarla.gui.host.set_active(pid, new_state)
            if pwidget is not None:
                pwidget.setActive(new_state, sendCallback=True, sendHost=False)
            if hasattr(node, "update"):
                node.update()
            scene = self.graphicsView.scene()
            if scene:
                scene.update()
        except Exception as e:
            print(f"CanvasContextToolBarOverlay::_slot_toggle_power error: {e}")

    def _slot_toggle_bypass(self, node):
        pid = getattr(node, "m_plugin_id", -1)
        if not (0 <= pid <= patchcanvas.MAX_PLUGIN_ID_ALLOWED):
            return
        try:
            from carla_shared import gCarla
            from carla_backend import PARAMETER_DRYWET

            pwidget = (
                gCarla.gui.getPluginWidget(pid)
                if hasattr(gCarla.gui, "getPluginWidget")
                else None
            )
            cur_val = gCarla.gui.host.get_internal_parameter_value(
                pid, PARAMETER_DRYWET
            )
            new_val = 1.0 if cur_val == 0.0 else 0.0
            gCarla.gui.host.set_drywet(pid, new_val)
            if pwidget is not None:
                pwidget.setParameterValue(PARAMETER_DRYWET, new_val, True)
                if hasattr(pwidget, "_update_bypass_state"):
                    pwidget._update_bypass_state(bool(new_val == 0.0))
            if hasattr(node, "update"):
                node.update()
            scene = self.graphicsView.scene()
            if scene:
                scene.update()
        except Exception as e:
            print(f"CanvasContextToolBarOverlay::_slot_toggle_bypass error: {e}")

    def _slot_batch_power(self, nodes):
        for n in nodes:
            self._slot_toggle_power(n)

    def _slot_batch_bypass(self, nodes):
        for n in nodes:
            self._slot_toggle_bypass(n)

    def _slot_batch_hide_ports(self, nodes):
        any_unhidden = any(
            not getattr(n, "m_hide_unconnected_ports", False) for n in nodes
        )
        for n in nodes:
            if hasattr(n, "setHideUnconnectedPorts"):
                n.setHideUnconnectedPorts(any_unhidden)
            else:
                n.m_hide_unconnected_ports = any_unhidden
                if hasattr(n, "updatePositions"):
                    n.updatePositions()
        scene = self.graphicsView.scene()
        if scene:
            scene.update()
        self.updateSelection()

    def _slot_toggle_hide_ports(self, node):
        new_val = not getattr(node, "m_hide_unconnected_ports", False)
        if hasattr(node, "setHideUnconnectedPorts"):
            node.setHideUnconnectedPorts(new_val)
        else:
            node.m_hide_unconnected_ports = new_val
            if hasattr(node, "updatePositions"):
                node.updatePositions()
            scene = self.graphicsView.scene()
            if scene:
                scene.update()
        self.updateSelection()

    def _slot_split_join(self, node):
        group_id = getattr(node, "m_group_id", -1)
        if group_id < 0:
            return
        if getattr(node, "m_split", False):
            patchcanvas.canvas.callback(patchcanvas.ACTION_GROUP_JOIN, group_id, 0, "")
        else:
            patchcanvas.canvas.callback(patchcanvas.ACTION_GROUP_SPLIT, group_id, 0, "")

    def _slot_disconnect_node(self, node):
        group_id = getattr(node, "m_group_id", -1)
        port_ids = set(getattr(node, "m_port_list_ids", []))
        conns_to_drop = []
        for c in patchcanvas.canvas.connection_list:
            if (c.group_out_id == group_id and c.port_out_id in port_ids) or (
                c.group_in_id == group_id and c.port_in_id in port_ids
            ):
                conns_to_drop.append(c.connection_id)
        for cid in conns_to_drop:
            patchcanvas.canvas.callback(patchcanvas.ACTION_PORTS_DISCONNECT, cid, 0, "")

    def _slot_disconnect_selected(self, nodes):
        node_groups_ports = set()
        for n in nodes:
            gid = getattr(n, "m_group_id", -1)
            for pid in getattr(n, "m_port_list_ids", []):
                node_groups_ports.add((gid, pid))
        conns_to_drop = []
        for c in patchcanvas.canvas.connection_list:
            if (c.group_out_id, c.port_out_id) in node_groups_ports or (
                c.group_in_id,
                c.port_in_id,
            ) in node_groups_ports:
                conns_to_drop.append(c.connection_id)
        for cid in conns_to_drop:
            patchcanvas.canvas.callback(patchcanvas.ACTION_PORTS_DISCONNECT, cid, 0, "")

    def _slot_arrange(self):
        patchcanvas.arrange()

    def _slot_repel_all(self):
        all_n = []
        for g in patchcanvas.canvas.group_list:
            for w in g.widgets:
                if w is not None and w.isVisible():
                    all_n.append(w)
        patchcanvas.repelNodes(all_n)

    def _slot_move_aside_all(self):
        patchcanvas.moveAsideNonConnectedNodes()

    def _slot_jump_rack(self, plugin_id):
        try:
            from carla_shared import gCarla

            if hasattr(gCarla.gui, "ui"):
                split_idx = gCarla.gui.ui.tabWidget.indexOf(
                    getattr(gCarla.gui, "tabSplit", None)
                )
                if split_idx >= 0:
                    gCarla.gui.ui.tabWidget.setCurrentIndex(split_idx)
                else:
                    gCarla.gui.ui.tabWidget.setCurrentIndex(0)
                pitem = gCarla.gui.getPluginItem(plugin_id)
                if pitem is not None and gCarla.gui.ui.listWidget is not None:
                    gCarla.gui.ui.listWidget.setCurrentItem(pitem)
                    gCarla.gui.ui.listWidget.scrollToItem(pitem)
        except Exception as e:
            print("Error jumping to rack:", e)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._dragPos = (
                _get_event_global_pos(event) - self.frameGeometry().topLeft()
            )
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
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
        # Top toolbar: pinned to the patchbay's top edge, horizontally centered.
        x = max(12, (parent.width() - self.width()) // 2)
        y = 12
        self.move(x, y)
        self.raise_()


# ------------------------------------------------------------------------------------------------------------
# Canvas Viewport Event Filter (Auto-Scroll & UI Disconnect)
# ------------------------------------------------------------------------------------------------------------


class CanvasViewportFilter(QObject):
    """Event filter managing boundary auto-scrolling during drag and quick disconnects."""

    def __init__(self, hostWindow, graphicsView):
        super().__init__(graphicsView.viewport())
        self.hostWindow = hostWindow
        self.graphicsView = graphicsView

        self._dragActive = False
        self._inSyntheticMouseMove = False

        self._scrollTimer = QTimer(self)
        self._scrollTimer.setInterval(20)  # 50 Hz smooth scrolling
        self._scrollTimer.timeout.connect(self._slot_autoScroll)

        # Create floating mode toolbar & context toolbar, parented to the
        # patchbay widget itself so they stay with the canvas frame when the
        # view is panned, zoomed or resized.
        overlayParent = self.graphicsView.parentWidget() or self.graphicsView
        self.toolBar = CanvasToolBarOverlay(self.graphicsView, overlayParent)
        if hasattr(self.hostWindow, "ui") and hasattr(self.hostWindow.ui, "menubar"):
            self.toolBar.btnMenu.setVisible(not self.hostWindow.ui.menubar.isVisible())
        self.toolBar.show()
        QTimer.singleShot(100, self.toolBar.reposition)

        self.contextToolBar = CanvasContextToolBarOverlay(
            self.graphicsView, overlayParent
        )
        self.contextToolBar.show()
        QTimer.singleShot(100, self.contextToolBar.reposition)

        # Let the view locate the search field housed in the top toolbar
        self.graphicsView.canvasContextToolBar = self.contextToolBar

        scene = self.graphicsView.scene()
        if scene and hasattr(scene, "selectionChanged"):
            scene.selectionChanged.connect(self.contextToolBar.updateSelection)

        # Hook up tool mode change listener to toolBar
        if hasattr(self.graphicsView, "toolModeChanged"):
            self.graphicsView.toolModeChanged.connect(self.toolBar.updateActiveButton)

        # Install self on viewport
        self.graphicsView.viewport().installEventFilter(self)

    def findPortOrCableUnderMouse(self, vp_pos):
        search_rect = QRect(vp_pos.x() - 8, vp_pos.y() - 8, 16, 16)
        items = self.graphicsView.items(search_rect)
        if not items:
            single = self.graphicsView.itemAt(vp_pos)
            if single is not None:
                items = [single]

        scene_pt = self.graphicsView.mapToScene(vp_pos)

        # 1. Search for a Port item (CanvasPort has m_port_id and m_group_id)
        for item in items:
            gid, pid = self.extractPortAndGroupIds(item)
            if gid is not None and pid is not None:
                return ("port", gid, pid)

        # 2. Check if any CanvasBox has a port under scene_pt
        for item in items:
            gid, pid = self.extractPortFromBox(item, scene_pt)
            if gid is not None and pid is not None:
                return ("port", gid, pid)

        # 3. Check if any item is directly a Cable / Connection line (CanvasBezierLine has item1, item2)
        for item in items:
            cid = self.extractConnectionId(item)
            if cid is not None:
                return ("cable", cid, None)

        # 4. Check patchcanvas.canvas.connection_list if present
        conn_list = getattr(
            getattr(patchcanvas, "canvas", None), "connection_list", None
        )
        if conn_list:
            for conn in conn_list:
                line = getattr(
                    conn, "line", getattr(conn, "fLine", getattr(conn, "m_line", None))
                )
                if line is not None and (
                    line in items or any(it is line for it in items)
                ):
                    cid = getattr(
                        conn,
                        "connection_id",
                        getattr(
                            conn,
                            "connectionId",
                            getattr(conn, "id", getattr(conn, "m_connection_id", None)),
                        ),
                    )
                    if cid is not None:
                        try:
                            return ("cable", int(cid), None)
                        except Exception:
                            pass

            try:
                stroker = QPainterPathStroker()
                stroker.setWidth(16.0)
                for conn in conn_list:
                    line = getattr(
                        conn,
                        "line",
                        getattr(conn, "fLine", getattr(conn, "m_line", None)),
                    )
                    if line is not None and hasattr(line, "shape"):
                        line_pt = line.mapFromScene(scene_pt)
                        path = line.path() if hasattr(line, "path") else line.shape()
                        hit_path = stroker.createStroke(path)
                        if hit_path.contains(line_pt):
                            cid = getattr(
                                conn,
                                "connection_id",
                                getattr(
                                    conn,
                                    "connectionId",
                                    getattr(
                                        conn,
                                        "id",
                                        getattr(conn, "m_connection_id", None),
                                    ),
                                ),
                            )
                            if cid is not None:
                                try:
                                    return ("cable", int(cid), None)
                                except Exception:
                                    pass
            except Exception as e:
                log_carla(f"carla_canvas: connection distance check error: {e}")

        return (None, None, None)

    def extractPortAndGroupIds(self, item):
        target = item
        while target is not None:
            pid = getattr(
                target,
                "m_port_id",
                getattr(
                    target,
                    "port_id",
                    getattr(target, "portId", getattr(target, "fPortId", None)),
                ),
            )
            gid = getattr(
                target,
                "m_group_id",
                getattr(
                    target,
                    "group_id",
                    getattr(
                        target,
                        "groupId",
                        getattr(
                            target,
                            "fGroupId",
                            getattr(
                                target, "clientId", getattr(target, "fClientId", None)
                            ),
                        ),
                    ),
                ),
            )

            if pid is not None and gid is None:
                parent = target.parentItem()
                if parent is not None:
                    gid = getattr(
                        parent,
                        "m_group_id",
                        getattr(
                            parent,
                            "group_id",
                            getattr(
                                parent,
                                "groupId",
                                getattr(
                                    parent,
                                    "fGroupId",
                                    getattr(
                                        parent,
                                        "clientId",
                                        getattr(parent, "fClientId", None),
                                    ),
                                ),
                            ),
                        ),
                    )

            if pid is not None and gid is not None:
                try:
                    return int(gid), int(pid)
                except Exception:
                    pass

            for attr in ("port", "fPort", "_port", "portData", "fPortData"):
                p_obj = getattr(target, attr, None)
                if p_obj is not None:
                    if isinstance(p_obj, dict):
                        p_id = p_obj.get(
                            "m_port_id",
                            p_obj.get("port_id", p_obj.get("portId", p_obj.get("id"))),
                        )
                        g_id = p_obj.get(
                            "m_group_id",
                            p_obj.get(
                                "group_id", p_obj.get("groupId", p_obj.get("clientId"))
                            ),
                        )
                    else:
                        p_id = getattr(
                            p_obj,
                            "m_port_id",
                            getattr(
                                p_obj,
                                "port_id",
                                getattr(p_obj, "portId", getattr(p_obj, "id", None)),
                            ),
                        )
                        g_id = getattr(
                            p_obj,
                            "m_group_id",
                            getattr(
                                p_obj,
                                "group_id",
                                getattr(
                                    p_obj, "groupId", getattr(p_obj, "clientId", None)
                                ),
                            ),
                        )
                    if p_id is not None and g_id is not None:
                        try:
                            return int(g_id), int(p_id)
                        except Exception:
                            pass

            if hasattr(target, "data"):
                try:
                    d = target.data(0)
                    if isinstance(d, tuple) and len(d) == 2:
                        return int(d[0]), int(d[1])
                except Exception:
                    pass

            target = target.parentItem()
        return None, None

    def extractPortFromBox(self, box_item, scene_pt):
        gid = getattr(
            box_item,
            "m_group_id",
            getattr(
                box_item,
                "group_id",
                getattr(
                    box_item,
                    "groupId",
                    getattr(
                        box_item,
                        "fGroupId",
                        getattr(
                            box_item, "clientId", getattr(box_item, "fClientId", None)
                        ),
                    ),
                ),
            ),
        )
        if gid is None:
            return None, None

        for attr in ("ports", "fPorts", "port_list", "fPortList", "_ports"):
            ports_list = getattr(box_item, attr, None)
            if ports_list:
                box_pt = box_item.mapFromScene(scene_pt)
                items_to_check = (
                    ports_list.values() if isinstance(ports_list, dict) else ports_list
                )
                for p in items_to_check:
                    pid = getattr(
                        p,
                        "m_port_id",
                        getattr(
                            p,
                            "port_id",
                            getattr(p, "portId", getattr(p, "fPortId", None)),
                        ),
                    )
                    if pid is None and isinstance(p, dict):
                        pid = p.get(
                            "m_port_id", p.get("port_id", p.get("portId", p.get("id")))
                        )
                    if pid is None:
                        continue
                    rect = getattr(
                        p, "rect", getattr(p, "fRect", getattr(p, "boundingRect", None))
                    )
                    if rect is not None:
                        r = rect() if callable(rect) else rect
                        if hasattr(r, "contains") and r.contains(box_pt):
                            return int(gid), int(pid)
                        if hasattr(r, "center"):
                            c = r.center()
                            dx = c.x() - box_pt.x()
                            dy = c.y() - box_pt.y()
                            if (dx * dx + dy * dy) <= 400:
                                return int(gid), int(pid)
        return None, None

    def extractConnectionId(self, item):
        target = item
        while target is not None:
            # 1. CanvasBezierLine has item1 and item2 as CanvasPort instances
            item1 = getattr(target, "item1", getattr(target, "m_item1", None))
            item2 = getattr(target, "item2", getattr(target, "m_item2", None))
            if item1 is not None and item2 is not None:
                g1, pt1 = self.extractPortAndGroupIds(item1)
                g2, pt2 = self.extractPortAndGroupIds(item2)
                if g1 is not None and g2 is not None:
                    # Search in patchcanvas.canvas.connection_list
                    conn_list = getattr(
                        getattr(patchcanvas, "canvas", None), "connection_list", None
                    )
                    if conn_list:
                        for conn in conn_list:
                            cgOut = getattr(
                                conn,
                                "group_out_id",
                                getattr(conn, "m_group_out_id", None),
                            )
                            cpOut = getattr(
                                conn,
                                "port_out_id",
                                getattr(conn, "m_port_out_id", None),
                            )
                            cgIn = getattr(
                                conn,
                                "group_in_id",
                                getattr(conn, "m_group_in_id", None),
                            )
                            cpIn = getattr(
                                conn, "port_in_id", getattr(conn, "m_port_in_id", None)
                            )
                            if (
                                cgOut == g1
                                and cpOut == pt1
                                and cgIn == g2
                                and cpIn == pt2
                            ) or (
                                cgOut == g2
                                and cpOut == pt2
                                and cgIn == g1
                                and cpIn == pt1
                            ):
                                cid = getattr(
                                    conn,
                                    "connection_id",
                                    getattr(
                                        conn,
                                        "connectionId",
                                        getattr(
                                            conn,
                                            "id",
                                            getattr(conn, "m_connection_id", None),
                                        ),
                                    ),
                                )
                                if cid is not None:
                                    return int(cid)
                            line = getattr(
                                conn,
                                "line",
                                getattr(conn, "fLine", getattr(conn, "m_line", None)),
                            )
                            if line is target or line is item:
                                cid = getattr(
                                    conn,
                                    "connection_id",
                                    getattr(
                                        conn,
                                        "connectionId",
                                        getattr(
                                            conn,
                                            "id",
                                            getattr(conn, "m_connection_id", None),
                                        ),
                                    ),
                                )
                                if cid is not None:
                                    return int(cid)

                    # Search in hostWindow.fConnections
                    for cid, (
                        cgOut,
                        cpOut,
                        cgIn,
                        cpIn,
                    ) in self.hostWindow.fConnections.items():
                        if (
                            cgOut == g1 and cpOut == pt1 and cgIn == g2 and cpIn == pt2
                        ) or (
                            cgOut == g2 and cpOut == pt2 and cgIn == g1 and cpIn == pt1
                        ):
                            return cid

                    # Search in item1/item2 parent box m_connection_lines
                    for port_item in (item1, item2):
                        box = (
                            port_item.parentItem()
                            if hasattr(port_item, "parentItem")
                            else None
                        )
                        if box is not None:
                            cb_lines = getattr(box, "m_connection_lines", None)
                            if cb_lines:
                                for cbl in cb_lines:
                                    line = getattr(
                                        cbl, "line", getattr(cbl, "m_line", None)
                                    )
                                    if line is target or line is item:
                                        cid = getattr(
                                            cbl,
                                            "connection_id",
                                            getattr(
                                                cbl,
                                                "connectionId",
                                                getattr(
                                                    cbl,
                                                    "id",
                                                    getattr(
                                                        cbl, "m_connection_id", None
                                                    ),
                                                ),
                                            ),
                                        )
                                        if cid is not None:
                                            return int(cid)

            # 2. Direct connection ID attributes
            for attr in (
                "connection_id",
                "connectionId",
                "fConnectionId",
                "m_connection_id",
                "id",
                "fId",
                "m_id",
                "conn_id",
                "connId",
                "connection",
                "fConnection",
                "conn",
                "fConn",
            ):
                val = getattr(target, attr, None)
                if val is not None:
                    if isinstance(val, int):
                        return val
                    elif isinstance(val, (str, float)):
                        try:
                            return int(val)
                        except Exception:
                            pass
                    elif isinstance(val, dict):
                        cid = val.get(
                            "connection_id", val.get("connectionId", val.get("id"))
                        )
                        if cid is not None:
                            try:
                                return int(cid)
                            except Exception:
                                pass
                    elif (
                        hasattr(val, "id")
                        or hasattr(val, "connection_id")
                        or hasattr(val, "connectionId")
                    ):
                        cid = getattr(
                            val,
                            "connection_id",
                            getattr(val, "connectionId", getattr(val, "id", None)),
                        )
                        if cid is not None:
                            try:
                                return int(cid)
                            except Exception:
                                pass

            # 3. QGraphicsItem.data()
            if hasattr(target, "data"):
                try:
                    for role in (0, 1, 2, 32):
                        d = target.data(role)
                        if isinstance(d, int):
                            return d
                        elif isinstance(d, (str, float)):
                            try:
                                return int(d)
                            except Exception:
                                pass
                except Exception:
                    pass

            target = target.parentItem()

        return None

    def eventFilter(self, watched, event):
        if watched is not self.graphicsView.viewport():
            return False

        if getattr(self, "_inSyntheticMouseMove", False):
            return False

        etype = event.type()
        is_press = (
            etype == QEvent.MouseButtonPress
            or (hasattr(QEvent, "Type") and etype == QEvent.Type.MouseButtonPress)
            or str(etype).endswith("MouseButtonPress")
        )
        is_move = (
            etype == QEvent.MouseMove
            or (hasattr(QEvent, "Type") and etype == QEvent.Type.MouseMove)
            or str(etype).endswith("MouseMove")
        )
        is_release = (
            etype == QEvent.MouseButtonRelease
            or (hasattr(QEvent, "Type") and etype == QEvent.Type.MouseButtonRelease)
            or str(etype).endswith("MouseButtonRelease")
        )
        is_resize = (
            etype == QEvent.Resize
            or (hasattr(QEvent, "Type") and etype == QEvent.Type.Resize)
            or str(etype).endswith("Resize")
        )

        # 1. UI-based Disconnect: Alt+Click, Shift+Click, or Middle-Click on Port or Cable
        if is_press:
            btn = event.button()
            mods = event.modifiers()
            keyboard_mods = QApplication.keyboardModifiers()
            is_alt = bool((mods & Qt.AltModifier) or (keyboard_mods & Qt.AltModifier))
            is_shift = bool(
                (mods & Qt.ShiftModifier) or (keyboard_mods & Qt.ShiftModifier)
            )
            is_middle_click = btn == Qt.MiddleButton
            is_disconnect_click = is_middle_click or (
                btn in (Qt.LeftButton, Qt.RightButton) and (is_alt or is_shift)
            )

            if is_disconnect_click:
                target_type, val1, val2 = self.findPortOrCableUnderMouse(event.pos())
                if target_type == "port":
                    gid, pid = val1, val2
                    conns_to_drop = [
                        cid
                        for cid, (cgOut, cpOut, cgIn, cpIn) in list(
                            self.hostWindow.fConnections.items()
                        )
                        if (cgOut == gid and cpOut == pid)
                        or (cgIn == gid and cpIn == pid)
                    ]
                    conn_list = getattr(
                        getattr(patchcanvas, "canvas", None), "connection_list", None
                    )
                    if conn_list:
                        for conn in conn_list:
                            cgOut = getattr(
                                conn,
                                "group_out_id",
                                getattr(conn, "m_group_out_id", None),
                            )
                            cpOut = getattr(
                                conn,
                                "port_out_id",
                                getattr(conn, "m_port_out_id", None),
                            )
                            cgIn = getattr(
                                conn,
                                "group_in_id",
                                getattr(conn, "m_group_in_id", None),
                            )
                            cpIn = getattr(
                                conn, "port_in_id", getattr(conn, "m_port_in_id", None)
                            )
                            if (cgOut == gid and cpOut == pid) or (
                                cgIn == gid and cpIn == pid
                            ):
                                cid = getattr(
                                    conn,
                                    "connection_id",
                                    getattr(
                                        conn, "connectionId", getattr(conn, "id", None)
                                    ),
                                )
                                if cid is not None and int(cid) not in conns_to_drop:
                                    conns_to_drop.append(int(cid))

                    log_carla(
                        f"carla_canvas: UI disconnect port ({gid}:{pid}) -> dropping {len(conns_to_drop)} connections (is_alt={is_alt})"
                    )
                    if conns_to_drop:
                        for cid in conns_to_drop:
                            partner_cid = (
                                findStereoPartnerConnection(cid) if is_alt else None
                            )
                            self.hostWindow.host.patchbay_disconnect(
                                self.hostWindow.fExternalPatchbay, cid
                            )
                            if partner_cid is not None:
                                log_carla(
                                    f"carla_canvas: Also disconnecting stereo partner connection {partner_cid}"
                                )
                                self.hostWindow.host.patchbay_disconnect(
                                    self.hostWindow.fExternalPatchbay, partner_cid
                                )
                        return True

                elif target_type == "cable":
                    conn_id = val1
                    log_carla(
                        f"carla_canvas: UI disconnect cable (connectionId={conn_id}, is_alt={is_alt})"
                    )
                    partner_cid = (
                        findStereoPartnerConnection(conn_id) if is_alt else None
                    )
                    self.hostWindow.host.patchbay_disconnect(
                        self.hostWindow.fExternalPatchbay, conn_id
                    )
                    if partner_cid is not None:
                        log_carla(
                            f"carla_canvas: Also disconnecting stereo partner connection {partner_cid}"
                        )
                        self.hostWindow.host.patchbay_disconnect(
                            self.hostWindow.fExternalPatchbay, partner_cid
                        )
                    return True

            # Normal drag tracking for auto-scrolling
            if btn in (Qt.LeftButton, Qt.MiddleButton, Qt.RightButton):
                self._dragActive = True

        elif is_move:
            if getattr(self, "_dragActive", False):
                self._checkStartAutoScroll()

        elif is_release:
            if QApplication.mouseButtons() == Qt.NoButton:
                self._dragActive = False
                if self._scrollTimer.isActive():
                    self._scrollTimer.stop()

        elif is_resize:
            if hasattr(self, "toolBar") and self.toolBar:
                self.toolBar.reposition()
            if hasattr(self, "contextToolBar") and self.contextToolBar:
                self.contextToolBar.reposition()

        return False

    def _checkStartAutoScroll(self):
        vp = self.graphicsView.viewport()
        cur_vp_pos = vp.mapFromGlobal(QCursor.pos())
        x = cur_vp_pos.x()
        y = cur_vp_pos.y()
        W = vp.width()
        H = vp.height()
        margin = 40

        near_edge = x < margin or x > W - margin or y < margin or y > H - margin
        if near_edge:
            if not self._scrollTimer.isActive():
                self._scrollTimer.start()
        else:
            if self._scrollTimer.isActive():
                self._scrollTimer.stop()

    def _slot_autoScroll(self):
        if (
            not getattr(self, "_dragActive", False)
            or QApplication.mouseButtons() == Qt.NoButton
        ):
            self._dragActive = False
            if self._scrollTimer.isActive():
                self._scrollTimer.stop()
            return

        vp = self.graphicsView.viewport()
        cur_global_pos = QCursor.pos()
        cur_vp_pos = vp.mapFromGlobal(cur_global_pos)
        x = cur_vp_pos.x()
        y = cur_vp_pos.y()
        W = vp.width()
        H = vp.height()
        margin = 40

        dx = 0
        dy = 0

        if x < margin:
            dist = margin - x
            dx = -min(40, max(5, int(dist * 0.4)))
        elif x > W - margin:
            dist = x - (W - margin)
            dx = min(40, max(5, int(dist * 0.4)))

        if y < margin:
            dist = margin - y
            dy = -min(40, max(5, int(dist * 0.4)))
        elif y > H - margin:
            dist = y - (H - margin)
            dy = min(40, max(5, int(dist * 0.4)))

        if dx != 0 or dy != 0:
            hsb = self.graphicsView.horizontalScrollBar()
            vsb = self.graphicsView.verticalScrollBar()
            if dx != 0:
                hsb.setValue(hsb.value() + dx)
            if dy != 0:
                vsb.setValue(vsb.value() + dy)

            # Keep dragging lines / items updated by sending a synthetic mouse move
            try:
                self._inSyntheticMouseMove = True
                fake_event = QMouseEvent(
                    QEvent.MouseMove,
                    QPointF(cur_vp_pos),
                    QPointF(cur_global_pos),
                    Qt.NoButton,
                    QApplication.mouseButtons(),
                    QApplication.keyboardModifiers(),
                )
                QApplication.sendEvent(vp, fake_event)
            except Exception:
                pass
            finally:
                self._inSyntheticMouseMove = False
        else:
            if self._scrollTimer.isActive():
                self._scrollTimer.stop()


# ------------------------------------------------------------------------------------------------------------
# Canvas Action Callback
# ------------------------------------------------------------------------------------------------------------


def canvasCallback(action, value1, value2, valueStr):
    if gCarla.gui is None:
        return
    host = gCarla.gui.host

    if getattr(gCarla.gui, "fCustomStopAction", 0) == getattr(
        gCarla.gui, "CUSTOM_ACTION_APP_CLOSE", 1
    ):
        return

    if (
        action == patchcanvas.ACTION_GROUP_INFO
        or action == patchcanvas.ACTION_GROUP_RENAME
    ):
        pass

    elif action == patchcanvas.ACTION_GROUP_SPLIT:
        groupId = value1
        patchcanvas.splitGroup(groupId)
        gCarla.gui.updateMiniCanvasLater()

    elif action == patchcanvas.ACTION_GROUP_JOIN:
        groupId = value1
        patchcanvas.joinGroup(groupId)
        gCarla.gui.updateMiniCanvasLater()

    elif action == patchcanvas.ACTION_GROUP_POSITION:
        if gCarla.gui.fIsProjectLoading:
            return
        if not host.is_engine_running():
            return
        groupId = value1
        x1, y1, x2, y2 = tuple(int(i) for i in valueStr.split(":"))
        host.patchbay_set_group_pos(
            gCarla.gui.fExternalPatchbay, groupId, x1, y1, x2, y2
        )
        if hasattr(gCarla.gui, "markProjectModified"):
            gCarla.gui.markProjectModified()
        if hasattr(gCarla.gui, "fSessionManager") and gCarla.gui.fSessionManager:
            gCarla.gui.fSessionManager.queue_node_position_sync()
        gCarla.gui.updateMiniCanvasLater()

    elif (
        action == patchcanvas.ACTION_PORT_INFO
        or action == patchcanvas.ACTION_PORT_RENAME
    ):
        pass

    elif action == patchcanvas.ACTION_PORTS_CONNECT:
        gOut, pOut, gIn, pIn = tuple(int(i) for i in valueStr.split(":"))
        log_carla(
            f"carla_canvas: ACTION_PORTS_CONNECT {gOut}:{pOut} -> {gIn}:{pIn} (external={gCarla.gui.fExternalPatchbay})"
        )

        if not host.patchbay_connect(
            gCarla.gui.fExternalPatchbay, gOut, pOut, gIn, pIn
        ):
            err = host.get_last_error()
            log_carla(f"carla_canvas: Connection failed: {err}", level="warn")
        else:
            log_carla("carla_canvas: Connection request succeeded", level="debug")
            if hasattr(gCarla.gui, "markProjectModified"):
                gCarla.gui.markProjectModified()
            if QApplication.keyboardModifiers() & Qt.AltModifier:
                autoConnectStereoPair(gOut, pOut, gIn, pIn)

    elif action == patchcanvas.ACTION_PORTS_DISCONNECT:
        connectionId = value1
        log_carla(
            f"carla_canvas: ACTION_PORTS_DISCONNECT connectionId={connectionId} (external={gCarla.gui.fExternalPatchbay})",
            level="debug",
        )

        alt_pressed = bool(QApplication.keyboardModifiers() & Qt.AltModifier)
        partner_conn_id = None
        if alt_pressed:
            partner_conn_id = findStereoPartnerConnection(connectionId)

        if not host.patchbay_disconnect(gCarla.gui.fExternalPatchbay, connectionId):
            err = host.get_last_error()
            log_carla(f"carla_canvas: Disconnect failed: {err}", level="warn")
        else:
            log_carla("carla_canvas: Disconnect request succeeded")
            if hasattr(gCarla.gui, "markProjectModified"):
                gCarla.gui.markProjectModified()
            if partner_conn_id is not None:
                log_carla(
                    f"carla_canvas: Stereo auto-disconnect (Alt): connectionId={partner_conn_id}"
                )
                host.patchbay_disconnect(gCarla.gui.fExternalPatchbay, partner_conn_id)

    elif action == patchcanvas.ACTION_PLUGIN_CLONE:
        pluginId = value1

        if not host.clone_plugin(pluginId):
            CustomMessageBox(
                gCarla.gui,
                QMessageBox.Warning,
                gCarla.gui.tr("Error"),
                gCarla.gui.tr("Operation failed"),
                host.get_last_error(),
                QMessageBox.Ok,
                QMessageBox.Ok,
            )

    elif action == patchcanvas.ACTION_PLUGIN_EDIT:
        pluginId = value1
        pwidget = gCarla.gui.getPluginSlotWidget(pluginId)

        if pwidget is not None:
            pwidget.showEditDialog()

    elif action == patchcanvas.ACTION_PLUGIN_RENAME:
        pluginId = value1
        pwidget = gCarla.gui.getPluginSlotWidget(pluginId)

        if pwidget is not None:
            pwidget.showRenameDialog()

    elif action == patchcanvas.ACTION_PLUGIN_REPLACE:
        pluginId = value1
        pwidget = gCarla.gui.getPluginSlotWidget(pluginId)

        if pwidget is not None:
            pwidget.showReplaceDialog()

    elif action == patchcanvas.ACTION_PLUGIN_REMOVE:
        pluginId = value1

        if not host.remove_plugin(pluginId):
            CustomMessageBox(
                gCarla.gui,
                QMessageBox.Warning,
                gCarla.gui.tr("Error"),
                gCarla.gui.tr("Operation failed"),
                host.get_last_error(),
                QMessageBox.Ok,
                QMessageBox.Ok,
            )

    elif action == patchcanvas.ACTION_PLUGIN_SHOW_UI:
        pluginId = value1
        pwidget = gCarla.gui.getPluginSlotWidget(pluginId)

        if pwidget is not None:
            pwidget.showCustomUI()

    elif action == patchcanvas.ACTION_BG_RIGHT_CLICK:
        gCarla.gui.slot_showPluginActionsMenu(value1, value2)

    elif action == patchcanvas.ACTION_INLINE_DISPLAY:
        if gCarla.gui.fIsProjectLoading:
            return
        if not host.is_engine_running():
            return
        pluginId = value1
        width, height = [int(v) for v in valueStr.split(":")]
        return host.render_inline_display(pluginId, width, height)

    elif action == getattr(patchcanvas, "ACTION_PLUGIN_COLOR", 17):
        pluginId = value1
        colorStr = valueStr
        if colorStr:
            c = QColor(colorStr)
            color_tuple = (c.red(), c.green(), c.blue())
            color_data_str = f"{c.red()};{c.green()};{c.blue()}"
            gCarla.gui.changePluginColor(pluginId, color_tuple, color_data_str)
        else:
            gCarla.gui.changePluginColor(pluginId, (255, 255, 255), "255;255;255")
